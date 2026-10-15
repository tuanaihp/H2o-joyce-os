# -*- coding: utf-8 -*-
"""lo_trinh.py - tab Lộ trình: kích hoạt lộ trình cho học viên, mở bài theo ngày, chấm điểm.

Thiết kế: docs/dev/2026-10-lo-trinh-hoc-vien-design.md.

KHÔNG GỌI MODEL Ở BƯỚC NÀO (yêu cầu của chủ studio 2026-10-15: vận hành không được tốn quota):
  - Bài mở theo ngày tính lúc đọc, từ ngày bắt đầu và ngày nghỉ được duyệt.
  - Bài trắc nghiệm chấm bằng so đáp án trong file bài học.
  - Rubric, must-pass, khảo sát: mentor nhập số, server cộng theo trọng số.
  - Đề xuất kết quả: luật cố định, ngưỡng lấy đúng từ brain (rubric-100-diem, khao-sat-4-tuan).
  - Tin Telegram: gửi thẳng Bot API, đánh dấu đã gửi để không gửi trùng.

Hai nơi lưu, tách bạch theo quyết định của spec chưng cất:
  - BÀI HỌC nằm trong brain `ThuyH2O - Hoc Viec`: wiki/hoc-viec/cap-do/<cap>/bai-hoc/*.md, mỗi ngày
    một file, frontmatter có `ngay`, `tieu_de`, `kiem_tra` (câu hỏi + đáp án). Trưởng đào tạo sửa
    như mọi trang wiki.
  - ĐIỂM VÀ BÀI NỘP của từng người nằm ở STATE_DIR/lo_trinh.json, KHÔNG vào brain.

Quyền kiểm ở server (không tin vai trò client gửi):
  - Quản trị (không có cookie nhân viên): mọi học viên.
  - Trưởng phòng (nhóm quyền quan_ly): học viên cùng phòng.
  - Mentor được gán: chấm học viên của mình, không kích hoạt hay kết luận.
  - Học viên: chỉ đọc bài và nộp bài của chính mình.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

import fastyaml   # bộ nạp YAML dùng libyaml, tự rơi về bộ nạp Python khi thiếu (quy ước repo)

BRAIN_GIAO_TRINH = "ThuyH2O - Hoc Viec"
THU_MUC_CAP = Path("wiki") / "hoc-viec" / "cap-do"

# Thang lộ trình theo sơ đồ của H2O (thứ tự hiển thị). CTV song song Nhân viên.
CAP_DO = (
    ("hoc-viec", "Học việc"),
    ("thuc-tap-sinh", "Thực tập sinh"),
    ("nhan-vien", "Nhân viên"),
    ("ctv", "CTV"),
    ("chuyen-vien-cap-cao", "Chuyên viên cấp cao"),
    ("chuyen-gia", "Chuyên gia"),
    ("quan-ly", "Quản lý nhóm"),
    ("truong-phong", "Trưởng phòng"),
    ("giam-doc", "CO-Giám đốc"),
    ("chu-tich-hdqt", "Chủ tịch HĐQT"),
)
TEN_CAP = dict(CAP_DO)
CAP_TIEP = {"hoc-viec": "thuc-tap-sinh"}

# Đúng bảng của wiki/hoc-viec/cap-do/hoc-viec/rubric-100-diem.md: (mã, tên, điểm tối đa).
RUBRIC = (
    ("ky_thuat", "Kỹ thuật chuyên môn", 35),
    ("quy_trinh", "Quy trình, vệ sinh và an toàn", 20),
    ("phuc_vu", "Chất lượng phục vụ và tư vấn", 15),
    ("ky_luat", "Kỷ luật, đúng giờ, hoàn thành bài", 10),
    ("thai_do", "Thái độ, hợp tác, tiếp thu", 10),
    ("nhat_ky", "Nhật ký, bằng chứng, tự đánh giá", 10),
)
# Đúng năm điều của wiki/hoc-viec/cap-do/hoc-viec/must-pass.md.
MUST_PASS = (
    ("ve_sinh", "Vệ sinh và an toàn dụng cụ"),
    ("bao_mat", "Bảo mật dữ liệu, hình ảnh khách hàng, quyền riêng tư"),
    ("pham_vi", "Không tự ý phục vụ khách ngoài phạm vi được giao"),
    ("trung_thuc", "Trung thực trong chấm công, bằng chứng và báo cáo"),
    ("an_toan", "Không có hành vi nguy hiểm hoặc vi phạm nghiêm trọng"),
)
# Phần II của phiếu khảo sát tuần (quản lý chấm), thang 10-100.
KHAO_SAT = (
    ("thai_do", "Thái độ và ý thức học nghề"),
    ("tuan_thu", "Tuân thủ văn hoá và quy trình"),
    ("hoa_nhap", "Hoà nhập và làm việc tập thể"),
)

NGUONG_DAT = 80            # rubric-100-diem: 80 trở lên đạt
NGUONG_BO_SUNG = 65        # 65 đến 79 cần bổ sung, dưới 65 trưởng phòng xem xét
NGUONG_KIEN_THUC = 70      # đề xuất tạm: trung bình bài kiểm tra từ 70%
NGUONG_KHAO_SAT = 70       # khao-sat-4-tuan: trung bình phần quản lý từ 70/100
SAN_KHAO_SAT = 50          # khao-sat-4-tuan: tuần gần nhất không tiêu chí nào dưới 50
LAN_NOP_TOI_DA = 2         # mỗi bài được nộp hai lần, lấy lần cao hơn
GIO_GUI = 7                # giờ gửi tin bài hôm nay (giờ Việt Nam)

GATE1 = ("dat", "thieu", "vi_pham")
KET_LUAN = ("dat", "can_bo_sung", "gia_han", "khong_dat", "rut_lui")
KET_LUAN_DONG = ("dat", "khong_dat", "rut_lui")   # các kết luận đóng lộ trình

_NGAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ID_RE = re.compile(r"^lt_[0-9a-f]{10}$")
_LOCK = threading.Lock()


# ============================================================ bài học (đọc từ brain)

def _tach_frontmatter(text: str) -> tuple:
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    try:
        fm = fastyaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    return (fm if isinstance(fm, dict) else {}), m.group(2)


def _chuan_cau_hoi(raw) -> list:
    """Câu hỏi hợp lệ: có `hoi`, ít nhất 2 `lua_chon`, `dap_an` là chỉ số trong khoảng. Câu sai
    định dạng bị bỏ thay vì làm hỏng cả bài (trưởng đào tạo sửa tay file này)."""
    out = []
    for q in raw if isinstance(raw, list) else []:
        if not isinstance(q, dict):
            continue
        hoi = str(q.get("hoi") or "").strip()
        lc = [str(x).strip() for x in (q.get("lua_chon") or []) if str(x).strip()]
        try:
            da = int(q.get("dap_an"))
        except Exception:
            continue
        if not hoi or len(lc) < 2 or not 0 <= da < len(lc):
            continue
        out.append({"hoi": hoi, "lua_chon": lc, "dap_an": da,
                    "giai_thich": str(q.get("giai_thich") or "").strip()})
    return out


def doc_bai_hoc(goc_brain: Path, cap: str) -> list:
    """Bài học `status: active` của một cấp, sắp theo ngày. Mỗi bài: ngay, tieu_de, nhanh, loai,
    thoi_luong_phut, muc_tieu, noi_dung (markdown), kiem_tra (có đáp án), nguon, file."""
    if cap not in TEN_CAP:
        return []
    d = Path(goc_brain) / THU_MUC_CAP / cap / "bai-hoc"
    if not d.is_dir():
        return []
    bai = {}
    for f in sorted(d.glob("*.md")):
        try:
            fm, than = _tach_frontmatter(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(fm.get("status") or "") != "active":
            continue
        try:
            ngay = int(fm.get("ngay"))
        except Exception:
            continue
        if ngay < 0 or ngay in bai:
            continue
        bai[ngay] = {
            "ngay": ngay,
            "tieu_de": str(fm.get("tieu_de") or f.stem),
            "nhanh": str(fm.get("nhanh") or "chung"),
            "loai": str(fm.get("loai_ngay") or "hoc"),
            "thoi_luong_phut": int(fm.get("thoi_luong_phut") or 0),
            "muc_tieu": [str(x) for x in (fm.get("muc_tieu") or []) if str(x).strip()],
            "noi_dung": than.strip(),
            "kiem_tra": _chuan_cau_hoi(fm.get("kiem_tra")),
            "nguon": [str(x) for x in (fm.get("nguon") or []) if str(x).strip()]
            if isinstance(fm.get("nguon"), list) else ([str(fm["nguon"])] if fm.get("nguon") else []),
            "file": f.name,
        }
    return [bai[k] for k in sorted(bai)]


def thang_lo_trinh(goc_brain: Path) -> list:
    """Chín bậc (và CTV) kèm số bài học đang dùng. Cấp nào chưa có bài thì so_bai = 0."""
    out = []
    for ma, ten in CAP_DO:
        ds = doc_bai_hoc(goc_brain, ma)
        out.append({"ma": ma, "ten": ten, "co_khung": (Path(goc_brain) / THU_MUC_CAP / ma).is_dir(),
                    "so_bai": len(ds), "so_ngay": (ds[-1]["ngay"] if ds else 0),
                    "so_bai_kiem_tra": sum(1 for b in ds if b["kiem_tra"])})
    return out


# ============================================================ lịch học (ngày đào tạo)

def _ngay(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def ngay_dao_tao(bat_dau: str, ngay_nghi, hom_nay: str) -> int:
    """Chỉ số ngày đào tạo của `hom_nay`: ngày bắt đầu là ngày 0, ngày nghỉ được duyệt không
    tính (lịch còn lại tự dịch). Trước ngày bắt đầu trả -1."""
    bd, hn = _ngay(bat_dau), _ngay(hom_nay)
    if hn < bd:
        return -1
    nghi = {str(x) for x in (ngay_nghi or [])}
    n, d = -1, bd
    while d <= hn:
        if d.isoformat() not in nghi:
            n += 1
        d += _dt.timedelta(days=1)
    return n


def lich_ngay(bat_dau: str, ngay_nghi, so_ngay: int) -> dict:
    """Ngày đào tạo -> ngày lịch (YYYY-MM-DD), từ 0 tới so_ngay."""
    nghi = {str(x) for x in (ngay_nghi or [])}
    out, n, d = {}, 0, _ngay(bat_dau)
    while n <= so_ngay:
        if d.isoformat() not in nghi:
            out[n] = d.isoformat()
            n += 1
        d += _dt.timedelta(days=1)
    return out


# ============================================================ chấm điểm (không gọi model)

def cham_bai(cau_hoi: list, tra_loi) -> dict:
    """So đáp án. `tra_loi` là danh sách chỉ số lựa chọn theo thứ tự câu (thiếu = sai)."""
    tl = list(tra_loi) if isinstance(tra_loi, (list, tuple)) else []
    ket = []
    dung = 0
    for i, q in enumerate(cau_hoi):
        try:
            chon = int(tl[i]) if i < len(tl) and tl[i] is not None else None
        except Exception:
            chon = None
        ok = chon == q["dap_an"]
        dung += 1 if ok else 0
        ket.append({"chon": chon, "dung": ok})
    tong = len(cau_hoi)
    return {"dung": dung, "tong": tong, "diem": round(dung * 100 / tong) if tong else None, "chi_tiet": ket}


def hoan_vi(eid: str, ngay: int, i: int, n: int) -> list:
    """Thứ tự hiện lựa chọn cho học viên: vị trí hiện p là lựa chọn gốc hoan_vi[p].

    Người soạn bài hay để đáp án ở cùng một vị trí (bản đầu: 52/69 câu là B), nên chọn bừa một
    chữ cũng qua. Xáo theo (học viên, ngày, câu) thì mỗi người một thứ tự, mở lại vẫn y nguyên,
    và file bài học trong brain không phải đổi."""
    import random
    p = list(range(n))
    random.Random(f"{eid}:{ngay}:{i}").shuffle(p)
    return p


def _ve_goc(eid: str, ngay: int, cau_hoi: list, tra_loi) -> list:
    """Chỉ số học viên chọn (theo thứ tự đã xáo) -> chỉ số gốc trong file bài học."""
    tl = list(tra_loi) if isinstance(tra_loi, (list, tuple)) else []
    out = []
    for i, q in enumerate(cau_hoi):
        hv = hoan_vi(eid, ngay, i, len(q["lua_chon"]))
        try:
            p = int(tl[i]) if i < len(tl) and tl[i] is not None else None
        except Exception:
            p = None
        out.append(hv[p] if p is not None and 0 <= p < len(hv) else None)
    return out


def _ra_hien(eid: str, ngay: int, cau_hoi: list, goc: list) -> list:
    """Chỉ số gốc -> vị trí đang hiện cho học viên này."""
    out = []
    for i, q in enumerate(cau_hoi):
        o = goc[i] if i < len(goc) else None
        out.append(hoan_vi(eid, ngay, i, len(q["lua_chon"])).index(o) if o is not None else None)
    return out


def diem_bai(hv: dict, ngay: int):
    """Điểm cao nhất của một bài đã nộp, hoặc None."""
    lan = (hv.get("nop") or {}).get(str(ngay)) or []
    ds = [x.get("diem") for x in lan if x.get("diem") is not None]
    return max(ds) if ds else None


def kien_thuc(hv: dict, bai: list, ngay_ht: int) -> dict:
    """Trung bình bài kiểm tra đã đến hạn. Bài của những ngày ĐÃ QUA mà chưa nộp tính là bỏ bài
    (điểm 0); bài của hôm nay chưa nộp thì chưa tính."""
    diem, bo = [], []
    for b in bai:
        if not b["kiem_tra"] or b["ngay"] > ngay_ht:
            continue
        d = diem_bai(hv, b["ngay"])
        if d is None:
            if b["ngay"] < ngay_ht:
                bo.append(b["ngay"])
                diem.append(0)
            continue
        diem.append(d)
    return {"trung_binh": round(sum(diem) / len(diem)) if diem else None, "so_bai": len(diem), "bo_bai": bo}


def tong_rubric(rubric: dict):
    """Tổng 100 điểm nếu đã chấm ĐỦ sáu nhóm, không thì None."""
    diem = (rubric or {}).get("diem") or {}
    if any(ma not in diem for ma, _, _ in RUBRIC):
        return None
    return sum(int(diem[ma]) for ma, _, _ in RUBRIC)


def danh_gia_khao_sat(khao_sat: dict) -> dict:
    """Bốn yếu tố của khao-sat-4-tuan, phần quản lý chấm."""
    tuan = sorted(int(k) for k in (khao_sat or {}) if str(k).isdigit())
    if not tuan:
        return {"co": False}
    tb_tuan = {}
    for t in tuan:
        v = khao_sat[str(t)]
        tb_tuan[t] = sum(int(v[m]) for m, _ in KHAO_SAT) / len(KHAO_SAT)
    cuoi = khao_sat[str(tuan[-1])]
    tb = sum(tb_tuan.values()) / len(tb_tuan)
    return {
        "co": True, "so_tuan": len(tuan), "trung_binh": round(tb),
        "dat_nguong": tb >= NGUONG_KHAO_SAT,
        "khong_duoi_san": all(int(cuoi[m]) >= SAN_KHAO_SAT for m, _ in KHAO_SAT),
        "khong_giam": tb_tuan[tuan[-1]] >= tb_tuan[tuan[0]],
    }


def de_xuat(hv: dict, bai: list, ngay_ht: int) -> dict:
    """Đề xuất kết quả theo luật của brain. Chỉ là ĐỀ XUẤT: kết luận do người bấm.

    ket_qua: dat | can_bo_sung | truong_phong_xem_xet | chua_du_du_lieu
    ly_do: danh sách mã (dashboard dịch sang chữ), kèm tham số nếu có."""
    ly_do = []
    mp = hv.get("must_pass") or {}
    if any(mp.get(m) == "truot" for m, _ in MUST_PASS):
        return {"ket_qua": "truong_phong_xem_xet", "ly_do": [{"ma": "mp_truot"}]}
    tong = tong_rubric(hv.get("rubric") or {})
    thieu_mp = [m for m, _ in MUST_PASS if mp.get(m) != "dat"]
    if tong is None or thieu_mp:
        if tong is None:
            ly_do.append({"ma": "thieu_rubric"})
        if thieu_mp:
            ly_do.append({"ma": "thieu_must_pass", "so": len(thieu_mp)})
        return {"ket_qua": "chua_du_du_lieu", "ly_do": ly_do}
    if tong < NGUONG_BO_SUNG:
        return {"ket_qua": "truong_phong_xem_xet", "ly_do": [{"ma": "rubric_duoi_65", "diem": tong}]}
    if tong < NGUONG_DAT:
        ly_do.append({"ma": "rubric_65_79", "diem": tong})
    kt = kien_thuc(hv, bai, ngay_ht)
    if kt["bo_bai"]:
        ly_do.append({"ma": "bo_bai", "so": len(kt["bo_bai"])})
    if kt["trung_binh"] is not None and kt["trung_binh"] < NGUONG_KIEN_THUC:
        ly_do.append({"ma": "kien_thuc_duoi_70", "diem": kt["trung_binh"]})
    g1 = (hv.get("gate1") or {}).get("ket_qua")
    if g1 != "dat":
        ly_do.append({"ma": "gate1_chua_dat"})
    ks = danh_gia_khao_sat(hv.get("khao_sat") or {})
    if not ks["co"]:
        ly_do.append({"ma": "khao_sat_thieu"})
    else:
        if not ks["dat_nguong"]:
            ly_do.append({"ma": "khao_sat_duoi_70", "diem": ks["trung_binh"]})
        if not ks["khong_duoi_san"]:
            ly_do.append({"ma": "khao_sat_duoi_san"})
        if not ks["khong_giam"]:
            ly_do.append({"ma": "khao_sat_giam"})
    return {"ket_qua": "can_bo_sung" if ly_do else "dat", "ly_do": ly_do}


# ============================================================ lưu trữ (STATE_DIR, ngoài brain)

def _doc(path: Path) -> dict:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("hoc_vien"), list):
            return d
    except Exception:
        pass
    return {"hoc_vien": []}


def _ghi(path: Path, d: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def _lich_su(hv: dict, nguoi: str, viec: str) -> None:
    hv.setdefault("lich_su", []).append({"ts": int(time.time()), "nguoi": nguoi, "viec": viec})
    hv["lich_su"] = hv["lich_su"][-200:]


# ============================================================ tiêm phụ thuộc từ main

@dataclass
class LoTrinhDeps:
    brains_dir: Callable[[], str]
    state_path: Callable[[], Path]
    staff_of: Callable[[Request], dict]              # {} = quản trị (không có cookie nhân viên)
    staff_cap: Callable[[dict], str]                 # "quan_ly" | "nhan_vien" | "hoc_viec"
    list_staff: Callable[[], list]
    get_staff: Callable[[str], Any]
    today: Callable[[], str]                         # YYYY-MM-DD theo giờ Việt Nam
    now_hour: Callable[[], int] = lambda: 12
    tg_send: Callable[[str, str], Awaitable[tuple]] = None   # gửi thẳng tới đúng chat_id


def _goc(deps: LoTrinhDeps) -> Path:
    return Path(deps.brains_dir()) / BRAIN_GIAO_TRINH


def _cung_phong(a: dict, b: dict) -> bool:
    return bool(set(a.get("phong_ban") or []) & set(b.get("phong_ban") or []))


def _vai(deps: LoTrinhDeps, request: Request) -> tuple:
    """(vai, staff). vai: quan_tri | quan_ly | nhan_vien | hoc_viec."""
    st = deps.staff_of(request) or {}
    if not st:
        return "quan_tri", {}
    return (deps.staff_cap(st) or "nhan_vien"), st


def _quan_ly_duoc(vai: str, st: dict, hv: dict, deps: LoTrinhDeps) -> bool:
    """Kích hoạt, cho nghỉ, kết luận: quản trị, hoặc trưởng phòng cùng phòng với học viên."""
    if vai == "quan_tri":
        return True
    if vai != "quan_ly":
        return False
    hoc = deps.get_staff(hv.get("staff_id")) or {"phong_ban": hv.get("phong_ban") or []}
    return _cung_phong(st, hoc)


def _cham_duoc(vai: str, st: dict, hv: dict, deps: LoTrinhDeps) -> bool:
    """Chấm Gate 1, khảo sát, rubric, must-pass: người quản lý được, hoặc mentor được gán."""
    if _quan_ly_duoc(vai, st, hv, deps):
        return True
    return bool(st) and st.get("id") == hv.get("mentor_id") and st.get("id") != hv.get("staff_id")


def _tom_tat(hv: dict, deps: LoTrinhDeps, hom_nay: str, bai_cache: dict) -> dict:
    cap = hv.get("cap_do")
    bai = bai_cache.setdefault(cap, doc_bai_hoc(_goc(deps), cap))
    so_ngay = bai[-1]["ngay"] if bai else 0
    ngay_ht = ngay_dao_tao(hv["ngay_bat_dau"], hv.get("ngay_nghi"), hom_nay)
    hom = next((b for b in bai if b["ngay"] == ngay_ht), None)
    mentor = deps.get_staff(hv.get("mentor_id")) if hv.get("mentor_id") else None
    kt = kien_thuc(hv, bai, ngay_ht)
    return {
        "id": hv["id"], "staff_id": hv.get("staff_id"), "ten": hv.get("ten"),
        "cap_do": cap, "cap_ten": TEN_CAP.get(cap, cap), "nhanh": hv.get("nhanh"),
        "ngay_bat_dau": hv["ngay_bat_dau"], "ngay_hien_tai": ngay_ht, "so_ngay": so_ngay,
        "trang_thai": hv.get("trang_thai"), "mentor_ten": (mentor or {}).get("ten") or "",
        "kien_thuc_tb": kt["trung_binh"], "bo_bai": len(kt["bo_bai"]),
        "rubric_tong": tong_rubric(hv.get("rubric") or {}),
        "de_xuat": de_xuat(hv, bai, ngay_ht)["ket_qua"],
        "ket_luan": (hv.get("ket_luan") or {}).get("ket_qua"),
        "bai_hom_nay": ({"ngay": hom["ngay"], "tieu_de": hom["tieu_de"],
                         "da_nop": diem_bai(hv, hom["ngay"]) is not None} if hom else None),
    }


def _loi(ma: str, code: int = 400):
    return JSONResponse({"ok": False, "error": ma}, status_code=code)


def register(app, deps: LoTrinhDeps):
    router = APIRouter()

    def _tim(d: dict, eid: str):
        if not _ID_RE.match(str(eid or "")):
            return None
        return next((x for x in d["hoc_vien"] if x.get("id") == eid), None)

    @router.get("/lo-trinh")
    async def lo_trinh_tong(request: Request):
        vai, st = _vai(deps, request)
        hom_nay = deps.today()
        d = await asyncio.to_thread(_doc, deps.state_path())
        cache: dict = {}
        thang = await asyncio.to_thread(thang_lo_trinh, _goc(deps))
        quan_ly, cua_toi = [], []
        for hv in d["hoc_vien"]:
            if st and hv.get("staff_id") == st.get("id"):
                cua_toi.append(_tom_tat(hv, deps, hom_nay, cache))
            elif _cham_duoc(vai, st, hv, deps):
                quan_ly.append(_tom_tat(hv, deps, hom_nay, cache))
        ung_vien = []
        if vai in ("quan_tri", "quan_ly"):
            for s in deps.list_staff():
                if not s.get("active", True) or s.get("id") == st.get("id"):
                    continue
                if vai == "quan_ly" and not _cung_phong(st, s):
                    continue
                ung_vien.append({"id": s.get("id"), "ten": s.get("ten"), "role": s.get("role")})
        return {"ok": True, "vai": vai, "hom_nay": hom_nay, "co_brain": _goc(deps).is_dir(),
                "thang": thang, "hoc_vien": quan_ly, "cua_toi": cua_toi, "ung_vien": ung_vien,
                "rubric": [{"ma": m, "ten": t, "toi_da": n} for m, t, n in RUBRIC],
                "must_pass": [{"ma": m, "ten": t} for m, t in MUST_PASS],
                "khao_sat": [{"ma": m, "ten": t} for m, t in KHAO_SAT]}

    @router.post("/lo-trinh/kich-hoat")
    async def lo_trinh_kich_hoat(request: Request, body: dict = Body(...)):
        vai, st = _vai(deps, request)
        if vai not in ("quan_tri", "quan_ly"):
            return _loi("khong_du_quyen", 403)
        sid = str(body.get("staff_id") or "")
        cap = str(body.get("cap_do") or "hoc-viec")
        ngay_bd = str(body.get("ngay_bat_dau") or deps.today())
        hoc = deps.get_staff(sid)
        if not hoc or not hoc.get("active", True):
            return _loi("khong_thay_nhan_vien", 404)
        if vai == "quan_ly" and not _cung_phong(st, hoc):
            return _loi("khac_phong", 403)
        if not _NGAY_RE.match(ngay_bd):
            return _loi("ngay_sai")
        try:
            _ngay(ngay_bd)
        except ValueError:
            return _loi("ngay_sai")
        bai = await asyncio.to_thread(doc_bai_hoc, _goc(deps), cap)
        if not bai:
            return _loi("cap_chua_co_bai")
        mentor_id = str(body.get("mentor_id") or "")
        if mentor_id and (mentor_id == sid or not deps.get_staff(mentor_id)):
            return _loi("mentor_sai")
        chat = re.sub(r"[^0-9\-]", "", str(body.get("telegram_chat_id") or ""))[:20]
        nguoi = (st or {}).get("ten") or "quản trị"
        with _LOCK:
            d = _doc(deps.state_path())
            if any(x.get("staff_id") == sid and x.get("cap_do") == cap and x.get("trang_thai") == "dang_hoc"
                   for x in d["hoc_vien"]):
                return _loi("da_kich_hoat", 409)
            hv = {
                "id": "lt_" + secrets.token_hex(5), "staff_id": sid, "ten": hoc.get("ten"),
                "phong_ban": list(hoc.get("phong_ban") or []), "cap_do": cap,
                "nhanh": str(body.get("nhanh") or "makeup"), "ngay_bat_dau": ngay_bd,
                "ngay_nghi": [], "mentor_id": mentor_id, "telegram_chat_id": chat,
                "trang_thai": "dang_hoc", "tao_luc": int(time.time()), "nguoi_kich_hoat": nguoi,
                "nop": {}, "rubric": {}, "must_pass": {}, "gate1": {}, "khao_sat": {},
                "ket_luan": {}, "da_gui": {},
            }
            _lich_su(hv, nguoi, f"kích hoạt lộ trình {TEN_CAP.get(cap, cap)} từ {ngay_bd}")
            d["hoc_vien"].append(hv)
            _ghi(deps.state_path(), d)
        return {"ok": True, "id": hv["id"]}

    @router.get("/lo-trinh/hoc-vien/{eid}")
    async def lo_trinh_chi_tiet(eid: str, request: Request):
        vai, st = _vai(deps, request)
        d = await asyncio.to_thread(_doc, deps.state_path())
        hv = _tim(d, eid)
        if not hv:
            return _loi("khong_thay", 404)
        la_ban_than = bool(st) and st.get("id") == hv.get("staff_id")
        if not la_ban_than and not _cham_duoc(vai, st, hv, deps):
            return _loi("khong_du_quyen", 403)
        hom_nay = deps.today()
        bai = await asyncio.to_thread(doc_bai_hoc, _goc(deps), hv["cap_do"])
        ngay_ht = ngay_dao_tao(hv["ngay_bat_dau"], hv.get("ngay_nghi"), hom_nay)
        lich = lich_ngay(hv["ngay_bat_dau"], hv.get("ngay_nghi"), bai[-1]["ngay"] if bai else 0)
        ds_bai = [{
            "ngay": b["ngay"], "tieu_de": b["tieu_de"], "loai": b["loai"], "ngay_lich": lich.get(b["ngay"]),
            "mo": b["ngay"] <= ngay_ht, "co_kiem_tra": bool(b["kiem_tra"]),
            "diem": diem_bai(hv, b["ngay"]), "so_lan": len((hv.get("nop") or {}).get(str(b["ngay"])) or []),
        } for b in bai]
        out = {"ok": True, "ban_than": la_ban_than, "tom_tat": _tom_tat(hv, deps, hom_nay, {hv["cap_do"]: bai}),
               "bai": ds_bai, "kien_thuc": kien_thuc(hv, bai, ngay_ht),
               "quan_ly_duoc": _quan_ly_duoc(vai, st, hv, deps),
               "cham_duoc": _cham_duoc(vai, st, hv, deps)}
        if not la_ban_than:
            out.update({
                "gate1": hv.get("gate1") or {}, "khao_sat": hv.get("khao_sat") or {},
                "khao_sat_danh_gia": danh_gia_khao_sat(hv.get("khao_sat") or {}),
                "rubric": hv.get("rubric") or {}, "must_pass": hv.get("must_pass") or {},
                "de_xuat": de_xuat(hv, bai, ngay_ht), "ket_luan": hv.get("ket_luan") or {},
                "ngay_nghi": hv.get("ngay_nghi") or [], "telegram": bool(hv.get("telegram_chat_id")),
                "lich_su": (hv.get("lich_su") or [])[-20:],
                "cap_tiep": TEN_CAP.get(CAP_TIEP.get(hv["cap_do"], ""), ""),
            })
        return out

    @router.get("/lo-trinh/bai/{eid}/{ngay}")
    async def lo_trinh_bai(eid: str, ngay: int, request: Request):
        vai, st = _vai(deps, request)
        d = await asyncio.to_thread(_doc, deps.state_path())
        hv = _tim(d, eid)
        if not hv:
            return _loi("khong_thay", 404)
        la_ban_than = bool(st) and st.get("id") == hv.get("staff_id")
        if not la_ban_than and not _cham_duoc(vai, st, hv, deps):
            return _loi("khong_du_quyen", 403)
        bai = await asyncio.to_thread(doc_bai_hoc, _goc(deps), hv["cap_do"])
        b = next((x for x in bai if x["ngay"] == ngay), None)
        if not b:
            return _loi("khong_thay", 404)
        ngay_ht = ngay_dao_tao(hv["ngay_bat_dau"], hv.get("ngay_nghi"), deps.today())
        if la_ban_than and b["ngay"] > ngay_ht:
            return _loi("chua_mo", 403)
        lan = (hv.get("nop") or {}).get(str(ngay)) or []
        diem = diem_bai(hv, ngay)
        # Học viên chỉ thấy đáp án khi đã hết lượt nộp hoặc đã đúng hết.
        lo_dap_an = (not la_ban_than) or len(lan) >= LAN_NOP_TOI_DA or diem == 100
        cau = []
        for i, q in enumerate(b["kiem_tra"]):
            p = hoan_vi(eid, ngay, i, len(q["lua_chon"]))
            m = {"hoi": q["hoi"], "lua_chon": [q["lua_chon"][o] for o in p]}
            if lo_dap_an:
                m.update({"dap_an": p.index(q["dap_an"]), "giai_thich": q["giai_thich"]})
            cau.append(m)
        cuoi = None
        if lan:
            cuoi = {**lan[-1], "tra_loi": _ra_hien(eid, ngay, b["kiem_tra"], lan[-1].get("tra_loi") or [])}
        return {"ok": True, "ngay": b["ngay"], "tieu_de": b["tieu_de"], "loai": b["loai"],
                "thoi_luong_phut": b["thoi_luong_phut"], "muc_tieu": b["muc_tieu"],
                "noi_dung": b["noi_dung"], "kiem_tra": cau, "nguon": b["nguon"],
                "so_lan": len(lan), "lan_toi_da": LAN_NOP_TOI_DA, "diem": diem,
                "lan_cuoi": cuoi,
                "nop_duoc": la_ban_than and hv.get("trang_thai") == "dang_hoc"
                and bool(b["kiem_tra"]) and len(lan) < LAN_NOP_TOI_DA and diem != 100}

    @router.post("/lo-trinh/bai/{eid}/{ngay}/nop")
    async def lo_trinh_nop(eid: str, ngay: int, request: Request, body: dict = Body(...)):
        vai, st = _vai(deps, request)
        with _LOCK:
            d = _doc(deps.state_path())
            hv = _tim(d, eid)
            if not hv:
                return _loi("khong_thay", 404)
            if not st or st.get("id") != hv.get("staff_id"):
                return _loi("chi_hoc_vien_nop", 403)
            if hv.get("trang_thai") != "dang_hoc":
                return _loi("lo_trinh_da_dong", 409)
            ds = doc_bai_hoc(_goc(deps), hv["cap_do"])
            b = next((x for x in ds if x["ngay"] == ngay), None)
            if not b or not b["kiem_tra"]:
                return _loi("khong_co_kiem_tra", 404)
            if b["ngay"] > ngay_dao_tao(hv["ngay_bat_dau"], hv.get("ngay_nghi"), deps.today()):
                return _loi("chua_mo", 403)
            lan = hv.setdefault("nop", {}).setdefault(str(ngay), [])
            if len(lan) >= LAN_NOP_TOI_DA or diem_bai(hv, ngay) == 100:
                return _loi("het_luot", 409)
            # Học viên gửi vị trí đang thấy (đã xáo); đổi về chỉ số gốc rồi mới chấm và lưu.
            kq = cham_bai(b["kiem_tra"], _ve_goc(eid, ngay, b["kiem_tra"], body.get("tra_loi")))
            lan.append({"ts": int(time.time()), "tra_loi": [c["chon"] for c in kq["chi_tiet"]],
                        "dung": kq["dung"], "tong": kq["tong"], "diem": kq["diem"]})
            _lich_su(hv, st.get("ten") or "học viên", f"nộp bài ngày {ngay}: {kq['diem']}%")
            _ghi(deps.state_path(), d)
            het = len(lan) >= LAN_NOP_TOI_DA or kq["diem"] == 100
        chi_tiet = []
        for i, (q, c) in enumerate(zip(b["kiem_tra"], kq["chi_tiet"])):
            p = hoan_vi(eid, ngay, i, len(q["lua_chon"]))
            m = {"dung": c["dung"], "chon": (p.index(c["chon"]) if c["chon"] is not None else None)}
            if het:
                m.update({"dap_an": p.index(q["dap_an"]), "giai_thich": q["giai_thich"]})
            chi_tiet.append(m)
        return {"ok": True, "diem": kq["diem"], "dung": kq["dung"], "tong": kq["tong"],
                "so_lan": len(lan), "lan_toi_da": LAN_NOP_TOI_DA, "het_luot": het, "chi_tiet": chi_tiet}

    @router.post("/lo-trinh/hoc-vien/{eid}/cham")
    async def lo_trinh_cham(eid: str, request: Request, body: dict = Body(...)):
        vai, st = _vai(deps, request)
        nguoi = (st or {}).get("ten") or "quản trị"
        with _LOCK:
            d = _doc(deps.state_path())
            hv = _tim(d, eid)
            if not hv:
                return _loi("khong_thay", 404)
            if not _cham_duoc(vai, st, hv, deps):
                return _loi("khong_du_quyen", 403)
            if hv.get("trang_thai") != "dang_hoc":
                return _loi("lo_trinh_da_dong", 409)
            viec = []
            if "gate1" in body:
                g = body.get("gate1") or {}
                kq = str(g.get("ket_qua") or "")
                if kq not in GATE1:
                    return _loi("gate1_sai")
                hv["gate1"] = {"ket_qua": kq, "ghi_chu": str(g.get("ghi_chu") or "")[:1000],
                               "nguoi": nguoi, "ts": int(time.time())}
                viec.append(f"Gate 1: {kq}")
            if "khao_sat" in body:
                k = body.get("khao_sat") or {}
                try:
                    tuan = int(k.get("tuan"))
                    diem = {m: int(k.get(m)) for m, _ in KHAO_SAT}
                except Exception:
                    return _loi("khao_sat_sai")
                if not 1 <= tuan <= 4 or any(not 10 <= v <= 100 for v in diem.values()):
                    return _loi("khao_sat_sai")
                hv.setdefault("khao_sat", {})[str(tuan)] = {**diem, "nguoi": nguoi, "ts": int(time.time())}
                viec.append(f"khảo sát tuần {tuan}")
            if "rubric" in body:
                r = body.get("rubric") or {}
                moi = {}
                for ma, _, toi_da in RUBRIC:
                    if r.get(ma) in (None, ""):
                        continue
                    try:
                        v = int(r.get(ma))
                    except Exception:
                        return _loi("rubric_sai")
                    if not 0 <= v <= toi_da:
                        return _loi("rubric_sai")
                    moi[ma] = v
                cu = (hv.get("rubric") or {}).get("diem") or {}
                hv["rubric"] = {"diem": {**cu, **moi}, "ghi_chu": str(r.get("ghi_chu") or "")[:1000],
                                "nguoi": nguoi, "ts": int(time.time())}
                viec.append("rubric")
            if "must_pass" in body:
                mp = body.get("must_pass") or {}
                for ma, _ in MUST_PASS:
                    v = mp.get(ma)
                    if v in ("dat", "truot"):
                        hv.setdefault("must_pass", {})[ma] = v
                    elif v in (None, ""):
                        continue
                    else:
                        return _loi("must_pass_sai")
                viec.append("must-pass")
            if not viec:
                return _loi("khong_co_gi_de_cham")
            _lich_su(hv, nguoi, "chấm " + ", ".join(viec))
            _ghi(deps.state_path(), d)
        return {"ok": True}

    @router.post("/lo-trinh/hoc-vien/{eid}/nghi")
    async def lo_trinh_nghi(eid: str, request: Request, body: dict = Body(...)):
        vai, st = _vai(deps, request)
        ngay = str(body.get("ngay") or "")
        if not _NGAY_RE.match(ngay):
            return _loi("ngay_sai")
        with _LOCK:
            d = _doc(deps.state_path())
            hv = _tim(d, eid)
            if not hv:
                return _loi("khong_thay", 404)
            if not _quan_ly_duoc(vai, st, hv, deps):
                return _loi("khong_du_quyen", 403)
            if ngay <= hv["ngay_bat_dau"]:
                return _loi("ngay_truoc_bat_dau")
            nghi = set(hv.get("ngay_nghi") or [])
            if body.get("bo"):
                nghi.discard(ngay)
            else:
                nghi.add(ngay)
            hv["ngay_nghi"] = sorted(nghi)
            _lich_su(hv, (st or {}).get("ten") or "quản trị",
                     ("bỏ ngày nghỉ " if body.get("bo") else "duyệt ngày nghỉ ") + ngay)
            _ghi(deps.state_path(), d)
        return {"ok": True, "ngay_nghi": hv["ngay_nghi"]}

    @router.post("/lo-trinh/hoc-vien/{eid}/ket-luan")
    async def lo_trinh_ket_luan(eid: str, request: Request, body: dict = Body(...)):
        vai, st = _vai(deps, request)
        kq = str(body.get("ket_qua") or "")
        if kq not in KET_LUAN:
            return _loi("ket_luan_sai")
        ly_do = str(body.get("ly_do") or "").strip()[:1000]
        if kq != "dat" and not ly_do:
            return _loi("can_ly_do")
        nguoi = (st or {}).get("ten") or "quản trị"
        with _LOCK:
            d = _doc(deps.state_path())
            hv = _tim(d, eid)
            if not hv:
                return _loi("khong_thay", 404)
            if not _quan_ly_duoc(vai, st, hv, deps):
                return _loi("khong_du_quyen", 403)
            if hv.get("trang_thai") != "dang_hoc":
                return _loi("lo_trinh_da_dong", 409)
            ds = doc_bai_hoc(_goc(deps), hv["cap_do"])
            dx = de_xuat(hv, ds, ngay_dao_tao(hv["ngay_bat_dau"], hv.get("ngay_nghi"), deps.today()))
            hv["ket_luan"] = {"ket_qua": kq, "ly_do": ly_do, "de_xuat_luc_do": dx["ket_qua"],
                              "nguoi": nguoi, "ts": int(time.time())}
            if kq in KET_LUAN_DONG:
                hv["trang_thai"] = "da_ket_luan"
            _lich_su(hv, nguoi, f"kết luận: {kq}" + (f" ({ly_do})" if ly_do else ""))
            _ghi(deps.state_path(), d)
        return {"ok": True, "trang_thai": hv["trang_thai"]}

    app.include_router(router)


# ============================================================ gửi tin bài hôm nay (Telegram)

def viec_can_gui(d: dict, deps: LoTrinhDeps, hom_nay: str) -> list:
    """(id học viên, chat_id, ngày đào tạo, tiêu đề) của các bài hôm nay chưa gửi tin."""
    out, cache = [], {}
    for hv in d.get("hoc_vien") or []:
        chat = hv.get("telegram_chat_id")
        if hv.get("trang_thai") != "dang_hoc" or not chat:
            continue
        n = ngay_dao_tao(hv["ngay_bat_dau"], hv.get("ngay_nghi"), hom_nay)
        if n < 0 or (hv.get("da_gui") or {}).get(str(n)):
            continue
        bai = cache.setdefault(hv["cap_do"], doc_bai_hoc(_goc(deps), hv["cap_do"]))
        b = next((x for x in bai if x["ngay"] == n), None)
        if b:
            out.append((hv["id"], chat, n, b["tieu_de"]))
    return out


async def gui_bai_hom_nay(deps: LoTrinhDeps) -> int:
    """Một lượt gửi. Gửi lỗi thì không đánh dấu, lượt sau thử lại; không bao giờ ném lỗi."""
    if deps.tg_send is None or deps.now_hour() < GIO_GUI:
        return 0
    hom_nay = deps.today()
    d = await asyncio.to_thread(_doc, deps.state_path())
    viec = await asyncio.to_thread(viec_can_gui, d, deps, hom_nay)
    da = 0
    for eid, chat, n, tieu_de in viec:
        text = (f"Joyce - Lộ trình học việc\nBài ngày {n}: {tieu_de}\n"
                f"Mở Joyce, vào tab Lộ trình để đọc bài và làm bài kiểm tra.")
        try:
            ok, _ = await deps.tg_send(chat, text)
        except Exception:
            ok = False
        if not ok:
            continue
        with _LOCK:
            d2 = _doc(deps.state_path())
            hv = next((x for x in d2["hoc_vien"] if x.get("id") == eid), None)
            if hv is not None:
                hv.setdefault("da_gui", {})[str(n)] = int(time.time())
                _ghi(deps.state_path(), d2)
                da += 1
    return da


async def vong_gui_bai(deps: LoTrinhDeps, chu_ky: int = 1800) -> None:
    while True:
        try:
            await gui_bai_hom_nay(deps)
        except Exception as e:  # noqa: BLE001 - vòng nền không được chết
            print(f"[lộ trình] gửi bài: {type(e).__name__}: {e}")
        await asyncio.sleep(chu_ky)
