/* chat-dock.js — khung hội thoại NỔI bên phải, mở từ menu pet "Trò chuyện".
 *
 * Vì sao có file này: trước đây bấm "Trò chuyện" ở pet là nhảy hẳn sang trang chat,
 * mất ngữ cảnh đang đứng (đang duyệt Tệp tin, đang xem Việc...). Chủ muốn khung chat
 * trượt ra bên phải để VỪA đọc hướng dẫn của Joyce VỪA thao tác trên trang đang mở.
 *
 * Không dựng khung chat thứ hai. Node chat THẬT (callBar, chatArea, bgStrip, attachBar,
 * modelBar, hudVoice) được MƯỢN qua window.JoyceChatBorrow - y hệt cách trang Trò chuyện,
 * Cộng sự và Code vẫn mượn (_borrowChatNodes trong console.js). Mượn node thật nghĩa là
 * mọi handler gửi/mic/đính kèm/streaming/picker model sống nguyên, và cùng một phiên:
 * mở dock lên thấy tiếp đúng cuộc đang chat, đóng dock là nó quay về chỗ cũ.
 *
 * Dock KHÔNG có nền mờ và không tự đóng khi bấm ra ngoài - cố tình, vì cả mục đích của
 * nó là để người dùng thao tác trang phía sau. Đóng bằng nút ✕ hoặc mở lại menu pet.
 */
(function () {
  var dock = null, slot = null;

  function dung() {
    if (dock) return;
    var ic = function (ten) { return window.ic ? window.ic(ten) : ""; };
    var ti = function (k, d) {
      try { var s = window.t && window.t(k); return s && s !== k ? s : d; } catch (e) { return d; }
    };
    dock = document.createElement("aside");
    dock.id = "chatDock";
    dock.className = "chat-dock";
    dock.hidden = true;
    dock.innerHTML =
      '<div class="cd-head">' +
        '<span class="cd-title">' + ic("message-circle") + ' ' + ti("chat.panel", "HỘI THOẠI") + '</span>' +
        '<span class="cd-acts">' +
          '<button class="mini-btn" id="cdFull" title="' + ti("chat.zoom", "Mở trang Trò chuyện") + '">' + ic("maximize") + '</button>' +
          '<button class="mini-btn" id="cdClose" title="' + ti("common.close", "Đóng") + '">' + ic("x") + '</button>' +
        '</span>' +
      '</div>' +
      '<div class="cd-slot" id="chatDockSlot"></div>';
    document.body.appendChild(dock);
    slot = dock.querySelector("#chatDockSlot");
    dock.querySelector("#cdFull").onclick = function () {
      dong();
      if (window.JoyceNav) JoyceNav.go("chat");
    };
    dock.querySelector("#cdClose").onclick = dong;
    // Khi node chat bị trang khác mượn lại (người dùng điều hướng sang trang Trò chuyện/
    // Cộng sự/Code trong lúc dock đang mở), slot của dock trở nên rỗng → tự xếp dock đi,
    // đừng để một khung rỗng treo trên màn hình.
    new MutationObserver(function () {
      if (dock.hidden || !slot) return;
      if (!slot.contains(document.getElementById("chatArea"))) {
        dock.hidden = true;
        document.body.classList.remove("chat-dock-on");
      }
    }).observe(slot, { childList: true });
  }

  function mo() {
    if (dock && !dock.hidden) { dong(); return; }
    if (!window.JoyceChatBorrow) { if (window.JoyceNav) JoyceNav.go("chat"); return; }
    dung();
    // Node đang được một trang khác giữ (Trò chuyện/Cộng sự/Code): trả về HUD rồi mượn
    // vào dock. Trang đó lượt render kế tiếp tự mượn lại nên không hỏng gì.
    if (JoyceChatBorrow.held()) JoyceChatBorrow.back();
    JoyceChatBorrow.borrow(slot);
    dock.hidden = false;
    document.body.classList.add("chat-dock-on");
    var ci = document.getElementById("chatInput");
    if (ci) setTimeout(function () { try { ci.focus(); } catch (e) {} }, 140);
  }

  function dong() {
    if (!dock || dock.hidden) return;
    // Chỉ TRẢ node khi chúng thật sự đang nằm trong dock. Nếu người dùng vừa điều hướng
    // sang trang Trò chuyện, renderChat đã mượn node ra khỏi dock rồi - gọi back() lúc
    // này sẽ xé node khỏi chính trang đó.
    if (slot && slot.contains(document.getElementById("chatArea"))) JoyceChatBorrow.back();
    dock.hidden = true;
    document.body.classList.remove("chat-dock-on");
  }

  window.JoyceChatDock = {
    mo: mo,
    dong: dong,
    toggle: mo,
    isOpen: function () { return !!(dock && !dock.hidden); },
  };
})();
