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

if _fails:
    print("\nTHẤT BẠI %d: %s" % (len(_fails), _fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
