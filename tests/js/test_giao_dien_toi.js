/* Giao diện TỐI đọc được trên mọi trang, kể cả trang làm sau này (0.65.43).

       node tests/js/test_giao_dien_toi.js

   Chủ repo báo 2026-10-07 (kèm ảnh): các tab Cẩm nang ở giao diện tối là thẻ TRẮNG chữ TRẮNG,
   "cho đến về sau với bất kỳ tab mới nào" cũng vậy. Hai nguyên nhân, cả hai đều im lặng:
     1. Trang viết var(--card, #fff) mà --card không ai định nghĩa -> trình duyệt lấy màu dự phòng
        sáng. Quét ra 15 biến kiểu đó (--danger-bg rơi về hồng nhạt, --surface/--acc rỗng...).
     2. Bản vá đã thêm --card nhưng chú thích CSS phía trên có "--surface-" + dấu sao + gạch chéo
        liền chữ: chú thích đóng sớm, phần còn lại thành CSS rác nuốt luôn khối :root của bản vá.
   Canh ở đây:
     - Không chú thích CSS nào đóng giữa chữ.
     - Dùng var(--x) ở đâu thì --x phải được định nghĩa ở đâu đó (CSS, hoặc JS đặt bằng setProperty).
     - Bộ biến ngữ nghĩa dùng chung nằm trong style.css và có giá trị riêng cho theme sáng.
     - Các cặp chữ/nền chính đủ tương phản (WCAG >= 4,5 cho chữ thường) ở cả hai theme. */
const fs = require("fs");
const path = require("path");

const DASH = path.join(__dirname, "..", "..", "dashboard");
const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!cond) fails.push(name);
}
function walk(d, out, withVendor) {
  for (const f of fs.readdirSync(d)) {
    const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) { if (f === "node_modules" || (f === "vendor" && !withVendor)) continue; walk(p, out, withVendor); }
    else if (/\.(css|js|html)$/.test(f)) out.push(p);
  }
  return out;
}
const own = walk(DASH, [], false), all = walk(DASH, [], true);
const rel = (p) => path.relative(DASH, p).replace(/\\/g, "/");
const read = (p) => fs.readFileSync(p, "utf8");

// ---- 1. Chú thích CSS không đóng giữa chữ ----
const badComments = [];
own.filter((p) => p.endsWith(".css")).forEach((p) => {
  read(p).split(/\r?\n/).forEach((line, i) => { if (/\*\/[^\s]/.test(line)) badComments.push(rel(p) + ":" + (i + 1)); });
});
check("không chú thích CSS nào đóng giữa chữ (dấu sao + gạch chéo liền chữ phía sau)", badComments.length === 0, badComments.join(", "));

// ---- 2. Biến dùng thì phải có định nghĩa ----
const defined = new Set();
all.forEach((p) => {
  let s = read(p);
  if (p.endsWith(".css")) s = s.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of s.matchAll(/(--[a-zA-Z0-9_-]+)\s*:/g)) defined.add(m[1]);
  for (const m of s.matchAll(/setProperty\(\s*["'`](--[a-zA-Z0-9_-]+)/g)) defined.add(m[1]);
});
const undef = {};
own.forEach((p) => {
  let s = read(p);
  if (p.endsWith(".css")) s = s.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of s.matchAll(/var\(\s*(--[a-zA-Z0-9_-]+)/g)) if (!defined.has(m[1])) (undef[m[1]] = undef[m[1]] || new Set()).add(rel(p));
});
const undefList = Object.keys(undef).map((k) => k + " (" + [...undef[k]].join(", ") + ")");
check("mọi var(--x) đều có --x được định nghĩa (không rơi về màu dự phòng sáng)", undefList.length === 0, undefList.join("; "));

// ---- 3. Bộ biến ngữ nghĩa dùng chung trong style.css ----
const STYLE = read(path.join(DASH, "style.css"));
const blocks = (sel) => {
  const out = {}, re = new RegExp(sel.replace(/[[\]"]/g, "\\$&") + "\\s*\\{([^}]*)\\}", "g");
  const css = STYLE.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of css.matchAll(re)) for (const d of m[1].matchAll(/(--[a-zA-Z0-9_-]+)\s*:\s*([^;]+);/g)) out[d[1]] = d[2].trim();
  return out;
};
const dark = blocks(":root"), light = Object.assign({}, dark, blocks(':root[data-theme="light"]'));
const SEM = ["--card", "--panel", "--line", "--wash", "--surface", "--acc", "--ink-3", "--danger-ink", "--danger-bg", "--warn-ink", "--warn-bg", "--ok-ink", "--ok-bg"];
check("style.css định nghĩa bộ biến ngữ nghĩa dùng chung", SEM.every((k) => k in dark), SEM.filter((k) => !(k in dark)).join(", "));
check("màu báo (lỗi / cảnh báo / ổn) có giá trị riêng cho theme sáng",
  ["--danger-ink", "--danger-bg", "--warn-ink", "--warn-bg", "--ok-ink", "--ok-bg"].every((k) => light[k] !== dark[k]));
check("--card trỏ về token của theme, không phải màu cứng", /^var\(--surface/.test(dark["--card"] || ""));

// ---- 4. Tương phản chữ / nền ----
const hex = (h) => { h = h.replace("#", ""); if (h.length === 3) h = h.split("").map((c) => c + c).join(""); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255); };
const lum = (c) => { const l = c.map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4))); return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2]; };
const ratio = (a, b) => { const x = lum(hex(a)), y = lum(hex(b)); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
[["tối", dark], ["sáng", light]].forEach(([ten, T]) => {
  [["--text", 7], ["--text2", 4.5], ["--danger-ink", 4.5], ["--warn-ink", 4.5], ["--ok-ink", 4.5], ["--text3", 3]].forEach(([k, min]) => {
    const r = /^#[0-9a-f]{3,6}$/i.test(T[k] || "") && /^#[0-9a-f]{3,6}$/i.test(T["--bg"] || "") ? ratio(T[k], T["--bg"]) : 0;
    check(`theme ${ten}: ${k} trên --bg đủ tương phản (>= ${min})`, r >= min, r.toFixed(2));
  });
});

// ---- 5. Các thẻ Cẩm nang dùng biến của theme ----
const CCSS = read(path.join(DASH, "console.css"));
check("thẻ Cẩm nang nền theo theme (var(--card...))", /\.cn-card \{[^}]*background: var\(--card/.test(CCSS));
check("quy ước dev có mục màu giao diện tối", /Màu và giao diện tối/.test(fs.readFileSync(path.join(__dirname, "..", "..", "docs", "quy-uoc-dev.md"), "utf8")));

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
