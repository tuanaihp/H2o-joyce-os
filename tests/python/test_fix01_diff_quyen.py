"""FIX-01 (Joyce Harness G1, JHA-01): so sánh quyền theo CÂY YAML, không theo dấu vân dòng.

    python tests/run.py fix01_diff_quyen      (không mạng, không model)

Trước 1.3.41 `factory.diff_quyen` lọc các dòng `key: value` rồi SẮP XẾP, nên:
- đổi `harness.budgets.max_tokens` (khoá lồng) không thấy gì;
- tráo `tools` giữa hai bước workflow vẫn ra cùng tập dòng đã sắp xếp, tức là không đổi;
- khoá quyền mới chưa biết (vd `permissions:`) bị coi là sửa nội dung thuần.
Mỗi ca âm dưới đây là một dạng đó. Điều kiện dừng của ticket: không đọc chắc cấu hình thì KHÔNG tự áp.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import sys

import factory  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


def agent(extra="", body="Bạn là trưởng phòng.\n\n## Quy trình\n1. Kiểm chứng từ.\n"):
    return "---\ntype: agent\nname: Trưởng Phòng\nrole: Thu\n" + extra + "---\n\n" + body


def wf(steps):
    return "---\ntype: workflow\nname: Quy trình thu\nsteps:\n" + steps + "---\n"


STEP_A = "  - agent: truong-phong-thu\n    task: |\n      Ghi thu\n"
STEP_B = "  - agent: giam-dinh-bao-mat\n    task: |\n      Kiểm tra\n"
diff = factory.diff_quyen
BAD = "(frontmatter không đọc được)"

# ---------------- ca âm: phải bị phát hiện (kể cả ca cũ vẫn phải đúng)
base = agent("harness:\n  budgets:\n    max_tokens: 100000\n  scope:\n    brains: [phong-thu]\n")
d = diff(base, base.replace("max_tokens: 100000", "max_tokens: 900000"))
check("khoá lồng: đổi harness.budgets.max_tokens bị phát hiện, nêu đúng đường dẫn", d == ["harness.budgets.max_tokens"], d)
d = diff(base, base.replace("brains: [phong-thu]", "brains: [phong-thu, phong-chi]"))
check("khoá lồng: mở rộng scope trong harness bị phát hiện", d == ["harness.scope.brains"], d)
d = diff(base, base.replace("    brains: [phong-thu]\n", "    brains: [phong-thu]\n    egress: any\n"))
check("khoá lạ THÊM vào trong harness bị phát hiện (subtree quyền phải review)", d == ["harness.scope.egress"], d)

tools1 = wf(STEP_A + "    tools: [joyce_shop]\n" + STEP_B + "    tools: []\n")
tools2 = wf(STEP_A + "    tools: []\n" + STEP_B + "    tools: [joyce_shop]\n")
check("tráo tools giữa hai bước workflow (cùng tập dòng) bị phát hiện", diff(tools1, tools2) == ["tools"], diff(tools1, tools2))
check("tráo agent giữa hai bước bị phát hiện", diff(wf(STEP_A + STEP_B), wf(STEP_B + STEP_A)) == ["agent"], diff(wf(STEP_A + STEP_B), wf(STEP_B + STEP_A)))

ALIAS_GOC = agent("x-shared: &t [read]\ntools: [read]\n")
ALIAS_MOI = agent("x-shared: &t [read, joyce_shop]\ntools: *t\n")
check("thêm quyền qua alias/anchor bị phát hiện (so theo giá trị đã giải)", diff(ALIAS_GOC, ALIAS_MOI) == ["tools"], diff(ALIAS_GOC, ALIAS_MOI))
check("viết lại bằng alias nhưng cùng giá trị thì KHÔNG đổi quyền",
      diff(agent("tools: [read, joyce_shop]\n"), agent("x-t: &t [read, joyce_shop]\ntools: *t\n")) == [], diff(agent("tools: [read, joyce_shop]\n"), agent("x-t: &t [read, joyce_shop]\ntools: *t\n")))

check("đổi kiểu dữ liệu (số thành chuỗi) bị phát hiện", diff(agent("max_retries: 2\n"), agent('max_retries: "2"\n')) == ["max_retries"])
check("đổi bool thành chuỗi bị phát hiện", diff(agent("enabled: false\n"), agent('enabled: "false"\n')) == ["enabled"])
check("bỏ một khoá quyền bị phát hiện", diff(agent("model: sonnet\n"), agent("")) == ["model"])
check("thêm một khoá quyền bị phát hiện", diff(agent(""), agent("model: gpt-6\n")) == ["model"])

check("khoá quyền mới CHƯA BIẾT ở cấp ngoài (permissions) không được coi là sửa nội dung",
      diff(agent(""), agent("permissions:\n  write: all\n")) == ["?permissions"], diff(agent(""), agent("permissions:\n  write: all\n")))
check("khoá lạ trong một bước workflow bị phát hiện",
      diff(wf(STEP_A), wf(STEP_A + "    can_write: true\n")) == ["?steps.can_write"], diff(wf(STEP_A), wf(STEP_A + "    can_write: true\n")))
check("khoá quyền mới của hệ loop (workspace, quiet_hours, status) cũng được canh",
      diff(agent(""), agent("workspace: C:/\n")) == ["workspace"] and diff(agent("status: off\n"), agent("status: active\n")) == ["status"])

# ---------------- không đọc chắc thì dừng, không suy là nội dung thuần
check("YAML lỗi ở bản nháp: không tự áp", diff(agent(""), "---\ntype: agent\nname: x: y: z\n  : [\n---\nthân\n") == [BAD])
check("YAML lỗi ở bản gốc: không tự áp", diff("---\ntype: agent\nname: a: b\n---\nthân", agent("")) == [BAD])
check("frontmatter không phải mapping (danh sách): không tự áp", diff(agent(""), "---\n- a\n- b\n---\nthân\n") == [BAD])
check("bản nháp BỎ frontmatter của file có frontmatter: bị phát hiện khi gốc có khoá quyền",
      diff(agent("model: sonnet\n"), "Chỉ còn thân bài, không frontmatter.\n") == ["model"])

# ---------------- sửa nội dung thuần vẫn hợp lệ (không làm hỏng tự cải tiến)
check("sửa thân bài: không đổi quyền", diff(agent(), agent(body="Nội dung mới hoàn toàn, dài hơn.\n")) == [])
check("sửa description/name/role/group: không đổi quyền",
      diff("---\ntype: agent\nname: A\ndescription: cũ\ngroup: Thu\n---\nx\n", "---\ntype: agent\nname: B\ndescription: mới\ngroup: Kế toán\n---\nx\n") == [])
check("workflow đổi lời giao việc: không đổi quyền", diff(wf(STEP_A), wf(STEP_A.replace("Ghi thu", "Ghi thu có chứng từ"))) == [])
check("đổi thứ tự các mục trong danh sách tools: không đổi quyền", diff(agent("tools: [a, b]\n"), agent("tools: [b, a]\n")) == [])
check("CRLF và LF cho cùng kết quả", diff(agent("model: a\n").replace("\n", "\r\n"), agent("model: a\n")) == [])
check("hai file không có frontmatter: không đổi quyền", diff("chỉ thân bài\n", "thân bài khác\n") == [])
check("hai bản giống hệt: rỗng", diff(base, base) == [])
check("cả hai bản đều giữ skills/model cũ, chỉ sửa thân: rỗng",
      diff(agent("skills: [a, b]\nmodel: sonnet\n"), agent("skills: [a, b]\nmodel: sonnet\n", body="Khác.\n")) == [])

# ---------------- giới hạn
to = agent("skills: [" + ", ".join(f"s{i}" for i in range(20000)) + "]\n")
check("frontmatter quá lớn: không đọc, không tự áp (không treo)", diff(agent(""), to) == [BAD])

# ---------------- đường áp: _proposal_apply dùng đúng hàm này
import asyncio, json, pathlib, tempfile  # noqa: E402
r = pathlib.Path(tempfile.mkdtemp(prefix="joyce-fix01-"))
(r / "agents").mkdir()
(r / "Joyce" / "proposals").mkdir(parents=True)
(r / "Joyce" / "factory.json").write_text(json.dumps({"self_improve": True}), encoding="utf-8")
GOC = agent("harness:\n  budgets:\n    max_tokens: 100000\n")
(r / "agents" / "tro-ly-a.md").write_text(GOC, encoding="utf-8")
NHAP = GOC.replace("max_tokens: 100000", "max_tokens: 900000").replace("1. Kiểm chứng từ.", "1. Kiểm chứng từ: đủ ngày, số tiền, đơn vị nhận, lý do.\n2. Thiếu một trong bốn thì chờ bổ sung.")
(r / "Joyce" / "proposals" / "2026-10-28-tro-ly-a.md").write_text(
    "---\ntype: proposal\nstatus: pending\nverdict: win\nrisk: low\ntarget_file: agents/tro-ly-a.md\n---\n# Đề xuất\n\n## Bản nháp đầy đủ\n\n```markdown\n" + NHAP + "```\n", encoding="utf-8")
hop = []


async def inbox(text, **kw):
    hop.append(text)


deps = factory.FactoryDeps(brains=lambda: ["Phong Thu"], task_root=lambda n: str(r), store=None, enqueue=None, loops=None,
                           workflows_dir=lambda root: pathlib.Path(root) / "workflows", inbox=inbox,
                           incidents_list=lambda b, n: [], settings_get=lambda: {}, state_dir=r)
rep = asyncio.run(factory.proposal_tick(deps))
check("tự cải tiến: đề xuất nâng ngân sách lồng nhau KHÔNG được tự áp dù ghi WIN và risk low",
      rep["applied"] == 0 and (r / "agents" / "tro-ly-a.md").read_text(encoding="utf-8") == GOC)
check("đề xuất chuyển sang chờ chủ và nêu đúng khoá", "cho_chu_duyet" in (r / "Joyce" / "proposals" / "2026-10-28-tro-ly-a.md").read_text(encoding="utf-8")
      and any("harness.budgets.max_tokens" in t for t in hop), hop)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
