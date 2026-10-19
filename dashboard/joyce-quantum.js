/* ============================================================================
 * JOYCE QUANTUM - nhân vật "3D Joyce" vẽ HOÀN TOÀN bằng hạt (1.3.23).
 *
 * Thay renderer cũ (apex-humanoid.js) vốn hiển thị ẢNH CHỤP lấy từ một trang web
 * khác. Bản này không dùng một file ảnh nào: hình người, lõi sáng, mạch năng lượng
 * và dãy núi đều sinh bằng toán ở máy, chạy trên WebGL2.
 *
 *   - Pho tượng 3D: các vành hạt ngang ôm đầu - cổ - vai (kiểu ảnh chụp cắt lớp),
 *     xoay thật theo trục dọc và ngang. Mặt trước sáng hơn mặt sau, viền sáng nhất,
 *     nên mắt đọc ra khối.
 *   - Lõi cam trong mặt + mạch cam toả xuống ngực + quầng sáng.
 *   - Dãy núi hạt phía sau, sống núi có "sông" cam.
 *   - Xuất hiện: hạt phóng ra từ một đốm sáng dưới chân, xoáy thành dòng như sao
 *     chổi rồi ghép lại thành hình (giống hạt lượng tử tự lắp ráp).
 *   - Mỗi chế độ một hiệu ứng: nghe = vòng sóng toả quanh đầu; nghĩ = tia quét
 *     dọc đầu + vành xoắn + lõi đập; nói = sóng lan từ miệng theo âm lượng + lát
 *     nhiễu ngang; kết nối lại = hạt tan ra rồi tụ lại; lỗi = tông đỏ + nhiễu.
 *
 * API giữ đúng hợp đồng mà joyce-humanoid.js và kit cử chỉ tay (joyce-hands/)
 * đang dùng: new JoyceHumanoidQuantum(host, opts) -> ready, loaded, enter, exit,
 * pause, resume, dispose, setState, setLevel, setAttention, pulse, notice, root.
 * ========================================================================== */
(function (global) {
  'use strict';

  const STATES = ['idle', 'listening', 'thinking', 'speaking', 'interrupting', 'reconnecting', 'error'];
  const STATE_LABEL = { idle: 'SẴN SÀNG', listening: 'ĐANG NGHE', thinking: 'ĐANG NGHĨ',
    speaking: 'ĐANG NÓI', interrupting: 'GIÁN ĐOẠN', reconnecting: 'KẾT NỐI LẠI…', error: 'LỖI' };

  // Tham số nhìn của từng chế độ, nội suy mềm mỗi khung (không giật khi đổi chế độ).
  //   agit khuấy hạt · swirl xoắn vành + bụi quay · ripple vòng sóng quanh đầu
  //   scan tia quét · core độ sáng lõi · glitch lát nhiễu ngang · wave sóng từ miệng
  //   dim độ sáng chung · red tông đỏ · dissolve hạt tan ra · lean nghiêng tới trước
  const LOOK = {
    idle:         { agit: .05, swirl: 0,   ripple: 0,  scan: 0, core: .80, glitch: 0,   wave: 0, dim: 1.00, red: 0, dissolve: 0,   lean: 0   },
    listening:    { agit: .04, swirl: 0,   ripple: 1,  scan: 0, core: .90, glitch: 0,   wave: 0, dim: 1.12, red: 0, dissolve: 0,   lean: .25 },
    thinking:     { agit: .08, swirl: 1,   ripple: 0,  scan: 1, core: 1.35, glitch: 0,  wave: 0, dim: 1.00, red: 0, dissolve: 0,   lean: 0   },
    speaking:     { agit: .12, swirl: .12, ripple: .2, scan: 0, core: 1.15, glitch: .55, wave: 1, dim: 1.15, red: 0, dissolve: 0,  lean: .10 },
    interrupting: { agit: 0,   swirl: 0,   ripple: 0,  scan: 0, core: .40, glitch: .2,  wave: 0, dim: .45,  red: 0, dissolve: 0,   lean: 0   },
    reconnecting: { agit: .20, swirl: .8,  ripple: 0,  scan: 0, core: .60, glitch: .3,  wave: 0, dim: .80,  red: 0, dissolve: .35, lean: 0   },
    error:        { agit: .10, swirl: 0,   ripple: 0,  scan: 0, core: .50, glitch: .8,  wave: 0, dim: .85,  red: 1, dissolve: .03, lean: 0   },
  };

  // Số hạt theo bậc chất lượng (joyce-humanoid.js chọn bậc qua maxDpr).
  const BUDGET = {
    high:     { shell: 26000, core: 2600, vein: 2600, glow: 90, mote: 900, land: 16000 },
    balanced: { shell: 15000, core: 1600, vein: 1600, glow: 60, mote: 600, land: 9000  },
    safe:     { shell: 7500,  core: 800,  vein: 800,  glow: 36, mote: 300, land: 4500  },
  };
  // kind của từng hạt (trùng với shader).
  const K = { SHELL: 0, CORE: 1, VEIN: 2, GLOW: 3, MOTE: 4, LAND: 5, RIVER: 6 };

  const clamp = (n, a = 0, b = 1) => Math.max(a, Math.min(b, Number.isFinite(n) ? n : 0));
  const lerp = (a, b, k) => a + (b - a) * k;
  function mulberry(seed) {
    let s = seed >>> 0;
    return () => {
      s = (s + 0x6D2B79F5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---------------------------------------------------------------- hình học
  // Biên dạng pho tượng: bán kính ngang (rx) và sâu (rz) của từng vành theo chiều cao y.
  const FIG = { head: [0.27, 0.66], neck: [0.16, 0.31], torso: [-0.44, 0.25], brain: [0, 0.45, 0.04] };
  function headR(y) {
    const t = clamp((y - FIG.head[0]) / (FIG.head[1] - FIG.head[0]));
    if (t <= 0.10) return 0.030 + t / 0.10 * 0.050;              // cằm -> hàm
    if (t <= 0.45) return 0.080 + (t - 0.10) / 0.35 * 0.076;     // hàm -> thái dương
    if (t <= 0.80) return 0.156 - (t - 0.45) / 0.35 * 0.028;     // sọ
    const u = (t - 0.80) / 0.20;
    return 0.128 * Math.sqrt(Math.max(0, 1 - u * u));            // đỉnh đầu khép
  }
  function neckR(y) {
    const t = clamp((y - FIG.neck[0]) / (FIG.neck[1] - FIG.neck[0]));
    return 0.050 * (1.32 - 0.32 * t);
  }
  function torsoR(y) {
    const t = clamp((y - FIG.torso[0]) / (FIG.torso[1] - FIG.torso[0]));
    if (t < 0.45) return 0.30 + t / 0.45 * 0.10;                 // ngực
    if (t < 0.66) return 0.40 + (t - 0.45) / 0.21 * 0.10;        // loe ra vai
    const u = (t - 0.66) / 0.34;                                 // vai tròn dốc về cổ
    return Math.max(0.066, 0.50 * Math.pow(Math.cos(u * Math.PI / 2), 0.62));
  }
  const torsoDepth = rx => 0.10 + rx * 0.28;

  // Nhiễu giá trị 2D + fbm "sống núi" cho dãy núi phía sau.
  function noise2(seed) {
    const h = (x, y) => {
      const s = Math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453;
      return s - Math.floor(s);
    };
    return (x, y) => {
      const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
      const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
      const a = h(xi, yi), b = h(xi + 1, yi), c = h(xi, yi + 1), d = h(xi + 1, yi + 1);
      return lerp(lerp(a, b, u), lerp(c, d, u), v);
    };
  }
  function ridge(n, x, z) {
    let amp = 0.5, f = 1, sum = 0, norm = 0;
    for (let o = 0; o < 4; o++) {
      const r = 1 - Math.abs(n(x * f, z * f) * 2 - 1);
      sum += r * r * amp; norm += amp; amp *= 0.5; f *= 2.03;
    }
    return sum / norm;                                           // 0..1, 1 = sống núi
  }

  /** Sinh toàn bộ cảnh. Hàm thuần (không GL) để test và để dựng lại khi đổi bậc. */
  function buildScene(budget, rand) {
    rand = rand || mulberry(20261019);
    const b = budget || BUDGET.high;
    const n = b.shell + b.core + b.vein + b.glow + b.mote + b.land;
    const pos = new Float32Array(n * 3), spawn = new Float32Array(n * 3),
          seed = new Float32Array(n * 4), kind = new Float32Array(n);
    let i = 0;
    const put = (x, y, z, k) => { pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z; kind[i] = k; i++; };

    // 1) Vỏ: các vành ngang. Vành rộng nhận nhiều hạt hơn (chia theo chu vi).
    const rings = [];
    for (let y = FIG.head[0]; y <= FIG.head[1]; y += 0.0105) { const r = headR(y); if (r > 0.012) rings.push([y, r, r * 1.06, 0]); }
    for (let y = FIG.neck[0]; y <= FIG.neck[1]; y += 0.012) { const r = neckR(y); rings.push([y, r, r * 1.1, 1]); }
    for (let y = FIG.torso[0]; y <= FIG.torso[1]; y += 0.0115) { const r = torsoR(y); rings.push([y, r, torsoDepth(r), 2]); }
    const circ = rings.map(r => Math.PI * (r[1] + r[2]));
    const tot = circ.reduce((a, c) => a + c, 0);
    let left = b.shell;
    rings.forEach((rg, ri) => {
      const cnt = ri === rings.length - 1 ? left : Math.min(left, Math.max(6, Math.round(b.shell * circ[ri] / tot)));
      left -= cnt;
      for (let j = 0; j < cnt; j++) {
        const a = (j / cnt) * Math.PI * 2 + rand() * 0.05;
        const wob = 1 + 0.035 * Math.sin(a * 3 + ri * 1.7);       // vành gợn nhẹ, nhìn "sống"
        let x = Math.cos(a) * rg[1] * wob;
        if (rg[3] === 0 && rg[0] > 0.37 && rg[0] < 0.53 && Math.abs(Math.cos(a)) > 0.9) x *= 1.06; // gờ tai
        put(x + (rand() - .5) * .004, rg[0] + (rand() - .5) * .003, Math.sin(a) * rg[2] * wob + (rand() - .5) * .004, K.SHELL);
      }
    });
    while (i < b.shell) put(0, 0.3, 0, K.SHELL);

    // 2) Lõi cam: khối elip trong mặt, lệch về phía trước.
    for (let c = 0; c < b.core; c++) {
      const u = rand() * 2 - 1, t = rand() * Math.PI * 2, rr = Math.sqrt(1 - u * u), r = Math.cbrt(rand());
      put(FIG.brain[0] + rr * Math.cos(t) * 0.055 * r, FIG.brain[1] - 0.02 + u * 0.06 * r,
          FIG.brain[2] + 0.03 + rr * Math.sin(t) * 0.04 * r, K.CORE);
    }

    // 3) Mạch cam: từ cổ toả xuống ngực và ra vai (đi bộ ngẫu nhiên có rẽ nhánh),
    //    nằm trên mặt trước thân + vài sợi chạy lên não.
    const front = (x, y) => {
      if (y > FIG.neck[0]) { const r = neckR(y); return r * 1.1 * Math.sqrt(Math.max(0, 1 - (x / r) ** 2)) + 0.004; }
      const r = torsoR(y); return torsoDepth(r) * Math.sqrt(Math.max(0, 1 - (x / r) ** 2)) + 0.004;
    };
    const paths = [];
    for (let p = 0; p < 16; p++) paths.push({ x: (rand() - .5) * .02, y: 0.16 - rand() * 0.04, a: -Math.PI / 2 + (rand() - .5) * 2.4, life: 30 + rand() * 40 });
    for (let p = 0; p < 4; p++) paths.push({ x: (rand() - .5) * .02, y: 0.17, a: Math.PI / 2 + (rand() - .5) * .3, life: 16, up: true });
    let v = 0, guard = 0;
    while (v < b.vein && guard++ < 200000) {
      const w = paths[guard % paths.length];
      if (w.life <= 0) {                                         // nhánh hết đời: mọc lại từ cổ
        Object.assign(w, { x: (rand() - .5) * .03, y: 0.15 - rand() * 0.05, a: -Math.PI / 2 + (rand() - .5) * 2.6, life: 25 + rand() * 45 });
        if (w.up) Object.assign(w, { y: 0.17, a: Math.PI / 2 + (rand() - .5) * .3, life: 16 });
      }
      w.a += (rand() - .5) * 0.45;
      if (w.up) w.a = lerp(w.a, Math.PI / 2, 0.3);
      w.x += Math.cos(w.a) * 0.011; w.y += Math.sin(w.a) * 0.011; w.life--;
      if (w.y < FIG.torso[0] + 0.02 || w.y > (w.up ? 0.40 : 0.2) || Math.abs(w.x) > torsoR(Math.min(w.y, 0.2)) * 0.95) { w.life = 0; continue; }
      for (let s = 0; s < 3 && v < b.vein; s++, v++) {
        const z = w.up ? FIG.brain[2] : front(w.x, w.y);
        put(w.x + (rand() - .5) * .004, w.y + (rand() - .5) * .004, z, K.VEIN);
      }
    }
    while (v++ < b.vein) put(0, 0.1, 0.1, K.VEIN);

    // 4) Quầng sáng: vài hạt to mờ ở lõi và cổ (giả bloom, không cần pass hậu kỳ).
    for (let g = 0; g < b.glow; g++) {
      const onFace = g < b.glow * 0.7;
      put((rand() - .5) * (onFace ? .10 : .05), onFace ? 0.40 + rand() * 0.14 : 0.0 + rand() * 0.18, 0.08, K.GLOW);
    }

    // 5) Bụi quanh thân.
    for (let m = 0; m < b.mote; m++) {
      const th = rand() * Math.PI * 2, ph = Math.acos(1 - 2 * rand()), r = 0.6 + rand() * 0.5;
      put(Math.sin(ph) * Math.cos(th) * r, 0.12 + Math.cos(ph) * r * 0.8, Math.sin(ph) * Math.sin(th) * r * 0.7, K.MOTE);
    }

    // 6) Dãy núi: hạt dồn về sống núi; đỉnh cao ở hai bên, thấp dần sau lưng tượng.
    const nz = noise2(7.3);
    let land = 0; guard = 0;
    while (land < b.land && guard++ < b.land * 30) {
      const xn = (rand() * 2 - 1) * 1.08, z = -0.25 - rand() * 1.0, depth = (3.1 - z) / 6.4;
      const r = ridge(nz, xn * 4.2 + 3.1, z * 2.4);
      if (rand() > r * r * 1.1) continue;                       // giữ hạt ở sống núi nhiều hơn
      const ax = Math.abs(xn), side = clamp((ax - 0.22) / 0.45) * (0.8 + 0.2 * Math.sin(ax * 9 + z * 3.1));
      const rn = clamp((r - 0.22) / 0.58);
      if (Math.abs(xn) < 0.30 || rn < 0.06) continue;           // sau lưng tượng và chân núi phẳng: bỏ (thành vệt sáng)
      const yn = -1.06 + rn * 1.32 * (0.14 + 0.86 * side);
      const x = xn * depth * 1.78, y = 0.22 + yn * depth;
      const river = r > 0.80 && rand() < 0.45;
      put(x, y, z, river ? K.RIVER : K.LAND); land++;
    }
    while (land++ < b.land) put(0, -2, -1, K.LAND);

    // Điểm xuất phát lắp ráp + hạt giống ngẫu nhiên.
    for (let q = 0; q < n; q++) {
      spawn[q * 3] = (rand() - .5) * .03; spawn[q * 3 + 1] = -0.20 + (rand() - .5) * .02; spawn[q * 3 + 2] = 0.05 + (rand() - .5) * .03;
      seed[q * 4] = rand(); seed[q * 4 + 1] = rand(); seed[q * 4 + 2] = rand(); seed[q * 4 + 3] = rand();
    }
    return { pos, spawn, seed, kind, n, counts: b };
  }

  // ---------------------------------------------------------------- shader
  const VS = `#version 300 es
precision highp float;
in vec3 aPos; in vec3 aSpawn; in vec4 aSeed; in float aKind;
uniform float uT, uAsm, uPR, uSize, uAspect, uFit, uLevel, uYaw, uPitch, uMotion, uShiftY;
uniform float uAgit, uSwirl, uScan, uCore, uGlitch, uWave, uDim, uRed, uDissolve, uLean;
out vec3 vC; out float vSoft;
float h1(float n){ return fract(sin(n) * 43758.5453); }
vec3 rotY(vec3 p, float a){ float c = cos(a), s = sin(a); return vec3(c*p.x + s*p.z, p.y, -s*p.x + c*p.z); }
vec3 rotX(vec3 p, float a){ float c = cos(a), s = sin(a); return vec3(p.x, c*p.y - s*p.z, s*p.y + c*p.z); }
void main(){
  bool land = aKind > 4.5;
  float k = aKind;
  // Lắp ráp: tượng ráp trước (trễ theo hạt), núi mọc lên sau cùng.
  float dly = land ? 0.62 + aSeed.x * 0.08 : aSeed.x * 0.66;
  float p = uAsm >= 1.0 ? 1.0 : smoothstep(dly, dly + 0.30, uAsm);
  vec3 pos = aPos;
  vec3 nrm = normalize(vec3(aPos.x, 0.0, aPos.z) + 1e-4);
  float mo = uMotion;
  if (!land) {
    pos.y *= 1.0 + 0.006 * sin(uT * 1.2) * mo;                                   // thở
    vec3 dir = normalize(vec3(h1(aSeed.y*91.0) - .5, h1(aSeed.z*57.0) - .5, h1(aSeed.w*33.0) - .5) + 1e-3);
    pos += dir * uDissolve * (0.22 + 0.22 * sin(uT * 1.6 + aSeed.x * 6.283)) * mo; // tan ra - tụ lại
    float j = uAgit * (0.4 + 1.6 * uLevel) * mo;
    pos += vec3(sin(uT*3.1 + aSeed.x*37.0), sin(uT*2.7 + aSeed.y*41.0), sin(uT*3.7 + aSeed.z*43.0)) * j * 0.01;
    if (k < 0.5) {
      pos = rotY(pos, sin(pos.y * 14.0 + uT * 2.2) * 0.10 * uSwirl * mo);          // vành xoắn khi nghĩ
      float dm = length(pos - vec3(0.0, 0.36, 0.11));
      pos += nrm * uWave * uLevel * 0.04 * sin(dm * 38.0 - uT * 9.0) * exp(-dm * 2.4) * mo; // sóng từ miệng
    }
    if (k > 3.5) pos = rotY(pos, uT * (0.05 + 0.55 * uSwirl) * mo);                // bụi quay
    if (k > 0.5 && k < 3.5) {                                                      // lõi đập
      vec3 c = vec3(0.0, 0.46, 0.05);
      if (k < 1.5) pos = c + (pos - c) * (1.0 + 0.07 * sin(uT * 5.0) * max(0.0, uCore - 0.7) * mo + 0.05 * uLevel);
    }
    pos.z += uLean * 0.08 * (pos.y + 0.4);
    pos.y -= 0.30; pos = rotX(rotY(pos, uYaw), uPitch); pos.y += 0.30;
    float band = floor(pos.y * 46.0), tk = floor(uT * 14.0);                       // lát nhiễu ngang
    if (h1(band * 13.1 + tk * 7.7) > 1.0 - uGlitch * 0.10) pos.x += (h1(band + tk) - 0.5) * 0.12 * uGlitch * mo;
  } else {
    pos = rotY(pos, uYaw * 0.12);
    pos.y += 0.006 * sin(uT * 0.7 + aPos.x * 3.0) * mo;
  }
  // Đường bay lắp ráp: từ đốm sáng dưới chân, vòng qua một điểm xoắn rồi về đích.
  vec3 P = pos;
  if (p < 1.0) {
    float e = mix(p, p * p * (3.0 - 2.0 * p), 0.4);
    if (land) {
      P = mix(pos + vec3(0.0, -0.9, 0.0), pos, e);
    } else {
      // Mọi hạt cùng một dải xoắn: hạt rời đốm sáng cùng lúc thì bay cùng pha, nên
      // nhìn thành DÒNG sao chổi uốn vòng chứ không phải đám bụi.
      float ph = dly * 3.2 + (aSeed.y - 0.5) * 0.25;
      vec3 c1 = vec3(-0.80 * cos(ph), -0.14 + aSeed.z * 0.05, 0.25 * sin(ph));
      vec3 c2 = vec3(0.70 * sin(ph + 0.6), aPos.y + 0.18, 0.25 * cos(ph));
      float u = 1.0 - e;
      P = u*u*u*aSpawn + 3.0*u*u*e*c1 + 3.0*u*e*e*c2 + e*e*e*pos;
    }
  }
  float z = 3.1 - P.z;
  vec2 ndc = (P.xy - vec2(0.0, 0.22)) * (6.4 * uFit) / z;
  ndc.x /= uAspect;
  ndc.y += uShiftY;
  gl_Position = vec4(ndc, 0.0, 1.0);

  // Màu + độ sáng theo loại hạt.
  float tw = 0.75 + 0.25 * sin(uT * (1.0 + aSeed.w * 2.0) + aSeed.x * 6.283);
  vec3 cyan = vec3(0.10, 0.85, 1.00), ice = vec3(0.78, 0.95, 1.00), amber = vec3(1.00, 0.55, 0.12), gold = vec3(1.00, 0.82, 0.45);
  vec3 col; float lum; float size; vSoft = 1.0;
  if (k < 0.5) {
    float nz = rotY(nrm, uYaw).z;
    float rim = 1.0 - abs(nz);
    lum = nz > 0.0 ? 0.42 + 0.75 * rim * rim : 0.16 + 0.2 * rim;                  // mặt trước sáng, viền sáng nhất
    col = mix(cyan, ice, rim * 0.6);
    float face = exp(-pow((aPos.y - 0.41) / 0.10, 2.0) - pow(aPos.x / 0.12, 2.0)) * smoothstep(0.0, 0.07, aPos.z) * step(0.27, aPos.y);
    col = mix(col, mix(amber, gold, 0.30), clamp(face * 1.6, 0.0, 1.0) * min(1.0, uCore));
    lum += face * 2.1 * uCore * (1.0 + uLevel * 0.8);
    float ys = 0.27 + (0.5 + 0.5 * sin(uT * 1.3)) * 0.40;                          // tia quét khi nghĩ
    float sc = (1.0 - smoothstep(0.0, 0.014, abs(aPos.y - ys))) * step(0.27, aPos.y) * uScan;
    lum += sc * 1.3; col = mix(col, vec3(1.0), sc * 0.6);
    size = 1.5;
  } else if (k < 1.5) { col = mix(amber, gold, aSeed.z); lum = 0.28 * uCore * (1.0 + uLevel * 0.9); size = 1.6; }
  else if (k < 2.5) { col = mix(amber, gold, aSeed.z * 0.5); lum = 0.75 * uCore * tw; size = 1.7; }
  else if (k < 3.5) { col = amber; lum = 0.07 * uCore * (1.0 + uLevel * 1.4); size = 30.0 + aSeed.z * 30.0; vSoft = 2.6; }
  else if (k < 4.5) { col = mix(cyan, ice, aSeed.z); lum = 0.30 * tw; size = 1.3; }
  else if (k < 5.5) { col = mix(cyan, vec3(0.05, 0.35, 0.65), aSeed.z * 0.45); lum = (0.80 + 0.35 * tw) * (1.0 + aPos.z * 0.25); size = 1.6; }
  else { col = mix(amber, gold, aSeed.z); lum = 0.95 * tw; size = 1.8; }
  col = mix(col, vec3(1.0, 0.30, 0.25), uRed * 0.75);
  float flight = p < 1.0 ? (0.45 + 0.55 * p) * (1.0 + 3.2 * p * (1.0 - p)) : 1.0;  // vệt sao chổi sáng khi bay
  vC = col * lum * uDim * flight * (p > 0.002 || land ? 1.0 : 0.0);
  gl_PointSize = max(1.0, size * uSize * uPR * (3.1 / z));
}`;

  const FS = `#version 300 es
precision highp float;
in vec3 vC; in float vSoft; out vec4 o;
void main(){
  float r = length(gl_PointCoord - vec2(0.5)) * 2.0;
  if (r > 1.0) discard;
  float a = pow(1.0 - r, vSoft) ;
  vec3 c = vC * a;
  o = vec4(c, clamp(max(c.r, max(c.g, c.b)), 0.0, 1.0));
}`;

  // Lớp phủ toàn khung: vòng sóng quanh đầu (nghe), vòng chạm (pulse), quầng lõi.
  const OVS = `#version 300 es
in vec2 aQ; out vec2 vUv;
void main(){ vUv = aQ * 0.5 + 0.5; gl_Position = vec4(aQ, 0.0, 1.0); }`;
  const OFS = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform vec2 uHead; uniform float uAspect, uT, uRipple, uCore, uLevel, uRed, uDim, uAsm, uIntro;
uniform vec4 uRip[4];
void main(){
  vec2 q = vUv * 2.0 - 1.0;
  vec2 d = (q - uHead) * vec2(uAspect, 1.0);
  float r = length(d);
  vec3 col = vec3(0.0);
  // Vòng sóng đồng tâm khi nghe: vạch mảnh trôi ra ngoài, mờ dần theo bán kính.
  float rings = smoothstep(0.975, 1.0, fract(r * 5.0 - uT * 0.55)) * smoothstep(0.30, 0.42, r) * exp(-r * 1.3);
  col += vec3(0.10, 0.80, 1.00) * rings * uRipple * 0.55;
  // Vòng chạm (pulse) từ cử chỉ tay hoặc nhịp nói.
  for (int i = 0; i < 4; i++) {
    vec4 rp = uRip[i];
    if (rp.w < 0.5) continue;
    float rr = length((q - rp.xy) * vec2(uAspect, 1.0));
    float R = rp.z * 0.9;
    col += vec3(0.10, 0.86, 1.0) * exp(-pow((rr - R) * 140.0, 2.0)) * (1.0 - rp.z / 2.0) * 0.20;
  }
  // Quầng sáng lõi cam phía sau mặt.
  float glow = exp(-dot(d - vec2(0.0, -0.02), d - vec2(0.0, -0.02)) * 22.0);
  col += mix(vec3(1.0, 0.45, 0.08), vec3(1.0, 0.3, 0.25), uRed) * glow * (0.10 + 0.12 * uLevel) * uCore * uAsm * (1.0 - uIntro);
  // Đốm sáng nơi hạt phóng ra lúc lắp ráp (dưới chân, giữa khung).
  vec2 sd = (q - vec2(0.0, -0.88)) * vec2(uAspect, 1.0);
  col += vec3(0.55, 0.95, 1.0) * exp(-dot(sd, sd) * 90.0) * sin(clamp(uAsm, 0.0, 1.0) * 3.14159) * 0.9;
  vec3 c = col * uDim;
  o = vec4(c, clamp(max(c.r, max(c.g, c.b)), 0.0, 1.0));
}`;

  // ---------------------------------------------------------------- lớp chính
  class JoyceHumanoidQuantum {
    constructor(host, options = {}) {
      if (!host || !host.appendChild) throw new TypeError('A mount HTMLElement is required');
      this.host = host; this.options = options;
      this.state = 'idle'; this.level = 0; this.externalLevel = 0; this.levelAt = -Infinity;
      this.running = false; this.paused = false; this.disposed = false; this.loaded = false;
      this.pointer = { x: 0, y: 0 }; this.yaw = 0; this.pitch = 0; this.ripples = [];
      this.listeners = [];
      this.look = Object.assign({}, LOOK.idle);
      const mq = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : null;
      this.reduced = options.reducedMotion ?? !!(mq && mq.matches);
      const dprMax = options.maxDpr || 1.5;
      this.tier = dprMax >= 1.5 ? 'high' : dprMax >= 1.25 ? 'balanced' : 'safe';

      this.root = document.createElement('section');
      this.root.className = 'jh jq';
      this.root.setAttribute('aria-label', 'Joyce: nhân vật hạt ánh sáng');
      this.intro = options.introOnly === true;
      if (this.intro) { this.root.className = 'jq-intro'; this.root.setAttribute('aria-hidden', 'true'); }
      this.root.innerHTML = this.intro ? '<canvas class="jh-gl" aria-hidden="true"></canvas><div class="jh-status" hidden></div><div class="jh-top" hidden></div><div class="jh-notice" hidden></div>' :
        '<canvas class="jh-gl" aria-hidden="true"></canvas>' +
        '<div class="jh-top" hidden><button data-action="exit" aria-label="Thoát lớp nhìn 3D">EXIT</button>' +
        '<button data-action="train" aria-label="Dạy cử chỉ tay">🎓 DẠY</button>' +
        '<button data-action="gesture" aria-pressed="false" aria-label="Bật tắt camera cử chỉ tay">✋ HAND CAM</button></div>' +
        '<div class="jh-status" role="status" aria-live="polite"></div>' +
        '<div class="jh-notice" role="status" hidden></div>';
      host.appendChild(this.root);
      this.$ = s => this.root.querySelector(s);
      this.canvas = this.$('.jh-gl'); this.status = this.$('.jh-status');

      this.listen(this.root, 'click', e => {
        const b = e.target.closest('button');
        if (b) { this.action(b.dataset.action); return; }
        if (this.running) {
          const r = this.root.getBoundingClientRect();
          this.pulse((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
        }
      });
      this.listen(this.root, 'pointermove', e => {
        const r = this.root.getBoundingClientRect();
        this.pointer = { x: clamp((e.clientX - r.left) / r.width) * 2 - 1, y: clamp((e.clientY - r.top) / r.height) * 2 - 1 };
      });
      this.listen(this.root, 'pointerleave', () => { this.pointer = { x: 0, y: 0 }; });
      this.listen(this.root, 'keydown', e => { if (e.key === 'Escape') this.exit(); });
      this.listen(document, 'visibilitychange', () => {
        if (document.hidden) { cancelAnimationFrame(this.raf); this.lastFrame = 0; }
        else if (this.running && !this.paused) this.raf = requestAnimationFrame(t => this.frame(t));
      });
      this.listen(this.canvas, 'webglcontextlost', e => { e.preventDefault(); cancelAnimationFrame(this.raf); this.gl = null; });
      this.listen(this.canvas, 'webglcontextrestored', () => { if (this.initGL() && this.running && !this.paused) this.raf = requestAnimationFrame(t => this.frame(t)); });
      if (mq && mq.addEventListener) this.listen(mq, 'change', e => { if (options.reducedMotion === undefined) this.reduced = e.matches; });
      if (global.ResizeObserver) { this.observer = new ResizeObserver(() => this.resize()); this.observer.observe(host); }
      this.resize();
      this.ready = Promise.resolve().then(() => {
        try { this.loaded = this.initGL(); }
        catch (err) { this.loaded = false; this.report(err); }
        if (this.loaded && options.autoStart) this.enter();
        return this.loaded;
      });
    }

    listen(t, ev, fn) { t.addEventListener(ev, fn); this.listeners.push(() => t.removeEventListener(ev, fn)); }
    report(error) { try { this.options.onError && this.options.onError(error); } catch (e) { /* bỏ qua */ }
      this.root.dispatchEvent(new CustomEvent('joyce-avatar:error', { detail: { message: error && error.message } })); }

    initGL() {
      const gl = this.canvas.getContext('webgl2', { alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: 'high-performance' });
      if (!gl) return false;
      this.gl = gl;
      const sh = (type, src) => {
        const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader');
        return s;
      };
      const link = (vs, fs) => {
        const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
        gl.linkProgram(p); if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'link');
        return p;
      };
      this.prog = link(VS, FS);
      this.oprog = link(OVS, OFS);
      this.u = {}; this.ou = {};
      ['uShiftY', 'uT', 'uAsm', 'uPR', 'uSize', 'uAspect', 'uFit', 'uLevel', 'uYaw', 'uPitch', 'uMotion', 'uAgit', 'uSwirl', 'uScan',
       'uCore', 'uGlitch', 'uWave', 'uDim', 'uRed', 'uDissolve', 'uLean'].forEach(n => { this.u[n] = gl.getUniformLocation(this.prog, n); });
      ['uHead', 'uAspect', 'uT', 'uRipple', 'uCore', 'uLevel', 'uRed', 'uDim', 'uAsm', 'uRip', 'uIntro'].forEach(n => { this.ou[n] = gl.getUniformLocation(this.oprog, n); });

      this.scene = buildScene(BUDGET[this.tier]);
      this.vao = gl.createVertexArray(); gl.bindVertexArray(this.vao);
      this.bufs = [];
      [['aPos', this.scene.pos, 3], ['aSpawn', this.scene.spawn, 3], ['aSeed', this.scene.seed, 4], ['aKind', this.scene.kind, 1]].forEach(([name, data, size]) => {
        const loc = gl.getAttribLocation(this.prog, name); if (loc < 0) return;
        const bo = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bo); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0); this.bufs.push(bo);
      });
      this.ovao = gl.createVertexArray(); gl.bindVertexArray(this.ovao);
      const qb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, qb);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
      const ql = gl.getAttribLocation(this.oprog, 'aQ'); gl.enableVertexAttribArray(ql); gl.vertexAttribPointer(ql, 2, gl.FLOAT, false, 0, 0);
      this.bufs.push(qb);
      gl.bindVertexArray(null);
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); gl.disable(gl.DEPTH_TEST);
      gl.clearColor(0.0, 0.004, 0.012, this.intro ? 0.0 : 1.0);
      this.resize();
      return true;
    }

    resize() {
      const r = this.host.getBoundingClientRect();
      this.w = Math.max(1, r.width); this.h = Math.max(1, r.height);
      this.dpr = Math.min(global.devicePixelRatio || 1, this.options.maxDpr || 1.5);
      this.canvas.width = Math.round(this.w * this.dpr); this.canvas.height = Math.round(this.h * this.dpr);
      if (this.gl) this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }

    action(a) {
      if (a === 'exit') this.exit();
      else if (a === 'gesture') { if (this.options.onGestureRequest) this.options.onGestureRequest(); }
      else if (a === 'train') { if (this.options.onTrainRequest) this.options.onTrainRequest(); }
    }
    enter() {
      if (!this.loaded || this.disposed) return;
      this.running = true; this.paused = false;
      this.$('.jh-top').hidden = false;
      this.replay();
    }
    exit() {
      this.running = false; cancelAnimationFrame(this.raf);
      this.$('.jh-top').hidden = true; this.status.textContent = '';
      if (this.options.onExit) this.options.onExit();
      this.root.dispatchEvent(new CustomEvent('joyce-avatar:exit'));
    }
    /** Chạy lại cảnh xuất hiện (hạt bay ra từ đốm sáng rồi ghép thành hình). */
    replay() {
      if (!this.running || this.disposed) return;
      cancelAnimationFrame(this.raf);
      this.startedAt = performance.now(); this.lastFrame = 0; this.ripples = []; this.ignited = false;
      this.raf = requestAnimationFrame(t => this.frame(t));
    }
    setState(state) {
      if (!STATES.includes(state)) throw new RangeError('Unknown avatar state: ' + state);
      if (this.disposed) return;
      this.state = state;
      if (this.options.onStateChange) this.options.onStateChange(state);
      this.root.dispatchEvent(new CustomEvent('joyce-avatar:state', { detail: { state } }));
    }
    setLevel(level) { this.externalLevel = clamp(Number(level)); this.levelAt = performance.now(); }
    /** Kit cử chỉ tay lái hướng nhìn: -1..1 mỗi trục, 0 là chính giữa. */
    setAttention(x = 0, y = 0) { this.pointer = { x: clamp(x, -1, 1), y: clamp(y, -1, 1) }; }
    /** Vòng sóng tại vị trí màn hình (0..1, gốc trên trái). */
    pulse(x = .5, y = .45) {
      this.ripples.push({ x: clamp(x), y: clamp(y), at: performance.now() });
      if (this.ripples.length > 4) this.ripples.shift();
    }
    notice(message) {
      if (this.disposed) return;
      const n = this.$('.jh-notice'); n.textContent = message; n.hidden = false;
      clearTimeout(this.noticeTimer); this.noticeTimer = setTimeout(() => { n.hidden = true; }, 6000);
    }

    frame(now) {
      if (this.disposed || !this.running || this.paused || document.hidden) return;
      this.raf = requestAnimationFrame(t => this.frame(t));
      const fps = this.options.fps || 40;
      if (this.lastFrame && now - this.lastFrame < 1000 / fps) return;
      const dt = this.lastFrame ? Math.min(0.1, (now - this.lastFrame) / 1000) : 1 / fps;
      this.lastFrame = now;
      const gl = this.gl; if (!gl) return;
      const t = now / 1000;
      const dur = this.options.assemblyDuration || 4.6;
      const asm = this.reduced ? 1 : clamp((now - this.startedAt) / 1000 / dur);

      // Mức âm: tiếng thật từ app (mic/TTS) nếu mới có; không thì nhịp nhẹ theo chế độ.
      let target = 0;
      if (now - this.levelAt < 1200) target = this.externalLevel;
      else if (this.state === 'thinking') target = .10 + .06 * Math.sin(t * 2);
      else if (this.state === 'reconnecting' || this.state === 'error') target = .06 + .05 * Math.sin(t * 1.6);
      this.level += (target - this.level) * .16;

      // Nội suy tham số chế độ.
      const goal = LOOK[this.state] || LOOK.idle, k = Math.min(1, dt * 4);
      for (const key in goal) this.look[key] = lerp(this.look[key], goal[key], k);

      // Hướng nhìn: bám con trỏ/bàn tay + đung đưa nhẹ.
      const motion = this.reduced ? 0 : 1;
      const yawGoal = (this.pointer.x * 0.55 + Math.sin(t * 0.37) * 0.10) * motion;
      const pitchGoal = (this.pointer.y * 0.16) * motion;
      this.yaw += (yawGoal - this.yaw) * .07; this.pitch += (pitchGoal - this.pitch) * .07;

      // Nhịp nói: mỗi lần tiếng vọt lên -> một vòng sóng từ miệng.
      const fit = Math.min(1, 1.25 * (this.w / this.h));
      const headY = (0.44 - 0.22) * 6.4 * fit / 3.06;           // toạ độ NDC của đầu (cùng phép chiếu shader)
      if (this.state === 'speaking' && this.level > .48 && now - (this.beatAt || 0) > 650) {
        this.beatAt = now; this.pulse(.5, .5 - headY / 2 + 0.02);
      }
      if (asm >= 1 && !this.ignited && !this.intro) { this.ignited = true; this.pulse(.5, .5 - headY / 2); }

      const L = this.look;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      gl.clear(gl.COLOR_BUFFER_BIT);

      // Lớp phủ trước (nằm dưới hạt khi cộng sáng - thứ tự không đổi kết quả cộng).
      gl.useProgram(this.oprog); gl.bindVertexArray(this.ovao);
      const ou = this.ou;
      gl.uniform2f(ou.uHead, 0, headY); gl.uniform1f(ou.uAspect, this.w / this.h); gl.uniform1f(ou.uT, t);
      gl.uniform1f(ou.uRipple, L.ripple * motion); gl.uniform1f(ou.uCore, L.core); gl.uniform1f(ou.uLevel, this.level);
      gl.uniform1f(ou.uRed, L.red); gl.uniform1f(ou.uDim, L.dim); gl.uniform1f(ou.uAsm, asm);
      const rip = new Float32Array(16);
      this.ripples = this.ripples.filter(q => now - q.at < 2000);
      this.ripples.forEach((q, i) => { rip[i * 4] = q.x * 2 - 1; rip[i * 4 + 1] = 1 - q.y * 2; rip[i * 4 + 2] = (now - q.at) / 1000; rip[i * 4 + 3] = 1; });
      gl.uniform4fv(ou.uRip, rip);
      gl.uniform1f(ou.uIntro, this.intro ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      gl.useProgram(this.prog); gl.bindVertexArray(this.vao);
      const u = this.u;
      gl.uniform1f(u.uShiftY, this.options.shiftY || 0);   // canh hình hạt khớp hình nền khác (cảnh mở đầu)
      gl.uniform1f(u.uT, t); gl.uniform1f(u.uAsm, asm); gl.uniform1f(u.uPR, this.dpr);
      gl.uniform1f(u.uSize, Math.min(this.w, this.h) / 760); gl.uniform1f(u.uAspect, this.w / this.h);
      gl.uniform1f(u.uFit, fit); gl.uniform1f(u.uLevel, this.level);
      gl.uniform1f(u.uYaw, this.yaw); gl.uniform1f(u.uPitch, this.pitch); gl.uniform1f(u.uMotion, motion);
      gl.uniform1f(u.uAgit, L.agit); gl.uniform1f(u.uSwirl, L.swirl); gl.uniform1f(u.uScan, L.scan * motion);
      gl.uniform1f(u.uCore, L.core); gl.uniform1f(u.uGlitch, L.glitch); gl.uniform1f(u.uWave, L.wave);
      gl.uniform1f(u.uDim, L.dim); gl.uniform1f(u.uRed, L.red); gl.uniform1f(u.uDissolve, L.dissolve); gl.uniform1f(u.uLean, L.lean);
      // Cảnh mở đầu chồng lên giao diện khác: chỉ vẽ hình người, bỏ dãy núi (nằm cuối mảng).
      gl.drawArrays(gl.POINTS, 0, this.intro ? this.scene.n - this.scene.counts.land : this.scene.n);
      gl.bindVertexArray(null);

      const msg = asm < 1 ? 'ĐANG LẮP RÁP... ' + Math.round(asm * 100) + '%' : (STATE_LABEL[this.state] || this.state.toUpperCase());
      if (msg !== this.status.textContent) this.status.textContent = msg;
      if (this.status.dataset.state !== this.state) this.status.dataset.state = this.state;
    }

    pause() { this.paused = true; cancelAnimationFrame(this.raf); }
    resume() {
      if (this.disposed || !this.running || !this.paused) return;
      this.paused = false; this.lastFrame = 0; this.raf = requestAnimationFrame(t => this.frame(t));
    }
    dispose() {
      if (this.disposed) return;
      this.disposed = true; this.running = false; cancelAnimationFrame(this.raf); clearTimeout(this.noticeTimer);
      if (this.observer) this.observer.disconnect();
      this.listeners.forEach(off => off());
      this.root.dispatchEvent(new CustomEvent('joyce-avatar:dispose'));
      const gl = this.gl;
      if (gl) { (this.bufs || []).forEach(b => gl.deleteBuffer(b)); gl.deleteProgram(this.prog); gl.deleteProgram(this.oprog); }
      this.root.remove();
    }
  }

  JoyceHumanoidQuantum.STATES = STATES;
  JoyceHumanoidQuantum.LOOK = LOOK;
  JoyceHumanoidQuantum.BUDGET = BUDGET;
  JoyceHumanoidQuantum.buildScene = buildScene;
  global.JoyceHumanoidQuantum = JoyceHumanoidQuantum;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { JoyceHumanoidQuantum, buildScene, LOOK, BUDGET, STATES, STATE_LABEL, VS, FS, OVS, OFS };
  }
})(typeof window !== 'undefined' ? window : globalThis);
