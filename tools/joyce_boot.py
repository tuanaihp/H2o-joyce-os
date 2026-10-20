"""Joyce OS - tự bật + tự sống lại trên Windows, KHÔNG qua .vbs (1.3.25).

Scheduled Task "JoyceOS-AutoStart" chạy file này bằng .venv\\Scripts\\pythonw.exe (không cửa sổ)
mỗi 5 phút. Mỗi lần chạy làm đúng việc của bộ đôi cũ joyce-boot.vbs + joyce-watchdog.vbs:

  - Người dùng bấm stop-joyce (có cờ server/.joyce-paused) -> im, không làm gì.
  - Máy vừa lên chưa đủ 90 giây -> chờ lượt sau (đỡ tranh đĩa với Windows lúc khởi động).
  - Cổng 7777 không ai nghe -> bật server (như start-joyce.vbs) rồi mở tunnel + gửi link mới
    qua Telegram (tools/tunnel_notify.py) và bật Ollama nếu nó chưa chạy.
  - Server đang sống -> chỉ canh tunnel (trừ khi chủ tắt bằng tools/tunnel-off.flag) và Ollama.

Vì sao bỏ .vbs: 360 Total Security mỗi lần mở máy quét "chương trình tự chạy" và TẮT mọi mục trỏ
tới script .vbs (log 360ScanLog ngày 20 và 21/10/2026: joyce-boot.vbs, start-joyce.vbs,
joyce-watchdog.vbs đều "禁止自启动 处理成功"). Run key mất, task mất, Joyce không lên, không có
link, lệnh "Link" trên Telegram cũng không ai trả lời. Task chạy thẳng một file .exe thì 360 để
yên (task H2O Video Studio chạy node.exe sống qua mọi lần quét).

Chạy tay để thử:  .venv\\Scripts\\python.exe tools\\joyce_boot.py --once
"""
from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 7777
UPTIME_MIN_S = 90
SERVER_WAIT_S = 90

NO_WINDOW = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW
DETACHED = 0x00000008 if os.name == "nt" else 0           # DETACHED_PROCESS
NEW_GROUP = 0x00000200 if os.name == "nt" else 0          # CREATE_NEW_PROCESS_GROUP


def ghi(msg: str) -> None:
    """Một dòng vào server/watchdog.log - vết duy nhất để biết lần tự bật đã làm gì."""
    try:
        with open(ROOT / "server" / "watchdog.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} [boot.py] {msg}\n")
    except OSError:
        pass


def cong_mo(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def uptime_s() -> float:
    if os.name == "nt":
        try:
            return ctypes.windll.kernel32.GetTickCount64() / 1000.0
        except Exception:
            return 1e9
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except Exception:
        return 1e9


def venv_python() -> Path:
    p = ROOT / ".venv" / "Scripts" / "python.exe"
    return p if p.exists() else Path(sys.executable)


def chay_nen(args: list, log: Path | None = None, env: dict | None = None, ghi_them: bool = False) -> None:
    """Bật tiến trình tách hẳn khỏi task (task thoát thì nó vẫn sống), không cửa sổ."""
    out = open(log, "a" if ghi_them else "w", encoding="utf-8", errors="replace") if log else subprocess.DEVNULL
    subprocess.Popen([str(a) for a in args], cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, env=env, close_fds=True,
                     creationflags=NO_WINDOW | DETACHED | NEW_GROUP)


def cloudflared_joyce_dang_chay() -> bool:
    """Chỉ tính cloudflared của JOYCE (dòng lệnh trỏ :7777) - tunnel :5170 của H2O Video
    Studio chạy song song không được nhận nhầm là tunnel Joyce."""
    if os.name != "nt":
        return False
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" | ForEach-Object CommandLine"],
                           capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW, errors="replace")
        return any("7777" in ln for ln in (r.stdout or "").splitlines())
    except Exception:
        return False


def ollama_dang_chay() -> bool:
    if cong_mo(11434, timeout=1.5):
        return True
    try:
        r = subprocess.run(["tasklist", "/NH"], capture_output=True, text=True, timeout=15,
                           creationflags=NO_WINDOW, errors="replace")
        return "ollama" in (r.stdout or "").lower()
    except Exception:
        return False


def bat_ollama() -> None:
    exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    if not exe.exists() or ollama_dang_chay():
        return
    env = dict(os.environ)
    # Kho model ở E:\Ollama\models (ổ C ít chỗ) + ngữ cảnh 16K - y như start-joyce.vbs.
    env.setdefault("OLLAMA_MODELS", r"E:\Ollama\models")
    env.setdefault("OLLAMA_CONTEXT_LENGTH", "16384")
    chay_nen([exe, "serve"], log=ROOT / "server" / "ollama.log", env=env, ghi_them=True)
    ghi("ollama chua chay -> da bat serve")


def bat_tunnel() -> None:
    if (ROOT / "tools" / "tunnel-off.flag").exists() or cloudflared_joyce_dang_chay():
        return
    chay_nen([venv_python(), ROOT / "tools" / "tunnel_notify.py"], log=ROOT / "tools" / "tunnel-notify.log")
    ghi("tunnel Joyce chua chay -> goi tunnel_notify (gui link moi)")


def bat_server() -> bool:
    chay_nen([venv_python(), ROOT / "server" / "main.py"], log=ROOT / "server" / "joyce.log")
    ghi("server khong nghe cong 7777 -> da bat server/main.py")
    han = time.time() + SERVER_WAIT_S
    while time.time() < han:
        if cong_mo(PORT):
            return True
        time.sleep(2)
    ghi(f"server chua len sau {SERVER_WAIT_S}s - xem server/joyce.log")
    return False


def mot_luot() -> str:
    if (ROOT / "server" / ".joyce-paused").exists():
        return "paused"
    if uptime_s() < UPTIME_MIN_S:
        return "boot-wait"
    if cong_mo(PORT):
        bat_tunnel()
        bat_ollama()
        return "alive"
    bat_server()
    bat_tunnel()
    bat_ollama()
    return "started"


def main() -> int:
    # --root <thư mục Joyce>: chạy một BẢN SAO của file này nằm ngoài repo (vd khi cài tay lúc
    # thư mục Joyce chưa có bản 1.3.25) mà vẫn bật đúng server của thư mục đó.
    global ROOT
    if "--root" in sys.argv:
        i = sys.argv.index("--root")
        if i + 1 < len(sys.argv) and Path(sys.argv[i + 1]).is_dir():
            ROOT = Path(sys.argv[i + 1]).resolve()
    try:
        kq = mot_luot()
    except Exception as e:                       # task không được chết câm
        ghi(f"loi: {e!r}")
        return 1
    if "--once" in sys.argv:
        print(kq)
    return 0


if __name__ == "__main__":
    sys.exit(main())
