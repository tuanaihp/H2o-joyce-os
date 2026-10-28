"""Kênh Messenger của Fanpage Facebook (1.3.40): khách nhắn Trang, Joyce nhận qua webhook của Meta.

Khác Telegram và Zalo Bot ở HAI điểm, và cả hai quyết định cách viết file này:

1. Tin đến bằng WEBHOOK (Meta gọi vào Joyce), không có vòng long-poll. `Transport` ở đây là lớp
   BỊ ĐỘNG: `start()` chỉ đăng ký mình vào sổ `_DANG_CHAY` theo id tài khoản, webhook
   (`routes/messenger.py`) tra sổ đó rồi gọi `xu_ly`. Nhờ vậy bot Messenger đi qua đúng `start_bot`,
   `status`, tab Tài khoản bot và Hộp thư như mọi kênh khác, không một nhánh riêng trong lõi.
2. Token là token CỦA TRANG (lấy từ kết nối "Facebook Trang", không dán tay) và Meta chỉ cho trả
   lời trong 24 giờ sau tin cuối của khách. Quá hạn thì `gui` trả lỗi nói thẳng chứ không gửi lậu.

Hai chế độ trả lời của một tài khoản (`meta.che_do_tra_loi`):
    cho_gui  (MẶC ĐỊNH) tin khách chỉ vào Hộp thư. Không gọi model, không gửi gì. Chủ bấm "Gợi ý trả
             lời" để Joyce soạn nháp, sửa rồi bấm Gửi.
    tu_dong  Joyce tự soạn và gửi qua Agent của bot, trong luật im/nói và giờ trực của bot. Chủ phải
             tự bật, có xác nhận.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import sys
import time
from typing import Any, Dict, List, Optional

from channels import KenhSpec
import localefmt

GRAPH = "https://graph.facebook.com/v25.0"
WEBHOOK_PATH = "/webhooks/messenger"
CUA_SO_TRA_LOI_GIO = 24          # Meta: chỉ trả lời trong 24 giờ sau tin cuối của khách
MAX_CHU_MOT_TIN = 1900           # Send API cắt ở 2000 ký tự; chừa lề cho dấu ngắt
CHE_DO = ("cho_gui", "tu_dong")
CHE_DO_MAC_DINH = "cho_gui"

SPEC = KenhSpec(
    id="messenger", nhan="Messenger", kind="bot", logo="messenger", mau="#0084FF",
    lay_token=("Không dán tay: Joyce tự lấy token Trang từ kết nối Facebook Trang khi anh bấm "
               "\"Bật hộp thư Messenger\" ở Cẩm nang, mục Fanpage."),
    tom_tat=("Khách nhắn thẳng Fanpage. Chỉ chat riêng, trả lời được trong 24 giờ sau tin cuối của "
             "khách (luật của Meta). Mặc định Joyce chỉ soạn nháp, chủ bấm gửi."),
    nang_luc={"nhom": False, "gui_chu": True, "gui_file": False},
    en={"lay_token": ("No pasting: Joyce takes the Page token from the Facebook Pages connection when you "
                      "press \"Turn on Messenger inbox\" in Handbook, Fanpage section."),
        "tom_tat": ("Customers message your Fanpage directly. Private chats only, and you can reply within "
                    "24 hours of the customer's last message (a Meta rule). By default Joyce only drafts; "
                    "you press send.")},
)

# account_id -> Transport đang chạy. Webhook tra sổ này để biết bot nào nhận tin của Trang nào.
_DANG_CHAY: Dict[str, "Transport"] = {}


# ============================================================
# Thuần: chữ ký, đọc payload
# ============================================================
def verify_signature(raw: bytes, header: str, app_secret: str) -> bool:
    """Kiểm `X-Hub-Signature-256` của Meta. Thiếu secret hoặc header thì TỪ CHỐI (đóng khi lỗi):
    webhook công khai mà không kiểm chữ ký thì ai biết địa chỉ cũng bơm được tin giả vào Hộp thư
    và (ở chế độ tự động) khiến Joyce trả lời một người không tồn tại."""
    secret = str(app_secret or "").strip()
    h = str(header or "").strip()
    if not secret or not h.startswith("sha256="):
        return False
    mong = hmac.new(secret.encode("utf-8"), raw or b"", hashlib.sha256).hexdigest()
    return hmac.compare_digest(mong, h[len("sha256="):].strip().lower())


def parse_webhook(body: Any) -> List[dict]:
    """Payload webhook -> danh sách sự kiện TIN KHÁCH đã chuẩn hoá.

    Mỗi phần tử: {page_id, psid, mid, ts, text, anh: [url], loai}. `loai` = "text" | "image" | "file" |
    "postback". Bỏ qua: echo (tin do chính Trang gửi), delivery, read, và payload không phải Trang.
    """
    out: List[dict] = []
    if not isinstance(body, dict) or body.get("object") != "page":
        return out
    for ent in body.get("entry") or []:
        if not isinstance(ent, dict):
            continue
        page_id = str(ent.get("id") or "")
        for m in ent.get("messaging") or []:
            if not isinstance(m, dict):
                continue
            psid = str((m.get("sender") or {}).get("id") or "")
            if not page_id or not psid or psid == page_id:
                continue
            ts = float(m.get("timestamp") or 0) / 1000.0 or time.time()
            msg = m.get("message")
            if isinstance(msg, dict):
                if msg.get("is_echo"):
                    continue
                anh, tep = [], []
                for a in msg.get("attachments") or []:
                    if not isinstance(a, dict):
                        continue
                    url = str(((a.get("payload") or {}).get("url")) or "")
                    (anh if a.get("type") == "image" else tep).append(url)
                chu = str(msg.get("text") or "").strip()
                if not chu and not anh and not tep:
                    continue
                loai = "text" if chu else ("image" if anh else "file")
                out.append({"page_id": page_id, "psid": psid, "mid": str(msg.get("mid") or ""),
                            "ts": ts, "text": chu, "anh": anh, "loai": loai})
            elif isinstance(m.get("postback"), dict):
                pb = m["postback"]
                chu = str(pb.get("title") or pb.get("payload") or "").strip()
                if chu:
                    out.append({"page_id": page_id, "psid": psid, "mid": str(pb.get("mid") or ""),
                                "ts": ts, "text": chu, "anh": [], "loai": "postback"})
    return out


def chia_tin(text: str, tran: int = MAX_CHU_MOT_TIN) -> List[str]:
    """Cắt một câu dài thành nhiều tin, ưu tiên ngắt ở xuống dòng hoặc dấu cách."""
    t = str(text or "").strip()
    if not t:
        return []
    out = []
    while len(t) > tran:
        cat = max(t.rfind("\n", 0, tran), t.rfind(" ", 0, tran))
        if cat < tran // 2:
            cat = tran
        out.append(t[:cat].strip())
        t = t[cat:].strip()
    if t:
        out.append(t)
    return out


def loi_gui(d: dict) -> str:
    """Lỗi Send API -> câu người đọc hiểu. Quá hạn 24 giờ là lỗi hay gặp nhất nên nói riêng."""
    e = (d or {}).get("error") or {}
    if not isinstance(e, dict):
        return str(e)[:200]
    code, sub = e.get("code"), e.get("error_subcode")
    if code == 10 or sub in (2018278, 2534022):
        return localefmt.chu(
            f"Quá {CUA_SO_TRA_LOI_GIO} giờ kể từ tin cuối của khách nên Meta không cho nhắn nữa. "
            "Trả lời bằng Meta Business Suite hoặc chờ khách nhắn lại.",
            f"More than {CUA_SO_TRA_LOI_GIO} hours since the customer's last message, so Meta will not "
            "let you reply. Use Meta Business Suite or wait for them to write again.")
    if code in (190, 102):
        return localefmt.chu("Token Trang hết hạn hoặc bị thu hồi. Bấm Bật hộp thư lại ở mục Fanpage.",
                             "The Page token expired or was revoked. Turn the inbox on again in the Fanpage section.")
    if code in (200, 230, 299) or "permission" in str(e.get("message") or "").lower():
        return localefmt.chu(
            "Thiếu quyền nhắn tin (pages_messaging). App Facebook chưa được cấp quyền này cho khách thật, "
            "hoặc chưa thêm quyền khi kết nối.",
            "Missing messaging permission (pages_messaging). The Facebook app has not been granted it for "
            "real customers, or the permission was not added when connecting.")
    return str(e.get("message") or "lỗi Send API")[:240]


# ============================================================
# Gọi Graph
# ============================================================
async def _graph(method: str, path: str, token: str, *, params: Optional[dict] = None,
                 json: Optional[dict] = None, timeout: float = 20) -> dict:
    import httpx
    url = f"{GRAPH}/{str(path).lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            if method == "GET":
                r = await c.get(url, params={**(params or {}), "access_token": token})
            else:
                r = await c.post(url, params={"access_token": token}, json=json or {})
        try:
            return r.json()
        except Exception:
            return {"error": {"message": f"HTTP {r.status_code}: {r.text[:160]}"}}
    except Exception as e:
        return {"error": {"message": f"{type(e).__name__}: {e}"}}


async def verify_token(token: str) -> dict:
    """Hỏi Meta token Trang này là Trang nào (khuôn chung của sổ kênh)."""
    tok = str(token or "").strip()
    d = await _graph("GET", "me", tok, params={"fields": "id,name"})
    if d.get("error") or not d.get("id"):
        return {"ok": False, "error": localefmt.chu(
            "Token Trang không hợp lệ hoặc Meta từ chối: " + str((d.get("error") or {}).get("message") or ""),
            "The Page token is not valid or Meta refused it: " + str((d.get("error") or {}).get("message") or ""))}
    return {"ok": True, "username": str(d["id"]), "bot_name": str(d.get("name") or ""),
            "vao_duoc_nhom": False, "account_type": "page"}


async def lay_ten_khach(token: str, psid: str) -> str:
    """Tên hiển thị của khách (cần pages_messaging). Không lấy được thì để trống, tin vẫn vào Hộp thư."""
    d = await _graph("GET", str(psid), token, params={"fields": "name"}, timeout=10)
    return str(d.get("name") or "") if isinstance(d, dict) and not d.get("error") else ""


async def dang_ky_trang(page_id: str, page_token: str, fields: str = "messages,messaging_postbacks") -> dict:
    """Cho app nhận tin của Trang này: POST /{page}/subscribed_apps. Trả {ok, error}."""
    d = await _graph("POST", f"{page_id}/subscribed_apps", page_token,
                     json={"subscribed_fields": [f for f in fields.split(",") if f]})
    if d.get("success"):
        return {"ok": True}
    return {"ok": False, "error": str((d.get("error") or {}).get("message") or d)[:240]}


async def huy_dang_ky_trang(page_id: str, page_token: str) -> dict:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.delete(f"{GRAPH}/{page_id}/subscribed_apps", params={"access_token": page_token})
        d = r.json()
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": bool(d.get("success")), "error": str((d.get("error") or {}).get("message") or "")}


async def gui(tk: dict, chat_id: str, text: str, chat_type: str = "private"):
    """Gửi một tin chữ từ Trang tới `chat_id` (PSID của khách). Trả (ok, lỗi)."""
    token = str((tk or {}).get("token") or "").strip()
    if not token:
        return False, localefmt.chu("tài khoản Messenger này chưa có token Trang",
                                    "this Messenger account has no Page token yet")
    phan = chia_tin(text)
    if not phan:
        return False, localefmt.chu("không có chữ để gửi", "nothing to send")
    for i, p in enumerate(phan):
        d = await _graph("POST", "me/messages", token, json={
            "recipient": {"id": str(chat_id)}, "messaging_type": "RESPONSE", "message": {"text": p}})
        if d.get("error") or not d.get("message_id"):
            return False, loi_gui(d) + (f" (đã gửi {i}/{len(phan)} đoạn)" if i else "")
    return True, ""


# ============================================================
# Lớp vận chuyển bị động
# ============================================================
class Transport:
    """Khuôn giống TelegramBot/ZaloBot đủ để `chatbot_runtime.start_bot` dùng, nhưng KHÔNG poll.

    `cfg_fn` trả bản ghi bot SỐNG (đọc lại mỗi lần: chủ đổi chế độ là có tác dụng ngay).
    `che_do_fn` trả chế độ trả lời của tài khoản. Cả hai do start_bot cấp.
    """

    def __init__(self, token, whitelist, answer_fn, command_fn, **kw):
        self.token = str(token or "")
        self.answer_fn = answer_fn
        self.cfg_fn = kw.get("cfg_fn") or (lambda: {})
        self.che_do_fn = kw.get("che_do_fn") or (lambda: CHE_DO_MAC_DINH)
        self.precheck_fn = kw.get("precheck_fn")
        self.account_id = ""
        self.status = "off"
        self.last_error = ""
        self._task: Optional[asyncio.Task] = None

    async def _giu_song(self):
        while True:
            await asyncio.sleep(3600)

    def start(self):
        self.status = "polling"      # nhãn của sổ trạng thái: ở đây nghĩa là "đang chờ webhook"
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._giu_song())
        if self.account_id:
            _DANG_CHAY[self.account_id] = self

    def stop(self):
        self.status = "stopped"
        if self._task:
            self._task.cancel()
            self._task = None
        if _DANG_CHAY.get(self.account_id) is self:
            _DANG_CHAY.pop(self.account_id, None)

    async def send_text(self, chat_id, text):
        return await gui({"token": self.token}, str(chat_id), str(text or ""))

    def _meta(self, ev: dict, ten: str = "") -> dict:
        return {"chat_id": ev["psid"], "chat_type": "private", "chat_title": "", "user_id": ev["psid"],
                "user_name": ten, "username": "", "message_id": ev.get("mid") or "",
                "account_id": self.account_id, "platform": "messenger", "_kenh": "messenger",
                "mentioned": True, "ts": float(ev.get("ts") or time.time())}

    async def xu_ly(self, ev: dict) -> dict:
        """Một tin khách. Trả {"che_do", "da_ghi", "da_gui", "loi"} để test và nhật ký đọc được."""
        import chatbot_runtime
        cfg = self.cfg_fn() or {}
        ten = ""
        try:
            ten = await lay_ten_khach(self.token, ev["psid"])
        except Exception:      # noqa: BLE001 - không lấy được tên không được làm mất tin
            ten = ""
        meta = self._meta(ev, ten)
        chu = ev.get("text") or ""
        if not chu and ev.get("anh"):
            chu = "[Khách gửi ảnh] " + str(ev["anh"][0])[:300]
            meta["co_anh"] = True
            meta["image_url"] = str(ev["anh"][0])
        elif not chu:
            chu = "[Khách gửi tệp đính kèm]"
        # Ghi tin khách TRƯỚC mọi thứ khác. Các nhánh im của bot (ngoài giờ trực, người chưa được chọn,
        # cuộc chat đã tiếp quản) trả về mà không tự ghi, và tin khách không được mất chỉ vì bot chọn im.
        # Hàm ghi chống trùng theo id tin Meta, nên `answer_fn` ghi lại lần nữa cũng không sinh dòng thứ hai.
        chatbot_runtime.ghi_tin_khach(cfg, meta, chu)
        che_do = self.che_do_fn()
        if che_do != "tu_dong" or not self.answer_fn:
            return {"che_do": "cho_gui", "da_ghi": True, "da_gui": False, "loi": ""}
        try:
            res = await self.answer_fn(chu, meta, None)
        except Exception as e:      # noqa: BLE001
            self.last_error = f"{type(e).__name__}: {e}"[:200]
            return {"che_do": "tu_dong", "da_ghi": True, "da_gui": False, "loi": self.last_error}
        dap = str((res or {}).get("text") or "").strip() if isinstance(res, dict) else ""
        if not dap or (isinstance(res, dict) and res.get("im_lang")):
            return {"che_do": "tu_dong", "da_ghi": True, "da_gui": False, "loi": ""}
        ok, loi = await self.send_text(ev["psid"], dap)
        if not ok:
            self.last_error = loi[:200]
        return {"che_do": "tu_dong", "da_ghi": True, "da_gui": ok, "loi": "" if ok else loi}
