"""Việc mẫu: quyền của nhân viên và phạm vi phòng (server/viec_mau.py + middleware nhân viên của main).

    python tests/run.py viec_mau_nhan_vien

Chủ chốt 2026-10-26: nhân viên MỌI chức vụ tự thêm / xoá việc mẫu trong phòng mình (không cần quản lý
duyệt, vì xoá được ngay). Bẫy cần canh: `/kanban/*` ghi chỉ cho Trưởng phòng trở lên, nên nút "Đã xong"
của nhân viên phải đi qua `/viec-mau/xong` chứ không gọi thẳng `/kanban/task`. Chọn "Toàn khối" (brain
mặc định) thì nhân viên chỉ nhận việc của phòng chính (brain đầu tiên được gán).
"""
from _paths import ROOT, SERVER  # noqa: F401
import os
import sys
import tempfile
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-vm-nv-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
os.environ["JOYCE_SESSIONS_DB"] = str(Path(state) / "sessions.db")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import main
import h2o_staff
import viec_mau as vm
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


class TasksGia:
    def __init__(self):
        self.done = []

    def ghi_viec_xong(self, brain, title, result, chat_id, key, who, metadata=None):
        self.done.append((brain, title, who))
        return "t_gia"

    def enqueue(self, *a, **k):
        return "t_cc"

    async def _claim_and_spawn(self, tid):
        return True


gia = TasksGia()
vm._deps.update(brain_root=main._brain_root, tasks=lambda: gia)

admin_app = FastAPI()
admin_app.get("/h2o-departments")(main.h2o_departments_list)
admin_app.post("/h2o-departments/seed")(main.h2o_departments_seed)
admin_app.post("/h2o-staff")(main.h2o_staff_add)
admin = TestClient(admin_app)
d = admin.post("/h2o-departments/seed").json()
BASE = Path(os.environ["BRAINS_DIR"])
ban = next(p for p in d["phong"] if p["brain"] == "Ban Hang - Sales Hinh Anh")
cskh = next(p for p in d["phong"] if p["brain"] == "CSKH - Sau Dich Vu va Khieu Nai")


def tao(ten, sdt, role, phong):
    r = admin.post("/h2o-staff", data={"ten": ten, "sdt": sdt, "pin": "1234", "role": role,
                                       "phong_ban": "\n".join(phong)})
    assert r.status_code == 200, r.text
    return r.json()["staff"]


lan = tao("Lan", "0901111222", "nhan_vien", [ban["id"], cskh["id"]])
hv = tao("Hoa", "0902222333", "hoc_viec", [ban["id"]])

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
    if await main._staff_slug_bad(request, path):
        return JSONResponse({"error": "slug"}, status_code=400)
    tok = main._STAFF_SCOPE.set(main._staff_scope_roots(st))
    try:
        return await call_next(request)
    finally:
        main._STAFF_SCOPE.reset(tok)


vm.register(app, main._brain_root, lambda: gia)
app.post("/kanban/task")(lambda: {"ok": True})
nv = TestClient(app)
nv.cookies.set("h2o_staff", h2o_staff.new_session(lan["id"]))
hoc = TestClient(app)
hoc.cookies.set("h2o_staff", h2o_staff.new_session(hv["id"]))

# ---- đọc: "Toàn khối" về phòng chính ----
r = nv.get("/viec-mau", params={"brain": "brain"})
check("nhân viên chọn Toàn khối: nhận việc của phòng CHÍNH (brain đầu tiên được gán)",
      r.status_code == 200 and r.json()["brain"] == ban["brain"] and len(r.json()["items"]) >= 5)
r = nv.get("/viec-mau", params={"brain": str(BASE / cskh["brain"])})
check("brain phòng thứ hai của mình: đúng bộ việc của phòng đó", r.json()["brain"] == cskh["brain"] and
      any(i["slug"] == "cham-soc-sau-chup" for i in r.json()["items"]))
r = nv.get("/viec-mau", params={"brain": str(BASE / "Ke Toan - Thu")})
check("brain phòng khác bị ép về phòng chính, không lộ việc phòng khác", r.json()["brain"] == ban["brain"])

# ---- ghi: nhân viên thường được thêm / xoá ----
r = nv.post("/viec-mau", data={"brain": "brain", "title": "Gửi hợp đồng", "group": "Sau chốt", "prompt": "Soạn mail cho {khach}",
                               "inputs": '[{"key":"khach","label":"Tên khách","required":true}]'})
check("nhân viên thường THÊM được việc (không bị 403 như /kanban)", r.status_code == 200 and r.json()["ok"])
check("việc mới nằm trong brain phòng chính và ghi tên người thêm",
      (BASE / ban["brain"] / "viec-mau" / "gui-hop-dong.md").is_file() and r.json()["item"]["by"] == "Lan")
r = nv.post("/viec-mau", data={"brain": str(BASE / "Ke Toan - Thu"), "title": "Việc lạ phòng khác", "prompt": "x"})
check("ghi nhầm vào phòng khác thì rơi về phòng chính, KHÔNG ghi vào phòng khác",
      r.status_code == 200 and not (BASE / "Ke Toan - Thu" / "viec-mau").exists()
      and (BASE / ban["brain"] / "viec-mau" / "viec-la-phong-khac.md").is_file())
r = nv.post("/viec-mau/delete", data={"brain": "brain", "slug": "gui-hop-dong"})
check("nhân viên thường XOÁ được việc", r.status_code == 200 and not (BASE / ban["brain"] / "viec-mau" / "gui-hop-dong.md").exists())
r = nv.post("/viec-mau", data={"brain": "brain", "slug": "../../../x", "title": "Xấu", "prompt": "x"})
check("slug thoát thư mục bị chặn", r.status_code == 400 and not (BASE / "x.md").exists())

# ---- Đã xong ----
r = nv.post("/viec-mau/xong", data={"brain": "brain", "slug": "tu-van-bao-gia-online", "title": "Tư vấn báo giá online",
                                    "values": '{"khach":"Mai"}', "result": "ok", "key": "nv-key-000001"})
check("nhân viên bấm Đã xong được", r.status_code == 200 and r.json()["ok"] and gia.done and gia.done[0][2] == "Lan")
check("hồ sơ nằm trong brain phòng chính", any((BASE / ban["brain"] / "sources" / "viec-lam").glob("*tu-van-bao-gia-online*.md")))
check("trong khi /kanban/task của nhân viên thường vẫn bị chặn (đúng, vì thế mới cần /viec-mau/xong)",
      nv.post("/kanban/task").status_code == 403)

# ---- Học việc: vẫn dùng được việc mẫu ----
r = hoc.get("/viec-mau", params={"brain": "brain"})
check("Học việc xem được việc mẫu của phòng mình", r.status_code == 200 and r.json()["brain"] == ban["brain"])
r = hoc.post("/viec-mau/xong", data={"brain": "brain", "slug": "tu-van-bao-gia-online", "values": "{}", "result": "x", "key": "hv-key-000001"})
check("Học việc bấm Đã xong được", r.status_code == 200 and r.json()["ok"])

print("\n" + ("TẤT CẢ OK" if not _fails else f"{len(_fails)} FAIL: " + "; ".join(_fails)))
sys.exit(1 if _fails else 0)
