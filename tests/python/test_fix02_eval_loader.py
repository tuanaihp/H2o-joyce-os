"""FIX-02 (Joyce Harness G1, JHA-02): bộ eval hỏng KHÔNG được hiểu là "không có bộ eval".

    python tests/run.py fix02_eval_loader      (không mạng, không model)

Trước 1.3.41, `_eval_cases` nuốt mọi lỗi và trả `[]`: JSON hỏng, root sai kiểu, case thiếu `check` đều ra
cùng kết quả với "chủ chưa khai eval", rồi `proposal_tick` áp bản nháp. Một file eval do chủ khai mà hỏng
phải CHẶN, không phải mở cửa. Ca thiếu `name`/`check` cũng không được lọc bỏ âm thầm.

Trạng thái: missing (không có file, không bắt buộc thì không chặn) | invalid (chặn, nêu lỗi từng ca) | valid.
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


def brain(eval_text=None, eval_obj=None, cfg=None):
    r = pathlib.Path(tempfile.mkdtemp(prefix="joyce-fix02-"))
    (r / "agents").mkdir()
    (r / "Joyce" / "evals").mkdir(parents=True)
    (r / "Joyce" / "proposals").mkdir(parents=True)
    (r / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True, **(cfg or {})}), encoding="utf-8")
    if eval_text is not None:
        (r / "Joyce" / "evals" / "tro-ly-a.json").write_text(eval_text, encoding="utf-8")
    elif eval_obj is not None:
        (r / "Joyce" / "evals" / "tro-ly-a.json").write_text(json.dumps(eval_obj, ensure_ascii=False), encoding="utf-8")
    return r


DRAFT = "---\ntype: agent\nname: A\n---\n## Vai trò\nnội dung\n"
OK_CASE = {"name": "có vai trò", "check": "contains", "value": "Vai trò"}


def ev(r, draft=DRAFT):
    return factory.eval_for_draft(str(r), "agents/tro-ly-a.md", draft)


def trang_thai(e):
    return (e or {}).get("status", "missing" if e is None else "?")


# ---------------- missing: không khai thì không chặn (như cũ)
check("không có file eval: trạng thái missing, không chặn", ev(brain()) is None)

# ---------------- invalid: mỗi dạng là một lỗ của bản cũ
e = ev(brain(eval_text="{ không phải json"))
check("JSON hỏng: invalid, KHÔNG phải 'không có eval'", trang_thai(e) == "invalid" and e["errors"], e)
e = ev(brain(eval_text=json.dumps("chuỗi chứ không phải mapping")))
check("root sai kiểu (chuỗi): invalid", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": "không phải danh sách"}))
check("`cases` sai kiểu: invalid", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": []}))
check("bộ rỗng (file có mà không ca nào): invalid, không được hiểu là đạt", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": [OK_CASE, {"name": "thiếu check", "value": "x"}]}))
check("ca thiếu `check` không bị lọc âm thầm: cả bộ invalid, nêu đúng ca", trang_thai(e) == "invalid" and any("thiếu check" in x for x in e["errors"]), e)
e = ev(brain(eval_obj={"cases": [OK_CASE, {"check": "contains", "value": "x"}]}))
check("ca thiếu `name`: invalid", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": [OK_CASE, "một chuỗi lạc vào"]}))
check("phần tử không phải mapping: invalid", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": [{"name": "không giá trị", "check": "contains"}]}))
check("check cần `value` mà thiếu: invalid (bản cũ luôn cho qua vì `'' in text` là True)", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": [{"name": "regex hỏng", "check": "regex", "value": "([a-z"}]}))
check("regex không biên dịch được: invalid", trang_thai(e) == "invalid", e)
e = ev(brain(eval_obj={"cases": [{"name": "dài", "check": "max_len", "value": "không phải số"}]}))
check("max_len không phải số dương: invalid", trang_thai(e) == "invalid", e)
nhieu = [{"name": f"ca{i}", "check": "contains", "value": "Vai trò"} for i in range(factory.EVAL_MAX_CASES + 1)]
e = ev(brain(eval_obj={"cases": nhieu}))
check("quá số ca cho phép: invalid, KHÔNG cắt âm thầm còn 20 ca rồi cho qua", trang_thai(e) == "invalid" and any("quá" in x for x in e["errors"]), e)
e = ev(brain(eval_text="x" * (factory.EVAL_MAX_BYTES + 10)))
check("file eval quá lớn: invalid, không đọc", trang_thai(e) == "invalid", e)

# ---------------- valid
e = ev(brain(eval_obj={"cases": [OK_CASE, {"name": "không quá dài", "check": "max_len", "value": 20000}]}))
check("bộ hợp lệ: valid, đếm số ca đọc, chạy, rớt", trang_thai(e) == "valid" and (e["read"], e["total"], len(e["fails"])) == (2, 2, 0), e)
e = ev(brain(eval_obj=[OK_CASE]))
check("root là danh sách các ca (dạng cũ) vẫn hợp lệ", trang_thai(e) == "valid" and e["total"] == 1, e)
e = ev(brain(eval_obj={"cases": [OK_CASE]}), "không có vai trò gì cả")
check("ca rớt thật: valid nhưng có fails", trang_thai(e) == "valid" and e["fails"] == ["có vai trò"], e)
e = ev(brain(eval_obj={"cases": [OK_CASE, {"name": "check lạ", "check": "chua", "value": "x"}]}))
check("check lạ: vẫn tính RỚT kèm nhãn không kiểm được (B-10 giữ nguyên)", e["fails"] == ["check lạ (không kiểm được)"] and e["passed"] == 1, e)

# ---------------- bắt buộc: thiếu cũng chặn khi chủ đặt eval_bat_buoc
e = factory.eval_for_draft(str(brain()), "agents/tro-ly-a.md", DRAFT, bat_buoc=True)
check("eval bắt buộc mà không có file: missing_required, chặn", trang_thai(e) == "missing_required" and e["errors"], e)
check("cấu hình eval_bat_buoc của brain được đọc, mặc định tắt",
      factory.load_factory_cfg(str(brain(cfg={"eval_bat_buoc": True})))["eval_bat_buoc"] is True
      and factory.load_factory_cfg(str(brain()))["eval_bat_buoc"] is False)

# ---------------- đường áp: bản nháp không được áp khi eval hỏng
GOC = "---\ntype: agent\nname: A\n---\n## Vai trò\ncũ\n"
NHAP = "---\ntype: agent\nname: A\n---\n## Vai trò\n" + "Nội dung mới đầy đủ hơn nhiều, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3 + "\n"


def chay(r):
    (r / "agents" / "tro-ly-a.md").write_text(GOC, encoding="utf-8")
    pf = r / "Joyce" / "proposals" / "2026-10-28-tro-ly-a.md"
    pf.write_text("---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: agents/tro-ly-a.md\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + NHAP + "```\n", encoding="utf-8")
    hop = []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: ["P"], task_root=lambda n: str(r), store=None, enqueue=None, loops=None,
                               workflows_dir=lambda root: pathlib.Path(root) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=r)
    rep = asyncio.run(factory.proposal_tick(deps))
    return rep, (r / "agents" / "tro-ly-a.md").read_text(encoding="utf-8"), pf.read_text(encoding="utf-8"), hop


rep, file_, prop, hop = chay(brain(eval_text="{ hỏng"))
check("eval JSON hỏng: bản nháp KHÔNG được áp, file giữ nguyên baseline", rep["applied"] == 0 and file_ == GOC)
check("proposal sang eval_failed và nêu lý do bộ eval không đọc được, chủ nhận thông báo",
      "status: eval_failed" in prop and any("eval" in t.lower() and "không" in t.lower() for t in hop), (prop[:200], hop))
rep, file_, prop, hop = chay(brain(eval_obj={"cases": [OK_CASE, {"name": "thiếu check"}]}))
check("ca thiếu check: bản nháp KHÔNG được áp", rep["applied"] == 0 and file_ == GOC)
rep, file_, prop, hop = chay(brain(eval_obj={"cases": [OK_CASE]}))
check("bộ eval hợp lệ và bản nháp đạt: vẫn tự áp như cũ", rep["applied"] == 1 and file_ != GOC)
rep, file_, prop, hop = chay(brain())
check("không khai eval và không bắt buộc: vẫn tự áp như cũ", rep["applied"] == 1 and file_ != GOC)
rep, file_, prop, hop = chay(brain(cfg={"eval_bat_buoc": True}))
check("eval bắt buộc mà thiếu: KHÔNG tự áp", rep["applied"] == 0 and file_ == GOC)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
