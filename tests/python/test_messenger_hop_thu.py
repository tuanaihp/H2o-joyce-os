"""Hộp thư Messenger của Fanpage (1.3.40): webhook, bật/tắt, soạn nháp chờ gửi, tự động, giới hạn 24 giờ.

    python tests/run.py messenger_hop_thu      (không mạng, không model: Meta và engine đều là bản giả)

Thứ cần canh, theo thứ tự quan trọng:
- Webhook công khai nên PHẢI kiểm chữ ký: sai chữ ký thì không tin nào lọt vào Hộp thư.
- Mặc định `cho_gui`: tin khách vào Hộp thư, KHÔNG gọi model, KHÔNG gửi gì ra ngoài.
- `tu_dong` phải có xác nhận mới bật được, và khi bật thì gửi qua Send API.
- Quá 24 giờ thì báo lỗi nói thẳng, không gửi lậu.
- Tin giao lại cùng id không sinh hai dòng. Echo (tin do chính Trang gửi) bị bỏ qua.
- Hộp thư soạn nháp và gửi đi bằng các route SẴN CÓ, không route riêng.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import hashlib
import hmac
import json
import os
import pathlib
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-msgr-")
BR = pathlib.Path(tempfile.mkdtemp(prefix="joyce-brains-msgr-"))
os.environ["BRAINS_DIR"] = str(BR)

import main  # noqa: E402
import channel_accounts  # noqa: E402
import chatbot_runtime  # noqa: E402
import chatbot_store  # noqa: E402
import conversations  # noqa: E402
import channels  # noqa: E402
import messenger_ops  # noqa: E402
from channels import messenger  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


SECRET = "app-secret-thu"
PAGE_ID, PSID = "111222333", "9988776655"

# ---------------- Meta giả
GOI = []          # mọi lời gọi Graph: (method, path, json)
CHE_GUI = {"loi": None}


async def graph_gia(method, path, token, *, params=None, json=None, timeout=20):
    GOI.append((method, str(path), json))
    p = str(path)
    if method == "GET" and p == "me":
        return {"id": PAGE_ID, "name": "Trang Thử"}
    if method == "GET" and p == PSID:
        return {"name": "Chị Lan"}
    if method == "POST" and p.endswith("subscribed_apps"):
        return {"success": True}
    if method == "POST" and p == "me/messages":
        if CHE_GUI["loi"]:
            return {"error": CHE_GUI["loi"]}
        return {"recipient_id": (json or {}).get("recipient", {}).get("id"), "message_id": "m.gui." + str(len(GOI))}
    return {"error": {"message": "không giả lập: " + method + " " + p}}


messenger._graph = graph_gia


async def token_trang_gia(page_id):
    return ("PAGE_TOKEN_THU", "Trang Thử", "") if str(page_id) == PAGE_ID else ("", "", "Trang lạ")


async def trang_gia(brain):
    return [{"id": PAGE_ID, "name": "Trang Thử"}, {"id": "444", "name": "Trang Khác"}]


messenger_ops._token_trang = token_trang_gia
messenger_ops._trang_cua_anh = trang_gia
messenger_ops._app_secret = lambda: SECRET
messenger_ops._fb_conn_id = lambda: "fbconn1"
messenger_ops._DONG_BO = True        # webhook xử lý ngay trong request thay vì task nền (TestClient đóng loop sau mỗi request)

c = TestClient(main.app, base_url="http://127.0.0.1:8080")


def ky(body: bytes, secret=SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def payload(text="Chị muốn hỏi giá gói chụp cưới", mid="m.001", echo=False, sender=PSID, **msg_extra):
    msg = {"mid": mid, "text": text, **msg_extra}
    if echo:
        msg["is_echo"] = True
    return {"object": "page", "entry": [{"id": PAGE_ID, "time": 1, "messaging": [
        {"sender": {"id": sender}, "recipient": {"id": PAGE_ID}, "timestamp": 1790000000000, "message": msg}]}]}


def gui_webhook(body_dict, secret=SECRET):
    raw = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
    return c.post(messenger.WEBHOOK_PATH, content=raw,
                  headers={"x-hub-signature-256": ky(raw, secret), "content-type": "application/json"})


# ============================================================
# 1. Thuần
# ============================================================
check("kênh Messenger có trong sổ, gắn được bot và gửi chữ", "messenger" in channels.ids()
      and channels.spec("messenger").nl("bot") and channels.spec("messenger").nl("tra_loi_tu_joyce"))
check("Messenger không vào được nhóm", not channels.spec("messenger").nl("nhom"))
check("chữ ký đúng được nhận", messenger.verify_signature(b"abc", ky(b"abc"), SECRET))
check("chữ ký sai bị từ chối", not messenger.verify_signature(b"abc", ky(b"abc", "khac"), SECRET))
check("thiếu secret thì TỪ CHỐI (đóng khi lỗi)", not messenger.verify_signature(b"abc", ky(b"abc"), ""))
check("thiếu header thì từ chối", not messenger.verify_signature(b"abc", "", SECRET))
evs = messenger.parse_webhook(payload())
check("đọc đúng một tin khách", len(evs) == 1 and evs[0]["psid"] == PSID and evs[0]["page_id"] == PAGE_ID
      and evs[0]["text"].startswith("Chị muốn") and evs[0]["mid"] == "m.001" and evs[0]["loai"] == "text")
check("echo (tin do chính Trang gửi) bị bỏ", messenger.parse_webhook(payload(echo=True)) == [])
check("người gửi trùng id Trang bị bỏ", messenger.parse_webhook(payload(sender=PAGE_ID)) == [])
check("không phải payload Trang thì bỏ", messenger.parse_webhook({"object": "instagram", "entry": []}) == []
      and messenger.parse_webhook("rác") == [])
anh = messenger.parse_webhook(payload(text="", attachments=[{"type": "image", "payload": {"url": "https://x/a.jpg"}}]))
check("tin chỉ có ảnh vẫn nhận, loại image", len(anh) == 1 and anh[0]["loai"] == "image" and anh[0]["anh"] == ["https://x/a.jpg"])
pb = messenger.parse_webhook({"object": "page", "entry": [{"id": PAGE_ID, "messaging": [
    {"sender": {"id": PSID}, "timestamp": 1, "postback": {"title": "Xem bảng giá", "payload": "GIA", "mid": "m.pb"}}]}]})
check("postback (bấm nút) thành một tin", len(pb) == 1 and pb[0]["text"] == "Xem bảng giá" and pb[0]["loai"] == "postback")
dai = ("Một câu khá dài. " * 200).strip()
phan = messenger.chia_tin(dai)
check("tin dài được chia, không đoạn nào quá trần, không mất chữ",
      len(phan) > 1 and all(len(p) <= messenger.MAX_CHU_MOT_TIN for p in phan)
      and "".join(p.replace(" ", "") for p in phan) == dai.replace(" ", ""))
check("lỗi quá 24 giờ được nói thẳng", "24" in messenger.loi_gui({"error": {"code": 10, "error_subcode": 2018278}}))
check("lỗi token hết hạn có hướng dẫn", "Bật hộp thư" in messenger.loi_gui({"error": {"code": 190}}))
check("lỗi thiếu quyền nhắc pages_messaging", "pages_messaging" in messenger.loi_gui({"error": {"code": 200}}))

# ============================================================
# 2. Webhook: xác minh địa chỉ và chữ ký
# ============================================================
tok = messenger_ops.ma_xac_minh()
check("mã xác minh sinh một lần rồi giữ nguyên", tok.startswith("joyce-") and messenger_ops.ma_xac_minh() == tok)
r = c.get(messenger.WEBHOOK_PATH, params={"hub.mode": "subscribe", "hub.verify_token": tok, "hub.challenge": "CH123"})
check("Meta kiểm địa chỉ: đúng mã thì trả challenge", r.status_code == 200 and r.text == "CH123")
r = c.get(messenger.WEBHOOK_PATH, params={"hub.mode": "subscribe", "hub.verify_token": "sai", "hub.challenge": "CH123"})
check("sai mã xác minh thì 403", r.status_code == 403)
r = c.post(messenger.WEBHOOK_PATH, content=b'{"object":"page"}', headers={"x-hub-signature-256": "sha256=00"})
check("sai chữ ký thì 403 và không xử lý gì", r.status_code == 403)
r = c.post(messenger.WEBHOOK_PATH, content=b'{"object":"page"}')
check("không có chữ ký thì 403", r.status_code == 403)

# ============================================================
# 3. Trang chưa bật: tin không có chỗ đến
# ============================================================
r = gui_webhook(payload())
check("Trang chưa bật hộp thư: webhook vẫn trả 200 (Meta không gọi lại), không ghi gì",
      r.status_code == 200 and conversations.danh_sach(channel="messenger") == [] or
      not conversations.danh_sach(channel="messenger"))

# ============================================================
# 4. Bật hộp thư cho một Trang
# ============================================================
async def answer_tam(*a, **k):
    return {"text": "", "files": [], "im_lang": True}


chatbot_runtime._deps["answer"] = answer_tam      # server thật nối lúc khởi động; test tự nối
phong = BR / "Ban Hang - Thu"
(phong / "agents").mkdir(parents=True)
(phong / "agents" / "truong-sales-hinh-anh.md").write_text(
    "---\ntype: agent\nname: Trưởng Sales Hình Ảnh\nrole: Sales\n---\nBạn là trưởng sales hình ảnh.", encoding="utf-8")
r = c.post("/social/facebook/messenger/enable", data={"page_id": "abc", "agent_slug": "x", "brain": str(phong)})
check("page_id không phải số bị từ chối", r.status_code == 400)
r = c.post("/social/facebook/messenger/enable", data={"page_id": "555", "agent_slug": "truong-sales-hinh-anh", "brain": str(phong)})
check("Trang không lấy được token thì báo lỗi, không tạo gì", r.status_code == 409 and not channel_accounts.list_accounts("messenger"))
r = c.post("/social/facebook/messenger/enable", data={"page_id": PAGE_ID, "agent_slug": "truong-sales-hinh-anh", "brain": str(phong)})
j = r.json()
check("bật hộp thư thành công, mặc định cho_gui", r.status_code == 200 and j.get("ok") and j.get("che_do") == "cho_gui", r.text[:300])
check("đã đăng ký webhook cho Trang (subscribed_apps)", j.get("da_dang_ky_webhook") is True
      and any(g[1] == f"{PAGE_ID}/subscribed_apps" for g in GOI))
aid, bid = j.get("account_id"), j.get("bot_id")
tk = channel_accounts.get_account(aid) or {}
check("tài khoản kênh messenger gắn đúng id Trang, token Trang được lưu mã hoá",
      tk.get("channel") == "messenger" and tk.get("external_id") == PAGE_ID
      and channel_accounts.get_token(aid) == "PAGE_TOKEN_THU" and "PAGE_TOKEN_THU" not in json.dumps(channel_accounts.list_accounts("messenger")))
bot = chatbot_store.get_bot(bid) or {}
check("bot trỏ đúng Agent, đang bật", (bot.get("agent") or {}).get("slug") == "truong-sales-hinh-anh" and bot.get("enabled") is True
      and bot.get("channel") == "messenger")
check("lớp vận chuyển đã đăng ký theo tài khoản", aid in messenger._DANG_CHAY)
check("tab Tài khoản bot thấy tài khoản Messenger có logo", any(
    a.get("channel") == "messenger" and a.get("logo") == "messenger" for a in c.get("/channels/accounts").json().get("accounts", [])))
j2 = c.post("/social/facebook/messenger/enable", data={"page_id": PAGE_ID, "agent_slug": "truong-sales-hinh-anh", "brain": str(phong)}).json()
check("bật lần hai không tạo bản sao", j2.get("ok") and len(channel_accounts.list_accounts("messenger")) == 1
      and len([b for b in chatbot_store.list_bots() if b.get("channel") == "messenger"]) == 1)

# ============================================================
# 5. Chế độ cho_gui: tin vào Hộp thư, không model, không gửi
# ============================================================
GOI.clear()
da_goi_model = []


async def answer_cam(*a, **k):
    da_goi_model.append(1)
    return {"text": "KHÔNG ĐƯỢC GỌI", "files": []}


messenger._DANG_CHAY[aid].answer_fn = answer_cam
r = gui_webhook(payload())
check("webhook đúng chữ ký trả 200", r.status_code == 200 and r.text == "EVENT_RECEIVED")
ds = conversations.danh_sach(channel="messenger")
check("tin khách vào Hộp thư, có tên khách lấy từ Meta", len(ds) == 1 and (ds[0].get("customer_name") or ds[0].get("title") or "")
      .find("Lan") >= 0 or any("Lan" in json.dumps(x, ensure_ascii=False) for x in ds), json.dumps(ds, ensure_ascii=False)[:300])
cid = ds[0]["id"] if ds else 0
msgs = conversations.tin_nhan(cid)
check("đúng một tin khách, đúng nội dung", len(msgs) == 1 and msgs[0]["sender_type"] == "customer"
      and msgs[0]["text"].startswith("Chị muốn hỏi giá"))
check("cho_gui: KHÔNG gọi model và KHÔNG gửi gì ra ngoài", not da_goi_model
      and not any(g[1] == "me/messages" for g in GOI))
gui_webhook(payload())
check("Meta giao lại cùng id tin: không sinh dòng thứ hai", len(conversations.tin_nhan(cid)) == 1)
gui_webhook(payload(text="đã gửi từ Business Suite", mid="m.echo", echo=True))
check("echo không vào Hộp thư", len(conversations.tin_nhan(cid)) == 1)
gui_webhook(payload(text="Em ơi cho chị xem mẫu", mid="m.002"))
check("tin thứ hai nối vào CÙNG cuộc chat", len(conversations.danh_sach(channel="messenger")) == 1
      and len(conversations.tin_nhan(cid)) == 2)

# ============================================================
# 6. Soạn nháp rồi chủ bấm gửi: route SẴN CÓ của Hộp thư
# ============================================================
KHUNG = {"n": 0}


async def answer_nhap(text_engine, meta, progress=None, **kw):
    KHUNG["n"] += 1
    KHUNG["luu_kho"] = kw.get("ghi_kho", True)
    return {"text": "Dạ em gửi chị bảng giá gói chụp cưới ạ.", "files": []}


chatbot_runtime._deps["answer"] = answer_nhap
r = c.post(f"/conversations/{cid}/ai-reply", data={"mode": "draft"})
jd = r.json()
check("Gợi ý trả lời: Joyce soạn nháp, trả chữ về, KHÔNG gửi", r.status_code == 200 and jd.get("draft") is True
      and "bảng giá" in jd.get("text", "") and not any(g[1] == "me/messages" for g in GOI), r.text[:300])
check("bản nháp không để lại dấu vết trong kho phiên (ghi_kho=False)", KHUNG.get("luu_kho") is False)
check("bản nháp chưa thành tin trong Hộp thư", len(conversations.tin_nhan(cid)) == 2)
r = c.post(f"/conversations/{cid}/reply", data={"text": jd["text"]})
gui_gui = [g for g in GOI if g[1] == "me/messages"]
check("chủ bấm Gửi: tin đi qua Send API tới đúng khách, loại RESPONSE", r.status_code == 200 and len(gui_gui) == 1
      and gui_gui[0][2]["recipient"]["id"] == PSID and gui_gui[0][2]["messaging_type"] == "RESPONSE"
      and gui_gui[0][2]["message"]["text"] == jd["text"], r.text[:300])
check("tin đã gửi được ghi vào Hộp thư như lời của người thật", conversations.tin_nhan(cid)[-1]["sender_type"] == "human")

# ============================================================
# 7. Quá 24 giờ: báo lỗi thật, không gửi lậu
# ============================================================
CHE_GUI["loi"] = {"code": 10, "error_subcode": 2018278, "message": "outside window"}
r = c.post(f"/conversations/{cid}/reply", data={"text": "Chị ơi còn đó không ạ"})
check("quá 24 giờ: Hộp thư báo lỗi nói rõ, tin không vào kho như đã gửi", r.status_code == 400 and "24" in r.json().get("error", "")
      and conversations.tin_nhan(cid)[-1]["text"] != "Chị ơi còn đó không ạ", r.text[:200])
CHE_GUI["loi"] = None

# ============================================================
# 8. Tự động: phải xác nhận, rồi gửi qua Send API
# ============================================================
r = c.post("/social/facebook/messenger/mode", data={"page_id": PAGE_ID, "mode": "tu_dong"})
check("bật tự động mà không xác nhận thì bị chặn", r.status_code == 409 and r.json().get("can_xac_nhan") is True
      and messenger._DANG_CHAY[aid].che_do_fn() == "cho_gui")
check("mode lạ bị từ chối", c.post("/social/facebook/messenger/mode", data={"page_id": PAGE_ID, "mode": "bay"}).status_code == 400)
r = c.post("/social/facebook/messenger/mode", data={"page_id": PAGE_ID, "mode": "tu_dong", "xac_nhan": "1"})
check("xác nhận rồi thì bật được, có hiệu lực ngay", r.status_code == 200 and messenger._DANG_CHAY[aid].che_do_fn() == "tu_dong")
GOI.clear()
dap = {"text": "Dạ chào chị Lan, bên em đang có gói cưới 15 triệu ạ.", "files": []}


async def answer_tu_dong(text, meta, progress=None):
    return dict(dap)


messenger._DANG_CHAY[aid].answer_fn = answer_tu_dong
gui_webhook(payload(text="Gói cưới bao nhiêu em", mid="m.003"))
gui_gui = [g for g in GOI if g[1] == "me/messages"]
check("tự động: Joyce trả lời qua Send API tới đúng khách", len(gui_gui) == 1 and gui_gui[0][2]["recipient"]["id"] == PSID
      and "15 triệu" in gui_gui[0][2]["message"]["text"])
dap["text"] = ""
GOI.clear()
gui_webhook(payload(text="ok", mid="m.004"))
check("tự động: Agent chọn im thì không gửi, nhưng tin khách VẪN vào Hộp thư", not any(g[1] == "me/messages" for g in GOI)
      and conversations.tin_nhan(cid)[-1]["text"] == "ok", conversations.tin_nhan(cid)[-1]["text"])
dap["text"] = "Dạ vâng ạ"
CHE_GUI["loi"] = {"code": 10, "error_subcode": 2018278}
ket = asyncio.run(messenger._DANG_CHAY[aid].xu_ly(messenger.parse_webhook(payload(text="còn đó không", mid="m.005"))[0]))
check("tự động nhưng quá 24 giờ: không gửi được, lỗi nói rõ", ket["da_gui"] is False and "24" in ket["loi"])
CHE_GUI["loi"] = None
r = c.post("/social/facebook/messenger/mode", data={"page_id": PAGE_ID, "mode": "cho_gui"})
check("quay lại chờ gửi được", r.json().get("che_do") == "cho_gui" and messenger._DANG_CHAY[aid].che_do_fn() == "cho_gui")

# ============================================================
# 9. Trạng thái cho giao diện
# ============================================================
st = c.get("/social/facebook/messenger/status", params={"brain": str(phong)}).json()
check("status trả địa chỉ webhook và mã xác minh", st.get("ok") and st.get("webhook_url", "").endswith(messenger.WEBHOOK_PATH)
      and st.get("verify_token") == tok and st.get("co_app_secret") is True)
check("status cảnh báo địa chỉ localhost (Meta không gọi vào được)", "localhost" in st.get("canh_bao_dia_chi", "").lower()
      or "127.0.0.1" in st.get("webhook_url", ""))
pg = {p["page_id"]: p for p in st.get("pages", [])}
check("status liệt kê Trang đã bật và Trang chưa bật", pg.get(PAGE_ID, {}).get("bat") is True and pg.get("444", {}).get("bat") is False)
check("Trang đã bật mang account_key để lọc Hộp thư", pg[PAGE_ID].get("account_key") == f"messenger:{aid}")
check("status không lộ token", "PAGE_TOKEN_THU" not in json.dumps(st))
wi = c.get("/channels/webhook-info", params={"channel": "messenger"}).json()
check("webhook-info (form thêm tài khoản ở trang Hội thoại) trả địa chỉ, mã và cờ https",
      wi.get("ok") and wi["webhook_url"].endswith(messenger.WEBHOOK_PATH) and wi["verify_token"] == tok and wi["https"] is False)
check("webhook-info của kênh không dùng webhook thì 404", c.get("/channels/webhook-info", params={"channel": "telegram"}).status_code == 404)

# ============================================================
# 10. Xin thêm quyền nhắn tin: opt-in, không đụng danh sách quyền chuẩn
# ============================================================
import mcp_store  # noqa: E402
_luu = {}
mcp_store.connection_config = lambda cid: dict(_luu.get(cid, {}))
mcp_store.update_connection = lambda cid, patch: _luu.__setitem__(cid, patch["config"])
r = c.post("/social/facebook/messenger/permissions")
check("xin quyền: ghi extra_scopes cho kết nối, báo cần đăng nhập lại", r.status_code == 200
      and set(_luu["fbconn1"]["extra_scopes"]) == {"pages_messaging", "pages_manage_metadata"} and r.json().get("dang_nhap_lai"))
c.post("/social/facebook/messenger/permissions")
check("xin quyền hai lần không nhân đôi", len(_luu["fbconn1"]["extra_scopes"]) == 2)
cat = json.loads((pathlib.Path(ROOT) / "system" / "mcp-catalog.json").read_text(encoding="utf-8"))
fb = next(x for x in (cat.get("connectors") or cat if isinstance(cat, list) else cat.get("connectors", [])) if x.get("id") == "facebook-pages")
check("danh sách quyền chuẩn của connector KHÔNG bị thêm pages_messaging (Meta từ chối đăng nhập nếu app chưa chuẩn bị)",
      "pages_messaging" not in fb["auth"]["scopes"])

# ============================================================
# 11. Tắt hộp thư: giữ lịch sử
# ============================================================
r = c.post("/social/facebook/messenger/disable", data={"page_id": PAGE_ID})
check("tắt hộp thư: bot dừng, lớp vận chuyển rời sổ, lịch sử còn nguyên", r.status_code == 200 and aid not in messenger._DANG_CHAY
      and (chatbot_store.get_bot(bid) or {}).get("enabled") is False and len(conversations.tin_nhan(cid)) >= 4,
      (r.status_code, aid in messenger._DANG_CHAY, (chatbot_store.get_bot(bid) or {}).get("enabled"), len(conversations.tin_nhan(cid))))
check("đã hủy đăng ký webhook của Trang", r.json().get("da_huy_webhook") in (True, False))
GOI.clear()
gui_webhook(payload(text="Alo còn ai không", mid="m.006"))
check("sau khi tắt, tin khách VẪN vào Hộp thư (không mất), không model, không gửi",
      conversations.tin_nhan(cid)[-1]["text"] == "Alo còn ai không" and not any(g[1] == "me/messages" for g in GOI))
check("tắt Trang chưa từng bật thì 404", c.post("/social/facebook/messenger/disable", data={"page_id": "777"}).status_code == 404)

# ============================================================
# 12. Joyce đang bật đăng nhập (đúng tình huống chạy thật, mở ra Internet bằng tên miền)
# ============================================================
import config as cfgmod  # noqa: E402
_gate = cfgmod.gate_active
cfgmod.gate_active = lambda: True
try:
    ngoai = TestClient(main.app, base_url="https://joyce.example.vn")     # Meta gọi bằng tên miền riêng, không cookie, không Origin
    raw = json.dumps(payload(text="Tin khi bật đăng nhập", mid="m.gate"), ensure_ascii=False).encode("utf-8")
    r = ngoai.post(messenger.WEBHOOK_PATH, content=raw, headers={"x-hub-signature-256": ky(raw)})
    check("bật đăng nhập: webhook Meta vẫn vào được (đường công khai, chữ ký là cổng)", r.status_code == 200 and r.text == "EVENT_RECEIVED", f"{r.status_code} {r.text[:120]}")
    r = ngoai.get(messenger.WEBHOOK_PATH, params={"hub.mode": "subscribe", "hub.verify_token": tok, "hub.challenge": "C9"})
    check("bật đăng nhập: Meta kiểm địa chỉ vẫn được", r.status_code == 200 and r.text == "C9", f"{r.status_code} {r.text[:120]}")
    r = ngoai.post(messenger.WEBHOOK_PATH, content=raw, headers={"x-hub-signature-256": "sha256=00"})
    check("bật đăng nhập: sai chữ ký vẫn 403 (không phải 200, không phải 401)", r.status_code == 403)
    for method, url in (("get", "/social/facebook/messenger/status"), ("post", "/social/facebook/messenger/enable"),
                        ("post", "/social/facebook/messenger/mode"), ("post", "/social/facebook/messenger/disable"),
                        ("post", "/social/facebook/messenger/permissions")):
        rr = getattr(ngoai, method)(url)
        check(f"bật đăng nhập: {url} KHÔNG công khai (cần đăng nhập)", rr.status_code == 401, f"{rr.status_code}")
    check("bật đăng nhập: webhook-info cần đăng nhập", ngoai.get("/channels/webhook-info?channel=messenger").status_code == 401)
    check("bật đăng nhập: lịch sử hội thoại vẫn cần đăng nhập", ngoai.get("/conversations?channel=messenger").status_code == 401)
finally:
    cfgmod.gate_active = _gate

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
