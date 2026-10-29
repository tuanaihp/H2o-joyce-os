"""G2 (hoàn tất): chat trực tiếp, kể cả khung chat của chủ và Telegram/CLI, cũng là lượt chạy thật trong sổ.

    python tests/run.py g2_chat_vao_so      (không mạng, không model; brain tạm)

Phiên của một TRỢ LÝ ghi theo trợ lý (revision = băm nội dung thô file agent) và quyền `allowed_effects` đi theo ngữ cảnh xuống tool của hub.
Chat thường ghi agent "joyce", chưa có revision. Lượt của bot khách KHÔNG ghi hai lần.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import hashlib
import os
import pathlib
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-g2chat-state-")
BR = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g2chat-brains-"))
os.environ["BRAINS_DIR"] = str(BR)
(BR / "nhanh" / "agents").mkdir(parents=True)
AGENT = "---\ntype: agent\nname: Trợ lý chỉ đọc\nallowed_effects: [read]\n---\nBạn chỉ đọc và báo cáo.\n"
(BR / "nhanh" / "agents" / "chi-doc.md").write_text(AGENT, encoding="utf-8", newline="")

import factory  # noqa: E402
import main  # noqa: E402
import run_context as RX  # noqa: E402
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


# ---------------- khung chat của chủ: phiên của một trợ lý
rid, tok = main._so_mo_luot_chat({"channel": "agent:chi-doc"}, "nhanh", "sess1", 7)
r = L.lay(rid)
check("phiên trợ lý: ghi theo TRỢ LÝ, cửa chat, brain là tên thư mục, logical execution theo (phiên, tin)",
      r and r["agent_id"] == "chi-doc" and r["entrypoint"] == "chat" and r["brain_id"] == "nhanh" and r["logical_execution_id"] == "chat:sess1:7", r)
check("revision = SHA-256 nội dung thô file agent (so được với canary)", r["agent_revision"] == hashlib.sha256(AGENT.encode("utf-8")).hexdigest())
ctx = RX.hien_tai()
check("ngữ cảnh lượt được đặt, mang quyền đã khai của file agent", ctx is not None and ctx.run_id == rid and ctx.allowed_effects == ("read",), ctx)
main._so_chot_luot_chat(rid, tok, "completed")
check("chốt lượt: hoàn tất, và ngữ cảnh được gỡ", L.lay(rid)["status"] == "completed" and RX.hien_tai() is None)

# ---------------- chat thường
rid2, tok2 = main._so_mo_luot_chat({"channel": "web"}, "nhanh", "sess2", 1)
r2 = L.lay(rid2)
check("chat thường: ghi là joyce, chưa có revision (không làm bằng chứng canary), quyền chưa khai", r2["agent_id"] == "joyce" and r2["agent_revision"] == ""
      and RX.hien_tai().allowed_effects is None)
main._so_chot_luot_chat(rid2, tok2, "failed")
check("lượt lỗi ghi failed kiểu hệ thống", L.lay(rid2)["status"] == "failed" and L.lay(rid2)["block_kind"] == "system" and RX.hien_tai() is None)
check("run_id rỗng và token rỗng: chốt không nổ", main._so_chot_luot_chat("", None, "completed") is None)

# ---------------- bằng chứng canary và telemetry nhờ chat
for i in range(5):
    a, t = main._so_mo_luot_chat({"channel": "agent:chi-doc"}, "nhanh", "s", 100 + i)
    main._so_chot_luot_chat(a, t, "completed")
check("5 lượt chat với trợ lý: telemetry_ready của file agent đó mở (canary quan sát được)",
      factory.telemetry_ready(None, "nhanh", "agents/chi-doc.md") is True)

# ---------------- chat không-WebSocket
thay = []


async def goc_gia(text, meta=None, progress=None, channel="telegram", bot=None, phien_kho="", ghi_kho=True):
    c = RX.hien_tai()
    thay.append((c.agent_id, c.entrypoint) if c else None)
    if text == "no":
        raise RuntimeError("hỏng")
    if text == "loi":
        return "Lỗi: provider chết"
    return {"text": "chào", "files": []}


main._tg_answer_goc = goc_gia


def chay(text, **kw):
    return asyncio.run(main._tg_answer(text, meta={"chat_id": "42"}, **kw))


def dong_moi(ref_tien_to):
    return [x for x in L.danh_sach(agent_id="joyce") if x["ref"].startswith(ref_tien_to)]


n0 = len(L.danh_sach(agent_id="joyce"))
out = chay("hi", channel="cli")
x = [y for y in L.danh_sach(agent_id="joyce") if y["ref"].startswith("cli:42:")]
check("chat CLI/Telegram: ghi một lượt joyce, hoàn tất, và trong lúc chạy tool thấy ngữ cảnh", out["text"] == "chào" and len(x) == 1 and x[0]["status"] == "completed"
      and thay[-1] == ("joyce", "chat"), (x, thay))
chay("loi", channel="telegram")
y = [z for z in L.danh_sach(agent_id="joyce") if z["ref"].startswith("telegram:42:")]
check("lượt trả CHUỖI lỗi được ghi failed", len(y) == 1 and y[0]["status"] == "failed", y)
try:
    chay("no", channel="cli")
except RuntimeError:
    pass
z = [w for w in L.danh_sach(agent_id="joyce") if w["status"] == "failed" and w["ref"].startswith("cli:42:")]
check("lượt nổ lỗi: lỗi vẫn tới người gọi, sổ chốt failed, ngữ cảnh được gỡ", len(z) == 1 and RX.hien_tai() is None, z)

so_truoc = len(L.danh_sach(agent_id="joyce"))
chay("hi", channel="zalo", bot={"id": "b"})
check("lượt của BOT đi thẳng, không ghi hai lần (chatbot_runtime đã ghi theo agent của bot)", len(L.danh_sach(agent_id="joyce")) == so_truoc and thay[-1] is None, thay[-1])

# ---------------- sổ hỏng không làm hỏng chat
_d = L._duong_dan
L.dong()
L._duong_dan = lambda: pathlib.Path(tempfile.gettempdir()) / "khong-ton-tai-g2chat" / "a" / "so.sqlite3"
check("sổ hỏng hẳn: chat vẫn trả lời bình thường", chay("hi", channel="cli")["text"] == "chào")
r_, t_ = main._so_mo_luot_chat({"channel": "agent:chi-doc"}, "nhanh", "s", 1)
check("sổ hỏng hẳn: mở lượt chat trả rỗng, không nổ", r_ == "" and t_ is None)
L._duong_dan = _d

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g2_chat_vao_so: tất cả pass")
