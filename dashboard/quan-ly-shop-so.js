/* Quản lý Shop: nối các module của trang mẫu vào SỔ THẬT của Joyce (API /shop/so/*, xem server/shop_so.py).
   Trang mẫu (quan-ly-shop.html) vẽ số cứng; file này thay các hàm vẽ module bằng bản đọc dữ liệu thật,
   hiện agent của từng phòng trên văn phòng ảo, và để trống (có chú thích) những module chưa nối.
   Nạp SAU script chính của trang, TRƯỚC đoạn nhúng CRM. */
(function () {
  'use strict';

  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const vnd = n => Math.round(Number(n) || 0).toLocaleString('vi-VN') + ' đ';
  const homNay = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
  const kyNay = () => homNay().slice(0, 7);
  const HD = { bao_gia: 'Báo giá', da_ky: 'Đã ký', hoan_thanh: 'Hoàn thành', huy: 'Hủy' };
  const HD_CLASS = { bao_gia: 'warn', da_ky: '', hoan_thanh: 'purple', huy: 'red' };
  const VAI = { sales: 'Sales', chup: 'Thợ chụp', makeup: 'Makeup', hotro: 'Hỗ trợ / hậu kỳ', khac: 'Khác' };
  const BG = { nhap: 'Nháp', da_gui: 'Đã gửi', chap_nhan: 'Chấp nhận', huy: 'Hủy' };
  const GV = { todo: 'Chưa làm', doing: 'Đang làm', done: 'Xong' };
  const VIEC = { todo: 'Chưa làm', doing: 'Đang làm', review: 'Chờ duyệt', done: 'Xong' };

  async function api(path, opts) {
    const r = await fetch(path, Object.assign({ credentials: 'same-origin' }, opts || {}));
    let j = null;
    try { j = await r.json(); } catch (e) { /* không phải JSON */ }
    if (!r.ok) throw new Error((j && (j.detail || j.error)) || ('Lỗi ' + r.status));
    return j;
  }
  const get = p => api(p);
  const post = (p, o) => {
    const fd = new FormData();
    Object.keys(o || {}).forEach(k => fd.append(k, o[k] !== null && typeof o[k] === 'object' ? JSON.stringify(o[k]) : o[k]));
    return api(p, { method: 'POST', body: fd });
  };
  const loi = e => toast(String((e && e.message) || e));

  const view = () => document.getElementById('moduleView');
  let cur = 0, seq = 0;
  const ui = { fin: 'quy', hr: 'ns', cv: 'bang', cvPhong: '', ky: kyNay(), luong: kyNay() };

  const css = document.createElement('style');
  css.textContent = [
    '.so-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:0 0 14px}',
    '.so-strip .kpi{min-height:70px;padding:11px}.so-strip strong{font-size:15px}',
    '.so-feed{margin:16px 0}.so-feed h3{margin:0 0 10px}',
    '.so-row{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #edf0ee;font-size:12px}',
    '.so-row:last-child{border-bottom:0}.so-row .t{color:#8a948e;min-width:54px;font-size:11px}',
    '.so-row b{color:#17201b}.so-row small{display:block;color:#707b74;margin-top:2px}',
    '.so-pill{display:inline-block;padding:2px 7px;border-radius:12px;background:#eef1ef;color:#58645d;font-size:10px;margin-left:6px}',
    '.room3d.working{filter:brightness(1.12);box-shadow:0 0 0 3px #fff9,0 0 24px 6px #ffd54f88}',
    '.room3d.working .worker{animation:soBounce .7s ease-in-out infinite alternate}',
    '@keyframes soBounce{from{transform:translateY(0)}to{transform:translateY(-6px)}}',
    '.so-empty{padding:34px 18px;text-align:center;color:#707b74;font-size:13px;line-height:1.6}',
    '.so-empty b{display:block;color:#17201b;font-size:15px;margin-bottom:6px}',
    '.so-cols{display:grid;grid-template-columns:repeat(4,1fr);gap:11px}',
    '.so-cols>div{background:#f4f6f4;border-radius:12px;padding:10px;min-height:140px}',
    '.so-cols h4{margin:0 0 9px;font-size:12px;color:#58645d}',
    '.so-mini{border:0;background:#eef1ef;border-radius:7px;padding:4px 8px;font-size:11px;cursor:pointer;margin:6px 4px 0 0}',
    '.so-note{font-size:11px;color:#707b74;margin:8px 0}',
    '#chatBox,.deploy{display:none!important}',
    '@media(max-width:680px){.so-strip{grid-template-columns:1fr 1fr}.so-cols{grid-template-columns:1fr}}'
  ].join('');
  document.head.appendChild(css);

  /* ---------------- hộp thoại nhỏ ---------------- */
  function modal(title, body, onSave, saveLabel) {
    closeModal();
    document.body.insertAdjacentHTML('beforeend',
      '<div class="modal" id="modal"><div class="modal-card"><div class="toolbar"><h3 style="margin:0;flex:1">' + esc(title) +
      '</h3><button class="ghost" onclick="closeModal()">×</button></div>' + body +
      '<div class="modal-actions"><button class="ghost" onclick="closeModal()">Hủy</button><button class="primary" id="soSave">' + esc(saveLabel || 'Lưu') + '</button></div></div></div>');
    document.getElementById('soSave').onclick = async () => {
      try { await onSave(); closeModal(); rerender(); } catch (e) { loi(e); }
    };
  }
  const val = id => (document.getElementById(id) || {}).value || '';
  const rerender = () => { if (cur) renderModule(cur); };
  function empty(i, title, desc, note) {
    return moduleHead('▫', title, desc) + '<div class="panel"><div class="so-empty"><b>Chưa nối dữ liệu thật</b>' + esc(note) + '</div></div>';
  }
  async function guard(i, fn) {
    const mine = ++seq; cur = i;
    view().innerHTML = '<div class="panel"><div class="so-empty">Đang tải...</div></div>';
    try {
      const html = await fn();
      if (mine === seq) view().innerHTML = html;
    } catch (e) {
      if (mine === seq) view().innerHTML = '<div class="panel"><div class="so-empty"><b>Không đọc được sổ</b>' + esc(e.message) +
        '<br>Nếu vừa cập nhật Joyce, hãy khởi động lại Joyce rồi nhấn Ctrl+F5.</div></div>';
    }
  }
  const hdOptions = (ds, chon) => '<option value="">Không gắn hợp đồng</option>' + ds.filter(h => h.trang_thai !== 'huy')
    .map(h => '<option value="' + esc(h.ma) + '"' + (h.ma === chon ? ' selected' : '') + '>' + esc(h.ma + ' · ' + h.ten_khach + ' · ' + vnd(h.gia_tri)) + '</option>').join('');
  const kyOptions = chon => { const o = []; const d = new Date(); for (let k = 0; k < 8; k++) { const t = new Date(d.getFullYear(), d.getMonth() - k, 1); const v = t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0'); o.push('<option value="' + v + '"' + (v === chon ? ' selected' : '') + '>Tháng ' + v.slice(5) + '/' + v.slice(0, 4) + '</option>'); } o.push('<option value="all"' + (chon === 'all' ? ' selected' : '') + '>Tất cả</option>'); return o.join(''); };

  /* ---------------- Thu chi và công nợ ---------------- */
  async function mFinance() {
    const [tq, quy, hds] = await Promise.all([get('/shop/so/tong-quan?ky=' + ui.ky), get('/shop/so/quy?ky=' + ui.ky), get('/shop/so/hop-dong')]);
    const cho = quy.items.filter(x => x.trang_thai === 'cho_duyet');
    const ghi = quy.items.filter(x => x.trang_thai === 'da_ghi');
    const tab = (k, t) => '<button class="' + (ui.fin === k ? 'active' : '') + '" onclick="soFin(\'' + k + '\')">' + t + '</button>';
    let body = '';
    if (ui.fin === 'no') {
      const no = hds.items.filter(h => (h.trang_thai === 'da_ky' || h.trang_thai === 'hoan_thanh') && h.con_no > 0);
      body = no.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>HỢP ĐỒNG</th><th>KHÁCH</th><th>GIÁ TRỊ</th><th>ĐÃ THU</th><th>CÒN NỢ</th></tr></thead><tbody>' +
        no.map(h => '<tr><td>' + esc(h.ma) + '</td><td>' + esc(h.ten_khach) + '</td><td>' + vnd(h.gia_tri) + '</td><td>' + vnd(h.thu) + '</td><td style="color:#e33150"><b>' + vnd(h.con_no) + '</b></td></tr>').join('') +
        '</tbody></table></div>' : '<div class="so-empty">Không có khách nào còn nợ.</div>';
    } else {
      const rows = (ui.fin === 'duyet' ? cho : quy.items);
      body = rows.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>NGÀY</th><th>THU / CHI</th><th>HẠNG MỤC</th><th>DIỄN GIẢI</th><th>SỐ TIỀN</th><th>PHÒNG GHI</th><th></th></tr></thead><tbody>' +
        rows.map(x => '<tr><td>' + esc(x.ngay) + '</td><td><span class="badge ' + (x.loai === 'chi' ? 'red' : '') + '">' + (x.loai === 'chi' ? 'Chi' : 'Thu') + '</span>' +
          (x.trang_thai === 'cho_duyet' ? '<span class="badge warn" style="margin-left:4px">Chờ duyệt</span>' : x.trang_thai === 'tu_choi' ? '<span class="badge red" style="margin-left:4px">Từ chối</span>' : '') + '</td><td>' + esc(x.hang_muc) + '</td><td>' +
          esc(x.dien_giai) + (x.hop_dong_ma ? '<small style="display:block;color:#707b74">' + esc(x.hop_dong_ma + ' · ' + x.hop_dong_khach) + '</small>' : '') + '</td><td style="color:' + (x.loai === 'thu' ? '#15955a' : '#e33150') + '"><b>' + vnd(x.so_tien) + '</b></td><td><small>' + esc(x.phong || '') + '</small></td><td>' +
          (x.trang_thai === 'cho_duyet' ? '<button class="so-mini" onclick="soDuyet(' + x.id + ',\'duyet\')">Duyệt</button><button class="so-mini" onclick="soDuyet(' + x.id + ',\'tu_choi\')">Từ chối</button>' : '') +
          '<button class="so-mini" title="Xóa phiếu" onclick="soXoaQuy(' + x.id + ')">×</button></td></tr>').join('') + '</tbody></table></div>' :
        '<div class="so-empty"><b>Chưa có phiếu nào trong kỳ này</b>Bấm "+ Phiếu thu" hoặc nhắn cho Joyce: "thu 15 triệu hợp đồng Tuấn Thủy".</div>';
    }
    return moduleHead('▣', 'Thu chi & công nợ', 'Sổ quỹ thật: phòng Thu và phòng Chi ghi, chủ duyệt các khoản chi lớn của nhân viên.') +
      kpis([['⊕', 'Tổng thu', vnd(tq.thu), 'đã ghi sổ'], ['⊙', 'Tổng chi', vnd(tq.chi), 'đã ghi sổ'], ['▣', 'Lãi gộp', vnd(tq.lai_gop), 'thu trừ chi'], ['♨', 'Công nợ khách', vnd(tq.cong_no), cho.length ? cho.length + ' khoản chi chờ duyệt' : '']]) +
      '<div class="subnav">' + tab('quy', '▤ Sổ quỹ　' + ghi.length) + tab('duyet', '◉ Chờ duyệt　' + cho.length) + tab('no', '♨ Công nợ khách') + '</div>' +
      '<div class="panel"><div class="toolbar"><button class="primary" onclick="soPhieu(\'thu\')">＋ Phiếu thu</button><button class="danger" onclick="soPhieu(\'chi\')">− Phiếu chi</button><select class="field" style="margin-left:auto" onchange="soKy(this.value)">' + kyOptions(ui.ky) + '</select></div>' + body + '</div>';
  }
  window.soFin = k => { ui.fin = k; rerender(); };
  window.soKy = v => { ui.ky = v; rerender(); };
  window.soDuyet = async (id, q) => { try { await post('/shop/so/quy/duyet', { id, quyet: q }); toast(q === 'duyet' ? 'Đã duyệt, khoản chi vào sổ' : 'Đã từ chối'); rerender(); } catch (e) { loi(e); } };
  window.soXoaQuy = async id => { if (!confirm('Xóa phiếu này khỏi sổ?')) return; try { await post('/shop/so/quy/xoa', { id }); rerender(); } catch (e) { loi(e); } };
  window.soPhieu = async loai => {
    let ds = []; try { ds = (await get('/shop/so/hop-dong')).items; } catch (e) { /* vẫn cho ghi không gắn */ }
    modal(loai === 'thu' ? 'Phiếu thu' : 'Phiếu chi',
      '<div class="form-grid"><label style="grid-column:1/-1">Số tiền (đồng) *<input class="field" id="soTien" type="number" min="1" autofocus></label>' +
      '<label>Hạng mục<input class="field" id="soHm" value="' + (loai === 'thu' ? 'Thanh toán hợp đồng' : 'Chi khác') + '"></label>' +
      '<label>Ngày<input class="field" id="soNgay" type="date" value="' + homNay() + '"></label>' +
      '<label style="grid-column:1/-1">Gắn hợp đồng<select class="field" id="soHd">' + hdOptions(ds, '') + '</select></label>' +
      '<label style="grid-column:1/-1">Diễn giải<input class="field" id="soDg" placeholder="' + (loai === 'thu' ? 'Khách chuyển khoản cọc' : 'Tiền setup studio') + '"></label></div>',
      async () => {
        const r = await post('/shop/so/su-kien', { data: { loai, so_tien: val('soTien'), hang_muc: val('soHm'), ngay: val('soNgay'), hop_dong: val('soHd'), dien_giai: val('soDg') } });
        if (!r.ok) throw new Error(r.loi.map(x => x.loi).join('; '));
        toast(r.ket_qua[0].tom_tat);
      }, 'Ghi phiếu');
  };

  /* ---------------- Đơn bán hàng = hợp đồng ---------------- */
  async function mOrders() {
    const [hds, tq] = await Promise.all([get('/shop/so/hop-dong'), get('/shop/so/tong-quan?ky=all')]);
    const ds = hds.items;
    const rows = ds.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>MÃ</th><th>KHÁCH</th><th>GÓI</th><th>GIÁ TRỊ</th><th>ĐÃ THU</th><th>ĐÃ CHI</th><th>LÃI GỘP</th><th>TRẠNG THÁI</th><th></th></tr></thead><tbody>' +
      ds.map(h => '<tr><td><b>' + esc(h.ma) + '</b><small style="display:block;color:#707b74">' + esc(h.ngay) + '</small></td><td>' + esc(h.ten_khach) + '<small style="display:block;color:#707b74">' + esc(h.sdt) + '</small></td><td>' + esc(h.goi) + '</td><td>' + vnd(h.gia_tri) + '</td><td>' + vnd(h.thu) + '</td><td>' + vnd(h.chi) + '</td><td><b style="color:' + (h.lai_gop >= 0 ? '#15955a' : '#e33150') + '">' + vnd(h.lai_gop) + '</b></td><td><select class="field" onchange="soHdTs(' + h.id + ',this.value)">' +
        Object.keys(HD).map(k => '<option value="' + k + '"' + (k === h.trang_thai ? ' selected' : '') + '>' + HD[k] + '</option>').join('') + '</select></td><td><button class="so-mini" onclick="soPhanCong(' + h.id + ',\'' + esc(h.ma) + '\')">Phân công</button><button class="so-mini" onclick="soChiaViec(' + h.id + ')">Chia việc</button><button class="so-mini" onclick="soBaoCao(' + h.id + ')">Đối soát</button></td></tr>').join('') + '</tbody></table></div>' :
      '<div class="so-empty"><b>Chưa có hợp đồng nào</b>Nhắn cho Joyce: "thêm hợp đồng Tuấn Thủy 0899252392, gói chụp ảnh studio 15 triệu" hoặc bấm "+ Hợp đồng".</div>';
    return moduleHead('🛒', 'Đơn bán hàng', 'Mỗi hợp đồng là một đơn: báo giá, ký, thu tiền, chi phí và lãi gộp. Khách lấy từ CRM, Sales ghi.') +
      kpis([['◉', 'Đã ký', String(tq.hop_dong.da_ky + tq.hop_dong.hoan_thanh), tq.hop_dong.hoan_thanh + ' hoàn thành'], ['▤', 'Đang báo giá', String(tq.hop_dong.bao_gia), 'tiềm năng ' + vnd(tq.pipeline)], ['⊕', 'Đã thu', vnd(tq.thu)], ['♨', 'Khách còn nợ', vnd(tq.cong_no)]]) +
      '<div class="panel"><div class="toolbar"><button class="primary" onclick="soHopDong()">＋ Hợp đồng</button></div>' + rows + '</div>';
  }
  window.soHopDong = () => modal('Hợp đồng mới',
    '<div class="form-grid"><label>Tên khách *<input class="field" id="soTen" autofocus></label><label>Số điện thoại<input class="field" id="soSdt"></label>' +
    '<label style="grid-column:1/-1">Gói / dịch vụ *<input class="field" id="soGoi" placeholder="Gói chụp ảnh studio"></label>' +
    '<label>Giá trị (đồng) *<input class="field" id="soGia" type="number" min="0"></label><label>Trạng thái<select class="field" id="soTs"><option value="bao_gia">Báo giá</option><option value="da_ky">Đã ký</option></select></label></div>' +
    '<p class="so-note">Khách tự vào CRM của phòng Sales (không tạo trùng nếu số điện thoại đã có).</p>',
    async () => {
      const r = await post('/shop/so/su-kien', { data: { loai: 'hop_dong', ten: val('soTen'), sdt: val('soSdt'), goi: val('soGoi'), gia_tri: val('soGia'), trang_thai: val('soTs') } });
      if (!r.ok) throw new Error(r.loi.map(x => x.loi).join('; '));
      toast(r.ket_qua[0].tom_tat);
    }, 'Tạo hợp đồng');
  window.soHdTs = async (id, ts) => { try { await post('/shop/so/hop-dong/trang-thai', { id, trang_thai: ts }); toast('Đã chuyển sang ' + HD[ts]); rerender(); } catch (e) { loi(e); } };
  window.soBaoCao = async id => { try { const r = await post('/shop/so/hop-dong/bao-cao', { id }); toast(r.ket_qua); } catch (e) { loi(e); } };
  window.soPhanCong = async (id, ma) => {
    let ns = []; try { ns = (await get('/shop/so/nhan-su')).items.filter(n => !n.nghi); } catch (e) { return loi(e); }
    if (!ns.length) return toast('Chưa có nhân sự. Vào "Nhân sự & lương" thêm người hoặc nạp nhân sự mẫu.');
    modal('Phân công cho ' + ma,
      '<div class="form-grid"><label style="grid-column:1/-1">Nhân sự<select class="field" id="soNs">' + ns.map(n => '<option value="' + esc(n.ten) + '">' + esc(n.ten + ' · ' + (VAI[n.vai] || n.vai)) + '</option>').join('') + '</select></label>' +
      '<label style="grid-column:1/-1">Vai trong hợp đồng<select class="field" id="soVai"><option value="">Theo vai của người đó</option>' + Object.keys(VAI).map(k => '<option value="' + k + '">' + VAI[k] + '</option>').join('') + '</select></label></div>' +
      '<p class="so-note">Phân công theo phần trăm. Muốn trả hoa hồng cố định theo từng đầu việc thì dùng nút "Chia việc". Hoa hồng chỉ có khi hợp đồng Đã ký.</p>',
      async () => { await post('/shop/so/phan-cong', { hop_dong_id: id, ten: val('soNs'), vai: val('soVai') }); toast('Đã phân công'); }, 'Phân công');
  };

  /* ---------------- Báo giá ---------------- */
  async function mQuotes() {
    const [bg, hds] = await Promise.all([get('/shop/so/bao-gia'), get('/shop/so/hop-dong')]);
    window.__soHd = hds.items;
    const rows = bg.items.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>SỐ</th><th>KHÁCH</th><th>NỘI DUNG</th><th>TỔNG</th><th>TRẠNG THÁI</th><th></th></tr></thead><tbody>' +
      bg.items.map(b => '<tr><td><b>' + esc(b.so) + '</b><small style="display:block;color:#707b74">' + esc(b.ngay) + '</small></td><td>' + esc(b.ten_khach) + '<small style="display:block;color:#707b74">' + esc(b.sdt) + '</small></td><td>' +
        esc(b.dong.map(d => d.ten + (d.sl > 1 ? ' x' + d.sl : '')).join(', ')) + '</td><td><b>' + vnd(b.tong) + '</b></td><td><select class="field" onchange="soBgTs(' + b.id + ',this.value)">' +
        Object.keys(BG).map(k => '<option value="' + k + '"' + (k === b.trang_thai ? ' selected' : '') + '>' + BG[k] + '</option>').join('') + '</select></td><td><button class="so-mini" onclick="soBgSua(' + b.id + ')">Sửa</button><button class="so-mini" onclick="soBgIn(' + b.id + ')">In / PDF</button></td></tr>').join('') + '</tbody></table></div>' :
      '<div class="so-empty"><b>Chưa có báo giá nào</b>Hợp đồng ở trạng thái "Báo giá" tự có báo giá nháp, hoặc bấm "+ Báo giá".</div>';
    window.__soBg = bg.items;
    return moduleHead('▤', 'Báo giá & hóa đơn', 'Lập báo giá, đổi trạng thái, in hoặc lưu PDF. Khách chấp nhận thì hợp đồng tự chuyển Đã ký.') +
      kpis([['▤', 'Báo giá', String(bg.items.length)], ['◴', 'Đang chờ khách', String(bg.items.filter(b => b.trang_thai === 'nhap' || b.trang_thai === 'da_gui').length)],
        ['✓', 'Đã chấp nhận', String(bg.items.filter(b => b.trang_thai === 'chap_nhan').length)], ['◉', 'Tổng giá trị chờ', vnd(bg.items.filter(b => b.trang_thai === 'nhap' || b.trang_thai === 'da_gui').reduce((s, b) => s + b.tong, 0))]]) +
      '<div class="panel"><div class="toolbar"><button class="primary" onclick="soBgSua(0)">＋ Báo giá</button></div>' + rows + '</div>';
  }
  window.soBgTs = async (id, ts) => { try { await post('/shop/so/bao-gia/trang-thai', { id, trang_thai: ts }); toast('Báo giá: ' + BG[ts]); rerender(); } catch (e) { loi(e); } };
  const dongRow = (d = {}) => '<div class="form-grid soDong" style="grid-template-columns:3fr 1fr 2fr;margin-bottom:6px"><input class="field q-ten" placeholder="Hàng hóa / dịch vụ" value="' + esc(d.ten || '') + '"><input class="field q-sl" type="number" min="0" step="any" value="' + (d.sl || 1) + '"><input class="field q-gia" type="number" min="0" placeholder="Đơn giá" value="' + (d.don_gia || '') + '"></div>';
  window.soBgThemDong = () => document.getElementById('soDongs').insertAdjacentHTML('beforeend', dongRow());
  window.soBgSua = id => {
    const b = id ? (window.__soBg || []).find(x => x.id === id) : null;
    modal(b ? 'Sửa báo giá ' + b.so : 'Báo giá mới',
      '<div class="form-grid"><label>Tên khách<input class="field" id="soKh" value="' + esc(b ? b.ten_khach : '') + '"></label><label>Số điện thoại<input class="field" id="soKs" value="' + esc(b ? b.sdt : '') + '"></label>' +
      '<label style="grid-column:1/-1">Gắn hợp đồng<select class="field" id="soBh">' + hdOptions(window.__soHd || [], '') + '</select></label></div><h4 style="margin:12px 0 6px">Hàng hóa / dịch vụ</h4><div id="soDongs">' +
      (b ? b.dong : [{}]).map(dongRow).join('') + '</div><button class="outline" type="button" onclick="soBgThemDong()">＋ Thêm dòng</button>' +
      '<div class="form-grid" style="margin-top:10px"><label>Giảm giá (%)<input class="field" id="soGiam" type="number" min="0" max="100" value="' + (b ? b.giam : 0) + '"></label><label>VAT (%)<input class="field" id="soVat" type="number" min="0" max="30" value="' + (b ? b.vat : 0) + '"></label>' +
      '<label style="grid-column:1/-1">Ghi chú<textarea class="field" id="soGc" style="width:100%">' + esc(b ? b.ghi_chu : 'Báo giá có hiệu lực trong 7 ngày.') + '</textarea></label></div>',
      async () => {
        const dong = [...document.querySelectorAll('.soDong')].map(r => ({ ten: r.querySelector('.q-ten').value, sl: r.querySelector('.q-sl').value, don_gia: r.querySelector('.q-gia').value })).filter(d => d.ten.trim());
        await post('/shop/so/bao-gia', { data: { id: b ? b.id : 0, ten_khach: val('soKh'), sdt: val('soKs'), hop_dong: val('soBh'), dong, giam: val('soGiam'), vat: val('soVat'), ghi_chu: val('soGc'), trang_thai: b ? b.trang_thai : 'nhap' } });
        toast('Đã lưu báo giá');
      }, 'Lưu báo giá');
  };
  window.soBgIn = id => {
    const b = (window.__soBg || []).find(x => x.id === id); if (!b) return;
    const w = window.open('', '_blank'); if (!w) return toast('Trình duyệt chặn cửa sổ in');
    const sub = b.dong.reduce((s, d) => s + d.sl * d.don_gia, 0), giam = sub * b.giam / 100, vat = (sub - giam) * b.vat / 100;
    w.document.write('<!doctype html><meta charset="utf-8"><title>' + esc(b.so) + '</title><body style="font:14px sans-serif;max-width:720px;margin:30px auto"><h1>BÁO GIÁ ' + esc(b.so) + '</h1><p>Ngày ' + esc(b.ngay) + '<br>Khách: <b>' + esc(b.ten_khach) + '</b> ' + esc(b.sdt) + '</p><table style="width:100%;border-collapse:collapse"><tr style="background:#eee"><th align=left>Nội dung</th><th>SL</th><th align=right>Đơn giá</th><th align=right>Thành tiền</th></tr>' +
      b.dong.map(d => '<tr><td>' + esc(d.ten) + '</td><td align=center>' + d.sl + '</td><td align=right>' + vnd(d.don_gia) + '</td><td align=right>' + vnd(d.sl * d.don_gia) + '</td></tr>').join('') +
      '</table><p align=right>Tạm tính ' + vnd(sub) + '<br>Giảm ' + b.giam + '%: -' + vnd(giam) + '<br>VAT ' + b.vat + '%: ' + vnd(vat) + '<br><b style="font-size:18px">Tổng ' + vnd(b.tong) + '</b></p><p>' + esc(b.ghi_chu) + '</p></body>');
    w.document.close(); w.focus(); w.print();
  };

  /* ---------------- Nhân sự và lương ---------------- */
  async function mHr() {
    const [ns, lg] = await Promise.all([get('/shop/so/nhan-su'), get('/shop/so/luong?ky=' + ui.luong)]);
    const cfg = ns.cau_hinh;
    const tab = (k, t) => '<button class="' + (ui.hr === k ? 'active' : '') + '" onclick="soHr(\'' + k + '\')">' + t + '</button>';
    let body = '';
    if (ui.hr === 'luong') {
      body = '<div class="toolbar"><select class="field" onchange="soLuongKy(this.value)">' + kyOptions(ui.luong) + '</select><span class="so-note" style="margin-left:auto">Hoa hồng theo từng đầu việc đã chia (tab Hoa hồng & việc); người chưa được chia việc thì tính ' + (lg.co_so_hh === 'lai_gop' ? 'phần trăm trên LÃI GỘP' : 'phần trăm trên DOANH THU ĐÃ THU') + ' của hợp đồng Đã ký.</span></div>' +
        (lg.dong.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>NHÂN SỰ</th><th>LƯƠNG CƠ BẢN</th><th>HỢP ĐỒNG</th><th>HOA HỒNG</th><th>TỔNG NHẬN</th></tr></thead><tbody>' +
          lg.dong.map(d => '<tr><td><b>' + esc(d.ten) + '</b><small style="display:block;color:#707b74">' + esc(d.chuc_vu) + '</small></td><td>' + vnd(d.luong_cb) + '</td><td>' +
            (d.chi_tiet.length ? d.chi_tiet.map(c => '<small style="display:block">' + esc(c.ma + ' · ' + c.ten_khach + ' · ' + (c.loai === 'cong_viec' ? c.cong_viec + (c.so_luong > 1 ? ' x' + c.so_luong : '') + ' · ' + vnd(c.so_tien) : c.ty_le + '% x ' + vnd(c.co_so))) + '</small>').join('') : '<small>chưa có</small>') + '</td><td>' + vnd(d.hoa_hong) + '</td><td><b>' + vnd(d.tong) + '</b></td></tr>').join('') +
          '<tr><td colspan="3"><b>Cộng</b></td><td><b>' + vnd(lg.tong_hoa_hong) + '</b></td><td><b>' + vnd(lg.tong_luong) + '</b></td></tr></tbody></table></div>' : '<div class="so-empty">Chưa có nhân sự để tính lương.</div>');
    } else if (ui.hr === 'cfg') {
      body = '<div class="form-grid"><label style="grid-column:1/-1">Hoa hồng tính trên<select class="field" id="soCs"><option value="lai_gop"' + (cfg.co_so_hh === 'lai_gop' ? ' selected' : '') + '>Lãi gộp (thu trừ chi của hợp đồng)</option><option value="doanh_thu"' + (cfg.co_so_hh === 'doanh_thu' ? ' selected' : '') + '>Doanh thu đã thu</option></select></label>' +
        Object.keys(VAI).filter(k => k !== 'khac').map(k => '<label>Tỉ lệ ' + VAI[k] + ' (%)<input class="field so-ty" data-vai="' + k + '" type="number" min="0" max="100" step="0.5" value="' + cfg.ty_le_vai[k] + '"></label>').join('') +
        '<label style="grid-column:1/-1">Hạn mức duyệt chi của nhân viên (đồng)<input class="field" id="soNguong" type="number" min="0" value="' + cfg.nguong_chi + '"></label></div>' +
        '<p class="so-note">Tỉ lệ riêng đặt ở hồ sơ từng người sẽ đè tỉ lệ theo vai. Chủ báo chi thì ghi luôn; nhân viên báo từ hạn mức này trở lên thì chờ chủ duyệt.</p><button class="primary" onclick="soLuuCfg()">Lưu cấu hình</button>';
    } else {
      body = (ns.items.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>HỌ TÊN</th><th>CHỨC VỤ</th><th>VAI</th><th>LƯƠNG CƠ BẢN</th><th>TỈ LỆ HOA HỒNG</th><th></th></tr></thead><tbody>' +
        ns.items.map(n => '<tr><td><b>' + esc(n.ten) + '</b>' + (n.mau ? '<span class="so-pill">mẫu</span>' : '') + (n.nghi ? '<span class="so-pill">đã nghỉ</span>' : '') + '<small style="display:block;color:#707b74">' + esc(n.phong_ban) + ' ' + esc(n.sdt) + '</small></td><td>' + esc(n.chuc_vu) + '</td><td>' + esc(VAI[n.vai] || n.vai) + '</td><td>' + vnd(n.luong_cb) + '</td><td>' + (n.ty_le == null ? cfg.ty_le_vai[n.vai] + '% (theo vai)' : n.ty_le + '%') + '</td><td><button class="so-mini" onclick="soNs(' + n.id + ')">Sửa</button><button class="so-mini" onclick="soNsXoa(' + n.id + ')">×</button></td></tr>').join('') + '</tbody></table></div>' :
        '<div class="so-empty"><b>Chưa có nhân sự</b>Bấm "+ Nhân sự", hoặc "Nạp nhân sự mẫu" để thử tính lương.</div>');
      window.__soNs = ns.items;
    }
    const coMau = ns.items.some(n => n.mau);
    return moduleHead('♟', 'Nhân sự & lương', 'Hồ sơ nhân sự, phân công theo hợp đồng và bảng lương có hoa hồng tính tự động từ sổ.') +
      kpis([['♙', 'Nhân sự đang làm', String(ns.items.filter(n => !n.nghi).length)], ['▣', 'Lương cơ bản', vnd(lg.dong.reduce((s, d) => s + d.luong_cb, 0))], ['⊕', 'Hoa hồng kỳ này', vnd(lg.tong_hoa_hong)], ['◉', 'Tổng lương kỳ ' + lg.ky, vnd(lg.tong_luong)]]) +
      '<div class="subnav">' + tab('ns', '♙ Nhân sự') + tab('luong', '▤ Bảng lương') + tab('cfg', '⚙ Tỉ lệ & hạn mức') + '</div>' +
      '<div class="panel">' + (ui.hr === 'ns' ? '<div class="toolbar"><button class="primary" onclick="soNs(0)">＋ Nhân sự</button>' + (coMau ? '<button class="outline" onclick="soMauXoa()">Xóa nhân sự mẫu</button>' : '<button class="outline" onclick="soMau()">Nạp nhân sự mẫu để thử tính lương</button>') + '</div>' : '') + body + '</div>';
  }
  window.soHr = k => { ui.hr = k; rerender(); };
  window.soLuongKy = v => { ui.luong = v; rerender(); };
  window.soMau = async () => { try { const r = await post('/shop/so/mau', {}); toast('Đã nạp ' + r.da_nap + ' nhân sự mẫu'); rerender(); } catch (e) { loi(e); } };
  window.soMauXoa = async () => { try { const r = await post('/shop/so/mau/xoa', {}); toast('Đã xóa ' + r.da_xoa + ' nhân sự mẫu'); rerender(); } catch (e) { loi(e); } };
  window.soNsXoa = async id => { if (!confirm('Xóa nhân sự này và các phân công của họ?')) return; try { await post('/shop/so/nhan-su/xoa', { id }); rerender(); } catch (e) { loi(e); } };
  window.soLuuCfg = async () => {
    const ty = {}; document.querySelectorAll('.so-ty').forEach(i => { ty[i.dataset.vai] = i.value; });
    try { await post('/shop/so/cau-hinh', { data: { co_so_hh: val('soCs'), ty_le_vai: ty, nguong_chi: val('soNguong') } }); toast('Đã lưu cấu hình'); rerender(); } catch (e) { loi(e); }
  };
  window.soNs = id => {
    const n = id ? (window.__soNs || []).find(x => x.id === id) : null;
    modal(n ? 'Sửa nhân sự' : 'Nhân sự mới',
      '<div class="form-grid"><label style="grid-column:1/-1">Họ tên *<input class="field" id="nTen" value="' + esc(n ? n.ten : '') + '"></label><label>Chức vụ<input class="field" id="nCv" value="' + esc(n ? n.chuc_vu : '') + '"></label>' +
      '<label>Vai<select class="field" id="nVai">' + Object.keys(VAI).map(k => '<option value="' + k + '"' + (n && n.vai === k ? ' selected' : '') + '>' + VAI[k] + '</option>').join('') + '</select></label>' +
      '<label>Phòng ban<input class="field" id="nPb" value="' + esc(n ? n.phong_ban : '') + '"></label><label>Điện thoại<input class="field" id="nSdt" value="' + esc(n ? n.sdt : '') + '"></label>' +
      '<label>Lương cơ bản (đồng)<input class="field" id="nLuong" type="number" min="0" value="' + (n ? n.luong_cb : 0) + '"></label><label>Tỉ lệ hoa hồng riêng (%)<input class="field" id="nTy" type="number" min="0" max="100" step="0.5" placeholder="theo vai" value="' + (n && n.ty_le != null ? n.ty_le : '') + '"></label>' +
      '<label style="grid-column:1/-1"><input id="nNghi" type="checkbox"' + (n && n.nghi ? ' checked' : '') + '> Đã nghỉ việc</label></div>',
      async () => { await post('/shop/so/nhan-su', { data: { id: n ? n.id : 0, ten: val('nTen'), chuc_vu: val('nCv'), vai: val('nVai'), phong_ban: val('nPb'), sdt: val('nSdt'), luong_cb: val('nLuong'), ty_le: val('nTy'), nghi: document.getElementById('nNghi').checked } }); toast('Đã lưu nhân sự'); });
  };

  /* ---------------- Hoa hồng & việc ---------------- */
  async function mCommission() {
    const [cv, gv, lg] = await Promise.all([get('/shop/so/cong-viec'), get('/shop/so/giao-viec'), get('/shop/so/luong?ky=' + ui.luong)]);
    window.__soCv = cv.items;
    const tab = (k, t) => '<button class="' + (ui.cv === k ? 'active' : '') + '" onclick="soCvTab(\'' + k + '\')">' + t + '</button>';
    const phongTen = ma => cv.phong[ma] || ma;
    let body = '';
    if (ui.cv === 'chia') {
      body = '<div class="toolbar"><button class="primary" onclick="soChiaViec(0)">＋ Chia việc</button><span class="so-note" style="margin-left:auto">Hợp đồng còn ở "Báo giá" thì chưa tính hoa hồng, ký xong mới vào bảng lương.</span></div>' +
        (gv.items.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>HỢP ĐỒNG</th><th>VIỆC</th><th>NGƯỜI LÀM</th><th>SL</th><th>HOA HỒNG</th><th>HẠN</th><th>TRẠNG THÁI</th><th></th></tr></thead><tbody>' +
          gv.items.map(g => '<tr><td><b>' + esc(g.hop_dong_ma || '') + '</b><small style="display:block;color:#707b74">' + esc(g.ten_khach || '') + (g.hd_trang_thai === 'bao_gia' ? ' · chờ ký' : '') + '</small></td><td>' + esc(g.ten) + '<small style="display:block;color:#707b74">' + esc(phongTen(g.ma_phong)) + '</small></td><td>' + esc(g.nhan_su_ten || '') + '</td><td>' + g.so_luong + '</td><td><b>' + vnd(g.hoa_hong * g.so_luong) + '</b>' + (g.phi_them ? '<small style="display:block;color:#707b74">thu thêm khách ' + vnd(g.phi_them * g.so_luong) + '</small>' : '') + '</td><td>' + esc(g.han || '') + '</td><td><select class="field" onchange="soGvTs(' + g.id + ',this.value)">' +
            Object.keys(GV).map(k => '<option value="' + k + '"' + (k === g.trang_thai ? ' selected' : '') + '>' + GV[k] + '</option>').join('') + '</select></td><td><button class="so-mini" onclick="soGvXoa(' + g.id + ')">×</button></td></tr>').join('') + '</tbody></table></div>' :
          '<div class="so-empty"><b>Chưa chia việc nào</b>Bấm "+ Chia việc", hoặc nhắn Joyce: "hợp đồng HD0001 giao Makeup cô dâu cho Lan, chụp ngoại cảnh cho Huy".</div>');
    } else if (ui.cv === 'tong') {
      const mine = lg.dong.map(d => ({ d, vs: d.chi_tiet.filter(c => c.loai === 'cong_viec'), pt: d.chi_tiet.filter(c => c.loai !== 'cong_viec') })).filter(x => x.vs.length || x.pt.length);
      body = '<div class="toolbar"><select class="field" onchange="soLuongKy(this.value)">' + kyOptions(ui.luong) + '</select><span class="so-note" style="margin-left:auto">Tính theo tháng ký hợp đồng. Số này là số vào bảng lương ở "Nhân sự & lương".</span></div>' +
        (mine.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>NHÂN SỰ</th><th>SỐ VIỆC</th><th>HOA HỒNG THEO VIỆC</th><th>HOA HỒNG PHẦN TRĂM</th><th>TỔNG</th></tr></thead><tbody>' +
          mine.map(x => '<tr><td><b>' + esc(x.d.ten) + '</b><small style="display:block;color:#707b74">' + esc(x.d.chuc_vu) + '</small></td><td>' + x.vs.length + ' (' + x.vs.filter(v => v.xong).length + ' xong)</td><td>' + vnd(x.vs.reduce((t, v) => t + v.so_tien, 0)) + '</td><td>' + vnd(x.pt.reduce((t, v) => t + v.so_tien, 0)) + '</td><td><b>' + vnd(x.d.hoa_hong) + '</b></td></tr>').join('') +
          '<tr><td colspan="4"><b>Cộng</b></td><td><b>' + vnd(lg.tong_hoa_hong) + '</b></td></tr></tbody></table></div>' : '<div class="so-empty"><b>Kỳ này chưa có hoa hồng</b>Cần hợp đồng Đã ký trong tháng và có người được chia việc hoặc phân công.</div>');
    } else {
      const ds = cv.items.filter(c => !ui.cvPhong || c.ma_phong === ui.cvPhong);
      const ps = Object.keys(cv.phong);
      cv.items.forEach(c => { if (ps.indexOf(c.ma_phong) < 0) ps.push(c.ma_phong); });
      body = '<div class="toolbar"><button class="primary" onclick="soCv(0)">＋ Đầu việc</button><button class="outline" onclick="soCvNap()">Bổ sung các việc còn thiếu từ bảng H2O</button>' +
        '<select class="field" onchange="soCvLoc(this.value)" style="margin-left:auto"><option value="">Tất cả phòng</option>' + ps.map(m => '<option value="' + esc(m) + '"' + (m === ui.cvPhong ? ' selected' : '') + '>' + esc(phongTen(m)) + '</option>').join('') + '</select></div>' +
        (ds.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th>PHÒNG</th><th>NHÓM</th><th>TÊN VIỆC</th><th>PHÍ THU THÊM KHÁCH</th><th>HOA HỒNG</th><th>SỐ NGÀY</th><th></th></tr></thead><tbody>' +
          ds.map(c => '<tr' + (c.ap_dung ? '' : ' style="opacity:.5"') + '><td>' + esc(phongTen(c.ma_phong)) + '<small style="display:block;color:#707b74">' + esc(c.ma_phong) + '</small></td><td>' + esc(c.nhom) + '</td><td><b>' + esc(c.ten) + '</b>' + (c.ap_dung ? '' : '<span class="so-pill">tạm ngưng</span>') + '</td><td>' + (c.phi_them ? vnd(c.phi_them) : '<span style="color:#9aa39e">0</span>') + '</td><td>' + (c.hoa_hong ? '<b>' + vnd(c.hoa_hong) + '</b>' : '<span style="color:#9aa39e">0</span>') + '</td><td>' + c.so_ngay + '</td><td><button class="so-mini" onclick="soCv(' + c.id + ')">Sửa</button><button class="so-mini" onclick="soCvXoa(' + c.id + ')">×</button></td></tr>').join('') + '</tbody></table></div>' :
          '<div class="so-empty"><b>Chưa có đầu việc nào</b>Bấm "+ Đầu việc" hoặc "Bổ sung các việc còn thiếu từ bảng H2O".</div>');
    }
    const mo = gv.items.filter(g => g.trang_thai !== 'done').length;
    return moduleHead('％', 'Hoa hồng & việc', 'Bảng đầu việc theo phòng kèm hoa hồng cố định mỗi việc. Chia việc cho từng hợp đồng, hoa hồng tự vào bảng lương.') +
      kpis([['▤', 'Đầu việc trong bảng', String(cv.items.length), cv.items.filter(c => c.hoa_hong > 0).length + ' việc có hoa hồng'], ['☑', 'Việc đã chia', String(gv.items.length), mo + ' chưa xong'], ['⊕', 'Hoa hồng kỳ ' + lg.ky, vnd(lg.tong_hoa_hong)], ['◉', 'Người được tính', String(lg.dong.filter(d => d.hoa_hong > 0).length)]]) +
      '<div class="subnav">' + tab('bang', '▤ Bảng việc & hoa hồng') + tab('chia', '☑ Việc đã chia') + tab('tong', '％ Hoa hồng từng người') + '</div><div class="panel">' + body + '</div>';
  }
  window.soCvTab = k => { ui.cv = k; rerender(); };
  window.soCvLoc = v => { ui.cvPhong = v; rerender(); };
  window.soCvNap = async () => { try { const r = await post('/shop/so/cong-viec/nap-h2o', {}); toast(r.da_nap ? 'Đã bổ sung ' + r.da_nap + ' việc' : 'Bảng đã đủ, không thiếu việc nào'); rerender(); } catch (e) { loi(e); } };
  window.soCvXoa = async id => { if (!confirm('Xóa đầu việc khỏi bảng? Các việc đã chia vẫn giữ số tiền cũ.')) return; try { await post('/shop/so/cong-viec/xoa', { id }); rerender(); } catch (e) { loi(e); } };
  window.soGvTs = async (id, ts) => { try { await post('/shop/so/giao-viec/buoc', { id, trang_thai: ts }); rerender(); } catch (e) { loi(e); } };
  window.soGvXoa = async id => { if (!confirm('Gỡ việc này? Hoa hồng của việc cũng mất.')) return; try { await post('/shop/so/giao-viec/xoa', { id }); rerender(); } catch (e) { loi(e); } };
  window.soCv = id => {
    const c = id ? (window.__soCv || []).find(x => x.id === id) : null;
    const mas = ['MAKEUP', 'PHOTO', 'PTS', 'OUT', 'WDRESS'];
    modal(c ? 'Sửa đầu việc' : 'Đầu việc mới',
      '<div class="form-grid"><label>Mã phòng *<input class="field" id="cMa" list="cMaList" value="' + esc(c ? c.ma_phong : (ui.cvPhong || 'MAKEUP')) + '"><datalist id="cMaList">' + mas.map(m => '<option value="' + m + '">').join('') + '</datalist></label>' +
      '<label>Nhóm công việc<input class="field" id="cNhom" value="' + esc(c ? c.nhom : '') + '"></label>' +
      '<label style="grid-column:1/-1">Tên công việc *<input class="field" id="cTen" value="' + esc(c ? c.ten : '') + '"></label>' +
      '<label>Phí thu thêm khách (đồng)<input class="field" id="cPhi" type="number" min="0" value="' + (c ? c.phi_them : 0) + '"></label>' +
      '<label>Hoa hồng (đồng mỗi việc)<input class="field" id="cHh" type="number" min="0" value="' + (c ? c.hoa_hong : 0) + '"></label>' +
      '<label>Số ngày làm<input class="field" id="cNgay" type="number" min="1" value="' + (c ? c.so_ngay : 1) + '"></label>' +
      '<label><input id="cAp" type="checkbox"' + (!c || c.ap_dung ? ' checked' : '') + '> Đang áp dụng</label></div>' +
      '<p class="so-note">Đổi giá chỉ áp dụng cho việc chia từ nay; việc đã chia giữ số tiền lúc chia.</p>',
      async () => { await post('/shop/so/cong-viec', { data: { id: c ? c.id : 0, ma_phong: val('cMa'), nhom: val('cNhom'), ten: val('cTen'), phi_them: val('cPhi'), hoa_hong: val('cHh'), so_ngay: val('cNgay'), ap_dung: document.getElementById('cAp').checked ? 1 : 0 } }); toast('Đã lưu đầu việc'); });
  };
  window.soChiaViec = async hid => {
    let hds = [], ns = [], cvs = [];
    try { [hds, ns, cvs] = await Promise.all([get('/shop/so/hop-dong'), get('/shop/so/nhan-su'), get('/shop/so/cong-viec')]); } catch (e) { return loi(e); }
    hds = hds.items.filter(h => h.trang_thai !== 'huy'); ns = ns.items.filter(n => !n.nghi); cvs = cvs.items.filter(c => c.ap_dung);
    if (!hds.length) return toast('Chưa có hợp đồng nào để chia việc.');
    if (!ns.length) return toast('Chưa có nhân sự. Vào "Nhân sự & lương" thêm người trước.');
    const nhom = {}; cvs.forEach(c => { (nhom[c.phong_ten] = nhom[c.phong_ten] || []).push(c); });
    modal('Chia việc cho hợp đồng',
      '<div class="form-grid"><label style="grid-column:1/-1">Hợp đồng *<select class="field" id="gHd">' + hds.map(h => '<option value="' + esc(h.ma) + '"' + (h.id === hid ? ' selected' : '') + '>' + esc(h.ma + ' · ' + h.ten_khach + ' · ' + h.goi) + '</option>').join('') + '</select></label>' +
      '<label style="grid-column:1/-1">Đầu việc *<select class="field" id="gCv">' + Object.keys(nhom).map(k => '<optgroup label="' + esc(k) + '">' + nhom[k].map(c => '<option data-ma="' + esc(c.ma_phong) + '" value="' + esc(c.ten) + '">' + esc(c.ten + ' · hoa hồng ' + vnd(c.hoa_hong)) + '</option>').join('') + '</optgroup>').join('') + '</select></label>' +
      '<label>Người làm *<select class="field" id="gNs">' + ns.map(n => '<option value="' + esc(n.ten) + '">' + esc(n.ten + ' · ' + (VAI[n.vai] || n.vai)) + '</option>').join('') + '</select></label>' +
      '<label>Số lượng<input class="field" id="gSl" type="number" min="1" step="any" value="1"></label>' +
      '<label>Hạn (để trống = hôm nay + số ngày của việc)<input class="field" id="gHan" type="date"></label></div>' +
      '<p class="so-note">Hoa hồng lấy đúng số trong bảng, vào bảng lương khi hợp đồng Đã ký. Người đã được chia việc ở hợp đồng này thì không bị cộng thêm phần trăm.</p>',
      async () => {
        const sel = document.getElementById('gCv'); const op = sel.options[sel.selectedIndex];
        const r = await post('/shop/so/su-kien', { data: { loai: 'giao_viec', hop_dong: val('gHd'), cong_viec: val('gCv'), ma_phong: op ? op.dataset.ma : '', ten: val('gNs'), so_luong: val('gSl'), han: val('gHan') } });
        if (!r.ok) throw new Error(r.loi.map(x => x.loi).join('; '));
        toast(r.ket_qua[0].tom_tat);
      }, 'Chia việc');
  };

  /* ---------------- Công việc ---------------- */
  async function mTasks() {
    const vs = (await get('/shop/so/viec')).items;
    const homnay = homNay();
    const cot = k => '<div><h4>' + VIEC[k] + '　' + vs.filter(v => v.trang_thai === k).length + '</h4>' + vs.filter(v => v.trang_thai === k).map(v =>
      '<div class="task-card"><b>' + esc(v.tieu_de) + '</b><span style="color:#707b74">' + esc(v.du_an || '') + (v.giao_cho ? ' · ' + esc(v.giao_cho) : '') + '</span>' +
      (v.han ? '<div style="margin-top:4px;color:' + (v.han < homnay && k !== 'done' ? '#e33150' : '#707b74') + '">Hạn ' + esc(v.han) + '</div>' : '') +
      '<div>' + Object.keys(VIEC).filter(x => x !== k).map(x => '<button class="so-mini" onclick="soViec(' + v.id + ',\'' + x + '\')">→ ' + VIEC[x] + '</button>').join('') + '<button class="so-mini" onclick="soViecXoa(' + v.id + ')">×</button></div></div>').join('') + '</div>';
    const qua = vs.filter(v => v.trang_thai !== 'done' && v.han && v.han < homnay).length;
    return moduleHead('☑', 'Công việc & dự án', 'Bảng việc theo hợp đồng và dự án. Joyce tạo việc khi anh nhắn "nhắc gọi khách Tuấn Thủy hôm thứ sáu".') +
      kpis([['▭', 'Đang mở', String(vs.filter(v => v.trang_thai !== 'done').length)], ['◷', 'Đang làm', String(vs.filter(v => v.trang_thai === 'doing').length)], ['♨', 'Quá hạn', String(qua)], ['✓', 'Đã xong', String(vs.filter(v => v.trang_thai === 'done').length)]]) +
      '<div class="panel"><div class="toolbar"><button class="primary" onclick="soViecMoi()">＋ Việc mới</button></div>' + (vs.length ? '<div class="so-cols">' + Object.keys(VIEC).map(cot).join('') + '</div>' : '<div class="so-empty"><b>Chưa có việc nào</b>Bấm "+ Việc mới" hoặc nhắn cho Joyce.</div>') + '</div>';
  }
  window.soViec = async (id, ts) => { try { await post('/shop/so/viec/buoc', { id, trang_thai: ts }); rerender(); } catch (e) { loi(e); } };
  window.soViecXoa = async id => { try { await post('/shop/so/viec/xoa', { id }); rerender(); } catch (e) { loi(e); } };
  window.soViecMoi = () => modal('Việc mới',
    '<div class="form-grid"><label style="grid-column:1/-1">Tiêu đề *<input class="field" id="vTd" autofocus></label><label>Dự án / hợp đồng<input class="field" id="vDa" placeholder="HD0001 hoặc Việc chung"></label><label>Giao cho<input class="field" id="vGc"></label>' +
    '<label>Hạn<input class="field" id="vHan" type="date"></label><label>Ưu tiên<select class="field" id="vUt"><option value="">Thường</option><option>Gấp</option></select></label></div>',
    async () => { const r = await post('/shop/so/su-kien', { data: { loai: 'viec', tieu_de: val('vTd'), du_an: val('vDa'), giao_cho: val('vGc'), han: val('vHan'), uu_tien: val('vUt') } }); if (!r.ok) throw new Error(r.loi.map(x => x.loi).join('; ')); toast('Đã tạo việc'); });

  /* ---------------- Tổng quan bán hàng ---------------- */
  async function mSales() {
    const [tq, quy] = await Promise.all([get('/shop/so/tong-quan?ky=' + ui.ky), get('/shop/so/quy?ky=' + ui.ky + '&loai=chi&trang_thai=da_ghi')]);
    const theo = {}; quy.items.forEach(x => { theo[x.hang_muc || 'Chi khác'] = (theo[x.hang_muc || 'Chi khác'] || 0) + x.so_tien; });
    const top = Object.entries(theo).sort((a, b) => b[1] - a[1]).slice(0, 6), max = top.length ? top[0][1] : 1;
    const hd = tq.hop_dong;
    return moduleHead('◴', 'Tổng quan bán hàng', 'Doanh thu, lãi gộp, hợp đồng và công nợ, tính từ sổ thu chi và hợp đồng thật.') +
      '<div class="panel" style="margin-bottom:16px"><b style="font-size:12px">Cần xử lý</b>　' + (tq.cho_duyet ? '<span class="badge warn">◉ ' + tq.cho_duyet + ' khoản chi chờ duyệt (' + vnd(tq.cho_duyet_tien) + ')</span> ' : '') +
      (tq.viec_qua_han ? '<span class="badge red">⏰ ' + tq.viec_qua_han + ' việc quá hạn</span> ' : '') + (hd.bao_gia ? '<span class="badge purple">▤ ' + hd.bao_gia + ' báo giá đang chờ khách</span>' : '') +
      (!tq.cho_duyet && !tq.viec_qua_han && !hd.bao_gia ? '<span class="so-note">Không có gì tồn đọng.</span>' : '') + '</div>' +
      kpis([['◉', 'Doanh thu kỳ ' + tq.ky, vnd(tq.thu)], ['↗', 'Lãi gộp', vnd(tq.lai_gop), 'thu ' + vnd(tq.thu) + ' trừ chi ' + vnd(tq.chi)], ['▤', 'Hợp đồng đã ký', String(hd.da_ky + hd.hoan_thanh), hd.hoan_thanh + ' hoàn thành'], ['♧', 'Khách còn nợ', vnd(tq.cong_no)]]) +
      '<div class="grid-2"><div class="panel"><h3>Phễu hợp đồng</h3>' + Object.keys(HD).map(k => '<div style="font-size:12px;margin:10px 0">' + HD[k] + '<span style="float:right">' + hd[k] + '</span></div>').join('') + '<div class="so-note">Tiềm năng đang báo giá: ' + vnd(tq.pipeline) + '</div></div>' +
      '<div class="panel"><h3>Chi theo hạng mục</h3>' + (top.length ? top.map(([k, v]) => '<div style="font-size:11px;margin:10px 0">' + esc(k) + '<span style="float:right">' + vnd(v) + '</span><div class="bar"><span style="width:' + Math.round(v / max * 100) + '%"></span></div></div>').join('') : '<div class="so-empty">Chưa có khoản chi nào.</div>') + '</div></div>';
  }

  /* ---------------- Trợ lý điều hành: nhật ký agent ---------------- */
  async function mAssistant() {
    const hd = (await get('/shop/so/hoat-dong?phut=1440')).items;
    return moduleHead('★', 'Trợ lý điều hành', 'Nhật ký agent từng phòng trong 24 giờ qua: ai làm gì, bằng skill nào.') +
      '<div class="panel"><div class="so-note">Nhắn cho Joyce trong chat, ví dụ: "thêm hợp đồng Tuấn Thủy 0899252392 gói chụp ảnh studio 15 triệu, thu 15tr, chi 4tr setup". Joyce tách thành các việc rồi giao đúng phòng: Sales ghi khách và hợp đồng, Phòng Thu ghi thu, Phòng Chi ghi chi, Đối Soát báo cáo, Nhân Sự tính hoa hồng.</div>' + feedHtml(hd) + '</div>';
  }

  /* ---------------- các module chưa nối ---------------- */
  const CHUA = {
    4: ['Kho hàng', 'Tồn kho theo mã hàng, nhập xuất và kiểm kho.', 'Studio bán dịch vụ nên kho vật tư (đạo cụ, váy, phụ kiện) chưa có sổ thật. Sẽ nối ở bước sau; hiện không hiện số mẫu để khỏi nhầm.'],
    6: ['Hộp chat khách', 'Zalo, Facebook, Telegram.', 'Tin nhắn khách thật nằm ở trang Chatbot (Hòm thư bot) của Joyce. Module này sẽ đọc chung kho đó ở bước sau.'],
    7: ['Chăm sóc khách', 'Nhắc lại khách hỏi chưa mua, remarketing.', 'Chưa nối. Hiện việc chăm khách nằm ở CRM vận hành (tab Việc và Phân khúc).'],
    8: ['Viết marketing', 'Nội dung, lịch đăng và chiến dịch.', 'Chưa nối. Phòng Marketing của H2O đã có agent riêng ở trang Cộng sự.'],
    9: ['Ảnh AI', 'Banner, ảnh sản phẩm.', 'Chưa nối vào Shop. Tạo ảnh bằng cách nhắn Joyce trong chat (công cụ tạo ảnh có sẵn).']
  };
  const goc = typeof renderModule === 'function' ? renderModule : null;
  const MODS = { 1: mSales, 2: mOrders, 3: mQuotes, 10: mFinance, 11: mHr, 12: mTasks, 13: mAssistant, 14: mCommission };
  renderModule = function (i) {
    if (MODS[i]) { guard(i, MODS[i]); return; }
    if (CHUA[i]) { cur = 0; ++seq; view().innerHTML = empty(i, CHUA[i][0], CHUA[i][1], CHUA[i][2]); return; }
    cur = 0; ++seq;
    if (goc) goc(i);
  };

  /* ---------------- văn phòng ảo: agent đang làm ---------------- */
  const ROOM_PREFIX = { sales: ['Ban Hang', 'ThuyH2O - Marketing va Bao Gia'], customer: ['CSKH'], marketing: ['Marketing'], finance: ['Ke Toan'], people: ['Nhan Su', 'Van Thu'], tech: [] };
  const gocText = {};
  Object.keys(statusText).forEach(k => { gocText[k] = statusText[k].slice(); });
  const ago = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - t)); return s < 60 ? s + ' giây' : s < 3600 ? Math.round(s / 60) + ' phút' : Math.round(s / 3600) + ' giờ'; };
  function feedHtml(items) {
    return items.length ? items.map(a => '<div class="so-row"><span class="t">' + ago(a.created_at) + '</span><div><b>' + esc(a.agent || a.phong) + '</b><span class="so-pill">' + esc(a.phong) + '</span>' + (a.trang_thai === 'cho_duyet' ? '<span class="so-pill" style="background:#fff4dd;color:#bc7518">chờ duyệt</span>' : '') + '<small>' + esc(a.hanh_dong) + (a.skill ? ' · skill ' + esc(a.skill) : '') + '</small></div></div>').join('') :
      '<div class="so-empty"><b>Chưa có hoạt động nào</b>Nhắn cho Joyce một việc kinh doanh, các agent sẽ hiện ở đây và trên văn phòng ảo.</div>';
  }
  /* Bong bóng 3D nhỏ: chỉ lấy vế đầu của câu (trước dấu phẩy hoặc ngoặc), tối đa 26 ký tự. Đủ chữ nằm ở nhật ký agent. */
  const nganGon = t => { const v = String(t || '').split(/[,(:]/)[0].trim(); return v.length > 26 ? v.slice(0, 25) + '…' : v; };
  function phongCuaRoom(brain) { for (const k of Object.keys(ROOM_PREFIX)) if (ROOM_PREFIX[k].some(p => brain === p || brain.indexOf(p + ' ') === 0 || brain.indexOf(p + ' - ') === 0)) return k; return ''; }

  const banner = document.getElementById('sampleBanner'); if (banner) banner.style.display = 'none';
  const rooms = document.getElementById('rooms');
  const strip = document.createElement('div'); strip.className = 'so-strip'; strip.id = 'soStrip';
  const feed = document.createElement('section'); feed.className = 'panel so-feed'; feed.id = 'soFeed';
  feed.innerHTML = '<h3>Agent đang làm việc</h3><div id="soFeedBody"></div>';
  const office = document.querySelector('#overviewView .summary');
  if (office && office.parentNode) { office.parentNode.insertBefore(strip, office); }
  if (rooms && rooms.parentNode) { rooms.parentNode.insertBefore(feed, rooms); }

  let lastId = 0, busy = false;
  async function poll() {
    if (busy) return; busy = true;
    try {
      const [h, tq] = await Promise.all([get('/shop/so/hoat-dong?phut=180'), get('/shop/so/tong-quan')]);
      const k = (ic, t, v, s) => '<div class="kpi"><div class="kpi-ico">' + ic + '</div><div><small>' + t + '</small><strong>' + v + '</strong><em>' + (s || '') + '</em></div></div>';
      strip.innerHTML = k('⊕', 'Thu tháng này', vnd(tq.thu)) + k('⊙', 'Chi tháng này', vnd(tq.chi)) + k('▣', 'Lãi gộp', vnd(tq.lai_gop)) + k('▤', 'Hợp đồng', String(tq.hop_dong.da_ky + tq.hop_dong.hoan_thanh) + ' đã ký', tq.hop_dong.bao_gia + ' báo giá') + k('◉', 'Chờ duyệt', String(tq.cho_duyet), tq.cho_duyet ? vnd(tq.cho_duyet_tien) : '');
      document.getElementById('soFeedBody').innerHTML = feedHtml(h.items.slice(0, 12));
      const moi = {}; h.items.forEach(a => { const r = phongCuaRoom(a.brain); if (r && !moi[r]) moi[r] = a; });
      Object.keys(gocText).forEach(r => {
        const a = moi[r], dangLam = a && (Date.now() / 1000 - a.created_at) < 600;
        statusText[r] = dangLam ? [nganGon(a.hanh_dong)] : gocText[r].slice();
        const el = document.querySelector('.room3d.r' + state.rooms.findIndex(x => x.id === r));
        if (el) el.classList.toggle('working', !!dangLam);
        const b = document.getElementById('bubble-' + r), c = document.getElementById('card-status-' + r);
        if (b && dangLam) b.textContent = statusText[r][0]; if (c && dangLam) c.textContent = statusText[r][0];
      });
      const newest = h.items.length ? h.items[0].id : 0;
      if (newest !== lastId) {
        const first = lastId === 0; lastId = newest;
        if (!first && cur && !document.getElementById('modal') && !view().classList.contains('hide')) rerender();
      }
    } catch (e) { /* chưa có quyền hoặc máy chủ chưa khởi động lại: giữ nguyên */ }
    busy = false;
  }
  poll(); setInterval(poll, 5000);
})();
