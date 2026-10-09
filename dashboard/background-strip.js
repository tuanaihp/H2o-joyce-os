/* background-strip.js - dải "đang chạy ngầm" ngay trên khung nhập.
 *
 * VÌ SAO CÓ FILE NÀY
 * Chủ repo báo (2026-08-06): "có agent chạy ngầm thì anh cũng không biết là nó đang chạy thật
 * hay không, không giống Claude nếu đang chạy ngầm thì vẫn có báo ở đầu hội thoại. Đây là
 * không thấy gì luôn và không chạy luôn."
 *
 * Đúng cả hai vế. Khung chat trước bản này KHÔNG hiện một chữ nào về việc nền: việc Kanban,
 * loop, nhắc hẹn đều sống ở trang khác. Muốn biết phải tự mở trang Việc - mà người dùng thì
 * không có lý do gì để nghĩ là phải mở. Tệ hơn, điều phối Kanban mặc định TẮT nên việc giao
 * từ chat nằm im vô thời hạn, và đó cũng là thứ không hiện ở đâu cả.
 *
 * VÀ VÌ SAO NÓ CHỈ CÒN HAI MỨC
 * Bản đầu có thêm mức xám "đang chờ tới giờ" gom cả nhắc hẹn lẫn loop. Chủ repo báo lại ngay
 * hôm sau (2026-08-07, kèm ảnh): "sao lại hiển thị 9 việc nền như này? anh không muốn vào chat
 * mà hiện ra như này đâu." Chín cái đó là chín nhắc hẹn đang đợi tới giờ - không chạy, không
 * hỏng, không cần ai làm gì, và trang Việc định kỳ đã liệt kê sẵn. Dải này trả lời đúng MỘT
 * câu hỏi: "ngay lúc này có cái gì đang chạy cho tôi không". Nhắc hẹn chờ tới giờ trả lời
 * "không", mà "không" thì phải im lặng chứ không phải dựng một khối chữ giữa khung chat.
 *
 * Còn lại hai mức, cả hai đều là thứ người dùng phải BIẾT NGAY:
 *   - đang chạy thật  -> chấm xanh nhấp nháy + tên việc đang chạy
 *   - đã giao, đang xếp hàng, điều phối TẮT -> chấm vàng + nói thẳng là nó KHÔNG tự chạy
 *   - còn lại          -> ẩn hẳn dải
 */
(function () {
  "use strict";

  // Chữ hiện ra lấy từ từ điển. Trong trình duyệt là window.t (i18n/index.js nạp trước mọi
  // module này); dưới node - nơi test require() thẳng file này - `window` CHƯA KHAI BÁO nên
  // đọc window.t là ReferenceError chứ không phải undefined, phải hỏi bằng typeof. Ở đó đọc
  // thẳng vi.json để hàm vẫn trả về chữ thật, không phải mã khoá.
  function tw(khoa, bien) {
    if (typeof window !== "undefined" && window.t) return window.t(khoa, bien);
    try {
      var s = require("./i18n/vi.json")[khoa] || khoa;
      return String(s).replace(/\{(\w+)\}/g, function (m, ten) {
        return (bien && bien[ten] != null) ? String(bien[ten]) : m;
      });
    } catch (e) { return khoa; }
  }

  var POLL_LIVE_MS = 6000;    // dải đang hiện việc: theo sát, trạng thái đổi từng nhịp
  var POLL_QUIET_MS = 20000;  // không có gì để hiện: vẫn hỏi nhưng thưa, đỡ quấy máy chủ
  var POLL_HIDDEN_MS = 60000; // tab ẩn: quay lại là hỏi ngay một nhát nên để rất thưa
  var MAX_CHIP = 4;           // dải là chỗ liếc mắt; muốn xem hết thì có nút sang trang Việc
  var timer = null, inflight = false, lastKey = "", dangHien = false, dangChay = false;
  // Nút × của chủ repo (2026-10-09): "hiện báo công việc như này ko có dấu X để a tắt".
  // Tắt = im đúng TRẠNG THÁI hiện tại (key); dữ liệu đổi - việc mới xếp, việc bắt đầu chạy -
  // thì hiện lại, vì đó là thông tin mới chứ không phải nhắc lại cái cũ.
  var dismissedKey = "";

  // Hai bảng này giữ KHOÁ từ điển chứ không giữ chữ: file còn chạy dưới node (test thuần)
  // nên không được tra từ điển lúc nạp, chỉ tra lúc vẽ - lúc đó chắc chắn có window.
  var NHAN = {
    running: "bgs.status.running", review: "bgs.status.review", blocked: "bgs.status.blocked",
    ready: "bgs.status.ready", todo: "bgs.status.todo", triage: "bgs.status.triage",
    enabled: "bgs.status.enabled", pending: "bgs.status.pending"
  };
  var LOAI = { task: "bgs.kind.task", loop: "bgs.kind.loop", reminder: "bgs.kind.reminder",
               job: "bgs.kind.job" };
  function nhan(x) { return NHAN[x] ? tw(NHAN[x]) : x; }
  function loai(x) { return LOAI[x] ? tw(LOAI[x]) : x; }

  /* Phần QUYẾT ĐỊNH tách thành hàm thuần: không đụng DOM nên test bằng node được, và mọi luật
     "hiện hay không, hiện cái gì" nằm gọn một chỗ thay vì rải trong lúc dựng HTML. */
  function quyetDinh(d) {
    var data = d || {};
    var items = data.items || [];
    // Máy chủ đời trước không gửi `level` - suy lại từ hai con số đếm, đừng ẩn nhầm dải.
    var muc = data.level || (data.running_count ? "run"
      : (data.stalled_count ? "stall" : "idle"));
    if (!items.length || (muc !== "run" && muc !== "stall")) {
      return { hien: false, muc: "idle", dau: "", chips: [], them: 0, warn: "" };
    }

    var chips = items.filter(function (x) {
      return muc === "run" ? x.status === "running" : !!x.stalled;
    });
    if (!chips.length) chips = items;   // máy chủ cũ không đánh dấu `stalled`
    var them = Math.max(0, chips.length - MAX_CHIP);
    chips = chips.slice(0, MAX_CHIP);

    var dau;
    if (muc === "run") dau = tw("bgs.dau_run", { count: data.running_count || chips.length });
    else dau = tw("bgs.dau_stall", { count: data.stalled_count || chips.length });
    var cua_toi = 0;
    for (var i = 0; i < chips.length; i++) if (chips[i].mine) cua_toi++;
    if (cua_toi) dau += " · " + tw("bgs.cua_hoi_thoai", { count: cua_toi });

    var warn = "", orch = data.orchestration || "off";
    if (muc === "stall") {
      warn = tw("bgs.warn_xep_hang", { muc: orch });
    }
    return { hien: true, muc: muc, dau: dau, chips: chips, them: them, warn: warn, orch: orch };
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { quyetDinh: quyetDinh };
  if (typeof document === "undefined") return;   // chạy bằng node (test): chỉ lấy hàm thuần

  function el() { return document.getElementById("bgStrip"); }

  function sid() {
    try { return (window.JoyceSessions && window.JoyceSessions.current()) || ""; }
    catch (e) { return ""; }
  }

  function brain() {
    try { return (window.JoyceSessions && window.JoyceSessions.brain()) || "brain"; }
    catch (e) { return "brain"; }
  }

  function esc(t) {
    return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // POST form như console.js (FormData + brain) - nudge/orchestration đều nhận kiểu này.
  function postAct(url, fields) {
    try {
      var f = new FormData();
      f.append("brain", brain());
      if (fields) for (var k in fields) f.append(k, fields[k]);
      return fetch(url, { method: "POST", body: f, credentials: "same-origin" })
        .then(function (r) { return r.json(); });
    } catch (err) { return null; }
  }

  function hide() {
    var e = el();
    if (e) { e.hidden = true; e.innerHTML = ""; }
    lastKey = "";
    dangHien = false;
  }

  function render(d) {
    var e = el();
    if (!e) return;
    // Voice V1: orb ghi hậu tố "N việc nền" từ đúng con số này (không có thì 0).
    try { if (window.JoyceOrb) window.JoyceOrb.setBackground((d && d.running_count) || 0); } catch (err) {}
    // Voice V3: số việc nền do BỘ NÃO GIỌNG giao cho chính cuộc nói chuyện này. Joyce dùng số
    // này để tự hỏi thăm ("em vẫn đang xem") thay vì bắt người dùng hỏi mới biết.
    try { if (window.JoyceOrb && window.JoyceOrb.setVoiceJobs) window.JoyceOrb.setVoiceJobs((d && d.voice_count) || 0); } catch (err) {}
    var q = quyetDinh(d);
    if (!q.hien) { hide(); return; }

    // Khoá so sánh: không vẽ lại DOM khi không có gì đổi. Vẽ lại mỗi nhịp làm nháy chấm nhấp
    // nháy và làm mất selection nếu người dùng đang bôi đen tên việc.
    var key = JSON.stringify([q.muc, q.dau, q.them, q.orch, q.chips.map(function (x) {
      return [x.kind, x.id, x.status, x.mine].join("|");
    })]);
    if (key === dismissedKey) return;   // đã bấm × đúng trạng thái này rồi
    dangHien = true;
    if (key === lastKey) return;
    lastKey = key;

    var chips = q.chips.map(function (x) {
      return '<span class="bg-chip' + (x.mine ? " mine" : "") +
        (x.status === "running" ? " on" : "") + '" title="' +
        esc(loai(x.kind)) + " · " + esc(nhan(x.status)) +
        (x.mine ? " · " + esc(tw("bgs.chip_mine")) : "") + '">' +
        '<b>' + esc(loai(x.kind)) + '</b> ' + esc(x.title) +
        ' <i>' + esc(nhan(x.status)) + '</i></span>';
    }).join("");
    if (q.them) chips += '<span class="bg-chip">' + esc(tw("bgs.chip_more", { so: q.them })) + "</span>";

    e.hidden = false;
    e.className = "bg-strip bg-" + q.muc;
    var xIco = (typeof ic === "function") ? ic("x") : "&times;";
    // Stall: dải tự xử được - "Chạy ngay" nhặt việc kế tiếp (giữ nguyên chế độ), "Bật tự vận
    // hành" đổi orchestration sang auto. Lời giải thích dài gọn vào tooltip của pill mode.
    var modePill = "", actBtns = "";
    if (q.muc === "stall") {
      modePill = '<span class="bg-mode" title="' + esc(q.warn) + '">' + esc(q.orch) + '</span>';
      var playIco = (typeof ic === "function") ? ic("play") : "";
      var zapIco = (typeof ic === "function") ? ic("zap") : "";
      var runPri = (q.orch === "manual") ? " pri" : "";
      var autoPri = (q.orch === "manual") ? "" : " pri";
      actBtns =
        '<button type="button" class="bg-act' + runPri + '" data-act="run" title="' +
        esc(tw("bgs.act_run_now_title")) + '">' + playIco + esc(tw("bgs.act_run_now")) + '</button>' +
        '<button type="button" class="bg-act' + autoPri + '" data-act="auto" title="' +
        esc(tw("bgs.act_auto_title")) + '">' + zapIco + esc(tw("bgs.act_auto")) + '</button>';
    }
    e.innerHTML =
      '<div class="bg-head"><span class="bg-dot"></span><span class="bg-title">' + esc(q.dau) +
      '</span>' + modePill + actBtns +
      '<button type="button" class="bg-open">' + esc(tw("bgs.open_kanban")) +
      '</button><button type="button" class="bg-x" aria-label="' + esc(tw("bgs.close")) +
      '" title="' + esc(tw("bgs.close")) + '">' + xIco + '</button></div>' +
      '<div class="bg-chips">' + chips + '</div>';

    var btn = e.querySelector(".bg-open");
    if (btn) btn.onclick = function () {
      try { window.Alpine.store("nav").go("kanban"); } catch (err) { location.hash = "#kanban"; }
    };
    var nutX = e.querySelector(".bg-x");
    if (nutX) nutX.onclick = function () { dismissedKey = lastKey; hide(); };
    e.querySelectorAll(".bg-act").forEach(function (b) {
      b.onclick = function () {
        b.disabled = true;
        var p = postAct(b.dataset.act === "run" ? "/kanban/nudge"
          : "/kanban/orchestration", b.dataset.act === "run" ? null : { mode: "auto" });
        (p || Promise.resolve()).then(refresh, refresh);
      };
    });
  }

  function refresh() {
    var e = el();
    if (!e || inflight) return null;
    var s = sid();
    inflight = true;
    var url = "/background?brain=" + encodeURIComponent(brain()) +
      "&chat_id=" + encodeURIComponent(s ? "web:" + s : "");
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d && d.ok) render(d); })
      .catch(function () { /* mất mạng thì giữ nguyên dải cũ, đừng nháy */ })
      .then(function () { inflight = false; });
  }

  function tick() {
    if (timer) { clearTimeout(timer); timer = null; }
    // Hẹn nhịp SAU khi câu trả lời về, vì nhịp phụ thuộc `dangHien` mà `dangHien` chỉ đúng sau
    // khi render xong. Hẹn trước thì mỗi lần từ rỗng chuyển sang có việc phải đợi hết một nhịp
    // thưa mới bám sát được - đúng lúc người dùng cần thấy nhất.
    var hen = function () {
      if (!dangChay) return;
      timer = setTimeout(tick, document.hidden ? POLL_HIDDEN_MS
        : (dangHien ? POLL_LIVE_MS : POLL_QUIET_MS));
    };
    var p = refresh();
    if (p && p.then) p.then(hen, hen); else hen();
  }

  function start() { if (!dangChay) { dangChay = true; tick(); } }
  function stop() {
    dangChay = false;
    if (timer) { clearTimeout(timer); timer = null; }
  }

  document.addEventListener("visibilitychange", function () {
    // Quay lại tab: hỏi NGAY một nhát rồi mới về nhịp thường. Người dùng rời máy 10 phút rồi
    // quay lại mà phải đợi thêm một nhịp mới thấy số đúng là đủ để họ kết luận "lại không chạy".
    if (!document.hidden) tick();
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();

  // Đổi hội thoại thì dải cũ không còn đúng nữa: xoá ngay rồi hỏi lại, đừng để chip của phiên
  // trước nằm lại vài giây trên phiên mới.
  window.JoyceBackground = {
    refresh: refresh,
    reset: function () { dismissedKey = ""; hide(); refresh(); },
    start: start,
    stop: stop
  };
})();
