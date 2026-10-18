// ============================================
// BRAIN CHAMBER V2 - vỏ ngoài mới cho khoang não.
//   - Công tắc lớp nhìn có nhãn (#brainViewSwitch): "Lõi nước" (HUD cầu + telemetry
//     của hud.js) <-> "Tinh vân" (đồ thị graph.js). Điều khiển qua window.JoyceHud
//     nên trạng thái lưu trong localStorage key cũ "joyce.hudView" vẫn đi theo.
//   - Drawer cài đặt trải nghiệm (#expDrawer): MƯỢN node #quickSet - cùng node mà
//     trang Cài đặt nhúng - để giọng nói / ảnh đại diện / tên miền mở được ngay
//     từ màn Brain mà không rời cột hội thoại. Đóng drawer thì node về
//     #quickSetHolder, đúng cơ chế parkQuickSet() của console.js.
// ============================================
(function () {
  "use strict";

  // ---------- Công tắc lớp nhìn ----------
  function initSwitch() {
    var sw = document.getElementById("brainViewSwitch");
    if (!sw) return;
    var btns = {};
    sw.querySelectorAll(".bvs-btn").forEach(function (b) { btns[b.dataset.view] = b; });

    function paint() {
      var onHud = !!(window.JoyceHud && window.JoyceHud.isOn());
      // Tab "hd" = 3D Joyce (pho tượng hạt, joyce-humanoid.js). humOn là lựa chọn
      // người dùng, không phải renderer - nên vẫn sáng đúng khi HUD vừa bật lại.
      var humOn = !!(window.JoyceHud && window.JoyceHud.humanoidOn && window.JoyceHud.humanoidOn());
      ["hd", "core", "graph"].forEach(function (v) {
        var b = btns[v]; if (!b) return;
        var active = v === "hd" ? (onHud && humOn) : v === "core" ? (onHud && !humOn) : !onHud;
        b.classList.toggle("active", active);
        b.setAttribute("aria-selected", active ? "true" : "false");
      });
    }

    sw.addEventListener("click", function (e) {
      var b = e.target.closest(".bvs-btn");
      if (!b || !window.JoyceHud) return;
      var v = b.dataset.view;
      if (v === "hd" || v === "core") {
        // Đặt lựa chọn humanoid TRƯỚC khi bật HUD: show() -> applyHum() đọc _humOn
        // một lần, khỏi lắp ráp rồi tắt ngay khi chuyển giữa hai lớp nhìn.
        if (window.JoyceHud.setHumanoid) window.JoyceHud.setHumanoid(v === "hd");
        if (typeof window.JoyceHud.set === "function") window.JoyceHud.set(true);
        else window.JoyceHud.toggle();
      } else {
        if (typeof window.JoyceHud.set === "function") window.JoyceHud.set(false);
        else window.JoyceHud.toggle();
      }
      paint();
    });

    // Lớp nhìn còn đổi từ nơi khác (phím tắt, localStorage của tab khác, nút icon cũ
    // nếu ai đó bật lại) - hud.js bắn sự kiện này sau mỗi lần show/hide.
    window.addEventListener("joyce:hud-view", paint);
    window.addEventListener("joyce:humanoid-view", paint);
    window.addEventListener("joyce:i18n", paint);
    paint();
  }

  // ---------- Drawer cài đặt trải nghiệm ----------
  function initDrawer() {
    var drawer = document.getElementById("expDrawer");
    var shade = document.getElementById("expShade");
    var body = document.getElementById("expDrawerBody");
    var btn = document.getElementById("expDrawerBtn");
    if (!drawer || !shade || !body || !btn) return;

    function quickSet() { return document.getElementById("quickSet"); }
    function holder() { return document.getElementById("quickSetHolder"); }

    function open() {
      var qs = quickSet();
      // #quickSet có thể đang nằm trong trang Cài đặt (#cviewBody). Trang Cài đặt
      // chỉ hiện khi rời màn Brain, còn drawer chỉ bấm được trên màn Brain, nên hai
      // nơi không giành nhau. Vẫn kiểm tra: node đang ở ngoài cviewBody thì mới mượn.
      if (qs && qs.parentNode && !qs.closest("#cviewBody")) body.appendChild(qs);
      drawer.hidden = false;
      shade.hidden = false;
      requestAnimationFrame(function () { drawer.classList.add("open"); });
      btn.setAttribute("aria-pressed", "true");
    }
    function close() {
      var qs = quickSet(), h = holder();
      drawer.classList.remove("open");
      if (qs && qs.parentNode === body && h) h.appendChild(qs);
      setTimeout(function () { drawer.hidden = true; shade.hidden = true; }, 220);
      btn.setAttribute("aria-pressed", "false");
    }
    function isOpen() { return !drawer.hidden; }

    btn.addEventListener("click", function () { isOpen() ? close() : open(); });
    shade.addEventListener("click", close);
    var x = document.getElementById("expClose");
    if (x) x.addEventListener("click", close);
    var full = document.getElementById("expFull");
    if (full) full.addEventListener("click", function () {
      close();
      try { if (window.Alpine) Alpine.store("nav").go("settings"); } catch (e) {}
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen()) close();
    });
    // Bấm sang trang quản lý (rail) hoặc nút Cài đặt trên topbar: console.js
    // parkQuickSet() rút node khỏi drawer - đóng luôn để không treo lớp phủ.
    document.addEventListener("click", function (e) {
      if (!isOpen()) return;
      if (e.target.closest(".rail-item") || e.target.closest("#settingsBtn")) close();
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () {
    initSwitch(); initDrawer();
  });
  else { initSwitch(); initDrawer(); }
})();
