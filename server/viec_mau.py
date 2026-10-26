"""Việc mẫu theo phòng - "Chat công việc hằng ngày" (docs/dev/2026-10-chat-cong-viec-hang-ngay.md).

Mỗi brain có một danh sách "việc mẫu": những việc nhân viên làm hằng ngày, hiện thành chip ở
khung chat. Bấm chip -> điền form ngắn -> Joyce làm. Làm xong bấm "Đã xong" thì:
  1. việc được ghi vào bảng Công việc (Kanban) của phòng, tạo thẳng ở cột Xong (KHÔNG xếp hàng
     chờ, nếu không bộ điều phối sẽ chạy lại việc đã làm xong - tốn quota hai lần);
  2. một hồ sơ nằm ở `sources/viec-lam/` (code ghi, không tốn model);
  3. đủ 3 hồ sơ mới của một việc, hoặc nhân viên bấm "Ghi nhớ cách làm này", thì xếp MỘT việc nền
     chưng cất lên `wiki/quy-trinh/viec-mau/<slug>.md` bằng engine phụ (model nền, rẻ).
Không có vòng quét định kỳ: mọi bước chạy tại lúc làm việc (luật repo 2026-08-16).

Nguồn việc mẫu gồm hai lớp, lớp sau đè lớp trước theo slug:
  - `system/viec-mau/<tên brain>/<slug>.md`: bộ mẫu đi kèm app (by: seed), cập nhật theo bản phát hành;
  - `<brain>/viec-mau/<slug>.md`: việc chủ/nhân viên tự thêm hoặc sửa. Xoá một việc seed thì ghi
    một file `hidden: true` (không xoá được file của app).
Brain con dùng bộ mẫu của brain cha khi chưa có bộ riêng ("Ban Hang - Sales Makeup" -> "Ban Hang").

Phạm vi nhân viên đi qua `brain_root` của main.py: brain ngoài phòng bị ép về phòng chính, nên
chọn "Toàn khối" thì nhân viên chỉ nhận việc của phòng chính của họ.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_deps: dict = {}   # main.py inject: brain_root(brain) -> str, tasks() -> TasksFeature | None

SEED_DIR = Path(__file__).resolve().parent.parent / "system" / "viec-mau"
NGUONG_CHUNG_CAT = 3          # đủ chừng này hồ sơ mới của một việc thì tự xếp một việc chưng cất
TOI_DA_O = 5                  # số ô nhập tối đa của một việc
TOI_DA_VIEC = 60              # số việc mẫu tối đa mỗi brain
LOAI_O = ("text", "longtext", "select")
_RE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")
_RE_KHOA_O = re.compile(r"^[a-z][a-z0-9_]{0,20}$")
_RE_ROUTE = re.compile(r"^(auto|wf:[a-z0-9-]{1,60}|agent:[a-z0-9-]{1,60})$")
_RE_KEY = re.compile(r"^[A-Za-z0-9_-]{6,40}$")
_RE_HOSO = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)-([0-9a-f]{8})\.md$")


def register(app, brain_root_fn, tasks_fn):
    _deps.update(brain_root=brain_root_fn, tasks=tasks_fn)
    app.include_router(router)


def _err(msg: str, status: int = 400):
    return JSONResponse({"ok": False, "error": msg}, status_code=status)


# ---------------------------------------------------------------- tiện ích chữ
def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def tao_slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", _fold(title)).strip("-")
    return s[:60].strip("-")


def _mot_dong(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


# ---------------------------------------------------------------- đọc / ghi file
def tach(txt: str) -> tuple:
    """(frontmatter dict, thân). Frontmatter tối giản một dòng một khoá; giá trị chữ nằm trong
    ngoặc kép JSON (do `dump` viết) hoặc để trần (file viết tay)."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", txt or "", re.S)
    if not m:
        return {}, (txt or "").strip()
    meta: dict = {}
    for ln in m.group(1).splitlines():
        k, sep, v = ln.partition(":")
        if not sep:
            continue
        v = v.strip()
        if v[:1] == '"':
            try:
                v = json.loads(v)
            except ValueError:
                v = v.strip('"')
        meta[k.strip()] = v
    return meta, m.group(2).strip()


def dump(meta: dict, body: str) -> str:
    q = lambda v: json.dumps(_mot_dong(v), ensure_ascii=False)
    dong = [
        "---", "type: viec-mau",
        f"title: {q(meta.get('title'))}",
        f"group: {q(meta.get('group'))}",
        f"icon: {_mot_dong(meta.get('icon')) or 'message-circle'}",
        "inputs: " + json.dumps(meta.get("inputs") or [], ensure_ascii=False, separators=(",", ":")),
        f"route: {meta.get('route') or 'auto'}",
        f"sop: {q(meta.get('sop'))}",
        f"by: {q(meta.get('by'))}",
        f"order: {int(meta.get('order') or 0)}",
        f"hidden: {'true' if meta.get('hidden') else 'false'}",
        "---", "", str(body or "").strip(), "",
    ]
    return "\n".join(dong)


def _ghi_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def chuan_o(raw) -> list:
    """Ô nhập hợp lệ (tối đa TOI_DA_O), bỏ ô hỏng thay vì làm hỏng cả việc."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "[]")
        except ValueError:
            raw = []
    out, seen = [], set()
    for o in raw if isinstance(raw, list) else []:
        if not isinstance(o, dict):
            continue
        key = str(o.get("key") or "").strip()
        if not _RE_KHOA_O.match(key) or key in seen:
            continue
        loai = str(o.get("type") or "text")
        if loai not in LOAI_O:
            loai = "text"
        item = {"key": key, "label": _mot_dong(o.get("label") or key)[:40], "type": loai,
                "required": bool(o.get("required"))}
        if loai == "select":
            ops = [_mot_dong(x)[:40] for x in (o.get("options") or []) if _mot_dong(x)][:12]
            if not ops:
                item["type"] = "text"
            else:
                item["options"] = ops
        seen.add(key)
        out.append(item)
        if len(out) >= TOI_DA_O:
            break
    return out


def _item(slug: str, meta: dict, body: str, origin: str) -> dict:
    route = str(meta.get("route") or "auto")
    try:
        order = int(meta.get("order") or 0)
    except (TypeError, ValueError):
        order = 0
    return {
        "slug": slug,
        "title": _mot_dong(meta.get("title") or slug)[:80],
        "group": _mot_dong(meta.get("group") or "Khác")[:40] or "Khác",
        "icon": _mot_dong(meta.get("icon") or "message-circle")[:40],
        "inputs": chuan_o(meta.get("inputs")),
        "route": route if _RE_ROUTE.match(route) else "auto",
        "sop": _mot_dong(meta.get("sop"))[:200],
        "by": _mot_dong(meta.get("by") or origin)[:60],
        "order": order,
        "hidden": str(meta.get("hidden")).lower() == "true" or meta.get("hidden") is True,
        "prompt": body,
        "origin": origin,
    }


def _doc_thu_muc(d: Path, origin: str) -> list:
    out = []
    try:
        files = sorted(d.glob("*.md"))
    except OSError:
        return out
    for f in files:
        slug = f.stem
        if not _RE_SLUG.match(slug):
            continue
        try:
            meta, body = tach(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        out.append(_item(slug, meta, body, origin))
    return out


def thu_muc_seed(ten_brain: str) -> Path | None:
    """Bộ mẫu của brain; brain con ("A - B") rơi về bộ của brain cha ("A")."""
    for ten in (ten_brain, ten_brain.split(" - ")[0].strip()):
        d = SEED_DIR / ten
        if ten and d.is_dir():
            return d
    return None


def liet_ke(root: str, kem_an: bool = False) -> list:
    seed_dir = thu_muc_seed(Path(root).name)
    theo_slug = {i["slug"]: i for i in (_doc_thu_muc(seed_dir, "seed") if seed_dir else [])}
    for i in _doc_thu_muc(Path(root) / "viec-mau", "brain"):
        i["ghi_de_seed"] = i["slug"] in theo_slug
        theo_slug[i["slug"]] = i
    items = sorted(theo_slug.values(), key=lambda i: (i["order"], _fold(i["title"])))
    return items if kem_an else [i for i in items if not i["hidden"]]


def nhom(items: list) -> list:
    out: list = []
    for i in items:
        if i["group"] not in out:
            out.append(i["group"])
    return out


def luu(root: str, data: dict, who: str) -> dict:
    """Thêm hoặc sửa một việc. Raise ValueError(thông báo cho người dùng) nếu không hợp lệ."""
    title = _mot_dong(data.get("title"))[:80]
    prompt = str(data.get("prompt") or "").strip()
    if not title:
        raise ValueError("Thiếu tên việc")
    if not prompt:
        raise ValueError("Thiếu nội dung lệnh")
    if len(prompt) > 4000:
        raise ValueError("Nội dung lệnh quá dài (tối đa 4000 ký tự)")
    co = {i["slug"]: i for i in liet_ke(root, kem_an=True)}
    slug = str(data.get("slug") or "").strip()
    if slug:
        if not _RE_SLUG.match(slug):
            raise ValueError("Mã việc không hợp lệ")
    else:
        slug = tao_slug(title)
        if not slug:
            raise ValueError("Tên việc không có chữ để đặt mã")
        if slug in co or any(_fold(i["title"]) == _fold(title) for i in co.values()):
            raise ValueError("Đã có việc tên này")
    cu = co.get(slug)
    if not cu and len(co) >= TOI_DA_VIEC:
        raise ValueError(f"Mỗi phòng tối đa {TOI_DA_VIEC} việc mẫu")
    route = str(data.get("route") or "auto").strip()
    if not _RE_ROUTE.match(route):
        route = "auto"
    meta = {
        "title": title,
        "group": _mot_dong(data.get("group") or (cu or {}).get("group") or "Khác")[:40] or "Khác",
        "icon": _mot_dong(data.get("icon") or (cu or {}).get("icon") or "message-circle")[:40],
        "inputs": chuan_o(data.get("inputs")),
        "route": route,
        "sop": _mot_dong(data.get("sop") if "sop" in data else (cu or {}).get("sop"))[:200],
        "by": (cu["by"] if cu and cu["origin"] == "brain" else who)[:60],
        "order": int(data.get("order") if str(data.get("order") or "").lstrip("-").isdigit()
                     else (cu or {}).get("order", 100)),
        "hidden": str(data.get("hidden") or "").lower() in ("1", "true", "on"),
    }
    _ghi_file(Path(root) / "viec-mau" / f"{slug}.md", dump(meta, prompt))
    return _item(slug, meta, prompt, "brain")


def xoa(root: str, slug: str) -> bool:
    """Xoá file của brain; việc seed thì ghi file ẩn (không đụng được file của app)."""
    if not _RE_SLUG.match(slug or ""):
        raise ValueError("Mã việc không hợp lệ")
    f = Path(root) / "viec-mau" / f"{slug}.md"
    seed_dir = thu_muc_seed(Path(root).name)
    la_seed = bool(seed_dir and (seed_dir / f"{slug}.md").is_file())
    if not f.is_file() and not la_seed:
        return False
    if la_seed:
        cu = next((i for i in liet_ke(root, True) if i["slug"] == slug), None) or {}
        meta = {k: cu.get(k) for k in ("title", "group", "icon", "inputs", "route", "sop", "by", "order")}
        meta["hidden"] = True
        _ghi_file(f, dump(meta, cu.get("prompt") or "-"))
    else:
        f.unlink()
    return True


# ---------------------------------------------------------------- hồ sơ và chưng cất
def thu_muc_ho_so(root: str) -> Path:
    return Path(root) / "sources" / "viec-lam"


def _file_trang_thai(root: str) -> Path:
    return Path(root) / "Joyce" / "viec-mau-state.json"


def _doc_trang_thai(root: str) -> dict:
    try:
        d = json.loads(_file_trang_thai(root).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ds_ho_so(root: str, slug: str = "") -> list:
    """[(đường dẫn, ngày, slug)] của các hồ sơ, mới nhất trước."""
    out = []
    try:
        files = list(thu_muc_ho_so(root).glob("*.md"))
    except OSError:
        return out
    for f in files:
        m = _RE_HOSO.match(f.name)
        if m and (not slug or m.group(2) == slug):
            out.append((f, m.group(1), m.group(2)))
    out.sort(key=lambda x: x[0].name, reverse=True)
    return out


def ho_so_moi(root: str, slug: str) -> list:
    moc = float((_doc_trang_thai(root).get(slug) or {}).get("da") or 0)
    res = []
    for f, _, _ in ds_ho_so(root, slug):
        try:
            if f.stat().st_mtime > moc:
                res.append(f)
        except OSError:
            continue
    return res


def thong_ke(root: str) -> dict:
    """{slug: {tong, bay_ngay, moi}} cho mục quản lý. Đọc tên file, không mở nội dung."""
    homnay = datetime.now().date()
    kq: dict = {}
    for f, ngay, slug in ds_ho_so(root):
        s = kq.setdefault(slug, {"tong": 0, "bay_ngay": 0, "moi": 0})
        s["tong"] += 1
        try:
            if (homnay - datetime.strptime(ngay, "%Y-%m-%d").date()).days < 7:
                s["bay_ngay"] += 1
        except ValueError:
            pass
    for slug, s in kq.items():
        s["moi"] = len(ho_so_moi(root, slug))
    return kq


def ghi_ho_so(root: str, slug: str, title: str, values: dict, nhan: list, result: str,
              who: str, edited: bool, key: str) -> tuple:
    """Ghi hồ sơ một lần làm. Trả (đường dẫn, mới?) - cùng `key` thì không ghi lại."""
    ngay = datetime.now().strftime("%Y-%m-%d")
    k8 = re.sub(r"[^0-9a-f]", "", uuid.uuid5(uuid.NAMESPACE_URL, f"{slug}:{key}").hex)[:8]
    f = thu_muc_ho_so(root) / f"{ngay}-{slug}-{k8}.md"
    # Bấm đúp qua đêm: cùng key nhưng khác ngày vẫn là bản cũ.
    for p, _, s in ds_ho_so(root, slug):
        if p.name.endswith(f"-{k8}.md"):
            return p, False
    dau = [f"- {nhan_o}: {_mot_dong(values.get(k))[:300]}" for k, nhan_o in nhan if _mot_dong(values.get(k))]
    txt = "\n".join([
        "---", "type: viec-lam", f"viec_mau: {slug}", "title: " + json.dumps(_mot_dong(title), ensure_ascii=False),
        "by: " + json.dumps(_mot_dong(who), ensure_ascii=False),
        "at: " + datetime.now().isoformat(timespec="seconds"),
        f"edited: {'true' if edited else 'false'}", "---", "",
        f"# {_mot_dong(title)}", "", "## Đầu vào", *(dau or ["- (không có)"]), "",
        "## Kết quả cuối", "", (result or "").strip()[:8000] or "(không có nội dung)", "",
    ])
    _ghi_file(f, txt)
    return f, True


def y_dinh_chung_cat(item: dict | None, slug: str, title: str, files: list) -> str:
    ds = "\n".join(f"- `sources/viec-lam/{p.name}`" for p in files[:20])
    sop = f" So với SOP gốc `{item['sop']}`, ghi rõ chỗ thực tế khác đi." if item and item.get("sop") else ""
    return (
        f"Chưng cất cách làm thực tế của việc \"{title}\" vào wiki của brain này. Các hồ sơ mới "
        f"(người làm đã xác nhận xong):\n{ds}\n\n"
        "Làm đúng quy trình INGEST: nạp skill ingest-source qua joyce_use_skill, đọc các hồ sơ bằng "
        f"joyce_read_file, rồi viết hoặc CẬP NHẬT (không ghi đè mất nội dung cũ) trang "
        f"`wiki/quy-trinh/viec-mau/{slug}.md` gồm: các bước làm thực tế, biến thể hay gặp, lỗi hay "
        f"gặp, mẹo của người làm.{sop} Trang ngắn, có frontmatter type: wiki và liên kết [[...]] tới "
        "hồ sơ. Thêm trang vào wiki/index.md để tra cứu được và append wiki/log.md. Không dùng gạch "
        "dài. Trả kết quả ngắn: trang đã cập nhật và 3 ý chính."
    )


async def chung_cat(root: str, brain: str, slug: str, chat_id: str, tu_dong: bool) -> dict:
    t = _deps["tasks"]()
    if t is None:
        return {"ok": False, "error": "Hàng đợi việc chưa sẵn sàng"}
    files = ho_so_moi(root, slug)
    if not files:
        return {"ok": False, "error": "Chưa có hồ sơ mới để chưng cất"}
    item = next((i for i in liet_ke(root, True) if i["slug"] == slug), None)
    title = (item or {}).get("title") or slug
    tid = t.enqueue(brain, f"[Chưng cất] {title}", y_dinh_chung_cat(item, slug, title, files),
                    "auto", 1, None, False, "viec-mau", chat_id, "mcp-read", "auto",
                    idempotency_key=f"chungcat:{slug}:{int(time.time() // 60)}")
    chay = await t._claim_and_spawn(tid)
    mark = _doc_trang_thai(root)
    mark[slug] = {"da": time.time(), "task": tid, "tu_dong": bool(tu_dong), "so_ho_so": len(files)}
    _ghi_file(_file_trang_thai(root), json.dumps(mark, ensure_ascii=False, indent=1))
    return {"ok": True, "id": tid, "running": bool(chay), "ho_so": len(files)}


# ---------------------------------------------------------------- HTTP
def _nguoi_lam(request: Request) -> str:
    st = getattr(request.state, "staff", None) or {}
    return _mot_dong(st.get("ten")) or "Chủ"


def _root(brain: str) -> str:
    return _deps["brain_root"](brain)


@router.get("/viec-mau")
async def viec_mau_list(brain: str = Query("brain"), all: int = Query(0), stats: int = Query(0)):
    root = _root(brain)
    items = liet_ke(root, kem_an=bool(all))
    out = {"ok": True, "brain": Path(root).name, "items": items, "groups": nhom(items)}
    if stats:
        out["stats"] = thong_ke(root)
    return out


@router.post("/viec-mau")
async def viec_mau_save(request: Request, brain: str = Form("brain"), slug: str = Form(""),
                        title: str = Form(""), group: str = Form(""), prompt: str = Form(""),
                        icon: str = Form(""), inputs: str = Form("[]"), route: str = Form("auto"),
                        sop: str = Form(""), order: str = Form(""), hidden: str = Form("")):
    root = _root(brain)
    data = {"slug": slug, "title": title, "group": group, "prompt": prompt, "icon": icon,
            "inputs": inputs, "route": route, "hidden": hidden}
    if sop:
        data["sop"] = sop
    if order:
        data["order"] = order
    try:
        item = luu(root, data, _nguoi_lam(request))
    except ValueError as e:
        return _err(str(e))
    except OSError as e:
        return _err(f"Không ghi được file: {e}", 500)
    return {"ok": True, "item": item}


@router.post("/viec-mau/delete")
async def viec_mau_delete(brain: str = Form("brain"), slug: str = Form(...)):
    try:
        ok = xoa(_root(brain), slug)
    except ValueError as e:
        return _err(str(e))
    except OSError as e:
        return _err(f"Không xoá được: {e}", 500)
    return {"ok": ok} if ok else _err("Không có việc đó", 404)


@router.post("/viec-mau/xong")
async def viec_mau_xong(request: Request, brain: str = Form("brain"), slug: str = Form(...),
                        title: str = Form(""), values: str = Form("{}"), result: str = Form(""),
                        edited: str = Form(""), chat_id: str = Form(""), key: str = Form("")):
    """Nút "Đã xong": ghi hồ sơ + tạo việc ở cột Xong + (đủ ngưỡng) chưng cất."""
    if not _RE_SLUG.match(slug or ""):
        return _err("Mã việc không hợp lệ")
    t = _deps["tasks"]()
    if t is None:
        return _err("Hàng đợi việc chưa sẵn sàng", 503)
    if not _RE_KEY.match(key or ""):
        key = uuid.uuid4().hex[:16]
    root = _root(brain)
    who = _nguoi_lam(request)
    try:
        vals = json.loads(values or "{}")
        vals = vals if isinstance(vals, dict) else {}
    except ValueError:
        vals = {}
    item = next((i for i in liet_ke(root, True) if i["slug"] == slug), None)
    ten = _mot_dong(title) or (item or {}).get("title") or slug
    nhan = [(o["key"], o["label"]) for o in (item or {}).get("inputs", [])]
    try:
        f, moi = ghi_ho_so(root, slug, ten, vals, nhan, result, who,
                           str(edited).lower() in ("1", "true", "on"), key)
    except OSError as e:
        return _err(f"Không ghi được hồ sơ: {e}", 500)
    chinh = next((_mot_dong(vals.get(k)) for k, _ in nhan if _mot_dong(vals.get(k))), "")
    tieu_de = f"{ten}: {chinh}"[:160] if chinh else ten
    tid = t.ghi_viec_xong(brain, tieu_de, result or tieu_de, chat_id, f"viecmau:{slug}:{key}", who,
                          {"viec_mau": slug, "ho_so": f"sources/viec-lam/{f.name}"})
    out = {"ok": True, "id": tid, "duplicate": not moi, "ho_so": f"sources/viec-lam/{f.name}"}
    moi_n = len(ho_so_moi(root, slug))
    out["ho_so_moi"] = moi_n
    if moi and moi_n >= NGUONG_CHUNG_CAT:
        try:
            out["chung_cat"] = await chung_cat(root, brain, slug, chat_id, tu_dong=True)
        except Exception as e:   # chưng cất hỏng không được làm mất việc đã ghi xong
            out["chung_cat"] = {"ok": False, "error": str(e)[:200]}
    return out


@router.post("/viec-mau/ghi-nho")
async def viec_mau_ghi_nho(brain: str = Form("brain"), slug: str = Form(...), chat_id: str = Form("")):
    """Nút "Ghi nhớ cách làm này": chưng cất NGAY, không chờ đủ ngưỡng."""
    if not _RE_SLUG.match(slug or ""):
        return _err("Mã việc không hợp lệ")
    r = await chung_cat(_root(brain), brain, slug, chat_id, tu_dong=False)
    return r if r.get("ok") else _err(r.get("error") or "Không chưng cất được", 409)
