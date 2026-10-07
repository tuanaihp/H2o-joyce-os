/* Gió quanh các đám mây, núi lửa + sông dung nham, vòi rồng thấp tới đáy mây + màu vòi (0.65.44).

       node tests/js/test_gio_nui_lua_voi_rong.js

   Chủ repo yêu cầu 2026-10-07 (kèm ảnh):
     - Vòi rồng cao quá nhìn không thật: chỉ nên từ mặt đất tới đám mây. Thêm các bản màu, có tông
       xám, tông tối, kèm sét nhiều hơn.
     - Luồng gió chỉ thổi quanh gần đám mây, từ đám này qua đám kia.
     - Núi lửa: dung nham nhảy nhẹ nhàng từ lõi Trái Đất phun lên đỉnh MỘT ngọn núi, chảy dài xuống
       chân núi thành sông dung nham chảy qua các ngả bao quanh Trái Đất, không điểm dừng.
   Chạy renderer THẬT trong vm (DOM giả, bản safe) với đồng hồ ảo, đọc trạng thái qua R.storm(). */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const PLANET = fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "brain-planet.js"), "utf8");
const CONSOLE = fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "console.js"), "utf8");
const MAIN = fs.readFileSync(path.join(__dirname, "..", "..", "server", "main.py"), "utf8");
const VI = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "i18n", "vi.json"), "utf8"));
const EN = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "i18n", "en.json"), "utf8"));
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
// khoảng cách góc từ điểm g tới cung tròn lớn A-B
const arcDist = (g, a, b) => {
  const n = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const ln = Math.hypot(...n) || 1;
  return Math.asin(Math.min(1, Math.abs(dot(g, n) / ln)));
};

// ---- 1. Gió chỉ quanh và giữa các đám mây ----
P.setLook({ wind: true }, { replace: true });
pump(6);
let st = r.storm();
check("bật riêng gió vẫn có các đám mây để gió thổi quanh", st.cells.length >= 2, st.cells.length + " đám");
let total = 0, near = 0, nhanNoi = 0;
pump(8, (i) => {
  if (i % 5) return;
  const s = r.storm(), byId = {};
  s.cells.forEach((c) => { byId[c.id] = c; });
  s.wind.forEach((w) => {
    total++;
    const A = byId[w.a], B = w.b != null ? byId[w.b] : null;
    if (!A) return;
    if (B) { nhanNoi++; if (arcDist(w.g, A.g, B.g) < 0.6 * Math.max(A.sig, B.sig) + 0.01 && ang(w.g, A.g) < ang(A.g, B.g) + 0.3) near++; }
    else if (ang(w.g, A.g) < 2.2 * A.sig) near++;
  });
});
check("có luồng gió đang thổi", total > 20, total + " lần đo");
check("mọi luồng gió nằm quanh một đám mây hoặc trên đường nối hai đám", near === total, near + "/" + total);
check("có luồng gió thổi TỪ đám này QUA đám kia", nhanNoi > 0, nhanNoi + "");
check("mây khi chỉ có gió là mây trắng xám, có mưa/sét mới đen", /var dkr = clamp\(stormLevel\(\) \/ Math\.max\(cloudLevel\(\), 1e-3\), 0, 1\);/.test(PLANET) && /rcW\*\.72\*uCo\.w/.test(PLANET));
check("bật riêng gió không tạo mưa, không tạo sét", r.storm().bolts.length === 0 && /function cellVis\(cl, cen\) \{ return cl\.k \* cloudLevel\(\)/.test(PLANET));
P.setLook({}, { replace: true });
pump(6);
check("tắt gió -> hết mây, hết gió", r.storm().cells.length === 0 && r.storm().wind.length === 0);

// ---- 2. Núi lửa + sông dung nham ----
P.setLook({ eruption: true }, { replace: true });
pump(1);
let vo = r.storm().volcano;
check("bật phun trào -> có MỘT ngọn núi lửa", !!vo && Array.isArray(vo.g));
const A = P.astro, latlon = (v) => [Math.asin(v[1]) * 57.2958, Math.atan2(v[0], v[2]) * 57.2958];
const ll = latlon(vo.g);
check("núi lửa đặt ở Krakatoa (eo Sunda), gần Việt Nam nên thấy ngay", Math.abs(ll[0] + 6.1) < 0.5 && Math.abs(ll[1] - 105.4) < 0.5, ll.map((x) => x.toFixed(1)).join(", "));
check("toả thành nhiều dòng sông (3 dòng chính + nhánh)", vo.rivers >= 3, vo.rivers + " dòng");
check("sông dài, chảy vòng quanh Trái Đất (dòng dài nhất >= 2,5 rad)", vo.longest >= 2.5, vo.longest.toFixed(2) + " rad");
const s1 = vo.shown;
pump(10);
const s2 = r.storm().volcano.shown;
check("sông chảy dài ra dần từ chân núi (không hiện tức thì)", s1 < s2, s1 + " -> " + s2 + " đoạn");
// 1.0.2: sông chảy chậm, có thanh tốc độ - chi tiết ở test_song_dung_nham.js
check("mảng vỏ nguội trôi theo đồng hồ chảy (theo tốc độ) = dung nham đang chảy không dừng", /c\.lineDashOffset = P_CRUST \* -ft \* sz;/.test(PLANET));
check("magma dâng từ lõi Trái Đất lên chân núi", /ống magma: từ mép lõi/.test(PLANET) && /volc\.magma\.push/.test(PLANET));
check("dung nham sủi NHẸ ở miệng núi (giọt nhảy thấp, rơi lại)", /vh: 0\.5 \+ Math\.random\(\) \* 0\.6/.test(PLANET) && /b\.vh -= 2\.2 \* dt/.test(PLANET));
check("bỏ kiểu bắn tung toé ở bốn miệng + khe nứt rải khắp vỏ", !/VENTS/.test(PLANET) && !/float fis=pow/.test(PLANET));
check("sông gần núi rực, xa thì nguội và nhỏ lại", /var f = \(rv\.start \+ mid\) \/ maxL/.test(PLANET) && /\(1 - 0\.3 \* f\)/.test(PLANET));
P.setLook({}, { replace: true });
pump(5);   // hiệu ứng tắt mờ dần (~3 giây), không tắt phụt
check("tắt phun trào -> không còn núi lửa", r.storm().volcano === null);

// ---- 3. Vòi rồng thấp tới đáy mây + màu ----
P.setLook({ tornado: true }, { replace: true });
const hts = [];
pump(90, (i) => { if (i % 10 === 0) { const t = r.storm().tornado; if (t && t.ht) hts.push(t.ht); } });   // 90 giây: nhiễu chậm, đo ngắn thì dao động
check("vòi rồng thấp: cao tối đa ~0,23 bán kính (mặt đất tới đáy mây)", hts.length > 10 && Math.max(...hts) <= 0.24, Math.max(...hts).toFixed(3));
check("vẫn lúc cao lúc thấp", Math.max(...hts) - Math.min(...hts) > 0.02);
check("đỉnh vòi nhập vào khối mây giông mẹ", /khối mây giông MẸ phủ đỉnh vòi/.test(PLANET));
check("có 5 màu vòi rồng: theo concept, xanh số, lửa, xám bão, đen tối",
  JSON.stringify(P.LOOK_ENUM.tornadoColor[0]) === JSON.stringify(["concept", "cyan", "fire", "grey", "dark"]) && P.LOOK_DEFAULT.tornadoColor === "concept");
const zap = (id) => { const m = PLANET.match(new RegExp('tc === "' + id + '"\\) return \\{[^}]*zap: \\[(\\d+), (\\d+)\\], ground: ([\\d.]+)')); return m ? [+m[1], +m[2], +m[3]] : null; };
const zc = zap("cyan"), zg = zap("grey"), zd = zap("dark");
check("tông xám nhiều sét hơn xanh số (nhịp ngắn hơn, đánh đất nhiều hơn)", zg && zc && zg[0] < zc[0] && zg[1] < zc[1] && zg[2] > zc[2]);
check("tông tối sét dày nhất, đánh cả xuống đất quanh chân vòi", zd && zg && zd[1] < zg[1] && zd[2] > zg[2] && /spawnBolt\(now, \{ g: torn\.g, sig: 0\.05, flash: 0 \}, Ht \* 0\.97\)/.test(PLANET));
check("tông xám / tối không phát sáng (bão thật)", /tc === "grey"\) return \{[^}]*glow: false/.test(PLANET) && /tc === "dark"\) return \{[^}]*glow: false/.test(PLANET));
check("chuẩn hoá giữ màu vòi hợp lệ, bỏ màu lạ", P.normLook({ tornadoColor: "dark" }).tornadoColor === "dark" && P.normLook({ tornadoColor: "tim" }).tornadoColor === "concept");
check("máy chủ nhận khoá tornadoColor", /"tornadoColor": \("concept", "cyan", "fire", "grey", "dark"\)/.test(MAIN));
check("Cài đặt có nút chọn màu vòi rồng", /data-look-tcolor="\$\{x\[0\]\}"/.test(CONSOLE) && /else if \(d\.lookTcolor\) doi\(\{ tornadoColor: d\.lookTcolor \}\);/.test(CONSOLE));
check("chuỗi màu vòi rồng có đủ vi + en", ["look.tor_color", "look.tc_concept", "look.tc_cyan", "look.tc_fire", "look.tc_grey", "look.tc_dark"].every((k) => VI[k] && EN[k]));
P.setLook({ tornado: true, tornadoColor: "dark" }, { replace: true });
let groundBolts = 0;
const seen = new Set();
pump(20, () => { r.storm().bolts.forEach((b) => { const k = b.map((x) => x.toFixed(5)).join(); if (!seen.has(k)) { seen.add(k); groundBolts++; } }); });
check("tông tối: sét đánh xuống đất quanh vòi rồng (không cần bật Sấm sét)", groundBolts >= 5, groundBolts + " tia");
r.destroy();

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
