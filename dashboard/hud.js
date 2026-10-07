// ============================================
// JOYCE HUD - lớp nhìn thứ hai của khoang não, phong cách "MAYA": quả cầu sáng
// giữa màn, hai cột panel dữ liệu hai bên, dải sóng âm ở đáy.
//
// Thiết kế:
//   - Không đụng graph.js: khi HUD bật, CSS .hud-on che #graph2d + #conceptLabels
//     + .brain-stats. Starfield (vũ trụ + lưới sàn) vẫn vẽ bên dưới nên bầu không
//     khí giữ nguyên; đồ thị vẫn chạy ngầm nên quay lại là tức thì.
//   - Mức âm/trạng thái nghĩ đọc LẠI từ window.__joyceGraph (level + _thinking) -
//     pumpAudioLevel của app.js nạp chúng mỗi frame rồi, HUD khỏi tự nghe mic.
//   - Panel là dữ liệu THẬT từ endpoint có sẵn, nạp lại 45s/lần khi đang nhìn.
// ============================================
(function () {
  "use strict";

  var KEY = "joyce.hudView";          // "1" = HUD, "0"/vắng = tinh vân (mặc định)
  var active = false;
  var built = false;
  var host = null;                    // .hud-center
  var view = null;                    // #hudView
  var waveCv = null;
  var rafId = 0, clockId = 0, dataId = 0, napId = 0;
  var _lvl = 0;                       // mức âm đã làm trơn (vẽ orb + sóng)
  var _waveHist = [];                 // lịch sử mức âm cho dải sóng
  // H2O Alien Intelligence Planet (brain-planet.js). null = đang dùng quả cầu 2D cũ
  // (cờ joyce_alien_intelligence_planet_v1 = "0", hoặc file chưa nạp).
  var planet = null;
  var _insets = null, _insetsAt = 0;

  // Dữ liệu panel (nạp từ API)
  var D = {
    models: null, ollamaOn: false,
    facts: null, notes: null,
    sessions: [], nextRem: null, remCount: 0,
    projOn: 0, projTotal: 0, projItems: [],
    latencyMs: null,                      // RTT của fetch /memory/stats - proxy cho độ khoẻ lõi
    wx: null,                             // /business-weather (thời tiết kinh doanh)
    nap: null,                            // /brain/nap-status (Joyce đang nạp dữ liệu?)
  };
  // Thời tiết: bấm vào biểu tượng để XEM THỬ lần lượt từng kiểu (chủ muốn thấy đủ hiệu ứng
  // khi số thật chưa nối). null = theo số liệu.
  var WX_ORDER = ["nang", "nang_nhe", "nhieu_may", "mua", "giong", "bao", "loc_xoay"];
  var WX_ICON = { nang: "sun", nang_nhe: "cloud-sun", nhieu_may: "cloud", mua: "cloud-rain",
                  giong: "cloud-lightning", bao: "wind", loc_xoay: "tornado" };
  // Khoá viết TƯỜNG MINH để test i18n dò được từng khoá.
  var WX_KEY = { nang: "wx.nang", nang_nhe: "wx.nang_nhe", nhieu_may: "wx.nhieu_may", mua: "wx.mua",
                 giong: "wx.giong", bao: "wx.bao", loc_xoay: "wx.loc_xoay" };
  var _wxPreview = null;

  function t(k) { return (window.t && window.t(k)) || k; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function brainPath() {
    var sel = document.getElementById("graphSource");
    var v = sel ? sel.value : "";
    return v.indexOf("path:") === 0 ? v.slice(5) : "brain";
  }
  function fmtAgo(ts) {                // ts = giây epoch → "5p trước" / "2h" / "3n"
    var d = Math.max(0, Date.now() / 1000 - (ts || 0));
    if (d < 60) return t("hud.just_now");
    if (d < 3600) return Math.floor(d / 60) + " " + t("hud.min_ago");
    if (d < 86400) return Math.floor(d / 3600) + " " + t("hud.hour_ago");
    return Math.floor(d / 86400) + " " + t("hud.day_ago");
  }

  // ---------- Nạp dữ liệu ----------
  function jget(u) {
    return fetch(u, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }
  function jpost(u) {
    return fetch(u, { method: "POST", credentials: "same-origin", body: new URLSearchParams() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }
  // Đo RTT một fetch nhẹ: V2 muốn panel Hệ thống khoe độ trễ thật chứ không phải
  // một vạch "ok" suông. /memory/stats là truy vấn rẻ nhất đang gọi sẵn.
  function jgetTimed(u) {
    var t0 = performance.now();
    return fetch(u, { credentials: "same-origin" })
      .then(function (r) { D.latencyMs = Math.round(performance.now() - t0); return r.ok ? r.json() : null; })
      .catch(function () { D.latencyMs = null; return null; });
  }
  function refresh() {
    var b = encodeURIComponent(brainPath());
    Promise.all([
      jget("/ollama-local/installed"),
      jgetTimed("/memory/stats?brain=" + b),
      jget("/sessions?brain=" + b + "&limit=4"),
      jget("/reminders"),
      jpost("/h2o-projects/check"),     // ping sống toàn bộ app (registry không lưu trạng thái)
      jget("/business-weather"),
    ]).then(function (rs) {
      var ol = rs[0], mem = rs[1], ses = rs[2], rem = rs[3], pj = rs[4];
      if (rs[5] && rs[5].ok) D.wx = rs[5];
      D.ollamaOn = !!(ol && ol.ok && Array.isArray(ol.models));
      D.models = D.ollamaOn ? ol.models.length : null;
      D.facts = mem && mem.facts != null ? mem.facts : null;
      var g = window.__joyceGraph;
      try { D.notes = g && g.graph ? g.graph.graphData().nodes.length : null; } catch (e) {}
      D.sessions = (ses && ses.sessions) || [];
      var pend = (rem && rem.pending) || [];
      D.remCount = pend.length;
      D.nextRem = null;
      pend.forEach(function (r) {
        if (r.due_at && (!D.nextRem || r.due_at < D.nextRem.due_at)) D.nextRem = r;
      });
      var items = (pj && pj.results) || [];
      D.projItems = items;
      D.projTotal = items.length;
      D.projOn = items.filter(function (p) { return p.ok; }).length;
      _syncOrbit();
      paintPanels();
    });
  }

  // ---------- Panel ----------
  function row(k, v, cls) {
    return '<div class="hp-row"><span class="hp-k">' + esc(k) + '</span><span class="hp-v ' +
      (cls || "") + '">' + esc(v) + '</span></div>';
  }
  // Từ điển có thể về SAU lúc dựng panel (fetch bất đồng bộ) - nếu vẽ sớm
  // quá, tiêu đề sẽ kẹt key trần mãi mãi. data-tk + repaintTitles vá cả khi
  // i18n xong muộn lẫn khi đổi ngôn ngữ.
  function repaintTitles() {
    if (!built) return;
    view.querySelectorAll(".hp-title[data-tk], .planet-call-btn[data-tk], .hs-end[data-tk]").forEach(function (el) {
      el.textContent = t(el.dataset.tk);
    });
  }

  // ---------- Nhịp tim tri thức (sparkline) ----------
  // V2 muốn "knowledge pulse": số note+fact mỗi lần nạp được gom vào một lịch sử
  // localStorage và vẽ thành đường nhỏ. Dữ liệu TỰ TÍCH LUỸ trên máy - không giả,
  // mẫu đầu tiên chính là lần nạp này, càng dùng lâu đường càng có nghĩa.
  var KPULSE_KEY = "joyce.kpulse";
  function pulsePush(n) {
    if (n == null || !isFinite(n)) return;
    var arr;
    try { arr = JSON.parse(localStorage.getItem(KPULSE_KEY) || "[]"); } catch (e) { arr = []; }
    var last = arr.length ? arr[arr.length - 1] : null;
    // Chỉ thêm mẫu mới khi giá trị đổi hoặc đã qua ~10 phút - tránh nạp lại liên tục
    // làm dãy toàn một số lặp, sparkline thành đường phẳng vô nghĩa.
    if (last && last[1] === n && Date.now() / 1000 - last[0] < 600) return;
    arr.push([Math.floor(Date.now() / 1000), n]);
    if (arr.length > 60) arr = arr.slice(-60);
    try { localStorage.setItem(KPULSE_KEY, JSON.stringify(arr)); } catch (e) {}
  }
  function pulseData() {
    try { return JSON.parse(localStorage.getItem(KPULSE_KEY) || "[]"); } catch (e) { return []; }
  }
  function drawSpark(cv) {
    if (!cv) return;
    var ctx = cv.getContext("2d");
    var W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    var pts = pulseData().map(function (p) { return p[1]; });
    var light = document.documentElement.getAttribute("data-theme") === "light";
    var col = "rgba(56,189,248,";
    if (pts.length < 2) {                       // chưa đủ mẫu: gạch nền mờ, không bịa đường
      ctx.strokeStyle = col + (light ? 0.25 : 0.18) + ")";
      ctx.setLineDash([3, 4]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(2, H / 2); ctx.lineTo(W - 2, H / 2); ctx.stroke();
      ctx.setLineDash([]);
      return;
    }
    var min = Math.min.apply(null, pts), max = Math.max.apply(null, pts);
    var span = Math.max(1, max - min);
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = col + (light ? 0.85 : 0.9) + ")";
    ctx.beginPath();
    pts.forEach(function (v, i) {
      var x = 2 + (i / (pts.length - 1)) * (W - 4);
      var y = H - 3 - ((v - min) / span) * (H - 6);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    // Chấm sáng ở mẫu cuối - "nhịp hiện tại".
    var lx = W - 2, ly = H - 3 - ((pts[pts.length - 1] - min) / span) * (H - 6);
    ctx.fillStyle = col + "1)";
    ctx.beginPath(); ctx.arc(lx, ly, 2.2, 0, Math.PI * 2); ctx.fill();
  }

  // Thang tín hiệu lõi: gộp Ollama local + độ trễ lõi thành 1-5 vạch kiểu cột sóng.
  // Ollama chết không làm hệ sập nhưng đáng báo yếu đi; RTT cao cũng vậy.
  function signalLevel() {
    var lat = D.latencyMs;
    if (lat == null) return D.ollamaOn ? 2 : 0;
    var lv = lat < 150 ? 5 : lat < 400 ? 4 : lat < 900 ? 3 : lat < 2000 ? 2 : 1;
    if (!D.ollamaOn) lv = Math.min(lv, 3);      // lõi phụ offline -> tín hiệu không đầy
    return lv;
  }
  function signalHtml() {
    var lv = signalLevel();
    var bars = "";
    for (var i = 1; i <= 5; i++) bars += '<span class="hp-sb' + (i <= lv ? " on" : "") + '"></span>';
    var latTxt = D.latencyMs != null ? D.latencyMs + "ms" : "--";
    return '<div class="hp-sigrow"><span class="hp-signal lv' + lv + '">' + bars + "</span>" +
      '<span class="hp-lat">' + latTxt + "</span></div>";
  }

  function money(v) {
    v = +v || 0;
    if (v >= 1e9) return (v / 1e9).toFixed(2).replace(".", ",") + " " + t("hud.wx_ty");
    return (v / 1e6).toFixed(1).replace(".", ",") + " " + t("hud.wx_tr");
  }
  function wxKey() { return _wxPreview || (D.wx && D.wx.state) || null; }
  function paintWx() {
    var el = document.getElementById("hpWx");
    var key = wxKey();
    if (planet && key) planet.setWeather(key);
    if (!el) return;
    if (!key) { el.innerHTML = '<div class="hp-empty">' + t("hud.none") + "</div>"; return; }
    var w = D.wx || {};
    var ico = window.ic ? window.ic(WX_ICON[key] || "sun") : "";
    var html = '<button class="hp-wx-now wx-' + key + '" type="button" id="hpWxBtn" title="' + esc(t("hud.wx_preview_hint")) + '">' +
      '<span class="hp-wx-ico">' + ico + '</span><span class="hp-wx-lbl">' + esc(t(WX_KEY[key])) + "</span>" +
      (!_wxPreview && w.pct != null ? '<span class="hp-wx-pct">' + esc(w.pct) + "%</span>" : "") + "</button>";
    var tags = "";
    if (_wxPreview) tags += '<span class="hp-wx-tag pv">' + esc(t("hud.wx_preview")) + "</span>";
    if (w.nguon === "demo") tags += '<span class="hp-wx-tag">' + esc(t("hud.wx_demo")) + "</span>";
    if (tags) html += '<div class="hp-wx-tags">' + tags + "</div>";
    if (!_wxPreview && !w.an_so && w.doanh_thu_thang != null) {
      html += row(t("hud.wx_month"), money(w.doanh_thu_thang) + " / " + money(w.chi_tieu_thang_tien_do)) +
              row(t("hud.wx_today"), money(w.doanh_thu_hom_nay));
    }
    el.innerHTML = html;
    el.querySelector("#hpWxBtn").addEventListener("click", function () {
      var i = WX_ORDER.indexOf(_wxPreview);
      _wxPreview = i < 0 ? WX_ORDER[0] : (i + 1 < WX_ORDER.length ? WX_ORDER[i + 1] : null);
      paintWx();
    });
  }
  function paintNap() {
    var el = document.getElementById("hpNap");
    if (!el) return;
    var n = D.nap;
    if (n && n.active) {
      var what = (n.items && n.items[0]) || (n.learning ? t("hud.nap_learning") : "");
      el.innerHTML = '<div class="hp-nap"><span class="hp-nap-dot"></span><span class="hp-nap-k">' + esc(t("hud.nap_now")) +
        '</span><span class="hp-nap-v">' + esc(what) + "</span></div>";
    } else el.innerHTML = "";
  }
  function pollNap() {
    jget("/brain/nap-status?brain=" + encodeURIComponent(brainPath())).then(function (r) {
      if (!r) return;
      D.nap = r;
      if (planet) planet.setIngest(r);
      paintNap();
    });
  }

  function paintPanels() {
    repaintTitles();
    paintWx();
    var el;
    // Trái 1: đồng hồ (vẽ bởi tickClock - giờ + ngày + thanh tiến trình ngày)
    // Trái 2: hệ thống - tín hiệu + latency + engine + brain
    el = document.getElementById("hpSys");
    if (el) {
      var modelTxt = (document.getElementById("mbModelTxt") || {}).textContent || "";
      el.innerHTML =
        signalHtml() +
        row(t("hud.sys_ollama"), D.ollamaOn ? (t("hud.online") + " · " + D.models + " model") : t("hud.offline"), D.ollamaOn ? "ok" : "bad") +
        row(t("hud.sys_engine"), modelTxt || "-") +
        row(t("hud.sys_brain"), brainPath());
    }
    // Trái 3: vault - số liệu + nhịp tim tri thức
    el = document.getElementById("hpVault");
    if (el) {
      el.innerHTML =
        row(t("hud.vault_notes"), D.notes != null ? D.notes : "-") +
        row(t("hud.vault_facts"), D.facts != null ? D.facts : "-") +
        '<canvas class="hp-spark" id="hpSpark" width="150" height="26" aria-hidden="true"></canvas>' +
        '<div id="hpNap"></div>';
      // Chỉ ghi mẫu khi ÍT NHẤT một nguồn đã về - mẫu 0 lúc mạng chưa kịp trả
      // sẽ kéo đáy sparkline xuống sai lệch.
      if (D.notes != null || D.facts != null) pulsePush((D.notes || 0) + (D.facts || 0));
      drawSpark(document.getElementById("hpSpark"));
      paintNap();
    }
    // Phải 1: tín hiệu gần nhất (hội thoại mới)
    el = document.getElementById("hpChats");
    if (el) {
      el.innerHTML = D.sessions.length
        ? D.sessions.slice(0, 3).map(function (s) {
            return '<div class="hp-item"><span class="hp-dot"></span><span class="hp-txt">' +
              esc(s.title || s.preview || t("sess.untitled")) + '</span><span class="hp-when">' +
              fmtAgo(s.updated_at) + "</span></div>";
          }).join("")
        : '<div class="hp-empty">' + t("hud.none") + "</div>";
    }
    // Phải 2: lịch hẹn - nhãn + ĐẾM NGƯỢC (tickClock cập nhật mỗi giây)
    el = document.getElementById("hpSched");
    if (el) {
      el.innerHTML = D.nextRem
        ? '<div class="hp-count" id="hpCount"></div>' +
          row(t("hud.rem_next"), D.nextRem.label || D.nextRem.text || "-") +
          row(t("hud.rem_due"), D.nextRem.due_human || "-", "ok") +
          row(t("hud.rem_count"), D.remCount)
        : '<div class="hp-empty">' + t("hud.none") + "</div>";
      tickCount();
    }
    // Phải 3: ma trận hệ sinh thái - mỗi app một hàng chấm+tên, bấm mở app
    el = document.getElementById("hpProj");
    if (el) {
      el.innerHTML = D.projTotal
        ? row(t("hud.proj_online"), D.projOn + "/" + D.projTotal, D.projOn === D.projTotal ? "ok" : "warn") +
          '<div class="hp-matrix">' + D.projItems.slice(0, 8).map(function (p) {
            return '<a class="hp-mrow ' + (p.ok ? "on" : "off") + '" href="' + esc(p.url || "#") +
              '" target="_blank" rel="noopener" title="' + esc((p.ten || "") + " · " + (p.status || p.err || "")) + '">' +
              '<span class="hp-pdot ' + (p.ok ? "on" : "off") + '"></span>' +
              '<span class="hp-mname">' + esc(p.ten || p.url || "-") + "</span></a>";
          }).join("") + "</div>"
        : '<div class="hp-empty">' + t("hud.none") + "</div>";
    }
  }

  // ---------- Đồng hồ + tiến trình ngày + đếm ngược lịch hẹn ----------
  function tickClock() {
    var el = document.getElementById("hpTime");
    var d = new Date();
    if (el) {
      var hh = String(d.getHours()).padStart(2, "0"), mm = String(d.getMinutes()).padStart(2, "0");
      var days = t("hud.days").split("|");
      el.innerHTML =
        '<div class="hp-clock">' + hh + '<span class="hp-clk-sep">:</span>' + mm + "</div>" +
        '<div class="hp-date">' + days[d.getDay()] + " · " + String(d.getDate()).padStart(2, "0") +
        "/" + String(d.getMonth() + 1).padStart(2, "0") + "</div>" +
        '<div class="hp-daybar"><span class="hp-dayfill" style="width:' +
        ((d.getHours() * 3600 + d.getMinutes() * 60 + d.getSeconds()) / 86400 * 100).toFixed(1) + '%"></span></div>';
    }
    tickCount();
  }

  // Đếm ngược tới lịch hẹn gần nhất - chạy theo tickClock (1s). V2 muốn countdown
  // sống thay vì dòng giờ tĩnh. due_at là giây epoch (cùng hệ với fmtAgo).
  function tickCount() {
    var el = document.getElementById("hpCount");
    if (!el) return;
    if (!D.nextRem || !D.nextRem.due_at) { el.textContent = ""; return; }
    var left = Math.floor(D.nextRem.due_at - Date.now() / 1000);
    var s = Math.abs(left), txt;
    if (s >= 86400) txt = Math.floor(s / 86400) + t("hud.cd_d") + " " + Math.floor(s % 86400 / 3600) + "h";
    else if (s >= 3600) txt = Math.floor(s / 3600) + "h " + Math.floor(s % 3600 / 60) + "m";
    else txt = Math.floor(s / 60) + "m " + (s % 60) + "s";
    el.textContent = left >= 0 ? "T-" + txt : txt + " " + t("hud.cd_late");
    el.classList.toggle("late", left < 0);
  }

  // ---------- Thiên thể: mặt trời + mặt trăng ----------
  // H2O Legacy là MẶT TRỜI (quầng vàng, chiếu sáng tinh cầu). Mặt trăng là một dự án bất
  // kỳ: chủ ghim ở ngăn kéo ngữ cảnh ("Đặt làm Mặt trăng"), không ghim thì mỗi tuần trăng
  // mới tự chuyển sang dự án kế tiếp trong registry. Pha trăng do brain-planet.js tính
  // theo ngày thật. Các app còn lại là vệ tinh trên ba vành dữ liệu.
  var MOON_KEY = "joyce.planetMoon";
  function isSun(p) { return /legacy/i.test(String((p.ten || p.name || "") + " " + (p.id || ""))); }
  function moonPinned() { try { return localStorage.getItem(MOON_KEY) || ""; } catch (e) { return ""; } }
  function setMoonPin(id) {
    try { if (id) localStorage.setItem(MOON_KEY, id); else localStorage.removeItem(MOON_KEY); } catch (e) {}
  }
  function moonId(items) {
    var cands = items.filter(function (p) { return !isSun(p); });
    if (!cands.length) return null;
    var pin = moonPinned();
    if (pin && cands.some(function (p) { return (p.id || p.ten) === pin; })) return pin;
    var lun = window.JoycePlanet ? window.JoycePlanet.moonPhase(new Date()).lunation : 0;
    var p = cands[((lun % cands.length) + cands.length) % cands.length];
    return p.id || p.ten;
  }
  function healthList() {
    var mid = moonId(D.projItems), sunDone = false;
    return D.projItems.map(function (p) {
      var h = projHealth(p);
      if (!sunDone && isSun(p)) { h.role = "sun"; sunDone = true; }
      else if (mid && (p.id || p.ten) === mid) h.role = "moon";
      return h;
    });
  }
  function _syncOrbit() {
    if (planet) planet.setProjects(healthList());
  }

  // Kết quả ping của registry -> ProjectHealth cho tinh cầu. URL đi thẳng từ server
  // (/h2o-projects/check), client không giữ địa chỉ app nào.
  function projHealth(p) {
    var code = +p.status || 0, st;
    if (p.ok) st = (p.api_ok === false || (p.ms || 0) > 4000) ? "degraded" : "online";
    else st = (code === 401 || code === 403) ? "unauthorized" : "offline";
    return { id: p.id || p.ten, name: p.ten || p.name || p.url || "-", url: p.url || "", status: st,
             ms: p.ms, httpStatus: code, err: p.err, ssl_days: p.ssl_days, api_ok: p.api_ok,
             vercel: p.vercel };
  }

  // ---------- Gương mặt trong khung hologram ----------
  // Nhân viên H2O đang đăng nhập và đã cài ảnh trong hồ sơ -> gương mặt của họ (Joyce nói
  // chuyện thay họ). Còn lại là Joyce: khuôn mặt Linh vật đã cài, không có thì logo Branding.
  function persona() {
    var st = window.__h2oStaff;
    if (st && st.avatar_v) {
      return { key: "st:" + st.id + ":" + st.avatar_v, staff: true, name: st.ten || "",
               src: "/staff/avatar/" + encodeURIComponent(st.id) + "?v=" + encodeURIComponent(st.avatar_v) };
    }
    return { key: "joyce", staff: false, name: "J O Y C E", src: joyceFaceSrc() };
  }
  function joyceFaceSrc() {
    try {
      if (window.JoycePet && window.JoycePet.usingMark && window.JoycePet.usingMark()) {
        var svg = window.JoycePet.markSvg();
        // <img> + data:image/svg+xml cần xmlns tường minh - chuỗi pet.js vẽ cho innerHTML
        // không mang theo (innerHTML tự suy không gian tên, Image thì không).
        if (svg && svg.indexOf("xmlns") < 0) svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ');
        if (svg) return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
      }
    } catch (e) {}
    return "/brand-logo";
  }

  // ---------- Khung hologram khi gọi ----------
  // Bấm tinh cầu = gọi Joyce. Lúc đường gọi mở, một màn hình điện tử dựng lên từ tinh cầu
  // (tinh cầu tự hạ xuống làm nền - brain-planet.js setInCall), ôm gương mặt người đang nói
  // chuyện. Trạng thái, đồng hồ, nút Tắt mic / Cúp máy đều MƯỢN của thanh gọi sẵn có, không
  // có đường gọi thứ hai.
  var _holo = { on: false, face: "", h: 0, n: 0, st: "" };
  function holoEl() { return view && view.querySelector("#holoScreen"); }
  function paintHoloFace(force) {
    var el = holoEl();
    if (!el) return;
    var ps = persona();
    if (!force && _holo.face === ps.key) return;
    _holo.face = ps.key;
    var img = el.querySelector(".hs-av");
    el.classList.remove("hs-noimg");
    // Ảnh hỏng -> logo Branding; logo cũng hỏng -> chữ J phát sáng (CSS), không để khung trống.
    img.onerror = function () {
      if (img.src.indexOf("/brand-logo") < 0) img.src = "/brand-logo";
      else { img.onerror = null; el.classList.add("hs-noimg"); }
    };
    img.src = ps.src;
    el.querySelector(".hs-name").textContent = ps.name;
    el.classList.toggle("hs-staff", ps.staff);
  }
  function updateHolo(call, state) {
    var el = holoEl();
    if (!el) return;
    if (call !== _holo.on) {
      _holo.on = call;
      if (call) {
        paintHoloFace(true);
        el.hidden = false;
        _holo.h = 0;
        requestAnimationFrame(function () { el.classList.add("on"); });
      } else {
        el.classList.remove("on");
        setTimeout(function () { if (!_holo.on) el.hidden = true; }, 520);
      }
    }
    if (!call) return;
    // Neo theo tinh cầu ĐANG hạ: đáy khung chạm vùng khí quyển phía trên hành tinh.
    if (!_holo.h || (_holo.n++ % 30) === 0) _holo.h = el.offsetHeight || 300;
    var g = planet && planet.planetGeom();
    if (g) {
      el.style.left = g.cx + "px";
      el.style.top = Math.max(50, g.cy - g.R * 0.55 - _holo.h) + "px";
    }
    if (state !== _holo.st) { _holo.st = state; el.dataset.st = state; }
    var os = document.getElementById("orbState");
    var stEl = el.querySelector(".hs-st");
    var txt = os ? os.textContent : "";
    if (stEl.textContent !== txt) stEl.textContent = txt;
    var ck = document.querySelector(".call-clock");
    var tEl = el.querySelector(".hs-time");
    var ct = ck ? ck.textContent : "";
    if (tEl.textContent !== ct) tEl.textContent = ct;
    var mb = document.querySelector(".call-mute");
    var mEl = el.querySelector(".hs-mute");
    if (mb && mEl.textContent !== mb.textContent) {
      mEl.textContent = mb.textContent;
      mEl.setAttribute("aria-pressed", mb.getAttribute("aria-pressed") || "false");
    }
    el.style.setProperty("--amp", _lvl.toFixed(3));
    var bars = el.querySelectorAll(".hs-wave i");
    var now = performance.now() / 1000;
    for (var i = 0; i < bars.length; i++) {
      var h = 3 + _lvl * 26 * (0.35 + 0.65 * Math.abs(Math.sin(i * 0.74 + now * 6.2)));
      bars[i].style.height = h.toFixed(1) + "px";
    }
  }

  // ---------- Dải sóng đáy ----------
  function drawWave() {
    var ctx = waveCv.getContext("2d");
    var W = waveCv.width, H = waveCv.height;
    var light = document.documentElement.getAttribute("data-theme") === "light";
    _waveHist.push(_lvl);
    if (_waveHist.length > 90) _waveHist.shift();
    ctx.clearRect(0, 0, W, H);
    var n = 72, bw = W / n, mid = H / 2;
    for (var i = 0; i < n; i++) {
      var idx = Math.floor((i / n) * _waveHist.length);
      var v = _waveHist[idx] || 0;
      var env = 0.5 + 0.5 * Math.sin(i / 2.7 + performance.now() / 480);
      var h = Math.max(1.5, (v * 0.95 + 0.03) * H * env + (v > 0.02 ? 0 : 0));
      var a = (0.18 + v * 0.8) * (light ? 0.6 : 1);
      ctx.fillStyle = "rgba(56,189,248," + a + ")";
      ctx.fillRect(i * bw + bw * 0.18, mid - h / 2, bw * 0.64, h);
    }
  }

  function loop(now) {
    if (!active) return;
    if (planet) feedPlanet();
    drawWave();
    rafId = requestAnimationFrame(loop);
  }

  // ---------- Tinh cầu mới: nạp trạng thái THẬT mỗi khung ----------
  // Nguồn duy nhất là những gì app.js đã vẽ ra: lớp của #orbState (do capNhatOrb() ghi từ
  // turn.state của đạo diễn giọng nói), cờ in-call của nút mic, trạng thái thanh gọi
  // (__joyceCallState, chỉ có "connecting" là orb không mang) và mức âm đã làm trơn của
  // đồ thị (pumpAudioLevel nạp từ voice.getLevel() = max(mic, loa)). Không timeout giả.
  function inCallNow() {
    var vb = document.getElementById("voiceBtn");
    return !!(vb && vb.classList.contains("in-call"));
  }
  function joyceState() {
    var os = document.getElementById("orbState");
    var cls = " " + (os ? os.className : "") + " ";
    if (cls.indexOf(" error ") >= 0) return "ERROR";
    if (cls.indexOf(" reconnecting ") >= 0) return "RECONNECTING";
    if (cls.indexOf(" paused ") >= 0) return "INTERRUPTING";
    if (cls.indexOf(" speaking ") >= 0) return "SPEAKING";
    if (cls.indexOf(" thinking ") >= 0) return "THINKING";
    if (cls.indexOf(" listening ") >= 0) return "LISTENING";
    if (inCallNow() && window.__joyceCallState === "connecting") return "CONNECTING";
    return "READY";
  }
  function feedPlanet() {
    var g = window.__joyceGraph;
    var target = Math.min(1, (g ? (g.level || 0) : 0) * 2.2);
    _lvl += (target - _lvl) * 0.12;
    var call = inCallNow();
    var st = joyceState();
    planet.setJoyceState(st);
    planet.setAudioAmplitude(_lvl);
    planet.setInCall(call);
    updateHolo(call, st);
  }

  // Chỗ hai cột telemetry + công tắc trên + nhãn trạng thái dưới đang chiếm, để camera
  // tinh cầu tự co lại khi cột hội thoại/sidebar đổi cỡ. Đọc layout tốn, nên giữ 500ms.
  function planetInsets() {
    var now = performance.now();
    if (_insets && now - _insetsAt < 500) return _insets;
    var hr = host.getBoundingClientRect();
    var quanSat = host.classList.contains("brain-overlays-hidden");
    function side(el, left) {
      if (quanSat) return 0;     // Chế độ Quan sát: khung đã ẩn, tinh cầu lấy trọn bề ngang
      if (!el || getComputedStyle(el).display === "none") return 0;
      var r = el.getBoundingClientRect();
      if (!r.width) return 0;
      return left ? Math.max(0, r.right - hr.left + 10) : Math.max(0, hr.right - r.left + 10);
    }
    _insets = { left: side(view.querySelector(".hud-left"), true),
                right: side(view.querySelector(".hud-right"), false),
                top: 46, bottom: hr.height < 420 ? 84 : 112 };
    _insetsAt = now;
    return _insets;
  }

  function mountPlanet() {
    if (planet || !built || !window.JoycePlanet) return;
    var stage = view.querySelector("#planetStage");
    if (!stage) return;
    try {
      planet = window.JoycePlanet.create({
        insets: planetInsets,
        onPlanetClick: function () { var vb = document.getElementById("voiceBtn"); if (vb) vb.click(); },
        onSatelliteClick: function (p) { openCtx(p); },
        onBackgroundClick: function () { if (_ctxId != null) closeCtx(); },
      });
      planet.mount(stage);
    } catch (e) {
      try { console.warn("[hud] tinh cầu không dựng được:", e); } catch (_) {}
      if (planet) { try { planet.destroy(); } catch (_) {} }
      planet = null;
      return;
    }
    view.classList.add("planet-mode");
    _insets = null;
    if (D.projItems.length) planet.setProjects(healthList());
    if (wxKey()) planet.setWeather(wxKey());
    if (D.nap) planet.setIngest(D.nap);
    if (!active) planet.pause();
  }
  function unmountPlanet() {
    if (!planet) return;
    planet.destroy();
    planet = null;
    closeCtx();
    updateHolo(false, "READY");
    view.classList.remove("planet-mode");
  }

  // ---------- Ngăn kéo ngữ cảnh dự án (bấm vệ tinh) ----------
  // Bấm vệ tinh KHÔNG mở app ngay: xem trạng thái trước, rồi mới chọn Mở / Kiểm tra lại.
  var _ctxId = null;
  // Khoá viết TƯỜNG MINH (không ghép "planet.st_" + ...) để test i18n dò được từng khoá.
  var ST_KEY = { online: "planet.st_online", degraded: "planet.st_degraded",
                 offline: "planet.st_offline", unauthorized: "planet.st_unauthorized" };
  function openCtx(p) {
    var box = view && view.querySelector("#planetCtx");
    if (!box || !p) return;
    _ctxId = p.id;
    var stTxt = t(ST_KEY[p.status] || ST_KEY.offline);
    var rows = [
      [t("planet.http"), p.httpStatus || "-"],
      [t("planet.latency"), p.ms != null ? p.ms + " ms" : "-"],
      [t("planet.ssl"), p.ssl_days != null ? p.ssl_days + " " + t("hud.day_ago") : "-"],
      [t("planet.api"), p.api_ok == null ? "-" : (p.api_ok ? "OK" : t("planet.st_offline"))],
      [t("planet.vercel"), (p.vercel && p.vercel.trang_thai) || "-"],
    ];
    if (p.err) rows.push([t("planet.err"), p.err]);
    if (p.role === "sun") rows.unshift([t("planet.role"), t("planet.role_sun")]);
    if (p.role === "moon" && planet) {
      var mi = planet.moonInfo();
      rows.unshift([t("planet.moon_phase"), t(mi.key) + " · " + Math.round(mi.illum * 100) + "%"]);
      rows.unshift([t("planet.role"), t(moonPinned() ? "planet.role_moon_pin" : "planet.role_moon_auto")]);
    }
    // Ghim mặt trăng: mọi app trừ mặt trời. Đang là trăng ghim -> nút bỏ ghim.
    var moonBtn = "";
    if (p.role === "moon" && moonPinned()) moonBtn = '<button class="pc-btn pc-moon" type="button" data-moon="">' + esc(t("planet.moon_unpin")) + "</button>";
    else if (p.role !== "sun" && p.role !== "moon") moonBtn = '<button class="pc-btn pc-moon" type="button" data-moon="' + esc(p.id) + '">' + esc(t("planet.moon_pin")) + "</button>";
    box.innerHTML =
      '<div class="pc-head"><span class="pc-dot st-' + esc(p.status) + '"></span>' +
        '<span class="pc-name">' + esc(p.name) + '</span>' +
        '<button class="pc-x" type="button" aria-label="' + esc(t("planet.close")) + '">&times;</button></div>' +
      '<div class="pc-st st-' + esc(p.status) + '">' + esc(stTxt) + "</div>" +
      rows.map(function (r) { return row(r[0], r[1]); }).join("") +
      '<div class="pc-acts">' +
        (p.url ? '<a class="pc-btn pc-open" href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(t("planet.open_app")) + "</a>" : "") +
        '<button class="pc-btn pc-re" type="button">' + esc(t("planet.recheck")) + "</button>" +
      "</div>" +
      (moonBtn ? '<div class="pc-acts">' + moonBtn + "</div>" : "") +
      // Nút ẩn rõ ràng (chủ báo 06/10: không biết cách tắt khung - nút x góc trên từng bị
      // nút Timelapse đè lên). Esc và bấm vào khoảng trống trên vũ trụ cũng đóng.
      '<div class="pc-acts"><button class="pc-btn pc-hide" type="button">' + esc(t("planet.hide")) + "</button></div>";
    box.hidden = false;
    box.querySelector(".pc-x").addEventListener("click", closeCtx);
    box.querySelector(".pc-hide").addEventListener("click", closeCtx);
    box.querySelector(".pc-re").addEventListener("click", function (e) { recheck(p.id, e.currentTarget); });
    var mb = box.querySelector(".pc-moon");
    if (mb) mb.addEventListener("click", function () {
      setMoonPin(mb.dataset.moon || "");
      _syncOrbit();
      var again = healthList().filter(function (h) { return h.id === p.id; })[0];
      if (again) openCtx(again);
    });
    var x = box.querySelector(".pc-x"); if (x) x.focus();
  }
  function closeCtx() {
    var box = view && view.querySelector("#planetCtx");
    if (box) { box.hidden = true; box.innerHTML = ""; }
    _ctxId = null;
  }
  function recheck(id, btn) {
    if (btn) { btn.disabled = true; btn.textContent = t("planet.checking"); }
    fetch("/h2o-projects/check", { method: "POST", credentials: "same-origin", body: new URLSearchParams({ ten: id || "" }) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (js) {
        var res = js && js.results && js.results[0];
        if (res) {
          D.projItems = D.projItems.map(function (q) { return (q.id || q.ten) === (res.id || res.ten) ? res : q; });
          D.projOn = D.projItems.filter(function (q) { return q.ok; }).length;
          _syncOrbit(); paintPanels();
          if (_ctxId === id) {
            var again = healthList().filter(function (h) { return h.id === (res.id || res.ten); })[0];
            openCtx(again || projHealth(res));
          }
        } else if (btn) { btn.disabled = false; btn.textContent = t("planet.recheck"); }
      });
  }

  // ---------- Dựng / gỡ ----------
  function build() {
    if (built) return;
    view = document.createElement("div");
    view.id = "hudView";
    view.innerHTML =
      // Tinh cầu mới phủ kín khoang (đứng ĐẦU để hai cột panel nằm đè lên trên nó).
      '<div id="planetStage"></div>' +
      '<div class="hud-col hud-left">' +
        '<div class="hud-panel"><div class="hp-title" data-tk="hud.time"></div><div id="hpTime"></div></div>' +
        '<div class="hud-panel hp-wx-panel"><div class="hp-title" data-tk="hud.wx_title"></div><div id="hpWx"></div></div>' +
        '<div class="hud-panel"><div class="hp-title" data-tk="hud.system"></div><div id="hpSys"></div></div>' +
        '<div class="hud-panel"><div class="hp-title" data-tk="hud.vault"></div><div id="hpVault"></div></div>' +
      "</div>" +
      '<div class="hud-col hud-right">' +
        '<div class="hud-panel"><div class="hp-title" data-tk="hud.chats"></div><div id="hpChats"></div></div>' +
        '<div class="hud-panel"><div class="hp-title" data-tk="hud.schedule"></div><div id="hpSched"></div></div>' +
        '<div class="hud-panel"><div class="hp-title" data-tk="hud.projects"></div><div id="hpProj"></div></div>' +
      "</div>" +
      '<canvas id="hudWave"></canvas>' +
      '<div class="planet-ctx" id="planetCtx" role="dialog" hidden></div>' +
      '<div class="holo-screen" id="holoScreen" role="region" aria-live="polite" hidden>' +
        '<div class="hs-frame">' +
          '<span class="hs-c hs-tl"></span><span class="hs-c hs-tr"></span><span class="hs-c hs-bl"></span><span class="hs-c hs-br"></span>' +
          '<div class="hs-bar"><span class="hs-live">LIVE</span><span class="hs-link">H2O · JOYCE LINK</span><span class="hs-time"></span></div>' +
          '<div class="hs-view"><img class="hs-av" alt=""><span class="hs-scan"></span><span class="hs-sweep"></span></div>' +
          '<div class="hs-name"></div>' +
          '<div class="hs-st"></div>' +
          '<div class="hs-wave">' + new Array(25).join("<i></i>") + "</div>" +
          '<div class="hs-acts"><button class="hs-btn hs-mute" type="button" aria-pressed="false"></button>' +
            '<button class="hs-btn hs-end" type="button" data-tk="call.hangup"></button></div>' +
        "</div>" +
      "</div>" +
      // Cửa DOM cho việc cốt lõi: canvas không phải lối duy nhất để gọi Joyce (bàn phím,
      // trình đọc màn hình). Ẩn khỏi mắt cho tới khi được focus bằng phím.
      '<button class="planet-call-btn" id="planetCallBtn" type="button" data-tk="planet.call_btn"></button>';
    host.appendChild(view);
    waveCv = view.querySelector("#hudWave");
    view.querySelector(".hs-mute").addEventListener("click", function () {
      var b = document.querySelector(".call-mute"); if (b) b.click();
    });
    view.querySelector(".hs-end").addEventListener("click", function () {
      var b = document.querySelector(".call-hangup");
      if (b) b.click(); else { var vb = document.getElementById("voiceBtn"); if (vb) vb.click(); }
    });
    view.querySelector("#planetCallBtn").addEventListener("click", function () {
      var vb = document.getElementById("voiceBtn"); if (vb) vb.click();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && _ctxId != null) closeCtx();
      // Phím H: bật/tắt Chế độ Quan sát (ẩn mọi khung để ngắm vũ trụ). Không bắt khi đang gõ.
      if ((e.key === "h" || e.key === "H") && active && !e.ctrlKey && !e.metaKey && !e.altKey) {
        var tg = e.target || {}, tag = (tg.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select" || tg.isContentEditable) return;
        var eye = document.getElementById("brainOverlayToggle");
        if (eye) { e.preventDefault(); eye.click(); _insets = null; }
      }
    });
    // Chế độ Quan sát: rê chuột sát mép trái/phải thì khung bên đó ló ra để xem nhanh.
    host.addEventListener("mousemove", function (e) {
      if (!active || !host.classList.contains("brain-overlays-hidden")) return;
      var r = host.getBoundingClientRect(), x = e.clientX - r.left;
      host.classList.toggle("hud-peek-l", x < 70);
      host.classList.toggle("hud-peek-r", x > r.width - 70);
    });
    host.addEventListener("mouseleave", function () { host.classList.remove("hud-peek-l", "hud-peek-r"); });
    built = true;
  }

  function sizeCanvases() {
    if (!built) return;
    _insets = null;                     // cột panel có thể vừa đổi cỡ theo khung
    var r = host.getBoundingClientRect();
    waveCv.width = Math.round(r.width * 0.5); waveCv.height = 56;
    waveCv.style.width = "50%"; waveCv.style.height = "56px";
  }

  function show() {
    build();
    active = true;
    host.classList.add("hud-on");
    mountPlanet();
    if (planet) planet.resume();
    sizeCanvases();
    tickClock(); paintPanels(); refresh();
    clockId = setInterval(tickClock, 1000);
    dataId = setInterval(refresh, 45000);
    pollNap();
    napId = setInterval(pollNap, 3000);
    rafId = requestAnimationFrame(loop);
    window.addEventListener("resize", sizeCanvases);
    localStorage.setItem(KEY, "1");
    var btn = document.getElementById("hudViewBtn");
    if (btn) btn.setAttribute("aria-pressed", "true");
    // brain-v2.js nghe sự kiện này để đồng bộ công tắc Lõi nước / Tinh vân.
    try { window.dispatchEvent(new Event("joyce:hud-view")); } catch (e) {}
  }
  function hide() {
    active = false;
    host.classList.remove("hud-on");
    if (planet) planet.pause();
    closeCtx();
    cancelAnimationFrame(rafId);
    clearInterval(clockId); clearInterval(dataId); clearInterval(napId);
    window.removeEventListener("resize", sizeCanvases);
    localStorage.setItem(KEY, "0");
    var btn = document.getElementById("hudViewBtn");
    if (btn) btn.setAttribute("aria-pressed", "false");
    try { window.dispatchEvent(new Event("joyce:hud-view")); } catch (e) {}
  }

  window.JoyceHud = {
    toggle: function () { (active ? hide : show)(); },
    isOn: function () { return active; },
    set: function (on) { if (!!on !== active) (on ? show : hide)(); },
    planet: function () { return planet; },
  };

  // Bật/tắt cờ joyce_alien_intelligence_planet_v1 lúc đang chạy (JoycePlanet.setEnabled):
  // dựng lại renderer để nó chọn hồ sơ mới - cờ tắt = bản Canvas 2D nhẹ, không shader.
  // (Quả cầu 2D thời trước đã gỡ theo yêu cầu chủ 2026-10-05; muốn xem lại thì xem git.)
  window.addEventListener("joyce:planet-flag", function () {
    if (!built) return;
    unmountPlanet();
    mountPlanet();
    if (planet && active) planet.resume();
  });
  // Nhân viên vừa đổi ảnh hồ sơ -> khung hologram dùng ảnh mới ngay.
  window.addEventListener("joyce:staff-avatar", function () { paintHoloFace(true); });

  document.addEventListener("DOMContentLoaded", function () {
    host = document.querySelector(".hud-center");
    var btn = document.getElementById("hudViewBtn");
    if (!host || !btn) return;
    btn.addEventListener("click", function () { window.JoyceHud.toggle(); });
    // Tab Dự án thêm/xoá app → bắn sự kiện này; HUD nạp lại để vệ tinh xuất
    // hiện/biến mất ngay thay vì chờ nhịp 45s.
    window.addEventListener("joyce-h2o-projects-change", function () { if (active) refresh(); });
    // Từ điển về muộn / đổi ngôn ngữ → vẽ lại tiêu đề panel.
    window.addEventListener("joyce:i18n", repaintTitles);
    if (localStorage.getItem(KEY) === "1") show();
    // Giao diện tinh cầu admin chỉnh ở Cài đặt -> Giao diện Joyce -> Quả tinh cầu. Máy chủ là
    // nguồn sự thật cho MỌI máy (nhân viên cũng đọc được GET /settings); localStorage chỉ là bản
    // nhớ tạm để mở trang là có ngay, nên hỏi SAU khi đã vẽ, không bắt tinh cầu chờ mạng.
    if (window.JoycePlanet && window.JoycePlanet.hydrateLook) {
      jget("/settings").then(function (j) {
        var pl = j && j.dashboard && j.dashboard.planet;
        if (pl && typeof pl === "object") window.JoycePlanet.hydrateLook(pl);
      });
    }
  });
})();
