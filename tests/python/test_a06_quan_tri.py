"""A06 (Joyce Harness, gói A): API quản trị triển khai cho chủ, an toàn ở server chứ không chỉ ẩn nút.

    python tests/run.py a06_quan_tri      (không mạng, không model; mọi file nằm trong thư mục tạm)

Kiểm: khôi phục từng đích dựa trên receipt, không đè bản đã sửa tay; không nhận đường dẫn từ client; chống làm hai lần theo
action_id; từ chối bản đã đổi (stale); yêu cầu nhân đi qua CÙNG cổng và không có nhánh ép; tài khoản nhân viên bị từ chối; chưa
đăng nhập thì 401; kết quả trả về không chứa đường dẫn tuyệt đối.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import time

STATE = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a06-state-"))
os.environ["JOYCE_STATE_DIR"] = str(STATE)
os.environ["BRAINS_DIR"] = str(pathlib.Path(tempfile.mkdtemp(prefix="joyce-a06-brains-")))

import factory  # noqa: E402
import factory_admin as fa  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


factory.telemetry_ready = lambda *a, **k: True
THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nupdated: 2026-10-01\n---\n" + THAN
MOI = GOC.replace("2026-10-01", "2026-10-28")
REL = "agents/tro-ly-a.md"


class Kho:
    def __init__(self):
        self.t = []

    def list_tasks(self, root, include_archived=False, limit=400):
        return list(self.t)


def dung(so_dich=2, xong=True):
    """Canary thật qua pipeline, rồi (xong=True) nhân đủ để mọi đích promoted có receipt."""
    b = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a06-"))
    roots = {"nguon": b / "nguon"}
    for i in range(so_dich):
        roots[f"dich{i}"] = b / f"dich{i}"
    for r in roots.values():
        (r / "agents").mkdir(parents=True)
        (r / "Joyce" / "proposals").mkdir(parents=True)
        (r / REL).write_text(GOC, encoding="utf-8", newline="")
    (roots["nguon"] / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
    (roots["nguon"] / "Joyce" / "proposals" / "2026-10-28-de-xuat.md").write_text(
        "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + REL + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + MOI + "```\n", encoding="utf-8")
    hop = []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=Kho(), enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda bb, n: [], settings_get=lambda: {}, state_dir=STATE)
    for p in STATE.glob("factory-state.json"):
        p.unlink()
    asyncio.run(factory.proposal_tick(deps))
    if xong:
        deps.store.t = [{"id": f"t{i}", "status": "done", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1, "updated_at": time.time() + 2}
                        for i in range(25)]
        st = factory._load_state(deps)
        st["canaries"][0]["promote_at"] = 0
        factory._save_state(deps, st)
        asyncio.run(factory.canary_tick(deps))
    return roots, deps


def c0(deps):
    return factory._load_state(deps)["canaries"][0]


def doc(roots, ten):
    return (roots[ten] / REL).read_text(encoding="utf-8")


def hanh_dong(deps, action, c, tid="", rev=None, aid=None, reason="lý do thử", **kw):
    return fa.thuc_hien(deps, action, canary_id=c["id"], target_id=tid, expected_revision=(factory._sha256(MOI) if rev is None else rev),
                        action_id=aid or ("a-" + os.urandom(6).hex()), reason=reason, **kw)


# ============================================================
# 1. Trạng thái cho giao diện
# ============================================================
roots, deps = dung()
c = c0(deps)
check("(chuẩn bị) canary đã nhân xong, mọi đích promoted có receipt", c["state"] == "promoted" and all(t["state"] == "promoted" and t["co_receipt"] for t in c["targets"]), c["state"])
ts = fa.trang_thai(deps)
d0 = ts["canaries"][0]
check("trạng thái liệt kê canary, nguồn đang chạy bản mới, từng đích kèm khả năng khôi phục",
      d0["state"] == "promoted" and d0["nguon_chay"] == "ban_moi" and len(d0["dich"]) == 2 and all(x["co_the_khoi_phuc"] for x in d0["dich"]) and d0["nguon_co_the_khoi_phuc"], d0)
check("trạng thái KHÔNG chứa đường dẫn tuyệt đối của máy (chỉ tên brain và đường dẫn tương đối)",
      str(STATE) not in json.dumps(ts, ensure_ascii=False) and not any(str(r) in json.dumps(ts, ensure_ascii=False) for r in roots.values()), "")
check("telemetry_ready đi kèm để UI không hiện xanh khi thiếu dữ liệu", "telemetry_ready" in ts and ts["tam_dung"] is False)

# ============================================================
# 2. Khôi phục từng đích
# ============================================================
tid0 = d0["dich"][0]["target_id"]
http, kq = hanh_dong(deps, "restore", c, tid0, aid="khoi-phuc-dich-0")
check("khôi phục một đích: ghi lại BẢN CŨ đúng từng byte, chỉ đích đó", http == 200 and kq["ok"] and doc(roots, "dich0") == GOC and doc(roots, "dich1") == MOI and doc(roots, "nguon") == MOI, (http, kq))
check("đích đã khôi phục được đánh dấu restored, không còn đề nghị khôi phục lần nữa", fa.trang_thai(deps)["canaries"][0]["dich"][0]["restored"] is True)
n_bak = len(list((roots["dich0"] / "Joyce" / "proposals" / ".backup").glob("*.bak")))
http2, kq2 = hanh_dong(deps, "restore", c, tid0, aid="khoi-phuc-dich-0")
check("cùng action_id bấm lại (double click, retry sau timeout): trả đúng kết quả cũ, KHÔNG làm lần hai", http2 == 200 and kq2.get("lap_lai") is True
      and len(list((roots["dich0"] / "Joyce" / "proposals" / ".backup").glob("*.bak"))) == n_bak)

http, kq = hanh_dong(deps, "restore", c, "nguon", aid="khoi-phuc-nguon")
check("khôi phục NGUỒN: nguồn về bản cũ, hiển thị nguồn đã khôi phục", http == 200 and doc(roots, "nguon") == GOC and fa.trang_thai(deps)["canaries"][0]["nguon_chay"] == "da_khoi_phuc", (http, kq))

# ---------------- sửa tay sau triển khai: conflict, không ghi đè
roots, deps = dung()
c = c0(deps)
tid1 = fa.trang_thai(deps)["canaries"][0]["dich"][1]["target_id"]
(roots["dich1"] / REL).write_text(MOI + "\nCHỦ VỪA SỬA TAY\n", encoding="utf-8", newline="")
http, kq = hanh_dong(deps, "restore", c, tid1)
check("khôi phục khi file đã bị sửa tay sau triển khai: CONFLICT, KHÔNG ghi đè bản của chủ", http == 409 and kq.get("conflict") and "CHỦ VỪA SỬA TAY" in doc(roots, "dich1"), (http, kq))
h, d = fa.diff_dich(deps, c["id"], tid1)
check("diff của đích bị sửa tay cho chủ thấy cái sẽ mất: có dòng của chủ, đường dẫn tương đối", h == 200 and "CHỦ VỪA SỬA TAY" in d["diff"] and d["brain"] == "dich1" and str(roots["dich1"]) not in d["diff"], d)

# ---------------- bản sao lưu bị sửa/hỏng
roots, deps = dung()
c = c0(deps)
t = fa.trang_thai(deps)["canaries"][0]["dich"][0]
bk = pathlib.Path(c0(deps)["targets"][0]["backup"])
bk.write_text("BẢN SAO LƯU BỊ THAY", encoding="utf-8", newline="")
http, kq = hanh_dong(deps, "restore", c, t["target_id"])
check("bản sao lưu bị sửa (hash không khớp nhật ký): KHÔNG ghi gì", http == 409 and doc(roots, "dich0") == MOI, (http, kq))
bk.unlink()
http, kq = hanh_dong(deps, "restore", c, t["target_id"])
check("bản sao lưu mất: KHÔNG ghi gì, nói rõ", http == 409 and doc(roots, "dich0") == MOI, (http, kq))

# ---------------- đích không có receipt
roots, deps = dung()
st = factory._load_state(deps)
st["canaries"][0]["targets"][0]["co_receipt"] = False
st["canaries"][0]["targets"][0]["state"] = "already"
factory._save_state(deps, st)
c = c0(deps)
http, kq = hanh_dong(deps, "restore", c, fa._tid(c["targets"][0]["root"]))
check("đích 'already' không có receipt: KHÔNG đủ căn cứ để khôi phục, từ chối", http == 409 and "receipt" in kq.get("error", ""), (http, kq))

# ============================================================
# 3. Chống giả mạo và đổi phiên bản
# ============================================================
roots, deps = dung()
c = c0(deps)
for xau in ("../../../etc/passwd", str(roots["dich0"]), "C:\\Windows\\System32", "khong-co-id"):
    http, kq = hanh_dong(deps, "restore", c, xau)
    check(f"target_id giả '{xau[:28]}': 404, không ghi, không đọc đường dẫn do client đưa", http == 404 and doc(roots, "dich0") == MOI, (http, kq))
http, kq = hanh_dong(deps, "restore", c, "nguon", rev="0" * 64)
check("expected_revision sai (canary đã đổi kể từ lúc chủ xem): stale, KHÔNG làm theo hình cũ", http == 409 and kq.get("stale") and doc(roots, "nguon") == MOI, (http, kq))
http, kq = fa.thuc_hien(deps, "restore", canary_id=c["id"], target_id="nguon", expected_revision=factory._sha256(MOI), action_id="ab", reason="đủ dài")
check("thiếu action_id hợp lệ: 400", http == 400)
http, kq = fa.thuc_hien(deps, "restore", canary_id=c["id"], target_id="nguon", expected_revision=factory._sha256(MOI), action_id="x" * 12, reason=" ")
check("thiếu lý do: 400", http == 400)
http, kq = fa.thuc_hien(deps, "xoa-het", canary_id=c["id"], expected_revision="", action_id="x" * 12, reason="đủ dài")
check("thao tác lạ: 400", http == 400)
http, kq = hanh_dong(deps, "restore", {"id": "khong-co"}, "nguon")
check("canary không tồn tại: 404", http == 404)

# ============================================================
# 4. Yêu cầu nhân: cùng cổng với tự nhân, không có nhánh ép
# ============================================================
roots, deps = dung(xong=False)
c = c0(deps)
factory.telemetry_ready = lambda *a, **k: False
http, kq = hanh_dong(deps, "promote", c)
check("yêu cầu nhân khi chưa có telemetry: từ chối và LIỆT KÊ điều kiện thiếu (telemetry, bằng chứng)",
      http == 409 and any("telemetry" in x for x in kq["dieu_kien_thieu"]) and any("việc đã chạy" in x for x in kq["dieu_kien_thieu"]) and doc(roots, "dich0") == GOC, kq)
factory.telemetry_ready = lambda *a, **k: True
deps.store.t = [{"id": f"t{i}", "status": "done", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1, "updated_at": time.time() + 2} for i in range(25)]
st = factory._load_state(deps)
st["canaries"][0]["promote_at"] = 0
factory._save_state(deps, st)
http, kq = hanh_dong(deps, "promote", c0(deps))
check("DÙ đủ mọi điều kiện, gói A không có nút ép nhân thủ công: vẫn không ghi đích", http == 409 and doc(roots, "dich0") == GOC, kq)

roots, deps = dung(xong=False)
st = factory._load_state(deps)
st["tam_dung"] = True
factory._save_state(deps, st)
check("đang tạm dừng: điều kiện nhân nêu rõ tạm dừng", any("tạm dừng" in x for x in fa.dieu_kien_nhan(deps, c0(deps))))

# ============================================================
# 5. Đã đọc và tạm dừng
# ============================================================
roots, deps = dung(xong=False)
c = c0(deps)
http, kq = hanh_dong(deps, "ack", c, reason="đã đọc, để đó")
check("ack: ghi nhận đã đọc, trạng thái canary KHÔNG đổi, nói rõ không phải đạt chất lượng",
      http == 200 and c0(deps)["acknowledged"]["ly_do"] == "đã đọc, để đó" and c0(deps)["state"] == "canary" and "KHÔNG" in kq["ghi_chu"], kq)
http, kq = fa.thuc_hien(deps, "pause", on=True, action_id="tam-dung-1", reason="kiểm tra")
check("pause bật: lưu vào state, trạng thái trả về phản ánh", http == 200 and fa.trang_thai(deps)["tam_dung"] is True)
http, kq = fa.thuc_hien(deps, "pause", on=False, action_id="tam-dung-2", reason="xong")
check("pause tắt lại được", http == 200 and fa.trang_thai(deps)["tam_dung"] is False)
check("nhật ký quản trị ghi người làm và lý do", [x["action"] for x in factory._load_state(deps)["nhat_ky_quan_tri"]][-2:] == ["pause", "pause"])

# ============================================================
# 6. Qua HTTP thật: phân quyền
# ============================================================
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import config as cfgmod  # noqa: E402

c_http = TestClient(main.app, base_url="http://127.0.0.1:8080")
check("GET /work/factory trả thêm khóa deployments (tương thích ngược: khóa cũ vẫn còn)",
      (lambda r: r.status_code == 200 and "deployments" in r.json() and "stages" in r.json() and "autonomy" in r.json())(c_http.get("/work/factory")))


class GiaYeuCau:
    class state:
        staff = {"ten": "nhân viên"}


check("tài khoản nhân viên bị từ chối ở chính route (403), không chỉ ẩn nút", main._chi_chu(GiaYeuCau).status_code == 403)


class GiaChu:
    class state:
        pass


check("chủ được qua", main._chi_chu(GiaChu) is None)
_gate = cfgmod.gate_active
cfgmod.gate_active = lambda: True
try:
    ngoai = TestClient(main.app, base_url="https://joyce.example.vn")
    for m, u in (("get", "/work/factory/diff?canary_id=x&target_id=y"), ("post", "/work/factory/action")):
        check(f"đã bật đăng nhập: {u.split('?')[0]} chưa đăng nhập thì 401", getattr(ngoai, m)(u).status_code == 401)
    loc = TestClient(main.app, base_url="http://127.0.0.1:8080")
    check("công cụ gọi từ localhost KHÔNG cookie cũng bị 401 (route không nằm trong danh sách miễn của localhost)",
          loc.post("/work/factory/action", data={"action": "pause"}).status_code == 401)
finally:
    cfgmod.gate_active = _gate
check("route quản trị không nằm trong danh sách công khai hay miễn localhost của main",
      not any(p.startswith("/work/factory") for p in main._AUTH_PUBLIC_EXACT + main._AUTH_PUBLIC_PREFIX + main._AUTH_LOCAL_EXACT))

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
