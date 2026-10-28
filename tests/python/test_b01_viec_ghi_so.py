"""B01 (gói B): việc giao cho trợ lý được host ghi vào sổ lượt chạy, theo trạng thái việc SAU khi worker xong.

    python tests/run.py b01_viec_ghi_so      (không mạng, không model)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import sys
import tempfile
from pathlib import Path

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-b01viec-state-")
import agent_jobs  # noqa: E402
import run_ledger as L  # noqa: E402
import tasks  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


BRAIN = Path(tempfile.mkdtemp(prefix="joyce-b01viec-")) / "Ban Hang"
(BRAIN / "agents").mkdir(parents=True)
(BRAIN / "agents" / "tro-ly.md").write_text("---\ntype: agent\nname: T\n---\nNội dung A\n", encoding="utf-8")


class Kho:
    def __init__(self):
        self.t = {}

    def get_task(self, tid):
        return self.t.get(tid)


tf = object.__new__(tasks.TasksFeature)
tf.store = Kho()


def viec(tid, key):
    return {"id": tid, "brain_root": str(BRAIN), "idempotency_key": key, "current_run_id": "run-" + tid, "execution_mode": "auto"}


# 1. việc giao cho trợ lý được mở lượt, mang revision của file agent thật
t1 = viec("t1", agent_jobs.assign_key("ABC", "tro-ly", "n1"))
rid = tf._so_mo_viec(t1)
r = L.lay(rid)
check("việc giao cho trợ lý: mở lượt, ghi agent, brain, cửa task, revision từ file agent thật",
      r and r["agent_id"] == "tro-ly" and r["brain_id"] == "Ban Hang" and r["entrypoint"] == "task" and len(r["agent_revision"]) == 64
      and r["logical_execution_id"] == "task:t1" and r["attempt_id"] == "run-t1", r)
import hashlib  # noqa: E402
check("agent_revision = SHA-256 của đúng nội dung file agent (so được với candidate_hash của canary)",
      r["agent_revision"] == hashlib.sha256((BRAIN / "agents" / "tro-ly.md").read_text(encoding="utf-8").encode("utf-8")).hexdigest())
check("việc thường (không giao cho trợ lý) không vào sổ", tf._so_mo_viec(viec("t2", "khac:abc")) == "")

# 2. chốt theo trạng thái việc
cases = [("done", "", "completed"), ("review", "", "needs_approval"), ("blocked", "approval", "needs_input"),
         ("blocked", "transient", "interrupted"), ("ready", "", "interrupted"), ("cancelled", "", "canceled"), ("lạ", "", "unknown")]
for i, (stt, bk, mong) in enumerate(cases):
    tid = f"c{i}"
    rid = tf._so_mo_viec(viec(tid, agent_jobs.assign_key("ABC", "tro-ly", f"n{i}")))
    tf.store.t[tid] = {"id": tid, "status": stt, "block_kind": bk}
    tf._so_chot_viec(tid, rid)
    check(f"việc {stt}/{bk or '-'} chốt thành {mong}", L.lay(rid)["status"] == mong, L.lay(rid)["status"])
check("việc xong ở trạng thái done KHÔNG tự thành đạt (chưa có kiểm chứng)",
      L.lay(L.danh_sach(agent_id="tro-ly")[-1]["run_id"]) is not None
      and all(x["verification_status"] == "unverified" for x in L.danh_sach(agent_id="tro-ly")))

# 3. retry: cùng một việc chạy hai lần vẫn là một logical execution
a = tf._so_mo_viec(viec("t9", agent_jobs.assign_key("ABC", "tro-ly", "n9")))
tf.store.t["t9"] = {"id": "t9", "status": "ready"}
tf._so_chot_viec("t9", a)
tt = viec("t9", agent_jobs.assign_key("ABC", "tro-ly", "n9"))
tt["current_run_id"] = "run-t9-lan2"
b = tf._so_mo_viec(tt)
tf.store.t["t9"] = {"id": "t9", "status": "done"}
tf._so_chot_viec("t9", b)
check("việc bị trả về hàng đợi rồi chạy lại: hai lần chạy nhưng một logical execution",
      len([x for x in L.danh_sach(agent_id="tro-ly") if x["logical_execution_id"] == "task:t9"]) == 2
      and L.thong_ke(agent_id="tro-ly")["thu_lai"] >= 1)

# 4. sổ hỏng không làm hỏng worker
_duong = L._duong_dan
L.dong()
L._duong_dan = lambda: Path(tempfile.gettempdir()) / "khong-ton-tai-xyz2" / "a" / "so.sqlite3"
check("sổ hỏng: mở lượt trả rỗng, không ném lỗi", tf._so_mo_viec(t1) == "")
tf._so_chot_viec("t1", "run-khong-co")
check("sổ hỏng: chốt không ném lỗi", True)
L._duong_dan = _duong

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b01_viec_ghi_so: tất cả pass")
