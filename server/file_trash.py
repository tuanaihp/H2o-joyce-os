"""Thùng rác cho MỌI thao tác xoá file/thư mục trong brain (chủ yêu cầu 2026-10-09).

Vì sao có: `/files/delete` trước đây gọi thẳng `shutil.rmtree`/`unlink`, xoá là mất hẳn -
`brains/` không nằm trong git nên không có đường hoàn tác nào. Brain bị xoá thì đã có thùng
rác riêng (`git_brain.move_to_trash`, giữ 30 ngày); file và thư mục BÊN TRONG brain thì chưa.

Mô hình: mỗi lần xoá là một MỤC trong `<STATE_DIR>/file-trash/<id>/`:
- `payload/<tên gốc>` - chính file hoặc thư mục đã xoá, giữ nguyên tên để phục hồi đúng
- `meta.json`        - brain, đường dẫn tương đối, kiểu, thời điểm xoá, dung lượng

Giữ nguyên tên trong `payload/` thay vì đổi tên theo id: phục hồi chỉ là move ngược lại, và
người dùng mở thẳng thư mục thùng rác vẫn đọc được tên file như cũ.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path

import config as cfgmod

GIU_NGAY = 30          # quá hạn này thì dọn hẳn, bằng với thùng rác brain
_TEN_META = "meta.json"
_TEN_PAYLOAD = "payload"


def goc() -> Path:
    return Path(cfgmod.STATE_DIR) / "file-trash"


def _dung_luong(p: Path) -> int:
    if p.is_file():
        try:
            return p.stat().st_size
        except OSError:
            return 0
    n = 0
    for dp, dns, fns in os.walk(p):
        dns[:] = [x for x in dns if x != ".git"]
        for f in fns:
            try:
                n += (Path(dp) / f).stat().st_size
            except OSError:
                pass
    return n


def _doc_meta(d: Path):
    try:
        m = json.loads((d / _TEN_META).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(m, dict):
        return None
    m["id"] = d.name
    return m


def _payload(d: Path):
    """File/thư mục thật bên trong một mục thùng rác (đúng một cái)."""
    pd = d / _TEN_PAYLOAD
    if not pd.is_dir():
        return None
    for x in pd.iterdir():
        return x
    return None


def bo_vao(abs_path, brain: str = "", rel: str = "") -> dict:
    """Chuyển file/thư mục vào thùng rác. Trả bản ghi mục đã tạo.

    `shutil.move` xử lý được cả khác ổ đĩa. Retry 3 lần vì Windows hay kẹt handle khi một
    engine còn đang mở file trong brain - y như `git_brain.move_to_trash`."""
    src = Path(abs_path)
    if not src.exists():
        raise FileNotFoundError(str(src))
    la_thu_muc = src.is_dir()
    co = _dung_luong(src)
    mid = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    d = goc() / mid
    (d / _TEN_PAYLOAD).mkdir(parents=True, exist_ok=True)
    dich = d / _TEN_PAYLOAD / src.name
    loi = None
    for _ in range(3):
        try:
            shutil.move(str(src), str(dich))
            loi = None
            break
        except Exception as e:
            loi = e
            time.sleep(0.3)
    if loi:
        shutil.rmtree(str(d), ignore_errors=True)
        raise loi
    meta = {"brain": brain, "rel": str(rel or "").replace("\\", "/"), "ten": src.name,
            "la_thu_muc": la_thu_muc, "xoa_luc": time.time(), "co": co,
            "duong_dan_cu": str(src)}
    (d / _TEN_META).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    meta["id"] = mid
    return meta


def danh_sach(brain: str = "") -> list:
    """Các mục trong thùng rác, mới nhất trước. `brain` rỗng = mọi brain."""
    g = goc()
    if not g.is_dir():
        return []
    out = []
    for d in g.iterdir():
        if not d.is_dir():
            continue
        m = _doc_meta(d)
        if not m:
            continue
        if brain and str(m.get("brain") or "") != brain:
            continue
        p = _payload(d)
        m["con_file"] = p is not None
        out.append(m)
    out.sort(key=lambda x: x.get("xoa_luc") or 0, reverse=True)
    return out


def lay(mid: str):
    """(meta, đường dẫn payload) của một mục, hoặc (None, None)."""
    d = goc() / str(mid or "")
    if not d.is_dir() or d.parent != goc():      # chặn id kiểu '../..'
        return None, None
    m = _doc_meta(d)
    if not m:
        return None, None
    return m, _payload(d)


def phuc_hoi(mid: str, dich) -> str:
    """Chuyển mục khỏi thùng rác về `dich` (đường dẫn TUYỆT ĐỐI do chỗ gọi tính và đã kiểm
    tra nằm trong brain). Trùng tên thì thêm hậu tố, không ghi đè thứ đang có."""
    m, p = lay(mid)
    if not m or not p:
        raise FileNotFoundError("Mục không còn trong thùng rác")
    dst = Path(dich)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        than, duoi = (dst.stem, dst.suffix) if dst.is_file() or dst.suffix else (dst.name, "")
        i = 1
        while dst.exists():
            dst = dst.parent / f"{than} (phuc hoi {i}){duoi}"
            i += 1
    shutil.move(str(p), str(dst))
    shutil.rmtree(str(goc() / mid), ignore_errors=True)
    return str(dst)


def xoa_han(mid: str) -> bool:
    d = goc() / str(mid or "")
    if not d.is_dir() or d.parent != goc():
        return False
    shutil.rmtree(str(d), ignore_errors=True)
    return True


def don(days: int = GIU_NGAY) -> int:
    """Dọn các mục quá hạn. Trả số mục đã dọn."""
    g = goc()
    if not g.is_dir():
        return 0
    moc = time.time() - days * 86400
    n = 0
    for d in g.iterdir():
        if not d.is_dir():
            continue
        m = _doc_meta(d)
        if m and (m.get("xoa_luc") or 0) < moc:
            shutil.rmtree(str(d), ignore_errors=True)
            n += 1
    return n
