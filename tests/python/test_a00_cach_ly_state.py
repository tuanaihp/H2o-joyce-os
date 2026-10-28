"""A00 (Joyce Harness, gói A): các test của G1 và gói A KHÔNG được trỏ vào state hay brain thật.

    python tests/run.py a00_cach_ly_state      (không mạng, không model)

Lý do: `config.STATE_DIR` mặc định là thư mục `server/` THẬT (có kanban, cài đặt, tài khoản kênh). Một test quên đặt
`JOYCE_STATE_DIR` mà lại import module đọc cấu hình sẽ đọc, và có thể ghi, dữ liệu thật của người dùng.

Cách kiểm: chạy từng test trong một tiến trình con, đặt sẵn một thư mục tạm làm `JOYCE_STATE_DIR` là phao, rồi sau khi test
chạy xong in ra `config.STATE_DIR` mà tiến trình đã dùng. Phải là một thư mục tạm, không bao giờ là `server/` của repo.
Test KHÔNG đặt biến môi trường thì dùng đúng phao của chúng ta (an toàn); test tự đặt thì dùng thư mục tạm của nó (an toàn).
Điều cần bắt là chỗ nào đó trong test ghi đè về `server/`.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import pathlib
import subprocess
import sys
import tempfile

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


# Các test cần cô lập: toàn bộ test G1 + các test harness đã có + các test gói A (thêm dần khi viết).
TESTS = [
    "test_fix01_diff_quyen.py", "test_fix02_eval_loader.py", "test_fix03_file_guard.py", "test_fix04_fix05_canary.py",
    "test_harness_ranh_gioi_quyen.py", "test_harness_map.py", "test_joyce_guard.py", "test_system_agents.py",
]
TESTS += sorted(p.name for p in (ROOT / "tests" / "python").glob("test_a0[1-7]*.py") if p.name != "test_a00_cach_ly_state.py")

THAT = pathlib.Path(SERVER).resolve()
WRAP = r"""
import runpy, sys, pathlib
p = sys.argv[1]
sys.path.insert(0, str(pathlib.Path(p).parent))      # chạy bằng -c thì thư mục test không tự nằm trong sys.path
code = 0
try:
    runpy.run_path(p, run_name="__main__")
except SystemExit as e:
    code = e.code or 0
cfg = sys.modules.get("config")
print("STATE_DIR=" + (str(pathlib.Path(cfg.STATE_DIR).resolve()) if cfg else "-"))
sys.exit(code)
"""
phao = pathlib.Path(tempfile.mkdtemp(prefix="joyce-a00-phao-")).resolve()
for t in TESTS:
    path = ROOT / "tests" / "python" / t
    env = dict(os.environ, JOYCE_STATE_DIR=str(phao), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("BRAINS_DIR", None)
    r = subprocess.run([sys.executable, "-c", WRAP, str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, cwd=str(ROOT), timeout=600)
    dong = [x for x in r.stdout.splitlines() if x.startswith("STATE_DIR=")]
    state = dong[-1][len("STATE_DIR="):] if dong else ""
    check(f"{t}: chạy xong (exit {r.returncode})", r.returncode == 0, (r.stdout + r.stderr)[-300:])
    check(f"{t}: không dùng state thật của server/", state in ("", "-") or pathlib.Path(state) != THAT, state)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
