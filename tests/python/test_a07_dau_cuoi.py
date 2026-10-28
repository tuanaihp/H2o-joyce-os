"""A07.2 (Joyce Harness, gói A): chạy MỘT đường đầy đủ trong sandbox, từ đề xuất tới khôi phục sau crash.

    python tests/run.py a07_dau_cuoi      (không mạng, không model; mọi file nằm trong thư mục tạm)

Kịch bản (ba brain: nguồn + hai đích, hai file mục tiêu):
  1. Hai đề xuất cùng lượt: một đổi HÀNH VI (thân bài) và một chỉ đổi hiển thị có bộ eval đạt.
  2. Đề xuất đổi hành vi KHÔNG tự áp, chờ chủ. Đề xuất hiển thị qua cổng eval và vào nguồn, mở canary.
  3. Đích 0 đúng baseline chung thì được nhân; đích 1 có biến thể riêng từ trước thì thành override, KHÔNG bị ghi đè.
  4. Tiến trình chết SAU khi ghi đích 0, TRƯỚC khi chốt nhật ký và lưu state. Khởi động lại: đối soát hoàn tất nhật ký.
  5. Giao diện quản trị thấy đúng trạng thái; chủ khôi phục đích 0 về đúng byte cũ; bấm lặp lại không làm hai lần.
  6. Cờ tạm dừng chặn đề xuất mới nhưng không làm mất đề xuất.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import time

STATE = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a07-state-"))
os.environ["JOYCE_STATE_DIR"] = str(STATE)
os.environ["BRAINS_DIR"] = str(pathlib.Path(tempfile.mkdtemp(prefix="joyce-a07-brains-")))

import factory  # noqa: E402
import _so_luot_chay  # noqa: E402
_so_luot_chay.cai_dat(factory)
import factory_admin as fa  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


factory.telemetry_ready = lambda *a, **k: True      # có đủ lượt chạy thật (D1); phần chưa có telemetry đã có test riêng ở A01

THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
REL_A = "agents/tro-ly-a.md"       # đề xuất chỉ đổi hiển thị (ngày cập nhật)
REL_B = "agents/tro-ly-b.md"       # đề xuất đổi thân bài, tức hành vi


def goc(ten):
    return f"---\ntype: agent\nname: {ten}\nupdated: 2026-10-01\n---\n" + THAN


A_CU = goc("Trợ lý A")
A_MOI = A_CU.replace("2026-10-01", "2026-10-28")
B_CU = goc("Trợ lý B")
B_MOI = B_CU + "\nLuôn trả lời bằng đúng một câu.\n"
BIEN_THE = A_CU + "\nPhòng này có quy ước riêng của chủ.\n"


def de_xuat(rel, ban_moi, tieu_de):
    return ("---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + rel + "\n---\n# " + tieu_de
            + "\n\n## Bản nháp đầy đủ\n\n```markdown\n" + ban_moi + "```\n")


class Kho:
    def __init__(self):
        self.t = []

    def list_tasks(self, root, include_archived=False, limit=400):
        return list(self.t)


b = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a07-"))
roots = {"nguon": b / "nguon", "dich0": b / "dich0", "dich1": b / "dich1"}
for r in roots.values():
    (r / "agents").mkdir(parents=True)
    (r / "Joyce" / "proposals").mkdir(parents=True)
    (r / REL_A).write_text(A_CU, encoding="utf-8", newline="")
    (r / REL_B).write_text(B_CU, encoding="utf-8", newline="")
(roots["dich1"] / REL_A).write_text(BIEN_THE, encoding="utf-8", newline="")      # biến thể riêng có từ TRƯỚC khi có đề xuất
(roots["nguon"] / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
(roots["nguon"] / "Joyce" / "evals").mkdir()
(roots["nguon"] / "Joyce" / "evals" / "tro-ly-a.json").write_text(
    json.dumps({"cases": [{"name": "còn mục Vai trò", "check": "contains", "value": "Vai trò"}]}, ensure_ascii=False), encoding="utf-8")
PROP = roots["nguon"] / "Joyce" / "proposals"
(PROP / "2026-10-28-hien-thi.md").write_text(de_xuat(REL_A, A_MOI, "Đổi ngày cập nhật"), encoding="utf-8")
(PROP / "2026-10-28-hanh-vi.md").write_text(de_xuat(REL_B, B_MOI, "Thêm quy tắc trả lời"), encoding="utf-8")

hop = []


async def inbox(text, **kw):
    hop.append(text)


deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=Kho(), enqueue=None, loops=None,
                           workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                           incidents_list=lambda bb, n: [], settings_get=lambda: {}, state_dir=STATE)


def doc(ten, rel):
    return (roots[ten] / rel).read_text(encoding="utf-8")


def trang_thai_de_xuat(ten_file):
    fm, _ = factory._proposal_front((PROP / ten_file).read_text(encoding="utf-8"))
    return (fm or {}).get("status")


# ============================================================
# 1-2. Phân loại, eval, chờ chủ, áp cái được phép
# ============================================================
asyncio.run(factory.proposal_tick(deps))
check("đề xuất đổi HÀNH VI không tự áp: nguồn giữ nguyên, trạng thái chờ chủ",
      doc("nguon", REL_B) == B_CU and trang_thai_de_xuat("2026-10-28-hanh-vi.md") == "cho_chu_duyet", trang_thai_de_xuat("2026-10-28-hanh-vi.md"))
check("chủ nhận được thông báo nói rõ lý do chờ (đổi hành vi)", any("hành vi" in t for t in hop), hop)
check("đề xuất chỉ đổi HIỂN THỊ, qua cổng eval, vào nguồn", doc("nguon", REL_A) == A_MOI, doc("nguon", REL_A)[:120])
st = factory._load_state(deps)
check("mở đúng một canary cho đề xuất hiển thị",
      len(st["canaries"]) == 1 and st["canaries"][0]["target"] == REL_A and st["canaries"][0]["state"] == "canary",
      [(c.get("target"), c.get("state")) for c in st["canaries"]])
fm_hv, _ = factory._proposal_front((PROP / "2026-10-28-hien-thi.md").read_text(encoding="utf-8"))
check("kết quả eval được gắn vào đề xuất, kèm băm bản nháp và băm file eval (không dùng lại cho bản khác)",
      fm_hv.get("eval_candidate_hash") == factory._sha256(A_MOI) and len(str(fm_hv.get("eval_revision"))) == 64
      and fm_hv.get("eval_hanh_vi") == "chua_co", fm_hv)
check("đích chưa bị đụng khi canary mới mở", doc("dich0", REL_A) == A_CU and doc("dich1", REL_A) == BIEN_THE)

# ============================================================
# 3-4. Đủ lượt chạy thật, nhân sang đích; tiến trình chết giữa chừng
# ============================================================
deps.store.t = [{"id": f"t{i}", "status": "done", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1, "updated_at": time.time() + 2}
                for i in range(25)]
st = factory._load_state(deps)
st["canaries"][0]["promote_at"] = 0
factory._save_state(deps, st)


class Chet(BaseException):
    pass


ghi_goc = factory._ghi_dich
lan = {"n": 0}


def ghi_roi_chet(deps_, goc_, dich, text, **kw):
    """Đích đầu tiên được ghi xong rồi tiến trình 'chết' trước khi chốt nhật ký và lưu state."""
    lan["n"] += 1
    if lan["n"] == 1:
        def hook(buoc):
            if buoc == "sau_ghi":
                raise Chet()
        kw["dung_tai"] = hook
    return ghi_goc(deps_, goc_, dich, text, **kw)


factory._ghi_dich = ghi_roi_chet
try:
    asyncio.run(factory.canary_tick(deps))
    chet = False
except Chet:
    chet = True
finally:
    factory._ghi_dich = ghi_goc
check("(mô phỏng) tiến trình chết SAU khi ghi một đích", chet)
da_ghi = [t for t in ("dich0", "dich1") if doc(t, REL_A) == A_MOI]
check("lúc chết có đúng một đích đã mang bản mới, đích có biến thể riêng không bị đụng",
      da_ghi == ["dich0"] and doc("dich1", REL_A) == BIEN_THE, da_ghi)
check("state trên đĩa chưa kịp ghi nhận đích đó (đúng cảnh crash)",
      not any(t.get("state") == "promoted" for t in factory._load_state(deps)["canaries"][0]["targets"]))

# khởi động lại: đối soát nhật ký rồi chạy tiếp
asyncio.run(factory.canary_tick(deps))
c = factory._load_state(deps)["canaries"][0]
tgs = {pathlib.Path(t["root"]).name: t for t in c["targets"]}
check("sau khởi động lại: đích 0 promoted có receipt đã chốt (không ghi hai lần, không mất đường khôi phục)",
      tgs["dich0"]["state"] == "promoted" and tgs["dich0"]["co_receipt"] and doc("dich0", REL_A) == A_MOI, tgs["dich0"])
check("đích 1 có biến thể riêng từ trước: override, nội dung của chủ còn nguyên",
      tgs["dich1"]["state"] == "override" and doc("dich1", REL_A) == BIEN_THE, tgs["dich1"])
check("canary không bị đánh dấu xong khi còn đích đang chờ chủ", c["state"] != "promoted", c["state"])

# ============================================================
# 5. Giao diện quản trị và khôi phục
# ============================================================
ts = fa.trang_thai(deps)
cs = ts["canaries"][0]
dich = {d["brain"]: d for d in cs["dich"]}
check("trạng thái quản trị: đích 0 khôi phục được, đích 1 override không có nút khôi phục",
      dich["dich0"]["co_the_khoi_phuc"] and not dich["dich1"]["co_the_khoi_phuc"], dich)
check("trạng thái không lộ đường dẫn tuyệt đối",
      str(b) not in json.dumps(ts, ensure_ascii=False) and str(STATE) not in json.dumps(ts, ensure_ascii=False))
http, kq = fa.thuc_hien(deps, "restore", canary_id=c["id"], target_id=dich["dich0"]["target_id"],
                        expected_revision=factory._sha256(A_MOI), action_id="e2e-khoi-phuc", reason="thử đầu cuối")
check("chủ khôi phục đích 0: về ĐÚNG byte bản cũ", http == 200 and kq.get("ok") and doc("dich0", REL_A) == A_CU, (http, kq))
http2, kq2 = fa.thuc_hien(deps, "restore", canary_id=c["id"], target_id=dich["dich0"]["target_id"],
                          expected_revision=factory._sha256(A_MOI), action_id="e2e-khoi-phuc", reason="thử đầu cuối")
check("bấm lặp lại cùng action_id: trả kết quả cũ, không khôi phục lần hai", http2 == 200 and kq2.get("lap_lai") is True and doc("dich0", REL_A) == A_CU)
check("đích 1 (biến thể của chủ) và nguồn không bị khôi phục nhầm", doc("dich1", REL_A) == BIEN_THE and doc("nguon", REL_A) == A_MOI)

# ---------------- số liệu cho Sơ đồ phản ánh đúng việc vừa xảy ra
sg = factory.stages_snapshot(deps)
check("Sơ đồ: cổng 7 ngày đếm đúng (1 tự áp, 1 chờ vì đổi hành vi)", sg["cong7"]["tu_ap"] == 1 and sg["cong7"]["hanh_vi"] == 1, sg["cong7"])
check("Sơ đồ: bộ ghi file thấy các lần ghi đã chốt và không còn nhật ký dở sau khi đối soát", sg["nhat_ky"]["da_chot"] >= 2 and sg["nhat_ky"]["dang_do"] == 0, sg["nhat_ky"])

# ============================================================
# 6. Tạm dừng
# ============================================================
(PROP / "2026-10-28-moi.md").write_text(de_xuat(REL_A, A_MOI.replace("2026-10-28", "2026-10-29"), "Đổi ngày lần nữa"), encoding="utf-8")
http, kq = fa.thuc_hien(deps, "pause", on=True, action_id="e2e-tam-dung", reason="thử")
check("chủ bật tạm dừng", http == 200 and kq.get("ok"), (http, kq))
asyncio.run(factory.proposal_tick(deps))
check("đang tạm dừng: đề xuất mới KHÔNG được áp và KHÔNG mất (vẫn pending)",
      trang_thai_de_xuat("2026-10-28-moi.md") == "pending" and doc("nguon", REL_A) == A_MOI, trang_thai_de_xuat("2026-10-28-moi.md"))

print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_a07_dau_cuoi: tất cả pass")
