"""G2 (chủ chốt 28/10/2026): tối đa 2 lượt tự cải tiến mỗi file mục tiêu mỗi 7 ngày.

    python tests/run.py g2_tran_tuan      (không mạng, không model; mọi file ở thư mục tạm)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import time

STATE = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g2t-state-"))
os.environ["JOYCE_STATE_DIR"] = str(STATE)

import factory  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
REL = "agents/tro-ly-a.md"


def goc(ngay):
    return f"---\ntype: agent\nname: Trợ lý A\nupdated: {ngay}\n---\n" + THAN


class Kho:
    def list_tasks(self, root, include_archived=False, limit=400):
        return []


def dung(cfg=None):
    root = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g2t-")) / "nguon"
    (root / "agents").mkdir(parents=True)
    (root / "Joyce" / "proposals").mkdir(parents=True)
    (root / REL).write_text(goc("2026-10-01"), encoding="utf-8", newline="")
    (root / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True, **(cfg or {})}), encoding="utf-8")

    async def inbox(text, **kw):
        pass

    deps = factory.FactoryDeps(brains=lambda: ["nguon"], task_root=lambda n: str(root), store=Kho(), enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda bb, n: [], settings_get=lambda: {}, state_dir=STATE)
    for p in STATE.glob("factory-state.json"):
        p.unlink()
    return root, deps


def de_xuat(root, ten, ngay):
    (root / "Joyce" / "proposals" / ten).write_text(
        "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + REL + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n"
        + goc(ngay) + "```\n", encoding="utf-8")


def trang_thai(root, ten):
    fm, _ = factory._proposal_front((root / "Joyce" / "proposals" / ten).read_text(encoding="utf-8"))
    return fm


root, deps = dung()
for i, ngay in enumerate(("2026-10-10", "2026-10-11", "2026-10-12"), 1):
    de_xuat(root, f"d{i}.md", ngay)
    asyncio.run(factory.proposal_tick(deps))
f1, f2, f3 = (trang_thai(root, f"d{i}.md") for i in (1, 2, 3))
check("hai lượt đầu tự áp", f1["status"] == "applied" and f2["status"] == "applied", (f1["status"], f2["status"]))
check("lượt thứ ba trong cùng tuần cho cùng file: KHÔNG tự áp, chờ chủ, mã quyết định là tuan",
      f3["status"] == "cho_chu_duyet" and str(f3.get("quyet_dinh")) == "tuan" and "7 ngày" in str(f3.get("ly_do_cho")), f3)
check("file mục tiêu dừng ở bản của lượt thứ hai", "2026-10-11" in (root / REL).read_text(encoding="utf-8"))

# file KHÁC không bị tính chung
(root / "agents" / "tro-ly-b.md").write_text(goc("2026-10-01").replace("Trợ lý A", "Trợ lý B"), encoding="utf-8", newline="")
(root / "Joyce" / "proposals" / "b1.md").write_text(
    "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: agents/tro-ly-b.md\n---\n# B\n\n## Bản nháp đầy đủ\n\n```markdown\n"
    + goc("2026-10-20").replace("Trợ lý A", "Trợ lý B") + "```\n", encoding="utf-8")
asyncio.run(factory.proposal_tick(deps))
check("trần tính theo TỪNG file: file khác vẫn được tự áp", trang_thai(root, "b1.md")["status"] == "applied")

# lượt cũ quá 7 ngày không tính
root, deps = dung()
for i in (1, 2):
    de_xuat(root, f"cu{i}.md", f"2026-09-0{i}")
    p = root / "Joyce" / "proposals" / f"cu{i}.md"
    p.write_text(p.read_text(encoding="utf-8").replace("status: pending", "status: applied\napplied_at: 2026-09-01 10:00"), encoding="utf-8")
de_xuat(root, "moi.md", "2026-10-15")
asyncio.run(factory.proposal_tick(deps))
check("hai lượt áp CŨ hơn 7 ngày không tính vào trần: lượt mới vẫn tự áp", trang_thai(root, "moi.md")["status"] == "applied", trang_thai(root, "moi.md"))

# trần đặt lại và tắt
root, deps = dung({"max_ap_tuan": 1})
for i, ngay in enumerate(("2026-10-10", "2026-10-11"), 1):
    de_xuat(root, f"d{i}.md", ngay)
    asyncio.run(factory.proposal_tick(deps))
check("chủ hạ trần xuống 1: lượt thứ hai đã chờ", trang_thai(root, "d1.md")["status"] == "applied" and trang_thai(root, "d2.md")["status"] == "cho_chu_duyet")
root, deps = dung({"max_ap_tuan": 0})
for i, ngay in enumerate(("2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13"), 1):
    de_xuat(root, f"d{i}.md", ngay)
    asyncio.run(factory.proposal_tick(deps))
check("chủ đặt 0 (không giới hạn): cả bốn lượt tự áp", all(trang_thai(root, f"d{i}.md")["status"] == "applied" for i in (1, 2, 3, 4)))
check("trần mặc định là 2 như chủ đã chốt", factory.load_factory_cfg(str(dung()[0]))["max_ap_tuan"] == 2)

print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g2_tran_tuan: tất cả pass")
