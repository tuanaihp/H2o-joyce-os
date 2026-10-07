"""Thời tiết kinh doanh cho tinh cầu: doanh thu so với chỉ tiêu theo tiến độ -> nắng/mây/mưa/bão.

Nguồn thật là H2O CRM Quản Trị (chỉ tiêu + doanh thu), CHƯA kết nối (chủ chốt 2026-10-06), nên
hiện chạy DỮ LIỆU MẪU: `nguon = "demo"` và mọi câu trả lời mang cờ đó để giao diện ghi rõ
"Dữ liệu mẫu" - không bao giờ để một con số bịa trông như số thật. Khi nối CRM, chỉ cần thay
`_so_lieu()` bằng một lời gọi lấy số thật; phần quy đổi thời tiết giữ nguyên.

Số mẫu là TẤT ĐỊNH theo ngày (cùng một ngày luôn ra cùng một đường doanh thu) để màn hình
không nhảy thời tiết mỗi lần tải lại, nhưng mỗi ngày một khác để thấy đủ các kiểu thời tiết.

Tiến độ tính trên doanh thu TÍCH LUỸ TỪ ĐẦU THÁNG so với chỉ tiêu tháng chia theo ngày đã qua
(cộng phần của hôm nay theo giờ mở cửa) - ổn định hơn so riêng từng ngày.
File cấu hình: STATE_DIR/business_weather.json (chỉ tiêu tháng, ngưỡng %), admin chỉnh tay."""
from __future__ import annotations

import calendar
import json
import random
import time
from datetime import datetime

import config as cfgmod

PATH = cfgmod.STATE_DIR / "business_weather.json"

# Thang thời tiết từ tốt tới xấu. `min_pct` = tiến độ tối thiểu để được kiểu đó.
NGUONG_MAC_DINH = {"nang": 100, "nang_nhe": 90, "nhieu_may": 75, "mua": 50, "giong": 30}
THU_TU = ["nang", "nang_nhe", "nhieu_may", "mua", "giong", "bao", "loc_xoay"]
NHAN = {"nang": "Nắng", "nang_nhe": "Nắng nhẹ", "nhieu_may": "Nhiều mây", "mua": "Mưa",
        "giong": "Giông", "bao": "Bão", "loc_xoay": "Lốc xoáy"}
GIO_MO, GIO_DONG = 8, 21          # giờ mở cửa studio: doanh thu trong ngày dồn vào khoảng này


def _cfg() -> dict:
    try:
        d = json.loads(PATH.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {}


def cau_hinh() -> dict:
    d = _cfg()
    ng = dict(NGUONG_MAC_DINH)
    ng.update({k: float(v) for k, v in (d.get("nguong") or {}).items() if k in NGUONG_MAC_DINH})
    return {"nguon": d.get("nguon") or "demo",
            "chi_tieu_thang": int(d.get("chi_tieu_thang") or 1_200_000_000),
            "nguong": ng}


def _phan_ngay_da_qua(now: datetime) -> float:
    """Phần doanh thu kỳ vọng của hôm nay đã 'đến hạn' theo giờ mở cửa (0..1)."""
    h = now.hour + now.minute / 60
    return min(1.0, max(0.0, (h - GIO_MO) / (GIO_DONG - GIO_MO)))


def _he_so_ngay(y: int, m: int, d: int) -> float:
    """Doanh thu mẫu của một ngày = chỉ tiêu ngày x hệ số này. Cuối tuần đông khách cưới hơn."""
    rng = random.Random(f"h2o-{y}-{m}-{d}")
    wd = datetime(y, m, d).weekday()
    nen = 1.25 if wd >= 5 else 0.9
    return max(0.05, rng.gauss(nen, 0.38))


def _so_lieu(now: datetime, chi_tieu_thang: int) -> dict:
    """DỮ LIỆU MẪU. Thay hàm này bằng số thật từ H2O CRM Quản Trị khi đã kết nối."""
    y, m, d = now.year, now.month, now.day
    so_ngay = calendar.monthrange(y, m)[1]
    ct_ngay = chi_tieu_thang / so_ngay
    phan = _phan_ngay_da_qua(now)
    # Xu hướng cả tháng (tháng tốt / tháng chậm), cũng tất định theo tháng.
    xu_huong = random.Random(f"h2o-thang-{y}-{m}").uniform(0.55, 1.2)
    dt_truoc = sum(ct_ngay * _he_so_ngay(y, m, i) * xu_huong for i in range(1, d))
    dt_hom_nay = ct_ngay * _he_so_ngay(y, m, d) * xu_huong * phan
    return {"doanh_thu_hom_nay": round(dt_hom_nay, -3),
            "chi_tieu_hom_nay_tien_do": round(ct_ngay * phan, -3),
            "doanh_thu_thang": round(dt_truoc + dt_hom_nay, -3),
            "chi_tieu_thang_tien_do": round(ct_ngay * (d - 1 + phan), -3),
            "du_lieu_day_du": True, "su_co": ""}


def thoi_tiet(pct: float, du_lieu_day_du: bool, su_co: str, nguong: dict) -> str:
    if su_co:
        return "loc_xoay"
    for k in ("nang", "nang_nhe", "nhieu_may", "mua", "giong"):
        if pct >= nguong[k]:
            kq = k
            break
    else:
        kq = "bao"
    # Thiếu dữ liệu thì không bao giờ "nắng": tối đa là nhiều mây, vì chưa đủ căn cứ.
    if not du_lieu_day_du and THU_TU.index(kq) < THU_TU.index("nhieu_may"):
        kq = "nhieu_may"
    return kq


def bao_cao(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    cfg = cau_hinh()
    s = _so_lieu(now, cfg["chi_tieu_thang"])
    muc_tieu = s["chi_tieu_thang_tien_do"]
    pct = (s["doanh_thu_thang"] / muc_tieu * 100) if muc_tieu > 0 else 100.0
    st = thoi_tiet(pct, s["du_lieu_day_du"], s["su_co"], cfg["nguong"])
    return {"ok": True, "nguon": cfg["nguon"], "state": st, "nhan": NHAN[st], "pct": round(pct, 1),
            "chi_tieu_thang": cfg["chi_tieu_thang"], "nguong": cfg["nguong"],
            "cap_nhat": int(time.time()), **s}
