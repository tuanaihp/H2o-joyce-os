"""Chuỗi dự phòng CHAT khi hết quota (1.3.18): `_stream_chain` đổi spec khi provider
trả lỗi quota trước khi phát nội dung, KHÔNG đổi khi đã ra chữ/tool/lỗi không-phải-quota;
`_chat_fallback_specs` đọc model.chat_fallbacks; `_fallback_chain` của Telegram ưu tiên
chuỗi chủ tự xếp trước thứ tự máy đoán.

    python tests/python/test_chat_fallback.py     (không mạng, không đụng settings thật)
"""
from _paths import ROOT, SERVER  # noqa: F401
import asyncio
import os
import sys
import tempfile

os.environ.setdefault("JOYCE_STATE_DIR", tempfile.mkdtemp(prefix="joyce-chatfb-"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import task_router as tr  # noqa: E402
import main  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


# ============================================================
# 1. _stream_chain: đổi spec khi quota, đúng thứ tự, không lặp
# ============================================================
calls = []


def _factory(log, script):
    """script: {(prov, model): [events]} - stream giả theo spec."""
    def make(p, k, m):
        async def gen():
            calls.append((p, k, m))
            for ev in script[(p, m)]:
                yield ev
        return gen()
    return make


def _drain(specs, make):
    async def go():
        return [ev async for ev in main._stream_chain(specs, make)]
    return asyncio.run(go())


QUOTA = {"type": "error", "content": "Error 429: too many requests, quota exceeded"}
OK = [{"type": "text", "content": "chào"}, {"type": "final", "content": "chào"}]

calls.clear()
evs = _drain([("gemini", "k1", "g2.5"), ("groq", "g1", "gpt-oss")],
             _factory(calls, {("gemini", "g2.5"): [QUOTA], ("groq", "gpt-oss"): OK}))
check("quota provider1 -> chuyển provider2 trả lời được",
      evs[-1]["type"] == "final" and [c[0] for c in calls] == ["gemini", "groq"])
check("key provider1 chết quota bị đánh dấu cháy", tr.burn_until("gemini", "k1") > 0)
tr.unburn()

# Đã phát text rồi mới lỗi -> KHÔNG chạy lại trên provider khác (nhân đôi nội dung)
calls.clear()
evs = _drain([("gemini", "k1", "g2.5"), ("groq", "g1", "gpt-oss")],
             _factory(calls, {("gemini", "g2.5"): [{"type": "text", "content": "nửa"},
                                                    QUOTA],
                              ("groq", "gpt-oss"): OK}))
check("đã ra chữ rồi lỗi -> không xoay (trả lỗi, không gọi provider2)",
      [c[0] for c in calls] == ["gemini"] and evs[-1]["type"] == "error")

# Lỗi KHÔNG phải quota -> không xoay
calls.clear()
evs = _drain([("gemini", "k1", "g2.5"), ("groq", "g1", "gpt-oss")],
             _factory(calls, {("gemini", "g2.5"): [{"type": "error",
                                                   "content": "500 internal"}],
                              ("groq", "gpt-oss"): OK}))
check("lỗi không-phải-quota -> không xoay provider",
      [c[0] for c in calls] == ["gemini"] and evs[-1]["type"] == "error")

# Mọi spec đều quota -> thử đúng mỗi spec một lần rồi trả lỗi (không lặp vô hạn)
calls.clear()
evs = _drain([("gemini", "k1", "g"), ("groq", "g1", "o"), ("deepseek", "d1", "v")],
             _factory(calls, {("gemini", "g"): [QUOTA], ("groq", "o"): [QUOTA],
                              ("deepseek", "v"): [QUOTA]}))
check("cả chuỗi đều quota: mỗi spec thử đúng một lần rồi dừng",
      [c[0] for c in calls] == ["gemini", "groq", "deepseek"] and evs[-1]["type"] == "error")
tr.unburn()

# tool_call đã phát -> xem như đã có tác động, KHÔNG replay trên provider khác
calls.clear()
evs = _drain([("gemini", "k1", "g"), ("groq", "g1", "o")],
             _factory(calls, {("gemini", "g"): [{"type": "tool_call", "name": "joyce_read_file"},
                                                QUOTA],
                              ("groq", "o"): OK}))
check("tool_call đã ra -> không replay (không nhân đôi hành động thật)",
      [c[0] for c in calls] == ["gemini"])

# ============================================================
# 2. _spec_keys: bung provider ra các key của vòng quay
# ============================================================
SK = {"gemini_api_key": "kA", "gemini_keys": ["kB", "kC"]}
check("_spec_keys bung đủ 3 key cùng provider",
      [k for _p, k, _m in main._spec_keys("gemini", "kA", "g", SK)] == ["kA", "kB", "kC"])
check("provider không có ring -> giữ key caller",
      main._spec_keys("ollama-local", "local", "qwen", {"ollama_local_endpoint": "http://x"}) ==
      [("ollama-local", "local", "qwen")])
check("key caller ngoài ring được thử trước ring",
      main._spec_keys("gemini", "kVIP", "g", SK)[0] == ("gemini", "kVIP", "g"))

# Key cháy xuống cuối hàng đợi của lượt
tr.unburn()
tr.burn_key("gemini", "kA", "429", 60)
check("key cháy xếp cuối trong lượt (vẫn được thử nốt)",
      [k for _p, k, _m in main._spec_keys("gemini", "kA", "g", SK)] == ["kB", "kC", "kA"])
tr.unburn()

# ============================================================
# 3. _chat_fallback_specs: đọc chat_fallbacks, lọc provider/API, bung key ring
# ============================================================
from config import read_settings, write_settings  # noqa: E402

_s = read_settings()
_s.setdefault("model", {})["chat_fallbacks"] = [
    {"provider": "gemini", "model": "g2.5"},
    {"provider": "grok-cli", "model": "grok-4"},          # CLI -> loại
    {"provider": "gemini", "model": "g2.5"},              # trùng -> loại
    {"provider": "ollama-local", "model": "qwen3:4b"},
    {"provider": "", "model": "x"},                        # rỗng -> loại
]
_s["model"]["gemini_api_key"] = "sk-gem-real-AAAA1111"
_s["model"]["gemini_keys"] = ["sk-gem-real-BBBB2222"]
_s["model"]["ollama_local_endpoint"] = "http://127.0.0.1:11434"
write_settings(_s)

specs = main._chat_fallback_specs(skip_prov="openrouter")
check("chuỗi user: gemini bung 2 key, CLI/trùng/rỗng bị loại, ollama-local vào được",
      specs == [("gemini", "sk-gem-real-AAAA1111", "g2.5"),
                ("gemini", "sk-gem-real-BBBB2222", "g2.5"),
                ("ollama-local", "local", "qwen3:4b")])
check("skip_prov loại provider khỏi chuỗi",
      main._chat_fallback_specs(skip_prov="gemini") ==
      [("ollama-local", "local", "qwen3:4b")])

# Provider API chưa có key -> không vào chuỗi (chỉ làm chậm)
_s["model"]["chat_fallbacks"] = [{"provider": "deepseek", "model": "d"}]
_s["model"].pop("deepseek_api_key", None)
write_settings(_s)
check("provider API chưa có key -> bị loại khỏi chuỗi",
      main._chat_fallback_specs() == [])

# ============================================================
# 4. _fallback_chain (Telegram): chuỗi chủ tự xếp đứng TRƯỚC thứ tự máy đoán
# ============================================================
_s["model"]["chat_fallbacks"] = [{"provider": "gemini", "model": "g2.5"}]
write_settings(_s)
chain = main._fallback_chain(_s["model"], "openrouter", "or-model")
check("Telegram chain: mắt chủ tự xếp đứng đầu",
      chain and chain[0] == ("gemini", "api", "sk-gem-real-AAAA1111", "g2.5"))
check("Telegram chain: provider hiện tại bị loại",
      all(p != "openrouter" for p, _k, _kk, _m in chain))

# Tắt hẳn thì chuỗi vẫn build được (cờ auto_fallback lọc ở caller, không ở đây)
_s["model"]["chat_fallbacks"] = []
write_settings(_s)
check("chat_fallbacks rỗng -> chain chỉ còn thứ tự máy đoán",
      all(e[0] != "gemini" or e[3] != "g2.5" for e in
          main._fallback_chain(_s["model"], "openrouter", "or")))

# ============================================================
# 5. POST /chat-fallbacks endpoint: chuẩn hoá + loại provider không hợp lệ
# ============================================================
class _Req:
    def __init__(self, body):
        self._b = body

    async def json(self):
        return self._b


r = asyncio.run(main.chat_fallbacks_set(_Req({"fallbacks": [
    {"provider": "gemini", "model": "g2.5"},
    {"provider": "groq"},
    {"provider": "gemini", "model": "g2.5"},   # trùng -> gộp
    {"provider": "bad-p", "model": "x"},        # provider lạ -> 400
]})))
check("endpoint 400 khi có provider không xoay được", getattr(r, "status_code", 200) == 400)

r = asyncio.run(main.chat_fallbacks_set(_Req({"fallbacks": [
    {"provider": "gemini", "model": "g2.5"}, {"provider": "groq"}]})))
_s = read_settings()
check("endpoint lưu chuỗi vào settings.model.chat_fallbacks",
      isinstance(r, dict) and r.get("ok")
      and _s["model"].get("chat_fallbacks") == [{"provider": "gemini", "model": "g2.5"},
                                               {"provider": "groq", "model": ""}])
_s["model"]["chat_fallbacks"] = []
write_settings(_s)

# GET /task-engines: chat_main + chat_fallbacks + api_providers có mặt
te = asyncio.run(main.task_engines_get())
check("GET /task-engines trả chat_main + chat_fallbacks + api_providers",
      "chat_main" in te and "chat_fallbacks" in te and "api_providers" in te)
check("api_providers đúng 9 nhà API",
      set(te["api_providers"]) == set(main.aux_engine.API_PROVIDERS))
check("không lộ API key trong response /task-engines",
      "sk-gem-real" not in __import__("json").dumps(te))

tr.unburn()
print("\nOK - test_chat_fallback: tất cả pass" if not _fails
      else f"\nFAIL {len(_fails)}: {_fails}")
sys.exit(1 if _fails else 0)
