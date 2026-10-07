/* Sông dung nham chảy CHẬM, lan rộng, cháy tới đâu khói tới đó, có chỉnh tốc độ (1.0.2).

       node tests/js/test_song_dung_nham.js

   Chủ repo (2026-10-07): "dòng dung nham chạy quá nhanh, anh muốn chạy lan to rộng như dòng sông,
   chảy chậm từ từ, vừa chảy đến đâu đốt cháy toả khói mù mịt xung quanh đến đó - có điều chỉnh
   tốc độ chảy nhanh chậm". Bản cũ hiện cả dòng sông trong ~10 giây (14 bước/giây).
   Chạy renderer THẬT trong vm (DOM giả) với đồng hồ ảo, đọc trạng thái qua R.storm().volcano. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", f), "utf8");
const PLANET = D("dashboard/brain-planet.js"), CONSOLE = D("dashboard/console.js"), MAIN = D("server/main.py");
const VI = JSON.parse(D("dashboard/i18n/vi.json")), EN = JSON.parse(D("dashboard/i18n/en.json"));
const fails = [];
const check = (n, c, x) => { console.log((c ? "ok   " : "FAIL ") + n + (x !== undefined ? "  " + x : "")); if (!c) fails.push(n); };
const U = new Proxy(function () {}, { get(t, k) { return k === "width" ? 10 : k === Symbol.toPrimitive ? () => 0 : U; }, apply() { return U; }, set() { return true; } });
const fakeEl = (tag) => ({ tagName: tag, style: {}, dataset: {}, hidden: false, className: "", width: 0, height: 0, offsetWidth: 140,
  classList: { add() {}, remove() {} }, children: [], appendChild(c) { this.children.push(c); return c; }, removeChild() {}, setAttribute() {},
  addEventListener() {}, removeEventListener() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 620, right: 900, bottom: 620 }),
  getContext: (k) => (k === "2d" ? U : null), setPointerCapture() {}, releasePointerCapture() {} });
let NOW = 1000, raf = null;
const ctx = { window: { matchMedia: () => ({ matches: false, addEventListener() {} }), devicePixelRatio: 1, addEventListener() {}, removeEventListener() {}, dispatchEvent() {} },
  document: { documentElement: { getAttribute: () => null }, createElement: fakeEl, addEventListener() {}, removeEventListener() {}, hidden: false },
  navigator: { deviceMemory: 8, hardwareConcurrency: 8 }, localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: { search: "" }, URLSearchParams, performance: { now: () => NOW }, requestAnimationFrame: (cb) => { raf = cb; return 1; }, cancelAnimationFrame() {},
  setTimeout: () => 0, clearTimeout() {}, console, Event: function (n) { this.type = n; } };
vm.createContext(ctx);
vm.runInContext(PLANET, ctx);
const P = ctx.window.JoycePlanet;
const r = P.create({});
r.mount(fakeEl("div"));
const pump = (sec, each) => { const n = Math.round(sec / 0.05); for (let i = 0; i < n; i++) { NOW += 50; const cb = raf; raf = null; if (cb) cb(NOW); if (each) each(i); } };
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const ang = (a, b) => Math.acos(Math.max(-1, Math.min(1, dot(a, b))));
const vo = () => r.storm().volcano;

// ---- 1. Chảy chậm ở tốc độ mặc định ----
check("tốc độ mặc định = 1, khoảng 0,2-3", P.LOOK_DEFAULT.lavaSpeed === 1 && P.LOOK_NUM.lavaSpeed[0] === 0.2 && P.LOOK_NUM.lavaSpeed[1] === 3);
P.setLook({ eruption: true }, { replace: true });
const tips = [];
pump(10, (i) => { const v = vo(); if (v) v.tips.forEach((g) => tips.push(g)); });
let v1 = vo();
check("10 giây đầu đầu dòng chỉ tiến ~16 bước (bản cũ 140)", v1.front > 13 && v1.front < 19, v1.front.toFixed(1));
check("dòng dài nhất cần hơn 1 phút mới chảy hết", v1.longest / 0.028 / 1.6 > 60, Math.round(v1.longest / 0.028 / 1.6) + " giây");
// ---- 2. Cháy tới đâu khói tới đó ----
check("đang chảy thì có khói", v1.plume.length > 20, v1.plume.length);
const gan = v1.plume.filter((g) => tips.some((t) => ang(g, t) < 0.06)).length;
check("khói bốc ngay trên đường dung nham vừa chảy qua (không rải khắp nơi)", gan / v1.plume.length >= 0.95, gan + "/" + v1.plume.length);
check("có đầu dòng đang chảy (3 dòng chính)", v1.tips.length >= 3, v1.tips.length);
// ---- 3. Thanh tốc độ ----
P.setLook({ eruption: false }, { replace: true }); pump(5);
check("tắt phun trào -> hết khói, đầu dòng về 0", vo() === null);
P.setLook({ eruption: true, lavaSpeed: 3 }, { replace: true }); pump(10);
const v3 = vo();
check("tốc độ 3x: 10 giây tiến gấp ~3 lần", v3.front > 42 && v3.front < 54, v3.front.toFixed(1));
P.setLook({ eruption: true, lavaSpeed: 0.2 }, { replace: false }); const f0 = vo().front; pump(10);
check("đổi tốc độ giữa chừng: tiến tiếp mượt từ chỗ đang đứng (không nhảy)", vo().front - f0 > 2.5 && vo().front - f0 < 4, (vo().front - f0).toFixed(2));
// ---- 4. Lan rộng như sông, mã + cài đặt ----
check("sông lan rộng dần phía sau đầu dòng", /var spread = 0\.35 \+ 0\.65 \* smooth\(0, LAVA_SPREAD, behind\);/.test(PLANET));
check("bề rộng theo kích thước thật trên quả cầu (phóng to là sông to)", /2 \* LAVA_HALF \* rv\.w \* R \* L\[0\] \* spread/.test(PLANET));
check("lớp bán trong suốt vẽ một nét liền (không lộ chuỗi hạt ở chỗ nối)", /var tail = Math\.max\(0, last - 5\);/.test(PLANET) && /path\(0, tail\); c\.stroke\(\);/.test(PLANET));
check("dải đất cháy sẫm hai bên + lửa ở đầu dòng", /\[2\.7, "rgba\(30,15,10,"/.test(PLANET) && /lửa ở đầu dòng/.test(PLANET));
check("khói nhiều hơn khi chảy nhanh hơn", /var rate = 9 \* spd \* rv\.w;/.test(PLANET));
check("Cài đặt có thanh tốc độ dòng dung nham", /truot\("lavaSpeed", "look\.lava_speed", "look\.slow", "look\.fast"\)/.test(CONSOLE));
check("máy chủ nhận và kẹp lavaSpeed 0,2-3", /"lavaSpeed": \(0\.2, 3\)/.test(MAIN));
check("chuẩn hoá kẹp tốc độ", P.normLook({ lavaSpeed: 9 }).lavaSpeed === 3 && P.normLook({ lavaSpeed: 0 }).lavaSpeed === 0.2);
check("chuỗi có đủ vi + en", ["look.lava_speed", "look.slow", "look.fast"].every((k) => VI[k] && EN[k]));
r.destroy();
if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nTất cả xanh.");
