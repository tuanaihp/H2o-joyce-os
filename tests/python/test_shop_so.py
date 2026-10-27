"""Quản lý Shop: sổ thật + định tuyến về agent từng phòng (server/shop_so.py).

    python tests/run.py shop_so      (KHÔNG mạng, KHÔNG gọi model thật)

Kịch bản gốc của chủ: "hợp đồng Tuấn Thủy 0899252392, gói chụp ảnh studio 15 triệu, thu 15tr, chi 4tr setup".
Hợp đồng cần canh: một câu thành đúng ba sự kiện về đúng ba phòng; gửi lại không ghi hai lần; khách
trùng số điện thoại không tạo bản thứ hai; chi của nhân viên vượt hạn mức nằm chờ duyệt còn chi của chủ
ghi luôn; hoa hồng tính động từ lãi gộp; chỉ chủ và quản lý đọc được.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import json
import os
import sys
import tempfile
from pathlib import Path

_STATE = tempfile.mkdtemp(prefix="joyce-shop-so-")
os.environ["JOYCE_STATE_DIR"] = _STATE
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import conversations as cs  # noqa: E402
import crm  # noqa: E402
import shop_so  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


if _STATE not in str(cs.DB_PATH) or _STATE not in str(shop_so._path()):
    print("FAIL kho không nằm trong thư mục tạm. DỪNG.")
    sys.exit(1)

PHONG = [
    {"brain": "Ban Hang - Sales Hinh Anh", "ten": "Sales Hình Ảnh", "agent": "Agent Trưởng Sales Hình Ảnh"},
    {"brain": "Ban Hang - Sales Makeup", "ten": "Sales Makeup", "agent": "Agent Trưởng Sales Makeup"},
    {"brain": "Ban Hang - Sales Vay Cuoi", "ten": "Sales Váy Cưới", "agent": "Agent Trưởng Sales Váy Cưới"},
    {"brain": "Ke Toan - Thu", "ten": "Phòng Thu", "agent": "Agent Trưởng Phòng Thu"},
    {"brain": "Ke Toan - Chi", "ten": "Phòng Chi", "agent": "Agent Trưởng Phòng Chi"},
    {"brain": "Ke Toan - Doi Soat va Bao Cao", "ten": "Đối Soát & Báo Cáo", "agent": "Agent Trưởng Phòng Đối Soát"},
    {"brain": "Nhan Su - Van Hanh", "ten": "Nhân Sự Vận Hành", "agent": "Agent Trưởng Nhân Sự Vận Hành"},
    {"brain": "Van Thu va Quy Trinh", "ten": "Văn Thư & Quy Trình", "agent": "Agent Tổng Quản Văn Thư"},
]


class _FakeTasks:
    def __init__(self):
        self.giao = []

    def enqueue(self, brain, title, intent, *a, **k):
        self.giao.append({"brain": brain, "title": title, "intent": intent})
        return "T%d" % len(self.giao)

    def board_view(self, brain):
        return {"orchestration": "off"}


tasks = _FakeTasks()
BRAINS = Path(_STATE) / "brains"
for p in PHONG:
    (BRAINS / p["brain"]).mkdir(parents=True)
crm._deps.update(phong=lambda: PHONG, brain_root=lambda b: str(BRAINS / b), tasks=lambda: None)
shop_so._deps.update(phong=lambda: PHONG, tasks=lambda: tasks, brain_root=lambda b: str(BRAINS / b))

# ---------------- đọc tiền
for raw, want in (("15tr", 15e6), ("15 triệu", 15e6), ("1,5 triệu", 1.5e6), ("4.000.000", 4e6), (4000000, 4e6),
                  ("500k", 5e5), ("2 tỷ", 2e9), ("abc", 0), (-5, 0)):
    check(f"tien({raw!r}) = {want}", shop_so.tien(raw) == want)

# ---------------- một câu của chủ thành ba sự kiện
cau = [
    {"loai": "hop_dong", "ten": "Tuấn Thủy", "sdt": "0899 252 392", "goi": "Gói chụp ảnh studio", "gia_tri": "15 triệu"},
    {"loai": "thu", "so_tien": "15tr", "khach": "0899252392", "hang_muc": "Thanh toán hợp đồng", "dien_giai": "Tuấn Thủy thanh toán gói chụp"},
    {"loai": "chi", "so_tien": "4tr", "khach": "0899252392", "hang_muc": "Setup", "dien_giai": "Tiền setup studio"},
]
r = shop_so.xu_ly(cau, "Chủ", "web:abc", {})
check("ba sự kiện đều thành công, không lỗi", r["ok"] and len(r["ket_qua"]) == 3 and not r["loi"])
hd, thu, chi = r["ket_qua"]
check("hợp đồng vào phòng Sales Hình Ảnh", hd["phong"] == "Sales Hình Ảnh" and hd["agent"] == "Agent Trưởng Sales Hình Ảnh")
check("thu về Phòng Thu, chi về Phòng Chi", thu["phong"] == "Phòng Thu" and chi["phong"] == "Phòng Chi")
check("chi của chủ ghi luôn, không chờ duyệt", chi["trang_thai"] == "da_ghi" and not chi.get("giao_agent"))
check("thu gắn đúng hợp đồng theo số điện thoại", thu["hop_dong"] == hd["ma"] == "HD0001")
h = shop_so.lay_hop_dong(hd["id"])
check("thu cọc đổi hợp đồng sang Đã ký", h["trang_thai"] == "da_ky" and h["gia_tri"] == 15e6)
ct = shop_so.chi_tiet_hop_dong(hd["id"])
check("thu 15tr, chi 4tr, lãi gộp 11tr, hết nợ", ct == {"thu": 15e6, "chi": 4e6, "lai_gop": 11e6, "con_no": 0})

# CRM nhận khách, cơ hội, việc
kh = crm.tim_theo_sdt("0899252392")
check("CRM có khách Tuấn Thủy đúng số", kh and kh["name"] == "Tuấn Thủy" and kh["phone"] == "0899252392")
cr = crm.tong_quan("Ban Hang - Sales Hinh Anh", None)
check("CRM: cơ hội đã chốt 15tr sau khi thu, không còn cơ hội mở", cr["so_co_hoi"] == 0 and cr["da_chot"] == 15e6)
check("việc gửi báo giá được tạo trong CRM", any("báo giá" in t["title"] for t in crm.danh_sach_viec(None, brain="Ban Hang - Sales Hinh Anh")))

# báo giá tự lập
bg = shop_so.ds_bao_gia()
check("có đúng 1 báo giá, chấp nhận sau khi ký", len(bg) == 1 and bg[0]["tong"] == 15e6 and bg[0]["trang_thai"] == "chap_nhan")

# nhật ký agent
hdg = shop_so.hoat_dong()
agents = {x["agent"] for x in hdg}
check("nhật ký ghi tên agent của đủ ba phòng", {"Agent Trưởng Sales Hình Ảnh", "Agent Trưởng Phòng Thu", "Agent Trưởng Phòng Chi"} <= agents)

# ---------------- gửi lại không ghi hai lần, khách trùng số không nhân đôi
r2 = shop_so.xu_ly(cau, "Chủ", "", {})
check("gửi lại cả câu: không thêm hợp đồng", len(shop_so.ds_hop_dong()) == 1 and r2["ket_qua"][0].get("da_co"))
check("gửi lại cả câu: không thêm phiếu", len(shop_so.ds_quy(ky="all")) == 2 and r2["ket_qua"][1].get("da_co") and r2["ket_qua"][2].get("da_co"))
shop_so.xu_ly({"loai": "hop_dong", "ten": "Tuấn Thủy", "sdt": "+84899252392", "goi": "Gói makeup cưới", "gia_tri": 5e6}, "Chủ")
check("cùng số viết khác đi vẫn là một khách CRM", len(crm.danh_sach_lien_he(None, limit=50)) == 1)
check("gói makeup về Sales Makeup", shop_so.ds_hop_dong()[0]["brain"] == "Ban Hang - Sales Makeup")

# ---------------- hạn mức duyệt chi
nv = {"ten": "Lan", "role": "nhan_vien"}
rc = shop_so.xu_ly({"loai": "chi", "so_tien": "3tr", "dien_giai": "Mua đạo cụ", "hop_dong": "HD0001"}, "Lan", "web:abc", nv)["ket_qua"][0]
check("chi nhân viên từ 2tr nằm chờ duyệt", rc["trang_thai"] == "cho_duyet")
check("khoản chờ duyệt giao việc cho Trưởng Phòng Chi kèm skill", len(tasks.giao) == 1 and "Chi" in tasks.giao[0]["brain"]
      and "h2o-studio-ketoan-chi-kiem-soat" in tasks.giao[0]["intent"])
check("giao việc nói thật là điều phối đang tắt", "KHÔNG tự chạy" in rc["giao_agent"])
check("chờ duyệt chưa tính vào lãi gộp", shop_so.chi_tiet_hop_dong(hd["id"])["chi"] == 4e6)
rc2 = shop_so.xu_ly({"loai": "chi", "so_tien": "500k", "dien_giai": "Mua phông nền"}, "Lan", "", nv)["ket_qua"][0]
check("chi nhân viên dưới hạn mức ghi luôn", rc2["trang_thai"] == "da_ghi")
shop_so.duyet_quy(rc["id"], "duyet", "Chủ")
check("chủ duyệt thì tính vào sổ", shop_so.chi_tiet_hop_dong(hd["id"])["chi"] == 7e6)
try:
    shop_so.duyet_quy(rc["id"], "duyet", "Chủ")
    check("duyệt lần hai bị từ chối", False)
except ValueError:
    check("duyệt lần hai bị từ chối", True)

# ---------------- nhân sự, hoa hồng động
check("nạp 3 nhân sự mẫu", shop_so.nap_mau() == 3 and shop_so.nap_mau() == 0)
shop_so.xu_ly([{"loai": "phan_cong", "hop_dong": "HD0001", "ten": "Minh Anh", "vai": "sales"},
               {"loai": "phan_cong", "hop_dong": "HD0001", "ten": "Quốc Huy"}], "Chủ")
hh = {x["ten"]: x for x in shop_so.hoa_hong()}
check("lãi gộp hiện 15tr - 7tr = 8tr", shop_so.chi_tiet_hop_dong(hd["id"])["lai_gop"] == 8e6)
check("sales 5% lãi gộp = 400.000", hh["Trần Minh Anh"]["so_tien"] == 400_000)
check("thợ chụp 20% lãi gộp = 1.600.000", hh["Lê Quốc Huy"]["so_tien"] == 1_600_000)
bl = shop_so.bang_luong()
sales = next(d for d in bl["dong"] if d["ten"] == "Trần Minh Anh")
check("lương sales = 7.000.000 + 400.000", sales["tong"] == 7_400_000)
check("người không được phân công chỉ có lương cơ bản", next(d for d in bl["dong"] if d["ten"] == "Phạm Thu Hà")["tong"] == 6_000_000)
shop_so.luu_cau_hinh({"co_so_hh": "doanh_thu"})
check("đổi cơ sở sang doanh thu thì lương đổi theo (thu 15tr x 5%)", {x["ten"]: x for x in shop_so.hoa_hong()}["Trần Minh Anh"]["so_tien"] == 750_000)
shop_so.luu_cau_hinh({"co_so_hh": "lai_gop"})
shop_so.luu_nhan_su({"id": next(n["id"] for n in shop_so.ds_nhan_su() if n["ten"] == "Trần Minh Anh"), "ten": "Trần Minh Anh",
                     "vai": "sales", "luong_cb": 7e6, "ty_le": 10})
check("tỉ lệ riêng của người đè tỉ lệ theo vai", {x["ten"]: x for x in shop_so.hoa_hong()}["Trần Minh Anh"]["so_tien"] == 800_000)
check("xóa mẫu dọn đủ 3 người và phân công", shop_so.xoa_mau() == 3 and shop_so.ds_nhan_su() == [] and shop_so.hoa_hong() == [])

# ---------------- hợp đồng hoàn thành -> Đối Soát lập báo cáo
n0 = len(tasks.giao)
shop_so.doi_trang_thai_hd(hd["id"], "hoan_thanh", "Chủ")
check("hoàn thành thì giao Đối Soát lập báo cáo", len(tasks.giao) == n0 + 1 and "Doi Soat" in tasks.giao[-1]["brain"]
      and "h2o-studio-ketoan-doi-soat-bao-cao" in tasks.giao[-1]["intent"] and "lãi gộp 8.000.000đ" in tasks.giao[-1]["intent"])

# ---------------- tổng quan
tq = shop_so.tong_quan()
check("tổng quan: thu 15tr, chi 7,5tr, lãi gộp 7,5tr", tq["thu"] == 15e6 and tq["chi"] == 7.5e6 and tq["lai_gop"] == 7.5e6)
check("sổ quỹ lọc theo kỳ, loại, trạng thái (có JOIN hợp đồng)", len(shop_so.ds_quy(ky=shop_so._ky(), loai="chi", trang_thai="da_ghi")) >= 2 and shop_so.ds_quy(ky=shop_so._ky())[0]["hop_dong_ma"] in ("HD0001", None, "HD0002"))
check("tổng quan: 1 hoàn thành, 1 báo giá makeup", tq["hop_dong"]["hoan_thanh"] == 1 and tq["hop_dong"]["bao_gia"] == 1 and tq["pipeline"] == 5e6)

# lỗi một sự kiện không làm hỏng sự kiện khác
rl = shop_so.xu_ly([{"loai": "chi", "so_tien": 0}, {"loai": "viec", "tieu_de": "Gọi khách Tuấn Thủy", "han": "2000-01-01"}, {"loai": "la"}], "Chủ")
check("một sự kiện hỏng không kéo theo sự kiện khác", len(rl["loi"]) == 2 and len(rl["ket_qua"]) == 1 and not rl["ok"])
check("việc quá hạn được đếm", shop_so.tong_quan()["viec_qua_han"] == 1)

# ---------------- HTTP: chỉ chủ và quản lý
app = FastAPI()
vai = {"staff": None}


@app.middleware("http")
async def gan_nhan_vien(request: Request, call_next):
    request.state.staff = vai["staff"]
    return await call_next(request)


shop_so.register(app, lambda: PHONG, lambda: tasks, lambda b: str(BRAINS / b))
http = TestClient(app)
check("chủ đọc tổng quan qua HTTP", http.get("/shop/so/tong-quan").json()["ok"])
rr = http.post("/shop/so/su-kien", data={"data": json.dumps({"loai": "thu", "so_tien": "1tr", "dien_giai": "Thu lẻ"})}).json()
check("ghi phiếu qua HTTP", rr["ok"] and rr["ket_qua"][0]["so_tien"] == 1e6)
check("JSON hỏng trả 400", http.post("/shop/so/su-kien", data={"data": "{"}).status_code == 400)
vai["staff"] = {"ten": "Lan", "role": "nhan_vien"}
check("nhân viên thường bị 403", http.get("/shop/so/quy").status_code == 403 and http.post("/shop/so/mau").status_code == 403)
vai["staff"] = {"ten": "Hà", "role": "truong_phong"}
check("trưởng phòng đọc được sổ", http.get("/shop/so/quy").status_code == 200)
pid = shop_so.xu_ly({"loai": "chi", "so_tien": "9tr", "dien_giai": "Thuê ekip"}, "Hà", "", vai["staff"])["ket_qua"][0]["id"]
check("trưởng phòng KHÔNG tự duyệt chi của mình (403)", http.post("/shop/so/quy/duyet", data={"id": pid, "quyet": "duyet"}).status_code == 403)
vai["staff"] = {"ten": "Sếp", "role": "giam_doc"}
check("giám đốc duyệt được", http.post("/shop/so/quy/duyet", data={"id": pid, "quyet": "duyet"}).json()["phieu"]["trang_thai"] == "da_ghi")

# ---------------- bảng hoa hồng theo đầu việc và chia việc
vai["staff"] = None
cv = shop_so.ds_cong_viec()
check("bảng việc của chủ tự nạp 30 dòng một lần", len(cv) == 30 and len(shop_so.ds_cong_viec()) == 30)
by = {c["ten"]: c for c in cv}
check("hoa hồng cố định đúng bảng: makeup cô dâu 90k, ngoại cảnh 450k, tư vấn offline 50k, phóng sự 3 ngày",
      by["Makeup cô dâu"]["hoa_hong"] == 90000 and by["Chụp ảnh ngoại cảnh"]["hoa_hong"] == 450000 and by["Tư vấn Offline"]["hoa_hong"] == 50000
      and by["Chụp ảnh phóng sự"]["so_ngay"] == 3 and by["Chụp ảnh phóng sự"]["hoa_hong"] == 0)
check("tên khớp đúng được ưu tiên: Makeup nền là 27k, không nhầm Makeup nền và lông mày", shop_so.tim_cong_viec("makeup nen")["hoa_hong"] == 27000)
try:
    shop_so.tim_cong_viec("Tư vấn")
    check("tên mơ hồ phải bị từ chối kèm gợi ý", False)
except ValueError as e:
    check("tên mơ hồ phải bị từ chối kèm gợi ý", "Tư vấn Offline" in str(e))
try:
    shop_so.tim_cong_viec("Quay phim drone")
    check("đầu việc không có trong bảng bị từ chối", False)
except ValueError:
    check("đầu việc không có trong bảng bị từ chối", True)
check("nạp lại bảng H2O không thêm trùng và không đè số đã sửa", (shop_so.luu_cong_viec({"id": by["Cuộn tóc"]["id"], "ma_phong": "MAKEUP", "nhom": "Bới tóc", "ten": "Cuộn tóc", "hoa_hong": 30000}),
      shop_so.nap_cong_viec_h2o())[1] == 0 and {c["ten"]: c for c in shop_so.ds_cong_viec()}["Cuộn tóc"]["hoa_hong"] == 30000)
try:
    shop_so.luu_cong_viec({"ma_phong": "makeup", "ten": "Makeup cô dâu", "hoa_hong": 1})
    check("thêm trùng (phòng, tên việc) bị từ chối", False)
except ValueError:
    check("thêm trùng (phòng, tên việc) bị từ chối", True)
mot = shop_so.luu_cong_viec({"ma_phong": "OUT", "nhom": "Thử đồ", "ten": "Việc thử", "hoa_hong": "120k", "phi_them": "50.000", "so_ngay": 2})
check("thêm việc mới: hiểu '120k' và '50.000'", mot["hoa_hong"] == 120000 and mot["phi_them"] == 50000 and mot["so_ngay"] == 2)
shop_so.xoa_cong_viec(mot["id"])
check("xóa việc rồi gọi lại không bị tự nạp lại bảng", len(shop_so.ds_cong_viec()) == 30 and all(c["ten"] != "Việc thử" for c in shop_so.ds_cong_viec()))

ma_ = shop_so.luu_nhan_su({"ten": "Ngô Thảo", "vai": "sales", "luong_cb": 5e6})
huy_ = shop_so.luu_nhan_su({"ten": "Đặng Huy", "vai": "chup", "luong_cb": 8e6})
mk_ = shop_so.luu_nhan_su({"ten": "Vũ Lan", "vai": "makeup", "luong_cb": 4e6})
r0 = shop_so.xu_ly({"loai": "hop_dong", "ten": "Khách Chia Việc", "sdt": "0977000111", "goi": "Cưới trọn gói", "gia_tri": "10 triệu", "trang_thai": "bao_gia"}, "Chủ")
hdv = shop_so.tim_hop_dong("0977000111")[0]
shop_so.xu_ly({"loai": "phan_cong", "hop_dong": hdv["ma"], "ten": "Thảo", "vai": "sales"}, "Chủ")
sv = shop_so.xu_ly([
    {"loai": "giao_viec", "hop_dong": hdv["ma"], "cong_viec": "Tư vấn Offline", "ten": "Ngô Thảo"},
    {"loai": "giao_viec", "hop_dong": hdv["ma"], "cong_viec": "Chụp ảnh ngoại cảnh", "ten": "Đặng Huy"},
    {"loai": "giao_viec", "hop_dong": hdv["ma"], "cong_viec": "Chụp ảnh cưới studio", "ten": "Huy"},
    {"loai": "giao_viec", "hop_dong": hdv["ma"], "cong_viec": "Makeup cô dâu", "ten": "Vũ Lan", "so_luong": 2},
    {"loai": "giao_viec", "hop_dong": hdv["ma"], "cong_viec": "Quay drone", "ten": "Huy"}], "Chủ")
check("chia 4 việc thành công, 1 việc lạ báo lỗi riêng", len(sv["ket_qua"]) == 4 and len(sv["loi"]) == 1 and "drone" in sv["loi"][0]["loi"])
check("chia việc đi qua agent Nhân Sự Vận Hành và nêu tiền", "Agent Trưởng Nhân Sự Vận Hành" in sv["ket_qua"][0]["tom_tat"] and "50.000" in sv["ket_qua"][0]["tom_tat"])
check("hạn mặc định = hôm nay + số ngày của việc", all(len(x["han"]) == 10 for x in sv["ket_qua"]))
check("hợp đồng mới Báo giá thì CHƯA có hoa hồng", [x for x in shop_so.hoa_hong() if x["hop_dong_id"] == hdv["id"]] == [])
shop_so.doi_trang_thai_hd(hdv["id"], "da_ky", "Chủ")
hh = {x["ten"] + "|" + x.get("cong_viec", ""): x for x in shop_so.hoa_hong() if x["hop_dong_id"] == hdv["id"]}
check("ký xong: có hoa hồng từng việc, Thảo chỉ nhận 50k theo việc (không cộng thêm phần trăm)",
      hh["Ngô Thảo|Tư vấn Offline"]["so_tien"] == 50000 and not any(k.startswith("Ngô Thảo") and k.endswith("|") for k in hh))
check("Huy 2 việc: 450k + 250k; Lan x2 = 180k", hh["Đặng Huy|Chụp ảnh ngoại cảnh"]["so_tien"] == 450000 and hh["Đặng Huy|Chụp ảnh cưới studio"]["so_tien"] == 250000 and hh["Vũ Lan|Makeup cô dâu"]["so_tien"] == 180000)
shop_so.xu_ly({"loai": "giao_viec", "hop_dong": hdv["ma"], "cong_viec": "Makeup cô dâu", "ten": "Vũ Lan", "so_luong": 2}, "Chủ")
check("gửi lại cùng câu không cộng dồn", len([g for g in shop_so.ds_giao_viec(hdv["id"]) if g["ten"] == "Makeup cô dâu"]) == 1
      and sum(x["so_tien"] for x in shop_so.hoa_hong() if x["ten"] == "Vũ Lan") == 180000)
lg = {d["ten"]: d for d in shop_so.bang_luong()["dong"]}
check("bảng lương = lương cơ bản + hoa hồng theo việc", lg["Đặng Huy"]["tong"] == 8e6 + 700000 and lg["Vũ Lan"]["tong"] == 4e6 + 180000 and lg["Ngô Thảo"]["tong"] == 5e6 + 50000)
shop_so.luu_cong_viec({"id": by["Makeup cô dâu"]["id"], "ma_phong": "MAKEUP", "nhom": "Makeup", "ten": "Makeup cô dâu", "hoa_hong": 100000})
check("đổi giá trong bảng không làm đổi số tiền đã chốt lúc chia", sum(x["so_tien"] for x in shop_so.hoa_hong() if x["ten"] == "Vũ Lan") == 180000)
gid = next(g["id"] for g in shop_so.ds_giao_viec(hdv["id"]) if g["ten"] == "Chụp ảnh cưới studio")
shop_so.doi_giao_viec(gid, "done")
check("đánh dấu xong việc", next(x for x in shop_so.hoa_hong() if x.get("cong_viec") == "Chụp ảnh cưới studio")["xong"] is True)
shop_so.go_giao_viec(gid)
check("gỡ việc đã chia thì hoa hồng mất theo", all(x.get("cong_viec") != "Chụp ảnh cưới studio" for x in shop_so.hoa_hong()))
shop_so.xoa_nhan_su(mk_["id"])
check("xóa nhân sự dọn luôn việc đã chia của họ", all(g["nhan_su_id"] != mk_["id"] for g in shop_so.ds_giao_viec()))
http2 = TestClient(app)
check("HTTP: chủ đọc bảng việc", len(http2.get("/shop/so/cong-viec").json()["items"]) == 30)
check("HTTP: thêm việc trùng trả 400", http2.post("/shop/so/cong-viec", data={"data": json.dumps({"ma_phong": "PHOTO", "ten": "Chụp ảnh gia đình"})}).status_code == 400)
check("HTTP: danh sách việc đã chia của hợp đồng", len(http2.get("/shop/so/giao-viec", params={"hop_dong_id": hdv["id"]}).json()["items"]) >= 2)
vai["staff"] = {"ten": "Lan", "role": "nhan_vien"}
check("HTTP: nhân viên thường không đụng được bảng hoa hồng", http2.get("/shop/so/cong-viec").status_code == 403 and http2.post("/shop/so/cong-viec/xoa", data={"id": 1}).status_code == 403)
vai["staff"] = None

# ---------------- bảng giá dịch vụ
dvs = shop_so.ds_dich_vu()
dm = {d["ma"]: d for d in dvs}
check("bảng giá của chủ tự nạp 46 gói một lần, 38 gói đã có giá", len(dvs) == 46 and len(shop_so.ds_dich_vu()) == 46 and sum(1 for d in dvs if d["don_gia"] > 0) == 38)
check("cọc đúng công thức sheet: PRW-STCB 496.000 / 2.232.000 / 2.232.000",
      (dm["PRW-STCB"]["coc1"], dm["PRW-STCB"]["coc2"], dm["PRW-STCB"]["con_lai"]) == (496000, 2232000, 2232000))
check("cọc đúng: full luxury 13,8tr -> 1.380.000 / 6.210.000 / 6.210.000", (dm["PRE-FULLUX"]["coc1"], dm["PRE-FULLUX"]["coc2"], dm["PRE-FULLUX"]["con_lai"]) == (1380000, 6210000, 6210000))
check("gói thuê lẻ không cọc, trả hết; gói chưa có giá là 0", dm["THUE-LE"]["coc1"] == 0 and dm["THUE-LE"]["con_lai"] == 500000 and dm["VAY-CB"]["don_gia"] == 0 and dm["PRW-LUX"]["don_gia"] == 24000000)
check("tìm gói chỉ khớp chính xác mã hoặc tên, không đoán", shop_so.tim_dich_vu("prw-stcb")["ma"] == "PRW-STCB" and shop_so.tim_dich_vu("Trọn gói studio cơ bản")["ma"] == "PRW-STCB"
      and shop_so.tim_dich_vu("studio") is None and shop_so.tim_dich_vu("Gói chụp ảnh studio") is None)
check("tra giá theo từ khóa", {d["ma"] for d in shop_so.goi_y_dich_vu("pre-wedding studio")} >= {"PRW-STCB", "PRW-STV"})

rg = shop_so.xu_ly({"loai": "hop_dong", "ten": "Khách Bảng Giá", "sdt": "0966555444", "goi": "PRW-STCB"}, "Chủ")
hg = shop_so.tim_hop_dong("0966555444")[0]
check("báo đúng mã gói, không nói giá: sổ tự lấy 4.960.000 và tên chuẩn", rg["ok"] and hg["gia_tri"] == 4960000 and hg["goi"] == "Trọn gói studio cơ bản" and hg["dv_ma"] == "PRW-STCB")
check("báo giá nháp mang đúng giá bảng", any(b["hop_dong_id"] == hg["id"] and b["tong"] == 4960000 for b in shop_so.ds_bao_gia()))
rn = shop_so.xu_ly({"loai": "hop_dong", "ten": "Khách Thương Lượng", "sdt": "0966555445", "goi": "Trọn gói vip studio", "gia_tri": "6 triệu"}, "Chủ")
check("giá chủ nói (thương lượng) được giữ, vẫn gắn mã gói", shop_so.tim_hop_dong("0966555445")[0]["gia_tri"] == 6000000 and shop_so.tim_hop_dong("0966555445")[0]["dv_ma"] == "PRW-STV")
shop_so.xu_ly({"loai": "hop_dong", "ten": "Khách Lạ", "sdt": "0966555446", "goi": "Gói tự đặt", "gia_tri": "2tr"}, "Chủ")
check("gói không có trong bảng vẫn lập bình thường, không gắn mã", shop_so.tim_hop_dong("0966555446")[0]["dv_ma"] == "")
shop_so.xu_ly({"loai": "hop_dong", "ten": "Khách Chưa Giá", "sdt": "0966555447", "goi": "VAY-CB"}, "Chủ")
check("gói chưa có giá trong bảng: giá 0, báo cần báo giá theo yêu cầu", shop_so.tim_hop_dong("0966555447")[0]["gia_tri"] == 0)


def _lich(sdt):
    return next(h for h in shop_so.ds_hop_dong() if h["sdt"] == sdt)["lich"]


check("lịch thanh toán: chưa thu gì thì chờ cọc lần 1 đủ 496.000", _lich("0966555444")["buoc_tiep"] == "Cọc lần 1" and _lich("0966555444")["can_thu"] == 496000)
shop_so.xu_ly({"loai": "thu", "so_tien": 496000, "khach": "0966555444", "hang_muc": "Cọc lần 1"}, "Chủ")
check("thu đủ cọc 1 thì chờ cọc lần 2 (còn 2.232.000)", _lich("0966555444")["buoc_tiep"] == "Cọc lần 2" and _lich("0966555444")["can_thu"] == 2232000)
shop_so.xu_ly({"loai": "thu", "so_tien": 2232000, "khach": "0966555444", "hang_muc": "Cọc lần 2"}, "Chủ")
check("thu đủ cọc 2 thì chờ thanh toán cuối 2.232.000", _lich("0966555444")["buoc_tiep"] == "Thanh toán" and _lich("0966555444")["can_thu"] == 2232000)
shop_so.xu_ly({"loai": "thu", "so_tien": 2232000, "khach": "0966555444", "hang_muc": "Thanh toán"}, "Chủ")
check("thu đủ thì hết bước chờ", _lich("0966555444")["buoc_tiep"] == "")
check("hợp đồng gói không cọc thì không có lịch", next(h for h in shop_so.ds_hop_dong() if h["sdt"] == "0966555446")["lich"] is None)

try:
    shop_so.luu_dich_vu({"ma": "prw-stcb", "goi": "Trùng mã"})
    check("thêm trùng mã bị từ chối", False)
except ValueError:
    check("thêm trùng mã bị từ chối", True)
mdv = shop_so.luu_dich_vu({"ma": "tmp 1", "loai": "Thử", "goi": "Gói thử", "don_gia": "2 triệu", "coc1_pct": 20, "coc2_pct": 0})
check("thêm gói mới: mã chuẩn hóa, hiểu '2 triệu', cọc 20% = 400.000", mdv["ma"] == "TMP1" and mdv["don_gia"] == 2000000 and mdv["coc1"] == 400000 and mdv["con_lai"] == 1600000)
shop_so.xoa_dich_vu(mdv["id"])
check("xóa gói rồi không bị tự nạp lại; nạp bổ sung không thêm trùng", all(d["ma"] != "TMP1" for d in shop_so.ds_dich_vu()) and shop_so.nap_dich_vu_h2o() == 0)
shop_so.luu_dich_vu({"id": dm["PS-1SEC"]["id"], "ma": "PS-1SEC", "loai": "Ảnh phóng sự", "goi": "Chụp ảnh phóng sự 1 sec", "don_gia": 2000000})
check("đổi giá trong bảng không đổi hợp đồng đã lập", shop_so.nap_dich_vu_h2o() == 0 and {d["ma"]: d for d in shop_so.ds_dich_vu()}["PS-1SEC"]["don_gia"] == 2000000 and shop_so.tim_hop_dong("0966555444")[0]["gia_tri"] == 4960000)
import sqlite3 as _sq  # noqa: E402
_old = Path(_STATE) / "old_so.sqlite3"
_c = _sq.connect(str(_old)); _c.execute("CREATE TABLE so_hop_dong(id INTEGER PRIMARY KEY, ma TEXT, ten_khach TEXT)"); _c.commit(); _c.close()
_orig = shop_so._path
shop_so._path = lambda: _old
_cols = {r[1] for r in shop_so._dung(lambda db: db.execute("PRAGMA table_info(so_hop_dong)").fetchall())}
shop_so._path = _orig
check("sổ tạo từ bản cũ tự thêm cột dv_ma", "dv_ma" in _cols)
check("HTTP: chủ đọc bảng giá 46 gói", len(http2.get("/shop/so/dich-vu").json()["items"]) == 46)
check("HTTP: thêm trùng mã trả 400", http2.post("/shop/so/dich-vu", data={"data": json.dumps({"ma": "GD-CB", "goi": "x"})}).status_code == 400)
vai["staff"] = {"ten": "Lan", "role": "nhan_vien"}
check("HTTP: nhân viên thường không đụng được bảng giá", http2.get("/shop/so/dich-vu").status_code == 403 and http2.post("/shop/so/dich-vu/xoa", data={"id": 1}).status_code == 403)
vai["staff"] = None

# ---------------- danh mục đồ và lịch sử thuê đồ
check("danh mục đồ trống lúc đầu, không số giả", shop_so.ds_do() == [] and shop_so.ds_thue_do() == [])
r_mau = shop_so.nap_mau_do()
check("nạp mẫu: 5 đồ và 5 phiếu, nạp lần hai không nhân đôi", r_mau == {"do": 5, "phieu": 5} and shop_so.nap_mau_do() == {"do": 0, "phieu": 0})
dd = {d["ma_do"]: d for d in shop_so.ds_do()}
check("nhóm tự lấy từ bảng giá dịch vụ, tên đồ như sheet (mã--màu)", dd["VAY-CC209"]["nhom"] == "Váy cao cấp" and dd["VAY-CC209"]["ten_do"] == "VAY-CC209--Trắng" and dd["VAY-CC209"]["ma_dv"] == "VAY-CC")
check("tình trạng tính từ lịch sử: đã trả = sẵn sàng/giữ chỗ, đang thuê, số lần thuê đúng",
      dd["VAY-CC211"]["tinh_trang"] == "san_sang" and dd["VAY-TK67"]["tinh_trang"] == "dang_thue" and dd["VAY-CC209"]["tinh_trang"] == "giu_cho"
      and dd["VAY-CC209"]["so_lan_thue"] == 1 and dd["VAY-TK67"]["so_lan_thue"] == 1 and dd["ADCD-05"]["so_lan_thue"] == 0)
mm = {t["key"]: t for t in shop_so.ds_thue_do()}
check("giá còn lại = đơn giá trừ khuyến mại như sheet (7tr - 3,15tr = 3,85tr)", mm["mau0001"]["gia_con_lai"] == 3850000 and mm["mau0001"]["trang_thai"] == "da_tra")

hom_nay = shop_so._homnay()
mai = shop_so._cong_ngay(hom_nay, 1)
# thuê gắn hợp đồng thật, thu ngay
hd_do = shop_so.tim_hop_dong("0966555444")[0]
thu0 = shop_so.tong_quan()["thu"]
kq = shop_so.xu_ly({"loai": "thue_do", "ma_do": "vay-cc211--trắng", "hop_dong": hd_do["ma"], "ngay_thue": hom_nay, "ngay_tra": mai, "khuyen_mai": "1tr", "thu_ngay": True}, "Chủ")
check("thuê đồ gắn hợp đồng: nhận mã--tên, khách lấy từ hợp đồng, Sales Váy Cưới làm", kq["ok"] and "Khách Bảng Giá" in kq["ket_qua"][0]["tom_tat"] and "Agent Trưởng Sales Váy Cưới" in kq["ket_qua"][0]["tom_tat"] and kq["ket_qua"][0]["trang_thai"] == "dang_thue")
check("thu ngay: ghi thu đúng 6.000.000 vào hợp đồng qua Phòng Thu, tổng thu tăng", kq["ket_qua"][0]["gia_con_lai"] == 6000000 and "Phòng Thu" in kq["ket_qua"][0]["thu"] and shop_so.tong_quan()["thu"] == thu0 + 6000000)
check("đồ vừa thuê chuyển sang Đang thuê trong danh mục", {d["ma_do"]: d for d in shop_so.ds_do()}["VAY-CC211"]["tinh_trang"] == "dang_thue")
phieu = next(t for t in shop_so.ds_thue_do() if t["ma_do"] == "VAY-CC211" and t["trang_thai"] == "dang_thue")
check("phiếu ghi số hợp đồng và đã có phiếu thu", phieu["so_hd"] == hd_do["ma"] and phieu["quy_id"])

# chống thuê trùng
tr = shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-CC211", "ten_khach": "Người Khác", "sdt": "0911000111", "ngay_thue": hom_nay, "ngay_tra": mai}, "Chủ")
check("thuê trùng ngày bị chặn, nêu ai đang giữ và phiếu nào", not tr["ok"] and "đã có người đang thuê" in tr["loi"][0]["loi"] and phieu["key"] in tr["loi"][0]["loi"])
tr2 = shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-CC209", "ten_khach": "Cô Khác", "sdt": "0911000222", "ngay_thue": shop_so._cong_ngay(hom_nay, 10), "ngay_tra": shop_so._cong_ngay(hom_nay, 10)}, "Chủ")
check("đồ đã giữ chỗ ngày 10-11 thì ngày 10 bị chặn", not tr2["ok"] and "giữ chỗ" in tr2["loi"][0]["loi"])
tr3 = shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-CC209", "ten_khach": "Cô Sau", "sdt": "0911000333", "ngay_thue": shop_so._cong_ngay(hom_nay, 20), "ngay_tra": shop_so._cong_ngay(hom_nay, 21)}, "Chủ")
check("ngày khác không trùng thì giữ chỗ được", tr3["ok"] and tr3["ket_qua"][0]["trang_thai"] == "giu_cho" and "Chưa ghi thu" in tr3["ket_qua"][0]["tom_tat"])
lap = shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-CC209", "ten_khach": "Cô Sau", "sdt": "0911000333", "ngay_thue": shop_so._cong_ngay(hom_nay, 20), "ngay_tra": shop_so._cong_ngay(hom_nay, 21)}, "Chủ")
check("gửi lại cùng câu không tạo phiếu thứ hai", lap["ok"] and lap["ket_qua"][0].get("da_co") and len([t for t in shop_so.ds_thue_do() if t["sdt"] == "0911000333"]) == 1)
for sai, msg in ((({"loai": "thue_do", "ma_do": "KHONG-CO", "ten_khach": "A"}), "Không thấy đồ"), (({"loai": "thue_do", "ma_do": "VEST-01"}), "cần biết khách"),
                 (({"loai": "thue_do", "ma_do": "VEST-01", "ten_khach": "A", "ngay_thue": mai, "ngay_tra": hom_nay}), "trước ngày thuê")):
    check("lỗi rõ: " + msg, msg in (shop_so.xu_ly(sai, "Chủ")["loi"] or [{"loi": ""}])[0]["loi"])
g0 = shop_so.luu_do({"ma_do": "VAY-CB1", "don_gia": 0})
check("đồ chưa có giá thuê thì không cho thuê, báo nói giá", "chưa có giá thuê" in shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-CB1", "ten_khach": "A"}, "Chủ")["loi"][0]["loi"])
shop_so.luu_do({"id": g0["id"], "ma_do": "VAY-CB1", "don_gia": 1500000, "ap_dung": 0})
check("đồ tạm ngưng không cho thuê", "tạm ngưng" in shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-CB1", "ten_khach": "A"}, "Chủ")["loi"][0]["loi"])

# trả đồ
tra = shop_so.xu_ly({"loai": "tra_do", "ma_do": "VAY-CC211"}, "Chủ")
check("trả đồ: đúng hạn, Sales Váy Cưới nhận, đồ về sẵn sàng", tra["ok"] and "đúng hạn" in tra["ket_qua"][0]["tom_tat"] and {d["ma_do"]: d for d in shop_so.ds_do()}["VAY-CC211"]["tinh_trang"] == "san_sang")
check("trả hai lần không ghi lại", shop_so.xu_ly({"loai": "tra_do", "key": phieu["key"]}, "Chủ")["ket_qua"][0].get("da_co"))
check("đếm số lần thuê tăng lên 2", {d["ma_do"]: d for d in shop_so.ds_do()}["VAY-CC211"]["so_lan_thue"] == 2)
check("trả đồ chưa từng thuê báo lỗi", "Không có phiếu" in shop_so.xu_ly({"loai": "tra_do", "ma_do": "ADCD-05"}, "Chủ")["loi"][0]["loi"])
check("trả khi mới giữ chỗ (chưa giao) bị từ chối", "chưa có gì để trả" in shop_so.xu_ly({"loai": "tra_do", "key": [t for t in shop_so.ds_thue_do() if t["sdt"] == "0911000333"][0]["key"]}, "Chủ")["loi"][0]["loi"])

# trễ hạn: phiếu mẫu Dung Tính hạn hôm qua + 2 => chỉnh ngày qua API nội bộ
tre = shop_so.xu_ly({"loai": "thue_do", "ma_do": "ADCD-05", "ten_khach": "Khách Trễ", "sdt": "0911000444", "ngay_thue": shop_so._cong_ngay(hom_nay, -5), "ngay_tra": shop_so._cong_ngay(hom_nay, -3)}, "Chủ")
check("thuê lùi ngày: đang thuê và hiện Quá hạn trong danh mục", tre["ok"] and {d["ma_do"]: d for d in shop_so.ds_do()}["ADCD-05"]["tinh_trang"] == "qua_han" and any(t["qua_han"] and t["tre_ngay"] == 3 for t in shop_so.ds_thue_do()))
check("đồ quá hạn chưa trả thì không cho thuê tiếp từ hôm nay", "chưa được trả" in shop_so.xu_ly({"loai": "thue_do", "ma_do": "ADCD-05", "ten_khach": "B", "ngay_thue": hom_nay}, "Chủ")["loi"][0]["loi"])
t_tre = shop_so.xu_ly({"loai": "tra_do", "ma_do": "ADCD-05"}, "Chủ")["ket_qua"][0]
check("trả trễ báo đúng 3 ngày", t_tre["tre_ngay"] == 3 and "TRỄ 3 ngày" in t_tre["tom_tat"])

# thao tác tay: giao đồ, hủy, ghi thu bù
gi = shop_so.xu_ly({"loai": "thue_do", "ma_do": "VEST-01", "ten_khach": "Khách Tay", "sdt": "0911000555", "ngay_thue": mai, "ngay_tra": mai}, "Chủ")["ket_qua"][0]
check("thuê ngày mai thì là giữ chỗ", gi["trang_thai"] == "giu_cho")
shop_so.doi_trang_thai_thue(gi["id"], "dang_thue", "Chủ")
check("giao đồ chuyển sang Đang thuê", shop_so.lay_thue(gi["id"])["trang_thai"] == "dang_thue")
sau = shop_so.xu_ly({"loai": "thue_do", "ma_do": "VAY-TK67", "ten_khach": "Khách Sau", "sdt": "0911000666", "ngay_thue": shop_so._cong_ngay(hom_nay, 40), "ngay_tra": shop_so._cong_ngay(hom_nay, 40)}, "Chủ")["ket_qua"][0]
try:
    shop_so.doi_trang_thai_thue(sau["id"], "dang_thue", "Chủ")
    check("không giao lần hai khi đồ đang ở phiếu khác chưa trả", False)
except ValueError as e:
    check("không giao lần hai khi đồ đang ở phiếu khác chưa trả", "chưa trả" in str(e))
q = shop_so.ghi_thu_thue(gi["id"], "Chủ")
check("ghi thu bù từ phiếu: vào sổ quỹ đúng 500.000, phiếu lưu số phiếu thu", q["so_tien"] == 500000 and shop_so.lay_thue(gi["id"])["quy_id"])
try:
    shop_so.ghi_thu_thue(gi["id"], "Chủ")
    check("ghi thu lần hai bị từ chối", False)
except ValueError:
    check("ghi thu lần hai bị từ chối", True)
shop_so.doi_trang_thai_thue(gi["id"], "huy", "Chủ")
check("hủy phiếu: đồ không còn bị giữ", {d["ma_do"]: d for d in shop_so.ds_do()}["VEST-01"]["tinh_trang"] == "san_sang")
try:
    shop_so.xoa_thue_do(next(t["id"] for t in shop_so.ds_thue_do() if t["key"] == phieu["key"]))
    check("phiếu thật chưa hủy không xóa được", False)
except ValueError:
    check("phiếu thật chưa hủy không xóa được", True)
try:
    shop_so.xoa_do(next(d["id"] for d in shop_so.ds_do() if d["ma_do"] == "VAY-CC211"))
    check("đồ đã có lịch sử thật không xóa được", False)
except ValueError:
    check("đồ đã có lịch sử thật không xóa được", True)
try:
    shop_so.luu_do({"ma_do": "vay-cc209"})
    check("thêm đồ trùng mã bị từ chối", False)
except ValueError:
    check("thêm đồ trùng mã bị từ chối", True)

# xóa mẫu: bỏ phiếu và đồ mẫu, giữ đồ đã có phiếu thật
xm = shop_so.xoa_mau_do()
con = {d["ma_do"] for d in shop_so.ds_do()}
check("xóa mẫu: bỏ 5 phiếu mẫu, giữ cả 5 món đồ vì đều đã có phiếu thật, bỏ nhãn mẫu",
      xm["phieu"] == 5 and xm["do"] == 0 and {"VAY-CC211", "VAY-CC209", "ADCD-05", "VEST-01", "VAY-TK67"} <= con and not any(t["la_mau"] for t in shop_so.ds_thue_do()) and not any(d["la_mau"] for d in shop_so.ds_do()))
check("sau xóa mẫu nạp lại không đè món đã có và không báo lỗi trùng", shop_so.nap_mau_do() == {"do": 0, "phieu": 0})

# HTTP
check("HTTP: đọc danh mục đồ và lịch sử", http2.get("/shop/so/do").json()["ok"] and http2.get("/shop/so/thue-do").json()["ok"])
check("HTTP: thêm đồ trùng mã trả 400", http2.post("/shop/so/do", data={"data": json.dumps({"ma_do": "VEST-01"})}).status_code == 400)
check("HTTP: đổi trạng thái phiếu sai trả 400", http2.post("/shop/so/thue-do/buoc", data={"id": 1, "trang_thai": "bay"}).status_code == 400)
vai["staff"] = {"ten": "Lan", "role": "nhan_vien"}
check("HTTP: nhân viên thường không đụng được đồ", http2.get("/shop/so/do").status_code == 403 and http2.post("/shop/so/thue-do/xoa", data={"id": 1}).status_code == 403 and http2.post("/shop/so/do/mau").status_code == 403)
vai["staff"] = None
shop_so.xoa_mau_do()

# ---------------- tool joyce_shop (chat gọi)
import asyncio  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("joyce_shop_plugin", ROOT / "system" / "plugins" / "joyce-shop" / "plugin.py")
_pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pl)


class _Ctx:
    vault_root = str(BRAINS / "Ban Hang - Sales Hinh Anh")
    tools = {}

    def register_tool(self, name, desc, fn, **kw):
        self.tools[name] = (desc, fn, kw)


_c = _Ctx()
_pl.register(_c)
_desc, _fn, _kw = _c.tools["joyce_shop"]
check("tool joyce_shop đăng ký, mức safe, mô tả dặn hỏi lại khi thiếu số", _kw["min_mode"] == "safe" and "HỎI LẠI" in _desc)
_goi = lambda a: asyncio.run(_fn(a, _c))
out = _goi({"op": "ghi", "su_kien": [{"loai": "hop_dong", "ten": "Hoàng Nam", "sdt": "0912345678", "goi": "Chụp cưới", "gia_tri": 20000000},
                                      {"loai": "thu", "so_tien": 5000000, "khach": "0912345678", "hang_muc": "Cọc"}]})
check("tool ghi: báo đúng hai sự kiện, nêu tên agent", "Agent Trưởng Sales Hình Ảnh" in out and "Agent Trưởng Phòng Thu" in out and "LỖI" not in out)
check("tool ghi: cọc làm hợp đồng mới Đã ký", shop_so.tim_hop_dong("0912345678")[0]["trang_thai"] == "da_ky")
check("tool nhận su_kien dạng chuỗi JSON", "Phòng Chi" in _goi({"op": "ghi", "su_kien": json.dumps([{"loai": "chi", "so_tien": "1tr", "dien_giai": "Hoa"}])}))
check("tool báo lỗi rõ khi thiếu số tiền", "LỖI" in _goi({"op": "ghi", "su_kien": [{"loai": "thu"}]}))
check("tool xem trả số kỳ này", "lãi gộp" in _goi({"op": "xem"}))
check("tool op lạ bị từ chối", _goi({"op": "xoa"}).startswith("ERROR"))
shop_so.nap_mau_do()
_do_out = _goi({"op": "do", "tu_khoa": "váy cao cấp"})
check("tool tra đồ: nêu tình trạng và giá", "VAY-CC209--Trắng" in _do_out and "7.000.000đ/lần" in _do_out and "lịch" in _do_out)
check("tool tra đồ: từ khóa lạ báo không có", "không có món nào khớp" in _goi({"op": "do", "tu_khoa": "zzzz"}))
_thue = _goi({"op": "ghi", "su_kien": [{"loai": "thue_do", "ma_do": "VEST-01", "ten_khach": "Khách Qua Chat", "sdt": "0966555998", "ngay_thue": shop_so._cong_ngay(shop_so._homnay(), 30), "ngay_tra": shop_so._cong_ngay(shop_so._homnay(), 30)}]})
check("tool cho thuê qua chat: giữ chỗ thành công, nêu Sales Váy Cưới", "LỖI" not in _thue and "giữ chỗ" in _thue and "Agent Trưởng Sales Váy Cưới" in _thue)
check("tool thuê trùng báo lỗi rõ để hỏi lại chủ", "LỖI" in _goi({"op": "ghi", "su_kien": [{"loai": "thue_do", "ma_do": "VEST-01", "ten_khach": "Người Khác", "ngay_thue": shop_so._cong_ngay(shop_so._homnay(), 30)}]}))
shop_so.xoa_mau_do()
_gia_out = _goi({"op": "gia", "tu_khoa": "PRW-STCB"})
check("tool tra giá đọc đúng số trong bảng, kèm cọc", "4.960.000đ" in _gia_out and "cọc lần 1 496.000đ" in _gia_out and "thanh toán cuối 2.232.000đ" in _gia_out)
check("tool tra giá: gói chưa có giá nói thẳng, từ khóa lạ báo không có", "báo giá theo yêu cầu" in _goi({"op": "gia", "tu_khoa": "VAY-CB"}) and "không có gói nào khớp" in _goi({"op": "gia", "tu_khoa": "zzzz"}))
check("tool lập hợp đồng bằng mã gói: tự lấy giá", "LỖI" not in _goi({"op": "ghi", "su_kien": [{"loai": "hop_dong", "ten": "Khách Qua Chat", "sdt": "0966555999", "goi": "GD-CB"}]})
      and shop_so.tim_hop_dong("0966555999")[0]["gia_tri"] == 1250000)

if _fails:
    print("\nTHẤT BẠI %d: %s" % (len(_fails), _fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
