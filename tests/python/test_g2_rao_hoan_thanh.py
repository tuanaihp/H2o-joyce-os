"""G2 #4 (chủ chốt 29/10/2026): rào hoàn thành cho việc tác động ra ngoài.

    python tests/run.py g2_rao_hoan_thanh      (không mạng, không model)

Câu "đã xong" của worker chỉ là ỨNG VIÊN. Việc external-write chưa được nghiệm thu ĐỘC LẬP thì vào cột duyệt, không tự sang `done`.
Việc đã qua nghiệm thu độc lập (how="ai") và việc loại khác không đổi.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-g2rao-state-")

import config as cfgmod  # noqa: E402
import tasks  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


F = tasks.TasksFeature
ngoai = {"capability": "external-write"}
doc = {"capability": "files"}

check("việc ra ngoài, chưa có điều kiện nghiệm thu (none): VÀO cột duyệt", F._rao_hoan_thanh(ngoai, "none") is True)
check("việc ra ngoài, người nghiệm thu không chạy được (unverified): VÀO cột duyệt", F._rao_hoan_thanh(ngoai, "unverified") is True)
check("việc ra ngoài đã qua nghiệm thu độc lập (ai): chạy như cũ, không bị rào", F._rao_hoan_thanh(ngoai, "ai") is False)
check("việc ra ngoài mà worker tự thú chưa xong (heuristic): đã bị chặn ở bước nghiệm thu, rào không chen vào", F._rao_hoan_thanh(ngoai, "heuristic") is False)
check("việc đọc/ghi file trong brain: KHÔNG bị rào (loại việc nhẹ)", F._rao_hoan_thanh(doc, "none") is False and F._rao_hoan_thanh(doc, "unverified") is False)
check("việc không có capability: không bị rào", F._rao_hoan_thanh({}, "none") is False)

# cấu hình: chủ đổi loại hoặc tắt hẳn
goc = cfgmod.read_settings
try:
    cfgmod.read_settings = lambda: {"tasks": {"rao_hoan_thanh": []}}
    check("chủ đặt danh sách rỗng: rào TẮT", F._rao_hoan_thanh(ngoai, "none") is False)
    cfgmod.read_settings = lambda: {"tasks": {"rao_hoan_thanh": ["external-write", "code"]}}
    check("chủ thêm loại 'code': việc code chưa nghiệm thu cũng vào duyệt", F._rao_hoan_thanh({"capability": "code"}, "none") is True)
    check("... và loại mặc định vẫn còn", F._rao_hoan_thanh(ngoai, "unverified") is True)
    cfgmod.read_settings = lambda: {"tasks": {"rao_hoan_thanh": "sai-kieu"}}
    check("cấu hình sai kiểu: rơi về mặc định (rào BẬT), không tắt im lặng", F._rao_hoan_thanh(ngoai, "none") is True)

    def hong():
        raise RuntimeError("settings hỏng")
    cfgmod.read_settings = hong
    check("đọc cấu hình hỏng: rơi về mặc định (rào BẬT)", F._rao_hoan_thanh(ngoai, "none") is True)
finally:
    cfgmod.read_settings = goc

# nối dây: kết quả của rào thật sự đi vào lệnh hoàn tất việc
src = (SERVER / "tasks.py").read_text(encoding="utf-8")
check("rào được tính từ KẾT QUẢ nghiệm thu `how` của chính lượt này", "rao_ht = self._rao_hoan_thanh(task, how)" in src)
check("rào ép việc vào cột duyệt qua needs_approval của store.complete",
      "needs_approval=(bool(task.get(\"needs_approval\")) or hi_gate or rao_ht) and not auto_ok" in src)
check("việc bị rào ghi dấu vết trong metadata để Sơ đồ và chủ thấy lý do", 'completion_gate="chua_nghiem_thu_doc_lap"' in src)

print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g2_rao_hoan_thanh: tất cả pass")
