"""Resonance: joyce_goal phải tới được tay bộ não theo ĐÚNG đường mà prompt chỉ, trên từng engine.

    python tests/run.py resonance_tool_path

Lỗi thật, tìm ra khi kiểm bằng mã sau pilot lần 2 (07/10/2026): dòng gợi ý trong system prompt bảo
"chưa thấy tool thì tìm bằng joyce_search_tools". Trên engine Claude Code, plugin đi bằng MCP in-process
"joyce-plugins" và hub bị báo bỏ nhóm plugin (X-Joyce-No-Plugins), nên joyce_search_tools không bao giờ
trả về joyce_goal ở đó. Gợi ý đúng cho mọi engine trừ engine dùng nhiều nhất.

Test chỉ kiểm cơ chế (đăng ký, danh sách tới engine, đường tìm, nguồn tin người dùng). Nó KHÔNG chứng
minh model sẽ chọn đúng; việc đó chỉ pilot thật mới trả lời được. Không gọi model, không đọc settings thật.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import tempfile
from pathlib import Path

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-res-toolpath-")

import claude_agent_sdk  # noqa: E402
import claude_sdk_engine  # noqa: E402
import luot_dang_chay  # noqa: E402
import main  # noqa: E402
import mcp_hub  # noqa: E402
import plugins_host  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


import resonance_store as RS  # noqa: E402
import turn_context  # noqa: E402
import _resonance_agent as RA  # noqa: E402


def _brain():
    d = Path(tempfile.mkdtemp(prefix="brain-toolpath-")).resolve()
    (d / "Joyce").mkdir()
    return str(d)


# A1: "bật" là lượt của một agent đã bật Cộng hưởng (ngữ cảnh lượt), không còn là công tắc brain.
ON, OFF = _brain(), _brain()
AG = RA.enable(RS.GoalStore(), ON)


def _names(vault):
    return {t["fn"] for t in plugins_host.plugin_tools("full", vault, scope_vault=False)[0]}


def _in_agent_turn(fn):
    with RA.turn(AG, "sess-tp", 1, "x", ON):
        return fn()


def _in_plain_turn(fn):
    tok = turn_context.bind(turn_context.make("dashboard", chat_id="sess-plain", la_chu=True,
                                              session_id="sess-plain", message_id=1))
    try:
        return fn()
    finally:
        turn_context.reset(tok)


# 1. Đăng ký theo đúng lượt và brain
check("lượt của agent đã bật: plugin_tools có joyce_goal", "joyce_goal" in _in_agent_turn(lambda: _names(ON)))
check("lượt chat thường cùng brain: plugin_tools không có joyce_goal",
      "joyce_goal" not in _in_plain_turn(lambda: _names(ON)))
check("ngoài lượt (danh sách hub dùng chung), brain có agent bật: có joyce_goal (chỉ gợi ý)", "joyce_goal" in _names(ON))
check("brain không có agent nào bật: không có joyce_goal", "joyce_goal" not in _names(OFF))
check("không biết brain: không có joyce_goal", "joyce_goal" not in _names(None))

# 2. Danh sách tới engine Claude: server in-process "joyce-plugins", hub được báo bỏ plugin
_seen = {}
_real = claude_agent_sdk.create_sdk_mcp_server


def _spy(name, tools=None, **kw):
    _seen[name] = {getattr(t, "name", None): getattr(t, "description", "") for t in (tools or [])}
    return _real(name, tools=tools, **kw)


claude_agent_sdk.create_sdk_mcp_server = _spy
_cfg = Path(tempfile.mkdtemp(prefix="cfg-toolpath-")) / "mcp.json"
_cfg.write_text(json.dumps({"mcpServers": {"joyce": {"type": "http", "url": "http://127.0.0.1:1/mcp/hub",
                                                     "headers": {"X-Joyce-Engine": "claude"}}}}), encoding="utf-8")


def _servers(vault):
    _seen.clear()
    _desc_seen.clear()
    e = claude_sdk_engine.ClaudeSDK(cwd=vault or ON)
    e.mcp_config = str(_cfg)
    e.joyce_vault = vault
    out = e._mcp_servers()[0] or {}
    _desc_seen.update(_seen.get("joyce-plugins") or {})
    return out


_desc_seen = {}


try:
    s_on = _in_agent_turn(lambda: _servers(ON))
    desc_on = dict(_desc_seen)
    check("Claude: có server joyce-plugins", "joyce-plugins" in s_on)
    check("Claude: joyce-plugins mang joyce_goal", "joyce_goal" in _seen.get("joyce-plugins", []))
    check("Claude: hub nhận X-Joyce-No-Plugins=1",
          (s_on.get("joyce", {}).get("headers") or {}).get("X-Joyce-No-Plugins") == "1")
    _servers(OFF)
    desc_off = dict(_desc_seen)
    check("Claude, brain tắt: joyce-plugins không mang joyce_goal", "joyce_goal" not in _seen.get("joyce-plugins", []))
    _servers(None)
    check("Claude, chưa đặt joyce_vault: không mang joyce_goal (main._apply_mcp phải đặt)",
          "joyce_goal" not in _seen.get("joyce-plugins", []))
finally:
    claude_agent_sdk.create_sdk_mcp_server = _real


# 3. Đường tìm: hub tìm ra joyce_goal khi có plugin (engine API/Codex), KHÔNG khi đi đường Claude
async def _search(include_plugins):
    _, route = await mcp_hub.discover_all("full", vault_root=ON, include_plugins=include_plugins,
                                          include_ambient=not include_plugins, force_refresh=True, force_lazy=True)
    res = await route[mcp_hub._LAZY_SEARCH]["call"]({"query": "joyce_goal mục tiêu"})
    return "joyce_goal" in str(res)


check("hub có plugin (engine API/Codex): joyce_search_tools tìm ra joyce_goal", asyncio.run(_search(True)))
check("hub đường Claude (No-Plugins): joyce_search_tools KHÔNG tìm ra joyce_goal", not asyncio.run(_search(False)))

# 4. Prompt chỉ đúng đường cho từng engine (dòng gợi ý chỉ có trong lượt của agent đã bật)
p_on = _in_agent_turn(lambda: main.build_system_prompt(ON))
p_off = main.build_system_prompt(OFF)
check("lượt chat thường cùng brain: prompt không nhắc joyce_goal",
      "joyce_goal" not in _in_plain_turn(lambda: main.build_system_prompt(ON)))
_full = "mcp__joyce-plugins__joyce_goal"
check("prompt nêu ToolSearch kèm tên đầy đủ đúng server in-process",
      "ToolSearch" in p_on and _full in p_on and _full == "mcp__" + "joyce-plugins" + "__joyce_goal")
check("prompt vẫn nêu joyce_search_tools cho engine khác", "joyce_search_tools" in p_on)
check("prompt nêu đủ ranh giới: làm luôn, joyce_task, joyce_schedule, joyce_goal",
      all(x in p_on for x in ("làm luôn", "joyce_task", "joyce_schedule", "joyce_goal op=create")))
check("brain tắt: prompt không nhắc joyce_goal hay ToolSearch",
      "joyce_goal" not in p_off and _full not in p_off)

# 5. Mô tả tool THẬT SỰ tới engine Claude (metadata của server in-process), brain bật và tắt.
# Brain tắt Resonance không được nhận chỉ dẫn mới nào: mô tả joyce_task giữ nguyên, không nhắc joyce_goal
# (review PR #579, P2). Ranh giới chỉ nằm ở mô tả joyce_goal và dòng gợi ý, hai thứ chỉ có khi bật.
check("joyce_task: mô tả tới engine giống hệt nhau khi bật và khi tắt",
      bool(desc_on.get("joyce_task")) and desc_on.get("joyce_task") == desc_off.get("joyce_task"))
check("joyce_task: mô tả không nhắc joyce_goal hay ranh giới Resonance",
      "joyce_goal" not in desc_off.get("joyce_task", "") and "hết trách nhiệm" not in desc_off.get("joyce_task", ""))
check("brain tắt: engine không nhận joyce_goal", "joyce_goal" not in desc_off)
check("joyce_goal (brain bật): nhắc sửa theo phản hồi và chỉ việc một lần sang joyce_task",
      "sửa theo phản hồi" in desc_on.get("joyce_goal", "") and "joyce_task" in desc_on.get("joyce_goal", ""))

# 6. Nguồn tin người dùng: tool đọc đúng lượt đang chạy của brain
k = luot_dang_chay.bat_dau("web:sess-tp", ON, msg_id=11, user_text="lời thật của người dùng")
lu = luot_dang_chay.doan_luot(ON) or {}
check("lượt đang chạy: đúng phiên, id tin, lời người dùng",
      lu.get("chat_id") == "web:sess-tp" and int(lu.get("msg_id") or 0) == 11
      and lu.get("user_text") == "lời thật của người dùng")
check("A1: đọc lời theo ĐÚNG khoá (phiên, id tin) của ngữ cảnh lượt",
      luot_dang_chay.loi_cua_luot("web:sess-tp", 11, ON) == "lời thật của người dùng"
      and luot_dang_chay.loi_cua_luot("web:sess-tp", 12, ON) is None
      and luot_dang_chay.loi_cua_luot("web:khac", 11, ON) is None)
luot_dang_chay.ket_thuc(k)
check("hết lượt: không còn lượt để đoán", not luot_dang_chay.doan_luot(ON))
check("hết lượt: khoá chính xác cũng không còn", luot_dang_chay.loi_cua_luot("web:sess-tp", 11, ON) is None)

print(f"\n{'FAIL' if _fails else 'OK'}: {len(_fails)} lỗi")
raise SystemExit(1 if _fails else 0)
