"""A05 (Joyce Harness, gói A): writer chung, khoá liên tiến trình, nhật ký trước ghi, phục hồi sau crash.

    python tests/run.py a05_writer      (không mạng, không model; mọi file nằm trong thư mục tạm, có tiến trình con thật)

Không kiểm "trạng thái trả về" mà kiểm BYTES cuối cùng trên đĩa và nhật ký, theo yêu cầu của plan: hai tiến trình thật cùng sửa
một đích; hai tiến trình thật cùng cập nhật state; chết trước/sau từng bước ghi; sao lưu hỏng; hai file cùng stem cùng giây;
skill nằm sâu; link symlink/junction ở cha và lá; editor sửa trước lúc lật lại.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time

import deploy_writer as dw  # noqa: E402
import factory  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def moi():
    base = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a05-"))
    goc = base / "brain"
    (goc / "agents").mkdir(parents=True)
    return base, goc, base / "khoa"


BAN_CU, BAN_MOI = "---\ntype: agent\nname: A\n---\nbản cũ\n", "---\ntype: agent\nname: A\n---\nbản mới\n"
PY = sys.executable


def chay_con(code, **env):
    e = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", **env)
    return subprocess.run([PY, "-c", textwrap.dedent(code)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=e, timeout=120)


DAU = f"import sys; sys.path.insert(0, {str(SERVER)!r})\nimport deploy_writer as dw\nfrom pathlib import Path\n"

# ============================================================
# 1. Ghi cơ bản: bytes xác định, nhật ký, sao lưu
# ============================================================
base, goc, kh = moi()
f = goc / "agents" / "a.md"
f.write_bytes(BAN_CU.encode("utf-8"))
rc = dw.ghi_co_dieu_kien(goc, f, BAN_MOI, thu_muc_khoa=kh, deployment_id="d" * 32, target_id="t" * 32, truoc_hash=sha(BAN_CU))
check("ghi có điều kiện: committed, bytes trên đĩa ĐÚNG bằng bản mới (không bị Windows đổi \\n thành \\r\\n)",
      rc["ket_qua"] == "committed" and f.read_bytes() == BAN_MOI.encode("utf-8"), (rc, f.read_bytes()[:60]))
bp = pathlib.Path(rc["backup"])
check("sao lưu nằm dưới <gốc>/Joyce/proposals/.backup, tên theo deployment và target, nội dung = bản cũ, hash khớp",
      bp.parent == goc / "Joyce" / "proposals" / ".backup" and bp.name == "a-dddddddd-tttttttt.bak" and bp.read_text(encoding="utf-8") == BAN_CU and rc["backup_hash"] == sha(BAN_CU), rc)
nk = dw.doc_receipt(goc, "d" * 32, "t" * 32)
check("nhật ký committed có before, after, backup", nk and nk["trang_thai"] == "committed" and nk["truoc_hash"] == sha(BAN_CU) and nk["sau_hash"] == sha(BAN_MOI), nk)
check("không để lại tệp tạm", not list((goc / "agents").glob("*.tmp*")))
rc2 = dw.ghi_co_dieu_kien(goc, f, "x", thu_muc_khoa=kh, deployment_id="e" * 32, target_id="t" * 32, truoc_hash=sha(BAN_CU))
check("so-rồi-ghi: hash mong đợi đã cũ thì conflict, KHÔNG ghi gì", rc2["ket_qua"] == "conflict" and f.read_bytes() == BAN_MOI.encode("utf-8"))
rc3 = dw.ghi_co_dieu_kien(goc, goc / "agents" / "khong-co.md", "x", thu_muc_khoa=kh, deployment_id="f" * 32, target_id="t" * 32, truoc_hash=sha("a"))
check("đích không còn: missing, KHÔNG tạo mới", rc3["ket_qua"] == "missing" and not (goc / "agents" / "khong-co.md").exists())

# ============================================================
# 2. Hai TIẾN TRÌNH thật cùng sửa một đích từ cùng một hash
# ============================================================
base, goc, kh = moi()
f = goc / "agents" / "a.md"
f.write_text(BAN_CU, encoding="utf-8", newline="")
mot = DAU + f"""
import sys, time
ten = sys.argv[1]
while time.time() < float(sys.argv[2]): time.sleep(0.001)      # vạch xuất phát chung để hai tiến trình đụng nhau thật
rc = dw.ghi_co_dieu_kien(Path({str(goc)!r}), Path({str(f)!r}), "---\\ntype: agent\\nname: A\\n---\\nbản của " + ten + "\\n", thu_muc_khoa=Path({str(kh)!r}),
    deployment_id=ten * 32, target_id="t" * 32, truoc_hash={sha(BAN_CU)!r})
print("KQ=" + rc["ket_qua"])
"""
xuat_phat = time.time() + 3.0
tp = [subprocess.Popen([PY, "-c", mot, t, str(xuat_phat)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONUTF8="1")) for t in ("x", "y")]
kq = [p.communicate(timeout=120)[0] for p in tp]
ket = sorted(l.split("=")[1] for o in kq for l in o.splitlines() if l.startswith("KQ="))
noi = f.read_bytes().decode("utf-8")
check("hai tiến trình thật cùng sửa từ một hash: ĐÚNG MỘT committed, một conflict (không bản nào bị đè âm thầm)", ket == ["committed", "conflict"], (ket, kq))
check("bytes cuối cùng là của bên thắng, nguyên vẹn, không lẫn", noi in ("---\ntype: agent\nname: A\n---\nbản của x\n", "---\ntype: agent\nname: A\n---\nbản của y\n"), noi)
check("chỉ MỘT bản sao lưu được tạo (bên thua không ghi gì)", len(list((goc / "Joyce" / "proposals" / ".backup").glob("*.bak"))) == 1)

# ============================================================
# 3. Hai tiến trình thật cập nhật state: không mất cập nhật
# ============================================================
base, goc, kh = moi()
st_dir = base / "state"
st_dir.mkdir()
code_state = DAU + f"""
import sys, time
sys.path.insert(0, {str(SERVER)!r})
import factory
ten, tg = sys.argv[1], float(sys.argv[2])
while time.time() < tg: time.sleep(0.001)
class D: pass
d = D(); d.state_dir = Path({str(st_dir)!r}); d.atomic_write_text = None
for i in range(15):
    with factory._khoa_state(d):
        st = factory._load_state(d)
        st["canaries"].append({{"id": ten + str(i), "state": "canary"}})
        factory._save_state(d, st)
print("XONG")
"""
xp = time.time() + 3.0
tp = [subprocess.Popen([PY, "-c", code_state, t, str(xp)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONUTF8="1")) for t in ("p", "q")]
outs = [p.communicate(timeout=180) for p in tp]
st = json.loads((st_dir / "factory-state.json").read_text(encoding="utf-8"))
ids = sorted(c["id"] for c in st["canaries"])
check("hai tiến trình thật mỗi bên thêm 15 canary vào state: đủ 30, không mất cập nhật nào", len(ids) == 30 and len(set(ids)) == 30, (len(ids), outs[0][1][-200:], outs[1][1][-200:]))

# ============================================================
# 4. Tiến trình chết GIỮ khoá: hệ điều hành nhả, không để khoá mồ côi
# ============================================================
base, goc, kh = moi()
f = goc / "agents" / "a.md"
f.write_text(BAN_CU, encoding="utf-8", newline="")
r = chay_con(DAU + f"""
import os
cm = dw.khoa(Path({str(kh)!r}), {str(f)!r})
cm.__enter__()
print("DANG_GIU", flush=True)
os._exit(0)            # chết mà KHÔNG nhả khoá
""")
t0 = time.time()
rc = dw.ghi_co_dieu_kien(goc, f, BAN_MOI, thu_muc_khoa=kh, deployment_id="g" * 32, target_id="t" * 32, truoc_hash=sha(BAN_CU))
check("tiến trình giữ khoá chết đột ngột: tiến trình khác lấy được khoá ngay (không chờ hết giờ)", "DANG_GIU" in r.stdout and rc["ket_qua"] == "committed" and time.time() - t0 < 10, (r.stdout, r.stderr[-200:], time.time() - t0))

# Hai tiến trình cùng tạo file khoá lần đầu: bên kia đã khoá byte 0 của file RỖNG thì bên này không được nổ PermissionError khi
# ghi byte khởi tạo (lỗi thật gặp khi 10 lần chạy song song trên Windows), mà phải chờ rồi hết giờ một cách có kiểm soát.
base, goc, kh = moi()
f = goc / "agents" / "a.md"
kh.mkdir(parents=True, exist_ok=True)
tep_khoa = dw._khoa_file(kh, os.path.normcase(str(f)))
giu = subprocess.Popen([PY, "-c", f"""
import os, sys, time
fd = os.open({str(tep_khoa)!r}, os.O_RDWR | os.O_CREAT, 0o600)
try:
    import msvcrt
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
except ImportError:
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
print("DA_KHOA", flush=True)
time.sleep(6)
"""], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
try:
    dong = giu.stdout.readline()
    try:
        with dw.khoa(kh, str(f), het_gio=1.0):
            loi_khoa = "lấy được khoá đang bị giữ"
    except dw.HetGioKhoa:
        loi_khoa = "het_gio"
    except OSError as e:
        loi_khoa = "OSError: " + repr(e)
finally:
    giu.kill()
    giu.wait()
check("file khoá rỗng đã bị tiến trình khác khoá byte 0: chờ rồi hết giờ có kiểm soát, KHÔNG nổ PermissionError khi ghi byte khởi tạo",
      "DA_KHOA" in dong and loi_khoa == "het_gio", (dong, loi_khoa))

# ============================================================
# 5. Chết giữa chừng ở từng bước + đối soát
# ============================================================
class Chet(BaseException):
    pass


def chet_o(buoc):
    def hook(b):
        if b == buoc:
            raise Chet()
    return hook


def thu_chet(buoc, sau_do=None):
    base, goc, kh = moi()
    f = goc / "agents" / "a.md"
    f.write_text(BAN_CU, encoding="utf-8", newline="")
    try:
        dw.ghi_co_dieu_kien(goc, f, BAN_MOI, thu_muc_khoa=kh, deployment_id="h" * 32, target_id="t" * 32, truoc_hash=sha(BAN_CU), dung_tai=chet_o(buoc))
    except Chet:
        pass
    if sau_do:
        sau_do(goc, f)
    ds = dw.doi_soat(goc, thu_muc_khoa=kh)
    return goc, f, kh, ds


goc, f, kh, ds = thu_chet("sau_sao_luu")
check("chết SAU sao lưu, TRƯỚC nhật ký: file nguyên bản cũ, không có nhật ký để đối soát", f.read_text(encoding="utf-8") == BAN_CU and ds == [], ds)
rc = dw.ghi_co_dieu_kien(goc, f, BAN_MOI, thu_muc_khoa=kh, deployment_id="h" * 32, target_id="t" * 32, truoc_hash=sha(BAN_CU))
check("chạy lại cùng triển khai sau khi chết ở bước đó: dùng lại sao lưu cũ (đúng nội dung), ghi thành công", rc["ket_qua"] == "committed" and f.read_text(encoding="utf-8") == BAN_MOI)

goc, f, kh, ds = thu_chet("sau_nhat_ky")
check("chết SAU nhật ký prepared, TRƯỚC khi ghi: file nguyên bản cũ; đối soát nhận ra chưa ghi và HUỶ nhật ký", f.read_text(encoding="utf-8") == BAN_CU and [x["viec"] for x in ds] == ["huy"], ds)
check("nhật ký sau đối soát ở trạng thái huy", dw.doc_receipt(goc, "h" * 32, "t" * 32)["trang_thai"] == "huy")

goc, f, kh, ds = thu_chet("sau_ghi")
check("chết SAU khi ghi, TRƯỚC khi chốt: file đã là bản mới; đối soát HOÀN TẤT nhật ký thành committed (có căn cứ nhật ký)",
      f.read_text(encoding="utf-8") == BAN_MOI and [x["viec"] for x in ds] == ["hoan_tat"] and dw.doc_receipt(goc, "h" * 32, "t" * 32)["trang_thai"] == "committed", ds)

goc, f, kh, ds = thu_chet("sau_nhat_ky", sau_do=lambda g, ff: ff.write_text("NGƯỜI KHÁC VỪA SỬA", encoding="utf-8", newline=""))
check("chết sau nhật ký rồi có NGƯỜI KHÁC sửa file: đối soát báo xung đột, KHÔNG đè và KHÔNG coi là của mình",
      f.read_text(encoding="utf-8") == "NGƯỜI KHÁC VỪA SỬA" and [x["viec"] for x in ds] == ["xung_dot"], ds)

# file bằng bản mới nhưng KHÔNG có nhật ký: không coi là do mình ghi
base, goc, kh = moi()
f = goc / "agents" / "a.md"
f.write_text(BAN_MOI, encoding="utf-8", newline="")
check("file đã bằng bản mới mà không có nhật ký nào: đối soát không nhận là của mình", dw.doi_soat(goc, thu_muc_khoa=kh) == [])

# ============================================================
# 6. Sao lưu: hỏng, mất, trùng tên
# ============================================================
base, goc, kh = moi()
f = goc / "agents" / "a.md"
f.write_text(BAN_CU, encoding="utf-8", newline="")
bp = dw.ten_sao_luu(goc, f, "i" * 32, "t" * 32)
bp.parent.mkdir(parents=True)
bp.write_text("MỘT BẢN SAO LƯU SAI NỘI DUNG", encoding="utf-8")
try:
    dw.ghi_co_dieu_kien(goc, f, BAN_MOI, thu_muc_khoa=kh, deployment_id="i" * 32, target_id="t" * 32, truoc_hash=sha(BAN_CU))
    loi = None
except OSError as e:
    loi = e
check("bản sao lưu cùng tên đã có mà SAI nội dung: từ chối ghi (không ghi khi chưa chắc cứu được), file nguyên vẹn",
      loi is not None and f.read_text(encoding="utf-8") == BAN_CU and bp.read_text(encoding="utf-8") == "MỘT BẢN SAO LƯU SAI NỘI DUNG", loi)

base, goc, kh = moi()
(goc / "skills" / "a").mkdir(parents=True)
(goc / "skills" / "b").mkdir(parents=True)
fa, fb = goc / "skills" / "a" / "SKILL.md", goc / "skills" / "b" / "SKILL.md"
fa.write_text("a cũ", encoding="utf-8", newline="")
fb.write_text("b cũ", encoding="utf-8", newline="")
ra = dw.ghi_co_dieu_kien(goc, fa, "a mới", thu_muc_khoa=kh, deployment_id="j" * 32, target_id=hashlib.sha256(b"a").hexdigest(), truoc_hash=sha("a cũ"))
rb = dw.ghi_co_dieu_kien(goc, fb, "b mới", thu_muc_khoa=kh, deployment_id="j" * 32, target_id=hashlib.sha256(b"b").hexdigest(), truoc_hash=sha("b cũ"))
check("hai file CÙNG stem (SKILL) ghi trong cùng một giây: hai sao lưu KHÁC tên, mỗi cái đúng nội dung của nó",
      ra["backup"] != rb["backup"] and pathlib.Path(ra["backup"]).read_text(encoding="utf-8") == "a cũ" and pathlib.Path(rb["backup"]).read_text(encoding="utf-8") == "b cũ", (ra["backup"], rb["backup"]))
check("skill lồng sâu: sao lưu nằm dưới gốc brain/Joyce/proposals/.backup, KHÔNG nằm trong skills/Joyce",
      pathlib.Path(ra["backup"]).parent == goc / "Joyce" / "proposals" / ".backup" and not (goc / "skills" / "Joyce").exists(), ra["backup"])

# ============================================================
# 7. Đường dẫn không an toàn: liên kết ở cha và ở lá, ra ngoài gốc
# ============================================================
base, goc, kh = moi()
ngoai = base / "ngoai"
ngoai.mkdir()
(ngoai / "a.md").write_text("NGOÀI GỐC", encoding="utf-8", newline="")


def tao_lk(link, dich):
    try:
        if os.name == "nt":
            return subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(dich)], capture_output=True, text=True).returncode == 0
        os.symlink(dich, link, target_is_directory=True)
        return True
    except OSError:
        return False


if tao_lk(goc / "lk", ngoai):
    try:
        dw.ghi_co_dieu_kien(goc, goc / "lk" / "a.md", "ĐÈ", thu_muc_khoa=kh, deployment_id="k" * 32, target_id="t" * 32, truoc_hash=sha("NGOÀI GỐC"))
        loi = None
    except dw.DuongKhongAnToan as e:
        loi = e
    check("thư mục cha là liên kết (junction/symlink) trỏ ra ngoài: TỪ CHỐI, file ngoài gốc nguyên vẹn",
          loi is not None and (ngoai / "a.md").read_text(encoding="utf-8") == "NGOÀI GỐC", loi)
else:
    print("skip liên kết thư mục: máy này không tạo được")
try:
    dw.duong_an_toan(goc, goc / ".." / "ngoai" / "a.md")
    loi = None
except dw.DuongKhongAnToan as e:
    loi = e
check("đường dẫn thoát ra ngoài gốc bằng ..: từ chối", loi is not None)
lk_file = goc / "agents" / "lk.md"
try:
    os.symlink(ngoai / "a.md", lk_file)
    co_symlink = True
except (OSError, NotImplementedError):
    co_symlink = False
if co_symlink:
    try:
        dw.ghi_co_dieu_kien(goc, lk_file, "ĐÈ", thu_muc_khoa=kh, deployment_id="l" * 32, target_id="t" * 32, truoc_hash=sha("NGOÀI GỐC"))
        loi = None
    except dw.DuongKhongAnToan as e:
        loi = e
    check("lá là symlink file: TỪ CHỐI", loi is not None and (ngoai / "a.md").read_text(encoding="utf-8") == "NGOÀI GỐC", loi)
else:
    print("skip symlink file: máy này thiếu quyền tạo symlink (junction thì đã thử ở trên)")

# ============================================================
# 8. Canary: giữ bản ghi đang cần, không cắt thẳng 50
# ============================================================
ds_cu = [{"id": f"kt{i}", "state": "promoted"} for i in range(60)] + [{"id": "dang", "state": "canary"}, {"id": "leg", "state": "legacy_review"},
                                                                    {"id": "mot", "state": "partial"}, {"id": "xd", "state": "conflict"}]
ds_cu.insert(5, {"id": "chen-giua", "state": "canary"})            # canary đang canh nằm ở GIỮA danh sách, không phải cuối
cat = factory._cat_canary(ds_cu)
ids = [c["id"] for c in cat]
check("cắt canary: mọi bản ghi CHƯA kết thúc (đang canh, legacy_review, partial, conflict) đều được giữ dù vượt 50",
      all(x in ids for x in ("dang", "leg", "mot", "xd", "chen-giua")), ids[:8])
check("chỉ cắt bản đã kết thúc, giữ 50 bản mới nhất", sum(1 for c in cat if c["state"] == "promoted") == 50 and "kt59" in ids and "kt0" not in ids)
check("bản cũ [-50:] sẽ làm mất canary đang canh ở giữa (chứng minh lỗi cũ có thật)", "chen-giua" not in [c["id"] for c in ds_cu[-50:]])

# ============================================================
# 9. Đường canary thật: editor sửa trước khi lật; lỗi lưu state sau khi ghi
# ============================================================
factory.telemetry_ready = lambda *a, **k: True
THAN = ("## Vai trò\n" + "Nội dung đầy đủ, có quy trình rõ ràng cho từng bước làm việc của phòng. " * 3).rstrip() + "\n"
GOC = "---\ntype: agent\nname: Trợ lý A\nupdated: 2026-10-01\n---\n" + THAN
MOI_ = GOC.replace("2026-10-01", "2026-10-28")
REL = "agents/tro-ly-a.md"


class Kho:
    def __init__(self):
        self.t = []

    def list_tasks(self, root, include_archived=False, limit=400):
        return list(self.t)


def dung_canary(so_dich=2):
    b = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a05c-"))
    roots = {"nguon": b / "nguon"}
    for i in range(so_dich):
        roots[f"dich{i}"] = b / f"dich{i}"
    for r in roots.values():
        (r / "agents").mkdir(parents=True)
        (r / "Joyce" / "proposals").mkdir(parents=True)
        (r / REL).write_text(GOC, encoding="utf-8", newline="")
    (roots["nguon"] / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
    (roots["nguon"] / "Joyce" / "proposals" / "2026-10-28-de-xuat.md").write_text(
        "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: " + REL + "\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + MOI_ + "```\n", encoding="utf-8")
    hop = []

    async def inbox(text, **kw):
        hop.append(text)

    deps = factory.FactoryDeps(brains=lambda: list(roots), task_root=lambda n: str(roots[n]), store=Kho(), enqueue=None, loops=None,
                               workflows_dir=lambda x: pathlib.Path(x) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=b)
    rep = asyncio.run(factory.proposal_tick(deps))
    assert rep["canary"] == 1, rep
    return roots, deps, hop


def san_sang(deps, bad=False):
    deps.store.t = [{"id": f"t{i}", "status": "blocked" if bad else "done", "idempotency_key": "agent:A:tro-ly-a", "created_at": time.time() + 1,
                     "updated_at": time.time() + 2} for i in range(25 if not bad else 1)]
    st = factory._load_state(deps)
    st["canaries"][0]["promote_at"] = 0
    factory._save_state(deps, st)


roots, deps, hop = dung_canary()
c = factory._load_state(deps)["canaries"][0]
check("áp nguồn qua writer chung: có nhật ký committed của lần áp, sao lưu tên duy nhất theo triển khai",
      dw.doc_receipt(roots["nguon"], c["deployment_id"], "nguon")["trang_thai"] == "committed" and pathlib.Path(c["backup"]).name.startswith("tro-ly-a-" + c["deployment_id"][:8]), c["backup"])
check("bytes file nguồn sau khi áp là bản nháp đúng từng byte", (roots["nguon"] / REL).read_bytes() == MOI_.encode("utf-8"))

# editor ngoài sửa nguồn ngay trước lúc lật lại: không đè
san_sang(deps, bad=True)
goc_bad = factory._canary_bad_signals


def sua_roi_bao(deps_, c_):
    kq = goc_bad(deps_, c_)
    (roots["nguon"] / REL).write_text("EDITOR NGOÀI VỪA SỬA", encoding="utf-8", newline="")
    return kq


factory._canary_bad_signals = sua_roi_bao
try:
    rep = asyncio.run(factory.canary_tick(deps))
finally:
    factory._canary_bad_signals = goc_bad
check("editor ngoài sửa nguồn ngay trước lúc lật lại: KHÔNG đè, canary nhường (superseded), bytes của editor còn nguyên",
      (roots["nguon"] / REL).read_text(encoding="utf-8") == "EDITOR NGOÀI VỪA SỬA" and factory._load_state(deps)["canaries"][0]["state"] == "superseded" and rep["reverted"] == 0, rep)

# lỗi lưu state SAU khi đã ghi đích: nhật ký trên đĩa vẫn còn, lần sau nhận lại đúng receipt, không thành "already" vô căn cứ
roots, deps, hop = dung_canary(so_dich=1)
san_sang(deps)
goc_save = factory._save_state
dem = {"n": 0}


def save_hong_sau_ghi(deps_, st_):
    # lần lưu đầu tiên trong nhịp nhân đích xảy ra NGAY sau khi ghi đích: giả lập đĩa đầy đúng lúc đó
    if any(t.get("state") == "promoted" for c in st_.get("canaries", []) for t in c.get("targets", [])):
        dem["n"] += 1
        raise OSError("đĩa đầy giả lập khi lưu state")
    return goc_save(deps_, st_)


factory._save_state = save_hong_sau_ghi
try:
    try:
        asyncio.run(factory.canary_tick(deps))
    except OSError:
        pass
finally:
    factory._save_state = goc_save
check("(chuẩn bị) đích ĐÃ được ghi nhưng state chưa lưu được", (roots["dich0"] / REL).read_bytes() == MOI_.encode("utf-8") and dem["n"] >= 1)
c = factory._load_state(deps)["canaries"][0]
check("state trên đĩa vẫn ghi đích là pending (mất cập nhật do lỗi lưu)", c["targets"][0]["state"] == "pending", c["targets"][0])
rep = asyncio.run(factory.canary_tick(deps))
c = factory._load_state(deps)["canaries"][0]
t0 = c["targets"][0]
check("chạy lại: nhận đúng RECEIPT của chính triển khai này (promoted, có sao lưu), KHÔNG hạ xuống 'already' vô căn cứ",
      t0["state"] == "promoted" and t0.get("co_receipt") is True and t0.get("backup") and pathlib.Path(t0["backup"]).read_text(encoding="utf-8") == GOC and c["state"] == "promoted", t0)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
