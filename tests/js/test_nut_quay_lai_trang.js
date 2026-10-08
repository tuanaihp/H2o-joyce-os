/* Nút Quay lại trang trước, cho MỌI trang.

       node tests/js/test_nut_quay_lai_trang.js

   Chủ repo báo 2026-10-08: đang ở Bảng điều hành, bấm mũi tên sang Tệp tin là hết đường về
   đúng chỗ vừa xem. Vệt được ghi ở navigateTo (mọi lần đổi trang đi qua đó), nút trên đầu
   trang lùi một bước và trả lại vị trí cuộn. File này chạy thật các hàm vệt trong vm với
   history giả, và khoá phần nút trong index.html. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..", "..");
const CON = fs.readFileSync(path.join(ROOT, "dashboard", "console.js"), "utf8");
const HTML = fs.readFileSync(path.join(ROOT, "dashboard", "index.html"), "utf8");
const CSS = fs.readFileSync(path.join(ROOT, "dashboard", "console.css"), "utf8");
const VI = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard", "i18n", "vi.json"), "utf8"));
const EN = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard", "i18n", "en.json"), "utf8"));

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };

function fn(name) {
  const start = CON.search(new RegExp("  (?:async )?function " + name + "\\("));
  if (start < 0) { check("có hàm " + name, false); return ""; }
  return CON.slice(start, CON.indexOf("\n  }", start) + 4);
}

// ---- Dựng một "trình duyệt" nhỏ: history có ngăn xếp thật + popstate ----
const nav = { active: "home", settingsTab: "general", cnSub: "tongquan", openGroup: "", navStack: [] };
const hist = { entries: [{ jvpg: 0 }], i: 0 };
let onPop = null;
const bodyEl = { scrollTop: 0, scrollHeight: 5000, clientHeight: 800 };
const ctx = {
  Alpine: { store: () => nav }, TRANG_GOP: {}, TRANG_CUOI_KEY: "k", localStorage: { setItem() {} },
  window: {}, document: { body: { classList: { toggle() {} } } }, _pageLeave: null,
  renderPage: () => { bodyEl.scrollTop = 0; }, refreshModelUi() {}, parkQuickSet() {}, recomputeGraph() {},
  groupLabelOf: () => "g", body: () => bodyEl, setTimeout: (f) => f(), Date,
  _dangLuiTrang: false, _cuonCho: null,
  history: {
    get state() { return hist.entries[hist.i]; },
    pushState(s) { hist.entries = hist.entries.slice(0, hist.i + 1); hist.entries.push(s); hist.i++; },
    back() { if (hist.i > 0) { hist.i--; onPop({ state: hist.entries[hist.i] }); } },
  },
};
ctx.window.Alpine = ctx.Alpine;
ctx.window.addEventListener = (ev, f) => { if (ev === "popstate") onPop = f; };
vm.createContext(ctx);
const nhanPopstate = CON.slice(CON.indexOf('    window.addEventListener("popstate", (e) => {'),
  CON.indexOf("\n    });", CON.indexOf('    window.addEventListener("popstate", (e) => {')) + 8);
check("bóc được bộ nghe popstate của vệt trang", nhanPopstate.length > 100 && /jvpg/.test(nhanPopstate));
vm.runInContext(["_doSauLichSu", "_traCuon", "_ghiVetTrang", "_layCuonCho", "_luiVe", "luiTrang", "navigateTo"]
  .map(fn).join("\n") + "\n" + nhanPopstate, ctx);

// Tổng quan (đã cuộn xuống 1200px) → Tệp tin → nút Quay lại
ctx.navigateTo("command");
bodyEl.scrollTop = 1200;
ctx.navigateTo("files");
check("đi một trang thì vệt có 2 bước (home, command)", nav.navStack.length === 2 && nav.navStack[1].id === "command");
check("vệt ghi vị trí cuộn của trang vừa rời", nav.navStack[1].cuon === 1200);
check("mỗi bước có một mục lịch sử trình duyệt mang jvpg", hist.entries.length === 3 && hist.entries[2].jvpg === 2);
ctx.luiTrang();
check("Quay lại về đúng Bảng điều hành", nav.active === "command");
check("Quay lại trả đúng vị trí cuộn", bodyEl.scrollTop === 1200);
check("lùi xong vệt bớt một bước, không ghi thêm", nav.navStack.length === 1);
check("lịch sử trình duyệt lùi theo, không lệch", hist.i === 1);

// Nút Back của trình duyệt / chuột / vuốt cạnh điện thoại
ctx.history.back();
check("Back trình duyệt cũng lùi trang (về Joyce)", nav.active === "home" && nav.navStack.length === 0);

// Trình sửa file chèn mục riêng; đóng nó (popstate về mục của trang hiện tại) không được lùi trang
ctx.navigateTo("kanban");
ctx.history.pushState({ jvfe: 1 });
ctx.history.back();
check("đóng trình sửa file không lùi trang", nav.active === "kanban" && nav.navStack.length === 1);

// Đổi tab trong Cài đặt không phải là một bước lùi
ctx.navigateTo("settings");
const truoc = nav.navStack.length;
ctx.navigateTo("settings", true, "appearance");
check("đổi tab Cài đặt không thêm bước vào vệt", nav.navStack.length === truoc && nav.settingsTab === "appearance");

// ---- Nút trên đầu trang ----
check("index.html có nút Quay lại ở đầu trang chung", /class="cview-back"[^>]*x-show="\$store\.nav\.navStack\.length"[^>]*@click="\$store\.nav\.back\(\)"/.test(HTML));
check("nút ghi rõ về trang nào", /t\('nav\.back_to'/.test(HTML) && /backMeta/.test(HTML));
check("store nav có navStack + back()", /navStack: \[\],/.test(CON) && /back\(\) \{ luiTrang\(\); \}/.test(CON));
check("i18n vi + en có nav.back_to", /\{trang\}/.test(VI["nav.back_to"] || "") && /\{trang\}/.test(EN["nav.back_to"] || ""));
check("CSS nút dùng token theme, không màu cứng",
  /\.cview-back \{[^}]*var\(--surface-1\)[^}]*\}/.test(CSS) && !/\.cview-back \{[^}]*#[0-9a-f]{3,6}/i.test(CSS));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_nut_quay_lai_trang: tất cả pass");
