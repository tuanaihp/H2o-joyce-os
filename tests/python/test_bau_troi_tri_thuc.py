"""Bầu trời tri thức - phía máy chủ (server/knowledge_sky.py). Chạy tay / CI:

    python tests/python/test_bau_troi_tri_thuc.py

Thiết kế: docs/dev/2026-10-bau-troi-tri-thuc.md. Không cần mạng, không cần máy chủ chạy: dựng
vài brain giả trong thư mục tạm rồi gọi thẳng các hàm của module. Phủ:
- phân loại thiên thể (đá vụn / vành 0-1-2 / sao, cờ proc), bỏ file hệ thống và skill hệ thống;
- phạm vi: admin ở brain chủ = gộp, admin ở brain phòng = một brain, nhân viên = một brain;
- id cố định theo tài liệu; /knowledge/quick chặn `..` và brain ngoài phạm vi;
- rút đầu mục không AI, kể cả trang .docx chuyển đổi chỉ có trang bìa.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JOYCE_STATE_DIR", tempfile.mkdtemp(prefix="joyce-sky-"))

import knowledge_sky as ks  # noqa: E402

_fails = []


def check(n, c):
    print(("ok   " if c else "FAIL ") + n)
    if not c:
        _fails.append(n)


def viet(p: Path, txt: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


goc = Path(tempfile.mkdtemp(prefix="sky-brains-"))
chu = goc / "Brain Default"
phong = goc / "ThuyH2O - Marketing va Bao Gia"
viet(chu / "wiki" / "bang-gia.md", "---\ntype: wiki\ntags: [gia]\n---\n# Bảng giá\n## Gói chụp ảnh cưới\n## Gói makeup\nXem [[quy-trinh-bao-gia]].\n")
viet(chu / "wiki" / "1. Quy Trình Báo Giá.md", "---\ntags: [quy-trinh]\n---\nQuy Trình Báo Giá\n")
viet(chu / "wiki" / "index.md", "# chỉ mục")
viet(chu / "wiki" / "_open-questions.md", "x")
viet(chu / "sources" / "bao-gia-2026.pdf", "%PDF")
# Tài liệu .docx kèm bản chữ trích ra (X.docx.txt): CÙNG một tài liệu, chỉ được là MỘT viên đá vụn.
viet(chu / "sources" / "quy-trinh-coc.docx", "PK")
viet(chu / "sources" / "quy-trinh-coc.docx.txt", "Quy trình cọc\n# Nhận cọc khách\n# Hoàn cọc khách\n")
viet(chu / "sources" / "ghi-chu-rieng.txt", "txt đứng riêng vẫn là tài liệu")
viet(chu / "inbox" / "ghi-chu.md", "ghi chú thô")
viet(chu / "skills" / "tu-van-bao-gia" / "SKILL.md", "---\nname: Tư vấn báo giá\n---\n")
viet(chu / "skills" / "joyce-builder" / "SKILL.md", "---\nname: joyce-builder\n---\n")
viet(chu / "workflows" / "bao-gia-tuan.md", "---\nname: Báo giá tuần\n---\n")
viet(chu / "memory" / "facts" / "khach-vip.md", "Khách VIP")
viet(chu / "Joyce" / "index.md", "tự sinh")
viet(chu / ".claude" / "skills" / "x" / "SKILL.md", "ẩn")
viet(phong / "wiki" / "kich-ban.md", "# Kịch bản tư vấn\n- Chào khách\n- Hỏi ngày cưới\n")

dang_la_nhan_vien = {"v": False}
ks._deps.update(brain_root=lambda b: str(chu) if b in ("", "brain") else (b if os.path.isdir(b) else str(chu)),
                default_dir=lambda: chu, is_staff=lambda: dang_la_nhan_vien["v"], brains_dir=str(goc))

# ---- phân loại ----
d = ks._dung_troi("brain")
theo_path = {(b["brain"], b["path"]): b for b in d["bodies"]}
B = lambda p: theo_path.get(("Brain Default", p))
check("admin ở brain chủ: trời gộp mọi brain", d["scope"] == "all" and {b["key"] for b in d["brains"]} == {"Brain Default", phong.name})
check("wiki thường = sao", (B("wiki/bang-gia.md") or {}).get("kind") == "star" and not B("wiki/bang-gia.md").get("proc"))
check("wiki quy trình = sao bốn cánh (proc)", (B("wiki/1. Quy Trình Báo Giá.md") or {}).get("proc") is True)
check("sources + inbox = đá vụn (kể cả pdf)",
      (B("sources/bao-gia-2026.pdf") or {}).get("kind") == "debris" and (B("inbox/ghi-chu.md") or {}).get("kind") == "debris")
check("skill riêng = vành 0", (B("skills/tu-van-bao-gia/SKILL.md") or {}).get("ring") == 0)
check("skill hệ thống không tính", B("skills/joyce-builder/SKILL.md") is None)
check("workflow = vành 1, trí nhớ = vành 2",
      (B("workflows/bao-gia-tuan.md") or {}).get("ring") == 1 and (B("memory/facts/khach-vip.md") or {}).get("ring") == 2)
check("bỏ index/_open-questions/Joyce/thư mục ẩn",
      not any(p.endswith(("index.md", "_open-questions.md")) or p.startswith(("Joyce/", ".claude/"))
              for _, p in theo_path))
check("tiêu đề lấy từ frontmatter name", B("skills/tu-van-bao-gia/SKILL.md")["title"] == "Tư vấn báo giá")
check("thiên thể không mang đường dẫn tuyệt đối", not any(str(goc) in str(v) for b in d["bodies"] for v in b.values()))
check("id cố định giữa hai lần dựng", ks._dung_troi("brain")["bodies"][0]["id"] == d["bodies"][0]["id"]
      and B("wiki/bang-gia.md")["id"] == ks._id_of("Brain Default", "wiki/bang-gia.md"))
check("số đếm khớp", d["counts"]["total"] == len(d["bodies"]) and d["counts"]["star"] == 3)
check("X.docx.txt gộp vào X.docx (không đếm đôi)",
      B("sources/quy-trinh-coc.docx") is not None and B("sources/quy-trinh-coc.docx.txt") is None
      and B("sources/ghi-chu-rieng.txt") is not None)
c0 = d["counts"]
check("số đếm chia đúng loại thiên thể: proc, kỹ năng, quy trình Joyce, trí nhớ",
      c0["proc"] == 1 and c0["skill"] == 1 and c0["workflow"] == 1 and c0["memory"] == 1
      and c0["skill"] + c0["workflow"] + c0["memory"] == c0["orbit"])
check("số đếm theo thương hiệu cộng lại đủ tổng", sum(c0["brands"].values()) == c0["total"] and c0["brains"] == 2)

# ---- phạm vi ----
d2 = ks._dung_troi(str(phong))
check("admin mở brain phòng: chỉ trời phòng đó", d2["scope"] == "brain" and [b["key"] for b in d2["brains"]] == [phong.name])
dang_la_nhan_vien["v"] = True
d3 = ks._dung_troi("brain")
check("nhân viên ở brain chủ: KHÔNG có trời gộp", d3["scope"] == "brain" and len(d3["brains"]) == 1)
dang_la_nhan_vien["v"] = False


# ---- đọc nhanh ----
async def quick(**kw):
    r = await ks.knowledge_quick(**{"brain": "brain", "src": "", "path": "", **kw})
    return r if isinstance(r, dict) else {"status": r.status_code}

r = asyncio.run(quick(src="Brain Default", path="wiki/bang-gia.md"))
check("đọc nhanh: đầu mục từ tiêu đề markdown", r.get("bullets") == ["Gói chụp ảnh cưới", "Gói makeup"])
r = asyncio.run(quick(src=phong.name, path="wiki/kich-ban.md"))
# Một tiêu đề lẻ chưa đủ (cần >= 2 mục), nên rơi xuống gạch đầu dòng - đúng thứ tự mục 5.1.
check("đọc nhanh: brain phòng trong trời gộp", r.get("ok") and r["bullets"] == ["Chào khách", "Hỏi ngày cưới"])
check("đọc nhanh: chặn ..", asyncio.run(quick(src="Brain Default", path="../ThuyH2O - Marketing va Bao Gia/wiki/kich-ban.md")).get("status") == 400)
check("đọc nhanh: brain lạ ngoài phạm vi -> 403", asyncio.run(quick(src="Khong Co", path="wiki/x.md")).get("status") == 403)
r = asyncio.run(quick(src="Brain Default", path="sources/quy-trinh-coc.docx"))
check("đọc nhanh .docx: lấy chữ từ bản .docx.txt đi kèm", r.get("text_file") is True and r["bullets"] == ["Nhận cọc khách", "Hoàn cọc khách"])
r = asyncio.run(quick(src="Brain Default", path="sources/bao-gia-2026.pdf"))
check("đọc nhanh: file thô không phải văn bản", r.get("ok") and r["text_file"] is False and r["bullets"] == [])
dang_la_nhan_vien["v"] = True
check("đọc nhanh: nhân viên không với sang brain khác",
      asyncio.run(quick(src=phong.name, path="wiki/kich-ban.md")).get("status") == 403)
dang_la_nhan_vien["v"] = False

# ---- rút đầu mục (không AI) ----
bia = ("---\ntype: wiki\n---\n> Nguồn gốc: [[sources/x.docx]]\n\nQuy Trình Bới Tóc Cô Dâu\nMã hiệu\n……/CG.CN.0001\n\n"
       "Lần ban hành\n01/ KHCN\n\nNgày ban hành\n03/09/2024\n\nTrang\n01\n")
check("trang bìa .docx: không ra đầu mục rác", ks.dau_muc(bia, "1. Quy Trình Bới Tóc Cô Dâu") == [])
docx = "Quy Trình Thông Tin Tổ Chức\nMã hiệu\n01/ KHCN\nSơ Đồ Tổ Chức\nBộ Nhận Diện Thương Hiệu\nSlogan - Câu Nói Tạo Động Lực\n"
check("dòng tiêu đề trần của .docx", ks.dau_muc(docx, "1. Quy Trình Thông Tin Tổ Chức")
      == ["Sơ Đồ Tổ Chức", "Bộ Nhận Diện Thương Hiệu", "Slogan - Câu Nói Tạo Động Lực"])
check("frontmatter tom_tat được ưu tiên",
      ks.dau_muc("---\ntom_tat:\n  - Điểm một quan trọng\n  - Điểm hai quan trọng\n---\n# Khác\n## Khác nữa\n", "x")
      == ["Điểm một quan trọng", "Điểm hai quan trọng"])
check("gạch đầu dòng cấp 1", ks.dau_muc("Mở đầu\n- Chào khách thân thiện\n- Hỏi ngày cưới\n  - con bỏ qua\n", "x")
      == ["Chào khách thân thiện", "Hỏi ngày cưới"])
check("mỗi mục tối đa 90 ký tự", all(len(s) <= 90 for s in ks.dau_muc("# " + "dài " * 60 + "\n# Mục hai ngắn\n", "x")))

# ---- tìm kiếm (giai đoạn 2: Big Bang) ----
viet(phong / "wiki" / "bao-gia-cuoi.md", "# Gói cưới\nBáo giá trọn gói, báo giá theo buổi. [[bang-gia]]\n")
r = ks.tim("brain", "Báo giá")
ten = [(h["brain"], h["path"]) for h in r["hits"]]
check("tìm: cùng phạm vi trời gộp (thấy cả brain phòng)", (phong.name, "wiki/bao-gia-cuoi.md") in ten)
check("tìm: gõ không dấu vẫn ra", [h["id"] for h in ks.tim("brain", "bao gia")["hits"]] == [h["id"] for h in r["hits"]])
check("tìm: khớp tên/tiêu đề đứng trước khớp nội dung",
      ten.index(("Brain Default", "sources/bao-gia-2026.pdf")) < ten.index(("Brain Default", "wiki/bang-gia.md")))
check("tìm: kết quả mang stem + links để nối chòm sao",
      next(h for h in r["hits"] if h["path"] == "wiki/bao-gia-cuoi.md")["links"] == ["bang-gia"])
check("tìm: không lộ đường dẫn tuyệt đối", not any(str(goc) in str(v) for h in r["hits"] for v in h.values()))
check("tìm: từ khoá rỗng / không khớp", ks.tim("brain", "  ")["hits"] == [] and ks.tim("brain", "zzqx")["total"] == 0)
dang_la_nhan_vien["v"] = True
check("tìm: nhân viên chỉ trong brain của mình",
      all(h["brain"] == "Brain Default" for h in ks.tim("brain", "báo giá")["hits"]))
dang_la_nhan_vien["v"] = False

# ---- tia tri thức: tool_label.tep rút đường dẫn file đầy đủ từ lệnh gọi công cụ ----
import tool_label  # noqa: E402
check("tep: Claude Read file_path tuyệt đối, KHÔNG rút gọn",
      tool_label.tep({"input": {"file_path": "E:/brains/ThuyH2O - Noi Quy va Bieu Mau/wiki/a.md"}})
      == ["E:/brains/ThuyH2O - Noi Quy va Bieu Mau/wiki/a.md"])
check("tep: arguments JSON lồng (Codex / MCP / bộ não API) + paths dạng mảng",
      tool_label.tep({"item": {"arguments": '{"path": "wiki/b.md", "paths": ["sources/c.docx"]}'}}) == ["wiki/b.md", "sources/c.docx"])
check("tep: lệnh không có file / payload lạ -> []",
      tool_label.tep({"input": {"command": "ls"}}) == [] and tool_label.tep(None) == [] and tool_label.tep({"input": "x"}) == [])
check("tep: không trùng, tối đa 8", tool_label.tep({"input": {"paths": ["a.md"] * 3 + [f"f{i}.md" for i in range(12)]}})
      == ["a.md"] + [f"f{i}.md" for i in range(7)])
check("tep: đường dẫn LẪN trong lệnh shell của Codex (Get-Content '...md'); lệnh tìm rg không tính",
      tool_label.tep({"item": {"command": ["powershell", "-Command", "Get-Content -LiteralPath 'E:\\b\\Brain Default\\wiki\\Bảng giá.md'"]}})
      == ["E:\\b\\Brain Default\\wiki\\Bảng giá.md"]
      and tool_label.tep({"item": {"command": 'rg -n "báo giá" wiki sources'}}) == [])
main_src = (SERVER / "main.py").read_text(encoding="utf-8")
check("mọi chỗ gửi tool_call đều kèm files", main_src.count('"files": tool_label.tep(') == 7
      and main_src.count("tool_label.chi_tiet(") == 7)

if _fails:
    print(f"\nFAIL - {len(_fails)} test: {_fails}")
    sys.exit(1)
print("\nOK - test_bau_troi_tri_thuc: tất cả pass")
