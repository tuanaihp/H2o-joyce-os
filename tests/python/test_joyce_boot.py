"""tools/joyce_boot.py - tự bật + tự sống lại không qua .vbs (1.3.25).

    python tests/run.py joyce_boot      (không mạng, không bật tiến trình thật)

360 Total Security tắt mọi mục tự chạy trỏ .vbs mỗi lần mở máy (log 20 + 21/10/2026), nên Joyce
không lên, không gửi link. Task mới chạy thẳng pythonw + joyce_boot.py. File này canh các nhánh
quyết định của joyce_boot (bấm stop thì im, máy vừa lên thì chờ, server chết thì bật, server
sống thì chỉ canh tunnel/Ollama) bằng cách thay các hàm đụng hệ thống bằng bản giả.
"""
from _paths import ROOT
import importlib.util
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_spec = importlib.util.spec_from_file_location("joyce_boot", ROOT / "tools" / "joyce_boot.py")
jb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jb)

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


goc = Path(tempfile.mkdtemp(prefix="joyce-boot-"))
(goc / "server").mkdir()
(goc / "tools").mkdir()
jb.ROOT = goc
goi = []
jb.bat_server = lambda: goi.append("server") or True
jb.bat_tunnel = lambda: goi.append("tunnel")
jb.bat_ollama = lambda: goi.append("ollama")
jb.uptime_s = lambda: 3600.0
jb.cong_mo = lambda port, host="127.0.0.1", timeout=2.0: False


def luot():
    goi.clear()
    return jb.mot_luot()


(goc / "server" / ".joyce-paused").write_text("x", encoding="utf-8")
check("người dùng bấm stop-joyce (cờ .joyce-paused) -> im, không bật gì", luot() == "paused" and goi == [])
(goc / "server" / ".joyce-paused").unlink()

jb.uptime_s = lambda: 30.0
check("máy vừa lên < 90 giây -> chờ lượt sau", luot() == "boot-wait" and goi == [])
jb.uptime_s = lambda: 3600.0

check("cổng 7777 không ai nghe -> bật server rồi tunnel (gửi link) rồi Ollama",
      luot() == "started" and goi == ["server", "tunnel", "ollama"])

jb.cong_mo = lambda port, host="127.0.0.1", timeout=2.0: True
check("server đang sống -> KHÔNG bật lại server, chỉ canh tunnel + Ollama",
      luot() == "alive" and goi == ["tunnel", "ollama"])


def _no(*a, **k):
    raise RuntimeError("boom")


jb.cong_mo = _no
check("lỗi bất ngờ -> main() trả 1 và ghi watchdog.log, không chết câm",
      jb.main() == 1 and "loi:" in (goc / "server" / "watchdog.log").read_text(encoding="utf-8"))

SRC = (ROOT / "tools" / "joyce_boot.py").read_text(encoding="utf-8")
check("tunnel chỉ tính cloudflared CỦA Joyce (:7777), không nhầm tunnel H2O Video Studio",
      '"7777" in ln' in SRC)
check("tôn trọng tools/tunnel-off.flag (chủ tắt tunnel có chủ đích)", "tunnel-off.flag" in SRC)
check("tiến trình bật ra không có cửa sổ và tách khỏi task", "CREATE_NO_WINDOW" in SRC and "DETACHED" in SRC)
check("không dùng em dash", "—" not in SRC)

if _fails:
    raise SystemExit(f"\nFAIL - test_joyce_boot: {len(_fails)} lỗi")
print("\nOK - test_joyce_boot: tất cả pass")
