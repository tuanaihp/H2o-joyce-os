"""G2 (Joyce Harness): ngữ cảnh lượt chạy do host đặt và quyết định quyền chung ở tool ghi file của MCP Hub.

    python tests/run.py g2_ngu_canh_quyen      (không mạng, không model; chỉ ghi trong vault tạm)

Phạm vi nói thẳng: mới nối cho tool `joyce_write_file` (effect internal_write) và ba cửa đã ghi sổ lượt chạy. Agent KHÔNG khai
`allowed_effects` vẫn chạy như cũ (đó là khoảng hở, không phải xanh); tool khác của hub chưa hỏi quyết định này.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import pathlib
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-g2-state-")

import mcp_hub  # noqa: E402
import run_context as RX  # noqa: E402
import run_ledger as L  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


# ---------------- đọc allowed_effects từ file agent
def agent(eff_dong=""):
    return "---\ntype: agent\nname: A\n" + eff_dong + "---\nThân.\n"


check("không khai allowed_effects: None (tương thích, ghi nhận là khoảng hở)", RX.doc_allowed_effects(agent()) is None)
check("khai danh sách", RX.doc_allowed_effects(agent("allowed_effects: [read, internal_write]\n")) == ("read", "internal_write"))
check("khai rỗng nghĩa là chỉ tính toán: tuple rỗng, khác None", RX.doc_allowed_effects(agent("allowed_effects: []\n")) == ())
check("khai kiểu chuỗi đơn", RX.doc_allowed_effects(agent("allowed_effects: read\n")) == ("read",))
check("YAML hỏng hoặc kiểu lạ: None (không đoán)", RX.doc_allowed_effects(agent("allowed_effects: {a: 1}\n")) is None
      and RX.doc_allowed_effects("---\nallowed_effects: [\n---\nx") is None and RX.doc_allowed_effects("không có frontmatter") is None)

# ---------------- quyết định
c0 = RX.RunContext("r", "a", "b", "bot", None)
c1 = RX.RunContext("r", "a", "b", "bot", ("read",))
c2 = RX.RunContext("r", "a", "b", "bot", ("read", "internal_write"))
c3 = RX.RunContext("r", "a", "b", "bot", ())
check("không ngữ cảnh: cho phép, lý do khong_ngu_canh", RX.cho_phep("internal_write", None) == (True, "khong_ngu_canh"))
check("agent chưa khai: cho phép, lý do chua_khai_bao", RX.cho_phep("external_write", c0) == (True, "chua_khai_bao"))
check("đã khai và có effect: cho phép", RX.cho_phep("internal_write", c2) == (True, "trong_grant"))
check("đã khai mà thiếu effect: CHẶN", RX.cho_phep("internal_write", c1) == (False, "ngoai_grant"))
check("khai rỗng: chặn mọi effect", RX.cho_phep("internal_write", c3)[0] is False and RX.cho_phep("read", c3)[0] is False)
check("effect lạ khi agent đã khai: chặn (không biết thì không cho)", RX.cho_phep("lam_gi_do", c2) == (False, "effect_la:lam_gi_do"))
check("effect lạ khi agent chưa khai: cho phép như cũ", RX.cho_phep("lam_gi_do", c0)[0] is True)

# ---------------- contextvar đi theo task và thread
tok = RX.dat(c1)
check("hien_tai thấy ngữ cảnh vừa đặt", RX.hien_tai() is c1)


async def con():
    a = RX.hien_tai()
    b = await asyncio.to_thread(RX.hien_tai)
    t = await asyncio.create_task(asyncio.sleep(0, result=RX.hien_tai()))
    return a, b, t


RX.go(tok)
check("gỡ ngữ cảnh trả về trạng thái trước", RX.hien_tai() is None)


async def chay_trong_ctx():
    tk = RX.dat(c1)
    try:
        return await con()
    finally:
        RX.go(tk)


x = asyncio.run(chay_trong_ctx())
check("ngữ cảnh đi theo cả coroutine, thread của to_thread và task con", all(v is c1 for v in x), x)
check("sau khi gỡ, không rò sang lượt khác", RX.hien_tai() is None)

# ---------------- ép ở tool ghi file của hub
v = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g2-vault-"))
(v / "wiki").mkdir()


def ghi(path, content="N"):
    tools, route = mcp_hub._builtin_tools("full", str(v))
    return asyncio.run(route["joyce_write_file"]["call"]({"path": path, "content": content}))


def ghi_trong(ctx, path):
    async def _():
        tk = RX.dat(ctx)
        try:
            tools, route = mcp_hub._builtin_tools("full", str(v))
            return await route["joyce_write_file"]["call"]({"path": path, "content": "N"})
        finally:
            RX.go(tk)
    return asyncio.run(_())


check("không ngữ cảnh: ghi như cũ", str(ghi("wiki/a.md")).startswith("Đã ghi") and (v / "wiki" / "a.md").exists())
check("agent chưa khai: ghi như cũ", str(ghi_trong(c0, "wiki/b.md")).startswith("Đã ghi"))
check("agent khai có internal_write: ghi được", str(ghi_trong(c2, "wiki/c.md")).startswith("Đã ghi"))
r = ghi_trong(c1, "wiki/d.md")
check("agent khai chỉ read: CHẶN, nói rõ lý do, file không được tạo", str(r).startswith("ERROR") and "allowed_effects" in str(r) and not (v / "wiki" / "d.md").exists(), r)
check("agent khai rỗng: chặn", str(ghi_trong(c3, "wiki/e.md")).startswith("ERROR") and not (v / "wiki" / "e.md").exists())
check("chính sách đường dẫn vẫn chạy cho agent được cấp (sources bất biến)", (lambda: (v / "sources").mkdir() or (v / "sources" / "g.md").write_text("G") or True)()
      and str(ghi_trong(c2, "sources/g.md")).startswith("ERROR") and (v / "sources" / "g.md").read_text() == "G")

# ---------------- ba cửa đặt ngữ cảnh
root = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g2-brain-"))
(root / "agents").mkdir()
(root / "agents" / "chi-doc.md").write_text(agent("allowed_effects: [read]\n"), encoding="utf-8")
rid = L.bat_dau(brain_id="nhanh", agent_id="chi-doc", entrypoint="bot", revision={"agent_revision": "x"})
ctx = L.ngu_canh(rid, root)
check("dựng ngữ cảnh từ dòng sổ và file agent thật: có run_id, agent, brain, effect đã khai",
      ctx and ctx.run_id == rid and ctx.agent_id == "chi-doc" and ctx.brain_id == "nhanh" and ctx.allowed_effects == ("read",), ctx)
check("lượt không có trong sổ: None, route chạy không ngữ cảnh", L.ngu_canh("khong-co", root) is None)

import chatbot_runtime as CR  # noqa: E402
CR._deps["brain_root"] = lambda brain: str(root)
tk = CR._so_ngu_canh(rid)
check("cửa bot đặt ngữ cảnh đúng agent và gỡ được", RX.hien_tai() is not None and RX.hien_tai().agent_id == "chi-doc")
CR._so_go_ngu_canh(tk)
check("gỡ xong thì sạch", RX.hien_tai() is None)
check("cửa bot với run_id rỗng không làm gì", CR._so_ngu_canh("") is None and RX.hien_tai() is None)

import tasks  # noqa: E402
tf = object.__new__(tasks.TasksFeature)
tk2 = tf._so_ngu_canh_viec(rid, str(root))
check("cửa việc đặt ngữ cảnh đúng", RX.hien_tai() is not None and RX.hien_tai().allowed_effects == ("read",))
RX.go(tk2)
check("cửa việc: gỡ xong thì sạch", RX.hien_tai() is None)


async def worker_thay():
    """Worker tạo bằng create_task SAU khi đặt ngữ cảnh thì thấy ngữ cảnh, dù coroutine cha đã gỡ nó."""
    tk3 = tf._so_ngu_canh_viec(rid, str(root))

    async def w():
        await asyncio.sleep(0.05)
        return RX.hien_tai()
    t = asyncio.create_task(w())
    RX.go(tk3)
    return await t, RX.hien_tai()


tw, cha = asyncio.run(worker_thay())
check("worker thấy ngữ cảnh lúc được tạo, còn coroutine cha đã gỡ (không rò sang việc khác)", tw is not None and tw.agent_id == "chi-doc" and cha is None)

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g2_ngu_canh_quyen: tất cả pass")
