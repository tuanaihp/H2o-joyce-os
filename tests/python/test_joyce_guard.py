"""Plugin bundled joyce-guard: ba luật cố định trước mỗi lời gọi tool (Joyce Harness, giai đoạn 0A).

    python tests/run.py joyce_guard      (không mạng, không model)

Chạy qua đúng đường thật: plugins_host nạp plugin, wrap_with_hooks bọc tool, hook trả deny thì tool
KHÔNG chạy và model nhận câu lý do.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import pathlib
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-guardtest-")

import plugins_host  # noqa: E402
import turn_context  # noqa: E402

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


desc = {d["slug"]: d for d in plugins_host.describe(None)}
check("joyce-guard có mặt, bật mặc định và nạp được", desc.get("joyce-guard", {}).get("enabled") is True
      and desc["joyce-guard"].get("loaded") is True)
check("có hook nên hub bọc mọi tool", plugins_host.has_tool_hooks(None))

vault = pathlib.Path(tempfile.mkdtemp(prefix="joyce-guard-vault-"))
(vault / "sources").mkdir()
(vault / "sources" / "hop-dong-goc.md").write_text("bản gốc", encoding="utf-8")
da_chay = []


def _tool(fn):
    async def base(args):
        da_chay.append(fn)
        return "OK"
    return plugins_host.wrap_with_hooks(fn, base, "full", str(vault))


def goi(fn, args, turn=None):
    da_chay.clear()
    tok = turn_context.bind(turn) if turn is not None else None
    try:
        kq = asyncio.run(_tool(fn)(args))
    finally:
        if tok is not None:
            turn_context.reset(tok)
    return kq, bool(da_chay)


CHU = turn_context.make("dashboard", "owner", "private", "web:1", la_chu=True)
KHACH = turn_context.make("telegram", "998877", "private", "998877", la_chu=False)

# ---- luật 1: file
kq, chay = goi("joyce_write_file", {"path": "sources/hop-dong-goc.md", "content": "x"})
check("ghi đè file đã có trong sources/ bị chặn, tool không chạy", not chay and "[joyce-guard]" in kq and "bất biến" in kq)
kq, chay = goi("joyce_write_file", {"path": str(vault / "sources" / "hop-dong-goc.md"), "content": "x"})
check("ghi đè bằng đường dẫn tuyệt đối cũng bị chặn", not chay)
_, chay = goi("joyce_write_file", {"path": "sources/2026-10-28-y-tuong.md", "content": "x"})
check("ghi file MỚI vào sources/ vẫn được (skill notes)", chay)
kq, chay = goi("joyce_write_file", {"path": "Memory/facts/a.md", "content": "x"})
check("ghi vào Memory/ viết hoa bị chặn, chỉ đúng memory/", not chay and "memory/" in kq)
_, chay = goi("joyce_write_file", {"path": "memory/facts/a.md", "content": "x"})
check("ghi vào memory/ viết thường vẫn được", chay)
_, chay = goi("joyce_write_file", {"path": "wiki/trang.md", "content": "x"})
check("ghi file thường không bị đụng", chay)

# ---- luật 2: Zalo
ok_khach = [goi("zalo_send_message", {"threadId": "1", "message": "hi"}, KHACH)[1] for _ in range(4)]
check("người không phải chủ gửi được 3 tin, tin thứ 4 bị chặn", ok_khach == [True, True, True, False])
check("tên tool có tiền tố connector vẫn bị đếm", not goi("joyce_zalo__zalo_send_image", {}, KHACH)[1])
ok_chu = [goi("zalo_send_message", {"threadId": "1", "message": "hi"}, CHU)[1] for _ in range(10)]
check("chủ gửi 10 tin liền không bị giới hạn", all(ok_chu))
nen = [goi("zalo_send_mention", {}, None)[1] for _ in range(31)]
check("việc nền không rõ người gọi: 30 tin rồi phanh", nen.count(True) == 30 and nen[-1] is False)
check("tool đọc Zalo không bị đếm", goi("zalo_get_messages", {}, KHACH)[1])

# ---- luật 3: Sổ Shop
kq, chay = goi("joyce_shop", {"op": "ghi", "su_kien": [{"loai": "chi", "so_tien": 8000000, "dien_giai": "mua đồ"}]}, CHU)
check("chi 8 triệu không gắn hợp đồng, không hạng mục: bị chặn kèm cách sửa", not chay and "hang_muc" in kq and "8.000.000đ" in kq)
check("chi lớn có khach thì ghi", goi("joyce_shop", {"op": "ghi", "su_kien": [{"loai": "chi", "so_tien": 8000000, "khach": "HD0001"}]}, CHU)[1])
check("chi lớn có hang_muc (chi chung) thì ghi", goi("joyce_shop", {"op": "ghi", "su_kien": [{"loai": "chi", "so_tien": 12000000, "hang_muc": "Mặt bằng"}]}, CHU)[1])
check("chi nhỏ không gắn gì vẫn ghi", goi("joyce_shop", {"op": "ghi", "su_kien": [{"loai": "chi", "so_tien": 300000}]}, CHU)[1])
check("thu lớn không bị luật chi đụng", goi("joyce_shop", {"op": "ghi", "su_kien": [{"loai": "thu", "so_tien": 50000000}]}, CHU)[1])
check("op=xem không bị đụng", goi("joyce_shop", {"op": "xem"}, CHU)[1])
check("tiền dạng chuỗi có dấu chấm vẫn được đọc đúng",
      not goi("joyce_shop", {"op": "ghi", "su_kien": [{"loai": "chi", "so_tien": "6.500.000"}]}, CHU)[1])

# ---- joyce_run_tool không bị chặn hai lần (luật áp ở lời gọi thật bên trong)
check("meta-tool joyce_run_tool đi qua, luật áp ở tool thật",
      goi("joyce_run_tool", {"name": "joyce_write_file", "args": {"path": "sources/hop-dong-goc.md"}})[1])

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
