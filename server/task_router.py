"""task_router.py - Phân việc não theo loại tác vụ + vòng quay API key nhiều tài khoản.

Hai trách nhiệm, một nhà, đứng SAU aux_engine (module này không import aux_engine -
aux_engine import nó, tránh vòng):

1. LOẠI TÁC VỤ NÀO CHẠY MODEL NÀO (settings["model"]["task_models"]). Trang Phân việc não
   liệt kê mọi loại việc nền thật sự gọi LLM (nhắc hẹn, loop, Kanban, ingest, bản tin sáng,
   quyết định trả lời nhóm, phán xét agent, tự học...) và cho chủ gán từng loại một
   provider/model riêng. Loại nào chưa gán thì đi theo "model việc nền" chung
   (settings.model.auxiliary) đúng như cũ - mặc định không đổi hành vi.

2. VÒNG QUAY API KEY (settings["model"]["<provider>_keys"]). Một provider API có thể nhận
   NHIỀU key (nhiều tài khoản hợp lệ người dùng tự đăng ký). `pick_key` trả key đầu tiên
   chưa bị đánh dấu "cháy"; engine gọi bị từ chối vì quota/429 thì `burn_key` khóa key đó
   một thời gian và `_ApiAuxEngine.query` nhảy sang key kế trong CÙNG lượt, trước khi chuỗi
   fallback tới mắt sau. Trạng thái cháy lưu STATE_DIR/key_burns.json nên restart server
   cũng không thử lại key vừa cháy.

   Đây là NHỮNG TÀI KHOẢN CHỦ SỞ HỮU tự đăng ký hợp lệ (mỗi tài khoản một key). Module
   không tạo, thu thập, hay gợi ý key; nó chỉ luân phiên những key chủ đã dán vào.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import time

import config as cfgmod

# ── provider API -> trường key chính trong settings["model"] ─────────────────────────────
# Nguồn chuẩn cho mọi nơi cần tra tên trường key (aux_engine._KEY_FIELD alias sang đây).
KEY_FIELD = {
    "openrouter": "openrouter_key",
    "openai": "openai_api_key",
    "gemini": "gemini_api_key",
    "groq": "groq_api_key",
    "deepseek": "deepseek_api_key",
    "anthropic-api": "anthropic_api_key",
    "ollama": "ollama_key",
    # ollama-local / openai-compat: thứ quyết định dùng được là ENDPOINT, key có thể rỗng.
    # Vẫn hỗ trợ vòng quay cho trường hợp nhiều endpoint sau proxy có xác thực.
    "ollama-local": "ollama_local_key",
    "openai-compat": "openai_compat_key",
}

# Provider hiện trên card Vòng quay key của trang Phân việc não. Endpoint-tự-khai
# (ollama-local, openai-compat) lấy key từ trường riêng nên giữ ngoài danh sách này -
# vòng quay của chúng vẫn hoạt động nếu ai đó điền key phụ, chỉ là UI không bày ra.
RING_PROVIDERS = ("gemini", "groq", "openrouter", "deepseek", "openai", "anthropic-api", "ollama")

# ── Danh mục LOẠI TÁC VỤ thật sự gọi LLM (bám call-site, không phải danh sách chung) ────
# `tag` là chuỗi các nơi gọi truyền vào aux_engine.apply(..., tag=...). prefix=True nghĩa
# là tag thật bắt đầu bằng chuỗi đó (dispatch:<id>:<suffix>). Loại nào không khớp tag nào
# sẽ dùng spec của "khac" (rồi mới tới auxiliary).
TASK_TYPES = [
    {"id": "reminder", "tag": "reminder",
     "vi": "Nhắc hẹn & cron", "en": "Reminders & cron",
     "vi_mo_ta": "Việc hẹn giờ chạy nền: báo cáo, nhắc việc, tác vụ lên lịch sẵn.",
     "en_mo_ta": "Scheduled background jobs: reports, reminders, timed chores.",
     "goi_y": ["groq", "ollama-local"],
     "vi_goi_y": "Lượt nhiều, prompt ngắn - Groq free nhanh hoặc model local là đủ.",
     "en_goi_y": "Frequent, short prompts - fast free Groq or a local model is enough."},
    {"id": "loop", "tag": "loop",
     "vi": "Vòng lặp tự chạy", "en": "Self-running loops",
     "vi_mo_ta": "Loop lặp theo chu kỳ tự kiểm tra và báo kết quả.",
     "en_mo_ta": "Periodic loops that self-verify and report results.",
     "goi_y": ["gemini", "groq"],
     "vi_goi_y": "Có gọi tool - Gemini/Groq free có tool-calling; chừa quota cho việc nặng.",
     "en_goi_y": "Uses tools - free Gemini/Groq support tool-calling; keeps quota cheap."},
    {"id": "kanban", "tag": "dispatch:", "prefix": True,
     "vi": "Việc Kanban (dispatch)", "en": "Kanban dispatch",
     "vi_mo_ta": "Task trên bảng Việc do Joyce tự nhặt chạy nền.",
     "en_mo_ta": "Work-board tasks Joyce picks up and runs in background.",
     "goi_y": ["gemini", "openrouter"],
     "vi_goi_y": "Việc thật có tool - Gemini free cho đa số; OpenRouter free dự phòng.",
     "en_goi_y": "Real tool work - free Gemini for most; OpenRouter free as fallback."},
    {"id": "ingest", "tag": "ingest",
     "vi": "Tiêu hoá nguồn vào wiki", "en": "Source ingestion",
     "vi_mo_ta": "Chưng cất tài liệu/nút thô thành bài wiki của Second Brain.",
     "en_mo_ta": "Distilling raw sources/notes into Second Brain wiki pages.",
     "goi_y": ["gemini", "deepseek"],
     "vi_goi_y": "Đọc-viết dài, không cần tool - Gemini context dài hoặc DeepSeek rẻ.",
     "en_goi_y": "Long read-write, no tools - long-context Gemini or cheap DeepSeek."},
    {"id": "learn", "tag": "learn",
     "vi": "Tự học (verify)", "en": "Self-improvement verify",
     "vi_mo_ta": "Vòng phản biện đọc-only duyệt skill/agent/workflow đề xuất.",
     "en_mo_ta": "Read-only critique passes reviewing proposed skills/agents/workflows.",
     "goi_y": ["gemini", "deepseek"],
     "vi_goi_y": "Chỉ đọc + trả JSON - model rẻ có reasoning tốt là đủ.",
     "en_goi_y": "Read-only JSON verdicts - a cheap model with decent reasoning works."},
    {"id": "curator", "tag": "curator",
     "vi": "Tự học (curator)", "en": "Self-improvement curator",
     "vi_mo_ta": "Pass tuyển chọn/tổng hợp của vòng tự học.",
     "en_mo_ta": "Selection/synthesis pass of the self-improvement loop.",
     "goi_y": ["gemini", "deepseek"],
     "vi_goi_y": "Như nhóm verify - chỉ đọc và trả JSON.",
     "en_goi_y": "Same as verify - read-only JSON output."},
    {"id": "today-brief", "tag": "today-brief",
     "vi": "Bản tin tổng hợp", "en": "Daily brief",
     "vi_mo_ta": "Bản tin sáng/tổng hợp ngày gửi về kênh.",
     "en_mo_ta": "Morning digest / daily summary pushed to a channel.",
     "goi_y": ["gemini", "openrouter"],
     "vi_goi_y": "Tóm tắt văn xuôi - model viết trôi chảy rẻ/free.",
     "en_goi_y": "Prose summarising - any fluent free/cheap model."},
    {"id": "reply-policy", "tag": "reply-policy",
     "vi": "Quyết định trả lời nhóm", "en": "Group reply policy",
     "vi_mo_ta": "Phán xét text-only: có nên trả lời tin nhắn nhóm không.",
     "en_mo_ta": "Text-only judge: whether to answer a group message.",
     "goi_y": ["groq", "ollama-local"],
     "vi_goi_y": "Câu quyết định nhịp cao, ngắn - Groq free hoặc local là nhanh nhất.",
     "en_goi_y": "High-rate short verdicts - free Groq or local is fastest."},
    {"id": "agent-judge", "tag": "agent-judge",
     "vi": "Phán xét kết quả agent", "en": "Agent result judge",
     "vi_mo_ta": "Text-only chấm điểm output của fork agent.",
     "en_mo_ta": "Text-only grading of agent fork output.",
     "goi_y": ["groq", "deepseek"],
     "vi_goi_y": "So sánh + chấm ngắn - model rẻ nhanh.",
     "en_goi_y": "Compare-and-grade, short output - a fast cheap model."},
    {"id": "khac", "tag": "",
     "vi": "Việc nền khác", "en": "Other background work",
     "vi_mo_ta": "Mọi việc nền không thuộc loại trên (cửa an toàn).",
     "en_mo_ta": "Any background job not listed above (safe default).",
     "goi_y": ["gemini", "openrouter"],
     "vi_goi_y": "Để trống = theo model việc nền chung ở trang Models.",
     "en_goi_y": "Empty = follows the global background model on the Models page."},
]
_TASK_BY_ID = {t["id"]: t for t in TASK_TYPES}


def task_key_for_tag(tag: str) -> str:
    """Tag call-site -> id loại tác vụ trong registry. Không khớp -> 'khac'."""
    t = str(tag or "").strip()
    # hậu tố router dính trên tag của mắt dự phòng (-main, -orfree) - gỡ ra trước khi tra.
    for suf in ("-main", "-orfree"):
        if t.endswith(suf):
            t = t[: -len(suf)]
            break
    for tt in TASK_TYPES:
        tg = tt.get("tag") or ""
        if not tg:
            continue
        if tt.get("prefix"):
            if t.startswith(tg):
                return tt["id"]
        elif t == tg:
            return tt["id"]
    return "khac"


def spec_for_tag(tag: str, settings: dict = None) -> dict:
    """{'provider','model'} cho một tag việc nền: gán riêng -> 'khac' -> model việc nền
    chung (auxiliary) -> Claude. Không đụng phanh ngân sách - read_spec() lo phần đó."""
    s = settings if settings is not None else cfgmod.read_settings()
    m = s.get("model", {}) or {}
    tm = m.get("task_models") or {}
    key = task_key_for_tag(tag)
    ent = tm.get(key) or {}
    if not (ent.get("provider") or "").strip() and key != "khac":
        ent = tm.get("khac") or {}
    prov = (ent.get("provider") or "").strip()
    if prov:
        return {"provider": prov, "model": (ent.get("model") or "").strip()}
    aux = m.get("auxiliary") or {}
    return {"provider": (aux.get("provider") or "anthropic-cli"),
            "model": (aux.get("model") or "")}


def task_list(settings: dict = None) -> list:
    """Danh sách loại tác vụ + spec hiệu lực + cờ `custom` (có gán riêng không)."""
    s = settings if settings is not None else cfgmod.read_settings()
    tm = ((s.get("model") or {}).get("task_models") or {})
    use30 = task_use_summary(30)
    out = []
    for tt in TASK_TYPES:
        own = (tm.get(tt["id"]) or {})
        spec_eff = spec_for_tag(tt.get("tag") or tt["id"], s)
        use = use30.get(tt["id"]) or {"in": 0, "out": 0, "turns": 0, "cost": 0.0,
                                      "cost_est": 0.0, "models": {}}
        out.append({**{k: tt[k] for k in ("id", "vi", "en", "vi_mo_ta", "en_mo_ta",
                                          "goi_y", "vi_goi_y", "en_goi_y")},
                    "spec": spec_eff,
                    "custom": bool((own.get("provider") or "").strip()),
                    "use": use,
                    "dx": _de_xuat(tt, spec_eff, use, s)})
    return out


def set_task_spec(task_id: str, provider: str, model: str = "", settings: dict = None) -> bool:
    """Gán/gỡ gán spec cho một loại tác vụ. provider rỗng = xoá gán riêng (về mặc định)."""
    if task_id not in _TASK_BY_ID:
        return False
    s = settings if settings is not None else cfgmod.read_settings()
    m = s.setdefault("model", {})
    tm = m.setdefault("task_models", {})
    prov = (provider or "").strip()
    if prov:
        tm[task_id] = {"provider": prov, "model": (model or "").strip()}
    else:
        tm.pop(task_id, None)
    if settings is None:
        cfgmod.write_settings(s)
    return True


def clear_task_specs() -> None:
    s = cfgmod.read_settings()
    ((s.get("model") or {}).pop("task_models", None))
    cfgmod.write_settings(s)


# ── Sổ mức dùng theo LOẠI TÁC VỤ (STATE_DIR/task_usage.json) ────────────────────────────
# Khác usage_store: sổ đó gộp theo provider|model cho trang Mức dùng; sổ này gộp theo loại
# việc (reminder/loop/kanban...) để trang Phân việc não trả lời "loại này đang đốt bao
# nhiêu token tiền, chạy trên não nào". Rollup theo ngày, giữ ~2 tháng.
_TASK_USE_PATH = cfgmod.STATE_DIR / "task_usage.json"
_TASK_USE_GIU = 62


def _load_task_use() -> dict:
    try:
        if _TASK_USE_PATH.exists():
            d = json.loads(_TASK_USE_PATH.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def task_use_note(tag: str, provider: str, model: str, tin: int = 0, tout: int = 0,
                  cost: float = 0.0) -> None:
    """Cộng một lượt gọi API vào sổ theo loại tác vụ. `cost` = chi phí provider trả về
    thật (Claude Code CLI...); còn lại là 0 và trang sẽ ước tính theo bảng giá."""
    tid = task_key_for_tag(tag)
    tin, tout = int(tin or 0), int(tout or 0)
    if tin <= 0 and tout <= 0 and not cost:
        return
    try:
        day = time.strftime("%Y-%m-%d")
        with _LOCK:
            d = _load_task_use()
            ent = d.setdefault(day, {}).setdefault(
                tid, {"in": 0, "out": 0, "turns": 0, "cost": 0.0, "models": {}})
            ent["in"] += tin
            ent["out"] += tout
            ent["turns"] += 1
            ent["cost"] += float(cost or 0.0)
            mk = f"{provider or '?'}|{model or ''}"
            mm = ent["models"].setdefault(mk, {"in": 0, "out": 0, "cost": 0.0})
            mm["in"] += tin
            mm["out"] += tout
            mm["cost"] += float(cost or 0.0)
            for old in sorted(d)[:-_TASK_USE_GIU]:
                d.pop(old, None)
            _TASK_USE_PATH.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception as e:      # noqa: BLE001 - cái sổ phụ không được chặn việc nền
        print(f"[task_use] {type(e).__name__}: {e}", file=sys.stderr)


def task_use_summary(days: int = 30) -> dict:
    """{task_id: {in,out,turns,cost,cost_est,models}} của `days` ngày gần nhất.

    `cost` = tiền provider trả về thật; `cost_est` = ước tính bổ sung theo bảng giá
    (usage_pricing.json) cho phần không có cost thật. Hai con số này phải trình bày là
    '≈ ước tính' - bảng giá tay cập nhật, model lạ không khớp thì tính 0.
    """
    try:
        import usage_parsers
        prices = usage_parsers.load_prices()
    except Exception:
        prices = {}
    d = _load_task_use()
    out: dict = {}
    for day in sorted(d)[-days:]:
        for tid, ent in (d.get(day) or {}).items():
            e = out.setdefault(tid, {"in": 0, "out": 0, "turns": 0, "cost": 0.0,
                                     "cost_est": 0.0, "models": {}})
            e["in"] += ent.get("in", 0)
            e["out"] += ent.get("out", 0)
            e["turns"] += ent.get("turns", 0)
            e["cost"] += float(ent.get("cost") or 0.0)
            for mk, mm in (ent.get("models") or {}).items():
                _p, _sep, mdl = mk.partition("|")
                me = e["models"].setdefault(mk, {"in": 0, "out": 0, "cost": 0.0,
                                                 "cost_est": 0.0})
                me["in"] += mm.get("in", 0)
                me["out"] += mm.get("out", 0)
                real = float(mm.get("cost") or 0.0)
                me["cost"] += real
                est = real or usage_parsers.estimate_cost(
                    {"model": mdl, "input": mm.get("in", 0),
                     "output": mm.get("out", 0)}, prices)
                me["cost_est"] += est
                e["cost_est"] += est
    return out


def _provider_runnable(prov: str, s: dict) -> bool:
    """Provider trong danh sách gợi ý có chạy được NGAY không: có key trong vòng quay
    (ollama-local/openai-compat thì chỉ cần endpoint)."""
    m = (s or {}).get("model", {}) or {}
    if prov == "ollama-local":
        return bool((m.get("ollama_local_endpoint") or "").strip())
    if prov == "openai-compat":
        return bool((m.get("openai_compat_base") or "").strip())
    return bool(keys_for(prov, s))


def _de_xuat(tt: dict, spec_eff: dict, use: dict, s: dict) -> dict:
    """Đề xuất não cho một loại tác vụ, dựa trên: danh sách gợi ý đã curate (goi_y),
    provider nào chủ ĐÃ nối thật (không đề xuất thứ chưa nối), và mức dùng thật.

    state: ok = đang theo gợi ý · switch = nên đổi · save = đúng gợi ý nhưng đang đốt
    tiền thật mà còn mắt rẻ hơn chạy được · none = chưa nối nhà gợi ý nào.
    """
    running = (spec_eff.get("provider") or "").strip()
    goi = list(tt.get("goi_y") or [])
    runnable = [p for p in goi if _provider_runnable(p, s)]
    cost_est = float((use or {}).get("cost_est") or 0.0)
    if running in goi:
        # Đúng gợi ý rồi - nhưng nếu đang tốn tiền thật còn mắt free/rẻ hơn nối được
        # thì nói nhẹ (Ollama local = $0; model ':free' và nhà chưa thấy tốn = ~0).
        cheaper = [p for p in runnable if p != running and p in ("ollama-local",)]
        if cost_est > 0.5 and cheaper:
            return {"provider": cheaper[0], "state": "save",
                    "vi": f"đang tốn ~${cost_est:.2f}/30n - {cheaper[0]} chạy được và miễn phí",
                    "en": f"costing ~${cost_est:.2f}/30d - {cheaper[0]} is connected and free"}
        return {"provider": running, "state": "ok",
                "vi": "đang theo gợi ý", "en": "on suggestion"}
    if runnable:
        p = runnable[0]
        return {"provider": p, "state": "switch",
                "vi": f"nên đổi sang {p}" + (f" (đang tốn ~${cost_est:.2f}/30n)" if cost_est > 0.5 else ""),
                "en": f"switch to {p}" + (f" (costing ~${cost_est:.2f}/30d)" if cost_est > 0.5 else "")}
    return {"provider": "", "state": "none",
            "vi": "chưa nối nhà gợi ý nào (vd " + ", ".join(goi[:2]) + ")",
            "en": "no suggested provider connected (e.g. " + ", ".join(goi[:2]) + ")"}


# ── Vòng quay API key ────────────────────────────────────────────────────────────────────
_BURN_PATH = cfgmod.STATE_DIR / "key_burns.json"
_LOCK = threading.Lock()
# provider -> {fingerprint: {"until": epoch, "why": str, "tail": "…abcd"}}
_burns: dict = {}
_burns_loaded = False


def _fp(key: str) -> str:
    return hashlib.sha1((key or "").encode("utf-8")).hexdigest()[:12]


def _tail(key: str) -> str:
    return "…" + key[-4:] if len(key or "") >= 4 else "…"


def _load_burns() -> None:
    global _burns_loaded
    with _LOCK:
        if _burns_loaded:
            return
        _burns_loaded = True
        try:
            raw = json.loads(_BURN_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for prov, slots in raw.items():
                    if isinstance(slots, dict):
                        _burns.setdefault(prov, {}).update(
                            {k: v for k, v in slots.items() if isinstance(v, dict)})
        except Exception:
            pass  # file hỏng/thiếu -> bắt đầu trống, không được làm chết router


def _save_burns() -> None:
    try:
        _BURN_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _BURN_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(_burns, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_BURN_PATH)
    except Exception as e:
        print(f"[task_router] không ghi được key_burns: {e}", file=sys.stderr)


def keys_for(provider: str, settings: dict = None) -> list:
    """Toàn bộ key của provider theo thứ tự: key chính trước, rồi <provider>_keys, khử trùng."""
    field = KEY_FIELD.get(provider)
    if not field:
        return []
    s = settings if settings is not None else cfgmod.read_settings()
    m = s.get("model", {}) or {}
    out: list = []

    def _push(v):
        v = (v or "").strip()
        if v and v not in out:
            out.append(v)

    _push(m.get(field))
    extra = m.get(provider + "_keys") or []
    if isinstance(extra, str):
        extra = re.split(r"[,\n\r]+", extra)
    for k in extra if isinstance(extra, list) else []:
        _push(k)
    return out


def burn_until(provider: str, key: str) -> float:
    """Mốc epoch key hết 'cháy' (0 = đang dùng được)."""
    _load_burns()
    ent = (_burns.get(provider) or {}).get(_fp(key)) or {}
    until = float(ent.get("until") or 0)
    return until if until > time.time() else 0.0


def pick_key(provider: str, settings: dict = None) -> str:
    """Key đầu tiên CHƯA cháy. Hết key sạch -> "" (engine coi là không sẵn sàng để chuỗi
    fallback sang mắt khác, đúng hơn là cố gọi một key đã biết là chết quota)."""
    for k in keys_for(provider, settings):
        if not burn_until(provider, k):
            return k
    return ""


def usable_keys(provider: str, settings: dict = None) -> list:
    """Ring cho một lượt gọi: key sạch trước, key đang cháy cuối (để caller còn thử nốt
    nếu burn chỉ là giây-cuối và mọi key đều bẩn - tốt hơn là bỏ cuộc hẳn)."""
    ks = keys_for(provider, settings)
    clean = [k for k in ks if not burn_until(provider, k)]
    dirty = [k for k in ks if burn_until(provider, k)]
    return clean + dirty


def burn_key(provider: str, key: str, why: str = "", seconds: float = 300.0) -> None:
    """Đánh dấu key tạm chết (quota/429/auth). `seconds` nên lấy từ burn_cooldown(text)."""
    if not key:
        return
    _load_burns()
    with _LOCK:
        (_burns.setdefault(provider, {}))[_fp(key)] = {
            "until": time.time() + max(30.0, float(seconds or 0)),
            "why": (why or "")[:240],
            "tail": _tail(key),
        }
        _save_burns()


def note_use(provider: str, key: str, tin: int = 0, tout: int = 0) -> None:
    """Đếm lượt/token lên đúng key slot (nhận diện bằng fingerprint + đuôi, không lưu key
    thô). Đây là chỗ attribution: trang Phân việc não thấy key nào gánh bao nhiêu lượt mà
    không lộ bí mật. Best-effort - một cái đếm không được làm chết lượt gọi."""
    if not key:
        return
    try:
        _load_burns()
        with _LOCK:
            ent = _burns.setdefault(provider, {}).setdefault(_fp(key), {"until": 0})
            ent["tail"] = _tail(key)
            ent["uses"] = int(ent.get("uses") or 0) + 1
            ent["tin"] = int(ent.get("tin") or 0) + int(tin or 0)
            ent["tout"] = int(ent.get("tout") or 0) + int(tout or 0)
            ent["last_ts"] = time.time()
            _save_burns()
    except Exception:
        pass


def unburn(provider: str = None) -> int:
    """Mở khoá tay. provider=None = dọn hết mọi provider. Trả số slot được mở."""
    _load_burns()
    with _LOCK:
        if provider is None:
            n = sum(len(v) for v in _burns.values())
            _burns.clear()
        else:
            n = len(_burns.get(provider) or {})
            _burns.pop(provider, None)
        _save_burns()
    return n


def ring_status(provider: str, settings: dict = None) -> dict:
    """Trạng thái vòng quay cho UI: số key, mấy cái đang cháy, đuôi key (KHÔNG lộ key)."""
    _load_burns()
    ks = keys_for(provider, settings)
    now = time.time()
    slots = []
    for k in ks:
        ent = (_burns.get(provider) or {}).get(_fp(k)) or {}
        until = float(ent.get("until") or 0)
        slots.append({"tail": _tail(k),
                      "burned": until > now,
                      "until": until if until > now else 0,
                      "why": (ent.get("why") or "")[:200],
                      "uses": int(ent.get("uses") or 0),
                      "tin": int(ent.get("tin") or 0),
                      "tout": int(ent.get("tout") or 0)})
    return {"provider": provider, "total": len(ks),
            "burned": sum(1 for s in slots if s["burned"]), "keys": slots}


def all_ring_status(settings: dict = None) -> list:
    return [ring_status(p, settings) for p in RING_PROVIDERS]


def set_keys(provider: str, keys, settings: dict = None) -> int:
    """Thay TOÀN BỘ vòng key của provider (dán mỗi dòng một key). key[0] -> trường chính,
    phần còn lại -> <provider>_keys. Trả số key đã lưu. Chủ động dọn burn khi vòng đổi:
    một key bị xoá khỏi vòng không được để lại fingerprint cháy ám key khác cùng đuôi."""
    field = KEY_FIELD.get(provider)
    if not field:
        return 0
    if isinstance(keys, str):
        keys = re.split(r"[,\n\r]+", keys)
    clean, seen = [], set()
    for k in keys or []:
        k = (k or "").strip()
        if k and k not in seen:
            seen.add(k)
            clean.append(k)
    s = settings if settings is not None else cfgmod.read_settings()
    m = s.setdefault("model", {})
    if clean:
        m[field] = clean[0]
    m[provider + "_keys"] = clean[1:]
    if settings is None:
        cfgmod.write_settings(s)
    # Vòng đổi thì trạng thái cháy của fingerprint cũ không còn ý nghĩa - mở hết cho
    # provider này rồi để lượt tới tự đánh dấu lại cái nào thật sự chết.
    _load_burns()
    with _LOCK:
        live = {_fp(k) for k in clean}
        slots = _burns.get(provider) or {}
        stale = [fp for fp in slots if fp not in live]
        for fp in stale:
            slots.pop(fp, None)
        _save_burns()
    return len(clean)


# ── Nhận diện lỗi quota + thời gian chờ ─────────────────────────────────────────────────
_QUOTA_RE = (
    r"\b429\b", r"too many requests", r"rate.?limit", r"resource.?exhaust",
    r"insufficient.?quota", r"quota\b", r"tokens? per (minute|day)",
    r"requests? per (minute|day|second)", r"\brpm\b|\btpm\b|\brpd\b|\btpd\b",
    r"usage limit", r"credit balance", r"billing", r"quota exceeded",
    r"exceeded your (current |)quota", r"hit your usage limit",
    r"hết hạn mức", r"hết lượt", r"vượt hạn mức", r"hết quota",
    # auth của KEY RIÊNG: key chết -> xoay key kế là đúng (khác với mất đăng nhập plan).
    r"invalid api key", r"api key not valid", r"incorrect api key",
    r"authentication.?fail", r"\b401\b", r"\b403\b",
)


def quota_error(text: str) -> bool:
    """Thông điệp lỗi này có phải dạng 'key này không gọi được nữa' (quota/rate/auth)
    mà xoay sang key khác có ích không."""
    low = (text or "").lower()
    return any(re.search(p, low) for p in _QUOTA_RE)


def burn_cooldown(text: str) -> float:
    """Ước lượng key nên nằm cháy bao lâu, suy từ nội dung lỗi (giây)."""
    low = (text or "").lower()
    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*(s|m|h|giay|giây|phut|phút|gio|giờ)", low)
    if m:
        v, u = float(m.group(1)), m.group(2)
        sec = v * 3600 if u in ("h", "gio", "giờ") else v * 60 if u in ("m", "phut", "phút") else v
        return min(sec + 10.0, 7200.0)
    if re.search(r"per day|daily|each day|day limit|rpd|tpd|mỗi ngày|trong ngày|hạn mức ngày", low):
        # Đa số free quota reset theo UTC - chờ tới nửa đêm UTC + 5 phút đệm.
        now = time.time()
        return max(60.0, (int(now // 86400) + 1) * 86400 + 300.0 - now)
    if re.search(r"per minute|rpm|tpm|mỗi phút", low):
        return 75.0
    return 300.0
