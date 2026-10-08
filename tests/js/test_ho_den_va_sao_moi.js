/* Hố đen luôn xoay, nhìn sâu vào hố đen, và sao mới sinh sau khi nạp (giai đoạn 3).

       node tests/js/test_ho_den_va_sao_moi.js

   Chủ yêu cầu 2026-10-08 (ảnh mẫu: xoáy bụi xanh, luồng bụi bị hút; đĩa bồi tụ trong xanh
   ngoài hồng cam, hai tia phản lực):
     - hố đen LUÔN xoay chậm kèm luồng bụi bị hút, đá vụn (tài liệu thô) chờ xung quanh;
     - bấm giữa hố đen thì phóng vào nhìn sâu: tinh thể dữ liệu thô xoáy vào, va nhau, nổ;
     - giai đoạn 3: nạp xong tia sáng bắn đúng ghim H2O Studio, tài liệu vừa chưng cất sinh
       thành sao mới bay từ đó lên chỗ của nó.
   Chạy thật các hàm trong vm với canvas giả và đồng hồ giả, cộng hợp đồng nối dây. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const HUD = D("hud.js");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));
const SKY = fs.readFileSync(path.join(__dirname, "..", "..", "server", "knowledge_sky.py"), "utf8");

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };
function fn(name) {
  const s = PLANET.indexOf("\n    function " + name + "(");
  if (s < 0) { check("có hàm " + name, false); return ""; }
  let i = PLANET.indexOf("{", s), d = 0;
  for (; i < PLANET.length; i++) { if (PLANET[i] === "{") d++; else if (PLANET[i] === "}" && --d === 0) break; }
  return PLANET.slice(s, i + 1);
}
const hang = (k) => { const m = new RegExp("var " + k + " = ([^;]+);").exec(PLANET); check("đọc được " + k, !!m); return m ? "var " + k + " = " + m[1] + ";" : ""; };

const ve = { text: [] };
const grad = { addColorStop() {} };
const c = new Proxy({}, {
  get(_, k) {
    if (k === "fillText") return (s) => ve.text.push(s);
    if (k === "createRadialGradient" || k === "createLinearGradient") return () => grad;
    return () => {};
  },
  set() { return true; },
});
let NOW = 1000;
const ctx = {
  performance: { now: () => NOW }, Math, window: {},
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v),
  smooth: (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); },
  rgba: (col, a) => "rgba(" + col.join(",") + "," + a + ")",
  geo: { cx: 400, cy: 300, R: 150, bh: { x: 700, y: 90, r: 14 } },
  W: 800, H: 600, profile: "high",
  ing: { on: false, items: [], k: 0, beam: 0 },
  know: { debris: Array.from({ length: 9 }, (_, i) => ({ b: { title: "tai-lieu-tho-" + i + ".docx" } })) },
  tip: { hidden: false },
  foc: null,
};
vm.createContext(ctx);
vm.runInContext([hang("BH_TILT"), hang("BH_CAP"), hang("bhs"), hang("BHV_CAP"), hang("bhv"),
  ...["hashRnd", "bhPt", "bhInit", "bhStream", "drawBHSwirl", "onBlackHole", "bhvName", "bhvCrystal", "bhvInit",
    "openBlackHole", "bhvPos", "drawCrystal", "drawBHView", "fireBurst", "blueBurst"].map(fn)].join("\n"), ctx);

// ---- hố đen luôn xoay ----
ctx.drawBHSwirl(c, NOW, 0);
const p0 = ctx.bhs.parts.map((p) => ({ a: p.a, r: p.r }));
check("xoáy bụi đủ hạt theo hồ sơ máy (high: 260 + 90 luồng)", ctx.bhs.parts.length === 260 && ctx.bhs.stream.length === 90);
const buoc = (n, dt) => { for (let i = 0; i < n; i++) { NOW += dt * 1000; ctx.drawBHSwirl(c, NOW, dt); } };
buoc(30, 1 / 30);
const quay = ctx.bhs.parts.map((p, i) => ({ r: p0[i].r, da: p.a - p0[i].a, vao: p.r < p0[i].r }));
const ngoai = quay.filter((q) => q.r > 5 && q.da > 0), trong = quay.filter((q) => q.r < 2 && q.da > 0);
// Vài hạt bị luồng bụi kéo về rìa đĩa (đặt lại góc) nên đo theo tỉ lệ, không đòi tuyệt đối.
check("hố đen LUÔN xoay khi không nạp gì (>= 90% hạt quay tới)", quay.filter((q) => q.da > 0).length >= 0.9 * quay.length);
check("trong xoay nhanh hơn ngoài (kiểu Kepler)",
  trong.length && ngoai.length && Math.min(...trong.map((q) => q.da)) > Math.max(...ngoai.map((q) => q.da)));
check("bụi trôi dần vào tâm", quay.filter((q) => q.vao).length > 200);
check("vành sáng quanh miệng hố xoay", ctx.bhs.spin > 0.4);
const t0 = ctx.bhs.parts[0].a; ctx.ing.k = 1; NOW += 33; ctx.drawBHSwirl(c, NOW, 1 / 30);
const nhanh = ctx.bhs.parts[0].a - t0; ctx.ing.k = 0; const t1 = ctx.bhs.parts[0].a; NOW += 33; ctx.drawBHSwirl(c, NOW, 1 / 30);
check("đang nạp dữ liệu thì xoáy nhanh hơn", nhanh > (ctx.bhs.parts[0].a - t1) * 2);
check("bấm trúng hố đen trong ~1,8 bán kính", ctx.onBlackHole(700 + 20, 90) && !ctx.onBlackHole(700 + 40, 90));

// ---- nhìn sâu vào hố đen ----
ctx.openBlackHole(true);
check("mở: tinh thể mang đúng tên tài liệu thô", ctx.bhv.crys.length === 26 && ctx.bhv.crys.every((q) => /^tai-lieu-tho-\d\.docx$/.test(q.name)));
const xem = (giay) => { const b = 1 / 30; for (let s = 0; s < giay - 1e-9; s += b) { NOW += b * 1000; ctx.drawBHView(c, NOW, b); } };
xem(1.5);
check("màn mở gần trọn sau 1,5 giây", ctx.bhv.k > 0.95);
check("có tiêu đề + số tài liệu chờ + lối ra", ve.text.includes("Hố đen chưng cất") && ve.text.includes("9 tài liệu thô đang chờ chưng cất")
  && ve.text.includes("Bấm bất kỳ đâu hoặc Esc để quay lại"));
let noLan = 0; const pushGoc = ctx.bhv.booms.push;
xem(6);
check("tinh thể va nhau gây nổ đều đặn (>= 2 vụ trong 6 giây)", ctx.bhv.nameI > 26 + 3);
check("tinh thể không lọt vào lòng hố (sàn 0,36)", ctx.bhv.crys.every((q) => q.rho >= 0.36 - 1e-9));
ctx.ing.on = true; ctx.ing.items = ["dang-nap.pdf"]; ve.text = []; xem(0.1);
check("đang nạp: ghi rõ tên tài liệu đang chưng cất", ve.text.includes("Đang chưng cất: dang-nap.pdf"));
ctx.ing.on = false;
ctx.openBlackHole(false); xem(1.5);
check("đóng: màn thu về hết", ctx.bhv.k === 0);
void noLan; void pushGoc;

// ---- nối dây trong mã nguồn ----
const up = PLANET.slice(PLANET.indexOf("function onUp("), PLANET.indexOf("function onDbl("));
check("đang nhìn sâu: bấm đâu cũng quay ra (xét trước mọi thứ)",
  up.indexOf("openBlackHole(false)") > 0 && up.indexOf("openBlackHole(false)") < up.indexOf("hitSat("));
check("bấm hố đen xét trước thiên thể và hành tinh",
  up.indexOf("onBlackHole(p.x, p.y)") > 0 && up.indexOf("onBlackHole(p.x, p.y)") < up.indexOf("hitKnow(p.x, p.y)")
  && up.indexOf("onBlackHole(p.x, p.y)") < up.indexOf("onPlanetClick"));
check("Esc thoát cảnh nhìn sâu", /on\(window, "keydown", function \(e\) \{ if \(e\.key === "Escape" && bhv\.target\) openBlackHole\(false\); \}\);/.test(PLANET));
check("đang nhìn sâu thì lăn chuột không phóng quả cầu", /if \(bhv\.k > 0\.05\) \{ e\.preventDefault\(\); return; \}/.test(PLANET));
check("xoáy bụi vẽ dưới thiên thể, cảnh nhìn sâu vẽ trên cùng",
  PLANET.indexOf("drawBHSwirl(c, now, ddt);") < PLANET.indexOf("drawKnowSky(c, now, ddt);")
  && PLANET.indexOf("drawBHView(c, now, reduced") > PLANET.indexOf("drawKnowFocus(c, now, reduced"));
check("vành photon không tô kín lòng hố (gradient từ tâm, trong suốt tới mép bóng)",
  /createRadialGradient\(C\.x, C\.y, 0, C\.x, C\.y, Rb \* 1\.35\), r0 = 0\.95 \/ 1\.35/.test(PLANET));
check("R.openBlackHole + R.blackHoleView lộ ra", /R\.openBlackHole = /.test(PLANET) && /R\.blackHoleView = /.test(PLANET));

// ---- giai đoạn 3 ----
const ctx3 = {
  performance: { now: () => NOW }, PAL: { gold: [255, 211, 106], cyan: [0, 231, 255] },
  clamp: ctx.clamp, ing: { beam: 0 },
  know: { stars: [], orbit: [], debris: [], hits: [], hover: null, counts: null, scope: "", bi: {}, byId: {}, hl: null },
  KNOW_DUST: [150, 160, 175],
};
vm.createContext(ctx3);
vm.runInContext(["hashRnd", "setKnowledge"].map(fn).join("\n"), ctx3);
const troi = (ids) => ({ brains: [{ key: "H2O Studio", color: "cyan" }], bodies: ids.map((id) => ({
  id, brain: "H2O Studio", kind: id.startsWith("0") ? "orbit" : "star", ring: 1, path: id + ".md", size: 0.2 })) });
ctx3.setKnowledge(troi(["a0000001", "a0000002", "0b000001"]));
check("lần nạp ĐẦU không coi là sao mới", ctx3.know.stars.every((s) => !s.born) && ctx3.ing.beam === 0);
ctx3.know.byId["0b000001"].a = 4.2;
ctx3.setKnowledge(troi(["a0000001", "a0000002", "0b000001", "a0000003", "a0000004"]));
const moi = ctx3.know.stars.filter((s) => s.born);
check("tài liệu vừa chưng cất thành sao mới (2 sao, nối đuôi nhau)", moi.length === 2 && moi[1].born > moi[0].born);
check("sao mới bắn lại tia sáng cho khớp nhịp", ctx3.ing.beam === 1);
check("nạp lại không làm chấm vành giật về góc ban đầu", ctx3.know.byId["0b000001"].a === 4.2);
check("tia sáng nhắm ghim H2O Studio khi đang thấy", /var stp = studioPt\(\), ex = stp \? stp\.x : /.test(PLANET)
  && /window\.JoyceVNGeo && window\.JoyceVNGeo\.studio/.test(PLANET));
check("sao mới bay từ ghim H2O Studio lên chỗ của nó", /s\.bornFrom = studioPt\(\)/.test(PLANET));
check("hud.js: nạp xong thì nạp lại bầu trời bỏ cache", /if \(_napDangChay && !r\.active\) setTimeout\(function \(\) \{ loadKnow\(true, true\); \}, 1200\);/.test(HUD)
  && /\(fresh \? "&fresh=1" : ""\)/.test(HUD));
check("máy chủ: fresh=1 bỏ qua cache 60 giây", /fresh: bool = Query\(False\)/.test(SKY) && /if hit and not fresh and/.test(SKY));
const khoa = ["planet.bh_tip", "planet.bh_tip_d", "planet.bh_title", "planet.bh_wait", "planet.bh_now", "planet.bh_exit"];
check("đủ chữ vi + en cho hố đen", khoa.every((k) => VI[k] && EN[k]) && !khoa.some((k) => /[–—]/.test(VI[k] + EN[k])));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_ho_den_va_sao_moi: tất cả pass");
