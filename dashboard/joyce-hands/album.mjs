// Album trình chiếu trong khoang não (.hud-center), mở bằng cử chỉ vuốt tay
// hoặc nút 🖼 ALBUM trên thanh điều khiển avatar.
// Nguồn ảnh ưu tiên: GET /album?source=sale -> kho H2O Sale Album trên Supabase
// (trả cây styles -> albums -> photos với URL R2 tuyệt đối, trình duyệt tải
// thẳng từ Cloudflare). Lỗi/trống -> về nguồn local GET /album?brain=<tên>
// (attachments/ + sources/ của brain, qua /files/raw) — nguồn này phẳng nên
// nhảy thẳng vào viewer, bỏ qua lưới chọn.
// Duyệt 3 tầng giống webapp CRM: lưới concept -> lưới album -> viewer ảnh
// (mũi tên ◀ ▶ + vuốt). Vuốt xuống = lùi 1 tầng / đóng. Zoom: khoảng cách
// ngón cái-ngón trỏ (pinchRatio 0..1.5) map tuyến tính 1x..4.5x, chỉ ở tầng
// xem ảnh và chỉ có MỘT tay trong khung.
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ZOOM_MIN = 1, ZOOM_MAX = 4.5, RATIO_LO = 0.28, RATIO_HI = 0.78;
const SALE_WEB_URL = 'https://h2ostudio-sale-crm-phi.vercel.app/';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export class JoyceAlbum {
  constructor({ host, brain = 'Ban Hang - Sales Hinh Anh', onState = () => {} } = {}) {
    if (!host) throw new TypeError('JoyceAlbum cần host (.hud-center).');
    this.host = host; this.brain = brain; this.onState = onState;
    this.el = null; this.images = null; this.tree = null;
    this.i = 0; this.zoom = 1; this.src = 'local';
    this.level = 0; this.sIdx = 0; this.aIdx = 0;
    this.loading = null; this.opened = false; this.disposed = false;
  }
  isOpen() { return this.opened; }
  _build() {
    const el = document.createElement('div');
    el.className = 'joyce-album';
    el.innerHTML =
      '<div class="ja-bar">' +
        '<button class="ja-back" data-x="back" aria-label="Quay lại">‹ QUAY</button>' +
        '<span class="ja-title"></span>' +
        '<button class="ja-web" data-x="web" aria-label="Mở trang webapp đầy đủ">↗ WEBAPP</button>' +
        '<button class="ja-x" data-x="close" aria-label="Đóng album">✕</button>' +
      '</div>' +
      '<div class="ja-hint"></div>' +
      '<div class="ja-body"></div>';
    el.addEventListener('click', e => {
      const card = e.target.closest('[data-pick]');
      if (card) { this._pick(+card.dataset.pick); return; }
      const act = e.target.closest('[data-x]');
      if (!act) return;
      const a = act.dataset.x;
      if (a === 'close') this.close();
      else if (a === 'back') this.back();
      else if (a === 'prev') this.prev();
      else if (a === 'next') this.next();
      else if (a === 'web') window.open(SALE_WEB_URL, '_blank', 'noopener');
    });
    this.host.appendChild(el);
    this.el = el;
    this.body = el.querySelector('.ja-body');
    this.hint = el.querySelector('.ja-hint');
    this.title = el.querySelector('.ja-title');
    this.backBtn = el.querySelector('.ja-back');
    this.webBtn = el.querySelector('.ja-web');
    return el;
  }
  async _load() {
    if (this.images || this.tree) return;
    if (!this.loading) {
      const b = encodeURIComponent(this.brain);
      const get = u => fetch(u, { credentials: 'same-origin' })
        .then(r => (r.ok ? r.json() : null)).catch(() => null);
      this.loading = get('/album?source=sale')
        .then(d => {
          if (d && d.tree && d.tree.length) {
            // Cây 3 tầng của app sale; cũng giữ list phẳng làm dự phòng.
            this.tree = d.tree; this.images = d.images || []; this.src = 'sale';
            return;
          }
          if (d && d.images && d.images.length) {
            this.images = d.images; this.src = 'sale'; return;
          }
          return get('/album?brain=' + b).then(d2 => {
            this.images = (d2 && d2.images) || []; this.src = 'local';
          });
        })
        .catch(() => { this.images = []; this.src = 'local'; });
    }
    return this.loading;
  }
  // --- điều hướng 3 tầng -------------------------------------------------
  _pick(idx) {                       // click chọn card ở tầng lưới
    if (this.level === 0) { this.sIdx = idx; this.level = 1; }
    else if (this.level === 1) { this.aIdx = idx; this.i = 0; this.level = 2; }
    else return;
    this._render();
  }
  back() {
    if (this.level === 2 && this.tree) { this.level = 1; this._render(); return; }
    if (this.level === 1) { this.level = 0; this._render(); return; }
    this.close();
  }
  _cards(items, sub) {
    return '<div class="ja-grid">' + items.map((it, n) =>
      '<button class="ja-card" data-pick="' + n + '">' +
        (it.cover
          ? '<img src="' + esc(it.cover) + '" alt="" loading="lazy" draggable="false">'
          : '<span class="ja-nocover"></span>') +
        (it.badge ? '<span class="ja-badge">' + esc(it.badge) + '</span>' : '') +
        '<span class="ja-info"><b>' + esc(it.title) + '</b><i>' + esc(sub(it)) + '</i></span>' +
      '</button>').join('') + '</div>';
  }
  _photos() {                        // danh sách ảnh của tầng viewer hiện tại
    if (!this.tree) return this.images || [];
    const al = this.tree[this.sIdx] && this.tree[this.sIdx].albums[this.aIdx];
    return al ? al.photos : [];
  }
  _render() {
    if (!this.el) return;
    const L = this.level, sale = !!this.tree;
    this.backBtn.style.display = L > 0 ? '' : 'none';
    this.webBtn.style.display = sale ? '' : 'none';
    if (L === 0) {
      this.title.textContent = 'H2O STUDIO · CHỌN CONCEPT';
      this.hint.textContent = 'click chọn concept · vuốt xuống: đóng';
      this.body.innerHTML = this._cards(this.tree,
        s => s.albums.length + ' album');
      return;
    }
    if (L === 1) {
      const st = this.tree[this.sIdx];
      this.title.textContent = (st.title || 'CONCEPT').toUpperCase();
      this.hint.textContent = 'click chọn album · vuốt xuống: quay lại';
      this.body.innerHTML = this._cards(st.albums,
        a => a.photos.length + ' ảnh');
      return;
    }
    const al = this.tree ? this.tree[this.sIdx].albums[this.aIdx] : null;
    this.title.textContent = (al ? al.title : 'ALBUM').toUpperCase();
    this.hint.textContent = 'vuốt/◀ ▶: lật ảnh · vuốt xuống: ' +
      (sale ? 'về album' : 'đóng') + ' · xòe/chụm 2 ngón: zoom';
    this._show();
  }
  _show() {
    const list = this._photos();
    if (!list.length) {
      this.body.innerHTML = '<div class="ja-empty">Album này chưa có ảnh<br>' +
        '<b>H2O Sale Album · ' + esc(this.brain) + '</b><br>' +
        '<span style="font-size:11px;opacity:.7">kiểm tra mạng/Supabase hoặc thả ảnh vào attachments/ của brain</span></div>';
      return;
    }
    const it = list[this.i];
    const src = /^https?:/i.test(it.url || '')
      ? it.url
      : '/files/raw?brain=' + encodeURIComponent(this.brain) + '&path=' + encodeURIComponent(it.path || '');
    // Khung hình DỌC 3:4 kiểu lookbook: nền là chính ảnh đó loang mờ phủ kín
    // khung (ảnh ngang/dọc nào cũng đầy đẹp), ảnh thật sắc nét contain ở giữa,
    // mũi tên + caption bám trong khung. Zoom chỉ tác động lớp ảnh nét (.ja-fg).
    this.body.innerHTML =
      '<div class="ja-view"><div class="ja-frame">' +
        '<img class="ja-bg" alt="" draggable="false">' +
        '<img class="ja-fg" alt="" draggable="false">' +
        '<button class="ja-nav ja-prev" data-x="prev" aria-label="Ảnh trước">◀</button>' +
        '<button class="ja-nav ja-next" data-x="next" aria-label="Ảnh tiếp">▶</button>' +
        '<div class="ja-capline"><b>' + (this.i + 1) + ' / ' + list.length + '</b>' +
        '<span>' + esc(it.name || 'photo') + '</span></div>' +
      '</div></div>';
    const bg = this.body.querySelector('.ja-bg'), fg = this.body.querySelector('.ja-fg');
    bg.src = src; fg.src = src; fg.alt = it.alt || it.name || '';
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
    this.i = 0; this.sIdx = 0; this.aIdx = 0;
    this.level = this.tree ? 0 : 2;         // sale: lưới concept; local: xem phẳng luôn
    this._render();
  }
  close() {
    if (!this.opened) return;
    this.opened = false;
    this.host.classList.remove('album-open');
    this.onState(false);
  }
  next() { if (!this.opened || this.level !== 2) return;
    const n = this._photos().length; if (!n) return;
    this.i = (this.i + 1) % n; this._show(); }
  prev() { if (!this.opened || this.level !== 2) return;
    const n = this._photos().length; if (!n) return;
    this.i = (this.i - 1 + n) % n; this._show(); }
  swipe(dir) {
    if (!this.opened) { if (dir === 'right' || dir === 'left') this.open(); return; }
    if (dir === 'down') { this.back(); return; }
    if (this.level === 2) { if (dir === 'right') this.next(); else if (dir === 'left') this.prev(); }
  }
  // Zoom liên tục từ khoảng cách 2 đầu ngón (pinchRatio trong kết quả tracking).
  zoomFromRatio(ratio) {
    if (!this.opened || this.level !== 2 || !Number.isFinite(ratio)) return;
    const z = ZOOM_MIN + (ZOOM_MAX - ZOOM_MIN) * clamp((ratio - RATIO_LO) / (RATIO_HI - RATIO_LO), 0, 1);
    this.setZoom(z);
  }
  setZoom(z) {
    this.zoom = clamp(z, ZOOM_MIN, ZOOM_MAX);
    if (this.el) this.el.style.setProperty('--ja-zoom', String(this.zoom));
  }
  dispose() { this.disposed = true; this.close(); if (this.el) this.el.remove(); this.el = null; }
}
