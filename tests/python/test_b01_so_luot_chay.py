"""B01 (Joyce Harness, gói B): sổ lượt chạy do host ghi, idempotent, không tự tính đạt khi không biết.

    python tests/run.py b01_so_luot_chay      (không mạng, không model; state ở thư mục tạm)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import sqlite3
import sys
import tempfile
import threading

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-b01-state-")
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


rv1 = L.chup_revision(agent_text="agent v1", harness_version="1.0.0", guard_on=True, eval_text="e1", deps={"skill-a": "s1"})
rv2 = L.chup_revision(agent_text="agent v1", harness_version="1.0.0", guard_on=True, eval_text="e1", deps={"skill-a": "s2"})
check("revision: skill đổi mà file agent không đổi vẫn cho deps_revisions khác (không gán nhầm cho bản cũ)",
      rv1["agent_revision"] == rv2["agent_revision"] and rv1["deps_revisions"] != rv2["deps_revisions"])
check("revision: bật tắt guard đổi harness_revision",
      rv1["harness_revision"] != L.chup_revision(agent_text="x", harness_version="1.0.0", guard_on=False)["harness_revision"])
check("revision: không lưu nội dung gốc, chỉ băm 64 ký tự", len(rv1["agent_revision"]) == 64 and "agent v1" not in str(rv1))

t0 = 1_000_000.0
r1 = L.bat_dau(brain_id="b1", agent_id="ke-toan", entrypoint="chat", ref="chat:1", engine="claude", model="m", revision=rv1, now=t0)
check("mở lượt: có run_id, trạng thái running, lưu revision host chụp",
      L.lay(r1)["status"] == "running" and L.lay(r1)["agent_revision"] == rv1["agent_revision"])
r1b = L.bat_dau(brain_id="b1", agent_id="ke-toan", entrypoint="chat", run_id=r1, now=t0 + 5)
check("callback mở trùng cùng run_id: không tạo bản thứ hai, không đổi giờ bắt đầu",
      r1b == r1 and L.lay(r1)["started_at"] == t0 and len(L.danh_sach()) == 1)

check("kết thúc lần đầu có hiệu lực",
      L.ket_thuc(r1, "completed", verification="verified_pass", now=t0 + 10) is True and L.lay(r1)["status"] == "completed")
check("kết thúc lần hai (callback trùng) KHÔNG đổi kết quả, chỉ đếm trùng",
      L.ket_thuc(r1, "failed", now=t0 + 20) is False and L.lay(r1)["status"] == "completed" and L.lay(r1)["trung_lap"] == 1)

r2 = L.bat_dau(brain_id="b1", agent_id="ke-toan", entrypoint="task", now=t0 + 30)
L.ket_thuc(r2, "failed", block_kind="business", verification="verified_pass", now=t0 + 31)
check("lượt lỗi không thể mang verified_pass dù người gọi truyền vậy", L.lay(r2)["verification_status"] == "unverified")
r3 = L.bat_dau(brain_id="b1", agent_id="ke-toan", entrypoint="chat", now=t0 + 40)
L.ket_thuc(r3, "trang-thai-la", now=t0 + 41)
check("trạng thái lạ thành unknown, không thành đạt", L.lay(r3)["status"] == "unknown")

# retry: nhiều lần thử của MỘT việc chỉ là một bằng chứng
a1 = L.bat_dau(brain_id="b1", agent_id="ke-toan", entrypoint="task", logical_execution_id="viec-9", attempt_id="1", now=t0 + 50)
L.ket_thuc(a1, "failed", block_kind="system", now=t0 + 51)
a2 = L.bat_dau(brain_id="b1", agent_id="ke-toan", entrypoint="task", logical_execution_id="viec-9", attempt_id="2", now=t0 + 60)
L.ket_thuc(a2, "completed", verification="verified_pass", now=t0 + 61)
tk = L.thong_ke(brain_id="b1", agent_id="ke-toan")
check("thống kê đếm theo logical execution: 5 lần chạy nhưng 4 việc độc lập, 2 lần thử của viec-9 là 1 bằng chứng",
      tk["lan_chay"] == 5 and tk["logical"] == 4 and tk["thu_lai"] == 1, tk)
check("thống kê: lần thử đầu lỗi hệ thống không bị tính thêm là rớt vì đã có lần sau",
      tk["loi_he_thong"] == 0 and tk["verified_pass"] == 2, tk)

# orphan / mất worker
o = L.bat_dau(brain_id="b2", agent_id="x", entrypoint="workflow", now=t0 - 1000)
n = L.don_mo_coi(t0 - 500, now=t0)
check("lượt running cũ không ai chốt thành interrupted, KHÔNG tính đạt hay rớt",
      n == 1 and L.lay(o)["status"] == "interrupted" and L.lay(o)["verification_status"] == "unverified")
st = L.thong_ke(brain_id="b2", agent_id="x")
check("thống kê tách gián đoạn ra riêng", st["gian_doan"] == 1 and st["verified_pass"] == 0, st)

# chờ duyệt không phải lỗi agent
w = L.bat_dau(brain_id="b3", agent_id="y", entrypoint="chat", now=t0)
L.ket_thuc(w, "needs_approval", block_kind="waiting", now=t0 + 1)
sw = L.thong_ke(brain_id="b3", agent_id="y")
check("chờ duyệt tách riêng, không tính vào rớt", sw["doi_duyet"] == 1 and sw["verified_fail"] == 0, sw)

# kiểm chứng đến sau
c = L.bat_dau(brain_id="b4", agent_id="z", entrypoint="chat", now=t0)
L.ket_thuc(c, "completed", now=t0 + 1)
sz = L.thong_ke(brain_id="b4", agent_id="z")
check("hoàn tất chưa kiểm: chua_kiem, chưa phải đạt", sz["chua_kiem"] == 1 and sz["verified_pass"] == 0, sz)
check("bộ chấm nâng lượt đã xong lên verified_pass một lần, lần sau không đổi được",
      L.danh_dau_kiem_chung(c, "verified_pass", ["ev1"]) is True and L.lay(c)["evidence_refs"] == ["ev1"]
      and L.danh_dau_kiem_chung(c, "verified_fail") is False and L.lay(c)["verification_status"] == "verified_pass")
d = L.bat_dau(brain_id="b4", agent_id="z", entrypoint="chat", now=t0)
check("lượt đang chạy chưa thể được kiểm chứng", L.danh_dau_kiem_chung(d, "verified_pass") is False)

# lọc theo revision: bằng chứng của bản cũ không lẫn vào bản mới
L.bat_dau(brain_id="b5", agent_id="q", entrypoint="chat", revision=rv1, now=t0)
L.bat_dau(brain_id="b5", agent_id="q", entrypoint="chat", revision=L.chup_revision(agent_text="agent v2"), now=t0)
check("lọc theo agent_revision tách đúng hai bản",
      len(L.danh_sach(brain_id="b5", agent_id="q", agent_revision=rv1["agent_revision"])) == 1)

# siêu dữ liệu: không có cột nội dung hội thoại
cols = [r[1] for r in sqlite3.connect(str(L._duong_dan())).execute("PRAGMA table_info(agent_runs)")]
check("sổ không có cột lưu prompt hay hội thoại", not any(k in cols for k in ("prompt", "message", "content", "text", "transcript")), cols)

# nhiều luồng cùng kết thúc một lượt: đúng một bên thắng
x = L.bat_dau(brain_id="b6", agent_id="t", entrypoint="chat", now=t0)
kq = []
ts = [threading.Thread(target=lambda: kq.append(L.ket_thuc(x, "completed"))) for _ in range(10)]
for t in ts:
    t.start()
for t in ts:
    t.join()
check("10 luồng cùng chốt một lượt: đúng một lần có hiệu lực", kq.count(True) == 1 and L.lay(x)["trung_lap"] == 9,
      (kq.count(True), L.lay(x)["trung_lap"]))

# giữ sổ không phình mãi: chỉ xoá lượt ĐÃ kết thúc và đủ cũ
cu_xong = L.bat_dau(brain_id="b7", agent_id="old", entrypoint="chat", now=t0 - 10_000_000)
L.ket_thuc(cu_xong, "completed", now=t0 - 9_999_990)
cu_chay = L.bat_dau(brain_id="b7", agent_id="old", entrypoint="chat", now=t0 - 10_000_000)
moi_xong = L.bat_dau(brain_id="b7", agent_id="old", entrypoint="chat", now=t0)
L.ket_thuc(moi_xong, "completed", now=t0 + 1)
n_xoa = L.don_cu(t0 - 1_000_000)
check("don_cu xoá lượt đã kết thúc quá cũ, GIỮ lượt còn đang chạy và lượt mới",
      n_xoa == 1 and L.lay(cu_xong) is None and L.lay(cu_chay) is not None and L.lay(moi_xong) is not None, n_xoa)

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b01_so_luot_chay: tất cả pass")
