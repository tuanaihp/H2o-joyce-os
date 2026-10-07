"""Nhóm Tổng quan (Command Center, spec V1.4 mục 53): server/joyce_overview.py.

    python tests/python/test_tong_quan.py

Dựng một app FastAPI riêng với nguồn giả (không nạp main), gọi thật ba endpoint và kiểm:
  - Nhân viên bị chặn 403 (mặt quản trị toàn hệ thống).
  - Một nguồn chết chỉ làm khối đó báo lỗi (`sections_down`), trang vẫn trả số các khối khác.
  - KPI là số đếm THẬT từ bảng việc, không có số mô phỏng của bản mẫu HTML (148, 93,8%...).
  - Phòng chưa có thư mục brain KHÔNG được đọc kanban: _brain_root() gặp đường dẫn không tồn
    tại sẽ về brain mặc định, đọc vào là việc của brain chính bị tính cho phòng đó.
  - Lịch gom nhắc hẹn mọi brain theo đúng ngày, bỏ trùng theo id, bỏ nhắc đã xong.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import tempfile
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

import joyce_overview as ov
import joyce_today as jt

_fails = []


def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  " + str(extra)) if extra else ""))
    if not cond:
        _fails.append(name)


TMP = tempfile.mkdtemp(prefix="joyce-ov-")
B_MAIN = os.path.join(TMP, "Brain Default")
B_SALE = os.path.join(TMP, "Sale - CRM")
B_THU = os.path.join(TMP, "Ke Toan - Thu")
for d in (B_MAIN, B_SALE, B_THU):
    os.makedirs(d)
B_GONE = os.path.join(TMP, "Chua Tao")          # phòng có trong sổ nhưng chưa có thư mục

NOW = time.time()


def _task(i, st, t=None):
    return {"id": f"t{i}", "title": f"Việc {i}", "status": st, "priority": 2,
            "created_at": t or NOW - 60, "updated_at": t or NOW - 60}


BOARDS = {
    "brain": {"columns": {"review": [_task(1, "review", NOW - 6 * 3600)], "blocked": [_task(2, "blocked")],
                          "ready": [_task(3, "ready")], "running": [_task(4, "running")],
                          "done": [_task(5, "done")]},
              "counts": {"review": 1, "blocked": 1, "ready": 1, "running": 1, "todo": 0, "triage": 0, "done": 1},
              "completed_24h": 3, "orchestration": "off"},
    B_SALE: {"columns": {"blocked": [_task(9, "blocked")]}, "counts": {"blocked": 1, "running": 2},
             "completed_24h": 4, "orchestration": "auto"},
    B_THU: {"columns": {}, "counts": {}, "completed_24h": 0, "orchestration": "off"},
}
DOC_BRAIN = []


def board_view(b):
    DOC_BRAIN.append(b)
    if b == "HONG":
        raise RuntimeError("sqlite khoá")
    return BOARDS.get(b) or BOARDS["brain"]   # giống _brain_root: lạ thì về brain mặc định


day0 = time.mktime(time.localtime(NOW)[:3] + (0, 0, 0, 0, 0, -1))
REMS = {
    B_MAIN: [{"id": "r1", "status": "pending", "due_at": day0 + 9 * 3600, "text": "Tư vấn cưới"},
             {"id": "r2", "status": "done", "due_at": day0 + 10 * 3600, "text": "Đã xong"},
             {"id": "r3", "status": "pending", "due_at": day0 + 86400 + 8 * 3600, "text": "Chụp ngoại cảnh",
              "cron": "0 8 * * *"}],
    B_SALE: [{"id": "r1", "status": "pending", "due_at": day0 + 9 * 3600, "text": "Tư vấn cưới (trùng id)"},
             {"id": "r4", "status": "pending", "due_at": day0 + 3 * 86400 + 15 * 3600, "text": "Gọi lại khách"}],
}

STAFF = {"ok": False}


def make(hong=None):
    hong = hong or set()

    def boom(name, val):
        def f(*a, **k):
            if name in hong:
                raise RuntimeError(name + " chết")
            return val() if callable(val) else val
        return f

    today = jt.TodayDeps(
        board_view=board_view, brain_names=lambda: [], reminders_load=lambda b: {"reminders": REMS.get(b, [])},
        reminders_notify=boom("reminders", (True, "")), inbox_unread=boom("inbox", 2),
        inbox_recent=lambda n: [{"title": "Báo cáo tuần", "kind": "answer", "ts": NOW - 300, "read": False}],
        projects_ping=lambda: [{"id": "legacy", "ten": "H2O Legacy", "ok": True, "ms": 120},
                               {"id": "book", "ten": "H2OBOOK", "ok": False, "status": 502}],
        connect_snapshot=boom("connectors", {"c1": {"ok": True}, "c2": {"ok": False, "message": "hết phiên"}}),
        engines_health=lambda: {"claude": {"ok": True}}, connector_names=lambda c: c,
        read_settings=lambda: {}, staff_by_cookie=lambda tok: {"id": "nv1"} if STAFF["ok"] else None,
        conns_list=lambda: [{"id": "c1", "enabled": True}, {"id": "c2", "enabled": True}],
    )
    phong = {
        "brands": [{"id": "h2o", "ten": "H2O Studio", "shared_brain": "H2O Studio"},
                   {"id": "thuy", "ten": "ThuyH2O", "shared_brain": "ThuyH2O Studio"}],
        "khoi": [{"id": "k1", "ten": "Kinh Doanh", "brand": "h2o"}, {"id": "k2", "ten": "Kế Toán", "brand": "thuy"}],
        "phong": [
            {"id": "sale", "ten": "Sale & CRM", "khoi_id": "k1", "brain": "Sale - CRM", "brain_path": B_SALE,
             "brain_ok": True, "so_nguon": 12, "so_wiki": 5, "so_nhan_vien": 3},
            {"id": "thu", "ten": "Phòng Thu", "khoi_id": "k2", "brain": "Ke Toan - Thu", "brain_path": B_THU,
             "brain_ok": True, "so_nguon": 0, "so_wiki": 4, "so_nhan_vien": 0},
            {"id": "gone", "ten": "Phòng Mới", "khoi_id": "k1", "brain": "Chua Tao", "brain_path": B_GONE,
             "brain_ok": False, "so_nguon": 0, "so_wiki": 0, "so_nhan_vien": 1},
        ],
    }
    app = FastAPI()
    ov.register(app, ov.OverviewDeps(
        today=today, phong_view=boom("departments", phong), brain_paths=lambda: [B_MAIN, B_SALE, B_THU],
        usage_today=lambda: {"turns": 41, "tokens": 120345},
        vault_counts=lambda b: {"sources": 7, "wiki": 3, "facts": 11}, skills_count=lambda b: 4))
    return TestClient(app, base_url="http://127.0.0.1:7777")


jt._ping_cache.update({"ts": 0.0, "items": None})
cl = make()

# ---- 1. Bảng điều hành ----
r = cl.get("/api/joyce/v1/overview?brain=brain")
d = r.json()
check("overview trả 200 + ok", r.status_code == 200 and d.get("ok") is True)
k = {x["key"]: x["value"] for x in d["kpis"]}
check("KPI là số đếm thật từ bảng việc", k == {"done24": 3, "running": 1, "review": 1, "blocked": 1, "queue": 1, "turns": 41}, k)
rv = [x for x in d["kpis"] if x["key"] == "review"][0]
check("chờ duyệt quá 4 giờ được đếm riêng", rv.get("meta_n") == 1)
q = [x for x in d["kpis"] if x["key"] == "queue"][0]
check("hàng chờ khi AI tự vận hành tắt -> tô cảnh báo", q["tone"] == "warn" and q["meta"] == "off")
check("không có số mô phỏng của bản mẫu (148 / 93,8% / 286)",
      not any(str(v) in ("148", "93,8%", "286") for v in k.values()))
check("hàng đợi ưu tiên có việc kẹt (từ Pulse) và có task_id để mở", any(p.get("task_id") == "t2" for p in d["priority"]))
check("hàng đợi không lặp việc đã có trong Pulse", len([p for p in d["priority"] if p.get("task_id") == "t1"]) <= 1)
dom = {x["key"]: x for x in d["domains"]}
check("lĩnh vực kết nối: 1/2 online, 1 rủi ro", dom["connectors"]["done"] == 1 and dom["connectors"]["open"] == 2 and dom["connectors"]["risk"] == 1)
check("lĩnh vực ứng dụng H2O: 1/2 online", dom["apps"]["done"] == 1 and dom["apps"]["risk"] == 1)
check("nguồn nghiệp vụ chưa nối được nói thật (CRM, Wedding, Academy)",
      [b["id"] for b in d["business_sources"]] == ["crm", "wedding", "academy"])
check("lịch hôm nay chỉ nhắc pending của hôm nay, bỏ trùng id",
      [s["title"] for s in d["schedule"]] == ["Tư vấn cưới"], [s["title"] for s in d["schedule"]])
check("trí nhớ: số thật của brain", d["memory"]["facts"] == 11 and d["memory"]["skills"] == 4 and d["memory"]["phong"] == 3)
check("hoạt động gần đây có hộp thư + việc vừa xong", any(a["kind"] == "task_done" for a in d["activity"]) and any(a["title"] == "Báo cáo tuần" for a in d["activity"]))
check("không nguồn nào chết -> partial False", d["partial"] is False and d["sections_down"] == [])

# ---- 2. Một nguồn chết không làm trắng trang ----
jt._ping_cache.update({"ts": 0.0, "items": None})
d2 = make({"connectors", "departments"}).get("/api/joyce/v1/overview?brain=brain").json()
check("nguồn kết nối + phòng ban chết: trang vẫn ok", d2.get("ok") is True)
check("báo đúng nguồn thiếu", "connectors" in d2["sections_down"] and "departments" in d2["sections_down"], d2["sections_down"])
check("các khối khác vẫn có số", {x["key"]: x["value"] for x in d2["kpis"]}["done24"] == 3 and d2["units"] == [])

# ---- 3. Phòng ban ----
DOC_BRAIN.clear()
dp = cl.get("/api/joyce/v1/overview/departments").json()
by = {p["id"]: p for p in dp["phong"]}
check("phòng ban trả đủ 3 phòng, 2 thương hiệu", len(dp["phong"]) == 3 and len(dp["units"]) == 2)
check("phòng có brain: việc đọc từ brain CỦA PHÒNG", by["sale"]["tasks"]["blocked"] == 1 and by["sale"]["tasks"]["done24"] == 4)
check("phòng có việc kẹt -> rủi ro", by["sale"]["status"] == "risk")
check("phòng chỉ có wiki khung (lúc dựng sơ đồ), chưa việc chưa tài liệu -> 'empty', không giả là ổn",
      by["thu"]["status"] == "empty")
check("'có dữ liệu' chỉ đếm phòng đã nạp tài liệu nguồn", {x["id"]: x for x in dp["units"]}["thuy"]["co_du_lieu"] == 0)
check("phòng chưa có thư mục brain -> 'nobrain', KHÔNG đọc kanban",
      by["gone"]["status"] == "nobrain" and by["gone"]["tasks"] is None and B_GONE not in DOC_BRAIN and "brain" not in DOC_BRAIN)
u = {x["id"]: x for x in dp["units"]}
check("thương hiệu H2O: 2 phòng, 1 có dữ liệu, cộng dồn việc", u["h2o"]["phong"] == 2 and u["h2o"]["co_du_lieu"] == 1 and u["h2o"]["tasks"]["blocked"] == 1)

# ---- 4. Lịch 7 ngày ----
cal = cl.get("/api/joyce/v1/overview/calendar?days=7&start=" + time.strftime("%Y-%m-%d", time.localtime(day0))).json()
check("lịch trả 7 ngày, ngày đầu là hôm nay", len(cal["days"]) == 7 and cal["days"][0]["today"] is True)
check("lịch bỏ trùng id + bỏ nhắc đã xong", cal["total"] == 3, cal["total"])
check("nhắc rơi đúng ngày", [len(x["items"]) for x in cal["days"][:4]] == [1, 1, 0, 1], [len(x["items"]) for x in cal["days"][:4]])
check("nhắc lặp lại được đánh dấu", cal["days"][1]["items"][0]["repeat"] is True)
check("start sai định dạng không vỡ", cl.get("/api/joyce/v1/overview/calendar?start=khong-phai-ngay").json()["ok"] is True)

# ---- 5. Nhân viên bị chặn ----
STAFF["ok"] = True
for u_ in ("/api/joyce/v1/overview", "/api/joyce/v1/overview/departments", "/api/joyce/v1/overview/calendar"):
    rr = cl.get(u_)
    check("nhân viên bị chặn 403: " + u_, rr.status_code == 403 and rr.json().get("error") == "staff_denied")
STAFF["ok"] = False

if _fails:
    print(f"\nFAIL: {len(_fails)} {_fails}")
    raise SystemExit(1)
print("\nTất cả xanh.")
