/* ============================================================================
 * JOYCE GESTURES - hiệu ứng "trích xuất dữ liệu" cho 3D Joyce (1.3.23).
 *
 * Khi Joyce làm việc, nhân vật phát tín hiệu ánh sáng (vòng sóng từ ngực, tia quét dọc
 * thân, hạt sáng bay lên), thân người nghiêng nhẹ và gật theo mỗi lần lấy được dữ liệu.
 * Dữ liệu THẬT bay ra màn hình: tên tệp trong brain mà lệnh đang đọc/tìm (tool_call.files)
 * và những con số, tên tệp có trong kết quả lệnh trả về (tool_result.content). Bộ đếm
 * "ĐANG DÒ DỮ LIỆU" chạy tổng số mục đã dò trong lượt. Không có dữ liệu thì không bịa số.
 *   - Trả lời: dữ liệu ngừng bay, bộ đếm chốt "ĐÃ DÒ N MỤC", ánh sáng nhịp theo giọng.
 *   - Rảnh: tắt dần.
 *
 * Toạ độ theo khung ảnh nhân vật (figureRect của apex-humanoid.js: cao min(h*1.01, w*1.6),
 * canh giữa, sát đáy). Không gọi model, không mạng; tôn trọng "giảm chuyển động" của OS.
 * ========================================================================== */
(function (global) {
  'use strict';

  const clamp = (n, a = 0, b = 1) => Math.max(a, Math.min(b, Number.isFinite(n) ? n : 0));
  const lerp = (a, b, k) => a + (b - a) * k;
  const ease = (k) => 1 - Math.pow(1 - clamp(k), 3);

  // Điểm phát dữ liệu theo khung ảnh (u ngang, v dọc từ đỉnh khung).
  const HEAD = [0.5, 0.38], CHEST = [0.5, 0.74];
  const SLOTS = 7;                                                      // số hàng mỗi bên, mỗi hàng một mục

  /** Khung ảnh nhân vật trong vùng w x h (khớp apex-humanoid.js). Hàm thuần cho test. */
  function figureRect(w, h, aspect) {
    const fh = Math.min(h * 1.01, w * 1.6), fw = fh * (aspect || 0.926);
    return { x: (w - fw) / 2, y: h - fh, w: fw, h: fh };
  }
  /** Chế độ theo trạng thái Joyce + hoạt động gần đây. Hàm thuần cho test. */
  function modeOf(state, lastToolAgoMs, lastStreamAgoMs) {
    if (state === 'SPEAKING' || lastStreamAgoMs < 1500) return 'answer';
    if (state === 'THINKING' || lastToolAgoMs < 4000) return 'work';
    return 'idle';
  }
  const DUOI = 'md|pdf|docx?|xlsx?|csv|txt|json|pptx?|png|jpe?g|webp|html?';
  /** Tên tệp gọn (bỏ thư mục, bỏ đuôi .md). */
  function tenGon(p) {
    const s = String(p || '').split(/[\\/]/).pop().replace(/\.md$/i, '');
    return s.length > 34 ? s.slice(0, 33) + '…' : s;
  }
  /** Rút dữ liệu thật từ chữ kết quả: con số, tên tệp, số dòng. Hàm thuần cho test. */
  function extractData(text) {
    const s = String(text || '');
    const names = [], numbers = [];
    const reTep = new RegExp('[^\\s"\'`<>|:()\\[\\]]+\\.(?:' + DUOI + ')\\b', 'gi');
    (s.match(reTep) || []).forEach((m) => { const n = tenGon(m); if (n && !names.includes(n)) names.push(n); });
    // Số trong tên tệp và số dòng kiểu grep ("tep.md:12:") không phải số liệu.
    const bo = s.replace(reTep, ' ').replace(/:\d+:/g, ' ');
    (bo.match(/\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?%?|\d+(?:[.,]\d+)?%|\d{2,}/g) || []).forEach((m) => {
      if (!numbers.includes(m)) numbers.push(m);
    });
    const lines = s.split(/\r?\n/).filter((l) => l.trim()).length;
    return { names: names.slice(0, 6), numbers: numbers.slice(0, 8), lines };
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
      this.state = 'READY'; this.level = 0; this.show = 0; this.answer = 0;
      this.label = ''; this.lastTool = -1e9; this.lastStream = -1e9;
      this.queue = []; this.flying = []; this.rings = []; this.sparks = [];
      this.total = 0; this.shown = 0; this.files = 0; this.nums = 0; this.nextPop = 0; this.nod = -1e9;
      this.turnOpen = false;
      this.running = false; this.disposed = false;
      const mq = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : null;
      this.reduced = !!(mq && mq.matches);
      this.onAct = (e) => this.act(e.detail || {});
      global.addEventListener('joyce:avatar-act', this.onAct);
    }
    newTurn() {
      if (this.turnOpen) return;
      this.turnOpen = true; this.total = 0; this.shown = 0; this.files = 0; this.nums = 0; this.queue = [];
    }
    act(d) {
      const now = performance.now();
      if (d.kind === 'tool') {
        this.newTurn(); this.lastTool = now;
        if (d.label) this.label = String(d.label).slice(0, 48);
        const fs = Array.isArray(d.files) ? d.files : [];
        fs.slice(0, 6).forEach((f) => this.queue.push({ txt: tenGon(f), kind: 'file' }));
        this.files += fs.length; this.total += Math.max(1, fs.length);
        this.signal(now);
      } else if (d.kind === 'result') {
        this.newTurn(); this.lastTool = now;
        const x = extractData(d.text);
        x.names.forEach((n) => this.queue.push({ txt: n, kind: 'file' }));
        x.numbers.forEach((n) => this.queue.push({ txt: n, kind: 'num' }));
        this.files += x.names.length; this.nums += x.numbers.length;
        this.total += Math.max(1, x.lines, x.names.length + x.numbers.length);
        if (this.queue.length > 24) this.queue.splice(0, this.queue.length - 24);
        this.signal(now);
      } else if (d.kind === 'answer') { this.lastStream = now; }
      else if (d.kind === 'done') { this.lastStream = -1e9; this.lastTool = -1e9; this.turnOpen = false; this.queue = []; }
    }
    signal(now) { this.nod = now; this.rings.push({ at: now }); if (this.rings.length > 6) this.rings.shift(); }
    setState(s) {
      this.state = String(s || 'READY').toUpperCase();
      if (this.state === 'THINKING') this.newTurn();
    }
    setLevel(v) { this.level = clamp(+v || 0); }
    start() { if (this.running || this.disposed) return; this.running = true; this.raf = requestAnimationFrame(t => this.frame(t)); }
    stop() { this.running = false; cancelAnimationFrame(this.raf); this.body(''); }

    // Chuyển động thân: nghiêng nhẹ, gật khi lấy được dữ liệu, nhún theo giọng khi trả lời.
    body(tf, flt) {
      const el = this.opts.getBody ? this.opts.getBody() : null;
      if (!el) return;
      el.style.transformOrigin = '50% 100%';
      el.style.transform = tf || '';
      el.style.filter = flt || '';
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
      // Bộ đếm còn đọng 3 giây sau lượt để người xem kịp thấy tổng.
      const linger = this.total > 0 && now - Math.max(this.lastTool, this.lastStream) < 7000;
      this.show = lerp(this.show, mode === 'idle' && !linger ? 0 : 1, Math.min(1, dt * 2.5));
      this.answer = lerp(this.answer, mode === 'work' ? 0 : 1, Math.min(1, dt * 2));
      this.shown = lerp(this.shown, this.total, Math.min(1, dt * 3.5));
      if (Math.abs(this.shown - this.total) < 0.5) this.shown = this.total;
      if (this.show < 0.01) { this.body(''); this.flying = []; return; }
      const R = figureRect(w, h, this.opts.getAspect ? this.opts.getAspect() : 0.926);
      const at = (uv) => [R.x + uv[0] * R.w, R.y + uv[1] * R.h];
      const work = this.show * (1 - this.answer);

      // ---- thân người
      const nodK = clamp(1 - (now - this.nod) / 450);
      const nod = Math.sin(nodK * Math.PI) * 0.9;
      const sway = Math.sin(t * 1.3) * 0.6 * work, lean = 0.012 * work;
      const bob = this.answer * this.show * this.level * 0.012;
      this.body('rotate(' + (sway + nod * 0.4).toFixed(3) + 'deg) scale(' + (1 + lean * 0.4 + nod * 0.006 + bob).toFixed(4) +
        ') translateY(' + (-(nod * 0.5 + bob * 40)).toFixed(2) + 'px)',
        'brightness(' + (1 + nodK * 0.35 * work + this.level * 0.15 * this.answer).toFixed(3) + ')');

      c.globalCompositeOperation = 'lighter';
      const C = at(CHEST), H = at(HEAD);

      // ---- tín hiệu ánh sáng: vòng sóng từ ngực mỗi lần lấy dữ liệu + nhịp đều khi đang dò
      if (work > 0.3 && now - (this.ringAt || 0) > 1100) { this.ringAt = now; this.rings.push({ at: now, soft: true }); }
      this.rings = this.rings.filter((q) => now - q.at < 1400);
      this.rings.forEach((q) => {
        const k = (now - q.at) / 1400, rad = R.w * (0.06 + k * 0.55);
        c.globalAlpha = (1 - k) * (q.soft ? 0.35 : 0.8) * this.show;
        c.strokeStyle = q.soft ? '#19ddff' : '#9ff3ff'; c.lineWidth = q.soft ? 1 : 2;
        c.beginPath(); c.ellipse(C[0], C[1], rad, rad * 0.32, 0, 0, Math.PI * 2); c.stroke();
      });
      // lõi sáng ở ngực, đập theo giọng khi trả lời
      const core = R.w * (0.05 + 0.03 * nodK + 0.04 * this.level * this.answer);
      const g = c.createRadialGradient(C[0], C[1], 0, C[0], C[1], core * 3);
      g.addColorStop(0, 'rgba(160,245,255,0.55)'); g.addColorStop(1, 'rgba(0,190,255,0)');
      c.globalAlpha = this.show * (0.5 + 0.5 * nodK); c.fillStyle = g;
      c.fillRect(C[0] - core * 3, C[1] - core * 3, core * 6, core * 6);
      // tia quét dọc thân khi đang dò
      if (work > 0.05) {
        const sy = R.y + R.h * (0.12 + ((t * 0.45) % 1) * 0.86);
        const lg = c.createLinearGradient(R.x + R.w * 0.15, 0, R.x + R.w * 0.85, 0);
        lg.addColorStop(0, 'rgba(25,221,255,0)'); lg.addColorStop(0.5, 'rgba(159,243,255,0.9)'); lg.addColorStop(1, 'rgba(25,221,255,0)');
        c.globalAlpha = work * 0.45; c.fillStyle = lg; c.fillRect(R.x + R.w * 0.15, sy, R.w * 0.7, 1.5);
      }
      // hạt sáng bay lên từ thân
      if (work > 0.2 && this.sparks.length < 70) {
        this.sparks.push({ x: C[0] + (Math.random() - 0.5) * R.w * 0.35, y: C[1] + Math.random() * R.h * 0.2, v: 30 + Math.random() * 50, at: now });
      }
      this.sparks = this.sparks.filter((s) => now - s.at < 1800);
      c.fillStyle = '#9ff3ff';
      this.sparks.forEach((s) => {
        const k = (now - s.at) / 1800;
        c.globalAlpha = (1 - k) * 0.7 * this.show;
        c.fillRect(s.x + Math.sin(k * 6 + s.v) * 3, s.y - k * s.v * 1.8, 1.6, 1.6);
      });

      // ---- dữ liệu thật bay ra (mỗi 160ms một mục khi đang dò)
      if (work > 0.3 && this.queue.length && now >= this.nextPop) {
        // Chỗ đậu: 2 cột hai bên tượng x SLOTS hàng, chọn ô đang trống để chữ không đè nhau.
        const busy = new Set(this.flying.map((f) => f.slot));
        const free = [];
        for (let k = 0; k < SLOTS * 2; k++) if (!busy.has(k)) free.push(k);
        if (free.length) {
          const it = this.queue.shift(), slot = free[Math.floor(Math.random() * free.length)];
          const left = slot < SLOTS, row = slot % SLOTS;
          const from = it.kind === 'num' ? C : H;
          const top = Math.max(R.y + R.h * 0.3, 150), bot = h - 30;
          const ty = top + (bot - top) * (row + 0.2 + Math.random() * 0.4) / SLOTS;
          const tx = left ? Math.max(10, R.x + R.w * (0.02 + Math.random() * 0.06)) : Math.min(w - 200, R.x + R.w * (0.74 + Math.random() * 0.06));
          this.flying.push(Object.assign({ x0: from[0], y0: from[1], x1: tx, y1: ty, at: now, slot }, it));
          this.nextPop = now + 160;
        }
      }
      const fz = Math.max(11, Math.min(16, R.w * 0.026));
      this.flying = this.flying.filter((f) => now - f.at < 3200);
      this.flying.forEach((f) => {
        const age = (now - f.at) / 1000, k = ease(age / 0.55);
        const x = lerp(f.x0, f.x1, k), y = lerp(f.y0, f.y1, k) - Math.max(0, age - 0.55) * 6;
        const a = this.show * (age < 0.15 ? age / 0.15 : age > 2.4 ? 1 - (age - 2.4) / 0.8 : 1);
        if (k < 1) {                                                      // vệt sáng lúc bay
          c.globalAlpha = a * 0.35 * (1 - k); c.strokeStyle = f.kind === 'num' ? '#ffb347' : '#19ddff'; c.lineWidth = 1;
          c.beginPath(); c.moveTo(f.x0, f.y0); c.lineTo(x, y); c.stroke();
        }
        c.globalAlpha = a;
        if (f.kind === 'num') { c.font = 'bold ' + Math.round(fz * 1.35) + 'px "Courier New", monospace'; c.fillStyle = '#ffc56b'; }
        else { c.font = Math.round(fz) + 'px "Courier New", monospace'; c.fillStyle = '#9ff3ff'; }
        c.fillText(f.kind === 'file' ? '▸ ' + f.txt : f.txt, x, y);
      });

      // ---- bộ đếm tổng
      c.globalCompositeOperation = 'source-over';
      const hx = Math.max(12, R.x + R.w * 0.02), hy = Math.max(28, R.y + R.h * 0.14);
      c.globalAlpha = this.show * 0.9; c.fillStyle = '#7fe9ff';
      c.font = Math.round(fz * 0.85) + 'px "Courier New", monospace';
      const working = this.answer < 0.5;
      c.fillText(working ? 'ĐANG DÒ DỮ LIỆU' : 'ĐÃ DÒ XONG', hx, hy);
      c.font = 'bold ' + Math.round(fz * 2.4) + 'px "Courier New", monospace'; c.fillStyle = '#e8fdff';
      c.fillText(Math.round(this.shown).toLocaleString('vi-VN') + (working ? '' : ' mục'), hx, hy + fz * 2.5);
      c.font = Math.round(fz * 0.8) + 'px "Courier New", monospace'; c.fillStyle = '#7fe9ff';
      c.fillText(this.files + ' tệp · ' + this.nums + ' số liệu', hx, hy + fz * 3.7);
      if (this.label && working) { c.globalAlpha = this.show * 0.75; c.fillText(this.label, hx, hy + fz * 4.9); }
      // vạch tiến trình chạy liên tục khi đang dò
      if (working) {
        const bw = R.w * 0.3, p = (t * 0.7) % 1;
        c.globalAlpha = this.show * 0.3; c.fillStyle = '#19ddff'; c.fillRect(hx, hy + fz * 0.6, bw, 2);
        c.globalAlpha = this.show; c.fillRect(hx + bw * p * 0.75, hy + fz * 0.6, bw * 0.25, 2);
      }
      c.globalAlpha = 1;
    }
    dispose() {
      if (this.disposed) return;
      this.disposed = true; this.stop();
      global.removeEventListener('joyce:avatar-act', this.onAct);
      this.canvas.remove();
    }
  }

  global.JoyceGestures = JoyceGestures;
  if (typeof module !== 'undefined' && module.exports) module.exports = { JoyceGestures, figureRect, modeOf, extractData, tenGon };
})(typeof window !== 'undefined' ? window : globalThis);
