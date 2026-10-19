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
check("usable_keys: sạch trước, cháy cuối (không mất key)",
      tr.usable_keys("gemini", SK) == ["kBBB", "kCCC", "kAAA"])
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
check("cooldown per-day chờ tới nửa đêm UTC", tr.burn_cooldown("requests per day exceeded") > 3600)
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

print("\nOK - test_task_router: tất cả pass" if not _fails
      else f"\nFAIL {len(_fails)}: {_fails}")
sys.exit(1 if _fails else 0)
