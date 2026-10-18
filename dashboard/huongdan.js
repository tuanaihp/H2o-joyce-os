/* dashboard/huongdan.js - tab "Hướng dẫn vận hành Joyce" trong trang Cài đặt.
   Thư viện vận hành cho CEO mới: lưới thẻ theo vùng vận hành, bấm vào đọc bản
   markdown đầy đủ. Nội dung sống ở brains/Brain Default/wiki/van-hanh/*.md nên
   cùng một tài liệu Joyce cũng trả lời được trong chat khi CEO hỏi thẳng. */
(function () {
  "use strict";
  const BRAIN = "Brain Default";   // _brain_root tự resolve tên -> Brain Default
  const DIR = "wiki/van-hanh";
  const DOCS = [
    { slug: "00-ban-do-tong-quan",        title: "Bản đồ tổng quan",         icon: "globe",          hook: "Joyce là gì, sơ đồ tổng, các trang chính, 3 nguyên tắc vận hành." },
    { slug: "10-doi-48-tro-ly",           title: "Đội hình 48 trợ lý",       icon: "users",          hook: "48 trợ lý phòng ban, 3 tầng model, trí nhớ riêng từng người." },
    { slug: "20-viec-kanban-duyet",       title: "Việc, Kanban & cổng duyệt",icon: "kanban-square",  hook: "Hàng đợi việc, công tắc AI tự vận hành, cột Chờ duyệt và Policy Gate." },
    { slug: "30-workflow-loop",           title: "Workflow, Loop & Nhắc hẹn",icon: "git-branch",     hook: "9 workflow chuỗi doanh thu gọi chéo phòng, 3 loop chạy nền, nhắc hẹn." },
    { slug: "40-mo-hinh-4-lop-tri-thuc",  title: "4 lớp tri thức",           icon: "layers",         hook: "Sources/Wiki/Memory/MCP là góc nhìn lên hệ thống có sẵn - quy tắc không dựng kho thứ hai." },
    { slug: "50-ky-nang-va-bai-hoc",      title: "Kỹ năng & bài học tự học", icon: "graduation-cap", hook: "Skill chuyên môn từng phòng và luồng bài học chờ duyệt JOYCE_LESSON." },
    { slug: "60-kenh-mcp-du-lieu-song",   title: "Kênh & MCP dữ liệu sống",  icon: "plug",           hook: "Chat/Telegram/Zalo/Fanpage và dữ liệu sống qua MCP các webapp H2O." },
    { slug: "70-tai-khoan-nhan-vien",     title: "Tài khoản & phân quyền",   icon: "key-round",      hook: "Đăng nhập SĐT + PIN, workspace riêng, phân quyền staff/admin." },
    { slug: "80-kien-truc-bo-nao-cong-ty",title: "Kiến trúc bộ não công ty", icon: "share-2",        hook: "Sơ đồ Joyce/Second Brain/MCP Hub, bảng định tuyến ngữ cảnh, quy trình 6 bước." },
    { slug: "90-van-hanh-hang-ngay-ceo",  title: "Vận hành hàng ngày (CEO)",  icon: "clipboard-check", hook: "Nhịp ngày cần nhìn gì, công tắc bật/tắt agent và loop, kiểm soát chi phí model, việc chờ duyệt." },
  ];
  const css = `
    .hd-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
    .hd-card{border:1px solid var(--line,rgba(128,128,128,.25));border-radius:12px;padding:14px;cursor:pointer;background:var(--card,rgba(128,128,128,.06));transition:.15s}
    .hd-card:hover{border-color:var(--accent,#11c7d8);transform:translateY(-1px)}
    .hd-card h3{margin:8px 0 6px;font-size:15px}
    .hd-card p{margin:0;font-size:12.5px;opacity:.75;line-height:1.5}
    .hd-ic{opacity:.8}
    .hd-reader{max-width:860px}
    .hd-back{margin-bottom:12px}
    .hd-md h1{font-size:22px}.hd-md h2{font-size:17px;margin-top:22px}.hd-md table{border-collapse:collapse}.hd-md td,.hd-md th{border:1px solid var(--line,rgba(128,128,128,.3));padding:6px 10px;font-size:13px}.hd-md code{background:rgba(128,128,128,.15);padding:1px 5px;border-radius:4px}.hd-md pre{background:rgba(128,128,128,.1);padding:12px;border-radius:8px;overflow:auto}
  `;
  function esc(s){ const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }
  async function renderHuongDan(el) {
    if (!document.getElementById("hdvh-css")) {
      const st=document.createElement("style"); st.id="hdvh-css"; st.textContent=css; document.head.appendChild(st);
    }
    el.innerHTML = `<div class="hd-grid">${DOCS.map(d=>`
      <button type="button" class="hd-card" data-slug="${d.slug}">
        <span class="hd-ic">${window.ic ? ic(d.icon,{cls:"ic-lg"}) : ""}</span>
        <h3>${esc(d.title)}</h3>
        <p>${esc(d.hook)}</p>
      </button>`).join("")}</div>`;
    // Tiêu đề thẻ lấy từ H1 của file md thật (nạp lười, không bắt buộc).
    el.querySelectorAll(".hd-card").forEach(c => c.onclick = () => openDoc(el, c.dataset.slug, c));
  }
  async function openDoc(el, slug, card) {
    el.innerHTML = `<div class="hd-reader"><button class="hd-back">← Quay lại thư viện</button><div class="hd-md">Đang nạp…</div></div>`;
    el.querySelector(".hd-back").onclick = () => renderHuongDan(el);
    try {
      const r = await fetch(`/files/raw?brain=${encodeURIComponent(BRAIN)}&path=${encodeURIComponent(DIR + "/" + slug + ".md")}`);
      if (!r.ok) throw new Error("HTTP " + r.status);
      const t = await r.text();
      const md = t.replace(/^---[\s\S]*?---\r?\n/, "");   // bóc frontmatter
      el.querySelector(".hd-md").innerHTML = (window.markdownToHtml || ((x)=>`<pre>${esc(x)}</pre>`))(md);
    } catch (e) {
      el.querySelector(".hd-md").innerHTML = `<p>Không đọc được tài liệu: ${esc(String(e))}</p>`;
    }
  }
  window.renderHuongDan = renderHuongDan;
})();
