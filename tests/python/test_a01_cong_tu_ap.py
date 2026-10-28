"""A01 (Joyce Harness, gói A): cổng host chặn tự áp, trạng thái an toàn cho canary cũ, cờ dừng.

    python tests/run.py a01_cong_tu_ap      (không mạng, không model; mọi file nằm trong thư mục tạm)

Chính sách (plan Sonnet mục 2.2 và 2.4): chỉ thay đổi `display_only` được tự áp; behavior_change, permission_change, unknown
và invalid đều chờ chủ (D3). File dùng chung nhiều brain cần canary, mà canary cần telemetry; chưa có telemetry thì KHÔNG
tự áp, KHÔNG tự nhân (D1). Cờ dừng không tắt giám định, đọc hay phục vụ bằng bản đã duyệt. Canary cũ chuyển legacy_review,
giữ nguyên bản ghi gốc, migration chạy lặp không đổi kết quả và không ghi file brain nào.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import hashlib
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


THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nrole: Thu\nupdated: 2026-10-01\n---\n" + THAN
H = "---\ntype: workflow\nname: Quy trình\nsteps:\n"


def dung(goc=GOC, nhap=None, rel="agents/tro-ly-a.md", cfg=None, them_brain=False, loai="agent"):
    base = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a01-"))
    r = base / "nguon"
    (r / pathlib.Path(rel).parent).mkdir(parents=True)
    (r / "Joyce" / "proposals").mkdir(parents=True)
    (r / rel).write_text(goc, encoding="utf-8")
    (r / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True, **(cfg or {})}), encoding="utf-8")
    roots = {"nguon": r}
    if them_brain:
        d = base / "dich"
        (d / pathlib.Path(rel).parent).mkdir(parents=True)
        (d / "Joyce" / "proposals").mkdir(parents=True)
        (d / rel).write_text(goc, encoding="utf-8")
        roots["dich"] = d
    pf = r / "Joyce" / "proposals" / "2026-10-28-de-xuat.md"
    pf.write_text("---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + rel + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n"
                  + (nhap if nhap is not None else goc) + "```\n", encoding="utf-8")
    hop = []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=None, enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=base)
    return roots, pf, hop, deps


def chay(deps):
    return asyncio.run(factory.proposal_tick(deps))


def doc(roots, rel="agents/tro-ly-a.md", ten="nguon"):
    return (roots[ten] / rel).read_text(encoding="utf-8")


def trang_thai(pf):
    for ln in pf.read_text(encoding="utf-8").split("\n"):
        if ln.startswith("status:"):
            return ln.split(":", 1)[1].strip()
    return ""


# ============================================================
# 1. Ma trận phân loại -> kết quả, qua đường apply thật (proposal_tick)
# ============================================================
def them_dong(extra):
    return GOC.replace("updated: 2026-10-01\n", "updated: 2026-10-01\n" + extra)


CAC_CA = [
    ("display_only (đổi updated, thêm tags)", GOC.replace("2026-10-01", "2026-10-28").replace("---\n" + THAN, "tags: [Thu]\n---\n" + THAN), True),
    ("behavior_change: thân bài", GOC.replace("Nội dung đầy đủ", "Nội dung đầy đủ hơn, được phép gửi tin cho khách"), False),
    ("behavior_change: role", GOC.replace("role: Thu", "role: Chi"), False),
    ("behavior_change: name", GOC.replace("name: Trợ lý A", "name: Giám đốc"), False),
    ("permission_change: model", them_dong("model: gpt-6\n"), False),
    ("permission_change: khoá lồng", them_dong("harness:\n  budgets:\n    max_tokens: 900000\n"), False),
    ("unknown: khoá lạ", them_dong("permissions:\n  write: all\n"), False),
    ("invalid: thiếu dấu đóng", "---\ntype: agent\nname: Trợ lý A\nthân bài không có dấu đóng " * 6, False),
    ("invalid: khoá trùng", them_dong("tools: [a]\ntools: [a, b]\n"), False),
]
for ten, nhap, duoc_ap in CAC_CA:
    roots, pf, hop, deps = dung(nhap=nhap)
    rep = chay(deps)
    check(f"{ten}: {'tự áp' if duoc_ap else 'KHÔNG tự áp, giữ nguyên file'}",
          (rep["applied"] == 1 and doc(roots) == nhap) if duoc_ap else (rep["applied"] == 0 and doc(roots) == GOC), (rep, doc(roots)[:80]))
    if not duoc_ap:
        check(f"{ten}: đề xuất sang cho_chu_duyet, có lý do, chủ nhận thông báo", trang_thai(pf) == "cho_chu_duyet" and "ly_do_cho" in pf.read_text(encoding="utf-8") and hop, (trang_thai(pf), hop))

# ---------------- hai ca chẩn đoán trực tiếp của Astra, kiểm ĐẦU CUỐI qua _proposal_apply
STEP1 = "  - id: s\n    agent: a\n    tools: []\n    task: t\n  - id: s\n    agent: b\n    tools: []\n    task: t\n---\n" + THAN
STEP2 = "  - id: s\n    agent: a\n    tools: [joyce_shop]\n    task: t\n  - id: s\n    agent: b\n    tools: []\n    task: t\n---\n" + THAN
roots, pf, hop, deps = dung(goc=H + STEP1, nhap=H + STEP2, rel="workflows/qt.md")
rep = chay(deps)
check("chẩn đoán 1 (hai bước trùng id, bước đầu tăng quyền): không tự áp, đi đến tận cổng chứ không bị parser khác chặn nhầm lý do",
      rep["applied"] == 0 and doc(roots, "workflows/qt.md") == H + STEP1 and trang_thai(pf) == "cho_chu_duyet", (rep, trang_thai(pf)))
roots, pf, hop, deps = dung(goc=GOC, nhap="---\ntype: agent\nname: Trợ lý A\nrole: Thu\nupdated: 2026-10-28\n" + THAN)
rep = chay(deps)
check("chẩn đoán 2 (YAML mở --- thiếu dấu đóng): không tự áp, file nguồn không bị ghi", rep["applied"] == 0 and doc(roots) == GOC, rep)

# ---------------- cả direct lẫn canary đều qua cổng
roots, pf, hop, deps = dung(nhap=GOC.replace("2026-10-01", "2026-10-28"))
check("direct + display_only: tự áp", chay(deps)["applied"] == 1)
roots, pf, hop, deps = dung(nhap=GOC.replace("role: Thu", "role: Chi"), them_brain=True)
factory.telemetry_ready = lambda *a, **k: True
try:
    rep = chay(deps)
finally:
    factory.telemetry_ready = lambda *a, **k: False
check("canary + behavior_change: bị chặn dù có telemetry (cổng áp cho cả hai đường)", rep["canary"] == 0 and rep["applied"] == 0 and doc(roots, ten="dich") == GOC, rep)

# ============================================================
# 2. D1: file dùng chung chưa có telemetry
# ============================================================
roots, pf, hop, deps = dung(nhap=GOC.replace("2026-10-01", "2026-10-28"), them_brain=True)
rep = chay(deps)
st = factory._load_state(deps)
check("D1: file dùng chung, chưa có telemetry: KHÔNG tự đưa vào nguồn, KHÔNG tạo canary",
      rep["canary"] == 0 and rep["applied"] == 0 and doc(roots) == GOC and doc(roots, ten="dich") == GOC and not st["canaries"], (rep, st["canaries"]))
check("D1: đề xuất vẫn được giữ (giám định, nháp) và chờ chủ, nói rõ lý do telemetry", trang_thai(pf) == "cho_chu_duyet" and "telemetry" in pf.read_text(encoding="utf-8"))
check("telemetry_ready hiện luôn False (gói B mới làm thật)", factory.telemetry_ready(deps, "nguon", "agents/tro-ly-a.md") is False)

# ============================================================
# 3. Cờ dừng: dừng tự triển khai, không tắt phục vụ
# ============================================================
roots, pf, hop, deps = dung(nhap=GOC.replace("2026-10-01", "2026-10-28"), cfg={"auto_deploy": False})
rep = chay(deps)
check("cờ dừng (auto_deploy=false): không tự áp, đề xuất GIỮ NGUYÊN trạng thái pending", rep["applied"] == 0 and rep["paused"] == 1 and trang_thai(pf) == "pending" and doc(roots) == GOC, (rep, trang_thai(pf)))
check("cờ dừng: bản hiện hành còn đó, đọc được (vẫn phục vụ)", "Trợ lý A" in doc(roots))
check("cờ dừng mặc định BẬT như cũ", factory.load_factory_cfg(str(roots["nguon"] / "..")).get("auto_deploy") is True)
roots, pf, hop, deps = dung(nhap=GOC.replace("2026-10-01", "2026-10-28"))
st = factory._load_state(deps)
st["tam_dung"] = True
factory._save_state(deps, st)
check("cờ dừng toàn cục trong state cũng dừng tự áp", chay(deps)["paused"] == 1 and doc(roots) == GOC)

# ============================================================
# 4. Canary cũ -> legacy_review; migration lặp không đổi và không ghi brain
# ============================================================
def bam(roots_):
    return {k: hashlib.sha256((v / "agents" / "tro-ly-a.md").read_bytes()).hexdigest() for k, v in roots_.items()}


roots, pf, hop, deps = dung(them_brain=True)
cu = {"id": "cu1", "brain": "nguon", "root": str(roots["nguon"]), "target": "agents/tro-ly-a.md", "slug": "tro-ly-a",
      "hash": "abc", "backup": "/x/y.bak", "proposal": "p.md", "applied_at": time.time() - 3600, "promote_at": time.time() - 10,
      "sharers": [str(roots["dich"])], "state": "canary"}
da_xong = dict(cu, id="cu2", state="promoted")
sf = pathlib.Path(deps.state_dir) / "factory-state.json"
sf.write_text(json.dumps({"watches": [], "perf_cd": {}, "sev_sent": {}, "canaries": [cu, da_xong]}), encoding="utf-8")   # state kiểu cũ, không có `schema`
truoc = bam(roots)
s1 = factory._load_state(deps)
c1 = next(c for c in s1["canaries"] if c["id"] == "cu1")
check("state cũ (không có schema): canary đang canh chuyển legacy_review, giữ nguyên nguồn/hash/sao lưu/các đích",
      c1["state"] == "legacy_review" and c1["hash"] == "abc" and c1["backup"] == "/x/y.bak" and c1["sharers"] == [str(roots["dich"])] and c1["legacy"]["state"] == "canary" and s1["schema"] == factory.STATE_SCHEMA, c1)
check("canary đã kết thúc (promoted) không bị đụng", next(c for c in s1["canaries"] if c["id"] == "cu2")["state"] == "promoted")
s2 = factory._load_state(deps)
check("migration chạy lặp không đổi kết quả (kể cả mốc thời gian)", json.dumps(s1, sort_keys=True) == json.dumps(factory._migrate_state(json.loads(json.dumps(s1))), sort_keys=True)
      and s2["canaries"][0]["state"] == "legacy_review")
check("migration không ghi file brain nào", bam(roots) == truoc)
rep = asyncio.run(factory.canary_tick(deps))
check("canary_tick không canh, không nhân, không lật canary legacy_review; báo số lượng", rep["promoted"] == 0 and rep["reverted"] == 0 and rep["legacy_review"] == 1 and bam(roots) == truoc, rep)
s3 = json.loads(sf.read_text(encoding="utf-8"))
check("restart: state đã lưu giữ legacy_review, schema và bản ghi gốc (không biến mất sau migration)",
      s3["schema"] == factory.STATE_SCHEMA and next(c for c in s3["canaries"] if c["id"] == "cu1")["state"] == "legacy_review" and len(s3["canaries"]) == 2)
snap = factory.stages_snapshot(deps)
check("Sơ đồ đếm được canary legacy_review (không bị rơi vào 'đang canh')", snap["canary"].get("legacy_review") == 1 and "canary" not in snap["canary"], snap["canary"])
rep = chay(deps)
check("bản hiện hành vẫn phục vụ được trong lúc đó: tick đề xuất chạy bình thường", rep["scanned"] >= 0)

# ---------------- tạm dừng không chặn lật lại khi có lỗi
factory.telemetry_ready = lambda *a, **k: True
try:
    roots, pf, hop, deps = dung(nhap=GOC.replace("2026-10-01", "2026-10-28"), them_brain=True)
    chay(deps)
finally:
    factory.telemetry_ready = lambda *a, **k: False
st = factory._load_state(deps)
check("(chuẩn bị) có một canary thật để thử tạm dừng", len(st["canaries"]) == 1 and st["canaries"][0]["state"] == "canary")
st["tam_dung"] = True
st["canaries"][0]["promote_at"] = 0
factory._save_state(deps, st)


class Kho:
    def list_tasks(self, root, include_archived=False, limit=400):
        return [{"id": "t1", "status": "done", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1, "updated_at": time.time() + 2} for _ in range(25)]


deps.store = Kho()
rep = asyncio.run(factory.canary_tick(deps))
check("đang tạm dừng: đủ giờ, đủ bằng chứng vẫn KHÔNG nhân", rep["promoted"] == 0 and rep["paused"] == 1 and doc(roots, ten="dich") == GOC, rep)


class KhoLoi:
    def list_tasks(self, root, include_archived=False, limit=400):
        return [{"id": "t9", "status": "blocked", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1, "updated_at": time.time() + 2}]


deps.store = KhoLoi()
rep = asyncio.run(factory.canary_tick(deps))
check("đang tạm dừng: có lỗi thì VẪN lật lại (an toàn không bị tắt theo cờ dừng)", rep["reverted"] == 1 and doc(roots) == GOC, rep)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
