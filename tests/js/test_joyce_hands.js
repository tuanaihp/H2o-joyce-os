// Tích hợp kit điều khiển tay (/static/joyce-hands/) vào 3D Joyce.
//
//     python tests/run.py --js joyce_hands -v    (hoặc node trực tiếp)
//
// - GestureEngine (unit, ESM): pinch dwell 160ms + hysteresis + cooldown 650ms, palm
//   dwell 650ms + ổn định vị trí + release 200ms + cooldown 1800ms, mất tay/tay xấu ->
//   reset, pointer 0..1 mirror.
// - Khớp nối apex: setAttention + action gesture -> onGestureRequest + sự kiện vòng đời
//   joyce-avatar:exit/dispose; KHÔNG còn detectForVideo/landmarker trên main thread.
// - Khớp nối wrapper: panel nạp lười, connectJoyceHands, VoiceQuietGate -> stopCurrent,
//   asset URL trỏ /static hiện có; index.html link CSS + bump cache.
"use strict";
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const ROOT = path.join(__dirname, "..", "..");
const read = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");

let fails = 0;
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (cond || !extra ? "" : "  " + String(extra).slice(0, 400)));
  if (!cond) fails++;
}

// Bàn tay giả đủ 21 điểm cho GestureEngine: cổ tay (0,0.85), khớp giữa (0,0.45)
// -> scale 0.4. opts: pinch (ngón cái chạm ngón trỏ) | open (4 ngón duỗi, cái xa).
function fakeHand(mode) {
  const lm = Array.from({ length: 21 }, () => ({ x: 0.5, y: 0.5 }));
  lm[0] = { x: 0.5, y: 0.85 };            // cổ tay
  lm[9] = { x: 0.5, y: 0.45 };            // khớp gốc ngón giữa -> scale = 0.4
  // 4 ngón: duỗi (tip xa cổ tay hơn pip ~1.4x) khi 'open', gập về cổ tay khi 'fist'/'pinch'
  const xs = { 8: 0.3, 12: 0.42, 16: 0.55, 20: 0.66 };
  for (const [tip, pip] of [[8, 6], [12, 10], [16, 14], [20, 18]]) {
    if (mode === "open") { lm[pip] = { x: xs[tip], y: 0.45 }; lm[tip] = { x: xs[tip], y: 0.18 }; }
    else { lm[pip] = { x: 0.5, y: 0.55 }; lm[tip] = { x: 0.5, y: 0.68 }; }   // gập lại
  }
  if (mode === "pinch") { lm[8] = { x: 0.4, y: 0.2 }; lm[4] = { x: 0.4, y: 0.2 }; }  // cái chạm trỏ
  else { lm[4] = { x: 0.85, y: 0.55 }; }                                           // cái dang xa
  return lm;
}

async function main() {
  const { GestureEngine } = await import(
    pathToFileURL(path.join(ROOT, "dashboard", "joyce-hands", "gesture-engine.mjs")).href);

  // ---- Pinch: dwell 160ms, bắn đúng 1 lần khi giữ, cần nhả + cooldown để bắn lại ----
  let g = new GestureEngine();
  let fired = 0, at = 0;
  const pinch = fakeHand("pinch");
  for (let t = 0; t <= 5000; t += 50) {
    const r = g.update(pinch, t);
    for (const ge of r.gestures) { fired++; at = t; }
  }
  check("pinch: giữ 5 giây chỉ bắn 1 lần", fired === 1, fired);
  check("pinch: bắn sau dwell ~160ms (không phải tức thì)", at >= 160, at);
  const open = fakeHand("open");
  g.update(open, 5100); g.update(open, 5200);                              // nhả pinch
  let r2 = g.update(pinch, 5300);
  check("pinch: chụm lại ngay chưa bắn (dwell lại)", r2.gestures.length === 0);
  r2 = g.update(pinch, 5500);
  check("pinch: giữ đủ dwell sau nhả thì bắn lại", r2.gestures.filter((x) => x.type === "pinch").length === 1);

  // ---- Palm: dwell 650ms + đứng yên + release + cooldown 1800 ----
  g = new GestureEngine();
  fired = 0;
  for (let t = 0; t <= 600; t += 50) { const r = g.update(open, t); fired += r.gestures.length; }
  check("palm: <650ms chưa bắn", fired === 0, fired);
  fired += g.update(open, 700).gestures.length;
  check("palm: đủ 650ms bắn 1 lần", fired === 1, fired);
  for (let t = 750; t <= 2000; t += 50) fired += g.update(open, t).gestures.length;
  check("palm: giữ tiếp không bắn dồn", fired === 1, fired);
  // lắc tay -> dwell reset, không bắn
  g = new GestureEngine();
  let moved = fakeHand("open"), jiggle = 0;
  for (let t = 0; t <= 800; t += 50) {
    moved[0] = { x: 0.5 + (t % 200 === 0 ? 0.12 : -0.06), y: 0.85 };         // vượt scale*.25
    jiggle += g.update(moved, t).gestures.length;
  }
  check("palm: tay lắc không tích đủ dwell -> không bắn", jiggle === 0, jiggle);
  // nhả (nắm tay) rồi xòe lại: phải chờ release + cooldown 1800
  g = new GestureEngine();
  g.update(open, 0); g.update(open, 700);                                   // bắn ~700
  const fist = fakeHand("fist");
  g.update(fist, 750); g.update(fist, 1000);                                // nhả >200ms
  let r3 = g.update(open, 1200);
  check("palm: xòe lại sớm (<cooldown) không bắn", r3.gestures.length === 0);
  for (let t = 1250; t <= 2600; t += 50) { r3 = g.update(open, t); if (r3.gestures.length) break; }
  check("palm: sau cooldown 1800 + dwell bắn lại", r3.gestures.length === 1 && r3.gestures[0].type === "palm");

  // ---- Mất tay / dữ liệu xấu ----
  const r4 = g.update(null, 3000);
  check("không tay -> tracked=false, pose none", r4.tracked === false && r4.pose === "none" && r4.gestures.length === 0);
  const bad = fakeHand("open"); bad[8] = { x: 9, y: 9 };
  check("landmark ngoài khung -> tracked=false", g.update(bad, 3100).tracked === false);
  check("bàn tay quá nhỏ (xa) -> tracked=false", g.update(fakeHand("open").map((p) => ({ x: 0.5 + (p.x - 0.5) * 0.02, y: 0.5 + (p.y - 0.5) * 0.02 })), 3200).tracked === false);

  // ---- Pointer mirror 0..1 ----
  g = new GestureEngine();
  const h = fakeHand("open"); h[8] = { x: 0.2, y: 0.3 };                      // tay bên trái khung
  const rp = g.update(h, 0);
  check("pointer mirror: x 0..1, tay trái -> attention phải", rp.pointer.x > 0.5 && rp.pointer.x <= 1, rp.pointer.x);

  // ---- Tài nguyên tĩnh ----
  for (const f of ["gesture-engine.mjs", "hand-controller.mjs", "hand-worker.js",
                   "joyce-bridge.mjs", "voice-quiet-gate.mjs", "hand-panel.mjs", "hand-panel.css"])
    check("có file joyce-hands/" + f, fs.existsSync(path.join(ROOT, "dashboard", "joyce-hands", f)));
  for (const f of ["hand_landmarker.task", "mediapipe/vision_bundle.mjs",
                   "mediapipe/wasm/vision_wasm_internal.wasm"])
    check("dùng lại asset /static/humanoid/" + f, fs.existsSync(path.join(ROOT, "dashboard", "humanoid", f)));

  // ---- Khớp nối apex ----
  const apex = read("dashboard/apex-humanoid.js");
  check("apex: có setAttention(x,y)", /setAttention\s*\(/.test(apex));
  check("apex: nút gesture -> onGestureRequest", apex.includes("onGestureRequest"));
  check("apex: phát joyce-avatar:dispose khi huỷ", apex.includes("joyce-avatar:dispose"));
  check("apex: phát joyce-avatar:exit khi thoát", apex.includes("joyce-avatar:exit"));
  check("apex: KHÔNG còn detectForVideo main thread", !apex.includes("detectForVideo"));
  check("apex: KHÔNG còn landmarker/hands state", !apex.includes("landmarker") && !apex.includes("toggleHands"));
  check("apex: không còn video .jh-cam", !apex.includes("jh-cam"));

  // ---- Khớp nối wrapper ----
  const wrap = read("dashboard/joyce-humanoid.js");
  check("wrapper: mountHandPanel lười", wrap.includes("mountHandPanel"));
  check("wrapper: connectJoyceHands", wrap.includes("connectJoyceHands"));
  check("wrapper: VoiceQuietGate -> stopCurrent", wrap.includes("VoiceQuietGate") && wrap.includes("stopCurrent"));
  check("wrapper: onGestureRequest truyền apex", wrap.includes("onGestureRequest: function"));
  check("wrapper: asset URL /static/joyce-hands + /static/humanoid", wrap.includes("/static/joyce-hands/") && wrap.includes("hand_landmarker.task"));
  check("wrapper: đóng panel khi rời lớp nhìn", wrap.includes("closeHands()"));
  check("wrapper: disposeHands trong destroy", wrap.includes("disposeHands()"));

  // ---- Hợp đồng riêng tư/an toàn của controller+worker ----
  const ctl = read("dashboard/joyce-hands/hand-controller.mjs");
  const wrk = read("dashboard/joyce-hands/hand-worker.js");
  check("controller: getUserMedia audio:false (không xin mic)", ctl.includes("audio:false") && !ctl.includes("audio:true"));
  check("controller: 1 frame đang chờ + bỏ kết quả cũ >500ms", ctl.includes("this.busy") && ctl.includes(">500"));
  check("controller: watchdog worker 4s + init timeout", ctl.includes("4000") && ctl.includes("initTimeoutMs"));
  check("controller: tắt cam khi ẩn tab/pagehide", ctl.includes("visibilitychange") && ctl.includes("pagehide"));
  check("controller: epoch chốn cấp quyền-chậm", ctl.includes("this.epoch"));
  check("worker: detectForVideo trong Worker (không main thread)", wrk.includes("detectForVideo"));
  check("worker: 2 tay -> trả count, landmarks null", wrk.includes("count") && wrk.includes("length===1"));

  // ---- index.html ----
  const html = read("dashboard/index.html");
  check("index.html: link hand-panel.css", html.includes("/static/joyce-hands/hand-panel.css"));
  check("index.html: bump ?v= apex-humanoid + joyce-humanoid", html.includes("apex-humanoid.js?v=4") && html.includes("joyce-humanoid.js?v=6"));

  console.log(fails ? fails + " FAIL" : "ALL PASS");
  process.exit(fails ? 1 : 0);
}

main().catch((e) => { console.log("FAIL  lỗi nạp ESM: " + e.message); process.exit(1); });
