// Joyce OS - Bao cao kiem ke thu vien skill, chi doc.
(function () {
  "use strict";
  var host = null, report = null, token = 0;
  var filters = { q: "", group: "", tag: "", status: "" };
  var GROUP_KEY = {
    "ban-hang": "slib.group.ban-hang", "cskh": "slib.group.cskh", "marketing": "slib.group.marketing",
    "nghien-cuu": "slib.group.nghien-cuu", "san-xuat": "slib.group.san-xuat", "ke-toan": "slib.group.ke-toan",
    "nhan-su": "slib.group.nhan-su", "dieu-hanh": "slib.group.dieu-hanh", "ca-nhan": "slib.group.ca-nhan",
    "cong-cu": "slib.group.cong-cu", "": "slib.group.unassigned"
  };
  var STATUS_KEY = {
    diverged: "slib.status.diverged", review: "slib.status.review",
    system: "slib.status.system", template: "slib.status.template"
  };
  function t(k, v) { return window.t ? window.t(k, v) : k; }
  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  }); }
  function locale() { return (window.JoyceI18n && window.JoyceI18n.locale()) || "vi-VN"; }
  function num(v) { return Number(v || 0).toLocaleString(locale()); }
  function date(v) { return v ? new Date(Number(v) * 1000).toLocaleString(locale()) : t("slib.none"); }
  function groupLabel(k) { return t(GROUP_KEY[k] || "slib.group.unassigned"); }
  async function api(path, opts) {
    var r = await fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts || {}));
    var d = await r.json();
    if (!r.ok || d.ok === false) throw new Error(d.error || ("HTTP " + r.status));
    return d;
  }
  function stat(label, value) {
    return '<div class="slib-stat"><strong>' + esc(num(value)) + '</strong><span>' + esc(t(label)) + '</span></div>';
  }
  function badges(s) {
    var out = ['<span class="slib-chip">' + esc(groupLabel(s.proposed_group || "")) + '</span>'];
    (s.tags || []).forEach(function (x) { out.push('<span class="slib-chip">' + esc(x) + '</span>'); });
    if (s.diverged && !s.template) out.push('<span class="slib-chip warn">' + esc(t("slib.status.diverged")) + '</span>');
    if (s.needs_review) out.push('<span class="slib-chip warn">' + esc(t("slib.status.review")) + '</span>');
    if (s.system) out.push('<span class="slib-chip ok">' + esc(t("slib.status.system")) + '</span>');
    if (s.template) out.push('<span class="slib-chip">' + esc(t("slib.status.template")) + '</span>');
    return out.join("");
  }
  function variantHtml(v, s) {
    var marks = [];
    if (v.sha === s.majority_sha) marks.push('<span class="slib-mark">' + esc(t("slib.majority")) + '</span>');
    if (v.sha === s.newest_sha) marks.push('<span class="slib-mark">' + esc(t("slib.newest")) + '</span>');
    return '<li><div><code>' + esc(String(v.sha || "").slice(0, 12)) + '</code>' + marks.join("") + '</div>'
      + '<div class="slib-muted">' + esc(t("slib.variant_meta", { copies: num(v.count), date: date(v.newest_mtime) })) + '</div>'
      + '<div>' + esc((v.brains || []).join(", ")) + '</div></li>';
  }
  function skillHtml(s) {
    var changed = !s.template && (s.diverged_brains || []).length
      ? '<div class="slib-alert"><b>' + esc(t("slib.changed")) + '</b> ' + esc(s.diverged_brains.join(", ")) + '</div>' : "";
    var newest = (s.newest_brains || []).length
      ? '<div class="slib-muted">' + esc(t("slib.newest_copy", { brains: s.newest_brains.join(", "), date: date(s.newest_mtime) })) + '</div>' : "";
    return '<article class="slib-card"><div class="slib-card-head"><div><h4>' + esc(s.name || s.slug) + '</h4><code>' + esc(s.slug) + '</code></div>'
      + '<div class="slib-badges">' + badges(s) + '</div></div>'
      + (s.description ? '<p>' + esc(s.description) + '</p>' : "")
      + '<div class="slib-facts"><span>' + esc(t("slib.copies", { n: num(s.copies) })) + '</span><span>' + esc(t("slib.variants", { n: num((s.variants || []).length) })) + '</span>'
      + '<span>' + esc(t("slib.agents_using", { n: num(s.agents_using) })) + '</span>'
      + (s.disabled_copies ? '<span>' + esc(t("slib.disabled", { n: num(s.disabled_copies) })) + '</span>' : "") + '</div>'
      + newest + changed + '<div class="slib-reason">' + esc(s.group_reason || t("slib.none")) + '</div>'
      + '<details><summary>' + esc(t("slib.variants_detail")) + '</summary><ol class="slib-variants">'
      + (s.variants || []).map(function (v) { return variantHtml(v, s); }).join("") + '</ol></details></article>';
  }
  function matches(s) {
    var q = filters.q.toLowerCase();
    if (filters.group && (s.proposed_group || "") !== filters.group) return false;
    if (filters.tag && (s.tags || []).indexOf(filters.tag) < 0) return false;
    if (filters.status === "diverged" && (!s.diverged || s.template)) return false;
    if (filters.status === "review" && !s.needs_review) return false;
    if (filters.status === "system" && !s.system) return false;
    if (filters.status === "template" && !s.template) return false;
    if (!q) return true;
    return [s.slug, s.name, s.description, s.proposed_group, (s.tags || []).join(" "), (s.brains || []).join(" ")]
      .join(" ").toLowerCase().indexOf(q) >= 0;
  }
  function renderList() {
    if (!host || !report) return;
    var list = (report.skills || []).filter(matches);
    var box = host.querySelector("#slibList");
    var count = host.querySelector("#slibCount");
    if (count) count.textContent = t("slib.result_count", { n: num(list.length) });
    if (box) box.innerHTML = list.length ? list.map(skillHtml).join("") : '<div class="slib-empty">' + esc(t("slib.no_match")) + '</div>';
  }
  function unmatchedHtml(rows) {
    if (!rows || !rows.length) return "";
    return '<section class="slib-unmatched"><h3>' + esc(t("slib.unmatched_title")) + '</h3><p>' + esc(t("slib.unmatched_body")) + '</p><div class="slib-unmatched-grid">'
      + rows.map(function (b) { return '<div><b>' + esc(b.name) + '</b><span>' + esc(b.suggested_group ? t("slib.suggested", { group: groupLabel(b.suggested_group) }) : t("slib.no_suggestion")) + '</span></div>'; }).join("")
      + '</div></section>';
  }
  function render() {
    if (!host || !report) return;
    var s = report.summary || {};
    var groups = (report.groups || []).map(function (g) { return g.key; });
    var tags = {};
    (report.skills || []).forEach(function (x) { (x.tags || []).forEach(function (tag) { tags[tag] = true; }); });
    host.innerHTML = '<div class="slib"><header class="slib-head"><div><h2>' + esc(t("slib.title")) + '</h2><p>' + esc(t("slib.subtitle")) + '</p></div>'
      + '<button type="button" id="slibRun">' + esc(t("slib.rerun")) + '</button></header>'
      + '<div class="slib-safe">' + esc(t("slib.readonly")) + '</div>'
      + '<div class="slib-meta">' + esc(t("slib.updated", { date: date(report.generated_at) })) + '</div>'
      + '<div class="slib-stats">' + stat("slib.summary.brains", s.brains) + stat("slib.summary.files", s.files)
      + stat("slib.summary.slugs", s.distinct_slugs) + stat("slib.summary.diverged", s.slugs_diverged)
      + stat("slib.summary.unmatched", s.unmatched_brains) + stat("slib.summary.review", s.needs_review) + '</div>'
      + unmatchedHtml(report.unmatched_brains)
      + '<section class="slib-filters"><input id="slibQ" type="search" placeholder="' + esc(t("slib.filter.search")) + '">'
      + '<select id="slibGroup" aria-label="' + esc(t("slib.filter.group")) + '"><option value="">' + esc(t("slib.filter.all_groups")) + '</option>'
      + groups.map(function (g) { return '<option value="' + esc(g) + '">' + esc(groupLabel(g)) + '</option>'; }).join("") + '</select>'
      + '<select id="slibTag" aria-label="' + esc(t("slib.filter.tag")) + '"><option value="">' + esc(t("slib.filter.all_tags")) + '</option>'
      + Object.keys(tags).sort().map(function (x) { return '<option value="' + esc(x) + '">' + esc(x) + '</option>'; }).join("") + '</select>'
      + '<select id="slibStatus" aria-label="' + esc(t("slib.filter.status")) + '"><option value="">' + esc(t("slib.filter.all_status")) + '</option>'
      + Object.keys(STATUS_KEY).map(function (x) { return '<option value="' + x + '">' + esc(t(STATUS_KEY[x])) + '</option>'; }).join("") + '</select></section>'
      + '<div class="slib-list-head"><b>' + esc(t("slib.skills_title")) + '</b><span id="slibCount"></span></div><div id="slibList" class="slib-list"></div></div>';
    host.querySelector("#slibRun").onclick = run;
    host.querySelector("#slibQ").oninput = function (e) { filters.q = e.target.value.trim(); renderList(); };
    host.querySelector("#slibGroup").onchange = function (e) { filters.group = e.target.value; renderList(); };
    host.querySelector("#slibTag").onchange = function (e) { filters.tag = e.target.value; renderList(); };
    host.querySelector("#slibStatus").onchange = function (e) { filters.status = e.target.value; renderList(); };
    renderList();
  }
  function empty() {
    host.innerHTML = '<div class="slib slib-first"><h2>' + esc(t("slib.empty_title")) + '</h2><p>' + esc(t("slib.empty_body")) + '</p>'
      + '<div class="slib-safe">' + esc(t("slib.readonly")) + '</div><button type="button" id="slibRun">' + esc(t("slib.run")) + '</button></div>';
    host.querySelector("#slibRun").onclick = run;
  }
  async function run() {
    var mine = ++token;
    if (host) host.innerHTML = '<div class="empty">' + esc(t("slib.running")) + '</div>';
    try {
      var d = await api("/skill-library/audit/run", { method: "POST", body: "{}" });
      if (mine !== token) return;
      report = d.report; render();
    } catch (e) {
      if (mine === token && host) host.innerHTML = '<div class="slib-error">' + esc(t("slib.error", { error: e.message })) + '</div>';
    }
  }
  async function open(target) {
    host = target; report = null; filters = { q: "", group: "", tag: "", status: "" };
    var mine = ++token;
    if (!host) return;
    host.innerHTML = '<div class="empty">' + esc(t("slib.loading")) + '</div>';
    try {
      var d = await api("/skill-library/audit");
      if (mine !== token) return;
      report = d.report;
      if (report) render(); else empty();
    } catch (e) {
      if (mine === token) host.innerHTML = '<div class="slib-error">' + esc(t("slib.error", { error: e.message })) + '</div>';
    }
  }
  window.JoyceSkillLibrary = { open: open };
})();
