// ============================================================
// brains-ui.js - Nhiều second brain trong 1 thư mục (BRAINS_DIR), nạp TỪ SERVER.
// Bổ sung cho app.js, KHÔNG sửa app.js (file UTF-16 dễ hỏng). Chỉ thao tác DOM:
//   - Đổ dropdown #graphSource từ GET /brains (thay vì localStorage).
//   - Nút #newBrainBtn → POST /brains/new tạo brain mới.
//   - Nút #delBrainBtn → POST /brains/delete xoá brain ĐANG CHỌN (xác nhận gõ đúng tên).
// Vẫn giữ "chọn folder ngoài bất kỳ" (option data-custom do app.js thêm).
// ============================================================
(function () {
  const sel = document.getElementById("graphSource");
  if (!sel) return;

  function label(b) {
    // notes_capped = server dừng đếm ở trần, con số là SÀN chứ không phải tổng thật.
    // Thêm dấu + để không nói dối; brain thường không bao giờ chạm trần này.
    const n = b.notes ? " · " + b.notes + (b.notes_capped ? "+" : "") : "";
    // Không gắn icon: <option> chỉ nhận chữ. Thư mục ngoài được app.js xếp vào
    // <optgroup> riêng nên vẫn phân biệt được mà không cần ký hiệu nào.
    return b.name + n;
  }

  // Chuẩn hoá path để so trùng: bỏ dấu phân cách cuối, \ -> /, thường hoá (Windows không phân biệt hoa/thường).
  function normPath(p) {
    return (p || "").replace(/[\\/]+$/, "").replace(/\\/g, "/").toLowerCase();
  }

  // Hỏi server 1 path còn là thư mục không. FAIL-SAFE: mọi trường hợp không CHẮC CHẮN (lỗi
  // mạng, endpoint thiếu/404 vì server chưa restart, JSON méo) → {is_dir:null} = CHƯA xác định
  // → GIỮ entry. Chỉ dọn khi server trả rõ is_dir=false. Tránh xoá nhầm folder ngoài hợp lệ.
  async function pathExists(p) {
    try {
      const resp = await fetch("/path/exists?path=" + encodeURIComponent(p));
      if (!resp.ok) return { exists: null, is_dir: null };
      const j = await resp.json();
      if (!j || typeof j.is_dir === "undefined") return { exists: null, is_dir: null };
      return j;
    } catch (e) {
      return { exists: null, is_dir: null };
    }
  }

  // Dọn danh sách thư mục ngoài (localStorage) đã hỏng: bỏ entry TRÙNG path với 1 não thật,
  // và entry mà path KHÔNG còn là thư mục (đã xoá khỏi ổ đĩa). Giữ folder ngoài hợp lệ + entry
  // chưa xác định được (tránh xoá nhầm khi server chớp lỗi). Nguồn sự thật là localStorage nên
  // dọn cả nó → lần app.js render sau vẫn đúng, không "sống lại" qua update.
  async function pruneCustomBrains(realBrains) {
    let list;
    try { list = JSON.parse(localStorage.getItem("joyce.brains") || "[]"); }
    catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    const realPaths = new Set((realBrains || []).map((b) => normPath(b.path)));
    const kept = [];
    for (const b of list) {
      if (!b || !b.path) continue;
      if (realPaths.has(normPath(b.path))) continue;   // đã là não thật -> bỏ thư mục ngoài trùng
      const chk = await pathExists(b.path);
      if (chk && chk.is_dir === true) { kept.push(b); continue; }   // còn thư mục → giữ
      if (chk && chk.exists === null) { kept.push(b); continue; }   // chưa xác định → giữ
      // còn lại: đã bị xoá / không phải thư mục → loại
    }
    if (kept.length !== list.length) {
      localStorage.setItem("joyce.brains", JSON.stringify(kept));
    }
    // Gỡ các option thư mục ngoài (do app.js đã render) không còn trong danh sách giữ lại.
    const keepVals = new Set(kept.map((b) => "path:" + b.path));
    [...sel.querySelectorAll("option[data-custom]")].forEach((o) => {
      if (keepVals.has(o.value)) return;
      if (sel.value === o.value) {           // đang chọn đúng cái bị gỡ → về brain mặc định
        sel.value = "brain";
        localStorage.setItem("joyce.graphSource", "brain");
        sel.dispatchEvent(new Event("change"));
      }
      o.remove();
    });
    // Gỡ hết option trong nhóm thì gỡ luôn nhóm, kẻo menu còn trơ lại cái nhãn
    // "Thư mục ngoài" không có gì bên dưới.
    [...sel.querySelectorAll("optgroup")].forEach((g) => {
      if (!g.querySelector || !g.querySelector("option")) g.remove();
    });
  }

  // ---- Lọc theo THƯƠNG HIỆU (chủ yêu cầu 06/10): mỗi brand một nút não màu đứng trước
  // dropdown - H2O Studio xanh, ThuyH2O hồng. Bấm nút nào thì dropdown chỉ còn brain của brand
  // đó (brain chung + các phòng) và tự bung ra. Brain không thuộc brand nào (Brain Default,
  // brain riêng, thư mục ngoài) luôn hiện; brain ĐANG MỞ cũng luôn giữ trong danh sách để lọc
  // không bao giờ tự đổi brain sau lưng người dùng.
  const BRAND_KEY = "joyce.brainBrand";
  let lastData = null;
  function escA(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function pickBrand(brands, brains, keepVal, forceBrand) {
    if (brands.length < 2) return null;
    const ids = brands.map((b) => b.id);
    if (forceBrand && ids.includes(forceBrand)) return forceBrand;
    const cur = brains.find((b) => "path:" + b.path === keepVal);
    if (cur && cur.brand_id && ids.includes(cur.brand_id)) return cur.brand_id;
    let saved = null;
    try { saved = localStorage.getItem(BRAND_KEY); } catch (e) {}
    return saved && ids.includes(saved) ? saved : ids[0];
  }
  function renderBrandSwitch(brands, active) {
    const box = document.getElementById("brandSwitch");
    const ico = document.querySelector ? document.querySelector(".navbar-brain .brain-select-ico") : null;
    if (!box) return;
    if (!active) {          // một thương hiệu (hoặc không có): giữ biểu tượng não cũ
      box.hidden = true;
      if (ico && ico.style) ico.style.display = "";
      return;
    }
    if (ico && ico.style) ico.style.display = "none";
    const svg = window.ic ? window.ic("brain") : "";
    box.innerHTML = brands.map((b) =>
      '<button type="button" class="brand-sw' + (b.id === active ? " on" : "") + '" data-brand="' + escA(b.id) +
      '" title="' + escA(b.ten) + '" aria-label="' + escA(b.ten) + '" aria-pressed="' + (b.id === active) +
      '" style="--bc:' + escA(b.mau || "#22d3ee") + '">' + svg + "</button>").join("");
    box.hidden = false;
    box.querySelectorAll("[data-brand]").forEach((btn) => {
      btn.onclick = () => {
        if (!lastData) return;
        renderOptions(lastData, sel.value, btn.dataset.brand);
        // Bung danh sách NGAY trong cùng cú bấm (showPicker cần thao tác người dùng còn hiệu lực).
        try { sel.focus(); if (sel.showPicker) sel.showPicker(); } catch (e) {}
      };
    });
  }

  async function loadBrains(selectPath, restoreSaved) {
    let data;
    try {
      data = await (await fetch("/brains")).json();
    } catch (e) {
      return; // server chưa sẵn sàng → giữ nguyên dropdown, thử lại lần sau
    }
    lastData = data;
    const brains = (data && data.brains) || [];
    const before = sel.value;   // lựa chọn TRƯỚC khi vẽ lại - để biết có cần báo "change" không
    let keepVal = sel.value;
    if (selectPath) keepVal = "path:" + selectPath;
    else if (restoreSaved) { try { keepVal = localStorage.getItem("joyce.graphSource") || keepVal; } catch (e) {} }
    renderOptions(data, keepVal, null);
    const scoped = !!(data && data.scoped);

    // Dọn folder ngoài hỏng/trùng TRƯỚC khi khôi phục lựa chọn (đừng khôi phục về path đã chết).
    await pruneCustomBrains(brains);

    if (selectPath) {
      const want = "path:" + selectPath;
      if ([...sel.options].some((o) => o.value === want)) {
        sel.value = want;
        localStorage.setItem("joyce.graphSource", want);
        sel.dispatchEvent(new Event("change"));
      }
    } else if (restoreSaved) {
      const saved = localStorage.getItem("joyce.graphSource");
      if (saved && saved !== before && [...sel.options].some((o) => o.value === saved)) {
        sel.value = saved;
        sel.dispatchEvent(new Event("change"));
      }
    }
    if (scoped) {
      // Nhân viên: lựa chọn hiện tại không phải brain phòng của họ (vd "brain" mặc định hay
      // brain đã bị gỡ quyền) -> chuyển sang phòng đầu tiên admin gán.
      const cur = sel.options[sel.selectedIndex];
      if (!cur || !cur.dataset.brain) {
        const first = sel.querySelector("option[data-brain]");
        if (first) {
          sel.value = first.value;
          localStorage.setItem("joyce.graphSource", first.value);
          sel.dispatchEvent(new Event("change"));
        }
      }
    }
  }

  // Vẽ lại các option brain từ dữ liệu /brains, lọc theo thương hiệu. ĐỒNG BỘ (không fetch) để
  // nút não bấm là danh sách đổi và bung ra ngay. keepVal: brain đang mở - luôn giữ lại.
  function renderOptions(data, keepVal, forceBrand) {
    const brains = (data && data.brains) || [];
    const brands = (data && Array.isArray(data.brands)) ? data.brands : [];
    const active = pickBrand(brands, brains, keepVal, forceBrand);
    if (active) { try { localStorage.setItem(BRAND_KEY, active); } catch (e) {} }
    renderBrandSwitch(brands, active);
    // scoped = tài khoản nhân viên H2O: server chỉ trả brain phòng ban của họ. Brain mặc định
    // của chủ và nút tạo/xoá brain không dành cho họ (server cũng chặn), nên giấu khỏi menu.
    const scoped = !!(data && data.scoped);
    [...sel.querySelectorAll("optgroup[data-brain-group]")].forEach((g) => g.remove());
    [...sel.querySelectorAll("option[data-brain]")].forEach((o) => o.remove());

    const defOpt = sel.querySelector('option[value="brain"]');
    if (defOpt) { defOpt.hidden = scoped; defOpt.disabled = scoped; }
    ["newBrainBtn", "delBrainBtn"].forEach((id) => {
      const b = document.getElementById(id);
      if (b && b.style) b.style.display = scoped ? "none" : "";
    });
    const frag = document.createDocumentFragment();
    // Brain phòng ban (b.group = tên khối) xếp vào <optgroup> theo khối, để 38 phòng không
    // trôi thành một danh sách phẳng. Brain thường vẫn đứng phẳng ngay sau brain mặc định.
    // Nhãn <optgroup> KHÔNG bấm chọn được, nên khối còn có một option "Toàn khối ..."
    // (b.khoi_brain) ghim ĐẦU nhóm - đó mới là chỗ chọn được để hỏi con số tổng cả khối.
    const groups = new Map();
    const nhom = (ten) => {
      if (!groups.has(ten)) {
        const g = document.createElement("optgroup");
        g.label = ten;
        g.dataset.brainGroup = "1";
        groups.set(ten, g);
      }
      return groups.get(ten);
    };
    brains.forEach((b) => {
      if (b.is_default) {
        if (defOpt) defOpt.textContent = label(b);
        return; // default đã có sẵn option value="brain"
      }
      // Lọc thương hiệu: brain của brand khác ẩn đi, trừ brain đang mở.
      if (active && b.brand_id && b.brand_id !== active && "path:" + b.path !== keepVal) return;
      const opt = document.createElement("option");
      opt.value = "path:" + b.path;
      const ten = b.khoi_brain
        ? window.t("brains.whole_block", { ten: b.label || b.name })
        : (b.label || b.name);
      opt.textContent = label(Object.assign({}, b, { name: ten }));
      opt.dataset.brain = "1";
      opt.dataset.brainName = b.name; // tên folder để xoá chính xác
      if (b.khoi_brain) opt.dataset.khoiBrain = "1";
      if (!b.group) { frag.appendChild(opt); return; }
      const g = nhom(b.group);
      // Ghim đầu nhóm: server trả brain khối trước brain phòng theo bảng chữ cái, nhưng đừng
      // phụ thuộc vào đó - thứ tự thư mục đổi là mục tổng trôi xuống giữa danh sách phòng.
      if (b.khoi_brain && g.firstChild) g.insertBefore(opt, g.firstChild);
      else g.appendChild(opt);
    });
    if (defOpt && defOpt.nextSibling) sel.insertBefore(frag, defOpt.nextSibling);
    else sel.appendChild(frag);
    if (groups.size) {
      // Nhóm phòng ban đứng sau brain thường, trước nhóm "Thư mục ngoài" của app.js (nếu có).
      const anchor = sel.querySelector("optgroup:not([data-brain-group])");
      const gf = document.createDocumentFragment();
      groups.forEach((g) => gf.appendChild(g));
      if (anchor) sel.insertBefore(gf, anchor);
      else sel.appendChild(gf);
    }
    // Gỡ rồi dựng lại option làm trình duyệt nhảy lựa chọn về dòng đầu: đặt lại đúng brain
    // đang mở (KHÔNG bắn change - brain không đổi, chỉ danh sách đổi).
    if (keepVal && sel.value !== keepVal && [...sel.options].some((o) => o.value === keepVal)) sel.value = keepVal;
  }

  async function newBrain() {
    const name = (await JoyceDialog.prompt(window.t("brains.new_prompt")) || "").trim();
    if (!name) return;
    const fd = new FormData();
    fd.append("name", name);
    let r;
    try { r = await (await fetch("/brains/new", { method: "POST", body: fd })).json(); }
    catch (e) { alert(window.t("brains.create_net_err")); return; }
    if (!r || !r.ok) { alert((r && r.error) || window.t("brains.create_failed")); return; }
    await loadBrains(r.path, false);
  }

  // Gỡ 1 thư mục ngoài khỏi danh sách - CHỈ khỏi menu + localStorage, KHÔNG đụng ổ đĩa.
  async function removeCustomFromList(opt) {
    const name = opt.textContent.trim();
    if (!await JoyceDialog.confirm(window.t("brains.confirm_remove_custom", { ten: name }))) return;
    let list;
    try { list = JSON.parse(localStorage.getItem("joyce.brains") || "[]"); } catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    list = list.filter((b) => b && ("path:" + b.path) !== opt.value);
    localStorage.setItem("joyce.brains", JSON.stringify(list));
    if (sel.value === opt.value) {
      sel.value = "brain";
      localStorage.setItem("joyce.graphSource", "brain");
    }
    opt.remove();
    sel.dispatchEvent(new Event("change"));
    alert(window.t("brains.removed_custom", { ten: name }));
  }

  async function deleteBrain() {
    const opt = sel.options[sel.selectedIndex];
    if (sel.value === "brain") { alert(window.t("brains.cannot_delete_default")); return; }
    if (!opt || !opt.dataset.brain) {
      // Thư mục ngoài: cho GỠ khỏi danh sách (không xoá ổ đĩa). Trước đây chỉ báo lỗi mà
      // không có cách gỡ nào → entry kẹt vĩnh viễn kể cả sau khi folder đã bị xoá.
      if (opt && opt.dataset.custom) { removeCustomFromList(opt); return; }
      alert(window.t("brains.only_listed"));
      return;
    }
    const name = opt.dataset.brainName;
    // Xác nhận KỸ: gõ đúng tên - vì đây là TOÀN BỘ tri thức trong não này, mất là không lấy lại được.
    const typed = await JoyceDialog.prompt(window.t("brains.delete_prompt", { ten: name }));
    if (typed === null) return;
    if (typed.trim() !== name) { alert(window.t("brains.name_mismatch")); return; }
    const fd = new FormData();
    fd.append("name", name);
    fd.append("confirm", typed.trim());
    let r;
    try { r = await (await fetch("/brains/delete", { method: "POST", body: fd })).json(); }
    catch (e) { alert(window.t("brains.delete_net_err")); return; }
    if (!r || !r.ok) { alert((r && r.error) || window.t("brains.delete_failed")); return; }
    // Về brain mặc định rồi nạp lại danh sách
    sel.value = "brain";
    localStorage.setItem("joyce.graphSource", "brain");
    await loadBrains(null, false);
    sel.dispatchEvent(new Event("change"));
    alert(window.t("brains.deleted", { ten: name }));
  }

  const nb = document.getElementById("newBrainBtn");
  if (nb) nb.addEventListener("click", newBrain);
  const db = document.getElementById("delBrainBtn");
  if (db) db.addEventListener("click", deleteBrain);

  loadBrains(null, true);

  window.JoyceBrains = {
    reload: () => loadBrains(null, false),
    // Lọc dropdown theo thương hiệu bằng code (giống bấm nút não màu, trừ việc bung danh sách).
    brand: (id) => { if (lastData) renderOptions(lastData, sel.value, id); },
  };
})();
