/* Test chat-kb.js - mục lục tri thức của brain trong khung chat trống.

       node tests/js/test_chat_kb.js

   KHÔNG cần trình duyệt/server: chỉ test 2 hàm thuần parseIndex() + renderHtml().
   Chốt chặn cần giữ:
   - mỗi ## heading có ít nhất 1 [[link]] -> một chip nhóm (kèm số trang);
   - link hệ thống (_open-questions, log, index, sources/) KHÔNG thành chip;
   - nhóm nào chỉ toàn link hệ thống thì không hiện;
   - chip mang data-kb để click handler điền câu hỏi vào ô chat;
   - index rỗng/thiếu -> renderHtml không được gọi (syncKb bỏ qua) nên ở đây chỉ
     kiểm parseIndex trả mảng rỗng. */
"use strict";
const { parseIndex, renderHtml } = require("../../dashboard/chat-kb.js");

let fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!cond) fails.push(name);
}

const MAU = [
  "# Wiki Index", "",
  "## dao-tao (đào tạo - học viện)",
  "- [[dao-tao/khoa-hoc/Danh Mục Khoá Học]] - mô tả.",
  "- [[dao-tao/quy-trinh/Quy Trình A]], [[dao-tao/quy-trinh/Quy Trình B]]",
  "## kinh-doanh",
  "- [[kinh-doanh/Báo Giá]]",
  "## trong-rong",
  "- [[_open-questions]], [[log]], [[index]]",
  "- [[sources/apple-notes/Notes/foo]] - nguồn thô.",
  "## điều hướng đặc biệt",
  "- [[Bản Đồ Triage]] - bản đồ file lẫn lộn.",
].join("\n");

// ---- parseIndex ----
const parsed = parseIndex(MAU);
const cats = parsed.cats;
check("nhóm chỉ toàn link hệ thống bị loại", cats.length === 3, String(cats.length));
check("nhóm dao-tao đếm đúng 3 trang",
  cats[0] && cats[0].pages.length === 3, JSON.stringify(cats[0] && cats[0].pages.length));
check("tách được nhiều [[link]] trên một dòng",
  cats[0] && cats[0].pages.some(p => p.base === "Quy Trình B"));
check("nhóm điều hướng giữ link trang thật, lọc phần hệ thống",
  cats[2] && cats[2].name === "điều hướng đặc biệt" && cats[2].pages.length === 1
    && cats[2].pages[0].rel === "Bản Đồ Triage");
check("link alias [[rel|alias]] lấy rel trước |",
  parseIndex("## x\n- [[a/b/Ten|Nhan khac]]").cats[0].pages[0].rel === "a/b/Ten");
check("index rỗng -> không nhóm", parseIndex("").cats.length === 0 && parseIndex("").flat.length === 0);
check("index thiếu -> không nhóm", parseIndex(null).cats.length === 0 && parseIndex(null).flat.length === 0);
check("link phẳng không nhóm -> vào flat (index kiểu phòng ban)",
  parseIndex("- [[A B]]\n- [[C D]]").flat.length === 2
    && parseIndex("- [[A B]]\n- [[C D]]").flat[0].base === "A B");
check("flat lọc link hệ thống y như nhóm", parseIndex("- [[log]]\n- [[_x]]\n- [[That]]").flat.length === 1);
check("link thư mục [[y-tuong/]] bị bỏ (không phải trang)",
  parseIndex("- [[y-tuong/]]\n- [[That]]").flat.length === 1);

// ---- renderHtml ----
const html = renderHtml(parsed);
check("chip nhóm mang data-kb", html.indexOf('data-kb="dao-tao (đào tạo - học viện)"') >= 0);
check("số trang trong nhóm in kèm", html.indexOf("dao-tao (đào tạo - học viện) <b>3</b>") >= 0);
check("tổng trang hiện ở huy hiệu", html.indexOf("5 trang") >= 0, "5 trang mong đợi");
check("nút xem đầy đủ trỏ về Cẩm nang", html.indexOf("chat-kb-more") >= 0);
check("không lộ link hệ thống", html.indexOf("_open-questions") < 0 && html.indexOf("sources/") < 0);
check("escape tên nhóm có ký tự đặc biệt",
  renderHtml({ cats: [{ name: 'a "b" <c>', pages: [{ rel: "x", base: "x" }] }], flat: [] })
    .indexOf('data-kb="a &quot;b&quot; &lt;c&gt;"') >= 0);
check("flat render thành chip trang hỏi đúng trang",
  renderHtml({ cats: [], flat: [{ rel: "a/X", base: "X" }] }).indexOf('class="chat-kb-page" data-kbp="X"') >= 0);

console.log(fails.length ? "\nFAIL - " + fails.length + " lỗi" : "\nTất cả xanh.");
process.exit(fails.length ? 1 : 0);
