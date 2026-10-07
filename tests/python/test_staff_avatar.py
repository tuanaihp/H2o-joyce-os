"""Ảnh đại diện nhân viên H2O: hiện trong khung hologram khi nhân viên gọi Joyce từ tinh cầu.

    python tests/run.py staff_avatar

Kiểm:
  - Admin đặt/xoá ảnh cho nhân viên; nhân viên tự đặt ảnh của CHÍNH MÌNH (id lấy từ cookie).
  - Nhân viên không được đặt ảnh cho người khác qua đường admin (/h2o-staff/avatar -> 403).
  - Chỉ nhận ảnh raster theo CHỮ KÝ FILE (PNG/JPG/WEBP/GIF): SVG và file giả đuôi bị từ chối,
    vì ảnh được phục vụ cùng origin với dashboard.
  - Quá 3MB bị từ chối; phục vụ lại đúng MIME + nosniff; xoá nhân viên thì xoá luôn ảnh.
"""
from _paths import ROOT, SERVER  # noqa: F401
import os
import tempfile
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-staff-avatar-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
os.environ["JOYCE_SESSIONS_DB"] = str(Path(state) / "sessions.db")

import main
import h2o_staff
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.post("/h2o-staff/avatar")(main.h2o_staff_avatar_admin)
app.post("/staff/avatar")(main.staff_avatar_self)
app.get("/staff/avatar/{sid}")(main.staff_avatar_get)
client = TestClient(app)

PNG = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64
JPG = bytes.fromhex("ffd8ffe0") + b"\x00" * 64
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'

ok, lan = h2o_staff.create("Nguyễn Lan", "0901234567", "1234")
assert ok, lan
ok, minh = h2o_staff.create("Trần Minh", "0907654321", "5678")
assert ok, minh

# ---- admin (không cookie nhân viên) ----
r = client.post("/h2o-staff/avatar", data={"id": lan["id"]}, files={"file": ("a.png", PNG, "image/png")})
assert r.status_code == 200 and r.json()["ok"], r.text
assert r.json()["staff"].get("avatar_v"), "record phải mang avatar_v để bỏ cache"
assert "pin_hash" not in r.json()["staff"], "không lộ hash PIN"
g = client.get(f"/staff/avatar/{lan['id']}")
assert g.status_code == 200 and g.content == PNG
assert g.headers["content-type"] == "image/png"
assert g.headers.get("x-content-type-options") == "nosniff"

# đổi sang JPG: file PNG cũ phải biến mất (không để hai ảnh cùng id)
r = client.post("/h2o-staff/avatar", data={"id": lan["id"]}, files={"file": ("a.jpg", JPG, "image/jpeg")})
assert r.status_code == 200
assert client.get(f"/staff/avatar/{lan['id']}").headers["content-type"] == "image/jpeg"
assert len(list(h2o_staff.AVATAR_DIR.glob(lan["id"] + ".*"))) == 1

# SVG / file giả đuôi -> từ chối, ảnh cũ giữ nguyên
r = client.post("/h2o-staff/avatar", data={"id": lan["id"]}, files={"file": ("x.png", SVG, "image/png")})
assert r.status_code == 400
assert client.get(f"/staff/avatar/{lan['id']}").content == JPG

# quá 3MB
big = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * (h2o_staff.AVATAR_MAX + 10)
assert client.post("/h2o-staff/avatar", data={"id": lan["id"]}, files={"file": ("b.png", big, "image/png")}).status_code == 400

# id lạ / có ký tự đường dẫn
assert client.post("/h2o-staff/avatar", data={"id": "../../settings"}, files={"file": ("a.png", PNG, "image/png")}).status_code == 400
assert client.get("/staff/avatar/..%2F..%2Fsettings").status_code == 404

# xoá ảnh = gửi không file
r = client.post("/h2o-staff/avatar", data={"id": lan["id"]})
assert r.status_code == 200 and "avatar_v" not in r.json()["staff"]
assert client.get(f"/staff/avatar/{lan['id']}").status_code == 404

# ---- nhân viên tự đặt ảnh ----
tok = h2o_staff.new_session(minh["id"])
client.cookies.set("h2o_staff", tok)
r = client.post("/staff/avatar", files={"file": ("me.png", PNG, "image/png")})
assert r.status_code == 200 and r.json()["staff"]["id"] == minh["id"]
assert client.get(f"/staff/avatar/{minh['id']}").content == PNG
# nhân viên KHÔNG được đặt ảnh cho người khác qua đường admin
r = client.post("/h2o-staff/avatar", data={"id": lan["id"]}, files={"file": ("a.png", PNG, "image/png")})
assert r.status_code == 403
client.cookies.clear()
# admin (không phải nhân viên) gọi đường tự-đặt -> 403, không tự gán cho ai
assert client.post("/staff/avatar", files={"file": ("me.png", PNG, "image/png")}).status_code == 403

# xoá nhân viên -> xoá luôn file ảnh
assert h2o_staff.remove(minh["id"])[0]
assert not list(h2o_staff.AVATAR_DIR.glob(minh["id"] + ".*"))

print("test_staff_avatar: OK")
