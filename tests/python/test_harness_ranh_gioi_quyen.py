"""Joyce Harness v1: ba lỗ ranh giới quyền đã xác minh trong code (ma trận nghiệm thu B-01, B-10, B-12).

    python tests/run.py harness_ranh_gioi_quyen      (không mạng, không model)

- B-01: `allowed_tools=[]` nghĩa là KHÔNG CÓ công cụ nào. Trước 1.3.39 engine Claude SDK coi [] như
  "không khai" rồi chạy `bypassPermissions`, tức mở toàn quyền đúng lúc nơi gọi định khoá chặt nhất.
- B-10: phép kiểm của bộ eval không chạy được (loại check lạ) là RỚT, không phải đạt.
- B-12: factory không tự áp đề xuất đổi trường quyền, dù đề xuất ghi `verdict: win` và `risk: low`
  (hai trường do agent giám định viết). Đề xuất chỉ đổi nội dung vẫn tự áp như cũ (chủ giữ chế độ tự áp).
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import factory  # noqa: E402
from claude_sdk_engine import ClaudeSDK  # noqa: E402

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


# ---------------- B-01
rong = ClaudeSDK(tag="workflow", allowed_tools=[])
o = rong._options()
check("B-01: allowed_tools=[] bật cổng kiểm từng lời gọi, không bypass",
      getattr(o, "permission_mode", None) == "default" and getattr(o, "can_use_tool", None) is not None)
check("B-01: allowed_tools=[] không nạp settings máy (allow-rule không che cổng)",
      getattr(o, "setting_sources", None) in (None, []))
servers, _strict = rong._mcp_servers()
check("B-01: allowed_tools=[] không đấu plugin in-process", "joyce-plugins" not in (servers or {}))
kq = asyncio.run(rong._permission_gate("Bash", {"command": "ls"}, None))
check("B-01: allowed_tools=[] từ chối mọi công cụ", type(kq).__name__ == "PermissionResultDeny")
kq2 = asyncio.run(rong._permission_gate("mcp__joyce__joyce_shop", {}, None))
check("B-01: allowed_tools=[] từ chối cả công cụ MCP của Joyce", type(kq2).__name__ == "PermissionResultDeny")
thuong = ClaudeSDK(tag="chat")._options()
check("B-01: không khai (None) vẫn là chat thường như cũ",
      getattr(thuong, "permission_mode", None) == "bypassPermissions")
co = ClaudeSDK(tag="loop", allowed_tools=["Read"])
check("B-01: danh sách có phần tử vẫn chạy như cũ",
      type(asyncio.run(co._permission_gate("Read", {}, None))).__name__ == "PermissionResultAllow"
      and type(asyncio.run(co._permission_gate("Bash", {}, None))).__name__ == "PermissionResultDeny")

# ---------------- B-10
root = Path(tempfile.mkdtemp(prefix="joyce-harness-b10-"))
(root / "Joyce" / "evals").mkdir(parents=True)
(root / "Joyce" / "evals" / "tro-ly-a.json").write_text(json.dumps({"cases": [
    {"name": "co-vai-tro", "check": "contains", "value": "Vai trò"},
    {"name": "go-sai-ten-check", "check": "chua", "value": "x"}]}, ensure_ascii=False), encoding="utf-8")
ev = factory.eval_for_draft(str(root), "agents/tro-ly-a.md", "## Vai trò\nnội dung")
check("B-10: check lạ tính là rớt, có nhãn không kiểm được",
      ev["fails"] == ["go-sai-ten-check (không kiểm được)"] and ev["passed"] == 1 and ev["total"] == 2)
ev2 = factory.eval_for_draft(str(root), "agents/tro-ly-a.md", "không có")
check("B-10: case rớt thật vẫn rớt", "co-vai-tro" in ev2["fails"])

# ---------------- B-12
GOC = "---\ntype: agent\nname: Trưởng Phòng Chi\nskills:\n- h2o-studio-ketoan-chi-kiem-soat\nmodel: \"\"\n---\n\nBạn là trưởng phòng chi.\n\n## Quy trình\n1. Kiểm chứng từ.\n"
NOI_DUNG = GOC.replace("1. Kiểm chứng từ.", "1. Kiểm chứng từ: đủ ngày, số tiền, đơn vị nhận, lý do.\n2. Thiếu một trong bốn thì ghi chờ bổ sung.")
NOI_QUYEN = NOI_DUNG.replace("- h2o-studio-ketoan-chi-kiem-soat\n", "- h2o-studio-ketoan-chi-kiem-soat\n- web-pilot\n").replace('model: ""', "model: gpt-6-astra")
check("B-12: chỉ đổi nội dung thì không có trường quyền nào đổi", factory.diff_quyen(GOC, NOI_DUNG) == [])
check("B-12: thêm skill và đổi model bị nhận ra", factory.diff_quyen(GOC, NOI_QUYEN) == ["model", "skills"])
WF = "---\ntype: workflow\nsteps:\n  - agent: truong-phong-chi\n    task: |\n      Ghi chi\n---\n"
check("B-12: bước workflow thêm tools bị nhận ra",
      factory.diff_quyen(WF, WF.replace("    task:", "    tools: [zalo_send_message]\n    task:")) == ["tools"])
check("B-12: bước workflow đổi agent bị nhận ra",
      factory.diff_quyen(WF, WF.replace("agent: truong-phong-chi", "agent: giam-dinh-ux")) == ["agent"])
check("B-12: bước workflow chỉ đổi lời giao việc thì không", factory.diff_quyen(WF, WF.replace("Ghi chi", "Ghi chi có chứng từ")) == [])


def _de_xuat(draft):
    return ("---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: agents/truong-phong-chi.md\n---\n"
            "# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + draft + "```\n")


def _chay(draft):
    r = Path(tempfile.mkdtemp(prefix="joyce-harness-b12-"))
    (r / "agents").mkdir()
    (r / "Joyce" / "proposals").mkdir(parents=True)
    (r / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
    (r / "agents" / "truong-phong-chi.md").write_text(GOC, encoding="utf-8")
    fp = r / "Joyce" / "proposals" / "2026-10-28-truong-phong-chi.md"
    fp.write_text(_de_xuat(draft), encoding="utf-8")
    hop_thu = []

    async def inbox(text, **kw):
        hop_thu.append(text)

    deps = factory.FactoryDeps(brains=lambda: ["Ke Toan - Chi"], task_root=lambda n: str(r), store=None, enqueue=None,
                               loops=None, workflows_dir=lambda root: Path(root) / "workflows", inbox=inbox,
                               incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=r)
    rep = asyncio.run(factory.proposal_tick(deps))
    return rep, (r / "agents" / "truong-phong-chi.md").read_text(encoding="utf-8"), fp.read_text(encoding="utf-8"), hop_thu


rep1, file1, prop1, _ = _chay(NOI_DUNG)
check("B-12: đề xuất chỉ đổi nội dung vẫn tự áp (chủ giữ chế độ tự áp)", rep1["applied"] == 1 and "đơn vị nhận" in file1)
check("bản nháp có mục ## trong thân agent không bị cắt cụt", "## Quy trình" in file1 and "chờ bổ sung" in file1)
check("bản nháp không khối ``` vẫn dừng ở mục ## kế tiếp",
      factory._extract_draft("## Bản nháp đầy đủ\nnội dung\n## Lý do\nx") == "nội dung")
rep2, file2, prop2, hop2 = _chay(NOI_QUYEN)
check("B-12: đề xuất đổi quyền KHÔNG tự áp dù ghi WIN và risk low", rep2["applied"] == 0 and rep2["canary"] == 0 and file2 == GOC)
check("B-12: đề xuất bị chuyển sang chờ chủ duyệt, nêu trường đổi",
      "status: cho_chu_duyet" in prop2 and "model" in prop2 and "skills" in prop2)
check("B-12: chủ nhận thông báo ở hộp thư", any("không tự áp" in t for t in hop2))

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
