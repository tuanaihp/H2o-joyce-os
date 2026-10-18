// 3D Joyce (joyce-humanoid.js): pho tượng hạt thay lớp nhìn "3D View".
// Chạy: node tests/js/test_joyce_humanoid.js
//
// Kiểm hai tầng:
//   1) Hình người tham số hoá (sampleFigure - hàm thuần, không cần GL): đủ hạt,
//      đúng bố cục đầu/cổ/vai, lõi vàng cam kind=1 trong đầu, bụi mờ kind=2.
//   2) API vòng đời (create/mount/setJoyceState/setAudioAmplitude/activate) với
//      DOM giả - canvas getContext trả null (máy không có WebGL2) phải chịu được:
//      dataset.quality="nogl", không ném, activate/pause/destroy vẫn gọi được.
//   3) Nối dây bằng source (khuôn test_mat_trang): tab đổi tên 3D Joyce, script
//      nạp, brain-v2 gọi setHumanoid, hud feed trạng thái, i18n nhãn mới.
const fs = require("fs");
const path = require("path");

// ---------- DOM giả tối thiểu ----------
function el() {
  const e = {
    children: [], dataset: {}, style: {}, hidden: false, className: "", textContent: "",
    _cls: new Set(),
    setAttribute() {}, appendChild(c) { e.children.push(c); c.parentNode = e; },
    removeChild() {}, addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return { width: 800, height: 600, left: 0, top: 0 }; },
    getContext() { return null; },   // giả máy KHÔNG có WebGL2
  };
  e.classList = {
    add: (c) => e._cls.add(c), remove: (c) => e._cls.delete(c),
    toggle: (c, f) => { const on = f === undefined ? !e._cls.has(c) : !!f; on ? e._cls.add(c) : e._cls.delete(c); },
    contains: (c) => e._cls.has(c),
  };
  return e;
}
const dispatched = [];
global.window = {
  addEventListener() {}, removeEventListener() {},
  dispatchEvent(ev) { dispatched.push(ev); return true; },
  devicePixelRatio: 1,
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  CustomEvent: class { constructor(t, o) { this.type = t; this.detail = (o || {}).detail; } },
};
global.document = {
  createElement: () => el(), hidden: false,
  addEventListener() {}, removeEventListener() {},
};
global.requestAnimationFrame = () => 0;
global.cancelAnimationFrame = () => {};
const _ls = new Map();
global.localStorage = { getItem: (k) => _ls.has(k) ? _ls.get(k) : null, setItem: (k, v) => _ls.set(k, String(v)), removeItem: (k) => _ls.delete(k) };

eval(fs.readFileSync(path.join(__dirname, "../../dashboard/joyce-humanoid.js"), "utf8"));

const fails = [];
const check = (name, cond, extra) => { console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : "")); if (!cond) fails.push(name); };

const H = window.JoyceHumanoid;

// ---------- 1) Module surface ----------
check("window.JoyceHumanoid tồn tại", !!H);
check("API: create + sampleFigure + STATES + activate", typeof H.create === "function" && typeof H.sampleFigure === "function" && Array.isArray(H.STATES) && typeof H.activate === "function");
check("STATES đủ 8 trạng thái thật của Joyce", H.STATES.length === 8 && H.STATES.indexOf("INTERRUPTING") >= 0 && H.STATES.indexOf("SPEAKING") >= 0);

// ---------- 2) sampleFigure: hình người ----------
const NB = 4000, NC = 300, NM = 200;
const fig = H.sampleFigure(NB, NC, NM);
check("tổng hạt = thân + lõi + bụi", fig.n === NB + NC + NM && fig.pos.length === fig.n * 3);
check("có vị trí xuất phát intro (aFrom)", fig.from.length === fig.n * 3);
check("có seed 4 kênh (phase/rate/twinkle/size)", fig.seed.length === fig.n * 4);

let head = 0, sho = 0, inBox = true;
for (let i = 0; i < NB; i++) {
  const x = fig.pos[i * 3], y = fig.pos[i * 3 + 1], z = fig.pos[i * 3 + 2];
  if (Math.abs(x) > 0.8 || y > 0.8 || y < -0.45 || Math.abs(z) > 0.5) inBox = false;
  if (y > 0.55) head++;
  if (Math.abs(x) > 0.3 && y < 0.2) sho++;
}
check("thân nằm trong hộp pho tượng (đầu ~0.73, vai rộng ~0.55)", inBox);
check("có khối đầu (hạt trên y>0.55)", head > NB * 0.15, head + " hạt");
check("có khối vai (hạt |x|>0.3 dưới cổ)", sho > NB * 0.08, sho + " hạt");

let coreOK = true, moteOK = true, coreInHead = 0;
for (let i = NB; i < NB + NC; i++) {
  if (fig.kind[i] !== 1) coreOK = false;
  const dy = fig.pos[i * 3 + 1] - 0.52;
  if (Math.abs(dy) < 0.12 && Math.abs(fig.pos[i * 3]) < 0.1) coreInHead++;
}
for (let i = NB + NC; i < fig.n; i++) {
  if (fig.kind[i] !== 2) moteOK = false;
}
check("lõi não kind=1, nằm gọn trong đầu", coreOK && coreInHead > NC * 0.7, coreInHead + "/" + NC);
check("bụi mờ kind=2", moteOK);

const fig2 = H.sampleFigure(NB, NC, NM);
check("cùng seed -> cùng hình (deterministic)", fig.pos[0] === fig2.pos[0] && fig.pos[3 * 100] === fig2.pos[3 * 100]);

// ---------- 3) STATE_CFG khớp trạng thái thật ----------
["READY", "CONNECTING", "LISTENING", "THINKING", "SPEAKING", "INTERRUPTING", "RECONNECTING", "ERROR"].forEach((s) => {
  const c = H.STATE_CFG[s];
  check("STATE_CFG[" + s + "] đủ hệ số", c && ["agit", "swirl", "breath", "lean", "dim", "err"].every((k) => typeof c[k] === "number"));
});
check("SPEAKING khuấy hơn LISTENING", H.STATE_CFG.SPEAKING.agit > H.STATE_CFG.LISTENING.agit);
check("LISTENING nghiêng tới trước (lean>0)", H.STATE_CFG.LISTENING.lean > 0 && H.STATE_CFG.READY.lean === 0);
check("THINKING xoáy vòng (swirl>0)", H.STATE_CFG.THINKING.swirl > 0);
check("ERROR có tông đỏ (err=1)", H.STATE_CFG.ERROR.err === 1);
check("INTERRUPTING mờ đi (dim<1)", H.STATE_CFG.INTERRUPTING.dim < 1);

// ---------- 4) Profiles ----------
check("4 hồ sơ chất lượng", Object.keys(H.PROFILES).sort().join(",") === "balanced,high,reduced,safe");
check("high nhiều hạt hơn safe", H.PROFILES.high.body > H.PROFILES.safe.body);
check("safe tắt twinkle, high bật", H.PROFILES.safe.twinkle === 0 && H.PROFILES.high.twinkle === 1);

// ---------- 5) Vòng đời không GL ----------
const host = el();
const R = H.create({});
check("create trả instance đủ API", ["mount","resize","setJoyceState","setAudioAmplitude","setInCall","pause","resume","activate","destroy","info","setQuality","isActive"].every((k) => typeof R[k] === "function"));
R.mount(host);
check("mount gắn canvas + nhãn trạng thái vào stage", host.children.length === 2 && host.children[0].className === "humanoid-gl" && host.children[1].className === "hum-status");
check("không WebGL2 -> dataset.quality=\"nogl\", không ném", host.dataset.quality === "nogl");
check("info().gl=false khi không có GL", R.info().gl === false);

R.setJoyceState("listening");
check("setJoyceState chuẩn hoá hoa/thường", R.info().state === "LISTENING");
R.setJoyceState("BOGUS_STATE");
check("trạng thái lạ -> READY", R.info().state === "READY");
R.setAudioAmplitude(5);
check("amplitude kẹp [0,1] trên", R.info().amp === 1);
R.setAudioAmplitude(-2);
check("amplitude kẹp [0,1] dưới", R.info().amp === 0);
R.setInCall(1);
check("setInCall coerce boolean", R.info().inCall === true);

R.activate(true);
check("activate bật lớp nhìn", R.isActive() && H.isActive() && host.classList.contains("humanoid-on"));
check("activate bắn sự kiện joyce:humanoid-view", dispatched.some((e) => e.type === "joyce:humanoid-view" && e.detail && e.detail.on === true));
R.activate(false);
check("deactivate tắt lớp nhìn", !R.isActive() && !H.isActive());
R.activate(true); R.pause(); R.resume(); R.destroy();
check("pause/resume/destroy không ném khi không GL", true);

// ---------- 6) Nối dây dashboard (source checks, khuôn test_mat_trang) ----------
const IDX = fs.readFileSync(path.join(__dirname, "../../dashboard/index.html"), "utf8");
const V2 = fs.readFileSync(path.join(__dirname, "../../dashboard/brain-v2.js"), "utf8");
const HUD = fs.readFileSync(path.join(__dirname, "../../dashboard/hud.js"), "utf8");
const CSS = fs.readFileSync(path.join(__dirname, "../../dashboard/style.css"), "utf8");
const VI = JSON.parse(fs.readFileSync(path.join(__dirname, "../../dashboard/i18n/vi.json"), "utf8"));
const EN = JSON.parse(fs.readFileSync(path.join(__dirname, "../../dashboard/i18n/en.json"), "utf8"));

check("index.html: tab hd nhãn \"3D Joyce\" icon bot", /data-view="hd"[\s\S]{0,140}data-ic="bot"[\s\S]{0,80}>3D Joyce</.test(IDX));
check("index.html: nạp joyce-humanoid.js trước hud.js", IDX.indexOf("/static/joyce-humanoid.js") > 0 && IDX.indexOf("/static/joyce-humanoid.js") < IDX.indexOf("/static/hud.js"));
check("index.html: không còn nhãn \"3D View\"", IDX.indexOf(">3D View<") < 0);
check("brain-v2: click tab gọi setHumanoid(v === \"hd\")", /setHumanoid\(v === "hd"\)/.test(V2));
check("brain-v2: paint đọc humanoidOn + nghe joyce:humanoid-view", /humanoidOn/.test(V2) && /joyce:humanoid-view/.test(V2));
check("brain-v2: không còn gọi setHdMode", !/setHdMode/.test(V2));
check("hud.js: feedPlanet đẩy state/amp/call cho humanoid", /humanoid\.setJoyceState\(st\)/.test(HUD) && /humanoid\.setAudioAmplitude\(_lvl\)/.test(HUD) && /humanoid\.setInCall\(call\)/.test(HUD));
check("hud.js: mountHumanoid lazy + applyHum bật/tắt theo HUD", /function mountHumanoid/.test(HUD) && /var want = _humOn && active/.test(HUD));
check("hud.js: humanoid bật thì planet.pause() nhường GPU", /if \(want\) planet\.pause\(\)/.test(HUD));
check("hud.js: JoyceHud API lộ setHumanoid + humanoidOn", /setHumanoid: setHumanoid/.test(HUD) && /humanoidOn: function/.test(HUD));
check("hud.js: nhớ lựa chọn qua localStorage", /joyce\.hudHumanoid/.test(HUD));
check("i18n vi/en: bview.hd = \"3D Joyce\"", VI["bview.hd"] === "3D Joyce" && EN["bview.hd"] === "3D Joyce");
check("css: lớp humanoid-gl + hum-status + humanoid-on dim tinh cầu", /\.humanoid-gl/.test(CSS) && /\.hum-status/.test(CSS) && /humanoid-on \.planet-gl/.test(CSS));

console.log();
if (fails.length) { console.log(fails.length + " FAIL: " + fails.join(", ")); process.exit(1); }
console.log("TẤT CẢ PASS");
