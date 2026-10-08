/* Big Bang khi tìm kiếm - giai đoạn 2 của bầu trời tri thức (bản 1.0.6).

       node tests/js/test_big_bang_tri_thuc.js

   Thiết kế: docs/dev/2026-10-bau-troi-tri-thuc.md mục 6. Chủ góp ý 2026-10-08 sau khi xem bản
   1.0.5: tinh cầu kiến thức GIỮ NGUYÊN CHỖ và phóng to tại chỗ (không bay ra vòng cung), mặt ĐÁ
   lồi lõm có màu dải ngân hà (không phải quả cầu xanh trơn), các thiên thể quanh nó lao vào gây
   nổ LỬA vàng rồi nổ XANH có tia sáng, và ánh Mặt Trời chiếu dần: khớp nhất sáng nhất.

   Chạy THẬT focusKnowledge + drawKnowFocus trong vm với canvas giả và đồng hồ giả, đi qua từng
   nhịp. Cộng hợp đồng nối dây: ô VAULT chỉ nổ khi Enter / ngừng gõ 0,7 giây, hud.js hỏi
   /knowledge/search, rê chuột hai chiều. */
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

// Bóc một hàm theo cặp ngoặc (hàm một dòng cũng bóc đúng).
function fn(name) {
  const s = PLANET.indexOf("\n    function " + name + "(");
  if (s < 0) { check("có hàm " + name, false); return ""; }
  let i = PLANET.indexOf("{", s), d = 0;
  for (; i < PLANET.length; i++) { if (PLANET[i] === "{") d++; else if (PLANET[i] === "}" && --d === 0) break; }
  return PLANET.slice(s, i + 1);
}

const ve = { fillText: [], lighter: 0, drawImage: 0 };
const grad = { addColorStop() {} };
const c = new Proxy({}, {
  get(_, k) {
    if (k === "fillText") return (s) => ve.fillText.push(s);
    if (k === "drawImage") return () => ve.drawImage++;
    if (k === "createRadialGradient" || k === "createLinearGradient") return () => grad;
    return () => {};
  },
  set(_, k, v) { if (k === "globalCompositeOperation" && v === "lighter") ve.lighter++; return true; },
});
let NOW = 1000;
const ctx = {
  performance: { now: () => NOW },
  window: { t: (k, v) => (k === "planet.k_more" ? "và " + v.n + " tài liệu nữa" : k) },
  PAL: { gold: [255, 211, 106], cyan: [0, 231, 255] },
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v),
  smooth: (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); },
  rgba: (col, a) => "rgba(" + col.join(",") + "," + a + ")",
  cam: { yaw: 0, pitch: 0 },
  ringPt: () => ({ x: 0, y: 0, z: 1 }),
  geo: { cx: 400, cy: 300, R: 150, sun: { x: 700, y: 120, r: 30 } },
  W: 800, H: 600, profile: "high",
  know: { hits: [], hover: null, hl: null, bi: { "H2O Studio": { i: 0, col: [0, 231, 255], name: "H2O Studio" } }, byId: {} },
  foc: null, ROCK: [], NP: null, NV: null,
  KNOW_DUST: [150, 160, 175],
};
vm.createContext(ctx);
const ham = ["hashRnd", "camRot", "knowPos", "focAvoidEarth", "focClamp", "focDim", "focHidden", "focusKnowledge", "h3", "vnoise", "fbm3",
  "rockSprite", "buildRockNow", "drawRockPlanet", "fireBurst", "blueBurst", "bez", "easeBack", "drawKnowFocus", "hitKnow"];
vm.runInContext(ham.map(fn).join("\n"), ctx);
for (const k of ["FOC_MAX", "FOC_T", "FOC_GALAXY"]) {   // FOC_MAX cùng dòng với FOC_MORE
  const m = new RegExp("var " + k + " = ([^;]+);").exec(PLANET);
  check("đọc được hằng " + k, !!m);
  if (m) vm.runInContext("var " + k + " = " + m[1] + ";", ctx);
}
check("nhịp: va chạm 1,1s, lửa 0,6s, xanh từ 1,6s, lớn lên 1,6-2,7s, nắng 2,0-3,6s",
  /FOC_T = \{ dim: 0\.3, hit: 1\.1, fire: 0\.6, blue0: 1\.6, blue: 1\.0, grow0: 1\.6, grow1: 2\.7, sun0: 2\.0, sun1: 3\.6, close: 0\.8 \}/.test(PLANET));

// Đếm số lần nổ lửa / nổ xanh theo thời điểm.
const no = { fire: [], blue: [] };
const fireGoc = ctx.fireBurst, blueGoc = ctx.blueBurst;
ctx.fireBurst = function (cc, it, R1, u) { no.fire.push(it.rank); return fireGoc(cc, it, R1, u); };
ctx.blueBurst = function (cc, it, R1, u) { no.blue.push(it.rank); return blueGoc(cc, it, R1, u); };

// Bầu trời: thiên thể đang hiện (sao có v) + một hàng xóm đang hiện ngay cạnh kết quả số 1.
const sao = (id, lon, lat) => ({ b: { id, kind: "star" }, col: [0, 231, 255],
  v: [Math.cos(lat) * Math.sin(lon) * 2, Math.sin(lat) * 2, Math.cos(lat) * Math.cos(lon) * 2] });
const k0 = sao("aaaa0001", 0.3, 0.6);
ctx.know.byId.aaaa0001 = k0;
const p0 = ctx.knowPos(k0);
const hangXom = { b: { id: "bbbb0001", kind: "star" }, col: [255, 62, 200] };
ctx.know.hits = [{ x: p0.x + 30, y: p0.y + 10, k: hangXom }];
const hits = Array.from({ length: 20 }, (_, i) => ({
  id: i === 0 ? "aaaa0001" : (0x10000000 + i).toString(16), brain: "H2O Studio", path: "wiki/bao-gia-" + i + ".md",
  title: "Báo giá " + i, stem: "bao-gia-" + i, links: i === 1 ? ["bao-gia-2"] : [], size: 0.5,
}));
ctx.focusKnowledge({ q: "báo giá", hits, total: 33 });
const f = () => ctx.foc;
check("12 tinh cầu + 8 chấm phụ", f().items.length === 12 && f().more.length === 8 && f().total === 33);
check("khớp nhất to nhất", f().items[0].rF > f().items[1].rF && f().items[1].rF > f().items[11].rF);
check("khớp nhất được nắng chiếu sáng nhất", f().items[0].lit === 1 && f().items.slice(1).every((it) => it.lit < 1));
check("hàng xóm đang hiện bị hút vào vụ nổ (ẩn khỏi trời nền)", ctx.focHidden(hangXom) && ctx.focHidden(k0));
check("mỗi kết quả có ít nhất 4 mảnh lao vào", f().items.every((it) => f().frags.filter((fr) => fr.it === it).length >= 4));
check("mảnh đầu tiên xuất phát đúng chỗ hàng xóm", f().frags[0].x0 === p0.x + 30 && f().frags[0].y0 === p0.y + 10);
check("tinh cầu không đè lên nhau sau khi giãn chỗ", f().items.every((A, i) => f().items.every((B, j) => j <= i
  || Math.hypot((B.p0.x + B.off.x) - (A.p0.x + A.off.x), (B.p0.y + B.off.y) - (A.p0.y + A.off.y)) >= A.rF + B.rF + 15)));

const chay = (giay) => { const b = 1 / 30; for (let s = 0; s < giay - 1e-9; s += b) { NOW += b * 1000; ctx.know.hits = []; ctx.drawKnowFocus(c, NOW, b); } };
chay(0.3);
check("0,3 giây: trời tối hẳn", f().dark > 0.95 && ctx.focDim() < 0.35);
check("mẫu đá được dựng dần mỗi khung một mẫu (hết hàng đợi)", f().toBuild.length === 0);
check("chưa nổ trước khi mảnh lao tới", no.fire.length === 0 && no.blue.length === 0);
chay(0.9);
check("1,2 giây: nổ LỬA ở tinh cầu khớp nhất, tia lửa văng", no.fire.includes(0) && f().sparks.length > 0 && no.blue.length === 0);
check("đang nổ chưa bấm được gì", ctx.know.hits.length === 0);
chay(0.6);
check("1,8 giây: sang nổ XANH chưng cất", no.blue.includes(0));
chay(1.0);
check("2,8 giây: 12 tinh cầu + 8 chấm phụ bấm được", ctx.know.hits.length === 20);
const it0 = f().items[0], lp = ctx.knowPos(k0);
check("tinh cầu GIỮ CHỖ: nằm đúng chỗ thật của nó (+ độ lệch giãn chỗ)",
  Math.abs(it0.px - Math.min(Math.max(lp.x + it0.off.x, it0.rF + 12), 800 - it0.rF - 12)) < 1
  && Math.hypot(it0.off.x, it0.off.y) < it0.rF * 3);
check("bấm trúng tinh cầu khớp nhất", ctx.hitKnow(it0.px, it0.py) === k0);
check("có nhãn cho 3 kết quả đầu", ["Báo giá 0", "Báo giá 1", "Báo giá 2"].every((s) => ve.fillText.includes(s)));
check("có dòng 'và 21 tài liệu nữa'", ve.fillText.includes("và 21 tài liệu nữa"));
check("nổ dùng chế độ phát sáng cộng dồn (lighter)", ve.lighter > 10);
// Nổ xanh của hạng sau trễ tối đa 11 x 0,035 + 0,08 giây so với hạng đầu: tới 3,2 giây là tắt hết.
check("nổ xanh tắt hết sau 3,2 giây", (() => { chay(0.4); const n0 = no.blue.length; chay(0.2); return no.blue.length === n0; })());
check("hàng xóm vẫn ẩn trong lúc chòm sao đứng chờ", ctx.focHidden(hangXom));

ctx.focusKnowledge(null);
chay(0.4);
check("xoá ô tìm: đang thu về, không bấm được nữa", f() && f().closing && ctx.know.hits.length === 0);
chay(0.5);
check("thu về xong: hết Big Bang, trời sáng lại, hàng xóm hiện lại", ctx.foc === null && ctx.focDim() === 1 && !ctx.focHidden(hangXom));

ctx.profile = "safe"; no.fire = []; no.blue = [];
ctx.focusKnowledge({ q: "x", hits: hits.slice(0, 3), total: 3 });
check("máy yếu: không mảnh, không hút hàng xóm", f().lite === true && f().frags.length === 0 && Object.keys(f().gone).length === 0);
chay(1.0);
check("máy yếu: không nổ, tinh cầu hiện sau 1 giây", no.fire.length === 0 && no.blue.length === 0 && ctx.know.hits.length === 3);
ctx.focusKnowledge({ q: "rong", hits: [], total: 0 });
check("không có kết quả = thu về", f().closing === true);

// ---- mặt đá + nối dây ----
check("tinh cầu là mặt đá (drawImage mẫu đá, có quầng hồng-xanh-tím), không còn quả cầu xanh trơn",
  /drawImage\(spr, -r, -r, r \* 2, r \* 2\)/.test(PLANET) && /FOC_GALAXY = \[\[255, 92, 190\], \[80, 150, 255\], \[150, 100, 255\]\]/.test(PLANET)
  && !/function drawMiniPlanet/.test(PLANET) && !/function focPal/.test(PLANET));
check("mặt đá có miệng hố (lòng lõm + vành nổi)", /h -= 0\.22 \* \(1 - q \* q\)/.test(PLANET) && /h \+= 0\.12 \* \(1 - \(q - 1\) \/ 0\.25\)/.test(PLANET));
check("nổ xanh có hai tia ngược chiều", /for \(var s = -1; s <= 1; s \+= 2\)/.test(PLANET));
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
