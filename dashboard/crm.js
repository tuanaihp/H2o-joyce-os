/* crm.js - trang "CRM van hanh": khach hang, co hoi, viec cham soc, de xuat ho so cho tung phong.
   Ke hoach: docs/dev/2026-10-crm-quan-tri-khach-hang.md. May chu: server/crm.py (/crm/*).

   Quyen: tai khoan nhan vien chi thay trang nay khi admin cap quyen `crm` (console.js an muc rail,
   server tra 403 neu goi tay). Co quyen roi thi chi thay khach/co hoi/viec cua PHONG minh.
   Mot khach co the thuoc NHIEU phong (nut + va - o phan Phong); co hoi, viec, giai doan thi cua
   tung phong. Joyce tu trich ho so tu hoi thoai nhung moi thay doi di qua tab "De xuat" cho nguoi
   duyet, tru khi chu bat che do tu ap.

   Phan thuan (dinhDangTien, trangThaiHan, chiaTheoGiaiDoan, ...) xuat ra cho test node.
   Ghi chu: KHONG dung ky tu em dash o bat ky dau. Chu giao dien deu qua tw() (khoa crm.*). */
(function () {
  "use strict";

  var TABS = ["contacts", "pipeline", "todos", "proposals", "segments"];
  var TRUONG_HO_SO = ["nhu_cau", "ngan_sach", "han", "phan_doi", "buoc_tiep", "tom_tat"];

  // Bảng tra khoá chữ: mỗi nhãn động đi qua một bảng với khoá ĐẦY ĐỦ, để bộ kiểm tra i18n quét
  // tĩnh thấy từng khoá (ghép chuỗi lúc chạy thì nó không thấy và khoá thiếu lọt qua).
  var K_TAB = { contacts: "crm.tab_contacts", pipeline: "crm.tab_pipeline", todos: "crm.tab_todos",
                proposals: "crm.tab_proposals", segments: "crm.tab_segments" };
  var K_MODE = { off: "crm.mode_off", duyet: "crm.mode_duyet", auto: "crm.mode_auto" };
  var K_HOSO = { nhu_cau: "crm.p_nhu_cau", ngan_sach: "crm.p_ngan_sach", han: "crm.p_han",
                 phan_doi: "crm.p_phan_doi", buoc_tiep: "crm.p_buoc_tiep", tom_tat: "crm.p_tom_tat" };
  var K_TRUONG = { name: "crm.f_name", phone: "crm.f_phone", email: "crm.f_email", company: "crm.f_company" };
  var K_SEG = { can_cham_hom_nay: "crm.seg_can_cham_hom_nay", dang_theo: "crm.seg_dang_theo",
                chua_co_co_hoi: "crm.seg_chua_co_co_hoi", than_thiet: "crm.seg_than_thiet",
                nguoi_lau_khong_cham: "crm.seg_nguoi_lau_khong_cham" };
  var K_SUKIEN = { tao: "crm.ev_create", sua: "crm.ev_edit", deal: "crm.ev_deal", viec: "crm.ev_todo", phong: "crm.ev_dept",
                   trich: "crm.ev_extract", duyet: "crm.ev_approve", wiki: "crm.ev_wiki", xoa: "crm.ev_delete",
                   khoi_phuc: "crm.ev_restore" };

  function tw(khoa, bien) {
    if (typeof window !== "undefined" && window.t) return window.t(khoa, bien);
    try {
      var s = require("./i18n/vi.json")[khoa] || khoa;
      return String(s).replace(/\{(\w+)\}/g, function (m, ten) {
        return (bien && bien[ten] != null) ? String(bien[ten]) : m;
      });
    } catch (e) { return khoa; }
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function ic(ten) {
    try { return (typeof window !== "undefined" && window.ic) ? window.ic(ten) : ""; }
    catch (e) { return ""; }
  }

  // ---------------------------------------------------------------- phan thuan
  function dinhDangTien(n) {
    var v = Math.round(Number(n) || 0);
    var s = String(Math.abs(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (v < 0 ? "-" : "") + s;
  }

  // "qua han" | "hom nay" | "sap toi" | "" cho mot viec chua xong.
  function trangThaiHan(todo) {
    if (!todo || todo.done) return "";
    if (todo.tre_han) return "late";
    if (todo.hom_nay) return "today";
    return todo.due ? "soon" : "";
  }

  // Cac cot pipeline: giu thu tu giai doan cua phong, tong tien moi cot.
  function chiaTheoGiaiDoan(stages) {
    return (stages || []).map(function (g) {
      var ds = g.deals || [];
      return { key: g.key, label: g.label, kind: g.kind, count: ds.length,
               total: ds.reduce(function (a, d) { return a + (Number(d.value) || 0); }, 0), deals: ds };
    });
  }

  function chuCaiDau(ten) {
    var t = String(ten || "").trim();
    if (!t) return "?";
    var p = t.split(/\s+/);
    return (p.length > 1 ? p[0][0] + p[p.length - 1][0] : t.slice(0, 2)).toUpperCase();
  }

  function nhanSuKien(kind) {
    return K_SUKIEN[kind] ? tw(K_SUKIEN[kind]) : kind;
  }

  // ---------------------------------------------------------------- goi may chu
  async function api(phuongThuc, url, data) {
    var opt = { method: phuongThuc, credentials: "same-origin" };
    if (data) {
      var fd = new FormData();
      Object.keys(data).forEach(function (k) { if (data[k] != null) fd.append(k, data[k]); });
      opt.body = fd;
    }
    var r = await fetch(url, opt);
    var j = null;
    try { j = await r.json(); } catch (e) { j = null; }
    if (!r.ok) {
      var loi = new Error((j && (j.detail || j.error)) || ("HTTP " + r.status));
      loi.status = r.status;
      throw loi;
    }
    return j || {};
  }

  // ---------------------------------------------------------------- giao dien
  function chenCss() {
    if (typeof document === "undefined" || document.getElementById("crmCss")) return;
    var s = document.createElement("style");
    s.id = "crmCss";
    s.textContent = [
      ".crm{display:flex;flex-direction:column;gap:12px;height:100%;min-height:0;color:var(--text)}",
      ".crm-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}",
      ".crm-sel,.crm-in,.crm-ta{box-sizing:border-box;border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--card);color:var(--text);font:inherit;font-size:14px}",
      ".crm-in,.crm-ta{width:100%;min-width:0}",
      ".crm-bar .crm-btn{flex:none}",
      ".crm-ta{resize:vertical;min-height:70px}",
      ".crm-in:focus,.crm-ta:focus,.crm-sel:focus{outline:none;border-color:var(--accent)}",
      ".crm-mode{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text2)}",
      ".crm-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}",
      ".crm-kpi{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:8px 12px}",
      ".crm-kpi small{display:block;color:var(--text3);font-size:12px}",
      ".crm-kpi b{font-size:18px}",
      ".crm-kpi.warn b{color:var(--danger-ink)}",
      ".crm-tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);overflow-x:auto}",
      ".crm-tab{border:0;background:transparent;color:var(--text2);padding:8px 12px;font:inherit;font-size:14px;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}",
      ".crm-tab.on{color:var(--text);border-bottom-color:var(--accent)}",
      ".crm-badge{display:inline-block;min-width:18px;text-align:center;margin-left:4px;padding:0 6px;border-radius:999px;background:var(--accent);color:var(--on-accent);font-size:11px}",
      ".crm-body{flex:1;min-height:0;overflow:auto}",
      ".crm-split{display:grid;grid-template-columns:minmax(240px,340px) 1fr;gap:12px;align-items:start}",
      ".crm-list{display:flex;flex-direction:column;gap:6px}",
      ".crm-row{display:flex;gap:10px;align-items:center;border:1px solid var(--line);border-radius:12px;padding:8px 10px;background:var(--card);cursor:pointer;text-align:left;font:inherit;color:inherit;width:100%}",
      ".crm-row.on,.crm-row:hover{border-color:var(--accent)}",
      ".crm-av{flex:none;width:34px;height:34px;border-radius:50%;background:var(--wash);color:var(--text2);display:grid;place-items:center;font-size:13px;font-weight:600}",
      ".crm-rt{min-width:0;flex:1}",
      ".crm-rt b,.crm-rt small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".crm-rt small{color:var(--text3);font-size:12px}",
      ".crm-card{border:1px solid var(--line);border-radius:14px;background:var(--card);padding:12px 14px;display:flex;flex-direction:column;gap:10px}",
      ".crm-card h3{margin:0;font-size:14px;color:var(--text2);font-weight:600}",
      ".crm-grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}",
      ".crm-f{display:flex;flex-direction:column;gap:3px}",
      ".crm-f label{font-size:12px;color:var(--text3)}",
      ".crm-chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}",
      ".crm-chip{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--line);background:var(--wash);border-radius:999px;padding:3px 10px;font-size:13px}",
      ".crm-chip button{border:0;background:transparent;color:var(--text3);cursor:pointer;padding:0 2px;font-size:14px;line-height:1}",
      ".crm-chip button:hover{color:var(--danger-ink)}",
      ".crm-btn{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:10px;padding:7px 12px;font:inherit;font-size:13px;cursor:pointer}",
      ".crm-btn:hover{border-color:var(--accent)}",
      ".crm-btn.pri{background:var(--accent);color:var(--on-accent);border-color:var(--accent);font-weight:700}",
      ".crm-btn.dng{color:var(--danger-ink)}",
      ".crm-btn:disabled{opacity:.6;cursor:default}",
      ".crm-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}",
      ".crm-err{color:var(--danger-ink);font-size:13px}",
      ".crm-ok{color:var(--text2);font-size:13px}",
      ".crm-muted{color:var(--text3);font-size:13px}",
      ".crm-pipe{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(220px,1fr);gap:10px;overflow-x:auto;padding-bottom:6px}",
      ".crm-col{border:1px solid var(--line);border-radius:14px;background:var(--wash);padding:8px;display:flex;flex-direction:column;gap:8px;min-height:120px}",
      ".crm-col h4{margin:0;font-size:13px;display:flex;align-items:center;gap:6px}",
      ".crm-col h4 span{margin-left:auto;color:var(--text3);font-weight:400}",
      ".crm-col.won h4{color:var(--accent)}",
      ".crm-col.lost h4{color:var(--text3)}",
      ".crm-deal{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:8px 10px;display:flex;flex-direction:column;gap:4px;font-size:13px}",
      ".crm-deal b{font-size:14px}",
      ".crm-todo{display:flex;gap:10px;align-items:center;border:1px solid var(--line);border-radius:12px;padding:8px 12px;background:var(--card)}",
      ".crm-todo.done .crm-tt{text-decoration:line-through;color:var(--text3)}",
      ".crm-tt{flex:1;min-width:0}",
      ".crm-han{font-size:12px;border-radius:999px;padding:1px 8px;background:var(--wash);color:var(--text2)}",
      ".crm-han.late{background:var(--danger-wash,var(--wash));color:var(--danger-ink)}",
      ".crm-han.today{color:var(--accent)}",
      ".crm-ev{display:flex;gap:8px;font-size:13px;color:var(--text2);padding:2px 0}",
      ".crm-ev time{flex:none;color:var(--text3);font-size:12px;min-width:74px}",
      ".crm-back{display:none}",
      ".crm-seg{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}",
      ".crm-prop label{display:flex;gap:8px;align-items:flex-start;font-size:13px}",
      "@media (max-width:820px){.crm-split{grid-template-columns:1fr}.crm.det .crm-lst{display:none}.crm:not(.det) .crm-det{display:none}.crm-back{display:inline-block}.crm-grid2{grid-template-columns:1fr}}"
    ].join("\n");
    document.head.appendChild(s);
  }

  function taoTrang(host) {
    chenCss();
    // Gốc riêng cho trang: lắng nghe sự kiện trên gốc này (không phải trên khung dùng chung của
    // console) để đổi trang là bộ lắng nghe đi theo gốc cũ, không dồn lại.
    host.innerHTML = "";
    var el = document.createElement("div");
    el.style.height = "100%";
    host.appendChild(el);
    var S = { me: null, brain: "", tab: "contacts", q: "", ds: [], sel: 0, chiTiet: null, pipe: null,
              viec: [], dexuat: [], seg: [], tq: null, loi: "", info: "", tamLoi: false,
              hienThem: false, daXoa: false, hienNhanh: false, nhanh: null, hopThu: null, hienDeal: false, hienViec: false };

    async function nap(chi) {
      try {
        if (!S.me) {
          S.me = await api("GET", "/crm/me");
          S.brain = S.me.admin ? "" : (S.me.mac_dinh || (S.me.phong[0] && S.me.phong[0].brain) || "");
        }
        var b = encodeURIComponent(S.brain);
        var tac = [api("GET", "/crm/tong-quan?brain=" + b).then(function (r) { S.tq = r; })];
        if (S.tab === "contacts") tac.push(api("GET", "/crm/lien-he?brain=" + b + "&q=" + encodeURIComponent(S.q) + (S.daXoa ? "&da_xoa=1" : "")).then(function (r) { S.ds = r.items; }));
        if (S.tab === "pipeline" && S.brain) tac.push(api("GET", "/crm/pipeline?brain=" + b).then(function (r) { S.pipe = r; }));
        if (S.tab === "todos") tac.push(api("GET", "/crm/viec?brain=" + b).then(function (r) { S.viec = r.items; }));
        if (S.tab === "proposals") tac.push(api("GET", "/crm/de-xuat?brain=" + b).then(function (r) { S.dexuat = r.items; }));
        if (S.tab === "segments" && S.brain) tac.push(api("GET", "/crm/phan-khuc?brain=" + b).then(function (r) { S.seg = r.items; }));
        if (S.tab === "contacts" && S.sel) tac.push(moChiTiet(S.sel, true));
        if (S.tab === "pipeline" || S.tab === "todos") tac.push(api("GET", "/crm/lien-he?brain=" + b + "&limit=500").then(function (r) { S.ds = r.items; }));
        await Promise.all(tac);
        S.loi = "";
      } catch (e) {
        S.loi = e.status === 403 ? tw("crm.no_access") : (e.message || tw("crm.err_load"));
      }
      if (!chi) ve();
    }

    async function moChiTiet(id, imLang) {
      S.sel = id;
      try { S.chiTiet = await api("GET", "/crm/lien-he/" + id); }
      catch (e) { S.chiTiet = null; S.sel = 0; if (!imLang) S.loi = e.message; }
      if (!imLang) ve();
    }

    async function lam(url, data, thanhCong, phuongThuc) {
      S.loi = ""; S.info = "";
      try {
        var r = await api(phuongThuc || "POST", url, data);
        if (thanhCong) S.info = thanhCong;
        await nap(true);
        return r;
      } catch (e) { S.loi = e.message; }
      finally { ve(); }
      return null;
    }

    // ---- cac khoi giao dien
    function khungTren() {
      var phong = S.me.phong || [];
      var banPhong = (!S.me.admin || !S.brain) ? null : phong.filter(function (p) { return p.brain === S.brain; })[0];
      var chon = phong.length > 1 || S.me.admin
        ? '<select class="crm-sel" data-a="brain">' + (S.me.admin ? '<option value="">' + esc(tw("crm.all_depts")) + "</option>" : "") + phong.map(function (p) {
            return '<option value="' + esc(p.brain) + '"' + (p.brain === S.brain ? " selected" : "") + ">" + esc(p.ten || p.brain) + "</option>";
          }).join("") + "</select>"
        : '<span class="crm-muted">' + esc((phong[0] && (phong[0].ten || phong[0].brain)) || "") + "</span>";
      var coQuyen = S.me.admin || S.me.quan_ly;
      var che = '<div class="crm-mode" title="' + esc(tw("crm.mode_tip")) + '">' + ic("sparkles") + "<span>" + esc(tw("crm.mode_lbl")) + "</span>"
        + (coQuyen
          ? '<select class="crm-sel" data-a="mode">' + ["off", "duyet", "auto"].map(function (m) {
              return '<option value="' + m + '"' + (S.me.che_do === m ? " selected" : "") + ">" + esc(tw(K_MODE[m])) + "</option>";
            }).join("") + "</select>"
          : "<b>" + esc(tw(K_MODE[S.me.che_do] || K_MODE.duyet)) + "</b>")
        + (coQuyen && S.me.che_do !== "off" ? "<span>" + esc(tw("crm.thr_pre")) + '</span><input class="crm-sel" type="number" min="2" max="100" style="width:64px" data-a="nguong" value="' + esc(S.me.nguong) + '"><span>' + esc(tw("crm.thr_post")) + "</span>" : "")
        + "</div>";
      var q = S.tq || {};
      var kp = [
        [tw("crm.kpi_contacts"), q.lien_he || 0, ""],
        [tw("crm.kpi_open"), dinhDangTien(q.dang_theo), ""],
        [tw("crm.kpi_won"), dinhDangTien(q.da_chot), ""],
        [tw("crm.kpi_todo"), q.viec_mo || 0, q.viec_tre ? "warn" : ""],
        [tw("crm.kpi_late"), q.viec_tre || 0, q.viec_tre ? "warn" : ""]
      ];
      var tabs = TABS.map(function (t) {
        var n = t === "proposals" ? (q.de_xuat || 0) : (t === "todos" ? (q.viec_mo || 0) : 0);
        return '<button class="crm-tab' + (S.tab === t ? " on" : "") + '" data-a="tab" data-v="' + t + '">' + esc(tw(K_TAB[t]))
          + (n ? '<span class="crm-badge">' + n + "</span>" : "") + "</button>";
      }).join("");
      var bat = banPhong ? '<label class="crm-muted"><input type="checkbox" data-a="phong-bat"' + (banPhong.bat ? " checked" : "") + "> " + esc(tw("crm.dept_on")) + "</label>" : "";
      var ro = S.me.chi_xem ? '<span class="crm-chip">' + esc(tw("crm.read_only")) + "</span>" : "";
      return '<div class="crm-top">' + chon + bat + ro + che + "</div>"
        + '<div class="crm-kpis">' + kp.map(function (k) {
          return '<div class="crm-kpi ' + k[2] + '"><small>' + esc(k[0]) + "</small><b>" + esc(k[1]) + "</b></div>";
        }).join("") + "</div>"
        + '<div class="crm-tabs">' + tabs + "</div>"
        + (S.loi ? '<div class="crm-err">' + esc(S.loi) + "</div>" : "")
        + (S.info ? '<div class="crm-ok">' + esc(S.info) + "</div>" : "");
    }

    function formKhach(c) {
      c = c || {};
      return '<form class="crm-card" data-form="contact" data-id="' + (c.id || "") + '">'
        + '<div class="crm-grid2">'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_name")) + '</label><input class="crm-in" name="name" value="' + esc(c.name) + '"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_phone")) + '</label><input class="crm-in" name="phone" value="' + esc(c.phone) + '" inputmode="tel"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_email")) + '</label><input class="crm-in" name="email" value="' + esc(c.email) + '"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_company")) + '</label><input class="crm-in" name="company" value="' + esc(c.company) + '"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_source")) + '</label><input class="crm-in" name="source" value="' + esc(c.source) + '"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_tags")) + '</label><input class="crm-in" name="tags" value="' + esc((c.tags || []).join(", ")) + '"></div>'
        + "</div>"
        + '<div class="crm-f"><label>' + esc(tw("crm.f_note")) + '</label><textarea class="crm-ta" name="note">' + esc(c.note) + "</textarea></div>"
        + '<div class="crm-bar"><button class="crm-btn pri" type="submit">' + esc(tw("crm.save")) + "</button>"
        + (c.id ? "" : '<button class="crm-btn" type="button" data-a="cancel-add">' + esc(tw("crm.cancel")) + "</button>") + "</div></form>";
    }

    function khungNhanh() {
      var n = S.nhanh;
      return '<div class="crm-card"><h3>' + esc(tw("crm.quick_title")) + "</h3>"
        + '<textarea class="crm-ta" data-r="quick" placeholder="' + esc(tw("crm.quick_ph")) + '"></textarea>'
        + '<div class="crm-bar"><button class="crm-btn pri" data-a="quick">' + esc(tw("crm.quick_go")) + "</button>"
        + '<span class="crm-muted">' + esc(tw("crm.quick_hint")) + "</span></div>"
        + (n ? (Object.keys(n).length
          ? '<div class="crm-ok">' + esc(tw("crm.quick_found")) + "</div>" + formKhach({ name: n.name, phone: n.phone, email: n.email, company: n.company,
              note: TRUONG_HO_SO.filter(function (k) { return n[k]; }).map(function (k) { return tw(K_HOSO[k]) + ": " + n[k]; }).join("\n") })
          : '<div class="crm-muted">' + esc(tw("crm.quick_none")) + "</div>") : "") + "</div>";
    }

    function trangDanhBa() {
      var dsHtml = S.daXoa ? (S.ds.length ? S.ds.map(function (c) {
        return '<div class="crm-bar"><span style="flex:1;min-width:0">' + esc(c.name || c.phone || ("#" + c.id)) + "</span>"
          + '<button class="crm-btn" data-a="restore" data-id="' + c.id + '">' + esc(tw("crm.restore")) + "</button></div>";
      }).join("") : '<div class="crm-muted">' + esc(tw("crm.trash_empty")) + "</div>") : S.ds.length ? S.ds.map(function (c) {
        return '<button class="crm-row' + (c.id === S.sel ? " on" : "") + '" data-a="open" data-id="' + c.id + '"><span class="crm-av">' + esc(chuCaiDau(c.name || c.phone))
          + '</span><span class="crm-rt"><b>' + esc(c.name || c.phone || ("#" + c.id)) + "</b><small>" + esc([c.company, c.phone].filter(Boolean).join(" | ")) + "</small></span></button>";
      }).join("") : '<div class="crm-muted">' + esc(tw("crm.empty_contacts")) + "</div>";
      var trai = '<div class="crm-lst"><div class="crm-list">'
        + '<div class="crm-bar"><input class="crm-in" data-r="search" placeholder="' + esc(tw("crm.search_ph")) + '" value="' + esc(S.q) + '" style="flex:1">'
        + '<button class="crm-btn pri" data-a="add" title="' + esc(tw("crm.add_contact")) + '">+</button></div>'
        + '<div class="crm-bar"><button class="crm-btn" data-a="quick-toggle">' + esc(tw("crm.quick_title")) + "</button>"
        + ((S.me.admin || S.me.quan_ly) ? '<button class="crm-btn" data-a="inbox">' + esc(tw("crm.from_inbox")) + "</button>" : "")
        + ((S.me.admin || S.me.quan_ly) ? '<button class="crm-btn" data-a="trash">' + esc(S.daXoa ? tw("crm.trash_back") : tw("crm.trash")) + "</button>" : "") + "</div>"
        + (S.hienNhanh ? khungNhanh() : "") + (S.hopThu ? khungHopThu() : "") + (S.hienThem ? formKhach() : "") + dsHtml + "</div></div>";
      return '<div class="crm-split">' + trai + '<div class="crm-det">' + (S.chiTiet ? chiTiet(S.chiTiet) : '<div class="crm-muted">' + esc(tw("crm.pick_contact")) + "</div>") + "</div></div>";
    }

    function khungHopThu() {
      var ds = S.hopThu || [];
      return '<div class="crm-card"><h3>' + esc(tw("crm.from_inbox")) + "</h3>"
        + (ds.length ? ds.slice(0, 30).map(function (k) {
          return '<div class="crm-bar"><span style="flex:1;min-width:0">' + esc(k.name || ("#" + k.id)) + ' <span class="crm-muted">' + esc(k.channel || "") + "</span></span>"
            + '<button class="crm-btn" data-a="import" data-id="' + k.id + '">' + esc(tw("crm.import")) + "</button></div>";
        }).join("") : '<div class="crm-muted">' + esc(tw("crm.inbox_none")) + "</div>") + "</div>";
    }

    function chiTiet(d) {
      var c = d.contact;
      var phongCon = (S.me.phong || []).filter(function (p) { return c.depts.indexOf(p.brain) < 0; });
      var tenPhong = function (b) { var p = (S.me.phong || []).filter(function (x) { return x.brain === b; })[0]; return (p && (p.ten || p.brain)) || b; };
      var phongHtml = '<div class="crm-card"><h3>' + esc(tw("crm.depts")) + '</h3><div class="crm-chips">'
        + c.depts.map(function (b) {
          return '<span class="crm-chip">' + esc(tenPhong(b)) + '<button data-a="dept-off" data-b="' + esc(b) + '" title="' + esc(tw("crm.dept_off")) + '">-</button></span>';
        }).join("")
        + (phongCon.length ? '<select class="crm-sel" data-a="dept-add"><option value="">+ ' + esc(tw("crm.dept_add")) + "</option>" + phongCon.map(function (p) {
          return '<option value="' + esc(p.brain) + '">' + esc(p.ten || p.brain) + "</option>";
        }).join("") + "</select>" : "") + "</div></div>";
      var pf = c.profile || {};
      var hs = TRUONG_HO_SO.filter(function (k) { return pf[k]; });
      var hsHtml = hs.length ? '<div class="crm-card"><h3>' + esc(tw("crm.profile")) + "</h3>" + hs.map(function (k) {
        return '<div class="crm-ev"><time>' + esc(tw(K_HOSO[k])) + "</time><span>" + esc(pf[k]) + "</span></div>";
      }).join("") + "</div>" : "";
      var dx = (d.proposals || []).map(function (p) { return khoiDeXuat(p); }).join("");
      var gd = d.stage_labels || {};
      var deals = '<div class="crm-card"><h3>' + esc(tw("crm.deals")) + '</h3>'
        + (d.deals.length ? d.deals.map(function (x) {
          var lb = (gd[x.brain] || {})[x.stage] || x.stage;
          return '<div class="crm-ev"><span style="flex:1"><b>' + esc(x.title) + "</b> <span class=\"crm-muted\">" + esc(tenPhong(x.brain)) + " | " + esc(lb)
            + (x.value ? " | " + esc(dinhDangTien(x.value)) : "") + "</span></span></div>";
        }).join("") : '<div class="crm-muted">' + esc(tw("crm.no_deals")) + "</div>")
        + '<div class="crm-bar"><button class="crm-btn" data-a="deal-form">+ ' + esc(tw("crm.add_deal")) + "</button>"
        + '<button class="crm-btn" data-a="todo-form">+ ' + esc(tw("crm.add_todo")) + "</button></div>"
        + (S.hienDeal ? formDeal(c) : "") + (S.hienViec ? formViec(c) : "") + "</div>";
      var todos = (d.todos || []).length ? '<div class="crm-card"><h3>' + esc(tw("crm.todos")) + "</h3>" + d.todos.map(dongViec).join("") + "</div>" : "";
      var ev = '<div class="crm-card"><h3>' + esc(tw("crm.timeline")) + "</h3>" + (d.events.length ? d.events.slice(0, 25).map(function (e) {
        return '<div class="crm-ev"><time>' + esc(new Date(e.created_at * 1000).toLocaleDateString()) + "</time><span><b>" + esc(nhanSuKien(e.kind)) + ":</b> " + esc(e.text) + "</span></div>";
      }).join("") : '<div class="crm-muted">' + esc(tw("crm.no_events")) + "</div>") + "</div>";
      var conv = (d.conversations || []).length ? '<div class="crm-card"><h3>' + esc(tw("crm.convs")) + "</h3>" + d.conversations.map(function (x) {
        return '<div class="crm-ev"><span style="flex:1">' + esc(x.last_message || x.title || "") + "</span></div>";
      }).join("") + "</div>" : "";
      var hanhDong = '<div class="crm-bar">'
        + '<button class="crm-btn crm-back" data-a="back">&larr; ' + esc(tw("crm.back")) + "</button>"
        + (c.customer_id ? '<button class="crm-btn" data-a="extract">' + ic("sparkles") + " " + esc(tw("crm.extract")) + "</button>" : "")
        + '<button class="crm-btn" data-a="remember">' + esc(tw("crm.remember")) + "</button>"
        + ((S.me.admin || S.me.quan_ly) ? '<button class="crm-btn dng" data-a="delete">- ' + esc(tw("crm.delete")) + "</button>" : "") + "</div>";
      return hanhDong + dx + formKhach(c) + phongHtml + hsHtml + deals + todos + conv + ev;
    }

    function khoiDeXuat(p) {
      var f = p.fields || {};
      var nhan = function (k) { return K_HOSO[k] ? tw(K_HOSO[k]) : tw(K_TRUONG[k] || K_TRUONG.name); };
      return '<div class="crm-card crm-prop" data-pid="' + p.id + '"><h3>' + esc(tw("crm.proposal_title")) + "</h3>"
        + Object.keys(f).map(function (k) {
          return '<label><input type="checkbox" data-k="' + esc(k) + '" checked><span><b>' + esc(nhan(k)) + ":</b> " + esc(f[k]) + "</span></label>";
        }).join("")
        + '<div class="crm-bar"><button class="crm-btn pri" data-a="approve" data-id="' + p.id + '">' + esc(tw("crm.approve")) + "</button>"
        + '<button class="crm-btn" data-a="reject" data-id="' + p.id + '">' + esc(tw("crm.reject")) + "</button></div></div>";
    }

    function tenPhongCua(b) {
      var p = (S.me.phong || []).filter(function (x) { return x.brain === b; })[0];
      return (p && (p.ten || p.brain)) || b;
    }

    function formDeal(c) {
      return '<form class="crm-card" data-form="deal" data-cid="' + c.id + '"><div class="crm-grid2">'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_deal_title")) + '</label><input class="crm-in" name="title"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_value")) + '</label><input class="crm-in" name="value" inputmode="numeric"></div></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_dept")) + '</label><select class="crm-sel" name="brain">' + (S.me.phong || []).filter(function (p) { return c.depts.indexOf(p.brain) >= 0; }).map(function (p) {
          return '<option value="' + esc(p.brain) + '"' + (p.brain === S.brain ? " selected" : "") + ">" + esc(p.ten || p.brain) + "</option>";
        }).join("") + "</select></div>"
        + '<div class="crm-bar"><button class="crm-btn pri" type="submit">' + esc(tw("crm.save")) + "</button></div></form>";
    }

    function formViec(c) {
      return '<form class="crm-card" data-form="todo" data-cid="' + c.id + '"><div class="crm-grid2">'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_todo_title")) + '</label><input class="crm-in" name="title"></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_due")) + '</label><input class="crm-in" type="date" name="due"></div></div>'
        + '<div class="crm-f"><label>' + esc(tw("crm.f_dept")) + '</label><select class="crm-sel" name="brain">' + (c.depts || []).map(function (b) {
          return '<option value="' + esc(b) + '"' + (b === S.brain ? " selected" : "") + ">" + esc(tenPhongCua(b)) + "</option>";
        }).join("") + "</select></div>"
        + '<div class="crm-bar"><button class="crm-btn pri" type="submit">' + esc(tw("crm.save")) + "</button></div></form>";
    }

    function dongViec(t) {
      var tt = trangThaiHan(t);
      return '<div class="crm-todo' + (t.done ? " done" : "") + '"><input type="checkbox" data-a="todo-done" data-id="' + t.id + '"' + (t.done ? " checked" : "") + ">"
        + '<span class="crm-tt">' + esc(t.title) + (t.contact_name ? ' <span class="crm-muted">| ' + esc(t.contact_name) + "</span>" : "") + "</span>"
        + (t.due ? '<span class="crm-han ' + tt + '">' + esc(t.due) + "</span>" : "")
        + '<button class="crm-btn" data-a="todo-del" data-id="' + t.id + '" title="' + esc(tw("crm.delete")) + '">-</button></div>';
    }

    function trangPipeline() {
      if (!S.brain) return '<div class="crm-muted">' + esc(tw("crm.pick_dept")) + "</div>";
      if (!S.pipe) return '<div class="crm-muted">' + esc(tw("crm.loading")) + "</div>";
      var cot = chiaTheoGiaiDoan(S.pipe.stages);
      var tl = S.pipe.ti_le_thang == null ? "-" : Math.round(S.pipe.ti_le_thang * 100) + "%";
      return '<div class="crm-bar"><span class="crm-muted">' + esc(tw("crm.win_rate")) + ": <b>" + esc(tl) + "</b></span>"
        + '<button class="crm-btn" data-a="stage-add">+ ' + esc(tw("crm.stage_add")) + "</button>"
        + '<button class="crm-btn" data-a="deal-new">+ ' + esc(tw("crm.add_deal")) + "</button></div>"
        + (S.hienDeal ? '<form class="crm-card" data-form="deal-new"><div class="crm-grid2">'
          + '<div class="crm-f"><label>' + esc(tw("crm.f_contact")) + '</label><select class="crm-sel" name="contact_id">' + S.ds.map(function (c) {
            return '<option value="' + c.id + '">' + esc(c.name || c.phone || ("#" + c.id)) + "</option>";
          }).join("") + "</select></div>"
          + '<div class="crm-f"><label>' + esc(tw("crm.f_deal_title")) + '</label><input class="crm-in" name="title"></div>'
          + '<div class="crm-f"><label>' + esc(tw("crm.f_value")) + '</label><input class="crm-in" name="value" inputmode="numeric"></div></div>'
          + '<div class="crm-bar"><button class="crm-btn pri" type="submit">' + esc(tw("crm.save")) + "</button></div></form>" : "")
        + '<div class="crm-pipe">' + cot.map(function (g) {
          return '<div class="crm-col ' + g.kind + '"><h4>' + esc(g.label)
            + (g.kind === "open" ? ' <button class="crm-btn" style="padding:0 8px" data-a="stage-del" data-k="' + esc(g.key) + '" title="' + esc(tw("crm.stage_del")) + '">-</button>' : "")
            + "<span>" + g.count + (g.total ? " | " + esc(dinhDangTien(g.total)) : "") + "</span></h4>"
            + g.deals.map(function (d) {
              return '<div class="crm-deal"><b>' + esc(d.title) + "</b><span class=\"crm-muted\">" + esc(d.contact_name || "") + (d.value ? " | " + esc(dinhDangTien(d.value)) : "") + "</span>"
                + '<select class="crm-sel" data-a="deal-move" data-id="' + d.id + '">' + cot.map(function (x) {
                  return '<option value="' + esc(x.key) + '"' + (x.key === d.stage ? " selected" : "") + ">" + esc(x.label) + "</option>";
                }).join("") + "</select>"
                + '<div class="crm-bar"><button class="crm-btn" data-a="open-contact" data-id="' + d.contact_id + '">' + esc(tw("crm.open")) + "</button>"
                + '<button class="crm-btn dng" data-a="deal-del" data-id="' + d.id + '">-</button></div></div>';
            }).join("") + "</div>";
        }).join("") + "</div>";
    }

    function trangViec() {
      return '<div class="crm-bar"><button class="crm-btn" data-a="todo-new">+ ' + esc(tw("crm.add_todo")) + "</button></div>"
        + (S.hienViec ? '<form class="crm-card" data-form="todo-new"><div class="crm-grid2">'
          + '<div class="crm-f"><label>' + esc(tw("crm.f_contact")) + '</label><select class="crm-sel" name="contact_id">' + S.ds.map(function (c) {
            return '<option value="' + c.id + '">' + esc(c.name || c.phone || ("#" + c.id)) + "</option>";
          }).join("") + "</select></div>"
          + '<div class="crm-f"><label>' + esc(tw("crm.f_todo_title")) + '</label><input class="crm-in" name="title"></div>'
          + '<div class="crm-f"><label>' + esc(tw("crm.f_due")) + '</label><input class="crm-in" type="date" name="due"></div>'
          + '<div class="crm-f"><label>' + esc(tw("crm.f_dept")) + '</label><select class="crm-sel" name="brain">' + (S.me.phong || []).map(function (p) {
            return '<option value="' + esc(p.brain) + '"' + (p.brain === S.brain ? " selected" : "") + ">" + esc(p.ten || p.brain) + "</option>";
          }).join("") + "</select></div></div>"
          + '<div class="crm-bar"><button class="crm-btn pri" type="submit">' + esc(tw("crm.save")) + "</button></div></form>" : "")
        + '<div class="crm-list">' + (S.viec.length ? S.viec.map(dongViec).join("") : '<div class="crm-muted">' + esc(tw("crm.empty_todos")) + "</div>") + "</div>";
    }

    function trangDeXuat() {
      return '<div class="crm-muted">' + esc(tw("crm.proposals_hint")) + "</div>"
        + (S.dexuat.length ? S.dexuat.map(function (p) {
          return '<div class="crm-bar" style="margin-top:8px"><b>' + esc(p.contact_name) + "</b></div>" + khoiDeXuat(p);
        }).join("") : '<div class="crm-muted" style="margin-top:8px">' + esc(tw("crm.empty_proposals")) + "</div>");
    }

    function trangPhanKhuc() {
      if (!S.brain) return '<div class="crm-muted">' + esc(tw("crm.pick_dept")) + "</div>";
      return '<div class="crm-seg">' + S.seg.map(function (g) {
        return '<div class="crm-card"><h3>' + esc(tw(K_SEG[g.key] || K_SEG.dang_theo)) + " (" + g.count + ")</h3>"
          + (g.contacts.length ? '<div class="crm-chips">' + g.contacts.slice(0, 20).map(function (c) {
            return '<button class="crm-chip" data-a="open-contact" data-id="' + c.id + '">' + esc(c.name) + "</button>";
          }).join("") + "</div>" : '<div class="crm-muted">-</div>') + "</div>";
      }).join("") + "</div>";
    }

    function ve() {
      if (!S.me) { el.innerHTML = '<div class="crm"><div class="crm-muted">' + esc(S.loi || tw("crm.loading")) + "</div></div>"; return; }
      if (!S.me.admin && !(S.me.phong || []).length) { el.innerHTML = '<div class="crm"><div class="crm-muted">' + esc(tw("crm.no_dept")) + "</div></div>"; return; }
      var body = { contacts: trangDanhBa, pipeline: trangPipeline, todos: trangViec, proposals: trangDeXuat, segments: trangPhanKhuc }[S.tab]();
      var giu = el.querySelector('[data-r="search"]');
      var dangGo = giu && document.activeElement === giu;
      el.innerHTML = '<div class="crm' + (S.sel && S.tab === "contacts" ? " det" : "") + '">' + khungTren() + '<div class="crm-body">' + body + "</div></div>";
      if (S.me.chi_xem) khoaGhi();
      if (dangGo) { var m = el.querySelector('[data-r="search"]'); if (m) { m.focus(); m.setSelectionRange(m.value.length, m.value.length); } }
    }

    // Chế độ chỉ xem: gỡ mọi nút và form ghi (máy chủ vẫn chặn 403, đây chỉ để khỏi bày nút vô ích).
    function khoaGhi() {
      var ghi = ["add", "quick-toggle", "inbox", "trash", "restore", "delete", "dept-off", "dept-add", "deal-form", "todo-form",
                 "deal-new", "todo-new", "deal-del", "todo-del", "todo-done", "stage-add", "stage-del", "deal-move", "extract",
                 "remember", "approve", "reject", "mode", "nguong", "phong-bat", "import", "cancel-add"];
      ghi.forEach(function (a) {
        [].slice.call(el.querySelectorAll('[data-a="' + a + '"]')).forEach(function (n) {
          if (n.tagName === "INPUT" || n.tagName === "SELECT") n.disabled = true; else n.style.display = "none";
        });
      });
      [].slice.call(el.querySelectorAll("form[data-form]")).forEach(function (f) { f.style.display = "none"; });
    }

    // ---- su kien
    function layForm(f) {
      var o = {}; new FormData(f).forEach(function (v, k) { o[k] = v; }); return o;
    }

    el.addEventListener("submit", async function (ev) {
      var f = ev.target.closest("form[data-form]");
      if (!f) return;
      ev.preventDefault();
      var kieu = f.getAttribute("data-form"), d = layForm(f);
      if (kieu === "contact") {
        var id = f.getAttribute("data-id");
        d.id = id || 0;
        if (!id) d.depts = S.brain;
        else d.depts = (S.chiTiet && S.chiTiet.contact.depts || []).join(",");
        var r = await lam("/crm/lien-he", d, tw("crm.saved"));
        if (r && r.contact) { S.hienThem = false; S.hienNhanh = false; S.nhanh = null; await moChiTiet(r.contact.id); }
      } else if (kieu === "deal") {
        d.contact_id = f.getAttribute("data-cid"); S.hienDeal = false;
        await lam("/crm/deal", d, tw("crm.saved")); await moChiTiet(S.sel);
      } else if (kieu === "deal-new") {
        d.brain = S.brain; S.hienDeal = false;
        await lam("/crm/deal", d, tw("crm.saved"));
      } else if (kieu === "todo") {
        d.contact_id = f.getAttribute("data-cid"); S.hienViec = false;
        await lam("/crm/viec", d, tw("crm.saved")); await moChiTiet(S.sel);
      } else if (kieu === "todo-new") {
        d.brain = d.brain || S.brain; S.hienViec = false;
        await lam("/crm/viec", d, tw("crm.saved"));
      }
    });

    el.addEventListener("input", function (ev) {
      var t = ev.target;
      if (t.getAttribute && t.getAttribute("data-r") === "search") {
        S.q = t.value;
        clearTimeout(S.timer);
        S.timer = setTimeout(function () { nap(); }, 300);
      }
    });

    el.addEventListener("change", async function (ev) {
      var t = ev.target, a = t.getAttribute && t.getAttribute("data-a");
      if (!a) return;
      if (a === "brain") { S.brain = t.value; S.sel = 0; S.chiTiet = null; S.pipe = null; await nap(); }
      else if (a === "mode") {
        var r = await lam("/crm/cau-hinh/trich", { che_do: t.value }, tw("crm.mode_saved"));
        if (r) S.me.che_do = r.che_do;
        ve();
      }
      else if (a === "phong-bat") {
        await lam("/crm/cau-hinh/phong", { brain: S.brain, bat: t.checked ? 1 : 0 }, tw("crm.dept_on_saved"));
        S.me = null; await nap();
      }
      else if (a === "nguong") {
        var r4 = await lam("/crm/cau-hinh/trich", { nguong: t.value }, tw("crm.mode_saved"));
        if (r4) S.me.nguong = r4.nguong;
        ve();
      }
      else if (a === "dept-add" && t.value) { await lam("/crm/lien-he/phong", { id: S.sel, brain: t.value, bat: 1 }); await moChiTiet(S.sel); }
      else if (a === "deal-move") { await lam("/crm/deal/buoc", { id: t.getAttribute("data-id"), stage: t.value }); }
      else if (a === "todo-done") { await lam("/crm/viec/xong", { id: t.getAttribute("data-id"), xong: t.checked ? 1 : 0 }); if (S.tab === "contacts") await moChiTiet(S.sel); }
    });

    el.addEventListener("click", async function (ev) {
      var b = ev.target.closest("[data-a]");
      if (!b || b.tagName === "SELECT" || b.type === "checkbox") return;
      var a = b.getAttribute("data-a"), id = b.getAttribute("data-id");
      if (a === "tab") { S.tab = b.getAttribute("data-v"); S.hienDeal = false; S.hienViec = false; await nap(); }
      else if (a === "open") { await moChiTiet(Number(id)); }
      else if (a === "open-contact") { S.tab = "contacts"; await nap(true); await moChiTiet(Number(id)); }
      else if (a === "back") { S.sel = 0; S.chiTiet = null; ve(); }
      else if (a === "add") { S.hienThem = !S.hienThem; ve(); }
      else if (a === "cancel-add") { S.hienThem = false; ve(); }
      else if (a === "quick-toggle") { S.hienNhanh = !S.hienNhanh; S.nhanh = null; ve(); }
      else if (a === "quick") {
        var ta = el.querySelector('[data-r="quick"]'), txt = ta ? ta.value : "";
        if (!txt.trim()) return;
        b.disabled = true;
        try { S.nhanh = (await api("POST", "/crm/nhap-nhanh", { text: txt })).fields; S.loi = ""; }
        catch (e) { S.loi = e.message; }
        ve();
      }
      else if (a === "inbox") {
        if (S.hopThu) { S.hopThu = null; ve(); return; }
        try { S.hopThu = (await api("GET", "/crm/hop-thu")).items; } catch (e) { S.loi = e.message; }
        ve();
      }
      else if (a === "import") {
        var r = await lam("/crm/hop-thu/nhap", { customer_id: id, brain: S.brain }, tw("crm.imported"));
        if (r && r.contact) { S.hopThu = null; await moChiTiet(r.contact.id); }
      }
      else if (a === "trash") { S.daXoa = !S.daXoa; S.sel = 0; S.chiTiet = null; await nap(); }
      else if (a === "restore") { await lam("/crm/lien-he/xoa", { id: id, khoi_phuc: 1 }, tw("crm.restored")); }
      else if (a === "dept-off") { await lam("/crm/lien-he/phong", { id: S.sel, brain: b.getAttribute("data-b"), bat: 0 }); await moChiTiet(S.sel); }
      else if (a === "delete") {
        if (typeof confirm === "function" && !confirm(tw("crm.confirm_delete"))) return;
        await lam("/crm/lien-he/xoa", { id: S.sel }, tw("crm.deleted")); S.sel = 0; S.chiTiet = null; ve();
      }
      else if (a === "extract") {
        b.disabled = true;
        var r2 = await lam("/crm/trich", { id: S.sel }, null);
        S.info = r2 ? (r2.co_gi_moi ? tw("crm.extract_new") : tw("crm.extract_none")) : "";
        await moChiTiet(S.sel);
      }
      else if (a === "remember") { var r3 = await lam("/crm/ghi-nho", { id: S.sel, brain: S.brain }, null); if (r3) { S.info = tw("crm.remembered", { path: r3.path }); ve(); } }
      else if (a === "deal-form") { S.hienDeal = !S.hienDeal; S.hienViec = false; ve(); }
      else if (a === "todo-form") { S.hienViec = !S.hienViec; S.hienDeal = false; ve(); }
      else if (a === "deal-new") { S.hienDeal = !S.hienDeal; ve(); }
      else if (a === "todo-new") { S.hienViec = !S.hienViec; ve(); }
      else if (a === "deal-del") { if (!confirm(tw("crm.confirm_delete_deal"))) return; await lam("/crm/deal/xoa", { id: id }); }
      else if (a === "todo-del") { await lam("/crm/viec/xoa", { id: id }); if (S.tab === "contacts") await moChiTiet(S.sel); }
      else if (a === "stage-add") {
        var ten = typeof prompt === "function" ? prompt(tw("crm.stage_prompt")) : "";
        if (ten && ten.trim()) await lam("/crm/giai-doan", { brain: S.brain, label: ten.trim() });
      }
      else if (a === "stage-del") {
        if (!confirm(tw("crm.confirm_stage_del"))) return;
        await lam("/crm/giai-doan/xoa", { brain: S.brain, key: b.getAttribute("data-k") });
      }
      else if (a === "approve" || a === "reject") {
        var khung = b.closest("[data-pid]");
        var chon = [].slice.call(khung.querySelectorAll("input[data-k]:checked")).map(function (x) { return x.getAttribute("data-k"); });
        if (a === "approve") await lam("/crm/de-xuat/duyet", { id: id, chon: chon.join(",") }, tw("crm.approved"));
        else await lam("/crm/de-xuat/bo", { id: id }, tw("crm.rejected"));
        if (S.tab === "contacts") await moChiTiet(S.sel);
      }
    });

    nap();
  }

  var api_pub = { render: function (el) { taoTrang(el); } };
  var thuan = { dinhDangTien: dinhDangTien, trangThaiHan: trangThaiHan, chiaTheoGiaiDoan: chiaTheoGiaiDoan,
                chuCaiDau: chuCaiDau, nhanSuKien: nhanSuKien };
  if (typeof window !== "undefined") window.JoyceCrm = Object.assign(api_pub, thuan);
  if (typeof module !== "undefined" && module.exports) module.exports = thuan;
})();
