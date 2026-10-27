(function (host) {
  "use strict";

  const K = Object.freeze({
    title: "crm.title",
    subtitle: "crm.subtitle",
    syncNotice: "crm.sync_notice",
    guide: "crm.guide",
    guideText: "crm.guide_text",
    contacts: "crm.contacts",
    pipeline: "crm.pipeline",
    todos: "crm.todos",
    contactCount: "crm.kpi.contacts",
    bought: "crm.kpi.bought",
    trackingValue: "crm.kpi.tracking_value",
    opportunities: "crm.kpi.opportunities",
    wonValue: "crm.kpi.won_value",
    winRate: "crm.kpi.win_rate",
    money: "crm.money",
    openTodos: "crm.kpi.open_todos",
    overdue: "crm.kpi.overdue",
    today: "crm.kpi.today",
    room: "crm.room",
    allRooms: "crm.all_rooms",
    readonly: "crm.readonly",
    enableRoom: "crm.enable_room",
    quickAi: "crm.quick_ai",
    quickAiHint: "crm.quick_ai_hint",
    pasteChat: "crm.paste_chat",
    readInfo: "crm.read_info",
    manualEntry: "crm.manual_entry",
    search: "crm.search",
    deletedContacts: "crm.deleted_contacts",
    importInbox: "crm.import_inbox",
    newContact: "crm.new_contact",
    emptyContacts: "crm.empty_contacts",
    contactDetails: "crm.contact_details",
    selectContact: "crm.select_contact",
    back: "crm.back",
    name: "crm.name",
    phone: "crm.phone",
    email: "crm.email",
    company: "crm.company",
    source: "crm.source",
    note: "crm.note",
    tags: "crm.tags",
    departments: "crm.departments",
    profile: "crm.profile",
    need: "crm.profile.need",
    budget: "crm.profile.budget",
    deadline: "crm.profile.deadline",
    objection: "crm.profile.objection",
    nextStep: "crm.profile.next_step",
    summary: "crm.profile.summary",
    locked: "crm.locked",
    edit: "crm.edit",
    save: "crm.save",
    cancel: "crm.cancel",
    remove: "crm.remove",
    restore: "crm.restore",
    delete: "crm.delete",
    addRoom: "crm.add_room",
    extract: "crm.extract",
    remember: "crm.remember",
    events: "crm.events",
    noEvents: "crm.no_events",
    deals: "crm.deals",
    noDeals: "crm.no_deals",
    proposals: "crm.proposals",
    noProposals: "crm.no_proposals",
    approveSelected: "crm.approve_selected",
    dismiss: "crm.dismiss",
    stage: "crm.stage",
    addStage: "crm.add_stage",
    renameStage: "crm.rename_stage",
    stageName: "crm.stage_name",
    chooseRoomPipeline: "crm.choose_room_pipeline",
    openContact: "crm.open_contact",
    newDeal: "crm.new_deal",
    dealTitle: "crm.deal_title",
    value: "crm.value",
    contact: "crm.contact",
    moveTo: "crm.move_to",
    emptyStage: "crm.empty_stage",
    due: "crm.due",
    status: "crm.status",
    open: "crm.open",
    done: "crm.done",
    all: "crm.all",
    addTodo: "crm.add_todo",
    todoTitle: "crm.todo_title",
    noTodos: "crm.no_todos",
    overdueLabel: "crm.overdue_label",
    todayLabel: "crm.today_label",
    aiDraft: "crm.ai_draft",
    reviewDraft: "crm.review_draft",
    createContact: "crm.create_contact",
    inbox: "crm.inbox",
    inboxSearch: "crm.inbox_search",
    import: "crm.import",
    emptyInbox: "crm.empty_inbox",
    segments: "crm.segments",
    autoExtract: "crm.auto_extract",
    autoOff: "crm.auto_off",
    autoReview: "crm.auto_review",
    autoApply: "crm.auto_apply",
    afterMessages: "crm.after_messages",
    update: "crm.update",
    loading: "crm.loading",
    retry: "crm.retry",
    genericError: "crm.generic_error",
    forbidden: "crm.forbidden",
    needRestart: "crm.need_restart",
    required: "crm.required",
    confirmDelete: "crm.confirm_delete",
    confirmRemoveStage: "crm.confirm_remove_stage",
    confirmRemoveRoom: "crm.confirm_remove_room",
    saved: "crm.saved",
    imported: "crm.imported",
    moved: "crm.moved",
    extracted: "crm.extracted",
    remembered: "crm.remembered",
    settingsSaved: "crm.settings_saved",
    roomUpdated: "crm.room_updated",
    proposalApproved: "crm.proposal_approved",
    proposalDismissed: "crm.proposal_dismissed",
    untitled: "crm.untitled",
    noValue: "crm.no_value",
    messages: "crm.messages",
    modeOff: "crm.mode.off",
    modeReview: "crm.mode.review",
    modeAuto: "crm.mode.auto"
  });

  const PROFILE_KEYS = Object.freeze({
    nhu_cau: K.need,
    ngan_sach: K.budget,
    han: K.deadline,
    phan_doi: K.objection,
    buoc_tiep: K.nextStep,
    tom_tat: K.summary
  });

  const CSS = `
    .jcrm{color:var(--text);min-width:0;font:inherit}
    .jcrm *{box-sizing:border-box}
    .jcrm :where(button,input,select,textarea){font-family:inherit;line-height:1.3}
    .jcrm-field,.jcrm-select,.jcrm-textarea{font-size:12px}
    .jcrm button{cursor:pointer}
    .jcrm-head{display:flex;align-items:flex-start;gap:12px;margin:4px 0 18px}
    .jcrm-head-icon{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;background:var(--accent-wash);color:var(--accent);flex:0 0 auto}
    .jcrm-icon svg{width:20px;height:20px;display:block}
    .jcrm-title{margin:0 0 4px;font-size:23px;line-height:1.2}
    .jcrm-subtitle{margin:0;color:var(--text2);font-size:13px;line-height:1.5;max-width:760px}
    .jcrm-head-actions{margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
    .jcrm-demo{border:1px solid color-mix(in srgb,var(--green) 32%,var(--line));background:color-mix(in srgb,var(--green) 8%,var(--card));border-radius:13px;padding:11px 13px;display:flex;align-items:center;gap:10px;margin-bottom:16px;color:var(--text2);font-size:12px}
    .jcrm-demo .jcrm-icon{color:var(--green)}
    .jcrm-guide{margin-bottom:14px}
    .jcrm-guide summary{cursor:pointer;color:var(--accent);font-size:12px;font-weight:700}
    .jcrm-guide p{font-size:11px;color:var(--text2);line-height:1.5;margin:10px 0 0}
    .jcrm-field,.jcrm-select,.jcrm-textarea{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:9px;padding:9px 10px;outline:none;min-width:0}
    .jcrm-field:focus,.jcrm-select:focus,.jcrm-textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 14%,transparent)}
    .jcrm-textarea{width:100%;min-height:84px;resize:vertical}
    .jcrm-btn{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:9px;padding:9px 12px;font-weight:700;font-size:12px;display:inline-flex;gap:7px;align-items:center;justify-content:center}
    .jcrm-btn svg{width:15px;height:15px}
    .jcrm-btn-primary{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
    .jcrm-btn-danger{background:var(--danger-wash);color:var(--danger-ink);border-color:color-mix(in srgb,var(--danger-ink) 28%,transparent)}
    .jcrm-btn-ghost{background:transparent;border-color:transparent;color:var(--text2)}
    .jcrm-btn-small{padding:6px 8px;font-size:11px}
    .jcrm-chip{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:4px 8px;background:var(--wash);color:var(--text2);font-size:10px;line-height:1.2}
    .jcrm-chip-accent{background:var(--accent-wash);color:var(--accent)}
    .jcrm-chip-danger{background:var(--danger-wash);color:var(--danger-ink)}
    .jcrm-chip-warn{background:color-mix(in srgb,var(--warn-ink) 14%,transparent);color:var(--warn-ink)}
    .jcrm-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px}
    .jcrm-kpi{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:14px;display:flex;gap:11px;min-height:92px;min-width:0}
    .jcrm-kpi-icon{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:var(--accent-wash);color:var(--accent);flex:0 0 auto}
    .jcrm-kpi:nth-child(2) .jcrm-kpi-icon{background:color-mix(in srgb,var(--info) 15%,transparent);color:var(--info)}
    .jcrm-kpi:nth-child(3) .jcrm-kpi-icon{background:color-mix(in srgb,var(--green) 15%,transparent);color:var(--green)}
    .jcrm-kpi:nth-child(4) .jcrm-kpi-icon{background:color-mix(in srgb,var(--warn-ink) 15%,transparent);color:var(--warn-ink)}
    .jcrm-kpi small{display:block;color:var(--text2);font-size:11px}
    .jcrm-kpi strong{display:block;font-size:19px;margin:2px 0;overflow-wrap:anywhere}
    .jcrm-kpi em{font-style:normal;color:var(--text3);font-size:10px}
    .jcrm-tabs{display:flex;gap:5px;align-items:center;background:var(--wash);border-radius:11px;padding:4px;margin:2px 0 16px;overflow:auto;max-width:100%;scrollbar-width:none}
    .jcrm-tabs::-webkit-scrollbar{display:none}
    .jcrm-tab{border:0;background:transparent;color:var(--text2);border-radius:8px;padding:8px 11px;white-space:nowrap;font-size:12px}
    .jcrm-tab.is-active{background:var(--card);color:var(--text);font-weight:750;box-shadow:0 1px 3px color-mix(in srgb,var(--text) 10%,transparent)}
    .jcrm-panel{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:14px;min-width:0}
    .jcrm-panel h3,.jcrm-panel h4{margin:0 0 12px}
    .jcrm-toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
    .jcrm-grow{flex:1 1 220px}
    .jcrm-grid-two{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,.9fr);gap:14px;align-items:start}
    .jcrm-ai{margin-bottom:12px}
    .jcrm-ai p{margin:3px 0 10px;color:var(--text2);font-size:11px}
    .jcrm-contact-list{border:1px solid var(--line);border-radius:13px;overflow:hidden}
    .jcrm-contact-row{display:grid;grid-template-columns:38px minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px;border:0;border-bottom:1px solid var(--line);width:100%;background:var(--card);color:var(--text);text-align:left}
    .jcrm-contact-row:last-child{border-bottom:0}
    .jcrm-contact-row:hover,.jcrm-contact-row.is-active{background:var(--accent-wash)}
    .jcrm-avatar{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:color-mix(in srgb,var(--accent) 20%,transparent);color:var(--accent);font-size:11px;font-weight:800}
    .jcrm-contact-row b,.jcrm-contact-row small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .jcrm-contact-row small{font-size:10px;color:var(--text2);margin-top:2px}
    .jcrm-detail-head{display:flex;gap:10px;align-items:flex-start;margin-bottom:14px}
    .jcrm-detail-head .jcrm-avatar{width:46px;height:46px}
    .jcrm-detail-head h3{margin:2px 0}
    .jcrm-detail-head p{margin:0;color:var(--text2);font-size:11px}
    .jcrm-detail-actions{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
    .jcrm-section{padding:14px 0;border-top:1px solid var(--line)}
    .jcrm-section:first-of-type{border-top:0}
    .jcrm-section-title{display:flex;align-items:center;gap:8px;margin-bottom:10px}
    .jcrm-section-title h4{margin:0;font-size:12px}
    .jcrm-profile{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
    .jcrm-profile-item{background:var(--wash);border-radius:10px;padding:10px;min-width:0}
    .jcrm-profile-item small{display:block;color:var(--text2);font-size:10px;margin-bottom:4px}
    .jcrm-profile-item span{font-size:12px;overflow-wrap:anywhere}
    .jcrm-room-chips{display:flex;gap:6px;flex-wrap:wrap}
    .jcrm-room-chip{display:inline-flex;align-items:center;gap:5px;background:var(--accent-wash);color:var(--accent);border-radius:999px;padding:5px 8px;font-size:10px}
    .jcrm-room-chip button{border:0;background:transparent;color:inherit;padding:0;line-height:1}
    .jcrm-timeline{display:grid;gap:8px}
    .jcrm-event{border-left:2px solid var(--line);padding-left:10px;font-size:11px;color:var(--text2)}
    .jcrm-event b{color:var(--text)}
    .jcrm-proposal{border:1px solid var(--line);border-radius:11px;padding:10px;margin-bottom:8px}
    .jcrm-proposal-fields{display:grid;gap:6px;margin:8px 0}
    .jcrm-check{display:flex;align-items:flex-start;gap:7px;font-size:11px}
    .jcrm-pipeline-wrap{overflow-x:auto;max-width:100%;padding-bottom:6px}
    .jcrm-pipeline{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(250px,1fr);gap:10px;min-width:max-content}
    .jcrm-lane{background:var(--wash);border:1px solid var(--line);border-radius:13px;padding:10px;min-height:330px;max-width:320px}
    .jcrm-lane.is-over{border-color:var(--accent);box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 20%,transparent)}
    .jcrm-lane-head{display:flex;gap:7px;align-items:center;margin-bottom:9px}
    .jcrm-lane-head b{font-size:11px;flex:1}
    .jcrm-lane-total{font-size:10px;color:var(--text2)}
    .jcrm-deal{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:8px;font-size:11px}
    .jcrm-deal[draggable=true]{cursor:grab}
    .jcrm-deal b{display:block;margin-bottom:5px}
    .jcrm-deal-value{font-weight:800;color:var(--green);margin:5px 0}
    .jcrm-deal-actions{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}
    .jcrm-deal-actions .jcrm-select{width:100%;font-size:10px;padding:6px}
    .jcrm-todo{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px 0;border-bottom:1px solid var(--line)}
    .jcrm-todo:last-child{border-bottom:0}
    .jcrm-todo.is-done .jcrm-todo-title{text-decoration:line-through;color:var(--text3)}
    .jcrm-todo-title{font-size:12px;font-weight:700}
    .jcrm-todo-meta{font-size:10px;color:var(--text2);margin-top:4px;display:flex;gap:6px;flex-wrap:wrap}
    .jcrm-empty{border:1px dashed var(--line);border-radius:11px;padding:24px 12px;text-align:center;color:var(--text3);font-size:12px}
    .jcrm-alert{border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--wash);color:var(--text2);font-size:12px;margin-bottom:12px}
    .jcrm-alert-danger{background:var(--danger-wash);color:var(--danger-ink);border-color:color-mix(in srgb,var(--danger-ink) 25%,transparent)}
    .jcrm-toast{position:fixed;right:20px;bottom:20px;z-index:1000;background:var(--text);color:var(--card);border-radius:10px;padding:10px 13px;font-size:12px;box-shadow:0 12px 32px color-mix(in srgb,var(--text) 25%,transparent)}
    .jcrm-modal-backdrop{position:fixed;inset:0;z-index:999;background:color-mix(in srgb,var(--text) 58%,transparent);display:grid;place-items:center;padding:18px}
    .jcrm-modal{width:min(620px,100%);max-height:min(820px,92vh);overflow:auto;background:var(--card);color:var(--text);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 24px 70px color-mix(in srgb,var(--text) 35%,transparent)}
    .jcrm-modal-head{display:flex;align-items:center;gap:8px;margin-bottom:14px}
    .jcrm-modal-head h3{margin:0;flex:1}
    .jcrm-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .jcrm-form-grid label{font-size:11px;color:var(--text2)}
    .jcrm-form-grid label.is-wide{grid-column:1/-1}
    .jcrm-form-grid input,.jcrm-form-grid select,.jcrm-form-grid textarea{width:100%;margin-top:5px}
    .jcrm-modal-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:14px}
    .jcrm-skeleton{height:88px;border-radius:14px;background:linear-gradient(90deg,var(--wash),var(--card),var(--wash));background-size:220% 100%;animation:jcrmPulse 1.2s infinite}
    @keyframes jcrmPulse{to{background-position:-220% 0}}
    .jcrm-mobile-only{display:none}
    @media(max-width:1000px){.jcrm-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:820px){.jcrm-grid-two{grid-template-columns:1fr}.jcrm-detail-panel{display:none}.jcrm.is-mobile-detail .jcrm-contact-panel{display:none}.jcrm.is-mobile-detail .jcrm-detail-panel{display:block}.jcrm-mobile-only{display:inline-flex}.jcrm-profile{grid-template-columns:1fr}.jcrm-form-grid{grid-template-columns:1fr}.jcrm-form-grid label.is-wide{grid-column:auto}.jcrm-pipeline{grid-auto-columns:minmax(235px,82vw)}}
    @media(max-width:520px){.jcrm-kpis{grid-template-columns:1fr 1fr;gap:8px}.jcrm-kpi{padding:10px;min-height:78px}.jcrm-kpi-icon{width:34px;height:34px}.jcrm-kpi strong{font-size:15px}.jcrm-head-actions{margin-left:0;width:100%}.jcrm-head-actions .jcrm-select{flex:1}.jcrm-toolbar>*{max-width:100%}}
  `;

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function dinhDangTien(value) {
    const number = Number(value || 0);
    return Number.isFinite(number) ? Math.round(number).toLocaleString("vi-VN") : "0";
  }

  function trangThaiHan(todo) {
    if (!todo || todo.done) return "";
    if (todo.tre_han) return "late";
    if (todo.hom_nay) return "today";
    return todo.due ? "soon" : "";
  }

  function chiaTheoGiaiDoan(stages) {
    return (stages || []).map(function (g) {
      const ds = g.deals || [];
      return { key: g.key, label: g.label, kind: g.kind, count: ds.length,
               total: ds.reduce(function (a, d) { return a + (Number(d.value) || 0); }, 0), deals: ds };
    });
  }

  function chuCaiDau(ten) {
    const t = String(ten || "").trim();
    if (!t) return "?";
    const p = t.split(/\s+/);
    return (p.length > 1 ? p[0][0] + p[p.length - 1][0] : t.slice(0, 2)).toUpperCase();
  }

  const K_SUKIEN = { tao: "crm.ev_create", sua: "crm.ev_edit", deal: "crm.ev_deal", viec: "crm.ev_todo", phong: "crm.ev_dept",
                     trich: "crm.ev_extract", duyet: "crm.ev_approve", wiki: "crm.ev_wiki", xoa: "crm.ev_delete",
                     khoi_phuc: "crm.ev_restore" };

  function nhanSuKien(kind) {
    return K_SUKIEN[kind] ? tw(K_SUKIEN[kind]) : kind;
  }

  function timHanhDong(eventOrNode) {
    const node = eventOrNode && eventOrNode.target ? eventOrNode.target : eventOrNode;
    if (!node || !node.closest) return null;
    return node.closest("[data-action]");
  }

  function icon(name) {
    if (host && typeof host.ic === "function") return host.ic(name);
    return "";
  }

  function tw(key, vars) {
    if (host && typeof host.t === "function") {
      const translated = host.t(key, vars || {});
      if (translated != null && translated !== key) return translated;
    }
    try {
      const raw = require("./i18n/vi.json")[key] || key;
      return String(raw).replace(/\{(\w+)\}/g, function (m, name) { return vars && vars[name] != null ? String(vars[name]) : m; });
    } catch (e) { return key; }
  }

  function query(params) {
    const qs = new URLSearchParams();
    Object.keys(params || {}).forEach(function (key) {
      const value = params[key];
      if (value !== undefined && value !== null) qs.set(key, value);
    });
    const text = qs.toString();
    return text ? "?" + text : "";
  }

  function apiError(response) {
    const error = new Error(response.status === 403 ? K.forbidden : response.status === 404 ? K.needRestart : K.genericError);
    error.status = response.status;
    return error;
  }

  async function apiGet(path, params) {
    const response = await fetch(path + query(params), { credentials: "same-origin" });
    if (!response.ok) throw apiError(response);
    return response.json();
  }

  async function apiPost(path, values) {
    const body = new FormData();
    Object.keys(values || {}).forEach(function (key) {
      const value = values[key];
      body.append(key, value == null ? "" : String(value));
    });
    const response = await fetch(path, { method: "POST", body: body, credentials: "same-origin" });
    if (!response.ok) throw apiError(response);
    return response.json();
  }

  function createState() {
    return {
      root: null,
      me: null,
      brain: "",
      mode: "contacts",
      summary: null,
      contacts: [],
      selectedId: null,
      detail: null,
      pipeline: null,
      todos: [],
      proposals: [],
      segments: [],
      inbox: [],
      showDeleted: false,
      todoDone: "0",
      search: "",
      loading: false,
      error: null,
      draggedDealId: null,
      toastTimer: null
    };
  }

  let state = createState();

  function canWrite() { return !!(state.me && !state.me.chi_xem); }
  function canManage() { return !!(state.me && !state.me.chi_xem && (state.me.admin || state.me.quan_ly)); }
  function isAdmin() { return !!(state.me && !state.me.chi_xem && state.me.admin); }

  function button(labelKey, action, className, attrs, iconName) {
    return `<button type="button" class="jcrm-btn ${className || ""}" data-action="${esc(action)}" ${attrs || ""}>${iconName ? `<span class="jcrm-icon">${icon(iconName)}</span>` : ""}<span>${esc(tw(labelKey))}</span></button>`;
  }

  function toast(key, vars) {
    if (!state.root) return;
    const old = state.root.querySelector(".jcrm-toast");
    if (old) old.remove();
    const el = document.createElement("div");
    el.className = "jcrm-toast";
    el.textContent = tw(key, vars);
    state.root.appendChild(el);
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(function () { el.remove(); }, 2600);
  }

  function showError(error) {
    state.error = error && error.message && String(error.message).startsWith("crm.") ? error.message : K.genericError;
    renderBody();
  }

  function summaryCards() {
    const s = state.summary || {};
    const cards = [
      ["users", K.contactCount, dinhDangTien(s.lien_he), tw(K.bought, { count: dinhDangTien(s.da_mua) })],
      ["target", K.trackingValue, tw(K.money, { value: dinhDangTien(s.dang_theo) }), tw(K.opportunities, { count: dinhDangTien(s.so_co_hoi) })],
      ["circle-check", K.wonValue, tw(K.money, { value: dinhDangTien(s.da_chot) }), tw(K.winRate, { rate: s.ti_le_thang == null ? "0" : Math.round(Number(s.ti_le_thang) * 100) })],
      ["heart-handshake", K.openTodos, dinhDangTien(s.viec_mo), tw(K.overdue, { count: dinhDangTien(s.viec_tre) })]
    ];
    return `<div class="jcrm-kpis">${cards.map(function (card) {
      return `<div class="jcrm-kpi"><div class="jcrm-kpi-icon jcrm-icon">${icon(card[0])}</div><div><small>${esc(tw(card[1]))}</small><strong>${esc(card[2])}</strong><em>${esc(card[3])}</em></div></div>`;
    }).join("")}</div>`;
  }

  function roomOptions(selected, includeAll) {
    const rooms = state.me && Array.isArray(state.me.phong) ? state.me.phong : [];
    const all = includeAll && state.me && state.me.admin ? `<option value="" ${selected === "" ? "selected" : ""}>${esc(tw(K.allRooms))}</option>` : "";
    return all + rooms.filter(function (room) { return room.bat !== false; }).map(function (room) {
      return `<option value="${esc(room.brain)}" ${String(selected) === String(room.brain) ? "selected" : ""}>${esc(room.ten || room.brain)}</option>`;
    }).join("");
  }

  function renderShell() {
    const root = state.root;
    root.innerHTML = `<style>${CSS}</style><div class="jcrm-main"></div><div class="jcrm-modal-host"></div>`;
    renderBody();
  }

  function renderBody() {
    if (!state.root) return;
    const main = state.root.querySelector(".jcrm-main");
    if (!main) return;
    if (!state.me) {
      main.innerHTML = state.error ? `<div class="jcrm-alert jcrm-alert-danger">${esc(tw(state.error))}</div>${button(K.retry, "retry-init", "jcrm-btn-primary")}` : `<div class="jcrm-skeleton"></div>`;
      return;
    }
    const roomControl = `<select class="jcrm-select" data-action="change-room" aria-label="${esc(tw(K.room))}">${roomOptions(state.brain, true)}</select>`;
    const enable = isAdmin() && state.brain ? `<label class="jcrm-chip"><input type="checkbox" data-action="enable-room" ${currentRoomEnabled() ? "checked" : ""}>${esc(tw(K.enableRoom))}</label>` : "";
    const totals = state.summary || {};
    main.innerHTML = `<div class="jcrm-head"><div class="jcrm-head-icon jcrm-icon">${icon("users")}</div><div><h1 class="jcrm-title">${esc(tw(K.title))}</h1><p class="jcrm-subtitle">${esc(tw(K.subtitle))}</p></div></div>${state.error ? `<div class="jcrm-alert jcrm-alert-danger">${esc(tw(state.error))}</div>` : ""}<div class="jcrm-demo"><span class="jcrm-icon">${icon("sparkles")}</span><span>${esc(tw(K.syncNotice))}</span></div>${summaryCards()}<div class="jcrm-tabs" role="tablist"><button class="jcrm-tab ${state.mode === "contacts" ? "is-active" : ""}" data-action="mode" data-mode="contacts">${esc(tw(K.contacts))} ${esc(dinhDangTien(totals.lien_he))}</button><button class="jcrm-tab ${state.mode === "pipeline" ? "is-active" : ""}" data-action="mode" data-mode="pipeline">${esc(tw(K.pipeline))} ${esc(dinhDangTien(totals.so_co_hoi))}</button><button class="jcrm-tab ${state.mode === "todos" ? "is-active" : ""}" data-action="mode" data-mode="todos">${esc(tw(K.todos))} ${esc(dinhDangTien(totals.viec_mo))}</button><span style="flex:1 1 16px"></span>${state.me.chi_xem ? `<span class="jcrm-chip jcrm-chip-warn">${esc(tw(K.readonly))}</span>` : ""}${roomControl}${enable}${canManage() ? button(K.autoExtract, "open-settings", "jcrm-btn-small", "", "sparkles") : ""}</div><div class="jcrm-view">${viewHtml()}</div>`;
  }

  function currentRoomEnabled() {
    const room = state.me && state.me.phong ? state.me.phong.find(function (item) { return String(item.brain) === String(state.brain); }) : null;
    return !room || room.bat !== false;
  }

  function viewHtml() {
    if (state.loading) return `<div class="jcrm-skeleton"></div>`;
    if (state.mode === "pipeline") return pipelineView();
    if (state.mode === "todos") return todosView();
    return contactsView();
  }

  function contactsView() {
    const writeTools = canWrite() ? `${button(K.manualEntry, "new-contact", "")}` : "";
    const manageTools = canManage() ? `${button(K.importInbox, "open-inbox", "jcrm-btn-small")}${button(K.deletedContacts, "toggle-deleted", state.showDeleted ? "jcrm-btn-primary jcrm-btn-small" : "jcrm-btn-small")}` : "";
    return `<details class="jcrm-guide jcrm-panel"><summary>${esc(tw(K.guide))}</summary><p>${esc(tw(K.guideText))}</p></details><div class="jcrm-grid-two"><section class="jcrm-contact-panel"><div class="jcrm-ai jcrm-panel"><h3>${esc(tw(K.quickAi))}</h3><p>${esc(tw(K.quickAiHint))}</p><textarea class="jcrm-textarea" data-role="quick-text" placeholder="${esc(tw(K.pasteChat))}" ${canWrite() ? "" : "disabled"}></textarea><div class="jcrm-toolbar" style="margin-top:8px;margin-bottom:0">${canWrite() ? button(K.readInfo, "read-quick", "jcrm-btn-primary", "", "sparkles") : ""}${writeTools}</div></div><div class="jcrm-toolbar"><input class="jcrm-field jcrm-grow" data-role="contact-search" value="${esc(state.search)}" placeholder="${esc(tw(K.search))}">${canWrite() ? button(K.newContact, "new-contact", "jcrm-btn-primary") : ""}</div><div class="jcrm-toolbar">${manageTools}${button(K.segments, "open-segments", "")}</div>${contactListHtml()}</section><section class="jcrm-detail-panel jcrm-panel">${contactDetailHtml()}</section></div>`;
  }

  function contactListHtml() {
    if (!state.contacts.length) return `<div class="jcrm-empty">${esc(tw(K.emptyContacts))}</div>`;
    return `<div class="jcrm-contact-list">${state.contacts.map(function (contact) {
      const meta = [contact.company, contact.source].filter(Boolean).join(" · ");
      return `<button type="button" class="jcrm-contact-row ${String(state.selectedId) === String(contact.id) ? "is-active" : ""}" data-action="select-contact" data-id="${esc(contact.id)}"><span class="jcrm-avatar">${esc(chuCaiDau(contact.name))}</span><span><b>${esc(contact.name || tw(K.untitled))}</b><small>${esc(meta)}</small></span><span>${contact.da_chot ? `<span class="jcrm-chip jcrm-chip-accent">${esc(tw(K.done))}</span>` : ""}</span></button>`;
    }).join("")}</div>`;
  }

  function contactDetailHtml() {
    const data = state.detail;
    if (!data || !data.contact) return `<div class="jcrm-empty">${esc(tw(K.selectContact))}</div>`;
    const contact = data.contact;
    const profile = contact.profile || {};
    const locked = Array.isArray(contact.locked) ? contact.locked : [];
    const rooms = Array.isArray(contact.depts) ? contact.depts : [];
    const roomChips = rooms.map(function (brain) {
      const room = state.me.phong.find(function (item) { return String(item.brain) === String(brain); });
      return `<span class="jcrm-room-chip">${esc(room ? room.ten || room.brain : brain)}${canWrite() && rooms.length > 1 ? `<button type="button" data-action="remove-contact-room" data-brain="${esc(brain)}" aria-label="${esc(tw(K.remove))}">-</button>` : ""}</span>`;
    }).join("");
    const remainingRooms = (state.me.phong || []).filter(function (room) { return !rooms.includes(room.brain) && room.bat !== false; });
    const addRoom = canWrite() && remainingRooms.length ? `<select class="jcrm-select" data-action="add-contact-room"><option value="">${esc(tw(K.addRoom))}</option>${remainingRooms.map(function (room) { return `<option value="${esc(room.brain)}">${esc(room.ten || room.brain)}</option>`; }).join("")}</select>` : "";
    const profileHtml = Object.keys(PROFILE_KEYS).map(function (key) {
      return `<div class="jcrm-profile-item"><small>${esc(tw(PROFILE_KEYS[key]))}${locked.includes(key) ? ` · ${esc(tw(K.locked))}` : ""}</small><span>${esc(profile[key] || "-")}</span></div>`;
    }).join("");
    const events = Array.isArray(data.events) ? data.events : [];
    const eventHtml = events.length ? events.map(function (event) {
      const label = event.title || event.type || event.label || "";
      const detail = event.text || event.note || event.content || "";
      const time = event.time || event.created_at || event.at || "";
      return `<div class="jcrm-event"><b>${esc(label)}</b><div>${esc(detail)}</div><small>${esc(time)}</small></div>`;
    }).join("") : `<div class="jcrm-empty">${esc(tw(K.noEvents))}</div>`;
    const deals = Array.isArray(data.deals) ? data.deals : [];
    const dealHtml = deals.length ? deals.map(function (deal) {
      return `<div class="jcrm-deal"><b>${esc(deal.title || tw(K.untitled))}</b><div>${esc(dinhDangTien(deal.value))}</div><span class="jcrm-chip">${esc(stageLabel(deal.brain, deal.stage, data.stage_labels))}</span></div>`;
    }).join("") : `<div class="jcrm-empty">${esc(tw(K.noDeals))}</div>`;
    return `<button type="button" class="jcrm-btn jcrm-mobile-only" data-action="back-list">${esc(tw(K.back))}</button><div class="jcrm-detail-head"><span class="jcrm-avatar">${esc(chuCaiDau(contact.name))}</span><div><h3>${esc(contact.name || tw(K.untitled))}</h3><p>${esc([contact.company, contact.source].filter(Boolean).join(" · "))}</p></div><div class="jcrm-detail-actions">${canWrite() ? button(K.edit, "edit-contact", "jcrm-btn-small", `data-id="${esc(contact.id)}"`) : ""}${canWrite() ? button(K.extract, "extract-contact", "jcrm-btn-small", `data-id="${esc(contact.id)}"`, "sparkles") : ""}${canWrite() && state.brain ? button(K.remember, "remember-contact", "jcrm-btn-small", `data-id="${esc(contact.id)}"`) : ""}${canManage() ? button(state.showDeleted ? K.restore : K.delete, state.showDeleted ? "restore-contact" : "delete-contact", "jcrm-btn-small jcrm-btn-danger", `data-id="${esc(contact.id)}"`) : ""}</div></div><div class="jcrm-section"><div class="jcrm-section-title"><h4>${esc(tw(K.departments))}</h4></div><div class="jcrm-room-chips">${roomChips}${addRoom}</div></div><div class="jcrm-section"><div class="jcrm-section-title"><h4>${esc(tw(K.profile))}</h4></div><div class="jcrm-profile">${profileHtml}</div></div><div class="jcrm-section"><div class="jcrm-section-title"><h4>${esc(tw(K.deals))}</h4>${canWrite() ? `<button class="jcrm-btn jcrm-btn-small" data-action="new-deal" data-contact-id="${esc(contact.id)}">${esc(tw(K.newDeal))}</button>` : ""}</div>${dealHtml}</div><div class="jcrm-section"><div class="jcrm-section-title"><h4>${esc(tw(K.events))}</h4></div><div class="jcrm-timeline">${eventHtml}</div></div><div class="jcrm-section"><div class="jcrm-section-title"><h4>${esc(tw(K.proposals))}</h4></div>${proposalsHtml(data.proposals || [])}</div>`;
  }

  function stageLabel(brain, key, labels) {
    return labels && labels[brain] && labels[brain][key] ? labels[brain][key] : key || "";
  }

  function proposalsHtml(proposals) {
    if (!proposals.length) return `<div class="jcrm-empty">${esc(tw(K.noProposals))}</div>`;
    return proposals.map(function (proposal) {
      const fields = proposal.fields || {};
      return `<div class="jcrm-proposal" data-proposal-id="${esc(proposal.id)}"><b>${esc(proposal.contact_name || tw(K.aiDraft))}</b><div class="jcrm-proposal-fields">${Object.keys(fields).map(function (key) {
        return `<label class="jcrm-check"><input type="checkbox" data-role="proposal-field" value="${esc(key)}" checked ${canWrite() ? "" : "disabled"}><span><b>${esc(tw(PROFILE_KEYS[key] || K.profile))}</b>: ${esc(fields[key])}</span></label>`;
      }).join("")}</div>${canWrite() ? `<div class="jcrm-toolbar">${button(K.approveSelected, "approve-proposal", "jcrm-btn-primary jcrm-btn-small", `data-id="${esc(proposal.id)}"`)}${button(K.dismiss, "dismiss-proposal", "jcrm-btn-small", `data-id="${esc(proposal.id)}"`)}</div>` : ""}</div>`;
    }).join("");
  }

  function pipelineView() {
    if (!state.brain) return `<div class="jcrm-alert">${esc(tw(K.chooseRoomPipeline))}</div>`;
    const pipeline = state.pipeline || { stages: [] };
    return `<div class="jcrm-toolbar"><span class="jcrm-chip jcrm-chip-accent">${esc(tw(K.winRate, { rate: pipeline.ti_le_thang == null ? "0" : Math.round(Number(pipeline.ti_le_thang) * 100) }))}</span><span class="jcrm-chip">${esc(tw(K.trackingValue))}: ${esc(dinhDangTien(pipeline.dang_theo))}</span><span class="jcrm-chip">${esc(tw(K.wonValue))}: ${esc(dinhDangTien(pipeline.da_chot))}</span><span class="jcrm-grow"></span>${canWrite() ? button(K.newDeal, "new-deal", "jcrm-btn-primary") : ""}${canWrite() ? button(K.addStage, "add-stage", "") : ""}</div><div class="jcrm-pipeline-wrap"><div class="jcrm-pipeline">${(pipeline.stages || []).map(stageLaneHtml).join("")}</div></div>`;
  }

  function stageLaneHtml(stage) {
    const controls = canWrite() && stage.kind === "open" ? `<button type="button" class="jcrm-btn jcrm-btn-small" data-action="rename-stage" data-key="${esc(stage.key)}" data-label="${esc(stage.label)}">${esc(tw(K.edit))}</button><button type="button" class="jcrm-btn jcrm-btn-small jcrm-btn-danger" data-action="delete-stage" data-key="${esc(stage.key)}">-</button>` : "";
    const deals = stage.deals || [];
    return `<section class="jcrm-lane" data-stage="${esc(stage.key)}"><div class="jcrm-lane-head"><b>${esc(stage.label)}</b><span class="jcrm-chip">${esc(stage.count == null ? deals.length : stage.count)}</span>${controls}</div><div class="jcrm-lane-total">${esc(dinhDangTien(stage.total))}</div><div style="margin-top:9px">${deals.length ? deals.map(function (deal) { return dealCardHtml(deal); }).join("") : `<div class="jcrm-empty">${esc(tw(K.emptyStage))}</div>`}</div></section>`;
  }

  function dealCardHtml(deal) {
    const stages = state.pipeline && state.pipeline.stages ? state.pipeline.stages : [];
    return `<article class="jcrm-deal" draggable="${canWrite() ? "true" : "false"}" data-deal-id="${esc(deal.id)}"><b>${esc(deal.title || tw(K.untitled))}</b><div>${esc(deal.contact_name || "")}</div><div class="jcrm-deal-value">${esc(dinhDangTien(deal.value))}</div>${canWrite() ? `<select class="jcrm-select" data-action="move-deal" data-id="${esc(deal.id)}">${stages.map(function (stage) { return `<option value="${esc(stage.key)}" ${String(stage.key) === String(deal.stage) ? "selected" : ""}>${esc(stage.label)}</option>`; }).join("")}</select>` : ""}<div class="jcrm-deal-actions"><button type="button" class="jcrm-btn jcrm-btn-small" data-action="open-contact" data-id="${esc(deal.contact_id)}">${esc(tw(K.openContact))}</button>${canWrite() ? `<button type="button" class="jcrm-btn jcrm-btn-small jcrm-btn-danger" data-action="delete-deal" data-id="${esc(deal.id)}">${esc(tw(K.delete))}</button>` : ""}</div></article>`;
  }

  function todosView() {
    return `<div class="jcrm-toolbar"><select class="jcrm-select" data-action="todo-filter"><option value="0" ${state.todoDone === "0" ? "selected" : ""}>${esc(tw(K.open))}</option><option value="1" ${state.todoDone === "1" ? "selected" : ""}>${esc(tw(K.done))}</option><option value="" ${state.todoDone === "" ? "selected" : ""}>${esc(tw(K.all))}</option></select><span class="jcrm-grow"></span>${canWrite() ? button(K.addTodo, "new-todo", "jcrm-btn-primary") : ""}</div><div class="jcrm-panel">${state.todos.length ? state.todos.map(todoRowHtml).join("") : `<div class="jcrm-empty">${esc(tw(K.noTodos))}</div>`}</div>`;
  }

  function todoRowHtml(todo) {
    const dueState = trangThaiHan(todo);
    const badge = dueState === "late" ? `<span class="jcrm-chip jcrm-chip-danger">${esc(tw(K.overdueLabel))}</span>` : dueState === "today" ? `<span class="jcrm-chip jcrm-chip-warn">${esc(tw(K.todayLabel))}</span>` : "";
    return `<div class="jcrm-todo ${todo.done ? "is-done" : ""}"><input type="checkbox" data-action="toggle-todo" data-id="${esc(todo.id)}" ${todo.done ? "checked" : ""} ${canWrite() ? "" : "disabled"}><div><div class="jcrm-todo-title">${esc(todo.title)}</div><div class="jcrm-todo-meta"><span>${esc(todo.contact_name || "")}</span><span>${esc(todo.brain || "")}</span><span>${esc(todo.due || "")}</span>${badge}</div></div>${canWrite() ? `<button type="button" class="jcrm-btn jcrm-btn-small jcrm-btn-danger" data-action="delete-todo" data-id="${esc(todo.id)}">${esc(tw(K.delete))}</button>` : ""}</div>`;
  }

  function openModal(titleKey, content, actions) {
    const hostEl = state.root.querySelector(".jcrm-modal-host");
    hostEl.innerHTML = `<div class="jcrm-modal-backdrop" data-action="modal-backdrop"><div class="jcrm-modal" role="dialog" aria-modal="true"><div class="jcrm-modal-head"><h3>${esc(tw(titleKey))}</h3><button type="button" class="jcrm-btn jcrm-btn-ghost" data-action="close-modal">x</button></div>${content}<div class="jcrm-modal-actions">${actions || button(K.cancel, "close-modal", "")}</div></div></div>`;
  }

  function closeModal() {
    const hostEl = state.root && state.root.querySelector(".jcrm-modal-host");
    if (hostEl) hostEl.innerHTML = "";
  }

  function contactForm(contact, draft) {
    const data = Object.assign({}, contact || {}, draft || {});
    const draftProfile = draft ? `<div class="jcrm-section"><div class="jcrm-section-title"><h4>${esc(tw(K.reviewDraft))}</h4></div><div class="jcrm-profile">${Object.keys(PROFILE_KEYS).filter(function (key) { return data[key]; }).map(function (key) { return `<div class="jcrm-profile-item"><small>${esc(tw(PROFILE_KEYS[key]))}</small><span>${esc(data[key])}</span></div>`; }).join("")}</div></div>` : "";
    const fields = `<form data-role="contact-form" data-id="${esc(data.id || 0)}"><div class="jcrm-form-grid"><label class="is-wide">${esc(tw(K.name))}<input class="jcrm-field" name="name" value="${esc(data.name || "")}" required></label><label>${esc(tw(K.phone))}<input class="jcrm-field" name="phone" value="${esc(data.phone || "")}"></label><label>${esc(tw(K.email))}<input class="jcrm-field" name="email" value="${esc(data.email || "")}"></label><label>${esc(tw(K.company))}<input class="jcrm-field" name="company" value="${esc(data.company || "")}"></label><label>${esc(tw(K.source))}<input class="jcrm-field" name="source" value="${esc(data.source || "")}"></label><label class="is-wide">${esc(tw(K.tags))}<input class="jcrm-field" name="tags" value="${esc(Array.isArray(data.tags) ? data.tags.join(", ") : data.tags || "")}"></label><label class="is-wide">${esc(tw(K.departments))}<input class="jcrm-field" name="depts" value="${esc(Array.isArray(data.depts) ? data.depts.join(", ") : data.depts || state.brain || "")}"></label><label class="is-wide">${esc(tw(K.note))}<textarea class="jcrm-textarea" name="note">${esc(data.note || data.tom_tat || "")}</textarea></label></div>${draftProfile}</form>`;
    openModal(data.id ? K.edit : K.newContact, fields, `${button(K.cancel, "close-modal", "")}${button(K.save, "save-contact", "jcrm-btn-primary")}`);
  }

  function dealForm(deal, contactId) {
    const contacts = state.contacts || [];
    const stages = state.pipeline && state.pipeline.stages ? state.pipeline.stages : [];
    const content = `<form data-role="deal-form" data-id="${esc(deal && deal.id || 0)}"><div class="jcrm-form-grid"><label>${esc(tw(K.contact))}<select class="jcrm-select" name="contact_id" required>${contacts.map(function (contact) { return `<option value="${esc(contact.id)}" ${String(contactId || deal && deal.contact_id) === String(contact.id) ? "selected" : ""}>${esc(contact.name)}</option>`; }).join("")}</select></label><label>${esc(tw(K.stage))}<select class="jcrm-select" name="stage">${stages.map(function (stage) { return `<option value="${esc(stage.key)}">${esc(stage.label)}</option>`; }).join("")}</select></label><label class="is-wide">${esc(tw(K.dealTitle))}<input class="jcrm-field" name="title" value="${esc(deal && deal.title || "")}" required></label><label class="is-wide">${esc(tw(K.value))}<input class="jcrm-field" name="value" type="number" value="${esc(deal && deal.value || 0)}"></label></div></form>`;
    openModal(K.newDeal, content, `${button(K.cancel, "close-modal", "")}${button(K.save, "save-deal", "jcrm-btn-primary")}`);
  }

  function todoForm() {
    const content = `<form data-role="todo-form"><div class="jcrm-form-grid"><label>${esc(tw(K.contact))}<select class="jcrm-select" name="contact_id">${state.contacts.map(function (contact) { return `<option value="${esc(contact.id)}">${esc(contact.name)}</option>`; }).join("")}</select></label><label>${esc(tw(K.due))}<input class="jcrm-field" type="date" name="due"></label><label class="is-wide">${esc(tw(K.todoTitle))}<input class="jcrm-field" name="title" required></label></div></form>`;
    openModal(K.addTodo, content, `${button(K.cancel, "close-modal", "")}${button(K.save, "save-todo", "jcrm-btn-primary")}`);
  }

  function settingsModal() {
    const modes = [["off", K.autoOff], ["duyet", K.autoReview], ["auto", K.autoApply]];
    const content = `<form data-role="settings-form"><div class="jcrm-form-grid"><label>${esc(tw(K.autoExtract))}<select class="jcrm-select" name="che_do">${modes.map(function (mode) { return `<option value="${mode[0]}" ${state.me.che_do === mode[0] ? "selected" : ""}>${esc(tw(mode[1]))}</option>`; }).join("")}</select></label><label>${esc(tw(K.afterMessages))}<input class="jcrm-field" type="number" min="1" name="nguong" value="${esc(state.me.nguong || 1)}"></label></div></form>`;
    openModal(K.autoExtract, content, `${button(K.cancel, "close-modal", "")}${button(K.update, "save-settings", "jcrm-btn-primary")}`);
  }

  function stageModal(mode, key, label) {
    const content = `<form data-role="stage-form" data-key="${esc(key || "")}"><label>${esc(tw(K.stageName))}<input class="jcrm-field" style="width:100%;margin-top:5px" name="label" value="${esc(label || "")}" required></label></form>`;
    openModal(mode === "rename" ? K.renameStage : K.addStage, content, `${button(K.cancel, "close-modal", "")}${button(K.save, mode === "rename" ? "save-stage-name" : "save-stage", "jcrm-btn-primary")}`);
  }

  async function inboxModal() {
    openModal(K.inbox, `<div class="jcrm-skeleton"></div>`);
    try {
      const result = await apiGet("/crm/hop-thu", { q: "" });
      state.inbox = result.items || [];
      renderInboxModal();
    } catch (error) { showModalError(K.inbox, error); }
  }

  function renderInboxModal() {
    const rows = state.inbox.length ? state.inbox.map(function (item) {
      return `<div class="jcrm-contact-row"><span class="jcrm-avatar">${esc(chuCaiDau(item.name))}</span><span><b>${esc(item.name)}</b><small>${esc(item.channel || "")}</small></span>${button(K.import, "import-inbox", "jcrm-btn-primary jcrm-btn-small", `data-id="${esc(item.id)}"`)}</div>`;
    }).join("") : `<div class="jcrm-empty">${esc(tw(K.emptyInbox))}</div>`;
    const content = `<div class="jcrm-toolbar"><input class="jcrm-field jcrm-grow" data-role="inbox-search" placeholder="${esc(tw(K.inboxSearch))}"><button class="jcrm-btn" data-action="search-inbox">${esc(tw(K.search))}</button></div><div class="jcrm-contact-list">${rows}</div>`;
    openModal(K.inbox, content);
  }

  async function segmentsModal() {
    openModal(K.segments, `<div class="jcrm-skeleton"></div>`);
    try {
      const result = await apiGet("/crm/phan-khuc", { brain: state.brain });
      state.segments = result.items || [];
      const content = state.segments.length ? state.segments.map(function (segment) {
        return `<div class="jcrm-proposal"><b>${esc(segment.label)}</b><span class="jcrm-chip" style="margin-left:7px">${esc(segment.count)}</span><div class="jcrm-room-chips" style="margin-top:8px">${(segment.contacts || []).map(function (contact) { return `<button type="button" class="jcrm-chip" data-action="open-contact" data-id="${esc(contact.id)}">${esc(contact.name)}</button>`; }).join("")}</div></div>`;
      }).join("") : `<div class="jcrm-empty">${esc(tw(K.emptyContacts))}</div>`;
      openModal(K.segments, content);
    } catch (error) { showModalError(K.segments, error); }
  }

  function showModalError(titleKey, error) {
    const key = error && error.message && String(error.message).startsWith("crm.") ? error.message : K.genericError;
    openModal(titleKey, `<div class="jcrm-alert jcrm-alert-danger">${esc(tw(key))}</div>`);
  }

  function formValues(selector) {
    const form = state.root.querySelector(selector);
    if (!form) return null;
    const values = {};
    new FormData(form).forEach(function (value, key) { values[key] = value; });
    return values;
  }

  async function init() {
    state.loading = true;
    try {
      const meResult = await apiGet("/crm/me");
      state.me = meResult;
      state.brain = meResult.mac_dinh || (meResult.phong && meResult.phong[0] ? meResult.phong[0].brain : "");
      if (meResult.admin && !state.brain) state.brain = "";
      state.error = null;
      await loadCurrent(true);
    } catch (error) {
      state.me = null;
      state.error = error && error.message && String(error.message).startsWith("crm.") ? error.message : K.genericError;
    } finally {
      state.loading = false;
      renderBody();
    }
  }

  async function loadSummary() {
    const result = await apiGet("/crm/tong-quan", { brain: state.brain });
    state.summary = result;
  }

  async function loadContacts(autoSelect) {
    const result = await apiGet("/crm/lien-he", { brain: state.brain, q: state.search, da_xoa: state.showDeleted ? 1 : 0 });
    state.contacts = result.items || [];
    const currentExists = state.contacts.some(function (item) { return String(item.id) === String(state.selectedId); });
    if (!currentExists) { state.selectedId = null; state.detail = null; }
    if (autoSelect && !state.selectedId && state.contacts.length && !(host.matchMedia && host.matchMedia("(max-width: 820px)").matches)) {
      state.selectedId = state.contacts[0].id;
      await loadDetail(state.selectedId, false);
    }
  }

  async function loadDetail(id, rerender) {
    const result = await apiGet("/crm/lien-he/" + encodeURIComponent(id));
    state.detail = result;
    state.selectedId = id;
    if (rerender !== false) {
      state.root.classList.add("is-mobile-detail");
      renderBody();
    }
  }

  async function loadPipeline() {
    if (!state.brain) { state.pipeline = null; return; }
    state.pipeline = await apiGet("/crm/pipeline", { brain: state.brain });
  }

  async function loadTodos() {
    const result = await apiGet("/crm/viec", { brain: state.brain, contact_id: "", xong: state.todoDone });
    state.todos = result.items || [];
  }

  async function loadCurrent(autoSelect) {
    state.loading = true;
    renderBody();
    try {
      await loadSummary();
      if (state.mode === "contacts") await loadContacts(autoSelect);
      if (state.mode === "pipeline") { await Promise.all([loadContacts(false), loadPipeline()]); }
      if (state.mode === "todos") { await Promise.all([loadContacts(false), loadTodos()]); }
      state.error = null;
    } catch (error) {
      state.error = error && error.message && String(error.message).startsWith("crm.") ? error.message : K.genericError;
    } finally {
      state.loading = false;
      renderBody();
    }
  }

  async function perform(task, successKey, reload) {
    try {
      await task();
      if (successKey) toast(successKey);
      if (reload !== false) await loadCurrent(false);
    } catch (error) { showError(error); }
  }

  async function handleClick(event) {
    const target = timHanhDong(event);
    if (!target) return;
    const action = target.dataset.action;
    if (action === "modal-backdrop" && event.target === target) return closeModal();
    if (action === "close-modal") return closeModal();
    if (action === "retry-init") return init();
    if (action === "mode") { state.mode = target.dataset.mode; state.root.classList.remove("is-mobile-detail"); return loadCurrent(true); }
    if (action === "back-list") { state.root.classList.remove("is-mobile-detail"); return; }
    if (action === "select-contact") return perform(function () { return loadDetail(target.dataset.id); }, null, false);
    if (action === "new-contact") return contactForm(null, null);
    if (action === "edit-contact") return contactForm(state.detail && state.detail.contact, null);
    if (action === "read-quick") return readQuickDraft();
    if (action === "save-contact") return saveContact();
    if (action === "toggle-deleted") { state.showDeleted = !state.showDeleted; state.selectedId = null; state.detail = null; return loadCurrent(true); }
    if (action === "delete-contact") return removeContact(target.dataset.id, false);
    if (action === "restore-contact") return removeContact(target.dataset.id, true);
    if (action === "extract-contact") return perform(function () { return apiPost("/crm/trich", { id: target.dataset.id }); }, K.extracted);
    if (action === "remember-contact") return perform(function () { return apiPost("/crm/ghi-nho", { id: target.dataset.id, brain: state.brain }).then(function (r) { toast(K.remembered, { path: (r && r.path) || "" }); }); }, null);
    if (action === "approve-proposal") return approveProposal(target);
    if (action === "dismiss-proposal") return perform(function () { return apiPost("/crm/de-xuat/bo", { id: target.dataset.id }); }, K.proposalDismissed);
    if (action === "new-deal") return dealForm(null, target.dataset.contactId || null);
    if (action === "save-deal") return saveDeal();
    if (action === "delete-deal") return perform(function () { return apiPost("/crm/deal/xoa", { id: target.dataset.id }); }, K.saved);
    if (action === "open-contact") { closeModal(); state.mode = "contacts"; await loadContacts(false); return loadDetail(target.dataset.id); }
    if (action === "add-stage") return stageModal("add");
    if (action === "rename-stage") return stageModal("rename", target.dataset.key, target.dataset.label);
    if (action === "save-stage") return saveStage(false);
    if (action === "save-stage-name") return saveStage(true);
    if (action === "delete-stage") return deleteStage(target.dataset.key);
    if (action === "new-todo") return todoForm();
    if (action === "save-todo") return saveTodo();
    if (action === "delete-todo") return perform(function () { return apiPost("/crm/viec/xoa", { id: target.dataset.id }); }, K.saved);
    if (action === "open-settings") return settingsModal();
    if (action === "save-settings") return saveSettings();
    if (action === "open-inbox") return inboxModal();
    if (action === "search-inbox") return searchInbox();
    if (action === "import-inbox") return importInbox(target.dataset.id);
    if (action === "open-segments") return segmentsModal();
  }

  async function handleChange(event) {
    const target = timHanhDong(event);
    if (!target) return;
    const action = target.dataset.action;
    if (action === "change-room") { state.brain = target.value; state.selectedId = null; state.detail = null; state.root.classList.remove("is-mobile-detail"); return loadCurrent(true); }
    if (action === "enable-room") return perform(function () { return apiPost("/crm/cau-hinh/phong", { brain: state.brain, bat: target.checked ? 1 : 0 }).then(function () { const room = state.me.phong.find(function (item) { return item.brain === state.brain; }); if (room) room.bat = target.checked; }); }, K.roomUpdated);
    if (action === "add-contact-room" && target.value) return perform(function () { return apiPost("/crm/lien-he/phong", { id: state.selectedId, brain: target.value, bat: 1 }).then(function () { return loadDetail(state.selectedId, false); }); }, K.roomUpdated);
    if (action === "move-deal") return perform(function () { return apiPost("/crm/deal/buoc", { id: target.dataset.id, stage: target.value }); }, K.moved);
    if (action === "todo-filter") { state.todoDone = target.value; return loadCurrent(false); }
    if (action === "toggle-todo") return perform(function () { return apiPost("/crm/viec/xong", { id: target.dataset.id, xong: target.checked ? 1 : 0 }); }, K.saved);
  }

  function handleInput(event) {
    if (event.target.matches('[data-role="contact-search"]')) {
      state.search = event.target.value;
      clearTimeout(handleInput.timer);
      handleInput.timer = setTimeout(function () { loadCurrent(true); }, 280);
    }
  }

  function handleDragStart(event) {
    const card = event.target.closest("[data-deal-id]");
    if (!card || !canWrite()) return;
    state.draggedDealId = card.dataset.dealId;
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
  }

  function handleDragOver(event) {
    const lane = event.target.closest("[data-stage]");
    if (!lane || !state.draggedDealId || !canWrite()) return;
    event.preventDefault();
    lane.classList.add("is-over");
  }

  function handleDragLeave(event) {
    const lane = event.target.closest("[data-stage]");
    if (lane) lane.classList.remove("is-over");
  }

  function handleDrop(event) {
    const lane = event.target.closest("[data-stage]");
    if (!lane || !state.draggedDealId || !canWrite()) return;
    event.preventDefault();
    lane.classList.remove("is-over");
    const id = state.draggedDealId;
    state.draggedDealId = null;
    perform(function () { return apiPost("/crm/deal/buoc", { id: id, stage: lane.dataset.stage }); }, K.moved);
  }

  function confirmAction(key) {
    return !host || typeof host.confirm !== "function" || host.confirm(tw(key));
  }

  async function readQuickDraft() {
    const input = state.root.querySelector('[data-role="quick-text"]');
    if (!input || !input.value.trim()) return toast(K.required);
    try {
      const result = await apiPost("/crm/nhap-nhanh", { text: input.value.trim() });
      contactForm(null, result.fields || {});
    } catch (error) { showError(error); }
  }

  async function saveContact() {
    const values = formValues('[data-role="contact-form"]');
    const form = state.root.querySelector('[data-role="contact-form"]');
    if (!values || !values.name || !form.reportValidity()) return;
    values.id = form.dataset.id || 0;
    await perform(async function () {
      const result = await apiPost("/crm/lien-he", values);
      state.selectedId = result.contact && result.contact.id;
      closeModal();
    }, K.saved);
  }

  async function removeContact(id, restore) {
    if (!restore && !confirmAction(K.confirmDelete)) return;
    await perform(function () { return apiPost("/crm/lien-he/xoa", { id: id, khoi_phuc: restore ? 1 : 0 }).then(function () { state.selectedId = null; state.detail = null; }); }, restore ? K.restore : K.saved);
  }

  async function approveProposal(target) {
    const card = target.closest("[data-proposal-id]");
    const checked = card ? Array.from(card.querySelectorAll('[data-role="proposal-field"]:checked')).map(function (input) { return input.value; }) : [];
    await perform(function () { return apiPost("/crm/de-xuat/duyet", { id: target.dataset.id, chon: checked.join(",") }); }, K.proposalApproved);
  }

  async function saveDeal() {
    const values = formValues('[data-role="deal-form"]');
    const form = state.root.querySelector('[data-role="deal-form"]');
    if (!values || !form.reportValidity()) return;
    values.id = form.dataset.id || 0;
    values.brain = state.brain;
    await perform(function () { return apiPost("/crm/deal", values).then(closeModal); }, K.saved);
  }

  async function saveStage(rename) {
    const values = formValues('[data-role="stage-form"]');
    const form = state.root.querySelector('[data-role="stage-form"]');
    if (!values || !form.reportValidity()) return;
    const path = rename ? "/crm/giai-doan/ten" : "/crm/giai-doan";
    const payload = { brain: state.brain, label: values.label };
    if (rename) payload.key = form.dataset.key;
    await perform(function () { return apiPost(path, payload).then(closeModal); }, K.saved);
  }

  async function deleteStage(key) {
    if (!confirmAction(K.confirmRemoveStage)) return;
    await perform(function () { return apiPost("/crm/giai-doan/xoa", { brain: state.brain, key: key }); }, K.saved);
  }

  async function saveTodo() {
    const values = formValues('[data-role="todo-form"]');
    const form = state.root.querySelector('[data-role="todo-form"]');
    if (!values || !form.reportValidity()) return;
    values.brain = state.brain;
    await perform(function () { return apiPost("/crm/viec", values).then(closeModal); }, K.saved);
  }

  async function saveSettings() {
    const values = formValues('[data-role="settings-form"]');
    await perform(function () { return apiPost("/crm/cau-hinh/trich", values).then(function () { state.me.che_do = values.che_do; state.me.nguong = values.nguong; closeModal(); }); }, K.settingsSaved);
  }

  async function searchInbox() {
    const input = state.root.querySelector('[data-role="inbox-search"]');
    try {
      const result = await apiGet("/crm/hop-thu", { q: input ? input.value : "" });
      state.inbox = result.items || [];
      renderInboxModal();
    } catch (error) { showModalError(K.inbox, error); }
  }

  async function importInbox(id) {
    await perform(function () { return apiPost("/crm/hop-thu/nhap", { customer_id: id, brain: state.brain }).then(closeModal); }, K.imported);
  }

  async function removeContactRoom(brain) {
    if (!confirmAction(K.confirmRemoveRoom)) return;
    await perform(function () { return apiPost("/crm/lien-he/phong", { id: state.selectedId, brain: brain, bat: 0 }).then(function () { return loadDetail(state.selectedId, false); }); }, K.roomUpdated);
  }

  function render(el) {
    if (!el || !el.appendChild) throw new TypeError("JoyceCrm.render requires an element");
    state = createState();
    const root = document.createElement("div");
    root.className = "jcrm";
    el.replaceChildren(root);
    state.root = root;
    root.addEventListener("click", function (event) {
      const target = timHanhDong(event);
      if (target && target.dataset.action === "remove-contact-room") {
        removeContactRoom(target.dataset.brain);
        return;
      }
      handleClick(event);
    });
    root.addEventListener("change", handleChange);
    root.addEventListener("input", handleInput);
    root.addEventListener("dragstart", handleDragStart);
    root.addEventListener("dragover", handleDragOver);
    root.addEventListener("dragleave", handleDragLeave);
    root.addEventListener("drop", handleDrop);
    renderShell();
    init();
  }

  const publicApi = { render: render, dinhDangTien: dinhDangTien, trangThaiHan: trangThaiHan, chiaTheoGiaiDoan: chiaTheoGiaiDoan, chuCaiDau: chuCaiDau, nhanSuKien: nhanSuKien };
  if (host) host.JoyceCrm = publicApi;
  if (typeof module !== "undefined" && module.exports) module.exports = { dinhDangTien: dinhDangTien, trangThaiHan: trangThaiHan, chiaTheoGiaiDoan: chiaTheoGiaiDoan, chuCaiDau: chuCaiDau, nhanSuKien: nhanSuKien };
})(typeof window !== "undefined" ? window : globalThis);
