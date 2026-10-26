/* ============================================================================
 * JOYCE MUSIC COMMAND - bắt lệnh nhạc bằng giọng (1.0.0).
 *
 * Chạy tại máy như JoyceSceneCmd: transcript khớp -> JoyceMusic xử lý ngay,
 * không đi vòng qua model. "mở nhạc lofi" phát Audius; "mở nhạc trên youtube"
 * mở tab YouTube Music; "mở nhạc trong máy" phát file local; "tắt nhạc",
 * "bài tiếp", "to lên" điều khiển player đang mở.
 *
 *   parse(text, opts) -> {action:'play'|'stop'|'resume'|'next'|'prev'|
 *                         'volup'|'voldown', query?, source?} | null
 *   try_(text, opts)  -> Promise<{action,label}|null>  (parse + áp dụng)
 *
 * opts.playerActive=true cho phép lệnh điều khiển trơn ("bài tiếp", "to lên").
 * Câu kể chuyện có chữ "nhạc" ("tôi thích nghe nhạc") không trúng vì thiếu
 * động từ ra lệnh đứng đầu cụm.
 * ========================================================================== */
(function (global) {
  'use strict';

  // Động từ mở/phát (đã strip). 'nghe' một mình không đủ ("tôi thích nghe nhạc"
  // là kể, không phải lệnh) - chỉ tính 'cho nghe'/'nghe thử' dạng mời mở.
  const PLAY = ['mo nhac', 'bat nhac', 'phat nhac', 'mo bai', 'bat bai', 'phat bai',
    'cho nghe', 'cho toi nghe', 'mo cho', 'bat cho', 'phat cho', 'cho mo', 'cho phat',
    'mo playlist', 'bat album', 'play', 'put on', 'nghe nhac', 'nghe bai'];
  const STOP = ['tat nhac', 'dung nhac', 'dung phat', 'tam dung nhac', 'ngung nhac',
    'ngat nhac', 'tat bai', 'stop music', 'stop the music', 'turn off music', 'pause music', 'pause the music'];
  const PAUSE = ['tam dung', 'dung lai nhac', 'pause'];
  const RESUME = ['phat tiep', 'tiep tuc phat', 'choi tiep', 'mo tiep', 'bat lai nhac',
    'resume', 'continue', 'tiep tuc nhac'];
  const NEXT = ['bai tiep', 'bai ke', 'qua bai', 'chuyen bai', 'doi bai', 'doi nhac',
    'bo bai', 'next song', 'next track', 'skip', 'next'];
  const PREV = ['bai truoc', 'lui bai', 'quay lai bai', 'bai vua roi', 'previous song', 'prev'];
  const VOLUP = ['to len', 'to hon', 'to len chut', 'tang am luong', 'louder', 'volume up', 'turn it up'];
  const VOLDOWN = ['nho lai', 'nho di', 'be lai', 'nho hon', 'giam am luong', 'vua thoi',
    'quieter', 'volume down', 'turn it down', 'lower'];
  // Gợi ý nguồn trong câu lệnh.
  const SRC = [
    [/\b(youtube|yt|you tube)\b/, 'youtube'],
    [/\b(trong may|trong may tinh|may tinh|local|ofline|offline|cua toi|nhac cua toi|nhac may)\b/, 'local'],
    [/\b(audius)\b/, 'audius'],
    [/\b(nhaccuatui|zing ?mp3|zing)\b/, 'youtube'],   // chưa có API: ngã mở YouTube
  ];
  // Từ chỉ nhạc nói chung - xoá khỏi phần query.
  const MUSIC_NOUN = ['nhac', 'bai nhac', 'bai hat', 'bai', 'music', 'song', 'songs',
    'track', 'am nhac', 'giai dieu', 'playlist', 'album'];
  const FILLER = ['joyce', 'oi', 'nhe', 'nha', 'di', 'ma', 'giup toi', 'giup minh',
    'giup', 'cho toi', 'cho minh', 'ho toi', 'ho minh', 'cai', 'mot chut', 'ti', 'chut',
    'di nao', 'nay', 'luon', 'ngay', 'dung', 'voi', 'nhe nhang', 'di cho', 'duoc khong',
    'please', 'hey', 'cho', 'ho'];

  function strip(s) {
    return String(s || '').toLowerCase()
      .replace(/đ/g, 'd').replace(/Đ/g, 'd')
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ').trim();
  }
  const has = (s, w) => new RegExp('(^|\\s)' + w.replace(/\s/g, '\\s') + '(\\s|$)').test(s);

  function sourceOf(s) {
    for (const [re, id] of SRC) if (re.test(s)) return id;
    return '';
  }

  /** Bỏ động từ mở + danh từ nhạc + gợi ý nguồn + đệm -> phần còn lại là query. */
  function queryOf(s) {
    let q = ' ' + s + ' ';
    for (const v of PLAY.concat(STOP, PAUSE, RESUME, NEXT, PREV, VOLUP, VOLDOWN))
      q = q.replace(new RegExp('\\s' + v.replace(/\s/g, '\\s') + '\\s', 'g'), ' ');
    for (const [re] of SRC) q = q.replace(new RegExp(re.source, 'g'), ' ');
    for (const n of MUSIC_NOUN) q = q.replace(new RegExp('\\s' + n.replace(/\s/g, '\\s') + '\\s', 'g'), ' ');
    for (const f of FILLER) q = q.replace(new RegExp('\\s' + f.replace(/\s/g, '\\s') + '\\s', 'g'), ' ');
    // 'tren'/'trong' dư từ gợi ý nguồn ("nhạc trên youtube").
    q = q.replace(/\s(tren|trong|o|bang|on|in|from)\s/g, ' ');
    return q.replace(/\s+/g, ' ').trim();
  }

  function parse(text, opts) {
    const s = strip(text);
    if (!s) return null;
    const active = !!(opts && opts.playerActive);

    // Điều khiển - cần danh từ nhạc trong câu HOẶC player đang mở.
    const musicish = MUSIC_NOUN.some(n => has(s, n)) || active;
    if (musicish) {
      if (STOP.some(v => has(s, v))) return { action: 'stop' };
      if (RESUME.some(v => has(s, v))) return { action: 'resume' };
      if (NEXT.some(v => has(s, v))) return { action: 'next' };
      if (PREV.some(v => has(s, v))) return { action: 'prev' };
      if (VOLUP.some(v => has(s, v))) return { action: 'volup' };
      if (VOLDOWN.some(v => has(s, v))) return { action: 'voldown' };
      if (PAUSE.some(v => has(s, v))) return { action: 'stop' };
    }

    // Mở/phát: cần động từ PLAY đứng kèm danh từ nhạc, HOẶC "play <gì đó>".
    const hasPlay = PLAY.some(v => has(s, v));
    const hasNoun = MUSIC_NOUN.some(n => has(s, n));
    if (!hasPlay || (!hasNoun && !has(s, 'play'))) return null;
    // Chống kể chuyện: "thich nghe nhac", "hay nghe nhac di" (sở thích/khuyên,
    // không phải mệnh lệnh mở). Phải có cả từ kể VÀ vắng mặt động từ mở mới loại.
    if (/\b(thich|hay|nen|se|dang|muon nghe|thich nghe)\b/.test(s) && !/(mo nhac|bat nhac|phat|cho nghe|play|choi nhac)/.test(s)) return null;
    return { action: 'play', query: queryOf(s), source: sourceOf(s) || 'auto' };
  }

  function labelFor(r) {
    const t = global.t || (k => k);
    if (r.label) return r.label;
    switch (r.action) {
      case 'stop': return t('music.stopped');
      case 'resume': return t('music.resumed');
      case 'next': return t('music.next');
      case 'prev': return t('music.prev');
      case 'volup': case 'voldown': return t('music.volume', { n: r.volume });
      default: return t('music.playing', { name: r.name || '' });
    }
  }

  async function try_(text, opts) {
    const hit = parse(text, opts);
    if (!hit) return null;
    const M = global.JoyceMusic;
    if (!M) return null;
    if (hit.action === 'play') {
      const r = await M.play(hit.query, { source: hit.source });
      return { action: r.action || 'play', label: r.label || labelFor({ action: 'play', name: hit.query }) };
    }
    if (hit.action === 'stop') { M.stop(); return { action: 'stop', label: labelFor({ action: 'stop' }) }; }
    if (hit.action === 'resume') { M.resume(); return { action: 'resume', label: labelFor({ action: 'resume' }) }; }
    if (hit.action === 'next') { M.next(); return { action: 'next', label: labelFor({ action: 'next' }) }; }
    if (hit.action === 'prev') { M.prev(); return { action: 'prev', label: labelFor({ action: 'prev' }) }; }
    if (hit.action === 'volup') { const n = M.volume(0.15); return { action: 'volup', label: labelFor({ action: 'volup', volume: n }) }; }
    if (hit.action === 'voldown') { const n = M.volume(-0.15); return { action: 'voldown', label: labelFor({ action: 'voldown', volume: n }) }; }
    return null;
  }

  const api = { parse, try: try_, strip };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.JoyceMusicCmd = api;
})(typeof window !== 'undefined' ? window : globalThis);
