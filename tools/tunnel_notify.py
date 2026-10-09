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
EXE = ROOT / "tools" / "cloudflared.exe"
LOG = ROOT / "tools" / "tunnel.log"
LAST = ROOT / "tools" / "tunnel-last.json"
SETTINGS = ROOT / "server" / "settings.json"

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
WAIT_SECONDS = 180


def cloudflared_dang_chay() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq cloudflared.exe", "/NH"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        return "cloudflared.exe" in out
    except Exception:
        return False


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
    f = LOG.open("a", encoding="utf-8")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | \
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
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

    cu = ""
    try:
        cu = json.loads(LAST.read_text(encoding="utf-8")).get("link", "")
    except Exception:
        pass

    # LUON ghi state moi nhat ngay khi thay link, ke ca khi gui telegram xit:
    # day la so nho ma tool joyce_access doc de tra lai link khi nguoi dung doi
    # ("gui lai link"), thay vi chi nho link sau khi gui thanh cong nhu truoc.
    state = {"link": link, "local": "http://127.0.0.1:7777", "at": time.time(),
             "telegram_sent": link == cu}
    try:
        LAST.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass

    if link == cu:
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
