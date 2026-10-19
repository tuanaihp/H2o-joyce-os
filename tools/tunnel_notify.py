# Tunnel Cloudflare cho Joyce: dam bao cloudflared dang chay, lay link
# trycloudflare.com tu log, gui link do qua bot Telegram da cau hinh trong
# server/settings.json. Chay xong thi thoat - cloudflared duoc tha detached
# nen song tiep doc lap voi script nay.
#
# Duoc goi tu start-joyce.vbs (moi lan Joyce khoi dong). Chay lai nhieu lan
# khong sao: cloudflared da co thi khong mo them, link da gui roi thi khong
# gui lai (nho trong tools/tunnel-last.json).
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "tools" / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
LOG = ROOT / "tools" / "tunnel.log"
LAST = ROOT / "tools" / "tunnel-last.json"
# Cờ "chủ cố ý tắt tunnel": có file này thì watchdog KHÔNG được tự mở lại. Không có nó thì
# người tự tay giết cloudflared để ngừng phơi máy ra Internet sẽ bị watchdog bật lại ở chu kỳ
# sau và phát link public mới qua Telegram - đúng điều họ vừa chặn.
TAT = ROOT / "tools" / "tunnel-off.flag"
SETTINGS = ROOT / "server" / "settings.json"

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
WAIT_SECONDS = 180


def tunnel_bi_tat() -> bool:
    return TAT.exists()


def _pids_cloudflared_joyce() -> list[int]:
    """PID các cloudflared CỦA JOYCE - nhận diện qua command line trỏ tunnel về :7777.

    Không được lọc theo tên ảnh `cloudflared.exe`: trên máy này H2O Video Studio
    chạy một cloudflared khác (tunnel :5170). Nhận lầm nó là "tunnel của Joyce đang
    sống" thì start-joyce/watchdog sẽ KHÔNG mở tunnel mới - server chết vẫn không có
    link; còn giet_cloudflared theo tên ảnh sẽ giết luôn tunnel của app kia."""
    if sys.platform == "win32":
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" "
                 "| ForEach-Object { $_.ProcessId.ToString() + ' ' + $_.CommandLine }"],
                capture_output=True, text=True, timeout=30,
            ).stdout
        except Exception:
            return []
        pids = []
        for line in out.splitlines():
            line = line.strip()
            if not line or "7777" not in line:
                continue
            try:
                pids.append(int(line.split(None, 1)[0]))
            except ValueError:
                pass
        return pids
    try:
        out = subprocess.run(["pgrep", "-af", "cloudflared"], capture_output=True,
                             text=True, timeout=15).stdout
        return [int(l.split(None, 1)[0]) for l in out.splitlines()
                if "cloudflared" in l and "7777" in l]
    except Exception:
        return []


def cloudflared_dang_chay() -> bool:
    """Có tiến trình cloudflared CỦA JOYCE (tunnel :7777) đang chạy không."""
    return bool(_pids_cloudflared_joyce())


def giet_cloudflared() -> bool:
    """Giết cloudflared CỦA JOYCE theo PID. Trả True nếu sau đó không còn cái nào.

    Cần cho op=refresh: ca dùng thật của nó là "tiến trình còn sống nhưng tunnel đã chết",
    mà mo_cloudflared() chỉ spawn chứ không thay thế - không giết trước thì link cũ vẫn đó.
    Chỉ đụng PID có cmdline chứa :7777 - tunnel cloudflared của app khác được tha."""
    try:
        if sys.platform == "win32":
            for pid in _pids_cloudflared_joyce():
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, timeout=20)
        else:
            subprocess.run(["pkill", "-f", "cloudflared.*7777"],
                           capture_output=True, timeout=20)
    except Exception:
        return False
    for _ in range(10):          # chờ HĐH thu hồi tiến trình trước khi mở cái mới
        if not cloudflared_dang_chay():
            return True
        time.sleep(0.3)
    return not cloudflared_dang_chay()


def link_trong_log() -> str:
    try:
        m = URL_RE.findall(LOG.read_text(encoding="utf-8", errors="replace"))
        return m[-1] if m else ""
    except Exception:
        return ""


def mo_cloudflared() -> None:
    if not EXE.exists():
        print("khong thay", EXE, "- bo qua tunnel", flush=True)
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    # Xoa log cu de link moi doc khong lan vao lan chay truoc.
    LOG.write_text("", encoding="utf-8")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | \
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    # `with`: tiến trình con đã nhận bản sao handle lúc spawn, nên cha đóng ngay được. Bản cũ
    # mở rồi bỏ đó, mỗi lần gọi rò một file handle sống hết đời tiến trình cha.
    with LOG.open("a", encoding="utf-8") as f:
        subprocess.Popen(
            [str(EXE), "tunnel", "--url", "http://localhost:7777"],
            stdout=f, stderr=subprocess.STDOUT,
            creationflags=flags, cwd=str(ROOT),
            close_fds=True,
        )


def _giai_ma(v: str) -> str:
    """Token trong settings.json duoc ma hoa at-rest ('enc:...') qua secrets_store cua
    Joyce. Dung lai dung ham giai ma cua no - cung chay trong venv nen import duoc."""
    if isinstance(v, str) and v.startswith("enc:"):
        sys.path.insert(0, str(ROOT / "server"))
        import secrets_store
        return secrets_store.decrypt(v)
    return v


def gui_telegram(text: str) -> bool:
    try:
        tg = json.loads(SETTINGS.read_text(encoding="utf-8")).get("telegram", {})
        token, raw = _giai_ma(tg.get("token", "")), str(tg.get("chat_id", ""))
        ids = [x.strip() for x in raw.split(",") if x.strip()]
        if not token or not ids:
            print("telegram chua cau hinh day du - khong gui", flush=True)
            return False
        ok = True
        for cid in ids:
            body = json.dumps({"chat_id": cid, "text": text}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=body, headers={"Content-Type": "application/json"})
            try:
                r = json.loads(urllib.request.urlopen(req, timeout=20).read())
                ok = ok and bool(r.get("ok"))
            except Exception as e:
                print("gui telegram loi:", e, flush=True)
                ok = False
        return ok
    except Exception as e:
        print("doc settings loi:", e, flush=True)
        return False


def main() -> int:
    if tunnel_bi_tat():
        print("co", TAT.name, "- chu da tat tunnel, khong mo lai", flush=True)
        return 0
    if not cloudflared_dang_chay():
        print("cloudflared chua chay - mo moi", flush=True)
        mo_cloudflared()
    else:
        print("cloudflared dang chay san", flush=True)

    link = ""
    het_han = time.time() + WAIT_SECONDS
    while time.time() < het_han:
        link = link_trong_log()
        if link:
            break
        time.sleep(3)

    if not link:
        print("het", WAIT_SECONDS, "giay van chua thay link tunnel", flush=True)
        return 1

    cu, da_gui_cu = "", False
    try:
        _d = json.loads(LAST.read_text(encoding="utf-8"))
        cu = _d.get("link", "")
        da_gui_cu = bool(_d.get("telegram_sent"))
    except Exception:
        pass

    # LUON ghi state moi nhat ngay khi thay link, ke ca khi gui telegram xit:
    # day la so nho ma tool joyce_access doc de tra lai link khi nguoi dung doi
    # ("gui lai link"), thay vi chi nho link sau khi gui thanh cong nhu truoc.
    #
    # telegram_sent phai mang theo ket qua gui THAT cua lan truoc. Ban cu ghi
    # `link == cu`, ma state duoc ghi TRUOC khi gui - nen mot lan gui that bai roi chay
    # lai se thay link trung va tu nhan la "da gui", trong khi chua gui duoc lan nao.
    state = {"link": link, "local": "http://127.0.0.1:7777", "at": time.time(),
             "telegram_sent": (link == cu) and da_gui_cu}
    try:
        LAST.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass

    if link == cu and da_gui_cu:
        print("link cu da gui roi, khong gui lai:", link, flush=True)
        return 0

    msg = "Link Joyce tu may tinh:\n\n" + link + "\n\nMo tren dien thoai de vao dashboard."
    if gui_telegram(msg):
        state["telegram_sent"] = True
        try:
            LAST.write_text(json.dumps(state), encoding="utf-8")
        except Exception:
            pass
        print("da gui link:", link, flush=True)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
