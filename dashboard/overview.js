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
  function moBrain(path, ten) {
    const sel = document.getElementById("graphSource");
    if (!sel || !path) return;
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
    go("files");
  }
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
    const kpis = (d.kpis || []).map((k) =>
      `<article class="ov-kpi"><div class="ov-kpi-top"><span>${esc(t(KPI_KEY[k.key] || k.key))}</span><span>${esc(t(KPI_SRC[k.source] || k.source))}</span></div>
       <div class="ov-kpi-v">${so(k.value)}</div><div class="ov-kpi-m ${k.tone || ""}">${esc(kpiMeta(k))}</div></article>`).join("");
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
  // PHÒNG BAN
  // ============================================================
  let _deptBrand = "all";
  function deptCard(p) {
    const c = p.tasks;
    const so3 = c ? `<div class="ov-dstats"><span><b>${so(c.done24)}</b> ${esc(t("ov.ds_done"))}</span><span><b>${so(c.open)}</b> ${esc(t("ov.ds_open"))}</span><span><b>${so(c.blocked)}</b> ${esc(t("ov.ds_blocked"))}</span></div>` : "";
    return `<button type="button" class="ov-dcard" data-dept="${esc(p.id)}"><div class="ov-dcard-top">${pill(STATUS_TONE[p.status], t(ST_KEY[p.status] || "ov.st_empty"))}<small>${esc(p.khoi)}</small></div>
      <h3>${esc(p.ten)}</h3><p>${esc(t("ov.dc_line", { nguon: p.nguon, wiki: p.wiki, nv: p.nhan_vien }))}</p>${so3}</button>`;
  }
  function moDrawer(p) {
    const old = document.getElementById("ovDrawer");
    if (old) old.remove();
    const c = p.tasks || {};
    const w = document.createElement("div");
    w.id = "ovDrawer";
    w.innerHTML = `<div class="ov-backdrop"></div><aside class="ov-drawer" role="dialog" aria-modal="true" aria-label="${esc(p.ten)}">
      <div class="ov-drawer-head"><div><span class="ov-eyebrow">${esc(p.brand)} · ${esc(p.khoi)}</span><h2>${esc(p.ten)}</h2></div><button type="button" class="ov-close" aria-label="${esc(t("common.close"))}">${ic("x")}</button></div>
      <div class="ov-drawer-body">${pill(STATUS_TONE[p.status], t(ST_KEY[p.status] || "ov.st_empty"))}
        <div class="ov-dmetric">${[["ov.ds_done", c.done24], ["ov.ds_open", c.open], ["ov.ds_review", c.review], ["ov.ds_blocked", c.blocked], ["ov.mem_sources", p.nguon], ["ov.mem_wiki", p.wiki]]
          .map(([k, v]) => `<div><strong>${v == null ? "-" : so(v)}</strong><span>${esc(t(k))}</span></div>`).join("")}</div>
        ${p.agent ? `<p class="ov-dim">${ic("bot")} ${esc(p.agent)}</p>` : ""}
        <div class="ov-deeplinks">
          ${p.has_brain ? `<button type="button" class="ov-deep" data-act="brain"><strong>${esc(t("ov.dl_brain"))}</strong><span>${esc(p.brain)}</span></button>` : `<div class="ov-dim">${esc(t("ov.dl_nobrain"))}</div>`}
          <button type="button" class="ov-deep" data-act="camnang"><strong>${esc(t("ov.dl_camnang"))}</strong><span>${esc(t("ov.dl_camnang_d"))}</span></button>
          <button type="button" class="ov-deep" data-act="ask"><strong>${esc(t("ov.dl_ask"))}</strong><span>${esc(t("ov.dl_ask_d"))}</span></button>
          <button type="button" class="ov-deep" data-act="staff"><strong>${esc(t("ov.dl_staff"))}</strong><span>${esc(t("ov.dl_staff_d"))}</span></button>
        </div></div></aside>`;
    document.body.appendChild(w);
    const dong = () => { w.remove(); document.removeEventListener("keydown", onKey); };
    const onKey = (e) => { if (e.key === "Escape") dong(); };
    document.addEventListener("keydown", onKey);
    w.querySelector(".ov-backdrop").onclick = dong;
    w.querySelector(".ov-close").onclick = dong;
    w.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => {
      const a = b.dataset.act;
      dong();
      if (a === "brain") moBrain(p.brain_path, p.ten);
      else if (a === "camnang") goSub("camnang", "phongban");
      else if (a === "staff") go("staff");
      else hoiJoyce(t("ov.dl_ask_q", { phong: p.ten }));
    }));
    setTimeout(() => { try { w.querySelector(".ov-close").focus(); } catch (e) {} }, 30);
  }
  async function renderDepartments(el) {
    el.innerHTML = loading();
    const r = await api("/api/joyce/v1/overview/departments");
    if (!el.isConnected) return;
    if (!r.ok) { el.innerHTML = `<div class="ov-page">${loiTrang(r.status === 403 ? t("ov.staff_denied") : t("ov.err_load"))}</div>`; return; }
    const d = r.data, units = d.units || [], phong = d.phong || [];
    if (!phong.length) {
      el.innerHTML = `<div class="ov-page"><div class="ov-empty big">${esc(t("ov.units_empty"))} ${linkBtn("staff", t("ov.units_go"))}</div></div>`;
      ganDieuHuong(el);
      return;
    }
    if (_deptBrand !== "all" && !units.some((u) => u.id === _deptBrand)) _deptBrand = "all";
    // Phòng cần nhìn trước lên đầu: có việc kẹt > chờ duyệt > ổn định > chưa có dữ liệu > chưa có brain.
    const HANG = { risk: 0, error: 1, wait: 2, good: 3, empty: 4, nobrain: 5 };
    const ds = phong.filter((p) => _deptBrand === "all" || p.brand_id === _deptBrand)
      .sort((a, b) => (HANG[a.status] ?? 9) - (HANG[b.status] ?? 9));
    const tabs = [["all", t("ov.all_units")]].concat(units.map((u) => [u.id, u.ten]));
    el.innerHTML = `<div class="ov-page">
      <div class="ov-toolbar"><div class="ov-chips">${tabs.map(([id, ten]) => `<button type="button" class="ov-chip" data-brand="${esc(id)}" aria-pressed="${id === _deptBrand}">${esc(ten)}</button>`).join("")}</div>
        <span class="ov-synced">${esc(t("ov.synced", { gio: gioCapNhat(d.generated_at) }))}</span></div>
      <div class="ov-unitsum">${units.filter((u) => _deptBrand === "all" || u.id === _deptBrand).map((u) => {
        const tk = u.tasks || {};
        return `<div class="ov-usum"><b>${esc(u.ten)}</b>${pill(STATUS_TONE[u.status], t(ST_KEY[u.status]))}<span>${esc(t("ov.unit_line", { phong: u.phong, dulieu: u.co_du_lieu, xong: tk.done24 || 0, mo: tk.open || 0, ket: tk.blocked || 0 }))}</span></div>`;
      }).join("")}</div>
      ${panel(t("ov.p_alldept"), t("ov.p_alldept_d"), `<div class="ov-dgrid">${ds.map(deptCard).join("")}</div>`)}</div>`;
    el.querySelectorAll("[data-brand]").forEach((b) => (b.onclick = () => { _deptBrand = b.dataset.brand; renderDepartments(el); }));
    el.querySelectorAll("[data-dept]").forEach((b) => (b.onclick = () => moDrawer(phong.find((p) => p.id === b.dataset.dept))));
    ganDieuHuong(el);
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

  const VIEWS = { command: renderCommand, departments: renderDepartments, calendar: renderCalendar, reports: renderReports };
  window.JoyceOverview = {
    VIEWS: Object.keys(VIEWS),
    render(el, view) { return (VIEWS[view] || renderCommand)(el); },
  };
})();
