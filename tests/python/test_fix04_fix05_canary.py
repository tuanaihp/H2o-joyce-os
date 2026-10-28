"""FIX-04 và FIX-05 (Joyce Harness G1, JHA-04, JHA-05): canary không ghi đè bản sửa riêng, không nhân khi chưa có bằng chứng.

    python tests/run.py fix04_fix05_canary      (không mạng, không model; mọi file nằm trong thư mục tạm)

FIX-04, theo từng ĐÍCH (mỗi brain nhận file chung là một đích):
- bản trước ghi đè mọi đích nếu "cùng tên file", kể cả đích chủ đã sửa tay sau lúc áp, và báo "đã nhân" kể cả khi
  chỉ một phần thành công. Nay: chụp hash từng đích lúc áp, so-rồi-ghi (CAS), sao lưu từng đích, bỏ qua đích xung đột,
  ghi trạng thái TỪNG đích ngay khi xong để process chết giữa chừng chạy lại không làm lại và không đè.

FIX-05, bằng chứng:
- bản trước nhân ra khi hết giờ dù không có việc nào chạy, và tìm slug trong tiêu đề/lý do để nhận lỗi. Nay: cần đủ
  thời gian VÀ đủ số việc đã chạy trên bản ứng viên (gắn qua khoá agent, không qua chữ), lỗi dừng canary ngay.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import pathlib
import sys
import tempfile
import time

import factory  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


NOW = time.time()
# A01 (1.3.42): D1 chặn canary khi chưa có telemetry, và D3 chặn thay đổi hành vi. Test này thử RIÊNG logic canary nên bật
# telemetry giả có chủ ý bằng monkeypatch, và dùng bản nháp chỉ đổi `updated:` (hiển thị thuần) để qua cổng phân loại.
factory.telemetry_ready = lambda *a, **k: True
THAN = "## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng thu. " * 3 + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nrole: Thu\nupdated: 2026-10-01\n---\n" + THAN
NHAP = "---\ntype: agent\nname: Trợ lý A\nrole: Thu\nupdated: 2026-10-28\n---\n" + THAN
RIENG = GOC + "\nPhòng này tự thêm một dòng riêng.\n"


class Kho:
    """Kho việc giả: list_tasks theo gốc brain."""

    def __init__(self):
        self.tasks = {}

    def them(self, root, **t):
        self.tasks.setdefault(str(root), []).append(t)

    def list_tasks(self, root, include_archived=False, limit=400):
        return list(self.tasks.get(str(root), []))


def viec(i, status="done", slug="tro-ly-a", tao=None, cap_nhat=None, **kw):
    return {"id": f"t{i}", "title": f"việc {i}", "status": status, "idempotency_key": f"agent:A1:{slug}",
            "created_at": tao if tao is not None else time.time() + 1, "updated_at": cap_nhat if cap_nhat is not None else time.time() + 2,
            "block_reason": "", **kw}


def dung(so_dich=2, cfg=None):
    """Dựng một canary thật: brain nguồn + `so_dich` brain nhận, qua proposal_tick (đường thật)."""
    base = pathlib.Path(tempfile.mkdtemp(prefix="joyce-fix45-"))
    roots = {"nguon": base / "nguon"}
    for i in range(so_dich):
        roots[f"dich{i}"] = base / f"dich{i}"
    for r in roots.values():
        (r / "agents").mkdir(parents=True)
        (r / "Joyce" / "proposals").mkdir(parents=True)
        (r / "agents" / "tro-ly-a.md").write_text(GOC, encoding="utf-8")
    (roots["nguon"] / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True, **(cfg or {})}), encoding="utf-8")
    (roots["nguon"] / "Joyce" / "proposals" / "2026-10-28-tro-ly-a.md").write_text(
        "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: agents/tro-ly-a.md\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + NHAP + "```\n", encoding="utf-8")
    kho, hop = Kho(), []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=kho, enqueue=None, loops=None,
                               workflows_dir=lambda r: pathlib.Path(r) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=base)
    rep = asyncio.run(factory.proposal_tick(deps))
    assert rep["canary"] == 1, rep
    return roots, kho, hop, deps


def trang_thai(deps):
    return factory._load_state(deps)["canaries"][0]


def het_gio(deps, **them):
    st = factory._load_state(deps)
    c = st["canaries"][0]
    c["promote_at"] = 0
    c.update(them)
    factory._save_state(deps, st)


def tick(deps):
    return asyncio.run(factory.canary_tick(deps))


def doc(roots, ten):
    return (roots[ten] / "agents" / "tro-ly-a.md").read_text(encoding="utf-8")


def du_bang_chung(kho, roots, n=20, **kw):
    for i in range(n):
        kho.them(roots["nguon"], **viec(i, **kw))


# ============================================================
# FIX-05: bằng chứng trước khi nhân
# ============================================================
roots, kho, hop, deps = dung()
het_gio(deps)
rep = tick(deps)
check("ZERO traffic: hết giờ mà không có việc nào chạy thì KHÔNG nhân", rep["promoted"] == 0 and doc(roots, "dich0") == GOC and doc(roots, "dich1") == GOC, rep)
check("zero traffic: canary còn chờ, ghi rõ thiếu bằng chứng", trang_thai(deps)["state"] == "canary" and rep.get("cho_bang_chung") == 1, (rep, trang_thai(deps)))

kho.them(roots["nguon"], **viec(1))
rep = tick(deps)
check("mới 1 việc (chưa đủ 20): vẫn KHÔNG nhân", rep["promoted"] == 0 and doc(roots, "dich0") == GOC, rep)

roots, kho, hop, deps = dung()
du_bang_chung(kho, roots, 19)
het_gio(deps)
check("19 việc: chưa đủ ngưỡng 20", tick(deps)["promoted"] == 0)
kho.them(roots["nguon"], **viec(99))
rep = tick(deps)
c = trang_thai(deps)
check("đủ 20 việc đã kiểm + đủ giờ + không lỗi: nhân", rep["promoted"] == 1 and c["state"] == "promoted" and doc(roots, "dich0") == NHAP + "" or doc(roots, "dich0").strip() == NHAP.strip(), (rep, c))
check("bằng chứng được ghi vào canary (số việc, số đạt, số lỗi)", c.get("evidence", {}).get("tasks") == 20 and c["evidence"].get("bad") == 0, c.get("evidence"))

roots, kho, hop, deps = dung()
for i in range(25):    # việc chạy TRƯỚC khi bản ứng viên được áp: không phải bằng chứng của nó
    kho.them(roots["nguon"], **viec(i, tao=NOW - 99999, cap_nhat=NOW - 99990))
het_gio(deps)
check("việc chạy trước lúc áp bản ứng viên KHÔNG được tính", tick(deps)["promoted"] == 0 and doc(roots, "dich0") == GOC)

roots, kho, hop, deps = dung()
for i in range(25):    # việc của agent KHÁC, hoặc việc không gắn agent nào
    kho.them(roots["nguon"], **viec(i, slug="giam-dinh-ux"))
kho.them(roots["nguon"], id="x", title="tro-ly-a làm gì đó", status="done", created_at=time.time() + 1, updated_at=time.time() + 2)
het_gio(deps)
check("việc của agent khác hoặc chỉ NHẮC slug trong tiêu đề không phải bằng chứng", tick(deps)["promoted"] == 0 and doc(roots, "dich0") == GOC)

roots, kho, hop, deps = dung(cfg={"canary_min_tasks": 3})
du_bang_chung(kho, roots, 3)
het_gio(deps)
check("ngưỡng chỉnh được theo brain (canary_min_tasks)", tick(deps)["promoted"] == 1)

# Lỗi: gắn theo khoá agent, KHÔNG theo chữ trong tiêu đề/lý do
roots, kho, hop, deps = dung()
kho.them(roots["nguon"], **viec(1, status="blocked", block_reason="lỗi quyền, không nói gì về tên trợ lý"))
rep = tick(deps)       # CHƯA hết giờ: lỗi vẫn phải dừng ngay
check("lỗi (việc blocked gắn đúng agent, KHÔNG nhắc slug) dừng canary NGAY dù chưa hết giờ",
      rep["reverted"] == 1 and doc(roots, "nguon") == GOC and doc(roots, "dich0") == GOC and trang_thai(deps)["state"] == "reverted", (rep, trang_thai(deps)))
check("lỗi được báo cho chủ kèm lý do", any("lật lại" in t for t in hop), hop)

roots, kho, hop, deps = dung()
kho.them(roots["nguon"], id="n1", title="trợ lý tro-ly-a bị lỗi", status="blocked", block_reason="tro-ly-a sai", created_at=time.time() + 1, updated_at=time.time() + 2)
rep = tick(deps)
check("việc blocked chỉ NHẮC slug (không gắn agent) không làm canary dừng nhầm", rep["reverted"] == 0 and trang_thai(deps)["state"] == "canary", rep)

roots, kho, hop, deps = dung()
kho.them(roots["nguon"], **viec(1, status="blocked", tao=NOW - 99999, cap_nhat=NOW - 99990))
check("lỗi của việc chạy TRƯỚC bản ứng viên không làm canary dừng", tick(deps)["reverted"] == 0)

# ============================================================
# FIX-04: từng đích
# ============================================================
def dich_xong(roots, kho, deps, n=20):
    du_bang_chung(kho, roots, n)
    het_gio(deps)


roots, kho, hop, deps = dung()
(roots["dich1"] / "agents" / "tro-ly-a.md").write_text(RIENG, encoding="utf-8")      # chủ sửa tay SAU lúc áp
dich_xong(roots, kho, deps)
rep = tick(deps)
c = trang_thai(deps)
check("đích bị chủ sửa tay sau lúc áp: GIỮ NGUYÊN bản riêng, không ghi đè", doc(roots, "dich1") == RIENG, doc(roots, "dich1")[:80])
check("đích còn nguyên bản gốc thì được nhân", doc(roots, "dich0").strip() == NHAP.strip())
check("kết quả KHÔNG báo 'toàn bộ thành công': trạng thái partial, nêu đúng đích xung đột",
      c["state"] == "partial" and rep["promoted"] == 0 and rep.get("partial") == 1
      and [t["state"] for t in c["targets"] if str(roots["dich1"]) == t["root"]] == ["conflict"], (rep, c))
check("thông báo nói rõ số đích nhân được và số đích giữ bản riêng", any("1/2" in t and "bản riêng" in t for t in hop), hop)

roots, kho, hop, deps = dung()
(roots["dich0"] / "agents" / "tro-ly-a.md").unlink()                                       # đích bị xoá
dich_xong(roots, kho, deps)
tick(deps)
c = trang_thai(deps)
check("đích bị xoá: KHÔNG tạo lại, ghi nhận missing", not (roots["dich0"] / "agents" / "tro-ly-a.md").exists()
      and [t["state"] for t in c["targets"] if str(roots["dich0"]) == t["root"]] == ["missing"], c)
check("đích khác vẫn nhân bình thường", doc(roots, "dich1").strip() == NHAP.strip())

roots, kho, hop, deps = dung()
dich_xong(roots, kho, deps)
tick(deps)
sao_luu = list((roots["dich0"] / "Joyce" / "proposals" / ".backup").glob("*.bak"))
check("mỗi đích bị ghi đều có bản sao lưu nội dung cũ", len(sao_luu) == 1 and sao_luu[0].read_text(encoding="utf-8") == GOC, sao_luu)
check("canary xong sạch: promoted, mọi đích promoted", trang_thai(deps)["state"] == "promoted"
      and all(t["state"] == "promoted" for t in trang_thai(deps)["targets"]))

# Chỉ một đích ghi lỗi
roots, kho, hop, deps = dung()
dich_xong(roots, kho, deps)
goc_ghi = factory._ghi_dich      # A05: cổng ghi chung của triển khai (trước đó là _ghi_nguyen_tu)


def ghi_hong_mot_dich(deps_, goc, dich, text, **kw):
    if str(roots["dich0"]) in str(dich):
        raise OSError("đĩa đầy giả lập")
    return goc_ghi(deps_, goc, dich, text, **kw)


factory._ghi_dich = ghi_hong_mot_dich
try:
    rep = tick(deps)
finally:
    factory._ghi_dich = goc_ghi
c = trang_thai(deps)
check("một đích ghi lỗi: các đích khác vẫn nhân, đích lỗi còn nguyên và KHÔNG báo toàn bộ thành công",
      doc(roots, "dich0") == GOC and doc(roots, "dich1").strip() == NHAP.strip() and c["state"] in ("canary", "partial") and rep["promoted"] == 0, (rep, c["state"]))
check("đích lỗi không để lại file tạm", not list((roots["dich0"] / "agents").glob("*.tmp*")))

# Process chết giữa lúc promote
roots, kho, hop, deps = dung(so_dich=3)
dich_xong(roots, kho, deps)


class Chet(BaseException):
    pass


dem = {"n": 0}


def chet_o_dich_hai(deps_, goc, dich, text, **kw):
    dem["n"] += 1
    if dem["n"] == 2:
        raise Chet()
    return goc_ghi(deps_, goc, dich, text, **kw)


factory._ghi_dich = chet_o_dich_hai
try:
    try:
        tick(deps)
    except Chet:
        pass
finally:
    factory._ghi_dich = goc_ghi
c = trang_thai(deps)
tt = {pathlib.Path(t["root"]).name: t["state"] for t in c["targets"]}
check("process chết giữa chừng: đích đã xong được GHI NHẬN ngay, canary chưa kết thúc", c["state"] == "canary" and list(tt.values()).count("promoted") == 1 and "pending" in tt.values(), tt)
da_xong = next(n for n, s in tt.items() if s == "promoted")
(roots[da_xong] / "agents" / "tro-ly-a.md").write_text(RIENG, encoding="utf-8")        # chủ sửa đích đã nhân TRƯỚC khi chạy lại
rep = tick(deps)
c = trang_thai(deps)
check("chạy lại sau khi chết: làm tiếp đích còn lại, KHÔNG đụng đích đã nhân (bản riêng mới của chủ được giữ)",
      doc(roots, da_xong) == RIENG and all(doc(roots, n).strip() == NHAP.strip() for n in tt if n != da_xong), tt)
check("sau khi làm nốt: promoted và mọi đích promoted", c["state"] == "promoted" and all(t["state"] == "promoted" for t in c["targets"]), c)
rep = tick(deps)
check("chạy lần nữa không làm gì thêm", rep["promoted"] == 0 and trang_thai(deps)["state"] == "promoted")

# Rollback có kiểm phiên bản
roots, kho, hop, deps = dung()
kho.them(roots["nguon"], **viec(1, status="blocked"))
goc_bad = factory._canary_bad_signals


def sua_tay_roi_bao_loi(deps_, c_):
    kq = goc_bad(deps_, c_)
    (roots["nguon"] / "agents" / "tro-ly-a.md").write_text(RIENG, encoding="utf-8")      # chủ sửa ngay lúc canary sắp lật
    return kq


factory._canary_bad_signals = sua_tay_roi_bao_loi
try:
    rep = tick(deps)
finally:
    factory._canary_bad_signals = goc_bad
check("lật lại mà chủ vừa sửa tay: KHÔNG ghi đè bản của chủ, canary nhường (superseded)",
      doc(roots, "nguon") == RIENG and trang_thai(deps)["state"] == "superseded" and rep["reverted"] == 0, (rep, trang_thai(deps)["state"]))

# Bản sửa riêng của chủ ở brain NGUỒN trong cửa sổ canary vẫn được nhường như cũ
roots, kho, hop, deps = dung()
(roots["nguon"] / "agents" / "tro-ly-a.md").write_text(RIENG, encoding="utf-8")
dich_xong(roots, kho, deps)
rep = tick(deps)
check("chủ sửa tay brain nguồn trong cửa sổ canary: nhường chủ, không nhân", rep["superseded"] == 1 and doc(roots, "dich0") == GOC)

# Canary cũ (tạo trước 1.3.41, không có `targets`) vẫn chạy an toàn
roots, kho, hop, deps = dung()
st = factory._load_state(deps)
c = st["canaries"][0]
c.pop("targets", None)
factory._save_state(deps, st)
(roots["dich1"] / "agents" / "tro-ly-a.md").write_text(RIENG, encoding="utf-8")
dich_xong(roots, kho, deps)
tick(deps)
check("canary cũ không có `targets`: đích còn nguyên bản gốc được nhân, đích đã sửa riêng được GIỮ",
      doc(roots, "dich0").strip() == NHAP.strip() and doc(roots, "dich1") == RIENG)

# Hết hạn thiếu bằng chứng
roots, kho, hop, deps = dung()
het_gio(deps, applied_at=NOW - 20 * 86400)
rep = tick(deps)
check("quá hạn chờ bằng chứng (14 ngày): đánh dấu hết hạn, KHÔNG nhân, báo chủ một lần", trang_thai(deps)["state"] == "het_han"
      and doc(roots, "dich0") == GOC and any("chưa đủ bằng chứng" in t for t in hop), (trang_thai(deps)["state"], hop))

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
