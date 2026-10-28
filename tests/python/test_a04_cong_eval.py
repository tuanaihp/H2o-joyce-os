"""A04 (Joyce Harness, gói A): cổng eval với bốn trạng thái, gắn kết quả vào đúng bản nháp.

    python tests/run.py a04_cong_eval      (không mạng, không model; mọi file nằm trong thư mục tạm)

Chủ chọn D4 nhẹ (28/10/2026): CHỈ chặn khi bộ eval `invalid` hoặc `valid_fail`; thiếu bộ eval (`missing`) KHÔNG bị D4 chặn,
`eval_bat_buoc` mặc định tắt. Vì D3 đã chặn tự áp mọi thay đổi hành vi và quyền ở gói A, ma trận cho thấy eval chỉ còn quyết
định ở nhánh `display_only`; nhánh còn lại luôn chờ chủ dù eval đạt. Test này CHỐT cả hai điều đó, kể cả điều ít tác dụng của
D4 nhẹ.

Bốn trạng thái: missing | invalid | valid_pass | valid_fail. Lỗi đọc file hoặc lỗi chạy evaluator KHÔNG bao giờ thành
missing hay pass. Kết quả gắn với `eval_candidate_hash` của bản nháp và `eval_revision` của file eval: đổi một trong hai thì
kết quả cũ không còn dùng được.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import pathlib
import sys
import tempfile

import factory  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nrole: Thu\nupdated: 2026-10-01\n---\n" + THAN
HIEN_THI = GOC.replace("2026-10-01", "2026-10-28")
HANH_VI = GOC.replace("role: Thu", "role: Chi")
QUYEN = GOC.replace("updated: 2026-10-01\n", "updated: 2026-10-01\nmodel: gpt-6\n")
REL = "agents/tro-ly-a.md"
CA_DAT = {"cases": [{"name": "có vai trò", "check": "contains", "value": "Vai trò"}]}
CA_RIT = {"cases": [{"name": "có chữ không tồn tại", "check": "contains", "value": "KHONG-BAO-GIO-CO"}]}


def dung(nhap, eval_obj=None, eval_text=None, cfg=None):
    base = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a04-"))
    r = base / "nguon"
    (r / "agents").mkdir(parents=True)
    (r / "Joyce" / "proposals").mkdir(parents=True)
    (r / "Joyce" / "evals").mkdir(parents=True)
    (r / REL).write_text(GOC, encoding="utf-8")
    (r / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True, **(cfg or {})}), encoding="utf-8")
    if eval_text is not None:
        (r / "Joyce" / "evals" / "tro-ly-a.json").write_text(eval_text, encoding="utf-8")
    elif eval_obj is not None:
        (r / "Joyce" / "evals" / "tro-ly-a.json").write_text(json.dumps(eval_obj, ensure_ascii=False), encoding="utf-8")
    pf = r / "Joyce" / "proposals" / "2026-10-28-tro-ly-a.md"
    pf.write_text("---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + REL + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + nhap + "```\n", encoding="utf-8")
    hop = []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: ["nguon"], task_root=lambda n: str(r), store=None, enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=base)
    return r, pf, hop, deps


def trang_thai(pf):
    fm, _ = factory._proposal_front(pf.read_text(encoding="utf-8"))
    return (fm or {}).get("status", "")


def chay(nhap, **kw):
    r, pf, hop, deps = dung(nhap, **kw)
    rep = asyncio.run(factory.proposal_tick(deps))
    return r, pf, hop, rep, (r / REL).read_text(encoding="utf-8")


# ============================================================
# 1. Ma trận: trạng thái eval x loại thay đổi
# ============================================================
EVAL = {"không có bộ eval (missing)": dict(), "bộ eval hỏng (invalid)": dict(eval_text="{ hỏng"),
        "bộ eval rớt (valid_fail)": dict(eval_obj=CA_RIT), "bộ eval đạt (valid_pass)": dict(eval_obj=CA_DAT)}
LOAI = {"display_only": HIEN_THI, "behavior_change": HANH_VI, "permission_change": QUYEN}
# (loại, trạng thái eval) -> có tự áp không
TU_AP = {("display_only", "không có bộ eval (missing)"): True, ("display_only", "bộ eval hỏng (invalid)"): False,
         ("display_only", "bộ eval rớt (valid_fail)"): False, ("display_only", "bộ eval đạt (valid_pass)"): True}
for loai, nhap in LOAI.items():
    for ten, kw in EVAL.items():
        r, pf, hop, rep, noi_dung = chay(nhap, **kw)
        duoc = TU_AP.get((loai, ten), False)
        check(f"{loai} + {ten}: {'tự áp' if duoc else 'KHÔNG tự áp, file giữ nguyên'}",
              (rep["applied"] == 1 and noi_dung == nhap) if duoc else (rep["applied"] == 0 and noi_dung == GOC), (rep, trang_thai(pf)))
r, pf, hop, rep, nd = chay(HANH_VI, eval_obj=CA_DAT)
check("D3 + eval đạt: thay đổi hành vi VẪN chờ chủ (eval chuỗi không thay gate hành vi)", trang_thai(pf) == "cho_chu_duyet" and nd == GOC)
r, pf, hop, rep, nd = chay(HIEN_THI, eval_obj=CA_RIT)
check("hiển thị + eval rớt: trạng thái eval_failed, chủ nhận thông báo", trang_thai(pf) == "eval_failed" and hop, (trang_thai(pf), hop))
r, pf, hop, rep, nd = chay(HIEN_THI, eval_text="{ hỏng")
check("hiển thị + eval hỏng: trạng thái eval_failed nêu bộ eval không dùng được", trang_thai(pf) == "eval_failed" and "không dùng được" in pf.read_text(encoding="utf-8"))

# ---------------- eval_bat_buoc = true: thiếu cũng chặn (tuỳ chọn, mặc định tắt)
r, pf, hop, rep, nd = chay(HIEN_THI, cfg={"eval_bat_buoc": True})
check("eval_bat_buoc=true: thiếu bộ eval chặn tự áp (tuỳ chọn của chủ)", rep["applied"] == 0 and nd == GOC and trang_thai(pf) == "eval_failed")
r, pf, hop, rep, nd = chay(HIEN_THI, cfg={"eval_bat_buoc": False})
check("eval_bat_buoc=false (mặc định, D4 nhẹ): thiếu bộ eval KHÔNG bị D4 chặn", rep["applied"] == 1)

# ============================================================
# 2. Chính sách hiệu lực nói thật, để UI không báo một đằng chạy một nẻo
# ============================================================
cs = factory.chinh_sach_eval({"eval_bat_buoc": False})
check("chính sách hiệu lực (mặc định): chặn invalid và fail, KHÔNG chặn missing, nói rõ thay đổi hành vi vẫn chờ chủ",
      cs["chan_invalid"] and cs["chan_fail"] and cs["chan_missing"] is False and cs["hanh_vi_van_cho_chu"] is True and cs["loai_eval"] == "chuoi", cs)
cs2 = factory.chinh_sach_eval({"eval_bat_buoc": True})
check("chính sách hiệu lực khi chủ bật bắt buộc: chặn cả missing", cs2["chan_missing"] is True and cs2["hanh_vi_van_cho_chu"] is True, cs2)
check("giá trị cấu hình lạ không làm mở cổng: coi như mặc định, không coi như 'tắt hết'", factory.chinh_sach_eval({"eval_bat_buoc": "linh tinh"})["chan_invalid"] is True)
check("eval chuỗi được gắn nhãn chuỗi, KHÔNG phải eval hành vi", "chuỗi" in cs["ghi_chu"].lower() and "hành vi" in cs["ghi_chu"].lower(), cs["ghi_chu"])

# ============================================================
# 3. Kết quả gắn với bản nháp và phiên bản eval
# ============================================================
r, pf, hop, rep, nd = chay(HIEN_THI, eval_obj=CA_DAT)
fm, _ = factory._proposal_front(pf.read_text(encoding="utf-8"))
check("kết quả eval ghi SHA-256 đầy đủ của bản nháp đã chấm và của file eval", fm and len(fm.get("eval_candidate_hash", "")) == 64
      and fm["eval_candidate_hash"] == factory._sha256(nd) and len(fm.get("eval_revision", "")) == 64, fm)
check("ghi rõ đây là eval chuỗi và bằng chứng hành vi CHƯA có", fm and fm.get("eval_loai") == "chuoi" and fm.get("eval_hanh_vi") == "chua_co", fm)
check("kết quả cũ không dùng được cho bản nháp khác", factory.eval_ket_qua_hop_le(fm, factory._sha256(nd), fm["eval_revision"]) is True
      and factory.eval_ket_qua_hop_le(fm, factory._sha256(nd + "x"), fm["eval_revision"]) is False)
check("sửa file eval sau khi chấm: kết quả cũ không còn hợp lệ (phải chạy lại)", factory.eval_ket_qua_hop_le(fm, factory._sha256(nd), "0" * 64) is False)
check("kết quả thiếu dấu băm: không hợp lệ", factory.eval_ket_qua_hop_le({}, "a" * 64, "b" * 64) is False)
r, pf, hop, rep, nd2 = chay(HIEN_THI, eval_obj=CA_RIT)
fm2, _ = factory._proposal_front(pf.read_text(encoding="utf-8"))
check("cả kết quả RỚT cũng gắn băm bản nháp đã chấm", fm2 and len(fm2.get("eval_candidate_hash", "")) == 64, fm2)

# ============================================================
# 4. Evaluator ném lỗi: không biến thành missing hay pass
# ============================================================
goc_load = factory.eval_load


def load_no(*a, **k):
    raise RuntimeError("evaluator hỏng giả lập")


factory.eval_load = load_no
try:
    r, pf, hop, rep, nd = chay(HIEN_THI, eval_obj=CA_DAT)
finally:
    factory.eval_load = goc_load
check("evaluator ném lỗi: KHÔNG tự áp (không thành missing, không thành pass), file giữ nguyên bản đã duyệt",
      rep["applied"] == 0 and nd == GOC and trang_thai(pf) == "eval_failed", (rep, trang_thai(pf)))
check("lỗi evaluator được báo cho chủ nêu rõ đây là lỗi chạy, không phải eval rớt", any("evaluator" in t.lower() or "lỗi khi chạy" in t.lower() for t in hop), hop)

# ============================================================
# 5. Một đề xuất bị chặn không làm dừng phục vụ hay các đề xuất khác
# ============================================================
base = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a04b-"))
roots = {}
rels = {"a": "agents/tro-ly-a.md", "b": "agents/tro-ly-b.md"}      # khác tên file để KHÔNG bị coi là file dùng chung (D1)
for ten in ("a", "b"):
    rr = base / ten
    (rr / "agents").mkdir(parents=True)
    (rr / "Joyce" / "proposals").mkdir(parents=True)
    (rr / "Joyce" / "evals").mkdir(parents=True)
    (rr / rels[ten]).write_text(GOC, encoding="utf-8")
    (rr / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
    (rr / "Joyce" / "proposals" / "2026-10-28-de-xuat.md").write_text(
        "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + rels[ten] + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + HIEN_THI + "```\n", encoding="utf-8")
    roots[ten] = rr
(roots["a"] / "Joyce" / "evals" / "tro-ly-a.json").write_text("{ hỏng", encoding="utf-8")        # brain a: eval hỏng
hop = []


async def inbox(text, **kw):
    hop.append(text)


deps = factory.FactoryDeps(brains=lambda: ["a", "b"], task_root=lambda n: str(roots[n]), store=None, enqueue=None, loops=None,
                           workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                           incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=base)
rep = asyncio.run(factory.proposal_tick(deps))
check("brain a bị chặn bởi eval hỏng, brain b vẫn được xử lý trong cùng lượt quét",
      (roots["a"] / rels["a"]).read_text(encoding="utf-8") == GOC and (roots["b"] / rels["b"]).read_text(encoding="utf-8") == HIEN_THI and rep["applied"] == 1, rep)
check("bản đang phục vụ ở brain bị chặn vẫn nguyên vẹn và đọc được", "Trợ lý A" in (roots["a"] / rels["a"]).read_text(encoding="utf-8"))

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
