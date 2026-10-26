"""CRM vận hành: quyền của tài khoản nhân viên (server/crm.py + middleware nhân viên của main).

    python tests/run.py crm_nhan_vien

Chủ chốt 2026-10-26: CRM là tab RIÊNG, nhân viên chỉ dùng khi admin cấp quyền `crm` cho từng tài
khoản. Có quyền rồi thì chỉ thấy khách/cơ hội/việc của PHÒNG mình; không tự cấp quyền cho mình được.
"""
from _paths import ROOT, SERVER, moi_duong_dan  # noqa: F401
import os
import sys
import tempfile
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-crm-nv-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
os.environ["JOYCE_SESSIONS_DB"] = str(Path(state) / "sessions.db")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import main
import h2o_staff
import crm
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


check("main đã gắn các route /crm", any(p.startswith("/crm") for p in moi_duong_dan(main.app)))

admin_app = FastAPI()
admin_app.get("/h2o-departments")(main.h2o_departments_list)
admin_app.post("/h2o-departments/seed")(main.h2o_departments_seed)
admin_app.post("/h2o-staff")(main.h2o_staff_add)
admin_app.post("/h2o-staff/update")(main.h2o_staff_update)
admin = TestClient(admin_app)
d = admin.post("/h2o-departments/seed").json()
BASE = Path(os.environ["BRAINS_DIR"])
ban = next(p for p in d["phong"] if p["brain"] == "Ban Hang - Sales Hinh Anh")
cskh = next(p for p in d["phong"] if p["brain"] == "CSKH - Sau Dich Vu va Khieu Nai")


def tao(ten, sdt, role, phong, quyen=""):
    r = admin.post("/h2o-staff", data={"ten": ten, "sdt": sdt, "pin": "1234", "role": role,
                                       "phong_ban": "\n".join(phong), "quyen": quyen})
    assert r.status_code == 200, r.text
    return r.json()["staff"]


lan = tao("Lan", "0901111222", "nhan_vien", [ban["id"]])
mai = tao("Mai", "0902222333", "nhan_vien", [cskh["id"]], quyen="crm")
check("tài khoản mới mặc định KHÔNG có quyền crm", lan["quyen"] == [])
check("admin cấp quyền khi tạo tài khoản", mai["quyen"] == ["crm"])
r = admin.post("/h2o-staff/update", data={"id": lan["id"], "quyen": "crm, bậy"})
check("cấp quyền: bỏ quyền không hợp lệ", r.json()["staff"]["quyen"] == ["crm"])
r = admin.post("/h2o-staff/update", data={"id": lan["id"], "quyen": "-"})
check("thu quyền bằng dấu -", r.json()["staff"]["quyen"] == [])

app = FastAPI()


@app.middleware("http")
async def _gac(request, call_next):
    st = h2o_staff.staff_by_token(request.cookies.get("h2o_staff", ""))
    if not st:
        return await call_next(request)
    request.state.staff = st
    path = request.url.path
    if main._staff_blocked(request, path):
        return JSONResponse({"error": "denied", "staff_denied": True}, status_code=403)
    tok = main._STAFF_SCOPE.set(main._staff_scope_roots(st))
    try:
        return await call_next(request)
    finally:
        main._STAFF_SCOPE.reset(tok)


app.include_router(crm.router)
app.post("/h2o-staff/update")(main.h2o_staff_update)


def client(sid):
    c = TestClient(app)
    c.cookies.set("h2o_staff", h2o_staff.new_session(sid))
    return c


admin_c = TestClient(app)
nv_lan = client(lan["id"])
nv_mai = client(mai["id"])

check("nhân viên chưa cấp quyền: /crm/me bị 403", nv_lan.get("/crm/me").status_code == 403)
check("nhân viên chưa cấp quyền: không đọc được danh sách khách", nv_lan.get("/crm/lien-he").status_code == 403)
check("nhân viên chưa cấp quyền: không tạo được khách", nv_lan.post("/crm/lien-he", data={"name": "x"}).status_code == 403)
r = nv_lan.post("/h2o-staff/update", data={"id": lan["id"], "quyen": "crm"})
check("nhân viên KHÔNG tự cấp quyền cho mình", r.status_code == 403 and h2o_staff.get(lan["id"])["quyen"] == [])

# admin cấp quyền thì dùng được; sổ nhân viên đọc lại mỗi request nên có hiệu lực ngay
admin.post("/h2o-staff/update", data={"id": lan["id"], "quyen": "crm"})
me = nv_lan.get("/crm/me")
check("sau khi được cấp: vào được, thấy đúng phòng của mình", me.status_code == 200 and not me.json()["admin"]
      and [p["brain"] for p in me.json()["phong"]] == [ban["brain"]] and me.json()["mac_dinh"] == ban["brain"])

r = nv_lan.post("/crm/lien-he", data={"name": "Khách Bán hàng", "phone": "0911000111"})
check("nhân viên tạo khách: tự gán phòng chính", r.status_code == 200 and r.json()["contact"]["depts"] == [ban["brain"]])
cid_ban = r.json()["contact"]["id"]
r = nv_mai.post("/crm/lien-he", data={"name": "Khách CSKH", "phone": "0922000222", "depts": ban["brain"]})
check("nhân viên CSKH cố gán sang phòng Bán hàng: bị bỏ, vẫn ở CSKH", r.json()["contact"]["depts"] == [cskh["brain"]])
cid_cs = r.json()["contact"]["id"]

check("Bán hàng không thấy khách chỉ thuộc CSKH", [c["name"] for c in nv_lan.get("/crm/lien-he").json()["items"]] == ["Khách Bán hàng"])
check("mở thẳng khách phòng khác bằng id: 404", nv_lan.get(f"/crm/lien-he/{cid_cs}").status_code == 404)
check("sửa khách phòng khác: 403", nv_lan.post("/crm/lien-he", data={"id": cid_cs, "name": "Lén"}).status_code == 403)
check("xoá khách phòng khác: 403", nv_lan.post("/crm/lien-he/xoa", data={"id": cid_cs}).status_code == 403)
check("tạo cơ hội trên khách phòng khác: 403", nv_lan.post("/crm/deal", data={"contact_id": cid_cs, "brain": ban["brain"], "title": "x"}).status_code == 403)
check("xin pipeline phòng khác: tự rơi về phòng mình, không lộ phòng khác",
      nv_lan.get("/crm/pipeline", params={"brain": cskh["brain"]}).json()["brain"] == ban["brain"])

# khách chung hai phòng: mỗi phòng chỉ thấy cơ hội của mình
admin_c_r = admin_c.post("/crm/lien-he/phong", data={"id": cid_ban, "brain": cskh["brain"], "bat": "1"})
check("admin thêm phòng CSKH cho khách Bán hàng", admin_c_r.status_code == 200)
nv_mai.post("/crm/deal", data={"contact_id": cid_ban, "brain": cskh["brain"], "title": "Xử lý khiếu nại"})
nv_lan.post("/crm/deal", data={"contact_id": cid_ban, "brain": ban["brain"], "title": "Báo giá gói cưới", "value": "5000000"})
dl = nv_mai.get(f"/crm/lien-he/{cid_ban}").json()
check("khách chung: CSKH chỉ thấy cơ hội của CSKH", [x["title"] for x in dl["deals"]] == ["Xử lý khiếu nại"])
dl = nv_lan.get(f"/crm/lien-he/{cid_ban}").json()
check("khách chung: Bán hàng chỉ thấy cơ hội của Bán hàng", [x["title"] for x in dl["deals"]] == ["Báo giá gói cưới"])
check("CSKH không đọc được pipeline Bán hàng", nv_mai.get("/crm/pipeline", params={"brain": ban["brain"]}).json()["brain"] == cskh["brain"])

# + / - giai đoạn trong phòng mình, và không chạm phòng khác
r = nv_lan.post("/crm/giai-doan", data={"brain": ban["brain"], "label": "Hẹn thử đồ"})
check("nhân viên thêm giai đoạn cho phòng mình", r.status_code == 200 and "Hẹn thử đồ" in [g["label"] for g in r.json()["stages"]])
r = nv_lan.post("/crm/giai-doan", data={"brain": cskh["brain"], "label": "Lén thêm"})
check("thêm giai đoạn ở phòng khác: rơi về phòng mình, phòng CSKH không đổi",
      "Lén thêm" not in [g["label"] for g in crm.giai_doan(cskh["brain"])])

# chế độ tự trích: chỉ quản lý hoặc chủ
r = nv_lan.post("/crm/cau-hinh/trich", data={"che_do": "auto"})
check("nhân viên thường không đổi được chế độ tự trích", r.status_code == 403 and crm.che_do_trich() == "duyet")
tp = tao("Hạnh", "0903333444", "truong_phong", [ban["id"]], quyen="crm")
r = client(tp["id"]).post("/crm/cau-hinh/trich", data={"che_do": "auto"})
check("trưởng phòng đổi được chế độ tự trích", r.status_code == 200 and crm.che_do_trich() == "auto")
admin_c.post("/crm/cau-hinh/trich", data={"che_do": "duyet"})

# nhập khách từ hộp thư: chỉ quản lý (hộp thư không chia theo phòng)
check("nhân viên thường không duyệt được hộp thư để nhập khách", nv_lan.get("/crm/hop-thu").status_code == 403)
check("trưởng phòng xem được danh sách hộp thư", client(tp["id"]).get("/crm/hop-thu").status_code == 200)

# wiki ghi đúng phòng
r = nv_lan.post("/crm/ghi-nho", data={"id": cid_ban, "brain": ban["brain"]})
check("ghi nhớ vào wiki phòng mình", r.status_code == 200 and (BASE / ban["brain"] / r.json()["path"]).is_file())
r = nv_lan.post("/crm/ghi-nho", data={"id": cid_ban, "brain": cskh["brain"]})
check("ghi wiki vào phòng khác: 403", r.status_code == 403)

print("\n" + ("TẤT CẢ OK" if not _fails else f"{len(_fails)} FAIL: " + "; ".join(_fails)))
sys.exit(1 if _fails else 0)
