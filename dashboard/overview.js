/* ============================================
   Nhóm TỔNG QUAN (Command Center) - spec V1.4 mục 53, mẫu
   tai-lieu-update-tu-openai/update-giao-dein-tong-quat/JOYCE_OVERVIEW_COMMAND_CENTER_V1.html.

   Bốn trang con: Bảng điều hành (command), Phòng ban (departments), Lịch & kế hoạch (calendar),
   Báo cáo (reports). Trang Hôm nay (today) giữ nguyên, do console.js vẽ.

   CHỈ ĐỌC, SỐ THẬT: dữ liệu từ /api/joyce/v1/overview* (server/joyce_overview.py). Bản mẫu dùng
   số giả; ở đây khối nào chưa có nguồn thì nói "chưa nối nguồn", không vẽ con số. Một nguồn
   lỗi chỉ làm khối đó báo lỗi, không làm trắng trang.

   Màu chỉ dùng token theme (--card, --line, --accent, --ok-ink...) để giao diện tối/sáng
   đều đọc được (tests/js/test_giao_dien_toi.js).
   ============================================ */
(function () {
  "use strict";

  const t = (k, p) => (window.t ? window.t(k, p) : k);
  const ic = (n, o) => (window.ic ? window.ic(n, o) : "");
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const so = (n) => {
    const v = Number(n);
    if (!isFinite(v)) return "-";
    try { return new Intl.NumberFormat((window.JoyceI18n && JoyceI18n.locale()) || "vi-VN").format(v); }
    catch (e) { return String(v); }
  };
  const pct = (r) => (r == null ? "" : Math.round(r * 100) + "%");
  function brain() {
    try { return (window.JoyceSessions && window.JoyceSessions.brain()) || "brain"; } catch (e) { return "brain"; }
  }
  async function api(url) {
    try {
      const r = await fetch(url, { credentials: "same-origin" });
      const d = await r.json().catch(() => null);
      return { ok: r.ok && !!d && d.ok !== false, status: r.status, data: d || {} };
    } catch (e) { return { ok: false, status: 0, data: {} }; }
  }
  function go(page) {
    try { const s = window.Alpine && window.Alpine.store("nav"); if (s && s.go) { s.go(page); return; } } catch (e) {}
  }
  function goSub(page, sub) {
    try { const s = window.Alpine && window.Alpine.store("nav"); if (s && s.goSub) { s.goSub(page, sub); return; } } catch (e) {}
    go(page);
  }
  // Điền sẵn câu hỏi vào ô chat, KHÔNG tự gửi (giống câu mẫu ở Cẩm nang).
  function hoiJoyce(cau) {
    go("chat");
    setTimeout(() => {
      const inp = document.getElementById("chatInput");
      if (!inp) return;
      inp.value = cau;
      try { inp.dispatchEvent(new Event("input", { bubbles: true })); inp.focus(); } catch (e) {}
    }, 80);
  }
  // Chuyển ô chọn brain sang brain phòng (cùng cách trang Nhân viên / Tệp tin làm).
  // TÁCH điều hướng ra khỏi đổi brain: nhiều chỗ cần đổi brain rồi nhảy sang trang KHÁC
  // (Bảng việc, Cộng sự, Không gian brain), không phải lúc nào cũng tới Tệp tin.
  function chonBrain(path, ten) {
    const sel = document.getElementById("graphSource");
    if (!sel || !path) return;
    if (path === "brain") {
      // Brain Default đã có sẵn option value="brain" - tạo option path: cho nó là sai.
      sel.value = "brain";
      try { localStorage.setItem("joyce.graphSource", "brain"); } catch (e) {}
      sel.dispatchEvent(new Event("change"));
      return;
    }
    const want = "path:" + path;
    if (![...sel.options].some((o) => o.value === want)) {
      const o = document.createElement("option");
      o.value = want; o.textContent = ten || path; o.dataset.brain = "1";
      o.dataset.brainName = String(path).split(/[\\/]/).pop();
      sel.appendChild(o);
    }
    sel.value = want;
    try { localStorage.setItem("joyce.graphSource", want); } catch (e) {}
    sel.dispatchEvent(new Event("change"));
  }
  function moBrain(path, ten) { chonBrain(path, ten); go("files"); }
  function gioCapNhat(ts) {
    try { return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); } catch (e) { return ""; }
  }
  const loading = () => `<div class="cview-placeholder"><div class="ph-ico">${ic("loader", { cls: "ic-xl ic-spin" })}</div><div>${esc(t("common.loading"))}</div></div>`;
  const loiTrang = (msg) => `<div class="ov-err">${ic("triangle-alert")} <span>${esc(msg)}</span></div>`;
  const pill = (tone, txt) => `<span class="ov-pill ${tone || ""}">${esc(txt)}</span>`;
  const STATUS_TONE = { good: "good", wait: "wait", risk: "risk", empty: "", nobrain: "", error: "risk" };
  const panel = (title, sub, body, action) => `<section class="ov-panel"><div class="ov-panel-head"><div><h3>${esc(title)}</h3>${sub ? `<p>${esc(sub)}</p>` : ""}</div>${action || ""}</div><div class="ov-panel-body">${body}</div></section>`;
  const linkBtn = (page, txt, attr) => `<button type="button" class="ov-link" ${attr || `data-go="${esc(page)}"`}>${esc(txt)} ${ic("chevron-right")}</button>`;
  function ganDieuHuong(el) {
    el.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => go(b.dataset.go)));
    el.querySelectorAll("[data-ask]").forEach((b) => (b.onclick = () => hoiJoyce(b.dataset.ask)));
    el.querySelectorAll("[data-task]").forEach((b) => (b.onclick = () => {
      if (window.JoyceKanbanShow && b.dataset.task) { go("kanban"); setTimeout(() => window.JoyceKanbanShow(b.dataset.task), 250); }
      else go(b.dataset.href || "kanban");
    }));
  }

  // ============================================================
  // BẢNG ĐIỀU HÀNH
  // ============================================================
  const KPI_KEY = { done24: "ov.k_done24", running: "ov.k_running", review: "ov.k_review",
    blocked: "ov.k_blocked", queue: "ov.k_queue", turns: "ov.k_turns" };
  const KPI_SRC = { kanban: "ov.src_kanban", usage: "ov.src_usage" };
  const DOMAIN = {
    work: ["ov.d_work", "ov.d_work_d", "square-kanban"], connectors: ["ov.d_conn", "ov.d_conn_d", "plug"],
    apps: ["ov.d_apps", "ov.d_apps_d", "rocket"], engines: ["ov.d_engines", "ov.d_engines_d", "cpu"],
    reminders: ["ov.d_rem", "ov.d_rem_d", "alarm-clock"], knowledge: ["ov.d_know", "ov.d_know_d", "brain"],
  };
  const SEV_BAR = { critical: "risk", high: "risk", medium: "wait", low: "teal" };
  const SEV_KEY = { critical: "ov.sev_critical", high: "ov.sev_high", medium: "ov.sev_medium", low: "ov.sev_low" };
  // Khoá viết TƯỜNG MINH, không ghép chuỗi tiền tố + biến: test_i18n.mjs dò từng khoá trong JS.
  const COL_KEY = { review: "ov.col_review", ready: "ov.col_ready", running: "ov.col_running" };
  const PS_KEY = { engine: "ov.ps_engine", h2o_app: "ov.ps_h2o_app", connector: "ov.ps_connector",
    kanban: "ov.ps_kanban", reminders: "ov.ps_reminders", inbox: "ov.ps_inbox" };
  const ATT_KEY = { review: "ov.att_review", blocked: "ov.att_blocked", alerts: "ov.att_alerts" };
  const MEM_KEY = { facts: "ov.mem_facts", wiki: "ov.mem_wiki", sources: "ov.mem_sources", skills: "ov.mem_skills",
    phong: "ov.mem_phong", brands: "ov.mem_brands" };
  const DOW_KEY = ["ov.dow_0", "ov.dow_1", "ov.dow_2", "ov.dow_3", "ov.dow_4", "ov.dow_5", "ov.dow_6"];
  const ST_KEY = { good: "ov.st_good", wait: "ov.st_wait", risk: "ov.st_risk", empty: "ov.st_empty",
    nobrain: "ov.st_nobrain", error: "ov.st_error" };

  function kpiMeta(k) {
    if (k.key === "review") return k.meta_n ? t("ov.km_stale", { so: k.meta_n }) : t("ov.km_review");
    if (k.key === "queue") return k.meta === "off" ? t("ov.km_orch_off") : t("ov.km_orch_on");
    if (k.key === "turns") return t("ov.km_tokens", { so: so(k.meta_n || 0) });
    if (k.key === "done24") return t("ov.km_done24");
    if (k.key === "blocked") return k.value ? t("ov.km_blocked") : t("ov.km_clean");
    return t("ov.km_running");
  }

  function domainRow(d) {
    const m = DOMAIN[d.key] || [d.key, "", "circle"];
    let cot1 = so(d.done), cot2 = so(d.open);
    let tien = "";
    if (d.ratio != null) {
      tien = `<div class="ov-prog"><div class="ov-prog-bar"><span style="width:${Math.max(2, Math.round(d.ratio * 100))}%"></span></div><div class="ov-prog-meta"><span>${esc(t(d.ratio_key === "done" ? "ov.r_done" : "ov.r_online"))}</span><span>${pct(d.ratio)}</span></div></div>`;
    } else if (d.key === "knowledge") {
      tien = `<span class="ov-dim">${esc(t("ov.facts_n", { so: so(d.meta_n || 0) }))}</span>`;
    } else if (d.key === "reminders") {
      tien = `<span class="ov-dim">${esc(d.risk ? t("ov.rem_nochannel") : t("ov.rem_ok"))}</span>`;
    }
    const risk = d.risk ? pill(d.key === "work" || d.key === "reminders" ? "wait" : "risk", so(d.risk)) : pill("good", "0");
    return `<tr><td><div class="ov-dmain"><span class="ov-dico">${ic(m[2])}</span><div><strong>${esc(t(m[0]))}</strong><span>${esc(t(m[1]))}</span></div></div></td>
      <td class="ov-num">${cot1}</td><td class="ov-num">${cot2}</td><td>${risk}</td><td>${tien}</td>
      <td><button type="button" class="ov-row-btn" data-go="${esc(d.href)}" title="${esc(t("ov.open"))}">${ic("chevron-right")}</button></td></tr>`;
  }

  function prioRow(p) {
    const nhan = p.status ? t(COL_KEY[p.status] || "ov.col_ready") : t(SEV_KEY[p.severity] || "ov.sev_low");
    const nut = p.task_id
      ? `<button type="button" class="ov-row-btn txt" data-task="${esc(p.task_id)}" data-href="${esc(p.href)}">${esc(t("ov.open"))}</button>`
      : `<button type="button" class="ov-row-btn txt" data-go="${esc(p.href)}">${esc(t("ov.open"))}</button>`;
    return `<article class="ov-prio"><i class="ov-bar ${SEV_BAR[p.severity] || "teal"}"></i>
      <div class="ov-prio-t"><strong>${esc(p.title)}</strong><span>${esc(p.meta || "")}</span></div>
      <div class="ov-prio-src">${esc(t(PS_KEY[p.source] || "ov.ps_kanban"))}<small>${esc(p.age || "")}</small></div>
      ${pill(SEV_BAR[p.severity] === "teal" ? "" : SEV_BAR[p.severity], nhan)}${nut}</article>`;
  }

  function unitCard(u) {
    const tk = u.tasks || {};
    const rows = (u.top || []).map((r) => {
      const c = r.tasks || {};
      return `<div class="ov-deptrow"><strong>${esc(r.ten)}</strong><span>${c.open != null ? esc(t("ov.open_n", { so: c.open })) : esc(t(ST_KEY[r.status] || "ov.st_empty"))}</span>${pill(STATUS_TONE[r.status], t(ST_KEY[r.status] || "ov.st_empty"))}</div>`;
    }).join("");
    return `<article class="ov-unit"><div class="ov-unit-head"><h3>${esc(u.ten)}</h3>${pill(STATUS_TONE[u.status], t(ST_KEY[u.status]))}</div>
      <p>${esc(t("ov.unit_line", { phong: u.phong, dulieu: u.co_du_lieu, xong: tk.done24 || 0, mo: tk.open || 0, ket: tk.blocked || 0 }))}</p>
      <div class="ov-deptrows">${rows}</div></article>`;
  }

  function sysRow(s) {
    let ten, meta;
    if (s.key === "engine") { ten = t("ov.sys_engine", { ten: s.name }); meta = s.meta || t("ov.sys_engine_ok"); }
    else if (s.key === "connectors") { ten = t("ov.sys_conn"); meta = t("ov.sys_n_online", { ok: s.n_ok, n: s.n }); }
    else if (s.key === "apps") { ten = t("ov.sys_apps"); meta = t("ov.sys_n_online", { ok: s.n_ok, n: s.n }); }
    else if (s.key === "kanban") { ten = t("ov.sys_kanban"); meta = s.meta === "off" ? t("ov.km_orch_off") : t("ov.km_orch_on"); }
    else { ten = t("ov.sys_rem"); meta = s.meta || t("ov.rem_ok"); }
    return `<button type="button" class="ov-hrow" data-go="${esc(s.href)}"><div><strong>${esc(ten)}</strong><span>${esc(meta)}</span></div><span class="ov-htag ${s.ok ? "" : "warn"}">${esc(t(s.ok ? "ov.h_ok" : "ov.h_warn"))}</span></button>`;
  }

  async function renderCommand(el) {
    el.innerHTML = loading();
    const r = await api("/api/joyce/v1/overview?brain=" + encodeURIComponent(brain()));
    if (!el.isConnected) return;
    if (!r.ok) {
      el.innerHTML = `<div class="ov-page">${loiTrang(r.status === 403 ? t("ov.staff_denied") : t("ov.err_load"))}</div>`;
      return;
    }
    const d = r.data;
    const att = (d.attention || []).map((a) =>
      `<span class="ov-att"><i class="ov-dot ${a.tone}"></i><b>${so(a.n)}</b> ${esc(t(ATT_KEY[a.key] || "ov.att_alerts"))}</span>`).join("");
    const kpis = (d.kpis || []).map((k) => {
      const arrow = k.tone === "good" ? `<span class="ov-kpi-trend good">${ic("trending-up")}</span>`
        : k.tone === "bad" ? `<span class="ov-kpi-trend bad">${ic("trending-down")}</span>`
        : k.tone === "warn" ? `<span class="ov-kpi-trend warn">${ic("minus")}</span>` : "";
      return `<article class="ov-kpi"><div class="ov-kpi-top"><span>${esc(t(KPI_KEY[k.key] || k.key))}</span><span>${esc(t(KPI_SRC[k.source] || k.source))}</span></div>
       <div class="ov-kpi-v">${so(k.value)}${arrow}</div><div class="ov-kpi-m ${k.tone || ""}">${esc(kpiMeta(k))}</div></article>`;
    }).join("");
    const prio = (d.priority || []).length ? (d.priority || []).map(prioRow).join("")
      : `<div class="ov-empty">${ic("circle-check")} ${esc(t("ov.prio_empty"))}</div>`;
    const domains = `<table class="ov-dtable"><thead><tr><th>${esc(t("ov.th_domain"))}</th><th>${esc(t("ov.th_done"))}</th><th>${esc(t("ov.th_total"))}</th><th>${esc(t("ov.th_risk"))}</th><th>${esc(t("ov.th_progress"))}</th><th></th></tr></thead><tbody>${(d.domains || []).map(domainRow).join("")}</tbody></table>
      <div class="ov-biz">${ic("plug")}<div><b>${esc(t("ov.biz_title"))}</b><span>${esc((d.business_sources || []).map((b) => b.name).join(" · "))}</span></div>${linkBtn("mcp", t("ov.biz_go"))}</div>`;
    const units = (d.units || []).length ? `<div class="ov-units">${d.units.map(unitCard).join("")}</div>`
      : `<div class="ov-empty">${esc(t("ov.units_empty"))} ${linkBtn("staff", t("ov.units_go"))}</div>`;
    const sched = (d.schedule || []).length ? `<div class="ov-timeline">${d.schedule.map((s) =>
      `<div class="ov-ti"><time>${esc(s.time)}</time><span class="ov-rail"></span><div><strong>${esc(s.title)}</strong><span>${esc([s.label, s.brain].filter(Boolean).join(" · "))}</span></div></div>`).join("")}</div>`
      : `<div class="ov-empty">${esc(t("ov.sched_empty"))}</div>`;
    const m = d.memory || {};
    const mem = `<div class="ov-mem">${[["facts", m.facts], ["wiki", m.wiki], ["sources", m.sources], ["skills", m.skills], ["phong", m.phong], ["brands", m.brands]]
      .map(([k, v]) => `<div><strong>${so(v || 0)}</strong><span>${esc(t(MEM_KEY[k]))}</span></div>`).join("")}</div>`;
    const act = (d.activity || []).length ? `<div class="ov-acts">${d.activity.map((a) =>
      `<div class="ov-act"><span class="ov-act-i">${ic(a.kind === "task_done" ? "circle-check" : a.kind === "reminder" ? "alarm-clock" : "inbox")}</span><div><strong>${esc(a.title)}</strong><span>${esc(a.label || t(a.kind === "task_done" ? "ov.act_task" : "ov.act_inbox"))}</span></div><time>${esc(a.age)}</time></div>`).join("")}</div>`
      : `<div class="ov-empty">${esc(t("ov.act_empty"))}</div>`;

    el.innerHTML = `<div class="ov-page">
      <div class="ov-toolbar"><span class="ov-synced">${esc(t("ov.synced", { gio: gioCapNhat(d.generated_at) }))}</span>
        ${d.partial ? `<span class="ov-partial">${ic("triangle-alert")} ${esc(t("ov.partial", { ds: (d.sections_down || []).join(", ") }))}</span>` : ""}
        <button type="button" class="ov-refresh" id="ovRefresh">${ic("rotate-cw")} ${esc(t("ov.refresh"))}</button></div>
      <section class="ov-brief"><div class="ov-brief-t"><span class="ov-eyebrow">${esc(t("ov.brief_eyebrow", { thu: d.weekday || "", ngay: d.date || "" }))}</span>
        <h2 id="ovBriefTitle">${esc((d.brief || {}).title || "")}</h2><p id="ovBriefText">${esc((d.brief || {}).text || "")}</p><div class="ov-atts">${att}</div></div>
        <div class="ov-brief-a"><button type="button" class="ov-primary" data-go="kanban">${esc(t("ov.btn_priority"))}</button><button type="button" class="ov-secondary" data-go="today">${esc(t("ov.btn_today"))}</button></div></section>
      <div class="ov-kpis">${kpis}</div>
      <div class="ov-dash"><div class="ov-stack">
        ${panel(t("ov.p_prio"), t("ov.p_prio_d"), `<div class="ov-prios">${prio}</div>`, linkBtn("kanban", t("ov.go_work")))}
        ${panel(t("ov.p_domains"), t("ov.p_domains_d"), domains)}
        ${panel(t("ov.p_units"), t("ov.p_units_d"), units, linkBtn("departments", t("ov.go_all")))}
      </div><aside class="ov-stack ov-right">
        ${panel(t("ov.p_sched"), t("ov.p_sched_d", { so: (d.schedule || []).length }), sched, linkBtn("calendar", t("ov.go_cal")))}
        ${panel(t("ov.p_sys"), t("ov.p_sys_d"), `<div class="ov-hlist">${(d.system || []).map(sysRow).join("")}</div>`)}
        ${panel(t("ov.p_mem"), t("ov.p_mem_d"), mem, linkBtn("home", t("ov.go_brain")))}
        ${panel(t("ov.p_act"), t("ov.p_act_d"), act)}
      </aside></div></div>`;
    ganDieuHuong(el);
    el.querySelector("#ovRefresh").onclick = () => renderCommand(el);
    // Câu brief viết bằng model phụ - về sau, có thì thay câu tính sẵn (giống trang Hôm nay).
    api("/api/joyce/v1/brief-ai?brain=" + encodeURIComponent(brain())).then((b) => {
      if (!el.isConnected || !b.ok || !b.data || b.data.fallback || typeof b.data.brief !== "string") return;
      const p = el.querySelector("#ovBriefText");
      if (p) p.textContent = b.data.brief;
    });
  }

  // ============================================================
  // PHÒNG BAN VẬN HÀNH - sơ đồ khối nối theo luồng việc
  // ============================================================
  let _deptBrand = "all";
  // Luồng doanh thu của studio theo hành trình khách: Nghiên Cứu ra concept -> Marketing
  // mang khách về -> Bán Hàng chốt -> CSKH đi cùng -> Sản Xuất làm -> Kế Toán chốt tiền.
  // Khối không nằm trong danh sách này là khối HỖ TRỢ (nhân sự, vệ sinh, truyền thông...).
  // Thứ tự luồng ĐẾN TỪ SỔ PHÒNG BAN (khoi.thu_tu_luong / khoi.trai_dai), không hardcode ở
  // đây nữa - cơ cấu phòng ban là dữ liệu, đổi nó không nên phải sửa JavaScript. Danh sách
  // dưới chỉ còn là lưới cứu khi server cũ chưa trả trường đó.
  const FLOW_FALLBACK = ["nghien-cuu", "marketing", "ban-hang", "san-xuat"];
  const DOT_C = { good: "var(--ok-ink)", wait: "var(--warn-ink)", risk: "var(--danger-ink)",
    error: "var(--danger-ink)", empty: "var(--text3)", nobrain: "var(--text3)" };

  function phongChip(p) {
    const c = p.tasks || {};
    return `<button type="button" class="ovw-phong" data-dept="${esc(p.id)}">
      <i class="ov-dot" style="background:${DOT_C[p.status] || "var(--text3)"}"></i>
      <span class="ovw-pmain"><b>${esc(p.ten)}</b><small>${esc(p.agent || t("ov.dw_no_agent"))}</small></span>
      ${c.open ? `<span class="ovw-n">${so(c.open)}</span>` : ""}
      ${c.blocked ? `<span class="ovw-n risk">${so(c.blocked)}</span>` : ""}
    </button>`;
  }

  function khoiCard(khoi, phongs, num) {
    const mo = phongs.reduce((s, p) => s + ((p.tasks || {}).open || 0), 0);
    const ket = phongs.reduce((s, p) => s + ((p.tasks || {}).blocked || 0), 0);
    return `<div class="ovw-khoi">
      <div class="ovw-khead"><span class="ovw-knum">${esc(num)}</span>
        <div class="ovw-kname"><b>${esc(khoi.ten)}</b><span>${esc(t("ov.dw_rooms", { so: phongs.length }))}</span></div>
        ${mo ? `<span class="ovw-n" title="${esc(t("ov.ds_open"))}">${so(mo)}</span>` : ""}
        ${ket ? `<span class="ovw-n risk" title="${esc(t("ov.ds_blocked"))}">${so(ket)}</span>` : ""}
      </div>
      <div class="ovw-kbody">${phongs.map(phongChip).join("")}</div>
    </div>`;
  }

  async function renderDepartments(el) {
    el.innerHTML = loading();
    const r = await api("/api/joyce/v1/overview/departments");
    if (!el.isConnected) return;
    if (!r.ok) { el.innerHTML = `<div class="ov-page">${loiTrang(r.status === 403 ? t("ov.staff_denied") : t("ov.err_load"))}</div>`; return; }
    const d = r.data, units = d.units || [], phong = d.phong || [], khois = d.khois || [];
    if (!phong.length) {
      el.innerHTML = `<div class="ov-page"><div class="ov-empty big">${esc(t("ov.units_empty"))} ${linkBtn("staff", t("ov.units_go"))}</div></div>`;
      ganDieuHuong(el);
      return;
    }
    if (_deptBrand !== "all" && !units.some((u) => u.id === _deptBrand)) _deptBrand = "all";
    const khoiMap = Object.fromEntries(khois.map((k) => [k.id, k]));

    // Gom phòng theo khối, rồi chia ba vai: CHUỖI chính (thu_tu_luong > 0), khối TRẢI DÀI
    // chạy dọc cả hành trình (trai_dai), và khối hỗ trợ còn lại.
    const byKhoi = {};
    phong.filter((p) => _deptBrand === "all" || p.brand_id === _deptBrand)
      .forEach((p) => { (byKhoi[p.khoi_id] = byKhoi[p.khoi_id] || []).push(p); });
    const ids = Object.keys(byKhoi);
    const bac = (id) => Number(khoiMap[id]?.thu_tu_luong || 0);
    const traiDai = (id) => !!khoiMap[id]?.trai_dai;
    let flowIds = ids.filter((id) => bac(id) > 0 && !traiDai(id)).sort((a, b) => bac(a) - bac(b));
    if (!flowIds.length) flowIds = FLOW_FALLBACK.filter((id) => byKhoi[id] && !traiDai(id));
    const spanIds = ids.filter(traiDai)
      .sort((a, b) => bac(a) - bac(b) || String(khoiMap[a]?.ten || a).localeCompare(String(khoiMap[b]?.ten || b)));
    const supIds = ids.filter((id) => !flowIds.includes(id) && !spanIds.includes(id))
      .sort((a, b) => String(khoiMap[a]?.ten || a).localeCompare(String(khoiMap[b]?.ten || b)));
    // Brand nào không có khối luồng nào (vd ThuyH2O) thì khối của nó vẫn nằm ở phần chính.
    const mainIds = flowIds.length ? flowIds : supIds;
    const restIds = flowIds.length ? supIds : [];

    // Mũi tên MANG SỐ: việc đang đọng ở khối NHẬN (kẹt + chờ duyệt + đang mở). Mũi tên trơn
    // chỉ là trang trí - nó không nói được chỗ nào đang tắc, mà đó mới là câu người ta mở
    // trang vận hành để hỏi.
    const un = (id) => Number(khoiMap[id]?.un || 0);
    const ket = (id) => Number((khoiMap[id]?.tasks || {}).blocked || 0);
    const noi = (idSau) => {
      const n = un(idSau), k = ket(idSau);
      return `<div class="ovw-arrow${k ? " risk" : ""}" title="${esc(t("ov.dw_arrow_t", { khoi: khoiMap[idSau]?.ten || idSau }))}">
        ${ic("chevron-right")}${n ? `<span class="ovw-an${k ? " risk" : ""}">${so(n)}</span>` : ""}</div>`;
    };
    const flowHtml = mainIds.map((id, i) =>
      khoiCard(khoiMap[id] || { ten: id }, byKhoi[id], String(i + 1).padStart(2, "0"))
    ).reduce((acc, card, i) => acc + (i ? noi(mainIds[i]) : "") + card, "");

    // Khối trải dài: một dải NẰM NGANG dưới chuỗi, đúng với việc nó chạm vào mọi chặng.
    // CSKH có Trước/Trong/Sau Dịch Vụ, Kế Toán thì Phòng Thu ở đầu còn Đối Soát ở cuối -
    // vẽ chúng thành một mắt xích giữa chuỗi là mô tả sai cơ cấu.
    const spanHtml = spanIds.map((id) => {
      const k = khoiMap[id] || { ten: id };
      const ps = byKhoi[id];
      return `<div class="ovw-span${ket(id) ? " risk" : ""}">
        <div class="ovw-span-h"><b>${esc(k.ten)}</b>
          <span>${esc(t("ov.dw_span_d", { so: ps.length }))}</span>
          ${un(id) ? `<span class="ovw-n${ket(id) ? " risk" : ""}">${so(un(id))}</span>` : ""}</div>
        <div class="ovw-span-b">${ps.map(phongChip).join("")}</div>
      </div>`;
    }).join("");

    const supHtml = restIds.length
      ? panel(t("ov.dw_support"), t("ov.dw_support_d"),
          `<div class="ovw-supp">${restIds.map((id) =>
            khoiCard(khoiMap[id] || { ten: id }, byKhoi[id], "")).join("")}</div>`)
      : "";

    const tabs = [["all", t("ov.all_units")]].concat(units.map((u) => [u.id, u.ten]));
    el.innerHTML = `<div class="ov-page">
      <div class="ov-toolbar"><div class="ov-chips">${tabs.map(([id, ten]) => `<button type="button" class="ov-chip" data-brand="${esc(id)}" aria-pressed="${id === _deptBrand}">${esc(ten)}</button>`).join("")}</div>
        <button type="button" class="ov-chip" id="ovCeoWs" title="${esc(t("ov.ws_ceo_d"))}">${ic("brain")} ${esc(t("ov.ws_ceo"))}</button>
        <span class="ov-synced">${esc(t("ov.synced", { gio: gioCapNhat(d.generated_at) }))}</span></div>
      <div class="ov-unitsum">${units.filter((u) => _deptBrand === "all" || u.id === _deptBrand).map((u, i) => {
        const tk = u.tasks || {};
        return `<div class="ov-usum" data-unit="${i}"><div class="ov-usum-ico">${ic("layers")}</div><div class="ov-usum-body"><b>${esc(u.ten)}</b>${pill(STATUS_TONE[u.status], t(ST_KEY[u.status]))}<span>${esc(t("ov.unit_line", { phong: u.phong, dulieu: u.co_du_lieu, xong: tk.done24 || 0, mo: tk.open || 0, ket: tk.blocked || 0 }))}</span>
        <div class="ov-usum-nums"><span><strong>${so(tk.done24 || 0)}</strong> ${esc(t("ov.ds_done"))}</span><span><strong>${so(tk.open || 0)}</strong> ${esc(t("ov.ds_open"))}</span><span><strong>${so(tk.blocked || 0)}</strong> ${esc(t("ov.ds_blocked"))}</span></div></div></div>`;
      }).join("")}</div>
      ${panel(t("ov.dw_flow"), t("ov.dw_flow_d"),
        `<div class="ovw-flow">${flowHtml}</div>`
        + (spanHtml ? `<div class="ovw-spans"><span class="ovw-spans-l">${esc(t("ov.dw_span_l"))}</span>${spanHtml}</div>` : ""))}
      ${supHtml}
      <p class="ov-dim" style="margin:0">${ic("info")} ${esc(t("ov.dw_hint"))}</p></div>`;
    el.querySelectorAll("[data-brand]").forEach((b) => (b.onclick = () => { _deptBrand = b.dataset.brand; renderDepartments(el); }));
    const nutCeo = el.querySelector("#ovCeoWs");
    // "Không gian CEO" = cùng một màn moBrainWs nhưng cho Brain Default (não tổng):
    // CEO xem đội hình/việc/loop/ý tưởng toàn công ty mà không lạc vào cây thư mục.
    if (nutCeo) nutCeo.onclick = () => moBrainWs({ id: "ceo", ten: "Brain Default", khoi: "CEO", khoi_id: "", brand: "", brain: "brain", brain_path: "brain", has_brain: true, tasks: {}, status: "", nguon: null, wiki: null, vai: "", nhiem_vu: [] }, khoiMap);
    el.querySelectorAll("[data-dept]").forEach((b) => (b.onclick = () => moWorkspace(phong.find((p) => p.id === b.dataset.dept), khoiMap)));
    ganDieuHuong(el);
  }

  // ---- Không gian brain: phần thân dùng chung --------------------------------------
  // Các khoảng "không gian brain" (hiện trạng, ý tưởng, đội hình, việc, loop, kho tri
  // thức) xuất hiện ở HAI nơi: trong drawer phòng (moWorkspace - trưởng phòng mở phòng
  // là thấy luôn) và trong overlay riêng (moBrainWs - nút "Không gian CEO" cho Brain
  // Default). Markup + nạp dữ liệu gom chung ở đây để hai nơi giống hệt nhau.
  const wsStatHtml = () => `<div class="ov-dmetric" id="ovwWsStat">${ic("loader", { cls: "ic-spin" })}</div>`;
  const wsIdeaHtml = () => `<section class="ovw-sec"><h4>${ic("lightbulb")} ${esc(t("ov.ws_idea"))}</h4>
      <p class="ov-dim ovw-sec-d">${esc(t("ov.ws_idea_d"))}</p>
      <div class="ovw-ichips">${["ov.ws_idea_c1", "ov.ws_idea_c2", "ov.ws_idea_c3"].map((kk) => `<button type="button" class="ov-chip" data-idea="${esc(kk)}">${esc(t(kk))}</button>`).join("")}</div>
      <textarea id="ovwIdea" rows="2" placeholder="${esc(t("ov.ws_idea_ph"))}"></textarea>
      <div class="ovw-assign-row">
        <button type="button" class="ov-primary" id="ovwIdeaGo">${ic("send")} ${esc(t("ov.ws_idea_go"))}</button>
        <span class="ov-dim" id="ovwIdeaMsg"></span>
      </div></section>`;
  const wsInfoHtml = () => `<section class="ovw-sec"><h4>${ic("users")} ${esc(t("ov.ws_team"))}</h4><div id="ovwWsTeam">${ic("loader", { cls: "ic-spin" })}</div></section>
      <section class="ovw-sec"><h4>${ic("square-kanban")} ${esc(t("ov.ws_tasks"))}</h4><div id="ovwWsTasks">${ic("loader", { cls: "ic-spin" })}</div></section>
      <section class="ovw-sec"><h4>${ic("repeat")} ${esc(t("ov.ws_loops"))}</h4><div id="ovwWsLoops">${ic("loader", { cls: "ic-spin" })}</div></section>
      <section class="ovw-sec"><h4>${ic("brain")} ${esc(t("ov.ws_know"))}</h4><div id="ovwWsKnow">${ic("loader", { cls: "ic-spin" })}</div></section>`;

  // Nạp + nối dây cho các khoảng không gian brain bên trong container `w`.
  // opts.teamFull: true = hiện cả chip workflow/kỹ năng (overlay CEO); false = chỉ
  // hàng agent có nút giao việc 1-1 (drawer phòng - wf/skill đã có ở cột Trong).
  // opts.statsExtra: ô số thêm vào dải hiện trạng (drawer thêm "nhân viên").
  // opts.dongHet: đóng sạch mọi lớp phủ trước khi nhảy trang (bảng việc, kênh agent...).
  function napWs(w, p, opts) {
    const o = opts || {};
    const bparam = p.brain || "brain";
    const eb = encodeURIComponent(bparam);
    const brainSel = p.brain_path || "brain";
    const dongHet = o.dongHet || function () {};
    const moTask = (id) => {
      dongHet(); chonBrain(brainSel, p.ten); go("kanban");
      if (id) setTimeout(() => { try { if (window.JoyceKanbanShow) window.JoyceKanbanShow(id); } catch (e) {} }, 250);
    };
    const denLoops = () => { dongHet(); chonBrain(brainSel, p.ten); setTimeout(() => go("selfimprove"), 60); };

    // Thu gọn nhóm (data-grp/data-grp-h): drawer phòng đã gắn ở moWorkspace, overlay
    // "Không gian CEO" thì chưa - gắn ở đây một lần. Cờ __grpBound tránh toggle 2 lần.
    const grpThu = window.__ovGrpThu || (window.__ovGrpThu = new Set());
    const grpKhoa = (kk) => String(p.brain || p.ten || "") + "|" + kk;
    if (!w.__grpBound) {
      w.__grpBound = true;
      w.addEventListener("click", (e) => {
        const h = e.target.closest("[data-grp-h]");
        if (!h || !w.contains(h)) return;
        const grp = h.closest("[data-grp]");
        if (!grp) return;
        const on = grp.classList.toggle("collapsed");
        const kk = grpKhoa(grp.dataset.grp);
        if (on) grpThu.add(kk); else grpThu.delete(kk);
      });
    }

    // Hiện trạng + bảng việc: một GET /kanban cho cả hai.
    api("/kanban?brain=" + eb).then((r) => {
      if (!w.isConnected) return;
      const stat = w.querySelector("#ovwWsStat"), tk = w.querySelector("#ovwWsTasks");
      const mode = w.querySelector("#ovwWsMode");
      if (!r.ok) { if (stat) stat.innerHTML = `<span class="ov-dim">${esc(t("ov.dw_cap_err"))}</span>`; if (tk) tk.innerHTML = ""; return; }
      const d = r.data || {}, cnt = d.counts || {}, cols = d.columns || {};
      const ORCH = { off: "ov.ws_orch_off", manual: "ov.ws_orch_manual", auto: "ov.ws_orch_auto" };
      const orchTxt = t(ORCH[d.orchestration] || "ov.ws_orch_off");
      if (mode) mode.textContent = orchTxt;
      const queue = (cnt.triage || 0) + (cnt.todo || 0) + (cnt.ready || 0);
      const cells = [["ov.ws_orch", orchTxt], ["ov.ws_col_queue", queue], ["ov.ws_col_running", cnt.running || 0],
        ["ov.ds_review", cnt.review || 0], ["ov.ds_blocked", cnt.blocked || 0], ["ov.ds_done", d.completed_24h || 0]]
        .concat((o.statsExtra || []).filter(([, v]) => v != null));
      if (stat) stat.innerHTML = cells
        .map(([kk, v]) => `<div><strong>${esc(String(v))}</strong><span>${esc(t(kk))}</span></div>`).join("");
      if (!tk) return;
      const li = (x) => `<button type="button" class="ovw-task" data-tid="${esc(x.id || "")}"><span>${esc(x.title || "")}</span>${x.needs_approval ? `<i>${ic("circle-check")}</i>` : ""}</button>`;
      const grp = (nhan, arr, cls) => arr.length ? `<div class="ovw-tgrp ${cls}"><b>${esc(nhan)} · ${arr.length}</b>${arr.slice(0, 6).map(li).join("")}${arr.length > 6 ? `<span class="ov-dim">+${arr.length - 6}</span>` : ""}</div>` : "";
      const q = (cols.triage || []).concat(cols.todo || [], cols.ready || []);
      const html = grp(t("ov.ws_col_running"), cols.running || [], "run")
        + grp(t("ov.ws_col_queue"), q, "wait") + grp(t("ov.ws_col_review"), cols.review || [], "rev")
        + grp(t("ov.ws_col_blocked"), cols.blocked || [], "blk");
      tk.innerHTML = html || `<p class="ov-dim">${esc(t("ov.ws_no_tasks"))}</p>`;
      tk.querySelectorAll("[data-tid]").forEach((b) => (b.onclick = () => moTask(b.dataset.tid)));
    });

    // Đội hình: agent (giao việc 1-1 qua kênh agent:<slug>) + workflow + kỹ năng.
    // Workflow còn đổ vào ô "Chạy qua" của form giao việc -> route wf:<slug>.
    Promise.all([api("/agents?brain=" + eb + "&prompt=0"), api("/workflows?brain=" + eb), api("/skills?brain=" + eb)])
      .then((rs) => {
        if (!w.isConnected) return;
        const team = w.querySelector("#ovwWsTeam");
        const ag = (rs[0].data && rs[0].data.agents) || [];
        const wf = (rs[1].data && rs[1].data.workflows) || [];
        const sk = (rs[2].data && rs[2].data.skills) || [];
        if (team) {
          const chip = (rel, ten) => `<button type="button" class="ovw-cap ovw-cap-lk" data-file="${esc(rel)}" title="${esc(rel)}">${esc(ten)}</button>`;
          const capLine = (nhan, arr, mk) => arr.length ? `<div class="ovw-capline"><span class="ov-dim">${esc(nhan)}</span>${arr.slice(0, 10).map(mk).join("")}${arr.length > 10 ? `<span class="ov-dim">+${arr.length - 10}</span>` : ""}</div>` : "";
          team.innerHTML =
            (ag.length ? `<div class="ovw-agents">${ag.map((a) => `<div class="ovw-agent">
                <span class="ovw-agent-n"><b>${esc(a.name || a.slug)}</b>${a.role ? `<i>${esc(a.role)}</i>` : ""}</span>
                <button type="button" class="ovw-icbtn" data-file="agents/${esc(a.slug)}.md" title="${esc(t("ov.ws_agent_file"))}">${ic("pen-line")}</button>
                <button type="button" class="ovw-icbtn ovw-agent-ask" data-slug="${esc(a.slug)}" title="${esc(t("ov.ws_agent_ask"))}">${ic("send")}</button>
              </div>`).join("")}</div>` : "")
            + (o.teamFull === false ? "" :
              capLine(t("ov.dw_workflows"), wf, (x) => chip("workflows/" + x.slug + ".md", x.name || x.slug))
              + capLine(t("ov.dw_skills"), sk, (x) => chip((x.enabled === false ? "skills/.disabled/" : "skills/") + x.slug + "/SKILL.md", x.name || x.slug)))
            || `<span class="ov-dim">${esc(t("ov.dw_cap_empty"))}</span>`;
          team.querySelectorAll("[data-file]").forEach((b) => (b.onclick = () => {
            if (window.JoyceFileEditor) window.JoyceFileEditor.open(b.dataset.file, { brain: brainSel });
          }));
          team.querySelectorAll(".ovw-agent-ask").forEach((b) => (b.onclick = () => {
            const slug = b.dataset.slug;
            dongHet(); chonBrain(brainSel, p.ten);
            // Kênh agent:<slug> trên trang Cộng sự = đường giao việc 1-1 với đúng agent đó.
            setTimeout(() => { try { if (window.JoyceWorkspace) window.JoyceWorkspace.openCommand("agent", slug); } catch (e) {} }, 120);
          }));
        }
        const sel = w.querySelector("#ovwWsARoute");
        if (sel) wf.forEach((x) => { const o2 = document.createElement("option"); o2.value = "wf:" + x.slug; o2.textContent = x.name || x.slug; sel.appendChild(o2); });
      }).catch(() => { const tm = w.querySelector("#ovwWsTeam"); if (tm) tm.innerHTML = `<span class="ov-dim">${esc(t("ov.dw_cap_err"))}</span>`; });

    // Vòng lặp riêng của brain phòng: file Joyce/loops/<slug>.md trong vault đó.
    api("/loops?brain=" + eb).then((r) => {
      if (!w.isConnected) return;
      const box = w.querySelector("#ovwWsLoops");
      if (!box) return;
      const loops = (r.data && r.data.loops) || [];
      if (!loops.length) { box.innerHTML = `<p class="ov-dim">${esc(t("ov.ws_no_loops"))}</p>`; return; }
      box.innerHTML = loops.map((l) => `<div class="ovw-loop">
          <span class="ovw-loop-s ${l.enabled ? "on" : "off"}">${ic(l.enabled ? "repeat" : "minus")}</span>
          <span class="ovw-loop-n"><b>${esc(l.name || l.slug)}</b><i>${esc(window.fmtInterval ? window.fmtInterval(l.interval_min || 0) : t("ov.ws_loop_min", { n: l.interval_min || 0 }))}${l.run_at ? " " + esc(l.run_at) : ""}${l.enabled ? "" : " · " + esc(t("ov.ws_loop_off"))}${l.auto_paused_reason ? " · " + esc(l.auto_paused_reason) : ""}</i></span>
          <span class="ovw-loop-r">${l.last_status ? esc(l.last_status) : ""}${l.fail_streak ? ` · ${esc(t("ov.ws_loop_fail", { n: l.fail_streak }))}` : ""}${l.next_run ? ` · ${esc(gioCapNhat(l.next_run))}` : ""}</span>
        </div>`).join("")
        + `<button type="button" class="ov-link" data-ws="loops">${esc(t("ov.ws_loops_go"))} ${ic("chevron-right")}</button>`;
      const go2 = box.querySelector("[data-ws]"); if (go2) go2.onclick = denLoops;
    });

    // Kho tri thức phòng: một GET gom nguồn/wiki/kênh/hay-mở thay vì N request. Trưởng
    // phòng đọc theo NGHĨA vận hành (đã nạp / đang dùng / hay mở / từ kênh chat), mỗi mục
    // bấm mở thẳng file - không phải đi đọc cây thư mục sources/wiki/memory.
    const KENH = { telegram: "Telegram", zalo: "Zalo", khach: t("ov.ws_know_kenh_khach") };
    const taiKnow = () => {
      api("/api/joyce/v1/overview/knowledge?brain=" + encodeURIComponent(brainSel)).then((r) => {
        if (!w.isConnected) return;
        const box = w.querySelector("#ovwWsKnow");
        if (!box) return;
        const d = (r.data && r.data.ok !== false) ? r.data : null;
        if (!d) { box.innerHTML = `<span class="ov-dim">${esc(t("ov.dw_cap_err"))}</span>`; return; }
        const c = d.counts || {};
        const fmtD = (ms) => { const x = new Date(ms * 1000); return String(x.getDate()).padStart(2, "0") + "/" + String(x.getMonth() + 1).padStart(2, "0"); };
        const moFile = (rel) => { if (window.JoyceFileEditor) window.JoyceFileEditor.open(rel, { brain: brainSel }); };
        const dong = (it, meta) => `<div class="ovw-kitem" data-rel="${esc(it.doc || it.rel)}" title="${esc(it.rel)}">`
          // Ngày chỉ hiện khi có mtime thật: mục xếp hạng "hay mở" không mang ngày, và trước đây
          // nó rơi về 0 nên hiện "01/01" ở mọi dòng.
          + `<span class="ovw-kname">${esc(it.ten)}</span><span class="ovw-kmeta">${meta}${it.mtime ? `<span class="ovw-kdate">${fmtD(it.mtime)}</span>` : ""}</span></div>`;
        // Nhóm luôn hiện kể cả khi rỗng (inner rỗng -> câu trống) - trưởng phòng thấy
        // cấu trúc đủ 4 mục, biết kênh nào CHƯA có dữ liệu thay vì mục đó biến mất.
        const grp = (khoa, icon, nhan, n, inner) =>
          `<div class="ovw-capgrp${grpThu.has(grpKhoa(khoa)) ? " collapsed" : ""}" data-grp="${khoa}"><span data-grp-h>${ic(icon)} ${esc(nhan)} <b>${n}</b>${ic("chevron-down")}</span><div>${inner || `<div class="ovw-ksub">${esc(t("ov.ws_know_empty"))}</div>`}</div></div>`;

        // Server chỉ gửi 40 tài liệu mới nhất: nói rõ phần còn lại thay vì cắt im lặng.
        const srcCon = Math.max(0, (c.sources || 0) - (d.sources || []).length);
        const srcHtml = (d.sources || []).map((it) => dong(it,
          `<b class="ovw-kb ${it.distilled ? "ok" : it.cu ? "old" : "wait"}">${esc(t(it.distilled ? "ov.ws_know_done" : "ov.ws_know_wait"))}</b>`)).join("")
          + (srcCon ? `<div class="ovw-ksub">${esc(t("ov.ws_know_more", { n: srcCon }))}</div>` : "");
        const wikiHtml = (d.wiki_groups || []).map((g) =>
          `<div class="ovw-ksub">${esc(g.chude ? g.chude.replace(/[-_]/g, " ") : t("ov.ws_know_common"))}</div>`
          + g.items.map((it) => dong(it, "")).join("")).join("");
        const hotHtml = (d.hot || []).length
          ? d.hot.map((it) => dong(it, `<span class="ov-dim">${esc(t("ov.ws_know_opens", { n: it.lan }))}</span>`)).join("")
          : `<div class="ovw-ksub">${esc(t("ov.ws_know_hot_empty"))}</div>`;
        const inboxHtml = (d.inbox || []).length
          ? d.inbox.map((it) => dong(it, `<b class="ovw-kb kenh">${esc(KENH[it.kenh] || it.kenh || t("ov.ws_know_kenh_khac"))}</b>`)).join("")
          : `<div class="ovw-ksub">${esc(t("ov.ws_know_inbox_empty"))}</div>`;

        box.innerHTML = `<div class="ov-dmetric">${[["ov.mem_sources", c.sources], ["ov.mem_wiki", c.wiki], ["ov.mem_facts", c.facts], ["ov.ws_know_inbox_n", c.inbox]]
            .map(([kk, v]) => `<div><strong>${v == null ? "-" : so(v)}</strong><span>${esc(t(kk))}</span></div>`).join("")}</div>
          ${d.stale ? `<div class="ovw-kwarn">${ic("triangle-alert")} ${esc(t("ov.ws_know_stale", { n: d.stale }))}</div>` : ""}
          ${grp("know-src", "inbox", t("ov.ws_know_src"), c.sources || 0, srcHtml)}
          ${grp("know-wiki", "book-open", t("ov.ws_know_wiki"), c.wiki || 0, wikiHtml)}
          ${grp("know-hot", "flame", t("ov.ws_know_hot"), (d.hot || []).length, hotHtml)}
          ${grp("know-inbox", "paperclip", t("ov.ws_know_inbox"), c.inbox || 0, inboxHtml)}
          <div class="ovw-know-acts">
            <button type="button" class="ov-secondary" id="ovwKnowUp">${ic("plus")} ${esc(t("ov.ws_know_up"))}</button>
            <button type="button" class="ov-ghost" id="ovwKnowDistill">${ic("sparkles")} ${esc(t("ov.ws_know_distill"))}</button>
            <button type="button" class="ov-ghost" id="ovwKnowBrowse">${ic("folder-open")} ${esc(t("ov.ws_know_browse"))}</button>
            <input type="file" id="ovwKnowFile" hidden>
            <span class="ov-dim ovw-kmsg" id="ovwKnowMsg"></span>
          </div>`;

        box.querySelectorAll(".ovw-kitem").forEach((el) => (el.onclick = () => moFile(el.dataset.rel)));
        const inp = box.querySelector("#ovwKnowFile"), msg = box.querySelector("#ovwKnowMsg");
        box.querySelector("#ovwKnowUp").onclick = () => inp.click();
        inp.onchange = async () => {
          if (!inp.files || !inp.files[0]) return;
          const fd = new FormData();
          fd.append("brain", brainSel); fd.append("folder", "sources"); fd.append("file", inp.files[0]);
          try {
            const rr = await fetch("/files/upload", { method: "POST", body: fd, credentials: "same-origin" });
            const jj = await rr.json().catch(() => ({}));
            msg.textContent = jj.ok ? t("ov.ws_know_up_ok", { ten: jj.name || inp.files[0].name }) : (jj.error || t("ov.ws_know_up_err"));
            if (jj.ok) setTimeout(taiKnow, 400);
          } catch (e) { msg.textContent = t("ov.ws_know_up_err"); }
          inp.value = "";
        };
        box.querySelector("#ovwKnowDistill").onclick = () => {
          dongHet(); chonBrain(brainSel, p.ten);
          setTimeout(() => hoiJoyce(t("ov.ws_know_distill_q", { phong: p.ten })), 120);
        };
        box.querySelector("#ovwKnowBrowse").onclick = () => { dongHet(); moBrain(brainSel, p.ten); };
      }).catch(() => {
        const box = w.querySelector("#ovwWsKnow");
        if (box && w.isConnected) box.innerHTML = `<span class="ov-dim">${esc(t("ov.dw_cap_err"))}</span>`;
      });
    };
    taiKnow();

    // Giao việc: tiêu đề + yêu cầu, "Chạy qua" = auto | wf:<slug>, tick Cần duyệt khi
    // việc chạm ngoài. Việc luôn vào đúng brain phòng - tránh lỗi giao nhầm não.
    const nutGo = w.querySelector("#ovwWsAGo");
    if (nutGo) nutGo.onclick = async () => {
      const title = (w.querySelector("#ovwWsATitle").value || "").trim();
      if (!title) { try { w.querySelector("#ovwWsATitle").focus(); } catch (e) {} return; }
      const fd = new FormData();
      fd.append("title", title);
      fd.append("intent", w.querySelector("#ovwWsAIntent").value || title);
      fd.append("brain", bparam);
      const route = w.querySelector("#ovwWsARoute") ? w.querySelector("#ovwWsARoute").value : "auto";
      if (route && route !== "auto") fd.append("route", route);
      if (w.querySelector("#ovwWsANeed").checked) fd.append("needs_approval", "1");
      const sid = window.JoyceSessions && window.JoyceSessions.current ? window.JoyceSessions.current() : "";
      if (sid) fd.append("chat_id", "web:" + sid);
      const msg = w.querySelector("#ovwWsAMsg");
      try {
        const r = await fetch("/kanban/task", { method: "POST", body: fd, credentials: "same-origin" });
        const rr = await r.json().catch(() => ({}));
        msg.textContent = rr.ok ? t("ov.dw_assign_ok", { phong: p.ten }) : (rr.error || t("ov.dw_assign_err"));
        if (rr.ok) { w.querySelector("#ovwWsATitle").value = ""; w.querySelector("#ovwWsAIntent").value = ""; }
      } catch (e) { msg.textContent = t("ov.dw_assign_err"); }
    };

    // Ý tưởng mới: task [Ý tưởng] route qua pipeline xu-ly-y-tuong-moi của CHÍNH brain
    // này. Pipeline đó tự chạy kể cả khi orchestration off, kết quả lưu wiki/y-tuong/
    // và báo về chat đang mở (chat_id web:<sid>) - lối trưởng phòng đề xuất cải tiến
    // mà không cần biết file nào.
    w.querySelectorAll("[data-idea]").forEach((b) => (b.onclick = () => {
      const o2 = w.querySelector("#ovwIdea"); o2.value = t(b.dataset.idea) + ": "; o2.focus();
    }));
    const nutIdea = w.querySelector("#ovwIdeaGo");
    if (nutIdea) nutIdea.onclick = async () => {
      const y = (w.querySelector("#ovwIdea").value || "").trim();
      if (!y) { try { w.querySelector("#ovwIdea").focus(); } catch (e) {} return; }
      const fd = new FormData();
      fd.append("title", "[Ý tưởng] " + y.slice(0, 80));
      fd.append("intent", y);
      fd.append("brain", bparam);
      fd.append("route", "wf:xu-ly-y-tuong-moi");
      const sid = window.JoyceSessions && window.JoyceSessions.current ? window.JoyceSessions.current() : "";
      if (sid) fd.append("chat_id", "web:" + sid);
      const msg = w.querySelector("#ovwIdeaMsg");
      try {
        const r = await fetch("/kanban/task", { method: "POST", body: fd, credentials: "same-origin" });
        const rr = await r.json().catch(() => ({}));
        msg.textContent = rr.ok ? t("ov.ws_idea_ok", { phong: p.ten }) : (rr.error || t("ov.ws_idea_err"));
        if (rr.ok) w.querySelector("#ovwIdea").value = "";
      } catch (e) { msg.textContent = t("ov.ws_idea_err"); }
    };
  }

  // ---- Workspace trưởng phòng: bấm vào một phòng ------------------------------------
  function moWorkspace(p, khoiMap) {
    const old = document.getElementById("ovDrawer");
    if (old) { if (typeof old.__dong === "function") old.__dong(); else old.remove(); }
    const k = (khoiMap || {})[p.khoi_id] || {};
    const c = p.tasks || {};
    const w = document.createElement("div");
    w.id = "ovDrawer";

    // Lộ trình trưởng phòng: 5 bước, tick theo dữ liệu THẬT của brain phòng đó.
    const steps = [
      { ok: !!p.has_brain, key: "ov.dw_s1" },
      { ok: (p.nguon || 0) > 0, key: "ov.dw_s2" },
      { ok: null, key: "ov.dw_s3", id: "ovwStep3" },   // đợi fetch agents/skills
      { ok: ((c.open || 0) + (c.done24 || 0) + (c.blocked || 0)) > 0, key: "ov.dw_s4" },
      { ok: (c.done24 || 0) > 0, key: "ov.dw_s5" },
    ];
    const stepHtml = (s) => `<li${s.id ? ` id="${esc(s.id)}"` : ""} class="${s.ok === true ? "done" : s.ok === false ? "todo" : "wait"}">
      ${ic(s.ok === true ? "circle-check" : s.ok === false ? "circle" : "loader", { cls: s.ok === null ? "ic-spin" : "" })}
      <span>${esc(t(s.key))}</span></li>`;

    w.innerHTML = `<div class="ov-backdrop"></div><aside class="ov-drawer ovw-wide" role="dialog" aria-modal="true" aria-label="${esc(p.ten)}">
      <div class="ov-drawer-head"><div><span class="ov-eyebrow">${esc(p.brand)} · ${esc(p.khoi)}</span><h2>${esc(p.ten)}</h2>
        ${p.agent ? `<span class="ov-dim">${ic("bot")} ${esc(p.agent)}${p.vai ? " - " + esc(p.vai) : ""}</span>` : ""}</div>
        <button type="button" class="ovw-full" aria-label="${esc(t("ov.dw_full"))}" title="${esc(t("ov.dw_full"))}" aria-pressed="false">${ic("maximize")}</button>
        <button type="button" class="ov-close" aria-label="${esc(t("common.close"))}">${ic("x")}</button></div>
      <div class="ov-drawer-body">
        <div class="ovw-acts">
          ${p.has_brain ? `<button type="button" class="ov-primary" data-act="assign">${ic("plus")} ${esc(t("ov.dw_assign"))}</button>` : ""}
          ${p.has_brain ? `<button type="button" class="ov-secondary" data-act="board">${ic("square-kanban")} ${esc(t("ov.dw_board"))}</button>
          <button type="button" class="ov-secondary" data-act="files">${ic("folder-open")} ${esc(t("ov.ws_files"))}</button>` : ""}
          <button type="button" class="ov-ghost" data-act="improve">${ic("sparkles")} ${esc(t("ov.dw_improve"))}</button>
          ${pill(STATUS_TONE[p.status], t(ST_KEY[p.status] || "ov.st_empty"))}
        </div>
        <div class="ovw-assign" id="ovwAssign" style="display:none">
          <input id="ovwWsATitle" placeholder="${esc(t("ov.dw_assign_title"))}">
          <textarea id="ovwWsAIntent" rows="2" placeholder="${esc(t("ov.dw_assign_intent"))}"></textarea>
          <div class="ovw-assign-row">
            <label class="ov-dim ovw-route">${esc(t("ov.ws_route"))} <select id="ovwWsARoute"><option value="auto">${esc(t("ov.ws_route_auto"))}</option></select></label>
            <label class="ovw-chk"><input type="checkbox" id="ovwWsANeed">${esc(t("ov.dw_need_approve"))}</label>
            <button type="button" class="ov-primary" id="ovwWsAGo">${esc(t("ov.dw_assign_go"))}</button>
            <span class="ov-dim" id="ovwWsAMsg"></span>
          </div>
        </div>
        ${p.has_brain ? wsStatHtml()
          : `<div class="ov-dmetric">${[["ov.ds_done", c.done24], ["ov.ds_open", c.open], ["ov.ds_review", c.review], ["ov.ds_blocked", c.blocked], ["ov.mem_sources", p.nguon], ["ov.mem_wiki", p.wiki], ["ov.dw_staff", p.nhan_vien]]
          .map(([kk, v]) => `<div><strong>${v == null ? "-" : so(v)}</strong><span>${esc(t(kk))}</span></div>`).join("")}</div>`}
        ${p.has_brain ? wsIdeaHtml() : ""}

        <div class="ovw-stages">
          <div class="ovw-stage"><h4><span class="ovw-knum">01</span> ${esc(t("ov.dw_before"))}</h4>
            <p class="ovw-stage-sub">${esc(t("ov.dw_before_d"))}</p>
            ${p.vai ? `<p class="ovw-vai">${esc(p.vai)}</p>` : ""}
            <ul class="ovw-list">${(p.nhiem_vu || []).map((nv) => `<li>${esc(nv)}</li>`).join("") || `<li class="ov-dim">${esc(t("ov.dw_no_duty"))}</li>`}</ul>
            <div class="ovw-qt" data-qt="truoc">${ic("loader", { cls: "ic-spin" })}</div>
          </div>
          <div class="ovw-stage"><h4><span class="ovw-knum">02</span> ${esc(t("ov.dw_during"))}</h4>
            <p class="ovw-stage-sub">${esc(t("ov.dw_during_d"))}</p>
            <div id="ovwCap">${ic("loader", { cls: "ic-spin" })}</div>
            <div class="ovw-qt" data-qt="trong"></div>
          </div>
          <div class="ovw-stage"><h4><span class="ovw-knum">03</span> ${esc(t("ov.dw_after"))}</h4>
            <p class="ovw-stage-sub">${esc(t("ov.dw_after_d"))}</p>
            <p class="ovw-vai">${esc(k.dau_ra || t("ov.dw_no_output"))}</p>
            <div class="ovw-qt" data-qt="sau"></div>
          </div>
        </div>
        <div class="ovw-qt-khac" id="ovwQtKhac"></div>
        ${p.has_brain ? wsInfoHtml() : ""}

        <div class="ovw-steps"><h4>${esc(t("ov.dw_steps"))}</h4><ul>${steps.map(stepHtml).join("")}</ul></div>
      </div></aside>`;
    document.body.appendChild(w);
    // AbortController thay cho removeEventListener tay: mở drawer lần 2 chỉ gọi old.remove()
    // chứ không gọi dong() của drawer cũ, nên listener keydown cũ còn bám document và tích
    // tụ thêm một cái mỗi lần mở. Gắn abort() lên chính node để lần mở sau dọn được nó.
    const huy = new AbortController();
    const dong = () => { huy.abort(); w.remove(); };
    w.__dong = dong;
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") dong(); },
                              { signal: huy.signal });
    w.querySelector(".ov-backdrop").onclick = dong;
    w.querySelector(".ov-close").onclick = dong;

    // Thu gon / mo rong TUNG NHOM trong 3 cot (Agent, Workflow, Ky nang, tung hang quy
    // trinh): phong nhieu quy trinh keo cot rat dai - chu repo bao 2026-10-09 them nut
    // mui ten so xuong/thu gon. Trang thai nho theo brain+nhom, song trong Set tren window
    // nen mo lai drawer trong phien van giu dung cho da gon.
    const grpThu = window.__ovGrpThu || (window.__ovGrpThu = new Set());
    const grpKhoa = (k) => String(p.brain || p.ten || "") + "|" + k;
    w.addEventListener("click", (e) => {
      const h = e.target.closest("[data-grp-h]");
      if (!h || !w.contains(h)) return;
      const grp = h.closest("[data-grp]");
      if (!grp) return;
      const on = grp.classList.toggle("collapsed");
      const k = grpKhoa(grp.dataset.grp);
      if (on) grpThu.add(k); else grpThu.delete(k);
    });
    w.__grpBound = true;   // napWs kiểm cờ này: overlay CEO chưa bind thì nó tự bind,
                           // drawer đã bind rồi thì khỏi gắn thêm (toggle hai lần = không đổi)
    // Nạp năng lực thật của brain phòng: agent phụ, workflow, skill.
    const cap = w.querySelector("#ovwCap");
    if (p.has_brain) {
      const b = encodeURIComponent(p.brain);
      Promise.all([api("/agents?brain=" + b + "&prompt=0"), api("/workflows?brain=" + b), api("/skills?brain=" + b)])
        .then((rs) => {
          if (!w.isConnected) return;
          const ag = (rs[0].data && rs[0].data.agents) || [];
          const wf = ((rs[1].data && rs[1].data.workflows) || []);
          const sk = ((rs[2].data && rs[2].data.skills) || []);
          const capBtn = (rel, ten) => `<button type="button" class="ovw-cap ovw-cap-lk" data-file="${esc(rel)}" title="${esc(rel)}">${esc(ten)}</button>`;
          const nhom = (icon, nhan, arr, lay, khoa) => arr.length
            ? `<div class="ovw-capgrp${grpThu.has(grpKhoa(khoa)) ? " collapsed" : ""}" data-grp="${khoa}"><span data-grp-h>${ic(icon)} ${esc(nhan)} <b>${arr.length}</b>${ic("chevron-down")}</span><div>${arr.slice(0, 8).map(lay).join("")}</div></div>` : "";
          cap.innerHTML =
            nhom("bot", t("ov.dw_agents"), ag, (a) => capBtn("agents/" + a.slug + ".md", a.name || a.slug), "ag") +
            nhom("git-branch", t("ov.dw_workflows"), wf, (x) => capBtn("workflows/" + x.slug + ".md", x.name || x.slug), "wf") +
            nhom("zap", t("ov.dw_skills"), sk, (x) => capBtn((x.enabled === false ? "skills/.disabled/" : "skills/") + x.slug + "/SKILL.md", x.name || x.slug), "sk") ||
            `<span class="ov-dim">${esc(t("ov.dw_cap_empty"))}</span>`;
          cap.querySelectorAll("[data-file]").forEach((b) => (b.onclick = () => {
            if (window.JoyceFileEditor) window.JoyceFileEditor.open(b.dataset.file, { brain: p.brain_path });
          }));
          const s3 = w.querySelector("#ovwStep3");
          if (s3) { s3.className = ag.length || sk.length ? "done" : "todo"; s3.innerHTML = `${ic(ag.length || sk.length ? "circle-check" : "circle")}<span>${esc(t("ov.dw_s3"))}</span>`; }
        }).catch(() => { if (w.isConnected) cap.innerHTML = `<span class="ov-dim">${esc(t("ov.dw_cap_err"))}</span>`; });
    } else {
      cap.innerHTML = `<span class="ov-dim">${esc(t("ov.dl_nobrain"))}</span>`;
    }

    // Toàn màn hình: drawer mặc định rộng 760px, không đủ cho ba cột quy trình.
    const nutFull = w.querySelector(".ovw-full");
    if (nutFull) nutFull.onclick = () => {
      const on = w.classList.toggle("ovw-fullscreen");
      nutFull.setAttribute("aria-pressed", on ? "true" : "false");
      nutFull.innerHTML = ic(on ? "minimize" : "maximize");
      nutFull.title = t(on ? "ov.dw_full_off" : "ov.dw_full");
    };

    // QUY TRÌNH THẬT của phòng, xếp vào đúng cột Trước / Trong / Sau. Ba cột này trước đây
    // chỉ là chữ mô tả vai trò - không nối vào tài liệu nào, nên trưởng phòng đọc xong vẫn
    // phải tự đi tìm file. Bấm một quy trình = MỞ THẲNG file .md trong trình sửa nổi
    // (file-editor.js, z-3000 nằm trên drawer z-61): xem và sửa tay ngay, đóng file là quay
    // lại workspace. Editor bắt Esc ở pha capture nên không đóng nhầm drawer bên dưới.
    // Nút "Nâng cấp quy trình" vẫn lo phần nhờ Joyce sửa hộ qua chat.
    const moQuyTrinh = (it) => {
      if (p.brain_path && window.JoyceFileEditor && typeof window.JoyceFileEditor.open === "function") {
        window.JoyceFileEditor.open(it.rel, { brain: p.brain_path });
        return;
      }
      hoiQuyTrinh(it);
    };
    // Icon chat chi hien khi hover dong quy trinh: nhay sang chat cua brain phong keo theo
    // duong dan file san trong cau lenh - chu du an: "click chuyen nhanh sang khung chat
    // joyce de nho chinh sua file do" ma khong de icon thuong truc cho roi mat.
    const hoiQuyTrinh = (it) => {
      dong();
      if (p.brain_path) moBrain(p.brain_path, p.ten);
      setTimeout(() => hoiJoyce(t("ov.dw_qt_prompt", { ten: it.ten, file: it.rel, phong: p.ten })), 120);
    };
    const veQt = (hop, ds, nhan, khoa) => {
      if (!hop) return;
      if (!ds.length) { hop.innerHTML = ""; hop.classList.remove("collapsed"); delete hop.dataset.grp; return; }
      hop.dataset.grp = khoa;
      hop.classList.toggle("collapsed", grpThu.has(grpKhoa(khoa)));
      hop.innerHTML = `<div class="ovw-qt-h" data-grp-h>${ic("scroll")} ${esc(nhan)} <b>${ds.length}</b>${ic("chevron-down")}</div>`
        + ds.map((it, i) => `<div class="ovw-qt-i" title="${esc(it.rel)}">`
          + `<button type="button" class="ovw-qt-open" data-i="${i}"><span>${esc(it.ten)}</span>${ic("pen-line")}</button>`
          + `<button type="button" class="ovw-qt-chat" data-i="${i}" title="${esc(t("ov.dw_qt_chat"))}">${ic("message-circle")}</button>`
          + `</div>`).join("");
      hop.querySelectorAll(".ovw-qt-open").forEach((b) => (b.onclick = () => moQuyTrinh(ds[+b.dataset.i])));
      hop.querySelectorAll(".ovw-qt-chat").forEach((b) => (b.onclick = () => hoiQuyTrinh(ds[+b.dataset.i])));
    };
    if (p.has_brain) {
      api("/api/joyce/v1/overview/quy-trinh?brain=" + encodeURIComponent(p.brain_path)).then((rq) => {
        if (!w.isConnected) return;
        const t0 = w.querySelector('[data-qt="truoc"]');
        // GỌI HỎNG khác RỖNG. Gộp hai cái làm một thì server chưa khởi động lại (endpoint
        // còn 404) cũng hiện "phòng chưa có quy trình nào" - câu đó sai và làm người dùng
        // đi sửa tên file trong khi lỗi nằm ở chỗ khác.
        if (!rq.ok) {
          w.querySelectorAll(".ovw-qt").forEach((x) => { x.innerHTML = ""; x.classList.remove("collapsed"); delete x.dataset.grp; });
          if (t0) t0.innerHTML = `<p class="ov-dim ovw-qt-none">${esc(t("ov.dw_qt_err"))}</p>`;
          return;
        }
        const g = (rq.data && rq.data.giai_doan) || {};
        [["truoc", "ov.dw_qt_before"], ["trong", "ov.dw_qt_during"], ["sau", "ov.dw_qt_after"]]
          .forEach(([key, nhan]) => veQt(w.querySelector(`[data-qt="${key}"]`), g[key] || [], t(nhan), "qt-" + key));
        veQt(w.querySelector("#ovwQtKhac"), g.khac || [], t("ov.dw_qt_other"), "qt-khac");
        // Gợi ý đặt tên chỉ hiện khi phòng CHƯA có quy trình nào - treo nó ở cột Trước khi
        // riêng cột đó rỗng thì sai, vì phòng có thể chỉ có quy trình Trong dịch vụ.
        if (t0 && !((rq.data && rq.data.tong) || 0)) t0.innerHTML = `<p class="ov-dim ovw-qt-none">${esc(t("ov.dw_qt_none"))}</p>`;
      });
    } else {
      w.querySelectorAll(".ovw-qt").forEach((x) => { x.innerHTML = ""; x.classList.remove("collapsed"); delete x.dataset.grp; });
    }

    w.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => {
      const a = b.dataset.act;
      if (a === "assign") {
        const f = w.querySelector("#ovwAssign");
        f.style.display = f.style.display === "none" ? "" : "none";
        if (f.style.display !== "none") { try { w.querySelector("#ovwWsATitle").focus(); } catch (e) {} }
        return;
      }
      if (a === "files") {
        // "Thư mục tệp" không nhảy sang cây file nữa - cuộn tới panel Tri thức phòng
        // ngay trong drawer (xem file thô vẫn có nút riêng "Mở thư mục tệp" trong panel).
        const kb = w.querySelector("#ovwWsKnow");
        const sec = kb ? kb.closest("section") : null;
        if (sec) {
          sec.scrollIntoView({ behavior: "smooth", block: "start" });
          sec.classList.remove("ovw-kflash"); void sec.offsetWidth;
          sec.classList.add("ovw-kflash");
          setTimeout(() => sec.classList.remove("ovw-kflash"), 1800);
          return;
        }
      }
      dong();
      if (a === "board") { chonBrain(p.brain_path, p.ten); setTimeout(() => go("kanban"), 60); }
      else if (a === "files") moBrain(p.brain_path, p.ten);
      else if (a === "improve") hoiJoyce(t("ov.dw_improve_q", { phong: p.ten, vai: p.vai || "", nhiemvu: (p.nhiem_vu || []).join("; "), daura: k.dau_ra || "" }));
    }));

    // Không gian brain của phòng nằm NGAY TRONG drawer này: hiện trạng, ý tưởng, đội
    // hình (giao việc 1-1 cho agent), việc phòng, loop riêng, kho tri thức. Trưởng phòng
    // mở phòng ra là có đủ màn làm việc, không phải đi đọc cây thư mục.
    if (p.has_brain) napWs(w, p, { teamFull: false, statsExtra: [["ov.dw_staff", p.nhan_vien]], dongHet: dong });
    setTimeout(() => { try { w.querySelector(".ov-close").focus(); } catch (e) {} }, 30);
  }

  // ---- Không gian brain: nút "Mở brain của phòng" mở cái này, KHÔNG mở thư mục file ----
  // Chủ bảo trưởng phòng nhìn cây thư mục sẽ không hiểu gì, nên màn này trả lời 4 câu
  // bằng ngôn ngữ vận hành: brain đang có gì (đội hình/loop/tri thức), việc nào đang
  // chạy hay chờ, giao việc cho ai (agent 1-1 hoặc hàng đợi), ý tưởng gửi ở đâu.
  // Overlay nằm TRÊN drawer phòng (z 70/71) và DƯỚI trình sửa file (z 3000): đóng ra
  // là quay lại workspace phòng. Dùng được cho cả Brain Default (nút "Không gian CEO").
  function moBrainWs(p, khoiMap) {
    const old = document.getElementById("ovBrainWs");
    if (old) { if (typeof old.__dong === "function") old.__dong(); else old.remove(); }
    const k = (khoiMap || {})[p.khoi_id] || {};
    const w = document.createElement("div");
    w.id = "ovBrainWs";
    w.innerHTML = `<div class="ov-backdrop"></div><aside class="ov-drawer ovw-ws" role="dialog" aria-modal="true" aria-label="${esc(p.ten)}">
      <div class="ov-drawer-head"><div><span class="ov-eyebrow">${esc(t("ov.ws_eyebrow", { phong: p.ten }))}</span><h2>${ic("brain")} ${esc(p.ten)}</h2>
        <span class="ov-dim" id="ovwWsMode"></span></div>
        <button type="button" class="ovw-full" aria-label="${esc(t("ov.dw_full"))}" title="${esc(t("ov.dw_full"))}" aria-pressed="false">${ic("maximize")}</button>
        <button type="button" class="ov-close" aria-label="${esc(t("common.close"))}">${ic("x")}</button></div>
      <div class="ov-drawer-body">
        <div class="ovw-acts">
          <button type="button" class="ov-secondary" data-ws="board">${ic("square-kanban")} ${esc(t("ov.dw_board"))}</button>
          <button type="button" class="ov-secondary" data-ws="files">${ic("folder-open")} ${esc(t("ov.ws_files"))}</button>
          <button type="button" class="ov-ghost" data-ws="improve">${ic("sparkles")} ${esc(t("ov.dw_improve"))}</button>
        </div>
        ${wsStatHtml()}
        ${wsIdeaHtml()}
        <section class="ovw-sec"><h4>${ic("plus")} ${esc(t("ov.dw_assign"))}</h4>
          <div class="ovw-assign" style="display:block">
            <input id="ovwWsATitle" placeholder="${esc(t("ov.dw_assign_title"))}">
            <textarea id="ovwWsAIntent" rows="2" placeholder="${esc(t("ov.dw_assign_intent"))}"></textarea>
            <div class="ovw-assign-row">
              <label class="ov-dim ovw-route">${esc(t("ov.ws_route"))} <select id="ovwWsARoute"><option value="auto">${esc(t("ov.ws_route_auto"))}</option></select></label>
              <label class="ovw-chk"><input type="checkbox" id="ovwWsANeed">${esc(t("ov.dw_need_approve"))}</label>
              <button type="button" class="ov-primary" id="ovwWsAGo">${esc(t("ov.dw_assign_go"))}</button>
              <span class="ov-dim" id="ovwWsAMsg"></span>
            </div>
          </div>
        </section>
        ${wsInfoHtml()}
      </div></aside>`;
    document.body.appendChild(w);

    const huy = new AbortController();
    const dong = () => { huy.abort(); w.remove(); };
    w.__dong = dong;
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") dong(); }, { signal: huy.signal });
    w.querySelector(".ov-backdrop").onclick = dong;
    w.querySelector(".ov-close").onclick = dong;
    const nutFull = w.querySelector(".ovw-full");
    if (nutFull) nutFull.onclick = () => {
      const on = w.classList.toggle("ovw-fullscreen");
      nutFull.setAttribute("aria-pressed", on ? "true" : "false");
      nutFull.innerHTML = ic(on ? "minimize" : "maximize");
      nutFull.title = t(on ? "ov.dw_full_off" : "ov.dw_full");
    };
    // Roi trang = dong ca workspace LAN drawer phong ben duoi, khong thi nguoi dung quay
    // lai thay hai lop phu chong nhau.
    const dongHet = () => {
      dong();
      const d = document.getElementById("ovDrawer");
      if (d && typeof d.__dong === "function") d.__dong(); else if (d) d.remove();
    };

    w.querySelectorAll("[data-ws]").forEach((b) => (b.onclick = () => {
      const a = b.dataset.ws;
      if (a === "board") { dongHet(); chonBrain(p.brain_path || "brain", p.ten); go("kanban"); }
      else if (a === "files") {
        const kb = w.querySelector("#ovwWsKnow");
        const sec = kb ? kb.closest("section") : null;
        if (sec) {
          sec.scrollIntoView({ behavior: "smooth", block: "start" });
          sec.classList.remove("ovw-kflash"); void sec.offsetWidth;
          sec.classList.add("ovw-kflash");
          setTimeout(() => sec.classList.remove("ovw-kflash"), 1800);
        } else { dongHet(); moBrain(p.brain_path || "brain", p.ten); }
      }
      else if (a === "improve") {
        dongHet(); chonBrain(p.brain_path || "brain", p.ten);
        setTimeout(() => hoiJoyce(t("ov.dw_improve_q", { phong: p.ten, vai: p.vai || "", nhiemvu: (p.nhiem_vu || []).join("; "), daura: k.dau_ra || "" })), 120);
      }
    }));
    napWs(w, p, { teamFull: true, dongHet: dongHet });
    setTimeout(() => { try { w.querySelector(".ov-close").focus(); } catch (e) {} }, 30);
  }

  // ============================================================
  // LỊCH & KẾ HOẠCH (nhắc hẹn của mọi brain, 7 ngày)
  // ============================================================
  let _calStart = null;   // "YYYY-MM-DD" của ngày đầu tuần đang xem; null = từ hôm nay
  const isoDay = (dt) => dt.getFullYear() + "-" + String(dt.getMonth() + 1).padStart(2, "0") + "-" + String(dt.getDate()).padStart(2, "0");
  function dichNgay(iso, n) { const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() + n); return isoDay(d); }
  async function renderCalendar(el) {
    el.innerHTML = loading();
    const start = _calStart || isoDay(new Date());
    const r = await api("/api/joyce/v1/overview/calendar?days=7&start=" + encodeURIComponent(start));
    if (!el.isConnected) return;
    if (!r.ok && r.status === 403) { el.innerHTML = `<div class="ov-page">${loiTrang(t("ov.staff_denied"))}</div>`; return; }
    const d = r.data || {};
    const days = d.days || [];
    const cols = days.map((x) => `<div class="ov-calcol${x.today ? " today" : ""}"><div class="ov-calhead"><b>${esc(t(DOW_KEY[x.dow] || "ov.dow_0"))}</b><span>${esc(x.dd)}</span></div>
      ${(x.items || []).length ? x.items.map((it) => `<div class="ov-calev${it.repeat ? " rep" : ""}" title="${esc(it.title)}"><time>${esc(it.time)}</time><strong>${esc(it.title)}</strong><span>${esc([it.label, it.brain].filter(Boolean).join(" · "))}</span></div>`).join("")
        : `<div class="ov-calnone">${esc(t("ov.cal_none"))}</div>`}</div>`).join("");
    el.innerHTML = `<div class="ov-page">
      <div class="ov-toolbar"><div class="ov-chips">
        <button type="button" class="ov-chip" id="ovCalPrev">${ic("chevron-left")} ${esc(t("ov.cal_prev"))}</button>
        <button type="button" class="ov-chip" id="ovCalToday">${esc(t("ov.cal_today"))}</button>
        <button type="button" class="ov-chip" id="ovCalNext">${esc(t("ov.cal_next"))} ${ic("chevron-right")}</button></div>
        <span class="ov-synced">${esc(t("ov.cal_total", { so: d.total || 0 }))}</span>
        <button type="button" class="ov-secondary" data-go="selfimprove">${ic("alarm-clock")} ${esc(t("ov.cal_add"))}</button></div>
      ${r.ok ? "" : loiTrang(t("ov.err_load"))}
      ${panel(t("ov.p_cal"), t("ov.p_cal_d"), `<div class="ov-cal">${cols}</div>`)}</div>`;
    el.querySelector("#ovCalPrev").onclick = () => { _calStart = dichNgay(start, -7); renderCalendar(el); };
    el.querySelector("#ovCalNext").onclick = () => { _calStart = dichNgay(start, 7); renderCalendar(el); };
    el.querySelector("#ovCalToday").onclick = () => { _calStart = null; renderCalendar(el); };
    ganDieuHuong(el);
  }

  // ============================================================
  // BÁO CÁO: mỗi thẻ trỏ về đúng chỗ đang giữ số liệu thật, hoặc nhờ Joyce viết báo cáo
  // từ dữ liệu thật (điền sẵn câu hỏi, không tự gửi).
  // ============================================================
  const REPORTS = [
    { id: "daily", icon: "sun", go: "command", ask: "ov.rq_daily", k: ["ov.rep_daily", "ov.rep_daily_d", "ov.rep_daily_src"] },
    { id: "weekly", icon: "trending-up", go: "kanban", ask: "ov.rq_weekly", k: ["ov.rep_weekly", "ov.rep_weekly_d", "ov.rep_weekly_src"] },
    { id: "dept", icon: "layers", go: "departments", ask: "ov.rq_dept", k: ["ov.rep_dept", "ov.rep_dept_d", "ov.rep_dept_src"] },
    { id: "social", icon: "share-2", sub: ["camnang", "fanpage"], ask: "ov.rq_social", k: ["ov.rep_social", "ov.rep_social_d", "ov.rep_social_src"] },
    { id: "knowledge", icon: "brain", go: "learn", ask: "ov.rq_knowledge", k: ["ov.rep_knowledge", "ov.rep_knowledge_d", "ov.rep_knowledge_src"] },
    { id: "usage", icon: "chart-column", go: "usage", ask: "ov.rq_usage", k: ["ov.rep_usage", "ov.rep_usage_d", "ov.rep_usage_src"] },
  ];
  function renderReports(el) {
    el.innerHTML = `<div class="ov-page">
      <section class="ov-brief"><div class="ov-brief-t"><span class="ov-eyebrow">${esc(t("ov.rep_eyebrow"))}</span><h2>${esc(t("ov.rep_title"))}</h2><p>${esc(t("ov.rep_text"))}</p></div></section>
      <div class="ov-reps">${REPORTS.map((r) => `<article class="ov-rep"><div class="ov-rep-i">${ic(r.icon)}</div>
        <h3>${esc(t(r.k[0]))}</h3><p>${esc(t(r.k[1]))}</p>
        <div class="ov-rep-meta"><span>${esc(t(r.k[2]))}</span></div>
        <div class="ov-rep-a"><button type="button" class="ov-secondary" data-rep-go="${esc(r.id)}">${esc(t("ov.rep_view"))}</button>
        <button type="button" class="ov-ghost" data-ask="${esc(t(r.ask))}">${ic("sparkles")} ${esc(t("ov.rep_ask"))}</button></div></article>`).join("")}</div></div>`;
    el.querySelectorAll("[data-rep-go]").forEach((b) => (b.onclick = () => {
      const r = REPORTS.find((x) => x.id === b.dataset.repGo);
      if (!r) return;
      if (r.sub) goSub(r.sub[0], r.sub[1]); else go(r.go);
    }));
    ganDieuHuong(el);
  }

  // ============================================================
  // TÀI LIỆU CHƯNG CẤT - bảng duyệt 3 nhóm để chủ nhìn là biết hôm nay cần duyệt gì:
  //   1) Chờ duyệt hôm nay : bản nháp mới tạo hôm nay (nổi bật, lên đầu)
  //   2) Hàng chờ tích luỹ : mọi bản nháp chưa chưng cất còn lại, chờ lâu nhất lên đầu
  //   3) Đã chưng cất      : trang wiki sửa trong 7 ngày, mới nhất trước - xem lại
  //                          chất lượng rồi đánh dấu "đã xem"
  // Draft = file trong wiki/_cho-duyet|_cho_duyet, hoặc có status: draft + cho-duyet.
  // Nút Duyệt -> POST chung-cat/duyet: server đổi status -> active, bỏ staging + tag
  // cho-duyet, chuyển file ra wiki chính thức, cập nhật wiki/index.md + log.md.
  // ============================================================
  let _ccMsg = null;    // {ok, text} - kết quả thao tác duyệt/gộp gần nhất
  async function renderChungCat(el) {
    el.innerHTML = loading();
    const r = await api("/api/joyce/v1/overview/chung-cat/duyet");
    if (!el.isConnected) return;
    if (!r.ok && r.status === 403) { el.innerHTML = `<div class="ov-page">${loiTrang(t("ov.staff_denied"))}</div>`; return; }
    if (!r.ok) { el.innerHTML = `<div class="ov-page">${loiTrang(t("ov.cc_err"))}</div>`; return; }
    const d = r.data || {};
    const moi = d.moi || [], cho = d.cho || [], da = d.da_duyet || [], lech = d.lech_thu_muc || [];

    const choBaoLau = (x) => x.cho_ngay >= 1 ? t("ov.cc_wait_d", { n: so(x.cho_ngay) }) : t("ov.cc_wait_today");
    const hangNhap = (x) => `
      <div class="ov-cc-row" data-rel="${esc(x.rel)}" data-brain="${esc(x.brain_path)}">
        <div class="ov-cc-main">
          <button type="button" class="ov-cc-name" title="${esc(x.rel)}">
            ${ic("file-text")}<span>${esc(x.ten)}</span>
          </button>
          <div class="ov-cc-sub">${esc(x.phong || x.brain)} · ${esc(x.rel)} · ${esc(t("ov.cc_created", { ngay: x.tao || "-", gio: x.gio }))}</div>
        </div>
        <div class="ov-cc-right">
          <span class="ov-cc-age">${esc(choBaoLau(x))}</span>
          ${pill("wait", t("ov.cc_state_draft"))}
          <button type="button" class="ov-cc-no" title="${esc(t("ov.cc_reject_tip"))}">${ic("trash-2")} ${esc(t("ov.cc_reject"))}</button>
          <button type="button" class="ov-cc-ok">${ic("check")} ${esc(t("ov.cc_approve"))}</button>
        </div>
      </div>`;
    const hangDaDuyet = (x) => `
      <div class="ov-cc-row${x.da_xem ? " seen" : ""}" data-rel="${esc(x.rel)}" data-brain="${esc(x.brain_path)}">
        <div class="ov-cc-main">
          <button type="button" class="ov-cc-name" title="${esc(x.rel)}">
            ${ic("file-text")}<span>${esc(x.ten)}</span>
          </button>
          <div class="ov-cc-sub">${esc(x.phong || x.brain)} · ${esc(x.rel)} · ${esc(x.ngay || "")} ${esc(x.gio)}</div>
        </div>
        <div class="ov-cc-right">
          ${x.moi_duyet ? pill("good", t("ov.cc_just")) : pill("good", t("ov.cc_state_done"))}
          <button type="button" class="ov-cc-seen" aria-pressed="${x.da_xem ? "true" : "false"}">
            ${ic(x.da_xem ? "circle-check" : "circle")}<span>${esc(t(x.da_xem ? "ov.cc_seen" : "ov.cc_mark"))}</span>
          </button>
        </div>
      </div>`;

    // Nhóm 2 và 3 gom theo phòng để đọc được danh sách dài nhiều brain.
    const gomPhong = (ds) => {
      const m = new Map();
      ds.forEach((x) => { const k = x.phong || x.brain; if (!m.has(k)) m.set(k, []); m.get(k).push(x); });
      return [...m.entries()];
    };
    const khoiPhong = (ds, ve) => gomPhong(ds).map(([phong, xs]) => `
      <div class="ov-cc-phong">
        <div class="ov-cc-phead"><b>${esc(phong)}</b><span class="ov-dim">${esc(t("ov.cc_count", { so: xs.length }))}</span>
          ${xs.some((x) => x.da_xem === false) ? `<span class="ov-cc-badge">${esc(t("ov.cc_unseen", { so: xs.filter((x) => !x.da_xem).length }))}</span>` : ""}</div>
        <div class="ov-cc-list">${xs.map(ve).join("")}</div>
      </div>`).join("");

    const nhom1 = moi.length ? `<div class="ov-cc-khoi">${moi.map(hangNhap).join("")}</div>`
      : `<div class="ov-empty">${ic("circle-check")} ${esc(t("ov.cc_empty_g1"))}</div>`;
    const nhom2 = cho.length ? `<div class="ov-cc-khoi">${khoiPhong(cho, hangNhap)}</div>`
      : `<div class="ov-empty">${ic("circle-check")} ${esc(t("ov.cc_empty_q"))}</div>`;
    const nhom3 = da.length ? `<div class="ov-cc-khoi">${khoiPhong(da, hangDaDuyet)}</div>`
      : `<div class="ov-empty">${esc(t("ov.cc_empty_g3"))}</div>`;

    const canhBao = lech.length ? `<div class="ov-cc-lech">
        ${ic("triangle-alert")}<div><b>${esc(t("ov.cc_merge"))}</b>
        <span>${esc(t("ov.cc_merge_d", { so: lech.length }))}</span></div>
        <button type="button" class="ov-secondary" id="ovCcMerge">${ic("git-branch")} ${esc(t("ov.cc_merge"))}</button>
      </div>` : "";
    const msg = _ccMsg ? `<div class="ov-cc-msg ${_ccMsg.ok ? "ok" : "err"}">${ic(_ccMsg.ok ? "circle-check" : "triangle-alert")} ${esc(_ccMsg.text)}</div>` : "";

    el.innerHTML = `<div class="ov-page">
      <div class="ov-toolbar">
        <span class="ov-synced">${esc(t("ov.cc_sum", { cho: d.tong_cho || 0, moi: moi.length, xong: da.length }))}</span>
        <button type="button" class="ov-refresh" id="ovCcRefresh">${ic("rotate-cw")} ${esc(t("ov.refresh"))}</button></div>
      ${msg}${canhBao}
      ${panel(t("ov.cc_g1"), t("ov.cc_g1_d"), nhom1)}
      ${panel(t("ov.cc_g2"), t("ov.cc_g2_d"), nhom2)}
      ${panel(t("ov.cc_g3"), t("ov.cc_g3_d"), nhom3)}
    </div>`;

    el.querySelector("#ovCcRefresh").onclick = () => { _ccMsg = null; renderChungCat(el); };
    const nutGop = el.querySelector("#ovCcMerge");
    if (nutGop) nutGop.onclick = async () => {
      nutGop.disabled = true;
      try {
        const res = await fetch("/api/joyce/v1/overview/chung-cat/gop-thu-muc", {
          method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json" }, body: "{}",
        });
        const dj = await res.json().catch(() => ({}));
        _ccMsg = res.ok && dj.ok !== false
          ? { ok: true, text: t("ov.cc_merge_done", { so: dj.moved || 0 }) }
          : { ok: false, text: t("ov.cc_fail", { loi: ": " + ((dj && dj.error) || res.status) }) };
      } catch (e) { _ccMsg = { ok: false, text: t("ov.cc_merge_fail") }; }
      if (el.isConnected) renderChungCat(el);
    };

    el.querySelectorAll(".ov-cc-row").forEach((row) => {
      const brain = row.dataset.brain, rel = row.dataset.rel;
      row.querySelector(".ov-cc-name").onclick = () => {
        if (window.JoyceFileEditor) window.JoyceFileEditor.open(rel, { brain });
      };
      const nutDuyet = row.querySelector(".ov-cc-ok");
      if (nutDuyet) nutDuyet.onclick = async () => {
        nutDuyet.disabled = true;
        nutDuyet.innerHTML = esc(t("ov.cc_approving"));
        try {
          const res = await fetch("/api/joyce/v1/overview/chung-cat/duyet", {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ brain_path: brain, rel }),
          });
          const dj = await res.json().catch(() => ({}));
          _ccMsg = res.ok && dj.ok !== false
            ? { ok: true, text: t("ov.cc_done", { ten: dj.ten || rel, path: dj.rel_moi || "" }) +
                (dj.nguon ? " " + t("ov.cc_done_src", { nguon: dj.nguon }) : "") }
            : { ok: false, text: t("ov.cc_fail", { loi: ": " + ((dj && dj.error) || res.status) }) };
        } catch (e) { _ccMsg = { ok: false, text: t("ov.cc_fail", { loi: "" }) }; }
        if (el.isConnected) renderChungCat(el);
      };
      const nutXoa = row.querySelector(".ov-cc-no");
      if (nutXoa) nutXoa.onclick = async () => {
        const ten = row.querySelector(".ov-cc-name span").textContent;
        // Luôn hỏi trước khi xoá - thiếu JoyceDialog thì rơi về confirm() của trình duyệt.
        const hoi = window.JoyceDialog
          ? await JoyceDialog.confirm(t("ov.cc_reject_q", { ten }),
                                      { kind: "err", okText: t("ov.cc_reject") })
          : window.confirm(t("ov.cc_reject_q", { ten }));
        if (!hoi) return;
        nutXoa.disabled = true;
        nutXoa.innerHTML = esc(t("ov.cc_rejecting"));
        try {
          const res = await fetch("/api/joyce/v1/overview/chung-cat/xoa", {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ brain_path: brain, rel }),
          });
          const dj = await res.json().catch(() => ({}));
          _ccMsg = res.ok && dj.ok !== false
            ? { ok: true, text: dj.nguon_xoa
                  ? t("ov.cc_reject_done2", { ten: dj.ten || rel, nguon: dj.nguon_xoa })
                  : t("ov.cc_reject_done", { ten: dj.ten || rel }) }
            : { ok: false, text: t("ov.cc_fail", { loi: ": " + ((dj && dj.error) || res.status) }) };
        } catch (e) { _ccMsg = { ok: false, text: t("ov.cc_fail", { loi: "" }) }; }
        if (el.isConnected) renderChungCat(el);
      };
      const nut = row.querySelector(".ov-cc-seen");
      if (nut) nut.onclick = async () => {
        const dangXem = !row.classList.contains("seen");
        nut.disabled = true;
        let ok = false;
        try {
          const res = await fetch("/api/joyce/v1/overview/chung-cat/xem", {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ brain_path: brain, rel, da_xem: dangXem }),
          });
          ok = res.ok;
        } catch (e) { ok = false; }
        nut.disabled = false;
        if (ok) renderChungCat(el);
      };
    });
    ganDieuHuong(el);
  }

  const VIEWS = { command: renderCommand, departments: renderDepartments, calendar: renderCalendar, reports: renderReports, chungcat: renderChungCat };
  window.JoyceOverview = {
    VIEWS: Object.keys(VIEWS),
    render(el, view) { return (VIEWS[view] || renderCommand)(el); },
  };
})();
