"""Tinh cầu Trái Đất H2O: thời tiết kinh doanh + trạng thái nạp dữ liệu (hố đen).

    python tests/run.py business_weather

Kiểm:
  - Quy đổi tiến độ doanh thu -> 7 kiểu thời tiết theo ngưỡng; thiếu dữ liệu thì không bao giờ
    "nắng"; có sự cố thì lốc xoáy.
  - Dữ liệu mẫu TẤT ĐỊNH theo ngày (tải lại không nhảy thời tiết) và luôn mang cờ nguon=demo.
  - /business-weather: admin thấy số, nhân viên chỉ thấy kiểu thời tiết (không lộ doanh thu).
  - /brain/nap-status: tải file lên -> đang nạp + tên file; file trong sources/ vừa đổi cũng tính.
"""
from _paths import ROOT, SERVER  # noqa: F401
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-thoi-tiet-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
os.environ["JOYCE_SESSIONS_DB"] = str(Path(state) / "sessions.db")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import main
import business_weather as bw
import h2o_staff
from fastapi import FastAPI
from fastapi.testclient import TestClient

NG = bw.NGUONG_MAC_DINH
assert bw.thoi_tiet(120, True, "", NG) == "nang"
assert bw.thoi_tiet(95, True, "", NG) == "nang_nhe"
assert bw.thoi_tiet(80, True, "", NG) == "nhieu_may"
assert bw.thoi_tiet(60, True, "", NG) == "mua"
assert bw.thoi_tiet(40, True, "", NG) == "giong"
assert bw.thoi_tiet(10, True, "", NG) == "bao"
assert bw.thoi_tiet(150, True, "mất kết nối POS", NG) == "loc_xoay"
assert bw.thoi_tiet(150, False, "", NG) == "nhieu_may", "thiếu dữ liệu thì không được nắng"

t = datetime(2026, 10, 6, 15, 0)
a, b = bw.bao_cao(t), bw.bao_cao(t)
assert a["state"] == b["state"] and a["doanh_thu_thang"] == b["doanh_thu_thang"], "mẫu phải tất định"
assert a["nguon"] == "demo", "chưa nối CRM thì phải ghi rõ là dữ liệu mẫu"
assert a["state"] in bw.THU_TU and a["pct"] > 0
kinds = {bw.bao_cao(datetime(2026, m, d, 15)).get("state") for m in (9, 10, 11, 12) for d in range(1, 29)}
assert len(kinds) >= 4, kinds

app = FastAPI()
app.get("/business-weather")(main.business_weather_get)
app.get("/brain/nap-status")(main.brain_nap_status)
app.post("/files/upload")(main.files_upload)
c = TestClient(app)

r = c.get("/business-weather").json()
assert r["ok"] and "doanh_thu_thang" in r and r["nguon"] == "demo"
ok, nv = h2o_staff.create("Lan", "0901111999", "1234")
assert ok
c.cookies.set("h2o_staff", h2o_staff.new_session(nv["id"]))
r = c.get("/business-weather").json()
assert r["state"] and "doanh_thu_thang" not in r and r.get("an_so"), "nhân viên không thấy số doanh thu"
c.cookies.clear()

brain = str(main._default_brain_dir())
main._ensure_brain_scaffold(brain)


def lam_cu_het():
    """Cho mọi file trong brain 'cũ' quá cửa sổ nạp (file mẫu của scaffold vừa tạo xong)."""
    old = time.time() - main._NAP_CUA_SO - 30
    for f in Path(brain).rglob("*"):
        if f.is_file():
            os.utime(f, (old, old))


lam_cu_het()
r = c.get("/brain/nap-status", params={"brain": brain}).json()
assert r["active"] is False, r
r = c.post("/files/upload", data={"brain": brain, "folder": "sources"},
           files={"file": ("bang-gia-2026.md", b"# Bang gia", "text/markdown")})
assert r.status_code == 200, r.text
r = c.get("/brain/nap-status", params={"brain": brain}).json()
assert r["active"] and "bang-gia-2026.md" in r["items"], r

# file trong wiki/ vừa đổi (Joyce đang chưng cất) cũng tính là đang nạp
main._NAP_SU_KIEN.clear()
wiki = Path(main._resolve_subfolder(brain, r"^(\d+\s*[-_.]\s*)?wiki$", "wiki"))
(wiki / "bang-gia.md").write_text("x", encoding="utf-8")
r = c.get("/brain/nap-status", params={"brain": brain}).json()
assert r["active"] and "bang-gia.md" in r["items"], r
# quá cửa sổ thời gian -> hết "đang nạp"
lam_cu_het()
assert c.get("/brain/nap-status", params={"brain": brain}).json()["active"] is False

print("OK business_weather")
