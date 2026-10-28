"""Khối Joyce Harness trên trang Sơ đồ (server/harness_map.py + /work/factory -> harness, 1.3.39).

    python tests/run.py harness_map      (không mạng, không model)

Hợp đồng: đèn lấy từ số thật, thứ chưa làm phải xám; mọi thành phần server trả ra đều có nhãn
trong dashboard/sodo.js (thiếu là dòng biến mất trong im lặng).
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import pathlib
import re
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-hxmap-")
BR = pathlib.Path(tempfile.mkdtemp(prefix="joyce-brains-hxmap-"))
os.environ["BRAINS_DIR"] = str(BR)

import harness_map  # noqa: E402

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def _st(snap, k):
    return next(x for t in snap["tiers"] for x in t["items"] if x["k"] == k)


base = dict(stages={}, guard_on=True, shared_agents=9, tool_rounds=30, trim_chars=80000,
            brains_total=61, brains_self_improve=61, agents=[], evals_brain=0)
s = harness_map.snapshot(**base)
check("ba tầng A, B, C", [t["id"] for t in s["tiers"]] == ["A", "B", "C"])
check("đếm tổng và số xanh khớp các đèn", s["total"] == 15 and s["ok"] == sum(
    1 for t in s["tiers"] for x in t["items"] if x["state"] == "ok"))
check("trần token đã chốt nhưng chưa ép: đèn xám, không tô xanh", _st(s, "budget")["state"] == "off"
      and _st(s, "budget")["v"] == {"n": 500000, "m": 1000000})
check("joyce-guard tắt thì đèn đỏ", _st(harness_map.snapshot(**dict(base, guard_on=False)), "guard")["state"] == "bad")
check("brain chưa có bộ ca thử: đèn xám", _st(s, "evals")["state"] == "off")
ag = [{"skills": ["a"], "allowed_effects": ["read"]}, {"skills": []}]
s2 = harness_map.snapshot(**dict(base, agents=ag, evals_brain=2,
                                 stages={"proposals": {"cho_chu_duyet": 1, "eval_failed": 0},
                                         "canary": {"canary": 1, "reverted": 1}}))
check("trợ lý: đếm số có skill", _st(s2, "agents")["v"] == {"n": 2, "s": 1})
check("khai phạm vi: 1/2 thì chưa xanh", _st(s2, "scope")["state"] == "off" and _st(s2, "scope")["v"] == {"n": 1, "m": 2})
check("có đề xuất chờ chủ thì cổng quyền vàng", _st(s2, "gate")["state"] == "warn" and _st(s2, "gate")["v"]["n"] == 1)
check("canary đã lật thì vàng", _st(s2, "canary")["state"] == "warn")
# A01 (1.3.42): chưa đủ dữ liệu KHÔNG được hiện xanh.
check("chưa có telemetry: đèn bằng chứng canary XÁM (off), không xanh", _st(s, "telemetry")["state"] == "off")
check("có telemetry thì xanh", _st(harness_map.snapshot(**dict(base, telemetry_ready=True)), "telemetry")["state"] == "ok")
for tt in ("legacy_review", "het_han", "partial", "conflict"):
    sx = harness_map.snapshot(**dict(base, stages={"canary": {tt: 2}}))
    check(f"canary ở trạng thái {tt}: vàng và đếm vào 'cần xem', không xanh", _st(sx, "canary")["state"] == "warn" and _st(sx, "canary")["v"]["l"] == 2)
check("không có canary nào cần xem: canary xanh", _st(harness_map.snapshot(**dict(base, stages={"canary": {"canary": 1}})), "canary")["state"] == "ok")

js = (pathlib.Path(ROOT) / "dashboard" / "sodo.js").read_text(encoding="utf-8")
hx_keys = set(re.findall(r"^\s{4}([a-z]+): \[\"sodo\.hx\.", js, re.M))
server_keys = {x["k"] for t in s["tiers"] for x in t["items"]}
check("mọi thành phần server trả ra đều có nhãn trong sodo.js", server_keys <= hx_keys and server_keys == hx_keys)

# ---- đi qua route thật
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
c = TestClient(main.app, base_url="http://127.0.0.1:8080")
chung = main._default_brain_dir()
r = c.get("/work/factory", params={"brain": str(chung)})
hx = (r.json() or {}).get("harness") or {}
check("/work/factory trả khối harness", r.status_code == 200 and hx.get("version") == harness_map.STANDARD_VERSION)
check("route: joyce-guard bật thật", _st(hx, "guard")["state"] == "ok")
check("route: 9 trợ lý dùng chung thật", _st(hx, "shared")["v"]["n"] == 9)
check("route: brain chung thấy trợ lý dùng chung trong số trợ lý", _st(hx, "agents")["v"]["n"] >= 9)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
