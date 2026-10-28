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
import uuid
import os
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
CANARY_MIN_TASKS = 20              # và phải có đủ ngần ấy việc ĐÃ CHẠY trên bản ứng viên (FIX-05, plan mục 9.1)
CANARY_HET_HAN_NGAY = 14          # chờ bằng chứng quá lâu thì dừng, báo chủ, KHÔNG nhân
CANARY_LOI_THU_LAI = 3            # một đích ghi lỗi được thử lại ngần ấy lần rồi bỏ
STATE_SCHEMA = 2                  # 1.3.42 (A01): có phiên bản; canary cũ chưa có telemetry chuyển legacy_review
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


def _migrate_state(d: dict) -> dict:
    """Đưa state về STATE_SCHEMA. CHẠY LẶP KHÔNG ĐỔI KẾT QUẢ (cổng là `schema`) và KHÔNG chạm vào file nào của brain.

    A01 (1.3.42): canary tạo trước khi có telemetry không có gì chứng minh bản ứng viên đã chạy ra sao, nên không được tiếp
    tục "canh" như thể đang kiểm chứng. Chuyển sang `legacy_review` (chờ chủ xem). Bản ghi gốc giữ NGUYÊN trong `legacy`
    (nguồn, hash, sao lưu, các đích), không tự giữ hay xoá ứng viên, không tự viết lại file nguồn."""
    if int(d.get("schema") or 1) >= STATE_SCHEMA:
        return d
    for c in d.get("canaries", []):
        if c.get("state") == "canary" and "legacy" not in c:
            c["legacy"] = {"state": "canary", "luc": time.time(), "ly_do": "tạo trước khi có telemetry để kiểm chứng canary"}
            c["state"] = "legacy_review"
    d["schema"] = STATE_SCHEMA
    return d


TRAN_AP_TUAN = 2                 # chủ chốt 28/10/2026: số lượt tự cải tiến tối đa mỗi file mỗi 7 ngày
TELEMETRY_MIN_RUNS = 5          # số lượt chạy tối thiểu trong cửa sổ để coi là "quan sát được"
TELEMETRY_CUA_SO_NGAY = 30


def telemetry_ready(deps: FactoryDeps, brain: str = "", rel: str = "") -> bool:
    """Có nguồn bằng chứng đáng tin để kiểm chứng một canary của file này chưa (D1).

    Từ 1.3.43 (B01) là phép kiểm THẬT trên sổ lượt chạy do host ghi: file phải là `agents/<slug>.md` và agent đó phải có ít nhất
    `TELEMETRY_MIN_RUNS` lượt chạy có revision đọc được trong `TELEMETRY_CUA_SO_NGAY` ngày ở brain này. Có lượt chạy chưa phải là
    đã đạt: canary vẫn chỉ nhân khi đủ lượt được KIỂM CHỨNG đạt (xem `_canary_evidence`). Hàm này chỉ trả lời "có quan sát được
    không". Không phải cờ cấu hình; test dùng monkeypatch có chủ ý. Lỗi đọc sổ là False (không biết thì không mở)."""
    try:
        m = re.match(r"^agents/([^/]+)\.md$", str(rel or "").replace("\\", "/"))
        if not m or not brain:
            return False
        import run_ledger
        rs = run_ledger.danh_sach(brain_id=str(brain), agent_id=m.group(1), tu=time.time() - TELEMETRY_CUA_SO_NGAY * 86400, gioi_han=200)
        return sum(1 for r in rs if r.get("agent_revision")) >= TELEMETRY_MIN_RUNS
    except Exception:  # noqa: BLE001
        return False


def telemetry_quan_sat_duoc() -> int:
    """Số trợ lý (theo brain) đang quan sát được: cùng ngưỡng với `telemetry_ready`. Cho đèn tổng ở Sơ đồ; 0 nghĩa là chưa trợ lý nào."""
    try:
        import run_ledger
        return run_ledger.agent_quan_sat_duoc(tu=time.time() - TELEMETRY_CUA_SO_NGAY * 86400, toi_thieu=TELEMETRY_MIN_RUNS)
    except Exception:  # noqa: BLE001
        return 0


def _so_lan_ap_tuan(deps: FactoryDeps, root: str, rel: str, bo_qua: Optional[Path] = None) -> int:
    """Số lần file `rel` ở brain `root` đã được TỰ áp trong 7 ngày qua, đếm từ chính các file đề xuất có trạng thái `applied` (áp thẳng hay
    qua canary đều đánh dấu như nhau). Giờ lấy từ `applied_at` host đã ghi, rơi về giờ sửa file nếu không đọc được. Đề xuất đang xét
    (`bo_qua`) không tự đếm mình. Không tin lời model."""
    now = time.time()
    n = 0
    try:
        pdir = Path(root) / "Joyce" / "proposals"
        for fp in pdir.glob("*.md") if pdir.is_dir() else []:
            if bo_qua is not None and fp.resolve() == Path(bo_qua).resolve():
                continue
            if fp.stat().st_size > PROPOSAL_MAX_BYTES:
                continue
            fm, _ = _proposal_front(fp.read_text(encoding="utf-8", errors="replace"))
            if not (isinstance(fm, dict) and str(fm.get("status") or "").lower() == "applied" and _target_relpath(fm.get("target_file")) == rel):
                continue
            try:
                luc = time.mktime(time.strptime(str(fm.get("applied_at")), "%Y-%m-%d %H:%M"))
            except (ValueError, TypeError, OverflowError):
                luc = fp.stat().st_mtime
            if now - luc <= 7 * 86400:
                n += 1
    except OSError:
        pass
    return n


def _dang_tam_dung(deps: FactoryDeps, cfg: Optional[dict] = None) -> bool:
    if cfg is not None and cfg.get("auto_deploy") is False:
        return True
    return bool(_load_state(deps).get("tam_dung"))


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
                return _migrate_state(d)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] đọc state: {type(e).__name__}: {e}", file=sys.stderr)
    return {"watches": [], "perf_cd": {}, "sev_sent": {}, "canaries": [], "schema": STATE_SCHEMA}


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
        # Chủ đặt true thì brain này KHÔNG tự áp đề xuất cho file chưa có bộ eval (FIX-02). Mặc định tắt: giữ
        # hành vi cũ cho 61 brain đang chạy, chỉ bộ eval HỎNG mới chặn.
        "eval_bat_buoc": bool(cfg.get("eval_bat_buoc", False)),
        # Cờ DỪNG tự triển khai (A01): false thì không tự áp và không tự nhân. KHÔNG tắt giám định, đọc, tạo đề xuất,
        # thử trong sandbox hay phục vụ bằng bản đã duyệt. Mặc định bật như trước.
        "auto_deploy": bool(cfg.get("auto_deploy", True)),
        "canary_hours": max(1, min(24 * 14, int(cfg.get("canary_hours", CANARY_DEFAULT_HOURS)))),
        "canary_min_tasks": max(1, min(200, int(cfg.get("canary_min_tasks", CANARY_MIN_TASKS)))),
        # Chủ chốt 28/10/2026: tối đa 2 lượt tự cải tiến mỗi file mục tiêu mỗi 7 ngày. 0 = không giới hạn (chỉ chủ đặt tay).
        "max_ap_tuan": max(0, min(50, int(cfg.get("max_ap_tuan", TRAN_AP_TUAN)))),
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
    # Bản nháp trong khối ```: lấy tới dấu đóng khối mà sau nó là hết file hoặc mục `## ` kế tiếp.
    # Trước 1.3.39 cắt ở `## ` đầu tiên, tức cắt cụt ngay ở mục `## Quy trình` TRONG thân agent.
    if rest.lstrip().startswith("```"):
        for f in re.finditer(r"^```[ \t]*\r?$", rest, re.M):
            sau = rest[f.end():].lstrip()
            if not sau or sau.startswith("## "):
                rest = rest[:f.end()]
                break
        else:
            nxt = re.search(r"^##\s+", rest, re.M)
            rest = rest[:nxt.start()] if nxt else rest
        draft = rest.strip()
    else:
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
    # PHẢI giữ dòng đóng `---`. Bản trước (có từ 1.3.38) bỏ nó, nên mọi đề xuất từng bị đổi trạng thái mất khả năng đọc lại
    # frontmatter ở lượt quét sau (`_proposal_front` trả None). Phát hiện khi A02 bắt đầu ghi dấu vào đề xuất đang pending.
    return "---" + "\n".join(out) + "\n---" + body


def _sha(text: str) -> str:
    """Hash NGẮN (16 ký tự) giữ cho bản ghi cũ và hiển thị. Hash mới dùng `_sha256`."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _sha256(text: str) -> str:
    """SHA-256 ĐẦY ĐỦ (64 ký tự) của văn bản. A02 (1.3.42): bản ghi triển khai mới lưu hash đầy đủ, chỉ rút ngắn khi hiển thị.

    Tính trên văn bản đã đọc bằng `read_text` (xuống dòng chuẩn hoá về `\\n`), nhất quán với mọi chỗ so sánh trong module này.
    Chưa phải hash bytes đĩa; writer dùng chung của A05 sẽ ghi bytes xác định rồi đối chiếu."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _khop(text: Optional[str], day_du: str = "", ngan: str = "") -> bool:
    """Văn bản có đúng bằng hash đã lưu không. Ưu tiên SHA-256 đầy đủ; bản ghi cũ chỉ có hash ngắn thì so hash ngắn."""
    if text is None:
        return False
    if day_du:
        return _sha256(text) == day_du
    return bool(ngan) and _sha(text) == ngan


def _target_relpath(raw) -> str:
    """Chuẩn hoá target_file thành relpath posix an toàn, hoặc '' nếu không hợp lệ."""
    rel = str(raw or "").strip().replace("\\", "/").lstrip("/")
    if not rel or rel.startswith("../") or "/../" in rel or not rel.endswith(".md"):
        return ""
    if not rel.startswith(_ALLOWED_TARGET_DIRS):
        return ""
    return rel


# So sánh quyền theo CÂY YAML nằm ở `harness_diff` (1.3.41, FIX-01 của gói G1). Bản 1.3.39 lọc dòng rồi sắp
# xếp nên bỏ sót khoá lồng (`harness.budgets.*`) và việc tráo `tools` giữa hai bước. Chỗ này chỉ giữ tên cũ
# để mã và test đã trỏ vào `factory.diff_quyen` / `factory._KHOA_QUYEN` không phải đổi.
import harness_diff  # noqa: E402
import deploy_writer  # noqa: E402
from harness_diff import classify as _phan_loai  # noqa: E402

_KHOA_QUYEN = harness_diff.KHOA_QUYEN
KHONG_DOC_DUOC = harness_diff.KHONG_DOC_DUOC


def diff_quyen(original: str, draft: str) -> list:
    """Tên các khoá quyền bị đổi giữa bản gốc và bản nháp (rỗng = chỉ đổi nội dung).

    Trả `[KHONG_DOC_DUOC]` khi không đọc chắc được cấu hình: coi như CẦN CHỦ XEM, không bao giờ tự áp."""
    return harness_diff.diff_quyen(original, draft)


def _brain_chung(deps: FactoryDeps, root: str, rel: str) -> list:
    """Gốc các brain KHÁC cũng có file `rel` (file dùng chung)."""
    ra = []
    for n in deps.brains() or []:
        try:
            r = deps.task_root(str(n))
            if r != str(Path(root)) and (Path(r) / rel).is_file():
                ra.append(r)
        except Exception:  # noqa: BLE001
            continue
    return ra


async def _cho_chu(deps: FactoryDeps, fp: Path, text: str, trang_thai: str, ly_do: str, tin: str, dedup: str) -> str:
    """Đánh dấu một đề xuất sang trạng thái chờ chủ, ghi lý do, báo hộp thư một lần. Luôn trả 'skipped'."""
    try:
        # `quyet_dinh` là mã ổn định lấy từ khoá chống trùng (quyen:<id>:<loai>, stale:, telemetry:, type:) để Sơ đồ đếm lý do chờ
        # mà không phải đoán từ câu chữ tiếng Việt của lý do.
        ma = str(dedup or "").split(":")
        quyet_dinh = ma[0] + (":" + ma[2] if ma[0] == "quyen" and len(ma) > 2 else "")
        fp.write_text(_fm_patch(text, {"status": trang_thai, "ly_do_cho": ly_do[:180], "quyet_dinh": quyet_dinh}), encoding="utf-8")
        await deps.inbox(tin, kind="system", label="self-improve", source="factory", dedup=dedup)
    except Exception:  # noqa: BLE001
        pass
    return "skipped"


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
            # Trước 1.3.42 chặn NÀY im lặng: đề xuất nằm `pending` mãi, chủ không biết vì sao không được áp. Nay chuyển sang
            # chờ chủ kèm lý do (cùng lớp bảo vệ, chỉ thêm khả năng nhìn thấy).
            return await _cho_chu(
                deps, fp, text, "cho_chu_duyet",
                "bản nháp không giữ được frontmatter hoặc đổi `type` của file (không đọc chắc được cấu hình)",
                f"🔐 **Tự cải tiến**: proposal `{fp.stem}` đổi `{rel}` nhưng bản nháp mất frontmatter hoặc đổi `type`. "
                f"Không tự áp - chờ anh xem.", f"type:{fp.stem}")

    # A02: bản nháp đã được xem khi nguồn ở phiên bản X thì không được ghi lên nguồn đã đổi sang phiên bản khác. Host đóng dấu
    # `reviewed_source_hash` lần đầu thấy đề xuất (xem proposal_tick); đề xuất chưa có dấu (viết trước 1.3.42) thì đóng dấu
    # ngay bây giờ, tức là chỉ chắc chắn từ lúc này.
    xem = str(fm.get("reviewed_source_hash") or "")
    if xem and xem != _sha256(original):
        return await _cho_chu(
            deps, fp, text, "cho_chu_duyet",
            "bản nguồn đã đổi sau khi đề xuất được xem (stale), cần giám định lại trên bản hiện tại",
            f"🔐 **Tự cải tiến**: proposal `{fp.stem}` được xem khi `{rel}` còn ở phiên bản cũ; sau đó file đã đổi. "
            f"Không ghi đè bản hiện tại - chờ anh xem hoặc giám định lại.", f"stale:{fp.stem}")

    # CỔNG HOST (A01, 1.3.42), áp cho CẢ direct lẫn canary và chạy TRƯỚC mọi thao tác ghi. Host tự phân loại, không tin
    # `risk: low` hay `verdict: win` do model viết (B-12). Chỉ `display_only` được qua; mọi loại khác, kể cả loại chưa phân
    # loại được, chờ chủ. Thân bài, `role`, `name`, `description`, `goal`, lời giao việc là HÀNH VI (D3).
    if _dang_tam_dung(deps, cfg):
        return "paused"      # cờ dừng tự triển khai: giữ nguyên đề xuất, KHÔNG đổi trạng thái, KHÔNG tắt giám định hay phục vụ
    tran = int(cfg.get("max_ap_tuan", TRAN_AP_TUAN) or 0)
    if tran:
        da = _so_lan_ap_tuan(deps, root, rel, fp)
        if da >= tran:
            return await _cho_chu(
                deps, fp, text, "cho_chu_duyet", f"file này đã tự cải tiến {da} lần trong 7 ngày (trần {tran} lần mỗi tuần mỗi file)",
                f"⏱️ **Tự cải tiến**: proposal `{fp.stem}` sửa `{rel}` nhưng file này đã được tự cải tiến {da} lần trong 7 ngày qua "
                f"(trần anh chốt: {tran} lần mỗi tuần). Không tự áp - chờ anh xem.", f"tuan:{fp.stem}")
    pl = _phan_loai(original, draft)
    loai = pl["class"]
    if loai != "display_only":
        ten = [t for c in ("permission_change", "unknown", "behavior_change", "invalid") for t in pl["paths"][c]]
        if loai == "invalid":
            ly_do = "không đọc chắc được cấu hình (frontmatter), cần anh xem: " + "; ".join(pl["errors"][:2])
            tin = f"🔐 **Tự cải tiến**: proposal `{fp.stem}` đổi `{rel}` nhưng cấu hình không đọc chắc được. Không tự áp - chờ anh xem."
        elif loai == "behavior_change":
            ly_do = "đổi hành vi (thân bài, vai trò, lời giao việc hoặc cấu trúc): " + ", ".join(pl["paths"]["behavior_change"][:5])
            tin = (f"🧭 **Tự cải tiến**: proposal `{fp.stem}` thắng giám định nhưng đổi hành vi của `{rel}` "
                   f"({', '.join(pl['paths']['behavior_change'][:5])}). Chưa có bộ kiểm hành vi nên chưa tự áp - chờ anh xem.")
        else:
            ly_do = "đổi trường quyền hoặc cách chạy: " + ", ".join(ten)
            tin = (f"🔐 **Tự cải tiến**: proposal `{fp.stem}` thắng giám định nhưng đổi {', '.join(ten[:5])} của `{rel}`. "
                   f"Thay đổi về quyền không tự áp - chờ anh xem.")
        return await _cho_chu(deps, fp, text, "cho_chu_duyet", ly_do, tin, f"quyen:{fp.stem}:{loai}")

    # Thay đổi dùng chung nhiều brain cần canary, mà canary cần telemetry (D1): chưa có thì KHÔNG tự đưa vào nguồn.
    chung = _brain_chung(deps, root, rel)
    if chung and not telemetry_ready(deps, brain, rel):
        return await _cho_chu(
            deps, fp, text, "cho_chu_duyet",
            f"file dùng chung {len(chung) + 1} brain, chưa có telemetry để canary kiểm chứng (D1)",
            f"🐤 **Tự cải tiến**: proposal `{fp.stem}` sửa `{rel}` dùng chung {len(chung) + 1} brain, mà chưa có dữ liệu chạy thật "
            f"để canary kiểm chứng. Không tự áp, không tự nhân - chờ anh xem.", f"telemetry:{fp.stem}")

    # Perf harness: bộ eval deterministic (nếu chủ đã khai cho file này) chạy lên bản nháp TRƯỚC khi áp.
    # FIX-02 (1.3.41): bộ eval HỎNG, hoặc thiếu khi chủ đặt bắt buộc, cũng CHẶN, không được hiểu là "không có eval".
    # A04 (1.3.42): lỗi khi CHẠY evaluator cũng là chặn (trước đây một exception ở đây làm cả lượt quét báo lỗi và đề xuất kẹt
    # pending không ai biết). Mọi kết quả gắn băm bản nháp và băm file eval để kết quả cũ không dùng cho bản khác.
    written = draft if draft.endswith("\n") else draft + "\n"
    try:
        ev = eval_for_draft(root, rel, draft, bat_buoc=bool(cfg.get("eval_bat_buoc") is True))
    except Exception as e:  # noqa: BLE001
        ev = {"status": "invalid", "ket_qua": "invalid", "loai": "chuoi", "eval_revision": "", "total": 0, "passed": 0, "read": 0,
              "fails": [], "errors": [f"lỗi khi chạy evaluator: {type(e).__name__}"]}
    dau_eval = {}
    if ev:
        dau_eval = {"eval_candidate_hash": _sha256(written), "eval_revision": ev.get("eval_revision") or "",
                    "eval_loai": ev.get("loai") or "chuoi", "eval_hanh_vi": "chua_co"}
    if ev and ev.get("status") != "valid":
        try:
            ly_do = "; ".join(ev.get("errors") or [])[:170]
            fp.write_text(_fm_patch(text, {
                "status": "eval_failed",
                "eval": (f"bộ eval không dùng được ({ev['ket_qua']}): " + ly_do)[:180], **dau_eval,
            }), encoding="utf-8")
            await deps.inbox(
                f"🧪 **Perf harness**: proposal `{fp.stem}` không tự áp vì bộ eval của `{rel}` không dùng được "
                f"({ly_do}). Giữ nguyên bản hiện tại - chờ anh sửa bộ eval hoặc xem đề xuất.",
                kind="system", label="self-improve", source="factory",
                dedup=f"evalbad:{fp.stem}")
        except Exception:  # noqa: BLE001
            pass
        return "skipped"
    if ev and ev["fails"]:
        try:
            fp.write_text(_fm_patch(text, {
                "status": "eval_failed",
                "eval": f"{ev['passed']}/{ev['total']} đạt; rớt: "
                        + ", ".join(ev["fails"][:5])[:180], **dau_eval,
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

    # A05 (1.3.42): MỘT writer chung. Khoá liên tiến trình, so-rồi-ghi theo hash bản đã xem, sao lưu tên duy nhất, nhật ký
    # prepared/committed, ghi nguyên tử bằng bytes xác định. Dùng đường dẫn CHƯA giải để thấy symlink/junction ở giữa đường.
    deployment_id = uuid.uuid4().hex
    try:
        rc = _ghi_dich(deps, root, Path(root) / rel, written, deployment_id=deployment_id, target_id="nguon", truoc_hash=_sha256(original))
    except deploy_writer.DuongKhongAnToan as e:
        return await _cho_chu(deps, fp, text, "cho_chu_duyet", f"đường dẫn đích có liên kết hoặc nằm ngoài brain: {e}"[:180],
                              f"🔐 **Tự cải tiến**: proposal `{fp.stem}` không tự áp vì đường dẫn của `{rel}` có liên kết (symlink hoặc "
                              f"junction) hoặc nằm ngoài brain. Chờ anh xem.", f"duong:{fp.stem}")
    except Exception as e:  # noqa: BLE001
        print(f"[factory] áp {rel}: {type(e).__name__}: {e}", file=sys.stderr)
        return "skipped"
    if rc.get("ket_qua") != "committed":
        return await _cho_chu(deps, fp, text, "cho_chu_duyet", "bản nguồn đã đổi giữa lúc kiểm và lúc ghi, không ghi đè",
                              f"🔐 **Tự cải tiến**: proposal `{fp.stem}` bị dừng vì `{rel}` vừa đổi đúng lúc sắp ghi. "
                              f"Không ghi đè - chờ anh xem.", f"doi-luc-ghi:{fp.stem}")
    bpath = rc["backup"]

    sharers = chung
    mode = "canary" if sharers else "direct"
    if sharers:
        # FIX-04 (1.3.41): chụp hash TỪNG đích ngay lúc áp. Lúc nhân chỉ ghi đích còn đúng bản này; đích đã bị chủ
        # sửa riêng kể từ đó là xung đột và được giữ nguyên.
        # A02 (1.3.42, D2 của chủ): đích CHỈ được tự nhân khi nội dung của nó ĐÚNG BẰNG bản nguồn TRƯỚC khi sửa (baseline chung).
        # Đích khác baseline từ trước là `override` (phòng có biến thể riêng), chờ chủ. Cùng tên file chưa đủ để chứng minh kế
        # thừa; hệ chưa có khái niệm package nên `package_id` để trống thay vì tự khai.
        goc_h = _sha256(original)
        targets = []
        for r in sharers:
            d = _doc_file(Path(r) / rel)
            oh = _sha256(d) if d is not None else ""
            if d is None:
                qh, tt = "thieu", "missing"
            elif oh == _sha256(written):
                qh, tt = "da_bang_ung_vien", "pending"   # đã đúng bản mới từ trước: sẽ ghi nhận `already`, không có receipt
            elif oh == goc_h:
                qh, tt = "ke_thua", "pending"
            else:
                qh, tt = "override", "override"
            targets.append({"root": r, "target_observed_hash": oh, "base_hash": _sha(d) if d is not None else "",
                            "quan_he": qh, "state": tt, "tries": 0})
        with _khoa_state(deps):
            st = _load_state(deps)           # đọc lại TRONG khoá: worker khác có thể vừa ghi
            st["canaries"].append({
                "id": _sha(f"{root}:{rel}:{time.time()}"), "deployment_id": deployment_id, "schema_version": STATE_SCHEMA,
                "package_id": None,
                "brain": brain, "root": str(Path(root)), "target": rel,
                "slug": target.stem.lower(), "hash": _sha(written), "revision": _sha(written),
                "source_baseline_hash": goc_h, "candidate_hash": _sha256(written),
                "backup": str(bpath), "proposal": fp.name,
                "applied_at": time.time(),
                "promote_at": time.time() + float(cfg.get("canary_hours") or CANARY_DEFAULT_HOURS) * 3600,
                "min_tasks": int(cfg.get("canary_min_tasks") or CANARY_MIN_TASKS),
                "sharers": sharers, "targets": targets, "state": "canary",
            })
            st["canaries"] = _cat_canary(st["canaries"])
            _save_state(deps, st)

    fp.write_text(_fm_patch(text, dict({
        "status": "applied", "applied_by": "factory",
        "applied_mode": mode, "applied_at": time.strftime("%Y-%m-%d %H:%M"),
    }, **({"eval": f"{ev['passed']}/{ev['total']} đạt", **dau_eval} if ev else {}))),
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
    rep = {"scanned": 0, "applied": 0, "canary": 0, "paused": 0}
    _doi_soat(deps)
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
                    # A02: đóng dấu bản nguồn LẦN ĐẦU thấy đề xuất, trước cả khi nó có verdict. Giám định có thể kéo dài; nguồn đổi
                    # trong lúc đó thì _proposal_apply nhận ra. Chỉ ghi khi chưa có dấu; giám định viết lại frontmatter làm mất
                    # dấu thì lần quét sau đóng dấu lại (chắc chắn yếu hơn, ghi ở plan).
                    if not fm.get("reviewed_source_hash"):
                        rel0 = _target_relpath(fm.get("target_file"))
                        nguon0 = _doc_file(Path(root) / rel0) if rel0 else None
                        if nguon0 is not None:
                            dau = _sha256(nguon0)
                            text = _fm_patch(text, {"reviewed_source_hash": dau})
                            fp.write_text(text, encoding="utf-8")
                            fm["reviewed_source_hash"] = dau
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
                    elif mode == "paused":
                        rep["paused"] += 1
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

EVAL_MAX_CASES = 20             # quá số này là bộ hỏng, KHÔNG cắt âm thầm còn 20 ca rồi cho qua
EVAL_MAX_BYTES = 256 * 1024
_EVAL_CHECK_CAN_GIA_TRI = ("contains", "not_contains", "has_key", "max_len", "regex")


def eval_load(root: str, slug: str) -> dict:
    """Đọc bộ eval của một file mục tiêu. Luôn trả một dict có `status`, không bao giờ trả "rỗng" cho lỗi.

    Trước 1.3.41 hàm này nuốt mọi lỗi và trả `[]`, nên JSON hỏng, root sai kiểu hay ca thiếu `check` đều bị
    hiểu là "chủ chưa khai eval" rồi bản nháp được áp (FIX-02, JHA-02).

        status "missing"  không có file (không phải lỗi; chỉ chặn khi `eval_bat_buoc`)
        status "invalid"  có file mà không dùng được: `errors` nêu từng lỗi, `cases` rỗng
        status "valid"    `cases` dùng được, `read` = số ca đọc

    Không bỏ ca nào âm thầm: MỘT ca sai là cả bộ invalid. Không tự sửa đáp án để cho qua."""
    out = {"status": "missing", "cases": [], "read": 0, "errors": [], "revision": ""}
    p = Path(root) / "Joyce" / "evals" / f"{slug}.json"
    try:
        if not p.is_file():
            return out
        out["status"] = "invalid"
        if p.stat().st_size > EVAL_MAX_BYTES:
            out["errors"].append(f"file eval lớn hơn {EVAL_MAX_BYTES // 1024}KB")
            return out
        raw = p.read_text(encoding="utf-8")
        out["revision"] = _sha256(raw)       # phiên bản của CHÍNH file eval: sửa nó thì kết quả chấm cũ hết hợp lệ
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        out["status"] = "invalid"
        out["errors"].append(f"không đọc được file eval: {type(e).__name__}")
        return out
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list):
        out["errors"].append("`cases` phải là danh sách (hoặc cả file là danh sách các ca)")
        return out
    out["read"] = len(cases)
    if not cases:
        out["errors"].append("bộ eval rỗng: file có mà không có ca nào")
        return out
    if len(cases) > EVAL_MAX_CASES:
        out["errors"].append(f"quá số ca cho phép ({len(cases)} > {EVAL_MAX_CASES})")
        return out
    ok = []
    for i, c in enumerate(cases, 1):
        if not isinstance(c, dict):
            out["errors"].append(f"ca {i}: không phải mapping")
            continue
        ten, chk, val = c.get("name"), c.get("check"), c.get("value")
        ma = str(ten)[:60] if isinstance(ten, str) and ten.strip() else f"#{i}"
        if not (isinstance(ten, str) and ten.strip()):
            out["errors"].append(f"ca {i}: thiếu name")
        if not (isinstance(chk, str) and chk.strip()):
            out["errors"].append(f"ca {ma}: thiếu check")
            continue
        if chk in _EVAL_CHECK_CAN_GIA_TRI:
            if chk == "max_len":
                if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
                    out["errors"].append(f"ca {ma}: max_len cần số nguyên dương")
                    continue
            elif not isinstance(val, str) or not val:
                out["errors"].append(f"ca {ma}: check {chk} cần value là chuỗi không rỗng")
                continue
            elif chk == "regex":
                try:
                    if len(val) > 500:
                        raise ValueError("quá dài")
                    re.compile(val, re.S)
                except Exception:  # noqa: BLE001
                    out["errors"].append(f"ca {ma}: regex không biên dịch được hoặc quá dài")
                    continue
        if isinstance(ten, str) and ten.strip():
            ok.append({"name": ten[:80], "check": chk, "value": val})
    if out["errors"]:
        return out
    out.update(status="valid", cases=ok)
    return out


def _eval_cases(root: str, slug: str) -> list:
    """Giữ tên cũ cho mã đã trỏ vào: chỉ trả các ca của bộ HỢP LỆ. Muốn biết vì sao rỗng thì gọi `eval_load`."""
    return eval_load(root, slug)["cases"]


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


def eval_for_draft(root: str, rel: str, draft: str, bat_buoc: bool = False) -> Optional[dict]:
    """Chạy bộ eval của file mục tiêu lên bản nháp.

    None = không khai eval và không bắt buộc (không có gì để kiểm). Còn lại luôn là dict có `ket_qua` thuộc bốn trạng thái của
    A04 cộng một biến thể: `valid_pass`, `valid_fail`, `invalid` (bộ hỏng, có `errors`), `missing_required` (chủ đặt
    `eval_bat_buoc` mà không có file). `status` giữ nguyên nghĩa cũ ("valid" | "invalid" | "missing_required") cho chỗ gọi cũ.
    `invalid` và `missing_required` KHÔNG phải "đạt": người gọi phải chặn. `eval_revision` là SHA-256 của file eval.

    Case không kiểm được (loại check lạ, lỗi khi chạy) tính là RỚT kèm nhãn "không kiểm được"
    (1.3.39, Joyce Harness B-10): "không thấy lỗi" không phải "đạt".

    Đây là eval CHUỖI (kiểm tĩnh trên chữ của bản nháp). Nó KHÔNG phải bằng chứng hành vi: `loai = "chuoi"`."""
    ld = eval_load(root, Path(rel).stem)
    base = {"loai": "chuoi", "eval_revision": ld.get("revision") or ""}
    if ld["status"] == "missing":
        if not bat_buoc:
            return None
        return {**base, "status": "missing_required", "ket_qua": "missing_required", "total": 0, "passed": 0, "read": 0, "fails": [],
                "errors": ["chủ đặt eval bắt buộc cho brain này mà file này chưa có bộ eval"]}
    if ld["status"] == "invalid":
        return {**base, "status": "invalid", "ket_qua": "invalid", "total": 0, "passed": 0, "read": ld["read"], "fails": [],
                "errors": ld["errors"]}
    res = _eval_run(ld["cases"], draft)
    fails = [r["name"] for r in res if r["ok"] is False]
    fails += [f"{r['name']} (không kiểm được)" for r in res if r["ok"] is None]
    return {**base, "status": "valid", "ket_qua": "valid_fail" if fails else "valid_pass", "total": len(res), "fails": fails,
            "passed": len(res) - len(fails), "read": ld["read"], "errors": []}


def chinh_sach_eval(cfg: Optional[dict]) -> dict:
    """Chính sách eval HIỆU LỰC của một brain, để giao diện và API nói đúng điều đang chạy (A04).

    D4 nhẹ của chủ (28/10/2026): luôn chặn `invalid` và `valid_fail`; `missing` chỉ chặn khi chủ bật `eval_bat_buoc`. Giá trị lạ
    của `eval_bat_buoc` KHÔNG làm mở cổng: chỉ đúng `True` mới coi là bắt buộc, còn lại về mặc định (không bắt buộc)."""
    bat = (cfg or {}).get("eval_bat_buoc") is True
    return {
        "chan_invalid": True, "chan_fail": True, "chan_missing": bat, "eval_bat_buoc": bat,
        # D3: thay đổi hành vi và quyền chờ chủ ở gói A DÙ eval đạt, nên eval chỉ quyết định ở nhánh hiển thị thuần.
        "hanh_vi_van_cho_chu": True, "loai_eval": "chuoi",
        "ghi_chu": ("Bộ eval hiện là eval CHUỖI (kiểm tĩnh chữ của bản nháp), chưa phải eval hành vi. Đạt eval chuỗi không đủ để tự áp "
                    "thay đổi hành vi: loại thay đổi đó luôn chờ chủ ở gói A. "
                    + ("Thiếu bộ eval cũng chặn tự áp." if bat else "Thiếu bộ eval không bị chặn riêng vì lý do này.")),
    }


def eval_ket_qua_hop_le(fm: Optional[dict], candidate_hash: str, eval_revision: str) -> bool:
    """Kết quả eval đã ghi trên đề xuất còn dùng được cho BẢN NHÁP này và PHIÊN BẢN eval này không (A04).

    Dùng ở mọi đường cần "đã qua eval": kết quả cũ không được áp cho bản nháp khác, và sửa file eval sau lúc chấm thì phải chấm lại.
    Thiếu dấu băm thì không hợp lệ (không suy đoán)."""
    fm = fm or {}
    ch, er = str(fm.get("eval_candidate_hash") or ""), str(fm.get("eval_revision") or "")
    if len(ch) != 64 or len(er) != 64:
        return False
    return ch == candidate_hash and er == eval_revision


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

    props = {"pending": 0, "applied": 0, "eval_failed": 0, "cho_chu_duyet": 0, "other": 0}
    verdicts = {"win": 0, "keep": 0, "inconclusive": 0}
    evals_n = ckpt_n = art_lines = 0
    risk_ct = {"low": 0, "standard": 0, "high": 0}
    auto_n = escalated_n = ci_open = pacing_n = 0
    done_24h = blocked_n = active_n = 0
    now = time.time()
    cong7 = {"tu_ap": 0, "hanh_vi": 0, "quyen": 0, "loi_thoi": 0, "telemetry": 0, "khung": 0, "eval_hong": 0, "khac": 0}
    nhat_ky = {"dang_do": 0, "da_chot": 0, "huy": 0}
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
                        if now - fp.stat().st_mtime <= 7 * 86400:      # quyết định của cổng trong 7 ngày gần nhất
                            qd = str((fm or {}).get("quyet_dinh") or "")
                            if s2 == "applied":
                                cong7["tu_ap"] += 1
                            elif s2 == "eval_failed":
                                cong7["eval_hong"] += 1
                            elif s2 == "cho_chu_duyet":
                                cong7[{"quyen:behavior_change": "hanh_vi", "quyen:permission_change": "quyen", "quyen:unknown": "quyen",
                                       "quyen:invalid": "khung", "type": "khung", "stale": "loi_thoi",
                                       "telemetry": "telemetry"}.get(qd, "khac")] += 1
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
            dd = Path(root) / "Joyce" / "proposals" / ".deploy"      # nhật ký của bộ ghi file (A05)
            if dd.is_dir():
                for jf in dd.glob("*.json"):
                    try:
                        tt = str(json.loads(jf.read_text(encoding="utf-8")).get("trang_thai") or "")
                    except (OSError, ValueError):
                        continue
                    nhat_ky["dang_do" if tt == "prepared" else "da_chot" if tt == "committed" else "huy"] += 1
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
    luot = {}
    dang_chay = {"theo_doi": 0, "dung_ban_hien_tai": 0, "ban_da_doi": 0}
    try:
        import run_ledger
        luot = run_ledger.thong_ke(tu=now - 7 * 86400)       # lượt chạy host đã ghi trong 7 ngày (B01)
        # Sổ đăng ký triển khai tối thiểu (G2): với mỗi trợ lý có lượt chạy, lượt MỚI NHẤT chạy trên đúng nội dung file hiện tại chưa?
        # Khác nghĩa là file đã đổi (đã triển khai hay chủ sửa tay) mà chưa lượt nào chạy trên bản mới: bản mới chưa được quan sát.
        for b in run_ledger.ban_gan_nhat(tu=now - TELEMETRY_CUA_SO_NGAY * 86400):
            dang_chay["theo_doi"] += 1
            try:
                root = deps.task_root(b["brain"])
                cur = run_ledger.doc_file_agent(root, b["agent"])
            except Exception:  # noqa: BLE001
                continue
            if cur and _sha256(cur) == b["revision"]:
                dang_chay["dung_ban_hien_tai"] += 1
            elif cur:
                dang_chay["ban_da_doi"] += 1
    except Exception as e:  # noqa: BLE001
        print(f"[factory] so luot chay: {type(e).__name__}: {e}", file=sys.stderr)
    return {
        "luot_chay": luot, "dang_chay": dang_chay, "watch": w_by, "canary": c_by,
        "perf_cooldowns": len(st.get("perf_cd") or {}),
        "sev_sent": len(st.get("sev_sent") or {}),
        "proposals": props, "verdicts": verdicts, "evals": evals_n, "cong7": cong7, "nhat_ky": nhat_ky,
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

def _thu_muc_khoa(deps: FactoryDeps) -> Path:
    """Thư mục tệp khoá liên tiến trình. Nằm ở state dir (chung mọi brain) vì một triển khai chạm nhiều brain."""
    return Path(deps.state_dir) / "deploy-locks"


def _ghi_dich(deps: FactoryDeps, goc, dich, text: str, *, deployment_id: str, target_id: str,
              truoc_hash: Optional[str] = None, dung_tai=None) -> dict:
    """MỘT cổng ghi file triển khai (áp nguồn, nhân đích, lật lại): khoá liên tiến trình, so-rồi-ghi, sao lưu tên duy nhất,
    nhật ký prepared/committed, ghi nguyên tử bằng bytes xác định. Xem deploy_writer. Trả receipt có `ket_qua`."""
    return deploy_writer.ghi_co_dieu_kien(Path(goc), Path(dich), text, thu_muc_khoa=_thu_muc_khoa(deps), deployment_id=deployment_id,
                                          target_id=target_id, truoc_hash=truoc_hash, dung_tai=dung_tai)


def _khoa_state(deps: FactoryDeps):
    """Khoá liên tiến trình cho chuỗi đọc-sửa-ghi của factory-state.json: hai worker không còn đè state của nhau.
    KHÔNG tái nhập; người gọi phải đọc lại state BÊN TRONG khoá."""
    return deploy_writer.khoa(_thu_muc_khoa(deps), "state:" + os.path.normcase(str(_state_path(deps))))


_CANARY_KET_THUC = ("promoted", "reverted", "superseded", "het_han")


def _cat_canary(ds: list, giu_ket_thuc: int = 50) -> list:
    """Giữ MỌI canary chưa kết thúc (đang canh, legacy_review, partial, conflict, ...) và chỉ cắt các bản ghi đã kết thúc quá
    `giu_ket_thuc` bản mới nhất. Bản cũ cắt thẳng `[-50:]` có thể loại một canary còn cần khôi phục. Không bao giờ xoá file sao lưu."""
    ket_thuc = [c for c in ds if c.get("state") in _CANARY_KET_THUC]
    bo = {id(c) for c in ket_thuc[:max(0, len(ket_thuc) - giu_ket_thuc)]}
    return [c for c in ds if id(c) not in bo]


def _doi_soat(deps: FactoryDeps, roots: Optional[list] = None) -> list:
    """Đối soát nhật ký `prepared` của các brain sau một lần chết giữa chừng. Xung đột chỉ ghi log, không đoán và không đè."""
    ra = []
    try:
        if roots is None:
            roots = [deps.task_root(str(n)) for n in (deps.brains() or [])]
            for c in _load_state(deps).get("canaries", []):
                roots.append(str(c.get("root") or ""))
                roots.extend(str(t.get("root") or "") for t in (c.get("targets") or []))
        for r in sorted({str(x) for x in roots if x}):
            for v in deploy_writer.doi_soat(Path(r), thu_muc_khoa=_thu_muc_khoa(deps)):
                ra.append({"goc": r, **v})
                if v.get("viec") == "xung_dot":
                    print(f"[factory] đối soát: {v.get('duong_dan')} khác cả bản trước lẫn bản sau, giữ nguyên", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"[factory] đối soát lỗi: {type(e).__name__}: {e}", file=sys.stderr)
    return ra


def _xep(ds: list, text: str, dedup: str) -> None:
    ds.append((text, dedup))


def _doc_file(path: Path) -> Optional[str]:
    """Nội dung file, hoặc None khi không có hay không đọc được."""
    try:
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
    except Exception:  # noqa: BLE001
        return None


def _canary_evidence(deps: FactoryDeps, c: dict) -> dict:
    """Bằng chứng của canary, đọc từ SỔ LƯỢT CHẠY do host ghi (B02, 1.3.43), không còn đọc Kanban.

    Chỉ tính lượt chạy đúng agent, đúng brain nguồn, đúng `agent_revision` = băm nội dung bản ứng viên (`candidate_hash`) và bắt đầu
    sau lúc áp. Lượt của bản cũ, của bản khác hay không đọc được revision bị loại và đếm riêng ở `khong_ro_revision`. Đếm theo
    logical execution: retry nhiều lần chỉ là một. `done` KHÔNG còn nghĩa là đạt: chỉ `verified_pass` mới là đạt; hoàn tất chưa kiểm
    (`chua_kiem`), chờ duyệt, gián đoạn và lỗi hệ thống được ghi riêng và KHÔNG bao giờ được cộng vào đạt. `ok`, `bad`, `tasks` giữ
    tên cũ cho chỗ dùng cũ: tasks = ok + bad, bad = lượt đã kiểm là rớt."""
    slug = str(c.get("slug") or "").lower()
    since = float(c.get("applied_at") or 0)
    cand = str(c.get("candidate_hash") or "")
    out = {"tasks": 0, "ok": 0, "bad": 0, "bad_ids": [], "checked_at": time.time(), "nguon": "run_ledger", "chua_kiem": 0,
           "gian_doan": 0, "doi_duyet": 0, "loi_he_thong": 0, "thu_lai": 0, "khong_ro_revision": 0}
    if len(cand) != 64 and c.get("hash"):
        # Canary tạo trước 1.3.42 chỉ có băm ngắn. Nếu file nguồn HIỆN TẠI vẫn đúng bằng băm ngắn đó thì nội dung file chính là bản
        # ứng viên và băm đầy đủ của nó là revision cần tìm; còn không thì không có gì để gán bằng chứng.
        cur = _doc_file(Path(str(c.get("root") or "")) / str(c.get("target") or ""))
        if cur is not None and _sha(cur) == str(c.get("hash")):
            cand = _sha256(cur)
    if not slug or len(cand) != 64:
        return out
    try:
        import run_ledger
        brain = Path(str(c.get("root"))).name
        tat_ca = run_ledger.danh_sach(brain_id=brain, agent_id=slug, tu=since, gioi_han=5000)
        out["khong_ro_revision"] = sum(1 for r in tat_ca if not r.get("agent_revision"))
        tk = run_ledger.thong_ke(brain_id=brain, agent_id=slug, agent_revision=cand, tu=since)
        out["ok"], out["bad"] = tk["verified_pass"], tk["verified_fail"]
        out["tasks"] = out["ok"] + out["bad"]
        for k in ("chua_kiem", "gian_doan", "doi_duyet", "loi_he_thong", "thu_lai"):
            out[k] = tk[k]
        if out["bad"]:
            cuoi: dict = {}
            for r in sorted(run_ledger.danh_sach(brain_id=brain, agent_id=slug, agent_revision=cand, tu=since, gioi_han=5000),
                            key=lambda x: x["started_at"]):
                cuoi[r["logical_execution_id"]] = r
            out["bad_ids"] = [r["run_id"] for r in cuoi.values() if r["verification_status"] == "verified_fail" or r["status"] == "failed"
                              and r["block_kind"] != "system"][:20]
    except Exception as e:  # noqa: BLE001
        print(f"[factory] canary bằng chứng {c.get('id')}: {type(e).__name__}: {e}", file=sys.stderr)
    return out


def _canary_bad_signals(deps: FactoryDeps, c: dict) -> list:
    """Id các việc LỖI đã chạy trên bản ứng viên (gắn qua khoá agent, không qua chữ). Rỗng = chưa thấy lỗi."""
    return _canary_evidence(deps, c)["bad_ids"][:5]


async def _bao(deps: FactoryDeps, text: str, dedup: str) -> None:
    try:
        await deps.inbox(text, kind="system", label="self-improve", source="factory", dedup=dedup)
    except Exception:  # noqa: BLE001
        pass


def _nhan_mot_dich(deps: FactoryDeps, c: dict, tg: dict, cand_hash: str, cand_text: str) -> None:
    """Nhân bản ứng viên sang MỘT đích. Điều kiện ghi (A02, D2): đích có quan hệ KẾ THỪA với bản nguồn trước sửa VÀ vẫn đúng
    bằng snapshot ngay trước khi ghi. Khác snapshot là `conflict`, khác baseline từ trước là `override`; cả hai giữ nguyên.
    Ghi qua writer chung (A05): khoá liên tiến trình, so-rồi-ghi, sao lưu tên duy nhất, nhật ký.
    Đặt tg['state'] = promoted | already | conflict | override | missing | error."""
    rel = str(c.get("target") or "")
    goc = Path(str(tg.get("root") or ""))
    dst = goc / rel
    dep_id = str(c.get("deployment_id") or c.get("id") or "")
    tid = _sha(str(goc))
    d = _doc_file(dst)
    if d is None:
        tg["state"] = "missing"        # đích bị xoá: KHÔNG tạo lại
        return
    if _khop(d, str(c.get("candidate_hash") or ""), cand_hash):
        # Đã là bản ứng viên. Nếu NHẬT KÝ của chính triển khai này đã `committed` đúng bản đó thì là do ta ghi (lần chạy trước chết
        # sau khi ghi, trước khi kịp lưu state): nhận lại receipt và đường khôi phục. Không có nhật ký thì chỉ nói "đã đúng bản".
        rc = deploy_writer.doc_receipt(goc, dep_id, tid) if dep_id else None
        if rc and rc.get("trang_thai") == "committed" and rc.get("sau_hash") == _sha256(d):
            tg["state"], tg["co_receipt"], tg["backup"] = "promoted", True, rc.get("backup") or ""
        else:
            tg["state"], tg["co_receipt"] = "already", False
        return
    quan_he = str(tg.get("quan_he") or "")
    if not quan_he:
        # Bản ghi tạo trước 1.3.42 không có xếp loại: lấy bản sao lưu của nguồn làm baseline chung. Đích khác bản đó là override.
        goc_chung = _doc_file(Path(str(c.get("backup") or "")))
        ref = _sha(goc_chung) if goc_chung is not None else ""
        quan_he = "ke_thua" if (ref and ref == str(tg.get("base_hash") or "")) else "override"
        tg["quan_he"] = quan_he
    if quan_he != "ke_thua":
        tg["state"] = "override"       # phòng có biến thể riêng từ trước: không tự ghi đè, chờ chủ (hợp nhất bằng đề xuất riêng)
        return
    chup_day_du = str(tg.get("target_observed_hash") or "")
    chup_ngan = str(tg.get("base_hash") or "")
    if not _khop(d, chup_day_du, chup_ngan):
        tg["state"] = "conflict"       # chủ đã sửa riêng kể từ lúc chụp: nhường
        return
    try:
        rc = _ghi_dich(deps, goc, dst, cand_text, deployment_id=dep_id or uuid.uuid4().hex, target_id=tid, truoc_hash=_sha256(d))
    except deploy_writer.DuongKhongAnToan as e:
        tg["state"], tg["error"] = "conflict", f"đường dẫn không an toàn: {e}"[:140]
        return
    except Exception as e:  # noqa: BLE001
        tg["tries"] = int(tg.get("tries") or 0) + 1
        tg["state"] = "error"
        tg["error"] = f"{type(e).__name__}: {e}"[:140]
        print(f"[factory] canary nhân {tg.get('root')}: {tg['error']}", file=sys.stderr)
        return
    kq = rc.get("ket_qua")
    if kq == "committed":
        tg["state"], tg["co_receipt"], tg["backup"] = "promoted", True, rc.get("backup") or ""
    elif kq == "missing":
        tg["state"] = "missing"
    else:
        tg["state"] = "conflict"       # đích đổi giữa lúc kiểm và lúc ghi (writer so-rồi-ghi dưới khoá)


def _ten_dich(tg: dict) -> str:
    return Path(str(tg.get("root") or "")).name or "?"


def _dich_dang_do(tgs: list) -> bool:
    return any(t.get("state") == "pending" or (t.get("state") == "error" and int(t.get("tries") or 0) < CANARY_LOI_THU_LAI)
               for t in tgs)


def _canary_loi(deps: FactoryDeps, thong_bao: list) -> dict:
    """Mỗi nhịp, với từng canary đang canh:

    1. File nguồn không còn đúng bản ứng viên (chủ sửa/xoá tay) -> superseded, nhường chủ.
    2. Có việc LỖI trên bản ứng viên -> lật lại NGAY, không chờ hết giờ (FIX-05). Lật có so-rồi-ghi: chủ vừa sửa tay
       thì nhường, không đè.
    3. Chưa hết giờ -> chờ. Hết giờ mà chưa đủ số việc đã chạy -> KHÔNG nhân (không traffic không phải bằng chứng);
       chờ quá CANARY_HET_HAN_NGAY thì dừng và báo chủ.
    4. Đủ giờ, đủ việc, không lỗi -> nhân TỪNG đích (FIX-04): đích còn đúng bản đã chụp mới được ghi, đích đã sửa riêng
       giữ nguyên, trạng thái từng đích lưu ngay nên chết giữa chừng chạy lại không làm lại, báo đúng số đích thành công."""
    rep = {"promoted": 0, "reverted": 0, "superseded": 0, "waiting": 0, "partial": 0, "conflict": 0,
           "cho_bang_chung": 0, "het_han": 0, "paused": 0, "legacy_review": 0}
    st = _load_state(deps)
    now = time.time()
    rep["legacy_review"] = sum(1 for x in st.get("canaries", []) if x.get("state") == "legacy_review")
    for c in st.get("canaries", []):
        if c.get("state") != "canary":
            continue
        target = Path(str(c.get("root") or "")) / str(c.get("target") or "")
        cand_hash = str(c.get("hash") or "")
        cur = _doc_file(target)
        if not cur or not _khop(cur, str(c.get("candidate_hash") or ""), cand_hash):
            c["state"] = "superseded"   # chủ sửa/xoá tay trong cửa sổ canary -> nhường chủ
            _save_state(deps, st)
            rep["superseded"] += 1
            continue

        bad = _canary_bad_signals(deps, c)
        if bad:
            goc = _doc_file(Path(str(c.get("backup") or "")))
            cur2 = _doc_file(target)
            if cur2 is None or not _khop(cur2, str(c.get("candidate_hash") or ""), cand_hash):
                c["state"] = "superseded"      # chủ vừa sửa tay ngay lúc canary sắp lật: không đè
                _save_state(deps, st)
                rep["superseded"] += 1
                continue
            try:
                if goc is None:
                    raise FileNotFoundError("không còn bản sao lưu để lật lại")
                rc = _ghi_dich(deps, c.get("root"), target, goc, deployment_id=str(c.get("deployment_id") or c.get("id")),
                               target_id="lat-lai", truoc_hash=_sha256(cur2))
                if rc.get("ket_qua") == "conflict":
                    c["state"] = "superseded"        # chủ sửa tay đúng lúc lật: so-rồi-ghi dưới khoá nhận ra, không đè
                    _save_state(deps, st)
                    rep["superseded"] += 1
                    continue
                if rc.get("ket_qua") != "committed":
                    raise OSError("lật lại không thành: " + str(rc.get("ket_qua")))
            except Exception as e:  # noqa: BLE001
                c["rollback_error"] = f"{type(e).__name__}: {e}"[:140]
                _save_state(deps, st)
                print(f"[factory] canary rollback {c.get('id')}: {c['rollback_error']}", file=sys.stderr)
                _xep(thong_bao, f"🐤 **Canary KHÔNG lật lại được**: `{c.get('target')}` ở {c.get('brain')} có {len(bad)} việc lỗi "
                                 f"nhưng không trả file về bản cũ được ({c['rollback_error']}). Anh kiểm tra tay giúp.",
                           f"canaryrevfail:{c.get('id')}")
                continue
            c["state"] = "reverted"
            c["evidence"] = {k: v for k, v in _canary_evidence(deps, c).items() if k != "bad_ids"}
            _save_state(deps, st)
            rep["reverted"] += 1
            _xep(thong_bao, f"🐤 **Canary lật lại**: `{c.get('target')}` ở {c.get('brain')} có {len(bad)} việc lỗi chạy trên "
                             f"bản mới (gắn đúng agent `{c.get('slug')}`). Đã trả file về bản cũ - không nhân sang brain khác.",
                       f"canaryrev:{c.get('id')}")
            continue

        if now < float(c.get("promote_at") or 0):
            rep["waiting"] += 1
            continue
        if _dang_tam_dung(deps):
            rep["paused"] += 1       # dừng chỉ chặn bước NHÂN; phát hiện lỗi và lật lại ở trên vẫn chạy
            continue

        ev = _canary_evidence(deps, c)
        c["evidence"] = {k: v for k, v in ev.items() if k != "bad_ids"}
        can = int(c.get("min_tasks") or CANARY_MIN_TASKS)
        if ev["tasks"] < can:
            if now - float(c.get("applied_at") or now) > CANARY_HET_HAN_NGAY * 86400:
                c["state"] = "het_han"
                _save_state(deps, st)
                rep["het_han"] += 1
                _xep(thong_bao, f"🐤 **Canary hết hạn**: `{c.get('target')}` ở {c.get('brain')} sau {CANARY_HET_HAN_NGAY} ngày chỉ có "
                                 f"{ev['tasks']}/{can} việc chạy trên bản mới, chưa đủ bằng chứng nên KHÔNG nhân sang brain khác. "
                                 f"Bản mới vẫn đang chạy ở {c.get('brain')}; anh quyết định giữ hay lật lại.",
                           f"canaryexp:{c.get('id')}")
            else:
                _save_state(deps, st)
                rep["cho_bang_chung"] += 1
            continue

        tgs = c.get("targets")
        if not isinstance(tgs, list):
            # Canary tạo trước 1.3.41 không có hash từng đích: lấy bản sao lưu của nguồn làm "bản gốc chung". Đích còn
            # giống hệt bản đó mới được ghi; khác thì coi là đã sửa riêng.
            goc_chung = _doc_file(Path(str(c.get("backup") or "")))
            base = _sha(goc_chung) if goc_chung is not None else ""
            tgs = [{"root": r, "base_hash": base, "state": "pending", "tries": 0} for r in (c.get("sharers") or [])]
            c["targets"] = tgs
        for tg in tgs:
            if tg.get("state") == "pending" or (tg.get("state") == "error" and int(tg.get("tries") or 0) < CANARY_LOI_THU_LAI):
                _nhan_mot_dich(deps, c, tg, cand_hash, cur)
                _save_state(deps, st)      # LƯU NGAY từng đích: chết giữa chừng thì lần sau không làm lại đích đã xong
        if _dich_dang_do(tgs):
            continue        # đích lỗi tạm thời: thử lại ở nhịp sau
        dat = [t for t in tgs if t.get("state") in ("promoted", "already")]
        c["promoted_count"] = len(dat)
        tong = len(tgs)
        gio = int((now - float(c.get("applied_at") or now)) / 3600)
        if len(dat) == tong:
            c["state"] = "promoted"
            rep["promoted"] += 1
            _xep(thong_bao, f"🐤 **Canary qua**: `{c.get('target')}` chạy ổn {gio}h ở {c.get('brain')} ({ev['ok']}/{ev['tasks']} việc đạt) "
                             f"- đã nhân bản sang {len(dat)} brain còn lại.", f"canaryok:{c.get('id')}")
        else:
            ov = [_ten_dich(t) for t in tgs if t.get("state") == "override"]
            gi = [_ten_dich(t) for t in tgs if t.get("state") == "conflict"]
            thieu = [_ten_dich(t) for t in tgs if t.get("state") == "missing"]
            loi = [_ten_dich(t) for t in tgs if t.get("state") == "error"]
            c["state"] = "partial" if dat else "conflict"
            rep["partial" if dat else "conflict"] += 1
            chi_tiet = []
            if ov:
                chi_tiet.append(f"{len(ov)} brain có bản riêng từ trước (override) nên không tự ghi đè ({', '.join(ov[:4])})")
            if gi:
                chi_tiet.append(f"{len(gi)} brain đã được sửa riêng nên giữ nguyên bản riêng ({', '.join(gi[:4])})")
            if thieu:
                chi_tiet.append(f"{len(thieu)} brain không còn file ({', '.join(thieu[:4])})")
            if loi:
                chi_tiet.append(f"{len(loi)} brain ghi lỗi ({', '.join(loi[:4])})")
            _xep(thong_bao, f"🐤 **Canary qua MỘT PHẦN**: `{c.get('target')}` ({ev['ok']}/{ev['tasks']} việc đạt) chỉ nhân được "
                             f"{len(dat)}/{tong} brain; " + "; ".join(chi_tiet) + ". Không ghi đè bản riêng của phòng nào.",
                       f"canarypart:{c.get('id')}")
        _save_state(deps, st)
    _save_state(deps, st)
    return rep


async def canary_tick(deps: FactoryDeps) -> dict:
    """Xem `_canary_loi`. Toàn bộ đọc-sửa-ghi state nằm dưới khoá liên tiến trình; thông báo hộp thư gửi SAU khi nhả khoá để một
    cuộc gọi hộp thư chậm không giữ khoá của worker khác. Đầu mỗi nhịp đối soát nhật ký của lần chết giữa chừng."""
    thong_bao: list = []
    _doi_soat(deps)
    with _khoa_state(deps):
        rep = _canary_loi(deps, thong_bao)
    for text, dedup in thong_bao:
        await _bao(deps, text, dedup)
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
