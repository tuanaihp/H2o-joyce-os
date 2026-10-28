"""Hộp thư Messenger của Fanpage (1.3.40): webhook Meta gọi vào, và các nút bật/tắt cho tab Cẩm nang.

Webhook (công khai, không cookie, bảo mật bằng mã xác minh và chữ ký HMAC của Meta):
    GET  /webhooks/messenger   Meta kiểm địa chỉ lúc dán vào Webhooks (hub.verify_token, hub.challenge)
    POST /webhooks/messenger   tin khách đến. Trả 200 NGAY, xử lý nền (Meta chờ tối đa vài giây)

Cho giao diện (cần đăng nhập, như mọi route khác):
    GET  /channels/webhook-info                  địa chỉ + mã xác minh cho form thêm tài khoản ở trang Hội thoại
    GET  /social/facebook/messenger/status       địa chỉ webhook, mã xác minh, từng Trang bật/tắt
    POST /social/facebook/messenger/enable       bật hộp thư cho một Trang (tự lấy token Trang)
    POST /social/facebook/messenger/disable      tắt (giữ nguyên lịch sử hội thoại)
    POST /social/facebook/messenger/mode         cho_gui | tu_dong (tu_dong phải có xac_nhan=1)
    POST /social/facebook/messenger/permissions  xin thêm quyền nhắn tin cho kết nối rồi đăng nhập lại

Hội thoại, soạn nháp, gửi, tiếp quản đều dùng các route SẴN CÓ của Hộp thư (`/conversations/...`),
không viết lại ở đây: tab Fanpage chỉ là một cửa sổ khác nhìn vào cùng kho.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import sys
from typing import Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

import channel_accounts
import chatbot_store
import config as cfgmod
import web_security
from channels import messenger

router = APIRouter()

QUYEN_NHAN_TIN = ["pages_messaging", "pages_manage_metadata"]
_NEN: set = set()          # giữ tham chiếu task nền, tránh bị dọn rác giữa chừng
_DONG_BO = False           # chỉ test đặt True: xử lý ngay trong request thay vì task nền


def _err(msg: str, status: int = 400, **them):
    return JSONResponse({"ok": False, "error": msg, **them}, status_code=status)


def _fb_conn_id() -> Optional[str]:
    import social_ops
    return social_ops._fb_conn_id()


def _app_secret() -> str:
    cid = _fb_conn_id()
    if not cid:
        return ""
    import mcp_store
    return str(mcp_store.connection_secrets(cid).get("client_secret") or "")


def ma_xac_minh() -> str:
    """Mã Meta gửi lại lúc kiểm webhook. Sinh một lần rồi giữ: không phải bí mật (Meta thấy nó) nhưng
    phải khó đoán để người lạ không tự 'đăng ký' webhook của mình vào Joyce."""
    cur = str(((cfgmod.read_settings().get("messenger") or {}).get("verify_token")) or "")
    if cur:
        return cur
    tok = "joyce-" + secrets.token_urlsafe(18)
    cfgmod.update_settings({"messenger": {"verify_token": tok}})
    return tok


def _tk_cua_trang(page_id: str) -> Optional[dict]:
    for a in channel_accounts.list_accounts("messenger"):
        if str(a.get("external_id") or "") == str(page_id):
            return a
    return None


def _bot_cua_tk(account_id: str) -> Optional[dict]:
    for b in chatbot_store.list_bots():
        if account_id in chatbot_store.account_ids_of(b):
            return b
    return None


# ============================================================
# Webhook
# ============================================================
@router.get(messenger.WEBHOOK_PATH)
async def webhook_xac_minh(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and secrets.compare_digest(
            str(q.get("hub.verify_token") or ""), ma_xac_minh()):
        return PlainTextResponse(str(q.get("hub.challenge") or ""))
    return PlainTextResponse("forbidden", status_code=403)


async def xu_ly_su_kien(ev: dict) -> dict:
    """Một tin khách đã chuẩn hoá. Có bot đang chạy thì giao cho nó; chưa có thì vẫn GHI vào Hộp thư
    (tin khách không được mất chỉ vì bot đang tắt)."""
    tk = _tk_cua_trang(ev.get("page_id") or "")
    if not tk:
        return {"ok": False, "ly_do": "trang_chua_bat"}
    aid = tk["id"]
    tb = messenger._DANG_CHAY.get(aid)
    if tb:
        return {"ok": True, **(await tb.xu_ly(ev))}
    bot = _bot_cua_tk(aid) or {}
    token = channel_accounts.get_token(aid)
    tam = messenger.Transport(token, "", None, None, cfg_fn=lambda: bot, che_do_fn=lambda: "cho_gui")
    tam.account_id = aid
    return {"ok": True, **(await tam.xu_ly(ev))}


async def _chay_nen(ev: dict) -> None:
    try:
        await xu_ly_su_kien(ev)
    except Exception as e:      # noqa: BLE001 - một tin hỏng không được làm sập vòng nhận
        print(f"[messenger] xử lý tin lỗi: {type(e).__name__}: {e}", file=sys.stderr)


@router.post(messenger.WEBHOOK_PATH)
async def webhook_nhan(request: Request):
    raw = await request.body()
    if not messenger.verify_signature(raw, request.headers.get("x-hub-signature-256", ""), _app_secret()):
        return PlainTextResponse("bad signature", status_code=403)
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception:
        return PlainTextResponse("bad json", status_code=400)
    for ev in messenger.parse_webhook(body):
        if _DONG_BO:
            await _chay_nen(ev)
            continue
        t = asyncio.create_task(_chay_nen(ev))
        _NEN.add(t)
        t.add_done_callback(_NEN.discard)
    return PlainTextResponse("EVENT_RECEIVED")


# ============================================================
# Cho giao diện
# ============================================================
def _webhook_url(request: Request) -> str:
    base = web_security.external_base(request.url.scheme, request.url.netloc,
                                      request.headers.get("x-forwarded-proto", ""),
                                      request.headers.get("x-forwarded-host", ""))
    return base + messenger.WEBHOOK_PATH


def _canh_bao_dia_chi(url: str) -> str:
    host = url.split("://", 1)[-1].split("/", 1)[0].lower()
    if host.startswith(("localhost", "127.", "[::1]")):
        return "Địa chỉ localhost: Meta không gọi vào được. Mở Joyce bằng tên miền riêng rồi vào lại trang này."
    if host.endswith("trycloudflare.com"):
        return "Đây là link tạm của Cloudflare, đổi mỗi lần mở lại tunnel nên webhook sẽ hỏng. Dùng tên miền riêng."
    if not url.startswith("https://"):
        return "Meta chỉ gọi vào địa chỉ HTTPS."
    return ""


async def _trang_cua_anh(brain: str) -> list:
    import social_ops
    out, err = await social_ops._call_tool("fb_pages_list", {}, brain)
    if err:
        return []
    ds = out if isinstance(out, list) else (out or {}).get("pages") or []
    return [p for p in ds if isinstance(p, dict) and not p.get("hidden")]


def _dong_trang(p: dict) -> dict:
    pid = str(p.get("id") or "")
    tk = _tk_cua_trang(pid)
    bot = _bot_cua_tk(tk["id"]) if tk else None
    return {
        "page_id": pid, "name": p.get("name") or pid,
        "bat": bool(tk and bot and bot.get("enabled")),
        "da_co_tai_khoan": bool(tk), "account_id": (tk or {}).get("id") or "",
        "bot_id": (bot or {}).get("id") or "",
        "agent": (((bot or {}).get("agent") or {}).get("slug")) or "",
        "che_do": str(((tk or {}).get("meta") or {}).get("che_do_tra_loi") or messenger.CHE_DO_MAC_DINH),
        "account_key": f"messenger:{tk['id']}" if tk else "",
    }


@router.get("/channels/webhook-info")
async def webhook_info(request: Request, channel: str = Query("")):
    """Địa chỉ và mã xác minh để dán sang nền tảng, cho form thêm tài khoản ở trang Hội thoại (kênh khai
    `WEBHOOK_PATH`). Hỏi server chứ không ghép từ location của trình duyệt: sau proxy chỉ server biết địa chỉ ngoài thật."""
    if str(channel).strip().lower() != "messenger":
        return _err("Kênh này không nhận tin bằng webhook của Joyce.", 404)
    url = _webhook_url(request)
    return {"ok": True, "channel": "messenger", "webhook_url": url, "verify_token": ma_xac_minh(),
            "https": url.startswith("https://"), "canh_bao": _canh_bao_dia_chi(url)}


@router.get("/social/facebook/messenger/status")
async def trang_thai(request: Request, brain: str = Query("brain")):
    import oauth_mcp
    cid = _fb_conn_id()
    url = _webhook_url(request)
    quyen = None
    if cid:
        da_cap = set(oauth_mcp.granted_scopes(cid))
        quyen = (all(s in da_cap for s in QUYEN_NHAN_TIN)) if da_cap else None
    return {"ok": True, "conn_id": cid, "ket_noi": bool(cid),
            "webhook_url": url, "verify_token": ma_xac_minh(), "canh_bao_dia_chi": _canh_bao_dia_chi(url),
            "co_app_secret": bool(_app_secret()), "quyen_nhan_tin": quyen,
            "pages": [_dong_trang(p) for p in await _trang_cua_anh(brain)]}


async def _token_trang(page_id: str):
    """(token Trang, tên Trang, lỗi) từ token người dùng của kết nối Facebook Trang."""
    import oauth_mcp
    cid = _fb_conn_id()
    if not cid:
        return "", "", "Chưa kết nối Facebook Trang."
    hdr = await oauth_mcp.auth_headers(cid)
    ut = (hdr.get("Authorization", "") or "").replace("Bearer ", "").strip()
    if not ut:
        return "", "", "Phiên Facebook hết hạn, kết nối lại ở trang Kết nối."
    d = await messenger._graph("GET", "me/accounts", ut, params={"fields": "id,name,access_token", "limit": 200})
    for p in (d or {}).get("data") or []:
        if str(p.get("id")) == str(page_id):
            if not p.get("access_token"):
                break
            return str(p["access_token"]), str(p.get("name") or ""), ""
    msg = str(((d or {}).get("error") or {}).get("message") or "")
    return "", "", ("Facebook không trả token cho Trang này" + (f": {msg}" if msg else "")
                    + ". Kiểm tra anh là admin Trang và đã tick chọn Trang khi đăng nhập.")


@router.post("/social/facebook/messenger/enable")
async def bat(page_id: str = Form(...), agent_slug: str = Form(...), brain: str = Form("brain")):
    import chatbot_runtime
    pid = str(page_id or "").strip()
    if not pid.isdigit():
        return _err("page_id phải là số.")
    token, ten, loi = await _token_trang(pid)
    if loi:
        return _err(loi, 409)
    kt = await messenger.verify_token(token)
    if not kt.get("ok"):
        return _err(kt.get("error") or "Token Trang không dùng được.", 409)
    dk = await messenger.dang_ky_trang(pid, token)      # lỗi ở đây không chặn: hay gặp khi app chưa được duyệt
    tk = _tk_cua_trang(pid)
    if tk:
        ok, loi = channel_accounts.update_account(tk["id"], {"token": token, "label": ten or tk.get("label")})
        if not ok:
            return _err(loi)
        aid = tk["id"]
        bot = _bot_cua_tk(aid)
        bid = (bot or {}).get("id") or ""
    else:
        bid, loi = chatbot_store.create_bot({
            "name": f"Messenger - {ten or pid}", "agent_slug": agent_slug, "agent_brain": brain, "brain": brain,
            "channel": "messenger", "token": token, "bot_username": pid, "account_label": ten or pid,
            "reply_when": "always", "icon": "messages-square"})
        if not bid:
            return _err(loi or "Không tạo được bot.")
        bot = chatbot_store.get_bot(bid) or {}
        aid = (chatbot_store.account_ids_of(bot) or [""])[0]
        channel_accounts.update_account(aid, {"meta": {"che_do_tra_loi": messenger.CHE_DO_MAC_DINH}})
    if bot and (bot.get("agent") or {}).get("slug") != agent_slug:
        chatbot_store.update_bot(bid, {"agent_slug": agent_slug, "agent_brain": brain})
    ok, loi = chatbot_store.set_enabled(bid, True)
    if not ok:
        return _err(loi)
    chay, loi_chay = chatbot_runtime.start_bot(bid)
    return {"ok": True, "bot_id": bid, "account_id": aid, "da_dang_ky_webhook": dk.get("ok", False),
            "loi_dang_ky": dk.get("error", ""), "dang_chay": chay, "loi_chay": loi_chay,
            "che_do": messenger.CHE_DO_MAC_DINH}


@router.post("/social/facebook/messenger/disable")
async def tat(page_id: str = Form(...)):
    import chatbot_runtime
    tk = _tk_cua_trang(str(page_id).strip())
    if not tk:
        return _err("Trang này chưa bật hộp thư.", 404)
    bot = _bot_cua_tk(tk["id"])
    if bot:
        chatbot_runtime.stop_bot(bot["id"])
        chatbot_store.set_enabled(bot["id"], False)
    token = channel_accounts.get_token(tk["id"])
    huy = await messenger.huy_dang_ky_trang(str(page_id).strip(), token) if token else {"ok": False}
    return {"ok": True, "da_huy_webhook": bool(huy.get("ok"))}


@router.post("/social/facebook/messenger/mode")
async def doi_che_do(page_id: str = Form(...), mode: str = Form(...), xac_nhan: str = Form("")):
    if mode not in messenger.CHE_DO:
        return _err("mode phải là cho_gui hoặc tu_dong.")
    tk = _tk_cua_trang(str(page_id).strip())
    if not tk:
        return _err("Trang này chưa bật hộp thư.", 404)
    if mode == "tu_dong" and str(xac_nhan).strip().lower() not in ("1", "true", "yes", "on"):
        return _err("Tự động trả lời gửi tin THẲNG cho khách, không qua anh duyệt. Cần xác nhận rõ.", 409,
                    can_xac_nhan=True)
    meta = dict(tk.get("meta") or {})
    meta["che_do_tra_loi"] = mode
    ok, loi = channel_accounts.update_account(tk["id"], {"meta": meta})
    return {"ok": True, "che_do": mode} if ok else _err(loi)


@router.post("/social/facebook/messenger/permissions")
async def xin_quyen(request: Request):
    """Thêm pages_messaging vào danh sách quyền xin lần đăng nhập tới, rồi để giao diện mở lại đăng nhập."""
    import mcp_store
    cid = _fb_conn_id()
    if not cid:
        return _err("Chưa kết nối Facebook Trang.", 409)
    cfg = mcp_store.connection_config(cid)
    cur = [str(x) for x in (cfg.get("extra_scopes") or [])]
    cfg["extra_scopes"] = cur + [s for s in QUYEN_NHAN_TIN if s not in cur]
    mcp_store.update_connection(cid, {"config": cfg})
    return {"ok": True, "conn_id": cid, "scopes": cfg["extra_scopes"], "dang_nhap_lai": True}


def register(app) -> None:
    app.include_router(router)
