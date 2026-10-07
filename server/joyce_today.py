# -*- coding: utf-8 -*-
"""
joyce_today.py - Trang "Hôm nay" + H2O Pulse (Experience Layer, gói nâng cấp Workstation).

NGUYÊN TẮC (spec tai-lieu-update-tu-openai): Joyce là lớp trải nghiệm - chỉ ĐỌC và tổng
hợp từ các store đã có sẵn (kanban sqlite, reminders.json, inbox, h2o_projects ping,
connect_health). KHÔNG tạo bảng/store nghiệp vụ mới, KHÔNG copy schema domain, KHÔNG ghi
mock data. Mọi nguồn được tiêm qua TodayDeps để module không phụ thuộc main.

H2O Pulse = feed cảnh báo "cần người ra tay": tín hiệu có chi phí im lặng (app down = mất
khách, connector chết = tự động hoá âm thầm hỏng, task blocked = việc chết đứng). Item tự
biến mất khi nguồn hết lỗi - không có nút "đã đọc" thủ công.

Xếp hạng: critical > high > medium > low, cùng mức thì cái chờ lâu lên trước.
"""
from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import JSONResponse

# Cache kết quả ping app H2O - ping_all() đi mạng ngoài (15 app x timeout) nên gọi thẳng
# mỗi lần load Today là treo trang. 120s đủ tươi cho màn tổng quan; HUD/Joyce vẫn có nút
# check tay ở trang Dự án khi cần sống thật.
_PING_TTL = 120.0
_ping_cache: dict = {"ts": 0.0, "items": None}
_ping_lock = asyncio.Lock()

# Task chờ duyệt quá ngưỡng này mới lên Pulse (review mới xong vài phút thì chưa đáng báo)
_REVIEW_STALE_SEC = 4 * 3600

# Cache brief LLM: chữ ký = brain + ngày + số liệu + pulse top. TTL 10 phút - đủ để F5
# không gọi lại aux model, đủ ngắn để số liệu đổi thì brief đổi theo.
_BRIEF_TTL = 600.0
_brief_cache: dict = {"key": "", "text": "", "ts": 0.0}
_brief_lock = asyncio.Lock()


@dataclass
class TodayDeps:
    """Mọi thứ module cần, tiêm từ main - đúng pattern TasksDeps/RemindersDeps."""

    board_view: Callable[[str], dict]            # tasks_feature.board_view(brain)
    brain_names: Callable[[], list]              # tên brain để gom reminders đa-vault
    reminders_load: Callable[[str], dict]        # reminders_feature._load(brain)
    reminders_notify: Callable[[], tuple]        # reminders_feature.notify_status()
    inbox_unread: Callable[[], int]              # inbox.so_chua_doc()
    inbox_recent: Callable[[int], list]          # inbox.danh_sach(limit)
    projects_ping: Callable[[], list]            # h2o_projects.ping_all() (đồng bộ, đi mạng)
    connect_snapshot: Callable[[], dict]         # connect_health.snapshot()
    engines_health: Callable[[], dict]           # connect_health._engines sống
    connector_names: Callable[[str], str]        # conn_id -> tên hiển thị
    read_settings: Callable[[], dict]            # cfgmod.read_settings
    staff_by_cookie: Callable[[str], Optional[dict]]   # h2o_staff.staff_by_token
    vault_stats: Callable[[str], dict] = lambda b: {}  # số note/fact nếu có
    get_day_bounds: Optional[Callable[[], tuple]] = None  # (start,end) epoch hôm nay
    # Phase 3-lite (contract /api/joyce/v1/*): đọc/ghi task qua adapter của kanban,
    # KHÔNG mở store mới. task_move là async vì phải await _asnapshot sau move.
    task_get: Optional[Callable[[str, str], Optional[dict]]] = None  # (tid, brain) -> task+events+runs
    task_move: Optional[Callable[..., Any]] = None                   # async (tid, status, brain, reason)
    agents_list: Optional[Callable[[str], list]] = None              # agents_index(brain, nhẹ)
    brief_ai: Optional[Callable[[str], Any]] = None                  # async prompt -> câu brief (aux model)
    knowledge_search: Optional[Callable[[str, str, int], Any]] = None  # async (brain, q, limit)
    threads_list: Optional[Callable[[Any, str, int], dict]] = None   # (request, brain, limit)
    thread_create: Optional[Callable[[Any, str], dict]] = None       # (request, brain) -> {id, channel}
    run_command: Optional[Callable[[str, str], Any]] = None          # async (name, brain) -> dict
    learn_review: Optional[Callable[[str, int], Any]] = None         # (brain, limit) -> {commits, git_repo}
    learn_undo: Optional[Callable[[str], Any]] = None                # (brain) -> kết quả git revert
    learn_enqueue: Optional[Callable[..., Any]] = None               # async (brain, sid, user, asst)
    task_enqueue: Optional[Callable[..., Any]] = None                # tasks_feature.enqueue -> tid
    thread_append: Optional[Callable[[str, str, str], Any]] = None   # (sid, role, content) -> msg id
    session_get: Optional[Callable[[str], Optional[dict]]] = None    # (sid) -> session dict
    staff_channel: Optional[Callable[[dict], str]] = None            # staff -> "staff:<id>"
    conns_list: Optional[Callable[[], list]] = None                  # mcp_store.list_connections (redacted)
    bots_list: Optional[Callable[[], list]] = None                   # chatbot_store.list_bots (redacted)


def _sev_rank(sev: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(sev, 9)


def _age_sec(ts: float) -> str:
    """'3h' / '25p' / 'vừa xong' - nhãn tuổi của cảnh báo."""
    dt = max(0, time.time() - float(ts or 0))
    if dt < 90:
        return "vừa xong"
    if dt < 3600:
        return f"{int(dt // 60)}p trước"
    if dt < 86400:
        return f"{int(dt // 3600)}h trước"
    return f"{int(dt // 86400)} ngày trước"


async def _ping_projects(deps: TodayDeps, force: bool = False) -> list:
    """Ping toàn bộ app H2O có cache TTL. Chạy trong thread để khỏi nghẽn event loop."""
    now = time.time()
    if not force and _ping_cache["items"] is not None and now - _ping_cache["ts"] < _PING_TTL:
        return _ping_cache["items"]
    async with _ping_lock:
        now = time.time()
        if not force and _ping_cache["items"] is not None and now - _ping_cache["ts"] < _PING_TTL:
            return _ping_cache["items"]
        try:
            items = await asyncio.to_thread(deps.projects_ping)
        except Exception:
            items = _ping_cache["items"] or []
        if items:
            _ping_cache["items"], _ping_cache["ts"] = items, time.time()
        return _ping_cache["items"] or []


def _pulse(deps: TodayDeps, brain: str, apps: list) -> tuple:
    """Hợp nhất mọi nguồn cảnh báo thành một feed xếp theo mức độ.

    Trả (items, errors): mỗi nguồn bọc try/except riêng - một nguồn chết
    (kanban sqlite khoá, connect_health lỗi) KHÔNG được làm sập cả feed,
    chỉ đánh dấu nguồn đó vào errors để UI hiện "thiếu nguồn" thay vì
    người dùng tưởng hệ thống đang sạch."""
    items: list[dict] = []
    errors: list[str] = []
    now = time.time()
    try:
        view = deps.board_view(brain) or {}
    except Exception as e:
        view, errors = {}, errors + ["kanban"]
        _log_pulse_error("kanban", e)
    cols = view.get("columns") or {}
    counts = view.get("counts") or {}

    # 1. Não AI chết / hết phiên -> mọi thứ im lặng, nặng nhất
    try:
        for name, rec in (deps.engines_health() or {}).items():
            if rec.get("ok") is False:
                items.append({
                    "severity": "critical", "source": "engine",
                    "title": f"Bộ não {name} lỗi",
                    "meta": (rec.get("message") or "mất kết nối/xác thực")[:140],
                    "since": rec.get("ts") or now, "href": "models",
                })
    except Exception as e:
        errors.append("engines"); _log_pulse_error("engines", e)

    # 2. App H2O offline -> mất khách/doanh thu trực tiếp
    for a in apps:
        if a.get("ok") is False:
            bits = []
            if a.get("status"):
                bits.append(f"HTTP {a['status']}")
            if a.get("err"):
                bits.append(str(a["err"])[:100])
            items.append({
                "severity": "critical", "source": "h2o_app",
                "title": f"{a.get('ten') or a.get('id')} không phản hồi",
                "meta": " · ".join(bits) or "không vào được",
                "since": now, "href": "projects",
            })

    # 3. Connector/MCP lỗi -> tự động hoá đang chạy nhưng không gọi được gì
    try:
        for cid, rec in (deps.connect_snapshot() or {}).items():
            if rec.get("ok") is False:
                items.append({
                    "severity": "high", "source": "connector",
                    "title": f"Kết nối {deps.connector_names(cid) or cid} lỗi",
                    "meta": str(rec.get("message") or rec.get("detail") or "")[:140],
                    "since": rec.get("ts") or now, "href": "mcp",
                })
    except Exception as e:
        errors.append("connectors"); _log_pulse_error("connectors", e)

    if "kanban" not in errors:
        # 4. Task bị kẹt (blocked) - từng task một dòng, kèm lý do
        for task in cols.get("blocked") or []:
            items.append({
                "severity": "high", "source": "kanban",
                "title": task.get("title") or "(không tên)",
                "meta": (task.get("block_reason") or "đang bị kẹt")[:140],
                "since": task.get("updated_at") or task.get("created_at") or now,
                "href": "kanban", "task_id": task.get("id"),
            })

        # 5. Chờ duyệt quá lâu
        review = cols.get("review") or []
        stale = [t for t in review
                 if now - float(t.get("updated_at") or t.get("created_at") or now) > _REVIEW_STALE_SEC]
        if stale:
            items.append({
                "severity": "medium", "source": "kanban",
                "title": f"{len(stale)} việc chờ duyệt quá {_REVIEW_STALE_SEC // 3600:.0f}h",
                "meta": (stale[0].get("title") or "")[:120],
                "since": min(float(t.get("updated_at") or t.get("created_at") or now) for t in stale),
                "href": "kanban", "task_id": stale[0].get("id"),
            })

        # 6. Việc xếp hàng nhưng orchestration tắt -> hàng đợi "chết câm" không ai hay
        waiting = int(counts.get("ready", 0)) + int(counts.get("todo", 0)) + int(counts.get("triage", 0))
        if waiting and view.get("orchestration") in ("off", "", None):
            items.append({
                "severity": "medium", "source": "kanban",
                "title": f"{waiting} việc đang nằm chờ",
                "meta": "AI tự vận hành đang tắt - bật trên trang Việc để Joyce nhận việc",
                "since": now, "href": "kanban",
            })

    # 7. Nhắc hẹn không có kênh báo -> nhắc vào hư không
    try:
        ok, why = deps.reminders_notify() or (True, "")
        if not ok:
            items.append({
                "severity": "medium", "source": "reminders",
                "title": "Nhắc hẹn thiếu kênh báo",
                "meta": str(why or "chưa nối Telegram/Zalo")[:140],
                "since": now, "href": "channels",
            })
    except Exception as e:
        errors.append("reminders"); _log_pulse_error("reminders", e)

    # 8. Hộp thư nền có kết quả chưa đọc -> nhẹ nhất, chỉ báo "có cái mới"
    try:
        unread = int(deps.inbox_unread() or 0)
        if unread:
            items.append({
                "severity": "low", "source": "inbox",
                "title": f"{unread} kết quả nền chưa đọc",
                "meta": "Kết quả task/loop/nhắc hẹn đã về hộp thư",
                "since": now, "href": "home",
            })
    except Exception as e:
        errors.append("inbox"); _log_pulse_error("inbox", e)

    items.sort(key=lambda x: (_sev_rank(x["severity"]), -(x.get("since") or 0)))
    return items, errors


def _log_pulse_error(source: str, e: Exception) -> None:
    """Log lỗi nguồn nhưng không vỡ feed. Print thay logging vì main.py dùng print."""
    try:
        print(f"[joyce-today] nguồn '{source}' lỗi: {e}")
    except Exception:
        pass


def _today_bounds() -> tuple:
    """Mốc đầu/cuối hôm nay theo giờ hệ thống (server đã theo múi giờ cấu hình)."""
    import datetime as _dt
    now = _dt.datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return start, start + 86400


def _schedule_today(deps: TodayDeps, brains: list) -> list:
    """Gom nhắc hẹn pending của MỌI brain đến hạn trong hôm nay (lịch của Joyce)."""
    start, end = _today_bounds()
    out = []
    for b in brains:
        try:
            rems = (deps.reminders_load(b) or {}).get("reminders") or []
        except Exception:
            continue
        for r in rems:
            due = float(r.get("due_at") or 0)
            if r.get("status") == "pending" and start <= due < end:
                out.append({
                    "time": time.strftime("%H:%M", time.localtime(due)),
                    "due_at": due,
                    "title": r.get("text") or r.get("label") or "(nhắc hẹn)",
                    "meta": r.get("label") or "",
                    "brain": b,
                })
    out.sort(key=lambda x: x["due_at"])
    return out[:12]


def _brief(counts: dict) -> dict:
    """Morning brief DETERMINISTIC từ số đếm - nhanh, đáng tin, không tốn token.
    Bản LLM-viết-có-hồn nằm ở phase sau (cần aux model + cache)."""
    parts = []
    if counts["blocked"]:
        parts.append(f"{counts['blocked']} việc đang bị kẹt")
    if counts["review"]:
        parts.append(f"{counts['review']} việc chờ duyệt")
    if counts["apps_down"]:
        parts.append(f"{counts['apps_down']} ứng dụng H2O không phản hồi")
    if counts["connectors_down"]:
        parts.append(f"{counts['connectors_down']} kết nối lỗi")
    if counts["unread"]:
        parts.append(f"{counts['unread']} kết quả nền chưa đọc")
    n = len(parts)
    title = f"{n} nhóm việc cần chú ý hôm nay" if n else "Mọi thứ đang vận hành ổn"
    return {"count": n, "title": title,
            "text": "Có " + ", ".join(parts) + "." if parts else
                    "Không có cảnh báo nào - Joyce canh hệ thống ổn định."}


def register(app, deps: TodayDeps):
    router = APIRouter()

    @router.get("/api/joyce/v1/pulse")
    async def api_pulse(brain: str = Query("brain")):
        apps = await _ping_projects(deps)
        items, errors = _pulse(deps, brain, apps)
        sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for it in items:
            sev[it["severity"]] = sev.get(it["severity"], 0) + 1
        # Số chờ duyệt luôn trả về (kể cả khi chưa quá 4h để lên pulse) - rail badge
        # đếm theo con số này, không theo pulse item.
        try:
            approvals = len((deps.board_view(brain) or {}).get("columns", {}).get("review") or [])
        except Exception:
            approvals = 0
        return {"ok": True, "pulse": items, "counts": sev, "total": len(items),
                "approvals": approvals,
                "partial": bool(errors), "sources_down": errors}

    @router.get("/api/joyce/v1/today")
    async def api_today(request: Request, brain: str = Query("brain")):
        try:
            view = deps.board_view(brain) or {}
        except Exception as e:
            _log_pulse_error("kanban/today", e)
            view = {}
        cols = view.get("columns") or {}
        counts = view.get("counts") or {}
        brains = deps.brain_names() or []
        apps = await _ping_projects(deps)
        pulse, src_down = _pulse(deps, brain, apps)
        try:
            unread = int(deps.inbox_unread() or 0)
        except Exception as e:
            _log_pulse_error("inbox/today", e)
            unread = 0
        pending_rems = []
        for b in brains:
            try:
                pending_rems += [r for r in (deps.reminders_load(b) or {}).get("reminders", [])
                                 if r.get("status") == "pending"]
            except Exception:
                pass

        # Ai đang xem: nhân viên -> tên nhân viên; admin -> tên workspace
        try:
            staff = deps.staff_by_cookie(request.cookies.get("h2o_staff", "")) or {}
        except Exception:
            staff = {}
        viewer = staff.get("name") or (deps.read_settings().get("workspace_name") or "H2O")

        # Task ưu tiên: kẹt/chờ duyệt lên đầu, rồi hàng chờ, rồi đang chạy - theo priority
        pri = (cols.get("blocked") or []) + (cols.get("review") or []) \
            + (cols.get("ready") or []) + (cols.get("todo") or []) \
            + (cols.get("running") or [])
        pri.sort(key=lambda t: (int(t.get("priority") or 2), float(t.get("created_at") or 0)))
        tasks = [{
            "id": t.get("id"), "title": t.get("title"), "status": t.get("status"),
            "priority": t.get("priority"), "needs_approval": bool(t.get("needs_approval")),
            "meta": (t.get("block_reason") or t.get("route") or "")[:100],
        } for t in pri[:8]]

        online = sum(1 for a in apps if a.get("ok"))
        try:
            conn_down = sum(1 for r in (deps.connect_snapshot() or {}).values() if r.get("ok") is False)
        except Exception as e:
            _log_pulse_error("connectors/today", e)
            conn_down = 0
        start, end = _today_bounds()
        today_rems = _schedule_today(deps, brains)
        brief = _brief({
            "blocked": int(counts.get("blocked", 0)),
            "review": int(counts.get("review", 0)),
            "apps_down": sum(1 for a in apps if a.get("ok") is False),
            "connectors_down": conn_down,
            "unread": unread,
        })

        metrics = [
            {"key": "running", "label": "Đang chạy", "value": counts.get("running", 0), "tone": "blue"},
            {"key": "review", "label": "Chờ duyệt", "value": counts.get("review", 0), "tone": "amber"},
            {"key": "done24", "label": "Xong 24h", "value": view.get("completed_24h", 0), "tone": "green"},
            {"key": "apps", "label": "App online", "value": f"{online}/{len(apps)}", "tone": "cyan"},
            {"key": "reminders", "label": "Hẹn hôm nay", "value": len(today_rems), "tone": "violet"},
            {"key": "unread", "label": "Hộp thư mới", "value": unread, "tone": "pink"},
        ]

        import datetime as _dt
        now = _dt.datetime.now()
        dow = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][now.weekday()]

        return {
            "ok": True,
            "viewer": viewer,
            "staff": bool(staff),
            "date": now.strftime("%d/%m/%Y"),
            "weekday": dow,
            "brain": brain,
            "orchestration": view.get("orchestration"),
            "brief": brief,
            "metrics": metrics,
            "tasks": tasks,
            "schedule": today_rems,
            "pulse": pulse,
            "apps": [{"id": a.get("id"), "name": a.get("ten"), "url": a.get("url"),
                      "ok": a.get("ok"), "ms": a.get("ms")} for a in apps],
            "approvals_pending": int(counts.get("review", 0)),
            "inbox_unread": unread,
            "reminders_pending": len(pending_rems),
            "partial": bool(src_down), "sources_down": src_down,
            # Spec Phase 2: mọi card có source label + last_synced_at khi phù hợp.
            # Client hiện "Cập nhật HH:MM" từ đây - không tự lấy giờ trình duyệt vì
            # dữ liệu phản ánh mốc SERVER đọc store, không phải mốc render.
            "generated_at": now.timestamp(),
            "sources": {"metrics": "kanban+h2o+inbox", "tasks": "kanban",
                        "schedule": "reminders", "pulse": "pulse", "apps": "h2o_projects"},
        }

    # ---- Contract v1 (Phase 3-lite): hành động/đọc chuẩn qua adapter ---------------
    # Staff: giữ đúng rào của /kanban - đọc được (xem việc chung), GHI bị 403.
    # Approve/reject là hành động nhạy cảm nên v1 cũng chặn staff tại đây thay vì
    # nhờ deny-list (đường /api/joyce/* không nằm trong _STAFF_DENY).
    def _staff_of(deps, request) -> dict:
        try:
            return deps.staff_by_cookie(request.cookies.get("h2o_staff", "")) or {}
        except Exception:
            return {}

    @router.get("/api/joyce/v1/tasks")
    async def api_tasks(brain: str = Query("brain")):
        try:
            view = deps.board_view(brain) or {}
        except Exception as e:
            _log_pulse_error("tasks", e)
            return {"ok": False, "error": "kanban lỗi", "columns": {}, "counts": {}}
        return {"ok": True, "columns": view.get("columns") or {},
                "counts": view.get("counts") or {},
                "orchestration": view.get("orchestration")}

    @router.get("/api/joyce/v1/approvals")
    async def api_approvals(brain: str = Query("brain")):
        now = time.time()
        try:
            review = (deps.board_view(brain) or {}).get("columns", {}).get("review") or []
        except Exception as e:
            _log_pulse_error("approvals", e)
            return {"ok": False, "error": "kanban lỗi", "items": [], "total": 0}
        items = [{
            "id": t.get("id"), "title": t.get("title"), "priority": t.get("priority"),
            "meta": (t.get("block_reason") or t.get("route") or "")[:120],
            "since": t.get("updated_at") or t.get("created_at"),
            "stale": bool(now - float(t.get("updated_at") or t.get("created_at") or now) > _REVIEW_STALE_SEC),
        } for t in review]
        items.sort(key=lambda x: float(x["since"] or 0))
        return {"ok": True, "items": items, "total": len(items),
                "stale_after_sec": _REVIEW_STALE_SEC}

    async def _approval_act(deps, request, tid, status, brain, reason):
        if _staff_of(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        if not deps.task_move:
            return JSONResponse({"ok": False, "error": "task_move chưa được tiêm"}, status_code=500)
        return await deps.task_move(tid, status, brain, reason)

    @router.post("/api/joyce/v1/approvals/{tid}/approve")
    async def api_approve(tid: str, request: Request, comment: str = Form(""),
                          brain: str = Form("brain")):
        return await _approval_act(deps, request, tid, "done", brain, comment or "approved")

    @router.post("/api/joyce/v1/approvals/{tid}/reject")
    async def api_reject(tid: str, request: Request, comment: str = Form(""),
                         brain: str = Form("brain")):
        # Từ chối = trả về hàng chờ (todo) để chỉnh/triage lại - khớp nút "Yêu cầu sửa"
        # của UI, không phải blocked (blocked báo là task KẸT, sai nghĩa).
        return await _approval_act(deps, request, tid, "todo", brain, comment or "requested changes")

    @router.get("/api/joyce/v1/context/task/{tid}")
    async def api_ctx_task(tid: str, brain: str = Query("brain")):
        if not deps.task_get:
            return JSONResponse({"ok": False, "error": "task_get chưa được tiêm"}, status_code=500)
        data = deps.task_get(tid, brain)
        if not data:
            return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
        return {"ok": True, **data}

    @router.get("/api/joyce/v1/agents")
    async def api_agents(brain: str = Query("brain")):
        if not deps.agents_list:
            return JSONResponse({"ok": False, "error": "agents_list chưa được tiêm"}, status_code=500)
        try:
            return {"ok": True, "agents": deps.agents_list(brain)}
        except Exception as e:
            _log_pulse_error("agents", e)
            return {"ok": False, "error": "không đọc được danh sách agent"}

    # ---- Brief viết bằng aux model ----------------------------------------------------
    # Trang Hôm nay render ngay bằng brief deterministic rồi gọi endpoint này SAU: aux
    # model có thể chậm/chết, không bao giờ được làm trang chờ. Cache theo chữ ký số liệu:
    # số không đổi thì trả lại câu cũ, tiết kiệm token và giữ brief ổn định khi F5. Aux
    # lỗi/trống → fallback=True với brief deterministic, UI giữ nguyên câu cũ.

    def _counts_now() -> dict:
        try:
            view = deps.board_view("brain") or {}
        except Exception:
            view = {}
        c = dict(view.get("counts") or {})
        cols = view.get("columns") or {}
        c["approvals"] = len(cols.get("review", []) or [])
        c["top"] = [(t.get("title") or "")[:60] for col in ("ready", "running")
                    for t in (cols.get(col) or []) if t.get("title")][:5]
        return c

    @router.get("/api/joyce/v1/brief-ai")
    async def api_brief_ai(brain: str = Query("brain")):
        try:
            pulse_items, _ = _build_pulse()
        except Exception:
            pulse_items = []
        counts = _counts_now()
        try:
            apps = _ping_cache["items"] or []   # chỉ cache - không ping mạng ở đây
            conn_down = sum(1 for r in (deps.connect_snapshot() or {}).values()
                            if r.get("ok") is False)
            unread = deps.inbox_unread()
        except Exception:
            apps, conn_down, unread = [], 0, 0
        base = _brief({
            "blocked": int(counts.get("blocked", 0)),
            "review": int(counts.get("approvals", counts.get("review", 0))),
            "apps_down": sum(1 for a in apps if a.get("ok") is False),
            "connectors_down": conn_down,
            "unread": unread,
        })
        if not deps.brief_ai:
            return {"ok": False, "fallback": True, "brief": base}
        sig = "|".join([
            brain, time.strftime("%Y-%m-%d"),
            ":".join(f"{k}={v}" for k, v in sorted(counts.items()) if k != "top"),
            ";".join(counts.get("top") or []),
            ";".join(str(p.get("title") or "")[:50] for p in pulse_items[:4]),
        ])
        if _brief_cache["key"] == sig and time.time() - _brief_cache["ts"] < _BRIEF_TTL:
            return {"ok": True, "fallback": False, "brief": _brief_cache["text"],
                    "title": base.get("title"), "cached": True}
        tops = " · ".join(t for t in (counts.get("top") or []) if t) or "chưa có"
        pulse_txt = " · ".join(str(p.get("title") or "") for p in pulse_items[:4]) or "không có"
        prompt = (f"Viết lời chào ngắn của trợ lý Joyce cho chủ, 1 tới 2 câu tiếng Việt, giọng "
                  f"ấm áp - chủ động - kiểm soát, không emoji, không dẫn dòng, tối đa 220 ký tự. "
                  f"Dữ liệu: kẹt {counts.get('blocked', 0)}, chờ duyệt {counts.get('approvals', 0)}, "
                  f"chờ chạy {counts.get('ready', 0)}, đang chạy {counts.get('running', 0)}, "
                  f"việc ưu tiên: {tops}. Cảnh báo: {pulse_txt}. "
                  f"Kết thúc bằng 1 gợi ý hành động đầu tiên cụ thể nếu có việc kẹt/cảnh báo.")
        try:
            async with _brief_lock:
                if (_brief_cache["key"] == sig
                        and time.time() - _brief_cache["ts"] < _BRIEF_TTL):
                    return {"ok": True, "fallback": False, "brief": _brief_cache["text"],
                            "title": base.get("title"), "cached": True}
                txt = await deps.brief_ai(prompt)
                txt = " ".join(str(txt or "").split())
                if len(txt) < 8:
                    raise RuntimeError("aux trả rỗng")
                _brief_cache.update({"key": sig, "text": txt[:500], "ts": time.time()})
                return {"ok": True, "fallback": False, "brief": txt[:500],
                        "title": base.get("title"), "cached": False}
        except Exception as e:  # noqa: BLE001 - aux chết/thiếu/chậm: giữ brief deterministic
            print(f"[joyce-today] brief-ai lỗi, dùng fallback: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return {"ok": False, "fallback": True, "brief": base}

    # ---- Tìm kiếm tri thức -------------------------------------------------------------
    # Bọc `/files/search` (đi qua _brain_root an toàn + threadpool), KHÔNG store mới. Staff
    # bị chặn /files/* nên v1 này cũng chặn staff chủ động - /api/joyce/* không nằm trong
    # deny-list nên phải tự kiểm, không được trông chờ middleware.
    @router.get("/api/joyce/v1/knowledge/search")
    async def api_knowledge_search(request: Request, q: str = Query(""),
                                   brain: str = Query("brain"),
                                   limit: int = Query(30, le=100, ge=1)):
        if _staff_of(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        q = (q or "").strip()
        if not q:
            return {"items": [], "q": q}
        if not deps.knowledge_search:
            return {"items": [], "q": q, "ok": False, "note": "search chưa cấu hình"}
        try:
            res = deps.knowledge_search(brain, q, limit)
            if asyncio.iscoroutine(res):
                res = await res
            items = (res or {}).get("items") or []
            for it in items:
                it["source"] = "vault"
            return {"items": items, "q": q, "count": len(items)}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] knowledge search lỗi: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return {"items": [], "q": q, "ok": False}

    # ---- Threads (phiên chat) ------------------------------------------------------------
    # Bọc `sessions_list`: dep nhận request để chính nó áp scope staff (kênh staff:<id>),
    # Joyce không tự chế lại logic lọc. POST tạo phiên web/staff - kênh cộng sự
    # (agent:/workflow:/coding:) vẫn đi qua `/sessions/new` cũ.
    @router.get("/api/joyce/v1/chat/threads")
    async def api_threads(request: Request, brain: str = Query("brain"),
                          limit: int = Query(50, le=200, ge=1)):
        if not deps.threads_list:
            return {"sessions": [], "ok": False}
        try:
            res = deps.threads_list(request, brain, limit)
            return {"sessions": (res or {}).get("sessions") or []}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] threads lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            return {"sessions": [], "ok": False}

    @router.post("/api/joyce/v1/chat/threads")
    async def api_thread_new(request: Request, brain: str = Form("brain")):
        if not deps.thread_create:
            return {"ok": False, "error": "chưa cấu hình"}
        try:
            return deps.thread_create(request, brain)
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] thread new lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            return JSONResponse({"ok": False, "error": "tạo phiên lỗi"}, status_code=500)

    # ---- Commands (whitelist, không shell) ----------------------------------------------
    # Bản đồ lệnh cố định nằm ở deps.run_command trong main.py ("kanban.nudge",
    # "pulse.refresh"...). Không nhận lệnh tuỳ ý: đây là cổng hành động kiểm soát cho
    # palette/Telegram sau này, không phải shell. Staff bị chặn toàn bộ.
    @router.post("/api/joyce/v1/commands")
    async def api_commands(request: Request, cmd: str = Form(...),
                           brain: str = Form("brain")):
        if _staff_of(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        if not deps.run_command:
            return {"ok": False, "error": "commands chưa cấu hình"}
        name = (cmd or "").strip()
        try:
            res = deps.run_command(name, brain)
            if asyncio.iscoroutine(res):
                res = await res
            if res is None:
                return JSONResponse({"ok": False, "error": f"lệnh '{name}' không có"},
                                    status_code=404)
            return {"ok": True, "cmd": name, "result": res}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] command '{name}' lỗi: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return JSONResponse({"ok": False, "cmd": name, "error": str(e)[:200]},
                                status_code=500)

    # ---- Learning proposals --------------------------------------------------------------
    # Bọc hàng chờ review của learn.py (commit học trong git brain + undo 1-click). KHÔNG
    # tạo store proposal mới - learn.py đã có /learn/review + /learn/undo, v1 chỉ đặt tên
    # chuẩn cho contract. Undo = ghi (git revert) nên staff bị chặn; đọc danh sách thì mở.
    @router.get("/api/joyce/v1/learning-proposals")
    async def api_learn_review(request: Request, brain: str = Query("brain"),
                               limit: int = Query(20, le=200, ge=1)):
        if not deps.learn_review:
            return {"items": [], "git_repo": False, "ok": False}
        try:
            res = deps.learn_review(brain, limit)
            if asyncio.iscoroutine(res):
                res = await res
            res = res or {}
            return {"ok": True, "git_repo": bool(res.get("git_repo")),
                    "items": res.get("commits") or []}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] learning-proposals lỗi: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return {"items": [], "git_repo": False, "ok": False}

    @router.post("/api/joyce/v1/learning-proposals/undo")
    async def api_learn_undo(request: Request, brain: str = Form("brain")):
        if _staff_of(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        if not deps.learn_undo:
            return JSONResponse({"ok": False, "error": "chưa cấu hình"}, status_code=500)
        try:
            res = deps.learn_undo(brain)
            if asyncio.iscoroutine(res):
                res = await res
            return res or {"ok": False}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] learning undo lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            return JSONResponse({"ok": False, "error": str(e)[:160]}, status_code=500)

    @router.post("/api/joyce/v1/learning-proposals")
    async def api_learn_propose(request: Request, text: str = Form(...),
                                brain: str = Form("brain")):
        """Đẩy một ghi chú vào hàng học của learn.py. Đây chỉ là NGUYÊN LIỆU - learn
        vẫn qua pipeline riêng (curator + duyệt), không phải ghi thẳng vào wiki.
        Staff bị chặn như mọi write khác."""
        if _staff_of(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        if not deps.learn_enqueue:
            return JSONResponse({"ok": False, "error": "chưa cấu hình"}, status_code=500)
        txt = (text or "").strip()
        if len(txt) < 20:
            return JSONResponse({"ok": False, "error": "quá ngắn để học"}, status_code=400)
        try:
            res = deps.learn_enqueue(brain, "", txt[:4000], "")
            if asyncio.iscoroutine(res):
                await res
            return {"ok": True, "queued": True}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] learn propose lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            return JSONResponse({"ok": False, "error": str(e)[:160]}, status_code=500)

    # ---- Agent runs ---------------------------------------------------------------------
    # Giao việc cho đội ngũ = enqueue task kanban (đúng đường /kanban/task POST đang dùng,
    # qua dep task_enqueue). Spec gọi "agent-runs" nhưng thực chất là một task có route/
    # capability - Joyce không tạo runtime thứ hai. Staff bị chặn như write /kanban.
    @router.post("/api/joyce/v1/agent-runs")
    async def api_agent_runs(request: Request, title: str = Form(...),
                             intent: str = Form(""), brain: str = Form("brain"),
                             needs_approval: bool = Form(False),
                             chat_id: str = Form(""),
                             idempotency_key: str = Form("")):
        if _staff_of(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        if not deps.task_enqueue:
            return JSONResponse({"ok": False, "error": "chưa cấu hình"}, status_code=500)
        t = (title or "").strip()
        if not t:
            return JSONResponse({"ok": False, "error": "thiếu title"}, status_code=400)
        try:
            res = deps.task_enqueue(brain, t[:500], (intent or "")[:4000],
                                    needs_approval=bool(needs_approval),
                                    created_by="api:v1", chat_id=(chat_id or "")[:120],
                                    idempotency_key=(idempotency_key or "")[:120])
            if asyncio.iscoroutine(res):
                res = await res
            return {"ok": True, "task_id": res, "queued": True}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] agent-run lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            return JSONResponse({"ok": False, "error": str(e)[:160]}, status_code=500)

    # ---- Context drawer tổng quát ---------------------------------------------------------
    # Spec: /context/:type/:id cho Customer/Lead/WeddingProject/Student/Campaign/Task.
    # Joyce = Experience Layer: chỉ "task" có nguồn nội bộ (kanban). Các type còn lại là
    # đối tượng domain của H2O Legacy - trả 404 với danh sách type hỗ trợ thay vì vẽ mock.
    _CONTEXT_TYPES = ("task",)

    @router.get("/api/joyce/v1/context/{ctype}/{cid}")
    async def api_context(ctype: str, cid: str, brain: str = Query("brain")):
        ctype = (ctype or "").strip().lower()
        if ctype not in _CONTEXT_TYPES:
            return JSONResponse({"ok": False, "error": f"type '{ctype}' không có adapter",
                                 "supported": list(_CONTEXT_TYPES)}, status_code=404)
        if not deps.task_get:
            return JSONResponse({"ok": False, "error": "task_get chưa được tiêm"},
                                status_code=500)
        data = deps.task_get(cid, brain)
        if not data:
            return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
        return {"ok": True, "type": ctype, **data}

    # ---- Chat thread messages --------------------------------------------------------------
    # Append tin user vào phiên (scope kiểm: staff chỉ được phiên kênh của mình). Reply vẫn
    # stream qua /chat với session id này - v1 không tự chạy engine (tránh nhân đôi tin khi
    # /chat cũng append user message). Endpoint phục vụ seeding thread từ client khác.
    @router.post("/api/joyce/v1/chat/threads/{sid}/messages")
    async def api_thread_msg(sid: str, request: Request, content: str = Form(...)):
        st = _staff_of(deps, request)
        if not deps.session_get or not deps.thread_append:
            return JSONResponse({"ok": False, "error": "chưa cấu hình"}, status_code=500)
        sess = deps.session_get(sid)
        if not sess:
            return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
        if st:
            chan = (sess.get("channel") or "")
            mine = deps.staff_channel(st) if deps.staff_channel else ""
            if mine and chan != mine:
                return JSONResponse({"ok": False, "error": "không phải phiên của bạn"},
                                    status_code=403)
        txt = (content or "").strip()
        if not txt:
            return JSONResponse({"ok": False, "error": "content rỗng"}, status_code=400)
        try:
            res = deps.thread_append(sid, "user", txt[:8000])
            if asyncio.iscoroutine(res):
                res = await res
            return {"ok": True, "message_id": res,
                    "note": "trả lời stream qua /chat với session này"}
        except Exception as e:  # noqa: BLE001
            print(f"[joyce-today] thread msg lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            return JSONResponse({"ok": False, "error": str(e)[:160]}, status_code=500)

    # ---- Integration Center (Phase 5, mặt máy đọc) -----------------------------------------
    # Một điểm đọc tổng hợp "sức khoẻ kết nối" cho dashboard/client khác: connector MCP
    # (redacted, không secrets) + health, engines (bộ não), app H2O (cache ping), bot kênh.
    # UI trang Kết nối vẫn như cũ - đây là contract v1 tương thích, KHÔNG di chuyển route.
    @router.get("/api/joyce/v1/integrations")
    async def api_integrations(brain: str = Query("brain")):
        out = {"ok": True, "connectors": [], "engines": [], "apps": [], "bots": []}
        try:
            health = deps.connect_snapshot() or {}
            for c in (deps.conns_list() if deps.conns_list else []):
                cid = str(c.get("id") or "")
                h = health.get(cid) or {}
                out["connectors"].append({
                    "id": cid, "label": c.get("label") or c.get("name") or cid,
                    "connector_id": c.get("connector_id"), "transport": c.get("transport"),
                    "enabled": bool(c.get("enabled")), "perm": c.get("perm") or "full",
                    "ok": h.get("ok"), "message": h.get("message") or "",
                    "checked_at": h.get("ts"), "href": "mcp",
                })
        except Exception as e:
            _log_pulse_error("integrations/conns", e)
        try:
            for name, r in (deps.engines_health() or {}).items():
                out["engines"].append({"name": name, "ok": bool(r.get("ok")),
                                       "message": r.get("message") or "",
                                       "since": r.get("ts"), "href": "models"})
        except Exception as e:
            _log_pulse_error("integrations/engines", e)
        try:
            for a in (await _ping_projects(deps)):
                out["apps"].append({"id": a.get("id"), "name": a.get("name"),
                                    "ok": bool(a.get("ok")), "ms": a.get("ms"),
                                    "url": a.get("url"), "href": "projects"})
        except Exception as e:
            _log_pulse_error("integrations/apps", e)
        try:
            for b in (deps.bots_list() if deps.bots_list else []):
                out["bots"].append({"id": b.get("id"), "name": b.get("name") or b.get("label"),
                                    "enabled": bool(b.get("enabled")), "href": "conversations"})
        except Exception as e:
            _log_pulse_error("integrations/bots", e)
        down = sum(1 for c in out["connectors"] if c["enabled"] and c["ok"] is False) \
             + sum(1 for e in out["engines"] if not e["ok"]) \
             + sum(1 for a in out["apps"] if not a["ok"])
        out["summary"] = {"connectors": len(out["connectors"]), "engines": len(out["engines"]),
                          "apps": len(out["apps"]), "bots": len(out["bots"]), "down": down}
        return out

    app.include_router(router)
