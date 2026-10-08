"""Bầu trời tri thức - dữ liệu cho quả tinh cầu (thiết kế: docs/dev/2026-10-bau-troi-tri-thuc.md).

Mỗi tài liệu kiến thức trong brain là một thiên thể:
- đá vụn (`debris`): sources/, inbox/ - tài liệu thô chưa chưng cất;
- chấm trên vành (`orbit`, ring 0/1/2): kỹ năng / quy trình / trí nhớ doanh nghiệp;
- sao (`star`): trang wiki đã chưng cất.

Phạm vi (chốt 2026-10-08): admin đứng ở brain chủ (Brain Default) thấy trời GỘP mọi brain;
admin mở brain một phòng thì chỉ phòng đó; nhân viên thì brain đang mở. Phạm vi nhân viên KHÔNG
tự tính ở đây: gốc brain đi qua `_brain_root` của main.py, vốn đã ép vào phòng được gán.

Chỉ đọc. Đường dẫn tuyệt đối không bao giờ ra khỏi máy chủ: thiên thể mang `brain` là tên thư
mục brain (key), `path` là đường dẫn trong brain đó.
"""
from __future__ import annotations

import os
import re
import time
import zlib
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()

_deps = {}   # main.py inject: brain_root(brain) -> str, default_dir() -> Path, is_staff() -> bool, brains_dir

# Tên file quản trị wiki và thư mục hệ thống - không phải kiến thức.
_BO_TEN = {"index.md", "log.md", "readme.md"}
_BO_THU_MUC = {"Joyce", "attachments", "agents", "00 - Dashboard", "01 - Daily Log",
               "02 - Weekly Log", "03 - Monthly Log", "04 - Future Log", "node_modules"}
_TOI_DA_THIEN_THE = 6000
_DOC_TOI_DA = 200_000
_HAN_CACHE = 60.0
_GAN_DAY = 7 * 86400

# Màu theo thương hiệu: tên màu trong PAL của renderer (brain-planet.js), không phải mã màu.
_MAU_BRAND = ["cyan", "magenta", "mint", "violet"]
_MAU_CHU = "gold"

_cache_file: dict = {}    # đường dẫn tuyệt đối -> (mtime, size, info)
_cache_troi: dict = {}    # (gốc, scope) -> (lúc dựng, payload)

_RE_LINK = re.compile(r"\[\[([^\]|#]+)")
_RE_SO_DAU = re.compile(r"^\s*\d+\s*[.)-]\s*")


def register(app, brain_root_fn, default_dir_fn, is_staff_fn, brains_dir):
    _deps.update(brain_root=brain_root_fn, default_dir=default_dir_fn,
                 is_staff=is_staff_fn, brains_dir=str(brains_dir))
    app.include_router(router)


def _err(msg: str, status: int = 400):
    return JSONResponse({"ok": False, "error": msg}, status_code=status)


def _fold(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def _id_of(brain_key: str, rel: str) -> str:
    """Băm cố định: cùng tài liệu luôn cùng id, cũng là hạt giống vị trí phía trình duyệt."""
    return format(zlib.crc32((brain_key + "/" + rel).encode("utf-8")) & 0xFFFFFFFF, "08x")


# ---------------------------------------------------------------- đọc tài liệu
def _frontmatter(txt: str) -> dict:
    """Frontmatter YAML tối giản (khoá: giá trị một dòng, danh sách [a, b] hoặc - a). Đủ cho
    title / name / tags / tom_tat / summary; không kéo thư viện YAML vào đường nóng."""
    if not txt.startswith("---"):
        return {}
    end = txt.find("\n---", 3)
    if end < 0:
        return {}
    out, khoa = {}, None
    for dong in txt[3:end].splitlines():
        if not dong.strip():
            continue
        if dong.lstrip().startswith("- ") and khoa:
            out.setdefault(khoa, [])
            if isinstance(out[khoa], list):
                out[khoa].append(dong.strip()[2:].strip().strip("\"'"))
            continue
        if ":" not in dong or dong.startswith(" "):
            continue
        k, v = dong.split(":", 1)
        khoa, v = k.strip().lower(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            out[khoa] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        elif v:
            out[khoa] = v.strip("\"'")
        else:
            out[khoa] = []
    return out


def _than(txt: str) -> str:
    """Phần thân sau frontmatter."""
    if txt.startswith("---"):
        end = txt.find("\n---", 3)
        if end >= 0:
            return txt[end + 4:]
    return txt


def _doc_text(p: Path) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(_DOC_TOI_DA)
    except OSError:
        return ""


def _info(p: Path) -> dict:
    """Tiêu đề, tag, liên kết đi của một file .md - cache theo mtime+size."""
    try:
        st = p.stat()
    except OSError:
        return {}
    key = str(p)
    hit = _cache_file.get(key)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    txt = _doc_text(p) if p.suffix.lower() == ".md" else ""
    fm = _frontmatter(txt) if txt else {}
    title = fm.get("title") or fm.get("name") or ""
    if isinstance(title, list):
        title = title[0] if title else ""
    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    links = {m.strip().split("/")[-1].lower() for m in _RE_LINK.findall(txt)} if txt else set()
    info = {"title": str(title).strip(), "tags": [str(t).lower() for t in tags],
            "links": sorted(links), "mtime": st.st_mtime}
    _cache_file[key] = (st.st_mtime, st.st_size, info)
    return info


def _la_quy_trinh(ten: str, info: dict) -> bool:
    if "quy-trinh" in (info.get("tags") or []):
        return True
    return _fold(_RE_SO_DAU.sub("", ten)).startswith("quy trinh")


# ---------------------------------------------------------------- quét một brain
def _bo_qua(name: str) -> bool:
    return name.startswith(".") or name.startswith("_")


def _quet_brain(root: Path, key: str) -> list:
    """Danh sách thiên thể của MỘT brain: (id, kind, ring, path, title, links_out, stem, mtime)."""
    out = []

    def them(p: Path, kind: str, ring: int, title: str, info: dict):
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            return
        out.append({"id": _id_of(key, rel), "kind": kind, "ring": ring, "brain": key, "path": rel,
                    "title": title or p.stem, "_links": info.get("links") or [],
                    "_stem": p.stem.lower(), "_mtime": info.get("mtime") or 0})

    # Đá vụn: nguyên liệu thô, mọi loại file.
    for thu_muc in ("sources", "inbox"):
        base = root / thu_muc
        if not base.is_dir():
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if not _bo_qua(d)]
            for fn in fns:
                if _bo_qua(fn):
                    continue
                p = Path(dp) / fn
                info = _info(p) if fn.lower().endswith(".md") else {"mtime": _mtime(p)}
                them(p, "debris", 0, info.get("title") or "", info)
    # Vành 0: kỹ năng.
    sk = root / "skills"
    if sk.is_dir():
        for d in sorted(sk.iterdir()):
            f = d / "SKILL.md"
            if d.is_dir() and not _bo_qua(d.name) and f.is_file():
                info = _info(f)
                them(f, "orbit", 0, info.get("title") or d.name, info)
    # Vành 1: quy trình (workflows + wiki quy trình); vành 2: trí nhớ doanh nghiệp.
    wf = root / "workflows"
    if wf.is_dir():
        for f in sorted(wf.glob("*.md")):
            if not _bo_qua(f.name):
                info = _info(f)
                them(f, "orbit", 1, info.get("title") or "", info)
    facts = root / "memory" / "facts"
    if facts.is_dir():
        for f in sorted(facts.glob("*.md")):
            if not _bo_qua(f.name):
                info = _info(f)
                them(f, "orbit", 2, info.get("title") or "", info)
    # Sao: wiki đã chưng cất (trừ quy trình, đã lên vành 1).
    wk = root / "wiki"
    if wk.is_dir():
        for dp, dns, fns in os.walk(wk):
            dns[:] = [d for d in dns if not _bo_qua(d) and d not in _BO_THU_MUC]
            for fn in fns:
                if _bo_qua(fn) or not fn.lower().endswith(".md") or fn.lower() in _BO_TEN:
                    continue
                p = Path(dp) / fn
                info = _info(p)
                if _la_quy_trinh(p.stem, info):
                    them(p, "orbit", 1, info.get("title") or "", info)
                else:
                    them(p, "star", 0, info.get("title") or "", info)
    return out


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


# ---------------------------------------------------------------- phạm vi + màu
def _la_brain(p: Path) -> bool:
    return p.is_dir() and not p.name.startswith(".") and any(
        (p / d).is_dir() for d in ("wiki", "skills", "sources", "memory"))


def _pham_vi(brain: str):
    """(scope, [(key, Path)]) - xem docstring module."""
    root = Path(_deps["brain_root"](brain)).resolve()
    if not _deps["is_staff"]():
        try:
            chu = Path(_deps["default_dir"]()).resolve()
        except Exception:
            chu = None
        if chu is not None and os.path.normcase(str(root)) == os.path.normcase(str(chu)):
            base = Path(_deps["brains_dir"])
            ds = [(p.name, p.resolve()) for p in sorted(base.iterdir()) if _la_brain(p)] if base.is_dir() else []
            if not any(os.path.normcase(str(r)) == os.path.normcase(str(root)) for _, r in ds):
                ds.insert(0, (root.name, root))
            return "all", ds
    return "brain", [(root.name, root)]


def _thong_tin_brain(key: str) -> dict:
    """Tên hiển thị, thương hiệu và màu của một brain (theo sổ phòng ban H2O)."""
    try:
        import h2o_departments as hd
        brands = hd.brands()
        bid = None
        phong = hd.phong_by_brain(key)
        if phong:
            b = hd.brand_of_phong(phong)
            bid = b and b.get("id")
        else:
            for b in brands:
                if str(hd.shared_brain_of_brand(b)).lower() == key.lower():
                    bid = b.get("id")
        if bid:
            idx = next((i for i, b in enumerate(brands) if b.get("id") == bid), 0)
            ten = next((b.get("ten") for b in brands if b.get("id") == bid), "")
            return {"key": key, "name": key, "brand": ten, "color": _MAU_BRAND[idx % len(_MAU_BRAND)]}
    except Exception:
        pass
    return {"key": key, "name": key, "brand": "", "color": _MAU_CHU}


def _dung_troi(brain: str) -> dict:
    scope, ds = _pham_vi(brain)
    bodies = []
    for key, root in ds:
        bodies.extend(_quet_brain(root, key))
    # Cỡ theo liên kết THẬT trong phạm vi: liên kết vào + liên kết đi, kẹp log.
    vao = {}
    for b in bodies:
        for ln in b["_links"]:
            vao[ln] = vao.get(ln, 0) + 1
    bay_gio = time.time()
    import math
    for b in bodies:
        n = vao.get(b["_stem"], 0) * 2 + len(b["_links"])
        b["size"] = round(min(1.0, math.log1p(n) / math.log1p(40)), 3)
        b["recent"] = bool(b["_mtime"] and bay_gio - b["_mtime"] < _GAN_DAY)
    bodies.sort(key=lambda b: (-b["size"], b["id"]))
    tong = len(bodies)
    counts = {"star": 0, "orbit": 0, "debris": 0, "total": tong}
    for b in bodies:
        counts[b["kind"]] += 1
    gon = [{k: v for k, v in b.items() if not k.startswith("_")} for b in bodies[:_TOI_DA_THIEN_THE]]
    return {"ok": True, "scope": scope, "brains": [_thong_tin_brain(k) for k, _ in ds],
            "bodies": gon, "counts": counts, "truncated": tong > len(gon)}


@router.get("/knowledge/sky")
async def knowledge_sky(brain: str = Query("brain")):
    from starlette.concurrency import run_in_threadpool
    root = str(Path(_deps["brain_root"](brain)).resolve())
    ck = (root, bool(_deps["is_staff"]()))
    hit = _cache_troi.get(ck)
    if hit and time.time() - hit[0] < _HAN_CACHE:
        return hit[1]
    data = await run_in_threadpool(_dung_troi, brain)
    _cache_troi[ck] = (time.time(), data)
    return data


# ---------------------------------------------------------------- đọc nhanh
_RE_TIEU_DE = re.compile(r"^\s{0,3}#{1,3}\s+(.+?)\s*#*\s*$")
_RE_GACH = re.compile(r"^(?:[-*+]|\d+[.)])\s+(.+)$")
_RE_RAC = re.compile(r"^[\W\d_]+$|^(trang|page|mã hiệu|lần ban hành|ngày ban hành)\b", re.I)


def _cat(s: str, n: int = 90) -> str:
    s = re.sub(r"\s+", " ", re.sub(r"[*_`]|\[\[|\]\]", "", s)).strip(" -:|")
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _them_muc(out: list, s: str, ten_file: str):
    s = _cat(s)
    if len(s) < 3 or _fold(s) == _fold(ten_file) or _RE_RAC.match(s):
        return
    if _fold(s) not in {_fold(x) for x in out}:
        out.append(s)


def dau_muc(txt: str, ten_file: str = "", toi_da: int = 6) -> list:
    """Rút 3-6 đầu mục có sẵn, KHÔNG gọi AI (mục 5.1 của tài liệu thiết kế)."""
    fm = _frontmatter(txt)
    for k in ("tom_tat", "summary"):
        v = fm.get(k)
        if v:
            out = []
            for s in (v if isinstance(v, list) else re.split(r"(?<=[.;])\s+", str(v))):
                _them_muc(out, s, ten_file)
            if len(out) >= 2:
                return out[:toi_da]
    than = _than(txt)
    dong = than.splitlines()
    # 2. tiêu đề markdown
    out = []
    for d in dong:
        m = _RE_TIEU_DE.match(d)
        if m:
            _them_muc(out, m.group(1), ten_file)
    if len(out) >= 2:
        return out[:toi_da]
    # 3. gạch đầu dòng cấp 1 trong 60 dòng đầu
    out = []
    for d in dong[:60]:
        if d[:1] in (" ", "\t"):
            continue
        m = _RE_GACH.match(d.strip()) if d.strip() else None
        if m:
            _them_muc(out, m.group(1), ten_file)
    if len(out) >= 2:
        return out[:toi_da]
    # 4. dòng tiêu đề trần (tài liệu chuyển từ .docx)
    out = []
    for d in dong[:400]:
        s = d.strip()
        if (4 <= len(s) <= 70 and not s.endswith((".", ",", ":", ";")) and len(s.split()) >= 2
                and not s.startswith((">", "|", "!", "[", "#", "-", "*"))):
            _them_muc(out, s, ten_file)
        if len(out) >= toi_da:
            break
    if len(out) >= 2:
        return out[:toi_da]
    # 5. ba câu đầu
    van = re.sub(r"\s+", " ", " ".join(x for x in dong if x.strip() and not x.lstrip().startswith(">")))
    out = []
    for c in re.split(r"(?<=[.!?])\s+", van)[:3]:
        _them_muc(out, c, ten_file)
    return out[:toi_da]


@router.get("/knowledge/quick")
async def knowledge_quick(brain: str = Query("brain"), src: str = Query(""), path: str = Query("")):
    scope, ds = _pham_vi(brain)
    goc = None
    if src:
        goc = next((r for k, r in ds if k == src), None)
    elif len(ds) == 1:
        goc = ds[0][1]
    if goc is None:
        return _err("brain ngoài phạm vi", 403)
    rel = (path or "").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return _err("đường dẫn không hợp lệ")
    p = (goc / rel).resolve()
    try:
        p.relative_to(goc)
    except ValueError:
        return _err("đường dẫn ngoài brain", 403)
    if not p.is_file():
        return _err("không thấy tài liệu", 404)
    la_md = p.suffix.lower() in (".md", ".txt")
    txt = _doc_text(p) if la_md else ""
    info = _info(p) if p.suffix.lower() == ".md" else {}
    return {"ok": True, "title": info.get("title") or p.stem, "brain_name": goc.name, "src": goc.name,
            "path": rel, "updated": _mtime(p), "text_file": la_md,
            "bullets": dau_muc(txt, p.stem) if la_md else []}
