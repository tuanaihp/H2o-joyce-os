"""Test router việc nền (_FallbackChain): engine phụ chết lúc CHẠY → Claude → OpenRouter
free mạnh nhất (ca thật: Codex hết quota ChatGPT làm nhắc hẹn chết, chỉ báo ⚠ về Telegram).
Chạy:  python tests/run.py aux_fallback    (KHÔNG mạng)."""
from _paths import ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path (xem tests/python/_paths.py)
import os, sys, tempfile, asyncio
os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-auxfb-test-")

_fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)

import aux_engine  # noqa: E402


class FakeEngine:
    """Engine giả theo hợp đồng ClaudeSDK: query() sinh dict sự kiện."""
    def __init__(self, events=None, available=True, raise_exc=None, provider=None):
        self.events = events or []
        self.available = available
        self.raise_exc = raise_exc
        self.ran = 0
        self.session_id = None
        if provider:
            self.provider = provider

    def is_available(self):
        return self.available

    def reset_session(self):
        self.session_id = None

    async def query(self, prompt):
        self.ran += 1
        if self.raise_exc:
            raise self.raise_exc
        for ev in self.events:
            yield ev


async def collect(engine, prompt="lam viec"):
    return [ev async for ev in engine.query(prompt)]


FB = aux_engine._FallbackChain
run = asyncio.run
FINAL = lambda s: {"type": "final", "content": s}
ERR = lambda s: {"type": "error", "content": s}

# --- mắt 1 chạy ngon → không đụng các mắt sau ---
codex = FakeEngine([{"type": "tool_call", "name": "x"}, FINAL("xong")])
claude = FakeEngine([FINAL("claude day")])
evs = run(collect(FB([codex, claude])))
check("mắt 1 ok: trả đúng sự kiện của nó", evs[-1] == FINAL("xong"))
check("mắt 1 ok: KHÔNG chạy mắt sau", claude.ran == 0)

# --- mắt 1 hết quota (ca Codex) → mắt 2 cứu ---
codex = FakeEngine([ERR("Codex: You've hit your usage limit.")])
claude = FakeEngine([FINAL("claude cứu")])
evs = run(collect(FB([codex, claude])))
check("hết quota: final đến từ Claude", evs[-1]["content"] == "claude cứu")
check("hết quota: error của mắt chết KHÔNG lọt ra ngoài", all(e.get("type") != "error" for e in evs))
check("hết quota: Claude chạy đúng 1 lần", claude.ran == 1)

# --- CHUỖI 3 MẮT: phụ chết + Claude cũng chết → OpenRouter free cứu ---
codex = FakeEngine([ERR("quota het")])
claude = FakeEngine(raise_exc=RuntimeError("claude cung het han muc"))
orfree = FakeEngine([FINAL("free model cuu ca lang")], provider="openrouter")
evs = run(collect(FB([codex, claude, orfree])))
check("chuỗi 3 mắt: hai mắt đầu chết, OpenRouter free cứu", evs[-1]["content"] == "free model cuu ca lang")
check("chuỗi 3 mắt: cả 3 đều được thử", codex.ran == 1 and claude.ran == 1 and orfree.ran == 1)

# --- mắt câm (không final) / unavailable đều coi là chết ---
evs = run(collect(FB([FakeEngine([{"type": "tool_call", "name": "y"}]), FakeEngine([FINAL("co final")])])))
check("mắt câm: mắt sau cứu", evs[-1]["content"] == "co final")
silent = FakeEngine(available=False)
evs = run(collect(FB([silent, FakeEngine([FINAL("truc tiep")])])))
check("mắt unavailable: nhảy thẳng mắt sau, không chạy mắt chết", evs[-1]["content"] == "truc tiep" and silent.ran == 0)

# --- cả chuỗi chết → trả error thật (không nuốt) ---
evs = run(collect(FB([FakeEngine([ERR("quota")]), FakeEngine(available=False)])))
check("cả chuỗi chết: lộ error để nơi gọi báo user", evs[-1]["type"] == "error")

# --- final "Not logged in" (Claude CLI chưa đăng nhập) = mắt CHẾT, không phải kết quả ---
# Ca thật 26/08: máy chỉ đăng nhập Gemini, việc nền mặc định Claude → learn vòng nào cũng
# nhận final "Not logged in · Please run /login" và tưởng đó là manifest.
dead = FakeEngine([FINAL("Not logged in · Please run /login")])
backup = FakeEngine([FINAL("nao chinh cuu")])
evs = run(collect(FB([dead, backup])))
check("final mất đăng nhập: mắt sau cứu", evs[-1]["content"] == "nao chinh cuu")
check("final mất đăng nhập: KHÔNG lọt ra ngoài",
      all("Not logged in" not in (e.get("content") or "") for e in evs))
long_final = "x" * 500 + " please run /login"
evs = run(collect(FB([FakeEngine([FINAL(long_final)]), FakeEngine([FINAL("khong duoc dung toi")])])))
check("final DÀI nhắc chữ login vẫn là nội dung thật", evs[-1]["content"] == long_final)
evs = run(collect(FB([FakeEngine([FINAL("Invalid API key · Please run /login")])])))
check("cả chuỗi mất đăng nhập → lộ error", evs[-1]["type"] == "error")

# --- hợp đồng attr: gán → MỌI mắt, đọc → mắt đầu; is_available OR cả chuỗi ---
a, b, c = FakeEngine(), FakeEngine(), FakeEngine()
w = FB([a, b, c])
w.max_wall_s = 300
check("gán attr đặt cho MỌI mắt", a.max_wall_s == b.max_wall_s == c.max_wall_s == 300)
a.tag = "reminder"
check("đọc attr lấy từ mắt đầu", w.tag == "reminder")
a.available = b.available = False
check("is_available = OR cả chuỗi", w.is_available() is True)
c.available = False
check("cả chuỗi tắt → is_available False", w.is_available() is False)

# --- chấm điểm model free OpenRouter: họ mạnh thắng, cùng họ thì to thắng ---
score = aux_engine._score_free_model
check("deepseek-r1 > llama cùng cỡ",
      score("deepseek/deepseek-r1:free") > score("meta-llama/llama-3.1-8b:free"))
check("cùng họ: 70b > 8b",
      score("meta-llama/llama-3.3-70b:free") > score("meta-llama/llama-3.1-8b:free"))
check("id lạ không nổ, điểm thấp nhất", score("ai21/jamba-x:free") <= score("qwen/qwen3-32b:free"))

# --- pick_openrouter_free: dùng cache khi còn hạn (không gọi mạng trong test) ---
aux_engine._OR_FREE_CACHE.update(ts=aux_engine.time.time(), model="test/model-cache:free")
check("pick dùng cache còn hạn", run(aux_engine.pick_openrouter_free("k")) == "test/model-cache:free")

# --- swap() ghép chuỗi đúng theo cấu hình ---
S_KEY = {"model": {"openrouter_key": "sk-or-test", "auxiliary": {}}}
S_NOKEY = {"model": {"auxiliary": {}}}
out = aux_engine.swap(FakeEngine(), spec={"provider": "openrouter", "model": "x/y"}, settings=S_KEY)
check("swap provider API → chuỗi fallback", type(out).__name__ == "_FallbackChain")
base = FakeEngine()
check("swap Claude KHÔNG key OpenRouter → trả nguyên engine, không bọc",
      aux_engine.swap(base, spec={"provider": "anthropic-cli", "model": ""}, settings=S_NOKEY) is base)
out = aux_engine.swap(FakeEngine(), spec={"provider": "anthropic-cli", "model": ""}, settings=S_KEY)
check("swap Claude CÓ key OpenRouter → bọc chuỗi [Claude, OR-free]",
      type(out).__name__ == "_FallbackChain" and len(out._all()) == 2
      and getattr(out._all()[1], "provider", "") == "openrouter")
out = aux_engine.swap(FakeEngine(), spec={"provider": "openrouter", "model": ""}, settings=S_KEY)
check("phụ = openrouter model trống → không nhân đôi mắt or-free",
      type(out).__name__ == "_FallbackChain" and len(out._all()) == 2)

# --- bộ não CHÍNH làm mắt dự phòng khi việc nền mặc định Claude (máy chỉ đăng nhập Gemini) ---
S_MAIN_GEMINI = {"model": {"gemini_api_key": "g-key", "auxiliary": {},
                           "main": {"provider": "gemini", "model": "gemini-2.5-flash-lite"}}}
out = aux_engine.swap(FakeEngine(), spec={"provider": "anthropic-cli", "model": ""},
                      settings=S_MAIN_GEMINI)
check("aux mặc định Claude + main Gemini → chuỗi [Claude, não chính Gemini]",
      type(out).__name__ == "_FallbackChain" and len(out._all()) == 2
      and getattr(out._all()[1], "provider", "") == "gemini"
      and getattr(out._all()[1], "model", "") == "gemini-2.5-flash-lite")
check("main_spec đọc đúng bộ não chính", aux_engine.main_spec(S_MAIN_GEMINI)
      == {"provider": "gemini", "model": "gemini-2.5-flash-lite"})
# main = Claude (mặc định) → không thêm mắt nào, hành vi cũ giữ nguyên (đã test ở trên).
# main TRÙNG provider phụ → không nhân đôi mắt.
S_BOTH_GEMINI = {"model": {"gemini_api_key": "g-key",
                           "auxiliary": {"provider": "gemini", "model": "m1"},
                           "main": {"provider": "gemini", "model": "m2"}}}
out = aux_engine.swap(FakeEngine(), settings=S_BOTH_GEMINI)
check("main trùng provider phụ → chuỗi chỉ [Gemini, Claude], không nhân đôi",
      type(out).__name__ == "_FallbackChain" and len(out._all()) == 2)
# main = provider không có builder nền (antigravity-cli) → bỏ qua êm, không nổ.
S_MAIN_AGY = {"model": {"auxiliary": {}, "main": {"provider": "antigravity-cli", "model": "x"}}}
base_agy = FakeEngine()
check("main không có builder nền → giữ nguyên engine Claude",
      aux_engine.swap(base_agy, spec={"provider": "anthropic-cli", "model": ""},
                      settings=S_MAIN_AGY) is base_agy)

# --- safe_retry (mức full): chỉ nhảy mắt khi mắt trước chết SẠCH (0 tool_call) ---
# Việc full thao tác ra ngoài: engine đã gọi tool rồi mới gãy = có thể đã làm một phần,
# chạy lại bằng engine khác rủi ro nhân đôi (đăng bài/gửi tin hai lần). Chết ngay từ đầu
# (hết lượt gói, provider sập trước khi làm gì) thì đổi engine an toàn.
claude_cap = FakeEngine([ERR("Hết lượt gói Claude Code - resets Oct 26, 10am")], provider="anthropic-cli")
gemini_ok = FakeEngine([FINAL("gemini chay tiep")], provider="gemini")
evs = run(collect(FB([claude_cap, gemini_ok], safe_retry=True)))
check("full + chết sạch (cap ngay): mắt sau cứu", evs[-1]["content"] == "gemini chay tiep")
check("full + chết sạch: gemini được gọi", gemini_ok.ran == 1)

# Mắt đầu gọi tool rồi mới gãy -> KHÔNG được nhảy mắt (việc có thể đã làm một phần)
claude_mid = FakeEngine([{"type": "tool_call", "name": "joyce_write"},
                         ERR("claude sap giua chung")], provider="anthropic-cli")
gemini2 = FakeEngine([FINAL("khong duoc chay toi")], provider="gemini")
evs = run(collect(FB([claude_mid, gemini2], safe_retry=True)))
check("full + gãy sau tool_call: DỪNG chuỗi, lỗi gốc lộ ra",
      evs[-1]["type"] == "error" and "sap giua chung" in evs[-1]["content"])
check("full + gãy sau tool_call: mắt sau KHÔNG chạy", gemini2.ran == 0)

# Chỉ phát chữ (suy nghĩ) rồi chết = chưa làm gì ngoài -> vẫn được đổi engine
claude_text = FakeEngine([{"type": "text", "content": "dang suy nghi..."},
                          ERR("het luot")], provider="anthropic-cli")
gemini3 = FakeEngine([FINAL("cuu duoc")], provider="gemini")
evs = run(collect(FB([claude_text, gemini3], safe_retry=True)))
check("full + chỉ text rồi chết: mắt sau vẫn cứu (text không gây hành động)",
      evs[-1]["content"] == "cuu duoc")

# Không bật safe_retry (auto/suggest): gãy sau tool_call vẫn được thử mắt sau như cũ
claude_mid2 = FakeEngine([{"type": "tool_call", "name": "joyce_read"},
                          ERR("sap")], provider="anthropic-cli")
gemini4 = FakeEngine([FINAL("auto van cuu")], provider="gemini")
evs = run(collect(FB([claude_mid2, gemini4])))
check("auto + gãy sau tool_call: vẫn thử mắt sau (không rào)", evs[-1]["content"] == "auto van cuu")

# swap(mode="full") dựng chuỗi safe_retry, không còn trả 1 engine trần
out = aux_engine.swap(FakeEngine(), spec={"provider": "anthropic-cli", "model": ""},
                      settings=S_KEY, mode="full")
check("full + Claude: được CHUỖI safe_retry thay vì engine trần",
      type(out).__name__ == "_FallbackChain" and len(out._all()) == 2
      and object.__getattribute__(out, "_safe_retry") is True)
out_auto = aux_engine.swap(FakeEngine(), spec={"provider": "anthropic-cli", "model": ""},
                           settings=S_KEY, mode="auto")
check("auto + Claude: chuỗi thường, không rào safe_retry",
      object.__getattribute__(out_auto, "_safe_retry") is False)

# --- FINAL GIẢ "hết lượt gói" (resets Oct 26): cũng là mắt CHẾT, chuỗi phải nhảy tiếp ---
# Ca thật 24/10: Claude Code in câu cap tiếng Anh vào chỗ câu trả lời (không phải error),
# chuỗi tưởng mắt đầu thành công -> bước workflow nhận "kết quả" là câu báo hết lượt.
cap_final = FakeEngine([FINAL("You've hit your usage limit. resets Oct 26, 10am")],
                       provider="anthropic-cli")
gemini5 = FakeEngine([FINAL("gemini nhay vao")], provider="gemini")
evs = run(collect(FB([cap_final, gemini5])))
check("final hết lượt: coi mắt đầu CHẾT, mắt sau cứu", evs[-1]["content"] == "gemini nhay vao")
check("final hết lượt: câu cap KHÔNG lọt ra ngoài như kết quả",
      all("usage limit" not in (e.get("content") or "") for e in evs if e.get("type") == "final"))
cap_final2 = FakeEngine([FINAL("Claude AI usage limit reached|1893000000")],
                        provider="anthropic-cli")
evs = run(collect(FB([cap_final2, FakeEngine([FINAL("or free chay")])])))
check("dạng máy 'reached|<epoch>': cũng coi là chết", evs[-1]["content"] == "or free chay")
# Bài thật TRÍCH câu hết lượt giữa văn bản -> không nghi oan, giữ nguyên kết quả
bai_that = "Hướng dẫn xử lý:\nKhi gặp thông báo session limit reached thì nên chờ.\n" + "Nội dung. " * 60
evs = run(collect(FB([FakeEngine([FINAL(bai_that)], provider="anthropic-cli"),
                      FakeEngine([FINAL("khong duoc toi")])])))
check("bài thật trích câu limit: giữ nguyên kết quả thật", evs[-1]["content"] == bai_that)

# --- final_loi_dang_nhap: nhận đúng mẫu, không nghi oan ---
check("bắt câu Not logged in", aux_engine.final_loi_dang_nhap("Not logged in · Please run /login"))
check("bắt câu OAuth hết hạn", aux_engine.final_loi_dang_nhap(
    "Failed to authenticate: OAuth session expired and could not be refreshed"))
check("final rỗng không phải lỗi auth", not aux_engine.final_loi_dang_nhap(""))
check("nội dung dài không bị nghi oan",
      not aux_engine.final_loi_dang_nhap("bao cao " * 100 + "please run /login"))

print()
if _fails:
    print(f"FAIL {len(_fails)} test: " + ", ".join(_fails)); sys.exit(1)
print("TẤT CẢ PASS")
