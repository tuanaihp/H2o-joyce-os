/* ============================================
   Tab LỘ TRÌNH (1.3.9): kích hoạt lộ trình cho học viên, đọc bài theo ngày, làm bài kiểm tra,
   mentor chấm, trưởng phòng kết luận. Server: server/lo_trinh.py.

   Không gọi model ở bước nào: bài mở theo ngày, trắc nghiệm chấm bằng đáp án trong file bài học,
   đề xuất kết quả theo luật cố định. Quyền kiểm ở server; trang này chỉ ẩn nút người dùng không
   bấm được để đỡ rối.

   Màu chỉ dùng token theme (--card, --line, --accent, --ok-ink...) để giao diện tối/sáng đều đọc
   được (tests/js/test_giao_dien_toi.js). Thiết kế: docs/dev/2026-10-lo-trinh-hoc-vien-design.md.
   ============================================ */
(function () {
  "use strict";

  const t = (k, p) => (window.t ? window.t(k, p) : k);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const so = (n) => (n == null ? "-" : String(n));

  // Khoá i18n viết đủ, không ghép chuỗi, để test kiểm được từng khoá.
  const DE_XUAT_KEY = {
    dat: "lt.de_xuat.dat", can_bo_sung: "lt.de_xuat.can_bo_sung",
    truong_phong_xem_xet: "lt.de_xuat.truong_phong_xem_xet", chua_du_du_lieu: "lt.de_xuat.chua_du_du_lieu",
  };
  const KET_LUAN_KEY = {
    dat: "lt.ket_luan.dat", can_bo_sung: "lt.ket_luan.can_bo_sung", gia_han: "lt.ket_luan.gia_han",
    khong_dat: "lt.ket_luan.khong_dat", rut_lui: "lt.ket_luan.rut_lui",
  };
  const GATE1_KEY = { dat: "lt.gate1.dat", thieu: "lt.gate1.thieu", vi_pham: "lt.gate1.vi_pham" };
  const LY_DO_KEY = {
    mp_truot: "lt.ly_do.mp_truot", thieu_rubric: "lt.ly_do.thieu_rubric",
    thieu_must_pass: "lt.ly_do.thieu_must_pass", rubric_duoi_65: "lt.ly_do.rubric_duoi_65",
    rubric_65_79: "lt.ly_do.rubric_65_79", bo_bai: "lt.ly_do.bo_bai",
    kien_thuc_duoi_70: "lt.ly_do.kien_thuc_duoi_70", gate1_chua_dat: "lt.ly_do.gate1_chua_dat",
    khao_sat_thieu: "lt.ly_do.khao_sat_thieu", khao_sat_duoi_70: "lt.ly_do.khao_sat_duoi_70",
    khao_sat_duoi_san: "lt.ly_do.khao_sat_duoi_san", khao_sat_giam: "lt.ly_do.khao_sat_giam",
  };
  const LOI_KEY = {
    khong_du_quyen: "lt.loi.khong_du_quyen", khac_phong: "lt.loi.khac_phong",
    da_kich_hoat: "lt.loi.da_kich_hoat", cap_chua_co_bai: "lt.loi.cap_chua_co_bai",
    ngay_sai: "lt.loi.ngay_sai", mentor_sai: "lt.loi.mentor_sai", het_luot: "lt.loi.het_luot",
    chua_mo: "lt.loi.chua_mo", can_ly_do: "lt.loi.can_ly_do", lo_trinh_da_dong: "lt.loi.lo_trinh_da_dong",
    rubric_sai: "lt.loi.rubric_sai", khao_sat_sai: "lt.loi.khao_sat_sai", chat_id_sai: "lt.loi.chat_id_sai",
  };
  const loiChu = (ma) => t(LOI_KEY[ma] || "lt.loi.chung");

  let _el = null;
  let _tong = null;           // dữ liệu GET /lo-trinh
  let _xem = { kieu: "tong" }; // tong | hoc_vien (id) | bai (id, ngay)

  async function goi(url, body) {
    const opt = { credentials: "same-origin" };
    if (body !== undefined) {
      opt.method = "POST";
      opt.headers = { "Content-Type": "application/json" };
      opt.body = JSON.stringify(body);
    }
    try {
      const r = await fetch(url, opt);
      return await r.json();
    } catch (e) {
      return null;
    }
  }

  const khu = (id, tieuDe, noi) =>
    `<section class="lt-khu" data-khu="${esc(id)}"><h3 class="lt-khu-tieu">${esc(tieuDe)}</h3>${noi}</section>`;
  const trong = (khoa) => `<p class="lt-phu">${esc(t(khoa))}</p>`;
  const nut = (act, chu, them) =>
    `<button type="button" class="lt-nut" data-act="${esc(act)}"${them || ""}>${esc(chu)}</button>`;
  const huy = (kq) => `<span class="lt-tag lt-dx-${esc(kq)}">${esc(t(DE_XUAT_KEY[kq] || DE_XUAT_KEY.chua_du_du_lieu))}</span>`;

  // ---------------------------------------------------------------- màn tổng
  function thang(ds) {
    return `<div class="lt-thang">` + (ds || []).map(c =>
      `<div class="lt-bac${c.so_bai ? " lt-bac-co" : ""}"><b>${esc(c.ten)}</b>` +
      `<small>${c.so_bai ? esc(t("lt.thang.so_bai", { n: c.so_bai })) : esc(t("lt.thang.chua_co_bai"))}</small></div>`
    ).join("") + `</div>`;
  }

  function theHocVien(h, cuaToi) {
    const tienDo = h.so_ngay ? Math.max(0, Math.min(100, Math.round(Math.max(0, h.ngay_hien_tai) * 100 / h.so_ngay))) : 0;
    const ngay = h.ngay_hien_tai < 0 ? t("lt.the.chua_bat_dau", { ngay: h.ngay_bat_dau })
      : t("lt.the.ngay", { n: Math.min(h.ngay_hien_tai, h.so_ngay), tong: h.so_ngay });
    const hom = h.bai_hom_nay
      ? `<p class="lt-hom">${esc(t("lt.the.bai_hom_nay"))}: <b>${esc(h.bai_hom_nay.tieu_de)}</b>` +
        (h.bai_hom_nay.da_nop ? ` <span class="lt-tag lt-ok">${esc(t("lt.the.da_nop"))}</span>` : "") + `</p>`
      : "";
    const ketLuan = h.ket_luan ? `<span class="lt-tag">${esc(t(KET_LUAN_KEY[h.ket_luan] || KET_LUAN_KEY.dat))}</span>` : "";
    return `<div class="lt-the">` +
      `<div class="lt-the-dau"><b>${esc(cuaToi ? h.cap_ten : h.ten)}</b><span class="lt-phu">${esc(cuaToi ? "" : h.cap_ten)}</span></div>` +
      `<div class="lt-thanh"><span style="width:${tienDo}%"></span></div>` +
      `<p class="lt-phu">${esc(ngay)}${h.mentor_ten ? " · " + esc(t("lt.the.mentor", { ten: h.mentor_ten })) : ""}</p>` +
      hom +
      `<p class="lt-so">${esc(t("lt.the.kien_thuc"))}: <b>${esc(h.kien_thuc_tb == null ? "-" : h.kien_thuc_tb + "%")}</b>` +
      (cuaToi ? "" : ` · ${esc(t("lt.the.rubric"))}: <b>${esc(so(h.rubric_tong))}</b> ${huy(h.de_xuat)} ${ketLuan}`) + `</p>` +
      (cuaToi && h.bai_hom_nay ? nut("mo-bai", t("lt.nut.hoc_bai_hom_nay"), ` data-id="${esc(h.id)}" data-ngay="${esc(h.bai_hom_nay.ngay)}"`) : "") +
      nut("mo-hoc-vien", cuaToi ? t("lt.nut.xem_lo_trinh") : t("lt.nut.xem_cham"), ` data-id="${esc(h.id)}"`) +
      `</div>`;
  }

  function formKichHoat(d) {
    const capCo = (d.thang || []).filter(c => c.so_bai > 0);
    if (!capCo.length) return trong("lt.kich_hoat.chua_co_cap");
    if (!(d.ung_vien || []).length) return trong("lt.kich_hoat.chua_co_nv");
    const opt = (ds, giaTri, chu) => ds.map(x => `<option value="${esc(giaTri(x))}">${esc(chu(x))}</option>`).join("");
    return `<div class="lt-form" data-form="kich-hoat">` +
      `<label>${esc(t("lt.kich_hoat.nhan_vien"))}<select name="staff_id">${opt(d.ung_vien, x => x.id, x => x.ten)}</select></label>` +
      `<label>${esc(t("lt.kich_hoat.cap"))}<select name="cap_do">${opt(capCo, x => x.ma, x => x.ten)}</select></label>` +
      `<label>${esc(t("lt.kich_hoat.nhanh"))}<select name="nhanh"><option value="makeup">Makeup</option></select></label>` +
      `<label>${esc(t("lt.kich_hoat.ngay_bat_dau"))}<input type="date" name="ngay_bat_dau" value="${esc(d.hom_nay)}"></label>` +
      `<label>${esc(t("lt.kich_hoat.mentor"))}<select name="mentor_id"><option value="">${esc(t("lt.kich_hoat.chua_gan"))}</option>` +
      `${opt(d.ung_vien, x => x.id, x => x.ten)}</select></label>` +
      `<label>${esc(t("lt.kich_hoat.telegram"))}<input type="text" name="telegram_chat_id" inputmode="numeric" placeholder="${esc(t("lt.kich_hoat.telegram_ph"))}"></label>` +
      `<p class="lt-phu">${esc(t("lt.kich_hoat.goi_y_telegram"))}</p>` +
      nut("kich-hoat", t("lt.nut.kich_hoat")) + `<p class="lt-bao" data-bao="kich-hoat"></p></div>`;
  }

  function veTong(d) {
    const dau = `<header class="lt-dau"><h2>${esc(t("page.lotrinh.title"))}</h2>` +
      `<p class="lt-phu">${esc(t("page.lotrinh.sub"))}</p></header>`;
    let h = dau;
    if ((d.cua_toi || []).length) {
      h += khu("cua_toi", t("lt.khu.cua_toi"), `<div class="lt-luoi">${d.cua_toi.map(x => theHocVien(x, true)).join("")}</div>`);
    }
    if (d.vai === "quan_tri" || d.vai === "quan_ly") {
      h += khu("kich_hoat", t("lt.khu.kich_hoat"), formKichHoat(d));
    }
    if (d.vai === "quan_tri" || d.vai === "quan_ly" || (d.hoc_vien || []).length) {
      h += khu("hoc_vien", t("lt.khu.hoc_vien"), (d.hoc_vien || []).length
        ? `<div class="lt-luoi">${d.hoc_vien.map(x => theHocVien(x, false)).join("")}</div>`
        : trong("lt.hoc_vien.trong"));
    }
    if (!(d.cua_toi || []).length && d.vai !== "quan_tri" && d.vai !== "quan_ly" && !(d.hoc_vien || []).length) {
      h += trong("lt.chua_co_lo_trinh");
    }
    h += khu("thang", t("lt.khu.thang"), thang(d.thang));
    return `<div class="lt-trang">${h}</div>`;
  }

  // ---------------------------------------------------------------- màn một học viên
  function bangBai(id, ds) {
    return `<table class="lt-bang"><thead><tr><th>${esc(t("lt.bai.cot_ngay"))}</th><th>${esc(t("lt.bai.cot_tieu_de"))}</th>` +
      `<th>${esc(t("lt.bai.cot_lich"))}</th><th>${esc(t("lt.bai.cot_diem"))}</th><th></th></tr></thead><tbody>` +
      ds.map(b => `<tr><td>${esc(b.ngay)}</td><td>${esc(b.tieu_de)}</td><td>${esc(b.ngay_lich || "")}</td>` +
        `<td>${b.co_kiem_tra ? esc(b.diem == null ? (b.mo ? t("lt.bai.chua_nop") : "-") : b.diem + "%") : esc(t("lt.bai.khong_kiem_tra"))}</td>` +
        `<td>${b.mo ? nut("mo-bai", t("lt.nut.mo_bai"), ` data-id="${esc(id)}" data-ngay="${esc(b.ngay)}"`) : esc(t("lt.bai.chua_mo"))}</td></tr>`
      ).join("") + `</tbody></table>`;
  }

  function formCham(d) {
    const tg = _tong || {};
    const g1 = d.gate1 || {};
    const rub = (d.rubric && d.rubric.diem) || {};
    const mp = d.must_pass || {};
    const chon = (ds, gt) => ds.map(([v, k]) => `<option value="${esc(v)}"${v === gt ? " selected" : ""}>${esc(t(k))}</option>`).join("");
    const gate = `<div class="lt-form" data-form="gate1"><h4>${esc(t("lt.cham.gate1"))}</h4>` +
      `<label>${esc(t("lt.cham.ket_qua"))}<select name="ket_qua">` +
      chon([["dat", GATE1_KEY.dat], ["thieu", GATE1_KEY.thieu], ["vi_pham", GATE1_KEY.vi_pham]], g1.ket_qua) +
      `</select></label><label>${esc(t("lt.cham.ghi_chu"))}<input type="text" name="ghi_chu" value="${esc(g1.ghi_chu || "")}"></label>` +
      nut("luu-gate1", t("lt.nut.luu")) + `</div>`;
    const ks = `<div class="lt-form" data-form="khao-sat"><h4>${esc(t("lt.cham.khao_sat"))}</h4>` +
      `<label>${esc(t("lt.cham.tuan"))}<select name="tuan"><option>1</option><option>2</option><option>3</option><option>4</option></select></label>` +
      (tg.khao_sat || []).map(k => `<label>${esc(k.ten)}<input type="number" min="10" max="100" step="10" name="${esc(k.ma)}"></label>`).join("") +
      nut("luu-khao-sat", t("lt.nut.luu")) +
      `<p class="lt-phu">${esc(t("lt.cham.khao_sat_da", { so: Object.keys(d.khao_sat || {}).length }))}</p></div>`;
    const rubric = `<div class="lt-form" data-form="rubric"><h4>${esc(t("lt.cham.rubric"))}</h4>` +
      (tg.rubric || []).map(r => `<label>${esc(r.ten)} (${esc(r.toi_da)})<input type="number" min="0" max="${esc(r.toi_da)}" name="${esc(r.ma)}" value="${esc(rub[r.ma] == null ? "" : rub[r.ma])}"></label>`).join("") +
      nut("luu-rubric", t("lt.nut.luu")) + `</div>`;
    const must = `<div class="lt-form" data-form="must-pass"><h4>${esc(t("lt.cham.must_pass"))}</h4>` +
      (tg.must_pass || []).map(m => `<label>${esc(m.ten)}<select name="${esc(m.ma)}"><option value="">-</option>` +
        chon([["dat", "lt.mp.dat"], ["truot", "lt.mp.truot"]], mp[m.ma]) + `</select></label>`).join("") +
      nut("luu-must-pass", t("lt.nut.luu")) + `</div>`;
    return `<div class="lt-luoi-form">${gate}${ks}${rubric}${must}</div>`;
  }

  function hopDeXuat(d) {
    const dx = d.de_xuat || { ket_qua: "chua_du_du_lieu", ly_do: [] };
    const ly = (dx.ly_do || []).map(l => `<li>${esc(t(LY_DO_KEY[l.ma] || "lt.ly_do.khac", { diem: l.diem, so: l.so }))}</li>`).join("");
    return `<div class="lt-de-xuat">${huy(dx.ket_qua)}${ly ? `<ul class="lt-danh-sach">${ly}</ul>` : ""}` +
      `<p class="lt-phu">${esc(t("lt.de_xuat.chi_la_de_xuat"))}</p></div>`;
  }

  function formKetLuan(d) {
    // "Cần bổ sung" và "Gia hạn" không đóng lộ trình: hiện kết luận cũ rồi vẫn cho kết luận lại.
    const cu = d.ket_luan && d.ket_luan.ket_qua
      ? `<p>${esc(t("lt.ket_luan.da", { kq: t(KET_LUAN_KEY[d.ket_luan.ket_qua] || KET_LUAN_KEY.dat), nguoi: d.ket_luan.nguoi || "" }))}</p>`
      : "";
    if (d.tom_tat.trang_thai !== "dang_hoc") return cu;
    return cu + `<div class="lt-form" data-form="ket-luan">` +
      `<label>${esc(t("lt.ket_luan.chon"))}<select name="ket_qua">` +
      ["dat", "can_bo_sung", "gia_han", "khong_dat", "rut_lui"].map(k => `<option value="${k}">${esc(t(KET_LUAN_KEY[k]))}</option>`).join("") +
      `</select></label><label>${esc(t("lt.ket_luan.ly_do"))}<input type="text" name="ly_do"></label>` +
      nut("ket-luan", t("lt.nut.ket_luan")) + `</div>`;
  }

  function veHocVien(d) {
    const tt = d.tom_tat;
    let h = `<header class="lt-dau">${nut("ve-tong", t("lt.nut.quay_lai"))}<h2>${esc(tt.ten)} · ${esc(tt.cap_ten)}</h2>` +
      `<p class="lt-phu">${esc(t("lt.the.bat_dau", { ngay: tt.ngay_bat_dau }))}${tt.mentor_ten ? " · " + esc(t("lt.the.mentor", { ten: tt.mentor_ten })) : ""}</p></header>`;
    const kt = d.kien_thuc || {};
    h += khu("bai", t("lt.khu.bai"), `<p class="lt-so">${esc(t("lt.the.kien_thuc"))}: <b>${esc(kt.trung_binh == null ? "-" : kt.trung_binh + "%")}</b>` +
      ((kt.bo_bai || []).length ? ` · <span class="lt-tag lt-canh">${esc(t("lt.ly_do.bo_bai", { so: kt.bo_bai.length }))}</span>` : "") + `</p>` +
      bangBai(tt.id, d.bai || []));
    if (!d.ban_than) {
      h += khu("de_xuat", t("lt.khu.de_xuat"), hopDeXuat(d));
      if (d.cham_duoc && tt.trang_thai === "dang_hoc") h += khu("cham", t("lt.khu.cham"), formCham(d));
      if (d.quan_ly_duoc) {
        h += khu("nghi", t("lt.khu.nghi"), `<div class="lt-form" data-form="nghi">` +
          `<p class="lt-phu">${esc((d.ngay_nghi || []).length ? t("lt.nghi.da", { ds: d.ngay_nghi.join(", ") }) : t("lt.nghi.chua"))}</p>` +
          `<label>${esc(t("lt.nghi.ngay"))}<input type="date" name="ngay"></label>` + nut("them-nghi", t("lt.nut.them_nghi")) + `</div>`);
        h += khu("telegram", t("lt.khu.telegram"), `<div class="lt-form" data-form="telegram">` +
          `<p class="lt-phu">${esc(d.telegram_chat_id ? t("lt.tg.dang_gui", { id: d.telegram_chat_id }) : t("lt.tg.chua_co"))}</p>` +
          `<label>${esc(t("lt.kich_hoat.telegram"))}<input type="text" name="telegram_chat_id" inputmode="numeric" ` +
          `value="${esc(d.telegram_chat_id || "")}" placeholder="${esc(t("lt.kich_hoat.telegram_ph"))}"></label>` +
          `<p class="lt-phu">${esc(t("lt.kich_hoat.goi_y_telegram"))}</p>` +
          nut("luu-telegram", t("lt.nut.luu")) + nut("thu-telegram", t("lt.nut.gui_thu")) +
          `<p class="lt-bao" data-bao="telegram"></p></div>`);
        h += khu("ket_luan", t("lt.khu.ket_luan"), formKetLuan(d));
      }
    }
    h += `<p class="lt-bao" data-bao="hoc-vien"></p>`;
    return `<div class="lt-trang" data-id="${esc(tt.id)}">${h}</div>`;
  }

  // ---------------------------------------------------------------- màn bài học
  function noiDung(md) {
    if (window.mdToHtml) {
      try { return window.mdToHtml(md || "", null); } catch (e) { /* rơi xuống chữ thô */ }
    }
    return `<pre class="lt-tho">${esc(md || "")}</pre>`;
  }

  function veCauHoi(b, ketQua) {
    if (!(b.kiem_tra || []).length) return trong("lt.bai.khong_kiem_tra_ngay");
    const ct = (ketQua && ketQua.chi_tiet) || [];
    const cuoi = (b.lan_cuoi && b.lan_cuoi.tra_loi) || [];
    return `<ol class="lt-cau">` + b.kiem_tra.map((q, i) => {
      const kq = ct[i];
      const chonTruoc = kq ? kq.chon : cuoi[i];
      const dapAn = kq && kq.dap_an !== undefined ? kq.dap_an : q.dap_an;
      const giai = (kq && kq.giai_thich) || q.giai_thich;
      return `<li class="${kq ? (kq.dung ? "lt-dung" : "lt-sai") : ""}"><p>${esc(q.hoi)}</p>` +
        q.lua_chon.map((lc, j) => `<label class="lt-chon${dapAn === j ? " lt-dap-an" : ""}">` +
          `<input type="radio" name="q${i}" value="${j}"${chonTruoc === j ? " checked" : ""}${b.nop_duoc ? "" : " disabled"}> ${esc(lc)}</label>`).join("") +
        (giai && dapAn !== undefined ? `<p class="lt-giai">${esc(giai)}</p>` : "") + `</li>`;
    }).join("") + `</ol>`;
  }

  function veBai(id, b, ketQua) {
    let h = `<header class="lt-dau">${nut("mo-hoc-vien", t("lt.nut.quay_lai"), ` data-id="${esc(id)}"`)}` +
      `<h2>${esc(b.tieu_de)}</h2><p class="lt-phu">${esc(t("lt.bai.thoi_luong", { phut: b.thoi_luong_phut || 0 }))}</p></header>`;
    if ((b.muc_tieu || []).length) {
      h += khu("muc_tieu", t("lt.khu.muc_tieu"), `<ul class="lt-danh-sach">${b.muc_tieu.map(m => `<li>${esc(m)}</li>`).join("")}</ul>`);
    }
    h += `<article class="lt-noi-dung">${noiDung(b.noi_dung)}</article>`;
    let diem = "";
    if (ketQua) diem = `<p class="lt-so">${esc(t("lt.bai.ket_qua", { diem: ketQua.diem, dung: ketQua.dung, tong: ketQua.tong }))}</p>`;
    else if (b.diem != null) diem = `<p class="lt-so">${esc(t("lt.bai.diem_cao_nhat", { diem: b.diem }))}</p>`;
    const conLuot = (b.lan_toi_da || 0) - (ketQua ? ketQua.so_lan : b.so_lan || 0);
    const nopDuoc = b.nop_duoc && !(ketQua && ketQua.het_luot);
    h += khu("kiem_tra", t("lt.khu.kiem_tra"), diem + veCauHoi({ ...b, nop_duoc: nopDuoc }, ketQua) +
      (nopDuoc ? nut("nop-bai", t("lt.nut.nop_bai"), ` data-id="${esc(id)}" data-ngay="${esc(b.ngay)}"`) +
        `<p class="lt-phu">${esc(t("lt.bai.con_luot", { n: Math.max(0, conLuot) }))}</p>` : ""));
    h += `<p class="lt-bao" data-bao="bai"></p>`;
    return `<div class="lt-trang">${h}</div>`;
  }

  // ---------------------------------------------------------------- điều hướng và sự kiện
  async function moTong() {
    _xem = { kieu: "tong" };
    const d = await goi("/lo-trinh");
    _tong = d;
    const dau = `<header class="lt-dau"><h2>${esc(t("page.lotrinh.title"))}</h2></header>`;
    if (!d || !d.ok) { _el.innerHTML = `<div class="lt-trang">${dau}<p class="lt-loi">${esc(t("lt.loi.tai"))}</p></div>`; return; }
    if (!d.co_brain) { _el.innerHTML = `<div class="lt-trang">${dau}${trong("lt.thieu_brain")}</div>`; return; }
    _el.innerHTML = veTong(d);
  }

  async function moHocVien(id) {
    _xem = { kieu: "hoc_vien", id };
    if (!_tong) _tong = await goi("/lo-trinh");
    const d = await goi("/lo-trinh/hoc-vien/" + encodeURIComponent(id));
    if (!d || !d.ok) { _el.innerHTML = `<div class="lt-trang"><p class="lt-loi">${esc(loiChu(d && d.error))}</p>${nut("ve-tong", t("lt.nut.quay_lai"))}</div>`; return; }
    _el.innerHTML = veHocVien(d);
  }

  async function moBai(id, ngay, ketQua) {
    _xem = { kieu: "bai", id, ngay };
    const b = await goi(`/lo-trinh/bai/${encodeURIComponent(id)}/${encodeURIComponent(ngay)}`);
    if (!b || !b.ok) { _el.innerHTML = `<div class="lt-trang"><p class="lt-loi">${esc(loiChu(b && b.error))}</p>${nut("ve-tong", t("lt.nut.quay_lai"))}</div>`; return; }
    _el.innerHTML = veBai(id, b, ketQua);
  }

  const giaTri = (form, ten) => {
    const o = form && form.querySelector(`[name="${ten}"]`);
    return o ? o.value : "";
  };
  const bao = (ten, chu) => {
    const o = _el && _el.querySelector && _el.querySelector(`[data-bao="${ten}"]`);
    if (o) o.textContent = chu;
  };

  async function luuCham(form, body) {
    const id = _xem.id;
    const r = await goi(`/lo-trinh/hoc-vien/${encodeURIComponent(id)}/cham`, body);
    if (!r || !r.ok) { bao("hoc-vien", loiChu(r && r.error)); return; }
    await moHocVien(id);
    bao("hoc-vien", t("lt.da_luu"));
  }

  async function xuLy(e) {
    // Khung trang dùng chung giữa các tab: chỉ nhận nút nằm trong trang Lộ trình.
    const btn = e.target && e.target.closest ? e.target.closest(".lt-trang [data-act]") : null;
    if (!btn) return;
    const act = btn.getAttribute("data-act");
    const form = btn.closest("[data-form]");
    if (act === "ve-tong") return moTong();
    if (act === "mo-hoc-vien") return moHocVien(btn.getAttribute("data-id"));
    if (act === "mo-bai") return moBai(btn.getAttribute("data-id"), btn.getAttribute("data-ngay"));
    if (act === "kich-hoat") {
      const body = {};
      for (const k of ["staff_id", "cap_do", "nhanh", "ngay_bat_dau", "mentor_id", "telegram_chat_id"]) body[k] = giaTri(form, k);
      const r = await goi("/lo-trinh/kich-hoat", body);
      if (!r || !r.ok) { bao("kich-hoat", loiChu(r && r.error)); return; }
      return moTong();
    }
    if (act === "nop-bai") {
      const id = btn.getAttribute("data-id");
      const ngay = btn.getAttribute("data-ngay");
      const n = _el.querySelectorAll(".lt-cau > li").length;
      const traLoi = [];
      for (let i = 0; i < n; i++) {
        const o = _el.querySelector(`input[name="q${i}"]:checked`);
        traLoi.push(o ? Number(o.value) : null);
      }
      const r = await goi(`/lo-trinh/bai/${encodeURIComponent(id)}/${encodeURIComponent(ngay)}/nop`, { tra_loi: traLoi });
      if (!r || !r.ok) { bao("bai", loiChu(r && r.error)); return; }
      return moBai(id, ngay, r);
    }
    if (act === "luu-gate1") return luuCham(form, { gate1: { ket_qua: giaTri(form, "ket_qua"), ghi_chu: giaTri(form, "ghi_chu") } });
    if (act === "luu-khao-sat") {
      const k = { tuan: giaTri(form, "tuan") };
      for (const x of (_tong && _tong.khao_sat) || []) k[x.ma] = giaTri(form, x.ma);
      return luuCham(form, { khao_sat: k });
    }
    if (act === "luu-rubric") {
      const r = {};
      for (const x of (_tong && _tong.rubric) || []) r[x.ma] = giaTri(form, x.ma);
      return luuCham(form, { rubric: r });
    }
    if (act === "luu-must-pass") {
      const m = {};
      for (const x of (_tong && _tong.must_pass) || []) m[x.ma] = giaTri(form, x.ma);
      return luuCham(form, { must_pass: m });
    }
    if (act === "them-nghi") {
      const r = await goi(`/lo-trinh/hoc-vien/${encodeURIComponent(_xem.id)}/nghi`, { ngay: giaTri(form, "ngay") });
      if (!r || !r.ok) { bao("hoc-vien", loiChu(r && r.error)); return; }
      return moHocVien(_xem.id);
    }
    if (act === "luu-telegram" || act === "thu-telegram") {
      const thu = act === "thu-telegram";
      const r = await goi(`/lo-trinh/hoc-vien/${encodeURIComponent(_xem.id)}/telegram`,
        { telegram_chat_id: giaTri(form, "telegram_chat_id"), gui_thu: thu });
      if (!r || !r.ok) { bao("telegram", loiChu(r && r.error)); return; }
      await moHocVien(_xem.id);
      let chu = t("lt.da_luu");
      if (thu) {
        chu = !r.telegram_chat_id ? t("lt.tg.can_id")
          : r.gui_thu ? t("lt.tg.thu_ok") : t("lt.tg.thu_loi", { loi: r.loi_gui || "" });
      }
      bao("telegram", chu);
      return;
    }
    if (act === "ket-luan") {
      const r = await goi(`/lo-trinh/hoc-vien/${encodeURIComponent(_xem.id)}/ket-luan`,
        { ket_qua: giaTri(form, "ket_qua"), ly_do: giaTri(form, "ly_do") });
      if (!r || !r.ok) { bao("hoc-vien", loiChu(r && r.error)); return; }
      return moHocVien(_xem.id);
    }
  }

  async function render(el) {
    _el = el;
    el.innerHTML = `<div class="lt-trang"><p class="lt-phu">${esc(t("lt.dang_tai"))}</p></div>`;
    if (el.addEventListener && !el.__ltGan) {
      el.addEventListener("click", (e) => { xuLy(e); });
      el.__ltGan = true;
    }
    await moTong();
  }

  // _ve: các hàm vẽ thuần, để test kiểm từng màn mà không cần DOM (tests/js/test_trang_lo_trinh.js).
  window.JoyceLoTrinh = { render, _ve: { veTong, veHocVien, veBai } };
})();
