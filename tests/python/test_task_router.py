"""Phân việc não + vòng quay API key (1.3.17): gán model theo loại tác vụ, xoay key khi
hết quota, nhận diện lỗi quota, attribution theo key slot.

    python tests/python/test_task_router.py     (không mạng, không đụng settings thật)

JOYCE_STATE_DIR được trỏ vào thư mục tạm TRƯỚC khi import server - task_router giữ
key_burns.json ở đó và cfgmod.write_settings cũng ghi vào đó, nên test này không bao giờ
đụng settings.json thật của máy.
"""
from _paths import ROOT, SERVER  # noqa: F401
import asyncio
import json
import os
import sys
import tempfile
import types

os.environ.setdefault("JOYCE_STATE_DIR", tempfile.mkdtemp(prefix="joyce-taskrouter-"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import task_router as tr  # noqa: E402
import aux_engine  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


# ============================================================
# 1. Danh mục loại tác vụ: tag call-site -> id registry
# ============================================================
check("dispatch:* -> kanban", tr.task_key_for_tag("dispatch:abc123:run") == "kanban")
check("reminder -> reminder", tr.task_key_for_tag("reminder") == "reminder")
check("tag mắt dự phòng -main gỡ hậu tố", tr.task_key_for_tag("loop-main") == "loop")
check("tag -orfree gỡ hậu tố", tr.task_key_for_tag("learn-orfree") == "learn")
check("tag lạ -> khac", tr.task_key_for_tag("gi-do") == "khac")
check("tag rỗng -> khac", tr.task_key_for_tag("") == "khac")
check("mọi tag thật của call-site đều có trong registry",
      all(tr.task_key_for_tag(t) != "khac" for t in
          ("reminder", "loop", "ingest", "learn", "curator", "today-brief",
           "reply-policy", "agent-judge", "dispatch:x:y")))

# ============================================================
# 2. spec_for_tag: gán riêng -> khac -> auxiliary -> Claude
# ============================================================
S = {"model": {"auxiliary": {"provider": "groq", "model": "llama-x"},
               "task_models": {"reminder": {"provider": "gemini", "model": "g-2.5"}}}}
check("loại gán riêng dùng spec riêng",
      tr.spec_for_tag("reminder", S) == {"provider": "gemini", "model": "g-2.5"})
check("loại chưa gán rơi về auxiliary",
      tr.spec_for_tag("loop", S) == {"provider": "groq", "model": "llama-x"})
S2 = {"model": {"auxiliary": {"provider": "groq", "model": "m"},
                "task_models": {"khac": {"provider": "deepseek", "model": "d"}}}}
check("'khac' override đè auxiliary cho loại chưa gán",
      tr.spec_for_tag("loop", S2) == {"provider": "deepseek", "model": "d"})
check("reminder vẫn ưu tiên gán riêng trước 'khac'",
      tr.spec_for_tag("reminder", {**S2, "model": {**S2["model"],
                     "task_models": {**S2["model"]["task_models"],
                                     "reminder": {"provider": "openai"}}}})["provider"] == "openai")
check("không cấu hình gì -> Claude mặc định",
      tr.spec_for_tag("loop", {"model": {}})["provider"] == "anthropic-cli")

# ============================================================
# 3. set_task_spec + task_list + clear (ghi settings.json tạm)
# ============================================================
check("set_task_spec id lạ -> False", tr.set_task_spec("khong-co", "gemini") is False)
check("set_task_spec hợp lệ", tr.set_task_spec("ingest", "deepseek", "ds-3") is True)
lst = {t["id"]: t for t in tr.task_list()}
check("task_list thấy spec vừa gán", lst["ingest"]["spec"] == {"provider": "deepseek", "model": "ds-3"})
check("task_list đánh cờ custom", lst["ingest"]["custom"] is True and lst["loop"]["custom"] is False)
check("mọi loại tác vụ đều có mô tả + gợi ý",
      all(t.get("vi_mo_ta") and t.get("goi_y") for t in tr.task_list()))
tr.set_task_spec("ingest", "", "")
check("provider rỗng = gỡ gán riêng", lst["ingest"]["id"] == "ingest"
      and {t["id"]: t for t in tr.task_list()}["ingest"]["custom"] is False)
tr.set_task_spec("ingest", "deepseek", "ds-3")
tr.clear_task_specs()
check("clear_task_specs xoá sạch",
      all(not t["custom"] for t in tr.task_list()))

# ============================================================
# 4. Vòng key: keys_for / pick_key / burn / usable / set_keys
# ============================================================
SK = {"model": {"gemini_api_key": "kAAA", "gemini_keys": ["kBBB", "kAAA", "kCCC"]}}
check("ring = key chính + key phụ, khử trùng",
      tr.keys_for("gemini", SK) == ["kAAA", "kBBB", "kCCC"])
check("provider không map field -> ring rỗng", tr.keys_for("grok-cli", SK) == [])
SK_STR = {"model": {"groq_api_key": "", "groq_keys": "g1\ng2, g1\n"}}
check("key phụ dạng chuỗi (dán mỗi dòng) cũng tách được", tr.keys_for("groq", SK_STR) == ["g1", "g2"])

tr.unburn()
check("pick_key trả key đầu chưa cháy", tr.pick_key("gemini", SK) == "kAAA")
tr.burn_key("gemini", "kAAA", "429", 60)
check("key cháy thì pick_key nhảy key kế", tr.pick_key("gemini", SK) == "kBBB")
check("usable_keys: bỏ key đang cháy tới khi cooldown hết",
      tr.usable_keys("gemini", SK) == ["kBBB", "kCCC"])
check("burn_until dương cho key vừa cháy", tr.burn_until("gemini", "kAAA") > 0)
n = tr.unburn("gemini")
check("unburn(provider) mở đúng 1 slot", n == 1 and tr.pick_key("gemini", SK) == "kAAA")

# set_keys: ghi field + _keys, dọn fingerprint cháy của key đã rời vòng
tr.set_keys("groq", ["k1", "k2", "k1", "", "k3"])
from config import read_settings  # noqa: E402
_m = read_settings().get("model", {})
check("set_keys: key[0] vào trường chính, phần còn vào <provider>_keys, khử trùng",
      _m.get("groq_api_key") == "k1" and _m.get("groq_keys") == ["k2", "k3"])
tr.burn_key("groq", "k9-cu-bo-di", "429", 60)
tr.set_keys("groq", ["k1", "k2", "k3"])
check("đổi vòng thì fingerprint cháy của key đã rời vòng bị dọn",
      tr.burn_until("groq", "k9-cu-bo-di") == 0)

# ring_status: đuôi key, đếm cháy, không lộ key thô (key thật dài 20+ ký tự)
SK_REAL = {"model": {"gemini_api_key": "sk-gem-AAAABBBB11112222",
                     "gemini_keys": ["sk-gem-CCCCDDDD33334444", "sk-gem-EEEEFFFF55556666"]}}
tr.burn_key("gemini", "sk-gem-AAAABBBB11112222", "quota exceeded", 60)
st = {r["provider"]: r for r in tr.all_ring_status(SK_REAL)}["gemini"]
check("ring_status đếm đúng", st["total"] == 3 and st["burned"] == 1)
check("slot chỉ lộ đuôi, không lộ key đầy",
      all(s["tail"].startswith("…") for s in st["keys"])
      and "sk-gem-AAAABBBB11112222" not in json.dumps(st))
tr.note_use("gemini", "sk-gem-CCCCDDDD33334444", 10, 20)
st2 = {r["provider"]: r for r in tr.all_ring_status(SK_REAL)}["gemini"]
slot_cc = [s for s in st2["keys"] if s["tail"].endswith("4444")][0]
check("note_use quy lượt về đúng key slot (attribution không lộ key)",
      slot_cc["uses"] >= 1 and slot_cc["tin"] >= 10 and slot_cc["tout"] >= 20)
tr.unburn()

# ============================================================
# 5. Nhận diện lỗi quota + thời gian chờ
# ============================================================
for msg in ("Error 429: Too Many Requests", "quota exceeded", "rate limit hit",
            "insufficient_quota", "tokens per day exceeded", "invalid api key",
            "You've hit your usage limit", "hết hạn mức", "401 Unauthorized"):
    check(f"quota_error nhận: {msg!r}", tr.quota_error(msg))
for msg in ("network timeout", "connection reset by peer", "model not found",
            "context length exceeded", ""):
    check(f"quota_error KHÔNG nhận oan: {msg!r}", not tr.quota_error(msg))
check("cooldown 'try again in 30s' ~ 40s", tr.burn_cooldown("try again in 30s") == 40.0)
_daily_cd = tr.burn_cooldown("requests per day exceeded")
check("cooldown per-day chờ tới nửa đêm Pacific + đệm",
      60 <= _daily_cd <= 25 * 3600)
check("cooldown per-minute ~ 75s", tr.burn_cooldown("tokens per minute exceeded") == 75.0)
check("cooldown không rõ -> 5 phút", tr.burn_cooldown("429") == 300.0)

# ============================================================
# 6. aux_engine tích hợp: read_spec(tag) + api_key_for ring-aware
# ============================================================
SA = {"model": {"auxiliary": {"provider": "groq", "model": "m"},
                "task_models": {"agent-judge": {"provider": "deepseek", "model": "d"}}}}
check("read_spec(tag) đi theo spec loại tác vụ",
      aux_engine.read_spec(SA, tag="agent-judge") == {"provider": "deepseek", "model": "d"})
check("read_spec(tag) loại chưa gán về auxiliary",
      aux_engine.read_spec(SA, tag="loop") == {"provider": "groq", "model": "m"})
check("read_spec() không tag giữ hành vi cũ",
      aux_engine.read_spec(SA) == {"provider": "groq", "model": "m"})

# api_key_for: primary cháy -> key kế (đường chat/vision cũng được phủ nhờ chỗ trung tâm này)
tr.unburn()
tr.burn_key("gemini", "kAAA", "429", 60)
check("api_key_for nhảy key khi primary cháy", aux_engine.api_key_for("gemini", SK) == "kBBB")
tr.burn_key("gemini", "kBBB", "429", 60)
tr.burn_key("gemini", "kCCC", "429", 60)
check("hết key sạch -> api_key_for '' (engine coi như không sẵn sàng, fallback đi tiếp)",
      aux_engine.api_key_for("gemini", SK) == "")
tr.unburn()

# ============================================================
# 7. _ApiAuxEngine.query: xoay key TRONG CÙNG lượt khi key đầu chết quota
# ============================================================
_calls = []


async def _fake_stream(key, model, messages, *rest):
    _calls.append(key)
    if key == "kAAA":
        yield {"type": "error", "content": "Error 429: quota exceeded, try again later"}
        return
    yield {"type": "usage", "input": 5, "output": 7}
    yield {"type": "text", "content": "xin chào"}


class _FakeEng:
    def __getattr__(self, name):
        return _fake_stream


async def _discover(*a, **k):
    return [], {}


_fake_hub = types.SimpleNamespace(discover_all=_discover)
sys.modules.setdefault("engine", _FakeEng())
sys.modules.setdefault("mcp_hub", _fake_hub)

tr.unburn()
tr.set_keys("gemini", ["kAAA", "kBBB"])
e = aux_engine._ApiAuxEngine(provider="gemini", model="g2.5", system_prompt="",
                             vault_root=None, mode="suggest", tag="t")


async def _run(eng):
    out = []
    async for ev in eng.query("hi"):
        out.append(ev)
    return out


evs = asyncio.run(_run(e))
check("key1 chết quota -> tự thử key2 trong cùng lượt", _calls == ["kAAA", "kBBB"])
check("lượt thành công trả final của key2",
      evs and evs[-1]["type"] == "final" and "xin chào" in evs[-1].get("content", ""))
check("key chết quota bị đánh dấu cháy", tr.burn_until("gemini", "kAAA") > 0)
tr.unburn()

# Lỗi KHÔNG phải quota: không xoay (xoay không cứu được), trả lỗi luôn
_calls.clear()


async def _fake_stream_500(key, model, messages, *rest):
    _calls.append(key)
    yield {"type": "error", "content": "500 internal server error"}


class _FakeEng500:
    def __getattr__(self, name):
        return _fake_stream_500


sys.modules["engine"] = _FakeEng500()
evs = asyncio.run(_run(e))
check("lỗi không-phải-quota thì KHÔNG xoay key (trả lỗi ngay, không đốt quota vô ích)",
      _calls == ["kAAA"])
check("lỗi không-phải-quota trả event error", evs and evs[-1]["type"] == "error")

# Mọi key đều quota: thử hết rồi mới báo lỗi (không vòng lặp vô hạn)
_calls.clear()


async def _fake_stream_q(key, model, messages, *rest):
    _calls.append(key)
    yield {"type": "error", "content": "429 too many requests"}


class _FakeEngQ:
    def __getattr__(self, name):
        return _fake_stream_q


sys.modules["engine"] = _FakeEngQ()
tr.unburn()
evs = asyncio.run(_run(e))
check("hết key đều quota: thử đúng mỗi key một lần rồi dừng (không lặp vô hạn)",
      sorted(_calls) == ["kAAA", "kBBB"] and evs[-1]["type"] == "error")

sys.modules.pop("engine", None)
sys.modules.pop("mcp_hub", None)

# ============================================================
# 3. Sổ mức dùng theo loại tác vụ + quy $ + đề xuất (1.3.19)
# ============================================================
tr._TASK_USE_PATH.unlink(missing_ok=True)

# Không ghi lượt 0-token-0-cost (sự kiện usage rỗng không được bẩn sổ)
tr.task_use_note("reminder", "gemini", "gemini-2.5-flash", 0, 0, 0)
check("lượt trống (0 token, 0 cost) không ghi sổ",
      not tr._TASK_USE_PATH.exists() or not tr._load_task_use())

tr.task_use_note("reminder", "gemini", "gemini-2.5-flash", 1000, 200)
tr.task_use_note("reminder", "gemini", "gemini-2.5-flash", 500, 100)
tr.task_use_note("dispatch:abc:run", "groq", "openai/gpt-oss-20b", 800, 400)
tr.task_use_note("dispatch:x:y", "ollama-local", "qwen3-vl:8b", 2000, 500)
tr.task_use_note("tag-la-khong-ro", "deepseek", "deepseek-r1", 100, 50)

s30 = tr.task_use_summary(30)
check("reminder gộp 2 lượt cùng model",
      s30["reminder"]["turns"] == 2 and s30["reminder"]["in"] == 1500
      and s30["reminder"]["out"] == 300)
check("dispatch:* quy về kanban + gộp 2 provider",
      s30["kanban"]["turns"] == 2 and s30["kanban"]["in"] == 2800
      and set(s30["kanban"]["models"]) ==
      {"groq|openai/gpt-oss-20b", "ollama-local|qwen3-vl:8b"})
check("tag lạ quy sổ vào khac", s30["khac"]["turns"] == 1)

# Quy $: model có giá trong usage_pricing.json thì cost_est > 0 (gemini-2.5-flash có giá);
# model ':free' hoặc nhà free thì vẫn 0 dù có token.
check("gemini-2.5-flash quy được tiền ước tính > 0",
      s30["reminder"]["cost_est"] > 0)
tr.task_use_note("learn", "openrouter", "x/y:free", 999999, 999999)
s30b = tr.task_use_summary(30)
check("model ':free' token lớn vẫn ước $0",
      any(mm["cost_est"] == 0 for mk, mm in s30b["learn"]["models"].items()
          if mk.endswith(":free")))

# cost thật (provider trả về, vd Claude Code CLI) được giữ riêng, không bị ước tính đè
tr.task_use_note("loop", "ClaudeCLI", "sonnet", 100, 50, cost=0.05)
s30c = tr.task_use_summary(30)
check("cost thật của provider cộng vào cost (không pha ước tính)",
      s30c["loop"]["cost"] == 0.05 and
      s30c["loop"]["models"]["ClaudeCLI|sonnet"]["cost_est"] == 0.05)

# task_list: mọi hàng đều có use + dx; dx không lộ key
tl = tr.task_list()
rmd = next(t for t in tl if t["id"] == "reminder")
check("task_list hàng reminder mang use 2 lượt", rmd["use"]["turns"] == 2)
check("task_list mọi hàng đều có dx.state", all(t["dx"]["state"]
      in ("ok", "switch", "save", "none") for t in tl))
check("dx + use không chứa chuỗi key nào",
      all("kAAA" not in json.dumps(t) and "kBBB" not in json.dumps(t) for t in tl))

# ============================================================
# 4. Vòng key khung dọc: add/remove từng key + xoá key chính khi vòng rỗng (1.3.19)
# ============================================================
import config as _cfg  # noqa: E402

_s = _cfg.read_settings()
_s.setdefault("model", {})["gemini_api_key"] = "kEXIST-1234567890"
_s["model"]["gemini_keys"] = []
_cfg.write_settings(_s)

check("add_key thêm vào cuối vòng",
      tr.add_key("gemini", "kNEW-abcdefgh") == 2 and
      tr.keys_for("gemini")[-1] == "kNEW-abcdefgh")
check("add_key key trùng bị từ chối (-2)",
      tr.add_key("gemini", "kNEW-abcdefgh") == -2)
check("add_key key rỗng bị từ chối (-1)", tr.add_key("gemini", "  ") == -1)
check("remove_key index giữa vòng",
      tr.remove_key("gemini", 1) == 1 and tr.keys_for("gemini") == ["kEXIST-1234567890"])
check("remove_key index xấu -> -1",
      tr.remove_key("gemini", 9) == -1 and tr.remove_key("gemini", -1) == -1)
# Xoá key CUỐI CÙNG: key chính cũng phải đi - trước đây m[field] chỉ ghi khi vòng không
# rỗng nên để lại một key ma vẫn chạy được.
check("gỡ key cuối: vòng rỗng và key chính bị xoá luôn",
      tr.remove_key("gemini", 0) == 0 and tr.keys_for("gemini") == [] and
      not (_cfg.read_settings().get("model") or {}).get("gemini_api_key"))

# Chuỗi dự phòng việc nền: provider được phép gồm cả engine CLI (Codex=gmail, Grok, Agy)
# vì xoay theo engine; anthropic-cli không vì nó đã là mắt mặc định.
check("aux_fb_providers gồm codex+grok+agy+api",
      set(("openai-oauth", "grok-cli", "antigravity-cli")) <= set(aux_engine.AUX_FB_PROVIDERS)
      and "anthropic-cli" not in aux_engine.AUX_FB_PROVIDERS)

print("\nOK - test_task_router: tất cả pass" if not _fails
      else f"\nFAIL {len(_fails)}: {_fails}")
sys.exit(1 if _fails else 0)
