/* ============================================================================
 * JOYCE SCENE COMMAND - bắt lệnh đổi cảnh nền avatar bằng giọng (1.0.0).
 *
 * Chạy hoàn toàn tại máy: transcript khớp thì JoyceBackdrops/JoyceHumanoid đổi
 * cảnh ngay, KHÔNG đi vòng qua model (nhanh, miễn phí, không gây lỗi não).
 *
 *   parse(text, opts) -> {id:'beach'|...|'next'} | null   (hàm thuần, test được)
 *   try_(text, opts)  -> {id, label} | null               (parse + áp dụng)
 *
 * Luật kích hoạt (đã strip dấu): có keyword cảnh VÀ (động từ đổi/xem HOẶC danh
 * từ nền/cảnh HOẶC câu chỉ gồm đúng keyword khi đang nhìn avatar). "kể cho tôi
 * về bãi biển" không trúng (thiếu intent); "bãi biển" trơn chỉ trúng khi đang
 * mở lớp nhìn 3D Joyce - lúc đó gần như chắc là lệnh.
 * ========================================================================== */
(function (global) {
  'use strict';

  // Keyword -> id cảnh. Dạng đã strip (không dấu, đ->d). Từ nhiều chữ xếp trước
  // để khớp lâu nhất thắng ("dai ngan ha" thắng "ngan ha").
  const KW = {
    beach:    ['bai bien', 'bo bien', 'bien', 'beach', 'dai duong', 'bai cat', 'song bien'],
    sunset:   ['hoang hon', 'sunset', 'chieu ta', 'mat troi lan', 'luc chieu', 'nang toi'],
    sunrise:  ['binh minh', 'sunrise', 'rang dong', 'ban mai', 'mat troi moc', 'tro sang', 'luc sang', 'mai sang'],
    planets:  ['hanh tinh', 'ngoai hanh tinh', 'planet', 'vu tru', 'ngoai vu tru', 'khong gian vu tru', 'outer space', 'space', 'sao hoa', 'sao kim', 'sao moc', 'sao tho'],
    milkyway: ['dai ngan ha', 'ngan ha', 'thien ha', 'milky way', 'milkyway', 'milky', 'galaxy', 'sao troi', 'bau troi sao', 'dem sao', 'tro sao', 'loi nuoc'],
    mountain: ['day nui', 'doi nui', 'ngon nui', 'nui', 'mountain', 'mac dinh', 'canh cu', 'canh goc', 'goc', 'ban dau', 'nhu cu'],
  };

  // Động từ/danh từ báo ý đồ đổi cảnh (đã strip). Tránh từ quá lỏng: 'cho' và
  // 've' một mình xuất hiện trong văn kể thường ("kể cho tôi về bãi biển" là câu
  // chuyện, không phải lệnh) - dạng ghép 'cho toi xem'/'quay ve' thì 'xem'/'tro ve'
  // đã bắt được rồi.
  const VERB = ['doi', 'chuyen sang', 'chuyen qua', 'chuyen canh', 'chuyen nen', 'chuyen doi', 'dat', 'mo', 'bat', 'xem', 'hien', 'hien thi', 'tro ve', 'quay ve', 'sang', 'thanh', 'lay', 'mang', 'dua', 'set', 'change', 'switch', 'show', 'display', 'make', 'muon', 'toi muon', 'give'];
  const NOUN = ['nen', 'background', 'backdrop', 'phong nen', 'hinh nen', 'phong canh', 'khung canh', 'canh', 'giao dien', 'wallpaper', 'hinh anh'];

  // Bỏ dấu tiếng Việt + ký tự lạ để so khớp. đ/Đ không phân rã qua NFD nên thay tay.
  function strip(s) {
    return String(s || '').toLowerCase()
      .replace(/đ/g, 'd').replace(/Đ/g, 'd')
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ').trim();
  }

  const contains = (s, w) => new RegExp('(^|\\s)' + w.replace(/\s/g, '\\s') + '(\\s|$)').test(s);

  /** {id} | {id:'next'} (đổi cảnh không chỉ đích) | null. opts.avatarActive cho
   *  phép câu trơn chỉ gồm keyword ("bãi biển") khi đang mở lớp nhìn 3D. */
  function parse(text, opts) {
    const s = strip(text);
    if (!s) return null;
    const verb = VERB.some(v => contains(s, v));
    const noun = NOUN.some(v => contains(s, v));
    // Nhiều keyword cùng câu: ý CUỐI thường là đích ("bãi biển như bên Lõi nước"
    // -> muốn cảnh Lõi nước). Bằng vị trí thì keyword dài hơn thắng.
    let hit = null;
    for (const id in KW) for (const k of KW[id]) {
      const re = new RegExp('(^|\\s)' + k.replace(/\s/g, '\\s') + '(\\s|$)');
      const m = re.exec(s);
      if (m && (!hit || m.index > hit.at || (m.index === hit.at && k.length > hit.k.length)))
        hit = { id, k, at: m.index };
    }
    if (hit && (verb || noun)) return { id: hit.id };
    // Câu trơn đúng một keyword của cảnh (kèm 'joyce'/'ơi'/'đi' đệm vẫn tính):
    // chỉ khi đang nhìn avatar - lúc đó nói trơn tên cảnh gần như chắc là lệnh.
    if (hit && opts && opts.avatarActive) {
      const bare = s.replace(/^(oi\s+|nay\s+)?joyce\s+/, '').replace(/^(oi|nay|a|ma)\s+/, '')
                    .replace(/\s+(nay|ne|di|thoi|di ma|nhe|nha)$/, '');
      if (KW[hit.id].some(k => bare === k)) return { id: hit.id };
    }
    // "đổi nền" / "đổi cảnh" không đích -> xoay cảnh kế.
    if (!hit && (verb && noun)) return { id: 'next' };
    return null;
  }

  function labelFor(id) {
    const B = global.JoyceBackdrops;
    const def = B && B.get(id);
    try {
      const v = global.t && global.t('scene.' + id);
      if (v && v !== 'scene.' + id) return v;
    } catch (e) {}
    if (def) {
      const lang = (global.document && document.documentElement.lang || 'vi').slice(0, 2);
      return lang === 'en' ? def.en : def.vi;
    }
    return id;
  }

  /** parse + áp dụng qua JoyceHumanoid.setScene. {id,label} | null. 'next' được
   *  quyết thành id thật theo cảnh đang chọn. */
  function try_(text, opts) {
    const hit = parse(text, opts);
    if (!hit) return null;
    const B = global.JoyceBackdrops, H = global.JoyceHumanoid;
    let id = hit.id;
    if (id === 'next') {
      const list = (B ? B.list() : []).map(s => s.id);
      const cur = (H && H.scene && H.scene()) || 'mountain';
      id = list.length ? list[(Math.max(0, list.indexOf(cur)) + 1) % list.length] : 'mountain';
    }
    try { if (H && H.setScene) H.setScene(id); } catch (e) {}
    return { id, label: labelFor(id) };
  }

  const api = { parse, try: try_, strip, KW };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.JoyceSceneCmd = api;
})(typeof window !== 'undefined' ? window : globalThis);
