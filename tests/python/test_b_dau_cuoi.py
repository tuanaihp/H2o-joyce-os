"""Gate B (Joyce Harness): MỘT luồng từ lượt chạy thật qua agent tới canary, trong sandbox.

    python tests/run.py b_dau_cuoi      (không mạng, không model)

Luồng: đề xuất chỉ đổi hiển thị, qua cổng, vào nguồn, mở canary -> bot gắn agent trả lời khách (host ghi lượt, chụp revision từ file
agent THẬT đang chạy) -> chủ chấm từng lượt -> đủ bằng chứng thì nhân -> một nhánh khác: lượt rớt thì lật lại. Cũng kiểm: lượt chạy
trên bản CŨ không được tính cho bản mới, và hoàn tất chưa chấm không tính đạt.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import pathlib
import sys
import tempfile

STATE = pathlib.Path(tempfile.mkdtemp(prefix="joyce-bgate-state-"))
os.environ["JOYCE_STATE_DIR"] = str(STATE)
os.environ["BRAINS_DIR"] = str(pathlib.Path(tempfile.mkdtemp(prefix="joyce-bgate-brains-")))

import chatbot_runtime as CR  # noqa: E402
import chatbot_store  # noqa: E402
import factory  # noqa: E402
import factory_admin as fa  # noqa: E402
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
SLUG = "tro-ly-a"


class Kho:
    def list_tasks(self, root, include_archived=False, limit=400):
        return []


def dung():
    b = pathlib.Path(tempfile.mkdtemp(prefix="joyce-bgate-"))
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
    return roots, deps


def bot_tra_loi(roots, n):
    """n lượt bot gắn agent trả lời khách: dùng đúng hàm của runtime, đọc đúng file agent đang nằm trong brain nguồn."""
    CR._deps["brain_root"] = lambda brain: str(roots["nguon"])
    CR._deps["read_agent"] = lambda brain, slug: ({"type": "agent"}, "x")
    chatbot_store.get_bot = lambda bid: {"id": "bot1", "agent": {"slug": SLUG, "brain": "nguon"}, "brain": "nguon", "engine": "claude"}
    ids = []
    for i in range(n):
        rid = CR._so_mo("bot1", {"chat_id": f"c{i}"})
        CR._so_chot(rid, "completed")
        ids.append(rid)
    return ids


def canary_tick(deps):
    st = factory._load_state(deps)
    st["canaries"][0]["promote_at"] = 0
    factory._save_state(deps, st)
    return asyncio.run(factory.canary_tick(deps))


def cham(deps, ids, kq):
    return [fa.cham_luot(deps, r, kq, "đã đọc câu trả lời")[0] for r in ids]


# ---------------------------------------------------------------- nhánh 1: đạt thì nhân
factory.telemetry_ready = lambda *a, **k: True        # bước mở canary dựa trên quan sát được; phần đọc sổ thật có test riêng ở b02
roots, deps = dung()
# bản CŨ đã có người dùng trước khi đề xuất vào: lượt này mang revision của bản cũ
cu = bot_tra_loi(roots, 4)
asyncio.run(factory.proposal_tick(deps))
c = factory._load_state(deps)["canaries"][0]
check("(chuẩn bị) đề xuất hiển thị vào nguồn, canary mở, nguồn đang chạy bản mới", c["state"] == "canary" and (roots["nguon"] / REL).read_text(encoding="utf-8") == MOI)

moi = bot_tra_loi(roots, 20)
rv_cu, rv_moi = L.lay(cu[0])["agent_revision"], L.lay(moi[0])["agent_revision"]
check("lượt chạy trước và sau khi đổi mang revision KHÁC nhau, lượt sau khớp băm bản ứng viên của canary",
      rv_cu != rv_moi and rv_moi == c["candidate_hash"] == factory._sha256(MOI), (rv_cu[:8], rv_moi[:8], c["candidate_hash"][:8]))
check("hoàn tất 20 lượt nhưng chưa chấm: canary CHỜ, không nhân", canary_tick(deps)["cho_bang_chung"] == 1
      and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC)
check("chủ chấm 4 lượt của bản CŨ đạt: vẫn không đủ bằng chứng cho bản mới (bản cũ không tính)", cham(deps, cu, "pass") == [200] * 4
      and factory._canary_evidence(deps, factory._load_state(deps)["canaries"][0])["ok"] == 0)
check("chủ chấm 19 lượt bản mới đạt: còn thiếu 1, chưa nhân", cham(deps, moi[:19], "pass") == [200] * 19 and canary_tick(deps)["cho_bang_chung"] == 1
      and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC)
check("chấm nốt lượt thứ 20: đủ bằng chứng đã kiểm, NHÂN sang đích",
      cham(deps, moi[19:], "pass") == [200] and canary_tick(deps)["promoted"] == 1 and (roots["dich0"] / REL).read_text(encoding="utf-8") == MOI)
c = factory._load_state(deps)["canaries"][0]
check("canary lưu tử số và mẫu số, có receipt từng đích để khôi phục", c["state"] == "promoted" and c["evidence"]["ok"] == 20 and all(t.get("co_receipt") for t in c["targets"]), c.get("evidence"))
tid = fa.trang_thai(deps)["canaries"][0]["dich"][0]["target_id"]
h, kq = fa.thuc_hien(deps, "restore", canary_id=c["id"], target_id=tid, expected_revision=factory._sha256(MOI), action_id="b-khoi-phuc", reason="thử đầu cuối")
check("chủ khôi phục đích về đúng byte cũ", h == 200 and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC, (h, kq))

sg1 = factory.stages_snapshot(deps)
check("sổ đăng ký: sau khi nhân, lượt mới nhất chạy đúng nội dung file hiện tại (1 trợ lý, 0 bản đã đổi)",
      sg1["dang_chay"] == {"theo_doi": 1, "dung_ban_hien_tai": 1, "ban_da_doi": 0}, sg1["dang_chay"])

# ---------------------------------------------------------------- nhánh 2: có lượt rớt thì lật lại
roots, deps = dung()
asyncio.run(factory.proposal_tick(deps))
moi = bot_tra_loi(roots, 6)
cham(deps, moi[:5], "pass")
check("chủ chấm 1 lượt RỚT", fa.cham_luot(deps, moi[5], "fail", "trả lời sai chính sách")[0] == 200)
rep = canary_tick(deps)
check("phát hiện lỗi đã kiểm: LẬT LẠI nguồn về bản cũ, không nhân, báo trạng thái reverted",
      rep["reverted"] == 1 and (roots["nguon"] / REL).read_text(encoding="utf-8") == GOC and (roots["dich0"] / REL).read_text(encoding="utf-8") == GOC
      and factory._load_state(deps)["canaries"][0]["state"] == "reverted")

sg2 = factory.stages_snapshot(deps)
check("sổ đăng ký: sau khi LẬT LẠI, file đã về bản cũ mà lượt chạy cuối là trên bản mới: báo 'bản đã đổi', không báo khớp",
      sg2["dang_chay"]["ban_da_doi"] == 1 and sg2["dang_chay"]["dung_ban_hien_tai"] == 0, sg2["dang_chay"])

# ---------------------------------------------------------------- Sơ đồ phản ánh đúng
sg = factory.stages_snapshot(deps)
check("Sơ đồ thấy lượt chạy thật đã ghi, có lượt đạt, có lượt gián đoạn bằng 0 (không giả vờ)",
      sg["luot_chay"]["logical"] >= 6 and sg["luot_chay"]["verified_pass"] >= 5 and sg["luot_chay"]["gian_doan"] == 0, sg["luot_chay"])

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b_dau_cuoi: tất cả pass")
