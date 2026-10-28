"""B02 (Joyce Harness, gói B): canary đọc bằng chứng từ sổ lượt chạy do host ghi, không từ Kanban.

    python tests/run.py b02_bang_chung_so      (không mạng, không model; mọi file ở thư mục tạm)

Ca chính: `done`/hoàn tất chưa kiểm KHÔNG phải đạt; chỉ lượt đã kiểm đạt, đúng agent, đúng brain, đúng revision của bản ứng viên và sau
lúc áp mới tính; retry của một việc là một bằng chứng; lỗi hệ thống không đổ cho agent; đủ 20 lượt đạt thì nhân, thiếu thì chờ rồi
hết hạn, có lượt rớt đã kiểm thì lật lại.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import time

STATE = pathlib.Path(tempfile.mkdtemp(prefix="joyce-b02-state-"))
os.environ["JOYCE_STATE_DIR"] = str(STATE)
os.environ["BRAINS_DIR"] = str(pathlib.Path(tempfile.mkdtemp(prefix="joyce-b02-brains-")))

import factory  # noqa: E402
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nupdated: 2026-10-01\n---\n" + THAN
MOI = GOC.replace("2026-10-01", "2026-10-28")
REL = "agents/tro-ly-a.md"
CAND = factory._sha256(MOI)


class Kho:
    def list_tasks(self, root, include_archived=False, limit=400):
        return []


def dung():
    b = pathlib.Path(tempfile.mkdtemp(prefix="joyce-b02-"))
    roots = {"nguon": b / "nguon", "dich0": b / "dich0"}
    for r in roots.values():
        (r / "agents").mkdir(parents=True)
        (r / "Joyce" / "proposals").mkdir(parents=True)
        (r / REL).write_text(GOC, encoding="utf-8", newline="")
    (roots["nguon"] / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
    (roots["nguon"] / "Joyce" / "proposals" / "2026-10-28-de-xuat.md").write_text(
        "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + REL + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + MOI + "```\n",
        encoding="utf-8")

    async def inbox(text, **kw):
        pass

    deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=Kho(), enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda bb, n: [], settings_get=lambda: {}, state_dir=STATE)
    for p in STATE.glob("factory-state.json"):
        p.unlink()
    L._db().execute("DELETE FROM agent_runs")
    asyncio.run(factory.proposal_tick(deps))
    return roots, deps


def c0(deps):
    return factory._load_state(deps)["canaries"][0]


def ghi(c, n, ket_qua="verified_pass", *, rev=None, brain=None, agent=None, luc=None, status="completed", block="", prefix="r"):
    ids = []
    for i in range(n):
        rid = f"{prefix}-{os.urandom(4).hex()}"
        L.bat_dau(brain_id=brain or pathlib.Path(c["root"]).name, agent_id=agent or c["slug"], entrypoint="task", run_id=rid,
                  logical_execution_id=rid, revision={"agent_revision": CAND if rev is None else rev},
                  now=luc if luc is not None else float(c["applied_at"]) + 10 + i)
        L.ket_thuc(rid, status, block_kind=block, verification=ket_qua)
        ids.append(rid)
    return ids


def tick(deps, c=None, sau_gio=0):
    st = factory._load_state(deps)
    st["canaries"][0]["promote_at"] = 0
    if sau_gio:
        st["canaries"][0]["applied_at"] = float(st["canaries"][0]["applied_at"]) - sau_gio
    factory._save_state(deps, st)
    return asyncio.run(factory.canary_tick(deps))


factory.telemetry_ready = lambda *a, **k: True      # phần quyết định mở canary có test riêng ở dưới

# ============================================================
# 1. Ngữ nghĩa của bằng chứng
# ============================================================
roots, deps = dung()
c = c0(deps)
check("(chuẩn bị) canary mở cho đúng file, nguồn mang bản mới, có băm đầy đủ của ứng viên", c["state"] == "canary" and c["candidate_hash"] == CAND, c)
ev = factory._canary_evidence(deps, c)
check("chưa có lượt nào: không có bằng chứng, nguồn ghi rõ là sổ lượt chạy", ev["tasks"] == 0 and ev["ok"] == 0 and ev["nguon"] == "run_ledger", ev)

ghi(c, 7, ket_qua="unverified")
ev = factory._canary_evidence(deps, c)
check("7 lượt HOÀN TẤT nhưng chưa kiểm chứng: KHÔNG tính đạt (chưa_kiểm = 7, ok = 0)", ev["ok"] == 0 and ev["chua_kiem"] == 7 and ev["tasks"] == 0, ev)

ghi(c, 3)
check("3 lượt đã kiểm đạt đúng revision: ok = 3", factory._canary_evidence(deps, c)["ok"] == 3)
ghi(c, 4, rev="b" * 64)
check("lượt của BẢN KHÁC (revision lệch) bị loại khỏi bằng chứng", factory._canary_evidence(deps, c)["ok"] == 3)
ghi(c, 4, brain="nguon-khac")
ghi(c, 4, agent="tro-ly-khac")
check("lượt của brain khác hoặc agent khác bị loại", factory._canary_evidence(deps, c)["ok"] == 3)
ghi(c, 4, luc=float(c["applied_at"]) - 100)
check("lượt bắt đầu TRƯỚC lúc áp bị loại (chạy trên bản cũ)", factory._canary_evidence(deps, c)["ok"] == 3)
ghi(c, 2, rev="")
ev = factory._canary_evidence(deps, c)
check("lượt không đọc được revision bị loại và đếm riêng (không gán bừa cho bản nào)", ev["ok"] == 3 and ev["khong_ro_revision"] == 2, ev)

# retry: một việc lỗi hệ thống rồi chạy lại đạt = MỘT bằng chứng đạt
a = "retry-1"
L.bat_dau(brain_id="nguon", agent_id=c["slug"], entrypoint="task", run_id="ra", logical_execution_id=a, attempt_id="1",
          revision={"agent_revision": CAND}, now=float(c["applied_at"]) + 50)
L.ket_thuc("ra", "failed", block_kind="system")
L.bat_dau(brain_id="nguon", agent_id=c["slug"], entrypoint="task", run_id="rb", logical_execution_id=a, attempt_id="2",
          revision={"agent_revision": CAND}, now=float(c["applied_at"]) + 51)
L.ket_thuc("rb", "completed", verification="verified_pass")
ev = factory._canary_evidence(deps, c)
check("việc lỗi hệ thống rồi chạy lại đạt: tính MỘT lần đạt (ok = 4), lần thử cũ nằm ở thu_lai", ev["ok"] == 4 and ev["thu_lai"] == 1 and ev["bad"] == 0, ev)

ghi(c, 3, status="failed", ket_qua="unverified", block="system", prefix="sys")
ev = factory._canary_evidence(deps, c)
check("lỗi hệ thống KHÔNG bị đổ cho agent: bad vẫn 0, ghi ở loi_he_thong", ev["bad"] == 0 and ev["loi_he_thong"] == 3 and ev["bad_ids"] == [], ev)

ghi(c, 2, status="needs_approval", ket_qua="unverified", block="waiting", prefix="wait")
check("chờ duyệt không phải lỗi agent và không phải đạt", factory._canary_evidence(deps, c)["bad"] == 0 and factory._canary_evidence(deps, c)["doi_duyet"] == 2)

xau = ghi(c, 1, ket_qua="verified_fail", status="failed", block="business", prefix="bad")
ev = factory._canary_evidence(deps, c)
check("lượt đã kiểm là RỚT: bad = 1 và có id để truy", ev["bad"] == 1 and ev["bad_ids"] == xau, ev)

# canary cũ chỉ có băm ngắn: suy ra từ nội dung file hiện tại nếu vẫn khớp
cu = dict(c)
cu.pop("candidate_hash")
check("canary cũ chỉ có băm ngắn: suy ra bản ứng viên từ file hiện tại, vẫn đọc được bằng chứng", factory._canary_evidence(deps, cu)["ok"] == 4)

# ============================================================
# 2. Quyết định nhân / chờ / hết hạn / lật lại
# ============================================================
roots, deps = dung()
c = c0(deps)
ghi(c, 19)
tick(deps)
c = c0(deps)
check("19 lượt đạt (thiếu 1): CHỜ, chưa nhân", c["state"] == "canary" and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC, c["state"])

roots, deps = dung()
c = c0(deps)
ghi(c, 40, ket_qua="unverified")
rep = tick(deps)
check("40 lượt hoàn tất mà CHƯA ai kiểm: không đủ bằng chứng, KHÔNG nhân (hoàn tất không phải đạt)",
      c0(deps)["state"] == "canary" and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC and rep["cho_bang_chung"] == 1, rep)
tick(deps, sau_gio=15 * 86400)
check("quá 14 ngày vẫn thiếu bằng chứng đã kiểm: HẾT HẠN, không tự nhân, bản mới vẫn ở nguồn", c0(deps)["state"] == "het_han"
      and (roots["nguon"] / REL).read_text(encoding="utf-8") == MOI and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC)

roots, deps = dung()
c = c0(deps)
ghi(c, 20)
tick(deps)
c = c0(deps)
check("đủ 20 lượt đã kiểm đạt, không rớt: NHÂN sang đích", c["state"] == "promoted" and (roots["dich0"] / REL).read_text(encoding="utf-8") == MOI, c["state"])
check("kết quả canary lưu tử số và mẫu số bằng chứng", c["evidence"]["ok"] == 20 and c["evidence"]["tasks"] == 20 and c["evidence"]["nguon"] == "run_ledger", c.get("evidence"))

roots, deps = dung()
c = c0(deps)
ghi(c, 25)
ghi(c, 1, ket_qua="verified_fail", status="failed", block="business", prefix="bad")
tick(deps)
check("25 lượt đạt nhưng CÓ MỘT lượt đã kiểm là rớt: lật lại, không nhân (rớt vẫn nằm trong mẫu, không loại để đủ số)",
      c0(deps)["state"] == "reverted" and (roots["nguon"] / REL).read_text(encoding="utf-8") == GOC
      and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC, c0(deps)["state"])

# ============================================================
# 3. telemetry_ready đọc sổ thật
# ============================================================
del factory.telemetry_ready
import importlib  # noqa: E402
importlib.reload(factory)       # lấy lại hàm thật sau khi đã monkeypatch ở trên
deps2 = None
L._db().execute("DELETE FROM agent_runs")


def luot(n, brain="nguon", agent="tro-ly-a", rev="a" * 64, luc=None):
    for i in range(n):
        rid = os.urandom(6).hex()
        L.bat_dau(brain_id=brain, agent_id=agent, entrypoint="bot", run_id=rid, revision={"agent_revision": rev},
                  now=time.time() - 60 if luc is None else luc)
        L.ket_thuc(rid, "completed")


check("chưa có lượt nào: telemetry_ready = False", factory.telemetry_ready(deps2, "nguon", REL) is False)
luot(4)
check("4 lượt (dưới ngưỡng 5): False", factory.telemetry_ready(deps2, "nguon", REL) is False)
luot(1)
check("5 lượt có revision trong cửa sổ: True", factory.telemetry_ready(deps2, "nguon", REL) is True)
check("brain khác không thừa hưởng", factory.telemetry_ready(deps2, "dich0", REL) is False)
check("file không phải agent (skill, workflow) thì không mở", factory.telemetry_ready(deps2, "nguon", "skills/x/SKILL.md") is False
      and factory.telemetry_ready(deps2, "nguon", "") is False)
L._db().execute("DELETE FROM agent_runs")
luot(8, rev="")
check("lượt không đọc được revision không tính vào độ quan sát được", factory.telemetry_ready(deps2, "nguon", REL) is False)
L._db().execute("DELETE FROM agent_runs")
luot(8, luc=time.time() - 40 * 86400)
check("lượt quá cũ (ngoài cửa sổ 30 ngày) không tính", factory.telemetry_ready(deps2, "nguon", REL) is False)

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b02_bang_chung_so: tất cả pass")
