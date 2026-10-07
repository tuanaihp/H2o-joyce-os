// ============================================
// POPUP MICRO RIÊNG CỦA JOYCE - thay cho alert() của trình duyệt.
//
// Chủ repo (2026-10-05): bật mic mà bật ra hộp "ballet-sky...trycloudflare.com says" của
// trình duyệt thì vừa xấu vừa khó hiểu. Việc ở đây:
//   1. explain(kind): báo lỗi mic bằng popup của app (đúng nguyên nhân, kèm các bước sửa
//      theo THIẾT BỊ + trình duyệt đang dùng). Đang mở mà người dùng cấp lại quyền qua ổ khoá
//      thì popup TỰ nhận ra (Permissions API onchange) và đổi sang nút "Gọi Joyce ngay".
//   2. gate() ở đầu nút mic: quyền chưa từng hỏi -> popup của Joyce giải thích trước, rồi
//      mới để trình duyệt hỏi; quyền đang bị chặn -> báo luôn, không mở cuộc gọi chắc chắn
//      hỏng. Hộp hỏi quyền của CHÍNH trình duyệt thì không app nào thay được (rào bảo mật).
//   3. ĐIỆN THOẠI, không cần cài gì (chủ repo, cùng ngày, kèm ảnh iPhone): mở link Joyce từ
//      Telegram/Zalo/Facebook là vào TRÌNH DUYỆT NHÚNG của app đó, nơi trang web gần như
//      không bao giờ được dùng micro. Popup có nút "Mở bằng Safari" (x-safari-https://, iOS
//      17+) / "Mở bằng Chrome" (intent:// trên Android) + "Chép link" làm đường lui. Trình
//      duyệt nhúng kiểu SFSafariViewController báo UA y hệt Safari nên KHÔNG dò được chắc
//      chắn - vì vậy nút Mở bằng Safari luôn có trong popup "micro bị chặn" trên iPhone.
// Permissions API không có (Firefox cũ...) thì gate() cho đi thẳng như trước.
// ============================================
(function () {
  "use strict";

  var perm = null;          // "granted" | "denied" | "prompt" | null (không đọc được)
  var dlg = null, onPermChange = null, lastFocus = null;
  var inAppBypass = false;  // người dùng chọn "Vẫn thử ở đây" trong trình duyệt nhúng

  function t(k) { return (window.t && window.t(k)) || k; }

  function watchPermission() {
    try {
      if (!navigator.permissions || !navigator.permissions.query) return;
      navigator.permissions.query({ name: "microphone" }).then(function (st) {
        perm = st.state;
        st.onchange = function () {
          perm = st.state;
          if (onPermChange) onPermChange(perm);
        };
      }).catch(function () { perm = null; });
    } catch (e) { perm = null; }
  }

  // ---------- thiết bị + trình duyệt ----------
  function env() {
    var ua = navigator.userAgent || "";
    var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && (navigator.maxTouchPoints || 0) > 1);
    var android = /Android/i.test(ua);
    var os = ios ? "ios" : android ? "android" : /Windows/.test(ua) ? "windows" : /Mac OS X|Macintosh/.test(ua) ? "mac" : "other";
    var appName = (ua.match(/Zalo|Telegram|FBAN|FBAV|FB_IAB|Instagram|Messenger|Line\/|MicroMessenger|TikTok|musical_ly|Twitter/i) || [""])[0];
    var standalone = !!(navigator.standalone || (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches));
    // iOS: WKWebView trần (không phải Safari/Chrome/Firefox/Edge iOS, không phải web app màn
    // hình chính) không mang chữ "Safari/" trong UA. Android: WebView mang "; wv)".
    var iosWebView = ios && !standalone && !/Safari\//.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
    var androidWebView = android && /; wv\)/.test(ua);
    return { os: os, inApp: !!appName || iosWebView || androidWebView, browser: browserKey(ua) };
  }
  // Cốc Cốc/Edge/Chrome cùng nhân Chromium nhưng tên menu khác; Safari và Firefox để quyền
  // ở chỗ khác hẳn.
  function browserKey(ua) {
    if (/coc_coc|CocCoc/i.test(ua)) return "coccoc";
    if (/Edg\/|EdgiOS/.test(ua)) return "edge";
    if (/Firefox\/|FxiOS/.test(ua)) return "firefox";
    if (/Safari\//.test(ua) && !/Chrome\/|Chromium\/|CriOS/.test(ua)) return "safari";
    return "chrome";
  }
  var BROWSER_STEP = {
    coccoc: "micdlg.step_lock_coccoc", edge: "micdlg.step_lock_edge", chrome: "micdlg.step_lock_chrome",
    firefox: "micdlg.step_lock_firefox", safari: "micdlg.step_lock_safari",
  };
  var OS_HINT = { windows: "micdlg.denied_os", mac: "micdlg.denied_mac", ios: "micdlg.denied_ios",
                  android: "micdlg.denied_android" };

  // Link mở đúng trang này bằng trình duyệt thật của máy.
  function safariUrl() { return /^https:/.test(location.href) ? "x-safari-" + location.href : ""; }
  function chromeUrl() {
    return "intent://" + location.host + location.pathname + location.search + location.hash +
      "#Intent;scheme=" + location.protocol.replace(":", "") + ";package=com.android.chrome;end";
  }
  function openOutAction(e) {
    if (e.os === "ios" && safariUrl()) return { label: t("micdlg.open_safari"), href: safariUrl(), cls: "pri" };
    if (e.os === "android") return { label: t("micdlg.open_chrome"), href: chromeUrl(), cls: "pri" };
    return null;
  }

  // Nội dung theo từng loại. Khoá i18n viết TƯỜNG MINH để test i18n dò được.
  function content(kind) {
    var e = env();
    switch (kind) {
      case "ask":
        return { tone: "info", title: t("micdlg.ask_title"), body: t("micdlg.ask_body"),
                 steps: [t("micdlg.ask_step1"), t("micdlg.ask_step2")],
                 actions: [{ label: t("micdlg.later"), act: "close" }, { label: t("micdlg.allow"), act: "retry", cls: "pri" }] };
      case "inapp": {
        var out = openOutAction(e);
        return { tone: "warn",
                 title: t(e.os === "android" ? "micdlg.inapp_title_android" : "micdlg.inapp_title"),
                 body: t("micdlg.inapp_body"),
                 steps: e.os === "android" ? [t("micdlg.inapp_step_android"), t("micdlg.inapp_step_copy")]
                                           : [t("micdlg.inapp_step_ios"), t("micdlg.inapp_step_copy")],
                 actions: [{ label: t("micdlg.copy_link"), act: "copy" }].concat(out ? [out] : [])
                          .concat([{ label: t("micdlg.try_here"), act: "bypass", cls: "ghost" }]) };
      }
      case "denied": {
        var steps = e.os === "ios" ? [t("micdlg.step_ios_aa"), t("micdlg.step_ios_allow"), t("micdlg.step_retry")]
          : e.os === "android" ? [t("micdlg.step_android_lock"), t("micdlg.step_allow"), t("micdlg.step_retry")]
          : [t(BROWSER_STEP[e.browser]), t("micdlg.step_allow"), t("micdlg.step_retry")];
        var acts = [{ label: t("micdlg.close"), act: "close" }, { label: t("micdlg.retry"), act: "retry", cls: "pri" }];
        // Điện thoại: có thể đang ở trình duyệt nhúng mà không dò được -> luôn cho lối ra.
        var out2 = (e.os === "ios" || e.os === "android") ? openOutAction(e) : null;
        if (out2) acts.push({ label: out2.label, href: out2.href, cls: "ghost" });
        return { tone: "warn", title: t("micdlg.denied_title"), body: t("micdlg.denied_body"), steps: steps,
                 hint: OS_HINT[e.os] ? t(OS_HINT[e.os]) : "", actions: acts, watch: true };
      }
      case "insecure":
        return { tone: "warn", title: t("app.mic_insecure"), body: t("app.mic_insecure_fix"),
                 actions: [{ label: t("micdlg.close"), act: "close" }] };
      case "none":
        return { tone: "warn", title: t("app.mic_none"), body: t("app.mic_none_fix"),
                 actions: [{ label: t("micdlg.close"), act: "close" }, { label: t("micdlg.retry"), act: "retry", cls: "pri" }] };
      case "service":
        return { tone: "warn", title: t("app.mic_service_blocked"),
                 body: t(e.os === "ios" ? "micdlg.service_ios" : "app.mic_service_blocked_fix"),
                 actions: [{ label: t("micdlg.close"), act: "close" }] };
      case "unsupported":
      case "voice_unsupported": {
        var out3 = e.inApp ? openOutAction(e) : null;
        return { tone: "warn", title: t(kind === "unsupported" ? "app.mic_unsupported" : "app.voice_unsupported"),
                 body: t(e.os === "ios" ? "micdlg.unsupported_ios" : "micdlg.unsupported_body"),
                 actions: [{ label: t("micdlg.close"), act: "close" }].concat(out3 ? [out3] : []) };
      }
      default:
        return { tone: "warn", title: String(kind || ""), actions: [{ label: t("micdlg.close"), act: "close" }] };
    }
  }

  var MIC_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"></rect>' +
    '<path d="M5 11a7 7 0 0 0 14 0M12 18v3M8.5 21h7"></path></svg>';
  var MIC_OFF_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18"></path>' +
    '<path d="M9 9v2a3 3 0 0 0 5.1 2.1M15 9.3V6a3 3 0 0 0-5.7-1.3"></path>' +
    '<path d="M5 11a7 7 0 0 0 11.5 5.4M19 11a7 7 0 0 1-.6 2.8M12 18v3M8.5 21h7"></path></svg>';

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function close(result) {
    if (!dlg) return;
    var d = dlg, cb = d._done;
    dlg = null; onPermChange = null;
    d.classList.remove("open");
    document.removeEventListener("keydown", d._key, true);
    setTimeout(function () { if (d.parentNode) d.parentNode.removeChild(d); }, 200);
    try { if (lastFocus && lastFocus.focus) lastFocus.focus(); } catch (e) {}
    if (cb) cb(!!result);
  }

  // Xin quyền thật: mở rồi đóng ngay luồng mic. Thành công thì quyền đã "granted" - đường gọi
  // của app.js chạy tiếp mà không gặp lỗi nữa.
  function requestMic() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return Promise.resolve(false);
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (st) {
      try { st.getTracks().forEach(function (tr) { tr.stop(); }); } catch (e) {}
      perm = "granted";
      return true;
    }).catch(function (e) {
      var n = e && e.name;
      if (n === "NotAllowedError" || n === "SecurityError") perm = "denied";
      return n === "NotFoundError" ? "none" : false;
    });
  }

  function copyLink() {
    var url = location.href;
    if (window.JoyceCopy) return Promise.resolve(window.JoyceCopy(url)).then(function () { return true; }, function () { return false; });
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(url).then(function () { return true; }, function () { return false; });
    return Promise.resolve(false);
  }

  function open(kind, done) {
    if (dlg) close(false);
    var c = content(kind);
    lastFocus = document.activeElement;
    var d = document.createElement("div");
    d.className = "micdlg-overlay";
    var acts = c.actions || [];
    d.innerHTML =
      '<div class="micdlg tone-' + c.tone + '" role="alertdialog" aria-modal="true" aria-labelledby="micdlgTitle" aria-describedby="micdlgBody">' +
        '<div class="micdlg-ico">' + (c.tone === "info" ? MIC_SVG : MIC_OFF_SVG) + '<span class="micdlg-pulse"></span></div>' +
        '<div class="micdlg-title" id="micdlgTitle">' + esc(c.title) + "</div>" +
        (c.body ? '<div class="micdlg-body" id="micdlgBody">' + esc(c.body) + "</div>" : "") +
        (c.steps ? '<ol class="micdlg-steps">' + c.steps.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ol>" : "") +
        (c.hint ? '<div class="micdlg-hint">' + esc(c.hint) + "</div>" : "") +
        '<div class="micdlg-state" hidden></div>' +
        '<div class="micdlg-acts">' + acts.filter(function (a) { return a.cls !== "ghost"; }).map(actHtml).join("") + "</div>" +
        acts.filter(function (a) { return a.cls === "ghost"; }).map(actHtml).join("") +
      "</div>";
    function actHtml(a, i) {
      var cls = "micdlg-btn" + (a.cls === "pri" ? " micdlg-pri" : a.cls === "ghost" ? " micdlg-ghost" : " micdlg-sec");
      if (a.href) return '<a class="' + cls + '" href="' + esc(a.href) + '" rel="noopener">' + esc(a.label) + "</a>";
      return '<button type="button" class="' + cls + '" data-act="' + esc(a.act) + '">' + esc(a.label) + "</button>";
    }
    d._done = done;
    document.body.appendChild(d);
    dlg = d;
    requestAnimationFrame(function () { d.classList.add("open"); });

    var pri = d.querySelector('[data-act="retry"]');
    var stEl = d.querySelector(".micdlg-state");
    function say(cls, txt) { stEl.hidden = false; stEl.className = "micdlg-state " + cls; stEl.textContent = txt; }
    function showGranted() {
      say("ok", t("micdlg.granted"));
      if (pri) { pri.textContent = t("micdlg.call_now"); pri.dataset.go = "1"; }
    }
    d.querySelectorAll("[data-act]").forEach(function (b) {
      b.addEventListener("click", function () {
        var act = b.dataset.act;
        if (act === "close") { close(false); return; }
        if (act === "bypass") { inAppBypass = true; close(true); return; }
        if (act === "copy") {
          copyLink().then(function (ok) { say(ok ? "ok" : "bad", t(ok ? "micdlg.copied" : "micdlg.copy_fail") + (ok ? "" : " " + location.href)); });
          return;
        }
        if (act === "retry") {
          if (b.dataset.go === "1") { close(true); return; }
          b.disabled = true;
          requestMic().then(function (ok) {
            b.disabled = false;
            if (ok === true) { if (kind === "ask") close(true); else showGranted(); }
            else if (kind === "ask" && perm === "denied") {
              // Bấm "Chặn" ở hộp hỏi của trình duyệt -> chuyển sang popup chỉ cách cấp lại.
              var cb = d._done; d._done = null; close(false); open("denied", cb);
            }
            else say("bad", t(ok === "none" ? "app.mic_none" : "micdlg.still_denied"));
          });
        }
      });
    });
    d.addEventListener("click", function (e) { if (e.target === d) close(false); });
    d._key = function (e) {
      if (e.key === "Escape") { e.stopPropagation(); close(false); }
    };
    document.addEventListener("keydown", d._key, true);
    // Người dùng sửa quyền qua ổ khoá trong lúc popup đang mở -> nhận ra ngay.
    if (c.watch) onPermChange = function (s) { if (s === "granted") showGranted(); };
    setTimeout(function () { var f = d.querySelector(".micdlg-pri") || d.querySelector(".micdlg-btn"); if (f) f.focus(); }, 30);
  }

  // Lỗi từ voice.js (err của SpeechRecognition) / app.js -> loại popup.
  var ERR_KIND = { "not-allowed": "denied", "audio-capture": "none", "service-not-allowed": "service",
                   "not-supported": "unsupported" };

  window.JoyceMicDialog = {
    // Báo lỗi mic. Popup "Gọi Joyce ngay" (sau khi đã cấp lại quyền) bấm lại nút mic.
    explain: function (errOrKind) {
      var kind = ERR_KIND[errOrKind] || errOrKind;
      if (kind === "denied" && !window.isSecureContext) kind = "insecure";
      // Trình duyệt nhúng (Zalo/Telegram/Facebook...) chặn mic -> chỉ thẳng lối ra trình duyệt thật.
      if (kind === "denied" && env().inApp && !inAppBypass) kind = "inapp";
      open(kind, function (go) { if (go) redial(); });
    },
    // Gọi ở ĐẦU nút mic (khi đang chuẩn bị BẮT ĐẦU gọi). true = cứ gọi tiếp; false = popup đã
    // mở và sẽ tự gọi lại khi người dùng cho phép.
    gate: function () {
      if (env().inApp && !inAppBypass && perm !== "granted") {
        open("inapp", function (ok) { if (ok) redial(); });
        return false;
      }
      if (perm === "prompt") {
        open("ask", function (ok) { if (ok) redial(); });
        return false;
      }
      if (perm === "denied") {
        open(!window.isSecureContext ? "insecure" : (env().inApp && !inAppBypass) ? "inapp" : "denied", function (go) { if (go) redial(); });
        return false;
      }
      return true;
    },
    env: env,
    plan: content,          // nội dung popup theo loại - cho test, không mở gì
    permission: function () { return perm; },
    isOpen: function () { return !!dlg; },
    close: function () { close(false); },
  };

  function redial() {
    var vb = document.getElementById("voiceBtn");
    if (vb && !vb.classList.contains("in-call")) setTimeout(function () { vb.click(); }, 60);
  }

  watchPermission();
})();
