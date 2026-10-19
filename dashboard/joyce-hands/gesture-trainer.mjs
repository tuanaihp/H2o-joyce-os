// Bảng HUẤN LUYỆN cử chỉ tay: dạy Joyce nhận diện theo chính tay người dùng.
// Khác chế độ điều khiển (camera ẩn) — ở đây CÓ khung xem trước vì luyện phải thấy tay.
// Mỗi cử chỉ quét 3 LẦN với nhịp khác nhau -> lấy trung bình + độ lệch làm ngưỡng
// khoan dung riêng (tay ai nấy khác nhau); 3 lần lệch quá -> báo quét lại, không lưu bừa.
// Hồ sơ lưu trên server: GET/PUT /hands/profile (STATE_DIR/hand_gestures.json).
import {JoyceHandController, HAND_EDGES} from './hand-controller.mjs';
import {fingerVector, clamp} from './gesture-engine.mjs';

export const HAND_ACTIONS = [
  {id:'pulse',        vi:'Sóng năng lượng',            en:'Energy pulse'},
  {id:'stop',         vi:'Bảo Joyce ngừng nói',        en:'Stop Joyce speaking'},
  {id:'album.open',   vi:'Mở album trình chiếu',       en:'Open album slideshow'},
  {id:'album.next',   vi:'Album: ảnh tiếp theo',       en:'Album: next photo'},
  {id:'album.prev',   vi:'Album: ảnh trước',           en:'Album: previous photo'},
  {id:'album.close',  vi:'Đóng album',                 en:'Close album'},
  {id:'fullscreen',   vi:'Toàn màn hình 3D Joyce',     en:'Fullscreen 3D Joyce'},
];
export const CALIB_SLOTS = [
  {id:'pinch', kind:'pinch', vi:'Chụm ngón cái + trỏ',        en:'Pinch thumb + index'},
  {id:'palm',  kind:'palm',  vi:'Xòe 5 ngón (ngừng nói)',     en:'Open palm (stop)'},
  {id:'swipe', kind:'swipe', vi:'Vuốt ngang nhanh',           en:'Quick horizontal swipe'},
];
const tt = (k, f) => { const v = window.t?.(k); return v && v !== k ? v : f; };
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const PROFILE_URL = '/hands/profile';
const HOLD_FRAMES = 20;      // ~1.3s @15fps giữ dáng mới chốt 1 lần quét
const GAP_FRAMES = 4;        // bắt buộc bỏ/lệch tay giữa 2 lần quét

const CSS = `
.jht{position:fixed;inset:0;z-index:70;display:flex;align-items:center;justify-content:center;background:#02070acc;backdrop-filter:blur(6px)}
.jht-box{width:min(880px,calc(100vw - 24px));max-height:calc(100dvh - 24px);overflow:auto;display:grid;grid-template-columns:minmax(240px,320px) 1fr;gap:14px;background:#061016;color:#cff7ff;border:1px solid #23505e;border-radius:16px;padding:16px;font:13px/1.5 system-ui,sans-serif;color-scheme:dark;box-shadow:0 24px 80px #000c}
.jht *{box-sizing:border-box}
.jht h3{margin:0 0 8px;font-size:15px}
.jht h4{margin:14px 0 6px;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:#39d9ee}
.jht button{border:1px solid #23505e;background:#0c202a;border-radius:8px;padding:7px 10px;color:inherit;font:inherit;cursor:pointer}
.jht button:disabled{opacity:.4;cursor:default}
.jht .jht-cam{position:relative;background:#02080b;border:1px solid #23505e;border-radius:10px;overflow:hidden;min-height:180px}
.jht .jht-cam video{display:block;width:100%;height:auto;transform:scaleX(-1)}
.jht .jht-cam canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.jht .jht-status{min-height:34px;font-size:12px;color:#8eaeb7;padding:8px 2px}
.jht .jht-status.err{color:#ffad9f}
.jht .jht-status.ok{color:#62f6c7}
.jht .jht-prog{height:6px;background:#0c202a;border-radius:3px;overflow:hidden;margin:6px 0}
.jht .jht-prog i{display:block;height:100%;width:0;background:#19ddff;transition:width .12s}
.jht .jht-row{display:flex;align-items:center;gap:8px;padding:8px;border:1px solid #173a44;border-radius:10px;margin-bottom:8px;background:#08141a}
.jht .jht-row .nm{flex:1;min-width:0}
.jht .jht-row .nm b{display:block;font-size:13px}
.jht .jht-row .nm small{color:#8eaeb7}
.jht .jht-dot{width:8px;height:8px;border-radius:50%;background:#3a5a63;flex:none}
.jht .jht-row.done .jht-dot{background:#62f6c7;box-shadow:0 0 8px #62f6c7aa}
.jht .jht-row.busy .jht-dot{background:#ffce7e;animation:jhtp 1s infinite}
@keyframes jhtp{50%{opacity:.3}}
.jht input[type=text],.jht select{background:#0c202a;border:1px solid #23505e;color:#cff7ff;border-radius:6px;padding:6px 8px;font:inherit;width:100%}
.jht .jht-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.jht .jht-head{display:flex;justify-content:space-between;align-items:center;grid-column:1/-1}
.jht .jht-close{font-size:18px;line-height:1;padding:6px 10px}
.jht .jht-note{color:#8eaeb7;font-size:11px}
.jht .jht-presets{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.jht .jht-presets button{font-size:12px;padding:5px 9px}
@media(max-width:720px){.jht-box{grid-template-columns:1fr}}
`;

class GestureTrainer {
  constructor(opts = {}) {
    this.opts = opts;
    this.profile = {custom: [], calib: {}};
    this.ctl = null; this.el = null; this.cap = null; this.disposed = false;
    this.onTracking = e => this._frame(e.detail || {});
  }
  async open() {
    if (this.el) { this.el.focus(); return this; }
    const style = document.createElement('style');
    style.textContent = CSS; this.styleEl = style; document.head.appendChild(style);
    const el = document.createElement('div');
    el.className = 'jht'; el.tabIndex = -1;
    el.innerHTML = `<div class="jht-box" role="dialog" aria-modal="true" aria-label="Gesture trainer">
      <div class="jht-head"><h3>🖐 ${esc(tt('htr.title', 'Dạy cử chỉ tay cho Joyce'))}</h3>
        <button class="jht-close" data-x title="Esc">✕</button></div>
      <div>
        <div class="jht-cam"><video muted playsinline></video><canvas></canvas></div>
        <div class="jht-prog"><i></i></div>
        <div class="jht-status">${esc(tt('htr.need_cam', 'Bấm "Bật camera" để bắt đầu.'))}</div>
        <div class="jht-actions"><button data-cam>${esc(tt('htr.cam_on', 'Bật camera'))}</button></div>
        <p class="jht-note">${esc(tt('htr.privacy', 'Camera xử lý tại máy, không gửi đi đâu. Mỗi cử chỉ quét 3 lần với nhịp khác nhau để Joyce học đúng tay anh.'))}</p>
      </div>
      <div>
        <h4>${esc(tt('htr.calib_h', 'Hiệu chuẩn cử chỉ có sẵn'))}</h4>
        <div data-list="calib"></div>
        <h4>${esc(tt('htr.custom_h', 'Cử chỉ của anh — gắn hành động'))}</h4>
        <div class="jht-presets" data-presets></div>
        <div data-list="custom"></div>
      </div></div>`;
    document.body.appendChild(el); this.el = el;
    el.querySelector('[data-x]').onclick = () => this.close();
    el.querySelector('[data-cam]').onclick = () => this._startCam();
    el.addEventListener('keydown', e => { if (e.key === 'Escape') this.close(); });
    try { const r = await fetch(PROFILE_URL, {credentials:'same-origin'});
      if (r.ok) { const d = await r.json(); if (d && typeof d === 'object') this.profile = {custom: d.custom || [], calib: d.calib || {}}; }
    } catch (e) {}
    this._render();
    el.focus();
    return this;
  }
  _render() {
    const calibBox = this.el.querySelector('[data-list=calib]');
    calibBox.innerHTML = CALIB_SLOTS.map(s => {
      const done = this._calibDone(s.id);
      return `<div class="jht-row ${done ? 'done' : ''}" data-slot="calib:${s.id}">
        <span class="jht-dot"></span><div class="nm"><b>${esc(s.vi)}</b>
        <small>${done ? esc(tt('htr.calibrated', 'đã hiệu chuẩn theo tay anh')) : esc(tt('htr.default', 'đang dùng ngưỡng mặc định'))}</small></div>
        <button data-train="${s.id}" ${this.cap ? 'disabled' : ''}>${esc(tt('htr.train', 'Luyện'))}</button>
        ${done ? `<button data-reset="${s.id}" ${this.cap ? 'disabled' : ''}>↺</button>` : ''}</div>`;
    }).join('');
    const pres = this.el.querySelector('[data-presets]');
    const presets = [['✌️','2 ngón'],['🤟','3 ngón'],['🖐','5 ngón'],['✊','Nắm tay'],['👌','OK']];
    pres.innerHTML = presets.map(([e, n]) => `<button data-preset="${e} ${n}">+ ${e} ${n}</button>`).join('');
    const cus = this.el.querySelector('[data-list=custom]');
    cus.innerHTML = this.profile.custom.map(g => `
      <div class="jht-row done" data-slot="custom:${esc(g.id)}">
        <span class="jht-dot"></span><div class="nm"><b>${esc(g.label)}</b>
        <select data-act="${esc(g.id)}">${HAND_ACTIONS.map(a => `<option value="${a.id}"${a.id === g.action ? ' selected' : ''}>${esc(a.vi)}</option>`).join('')}</select></div>
        <button data-retrain="${esc(g.id)}" ${this.cap ? 'disabled' : ''}>↻</button>
        <button data-del="${esc(g.id)}" ${this.cap ? 'disabled' : ''}>✕</button></div>`).join('');
    // wire
    this.el.querySelectorAll('[data-train]').forEach(b => b.onclick = () => this._train({kind: CALIB_SLOTS.find(s => s.id === b.dataset.train).kind, slot: b.dataset.train}));
    this.el.querySelectorAll('[data-reset]').forEach(b => b.onclick = () => this._resetCalib(b.dataset.reset));
    this.el.querySelectorAll('[data-preset]').forEach(b => b.onclick = () => this._addCustom(b.dataset.preset));
    this.el.querySelectorAll('[data-retrain]').forEach(b => b.onclick = () => { const g = this.profile.custom.find(x => x.id === b.dataset.retrain); if (g) this._train({kind:'pose', custom:g}); });
    this.el.querySelectorAll('[data-del]').forEach(b => b.onclick = () => this._delCustom(b.dataset.del));
    this.el.querySelectorAll('[data-act]').forEach(s => s.onchange = () => { const g = this.profile.custom.find(x => x.id === s.dataset.act); if (g) { g.action = s.value; this._save(); } });
  }
  _calibDone(id) {
    return {pinch: 'pinchOn', palm: 'palmExtMin', swipe: 'swipeMinDelta'}[id] in (this.profile.calib || {});
  }
  _status(msg, cls = '') { const s = this.el.querySelector('.jht-status'); s.textContent = msg; s.className = 'jht-status ' + cls; }
  _prog(p) { this.el.querySelector('.jht-prog i').style.width = Math.round(p * 100) + '%'; }
  async _startCam() {
    if (this.ctl) return;
    this._status(tt('htr.loading', 'Đang nạp bộ nhận diện…'));
    const video = this.el.querySelector('video'), overlay = this.el.querySelector('canvas');
    const def = p => new URL(p, location.origin + '/static/joyce-hands/').href;
    const a = this.opts.assets || {};
    this.ctl = new JoyceHandController({
      video, overlay, fps: 15,
      workerURL: a.workerURL || '/static/joyce-hands/hand-worker.js',
      moduleURL: a.moduleURL || '/static/humanoid/mediapipe/vision_bundle.mjs',
      wasmURL: a.wasmURL || '/static/humanoid/mediapipe/wasm',
      modelURL: a.modelURL || '/static/humanoid/hand_landmarker.task',
    });
    this.ctl.addEventListener('status', e => {
      this._status(e.detail.message || '', e.detail.state === 'error' ? 'err' : e.detail.state === 'active' ? 'ok' : '');
      this.el.querySelector('[data-cam]').textContent = e.detail.state === 'active' ? '● CAM ON' : tt('htr.cam_on', 'Bật camera');
    });
    this.ctl.addEventListener('tracking', this.onTracking);
    await this.ctl.start();
  }
  _frame(d) {
    const c = this.cap; if (!c) return;
    const lm = d.landmarks;
    // khoảng nghỉ bắt buộc giữa 2 lần quét: tay phải rời/mất một nhịp
    if (c.needGap) { c.gapN = d.tracked && lm ? 0 : c.gapN + 1; if (c.gapN < GAP_FRAMES) return; c.needGap = false; c.acc = []; }
    if (!(d.tracked && lm)) { c.acc = []; return; }
    let sample = null;
    if (c.kind === 'pose') sample = fingerVector(lm, this.ctl.canvas.width / this.ctl.canvas.height);
    else if (c.kind === 'pinch') { if (d.pose !== 'pinch' || !Number.isFinite(d.pinchRatio)) { c.acc = []; return; } sample = d.pinchRatio; }
    else if (c.kind === 'palm') {
      const fv = fingerVector(lm, this.ctl.canvas.width / this.ctl.canvas.height);
      if (!fv.slice(1).every(v => v > .65)) { c.acc = []; return; }
      const dist = (a, b) => Math.hypot((lm[a].x - lm[b].x) * 4 / 3, lm[a].y - lm[b].y);
      sample = Math.min(...[[8,6],[12,10],[16,14],[20,18]].map(([t, p]) => dist(t, 0) / (dist(p, 0) || 1e-6)));
    } else if (c.kind === 'swipe') { this._frameSwipe(d); return; }
    // giữ dáng yên: wrist không trôi quá 8% khung mỗi nhịp
    if (c.lastW && Math.hypot(lm[0].x - c.lastW.x, lm[0].y - c.lastW.y) > .08) c.acc = [];
    c.lastW = {x: lm[0].x, y: lm[0].y};
    c.acc.push(sample);
    const n = Math.min(1, c.acc.length / HOLD_FRAMES);
    this._prog((c.reps.length + n) / 3);
    this._status(`${tt('htr.rep', 'Lần')} ${c.reps.length + 1}/3 — ${esc(tt('htr.hold', 'giữ yên'))} ${Math.round(n * 100)}%`);
    if (c.acc.length >= HOLD_FRAMES) {
      c.reps.push(this._median(c.acc)); c.needGap = true; c.gapN = 0; c.acc = []; c.lastW = null;
      this._status(`${tt('htr.got', 'Đã ghi lần')} ${c.reps.length}/3 — ${tt('htr.again', 'bỏ tay ra rồi làm lại (nhịp khác cũng được)')}`, 'ok');
      if (c.reps.length >= 3) this._finish();
    }
  }
  _frameSwipe(d) {
    const c = this.cap, p = d.pointer;
    if (p) c.trail.push({x: p.x, y: p.y, t: performance.now()});
    const now = performance.now();
    while (c.trail.length && now - c.trail[0].t > 700) c.trail.shift();
    if (c.trail.length < 4) return;
    const a = c.trail[0], b = c.trail[c.trail.length - 1];
    const dx = Math.abs(b.x - a.x), dy = Math.abs(b.y - a.y), span = b.t - a.t;
    if (Math.max(dx, dy) >= .16 && span <= 600) {
      c.reps.push({delta: Math.max(dx, dy), span});
      c.trail = []; c.needGap = true; c.gapN = 0;
      this._status(`${tt('htr.got', 'Đã ghi lần')} ${c.reps.length}/3 — ${tt('htr.again', 'bỏ tay ra rồi làm lại (nhịp khác cũng được)')}`, 'ok');
      this._prog(c.reps.length / 3);
      if (c.reps.length >= 3) this._finish();
    }
  }
  _median(acc) {
    if (!Array.isArray(acc[0])) { const s = [...acc].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; }
    return acc[0].map((_, i) => { const s = acc.map(v => v[i]).sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; });
  }
  async _train(task) {
    await this._startCam();
    if (!this.ctl || this.ctl.state !== 'active') { this._status(tt('htr.need_cam2', 'Cần camera đang bật để luyện.'), 'err'); return; }
    this.cap = {kind: task.kind, slot: task.slot, custom: task.custom, reps: [], acc: [], trail: [], needGap: true, gapN: 0, lastW: null};
    this._render();
    const hint = {pose: 'giơ đúng dáng và giữ yên', pinch: 'chụm ngón cái + trỏ và giữ',
      palm: 'xòe 5 ngón và giữ yên', swipe: 'vuốt tay ngang thật nhanh qua khung hình'}[task.kind];
    this._status(`${tt('htr.go', 'Bắt đầu')} — ${hint} (${tt('htr.rep', 'Lần')} 1/3)`);
    this._prog(0);
  }
  _finish() {
    const c = this.cap; this.cap = null;
    const med = arr => { const s = [...arr].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
    if (c.kind === 'pose') {
      const vec = [0,1,2,3,4].map(i => med(c.reps.map(r => r[i])));
      const std = [0,1,2,3,4].map(i => {
        const m = vec[i]; return Math.sqrt(c.reps.reduce((s, r) => s + (r[i] - m) ** 2, 0) / c.reps.length);
      });
      if (Math.max(...[0,1,2,3,4].map(i => Math.max(...c.reps.map(r => r[i])) - Math.min(...c.reps.map(r => r[i])))) > .5) {
        this._status(tt('htr.unstable', '3 lần lệch nhau quá — giữ cùng một dáng rồi luyện lại.'), 'err');
        this._render(); return;
      }
      c.custom.vec = vec.map(v => +v.toFixed(3));
      c.custom.tol = std.map(s => +clamp(.14 + s * 2.5, .14, .45).toFixed(3));
      if (!c.custom.id) c.custom.id = 'g_' + Date.now().toString(36);
      if (!this.profile.custom.find(g => g.id === c.custom.id)) this.profile.custom.push(c.custom);
    } else if (c.kind === 'pinch') {
      const r = c.reps.reduce((a, b) => a + b, 0) / c.reps.length;
      this.profile.calib.pinchOn = +clamp(r - .07, .1, .45).toFixed(3);
      this.profile.calib.pinchOff = +clamp(r + .16, this.profile.calib.pinchOn + .08, .7).toFixed(3);
    } else if (c.kind === 'palm') {
      const e = c.reps.reduce((a, b) => a + b, 0) / c.reps.length;
      this.profile.calib.palmExtMin = +clamp(e * .92, 1.03, 1.25).toFixed(3);
    } else if (c.kind === 'swipe') {
      const d = c.reps.reduce((a, b) => a + b.delta, 0) / c.reps.length;
      const s = c.reps.reduce((a, b) => a + b.span, 0) / c.reps.length;
      this.profile.calib.swipeMinDelta = +clamp(d * .72, .14, .4).toFixed(3);
      this.profile.calib.swipeMaxSpanMs = Math.round(clamp(s * 1.35, 260, 750));
    }
    this._status(tt('htr.saved', 'Đã chốt và lưu hồ sơ ✓'), 'ok');
    this._prog(1);
    this._render();
    this._save();
  }
  _addCustom(label) {
    const g = {id: 'g_' + Date.now().toString(36) + Math.floor(Math.random() * 99), label, action: 'pulse', vec: null, tol: null};
    this._train({kind: 'pose', custom: g});
  }
  _delCustom(id) {
    this.profile.custom = this.profile.custom.filter(g => g.id !== id);
    this._render(); this._save();
  }
  _resetCalib(slot) {
    const keys = {pinch: ['pinchOn', 'pinchOff'], palm: ['palmExtMin'], swipe: ['swipeMinDelta', 'swipeMaxSpanMs']}[slot] || [];
    for (const k of keys) delete this.profile.calib[k];
    this._render(); this._save();
  }
  async _save() {
    try {
      const r = await fetch(PROFILE_URL, {method: 'PUT', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(this.profile)});
      if (!r.ok) throw new Error(String(r.status));
      window.dispatchEvent(new CustomEvent('joyce-hands:profile', {detail: this.profile}));
    } catch (e) { this._status(tt('htr.save_err', 'Lưu hồ sơ thất bại — thử lại.'), 'err'); }
  }
  close() {
    this.disposed = true; this.cap = null;
    if (this.ctl) { try { this.ctl.dispose(); } catch (e) {} this.ctl = null; }
    if (this.el) { this.el.remove(); this.el = null; }
    if (this.styleEl) { this.styleEl.remove(); this.styleEl = null; }
  }
}
let _inst = null;
export function openHandTrainer(opts = {}) {
  if (!_inst || _inst.disposed) _inst = new GestureTrainer(opts);
  return _inst.open();
}
export {GestureTrainer, HAND_EDGES};
