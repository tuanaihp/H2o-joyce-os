// Album trình chiếu trong khoang não (.hud-center), mở bằng cử chỉ vuốt tay.
// Nguồn ảnh ưu tiên: GET /album?source=sale -> kho H2O Sale Album trên Supabase
// (trả URL R2 tuyệt đối, trình duyệt tải thẳng từ Cloudflare). Lỗi/trống -> về
// nguồn local GET /album?brain=<tên> (attachments/ + sources/ của brain, qua /files/raw).
// Zoom: khoảng cách ngón cái-ngón trỏ (pinchRatio 0..1.5) map tuyến tính 1x..4.5x
// khi album đang mở và chỉ có MỘT tay trong khung.
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ZOOM_MIN = 1, ZOOM_MAX = 4.5, RATIO_LO = 0.28, RATIO_HI = 0.78;

export class JoyceAlbum {
  constructor({ host, brain = 'Ban Hang - Sales Hinh Anh', onState = () => {} } = {}) {
    if (!host) throw new TypeError('JoyceAlbum cần host (.hud-center).');
    this.host = host; this.brain = brain; this.onState = onState;
    this.el = null; this.images = null; this.i = 0; this.zoom = 1;
    this.src = 'local';
    this.loading = null; this.opened = false; this.disposed = false;
  }
  isOpen() { return this.opened; }
  _build() {
    const el = document.createElement('div');
    el.className = 'joyce-album';
    el.innerHTML = '<div class="ja-hint">vuốt tay: lật ảnh · vuốt xuống: đóng · xòe/chụm 2 ngón: phóng to · thu nhỏ</div>' +
      '<figure><img alt=""></figure><div class="ja-cap"></div>';
    this.host.appendChild(el);
    this.el = el; this.img = el.querySelector('img'); this.cap = el.querySelector('.ja-cap');
    return el;
  }
  async _load() {
    if (this.images) return this.images;
    if (!this.loading) {
      const b = encodeURIComponent(this.brain);
      const get = u => fetch(u, { credentials: 'same-origin' })
        .then(r => (r.ok ? r.json() : null)).catch(() => null);
      this.loading = get('/album?source=sale')
        .then(d => (d && d.images && d.images.length ? { list: d.images, src: 'sale' } : null))
        .then(hit => hit || get('/album?brain=' + b)
          .then(d => ({ list: (d && d.images) || [], src: 'local' })))
        .then(res => { this.images = res.list; this.src = res.src; return this.images; })
        .catch(() => { this.images = []; this.src = 'local'; return this.images; });
    }
    return this.loading;
  }
  _show() {
    if (!this.images.length) {
      this.img.removeAttribute('src');
      this.cap.textContent = 'Album trống';
      this.el.querySelector('.ja-hint').textContent = 'kiểm tra kết nối Sale Album hoặc thả ảnh vào brain "' + this.brain + '"';
      const fig = this.el.querySelector('figure');
      fig.innerHTML = '<div class="ja-empty">Chưa lấy được ảnh nào<br><b>H2O Sale Album · ' + this.brain + '</b><br><span style="font-size:11px;opacity:.7">kiểm tra mạng/Supabase hoặc thả ảnh vào attachments/ của brain rồi vuốt lại</span></div>';
      return;
    }
    const it = this.images[this.i];
    // Ảnh sale có url tuyệt đối (R2) -> tải thẳng; ảnh local có path -> qua /files/raw.
    this.img.src = /^https?:/i.test(it.url || '')
      ? it.url
      : '/files/raw?brain=' + encodeURIComponent(this.brain) + '&path=' + encodeURIComponent(it.path);
    this.img.alt = it.alt || it.name;
    this.cap.textContent = (this.i + 1) + ' / ' + this.images.length + ' · ' + it.name;
    this.setZoom(1);
  }
  async open() {
    if (this.opened || this.disposed) return;
    this.opened = true;
    if (!this.el) this._build();
    this.host.classList.add('album-open');
    this.onState(true);
    await this._load();
    if (!this.opened) return;               // đóng trong lúc chờ fetch
    this.i = 0;
    this._show();
  }
  close() {
    if (!this.opened) return;
    this.opened = false;
    this.host.classList.remove('album-open');
    this.onState(false);
  }
  next() { if (!this.opened || !this.images || !this.images.length) return;
    this.i = (this.i + 1) % this.images.length; this._show(); }
  prev() { if (!this.opened || !this.images || !this.images.length) return;
    this.i = (this.i - 1 + this.images.length) % this.images.length; this._show(); }
  swipe(dir) {
    if (!this.opened) { if (dir === 'right' || dir === 'left') this.open(); return; }
    if (dir === 'right') this.next();
    else if (dir === 'left') this.prev();
    else if (dir === 'down') this.close();
  }
  // Zoom liên tục từ khoảng cách 2 đầu ngón (pinchRatio trong kết quả tracking).
  zoomFromRatio(ratio) {
    if (!this.opened || !Number.isFinite(ratio)) return;
    const z = ZOOM_MIN + (ZOOM_MAX - ZOOM_MIN) * clamp((ratio - RATIO_LO) / (RATIO_HI - RATIO_LO), 0, 1);
    this.setZoom(z);
  }
  setZoom(z) {
    this.zoom = clamp(z, ZOOM_MIN, ZOOM_MAX);
    if (this.el) this.el.style.setProperty('--ja-zoom', String(this.zoom));
  }
  dispose() { this.disposed = true; this.close(); if (this.el) this.el.remove(); this.el = null; }
}
