"""Test lớp factory (OpenAI agentic factory) - deps giả, không cần server/mạng.
Chạy: python tests/python/test_factory.py"""
import asyncio
import io
import json
import sys
import tempfile
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "server"))
import factory  # noqa: E402

PASS = [0]
FAIL = [0]


def t(name, ok, extra=""):
    PASS[0] += 1 if ok else 0
    FAIL[0] += 0 if ok else 1
    print(f"{'✓' if ok else '✗'} {name}{' - ' + extra if extra else ''}")


NOW = time.time()
TMP = Path(tempfile.mkdtemp(prefix="factory-test-"))


class FakeStore:
    def __init__(self, by_root, events=None):
        self.by = by_root
        self.events = events or {}
        self.moved = []

    def list_tasks(self, root, include_archived=False, limit=500):
        return self.by.get(root, [])

    def list_events_bulk(self, task_ids, limit=20):
        return {tid: self.events.get(tid, []) for tid in task_ids}

    def move(self, task_id, status, reason=""):
        self.moved.append((task_id, status, reason))
        return True


class FakeLoops:
    def read_state(self, brain):
        return {}

    def list_loops(self, brain):
        return [{"slug": "bao-cao", "title": "Báo cáo sáng", "enabled": True}]

    def loop_view(self, brain, lp, st_all=None):
        return {"run_count": 5}


def make_deps(*, tasks=None, enqueued=None, incidents=None, inbox=None, workflows=None):
    sent = []
    calls = enqueued if enqueued is not None else []

    async def _inbox(text, **kw):
        sent.append((text, kw))

    def _enqueue(brain, title, intent, **kw):
        calls.append({"brain": brain, "title": title, "intent": intent, **kw})
        return "tid_" + str(len(calls))

    root_map = {"brain": str(TMP / "brain")}
    (TMP / "brain").mkdir(parents=True, exist_ok=True)
    if workflows is not None:
        wdir = TMP / "brain" / "workflows"
        wdir.mkdir(parents=True, exist_ok=True)
        for w in workflows:
            (wdir / w).write_text("x", encoding="utf-8")

    deps = factory.FactoryDeps(
        brains=lambda: ["brain"],
        task_root=lambda n: root_map.get(n, str(TMP / n)),
        store=tasks or FakeStore({}),
        enqueue=_enqueue,
        loops=FakeLoops(),
        workflows_dir=lambda root: Path(root) / "workflows",
        inbox=inbox or _inbox,
        incidents_list=lambda brain, limit: incidents or [],
        settings_get=lambda: {},
        state_dir=TMP,
        atomic_write_text=None,
    )
    return deps, sent, calls


# ── 1. Low-risk auto: chỉ qua khi risk=low + cap an toàn ─────────────────────
t("risk=low + files → auto", factory.low_risk_auto(
    {"metadata": {"risk": "low"}, "capability": "files"}) is True)
t("risk=low + external-write → KHÔNG auto", factory.low_risk_auto(
    {"metadata": {"risk": "low"}, "capability": "external-write"}) is False)
t("risk=standard → KHÔNG auto", factory.low_risk_auto(
    {"metadata": {"risk": "standard"}, "capability": "files"}) is False)
t("cờ tắt → KHÔNG auto", factory.low_risk_auto(
    {"metadata": {"risk": "low"}, "capability": "files"}, cfg_low_risk_auto=False) is False)

# ── 2. extra_meta whitelist: key lạ bị lọc, key đúng đi qua ──────────────────
em = factory.extra_meta_from(risk="low", post_check="npm test",
                             watch_spec={"checks": [{"type": "file_exists", "path": "a.md"}]})
t("extra_meta giữ risk/post_check/watch_spec",
  em.get("risk") == "low" and em.get("post_check") == ["npm test"]
  and em["watch_spec"]["checks"][0]["type"] == "file_exists")
t("risk lạ bị loại", factory.extra_meta_from(risk="totally-safe").get("risk") is None)

# ── 3. watch_spec sanitize: check lạ bị bỏ, path rỗng bị bỏ ──────────────────
ws = factory.sanitize_watch_spec({"checks": [
    {"type": "file_exists", "path": "a.md"},
    {"type": "exec", "cmd": "rm -rf /"},
    {"type": "file_exists"},
    {"type": "url_ok", "url": "ftp://x"},
    {"type": "url_ok", "url": "https://ok"},
]})
t("watch_spec lọc check lạ", ws and len(ws["checks"]) == 2)
t("watch_spec rỗng → None", factory.sanitize_watch_spec({"checks": []}) is None)

# ── 4. CI babysit: không có post_check → không chạy ──────────────────────────
deps, sent, calls = make_deps()
res = asyncio.run(factory.ci_babysit(
    deps, str(TMP / "brain"),
    {"id": "t1", "title": "v", "status": "done", "brain_root": str(TMP / "brain"),
     "metadata": {}, "capability": "files"}))
t("không post_check → ran=False, không enqueue", res["ran"] is False and not calls)

# ── 5. CI babysit fail → enqueue [CI fix] đúng lượt ──────────────────────────
(TMP / "brain" / "Joyce").mkdir(parents=True, exist_ok=True)
(TMP / "brain" / "Joyce" / "factory.json").write_text(json.dumps({
    "post_check": {"code": ["python -c \"import sys;sys.exit(1)\""]},
    "ci_max_rounds": 2}), encoding="utf-8")
deps, sent, calls = make_deps()
task = {"id": "t9", "title": "sửa code", "status": "done",
        "brain_root": str(TMP / "brain"), "chat_id": "web:x",
        "metadata": {}, "capability": "code"}
res = asyncio.run(factory.ci_babysit(deps, str(TMP / "brain"), task))
t("check đỏ → enqueue [CI fix] vòng 1, idempotent",
  res["ran"] and not res["passed"] and len(calls) == 1
  and calls[0]["idempotency_key"] == "cifix:t9:1"
  and calls[0]["extra_meta"]["ci_round"] == 1)

# ── 6. Vượt max rounds → inbox cảnh báo, KHÔNG enqueue ───────────────────────
deps, sent, calls = make_deps()
task2 = dict(task, id="t10", metadata={"ci_round": 2})
res = asyncio.run(factory.ci_babysit(deps, str(TMP / "brain"), task2))
t("quá max_rounds → không enqueue, chỉ báo chuông",
  res["passed"] is False and not calls and any("CI babysit" in s[0] for s in sent))

# ── 7. Watcher: file_exists OK → state ok + inbox ────────────────────────────
(TMP / "brain" / "out.md").write_text("xong", encoding="utf-8")
deps, sent, calls = make_deps()
wtask = {"id": "w1", "title": "viết báo cáo", "status": "done",
         "brain_root": str(TMP / "brain"), "chat_id": "",
         "metadata": {"watch_spec": {"checks": [{"type": "file_exists", "path": "out.md"}],
                                     "delay_min": 0, "minutes": 60}}}
ok = asyncio.run(factory.watch_register(deps, str(TMP / "brain"), wtask))
rep = asyncio.run(factory.watch_tick(deps))
t("watch đăng ký + file có → state ok", ok and rep["ok"] == 1)
t("watch ok → inbox báo đóng", any("Handhold" in s[0] for s in sent))

# ── 8. Watcher fail → mở lại task MỘT lần + inbox ────────────────────────────
store = FakeStore({})
deps, sent, calls = make_deps(tasks=store)
wtask2 = {"id": "w2", "title": "đăng bài", "status": "done",
          "brain_root": str(TMP / "brain"), "chat_id": "",
          "metadata": {"watch_spec": {"checks": [{"type": "file_exists", "path": "chua-co.md"}],
                                     "delay_min": 0, "minutes": 60}}}
asyncio.run(factory.watch_register(deps, str(TMP / "brain"), wtask2))
rep = asyncio.run(factory.watch_tick(deps))
t("watch fail → reopen về ready", rep["failed"] == 1
  and store.moved and store.moved[0][1] == "ready")
moved0 = len(store.moved)
rep2 = asyncio.run(factory.watch_tick(deps))
t("watch fail chỉ reopen MỘT lần", rep2["failed"] == 0 and len(store.moved) == moved0)

# ── 9. Perf Factory: 2 incident cùng chữ ký → 1 task root-cause, dedup ────────
incidents = [
    {"status": "needs_you", "at": NOW, "last_at": NOW, "count": 1, "source": "kanban",
     "ref": "a1", "brain": "brain", "error": "TimeoutError 192.168.1.5:8080 conn reset"},
    {"status": "needs_you", "at": NOW, "last_at": NOW, "count": 1, "source": "kanban",
     "ref": "a2", "brain": "brain", "error": "TimeoutError 10.0.0.3:9000 conn reset"},
]
deps, sent, calls = make_deps(incidents=incidents)
rep = asyncio.run(factory.pattern_tick(deps))
t("cùng chữ ký ≥2 → enqueue [Perf] root-cause", len(rep["perf"]) == 1
  and calls and calls[0]["title"].startswith("[Perf]"))
calls.clear()
rep2 = asyncio.run(factory.pattern_tick(deps))
t("cooldown 6h → không enqueue trùng", not rep2["perf"] and not calls)

# ── 10. Sevbot: ≥3 cùng chữ ký → bản tin (dedup ngày), không tự hành ─────────
deps, sent, calls = make_deps(incidents=incidents + [
    {"status": "needs_you", "at": NOW, "last_at": NOW, "count": 1, "source": "loop",
     "ref": "a3", "brain": "brain", "error": "TimeoutError 1.2.3.4 conn reset"},
])
rep = asyncio.run(factory.pattern_tick(deps))
t("≥3 cùng chữ ký → Sevbot inbox", len(rep["sev"]) == 1
  and any("Sevbot" in s[0] for s in sent))

# ── 11. Discovery: cùng tiêu đề xong tay ≥3 → gợi ý lặp ─────────────────────
done_same = [{"id": f"d{i}", "title": "Soi tồn kho cuối ngày", "status": "done",
              "created_by": "user", "updated_at": NOW - i * 86400,
              "metadata": {}} for i in (1, 2, 3)]
store = FakeStore({str(TMP / "brain"): done_same})
deps, sent, calls = make_deps(tasks=store)
cur = {"id": "d4", "title": "Soi tồn kho cuối ngày", "status": "done",
       "created_by": "user", "metadata": {}}
ok = asyncio.run(factory.discovery_suggest(deps, str(TMP / "brain"), cur))
t("việc tay lặp ≥3 → gợi ý lặp", ok and any("Gợi ý lặp" in s[0] for s in sent))

# ── 12. Recipes: ghi file gallery có loop + workflow + việc lặp ─────────────
store2 = FakeStore({str(TMP / "brain"): done_same})
deps, sent, calls = make_deps(tasks=store2, workflows=["wf-a.md", "wf-b.md"])
ok = factory.write_recipes(deps, "brain", str(TMP / "brain"))
p = TMP / "brain" / "Joyce" / "recipe-gallery.md"
t("recipe-gallery ghi file đủ phần", ok and p.exists()
  and "bao-cao" in p.read_text(encoding="utf-8")
  and "wf-a" in p.read_text(encoding="utf-8")
  and "soi tồn kho" in p.read_text(encoding="utf-8"))

# ── 13. Chữ ký lỗi chuẩn hoá: khác path/số vẫn một cụm ──────────────────────
s1 = factory._signature("TimeoutError 192.168.1.5:8080 conn reset")
s2 = factory._signature("TimeoutError 10.0.0.3:9000 conn reset")
t("signature gom cùng gốc", s1 == s2 and s1)


def _make_proposal(root, name, *, verdict="win", risk="low", target="agents/x.md",
                   draft=None, status="pending"):
    pdir = Path(root) / "Joyce" / "proposals"
    pdir.mkdir(parents=True, exist_ok=True)
    draft = draft if draft is not None else (
        "---\ntype: agent\nname: X\n---\n# X mới\n" + "nội dung mới đầy đủ. " * 12)
    text = f"""---
type: proposal
target: x
target_file: {target}
status: {status}
verdict: "{verdict}"
risk: {risk}
created: 2026-10-24
---
# Đề xuất
## Bằng chứng
- lặp lỗi
## Sửa đề xuất
- sửa dòng
## Bản nháp đầy đủ
{draft}
## Lượt giám định
WIN
"""
    fp = pdir / name
    fp.write_text(text, encoding="utf-8")
    return fp


# ── 14. Self-improve: WIN + low + có nháp → tự áp, backup có sẵn ────────────
brain1 = TMP / "brain"
(brain1 / "agents").mkdir(parents=True, exist_ok=True)
old_text = "---\ntype: agent\nname: X\n---\n# X cũ\nnội dung cũ\n"
(brain1 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
fp = _make_proposal(str(brain1), "2026-10-24-x.md")
deps, sent, calls = make_deps()
rep = asyncio.run(factory.proposal_tick(deps))
new_text = (brain1 / "agents" / "x.md").read_text(encoding="utf-8")
t("proposal WIN+low+nháp → file được áp",
  rep["applied"] == 1 and "# X mới" in new_text and "nội dung cũ" not in new_text)
t("proposal đổi status applied", "status: applied" in fp.read_text(encoding="utf-8"))
t("backup bản cũ tồn tại",
  any((brain1 / "Joyce" / "proposals" / ".backup").glob("x-*.bak")))

# ── 15. Các cổng an toàn: keep / standard / target ngoài / không nháp ────────
for name, kw, expect_unchanged in [
    ("p-keep.md", dict(verdict="keep"), True),
    ("p-std.md", dict(risk="standard"), True),
    ("p-src.md", dict(target="sources/leak.md"), True),
    ("p-nodraft.md", dict(draft="không cần - chỉ sửa vài dòng"), True),
]:
    (brain1 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
    _make_proposal(str(brain1), name, **kw)
    deps, sent, calls = make_deps()
    asyncio.run(factory.proposal_tick(deps))
    cur = (brain1 / "agents" / "x.md").read_text(encoding="utf-8")
    t(f"{name} → không tự áp", cur == old_text)

# ── 16. Canary: file chung 2 brain → áp 1 brain, tới hạn mới nhân ───────────
brain2 = TMP / "brain2"
(brain2 / "agents").mkdir(parents=True, exist_ok=True)
(brain2 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
(brain1 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
# dọn state factory cũ của các test trước
(TMP / "factory-state.json").unlink(missing_ok=True)
fp2 = _make_proposal(str(brain1), "2026-10-24-x2.md")
deps, sent, calls = make_deps()
deps.brains = lambda: ["brain", "brain2"]
rep = asyncio.run(factory.proposal_tick(deps))
same2 = (brain2 / "agents" / "x.md").read_text(encoding="utf-8") == old_text
t("file chung → áp brain gốc, brain kia CHƯA đổi (canary)",
  rep["canary"] == 1 and "# X mới" in (brain1 / "agents" / "x.md").read_text(
      encoding="utf-8") and same2)
# giả hết hạn canary
stf = json.loads((TMP / "factory-state.json").read_text(encoding="utf-8"))
stf["canaries"][0]["promote_at"] = 0
(TMP / "factory-state.json").write_text(json.dumps(stf), encoding="utf-8")
rep = asyncio.run(factory.canary_tick(deps))
t("canary qua cửa sổ → nhân sang brain2",
  rep["promoted"] == 1
  and "# X mới" in (brain2 / "agents" / "x.md").read_text(encoding="utf-8"))

# ── 17. Canary có tín hiệu xấu → rollback, không nhân ───────────────────────
(brain1 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
(brain2 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
(TMP / "factory-state.json").unlink(missing_ok=True)
_make_proposal(str(brain1), "2026-10-24-x3.md")
badstore = FakeStore({str(brain1): [
    {"id": "b1", "title": "chạy x", "intent": "x", "status": "blocked",
     "block_reason": "agent x sai", "updated_at": NOW, "metadata": {}}]})
deps, sent, calls = make_deps(tasks=badstore)
deps.brains = lambda: ["brain", "brain2"]
deps.task_root = lambda n: str(brain1) if n == "brain" else str(brain2)
deps.store = badstore
asyncio.run(factory.proposal_tick(deps))
stf = json.loads((TMP / "factory-state.json").read_text(encoding="utf-8"))
# applied_at về 0: việc blocked (updated_at=NOW) nằm TRONG cửa sổ canary
stf["canaries"][0]["promote_at"] = 0
stf["canaries"][0]["applied_at"] = 0
(TMP / "factory-state.json").write_text(json.dumps(stf), encoding="utf-8")
rep = asyncio.run(factory.canary_tick(deps))
t("canary thấy blocked nhắc slug → rollback, brain2 không đổi",
  rep["reverted"] == 1
  and (brain1 / "agents" / "x.md").read_text(encoding="utf-8") == old_text
  and (brain2 / "agents" / "x.md").read_text(encoding="utf-8") == old_text)

# ── 18. Autonomy: việc xong có operator_move = cần người ─────────────────────
done_tasks = [{"id": f"a{i}", "title": f"v{i}", "status": "done",
               "updated_at": NOW - i * 100, "metadata": {}} for i in range(4)]
done_tasks.append({"id": "rv", "title": "chờ", "status": "review",
                   "updated_at": NOW, "metadata": {}})
evts = {"a0": [{"event_type": "operator_move"}], "a3": [{"event_type": "operator_grant"}]}
store3 = FakeStore({str(brain1): done_tasks}, events=evts)
deps, sent, calls = make_deps(tasks=store3)
a = factory.autonomy_stats(deps, str(brain1))
t("autonomy 4 done, 2 bị chạm → ratio 0.5, pending 1",
  a["finished"] == 4 and a["touched"] == 2 and a["ratio"] == 0.5
  and a["pending_human"] == 1)

# ── 19. Perf harness eval: case đủ loại, fail đếm đúng ─────────────────────
ev = factory._eval_run([
    {"name": "có mục Cấm", "check": "contains", "value": "## Cấm"},
    {"name": "có type", "check": "has_key", "value": "type"},
    {"name": "không quá dài", "check": "max_len", "value": 500},
    {"name": "không hứa", "check": "not_contains", "value": "em sẽ quay lại"},
    {"name": "có số phiên bản", "check": "regex", "value": "v\\d+"},
    {"name": "check lạ bỏ qua", "check": "magic", "value": "x"},
], "type: agent\n## Cấm\nv2 nội dung")
oks = {r["name"]: r["ok"] for r in ev}
t("eval 6 case: 5 đạt, check lạ = None",
  oks["có mục Cấm"] is True and oks["có type"] is True
  and oks["không quá dài"] is True and oks["không hứa"] is True
  and oks["có số phiên bản"] is True and oks["check lạ bỏ qua"] is None)

# ── 20. Eval FAIL → proposal WIN+low KHÔNG tự áp, status eval_failed ───────
(brain1 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
(TMP / "factory-state.json").unlink(missing_ok=True)
evdir = brain1 / "Joyce" / "evals"
evdir.mkdir(parents=True, exist_ok=True)
(evdir / "x.json").write_text(json.dumps({"cases": [
    {"name": "phải giữ mục Giới hạn", "check": "contains", "value": "## Giới hạn"},
    {"name": "giữ type", "check": "has_key", "value": "type"},
]}), encoding="utf-8")
_make_proposal(str(brain1), "2026-10-24-evalfail.md")
deps, sent, calls = make_deps()
rep = asyncio.run(factory.proposal_tick(deps))
t("eval rớt → KHÔNG áp, status eval_failed + báo inbox",
  (brain1 / "agents" / "x.md").read_text(encoding="utf-8") == old_text
  and "eval_failed" in (brain1 / "Joyce" / "proposals" / "2026-10-24-evalfail.md")
      .read_text(encoding="utf-8")
  and any("Perf harness" in s[0] for s in sent))

# ── 21. Eval đạt → áp bình thường + ghi điểm eval vào proposal ─────────────
(evdir / "x.json").write_text(json.dumps({"cases": [
    {"name": "giữ type", "check": "has_key", "value": "type"},
    {"name": "có nội dung", "check": "contains", "value": "nội dung mới"},
]}), encoding="utf-8")
_make_proposal(str(brain1), "2026-10-24-evalok.md")
deps, sent, calls = make_deps()
rep = asyncio.run(factory.proposal_tick(deps))
t("eval đạt → áp + proposal ghi điểm eval",
  "nội dung mới" in (brain1 / "agents" / "x.md").read_text(encoding="utf-8")
  and "eval:" in (brain1 / "Joyce" / "proposals" / "2026-10-24-evalok.md")
      .read_text(encoding="utf-8"))

# ── 22. Eval file hỏng JSON → CHẶN, giữ bản hiện tại (FIX-02, JHA-02) ───────
# Trước 1.3.41 test này khẳng định ngược lại ("hỏng thì vẫn áp, đừng để kẹt"). Chủ khai eval là để có cổng chặn;
# cổng hỏng mà vẫn mở thì không còn là cổng. Chi tiết các dạng hỏng ở test_fix02_eval_loader.py.
(brain1 / "agents" / "x.md").write_text(old_text, encoding="utf-8")
(evdir / "x.json").write_text("{hỏng json", encoding="utf-8")
_make_proposal(str(brain1), "2026-10-24-evalbad.md")
deps, sent, calls = make_deps()
rep = asyncio.run(factory.proposal_tick(deps))
t("eval hỏng → KHÔNG áp, giữ nguyên bản hiện tại",
  (brain1 / "agents" / "x.md").read_text(encoding="utf-8") == old_text)
t("eval hỏng → proposal sang eval_failed và báo inbox",
  "status: eval_failed" in (brain1 / "Joyce" / "proposals" / "2026-10-24-evalbad.md").read_text(encoding="utf-8")
  and any("bộ eval" in str(x) for x in sent))

# ── 23. Artifact index: done + artifacts → ghi index, dedup, giữ mới đầu ───
deps, sent, calls = make_deps()
at = {"id": "art1", "title": "làm slide quý 4", "status": "done",
      "brain_root": str(brain1),
      "artifacts": ["Joyce/artifacts/slide-q4.html", "Joyce/artifacts/bao-cao.md"],
      "metadata": {}}
ok1 = asyncio.run(factory.artifact_index(deps, str(brain1), at))
ok2 = asyncio.run(factory.artifact_index(deps, str(brain1), at))
aidx = brain1 / "Joyce" / "artifacts-index.md"
t("artifact_index ghi file, lần 2 dedup",
  ok1 and not ok2 and aidx.exists()
  and "slide-q4.html" in aidx.read_text(encoding="utf-8"))
t("chưa done → không ghi", asyncio.run(factory.artifact_index(
    deps, str(brain1), dict(at, id="art2", status="running"))) is False)

# ── 24. Pacing + checkpoint (cần tasks.py - bỏ qua khi thiếu fastapi) ────────
try:
    import tasks as tasks_mod

    class _PacingFake:
        def __init__(self, items):
            self.items = items

        def list_tasks(self, root, include_archived=False, limit=500):
            return self.items

    feat = tasks_mod.TasksFeature.__new__(tasks_mod.TasksFeature)
    many = [{"capability": "external-write", "status": "done",
             "updated_at": NOW - i * 60} for i in range(15)]
    feat.store = _PacingFake(many)
    nb = feat._pacing_not_before("root")
    t("15 external-write/giờ → pacing defer > now",
      nb > NOW + tasks_mod.PACING_DEFER_SECONDS - 1)
    feat.store = _PacingFake(many[:5])
    t("5 external-write/giờ → không pacing", feat._pacing_not_before("root") == 0.0)
    feat.store = _PacingFake([
        {"capability": "external-write", "status": "done",
         "updated_at": NOW - 7200}])  # ngoài cửa sổ 1h
    t("external-write cũ ngoài cửa sổ → không tính",
      feat._pacing_not_before("root") == 0.0)

    ckroot = TMP / "ckbrain"
    feat._ckpt_write(str(ckroot), {"id": "ck1", "title": "việc dài"},
                     "đã làm xong bước 1-3, còn bước 4")
    body = feat._ckpt_read(str(ckroot), "ck1")
    t("checkpoint ghi rồi đọc được", "bước 1-3" in body)
    feat._ckpt_clear(str(ckroot), "ck1")
    t("checkpoint clear xoá file", feat._ckpt_read(str(ckroot), "ck1") == "")
except Exception as e:  # noqa: BLE001
    print(f"  (bỏ test pacing/checkpoint: {type(e).__name__}: {e})")

# ── 25. Sevbot ask plugin: register đúng tool, trả lỗi ngoài server ─────────
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "sevbot_ask_plugin",
        str(Path(__file__).resolve().parents[2]
            / "system" / "plugins" / "sevbot-ask" / "plugin.py"))
    _plug = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_plug)

    class _Ctx:
        vault_root = str(brain1)

        def __init__(self):
            self.tools = {}

        def register_tool(self, name, description, handler, min_mode, schema):
            self.tools[name] = {"handler": handler, "min_mode": min_mode}

    _c = _Ctx()
    _plug.register(_c)
    t("sevbot plugin đăng ký sevbot_ask readonly",
      "sevbot_ask" in _c.tools and _c.tools["sevbot_ask"]["min_mode"] == "readonly")
    out = _c.tools["sevbot_ask"]["handler"]({}, _c)
    t("ngoài server → trả thư lỗi thân thiện", "ERROR" in out or "open_count" in out)
except Exception as e:  # noqa: BLE001
    print(f"  (bỏ test sevbot plugin: {type(e).__name__}: {e})")

# ── 26. stages_snapshot: đếm đủ các mắt xích ───────────────────────────────
(TMP / "factory-state.json").unlink(missing_ok=True)
sbstore = FakeStore({str(brain1): [
    {"id": "x1", "title": "[CI fix] sửa", "status": "ready", "capability": "code",
     "updated_at": NOW, "metadata": {"risk": "low", "auto_approved": "low_risk"}},
    {"id": "x2", "title": "v", "status": "done", "capability": "files",
     "updated_at": NOW, "metadata": {"risk": "high"}},
    {"id": "x3", "title": "v", "status": "blocked", "capability": "files",
     "updated_at": NOW, "metadata": {}},
]})
deps, sent, calls = make_deps(tasks=sbstore)
snap = factory.stages_snapshot(deps)
t("stages_snapshot đếm ci_open/auto/capacity",
  snap["ci_open"] == 1 and snap["auto_approved"] == 1
  and snap["capacity"]["done_24h"] == 1 and snap["capacity"]["blocked"] == 1
  and snap["risk"]["low"] == 1 and snap["risk"]["high"] == 1)

# ── 27. agent_scoreboard: đếm việc theo agent + proposal WIN ───────────────
adir = brain1 / "agents"
(adir / "nv-ban-hang.md").write_text(
    "---\ntype: agent\nname: NV Bán hàng\nrole: tư vấn chốt sale\n---\n# NV\n",
    encoding="utf-8")
agstore = FakeStore({str(brain1): [
    {"id": "a1", "title": "v", "status": "done", "updated_at": NOW, "metadata": {},
     "idempotency_key": "agent:m1:nv-ban-hang:1"},
    {"id": "a2", "title": "v", "status": "done", "updated_at": NOW, "metadata": {},
     "idempotency_key": "agent:m1:nv-ban-hang:2"},
    {"id": "a3", "title": "v", "status": "blocked", "updated_at": NOW, "metadata": {},
     "idempotency_key": "agent:m1:nv-ban-hang:3"},
    {"id": "a4", "title": "v", "status": "done", "updated_at": NOW, "metadata": {},
     "idempotency_key": ""},
]})
deps, sent, calls = make_deps(tasks=agstore)
rows = factory.agent_scoreboard(deps, str(brain1))
nv = next((r for r in rows if r["slug"] == "nv-ban-hang"), None)
t("scoreboard đếm đúng agent: done2 blocked1 score67",
  nv is not None and nv["done"] == 2 and nv["blocked"] == 1
  and nv["score"] == 67 and nv["role"].startswith("tư vấn"))
t("task không gắn agent không bị tính nhầm",
  sum(r["done"] for r in rows) == 2)

print(f"\n{PASS[0]} pass · {FAIL[0]} fail")
sys.exit(1 if FAIL[0] else 0)
