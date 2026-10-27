"""Quản lý Shop: máy chủ giữ trạng thái chung của trang quan-ly-shop.html (server/shop_state.py).

    python tests/run.py shop_state

Trang mẫu giữ dữ liệu của 12 module trong localStorage nên mỗi máy một bản. /shop/state cho nhiều máy
dùng chung một bản; chỉ chủ và quản lý đọc ghi được vì trong đó có thu chi và nhân sự.
"""
from _paths import ROOT, SERVER, moi_duong_dan  # noqa: F401
import json
import os
import sys
import tempfile
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-shop-state-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import shop_state
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


app = FastAPI()
vai = {"staff": None}


@app.middleware("http")
async def gan_nhan_vien(request: Request, call_next):
    request.state.staff = vai["staff"]
    return await call_next(request)


shop_state.register(app)
http = TestClient(app)

r = http.get("/shop/state").json()
check("chưa lưu gì thì trả về rỗng", r["ok"] and r["keys"] == {} and r["updated"] == 0)

biz = json.dumps({"orders": [{"id": 1}], "ledger": [], "staff": [], "tasks": [], "stock": [3, 4]})
r = http.post("/shop/state", data={"data": json.dumps({"joyce-shop-business": biz, "joyce-shop-sample": "1"})})
check("lưu được hai khoá hợp lệ", r.status_code == 200 and r.json()["ok"])
g = http.get("/shop/state").json()
check("đọc lại đúng nguyên văn từng khoá", g["keys"]["joyce-shop-business"] == biz and g["keys"]["joyce-shop-sample"] == "1" and g["updated"] > 0)
check("file nằm trong thư mục state", (Path(state) / "shop_state.json").exists())

r = http.post("/shop/state", data={"data": json.dumps({"khoa-la": "{}", "joyce-shop-chat": "[]"})})
g = http.get("/shop/state").json()
check("khoá lạ bị bỏ qua, ghi đè theo bản mới nhất", r.status_code == 200 and "khoa-la" not in g["keys"] and g["keys"] == {"joyce-shop-chat": "[]"})

check("chuỗi không phải JSON bị từ chối 400", http.post("/shop/state", data={"data": json.dumps({"joyce-shop-chat": "khong phai json"})}).status_code == 400)
check("giá trị không phải chuỗi bị từ chối 400", http.post("/shop/state", data={"data": json.dumps({"joyce-shop-chat": [1, 2]})}).status_code == 400)
check("phần thân không phải object bị từ chối 400", http.post("/shop/state", data={"data": "[1]"}).status_code == 400)
lon = json.dumps("x" * (shop_state.TOI_DA + 10))
check("dữ liệu quá lớn bị từ chối, không cắt cụt", http.post("/shop/state", data={"data": json.dumps({"joyce-shop-chat": lon})}).status_code == 400)
check("lỗi không làm hỏng bản đang lưu", http.get("/shop/state").json()["keys"] == {"joyce-shop-chat": "[]"})

vai["staff"] = {"ten": "Lan", "role": "nhan_vien"}
check("nhân viên thường đọc bị 403", http.get("/shop/state").status_code == 403)
check("nhân viên thường ghi bị 403", http.post("/shop/state", data={"data": "{}"}).status_code == 403)
vai["staff"] = {"ten": "Hà", "role": "truong_phong"}
check("trưởng phòng đọc được", http.get("/shop/state").status_code == 200)
check("trưởng phòng ghi được", http.post("/shop/state", data={"data": json.dumps({"joyce-shop-sample": "0"})}).status_code == 200)

if _fails:
    print("\nTHẤT BẠI %d: %s" % (len(_fails), _fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
