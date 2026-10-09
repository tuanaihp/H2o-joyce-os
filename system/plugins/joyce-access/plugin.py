"""Plugin bundled: tool `joyce_access` - tra lai duong truy cap Joyce khi duoc doi.

Vì sao tool này tồn tại
=======================
Link tunnel trycloudflare.com DOI MOI LAN cloudflared khoi dong lai, va tunnel chi duoc
gui qua Telegram MOT LAN luc khoi dong (tools/tunnel_notify.py). Truoc tool nay, nguoi
dung go "gui lai link" trong chat thi Joyce khong co cach nao lay lai link - phai mo may
doc log bang tay.

Ba op:
- get:     doc link moi nhat (tools/tunnel-last.json, fallback quet tunnel.log) + link
           local 127.0.0.1:7777 + tuoi link. Khong gui di dau ca.
- send:    gui link do qua Telegram cho cac chat_id da cau hinh.
- refresh: tunnel chet/doi link -> chay lai tunnel_notify de mo cloudflared moi va lay
           link moi. Cham nhat vi cho tunnel len (toi da ~60s).
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"
LAST = TOOLS / "tunnel-last.json"
LOG = TOOLS / "tunnel.log"
LOCAL = "http://127.0.0.1:7777"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _doc_state() -> dict:
    """Link tunnel moi nhat da biet.

    Uu tien tunnel.log truoc: file do bi XOA MOI LAN cloudflared mo lai (mo_cloudflared
    ghi de trong), nen URL cuoi cung trong log luon la cua tunnel DANG CHAY. tunnel-last.json
    chi la 'link da gui telegram' - neu lan gui do timeout thi no giu link cu da chet, con
    log da co link moi (ca that 2026-10-09)."""
    st = {"tunnel": "", "local": LOCAL, "at": 0.0, "telegram_sent": False}
    try:
        d = json.loads(LAST.read_text(encoding="utf-8"))
        st["at"] = float(d.get("at") or 0)
        st["telegram_sent"] = bool(d.get("telegram_sent"))
        st["tunnel"] = str(d.get("link") or "")
    except Exception:
        pass
    try:
        m = URL_RE.findall(LOG.read_text(encoding="utf-8", errors="replace"))
        if m and m[-1] != st["tunnel"]:
            st["tunnel"] = m[-1]
            st["at"] = LOG.stat().st_mtime
            st["telegram_sent"] = False     # link trong log moi hon link da gui
    except Exception:
        pass
    return st


def _song(link: str) -> bool:
    """Tunnel con song khong - HEAD/GET nhe, timeout 4s. Cau tra loi nao cung tinh."""
    try:
        urllib.request.urlopen(link, timeout=4)
        return True
    except Exception:
        return False


def _gui_telegram(text: str) -> bool:
    """Dung lai dung ham gui cua tunnel_notify (doc settings.json, giai ma token)."""
    try:
        if str(TOOLS) not in sys.path:
            sys.path.insert(0, str(TOOLS))
        import tunnel_notify
        return bool(tunnel_notify.gui_telegram(text))
    except Exception as e:
        print("joyce_access gui telegram loi:", e, flush=True)
        return False


def _get(args, ctx) -> str:
    st = _doc_state()
    if not st["tunnel"]:
        return ("Chưa có link tunnel nào được ghi lại. Có thể cloudflared chưa chạy - "
                "gọi op=refresh để mở tunnel mới. Link local luôn là " + LOCAL)
    tuoi = ""
    if st["at"]:
        phut = int((time.time() - st["at"]) / 60)
        tuoi = f" (ghi {phut} phút trước)" if phut > 0 else " (vừa ghi)"
    return (f"Link tunnel mới nhất: {st['tunnel']}{tuoi}\n"
            f"Link local (trong nhà): {st['local']}\n"
            f"Đã gửi Telegram lúc khởi động: {'có' if st['telegram_sent'] else 'chưa'}")


def _send(args, ctx) -> str:
    st = _doc_state()
    if not st["tunnel"]:
        return "ERROR: chưa có link tunnel để gửi. Gọi op=refresh để mở tunnel trước."
    text = ("Link Joyce tu may tinh (gui lai theo yeu cau):\n\n" + st["tunnel"] +
            "\n\nLink local: " + LOCAL)
    if _gui_telegram(text):
        return f"Đã gửi lại link qua Telegram: {st['tunnel']}"
    return "ERROR: gửi Telegram không được (kiểm tra cấu hình bot trong Cài đặt)."


def _refresh(args, ctx) -> str:
    try:
        if str(TOOLS) not in sys.path:
            sys.path.insert(0, str(TOOLS))
        import tunnel_notify
        if not tunnel_notify.cloudflared_dang_chay():
            tunnel_notify.mo_cloudflared()
    except Exception as e:
        return f"ERROR: không mở được cloudflared ({type(e).__name__}: {e})."
    # Cho tunnel in link ra log - toi da 60s cho refresh-on-demand (khac 180s luc boot).
    link, het = "", time.time() + 60
    while time.time() < het:
        st = _doc_state()
        if st["tunnel"] and _song(st["tunnel"]):
            link = st["tunnel"]
            break
        time.sleep(3)
    if not link:
        return ("ERROR: chờ 60 giây vẫn chưa thấy link tunnel sống. Xem tools/tunnel.log "
                "để biết cloudflared kẹt ở đâu.")
    _gui_telegram("Link Joyce moi sau khi refresh:\n\n" + link)
    return f"Tunnel mới đã lên và đã gửi Telegram: {link}\nLink local: {LOCAL}"


def register(ctx):
    ctx.register_tool(
        "joyce_access",
        "Lấy lại đường truy cập Joyce khi người dùng đòi ('gửi lại link', 'link Joyce', "
        "'link truy cập mới', 'sao không vào được'). op=get: trả link tunnel Cloudflare mới "
        "nhất đã lưu + link local (mặc định, KHÔNG gửi đi đâu). op=send: gửi link đó qua "
        "Telegram. op=refresh: link cũ chết/đổi - mở lại cloudflared, lấy link mới và gửi "
        "Telegram luôn (chờ tới ~60s). Luôn báo rõ cả link local 127.0.0.1:7777 cho người "
        "dùng đang ngồi trên cùng máy.",
        _chay,
        schema={
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": ["get", "send", "refresh"],
                       "description": "get=xem link (mặc định), send=gửi Telegram, refresh=tunnel chết thì mở lại và lấy link mới"},
            },
            "required": ["op"],
        },
        min_mode="safe",
        emoji="🔗",
    )


async def _chay(args, ctx) -> str:
    op = str((args or {}).get("op") or "get").strip().lower()
    if op == "get":
        return _get(args, ctx)
    if op == "send":
        return _send(args, ctx)
    if op == "refresh":
        return _refresh(args, ctx)
    return "ERROR: op phải là 'get', 'send' hoặc 'refresh'."
