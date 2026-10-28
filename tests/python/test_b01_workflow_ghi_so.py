"""B01 (gói B): mỗi bước workflow gắn agent được host ghi vào sổ lượt chạy, theo kết quả thật của bước.

    python tests/run.py b01_workflow_ghi_so      (không mạng, không model: engine giả)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-b01wf-state-")
import main  # noqa: E402
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


class EngineGia:
    def __init__(self, evs):
        self.evs = evs

    async def query(self, prompt):
        for ev in self.evs:
            yield ev


def mk_gia(kich_ban):
    hang = list(kich_ban)

    def _mk(sysprompt, model=None, provider="", extra_tools=()):
        return EngineGia(hang.pop(0) if hang else [{"type": "final", "content": ""}])
    return _mk


def sysprompt_gia(slug):
    return (slug, "bạn là agent", "claude-sonnet-4", "anthropic-cli")


def chay(kich_ban, verify="", nid="n1"):
    node = SimpleNamespace(id=nid, kind="model_step", agent="nguoi-viet", verify_agent=verify, max_retries=0,
                           metadata={"legacy_index": 0})

    async def sink(ev):
        pass

    return asyncio.run(main._run_workflow_step(node, "viết bài", mk_gia(kich_ban), sysprompt_gia, sink, session_id="s1", brain_id="BrainThu"))


kq = chay([[{"type": "final", "content": "BẢN THẢO"}]], nid="n1")
rs = L.danh_sach(agent_id="nguoi-viet")
check("bước chạy sạch: một lượt completed, entrypoint workflow, chưa kiểm chứng (không có verify_agent)",
      kq.get("output") == "BẢN THẢO" and len(rs) == 1 and rs[0]["status"] == "completed" and rs[0]["entrypoint"] == "workflow"
      and rs[0]["verification_status"] == "unverified" and rs[0]["brain_id"] == "BrainThu", rs)

kq2 = chay([[{"type": "error", "content": "engine chết"}], [{"type": "error", "content": "engine chết"}]], nid="n2")
r2 = [x for x in L.danh_sach(agent_id="nguoi-viet") if x["ref"].endswith(":n2")]
check("bước lỗi engine rồi im (không chữ nào): lượt failed, KHÔNG thành hoàn tất hay đạt", not kq2.get("output") and len(r2) == 1 and r2[0]["status"] == "failed"
      and r2[0]["verification_status"] == "unverified", r2)

# logical execution theo (phiên, node): chạy lại cùng node là cùng một việc
chay([[{"type": "final", "content": "BẢN 2"}]], nid="n1")
logic = [x for x in L.danh_sach(agent_id="nguoi-viet") if x["logical_execution_id"] == "wf:s1:n1"]
check("chạy lại cùng node trong cùng phiên: hai lượt nhưng cùng một logical execution", len(logic) == 2)

# huỷ giữa chừng phải chốt
class EngineTreo:
    async def query(self, prompt):
        await asyncio.sleep(30)
        yield {"type": "final", "content": "x"}


async def huy():
    node = SimpleNamespace(id="n9", kind="model_step", agent="nguoi-viet", verify_agent="", max_retries=0, metadata={})

    async def sink(ev):
        pass
    t = asyncio.create_task(main._run_workflow_step(node, "p", lambda *a, **k: EngineTreo(), sysprompt_gia, sink, session_id="s9", brain_id="BrainThu"))
    await asyncio.sleep(0.3)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass


asyncio.run(huy())
r9 = [x for x in L.danh_sach(agent_id="nguoi-viet") if x["ref"].endswith(":n9")]
check("bước bị huỷ giữa chừng: lượt được chốt canceled, không treo running", len(r9) == 1 and r9[0]["status"] == "canceled", r9)

# sổ hỏng không làm hỏng bước
from pathlib import Path  # noqa: E402
_d = L._duong_dan
L.dong()
L._duong_dan = lambda: Path(tempfile.gettempdir()) / "khong-ton-tai-xyz3" / "a" / "so.sqlite3"
kq3 = chay([[{"type": "final", "content": "VẪN CHẠY"}]], nid="n3")
check("sổ hỏng hẳn: bước workflow vẫn chạy và trả kết quả bình thường", kq3.get("output") == "VẪN CHẠY", kq3)
L._duong_dan = _d

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b01_workflow_ghi_so: tất cả pass")
