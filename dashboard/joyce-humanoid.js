// ============================================
// JOYCE HUMANOID - lớp nhìn "3D Joyce" trong khoang não (thay "3D View").
//
// Hai đường render, cùng một API vòng đời (mount/activate/setJoyceState/
// setAudioAmplitude/pause/resume/destroy):
//   1) APEX (apex-humanoid.js -> global JoyceHumanoidApex): renderer tham chiếu
//      plates WebP + trường hạt, mount khi class có mặt VÀ assets nạp được.
//   2) Procedural (file này, fallback): pho tượng bán thân ~16 nghìn hạt WebGL2
//      point sprites tham số hoá - đầu/cổ/vai contour, lõi "não" vàng cam,
//      sống lưng tết + nốt ngực. Dùng khi thiếu apex file/assets/WebGL.
//
// Phản ứng theo trạng thái THẬT của Joyce (hud.js feedPlanet đẩy vào):
//   READY        thở nhẹ, lơ lửng
//   LISTENING    hơi nghiêng tới trước, sáng hơn chút (chú ý)
//   THINKING     hạt quay vòng quanh trục dọc + lõi đập nhanh
//   SPEAKING     khuấy động theo mức âm (mic + loa), dải miệng rung theo tiếng
//   CONNECTING   lấp lánh tụ lại
//   INTERRUPTING mờ đi, gần như đứng yên
//   RECONNECTING xoáy mạnh tụ lại
//   ERROR        đổi tông đỏ nhạt
//
// Mở lớp nhìn lần đầu: hạt từ vị trí rải rác lắp ráp thành hình (intro ~1.9s,
// giống cảnh "Opening Humanoid view"). Hồ sơ chất lượng high/balanced/safe/
// reduced y như tinh cầu; FPS < 30 thì tự hạ, mất context WebGL thì chờ dựng lại.
// ============================================
(function () {
  "use strict";

  var QKEY = "joyce.humanoidQuality";
  var STATES = ["READY", "CONNECTING", "LISTENING", "THINKING", "SPEAKING",
                "INTERRUPTING", "RECONNECTING", "ERROR"];

  // Tham số chuyển động theo trạng thái. agit = độ khuấy hạt, swirl = quay vòng
  // quanh trục dọc, breath = thở, lean = nghiêng tới trước, dim = nhân độ sáng,
  // err = lượng tông đỏ. Mọi giá trị được nội suy mềm mỗi khung.
  var STATE_CFG = {
    READY:        { agit: 0.10, swirl: 0.00, breath: 1.0, lean: 0.00, dim: 1.00, err: 0 },
    CONNECTING:   { agit: 0.38, swirl: 0.30, breath: 0.5, lean: 0.00, dim: 1.00, err: 0 },
    LISTENING:    { agit: 0.05, swirl: 0.00, breath: 0.6, lean: 0.30, dim: 1.12, err: 0 },
    THINKING:     { agit: 0.15, swirl: 0.55, breath: 0.5, lean: 0.00, dim: 1.00, err: 0 },
    SPEAKING:     { agit: 0.30, swirl: 0.08, breath: 0.9, lean: 0.14, dim: 1.20, err: 0 },
    INTERRUPTING: { agit: 0.02, swirl: 0.00, breath: 0.3, lean: 0.00, dim: 0.45, err: 0 },
    RECONNECTING: { agit: 0.26, swirl: 0.85, breath: 0.5, lean: 0.00, dim: 0.80, err: 0 },
    ERROR:        { agit: 0.18, swirl: 0.00, breath: 0.4, lean: 0.00, dim: 0.85, err: 1 },
  };

  var PROFILES = {
    //        body   core  mote  dprMax  twinkle
    high:     { body: 12000, core: 950, mote: 650, dpr: 2.0,  twinkle: 1 },
    balanced: { body: 7200,  core: 620, mote: 420, dpr: 1.5,  twinkle: 1 },
    safe:     { body: 3600,  core: 340, mote: 220, dpr: 1.0,  twinkle: 0 },
    reduced:  { body: 3600,  core: 340, mote: 220, dpr: 1.0,  twinkle: 0 },
  };
  var LADDER = ["high", "balanced", "safe"];

  var BODY_COL = [0.10, 0.87, 1.00];   // xanh cyan H2O
  var ICE_COL  = [0.75, 0.93, 1.00];   // viền sáng
  var CORE_COL = [1.00, 0.71, 0.30];   // lõi não vàng cam
  var MOTE_COL = [0.45, 0.80, 1.00];
  var ERR_COL  = [1.00, 0.35, 0.30];

  var ASSEMBLY_S = 1.9;          // giây lắp ráp intro
  // Pho tượng kiểu "contour MRI" (đúng ảnh mẫu chủ duyệt): hạt nằm trên các
  // VÀNH NGANG rời nhau nên ruột rỗng, viền sáng rõ, lõi vàng lộ ra xuyên qua
  // đầu-ngực - khác hẳn khối đặc phủ mặt. Biên dạng điều khiển bằng 2 hàm
  // profile bán kính theo chiều cao: headRx (cằm->sọ) và torsoRx (eo->vai).
  var FIG = { headY: [0.27, 0.65], headMaxR: 0.155, brain: [0, 0.46, 0.01],
              neckY: [0.16, 0.29], neckR: 0.048,
              torsoY: [-0.42, 0.20], waistR: 0.24, shoR: 0.50 };

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, k) { return a + (b - a) * k; }
  function mulberry(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---------- Hình người tham số hoá (không asset ngoài) ----------
  // Trả về { pos, from, seed, kind, n } - mảng phẳng để nạp buffer, dùng được cả
  // trong test (không cần GL). kind: 0 thân, 1 lõi, 2 bụi mờ.
  function sampleFigure(nBody, nCore, nMote, rand) {
    rand = rand || mulberry(977231);
    var n = nBody + nCore + nMote;
    var pos = new Float32Array(n * 3), from = new Float32Array(n * 3),
        seed = new Float32Array(n * 4), kind = new Float32Array(n);
    var i, th, ph, r;

    // Biên dạng đầu theo chiều cao y: cằm nhọn -> hàm -> thái dương rộng nhất
    // -> đỉnh sọ khép dần. Trả về bán kính ngang rx tại mỗi vành.
    function headRx(y) {
      var t = clamp((y - FIG.headY[0]) / (FIG.headY[1] - FIG.headY[0]), 0, 1);
      if (t <= 0.10) return 0.028 + t / 0.10 * 0.052;           // cằm -> hàm
      if (t <= 0.45) return 0.080 + (t - 0.10) / 0.35 * 0.075;  // hàm -> thái dương
      if (t <= 0.80) return 0.155 - (t - 0.45) / 0.35 * 0.028;  // sọ
      var u = (t - 0.80) / 0.20;                                 // đỉnh đầu khép
      return 0.127 * Math.sqrt(Math.max(0, 1 - u * u));
    }
    // Biên dạng thân: eo hẹp -> ngực -> vai loe mạnh -> dome rủ về cổ.
    function torsoRx(y) {
      var t = clamp((y - FIG.torsoY[0]) / (FIG.torsoY[1] - FIG.torsoY[0]), 0, 1);
      if (t < 0.50) return FIG.waistR + t / 0.5 * 0.12;          // eo -> ngực
      if (t < 0.78) return 0.36 + (t - 0.5) / 0.28 * 0.14;       // loe ra vai
      var u = (t - 0.78) / 0.22;                                  // dome vai -> cổ
      return FIG.shoR - u * u * 0.43;
    }

    // Danh sách vành ngang [y, rx, rz]. Bước y quyết định "độ nét" contour -
    // đủ thưa để thấy rõ vân, đủ dày để hình liền.
    var rings = [], ry, rx;
    for (ry = FIG.headY[0]; ry <= FIG.headY[1]; ry += 0.0125) {
      rx = headRx(ry);
      if (rx > 0.012) rings.push([ry, rx, rx * 1.05, 0]);        // 0 = đầu (z hơi sâu hơn x)
    }
    for (ry = FIG.neckY[0]; ry <= FIG.neckY[1]; ry += 0.014) {
      // Cổ lõm: mảnh ngay dưới cằm, loe dần ra chỗ gặp vai - không phải ống thẳng.
      var nt = (ry - FIG.neckY[0]) / (FIG.neckY[1] - FIG.neckY[0]);
      var nr = FIG.neckR * (1.30 - 0.30 * nt);
      rings.push([ry, nr, nr * 1.1, 1]);                         // 1 = cổ
    }
    for (ry = FIG.torsoY[0]; ry <= FIG.torsoY[1]; ry += 0.013) {
      rx = torsoRx(ry);
      rings.push([ry, rx, 0.10 + rx * 0.28, 2]);                 // 2 = thân/vai (z ~0.28x)
    }
    // Chia hạt theo chu vi vành (vành rộng nhận nhiều hạt hơn).
    var circ = rings.map(function (rg) { return Math.PI * (rg[1] + rg[2]); });
    var totCirc = circ.reduce(function (a, c) { return a + c; }, 0);
    var cnts = circ.map(function (c) { return Math.max(4, Math.round(nBody * c / totCirc)); });
    var diff = cnts.reduce(function (a, c) { return a + c; }, 0) - nBody;
    var ki = 0;
    while (diff !== 0) {   // cân cho khớp nBody: bớt/thêm vào vành lớn nhất
      var bi = 0; for (var q = 0; q < cnts.length; q++) if (circ[q] > circ[bi]) bi = q;
      if (diff > 0 && cnts[bi] > 4) { cnts[bi]--; diff--; } else if (diff < 0) { cnts[bi]++; diff++; } else diff = 0;
      if (++ki > 9999) break;
    }
    i = 0;
    for (var ri = 0; ri < rings.length && i < nBody; ri++) {
      var rg = rings[ri], cnt = Math.min(cnts[ri], nBody - i);
      for (var pj = 0; pj < cnt; pj++, i++) {
        var a = (pj / cnt) * Math.PI * 2 + rand() * 0.12;        // đều quanh vành + rung nhẹ
        // Vành gợn sóng (nét đặc trưng bản mẫu): bán kính đập theo góc + cao độ
        // dao động nhẹ - đường nhìn "sống" chứ không phải elip trơn.
        var wob = 1 + 0.045 * Math.sin(a * 3 + ri * 1.7);
        var px = Math.cos(a) * rg[1] * wob;
        pos[i * 3] = px + (rand() - 0.5) * 0.006;
        pos[i * 3 + 1] = rg[0] + (rand() - 0.5) * 0.005 + 0.004 * Math.sin(a * 5 + ri * 0.9);
        pos[i * 3 + 2] = Math.sin(a) * rg[2] * wob + (rand() - 0.5) * 0.006;
        // Gờ tai: hai điểm cực biên x của vành đầu nhô nhẹ ra.
        if (rg[3] === 0 && rg[0] > 0.36 && rg[0] < 0.53 && Math.abs(Math.cos(a)) > 0.88) {
          pos[i * 3] = px * 1.07;
        }
      }
    }
    while (i < nBody) { i++; pos[(i - 1) * 3 + 1] = 0.4; }       // an toàn: phần dư chụm vào cổ

    // Lõi vàng (kind=1) = não + sống lưng + nốt ngực, như "hệ thần kinh" phát
    // sáng chạy xuyên pho tượng - nét nhận diện chính trong ảnh mẫu.
    var nBrain = Math.round(nCore * 0.50), nSpine = Math.round(nCore * 0.28),
        nChestN = nCore - nBrain - nSpine;
    for (i = nBody; i < nBody + nBrain; i++) {                    // não: phủ vùng mặt, lệch trước
      var u2 = rand() * 2 - 1, t2 = rand() * Math.PI * 2, rr2 = Math.sqrt(1 - u2 * u2);
      r = Math.cbrt(rand());
      pos[i * 3] = FIG.brain[0] + rr2 * Math.cos(t2) * 0.075 * r;
      pos[i * 3 + 1] = FIG.brain[1] + u2 * 0.10 * r;
      pos[i * 3 + 2] = FIG.brain[2] + 0.02 + rr2 * Math.sin(t2) * 0.055 * r;
      kind[i] = 1;
    }
    for (i = nBody + nBrain; i < nBody + nBrain + nSpine; i++) {  // sống lưng: 3 sợi tết lệch pha
      var sy = lerp(-0.08, 0.42, rand());
      var ph2 = ((i - nBody - nBrain) % 3) * 2.094;
      pos[i * 3] = Math.sin(sy * 9 + ph2) * 0.018 + (rand() - 0.5) * 0.006;
      pos[i * 3 + 1] = sy;
      pos[i * 3 + 2] = 0.01 + Math.cos(sy * 9 + ph2) * 0.018 + (rand() - 0.5) * 0.006;
      kind[i] = 1;
    }
    for (i = nBody + nBrain + nSpine; i < nBody + nCore; i++) {   // nốt ngực sáng
      var u3 = rand() * 2 - 1, t3 = rand() * Math.PI * 2, rr3 = Math.sqrt(1 - u3 * u3);
      r = Math.cbrt(rand());
      pos[i * 3] = rr3 * Math.cos(t3) * 0.042 * r;
      pos[i * 3 + 1] = -0.07 + u3 * 0.05 * r;
      pos[i * 3 + 2] = 0.05 + rr3 * Math.sin(t3) * 0.035 * r;
      kind[i] = 1;
    }
    // Bụi mờ quanh thân (vỏ cầu r 0.55..1.0 quanh tâm tượng).
    for (i = nBody + nCore; i < n; i++) {
      th = rand() * Math.PI * 2; ph = Math.acos(1 - 2 * rand());
      r = 0.55 + rand() * 0.45;
      pos[i * 3] = Math.sin(ph) * Math.cos(th) * r * 0.9;
      pos[i * 3 + 1] = 0.08 + Math.cos(ph) * r * 0.75;
      pos[i * 3 + 2] = Math.sin(ph) * Math.sin(th) * r * 0.9;
      kind[i] = 2;
    }
    // Vị trí xuất phát intro: 60% vỏ cầu r 1.2..1.7, 40% tràn từ dưới lên.
    for (i = 0; i < n; i++) {
      if (rand() < 0.6) {
        th = rand() * Math.PI * 2; ph = Math.acos(1 - 2 * rand());
        r = 1.2 + rand() * 0.5;
        from[i * 3] = Math.sin(ph) * Math.cos(th) * r;
        from[i * 3 + 1] = 0.08 + Math.cos(ph) * r;
        from[i * 3 + 2] = Math.sin(ph) * Math.sin(th) * r;
      } else {
        from[i * 3] = (rand() - 0.5) * 2.4;
        from[i * 3 + 1] = -0.9 - rand() * 0.5;
        from[i * 3 + 2] = (rand() - 0.5) * 1.4;
      }
      seed[i * 4] = rand(); seed[i * 4 + 1] = 0.42 + rand() * 0.45;
      seed[i * 4 + 2] = rand(); seed[i * 4 + 3] = 1.6 + rand() * 3.4;
    }
    return { pos: pos, from: from, seed: seed, kind: kind, n: n };
  }

  var VS = "#version 300 es\nprecision highp float;\n" + [
    "in vec3 aPos; in vec3 aFrom; in vec4 aSeed; in float aKind;",
    "uniform float uT,uAsm,uPR,uSizeK,uAgit,uLevel,uSwirl,uBreath,uLean,uDim,uErr,uTwOn,uAspect,uFit,uReduced;",
    "out vec3 vC;",
    "float h1(float n){return fract(sin(n)*43758.5453);}",
    "void main(){",
    "  float dly = h1(aSeed.x*7.31)*0.55;",
    "  float p = uAsm>=1.0 ? 1.0 : smoothstep(dly, dly+0.45, uAsm);",
    "  vec3 pos = mix(aFrom, aPos, p);",
    "  float br = uBreath*(1.0-uReduced);",
    "  pos.y *= 1.0 + br*0.012*sin(uT*1.1 + aSeed.x*6.283);",
    "  pos.x *= 1.0 + br*0.006*sin(uT*1.1 + 1.7);",
    "  float sw = uSwirl*(1.0-uReduced);",
    "  float sa = sw*(uT*1.4 + aSeed.y*6.283);",
    "  float sr = 0.018*(abs(pos.y)+0.25);",
    "  pos.x += cos(sa)*sr*step(0.001,sw); pos.z += sin(sa)*sr*step(0.001,sw);",
    "  float jit = uAgit*(0.35+1.8*uLevel)*(1.0-uReduced);",
    "  pos.x += sin(uT*3.1+aSeed.x*37.0)*jit*0.012;",
    "  pos.y += sin(uT*2.7+aSeed.y*41.0)*jit*0.012;",
    "  pos.z += sin(uT*3.7+aSeed.z*43.0)*jit*0.012;",
    "  float mouth = (1.0-smoothstep(0.0,0.045,abs(pos.y-0.36)))*step(0.0,pos.z)*step(aKind,0.5);",
    "  pos.z += mouth*sin(uT*9.0+aSeed.w*40.0)*uLevel*jit*0.05;",
    "  pos.z += uLean*0.10*(0.4+pos.y); pos.y -= uLean*0.02;",
    "  float yaw = sin(uT*0.15)*0.10*(1.0-uReduced);",
    "  float cy=cos(yaw), sy=sin(yaw);",
    "  pos.xz = mat2(cy,-sy,sy,cy)*pos.xz;",
    "  vec2 ndc = pos.xy * uFit / (1.0 + pos.z*0.28);",
    "  ndc.x /= uAspect;",
    "  gl_Position = vec4(ndc, 0.0, 1.0);",
    "  float tw = 1.0 + uTwOn*0.35*sin(uT*aSeed.y+aSeed.x*6.283);",
    "  gl_PointSize = max(1.0, aSeed.w*uSizeK*uPR*tw*(1.0+uLevel*(aKind>0.5?0.9:0.3)));",
    "  float hue = h1(aSeed.z*5.17);",
    "  vec3 col = mix(vec3(0.10,0.87,1.00), vec3(0.75,0.93,1.00), hue*0.3);",
    "  float lum = 0.72;",
    "  if (aKind>1.5) { col = vec3(0.45,0.80,1.00); lum = 0.30; }",
    "  else if (aKind>0.5) { col = mix(vec3(1.00,0.71,0.30), vec3(1.00,0.85,0.55), hue); lum = 1.0; }",
    "  col = mix(col, vec3(1.00,0.35,0.30), uErr*0.7);",
    "  float pulse = 1.0 + (aKind>0.5 ? uLevel*0.8 + 0.18*sin(uT*2.3) : 0.0);",
    "  float fade = p < 1.0 ? (0.35+0.65*p) : 1.0;",
    "  vC = col * lum * uDim * pulse * fade * (0.55+0.45*tw);",
    "}"].join("\n");

  var FS = "#version 300 es\nprecision highp float;\n" + [
    "in vec3 vC; out vec4 o;",
    "void main(){",
    "  float r = length(gl_PointCoord - vec2(0.5));",
    "  if (r > 0.5) discard;",
    "  float a = 1.0 - smoothstep(0.06, 0.5, r);",
    "  o = vec4(vC * a, 1.0);",
    "}"].join("\n");

  function reducedOn() {
    try { return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
    catch (e) { return false; }
  }
  function readQ() {
    try { var q = localStorage.getItem(QKEY); return PROFILES[q] ? q : null; } catch (e) { return null; }
  }
  function pickProfile(requested) {
    if (requested) return requested;
    if (reducedOn()) return "reduced";
    var q = readQ(); if (q) return q;
    return "high";
  }

  // Bản đồ trạng thái Joyce -> trạng thái plate của renderer APEX
  // (apex-humanoid.js): idle/listening/thinking/speaking là plate riêng;
  // interrupting/reconnecting/error hiện đúng nhãn nhưng dùng plate idle.
  var APEX_STATES = { READY: "idle", CONNECTING: "idle", LISTENING: "listening",
                      THINKING: "thinking", SPEAKING: "speaking",
                      INTERRUPTING: "interrupting", RECONNECTING: "reconnecting",
                      ERROR: "error" };
  function mapState(s) {
    s = String(s || "READY").toUpperCase();
    return APEX_STATES[s] || "idle";
  }

  function create(opts) {
    opts = opts || {};
    var host = null, layer = null, cv = null, st = null, gl = null, prog = null, vao = null;
    // mode: null chưa dựng | "apex" renderer tham chiếu (apex-humanoid.js) |
    // "procedural" pho tượng hạt tham số hoá (fallback khi thiếu assets/WebGL).
    var apex = null, mode = null;
    var bufs = null, uni = {}, fig = null;
    var destroyed = false, paused = true, running = false, raf = 0, mounted = false;
    var active = false;                 // tab "3D Joyce" đang được chọn hay không
    var profile = "high", requested = null;
    var state = "READY", stateAt = 0, amp = 0, inCall = false;
    var cur = { agit: 0.1, swirl: 0, breath: 1, lean: 0, dim: 1, err: 0 };
    var t0 = 0, lastNow = 0, asmT = 0, asmDone = false;
    var fpsAcc = 0, fpsN = 0, fpsBad = 0;
    var W = 2, H = 2, dpr = 1, reduced = reducedOn();
    var listeners = [], ro = null;

    function on(el, ev, fn, o) { if (!el) return; el.addEventListener(ev, fn, o); listeners.push([el, ev, fn, o]); }

    function normState(s) {
      s = String(s || "READY").toUpperCase();
      return STATES.indexOf(s) >= 0 ? s : "READY";
    }

    function compile(type, src) {
      var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        try { console.warn("[humanoid] shader:", gl.getShaderInfoLog(s)); } catch (_) {}
        return null;
      }
      return s;
    }
    function makeProgram() {
      var v = compile(gl.VERTEX_SHADER, VS), f = compile(gl.FRAGMENT_SHADER, FS);
      if (!v || !f) return null;
      var p = gl.createProgram();
      gl.attachShader(p, v); gl.attachShader(p, f); gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) return null;
      ["uT","uAsm","uPR","uSizeK","uAgit","uLevel","uSwirl","uBreath","uLean",
       "uDim","uErr","uTwOn","uAspect","uFit","uReduced"].forEach(function (u) {
        uni[u] = gl.getUniformLocation(p, u);
      });
      return p;
    }
    function buildBuffers() {
      var pr = PROFILES[profile] || PROFILES.high;
      fig = sampleFigure(pr.body, pr.core, pr.mote, mulberry(977231));
      vao = gl.createVertexArray(); gl.bindVertexArray(vao);
      bufs = {};
      [["aPos", fig.pos, 3], ["aFrom", fig.from, 3], ["aSeed", fig.seed, 4], ["aKind", fig.kind, 1]].forEach(function (b) {
        var loc = gl.getAttribLocation(prog, b[0]);
        if (loc < 0) return;
        var bo = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, bo);
        gl.bufferData(gl.ARRAY_BUFFER, b[1], gl.STATIC_DRAW);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, b[2], gl.FLOAT, false, 0, 0);
        bufs[b[0]] = bo;
      });
      gl.bindVertexArray(null);
    }
    function initGL() {
      gl = cv.getContext("webgl2", { alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: "low-power" });
      if (!gl) { if (host) host.dataset.quality = "nogl"; return false; }
      prog = makeProgram(); if (!prog) return false;
      buildBuffers();
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
      gl.disable(gl.DEPTH_TEST);
      gl.clearColor(0, 0, 0, 0);
      on(cv, "webglcontextlost", function (e) { e.preventDefault(); stopLoop(); }, false);
      on(cv, "webglcontextrestored", function () {
        prog = makeProgram(); if (prog) { buildBuffers(); if (!paused) startLoop(); }
      }, false);
      return true;
    }

    function resize() {
      if (!host || !cv) return;
      var r = host.getBoundingClientRect();
      W = Math.max(2, Math.round(r.width)); H = Math.max(2, Math.round(r.height));
      var pr = PROFILES[profile] || PROFILES.high;
      dpr = Math.min(window.devicePixelRatio || 1, pr.dpr);
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      cv.style.width = W + "px"; cv.style.height = H + "px";
      if (gl) gl.viewport(0, 0, cv.width, cv.height);
    }

    function frame(now) {
      if (!running || !gl || !prog) return;
      var dt = lastNow ? Math.min(0.1, (now - lastNow) / 1000) : 0.016;
      lastNow = now;
      t0 += dt;
      // FPS tự hạ bậc (trừ khi đã safe/reduced).
      fpsAcc += dt; fpsN++;
      if (fpsAcc >= 1) {
        var fps = fpsN / fpsAcc;
        fpsAcc = 0; fpsN = 0;
        if (fps < 30 && active && LADDER.indexOf(profile) < LADDER.length - 1) {
          if (++fpsBad >= 3) {
            fpsBad = 0;
            profile = LADDER[LADDER.indexOf(profile) + 1];
            if (host) host.dataset.quality = profile;
            prog = makeProgram(); if (prog) buildBuffers(); resize();
          }
        } else fpsBad = 0;
      }
      // Intro lắp ráp.
      if (!asmDone) { asmT += dt; if (asmT >= ASSEMBLY_S + 0.55) asmDone = true; }
      // Nội suy trạng thái.
      var tg = STATE_CFG[state] || STATE_CFG.READY;
      var k = Math.min(1, dt * 5);
      cur.agit = lerp(cur.agit, tg.agit, k); cur.swirl = lerp(cur.swirl, tg.swirl, k);
      cur.breath = lerp(cur.breath, tg.breath, k); cur.lean = lerp(cur.lean, tg.lean, k);
      cur.dim = lerp(cur.dim, tg.dim, k); cur.err = lerp(cur.err, tg.err, k);

      var pr = PROFILES[profile] || PROFILES.high;
      gl.viewport(0, 0, cv.width, cv.height);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(prog);
      gl.bindVertexArray(vao);
      var asm = asmDone ? 1 : clamp(asmT / ASSEMBLY_S, 0, 1);
      gl.uniform1f(uni.uT, t0);
      gl.uniform1f(uni.uAsm, reduced ? 1 : asm);
      gl.uniform1f(uni.uPR, dpr);
      // uSizeK tính theo pixel CSS (H/W), dpr đi qua uPR riêng trong shader -
      // dùng cv.height (đã nhân dpr) ở đây sẽ nhân đôi dpr và phồng cỡ hạt.
      gl.uniform1f(uni.uSizeK, Math.min(H, W) / 620);
      gl.uniform1f(uni.uAgit, cur.agit);
      gl.uniform1f(uni.uLevel, amp);
      gl.uniform1f(uni.uSwirl, cur.swirl);
      gl.uniform1f(uni.uBreath, cur.breath);
      gl.uniform1f(uni.uLean, cur.lean);
      gl.uniform1f(uni.uDim, cur.dim);
      gl.uniform1f(uni.uErr, cur.err);
      gl.uniform1f(uni.uTwOn, pr.twinkle && !reduced ? 1 : 0);
      gl.uniform1f(uni.uAspect, W / H);
      // Pho tượng chiếm ~70% nửa chiều cao khung; kẹp lại khi khoang quá hẹp
      // ngang (mobile dọc) để vai không tràn mép.
      gl.uniform1f(uni.uFit, Math.min(0.70, 1.5 * (W / H)));
      gl.uniform1f(uni.uReduced, reduced ? 1 : 0);
      gl.drawArrays(gl.POINTS, 0, fig.n);
      gl.bindVertexArray(null);
    }
    function loopFn(now) { frame(now); if (running) raf = requestAnimationFrame(loopFn); }
    function startLoop() { if (running || destroyed || !gl) return; running = true; lastNow = 0; raf = requestAnimationFrame(loopFn); }
    function stopLoop() { running = false; cancelAnimationFrame(raf); raf = 0; }

    function syncStatus() {
      if (!st) return;
      st.textContent = "JOYCE 3D · " + state;
      st.dataset.st = state.toLowerCase();
    }

    // ---------- Đường render ----------
    // Renderer chính = APEX (texture plates tham chiếu + hạt 2D). Nếu
    // apex-humanoid.js không nạp được, ctor nổ, hoặc assets hỏng/thiếu ->
    // tự động rơi về renderer procedural (hạt tham số hoá) bên dưới.
    function startProcedural() {
      mode = "procedural";
      if (host && host.dataset) { host.dataset.mode = "procedural"; host.dataset.quality = profile; }
      cv = document.createElement("canvas");
      cv.className = "humanoid-gl"; cv.setAttribute("aria-hidden", "true");
      // Ẩn bằng style.display, KHÔNG bằng thuộc tính hidden: CSS ".planet-stage >
      // canvas { display:block }" và ".humanoid-gl { display:block }" đều có độ
      // ưu tiên cao hơn [hidden] nên hidden không bao giờ giấu được canvas.
      cv.style.display = "none";
      st = document.createElement("div");
      st.className = "hum-status"; st.setAttribute("aria-hidden", "true");
      st.style.display = "none";
      layer.appendChild(cv); layer.appendChild(st);
      initGL(); resize(); syncStatus();
    }
    function dropApex() {
      if (apex) { try { apex.dispose(); } catch (e) {} apex = null; }
      if (layer) { try { layer.textContent = ""; } catch (e) {} }
      startProcedural();
      if (active) applyActive(true);
    }

    // ---- Điều khiển tay qua camera (kit /static/joyce-hands/) ----
    // KHÔNG có khung xem trước: video sống ngoài DOM, giao diện chỉ là pho tượng.
    // Bấm ✋ HAND CAM -> tự xin quyền camera + bật nhận diện; bấm lại/rời lớp nhìn
    // -> tắt hẳn. Bridge: tracking -> apex.setAttention, pinch -> apex.pulse,
    // palm -> VoiceQuietGate -> đường ngắt thoại THẬT của app.js (stopCurrent()
    // = nút "Dừng": cắt TTS đang phát + huỷ lượt đúng phiên; mic/cuộc gọi giữ nguyên).
    var handCtl = null, handsDetach = null, handsGate = null, handsMods = null, handsLoading = null;
    var album = null;      // JoyceAlbum: trình chiếu ảnh trong khoang não (vuốt tay mở)
    function handAssets() {
      return { workerURL: "/static/joyce-hands/hand-worker.js",
               moduleURL: "/static/humanoid/mediapipe/vision_bundle.mjs",
               wasmURL: "/static/humanoid/mediapipe/wasm",
               modelURL: "/static/humanoid/hand_landmarker.task" };
    }
    function voiceSnapshot() {
      var os = document.getElementById("orbState"), sid = "";
      try { sid = (typeof savedSessionId !== "undefined" && savedSessionId) ? String(savedSessionId) : ""; } catch (e) {}
      var speaking = !!(os && (" " + os.className + " ").indexOf(" speaking ") >= 0);
      return { state: speaking ? "speaking" : "idle", responseId: sid || (speaking ? "live" : ""), sessionId: sid };
    }
    function ensureAlbum() {
      if (album || !handsMods || !handsMods.album) return;
      var hc = document.querySelector(".hud-center");
      if (!hc) return;
      album = new handsMods.album.JoyceAlbum({ host: hc, brain: "Ban Hang - Sales Hinh Anh" });
    }
    // Hồ sơ cử chỉ đã luyện (server STATE_DIR/hand_gestures.json): nạp vào engine khi
    // mở cam, và áp lại ngay khi bảng huấn luyện lưu (event joyce-hands:profile).
    function applyHandProfile(p) {
      if (handCtl && handCtl.engine && p && typeof p === "object") {
        try { handCtl.engine.setProfile(p); } catch (e) {}
      }
    }
    function fetchHandProfile() {
      fetch("/hands/profile", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(applyHandProfile).catch(function () {});
    }
    var onProfileSaved = function (e) { applyHandProfile(e.detail); };
    window.addEventListener("joyce-hands:profile", onProfileSaved);
    // Cử chỉ TỰ LUYỆN -> hành động thật trong khoang não.
    function runHandAction(act) {
      var hc = document.querySelector(".hud-center");
      switch (act) {
        case "album.open":  ensureAlbum(); if (album) album.open(); break;
        case "album.next":  if (album) album.next(); break;
        case "album.prev":  if (album) album.prev(); break;
        case "album.close": if (album) album.close(); break;
        case "fullscreen":
          if (!hc) break;
          if (document.fullscreenElement) document.exitFullscreen();
          else if (hc.requestFullscreen) hc.requestFullscreen();
          break;
        case "stop": if (handsGate) handsGate.request({ reason: "trained-pose", source: "camera" }); break;
        default: if (apex && apex.pulse) apex.pulse(0.5, 0.45); break;   // "pulse"
      }
    }
    // Bảng huấn luyện có camera riêng; tạm ngừng cam điều khiển để khỏi 2 worker đua nhau,
    // đóng bảng xong thì mở lại nếu trước đó đang bật.
    var trainerOpen = false, trainerWasActive = false;
    function openHandTrainer() {
      if (trainerOpen) return;
      trainerOpen = true;
      trainerWasActive = !!(handCtl && (handCtl.state === "active" || handCtl.state === "starting"));
      if (trainerWasActive) { try { handCtl.stop(); } catch (e) {} }
      import("/static/joyce-hands/gesture-trainer.mjs").then(function (m) {
        var p = m.openHandTrainer();
        var waitClose = setInterval(function () {
          var box = document.querySelector(".jht");
          if (box) return;
          clearInterval(waitClose); trainerOpen = false;
          fetchHandProfile();
          if (trainerWasActive && handCtl && !destroyed) { try { handCtl.start(); } catch (e) {} }
        }, 400);
      }).catch(function () { trainerOpen = false; if (trainerWasActive && handCtl) handCtl.start(); });
    }
    function wireHands() {
      if (!handCtl || !handsMods || !apex || !apex.root || apex.disposed) return;
      if (handsDetach) { try { handsDetach(); } catch (e) {} handsDetach = null; }
      ensureAlbum();
      handsDetach = handsMods.bridge.connectJoyceHands(handCtl, apex, {
        onQuietRequest: function (meta) { if (handsGate) handsGate.request(meta); },
        onGesture: function (d) {
          // Vuốt tay qua camera -> mở/lật/đóng album trình chiếu trên sân khấu não.
          if (d && d.type === "swipe" && album) album.swipe(d.dir);
          // Cử chỉ tự luyện -> hành động anh đã gán (album/fullscreen/pulse/stop...).
          if (d && d.type === "custom" && d.action) runHandAction(d.action);
        },
        onTracking: function (d) {
          // Album đang mở: khoảng cách 2 đầu ngón (cái-trỏ) = zoom liên tục.
          // Chỉ tính khi đúng 1 tay, không phải pose palm (đó là cử chỉ ngừng nói).
          if (album && album.isOpen() && d.tracked && d.pose !== "palm" && (d.handCount === 1 || d.handCount === undefined)) album.zoomFromRatio(d.pinchRatio);
        },
      });
    }
    function syncHandButton(state) {
      var b = apex && apex.root && apex.root.querySelector("[data-action=gesture]");
      if (!b) return;
      b.disabled = state === "starting";
      b.setAttribute("aria-pressed", String(state === "active"));
      b.textContent = state === "active" ? "✋ CAM ON" : "✋ HAND CAM";
    }
    function toggleHands() {
      if (handsLoading) return;
      if (handCtl) {
        if (handCtl.state === "active" || handCtl.state === "starting") handCtl.stop();
        else handCtl.start();
        return;
      }
      handsLoading = Promise.all([
        import("/static/joyce-hands/hand-controller.mjs"),
        import("/static/joyce-hands/joyce-bridge.mjs"),
        import("/static/joyce-hands/voice-quiet-gate.mjs"),
        import("/static/joyce-hands/album.mjs"),
      ]).then(function (mods) {
        if (destroyed) return;
        handsMods = { controller: mods[0], bridge: mods[1], gate: mods[2], album: mods[3] };
        var video = document.createElement("video");   // không gắn DOM -> không khung hình
        handCtl = new handsMods.controller.JoyceHandController(Object.assign(handAssets(), { video: video }));
        handCtl.addEventListener("status", function (e) {
          syncHandButton(e.detail.state);
          if (apex && apex.notice && e.detail.state !== "off") apex.notice(e.detail.message);
        });
        handCtl.addEventListener("error", function (e) { if (apex && apex.notice && e.detail) apex.notice(e.detail.message); });
        handsGate = new handsMods.gate.VoiceQuietGate({
          getSnapshot: voiceSnapshot,
          interruptSpeech: function () { try { if (window.stopCurrent) window.stopCurrent(); } catch (e) {} },
          onResult: function (r) {
            // Không nói -> pulse nhẹ thay cho im lặng (kit: idle = no-op có phản hồi UI).
            if (r && r.status === "ignored" && apex && apex.pulse) { try { apex.pulse(0.5, 0.45); } catch (e) {} }
          },
        });
        wireHands();
        fetchHandProfile();          // nạp cử chỉ đã luyện vào engine trước khi chạy
        handCtl.start();
      }).catch(function () {}).finally(function () { handsLoading = null; });
    }
    function closeHands() { if (handCtl) { try { handCtl.stop(); } catch (e) {} } if (album) { try { album.close(); } catch (e) {} } }
    function disposeHands() {
      window.removeEventListener("joyce-hands:profile", onProfileSaved);
      if (handsDetach) { try { handsDetach(); } catch (e) {} handsDetach = null; }
      if (handsGate) { try { handsGate.dispose(); } catch (e) {} handsGate = null; }
      if (album) { try { album.dispose(); } catch (e) {} album = null; }
      if (handCtl) { try { handCtl.dispose(); } catch (e) {} handCtl = null; }
      handsMods = null;
    }
    function startApex() {
      var Ctor = null;
      try { Ctor = window.JoyceHumanoidApex; } catch (e) {}
      if (!Ctor) return;
      try {
        apex = new Ctor(layer, {
          assetsBase: opts.assetsBase || "/static/humanoid/",
          autoStart: false,            // activate() điều khiển enter()
          controls: false,             // giấu nav demo - mic/TTS thật của Joyce lái
          demo: false,                 // không envelope giả khi speaking
          maxDpr: profile === "high" ? 1.5 : profile === "balanced" ? 1.25 : 1,
          fps: profile === "high" || profile === "balanced" ? 40 : 24,
          // Profile "reduced" chỉ hạ dpr/fps — KHÔNG được bỏ intro lắp ráp hay
          // field hạt (đó là nét mặt của Joyce). Chỉ cờ prefers-reduced-motion
          // của OS (accessibility) mới được tắt; để undefined thì apex tự đọc
          // mediaQuery của chính nó + bắt được khi OS đổi giữa chừng.
          reducedMotion: reduced || undefined,
          onExit: function () { if (opts.onExit) opts.onExit(); },
          onError: function () {},
          onGestureRequest: function () { toggleHands(); },
          onTrainRequest: function () { openHandTrainer(); },
        });
      } catch (e) { apex = null; return; }
      Promise.resolve(apex.ready).then(function () {
        if (destroyed || !apex) return;
        if (!apex.loaded) { dropApex(); return; }   // assets/WebGL fail -> fallback
        mode = "apex";
        if (host && host.dataset) host.dataset.mode = "apex";
        try { apex.setState(mapState(state)); apex.setLevel(amp); } catch (e) {}
        wireHands();   // panel mở sẵn mà apex dựng lại -> nối bridge vào avatar mới
        if (active) { try { apex.enter(); } catch (e) {} }
      }).catch(function () { if (!destroyed) dropApex(); });
    }

    // Bật/tắt hẳn phần hiển thị: lớp bọc .hum-layer giấu cả cây DOM của
    // renderer đang dùng (apex .jh hoặc canvas+hud-status procedural).
    function applyActive(on) {
      if (!on) closeHands();   // rời lớp nhìn -> đóng panel + tắt camera (kit spec)
      if (layer) layer.style.display = on ? "" : "none";
      if (apex && apex.loaded) { try { on ? apex.enter() : apex.pause(); } catch (e) {} }
      // "" = trả về display:block của stylesheet; "none" = giấu hẳn (xem lý do
      // ở startProcedural - [hidden] thua specificity nên không dùng được).
      if (cv) cv.style.display = on ? "" : "none";
      if (st) st.style.display = on ? "" : "none";
      if (on) {
        asmDone = false; asmT = 0;
        paused = false;
        if (!document.hidden) startLoop();
      } else stopLoop();
    }

    var R = {};
    R.mount = function (el) {
      if (mounted || !el) return;
      host = el; mounted = true;
      layer = document.createElement("div");
      layer.className = "hum-layer";
      layer.style.display = "none";
      host.appendChild(layer);
      startApex();
      if (!apex) startProcedural();
      if (window.ResizeObserver) { ro = new ResizeObserver(resize); ro.observe(host); }
      else on(window, "resize", resize);
    };
    R.resize = resize;
    R.setJoyceState = function (s) {
      s = normState(s);
      if (s !== state) {
        state = s; stateAt = performance.now(); syncStatus();
        if (apex && apex.loaded) { try { apex.setState(mapState(state)); } catch (e) {} }
      }
    };
    R.setAudioAmplitude = function (v) {
      amp = clamp(+v || 0, 0, 1);
      if (apex && apex.loaded) { try { apex.setLevel(amp); } catch (e) {} }
    };
    R.setInCall = function (v) { inCall = !!v; };
    R.pause = function () {
      paused = true; stopLoop();
      closeHands();
      if (apex && apex.loaded) { try { apex.pause(); } catch (e) {} }
    };
    R.resume = function () {
      paused = false; if (!document.hidden) startLoop(); resize();
      if (apex && apex.loaded) { try { apex.resume(); } catch (e) {} }
    };
    R.isActive = function () { return active; };
    // Bật/tắt lớp nhìn humanoid (tab "3D Joyce"). Bật lần đầu = tạo hình lại
    // từ đầu (intro lắp ráp). Tắt = ẩn layer + dừng vòng lặp để nhường GPU.
    R.activate = function (on) {
      on = !!on;
      if (on === active) return;
      active = on;
      if (host) host.classList.toggle("humanoid-on", on);
      applyActive(on);
      try { window.dispatchEvent(new CustomEvent("joyce:humanoid-view", { detail: { on: on } })); } catch (_) {}
    };
    R.setQuality = function (p) {
      requested = /^(high|balanced|safe|reduced)$/.test(p) ? p : null;
      try { if (requested) localStorage.setItem(QKEY, requested); else localStorage.removeItem(QKEY); } catch (e) {}
      profile = pickProfile(requested);
      if (host) host.dataset.quality = profile;
      if (gl && prog) { buildBuffers(); }
      resize();
    };
    R.destroy = function () {
      if (destroyed) return; destroyed = true; stopLoop();
      disposeHands();
      if (apex) { try { apex.dispose(); } catch (e) {} apex = null; }
      listeners.forEach(function (l) { try { l[0].removeEventListener(l[1], l[2], l[3]); } catch (e) {} });
      listeners = []; if (ro) { try { ro.disconnect(); } catch (e) {} ro = null; }
      if (cv && cv.parentNode) cv.parentNode.removeChild(cv);
      if (st && st.parentNode) st.parentNode.removeChild(st);
      if (layer && layer.parentNode) layer.parentNode.removeChild(layer);
      host = layer = cv = st = null;
    };
    R.info = function () {
      return { state: state, active: active, profile: profile, points: fig ? fig.n : 0,
               mode: mode || (apex ? "apex-loading" : "procedural"),
               reduced: reduced, inCall: inCall, gl: !!gl, amp: amp };
    };
    profile = pickProfile(null);
    window.JoyceHumanoid._inst = R;
    return R;
  }

  window.JoyceHumanoid = {
    _inst: null,
    create: create,
    // Hàm thuần lộ ra cho test + soi gỡ lỗi, không phụ thuộc GL.
    sampleFigure: sampleFigure,
    STATE_CFG: STATE_CFG,
    PROFILES: PROFILES,
    STATES: STATES.slice(),
    APEX_STATES: APEX_STATES,
    mapState: mapState,
    isActive: function () { return this._inst ? this._inst.isActive() : false; },
    activate: function (on) { if (this._inst) this._inst.activate(on); },
    info: function () { return this._inst ? this._inst.info() : null; },
  };
})();
