/* Big Bang khi tìm kiếm - giai đoạn 2 của bầu trời tri thức.

       node tests/js/test_big_bang_tri_thuc.js

   Thiết kế: docs/dev/2026-10-bau-troi-tri-thuc.md mục 6. Chạy THẬT focusKnowledge +
   drawKnowFocus trong vm với canvas giả và đồng hồ giả, đi qua từng nhịp: tối trời, hội tụ,
   va chạm (mảnh văng), nở chòm sao (bấm được), thu về khi xoá ô tìm. Cộng hợp đồng nối dây:
   ô VAULT chỉ nổ khi Enter / ngừng gõ 0,7 giây, hud.js hỏi /knowledge/search, rê chuột hai chiều. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const HUD = D("hud.js");
const CON = D("console.js");
const STYLE = D("style.css");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };

function fn(name) {
  const start = PLANET.search(new RegExp("\\n    function " + name + "\\("));
  if (start < 0) { check("có hàm " + name, false); return ""; }
  return PLANET.slice(start, PLANET.indexOf("\n    }\n", start) + 7);
}

// Canvas giả: đếm lệnh vẽ, không vẽ gì.
const ve = { fillRect: 0, arc: 0, stroke: 0, fillText: [] };
const grad = { addColorStop() {} };
const c = new Proxy({}, {
  get(_, k) {
    if (k === "fillRect") return () => ve.fillRect++;
    if (k === "arc") return () => ve.arc++;
    if (k === "stroke") return () => ve.stroke++;
    if (k === "fillText") return (s) => ve.fillText.push(s);
    if (k === "createRadialGradient" || k === "createLinearGradient") return () => grad;
    return () => {};
  },
  set() { return true; },
});
let NOW = 1000;
const ctx = {
  performance: { now: () => NOW },
  window: { t: (k, v) => (k === "planet.k_more" ? "và " + v.n + " tài liệu nữa" : k) },
  PAL: { gold: [255, 211, 106], cyan: [0, 231, 255] },
  PALETTES: { ocean: { deep: [0.01, 0.06, 0.2], sea: [0.024, 0.298, 1], rim: [0, 0.906, 1] } },
  look: { palette: "ocean" },
  hexRGB: (h) => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255],
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v),
  smooth: (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); },
  rgba: (col, a) => "rgba(" + col.join(",") + "," + a + ")",
  geo: { cx: 400, cy: 300, R: 150 },
  W: 800, H: 600, profile: "high",
  know: { hits: [], hover: null, hl: null, bi: { "H2O Studio": { col: [0, 231, 255], name: "H2O Studio" } }, byId: {} },
  foc: null,
  FOC_MAX: 12, FOC_MORE: 30,
  FOC_T: { dim: 0.3, boom: 1.1, bloom0: 1.4, bloom1: 2.5, close: 0.8 },
};
vm.createContext(ctx);
vm.runInContext(["hashRnd", "focDim", "focusKnowledge", "focPal", "drawMiniPlanet", "focStart", "bez", "easeBack",
  "drawKnowFocus", "hitKnow"].map(fn).join("\n"), ctx);
check("hằng nhịp khớp mã nguồn", /FOC_T = \{ dim: 0\.3, boom: 1\.1, bloom0: 1\.4, bloom1: 2\.5, close: 0\.8 \}/.test(PLANET));

// Thiên thể đang hiện trên trời (có vị trí màn hình) + 20 kết quả, 2 cái liên kết nhau.
const k0 = { b: { id: "aaaa0001" }, col: [0, 231, 255], sx: 700, sy: 80, seen: NOW };
ctx.know.byId.aaaa0001 = k0;
const hits = Array.from({ length: 20 }, (_, i) => ({
  id: (i === 0 ? "aaaa0001" : (0x10000000 + i).toString(16)), brain: "H2O Studio", path: "wiki/bao-gia-" + i + ".md",
  title: "Báo giá " + i, stem: "bao-gia-" + i, links: i === 1 ? ["bao-gia-2"] : [], size: 0.5,
}));
ctx.focusKnowledge({ q: "báo giá", hits, total: 33 });
const f = () => ctx.foc;
check("12 tinh cầu + 8 chấm phụ", f().items.length === 12 && f().more.length === 8 && f().total === 33);
check("ô trên cung không trùng nhau", new Set(f().items.map((it) => it.slot)).size === 12);
check("hạng 1 nằm giữa cung", Math.abs(f().items[0].slot - 5.5) <= 0.5);
check("thiên thể đang hiện bay từ đúng chỗ của nó", f().items[0].x0 === 700 && f().items[0].y0 === 80);
check("thiên thể liên quan bị ẩn khỏi trời nền", f().ids.aaaa0001 === 1);

const chay = (giay) => { const buoc = 1 / 30; for (let s = 0; s < giay; s += buoc) { NOW += buoc * 1000; ctx.know.hits = []; ctx.drawKnowFocus(c, NOW, buoc); } };
chay(0.3);
check("0,3 giây: trời đã tối hẳn", f().dark > 0.95 && ctx.focDim() < 0.35);
check("chưa nổ trước 1,1 giây", !f().boom && f().shards.length === 0);
chay(0.85);
check("1,15 giây: đã va chạm, có mảnh văng", f().boom && f().shards.length > 30);
check("đang nổ chưa bấm được gì", ctx.know.hits.length === 0);
chay(1.5);
check("2,65 giây: chòm sao bấm được (12 tinh cầu + 8 chấm)", ctx.know.hits.length === 20);
check("mảnh văng đã tắt hết", f().shards.length === 0);
check("có nhãn cho 3 kết quả đầu", ["Báo giá 0", "Báo giá 1", "Báo giá 2"].every((s) => ve.fillText.includes(s)));
check("có dòng 'và 21 tài liệu nữa'", ve.fillText.includes("và 21 tài liệu nữa"));
const p0 = f().items[0];
check("tinh cầu hạng 1 ở phía trên địa cầu", p0.py < ctx.geo.cy - ctx.geo.R);
check("bấm trúng tinh cầu hạng 1", ctx.hitKnow(p0.px, p0.py) === p0.k);
const stroke0 = ve.stroke; ctx.know.hits = []; ctx.drawKnowFocus(c, NOW, 1 / 30);
check("có vệt nối chòm sao giữa hai tài liệu liên kết", ve.stroke > stroke0);

ctx.focusKnowledge(null);
chay(0.4);
check("xoá ô tìm: đang thu về, không bấm được nữa", f() && f().closing && ctx.know.hits.length === 0);
chay(0.5);
check("thu về xong: hết Big Bang, trời sáng lại", ctx.foc === null && ctx.focDim() === 1);

ctx.profile = "safe";
ctx.focusKnowledge({ q: "x", hits: hits.slice(0, 3), total: 3 });
check("máy yếu: bỏ hội tụ và vụ nổ", f().lite === true);
chay(0.6);
check("máy yếu: chòm sao hiện ngay sau 0,5 giây, không mảnh văng", ctx.know.hits.length === 3 && f().shards.length === 0);
ctx.focusKnowledge({ q: "rong", hits: [], total: 0 });
check("không có kết quả = thu về", f().closing === true);

// ---- nối dây ----
check("ô VAULT: nổ khi Enter hoặc ngừng gõ 0,7 giây, không theo từng chữ",
  /skyT = setTimeout\(\(\) => bauTroi\(input\.value\.trim\(\)\), 700\)/.test(CON) && /e\.key === "Enter"\) \{ clearTimeout\(t\); apply\(\); bauTroi/.test(CON));
check("ô VAULT: cùng từ khoá không nổ lại", /if \(q === skyQ\) return;/.test(CON));
check("ô VAULT: xoá / Esc thì thu chòm sao", /e\.key === "Escape"\) \{ input\.value = ""; apply\(\); bauTroi\(""\)/.test(CON));
check("hud.js hỏi /knowledge/search và bỏ kết quả của từ khoá cũ",
  /\/knowledge\/search\?brain=/.test(HUD) && /if \(_timQ !== q \|\| !planet\) return;/.test(HUD));
check("rê chuột hai chiều", /joyce:vault-hover/.test(CON) && /joyce:vault-hover/.test(HUD)
  && /joyce:sky-hover/.test(HUD) && /joyce:sky-hover/.test(CON) && /onKnowledgeHover: baoRePhiaVault/.test(HUD));
check("Big Bang vẽ sau cùng (đè cả nhãn)", PLANET.indexOf("drawKnowFocus(c, now, reduced") > PLANET.indexOf("if (opts.labels !== false) drawLabels(c);"));
check("R.focusKnowledge / highlightKnowledge / knowledgeFocus lộ ra",
  /R\.focusKnowledge = focusKnowledge;/.test(PLANET) && /R\.highlightKnowledge = /.test(PLANET) && /R\.knowledgeFocus = /.test(PLANET));
check("chữ 'và N tài liệu nữa' có vi + en", /\{n\}/.test(VI["planet.k_more"] || "") && /\{n\}/.test(EN["planet.k_more"] || ""));
check("dòng kết quả sáng theo token theme", /\.vr-item\.vr-sky \{ background: var\(--info-wash\); box-shadow: inset 2px 0 0 var\(--accent\); \}/.test(STYLE));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_big_bang_tri_thuc: tất cả pass");
