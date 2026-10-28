"""Test prompt caching engine API (v0.9.33). Chạy tay / CI:

    python tests/run.py engine_cache

Không cần API key, không chạm mạng - chỉ test logic đánh dấu cache_control:
- _anthropic_mark_last: copy-khi-đánh-dấu, KHÔNG mutate conv gốc, marker không tích luỹ
  qua các vòng tool (trần Anthropic 4 breakpoint/request).
- _or_mark_system: đánh dấu system OpenRouter (model Claude), không mutate or_messages.
- _is_claude_model: nhận diện model họ Claude.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path (xem tests/python/_paths.py)
import json
import sys
import os


from engine import (_anthropic_mark_last, _apply_anthropic_cache,   # noqa: E402
                    _is_claude_model, _or_mark_system)

_fails = []


def check(name, cond):
    print(("ok  " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


def count_markers(obj):
    """Đếm số cache_control trong 1 payload (đệ quy)."""
    if isinstance(obj, dict):
        return sum(count_markers(v) for v in obj.values()) + (1 if "cache_control" in obj else 0)
    if isinstance(obj, list):
        return sum(count_markers(v) for v in obj)
    return 0


# ---- 1. _anthropic_mark_last: content dạng chuỗi ----
conv = [{"role": "user", "content": "câu hỏi"}]
marked = _anthropic_mark_last(conv)
check("str: message cuối được đánh dấu", count_markers(marked) == 1)
check("str: conv gốc KHÔNG bị mutate", count_markers(conv) == 0)
check("str: giữ nguyên text", marked[-1]["content"][0]["text"] == "câu hỏi")

# ---- 2. _anthropic_mark_last: content dạng list (tool_result) ----
conv = [{"role": "user", "content": "hỏi"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "f", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "kq"}]}]
marked = _anthropic_mark_last(conv)
check("list: chỉ 1 marker", count_markers(marked) == 1)
check("list: marker nằm ở block cuối message cuối", "cache_control" in marked[-1]["content"][-1])
check("list: conv gốc sạch", count_markers(conv) == 0)

# ---- 3. Mô phỏng vòng tool: marker KHÔNG tích luỹ, mỗi request <= 4 breakpoint ----
sys_txt = "system prompt dài" * 100
tools = [{"name": "tool_a", "input_schema": {}}, {"name": "tool_b", "input_schema": {}}]
tools[-1]["cache_control"] = {"type": "ephemeral"}   # như anthropic_chat_with_mcp làm 1 lần
conv = [{"role": "user", "content": "hỏi"}]
for rnd in range(5):   # 5 vòng tool liên tiếp
    payload = {"messages": _anthropic_mark_last(conv), "tools": tools,
               "system": [{"type": "text", "text": sys_txt, "cache_control": {"type": "ephemeral"}}]}
    n = count_markers(payload)
    if n > 4:
        check(f"vòng {rnd}: {n} breakpoint vượt trần 4", False)
        break
    # giả lập model gọi tool + tool_result nối vào conv (như vòng thật)
    conv.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{rnd}", "name": "tool_a", "input": {}}]})
    conv.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{rnd}", "content": "kq"}]})
else:
    check("5 vòng tool: breakpoint mỗi request luôn <= 4 (3)", True)
check("5 vòng tool: conv gốc vẫn 0 marker", count_markers(conv) == 0)
check("payload serialize được JSON", bool(json.dumps(payload)))

# ---- 4. _or_mark_system ----
msgs = [{"role": "system", "content": "sys dài"}, {"role": "user", "content": "hỏi"},
        {"role": "assistant", "content": "đáp"}]
out = _or_mark_system(msgs)
check("or: system được đánh dấu", isinstance(out[0]["content"], list)
      and "cache_control" in out[0]["content"][0])
check("or: chỉ đánh dấu 1 chỗ", count_markers(out) == 1)
check("or: messages gốc KHÔNG mutate (or_messages sống qua nhiều lượt)",
      isinstance(msgs[0]["content"], str) and count_markers(msgs) == 0)
check("or: user/assistant giữ nguyên object", out[1] is msgs[1] and out[2] is msgs[2])
check("or: không system → giữ nguyên", count_markers(_or_mark_system([{"role": "user", "content": "x"}])) == 0)

# ---- 5. _is_claude_model ----
check("claude qua openrouter", _is_claude_model("anthropic/claude-sonnet-4-6"))
check("tên có claude", _is_claude_model("claude-opus-4-8"))
check("gpt không phải claude", not _is_claude_model("openai/gpt-4o-mini"))
check("None an toàn", not _is_claude_model(None))

# ---- 6. _apply_anthropic_cache (nhánh chat thuần - hành vi cũ giữ nguyên) ----
payload = {"system": "sys", "messages": [{"role": "user", "content": "a"},
                                         {"role": "assistant", "content": "b"},
                                         {"role": "user", "content": "c"}]}
_apply_anthropic_cache(payload)
check("chat thuần: system thành block có marker", "cache_control" in payload["system"][0])
check("chat thuần: tổng breakpoint <= 4", count_markers(payload) <= 4)

# ---- 7. 1.3.39: đuôi đổi theo lượt (đồng hồ, ngôn ngữ, mức dùng) không làm trượt cache phần tĩnh ----
tinh = "# JOYCE OS\nluật..." * 50
def _sys(gio, token):
    return tinh + f"\n\n# === BÂY GIỜ ===\n{gio}\n\n# === MỨC DÙNG HÔM NAY (Joyce tự đo) ===\n{token} token"
p1 = {"system": _sys("09:01", 1000), "messages": [{"role": "user", "content": "a"}]}
p2 = {"system": _sys("09:07", 5321), "messages": [{"role": "user", "content": "a"}]}
_apply_anthropic_cache(p1)
_apply_anthropic_cache(p2)
check("tách đôi: phần tĩnh mang marker, đuôi không", "cache_control" in p1["system"][0]
      and "cache_control" not in p1["system"][1] and p1["system"][1]["text"].startswith("\n\n# === BÂY GIỜ"))
check("tách đôi: hai lượt khác giờ có phần tĩnh giống hệt (trúng cache)", p1["system"][0] == p2["system"][0])
check("tách đôi: ghép lại đúng bản gốc", p1["system"][0]["text"] + p1["system"][1]["text"] == _sys("09:01", 1000))
check("tách đôi: vẫn <= 4 breakpoint", count_markers(p1) <= 4)
o2 = _or_mark_system([{"role": "system", "content": _sys("10:00", 1)}])
check("or: tách đôi, chỉ phần tĩnh có marker", len(o2[0]["content"]) == 2 and count_markers(o2) == 1)
from engine import _system_blocks  # noqa: E402
check("không có đuôi thì giữ một khối như cũ", len(_system_blocks("chỉ có luật", {"type": "ephemeral"})) == 1)

if _fails:
    print(f"\nFAIL - {len(_fails)} test: {_fails}")
    sys.exit(1)
print("\nOK - test_engine_cache: tất cả pass")
