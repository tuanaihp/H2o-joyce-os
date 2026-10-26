/* ============================================================================
 * JOYCE BACKDROPS - cảnh nền thủ tục cho lớp nhìn 3D Joyce (1.0.0).
 *
 * Mỗi "cảnh" là một hàm vẽ canvas 2D theo đúng phong cách backdrop-v1.webp: nền
 * gần đen, lưới hạt cyan nối gân mảnh, tĩnh mạch cam, bụi sao thưa. Không file
 * ảnh nào phải tải - đổi cảnh là vẽ lại tại máy, nên lệnh giọng ăn ngay lập tức.
 * Cảnh "mountain" vẫn ưu tiên ảnh gốc (asset) vì đó là mặt nhận diện.
 *
 * API: JoyceBackdrops.list() -> [{id, vi, en, asset?}]
 *      JoyceBackdrops.get(id) -> def | null
 *      JoyceBackdrops.render(ctx, id, w, h) - vẽ vào ctx đã có kích thước.
 * ========================================================================== */
(function (global) {
  'use strict';

  const SCENES = [
    { id: 'mountain', vi: 'Dãy núi',      en: 'Mountains',  asset: true },
    { id: 'beach',    vi: 'Bãi biển',     en: 'Beach' },
    { id: 'sunset',   vi: 'Hoàng hôn',    en: 'Sunset' },
    { id: 'sunrise',  vi: 'Bình minh',    en: 'Sunrise' },
    { id: 'planets',  vi: 'Hành tinh',    en: 'Planets' },
    { id: 'milkyway', vi: 'Dải ngân hà',  en: 'Milky Way' },
  ];

  // Bảng màu của Joyce: bầu trời gần đen + cyan băng + cam/gold năng lượng.
  const CYAN = '26,217,255', ICE = '190,240,255', AMBER = '255,154,31',
        GOLD = '255,209,102', VIOLET = '150,120,255', WHITE = '235,245,255';

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
  const lerp = (a, b, k) => a + (b - a) * k;

  function dot(ctx, x, y, r, col, a) {
    ctx.fillStyle = `rgba(${col},${a})`;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
  }
  function link(ctx, ax, ay, bx, by, col, a, w) {
    ctx.strokeStyle = `rgba(${col},${a})`;
    ctx.lineWidth = w || 0.55;
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
  }
  function glow(ctx, x, y, r, col, a) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, `rgba(${col},${a})`);
    g.addColorStop(1, `rgba(${col},0)`);
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function skyFill(ctx, w, h, stops) {
    const g = ctx.createLinearGradient(0, 0, 0, h);
    for (const [p, c] of stops) g.addColorStop(p, c);
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  }

  /** Bụi sao nền: n chấm nhỏ trong vùng, màu pha theo rand. */
  function starDust(ctx, w, h, n, rand, opt) {
    const y0 = (opt && opt.y0) || 0, y1 = (opt && opt.y1) || 1;
    const cols = (opt && opt.cols) || [ICE, CYAN, WHITE];
    for (let i = 0; i < n; i++) {
      const x = rand() * w, y = (y0 + rand() * (y1 - y0)) * h;
      const r = 0.3 + rand() * (opt && opt.big ? 1.3 : 0.8);
      const c = cols[(rand() * cols.length) | 0];
      dot(ctx, x, y, r, c, 0.06 + rand() * 0.5);
    }
  }

  /** Sống núi giả-fbm theo sin, seed ổn định: gợn nhiều quãng tần. */
  function ridgeFn(rand, amp, off) {
    const ph = [], fr = [], am = [];
    let a = 1;
    for (let o = 0; o < 5; o++) { ph.push(rand() * 6.2832); fr.push(1.4 + o * 1.9 + rand()); am.push(a); a *= 0.5; }
    const norm = am.reduce((s, v) => s + v, 0);
    return (t) => {           // t 0..1 ngang màn -> độ cao tương đối -amp..amp
      let s = 0;
      for (let o = 0; o < 5; o++) s += Math.sin(t * fr[o] * 6.2832 + ph[o] + off) * am[o];
      return s / norm * amp;
    };
  }

  /** Lưới hạt quanh một đường sống: chấm trên sống + scatter phía dưới + gân nối
   *  gần nhau (bucket lưới để khỏi O(n²)). */
  function meshRidge(ctx, w, h, spec, rand) {
    const yFn = spec.yFn, base = spec.base, col = spec.col || CYAN;
    const pts = [];
    const step = spec.step || 9;
    for (let x = -step; x <= w + step; x += step) {
      const y = base + yFn(x / w) * h;
      pts.push([x + (rand() - .5) * 4, y + (rand() - .5) * 4]);
      // Tán hạt xuống sườn: mật độ loãng dần theo độ sâu.
      for (let d = 1; d <= (spec.depth || 10); d++) {
        if (rand() > 0.8 - d * 0.07) continue;
        pts.push([x + (rand() - .5) * 22, y + d * (5 + rand() * 7)]);
      }
    }
    // Gân nối láng giềng gần (bucket theo cột để nhanh).
    const cell = 30, grid = new Map();
    for (const p of pts) {
      const gx = (p[0] / cell) | 0, gy = (p[1] / cell) | 0, k = gx + ':' + gy;
      (grid.get(k) || grid.set(k, []).get(k)).push(p);
    }
    for (const p of pts) {
      const gx = (p[0] / cell) | 0, gy = (p[1] / cell) | 0;
      let linked = 0;
      for (let dx = -1; dx <= 1 && linked < 2; dx++) for (let dy = -1; dy <= 1 && linked < 2; dy++) {
        const arr = grid.get((gx + dx) + ':' + (gy + dy));
        if (!arr) continue;
        for (const q of arr) {
          if (q === p || linked >= 2) continue;
          const d2 = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2;
          if (d2 < 26 * 26) { link(ctx, p[0], p[1], q[0], q[1], col, spec.linkA || 0.10); linked++; }
        }
      }
    }
    for (const p of pts) dot(ctx, p[0], p[1], spec.dotR || 0.9, col, spec.dotA || 0.5);
  }

  /** Tĩnh mạch cam chảy dọc sườn (đi bộ ngẫu nhiên, chấm sáng tại khớp). */
  function veins(ctx, w, h, rand, opt) {
    const yFn = opt.yFn, base = opt.base, n = opt.n || 12, col = opt.col || AMBER;
    for (let v = 0; v < n; v++) {
      let x = rand() * w, y = base + yFn(x / w) * h + rand() * 20;
      let px = x, py = y;
      const steps = 16 + (rand() * 26) | 0;
      for (let s = 0; s < steps; s++) {
        x += (rand() - .5) * 26; y += 5 + rand() * 9;
        link(ctx, px, py, x, y, col, 0.30 + rand() * 0.25, 0.8);
        if (rand() < 0.35) dot(ctx, x, y, 0.8 + rand(), col, 0.5 + rand() * 0.4);
        px = x; py = y;
        if (y > h * (opt.to || 0.95)) break;
      }
    }
  }

  /** Đĩa mặt trời/trăng: lõi sáng + quầng lớn. */
  function sunDisc(ctx, x, y, r, core, halo, haloA) {
    glow(ctx, x, y, r * 4.5, halo, haloA);
    glow(ctx, x, y, r * 2.2, halo, haloA * 1.6);
    const g = ctx.createRadialGradient(x, y - r * 0.2, 0, x, y, r);
    g.addColorStop(0, `rgba(${core},1)`); g.addColorStop(0.7, `rgba(${core},0.85)`);
    g.addColorStop(1, `rgba(${halo},0.12)`);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
  }

  /** Vệt phản chiếu trên mặt nước: cột hạt rung ngang, mờ dần xuống dưới. */
  function glints(ctx, x, y0, y1, spread, col, rand) {
    for (let y = y0; y < y1; y += 4 + rand() * 5) {
      const t = (y - y0) / (y1 - y0);
      const n = 1 + (rand() * 3) | 0;
      for (let i = 0; i < n; i++) {
        const gx = x + (rand() - .5) * spread * (0.4 + t * 1.6);
        link(ctx, gx - 2 - rand() * 8, y, gx + 2 + rand() * 8, y, col, (1 - t) * (0.12 + rand() * 0.3), 0.9);
      }
    }
  }

  // ------------------------------------------------------------------ cảnh

  /** Núi (bản thủ tục - dự phòng khi asset gốc không dùng được). */
  function genMountain(ctx, w, h) {
    const rand = mulberry(20261018);
    skyFill(ctx, w, h, [[0, '#010409'], [0.55, '#020608'], [1, '#000204']]);
    starDust(ctx, w, h, 260, rand, { y1: 0.55 });
    const dip = (t) => -Math.cos(t * Math.PI) * 0.5 - 0.5;      // cao ở hai mép, lõm giữa
    const far = ridgeFn(rand, 0.10, 1.3), near = ridgeFn(rand, 0.08, 4.7);
    const farY = (t) => 0.56 + far(t) + dip(t) * -0.16;
    const nearY = (t) => 0.70 + near(t) + dip(t) * -0.13;
    meshRidge(ctx, w, h, { yFn: farY, base: 0, depth: 12, col: CYAN, dotA: 0.38, linkA: 0.09 }, rand);
    meshRidge(ctx, w, h, { yFn: nearY, base: 0, depth: 9, col: CYAN, dotA: 0.55, dotR: 1.1, linkA: 0.13 }, rand);
    veins(ctx, w, h, rand, { yFn: nearY, base: 0, n: 12, to: 0.97 });
    veins(ctx, w, h, rand, { yFn: farY, base: 0, n: 6, to: 0.85, col: GOLD });
    // Chân đổ bóng lên để nhân vật nổi lên.
    const g = ctx.createLinearGradient(0, h * 0.8, 0, h);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.65)');
    ctx.fillStyle = g; ctx.fillRect(0, h * 0.8, w, h * 0.2);
  }

  /** Bãi biển: chân trời phát sáng, sóng lưới hạt xếp lớp, trăng đổ vệt cam. */
  function genBeach(ctx, w, h) {
    const rand = mulberry(1977);
    skyFill(ctx, w, h, [[0, '#01040a'], [0.5, '#02070c'], [0.58, '#032028'], [0.6, '#02141a'], [1, '#000203']]);
    starDust(ctx, w, h, 300, rand, { y1: 0.5 });
    const hz = 0.585;
    // Chân trời: vạch cyan mảnh + quầng mờ hai phía.
    glow(ctx, w * 0.5, hz * h, w * 0.62, CYAN, 0.05);
    link(ctx, 0, hz * h, w, hz * h, ICE, 0.35, 1.1);
    link(ctx, 0, hz * h + 2, w, hz * h + 2, CYAN, 0.18, 2.4);
    // Trăng nhỏ trên phải + vệt sáng đổ xuống mặt nước.
    const mx = w * 0.74, my = h * 0.20;
    sunDisc(ctx, mx, my, h * 0.035, ICE, CYAN, 0.10);
    glints(ctx, mx, hz * h + 6, h * 0.94, 46, AMBER, rand);
    // Sóng: các hàng gợn sin, sâu dần; đợt gần đặc và sáng hơn.
    for (let row = 0; row < 9; row++) {
      const t = row / 8, y = lerp(hz + 0.015, 0.94, t * t * 0.85 + t * 0.15) * h;
      const amp = lerp(2, 12, t), lam = lerp(60, 170, t), ph = rand() * 6.28;
      const a = lerp(0.55, 0.12, t);
      const pts = [];
      for (let x = 0; x <= w; x += 7) {
        const yy = y + Math.sin(x / lam * 6.2832 + ph) * amp + (rand() - .5) * 2;
        pts.push([x, yy]);
        if (rand() < 0.85) dot(ctx, x, yy, 0.7 + rand() * 0.7, row < 3 ? ICE : CYAN, a * (0.5 + rand() * 0.6));
      }
      for (let i = 1; i < pts.length; i += 2)
        link(ctx, pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1], CYAN, a * 0.16);
      // Bọt sóng đỉnh: vài đốm trắng tản trên đỉnh gợn.
      if (row > 1) for (let b = 0; b < 8; b++) {
        const bx = rand() * w, by = y + Math.sin(bx / lam * 6.2832 + ph) * amp - 2;
        dot(ctx, bx, by, 0.8 + rand(), WHITE, a * 0.7);
      }
    }
    // Cát: vệt hạt ấm thưa ở đáy.
    for (let i = 0; i < 130; i++) dot(ctx, rand() * w, (0.94 + rand() * 0.05) * h, 0.4 + rand() * 0.9, rand() < 0.4 ? AMBER : CYAN, 0.10 + rand() * 0.3);
  }

  /** Hoàng hôn: mặt trời cam lớn chạm chân trời, dãy núi tối in bóng. */
  function genSunset(ctx, w, h) {
    const rand = mulberry(2408);
    skyFill(ctx, w, h, [[0, '#02040a'], [0.42, '#0a0806'], [0.58, '#2a1204'], [0.66, '#1c0c03'], [1, '#050302']]);
    starDust(ctx, w, h, 140, rand, { y1: 0.32 });
    const hz = 0.64, sx = w * 0.5, sy = hz * h - h * 0.015;
    sunDisc(ctx, sx, sy, h * 0.085, GOLD, AMBER, 0.16);
    // Rặng mây ngang mỏng cắt qua đĩa trời.
    for (let i = 0; i < 5; i++) {
      const cy = sy - h * 0.10 + i * h * 0.035 + (rand() - .5) * 6;
      const cw = w * (0.18 + rand() * 0.30), cx = sx + (rand() - .5) * w * 0.5;
      link(ctx, cx - cw / 2, cy, cx + cw / 2, cy, AMBER, 0.10 + rand() * 0.10, 3 + rand() * 4);
    }
    // Sống núi đen in bóng: gần như không màu, chỉ gờ trên có viền cam mỏng.
    const ridge = ridgeFn(rand, 0.07, 2.2);
    const yR = (t) => (0.70 + ridge(t) + Math.cos(t * Math.PI) * -0.05) * h;
    ctx.fillStyle = '#030202';
    ctx.beginPath(); ctx.moveTo(0, h);
    for (let x = 0; x <= w; x += 6) ctx.lineTo(x, yR(x / w));
    ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
    // Viền sống cháy cam (mặt trời hắt lưng) + gân mảnh.
    let px = 0, py = yR(0);
    for (let x = 2; x <= w; x += 4) {
      const y = yR(x / w);
      link(ctx, px, py, x, y, AMBER, 0.10 + 0.25 * Math.max(0, 1 - Math.abs(x / w - 0.5) * 3), 0.8);
      if (rand() < 0.4) dot(ctx, x, y, 0.6 + rand() * 0.6, AMBER, 0.3 + rand() * 0.4);
      px = x; py = y;
    }
    // Vệt phản chiếu mỏng trên mặt đất/sóng xa.
    glints(ctx, sx, hz * h + 8, h * 0.8, 30, GOLD, rand);
  }

  /** Bình minh: mặt trời vàng-ấm vừa lên, quầng cam lan rộng từ chân trời,
   *  sương ngang vàng nhạt, đồi thấp gờ cyan - khác hoàng hôn ở chỗ sáng hơn,
   *  mặt trời cao hơn và tông chuyển cyan+gold thay vì cam đậm. */
  function genSunrise(ctx, w, h) {
    const rand = mulberry(515);
    skyFill(ctx, w, h, [[0, '#020810'], [0.30, '#072a30'], [0.46, '#0d4a52'], [0.58, '#0f5a5e'], [0.72, '#082c30'], [1, '#02100f']]);
    starDust(ctx, w, h, 160, rand, { y1: 0.26 });
    const sx = w * 0.5, sy = h * 0.46;
    // Vầng ấm khổng lồ hắt từ chân trời lên - đặc trưng của bình minh.
    glow(ctx, sx, h * 0.62, w * 0.55, AMBER, 0.10);
    glow(ctx, sx, h * 0.60, w * 0.30, GOLD, 0.12);
    sunDisc(ctx, sx, sy, h * 0.062, GOLD, AMBER, 0.22);
    glow(ctx, sx, sy, h * 0.16, GOLD, 0.30);
    // Tia sáng mỏng toả xuống mặt đất.
    for (let i = 0; i < 9; i++) {
      const a = Math.PI / 2 + (i / 8 - 0.5) * 1.9;
      const x1 = sx + Math.cos(a) * h * 0.08, y1 = sy + Math.sin(a) * h * 0.08;
      const x2 = sx + Math.cos(a) * h * 0.55, y2 = sy + Math.sin(a) * h * 0.55;
      link(ctx, x1, y1, x2, y2, GOLD, 0.05 + rand() * 0.05, 1.6 + rand() * 2);
    }
    // Sương: dải sáng mỏng ngang, ấm gần mặt trời.
    for (let i = 0; i < 4; i++) {
      const my = (0.55 + i * 0.05 + rand() * 0.02) * h;
      glow(ctx, w * (0.2 + rand() * 0.6), my, w * 0.30, GOLD, 0.045);
      link(ctx, 0, my, w, my, ICE, 0.07, 5 + rand() * 7);
    }
    // Đồi thấp in bóng mềm (sáng trước nên chỉ gờ cyan nhạt).
    const ridge = ridgeFn(rand, 0.05, 3.9);
    const yR = (t) => (0.74 + ridge(t)) * h;
    ctx.fillStyle = '#02100e';
    ctx.beginPath(); ctx.moveTo(0, h);
    for (let x = 0; x <= w; x += 6) ctx.lineTo(x, yR(x / w));
    ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
    let px = 0, py = yR(0);
    for (let x = 3; x <= w; x += 5) {
      const y = yR(x / w);
      link(ctx, px, py, x, y, CYAN, 0.16, 0.7);
      if (rand() < 0.3) dot(ctx, x, y, 0.7, CYAN, 0.4);
      px = x; py = y;
    }
    veins(ctx, w, h, rand, { yFn: (t) => yR(t) / h - 0.02, base: 0, n: 8, to: 0.94, col: GOLD });
    // Chim sớm: vài nét chữ v nhỏ.
    ctx.strokeStyle = `rgba(${ICE},0.45)`; ctx.lineWidth = 0.9;
    for (let i = 0; i < 9; i++) {
      const bx = w * (0.15 + rand() * 0.7), by = h * (0.18 + rand() * 0.18), s = 3 + rand() * 4;
      ctx.beginPath(); ctx.moveTo(bx - s, by); ctx.lineTo(bx, by - s * 0.7); ctx.lineTo(bx + s, by); ctx.stroke();
    }
  }

  /** Hành tinh: một hành tinh lớn có vành rõ + vệ tinh nhỏ, nền sao dày. Đĩa
   *  hành tinh phải ĐỌC được là một khối tròn: viền liền + ruột đặc + terminator
   *  (nửa sáng/nửa tối), chứ không phải đám chấm loãng. */
  function genPlanets(ctx, w, h) {
    const rand = mulberry(777);
    skyFill(ctx, w, h, [[0, '#01030a'], [0.6, '#020610'], [1, '#00020a']]);
    starDust(ctx, w, h, 650, rand, { big: true });
    glow(ctx, w * 0.30, h * 0.36, w * 0.30, VIOLET, 0.04);
    glow(ctx, w * 0.68, h * 0.62, w * 0.22, CYAN, 0.035);

    // ---- Hành tinh chính: khối tròn dựng từ lưới hạt, có vành nghiêng.
    const cx = w * 0.34, cy = h * 0.34, R = Math.min(w, h) * 0.16;
    glow(ctx, cx, cy, R * 3.4, CYAN, 0.10);
    // Ruột đĩa: hạt đặc, phân nửa sáng/tối theo góc tới nguồn sáng (trên-trái).
    for (let i = 0; i < 1500; i++) {
      const a = rand() * 6.2832, rr = Math.sqrt(rand()) * R;
      const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr;
      const lit = 0.45 + 0.55 * Math.cos(Math.atan2(y - cy, x - cx) + 2.35);   // terminator
      const edge = rr > R * 0.88 ? 0.5 : 0;                                  // sáng gờ
      dot(ctx, x, y, 0.5 + rand() * 0.9, lit > 0.72 ? ICE : CYAN,
          Math.min(0.95, 0.14 + 0.62 * lit + edge * lit) * (0.5 + rand() * 0.5));
    }
    // Viền đĩa liền (đọc được mặt cầu) + điểm sáng gờ phía sáng.
    ctx.strokeStyle = `rgba(${ICE},0.55)`; ctx.lineWidth = 1.0;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 6.2832); ctx.stroke();
    ctx.strokeStyle = `rgba(${CYAN},0.20)`; ctx.lineWidth = 3.2;
    ctx.beginPath(); ctx.arc(cx, cy, R + 1.6, 0, 6.2832); ctx.stroke();
    // Vành: hai dải ellipse nghiêng -19°, hạt đặc, sáng phía trước.
    const tilt = -0.33;
    for (const [rr0, rr1, col, base] of [[1.45, 1.62, AMBER, 0.75], [1.75, 1.95, GOLD, 0.5]]) {
      for (let i = 0; i < 700; i++) {
        const a = rand() * 6.2832, rr = R * (rr0 + rand() * (rr1 - rr0));
        const ex = Math.cos(a) * rr, ey = Math.sin(a) * rr * 0.36;
        const x = cx + ex * Math.cos(tilt) - ey * Math.sin(tilt);
        const y = cy + ex * Math.sin(tilt) + ey * Math.cos(tilt);
        // Nửa vành đi SAU hành tinh (bị đĩa che) thì tối mờ - kiểm tra bằng toạ độ.
        const behind = Math.sin(a) < 0 && Math.hypot(x - cx, y - cy) < R * 1.02;
        if (behind) continue;
        const front = Math.hypot(x - cx, y - cy) > R;
        dot(ctx, x, y, 0.4 + rand() * 0.9, col, (front ? base : base * 0.4) * (0.4 + rand() * 0.6));
      }
    }
    // ---- Vệ tinh nhỏ dưới phải, tông cam.
    const mx = w * 0.74, my = h * 0.64, mr = Math.min(w, h) * 0.05;
    glow(ctx, mx, my, mr * 4.5, AMBER, 0.08);
    for (let i = 0; i < 260; i++) {
      const a = rand() * 6.2832, rr = Math.sqrt(rand()) * mr;
      const lit = 0.45 + 0.55 * Math.cos(Math.atan2(my + Math.sin(a) * rr - my, mx + Math.cos(a) * rr - mx) + 2.35);
      dot(ctx, mx + Math.cos(a) * rr, my + Math.sin(a) * rr, 0.5 + rand() * 0.7,
          lit > 0.7 ? GOLD : AMBER, (0.2 + 0.6 * lit) * (0.5 + rand() * 0.5));
    }
    ctx.strokeStyle = `rgba(${AMBER},0.5)`; ctx.lineWidth = 0.9;
    ctx.beginPath(); ctx.arc(mx, my, mr, 0, 6.2832); ctx.stroke();
    // Sao băng nhỏ.
    for (let i = 0; i < 4; i++) {
      const x = rand() * w, y = rand() * h * 0.45, l = 16 + rand() * 30, an = 0.6 + rand() * 0.4;
      link(ctx, x, y, x + l * Math.cos(an), y + l * Math.sin(an), ICE, 0.4, 0.9);
      dot(ctx, x, y, 1.3, WHITE, 0.85);
    }
  }

  /** Dải ngân hà: dải sao chéo đặc dần về tâm + tinh vân tím-cyan - kiểu Lõi nước. */
  function genMilkyway(ctx, w, h) {
    const rand = mulberry(51000);
    skyFill(ctx, w, h, [[0, '#010208'], [0.5, '#020410'], [1, '#010208']]);
    const diag = Math.hypot(w, h);
    // Dải chéo qua tâm, nghiêng ~-24°; t là vị trí dọc dải, d là lệch ngang.
    const ang = -0.42, ca = Math.cos(ang), sa = Math.sin(ang);
    const cx = w * 0.5, cy = h * 0.46, bandW = diag * 0.075;
    // Tinh vân: vệt mờ to nằm dọc dải - phải ĐỌC được màng sáng chứ không chỉ
    // là mấy đốm rời, nên xếp chồng dày và ấm hơn quanh lõi.
    for (let i = 0; i < 14; i++) {
      const t = (i / 13 - 0.5) * diag * 0.95, off = (rand() - .5) * bandW * 1.5;
      const x = cx + t * ca - off * sa, y = cy + t * sa + off * ca;
      glow(ctx, x, y, bandW * (1.0 + rand()), rand() < 0.5 ? VIOLET : (rand() < 0.55 ? CYAN : AMBER), 0.045 + rand() * 0.05);
    }
    // Lõi sáng lệch phải (nhân thiên hà) - đốm sáng mạch nhất của cảnh.
    const gx = cx + diag * 0.10 * ca, gy = cy + diag * 0.10 * sa;
    glow(ctx, gx, gy, bandW * 3.0, GOLD, 0.10);
    glow(ctx, gx, gy, bandW * 1.5, WHITE, 0.12);
    // Sao dải: đặc hơn hẳn - mật độ gaussian theo lệch ngang, đông gấp đôi quanh lõi.
    for (let i = 0; i < 4200; i++) {
      const t = (rand() - 0.5) * diag * 1.15;
      const g = (rand() + rand() + rand() - 1.5) / 1.5;         // ~gauss -1..1
      const d = g * bandW;
      const x = cx + t * ca - d * sa + (rand() - .5) * 3, y = cy + t * sa + d * ca + (rand() - .5) * 3;
      if (x < -8 || x > w + 8 || y < -8 || y > h + 8) continue;
      const nearCore = Math.hypot(x - gx, y - gy) < bandW * 1.9 ? 1.8 : 1;
      const col = rand() < 0.60 ? (rand() < 0.5 ? ICE : WHITE) : (rand() < 0.6 ? CYAN : (rand() < 0.5 ? VIOLET : AMBER));
      dot(ctx, x, y, 0.3 + rand() * rand() * 1.6, col, Math.min(1, (0.12 + rand() * 0.75) * nearCore));
    }
    // Sao nền rải + vài sao sáng có quầng.
    starDust(ctx, w, h, 420, rand, { big: true });
    for (let i = 0; i < 26; i++) {
      const x = rand() * w, y = rand() * h;
      glow(ctx, x, y, 4 + rand() * 7, rand() < 0.6 ? ICE : GOLD, 0.25);
      dot(ctx, x, y, 0.8 + rand(), WHITE, 0.85);
    }
    // Vân bụi tối lười qua: vài khe hở (giả lập bằng vệt sao loãng đã tự có).
  }

  const GEN = { mountain: genMountain, beach: genBeach, sunset: genSunset,
                sunrise: genSunrise, planets: genPlanets, milkyway: genMilkyway };

  global.JoyceBackdrops = {
    list() { return SCENES.slice(); },
    get(id) { return SCENES.find(s => s.id === id) || null; },
    /** Vẽ cảnh vào ctx (canvas đã đặt kích thước). Id lạ -> bỏ qua. */
    render(ctx, id, w, h) {
      const fn = GEN[id];
      if (!fn) return false;
      ctx.save();
      try { ctx.clearRect(0, 0, w, h); fn(ctx, w, h); }
      finally { ctx.restore(); }
      return true;
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
