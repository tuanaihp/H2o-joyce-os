"""G3 (nền móng trong sandbox): luồng Đối Soát chỉ đọc đi qua ĐÚNG các mảnh thật, bằng dữ liệu tổng hợp và agent giả.

    python tests/run.py g3_doi_soat_sandbox      (không mạng, không model; brain tạm)

Chứng minh bằng test, KHÔNG phải bằng một lần chạy thật: (1) bộ kiểm độc lập tính lại số và bắt đúng các kiểu sai; (2) agent Đối Soát khai `allowed_effects: [read]`
đọc được sổ nhưng bị chặn khi thử ghi; (3) lượt chạy được ghi, đo token, và được chấm theo kết quả của bộ kiểm, không theo câu "xong" của agent; (4) retry cùng
một việc là một bằng chứng; (5) máy chết giữa chừng thành gián đoạn, không tính đạt. Pilot thật còn chờ chủ duyệt (docs/dev/2026-10-29-ho-so-pilot-doi-soat.md).
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import os
import pathlib
import shutil
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-g3-state-")
BR = pathlib.Path(tempfile.mkdtemp(prefix="joyce-g3-brains-"))
os.environ["BRAINS_DIR"] = str(BR)
BRAIN = "doi-soat-thu"
SLUG = "truong-phong-doi-soat"
(BR / BRAIN / "agents").mkdir(parents=True)
(BR / BRAIN / "wiki").mkdir()
(BR / BRAIN / "agents" / f"{SLUG}.md").write_text(
    "---\ntype: agent\nname: Trưởng phòng Đối Soát\nallowed_effects: [read]\n---\nBạn đối chiếu số liệu theo kỳ, chỉ đọc, nêu khoản lệch.\n", encoding="utf-8", newline="")
shutil.copy(ROOT / "tests" / "fixtures" / "g3" / "doi_soat_mau.json", BR / BRAIN / "wiki" / "so-quy-mau.json")

import doi_soat_kiem as K  # noqa: E402
import factory  # noqa: E402
import factory_admin as fa  # noqa: E402
import main  # noqa: E402
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


DL = json.loads((ROOT / "tests" / "fixtures" / "g3" / "doi_soat_mau.json").read_text(encoding="utf-8"))
DUNG = [{"hop_dong": "HD-001", "tong_thu": 4_500_000, "con_phai_thu": 10_500_000},
        {"hop_dong": "HD-002", "tong_thu": 8_000_000, "con_phai_thu": 0},
        {"hop_dong": "HD-003", "tong_thu": 0, "con_phai_thu": 5_000_000}]

# ============================================================ 1. bộ kiểm độc lập
t = K.tinh(DL)
check("tính lại đúng ví dụ của kế hoạch: HD-001 tổng thu 4,5 triệu, còn phải thu 10,5 triệu",
      t["hop_dong"]["HD-001"]["tong_thu"] == 4_500_000 and t["hop_dong"]["HD-001"]["con_phai_thu"] == 10_500_000 and not t["loi"], t)
check("thu và chi tính RIÊNG (không suy ra lãi gộp): HD-002 thu 8 triệu, chi 2 triệu", t["hop_dong"]["HD-002"]["tong_thu"] == 8_000_000 and t["hop_dong"]["HD-002"]["tong_chi"] == 2_000_000)
check("báo cáo đúng đủ ba hợp đồng: ĐẠT", K.kiem(DL, DUNG)["dat"] is True)

sai_chi = [dict(DUNG[0], tong_thu=4_500_000 - 700_000, con_phai_thu=10_500_000 + 700_000)] + DUNG[1:]
r = K.kiem(DL, sai_chi)
check("agent trừ chi vào thu (lẫn khái niệm): KHÔNG đạt, chỉ ra đúng trường lệch và số đúng",
      r["dat"] is False and r["ket_qua"][0]["lech"]["tong_thu"]["dung"] == 4_500_000, r)
check("báo cáo thiếu một hợp đồng (phủ không đủ): KHÔNG đạt, nêu hợp đồng thiếu", K.kiem(DL, DUNG[:2])["dat"] is False and K.kiem(DL, DUNG[:2])["thieu"] == ["HD-003"])
check("báo cáo có hợp đồng không tồn tại: KHÔNG đạt", K.kiem(DL, DUNG + [{"hop_dong": "HD-999", "tong_thu": 1, "con_phai_thu": 1}])["thua"] == ["HD-999"])
check("báo cáo rỗng: KHÔNG đạt (không có gì được kiểm)", K.kiem(DL, [])["dat"] is False)
check("số lẻ, chữ, bool, thiếu trường đều tính là lệch", all(K.kiem(DL, [dict(DUNG[0], tong_thu=v)] + DUNG[1:])["dat"] is False for v in (4500000.0, "4500000", True, None)))
hong = json.loads(json.dumps(DL))
hong["phieu"].append({"id": "P-01", "hop_dong": "HD-001", "loai": "thu", "so_tien": 1500000})
check("phiếu trùng mã (nguy cơ tính trùng): cả lần kiểm KHÔNG đạt dù báo cáo khớp số", K.kiem(hong, DUNG)["dat"] is False and K.kiem(hong, DUNG)["loi_du_lieu"])
hong2 = json.loads(json.dumps(DL))
hong2["phieu"][0]["so_tien"] = -5
hong2["phieu"].append({"id": "P-99", "hop_dong": "HD-404", "loai": "thu", "so_tien": 10})
check("số âm và phiếu trỏ tới hợp đồng không có: bị báo là lỗi dữ liệu", len(K.tinh(hong2)["loi"]) == 2, K.tinh(hong2)["loi"])
vuot = json.loads(json.dumps(DL))
vuot["phieu"].append({"id": "P-77", "hop_dong": "HD-003", "loai": "thu", "so_tien": 6_000_000})
check("thu vượt giá trị hợp đồng: còn phải thu ÂM được giữ nguyên để lộ ra, không kẹp về 0", K.tinh(vuot)["hop_dong"]["HD-003"]["con_phai_thu"] == -1_000_000)

# ============================================================ 2-5. luồng thật trong sandbox
STATE = pathlib.Path(os.environ["JOYCE_STATE_DIR"])
deps = factory.FactoryDeps(brains=lambda: [], task_root=lambda n: "", store=None, enqueue=None, loops=None,
                           workflows_dir=lambda x: pathlib.Path(x), inbox=None, incidents_list=lambda bb, n: [],
                           settings_get=lambda: {}, state_dir=STATE)
mcp_hub.invalidate_cache()
_tools, ROUTE = asyncio.run(mcp_hub.discover_all("full", vault_root=str(BR / BRAIN)))


def luot_agent(bao_cao, thu_ghi=False, mid=1, token=(1200, 300)):
    """Một lượt agent Đối Soát: mở lượt như khung chat thật, đọc sổ qua hub, (tuỳ chọn) thử ghi, báo cáo; trả (run_id, kq_kiem, ket_qua_ghi)."""
    rid, tok = main._so_mo_luot_chat({"channel": f"agent:{SLUG}"}, BRAIN, "g3", mid)
    kq_ghi = None

    async def lam():
        nonlocal kq_ghi
        raw = await ROUTE["joyce_read_file"]["call"]({"path": "wiki/so-quy-mau.json"})
        du_lieu = json.loads(raw)
        L.ghi_usage(rid, {"input": token[0], "output": token[1]})
        if thu_ghi:
            kq_ghi = await ROUTE["joyce_write_file"]["call"]({"path": "wiki/sua-so.md", "content": "đã chỉnh số"})
        return K.kiem(du_lieu, bao_cao)
    try:
        kiem = asyncio.run(_trong_ctx(lam))
    finally:
        main._so_chot_luot_chat(rid, tok, "completed")
    return rid, kiem, kq_ghi


async def _trong_ctx(fn):
    # asyncio.run tạo context mới nên phải đặt lại ngữ cảnh của lượt: dựng từ chính dòng sổ như host làm
    c = L.ngu_canh(L.danh_sach(agent_id=SLUG, gioi_han=1)[0]["run_id"], str(BR / BRAIN))
    tk = RX.dat(c)
    try:
        return await fn()
    finally:
        RX.go(tk)


rid1, kiem1, _ = luot_agent(DUNG, mid=1)
r1 = L.lay(rid1)
check("lượt đúng: bộ kiểm ĐẠT; lượt được ghi theo agent Đối Soát, cửa chat, đúng bản file agent", kiem1["dat"] is True and r1["agent_id"] == SLUG and r1["entrypoint"] == "chat" and len(r1["agent_revision"]) == 64)
check("token của lượt được đo từ sự kiện usage (1500 token)", r1["tokens_in"] + r1["tokens_out"] == 1500, r1)
check("chấm theo KẾT QUẢ BỘ KIỂM: đạt thì chấm đạt", fa.cham_luot(deps, rid1, "pass" if kiem1["dat"] else "fail", "bộ kiểm độc lập khớp từng đồng")[0] == 200
      and L.lay(rid1)["verification_status"] == "verified_pass")

rid2, kiem2, _ = luot_agent(sai_chi, mid=2)
check("lượt SAI (lẫn chi vào thu): bộ kiểm KHÔNG đạt, và lượt bị chấm RỚT dù agent báo 'xong'",
      kiem2["dat"] is False and fa.cham_luot(deps, rid2, "pass" if kiem2["dat"] else "fail", "lệch số so với tính lại")[0] == 200
      and L.lay(rid2)["verification_status"] == "verified_fail")

rid3, kiem3, kq_ghi = luot_agent(DUNG, thu_ghi=True, mid=3)
check("agent chỉ đọc THỬ GHI: tool bị chặn, file KHÔNG được tạo", str(kq_ghi).startswith("ERROR") and not (BR / BRAIN / "wiki" / "sua-so.md").exists(), kq_ghi)
check("lần thử ghi được ghi vào sổ (điều kiện dừng pilot: agent cố làm điều không được phép)", L.lay(rid3)["quyen_bi_chan"] == 1, L.lay(rid3)["quyen_bi_chan"])
check("trong lượt có thử ghi, việc ĐỌC vẫn chạy và kết quả đối chiếu vẫn đúng", kiem3["dat"] is True)

# retry: cùng một tin trong cùng phiên là MỘT việc
rid4a, _, _ = luot_agent(sai_chi, mid=4)
rid4b, k4, _ = luot_agent(DUNG, mid=4)
tk = L.thong_ke(agent_id=SLUG)
logic4 = [x for x in L.danh_sach(agent_id=SLUG) if x["logical_execution_id"] == "chat:g3:4"]
check("lần thử lại cùng tin: hai lượt nhưng một logical execution", len(logic4) == 2 and tk["thu_lai"] >= 1, tk)

# máy chết giữa chừng
rid5, tok5 = main._so_mo_luot_chat({"channel": f"agent:{SLUG}"}, BRAIN, "g3", 5)
RX.go(tok5) if tok5 is not None else None
n = L.don_mo_coi(1e12)
check("máy chết giữa lượt: thành interrupted khi khởi động lại, KHÔNG tính đạt hay rớt",
      n >= 1 and L.lay(rid5)["status"] == "interrupted" and L.lay(rid5)["verification_status"] == "unverified")

# trần token
goc_settings = main.cfgmod.read_settings
try:
    main.cfgmod.read_settings = lambda: {"tasks": {"tran_token_luot": 1000}}
    rid6, tok6 = main._so_mo_luot_chat({"channel": f"agent:{SLUG}"}, BRAIN, "g3", 6)
    tong, vuot_ = L.ghi_usage(rid6, {"input": 900, "output": 200})
    main._so_chot_luot_chat(rid6, tok6, "failed")
    check("lượt vượt trần token (1.100 > 1.000) được báo vượt", vuot_ is True and tong == 1100)
finally:
    main.cfgmod.read_settings = goc_settings

st = L.thong_ke(agent_id=SLUG)
check("thống kê gộp: có lượt đạt, có lượt rớt, có gián đoạn, có lần bị chặn quyền", st["verified_pass"] >= 1 and st["verified_fail"] >= 1 and st["gian_doan"] >= 1 and st["lan_bi_chan_quyen"] >= 1, st)

L.dong()
print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_g3_doi_soat_sandbox: tất cả pass")
