/* ============================================================================
 * JOYCE OS - Tinh vân kiểu CHÒM SAO (docs/dev/2026-10-tinh-van-apex-design.md, chủ duyệt 20/10/2026)
 *
 * Lớp nhìn "Tinh vân" mặc định: ở giữa là QUẢ CẦU của brain đang mở (Trái Đất cho Brain Default,
 * tinh cầu đúng phòng ban cho brain phòng, ngôi sao cho brain chung thương hiệu - cùng bảng màu và
 * đặc trưng với thiên hà ở tab Lõi nước), bao bởi vòng vàng. Quanh đó là các nhánh của bộ não:
 *   - xanh   = thư mục tri thức (wiki, sources, facts...)
 *   - cam    = vận hành (agents, skills, workflows, loops, van-hanh)
 *   - xám    = kết nối MCP (nét đứt khi chưa bật)
 * Joyce đọc / ghi file hay gọi công cụ thì đúng nhánh đó sáng, hạt chạy từ lõi ra nút.
 * Đồ thị note cũ (graph.js) vẫn còn nguyên, chuyển qua bằng nút "Mạng note".
 *
 * Cảm hứng và một phần cách dựng (dây cong, vòng quỹ đạo chấm, mạch PCB, hạt chạy dọc dây, nút thở
 * lệch pha, vòng vàng nhiều lớp) lấy từ APEX-UI của Ruben Mouradian, giấy phép MIT
 * (https://github.com/RubenM1990/APEX-UI). Không dùng tên hay thương hiệu "Apex".
 *
 * JS thuần, không thư viện: SVG cho mạng + một canvas cho quả cầu xoay. Chỉ chạy vòng vẽ khi lớp
 * nhìn này đang hiện; tôn trọng "giảm chuyển động" của hệ điều hành.
 * Mọi chữ hiện ra đi qua window.t (từ điển i18n, khoá "tv.*").
 * ========================================================================== */
(function (global) {
  'use strict';

  var NS = 'http://www.w3.org/2000/svg';
  var VW = 680, VH = 480, AX = 340, AY = 226;
  var RING = 72, PR = 52, MINR = 122;
  var LEVEL = { idle: 0.32, listening: 0.6, thinking: 0.9, speaking: 0.78 };
  var OPS = { agents: 1, skills: 1, workflows: 1, loops: 1, plugins: 1, 'van-hanh': 1, joyce: 1 };
  var SKIP = { attachments: 1, assets: 1, images: 1, _archive: 1 };
  var MAX_FOLDERS = 12, MAX_MCP = 10;

  var tt = function (k, v) {
    if (global.t) return global.t(k, v);
    return k;
  };
  var clamp = function (v, a, b) { return v < a ? a : v > b ? b : v; };
  function strHash(s) {
    var h = 2166136261; s = String(s || '');
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function gapKhoa(s) {
    // Dải dấu kết hợp + chữ "đ" viết bằng mã \\u để mã chạy chỉ toàn ASCII (test i18n soi chữ Việt).
    return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\u0111/gi, 'd').toLowerCase().replace(/[^a-z0-9]+/g, '');
  }

  // ---------------------------------------------------------------- hàm thuần (có test)
  /** Tên thư mục -> {key, name}: bỏ tiền tố "07 - ", bỏ thư mục ẩn (.claude...). */
  function folderOf(name) {
    var raw = String(name || '').trim();
    if (!raw || raw.charAt(0) === '.') return null;
    var name2 = raw.replace(/^\d+\s*[-_.]\s*/, '').trim();
    var key = name2.toLowerCase();
    if (!key || SKIP[key]) return null;
    return { key: key, name: name2 };
  }
  function layerOf(key) { return OPS[key] ? 'ops' : 'know'; }
  /** Gom note theo THƯ MỤC GỐC trong brain (wiki/y-tuong/x.md -> wiki). Note nằm thẳng ở gốc bỏ qua. */
  function groupFolders(nodes) {
    var by = {}, total = 0;
    (nodes || []).forEach(function (n) {
      var segs = String(n.path || '').split('/');
      if (segs.length < 3) return;                 // <gốc>/<note> : không thuộc nhánh nào
      var f = folderOf(segs[1]);
      if (!f) return;
      total++;
      var g = by[f.key] || (by[f.key] = { key: f.key, name: f.name, count: 0, layer: layerOf(f.key) });
      g.count++;
    });
    var all = Object.keys(by).map(function (k) { return by[k]; });
    all.sort(function (a, b) { return b.count - a.count || (a.key < b.key ? -1 : 1); });
    // Nhánh vận hành có mặt là luôn giữ (ít note vẫn là bộ phận quan trọng), còn lại lấy theo số note.
    var ops = all.filter(function (g) { return g.layer === 'ops'; }).slice(0, 5);
    var know = all.filter(function (g) { return g.layer === 'know'; }).slice(0, MAX_FOLDERS - ops.length);
    return { folders: know.concat(ops), total: total };
  }
  /** Đặt nút: thư mục trên vòng elip trong (chừa khe đáy cho chữ trạng thái), MCP trên vòng ngoài. */
  function layout(folders, mcps) {
    var out = [], n = folders.length, maxC = 1;
    folders.forEach(function (f) { if (f.count > maxC) maxC = f.count; });
    var gap = 64, a0 = 90 + gap / 2, sweep = 360 - gap;
    folders.forEach(function (f, i) {
      var ang = (a0 + (n === 1 ? sweep / 2 : (i + 0.5) * sweep / n)) * Math.PI / 180;
      var k = Math.sqrt(f.count / maxC);
      var sc = 1.07 - 0.15 * k;                       // nhánh lớn nằm gần lõi hơn
      var x = AX + Math.cos(ang) * 200 * sc, y = AY + Math.sin(ang) * 152 * sc;
      var dx = x - AX, dy = y - AY, d = Math.hypot(dx, dy) || 1;
      if (d < MINR) { x = AX + dx / d * MINR; y = AY + dy / d * MINR; }
      out.push({ id: 'f:' + f.key, key: f.key, label: f.name, layer: f.layer, count: f.count,
                 x: x, y: y, r: 5.5 + 4 * k, live: f.count > 0, bend: ((strHash(f.key) % 21) - 10) * 2.4 });
    });
    var SLOTS = [160, 20, 200, 340, 142, 38, 222, 318, 248, 292];
    (mcps || []).slice(0, MAX_MCP).forEach(function (m, i) {
      var ang = SLOTS[i] * Math.PI / 180;
      out.push({ id: 'm:' + m.id, key: m.id, label: m.label, layer: 'mcp', mcp: m,
                 x: AX + Math.cos(ang) * 284, y: AY + Math.sin(ang) * 200, r: 5, live: !!m.enabled,
                 bend: ((strHash(m.id) % 21) - 10) * 2 });
    });
    return out;
  }
  /** Nhánh nào đang được dùng: file -> thư mục, tên công cụ -> nhánh vận hành / MCP. */
  function targetsFor(detail, nodes, nguon) {
    var d = detail || {}, hit = {}, out = [];
    var add = function (n) { if (n && !hit[n.id]) { hit[n.id] = 1; out.push(n.id); } };
    var byKey = {};
    nodes.forEach(function (n) { if (n.layer !== 'mcp') byKey[n.key] = n; });
    (d.files || []).forEach(function (f) {
      var segs = String(f || '').replace(/\\/g, '/').toLowerCase().split('/');
      for (var i = 0; i < segs.length - 1; i++) {
        var fo = folderOf(segs[i]);
        if (fo && byKey[fo.key]) { add(byKey[fo.key]); break; }
      }
    });
    var tool = String(d.tool || '');
    if (tool) {
      if (/skill/i.test(tool)) add(byKey.skills);
      if (/^(task|agent)$|delegate|joyce_agent/i.test(tool)) add(byKey.agents);
      if (/workflow/i.test(tool)) add(byKey.workflows);
      if (/joyce_schedule|loop/i.test(tool)) add(byKey.loops);
      var g = nguon ? nguon(tool) : null;
      if (g && g.key) {
        nodes.forEach(function (n) {
          if (n.layer !== 'mcp') return;
          var a = gapKhoa(n.label) || '', b = gapKhoa(n.mcp && n.mcp.slug) || '', k = g.key;
          if ((a && (a === k || (a.length >= 4 && k.indexOf(a) >= 0) || (k.length >= 4 && a.indexOf(k) >= 0))) ||
              (b && (b === k || (b.length >= 4 && k.indexOf(b) >= 0)))) add(n);
        });
      }
    }
    return out;
  }
  /** Kiểu quả cầu theo brain đang mở, tra trong dữ liệu thiên hà phòng ban (/knowledge/galaxy). */
  function sphereFor(gal, key) {
    if (gal) {
      if (gal.earth && gal.earth.key === key) return { kind: 'earth', style: '_earth', ten: gal.earth.ten || key };
      var p = (gal.phong || []).filter(function (x) { return x.key === key; })[0];
      if (p) return { kind: 'dept', style: p.khoi, ten: p.ten || key };
      var s = (gal.stars || []).filter(function (x) { return x.key === key; })[0];
      if (s) return { kind: 'star', style: s.brand || 'h2o', ten: s.ten || key };
    }
    return { kind: key === 'Brain Default' ? 'earth' : 'dept', style: key === 'Brain Default' ? '_earth' : '', ten: key };
  }

  // ---------------------------------------------------------------- bề mặt quả cầu
  // Bảng màu + đặc trưng phòng ban: CHÉP từ brain-planet.js (thiên hà Lõi nước) để hai lớp nhìn
  // cùng một "gương mặt", mà không phải đụng vào brain-planet.js.
  var PALETTES = {
    ocean: { deep: [0.01, 0.06, 0.2], sea: [0.024, 0.298, 1], rim: [0, 0.906, 1] },
    emerald: { deep: [0.004, 0.07, 0.045], sea: [0.02, 0.6, 0.36], rim: [0.3, 1, 0.62] },
    amethyst: { deep: [0.05, 0.015, 0.14], sea: [0.42, 0.18, 0.95], rim: [0.86, 0.48, 1] },
    sunset: { deep: [0.12, 0.02, 0.06], sea: [0.92, 0.3, 0.22], rim: [1, 0.68, 0.3] },
    ice: { deep: [0.05, 0.1, 0.18], sea: [0.5, 0.74, 0.95], rim: [0.85, 0.97, 1] },
    lava: { deep: [0.09, 0.01, 0], sea: [0.72, 0.15, 0.03], rim: [1, 0.45, 0.1] },
    gold: { deep: [0.09, 0.055, 0], sea: [0.82, 0.58, 0.12], rim: [1, 0.86, 0.42] },
    abyss: { deep: [0, 0.004, 0.02], sea: [0.06, 0.09, 0.24], rim: [0.3, 0.4, 0.85] },
    pink: { deep: [0.14, 0.03, 0.1], sea: [0.86, 0.36, 0.7], rim: [1, 0.72, 0.9] },
    paper: { deep: [0.08, 0.08, 0.1], sea: [0.55, 0.57, 0.62], rim: [0.9, 0.92, 0.95] },
  };
  var GX_STYLE = {
    'ke-toan': { pal: 'gold', feat: 'ring' }, 'nhan-su': { pal: 'emerald', feat: 'clouds' },
    'marketing': { pal: 'sunset', feat: 'storm' }, 'ban-hang': { pal: 'lava', feat: 'cracks' },
    'san-xuat': { pal: 'lava', feat: 'volcano' }, 'nghien-cuu': { pal: 'amethyst', feat: 'crystal' },
    'cskh': { pal: 'ocean', feat: 'waves' }, 've-sinh': { pal: 'ice', feat: 'ice' },
    'xu-ly-truyen-thong': { pal: 'abyss', feat: 'antenna' }, 'van-thu-va-quy-trinh': { pal: 'paper', feat: 'paper' },
    'thuyh2o': { pal: 'pink', feat: 'glitter' }, '_earth': { pal: 'ocean', feat: 'earth' },
  };
  var NP = null, NV = null;
  function h3(i, j, k) {
    if (!NP) {
      var s = 1337, rnd = function () { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }, pm = [], q;
      NP = new Uint8Array(512); NV = new Float32Array(256);
      for (q = 0; q < 256; q++) { pm.push(q); NV[q] = rnd(); }
      for (q = 255; q > 0; q--) { var w = (rnd() * (q + 1)) | 0, tmp = pm[q]; pm[q] = pm[w]; pm[w] = tmp; }
      for (q = 0; q < 512; q++) NP[q] = pm[q & 255];
    }
    return NV[NP[NP[NP[i & 255] + (j & 255)] + (k & 255)]];
  }
  function vnoise(x, y, z) {
    var xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), xf = x - xi, yf = y - yi, zf = z - zi;
    var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
    var L = function (a, b, t) { return a + (b - a) * t; };
    return L(L(L(h3(xi, yi, zi), h3(xi + 1, yi, zi), u), L(h3(xi, yi + 1, zi), h3(xi + 1, yi + 1, zi), u), v),
             L(L(h3(xi, yi, zi + 1), h3(xi + 1, yi, zi + 1), u), L(h3(xi, yi + 1, zi + 1), h3(xi + 1, yi + 1, zi + 1), u), v), w);
  }
  function fbm(x, y, z, o) {
    var s = 0, a = 0.5, f = 1;
    for (var i = 0; i < o; i++) { s += a * vnoise(x * f, y * f, z * f); f *= 2.03; a *= 0.5; }
    return s / (1 - Math.pow(0.5, o));
  }
  function smooth(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  /** Bản đồ bề mặt dạng kinh-vĩ độ: màu nền (chịu ánh sáng) + màu tự phát sáng (dung nham, kim tuyến). */
  function buildSurface(styleKey, seed) {
    var TW = 256, TH = 128, base = new Float32Array(TW * TH * 3), em = new Float32Array(TW * TH * 3);
    var st = GX_STYLE[styleKey] || { pal: 'ocean', feat: 'clouds' }, P = PALETTES[st.pal] || PALETTES.ocean;
    var off = (seed % 97) / 3;
    for (var j = 0; j < TH; j++) {
      var lat = (0.5 - (j + 0.5) / TH) * Math.PI, cl = Math.cos(lat), sy = Math.sin(lat);
      for (var i = 0; i < TW; i++) {
        var lon = (i + 0.5) / TW * Math.PI * 2, x = cl * Math.cos(lon), z = cl * Math.sin(lon), y = sy;
        var o = (j * TW + i) * 3, h = fbm(x * 2.4 + off, y * 2.4, z * 2.4, 4), k = smooth(0.35, 0.7, h);
        var c = [P.deep[0] + (P.sea[0] - P.deep[0]) * k, P.deep[1] + (P.sea[1] - P.deep[1]) * k, P.deep[2] + (P.sea[2] - P.deep[2]) * k];
        var them = 0, tc = P.rim, glow = 0, gc = [1, 0.6, 0.2];
        if (st.feat === 'earth') {
          var land = smooth(0.5, 0.56, fbm(x * 1.8 + 3, y * 1.8, z * 1.8, 5));
          var ocean = [0.02, 0.16 + 0.12 * k, 0.45 + 0.3 * k], green = [0.12 + 0.2 * h, 0.36 + 0.12 * h, 0.12], sand = [0.55, 0.47, 0.3];
          var dry = smooth(0.55, 0.7, fbm(x * 3 + 7, y * 3, z * 3, 3));
          for (var q = 0; q < 3; q++) c[q] = ocean[q] + ((green[q] + (sand[q] - green[q]) * dry) - ocean[q]) * land;
          if (Math.abs(sy) > 0.86) { them = smooth(0.86, 0.93, Math.abs(sy)); tc = [0.95, 0.98, 1]; }
          var cloud = smooth(0.56, 0.74, fbm(x * 3.2 + 11, y * 3.2, z * 3.2 + off, 4));
          them = Math.max(them, cloud * 0.85); if (cloud > 0.05) tc = [1, 1, 1];
        } else if (st.feat === 'clouds') { them = smooth(0.58, 0.72, fbm(x * 3.4 + 9, y * 3.4, z * 3 + off, 3)) * 0.8; tc = [1, 1, 1]; }
        else if (st.feat === 'storm') {
          var band = 0.5 + 0.5 * Math.sin(y * 11 + fbm(x * 3, y * 3, off, 2) * 3);
          c = c.map(function (v) { return v * (0.75 + 0.45 * band); });
          var sx = lon - 1.2, sy2 = (lat - 0.25) * 1.8; them = Math.exp(-(sx * sx + sy2 * sy2) * 6) * 0.85; tc = [1, 0.55, 0.3];
        } else if (st.feat === 'cracks' || st.feat === 'volcano') {
          c = c.map(function (v) { return v * (st.feat === 'volcano' ? 0.35 : 0.5); });
          var cr = Math.abs(fbm(x * 4 + off, y * 4, z * 4, 3) - 0.5);
          glow = (1 - smooth(0, st.feat === 'volcano' ? 0.03 : 0.05, cr)) * 1.1; gc = [1, 0.55, 0.15];
        } else if (st.feat === 'crystal') { them = smooth(0.66, 0.72, fbm(x * 7 + off, y * 7, z * 7, 2)) * 0.9; tc = [0.95, 0.85, 1]; }
        else if (st.feat === 'waves') { them = Math.pow(0.5 + 0.5 * Math.sin(y * 26 + x * 4 + h * 6), 6) * 0.35; tc = [0.75, 0.95, 1]; }
        else if (st.feat === 'ice') { them = smooth(0.55, 0.85, Math.abs(sy) + (h - 0.5) * 0.4); tc = [1, 1, 1]; }
        else if (st.feat === 'glitter') { glow = h3((i * 7) | 0, (j * 7) | 0, seed & 255) > 0.97 ? 0.9 : 0; gc = [1, 0.9, 0.97]; }
        else if (st.feat === 'antenna') { glow = Math.pow(0.5 + 0.5 * Math.sin(lon * 18), 40) * smooth(0.3, 0.0, Math.abs(sy)) * 0.8; gc = [0.5, 0.65, 1]; }
        else if (st.feat === 'paper') { them = Math.pow(0.5 + 0.5 * Math.sin(y * 60), 8) * 0.25; tc = [0.95, 0.96, 1]; }
        for (var ch = 0; ch < 3; ch++) {
          base[o + ch] = c[ch] + (tc[ch] - c[ch]) * clamp(them, 0, 1);
          em[o + ch] = gc[ch] * glow;
        }
      }
    }
    return { TW: TW, TH: TH, base: base, em: em, rim: P.rim, ring: st.feat === 'ring' };
  }

  // ---------------------------------------------------------------- lớp vẽ
  function Constellation(host, opts) {
    this.host = host; this.opts = opts || {};
    this.state = 'idle'; this.level = 0; this.awake = 0;
    this.folders = []; this.total = 0; this.links = 0; this.mcps = []; this.gal = null; this.brainKey = 'Brain Default';
    this.nodes = []; this.live = []; this.sel = null; this.hover = null; this.coRecent = [];
    this.running = false; this.visible = false; this.disposed = false;
    var mq = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : null;
    this.reduced = !!(mq && mq.matches);
    this.light = typeof document !== 'undefined' && document.documentElement && document.documentElement.getAttribute('data-theme') === 'light';
    this.build();
  }
  var C = Constellation.prototype;

  C.pal = function () {
    return this.light ? {
      ring: '#93a9bb', pcb: '#5d7f97', pcbDot: '#0e7490', fieldMesh: '#9db1c0', fieldDot: '#0e7490', mesh: '#8ba2b4',
      spoke: '#46708e', spokeHot: '#0891b2', link: '#0d9488', label: '#1f2d3a', labelMinor: '#55677a', labelDorm: '#8a99a8',
      mote: '#0aa9c8', moteHot: '#067a96', gold: '#b26d05', goldHi: '#d48a10',
      col: { know: '#067a96', ops: '#b26d05', mcp: '#64748b' },
    } : {
      ring: '#1b5f78', pcb: '#1c5f7a', pcbDot: '#37d6ef', fieldMesh: '#143f4f', fieldDot: '#2bd0e6', mesh: '#1a5468',
      spoke: '#22566b', spokeHot: '#33eaff', link: '#5eead4', label: '#dfeaf3', labelMinor: '#93a8ba', labelDorm: '#546a7d',
      mote: '#5fe0f2', moteHot: '#bff6ff', gold: '#f5a623', goldHi: '#ffd080',
      col: { know: '#00e5ff', ops: '#f5a623', mcp: '#7f9bb3' },
    };
  };

  C.build = function () {
    var root = this.root = document.createElement('div');
    root.className = 'bc-layer'; root.id = 'brainConst';
    this.cv = document.createElement('canvas'); this.cv.className = 'bc-sphere'; this.cv.setAttribute('aria-hidden', 'true');
    this.svg = document.createElementNS(NS, 'svg');
    this.svg.setAttribute('class', 'bc-web'); this.svg.setAttribute('viewBox', '0 0 ' + VW + ' ' + VH);
    this.svg.setAttribute('preserveAspectRatio', 'xMidYMid meet'); this.svg.setAttribute('aria-hidden', 'true');
    this.nav = document.createElement('nav'); this.nav.className = 'bc-sr';
    this.card = document.createElement('div'); this.card.className = 'bc-card'; this.card.hidden = true;
    this.card.setAttribute('role', 'dialog');
    root.appendChild(this.cv); root.appendChild(this.svg); root.appendChild(this.nav); root.appendChild(this.card);
    this.host.appendChild(root);
    this.off = document.createElement('canvas');
    var self = this;
    this._onKey = function (e) { if (e.key === 'Escape' && !self.card.hidden) self.closeCard(); };
    document.addEventListener('keydown', this._onKey);
  };

  C.mk = function (t, a) { var e = document.createElementNS(NS, t); for (var k in a) e.setAttribute(k, a[k]); return e; };

  // ---------------------------------------------------------------- dữ liệu vào
  C.setGraph = function (nodes, stats) {
    var g = groupFolders(nodes);
    this.folders = g.folders; this.total = (stats && stats.total_notes) || g.total; this.links = (stats && stats.total_links) || 0;
    this.render();
  };
  C.setMcp = function (list) {
    var arr = (list || []).map(function (s) { return { id: String(s.id || s.slug || s.label), label: s.label || s.name || s.slug || '?', slug: s.slug || '', enabled: !!s.enabled }; });
    arr.sort(function (a, b) { return (b.enabled - a.enabled) || (a.label < b.label ? -1 : 1); });
    this.mcps = arr; this.render();
  };
  C.setGalaxy = function (gal) { this.gal = gal; this.sphere = null; };
  C.setBrain = function (key, ten) { this.brainKey = key || 'Brain Default'; this.brainTen = ten || ''; this.sphere = null; this.render(); };
  C.setState = function (s) { this.state = LEVEL[s] != null ? s : 'idle'; this.paintState(); };
  C.setLevel = function (v) { var raw = clamp(+v || 0, 0, 1); this.level += (raw - this.level) * (raw > this.level ? 0.3 : 0.06); };
  C.setTheme = function (light) { this.light = !!light; this.render(); };

  // ---------------------------------------------------------------- dựng SVG
  C.render = function () {
    if (!this.svg) return;
    var P = this.pal(), mk = this.mk.bind(this), self = this;
    this.svg.replaceChildren(); this.live = [];
    var defs = mk('defs', {});
    defs.innerHTML = '<filter id="bc-glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
      '<filter id="bc-line" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="1.9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
      '<filter id="bc-ring" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
      '<radialGradient id="bc-amb" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="' + P.gold + '" stop-opacity="0.09"/><stop offset="100%" stop-color="' + P.gold + '" stop-opacity="0"/></radialGradient>';
    var pcbG = mk('g', {}), ringsG = mk('g', {}), fillG = mk('g', {}), meshG = mk('g', {}), spokesG = mk('g', {}),
        pulsesG = mk('g', {}), nodesG = mk('g', {}), coreG = mk('g', {});
    this.svg.append(defs, pcbG, ringsG, fillG, meshG, spokesG, pulsesG, nodesG, coreG);
    if (!this.light) [pcbG, meshG, spokesG].forEach(function (g) { g.setAttribute('filter', 'url(#bc-line)'); });
    this.pulsesG = pulsesG;
    var seed = 11, rnd = function () { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
    var narrow = (this.host.clientWidth || 900) < 620;

    [RING + 34, RING + 86, RING + 150].forEach(function (r) {
      ringsG.append(mk('circle', { cx: AX, cy: AY, r: r, fill: 'none', stroke: P.ring, opacity: 0.32, 'stroke-width': 1, 'stroke-dasharray': '1 7' }));
    });
    if (!narrow) [-1, 1].forEach(function (side) {
      for (var i = 0; i < 5; i++) {
        var y = AY + (i - 2) * 58 + (rnd() * 16 - 8), sx = AX + side * (RING + 60 + rnd() * 30);
        var mx = side < 0 ? (40 + rnd() * 56) : (584 + rnd() * 56), y2 = y + (rnd() * 30 - 15), jx = side < 0 ? (10 + rnd() * 18) : (652 + rnd() * 18);
        pcbG.append(mk('path', { d: 'M' + sx + ' ' + y + ' H' + mx + ' V' + y2 + ' H' + jx, fill: 'none', stroke: P.pcb, opacity: 0.42, 'stroke-width': 1 }));
        pcbG.append(mk('circle', { cx: jx, cy: y2, r: 2.4, fill: P.pcbDot, opacity: 0.8 }));
      }
    });
    var fill = [];
    for (var i = 0; i < 16; i++) { var fx = 36 + rnd() * 608, fy = 30 + rnd() * 400; if (Math.hypot(fx - AX, fy - AY) > 180) fill.push({ x: fx, y: fy }); }
    fill.forEach(function (f) {
      var near = null, nd = 1e9;
      fill.forEach(function (g) { if (g !== f) { var d = Math.hypot(g.x - f.x, g.y - f.y); if (d < nd) { nd = d; near = g; } } });
      if (near && nd < 110) meshG.append(mk('line', { x1: f.x, y1: f.y, x2: near.x, y2: near.y, stroke: P.fieldMesh, 'stroke-width': 1, opacity: 0.4 }));
      var c = mk('circle', { cx: f.x, cy: f.y, r: 1.1, fill: P.fieldDot, 'class': 'bc-twinkle' });
      c.style.animationDelay = (rnd() * 4).toFixed(2) + 's';
      fillG.append(c);
    });

    // ---- nút + dây
    var pts = this.nodes = layout(this.folders, this.mcps);
    var tot = this.total || 1;
    pts.forEach(function (n) {
      var o = pts.filter(function (m) { return m !== n; }).map(function (m) { return { m: m, d: Math.hypot(m.x - n.x, m.y - n.y) }; })
        .sort(function (a, b) { return a.d - b.d; })[0];
      if (o && n.id < o.m.id && o.d < 150) meshG.append(mk('line', { x1: n.x, y1: n.y, x2: o.m.x, y2: o.m.y, stroke: P.mesh, 'stroke-width': 1, opacity: 0.45 }));
    });
    var nav = this.nav; nav.replaceChildren(); nav.setAttribute('aria-label', tt('tv.nav_aria'));
    pts.forEach(function (n) {
      n.col = P.col[n.layer];
      var dx = n.x - AX, dy = n.y - AY, l = Math.hypot(dx, dy) || 1;
      // Dây mọc từ MÉP vòng vàng chứ không từ tâm: tâm là quả cầu, vẽ dây xuyên qua là bẩn hình.
      var sx0 = AX + dx / l * (RING + 5), sy0 = AY + dy / l * (RING + 5), mx = (sx0 + n.x) / 2, my = (sy0 + n.y) / 2;
      n.spoke = mk('path', { d: 'M' + sx0.toFixed(1) + ' ' + sy0.toFixed(1) + ' Q' + (mx + (-dy / l) * n.bend) + ' ' + (my + (dx / l) * n.bend) + ' ' + n.x + ' ' + n.y,
                             fill: 'none', stroke: P.spoke, 'stroke-width': 1, opacity: n.live ? 0.72 : 0.36 });
      if (n.layer === 'mcp' && !n.live) n.spoke.setAttribute('stroke-dasharray', '3 4');
      spokesG.append(n.spoke);
      n.haloR = n.r + 1.5; n.phase = (strHash(n.id) % 628) / 100;
      n.halo = mk('circle', { cx: n.x, cy: n.y, r: n.haloR, fill: n.col, filter: 'url(#bc-glow)', opacity: n.live ? 0.32 : 0.18 });
      n.circ = mk('circle', { cx: n.x, cy: n.y, r: n.r, fill: 'none', stroke: n.col, 'stroke-width': n.live ? 2 : 1.3, opacity: n.live ? 1 : 0.6 });
      if (!n.live) n.circ.setAttribute('stroke-dasharray', '2 2');
      nodesG.append(n.halo, n.circ);
      var ux = dx / l, uy = dy / l, off = n.r + 10, above = uy > 0.82, top = uy < -0.6;
      var anchor = above || top ? 'middle' : (ux > 0.3 ? 'start' : (ux < -0.3 ? 'end' : 'middle'));
      var tx = above || top ? n.x : n.x + ux * off, ty = above ? n.y - (n.r + 18) : n.y + uy * off + (Math.abs(uy) < 0.3 ? 2 : 0);
      if (top) ty = n.y - n.r - 21;                                 // nút phía trên: nhãn + số liệu đều nằm TRÊN nút
      if (n.layer === 'mcp') { anchor = 'middle'; tx = n.x; ty = n.y + n.r + 13; }   // MCP ở vòng ngoài: nhãn dưới nút, khỏi tràn mép
      var minor = n.layer === 'mcp' || !n.live;
      var t1 = mk('text', { x: tx, y: ty, 'text-anchor': anchor, 'font-size': minor ? 10 : 12, 'class': 'bc-label',
                            fill: !n.live ? P.labelDorm : (minor ? P.labelMinor : P.label), 'letter-spacing': n.layer === 'mcp' ? 0 : 1 });
      t1.textContent = n.layer === 'mcp' ? n.label : n.label.toUpperCase();
      if (!(narrow && n.layer === 'mcp')) nodesG.append(t1);
      if (n.layer !== 'mcp' && !narrow) {
        var t2 = mk('text', { x: tx, y: ty + 13, 'text-anchor': anchor, 'font-size': 9, 'class': 'bc-label bc-meta', fill: P.labelMinor });
        t2.textContent = tt('tv.meta', { n: n.count, p: Math.round(n.count / tot * 100) });
        nodesG.append(t2);
      }
      var hit = mk('circle', { cx: n.x, cy: n.y, r: Math.max(n.r + 13, 17), fill: 'transparent', 'class': 'bc-hit' });
      hit.addEventListener('click', function () { self.openCard(n); });
      hit.addEventListener('pointerenter', function () { self.setHover(n); });
      hit.addEventListener('pointerleave', function () { self.setHover(null); });
      nodesG.append(hit);
      var b = document.createElement('button'); b.type = 'button'; b.textContent = n.label;
      b.addEventListener('click', function () { self.openCard(n); }); nav.appendChild(b);
    });

    // ---- lõi: khung vòng vàng quanh quả cầu
    coreG.append(mk('ellipse', { cx: AX, cy: AY, rx: RING + 70, ry: RING + 52, fill: 'url(#bc-amb)', 'class': 'bc-amb' }));
    [RING + 14, RING + 24, RING + 36].forEach(function (r, i) {
      coreG.append(mk('circle', { cx: AX, cy: AY, r: r, stroke: P.gold, 'stroke-width': i ? 0.5 : 0.8, 'stroke-opacity': 0.16 - i * 0.03, fill: 'none', 'stroke-dasharray': i % 2 ? '3 7' : 'none' }));
    });
    this.waves = [0, 1, 2].map(function () { var w = mk('circle', { cx: AX, cy: AY, r: RING, stroke: P.gold, 'stroke-width': 1, fill: 'none', opacity: 0 }); coreG.append(w); return w; });
    coreG.append(mk('circle', { cx: AX, cy: AY, r: RING, stroke: P.gold, 'stroke-width': 14, 'stroke-opacity': 0.08, fill: 'none', filter: 'url(#bc-ring)' }));
    coreG.append(mk('circle', { cx: AX, cy: AY, r: RING, stroke: P.gold, 'stroke-width': 4, 'stroke-opacity': 0.35, fill: 'none', filter: 'url(#bc-ring)' }));
    this.bright = mk('circle', { cx: AX, cy: AY, r: RING, stroke: P.goldHi, 'stroke-width': 2.2, 'stroke-opacity': 0.95, fill: 'none', 'stroke-dasharray': '120 18 40 18' });
    this.swirl = mk('circle', { cx: AX, cy: AY, r: RING + 7, stroke: P.gold, 'stroke-width': 1, 'stroke-opacity': 0.4, fill: 'none', 'stroke-dasharray': '8 14' });
    coreG.append(this.bright, this.swirl);
    coreG.append(mk('line', { x1: AX, y1: AY - (RING + 46), x2: AX, y2: AY - (RING + 30), stroke: P.gold, 'stroke-width': 1, opacity: 0.3 }));
    var name = mk('text', { x: AX, y: AY + RING + 22, 'text-anchor': 'middle', 'font-size': 11, 'letter-spacing': 2.5, fill: P.gold, 'class': 'bc-label' });
    name.textContent = String(this.sphereInfo().ten || '').toUpperCase();
    this.stLabel = mk('text', { x: AX, y: AY + RING + 37, 'text-anchor': 'middle', 'font-size': 9, 'letter-spacing': 3, fill: P.gold, opacity: 0.6 });
    coreG.append(name, this.stLabel);
    this.bars = [];
    for (var b2 = 0; b2 < 16; b2++) {
      var bx = AX - 46 + b2 * 6, bar = mk('rect', { x: bx, y: AY + RING + 44, width: 2.6, height: 2, rx: 1.2, fill: P.gold, opacity: 0.4 });
      coreG.append(bar); this.bars.push(bar);
    }
    var coreHit = mk('circle', { cx: AX, cy: AY, r: RING, fill: 'transparent', 'class': 'bc-hit' });
    coreHit.addEventListener('click', function () { self.openCard({ id: 'core', layer: 'core' }); });
    coreG.append(coreHit);
    this.paintState();
    this.setHover(this.hover);
    this.place();
  };

  C.sphereInfo = function () {
    var s = sphereFor(this.gal, this.brainKey);
    if (this.brainTen && s.ten === this.brainKey) s.ten = this.brainTen;   // thiên hà không biết tên đẹp hơn
    return s;
  };
  C.paintState = function () {
    if (!this.stLabel) return;
    var k = { idle: 'tv.st_idle', listening: 'tv.st_listen', thinking: 'tv.st_think', speaking: 'tv.st_speak' }[this.state] || 'tv.st_idle';
    this.stLabel.textContent = tt(k);
  };
  C.setHover = function (n) {
    this.hover = n;
    var on = !!n;
    this.nodes.forEach(function (m) {
      var dim = on && m !== n;
      [m.circ, m.halo, m.spoke].forEach(function (e) { if (e) e.style.opacity = dim ? '0.25' : ''; });
    });
  };

  // ---------------------------------------------------------------- quả cầu (canvas)
  /** Canh canvas quả cầu trùng tâm SVG (viewBox "meet" nên phải tự tính tỉ lệ). */
  C.place = function () {
    var w = this.root.clientWidth || this.host.clientWidth, h = this.root.clientHeight || this.host.clientHeight;
    if (!w || !h) return;
    var s = Math.min(w / VW, h / VH), ox = (w - VW * s) / 2, oy = (h - VH * s) / 2;
    var R = PR * s, pad = R * 0.55, size = Math.round((R + pad) * 2);
    var dpr = Math.min(global.devicePixelRatio || 1, 1.5);
    this.cv.style.width = this.cv.style.height = size + 'px';
    this.cv.style.left = Math.round(ox + AX * s - size / 2) + 'px';
    this.cv.style.top = Math.round(oy + AY * s - size / 2) + 'px';
    var px = Math.round(size * dpr);
    if (this.cv.width !== px) { this.cv.width = this.cv.height = px; this.lut = null; }
    this.rpx = Math.min(150, Math.round(R * dpr));     // bán kính dựng (tối đa 300px để giữ nhẹ)
    this.scaleUp = (R * dpr) / this.rpx;
  };
  C.buildLut = function () {
    var r = this.rpx, D = r * 2, n = D * D, tilt = 0.38, ct = Math.cos(tilt), stl = Math.sin(tilt);
    var u = new Float32Array(n), v = new Int16Array(n), lit = new Float32Array(n), a = new Float32Array(n), rim = new Float32Array(n);
    for (var y = 0; y < D; y++) for (var x = 0; x < D; x++) {
      var i = y * D + x, nx = (x + 0.5) / r - 1, ny = (y + 0.5) / r - 1, r2 = nx * nx + ny * ny;
      if (r2 > 1) { a[i] = 0; continue; }
      var nz = Math.sqrt(1 - r2);
      var X = nx * ct + ny * stl, Y = -nx * stl + ny * ct;          // nghiêng trục quay
      var lat = Math.asin(clamp(-Y, -1, 1)), lon = Math.atan2(X, nz);
      u[i] = lon / (Math.PI * 2) + 0.5; v[i] = Math.round((0.5 - lat / Math.PI) * 127);
      lit[i] = clamp(0.22 + 0.9 * (-0.55 * nx - 0.6 * ny + 0.58 * nz), 0.06, 1.15);
      rim[i] = Math.pow(1 - nz, 3) * 0.6;
      a[i] = clamp((1 - Math.sqrt(r2)) * r * 0.9, 0, 1);
    }
    this.lut = { u: u, v: v, lit: lit, a: a, rim: rim, D: D };
    this.off.width = this.off.height = D;
    this.img = this.off.getContext('2d').createImageData(D, D);
  };
  C.drawSphere = function (t) {
    var ctx = this.cv.getContext('2d'), W = this.cv.width, c = W / 2;
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, W, W);
    var info = this.sphereInfo(), R = this.rpx * this.scaleUp, lv = LEVEL[this.state] || 0.3;
    if (!this.sphere || this.sphere.key !== info.style + '|' + info.kind) {
      this.sphere = { key: info.style + '|' + info.kind, kind: info.kind, surf: info.kind === 'star' ? null : buildSurface(info.style || 'generic', strHash(this.brainKey)) };
    }
    var surf = this.sphere.surf, rimc = surf ? surf.rim : [1, 0.85, 0.5];
    // quầng khí quyển
    var g = ctx.createRadialGradient(c, c, R * 0.85, c, c, R * 1.5);
    g.addColorStop(0, 'rgba(' + Math.round(rimc[0] * 255) + ',' + Math.round(rimc[1] * 255) + ',' + Math.round(rimc[2] * 255) + ',' + (0.32 + 0.2 * lv * this.awake) + ')');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c, c, R * 1.5, 0, Math.PI * 2); ctx.fill();
    if (this.sphere.kind === 'star') {                              // brain chung thương hiệu: ngôi sao
      var s = ctx.createRadialGradient(c, c, 0, c, c, R);
      s.addColorStop(0, 'rgba(255,255,240,1)'); s.addColorStop(0.55, 'rgba(255,214,120,0.95)'); s.addColorStop(1, 'rgba(255,150,40,0.15)');
      ctx.fillStyle = s; ctx.beginPath(); ctx.arc(c, c, R, 0, Math.PI * 2); ctx.fill();
      ctx.globalCompositeOperation = 'lighter';
      for (var k = 0; k < 12; k++) {
        var an = k / 12 * Math.PI * 2 + t * 0.00012, len = R * (1.25 + 0.15 * Math.sin(t / 700 + k * 1.7));
        ctx.strokeStyle = 'rgba(255,200,110,0.18)'; ctx.lineWidth = R * 0.05;
        ctx.beginPath(); ctx.moveTo(c + Math.cos(an) * R * 0.8, c + Math.sin(an) * R * 0.8); ctx.lineTo(c + Math.cos(an) * len, c + Math.sin(an) * len); ctx.stroke();
      }
      ctx.globalCompositeOperation = 'source-over';
      return;
    }
    if (!this.lut) this.buildLut();
    var L = this.lut, D = L.D, d = this.img.data, rot = (t * 0.000025) % 1, TW = surf.TW, base = surf.base, em = surf.em;
    for (var i = 0, n = D * D; i < n; i++) {
      var o = i * 4, al = L.a[i];
      if (!al) { d[o + 3] = 0; continue; }
      var uu = L.u[i] + rot; uu -= Math.floor(uu);
      var ti = (L.v[i] * TW + ((uu * TW) | 0)) * 3, li = L.lit[i], rr = L.rim[i];
      d[o] = clamp((base[ti] * li + em[ti] + rimc[0] * rr) * 255, 0, 255);
      d[o + 1] = clamp((base[ti + 1] * li + em[ti + 1] + rimc[1] * rr) * 255, 0, 255);
      d[o + 2] = clamp((base[ti + 2] * li + em[ti + 2] + rimc[2] * rr) * 255, 0, 255);
      d[o + 3] = al * 255;
    }
    this.off.getContext('2d').putImageData(this.img, 0, 0);
    var drawRing = function (front) {                               // vành (Kế toán)
      ctx.save(); ctx.translate(c, c); ctx.rotate(-0.38);
      ctx.beginPath(); ctx.ellipse(0, 0, R * 1.75, R * 0.42, 0, front ? 0 : Math.PI, front ? Math.PI : Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,220,140,0.55)'; ctx.lineWidth = R * 0.12; ctx.stroke();
      ctx.strokeStyle = 'rgba(255,240,200,0.35)'; ctx.lineWidth = R * 0.03; ctx.stroke(); ctx.restore();
    };
    if (surf.ring) drawRing(false);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.off, c - R, c - R, R * 2, R * 2);
    if (surf.ring) drawRing(true);
  };

  // ---------------------------------------------------------------- hoạt cảnh
  C.spawn = function (spoke, faint) {
    var P = this.pal(), el = this.mk('circle', { r: faint ? 0.9 : 1.5, fill: faint ? P.mote : P.moteHot, filter: 'url(#bc-glow)' });
    this.pulsesG.append(el);
    var L = 0; try { L = spoke.getTotalLength(); } catch (e) {}
    this.live.push({ el: el, born: performance.now(), spoke: spoke, L: L, faint: faint });
  };
  /** Nhánh được dùng thật (Joyce đọc/ghi file, gọi công cụ): dòng hạt chạy từ lõi ra, nút sáng. */
  C.fire = function (ids) {
    var self = this, P = this.pal(), now = performance.now();
    ids.forEach(function (id, k) {
      var n = self.nodes.filter(function (m) { return m.id === id; })[0];
      if (!n) return;
      setTimeout(function () {
        if (self.disposed) return;
        n.spoke.setAttribute('stroke', P.spokeHot); n.spoke.setAttribute('stroke-width', 1.6); n.spoke.setAttribute('opacity', 0.75);
        n._until = performance.now() + 1150;
        var stream = function () { if (!self.disposed && performance.now() < n._until) { self.spawn(n.spoke, false); setTimeout(stream, 105); } };
        stream();
        setTimeout(function () { n.circ.setAttribute('filter', 'url(#bc-glow)'); n.circ.setAttribute('r', n.r + 3); n.circ.setAttribute('stroke-width', 3); n.circ.setAttribute('opacity', 1); }, 560);
        setTimeout(function () {
          n.spoke.setAttribute('stroke', P.spoke); n.spoke.setAttribute('stroke-width', 1); n.spoke.setAttribute('opacity', n.live ? 0.72 : 0.36);
          n.circ.removeAttribute('filter'); n.circ.setAttribute('r', n.r); n.circ.setAttribute('stroke-width', n.live ? 2 : 1.3); n.circ.setAttribute('opacity', n.live ? 1 : 0.6);
        }, 2050);
      }, k * 210);
      // Hai nhánh cùng được dùng trong vài giây: dây nối tạm "đang phối hợp".
      self.coRecent = self.coRecent.filter(function (c) { return now - c.t < 3500 && c.n !== n; });
      var prev = self.coRecent[self.coRecent.length - 1];
      if (prev) {
        var ln = self.mk('line', { x1: prev.n.x, y1: prev.n.y, x2: n.x, y2: n.y, stroke: P.link, 'stroke-width': 1.3, opacity: 0 });
        self.pulsesG.append(ln);
        setTimeout(function () { ln.setAttribute('opacity', 0.6); }, 560);
        setTimeout(function () { ln.remove(); }, 2600);
      }
      self.coRecent.push({ n: n, t: now });
    });
    this.awakeUntil = now + 4000;
    this.start();
  };
  C.trace = function (detail) {
    var d = detail || {};
    if (d.pha === 'start') { this.awakeUntil = performance.now() + 6000; return; }
    if (d.pha !== 'tool') return;
    var nguon = global.JoyceTriThuc && global.JoyceTriThuc.nguon;
    var ids = targetsFor(d, this.nodes, nguon);
    if (ids.length) this.fire(ids);
  };

  C.loop = function (t) {
    if (!this.running || this.disposed) return;
    var self = this;
    this.raf = requestAnimationFrame(function (x) { self.loop(x); });
    var busy = this.state !== 'idle' || (this.awakeUntil || 0) > t || this.live.length || this.hover;
    var minDt = busy ? 33 : 66;                                     // nghỉ thì 15 khung/giây là đủ
    if (t - (this.last || 0) < minDt) return;
    var dt = Math.min(0.1, (t - (this.last || t)) / 1000); this.last = t;
    var lv = LEVEL[this.state] != null ? LEVEL[this.state] : 0.32;
    this.awake += ((busy ? 1 : 0) - this.awake) * Math.min(1, dt * 2);
    this.phase = (this.phase || 0) + dt * (0.85 + 1.9 * lv);
    var k = (Math.sin(this.phase) + 1) / 2;
    for (var i = 0; i < this.nodes.length; i++) {
      var n = this.nodes[i], kk = (Math.sin(this.phase * 0.85 + n.phase) + 1) / 2;
      n.halo.setAttribute('opacity', ((n.live ? 0.16 : 0.08) + (n.live ? 0.3 : 0.16) * kk).toFixed(3));
      n.halo.setAttribute('r', (n.haloR + 2 * kk).toFixed(2));
    }
    if (this.bright) {
      this.bright.setAttribute('transform', 'rotate(' + ((t / 90) % 360).toFixed(1) + ' ' + AX + ' ' + AY + ')');
      this.swirl.setAttribute('transform', 'rotate(' + (-(t / 60) % 360).toFixed(1) + ' ' + AX + ' ' + AY + ')');
      this.swirl.setAttribute('stroke-opacity', (0.15 + 0.35 * this.awake).toFixed(2));
      var speak = this.state === 'speaking' ? 1 : 0, lvl = Math.max(this.level, 0.15 * this.awake);
      this.waves.forEach(function (w, j) {
        var p = ((t / 2600) + j / 3) % 1;
        w.setAttribute('r', (RING + p * 60).toFixed(1));
        w.setAttribute('opacity', ((1 - p) * (0.08 + 0.32 * Math.max(speak * 0.6, self.awake * 0.4, lvl))).toFixed(3));
      });
      for (var b = 0; b < this.bars.length; b++) {
        var h = 2 + (2 + 14 * lvl) * Math.abs(Math.sin(t / 180 + b * 0.8)) * (0.3 + 0.7 * this.awake);
        this.bars[b].setAttribute('height', h.toFixed(1));
        this.bars[b].setAttribute('y', (AY + RING + 50 - h / 2).toFixed(1));
        this.bars[b].setAttribute('opacity', (0.3 + 0.6 * this.awake).toFixed(2));
      }
    }
    // hạt mờ trôi từ lõi ra các nhánh: thức thì dày hơn
    if (t > (this.nextAmbient || 0) && this.live.length < (busy ? 18 : 8) && this.nodes.length) {
      this.spawn(this.nodes[(Math.random() * this.nodes.length) | 0].spoke, true);
      this.nextAmbient = t + (470 - 330 * lv * this.awake) * (0.5 + Math.random() * 0.7);
    }
    for (var q = this.live.length - 1; q >= 0; q--) {
      var p = this.live[q], pr = (t - p.born) / 620;
      if (pr >= 1 || !p.L) { p.el.remove(); this.live.splice(q, 1); continue; }
      var pt = p.spoke.getPointAtLength(pr * p.L);
      p.el.setAttribute('cx', pt.x.toFixed(1)); p.el.setAttribute('cy', pt.y.toFixed(1));
      p.el.setAttribute('opacity', ((p.faint ? 0.4 : 0.9) * Math.sin(pr * Math.PI)).toFixed(3));
    }
    this.drawSphere(t);
  };
  C.start = function () {
    if (this.running || this.disposed || !this.visible) return;
    if (this.reduced) { this.drawSphere(0); return; }
    this.running = true; var self = this;
    this.raf = requestAnimationFrame(function (x) { self.loop(x); });
  };
  C.stop = function () { this.running = false; cancelAnimationFrame(this.raf); };
  C.show = function (on) {
    this.visible = !!on;
    this.root.hidden = !on;
    if (on) { this.place(); this.start(); this.drawSphere(performance.now()); } else { this.stop(); this.closeCard(); }
  };
  C.resize = function () { this.place(); if (this.visible) this.drawSphere(performance.now()); };

  // ---------------------------------------------------------------- thẻ tổng quan
  C.closeCard = function () { this.card.hidden = true; this.card.replaceChildren(); };
  C.openCard = function (n) {
    var self = this, card = this.card, col = n.layer === 'core' ? this.pal().gold : n.col;
    card.replaceChildren(); card.hidden = false; card.style.setProperty('--bc-c', col);
    var head = document.createElement('div'); head.className = 'bc-card-head';
    var dot = document.createElement('span'); dot.className = 'bc-dot';
    var ttl = document.createElement('div'); ttl.className = 'bc-card-ttl';
    var sub = document.createElement('div'); sub.className = 'bc-card-sub';
    var x = document.createElement('button'); x.type = 'button'; x.className = 'bc-x'; x.textContent = '×';
    x.setAttribute('aria-label', tt('tv.close')); x.onclick = function () { self.closeCard(); };
    var box = document.createElement('div'); box.append(ttl, sub);
    head.append(dot, box, x); card.appendChild(head);
    var body = document.createElement('div'); body.className = 'bc-card-body'; card.appendChild(body);
    var btn = function (label, fn) { var b = document.createElement('button'); b.type = 'button'; b.className = 'bc-btn'; b.textContent = label; b.onclick = fn; return b; };
    card.setAttribute('aria-label', n.label || '');
    if (n.layer === 'core') {
      var info = this.sphereInfo();
      ttl.textContent = String(info.ten || '').toUpperCase();
      sub.textContent = tt('tv.core_meta', { n: this.total, l: this.links });
      body.appendChild(btn(tt('tv.open_net'), function () { self.closeCard(); if (self.opts.onNoteMode) self.opts.onNoteMode(); }));
    } else if (n.layer === 'mcp') {
      ttl.textContent = n.label.toUpperCase();
      sub.textContent = tt('tv.layer_mcp');
      var st = document.createElement('div'); st.className = 'bc-status' + (n.live ? ' on' : '');
      st.textContent = tt(n.live ? 'tv.mcp_on' : 'tv.mcp_off'); body.appendChild(st);
      body.appendChild(btn(tt('tv.open_connect'), function () {
        self.closeCard(); try { if (global.Alpine) global.Alpine.store('nav').go('mcp'); } catch (e) {}
      }));
    } else {
      ttl.textContent = n.label.toUpperCase();
      sub.textContent = tt(n.layer === 'ops' ? 'tv.layer_ops' : 'tv.layer_know') + ' · ' + tt('tv.meta', { n: n.count, p: Math.round(n.count / (this.total || 1) * 100) });
      var cap = document.createElement('div'); cap.className = 'bc-cap'; cap.textContent = tt('tv.recent'); body.appendChild(cap);
      var list = document.createElement('div'); list.className = 'bc-list';
      var notes = (this.opts.notesOf ? this.opts.notesOf(n.key) : []).slice(0, 6);
      if (!notes.length) { var e0 = document.createElement('div'); e0.className = 'bc-empty'; e0.textContent = tt('tv.empty'); list.appendChild(e0); }
      notes.forEach(function (note) {
        var b = btn(note.label || note.path, function () { if (global.onGraphNodeClick) global.onGraphNodeClick(note); });
        b.className = 'bc-note'; list.appendChild(b);
      });
      body.appendChild(list);
      var row = document.createElement('div'); row.className = 'bc-row';
      if (n.key === 'agents' || n.key === 'skills' || n.key === 'workflows') {
        row.appendChild(btn(tt('tv.open_studio'), function () {
          self.closeCard(); var s = document.querySelector('#brainStats .bstat[data-tab="' + n.key + '"]'); if (s) s.click();
        }));
      }
      row.appendChild(btn(tt('tv.open_net'), function () { self.closeCard(); if (self.opts.onNoteMode) self.opts.onNoteMode(n.key); }));
      body.appendChild(row);
    }
    // kéo thả bằng thanh tiêu đề
    head.onpointerdown = function (e) {
      if (e.target === x) return;
      var r = card.getBoundingClientRect(), pr = self.root.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
      var mv = function (ev) { card.style.left = (ev.clientX - pr.left - sx) + 'px'; card.style.top = (ev.clientY - pr.top - sy) + 'px'; card.style.transform = 'none'; };
      var up = function () { document.removeEventListener('pointermove', mv); document.removeEventListener('pointerup', up); };
      document.addEventListener('pointermove', mv); document.addEventListener('pointerup', up);
    };
    card.style.left = ''; card.style.top = ''; card.style.transform = '';
    setTimeout(function () { try { x.focus(); } catch (e) {} }, 0);
  };

  C.dispose = function () {
    this.disposed = true; this.stop();
    document.removeEventListener('keydown', this._onKey);
    this.root.remove();
  };

  global.JoyceConstellation = Constellation;

  // ---------------------------------------------------------------- nối vào khoang não
  // Chế độ của lớp nhìn Tinh vân: "chom" (chòm sao, mặc định) hoặc "note" (đồ thị note cũ, graph.js).
  // Lớp .tv-chom trên .hud-center che đồ thị note bằng CSS; đồ thị vẫn nạp dữ liệu (thẻ tổng quan
  // lấy danh sách note từ đó) nhưng tạm dừng vẽ cho đỡ tốn CPU.
  var MODE_KEY = 'joyce.tvMode';
  function brainOfSelect() {
    var sel = document.getElementById('graphSource'), v = sel ? sel.value : 'brain';
    var key = v.indexOf('path:') === 0 ? v.slice(5).replace(/[\\/]+$/, '').split(/[\\/]/).pop() : 'Brain Default';
    var opt = sel && sel.selectedOptions && sel.selectedOptions[0];
    var ten = opt ? String(opt.textContent || '').replace(/\s*·\s*\d+\s*$/, '').trim() : '';
    return { key: key, ten: ten };
  }
  function graphNodes() {
    var g = global.__joyceGraph;
    try { return (g && g.graph && g.graph.graphData().nodes) || []; } catch (e) { return []; }
  }
  function notesOf(key) {
    return graphNodes().filter(function (n) {
      var segs = String(n.path || '').split('/'); if (segs.length < 3) return false;
      var f = folderOf(segs[1]); return f && f.key === key;
    }).sort(function (a, b) { return (b.t || 0) - (a.t || 0); });
  }
  function boot() {
    var host = document.querySelector('.hud-center');
    if (!host || host.__tv) return;
    var mode = 'chom';
    try { if (localStorage.getItem(MODE_KEY) === 'note') mode = 'note'; } catch (e) {}
    var inst = host.__tv = new Constellation(host, { notesOf: notesOf, onNoteMode: function () { setMode('note'); } });
    var btn = document.getElementById('tvModeBtn');
    var hudOn = function () { return host.classList.contains('hud-on'); };
    function apply() {
      var chom = mode === 'chom';
      host.classList.toggle('tv-chom', chom);
      inst.show(chom && !hudOn() && !document.hidden);
      var g = global.__joyceGraph;
      if (g && !hudOn()) { try { if (chom) g.pause(); else { g.wake(); if (g.refit) g.refit(300); } } catch (e) {} }
      if (btn) {
        btn.setAttribute('aria-pressed', chom ? 'false' : 'true');
        var k = chom ? 'tv.mode_to_note' : 'tv.mode_to_chom';
        btn.setAttribute('aria-label', tt(k)); btn.title = tt(k);
      }
    }
    function setMode(m) { mode = m === 'note' ? 'note' : 'chom'; try { localStorage.setItem(MODE_KEY, mode); } catch (e) {} apply(); }
    function syncBrain() { var b = brainOfSelect(); inst.setBrain(b.key, b.ten); }
    if (btn) btn.addEventListener('click', function () { setMode(mode === 'chom' ? 'note' : 'chom'); });
    // Timelapse chỉ có ở đồ thị note: bấm khi đang ở chòm sao thì chuyển sang Mạng note trước
    // (bắt ở pha capture của document để chạy TRƯỚC trình xử lý timelapse của brain-view.js).
    document.addEventListener('click', function (e) {
      if (mode === 'chom' && e.target && e.target.closest && e.target.closest('#graphTimelapseBtn')) setMode('note');
    }, true);
    global.addEventListener('joyce:graph-data', function (e) {
      var d = e.detail || {}; syncBrain(); inst.setGraph(d.nodes || graphNodes(), d.stats || null);
    });
    var addT = null;
    global.addEventListener('joyce:graph-add', function () {
      clearTimeout(addT); addT = setTimeout(function () { inst.setGraph(graphNodes(), null); }, 800);
    });
    global.addEventListener('joyce:turn-trace', function (e) { if (inst.visible) inst.trace(e.detail); });
    global.addEventListener('joyce:hud-view', apply);
    global.addEventListener('joyce-graph-created', function () { setTimeout(apply, 0); });   // đồ thị note sinh SAU file này: dừng vẽ nó nếu đang ở chòm sao
    global.addEventListener('joyce:i18n', function () { inst.render(); apply(); });
    global.addEventListener('joyce-theme-change', function (e) { inst.setTheme(!!(e && e.detail && e.detail.light)); });
    document.addEventListener('visibilitychange', apply);
    document.addEventListener('change', function (e) { if (e.target && e.target.id === 'graphSource') syncBrain(); });
    var rzT = null, lastW = host.clientWidth;
    global.addEventListener('resize', function () {
      clearTimeout(rzT);
      rzT = setTimeout(function () {
        var w = host.clientWidth;
        if ((w < 620) !== (lastW < 620)) inst.render(); else inst.resize();   // qua mốc điện thoại thì dựng lại
        lastW = w;
      }, 200);
    });
    var getJ = function (u) { return fetch(u, { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); };
    getJ('/knowledge/galaxy').then(function (g) { if (g && g.ok !== false) { inst.setGalaxy(g); inst.render(); } });
    var loadMcp = function () { getJ('/mcp/list').then(function (d) { if (d && d.servers) inst.setMcp(d.servers); }); };
    loadMcp(); setInterval(function () { if (inst.visible) loadMcp(); }, 300000);
    syncBrain();
    if (graphNodes().length) inst.setGraph(graphNodes(), null);   // đồ thị đã nạp trước khi file này chạy
    apply();
    global.JoyceTinhVan = {
      setState: function (s) { inst.setState({ listening: 'listening', thinking: 'thinking', speaking: 'speaking' }[s] || 'idle'); },
      setLevel: function (v) { if (inst.visible) inst.setLevel(v); },
      mode: function () { return mode; }, setMode: setMode,
    };
  }
  if (typeof document !== 'undefined' && document.addEventListener) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Constellation: Constellation, folderOf: folderOf, layerOf: layerOf, groupFolders: groupFolders,
                       layout: layout, targetsFor: targetsFor, sphereFor: sphereFor, buildSurface: buildSurface,
                       GEOM: { VW: VW, VH: VH, AX: AX, AY: AY, RING: RING, MINR: MINR } };
  }
})(typeof window !== 'undefined' ? window : globalThis);
