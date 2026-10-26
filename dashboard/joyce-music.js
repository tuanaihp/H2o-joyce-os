/* ============================================================================
 * JOYCE MUSIC - trình phát nhạc mini điều khiển bằng giọng (1.0.0).
 *
 * Nguồn phát (tất cả FREE, không khoá API, không đụng quota):
 *   - audius : Audius public API (api.audius.co) - stream bài đầy đủ, không cần
 *              khoá. Mạnh về lofi/chill/EDM/quốc tế, nhạc VN mỏng.
 *   - local  : file nhạc trong máy qua endpoint /music/library + /music/file
 *              (quét STATE_DIR/music + ~/Music). Offline hoàn toàn.
 *   - youtube: mở YouTube Music search trong tab mới - gì cũng có kể cả VN pop,
 *              free của chính chủ (quảng cáo YT), Joyce không tốn tí quota nào.
 *
 * API: play(query,opts) -> Promise<{ok,label,...}> ; pause/resume/stop/next/prev
 *      /volume(d) ; isActive() ; status() ; try_ làm ở joyce-music-cmd.js.
 *
 * Autoplay: nếu trình duyệt chặn phát tự động (chưa từng tương tác), thanh
 * player vẫn hiện và bấm ▶ là chạy - lệnh giọng sau đó không bị chặn nữa.
 * ========================================================================== */
(function (global) {
  'use strict';

  const AUDIUS = 'https://api.audius.co';
  const APP = 'joyce';
  const LS_VOL = 'joyce.music.vol';

  const S = {
    audio: null,          // trình phát nội bộ: Howl bọc API giống HTMLAudioElement
    queue: [],            // [{id,title,artist,src,source}]
    idx: -1,
    source: '',           // nguồn đang dùng: 'audius'|'local'
    lastQuery: '',        // nhớ query để "mở nhạc" trơn phát tiếp
    bar: null,
    builtAt: 0,
    duckTimer: null,
  };

  // ---- Duck nhạc khi Joyce nói ----
  // Joyce nói (TTS qua voice.js hoặc voice-live WebRTC) -> nhạc tụt còn DUCK_RATIO,
  // im hẳn DUCK_HOLD_MS mới trả lên. HOLD che khe hở giữa các câu TTS liên tiếp,
  // không thì nhạc sẽ bật/tắt giật cục theo từng câu.
  const DUCK_RATIO = 0.16;
  const DUCK_HOLD_MS = 1600;
  const DUCK_FADE_MS = 650;

  function speakingNow() {
    try { if (global.JoyceVoiceMain && global.JoyceVoiceMain.isSpeaking()) return true; } catch (e) {}
    try { if (global.JoyceVoiceLive && global.JoyceVoiceLive.isSpeaking()) return true; } catch (e) {}
    return false;
  }

  function startDuckWatch() {
    if (S.duckTimer) return;
    var quietSince = 0, ducked = false;
    S.duckTimer = setInterval(function () {
      var a = S.audio;
      if (!a || !a.src || a.paused) { ducked = false; quietSince = 0; return; }
      var now = Date.now();
      if (speakingNow()) {
        quietSince = 0;
        if (!ducked) { ducked = true; a._duckTo(DUCK_RATIO); }
      } else if (ducked) {
        if (!quietSince) quietSince = now;
        else if (now - quietSince > DUCK_HOLD_MS) { ducked = false; quietSince = 0; a._duckTo(1); }
      }
    }, 300);
  }

  function t(k, vars) { try { return global.t ? global.t(k, vars) : k; } catch (e) { return k; } }

  function el(tag, cls, txt) { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

  /* Trình phát nội bộ: Howl (Howler.js, vendor/howler.core.min.js) bọc API giống
     HTMLAudioElement để các chỗ gọi cũ không đổi. html5:true để stream URL Audius/
     local chứ không buffer cả file; điểm lợi thật là fade() mượt - nền cho duck
     nhạc khi Joyce nói (startDuckWatch). Mỗi src mới là một Howl mới, unload cái cũ. */
  function makePlayer() {
    var howl = null, url = '', vol = 0.8, duck = 1, ended = true;
    var L = {};
    function emit(ev) { (L[ev] || []).forEach(function (f) { try { f(); } catch (e) {} }); }
    function eff() { return Math.min(1, Math.max(0, vol * duck)); }
    function mount(u) {
      if (howl) { try { howl.unload(); } catch (e) {} howl = null; }
      url = u || ''; ended = !url;
      if (!url || !global.Howl) return;
      howl = new Howl({
        src: [url], html5: true, volume: eff(),
        onplay: function () { ended = false; emit('playing'); },
        onend: function () { ended = true; emit('ended'); },
        // onloaderror: track chết -> 'error' -> bài kế. KHÔNG emit 'error' từ
        // onplayerror: đó thường là autoplay bị chặn, Howler tự thử lại sau cử chỉ
        // đầu tiên của người dùng; emit 'error' ở đây sẽ quét sạch queue.
        onloaderror: function () { emit('error'); },
      });
    }
    return {
      get src() { return url; },
      set src(u) { mount(u); },
      get paused() { return !howl || !howl.playing(); },
      get ended() { return ended; },
      get volume() { return vol; },
      set volume(v) { vol = Math.min(1, Math.max(0, parseFloat(v) || 0)); if (howl) howl.volume(eff()); },
      play: function () { if (!howl) return Promise.reject(new Error('no src')); try { howl.play(); return Promise.resolve(); } catch (e) { return Promise.reject(e); } },
      pause: function () { if (howl) howl.pause(); },
      removeAttribute: function (k) { if (k === 'src') mount(''); },
      load: function () {},
      addEventListener: function (ev, f) { (L[ev] = L[ev] || []).push(f); },
      _duckTo: function (r) {
        duck = r;
        if (!howl) return;
        if (howl.playing()) howl.fade(howl.volume(), eff(), DUCK_FADE_MS);
        else howl.volume(eff());
      },
    };
  }

  function audio() {
    if (!S.audio) {
      S.audio = makePlayer();
      S.audio.addEventListener('ended', () => next(true));
      // Track lỗi -> bài kế; nhưng lỗi dồn >4 lần liền thì dừng, tránh vòng lặp
      // vô hạn khi cả queue đều chết (mất mạng, nguồn sập).
      S.audio.addEventListener('error', () => {
        if (!S.audio.src) return;
        S.errs = (S.errs || 0) + 1;
        if (S.errs > 4) { stop(); return; }
        next(true);
      });
      S.audio.addEventListener('playing', () => { S.errs = 0; paint(); });
      try { S.audio.volume = Math.min(1, Math.max(0, parseFloat(localStorage.getItem(LS_VOL)) || 0.8)); } catch (e) { S.audio.volume = 0.8; }
      startDuckWatch();
    }
    return S.audio;
  }

  /* ------------------------------ UI thanh phát ---------------------------- */

  function buildBar() {
    if (S.bar) return S.bar;
    const bar = el('div', 'jm-bar'); bar.id = 'joyce-music';
    bar.innerHTML =
      '<button class="jm-btn jm-prev" title="Prev" aria-label="Previous">⏮</button>' +
      '<button class="jm-btn jm-play" title="Play/Pause" aria-label="Play">▶</button>' +
      '<button class="jm-btn jm-next" title="Next" aria-label="Next">⏭</button>' +
      '<div class="jm-meta"><div class="jm-title">-</div><div class="jm-sub">-</div></div>' +
      '<span class="jm-src"></span>' +
      '<input class="jm-vol" type="range" min="0" max="100" value="80" aria-label="Volume">' +
      '<button class="jm-btn jm-close" title="Close" aria-label="Close">✕</button>';
    document.body.appendChild(bar);
    bar.querySelector('.jm-play').addEventListener('click', () => { const a = audio(); a.paused ? a.play().catch(() => {}) : a.pause(); });
    bar.querySelector('.jm-prev').addEventListener('click', () => prev());
    bar.querySelector('.jm-next').addEventListener('click', () => next(false));
    bar.querySelector('.jm-close').addEventListener('click', () => stop());
    const vol = bar.querySelector('.jm-vol');
    vol.addEventListener('input', () => { audio().volume = vol.value / 100; try { localStorage.setItem(LS_VOL, vol.value); } catch (e) {} });
    S.bar = bar;
    return bar;
  }

  function paint() {
    const tr = S.queue[S.idx];
    // Re-paint trễ (play() promise reject sau khi stop()) không được hồi sinh bar.
    if (!tr) { hideBar(); return; }
    const bar = buildBar(), a = audio();
    bar.classList.add('on');
    bar.querySelector('.jm-play').textContent = a.paused ? '▶' : '⏸';
    bar.querySelector('.jm-title').textContent = tr ? tr.title : '-';
    bar.querySelector('.jm-sub').textContent = tr ? (tr.artist || '') : '';
    bar.querySelector('.jm-src').textContent = S.source === 'local' ? t('music.srcLocal') : 'AUDIUS · FREE';
    bar.querySelector('.jm-vol').value = Math.round(a.volume * 100);
  }

  function hideBar() { if (S.bar) S.bar.classList.remove('on'); }

  /* ------------------------------ Phát thật -------------------------------- */

  function playAt(i) {
    const tr = S.queue[i];
    if (!tr) return false;
    S.idx = i;
    const a = audio();
    a.src = tr.src;
    paint();
    const p = a.play();
    if (p && p.catch) p.catch(() => { paint(); }); // autoplay bị chặn: bar vẫn mở, bấm ▶ chạy
    return true;
  }

  /** Phát nhạc theo query. source: 'auto'|'audius'|'local'|'youtube'.
   *  Trả {ok, action:'playing'|'opened'|'none', label} - label là câu phản hồi mờ. */
  async function play(query, opts) {
    opts = opts || {};
    const q = (query || '').trim();
    const src = opts.source || 'auto';
    if (q) S.lastQuery = q;

    // YouTube: mở tab - không cần queue, không quota, mọi bài đều có.
    if (src === 'youtube') {
      const url = 'https://music.youtube.com/search?q=' + encodeURIComponent(q || 'music');
      global.open(url, '_blank', 'noopener');
      return { ok: true, action: 'opened', label: t('music.youtube', { q: q || 'music' }) };
    }

    if (src === 'local' || src === 'auto') {
      const got = await searchLocal(q);
      if (got.length) { S.queue = got; S.source = 'local'; playAt(0); return { ok: true, action: 'playing', label: t('music.playing', { name: got[0].title }) }; }
      if (src === 'local') return { ok: false, action: 'none', label: t('music.noneLocal') };
    }

    // Audius (mặc định / khi local trống ở chế độ auto).
    if (src === 'audius' || src === 'auto') {
      const got = await searchAudius(q);
      if (got.length) { S.queue = got; S.source = 'audius'; playAt(0); return { ok: true, action: 'playing', label: t('music.playing', { name: got[0].title }) }; }
      // Trống cả hai: ngã YouTube - người dùng vẫn có nhạc ngay.
      if (!q || src === 'audius') return { ok: false, action: 'none', label: t('music.none') };
      const url = 'https://music.youtube.com/search?q=' + encodeURIComponent(q);
      global.open(url, '_blank', 'noopener');
      return { ok: true, action: 'opened', label: t('music.noneYt', { q }) };
    }
    return { ok: false, action: 'none', label: t('music.none') };
  }

  async function searchAudius(q) {
    try {
      const u = AUDIUS + '/v1/tracks/' + (q ? 'search?query=' + encodeURIComponent(q) + '&limit=12' : 'trending?limit=12') + '&app_name=' + APP + '&is_streamable=true';
      const d = await (await fetch(u)).json();
      return (d.data || []).filter(x => x.is_streamable !== false)
        .map(x => ({ id: x.id, title: x.title, artist: (x.user && x.user.name) || '', src: AUDIUS + '/v1/tracks/' + x.id + '/stream?app_name=' + APP, source: 'audius' }));
    } catch (e) { return []; }
  }

  async function searchLocal(q) {
    try {
      const d = await (await fetch('/music/library' + (q ? '?q=' + encodeURIComponent(q) : ''))).json();
      return (d.tracks || []).map(x => ({ id: x.id, title: x.title, artist: x.folder || '', src: '/music/file/' + x.id, source: 'local' }));
    } catch (e) { return []; }
  }

  /* ------------------------------- Điều khiển ------------------------------ */

  function isActive() { return !!(S.audio && S.audio.src && !S.audio.ended) || !!(S.bar && S.bar.classList.contains('on')); }

  function pause() { if (S.audio && !S.audio.paused) { S.audio.pause(); paint(); return true; } return false; }
  function resume() { if (S.audio && S.audio.src && S.audio.paused) { S.audio.play().catch(() => {}); paint(); return true; } return false; }
  function stop() { if (S.audio) { S.audio.pause(); S.audio.removeAttribute('src'); S.audio.load(); } S.queue = []; S.idx = -1; hideBar(); return true; }

  function next(autoEnded) {
    if (!S.queue.length) return false;
    const i = (S.idx + 1) % S.queue.length;
    playAt(i);
    return true;
  }
  function prev() {
    if (!S.queue.length) return false;
    const i = (S.idx - 1 + S.queue.length) % S.queue.length;
    playAt(i);
    return true;
  }
  function volume(delta) {
    const a = audio(); a.volume = Math.min(1, Math.max(0, a.volume + delta));
    try { localStorage.setItem(LS_VOL, String(Math.round(a.volume * 100))); } catch (e) {}
    paint();
    return Math.round(a.volume * 100);
  }
  function status() {
    const tr = S.queue[S.idx];
    return { active: isActive(), paused: !S.audio || S.audio.paused, title: tr && tr.title, source: S.source, count: S.queue.length };
  }

  global.JoyceMusic = { play, pause, resume, stop, next, prev, volume, isActive, status, _s: S };
})(typeof window !== 'undefined' ? window : globalThis);
