/* Nhóm TỔNG QUAN trên thanh bên (spec V1.4 mục 53, mẫu JOYCE_OVERVIEW_COMMAND_CENTER_V1.html).

       node tests/js/test_tong_quan.js

   Tổng quan
   ├── Bảng điều hành   (command)
   ├── Hôm nay          (today - trang cũ giữ nguyên)
   ├── Phòng ban        (departments)
   ├── Lịch & kế hoạch  (calendar)
   └── Báo cáo          (reports)

   Canh: nhóm đứng đầu thanh bên với đủ 5 trang đúng thứ tự (chạy railGroups() thật), nhân viên
   không thấy 4 trang quản trị, renderPage giao 4 trang cho overview.js, overview.js nạp trước
   console.js, mọi khoá t() của overview.js có trong cả hai từ điển, và trang chỉ dùng màu theo
   theme (không tô màu cứng - giao diện tối đọc được). */
const fs = require("fs");
const path = require("path");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "..", "..");
const D = (f) => fs.readFileSync(path.join(ROOT, "dashboard", f), "utf8");
const CON = D("console.js"), OV = D("overview.js"), HTML = D("index.html"), CSS = D("console.css");
const VI = JSON.parse(D("i18n/vi.json")), EN = JSON.parse(D("i18n/en.json"));
const fails = [];
const check = (n, c, x) => { console.log((c ? "ok   " : "FAIL ") + n + (x ? "  " + x : "")); if (!c) fails.push(n); };

function groupsFor(staff) {
  const ctx = { ICON: {}, GICON: {}, t: (k) => k, window: staff ? { __h2oStaff: { role: "nhan_vien" } } : {} };
  vm.createContext(ctx);
  vm.runInContext(CON.slice(CON.indexOf("  const RAIL_ITEMS ="), CON.indexOf("  // Nhãn nhóm chứa")) +
    "\nglobalThis.groups = railGroups();", ctx);
  return ctx.groups;
}
const g0 = groupsFor(false)[0];
check("nhóm đầu tiên trên thanh bên là Tổng quan", g0 && g0.label === "nav.group.tong_quan");
check("Tổng quan có đủ 5 trang con đúng thứ tự", g0 && Array.from(g0.items, (i) => i.id).join(",") === "command,today,departments,calendar,reports",
  g0 && Array.from(g0.items, (i) => i.id).join(","));
const gs = groupsFor(true).find((g) => g.items.some((i) => i.id === "today"));
check("nhân viên chỉ thấy Hôm nay trong nhóm Tổng quan (4 trang kia là mặt quản trị)",
  gs && Array.from(gs.items, (i) => i.id).join(",") === "today");
check("renderPage giao 4 trang cho overview.js",
  /\["command", "departments", "calendar", "reports"\]\.includes\(id\)\) \{\s*if \(window\.JoyceOverview\) return window\.JoyceOverview\.render\(el, id\);/.test(CON));
const iOv = HTML.indexOf("/static/overview.js"), iCon = HTML.indexOf("/static/console.js");
check("index.html nạp overview.js TRƯỚC console.js", iOv > 0 && iOv < iCon);
check("overview.js xuất JoyceOverview với 4 trang",
  /VIEWS = \{ command: renderCommand, departments: renderDepartments, calendar: renderCalendar, reports: renderReports \}/.test(OV));
check("overview.js chỉ ĐỌC: không gọi POST nào", !/method:\s*["']POST/.test(OV));
check("câu hỏi gửi Joyce chỉ ĐIỀN SẴN, không tự gửi", /function hoiJoyce/.test(OV) && !/chatSend|sendBtn|\.click\(\)/.test(OV.slice(OV.indexOf("function hoiJoyce"), OV.indexOf("function moBrain"))));

// khoá t() trong overview.js
const keys = new Set();
for (const m of OV.matchAll(/"((?:ov|page|nav\.group)\.[a-z0-9_.]+)"/g)) keys.add(m[1]);
for (const id of ["command", "departments", "calendar", "reports"]) keys.add(`page.${id}.label`);
keys.add("nav.group.tong_quan");
const thieu = [...keys].filter((k) => !VI[k] || !EN[k]);
check("mọi khoá của Tổng quan có đủ vi + en", thieu.length === 0, thieu.join(", "));
check("không ghép khoá động (test_i18n không dò được)", !/t\("ov\.[a-z_]*_" \+/.test(OV));

// màu theo theme
const ovCss = CSS.slice(CSS.indexOf("/* ---- Nhóm TỔNG QUAN"));
check("có khối CSS Tổng quan", ovCss.length > 1000);
const cung = (ovCss.match(/(?:^|[^-\w])(?:color|background(?:-color)?)\s*:\s*(#[0-9a-f]{3,8}|white|black)\b/gi) || []);
check("CSS Tổng quan không tô màu cứng cho chữ/nền (dùng token theme)", cung.length === 0, cung.join(" | "));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nTất cả xanh.");
