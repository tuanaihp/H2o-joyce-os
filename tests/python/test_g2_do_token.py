"""G2 #3 (chủ chốt 29/10/2026): đo token THẬT theo từng lượt chạy, và trần token cấu hình được.

    python tests/run.py g2_do_token      (không mạng, không model; engine giả)

Đo: mọi sự kiện `usage` của lượt đang chạy được cộng vào dòng của lượt trong sổ. Lượt không nhận sự kiện nào là CHƯA ĐO, không phải 0 token.
Trần: settings.tasks.tran_token_luot, mặc định không chặn, kẹp tối đa 1 triệu (chủ chốt: không tự tăng quá 1 triệu); vượt thì dừng cả chuỗi.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-g2tok-state-")

import aux_engine  # noqa: E402
import config as cfgmod  # noqa: E402
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


def cau_hinh(tran):
    cfgmod.read_settings = lambda: {"tasks": {"tran_token_luot": tran}}


goc_settings = cfgmod.read_settings

# ---------------------------------------------------------------- 1. sổ
r1 = L.bat_dau(brain_id="b", agent_id="a", entrypoint="bot")
check("mới mở: chưa đo, 0 sự kiện", L.lay(r1)["usage_events"] == 0 and L.lay(r1)["tokens_in"] == 0)
check("cộng một sự kiện: trả tổng token đã đo", L.cong_token(r1, 1000, 200, 0.01) == 1200)
check("cộng sự kiện thứ hai: cộng dồn, đếm 2 sự kiện", L.cong_token(r1, "300", 50.0) == 1550 and L.lay(r1)["usage_events"] == 2)
check("giá trị rác (âm, chữ, None) coi là 0, không làm hỏng", L.cong_token(r1, -5, "x") == 1550 and L.cong_token(r1, None, None) == 1550)
check("lượt không có trong sổ: tổng 0, không nổ", L.cong_token("khong-co", 10, 10) == 0)
L.ket_thuc(r1, "completed")
r2 = L.bat_dau(brain_id="b", agent_id="a", entrypoint="bot")
L.ket_thuc(r2, "completed")
tk = L.thong_ke(brain_id="b", agent_id="a")
check("thống kê cộng token trên các lần chạy", tk["token_vao"] == 1300 and tk["token_ra"] == 250, tk)
check("lượt xong mà không nhận usage nào được đếm là CHƯA ĐO, không tính 0 token", tk["lan_chua_do_token"] == 1, tk)

# ---------------------------------------------------------------- 2. trần cấu hình
try:
    cau_hinh(0)
    check("không đặt trần: không chặn dù tốn bao nhiêu", L.tran_token_luot() == 0 and L.ghi_usage(r1, {"input": 99_000_000}) [1] is False)
    cau_hinh(500_000)
    check("trần 500k: dưới trần thì cho qua", L.ghi_usage(L.bat_dau(brain_id="b", agent_id="c", entrypoint="bot"), {"input": 400_000, "output": 50_000})[1] is False)
    rr = L.bat_dau(brain_id="b", agent_id="c", entrypoint="bot")
    L.ghi_usage(rr, {"input": 400_000})
    tong, vuot = L.ghi_usage(rr, {"input": 100_000, "output": 1})
    check("vượt trần 500k: báo vượt kèm tổng đã đo", vuot is True and tong == 500_001, (tong, vuot))
    cau_hinh(50_000_000)
    check("cấu hình lớn hơn 1 triệu bị kẹp xuống 1 triệu (không tự tăng)", L.tran_token_luot() == 1_000_000)
    cau_hinh("abc")
    check("cấu hình sai kiểu: không chặn (đo vẫn chạy)", L.tran_token_luot() == 0)
    cau_hinh(500_000)
    check("không có ngữ cảnh lượt chạy: không đo, không chặn", L.ghi_usage("", {"input": 9_999_999}) == (0, False))
    check("sự kiện không phải dict: không nổ", L.ghi_usage(rr, "usage") == (0, False))

    # ---------------------------------------------------------------- 3. chuỗi engine việc nền (aux_engine)
    class Mat:
        def __init__(self, ten, sk):
            self.provider = ten
            self.sk = sk
            self.da_goi = 0
            self.model = "m"
            self.tag = "aux"

        def is_available(self):
            return True

        async def query(self, prompt):
            self.da_goi += 1
            for e in self.sk:
                yield e

    def chay_chuoi(mats, ctx):
        async def go():
            tk_ = RX.dat(ctx)
            try:
                ch = aux_engine._FallbackChain(mats)
                return [e async for e in ch.query("hi")]
            finally:
                RX.go(tk_)
        return asyncio.run(go())

    ra = L.bat_dau(brain_id="b", agent_id="chuoi", entrypoint="task")
    ctx = RX.RunContext(ra, "chuoi", "b", "task", None)
    m1 = Mat("p1", [{"type": "usage", "input": 1000, "output": 100}, {"type": "text", "content": "xong"}, {"type": "final", "content": "xong"}])
    ev = chay_chuoi([m1], ctx)
    check("chuỗi việc nền: lượt chạy được ghi 1100 token từ sự kiện usage thật", L.lay(ra)["tokens_in"] == 1000 and L.lay(ra)["tokens_out"] == 100, L.lay(ra))
    check("chuỗi việc nền: kết quả vẫn đi tới người gọi nguyên vẹn", [e["type"] for e in ev] == ["usage", "text", "final"], ev)

    rb = L.bat_dau(brain_id="b", agent_id="chuoi", entrypoint="task")
    ctx2 = RX.RunContext(rb, "chuoi", "b", "task", None)
    cau_hinh(1000)
    m2a = Mat("p2a", [{"type": "usage", "input": 900, "output": 200}, {"type": "text", "content": "đáng lẽ chưa tới"}, {"type": "final", "content": "x"}])
    m2b = Mat("p2b", [{"type": "final", "content": "mắt dự phòng"}])
    ev = chay_chuoi([m2a, m2b], ctx2)
    check("vượt trần: DỪNG, trả lỗi nói rõ tổng và trần", ev[-1]["type"] == "error" and "vượt trần 1,000" in ev[-1]["content"] and "1,100" in ev[-1]["content"], ev)
    check("vượt trần: KHÔNG nhảy sang mắt dự phòng (đổi engine chỉ tốn thêm token)", m2b.da_goi == 0, m2b.da_goi)
    check("vượt trần: câu trả lời dở dang không lọt ra", not any(e.get("content") == "đáng lẽ chưa tới" for e in ev), ev)

    cau_hinh(0)
    rc = L.bat_dau(brain_id="b", agent_id="chuoi", entrypoint="task")
    ev = chay_chuoi([Mat("p3", [{"type": "usage", "input": 5_000_000, "output": 1}, {"type": "final", "content": "ok"}])], RX.RunContext(rc, "chuoi", "b", "task", None))
    check("không trần: lượt tốn 5 triệu token vẫn chạy xong, và số được ghi lại", ev[-1].get("content") == "ok" and L.lay(rc)["tokens_in"] == 5_000_000)
    ev = chay_chuoi([Mat("p4", [{"type": "usage", "input": 7, "output": 1}, {"type": "final", "content": "ok"}])], None)
    check("không có ngữ cảnh: chuỗi chạy bình thường, không nổ", ev[-1].get("content") == "ok")

    # ---------------------------------------------------------------- 4. chuỗi chat API (main._stream_chain)
    def chay_stream(sk_cac_mat, ctx):
        async def make(p, k, m):
            for e in sk_cac_mat[p]:
                yield e

        async def go():
            tk_ = RX.dat(ctx)
            try:
                return [e async for e in main._stream_chain([("pa", "", "m"), ("pb", "", "m")], make)]
            finally:
                RX.go(tk_)
        return asyncio.run(go())

    rd = L.bat_dau(brain_id="b", agent_id="chat", entrypoint="bot")
    cau_hinh(1000)
    ev = chay_stream({"pa": [{"type": "usage", "input": 1500, "output": 0}, {"type": "text", "content": "dở"}], "pb": [{"type": "text", "content": "dự phòng"}]},
                     RX.RunContext(rd, "chat", "b", "bot", None))
    check("chuỗi chat API: vượt trần thì dừng và báo lỗi, không chạy provider dự phòng",
          ev[-1]["type"] == "error" and "vượt trần" in ev[-1]["content"] and not any(e.get("content") == "dự phòng" for e in ev), ev)
    check("chuỗi chat API: token của lượt được ghi", L.lay(rd)["tokens_in"] == 1500)
    cau_hinh(0)
    re_ = L.bat_dau(brain_id="b", agent_id="chat", entrypoint="bot")
    ev = chay_stream({"pa": [{"type": "usage", "input": 20, "output": 5}, {"type": "text", "content": "chào"}], "pb": []}, RX.RunContext(re_, "chat", "b", "bot", None))
    check("chuỗi chat API: không trần thì chạy bình thường và ghi 25 token", [e["type"] for e in ev] == ["usage", "text"] and L.lay(re_)["tokens_in"] + L.lay(re_)["tokens_out"] == 25)
finally:
    cfgmod.read_settings = goc_settings
    L.dong()

print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g2_do_token: tất cả pass")
