// Surface "students" trong khoang não (.hud-center): thẻ học viên từ H2O Book
// (app Next.js trên Vercel). Mở bằng giọng nói ("mở thông tin học viên lên màn
// hình") qua tool joyce_ui action=open_surface -> JoyceScreen.open('students').
// Dữ liệu: GET /ext/h2obook/students?q= — Joyce server gọi /api/public/v1/students
// của app bằng key h2o_* (scope students:read); trình duyệt KHÔNG cầm key.
// 2 tầng: lưới thẻ học viên (có ô tìm theo tên/SĐT) -> thẻ chi tiết.
// Vuốt xuống = lùi 1 tầng / đóng; vuốt trái/phải ở tầng chi tiết = học viên
// trước/sau. Pinch không dùng (danh sách, không phải ảnh).
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export class JoyceStudents {
  constructor({ host, onState = () => {} } = {}) {
    if (!host) throw new TypeError('JoyceStudents cần host (.hud-center).');
    this.host = host; this.onState = onState;
    this.el = null; this.students = null; this.mode = '';
    this.i = 0; this.level = 0;
    this.q = ''; this.qTimer = 0;
    this.loading = null; this.opened = false; this.disposed = false;
  }
  isOpen() { return this.opened; }
  _build() {
    const el = document.createElement('div');
    el.className = 'joyce-album js-students';
    el.innerHTML =
      '<div class="ja-bar">' +
        '<button class="ja-back" data-x="back" aria-label="Quay lại">‹ QUAY</button>' +
        '<span class="ja-title"></span>' +
        '<input class="js-q" type="search" placeholder="tìm tên / SĐT..." aria-label="Tìm học viên">' +
        '<button class="ja-x" data-x="close" aria-label="Đóng">✕</button>' +
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
    });
    const q = el.querySelector('.js-q');
    q.addEventListener('input', () => {
      clearTimeout(this.qTimer);
      this.qTimer = setTimeout(() => { this.q = q.value.trim(); this.students = null; this._reload(); }, 350);
    });
    q.addEventListener('keydown', e => e.stopPropagation());
    this.host.appendChild(el);
    this.el = el;
    this.body = el.querySelector('.ja-body');
    this.hint = el.querySelector('.ja-hint');
    this.title = el.querySelector('.ja-title');
    this.backBtn = el.querySelector('.ja-back');
    this.qEl = q;
    return el;
  }
  async _load() {
    if (this.students) return;
    if (!this.loading) {
      this.loading = fetch('/ext/h2obook/students?q=' + encodeURIComponent(this.q),
        { credentials: 'same-origin' })
        .then(r => (r.ok ? r.json() : null))
        .then(d => {
          this.students = (d && d.students) || [];
          this.mode = (d && d.mode) || '';
          this.err = d && d.error ? (d.detail || d.error) : '';
          if (!d) this.err = 'server không trả lời';
        })
        .catch(() => { this.students = []; this.err = 'không gọi được Joyce server'; });
    }
    return this.loading;
  }
  _reload() {
    if (!this.opened) return;
    this.loading = null; this.level = 0;
    this._renderLoading();
    this._load().then(() => { if (this.opened) { this.i = 0; this._render(); } });
  }
  _pick(idx) {
    if (this.level !== 0) return;
    this.i = idx; this.level = 1; this._render();
  }
  back() {
    if (this.level === 1) { this.level = 0; this._render(); return; }
    this.close();
  }
  _status(st) {
    const s = String(st || '').toLowerCase();
    if (s === 'active' || s === 'hoạt động') return '<em class="js-ok">ĐANG HỌC</em>';
    if (s === 'invited' || s === 'pending') return '<em class="js-wait">MỜI</em>';
    return st ? '<em>' + esc(st).toUpperCase() + '</em>' : '';
  }
  _grid() {
    if (!this.students.length) return '<div class="ja-empty">' +
      (this.q ? 'Không có học viên nào khớp "' + esc(this.q) + '"' : 'Chưa có học viên nào') +
      '<br><b>H2O Book</b></div>';
    return '<div class="ja-grid">' + this.students.map((s, n) =>
      '<button class="ja-card js-card" data-pick="' + n + '">' +
        '<span class="js-ava">' + esc((s.name || '?').trim().charAt(0).toUpperCase()) + '</span>' +
        '<span class="ja-info"><b>' + esc(s.name) + '</b>' +
        '<i>' + esc(s.stage || s.phone || s.email || '—') + '</i>' +
        this._status(s.status) + '</span>' +
      '</button>').join('') + '</div>';
  }
  _detail() {
    const s = this.students[this.i];
    if (!s) { this.level = 0; this._render(); return; }
    const n = this.students.length;
    this.body.innerHTML =
      '<div class="ja-view"><div class="js-detail">' +
        '<button class="ja-nav js-prev" data-x="prev" aria-label="Học viên trước">◀</button>' +
        '<div class="js-profile">' +
          '<span class="js-ava js-ava-big">' + esc((s.name || '?').trim().charAt(0).toUpperCase()) + '</span>' +
          '<h3>' + esc(s.name) + '</h3>' + this._status(s.status) +
          '<dl>' +
            (s.stage ? '<dt>Giai đoạn</dt><dd>' + esc(s.stage) + '</dd>' : '') +
            (s.phone ? '<dt>SĐT</dt><dd>' + esc(s.phone) + '</dd>' : '') +
            (s.email ? '<dt>Email</dt><dd>' + esc(s.email) + '</dd>' : '') +
            (s.progress ? '<dt>Tiến độ</dt><dd>' + esc(s.progress) + '%</dd>' : '') +
            (s.joinedAt ? '<dt>Tham gia</dt><dd>' + esc(String(s.joinedAt).slice(0, 10)) + '</dd>' : '') +
          '</dl>' +
        '</div>' +
        '<button class="ja-nav js-next" data-x="next" aria-label="Học viên tiếp">▶</button>' +
        '<div class="js-pos">' + (this.i + 1) + ' / ' + n + '</div>' +
      '</div></div>';
  }
  _renderLoading() {
    this.body.innerHTML = '<div class="ja-empty">đang tải danh sách học viên...</div>';
  }
  _render() {
    if (!this.el) return;
    this.backBtn.style.display = this.level > 0 ? '' : 'none';
    this.qEl.style.display = this.level === 0 ? '' : 'none';
    if (this.err) {
      this.title.textContent = 'H2O BOOK · HỌC VIÊN';
      this.hint.textContent = '';
      this.body.innerHTML = '<div class="ja-empty">' + esc(this.err) + '<br>' +
        '<span style="font-size:11px;opacity:.7">tạo API key ở trang Enterprise của H2O Book ' +
        'rồi đặt h2obook.api_key trong settings.json của Joyce</span></div>';
      return;
    }
    if (this.level === 0) {
      this.title.textContent = 'H2O BOOK · ' + this.students.length + ' HỌC VIÊN';
      this.hint.textContent = 'click chọn học viên · gõ tìm theo tên/SĐT · vuốt xuống: đóng';
      this.body.innerHTML = this._grid();
      return;
    }
    const s = this.students[this.i];
    this.title.textContent = (s ? s.name : 'HỌC VIÊN').toUpperCase();
    this.hint.textContent = 'vuốt/◀ ▶: học viên trước-sau · vuốt xuống: về danh sách';
    this._detail();
  }
  async open() {
    if (this.opened || this.disposed) return;
    this.opened = true;
    if (!this.el) this._build();
    this.host.classList.add('album-open');
    this.onState(true);
    this._renderLoading();
    await this._load();
    if (!this.opened) return;
    this.i = 0; this.level = 0;
    this._render();
  }
  close() {
    if (!this.opened) return;
    this.opened = false;
    this.host.classList.remove('album-open');
    this.onState(false);
  }
  next() { if (!this.opened || this.level !== 1) return;
    const n = this.students.length; if (!n) return;
    this.i = (this.i + 1) % n; this._render(); }
  prev() { if (!this.opened || this.level !== 1) return;
    const n = this.students.length; if (!n) return;
    this.i = (this.i - 1 + n) % n; this._render(); }
  swipe(dir) {
    if (!this.opened) { if (dir === 'right' || dir === 'left') this.open(); return; }
    if (dir === 'down') { this.back(); return; }
    if (this.level === 1) { if (dir === 'right') this.next(); else if (dir === 'left') this.prev(); }
  }
  zoomFromRatio() {}   // danh sách không zoom; giữ tên hàm để JoyceScreen gọi thống nhất
  dispose() { this.disposed = true; clearTimeout(this.qTimer); this.close();
    if (this.el) this.el.remove(); this.el = null; }
}
