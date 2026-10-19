/* Đôi tay hạt + bảng hologram của 3D Joyce (dashboard/joyce-gestures.js).

     node tests/js/test_joyce_gestures.js

   Canh: hàm thuần (khung ảnh, chế độ tay), nối dây (index.html, app.js phát sự kiện,
   joyce-humanoid.js tạo/huỷ), không nạp ảnh, không em dash. */
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..", "..");
const doc = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const fails = [];
function check(ten, ok) { console.log((ok ? "ok   " : "FAIL ") + ten); if (!ok) fails.push(ten); }

const SRC = doc("dashboard/joyce-gestures.js");
const G = require(path.join(ROOT, "dashboard/joyce-gestures.js"));
const IDX = doc("dashboard/index.html");
const APP = doc("dashboard/app.js");
const WRAP = doc("dashboard/joyce-humanoid.js");

// 1) Hàm thuần
const r = G.figureRect(1280, 720, 0.926);
check("figureRect khớp apex: cao min(h*1.01, w*1.6), canh giữa, sát đáy",
  Math.abs(r.h - 727.2) < 0.01 && Math.abs(r.y - (720 - 727.2)) < 0.01 && Math.abs(r.x - (1280 - r.w) / 2) < 0.01);
check("modeOf: đang nghĩ -> làm việc", G.modeOf("THINKING", 1e9, 1e9) === "work");
check("modeOf: vừa có tool_call (dưới 4s) -> làm việc dù trạng thái READY", G.modeOf("READY", 1000, 1e9) === "work");
check("modeOf: đang nói hoặc chữ đang chảy -> trả lời", G.modeOf("SPEAKING", 1e9, 1e9) === "answer" && G.modeOf("READY", 1e9, 500) === "answer");
check("modeOf: không có gì -> rảnh (tay tan)", G.modeOf("READY", 9000, 9000) === "idle");
check("có 3 bảng hologram", G.PANELS.length === 3);

// 2) Nối dây
check("index.html: nạp joyce-gestures.js trước joyce-humanoid.js",
  IDX.indexOf("/static/joyce-gestures.js") > 0 && IDX.indexOf("/static/joyce-gestures.js") < IDX.indexOf("/static/joyce-humanoid.js"));
check("app.js: có hàm avatarAct phát joyce:avatar-act", /function avatarAct\(kind, label\)/.test(APP) && APP.includes('"joyce:avatar-act"'));
check("app.js: tool_call -> avatarAct(\"tool\", nhãn việc thật)", APP.includes('avatarAct("tool", _nhan)'));
check("app.js: tool_result / stream / turn_done đều báo cho nhân vật",
  APP.includes('avatarAct("result")') && APP.includes('avatarAct("answer")') && APP.includes('avatarAct("done")'));
check("wrapper: tạo JoyceGestures khi hình gốc sẵn sàng, chuyển state/level, huỷ khi destroy",
  WRAP.includes("new window.JoyceGestures(layer") && WRAP.includes("gestures.setState(state)") &&
  WRAP.includes("gestures.setLevel(amp)") && WRAP.includes("gestures.dispose()"));
check("wrapper: rời lớp nhìn thì dừng vẽ tay", WRAP.includes("if (gestures) gestures.stop();"));

// 3) An toàn
check("module lắng nghe joyce:avatar-act và gỡ khi huỷ", SRC.includes("addEventListener('joyce:avatar-act'") && SRC.includes("removeEventListener('joyce:avatar-act'"));
check("module không nạp ảnh, không gọi mạng", !SRC.includes("new Image(") && !SRC.includes("fetch("));
check("tôn trọng giảm chuyển động của hệ điều hành", SRC.includes("prefers-reduced-motion"));
check("không có em dash", !SRC.includes("—"));

console.log(fails.length ? "\n" + fails.length + " FAIL" : "\nTẤT CẢ PASS");
process.exit(fails.length ? 1 : 0);
