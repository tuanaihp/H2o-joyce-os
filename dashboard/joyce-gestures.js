/* ============================================================================
 * JOYCE GESTURES - đôi tay hạt sáng + bảng hologram cho "3D Joyce" (1.3.24).
 *
 * Ảnh nhân vật là bán thân không có tay, nên tay được DỰNG THÊM bằng hạt cùng phong cách
 * vân xanh, chồng lên ảnh (canvas 2D, cộng sáng). Tay chỉ xuất hiện khi Joyce làm việc:
 *   - Làm task / tìm kiếm (THINKING hoặc vừa có tool_call): hạt tụ thành hai cánh tay từ
 *     dưới vai, luân phiên bấm, vuốt các bảng hologram nổi trước ngực. Bảng hiện đúng việc
 *     đang chạy (tên lệnh từ luồng chat, sự kiện "joyce:avatar-act"), thanh quét, dòng
 *     kết quả hiện dần, vòng chạm ở đầu ngón tay.
 *   - Trả lời (SPEAKING hoặc chữ đang chảy): tay hạ dần, khoa nhẹ theo nhịp giọng; còn một
 *     bảng "ĐANG TRẢ LỜI" với dòng chữ đang soạn.
 *   - Rảnh: tay tan thành hạt, chỉ còn tượng.
 *
 * Toạ độ đặt theo đúng khung ảnh nhân vật (figureRect của apex-humanoid.js: cao
 * min(h*1.01, w*1.6), canh giữa, sát đáy) nên vai và ngực khớp ảnh ở mọi cỡ màn hình.
 * Không gọi model, không mạng; tôn trọng "giảm chuyển động" của hệ điều hành.
 * ========================================================================== */
(function (global) {
  'use strict';

  const clamp = (n, a = 0, b = 1) => Math.max(a, Math.min(b, Number.isFinite(n) ? n : 0));
  const lerp = (a, b, k) => a + (b - a) * k;
  const hash = (n) => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };

  // Vị trí theo khung ảnh (u ngang 0..1, v dọc 0..1 từ đỉnh đầu xuống đáy khung).
  const SHOULDER = { L: [0.30, 0.80], R: [0.70, 0.80] };
  const ELBOW = { L: [0.20, 1.06], R: [0.80, 1.06] };
  // Bảng hologram: [u0, v0, u1, v1, nghiêng]. Trái thấp, phải thấp, trên phải (nhãn việc).
  const PANELS = [
    { id: 'L', box: [0.04, 0.60, 0.40, 0.80], skew: 0.06 },
    { id: 'R', box: [0.60, 0.58, 0.96, 0.78], skew: -0.06 },
    { id: 'T', box: [0.66, 0.26, 1.02, 0.40], skew: -0.04 },
  ];

  /** Khung ảnh nhân vật trong vùng w x h (khớp apex-humanoid.js). Hàm thuần cho test. */
  function figureRect(w, h, aspect) {
    const fh = Math.min(h * 1.01, w * 1.6), fw = fh * (aspect || 0.926);
    return { x: (w - fw) / 2, y: h - fh, w: fw, h: fh };
  }
  /** Chế độ tay theo trạng thái Joyce + hoạt động gần đây. Hàm thuần cho test. */
  function modeOf(state, lastToolAgoMs, lastStreamAgoMs) {
    if (state === 'SPEAKING' || lastStreamAgoMs < 1500) return 'answer';
    if (state === 'THINKING' || lastToolAgoMs < 4000) return 'work';
    return 'idle';
  }

  class JoyceGestures {
    constructor(host, opts = {}) {
      this.host = host; this.opts = opts;
      this.canvas = document.createElement('canvas');
      this.canvas.className = 'jg-layer';
      this.canvas.setAttribute('aria-hidden', 'true');
      this.canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:4';
      host.appendChild(this.canvas);
      this.ctx = this.canvas.getContext('2d');
      this.state = 'READY'; this.level = 0;
      this.show = 0; this.panelShow = 0; this.answer = 0;
      this.label = ''; this.lastTool = -1e9; this.lastStream = -1e9;
      this.arms = {
        L: { tip: null, goal: null, nextAt: 0, tapAt: -1e9, panel: 0 },
        R: { tip: null, goal: null, nextAt: 400, tapAt: -1e9, panel: 1 },
      };
      this.ripples = []; this.rows = [[], [], []]; this.btnHot = [-1e9, -1e9, -1e9, -1e9, -1e9, -1e9];
      this.running = false; this.disposed = false;
      const mq = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : null;
      this.reduced = !!(mq && mq.matches);
      this.onAct = (e) => this.act(e.detail || {});
      global.addEventListener('joyce:avatar-act', this.onAct);
    }
    act(d) {
      const now = performance.now();
      if (d.kind === 'tool') { this.lastTool = now; if (d.label) this.label = String(d.label).slice(0, 40); this.pushRow(0); this.pushRow(2); }
      else if (d.kind === 'result') { this.lastTool = now; this.pushRow(1); }
      else if (d.kind === 'answer') { this.lastStream = now; }
      else if (d.kind === 'done') { this.lastStream = -1e9; this.lastTool = -1e9; }
    }
    pushRow(p) { const r = this.rows[p]; r.push({ w: 0.35 + Math.random() * 0.6, at: performance.now() }); if (r.length > 5) r.shift(); }
    setState(s) { this.state = String(s || 'READY').toUpperCase(); }
    setLevel(v) { this.level = clamp(+v || 0); }
    start() { if (this.running || this.disposed) return; this.running = true; this.raf = requestAnimationFrame(t => this.frame(t)); }
    stop() { this.running = false; cancelAnimationFrame(this.raf); }

    // Ống hạt: lõi mờ, viền sáng, vân ngang cách đều (giống vân của tượng). show<1 thì hạt
    // còn tản ra (đang tụ lại thành tay).
    tube(A, B, rA, rB, seed, t, alpha) {
      const c = this.ctx, dx = B[0] - A[0], dy = B[1] - A[1], L = Math.hypot(dx, dy) || 1;
      const nx = -dy / L, ny = dx / L, steps = Math.max(2, Math.floor(L / 2.6)), spread = (1 - this.show) * 70;
      // Khối sáng mờ bên dưới: cho cánh tay có độ dày thay vì chỉ là hai vệt chấm.
      c.globalAlpha = alpha * 0.10; c.strokeStyle = "#19ddff"; c.lineCap = "round";
      c.lineWidth = (rA + rB); c.beginPath(); c.moveTo(A[0], A[1]); c.lineTo(B[0], B[1]); c.stroke();
      c.globalAlpha = alpha * 0.10; c.lineWidth = (rA + rB) * 0.45; c.stroke();
      for (let i = 0; i <= steps; i++) {
        const k = i / steps, cx = A[0] + dx * k, cy = A[1] + dy * k, r = lerp(rA, rB, k);
        const ring = i % 3 === 0;
        const n = ring ? 15 : 9;
        for (let j = 0; j < n; j++) {
          const s = (j / (n - 1)) * 2 - 1, id = seed + i * 31.7 + j * 7.3;
          if (!ring && Math.abs(s) < 0.55 && hash(id) > 0.55) continue;     // ruột thưa, viền dày
          const jx = (hash(id + 1) - 0.5) * spread + Math.sin(t * 1.7 + id) * 0.4;
          const jy = (hash(id + 2) - 0.5) * spread;
          const rim = Math.pow(Math.abs(s), 3);
          c.globalAlpha = Math.min(1, alpha * (ring ? 0.8 : 0.45 + 0.55 * rim));
          c.fillStyle = hash(id + 3) > 0.94 ? '#ffb347' : (rim > 0.6 ? '#9ff3ff' : '#19ddff');
          c.fillRect(cx + nx * r * s + jx, cy + ny * r * s + jy, 1.7, 1.7);
        }
      }
    }
    hand(W, T, size, seed, t, alpha, pressed) {
      const dx = T[0] - W[0], dy = T[1] - W[1], L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
      // Lòng bàn tay: chấm hạt trong elip quanh cổ tay.
      const c = this.ctx, spread = (1 - this.show) * 60;
      for (let i = 0; i < 160; i++) {
        const a = hash(seed + i) * Math.PI * 2, rr = Math.sqrt(hash(seed + i + 9)) * size;
        c.globalAlpha = alpha * (0.3 + 0.6 * (rr / size));
        c.fillStyle = '#19ddff';
        c.fillRect(W[0] + Math.cos(a) * rr * 1.1 + (hash(seed + i + 3) - 0.5) * spread, W[1] + Math.sin(a) * rr * 0.8, 1.3, 1.3);
      }
      // Ngón trỏ duỗi tới điểm chạm; ba ngón co + ngón cái là các đoạn ngắn lệch góc.
      this.tube(W, T, size * 0.28, size * 0.2, seed + 50, t, alpha);
      [-0.55, -0.25, 0.3, 0.75].forEach((ang, k) => {
        const ca = Math.cos(ang), sa = Math.sin(ang), len = size * (k === 3 ? 0.9 : 1.15);
        const vx = ux * ca - uy * sa, vy = ux * sa + uy * ca;
        const B = [W[0] + vx * len, W[1] + vy * len];
        this.tube(W, B, size * 0.22, size * 0.17, seed + 80 + k * 13, t, alpha * 0.85);
      });
      if (pressed > 0) {                                                  // đầu ngón sáng khi chạm
        c.globalAlpha = alpha * pressed;
        const g = c.createRadialGradient(T[0], T[1], 0, T[0], T[1], 16);
        g.addColorStop(0, 'rgba(255,190,90,0.9)'); g.addColorStop(1, 'rgba(255,140,30,0)');
        c.fillStyle = g; c.fillRect(T[0] - 16, T[1] - 16, 32, 32);
      }
    }
    panelPath(P, R) {
      const [u0, v0, u1, v1] = P.box, s = P.skew;
      const x0 = R.x + u0 * R.w, x1 = R.x + u1 * R.w, y0 = R.y + v0 * R.h, y1 = R.y + v1 * R.h, sk = s * R.w;
      return [[x0 + sk, y0], [x1 + sk, y0], [x1, y1], [x0, y1]];
    }
    // Nút bấm trên bảng (3 nút dọc mép dưới) -> toạ độ màn hình.
    buttonPos(pi, bi, R) {
      const q = this.panelPath(PANELS[pi], R);
      const fx = 0.22 + bi * 0.28, fy = 0.80;
      const top = [lerp(q[0][0], q[1][0], fx), q[0][1]], bot = [lerp(q[3][0], q[2][0], fx), q[3][1]];
      return [lerp(top[0], bot[0], fy), lerp(top[1], bot[1], fy)];
    }
    drawPanel(pi, R, t, alpha, title) {
      const c = this.ctx, q = this.panelPath(PANELS[pi], R), now = performance.now();
      c.globalAlpha = alpha * 0.16; c.fillStyle = '#0a4f66';
      c.beginPath(); q.forEach((p, i) => (i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]))); c.closePath(); c.fill();
      c.globalAlpha = alpha * 0.75; c.strokeStyle = '#19ddff'; c.lineWidth = 1; c.stroke();
      const x0 = q[0][0] + 8, y0 = q[0][1] + 14, wid = q[1][0] - q[0][0] - 16, hei = q[3][1] - q[0][1];
      c.globalAlpha = alpha; c.fillStyle = '#9ff3ff'; c.font = '10px "Courier New", monospace';
      c.fillText(title, x0, y0);
      // Dòng kết quả hiện dần (mỗi tool_call/tool_result đẩy thêm một dòng).
      this.rows[pi].forEach((r, i) => {
        const age = clamp((now - r.at) / 600);
        c.globalAlpha = alpha * 0.55; c.fillStyle = i % 2 ? '#19ddff' : '#7fe9ff';
        c.fillRect(x0, y0 + 8 + i * 7, wid * r.w * age, 2);
      });
      // Thanh quét chạy dọc bảng.
      const sy = q[0][1] + ((t * 0.8 + pi * 0.37) % 1) * hei;
      c.globalAlpha = alpha * 0.25; c.fillStyle = '#9ff3ff'; c.fillRect(q[3][0] + 2, sy, wid + 12, 1);
      for (let b = 0; b < 3; b++) {                                        // nút
        const p = this.buttonPos(pi, b, R), hot = clamp(1 - (now - this.btnHot[pi * 3 + b]) / 500);
        c.globalAlpha = alpha * (0.45 + 0.55 * hot); c.strokeStyle = hot > 0 ? '#ffb347' : '#19ddff';
        c.strokeRect(p[0] - 12, p[1] - 5, 24, 10);
        if (hot > 0) { c.globalAlpha = alpha * hot * 0.5; c.fillStyle = '#ffb347'; c.fillRect(p[0] - 12, p[1] - 5, 24, 10); }
      }
    }

    frame(now) {
      if (!this.running || this.disposed) return;
      this.raf = requestAnimationFrame(t => this.frame(t));
      const r = this.host.getBoundingClientRect(), w = Math.max(1, r.width), h = Math.max(1, r.height);
      const dpr = Math.min(global.devicePixelRatio || 1, 1.5);
      if (this.canvas.width !== Math.round(w * dpr)) { this.canvas.width = Math.round(w * dpr); this.canvas.height = Math.round(h * dpr); }
      const c = this.ctx; c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h);
      if (this.reduced) return;
      const t = now / 1000, dt = Math.min(0.1, (now - (this.last || now)) / 1000); this.last = now;
      const mode = modeOf(this.state, now - this.lastTool, now - this.lastStream);
      this.show = lerp(this.show, mode === 'idle' ? 0 : 1, Math.min(1, dt * 2.2));
      this.answer = lerp(this.answer, mode === 'answer' ? 1 : 0, Math.min(1, dt * 2));
      this.panelShow = lerp(this.panelShow, mode === 'idle' ? 0 : 1, Math.min(1, dt * 3));
      if (this.show < 0.01 && this.panelShow < 0.01) return;
      const R = figureRect(w, h, this.opts.getAspect ? this.opts.getAspect() : 0.926);
      const at = (uv) => [R.x + uv[0] * R.w, R.y + uv[1] * R.h];
      c.globalCompositeOperation = 'lighter';

      // Bảng: làm việc -> 3 bảng (nhãn việc ở bảng trên); trả lời -> chỉ bảng phải.
      const workA = this.panelShow * (1 - this.answer);
      const title = this.label || 'ĐANG TÌM KIẾM…';
      if (workA > 0.01) { this.drawPanel(0, R, t, workA, 'TÌM KIẾM'); this.drawPanel(2, R, t, workA, title); }
      this.drawPanel(1, R, t, this.panelShow, this.answer > 0.5 ? 'ĐANG TRẢ LỜI' : 'KẾT QUẢ');
      if (this.answer > 0.5 && now - (this.rowAt || 0) > 420) { this.rowAt = now; this.pushRow(1); }

      // Tay: chọn nút đích theo nhịp; tới nơi thì "chạm" (sáng nút + vòng sóng + thêm dòng).
      ['L', 'R'].forEach((side, si) => {
        const arm = this.arms[side];
        if (now >= arm.nextAt) {
          if (this.answer > 0.5) {
            arm.goal = null;                                              // trả lời: tay khoa nhẹ trước ngực
          } else {
            const pi = side === 'L' ? 0 : (Math.random() < 0.7 ? 1 : 2), bi = Math.floor(Math.random() * 3);
            arm.panel = pi; arm.btn = bi; arm.goal = this.buttonPos(pi, bi, R); arm.tapped = false;
          }
          arm.nextAt = now + 650 + Math.random() * 650 + si * 120;
        }
        const rest = at([side === 'L' ? 0.40 : 0.60, 0.88 + Math.sin(t * 2.2 + si) * 0.015 * (1 + this.level * 2)]);
        const goal = arm.goal || rest;
        if (!arm.tip) arm.tip = at(ELBOW[side]);
        const k = Math.min(1, dt * 7);
        arm.tip = [lerp(arm.tip[0], goal[0], k), lerp(arm.tip[1], goal[1], k)];
        const near = arm.goal && Math.hypot(arm.tip[0] - goal[0], arm.tip[1] - goal[1]) < 4;
        if (near && !arm.tapped) {
          arm.tapped = true; arm.tapAt = now; this.btnHot[arm.panel * 3 + arm.btn] = now;
          this.ripples.push({ x: goal[0], y: goal[1], at: now }); if (this.ripples.length > 8) this.ripples.shift();
          if (Math.random() < 0.5) this.pushRow(arm.panel);
        }
        const press = clamp(1 - (now - arm.tapAt) / 350);
        const S = at(SHOULDER[side]), E0 = at(ELBOW[side]);
        const E = [lerp(E0[0], arm.tip[0], 0.18), lerp(E0[1], arm.tip[1], 0.08)];
        const fl = R.h * 0.065, dx = arm.tip[0] - E[0], dy = arm.tip[1] - E[1], L = Math.hypot(dx, dy) || 1;
        const Wr = [arm.tip[0] - dx / L * fl, arm.tip[1] - dy / L * fl];
        const tipIn = [arm.tip[0] + dx / L * press * 3, arm.tip[1] + dy / L * press * 3];
        const a = this.show * 0.95;
        this.tube(S, E, R.w * 0.075, R.w * 0.062, si * 1000, t, a);
        this.tube(E, Wr, R.w * 0.062, R.w * 0.040, si * 1000 + 300, t, a);
        this.hand(Wr, tipIn, R.w * 0.048, si * 1000 + 600, t, a, press);
      });

      // Vòng sóng ở chỗ chạm.
      this.ripples = this.ripples.filter(q => now - q.at < 700);
      this.ripples.forEach(q => {
        const age = (now - q.at) / 700;
        c.globalAlpha = (1 - age) * 0.7; c.strokeStyle = '#ffb347'; c.lineWidth = 1.2;
        c.beginPath(); c.ellipse(q.x, q.y, 4 + age * 30, 2 + age * 14, 0, 0, Math.PI * 2); c.stroke();
      });
      c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
    }
    dispose() {
      if (this.disposed) return;
      this.disposed = true; this.stop();
      global.removeEventListener('joyce:avatar-act', this.onAct);
      this.canvas.remove();
    }
  }

  global.JoyceGestures = JoyceGestures;
  if (typeof module !== 'undefined' && module.exports) module.exports = { JoyceGestures, figureRect, modeOf, PANELS };
})(typeof window !== 'undefined' ? window : globalThis);
