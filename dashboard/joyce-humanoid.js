// ============================================
// JOYCE HUMANOID - lớp nhìn "3D Joyce" trong khoang não (thay "3D View").
//
// Pho tượng bán thân người dựng từ ~16 nghìn hạt phát sáng (WebGL2 point sprites,
// không thư viện ngoài - đúng chuẩn brain-planet.js): đầu elip + cổ trụ + vai
// bán cầu dẹt, lõi "não" màu vàng cam giữa đầu, thêm bụi mờ quanh thân.
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
  // Tỷ lệ pho tượng bán thân: đầu nhỏ trên cổ ngắn, thanh vai cong + lồng ngực
  // bên dưới. Tách "vai" và "ngực" thành 2 ellipsoid chồng nhau - một ellipsoid
  // dẹt duy nhất (thiết kế đầu) nhìn ra đĩa bay chứ không ra người.
  var FIG = { head: [0, 0.44, 0], headR: [0.15, 0.20, 0.145],
              neckY: [0.18, 0.30], neckR: 0.05,
              sho:  { c: [0, 0.03, 0],  r: [0.50, 0.14, 0.16] },
              chest:{ c: [0, -0.15, 0], r: [0.32, 0.25, 0.15] } };

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
    var i, x, y, z, th, ph, r, k;

    // Mặt cầu đều (Fibonacci) co vào elip.
    function ellipsoid(cx, cy, cz, rx, ry, rz, jitter) {
      var t = (i + 0.5) / nBody, y0 = 1 - 2 * t;
      var rr = Math.sqrt(Math.max(0, 1 - y0 * y0));
      th = i * 2.39996322972865332;
      x = rr * Math.cos(th); y = y0; z = rr * Math.sin(th);
      pos[i * 3] = cx + x * rx + (rand() - 0.5) * jitter;
      pos[i * 3 + 1] = cy + y * ry + (rand() - 0.5) * jitter;
      pos[i * 3 + 2] = cz + z * rz + (rand() - 0.5) * jitter;
    }

    // Phân bổ thân: đầu 30% (ít hơn bản đầu - đầu nhỏ lại, đỡ cháy sáng),
    // cổ 5%, thanh vai 35%, lồng ngực 30%.
    var nHead = Math.round(nBody * 0.30), nNeck = Math.round(nBody * 0.05),
        nSho = Math.round(nBody * 0.35), nChest = nBody - nHead - nNeck - nSho, b0 = 0;
    for (i = 0; i < nHead; i++) { b0 = i; ellipsoid(FIG.head[0], FIG.head[1], FIG.head[2], FIG.headR[0], FIG.headR[1], FIG.headR[2], 0.007); }
    for (i = b0 + 1; i < b0 + 1 + nNeck; i++) {
      th = rand() * Math.PI * 2; y = lerp(FIG.neckY[0], FIG.neckY[1], rand());
      pos[i * 3] = Math.cos(th) * FIG.neckR; pos[i * 3 + 1] = y; pos[i * 3 + 2] = Math.sin(th) * FIG.neckR;
    }
    // Thanh vai: ellipsoid rộng-thấp, đỉnh cong rủ xuống hai bên; bóp thêm
    // chiều sâu z theo |x| để cánh tay thon dần ra mép - bớt dáng "đĩa bay".
    for (i = b0 + 1 + nNeck; i < b0 + 1 + nNeck + nSho; i++) {
      th = rand() * Math.PI * 2; ph = Math.acos(1 - 2 * rand());
      x = Math.sin(ph) * Math.cos(th) * FIG.sho.r[0];
      y = Math.cos(ph) * FIG.sho.r[1];
      z = Math.sin(ph) * Math.sin(th) * FIG.sho.r[2];
      var tap = 1 - 0.42 * Math.pow(Math.min(1, Math.abs(x) / FIG.sho.r[0]), 2);
      pos[i * 3] = FIG.sho.c[0] + x + (rand() - 0.5) * 0.008;
      pos[i * 3 + 1] = FIG.sho.c[1] + y + (rand() - 0.5) * 0.008;
      pos[i * 3 + 2] = FIG.sho.c[2] + z * tap + (rand() - 0.5) * 0.008;
    }
    // Lồng ngực: ellipsoid hẹp hơn vai, đứng hơn - thân dưới thanh vai.
    for (i = b0 + 1 + nNeck + nSho; i < nBody; i++) {
      th = rand() * Math.PI * 2; ph = Math.acos(1 - 2 * rand());
      pos[i * 3] = FIG.chest.c[0] + Math.sin(ph) * Math.cos(th) * FIG.chest.r[0] + (rand() - 0.5) * 0.008;
      pos[i * 3 + 1] = FIG.chest.c[1] + Math.cos(ph) * FIG.chest.r[1] + (rand() - 0.5) * 0.008;
      pos[i * 3 + 2] = FIG.chest.c[2] + Math.sin(ph) * Math.sin(th) * FIG.chest.r[2] + (rand() - 0.5) * 0.008;
    }
    // Lõi não: cụm hạt nhỏ gọn trong đầu, hơi lệch trước.
    for (i = nBody; i < nBody + nCore; i++) {
      var u = rand() * 2 - 1, t2 = rand() * Math.PI * 2, rr2 = Math.sqrt(1 - u * u);
      r = Math.cbrt(rand());
      pos[i * 3] = rr2 * Math.cos(t2) * 0.055 * r;
      pos[i * 3 + 1] = FIG.head[1] + 0.015 + u * 0.075 * r;
      pos[i * 3 + 2] = 0.02 + rr2 * Math.sin(t2) * 0.05 * r;
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
    "  float mouth = (1.0-smoothstep(0.0,0.045,abs(pos.y-0.40)))*step(0.0,pos.z)*step(aKind,0.5);",
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

  function create(opts) {
    opts = opts || {};
    var host = null, cv = null, st = null, gl = null, prog = null, vao = null;
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

    var R = {};
    R.mount = function (el) {
      host = el; mounted = true;
      cv = document.createElement("canvas");
      cv.className = "humanoid-gl"; cv.setAttribute("aria-hidden", "true");
      // Ẩn bằng style.display, KHÔNG bằng thuộc tính hidden: CSS ".planet-stage >
      // canvas { display:block }" và ".humanoid-gl { display:block }" đều có độ
      // ưu tiên cao hơn [hidden] nên hidden không bao giờ giấu được canvas.
      cv.style.display = "none";
      st = document.createElement("div");
      st.className = "hum-status"; st.setAttribute("aria-hidden", "true");
      st.style.display = "none";
      host.appendChild(cv); host.appendChild(st);
      if (host.dataset) host.dataset.quality = profile;
      initGL(); resize(); syncStatus();
      if (window.ResizeObserver) { ro = new ResizeObserver(resize); ro.observe(host); }
      else on(window, "resize", resize);
    };
    R.resize = resize;
    R.setJoyceState = function (s) {
      s = normState(s);
      if (s !== state) { state = s; stateAt = performance.now(); syncStatus(); }
    };
    R.setAudioAmplitude = function (v) { amp = clamp(+v || 0, 0, 1); };
    R.setInCall = function (v) { inCall = !!v; };
    R.pause = function () { paused = true; stopLoop(); };
    R.resume = function () { paused = false; if (!document.hidden) startLoop(); resize(); };
    R.isActive = function () { return active; };
    // Bật/tắt lớp nhìn humanoid (tab "3D Joyce"). Bật lần đầu = tạo hình lại
    // từ đầu (intro lắp ráp). Tắt = ẩn canvas + dừng vòng lặp để nhường GPU.
    R.activate = function (on) {
      on = !!on;
      if (on === active) return;
      active = on;
      if (host) host.classList.toggle("humanoid-on", on);
      // "" = trả về display:block của stylesheet; "none" = giấu hẳn (xem lý do
      // ở mount - [hidden] thua specificity nên không dùng được).
      if (cv) cv.style.display = on ? "" : "none";
      if (st) st.style.display = on ? "" : "none";
      if (on) {
        asmDone = false; asmT = 0;
        paused = false;
        if (!document.hidden) startLoop();
      } else stopLoop();
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
      listeners.forEach(function (l) { try { l[0].removeEventListener(l[1], l[2], l[3]); } catch (e) {} });
      listeners = []; if (ro) { try { ro.disconnect(); } catch (e) {} ro = null; }
      if (cv && cv.parentNode) cv.parentNode.removeChild(cv);
      if (st && st.parentNode) st.parentNode.removeChild(st);
    };
    R.info = function () {
      return { state: state, active: active, profile: profile, points: fig ? fig.n : 0,
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
    isActive: function () { return this._inst ? this._inst.isActive() : false; },
    activate: function (on) { if (this._inst) this._inst.activate(on); },
    info: function () { return this._inst ? this._inst.info() : null; },
  };
})();
