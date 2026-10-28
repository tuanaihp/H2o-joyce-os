"""Sổ lượt chạy của agent (B01, Joyce Harness): host ghi MỌI lượt chạy, agent không tự khai.

Vì sao có: canary cần biết bản cấu hình nào đã chạy ra sao trong công việc thật. Trước đây chỉ có `task_runs` của Kanban (chat,
workflow và bot khách hàng không đi qua đó) và việc không gắn với agent (0/160), nên mọi bằng chứng canary đều rỗng. Sổ này là kho
lượt chạy NGHIỆP VỤ chung cho chat, workflow và task. Nó chỉ GHI NHẬN; không đổi cách agent trả lời, không chặn gì.

Nguyên tắc:
- Host sinh `run_id`, chụp revision TRƯỚC khi gọi model, từ chính nội dung đã nạp. Agent không tự khai revision hay kết quả kiểm.
- Sự kiện idempotent: kết thúc hai lần chỉ có hiệu lực một lần (lần sau đếm vào `trung_lap`). Retry của cùng một việc dùng chung
  `logical_execution_id` nên không thành nhiều bằng chứng độc lập.
- Mất worker, hết hạn, restart: `interrupted` hoặc `unknown`, KHÔNG tự tính đạt hay rớt.
- Chỉ lưu metadata và băm. Không lưu prompt, hội thoại khách hay bí mật.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import config

LEDGER_VERSION = "run-ledger-v1"

TRANG_THAI = ("running", "completed", "failed", "canceled", "interrupted", "unknown", "needs_approval", "needs_input")
KET_THUC = tuple(t for t in TRANG_THAI if t != "running")
KIEM_CHUNG = ("unverified", "verified_pass", "verified_fail", "not_applicable")
LOAI_CHAN = ("", "business", "system", "permission", "waiting", "unknown")
DAU_VAO = ("chat", "workflow", "task", "bot", "loop", "reminder", "other")

_LOCK = threading.RLock()
_CONN: dict = {}


def _duong_dan() -> Path:
    return config.STATE_DIR / "run_ledger.sqlite3"


def _db() -> sqlite3.Connection:
    p = str(_duong_dan())
    with _LOCK:
        c = _CONN.get(p)
        if c is None:
            c = sqlite3.connect(p, timeout=30, check_same_thread=False, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY, logical_execution_id TEXT NOT NULL, attempt_id TEXT NOT NULL DEFAULT '',
                parent_run_id TEXT NOT NULL DEFAULT '', brain_id TEXT NOT NULL DEFAULT '', agent_id TEXT NOT NULL DEFAULT '',
                entrypoint TEXT NOT NULL DEFAULT 'other', ref TEXT NOT NULL DEFAULT '',
                started_at REAL NOT NULL, finished_at REAL, engine TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'running', block_kind TEXT NOT NULL DEFAULT '',
                verification_status TEXT NOT NULL DEFAULT 'unverified', evidence_refs TEXT NOT NULL DEFAULT '[]',
                agent_revision TEXT NOT NULL DEFAULT '', harness_revision TEXT NOT NULL DEFAULT '',
                effective_config_hash TEXT NOT NULL DEFAULT '', grant_hash TEXT NOT NULL DEFAULT '',
                eval_revision TEXT NOT NULL DEFAULT '', deps_revisions TEXT NOT NULL DEFAULT '{}',
                trung_lap INTEGER NOT NULL DEFAULT 0)""")
            c.execute("CREATE INDEX IF NOT EXISTS ix_runs_agent ON agent_runs(brain_id, agent_id, started_at DESC)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_runs_logic ON agent_runs(logical_execution_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_runs_rev ON agent_runs(agent_id, agent_revision)")
            _CONN[p] = c
        return c


def dong() -> None:
    """Đóng kết nối (test và tắt máy)."""
    with _LOCK:
        for c in _CONN.values():
            try:
                c.close()
            except sqlite3.Error:
                pass
        _CONN.clear()


# ---------------------------------------------------------------- revision (chụp từ nội dung THỰC SỰ nạp)
def _sha(text) -> str:
    return hashlib.sha256((text if isinstance(text, str) else json.dumps(text, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()


def chup_revision(*, agent_text: str = "", harness_version: str = "", guard_on: bool = False, config_view: Optional[dict] = None,
                  grant_view: Optional[dict] = None, eval_text: str = "", deps: Optional[dict] = None) -> dict:
    """Băm những gì lượt chạy sắp dùng. Mỗi tham số là nội dung đã nạp vào lượt này, không phải mtime hay tên.

    `deps` là {tên skill hoặc workflow: nội dung}. Một skill đổi mà file agent không đổi vẫn cho ra `deps_revisions` khác, nên bằng
    chứng không bị gán nhầm cho bản cũ."""
    return {
        "agent_revision": _sha(agent_text) if agent_text else "",
        "harness_revision": _sha({"v": harness_version, "guard": bool(guard_on)}),
        "effective_config_hash": _sha(config_view or {}),
        "grant_hash": _sha(grant_view or {}),
        "eval_revision": _sha(eval_text) if eval_text else "",
        "deps_revisions": {str(k): _sha(v) for k, v in sorted((deps or {}).items())},
    }


# ---------------------------------------------------------------- vòng đời
def bat_dau(*, brain_id: str, agent_id: str, entrypoint: str, ref: str = "", engine: str = "", model: str = "",
            logical_execution_id: str = "", attempt_id: str = "", parent_run_id: str = "", run_id: str = "",
            revision: Optional[dict] = None, now: Optional[float] = None) -> str:
    """Mở một lượt chạy. Gọi lại với cùng `run_id` là no-op (callback trùng). Trả run_id."""
    rid = run_id or uuid.uuid4().hex
    logic = logical_execution_id or rid
    rv = revision or {}
    ep = entrypoint if entrypoint in DAU_VAO else "other"
    with _LOCK:
        _db().execute(
            """INSERT OR IGNORE INTO agent_runs
               (run_id, logical_execution_id, attempt_id, parent_run_id, brain_id, agent_id, entrypoint, ref, started_at, engine, model,
                agent_revision, harness_revision, effective_config_hash, grant_hash, eval_revision, deps_revisions)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, logic, attempt_id or uuid.uuid4().hex[:12], parent_run_id, str(brain_id), str(agent_id), ep, str(ref)[:200],
             float(now if now is not None else time.time()), str(engine)[:60], str(model)[:80],
             rv.get("agent_revision", ""), rv.get("harness_revision", ""), rv.get("effective_config_hash", ""),
             rv.get("grant_hash", ""), rv.get("eval_revision", ""), json.dumps(rv.get("deps_revisions") or {}, ensure_ascii=False)))
    return rid


def ket_thuc(run_id: str, status: str, *, block_kind: str = "", verification: str = "unverified", evidence_refs: Optional[list] = None,
             now: Optional[float] = None) -> bool:
    """Chốt một lượt chạy. Chỉ có hiệu lực MỘT lần (running thành trạng thái cuối); lần sau là sự kiện trùng, trả False.

    Trạng thái lạ thành `unknown`. `verified_pass` chỉ hợp lệ khi lượt `completed`: một lượt lỗi hay bị chặn không thể được tính
    là đạt dù ai gọi hàm này truyền gì."""
    st = status if status in KET_THUC else "unknown"
    ver = verification if verification in KIEM_CHUNG else "unverified"
    if ver == "verified_pass" and st != "completed":
        ver = "unverified"
    bk = block_kind if block_kind in LOAI_CHAN else "unknown"
    with _LOCK:
        c = _db()
        n = c.execute(
            """UPDATE agent_runs SET status=?, finished_at=?, block_kind=?, verification_status=?, evidence_refs=?
               WHERE run_id=? AND status='running'""",
            (st, float(now if now is not None else time.time()), bk, ver, json.dumps(list(evidence_refs or [])[:20], ensure_ascii=False),
             run_id)).rowcount
        if n == 0:
            c.execute("UPDATE agent_runs SET trung_lap=trung_lap+1 WHERE run_id=?", (run_id,))
        return n == 1


def danh_dau_kiem_chung(run_id: str, verification: str, evidence_refs: Optional[list] = None) -> bool:
    """Kiểm chứng đến SAU khi lượt đã xong (người duyệt, bộ chấm). Chỉ nâng một lượt `completed` chưa kiểm."""
    if verification not in ("verified_pass", "verified_fail", "not_applicable"):
        return False
    with _LOCK:
        if verification == "verified_pass" and _trang_thai(run_id) != "completed":
            return False
        return _db().execute(
            "UPDATE agent_runs SET verification_status=?, evidence_refs=? WHERE run_id=? AND verification_status='unverified'"
            " AND status<>'running'",
            (verification, json.dumps(list(evidence_refs or [])[:20], ensure_ascii=False), run_id)).rowcount == 1


def _trang_thai(run_id: str) -> str:
    r = _db().execute("SELECT status FROM agent_runs WHERE run_id=?", (run_id,)).fetchone()
    return r["status"] if r else ""


def don_mo_coi(truoc: float, *, now: Optional[float] = None) -> int:
    """Lượt `running` bắt đầu trước `truoc` mà không ai chốt (máy tắt, worker chết) thành `interrupted`. KHÔNG tính đạt hay rớt."""
    with _LOCK:
        return _db().execute(
            "UPDATE agent_runs SET status='interrupted', finished_at=? WHERE status='running' AND started_at<?",
            (float(now if now is not None else time.time()), float(truoc))).rowcount


# ---------------------------------------------------------------- đọc
def _dong(r) -> dict:
    d = dict(r)
    d["evidence_refs"] = json.loads(d.get("evidence_refs") or "[]")
    d["deps_revisions"] = json.loads(d.get("deps_revisions") or "{}")
    return d


def lay(run_id: str) -> Optional[dict]:
    r = _db().execute("SELECT * FROM agent_runs WHERE run_id=?", (run_id,)).fetchone()
    return _dong(r) if r else None


def danh_sach(*, brain_id: str = "", agent_id: str = "", agent_revision: str = "", tu: float = 0.0, gioi_han: int = 500) -> list:
    q, a = "SELECT * FROM agent_runs WHERE started_at>=?", [float(tu)]
    for col, v in (("brain_id", brain_id), ("agent_id", agent_id), ("agent_revision", agent_revision)):
        if v:
            q += f" AND {col}=?"
            a.append(v)
    q += " ORDER BY started_at DESC LIMIT ?"
    a.append(int(gioi_han))
    return [_dong(r) for r in _db().execute(q, a).fetchall()]


def thong_ke(*, brain_id: str = "", agent_id: str = "", agent_revision: str = "", tu: float = 0.0) -> dict:
    """Đếm theo LOGICAL EXECUTION, không theo lần thử: retry nhiều lần chỉ là một bằng chứng. Với mỗi logical execution lấy lần thử
    MỚI NHẤT làm kết quả (các lần trước nằm ở `thu_lai`). `unknown` và `interrupted` tách riêng, không bao giờ được cộng vào đạt."""
    runs = danh_sach(brain_id=brain_id, agent_id=agent_id, agent_revision=agent_revision, tu=tu, gioi_han=5000)
    cuoi: dict = {}
    for r in sorted(runs, key=lambda x: x["started_at"]):
        cuoi[r["logical_execution_id"]] = r
    out = {"lan_chay": len(runs), "logical": len(cuoi), "thu_lai": len(runs) - len(cuoi), "verified_pass": 0, "verified_fail": 0,
           "chua_kiem": 0, "dang_chay": 0, "doi_duyet": 0, "gian_doan": 0, "loi_he_thong": 0, "trung_lap": sum(r["trung_lap"] for r in runs)}
    for r in cuoi.values():
        s, v = r["status"], r["verification_status"]
        if s == "running":
            out["dang_chay"] += 1
        elif s in ("needs_approval", "needs_input"):
            out["doi_duyet"] += 1
        elif s in ("interrupted", "unknown", "canceled"):
            out["gian_doan"] += 1
        elif s == "failed" and r["block_kind"] == "system":
            out["loi_he_thong"] += 1
        elif v == "verified_pass":
            out["verified_pass"] += 1
        elif v == "verified_fail" or s == "failed":
            out["verified_fail"] += 1
        else:
            out["chua_kiem"] += 1
    return out


# ---------------------------------------------------------------- tiện ích cho nơi gọi
def chup_cho_agent(root, slug: str, agent_text: str, *, harness_version: str = "", guard_on: bool = False, config_view: Optional[dict] = None,
                   grant_view: Optional[dict] = None, deps: Optional[dict] = None) -> dict:
    """Chụp revision của MỘT agent sắp chạy. `agent_text` là nội dung đã nạp thật cho lượt này; bộ ca thử đọc từ
    `<root>/Joyce/evals/<slug>.json` nếu có. Lỗi đọc file eval không làm hỏng lượt: revision eval để rỗng."""
    ev = ""
    try:
        p = Path(str(root)) / "Joyce" / "evals" / f"{slug}.json"
        if p.is_file():
            ev = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        ev = ""
    return chup_revision(agent_text=agent_text, harness_version=harness_version, guard_on=guard_on, config_view=config_view,
                         grant_view=grant_view, eval_text=ev, deps=deps)


def ghi_an_toan(fn, *a, **k):
    """Gọi một hàm của sổ mà KHÔNG BAO GIỜ làm hỏng lượt chạy thật: lỗi sổ chỉ ra stderr. Trả kết quả hoặc None."""
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa: BLE001
        import sys
        print(f"[run_ledger] {type(e).__name__}: {e}", file=sys.stderr)
        return None


def bo(run_id: str) -> bool:
    """Gỡ một lượt `running` chưa làm gì (lượt im lặng). Chỉ gỡ được lượt còn đang chạy: lượt đã chốt là bằng chứng, không xoá."""
    with _LOCK:
        return _db().execute("DELETE FROM agent_runs WHERE run_id=? AND status='running'", (run_id,)).rowcount == 1


def agent_quan_sat_duoc(*, tu: float, toi_thieu: int) -> int:
    """Số cặp (brain, agent) có ít nhất `toi_thieu` lượt chạy đọc được revision kể từ `tu`."""
    r = _db().execute(
        "SELECT COUNT(*) AS n FROM (SELECT brain_id, agent_id FROM agent_runs WHERE started_at>=? AND agent_revision<>'' "
        "GROUP BY brain_id, agent_id HAVING COUNT(*)>=?)", (float(tu), int(toi_thieu))).fetchone()
    return int(r["n"] if r else 0)


def doc_file_agent(root, slug: str) -> str:
    """Nội dung THÔ của file agent sắp chạy: `<root>/agents/<slug>.md`, rơi về bản dùng chung của hệ thống nếu brain không có bản
    riêng. `agent_revision` là băm đúng chuỗi này nên so được với `candidate_hash` của canary (cùng băm nội dung file). Không đọc
    được thì trả rỗng và revision rỗng: lượt vẫn ghi nhưng không bao giờ được tính làm bằng chứng cho một bản cụ thể."""
    try:
        if root:
            p = Path(str(root)) / "agents" / f"{slug}.md"
            if p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
        import system_agents
        sp = system_agents.path(slug)
        if sp is not None and Path(sp).is_file():
            return Path(sp).read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    return ""
