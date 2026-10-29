"""Engine cho VIỆC NỀN (loop, việc Kanban, nhắc hẹn, tự học, tiêu hoá nguồn).

Trước đây việc nền luôn chạy bằng Claude Code, ô chọn ở trang Model bị khoá cứng vào
danh sách model của provider 'anthropic-cli' - muốn đẩy việc nền sang gói ChatGPT hay
một API rẻ để đỡ hạn mức Claude thì không có đường. Module này mở đường đó.

Cách nối vào (cố ý ít xâm lấn): các nơi chạy nền VẪN dựng engine Claude y như cũ, kèm
đủ allowlist/mode/MCP mà chúng vốn tính toán; xong xuôi mới gọi `swap()`. Nếu người dùng
để mặc định Claude thì `swap()` trả lại đúng engine đó, không đổi gì. Chọn provider khác
thì `swap()` đọc chính các thuộc tính engine Claude đã tính (system_prompt, cwd, vault,
mode, allowlist) và dựng engine tương ứng - nên mọi quyết định an toàn ở đầu kia được
thừa hưởng nguyên vẹn, không phải chép lại.

Ba loại engine, khác nhau ở CÔNG CỤ có được - đây là chỗ phải cẩn thận:
- anthropic-cli: Claude Code. Tool file native + Bash + MCP, chặn theo allowlist per-call.
- openai-oauth: Codex CLI, cũng là agent thật (đọc/ghi file + MCP qua profile joyce).
  Sandbox của Codex ánh xạ theo mode: suggest -> read-only, auto -> workspace-write,
  full -> toàn quyền. KHÔNG có allowlist per-call như Claude nên chỉ chặn ở tầng sandbox.
- grok-cli: Grok Build CLI chạy bằng gói SuperGrok / X Premium+. Cũng agent thật (tool file +
  MCP hub qua .grok/config.toml trong brain). Mức quyền xuống thẳng cờ chặn của CLI:
  suggest -> chặn Write/Edit/Bash, auto -> chặn Bash, full -> không chặn ở tầng CLI.
- api (openrouter/openai/gemini/anthropic-api): KHÔNG có tool native. Bù lại hub cấp
  joyce_read_file / joyce_list_dir / joyce_write_file / joyce_use_skill + tool MCP, và
  joyce_write_file tự chặn khi mode là suggest (mcp_hub._builtin_tools). Không có Bash,
  không có WebFetch - hẹp hơn Claude, nhưng đủ cho việc nền đọc/ghi ghi chú trong vault.

Hợp đồng sự kiện giữ y như ClaudeSDK để nơi gọi không phải sửa: query() sinh dict
{"type": "tool_call"|"final"|"error"|"usage", ...}. Đường API sinh "text" nhiều mảnh nên
ở đây gom lại thành đúng MỘT "final" ở cuối - việc nền đều chỉ đọc sự kiện final.
"""
from __future__ import annotations

import os
import re
import sys
import time
from typing import Optional

import config as cfgmod
import task_router

CLAUDE = "anthropic-cli"
CODEX = "openai-oauth"
GROK_CLI = "grok-cli"
ANTIGRAVITY = "antigravity-cli"
API_PROVIDERS = ("openrouter", "openai", "gemini", "groq", "deepseek", "zai", "anthropic-api", "ollama",
                 "ollama-local", "openai-compat")

# provider -> tên trường chứa API key trong settings["model"]. Bản chuẩn nằm ở
# task_router.KEY_FIELD (nhà của vòng quay nhiều key); alias để mã cũ đọc _KEY_FIELD vẫn chạy.
_KEY_FIELD = task_router.KEY_FIELD

# mode của Joyce -> sandbox của Codex CLI. Bản đồ thật nằm ở `claude_cli.codex_sandbox_cho_mode`
# (nó còn đọc cờ JOYCE_CODEX_SANDBOX); giữ dict này để mã cũ đọc tên mức vẫn chạy.
_CODEX_SANDBOX = {"suggest": "read-only", "auto": "workspace-write", "full": None}

# ── Final "mất đăng nhập" phải bị coi là engine CHẾT, không phải kết quả ──────────────────
# Claude Code chưa đăng nhập KHÔNG trả event error: ResultMessage lỗi vẫn có chữ nên
# claude_sdk_engine map thành một FINAL ngắn "Not logged in · Please run /login".
# _FallbackChain mà tin final đó là thành công thì mắt sau không bao giờ được thử.
# Ca thật 26/08: máy chỉ đăng nhập Gemini, việc nền mặc định Claude → vòng tự học nào
# cũng chết với đúng câu này, nhật ký chỉ ghi "không parse được manifest" khó hiểu.
# Danh sách mẫu đồng bộ TAY với connect_health._ENGINE_AUTH_PATTERNS (không import -
# module này phải test đứng một mình được, xem tests/python/test_aux_fallback.py).
_AUTH_FINAL_PATTERNS = ("please run /login", "not logged in", "invalid api key",
                        "api key not found", "failed to authenticate",
                        "oauth session expired", "oauth token has expired",
                        "could not be refreshed", "refresh token was already used",
                        "log out and sign in again")
_AUTH_FINAL_MAX = 400   # câu lỗi đăng nhập luôn ngắn; final dài là nội dung thật, đừng nghi oan


def final_loi_dang_nhap(text: str) -> bool:
    """Final này có phải câu báo mất đăng nhập của engine CLI không."""
    t = (text or "").strip()
    if not t or len(t) > _AUTH_FINAL_MAX:
        return False
    low = t.lower()
    return any(p in low for p in _AUTH_FINAL_PATTERNS)


def _final_het_luot(engine, content) -> bool:
    """Final này có phải câu báo HẾT LƯỢT gói thuê bao (Claude/Codex...) không.

    Hai rào: câu báo phải CHIẾM TRỌN output (subscription_dominates - bài viết thật trích
    câu đó không tính) VÀ bộ phân tích nhận đúng dạng hạn mức (parse_subscription_limit).
    engine_hint lấy theo provider của mắt để nhận đúng tên gói. Lỗi/thiếu module -> False:
    khi không chắc thì coi là nội dung thật, không nuốt kết quả của người dùng."""
    try:
        import limit_learner
        raw = str(content or "")
        if not limit_learner.subscription_dominates(raw):
            return False
        hint = limit_learner.ENGINE_HINT_BY_PROVIDER.get(
            getattr(engine, "provider", "") or "", "")
        return limit_learner.parse_subscription_limit(raw, engine_hint=hint) is not None
    except Exception:   # noqa: BLE001
        return False

# ── Trần wall-clock cho fork NỀN (nhắc hẹn/cron, việc Kanban, bước workflow) ──────────────
# Mặc định 3600s (1 giờ). Trước đây mỗi nơi ghim một số cứng (nhắc hẹn 300, workflow 300,
# Kanban 600) và 300s giết chết việc nền THẬT của người dùng: quét 11 phân mục Meta Ads +
# ghi Google Sheet + gửi Telegram bị chặt ngang lúc đang ghi dở, result rỗng (báo 18/08).
# Trần này là LƯỚI ĐỠ chống fork treo vô hạn, không phải công cụ quản chi phí - fork đơ
# thật thì watchdog idle-timeout của engine bắt sớm hơn nhiều, nên đặt trần theo việc nền
# DÀI NHẤT hợp lệ chứ không theo việc trung bình. Chỉnh qua env JOYCE_BG_MAX_WALL_S
# (giây; giá trị rác hoặc <= 0 thì về mặc định).
BG_MAX_WALL_S_DEFAULT = 3600


def bg_max_wall_s() -> int:
    try:
        v = int(os.getenv("JOYCE_BG_MAX_WALL_S", "") or 0)
        if v > 0:
            return v
    except (TypeError, ValueError):
        pass
    return BG_MAX_WALL_S_DEFAULT

# ── Chọn model FREE mạnh nhất trên OpenRouter (mắt xích cuối của router việc nền) ──
# Xếp hạng theo HỌ model (đầu danh sách = mạnh nhất) rồi tới cỡ tham số trong id, rồi context.
# Danh sách model free của OpenRouter đổi liên tục nên chấm điểm động thay vì ghim cứng 1 tên.
_FREE_FAMILY_RANK = ("deepseek-r1", "deepseek", "qwen3", "qwen", "llama-4", "llama-3.3",
                     "llama", "glm", "gemini", "mistral", "kimi")
_OR_FREE_CACHE = {"ts": 0.0, "model": ""}   # cache 6h - khỏi gọi API models mỗi lần fallback
_OR_FREE_TTL = 6 * 3600


def _score_free_model(mid: str, ctx: int = 0) -> tuple:
    low = (mid or "").lower()
    fam = 0
    for i, f in enumerate(_FREE_FAMILY_RANK):
        if f in low:
            fam = len(_FREE_FAMILY_RANK) - i
            break
    sizes = [int(x) for x in re.findall(r"(\d{1,4})b\b", low)]
    return (fam, max(sizes, default=0), ctx)


async def pick_openrouter_free(key: str = "") -> str:
    """Model free mạnh nhất đang có trên OpenRouter. Lỗi mạng → đoán tĩnh một id phổ biến."""
    now = time.time()
    if _OR_FREE_CACHE["model"] and now - _OR_FREE_CACHE["ts"] < _OR_FREE_TTL:
        return _OR_FREE_CACHE["model"]
    data = []
    try:
        import httpx
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        async with httpx.AsyncClient(timeout=20) as cx:
            r = await cx.get("https://openrouter.ai/api/v1/models", headers=headers)
            r.raise_for_status()
            data = (r.json() or {}).get("data") or []
    except Exception as e:
        print(f"[aux router] không tải được danh sách model OpenRouter: {e}", file=sys.stderr)
    best, best_score = "", (-1, -1, -1)
    for m in data:
        mid = m.get("id") or ""
        if not mid.endswith(":free"):
            continue
        score = _score_free_model(mid, int(m.get("context_length") or 0))
        if score > best_score:
            best, best_score = mid, score
    if not best:
        best = "deepseek/deepseek-chat:free"
    _OR_FREE_CACHE.update(ts=now, model=best)
    return best


def read_spec(settings: dict = None, tag: str = None) -> dict:
    """{'provider','model'} của model việc nền. Cấu hình cũ chỉ có 'model' (luôn là alias
    Claude) nên thiếu provider = anthropic-cli - giữ nguyên hành vi bản cũ.

    `tag` (1.3.17): loại tác vụ đang chạy. Trang Phân việc não gán từng loại một provider/
    model riêng trong settings.model.task_models (task_router.spec_for_tag); tag=None hoặc
    loại chưa gán thì vẫn về model việc nền chung (auxiliary) như cũ.

    PHANH NGÂN SÁCH: nếu tháng này đã tiêu quá trần tiền người dùng đặt VÀ họ đã bật tự
    phanh, việc nền không được tiêu thêm tiền mặt nữa. Nó không dừng lại - nó chuyển sang
    đường KHÔNG tính tiền theo token: gói thuê bao đang đăng nhập, hoặc model free của
    OpenRouter. Chat của người dùng KHÔNG bị đụng tới; chỉ việc chạy nền bị hạ, vì đó là
    phần tiêu tiền lúc người ta không ngồi nhìn.
    """
    s = settings if settings is not None else cfgmod.read_settings()
    if tag:
        try:
            spec = task_router.spec_for_tag(tag, s)
        except Exception:                    # noqa: BLE001 - lỗi tra loại thì về auxiliary
            spec = None
    else:
        spec = None
    if spec is None:
        aux = (s.get("model", {}) or {}).get("auxiliary") or {}
        spec = {"provider": (aux.get("provider") or CLAUDE), "model": (aux.get("model") or "")}
    if spec["provider"] not in API_PROVIDERS:
        return spec                      # gói thuê bao: không tính tiền theo token, kệ phanh
    try:
        import usage_saving
        if not usage_saving.dang_phanh().get("bat"):
            return spec
    except Exception:                    # noqa: BLE001 - thiếu module thì cứ chạy như cũ
        return spec
    return _spec_ne_tien(s, spec)


def _spec_ne_tien(s: dict, spec: dict) -> dict:
    """Đường thay thế khi phanh: ưu tiên gói thuê bao đã đăng nhập, cuối cùng là OpenRouter free.

    `availability` trả True VÔ ĐIỀU KIỆN cho anthropic-cli (nó không kiểm binary `claude` có
    trên máy hay không, khác hẳn nhánh Codex/Gemini). Nên nếu chỉ hỏi availability thì vòng
    này luôn dừng ở mắt đầu, và trên máy KHÔNG cài Claude Code việc nền bị đẩy sang một engine
    không chạy được - phanh biến thành cái làm chết việc nền. Phải hỏi thẳng binary.
    """
    for prov in (CLAUDE, CODEX):
        ok, _ly_do = availability({"provider": prov}, s)
        if ok and _co_binary(prov):
            return {"provider": prov, "model": ""}
    if api_key_for("openrouter", s):
        # model "" trên OpenRouter = tự chọn model FREE mạnh nhất lúc chạy (_ApiAuxEngine.query).
        return {"provider": "openrouter", "model": ""}
    return spec                          # không có đường nào rẻ hơn -> giữ nguyên, đừng làm chết việc nền


def _co_binary(prov: str) -> bool:
    """Engine CLI đó có thật trên máy không. Lỗi/thiếu module -> False (đừng đoán là có)."""
    try:
        import claude_cli
        if prov == CLAUDE:
            return bool(claude_cli.find_claude_cli())
        if prov == CODEX:
            return bool(claude_cli.find_codex_cli())
    except Exception:   # noqa: BLE001 - không dò được thì coi như không có, rồi thử mắt sau
        return False
    return False


def main_spec(settings: dict = None) -> dict:
    """{'provider','model'} của MAIN MODEL (bộ não người dùng chọn ở trang Models).

    Bản rút của main._effective_main - chép lại thay vì import main (module này không được
    import main, tránh vòng). Dùng làm MẮT DỰ PHÒNG cho việc nền: người để trống model phụ
    thì aux mặc định Claude, nhưng máy chỉ đăng nhập Gemini/OpenAI... thì Claude chết và
    việc nền chết theo dù bộ não CHÍNH vẫn chạy ngon - chuỗi fallback phải biết tới nó.
    """
    s = settings if settings is not None else cfgmod.read_settings()
    m = s.get("model", {}) or {}
    main = m.get("main") or {}
    if main.get("provider"):
        return {"provider": main["provider"], "model": main.get("model") or ""}
    eng = m.get("engine")
    if eng == "openrouter":
        return {"provider": "openrouter", "model": m.get("openrouter_model") or ""}
    if eng == "anthropic-api":
        return {"provider": "anthropic-api", "model": m.get("claude_model") or ""}
    return {"provider": CLAUDE, "model": m.get("claude_model") or ""}


def is_claude(spec: dict) -> bool:
    return (spec or {}).get("provider", CLAUDE) == CLAUDE


def api_key_for(provider: str, settings: dict = None) -> str:
    field = _KEY_FIELD.get(provider)
    if not field:
        return ""
    s = settings if settings is not None else cfgmod.read_settings()
    m = s.get("model", {}) or {}
    if provider == "openai-compat":
        # Có Base URL là chạy được; khoá rỗng thì gửi "none" (endpoint không đòi xác thực).
        return (m.get(field) or "none") if (m.get("openai_compat_base") or "").strip() else ""
    if provider == "ollama-local":
        # Endpoint quyết định, khoá có thể rỗng - lấy key đầu vòng nếu ai đó điền thêm.
        ks = task_router.keys_for(provider, s)
        return ks[0] if ks else ""
    # 1.3.17: vòng quay nhiều key - trả key chưa bị đánh dấu cháy; hết key sạch -> ""
    # để caller/availability coi engine như không sẵn sàng và fallback sang mắt sau.
    return task_router.pick_key(provider, s)


def availability(spec: dict, settings: dict = None) -> tuple:
    """(dùng được?, lý do nếu không). Để trang Model cảnh báo TRƯỚC khi người dùng chọn
    nhầm một provider chưa đăng nhập / chưa có key rồi việc nền chết lặng lẽ."""
    prov = (spec or {}).get("provider", CLAUDE)
    if prov == CLAUDE:
        return True, ""
    if prov == CODEX:
        try:
            from claude_cli import find_codex_cli
            if not find_codex_cli():
                return False, "Chưa cài Codex CLI (cần đăng nhập gói ChatGPT)."
        except Exception:
            return False, "Không kiểm tra được Codex CLI."
        return True, ""
    if prov == GROK_CLI:
        try:
            import grok_cli as _g
            st = _g.auth_status()
            if not st.get("connected"):
                return False, st.get("error") or "Grok Build CLI chưa sẵn sàng."
        except Exception:
            return False, "Không kiểm tra được Grok Build CLI."
        return True, ""
    if prov == ANTIGRAVITY:
        try:
            import antigravity_cli as _a
            if not _a.find_antigravity_cli():
                return False, "Chưa cài Antigravity CLI (`agy`) trên máy chạy Joyce."
            # Bản NỀN (đọc cache, làm mới bằng thread), KHÔNG phải auth_status(): hàm này chạy
            # ngay trong code async (học sau lượt chat, việc Kanban, nhắc hẹn, loop), mà
            # auth_status() hỏi thẳng `agy models` tới 80 giây. Cả app đứng theo: chủ repo đổi
            # trợ lý giữa lúc Gemini đang chạy thì màn hình không đổi (23/09).
            # "dang_kiem" = mới khởi động, chưa có kết quả: cứ cho chạy, lượt thật tự báo lỗi.
            st = _a.auth_status_nen()
            if not st.get("connected") and not st.get("dang_kiem"):
                return False, st.get("error") or "Antigravity CLI chưa đăng nhập Google."
        except Exception:
            return False, "Không kiểm tra được Antigravity CLI."
        return True, ""
    # Ollama máy nhà xét theo ĐỊA CHỈ, không theo khoá: Ollama trần không có xác thực nên
    # khoá rỗng là trạng thái BÌNH THƯỜNG. Để nó rơi vào nhánh kiểm khoá bên dưới thì mọi
    # agent dùng model local đều bị báo "chưa có API key" dù đang chạy ngon.
    if prov == "ollama-local":
        s = settings if settings is not None else cfgmod.read_settings()
        if not (s.get("model", {}) or {}).get("ollama_local_endpoint"):
            return False, "Chưa đặt địa chỉ Ollama - vào trang Models, tab Local Model."
        return True, ""
    if prov == "openai-compat":
        s = settings if settings is not None else cfgmod.read_settings()
        if not (s.get("model", {}) or {}).get("openai_compat_base"):
            return False, "Chưa đặt Base URL cho OpenAI Compatible - vào trang Models."
        return True, ""
    if prov in API_PROVIDERS:
        if not api_key_for(prov, settings):
            return False, f"Chưa có API key cho {prov} - vào trang Model dán key trước."
        return True, ""
    return False, f"Provider lạ: {prov}"


class _ApiAuxEngine:
    """Engine việc nền chạy bằng provider API, mang hợp đồng của ClaudeSDK.

    Công cụ lấy từ hub (builtin file vault + MCP). Hub tự chặn ghi khi mode=suggest, nên
    loop chế độ chỉ-đọc vẫn chỉ-đọc dù chạy trên engine này.
    """

    def __init__(self, provider, model, system_prompt=None, vault_root=None,
                 mode="full", tag="aux", reasoning="off"):
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.vault_root = vault_root
        self.joyce_mode = mode
        self.tag = tag
        self.reasoning = reasoning
        self.session_id = None      # engine API không có phiên nối tiếp - giữ cho đủ hợp đồng

    def is_available(self) -> bool:
        return bool(api_key_for(self.provider))

    def reset_session(self):
        self.session_id = None

    async def query(self, prompt: str):
        import engine as eng
        import mcp_hub

        # Vòng quay nhiều key (task_router, 1.3.17): key chưa 'cháy' xếp trước; key bị
        # quota/429/auth từ chối thì đánh dấu cháy và thử ngay key kế TRONG CÙNG lượt,
        # trước khi chuỗi fallback tới mắt sau. ollama-local trần có key "" vẫn là một
        # slot hợp lệ; provider nào key bắt buộc mà ring chỉ có "" thì báo thiếu key.
        ring = task_router.usable_keys(self.provider) or [""]
        if not any(ring):
            import localefmt
            yield {"type": "error", "content": localefmt.chu(f"Chưa có API key cho {self.provider}.",
                                                             f"No API key for {self.provider}.")}
            return

        # OpenRouter model trống = "tự chọn free mạnh nhất". User ghi đè bằng
        # settings model.fallback_openrouter_model; lần chọn tự động đầu tiên cũng lưu vào
        # đúng field đó để user thấy đang dùng gì và đổi sau nếu muốn.
        if self.provider == "openrouter" and not self.model:
            try:
                s = cfgmod.read_settings()
                override = ((s.get("model", {}) or {}).get("fallback_openrouter_model") or "").strip()
                self.model = override or await pick_openrouter_free(ring[0])
                if not override and self.model:
                    s.setdefault("model", {})["fallback_openrouter_model"] = self.model
                    cfgmod.write_settings(s)
            except Exception as e:
                print(f"[aux router] chọn model free lỗi: {e}", file=sys.stderr)
            if not self.model:
                import localefmt
                yield {"type": "error", "content": localefmt.chu("Không chọn được model free OpenRouter.",
                                                                 "Could not pick a free OpenRouter model.")}
                return

        tools, route = [], {}
        # `no_tools` (strip_tools): text-only turn on untrusted input, so the hub is never asked for anything.
        if not getattr(self, "no_tools", False):
            try:
                tools, route = await mcp_hub.discover_all(self.joyce_mode or "full",
                                                          vault_root=self.vault_root)
            except Exception as e:
                print(f"[aux discover] {e}", file=sys.stderr)

        messages = []
        sysprompt = self.system_prompt or ""
        # Khai THẬT năng lực của engine này. Không có dòng này, model chỉ thấy "gọi tool X
        # không được" rồi tự dựng một lý do nghe hợp lý mà sai - hay gặp nhất là đổ cho quyền
        # ("phiên này bị chặn quyền"), khiến chủ đi sửa mức quyền trong khi mức quyền không hề
        # sai. Nói rõ THIẾU GÌ và VÌ SAO thì câu báo về mới dẫn đúng tới việc cần làm.
        sysprompt += (
            "\n\n[Sự thật hệ thống - năng lực của phiên này] Bạn đang chạy bằng engine API "
            f"'{self.provider}', KHÔNG phải Claude Code. Bạn có: các tool qua MCP Hub của Joyce "
            "(gồm tool đọc/ghi file trong vault và mọi MCP người dùng đã đấu vào Joyce). "
            "Bạn KHÔNG có: lệnh máy (Bash), tự mở URL (WebFetch/WebSearch), và KHÔNG có các "
            "connector gắn thẳng vào TÀI KHOẢN Claude - Gmail, Google Drive, Google Calendar "
            "gọi bằng tool native `mcp__<tên>__*` chỉ tồn tại trên engine Claude Code. "
            "Nếu việc được giao cần một trong những thứ đó, hãy nói THẲNG là engine hiện tại "
            "không có công cụ ấy và chủ cần đổi model việc nền sang Claude Code. TUYỆT ĐỐI "
            "không mô tả chuyện này là bị chặn quyền hay thiếu quyền: mức quyền không liên "
            "quan, đây là chuyện engine nào có tool nào."
        )
        if sysprompt.strip():
            messages.append({"role": "system", "content": sysprompt})
        messages.append({"role": "user", "content": prompt})

        # Đường API sinh "text" theo mảnh; việc nền chỉ đọc "final" nên gom lại rồi phát MỘT lần.
        # Mỗi lần thử một key của ring: lỗi quota/auth -> burn + key kế; lỗi khác -> trả luôn
        # (xoay key không cứu được lỗi server/prompt); hết key -> trả lỗi cuối để chuỗi
        # fallback sang mắt engine khác.
        last_err = None
        for key in ring:
            if tools:
                fn = {"openrouter": eng.openrouter_chat_with_mcp,
                      "openai": eng.openai_chat_with_mcp,
                      "gemini": eng.gemini_chat_with_mcp, "groq": eng.groq_chat_with_mcp,
                      "deepseek": eng.deepseek_chat_with_mcp,
                      "zai": eng.zai_chat_with_mcp,
                      "anthropic-api": eng.anthropic_chat_with_mcp,
                      "ollama": eng.ollama_chat_with_mcp,
                      "ollama-local": eng.ollama_local_chat_with_mcp,
                      "openai-compat": eng.openai_compat_chat_with_mcp}[self.provider]
                stream = fn(key, self.model, messages, self.reasoning, tools, route)
            else:
                fn = {"openrouter": eng.openrouter_stream, "openai": eng.openai_stream,
                      "gemini": eng.gemini_stream, "groq": eng.groq_stream,
                      "deepseek": eng.deepseek_stream,
                      "zai": eng.zai_stream,
                      "anthropic-api": eng.anthropic_stream,
                      "ollama": eng.ollama_stream,
                      "ollama-local": eng.ollama_local_stream,
                      "openai-compat": eng.openai_compat_stream}[self.provider]
                stream = fn(key, self.model, messages, self.reasoning)
            buf = []
            err = None
            async for ev in stream:
                t = ev.get("type")
                if t == "text":
                    buf.append(ev.get("content") or "")
                elif t == "usage":
                    self._ghi_muc_dung(ev)
                    try:
                        task_router.note_use(self.provider, key,
                                             ev.get("input", 0), ev.get("output", 0))
                    except Exception:
                        pass
                    yield ev
                elif t == "tool_call":
                    yield ev
                elif t == "error":
                    err = ev.get("content") or "lỗi không rõ"
                    break
            if err is None:
                yield {"type": "final", "content": "".join(buf)}
                return
            if key and task_router.quota_error(err):
                task_router.burn_key(self.provider, key, err, task_router.burn_cooldown(err))
                print(f"[aux keyring] {self.provider} key {task_router._tail(key)} cháy "
                      f"({err[:120]}) → thử key kế", file=sys.stderr)
                last_err = err
                continue
            yield {"type": "error", "content": err}
            return
        yield {"type": "error",
               "content": last_err or f"Mọi key của {self.provider} đều không gọi được."}

    def _ghi_muc_dung(self, ev: dict) -> None:
        """Cộng lượt việc nền này vào sổ mức dùng.

        Đây là chỗ DUY NHẤT việc nền chạy bằng API key đi qua. Trước đây không có nó: cả 12
        chỗ gọi `usage_store.record` trong repo đều nằm trên đường CHAT, còn loop / việc
        Kanban / nhắc hẹn / tự học đều chạy qua đây và không ghi gì. Hệ quả là trang Mức dùng
        không thấy phần token nền của nhánh API, và tệ hơn: trần tiền tháng cùng cái phanh
        ngân sách không nhìn thấy ĐÚNG khoản chi mà chúng sinh ra để chặn - việc nền tiêu tiền
        lúc không ai ngồi nhìn.

        Best-effort: hỏng thì nuốt, một cái sổ đếm không được phép làm chết việc nền.
        """
        try:
            import usage_store
            usage_store.record(self.provider, self.model,
                               ev.get("input", 0), ev.get("output", 0), ev.get("cost", 0) or 0)
        except Exception as e:  # noqa: BLE001
            print(f"[aux usage] {type(e).__name__}: {e}", file=sys.stderr)


class _FallbackChain:
    """Router việc nền: CHUỖI engine thử lần lượt, mắt trước chết LÚC CHẠY (hết quota, CLI
    lỗi, stream câm không final, không sẵn sàng) thì chạy lại nguyên prompt bằng mắt sau.
    Chuỗi điển hình: engine phụ user chọn → Claude → OpenRouter model free mạnh nhất.
    Triết lý của swap() vốn là "việc nền phải chạy chứ không chết" nhưng trước đây chỉ đỡ
    được lỗi lúc DỰNG (thiếu key/CLI); lỗi lúc chạy thì chết thật - ca thật: Codex "You've
    hit your usage limit" làm nhắc hẹn chỉ báo ⚠ về Telegram rồi thôi.
    Trong suốt với nơi gọi: đọc attr → mắt đầu; GÁN attr (max_wall_s...) → đặt cho MỌI mắt
    để engine dự phòng cũng nhận giới hạn/cấu hình mà caller đặt sau swap()."""

    def __init__(self, engines, safe_retry=False):
        object.__setattr__(self, "_engines", [e for e in (engines or []) if e is not None])
        # safe_retry (việc mức full): chỉ được nhảy sang mắt kế tiếp khi mắt trước chết mà
        # CHƯA gọi tool nào - tức nó chưa hề làm gì, đổi engine không thể nhân đôi hành
        # động ra ngoài. Mắt đã gọi tool rồi mới gãy (đăng 1/3 bài xong chết) thì DỪNG và
        # báo đúng lỗi gốc, vì chạy lại nguyên prompt bằng engine khác có thể làm việc đó
        # một lần nữa. Đây là điều kiện duy nhất khiến full được có chuỗi dự phòng.
        object.__setattr__(self, "_safe_retry", bool(safe_retry))

    def _all(self):
        return object.__getattribute__(self, "_engines")

    def __getattr__(self, name):
        return getattr(self._all()[0], name)

    def __setattr__(self, name, value):
        for e in self._all():
            try:
                setattr(e, name, value)
            except Exception:
                pass

    def is_available(self) -> bool:
        for e in self._all():
            try:
                if e.is_available():
                    return True
            except Exception:
                pass
        return False

    def reset_session(self):
        for e in self._all():
            try:
                e.reset_session()
            except Exception:
                pass

    @staticmethod
    def _name(e) -> str:
        return getattr(e, "provider", None) or type(e).__name__

    async def query(self, prompt: str):
        fail = "chuỗi engine việc nền rỗng"
        dau = ""      # lỗi của mắt xích ĐẦU TIÊN thật sự chạy - thường là lỗi có nghĩa nhất
        safe_retry = bool(object.__getattribute__(self, "_safe_retry"))
        for e in self._all():
            saw_tool = False
            try:
                if not e.is_available():
                    fail = f"{self._name(e)} không sẵn sàng"
                    continue
                got_final, got_error = False, None
                async for ev in e.query(prompt):
                    t = (ev or {}).get("type")
                    if t == "error":
                        got_error = ev.get("content") or f"{self._name(e)} trả error"
                        # Hub bắt buộc không lên: mọi mắt sau lấy tool qua đúng hub đó, chạy tiếp
                        # là chạy mù rồi báo xong giả. Dừng cả chuỗi, trả nguyên lỗi
                        # (claude_cli.codex_error_text đã đặt lý do lên đầu).
                        if _hub_bat_buoc_hong(got_error):
                            print(f"[aux router] {self._name(e)}: hub bắt buộc không lên - dừng chuỗi, "
                                  "không thử mắt kế tiếp.", file=sys.stderr)
                            # Giữ cả lỗi của mắt TRƯỚC (vd Claude hết lượt gói): tasks._het_luot
                            # đọc nó để hoãn tới giờ gói mở lại. Lý do hub đứng đầu vì ô lỗi bị cắt.
                            yield {"type": "error",
                                   "content": got_error + (f" | {dau}" if dau else "")}
                            return
                        break
                    # Engine CLI chưa đăng nhập trả một FINAL ngắn kiểu "Not logged in ·
                    # Please run /login" chứ không phải error - nuốt nó lại và coi là mắt
                    # chết, kẻo chuỗi dự phòng tưởng thành công rồi dừng (xem chú thích
                    # ở _AUTH_FINAL_PATTERNS).
                    # Cuộc đua làm mới token Claude: phiên KHÔNG mất, nhưng lượt này hỏng và
                    # việc nền không tự gửi lại được -> vẫn phải nhảy sang mắt kế tiếp. Đọc CỜ
                    # chứ không khớp chữ: câu người đọc đã được viết lại cho dễ hiểu.
                    if t == "final" and ev.get("dua_token"):
                        got_error = (f"{self._name(e)} trùng lúc làm mới phiên đăng nhập "
                                     "(hai lượt cùng dùng một tài khoản)")
                        break
                    if t == "final" and final_loi_dang_nhap(ev.get("content")):
                        got_error = (f"{self._name(e)} mất đăng nhập: "
                                     + (ev.get("content") or "").strip()[:200])
                        break
                    # HẾT LƯỢT GÓI THUÊ BAO CŨNG LÀ MỘT FINAL GIẢ: Claude/Codex in nguyên câu
                    # "resets Oct 26, 10am" vào đúng chỗ câu trả lời chứ không báo error.
                    # Không nuốt nó như final thường thì chuỗi tưởng mắt này THÀNH CÔNG và
                    # dừng - câu hết lượt trở thành "kết quả" của bước (ca thật workflow
                    # tham-muu-tong-hop 24/10). Coi mắt đó là chết, nhảy sang mắt sau.
                    if t == "final" and _final_het_luot(e, ev.get("content")):
                        got_error = (str(ev.get("content") or "").strip()[:400]
                                     or f"{self._name(e)} hết lượt gói thuê bao")
                        break
                    if t == "tool_call":
                        saw_tool = True
                    yield ev
                    if t == "usage":
                        # Sổ theo loại tác vụ cho trang Phân việc não (1.3.19): quy lượt
                        # này về tag việc + đúng provider/model của mắt ĐANG chạy (mắt dự
                        # phòng chạy thì tính cho mắt đó, không phải mắt đầu chuỗi).
                        try:
                            task_router.task_use_note(
                                getattr(self, "_task_tag", "") or getattr(e, "tag", "") or "aux",
                                self._name(e), getattr(e, "model", "") or ev.get("model") or "",
                                ev.get("input") or ev.get("input_tokens") or 0,
                                ev.get("output") or ev.get("output_tokens") or 0,
                                ev.get("cost") or ev.get("cost_usd") or ev.get("total_cost_usd") or 0)
                        except Exception:
                            pass
                        # Đo token THẬT cho lượt chạy này (sổ lượt chạy) và chặn khi vượt trần chủ đặt (settings.tasks.tran_token_luot, mặc định
                        # không chặn). Vượt trần thì DỪNG CẢ CHUỖI: nhảy sang mắt kế tiếp là tốn thêm token chứ không đỡ.
                        try:
                            import run_context
                            import run_ledger
                            _rc = run_context.hien_tai()
                            _tong, _vuot = run_ledger.ghi_usage(_rc.run_id if _rc else "", ev)
                        except Exception:
                            _tong, _vuot = 0, False
                        if _vuot:
                            yield {"type": "error", "content": f"Lượt này đã dùng {_tong:,} token, vượt trần {run_ledger.tran_token_luot():,} token chủ đặt nên dừng."}
                            return
                    if t == "final":
                        got_final = True
                if got_final:
                    return                                       # mắt này chạy ngon → xong
                fail = got_error or f"{self._name(e)} kết thúc mà không có final"
            except Exception as exc:
                fail = f"{self._name(e)}: {type(exc).__name__}: {exc}"
            if safe_retry and saw_tool:
                # full: mắt đã gọi tool rồi mới gãy - có thể đã làm MỘT PHẦN việc ra ngoài.
                # Chạy lại bằng engine khác rủi ro nhân đôi (đăng bài 2 lần, gửi tin 2 lần).
                print(f"[aux router] {self._name(e)} gãy SAU khi đã gọi tool - dừng chuỗi "
                      f"(không chạy lại việc có thể đã làm một phần). Lý do: {str(fail)[:300]}",
                      file=sys.stderr)
                dau = dau or str(fail)
                break
            print(f"[aux router] {self._name(e)} lỗi → thử mắt xích kế tiếp. Lý do: {str(fail)[:300]}",
                  file=sys.stderr)
            dau = dau or str(fail)
        # Hết chuỗi: trả CẢ lỗi đầu lẫn lỗi cuối. Chỉ trả lỗi cuối ("openrouter không sẵn sàng")
        # là câu "hết lượt gói Claude" của mắt đầu bị nuốt, và hàng đợi việc không nhận ra để hoãn
        # tới giờ gói mở lại (tasks._het_luot đọc câu này).
        noi = str(fail) if (not dau or dau == str(fail)) else f"{dau} | {fail}"
        yield {"type": "error", "content": noi}


# Provider được phép nằm trong chuỗi dự phòng VIỆC NỀN (settings.model.aux_fallbacks).
# Khác chat_fallbacks (chỉ API): việc nền chạy được cả engine CLI vì _FallbackChain xoay
# theo engine chứ không theo key - nên Codex (đăng nhập Gmail), Grok CLI, Antigravity
# đều được xếp làm mắt. anthropic-cli không có trong danh sách vì nó ĐÃ là mắt mặc định.
AUX_FB_PROVIDERS = (CODEX, GROK_CLI, ANTIGRAVITY) + tuple(API_PROVIDERS)


def _engine_for_spec(sp, claude_cli_obj, mode, tag, codex_profile=None):
    """spec {provider, model} -> engine việc nền tương ứng, hoặc None nếu provider không
    dựng được ở đây. Tách ra để chuỗi dự phòng việc nền (aux_fallbacks) dựng được nhiều
    mắt từ một danh sách spec thay vì chỉ mắt chính."""
    prov = (sp or {}).get("provider")
    if prov == CODEX:
        return _build_codex(sp, claude_cli_obj, mode, tag, codex_profile)
    if prov == GROK_CLI:
        return _build_grok(sp, claude_cli_obj, mode, tag)
    if prov == ANTIGRAVITY:
        return _build_antigravity(sp, claude_cli_obj, mode, tag)
    if prov in API_PROVIDERS:
        return _build_api(sp, claude_cli_obj, mode, tag)
    return None


def _aux_fb_links(cli, mode, tag, settings, primary_sp, codex_profile=None):
    """Dựng các mắt từ settings.model.aux_fallbacks: chuỗi provider chủ tự xếp cho việc
    nền - hết key/quota provider trước thì nhảy provider sau (mỗi nhà vẫn xoay hết vòng
    key của chính nó trước). Bỏ mắt trùng provider+model với mắt chính và mắt không
    khả dụng (thiếu key/chưa cài CLI) để chuỗi không mang xác chết."""
    s = settings if settings is not None else cfgmod.read_settings()
    m = (s.get("model") or {})
    links, seen = [], set()
    if primary_sp:
        seen.add(((primary_sp.get("provider") or ""), (primary_sp.get("model") or "")))
    for e in m.get("aux_fallbacks") or []:
        if not isinstance(e, dict):
            continue
        prov, mdl = (e.get("provider") or "").strip(), (e.get("model") or "").strip()
        if not prov or (prov, mdl) in seen or prov not in AUX_FB_PROVIDERS:
            continue
        seen.add((prov, mdl))
        sp = {"provider": prov, "model": mdl}
        ok, _why = availability(sp, s)
        if not ok:
            continue
        eng = _engine_for_spec(sp, cli, mode, tag, codex_profile)
        if eng is not None:
            links.append(eng)
    return links


def _build_api(spec, claude_cli_obj, mode, tag):
    return _ApiAuxEngine(
        provider=spec["provider"],
        model=spec.get("model") or "",
        system_prompt=getattr(claude_cli_obj, "system_prompt", None),
        vault_root=getattr(claude_cli_obj, "joyce_vault", None),
        mode=mode or getattr(claude_cli_obj, "joyce_mode", None) or "full",
        tag=tag or getattr(claude_cli_obj, "tag", "aux"),
    )


def _build_codex(spec, claude_cli_obj, mode, tag, codex_profile=None):
    from claude_cli import CodexCLI, codex_sandbox_cho_mode
    cc = CodexCLI(cwd=getattr(claude_cli_obj, "cwd", None),
                  tag=tag or getattr(claude_cli_obj, "tag", "aux"),
                  model=spec.get("model") or None,
                  instructions=getattr(claude_cli_obj, "system_prompt", None))
    # Codex không có allowlist per-call như Claude → chặn ở tầng sandbox của chính nó.
    # `codex_sandbox_cho_mode` còn đọc cờ JOYCE_CODEX_SANDBOX: trong Docker, bubblewrap không
    # chạy nổi nên rào đó không phải "chặt hơn" mà là "chết hẳn", và cờ là đường thoát.
    cc.sandbox = codex_sandbox_cho_mode(mode or getattr(claude_cli_obj, "joyce_mode", None) or "full")
    cc.vault_root = getattr(claude_cli_obj, "joyce_vault", None)   # ảnh Codex vẽ về đúng brain
    if codex_profile:
        try:
            cc.profile = codex_profile()   # profile joyce = thấy MCP của Joyce (POS, connector...)
        except Exception as e:
            print(f"[aux codex profile] {e}", file=sys.stderr)
    try:
        import mcp_hub
        mcp_hub.dat_codex_vault(cc.extra_config, getattr(claude_cli_obj, "joyce_vault", None))
        # The job's own level, not the profile's `full` (see mcp_hub.dat_codex_mode).
        mcp_hub.dat_codex_mode(cc.extra_config,
                               mode or getattr(claude_cli_obj, "joyce_mode", None) or "full")
    except Exception as e:
        print(f"[aux codex vault] {e}", file=sys.stderr)
    # Việc nền theo lịch: hub bắt buộc, không app ChatGPT - xem mcp_hub.CODEX_REQUIRED_KEY. Chat
    # không đi qua hàm này, còn workflow Codex dựng engine riêng (main._workflow_agent_helpers),
    # nên chỉ các làn trong la_viec_nen_theo_lich đổi hành vi.
    try:
        if (cc.profile and la_viec_nen_theo_lich(cc.tag)
                and bool(cfgmod.read_settings().get("mcp", {}).get("hub", True))):
            import mcp_hub
            mcp_hub.dat_codex_hub_bat_buoc(cc.extra_config)
            mcp_hub.dat_codex_tat_app(cc.extra_config)
    except Exception as e:
        print(f"[aux codex hub] {e}", file=sys.stderr)
    # Fast mode (0.164.0): background runs never get the bolt. Force the normal tier, or a
    # config.toml with service_tier = "priority" would make every scheduled run fast.
    cc.extra_config[:] = [x for x in cc.extra_config if not str(x).startswith("service_tier=")]
    cc.extra_config.append('service_tier="default"')
    return cc


# Nhãn lượt của việc nền THEO LỊCH: nhắc hẹn, loop, Kanban ("dispatch:<id>:<hậu tố>"). Mắt dự
# phòng dựng từ bộ não chính mang thêm hậu tố "-main" (_main_fallback_engine).
_TAG_VIEC_NEN_THEO_LICH = ("reminder", "loop")


def la_viec_nen_theo_lich(tag) -> bool:
    t = str(tag or "").strip()
    if t.endswith("-main"):
        t = t[:-len("-main")]
    return t in _TAG_VIEC_NEN_THEO_LICH or t.startswith("dispatch:")


def _hub_bat_buoc_hong(text) -> bool:
    try:
        from claude_cli import codex_loi_hub_bat_buoc
        return codex_loi_hub_bat_buoc(text)
    except Exception:
        return False


def _build_grok(spec, claude_cli_obj, mode, tag):
    """Engine việc nền/agent chạy bằng Grok Build CLI (`grok`).

    Mức quyền xuống thẳng cờ `--deny` của CLI chứ không phải một lời hứa trong prompt, và
    `grok_cli.permission_cho_mode` fail-closed (mode lạ về nấc chặt nhất). Cùng vai với sandbox
    của Codex - lớp chặn tool NATIVE, còn rào tiền/đơn/đăng bài vẫn nằm ở MCP Hub.

    Entry MCP dựng bằng `grok_cli.hub_entry()` chứ KHÔNG viết tay: Grok đọc khoá `url`, còn
    `agy` đọc `serverUrl`. Chép nhầm khoá giữa hai engine là không có lấy một tool nào của
    Joyce mà không một câu lỗi nào - đúng thứ đã xảy ra với `agy` mấy bản liền.
    """
    import grok_cli as _g
    muc = mode or getattr(claude_cli_obj, "joyce_mode", None) or "full"
    gc = _g.GrokCLI(cwd=getattr(claude_cli_obj, "cwd", None),
                    tag=tag or getattr(claude_cli_obj, "tag", "aux"),
                    model=spec.get("model") or None,
                    instructions=getattr(claude_cli_obj, "system_prompt", None))
    gc.mode = muc
    vault = getattr(claude_cli_obj, "joyce_vault", None) or getattr(claude_cli_obj, "cwd", None)
    if vault:
        try:
            import mcp_hub
            hub = None
            if bool(cfgmod.read_settings().get("mcp", {}).get("hub", True)):
                hub = _g.hub_entry(mcp_hub.hub_url(),
                                   {"Authorization": f"Bearer {mcp_hub.hub_token()}",
                                    "X-Joyce-Mode": muc, "X-Joyce-Vault": str(vault)})
            _g.ghi_mcp_settings(vault, hub)
        except Exception as e:
            print(f"[aux grok mcp] {e}", file=sys.stderr)
    return gc


def _build_antigravity(spec, claude_cli_obj, mode, tag):
    """Engine việc nền/agent chạy bằng Antigravity CLI (`agy`).

    Khác `_build_grok` ở hai chỗ, và cả hai đều là lý do phải viết riêng thay vì dùng chung:

    - **Mức quyền yếu hơn thật.** `agy` KHÔNG có cờ chặn per-tool như `--deny` của Grok;
      `suggest` ở đây chỉ được siết bằng `--sandbox` cộng lời dặn trong prompt. Xem
      `antigravity_cli.co_quyen_cho_mode` - nó nói thẳng chuyện này, và rào tiền/đơn/đăng bài
      vẫn nằm ở MCP Hub chứ không ở CLI.
    - **Hình dạng entry MCP khác hẳn.** `agy` đọc khoá `serverUrl`, Grok đọc `url`. Chép nhầm
      khoá là engine chạy trơn tru mà không có lấy một tool nào của Joyce, không một tiếng
      động - đúng thứ đã xảy ra mấy bản liền. Nên dựng entry bằng `antigravity_cli.hub_entry()`
      chứ không viết tay.
    """
    import antigravity_cli as _a
    muc = mode or getattr(claude_cli_obj, "joyce_mode", None) or "full"
    ac = _a.AntigravityCLI(cwd=getattr(claude_cli_obj, "cwd", None),
                           tag=tag or getattr(claude_cli_obj, "tag", "aux"),
                           model=spec.get("model") or None,
                           instructions=getattr(claude_cli_obj, "system_prompt", None))
    ac.mode = muc
    vault = getattr(claude_cli_obj, "joyce_vault", None) or getattr(claude_cli_obj, "cwd", None)
    if vault:
        try:
            import mcp_hub
            hub = None
            if bool(cfgmod.read_settings().get("mcp", {}).get("hub", True)):
                hub = _a.hub_entry(mcp_hub.hub_url(),
                                   {"Authorization": f"Bearer {mcp_hub.hub_token()}",
                                    "X-Joyce-Mode": muc, "X-Joyce-Vault": str(vault)})
            _a.ghi_mcp_settings(vault, hub)
        except Exception as e:
            print(f"[aux antigravity mcp] {e}", file=sys.stderr)
    return ac


def apply(deps, cli, mode: str = None, tag: str = None):
    """Dùng ở các nơi chạy nền sau khi đã dựng xong engine Claude.

    deps.aux_swap được main tiêm; thiếu nó (unit test dựng deps tối giản) thì rơi về cách
    cũ - chỉ đặt model - nên test cũ không phải sửa và hành vi không đổi.
    """
    fn = getattr(deps, "aux_swap", None)
    if fn:
        return fn(cli, mode=mode, tag=tag)
    getter = getattr(deps, "aux_model", None)
    if getter:
        cli.model = getter() or None
    return cli


def _main_fallback_engine(cli, mode, tag, settings, exclude, codex_profile=None):
    """Mắt dự phòng dựng từ BỘ NÃO CHÍNH của người dùng, hoặc None nếu không dựng được.

    exclude = tập provider đã có mặt trong chuỗi (aux + Claude) - trùng thì khỏi thêm.
    Provider không có builder nền (ollama, antigravity-cli) trả None, chuỗi còn lại lo.
    """
    sp = main_spec(settings)
    prov = sp.get("provider") or ""
    if not prov or prov == CLAUDE or prov in (exclude or set()):
        return None
    ok, _why = availability(sp, settings)
    if not ok:
        return None
    t = (tag or getattr(cli, "tag", "aux")) + "-main"
    try:
        if prov == CODEX:
            return _build_codex(sp, cli, mode, t, codex_profile)
        if prov == GROK_CLI:
            return _build_grok(sp, cli, mode, t)
        if prov in API_PROVIDERS:
            return _build_api(sp, cli, mode, t)
    except Exception as e:
        print(f"[aux router] không dựng được mắt não-chính ({prov}): {e}", file=sys.stderr)
    return None


def _co_mat_orfree(chain) -> bool:
    """Chuỗi đã chứa một mắt OpenRouter model trống (= tự chọn free) chưa - có rồi thì
    mắt or_free cuối trùng hệt, khỏi thêm."""
    return any(getattr(e, "provider", "") == "openrouter"
               and not (getattr(e, "model", "") or "").strip() for e in chain)


def _openrouter_free_engine(cli, mode, tag, settings):
    """Mắt xích CUỐI của router: OpenRouter model free (model '' = tự chọn free mạnh nhất
    lúc chạy, xem _ApiAuxEngine.query). Chưa có key OpenRouter thì không có mắt này."""
    if not api_key_for("openrouter", settings):
        return None
    return _ApiAuxEngine(
        provider="openrouter",
        model="",
        system_prompt=getattr(cli, "system_prompt", None),
        vault_root=getattr(cli, "joyce_vault", None),
        mode=mode or getattr(cli, "joyce_mode", None) or "full",
        tag=(tag or getattr(cli, "tag", "aux")) + "-orfree",
    )


def strip_tools(engine, base):
    """Make a swapped engine (or fallback chain) TEXT-ONLY: no hub, no MCP of any kind (0.77.0).

    For turns whose prompt carries untrusted text (the group reply judge, its self-review): a stranger can write
    instructions into a group message, and the prompt fences them as data, but the only real wall is that the
    model has nothing to call. `base` is the sandboxed Claude engine the caller built before `swap` (allowed_tools
    set, empty MCP file, empty cwd), so it is safe as is. Every other link is stripped or DROPPED:

    - API engines: `no_tools` skips `discover_all`.
    - Codex: no `-p` profile (that is where the hub entry lives) and `mcp_servers={}` wipes any MCP the user's
      own config.toml declares.
    - Grok: its MCP file lives in the working directory (the empty sandbox folder), so the hub entry is removed.
    - Antigravity (`agy`) and anything unknown: dropped. `agy` reads MCP servers from the shared HOME file, which
      also serves the owner's own chats, so there is no way to take the hub away for one turn.

    Nothing left: fall back to `base` (a dead Claude login then fails the turn, which the judge treats as silence).
    """
    try:
        links = list(engine._all()) if isinstance(engine, _FallbackChain) else [engine]
    except Exception:       # noqa: BLE001
        return base
    keep = []
    for e in links:
        if e is base:
            keep.append(e)
            continue
        try:
            if isinstance(e, _ApiAuxEngine):
                e.no_tools = True
                keep.append(e)
                continue
            from claude_cli import CodexCLI
            if isinstance(e, CodexCLI):
                e.profile = None
                e.extra_config = [c for c in (e.extra_config or []) if not str(c).startswith("mcp_servers")]
                e.extra_config.append("mcp_servers={}")
                keep.append(e)
                continue
            import grok_cli
            if isinstance(e, grok_cli.GrokCLI):
                grok_cli.ghi_mcp_settings(e.cwd, None)
                keep.append(e)
                continue
        except Exception as ex:      # noqa: BLE001 - cannot prove it is tool-free: drop it
            print(f"[aux strip_tools] bỏ {type(e).__name__}: {type(ex).__name__}: {ex}", file=sys.stderr)
            continue
        print(f"[aux strip_tools] bỏ {type(e).__name__}: không tắt được công cụ cho riêng lượt này", file=sys.stderr)
    if not keep:
        return _chain_tagged(base, getattr(engine, "_task_tag", ""))
    return _chain_tagged(keep[0] if len(keep) == 1 else _FallbackChain(keep),
                         getattr(engine, "_task_tag", ""))


def _chain_tagged(engine, tag):
    """Bọc mọi kết quả swap() vào _FallbackChain + gắn `_task_tag` để query ghi mức dùng
    theo loại tác vụ (1.3.19). Chuỗi 1-mắt trong suốt y hệt engine trần: is_available/
    query/attr đều uỷ quyền mắt duy nhất, chỉ khác là query đếm được token cho sổ loại
    việc. `object.__setattr__` bắt buộc vì __setattr__ của chuỗi lan sang các mắt."""
    ch = engine if isinstance(engine, _FallbackChain) else _FallbackChain([engine])
    object.__setattr__(ch, "_task_tag", tag or "")
    return ch


def swap(cli, mode: str = None, tag: str = None, spec: dict = None,
         codex_profile=None, settings: dict = None):
    """Engine Claude đã dựng -> ROUTER việc nền theo model phụ người dùng chọn.

    Chuỗi fallback (mắt trước chết lúc chạy thì mắt sau tiếp quản, xem _FallbackChain):
      engine phụ user chọn → Claude → BỘ NÃO CHÍNH đang chat (nếu khác hai mắt trước)
      → OpenRouter model free mạnh nhất (nếu có key).
    Mắt não-chính là để máy KHÔNG đăng nhập Claude (chỉ chạy Gemini/OpenAI/Groq...) vẫn
    tự học và chạy việc nền được bằng đúng bộ não người dùng đang dùng, thay vì chết lặng
    với "Not logged in". Mặc định Claude + không dựng được mắt nào khác thì trả NGUYÊN
    engine Claude như xưa; hỏng cấu hình kiểu gì việc nền cũng phải chạy được chứ không chết.
    """
    try:
        sp = spec if spec is not None else read_spec(settings, tag=tag)
        prov = sp.get("provider", CLAUDE)
        # MỨC FULL CÓ CHUỖI NHƯNG BỊ THẮT CHẶT (safe_retry): chỉ nhảy sang mắt kế tiếp khi
        # mắt trước chết mà CHƯA gọi tool nào - tức provider sập/hết lượt NGAY TỪ ĐẦU, chưa
        # làm gì nên đổi engine không thể nhân đôi hành động. Mắt đã gọi tool rồi mới gãy
        # (đăng được 1/3 bài xong chết) thì chuỗi DỪNG và báo đúng lỗi gốc - đúng lý do
        # trước đây full không có chuỗi: engine khác không có tool NATIVE của Claude, model
        # không biết mình vừa bị đổi engine, và việc làm dở có thể bị làm lại từ đầu.
        safe_retry = str(mode or "").strip().lower() == "full"
        primary = None
        if prov == CLAUDE:
            cli.model = sp.get("model") or None
        else:
            ok, why = availability(sp, settings)
            if ok:
                primary = _engine_for_spec(sp, cli, mode, tag, codex_profile)
            else:
                # Provider đã chọn không dùng được NGAY TỪ ĐẦU (thiếu key/CLI): chưa hề có
                # hành động nào nên đổi engine an toàn kể cả full - đi đường chuỗi Claude.
                print(f"[aux] {why} → việc nền đi theo chuỗi.", file=sys.stderr)
        chain = [primary] if primary is not None else [cli]
        _fbs = _aux_fb_links(cli, mode, tag, settings, sp, codex_profile)
        chain += _fbs
        if primary is not None:
            chain.append(cli)
        _fb_provs = {getattr(e, "provider", "") for e in _fbs}
        mn = _main_fallback_engine(cli, mode, tag, settings,
                                   {CLAUDE, prov} | _fb_provs, codex_profile)
        if mn:
            chain.append(mn)
        or_free = _openrouter_free_engine(cli, mode, tag, settings)
        # Chuỗi đã có mắt openrouter model trống (tự chọn free) thì or_free trùng hệt → khỏi thêm.
        if or_free and not _co_mat_orfree(chain):
            chain.append(or_free)
        return _chain_tagged(_FallbackChain(chain, safe_retry=safe_retry), tag)
    except Exception as e:
        print(f"[aux swap] {e} → giữ engine Claude.", file=sys.stderr)
    return cli
