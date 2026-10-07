"""Trang Hôm nay + H2O Pulse (joyce_today.py) - Experience Layer read-only.

    python tests/run.py joyce_today     (KHÔNG mạng, KHÔNG import main)

Spec gói Workstation: Pulse là feed "cần người ra tay" hợp nhất nguồn có sẵn
(kanban / h2o_projects / connect_health / reminders / inbox), xếp severity x độ
cũ, tự biến mất khi nguồn hết lỗi, và MỘT NGUỒN CHẾT KHÔNG ĐƯỢC KÉO SẬP cả feed.

Test bằng TodayDeps giả - không đụng sqlite/mạng, nên chạy được trên mọi máy.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import joyce_today  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


NOW = time.time()


def _deps(**over):
    """TodayDeps giả với mọi nguồn SẠCH - test nào cần lỗi thì ghi đè."""
    base = dict(
        board_view=lambda b: {"columns": {}, "counts": {}, "orchestration": "auto"},
        brain_names=lambda: ["Brain Default"],
        reminders_load=lambda b: {"reminders": []},
        reminders_notify=lambda: (True, ""),
        inbox_unread=lambda: 0,
        inbox_recent=lambda n: [],
        projects_ping=lambda: [],
        connect_snapshot=lambda: {},
        engines_health=lambda: {},
        connector_names=lambda c: c,
        read_settings=lambda: {"workspace_name": "H2O"},
        staff_by_cookie=lambda t: None,
    )
    base.update(over)
    return joyce_today.TodayDeps(**base)


def _boom(*a):
    raise RuntimeError("nguồn chết")


# --- Sạch hết -> feed rỗng, không errors ---
items, errs = joyce_today._pulse(_deps(), "brain", [])
check("sạch hết: feed rỗng", items == [])
check("sạch hết: không errors", errs == [])

# --- Mọi nguồn cùng báo -> đúng thứ tự severity, critical trước low sau ---
deps = _deps(
    board_view=lambda b: {
        "columns": {"blocked": [{"id": "t_b1", "title": "Việc kẹt", "updated_at": NOW - 600}],
                    "review": [{"id": "t_r1", "title": "Chờ duyệt", "updated_at": NOW - 5 * 3600}],
                    "ready": [{"title": "x"}], "todo": [], "triage": []},
        "counts": {"blocked": 1, "review": 1, "ready": 1},
        "orchestration": "off",
    },
    inbox_unread=lambda: 2,
    engines_health=lambda: {"ollama": {"ok": False, "message": "mất kết nối", "ts": NOW - 60}},
    connect_snapshot=lambda: {"zalo": {"ok": False, "message": "hết phiên", "ts": NOW - 30}},
)
apps = [{"id": "wedding", "ten": "Wedding", "ok": False, "status": 503, "err": ""}]
items, errs = joyce_today._pulse(deps, "brain", apps)
sevs = [i["severity"] for i in items]
check("thứ tự severity không giảm (critical trước)",
      sevs == sorted(sevs, key=joyce_today._sev_rank))
check("engine chết -> critical", any(i["severity"] == "critical" and i["source"] == "engine" for i in items))
check("app down -> critical", any(i["severity"] == "critical" and i["source"] == "h2o_app" for i in items))
check("connector lỗi -> high", any(i["source"] == "connector" for i in items))
check("blocked -> high + kèm lý do", any(i["source"] == "kanban" and i["severity"] == "high" for i in items))
check("review cũ >4h -> medium", any("chờ duyệt" in i["title"] for i in items))
check("orchestration tắt + hàng chờ -> medium", any("nằm chờ" in i["title"] for i in items))
check("inbox unread -> low", any(i["source"] == "inbox" and i["severity"] == "low" for i in items))
check("mọi item đều có href điều hướng", all(i.get("href") for i in items))
check("item kanban đơn-task kèm task_id (mở drawer từ Pulse)",
      any(i.get("task_id") == "t_b1" for i in items if i["severity"] == "high")
      and any(i.get("task_id") == "t_r1" for i in items if "chờ duyệt" in i["title"]))
check("errors rỗng khi đủ nguồn", errs == [])

# --- Review MỚI (chưa quá 4h) KHÔNG được lên Pulse ---
deps_fresh_review = _deps(board_view=lambda b: {
    "columns": {"review": [{"title": "Mới xong", "updated_at": NOW - 600}]},
    "counts": {"review": 1}, "orchestration": "auto"})
items2, _ = joyce_today._pulse(deps_fresh_review, "brain", [])
check("review mới <4h không lên Pulse", not any("chờ duyệt" in i["title"] for i in items2))

# --- Nguồn chết -> feed vẫn sống, nguồn đó vào errors ---
deps_dead = _deps(
    board_view=_boom,
    connect_snapshot=_boom,
    reminders_notify=_boom,
    inbox_unread=_boom,
    engines_health=_boom,
)
items3, errs3 = joyce_today._pulse(deps_dead, "brain", [])
check("mọi nguồn chết: feed vẫn trả về (rỗng)", items3 == [])
check("mọi nguồn chết được kể tên",
      set(errs3) == {"kanban", "connectors", "reminders", "inbox", "engines"})

deps_half = _deps(
    board_view=lambda b: {"columns": {"blocked": [{"title": "Kẹt", "updated_at": NOW}]},
                          "counts": {"blocked": 1}, "orchestration": "auto"},
    inbox_unread=_boom)
items4, errs4 = joyce_today._pulse(deps_half, "brain", [])
check("1 nguồn chết: nguồn khác vẫn báo", len(items4) == 1 and items4[0]["source"] == "kanban")
check("1 nguồn chết: errors chỉ tên nguồn đó", errs4 == ["inbox"])

# --- Lịch hôm nay: chỉ lấy pending TRONG ngày, xuyên mọi brain ---
future = NOW + 86400 * 3
# Giữa ngày HÔM NAY (không phải "bây giờ + 1 giờ": chạy test sau 23 giờ thì mốc đó rơi sang
# ngày mai và test đỏ oan - đã gặp 06/10/2026 lúc 23:2x).
_s0, _e0 = joyce_today._today_bounds()
HOP_AT = (_s0 + _e0) / 2
def _sch_load(b):
    if b != "Brain Default":
        return {"reminders": []}
    return {"reminders": [
        {"status": "pending", "due_at": HOP_AT, "text": "Họp"},
        {"status": "pending", "due_at": future, "text": "Mai sau"},
        {"status": "done", "due_at": NOW + 7200, "text": "Xong rồi"},
    ]}


deps_sch = _deps(
    brain_names=lambda: ["Brain Default", "Brain Phu"],
    reminders_load=_sch_load,
)
sch = joyce_today._schedule_today(deps_sch, deps_sch.brain_names())
check("lịch hôm nay: chỉ pending trong ngày", [s["title"] for s in sch] == ["Họp"])

# --- Brief deterministic: nguồn nào đếm được thì nói đó ---
b = joyce_today._brief({"blocked": 0, "review": 2, "apps_down": 1,
                        "connectors_down": 0, "unread": 0})
check("brief kể đúng nhóm cần chú ý", b["count"] == 2 and "chờ duyệt" in b["text"])
b0 = joyce_today._brief({"blocked": 0, "review": 0, "apps_down": 0,
                         "connectors_down": 0, "unread": 0})
check("brief sạch -> 'đang vận hành ổn'", b0["count"] == 0)

# --- Contract v1 (Phase 3-lite): router lên app mini, không import main ---
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_moved = []


async def _fake_move(tid, status, brain, reason):
    _moved.append((tid, status, brain, reason))
    return {"ok": True, "status": status}


def _fake_get(tid, brain):
    if tid != "t_1":
        return None
    return {"task": {"id": tid, "status": "review"}, "events": [], "runs": []}


_app = FastAPI()
joyce_today.register(_app, _deps(
    board_view=lambda b: {"columns": {"review": [
        {"id": "t_1", "title": "Viec A", "updated_at": NOW}]},
        "counts": {"review": 1}},
    task_get=_fake_get, task_move=_fake_move,
    agents_list=lambda b: [{"slug": "a1", "name": "Agent A"}],
))
c = TestClient(_app)

j = c.get("/api/joyce/v1/tasks").json()
check("v1 tasks: trả counts.review", j["ok"] and j["counts"]["review"] == 1)

j = c.get("/api/joyce/v1/approvals").json()
check("v1 approvals: liệt task review + stale flag",
      j["total"] == 1 and j["items"][0]["id"] == "t_1" and j["items"][0]["stale"] is False)

r = c.post("/api/joyce/v1/approvals/t_1/approve")
check("v1 approve -> move done", r.json().get("ok") and _moved[-1][1] == "done")

r = c.post("/api/joyce/v1/approvals/t_1/reject", data={"comment": "sua lai"})
check("v1 reject -> move todo + reason", _moved[-1] == ("t_1", "todo", "brain", "sua lai"))

check("v1 context task", c.get("/api/joyce/v1/context/task/t_1").json()["task"]["id"] == "t_1")
check("v1 context 404", c.get("/api/joyce/v1/context/task/zzz").status_code == 404)
check("v1 agents", c.get("/api/joyce/v1/agents").json()["agents"][0]["slug"] == "a1")

# Staff đứng trên cookie h2o_staff hợp lệ -> approve/reject 403 (khớp rào /kanban)
_app_staff = FastAPI()
joyce_today.register(_app_staff, _deps(staff_by_cookie=lambda t: {"id": "st1"},
                                       task_move=_fake_move))
cs = TestClient(_app_staff)
check("staff approve -> 403", cs.post("/api/joyce/v1/approvals/t_1/approve").status_code == 403)
check("staff reject -> 403", cs.post("/api/joyce/v1/approvals/t_1/reject").status_code == 403)
check("staff vẫn đọc được danh sách", cs.get("/api/joyce/v1/approvals").status_code == 200)

# --- Brief LLM (aux model): fallback an toàn + cache theo chữ ký số liệu ---
_calls = []


async def _brief_ok(prompt):
    _calls.append(prompt)
    return "Sáng nay hệ thống êm, chỉ còn 1 việc chờ duyệt. Gợi ý: duyệt Viec A trước."


async def _brief_boom(prompt):
    raise RuntimeError("aux chết")


joyce_today._brief_cache.update({"key": "", "text": "", "ts": 0.0})
_app_brief = FastAPI()
joyce_today.register(_app_brief, _deps(brief_ai=_brief_ok))
cb = TestClient(_app_brief)
r = cb.get("/api/joyce/v1/brief-ai").json()
check("brief-ai: trả câu LLM", r.get("ok") and not r.get("fallback")
      and "duyệt" in r["brief"])
r2 = cb.get("/api/joyce/v1/brief-ai").json()
check("brief-ai: cache hit (dep gọi 1 lần)", r2.get("cached") and len(_calls) == 1)

joyce_today._brief_cache.update({"key": "", "text": "", "ts": 0.0})
_app_brief_dead = FastAPI()
joyce_today.register(_app_brief_dead, _deps(brief_ai=_brief_boom))
cd = TestClient(_app_brief_dead)
r = cd.get("/api/joyce/v1/brief-ai").json()
check("brief-ai: aux chết -> fallback deterministic", r.get("fallback") is True
      and isinstance(r.get("brief"), dict) and r["brief"].get("title"))

_app_brief_none = FastAPI()
joyce_today.register(_app_brief_none, _deps())  # không tiêm brief_ai
cn = TestClient(_app_brief_none)
check("brief-ai: chưa cấu hình aux -> fallback", cn.get("/api/joyce/v1/brief-ai").json().get("fallback") is True)

# --- Knowledge search: bọc /files/search, staff 403 ---
_app_kn = FastAPI()
joyce_today.register(_app_kn, _deps(
    knowledge_search=lambda b, q, l: {"items": [{"path": "wiki/A.md", "name": "A.md"}]}))
ck = TestClient(_app_kn)
j = ck.get("/api/joyce/v1/knowledge/search", params={"q": "pareto"}).json()
check("knowledge: item gắn source=vault", j["items"][0]["source"] == "vault")
check("knowledge: q rỗng -> items rỗng", ck.get("/api/joyce/v1/knowledge/search").json()["items"] == [])

_app_kn_staff = FastAPI()
joyce_today.register(_app_kn_staff, _deps(staff_by_cookie=lambda t: {"id": "st1"},
                                          knowledge_search=lambda b, q, l: {"items": []}))
cks = TestClient(_app_kn_staff)
cks.cookies.set("h2o_staff", "tok")
check("knowledge: staff 403", cks.get("/api/joyce/v1/knowledge/search", params={"q": "x"}).status_code == 403)

# --- Chat threads: dep nhận request để tự scope staff ---
_seen_req = []


def _threads(req, b, lim):
    _seen_req.append(req is not None)
    return {"sessions": [{"id": "s1", "title": "Ca sáng"}]}


_app_th = FastAPI()
joyce_today.register(_app_th, _deps(
    threads_list=_threads,
    thread_create=lambda req, b: {"ok": True, "id": "s9", "channel": "web"}))
ct = TestClient(_app_th)
check("threads list", ct.get("/api/joyce/v1/chat/threads").json()["sessions"][0]["id"] == "s1")
check("threads list: dep nhận request", _seen_req and all(_seen_req))
check("threads new", ct.post("/api/joyce/v1/chat/threads").json()["id"] == "s9")

# --- Commands: whitelist + staff 403 ---
async def _cmds(name, brain):
    return {"kanban.nudge": {"started": False}}.get(name)


_app_cmd = FastAPI()
joyce_today.register(_app_cmd, _deps(run_command=_cmds))
cc = TestClient(_app_cmd)
check("commands: lệnh có trong whitelist", cc.post("/api/joyce/v1/commands", data={"cmd": "kanban.nudge"}).json()["ok"])
check("commands: lệnh lạ -> 404", cc.post("/api/joyce/v1/commands", data={"cmd": "rm -rf /"}).status_code == 404)

_app_cmd_staff = FastAPI()
joyce_today.register(_app_cmd_staff, _deps(staff_by_cookie=lambda t: {"id": "st1"},
                                           run_command=_cmds))
ccs = TestClient(_app_cmd_staff)
ccs.cookies.set("h2o_staff", "tok")
check("commands: staff 403", ccs.post("/api/joyce/v1/commands", data={"cmd": "kanban.nudge"}).status_code == 403)

# --- Learning proposals: bọc hàng chờ học của learn.py + undo (staff 403) ---
_app_lp = FastAPI()
joyce_today.register(_app_lp, _deps(
    learn_review=lambda b, l: {"git_repo": True,
                               "commits": [{"hash": "abc123", "msg": "học A"}]},
    learn_undo=lambda b: {"ok": True, "reverted": "abc123"}))
cl = TestClient(_app_lp)
j = cl.get("/api/joyce/v1/learning-proposals").json()
check("learn: trả commits + git_repo", j["ok"] and j["items"][0]["hash"] == "abc123"
      and j["git_repo"] is True)
check("learn undo", cl.post("/api/joyce/v1/learning-proposals/undo").json()["reverted"] == "abc123")

_app_lp_staff = FastAPI()
joyce_today.register(_app_lp_staff, _deps(staff_by_cookie=lambda t: {"id": "st1"},
                                          learn_undo=lambda b: {"ok": True}))
cls = TestClient(_app_lp_staff)
check("learn undo: staff 403", cls.post("/api/joyce/v1/learning-proposals/undo").status_code == 403)

# --- Phase contract nốt: learning POST, agent-runs, context generic, thread messages ---
_enq = []


async def _learn_enq(brain, sid, u, a):
    _enq.append((brain, sid, u[:20], a))


_app_lp2 = FastAPI()
joyce_today.register(_app_lp2, _deps(learn_enqueue=_learn_enq))
cl2 = TestClient(_app_lp2)
check("learn POST: queue ok", cl2.post("/api/joyce/v1/learning-proposals",
      data={"text": "ghi chú đủ dài để được học abcxyz"}).json()["ok"] is True and _enq)
check("learn POST: quá ngắn -> 400", cl2.post("/api/joyce/v1/learning-proposals",
      data={"text": "ngắn"}).status_code == 400)

_runs = []


def _run_enq(brain, title, intent, **kw):
    _runs.append((brain, title, kw))
    return "t_new"


_app_run = FastAPI()
joyce_today.register(_app_run, _deps(task_enqueue=_run_enq))
cr = TestClient(_app_run)
j = cr.post("/api/joyce/v1/agent-runs", data={"title": "Soạn bài", "needs_approval": "true"}).json()
check("agent-runs: trả task_id", j["ok"] and j["task_id"] == "t_new" and _runs[0][2]["needs_approval"])
check("agent-runs: thiếu title -> reject", cr.post("/api/joyce/v1/agent-runs",
      data={"title": ""}).status_code in (400, 422))

_app_run_staff = FastAPI()
joyce_today.register(_app_run_staff, _deps(staff_by_cookie=lambda t: {"id": "s"},
                                           task_enqueue=_run_enq))
crs = TestClient(_app_run_staff)
check("agent-runs: staff 403", crs.post("/api/joyce/v1/agent-runs", data={"title": "x"}).status_code == 403)

# Context tổng quát: task hoạt động, type domain khác trả 404 + supported
check("context task generic", c.get("/api/joyce/v1/context/task/t_1").json()["task"]["id"] == "t_1")
j = c.get("/api/joyce/v1/context/customer/cu_1").json()
check("context domain khác -> 404 + supported", j.get("supported") == ["task"])

# Thread messages: append vào phiên có thật, staff chỉ phiên kênh mình
_appended = []
_app_msg = FastAPI()
joyce_today.register(_app_msg, _deps(
    session_get=lambda sid: {"id": sid, "channel": "web"} if sid == "s1" else None,
    thread_append=lambda sid, role, c: _appended.append((sid, role, c)) or 42))
cm = TestClient(_app_msg)
j = cm.post("/api/joyce/v1/chat/threads/s1/messages", data={"content": "chào"}).json()
check("thread msg: append + message_id", j["ok"] and j["message_id"] == 42
      and _appended[-1][1] == "user")
check("thread msg: phiên lạ -> 404", cm.post("/api/joyce/v1/chat/threads/nope/messages",
      data={"content": "x"}).status_code == 404)

_app_msg_staff = FastAPI()
joyce_today.register(_app_msg_staff, _deps(
    staff_by_cookie=lambda t: {"id": "st9"},
    staff_channel=lambda st: "staff:st9",
    session_get=lambda sid: {"id": sid, "channel": "web"},
    thread_append=lambda *a: 1))
cms = TestClient(_app_msg_staff)
check("thread msg: staff phiên người khác -> 403",
      cms.post("/api/joyce/v1/chat/threads/s1/messages", data={"content": "x"}).status_code == 403)

# --- Integration Center: aggregate connectors + engines + apps + bots ---
_app_int = FastAPI()
joyce_today.register(_app_int, _deps(
    conns_list=lambda: [{"id": "gg", "label": "Gmail", "connector_id": "google",
                         "transport": "http", "enabled": True, "perm": "full"}],
    connect_snapshot=lambda: {"gg": {"ok": False, "message": "token hết hạn", "ts": NOW}},
    engines_health=lambda: {"claude": {"ok": True, "message": "", "ts": NOW}},
    bots_list=lambda: [{"id": "b1", "name": "Bot sale", "enabled": True}],
))
ci = TestClient(_app_int)
j = ci.get("/api/joyce/v1/integrations").json()
check("integrations: connector gộp health", j["connectors"][0]["ok"] is False
      and j["connectors"][0]["id"] == "gg")
check("integrations: summary đếm down", j["summary"]["down"] == 1
      and j["summary"]["connectors"] == 1)
check("integrations: engine + bot", j["engines"][0]["name"] == "claude"
      and j["bots"][0]["id"] == "b1")

# agent-runs truyền idempotency_key xuống enqueue
_runs2 = []


def _run_enq2(brain, title, intent, **kw):
    _runs2.append(kw)
    return "t_idem"


_app_idem = FastAPI()
joyce_today.register(_app_idem, _deps(task_enqueue=_run_enq2))
cid = TestClient(_app_idem)
cid.post("/api/joyce/v1/agent-runs", data={"title": "X", "idempotency_key": "k-1"})
check("agent-runs: idempotency_key qua enqueue", _runs2[-1].get("idempotency_key") == "k-1")

print()
if _fails:
    print("FAIL:", ", ".join(_fails))
    sys.exit(1)
print("PASS joyce_today")
