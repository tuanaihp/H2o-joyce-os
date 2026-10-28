"""B02 (gói B): chủ chấm một lượt chạy là đạt hoặc rớt; đó là đường hợp lệ để lượt thành bằng chứng canary.

    python tests/run.py b02_cham_luot      (không mạng, không model)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

STATE = pathlib.Path(tempfile.mkdtemp(prefix="joyce-b02g-state-"))
os.environ["JOYCE_STATE_DIR"] = str(STATE)

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


deps = factory.FactoryDeps(brains=lambda: [], task_root=lambda n: "", store=None, enqueue=None, loops=None,
                           workflows_dir=lambda x: pathlib.Path(x), inbox=None, incidents_list=lambda bb, n: [],
                           settings_get=lambda: {}, state_dir=STATE)


def lượt(status="completed", ver="unverified", rev="a" * 64):
    rid = os.urandom(6).hex()
    L.bat_dau(brain_id="b", agent_id="tro-ly", entrypoint="task", run_id=rid, revision={"agent_revision": rev})
    L.ket_thuc(rid, status, verification=ver)
    return rid


a = lượt()
check("danh sách chờ chấm có lượt hoàn tất chưa chấm, chỉ metadata, không lộ nội dung",
      [x["run_id"] for x in fa.luot_can_cham()] == [a] and set(fa.luot_can_cham()[0]) == {"run_id", "brain", "agent", "cua", "ref", "luc", "ban"})
check("trạng thái quản trị mang theo danh sách chờ chấm", [x["run_id"] for x in fa.trang_thai(deps)["luot_can_cham"]] == [a])

check("kết quả lạ bị từ chối", fa.cham_luot(deps, a, "xong", "lý do thử")[0] == 400)
check("thiếu lý do bị từ chối", fa.cham_luot(deps, a, "pass", "")[0] == 400)
check("lượt không tồn tại: 404", fa.cham_luot(deps, "khong-co", "pass", "lý do thử")[0] == 404)

h, kq = fa.cham_luot(deps, a, "pass", "đã đọc kết quả, đúng")
check("chấm đạt: lượt thành verified_pass, có dấu vết người chấm", h == 200 and L.lay(a)["verification_status"] == "verified_pass"
      and L.lay(a)["evidence_refs"] == ["owner:chu"], (h, kq))
h2, kq2 = fa.cham_luot(deps, a, "fail", "đổi ý")
check("chấm rồi thì KHÔNG đổi lại bằng đường này (409), kết quả cũ còn nguyên", h2 == 409 and L.lay(a)["verification_status"] == "verified_pass", (h2, kq2))
check("lượt đã chấm biến khỏi danh sách chờ", fa.luot_can_cham() == [])

b = lượt()
h3, _ = fa.cham_luot(deps, b, "fail", "sai nghiệp vụ")
check("chấm rớt: verified_fail", h3 == 200 and L.lay(b)["verification_status"] == "verified_fail")

c = lượt(status="failed")
check("lượt lỗi không chấm đạt được", fa.cham_luot(deps, c, "pass", "thử")[0] == 409 and L.lay(c)["verification_status"] == "unverified")
d = L.bat_dau(brain_id="b", agent_id="tro-ly", entrypoint="task")
check("lượt đang chạy không chấm được", fa.cham_luot(deps, d, "pass", "thử")[0] == 409)

st = factory._load_state(deps)
nk = [x for x in st.get("nhat_ky_quan_tri", []) if x.get("action") == "cham_luot"]
check("nhật ký quản trị ghi cả hai lần chấm với người, lý do, run_id", len(nk) == 2 and nk[0]["run_id"] == a and nk[0]["nguoi"] == "chu" and nk[1]["ket_qua"] == "fail", nk)

# route: chỉ chủ
import main  # noqa: E402
req_nv = SimpleNamespace(state=SimpleNamespace(staff={"id": "nv1"}))
req_chu = SimpleNamespace(state=SimpleNamespace())
check("nhân viên bị từ chối ở route (403)", main._chi_chu(req_nv).status_code == 403)
check("chủ qua được", main._chi_chu(req_chu) is None)
rs = [r for r in main.app.routes if getattr(r, "path", "") == "/work/factory/grade"]
check("route /work/factory/grade có đăng ký, chỉ POST", len(rs) == 1 and rs[0].methods == {"POST"})
check("route không nằm trong danh sách công khai hay miễn đăng nhập cục bộ",
      "/work/factory/grade" not in main._AUTH_PUBLIC_EXACT and "/work/factory/grade" not in main._AUTH_LOCAL_EXACT
      and not any("/work/factory/grade".startswith(x) for x in main._AUTH_PUBLIC_PREFIX))

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b02_cham_luot: tất cả pass")
