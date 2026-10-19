// 3D Joyce (joyce-humanoid.js): pho tượng hạt thay lớp nhìn "3D View".
// Chạy: node tests/js/test_joyce_humanoid.js
//
// Kiểm ba tầng:
//   1) Hình người tham số hoá (sampleFigure - hàm thuần, không cần GL): đủ hạt,
//      đúng bố cục đầu/cổ/vai, lõi vàng cam kind=1 trong đầu, bụi mờ kind=2.
//   2) API vòng đời (create/mount/setJoyceState/setAudioAmplitude/activate) với
//      DOM giả - canvas getContext trả null (máy không có WebGL2) phải chịu được:
//      dataset.quality="nogl", không ném, activate/pause/destroy vẫn gọi được.
//   3) Đường render APEX (apex-humanoid.js, global JoyceHumanoidApex): renderer
//      tham chiếu được ưu tiên khi có sẵn; ctor nổ / assets fail -> rơi về
//      procedural; setJoyceState map sang plate-state, setAudioAmplitude -> setLevel.
//   4) Nối dây bằng source (khuôn test_mat_trang): tab đổi tên 3D Joyce, script
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

let head = 0, sho = 0, chest = 0, inBox = true;
for (let i = 0; i < NB; i++) {
  const x = fig.pos[i * 3], y = fig.pos[i * 3 + 1], z = fig.pos[i * 3 + 2];
  if (Math.abs(x) > 0.65 || y > 0.72 || y < -0.5 || Math.abs(z) > 0.3) inBox = false;
  if (y > 0.45) head++;
  if (Math.abs(x) > 0.3 && y < 0.15) sho++;
  if (y < -0.25) chest++;
}
check("thân nằm trong hộp pho tượng (đầu ~0.64, vai rộng ~0.5)", inBox);
check("có khối đầu (hạt trên y>0.45)", head > NB * 0.10, head + " hạt");
check("có thanh vai (hạt |x|>0.3 dưới cổ)", sho > NB * 0.08, sho + " hạt");
check("có lồng ngực (hạt dưới y<-0.25, không phải đĩa bay)", chest > NB * 0.08, chest + " hạt");

let coreOK = true, moteOK = true, coreInHead = 0, spinePts = 0, chestNode = 0;
for (let i = NB; i < NB + NC; i++) {
  if (fig.kind[i] !== 1) coreOK = false;
  const x = fig.pos[i * 3], y = fig.pos[i * 3 + 1];
  if (Math.abs(y - 0.46) < 0.12 && Math.abs(x) < 0.1) coreInHead++;      // cụm não
  if (Math.abs(x) < 0.05 && y > 0.0 && y < 0.42) spinePts++;             // sống lưng
  if (y < -0.02 && y > -0.16) chestNode++;                               // nốt ngực
}
for (let i = NB + NC; i < fig.n; i++) {
  if (fig.kind[i] !== 2) moteOK = false;
}
// Lõi vàng = não (~45%) + sống lưng (~30%) + nốt ngực (~25%) - đúng ảnh mẫu:
// não sáng trong đầu, cột vàng chạy cổ xuống ngực.
check("lõi kind=1: cụm não trong đầu", coreOK && coreInHead > NC * 0.35, coreInHead + "/" + NC);
check("lõi kind=1: sống lưng cổ-ngực", spinePts > NC * 0.2, spinePts + " hạt");
check("lõi kind=1: nốt ngực", chestNode > NC * 0.15, chestNode + " hạt");
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

// ---------- 4b) mapState sang plate-state của APEX ----------
check("mapState tồn tại", typeof H.mapState === "function");
check("mapState: LISTENING->listening, SPEAKING->speaking, THINKING->thinking", H.mapState("LISTENING") === "listening" && H.mapState("speaking") === "speaking" && H.mapState("THINKING") === "thinking");
check("mapState: READY/CONNECTING->idle, ERROR->error, INTERRUPTING->interrupting", H.mapState("READY") === "idle" && H.mapState("CONNECTING") === "idle" && H.mapState("ERROR") === "error" && H.mapState("INTERRUPTING") === "interrupting");
check("mapState: trạng thái lạ -> idle", H.mapState("BOGUS") === "idle" && H.mapState() === "idle");

// ---------- 4) Profiles ----------
check("4 hồ sơ chất lượng", Object.keys(H.PROFILES).sort().join(",") === "balanced,high,reduced,safe");
check("high nhiều hạt hơn safe", H.PROFILES.high.body > H.PROFILES.safe.body);
check("safe tắt twinkle, high bật", H.PROFILES.safe.twinkle === 0 && H.PROFILES.high.twinkle === 1);

// ---------- 5) Vòng đời không GL ----------
const host = el();
const R = H.create({});
check("create trả instance đủ API", ["mount","resize","setJoyceState","setAudioAmplitude","setInCall","pause","resume","activate","destroy","info","setQuality","isActive"].every((k) => typeof R[k] === "function"));
R.mount(host);
check("mount gắn lớp bọc .hum-layer vào stage", host.children.length === 1 && host.children[0].className === "hum-layer");
check("layer chứa canvas + nhãn trạng thái (fallback procedural)", host.children[0].children.length === 2 && host.children[0].children[0].className === "humanoid-gl" && host.children[0].children[1].className === "hum-status");
check("không WebGL2 -> dataset.quality=\"nogl\", không ném", host.dataset.quality === "nogl");
check("không có JoyceHumanoidApex -> mode procedural", host.dataset.mode === "procedural" && R.info().mode === "procedural");
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

// ---------- 5b) Đường render APEX (JoyceHumanoidApex stub) ----------
// Renderer APEX được ưu tiên khi global JoyceHumanoidApex có mặt: mount dựng
// instance trong .hum-layer, activate->enter, deactivate->pause, state/level
// được chuyển tiếp; destroy->dispose. Các đường hỏng phải rơi về procedural.
(async function apexSection() {
  const tick = () => new Promise((r) => setImmediate(r));
  function fakeApex(behavior) {
    const calls = { opts: null, enter: 0, pause: 0, resume: 0, dispose: 0, states: [], levels: [] };
    global.window.JoyceHumanoidApex = function (hostEl, opts) {
      calls.opts = opts;
      const self = this;
      self.loaded = false;
      self.root = el(); hostEl.appendChild(self.root);
      self.ready = Promise.resolve().then(() => { self.loaded = behavior !== "fail"; });
      ["enter", "pause", "resume", "dispose"].forEach((m) => { self[m] = () => { calls[m]++; }; });
      self.setState = (s) => { calls.states.push(s); };
      self.setLevel = (v) => { calls.levels.push(v); };
    };
    return calls;
  }
  // a) APEX khoẻ -> mode apex, state/level/enter/pause/dispose chuyển tiếp đúng.
  let calls = fakeApex("ok");
  const hostA = el(), RA = H.create({});
  RA.activate(true);                 // chọn tab trước khi mount (want persist)
  RA.mount(hostA);
  check("apex: mount dựng .hum-layer chứa root .jh của Apex", hostA.children.length === 1 && hostA.children[0].className === "hum-layer" && hostA.children[0].children.length === 1);
  check("apex: options assetsBase/controls/demo/autoStart đúng hợp đồng", calls.opts && calls.opts.assetsBase === "/static/humanoid/" && calls.opts.controls === false && calls.opts.demo === false && calls.opts.autoStart === false);
  await tick(); await tick();
  check("apex: mode=\"apex\" sau khi ready+loaded", hostA.dataset.mode === "apex" && RA.info().mode === "apex");
  check("apex: activate trước load -> enter() được gọi khi ready", calls.enter === 1);
  RA.setJoyceState("SPEAKING"); RA.setAudioAmplitude(0.7);
  check("apex: setJoyceState -> setState(plate), setAudioAmplitude -> setLevel", calls.states.indexOf("speaking") >= 0 && calls.levels.indexOf(0.7) >= 0);
  RA.activate(false);
  check("apex: deactivate -> pause()", calls.pause === 1);
  RA.activate(true);
  check("apex: re-activate -> enter() lại (replay lắp ráp)", calls.enter === 2);
  RA.destroy();
  check("apex: destroy -> dispose()", calls.dispose === 1);

  // b) Ctor nổ -> rơi về procedural ngay trong mount.
  global.window.JoyceHumanoidApex = function () { throw new Error("no apex"); };
  const hostB = el(), RB = H.create({});
  RB.mount(hostB);
  check("apex ctor nổ -> fallback procedural (canvas trong layer)", hostB.dataset.mode === "procedural" && hostB.children[0].children[0].className === "humanoid-gl");
  RB.destroy();

  // c) Assets hỏng (ready nhưng loaded=false) -> dọn apex rồi fallback.
  calls = fakeApex("fail");
  const hostC = el(), RC = H.create({});
  RC.mount(hostC);
  await tick(); await tick();
  check("apex assets fail -> dispose + fallback procedural", calls.dispose === 1 && hostC.dataset.mode === "procedural" && RC.info().mode === "procedural");
  RC.activate(true);
  check("fallback procedural vẫn activate được", RC.isActive() === true);
  RC.destroy();

  delete global.window.JoyceHumanoidApex;
  finish();
})().catch((e) => { console.log("FAIL apex section thả ngoại lệ: " + (e && e.message)); fails.push("apex section"); finish(); });

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

// ---------- 7) Tích hợp APEX trên đĩa (source checks) ----------
const APEX = fs.readFileSync(path.join(__dirname, "../../dashboard/apex-humanoid.js"), "utf8");
const HCSS = fs.readFileSync(path.join(__dirname, "../../dashboard/humanoid.css"), "utf8");
const GI = fs.readFileSync(path.join(__dirname, "../../.gitignore"), "utf8");
check("index.html: nạp apex-humanoid.js trước joyce-humanoid.js", IDX.indexOf("/static/apex-humanoid.js") > 0 && IDX.indexOf("/static/apex-humanoid.js") < IDX.indexOf("/static/joyce-humanoid.js"));
check("index.html: link humanoid.css", /\/static\/humanoid\.css/.test(IDX));
check("apex-humanoid.js: export global JoyceHumanoidApex", /global\.JoyceHumanoidApex\s*=/.test(APEX));
check("apex-humanoid.js: KHÔNG đè global JoyceHumanoid", !/global\.JoyceHumanoid\s*=/.test(APEX));
check("apex-humanoid.js: assetsBase mặc định ./assets/ (wrapper ghi đè /static/humanoid/)", /assetsBase\|\|'\.\/assets\/'/.test(APEX));
check("apex-humanoid.js: class JoyceHumanoid có API enter/setState/setLevel/pause/resume/dispose", ["enter", "setState", "setLevel", "pause", "resume", "dispose"].every((m) => new RegExp("\\n\\s{4}" + m + "\\(").test(APEX)));
// Camera tay đã chuyển sang bộ joyce-hands/ (Worker, xem test_joyce_hands.js): avatar chỉ giữ nút mở.
check("apex-humanoid.js: camera tay nằm ở joyce-hands/, avatar chỉ gọi onGestureRequest", !/toggleHands|detectForVideo|jh-cam/.test(APEX) && /onGestureRequest/.test(APEX));
check("apex-humanoid.js: parallax tilt theo attention trong shader", /q\.y-\.5\)\*attention\.x\*/.test(APEX));
// Quay đầu giả-3D: yaw uniform, nén ngang foreshorten, vùng mặt trượt hơn viền.
check("apex-humanoid.js: yaw uniform + foreshorten ngang trong shader", /uniform float yaw/.test(APEX) && /cos\(turn\*\.42\)/.test(APEX));
check("apex-humanoid.js: vùng mặt trượt nhiều hơn viền khi quay", /\.012\+\.038\*inner/.test(APEX));
check("apex-humanoid.js: yaw bám con trỏ/bàn tay + sway idle", /targetYaw=clamp\(this\.pointer\.x\*\.6/.test(APEX));
check("apex-humanoid.js: lớp hạt xoay cùng góc yaw", /dx\/fw-turn/.test(APEX));
check("apex-humanoid.js: hạt + lõi miệng nhịp theo tiếng", /speakBoost/.test(APEX) && /sin\(clock\*7\./.test(APEX));
check("apex-humanoid.js: ripple nhịp từ miệng khi nói", /level>\.48.*_beatAt/.test(APEX));
check("humanoid.css: đã gỡ rule demo-host html,body + #joyce-humanoid", !/html,body\{/.test(HCSS) && !/#joyce-humanoid\{/.test(HCSS));
check("humanoid.css: giữ scoped .jh + style .jh-cam", /\.jh\{/.test(HCSS) && /\.jh-cam\{/.test(HCSS));
check("style.css: có rule .hum-layer + ẩn holo-screen khi 3D Joyce", /\.hum-layer/.test(CSS) && /hum-mode \.holo-screen/.test(CSS));
check(".gitignore chặn dashboard/humanoid/ (artwork license chưa xác minh)", /^dashboard\/humanoid\//m.test(GI));
const ADIR = path.join(__dirname, "../../dashboard/humanoid");
if (fs.existsSync(ADIR)) {
  const need = ["apex-idle-v1.webp", "apex-listening-v1.webp", "apex-thinking-v1.webp", "apex-speaking-v1.webp", "apex-speaking-strong-v1.webp", "backdrop-v1.webp", "apex-assembly-25-v1.webp", "apex-assembly-60-v1.webp"];
  let wOK = true;
  for (const f of need) { const p = path.join(ADIR, f); if (!fs.existsSync(p)) { wOK = false; break; } const b = fs.readFileSync(p); if (b.toString("ascii", 0, 4) !== "RIFF" || b.toString("ascii", 8, 12) !== "WEBP") wOK = false; }
  check("assets APEX đủ 8 plate WebP hợp lệ trong dashboard/humanoid/", wOK);
  const mp = ["mediapipe/vision_bundle.mjs", "mediapipe/wasm/vision_wasm_internal.wasm", "mediapipe/wasm/vision_wasm_nosimd_internal.wasm", "hand_landmarker.task"];
  check("mediapipe hand-tracking đủ bundle + wasm + model", mp.every((f) => { const p = path.join(ADIR, f); return fs.existsSync(p) && fs.statSync(p).size > 50000; }));
} else {
  console.log("info  dashboard/humanoid/ vắng trên máy này -> renderer sẽ tự rơi về procedural (đúng thiết kế)");
}

// ---------- 8) Cảnh mở đầu: hạt lượng tử ghép thành hình (1.3.23) ----------
const QSRC = fs.readFileSync(path.join(__dirname, '../../dashboard/joyce-quantum.js'), 'utf8');
const Q = require(path.join(__dirname, '../../dashboard/joyce-quantum.js'));
const WRAP = fs.readFileSync(path.join(__dirname, '../../dashboard/joyce-humanoid.js'), 'utf8');
check('index.html: nạp joyce-quantum.js giữa apex-humanoid.js và joyce-humanoid.js', IDX.indexOf('/static/apex-humanoid.js') < IDX.indexOf('/static/joyce-quantum.js') && IDX.indexOf('/static/joyce-quantum.js') < IDX.indexOf('/static/joyce-humanoid.js'));
check('quantum: có chế độ introOnly (nền trong suốt, không nút, bỏ núi)', QSRC.includes('options.introOnly === true') && QSRC.includes('this.intro ? 0.0 : 1.0') && QSRC.includes('scene.counts.land'));
check('quantum: KHÔNG nạp file ảnh nào', !QSRC.includes('new Image('));
check('wrapper: mở lớp nhìn chạy cảnh hạt rồi mới bật hình gốc', WRAP.includes('function startIntro(onApex)') && WRAP.includes('startIntro(enterApex)') && WRAP.includes('new window.JoyceQuantumIntro('));
check('wrapper: hạt lấy khuôn từ CHÍNH ảnh nhân vật (khớp hình cuối)', WRAP.includes('image: apex && apex.images && apex.images.idle') && WRAP.includes('aspect: apex && apex.aspect'));
const img = { data: new Uint8ClampedArray(4 * 10 * 10) };
for (let i = 0; i < 100; i++) { const on = (i % 10) >= 3 && (i % 10) < 7; img.data[i * 4] = on ? 30 : 0; img.data[i * 4 + 1] = on ? 220 : 0; img.data[i * 4 + 2] = on ? 255 : 0; img.data[i * 4 + 3] = 255; }
const smp = Q.sampleImageData(img.data, 10, 10, 1000);
let inBand = true; for (let k = 0; k < smp.n; k++) { const u = smp.uv[k * 2]; if (u < 0.3 || u > 0.7) inBand = false; }
check('sampleImageData: chỉ lấy điểm sáng, đích nằm đúng vùng sáng của ảnh, giữ màu', smp.n > 0 && inBand && smp.col[1] > 0.8);
check('sampleImageData: tôn trọng trần số hạt', Q.sampleImageData(img.data, 10, 10, 5).n === 5);
check('intro dùng cùng phép đặt khung với renderer ảnh (figureRect)', QSRC.includes('Math.min(h * 1.01, w * 1.6)'));
check('wrapper: rời lớp nhìn / huỷ thì dọn cảnh hạt', WRAP.includes('closeHands(); stopIntro();') && /stopIntro\(\);\s*if \(apex\) \{ try \{ apex\.dispose/.test(WRAP));
check('wrapper: có cảnh hạt thì hình gốc hiện nhanh (không lắp ráp lần hai)', WRAP.includes('assemblyDuration: introAvailable() ? 1.4'));
check('wrapper: giảm chuyển động của hệ điều hành thì bỏ cảnh hạt', WRAP.includes('JoyceQuantumIntro && !reduced'));
const sc = Q.buildScene(Q.BUDGET.safe);
check('quantum: buildScene chạy được, đủ số hạt', sc.n === Object.values(Q.BUDGET.safe).reduce((a, c) => a + c, 0));

function finish() {
  console.log();
  if (fails.length) { console.log(fails.length + " FAIL: " + fails.join(", ")); process.exit(1); }
  console.log("TẤT CẢ PASS");
}
