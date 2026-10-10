"""Trang Nghiên cứu: sáu khu đọc từ brain phòng Nghiên cứu concept. CHỈ ĐỌC.

Thiết kế: docs/dev/2026-10-process-factory-design.md. Kế hoạch: docs/dev/2026-10-11-process-factory-plan.md.

Trạng thái ý tưởng lấy từ frontmatter `giai_doan` và `loai` (skill h2o-y-tuong ghi khi chạy ý tưởng).
Trang thiếu `giai_doan` thì suy ra từ `status` cũ (draft, active, archived) để không mất trang đã có.
Mọi lỗi đọc file chỉ làm bỏ qua file đó, không làm trắng cả trang.
"""
import datetime as _dt
import re
from pathlib import Path

from skill_router import split_frontmatter

PILOT_BRAIN = "Nghien Cuu - Concept Hinh Anh"

GIAI_DOAN = ("moi", "phan-tich", "ban-nhap", "ra-soat", "cho-duyet", "pilot", "hoat-dong", "gac")
# Các cột của pipeline, theo thứ tự đi từ ý tưởng đến hoạt động. `gac` không hiện ở pipeline.
PIPELINE = ("moi", "phan-tich", "ban-nhap", "ra-soat", "cho-duyet", "pilot", "hoat-dong")
LOAI = ("concept", "quy-trinh-moi", "sua-quy-trinh")
_STATUS_CU = {"draft": "moi", "active": "hoat-dong", "archived": "gac"}
_CONCEPT_THU_VIEN = ("pilot", "hoat-dong", "gac")
_CR_DONG = ("hoat-dong", "gac")

MAX_BYTES = 200_000       # trần đọc mỗi file, tránh một file khổng lồ làm chậm trang
MUC_RADAR = 5
MUC_NHAT_KY = 30

_LOG_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] ([^|]+)\|\s*(.+?)\s*$")
_TIEU_DE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)


def _khoi_theo_dong(text: str) -> dict:
    """Dự phòng khi YAML lỗi: đọc từng dòng `khoa: giá trị`, tách ở dấu hai chấm ĐẦU TIÊN.

    Skill ghi frontmatter bằng LLM nên một giá trị chứa `: ` không có ngoặc kép rất hay gặp.
    Thay vì mất cả khối (và cùng lúc mất giai_doan, loai), chỉ dòng đó bị đọc theo cách đơn giản.
    """
    meta = {}
    if not text.startswith("---"):
        return meta
    khoi = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    for dong in khoi.splitlines():
        if not dong or dong[0] in " \t-" or ":" not in dong:
            continue
        khoa, gia_tri = dong.split(":", 1)
        meta[khoa.strip()] = gia_tri.strip().strip("\"'")
    return meta


def _doc(path: Path):
    """(meta, body) của một file md, hoặc None nếu không đọc được."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            text = f.read(MAX_BYTES)
    except OSError:
        return None
    meta, body = split_frontmatter(text)
    if not meta:
        meta = _khoi_theo_dong(text)
    return meta or {}, body or ""


def _file_md(folder: Path):
    """Các file .md trong thư mục, bỏ file gạch dưới (_open-questions.md, _session-handoff.md)."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.md") if p.is_file() and not p.name.startswith("_"))


def _chuoi(meta: dict, khoa: str) -> str:
    # YAML tự đổi `2026-10-11` thành date, nên mọi giá trị đều ép về chuỗi.
    return str(meta.get(khoa) or "").strip()


def _ngay(meta: dict, khoa: str) -> str:
    return _chuoi(meta, khoa)[:10]


def _tieu_de(meta: dict, body: str, slug: str) -> str:
    tieu = _chuoi(meta, "title") or _chuoi(meta, "name")
    if not tieu:
        m = _TIEU_DE_RE.search(body)
        tieu = m.group(1).strip() if m else ""
    return tieu or slug


def _giai_doan(meta: dict) -> str:
    gd = _chuoi(meta, "giai_doan").lower()
    if gd in GIAI_DOAN:
        return gd
    return _STATUS_CU.get(_chuoi(meta, "status").lower(), "moi")


def _loai(meta: dict) -> str:
    lo = _chuoi(meta, "loai").lower()
    return lo if lo in LOAI else "concept"


def _booking(meta: dict):
    raw = _chuoi(meta, "booking")
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _y_tuong(root: Path):
    out = []
    for p in _file_md(root / "wiki" / "y-tuong"):
        doc = _doc(p)
        if doc is None:
            continue
        meta, body = doc
        out.append({
            "slug": p.stem,
            "tieu_de": _tieu_de(meta, body, p.stem),
            "loai": _loai(meta),
            "giai_doan": _giai_doan(meta),
            "ngay": _ngay(meta, "created") or _ngay(meta, "ngay"),
            "booking": _booking(meta),
        })
    return out


def _sop(root: Path, hom_nay: str):
    out = []
    for p in _file_md(root / "wiki" / "quy-trinh"):
        doc = _doc(p)
        if doc is None:
            continue
        meta, body = doc
        status = _chuoi(meta, "status").lower() or "active"
        ra_soat = _ngay(meta, "ngay_ra_soat")
        out.append({
            "slug": p.stem,
            "tieu_de": _tieu_de(meta, body, p.stem),
            "status": status,
            "phien_ban": _chuoi(meta, "phien_ban"),
            "ngay_ra_soat": ra_soat,
            # Quá hạn chỉ tính cho SOP còn hiệu lực. Bản đã thay thế không cần rà soát nữa.
            "qua_han": status == "active" and bool(ra_soat) and ra_soat < hom_nay,
            "thay_the": _chuoi(meta, "thay_the"),
        })
    return out


def _radar(root: Path):
    out = []
    for p in _file_md(root / "wiki" / "radar"):
        doc = _doc(p)
        if doc is None:
            continue
        meta, body = doc
        out.append({"slug": p.stem, "tieu_de": _tieu_de(meta, body, p.stem), "ngay": _ngay(meta, "ngay")})
    out.sort(key=lambda r: (r["ngay"], r["slug"]), reverse=True)
    return out[:MUC_RADAR]


def _nhat_ky(root: Path):
    p = root / "wiki" / "log.md"
    if not p.is_file():
        return []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    muc = []
    for dong in lines:
        m = _LOG_RE.match(dong)
        if m:
            muc.append({"ngay": m.group(1), "loai": m.group(2).strip(), "tieu_de": m.group(3)})
    # log là nối đuôi theo thời gian, nên đảo lại để mới nhất lên đầu.
    return list(reversed(muc))[:MUC_NHAT_KY]


def _rong(hom_nay: str, co_brain: bool) -> dict:
    return {
        "brain": PILOT_BRAIN, "co_brain": co_brain, "hom_nay": hom_nay,
        "tong_quan": {"y_tuong_tong": 0, "theo_giai_doan": {g: 0 for g in GIAI_DOAN},
                      "sop_active": 0, "sop_superseded": 0, "sop_qua_han": 0,
                      "change_request_mo": 0, "pilot_dang_chay": 0},
        "pipeline": {"cot": [{"giai_doan": g, "the": []} for g in PIPELINE]},
        "thu_vien": {"concept": [], "nguon_booking": False},
        "quy_trinh": {"sop": [], "change_request": []},
        "radar": {"muc": []},
        "nhat_ky": {"muc": []},
    }


def doc_trang(root: Path, hom_nay: str = None) -> dict:
    """Sáu khu của trang Nghiên cứu cho một brain. `hom_nay` để test truyền ngày cố định."""
    hom_nay = hom_nay or _dt.date.today().isoformat()
    root = Path(root)
    if not root.is_dir():
        return _rong(hom_nay, co_brain=False)

    yt = _y_tuong(root)
    sop = _sop(root, hom_nay)
    cr_mo = [y for y in yt if y["loai"] == "sua-quy-trinh" and y["giai_doan"] not in _CR_DONG]
    theo_gd = {g: 0 for g in GIAI_DOAN}
    for y in yt:
        theo_gd[y["giai_doan"]] += 1

    thu_vien = [
        {"slug": y["slug"], "tieu_de": y["tieu_de"], "giai_doan": y["giai_doan"], "booking": y["booking"]}
        for y in yt if y["loai"] == "concept" and y["giai_doan"] in _CONCEPT_THU_VIEN
    ]
    cot = [{"giai_doan": g,
            "the": [{"slug": y["slug"], "tieu_de": y["tieu_de"], "loai": y["loai"], "ngay": y["ngay"]}
                    for y in yt if y["giai_doan"] == g]}
           for g in PIPELINE]

    return {
        "brain": PILOT_BRAIN, "co_brain": True, "hom_nay": hom_nay,
        "tong_quan": {
            "y_tuong_tong": len(yt),
            "theo_giai_doan": theo_gd,
            "sop_active": sum(1 for s in sop if s["status"] == "active"),
            "sop_superseded": sum(1 for s in sop if s["status"] == "superseded"),
            "sop_qua_han": sum(1 for s in sop if s["qua_han"]),
            "change_request_mo": len(cr_mo),
            "pilot_dang_chay": theo_gd["pilot"],
        },
        "pipeline": {"cot": cot},
        "thu_vien": {"concept": thu_vien,
                     "nguon_booking": any(t["booking"] is not None for t in thu_vien)},
        "quy_trinh": {
            "sop": sop,
            "change_request": [{"slug": y["slug"], "tieu_de": y["tieu_de"], "giai_doan": y["giai_doan"]}
                               for y in cr_mo],
        },
        "radar": {"muc": _radar(root)},
        "nhat_ky": {"muc": _nhat_ky(root)},
    }
