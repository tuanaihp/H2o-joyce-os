"""Bầu trời tri thức - dữ liệu cho quả tinh cầu (thiết kế: docs/dev/2026-10-bau-troi-tri-thuc.md).

Mỗi tài liệu kiến thức trong brain là một thiên thể:
- đá vụn (`debris`): sources/, inbox/ - tài liệu thô chưa chưng cất;
- chấm trên vành (`orbit`, ring 0/1/2): kỹ năng / quy trình Joyce (workflows) / trí nhớ doanh nghiệp;
- sao (`star`): trang wiki đã chưng cất; trang là quy trình mang cờ `proc` (vẽ sao bốn cánh).

Phạm vi (chốt 2026-10-08): admin đứng ở brain chủ (Brain Default) thấy trời GỘP mọi brain;
admin mở brain một phòng thì chỉ phòng đó; nhân viên thì brain đang mở. Phạm vi nhân viên KHÔNG
tự tính ở đây: gốc brain đi qua `_brain_root` của main.py, vốn đã ép vào phòng được gán.

Chỉ đọc. Thiên thể mang `brain` là tên thư mục brain (key), `path` là đường dẫn trong brain đó.
Đường dẫn gốc chỉ đi ra ở mảng `brains` và chỉ cho brain TRONG phạm vi (để mở file khi bấm).
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


def register(app, brain_root_fn, default_dir_fn, is_staff_fn, brains_dir, scope_fn=None):
    """scope_fn(): các gốc brain nhân viên được phép (rỗng = admin), cho thiên hà phòng ban."""
    _deps.update(brain_root=brain_root_fn, default_dir=default_dir_fn,
                 is_staff=is_staff_fn, brains_dir=str(brains_dir), scope=scope_fn or (lambda: ()))
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

    def them(p: Path, kind: str, ring: int, title: str, info: dict, proc: bool = False):
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            return
        b = {"id": _id_of(key, rel), "kind": kind, "ring": ring, "brain": key, "path": rel,
             "title": title or p.stem, "_links": info.get("links") or [],
             "_stem": p.stem.lower(), "_mtime": info.get("mtime") or 0}
        if proc:
            b["proc"] = True
        out.append(b)

    # Đá vụn: nguyên liệu thô, mọi loại file.
    for thu_muc in ("sources", "inbox"):
        base = root / thu_muc
        if not base.is_dir():
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if not _bo_qua(d)]
            co = {f.lower() for f in fns}
            for fn in fns:
                if _bo_qua(fn) or _la_ban_chu(fn, co):
                    continue
                p = Path(dp) / fn
                info = _info(p) if fn.lower().endswith(".md") else {"mtime": _mtime(p)}
                them(p, "debris", 0, info.get("title") or "", info)
    # Vành 0: kỹ năng của brain. Bỏ skill HỆ THỐNG (joyce-builder, notes...): mỗi brain đều mang
    # một bản sao, tính vào thì 46 brain thành 276 chấm giống hệt nhau, không phải kiến thức.
    sk = root / "skills"
    if sk.is_dir():
        for d in sorted(sk.iterdir()):
            f = d / "SKILL.md"
            if d.is_dir() and not _bo_qua(d.name) and f.is_file() and not _skill_he_thong(d.name):
                info = _info(f)
                them(f, "orbit", 0, info.get("title") or d.name, info)
    # Vành 1: quy trình Joyce (workflows); vành 2: trí nhớ doanh nghiệp.
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
    # Sao: MỌI trang wiki đã chưng cất. Wiki của H2O phần lớn là quy trình (214/222 lúc viết),
    # đưa chúng lên vành thì bầu trời trống trơn và một vành chật cứng; nên quy trình vẫn là
    # sao, chỉ mang cờ `proc` để vẽ khác hình.
    wk = root / "wiki"
    if wk.is_dir():
        for dp, dns, fns in os.walk(wk):
            dns[:] = [d for d in dns if not _bo_qua(d) and d not in _BO_THU_MUC]
            for fn in fns:
                if _bo_qua(fn) or not fn.lower().endswith(".md") or fn.lower() in _BO_TEN:
                    continue
                p = Path(dp) / fn
                info = _info(p)
                them(p, "star", 0, info.get("title") or "", info, proc=_la_quy_trinh(p.stem, info))
    return out


def _la_ban_chu(fn: str, cung_thu_muc: set) -> bool:
    """`X.docx.txt` nằm cạnh `X.docx`: bản chữ trích ra để chưng cất, CÙNG một tài liệu. Đếm cả
    hai thì 209 tài liệu .docx thành 418 viên đá vụn (chủ hỏi 2026-10-08 sao số liệu lệch)."""
    f = fn.lower()
    if not f.endswith(".txt"):
        return False
    goc = f[:-4]
    return "." in goc and goc in cung_thu_muc


def _skill_he_thong(slug: str) -> bool:
    try:
        import system_sync
        return system_sync.is_system_skill(slug)
    except Exception:
        return slug in {"joyce-builder", "ingest-source", "query-wiki", "lint-wiki", "notes", "html-to-webcake"}


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


def _tat_ca(brain: str):
    """(scope, [(key, gốc)], thiên thể ĐẦY ĐỦ kể cả trường nội bộ `_*`) - dùng chung cho dựng
    bầu trời và tìm kiếm, để hai bên luôn cùng phạm vi, cùng phân loại."""
    scope, ds = _pham_vi(brain)
    bodies = []
    for key, root in ds:
        bodies.extend(_quet_brain(root, key))
    return scope, ds, bodies


def _dung_troi(brain: str) -> dict:
    scope, ds, bodies = _tat_ca(brain)
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
    counts = {"star": 0, "orbit": 0, "debris": 0, "total": tong, "proc": 0, "skill": 0, "workflow": 0,
              "memory": 0, "brains": len(ds), "brands": {}}
    tt = {k: _thong_tin_brain(k) for k, _ in ds}
    for b in bodies:
        counts[b["kind"]] += 1
        if b.get("proc"):
            counts["proc"] += 1
        if b["kind"] == "orbit":
            counts[("skill", "workflow", "memory")[b["ring"]]] += 1
        ten = tt.get(b["brain"], {}).get("brand") or ""
        counts["brands"][ten] = counts["brands"].get(ten, 0) + 1
    gon = [{k: v for k, v in b.items() if not k.startswith("_")} for b in bodies[:_TOI_DA_THIEN_THE]]
    # `path` của từng brain: để trình duyệt mở được file ở brain phòng khác khi bấm một thiên thể
    # (bầu trời gộp của admin). Chỉ brain TRONG phạm vi mới có mặt ở đây, nên nhân viên không
    # thấy đường dẫn phòng khác; thiên thể vẫn chỉ mang key + đường dẫn trong brain.
    return {"ok": True, "scope": scope, "brains": [dict(_thong_tin_brain(k), path=str(r)) for k, r in ds],
            "bodies": gon, "counts": counts, "truncated": tong > len(gon)}


# ---------------------------------------------------------------- tìm kiếm (giai đoạn 2)
_cache_chu: dict = {}   # đường dẫn tuyệt đối -> (mtime, size, nội dung đã gấp về khoá so)
_TOI_DA_KQ = 60


def _chu_gap(p: Path) -> str:
    """Nội dung file văn bản, gấp bằng _khoa_so (bỏ dấu, chỉ chữ/số) - cache theo mtime+size."""
    try:
        st = p.stat()
    except OSError:
        return ""
    hit = _cache_chu.get(str(p))
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    chu = " " + _khoa_so(_doc_text(p)) + " "
    _cache_chu[str(p)] = (st.st_mtime, st.st_size, chu)
    return chu


def tim(brain: str, q: str) -> dict:
    """Tìm trong CÙNG phạm vi bầu trời (admin ở brain chủ = mọi phòng). Khớp cả CỤM từ khoá
    (không dấu): tên/tiêu đề được 3 điểm, nội dung được 1 điểm cộng theo số lần xuất hiện,
    rồi cộng nửa cỡ thiên thể để tài liệu nhiều liên kết đứng trước khi ngang điểm."""
    cum = _khoa_so(q)
    scope, ds, bodies = _tat_ca(brain)
    if not cum:
        return {"ok": True, "q": q, "scope": scope, "hits": [], "total": 0}
    goc = dict(ds)
    vao = {}
    for b in bodies:
        for ln in b["_links"]:
            vao[ln] = vao.get(ln, 0) + 1
    import math
    kq = []
    for b in bodies:
        ten = " " + _khoa_so(b["title"] + " " + Path(b["path"]).stem) + " "
        diem = 0.0
        if cum in ten:
            diem = 3.0 + (0.5 if (" " + cum + " ") in ten else 0.0)
        elif b["path"].lower().endswith((".md", ".txt")) and b["brain"] in goc:
            n = _chu_gap(goc[b["brain"]] / b["path"]).count(cum)
            if n:
                diem = 1.0 + min(1.0, n / 10)
        if diem:
            co = min(1.0, math.log1p(vao.get(b["_stem"], 0) * 2 + len(b["_links"])) / math.log1p(40))
            kq.append((diem + co * 0.5, co, b))
    kq.sort(key=lambda x: (-x[0], x[2]["id"]))
    hits = []
    for diem, co, b in kq[:_TOI_DA_KQ]:
        h = {k: v for k, v in b.items() if not k.startswith("_")}
        h.update(score=round(diem, 3), size=round(co, 3), stem=b["_stem"], links=b["_links"][:30])
        hits.append(h)
    return {"ok": True, "q": q, "scope": scope, "hits": hits, "total": len(kq)}


@router.get("/knowledge/search")
async def knowledge_search(brain: str = Query("brain"), q: str = Query("")):
    from starlette.concurrency import run_in_threadpool
    if len(q or "") > 200:
        return _err("từ khoá quá dài")
    return await run_in_threadpool(tim, brain, q or "")


# ---------------------------------------------------------------- thiên hà phòng ban
# Thiết kế: docs/dev/2026-10-thien-ha-phong-ban.md. Mỗi brain phòng ban là một tinh cầu ở tầng zoom
# Thiên hà; số liệu ở đây quyết định to nhỏ, sáng tối, nhấp nháy đỏ, hố đen nhỏ, số mặt trăng.
_cache_ha: dict = {}


def _viec_ket() -> dict:
    """Số việc KẸT (status blocked) trên bảng Việc theo gốc brain. Đọc thẳng SQLite chỉ đọc; lỗi
    thì trả rỗng (thiên hà vẫn vẽ, chỉ không nhấp nháy)."""
    out = {}
    try:
        import sqlite3
        import config as cfgmod
        db = Path(cfgmod.STATE_DIR) / "kanban.sqlite3"
        if not db.is_file():
            return out
        con = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True, timeout=2)
        try:
            for root, n in con.execute("select brain_root, count(*) from tasks where status = 'blocked' group by brain_root"):
                if root:
                    out[os.path.normcase(str(Path(root).resolve()))] = int(n)
        finally:
            con.close()
    except Exception:
        return {}
    return out


def _dong_thien_ha(key: str, root: Path, ket: dict, bay_gio: float) -> dict:
    bs = _quet_brain(root, key)
    ag = root / "agents"
    return {
        "key": key, "path": str(root),
        "docs": sum(1 for b in bs if b["kind"] != "debris"),
        "raw": sum(1 for b in bs if b["kind"] == "debris"),
        "proc": sum(1 for b in bs if b.get("proc")),
        "recent7": sum(1 for b in bs if b["_mtime"] and bay_gio - b["_mtime"] < _GAN_DAY),
        "agents": len([f for f in ag.glob("*.md") if not _bo_qua(f.name)]) if ag.is_dir() else 0,
        "stuck": ket.get(os.path.normcase(str(root.resolve())), 0),
    }


def dung_thien_ha() -> dict:
    """Thiên hà: brain chủ (Trái Đất), brain chung của từng thương hiệu (ngôi sao đầu cánh tay),
    và mọi brain phòng ban kèm khối / thương hiệu / số liệu. Nhân viên chỉ thấy phòng được gán,
    các phòng khác chỉ là con số `others` (đốm sao mờ không tên)."""
    import h2o_departments as hd
    base = Path(_deps["brains_dir"])
    la_nv = bool(_deps["is_staff"]())
    duoc = None
    if la_nv:   # phạm vi nhân viên: đúng các gốc mà _brain_root cho phép
        duoc = {os.path.normcase(str(Path(r).resolve())) for r in (_deps.get("scope", lambda: ())() or ())}
    ket, bay_gio = _viec_ket(), time.time()
    brands = {b.get("id"): b for b in hd.brands()}
    ds = hd.list_all()
    khoi = {k["id"]: k for k in ds.get("khoi", [])}
    out_khoi = [{"id": k["id"], "ten": k.get("ten", k["id"]), "brand": k.get("brand") or "h2o"} for k in ds.get("khoi", [])]
    phong, others = [], 0
    for p in ds.get("phong", []):
        ten_brain = str(p.get("brain") or "").strip()
        root = base / ten_brain
        if not ten_brain or not root.is_dir():
            continue
        if duoc is not None and os.path.normcase(str(root.resolve())) not in duoc:
            others += 1
            continue
        k = khoi.get(p.get("khoi_id")) or {}
        d = _dong_thien_ha(ten_brain, root.resolve(), ket, bay_gio)
        d.update(ten=p.get("ten") or ten_brain, khoi=p.get("khoi_id") or "", khoi_ten=k.get("ten", ""),
                 brand=k.get("brand") or "h2o")
        phong.append(d)
    sao = []
    for bid, b in brands.items():
        sb = str(hd.shared_brain_of_brand(b) or "")
        root = base / sb
        if sb and root.is_dir():
            d = _dong_thien_ha(sb, root.resolve(), ket, bay_gio)
            d.update(ten=b.get("ten") or sb, brand=bid)
            sao.append(d)
    earth = None
    if not la_nv:
        chu = Path(_deps["default_dir"]()).resolve()
        earth = _dong_thien_ha(chu.name, chu, ket, bay_gio)
        earth.update(ten=chu.name)
    return {"ok": True, "staff": la_nv, "earth": earth, "stars": sao, "khoi": out_khoi,
            "phong": phong, "others": others}


@router.get("/knowledge/galaxy")
async def knowledge_galaxy(fresh: bool = Query(False)):
    from starlette.concurrency import run_in_threadpool
    ck = (bool(_deps["is_staff"]()), tuple(_deps.get("scope", lambda: ())() or ()))
    hit = _cache_ha.get(ck)
    if hit and not fresh and time.time() - hit[0] < _HAN_CACHE:
        return hit[1]
    data = await run_in_threadpool(dung_thien_ha)
    _cache_ha[ck] = (time.time(), data)
    return data


@router.get("/knowledge/sky")
async def knowledge_sky(brain: str = Query("brain"), fresh: bool = Query(False)):
    """`fresh=1`: bỏ qua cache 60 giây - hud.js gọi ngay sau khi nạp dữ liệu xong để tài liệu vừa
    chưng cất hiện thành sao mới liền, không phải chờ cache hết hạn."""
    from starlette.concurrency import run_in_threadpool
    root = str(Path(_deps["brain_root"](brain)).resolve())
    ck = (root, bool(_deps["is_staff"]()))
    hit = _cache_troi.get(ck)
    if hit and not fresh and time.time() - hit[0] < _HAN_CACHE:
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


def _co_nghia(s: str) -> bool:
    """Ít nhất hai từ có chữ cái thật: loại "01/ KHCN", "Trang 01", mã hiệu."""
    return sum(1 for w in s.split() if sum(ch.isalpha() for ch in w) >= 2) >= 2


def _khoa_so(s: str) -> str:
    """Khoá so trùng: bỏ dấu, bỏ số thứ tự đầu, mọi ký tự không phải chữ/số thành một dấu cách.
    Để "Bảng giá" trùng tên file `bang-gia.md`, "Quy Trình X" trùng `1. Quy Trình X.md`."""
    return " ".join(re.sub(r"[^0-9a-z]+", " ", _fold(_RE_SO_DAU.sub("", s))).split())


def _them_muc(out: list, s: str, ten_file: str):
    s = _cat(s)
    if len(s) < 3 or _khoa_so(s) == _khoa_so(ten_file) or _RE_RAC.match(s) or not _co_nghia(s):
        return
    if _khoa_so(s) not in {_khoa_so(x) for x in out}:
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
    # 5. ba câu đầu - chỉ từ dòng ra câu (>= 5 từ). Ghép mọi dòng lại như bản đầu thì trang bìa
    # .docx (mã hiệu, ngày ban hành, số trang) thành một "câu" rác dài.
    van = " ".join(x.strip() for x in dong if len(x.split()) >= 5 and not x.lstrip().startswith((">", "|")))
    out2 = list(out)
    for c in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", van))[:3]:
        _them_muc(out2, c, ten_file)
    return out2[:toi_da]


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
    ban_chu = p.with_name(p.name + ".txt")   # X.docx -> X.docx.txt (bản chữ trích sẵn)
    if not la_md and ban_chu.is_file():
        la_md = True
        txt = _doc_text(ban_chu)
    else:
        txt = _doc_text(p) if la_md else ""
    info = _info(p) if p.suffix.lower() == ".md" else {}
    return {"ok": True, "title": info.get("title") or p.stem, "brain_name": goc.name, "src": goc.name,
            "path": rel, "updated": _mtime(p), "text_file": la_md,
            "bullets": dau_muc(txt, p.stem) if la_md else []}
