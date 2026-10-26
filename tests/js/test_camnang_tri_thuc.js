/* Test triThucPanel (camnang.js) - panel "Tri thức trong brain".

   Panel đọc wiki/index.md của brain đang chọn, vẽ thành nhóm (## heading) + chip
   hỏi (mỗi [[link]]) để CEO bấm là điền sẵn câu hỏi vào ô chat. Test trích hàm
   ra khỏi IIFE rồi chạy với stub - không cần trình duyệt hay server:

       node tests/js/test_camnang_tri_thuc.js

   Chốt chặn cần giữ:
   - mỗi ## heading thành MỘT nhóm, ### thành tiểu mục trong nhóm đó;
   - nhiều [[link]] trên một dòng vẫn tách thành nhiều chip;
   - link hệ thống (_open-questions, log, index, sources/) KHÔNG thành chip;
   - chip mang data-ask (điền câu hỏi) và nút mắt mang data-file="wiki/<rel>.md";
   - index trống/thiếu -> trạng thái rỗng có hướng dẫn, KHÔNG ném lỗi. */
"use strict";
const fs = require("fs");
const path = require("path");

const DASH = path.join(__dirname, "..", "..", "dashboard");
const src = fs.readFileSync(path.join(DASH, "camnang.js"), "utf8");

const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!cond) fails.push(name);
}

// ---- Trích hàm triThucPanel và chạy với stub tối thiểu ----
const m = src.match(/function triThucPanel\(md\) \{[\s\S]*?\n  \}/);
check("trích được triThucPanel ra khỏi camnang.js", !!m);

const esc = (s) => (s || "").toString()
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const panel = (icon, t, d, inner) => `[PANEL ${icon}|${t}|${d}]` + inner + "[/PANEL]";
const tw = (k, bien) => k + (bien && bien.ten != null ? "{" + bien.ten + "}" : "");
const ic = (ten) => "<i:" + ten + ">";

const triThucPanel = new Function(
  "panel", "tw", "esc", "ic",
  "return " + m[0] + ";")(panel, tw, esc, ic);

const MAU = [
  "# Wiki Index", "",
  "## dao-tao (đào tạo - học viện)",
  "### khoa-hoc",
  "- [[dao-tao/khoa-hoc/Danh Mục Khoá Học]] - 15 khoá + giá.",
  "### quy-trinh",
  "- [[dao-tao/quy-trinh/Quy Trình A]], [[dao-tao/quy-trinh/Quy Trình B]]",
  "## kinh-doanh",
  "- [[kinh-doanh/Báo Giá]]",
  "## điều hướng đặc biệt",
  "- [[Bản Đồ Triage]] - bản đồ file lẫn lộn.",
  "- [[_open-questions]] - mâu thuẫn mở.",
  "- [[log]] - nhật ký.",
  "- [[sources/apple-notes/Notes/foo]] - nguồn thô, không phải wiki.",
].join("\n");

const html = triThucPanel(MAU);

check("panel bọc đúng tiêu đề Tri thức", html.indexOf("[PANEL book-open|camnang.kb_t|") === 0);
check("đủ số nhóm có trang (kể cả điều hướng đặc biệt)",
  (html.match(/class="cn-kb"/g) || []).length === 3,
  String((html.match(/class="cn-kb"/g) || []).length));
check("tách đủ chip từ dòng nhiều link + link đơn",
  (html.match(/class="cn-chip"/g) || []).length === 5,
  String((html.match(/class="cn-chip"/g) || []).length));
check("chip mang data-ask điền sẵn câu hỏi theo trang",
  html.indexOf('data-ask="camnang.kb_ask{Danh Mục Khoá Học}"') >= 0);
check("nút mắt trỏ đúng file wiki của trang",
  html.indexOf('data-file="wiki/dao-tao/khoa-hoc/Danh Mục Khoá Học.md"') >= 0);
check("tiểu mục ### hiện trong nhóm", html.indexOf('class="cn-kb-sub">khoa-hoc') >= 0);
check("link hệ thống bị lọc (_open-questions, log, sources/)",
  html.indexOf("_open-questions") < 0 && html.indexOf('data-file="wiki/log.md"') < 0
    && html.indexOf("sources/apple-notes") < 0);
check("nút tóm tắt nhóm hỏi đúng nhóm",
  html.indexOf('data-ask="camnang.kb_sum_ask{dao-tao (đào tạo - học viện)}"') >= 0);

// ---- Index kiểu PHẲNG (brain phòng ban): link không nằm dưới ## nào ----
const phang = triThucPanel("- [[A B C]] - x.\n- [[D E]] - y.\n## Y tuong\n- [[y-tuong/]] - kho.");
check("index phẳng vẫn render được trang", phang.indexOf('data-file="wiki/A B C.md"') >= 0
  && phang.indexOf('data-file="wiki/D E.md"') >= 0);
check("index phẳng không vẽ header nhóm rỗng", phang.indexOf('class="cn-kb-cat"') < 0);

// ---- Trạng thái rỗng ----
const rong = triThucPanel("");
check("index thiếu/rỗng -> panel trạng thái rỗng, không ném lỗi",
  rong.indexOf("cn-kb-empty") >= 0 && rong.indexOf("camnang.kb_empty") >= 0);
const trang = triThucPanel("## nhom\n- [[log]]\n");
check("index chỉ có link hệ thống -> vẫn trạng thái rỗng", trang.indexOf("cn-kb-empty") >= 0);

console.log(fails.length ? "\nFAIL - " + fails.length + " lỗi" : "\nTất cả xanh.");
process.exit(fails.length ? 1 : 0);
