/* ============================================================================
 * JOYCE VOICE CLONE COMMAND - bắt lệnh "fake giọng anh/em/tôi" bằng giọng nói,
 * xử lý trọn tại máy: ghi mẫu từ chính mic đang nghe -> POST /voices/clone ->
 * settings tts_provider=clone. KHÔNG đi vòng qua model (nhanh, 0 quota).
 *
 * Luồng:
 *   1. onTranscript khớp lệnh clone  -> arm: Joyce nói "nói câu ~10s" + chờ.
 *   2. onInterim đầu tiên sau arm    -> bắt đầu MediaRecorder trên micStream
 *      (echoCancellation sẵn nên không dính tiếng loa của Joyce).
 *   3. onTranscript kế tiếp          -> nuốt chữ (đó là câu mẫu, không gửi não),
 *      dừng recorder, upload, lưu settings, Joyce xác nhận BẰNG giọng vừa clone.
 *   4. Lệnh "giọng cũ/giọng mặc định" -> revert tts_provider=edge.
 *
 *   init({stream, speak, toast})   - stream() trả MediaStream mic đang mở
 *   onTranscript(text) -> bool     - true = đã xử lý, đừng gửi não
 *   onInterim(text)                - gọi để biết người bắt đầu nói (ghi âm)
 * ========================================================================== */
(function (global) {
  'use strict';

  function strip(s) {
    return String(s || '').toLowerCase()
      .replace(/đ/g, 'd').replace(/Đ/g, 'd')
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ').trim();
  }

  // Cụm báo ý đồ nhân bản giọng (đã strip). Chỉ cần chứa 1 cụm -> lệnh clone;
  // thiếu mục tiêu thì mặc định "giọng của tôi".
  const CLONE_KW = [
    'fake giong', 'nhan ban giong', 'hoc giong', 'gia giong', 'bat chuoc giong',
    'clone giong', 'sao chep giong', 'copy giong', 'doc bang giong cua',
    'noi bang giong cua', 'noi giong cua', 'dung giong cua', 'lay giong cua',
    'giong noi cua', 'giong cua toi', 'giong cua anh', 'giong cua em',
    'giong cua minh', 'clone my voice', 'copy my voice', 'use my voice',
  ];
  const REVERT_KW = [
    'doi lai giong', 'giong cu', 'giong mac dinh', 've giong cu', 'quay lai giong',
    'dung lai giong joyce', 'tat giong nhan ban', 'dung giong mac dinh',
    'giong joyce cu', 'bo giong nhan ban', 'tra lai giong', 'default voice',
    'old voice', 'original voice',
  ];

  // Suy ra tên hồ sơ từ đại từ sau "cua". Không khớp -> "Giọng của tôi".
  function voiceName(s) {
    const m = s.match(/cua\s+([a-z0-9\s]{1,20})/);
    const who = m ? m[1].trim().split(/\s+/)[0] : '';
    const map = { anh: 'Giọng anh', em: 'Giọng em', chi: 'Giọng chị', co: 'Giọng cô', chu: 'Giọng chú', toi: 'Giọng của tôi', minh: 'Giọng của tôi', tao: 'Giọng của tôi', my: 'My voice' };
    if (map[who]) return map[who];
    if (/my voice/.test(s)) return 'My voice';
    if (/giong cua (toi|minh)/.test(s)) return 'Giọng của tôi';
    if (who && who.length >= 2) return 'Giọng ' + who;
    return 'Giọng của tôi';
  }

  // Khớp theo ranh từ - "giong cu" KHÔNG được ăn trong "giong cua anh".
  const has = (s, w) => new RegExp('(^|\\s)' + w.replace(/\s/g, '\\s') + '(?=\\s|$)').test(s);

  /** {action:'clone', name} | {action:'revert'} | null (hàm thuần, test được). */
  function parse(text) {
    const s = strip(text);
    if (!s) return null;
    if (REVERT_KW.some(k => has(s, k))) return { action: 'revert' };
    if (CLONE_KW.some(k => has(s, k))) return { action: 'clone', name: voiceName(s) };
    return null;
  }

  // ---- Trạng thái chạy ----
  let _ctx = null;       // {stream, speak, toast}
  let _armed = null;     // {name, deadline, timer}
  let _rec = null;       // MediaRecorder đang ghi câu mẫu
  let _chunks = [];
  let _tail = null;      // timeout đuôi sau câu chốt
  let _cap = null;       // timeout chặn trần 20s

  function init(ctx) { _ctx = ctx || null; }

  function _say(key, fb) {
    const t = global.t ? global.t(key) : fb;
    if (_ctx && _ctx.speak) _ctx.speak(t);
    if (_ctx && _ctx.toast) _ctx.toast(t);
  }

  function _disarm() {
    if (_armed && _armed.timer) clearTimeout(_armed.timer);
    _armed = null;
  }

  function _cancel(msg) {
    _disarm();
    _stopRec(false);
    if (msg) _say('voice.clonecmd_timeout', msg);
  }

  function _stopRec(use) {
    clearTimeout(_tail); _tail = null;
    clearTimeout(_cap); _cap = null;
    const r = _rec; _rec = null;
    if (!r) return;
    if (!use) { try { r.onstop = null; r.state !== 'inactive' && r.stop(); } catch (e) {} _chunks = []; return; }
    if (r.state === 'inactive') {
      // Đã tự dừng trước đó - onstop không bắn lại, xử lý blob luôn.
      const blob = _chunks.length ? new Blob(_chunks, { type: r.mimeType || 'audio/webm' }) : null;
      _chunks = [];
      _uploadDone(blob);
      return;
    }
    try { r.stop(); } catch (e) { _uploadDone(null); }
  }

  function _startRec() {
    if (_rec || !_armed || !_ctx || !_ctx.stream) return;
    const st = _ctx.stream();
    if (!st || typeof MediaRecorder === 'undefined') { _cancel(); return; }
    const opts = {};
    if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm;codecs=opus'))
      opts.mimeType = 'audio/webm;codecs=opus';
    try {
      _rec = new MediaRecorder(st, opts);
      _chunks = [];
      _rec.ondataavailable = ev => { if (ev.data && ev.data.size) _chunks.push(ev.data); };
      _rec.onstop = () => {
        const blob = _chunks.length ? new Blob(_chunks, { type: _rec.mimeType || 'audio/webm' }) : null;
        _uploadDone(blob);
      };
      _rec.start();
      // Trần 20s: v-tts chỉ cần 3-10s, nói dài hơn cũng cắt lấy phần đầu.
      _cap = setTimeout(() => _stopRec(true), 20000);
    } catch (e) { _rec = null; _cancel(); }
  }

  async function _uploadDone(blob) {
    const armed = _armed; _disarm();
    if (!armed) { _chunks = []; return; }
    if (!blob || blob.size < 8000) {   // < ~2-3s opus
      _say('voice.clonecmd_short', 'Mẫu ngắn quá, anh nói câu dài hơn một chút nhé.');
      return;
    }
    _say('voice.clonecmd_saving', 'Đang học giọng, một chút thôi...');
    try {
      const fd = new FormData();
      fd.append('file', blob, 'mau-giong.webm');
      fd.append('name', armed.name);
      const r = await (await fetch('/voices/clone', { method: 'POST', body: fd })).json();
      if (!r || !r.ok || !r.voice) { _say('voice.clonecmd_fail', 'Không lưu được giọng, anh thử lại nhé.'); return; }
      const s = await (await fetch('/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'section=voice&data=' + encodeURIComponent(JSON.stringify(
          { tts_provider: 'clone', clone_voice: r.voice.slug })),
      })).json();
      if (!s || !s.ok) { _say('voice.clonecmd_fail', 'Lưu giọng xong mà chưa bật được, anh chọn lại trong cài đặt nhé.'); return; }
      _say('voice.clonecmd_done', 'Xong rồi, giờ em nói bằng giọng của anh nè.');
    } catch (e) { _say('voice.clonecmd_fail', 'Có lỗi khi lưu giọng, anh thử lại nhé.'); }
  }

  async function _revert() {
    try {
      await fetch('/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'section=voice&data=' + encodeURIComponent(JSON.stringify({ tts_provider: 'edge' })),
      });
      _say('voice.clonecmd_reverted', 'Ok, em quay lại giọng mặc định rồi.');
    } catch (e) { _say('voice.clonecmd_fail', 'Có lỗi, anh thử lại nhé.'); }
  }

  /** onInterim từ JoyceVoice: người bắt đầu nói sau khi được dặn -> ghi mẫu. */
  function onInterim(text) {
    if (_armed && !_rec && strip(text)) _startRec();
  }

  /** onTranscript từ JoyceVoice. Trả true = đã xử lý xong (nuốt câu). */
  function onTranscript(text) {
    // Đang ghi câu mẫu: câu này là MẪU GIỌNG - dừng recorder (đuôi 500ms cho
    // chắc), nuốt chữ không gửi não dù text rỗng.
    if (_rec) { _tail = setTimeout(() => _stopRec(true), 500); return true; }
    // Đã arm mà chưa ai nói -> vẫn chờ (câu rỗng lẻ không hủy).
    const hit = parse(text);
    if (!hit) {
      if (_armed && !_rec) {
        // Provider không bắn interim transcript (OpenAI realtime thuần): câu mẫu
        // vừa nói đã trôi qua trước khi kịp mở recorder. Mở ghi từ BÂY GIỜ cho
        // câu kế tiếp, vẫn nuốt câu này khỏi não để lệnh đi tiếp.
        _startRec();
        if (_rec) { _say('voice.clonecmd_again', 'Em chưa kịp ghi, anh nói thêm một câu nữa nhé.'); return true; }
      }
      return false;
    }
    if (hit.action === 'revert') { _disarm(); _revert(); return true; }
    if (!_ctx || !_ctx.stream || !_ctx.stream()) {
      _say('voice.clonecmd_need_mic', 'Mở mic lên đã rồi nói lại nhé - em cần nghe giọng thật của anh.');
      return true;
    }
    _disarm();   // đang chờ mẫu cũ thì hủy, arm lượt mới (timer cũ không bắn nhầm)
    _armed = { name: hit.name };
    _armed.timer = setTimeout(() => {
      _armed = null;
      _say('voice.clonecmd_timeout', 'Lâu quá em chưa nghe được, lúc nào rảnh nói lại nhé.');
    }, 30000);
    _say('voice.clonecmd_prompt', 'Ok, giờ anh nói một câu gì đó dài khoảng mười giây để em học giọng.');
    return true;
  }

  global.JoyceVoiceCloneCmd = { init, parse, onTranscript, onInterim };
})(window);
