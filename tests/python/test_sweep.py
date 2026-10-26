"""Test sweep bù — quét "việc đáng lẽ đã chạy mà lỡ" với deps giả, không cần server.
Chạy: python tests/python/test_sweep.py"""
import asyncio
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "server"))
import sweep  # noqa: E402

PASS = [0]
FAIL = [0]


def t(name, ok, extra=""):
    PASS[0] += 1 if ok else 0
    FAIL[0] += 0 if ok else 1
    print(f"{'✓' if ok else '✗'} {name}{' — ' + extra if extra else ''}")


NOW = time.time()


class FakeReminders:
    def __init__(self, by_brain):
        self.by = by_brain

    def pending_views(self, brain):
        return self.by.get(brain, [])


class FakeTaskStore:
    def __init__(self, by_root):
        self.by = by_root

    def list_tasks(self, root, include_archived=False, limit=500):
        return self.by.get(root, [])


class FakeTasks:
    def __init__(self, by_root):
        self.store = FakeTaskStore(by_root)


class FakeLoops:
    def __init__(self, loops, views):
        self._loops = loops
        self._views = views

    def read_state(self, brain):
        return {}

    def list_loops(self, brain):
        return self._loops.get(brain, [])

    def loop_view(self, brain, lp, st_all=None):
        return self._views.get((brain, lp.get("slug")), {})


def make_deps(*, reminders=None, tasks=None, loops=None, loop_views=None, inbox=None):
    sent = []
    async def _inbox(text, **kw):
        sent.append((text, kw))
    return sweep.SweepDeps(
        brains=lambda: ["brain", "phong-sx"],
        task_root=lambda n: "/root/" + n,
        reminders=reminders or FakeReminders({}),
        tasks=tasks or FakeTasks({}),
        loops=FakeLoops(loops or {}, loop_views or {}),
        inbox=inbox or _inbox,
    ), sent


# ── 1. Brain sạch → không báo gì ─────────────────────────────────────────────
deps, sent = make_deps()
rep = asyncio.run(sweep.run_sweep(deps))
t("brain sạch → found=False, không gửi thư", rep["found"] is False and not sent)

# ── 2. Nhắc hẹn trễ quá grace → vào báo cáo + digest ────────────────────────
deps, sent = make_deps(reminders=FakeReminders({
    "brain": [{"id": "r1", "text": "họp team", "due_at": NOW - 7200, "status": "pending"}],
}))
rep = asyncio.run(sweep.run_sweep(deps))
t("nhắc trễ 2h → found + 1 late_reminder", rep["found"] and rep["brains"][0]["late_reminders"] == 1)
t("digest gửi đúng 1 thư có dedup theo giờ", len(sent) == 1 and sent[0][1].get("dedup", "").startswith("sweep:"))
t("digest kể tên brain + việc", "brain" in sent[0][0] and "họp team" in sent[0][0])

# ── 3. Nhắc trễ < grace → không tính ─────────────────────────────────────────
deps, sent = make_deps(reminders=FakeReminders({
    "brain": [{"id": "r2", "text": "gần hạn", "due_at": NOW - 60, "status": "pending"}],
}))
rep = asyncio.run(sweep.run_sweep(deps))
t("nhắc trễ 1 phút (< grace) → không tính", rep["found"] is False and not sent)

# ── 4. Task running kẹt (claim hết hạn) + ready hoãn quá hạn ──────────────────
deps, sent = make_deps(tasks=FakeTasks({
    "/root/phong-sx": [
        {"id": "t1", "title": "render video", "status": "running", "claim_expires_at": NOW - 3600},
        {"id": "t2", "title": "đợi gói mở", "status": "ready", "not_before": NOW - 7200},
        {"id": "t3", "title": "worker sống", "status": "running", "claim_expires_at": NOW + 3600},
        {"id": "t4", "title": "bình thường", "status": "ready", "not_before": 0},
    ],
}))
rep = asyncio.run(sweep.run_sweep(deps))
b = rep["brains"][0]
t("task kẹt running → stuck_tasks=1", b["stuck_tasks"] == 1)
t("task ready quá not_before → deferred=1", b["deferred_tasks"] == 1)

# ── 5. Loop bật mà next_run quá hạn nhiều → lỡ nhịp ──────────────────────────
deps, sent = make_deps(
    loops={"brain": [{"slug": "bao-cao", "title": "Báo cáo sáng", "enabled": True, "interval_min": 60}]},
    loop_views={("brain", "bao-cao"): {"next_run": NOW - 5400, "auto_paused_reason": "", "running": False}},
)
rep = asyncio.run(sweep.run_sweep(deps))
t("loop lỡ 1.5h → overdue_loops=1", rep["found"] and rep["brains"][0]["overdue_loops"] == 1)

# ── 6. Loop bị auto-pause / đang chạy → không tính ────────────────────────────
deps, sent = make_deps(
    loops={"brain": [{"slug": "l1", "title": "L1", "enabled": True, "interval_min": 60}]},
    loop_views={("brain", "l1"): {"next_run": NOW - 99999, "auto_paused_reason": "fail nhiều", "running": False}},
)
rep = asyncio.run(sweep.run_sweep(deps))
t("loop auto-paused → không tính lỡ", rep["found"] is False)

# ── 7. notify=False → vẫn báo cáo nhưng không gửi thư ─────────────────────────
deps, sent = make_deps(reminders=FakeReminders({
    "brain": [{"id": "r9", "text": "trễ", "due_at": NOW - 4000, "status": "pending"}],
}))
rep = asyncio.run(sweep.run_sweep(deps, notify=False))
t("notify=False → báo cáo có, thư không", rep["found"] is True and not sent)

# ── 8. Một brain scan lỗi → sweep vẫn xong các brain khác ─────────────────────
class BadReminders:
    def pending_views(self, brain):
        raise RuntimeError("disk lỗi")

deps, sent = make_deps(reminders=BadReminders(), tasks=FakeTasks({
    "/root/phong-sx": [{"id": "tx", "title": "kẹt", "status": "running", "claim_expires_at": NOW - 4000}],
}))
rep = asyncio.run(sweep.run_sweep(deps))
t("một nguồn lỗi không làm chết sweep", rep["found"] is True and rep["brains"][0]["stuck_tasks"] == 1)

print(f"\n{PASS[0]} pass · {FAIL[0]} fail")
sys.exit(1 if FAIL[0] else 0)
