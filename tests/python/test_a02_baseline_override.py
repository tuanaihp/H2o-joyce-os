"""A02 (Joyce Harness, gói A): baseline chung, override, quan hệ kế thừa, kiểm phiên bản cả ở nguồn.

    python tests/run.py a02_baseline_override      (không mạng, không model; mọi file nằm trong thư mục tạm)

Điều G1-02 chỉ ra: bản FIX-04 chỉ bảo vệ đích bị sửa SAU lúc chụp. Đích VỐN ĐÃ KHÁC bản nguồn từ trước (phòng có biến thể
riêng từ lâu) vẫn bị ghi đè nếu không đổi kể từ lúc chụp. Quy tắc D2 (chủ duyệt): chỉ tự nhân khi đích đúng bằng bản nguồn
TRƯỚC khi sửa (baseline chung) VÀ vẫn đúng bằng snapshot ngay trước khi ghi; đích khác baseline là `override` chờ chủ.

Mọi ca dưới đây đi qua `proposal_tick` rồi `canary_tick` (đường thật), không chỉ gọi hàm phụ. Telemetry giả được bật có chủ ý
để thử riêng logic nhân (D1 chặn canary khi chưa có telemetry thật).
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
import _so_luot_chay  # noqa: E402
_so_luot_chay.cai_dat(factory)

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


factory.telemetry_ready = lambda *a, **k: True
THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nrole: Thu\nupdated: 2026-10-01\n---\n" + THAN
MOI = GOC.replace("2026-10-01", "2026-10-28")
RIENG = GOC + "\nBiến thể riêng của phòng này từ lâu.\n"
REL = "agents/tro-ly-a.md"


class Kho:
    def __init__(self):
        self.t = []

    def list_tasks(self, root, include_archived=False, limit=400):
        return list(self.t)


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def dung(dich=("dich0", "dich1"), noi_dung=None, nhap=MOI, goc=GOC):
    """Nguồn + các brain đích. `noi_dung`: {tên đích: nội dung file}; thiếu thì dùng GOC."""
    base = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a02-"))
    roots = {"nguon": base / "nguon"}
    for d in dich:
        roots[d] = base / d
    for k, r in roots.items():
        (r / "agents").mkdir(parents=True)
        (r / "Joyce" / "proposals").mkdir(parents=True)
        (r / REL).write_text((noi_dung or {}).get(k, goc), encoding="utf-8")
    (roots["nguon"] / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
    pf = roots["nguon"] / "Joyce" / "proposals" / "2026-10-28-tro-ly-a.md"
    pf.write_text("---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + REL + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + nhap + "```\n", encoding="utf-8")
    hop = []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=Kho(), enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=base)
    return roots, pf, hop, deps


def ap(deps):
    return asyncio.run(factory.proposal_tick(deps))


def canary(deps):
    st = factory._load_state(deps)
    return st["canaries"][0] if st["canaries"] else None


def du_bang_chung(deps, n=25):
    deps.store.t = [{"id": f"t{i}", "status": "done", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1, "updated_at": time.time() + 2}
                    for i in range(n)]


def het_gio(deps):
    st = factory._load_state(deps)
    st["canaries"][0]["promote_at"] = 0
    factory._save_state(deps, st)


def tick(deps):
    return asyncio.run(factory.canary_tick(deps))


def doc(roots, ten):
    return (roots[ten] / REL).read_text(encoding="utf-8")


# ============================================================
# 1. Hash đầy đủ và bản ghi triển khai
# ============================================================
roots, pf, hop, deps = dung()
ap(deps)
c = canary(deps)
check("bản ghi canary lưu SHA-256 ĐẦY ĐỦ (64 ký tự) của baseline nguồn và ứng viên",
      c and len(c.get("source_baseline_hash", "")) == 64 and c["source_baseline_hash"] == sha(GOC)
      and len(c.get("candidate_hash", "")) == 64 and c["candidate_hash"] == sha(MOI), c and {k: c.get(k) for k in ("source_baseline_hash", "candidate_hash")})
check("có deployment_id, schema_version; package_id để trống vì hệ chưa có khái niệm package (không tự khai kế thừa)",
      c and c.get("deployment_id") and c.get("schema_version") == factory.STATE_SCHEMA and c.get("package_id") in (None, ""), c and {k: c.get(k) for k in ("deployment_id", "schema_version", "package_id")})
check("từng đích có hash quan sát SHA-256 đầy đủ lúc chụp và được xếp loại kế thừa",
      c and all(len(t.get("target_observed_hash", "")) == 64 and t.get("quan_he") == "ke_thua" for t in c["targets"]), c and c["targets"])
check("hash ngắn cũ vẫn còn để tương thích", c and c.get("hash") == factory._sha(MOI))

# ============================================================
# 2. Đích VỐN ĐÃ KHÁC bản nguồn trước khi sửa: override, không bị ghi đè (G1-02)
# ============================================================
roots, pf, hop, deps = dung(noi_dung={"dich1": RIENG})
ap(deps)
c = canary(deps)
q = {pathlib.Path(t["root"]).name: t for t in c["targets"]}
check("đích đã khác baseline từ TRƯỚC khi sửa được xếp là override ngay lúc lập kế hoạch", q["dich1"]["quan_he"] == "override" and q["dich1"]["state"] == "override" and q["dich0"]["quan_he"] == "ke_thua", q)
du_bang_chung(deps)
het_gio(deps)
rep = tick(deps)
c = canary(deps)
check("nhân: đích kế thừa được ghi, đích override GIỮ NGUYÊN bản riêng dù không đổi từ lúc chụp",
      doc(roots, "dich0") == MOI and doc(roots, "dich1") == RIENG, (doc(roots, "dich1")[-60:], rep))
check("kết quả partial, nêu đích override, không báo toàn bộ thành công", c["state"] == "partial" and rep["partial"] == 1 and rep["promoted"] == 0
      and any("override" in t or "bản riêng" in t for t in hop), (c["state"], hop))
check("đích override KHÔNG có sao lưu vì không bị ghi", not list((roots["dich1"] / "Joyce" / "proposals").glob(".backup/*")))

# Tất cả đích đều override: không ghi gì
roots, pf, hop, deps = dung(noi_dung={"dich0": RIENG, "dich1": RIENG + "x"})
ap(deps)
du_bang_chung(deps)
het_gio(deps)
rep = tick(deps)
check("mọi đích đều override: không ghi đích nào, canary kết thúc conflict (không phải promoted)",
      doc(roots, "dich0") == RIENG and doc(roots, "dich1") == RIENG + "x" and canary(deps)["state"] == "conflict" and rep["conflict"] == 1, (canary(deps)["state"], rep))

# Cùng slug, khác nội dung ở brain khác: cùng tên không đủ chứng minh cùng package
roots, pf, hop, deps = dung(dich=("dich0",), noi_dung={"dich0": GOC.replace("name: Trợ lý A", "name: Trợ lý của phòng khác")})
ap(deps)
check("cùng tên file khác nội dung ở brain khác: override, không tự nhân", canary(deps)["targets"][0]["quan_he"] == "override")

# ============================================================
# 3. Sửa SAU lúc chụp, xoá, lỗi một đích (giữ từ FIX-04, nay qua phân loại mới)
# ============================================================
roots, pf, hop, deps = dung()
ap(deps)
(roots["dich1"] / REL).write_text(RIENG, encoding="utf-8")
du_bang_chung(deps)
het_gio(deps)
tick(deps)
q = {pathlib.Path(t["root"]).name: t["state"] for t in canary(deps)["targets"]}
check("đích sửa SAU lúc chụp: conflict, giữ bản của chủ", q["dich1"] == "conflict" and doc(roots, "dich1") == RIENG and q["dich0"] == "promoted")

roots, pf, hop, deps = dung()
ap(deps)
(roots["dich0"] / REL).unlink()
du_bang_chung(deps)
het_gio(deps)
tick(deps)
q = {pathlib.Path(t["root"]).name: t["state"] for t in canary(deps)["targets"]}
check("đích bị xoá: missing, không tạo lại", q["dich0"] == "missing" and not (roots["dich0"] / REL).exists() and q["dich1"] == "promoted")

# Đích đã bằng ứng viên nhưng KHÔNG có receipt: đã đúng bản, nhưng không kết luận hệ thống từng ghi
roots, pf, hop, deps = dung(noi_dung={"dich0": MOI})
ap(deps)
du_bang_chung(deps)
het_gio(deps)
tick(deps)
t0 = next(t for t in canary(deps)["targets"] if t["root"].endswith("dich0"))
check("đích đã bằng ứng viên từ trước: already, ghi rõ KHÔNG có receipt nên không đủ căn cứ khôi phục",
      t0["state"] == "already" and t0.get("co_receipt") is False and not t0.get("backup"), t0)
t1 = next(t for t in canary(deps)["targets"] if t["root"].endswith("dich1"))
check("đích do chính lần này ghi: promoted, có receipt và sao lưu", t1["state"] == "promoted" and t1.get("co_receipt") is True and t1.get("backup"), t1)

# ============================================================
# 4. Kiểm phiên bản ở NGUỒN: review hash này thì không ghi lên nguồn đã đổi
# ============================================================
roots, pf, hop, deps = dung(dich=())
# tick đầu: chỉ nhìn thấy đề xuất, chưa đủ điều kiện áp (verdict còn keep) -> chỉ đóng dấu bản nguồn đã thấy
txt = pf.read_text(encoding="utf-8")
pf.write_text(txt.replace("verdict: win", "verdict: keep"), encoding="utf-8")
ap(deps)
dau = [ln for ln in pf.read_text(encoding="utf-8").split("\n") if ln.startswith("reviewed_source_hash:")]
check("lần đầu thấy đề xuất, host đóng dấu SHA-256 đầy đủ của bản nguồn đã thấy", len(dau) == 1 and dau[0].split(":", 1)[1].strip() == sha(GOC), dau)
(roots["nguon"] / REL).write_text(RIENG, encoding="utf-8")          # chủ sửa nguồn SAU lần xem đó
pf.write_text(pf.read_text(encoding="utf-8").replace("verdict: keep", "verdict: win"), encoding="utf-8")
rep = ap(deps)
check("nguồn đã đổi sau khi được xem: KHÔNG ghi đè (stale), đề xuất chờ chủ, nêu lý do",
      rep["applied"] == 0 and doc(roots, "nguon") == RIENG and "cho_chu_duyet" in pf.read_text(encoding="utf-8") and any("đã đổi" in t for t in hop), (rep, hop))

roots, pf, hop, deps = dung(dich=())
ap(deps)
check("nguồn không đổi từ lúc xem: vẫn áp bình thường (cổng phiên bản không chặn oan)", doc(roots, "nguon") == MOI)

# ============================================================
# 5. Canary cũ (trước 1.3.42) chưa có baseline: không đoán, lấy sao lưu làm gốc chung
# ============================================================
roots, pf, hop, deps = dung(noi_dung={"dich1": RIENG})
ap(deps)
st = factory._load_state(deps)
cc = st["canaries"][0]
for k in ("source_baseline_hash", "candidate_hash", "deployment_id", "schema_version"):
    cc.pop(k, None)
for t in cc["targets"]:
    t.pop("quan_he", None)
    t.pop("target_observed_hash", None)
    t["state"] = "pending"
factory._save_state(deps, st)
du_bang_chung(deps)
het_gio(deps)
tick(deps)
q = {pathlib.Path(t["root"]).name: t["state"] for t in canary(deps)["targets"]}
check("bản ghi cũ thiếu trường mới vẫn chạy an toàn: đích khác bản sao lưu nguồn là conflict/override, không bị đè",
      doc(roots, "dich1") == RIENG and q["dich1"] in ("conflict", "override"), q)

# ============================================================
# 6. Hồi quy: `_fm_patch` phải giữ dòng đóng `---` (lỗi có từ 1.3.38, lộ ra khi A02 bắt đầu đóng dấu đề xuất pending)
# ============================================================
goc_de_xuat = "---\ntype: proposal\nstatus: pending\nverdict: win\n---\n# Đề xuất\n\nThân giữ nguyên.\n"
v1 = factory._fm_patch(goc_de_xuat, {"status": "applied", "applied_by": "factory"})
fm1, body1 = factory._proposal_front(v1)
check("_fm_patch: sau khi đổi trạng thái vẫn đọc lại được frontmatter và thân bài còn nguyên",
      isinstance(fm1, dict) and fm1["status"] == "applied" and fm1["applied_by"] == "factory" and "Thân giữ nguyên." in body1, (v1, fm1))
v2 = factory._fm_patch(v1, {"status": "cho_chu_duyet", "ly_do_cho": "thử"})
fm2, body2 = factory._proposal_front(v2)
check("_fm_patch: vá liên tiếp nhiều lần vẫn đọc được, không nhân đôi khoá", isinstance(fm2, dict) and fm2["status"] == "cho_chu_duyet"
      and v2.count("status:") == 1 and v2.count("\n---\n") >= 1 and body2.strip().endswith("Thân giữ nguyên."), v2)
check("_fm_patch: dòng đóng nằm đúng một lần trước thân bài", v2.split("\n").count("---") == 2, v2)
roots, pf, hop, deps = dung(dich=(), nhap=GOC.replace("role: Thu", "role: Chi"))     # đổi hành vi: bị chặn, đề xuất bị vá trạng thái
ap(deps)
fm3, _ = factory._proposal_front(pf.read_text(encoding="utf-8"))
check("đề xuất bị chuyển trạng thái qua pipeline thật vẫn đọc lại được sau đó", isinstance(fm3, dict) and fm3.get("status") == "cho_chu_duyet" and fm3.get("reviewed_source_hash"), fm3)
rep2 = ap(deps)
check("quét lần hai không làm hỏng gì, đề xuất đã chờ chủ không bị xử lý lại", rep2["scanned"] == 0 and rep2["applied"] == 0, rep2)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
