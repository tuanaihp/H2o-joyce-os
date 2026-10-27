"""Quản lý Shop: SỔ THẬT (hợp đồng, báo giá, thu chi, nhân sự, việc) và nhật ký agent từng phòng.

Trang `dashboard/quan-ly-shop.html` trước đây vẽ số cứng trong mã trang. Ở đây là kho dữ liệu thật mà
mọi agent cùng ghi qua MỘT cửa (`xu_ly`), còn trang chỉ đọc.

Luồng một câu của chủ trong chat (ví dụ "hợp đồng Tuấn Thủy 0899252392, gói chụp studio 15 triệu,
thu 15tr, chi 4tr setup"):
  1. Joyce (bộ não tổng) chỉ ĐỌC câu và tách thành các sự kiện có cấu trúc, gọi tool `joyce_shop`.
  2. `xu_ly` định tuyến từng sự kiện về phòng phụ trách (Sales, Thu, Chi, Đối Soát, Nhân Sự), ghi
     sổ bằng LUẬT CỐ ĐỊNH (không tốn quota model) và ghi một dòng nhật ký mang tên agent của phòng đó,
     để văn phòng ảo hiện đúng agent đang làm.
  3. Chỉ khi cần phán đoán (khoản chi của nhân viên vượt hạn mức, hợp đồng hoàn thành cần báo cáo)
     mới giao một việc Kanban cho agent trưởng phòng, kèm tên skill của phòng.

Hạn mức duyệt chi (mô hình bảng phân quyền duyệt): chi do CHỦ báo thì ghi luôn; chi do nhân viên
báo mà từ ngưỡng trở lên thì nằm ở "chờ duyệt" cho chủ bấm duyệt. Người ghi khác người duyệt.

Hoa hồng nhân sự tính ĐỘNG từ sổ (lãi gộp = thu đã ghi trừ chi đã ghi của hợp đồng), nên sửa một
phiếu là lương đổi theo, không có số lưu cũ. Chỉ chủ và quản lý đọc ghi được (có thu chi và lương).
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
import unicodedata
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Form, HTTPException, Request

import config as cfgmod
import crm
import shop_state

router = APIRouter()

_deps: Dict[str, Callable] = {
    "phong": lambda: [],            # -> [{"brain":..., "ten":..., "agent":...}]
    "brain_root": lambda b: "",     # tên brain -> thư mục
    "tasks": lambda: None,          # -> TasksFeature
}

NGUONG_CHI_MAC_DINH = 2_000_000
TY_LE_VAI_MAC_DINH = {"sales": 5.0, "chup": 20.0, "makeup": 15.0, "hotro": 3.0, "khac": 0.0}
VAI_HOP_LE = tuple(TY_LE_VAI_MAC_DINH)
CHU = ("ceo", "giam_doc")          # vai trò được coi như chủ khi duyệt chi
TRANG_THAI_HD = ("bao_gia", "da_ky", "hoan_thanh", "huy")
TRANG_THAI_VIEC = ("todo", "doing", "review", "done")
TRUNG_LAP_GIAY = 600               # cùng một sự kiện gửi lại trong 10 phút thì không ghi hai lần

# Phòng phụ trách từng loại việc (tên brain trong sổ phòng ban) và skill của phòng đó.
VAI_PHONG = {
    "sales": ("Ban Hang - Sales Hinh Anh", "h2o-studio-sale-lead-triage"),
    "sales_makeup": ("Ban Hang - Sales Makeup", "h2o-studio-sale-lead-triage"),
    "sales_vay": ("Ban Hang - Sales Vay Cuoi", "h2o-studio-sale-lead-triage"),
    "sales_thuyh2o": ("ThuyH2O - Marketing va Bao Gia", ""),
    "thu": ("Ke Toan - Thu", "h2o-studio-ketoan-thu-cong-no"),
    "chi": ("Ke Toan - Chi", "h2o-studio-ketoan-chi-kiem-soat"),
    "doi_soat": ("Ke Toan - Doi Soat va Bao Cao", "h2o-studio-ketoan-doi-soat-bao-cao"),
    "nhan_su": ("Nhan Su - Van Hanh", "h2o-studio-nhansu-tuyen-danh-gia-van-hanh"),
    "van_thu": ("Van Thu va Quy Trinh", "h2o-studio-vanthu-quy-trinh"),
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS so_hop_dong(
  id INTEGER PRIMARY KEY, ma TEXT, contact_id INTEGER, ten_khach TEXT, sdt TEXT, goi TEXT,
  gia_tri REAL DEFAULT 0, thuong_hieu TEXT DEFAULT 'h2o', brain TEXT DEFAULT '', trang_thai TEXT DEFAULT 'bao_gia',
  deal_id INTEGER, ngay TEXT, ngay_ky TEXT, nguoi_tao TEXT DEFAULT '', created_at REAL, dv_ma TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS so_quy(
  id INTEGER PRIMARY KEY, loai TEXT, so_tien REAL, hang_muc TEXT DEFAULT '', dien_giai TEXT DEFAULT '', ngay TEXT,
  hop_dong_id INTEGER, trang_thai TEXT DEFAULT 'da_ghi', phong TEXT DEFAULT '', agent TEXT DEFAULT '',
  nguoi_ghi TEXT DEFAULT '', khoa TEXT DEFAULT '', created_at REAL, quyet_boi TEXT DEFAULT '', quyet_luc REAL);
CREATE INDEX IF NOT EXISTS ix_so_quy_hd ON so_quy(hop_dong_id, trang_thai);
CREATE TABLE IF NOT EXISTS so_bao_gia(
  id INTEGER PRIMARY KEY, so TEXT, hop_dong_id INTEGER, ten_khach TEXT DEFAULT '', sdt TEXT DEFAULT '',
  dong_json TEXT DEFAULT '[]', giam REAL DEFAULT 0, vat REAL DEFAULT 0, tong REAL DEFAULT 0,
  trang_thai TEXT DEFAULT 'nhap', ghi_chu TEXT DEFAULT '', ngay TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS so_nhan_su(
  id INTEGER PRIMARY KEY, ten TEXT, chuc_vu TEXT DEFAULT '', vai TEXT DEFAULT 'khac', phong_ban TEXT DEFAULT '',
  sdt TEXT DEFAULT '', luong_cb REAL DEFAULT 0, ty_le REAL, nghi INTEGER DEFAULT 0, mau INTEGER DEFAULT 0, created_at REAL);
CREATE TABLE IF NOT EXISTS so_phan_cong(
  hop_dong_id INTEGER, nhan_su_id INTEGER, vai TEXT DEFAULT '', PRIMARY KEY(hop_dong_id, nhan_su_id));
CREATE TABLE IF NOT EXISTS so_viec(
  id INTEGER PRIMARY KEY, tieu_de TEXT, du_an TEXT DEFAULT '', giao_cho TEXT DEFAULT '', han TEXT DEFAULT '',
  uu_tien TEXT DEFAULT '', trang_thai TEXT DEFAULT 'todo', hop_dong_id INTEGER, phong TEXT DEFAULT '', created_at REAL);
CREATE TABLE IF NOT EXISTS so_hoat_dong(
  id INTEGER PRIMARY KEY, brain TEXT, phong TEXT, agent TEXT, skill TEXT DEFAULT '', hanh_dong TEXT,
  loai TEXT DEFAULT '', ref_id INTEGER, trang_thai TEXT DEFAULT 'xong', created_at REAL);
CREATE INDEX IF NOT EXISTS ix_so_hd_t ON so_hoat_dong(created_at);
CREATE TABLE IF NOT EXISTS so_cau_hinh(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS so_cong_viec(
  id INTEGER PRIMARY KEY, ma_phong TEXT, nhom TEXT DEFAULT '', ten TEXT, phi_them REAL DEFAULT 0,
  hoa_hong REAL DEFAULT 0, so_ngay INTEGER DEFAULT 1, ap_dung INTEGER DEFAULT 1, created_at REAL,
  UNIQUE(ma_phong, ten));
CREATE TABLE IF NOT EXISTS so_dich_vu(
  id INTEGER PRIMARY KEY, ma TEXT UNIQUE, loai TEXT DEFAULT '', goi TEXT, don_gia REAL DEFAULT 0,
  coc1_pct REAL DEFAULT 0, coc2_pct REAL DEFAULT 0, ap_dung INTEGER DEFAULT 1, created_at REAL);
CREATE TABLE IF NOT EXISTS so_do(
  id INTEGER PRIMARY KEY, ma_dv TEXT DEFAULT '', pb TEXT DEFAULT '', ma_do TEXT UNIQUE, nhom TEXT DEFAULT '', co TEXT DEFAULT '',
  mau_sac TEXT DEFAULT '', mo_ta TEXT DEFAULT '', hinh TEXT DEFAULT '', don_gia REAL DEFAULT 0, ap_dung INTEGER DEFAULT 1,
  la_mau INTEGER DEFAULT 0, created_at REAL);
CREATE TABLE IF NOT EXISTS so_thue_do(
  id INTEGER PRIMARY KEY, key TEXT UNIQUE, hop_dong_id INTEGER, so_hd TEXT DEFAULT '', nguoi_tao TEXT DEFAULT '', ma_do TEXT,
  nhom TEXT DEFAULT '', ghi_chu TEXT DEFAULT '', don_gia REAL DEFAULT 0, khuyen_mai REAL DEFAULT 0, gia_con_lai REAL DEFAULT 0,
  trang_thai TEXT DEFAULT 'giu_cho', ngay_thue TEXT, ngay_tra_du_kien TEXT, ngay_tra_thuc TEXT DEFAULT '', khach TEXT DEFAULT '',
  sdt TEXT DEFAULT '', quy_id INTEGER, la_mau INTEGER DEFAULT 0, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_so_thue_do ON so_thue_do(ma_do, trang_thai);
CREATE TABLE IF NOT EXISTS so_giao_viec(
  id INTEGER PRIMARY KEY, hop_dong_id INTEGER, cong_viec_id INTEGER, nhan_su_id INTEGER, ten TEXT, ma_phong TEXT DEFAULT '',
  hoa_hong REAL DEFAULT 0, phi_them REAL DEFAULT 0, so_luong REAL DEFAULT 1, han TEXT DEFAULT '',
  trang_thai TEXT DEFAULT 'todo', created_at REAL, UNIQUE(hop_dong_id, cong_viec_id, nhan_su_id));
"""

# Bảng giá dịch vụ: (mã, loại, gói, đơn giá, % cọc lần 1, % cọc lần 2) - chép nguyên từ tab "3_DM dịch vụ" của chủ ngày 27/10/2026.
# Cọc lần 1 = đơn giá x %; cọc lần 2 = phần còn lại x %; thanh toán = phần còn lại cuối cùng. Đơn giá 0 nghĩa là sheet chưa điền giá (báo giá theo yêu cầu).
DICH_VU_H2O = [
    ('PRW-STCB', 'Pre-wedding', 'Trọn gói studio cơ bản', 4960000, 10, 50),
    ('PRW-GOL', 'Pre-wedding', 'Trọn gói cơ bản studio', 5600000, 10, 50),
    ('PRW-STV', 'Pre-wedding', 'Trọn gói vip studio', 6300000, 10, 50),
    ('PRW-SNT', 'Pre-wedding', 'Trọn gói studio nội thành', 8600000, 10, 50),
    ('PRW-STNT', 'Pre-wedding', 'Trọn gói studio nội thành vip', 9600000, 10, 50),
    ('PRW-PT', 'Pre-wedding', 'Trọn gói ngoại cảnh phim trường', 8600000, 10, 50),
    ('PRW-PTV', 'Pre-wedding', 'Trọn gói phim trường vip', 9500000, 10, 50),
    ('PRW-STNC', 'Pre-wedding', 'Trọn gói studio ngoại cảnh vip', 9600000, 10, 50),
    ('PRW-PTHN', 'Pre-wedding', 'Trọn gói phim trường vip Hà Nội', 11600000, 10, 50),
    ('PRW-HLV', 'Pre-wedding', 'Trọn gói vip tuần châu Hạ Long', 11600000, 10, 50),
    ('PRW-LUX', 'Pre-wedding', 'Trọn gói ngoại cảnh full luxury', 24000000, 10, 50),
    ('MUCD-CB1', 'Trọn gói makeup', 'Combo một ngày cưới', 0, 0, 0),
    ('MUCD-CB2', 'Trọn gói makeup', 'Combo hai ngày cưới', 0, 0, 0),
    ('MUCD-LUX', 'Trọn gói makeup', 'Combo hai ngày cưới luxury', 0, 0, 0),
    ('MUCD-CB3', 'Trọn gói makeup', 'Combo ăn hỏi', 0, 0, 0),
    ('MUA-DVLE', 'Trọn gói makeup', 'Makeup lẽ', 0, 0, 0),
    ('PS-1SEC', 'Ảnh phóng sự', 'Chụp ảnh phóng sự 1 sec', 1800000, 0, 0),
    ('PS-2SEC', 'Ảnh phóng sự', 'Chụp ảnh phóng sự 2 sec', 2800000, 0, 0),
    ('PS-3SEC', 'Ảnh phóng sự', 'Chụp ảnh phóng sự 3 sec', 3500000, 0, 0),
    ('QP-TT', 'Quay phim', 'Quay truyền thống', 3500000, 0, 0),
    ('QP-PRW', 'Quay phim', 'Quay pre-wedding', 2500000, 0, 0),
    ('QP-FLY', 'Quay phim', 'Quay flycam', 1000000, 0, 0),
    ('BEA-CB', 'Beauty', 'Chụp ảnh beauty cơ bản', 1500000, 0, 0),
    ('BEA-VP', 'Beauty', 'Chụp ảnh beauty Vip', 2500000, 0, 0),
    ('GD-CB', 'Gia đình', 'Trọn gói gia đình cơ bản', 1250000, 0, 0),
    ('GD-NC', 'Gia đình', 'Trọn gói gia đình nâng cấp', 1750000, 0, 0),
    ('GD-CC', 'Gia đình', 'Trọn gói gia đình cao cấp', 2650000, 0, 0),
    ('GD-LUX', 'Gia đình', 'Trọn gói gia đình luxury', 3560000, 0, 0),
    ('KID-CB', 'Baby', 'Trọn gói baby cơ bản', 550000, 0, 0),
    ('KID-VP', 'Baby', 'Trọn gói baby vip', 1200000, 0, 0),
    ('IN-3045', 'In ấn', 'Ảnh in cỡ 30x45', 350000, 0, 0),
    ('IN-4060', 'In ấn', 'Ảnh in cỡ 40x60', 600000, 0, 0),
    ('IN-5075', 'In ấn', 'Ảnh in cỡ 50x75', 800000, 0, 0),
    ('IN-6090', 'In ấn', 'Ảnh in cỡ 60x90', 1000000, 0, 0),
    ('IN-70110', 'In ấn', 'Ảnh in cỡ 70x110', 2500000, 0, 0),
    ('IN-80112', 'In ấn', 'Ảnh in cỡ 80x120', 3500000, 0, 0),
    ('IN-1150', 'In ấn', 'Ảnh in cỡ 100x150', 5500000, 0, 0),
    ('VAY-CB', 'Thuê váy', 'Váy combo', 0, 0, 0),
    ('VAY-TK', 'Thuê váy', 'Váy thiết kế', 0, 0, 0),
    ('VAY-CC', 'Thuê váy', 'Váy cao cấp', 0, 0, 0),
    ('VEST', 'Thuê vest', 'Áo vest cao cấp', 500000, 0, 0),
    ('ADCD', 'Thuê áo dài cô dâu', 'Thuê áo dài cô dâu', 500000, 0, 0),
    ('PRE-FULLUX', 'Pre-wedding', 'Trọn gói full luxury studio', 13800000, 10, 50),
    ('THUE-LE', 'Thuê lễ', 'Gói dịch vụ thuê lễ', 500000, 0, 0),
    ('ADM', 'Thuê áo dài mẹ', 'Thuê áo dài mẹ', 500000, 0, 0),
    ('PRW-STV2', 'Pre-wedding', 'Trọn gói vip studio 2', 7600000, 10, 50),
]

# Mã phòng trong bảng "5_DS chia việc" của H2O: tên hiển thị và vai nhân sự hay gặp ở phòng đó.
MA_PHONG = {
    "MAKEUP": ("Makeup", "makeup"), "PHOTO": ("Chụp ảnh", "chup"), "PTS": ("Photoshop, hậu kỳ", "hotro"),
    "OUT": ("Thử đồ", "hotro"), "WDRESS": ("Tư vấn váy", "sales"),
}
# (mã phòng, nhóm, tên việc, phí thu thêm khách, hoa hồng, số ngày) - chép nguyên từ Google Sheet của chủ ngày 27/10/2026.
# Bốn dòng 27 đến 30 của sheet đang bị ẩn nên chưa có ở đây.
CONG_VIEC_H2O = [
    ("MAKEUP", "Bới tóc", "Bới tóc cô dâu ăn hỏi", 0, 70000, 1), ("MAKEUP", "Bới tóc", "Bới tóc cô dâu ngày cưới", 0, 70000, 1),
    ("MAKEUP", "Bới tóc", "Bới tóc cô dâu", 0, 70000, 1), ("MAKEUP", "Bới tóc", "Bới tóc lễ dự", 0, 0, 1),
    ("MAKEUP", "Bới tóc", "Bới tóc 2 lần ngày chụp", 0, 0, 1), ("MAKEUP", "Bới tóc", "Cuộn tóc", 0, 21000, 1),
    ("MAKEUP", "Bới tóc", "Hoàn thiện", 0, 49000, 1), ("MAKEUP", "Bới tóc", "Thay tóc chụp", 0, 0, 1),
    ("MAKEUP", "Bới tóc", "Take care chụp", 0, 0, 1),
    ("PHOTO", "Chụp studio", "Chụp ảnh cưới studio", 0, 250000, 1), ("PHOTO", "Chụp studio", "Chụp ảnh gia đình", 0, 0, 1),
    ("PHOTO", "Chụp studio", "Chụp ảnh khác", 0, 0, 1), ("PHOTO", "Chụp ngoại cảnh", "Chụp ảnh ngoại cảnh", 0, 450000, 1),
    ("PHOTO", "Chụp studio", "Chụp ảnh phóng sự", 0, 0, 3),
    ("MAKEUP", "Makeup", "Makeup cô dâu", 0, 90000, 1), ("MAKEUP", "Makeup", "Makeup lễ dự", 0, 0, 1),
    ("MAKEUP", "Makeup", "Makeup nền", 0, 27000, 1), ("MAKEUP", "Makeup", "Makeup nền và lông mày", 0, 45000, 1),
    ("MAKEUP", "Makeup", "Hoàn thiện có lông mày", 0, 63000, 1), ("MAKEUP", "Makeup", "Hoàn thiện không lông mày", 0, 45000, 1),
    ("PTS", "Pts", "Chạy slide ảnh", 0, 0, 1), ("PTS", "Pts", "Photoshop ảnh khung", 0, 150000, 1),
    ("PTS", "Pts", "Photoshop ảnh các loại", 0, 0, 1), ("PTS", "Pts", "Photoshop ảnh phóng 60x90", 0, 50000, 1),
    ("OUT", "Thử đồ", "Sắp đồ cho khách", 0, 0, 1),
    ("WDRESS", "Tư vấn váy", "Tư vấn Offline", 0, 50000, 1), ("WDRESS", "Tư vấn váy", "Tư vấn Online", 0, 0, 3),
    ("WDRESS", "Tư vấn váy", "Tư vấn váy", 0, 0, 1),
    ("MAKEUP", "Makeup", "Makeup cd ăn hỏi", 0, 90000, 1), ("MAKEUP", "Makeup", "Makeup cd cưới", 0, 90000, 1),
]

_lock = threading.RLock()
_ready: set = set()


def _path():
    return cfgmod.STATE_DIR / "shop_so.sqlite3"


def _db() -> sqlite3.Connection:
    p = _path()
    c = sqlite3.connect(str(p), timeout=15)
    c.row_factory = sqlite3.Row
    if str(p) not in _ready:
        c.executescript(_SCHEMA)
        if "dv_ma" not in {r[1] for r in c.execute("PRAGMA table_info(so_hop_dong)").fetchall()}:   # sổ tạo từ bản cũ
            c.execute("ALTER TABLE so_hop_dong ADD COLUMN dv_ma TEXT DEFAULT ''")
        c.commit()
        _ready.add(str(p))
    return c


def _dung(f):
    with _lock:
        c = _db()
        try:
            return f(c)
        finally:
            c.close()


def _rows(rs) -> List[dict]:
    return [dict(r) for r in rs]


def _ascii(s: Any) -> str:
    s = unicodedata.normalize("NFD", str(s or "")).replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _s(v: Any, n: int = 200) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _homnay() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ky(ngay: str = "") -> str:
    return (ngay or _homnay())[:7]


def tien(v: Any) -> float:
    """15000000, "15.000.000", "15tr", "15 triệu", "1,5 triệu", "500k" -> số đồng. Không hiểu thì 0."""
    if isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return max(0.0, float(v))
    m = re.search(r"(\d[\d.,]*)\s*(trieu|tr|nghin|ngan|k|ty)?\b", _ascii(v).lower())
    if not m:
        return 0.0
    num, unit = m.group(1), m.group(2) or ""
    cham_nhom = re.fullmatch(r"\d{1,3}([.,]\d{3})+", num) is not None   # 15.000.000: dấu là phân nhóm
    if unit and not cham_nhom:
        x = float(num.replace(",", "."))
        return x * {"trieu": 1e6, "tr": 1e6, "nghin": 1e3, "ngan": 1e3, "k": 1e3, "ty": 1e9}[unit]
    if unit:
        return float(re.sub(r"[.,]", "", num)) * {"trieu": 1e6, "tr": 1e6, "nghin": 1e3, "ngan": 1e3, "k": 1e3, "ty": 1e9}[unit]
    return float(re.sub(r"[.,]", "", num))


def _vnd(x: Any) -> str:
    """15000000 -> "15.000.000" (chấm phân nhóm kiểu Việt)."""
    return f"{int(round(float(x or 0))):,}".replace(",", ".")


def _ngay_ok(v: Any) -> str:
    s = str(v or "").strip()
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else _homnay()


# ---------------------------------------------------------------- cấu hình
def cau_hinh() -> dict:
    def f(db):
        d = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM so_cau_hinh").fetchall()}
        try:
            tl = json.loads(d.get("ty_le_vai") or "{}")
        except Exception:
            tl = {}
        ty = dict(TY_LE_VAI_MAC_DINH)
        ty.update({k: float(v) for k, v in tl.items() if k in VAI_HOP_LE})
        return {"nguong_chi": float(d.get("nguong_chi") or NGUONG_CHI_MAC_DINH),
                "co_so_hh": d.get("co_so_hh") if d.get("co_so_hh") in ("lai_gop", "doanh_thu") else "lai_gop",
                "ty_le_vai": ty}
    return _dung(f)


def luu_cau_hinh(data: dict) -> dict:
    def f(db):
        if "nguong_chi" in data:
            db.execute("INSERT OR REPLACE INTO so_cau_hinh(key,value) VALUES('nguong_chi',?)",
                       (str(max(0.0, tien(data["nguong_chi"]))),))
        if data.get("co_so_hh") in ("lai_gop", "doanh_thu"):
            db.execute("INSERT OR REPLACE INTO so_cau_hinh(key,value) VALUES('co_so_hh',?)", (data["co_so_hh"],))
        if isinstance(data.get("ty_le_vai"), dict):
            cur = cau_hinh()["ty_le_vai"]
            for k, v in data["ty_le_vai"].items():
                if k in VAI_HOP_LE:
                    cur[k] = max(0.0, min(100.0, float(v)))
            db.execute("INSERT OR REPLACE INTO so_cau_hinh(key,value) VALUES('ty_le_vai',?)", (json.dumps(cur),))
        db.commit()
    _dung(f)
    return cau_hinh()


# ---------------------------------------------------------------- phòng và nhật ký agent
def _phong(brain: str) -> dict:
    for p in (_deps["phong"]() or []):
        if p.get("brain") == brain:
            return {"brain": brain, "ten": p.get("ten") or brain, "agent": p.get("agent") or ""}
    return {"brain": brain, "ten": brain, "agent": ""}


def phong_sales(dich_vu: str = "", thuong_hieu: str = "h2o") -> str:
    t = _ascii(dich_vu).lower()
    if thuong_hieu == "thuyh2o":
        return VAI_PHONG["sales_thuyh2o"][0]
    if "makeup" in t or "trang diem" in t:
        return VAI_PHONG["sales_makeup"][0]
    if re.search(r"\bvay\b", t):          # "chụp cưới" là Hình Ảnh, chỉ "váy" mới về Sales Váy Cưới
        return VAI_PHONG["sales_vay"][0]
    return VAI_PHONG["sales"][0]


def ghi_hoat_dong(brain: str, hanh_dong: str, loai: str = "", ref_id: int = 0, trang_thai: str = "xong",
                  skill: str = "") -> dict:
    """Một dòng 'agent của phòng này vừa làm gì'. Văn phòng ảo đọc bảng này để hiện bong bóng."""
    p = _phong(brain)
    if not skill:
        skill = next((s for b, s in VAI_PHONG.values() if b == brain), "")
    now = time.time()

    def f(db):
        cur = db.execute("INSERT INTO so_hoat_dong(brain, phong, agent, skill, hanh_dong, loai, ref_id, trang_thai, created_at)"
                         " VALUES(?,?,?,?,?,?,?,?,?)",
                         (brain, p["ten"], p["agent"], skill, _s(hanh_dong, 240), loai, int(ref_id or 0), trang_thai, now))
        db.commit()
        return int(cur.lastrowid)
    i = _dung(f)
    return {"id": i, "brain": brain, "phong": p["ten"], "agent": p["agent"], "skill": skill,
            "hanh_dong": hanh_dong, "trang_thai": trang_thai, "created_at": now}


def hoat_dong(phut: int = 180, limit: int = 60) -> List[dict]:
    moc = time.time() - max(1, int(phut)) * 60
    return _dung(lambda db: _rows(db.execute(
        "SELECT * FROM so_hoat_dong WHERE created_at>=? ORDER BY id DESC LIMIT ?", (moc, int(limit))).fetchall()))


def _giao_agent(brain: str, tieu_de: str, intent: str, chat_id: str = "") -> str:
    """Giao một việc Kanban cho agent trưởng phòng. Trả câu nói thật về việc đó có tự chạy không."""
    f = _deps["tasks"]()
    root = _deps["brain_root"](brain) if f else ""
    if f is None or not root:
        return "Chưa giao được cho agent (hàng đợi việc chưa sẵn sàng); khoản này nằm chờ duyệt ở trang Thu chi."
    try:
        tid = f.enqueue(root, tieu_de, intent, "auto", 2, [], False, "chat", chat_id, "auto", "suggest", "")
    except Exception as e:
        return f"Chưa giao được cho agent ({type(e).__name__}: {e})."
    muc = "off"
    try:
        muc = f.board_view(root).get("orchestration") or "off"
    except Exception:
        pass
    p = _phong(brain)
    if str(muc).lower() == "auto":
        return f"Đã giao việc {tid} cho {p['agent'] or p['ten']}, kết quả tự về chat."
    return (f"Đã xếp việc {tid} cho {p['agent'] or p['ten']} nhưng điều phối của phòng \"{p['ten']}\" đang "
            f"\"{muc}\" nên việc KHÔNG tự chạy; bật \"AI tự vận hành\" ở trang Việc của phòng đó.")


# ---------------------------------------------------------------- tìm hợp đồng
def lay_hop_dong(hid: int) -> Optional[dict]:
    r = _dung(lambda db: db.execute("SELECT * FROM so_hop_dong WHERE id=?", (int(hid),)).fetchone())
    return dict(r) if r else None


def tim_hop_dong(ref: Any) -> tuple:
    """(hợp đồng|None, cảnh báo). ref: mã HD0001, số điện thoại, hoặc một phần tên khách."""
    ref = _s(ref, 120)
    if not ref:
        return None, ""
    ma = re.fullmatch(r"(?i)hd\s*0*(\d+)", ref)
    if ma:
        hd = lay_hop_dong(int(ma.group(1)))
        return hd, "" if hd else f"Không có hợp đồng {ref}."
    n = crm.chuan_sdt(ref)
    ds = _dung(lambda db: _rows(db.execute("SELECT * FROM so_hop_dong WHERE trang_thai!='huy' ORDER BY id DESC").fetchall()))
    if n:
        kq = [h for h in ds if h["sdt"] == n]
    else:
        t = _ascii(ref).lower()
        kq = [h for h in ds if t in _ascii(h["ten_khach"]).lower()]
    if not kq:
        return None, f"Không thấy hợp đồng nào của \"{ref}\"."
    if len(kq) > 1:
        return kq[0], f"\"{ref}\" có {len(kq)} hợp đồng, đã gắn vào mới nhất ({kq[0]['ma']})."
    return kq[0], ""


# ---------------------------------------------------------------- ghi sổ (một cửa)
def _khoa(*parts) -> str:
    return hashlib.sha1("|".join(_ascii(p).lower() for p in parts).encode("utf-8")).hexdigest()[:16]


def _ma(db, bang: str, tiep_dau: str) -> str:
    n = db.execute(f"SELECT COALESCE(MAX(id),0)+1 FROM {bang}").fetchone()[0]
    return f"{tiep_dau}{int(n):04d}"


def _la_chu(by_info: dict) -> bool:
    return not by_info or str(by_info.get("role") or "") in CHU


def _su_kien_hop_dong(sk: dict, by: str, chat_id: str) -> dict:
    ten = _s(sk.get("ten") or sk.get("khach"), 120)
    sdt = crm.chuan_sdt(sk.get("sdt") or "")
    goi = _s(sk.get("goi") or sk.get("dich_vu"), 160) or "Hợp đồng"
    gia = tien(sk.get("gia_tri", sk.get("so_tien", 0)))
    dv = tim_dich_vu(sk.get("dich_vu_ma") or goi)
    if dv:
        # Báo đúng mã hoặc đúng tên gói trong bảng giá: lấy tên chuẩn, và giá nếu chủ không nói giá khác (giá thương lượng được giữ).
        if _ascii(goi).lower() == _ascii(dv["ma"]).lower():
            goi = dv["goi"]
        if gia <= 0:
            gia = dv["don_gia"]
    th = "thuyh2o" if _ascii(sk.get("thuong_hieu")).lower().startswith("thuy") else "h2o"
    if not (ten or sdt):
        raise ValueError("Hợp đồng cần ít nhất tên khách hoặc số điện thoại")
    brain = phong_sales(goi, th)
    # Gửi lại cùng hợp đồng thì trả hợp đồng cũ, đừng tạo bản thứ hai.
    cu = _dung(lambda db: db.execute(
        "SELECT * FROM so_hop_dong WHERE trang_thai!='huy' AND gia_tri=? ORDER BY id DESC", (gia,)).fetchall())
    cu = [dict(r) for r in cu if _ascii(r["goi"]).lower() == _ascii(goi).lower()
          and (r["sdt"] == sdt if sdt else _ascii(r["ten_khach"]).lower() == _ascii(ten).lower())]
    if cu:
        return {"loai": "hop_dong", "id": cu[0]["id"], "ma": cu[0]["ma"], "da_co": True, "phong": _phong(brain)["ten"],
                "tom_tat": f"Hợp đồng {cu[0]['ma']} của {cu[0]['ten_khach']} đã có từ trước, không tạo lại."}
    # CRM: tìm khách theo số điện thoại trước khi tạo.
    kh = crm.tim_theo_sdt(sdt) if sdt else None
    if kh:
        if brain not in (kh.get("depts") or []):
            crm.gan_phong(kh["id"], brain, True, None, by)
    else:
        kh = crm.luu_lien_he({"name": ten or sdt, "phone": sdt, "source": "Chat Joyce", "depts": [brain]}, None, by, brain)
    trang_thai = sk.get("trang_thai") if sk.get("trang_thai") in TRANG_THAI_HD else "bao_gia"
    ds_gd = {g["key"]: g for g in crm.giai_doan(brain)}
    stage = "da_chot" if trang_thai in ("da_ky", "hoan_thanh") and "da_chot" in ds_gd else ("cho_chot" if "cho_chot" in ds_gd else list(ds_gd)[0])
    deal = crm.luu_deal({"contact_id": kh["id"], "brain": brain, "title": goi, "value": str(int(gia)), "stage": stage}, None, by)
    if deal and deal.get("stage") != stage:
        crm.chuyen_buoc(deal["id"], stage, None, by)
    if trang_thai == "bao_gia":
        crm.them_viec({"contact_id": kh["id"], "brain": brain, "title": f"Gửi báo giá cho {ten or sdt}"}, None, by)

    now = time.time()
    ngay = _ngay_ok(sk.get("ngay"))

    def f(db):
        ma = _ma(db, "so_hop_dong", "HD")
        cur = db.execute("INSERT INTO so_hop_dong(ma, contact_id, ten_khach, sdt, goi, gia_tri, thuong_hieu, brain, trang_thai,"
                         " deal_id, ngay, ngay_ky, nguoi_tao, created_at, dv_ma) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (ma, kh["id"], ten or kh.get("name") or sdt, sdt, goi, gia, th, brain, trang_thai,
                          deal["id"] if deal else None, ngay, ngay if trang_thai != "bao_gia" else "", by, now, dv["ma"] if dv else ""))
        hid = int(cur.lastrowid)
        bg = ""
        if trang_thai == "bao_gia":
            bg = _ma(db, "so_bao_gia", "BG")
            dong = [{"ten": goi, "sl": 1, "don_gia": gia}]
            db.execute("INSERT INTO so_bao_gia(so, hop_dong_id, ten_khach, sdt, dong_json, giam, vat, tong, trang_thai, ghi_chu, ngay,"
                       " created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (bg, hid, ten or sdt, sdt, json.dumps(dong, ensure_ascii=False), 0, 0, gia, "nhap",
                        "Báo giá có hiệu lực trong 7 ngày.", ngay, now))
        db.commit()
        return hid, ma, bg
    hid, ma, bg = _dung(f)
    for pc in (sk.get("phan_cong") or []):
        try:
            phan_cong(hid, pc.get("ten") or pc.get("nhan_su"), pc.get("vai") or "")
        except Exception:
            pass
    hd = ghi_hoat_dong(brain, f"Nhận khách {ten or sdt}, lập {('báo giá ' + bg) if bg else 'hợp đồng'} {_vnd(gia)}đ ({goi}), ghi CRM", "hop_dong", hid, skill=VAI_PHONG["sales"][1])
    return {"loai": "hop_dong", "id": hid, "ma": ma, "bao_gia": bg, "contact_id": kh["id"], "deal_id": deal["id"] if deal else None,
            "phong": hd["phong"], "agent": hd["agent"], "gia_tri": gia, "dich_vu": dv["ma"] if dv else "",
            "tom_tat": f"{hd['agent'] or hd['phong']}: khách {ten or sdt} vào CRM ({hd['phong']}), cơ hội {_vnd(gia)}đ ở bước chờ chốt, "
                       f"hợp đồng {ma}"  + (f", báo giá {bg}" if bg else "") + "."
                       + (f" Gói {dv['ma']} theo bảng giá." if dv and dv["don_gia"] > 0 else "")
                       + (f" Gói {dv['ma']} chưa có giá trong bảng, cần báo giá theo yêu cầu." if dv and dv["don_gia"] <= 0 and gia <= 0 else "")}


def _su_kien_quy(sk: dict, by: str, chat_id: str, by_info: dict, loai: str) -> dict:
    so_tien = tien(sk.get("so_tien", sk.get("gia_tri", 0)))
    if so_tien <= 0:
        raise ValueError("Phiếu " + ("thu" if loai == "thu" else "chi") + " cần số tiền lớn hơn 0")
    dien_giai = _s(sk.get("dien_giai") or sk.get("noi_dung") or sk.get("ghi_chu"), 240)
    hang_muc = _s(sk.get("hang_muc"), 60) or ("Thu khác" if loai == "thu" else "Chi khác")
    ngay = _ngay_ok(sk.get("ngay"))
    hd, canh_bao = (None, "")
    ref = sk.get("hop_dong") or sk.get("sdt") or sk.get("khach")
    if ref:
        hd, canh_bao = tim_hop_dong(ref)
    khoa = _khoa(loai, so_tien, hang_muc, dien_giai, hd["id"] if hd else 0, ngay)
    brain = VAI_PHONG[loai][0]
    cu = _dung(lambda db: db.execute("SELECT * FROM so_quy WHERE khoa=? AND created_at>?", (khoa, time.time() - TRUNG_LAP_GIAY)).fetchone())
    if cu:
        return {"loai": loai, "id": cu["id"], "da_co": True, "phong": _phong(brain)["ten"],
                "tom_tat": f"Phiếu {loai} {_vnd(so_tien)}đ này vừa được ghi, không ghi lại lần hai."}
    cfg = cau_hinh()
    cho_duyet = loai == "chi" and not _la_chu(by_info) and so_tien >= cfg["nguong_chi"]
    trang_thai = "cho_duyet" if cho_duyet else "da_ghi"
    p = _phong(brain)

    def f(db):
        cur = db.execute("INSERT INTO so_quy(loai, so_tien, hang_muc, dien_giai, ngay, hop_dong_id, trang_thai, phong, agent, nguoi_ghi,"
                         " khoa, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                         (loai, so_tien, hang_muc, dien_giai, ngay, hd["id"] if hd else None, trang_thai, p["ten"], p["agent"],
                          by, khoa, time.time()))
        db.commit()
        return int(cur.lastrowid)
    qid = _dung(f)
    note = []
    if hd:
        note.append(f"gắn hợp đồng {hd['ma']} ({hd['ten_khach']})")
        if loai == "thu" and hd["trang_thai"] == "bao_gia":
            doi_trang_thai_hd(hd["id"], "da_ky", by)
            note.append("hợp đồng chuyển sang Đã ký")
    elif ref:
        note.append(canh_bao or "chưa gắn được hợp đồng")
    elif loai == "thu":
        note.append("chưa gắn hợp đồng nào")
    if canh_bao and hd:
        note.append(canh_bao)
    hanh = (f"Ghi {'thu' if loai == 'thu' else 'chi'} {_vnd(so_tien)}đ ({hang_muc})"
            + (f", {dien_giai}" if dien_giai else "") + (", CHỜ DUYỆT" if cho_duyet else ""))
    ghi_hoat_dong(brain, hanh, loai, qid, "cho_duyet" if cho_duyet else "xong")
    ra = {"loai": loai, "id": qid, "so_tien": so_tien, "trang_thai": trang_thai, "phong": p["ten"], "agent": p["agent"],
          "hop_dong": hd["ma"] if hd else "", "canh_bao": canh_bao,
          "tom_tat": f"{p['agent'] or p['ten']}: {'thu' if loai == 'thu' else 'chi'} {_vnd(so_tien)}đ"
                     + (" - " + "; ".join(note) if note else "") + (". CHỜ CHỦ DUYỆT (vượt hạn mức)" if cho_duyet else ". Đã ghi sổ.")}
    if cho_duyet:
        ra["giao_agent"] = _giao_agent(brain, f"[Kiểm chi] {dien_giai or hang_muc} {_vnd(so_tien)}đ",
                                       f"Khoản chi {_vnd(so_tien)}đ ({hang_muc}) '{dien_giai}' do {by} báo, vượt hạn mức "
                                       f"{_vnd(cfg['nguong_chi'])}đ nên đang chờ chủ duyệt (phiếu số {qid} ở trang Thu chi). "
                                       f"Dùng skill {VAI_PHONG['chi'][1]}: kiểm chứng từ, phân loại COGS hay vận hành, gắn đúng hợp đồng, "
                                       "nêu rủi ro. Không tự duyệt.", chat_id)
    return ra


def _su_kien_viec(sk: dict, by: str) -> dict:
    tieu_de = _s(sk.get("tieu_de") or sk.get("ten"), 200)
    if not tieu_de:
        raise ValueError("Việc cần tiêu đề")
    hd = tim_hop_dong(sk.get("hop_dong"))[0] if sk.get("hop_dong") else None
    uu = sk.get("uu_tien") if sk.get("uu_tien") in ("Gấp", "Cao", "") else ""
    brain = VAI_PHONG["van_thu"][0]

    def f(db):
        cur = db.execute("INSERT INTO so_viec(tieu_de, du_an, giao_cho, han, uu_tien, trang_thai, hop_dong_id, phong, created_at)"
                         " VALUES(?,?,?,?,?,?,?,?,?)",
                         (tieu_de, _s(sk.get("du_an"), 80) or (hd["ma"] if hd else "Việc chung"), _s(sk.get("giao_cho"), 80),
                          _s(sk.get("han"), 10), uu, "todo", hd["id"] if hd else None, _phong(brain)["ten"], time.time()))
        db.commit()
        return int(cur.lastrowid)
    vid = _dung(f)
    h = ghi_hoat_dong(brain, f"Tạo việc: {tieu_de}", "viec", vid)
    return {"loai": "viec", "id": vid, "phong": h["phong"], "agent": h["agent"],
            "tom_tat": f"{h['agent'] or h['phong']}: tạo việc \"{tieu_de}\"."}


def xu_ly(events: Any, by: str = "Joyce", chat_id: str = "", by_info: Optional[dict] = None) -> dict:
    """Cửa duy nhất để ghi sổ. `events`: một sự kiện hoặc danh sách; mỗi sự kiện có `loai`:
    hop_dong | thu | chi | viec | phan_cong | giao_viec | thue_do | tra_do. Lỗi một sự kiện không làm hỏng các sự kiện khác."""
    if isinstance(events, dict):
        events = [events]
    by_info = by_info or {}
    kq, loi = [], []
    for i, sk in enumerate(events or []):
        if not isinstance(sk, dict):
            loi.append({"stt": i + 1, "loi": "Sự kiện phải là một object"})
            continue
        loai = _ascii(sk.get("loai")).lower().strip()
        try:
            if loai in ("hop_dong", "bao_gia", "khach"):
                kq.append(_su_kien_hop_dong(sk, by, chat_id))
            elif loai in ("thu", "chi"):
                kq.append(_su_kien_quy(sk, by, chat_id, by_info, loai))
            elif loai == "viec":
                kq.append(_su_kien_viec(sk, by))
            elif loai == "phan_cong":
                hd = tim_hop_dong(sk.get("hop_dong"))[0]
                if not hd:
                    raise ValueError("Không thấy hợp đồng để phân công")
                kq.append(phan_cong(hd["id"], sk.get("ten") or sk.get("nhan_su"), sk.get("vai") or ""))
            elif loai == "thue_do":
                kq.append(_su_kien_thue_do(sk, by, chat_id, by_info))
            elif loai == "tra_do":
                kq.append(_su_kien_tra_do(sk, by))
            elif loai == "giao_viec":
                hd = tim_hop_dong(sk.get("hop_dong"))[0]
                if not hd:
                    raise ValueError("Không thấy hợp đồng để chia việc")
                kq.append(giao_viec(hd["id"], sk.get("cong_viec") or sk.get("viec"), sk.get("ten") or sk.get("nhan_su"),
                                    sk.get("so_luong") or 1, sk.get("han") or "", sk.get("ma_phong") or ""))
            else:
                raise ValueError("loai phải là hop_dong, thu, chi, viec, phan_cong, giao_viec, thue_do hoặc tra_do")
        except (ValueError, PermissionError) as e:
            loi.append({"stt": i + 1, "loai": loai, "loi": str(e)})
    return {"ok": not loi, "ket_qua": kq, "loi": loi}


# ---------------------------------------------------------------- hợp đồng, báo giá
def doi_trang_thai_hd(hid: int, ts: str, by: str = "") -> dict:
    if ts not in TRANG_THAI_HD:
        raise ValueError("Trạng thái hợp đồng không hợp lệ")
    hd = lay_hop_dong(hid)
    if not hd:
        raise ValueError("Không thấy hợp đồng")

    def f(db):
        db.execute("UPDATE so_hop_dong SET trang_thai=?, ngay_ky=CASE WHEN ?='da_ky' AND COALESCE(ngay_ky,'')='' THEN ? ELSE ngay_ky END WHERE id=?",
                   (ts, ts, _homnay(), int(hid)))
        if ts == "da_ky":
            db.execute("UPDATE so_bao_gia SET trang_thai='chap_nhan' WHERE hop_dong_id=? AND trang_thai IN ('nhap','da_gui')", (int(hid),))
        if ts == "huy":
            db.execute("UPDATE so_bao_gia SET trang_thai='huy' WHERE hop_dong_id=? AND trang_thai IN ('nhap','da_gui')", (int(hid),))
        db.commit()
    _dung(f)
    try:
        if hd.get("deal_id") and hd.get("brain"):
            ds = {g["key"]: g for g in crm.giai_doan(hd["brain"])}
            muc = {"da_ky": "da_chot", "hoan_thanh": "da_chot", "huy": "mat", "bao_gia": "cho_chot"}[ts]
            if muc in ds:
                crm.chuyen_buoc(hd["deal_id"], muc, None, by or "Joyce")
    except Exception:
        pass
    ten = {"da_ky": "đã ký", "hoan_thanh": "hoàn thành", "huy": "hủy", "bao_gia": "báo giá"}[ts]
    ghi_hoat_dong(hd.get("brain") or VAI_PHONG["sales"][0], f"Hợp đồng {hd['ma']} ({hd['ten_khach']}) chuyển sang {ten}", "hop_dong", hid)
    if ts == "hoan_thanh":
        giao_bao_cao(hid)
    return lay_hop_dong(hid)


def giao_bao_cao(hid: int, chat_id: str = "") -> str:
    """Hợp đồng xong: phòng Đối Soát (agent + skill của phòng) lập báo cáo lãi lỗ. Đây là chỗ MỘT lượt model có giá trị."""
    hd = lay_hop_dong(hid)
    if not hd:
        return "Không thấy hợp đồng."
    ct = chi_tiet_hop_dong(hid)
    brain = VAI_PHONG["doi_soat"][0]
    ghi_hoat_dong(brain, f"Đối soát hợp đồng {hd['ma']}: thu {_vnd(ct['thu'])}đ, chi {_vnd(ct['chi'])}đ, lãi gộp {_vnd(ct['lai_gop'])}đ",
                  "doi_soat", hid)
    return _giao_agent(brain, f"[Đối soát] Hợp đồng {hd['ma']} {hd['ten_khach']}",
                       f"Hợp đồng {hd['ma']} ({hd['goi']}) của {hd['ten_khach']} đã hoàn thành. Giá trị {_vnd(hd['gia_tri'])}đ, đã thu "
                       f"{_vnd(ct['thu'])}đ, đã chi {_vnd(ct['chi'])}đ, còn nợ {_vnd(ct['con_no'])}đ, lãi gộp {_vnd(ct['lai_gop'])}đ. "
                       f"Dùng skill {VAI_PHONG['doi_soat'][1]}: kết luận đủ/nợ/hoàn, nêu chênh lệch và 1 đến 3 việc cần làm.",
                       chat_id)


def chi_tiet_hop_dong(hid: int) -> dict:
    def f(db):
        t = db.execute("SELECT COALESCE(SUM(so_tien),0) FROM so_quy WHERE hop_dong_id=? AND loai='thu' AND trang_thai='da_ghi'", (int(hid),)).fetchone()[0]
        c = db.execute("SELECT COALESCE(SUM(so_tien),0) FROM so_quy WHERE hop_dong_id=? AND loai='chi' AND trang_thai='da_ghi'", (int(hid),)).fetchone()[0]
        g = db.execute("SELECT gia_tri FROM so_hop_dong WHERE id=?", (int(hid),)).fetchone()
        return float(t), float(c), float(g[0] if g else 0)
    t, c, g = _dung(f)
    return {"thu": t, "chi": c, "lai_gop": t - c, "con_no": max(0.0, g - t)}


def ds_hop_dong(trang_thai: str = "", q: str = "") -> List[dict]:
    rows = _dung(lambda db: _rows(db.execute("SELECT * FROM so_hop_dong ORDER BY id DESC").fetchall()))
    out = []
    t = _ascii(q).lower()
    for h in rows:
        if trang_thai and h["trang_thai"] != trang_thai:
            continue
        if t and t not in _ascii(h["ten_khach"] + " " + h["goi"] + " " + h["ma"] + " " + h["sdt"]).lower():
            continue
        h.update(chi_tiet_hop_dong(h["id"]))
        h["lich"] = _lich_hop_dong(h)
        out.append(h)
    return out


def luu_bao_gia(data: dict, by: str = "") -> dict:
    bid = int(data.get("id") or 0)
    dong = []
    for x in (data.get("dong") or []):
        ten = _s(x.get("ten"), 160)
        if ten:
            dong.append({"ten": ten, "sl": max(0.0, float(x.get("sl") or 1)), "don_gia": tien(x.get("don_gia", 0))})
    if not dong:
        raise ValueError("Báo giá cần ít nhất một dòng hàng hóa hoặc dịch vụ")
    giam = max(0.0, min(100.0, float(data.get("giam") or 0)))
    vat = max(0.0, min(30.0, float(data.get("vat") or 0)))
    tong = sum(d["sl"] * d["don_gia"] for d in dong) * (1 - giam / 100) * (1 + vat / 100)
    ten_khach, sdt = _s(data.get("ten_khach"), 120), crm.chuan_sdt(data.get("sdt") or "")
    ts = data.get("trang_thai") if data.get("trang_thai") in ("nhap", "da_gui", "chap_nhan", "huy") else "nhap"
    hd = None
    if data.get("hop_dong"):
        hd = tim_hop_dong(data["hop_dong"])[0]
    hid = hd["id"] if hd else (int(data.get("hop_dong_id") or 0) or None)

    def f(db):
        if bid:
            db.execute("UPDATE so_bao_gia SET ten_khach=?, sdt=?, dong_json=?, giam=?, vat=?, tong=?, trang_thai=?, ghi_chu=?, hop_dong_id=? WHERE id=?",
                       (ten_khach, sdt, json.dumps(dong, ensure_ascii=False), giam, vat, tong, ts, _s(data.get("ghi_chu"), 400), hid, bid))
            db.commit()
            return bid
        so = _ma(db, "so_bao_gia", "BG")
        cur = db.execute("INSERT INTO so_bao_gia(so, hop_dong_id, ten_khach, sdt, dong_json, giam, vat, tong, trang_thai, ghi_chu, ngay, created_at)"
                         " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                         (so, hid, ten_khach, sdt, json.dumps(dong, ensure_ascii=False), giam, vat, tong, ts,
                          _s(data.get("ghi_chu"), 400), _homnay(), time.time()))
        db.commit()
        return int(cur.lastrowid)
    i = _dung(f)
    ghi_hoat_dong(hd["brain"] if hd and hd.get("brain") else VAI_PHONG["sales"][0],
                  f"{'Sửa' if bid else 'Lập'} báo giá cho {ten_khach or 'khách'} {_vnd(tong)}đ", "bao_gia", i,
                  skill=VAI_PHONG["sales"][1])
    return lay_bao_gia(i)


def lay_bao_gia(bid: int) -> Optional[dict]:
    r = _dung(lambda db: db.execute("SELECT * FROM so_bao_gia WHERE id=?", (int(bid),)).fetchone())
    if not r:
        return None
    d = dict(r)
    d["dong"] = json.loads(d.pop("dong_json") or "[]")
    return d


def ds_bao_gia() -> List[dict]:
    ids = _dung(lambda db: [r[0] for r in db.execute("SELECT id FROM so_bao_gia ORDER BY id DESC").fetchall()])
    return [lay_bao_gia(i) for i in ids]


def doi_trang_thai_bg(bid: int, ts: str, by: str = "") -> dict:
    if ts not in ("nhap", "da_gui", "chap_nhan", "huy"):
        raise ValueError("Trạng thái báo giá không hợp lệ")
    bg = lay_bao_gia(bid)
    if not bg:
        raise ValueError("Không thấy báo giá")
    _dung(lambda db: (db.execute("UPDATE so_bao_gia SET trang_thai=? WHERE id=?", (ts, int(bid))), db.commit()))
    if ts == "chap_nhan" and bg.get("hop_dong_id"):
        doi_trang_thai_hd(bg["hop_dong_id"], "da_ky", by)
    return lay_bao_gia(bid)


# ---------------------------------------------------------------- duyệt chi, sổ quỹ
def duyet_quy(qid: int, quyet: str, by: str) -> dict:
    if quyet not in ("duyet", "tu_choi"):
        raise ValueError("quyet phải là duyet hoặc tu_choi")
    r = _dung(lambda db: db.execute("SELECT * FROM so_quy WHERE id=?", (int(qid),)).fetchone())
    if not r:
        raise ValueError("Không thấy phiếu")
    if r["trang_thai"] != "cho_duyet":
        raise ValueError("Phiếu này không ở trạng thái chờ duyệt")
    ts = "da_ghi" if quyet == "duyet" else "tu_choi"
    _dung(lambda db: (db.execute("UPDATE so_quy SET trang_thai=?, quyet_boi=?, quyet_luc=? WHERE id=?", (ts, by, time.time(), int(qid))), db.commit()))
    ghi_hoat_dong(VAI_PHONG["chi"][0], f"{'Chủ duyệt' if quyet == 'duyet' else 'Chủ từ chối'} phiếu chi {_vnd(r['so_tien'])}đ ({r['dien_giai'] or r['hang_muc']})",
                  "chi", qid)
    return dict(_dung(lambda db: db.execute("SELECT * FROM so_quy WHERE id=?", (int(qid),)).fetchone()))


def ds_quy(ky: str = "", loai: str = "", trang_thai: str = "", limit: int = 300) -> List[dict]:
    where, args = ["1=1"], []
    if ky and ky != "all":
        where.append("q.ngay LIKE ?")
        args.append(ky + "%")
    if loai in ("thu", "chi"):
        where.append("q.loai=?")
        args.append(loai)
    if trang_thai:
        where.append("q.trang_thai=?")
        args.append(trang_thai)
    sql = ("SELECT q.*, h.ma AS hop_dong_ma, h.ten_khach AS hop_dong_khach FROM so_quy q LEFT JOIN so_hop_dong h ON h.id=q.hop_dong_id"
           " WHERE " + " AND ".join(where) + " ORDER BY q.ngay DESC, q.id DESC LIMIT ?")
    return _dung(lambda db: _rows(db.execute(sql, args + [int(limit)]).fetchall()))


def xoa_quy(qid: int) -> bool:
    return bool(_dung(lambda db: (db.execute("DELETE FROM so_quy WHERE id=?", (int(qid),)), db.commit())))


# ---------------------------------------------------------------- nhân sự, lương
def luu_nhan_su(data: dict) -> dict:
    nid = int(data.get("id") or 0)
    ten = _s(data.get("ten"), 120)
    if not ten:
        raise ValueError("Nhân sự cần họ tên")
    vai = data.get("vai") if data.get("vai") in VAI_HOP_LE else "khac"
    ty = data.get("ty_le")
    ty = None if ty in (None, "") else max(0.0, min(100.0, float(ty)))
    luong = tien(data.get("luong_cb", 0))

    def f(db):
        if nid:
            db.execute("UPDATE so_nhan_su SET ten=?, chuc_vu=?, vai=?, phong_ban=?, sdt=?, luong_cb=?, ty_le=?, nghi=? WHERE id=?",
                       (ten, _s(data.get("chuc_vu"), 80), vai, _s(data.get("phong_ban"), 80), crm.chuan_sdt(data.get("sdt") or ""),
                        luong, ty, 1 if data.get("nghi") else 0, nid))
            db.commit()
            return nid
        cur = db.execute("INSERT INTO so_nhan_su(ten, chuc_vu, vai, phong_ban, sdt, luong_cb, ty_le, nghi, mau, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (ten, _s(data.get("chuc_vu"), 80), vai, _s(data.get("phong_ban"), 80), crm.chuan_sdt(data.get("sdt") or ""),
                          luong, ty, 1 if data.get("nghi") else 0, 1 if data.get("mau") else 0, time.time()))
        db.commit()
        return int(cur.lastrowid)
    i = _dung(f)
    return dict(_dung(lambda db: db.execute("SELECT * FROM so_nhan_su WHERE id=?", (i,)).fetchone()))


def ds_nhan_su() -> List[dict]:
    return _dung(lambda db: _rows(db.execute("SELECT * FROM so_nhan_su ORDER BY nghi, id").fetchall()))


def xoa_nhan_su(nid: int) -> None:
    def f(db):
        db.execute("DELETE FROM so_phan_cong WHERE nhan_su_id=?", (int(nid),))
        db.execute("DELETE FROM so_giao_viec WHERE nhan_su_id=?", (int(nid),))
        db.execute("DELETE FROM so_nhan_su WHERE id=?", (int(nid),))
        db.commit()
    _dung(f)


def phan_cong(hid: int, ten: Any, vai: str = "") -> dict:
    t = _ascii(ten).lower().strip()
    if not t:
        raise ValueError("Phân công cần tên nhân sự")
    ns = [n for n in ds_nhan_su() if not n["nghi"] and t in _ascii(n["ten"]).lower()]
    if not ns:
        raise ValueError(f"Không thấy nhân sự \"{ten}\"")
    n = ns[0]
    v = vai if vai in VAI_HOP_LE else n["vai"]
    _dung(lambda db: (db.execute("INSERT OR REPLACE INTO so_phan_cong(hop_dong_id, nhan_su_id, vai) VALUES(?,?,?)", (int(hid), n["id"], v)), db.commit()))
    hd = lay_hop_dong(hid) or {}
    ghi_hoat_dong(VAI_PHONG["nhan_su"][0], f"Phân công {n['ten']} ({v}) vào hợp đồng {hd.get('ma', hid)}", "phan_cong", hid)
    return {"loai": "phan_cong", "hop_dong": hd.get("ma"), "nhan_su": n["ten"], "vai": v,
            "tom_tat": f"Phân công {n['ten']} ({v}) vào hợp đồng {hd.get('ma', hid)}."}


def go_phan_cong(hid: int, nid: int) -> None:
    _dung(lambda db: (db.execute("DELETE FROM so_phan_cong WHERE hop_dong_id=? AND nhan_su_id=?", (int(hid), int(nid))), db.commit()))


# ---------------------------------------------------------------- danh mục việc và chia việc
TRANG_THAI_GV = ("todo", "doing", "done")


def _nap_h2o(db, ghi_de: bool = False) -> int:
    n = 0
    for ma, nhom, ten, phi, hh, ngay in CONG_VIEC_H2O:
        cur = db.execute("SELECT id FROM so_cong_viec WHERE ma_phong=? AND ten=?", (ma, ten)).fetchone()
        if cur and not ghi_de:
            continue
        if cur:
            db.execute("UPDATE so_cong_viec SET nhom=?, phi_them=?, hoa_hong=?, so_ngay=? WHERE id=?", (nhom, phi, hh, ngay, cur["id"]))
        else:
            db.execute("INSERT INTO so_cong_viec(ma_phong, nhom, ten, phi_them, hoa_hong, so_ngay, ap_dung, created_at) VALUES(?,?,?,?,?,?,1,?)",
                       (ma, nhom, ten, phi, hh, ngay, time.time()))
        n += 1
    db.commit()
    return n


def nap_cong_viec_h2o(ghi_de: bool = False) -> int:
    """Nạp bảng việc và hoa hồng của H2O. Mặc định chỉ thêm dòng còn thiếu, không đè số chủ đã sửa."""
    return _dung(lambda db: _nap_h2o(db, ghi_de))


def ds_cong_viec() -> List[dict]:
    def f(db):
        # Lần đầu dùng thì tự nạp bảng của chủ một lần; xóa hết sau đó sẽ không bị nạp lại.
        if not db.execute("SELECT 1 FROM so_cau_hinh WHERE key='cv_da_nap'").fetchone():
            _nap_h2o(db)
            db.execute("INSERT OR REPLACE INTO so_cau_hinh(key,value) VALUES('cv_da_nap','1')")
            db.commit()
        return _rows(db.execute("SELECT * FROM so_cong_viec ORDER BY ma_phong, id").fetchall())
    out = _dung(f)
    for r in out:
        r["phong_ten"] = MA_PHONG.get(r["ma_phong"], (r["ma_phong"], "khac"))[0]
        r["vai_goi_y"] = MA_PHONG.get(r["ma_phong"], ("", "khac"))[1]
    return out


def luu_cong_viec(data: dict) -> dict:
    cid = int(data.get("id") or 0)
    ma = _ascii(data.get("ma_phong")).upper().strip().replace(" ", "")[:20]
    ten = _s(data.get("ten"), 160)
    if not ma or not ten:
        raise ValueError("Việc cần mã phòng và tên việc")
    nhom = _s(data.get("nhom"), 80)
    phi, hh = tien(data.get("phi_them", 0)), tien(data.get("hoa_hong", 0))
    ngay = max(1, min(365, int(float(data.get("so_ngay") or 1))))
    ap = 0 if data.get("ap_dung") in (0, "0", False, "false") else 1

    def f(db):
        if cid:
            db.execute("UPDATE so_cong_viec SET ma_phong=?, nhom=?, ten=?, phi_them=?, hoa_hong=?, so_ngay=?, ap_dung=? WHERE id=?",
                       (ma, nhom, ten, phi, hh, ngay, ap, cid))
            db.commit()
            return cid
        if db.execute("SELECT 1 FROM so_cong_viec WHERE ma_phong=? AND ten=?", (ma, ten)).fetchone():
            raise ValueError(f"Phòng {ma} đã có việc \"{ten}\"")
        cur = db.execute("INSERT INTO so_cong_viec(ma_phong, nhom, ten, phi_them, hoa_hong, so_ngay, ap_dung, created_at) VALUES(?,?,?,?,?,?,?,?)",
                         (ma, nhom, ten, phi, hh, ngay, ap, time.time()))
        db.commit()
        return int(cur.lastrowid)
    try:
        i = _dung(f)
    except sqlite3.IntegrityError:
        raise ValueError(f"Phòng {ma} đã có việc \"{ten}\"")
    return dict(_dung(lambda db: db.execute("SELECT * FROM so_cong_viec WHERE id=?", (i,)).fetchone()))


def xoa_cong_viec(cid: int) -> None:
    """Xóa khỏi danh mục; các việc đã chia giữ nguyên số tiền đã chốt lúc chia."""
    _dung(lambda db: (db.execute("DELETE FROM so_cong_viec WHERE id=?", (int(cid),)), db.commit()))


def tim_cong_viec(ten: Any, ma_phong: str = "") -> dict:
    t = _ascii(ten).lower().strip()
    if not t:
        raise ValueError("Cần tên đầu việc")
    ds = [c for c in ds_cong_viec() if c["ap_dung"] and (not ma_phong or c["ma_phong"] == ma_phong.upper())]
    ex = [c for c in ds if _ascii(c["ten"]).lower() == t]
    if len(ex) == 1:
        return ex[0]
    kq = ex or [c for c in ds if t in _ascii(c["ten"]).lower()]
    if len(kq) == 1:
        return kq[0]
    if not kq:
        raise ValueError(f"Không thấy đầu việc \"{ten}\" trong bảng hoa hồng")
    raise ValueError("Có nhiều việc khớp \"" + str(ten) + "\": " + "; ".join(f"{c['ten']} ({c['ma_phong']})" for c in kq[:6]) + ". Nói rõ hơn hoặc kèm mã phòng.")


# ---------------------------------------------------------------- bảng giá dịch vụ
def lich_thanh_toan(gia: float, coc1_pct: float = 0, coc2_pct: float = 0) -> dict:
    """Cọc lần 1, cọc lần 2 và phần thanh toán cuối của một khoản `gia`, cùng cách sheet của chủ tính."""
    gia = max(0.0, float(gia or 0))
    c1 = round(gia * max(0.0, min(100.0, float(coc1_pct or 0))) / 100.0)
    c2 = round((gia - c1) * max(0.0, min(100.0, float(coc2_pct or 0))) / 100.0)
    return {"coc1": c1, "coc2": c2, "con_lai": gia - c1 - c2}


def _nap_dv(db, ghi_de: bool = False) -> int:
    n = 0
    for ma, loai, goi, gia, c1, c2 in DICH_VU_H2O:
        cur = db.execute("SELECT id FROM so_dich_vu WHERE ma=?", (ma,)).fetchone()
        if cur and not ghi_de:
            continue
        if cur:
            db.execute("UPDATE so_dich_vu SET loai=?, goi=?, don_gia=?, coc1_pct=?, coc2_pct=? WHERE id=?", (loai, goi, gia, c1, c2, cur["id"]))
        else:
            db.execute("INSERT INTO so_dich_vu(ma, loai, goi, don_gia, coc1_pct, coc2_pct, ap_dung, created_at) VALUES(?,?,?,?,?,?,1,?)",
                       (ma, loai, goi, gia, c1, c2, time.time()))
        n += 1
    db.commit()
    return n


def nap_dich_vu_h2o(ghi_de: bool = False) -> int:
    """Nạp bảng giá H2O. Mặc định chỉ thêm mã còn thiếu, không đè giá chủ đã sửa."""
    return _dung(lambda db: _nap_dv(db, ghi_de))


def ds_dich_vu() -> List[dict]:
    def f(db):
        # Lần đầu dùng thì tự nạp bảng giá của chủ một lần; xóa hết sau đó sẽ không bị nạp lại.
        if not db.execute("SELECT 1 FROM so_cau_hinh WHERE key='dv_da_nap'").fetchone():
            _nap_dv(db)
            db.execute("INSERT OR REPLACE INTO so_cau_hinh(key,value) VALUES('dv_da_nap','1')")
            db.commit()
        return _rows(db.execute("SELECT * FROM so_dich_vu ORDER BY id").fetchall())
    out = _dung(f)
    for r in out:
        r.update(lich_thanh_toan(r["don_gia"], r["coc1_pct"], r["coc2_pct"]))
    return out


def luu_dich_vu(data: dict) -> dict:
    did = int(data.get("id") or 0)
    ma = re.sub(r"\s+", "", _ascii(data.get("ma")).upper())[:30]
    goi = _s(data.get("goi"), 160)
    if not ma or not goi:
        raise ValueError("Dịch vụ cần mã và tên gói")
    loai = _s(data.get("loai"), 80)
    gia = tien(data.get("don_gia", 0))
    c1 = max(0.0, min(100.0, float(data.get("coc1_pct") or 0)))
    c2 = max(0.0, min(100.0, float(data.get("coc2_pct") or 0)))
    ap = 0 if data.get("ap_dung") in (0, "0", False, "false") else 1

    def f(db):
        if did:
            db.execute("UPDATE so_dich_vu SET ma=?, loai=?, goi=?, don_gia=?, coc1_pct=?, coc2_pct=?, ap_dung=? WHERE id=?", (ma, loai, goi, gia, c1, c2, ap, did))
            db.commit()
            return did
        cur = db.execute("INSERT INTO so_dich_vu(ma, loai, goi, don_gia, coc1_pct, coc2_pct, ap_dung, created_at) VALUES(?,?,?,?,?,?,?,?)",
                         (ma, loai, goi, gia, c1, c2, ap, time.time()))
        db.commit()
        return int(cur.lastrowid)
    try:
        i = _dung(f)
    except sqlite3.IntegrityError:
        raise ValueError(f"Mã {ma} đã có trong bảng giá")
    return next(d for d in ds_dich_vu() if d["id"] == i)


def xoa_dich_vu(did: int) -> None:
    """Xóa khỏi bảng giá; hợp đồng đã lập giữ nguyên giá trị."""
    _dung(lambda db: (db.execute("DELETE FROM so_dich_vu WHERE id=?", (int(did),)), db.commit()))


def tim_dich_vu(ten: Any) -> Optional[dict]:
    """Khớp CHÍNH XÁC theo mã hoặc tên gói (không phân biệt hoa thường, dấu). Không đoán gần đúng để khỏi báo nhầm giá."""
    t = _ascii(ten).lower().strip()
    if not t:
        return None
    ds = [d for d in ds_dich_vu() if d["ap_dung"]]
    for d in ds:
        if _ascii(d["ma"]).lower() == t:
            return d
    kq = [d for d in ds if _ascii(d["goi"]).lower() == t]
    return kq[0] if len(kq) == 1 else None


def goi_y_dich_vu(tu_khoa: str = "", limit: int = 12) -> List[dict]:
    """Tìm theo từ khóa trong mã, loại, tên gói (Joyce dùng khi khách hỏi giá)."""
    t = _ascii(tu_khoa).lower().strip()
    ds = [d for d in ds_dich_vu() if d["ap_dung"]]
    if not t:
        return ds[:limit]
    tu = t.split()
    return [d for d in ds if all(x in _ascii(d["ma"] + " " + d["loai"] + " " + d["goi"]).lower() for x in tu)][:limit]


def _lich_hop_dong(h: dict) -> Optional[dict]:
    """Lịch cọc/thanh toán của hợp đồng đặt từ bảng giá, và bước đang chờ khách trả."""
    if not h.get("dv_ma"):
        return None
    dv = next((d for d in ds_dich_vu() if d["ma"] == h["dv_ma"]), None)
    if not dv or (not dv["coc1_pct"] and not dv["coc2_pct"]):
        return None
    lich = lich_thanh_toan(h["gia_tri"], dv["coc1_pct"], dv["coc2_pct"])
    thu = h.get("thu", 0)
    if thu >= h["gia_tri"] > 0:
        buoc = ""
    elif thu < lich["coc1"]:
        buoc = "Cọc lần 1"
    elif thu < lich["coc1"] + lich["coc2"]:
        buoc = "Cọc lần 2"
    else:
        buoc = "Thanh toán"
    lich["buoc_tiep"] = buoc
    lich["can_thu"] = {"Cọc lần 1": lich["coc1"], "Cọc lần 2": lich["coc1"] + lich["coc2"], "Thanh toán": h["gia_tri"]}.get(buoc, 0) - thu if buoc else 0
    return lich


def giao_viec(hid: int, cong_viec: Any, ten: Any, so_luong: Any = 1, han: str = "", ma_phong: str = "") -> dict:
    hd = lay_hop_dong(hid)
    if not hd or hd["trang_thai"] == "huy":
        raise ValueError("Không thấy hợp đồng để chia việc")
    cv = tim_cong_viec(cong_viec, ma_phong)
    t = _ascii(ten).lower().strip()
    if not t:
        raise ValueError("Chia việc cần tên nhân sự")
    ns = [n for n in ds_nhan_su() if not n["nghi"] and t in _ascii(n["ten"]).lower()]
    if not ns:
        raise ValueError(f"Không thấy nhân sự \"{ten}\"")
    n = ns[0]
    try:
        sl = float(so_luong or 1)
    except (TypeError, ValueError):
        sl = 1.0
    sl = max(0.0, min(1000.0, sl)) or 1.0
    han = _s(han, 10)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", han):
        han = (datetime.now() + timedelta(days=int(cv["so_ngay"] or 1))).strftime("%Y-%m-%d")

    def f(db):
        r = db.execute("SELECT id FROM so_giao_viec WHERE hop_dong_id=? AND cong_viec_id=? AND nhan_su_id=?", (hd["id"], cv["id"], n["id"])).fetchone()
        if r:   # gửi lại cùng câu thì cập nhật, không cộng dồn
            db.execute("UPDATE so_giao_viec SET so_luong=?, han=?, hoa_hong=?, phi_them=? WHERE id=?", (sl, han, cv["hoa_hong"], cv["phi_them"], r["id"]))
            db.commit()
            return r["id"]
        cur = db.execute("INSERT INTO so_giao_viec(hop_dong_id, cong_viec_id, nhan_su_id, ten, ma_phong, hoa_hong, phi_them, so_luong, han, trang_thai, created_at)"
                         " VALUES(?,?,?,?,?,?,?,?,?,'todo',?)", (hd["id"], cv["id"], n["id"], cv["ten"], cv["ma_phong"], cv["hoa_hong"], cv["phi_them"], sl, han, time.time()))
        db.commit()
        return int(cur.lastrowid)
    gid = _dung(f)
    tien_hh = round(cv["hoa_hong"] * sl)
    h = ghi_hoat_dong(VAI_PHONG["nhan_su"][0], f"Chia việc \"{cv['ten']}\" cho {n['ten']} ({hd['ma']}), hoa hồng {_vnd(tien_hh)}", "giao_viec", gid)
    return {"loai": "giao_viec", "id": gid, "hop_dong": hd["ma"], "nhan_su": n["ten"], "cong_viec": cv["ten"], "hoa_hong": tien_hh, "han": han,
            "phong": h["phong"], "agent": h["agent"],
            "tom_tat": f"{h['agent'] or h['phong']}: chia \"{cv['ten']}\" cho {n['ten']} ({hd['ma']}), hoa hồng {_vnd(tien_hh)}."}


def ds_giao_viec(hid: int = 0) -> List[dict]:
    sql = ("SELECT g.*, h.ma AS hop_dong_ma, h.ten_khach, h.trang_thai AS hd_trang_thai, n.ten AS nhan_su_ten FROM so_giao_viec g"
           " LEFT JOIN so_hop_dong h ON h.id=g.hop_dong_id LEFT JOIN so_nhan_su n ON n.id=g.nhan_su_id")
    if hid:
        return _dung(lambda db: _rows(db.execute(sql + " WHERE g.hop_dong_id=? ORDER BY g.id", (int(hid),)).fetchall()))
    return _dung(lambda db: _rows(db.execute(sql + " ORDER BY g.id DESC LIMIT 500").fetchall()))


def doi_giao_viec(gid: int, ts: str) -> None:
    if ts not in TRANG_THAI_GV:
        raise ValueError("Trạng thái không hợp lệ")
    _dung(lambda db: (db.execute("UPDATE so_giao_viec SET trang_thai=? WHERE id=?", (ts, int(gid))), db.commit()))


def go_giao_viec(gid: int) -> None:
    _dung(lambda db: (db.execute("DELETE FROM so_giao_viec WHERE id=?", (int(gid),)), db.commit()))


def hoa_hong(ky: str = "") -> List[dict]:
    """Hoa hồng tạm tính theo kỳ (tháng ký hợp đồng). Chỉ hợp đồng Đã ký hoặc Hoàn thành mới có hoa hồng.
    Hai nguồn: số tiền cố định theo từng đầu việc đã chia (loai=cong_viec), và phần trăm theo vai (loai=ty_le).
    Người đã được chia việc trong một hợp đồng thì chỉ hưởng theo việc ở hợp đồng đó, không cộng thêm phần trăm."""
    cfg = cau_hinh()
    ky = ky or _ky()
    pcs = _dung(lambda db: _rows(db.execute(
        "SELECT p.hop_dong_id, p.nhan_su_id, p.vai, n.ten, n.ty_le, h.ma, h.ten_khach, h.gia_tri, h.ngay_ky, h.ngay, h.trang_thai"
        " FROM so_phan_cong p JOIN so_nhan_su n ON n.id=p.nhan_su_id JOIN so_hop_dong h ON h.id=p.hop_dong_id"
        " WHERE h.trang_thai IN ('da_ky','hoan_thanh')").fetchall()))
    gvs = _dung(lambda db: _rows(db.execute(
        "SELECT g.*, n.ten AS nhan_su_ten, n.vai AS nhan_su_vai, h.ma, h.ten_khach, h.ngay_ky, h.ngay, h.trang_thai AS hd_ts"
        " FROM so_giao_viec g JOIN so_nhan_su n ON n.id=g.nhan_su_id JOIN so_hop_dong h ON h.id=g.hop_dong_id"
        " WHERE h.trang_thai IN ('da_ky','hoan_thanh')").fetchall()))
    co_viec = {(g["hop_dong_id"], g["nhan_su_id"]) for g in gvs}
    out = []
    for p in pcs:
        if ky != "all" and _ky(p["ngay_ky"] or p["ngay"]) != ky:
            continue
        if (p["hop_dong_id"], p["nhan_su_id"]) in co_viec:
            continue
        ct = chi_tiet_hop_dong(p["hop_dong_id"])
        co_so = max(0.0, ct["lai_gop"]) if cfg["co_so_hh"] == "lai_gop" else ct["thu"]
        ty = p["ty_le"] if p["ty_le"] is not None else cfg["ty_le_vai"].get(p["vai"], 0.0)
        out.append({"loai": "ty_le", "hop_dong_id": p["hop_dong_id"], "ma": p["ma"], "ten_khach": p["ten_khach"], "nhan_su_id": p["nhan_su_id"],
                    "ten": p["ten"], "vai": p["vai"], "co_so": co_so, "co_so_loai": cfg["co_so_hh"], "ty_le": ty,
                    "so_tien": round(co_so * ty / 100.0), "trang_thai": p["trang_thai"]})
    for g in gvs:
        if ky != "all" and _ky(g["ngay_ky"] or g["ngay"]) != ky:
            continue
        out.append({"loai": "cong_viec", "hop_dong_id": g["hop_dong_id"], "ma": g["ma"], "ten_khach": g["ten_khach"], "nhan_su_id": g["nhan_su_id"],
                    "ten": g["nhan_su_ten"], "vai": g["nhan_su_vai"], "cong_viec": g["ten"], "ma_phong": g["ma_phong"], "so_luong": g["so_luong"],
                    "don_gia": g["hoa_hong"], "co_so": g["hoa_hong"], "ty_le": None, "so_tien": round(g["hoa_hong"] * g["so_luong"]),
                    "xong": g["trang_thai"] == "done", "trang_thai": g["hd_ts"]})
    return out


def bang_luong(ky: str = "") -> dict:
    ky = ky or _ky()
    hh = hoa_hong(ky)
    dong = []
    for n in ds_nhan_su():
        if n["nghi"]:
            continue
        mine = [x for x in hh if x["nhan_su_id"] == n["id"]]
        tong_hh = sum(x["so_tien"] for x in mine)
        dong.append({"nhan_su_id": n["id"], "ten": n["ten"], "chuc_vu": n["chuc_vu"], "vai": n["vai"], "luong_cb": n["luong_cb"],
                     "hoa_hong": tong_hh, "so_hop_dong": len(mine), "tong": n["luong_cb"] + tong_hh, "chi_tiet": mine})
    return {"ky": ky, "co_so_hh": cau_hinh()["co_so_hh"], "dong": dong, "tong_luong": sum(d["tong"] for d in dong),
            "tong_hoa_hong": sum(d["hoa_hong"] for d in dong)}


NHAN_SU_MAU = [
    ("Trần Minh Anh", "Sales", "sales", "Bán hàng", 7_000_000),
    ("Lê Quốc Huy", "Thợ chụp chính", "chup", "Sản xuất", 8_000_000),
    ("Phạm Thu Hà", "Hậu kỳ và hỗ trợ", "hotro", "Sản xuất", 6_000_000),
]


def nap_mau() -> int:
    if any(n["mau"] for n in ds_nhan_su()):
        return 0
    for ten, cv, vai, pb, luong in NHAN_SU_MAU:
        luu_nhan_su({"ten": ten, "chuc_vu": cv, "vai": vai, "phong_ban": pb, "luong_cb": luong, "mau": True})
    ghi_hoat_dong(VAI_PHONG["nhan_su"][0], f"Nạp {len(NHAN_SU_MAU)} nhân sự mẫu để thử tính lương", "nhan_su", 0)
    return len(NHAN_SU_MAU)


def xoa_mau() -> int:
    ids = [n["id"] for n in ds_nhan_su() if n["mau"]]
    for i in ids:
        xoa_nhan_su(i)
    return len(ids)


# ---------------------------------------------------------------- danh mục đồ, lịch sử thuê đồ
TRANG_THAI_THUE = ("giu_cho", "dang_thue", "da_tra", "huy")      # 1. Giữ chỗ, 2. Đang thuê, 4. Đã trả (như sheet của chủ), Hủy
NGAY_GIAT_MAC_DINH = 3                                             # ngày giặt phơi sau mỗi lần trả, trước khi cho thuê lại
_VAI_THUE_DO = "sales_vay"                                       # phòng nhận việc cho thuê và nhận trả đồ


def _ngay_hop_le(v: Any) -> str:
    x = str(v or "").strip()
    return x if re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) else ""


def _cong_ngay(ngay: str, n: int) -> str:
    return (datetime.strptime(ngay, "%Y-%m-%d") + timedelta(days=n)).strftime("%Y-%m-%d")


def _chuan_ma_do(v: Any) -> str:
    x = _ascii(v).upper().strip()
    x = x.split("--")[0]            # "VAY-CC209--Trắng" (tên đồ trong sheet) -> mã đồ
    return re.sub(r"\s+", "", x)[:40]


def _dmy(ngay: str) -> str:
    return datetime.strptime(ngay, "%Y-%m-%d").strftime("%d/%m/%Y")


def _ngay_giat(db) -> int:
    """Số ngày giặt phơi sau mỗi lần trả. Đọc từ cấu hình ngay_giat nếu có, không thì 3 ngày."""
    r = db.execute("SELECT value FROM so_cau_hinh WHERE key='ngay_giat'").fetchone()
    try:
        return max(0, min(30, int(float(r[0])))) if r else NGAY_GIAT_MAC_DINH
    except (TypeError, ValueError):
        return NGAY_GIAT_MAC_DINH


def _khoang_ban(v: dict, buf: int) -> tuple:
    """Đồ bị chiếm từ ngày thuê đến hết ngày trả (thực tế nếu đã trả, dự kiến nếu chưa), cộng số ngày giặt phơi.
    Trả về (ngày bắt đầu, ngày sẵn sàng cho thuê lại)."""
    het = v["ngay_tra_thuc"] if v["trang_thai"] == "da_tra" and v["ngay_tra_thuc"] else v["ngay_tra_du_kien"]
    return v["ngay_thue"], _cong_ngay(het, buf)


def _thong_bao_trung(ma: str, dung: list, tu: str, den: str, buf: int) -> str:
    chi = []
    for v, het in dung:
        het_thuc = _cong_ngay(het, -buf)
        tt = {"dang_thue": "đang thuê", "giu_cho": "giữ chỗ"}.get(v["trang_thai"], "đã trả, đang giặt phơi")
        chi.append(f"{v['khach']} thuê {_dmy(v['ngay_thue'])} đến {_dmy(het_thuc)} ({tt}, phiếu {v['key']})")
    san = max(het for _, het in dung)
    return (f"Đồ {ma} không cho thuê từ {_dmy(tu)} đến {_dmy(den)} vì trùng lịch: " + "; ".join(chi)
            + f". Sau mỗi lần trả cần {buf} ngày giặt phơi, nên đồ sẵn sàng lại từ {_dmy(san)}. Ngày thuê sớm nhất: {_dmy(san)}.")


def ds_do() -> List[dict]:
    """Danh mục đồ kèm tình trạng tính từ lịch sử thuê: sẵn sàng, đang giặt, giữ chỗ, đang thuê, quá hạn, tạm ngưng."""
    hn = _homnay()

    def f(db):
        it = _rows(db.execute("SELECT * FROM so_do ORDER BY id").fetchall())
        act = _rows(db.execute("SELECT key, ma_do, trang_thai, ngay_thue, ngay_tra_du_kien, khach FROM so_thue_do"
                               " WHERE trang_thai IN ('giu_cho','dang_thue') ORDER BY ngay_thue").fetchall())
        dem = {r[0]: r[1] for r in db.execute("SELECT ma_do, COUNT(*) FROM so_thue_do WHERE trang_thai IN ('dang_thue','da_tra') GROUP BY ma_do").fetchall()}
        tra = {r[0]: r[1] for r in db.execute("SELECT ma_do, MAX(ngay_tra_thuc) FROM so_thue_do WHERE trang_thai='da_tra' AND ngay_tra_thuc!='' GROUP BY ma_do").fetchall()}
        return it, act, dem, tra, _ngay_giat(db)
    it, act, dem, tra, buf = _dung(f)
    for r in it:
        mine = [a for a in act if a["ma_do"] == r["ma_do"]]
        dang = next((a for a in mine if a["trang_thai"] == "dang_thue"), None)
        r["ten_do"] = f"{r['ma_do']}--{r['mau_sac']}" if r["mau_sac"] else r["ma_do"]
        r["so_lan_thue"] = int(dem.get(r["ma_do"], 0))
        r["lich"] = [{"key": a["key"], "trang_thai": a["trang_thai"], "tu": a["ngay_thue"], "den": a["ngay_tra_du_kien"], "khach": a["khach"]} for a in mine]
        r["hien_tai"] = (dang or (mine[0] if mine else {})).get("key", "")
        r["san_lai"] = ""
        if not r["ap_dung"]:
            r["tinh_trang"] = "tam_ngung"
        elif dang:
            r["tinh_trang"] = "qua_han" if dang["ngay_tra_du_kien"] < hn else "dang_thue"
        elif mine:
            r["tinh_trang"] = "giu_cho"
        elif r["ma_do"] in tra and _cong_ngay(tra[r["ma_do"]], buf) > hn:
            r["tinh_trang"] = "dang_giat"
            r["san_lai"] = _cong_ngay(tra[r["ma_do"]], buf)
        else:
            r["tinh_trang"] = "san_sang"
    return it


def luu_do(data: dict) -> dict:
    did = int(data.get("id") or 0)
    ma = _chuan_ma_do(data.get("ma_do"))
    if not ma:
        raise ValueError("Đồ cần mã đồ dùng")
    ma_dv = re.sub(r"\s+", "", _ascii(data.get("ma_dv")).upper())[:30] or re.sub(r"\d.*$", "", ma).rstrip("-")
    dv = next((d for d in ds_dich_vu() if d["ma"] == ma_dv), None)
    nhom = _s(data.get("nhom"), 100) or (dv["goi"] if dv else "")
    gia = tien(data.get("don_gia", 0))
    ap = 0 if data.get("ap_dung") in (0, "0", False, "false") else 1
    vals = (ma_dv, _s(data.get("pb"), 80), ma, nhom, _s(data.get("co"), 20), _s(data.get("mau_sac"), 40),
            _s(data.get("mo_ta"), 300), _s(data.get("hinh"), 400), gia, ap)

    def f(db):
        if did:
            cu = db.execute("SELECT ma_do FROM so_do WHERE id=?", (did,)).fetchone()
            if cu and cu["ma_do"] != ma and db.execute("SELECT 1 FROM so_thue_do WHERE ma_do=?", (cu["ma_do"],)).fetchone():
                raise ValueError("Đồ đã có lịch sử thuê nên không đổi mã được; tạo đồ mới và tạm ngưng đồ cũ")
            db.execute("UPDATE so_do SET ma_dv=?, pb=?, ma_do=?, nhom=?, co=?, mau_sac=?, mo_ta=?, hinh=?, don_gia=?, ap_dung=? WHERE id=?", vals + (did,))
            db.commit()
            return did
        cur = db.execute("INSERT INTO so_do(ma_dv, pb, ma_do, nhom, co, mau_sac, mo_ta, hinh, don_gia, ap_dung, la_mau, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)",
                         vals + (time.time(),))
        db.commit()
        return int(cur.lastrowid)
    try:
        i = _dung(f)
    except sqlite3.IntegrityError:
        raise ValueError(f"Mã đồ {ma} đã có trong danh mục")
    return next(d for d in ds_do() if d["id"] == i)


def xoa_do(did: int) -> None:
    def f(db):
        r = db.execute("SELECT ma_do FROM so_do WHERE id=?", (int(did),)).fetchone()
        if not r:
            return
        if db.execute("SELECT 1 FROM so_thue_do WHERE ma_do=? AND la_mau=0", (r["ma_do"],)).fetchone():
            raise ValueError("Đồ đã có lịch sử thuê thật nên không xóa được; chuyển sang Tạm ngưng")
        db.execute("DELETE FROM so_thue_do WHERE ma_do=?", (r["ma_do"],))
        db.execute("DELETE FROM so_do WHERE id=?", (int(did),))
        db.commit()
    _dung(f)


def _tim_do(x: Any) -> Optional[dict]:
    ma = _chuan_ma_do(x)
    if not ma:
        return None
    ds = ds_do()
    kq = [d for d in ds if d["ma_do"] == ma]
    return kq[0] if kq else None


def _log_thue(brain_vai: str, hanh: str, ref: int, loai: str = "thue_do") -> dict:
    return ghi_hoat_dong(VAI_PHONG[brain_vai][0], hanh, loai, ref)


def _su_kien_thue_do(sk: dict, by: str, chat_id: str, by_info: dict) -> dict:
    it = _tim_do(sk.get("ma_do") or sk.get("do"))
    if not it:
        raise ValueError(f"Không thấy đồ \"{sk.get('ma_do') or sk.get('do') or ''}\" trong danh mục đồ")
    if not it["ap_dung"]:
        raise ValueError(f"Đồ {it['ma_do']} đang tạm ngưng, chưa cho thuê được")
    ref = sk.get("hop_dong") or sk.get("khach_ref") or ""
    hd, canh_bao = tim_hop_dong(ref) if ref else (None, "")
    ten = _s(sk.get("ten_khach") or sk.get("khach") or (hd["ten_khach"] if hd else ""), 120)
    sdt = crm.chuan_sdt(sk.get("sdt") or (hd["sdt"] if hd else "") or "")
    if not (ten or sdt):
        raise ValueError("Cho thuê cần biết khách: hợp đồng, tên hoặc số điện thoại")
    hn = _homnay()
    tu = _ngay_hop_le(sk.get("ngay_thue") or sk.get("ngay")) or hn
    den = _ngay_hop_le(sk.get("ngay_tra") or sk.get("ngay_tra_du_kien")) or tu
    if den < tu:
        raise ValueError("Ngày trả không được trước ngày thuê")
    gia = tien(sk.get("don_gia", 0)) or it["don_gia"]
    if gia <= 0:
        raise ValueError(f"Đồ {it['ma_do']} chưa có giá thuê; nói giá thuê hoặc điền ở Danh mục đồ")
    km = min(tien(sk.get("khuyen_mai", 0)), gia)
    con = gia - km
    ts = sk.get("trang_thai") if sk.get("trang_thai") in ("giu_cho", "dang_thue") else ("dang_thue" if tu <= hn else "giu_cho")
    thu_ngay = sk.get("thu_ngay") in (True, 1, "1", "true", "co", "có")
    key = uuid.uuid4().hex[:8]

    def f(db):
        buf = _ngay_giat(db)
        dung = []
        for v in _rows(db.execute("SELECT * FROM so_thue_do WHERE ma_do=? AND trang_thai IN ('giu_cho','dang_thue','da_tra')",
                                  (it["ma_do"],)).fetchall()):
            bat, het = _khoang_ban(v, buf)
            if tu < het and bat < _cong_ngay(den, buf):   # khoảng thuê mới (kể cả giặt phơi) chạm khoảng đã có
                dung.append((v, het))
        if dung:
            v = dung[0][0]
            if len(dung) == 1 and v["trang_thai"] in ("giu_cho", "dang_thue") and v["ngay_thue"] == tu and (
                    (sdt and v["sdt"] == sdt) or (not sdt and _ascii(v["khach"]).lower() == _ascii(ten).lower())):
                return {"da_co": v}
            raise ValueError(_thong_bao_trung(it["ma_do"], dung, tu, den, buf))
        qh = db.execute("SELECT * FROM so_thue_do WHERE ma_do=? AND trang_thai='dang_thue' AND ngay_tra_du_kien<? AND ngay_thue<=?", (it["ma_do"], hn, tu)).fetchone()
        if qh and tu <= hn:
            raise ValueError(f"Đồ {it['ma_do']} chưa được trả: phiếu {qh['key']} của {qh['khach']} đã quá hạn từ {qh['ngay_tra_du_kien']}")
        cur = db.execute("INSERT INTO so_thue_do(key, hop_dong_id, so_hd, nguoi_tao, ma_do, nhom, ghi_chu, don_gia, khuyen_mai, gia_con_lai, trang_thai,"
                         " ngay_thue, ngay_tra_du_kien, khach, sdt, la_mau, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)",
                         (key, hd["id"] if hd else None, hd["ma"] if hd else _s(sk.get("so_hd"), 40), by, it["ma_do"], it["nhom"],
                          _s(sk.get("ghi_chu"), 300), gia, km, con, ts, tu, den, ten, sdt, time.time()))
        db.commit()
        return {"id": int(cur.lastrowid)}
    r = _dung(f)
    if "da_co" in r:
        v = r["da_co"]
        return {"loai": "thue_do", "id": v["id"], "key": v["key"], "da_co": True,
                "tom_tat": f"Phiếu thuê {it['ma_do']} của {v['khach']} ({v['ngay_thue']}) đã có từ trước, không tạo lại."}
    tid = r["id"]
    h = _log_thue(_VAI_THUE_DO, f"Cho thuê {it['ma_do']} ({it['nhom']}) cho {ten or sdt}, {tu} đến {den}, còn lại {_vnd(con)}đ", tid)
    tom = (f"{h['agent'] or h['phong']}: {'giữ chỗ' if ts == 'giu_cho' else 'cho thuê'} {it['ma_do']} ({it['nhom']}) cho {ten or sdt} "
           f"từ {tu} đến {den}, giá {_vnd(gia)}đ" + (f" giảm {_vnd(km)}đ" if km else "") + f", còn lại {_vnd(con)}đ (phiếu {key})")
    if hd:
        tom += f", gắn hợp đồng {hd['ma']}"
    elif ref:
        tom += f" ({canh_bao or 'chưa gắn được hợp đồng'})"
    ra = {"loai": "thue_do", "id": tid, "key": key, "ma_do": it["ma_do"], "gia_con_lai": con, "trang_thai": ts, "phong": h["phong"], "agent": h["agent"],
          "hop_dong": hd["ma"] if hd else ""}
    if thu_ngay and con > 0:
        q = _su_kien_quy({"loai": "thu", "so_tien": con, "hop_dong": hd["ma"] if hd else sdt, "hang_muc": "Thuê đồ",
                          "dien_giai": f"Thuê {it['ma_do']} phiếu {key}"}, by, chat_id, by_info, "thu")
        _dung(lambda db: (db.execute("UPDATE so_thue_do SET quy_id=? WHERE id=?", (q["id"], tid)), db.commit()))
        ra["thu"] = q["tom_tat"]
        tom += ". " + q["tom_tat"]
    else:
        tom += f". Chưa ghi thu {_vnd(con)}đ."
    ra["tom_tat"] = tom
    return ra


def _phieu_dang_thue(sk: dict) -> dict:
    key = _s(sk.get("key") or sk.get("phieu"), 20).lower()
    ma = _chuan_ma_do(sk.get("ma_do") or sk.get("do"))
    if not key and not ma:
        raise ValueError("Trả đồ cần mã đồ hoặc mã phiếu")
    r = _dung(lambda db: db.execute(
        "SELECT * FROM so_thue_do WHERE " + ("key=?" if key else "ma_do=? AND trang_thai IN ('dang_thue','giu_cho')") + " ORDER BY id DESC",
        (key or ma,)).fetchone())
    if not r:
        raise ValueError(f"Không có phiếu thuê {'mã ' + key if key else 'đang mở của đồ ' + ma}")
    return dict(r)


def _su_kien_tra_do(sk: dict, by: str) -> dict:
    r = _phieu_dang_thue(sk)
    if r["trang_thai"] == "da_tra":
        return {"loai": "tra_do", "id": r["id"], "key": r["key"], "da_co": True, "tom_tat": f"Phiếu {r['key']} ({r['ma_do']}) đã trả từ {r['ngay_tra_thuc']}, không ghi lại."}
    if r["trang_thai"] != "dang_thue":
        raise ValueError(f"Phiếu {r['key']} đang ở trạng thái {'giữ chỗ (chưa giao đồ)' if r['trang_thai'] == 'giu_cho' else 'đã hủy'}, chưa có gì để trả")
    ngay = _ngay_hop_le(sk.get("ngay")) or _homnay()
    _dung(lambda db: (db.execute("UPDATE so_thue_do SET trang_thai='da_tra', ngay_tra_thuc=? WHERE id=?", (ngay, r["id"])), db.commit()))
    tre = (datetime.strptime(ngay, "%Y-%m-%d") - datetime.strptime(r["ngay_tra_du_kien"], "%Y-%m-%d")).days
    h = _log_thue(_VAI_THUE_DO, f"Nhận trả {r['ma_do']} từ {r['khach']}" + (f", trễ {tre} ngày" if tre > 0 else ""), r["id"], "tra_do")
    return {"loai": "tra_do", "id": r["id"], "key": r["key"], "ma_do": r["ma_do"], "tre_ngay": max(0, tre), "phong": h["phong"], "agent": h["agent"],
            "tom_tat": f"{h['agent'] or h['phong']}: nhận trả {r['ma_do']} từ {r['khach']} ngày {ngay}" + (f", TRỄ {tre} ngày so với hạn {r['ngay_tra_du_kien']}" if tre > 0 else ", đúng hạn") + ". Đồ sẵn sàng cho thuê lại."}


def ds_thue_do(trang_thai: str = "") -> List[dict]:
    hn = _homnay()
    sql = ("SELECT t.*, d.mau_sac, d.co FROM so_thue_do t LEFT JOIN so_do d ON d.ma_do=t.ma_do"
           + (" WHERE t.trang_thai=?" if trang_thai else "") + " ORDER BY t.id DESC LIMIT 500")
    out = _dung(lambda db: _rows(db.execute(sql, (trang_thai,) if trang_thai else ()).fetchall()))
    for r in out:
        r["qua_han"] = r["trang_thai"] == "dang_thue" and r["ngay_tra_du_kien"] < hn
        r["tre_ngay"] = (datetime.strptime(hn, "%Y-%m-%d") - datetime.strptime(r["ngay_tra_du_kien"], "%Y-%m-%d")).days if r["qua_han"] else 0
    return out


def doi_trang_thai_thue(tid: int, ts: str, by: str = "") -> dict:
    if ts not in TRANG_THAI_THUE:
        raise ValueError("Trạng thái phiếu thuê không hợp lệ")
    r = _dung(lambda db: db.execute("SELECT * FROM so_thue_do WHERE id=?", (int(tid),)).fetchone())
    if not r:
        raise ValueError("Không thấy phiếu thuê")
    r = dict(r)
    if r["trang_thai"] == ts:
        return r
    if ts == "da_tra":
        return _su_kien_tra_do({"key": r["key"]}, by) and (lay_thue(tid) or {})
    if ts == "dang_thue":
        kt = _dung(lambda db: db.execute("SELECT key, khach FROM so_thue_do WHERE ma_do=? AND trang_thai='dang_thue' AND id!=?", (r["ma_do"], r["id"])).fetchone())
        if kt:
            raise ValueError(f"Đồ {r['ma_do']} đang ở phiếu {kt['key']} của {kt['khach']}, chưa trả nên chưa giao tiếp được")
    _dung(lambda db: (db.execute("UPDATE so_thue_do SET trang_thai=? WHERE id=?", (ts, r["id"])), db.commit()))
    _log_thue(_VAI_THUE_DO, {"dang_thue": f"Giao {r['ma_do']} cho {r['khach']}", "huy": f"Hủy phiếu thuê {r['key']} ({r['ma_do']}, {r['khach']})",
                             "giu_cho": f"Chuyển phiếu {r['key']} về giữ chỗ"}[ts], r["id"])
    return lay_thue(tid) or {}


def lay_thue(tid: int) -> Optional[dict]:
    r = _dung(lambda db: db.execute("SELECT * FROM so_thue_do WHERE id=?", (int(tid),)).fetchone())
    return dict(r) if r else None


def ghi_thu_thue(tid: int, by: str, by_info: Optional[dict] = None) -> dict:
    r = lay_thue(tid)
    if not r:
        raise ValueError("Không thấy phiếu thuê")
    if r["quy_id"]:
        raise ValueError("Phiếu này đã ghi thu rồi")
    if r["trang_thai"] == "huy" or r["gia_con_lai"] <= 0:
        raise ValueError("Phiếu đã hủy hoặc không còn tiền cần thu")
    q = _su_kien_quy({"loai": "thu", "so_tien": r["gia_con_lai"], "hop_dong": r["so_hd"] or r["sdt"], "hang_muc": "Thuê đồ",
                      "dien_giai": f"Thuê {r['ma_do']} phiếu {r['key']}"}, by, "", by_info or {}, "thu")
    _dung(lambda db: (db.execute("UPDATE so_thue_do SET quy_id=? WHERE id=?", (q["id"], int(tid))), db.commit()))
    return q


def xoa_thue_do(tid: int) -> None:
    r = lay_thue(tid)
    if r and not r["la_mau"] and r["trang_thai"] != "huy":
        raise ValueError("Chỉ xóa được phiếu đã hủy hoặc dữ liệu mẫu; phiếu thật hãy chuyển sang Hủy")
    _dung(lambda db: (db.execute("DELETE FROM so_thue_do WHERE id=?", (int(tid),)), db.commit()))


def goi_y_do(tu_khoa: str = "", limit: int = 10) -> List[dict]:
    t = _ascii(tu_khoa).lower().split()
    ds = ds_do()
    if t:
        ds = [d for d in ds if all(x in _ascii(d["ma_do"] + " " + d["nhom"] + " " + d["mau_sac"] + " " + d["co"] + " " + d["ma_dv"]).lower() for x in t)]
    return ds[:limit]


def _mau_do_ngay(n: int) -> str:
    return _cong_ngay(_homnay(), n)


def nap_mau_do() -> dict:
    """5 món đồ và 5 phiếu thuê MẪU (đánh dấu để xóa gọn), dùng thử luồng thuê và trả."""
    if any(d["la_mau"] for d in ds_do()):
        return {"do": 0, "phieu": 0}
    co_san = {d["ma_do"] for d in ds_do()}
    items = [("VAY-CC", "VAY-CC209", "Váy cao cấp", "M", "Trắng", 7000000), ("VAY-CC", "VAY-CC211", "Váy cao cấp", "S", "Trắng", 7000000),
             ("VAY-TK", "VAY-TK67", "Váy thiết kế", "M", "Trắng", 2450000), ("VEST", "VEST-01", "Áo vest cao cấp", "L", "Đen", 500000),
             ("ADCD", "ADCD-05", "Áo dài cô dâu", "M", "Đỏ", 500000)]
    items = [x for x in items if x[1] not in co_san]       # món đã có (kể cả đã thuê thật) thì giữ nguyên, không đè
    for ma_dv, ma, nhom, co, mau, gia in items:
        d = luu_do({"ma_dv": ma_dv, "pb": "Tư vấn váy", "ma_do": ma, "nhom": nhom, "co": co, "mau_sac": mau, "don_gia": gia, "mo_ta": "Đồ mẫu để thử luồng thuê và trả"})
        _dung(lambda db, i=d["id"]: (db.execute("UPDATE so_do SET la_mau=1 WHERE id=?", (i,)), db.commit()))
    ph = [("VAY-CC209", "Nguyễn Thảo Vân", "0900000001", -20, -19, 3150000, "da_tra", -19), ("VAY-CC211", "Lan Anh Chung", "0900000002", -12, -11, 0, "da_tra", -11),
          ("VEST-01", "Quỳnh Anh", "0900000003", -6, -5, 0, "da_tra", -4), ("VAY-TK67", "Dung Tính", "0900000004", -1, 1, 0, "dang_thue", None),
          ("VAY-CC209", "Hoa Thành", "0900000005", 10, 11, 1000000, "giu_cho", None)]
    ph = [x for x in ph if x[0] not in co_san]
    gia = {m: g for _, m, _, _, _, g in items}
    nhom = {m: n for _, m, n, _, _, _ in items}

    def f(db):
        for i, (ma, ten, sdt, a, b, km, ts, tra) in enumerate(ph, 1):
            db.execute("INSERT INTO so_thue_do(key, hop_dong_id, so_hd, nguoi_tao, ma_do, nhom, ghi_chu, don_gia, khuyen_mai, gia_con_lai, trang_thai,"
                       " ngay_thue, ngay_tra_du_kien, ngay_tra_thuc, khach, sdt, la_mau, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
                       (f"mau{i:04d}", None, f"MẪU-{i:02d}", "Joyce (mẫu)", ma, nhom[ma], "", gia[ma], km, gia[ma] - km, ts, _mau_do_ngay(a), _mau_do_ngay(b),
                        _mau_do_ngay(tra) if tra is not None else "", ten, sdt, time.time()))
        db.commit()
    _dung(f)
    _log_thue(_VAI_THUE_DO, f"Nạp {len(items)} món đồ và {len(ph)} phiếu thuê mẫu để thử luồng", 0)
    return {"do": len(items), "phieu": len(ph)}


def xoa_mau_do() -> dict:
    def f(db):
        p = db.execute("DELETE FROM so_thue_do WHERE la_mau=1").rowcount
        mau = [r["ma_do"] for r in db.execute("SELECT ma_do FROM so_do WHERE la_mau=1").fetchall()]
        d = 0
        for ma in mau:
            if db.execute("SELECT 1 FROM so_thue_do WHERE ma_do=?", (ma,)).fetchone():     # đã có phiếu thật: giữ lại, bỏ nhãn mẫu
                db.execute("UPDATE so_do SET la_mau=0 WHERE ma_do=?", (ma,))
            else:
                db.execute("DELETE FROM so_do WHERE ma_do=?", (ma,))
                d += 1
        db.commit()
        return {"do": d, "phieu": p}
    return _dung(f)


# ---------------------------------------------------------------- việc
def ds_viec() -> List[dict]:
    return _dung(lambda db: _rows(db.execute(
        "SELECT v.*, h.ma AS hop_dong_ma FROM so_viec v LEFT JOIN so_hop_dong h ON h.id=v.hop_dong_id ORDER BY v.id DESC").fetchall()))


def doi_buoc_viec(vid: int, ts: str) -> None:
    if ts not in TRANG_THAI_VIEC:
        raise ValueError("Trạng thái việc không hợp lệ")
    _dung(lambda db: (db.execute("UPDATE so_viec SET trang_thai=? WHERE id=?", (ts, int(vid))), db.commit()))


def xoa_viec(vid: int) -> None:
    _dung(lambda db: (db.execute("DELETE FROM so_viec WHERE id=?", (int(vid),)), db.commit()))


# ---------------------------------------------------------------- tổng quan
def tong_quan(ky: str = "") -> dict:
    ky = ky or _ky()
    like = "%" if ky == "all" else ky + "%"

    def f(db):
        s = lambda sql, a=(): float(db.execute(sql, a).fetchone()[0] or 0)
        thu = s("SELECT SUM(so_tien) FROM so_quy WHERE loai='thu' AND trang_thai='da_ghi' AND ngay LIKE ?", (like,))
        chi = s("SELECT SUM(so_tien) FROM so_quy WHERE loai='chi' AND trang_thai='da_ghi' AND ngay LIKE ?", (like,))
        cho = db.execute("SELECT COUNT(*), COALESCE(SUM(so_tien),0) FROM so_quy WHERE trang_thai='cho_duyet'").fetchone()
        hd = {r[0]: r[1] for r in db.execute("SELECT trang_thai, COUNT(*) FROM so_hop_dong GROUP BY trang_thai").fetchall()}
        pipe = s("SELECT SUM(gia_tri) FROM so_hop_dong WHERE trang_thai='bao_gia'")
        qua_han = int(s("SELECT COUNT(*) FROM so_viec WHERE trang_thai!='done' AND han!='' AND han<?", (_homnay(),)))
        viec_mo = int(s("SELECT COUNT(*) FROM so_viec WHERE trang_thai!='done'"))
        return thu, chi, cho, hd, pipe, qua_han, viec_mo
    thu, chi, cho, hd, pipe, qua_han, viec_mo = _dung(f)
    no = sum(h["con_no"] for h in ds_hop_dong() if h["trang_thai"] in ("da_ky", "hoan_thanh"))
    return {"ky": ky, "thu": thu, "chi": chi, "lai_gop": thu - chi, "cho_duyet": int(cho[0]), "cho_duyet_tien": float(cho[1]),
            "hop_dong": {k: hd.get(k, 0) for k in TRANG_THAI_HD}, "pipeline": pipe, "cong_no": no,
            "viec_qua_han": qua_han, "viec_mo": viec_mo, "luong": bang_luong(ky if ky != "all" else "")["tong_luong"]}


# ---------------------------------------------------------------- HTTP (chỉ chủ và quản lý)
def _ten(request: Request) -> str:
    st = getattr(request.state, "staff", None) or {}
    return str(st.get("ten") or "Chủ")


def _loi(f):
    import functools

    @functools.wraps(f)
    async def w(*a, **k):
        try:
            return await f(*a, **k)
        except (ValueError, PermissionError) as e:
            raise HTTPException(400, str(e))
    return w


def _json(data: str) -> Any:
    try:
        return json.loads(data)
    except Exception:
        raise HTTPException(400, "Dữ liệu không phải JSON")


@router.get("/shop/so/tong-quan")
async def r_tong_quan(request: Request, ky: str = ""):
    shop_state._kiem_quyen(request)
    return {"ok": True, **tong_quan(ky)}


@router.get("/shop/so/quy")
async def r_quy(request: Request, ky: str = "", loai: str = "", trang_thai: str = ""):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_quy(ky, loai, trang_thai)}


@router.post("/shop/so/su-kien")
@_loi
async def r_su_kien(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    st = getattr(request.state, "staff", None) or {}
    return xu_ly(_json(data), _ten(request), "", st)


@router.post("/shop/so/quy/duyet")
@_loi
async def r_duyet(request: Request, id: int = Form(...), quyet: str = Form(...)):
    shop_state._kiem_quyen(request)
    st = getattr(request.state, "staff", None) or {}
    if not _la_chu(st):
        raise HTTPException(403, "Chỉ chủ hoặc giám đốc duyệt chi")
    return {"ok": True, "phieu": duyet_quy(id, quyet, _ten(request))}


@router.post("/shop/so/quy/xoa")
@_loi
async def r_xoa_quy(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    st = getattr(request.state, "staff", None) or {}
    if not _la_chu(st):
        raise HTTPException(403, "Chỉ chủ hoặc giám đốc xóa phiếu")
    return {"ok": xoa_quy(id)}


@router.get("/shop/so/hop-dong")
async def r_hd(request: Request, trang_thai: str = "", q: str = ""):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_hop_dong(trang_thai, q)}


@router.post("/shop/so/hop-dong/trang-thai")
@_loi
async def r_hd_ts(request: Request, id: int = Form(...), trang_thai: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "hop_dong": doi_trang_thai_hd(id, trang_thai, _ten(request))}


@router.post("/shop/so/hop-dong/bao-cao")
@_loi
async def r_hd_bao_cao(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "ket_qua": giao_bao_cao(id)}


@router.get("/shop/so/bao-gia")
async def r_bg(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_bao_gia()}


@router.post("/shop/so/bao-gia")
@_loi
async def r_bg_luu(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "bao_gia": luu_bao_gia(_json(data), _ten(request))}


@router.post("/shop/so/bao-gia/trang-thai")
@_loi
async def r_bg_ts(request: Request, id: int = Form(...), trang_thai: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "bao_gia": doi_trang_thai_bg(id, trang_thai, _ten(request))}


@router.get("/shop/so/nhan-su")
async def r_ns(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_nhan_su(), "cau_hinh": cau_hinh()}


@router.post("/shop/so/nhan-su")
@_loi
async def r_ns_luu(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "nhan_su": luu_nhan_su(_json(data))}


@router.post("/shop/so/nhan-su/xoa")
@_loi
async def r_ns_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    xoa_nhan_su(id)
    return {"ok": True}


@router.post("/shop/so/phan-cong")
@_loi
async def r_pc(request: Request, hop_dong_id: int = Form(...), ten: str = Form(...), vai: str = Form("")):
    shop_state._kiem_quyen(request)
    return {"ok": True, **phan_cong(hop_dong_id, ten, vai)}


@router.post("/shop/so/phan-cong/go")
@_loi
async def r_pc_go(request: Request, hop_dong_id: int = Form(...), nhan_su_id: int = Form(...)):
    shop_state._kiem_quyen(request)
    go_phan_cong(hop_dong_id, nhan_su_id)
    return {"ok": True}


@router.get("/shop/so/luong")
async def r_luong(request: Request, ky: str = ""):
    shop_state._kiem_quyen(request)
    return {"ok": True, **bang_luong(ky)}


@router.post("/shop/so/cau-hinh")
@_loi
async def r_cfg(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "cau_hinh": luu_cau_hinh(_json(data))}


@router.get("/shop/so/viec")
async def r_viec(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_viec()}


@router.post("/shop/so/viec/buoc")
@_loi
async def r_viec_buoc(request: Request, id: int = Form(...), trang_thai: str = Form(...)):
    shop_state._kiem_quyen(request)
    doi_buoc_viec(id, trang_thai)
    return {"ok": True}


@router.post("/shop/so/viec/xoa")
@_loi
async def r_viec_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    xoa_viec(id)
    return {"ok": True}


@router.get("/shop/so/hoat-dong")
async def r_hoat_dong(request: Request, phut: int = 180):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": hoat_dong(phut), "ts": time.time()}


@router.post("/shop/so/mau")
async def r_mau(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "da_nap": nap_mau()}


@router.post("/shop/so/mau/xoa")
async def r_mau_xoa(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "da_xoa": xoa_mau()}


@router.get("/shop/so/cong-viec")
async def r_cv(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_cong_viec(), "phong": {k: v[0] for k, v in MA_PHONG.items()}}


@router.post("/shop/so/cong-viec")
@_loi
async def r_cv_luu(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "cong_viec": luu_cong_viec(_json(data))}


@router.post("/shop/so/cong-viec/xoa")
@_loi
async def r_cv_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    xoa_cong_viec(id)
    return {"ok": True}


@router.post("/shop/so/cong-viec/nap-h2o")
async def r_cv_nap(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "da_nap": nap_cong_viec_h2o()}


@router.get("/shop/so/giao-viec")
async def r_gv(request: Request, hop_dong_id: int = 0):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_giao_viec(hop_dong_id)}


@router.post("/shop/so/giao-viec/buoc")
@_loi
async def r_gv_buoc(request: Request, id: int = Form(...), trang_thai: str = Form(...)):
    shop_state._kiem_quyen(request)
    doi_giao_viec(id, trang_thai)
    return {"ok": True}


@router.post("/shop/so/giao-viec/xoa")
@_loi
async def r_gv_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    go_giao_viec(id)
    return {"ok": True}


@router.get("/shop/so/dich-vu")
async def r_dv(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_dich_vu()}


@router.post("/shop/so/dich-vu")
@_loi
async def r_dv_luu(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "dich_vu": luu_dich_vu(_json(data))}


@router.post("/shop/so/dich-vu/xoa")
@_loi
async def r_dv_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    xoa_dich_vu(id)
    return {"ok": True}


@router.post("/shop/so/dich-vu/nap-h2o")
async def r_dv_nap(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "da_nap": nap_dich_vu_h2o()}


@router.get("/shop/so/do")
async def r_do(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_do()}


@router.post("/shop/so/do")
@_loi
async def r_do_luu(request: Request, data: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "do": luu_do(_json(data))}


@router.post("/shop/so/do/xoa")
@_loi
async def r_do_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    xoa_do(id)
    return {"ok": True}


@router.post("/shop/so/do/mau")
async def r_do_mau(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, **nap_mau_do()}


@router.post("/shop/so/do/mau/xoa")
async def r_do_mau_xoa(request: Request):
    shop_state._kiem_quyen(request)
    return {"ok": True, **xoa_mau_do()}


@router.get("/shop/so/thue-do")
async def r_thue(request: Request, trang_thai: str = ""):
    shop_state._kiem_quyen(request)
    return {"ok": True, "items": ds_thue_do(trang_thai)}


@router.post("/shop/so/thue-do/buoc")
@_loi
async def r_thue_buoc(request: Request, id: int = Form(...), trang_thai: str = Form(...)):
    shop_state._kiem_quyen(request)
    return {"ok": True, "phieu": doi_trang_thai_thue(id, trang_thai, _ten(request))}


@router.post("/shop/so/thue-do/ghi-thu")
@_loi
async def r_thue_thu(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    st = getattr(request.state, "staff", None) or {}
    return {"ok": True, "phieu_thu": ghi_thu_thue(id, _ten(request), st)}


@router.post("/shop/so/thue-do/xoa")
@_loi
async def r_thue_xoa(request: Request, id: int = Form(...)):
    shop_state._kiem_quyen(request)
    xoa_thue_do(id)
    return {"ok": True}


def register(app, phong_fn, tasks_fn, brain_root_fn) -> None:
    _deps.update(phong=phong_fn, tasks=tasks_fn, brain_root=brain_root_fn)
    app.include_router(router)
