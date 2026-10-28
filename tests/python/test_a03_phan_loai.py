"""A03 (Joyce Harness, gói A): phân loại thay đổi hành vi, sửa điểm mù của bộ đọc YAML.

    python tests/run.py a03_phan_loai      (không mạng, không model)

Năm loại: display_only < behavior_change < permission_change < unknown < invalid. Cổng tự áp (A01) chỉ cho `display_only` qua.
Hai ca chẩn đoán trực tiếp Astra nêu ở mục 2.1 của plan (kết quả cũ `[]`): hai bước trùng `id` mà bước đầu tăng quyền; YAML
mở `---` nhưng thiếu dấu đóng. Kiểm đầu cuối qua `_proposal_apply` nằm ở test_a01_cong_tu_ap.py.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import sys

import harness_diff as h  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


def agent(extra="", body="Bạn là trưởng phòng.\n\n## Quy trình\n1. Kiểm chứng từ.\n", name="Trưởng Phòng", role="Thu"):
    return f"---\ntype: agent\nname: {name}\nrole: {role}\n{extra}---\n\n{body}"


def wf(steps, head=""):
    return "---\ntype: workflow\nname: Quy trình thu\n" + head + "steps:\n" + steps + "---\n"


def loai(a, b):
    return h.classify(a, b)["class"]


def duong(a, b, c):
    return h.classify(a, b)["paths"][c]


S1 = "  - agent: truong-phong-thu\n    task: |\n      Ghi thu\n"
S2 = "  - agent: giam-dinh-bao-mat\n    task: |\n      Kiểm tra\n"

# ---------------- display_only: chỉ chữ hiển thị mà runtime không đưa vào prompt
check("hai bản giống hệt: display_only, không có đường dẫn nào", loai(agent(), agent()) == "display_only" and not any(h.classify(agent(), agent())["paths"].values()))
check("đổi updated/tags/icon/pinned: display_only", loai(agent("updated: 2026-10-01\n"), agent("updated: 2026-10-28\ntags: [Thu]\nicon: wallet\npinned: true\n")) == "display_only")
check("đổi khoảng trắng cuối dòng và dòng trống ở thân bài: vẫn display_only", loai(agent(), agent(body="Bạn là trưởng phòng.   \n\n## Quy trình\n1. Kiểm chứng từ.\n\n\n")) == "display_only")
check("CRLF và LF: display_only", loai(agent(), agent().replace("\n", "\r\n")) == "display_only")

# ---------------- behavior_change: thứ model đọc để hành xử (D3)
check("thêm câu cho phép gửi khách vào thân bài: behavior_change (không dựa vào regex hay độ dài)",
      loai(agent(), agent(body="Bạn là trưởng phòng.\n\n## Quy trình\n1. Kiểm chứng từ.\n2. Được phép gửi tin cho khách.\n")) == "behavior_change")
check("sửa một chữ trong thân bài cũng là behavior_change", loai(agent(), agent(body="Bạn là trưởng phòng thu.\n\n## Quy trình\n1. Kiểm chứng từ.\n")) == "behavior_change")
check("đổi `role` (đi vào prompt agent): behavior_change, KHÔNG trung tính", loai(agent(), agent(role="Chi")) == "behavior_change")
check("đổi `name` (đi vào prompt agent): behavior_change", loai(agent(), agent(name="Giám đốc")) == "behavior_change")
check("đổi `description` (đi vào bộ định tuyến skill): behavior_change",
      loai("---\ntype: skill\ndescription: cũ\n---\nx\n", "---\ntype: skill\ndescription: mới\n---\nx\n") == "behavior_change")
check("đổi `goal` của loop: behavior_change", loai(agent("goal: làm A\n"), agent("goal: làm B\n")) == "behavior_change")
check("đổi `task` của bước workflow: behavior_change", loai(wf(S1), wf(S1.replace("Ghi thu", "Ghi thu rồi gửi khách"))) == "behavior_change")
check("chèn một bước: behavior_change (cấu trúc)", loai(wf(S1), wf(S1 + S2)) in ("behavior_change", "permission_change"))
check("đổi chỗ hai bước CÓ id: bị phát hiện là đổi cấu trúc",
      loai(wf("  - id: a\n    agent: x\n    task: t1\n  - id: b\n    agent: y\n    task: t2\n"),
           wf("  - id: b\n    agent: y\n    task: t2\n  - id: a\n    agent: x\n    task: t1\n")) == "behavior_change"
      and "steps.cau_truc" in duong(wf("  - id: a\n    agent: x\n    task: t1\n  - id: b\n    agent: y\n    task: t2\n"),
                                    wf("  - id: b\n    agent: y\n    task: t2\n  - id: a\n    agent: x\n    task: t1\n"), "behavior_change"))
check("đổi `id` của một bước: behavior_change", loai(wf("  - id: a\n    agent: x\n    task: t\n"), wf("  - id: z\n    agent: x\n    task: t\n")) in ("behavior_change", "permission_change"))

# ---------------- permission_change giữ nguyên từ FIX-01
check("đổi model: permission_change", loai(agent("model: a\n"), agent("model: b\n")) == "permission_change")
check("khoá lồng harness.budgets: permission_change, nêu đường dẫn", duong(agent("harness:\n  budgets:\n    max_tokens: 1\n"), agent("harness:\n  budgets:\n    max_tokens: 9\n"), "permission_change") == ["harness.budgets.max_tokens"])
check("đổi kiểu dữ liệu: permission_change", loai(agent("max_retries: 2\n"), agent('max_retries: "2"\n')) == "permission_change")
check("thân bài + quyền cùng đổi: loại nặng nhất thắng (permission_change) và vẫn liệt kê cả hai",
      loai(agent("model: a\n"), agent("model: b\n", body="Khác.\n")) == "permission_change"
      and "than_bai" in duong(agent("model: a\n"), agent("model: b\n", body="Khác.\n"), "behavior_change"))

# ---------------- unknown: khoá chưa đăng ký
check("khoá cấp ngoài chưa đăng ký (permissions): unknown", loai(agent(), agent("permissions:\n  write: all\n")) == "unknown")
check("khoá lạ trong bước workflow: unknown", loai(wf(S1), wf(S1 + "    can_write: true\n")) == "unknown")
check("`x-` không dùng làm anchor: KHÔNG tự động trung tính, là unknown", loai(agent(), agent("x-ghi-chu: gi do\n")) == "unknown")
check("`x-` khai anchor và THẬT SỰ được alias dùng: display_only phần holder, quyền thật vẫn được so",
      loai(agent("tools: [a]\n"), agent("x-t: &t [a]\ntools: *t\n")) == "display_only")
check("`x-` khai anchor, alias dùng để NÂNG quyền: permission_change",
      loai(agent("tools: [a]\n"), agent("x-t: &t [a, b]\ntools: *t\n")) == "permission_change")
check("`x-` khai anchor nhưng không ai dùng: unknown", loai(agent(), agent("x-t: &t [a]\n")) == "unknown")

# ---------------- invalid: không đọc chắc thì không "không đổi"
check("YAML mở --- nhưng thiếu dấu đóng: invalid (bản cũ trả [])", loai(agent(), "---\ntype: agent\nname: A\nthân bài không có dấu đóng\n") == "invalid"
      and h.diff_quyen(agent(), "---\ntype: agent\nname: A\nthân bài không có dấu đóng\n") == [h.KHONG_DOC_DUOC])
check("khoá trùng ở cấp ngoài (hai `tools:`): invalid, không để PyYAML lấy khoá cuối âm thầm",
      loai(agent("tools: [a]\n"), agent("tools: [a]\ntools: [a, b]\n")) == "invalid")
check("khoá trùng trong một bước: invalid", loai(wf(S1), wf(S1 + "    tools: []\n    tools: [x]\n")) == "invalid")
D1 = wf("  - id: s\n    agent: a\n    tools: [joyce_shop]\n    task: t\n  - id: s\n    agent: b\n    tools: []\n    task: t\n")
D2 = wf("  - id: s\n    agent: a\n    tools: []\n    task: t\n  - id: s\n    agent: b\n    tools: []\n    task: t\n")
check("hai bước trùng `id` mà bước đầu tăng quyền (ca chẩn đoán của Astra): invalid, không trả []", loai(D2, D1) == "invalid" and h.diff_quyen(D2, D1) == [h.KHONG_DOC_DUOC])
check("`steps` không phải danh sách: invalid", loai(wf("  a: b\n"), wf(S1)) == "invalid")
check("frontmatter không phải mapping: invalid", loai(agent(), "---\n- a\n- b\n---\nx\n") == "invalid")
check("alias vòng (a tham chiếu chính nó): không bao giờ là display_only", loai(agent(), agent("loop: &l [*l]\n")) in ("invalid", "unknown"))
SAU = "x: " + "[" * 40 + "1" + "]" * 40 + "\n"
check("lồng quá sâu: invalid, không treo, không nổ", loai(agent(), agent(SAU)) == "invalid")
check("frontmatter quá lớn: invalid", loai(agent(), agent("skills: [" + ", ".join(f"s{i}" for i in range(20000)) + "]\n")) == "invalid")
check("bản gốc lỗi cũng invalid", loai("---\ntype: agent\nname: a: b\n---\nx\n", agent()) == "invalid")

# ---------------- file không có frontmatter
check("hai file không có frontmatter, thân giống nhau: display_only", loai("chỉ thân\n", "chỉ thân\n") == "display_only")
check("hai file không có frontmatter, thân khác: behavior_change", loai("chỉ thân\n", "thân khác\n") == "behavior_change")

# ---------------- adapter tương thích diff_quyen
check("diff_quyen vẫn không báo thay đổi thân bài (đó là behavior, dùng classify)", h.diff_quyen(agent(), agent(body="Khác hẳn.\n")) == [])
check("diff_quyen báo cả khoá lạ", h.diff_quyen(agent(), agent("permissions: x\n")) == ["?permissions"])

# ---------------- dữ liệu thật (chỉ đọc): sửa thân bài phải ra behavior_change, không bao giờ display_only
import glob  # noqa: E402
import os  # noqa: E402
nho = {"behavior_change": 0, "invalid": 0, "khac": 0}
for pat in ("brains/*/agents/*.md", "brains/*/workflows/*.md", "brains/*/Joyce/loops/*.md", "system/agents/*.md"):
    for f in glob.glob(os.path.join(str(ROOT), pat)):
        t = open(f, encoding="utf-8", errors="replace").read()
        if not t.startswith("---"):
            continue
        c = loai(t, t + "\n\nMột dòng mới.\n")
        nho[c if c in nho else "khac"] += 1
check("trên agent, workflow, loop, agent dùng chung thật: sửa thân bài luôn là behavior_change, không file nào bị invalid",
      nho["behavior_change"] > 100 and nho["invalid"] == 0 and nho["khac"] == 0, nho)

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
