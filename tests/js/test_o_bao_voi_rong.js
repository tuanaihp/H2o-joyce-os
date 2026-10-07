/* Ô bão (mưa từng vùng + sét trong vùng mưa) và vòi rồng hạt sáng chạy quanh tinh cầu (0.65.41).

       node tests/js/test_o_bao_voi_rong.js

   Chủ repo yêu cầu 2026-10-07 (kèm ảnh tham khảo): mưa chỉ ở những đám mây u tối, rơi từ dưới
   mây xuống bề mặt, từng vùng cách nhau chứ không mưa khắp quả cầu; sét vàng trắng lan rộng,
   đánh xuống trong vùng mưa; vòi rồng như ảnh mẫu (hạt xoắn, loe ở đỉnh), chạy quanh tinh cầu
   qua các vùng khác nhau không điểm dừng, lúc to lúc nhỏ, lúc cao lúc thấp, gió cuộn xoáy.

   Chạy renderer THẬT trong vm với DOM giả (bản safe, không WebGL) và tự bơm khung hình với đồng
   hồ ảo, rồi đọc trạng thái qua R.storm(). */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const PLANET = fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "brain-planet.js"), "utf8");
const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!cond) fails.push(name);
}
const U = new Proxy(function () {}, {
  get(t, k) { return k === "width" ? 10 : k === Symbol.toPrimitive ? () => 0 : U; },
  apply() { return U; }, set() { return true; },
});
function fakeEl(tag) {
  return {
    tagName: tag, style: {}, dataset: {}, hidden: false, className: "", width: 0, height: 0, offsetWidth: 140,
    classList: { add() {}, remove() {} }, children: [],
    appendChild(c) { this.children.push(c); return c; }, removeChild() {}, setAttribute() {},
    addEventListener() {}, removeEventListener() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 620, right: 900, bottom: 620 }),
    getContext: (k) => (k === "2d" ? U : null), setPointerCapture() {}, releasePointerCapture() {},
  };
}
let NOW = 1000, raf = null;
const ctx = {
  window: { matchMedia: () => ({ matches: false, addEventListener() {} }), devicePixelRatio: 1,
    addEventListener() {}, removeEventListener() {}, dispatchEvent() {} },
  document: { documentElement: { getAttribute: () => null }, createElement: fakeEl, addEventListener() {}, removeEventListener() {}, hidden: false },
  navigator: { deviceMemory: 8, hardwareConcurrency: 8 },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: { search: "" }, URLSearchParams, performance: { now: () => NOW },
  requestAnimationFrame: (cb) => { raf = cb; return 1; }, cancelAnimationFrame() {},
  setTimeout: () => 0, clearTimeout() {}, console, Event: function (n) { this.type = n; },
};
vm.createContext(ctx);
vm.runInContext(PLANET, ctx);
const P = ctx.window.JoycePlanet;
const r = P.create({});
r.mount(fakeEl("div"));
function pump(sec, each) {
  const n = Math.round(sec / 0.05);
  for (let i = 0; i < n; i++) { NOW += 50; const cb = raf; raf = null; if (cb) cb(NOW); if (each) each(i); }
}
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const ang = (a, b) => Math.acos(Math.max(-1, Math.min(1, dot(a, b))));
const A = P.astro, G = A.viewMat(14.5, 108.4);   // góc nhìn mặc định (VIEW_HOME)
const viewZ = (g) => A.toView(G, g)[2];

// ---- 1. Mưa từng vùng ----
P.setLook({ rain: true }, { replace: true });
pump(6);
let st = r.storm();
check("bật mưa -> có ô bão (bản safe: 2 ô)", st.cells.length === 2, st.cells.length + " ô");
check("các ô bão nằm cách xa nhau (>= 0,4 rad), không phủ khắp quả cầu",
  st.cells.length === 2 && ang(st.cells[0].g, st.cells[1].g) > 0.4, st.cells.length === 2 ? ang(st.cells[0].g, st.cells[1].g).toFixed(2) : "");
check("ô bão sinh ra ở nửa cầu đang thấy", st.cells.every((c) => viewZ(c.g) > -0.1));
check("mỗi ô chỉ phủ một vùng nhỏ (bán kính 0,12-0,2 rad)", st.cells.every((c) => c.sig >= 0.12 && c.sig <= 0.2));
check("ô bão lớn dần lên chứ không bật phụt (cường độ 0..1)", st.cells.every((c) => c.k >= 0 && c.k <= 1));
const g0 = st.cells[0].g.slice();
pump(3);
check("ô bão trôi theo gió (đổi chỗ theo thời gian)", ang(g0, r.storm().cells[0].g) > 0.005);
check("mưa không làm mây dày khắp quả cầu: shader chỉ mưa trong ô (uCl.w * rcW)",
  /gl\.uniform4f\(u\.uCl, look\.clouds \* 0\.55, Math\.min\(0\.85, look\.cloudDark \* 0\.75\)/.test(PLANET) &&
  /float rn=\(uWx\.y\*\(wv\+sw\)\+uCl\.w\*rcW\*\.6\)\*cm;/.test(PLANET));
check("shader làm mây dày + đen trong ô bão", /cov=uCl\.x\+[^;]*rcW\*1\.1;/.test(PLANET) && /rcW\*\.72/.test(PLANET));
check("hạt mưa rơi từ đáy mây (điểm đất nâng lên) xuống điểm đất",
  /var sx = gp\.x \+ up\[0\] \* L/.test(PLANET) && /c\.moveTo\(x - \(gp\.x - sx\)/.test(PLANET));
check("khối mây vẽ SAU mưa (hạt mưa chui ra từ đáy mây)", /drawRain\(c, dt\);\s*drawStormClouds\(c\);/.test(PLANET));

// ---- 2. Sét chỉ trong vùng mưa ----
P.setLook({ rain: true, lightning: true }, { replace: true });
let nBolts = 0, outside = 0;
const seen = new Set();
pump(25, () => {
  const s = r.storm();
  s.bolts.forEach((b) => {
    const key = b.map((x) => x.toFixed(5)).join(",");
    if (seen.has(key)) return;
    seen.add(key); nBolts++;
    const near = s.cells.some((c) => ang(b, c.g) < 2.2 * c.sig);
    if (!near) outside++;
  });
});
check("bật sét -> có tia sét đánh xuống", nBolts >= 4, nBolts + " tia");
check("mọi tia sét đều nằm trong vùng mưa của một ô bão", outside === 0, outside + " tia ngoài ô");
check("sét màu vàng trắng (quầng vàng cam, lõi trắng)", /rgba\(255,190,80,/.test(PLANET) && /rgba\(255,255,240,/.test(PLANET));
check("sét lan rộng: nhiều nhánh + tia bò trên mặt đất", /nb = 2 \+ \(\(Math\.random\(\) \* 3\) \| 0\)/.test(PLANET) && /b\.arcs\.forEach/.test(PLANET));
check("có chớp trong mây (khối mây loé)", /else cl\.flash = 1;/.test(PLANET));
P.setLook({}, { replace: true });
pump(8);
check("tắt mưa + sét -> ô bão tan hết", r.storm().cells.length === 0);

// ---- 3. Vòi rồng ----
P.setLook({ tornado: true }, { replace: true });
const samples = [];
pump(90, (i) => { if (i % 20 === 0) { const t = r.storm().tornado; if (t) samples.push(t); } });
check("bật lốc -> có vòi rồng", samples.length > 50);
let stops = 0;
for (let i = 1; i < samples.length; i++) if (ang(samples[i].g, samples[i - 1].g) < 0.01) stops++;
check("vòi rồng chạy KHÔNG điểm dừng", stops === 0, stops + " lần đứng yên");
let far = 0;
samples.forEach((a) => samples.forEach((b) => { far = Math.max(far, ang(a.g, b.g)); }));
check("đi qua nhiều vùng khác nhau trên tinh cầu", far > 0.6, far.toFixed(2) + " rad");
const vis = samples.filter((s) => viewZ(s.g) > 0).length / samples.length;
check("phần lớn thời gian ở nửa cầu đang thấy (lái về giữa khi ra mép)", vis > 0.8, (vis * 100).toFixed(0) + "%");
const szs = samples.map((s) => s.sz), hks = samples.map((s) => s.hk);
check("lúc to lúc nhỏ", Math.max(...szs) - Math.min(...szs) > 0.2 && Math.min(...szs) >= 0.6 && Math.max(...szs) <= 1.35);
check("lúc cao lúc thấp", Math.max(...hks) - Math.min(...hks) > 0.2 && Math.min(...hks) >= 0.5 && Math.max(...hks) <= 1.2);
check("hạt xoắn quanh trục, loe rộng ở đỉnh (phễu nhỏ dần xuống chân)",
  /var rad = function \(f\) \{ return rBot \+ \(rTop - rBot\) \* Math\.pow\(f, 1\.6\); \};/.test(PLANET) && /Math\.max\(0, p\.f - 0\.86\) \* 3\.4/.test(PLANET));
check("gió cuộn xoắn ốc quanh chân + quanh thân", /for \(var arm = 0; arm < 3; arm\+\+\)/.test(PLANET) && /gió thổi vòng quanh thân/.test(PLANET));
check("sét quấn quanh vòi", /torn\.zaps\.push\(zz\)/.test(PLANET));
check("màu hạt theo concept bề mặt (Đại dương = xanh, Dung nham = lửa) hoặc màu chọn riêng", /function tornadoTheme\(\)/.test(PLANET) && /particleSprite\(cb\)/.test(PLANET));
check("mây xoáy/đế mây/bụi chân vẽ bằng elip mờ đều (không ra đĩa mép cứng)", (PLANET.match(/softEllipse\(c, /g) || []).length >= 4);
P.setLook({}, { replace: true });
pump(6);
check("tắt lốc -> vòi rồng biến mất", r.storm().tornado === null);
r.destroy();

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
