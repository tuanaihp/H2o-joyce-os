"""Thu gọn kết quả tool cũ trong một lượt (engine._thu_gon_ket_qua_cu, Joyce Harness giai đoạn 0A).

    python tests/run.py thu_gon_tool_cu      (không mạng, không model)
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import sys

from engine import _thu_gon_ket_qua_cu, TOOL_CU_NGAN_SACH  # noqa: E402

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


TRANG = "đơn hàng " * 880    # ~8k ký tự, đúng trần _clip_tool_result của một kết quả


def anthropic(n, ten="pos_list_orders"):
    conv = [{"role": "user", "content": "doanh thu tháng 10"}]
    for i in range(n):
        conv.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": ten, "input": {"page": i}}]})
        conv.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": f"TRANG {i}\n" + TRANG}]})
    return conv


def kq(conv):
    return [b["content"] for m in conv if isinstance(m.get("content"), list) for b in m["content"] if b.get("type") == "tool_result"]


nho = anthropic(3)
check("dưới ngân sách thì không đụng gì", _thu_gon_ket_qua_cu(nho) == 0 and all("THU GỌN" not in x for x in kq(nho)))

lon = anthropic(12)
n = _thu_gon_ket_qua_cu(lon)
k = kq(lon)
check("vượt ngân sách thì thu gọn kết quả cũ", n > 0 and "KẾT QUẢ CŨ ĐÃ THU GỌN" in k[0])
check("phần đầu kết quả cũ vẫn còn (model biết đó là trang nào)", k[0].startswith("TRANG 0"))
check("4 kết quả mới nhất giữ nguyên", all("THU GỌN" not in x for x in k[-4:]))
check("tổng còn dưới ngân sách", sum(map(len, k)) <= TOOL_CU_NGAN_SACH)
check("câu thu gọn nói cách lấy lại", "gọi lại `pos_list_orders`" in k[0])
check("chạy lần hai không thu gọn chồng", _thu_gon_ket_qua_cu(lon) == 0)

shop = anthropic(12, ten="joyce_shop")
check("kết quả Sổ Shop được ghim, không bao giờ thu gọn", _thu_gon_ket_qua_cu(shop) == 0)

oa = [{"role": "user", "content": "x"}]
for i in range(12):
    oa.append({"role": "assistant", "content": None, "tool_calls": [{"id": f"c{i}", "function": {"name": "ads_report", "arguments": "{}"}}]})
    oa.append({"role": "tool", "tool_call_id": f"c{i}", "content": TRANG})
check("dạng OpenAI chat cũng thu gọn", _thu_gon_ket_qua_cu(oa) > 0 and "gọi lại `ads_report`" in oa[2]["content"])

rs = [{"role": "user", "content": "x"}]
for i in range(12):
    rs.append({"type": "function_call", "call_id": f"r{i}", "name": "ga_report", "arguments": "{}"})
    rs.append({"type": "function_call_output", "call_id": f"r{i}", "output": TRANG})
check("dạng Responses của Codex cũng thu gọn", _thu_gon_ket_qua_cu(rs) > 0 and "THU GỌN" in rs[2]["output"]
      and "THU GỌN" not in rs[-1]["output"])

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
