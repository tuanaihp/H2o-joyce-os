"""Plugin bundled: đồng bộ Apple Notes -> brain của Joyce qua Shortcut (iPhone/Mac).

Vì sao plugin này tồn tại
=========================
Apple không mở API cho Notes, nên máy PC không kéo ghi chú về được - chỉ thiết bị Apple đọc
được, qua app Shortcuts. Chiều duy nhất đúng là ĐẨY: một Shortcut trên iPhone/Mac chọn thư
mục, đóng gói JSON rồi POST thẳng lên Joyce. Trước plugin này không có điểm đổ bộ nào:
`/upload` đòi phiên dashboard và chỉ stage file, còn model thì không chạm được ghi chú trên
điện thoại chủ.

Đường đi của một ghi chú
========================
    Shortcut (Find Notes -> JSON) --POST--> /ext/apple-notes/push
        -> ghi <brain>/sources/apple-notes/<thư mục>/<tên note>.md
    -> ingest-source chưng cất lên wiki như mọi source khác.

Đường HTTP (đăng ký ở register)
===============================
- `GET  /ext/apple-notes/`          trang cài đặt - PHIÊN dashboard (xem token, chọn brain)
- `POST /ext/apple-notes/cai-dat`   lưu brain đích / cấp lại token - PHIÊN dashboard
- `GET  /ext/apple-notes/ping`      công khai, điện thoại gọi thử kết nối (kèm token)
- `POST /ext/apple-notes/push`      công khai, nhận gói notes JSON (kèm token)
- `POST /ext/apple-notes/folders`   công khai, nhận CÂY THƯ MỤC (nền cho bước chọn thư mục
                                    trong app - lưu lại để trang cài đặt hiển thị)

An toàn
=======
- Hai đường public (`push`, `folders`, `ping`) tự xác thực bằng token sinh ngẫu nhiên, so
  bằng compare_digest; token nằm trong STATE_DIR/plugin-data/apple-notes/config.json, chỉ
  hiện trên trang cài đặt đã đăng nhập. Lộ token = lộ quyền GHI note vào brain (không đọc
  được gì), nên nút "cấp lại" chỉ là một cú bấm.
- Ghi có giới hạn: nghiễm nhiên chỉ trong sources/apple-notes/ của MỘT brain trong
  BRAINS_DIR, tên thư mục/tên note đều qua _sach_ten (cắt `/`, `\\`, `..`), tổng payload
  chặn trần. Note xoá trên điện thoại KHÔNG xoá file trong brain (sources là source of
  truth - giữ lại đúng hợp đồng của lớp nguồn).
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from plugins_host import PROJECT_ROOT

# Trần bảo vệ đường public: ghi chú là văn bản, ai cố đẩy lớn hơn là sai quy trình chứ không
# phải nhu cầu thật.
_MAX_BODY = 20 * 1024 * 1024          # toàn bộ payload push
_MAX_NOTE_BODY = 1024 * 1024          # thân một note
_MAX_NOTES = 2000                     # số note trong một lần push
_MAX_FOLDERS = 500

_TEN_SACH = re.compile(r"[^\w\-. ()À-ỹ]", re.UNICODE)
_SOURCES_RE = r"^(\d+\s*[-_.]\s*)?sources$"


# ---------------------------------------------------------------- cấu hình & trạng thái
def _tep(ctx, ten: str) -> Path:
    return ctx.data_dir / ten


def _doc_json(p: Path, mac_dinh):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, type(mac_dinh)) else mac_dinh
    except Exception:
        return mac_dinh


def _ghi_json(p: Path, data) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception:
        pass


def _cfg(ctx) -> dict:
    """Cấu hình plugin: {token, brain}. Token sinh MỘT LẦN rồi nằm lại - Shortcut giữ bản
    đó, đổi token là phải sửa shortcut nên không tự xoay."""
    cfg = _doc_json(_tep(ctx, "config.json"), {})
    doi = False
    if not cfg.get("token"):
        cfg["token"] = "japn_" + secrets.token_urlsafe(24)
        doi = True
    if not cfg.get("brain"):
        cfg["brain"] = "Brain Default"
        doi = True
    if doi:
        _ghi_json(_tep(ctx, "config.json"), cfg)
    return cfg


def _ghi_cfg(ctx, cfg: dict) -> None:
    _ghi_json(_tep(ctx, "config.json"), cfg)


def _brains_dir() -> Path:
    # Giống BRAINS_DIR của main.py - plugin không import main (main nạp plugin, vòng tròn).
    return Path(os.getenv("BRAINS_DIR", str(PROJECT_ROOT / "brains")))


def _brain_dir(ten: str):
    """TÊN brain -> thư mục, chỉ trong BRAINS_DIR. None nếu tên lạ (không fallback âm thầm:
    ghi nhầm brain còn tệ hơn báo lỗi)."""
    ten = str(ten or "").strip()
    if not ten:
        return None
    try:
        base = _brains_dir().resolve()
        p = (base / ten).resolve()
        if p.is_dir() and base in p.parents:
            return p
    except Exception:
        pass
    return None


def _ds_brain() -> list:
    try:
        return sorted(d.name for d in _brains_dir().iterdir()
                      if d.is_dir() and not d.name.startswith("."))
    except Exception:
        return []


def _thu_muc_nguon(root: Path) -> Path:
    """sources/ của brain (linh hoạt '06 - Sources'), không thì tạo 'sources'."""
    try:
        for n in os.listdir(root):
            f = root / n
            if f.is_dir() and re.match(_SOURCES_RE, n.strip(), re.IGNORECASE):
                return f
    except Exception:
        pass
    d = root / "sources"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- helpers ghi file
def _sach_ten(ten: str, mac_dinh: str = "khong-ten") -> str:
    """Tên file/thư mục an toàn: cùng khuôn _sanitize_filename của lõi + cắt dấu tách đường
    dẫn và '..' để payload không leo ra ngoài sources/apple-notes/."""
    t = re.sub(r"[/\\]+", " ", str(ten or ""))
    t = _TEN_SACH.sub("_", t).strip().strip(".")
    if not t or t in (".", ".."):
        return mac_dinh
    return t[:120]


def _duong_thu_muc(thu_muc: str) -> str:
    """'Work/Dự án/A' -> 'Work/Dự án/A' sạch từng đoạn, bỏ đoạn rỗng. Rỗng -> '_goc'."""
    doan = [_sach_ten(p, "") for p in re.split(r"[/\\]+", str(thu_muc or ""))]
    doan = [p for p in doan if p][:6]
    return "/".join(doan) if doan else "_goc"


def _iso(v) -> str:
    """Chuỗi thời gian Apple gửi (ISO hoặc epoch) -> ISO string; rỗng -> ''."""
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
        except Exception:
            return ""
    return str(v)[:40]


def _id_note(note: dict, thu_muc: str, tieu_de: str) -> str:
    raw = str(note.get("id") or note.get("uuid") or "").strip()
    if raw:
        return raw[:120]
    # Không có id từ Shortcut: suy ra từ folder+title để push lại vẫn khớp cùng file.
    return hashlib.sha256(f"{thu_muc}\x00{tieu_de}".encode("utf-8")).hexdigest()[:16]


def _xac_thuc(request, ctx) -> bool:
    tok = _cfg(ctx).get("token") or ""
    if not tok:
        return False
    raw = str(request.headers.get("authorization") or "")
    dua = raw[7:].strip() if raw[:7].lower() == "bearer " else ""
    if not dua:
        dua = str(request.query_params.get("token") or "")
    return bool(dua) and hmac.compare_digest(dua, tok)


# ---------------------------------------------------------------- HTTP: trang cài đặt
def _trang_cai_dat(request, ctx):
    cfg = _cfg(ctx)
    last = _doc_json(_tep(ctx, "last_sync.json"), {})
    cay = _doc_json(_tep(ctx, "folders.json"), {})
    esc = html.escape
    ds = _ds_brain()
    datalist = "".join(f'<option value="{esc(b)}">' for b in ds)
    brain_hien_tai = cfg.get("brain") or "Brain Default"
    brain_ok = _brain_dir(brain_hien_tai) is not None

    dong_cay = ""
    for f in (cay.get("folders") or [])[:80]:
        dong_cay += f"<li>{esc(str(f))}</li>"
    if not dong_cay:
        dong_cay = "<li><i>Chưa có - chạy shortcut 'gửi cây thư mục' trên iPhone/Mac.</i></li>"

    last_html = "<i>Chưa đồng bộ lần nào.</i>"
    if last.get("at"):
        last_html = (f"{esc(last.get('at',''))} - thiết bị <b>{esc(last.get('device') or '?')}</b>, "
                     f"ghi {last.get('written', 0)} note mới/cập nhật, "
                     f"bỏ qua {last.get('skipped', 0)} note chưa đổi, "
                     f"brain <b>{esc(last.get('brain') or '?')}</b>.")

    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Apple Notes Sync</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:640px;margin:24px auto;padding:0 16px;color:#222}}
code,pre{{background:#f2f2f4;padding:2px 6px;border-radius:6px}}
pre{{padding:10px;overflow-x:auto}}
.tok{{word-break:break-all;font-family:ui-monospace,monospace}}
input,button{{font-size:14px;padding:6px 10px;margin:4px 0}}
.card{{border:1px solid #ddd;border-radius:10px;padding:14px 16px;margin:14px 0}}
</style>
<h2>Đồng bộ Apple Notes</h2>

<div class="card">
<b>1. Endpoint để Shortcut gọi:</b>
<pre>POST &lt;địa-chỉ-Joyce&gt;/ext/apple-notes/push</pre>
Ví dụ: <code>https://joyce-cua-anh.example.com/ext/apple-notes/push</code><br>
(Kiểm thử: <code>GET /ext/apple-notes/ping?token=TOKEN</code>)<br>
Trên MacBook: <a href="/ext/apple-notes/script"><b>⬇ Tải script cho MacBook</b></a>
(file .command đã điền sẵn URL tunnel + token hiện tại) — về Downloads chạy
<code>bash ~/Downloads/apple-notes-sync.command</code>, hiện hộp chọn thư mục của macOS.
Trên iPhone: dựng theo hướng dẫn Shortcuts.
</div>

<div class="card">
<b>2. Token (dán vào header <code>Authorization: Bearer ...</code> của shortcut):</b>
<p class="tok"><code>{esc(cfg.get("token",""))}</code></p>
<form method="post" action="/ext/apple-notes/cai-dat" style="display:inline">
<input type="hidden" name="op" value="regen"><button>↺ Cấp lại token</button>
</form>
</div>

<div class="card">
<b>3. Brain đích</b> {'✅' if brain_ok else '⚠️ TÊN NÀY KHÔNG CÓ TRONG brains/'}
<form method="post" action="/ext/apple-notes/cai-dat">
<input type="hidden" name="op" value="brain">
<input name="brain" list="brains" value="{esc(brain_hien_tai)}" size="34">
<datalist id="brains">{datalist}</datalist>
<button>Lưu</button>
</form>
Notes sẽ vào <code>&lt;brain&gt;/sources/apple-notes/&lt;thư mục&gt;/</code>
</div>

<div class="card">
<b>4. Lệnh chạy trên MacBook</b> (mở Terminal: <code>Cmd + Space</code> → gõ <code>terminal</code> → Enter, rồi dán lệnh):
<br><br>
<b>Đồng bộ:</b>
<pre>bash ~/Downloads/apple-notes-sync.command</pre>
<b>Lần sau chạy lại:</b> trong Terminal bấm phím <code>↑</code> (mũi tên lên) rồi Enter - hiện lại lệnh vừa chạy, khỏi gõ.<br><br>
<b>Tải bị trùng tên (file -1, -2):</b>
<pre>ls ~/Downloads/apple-notes-sync*</pre>
rồi chạy bản mới nhất, ví dụ <code>bash ~/Downloads/apple-notes-sync-1.command</code><br><br>
<b>Dọn bản cũ rồi tải lại ở mục 1:</b>
<pre>rm -f ~/Desktop/apple-notes-sync.command ~/Downloads/apple-notes-sync*.command</pre>
</div>

<div class="card"><b>Lần đồng bộ cuối:</b><br>{last_html}</div>
<div class="card"><b>Cây thư mục điện thoại đã gửi ({esc(str(cay.get('at') or '—'))}):</b>
<ul>{dong_cay}</ul></div>"""


def _tai_script(request, ctx):
    """Tải tools/apple-notes-sync.command với JOYCE_URL + TOKEN đã điền sẵn - anh chỉ
    việc tải về MacBook và chạy, khỏi sửa tay. Đường này đòi phiên dashboard (không
    public), nên token lộ ra được an toàn."""
    cfg = _cfg(ctx)
    p = PROJECT_ROOT / "tools" / "apple-notes-sync.command"
    try:
        src = p.read_text(encoding="utf-8")
    except OSError:
        return {"ok": False, "error": f"không đọc được {p}"}
    link = ""
    try:
        link = str(json.loads((PROJECT_ROOT / "tools" / "tunnel-last.json")
                              .read_text(encoding="utf-8")).get("link") or "")
    except Exception:
        pass
    src = re.sub(r'^JOYCE_URL="[^"]*"', f'JOYCE_URL="{link}"', src, count=1, flags=re.M)
    src = re.sub(r'^TOKEN="[^"]*"', f'TOKEN="{cfg.get("token", "")}"', src, count=1, flags=re.M)
    from starlette.responses import Response
    return Response(src.encode("utf-8"), media_type="application/octet-stream",
                    headers={"Content-Disposition": 'attachment; filename="apple-notes-sync.command"'})


async def _luu_cai_dat(request, ctx):
    form = await request.form()
    cfg = _cfg(ctx)
    op = str(form.get("op") or "")
    if op == "regen":
        cfg["token"] = "japn_" + secrets.token_urlsafe(24)
    elif op == "brain":
        ten = str(form.get("brain") or "").strip()
        if not _brain_dir(ten):
            return {"ok": False, "error": f"Không có brain tên '{ten}' trong BRAINS_DIR"}
        cfg["brain"] = ten
    _ghi_cfg(ctx, cfg)
    # Về lại trang cài đặt (303 để trình duyệt GET lại, không resubmit form).
    from starlette.responses import RedirectResponse
    return RedirectResponse("/ext/apple-notes/", status_code=303)


# ---------------------------------------------------------------- HTTP: đường public
def _ping(request, ctx):
    if not _xac_thuc(request, ctx):
        return _tu_choi()
    cfg = _cfg(ctx)
    return {"ok": True, "plugin": "apple-notes", "brain": cfg.get("brain")}


def _tu_choi():
    from starlette.responses import JSONResponse
    return JSONResponse({"ok": False, "error": "token sai hoặc thiếu"}, status_code=401)


async def _nhan_cay_thu_muc(request, ctx):
    """Cách A chưa dùng đến, nhưng shortcut có thể gửi cây thư mục trước để trang cài đặt
    hiển thị (và là nền của bước 'tick thư mục trong app' sau này)."""
    if not _xac_thuc(request, ctx):
        return _tu_choi()
    try:
        data = await request.json()
    except Exception:
        return _tu_choi_json("body không phải JSON")
    folders = data.get("folders") if isinstance(data, dict) else data
    if not isinstance(folders, list):
        return _tu_choi_json("thiếu folders: [...]")
    folders = [str(f)[:300] for f in folders[:_MAX_FOLDERS]]
    _ghi_json(_tep(ctx, "folders.json"), {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "device": str((data or {}).get("device") or "")[:60] if isinstance(data, dict) else "",
        "folders": folders})
    return {"ok": True, "folders": len(folders)}


def _tu_choi_json(loi: str):
    from starlette.responses import JSONResponse
    return JSONResponse({"ok": False, "error": loi}, status_code=400)


async def _nhan_push(request, ctx):
    if not _xac_thuc(request, ctx):
        return _tu_choi()
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > _MAX_BODY:
        return _tu_choi_json("payload quá lớn")
    raw = await request.body()
    if len(raw) > _MAX_BODY:
        return _tu_choi_json("payload quá lớn")
    try:
        data = json.loads(raw)
    except Exception:
        return _tu_choi_json("body không phải JSON")
    if not isinstance(data, dict):
        return _tu_choi_json("body phải là JSON object")

    cfg = _cfg(ctx)
    ten_brain = str(data.get("brain") or cfg.get("brain") or "Brain Default")
    root = _brain_dir(ten_brain)
    if root is None:
        return _tu_choi_json(f"Không có brain tên '{ten_brain}'")

    # Hai dạng payload:
    #   {"folders": {"Work": [note,...], "Work/Sub": [...]}}   (shortcut mặc định)
    #   {"folder": "Work", "notes": [note,...]}                (đẩy từng thư mục một)
    cap_nhat = {}
    folders = data.get("folders")
    if isinstance(folders, dict):
        for ten_thu, ds in folders.items():
            if isinstance(ds, list):
                cap_nhat.setdefault(str(ten_thu), []).extend(ds)
    elif isinstance(data.get("notes"), list):
        cap_nhat[str(data.get("folder") or "")] = list(data["notes"])
    if not cap_nhat:
        return _tu_choi_json("thiếu 'folders' (object thư-mục -> [notes]) hoặc 'folder'+'notes'")

    seen = _doc_json(_tep(ctx, "seen.json"), {})
    thu_goc = _thu_muc_nguon(root) / "apple-notes"
    ghi, bo_qua, loi = 0, 0, []
    da_dem = 0

    for ten_thu, ds in cap_nhat.items():
        rel_thu = _duong_thu_muc(ten_thu)
        try:
            (thu_goc / rel_thu).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            loi.append(f"{rel_thu}: không tạo được thư mục ({e})")
            continue
        for note in ds:
            if da_dem >= _MAX_NOTES:
                break
            da_dem += 1
            if not isinstance(note, dict):
                continue
            try:
                kq = _ghi_mot_note(thu_goc, rel_thu, note, seen)
            except Exception as e:
                loi.append(f"{rel_thu}: {type(e).__name__}: {e}")
                continue
            if kq == "skip":
                bo_qua += 1
            else:
                ghi += 1

    _ghi_json(_tep(ctx, "seen.json"), seen)
    _ghi_json(_tep(ctx, "last_sync.json"), {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "device": str(data.get("device") or "")[:60],
        "brain": ten_brain, "written": ghi, "skipped": bo_qua,
        "errors": len(loi)})
    out = {"ok": True, "written": ghi, "skipped": bo_qua, "brain": ten_brain,
           "folder": str(thu_goc.relative_to(root))}
    if loi:
        out["errors"] = loi[:10]
    return out


def _ghi_mot_note(thu_goc: Path, rel_thu: str, note: dict, seen: dict) -> str:
    """Ghi 1 note -> sources/apple-notes/<folder>/<tên>.md. Trả 'skip' nếu chưa đổi."""
    tieu_de = str(note.get("title") or note.get("name") or "").strip() or "Không tên"
    body = str(note.get("body") or note.get("text") or "")
    if len(body) > _MAX_NOTE_BODY:
        body = body[:_MAX_NOTE_BODY] + "\n\n[...cắt bớt, note quá dài]"
    nid = _id_note(note, rel_thu, tieu_de)
    modified = _iso(note.get("modified") or note.get("modification_date"))
    created = _iso(note.get("created") or note.get("creation_date"))

    ten_file = _sach_ten(tieu_de) + ".md"
    rel_moi = f"{rel_thu}/{ten_file}"
    cu = seen.get(nid) or {}
    rel_cu = str(cu.get("path") or "")

    # Đụng độ tên file: một id KHÁC đã giữ path này -> thêm đuôi hash cho tách.
    for oid, o in seen.items():
        if oid != nid and o.get("path") == rel_moi:
            rel_moi = f"{rel_thu}/{_sach_ten(tieu_de)}-{nid[:6]}.md"
            break

    f_moi = thu_goc / rel_moi
    if (cu.get("modified") == modified and rel_cu == rel_moi and f_moi.is_file()):
        return "skip"

    fm = ["---", "type: source", "source_kind: own-note", "status: unprocessed",
          f"created: {created or datetime.now().date().isoformat()}",
          f"synced_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
          f'apple_id: "{nid}"',
          f'apple_folder: "{rel_thu}"']
    if modified:
        fm.append(f"apple_modified: {modified}")
    fm += ["---", "", f"# {tieu_de}", "", body.rstrip(), ""]
    f_moi.parent.mkdir(parents=True, exist_ok=True)
    f_moi.write_text("\n".join(fm), encoding="utf-8")

    # Note đổi tên/thư mục: dọn file ở đường cũ (chỉ file do mình ghi).
    if rel_cu and rel_cu != rel_moi:
        f_cu = thu_goc / rel_cu
        try:
            if f_cu.is_file():
                f_cu.unlink()
        except OSError:
            pass
    seen[nid] = {"path": rel_moi, "modified": modified}
    return "write"


# ---------------------------------------------------------------- tool cho engine
def _trang_thai(args, ctx) -> str:
    cfg = _cfg(ctx)
    last = _doc_json(_tep(ctx, "last_sync.json"), {})
    cay = _doc_json(_tep(ctx, "folders.json"), {})
    seen = _doc_json(_tep(ctx, "seen.json"), {})
    d = [f"Đồng bộ Apple Notes -> brain '{cfg.get('brain')}' "
         f"(sources/apple-notes/, hiện giữ {len(seen)} note đã biết)."]
    if last.get("at"):
        d.append(f"Lần đồng bộ cuối: {last['at']} từ '{last.get('device') or '?'}' - "
                 f"ghi {last.get('written', 0)}, bỏ qua {last.get('skipped', 0)}"
                 + (f", lỗi {last.get('errors', 0)}" if last.get('errors') else ""))
    else:
        d.append("Chưa đồng bộ lần nào. Trang cài đặt: /ext/apple-notes/ (lấy token cho "
                 "shortcut ở đó).")
    if cay.get("folders"):
        d.append(f"Cây thư mục điện thoại gửi ({cay.get('at','?')}): "
                 + ", ".join(str(f) for f in cay["folders"][:30])
                 + (" ..." if len(cay["folders"]) > 30 else ""))
    return "\n".join(d)


# ---------------------------------------------------------------- đăng ký
def register(ctx):
    _cfg(ctx)   # sinh token ngay lần nạp đầu - trang cài đặt và test đọc được ngay
    ctx.register_http("", _trang_cai_dat)                                   # trang cài đặt
    ctx.register_http("cai-dat", _luu_cai_dat, methods=("POST",))           # lưu cấu hình
    ctx.register_http("script", _tai_script)                                # tải script Mac đã điền sẵn
    ctx.register_http("ping", _ping, public=True, no_cookie=True)           # test từ phone
    ctx.register_http("push", _nhan_push, methods=("POST",),
                      public=True, no_cookie=True)                          # Shortcut -> notes
    ctx.register_http("folders", _nhan_cay_thu_muc, methods=("POST",),
                      public=True, no_cookie=True)                          # Shortcut -> cây thư mục
    ctx.register_tool(
        "apple_notes_status",
        "Báo tình trạng đồng bộ Apple Notes: brain đích, lần đồng bộ cuối, số note đã ghi "
        "vào sources/apple-notes/, cây thư mục điện thoại đã gửi. Dùng khi người dùng hỏi "
        "apple notes đang đồng bộ thư mục nào / đồng bộ chưa / note đi vào đâu.",
        _trang_thai,
        schema={"type": "object", "properties": {}},
        min_mode="readonly",
        emoji="🍎",
    )
