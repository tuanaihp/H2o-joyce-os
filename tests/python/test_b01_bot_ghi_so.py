"""B01 (gói B): lượt trả lời của bot được host ghi vào sổ lượt chạy, mà sổ hỏng không làm hỏng lượt.

    python tests/run.py b01_bot_ghi_so      (không mạng, không model)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import sys
import tempfile
from pathlib import Path

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-b01bot-state-")
TEMP = Path(tempfile.mkdtemp(prefix="joyce-b01bot-"))
(TEMP / "Joyce" / "evals").mkdir(parents=True)
(TEMP / "Joyce" / "evals" / "tro-ly-ban-hang.json").write_text('{"cases": []}', encoding="utf-8")

import chatbot_runtime as CR  # noqa: E402
import chatbot_store  # noqa: E402
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


CFG = {"id": "bot1", "agent": {"slug": "tro-ly-ban-hang", "brain": "Ban Hang"}, "brain": "Ban Hang", "engine": "claude"}
NOI_DUNG = {"v": "Bạn là trợ lý bán hàng."}
CR._deps["read_agent"] = lambda brain, slug: ({"type": "agent", "name": "Bán hàng"}, NOI_DUNG["v"])
CR._deps["brain_root"] = lambda brain: str(TEMP)
chatbot_store.get_bot = lambda bid: dict(CFG)


def rows():
    return L.danh_sach(brain_id="Ban Hang", agent_id="tro-ly-ban-hang")


# 1. mở và chốt lượt: revision chụp từ nội dung thật
rid = CR._so_mo("bot1", {"chat_id": "c1"})
r = L.lay(rid)
check("mở lượt cho bot gắn agent: ghi agent, brain, kênh bot, revision thật (agent và bộ ca thử)",
      r and r["agent_id"] == "tro-ly-ban-hang" and r["brain_id"] == "Ban Hang" and r["entrypoint"] == "bot"
      and len(r["agent_revision"]) == 64 and len(r["eval_revision"]) == 64, r)
CR._so_chot(rid, "completed")
check("chốt lượt hoàn tất, chưa kiểm chứng", L.lay(rid)["status"] == "completed" and L.lay(rid)["verification_status"] == "unverified")

# 2. agent đổi nội dung thì revision đổi
NOI_DUNG["v"] = "Bạn là trợ lý bán hàng. Luôn chào khách trước."
rid2 = CR._so_mo("bot1", {"chat_id": "c1"})
check("agent đổi nội dung: revision lượt mới khác lượt cũ (bằng chứng không lẫn giữa hai bản)",
      L.lay(rid2)["agent_revision"] != L.lay(rid)["agent_revision"])
CR._so_chot(rid2, "completed")

# 3. bot không gắn agent: không ghi sổ
chatbot_store.get_bot = lambda bid: {"id": "bot9", "brain": "Ban Hang"}
check("bot không gắn agent thì không có lượt trong sổ (không có gì để gán bằng chứng)", CR._so_mo("bot9", {}) == "")
chatbot_store.get_bot = lambda bid: dict(CFG)

# 4. sổ hỏng không làm hỏng lượt
CR._deps["read_agent"] = lambda brain, slug: (_ for _ in ()).throw(RuntimeError("không đọc được agent"))
rid3 = CR._so_mo("bot1", {})
check("agent đọc không được: vẫn ghi lượt với revision rỗng (không giả vờ biết), không ném lỗi",
      rid3 and L.lay(rid3)["agent_revision"] == "")
L.dong()
_duong_that = L._duong_dan
L._duong_dan = lambda: Path(tempfile.gettempdir()) / "khong-ton-tai-xyz" / "a" / "so.sqlite3"
CR._deps["read_agent"] = lambda brain, slug: ({"type": "agent"}, "ND")
check("sổ hỏng hẳn (không mở được file): _so_mo trả rỗng thay vì ném lỗi", CR._so_mo("bot1", {}) == "")
L._duong_dan = _duong_that
CR._so_chot("", "completed")
check("chốt với run_id rỗng là no-op", True)

# 5. đường đi thật qua _make_answer_fn: lượt im lặng không vào sổ, lượt lỗi được chốt failed
import config  # noqa: E402
config.STATE_DIR = Path(tempfile.mkdtemp(prefix="joyce-b01bot-state2-"))
L.dong()
CR._deps["read_agent"] = lambda brain, slug: ({"type": "agent"}, "ND")
fn = CR._make_answer_fn("bot1")
CR._nen_tra_loi = lambda cfg, meta: False
out = asyncio.run(fn("xin chào", meta={"chat_id": "c1"}))
check("lượt im lặng (không gọi model) không để lại dòng nào trong sổ", out.get("im_lang") and rows() == [], rows())

CR._nen_tra_loi = lambda cfg, meta: True
chatbot_store.ap_ngoai_le = lambda cfg, meta: (_ for _ in ()).throw(RuntimeError("hỏng giữa chừng"))
try:
    asyncio.run(fn("xin chào", meta={"chat_id": "c1"}))
    nem = False
except RuntimeError:
    nem = True
rs = rows()
check("lượt nổ lỗi: lỗi vẫn tới người gọi, và sổ chốt failed (không treo running)",
      nem and len(rs) == 1 and rs[0]["status"] == "failed" and rs[0]["block_kind"] == "system", rs)

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b01_bot_ghi_so: tất cả pass")
