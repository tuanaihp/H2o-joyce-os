/* Cảm ứng trên tinh cầu: chụm/mở hai ngón để zoom, chạm đúp về góc nhìn đầu (0.65.39).

       node tests/js/test_tinh_cau_cham.js

   Chủ repo hỏi 2026-10-07: "trên giao diện điện thoại chưa zoom to zoom nhỏ quả tinh cầu bằng 2
   đầu ngón tay được". Trước bản này renderer chỉ biết MỘT con trỏ: ngón thứ hai ghi đè điểm kéo
   của ngón đầu nên quả cầu xoay giật chứ không zoom, và chạm đúp (điện thoại không chắc bắn
   dblclick) thành hai cú bấm = gọi Joyce rồi cúp ngay.

   Chạy renderer THẬT trong vm với một DOM giả tối thiểu (không WebGL nên rơi về bản safe, đủ để
   kiểm phần tương tác), rồi bắn chuỗi PointerEvent như ngón tay thật. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const PLANET = fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "brain-planet.js"), "utf8");
const fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

// Canvas 2D giả: mọi thuộc tính/hàm trả về chính nó, measureText().width = 10.
const U = new Proxy(function () {}, {
  get(t, k) { return k === "width" ? 10 : k === Symbol.toPrimitive ? () => 0 : U; },
  apply() { return U; },
  set() { return true; },
});
function fakeEl(tag) {
  const L = {};
  return {
    tagName: tag, style: {}, dataset: {}, hidden: false, className: "", width: 0, height: 0, offsetWidth: 140,
    classList: { add() {}, remove() {} }, children: [],
    appendChild(c) { this.children.push(c); c.parentNode = this; return c; },
    removeChild() {}, setAttribute() {},
    addEventListener(ev, fn) { (L[ev] = L[ev] || []).push(fn); }, removeEventListener() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600, right: 800, bottom: 600 }),
    getContext: (k) => (k === "2d" ? U : null),
    setPointerCapture() {}, releasePointerCapture() {},
    fire(ev, e) { (L[ev] || []).forEach((f) => f(e)); },
  };
}
let NOW = 1000;
let timers = [], tid = 0;
function sandbox() {
  const ctx = {
    window: { matchMedia: () => ({ matches: false, addEventListener() {} }), devicePixelRatio: 1,
      addEventListener() {}, removeEventListener() {}, dispatchEvent() {} },
    document: { documentElement: { getAttribute: () => null }, createElement: fakeEl,
      addEventListener() {}, removeEventListener() {}, hidden: false },
    navigator: { deviceMemory: 8, hardwareConcurrency: 8 },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: "" }, URLSearchParams, performance: { now: () => NOW },
    requestAnimationFrame: () => 1, cancelAnimationFrame() {},
    setTimeout: (fn) => { timers.push({ id: ++tid, fn }); return tid; },
    clearTimeout: (id) => { timers = timers.filter((x) => x.id !== id); },
    console, Event: function (n) { this.type = n; },
  };
  vm.createContext(ctx);
  vm.runInContext(PLANET, ctx);
  return ctx;
}
function runTimers() { const t = timers; timers = []; t.forEach((x) => x.fn()); }

const sb = sandbox();
let calls = 0;
function mount(opts) {
  const r = sb.window.JoycePlanet.create(Object.assign({ onPlanetClick: () => { calls++; } }, opts || {}));
  const host = fakeEl("div");
  r.mount(host);
  return { r, ov: host.children[1] };
}
const { r, ov } = mount();
const geo = r.planetGeom();
check("dựng được renderer với DOM giả (bản safe)", r.quality() === "safe" && geo.R > 50);
const cx = geo.cx, cy = geo.cy;
function ev(id, x, y, extra) {
  return Object.assign({ pointerId: id, pointerType: "touch", isPrimary: false, button: 0,
    clientX: x, clientY: y, preventDefault() {} }, extra || {});
}
const near = (a, b, e) => Math.abs(a - b) < (e || 1e-6);

// ---- 1. Mở hai ngón: zoom to ----
ov.fire("pointerdown", ev(1, cx - 100, cy, { isPrimary: true }));
ov.fire("pointerdown", ev(2, cx + 100, cy));                 // hai ngón cách 200px
ov.fire("pointermove", ev(2, cx + 300, cy));                 // cách 400px: x2
check("mở hai ngón gấp đôi khoảng cách -> zoom x2", near(r.camera().zoom, 2));
ov.fire("pointermove", ev(2, cx + 700, cy));                 // cách 800px: x4
check("mở rộng hơn nữa -> zoom x4", near(r.camera().zoom, 4));
ov.fire("pointermove", ev(2, cx + 100000, cy));
check("zoom bị kẹp ở trần 12 (cận cảnh Hải Phòng)", near(r.camera().zoom, 12));

// ---- 2. Chụm hai ngón: zoom nhỏ ----
ov.fire("pointermove", ev(2, cx + 100, cy));                 // về 200px: về x1
check("chụm về khoảng cách ban đầu -> zoom về x1", near(r.camera().zoom, 1));
ov.fire("pointermove", ev(2, cx - 90, cy));                  // 10px: x0,05 -> kẹp 0,12 (tầng Thiên hà)
check("chụm sát -> lùi xa, kẹp ở sàn 0,12 (tầng Thiên hà phòng ban)", near(r.camera().zoom, 0.12));
ov.fire("pointermove", ev(2, cx + 100, cy));

// ---- 3. Kéo hai ngón: xoay; nhấc ngón: không phải bấm ----
const yaw0 = r.camera().yaw;
ov.fire("pointermove", ev(1, cx - 60, cy));
ov.fire("pointermove", ev(2, cx + 140, cy));                 // điểm giữa dời 40px sang phải
check("kéo cả hai ngón -> xoay quả cầu", r.camera().yaw > yaw0);
check("kéo song song không đổi zoom", near(r.camera().zoom, 1));
ov.fire("pointerup", ev(2, cx + 140, cy));
ov.fire("pointermove", ev(1, cx - 20, cy));                  // ngón còn lại kéo tiếp
ov.fire("pointerup", ev(1, cx - 20, cy));
runTimers();
check("nhấc ngón sau khi chụm KHÔNG gọi Joyce", calls === 0);

// ---- 4. Chạm một lần vẫn gọi Joyce; chạm đúp về góc nhìn đầu ----
NOW += 1000;
ov.fire("pointerdown", ev(3, cx, cy, { isPrimary: true }));
ov.fire("pointerup", ev(3, cx, cy));
runTimers();
check("chạm một lần vào hành tinh -> gọi Joyce", calls === 1);
ov.fire("pointerdown", ev(4, cx - 100, cy, { isPrimary: true }));
ov.fire("pointerdown", ev(5, cx + 100, cy));
ov.fire("pointermove", ev(5, cx + 300, cy));
ov.fire("pointerup", ev(5, cx + 300, cy)); ov.fire("pointerup", ev(4, cx - 100, cy));
check("(chuẩn bị) đã zoom x2", near(r.camera().zoom, 2));
NOW += 1000;
ov.fire("pointerdown", ev(6, cx, cy, { isPrimary: true })); ov.fire("pointerup", ev(6, cx, cy));
NOW += 180;
ov.fire("pointerdown", ev(7, cx + 8, cy + 5, { isPrimary: true })); ov.fire("pointerup", ev(7, cx + 8, cy + 5));
runTimers();
check("chạm đúp -> về zoom x1 và góc nhìn đầu", near(r.camera().zoom, 1) && r.camera().yaw === 0 && r.camera().pitch === 0);
check("chạm đúp KHÔNG gọi rồi cúp Joyce", calls === 1);
NOW += 1000;
ov.fire("pointerdown", ev(8, cx, cy, { isPrimary: true })); ov.fire("pointerup", ev(8, cx, cy));
runTimers();                                                  // nhịp chờ 260ms của cú bấm đầu đã trôi qua
NOW += 600;
ov.fire("pointerdown", ev(9, cx, cy, { isPrimary: true })); ov.fire("pointerup", ev(9, cx, cy));
runTimers();
check("hai lần chạm cách xa nhau là hai cú bấm riêng", calls === 3);

// ---- 5. Bền: huỷ cử chỉ, con trỏ sót ----
ov.fire("pointerdown", ev(10, cx - 100, cy, { isPrimary: true }));
ov.fire("pointerdown", ev(11, cx + 100, cy));
ov.fire("pointercancel", ev(11, cx + 100, cy));
ov.fire("pointermove", ev(10, cx + 300, cy));
check("pointercancel (hệ điều hành cướp cử chỉ) dừng chụm, không zoom bậy", near(r.camera().zoom, 1));
ov.fire("pointerdown", ev(20, cx, cy, { isPrimary: true }));   // ngón 10 chưa từng nhấc: sót
ov.fire("pointermove", ev(20, cx + 300, cy));
check("ngón mới của cử chỉ mới không bị chụm với ngón sót", near(r.camera().zoom, 1));
ov.fire("pointerup", ev(20, cx + 300, cy));
const yawM = r.camera().yaw;
ov.fire("pointerdown", ev(30, cx, cy, { pointerType: "mouse", isPrimary: true, button: 2 }));
ov.fire("pointermove", ev(30, cx + 200, cy, { pointerType: "mouse" }));
check("chuột phải không bắt đầu kéo xoay", r.camera().yaw === yawM && near(r.camera().zoom, 1));

// ---- 6. Touchpad + Safari ----
let pd = 0;
ov.fire("wheel", { ctrlKey: true, deltaY: -50, preventDefault() { pd++; } });
check("chụm touchpad (wheel + ctrlKey) zoom mượt theo lực tay", near(r.camera().zoom, Math.exp(0.5), 1e-9) && pd === 1);
r.zoom(1);
let gs = 0;
ov.fire("gesturestart", { preventDefault() { gs++; } });
ov.fire("gesturechange", { preventDefault() { gs++; } });
check("Safari iOS: chặn phóng cả trang khi chụm trên quả cầu", gs === 2);
const pv = mount({ wheel: false });
pd = 0;
pv.ov.fire("wheel", { ctrlKey: false, deltaY: -100, preventDefault() { pd++; } });
check("ô xem trước: lăn chuột thường để cuộn trang (không zoom)", near(pv.r.camera().zoom, 1) && pd === 0);
pv.ov.fire("pointerdown", ev(40, cx - 100, cy, { isPrimary: true }));
pv.ov.fire("pointerdown", ev(41, cx + 100, cy));
pv.ov.fire("pointermove", ev(41, cx + 300, cy));
check("ô xem trước: vẫn chụm hai ngón để zoom được", near(pv.r.camera().zoom, 2));
pv.r.destroy(); r.destroy();

check("CSS: lớp vẽ tinh cầu tắt cử chỉ mặc định của trình duyệt (touch-action:none)",
  /\.planet-stage \.planet-ov \{ touch-action: none; \}/.test(fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "style.css"), "utf8")));

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
