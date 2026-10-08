// JOYCE OS - Trang Kinh doanh (nhóm Năng lực).
//
// Trang cha cho các công cụ kinh doanh của H2O. Tab con đầu tiên là "Xưởng content AI":
// workspace tạo/duyệt/bàn giao tài sản nội dung cho H2O Studio và Thủy H2O Academy,
// dựng từ prototype standalone (xuong-content.html) nhúng bằng iframe để giữ nguyên
// giao diện + logic demo của bản thiết kế mà không viết lại.
//
// Cơ chế tab con y hệt Cẩm nang: rail có mục con (KD_SUBS trong console.js), bấm sub
// gọi goSub -> openSub, bấm thẳng mục cha -> render() đọc window.__kdSub.
// Thêm tab con mới = thêm 1 dòng KD_SUBS + 1 entry KD_VIEWS ở đây.
(function () {
  "use strict";

  // id tab con -> cách vẽ. "Xưởng content AI" là trang nhúng iframe; tab sau có thể
  // là renderer riêng (hàm) tuỳ nhu cầu.
  const KD_VIEWS = {
    xuongcontent: { iframe: "/static/xuong-content.html", title: "Xưởng content AI" },
  };
  const KD_DEFAULT = "xuongcontent";

  let _el = null;      // container đang gắn trang (để openSub vẽ lại tại chỗ)
  let _sub = null;     // tab con đang hiển thị
  let _css = false;

  // Iframe cần khung cao tuyệt đối: trang này đi kèm chế độ cview-hoi-thoai (ẩn head
  // chung, body flex cột) nên .kd-page flex:1 là đủ; height:100% phòng lúc class đó
  // chưa kịp bật.
  function _injectCss() {
    if (_css) return;
    _css = true;
    const s = document.createElement("style");
    s.textContent =
      ".kd-page{display:flex;flex-direction:column;flex:1 1 auto;min-height:0;height:100%}" +
      ".kd-frame{flex:1 1 auto;width:100%;height:100%;min-height:420px;border:0;border-radius:12px;background:#071319}";
    document.head.appendChild(s);
  }

  function _ve(el, id) {
    const view = KD_VIEWS[id] || KD_VIEWS[KD_DEFAULT];
    id = KD_VIEWS[id] ? id : KD_DEFAULT;
    // Đổi sub mà cùng loại khung thì chỉ cần đổi src, khỏi dựng lại DOM (iframe giữ
    // trạng thái khi quay lại đúng sub đang mở).
    if (view.iframe) {
      const fr = el.querySelector("iframe.kd-frame");
      if (fr && _sub === id) return;
      if (fr) { fr.src = view.iframe; fr.title = view.title; _sub = id; return; }
      el.innerHTML = `<div class="kd-page"><iframe class="kd-frame" src="${view.iframe}" title="${view.title}"></iframe></div>`;
    }
    _sub = id;
  }

  window.JoyceKinhDoanh = {
    render(el) {
      _injectCss();
      _el = el;
      // __kdSub do store.nav.goSub đặt trước khi đổi trang (giống __cnSub của Cẩm nang);
      // đọc xong xoá ngay để lần render sau không bị kẹt tab con cũ.
      const muon = (typeof window !== "undefined" && window.__kdSub) || KD_DEFAULT;
      try { window.__kdSub = null; } catch (e) {}
      _ve(el, muon);
    },
    openSub(id) {
      if (_el && _el.isConnected) { _ve(_el, id); return; }
      try { window.__kdSub = id; } catch (e) {} // trang chưa mở: render() sẽ đọc
    },
  };
})();
