/* Bầu trời tri thức - phía trình duyệt (brain-planet.js + hud.js + Cài đặt).

       node tests/js/test_bau_troi_tri_thuc.js

   Thiết kế: docs/dev/2026-10-bau-troi-tri-thuc.md. Chạy THẬT setKnowledge / hitKnow trong vm
   (vị trí cố định theo id, phân loại, trần theo hồ sơ máy), cộng các hợp đồng đọc từ mã nguồn:
   thứ tự vẽ, bấm thiên thể trước khi bấm hành tinh, hud.js nạp đúng endpoint, công tắc trong
   Cài đặt, chữ có đủ vi + en, CSS dùng token theme. */
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

function fn(src, name) {
  const start = src.search(new RegExp("\\n    function " + name + "\\("));
  if (start < 0) { check("có hàm " + name, false); return ""; }
  return src.slice(start, src.indexOf("\n    }\n", start) + 7);
}

// ---- chạy thật setKnowledge / hitKnow ----
const ctx = {
  PAL: { cyan: [0, 231, 255], magenta: [255, 62, 200], gold: [255, 211, 106] },
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v),
  KNOW_DUST: [150, 160, 175],
  performance: { now: () => 0 }, ing: { beam: 0 },
  know: { stars: [], orbit: [], debris: [], hits: [], hover: null, counts: null, scope: "" },
};
vm.createContext(ctx);
vm.runInContext(["hashRnd", "setKnowledge", "hitKnow"].map((n) => fn(PLANET, n)).join("\n"), ctx);
const data = {
  scope: "all", counts: { total: 4 },
  brains: [{ key: "H2O Studio", color: "cyan" }, { key: "ThuyH2O - Hoc Vien", color: "magenta" }],
  bodies: [
    { id: "4f281768", kind: "star", brain: "H2O Studio", path: "wiki/a.md", size: 0.9, proc: true },
    { id: "0000abcd", kind: "orbit", ring: 2, brain: "ThuyH2O - Hoc Vien", path: "memory/facts/b.md", size: 0.1 },
    { id: "12345678", kind: "debris", brain: "Lạ", path: "sources/c.pdf", size: 0 },
    { id: "9abcdef0", kind: "star", brain: "ThuyH2O - Hoc Vien", path: "wiki/d.md", size: 0.3 },
  ],
};
ctx.setKnowledge(data);
const k1 = JSON.stringify(ctx.know.stars.map((s) => s.v));
check("phân loại: 2 sao, 1 chấm vành, 1 đá vụn",
  ctx.know.stars.length === 2 && ctx.know.orbit.length === 1 && ctx.know.debris.length === 1);
check("màu theo thương hiệu, brain lạ về vàng",
  ctx.know.stars[0].col === ctx.PAL.cyan && ctx.know.orbit[0].col === ctx.PAL.magenta && ctx.know.debris[0].col === ctx.PAL.gold);
check("chấm vành giữ đúng vành", ctx.know.orbit[0].ring === 2);
check("đá vụn là đa giác 5-7 cạnh", ctx.know.debris[0].poly.length >= 5 && ctx.know.debris[0].poly.length <= 7);
ctx.setKnowledge(JSON.parse(JSON.stringify(data)));
check("vị trí CỐ ĐỊNH theo id (nạp lại không nhảy)", JSON.stringify(ctx.know.stars.map((s) => s.v)) === k1);
const thuTuKhac = JSON.parse(JSON.stringify(data));
thuTuKhac.bodies.reverse();
ctx.setKnowledge(thuTuKhac);
const v4f = ctx.know.stars.find((s) => s.b.id === "4f281768").v;
check("đổi thứ tự danh sách không đổi vị trí", JSON.stringify(v4f) === JSON.stringify(JSON.parse(k1)[0]));
check("sao nằm trong vỏ 1,55-2,6R", ctx.know.stars.every((s) => { const r = Math.hypot(...s.v); return r >= 1.549 && r <= 2.601; }));
ctx.setKnowledge({});
check("dữ liệu rỗng không vỡ", ctx.know.stars.length === 0 && ctx.know.debris.length === 0);
ctx.know.hits = [{ x: 100, y: 100, k: "A" }, { x: 140, y: 100, k: "B" }];
check("bấm trong 9px trúng thiên thể gần nhất", ctx.hitKnow(103, 102) === "A" && ctx.hitKnow(137, 99) === "B");
check("bấm xa hơn 9px thì không trúng", ctx.hitKnow(120, 100) === null);

// ---- hợp đồng trong mã nguồn ----
check("trần theo hồ sơ máy (safe nhỏ nhất)", /KNOW_CAP = \{ high: \[1500, 600, 600\], balanced: \[900, 400, 350\], safe: \[300, 150, 120\]/.test(PLANET));
const iSky = PLANET.indexOf("drawKnowSky(c, now, ddt);"), iRing = PLANET.indexOf("drawRings(c, false);", iSky - 200);
check("sao + đá vụn vẽ TRƯỚC vành (nằm sau mọi thứ)", iSky > 0 && iRing > iSky);
check("chấm vành vẽ cả nửa sau lẫn nửa trước",
  /drawKnowOrbit\(c, false, ddt\);/.test(PLANET) && /drawKnowOrbit\(c, true, 0\);/.test(PLANET));
const up = PLANET.slice(PLANET.indexOf("function onUp("), PLANET.indexOf("function onDbl("));
check("bấm thiên thể được xét trước bấm hành tinh (gọi Joyce)",
  up.indexOf("hitKnow(p.x, p.y)") > 0 && up.indexOf("hitKnow(p.x, p.y)") < up.indexOf("onPlanetClick"));
check("chấm vành hưởng thanh Cỡ chấm trên vành", /look\.orbitDot \* \(front \? 1 : 0\.8\)/.test(PLANET));
check("công tắc knowledge trong LOOK_BOOL + FX_KEYS",
  /LOOK_BOOL = \{[^}]*knowledge: true/.test(PLANET) && /FX_KEYS = \[[^\]]*"knowledge"/.test(PLANET));
check("R.setKnowledge + R.knowledgeInfo lộ ra", /R\.setKnowledge = setKnowledge;/.test(PLANET) && /R\.knowledgeInfo = /.test(PLANET));
check("hud.js nạp /knowledge/sky và đọc nhanh /knowledge/quick",
  /\/knowledge\/sky\?brain=/.test(HUD) && /\/knowledge\/quick\?brain=/.test(HUD) && /onKnowledgeClick: function \(b\) \{ openKnow\(b\);/.test(HUD));
check("bấm thiên thể CHỈ mở thẻ tóm tắt; nút Mở trên thẻ mới mở khung file lớn (kể cả brain phòng khác)",
  /onKnowledgeClick: function \(b\) \{ openKnow\(b\); \},/.test(HUD)
  && /if \(mo\) mo\.addEventListener\("click", function \(\) \{ moFileTriThuc\(b\); \}\);/.test(HUD)
  && /window\.JoyceFileEditor\.open\(b\.path, goc \? \{ brain: goc \} : null\)/.test(HUD));
check("tìm brain của file: /knowledge/sky -> ô chọn brain -> /brains (máy chủ cũ vẫn mở được)",
  /x\.dataset\.brainName === b\.brain/.test(HUD) && /jget\("\/brains"\)/.test(HUD) && /hit\.is_default \? "brain" : hit\.path/.test(HUD));
check("trình sửa file mở được brain khác (opts.brain)", /var b = \(opts && opts\.brain\) \|\| brain\(\);/.test(D("file-editor.js")));
check("Cài đặt có công tắc Bầu trời tri thức", /congTac\("knowledge", "sparkles", "look\.fx_knowledge", "look\.fx_knowledge_d"\)/.test(CON));
const khoa = ["planet.k_star", "planet.k_proc", "planet.k_skill", "planet.k_workflow", "planet.k_memory", "planet.k_debris",
  "planet.k_loading", "planet.k_err", "planet.k_no_heads", "planet.k_raw", "planet.k_open", "planet.k_ask", "planet.k_ask_q",
  "look.fx_knowledge", "look.fx_knowledge_d"];
const thieu = khoa.filter((k) => !VI[k] || !EN[k]);
check("đủ chữ vi + en" + (thieu.length ? " (thiếu " + thieu.join(", ") + ")" : ""), thieu.length === 0);
check("chữ mới không có gạch ngang dài", !khoa.some((k) => /[–—]/.test((VI[k] || "") + (EN[k] || ""))));
const css = STYLE.slice(STYLE.indexOf("/* Thẻ Đọc nhanh"), STYLE.indexOf(".planet-ctx .pc-know-note"));
check("CSS thẻ Đọc nhanh dùng token theme, không màu cứng", css.length > 100 && !/#[0-9a-f]{3,6}\b|\bwhite\b(?!-)/i.test(css));

// ---- KHO TRI THỨC trong khung TÍN HIỆU GẦN (chạy thật trong vm) ----
function fnHud(name) {
  const s = HUD.indexOf("\n  function " + name + "(");
  if (s < 0) { check("hud.js có hàm " + name, false); return ""; }
  let i = HUD.indexOf("{", s), d = 0;
  for (; i < HUD.length; i++) { if (HUD[i] === "{") d++; else if (HUD[i] === "}" && --d === 0) break; }
  return HUD.slice(s, i + 1);
}
const hctx = { D: {}, t: (k, v) => k + (v ? JSON.stringify(v) : ""), esc: (s) => String(s),
  row: (k, v) => "<row " + k + "=" + v + ">" };
vm.createContext(hctx);
vm.runInContext(fnHud("gopBanChu") + "\n" + fnHud("khoTriThucHtml"), hctx);
const raw = { scope: "all", brains: [{ key: "A", brand: "H2O Studio" }, { key: "B", brand: "ThuyH2O" }, { key: "C", brand: "" }],
  bodies: [
    { id: "1", kind: "debris", brain: "A", path: "sources/x.docx" }, { id: "2", kind: "debris", brain: "A", path: "sources/x.docx.txt" },
    { id: "3", kind: "debris", brain: "B", path: "sources/x.docx.txt" }, { id: "4", kind: "star", brain: "B", path: "wiki/q.md", proc: true },
    { id: "5", kind: "orbit", ring: 0, brain: "C", path: "skills/s/SKILL.md" }, { id: "6", kind: "orbit", ring: 2, brain: "A", path: "memory/facts/f.md" }] };
const g = hctx.gopBanChu(raw);
check("trình duyệt cũng gộp X.docx.txt cùng brain (khác brain thì giữ)", g.bodies.length === 5 && !g.bodies.some((b) => b.id === "2"));
check("đếm lại đúng loại", g.counts.total === 5 && g.counts.debris === 2 && g.counts.star === 1 && g.counts.proc === 1
  && g.counts.skill === 1 && g.counts.memory === 1 && g.counts.workflow === 0);
check("đếm theo thương hiệu", g.counts.brands["H2O Studio"] === 2 && g.counts.brands.ThuyH2O === 2 && g.counts.brands[""] === 1);
hctx.D.know = g;
const html = hctx.khoTriThucHtml();
check("khối KHO TRI THỨC có tổng, từng loại và thương hiệu",
  /hud\.k_title/.test(html) && /hud\.k_total=5/.test(html) && /hud\.k_debris=2/.test(html) && /hud\.k_owner/.test(html));
check("khối nằm trong khung TÍN HIỆU GẦN", /el\.innerHTML \+= khoTriThucHtml\(\);/.test(HUD));
const khoaKho = ["hud.k_title", "hud.k_scope_all", "hud.k_scope_one", "hud.k_total", "hud.k_star", "hud.k_proc", "hud.k_skill",
  "hud.k_workflow", "hud.k_memory", "hud.k_debris", "hud.k_owner"];
check("đủ chữ vi + en cho KHO TRI THỨC", khoaKho.every((k) => VI[k] && EN[k]));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_bau_troi_tri_thuc: tất cả pass");
