/* H2O ALIEN INTELLIGENCE PLANET: renderer mới của lớp "Lõi nước" (dashboard/brain-planet.js).

       node tests/js/test_tinh_cau_alien.js

   Chủ repo muốn (2026-10-05) thay quả cầu nước 2D bằng một tinh cầu 3D. Duyệt xong thiết kế,
   chủ yêu cầu GỠ HẲN quả cầu 2D cũ; cờ joyce_alien_intelligence_planet_v1 giờ chỉ còn ép bản
   Canvas 2D nhẹ (không shader). Thêm theo yêu cầu cùng ngày: H2O Legacy là MẶT TRỜI chiếu
   sáng tinh cầu, một dự án là MẶT TRĂNG có pha đúng ngày thật, bấm cầu gọi thì khung
   hologram (avatar Joyce hoặc ảnh nhân viên) dựng lên và tinh cầu hạ xuống làm nền.
   Các điều kiện được kiểm ở đây:
     - Cờ mặc định BẬT, "0" là bản nhẹ Canvas 2D; quả cầu 2D cũ không còn.
     - Renderer có đủ interface BrainRenderer (mount/resize/setJoyceState/...).
     - Trạng thái Joyce lấy từ runtime THẬT (lớp của #orbState, nút gọi), không timeout giả.
     - Registry dự án đi từ server: client không hard-code địa chỉ app nào.
     - Có đường lui khi WebGL lỗi, tôn trọng prefers-reduced-motion, dọn sạch khi huỷ.
     - Khung sáng vuông sau quả cầu cũ (gradient bị fillRect cắt theo mép canvas) không quay lại.
   Kiểm trên SOURCE thật, cộng chạy thử các hàm thuần trong vm. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const HUD = D("hud.js");
const HTML = D("index.html");
const STYLE = D("style.css");
const APP = D("app.js");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}
const CODE = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'])\/\/[^\n]*/g, "$1");

// ---- 1. Nạp đúng thứ tự, có cờ ----
const iP = HTML.indexOf("/static/brain-planet.js"), iH = HTML.indexOf("/static/hud.js");
check("index.html nạp brain-planet.js", iP > 0);
check("brain-planet.js nạp TRƯỚC hud.js", iP > 0 && iP < iH);
check("tên cờ đúng joyce_alien_intelligence_planet_v1", PLANET.indexOf('"joyce_alien_intelligence_planet_v1"') > 0);

// ---- 2. Chạy renderer trong vm (không DOM): cờ + interface ----
function sandbox(store, search) {
  const win = {
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    devicePixelRatio: 1,
    addEventListener() {}, dispatchEvent() {},
  };
  const ctx = {
    window: win, document: { documentElement: { getAttribute: () => null }, createElement: () => ({ getContext: () => null }) },
    navigator: { deviceMemory: 8, hardwareConcurrency: 8 },
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } },
    location: { search: search || "" }, URLSearchParams, performance: { now: () => 0 },
    requestAnimationFrame: () => 1, cancelAnimationFrame() {}, setTimeout, clearTimeout, console, Event: function (n) { this.type = n; },
  };
  vm.createContext(ctx);
  vm.runInContext(PLANET, ctx);
  return ctx;
}
let sb = sandbox({});
const JP = sb.window.JoycePlanet;
check("window.JoycePlanet có mặt", !!JP);
check("cờ mặc định BẬT khi chưa đặt", JP.enabled() === true);
sb = sandbox({ joyce_alien_intelligence_planet_v1: "0" });
check('cờ "0" = TẮT (về quả cầu cũ)', sb.window.JoycePlanet.enabled() === false);
sb = sandbox({}, "?joyce_alien_intelligence_planet_v1=0");
check("?joyce_alien_intelligence_planet_v1=0 trên URL tắt được và ghi nhớ", sb.window.JoycePlanet.enabled() === false
  && sb.localStorage.getItem("joyce_alien_intelligence_planet_v1") === "0");

const r = JP.create({});
["mount", "resize", "setJoyceState", "setAudioAmplitude", "setProjects", "setQuality", "pause", "resume", "destroy", "setInCall"]
  .forEach((m) => check("BrainRenderer." + m + " là hàm", typeof r[m] === "function"));
r.setJoyceState("thinking");
check("setJoyceState không phân biệt hoa thường", r.state() === "THINKING");
r.setJoyceState("khong-co");
check("trạng thái lạ -> READY, không vỡ", r.state() === "READY");
check("đủ 8 trạng thái của state machine",
  ["READY", "CONNECTING", "LISTENING", "THINKING", "SPEAKING", "INTERRUPTING", "RECONNECTING", "ERROR"]
    .every((s) => JP.STATES.indexOf(s) >= 0));
let threw = false;
try { r.setQuality("balanced"); r.setProjects([{ id: "a", name: "A", status: "online" }]); r.destroy(); r.destroy(); }
catch (e) { threw = e; }
check("setQuality/setProjects trước mount + destroy 2 lần không ném lỗi", !threw);

// ---- 3. Hiệu năng + an toàn trong renderer ----
const PC = CODE(PLANET);
check("có shader WebGL2 + đường lui Canvas 2D (drawSafePlanet)", /getContext\("webgl2"/.test(PC) && /function drawSafePlanet/.test(PC));
check("DPR tối đa 2", /Math\.min\(dpr, profile === "high" \? 2 : 1\.25\)/.test(PC) && /dprOv = Math\.min\(dpr, 2\)/.test(PC));
check("FPS < 30 thì hạ chất lượng", /1 \/ avg < 30/.test(PC));
check("ẩn tab thì dừng vẽ", /visibilitychange/.test(PC) && /document\.hidden\) stopLoop\(\)/.test(PC));
check("xử lý webglcontextlost (preventDefault + về safe)", /webglcontextlost/.test(PC) && /function onLost\(e\) \{\s*e\.preventDefault\(\)/.test(PC));
check("tôn trọng prefers-reduced-motion", /prefers-reduced-motion: reduce/.test(PC) && /return "reduced"/.test(PC));
check("destroy: huỷ RAF, gỡ listener, ngắt ResizeObserver, thả context", (function () {
  const s = PC.slice(PC.indexOf("R.destroy = function"), PC.indexOf("R.setInCall"));
  return /stopLoop\(\)/.test(s) && /removeEventListener/.test(s) && /ro\.disconnect\(\)/.test(s) && /loseContext\(\)/.test(s);
})());
// 0.65.35: bản đồ Việt Nam là texture DỰNG TẠI CHỖ từ dữ liệu nhúng (vn-geo.js) - vẫn cấm
// ảnh/tài nguyên ngoài; mọi texImage2D phải nạp mảng điểm ảnh trong bộ nhớ (u8), không nạp ảnh.
check("không tải texture/ảnh ngoài trong renderer",
  !/new Image\(|https?:\/\//.test(PC) &&
  (PC.match(/texImage2D\([^;]*\)/g) || []).every((x) => /, u8\)$/.test(x)));
check("bấm cầu chờ nhịp double-click (không gọi rồi cúp ngay)", /clickTimer = setTimeout/.test(PC) && /function onDbl\(\) \{\s*clearTimeout\(clickTimer\)/.test(PC));
// 0.65.35: zoom 4 tầng (Ngân Hà -> cận cảnh Hải Phòng), chủ duyệt; vẫn phải KẸP trong trần cố định.
check("zoom bị kẹp trong phạm vi an toàn",
  /clamp\(cam\.tzoom \* [^;]+, ZMIN, ZMAX\)/.test(PC) && /var ZMIN = 0\.32, ZMAX = 12;/.test(PC));
check("vòng lặp đã dừng thì khung xếp hàng không tự đặt lại RAF", /if \(destroyed \|\| \(!once && !running\)\) return;/.test(PC));

// ---- 4. KHÔNG còn khung sáng vuông ----
// Quả cầu cũ phủ gradient khí quyển bằng fillRect(0,0,W,H) trên canvas vuông. Bản mới vẽ khí
// quyển trong shader trên canvas phủ KÍN khoang, còn bản safe vẽ bằng cung tròn.
const SAFE = PC.slice(PC.indexOf("function drawSafePlanet"), PC.indexOf("function drawRings"));
check("CANARY: khí quyển bản safe không fillRect cả canvas", SAFE.indexOf("fillRect(0, 0") === -1);
check("canvas tinh cầu phủ kín khoang não", /#planetStage \{ position: absolute; inset: 0;/.test(STYLE));
check("CANARY: canvas #hudOrb vuông cũ không còn ở đâu", HUD.indexOf("hudOrb") === -1 && STYLE.indexOf("#hudOrb {") === -1);

// ---- 5. hud.js: rollback + state thật ----
const HC = CODE(HUD);
check("quả cầu 2D cũ (drawOrb) đã gỡ theo yêu cầu chủ", !/function drawOrb\(/.test(HC) && !/_dotPos|_satLabel/.test(HC));
check("cờ tắt = bản Canvas 2D nhẹ (safe), không phải màn trống", /if \(!flagOn\(\)\) return "safe";/.test(PC));
check("đổi cờ lúc chạy: gỡ/gắn một bước", /joyce:planet-flag/.test(HC) && /unmountPlanet\(\)/.test(HC));
check("ẩn lớp Lõi nước thì tạm dừng tinh cầu", /if \(planet\) planet\.pause\(\);/.test(HC));
check("không có setTimeout giả lập trạng thái trong feedPlanet",
  !/setTimeout/.test(HC.slice(HC.indexOf("function feedPlanet"), HC.indexOf("function planetInsets"))));
check("app.js đẩy trạng thái thanh gọi ra cho tinh cầu", /window\.__joyceCallState = st;/.test(APP));

function extract(src, name) {
  const i = src.indexOf("function " + name + "(");
  let depth = 0, j = src.indexOf("{", i);
  for (let k = j; k < src.length; k++) {
    if (src[k] === "{") depth++;
    else if (src[k] === "}" && --depth === 0) return src.slice(i, k + 1);
  }
  return "";
}
// joyceState đọc lớp #orbState - đúng chỗ capNhatOrb() ghi từ turn.state
const fsrc = extract(HUD, "inCallNow") + "\n" + extract(HUD, "joyceState") + "\nmodule.exports = joyceState;";
function stateFor(cls, inCall, callState) {
  const mod = { exports: null };
  const ctx = {
    module: mod,
    window: { __joyceCallState: callState },
    document: { getElementById: (id) => id === "orbState" ? { className: "orb-state " + cls }
      : id === "voiceBtn" ? { classList: { contains: (c) => c === "in-call" && !!inCall } } : null },
  };
  vm.createContext(ctx); vm.runInContext(fsrc, ctx);
  return mod.exports();
}
check("orb rỗng -> READY", stateFor("", false) === "READY");
check("listening -> LISTENING", stateFor("listening", true) === "LISTENING");
check("thinking -> THINKING", stateFor("thinking", false) === "THINKING");
check("speaking -> SPEAKING", stateFor("speaking", true) === "SPEAKING");
check("paused (bị ngắt lời) -> INTERRUPTING", stateFor("paused", true) === "INTERRUPTING");
check("reconnecting -> RECONNECTING", stateFor("reconnecting", true) === "RECONNECTING");
check("error -> ERROR", stateFor("error", false) === "ERROR");
check("đang gọi + thanh gọi connecting -> CONNECTING", stateFor("", true, "connecting") === "CONNECTING");
check("connecting cũ còn sót nhưng đã cúp máy -> READY", stateFor("", false, "connecting") === "READY");

// projHealth: online / degraded / offline / unauthorized từ kết quả ping thật
const phSrc = extract(HUD, "projHealth") + "\nmodule.exports = projHealth;";
const pm = { exports: null }; const pctx = { module: pm }; vm.createContext(pctx); vm.runInContext(phSrc, pctx);
const ph = pm.exports;
check("200 nhanh -> online", ph({ id: "a", ten: "A", url: "u", ok: true, status: 200, ms: 300 }).status === "online");
check("lên nhưng API dữ liệu chết -> degraded", ph({ id: "a", ok: true, status: 200, ms: 300, api_ok: false }).status === "degraded");
check("lên nhưng chậm > 4s -> degraded", ph({ id: "a", ok: true, status: 200, ms: 5200 }).status === "degraded");
check("401/403 -> unauthorized", ph({ id: "a", ok: false, status: 403 }).status === "unauthorized");
check("500 / không trả lời -> offline", ph({ id: "a", ok: false, status: 0 }).status === "offline");
check("URL lấy nguyên từ server", ph({ id: "a", ok: true, status: 200, url: "https://x.example" }).url === "https://x.example");

// ---- 6. Không hard-code URL dự án; bấm vệ tinh mở ngăn kéo ngữ cảnh trước ----
check("brain-planet.js không chứa địa chỉ http nào", !/https?:\/\//.test(PC));
check("bấm vệ tinh -> openCtx (không window.open thẳng)", /onSatelliteClick: function \(p\) \{ openCtx\(p\); \}/.test(HC));
check("ngăn kéo có nút Kiểm tra lại gọi /h2o-projects/check", /fetch\("\/h2o-projects\/check"/.test(HC.slice(HC.indexOf("function recheck"))));
check("có nút DOM gọi Joyce ngoài canvas", /id="planetCallBtn"/.test(HUD));

// ---- 6b. Mặt trời / mặt trăng ----
let sb2 = sandbox({});
const JP2 = sb2.window.JoycePlanet;
function phaseAt(iso) { return JP2.moonPhase(new Date(iso)); }
check("trăng tròn 23/4/2024 23:49 UTC", JP2.moonPhaseKey(phaseAt("2024-04-23T23:49:00Z").phase) === "full");
check("trăng mới hôm nhật thực 8/4/2024", JP2.moonPhaseKey(phaseAt("2024-04-08T18:21:00Z").phase) === "new");
check("trăng tròn 26/9/2026", JP2.moonPhaseKey(phaseAt("2026-09-26T16:49:00Z").phase) === "full");
check("5/10/2026 là trăng khuyết cuối tháng", JP2.moonPhaseKey(phaseAt("2026-10-05T14:00:00Z").phase) === "wan_cres");
check("độ sáng trăng tròn ~100%, trăng mới ~0%",
  phaseAt("2024-04-23T23:49:00Z").illum > 0.99 && phaseAt("2024-04-08T18:21:00Z").illum < 0.01);
check("mỗi pha có khoá i18n vi + en", Object.keys(JP2.MOON_KEYS).every((k) => VI[JP2.MOON_KEYS[k]] && EN[JP2.MOON_KEYS[k]]));
// 0.65.35: Mặt Trời theo GIỜ THẬT - cùng MỘT vector (Lv) vừa chiếu sáng shader (uL) vừa đặt
// đĩa Mặt Trời trên màn hình, nên ánh sáng và vị trí đĩa không bao giờ lệch nhau.
check("hướng sáng của tinh cầu lấy từ vị trí mặt trời",
  /vec3 L=normalize\(uL\)/.test(PC) && /var Lv = toView\(Gm, sunG\);\s*geo\.L = Lv;/.test(PC) &&
  /gl\.uniform3f\(u\.uL, Lv\[0\], Lv\[1\], Lv\[2\]\)/.test(PC));
check("có chùm sáng mặt trời chiếu xuống tinh cầu", /float beam=/.test(PC) && /sunC\+=uSunC\*beam/.test(PC));
check("mặt trăng sau hành tinh bị khoét che thật", /c\.arc\(geo\.cx, geo\.cy, geo\.R, 0, 6\.2832, true\); c\.clip\(\)/.test(PC));
// 0.65.35: phần sáng của trăng luôn quay về phía Mặt Trời thật (đĩa xoay theo hướng nắng);
// khi nắng chiếu từ phải sang (lúc chiều tối, trăng đầu tháng ở bán cầu Bắc) thì sáng bên phải.
// 0.65.38: pha VẼ có thể do chủ tự chỉnh ở tab Quả tinh cầu (moonShownPhase), mặc định vẫn là
// pha thật của ngày (moonPh.phase); hướng sáng vẫn quay về Mặt Trời thật.
check("trăng đầu tháng sáng bên phải (bán cầu Bắc)",
  /var k = Math\.cos\(2 \* Math\.PI \* p\), side = 1;/.test(PC) &&
  /function moonShownPhase\(\) \{ return LD\.moonP != null \? LD\.moonP : moonPh\.phase; \}/.test(PC) &&
  /drawMoonDisc\(c, pt\.x, pt\.y, r, moonShownPhase\(\), col, front \? 1 : 0\.75, Math\.atan2\(-Lv\[1\], Lv\[0\]\)/.test(PC));

// vai thiên thể từ registry: Legacy = mặt trời, mặt trăng ghim hoặc tự đổi theo tuần trăng
const roleSrc = ["isSun", "moonPinned", "moonId", "projHealth", "healthList"].map((n) => extract(HUD, n)).join("\n") +
  "\nmodule.exports = healthList;";
function rolesWith(items, pin, lunation) {
  const mod = { exports: null };
  const ctx = { module: mod, D: { projItems: items }, MOON_KEY: "joyce.planetMoon",
    localStorage: { getItem: () => pin || null },
    window: { JoycePlanet: { moonPhase: () => ({ lunation: lunation || 0 }) } } };
  vm.createContext(ctx); vm.runInContext(roleSrc, ctx);
  const out = {};
  mod.exports().forEach((h) => { out[h.id] = h.role || ""; });
  return out;
}
const ITEMS = [{ id: "legacy", ten: "H2O Legacy", ok: true, status: 200 }, { id: "book", ten: "H2OBOOK", ok: true, status: 200 },
               { id: "video", ten: "H2OVIDEOEDIT", ok: true, status: 200 }];
let ro = rolesWith(ITEMS, "", 0);
check("H2O Legacy là mặt trời", ro.legacy === "sun");
check("không ghim: có đúng một mặt trăng, không phải Legacy",
  Object.values(ro).filter((v) => v === "moon").length === 1 && ro.legacy !== "moon");
check("không ghim: sang tuần trăng mới thì mặt trăng đổi dự án",
  JSON.stringify(rolesWith(ITEMS, "", 0)) !== JSON.stringify(rolesWith(ITEMS, "", 1)));
ro = rolesWith(ITEMS, "video", 0);
check("ghim mặt trăng = đúng dự án đã ghim, mọi tuần trăng", ro.video === "moon" && rolesWith(ITEMS, "video", 7).video === "moon");
check("ghim nhầm vào Legacy thì không cướp vai mặt trời", rolesWith(ITEMS, "legacy", 0).legacy === "sun");

// ---- 6c. Khung hologram khi gọi ----
check("đang gọi -> tinh cầu hạ xuống (callK trong layout)", /availH \* \(0\.47 \+ 0\.19 \* callK\)/.test(PC));
check("khung hologram có trong DOM của lớp Lõi nước", /id="holoScreen"/.test(HUD));
check("nút Tắt mic / Cúp máy mượn đúng nút của thanh gọi (không có đường gọi thứ hai)",
  /querySelector\("\.call-mute"\)/.test(HC) && /querySelector\("\.call-hangup"\)/.test(HC));
const perSrc = extract(HUD, "joyceFaceSrc") + "\n" + extract(HUD, "persona") + "\nmodule.exports = persona;";
function personaWith(staff) {
  const mod = { exports: null };
  const ctx = { module: mod, window: { __h2oStaff: staff }, encodeURIComponent };
  vm.createContext(ctx); vm.runInContext(perSrc, ctx);
  return mod.exports();
}
check("không phải nhân viên -> gương mặt Joyce", personaWith(null).staff === false && personaWith(null).name === "J O Y C E");
check("nhân viên chưa cài ảnh -> vẫn là Joyce", personaWith({ id: "st_a_abc123", ten: "A" }).staff === false);
const pst = personaWith({ id: "st_lan_abc123", ten: "Nguyễn Lan", avatar_v: 9 });
check("nhân viên đã cài ảnh -> ảnh hồ sơ của họ + tên",
  pst.staff === true && pst.name === "Nguyễn Lan" && pst.src === "/staff/avatar/st_lan_abc123?v=9");
check("tab Nhân viên có chỗ tải ảnh (admin + tự đổi)",
  /\/h2o-staff\/avatar/.test(D("console.js")) && /"\/staff\/avatar"/.test(D("console.js")));

// ---- 7. i18n đủ hai thứ tiếng ----
const keys = Object.keys(VI).filter((k) => k.indexOf("planet.") === 0);
check("có chuỗi planet.* tiếng Việt", keys.length >= 10);
check("mọi chuỗi planet.* có bản tiếng Anh", keys.every((k) => typeof EN[k] === "string" && EN[k]));
check("không em dash trong file mới", PLANET.indexOf("—") === -1);

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
