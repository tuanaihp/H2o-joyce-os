/* Giao diện tinh cầu tùy biến: Cài đặt -> Giao diện Joyce -> Quả tinh cầu (0.65.38).

       node tests/js/test_tinh_cau_tuy_bien.js

   Chủ repo yêu cầu 2026-10-07 một tab chỉnh giao diện quả tinh cầu: Mặt Trời mạnh/yếu + đổi
   màu, Mặt Trăng tròn/khuyết + sáng/mờ, concept màu bề mặt, mây mỏng/dày/u tối, công tắc mưa,
   sấm sét, gió mạnh, lốc xoáy, lõi rõ/mờ + sáng/yếu, dung nham phun trào. Điều kiện canh ở đây:
     - Bộ tham số MẶC ĐỊNH tái tạo đúng giao diện cũ (bảng màu "ocean" = hằng số trong shader).
     - Chuẩn hoá chặt: khoá lạ bỏ, số kẹp khoảng, màu chỉ "#rrggbb", bool phải là bool thật.
     - Một bộ tham số dùng chung: setLook ghi localStorage + bắn sự kiện, máy chủ thắng khi hoà.
     - Shader khai đủ uniform mới và renderer lấy được vị trí của chúng.
     - Trang Cài đặt có tab "appearance", ô xem trước được dọn khi rời trang, lưu qua
       /settings section=dashboard rồi đọc lại để báo thật.
   Kiểm trên SOURCE thật, cộng chạy các hàm thuần trong vm. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const CONSOLE = D("console.js");
const HUD = D("hud.js");
const CSS = D("console.css");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

const fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

function sandbox(store) {
  const events = [];
  const win = {
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    devicePixelRatio: 1, addEventListener() {}, dispatchEvent(e) { events.push(e.type); },
  };
  const ctx = {
    window: win, document: { documentElement: { getAttribute: () => null }, createElement: () => ({ getContext: () => null }) },
    navigator: { deviceMemory: 8, hardwareConcurrency: 8 },
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } },
    location: { search: "" }, URLSearchParams, performance: { now: () => 0 },
    requestAnimationFrame: () => 1, cancelAnimationFrame() {}, setTimeout, clearTimeout, console, Event: function (n) { this.type = n; },
  };
  vm.createContext(ctx);
  vm.runInContext(PLANET, ctx);
  ctx.events = events;
  return ctx;
}

// ---- 1. API + mặc định = giao diện cũ ----
let store = {};
let sb = sandbox(store);
const P = sb.window.JoycePlanet;
["normLook", "getLook", "setLook", "hydrateLook", "lookInfo"].forEach((f) => check("JoycePlanet." + f + " là hàm", typeof P[f] === "function"));
["LOOK_DEFAULT", "LOOK_NUM", "LOOK_BOOL", "LOOK_ENUM", "PALETTES", "SCENES"].forEach((k) => check("JoycePlanet." + k + " có mặt", P[k] && typeof P[k] === "object"));
const DEF = P.LOOK_DEFAULT;
check("mặc định: Mặt Trời 100%, màu vàng nắng cũ", DEF.sunPower === 1 && DEF.sunSize === 1 && DEF.sunColor === "#ffd46b");
check("mặc định: trăng theo lịch thật", DEF.moonMode === "auto" && DEF.moonGlow === 1 && DEF.moonSize === 1);
check("mặc định: concept Đại dương H2O", DEF.palette === "ocean" && DEF.surface === 1 && DEF.atmo === 1);
check("mặc định: mọi hiệu ứng TẮT, chỉ vành quỹ đạo bật",
  ["rain", "lightning", "wind", "tornado", "eruption"].every((k) => DEF[k] === false) && DEF.orbits === true);
check("mặc định: lõi 100%", DEF.coreVis === 1 && DEF.coreGlow === 1);
// độ phủ mây nền trước đây là hằng .16 trong shader; nay = clouds * 0.55 (0.3 -> 0.165)
check("mặc định: mây nền ~ hằng .16 cũ", Math.abs(DEF.clouds * 0.55 - 0.16) < 0.01 && /look\.clouds \* 0\.55/.test(PLANET));
const vec = (name) => {
  const m = PLANET.match(new RegExp(name + "=vec3\\(([^)]*)\\)"));
  return m ? m[1].split(",").map((x) => parseFloat(x.trim().replace(/\.$/, ""))) : null;
};
const near = (a, b) => a && b && a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) < 1e-3);
check("bảng màu ocean = đúng hằng OCEAN/CYAN/MINT của shader",
  near(P.PALETTES.ocean.sea, vec("OCEAN")) && near(P.PALETTES.ocean.rim, vec("CYAN")) && near(P.PALETTES.ocean.mint, vec("MINT")) &&
  near(P.PALETTES.ocean.deep, [0.01, 0.06, 0.2]));

// ---- 2. Chuẩn hoá ----
let n = P.normLook({ sunPower: 9, moonFull: -3, clouds: "0.75", coreVis: true, sunColor: "red", seaColor: "#ABCDEF",
  rain: "true", tornado: true, palette: "khong-co", moonMode: "manual", xau: "<script>" });
check("số vượt trần bị kẹp", n.sunPower === 2 && n.moonFull === 0);
check("số dạng chuỗi được nhận", n.clouds === 0.75);
check("bool không phải số (true -> giữ mặc định)", n.coreVis === 1);
check("màu sai định dạng bị bỏ, màu đúng về chữ thường", n.sunColor === "#ffd46b" && n.seaColor === "#abcdef");
check('bool phải là bool thật ("true" dạng chuỗi bị bỏ)', n.rain === false && n.tornado === true);
check("lựa chọn lạ về mặc định, lựa chọn đúng được giữ", n.palette === "ocean" && n.moonMode === "manual");
check("khoá lạ không lọt vào", !("xau" in n));
check("normLook(null) = mặc định", JSON.stringify(P.normLook(null)) === JSON.stringify(DEF));

// ---- 3. Một bộ tham số dùng chung + lưu tạm ----
P.setLook({ sunPower: 1.5, rain: true });
check("setLook gộp vào bộ hiện tại", P.getLook().sunPower === 1.5 && P.getLook().rain === true && P.getLook().palette === "ocean");
check("setLook ghi localStorage joyce.planetLook", JSON.parse(store["joyce.planetLook"]).sunPower === 1.5);
check("setLook bắn sự kiện joyce:planet-look", sb.events.indexOf("joyce:planet-look") >= 0);
P.setLook({ palette: "lava" }, { replace: true });
check("replace: khoá vắng về mặc định", P.getLook().palette === "lava" && P.getLook().sunPower === 1 && P.getLook().rain === false);
P.hydrateLook({ moonMode: "manual", moonFull: 0.5 });
check("hydrateLook (bản máy chủ) thay CẢ bộ", P.getLook().palette === "ocean" && P.getLook().moonMode === "manual");
const sb2 = sandbox(store);
check("mở lại trang: đọc lại bản nhớ tạm", sb2.window.JoycePlanet.getLook().moonFull === 0.5);
check("getLook trả BẢN SAO (sửa ngoài không lọt vào)", (() => { const L = P.getLook(); L.sunPower = 99; return P.getLook().sunPower !== 99; })());
const sb3 = sandbox({ "joyce.planetLook": "{hỏng" });
check("bản nhớ tạm hỏng -> mặc định, không vỡ", JSON.stringify(sb3.window.JoycePlanet.getLook()) === JSON.stringify(DEF));

// ---- 4. Giá trị suy ra ----
const phase = (full) => { P.setLook({ moonMode: "manual", moonFull: full }, { replace: true }); return P.lookInfo().moonP; };
check("trăng tự chỉnh: tròn = pha 0,5", Math.abs(phase(1) - 0.5) < 1e-9);
check("trăng tự chỉnh: bán nguyệt = pha 0,25", Math.abs(phase(0.5) - 0.25) < 1e-9);
check("trăng tự chỉnh: non = pha 0", Math.abs(phase(0)) < 1e-9);
P.setLook({}, { replace: true });
check("trăng theo lịch thật: không ép pha", P.lookInfo().moonP === null);
P.setLook({ palette: "custom", seaColor: "#ff0000", rimColor: "#00ff00" }, { replace: true });
const LI = P.lookInfo();
check("concept tự chọn lấy đúng màu biển + viền", near(LI.pal.sea, [1, 0, 0]) && near(LI.pal.rim, [0, 1, 0]));
P.setLook({}, { replace: true });

// ---- 5. Cảnh dựng sẵn hợp lệ ----
Object.keys(P.SCENES).forEach((id) => {
  const sc = P.SCENES[id], L = P.normLook(sc);
  check("cảnh " + id + ": mọi khoá + giá trị đều hợp lệ", Object.keys(sc).every((k) => k in DEF && L[k] === sc[k]));
});
check("có đủ cảnh bão, lốc xoáy, núi lửa, đêm trăng",
  P.SCENES.storm.lightning && P.SCENES.tornado.tornado && P.SCENES.volcano.eruption && P.SCENES.moon_night.moonMode === "manual");

// ---- 6. Shader + renderer ----
const UNI = ["uPa", "uPb", "uPc", "uPd", "uLk", "uMoonV", "uCl", "uTor", "uBolt", "uCo"];
check("shader khai đủ uniform mới", UNI.every((u) => new RegExp("uniform vec[34] " + u + ";").test(PLANET)));
const locList = PLANET.slice(PLANET.indexOf('["uRes", "uC"'), PLANET.indexOf(".forEach(function (k) { u[k] = gl.getUniformLocation"));
check("renderer lấy vị trí mọi uniform mới", UNI.every((u) => locList.indexOf('"' + u + '"') >= 0));
check("renderer nạp giá trị mọi uniform mới mỗi khung", UNI.every((u) => new RegExp("gl\\.uniform[34]f\\(u\\." + u + ",").test(PLANET)));
check("cột magma không còn dùng atan (vệt gãy ở ±π)", PLANET.indexOf("atan(prc.y,prc.x)") === -1);
check("mây trôi theo PHA gió tích luỹ (không giật khi bật gió)", /windT \+= dt \* \(1 \+ 7 \* fx\.wind\)/.test(PLANET) && /rY\(uCl\.z\*\.004\)/.test(PLANET));
["drawWind", "drawRain", "drawEruption", "drawHot", "drawTornado", "drawLightning"].forEach((f) =>
  check("có hiệu ứng " + f, new RegExp("function " + f + "\\(").test(PLANET)));
check("hiệu ứng vẽ trước vành + trăng phía trước (bị che đúng)",
  /drawMoon\(c, false, ddt\);\s*drawLookFx\(c, now, ddt\);\s*drawRings\(c, true\);/.test(PLANET));
check("Mặt Trời: tín hiệu sức khoẻ H2O Legacy vẫn đè lên màu tự chọn", /h\.c\[0\] \* 0\.7/.test(PLANET));
// 0.65.44: núi lửa không còn bắn hạt; dung nham chảy thành sông (số đoạn cố định, dựng một lần).
check("núi lửa: sông dung nham dựng một lần, không bắn hạt tung toé", /if \(!volc\.rivers\) volc\.rivers = buildRivers\(\);/.test(PLANET) && !/ventAcc/.test(PLANET));
check("ô xem trước: tuỳ chọn tắt nhãn, tooltip, lăn chuột",
  /if \(opts\.labels !== false\) drawLabels\(c\);/.test(PLANET) && /opts\.tips === false/.test(PLANET) && /if \(opts\.wheel === false && !e\.ctrlKey\) return;/.test(PLANET));
let threw = false;
try {
  const r = P.create({ labels: false, tips: false, wheel: false, dark: true });
  P.setLook({ rain: true, tornado: true, eruption: true, lightning: true });
  r.setProjects([{ id: "m", name: "", role: "moon", status: "online" }]);
  r.destroy(); r.destroy();
  P.setLook({}, { replace: true });
} catch (e) { threw = e; }
check("renderer tạo/huỷ với tuỳ chọn xem trước không ném lỗi", !threw);
const DES = PLANET.slice(PLANET.indexOf("R.destroy = function"), PLANET.indexOf("R.setInCall"));
check("destroy dọn mảng hạt của hiệu ứng", /cells = \[\]; splashes = \[\]; streaks = \[\]; bolts = \[\]; hot = \[\]; torn\.g = null; torn\.parts = \[\]/.test(DES));

// ---- 7. Trang Cài đặt ----
check("tab appearance có trong danh sách tab Cài đặt", /const tabs = \["general", "voice", "appearance", "pet", "usage", "updates"\];/.test(CONSOLE));
check("navigateTo nhận tab appearance", /\["general", "voice", "appearance", "pet", "usage", "updates"\]\.includes\(tab\)/.test(CONSOLE));
check("renderSettingsPage vẽ tab appearance", /tab === "appearance"\) await renderAppearancePage\(panel\)/.test(CONSOLE));
check("khung tab con (sau này thêm giao diện khác)", /const LOOK_SUBS = \{ planet: \{/.test(CONSOLE) && /role="tablist"/.test(CONSOLE.slice(CONSOLE.indexOf("async function renderAppearancePage"))));
const LP = CONSOLE.slice(CONSOLE.indexOf("async function renderPlanetLook"), CONSOLE.indexOf("async function renderSettingsPage"));
check("ô xem trước dọn qua _pageLeave + tự huỷ khi rời DOM", /_pageLeave = dung;/.test(LP) && /box\.isConnected/.test(LP) && /prev\.destroy\(\)/.test(LP));
check("lưu qua /settings section=dashboard khoá planet", /saveSetting\("dashboard", \{ planet: L \}\)/.test(LP));
check("lưu xong ĐỌC LẠI /settings để báo thật", /fetch\("\/settings", \{ cache: "no-store" \}\)/.test(LP) && /look\.saved_local/.test(LP));
check("mở tab: bản máy chủ thắng bản nhớ tạm", /P\.hydrateLook\(tuMayChu\)/.test(LP));
check("khoảng thanh trượt đọc từ JoycePlanet (không khai lại)", /const NUM = P\.LOOK_NUM;/.test(LP));
const keys = new Set((CONSOLE.match(/"look\.[a-z0-9_]+"/g) || []).map((s) => s.slice(1, -1)));
check("trang Cài đặt dùng nhiều khoá look.*", keys.size > 60);
const thieu = [...keys].filter((k) => !VI[k] || !EN[k]);
check("mọi khoá look.* có bản vi + en" + (thieu.length ? " (thiếu " + thieu.slice(0, 5).join(", ") + ")" : ""), thieu.length === 0);
check("nhãn tab Giao diện Joyce có đủ hai thứ tiếng", VI["settings.tab.appearance"] === "Giao diện Joyce" && !!EN["settings.tab.appearance"]);
// 0.65.42: khung xem trước kéo giãn tự do (chủ: "kéo rộng tự do khung tinh cầu demo to ra gần hết khung bên phải")
check("trang Giao diện Joyce dùng hết bề ngang (bỏ trần 960px)", /\.settings-page\.look-page \{ width: 100%; max-width: none; \}/.test(CSS));
check("khung xem trước mặc định lấp phần còn lại bên phải", /grid-template-columns: var\(--look-ctl, minmax\(340px, 520px\)\) 12px minmax\(300px, 1fr\);/.test(CSS));
check("có vạch kéo dọc đổi bề rộng + mép kéo dưới đổi chiều cao + nút phóng tối đa",
  /id="lookSplit" role="separator" aria-orientation="vertical"/.test(LP) && /id="lookResizeH" role="separator" aria-orientation="horizontal"/.test(LP) && /id="lookMax"/.test(LP));
check("kéo bằng con trỏ (chuột / ngón tay) có giữ con trỏ", /keo\(split, ev =>/.test(LP) && /keo\(handH, ev =>/.test(LP) && /setPointerCapture/.test(LP));
check("kéo được cả bằng bàn phím (mũi tên, Enter)", /phim\(split, "x"\); phim\(handH, "y"\);/.test(LP));
check("bấm đúp vạch / nút góc: phóng tối đa hoặc trả về", /split\.addEventListener\("dblclick", phongToiDa\)/.test(LP) && /maxBtn\.addEventListener\("click", phongToiDa\)/.test(LP));
check("cỡ khung nhớ theo máy (localStorage)", /KHOA_CO = "joyce\.lookPreviewSize"/.test(LP));
check("cỡ kẹp trong giới hạn (cột chỉnh >= 340px, khung >= 300px, cao >= 220px)", /CTL_MIN = 340, PV_MIN = 300, H_MIN = 220/.test(LP));
check("rời trang thì gỡ listener resize của cửa sổ", /window\.removeEventListener\("resize", apCo\)/.test(LP));
check("chiều cao khung theo biến --look-h (cả điện thoại)", /height: var\(--look-h, min\(72vh, 820px\)\)/.test(CSS) && /height: var\(--look-h, 220px\)/.test(CSS));
check("điện thoại ẩn vạch kéo dọc (một cột)", /\.look-split \{ display: none; \}/.test(CSS));
check("CSS: bố cục + [hidden] thắng display", /\.look-layout \{/.test(CSS) && /\[data-look-show\]\[hidden\] \{ display: none !important; \}/.test(CSS));
check("hud.js hoà giao diện tinh cầu từ máy chủ lúc khởi động",
  /jget\("\/settings"\)/.test(HUD) && /window\.JoycePlanet\.hydrateLook\(pl\)/.test(HUD));

// navigateTo chạy thật trong vm (cùng cách tests/js/test_settings_tabs.js)
function fn(name) {
  const start = CONSOLE.search(new RegExp("  (?:async )?function " + name + "\\("));
  return CONSOLE.slice(start, CONSOLE.indexOf("\n  }", start) + 4);
}
const nav = { active: "home", settingsTab: "general" };
const rendered = [];
const nctx = {
  Alpine: { store: () => nav }, TRANG_GOP: {}, TRANG_CUOI_KEY: "k", localStorage: { setItem() {} },
  window: {}, document: { body: { classList: { toggle() {} } } }, _pageLeave: null,
  renderPage: (id) => rendered.push([id, nav.settingsTab]), refreshModelUi() {}, parkQuickSet() {}, recomputeGraph() {},
};
vm.createContext(nctx);
vm.runInContext(fn("navigateTo"), nctx);
nctx.navigateTo("settings", true, "appearance");
check("navigateTo(settings, appearance) mở đúng tab", nav.active === "settings" && nav.settingsTab === "appearance");

// ---- 8. Luật toàn dự án ----
[["brain-planet.js", PLANET], ["console.js", CONSOLE], ["hud.js", HUD], ["console.css", CSS]].forEach(([f, s]) =>
  check("không em dash trong " + f, s.indexOf(String.fromCharCode(0x2014)) === -1));

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
