/* Mục con trên rail (Cẩm nang -> Phòng ban / Fanpage / Zalo) phải THẬT SỰ hiện ra (0.65.45).

       node tests/js/test_rail_muc_con.js

   Chủ repo muốn (2026-10-07): Cẩm nang có nút sổ xuống, ba tab con độc lập Phòng ban, Fanpage,
   Zalo; bấm thẳng "Cẩm nang" là Tổng quan. Bản đầu có đủ mã nhưng mục con KHÔNG BAO GIỜ hiện:
   khuôn <template x-for> của rail có HAI phần tử gốc (nút mục + khối mục con), mà x-for của Alpine
   chỉ nhân bản phần tử gốc ĐẦU TIÊN, khối mục con bị bỏ im lặng. Đo trên app thật (Chrome qua
   DevTools): 0 nút .rail-sub trong DOM.
   Thêm một lỗi: vào một tab con, sang trang khác, bấm lại "Cẩm nang" vẫn ra tab con cũ, vì
   camnang.js giữ tab lần trước còn rail chỉ ép Tổng quan khi đang đứng trong Cẩm nang.

   Canh ở đây:
     - MỌI <template x-for> trong các trang HTML của dashboard có đúng MỘT phần tử gốc.
     - Rail Cẩm nang có bốn mục con đúng thứ tự, bọc chung một gốc với nút mục.
     - store.nav.go("camnang") từ trang khác luôn ghi rõ tab con cần mở (Tổng quan nếu không qua mục con). */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const DASH = path.join(__dirname, "..", "..", "dashboard");
const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!cond) fails.push(name);
}

// ---- 1. Mọi <template x-for> có đúng một phần tử gốc ----
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);
function rootsOfTemplates(html) {
  const src = html.replace(/<!--[\s\S]*?-->/g, (m) => " ".repeat(m.length));
  const out = [];
  const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^<>"']|"[^"]*"|'[^']*')*?)(\/?)>/g;
  const stack = [];   // mỗi phần tử: { tag, tpl: {line, roots} | null }
  let m;
  while ((m = tagRe.exec(src))) {
    const close = !!m[1], tag = m[2].toLowerCase(), attrs = m[3], selfClose = !!m[4] || VOID.has(tag);
    if (close) {
      while (stack.length && stack[stack.length - 1].tag !== tag) stack.pop();
      const top = stack.pop();
      if (top && top.tpl) out.push(top.tpl);
      continue;
    }
    // phần tử con TRỰC TIẾP của một <template x-for> = một gốc
    const parent = stack[stack.length - 1];
    if (parent && parent.tpl) parent.tpl.roots.push(tag);
    if (selfClose) continue;
    const isFor = tag === "template" && /\sx-for\s*=/.test(" " + attrs);
    stack.push({ tag, tpl: isFor ? { line: src.slice(0, m.index).split("\n").length, roots: [], attr: (attrs.match(/x-for\s*=\s*"([^"]*)"/) || [])[1] } : null });
  }
  return out;
}
const pages = fs.readdirSync(DASH).filter((f) => f.endsWith(".html"));
let total = 0;
const bad = [];
pages.forEach((f) => {
  rootsOfTemplates(fs.readFileSync(path.join(DASH, f), "utf8")).forEach((t) => {
    total++;
    if (t.roots.length !== 1) bad.push(f + ":" + t.line + ' x-for="' + t.attr + '" có ' + t.roots.length + " gốc (" + t.roots.join(", ") + ")");
  });
});
check("bộ dò tìm thấy các khuôn x-for (không dò hỏng)", total >= 3, total + " khuôn");
check("mọi <template x-for> có đúng MỘT phần tử gốc (Alpine chỉ nhân bản gốc đầu tiên)", bad.length === 0, bad.join("; "));
// tự kiểm bộ dò: khuôn hai gốc phải bị bắt
const thu = rootsOfTemplates('<div><template x-for="a in b"><button>x</button><template x-if="a"><p>y</p></template></template></div>');
check("bộ dò bắt được khuôn hai gốc (canary)", thu.length === 1 && thu[0].roots.length === 2);

// ---- 2. Rail Cẩm nang ----
const HTML = fs.readFileSync(path.join(DASH, "index.html"), "utf8");
const CON = fs.readFileSync(path.join(DASH, "console.js"), "utf8");
const CSS = fs.readFileSync(path.join(DASH, "console.css"), "utf8");
check("nút mục + khối mục con bọc chung một gốc .rail-item-wrap", /<div class="rail-item-wrap">\s*<button class="rail-item"/.test(HTML) && /\.rail-item-wrap \{ display: contents; \}/.test(CSS));
const subs = (CON.match(/const CN_SUBS = (\[[\s\S]*?\])\s*\.map/) || [])[1] || "[]";
const ids = JSON.parse(subs).map((x) => x[0]);
check("Cẩm nang có bốn mục con đúng thứ tự: Tổng quan, Phòng ban, Fanpage, Zalo", JSON.stringify(ids) === '["tongquan","phongban","fanpage","zalo"]', ids.join(","));
check("có chevron sổ xuống đóng/mở nhóm mục con", /class="rail-chev"/.test(HTML) && /@click\.stop="\$store\.nav\.toggleSubs\(it\.id\)"/.test(HTML));
check("đang ở mục con thì chỉ mục con sáng, mục cha không tô nền", /'has-sub-active'/.test(HTML) && /\$store\.nav\.activeSub\(it\.id\) === \$store\.nav\.subDefault\(it\.id\)/.test(HTML));

// Rail Kinh doanh (2026-10-08): cùng cơ chế Cẩm nang, sub đầu tiên là Xưởng content AI.
const kdSubs = (CON.match(/const KD_SUBS = (\[[\s\S]*?\])\s*\.map/) || [])[1] || "[]";
const kdIds = JSON.parse(kdSubs).map((x) => x[0]);
check("Kinh doanh có mục con Xưởng content AI", kdIds[0] === "xuongcontent", kdIds.join(","));
check("Kinh doanh nằm trong nhóm Năng lực", /"nang_luc"[^\n]*ids:\s*\[[^\]]*"kinhdoanh"/.test(CON));

// go("camnang") chạy thật: từ trang khác phải ghi rõ tab con cần mở
const start = CON.search(/ {6}go\(id\) \{\r?\n\s*const item = RAIL_ITEMS\.find/);   // go() của store nav (không phải bản một dòng cùng tên)
const goSrc = CON.slice(start, CON.indexOf("\n      },", start) + 9).replace(/^\s*go\(id\) \{/, "function go(id) {").replace(/\},\s*$/, "}");
function chay(active, preSub) {
  const nav = [];
  const ctx = { RAIL_ITEMS: [{ id: "camnang" }, { id: "workspace" }], groupLabelOf: () => null, recomputeGraph() {},
    navigateTo: (id) => nav.push(id), window: { __cnSub: preSub || null, __kdSub: null } };
  vm.createContext(ctx);
  vm.runInContext(goSrc + "\nthis.go = go;", ctx);
  const store = { active, cnSub: "fanpage", kdSub: "xuongcontent", openGroup: null };
  ctx.go.call(store, "camnang");
  return { sub: ctx.window.__cnSub, nav, cnSub: store.cnSub };
}
let r = chay("workspace", null);
check("bấm \"Cẩm nang\" từ trang khác -> mở Tổng quan (không giữ tab con cũ)", r.sub === "tongquan" && r.cnSub === "tongquan" && r.nav[0] === "camnang", JSON.stringify(r));
r = chay("workspace", "zalo");
check("bấm mục con Zalo từ trang khác -> mở đúng Zalo", r.sub === "zalo" && r.nav[0] === "camnang");

// go("kinhdoanh") y hệt: từ trang khác mở Xưởng content AI; sub đặt trước được tôn trọng
function chayKd(active, preSub) {
  const nav = [];
  const ctx = { RAIL_ITEMS: [{ id: "kinhdoanh" }, { id: "workspace" }], groupLabelOf: () => null, recomputeGraph() {},
    navigateTo: (id) => nav.push(id), window: { __cnSub: null, __kdSub: preSub || null } };
  vm.createContext(ctx);
  vm.runInContext(goSrc + "\nthis.go = go;", ctx);
  const store = { active, cnSub: "tongquan", kdSub: "xuongcontent", openGroup: null };
  ctx.go.call(store, "kinhdoanh");
  return { sub: ctx.window.__kdSub, nav, kdSub: store.kdSub };
}
r = chayKd("workspace", null);
check("bấm \"Kinh doanh\" từ trang khác -> mở Xưởng content AI", r.sub === "xuongcontent" && r.kdSub === "xuongcontent" && r.nav[0] === "kinhdoanh", JSON.stringify(r));
r = chayKd("workspace", "xuongcontent");
check("bấm mục con Xưởng content AI từ trang khác -> mở đúng tab đó", r.sub === "xuongcontent" && r.nav[0] === "kinhdoanh");

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
