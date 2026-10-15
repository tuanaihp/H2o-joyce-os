/* chat-file.js - file brain trong khung chat Joyce.

   Hai nang luc:
   1) Nut file (icon file-text) canh nut ghim (brainFileBtn): mo panel chon file .md trong brain (duyet thu muc
      hoac tim theo ten) -> chen `path` vao o nhap. AI doc duoc file qua vault tools, nen chi
      can "tom tat `wiki/x.md`" la no mo dung file do. Tin nguoi dung co `path.md` duoc
      linkifyMd bien thanh link bam mo trinh sua (handler jv-floc document-level co san).
   2) Nut "Ghi nho" (icon star) (data-act="remember") tren moi bong bong: ghi NGUYEN VAN tin vao
      sources/ cua brain dang choi (frontmatter type: source, source_kind: chat) - lo
      ingest-source / loop se chung cat len wiki sau. Day la cach bo nho "moc dan" moi ngay.

   Thu muc khong dinh ky tu em dash. */
(function () {
  "use strict";

  function tw(k) { return (typeof window !== "undefined" && window.t) ? window.t(k) : k; }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function curBrain() {
    return (typeof window.currentBrainPath === "function") ? window.currentBrainPath() : "brain";
  }

  // -------- 1) Bo chon file brain --------------------------------------
  // `home` (goc brain, tuong doi tran) cache THEO TUNG BRAIN: doi brain ma dung lai home cu
  // la ghi nho roi vao sources/ cua brain truoc.
  var panel = null, homes = {}, home = "", seq = 0;

  function ensurePanel() {
    if (panel) return panel;
    panel = document.createElement("div");
    panel.id = "brainFilePanel";
    panel.className = "slash-menu";           // muon kieu dropdown cua menu "/" cho dong nhat
    panel.style.display = "none";
    document.body.appendChild(panel);
    return panel;
  }

  function hide() { seq++; if (panel) panel.style.display = "none"; }

  function positionPanel(anchor) {
    var rect = anchor.getBoundingClientRect();
    panel.style.left = rect.left + "px";
    panel.style.width = Math.max(360, rect.width + 120) + "px";
    panel.style.bottom = (window.innerHeight - rect.top + 6) + "px";
    panel.style.maxHeight = "min(50vh, 420px)";
  }

  function insertRef(path) {
    var input = document.getElementById("chatInput");
    if (!input) return;
    var ins = "`" + path + "` ";
    var s = input.selectionStart == null ? input.value.length : input.selectionStart;
    var e = input.selectionEnd == null ? s : input.selectionEnd;
    input.value = input.value.slice(0, s) + ins + input.value.slice(e);
    try { input.focus(); input.setSelectionRange(s + ins.length, s + ins.length); } catch (err) {}
  }

  // Icon Lucide thay emoji (tests/python/test_icons.py): đổi màu theo theme như mọi icon khác.
  function icon(ten) { return window.ic ? window.ic(ten) + " " : ""; }

  function rowHtml(it) {
    return '<div class="slash-item" data-p="' + esc(it.path) + '" data-nav="' + esc(it.dirPath || it.path) +
      '" data-dir="' + (it.type === "dir" ? 1 : 0) + '">' +
      '<span class="slash-name">' + icon(it.type === "dir" ? "folder" : "file-text") + esc(it.name) + "</span>" +
      '<span class="slash-desc">' + esc(it.path) + "</span></div>";
  }

  async function listDir(path, brain) {
    brain = brain || curBrain();
    var r = await fetch("/files/list?brain=" + encodeURIComponent(brain) +
      (path ? "&path=" + encodeURIComponent(path) : ""));
    var d = await r.json().catch(function () { return {}; });
    if (d.home != null) { homes[brain] = d.home; if (brain === curBrain()) home = d.home; }
    return d;
  }

  function renderBrowse(d, headHtml) {
    var items = (d.items || []).filter(function (it) {
      return it.type === "dir" || /\.(md|txt|json|ya?ml|csv)$/i.test(it.name);
    });
    // Path CHEN vao tin la tuong doi GOC BRAIN (wiki/x.md) - quy uoc CLAUDE.md va AI viet;
    // path duyet thu muc (data-dir) van theo tran de goi /files/list.
    var relBase = (d.path && home && d.path.indexOf(home + "/") === 0)
      ? d.path.slice(home.length + 1) : (d.path === home ? "" : d.path || "");
    var rows = items.slice(0, 60).map(function (it) {
      var rel = (relBase ? relBase + "/" : "") + it.name;
      return rowHtml({name: it.name, type: it.type, path: rel, dirPath: (d.path ? d.path + "/" : "") + it.name});
    }).join("");
    panel.innerHTML = headHtml +
      '<div style="padding:6px 8px;border-bottom:1px solid var(--line,rgba(0,0,0,.08))">' +
      '<input id="bfQ" class="bf-q" placeholder="' + esc(tw("bf.search_ph")) + '" ' +
      'style="width:100%;box-sizing:border-box;padding:6px 9px;border:1px solid var(--line,#ccc);border-radius:8px;font:inherit;background:var(--field-bg,var(--bg));color:inherit"></div>' +
      '<div class="bf-list" style="overflow:auto">' +
      // Chi cho "len" khi dang SAU HON goc brain - khong leo ra ngoai tran duyet.
      (home && d.path && d.path.indexOf(home + "/") === 0 ? '<div class="slash-item bf-up">' + icon("arrow-left") + '..</div>' : "") +
      (rows || '<div class="slash-item" style="opacity:.6">' + esc(tw("bf.empty")) + "</div>") +
      "</div>";
    wire();
  }

  function renderSearch(q, items) {
    var rows = items.filter(function (it) { return it.type !== "dir"; })
      .map(function (it) {
        // /files/search tra path theo TRAN - doi ve tuong doi goc brain truoc khi chen.
        var p = it.path;
        if (home && p.indexOf(home + "/") === 0) p = p.slice(home.length + 1);
        return rowHtml({name: it.name, type: "file", path: p});
      }).join("");
    panel.querySelector(".bf-list").innerHTML =
      rows || '<div class="slash-item" style="opacity:.6">' + esc(tw("bf.empty")) + "</div>";
  }

  function wire() {
    var input = panel.querySelector("#bfQ");
    var deb = null;
    if (input) {
      input.addEventListener("input", function () {
        var q = input.value.trim();
        clearTimeout(deb);
        if (!q) { open(); return; }
        var my = ++seq;
        deb = setTimeout(async function () {
          try {
            var r = await fetch("/files/search?brain=" + encodeURIComponent(curBrain()) +
              "&q=" + encodeURIComponent(q) + "&mode=name&limit=20");
            var d = await r.json().catch(function () { return {}; });
            if (my !== seq || !panel || panel.style.display === "none") return;
            renderSearch(q, d.items || []);
          } catch (e) {}
        }, 250);
      });
      input.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });
    }
    panel.querySelectorAll(".slash-item[data-p]").forEach(function (el) {
      el.addEventListener("mousedown", function (e) {
        e.preventDefault();
        // Thu muc duyet theo path TRAN (data-nav), file chen path GOC BRAIN (data-p).
        if (el.dataset.dir === "1") { open(el.dataset.nav); return; }
        insertRef(el.dataset.p); hide();
      });
    });
    var up = panel.querySelector(".bf-up");
    if (up) up.addEventListener("mousedown", function (e) {
      e.preventDefault();
      var cur = panel.dataset.cur || "";
      open(cur.split("/").slice(0, -1).join("/"));
    });
  }

  async function open(path) {
    ensurePanel();
    home = homes[curBrain()] != null ? homes[curBrain()] : "";
    panel.dataset.cur = path || "";
    panel.innerHTML = '<div class="slash-item" style="opacity:.6">…</div>';
    panel.style.display = "block";
    positionPanel(document.getElementById("brainFileBtn"));
    try {
      var d = await listDir(path);
      // Hien path TUONG DOI goc brain cho de doc ("wiki/" thay vi "brains/Brain Default/wiki").
      var rel = (d.path && home && d.path.indexOf(home + "/") === 0)
        ? d.path.slice(home.length + 1) : (d.path || "");
      var head = '<div style="padding:6px 10px;font-size:12px;opacity:.65">' +
        esc(tw("bf.title")) + " · " + esc(rel || "/") + "</div>";
      renderBrowse(d, head);
      var q = panel.querySelector("#bfQ");
      if (q) q.focus();
    } catch (e) {
      panel.innerHTML = '<div class="slash-item" style="opacity:.6">' + esc(tw("bf.err")) + "</div>";
    }
  }

  function toggle(anchor) {
    ensurePanel();
    if (panel.style.display !== "none") { hide(); return; }
    open("");
  }

  // Dong panel khi bam ra ngoai
  if (typeof document !== "undefined") {
    document.addEventListener("mousedown", function (e) {
      if (!panel || panel.style.display === "none") return;
      var btn = document.getElementById("brainFileBtn");
      if (panel.contains(e.target) || (btn && btn.contains(e.target))) return;
      hide();
    });
  }

  // -------- 2) Ghi nho tin nhan -> sources/ -----------------------------
  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  async function remember(text, ts) {
    text = String(text || "").trim();
    if (!text) throw new Error(tw("bf.rem_empty"));
    // Chot brain MOT lan cho ca luot ghi - nguoi dung doi brain giua chung khong lam lech.
    var brain = curBrain();
    if (homes[brain] == null) { try { await listDir("", brain); } catch (e) {} }
    // Chua biet goc brain thi KHONG ghi: home "" hop le (tran = goc brain), nhung "khong biet"
    // ma doan "" la ghi ra sources/ o TRAN (tren localhost tran la ca o dia).
    if (homes[brain] == null) throw new Error(tw("bf.err"));
    var h = homes[brain];
    var d = ts ? new Date(ts) : new Date();
    // Them ms + duoi ngau nhien: /files/write GHI DE im lang, 2 tin ghi nho cung giay la mat 1.
    var stamp = d.getFullYear() + pad2(d.getMonth() + 1) + pad2(d.getDate()) +
      "-" + pad2(d.getHours()) + pad2(d.getMinutes()) + pad2(d.getSeconds()) +
      "-" + String(d.getMilliseconds()).padStart(3, "0") + Math.random().toString(36).slice(2, 5);
    var path = (h ? h.replace(/\/+$/, "") + "/" : "") + "sources/ghi-nho-" + stamp + ".md";
    // title giup lo ingest/wiki doc nhanh; JSON.stringify = chuoi YAML hai-nhay hop le.
    var title = text.replace(/\s+/g, " ").slice(0, 80);
    var content = "---\ntype: source\nsource_kind: chat\nstatus: unprocessed\ntitle: " +
      JSON.stringify(title) + "\ncreated: " + d.toISOString() + "\n---\n\n" + text + "\n";
    var fd = new FormData();
    fd.append("brain", brain);
    fd.append("path", path);
    fd.append("content", content);
    var r = await fetch("/files/write", { method: "POST", body: fd });
    var out = await r.json().catch(function () { return {}; });
    if (!out.ok) throw new Error(out.error || tw("bf.err"));
    return path;
  }

  // -------- 3) `path.md` trong tin nguoi dung -> link bam mo trinh sua --
  // Chay TREN chuoi da escapeHtml: backtick khong bi escape nen van so khop duoc.
  // Chi nhan chuoi giong path vault (co duoi file, khong ky tu cam, khong ".."),
  // khop doi theo codeFilePath cua chat-render.js.
  function linkifyMd(escaped) {
    return String(escaped || "").replace(/`([^`\n]{2,240})`/g, function (m, p) {
      var c = String(p).trim().replace(/\\/g, "/").replace(/^\.?\//, "");
      if (!/\.[a-z0-9]{1,6}$/i.test(c)) return m;
      if (/[:<>"|?*\[\]&]/.test(c)) return m;
      if (c.indexOf("/") < 0 && !/\.md$/i.test(c)) return m;
      if (/(^|\/)\.\.(\/|$)/.test(c)) return m;
      return '<a href="#open=' + encodeURIComponent(c) + '" data-vault-path="' + c +
        '" class="jv-floc">' + m + "</a>";
    });
  }

  window.JoyceChatFile = { toggle: toggle, hide: hide, remember: remember, linkifyMd: linkifyMd };
})();
