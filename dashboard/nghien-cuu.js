/* ============================================
   Trang NGHIÊN CỨU (plan 1.3.7, T3): sáu khu đọc từ GET /nghien-cuu (server/nghien_cuu.py).

   Tổng quan · Radar xu hướng · Pipeline ý tưởng · Thư viện concept · Quy trình liên quan ·
   Nhật ký quyết định.

   CHỈ ĐỌC. Khu nào chưa có nguồn thì nói rõ ("chưa nối nguồn", "chưa có"), không vẽ số giả.
   Màu chỉ dùng token theme (--card, --line, --accent, --ok-ink...) để giao diện tối/sáng đều đọc được
   (tests/js/test_giao_dien_toi.js). Thiết kế: docs/dev/2026-10-process-factory-design.md.
   ============================================ */
(function () {
  "use strict";

  const t = (k, p) => (window.t ? window.t(k, p) : k);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const so = (n) => (n == null ? "-" : String(Number(n) || 0));

  // Khoá i18n viết đủ, không ghép chuỗi, để test_i18n.mjs kiểm được từng khoá.
  const KHU_KEY = {
    tong_quan: "nc.khu.tong_quan", radar: "nc.khu.radar", pipeline: "nc.khu.pipeline",
    thu_vien: "nc.khu.thu_vien", quy_trinh: "nc.khu.quy_trinh", nhat_ky: "nc.khu.nhat_ky",
  };
  const GIAI_DOAN_KEY = {
    moi: "nc.giai_doan.moi", "phan-tich": "nc.giai_doan.phan-tich", "ban-nhap": "nc.giai_doan.ban-nhap",
    "ra-soat": "nc.giai_doan.ra-soat", "cho-duyet": "nc.giai_doan.cho-duyet", pilot: "nc.giai_doan.pilot",
    "hoat-dong": "nc.giai_doan.hoat-dong", gac: "nc.giai_doan.gac",
  };
  const LOAI_KEY = {
    concept: "nc.loai.concept", "quy-trinh-moi": "nc.loai.quy-trinh-moi", "sua-quy-trinh": "nc.loai.sua-quy-trinh",
  };
  const giaiDoan = (g) => t(GIAI_DOAN_KEY[g] || GIAI_DOAN_KEY.moi);
  const loaiTen = (l) => t(LOAI_KEY[l] || LOAI_KEY.concept);

  const khu = (id, noi) =>
    `<section class="nc-khu" data-khu="${esc(id)}"><h3 class="nc-khu-tieu">${esc(t(KHU_KEY[id]))}</h3>${noi}</section>`;

  const trong = (khoa) => `<p class="nc-trong">${esc(t(khoa))}</p>`;

  const so1 = (n, nhan, canh) =>
    `<div class="nc-so${canh ? " nc-canh" : ""}"><b>${so(n)}</b><span>${esc(nhan)}</span></div>`;

  function tongQuan(tq) {
    return `<div class="nc-so-hang">` +
      so1(tq.y_tuong_tong, t("nc.tong.y_tuong")) +
      so1(tq.pilot_dang_chay, t("nc.tong.pilot")) +
      so1(tq.change_request_mo, t("nc.tong.cr_mo")) +
      so1(tq.sop_active, t("nc.tong.sop_hieu_luc")) +
      so1(tq.sop_qua_han, t("nc.tong.sop_qua_han"), tq.sop_qua_han > 0) +
      `</div>`;
  }

  function radar(r) {
    const muc = (r && r.muc) || [];
    if (!muc.length) return trong("nc.radar.trong");
    return `<ul class="nc-danh-sach">` + muc.map(m =>
      `<li><b>${esc(m.tieu_de)}</b> <span class="nc-phu">${esc(m.ngay)}</span></li>`).join("") + `</ul>`;
  }

  function pipeline(p) {
    const cot = (p && p.cot) || [];
    return `<div class="nc-pipeline">` + cot.map(c => {
      const the = c.the.length
        ? c.the.map(x => `<div class="nc-the"><b>${esc(x.tieu_de)}</b>` +
            `<small>${esc(loaiTen(x.loai))}${x.ngay ? " · " + esc(x.ngay) : ""}</small></div>`).join("")
        : `<p class="nc-phu">${esc(t("nc.pipeline.trong"))}</p>`;
      return `<div class="nc-cot"><div class="nc-cot-dau">${esc(giaiDoan(c.giai_doan))}` +
        `<span>${c.the.length}</span></div>${the}</div>`;
    }).join("") + `</div>`;
  }

  function thuVien(tv) {
    const ds = (tv && tv.concept) || [];
    if (!ds.length) return trong("nc.thu_vien.trong");
    return `<table class="nc-bang"><thead><tr><th>${esc(t("nc.thu_vien.cot_ten"))}</th>` +
      `<th>${esc(t("nc.thu_vien.cot_giai_doan"))}</th><th>${esc(t("nc.thu_vien.cot_booking"))}</th></tr></thead><tbody>` +
      ds.map(c => `<tr><td>${esc(c.tieu_de)}</td><td>${esc(giaiDoan(c.giai_doan))}</td>` +
        `<td>${c.booking == null ? esc(t("nc.thu_vien.booking_chua_noi")) : so(c.booking)}</td></tr>`).join("") +
      `</tbody></table>`;
  }

  function quyTrinh(qt) {
    const sop = (qt && qt.sop) || [];
    const cr = (qt && qt.change_request) || [];
    const dsSop = sop.length
      ? `<ul class="nc-danh-sach">` + sop.map(s =>
          `<li><b>${esc(s.tieu_de)}</b> <span class="nc-phu">${esc(s.phien_ban ? "v" + s.phien_ban : "")}</span> ` +
          `<span class="nc-tag">${esc(s.status === "superseded" ? t("nc.sop.superseded") : t("nc.sop.active"))}</span>` +
          (s.qua_han ? ` <span class="nc-tag nc-tag-canh">${esc(t("nc.quy_trinh.qua_han"))} ${esc(s.ngay_ra_soat)}</span>` : "") +
          `</li>`).join("") + `</ul>`
      : trong("nc.quy_trinh.trong");
    const dsCr = cr.length
      ? `<h4 class="nc-tieu-phu">${esc(t("nc.quy_trinh.cr_tieu_de"))}</h4><ul class="nc-danh-sach">` +
        cr.map(c => `<li><b>${esc(c.tieu_de)}</b> <span class="nc-phu">${esc(giaiDoan(c.giai_doan))}</span></li>`).join("") +
        `</ul>`
      : `<p class="nc-phu">${esc(t("nc.quy_trinh.cr_trong"))}</p>`;
    return dsSop + dsCr;
  }

  function nhatKy(nk) {
    const muc = (nk && nk.muc) || [];
    if (!muc.length) return trong("nc.nhat_ky.trong");
    return `<ul class="nc-danh-sach">` + muc.map(m =>
      `<li><span class="nc-phu">${esc(m.ngay)}</span> <b>${esc(m.loai)}</b> ${esc(m.tieu_de)}</li>`).join("") + `</ul>`;
  }

  async function render(el) {
    el.innerHTML = `<div class="nc-trang"><p class="nc-phu">${esc(t("nc.dang_tai"))}</p></div>`;
    let d = null;
    try {
      const r = await fetch("/nghien-cuu", { credentials: "same-origin" });
      d = await r.json();
    } catch (e) {
      d = null;
    }
    const dau = `<header class="nc-dau"><h2>${esc(t("page.nghiencuu.title"))}</h2>` +
      `<p class="nc-phu">${esc(t("page.nghiencuu.sub"))}</p></header>`;
    if (!d || !d.ok) {
      el.innerHTML = `<div class="nc-trang">${dau}<p class="nc-loi">${esc(t("nc.loi"))}</p></div>`;
      return;
    }
    if (!d.co_brain) {
      el.innerHTML = `<div class="nc-trang">${dau}${trong("nc.thieu_brain")}</div>`;
      return;
    }
    el.innerHTML = `<div class="nc-trang">${dau}` +
      khu("tong_quan", tongQuan(d.tong_quan)) +
      khu("radar", radar(d.radar)) +
      khu("pipeline", pipeline(d.pipeline)) +
      khu("thu_vien", thuVien(d.thu_vien)) +
      khu("quy_trinh", quyTrinh(d.quy_trinh)) +
      khu("nhat_ky", nhatKy(d.nhat_ky)) +
      `</div>`;
  }

  window.JoyceNghienCuu = { render };
})();
