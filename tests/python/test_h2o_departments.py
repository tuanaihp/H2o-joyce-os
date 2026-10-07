"""Phòng ban H2O: mỗi phòng một brain + agent trưởng phòng, brain chung H2O Studio, và nhân
viên bị khoá vào đúng brain phòng của mình.

    python tests/run.py h2o_departments

Kiểm:
  - Dựng sơ đồ mẫu: 38 phòng, mỗi phòng một brain + file agent trưởng phòng, brain chung có sơ
    đồ phòng ban. Chạy lại vô hại và KHÔNG ghi đè agent đã sửa tay.
  - Phạm vi nhân viên (_STAFF_SCOPE): trình duyệt gửi Brain Default hay brain phòng khác thì
    _brain_root vẫn trả brain phòng của họ; thư mục con trong brain phòng thì giữ nguyên.
  - Nhân viên chưa gán phòng làm việc trong không gian riêng, không phải Brain Default.
  - /brains với phạm vi chỉ trả brain của nhân viên, đúng thứ tự gán, không có brain mặc định.
  - System prompt của brain phòng mang khối PHÒNG BAN H2O + bộ nhớ chung H2O Studio.
  - Mặt quản trị phòng ban chặn nhân viên; gỡ phòng thì gỡ khỏi hồ sơ nhân viên.
"""
from _paths import ROOT, SERVER  # noqa: F401
import os
import sys
import tempfile
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-phong-ban-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
os.environ["JOYCE_SESSIONS_DB"] = str(Path(state) / "sessions.db")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import main
import h2o_departments as dep
import h2o_staff
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.get("/h2o-departments")(main.h2o_departments_list)
app.post("/h2o-departments/seed")(main.h2o_departments_seed)
app.post("/h2o-departments/phong")(main.h2o_departments_add)
app.post("/h2o-departments/phong/delete")(main.h2o_departments_delete)
app.post("/h2o-staff")(main.h2o_staff_add)
app.get("/staff/me")(main.staff_me)
client = TestClient(app)
BASE = Path(os.environ["BRAINS_DIR"])

# ---- dựng sơ đồ mẫu ----
r = client.post("/h2o-departments/seed")
assert r.status_code == 200 and r.json()["ok"], r.text
d = r.json()
assert len(d["phong"]) == 38, len(d["phong"])
assert len(d["khoi"]) == 10, len(d["khoi"])
assert len({p["brain"].lower() for p in d["phong"]}) == 38, "tên brain phòng phải duy nhất"
for p in d["phong"]:
    assert p["brain_ok"], p["brain"]
    assert p["brain"].isascii(), "tên thư mục brain phải ASCII: " + p["brain"]
    f = BASE / p["brain"] / "agents" / f"{p['agent_slug']}.md"
    assert f.is_file(), f
    txt = f.read_text(encoding="utf-8")
    assert "type: agent" in txt and p["agent"] in txt
    assert "—" not in txt, "agent không được có em dash"
assert d["shared_ok"]
assert (BASE / dep.SHARED_BRAIN / dep.ORG_CHART_REL).is_file()

mk = next(p for p in d["phong"] if p["id"] == "san-xuat--makeup")
mkt = next(p for p in d["phong"] if p["id"] == "marketing--marketing-makeup")
assert mk["brain"] == "San Xuat - Makeup" and mk["agent"] == "Agent Trưởng Phòng Makeup"

# chạy lại: không tạo trùng, không ghi đè agent đã sửa tay
agent_mk = BASE / mk["brain"] / "agents" / f"{mk['agent_slug']}.md"
agent_mk.write_text("sửa tay", encoding="utf-8")
r = client.post("/h2o-departments/seed")
assert r.json()["brain_moi"] == [] and r.json()["agent_moi"] == []
assert len(r.json()["phong"]) == 38
assert agent_mk.read_text(encoding="utf-8") == "sửa tay"

# ---- nhân viên + phòng ban ----
r = client.post("/h2o-staff", data={"ten": "Lan", "sdt": "0901111222", "pin": "1234",
                                    "role": "nhan_vien",
                                    "phong_ban": f"{mk['id']}\n{mkt['id']}\nkhong-ton-tai"})
assert r.status_code == 200, r.text
lan = r.json()["staff"]
assert lan["phong_ban"] == [mk["id"], mkt["id"]], "id lạ phải bị bỏ, thứ tự giữ nguyên"
ok, minh = h2o_staff.create("Minh", "0903333444", "5678")   # chưa gán phòng
assert ok

lan_rec = h2o_staff.get(lan["id"])
scope = main._staff_scope_roots(lan_rec)
assert [Path(x).name for x in scope] == [mk["brain"], mkt["brain"]]

default = str(main._default_brain_dir())
tok = main._STAFF_SCOPE.set(scope)
try:
    # gửi Brain Default / "brain" / brain phòng khác -> về brain phòng đầu tiên
    assert Path(main._brain_root(default)).name == mk["brain"]
    assert Path(main._brain_root("brain")).name == mk["brain"]
    khac = str(BASE / "Ke Toan - Thu")
    assert Path(main._brain_root(khac)).name == mk["brain"]
    # brain phòng thứ hai được phép -> giữ nguyên
    assert Path(main._brain_root(str(BASE / mkt["brain"]))).name == mkt["brain"]
    # thư mục con của brain phòng -> giữ nguyên
    sub = BASE / mk["brain"] / "wiki"
    assert main._brain_root(str(sub)) == str(sub)
    # bộ nhớ cũng đi theo phạm vi
    assert mk["brain"] in str(main._brain_memory_dir(default))
    # /brains chỉ trả brain của nhân viên, đúng thứ tự, không có brain mặc định
    ds = main._list_brains_sync(scope)
    assert ds.get("scoped") is True
    assert [b["name"] for b in ds["brains"]] == [mk["brain"], mkt["brain"]], ds
    assert not any(b["is_default"] for b in ds["brains"])
    assert ds["brains"][0]["label"] == "Phòng Makeup" and ds["brains"][0]["group"] == "Sản Xuất"
finally:
    main._STAFF_SCOPE.reset(tok)

# ngoài phạm vi (admin) -> không đổi gì
assert main._brain_root(default) == default
adm = main._list_brains_sync()
assert len(adm["brains"]) >= 40 and "scoped" not in adm

# nhân viên chưa gán phòng -> không gian riêng, không phải Brain Default
scope_m = main._staff_scope_roots(h2o_staff.get(minh["id"]))
assert len(scope_m) == 1 and "staff_workspaces" in scope_m[0]
tok = main._STAFF_SCOPE.set(scope_m)
try:
    assert main._brain_root(default) == scope_m[0]
finally:
    main._STAFF_SCOPE.reset(tok)

# ---- system prompt của brain phòng ----
shared_mem = BASE / dep.SHARED_BRAIN / "memory" / "MEMORY.md"
shared_mem.write_text("- [Bảng giá 2026](facts/bang-gia.md) - gói chụp từ 15 triệu\n", encoding="utf-8")
sp = main.build_system_prompt(str(BASE / mk["brain"]))
assert "# === PHÒNG BAN H2O ===" in sp
assert "Phòng Makeup" in sp and "Sản Xuất" in sp
assert "Bảng giá 2026" in sp, "bộ nhớ chung H2O Studio phải được nạp"
assert "# === PHÒNG BAN H2O ===" not in main.build_system_prompt(default), \
    "Brain Default của chủ không mang khối phòng ban"

# ---- nhân viên bị chặn khỏi mặt quản trị phòng ban ----
cookie = h2o_staff.new_session(lan["id"])
client.cookies.set("h2o_staff", cookie)
assert client.get("/h2o-departments").status_code == 403
assert client.post("/h2o-departments/seed").status_code == 403
me = client.get("/staff/me").json()["staff"]
assert [x["id"] for x in me["phong_ban_info"]] == [mk["id"], mkt["id"]]
client.cookies.clear()

# ---- thêm / gỡ phòng ----
r = client.post("/h2o-departments/phong", data={"khoi": "Sản Xuất", "ten": "Phòng Quay Phim",
                                                "agent": "Agent Trưởng Phòng Quay Phim"})
assert r.status_code == 200, r.text
qp = r.json()["phong"]
assert qp["brain"] == "San Xuat - Quay Phim" and (BASE / qp["brain"]).is_dir()
assert client.post("/h2o-departments/phong", data={"khoi": "Sản Xuất", "ten": "Phòng Quay Phim"}).status_code == 400

r = client.post("/h2o-departments/phong/delete", data={"id": mkt["id"]})
assert r.status_code == 200
assert h2o_staff.get(lan["id"])["phong_ban"] == [mk["id"]], "gỡ phòng phải gỡ khỏi hồ sơ nhân viên"
assert (BASE / mkt["brain"]).is_dir(), "gỡ phòng KHÔNG xoá brain"
assert mkt["brain"] not in (BASE / dep.SHARED_BRAIN / dep.ORG_CHART_REL).read_text(encoding="utf-8")

# =========================================================================================
# Giai đoạn 2 + 3: quyền theo chức vụ trong brain phòng ban, và đề xuất lên brain chung.
# App thử dựng middleware Y HỆT nhánh nhân viên của main._auth_guard (chặn quyền -> kiểm slug
# -> khoá phạm vi brain), để thử đúng thứ tự thật mà không cần bật cổng đăng nhập.
# =========================================================================================
from fastapi.responses import JSONResponse

app2 = FastAPI()


@app2.middleware("http")
async def _gac_nhan_vien(request, call_next):
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


app2.get("/files/list")(main.files_list)
app2.post("/files/write")(main.files_write)
app2.post("/agents")(main.save_agent)
app2.post("/agents/delete")(main.delete_agent)
app2.post("/h2o-shared/propose")(main.h2o_shared_propose)
app2.get("/h2o-shared/proposals")(main.h2o_shared_list)
app2.post("/h2o-shared/decide")(main.h2o_shared_decide)
app2.get("/inbox")(main.inbox_list)
app2.post("/inbox/read")(main.inbox_read)
c2 = TestClient(app2)
MKB = BASE / mk["brain"]


def la(role):
    h2o_staff.update(lan["id"], role=role)
    c2.cookies.set("h2o_staff", h2o_staff.new_session(lan["id"]))


# ---- Nhân viên: xem + ghi file trong brain phòng, KHÔNG sửa trợ lý ----
la("nhan_vien")
r = c2.get("/files/list", params={"brain": default})
assert r.status_code == 200, r.text
names = {i["name"] for i in r.json().get("items", [])}
assert "agents" in names and "memory" in names, "Tệp tin phải mở đúng brain phòng, không phải Brain Default"
r = c2.post("/files/write", data={"brain": default, "path": "sources/ghi-chu-ca.md", "content": "Ca sáng 3 cô dâu"})
assert r.status_code == 200, r.text
assert (MKB / "sources" / "ghi-chu-ca.md").is_file(), "ghi vào brain phòng"
assert not (Path(default) / "sources" / "ghi-chu-ca.md").exists(), "KHÔNG ghi vào Brain Default"
r = c2.post("/files/write", data={"brain": default, "path": "../Ke Toan - Thu/x.md", "content": "x"})
assert r.status_code in (400, 403) and not (BASE / "Ke Toan - Thu" / "x.md").exists(), "trần duyệt = gốc brain phòng"
assert c2.post("/agents", data={"name": "Thử", "brain": default}).status_code == 403
assert c2.post("/h2o-shared/propose", data={"path": "sources/ghi-chu-ca.md"}).status_code == 403
for p in ("/browse", "/path/exists", "/coding/repos", "/ingest-upload", "/kanban/task/grant",
          "/h2o-shared/decide", "/learn/config", "/vault/init", "/brain/migrate"):
    assert c2.post(p).status_code == 403, p

# ---- Học việc: chỉ xem ----
la("hoc_viec")
assert c2.get("/files/list", params={"brain": default}).status_code == 200
assert c2.post("/files/write", data={"brain": default, "path": "a.md", "content": "x"}).status_code == 403

# ---- Trưởng phòng: sửa trợ lý của phòng; slug lách đường dẫn bị chặn ----
la("truong_phong")
r = c2.post("/agents", data={"name": "Trợ lý lịch makeup", "brain": default})
assert r.status_code == 200, r.text
assert (MKB / "agents" / f"{r.json()['slug']}.md").is_file(), "trợ lý mới nằm trong brain phòng"
victim = Path(default) / "agents" / "khong-duoc-xoa.md"
victim.parent.mkdir(parents=True, exist_ok=True)
victim.write_text("x", encoding="utf-8")
r = c2.post("/agents/delete", data={"slug": "../../Brain Default/agents/khong-duoc-xoa", "brain": default})
assert r.status_code == 400 and victim.exists(), "slug ../ không được xoá file ngoài brain phòng"
assert c2.post("/agents", data={"name": "x", "slug": "..\\..\\x", "brain": default}).status_code == 400

# ---- Đề xuất lên H2O Studio: trưởng phòng gửi -> admin duyệt -> có trong brain chung ----
r = c2.post("/h2o-shared/propose", data={"path": "sources/ghi-chu-ca.md", "brain": default, "note": "dùng chung"})
assert r.status_code == 200, r.text
pid = r.json()["proposal"]["id"]
assert r.json()["proposal"]["status"] == "pending" and r.json()["proposal"]["brain"] == mk["brain"]
assert c2.get("/h2o-shared/proposals").status_code == 403, "nhân viên không xem hàng đợi duyệt"
# Thư báo admin nằm ở brain chung -> nhân viên KHÔNG thấy; thư admin ở Brain Default cũng không
main.inbox.add("Doanh thu tháng của chủ", kind="report", brain=default)
items = c2.get("/inbox").json()["items"]
assert not any("Doanh thu" in (x.get("body") or "") for x in items), "nhân viên không đọc thư của admin"
assert not any("đề xuất" in (x.get("body") or "") for x in items)

c2.cookies.clear()   # admin
assert any(x["id"] == pid for x in c2.get("/h2o-shared/proposals").json()["items"])
r = c2.post("/h2o-shared/decide", data={"id": pid, "approve": "1"})
assert r.status_code == 200, r.text
dest = BASE / dep.SHARED_BRAIN / r.json()["proposal"]["dest"]
assert dest.is_file() and dest.read_text(encoding="utf-8") == "Ca sáng 3 cô dâu"
assert f"{dep.SHARED_INBOX_REL}/{mk['brain']}/" in r.json()["proposal"]["dest"]
assert c2.post("/h2o-shared/decide", data={"id": pid, "approve": "1"}).status_code == 400, "không duyệt hai lần"

# người đề xuất nhận thư báo đã duyệt (kênh staff:<id>), và đánh dấu đọc được thư của mình
la("truong_phong")
mine = [x for x in c2.get("/inbox").json()["items"] if "Đã duyệt" in (x.get("title") or "")]
assert mine, "người đề xuất phải nhận thư báo"
assert c2.post("/inbox/read", json={"id": mine[0]["id"]}).json()["changed"] == 1
c2.cookies.clear()

# admin đề xuất thì chép thẳng, khỏi tự duyệt
(Path(default) / "bang-gia.md").write_text("Gói A 15tr", encoding="utf-8")
r = c2.post("/h2o-shared/propose", data={"path": "bang-gia.md", "brain": default})
assert r.status_code == 200 and r.json().get("auto_approved"), r.text
assert (BASE / dep.SHARED_BRAIN / r.json()["proposal"]["dest"]).is_file()

# =========================================================================================
# Khoá mục hệ thống với nhân viên (admin bật/tắt, chọn mục)
# =========================================================================================
app2.post("/files/delete")(main.files_delete)
app2.post("/files/rename")(main.files_rename)
app2.post("/files/upload")(main.files_upload)
app2.post("/h2o-departments/khoa")(main.h2o_departments_lock)
c2 = TestClient(app2)   # dựng lại client để nhận route vừa thêm
assert dep.lock_config()["bat"] is True, "mặc định khoá BẬT"

la("truong_phong")      # kể cả trưởng phòng cũng bị khoá mục hệ thống
items = {i["name"]: i for i in c2.get("/files/list", params={"brain": default}).json()["items"]}
assert ".claude" not in items and ".joyce" not in items, "nhân viên không thấy mục kỹ thuật bắt đầu bằng dấu chấm"
assert items["memory"]["locked"] and items["agents"]["locked"] and not items["sources"]["locked"]
inside = c2.get("/files/list", params={"brain": default, "path": "memory"}).json()
assert inside["locked"] is True, "đứng trong mục khoá -> cờ locked cho toolbar"


def ghi(path, content="x"):
    return c2.post("/files/write", data={"brain": default, "path": path, "content": content})


assert ghi("memory/hack.md").status_code == 403 and ghi("memory/hack.md").json().get("locked")
assert ghi("sources/../memory/hack2.md").status_code == 403, "../ không lách được khoá"
assert ghi("AGENTS.md", "").status_code == 403
assert c2.post("/files/delete", data={"brain": default, "path": "agents"}).status_code == 403
assert (MKB / "agents").is_dir()
assert c2.post("/files/rename", data={"brain": default, "path": "memory", "newname": "x"}).status_code == 403
assert c2.post("/files/rename", data={"brain": default, "path": "sources", "newname": "wiki"}).status_code == 403, \
    "không đặt tên đè lên mục khoá"
r = c2.post("/files/upload", data={"brain": default, "path": ""},
            files={"file": ("CLAUDE.md", b"x", "text/markdown")})
assert r.status_code == 403
assert ghi("sources/van-ghi-duoc.md").status_code == 200, "thư mục dữ liệu vẫn ghi bình thường"
assert c2.post("/h2o-departments/khoa", data={"bat": "0"}).status_code == 403, "nhân viên không tự mở khoá"

# admin tắt khoá -> nhân viên ghi được; admin chọn mục riêng -> theo đúng danh sách đó
c2.cookies.clear()
assert c2.post("/h2o-departments/khoa", data={"bat": "0"}).json()["khoa"]["bat"] is False
la("truong_phong")
assert ghi("memory/khi-mo-khoa.md").status_code == 200
c2.cookies.clear()
r = c2.post("/h2o-departments/khoa", data={"bat": "1", "muc": "sources\n../x\nmemory"})
assert r.json()["khoa"]["muc"] == ["sources", "memory"], "bỏ mục có đường dẫn lạ"
la("truong_phong")
assert ghi("sources/bi-khoa.md").status_code == 403
assert ghi("wiki/gio-mo.md").status_code == 200, "wiki không còn trong danh sách khoá"
c2.cookies.clear()
c2.post("/h2o-departments/khoa", data={"muc": "\n".join(dep.KHOA_MAC_DINH)})
# admin không bao giờ bị khoá
assert c2.post("/files/write", data={"brain": str(MKB), "path": "memory/admin.md", "content": "x"}).status_code == 200

print("OK h2o_departments")
