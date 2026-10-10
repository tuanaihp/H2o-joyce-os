/* Trang Cẩm nang: bản đồ năng lực - "Joyce làm được gì" theo những gì ĐÃ kết nối
 * + đội ngũ (trợ lý/quy trình/kỹ năng) của brain đang chọn.
 *
 * V3 - redesign theo mẫu JOYCE_CAM_NANG_ONLY_V1.html:
 *   Tổng quan = hero + 4 thẻ số + lưới năng lực + cột phải (bắt đầu nhanh,
 *   phân bổ kỹ năng). Fanpage = 2 cột (danh sách Trang + tác vụ + bài đăng
 *   bên trái; báo cáo/quyền/nháp/việc tự động/trợ lý bên phải). Zalo = empty
 *   state 3 bước khi chưa kết nối. Phòng ban = 3 cột (đơn vị | lưới phòng +
 *   pipeline | drawer chi tiết sticky).
 *
 * V2 - tab con theo kênh (JOYCE SOCIAL OPS): trên "Tổng quan" còn một tab cho mỗi
 * kênh có module vận hành riêng (OPS_MODULES). Tab kênh = trạng thái kết nối,
 * số liệu THẬT qua /social/* (endpoint chỉ-đọc, đi qua gate readonly của plugin
 * host), tác vụ nhanh (gõ sẵn vào chat), việc tự động liên quan (loop/nhắc hẹn),
 * trợ lý phụ trách và tài liệu đặc tả. Thêm kênh mới = thêm 1 mục OPS_MODULES.
 *
 * File riêng thay vì nhét vào console.js (đã ~7k dòng), theo đúng cách packs.js/
 * conversations.js đang làm: console.js dựng khung rồi gọi window.JoyceCamNang.render(el).
 *
 * Dữ liệu vẽ từ endpoint THẬT (/connect/catalog, /connect/health, /social/*,
 * /agents, /workflows, /skills, /loops, /reminders, /brains) + catalog đặc tả
 * /static/data/h2o-skill-catalog.json - không tự khai danh sách connector trong
 * JS. Field `can_do`/`examples` của connector sống trong catalog (mcp-catalog.json
 * hoặc gói), trang này chỉ hiển thị. Mọi con số từ đặc tả đều gắn nhãn, không
 * bao giờ trình bày như năng lực đang chạy.
 */
(function () {
  "use strict";

  // Icon dùng chung của dashboard. KHÔNG emoji: tests/python/test_icons.py canh chuyện đó.
  function ic(ten, opt) { return (window.ic ? window.ic(ten, opt) : ""); }

  const esc = (s) => (s || "").toString()
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  // Từ điển vi.json khi file này chạy DƯỚI NODE (test nạp nó bằng `new Function`).
  // Trong `new Function` `require` không tồn tại - mượn process.mainModule.require.
  let _tuVi = null;
  function tuDienVi() {
    if (_tuVi) return _tuVi;
    _tuVi = {};
    try {
      const req = process.mainModule.require;
      const p = req("path");
      const goc = p.dirname(process.mainModule.filename);
      [p.join(process.cwd(), "dashboard/i18n/vi.json"),
       p.join(goc, "../../dashboard/i18n/vi.json"),
       p.join(goc, "i18n/vi.json")].forEach((d) => {
        if (Object.keys(_tuVi).length) return;
        try { _tuVi = req(d) || {}; } catch (e) { /* thử đường kế tiếp */ }
      });
    } catch (e) { /* trình duyệt: không có process, và cũng không cần */ }
    return _tuVi;
  }
  function tw(khoa, bien) {
    if (typeof window !== "undefined" && window.t) return window.t(khoa, bien);
    const s = tuDienVi()[khoa];
    if (s == null) return khoa;
    return String(s).replace(/\{(\w+)\}/g, (m, ten) =>
      (bien && bien[ten] != null) ? String(bien[ten]) : m);
  }

  function brain() {
    try { return window.JoyceSessions ? window.JoyceSessions.brain() : "brain"; }
    catch (e) { return "brain"; }
  }
  async function api(url) {
    const r = await fetch(url);
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    return { ok: r.ok && !(d && d.ok === false), status: r.status, data: d };
  }
  const fmtSo = (n) => {
    const v = Number(n);
    if (!isFinite(v)) return "-";
    try { return new Intl.NumberFormat("vi-VN").format(v); } catch (e) { return String(v); }
  };
  const fmtGio = (iso) => {
    const d = new Date(iso || 0);
    if (isNaN(d)) return "";
    try { return d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); }
    catch (e) { return String(iso || ""); }
  };

  // Icon connector 3 dạng, y như iconInner() của console.js: URL → <img>, tên Lucide → SVG,
  // còn lại in thẳng (catalog tự thêm có thể dùng emoji - đừng biến thành dấu hỏi).
  function iconInner(con) {
    const src = (con && con.icon) || "plug";
    if (/^(https?:|\/)/.test(src)) {
      return '<img class="ico-img" src="' + esc(src) + '" alt="" loading="lazy">';
    }
    return (window.Icons && window.Icons.has && window.Icons.has(src)) ? ic(src) : esc(src);
  }

  function diTo(trang) {
    try {
      const s = window.Alpine && window.Alpine.store("nav");
      if (s && s.go) { s.go(trang); return; }
    } catch (e) {}
    location.hash = "#" + trang;
  }

  // Bấm câu mẫu → sang trang Trò chuyện, ĐIỀN SẴN vào ô chat rồi focus. Không tự gửi:
  // một chip "đăng bài" mà gửi thẳng là Joyce đăng thật trước khi người đọc kịp sửa nội dung.
  function dienCau(cau) {
    diTo("chat");
    setTimeout(() => {
      const inp = document.getElementById("chatInput");
      if (!inp) return;
      inp.value = cau;
      try { inp.dispatchEvent(new Event("input", { bubbles: true })); } catch (e) {}
      try { inp.focus(); } catch (e) {}
      try { inp.style.height = "auto"; inp.style.height = Math.min(inp.scrollHeight, 160) + "px"; } catch (e) {}
    }, 60);
  }

  // Chấm trạng thái kết nối từ /connect/health (khóa theo id KẾT NỐI, không phải connector).
  function chamSucKhoe(conns, health) {
    if (!conns.length) return "";
    let allOk = true, anyOk = false;
    conns.forEach(c => {
      const h = health && health[c.id];
      if (h && h.ok) anyOk = true; else allOk = false;
    });
    if (anyOk) return '<span class="cdot on">●</span>';
    return '<span class="cdot" style="color:var(--warn-ink,#b9821f)">●</span>';
  }

  const QUYEN = { full: "cs.cn_perm_full", safe: "cs.cn_perm_safe", readonly: "cs.cn_perm_readonly" };
  function nhanQuyen(conns) {
    return conns.map(c => tw(QUYEN[c.perm] || "cs.cn_perm_readonly"))
      .filter((v, i, a) => a.indexOf(v) === i);
  }
  function quyenCaoNhat(conns) {
    if (conns.some(c => c.perm === "full")) return "full";
    if (conns.some(c => c.perm === "safe")) return "safe";
    return "readonly";
  }

  // Panel khung chuẩn: đầu panel (icon + tiêu đề + mô tả) + thân. `phai` = HTML góc phải.
  function panel(icon, tieude, mota, inner, phai) {
    return '<section class="cn-panel"><div class="cn-panel-h"><div class="cn-panel-ht">'
      + (icon ? '<span class="cn-panel-i">' + ic(icon) + '</span>' : '')
      + '<div class="cn-panel-tb"><h3>' + esc(tieude) + '</h3>'
      + (mota ? '<p>' + esc(mota) + '</p>' : "")
      + '</div></div>' + (phai || "") + '</div>'
      + '<div class="cn-panel-b">' + inner + '</div></section>';
  }
  function pill(loai, txt) {
    return '<span class="cn-pill ' + loai + '">' + esc(txt) + '</span>';
  }

  // ============================================================
  // TAB CON - module vận hành theo kênh. `conn` = connector id trong catalog;
  // `kw` = regex lọc loop/nhắc hẹn/trợ lý liên quan tới kênh; `render` nhận
  // {el, con, conns, health, agents} rồi tự fetch phần còn lại từng section
  // (lazy: bảng số liệu không chặn phần còn lại của trang).
  // ============================================================
  const OPS_MODULES = [
    {
      id: "fanpage", conn: "facebook-pages", icon: "share-2",
      labelKey: "camnang.tab_fanpage", kw: /facebook|fb_|fanpage|fan page|\btrang\b/i,
      render: renderFanpageOps,
    },
    {
      id: "zalo", conn: "zalo", icon: "message-circle",
      labelKey: "camnang.tab_zalo", kw: /zalo/i,
      render: renderKenOps,
    },
    // conn: null = tab không gắn connector - luôn hiện (bản đồ phòng ban theo spec V1.1).
    {
      id: "phongban", conn: null, icon: "layers",
      labelKey: "camnang.tab_phongban", kw: /./,
      render: renderPhongBan,
    },
  ];

  const CN_STATE = { tab: "tongquan", fbPage: "", pbUnit: "studio", pbDept: "", pbQ: "" };
  let _rootEl = null;
  // Đồng bộ chấm sáng trên rail: mục con của Cẩm nang sáng theo store.nav.cnSub.
  function syncRailSub(id) {
    try {
      const s = window.Alpine && window.Alpine.store("nav");
      if (s) s.cnSub = id;
    } catch (e) {}
  }
  function chonTab(id, extra) {
    CN_STATE.tab = id;
    if (extra && extra.pbUnit) { CN_STATE.pbUnit = extra.pbUnit; CN_STATE.pbDept = ""; CN_STATE.pbQ = ""; }
    syncRailSub(id);
    if (_rootEl) render(_rootEl);
  }

  // ---------- Khối dùng chung cho mọi tab kênh ----------

  // Thẻ trạng thái kết nối của kênh: tài khoản + quyền + sức khoẻ + nút sang trang Kết nối.
  function theTrangThai(con, conns, health) {
    const noi = conns.length > 0;
    let h = '<div class="cn-ops-status ' + (noi ? "on" : "off") + '">'
      + '<span class="cn-ico">' + iconInner(con || {}) + '</span><div class="cn-ops-status-t">';
    if (noi) {
      h += '<b>' + conns.map(c => esc(c.label || c.id)).join(" · ") + '</b>'
        + '<span class="cn-sub">' + esc(nhanQuyen(conns).join(" · ")) + '</span>';
    } else {
      h += '<b>' + esc(tw("camnang.ops_notconn")) + '</b>'
        + '<span class="cn-sub">' + esc(tw("camnang.ops_notconn_d")) + '</span>';
    }
    h += '</div>' + chamSucKhoe(conns, health)
      + '<button type="button" class="mp-btn" data-goto="mcp">'
      + esc(tw(noi ? "camnang.ops_setup" : "camnang.go_connect")) + '</button></div>';
    return h;
  }

  // Lưới câu mẫu dạng thẻ (prompt-grid của mẫu): {page} thay bằng Trang đang chọn.
  function promptGrid(ds) {
    return '<div class="cn-pgrid">' + ds.map(x =>
      '<button type="button" class="cn-prompt" data-ask="' + esc(x.cau) + '">'
      + (x.icon ? '<span class="cn-prompt-i">' + ic(x.icon) + '</span>' : "")
      + '<span>' + esc(x.cau) + '</span></button>').join("") + '</div>';
  }

  // Chips câu mẫu nhỏ gọn (dùng cho nháp / câu đơn).
  function chipsCau(ds) {
    return '<div class="cn-ex">' + ds.map(x =>
      '<button type="button" class="cn-chip" data-ask="' + esc(x.cau) + '">'
      + (x.icon ? ic(x.icon) + " " : "") + esc(x.cau) + '</button>').join("") + '</div>';
  }

  // Việc tự động liên quan tới kênh: loop + nhắc hẹn lọc theo từ khoá kw.
  async function napViecTuDong(box, kw) {
    const b = encodeURIComponent(brain());
    const [loops, rems] = await Promise.all([
      api("/loops?brain=" + b).then(r => (r.data && r.data.loops) || []).catch(() => []),
      api("/reminders?brain=" + b).then(r => (r.data && r.data.pending) || []).catch(() => []),
    ]);
    const loc = (txt) => kw.test(txt || "");
    const vongLap = loops.filter(l => loc(l.name + " " + (l.goal || "") + " " + (l.slug || "")));
    const nhac = rems.filter(r => loc(r.text + " " + (r.label || "")));
    if (!vongLap.length && !nhac.length) {
      box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.ops_jobs_none")) + '</div>'
        + '<button type="button" class="mp-btn" data-goto="kanban">' + esc(tw("camnang.ops_jobs_go")) + '</button>';
      return;
    }
    let h = '<div class="cn-jobs">';
    vongLap.forEach(l => {
      const bat = l.enabled !== false && l.paused !== true;
      h += '<div class="cn-job"><span class="cdot ' + (bat ? "on" : "") + '">●</span>'
        + '<div class="cn-job-t"><b>' + esc(l.name || l.slug) + '</b>'
        + '<span class="cn-sub">' + ic("repeat") + ' '
        + esc(tw("camnang.ops_job_loop", { phut: String(l.interval_min || "?") })) + '</span></div></div>';
    });
    nhac.forEach(r => {
      h += '<div class="cn-job"><span class="cdot on">●</span>'
        + '<div class="cn-job-t"><b>' + esc(r.text || r.label || "") + '</b>'
        + '<span class="cn-sub">' + ic("alarm-clock") + ' '
        + esc(fmtGio(new Date((r.due_at || 0) * 1000))) + (r.cron ? " · cron" : "") + '</span></div></div>';
    });
    h += '</div><button type="button" class="mp-btn" data-goto="kanban">' + esc(tw("camnang.ops_jobs_go")) + '</button>';
    box.innerHTML = h;
    box.querySelectorAll("[data-goto]").forEach(n => n.onclick = () => diTo(n.dataset.goto));
  }

  // Trợ lý của brain phù hợp kênh (tên/vai trò khớp từ khoá) - tối đa 4.
  function theTroLy(agents, kw) {
    const khop = agents.filter(a => kw.test((a.name || "") + " " + (a.role || "")));
    const hien = (khop.length ? khop : agents).slice(0, 4);
    if (!hien.length) return "";
    return '<div class="cn-grid">' + hien.map(a =>
      '<div class="cn-mini"><div class="cn-mini-t">' + ic("bot") + ' <b>' + esc(a.name || a.slug) + '</b></div>'
      + (a.role ? '<div class="cn-mini-d">' + esc(a.role) + '</div>' : "")
      + '</div>').join("") + '</div>';
  }

  // Mở file trong vault brain đang chọn (vd wiki/joyce-social-ops-spec.md) - thẻ đặc tả
  // trước đây data-goto="learn" nhảy sang trang Tự học (cấu hình), sai đích hoàn toàn.
  function moFileVault(path) {
    try {
      if (typeof window.JoyceOpenVaultPath === "function") { window.JoyceOpenVaultPath(path); return; }
      if (typeof window.JoyceOpenFiles === "function") { window.JoyceOpenFiles(path); return; }
    } catch (e) {}
    diTo("files");
  }

  function ganChip(el) {
    el.querySelectorAll("[data-ask]").forEach(ch =>
      ch.onclick = () => dienCau(ch.dataset.ask || ""));
    el.querySelectorAll("[data-goto]").forEach(n =>
      n.onclick = () => diTo(n.dataset.goto));
    el.querySelectorAll("[data-file]").forEach(n =>
      n.onclick = () => moFileVault(n.dataset.file || ""));
    el.querySelectorAll("[data-open-tab]").forEach(n =>
      n.onclick = () => chonTab(n.dataset.openTab, { pbUnit: n.dataset.unit }));
  }

  // ============================================================
  // TAB FANPAGE (facebook-pages) - Social Ops kênh đầu tiên.
  // Bố cục 2 cột theo mẫu: trái = Trang + tác vụ + bài đăng; phải = báo cáo
  // tuần + quyền + nháp chờ duyệt + việc tự động + trợ lý + đặc tả.
  // ============================================================

  const FB_METRIC = {
    page_media_view: "camnang.m_media_view", page_views_total: "camnang.m_page_views",
    page_post_engagements: "camnang.m_engagements", page_daily_follows: "camnang.m_follows",
    page_daily_unfollows: "camnang.m_unfollows", page_follows: "camnang.m_followers",
    page_video_views: "camnang.m_video_views",
  };

  async function renderFanpageOps(el, ctx, mod) {
    const { conns, health } = ctx;
    let h = theTrangThai(ctx.con, conns, health);
    if (!conns.length) { el.innerHTML = h; ganChip(el); return; }

    h += '<div class="cn-2col"><div class="cn-col">'
      + panel("users", tw("camnang.fb_pages"), tw("camnang.fb_pages_d"),
          '<div id="cnFbPages" class="cn-plist"><div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div></div>',
          pill("good", tw("camnang.st_connected")))
      + panel("zap", tw("camnang.ops_tasks"), tw("camnang.fb_tasks_d"), '<div id="cnFbTasks"></div>')
      + panel("list-todo", tw("camnang.fb_posts"), "", '<div id="cnFbPosts"></div>')
      + '</div><aside class="cn-col">'
      + panel("chart-column", tw("camnang.fb_report"), tw("camnang.fb_report_d"),
          '<div id="cnFbReport"><div class="cn-mini-d">' + esc(tw("camnang.fb_pick_page")) + '</div></div>')
      + panel("check", tw("camnang.fb_perm"), tw("camnang.fb_perm_d"), theQuyenFanpage(conns))
      + panel("square-pen", tw("camnang.fb_drafts"), "",
          '<div id="cnFbDrafts"><div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div></div>')
      + panel("repeat", tw("camnang.ops_jobs"), "",
          '<div id="cnFbJobs"><div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div></div>')
      + panel("bot", tw("camnang.ops_agents"), "", theTroLy(ctx.agents || [], mod.kw)
          || '<div class="cn-mini-d">' + esc(tw("camnang.ops_agents_none")) + '</div>')
      + panel("scroll-text", tw("camnang.ops_spec"), "",
          '<div class="cn-mini cn-mini-off" data-file="wiki/joyce-social-ops-spec.md"><div class="cn-mini-t">'
          + ic("book-open") + ' <b>Joyce Social Ops - đặc tả V1</b></div>'
          + '<div class="cn-mini-d">' + esc(tw("camnang.ops_spec_d")) + '</div></div>')
      + '</aside></div>';
    el.innerHTML = h;
    ganChip(el);

    napFanpages(ctx.con);
    napBaiNhap(el.querySelector("#cnFbDrafts"), mod.kw);
    napViecTuDong(el.querySelector("#cnFbJobs"), mod.kw);
  }

  // Quyền đang dùng: 3 dòng (đọc / phản hồi / xuất bản) theo mức quyền THẬT của
  // kết nối. Xuất bản luôn hiển thị "Duyệt" - spec bắt buộc duyệt trước khi đăng.
  function theQuyenFanpage(conns) {
    const q = quyenCaoNhat(conns);
    const co = pill("good", tw("camnang.perm_yes"));
    const duyet = pill("wait", tw("camnang.perm_review"));
    const thieu = pill("wait", tw("camnang.perm_miss"));
    const row = (icon, t, d, p) =>
      '<div class="cn-permrow"><span class="cn-perm-i">' + ic(icon) + '</span>'
      + '<div class="cn-perm-t"><b>' + esc(t) + '</b><span>' + esc(d) + '</span></div>' + p + '</div>';
    return row("eye", tw("camnang.perm_read_t"), tw("camnang.perm_read_d"), co)
      + row("message-circle", tw("camnang.perm_reply_t"), tw("camnang.perm_reply_d"),
            q === "readonly" ? thieu : co)
      + row("send", tw("camnang.perm_pub_t"), tw("camnang.perm_pub_d"),
            q === "full" ? duyet : thieu);
  }

  async function napFanpages(con) {
    const box = document.getElementById("cnFbPages");
    if (!box) return;
    const r = await api("/social/facebook/pages?brain=" + encodeURIComponent(brain()));
    if (!r.ok) {
      box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.fb_err", { loi: (r.data && r.data.error) || r.status })) + '</div>';
      return;
    }
    const pages = (r.data && (r.data.pages || (Array.isArray(r.data) ? r.data : []))) || [];
    const daGo = (r.data && r.data.hidden) || [];
    // Hàng Trang là <div role=button> chứ không phải <button>: bên trong còn nút Gỡ, mà nút
    // lồng trong nút là HTML sai (trình duyệt tách nó ra ngoài, bấm Gỡ thành bấm chọn Trang).
    box.innerHTML = (pages.length ? pages.map(p => {
      const nq = (p.tasks || []).length;
      return '<div role="button" tabindex="0" class="cn-prow cn-page" data-page="' + esc(p.id)
        + '" data-pname="' + esc(p.name) + '">'
        + '<span class="cn-plogo">' + iconInner(con || {}) + '</span>'
        + '<span class="cn-pmain"><b>' + esc(p.name) + '</b><span>' + esc(p.category || "") + '</span></span>'
        + '<span class="cn-pcell"><b class="cn-mono">' + esc(p.id) + '</b>'
        + '<span>' + (nq ? esc(tw("camnang.fb_tasks_n", { so: nq })) : "") + '</span></span>'
        + '<button type="button" class="cn-popen" data-fbopen="' + esc(p.id) + '"'
        + ' title="' + esc(tw("camnang.fb_open_t")) + '" aria-label="' + esc(tw("camnang.fb_open_t") + ": " + p.name) + '">'
        + ic("external-link") + '</button>'
        + '<button type="button" class="cn-prm" data-hide="' + esc(p.id) + '" data-pname="' + esc(p.name) + '"'
        + ' title="' + esc(tw("camnang.fb_hide_t")) + '" aria-label="' + esc(tw("camnang.fb_hide_t") + ": " + p.name) + '">'
        + ic("x") + '<span>' + esc(tw("camnang.fb_hide")) + '</span></button>'
        + '<span class="cn-pgo">' + ic("chevron-right") + '</span></div>';
    }).join("") : '<div class="cn-mini-d">' + esc(tw("camnang.fb_pages_none")) + '</div>')
      + theThemTrang(daGo, r.data && r.data.conn_id);
    ganThemTrang(box, con, r.data && r.data.conn_id);
    if (!pages.length) return;
    const chon = (c) => {
      CN_STATE.fbPage = c.dataset.page;
      box.querySelectorAll(".cn-page").forEach(x => x.classList.toggle("sel", x === c));
      napBaoCao(c.dataset.page, c.dataset.pname);
      napBaiDang(c.dataset.page);
      napTacVu();
    };
    // Nút link mở thẳng Trang trên Facebook (facebook.com/<id> đổ về vanity URL nếu có).
    // stopPropagation + lọc closest ở handler hàng: bấm icon không được thành "chọn Trang".
    box.querySelectorAll("[data-fbopen]").forEach(b =>
      b.onclick = (e) => {
        e.stopPropagation();
        window.open("https://www.facebook.com/" + encodeURIComponent(b.dataset.fbopen), "_blank", "noopener");
      });
    box.querySelectorAll(".cn-page").forEach(c => {
      c.onclick = (e) => { if (!e.target.closest(".cn-prm,.cn-popen")) chon(c); };
      c.onkeydown = (e) => {
        if (e.target !== c || (e.key !== "Enter" && e.key !== " ")) return;
        e.preventDefault(); chon(c);
      };
    });
    box.querySelectorAll(".cn-prm").forEach(b =>
      b.onclick = async (e) => {
        e.stopPropagation();
        const dlg = window.JoyceDialog;
        const dongY = dlg ? await dlg.confirm(tw("camnang.fb_hide_q", { ten: b.dataset.pname }),
          { title: tw("camnang.fb_hide_t"), okText: tw("camnang.fb_hide"), kind: "warn" }) : true;
        if (!dongY) return;
        if (String(CN_STATE.fbPage) === String(b.dataset.hide)) CN_STATE.fbPage = null;
        await doiHienTrang(b.dataset.hide, true, con);
      });
    // Tự chọn Trang đầu (hoặc trang đã chọn trước) để báo cáo + bài đăng hiện ngay.
    const chonTruoc = CN_STATE.fbPage && pages.find(p => String(p.id) === String(CN_STATE.fbPage));
    const p0 = chonTruoc || pages[0];
    CN_STATE.fbPage = p0.id;
    const node = box.querySelector('.cn-page[data-page="' + CSS.escape(String(p0.id)) + '"]');
    if (node) node.classList.add("sel");
    napBaoCao(p0.id, p0.name);
    napBaiDang(p0.id);
    napTacVu();
  }

  // Gỡ / thêm lại một Trang. Gỡ chỉ là Joyce thôi quản lý (máy chủ ghi hidden_pages vào kết
  // nối facebook-pages, plugin fb_* lọc theo): Facebook không cho app bỏ riêng một Trang khỏi
  // token, chỉ thu hồi được cả app.
  async function doiHienTrang(pid, an, con) {
    let d = null;
    try {
      const r = await fetch("/social/facebook/pages/visibility", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_id: String(pid), hidden: !!an, brain: brain() }) });
      d = await r.json().catch(() => null);
      if (!r.ok && d) d.ok = false;
    } catch (e) { d = null; }
    const dlg = window.JoyceDialog;
    if (!d || d.ok === false) {
      if (dlg) dlg.toast(tw("camnang.fb_vis_err", { loi: (d && d.error) || "" }), true);
      return;
    }
    if (dlg) dlg.toast(tw(an ? "camnang.fb_hidden_ok" : "camnang.fb_shown_ok"));
    napFanpages(con);
  }

  // Khối cuối danh sách: Trang đã gỡ (bấm Thêm lại) + nút đăng nhập Facebook lại để tick thêm
  // Trang mới. Trang chưa từng tick lúc đăng nhập thì Joyce không thấy, chỉ Facebook thêm được.
  function theThemTrang(daGo, connId) {
    let h = '<div class="cn-padd">';
    if (daGo.length) {
      h += '<div class="cn-padd-h">' + esc(tw("camnang.fb_hidden_h", { so: daGo.length })) + '</div>'
        + daGo.map(p => '<div class="cn-prow cn-prow-off">'
          + '<span class="cn-pmain"><b>' + esc(p.name) + '</b><span>' + esc(p.category || "") + '</span></span>'
          + '<button type="button" class="cn-padd-btn" data-show="' + esc(p.id) + '">' + ic("plus")
          + '<span>' + esc(tw("camnang.fb_show")) + '</span></button></div>').join("");
    }
    if (connId) {
      h += '<button type="button" class="cn-padd-btn cn-padd-fb" data-fb-add="1">' + ic("plus")
        + '<span>' + esc(tw("camnang.fb_add")) + '</span></button>'
        + '<div class="cn-padd-d">' + esc(tw("camnang.fb_add_d")) + '</div>';
    }
    return h + '</div>';
  }
  function ganThemTrang(box, con, connId) {
    box.querySelectorAll("[data-show]").forEach(b =>
      b.onclick = () => doiHienTrang(b.dataset.show, false, con));
    const nut = box.querySelector("[data-fb-add]");
    if (!nut || !connId) return;
    nut.onclick = async () => {
      nut.disabled = true;
      let d = null;
      try {
        const r = await fetch("/connect/oauth/start", { method: "POST",
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: connId }) });
        d = await r.json().catch(() => null);
      } catch (e) { d = null; }
      nut.disabled = false;
      if (!d || d.ok === false || !d.url) {
        if (window.JoyceDialog) window.JoyceDialog.toast(tw("camnang.fb_vis_err", { loi: (d && d.error) || "" }), true);
        return;
      }
      window.open(d.url, "_blank");
      // Đăng nhập xong quay lại tab này là nạp lại danh sách, Trang vừa tick hiện ngay.
      window.addEventListener("focus", () => napFanpages(con), { once: true });
    };
  }

  // Báo cáo tuần: tổng giá trị mỗi metric + follower hiện tại + ghi chú metric trống/lỗi.
  async function napBaoCao(pid, pname) {
    const box = document.getElementById("cnFbReport");
    if (!box) return;
    box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div>';
    const r = await api("/social/facebook/insights?page_id=" + encodeURIComponent(pid)
      + "&period=week&brain=" + encodeURIComponent(brain()));
    if (!r.ok) {
      box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.fb_err", { loi: (r.data && r.data.error) || r.status })) + '</div>';
      return;
    }
    const d = r.data || {};
    const tong = {};
    (d.metrics || []).forEach(m => {
      tong[m.name] = (m.values || []).reduce((s, v) => s + (Number(v.value) || 0), 0);
    });
    let h = '<div class="cn-stat-grid">';
    if (d.followers_count != null) {
      h += '<div class="cn-stat"><div class="cn-stat-n">' + fmtSo(d.followers_count) + '</div>'
        + '<div class="cn-stat-l">' + esc(tw("camnang.m_followers")) + '</div></div>';
    }
    Object.keys(FB_METRIC).forEach(k => {
      if (tong[k] == null) return;
      h += '<div class="cn-stat"><div class="cn-stat-n">' + fmtSo(tong[k]) + '</div>'
        + '<div class="cn-stat-l">' + esc(tw(FB_METRIC[k])) + '</div></div>';
    });
    h += '</div>';
    const trong = (d.metrics_trong || []).length, loi = (d.metrics_loi || []).length;
    if (trong || loi) {
      h += '<div class="cn-mini-d">'
        + (trong ? esc(tw("camnang.m_trong", { so: trong })) : "")
        + (trong && loi ? " · " : "")
        + (loi ? esc(tw("camnang.m_loi", { so: loi })) : "") + '</div>';
    }
    box.innerHTML = h;
  }

  // Bài gần đây: bảng nội dung + react/comment/share + link mở bài trên Facebook.
  async function napBaiDang(pid) {
    const box = document.getElementById("cnFbPosts");
    if (!box) return;
    box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div>';
    const r = await api("/social/facebook/posts?page_id=" + encodeURIComponent(pid)
      + "&limit=8&brain=" + encodeURIComponent(brain()));
    if (!r.ok) {
      box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.fb_err", { loi: (r.data && r.data.error) || r.status })) + '</div>';
      return;
    }
    const posts = ((r.data && r.data.data) || []);
    if (!posts.length) {
      box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.fb_posts_none")) + '</div>';
      return;
    }
    let h = '<div class="cn-tbl"><div class="cn-tr cn-th"><span>' + esc(tw("camnang.c_time")) + '</span>'
      + '<span>' + esc(tw("camnang.c_post")) + '</span>'
      + '<span class="cn-num">' + esc(tw("camnang.c_react")) + '</span>'
      + '<span class="cn-num">' + esc(tw("camnang.c_cmt")) + '</span>'
      + '<span class="cn-num">' + esc(tw("camnang.c_share")) + '</span><span></span></div>';
    posts.forEach(p => {
      const txt = (p.message || p.story || "").replace(/\s+/g, " ").slice(0, 90);
      const react = p.reactions && p.reactions.summary ? p.reactions.summary.total_count : 0;
      const cmt = p.comments && p.comments.summary ? p.comments.summary.total_count : 0;
      const share = p.shares ? p.shares.count : 0;
      h += '<div class="cn-tr"><span class="cn-mono">' + esc(fmtGio(p.created_time)) + '</span>'
        + '<span class="cn-clip">' + esc(txt) + '</span>'
        + '<span class="cn-num">' + fmtSo(react) + '</span>'
        + '<span class="cn-num">' + fmtSo(cmt) + '</span>'
        + '<span class="cn-num">' + fmtSo(share) + '</span>'
        + '<span>' + (p.permalink_url ? '<a class="cn-link" href="' + esc(p.permalink_url) + '" target="_blank" rel="noopener">' + ic("external-link") + '</a>' : "") + '</span></div>';
    });
    box.innerHTML = h + '</div>';
  }

  // Tác vụ nhanh Fanpage: 7 lời hứa của spec → thẻ prompt, {page} đổi theo Trang đang chọn.
  function napTacVu() {
    const box = document.getElementById("cnFbTasks");
    if (!box) return;
    const pname = (document.querySelector("#cnFbPages .cn-page.sel") || {}).dataset
      ? (document.querySelector("#cnFbPages .cn-page.sel").dataset.pname || "") : "";
    const p = pname ? ('"' + pname + '"') : "";
    const ds = [
      { icon: "chart-column", cau: tw("camnang.ex_fb_week", { page: p }) },
      { icon: "trending-up", cau: tw("camnang.ex_fb_top", { page: p }) },
      { icon: "inbox", cau: tw("camnang.ex_fb_cmt", { page: p }) },
      { icon: "square-pen", cau: tw("camnang.ex_fb_draft", { page: p }) },
      { icon: "play", cau: tw("camnang.ex_fb_reel", { page: p }) },
      { icon: "alarm-clock", cau: tw("camnang.ex_fb_cron", { page: p }) },
    ];
    box.innerHTML = promptGrid(ds);
    ganChip(box);
  }

  // Bài nháp chờ duyệt: task kanban của brain hiện tại khớp từ khoá kênh và đang ở
  // cột review (cần duyệt) hoặc queue. Nút "Duyệt" = move -> ready; dispatcher sẽ chạy
  // task (gọi fb_page_post) khi orchestration của brain bật. Đây là luồng duyệt THẬT của
  // Joyce, không phải UI riêng - ai tạo task bằng needs_approval thì nó nằm đây.
  async function napBaiNhap(box, kw) {
    if (!box) return;
    const b = encodeURIComponent(brain());
    const r = await api("/kanban?brain=" + b).catch(() => ({ ok: false }));
    const ops = (r.ok && r.data && r.data.operations) || {};
    const ds = ((ops.attention || []).concat(ops.queue || []))
      .filter(tk => kw.test((tk.title || "") + " " + (tk.intent || "") + " " + (tk.description || "")));
    let h = "";
    if (!ds.length) {
      h += '<div class="cn-mini-d">' + esc(tw("camnang.fb_drafts_none")) + '</div>';
    } else {
      h += '<div class="cn-jobs">' + ds.map(tk => {
        const choDuyet = tk.status === "review";
        return '<div class="cn-job"><span class="cdot' + (choDuyet ? "" : " on") + '">●</span>'
          + '<div class="cn-job-t"><b>' + esc(tk.title || tk.id) + '</b>'
          + '<span class="cn-sub">' + esc(tw("camnang.fb_draft_status", { st: tk.status }))
          + (choDuyet ? " · " + esc(tw("camnang.fb_draft_needs")) : "") + '</span></div>'
          + (choDuyet ? '<button type="button" class="mp-btn" data-approve="' + esc(tk.id) + '">'
            + esc(tw("camnang.fb_draft_ok")) + '</button>' : "")
          + '</div>';
      }).join("") + '</div>';
    }
    const pname = (document.querySelector("#cnFbPages .cn-page.sel") || {}).dataset
      ? (document.querySelector("#cnFbPages .cn-page.sel").dataset.pname || "") : "";
    h += chipsCau([{ icon: "square-pen", cau: tw("camnang.ex_fb_draftq", { page: pname ? '"' + pname + '"' : "" }) }]);
    box.innerHTML = h;
    ganChip(box);
    box.querySelectorAll("[data-approve]").forEach(n => n.onclick = async () => {
      n.disabled = true;
      const fd = new FormData();
      fd.append("id", n.dataset.approve); fd.append("status", "ready"); fd.append("brain", brain());
      try { await fetch("/kanban/task/move", { method: "POST", body: fd }); } catch (e) {}
      napBaiNhap(box, kw);
    });
  }

  // ============================================================
  // TAB KÊNH KHÁC (zalo, và connector khai sau này): khung chung -
  // trạng thái + năng lực + câu mẫu (từ catalog) + việc tự động liên quan.
  // Chưa kết nối → empty state 3 bước theo mẫu thay vì trang trống.
  // ============================================================
  function renderKenOps(el, ctx, mod) {
    const { con, conns, health, agents } = ctx;
    if (!conns.length) {
      const buoc = [1, 2, 3].map(i =>
        '<div class="cn-step"><b>' + esc(tw("camnang.k_step", { n: i })) + '</b>'
        + '<strong>' + esc(tw("camnang.k_step" + i + "_t")) + '</strong>'
        + '<span>' + esc(tw("camnang.k_step" + i + "_d")) + '</span></div>').join("");
      el.innerHTML = '<section class="cn-panel cn-estate"><div class="cn-estate-in">'
        + '<div class="cn-esym">' + iconInner(con || {}) + '</div>'
        + '<h2>' + esc(tw("camnang.k_empty_t", { ten: (con && con.name) || mod.id })) + '</h2>'
        + '<p>' + esc(tw("camnang.k_empty_d")) + '</p>'
        + '<div class="cn-steps">' + buoc + '</div>'
        + '<div class="cn-note"><span class="cn-note-i">' + ic("circle-help") + '</span><span>'
        + esc(tw("camnang.k_empty_note")) + '</span></div>'
        + '<div class="cn-hero-act">'
        + '<button type="button" class="mp-btn primary" data-goto="mcp">' + esc(tw("camnang.go_connect")) + '</button>'
        + '<button type="button" class="mp-btn" data-ask="' + esc(tw("camnang.k_ask", { ten: (con && con.name) || mod.id })) + '">'
        + esc(tw("camnang.k_ask_btn")) + '</button></div>'
        + '</div></section>';
      ganChip(el);
      return;
    }
    let h = theTrangThai(con, conns, health);
    const dos = (con && con.can_do) || [], exs = (con && con.examples) || [];
    h += '<div class="cn-2col"><div class="cn-col">';
    if (dos.length) {
      h += panel("sparkles", tw("camnang.ops_can_do"), "",
        '<ul class="cn-ul">' + dos.map(x => '<li>' + esc(x) + '</li>').join("") + '</ul>');
    }
    if (exs.length) {
      h += panel("zap", tw("camnang.ops_tasks"), "", promptGrid(exs.map(x => ({ cau: x }))));
    }
    h += '</div><aside class="cn-col">'
      + panel("repeat", tw("camnang.ops_jobs"), "",
          '<div id="cnOpsJobs"><div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div></div>')
      + panel("bot", tw("camnang.ops_agents"), "", theTroLy(agents || [], mod.kw)
          || '<div class="cn-mini-d">' + esc(tw("camnang.ops_agents_none")) + '</div>')
      + '</aside></div>';
    el.innerHTML = h;
    ganChip(el);
    napViecTuDong(el.querySelector("#cnOpsJobs"), mod.kw);
  }

  // ============================================================
  // TAB PHÒNG BAN - Department Brain + Skill Catalog theo spec V1.1,
  // bố cục 3 cột theo mẫu: đơn vị | lưới phòng + pipeline | drawer chi tiết.
  // Hai nguồn dữ liệu, gắn nhãn rõ để không lẫn:
  //   THẬT: GET /brains (não phòng ban đang có trên máy) + agents/skills của brain đang chọn.
  //   ĐẶC TẢ: /static/data/h2o-skill-catalog.json - 121 kỹ năng + 3 chuỗi trích từ spec.
  // ============================================================

  const PB_UNIT = {
    studio: { nhan: "camnang.pb_brand_studio", chain: "wedding" },
    academy: { nhan: "camnang.pb_brand_academy", chain: "academy" },
    shared: { nhan: "camnang.pb_brand_shared", chain: "knowledge_loop" },
  };

  function renderPhongBan(el, ctx, mod) {
    const { specCat } = ctx;
    const depts = (specCat && specCat.departments) || [];
    const chains = (specCat && specCat.chains) || {};
    const tenBrain = (x) => x.name || x.id || "";
    const brainsOf = (d) => (d.brain_prefix || [])
      .map(pf => (ctx.brains || []).filter(x => tenBrain(x).indexOf(pf) === 0))
      .reduce((a, x) => a.concat(x), []);
    // Map skill id -> tên để pipeline hiển thị tên ngắn thay vì slug dài.
    const tenSkill = {};
    depts.forEach(d => (d.skills || []).forEach(s => { tenSkill[s.id] = s.name; }));

    el.innerHTML =
      '<div class="cn-dept">'
      + '<aside class="cn-panel cn-units" id="cnPbUnits"></aside>'
      + '<div class="cn-dept-mid">'
      +   '<div class="cn-dept-top"><div class="cn-dept-t">'
      +   '<h3 id="cnPbUnitT"></h3><p id="cnPbUnitD"></p></div>'
      +   '<label class="cn-search"><span class="cn-search-i">' + ic("search") + '</span>'
      +   '<input id="cnPbSearch" type="search" placeholder="' + esc(tw("camnang.pb_search")) + '">'
      +   '</label></div>'
      +   '<div class="cn-dept-grid" id="cnPbGrid"></div>'
      +   '<div class="cn-flow"><div class="cn-flow-t"><span>' + ic("git-branch") + '</span>'
      +   '<div class="cn-panel-tb"><h3 id="cnPbChainT"></h3><p>'
      +   esc(tw("camnang.pb_flow_d")) + '</p></div>'
      +   '<span class="cn-badge-spec">' + esc(tw("camnang.pb_spec_badge")) + '</span></div>'
      +   '<div class="cn-flow-lane" id="cnPbLane"></div></div>'
      + '</div>'
      + '<aside class="cn-panel cn-drawer" id="cnPbDrawer"></aside>'
      + '</div>'
      // Phần dữ liệu THẬT bên dưới giữ nguyên.
      + '<div class="cn-sec">' + ic("database") + " " + esc(tw("camnang.pb_map")) + '</div>'
      + '<div id="cnPbBrains"><div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div></div>'
      + '<div class="cn-sec">' + ic("bot") + " " + esc(tw("camnang.pb_real")) + '</div>'
      + '<div class="cn-mini-d" style="margin-bottom:8px">' + esc(tw("camnang.pb_real_d")) + '</div>'
      + theNhanSu(ctx.agents || [], ctx.workflows || [], ctx.skills || [])
      + '<div class="cn-sec">' + ic("repeat") + " " + esc(tw("camnang.pb_jobs")) + '</div>'
      + '<div id="cnPbJobs"><div class="cn-mini-d">' + esc(tw("camnang.fb_loading")) + '</div></div>'
      + '<div class="cn-sec">' + ic("scroll-text") + " " + esc(tw("camnang.ops_spec")) + '</div>'
      + '<div class="cn-mini cn-mini-off" data-file="wiki/joyce-department-brain-spec.md"><div class="cn-mini-t">'
      + ic("book-open") + ' <b>Department Brain + Skill Catalog - đặc tả V1.1</b></div>'
      + '<div class="cn-mini-d">' + esc(tw("camnang.pb_spec_d")) + '</div></div>';
    ganChip(el);
    napBanDoNao(el.querySelector("#cnPbBrains"), ctx.brains);
    napViecTuDong(el.querySelector("#cnPbJobs"), mod.kw);

    // ---- Phần catalog 3 cột (đặc tả) ----
    const unitsBox = el.querySelector("#cnPbUnits");
    const grid = el.querySelector("#cnPbGrid");
    const drawer = el.querySelector("#cnPbDrawer");
    const lane = el.querySelector("#cnPbLane");
    const chainT = el.querySelector("#cnPbChainT");
    if (!depts.length) {
      unitsBox.innerHTML = '<div class="cn-mini-d" style="padding:10px">' + esc(tw("camnang.pb_catalog_none")) + '</div>';
      return;
    }

    function renderUnits() {
      unitsBox.innerHTML = Object.keys(PB_UNIT).map(u => {
        const grp = depts.filter(d => d.brand === u);
        const n = grp.reduce((s, d) => s + (d.skills || []).length, 0);
        return '<button type="button" class="cn-unit' + (CN_STATE.pbUnit === u ? " on" : "")
          + '" data-unit="' + u + '"><b>' + esc(tw(PB_UNIT[u].nhan)) + '</b>'
          + '<span>' + esc(tw("camnang.pb_unit_line", { p: grp.length, s: n })) + '</span></button>';
      }).join("");
      unitsBox.querySelectorAll(".cn-unit").forEach(b =>
        b.onclick = () => { CN_STATE.pbUnit = b.dataset.unit; CN_STATE.pbDept = ""; CN_STATE.pbQ = "";
          const q = el.querySelector("#cnPbSearch"); if (q) q.value = "";
          renderUnits(); renderGrid(); });
    }

    function phongHien() {
      const q = (CN_STATE.pbQ || "").toLowerCase();
      return depts.filter(d => d.brand === CN_STATE.pbUnit)
        .filter(d => !q || (d.name + " " + (d.desc || "") + " " + d.id).toLowerCase().includes(q));
    }

    function renderGrid() {
      const u = PB_UNIT[CN_STATE.pbUnit];
      const ds = phongHien();
      el.querySelector("#cnPbUnitT").textContent = tw(u.nhan);
      el.querySelector("#cnPbUnitD").textContent = tw("camnang.pb_unit_sub", {
        p: ds.length, s: ds.reduce((s2, d) => s2 + (d.skills || []).length, 0) });
      // Pipeline của đơn vị.
      const buoc = chains[u.chain] || [];
      chainT.textContent = tw(u.chain === "wedding" ? "camnang.pb_chain_wedding" : u.chain === "academy" ? "camnang.pb_chain_academy" : "camnang.pb_chain_kl")
        + " · " + tw("camnang.pb_step_n", { so: buoc.length });
      lane.innerHTML = buoc.map((s, i) =>
        '<div class="cn-fstep"><b>' + esc(tw("camnang.pb_step", { n: i + 1 })) + '</b>'
        + '<strong>' + esc(tenSkill[s] || s) + '</strong></div>').join("");
      // Lưới phòng.
      if (!ds.length) {
        grid.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.pb_none_q")) + '</div>';
        renderDrawer(null);
        return;
      }
      grid.innerHTML = ds.map((d, i) => {
        const thuc = brainsOf(d);
        return '<button type="button" class="cn-dcard" data-i="' + i + '">'
          + '<div class="cn-dcard-h"><span>' + esc(tw("camnang.pb_skills_n_up", { so: (d.skills || []).length })) + '</span>'
          + (thuc.length ? '<em class="cn-badge-real">' + esc(tw("camnang.pb_brain_map", { so: thuc.length })) + '</em>' : "")
          + '</div><h4>' + esc(d.name) + '</h4><p>' + esc(d.desc || "") + '</p></button>';
      }).join("");
      grid.querySelectorAll(".cn-dcard").forEach(c =>
        c.onclick = () => {
          CN_STATE.pbDept = ds[Number(c.dataset.i)].id;
          grid.querySelectorAll(".cn-dcard").forEach(x => x.classList.toggle("sel", x === c));
          renderDrawer(ds[Number(c.dataset.i)]);
        });
      // Chọn phòng đầu tiên (hoặc phòng đã chọn còn trong tầm lọc).
      const cur = ds.find(d => d.id === CN_STATE.pbDept) || ds[0];
      CN_STATE.pbDept = cur.id;
      const node = grid.querySelector('.cn-dcard[data-i="' + ds.indexOf(cur) + '"]');
      if (node) node.classList.add("sel");
      renderDrawer(cur);
    }

    function renderDrawer(d) {
      if (!d) {
        drawer.innerHTML = '<div class="cn-drawer-t"><span class="cn-drawer-eb">'
          + esc(tw("camnang.pb_none_q")) + '</span></div>';
        return;
      }
      const thuc = brainsOf(d);
      drawer.innerHTML =
        '<div class="cn-drawer-t"><span class="cn-drawer-eb">'
        + esc(tw("camnang.pb_skills_n", { so: (d.skills || []).length }))
        + ' <span class="cn-badge-spec">' + esc(tw("camnang.pb_spec_badge")) + '</span></span>'
        + '<h3>' + esc(d.name) + '</h3><p>' + esc(d.desc || "") + '</p></div>'
        + '<div class="cn-drawer-b">'
        + (thuc.length
            ? '<div class="cn-mini-d cn-pb-brains">' + esc(tw("camnang.pb_brains_real")) + " "
              + thuc.map(x => '<b>' + esc(x.label || tenBrain(x)) + '</b>').join(", ") + ' '
              + '<span class="cn-pb-skillcount" data-brains="' + esc(thuc.map(tenBrain).join("|")) + '"></span></div>'
            : '<div class="cn-mini-d cn-pb-brains">' + esc(tw("camnang.pb_brain_none")) + '</div>')
        + '<div class="cn-dlist">'
        + (d.skills || []).map((s, i) =>
            '<div class="cn-drow"><div class="cn-drow-t"><b>' + esc(s.name) + '</b>'
            + (s.approval && s.approval !== "Không"
                ? '<span class="cn-badge-appr">' + ic("check") + ' ' + esc(tw("camnang.pb_needs_appr")) + '</span>' : "")
            + '</div>'
            + (s.trigger ? '<span>' + esc(tw("camnang.pb_trigger", { x: s.trigger })) + '</span>' : "")
            + '</div>').join("") + '</div></div>'
        + '<div class="cn-drawer-act">'
        + '<button type="button" class="mp-btn" data-ask="'
        + esc(tw("camnang.pb_ask", { ten: d.name })) + '">' + ic("message-circle") + ' '
        + esc(tw("camnang.pb_ask_btn")) + '</button>'
        + '<button type="button" class="mp-btn primary" data-goto="skills">'
        + ic("puzzle") + ' ' + esc(tw("camnang.pb_open_skills")) + '</button></div>';
      ganChip(drawer);
      // Đếm skill THẬT trong các brain map sang phòng (lazy fetch khi drawer render).
      drawer.querySelectorAll(".cn-pb-skillcount[data-brains]").forEach(async sp => {
        const ns = (sp.dataset.brains || "").split("|").filter(Boolean);
        let so = 0;
        await Promise.all(ns.map(nb =>
          api("/skills?brain=" + encodeURIComponent(nb))
            .then(r => { so += ((r.data && r.data.skills) || []).length; })
            .catch(() => {})));
        sp.textContent = "· " + tw("camnang.pb_skills_real", { so });
      });
    }

    el.querySelector("#cnPbSearch").addEventListener("input", ev => {
      CN_STATE.pbQ = ev.target.value || ""; renderGrid();
    });
    renderUnits();
    renderGrid();
  }

  // Bản đồ não thật: /brains trả {brains:[{id,label,group,brand,...}]} - nhóm theo `group`
  // (khối phòng ban mà admin đã gán trong registry). Brain chưa gán khối rơi về nhóm "Khác".
  function napBanDoNao(box, ds) {
    if (!ds || !ds.length) {
      box.innerHTML = '<div class="cn-mini-d">' + esc(tw("camnang.pb_map_none")) + '</div>';
      return;
    }
    const nhom = {};
    ds.forEach(x => {
      const g = x.group || tw("camnang.pb_group_other");
      (nhom[g] = nhom[g] || []).push(x);
    });
    const cur = brain();
    let h = "";
    Object.keys(nhom).sort().forEach(g => {
      h += '<div class="cn-pb-grp"><div class="cn-pb-grp-t"><b>' + esc(g) + '</b>'
        + '<span class="cn-perm">' + esc(tw("camnang.pb_brain_n", { so: nhom[g].length })) + '</span></div>'
        + '<div class="cn-grid">' + nhom[g].map(x =>
          '<div class="cn-mini' + (x.id === cur || x.name === cur ? " cn-page sel" : "") + '">'
          + '<div class="cn-mini-t">' + ic("database") + ' <b>' + esc(x.label || x.name || x.id) + '</b></div>'
          + (x.brand ? '<div class="cn-mini-d">' + esc(x.brand) + '</div>' : "")
          + '</div>').join("") + '</div></div>';
    });
    box.innerHTML = h;
  }

  // ============================================================
  // TAB TỔNG QUAN - bố cục theo mẫu: hero + 4 thẻ số + lưới năng lực;
  // cột phải: bắt đầu nhanh + phân bổ kỹ năng; dưới: nguồn đã nối + đội ngũ.
  // ============================================================
  function theConnector(con, conns, health) {
    const dos = con.can_do || [], exs = con.examples || [];
    const quyen = nhanQuyen(conns);
    return '<div class="cn-card">'
      + '<div class="cn-card-head">'
      +   '<span class="cn-ico">' + iconInner(con) + '</span>'
      +   '<div class="cn-card-t"><b>' + esc(con.name || con.id) + '</b>'
      +   '<span class="cn-sub">' + conns.map(c => esc(c.label || "")).join(" · ")
      +     (quyen.length ? ' <span class="cn-perm">' + esc(quyen.join(" · ")) + '</span>' : "") + '</span></div>'
      +   chamSucKhoe(conns, health)
      + '</div>'
      + (dos.length
          ? '<ul class="cn-ul">' + dos.map(x => '<li>' + esc(x) + '</li>').join("") + '</ul>'
          : (con.description ? '<div class="cn-desc">' + esc(con.description) + '</div>' : ""))
      + (exs.length
          ? '<div class="cn-ex">' + exs.map(x =>
              '<button type="button" class="cn-chip" data-ask="' + esc(x) + '">' + esc(x) + '</button>').join("") + '</div>'
          : "")
      + '</div>';
  }

  function theNhanSu(agents, workflows, skills) {
    if (!agents.length && !workflows.length && !skills.length) return "";
    let h = '<div class="cn-sec">' + esc(tw("camnang.team")) + '</div><div class="cn-grid">';
    agents.forEach(a => {
      h += '<div class="cn-mini"><div class="cn-mini-t">' + ic("bot") + ' <b>' + esc(a.name || a.slug) + '</b></div>'
        + (a.role ? '<div class="cn-mini-d">' + esc(a.role) + '</div>' : "")
        + '</div>';
    });
    workflows.forEach(w => {
      const nb = (w.steps || []).length;
      h += '<div class="cn-mini"><div class="cn-mini-t">' + ic("workflow") + ' <b>' + esc(w.name || w.slug) + '</b>'
        + (nb ? ' <span class="cn-perm">' + tw("camnang.steps_n", { so: nb }) + '</span>' : "") + '</div>'
        + (w.description ? '<div class="cn-mini-d">' + esc(w.description) + '</div>' : "")
        + '</div>';
    });
    skills.forEach(s => {
      h += '<div class="cn-mini"><div class="cn-mini-t">' + ic("puzzle") + ' <b>' + esc(s.name || s.slug) + '</b></div>'
        + (s.description ? '<div class="cn-mini-d">' + esc(s.description) + '</div>' : "")
        + '</div>';
    });
    return h + '</div>';
  }

  function renderTongQuan(el, ctx) {
    const { cat, byCon, health, agents, workflows, skills, brains, specCat } = ctx;
    const connected = cat.filter(c => (byCon[c.id] || []).length);
    const chuaNoi = cat.filter(c => !(byCon[c.id] || []).length);
    const depts = (specCat && specCat.departments) || [];
    const nSpec = depts.reduce((s, d) => s + (d.skills || []).length, 0);
    const unitN = (b) => depts.filter(d => d.brand === b)
      .reduce((s, d) => s + (d.skills || []).length, 0);
    const unitP = (b) => depts.filter(d => d.brand === b).length;

    // Thẻ năng lực nổi bật: 2 kênh (trạng thái THẬT) + 2 đơn vị (số liệu ĐẶC TẢ).
    function theCap(opt) {
      return '<button type="button" class="cn-cap" data-open-tab="' + esc(opt.tab) + '"'
        + (opt.unit ? ' data-unit="' + esc(opt.unit) + '"' : "") + '>'
        + '<div class="cn-cap-top"><span class="cn-cap-ico">' + iconInner(opt.con || { icon: opt.icon }) + '</span>'
        + opt.badge + '</div>'
        + '<h4>' + esc(opt.t) + '</h4><p>' + esc(opt.d) + '</p>'
        + '<span class="cn-cap-l">' + esc(opt.l) + ' ' + ic("chevron-right") + '</span></button>';
    }
    const fbCon = cat.find(c => c.id === "facebook-pages") || {};
    const zlCon = cat.find(c => c.id === "zalo") || {};
    const stNoi = (cid) => (byCon[cid] || []).length
      ? pill("good", tw("camnang.st_connected")) : pill("wait", tw("camnang.st_notconn"));

    // Bắt đầu nhanh: 4 thao tác mở đúng tab con.
    const nhanh = [
      { t: "camnang.qs1_t", d: "camnang.qs1_d", tab: "fanpage" },
      { t: "camnang.qs2_t", d: "camnang.qs2_d", tab: "phongban" },
      { t: "camnang.qs3_t", d: "camnang.qs3_d", tab: "phongban", unit: "studio" },
      { t: "camnang.qs4_t", d: "camnang.qs4_d", tab: "phongban", unit: "academy" },
    ].map((x, i) =>
      '<button type="button" class="cn-qt" data-open-tab="' + x.tab + '"'
      + (x.unit ? ' data-unit="' + x.unit + '"' : "") + '>'
      + '<span class="cn-qt-i">' + String(i + 1).padStart(2, "0") + '</span>'
      + '<span class="cn-qt-t"><b>' + esc(tw(x.t)) + '</b><span>' + esc(tw(x.d)) + '</span></span>'
      + '<span class="cn-pgo">' + ic("chevron-right") + '</span></button>').join("");

    // Phân bổ kỹ năng: 3 đơn vị, % trên tổng đặc tả.
    const brand = (u, dkey) => {
      const n = unitN(u), pc = nSpec ? Math.round(n / nSpec * 1000) / 10 : 0;
      return '<div class="cn-brand"><div class="cn-brand-h"><h4>' + esc(tw(PB_UNIT[u].nhan)) + '</h4>'
        + '<b>' + fmtSo(n) + '</b></div><p>' + esc(tw(dkey)) + '</p>'
        + '<div class="cn-bar"><span style="width:' + pc + '%"></span></div>'
        + '<div class="cn-brand-f"><span>' + esc(tw("camnang.pb_dept_n", { so: unitP(u) }))
        + '</span><span>' + pc + '%</span></div></div>';
    };

    const metric = (n, l, note, spec) =>
      '<div class="cn-metric"><div class="cn-metric-l">' + esc(l)
      + (spec ? ' <span class="cn-badge-spec">' + esc(tw("camnang.pb_spec_badge")) + '</span>' : "")
      + '</div><div class="cn-metric-n">' + fmtSo(n) + '</div>'
      + '<div class="cn-metric-d">' + esc(note) + '</div></div>';

    let h = '<div class="cn-ov"><div class="cn-col">'
      // Hero
      + '<section class="cn-hero"><span class="cn-eb">' + esc(tw("camnang.hero_eb")) + '</span>'
      + '<h2>' + esc(tw("camnang.hero_t")) + '</h2><p>' + esc(tw("camnang.hero_d")) + '</p>'
      + '<div class="cn-hero-act">'
      + '<button type="button" class="mp-btn primary" data-open-tab="phongban">'
      + esc(tw("camnang.hero_a1")) + '</button>'
      + '<button type="button" class="mp-btn" data-open-tab="fanpage">'
      + esc(tw("camnang.hero_a2")) + '</button></div></section>'
      // 4 thẻ số
      + '<div class="cn-metrics">'
      + metric(nSpec, tw("camnang.mt_skill"), tw("camnang.mt_skill_d"), true)
      + metric(depts.length, tw("camnang.mt_dept"), tw("camnang.mt_dept_d"), true)
      + metric(connected.length, tw("camnang.mt_conn"), tw("camnang.mt_conn_d"), false)
      + metric((brains || []).length, tw("camnang.mt_brain"), tw("camnang.mt_brain_d"), false)
      + '</div>'
      // Năng lực nổi bật
      + panel("sparkles", tw("camnang.cap_t"), tw("camnang.cap_d"),
          '<div class="cn-caps">'
          + theCap({ tab: "fanpage", con: fbCon, badge: stNoi("facebook-pages"),
                     t: tw("camnang.cap_fb_t"), d: tw("camnang.cap_fb_d"), l: tw("camnang.cap_fb_l") })
          + theCap({ tab: "zalo", con: zlCon, badge: stNoi("zalo"),
                     t: tw("camnang.cap_zl_t"), d: tw("camnang.cap_zl_d"), l: tw("camnang.cap_zl_l") })
          + theCap({ tab: "phongban", unit: "studio", icon: "puzzle",
                     badge: pill("spec", tw("camnang.pb_skills_n", { so: unitN("studio") })),
                     t: tw("camnang.cap_st_t"), d: tw("camnang.cap_st_d"), l: tw("camnang.cap_st_l") })
          + theCap({ tab: "phongban", unit: "academy", icon: "book-open",
                     badge: pill("spec", tw("camnang.pb_skills_n", { so: unitN("academy") })),
                     t: tw("camnang.cap_ac_t"), d: tw("camnang.cap_ac_d"), l: tw("camnang.cap_ac_l") })
          + '</div>')
      + '</div><aside class="cn-col">'
      + panel("rocket", tw("camnang.qs_t"), tw("camnang.qs_d"), '<div class="cn-qlist">' + nhanh + '</div>')
      + panel("chart-column", tw("camnang.brand_t"), tw("camnang.brand_d"),
          brand("studio", "camnang.brand_st_d") + brand("academy", "camnang.brand_ac_d")
          + brand("shared", "camnang.brand_sh_d"))
      + '</aside></div>';

    if (!connected.length && !agents.length) {
      h += '<div class="cn-empty">' + ic("book-open", { cls: "ic-xl" })
        + '<div class="cn-empty-t">' + esc(tw("camnang.empty_t")) + '</div>'
        + '<div class="cn-empty-d">' + esc(tw("camnang.empty_d")) + '</div>'
        + '<button type="button" class="mp-btn primary" data-goto="mcp">' + esc(tw("camnang.go_connect")) + '</button></div>';
    } else {
      if (connected.length) {
        h += '<div class="cn-sec">' + esc(tw("camnang.connected")) + '</div><div class="cn-grid">'
          + connected.map(c => theConnector(c, byCon[c.id], health)).join("") + '</div>';
      }
      h += theNhanSu(agents, workflows, skills);
      if (chuaNoi.length) {
        h += '<details class="cn-more"><summary>' + esc(tw("camnang.not_yet", { so: chuaNoi.length })) + '</summary>'
          + '<div class="cn-grid">' + chuaNoi.map(c =>
              '<div class="cn-mini cn-mini-off" data-conn="' + esc(c.id) + '"><div class="cn-mini-t">'
              + '<span class="cn-ico sm">' + iconInner(c) + '</span> <b>' + esc(c.name || c.id) + '</b></div>'
              + (c.description ? '<div class="cn-mini-d">' + esc(c.description) + '</div>' : "")
              + '</div>').join("") + '</div></details>';
      }
    }
    el.innerHTML = h;
    el.querySelectorAll(".cn-mini-off[data-conn]").forEach(b =>
      b.onclick = () => diTo("mcp"));
    ganChip(el);
  }

  // ============================================================
  async function render(el) {
    _rootEl = el;
    el.innerHTML = '<div class="cview-placeholder"><div class="ph-ico">'
      + ic("loader", { cls: "ic-xl ic-spin" }) + '</div><div>' + esc(tw("common.loading")) + '</div></div>';
    const b = encodeURIComponent(brain());
    let cat = [], conns = [], health = {}, agents = [], workflows = [], skills = [],
        brains = [], specCat = null;
    try {
      const rs = await Promise.all([
        api("/connect/catalog"), api("/connect/health"),
        api("/agents?brain=" + b + "&prompt=0"), api("/workflows?brain=" + b),
        api("/skills?brain=" + b), api("/brains"),
        api("/static/data/h2o-skill-catalog.json"),
      ]);
      cat = (rs[0].data && rs[0].data.catalog) || [];
      conns = (rs[0].data && rs[0].data.connections) || [];
      health = (rs[1].data && rs[1].data.health) || {};
      agents = (rs[2].data && rs[2].data.agents) || [];
      workflows = ((rs[3].data && rs[3].data.workflows) || []).filter(w => w.status === "active");
      skills = (rs[4].data && rs[4].data.skills) || [];
      brains = (rs[5].data && (rs[5].data.brains || rs[5].data.list)) || [];
      specCat = rs[6].data || null;
    } catch (e) {
      el.innerHTML = '<div class="cview-placeholder"><div class="ph-ico">'
        + ic("triangle-alert", { cls: "ic-xl" }) + '</div><div>' + esc(tw("cs.cn_load_err")) + '</div></div>';
      return;
    }

    const byCon = {};
    conns.filter(c => c.enabled !== false).forEach(c => {
      (byCon[c.connector_id || "custom"] = byCon[c.connector_id || "custom"] || []).push(c);
    });

    // Tab con giờ nằm trên rail (mục con của Cẩm nang): store.nav.goSub đặt
    // window.__cnSub trước khi renderPage gọi hàm này. Không còn thanh tab trong
    // trang - dòng ngữ cảnh nhỏ bên dưới cho biết đang đứng ở tab nào.
    const tabs = [{ id: "tongquan", icon: "chart-column", labelKey: "camnang.tab_tongquan" }]
      .concat(OPS_MODULES.filter(m => !m.conn || cat.some(c => c.id === m.conn)));
    const subCho = (typeof window !== "undefined" && window.__cnSub) || "";
    if (subCho) {
      CN_STATE.tab = subCho;
      try { window.__cnSub = null; } catch (e) {}
    }
    if (!tabs.some(x => x.id === CN_STATE.tab)) CN_STATE.tab = "tongquan";
    syncRailSub(CN_STATE.tab);

    const tabDang = tabs.find(x => x.id === CN_STATE.tab) || tabs[0];
    el.innerHTML = '<div class="cn-curtab">' + ic(tabDang.icon) + ' <b>'
      + esc(tw(tabDang.labelKey)) + '</b></div><div id="cnBody"></div>';

    const body = el.querySelector("#cnBody");
    const ctx = { cat, conns, byCon, health, agents, workflows, skills, brains, specCat };
    if (CN_STATE.tab === "tongquan") {
      renderTongQuan(body, ctx);
      return;
    }
    const mod = OPS_MODULES.find(m => m.id === CN_STATE.tab);
    if (!mod) { renderTongQuan(body, ctx); return; }
    mod.render(body, { con: cat.find(c => c.id === mod.conn) || {},
                       conns: byCon[mod.conn] || [], health, agents, workflows, skills,
                       brains, specCat }, mod);
  }

  window.JoyceCamNang = {
    render,
    // Mở đúng tab con (rail gọi khi bấm mục con của Cẩm nang, hoặc link trong trang).
    openSub(id) { chonTab(id); },
  };
})();
