/* Skill Learn Update: repo -> quet tinh -> AI doc, phan loai, dich -> chu duyet -> cai. Khong co gi tu cai. */
(function () {
  "use strict";
  var state = null, tab = null, typeF = "all", catF = "all", query = "", panel = null, busy = false, timer = null, wasRunning = false;
  var sel = {};
  var CATS = ["ban-hang", "marketing", "noi-dung", "du-lieu", "ke-toan", "tu-dong-hoa", "giao-tiep", "nghien-cuu", "lap-trinh", "cuoc-song", "khac"];
  var TABS = ["take", "later", "raw", "skip", "done"];
  var brain = function () { return window.currentBrainPath ? window.currentBrainPath() : "brain"; };
  var t = function (k, v) { return window.t ? window.t(k, v) : k; };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  }); };
  var icon = function (n) { return window.ic ? window.ic(n) : ""; };
  function fmt(ts) { return ts ? new Date(Number(ts) * 1000).toLocaleString() : t("sl.never"); }
  async function api(path, opts) {
    var sep = path.indexOf("?") >= 0 ? "&" : "?";
    var res = await fetch(path + sep + "brain=" + encodeURIComponent(brain()), Object.assign({
      headers: { "Content-Type": "application/json" }
    }, opts || {}));
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok || data.ok === false) throw new Error(data.error || t("sl.err_connect"));
    return data;
  }
  function post(path, body) { return api(path, { method: "POST", body: JSON.stringify(body || {}) }); }

  function an(c) { return c.analysis || null; }
  function label(c) { return (an(c) && an(c).title) || c.name; }
  function bucket(c) {
    if (c.status === "installed" || c.status === "rejected") return "done";
    if (c.status !== "pending") return "";
    var v = an(c) ? an(c).verdict : "";
    return v === "take" ? "take" : v === "skip" ? "skip" : v === "later" ? "later" : "raw";
  }
  function find(id) { return (state.candidates || []).filter(function (c) { return c.id === id; })[0]; }
  function haystack(c) {
    var a = an(c) || {};
    return [c.name, c.slug, c.description, a.title, a.what, a.gain, a.reason].join(" ").toLowerCase();
  }
  function passes(c) {
    if (typeF !== "all" && (c.type || "skill") !== typeF) return false;
    if (catF !== "all" && ((an(c) || {}).category || "") !== catF) return false;
    return !query || haystack(c).indexOf(query.toLowerCase()) >= 0;
  }
  function counts(rows) {
    var n = { take: 0, later: 0, raw: 0, skip: 0, done: 0 };
    rows.forEach(function (c) { var b = bucket(c); if (b) n[b]++; });
    return n;
  }
  function pendingIds(rows) { return rows.filter(function (c) { return c.status === "pending" && c.installable !== false; }).map(function (c) { return c.id; }); }

  function chip(text, cls) { return '<span class="sl-chip' + (cls ? " " + cls : "") + '">' + esc(text) + '</span>'; }
  function riskText(k) { return t(k === "high" ? "sl.risk.high" : k === "medium" ? "sl.risk.medium" : "sl.risk.low"); }
  function kindText(k) { return t(k === "update" ? "sl.kind.update" : k === "current" ? "sl.kind.current" : "sl.kind.new"); }

  function notesHtml(c) {
    var a = an(c);
    if (!a) {
      return '<div class="sl-raw"><div class="sl-raw-title">' + esc(t("sl.no_ai")) + '</div><div class="sl-raw-desc">' +
        esc(c.description || t("sl.no_desc")) + '</div>' +
        (c.analysis_error ? '<div class="sl-err">' + esc(c.analysis_error) + '</div>' : '') +
        (state.can_analyze ? '<button data-act="analyze" data-id="' + esc(c.id) + '">' + icon("sparkles") + esc(t("sl.ask_ai")) + '</button>' : '') + '</div>';
    }
    var rows = [["sl.what", a.what, ""], ["sl.gain", a.gain, "gain"], ["sl.reason", a.reason, ""]];
    if (a.overlap) rows.push(["sl.overlap", a.overlap, ""]);
    if (a.caution) rows.push(["sl.caution", a.caution, "warn"]);
    return '<dl class="sl-notes">' + rows.filter(function (r) { return r[1]; }).map(function (r) {
      return '<div class="' + r[2] + '"><dt>' + esc(t(r[0])) + '</dt><dd>' + esc(r[1]) + '</dd></div>';
    }).join("") + '</dl><div class="sl-ai-by">' + esc(t("sl.ai_by", { model: a.model || "AI" })) +
      ' <button class="sl-link" data-act="analyze" data-id="' + esc(c.id) + '" data-force="1">' + esc(t("sl.redo")) + '</button></div>';
  }

  function cardHtml(c) {
    var a = an(c), isPlugin = c.type === "plugin", pending = c.status === "pending";
    var v = a ? a.verdict : "";
    var warns = (c.warnings || []).length ? '<ul class="sl-warnings">' + c.warnings.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul>' : "";
    var tools = isPlugin && (c.tools || []).length ? '<div class="sl-tools">' + esc(t("sl.tools")) + ' ' + c.tools.map(function (x) { return '<code>' + esc(x) + '</code>'; }).join(" ") + '</div>' : "";
    var plug = isPlugin && pending ? '<div class="sl-plugnote">' + icon("shield") + esc(t("sl.plugin_note")) + '</div>' : "";
    var blocked = c.installable === false ? '<div class="sl-err">' + esc(c.blocked_reason || t("sl.cannot_install")) + '</div>' : "";
    var acts;
    if (pending) {
      acts = '<div class="sl-actions">' + (c.installable === false ? "" : '<button class="primary" data-act="install" data-id="' + esc(c.id) + '">' +
        icon("circle-check") + esc(t(c.kind === "update" ? "sl.approve_update" : "sl.approve")) + '</button>') +
        '<button data-act="reject" data-id="' + esc(c.id) + '">' + esc(t("sl.skip_it")) + '</button></div>';
    } else {
      acts = '<div class="sl-actions">' + chip(t("sl.status." + c.status)) + '</div>';
    }
    var check = pending && c.installable !== false ? '<label class="sl-pick"><input type="checkbox" data-chg="pick" data-id="' + esc(c.id) + '"' + (sel[c.id] ? " checked" : "") + '></label>' : "";
    return '<article class="sl-card' + (v ? " v-" + esc(v) : "") + (sel[c.id] ? " picked" : "") + '"><div class="sl-card-head">' + check +
      '<div class="sl-card-titles"><div class="sl-card-title">' + esc(label(c)) + '</div><div class="sl-card-orig">' + esc(c.name) + ' · ' + esc(c.relative) + '</div></div>' +
      '<div class="sl-badges">' + (v ? chip(t("sl.verdict." + v), "sl-v-" + v) : "") + chip(t(isPlugin ? "sl.type.plugin" : "sl.type.skill"), "sl-type-" + (isPlugin ? "plugin" : "skill")) + '</div></div>' +
      notesHtml(c) + tools +
      '<div class="sl-meta">' + (a && a.category ? chip(t("sl.cat." + a.category)) : "") + chip(riskText(c.risk), "sl-risk-" + esc(c.risk)) +
      chip(kindText(c.kind)) + chip(c.source_name) + '</div>' + warns + plug + blocked + acts +
      '<details><summary>' + esc(t("sl.original")) + '</summary><div class="sl-orig-desc">' + esc(c.description || "") + '</div><pre>' + esc(c.excerpt || "") + '</pre></details></article>';
  }

  function sourceHtml(s) {
    var meta = s.last_error ? '<div class="sl-source-meta bad">' + esc(s.last_error) + '</div>'
      : '<div class="sl-source-meta">' + esc(t("sl.found_n", { n: s.skill_count || 0 })) + ' · ' + esc(fmt(s.last_sync)) + '</div>';
    return '<div class="sl-source"><div><div class="sl-source-name">' + icon(s.kind === "github" ? "git-branch" : "folder") + esc(s.name) +
      chip(s.kind === "github" ? "GitHub" : "Local") + '</div><div class="sl-source-path" title="' + esc(s.location) + '">' + esc(s.location) + '</div>' + meta +
      '</div><div class="sl-source-actions"><button data-act="sync" data-id="' + esc(s.id) + '" title="' + esc(t("sl.resync")) + '">' + icon("rotate-cw") +
      '</button><button class="danger" data-act="del" data-id="' + esc(s.id) + '" title="' + esc(t("sl.remove_src")) + '">' + icon("trash-2") + '</button></div></div>';
  }

  function jobHtml() {
    var j = state.job || {}, out = "";
    if (j.running) {
      var pct = j.total ? Math.round(100 * (j.done || 0) / j.total) : 6;
      out += '<div class="sl-job"><div class="sl-job-text">' + icon("sparkles") + esc(t("sl.job_running", { done: j.done || 0, total: j.total || "?" })) +
        '</div><div class="sl-bar"><i style="width:' + pct + '%"></i></div></div>';
    } else if (j.error) {
      out += '<div class="sl-job bad"><div class="sl-job-text">' + esc(t("sl.job_error", { err: j.error })) + '</div>' +
        (state.can_analyze ? '<button data-act="analyze-all">' + esc(t("sl.retry")) + '</button>' : '') + '</div>';
    }
    if (!state.can_analyze) out += '<div class="sl-job bad"><div class="sl-job-text">' + esc(t("sl.no_model")) + '</div></div>';
    return out;
  }

  function render() {
    if (!panel || !state) return;
    var keep = { add: (panel.querySelector("#slLocation") || {}).value || "" };
    var sf = panel.querySelector("#slSearch"), hadFocus = sf && document.activeElement === sf, caret = hadFocus ? sf.selectionStart : 0;
    var all = state.candidates || [], st = state.stats || {}, sch = state.schedule || {}, running = !!(state.job && state.job.running);
    if (wasRunning && !running) tab = null;
    wasRunning = running;
    if (!tab) tab = TABS.filter(function (k) { return counts(all)[k] > 0; })[0] || "take";
    var visible = all.filter(passes), n = counts(visible);
    var list = visible.filter(function (c) { return bucket(c) === tab; });
    var cats = CATS.filter(function (k) { return all.some(function (c) { return (an(c) || {}).category === k; }); });
    var picked = Object.keys(sel).filter(function (k) { return sel[k] && find(k) && find(k).status === "pending"; });
    var canPick = pendingIds(list);
    panel.innerHTML = '<div class="sl">' +
      '<section class="sl-hero"><div><h3>Skill Learn Update</h3><p>' + esc(t("sl.hero")) + '</p></div><div class="sl-stats">' +
      stat(st.sources, "sl.stat.sources") + stat(st.take, "sl.stat.take") + stat(st.pending, "sl.stat.pending") + stat(st.high_risk, "sl.stat.risk") + '</div></section>' +
      '<section class="sl-box sl-addbox"><div class="sl-head"><h4>' + esc(t("sl.add_title")) + '</h4><button data-act="sync-all">' + icon("rotate-cw") + esc(t("sl.scan_all")) + '</button></div>' +
      '<div class="sl-sub">' + esc(t("sl.add_sub")) + '</div><div class="sl-add"><input id="slLocation" placeholder="' + esc(t("sl.add_ph")) + '"><button class="primary" data-act="add">' +
      icon("plus") + esc(t("sl.add_btn")) + '</button></div><div class="sl-msg" id="slMsg"></div>' +
      ((state.sources || []).length ? '<div class="sl-sources">' + state.sources.map(sourceHtml).join("") + '</div>' : '') + '</section>' + jobHtml() +
      '<section class="sl-box"><div class="sl-head"><h4>' + esc(t("sl.board")) + '</h4><div class="sl-tools-row">' +
      '<select data-chg="type"><option value="all">' + esc(t("sl.f.all_types")) + '</option><option value="skill"' + (typeF === "skill" ? " selected" : "") + '>' + esc(t("sl.type.skill")) +
      '</option><option value="plugin"' + (typeF === "plugin" ? " selected" : "") + '>' + esc(t("sl.type.plugin")) + '</option></select>' +
      '<select data-chg="cat"><option value="all">' + esc(t("sl.f.all_cats")) + '</option>' + cats.map(function (k) {
        return '<option value="' + k + '"' + (catF === k ? " selected" : "") + '>' + esc(t("sl.cat." + k)) + '</option>'; }).join("") + '</select>' +
      '<input id="slSearch" class="sl-search" type="search" placeholder="' + esc(t("sl.search")) + '" value="' + esc(query) + '"></div></div>' +
      '<div class="sl-tabs">' + TABS.map(function (k) { return '<button data-act="tab" data-v="' + k + '" class="' + (tab === k ? "on" : "") + '">' + esc(t("sl.tab." + k)) +
        ' <b>' + n[k] + '</b></button>'; }).join("") + '</div>' +
      (tab !== "done" && canPick.length ? '<div class="sl-selbar"><label><input type="checkbox" data-chg="pickall"' + (canPick.every(function (i) { return sel[i]; }) ? " checked" : "") + '> ' +
        esc(t("sl.pick_all", { n: canPick.length })) + '</label>' + (tab === "raw" && state.can_analyze ? '<button data-act="analyze-all">' + icon("sparkles") + esc(t("sl.ask_all")) + '</button>' : '') + '</div>' : '') +
      '<div class="sl-cards">' + (list.map(cardHtml).join("") || '<div class="sl-empty">' + esc(t(all.length ? "sl.empty_tab" : "sl.empty_none")) + '</div>') + '</div></section>' +
      (picked.length ? '<div class="sl-bulk"><strong>' + esc(t("sl.picked_n", { n: picked.length })) + '</strong><button class="primary" data-act="bulk-install">' + icon("circle-check") +
        esc(t("sl.bulk_install")) + '</button><button data-act="bulk-reject">' + esc(t("sl.bulk_reject")) + '</button><button data-act="pick-clear">' + esc(t("sl.pick_clear")) + '</button></div>' : '') +
      '<div class="sl-grid2"><section class="sl-box"><h4>' + esc(t("sl.sched_title")) + '</h4><div class="sl-sub">' + esc(t("sl.sched_sub")) + '</div><div class="sl-schedule"><label class="sl-switch"><input data-chg="sched" type="checkbox"' +
      (sch.enabled ? " checked" : "") + '><span></span></label><input class="sl-time" data-chg="time" type="time" value="' + esc(sch.time || "07:30") + '">' +
      chip(sch.enabled ? t("sl.sched_next", { when: fmt(sch.next_run) }) : t("sl.sched_off")) + '</div></section>' +
      '<section class="sl-box"><h4>' + esc(t("sl.route_title")) + '</h4><div class="sl-sub">' + esc(t("sl.route_sub")) + '</div><div class="sl-route"><div><span>' + esc(t("sl.route_scan")) +
      '</span><strong>' + esc(t("sl.route_scan_v")) + '</strong></div><div><span>' + esc(t("sl.route_ai")) + '</span><strong>' + esc((state.routing || {}).classification || "glm-4.7-flash") + '</strong></div></div></section></div>' +
      '<section class="sl-box"><h4>' + esc(t("sl.history")) + '</h4>' + ((state.runs || []).slice(0, 5).map(function (r) {
        return '<div class="sl-run"><strong>' + esc(fmt(r.at)) + '</strong> · ' + esc(t(r.reason === "daily" ? "sl.run.daily" : "sl.run.manual")) + ' · ' +
          esc(t("sl.run.found", { found: r.found || 0, pending: r.pending || 0 })) + ((r.errors || []).length ? ' · ' + esc(t("sl.run.errors", { n: r.errors.length })) : '') + '</div>'; }).join("") ||
        '<div class="sl-sub">' + esc(t("sl.no_runs")) + '</div>') + '</section></div>';
    var add = panel.querySelector("#slLocation");
    if (add) add.value = keep.add;
    if (hadFocus) { var ns = panel.querySelector("#slSearch"); if (ns) { ns.focus(); try { ns.setSelectionRange(caret, caret); } catch (e) { /* type=search */ } } }
    setBusy(busy);
    poll();
  }
  function stat(v, k) { return '<div class="sl-stat"><strong>' + esc(v || 0) + '</strong><span>' + esc(t(k)) + '</span></div>'; }

  function setBusy(on) {
    busy = on;
    if (panel) panel.querySelectorAll("button,input,select").forEach(function (x) { if (x.id !== "slSearch") x.disabled = !!on; });
  }
  function showMsg(text, bad) { var el = panel && panel.querySelector("#slMsg"); if (el) { el.textContent = text || ""; el.classList.toggle("err", !!bad); } }
  function poll() {
    clearTimeout(timer);
    if (!(state && state.job && state.job.running)) return;
    timer = setTimeout(async function () {
      if (!panel || !document.body.contains(panel) || !panel.querySelector(".sl")) return;
      try { state = await api("/skill-learn"); render(); } catch (e) { poll(); }
    }, 2500);
  }
  async function reload() { state = await api("/skill-learn"); render(); }

  async function guarded(fn, onErr) {
    setBusy(true);
    try { await fn(); } catch (e) { (onErr || function (m) { showMsg(m, true); })(e.message); } finally { setBusy(false); }
  }
  function sync(ids) {
    return guarded(async function () {
      showMsg(t("sl.syncing"));
      var r = await post("/skill-learn/sync", { source_ids: ids || [] });
      state = r.state; render();
      showMsg(r.run_ok ? t(r.analysis && r.analysis.started ? "sl.scanned_ai" : "sl.scanned") : t("sl.scanned_err"), !r.run_ok);
    });
  }
  function analyze(ids, force) {
    return guarded(async function () {
      var r = await post("/skill-learn/analyze", { candidate_ids: ids || [], force: !!force });
      state = r.state; render();
    });
  }
  async function review(ids, action) {
    var rows = ids.map(find).filter(Boolean);
    if (!rows.length) return;
    var risky = rows.filter(function (c) { return c.type === "plugin" || c.risk === "high"; });
    if (action === "install" && risky.length) {
      var name = rows.length === 1 ? label(rows[0]) : t("sl.n_items", { n: rows.length });
      var msg = t("sl.confirm_install", { name: name });
      if (risky.some(function (c) { return c.type === "plugin"; })) msg += "\n\n" + t("sl.confirm_plugin");
      if (risky.some(function (c) { return c.risk === "high"; })) msg += "\n\n" + t("sl.confirm_risk");
      if (!window.confirm(msg)) return;
    } else if (action === "install" && rows.length > 1 && !window.confirm(t("sl.confirm_bulk", { n: rows.length }))) return;
    await guarded(async function () {
      var r = ids.length === 1 ? await post("/skill-learn/review", { candidate_id: ids[0], action: action })
        : await post("/skill-learn/review-batch", { candidate_ids: ids, action: action });
      state = r.state; ids.forEach(function (i) { delete sel[i]; }); render();
      var bad = (r.results || []).filter(function (x) { return !x.ok; });
      if (bad.length) window.alert(t("sl.some_failed") + "\n" + bad.map(function (x) { return "- " + (x.name || x.id) + ": " + x.error; }).join("\n"));
      if (action === "install") {
        if (rows.some(function (c) { return c.type === "plugin"; })) showMsg(t("sl.plugin_off"));
        window.dispatchEvent(new CustomEvent("joyce:skills-changed"));
      }
    }, function (m) { window.alert(m); });
  }

  function visibleIds() { return pendingIds((state.candidates || []).filter(passes).filter(function (c) { return bucket(c) === tab; })); }
  function onClick(e) {
    var b = e.target.closest("[data-act]");
    if (!b || b.disabled || !state) return;
    var a = b.dataset.act, id = b.dataset.id;
    if (a === "add") {
      var v = (panel.querySelector("#slLocation").value || "").trim();
      if (!v) return;
      guarded(async function () {
        var r = await post("/skill-learn/sources", { location: v });
        state = r.state; render(); await sync([r.source_id]);
      });
    } else if (a === "sync-all") sync([]);
    else if (a === "sync") sync([id]);
    else if (a === "del") {
      if (!window.confirm(t("sl.confirm_del"))) return;
      guarded(async function () { state = (await api("/skill-learn/sources/" + encodeURIComponent(id), { method: "DELETE" })).state; render(); });
    } else if (a === "tab") { tab = b.dataset.v; render(); }
    else if (a === "install") review([id], "install");
    else if (a === "reject") review([id], "reject");
    else if (a === "analyze") analyze([id], b.dataset.force === "1");
    else if (a === "analyze-all") analyze([], false);
    else if (a === "bulk-install") review(Object.keys(sel).filter(function (k) { return sel[k]; }), "install");
    else if (a === "bulk-reject") review(Object.keys(sel).filter(function (k) { return sel[k]; }), "reject");
    else if (a === "pick-clear") { sel = {}; render(); }
  }
  function onChange(e) {
    var el = e.target.closest("[data-chg]");
    if (!el || !state) return;
    var k = el.dataset.chg;
    if (k === "type") { typeF = el.value; render(); }
    else if (k === "cat") { catF = el.value; render(); }
    else if (k === "pick") { sel[el.dataset.id] = el.checked; render(); }
    else if (k === "pickall") { visibleIds().forEach(function (i) { sel[i] = el.checked; }); render(); }
    else if (k === "sched" || k === "time") {
      guarded(async function () {
        state = (await post("/skill-learn/schedule", { enabled: panel.querySelector('[data-chg="sched"]').checked, time: panel.querySelector('[data-chg="time"]').value })).state;
        render();
      }, function (m) { window.alert(m); });
    }
  }
  function onInput(e) {
    if (e.target.id === "slSearch") { query = e.target.value.trim(); render(); }
  }
  function onKey(e) {
    if (e.target.id === "slLocation" && e.key === "Enter") { var b = panel.querySelector('[data-act="add"]'); if (b) b.click(); }
  }

  async function open(target) {
    var host = target || document.getElementById("panel-skills"); if (!host) return;
    // Xu ly su kien gan vao mot khung RIENG ben trong panel: tab Kỹ năng thuong cung do vao #panel-skills,
    // khung nay bi go di thi handler cung mat, khong chan nhầm nút (data-act) cua tab kia.
    host.innerHTML = "";
    panel = document.createElement("div");
    panel.className = "sl-root";
    host.appendChild(panel);
    state = null; tab = null; wasRunning = false;
    panel.onclick = onClick; panel.onchange = onChange; panel.oninput = onInput; panel.onkeydown = onKey;
    panel.innerHTML = '<div class="empty">' + esc(t("sl.loading")) + '</div>';
    try { await reload(); } catch (e) { panel.innerHTML = '<div class="sl-empty">' + esc(t("sl.err_load", { err: e.message })) + '</div>'; }
  }
  window.JoyceSkillLearn = { open: open };
})();
