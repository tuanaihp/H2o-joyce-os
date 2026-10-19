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

  // ---- Vuốt tay: quét nhanh >=0.28 khung trong <450ms -> 1 swipe, cooldown ----
  // Swipe đo trên đầu ngón trỏ (pointer mirrored): tay người dùng sang PHẢI ->
  // raw x GIẢM -> mirrored pointer.x TĂNG -> dir 'right'. Chỉ đổ lm[8], giữ tay trong khung.
  const handAt = (x8, y8) => { const hh = fakeHand("open"); hh[8] = { x: x8, y: y8 }; return hh; };
  g = new GestureEngine();
  let swipes = [];
  for (let t = 0; t <= 400; t += 50) g.update(handAt(0.85, 0.18), t);          // giữ ngón ở bên phải raw (mirrored trái)
  for (let t = 450; t <= 550; t += 50) {                                     // quét ngón sang trái raw = mirrored PHẢI
    const r = g.update(handAt(0.3, 0.18), t);
    swipes = swipes.concat(r.gestures.filter((x) => x.type === "swipe"));
  }
  check("vuốt phải nhanh -> bắn swipe right đúng 1 lần", swipes.length === 1 && swipes[0].dir === "right", JSON.stringify(swipes));
  for (let t = 600; t <= 700; t += 50) {                                     // quét tiếp trong cooldown
    const r = g.update(handAt(0.08, 0.18), t);
    swipes = swipes.concat(r.gestures.filter((x) => x.type === "swipe"));
  }
  check("vuốt trong cooldown không bắn thêm", swipes.length === 1, swipes.length);
  g = new GestureEngine();
  swipes = [];
  for (let t = 0; t <= 1200; t += 100) {                                     // di chuyển CHẬM -> không swipe
    const r = g.update(handAt(0.85 - t * 0.0004, 0.18), t);
    swipes = swipes.concat(r.gestures.filter((x) => x.type === "swipe"));
  }
  check("tay trôi chậm không bắn swipe", swipes.length === 0, swipes.length);
  g = new GestureEngine();
  swipes = [];
  for (let t = 0; t <= 400; t += 50) g.update(handAt(0.3, 0.15), t);
  for (let t = 450; t <= 550; t += 50) {
    const r = g.update(handAt(0.3, 0.75), t);                                // vuốt XUỐNG
    swipes = swipes.concat(r.gestures.filter((x) => x.type === "swipe"));
  }
  check("vuốt xuống -> swipe down (đóng album)", swipes.length === 1 && swipes[0].dir === "down", JSON.stringify(swipes));

  // ---- Cử chỉ TỰ LUYỆN (bảng huấn luyện): fingerVector + setProfile + dwell/cooldown ----
  const { fingerVector } = await import(
    pathToFileURL(path.join(ROOT, "dashboard", "joyce-hands", "gesture-engine.mjs")).href);
  // Tay "2 ngón" (trỏ+giữa duỗi, nhẫn+út gập, cái dang): biến thể của fakeHand.
  const peaceHand = () => {
    const lm = fakeHand("fist");
    for (const [tip, pip, xs] of [[8, 6, 0.3], [12, 10, 0.42]]) {
      lm[pip] = { x: xs, y: 0.45 }; lm[tip] = { x: xs, y: 0.18 };
    }
    return lm;
  };
  const vecOpen = fingerVector(fakeHand("open"), 4 / 3);
  const vecPeace = fingerVector(peaceHand(), 4 / 3);
  const vecFist = fingerVector(fakeHand("fist"), 4 / 3);
  check("fingerVector: xòe đủ -> 4 ngón ~duỗi", vecOpen.slice(1).every((v) => v > 0.5), JSON.stringify(vecOpen));
  check("fingerVector: nắm tay -> ngón ~gập", vecFist.slice(1).every((v) => v < 0.45), JSON.stringify(vecFist));
  check("fingerVector: 2 ngón -> chỉ trỏ+giữa duỗi", vecPeace[1] > 0.55 && vecPeace[2] > 0.45 && vecPeace[3] < 0.45 && vecPeace[4] < 0.45, JSON.stringify(vecPeace));

  const profile2 = { custom: [{ id: "g_peace", label: "2 ngón", action: "album.next", vec: vecPeace, tol: [0.3, 0.3, 0.3, 0.3, 0.3] }], calib: {} };
  g = new GestureEngine();
  g.setProfile(profile2);
  let customs = [];
  for (let t = 0; t <= 400; t += 50) customs = customs.concat(g.update(peaceHand(), t).gestures);
  check("cử chỉ luyện: <450ms dwell chưa bắn", customs.length === 0, customs.length);
  customs = customs.concat(g.update(peaceHand(), 500).gestures, g.update(peaceHand(), 550).gestures);
  check("cử chỉ luyện: đủ dwell bắn custom + action", customs.length === 1 && customs[0].type === "custom" && customs[0].action === "album.next", JSON.stringify(customs));
  for (let t = 600; t <= 1200; t += 50) customs = customs.concat(g.update(peaceHand(), t).gestures);
  check("cử chỉ luyện: giữ không bắn dồn", customs.length === 1, customs.length);
  // nhả tay (nắm) rồi giơ lại: release 200ms + cooldown 1500ms
  g.update(fakeHand("fist"), 1250); g.update(fakeHand("fist"), 1500);
  let c2 = g.update(peaceHand(), 1700).gestures.length;
  check("cử chỉ luyện: giơ lại sớm (<cooldown) không bắn", c2 === 0, c2);
  c2 = 0;
  for (let t = 3200; t <= 3800; t += 50) { c2 += g.update(peaceHand(), t).gestures.length; if (c2) break; }
  check("cử chỉ luyện: hết cooldown bắn lại", c2 === 1, c2);
  // dáng KHÁC mẫu không khớp
  g = new GestureEngine(); g.setProfile(profile2);
  c2 = 0;
  for (let t = 0; t <= 800; t += 50) c2 += g.update(fakeHand("fist"), t).gestures.length;
  check("cử chỉ luyện: dáng sai không kích hoạt", c2 === 0, c2);
  // tay lắc -> reset dwell
  g = new GestureEngine(); g.setProfile(profile2);
  const jig = peaceHand(); c2 = 0;
  for (let t = 0; t <= 800; t += 50) {
    jig[0] = { x: 0.5 + (t % 200 === 0 ? 0.12 : -0.06), y: 0.85 };
    c2 += g.update(jig, t).gestures.length;
  }
  check("cử chỉ luyện: tay lắc không tích dwell", c2 === 0, c2);

  // Dáng luyện "5 ngón" THAY lệnh palm mặc định: palm gốc tắt, chỉ custom bắn.
  g = new GestureEngine();
  g.setProfile({ custom: [{ id: "g_palm", label: "5 ngón", action: "stop", vec: vecOpen, tol: [0.3, 0.3, 0.3, 0.3, 0.3] }], calib: {} });
  let palms = 0, cust = 0;
  for (let t = 0; t <= 900; t += 50) for (const ge of g.update(fakeHand("open"), t).gestures) {
    if (ge.type === "palm") palms++; if (ge.type === "custom") cust++;
  }
  check("5 ngón tự luyện thay palm: custom bắn, palm gốc tắt", cust === 1 && palms === 0, `custom=${cust} palm=${palms}`);
  // Không có dáng palm-like -> palm gốc vẫn sống
  g = new GestureEngine(); g.setProfile(profile2);
  let p2 = 0;
  for (let t = 0; t <= 900; t += 50) p2 += g.update(fakeHand("open"), t).gestures.filter((x) => x.type === "palm").length;
  check("không luyện 5 ngón -> palm mặc định vẫn bắn", p2 === 1, p2);

  // Hiệu chuẩn: calib.pinchOn ghi đè ngưỡng mặc định.
  const softPinch = fakeHand("pinch"); softPinch[4] = { x: 0.4, y: 0.15 }; softPinch[8] = { x: 0.4, y: 0.2 };
  g = new GestureEngine(); g.setProfile({ custom: [], calib: { pinchOn: 0.05 } });
  let p3 = 0;
  for (let t = 0; t <= 800; t += 50) p3 += g.update(softPinch, t).gestures.filter((x) => x.type === "pinch").length;
  check("calib pinchOn=0.05: khoảng cách 0.125 không còn tính là chụm", p3 === 0, p3);
  g = new GestureEngine();
  for (let t = 0; t <= 800; t += 50) p3 += g.update(softPinch, t).gestures.filter((x) => x.type === "pinch").length;
  check("mặc định pinchOn=0.32: cùng khoảng đó vẫn là chụm", p3 === 1, p3);

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

  // ---- Khớp nối wrapper (chế độ headless: không khung xem trước) ----
  const wrap = read("dashboard/joyce-humanoid.js");
  check("wrapper: JoyceHandController nạp lười", wrap.includes("JoyceHandController") && wrap.includes("hand-controller.mjs"));
  check("wrapper: video KHÔNG gắn DOM (giao diện chỉ là Joyce)", wrap.includes("document.createElement(\"video\")") && !wrap.includes("appendChild(video"));
  check("wrapper: không mount panel xem trước", !wrap.includes("mountHandPanel"));
  check("wrapper: connectJoyceHands", wrap.includes("connectJoyceHands"));
  check("wrapper: VoiceQuietGate -> stopCurrent", wrap.includes("VoiceQuietGate") && wrap.includes("stopCurrent"));
  check("wrapper: onGestureRequest -> toggleHands tự bật camera", wrap.includes("onGestureRequest: function () { toggleHands(); }"));
  check("wrapper: trạng thái camera -> nút + notice avatar", wrap.includes("syncHandButton") && wrap.includes("apex.notice"));
  check("wrapper: asset URL /static/joyce-hands + /static/humanoid", wrap.includes("/static/joyce-hands/") && wrap.includes("hand_landmarker.task"));
  check("wrapper: tắt cam khi rời lớp nhìn", wrap.includes("closeHands()"));
  check("wrapper: disposeHands trong destroy", wrap.includes("disposeHands()"));
  check("wrapper: album.mjs nạp lười cùng kit", wrap.includes("album.mjs"));
  check("wrapper: swipe -> album.swipe(dir)", wrap.includes('d.type === "swipe"') && wrap.includes("album.swipe"));
  check("wrapper: pinchRatio -> zoom album (1 tay, không palm)", wrap.includes("zoomFromRatio") && wrap.includes('d.pose !== "palm"'));

  // ---- Album trình chiếu + fullscreen ----
  const album = read("dashboard/joyce-hands/album.mjs");
  check("album.mjs tồn tại", !!album);
  check("album: nguồn /album + ảnh qua /files/raw", album.includes("/album?brain=") && album.includes("/files/raw?brain="));
  check("album: brain mặc định Sales Hinh Anh", album.includes("Ban Hang - Sales Hinh Anh"));
  check("album: swipe phải/trái lật, xuống đóng", album.includes("'right'") && album.includes("this.close()"));
  check("album: zoom liên tục từ ratio 2 ngón, kẹp 1..4.5", album.includes("zoomFromRatio") && album.includes("ZOOM_MAX = 4.5"));
  check("album: pho tượng thu nhỏ qua class album-open", album.includes("album-open"));
  const css = read("dashboard/style.css");
  check("css: album overlay + hum-layer thu nhỏ khi album mở", css.includes(".joyce-album") && css.includes("album-open #planetStage .hum-layer"));
  check("css: hud-center fullscreen", css.includes(".hud-center:fullscreen"));
  const html2 = read("dashboard/index.html");
  check("index.html: nút stageFullscreen cạnh icon mắt", html2.includes('id="stageFullscreen"'));
  const bview = read("dashboard/brain-view.js");
  check("brain-view: requestFullscreen trên .hud-center", bview.includes("requestFullscreen") && bview.includes("hud-center"));
  const srv = read("server/main.py");
  check("server: endpoint GET /album quét attachments+sources", srv.includes('@app.get("/album")') && srv.includes("_ALBUM_IMG_EXTS"));
  const eng = read("dashboard/joyce-hands/gesture-engine.mjs");
  check("engine: swipe trail + dir right/left/down/up", eng.includes("swipeTrail") && eng.includes("dir = 'down'"));

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
  check("index.html: không tải CSS panel (không khung camera trên UI)", !html.includes("hand-panel.css"));
  check("index.html: bump ?v= apex-humanoid + joyce-humanoid", html.includes("apex-humanoid.js?v=5") && html.includes("joyce-humanoid.js?v=8"));

  // ---- Bảng HUẤN LUYỆN cử chỉ (gesture-trainer + endpoint + khớp nối) ----
  check("có file gesture-trainer.mjs", fs.existsSync(path.join(ROOT, "dashboard", "joyce-hands", "gesture-trainer.mjs")));
  const trn = read("dashboard/joyce-hands/gesture-trainer.mjs");
  check("trainer: dùng JoyceHandController riêng + có preview (overlay)", trn.includes("JoyceHandController") && trn.includes("overlay"));
  check("trainer: quét 3 lần mới chốt", trn.includes("reps.length >= 3") || trn.includes("reps.length>=3"));
  check("trainer: giữ dáng qua nhiều khung (HOLD_FRAMES)", trn.includes("HOLD_FRAMES"));
  check("trainer: 3 lần lệch quá -> báo quét lại", trn.includes("> .5") || trn.includes("unstable"));
  check("trainer: lưu/đọc /hands/profile", trn.includes("/hands/profile") && trn.includes("method: 'PUT'"));
  check("trainer: gắn hành động cho cử chỉ (HAND_ACTIONS)", trn.includes("album.open") && trn.includes("fullscreen"));
  check("trainer: hiệu chuẩn pinch/palm/swipe", trn.includes("pinchOn") && trn.includes("palmExtMin") && trn.includes("swipeMinDelta"));
  check("trainer: phát sự kiện joyce-hands:profile sau lưu", trn.includes("joyce-hands:profile"));
  check("engine: export fingerVector + setProfile", eng.includes("export function fingerVector") && eng.includes("setProfile"));
  check("engine: custom pose dwell/cooldown/release riêng", eng.includes("poseHoldMs") && eng.includes("poseCooldownMs"));
  check("engine: palmSuppressed khi luyện dáng xòe", eng.includes("palmSuppressed"));
  check("controller: tracking kèm landmarks thô", ctl.includes("landmarks:data.landmarks"));
  check("server: GET/PUT /hands/profile + whitelist action", srv.includes('"/hands/profile"') && srv.includes("_HAND_ACTIONS") && srv.includes("hand_gestures.json"));
  check("apex: nút DẠY -> onTrainRequest", apex.includes('data-action="train"') && apex.includes("onTrainRequest"));
  check("wrapper: mở trainer + tạm tắt cam điều khiển", wrap.includes("openHandTrainer") && wrap.includes("trainerWasActive"));
  check("wrapper: custom action -> runHandAction (album/fullscreen)", wrap.includes('d.type === "custom"') && wrap.includes("runHandAction") && wrap.includes('"album.open"'));
  check("wrapper: nạp profile khi start + nghe sự kiện lưu", wrap.includes("fetchHandProfile") && wrap.includes("joyce-hands:profile"));
  const cj = read("dashboard/console.js");
  check("settings: thẻ Cử chỉ tay + nút mở trainer", cj.includes("setHandTrain") && cj.includes("gesture-trainer.mjs"));
  for (const lang of ["vi", "en", "de"]) {
    const ij = read("dashboard/i18n/" + lang + ".json");
    check(`i18n ${lang}: settings.hands + htr.*`, ij.includes('"settings.hands"') && ij.includes('"htr.title"') && ij.includes('"settings.hands_meta_done"'));
  }

  console.log(fails ? fails + " FAIL" : "ALL PASS");
  process.exit(fails ? 1 : 0);
}

main().catch((e) => { console.log("FAIL  lỗi nạp ESM: " + e.message); process.exit(1); });
