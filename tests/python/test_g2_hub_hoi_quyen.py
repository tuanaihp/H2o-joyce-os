"""G2 #2 (hoàn tất): MỌI tool của MCP Hub hỏi quyết định quyền chung, không chỉ tool ghi file.

    python tests/run.py g2_hub_hoi_quyen      (không mạng, không model; vault tạm)

Agent đã khai `allowed_effects` mà gọi tool có effect ngoài danh sách thì bị chặn, và lần chặn được ghi vào sổ lượt chạy. Agent chưa khai, hoặc route
không có ngữ cảnh lượt chạy: chạy như cũ.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import pathlib
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-g2hub-state-")

import mcp_hub  # noqa: E402
import run_context as RX  # noqa: E402
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


# ---------------- ánh xạ effect
H = mcp_hub.hub_effect
check("tool đọc (MCP, lõi, plugin) là read", H({"effect": "read", "source_type": "mcp"}) == "read" and H({"effect": "none", "source_type": "builtin"}) == "read")
check("tool lõi của Joyce ghi vào brain là internal_write", H({"effect": "write", "source_type": "builtin"}) == "internal_write")
check("tool lõi mức full (shell, hành động nặng) là external_write", H({"effect": "full", "source_type": "builtin"}) == "external_write")
check("tool MCP ghi ra hệ thống ngoài là external_write", H({"effect": "write", "source_type": "mcp"}) == "external_write")
check("tool MCP nguy hiểm là destructive", H({"effect": "danger", "source_type": "mcp"}) == "destructive")
check("plugin theo mức quyền: readonly -> read, safe -> internal_write, full -> external_write",
      H({"effect": "x", "source_type": "plugin", "required_mode": "readonly"}) == "read"
      and H({"effect": "x", "source_type": "plugin", "required_mode": "safe"}) == "internal_write"
      and H({"effect": "x", "source_type": "plugin", "required_mode": "full"}) == "external_write")
check("effect lạ, không nhận ra: thận trọng, external_write", H({"effect": "gi-do", "source_type": "mcp"}) == "external_write" and H({}) == "external_write")

# ---------------- bọc lời gọi
da_goi = []


async def goc_async(args):
    da_goi.append(("async", args))
    return "xong-async"


def goc_dong_bo_tra_coroutine(args):
    async def _():
        da_goi.append(("sync", args))
        return "xong-sync"
    return _()


def route_gia():
    r = {"doc": {"effect": "read", "source_type": "mcp", "call": goc_async},
         "ghi_ngoai": {"effect": "write", "source_type": "mcp", "call": goc_async},
         "pha": {"effect": "danger", "source_type": "mcp", "call": goc_dong_bo_tra_coroutine}}
    for k, v in r.items():
        mcp_hub._boc_quyen(k, v)
    return r


def goi(route, ten, ctx):
    async def go():
        tk = RX.dat(ctx)
        try:
            return await route[ten]["call"]({"x": 1})
        finally:
            RX.go(tk)
    return asyncio.run(go())


rid = L.bat_dau(brain_id="b", agent_id="doi-soat", entrypoint="task")
chi_doc = RX.RunContext(rid, "doi-soat", "b", "task", ("read",))
chua_khai = RX.RunContext("r2", "a", "b", "task", None)
rong = RX.RunContext("r3", "a", "b", "task", ())
rt = route_gia()

check("agent khai [read]: tool đọc chạy", goi(rt, "doc", chi_doc) == "xong-async")
r = goi(rt, "ghi_ngoai", chi_doc)
check("agent khai [read]: tool ghi ra ngoài BỊ CHẶN, nói rõ effect và tên tool, tool gốc KHÔNG được gọi",
      str(r).startswith("ERROR") and "external_write" in r and "ghi_ngoai" in r and ("async", {"x": 1}) not in da_goi[1:], (r, da_goi))
da_goi.clear()
check("agent khai [read]: tool nguy hiểm (gốc đồng bộ trả coroutine) cũng bị chặn", str(goi(rt, "pha", chi_doc)).startswith("ERROR") and not da_goi)
check("lần chặn được GHI vào sổ lượt chạy (dấu hiệu cần xem của pilot)", L.lay(rid)["quyen_bi_chan"] == 2, L.lay(rid)["quyen_bi_chan"])
check("thống kê gộp số lần bị chặn", L.thong_ke(brain_id="b", agent_id="doi-soat")["lan_bi_chan_quyen"] == 2)
check("agent khai [read, external_write]: tool ghi ngoài chạy", goi(rt, "ghi_ngoai", RX.RunContext("r4", "a", "b", "task", ("read", "external_write"))) == "xong-async")
check("agent khai [] (chỉ tính toán): ngay cả tool đọc cũng bị chặn", str(goi(rt, "doc", rong)).startswith("ERROR"))
check("agent CHƯA khai: mọi tool chạy như cũ", goi(rt, "ghi_ngoai", chua_khai) == "xong-async" and goi(rt, "pha", chua_khai) == "xong-sync")
check("không có ngữ cảnh lượt chạy: chạy như cũ", goi(rt, "ghi_ngoai", None) == "xong-async")
check("bọc hai lần không lồng thêm lớp (route cache dùng lại entry)", (lambda e: (mcp_hub._boc_quyen("t", e), e["call"], mcp_hub._boc_quyen("t", e), e["call"]))(
    {"effect": "read", "source_type": "mcp", "call": goc_async})[1] is not None)
e1 = {"effect": "read", "source_type": "mcp", "call": goc_async}
mcp_hub._boc_quyen("t", e1)
c1 = e1["call"]
mcp_hub._boc_quyen("t", e1)
check("bọc lần hai giữ nguyên hàm đã bọc", e1["call"] is c1)

# ---------------- qua discover_all thật (tool lõi của hub)
v = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g2hub-vault-"))
(v / "wiki").mkdir()
mcp_hub.invalidate_cache()
tools, route = asyncio.run(mcp_hub.discover_all("full", vault_root=str(v)))
# Hai meta-tool của tầng lười (tìm và chạy tool MCP) không tự có effect; chúng điều phối sang route ĐẦY ĐỦ, mà route đó đã được bọc, nên quyền vẫn được hỏi.
META = {"joyce_search_tools", "joyce_run_tool"}
check("discover_all trả route có tool lõi và mọi `call` (trừ hai meta-tool của tầng lười) đã được bọc hỏi quyền",
      "joyce_write_file" in route and all(getattr(e.get("call"), "_joyce_quyen", False) for k, e in route.items() if e.get("call") and k not in META),
      [k for k, e in route.items() if k not in META and not getattr(e.get("call"), "_joyce_quyen", False)])
rid2 = L.bat_dau(brain_id="b", agent_id="chi-doc", entrypoint="bot")
ctx2 = RX.RunContext(rid2, "chi-doc", "b", "bot", ("read",))


async def thu():
    tk = RX.dat(ctx2)
    try:
        return await route["joyce_write_file"]["call"]({"path": "wiki/x.md", "content": "N"})
    finally:
        RX.go(tk)


kq = asyncio.run(thu())
check("tool ghi file của hub, qua route thật, bị chặn cho agent [read] và file KHÔNG được tạo",
      str(kq).startswith("ERROR") and not (v / "wiki" / "x.md").exists(), kq)
check("... và lần chặn nằm trong sổ", L.lay(rid2)["quyen_bi_chan"] >= 1)

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g2_hub_hoi_quyen: tất cả pass")
