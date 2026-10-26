"""factory.py - lớp "agentic software factory" cho Joyce (port ý tưởng OpenAI, Pragmatic
Engineer 15/09/2026; trang học: wiki/agent-update/OpenAI Software Factory - nha may agentic
9 buoc).

OpenAI khép kín vòng đời một thay đổi bằng các feedback loop NHỎ quanh việc: agent code xong
thì CI babysit đến khi green, change được giao cho một deploy-watcher "handhold" đến khi an
toàn, Perf Factory gom alert trùng rồi đề xuất fix, Sevbot đọc nhiều sự cố cùng gốc rồi đề
xuất mitigation (không tự hành động). Joyce đã có các mảnh tương đương rời: kanban (implement),
giám-định PPC (review), incident_desk (triage từng sự cố), resonance/joyce_goal (/goal nền),
sweep (nhìn việc lỡ). Module này nối các mảnh còn thiếu thành vòng kín:

  1. CI babysit   - task có `post_check` (lệnh kiểm chứng do chủ khai trong Joyce/factory.json
                    hoặc truyền lúc enqueue) chạy xong thì tự chạy lệnh; fail → enqueue task
                    `[CI fix]` kèm output, tối đa CI_MAX_ROUNDS vòng. Lệnh check KHÔNG bao giờ
                    lấy từ output model - chỉ từ file cấu hình chủ sở hữu hoặc caller tin cậy.
  2. Deploy watch - task khai `watch_spec` (declarative: file_exists/contains/url_ok) được ghi
                    nhận khi xong; `watch_tick` (5 phút) kiểm chứng kết quả thật, fail → mở lại
                    task MỘT lần + báo hòm thư (hành vi "handhold"). Check chỉ được đọc, không
                    được làm gì khác.
  3. Perf Factory - gom lỗi kanban/incident cùng "chữ ký" trong 24h; ≥2 → enqueue MỘT task
                    `[Perf] root-cause` (idempotent + cooldown 6h) thay vì N task lặp.
  4. Sevbot       - chữ ký ≥3 (hoặc nhiều incident needs_you cùng gốc) → MỘT bản tin context
                    + đề xuất mitigation vào hòm thư (dedup theo ngày). KHÔNG tự hành động -
                    y như Sevbot của OpenAI chỉ đề xuất, người quyết.
  5. Discovery    - cùng tiêu đề task xong tay ≥3 lần/30 ngày → gợi ý làm loop/nhắc hẹn
                    (giải "awareness overhang" - chủ không biết Joyce làm lặp được).
  6. Recipes      - ghi `Joyce/recipe-gallery.md` mỗi brain: loop đang bật, workflow active,
                    việc tay lặp đã chứng minh chạy tốt - "recipe" để phòng khác copy.
  7. Self-improve - proposal PPC có verdict=win + risk=low + "Bản nháp đầy đủ" → TỰ ÁP vào
                    file agent/skill/workflow (bản backup cạnh proposal, luôn lật lại được).
                    OpenAI: "skills nội bộ do Codex TỰ DUY TRÌ". risk=standard/high hay thiếu
                    bản nháp → vẫn chờ chủ duyệt như cũ.
  8. Canary       - file mục tiêu tồn tại ở ≥2 brain (file chung đã nhân) → áp ở brain đề
                    xuất TRƯỚC, giữ canary_hours; qua cửa sổ không có tín hiệu xấu mới nhân
                    sang các brain còn lại. Tín hiệu xấu (task blocked nhắc tới slug) → tự
                    rollback file. OpenAI: deploy agent canh feature-flag rollout.
  9. Autonomy     - `autonomy_stats`: % việc xong KHÔNG cần người chạm (không review cột,
                    không grant quyền) - KPI "surface area người phải quản" mà OpenAI đo,
                    trả qua GET /work/factory.

Phân biệt với các mảnh đã có: incident_desk xử TỪNG sự cố (triage 1 lỗi), module này xử PATTERN
(nhiều lỗi cùng gốc). Sweep NHÌN việc lỡ giờ, module này HÀNH ĐỘNG quanh việc đã chạy.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import winproc

# ── Ngưỡng ──────────────────────────────────────────────────────────────────
WATCH_TICK_SECONDS = 300          # watcher chạy mỗi 5 phút
PATTERN_TICK_SECONDS = 3600       # Perf/Sevbot/recipes quét mỗi giờ (cùng nhịp sweep)
CI_MAX_ROUNDS = 3                 # tối đa vòng "sửa cho CI green"
CI_CMD_TIMEOUT = 300              # mỗi lệnh check tối đa 5 phút
WATCH_DEFAULT_DELAY_MIN = 10      # watcher bắt đầu soi sau khi xong 10p (hệ thống ngoài cần giờ xử lý)
WATCH_DEFAULT_MINUTES = 120       # theo dõi tối đa 2 giờ
PATTERN_WINDOW_SECONDS = 24 * 3600
PERF_MIN_HITS = 2                 # ≥2 cùng chữ ký → xếp task root-cause
SEV_MIN_HITS = 3                  # ≥3 cùng chữ ký → bản tin Sevbot
PERF_COOLDOWN_SECONDS = 6 * 3600  # 1 chữ ký không xếp task root-cause quá 1 lần/6h
DISCOVERY_MIN_DONE = 3            # ≥3 lần xong tay cùng việc trong 30 ngày → gợi ý lặp
DISCOVERY_WINDOW_SECONDS = 30 * 24 * 3600
CANARY_DEFAULT_HOURS = 24         # file chung: áp 1 brain, canh 24h mới nhân các brain khác
PROPOSAL_MAX_GROW = 4.0           # bản nháp không được phình quá 4x file gốc (chống viết đè bừa)
PROPOSAL_MIN_LEN = 120            # draft dưới mức này coi như rỗng - không tự áp
PROPOSAL_MAX_BYTES = 400 * 1024   # proposal quá lớn không đọc
AUTONOMY_DAYS = 30                # cửa sổ đo "việc tự xong không cần người"
AUTONOMY_CAP = 400                # tối đa task đếm mỗi brain (chống quét khổng lồ)

# Proposal chỉ được tự áp vào file PROMPT của agent/skill/workflow trong brain -
# không đụng sources/ (bất biến), CLAUDE.md/AGENTS.md (schema người+AI), code server.
_ALLOWED_TARGET_DIRS = ("agents/", "skills/", "workflows/")
# Sự kiện kanban do NGƯỜI gây ra - có mặt = việc cần người chạm, tính vào autonomy.
_HUMAN_EVENTS = ("operator_move", "operator_grant")

# Capability được coi "low-risk" cho auto-approve: chỉ đọc dữ liệu hoặc ghi trong brain.
# external-write/code đi tiền/ngoài KHÔNG BAO GIỜ auto - dù specifier có khai low đi nữa.
SAFE_RISK_CAPS = {"files", "research", "mcp-read"}

_META_KEYS = ("risk", "post_check", "watch_spec")   # khoá metadata được truyền từ caller


@dataclass
class FactoryDeps:
    """Mượn từ main.py - inject để test được, không vòng import."""
    brains: Callable[[], list]                     # list TÊN brain
    task_root: Callable[[str], str]                # tên brain → root path
    store: object                                  # tasks_feature.store (list/get/move)
    enqueue: Callable                              # tasks_feature.enqueue
    loops: object                                  # loop_feature (list_loops + loop_view + read_state)
    workflows_dir: Callable[[str], Path]           # root → thư mục workflows/
    inbox: Callable                                # async (text, {kind,label,source,dedup})
    incidents_list: Callable[[str, int], list]     # incident_desk.list(brain, limit)
    settings_get: Callable[[], dict]               # cfgmod.read_settings
    state_dir: Path
    atomic_write_text: Optional[Callable] = None


# ── State (STATE_DIR/factory-state.json) ────────────────────────────────────

def _state_path(deps: FactoryDeps) -> Path:
    return Path(deps.state_dir) / "factory-state.json"


def _load_state(deps: FactoryDeps) -> dict:
    try:
        p = _state_path(deps)
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                d.setdefault("watches", [])
                d.setdefault("perf_cd", {})
                d.setdefault("sev_sent", {})
                d.setdefault("canaries", [])
                return d
    except Exception as e:  # noqa: BLE001
        print(f"[factory] đọc state: {type(e).__name__}: {e}", file=sys.stderr)
    return {"watches": [], "perf_cd": {}, "sev_sent": {}, "canaries": []}


def _save_state(deps: FactoryDeps, st: dict) -> None:
    text = json.dumps(st, ensure_ascii=False, indent=1)
    p = _state_path(deps)
    try:
        if deps.atomic_write_text:
            deps.atomic_write_text(p, text)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"[factory] ghi state: {type(e).__name__}: {e}", file=sys.stderr)


# ── Cấu hình per-brain: Joyce/factory.json ──────────────────────────────────

def load_factory_cfg(root: str) -> dict:
    """Đọc Joyce/factory.json của brain. Không có file → mặc định an toàn:
    không có lệnh post_check nào (CI babysit ngủ), watcher mặc định 10p/120p."""
    cfg = {}
    try:
        p = Path(root) / "Joyce" / "factory.json"
        if p.is_file():
            cfg = json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"[factory] factory.json {root}: {type(e).__name__}: {e}", file=sys.stderr)
    return {
        "post_check": cfg.get("post_check") if isinstance(cfg.get("post_check"), dict) else {},
        "ci_max_rounds": max(0, min(5, int(cfg.get("ci_max_rounds", CI_MAX_ROUNDS)))),
        "watch_delay_min": max(0, int(cfg.get("watch_delay_min", WATCH_DEFAULT_DELAY_MIN))),
        "watch_minutes": max(5, int(cfg.get("watch_minutes", WATCH_DEFAULT_MINUTES))),
        "low_risk_auto": bool(cfg.get("low_risk_auto", True)),
        "discovery": bool(cfg.get("discovery", True)),
        "recipes": bool(cfg.get("recipes", True)),
        "self_improve": bool(cfg.get("self_improve", True)),
        "canary_hours": max(1, min(24 * 14, int(cfg.get("canary_hours", CANARY_DEFAULT_HOURS)))),
    }


def _post_check_cmds(root: str, task: dict, cfg: dict) -> list:
    """Lệnh kiểm chứng cho task: metadata.post_check (caller tin cậy) ưu tiên,
    sau đó lệnh khai cho capability trong factory.json. KHÔNG lấy từ model/specifier."""
    md = task.get("metadata") or {}
    cmds = md.get("post_check")
    if isinstance(cmds, str):
        cmds = [cmds]
    if not isinstance(cmds, list) or not cmds:
        cap = str(task.get("capability") or "")
        cmds = (cfg.get("post_check") or {}).get(cap) \
            or (cfg.get("post_check") or {}).get("*") or []
    out = [str(c).strip() for c in cmds if str(c).strip()][:5]
    return out


# ── #2 Risk gating ──────────────────────────────────────────────────────────

def low_risk_auto(task: dict, cfg_low_risk_auto: bool = True) -> bool:
    """Việc chờ duyệt mà RỦI RO THẤP → bỏ cột review (auto-approve kiểu OpenAI).

    Tất cả phải đúng: caller/specifier khai `risk=low`, capability chỉ đọc/ghi-trong-brain
    (SAFE_RISK_CAPS - external-write/tiền không bao giờ tự qua), và brain không tắt cờ.
    """
    if not cfg_low_risk_auto:
        return False
    md = task.get("metadata") or {}
    if str(md.get("risk") or "").lower() != "low":
        return False
    return str(task.get("capability") or "") in SAFE_RISK_CAPS


def extra_meta_from(risk: str = "", post_check=None, watch_spec=None) -> dict:
    """Lọc khoá metadata caller được phép truyền (whitelist - chặn key lạ đi ngầm)."""
    out = {}
    if str(risk or "").strip().lower() in ("low", "standard", "high"):
        out["risk"] = str(risk).strip().lower()
    if post_check:
        cmds = post_check if isinstance(post_check, list) else [post_check]
        out["post_check"] = [str(c)[:300] for c in cmds if str(c).strip()][:5]
    ws = sanitize_watch_spec(watch_spec)
    if ws:
        out["watch_spec"] = ws
    return out


def sanitize_watch_spec(ws) -> Optional[dict]:
    """watch_spec chỉ được là dữ liệu declarative; loại check không biết bị bỏ."""
    if not isinstance(ws, dict):
        return None
    checks = []
    for c in (ws.get("checks") or [])[:8]:
        if not isinstance(c, dict):
            continue
        t = str(c.get("type") or "")
        if t == "file_exists" and c.get("path"):
            checks.append({"type": t, "path": str(c["path"])[:400]})
        elif t == "contains" and c.get("path") and c.get("needle") is not None:
            checks.append({"type": t, "path": str(c["path"])[:400],
                           "needle": str(c["needle"])[:300]})
        elif t == "url_ok" and str(c.get("url") or "").startswith(("http://", "https://")):
            checks.append({"type": t, "url": str(c["url"])[:500]})
    if not checks:
        return None
    return {
        "checks": checks,
        "delay_min": max(0, int(ws.get("delay_min", WATCH_DEFAULT_DELAY_MIN))),
        "minutes": max(5, int(ws.get("minutes", WATCH_DEFAULT_MINUTES))),
    }


# ── #1 CI babysit ───────────────────────────────────────────────────────────

async def _run_cmd(cmd: str, cwd: str) -> tuple:
    """(ok, output tail) - lệnh chạy trong brain root, timeout cứng."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            **winproc.kwargs_no_window())
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=CI_CMD_TIMEOUT)
            tail = (out or b"").decode("utf-8", "replace")[-1500:]
            return proc.returncode == 0, tail
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return False, f"lệnh chạy quá {CI_CMD_TIMEOUT}s (đã dừng)"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


async def ci_babysit(deps: FactoryDeps, root: str, task: dict) -> dict:
    """Chạy post_check của việc vừa xong. Fail → xếp task [CI fix] (≤ CI_MAX_ROUNDS).

    Trả {ran, passed, fix_tid} - không ném lỗi (chạy trong finally của worker)."""
    res = {"ran": False, "passed": True, "fix_tid": ""}
    try:
        cfg = load_factory_cfg(root)
        cmds = _post_check_cmds(root, task, cfg)
        if not cmds or str(task.get("status") or "") not in ("done", "review"):
            return res
        res["ran"] = True
        fails = []
        for cmd in cmds:
            ok, tail = await _run_cmd(cmd, root)
            if not ok:
                fails.append({"cmd": cmd, "tail": tail})
        res["passed"] = not fails
        if res["passed"]:
            return res

        md = task.get("metadata") or {}
        round_no = int(md.get("ci_round") or 0) + 1
        if round_no > int(cfg.get("ci_max_rounds") or CI_MAX_ROUNDS):
            await deps.inbox(
                f"🧪 **CI babysit**: '{task.get('title')}' đã sửa {CI_MAX_ROUNDS} vòng mà check "
                f"vẫn đỏ ({fails[0]['cmd'][:80]}). Dừng tự sửa - cần anh xem tay.",
                kind="system", label="ci babysit", source="factory",
                dedup=f"cimax:{task.get('id')}")
            return res

        tail_txt = "\n---\n".join(
            f"$ {f['cmd']}\n{f['tail'][-700:]}" for f in fails)[:1800]
        brain = str(task.get("brain_root") or root)
        fix_tid = deps.enqueue(
            brain,
            f"[CI fix v{round_no}] {str(task.get('title') or '')[:90]}",
            "Việc gốc đã làm xong nhưng lệnh kiểm chứng đỏ. Sửa cho các lệnh sau PASS rồi "
            "báo lại những gì đã sửa:\n\n" + tail_txt
            + f"\n\nViệc gốc: {task.get('id')} · {task.get('title')}",
            priority=1,
            created_by="factory",
            chat_id=str(task.get("chat_id") or ""),
            idempotency_key=f"cifix:{task.get('id')}:{round_no}",
            extra_meta={"ci_round": round_no,
                        "post_check": [f["cmd"] for f in fails],
                        "risk": "low",
                        "ci_origin": str(task.get("id") or "")},
        )
        res["fix_tid"] = fix_tid
        await deps.inbox(
            f"🧪 **CI babysit**: check của '{task.get('title')}' đỏ "
            f"({len(fails)}/{len(cmds)} lệnh) - đã xếp việc sửa vòng {round_no}/"
            f"{cfg.get('ci_max_rounds')}.",
            kind="system", label="ci babysit", source="factory",
            dedup=f"ci:{task.get('id')}:{round_no}")
    except Exception as e:  # noqa: BLE001
        print(f"[factory] ci_babysit {task.get('id')}: {type(e).__name__}: {e}", file=sys.stderr)
    return res


# ── #4 Deploy watcher ("handhold") ──────────────────────────────────────────

async def watch_register(deps: FactoryDeps, root: str, task: dict) -> bool:
    """Task xong mà khai watch_spec → ghi vào sổ theo dõi."""
    try:
        md = task.get("metadata") or {}
        spec = sanitize_watch_spec(md.get("watch_spec"))
        if not spec or str(task.get("status") or "") not in ("done", "review"):
            return False
        cfg = load_factory_cfg(root)
        # None-aware: spec.delay_min=0 là "soi ngay", không được rơi về mặc định 10p
        # của brain (lỗi thật gặp trong test: watch cứ nằm chờ mãi).
        delay = int(spec["delay_min"]) if spec.get("delay_min") is not None \
            else int(cfg.get("watch_delay_min"))
        minutes = int(spec["minutes"]) if spec.get("minutes") is not None \
            else int(cfg.get("watch_minutes"))
        now = time.time()
        st = _load_state(deps)
        st["watches"] = [w for w in st["watches"]
                         if w.get("task_id") != task.get("id")]
        st["watches"].append({
            "task_id": str(task.get("id") or ""),
            "brain": str(task.get("brain_root") or root),
            "root": root,
            "title": str(task.get("title") or "")[:160],
            "chat_id": str(task.get("chat_id") or ""),
            "spec": spec,
            "after": now + delay * 60,
            "until": now + minutes * 60,
            "state": "watching",
        })
        st["watches"] = st["watches"][-200:]
        _save_state(deps, st)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[factory] watch_register {task.get('id')}: {type(e).__name__}: {e}",
              file=sys.stderr)
        return False


def _check_one(check: dict, root: str) -> tuple:
    """(ok, ghi chú lỗi) - check chỉ ĐỌC: file trong brain hoặc status URL."""
    t = check.get("type")
    if t in ("file_exists", "contains"):
        try:
            p = (Path(root) / str(check.get("path") or "")).resolve()
            if Path(root).resolve() not in p.parents and p != Path(root).resolve():
                return False, "đường dẫn watch_spec ra ngoài brain (từ chối)"
            if t == "file_exists":
                return (p.exists(), "" if p.exists() else f"chưa thấy {check.get('path')}")
            if not p.is_file():
                return False, f"chưa có file {check.get('path')} để đọc"
            txt = p.read_text(encoding="utf-8", errors="replace")[:200000]
            ok = str(check.get("needle") or "") in txt
            return ok, "" if ok else f"không thấy chuỗi cần tìm trong {check.get('path')}"
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"
    if t == "url_ok":
        try:
            req = urllib.request.Request(str(check.get("url")), method="HEAD",
                                         headers={"User-Agent": "joyce-watch/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                ok = 200 <= r.status < 400
                return ok, "" if ok else f"HTTP {r.status}"
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"
    return True, "check không biết (bỏ qua)"


async def watch_tick(deps: FactoryDeps) -> dict:
    """Mỗi 5 phút: kiểm chứng các watch tới hạn. Fail → mở lại task MỘT lần."""
    rep = {"checked": 0, "ok": 0, "failed": 0, "expired": 0}
    st = _load_state(deps)
    now = time.time()
    changed = False
    for w in st.get("watches", []):
        if w.get("state") != "watching" or now < float(w.get("after") or 0):
            continue
        if now > float(w.get("until") or 0):
            w["state"] = "expired"
            changed = True
            rep["expired"] += 1
            continue
        rep["checked"] += 1
        root = str(w.get("root") or "")
        fails = [note for c in (w.get("spec") or {}).get("checks") or []
                 for ok, note in [_check_one(c, root)] if not ok and note]
        if not fails:
            w["state"] = "ok"
            changed = True
            rep["ok"] += 1
            try:
                await deps.inbox(
                    f"👀 **Handhold**: '{w.get('title')}' đã kiểm chứng xong - kết quả đúng như "
                    f"theo dõi, đóng watch.",
                    kind="system", label="deploy watch", source="factory",
                    dedup=f"watchok:{w.get('task_id')}")
            except Exception:
                pass
            continue
        # Fail: mở lại task MỘT lần (OpenAI: agent handhold kéo change về khi tín hiệu xấu)
        w["state"] = "reopened"
        changed = True
        rep["failed"] += 1
        try:
            deps.store.move(str(w.get("task_id")), "ready",
                            "watcher: " + "; ".join(fails)[:300])
        except Exception as e:  # noqa: BLE001
            print(f"[factory] watcher reopen {w.get('task_id')}: {type(e).__name__}: {e}",
                  file=sys.stderr)
        try:
            await deps.inbox(
                f"👀 **Handhold**: '{w.get('title')}' kiểm chứng THẤT BẠI - "
                f"{'; '.join(fails)[:240]}. Đã đưa việc về Sẵn sàng chạy lại.",
                kind="system", label="deploy watch", source="factory",
                dedup=f"watchfail:{w.get('task_id')}")
        except Exception:
            pass
    if changed:
        _save_state(deps, st)
    return rep


# ── #5 Perf Factory + #6 Sevbot (pattern trên sự cố) ────────────────────────

def _signature(text: str) -> str:
    """Chữ ký lỗi: chuẩn hoá để cùng gốc gom một cụm (bỏ path/số/id)."""
    s = re.sub(r"[A-Za-z]:\\[^\s]+|/[^\s]+", " ", str(text or "").lower())
    s = re.sub(r"\b[0-9a-f]{8,}\b|\d+", " ", s)
    s = re.sub(r"[^a-z0-9à-ỹ ]+", " ", s)
    return " ".join(s.split())[:80]


def _collect_failures(deps: FactoryDeps, now: float) -> dict:
    """{sig: {count, refs:[...], brain, sample}} từ incident + task blocked 24h."""
    groups: dict = {}
    try:
        for inc in deps.incidents_list("", 200) or []:
            if str(inc.get("status") or "") not in ("open", "needs_you", "retrying"):
                continue
            at = float(inc.get("last_at") or inc.get("at") or 0)
            if now - at > PATTERN_WINDOW_SECONDS:
                continue
            sig = _signature(inc.get("error") or inc.get("title") or "")
            if not sig:
                continue
            g = groups.setdefault(sig, {"count": 0, "refs": [], "brain": "", "sample": ""})
            g["count"] += int(inc.get("count") or 1)
            g["refs"].append(f"{inc.get('source')}:{inc.get('ref')}")
            g["brain"] = g["brain"] or str(inc.get("brain") or "")
            g["sample"] = g["sample"] or str(inc.get("error") or "")[:400]
    except Exception as e:  # noqa: BLE001
        print(f"[factory] incidents scan: {type(e).__name__}: {e}", file=sys.stderr)
    for name in deps.brains() or []:
        try:
            root = deps.task_root(str(name))
            for t in deps.store.list_tasks(root, include_archived=False) or []:
                if str(t.get("status") or "") != "blocked":
                    continue
                if str(t.get("block_kind") or "") in ("needs_input", "limit", "capability"):
                    continue
                at = float(t.get("updated_at") or 0)
                if now - at > PATTERN_WINDOW_SECONDS:
                    continue
                sig = _signature(t.get("block_reason") or t.get("title") or "")
                if not sig:
                    continue
                g = groups.setdefault(sig, {"count": 0, "refs": [], "brain": "", "sample": ""})
                g["count"] += 1
                g["refs"].append(f"kanban:{t.get('id')}")
                g["brain"] = g["brain"] or str(t.get("brain_root") or root)
                g["sample"] = g["sample"] or str(t.get("block_reason") or "")[:400]
        except Exception as e:  # noqa: BLE001
            print(f"[factory] kanban scan {name}: {type(e).__name__}: {e}", file=sys.stderr)
    return groups


async def pattern_tick(deps: FactoryDeps) -> dict:
    """Perf Factory: ≥2 cùng chữ ký → MỘT task root-cause. Sevbot: ≥3 → bản tin đề xuất."""
    rep = {"patterns": 0, "perf": [], "sev": []}
    now = time.time()
    groups = _collect_failures(deps, now)
    if not groups:
        return rep
    st = _load_state(deps)
    changed = False
    for sig, g in sorted(groups.items(), key=lambda kv: -kv[1]["count"]):
        if g["count"] < PERF_MIN_HITS:
            continue
        rep["patterns"] += 1
        sig_hash = hashlib.sha1(sig.encode("utf-8")).hexdigest()[:10]
        refs = ", ".join(g["refs"][:5])

        # Perf Factory: một task root-cause duy nhất cho cụm lỗi (cooldown 6h/chữ ký)
        if now - float(st["perf_cd"].get(sig_hash) or 0) > PERF_COOLDOWN_SECONDS:
            try:
                brain = g["brain"] or str(deps.brains()[0])
                tid = deps.enqueue(
                    brain,
                    f"[Perf] root-cause: {sig[:70]}",
                    f"PERF FACTORY - cụm {g['count']} sự cố CÙNG CHỮ KÝ trong 24h, khả năng "
                    f"một gốc chung thay vì nhiều lỗi rời:\n\nChữ ký: {sig}\n"
                    f"Đối tượng: {refs}\nLỗi mẫu:\n{g['sample']}\n\n"
                    "Việc: đọc log/trạng thái các đối tượng trên, xác định GỐC CHUNG, "
                    "đề xuất sửa một lần cho cả cụm. Không sửa từng việc lẻ.",
                    priority=1, created_by="factory",
                    idempotency_key=f"perf:{sig_hash}",
                    extra_meta={"risk": "low", "perf_sig": sig_hash},
                )
                st["perf_cd"][sig_hash] = now
                changed = True
                rep["perf"].append({"sig": sig, "count": g["count"], "task": tid})
            except Exception as e:  # noqa: BLE001
                print(f"[factory] perf enqueue {sig_hash}: {type(e).__name__}: {e}",
                      file=sys.stderr)

        # Sevbot: bản tin context + mitigation đề xuất (dedup theo ngày) - KHÔNG tự hành.
        if g["count"] >= SEV_MIN_HITS:
            day = time.strftime("%Y-%m-%d", time.localtime(now))
            if st["sev_sent"].get(sig_hash) != day:
                st["sev_sent"][sig_hash] = day
                changed = True
                rep["sev"].append({"sig": sig, "count": g["count"]})
                try:
                    await deps.inbox(
                        f"🚨 **Sevbot**: {g['count']} sự cố CÙNG MẪU trong 24h - khả năng một "
                        f"gốc chung.\nChữ ký: {sig}\nĐối tượng: {refs}\nLỗi mẫu: "
                        f"{g['sample'][:200]}\nĐề xuất: việc `[Perf] root-cause` đã (hoặc sẽ) "
                        f"được xếp để điều tra gốc; nếu lỗi liên quan đăng nhập/khoá API/quota "
                        f"thì chỉ anh gỡ được - xem trang Kết nối/Cài đặt. Em không tự hành "
                        f"động ngoài việc xếp việc điều tra.",
                        kind="system", label="sevbot", source="factory",
                        dedup=f"sev:{sig_hash}:{day}")
                except Exception as e:  # noqa: BLE001
                    print(f"[factory] sev inbox {sig_hash}: {type(e).__name__}: {e}",
                          file=sys.stderr)
    if changed:
        # Dọn khoá cũ khỏi cooldown/sent (giữ state nhỏ)
        st["perf_cd"] = {k: v for k, v in st["perf_cd"].items()
                         if now - float(v) < PATTERN_WINDOW_SECONDS * 3}
        st["sev_sent"] = {k: v for k, v in st["sev_sent"].items()
                          if v >= time.strftime("%Y-%m-%d",
                                                time.localtime(now - 3 * 86400))}
        _save_state(deps, st)
    return rep


# ── #8 Discovery suggestion ─────────────────────────────────────────────────

async def discovery_suggest(deps: FactoryDeps, root: str, task: dict) -> bool:
    """Cùng việc xong tay ≥DISCOVERY_MIN_DONE lần/30 ngày → gợi ý làm loop/nhắc hẹn."""
    try:
        cfg = load_factory_cfg(root)
        if not cfg.get("discovery"):
            return False
        if str(task.get("status") or "") != "done":
            return False
        if str(task.get("created_by") or "") in ("loop", "workflow", "factory", "system"):
            return False
        title_norm = " ".join(str(task.get("title") or "").lower().split())
        if len(title_norm) < 8 or title_norm.startswith("["):
            return False
        now = time.time()
        same = [t for t in deps.store.list_tasks(root, include_archived=False) or []
                if t.get("id") != task.get("id")
                and str(t.get("status") or "") == "done"
                and " ".join(str(t.get("title") or "").lower().split()) == title_norm
                and now - float(t.get("updated_at") or 0) < DISCOVERY_WINDOW_SECONDS]
        if len(same) + 1 < DISCOVERY_MIN_DONE:
            return False
        n = len(same) + 1
        await deps.inbox(
            f"💡 **Gợi ý lặp**: việc '{task.get('title')}' đã chạy tay thành công {n} lần "
            f"trong 30 ngày. Nếu việc này định kỳ, anh có thể bảo em đặt loop hoặc nhắc hẹn "
            f"- khỏi giao tay mỗi lần.",
            kind="system", label="gợi ý lặp", source="factory",
            dedup=f"discover:{title_norm}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[factory] discovery {task.get('id')}: {type(e).__name__}: {e}",
              file=sys.stderr)
        return False


# ── #10 Recipe gallery ──────────────────────────────────────────────────────

def write_recipes(deps: FactoryDeps, name: str, root: str) -> bool:
    """Ghi Joyce/recipe-gallery.md: loop đang bật + workflow active + việc tay lặp đã chứng
    minh - 'sổ công thức' để phòng khác copy (role plugins của OpenAI)."""
    try:
        cfg = load_factory_cfg(root)
        if not cfg.get("recipes"):
            return False
        lines = [f"# Recipe gallery - {name}",
                 "",
                 "> Tự sinh bởi factory (mỗi giờ). Công thức ĐÃ CHẠY được của brain này -",
                 "> phòng khác muốn dùng lại thì copy file loop/workflow tương ứng.",
                 ""]
        try:
            st_all = deps.loops.read_state(name)
            loops_on = [lp for lp in deps.loops.list_loops(name) or [] if lp.get("enabled")]
            lines.append(f"## Loop đang bật ({len(loops_on)})")
            for lp in loops_on[:20]:
                v = deps.loops.loop_view(name, lp, st_all)
                runs = v.get("run_count") or v.get("runs") or "?"
                lines.append(f"- `{lp.get('slug')}` - {lp.get('title') or lp.get('slug')} "
                             f"(đã chạy {runs} lượt)")
            if not loops_on:
                lines.append("- (chưa có loop nào bật)")
        except Exception as e:  # noqa: BLE001
            lines.append(f"## Loop đang bật\n- (đọc lỗi: {type(e).__name__})")
        try:
            wdir = deps.workflows_dir(root)
            wfs = sorted(Path(wdir).glob("*.md")) if Path(wdir).is_dir() else []
            lines += ["", f"## Workflow ({len(wfs)})"]
            for fp in wfs[:20]:
                lines.append(f"- `{fp.stem}`")
            if not wfs:
                lines.append("- (chưa có workflow)")
        except Exception:  # noqa: BLE001
            pass
        try:
            seen = {}
            for t in deps.store.list_tasks(root, include_archived=False) or []:
                if str(t.get("status") or "") != "done":
                    continue
                key = " ".join(str(t.get("title") or "").lower().split())
                if len(key) < 8 or key.startswith("["):
                    continue
                seen[key] = seen.get(key, 0) + 1
            repeated = sorted(((k, v) for k, v in seen.items() if v >= 2),
                              key=lambda kv: -kv[1])[:10]
            lines += ["", "## Việc tay lặp đã chứng minh (≥2 lần xong)"]
            for k, v in repeated:
                lines.append(f"- {k} (x{v})")
            if not repeated:
                lines.append("- (chưa có)")
        except Exception:  # noqa: BLE001
            pass
        p = Path(root) / "Joyce" / "recipe-gallery.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[factory] recipes {name}: {type(e).__name__}: {e}", file=sys.stderr)
        return False


# ── #13 Self-maintaining harness: proposal WIN + low-risk tự áp ─────────────
#
# Luồng PPC: ky-su-harness viết Joyce/proposals/<date>-<slug>.md → giam-dinh-harness
# chấm ẩn danh → ghi verdict vào frontmatter. Trước đây MỌI proposal đều nằm chờ chủ
# mở tay. OpenAI để Codex tự duy trì skills nội bộ; ở Joyce tương đương = proposal
# "low-risk" (sửa nhỏ, đảo ngược được, chỉ đụng file prompt) sau khi WIN được áp luôn.
# Chốt an toàn: host tự kiểm (không tin lời model) - target phải nằm trong
# _ALLOWED_TARGET_DIRS, file phải TỒN TẠI sẵn (không tạo mới), phải có bản nháp đầy
# đủ, độ dài hợp lý, và nếu file gốc có frontmatter thì bản nháp phải giữ đúng type.


def _proposal_front(text: str) -> tuple:
    """(frontmatter dict, body) hoặc (None, None) khi file không có frontmatter.

    Parser tối thiểu `key: value` tự viết - KHÔNG qua yaml vì factory chạy được cả
    trong môi trường thiếu PyYAML, và frontmatter proposal chỉ cần vài khoá đơn
    (type/status/verdict/risk/target_file). Khoá có giá trị phức tạp (list/dict)
    không nằm trong đề xuất nên không cần đầy đủ YAML.
    """
    if not (text or "").startswith("---"):
        return None, None
    open_end = text.find("\n")
    if open_end < 0:
        return None, None
    close = re.search(r"^---[ \t]*\r?$", text[open_end:], re.M)
    if not close:
        return None, None
    head = text[open_end:open_end + close.start()]
    body = text[open_end + close.end():]
    fm = {}
    for ln in head.split("\n"):
        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", ln.strip())
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm, body


def _extract_draft(body: str) -> str:
    """Nội dung mục '## Bản nháp đầy đủ' - phần duy nhất được phép áp thẳng."""
    m = re.search(r"^##\s+Bản nháp đầy đủ[^\n]*\n", body or "", re.M | re.I)
    if not m:
        return ""
    rest = body[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    draft = (rest[:nxt.start()] if nxt else rest).strip()
    if draft.startswith("```"):
        draft = re.sub(r"^```[a-zA-Z]*\s*\n", "", draft)
        draft = re.sub(r"\n```\s*$", "", draft)
    draft = draft.strip()
    if not draft or draft.lower().startswith("không cần"):
        return ""
    return draft


def _fm_patch(text: str, extra: dict) -> str:
    """Sửa/thêm khoá trong frontmatter, giữ nguyên body."""
    if not (text or "").startswith("---"):
        return text
    open_end = text.find("\n")
    if open_end < 0:
        return text
    close = re.search(r"^---[ \t]*\r?$", text[open_end:], re.M)
    if not close:
        return text
    head = text[open_end:open_end + close.start()]
    body = text[open_end + close.end():]
    out, seen = [], set()
    for ln in head.rstrip("\n").split("\n"):
        m = re.match(r"^([\w-]+)\s*:", ln)
        if m and m.group(1) in extra:
            out.append(f"{m.group(1)}: {extra[m.group(1)]}")
            seen.add(m.group(1))
        else:
            out.append(ln)
    for k, v in extra.items():
        if k not in seen:
            out.append(f"{k}: {v}")
    return "---" + "\n".join(out) + "\n" + body


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _target_relpath(raw) -> str:
    """Chuẩn hoá target_file thành relpath posix an toàn, hoặc '' nếu không hợp lệ."""
    rel = str(raw or "").strip().replace("\\", "/").lstrip("/")
    if not rel or rel.startswith("../") or "/../" in rel or not rel.endswith(".md"):
        return ""
    if not rel.startswith(_ALLOWED_TARGET_DIRS):
        return ""
    return rel


async def _proposal_apply(deps: FactoryDeps, brain: str, root: str, fp: Path,
                          text: str, fm: dict, cfg: dict) -> str:
    """Áp 1 proposal đã qua kiểm. Trả 'applied'|'canary'|'skipped'."""
    rel = _target_relpath(fm.get("target_file"))
    if not rel:
        return "skipped"
    target = (Path(root) / rel).resolve()
    broot = Path(root).resolve()
    if broot not in target.parents or not target.is_file():
        return "skipped"
    _, body = _proposal_front(text)
    draft = _extract_draft(body)
    if not draft or len(draft) < PROPOSAL_MIN_LEN:
        return "skipped"
    original = target.read_text(encoding="utf-8", errors="replace")
    # Ngưỡng "phình bất thường": file nhỏ (prompt vài dòng) vẫn cần được viết lại
    # gọn - chỉ chặn khi draft vượt CẢ 4x lẫn trần tuyệt đối 20KB (file prompt
    # agent/skill hiếm khi quá 20KB; vượt = đáng ngờ, để người duyệt).
    if len(draft) > max(int(len(original) * PROPOSAL_MAX_GROW), 20 * 1024):
        return "skipped"
    # File gốc có frontmatter → bản nháp phải giữ frontmatter cùng `type`
    # (chống model viết bản nháp làm mất schema file agent/skill).
    old_fm, _ = _proposal_front(original)
    if old_fm is not None:
        new_fm, _ = _proposal_front(draft)
        if not isinstance(new_fm, dict) or new_fm.get("type") != old_fm.get("type"):
            return "skipped"

    # Perf harness: bộ eval deterministic (nếu chủ đã khai cho file này) chạy lên
    # bản nháp TRƯỚC khi áp. Case FAIL → không tự áp, đánh dấu eval_failed để chủ
    # thấy đề xuất đã qua đường chứng mà vấp ở đâu.
    ev = eval_for_draft(root, rel, draft)
    if ev and ev["fails"]:
        try:
            fp.write_text(_fm_patch(text, {
                "status": "eval_failed",
                "eval": f"{ev['passed']}/{ev['total']} đạt; rớt: "
                        + ", ".join(ev["fails"][:5])[:180],
            }), encoding="utf-8")
            await deps.inbox(
                f"🧪 **Perf harness**: proposal `{fp.stem}` WIN+low nhưng bản nháp rớt "
                f"{len(ev['fails'])}/{ev['total']} case eval ({', '.join(ev['fails'][:3])}). "
                f"Không tự áp - chờ anh xem.",
                kind="system", label="self-improve", source="factory",
                dedup=f"evalfail:{fp.stem}")
        except Exception:  # noqa: BLE001
            pass
        return "skipped"

    backup_dir = Path(root) / "Joyce" / "proposals" / ".backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    bpath = backup_dir / f"{target.stem}-{int(time.time())}.bak"
    bpath.write_text(original, encoding="utf-8")

    written = draft if draft.endswith("\n") else draft + "\n"
    if deps.atomic_write_text:
        deps.atomic_write_text(target, written)
    else:
        target.write_text(written, encoding="utf-8")

    st = _load_state(deps)
    sharers = []
    for n in deps.brains() or []:
        try:
            r = deps.task_root(str(n))
            if r != str(Path(root)) and (Path(r) / rel).is_file():
                sharers.append(r)
        except Exception:  # noqa: BLE001
            continue
    mode = "canary" if sharers else "direct"
    if sharers:
        st["canaries"].append({
            "id": _sha(f"{root}:{rel}:{time.time()}"),
            "brain": brain, "root": str(Path(root)), "target": rel,
            "slug": target.stem.lower(), "hash": _sha(written),
            "backup": str(bpath), "proposal": fp.name,
            "applied_at": time.time(),
            "promote_at": time.time() + float(cfg.get("canary_hours") or CANARY_DEFAULT_HOURS) * 3600,
            "sharers": sharers, "state": "canary",
        })
        st["canaries"] = st["canaries"][-50:]
        _save_state(deps, st)

    fp.write_text(_fm_patch(text, dict({
        "status": "applied", "applied_by": "factory",
        "applied_mode": mode, "applied_at": time.strftime("%Y-%m-%d %H:%M"),
    }, **({"eval": f"{ev['passed']}/{ev['total']} đạt"} if ev else {}))),
        encoding="utf-8")
    try:
        if mode == "canary":
            await deps.inbox(
                f"🐤 **Canary**: proposal `{fp.stem}` đã tự áp vào `{rel}` ở brain "
                f"{brain} (bản chung {len(sharers)+1} brain). Canh {cfg.get('canary_hours')}h "
                f"rồi mới nhân sang phòng khác; xấu thì tự lật lại.",
                kind="system", label="self-improve", source="factory",
                dedup=f"canary:{fp.stem}")
        else:
            await deps.inbox(
                f"🔧 **Tự cải tiến**: proposal `{fp.stem}` (WIN, low-risk) đã áp vào "
                f"`{rel}` - bản cũ lưu tại `Joyce/proposals/.backup/`, muốn lật lại thì "
                f"copy bản backup đè lên.",
                kind="system", label="self-improve", source="factory",
                dedup=f"apply:{fp.stem}:{fp.stat().st_mtime_ns}")
    except Exception:  # noqa: BLE001
        pass
    return "canary" if mode == "canary" else "applied"


async def proposal_tick(deps: FactoryDeps) -> dict:
    """Quét Joyce/proposals/ mọi brain: verdict=win + risk=low → tự áp (self-improve)."""
    rep = {"scanned": 0, "applied": 0, "canary": 0}
    for name in deps.brains() or []:
        try:
            root = deps.task_root(str(name))
            cfg = load_factory_cfg(root)
            if not cfg.get("self_improve"):
                continue
            pdir = Path(root) / "Joyce" / "proposals"
            if not pdir.is_dir():
                continue
            for fp in sorted(pdir.glob("*.md")):
                try:
                    if fp.stat().st_size > PROPOSAL_MAX_BYTES:
                        continue
                    text = fp.read_text(encoding="utf-8", errors="replace")
                    fm, _ = _proposal_front(text)
                    if not isinstance(fm, dict):
                        continue
                    if str(fm.get("type") or "") != "proposal":
                        continue
                    if str(fm.get("status") or "").lower() != "pending":
                        continue
                    if str(fm.get("verdict") or "").lower() != "win":
                        continue
                    if str(fm.get("risk") or "").lower() != "low":
                        continue
                    rep["scanned"] += 1
                    mode = await _proposal_apply(deps, str(name), root, fp, text, fm, cfg)
                    if mode == "canary":
                        rep["canary"] += 1
                    elif mode == "applied":
                        rep["applied"] += 1
                except Exception as e:  # noqa: BLE001
                    print(f"[factory] proposal {fp.name}: {type(e).__name__}: {e}",
                          file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[factory] proposals {name}: {type(e).__name__}: {e}", file=sys.stderr)
    return rep


# ── #20 Artifact gallery: index file do task tạo ra ─────────────────────────
#
# "Agents write your artifacts" (OpenAI: slide, sheet, doc là sản phẩm chính).
# Task xong có artifacts → ghi dòng vào Joyce/artifacts-index.md (mới nhất trên
# đầu, giữ 80 dòng) để chủ/agent sau tra "file X do việc nào sinh ra" mà không mò
# kanban từng task.

async def artifact_index(deps: FactoryDeps, root: str, task: dict) -> bool:
    try:
        if str(task.get("status") or "") != "done":
            return False
        arts = [str(a).strip() for a in (task.get("artifacts") or [])
                if str(a or "").strip()][:8]
        if not arts:
            return False
        p = Path(root) / "Joyce" / "artifacts-index.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        entry = (f"- [{time.strftime('%Y-%m-%d %H:%M')}] "
                 f"{str(task.get('title') or '')[:80]} → "
                 + ", ".join(f"`{a}`" for a in arts))
        old = ""
        if p.is_file():
            old = p.read_text(encoding="utf-8", errors="replace")
        lines = [ln for ln in old.split("\n") if ln.startswith("- ")]
        if entry in lines:
            return False
        lines.insert(0, entry)
        head = ("# Artifact index\n\n> Tự duy trì bởi factory - file do các task tạo ra,\n"
                "> mới nhất ở trên. Chi tiết việc xem ở bảng Kanban.\n\n")
        p.write_text(head + "\n".join(lines[:80]) + "\n", encoding="utf-8")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[factory] artifacts {task.get('id')}: {type(e).__name__}: {e}",
              file=sys.stderr)
        return False


# ── #14 Perf harness: eval deterministic TRƯỚC khi áp ───────────────────────
#
# OpenAI đẩy PR qua "Synthetics A/B perf framework" TRƯỚC review để reviewer có
# bằng chứng thay vì chấm cảm quan. Bản Joyce: `Joyce/evals/<slug>.json` - chủ khai
# case kiểm tra deterministic cho file prompt đó. proposal_tick chạy eval lên BẢN
# NHÁP trước khi áp: case nào FAIL thì KHÔNG tự áp (status: eval_failed, chờ chủ),
# còn đạt thì ghi điểm eval vào proposal - giám-định/chủ đều thấy bằng chứng.
#
# Mẫu Joyce/evals/<slug>.json:
#   {"cases": [{"name": "giữ mục Cấm", "check": "contains", "value": "## Cấm"},
#              {"name": "không bỏ frontmatter", "check": "has_key", "value": "type"},
#              {"name": "không quá dài", "check": "max_len", "value": 20000},
#              {"name": "không hứa hẹn", "check": "not_contains", "value": "em sẽ quay lại"}]}

def _eval_cases(root: str, slug: str) -> list:
    try:
        p = Path(root) / "Joyce" / "evals" / f"{slug}.json"
        if not p.is_file():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        cases = data.get("cases") if isinstance(data, dict) else data
        out = []
        for c in (cases or [])[:20]:
            if isinstance(c, dict) and c.get("name") and c.get("check"):
                out.append({"name": str(c["name"])[:80], "check": str(c["check"]),
                            "value": c.get("value")})
        return out
    except Exception:  # noqa: BLE001
        return []


def _eval_run(cases: list, text: str) -> list:
    res = []
    for c in cases:
        chk, val = c["check"], c.get("value")
        try:
            if chk == "contains":
                ok = str(val or "") in text
            elif chk == "not_contains":
                ok = str(val or "") not in text
            elif chk == "has_key":
                ok = bool(re.search(rf"^{re.escape(str(val))}\s*:", text, re.M))
            elif chk == "max_len":
                ok = len(text) <= int(val or 0)
            elif chk == "regex":
                ok = bool(re.search(str(val or ""), text, re.S))
            else:
                ok = None      # check lạ: bỏ qua, không tính fail
            res.append({"name": c["name"], "ok": ok})
        except Exception:  # noqa: BLE001
            res.append({"name": c["name"], "ok": None})
    return res


def eval_for_draft(root: str, rel: str, draft: str) -> Optional[dict]:
    """Chạy eval cases của file mục tiêu lên bản nháp. None = không có bộ eval."""
    cases = _eval_cases(root, Path(rel).stem)
    if not cases:
        return None
    res = _eval_run(cases, draft)
    fails = [r["name"] for r in res if r["ok"] is False]
    return {"total": len(res), "fails": fails,
            "passed": len(res) - len(fails) - sum(1 for r in res if r["ok"] is None)}


# ── Số liệu sống cho tab Sơ đồ ──────────────────────────────────────────────
#
# Tab Sơ đồ vẽ "nhà máy" thành pipeline trực quan; mỗi mắt xích cần MỘT con số thật
# thay vì chữ trang trí. Hàm này gom số đó từ state factory + file Joyce/* + kanban.

def stages_snapshot(deps: FactoryDeps) -> dict:
    st = _load_state(deps)
    w_by = {"watching": 0, "ok": 0, "failed": 0}
    for w in st.get("watches", []):
        s = str(w.get("state") or "")
        if s in w_by:
            w_by[s] += 1
    c_by: dict = {}
    for c in st.get("canaries", []):
        k = str(c.get("state") or "?")
        c_by[k] = c_by.get(k, 0) + 1

    props = {"pending": 0, "applied": 0, "eval_failed": 0, "other": 0}
    verdicts = {"win": 0, "keep": 0, "inconclusive": 0}
    evals_n = ckpt_n = art_lines = 0
    risk_ct = {"low": 0, "standard": 0, "high": 0}
    auto_n = escalated_n = ci_open = pacing_n = 0
    done_24h = blocked_n = active_n = 0
    now = time.time()
    for name in deps.brains() or []:
        try:
            root = deps.task_root(str(name))
            pdir = Path(root) / "Joyce" / "proposals"
            if pdir.is_dir():
                for fp in pdir.glob("*.md"):
                    # README.md được seed sẵn vào mọi brain, không phải proposal thật -
                    # đếm vào "other" làm con số pipeline lệch 60+ mà không ai thấy được.
                    if fp.name.upper().startswith("README"):
                        continue
                    try:
                        if fp.stat().st_size > PROPOSAL_MAX_BYTES:
                            continue
                        fm, _ = _proposal_front(fp.read_text(
                            encoding="utf-8", errors="replace"))
                        s2 = str((fm or {}).get("status") or "").lower()
                        props[s2 if s2 in props else "other"] += 1
                        # Kết quả giám định (win/keep/inconclusive) - "công đoạn
                        # review" hiện ra trên Sơ đồ thay vì chỉ có trạng thái.
                        v2 = str((fm or {}).get("verdict") or "").lower()
                        if v2 in verdicts:
                            verdicts[v2] += 1
                    except Exception:  # noqa: BLE001
                        continue
            ed = Path(root) / "Joyce" / "evals"
            if ed.is_dir():
                evals_n += sum(1 for _ in ed.glob("*.json"))
            cd = Path(root) / "Joyce" / "checkpoints"
            if cd.is_dir():
                ckpt_n += sum(1 for _ in cd.glob("*.md"))
            ax = Path(root) / "Joyce" / "artifacts-index.md"
            if ax.is_file():
                try:
                    art_lines += sum(1 for ln in ax.read_text(
                        encoding="utf-8", errors="replace").split("\n")
                        if ln.startswith("- "))
                except Exception:  # noqa: BLE001
                    pass
            for t in deps.store.list_tasks(root, include_archived=False, limit=400) or []:
                md = t.get("metadata") or {}
                r = str(md.get("risk") or "").lower()
                if r in risk_ct:
                    risk_ct[r] += 1
                if md.get("auto_approved"):
                    auto_n += 1
                if md.get("escalated"):
                    escalated_n += 1
                stt = str(t.get("status") or "")
                if stt == "done" and now - float(t.get("updated_at") or 0) <= 86400:
                    done_24h += 1
                if stt == "blocked":
                    blocked_n += 1
                if stt in ("running", "ready", "todo", "blocked", "review"):
                    active_n += 1
                if (str(t.get("title") or "").startswith("[CI fix]")
                        and stt not in ("done", "cancelled", "archived")):
                    ci_open += 1
                if (stt in ("ready", "todo")
                        and "Giãn nhịp" in str(t.get("block_reason") or "")):
                    pacing_n += 1
        except Exception as e:  # noqa: BLE001
            print(f"[factory] stages {name}: {type(e).__name__}: {e}", file=sys.stderr)
    return {
        "watch": w_by, "canary": c_by,
        "perf_cooldowns": len(st.get("perf_cd") or {}),
        "sev_sent": len(st.get("sev_sent") or {}),
        "proposals": props, "verdicts": verdicts, "evals": evals_n,
        "checkpoints": ckpt_n, "artifacts": art_lines,
        "risk": risk_ct, "auto_approved": auto_n, "escalated": escalated_n,
        "ci_open": ci_open, "pacing_deferred": pacing_n,
        "capacity": {"done_24h": done_24h, "blocked": blocked_n, "active": active_n,
                     "blocked_pct": round(100.0 * blocked_n / active_n, 1) if active_n else 0.0},
    }


def agent_scoreboard(deps: FactoryDeps, root: str) -> list:
    """Bảng điểm hiệu quả từng agent trong MỘT brain: việc được giao riêng cho nó
    (idempotency `agent:<mã>:<slug>`) done/blocked/running + số proposal WIN nhắm
    file của nó (bằng chứng PPC giúp agent tốt hơn). Agent không ai giao việc vẫn
    xuất hiện với điểm 0 để chủ thấy ai "đang đứng ngoài"."""
    out: dict = {}
    adir = Path(root) / "agents"
    if adir.is_dir():
        for fp in sorted(adir.glob("*.md")):
            try:
                if fp.stat().st_size > PROPOSAL_MAX_BYTES:
                    continue
                fm, _ = _proposal_front(fp.read_text(
                    encoding="utf-8", errors="replace"))
                slug = fp.stem
                out[slug] = {"slug": slug,
                             "name": str((fm or {}).get("name") or slug),
                             "role": str((fm or {}).get("role") or "")[:90],
                             "done": 0, "blocked": 0, "running": 0, "open": 0,
                             "wins": 0}
            except Exception:  # noqa: BLE001
                continue
    for t in deps.store.list_tasks(root, include_archived=False, limit=400) or []:
        ik = str(t.get("idempotency_key") or "")
        if not ik.startswith("agent:"):
            continue
        parts = ik[len("agent:"):].split(":")
        slug = parts[1] if len(parts) > 1 else ""
        row2 = out.get(slug)
        if row2 is None:
            continue
        s2 = str(t.get("status") or "")
        if s2 == "done":
            row2["done"] += 1
        elif s2 == "blocked":
            row2["blocked"] += 1
        elif s2 == "running":
            row2["running"] += 1
        else:
            row2["open"] += 1
    pdir = Path(root) / "Joyce" / "proposals"
    if pdir.is_dir():
        for fp in pdir.glob("*.md"):
            try:
                if fp.stat().st_size > PROPOSAL_MAX_BYTES:
                    continue
                fm, _ = _proposal_front(fp.read_text(
                    encoding="utf-8", errors="replace"))
                if not isinstance(fm, dict):
                    continue
                if str(fm.get("verdict") or "").lower() != "win":
                    continue
                tf = str(fm.get("target_file") or "")
                if tf.startswith("agents/") and tf.endswith(".md"):
                    slug = Path(tf).stem
                    if slug in out:
                        out[slug]["wins"] += 1
            except Exception:  # noqa: BLE001
                continue
    rows = list(out.values())
    for r in rows:
        tot = r["done"] + r["blocked"]
        r["score"] = round(100.0 * r["done"] / tot) if tot else None
    rows.sort(key=lambda r: (-(r["done"] or 0), -(r["wins"] or 0), str(r["slug"])))
    return rows


# ── #11 Canary rollout: file chung giữ ở 1 brain, canh rồi mới nhân ─────────

def _canary_bad_signals(deps: FactoryDeps, c: dict) -> list:
    """Task blocked trong cửa sổ canary mà nhắc tới slug file mục tiêu → tín hiệu xấu."""
    slug = str(c.get("slug") or "").lower()
    if not slug:
        return []
    bad = []
    try:
        since = float(c.get("applied_at") or 0)
        for t in deps.store.list_tasks(str(c.get("root")), include_archived=False) or []:
            if str(t.get("status") or "") != "blocked":
                continue
            if float(t.get("updated_at") or 0) < since:
                continue
            hay = " ".join(str(t.get(k) or "") for k in
                           ("title", "intent", "block_reason")).lower()
            if slug in hay:
                bad.append(str(t.get("id") or ""))
    except Exception as e:  # noqa: BLE001
        print(f"[factory] canary scan {c.get('id')}: {type(e).__name__}: {e}", file=sys.stderr)
    return bad[:5]


async def canary_tick(deps: FactoryDeps) -> dict:
    """Tới hạn promote: file còn nguyên + không tín hiệu xấu → nhân sang các brain khác;
    có tín hiệu xấu → rollback file về bản backup; chủ đã đổi tay → superseded, nhường."""
    rep = {"promoted": 0, "reverted": 0, "superseded": 0, "waiting": 0}
    st = _load_state(deps)
    now = time.time()
    changed = False
    for c in st.get("canaries", []):
        if c.get("state") != "canary":
            continue
        if now < float(c.get("promote_at") or 0):
            rep["waiting"] += 1
            continue
        target = Path(str(c.get("root") or "")) / str(c.get("target") or "")
        try:
            cur = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
        except Exception:  # noqa: BLE001
            cur = ""
        if not cur or _sha(cur) != str(c.get("hash") or ""):
            c["state"] = "superseded"   # chủ sửa/xoá tay trong cửa sổ canary → nhường chủ
            changed = True
            rep["superseded"] += 1
            continue
        bad = _canary_bad_signals(deps, c)
        if bad:
            try:
                bp = Path(str(c.get("backup") or ""))
                if bp.is_file():
                    target.write_text(bp.read_text(encoding="utf-8", errors="replace"),
                                      encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                print(f"[factory] canary rollback {c.get('id')}: {type(e).__name__}: {e}",
                      file=sys.stderr)
            c["state"] = "reverted"
            changed = True
            rep["reverted"] += 1
            try:
                await deps.inbox(
                    f"🐤 **Canary lật lại**: `{c.get('target')}` ở {c.get('brain')} làm "
                    f"{len(bad)} việc vấp ngay sau khi áp (đề cập slug `{c.get('slug')}`). "
                    f"Đã trả file về bản cũ - không nhân sang brain khác.",
                    kind="system", label="self-improve", source="factory",
                    dedup=f"canaryrev:{c.get('id')}")
            except Exception:  # noqa: BLE001
                pass
            continue
        # Promote: ghi cùng nội dung sang các brain khác đang có file này
        promoted = 0
        for r in c.get("sharers") or []:
            try:
                dst = Path(r) / str(c.get("target"))
                if dst.is_file():
                    dst.write_text(cur, encoding="utf-8")
                    promoted += 1
            except Exception as e:  # noqa: BLE001
                print(f"[factory] canary promote {r}: {type(e).__name__}: {e}",
                      file=sys.stderr)
        c["state"] = "promoted"
        c["promoted_count"] = promoted
        changed = True
        rep["promoted"] += 1
        try:
            await deps.inbox(
                f"🐤 **Canary qua**: `{c.get('target')}` chạy ổn "
                f"{int((now - float(c.get('applied_at') or now)) / 3600)}h ở "
                f"{c.get('brain')} - đã nhân bản sang {promoted} brain còn lại.",
                kind="system", label="self-improve", source="factory",
                dedup=f"canaryok:{c.get('id')}")
        except Exception:  # noqa: BLE001
            pass
    if changed:
        _save_state(deps, st)
    return rep


# ── #12 Autonomy ratio - "surface area người phải quản" ─────────────────────

def autonomy_stats(deps: FactoryDeps, root: str, days: int = AUTONOMY_DAYS,
                   cap: int = AUTONOMY_CAP) -> dict:
    """% việc xong trong `days` ngày KHÔNG cần người chạm (không operator_move /
    operator_grant trong lịch sử). Đây là KPI thật của factory: người càng ít phải
    can thiệp thì harness càng hiệu quả - đúng cách OpenAI đo "surface area"."""
    out = {"days": days, "finished": 0, "touched": 0, "untouched": 0,
           "ratio": None, "pending_human": 0}
    try:
        cutoff = time.time() - days * 86400
        done = []
        for t in deps.store.list_tasks(root, include_archived=False, limit=2000) or []:
            s = str(t.get("status") or "")
            if s == "done" and float(t.get("updated_at") or 0) >= cutoff:
                done.append(t)
            elif s in ("review", "blocked"):
                out["pending_human"] += 1
        done.sort(key=lambda x: float(x.get("updated_at") or 0))
        done = done[-cap:]
        out["finished"] = len(done)
        bulk = {}
        try:
            bulk = deps.store.list_events_bulk(
                [str(t.get("id")) for t in done], limit=50) or {}
        except Exception:  # noqa: BLE001
            bulk = {}
        for t in done:
            evs = bulk.get(str(t.get("id"))) or []
            if any(str(e.get("event_type") or "") in _HUMAN_EVENTS for e in evs):
                out["touched"] += 1
        out["untouched"] = out["finished"] - out["touched"]
        if out["finished"]:
            out["ratio"] = round(out["untouched"] / out["finished"], 3)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] autonomy {root}: {type(e).__name__}: {e}", file=sys.stderr)
    return out


# ── Hook nối vào tasks._run_worker (sau complete) ───────────────────────────

async def post_task(deps: FactoryDeps, root: str, task: dict) -> None:
    """Gọi ở finally của worker khi việc rơi vào done/review/blocked.
    CI babysit (fix loop) → đăng ký watcher → gợi ý lặp. Không ném - đây là
    đường phụ, lỗi ở đây không được nuốt báo cáo chính."""
    try:
        await ci_babysit(deps, root, task)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] ci hook: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        await watch_register(deps, root, task)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] watch hook: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        await discovery_suggest(deps, root, task)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] discovery hook: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        await artifact_index(deps, root, task)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] artifacts hook: {type(e).__name__}: {e}", file=sys.stderr)


# ── Nhịp định kỳ (scheduler gọi mỗi ~5p) ────────────────────────────────────

_last_pattern = [0.0]


async def tick(deps: FactoryDeps) -> dict:
    """Watcher mỗi lần tick; pattern+recipes mỗi giờ. Trả report gộp."""
    rep = {}
    rep["watch"] = await watch_tick(deps)
    now = time.time()
    if now - _last_pattern[0] >= PATTERN_TICK_SECONDS:
        _last_pattern[0] = now
        rep["pattern"] = await pattern_tick(deps)
        try:
            rep["proposals"] = await proposal_tick(deps)
        except Exception as e:  # noqa: BLE001
            print(f"[factory] proposals tick: {type(e).__name__}: {e}", file=sys.stderr)
        try:
            rep["canary"] = await canary_tick(deps)
        except Exception as e:  # noqa: BLE001
            print(f"[factory] canary tick: {type(e).__name__}: {e}", file=sys.stderr)
        done_b = []
        for name in deps.brains() or []:
            try:
                root = deps.task_root(str(name))
                if write_recipes(deps, str(name), root):
                    done_b.append(str(name))
            except Exception as e:  # noqa: BLE001
                print(f"[factory] recipes {name}: {type(e).__name__}: {e}", file=sys.stderr)
        rep["recipes"] = done_b
    return rep


def enabled(settings: dict) -> bool:
    """Công tắc tổng: settings.factory.enabled (mặc định bật)."""
    return bool(((settings or {}).get("factory") or {}).get("enabled", True))
