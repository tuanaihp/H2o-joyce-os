"""Sweep bù - port ý tưởng `missingPostWorkflow` của Postiz sang Joyce.

Postiz chạy một workflow quét giờ: tìm bài QUEUE đã quá `publishDate` mà timer
durable không nhặt được (worker sập, workflow chết) rồi `signalWithStart` đẩy
chạy lại. Bản chất: hệ thống tự hỏi "có việc nào ĐÁNG LẼ đã xảy ra mà chưa?".

Joyce đã tự chữa từng phần (nhắc hẹn trễ tự bắn ở tick sau, Kanban running kẹt
được `reclaim_stale` thu hồi, loop quá hạn được `_pick_due` chọn, việc hoãn vì
hết hạn mức quay lại sau `not_before`). Cái thiếu là TẦNG NHÌN: khi máy tắt nửa
ngày hoặc một mắt xích chết ngầm, người dùng không biết đã lỡ gì.

Module này quét mọi brain mỗi SWEEP_INTERVAL_SECONDS, tổng hợp các khoản "đáng lẽ
đã chạy mà chưa/chạy trễ", rồi bỏ MỘT mẩu thư digest vào hòm thư (dedup theo giờ
để không spam). Không tự sửa gì - sửa là việc của từng bộ phận đã có; sweep chỉ
làm việc bỏ lỡ không bao giờ lặng lẽ.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

SWEEP_INTERVAL_SECONDS = 3600          # mỗi giờ quét một lần, như Postiz
LATE_GRACE_SECONDS = 15 * 60           # nhắc hẹn/loop trễ dưới 15p coi như bình thường
LOOP_OVERDUE_FACTOR = 2.0              # loop quá hạn > 2× chu kỳ mới tính là "lỡ"


@dataclass
class SweepDeps:
    """Những gì sweep cần mượn từ main.py - inject để test được và không vòng import."""
    brains: Callable[[], list]                       # → list TÊN brain (scheduler_brains)
    task_root: Callable[[str], str]                  # tên brain → đường dẫn gốc cho TaskStore
    reminders: object                                # reminders_feature (pending_views)
    tasks: object                                    # tasks_feature (.store.list_tasks)
    loops: object                                    # loop_feature (list_loops + loop_view + read_state)
    inbox: Callable                                  # (text, {kind,label,source,dedup}) → thư digest


@dataclass
class BrainSweep:
    brain: str
    late_reminders: list = field(default_factory=list)     # [{id,text,due_at,late_min}]
    stuck_tasks: list = field(default_factory=list)        # running kẹt, chờ reclaim
    deferred_tasks: list = field(default_factory=list)     # ready nhưng not_before đã qua mà chưa nhặt
    overdue_loops: list = field(default_factory=list)      # [{slug,last_run,overdue_min}]
    capacity: dict = field(default_factory=dict)           # throughput/hàng chờ/tỷ lệ blocked

    @property
    def count(self) -> int:
        return (len(self.late_reminders) + len(self.stuck_tasks)
                + len(self.deferred_tasks) + len(self.overdue_loops))


def _scan_brain(deps: SweepDeps, name: str, now: float) -> BrainSweep:
    out = BrainSweep(brain=name)

    # 1) Nhắc hẹn pending đã quá hạn - tick sẽ bắn bù nhưng sweep ghi nhận độ trễ.
    try:
        for r in deps.reminders.pending_views(name) or []:
            due = float(r.get("due_at") or 0)
            if due and due <= now - LATE_GRACE_SECONDS:
                out.late_reminders.append({
                    "id": r.get("id"), "text": str(r.get("text") or r.get("label") or "")[:80],
                    "due_at": due, "late_min": int((now - due) / 60),
                })
    except Exception as e:  # noqa: BLE001 - quét đừng làm chết sweep
        print(f"[sweep] reminders {name}: {type(e).__name__}: {e}", file=sys.stderr)

    # 2) Kanban: task 'running' mà claim hết hạn (worker chết ngầm - reclaim sẽ cứu)
    #    + task 'ready/todo' treo not_before quá hạn mà dispatcher chưa nhặt.
    #    Kèm capacity digest (OpenAI: load hệ tăng 10x mới thấy bottleneck - đo
    #    throughput/chờ queue/tỷ lệ blocked để thấy TRƯỚC khi hàng vỡ).
    try:
        root = deps.task_root(name)
        done_24h = done_7d = 0
        queue_wait_min = 0.0
        oldest_ready = 0.0
        blocked_n = review_n = active_n = 0
        for t in deps.tasks.store.list_tasks(root, include_archived=False) or []:
            st = t.get("status")
            upd = float(t.get("updated_at") or 0)
            if st == "running":
                active_n += 1
                exp = float(t.get("claim_expires_at") or 0)
                if exp and exp < now - LATE_GRACE_SECONDS:
                    out.stuck_tasks.append({"id": t.get("id"), "title": str(t.get("title") or "")[:80],
                                            "late_min": int((now - exp) / 60)})
            elif st in ("ready", "todo"):
                active_n += 1
                nb = float(t.get("not_before") or 0)
                if nb and nb < now - LATE_GRACE_SECONDS:
                    out.deferred_tasks.append({"id": t.get("id"), "title": str(t.get("title") or "")[:80],
                                               "late_min": int((now - nb) / 60)})
                elif not nb:
                    oldest_ready = max(oldest_ready, now - upd)
            elif st == "done":
                if upd and now - upd <= 86400:
                    done_24h += 1
                if upd and now - upd <= 7 * 86400:
                    done_7d += 1
            elif st == "blocked":
                blocked_n += 1
                active_n += 1
            elif st == "review":
                review_n += 1
                active_n += 1
        if oldest_ready:
            queue_wait_min = round(oldest_ready / 60, 1)
        out.capacity = {
            "done_24h": done_24h, "done_7d": done_7d,
            "blocked": blocked_n, "review": review_n, "active": active_n,
            "queue_wait_min": queue_wait_min,
            "blocked_pct": round(100.0 * blocked_n / active_n, 1) if active_n else 0.0,
        }
    except Exception as e:  # noqa: BLE001
        print(f"[sweep] kanban {name}: {type(e).__name__}: {e}", file=sys.stderr)

    # 3) Loop bật mà next_run đã qua quá lâu - loop này "lỡ nhịp" (auto-pause thì bỏ).
    try:
        st_all = deps.loops.read_state(name)
        for lp in deps.loops.list_loops(name) or []:
            if not lp.get("enabled"):
                continue
            v = deps.loops.loop_view(name, lp, st_all)
            if v.get("auto_paused_reason") or v.get("running"):
                continue
            nxt = float(v.get("next_run") or 0)
            if nxt and nxt < now - LATE_GRACE_SECONDS:
                out.overdue_loops.append({"slug": lp.get("slug"), "title": str(lp.get("title") or lp.get("slug") or "")[:60],
                                          "overdue_min": int((now - nxt) / 60)})
    except Exception as e:  # noqa: BLE001
        print(f"[sweep] loops {name}: {type(e).__name__}: {e}", file=sys.stderr)

    return out


def _fmt_min(m: int) -> str:
    if m < 60:
        return f"{m}p"
    h, mm = divmod(m, 60)
    return f"{h}h{mm:02d}" if h < 24 else f"{m // 1440} ngày"


def digest_text(items: list[BrainSweep], now: float) -> str:
    """Một mẩu digest ngắn gọn - nhóm theo brain, liệt kê loại lỡ."""
    lines = ["🧹 **Sweep bù** - phát hiện việc đáng lẽ đã chạy nhưng bị lỡ:"]
    for b in items:
        lines.append(f"\n**{b.brain}**")
        for r in b.late_reminders[:3]:
            lines.append(f"· ⏰ Nhắc trễ {_fmt_min(r['late_min'])}: {r['text']}")
        for t in b.stuck_tasks[:3]:
            lines.append(f"· 🔧 Việc kẹt 'đang chạy' {_fmt_min(t['late_min'])} (sẽ thu hồi về Sẵn sàng): {t['title']}")
        for t in b.deferred_tasks[:3]:
            lines.append(f"· ⏸ Việc hoãn quá hạn {_fmt_min(t['late_min'])} chưa được nhặt: {t['title']}")
        for l in b.overdue_loops[:3]:
            lines.append(f"· 🔁 Loop lỡ nhịp {_fmt_min(l['overdue_min'])}: {l['title']}")
        # Capacity digest: chỉ báo khi hàng đang bị bóp (blocked nhiều / chờ lâu)
        cap = b.capacity or {}
        if cap.get("blocked_pct", 0) >= 30 or cap.get("queue_wait_min", 0) >= 60:
            lines.append(
                f"· 📊 Hàng việc đang nghẽn: {cap.get('active', 0)} việc, "
                f"blocked {cap.get('blocked_pct', 0)}%, chờ lâu nhất "
                f"{_fmt_min(int(cap.get('queue_wait_min', 0)))}, xong 24h qua: "
                f"{cap.get('done_24h', 0)}")
    lines.append("\nCác bộ phận tự chữa vẫn đang chạy - mẩu này chỉ để anh biết có gì đã lỡ. "
                 "Kiểm tra trang **Việc** nếu con số cứ tăng.")
    return "\n".join(lines)


_last_report: dict = {"ts": 0.0}


async def run_sweep(deps: SweepDeps, *, notify: bool = True) -> dict:
    """Quét tất cả brain, trả {now, found, brains:[BrainSweep…]}. Có khoản lỡ thì
    gửi 1 thư digest (dedup theo giờ - sweep mỗi giờ nên tối đa 1 thư/giờ)."""
    now = time.time()
    found: list[BrainSweep] = []
    for name in deps.brains() or []:
        try:
            b = _scan_brain(deps, str(name), now)
            if b.count:
                found.append(b)
        except Exception as e:  # noqa: BLE001
            print(f"[sweep] brain {name}: {type(e).__name__}: {e}", file=sys.stderr)

    report = {"now": now, "found": bool(found), "brains": [
        {"brain": b.brain, "late_reminders": len(b.late_reminders), "stuck_tasks": len(b.stuck_tasks),
         "deferred_tasks": len(b.deferred_tasks), "overdue_loops": len(b.overdue_loops),
         "count": b.count, "capacity": b.capacity} for b in found]}

    if found and notify:
        # Dedup theo giờ: sweep lặp lại cùng khoản lỡ thì không bấm chuông lần nữa.
        hour_key = time.strftime("%Y-%m-%d-%H", time.localtime(now))
        try:
            await deps.inbox(digest_text(found, now),
                             kind="system", label="sweep bù", source="sweep",
                             dedup=f"sweep:{hour_key}:{sum(b.count for b in found)}")
        except Exception as e:  # noqa: BLE001
            print(f"[sweep] inbox lỗi: {type(e).__name__}: {e}", file=sys.stderr)
    return report
