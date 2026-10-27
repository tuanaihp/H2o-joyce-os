"""CRM vận hành (server/crm.py): khách theo phòng, cơ hội, việc, giai đoạn +/-, đề xuất hồ sơ.

    python tests/run.py crm      (KHÔNG mạng, KHÔNG gọi model thật)

Hợp đồng cần canh: một khách thuộc NHIỀU phòng nhưng cơ hội/việc thì của TỪNG phòng (phòng B không
thấy cơ hội phòng A); giai đoạn thêm/xoá được và Đã chốt / Mất luôn nằm cuối; Joyce trích hồ sơ
chỉ ra ĐỀ XUẤT chờ duyệt (trừ chế độ tự áp), không đè trường nhân viên đã sửa tay; wiki phòng không
chứa số điện thoại/email.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_STATE = tempfile.mkdtemp(prefix="joyce-crm2-")
os.environ["JOYCE_STATE_DIR"] = _STATE
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import conversations as cs  # noqa: E402
import crm  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


if _STATE not in str(cs.DB_PATH):
    print(f"FAIL kho không nằm trong thư mục tạm: {cs.DB_PATH}. DỪNG.")
    sys.exit(1)

BAN, CS = "Ban Hang", "CSKH"
BRAINS = Path(_STATE) / "brains"
for b in (BAN, CS):
    (BRAINS / b).mkdir(parents=True)
crm._deps.update(phong=lambda: [{"brain": BAN, "ten": "Bán hàng"}, {"brain": CS, "ten": "CSKH"}],
                 brain_root=lambda b: str(BRAINS / b), tasks=lambda: None)

# ---------------- chuẩn hoá SĐT, email
check("SĐT +84 và có dấu cách về 0xxxxxxxxx", crm.chuan_sdt("+84 901 234 567") == "0901234567" and crm.chuan_sdt("0901.234.567") == "0901234567")
check("SĐT quá ngắn bị bỏ", crm.chuan_sdt("12345") == "")
check("bắt SĐT và email trong câu chat", crm.bat_sdt("gọi em số 0901 234 567 nhé") == ["0901234567"]
      and crm.bat_email("mail: Lan.Anh@Gmail.com ạ") == ["lan.anh@gmail.com"])
check("số có 12 chữ số không bị cắt ra thành SĐT", crm.bat_sdt("mã đơn 123456789012") == [])

# ---------------- khách + phòng
c1 = crm.luu_lien_he({"name": "Chị Lan", "phone": "0901 234 567", "tags": ["vip", "vip", "b2b"], "depts": [BAN]}, None, "Chủ")
check("tạo khách: SĐT chuẩn, tag bỏ trùng, có phòng", c1["phone"] == "0901234567" and c1["tags"] == ["vip", "b2b"] and c1["depts"] == [BAN])
check("khách mới có dòng thời gian 'tạo'", any(True for _ in [0]) and crm._dung(lambda db: db.execute(
    "SELECT COUNT(*) n FROM crm_events WHERE contact_id=? AND kind='tao'", (c1["id"],)).fetchone()["n"]) == 1)
try:
    crm.luu_lien_he({"name": "", "phone": "", "email": ""}, None, "Chủ")
    check("khách trống bị từ chối", False)
except ValueError:
    check("khách trống bị từ chối", True)

# nhân viên phòng Bán hàng: chỉ gán được phòng của mình
nv = {BAN}
c2 = crm.luu_lien_he({"name": "Anh Nam", "depts": [CS, BAN]}, nv, "Lan NV", BAN)
check("nhân viên chỉ gán được phòng của mình (CSKH bị bỏ)", c2["depts"] == [BAN])
c3 = crm.luu_lien_he({"name": "Khách không phòng"}, nv, "Lan NV", BAN)
check("không nêu phòng thì rơi về phòng chính của nhân viên", c3["depts"] == [BAN])

# + / - phòng
check("admin thêm phòng CSKH cho Chị Lan", crm.gan_phong(c1["id"], CS, True, None, "Chủ") == [BAN, CS])
check("gỡ phòng CSKH", crm.gan_phong(c1["id"], CS, False, None, "Chủ") == [BAN])
try:
    crm.gan_phong(c1["id"], BAN, False, None, "Chủ")
    check("không gỡ được phòng cuối cùng", False)
except ValueError:
    check("không gỡ được phòng cuối cùng", True)
crm.gan_phong(c1["id"], CS, True, None, "Chủ")

# phạm vi đọc
ds_ban = crm.danh_sach_lien_he({BAN})
ds_cs = crm.danh_sach_lien_he({CS})
check("phòng Bán hàng thấy 3 khách", len(ds_ban) == 3)
check("phòng CSKH chỉ thấy Chị Lan (khách chung)", [c["name"] for c in ds_cs] == ["Chị Lan"])
check("admin (None) thấy tất cả", len(crm.danh_sach_lien_he(None)) == 3)
check("lọc theo phòng", len(crm.danh_sach_lien_he(None, brain=CS)) == 1)
check("tìm theo SĐT và theo tag", [c["name"] for c in crm.danh_sach_lien_he(None, q="0901234567")] == ["Chị Lan"]
      and [c["name"] for c in crm.danh_sach_lien_he(None, tag="vip")] == ["Chị Lan"])
try:
    crm.luu_lien_he({"id": c2["id"], "name": "Sửa lén"}, {CS}, "Nhân viên CSKH")
    check("phòng khác không sửa được khách của phòng Bán hàng", False)
except PermissionError:
    check("phòng khác không sửa được khách của phòng Bán hàng", True)

# sửa tay thì khoá trường
c1b = crm.luu_lien_he({"id": c1["id"], "name": "Chị Lan Anh", "phone": "0901234567", "depts": [BAN, CS]}, None, "Chủ")
check("sửa tay: ghi nhận trường bị khoá để Joyce không đè", "name" in c1b["locked"] and c1b["name"] == "Chị Lan Anh")

# ---------------- giai đoạn +/-
gd = crm.giai_doan(BAN)
check("5 giai đoạn mặc định, Đã chốt và Mất ở cuối", [g["key"] for g in gd] == ["moi", "tu_van", "cho_chot", "da_chot", "mat"])
moi = crm.them_giai_doan(BAN, "Gửi báo giá")
gd = crm.giai_doan(BAN)
check("giai đoạn thêm nằm TRƯỚC Đã chốt", [g["label"] for g in gd][-3:] == ["Gửi báo giá", "Đã chốt", "Mất"])
check("giai đoạn của phòng này không đổi phòng kia", len(crm.giai_doan(CS)) == 5)
try:
    crm.them_giai_doan(BAN, "gửi báo giá")
    check("không thêm trùng tên giai đoạn", False)
except ValueError:
    check("không thêm trùng tên giai đoạn", True)
try:
    crm.xoa_giai_doan(BAN, "da_chot")
    check("không xoá được Đã chốt", False)
except ValueError:
    check("không xoá được Đã chốt", True)

# ---------------- cơ hội
d1 = crm.luu_deal({"contact_id": c1["id"], "brain": BAN, "title": "Tiệc công ty", "value": "12.000.000", "stage": "tu_van"}, {BAN}, "Lan NV")
check("cơ hội: giá trị đọc đúng 12 triệu", d1["value"] == 12000000.0 and d1["stage"] == "tu_van")
crm.luu_deal({"contact_id": c1["id"], "brain": CS, "title": "Bảo hành", "value": "0"}, None, "Chủ")
check("cơ hội phòng A KHÔNG hiện ở pipeline phòng B",
      all(d["brain"] == CS for g in crm.pipeline(CS, {CS})["stages"] for d in g["deals"])
      and sum(g["count"] for g in crm.pipeline(CS, {CS})["stages"]) == 1)
try:
    crm.pipeline(BAN, {CS})
    check("phòng khác không mở pipeline phòng Bán hàng", False)
except PermissionError:
    check("phòng khác không mở pipeline phòng Bán hàng", True)
try:
    crm.luu_deal({"contact_id": c2["id"], "brain": CS, "title": "Lén"}, {CS}, "NV CSKH")
    check("nhân viên CSKH không tạo cơ hội trên khách chỉ thuộc phòng Bán hàng", False)
except PermissionError:
    check("nhân viên CSKH không tạo cơ hội trên khách chỉ thuộc phòng Bán hàng", True)
crm.chuyen_buoc(d1["id"], "da_chot", {BAN}, "Lan NV")
pl = crm.pipeline(BAN, {BAN})
check("chốt xong: tính vào Đã chốt, tỉ lệ thắng 100%", pl["da_chot"] == 12000000 and pl["ti_le_thang"] == 1.0)
try:
    crm.chuyen_buoc(d1["id"], "khong_co", {BAN}, "x")
    check("giai đoạn lạ bị từ chối", False)
except ValueError:
    check("giai đoạn lạ bị từ chối", True)

# xoá giai đoạn: cơ hội trong đó chuyển về giai đoạn mở đầu
d2 = crm.luu_deal({"contact_id": c2["id"], "brain": BAN, "title": "Báo giá nhỏ", "stage": moi["key"]}, {BAN}, "Lan NV")
kq = crm.xoa_giai_doan(BAN, moi["key"])
check("xoá giai đoạn: cơ hội trong đó chuyển sang giai đoạn mở đầu", kq["chuyen"] == 1 and crm.lay_deal(d2["id"])["stage"] == "moi")

# ---------------- việc chăm sóc
hom_nay = time.strftime("%Y-%m-%d")
qua = time.strftime("%Y-%m-%d", time.localtime(time.time() - 3 * 86400))
t1 = crm.them_viec({"contact_id": c1["id"], "brain": BAN, "title": "Gọi lại chị Lan", "due": hom_nay}, {BAN}, "Lan NV")
t2 = crm.them_viec({"contact_id": c1["id"], "brain": BAN, "title": "Gửi báo giá", "due": qua}, {BAN}, "Lan NV")
vs = crm.danh_sach_viec({BAN}, brain=BAN)
check("việc trễ hạn và việc hôm nay được đánh dấu", {v["title"]: (v["tre_han"], v["hom_nay"]) for v in vs} ==
      {"Gọi lại chị Lan": (False, True), "Gửi báo giá": (True, False)})
check("việc trễ hạn xếp trước việc hôm nay", vs[0]["title"] == "Gửi báo giá")
try:
    crm.them_viec({"contact_id": c1["id"], "brain": BAN, "title": "x", "due": "30/10/2026"}, None, "Chủ")
    check("hạn sai định dạng bị từ chối", False)
except ValueError:
    check("hạn sai định dạng bị từ chối", True)
check("phòng khác không thấy việc phòng Bán hàng", crm.danh_sach_viec({CS}, brain=BAN) == [] or all(v["brain"] != BAN for v in crm.danh_sach_viec({CS})))
ghi = []


class TasksGia:
    def ghi_viec_xong(self, brain, title, result, chat_id, key, who, metadata=None):
        ghi.append((brain, title, key))
        return "t1"


crm._deps["tasks"] = lambda: TasksGia()
crm.xong_viec(t1["id"], {BAN}, "Lan NV")
check("bấm xong: việc đáp xuống cột Xong của Kanban phòng", ghi and ghi[0][0] == BAN and ghi[0][1].startswith("[CRM] Gọi lại chị Lan"))
check("việc xong không còn trong danh sách mở", [v["title"] for v in crm.danh_sach_viec({BAN}, brain=BAN)] == ["Gửi báo giá"])

# ---------------- trích hồ sơ: đề xuất, duyệt, khoá, chế độ
def model_gia(prompt, text):
    return 'Đây là kết quả: {"name": "Lan Nguyen", "company": "Quán Lan Anh", "nhu_cau": "bánh sự kiện 50 người", "ngan_sach": "12 triệu", "bay": "x", "phone": "0988000111"}'


crm._deps["model"] = model_gia
f = crm.trich_tu_chu("khách: em ở 0901 234 567, mail lan@x.vn")
check("luật cố định thắng model (SĐT trong chat, không phải số model nói)", f["phone"] == "0901234567" and f["email"] == "lan@x.vn")
check("model bổ sung trường hồ sơ, bỏ khoá lạ", f["nhu_cau"].startswith("bánh sự kiện") and "bay" not in f)
check("không có model thì vẫn ra SĐT/email", "nhu_cau" not in crm.trich_tu_chu("0901234567", dung_model=False))

# khách nối hộp thư
cs.ghi_su_kien({"channel": "telegram", "account_id": "b1", "account_name": "Bot", "bot_id": "b1", "chat_type": "private",
                "external_chat_id": "77", "sender_type": "customer", "sender_id": "77", "sender_name": "Lan Nguyen",
                "text": "em cần bánh cho 50 người, ngân sách khoảng 12 triệu", "external_message_id": "m1"})
kh = cs.danh_sach_khach()[0]
check("khách hộp thư chưa vào CRM nằm trong danh sách có thể nhập", any(k["id"] == kh["id"] for k in crm.khach_hop_thu_chua_nhap()))
lh = crm.nhap_tu_hop_thu(kh["id"], BAN, "Chủ")
check("nhập từ hộp thư: có customer_id, phòng, nguồn", lh["customer_id"] == kh["id"] and lh["depts"] == [BAN])
check("nhập lần hai là cùng một khách, không nhân đôi", crm.nhap_tu_hop_thu(kh["id"], CS, "Chủ")["id"] == lh["id"]
      and crm.lay_lien_he(lh["id"])["depts"] == [BAN, CS])
kq = crm.trich_lien_he(lh["id"])
check("trích bằng tay: ra ĐỀ XUẤT chờ duyệt, chưa ghi vào hồ sơ", kq["ok"] and not kq["da_ap"] and crm.lay_lien_he(lh["id"])["profile"] == {})
dx = crm.danh_sach_de_xuat({BAN})
check("đề xuất hiện ở hàng chờ của phòng", len(dx) == 1 and dx[0]["fields"]["nhu_cau"].startswith("bánh sự kiện"))
check("phòng không liên quan không thấy đề xuất", crm.danh_sach_de_xuat({"Phong Khac"}) == [])
check("đọc lại khi không có tin mới thì không tạo đề xuất mới", crm.trich_lien_he(lh["id"]).get("co_gi_moi") is False)
crm.duyet_de_xuat(dx[0]["id"], {BAN}, "Lan NV", chon=["nhu_cau", "ngan_sach"])
l2 = crm.lay_lien_he(lh["id"])
check("duyệt chọn lọc: chỉ nhu cầu và ngân sách vào hồ sơ", l2["profile"].get("nhu_cau") and l2["profile"].get("ngan_sach") and l2["company"] == "")
check("đề xuất đã duyệt biến khỏi hàng chờ", crm.danh_sach_de_xuat({BAN}) == [])

# tay sửa tên thì Joyce không đè
crm.luu_lien_he({"id": lh["id"], "name": "Chị Lan (VIP)"}, None, "Chủ")
cs.ghi_su_kien({"channel": "telegram", "account_id": "b1", "bot_id": "b1", "chat_type": "private", "external_chat_id": "77",
                "sender_type": "customer", "sender_id": "77", "sender_name": "Lan Nguyen",
                "text": "ok em, gọi 0977 111 222 nhé", "external_message_id": "m2"})
kq = crm.trich_lien_he(lh["id"])
check("tin mới có SĐT khác: ra đề xuất mới", kq["co_gi_moi"] and kq["fields"].get("phone") == "0977111222")
check("tên đã sửa tay thì Joyce không đề xuất đổi", "name" not in kq["fields"])
crm.duyet_de_xuat(crm.danh_sach_de_xuat({BAN})[0]["id"], {BAN}, "Lan NV", tu_choi=True)
check("bỏ đề xuất thì SĐT không đổi", crm.lay_lien_he(lh["id"])["phone"] == "")

# chế độ auto + ngưỡng + móc từ hộp thư
check("mặc định là chế độ duyệt, ngưỡng 8", crm.che_do_trich() == "duyet" and crm.nguong_trich() == 8)
crm._dung(lambda db: (crm._put_set(db, "auto_mode", "off"), db.commit()))
n0 = len(crm.danh_sach_de_xuat(None))
for i in range(10):
    cs.ghi_su_kien({"channel": "telegram", "account_id": "b1", "bot_id": "b1", "chat_type": "private", "external_chat_id": "77",
                    "sender_type": "customer", "sender_id": "77", "sender_name": "Lan Nguyen",
                    "text": f"tin {i} số 0966 555 444", "external_message_id": f"o{i}"})
time.sleep(0.4)
check("chế độ TẮT: nhiều tin cũng không tự trích", len(crm.danh_sach_de_xuat(None)) == n0)
crm._dung(lambda db: (crm._put_set(db, "auto_mode", "auto"), crm._put_set(db, "auto_n", "3"), db.commit()))
cs.ghi_su_kien({"channel": "telegram", "account_id": "b1", "bot_id": "b1", "chat_type": "private", "external_chat_id": "77",
                "sender_type": "customer", "sender_id": "77", "sender_name": "Lan Nguyen",
                "text": "thêm một tin nữa", "external_message_id": "o99"})
for _ in range(40):
    if crm.lay_lien_he(lh["id"])["phone"]:
        break
    time.sleep(0.1)
check("chế độ AUTO đủ ngưỡng: Joyce tự áp vào hồ sơ (SĐT mới)", crm.lay_lien_he(lh["id"])["phone"] == "0966555444")
check("tự áp ghi dòng thời gian 'Joyce (tự động)'", crm._dung(lambda db: db.execute(
    "SELECT COUNT(*) n FROM crm_events WHERE contact_id=? AND by='Joyce (tự động)'", (lh["id"],)).fetchone()["n"]) >= 1)
crm._dung(lambda db: (crm._put_set(db, "auto_mode", "duyet"), db.commit()))

# ---------------- wiki, phân khúc, tổng quan, xoá/khôi phục
kq = crm.ghi_nho_wiki(lh["id"], BAN, {BAN}, "Lan NV")
md = (BRAINS / BAN / kq["path"]).read_text(encoding="utf-8")
check("wiki phòng có nhu cầu, KHÔNG có số điện thoại hay email", "bánh sự kiện" in md and "0966555444" not in md and "@" not in md)
try:
    crm.ghi_nho_wiki(lh["id"], CS, {BAN}, "x")
    check("không ghi wiki vào phòng ngoài phạm vi", False)
except PermissionError:
    check("không ghi wiki vào phòng ngoài phạm vi", True)
seg = {s["key"]: s for s in crm.phan_khuc(BAN, {BAN})}
check("phân khúc: 'Cần chăm hôm nay' gồm khách có việc trễ, 'Chưa có cơ hội' có khách chưa deal",
      c1["id"] in [c["id"] for c in seg["can_cham_hom_nay"]["contacts"]]
      and lh["id"] in [c["id"] for c in seg["chua_co_co_hoi"]["contacts"]])
tq = crm.tong_quan(BAN, {BAN})
check("tổng quan: việc trễ 1, đã chốt 12 triệu", tq["viec_tre"] == 1 and tq["da_chot"] == 12000000)
check("tổng quan: 1 khách đã mua, số cơ hội đang theo là số nguyên, tỉ lệ thắng 100%",
      tq["da_mua"] == 1 and isinstance(tq["so_co_hoi"], int) and tq["ti_le_thang"] == 1.0)
tq_all = crm.tong_quan("", None)
check("tổng quan Tất cả phòng cộng dồn các phòng (trước đây luôn 0): đã chốt >= phòng Bán hàng, thấy cả khách đã mua",
      tq_all["da_chot"] >= 12000000 and tq_all["da_mua"] >= 1)
check("tổng quan Tất cả phòng chỉ cộng phòng người xem được thấy", crm.tong_quan("", {CS})["da_chot"] == 0)
check("cột giá trị đã chốt của danh bạ: khách chốt 12 triệu, khách chưa chốt không có mục",
      crm.tong_da_chot([c1["id"], lh["id"]], {BAN}) == {c1["id"]: 12000000}
      and crm.tong_da_chot([c1["id"]], {CS}) == {} and crm.tong_da_chot([], None) == {})
crm.xoa_lien_he(c3["id"], {BAN}, "Lan NV")
check("xoá khách là xoá mềm: biến khỏi danh sách nhưng khôi phục được", c3["id"] not in [c["id"] for c in crm.danh_sach_lien_he({BAN})]
      and c3["id"] in [c["id"] for c in crm.danh_sach_lien_he({BAN}, da_xoa=True)])
crm.xoa_lien_he(c3["id"], {BAN}, "Lan NV", khoi_phuc=True)
check("khôi phục khách", c3["id"] in [c["id"] for c in crm.danh_sach_lien_he({BAN})])

# ---------------- HTTP
app = FastAPI()
app.include_router(crm.router)
nguoi = {"staff": None}


@app.middleware("http")
async def _gia(request, call_next):
    st = nguoi["staff"]
    if st:
        request.state.staff = st
    return await call_next(request)


crm._deps["scope"] = lambda: (str(BRAINS / BAN),) if nguoi["staff"] else ()
http = TestClient(app)
r = http.get("/crm/me").json()
check("HTTP admin: thấy 2 phòng, chế độ trích", r["admin"] and len(r["phong"]) == 2 and r["che_do"] == "duyet")
r = http.post("/crm/lien-he", data={"name": "Khách qua HTTP", "phone": "0911222333", "depts": BAN})
check("HTTP: tạo khách", r.status_code == 200 and r.json()["contact"]["phone"] == "0911222333")
r = http.post("/crm/giai-doan", data={"brain": BAN, "label": "Hẹn gặp"})
check("HTTP: nút + giai đoạn", r.status_code == 200 and "Hẹn gặp" in [g["label"] for g in r.json()["stages"]])
key = [g["key"] for g in r.json()["stages"] if g["label"] == "Hẹn gặp"][0]
r = http.post("/crm/giai-doan/xoa", data={"brain": BAN, "key": key})
check("HTTP: nút - giai đoạn", r.status_code == 200 and "Hẹn gặp" not in [g["label"] for g in r.json()["stages"]])
r = http.post("/crm/giai-doan/xoa", data={"brain": BAN, "key": "da_chot"})
check("HTTP: xoá Đã chốt trả 400 kèm lý do", r.status_code == 400 and "Đã chốt" in r.json()["detail"])
r = http.post("/crm/nhap-nhanh", data={"text": "Anh Tuấn 0933 111 222 tuan@x.vn", "model": 0})
check("HTTP: nhập nhanh trả bản nháp, chưa lưu gì", r.json()["fields"]["phone"] == "0933111222"
      and not [c for c in crm.danh_sach_lien_he(None, q="0933111222")])
r = http.post("/crm/cau-hinh/trich", data={"che_do": "auto", "nguong": "5"})
check("HTTP admin đổi chế độ tự trích", r.json()["che_do"] == "auto" and r.json()["nguong"] == 5)
http.post("/crm/cau-hinh/trich", data={"che_do": "duyet", "nguong": "8"})
r = http.post("/crm/cau-hinh/trich", data={"che_do": "bậy"})
check("chế độ lạ bị từ chối", r.status_code == 400)
d = http.get(f"/crm/lien-he/{c1['id']}").json()
check("HTTP chi tiết: có cơ hội, việc, dòng thời gian, nhãn giai đoạn", d["deals"] and d["todos"] and d["events"] and BAN in d["stage_labels"])

print("\n" + ("TẤT CẢ OK" if not _fails else f"{len(_fails)} FAIL: " + "; ".join(_fails)))
sys.exit(1 if _fails else 0)
