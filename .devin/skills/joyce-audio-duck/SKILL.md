# Joyce Audio — Howler, ducking và quy ước giọng nói

Skill này áp dụng khi sửa playback âm thanh trong `dashboard/` (nhạc, TTS,
hiệu ứng), hoặc thêm nguồn âm thanh mới cần phối hợp với giọng nói của Joyce.

## Sơ đồ hiện tại

- `dashboard/vendor/howler.core.min.js` — Howler.js core (không spatial). Chỉ
  `joyce-music.js` dùng; nạp trước `joyce-music.js` trong `index.html`.
- `dashboard/joyce-music.js` — trình phát nhạc. Trình phát nội bộ là
  `makePlayer()`: một **Howl bọc API giống HTMLAudioElement** (`src`, `paused`,
  `ended`, `volume`, `play()→Promise`, `pause()`, `removeAttribute('src')`,
  `load()`, `addEventListener`, `_duckTo(r)`). Mọi chỗ gọi đều qua API này —
  KHÔNG tạo `new Audio()` hay `new Howl()` trực tiếp ngoài `makePlayer()`.
  `html5:true` để stream URL Audius/local không buffer cả file.
- `dashboard/voice.js` — TTS/recognition: `new Audio()` THUẦN, có hệ thống
  "nhá tiếng" riêng (`_dangNha`, `_nhaTiengThuXem`, `NHA_GAIN`) để phân biệt
  echo loa với người thật. **ĐỪNG chuyển voice.js sang Howler** — hệ nhá tiếng
  phụ thuộc `audio.volume` trực tiếp và kỹ thuật pause-probe mà Howler che mất.
- `dashboard/voice-live.js` — WebRTC live voice, `window.JoyceVoiceLive`.
- `dashboard/app.js` — `window.JoyceVoiceMain = voice` (instance `JoyceVoice`
  chính, expose để music đọc trạng thái).

## Hợp đồng ducking

`JoyceVoiceMain.isSpeaking()` đã gom đủ các đường phát tiếng: Audio element
(`isPlaying`), Web Speech (`synth.speaking`), và tôn trọng `_paused`. Live mode
thêm `JoyceVoiceLive.isSpeaking()`. Khi thêm nguồn tiếng MỚI của Joyce
(ví dụ kênh TTS thứ hai), phải cho nó vào `isSpeaking()` hoặc expose một cờ
tương đương — nếu không nhạc sẽ không duck.

Watcher trong `joyce-music.js` (`startDuckWatch`, 300ms):
- đang nói → `_duckTo(0.16)` (nhạc còn 16%, `Howl.fade` 650ms)
- im liên tục > `DUCK_HOLD_MS` (1600ms) → `_duckTo(1)`
- HOLD tồn tại để che khe hở GIỮA các câu TTS liên tiếp — bỏ nó thì nhạc
  bật/tắt giật cục theo từng câu. Đừng rút ngắn dưới ~1200ms.
- `_duckTo` chỉ nhân vào `eff()` = `vol × duck`; volume slider vẫn là volume
  nền của người dùng.

## Bẫy đã gặp

- `onplayerror` của Howler bắn khi autoplay bị chặn — **đừng** map nó vào sự
  kiện `error` (error = track chết → bài kế → quét sạch queue). Howler tự thử
  lại sau cử chỉ đầu tiên của người dùng.
- Mỗi `src` mới phải `unload()` Howl cũ rồi tạo Howl mới (xem `mount()`),
  nếu không stream cũ chạy tiếp ngầm.
- `play()` trả `Promise.resolve()` kể cả khi autoplay bị chặn; UI biết trạng
  thái qua `paused`, không qua promise — giữ nguyên quy ước này.

## Kiểm tra nhanh (node)

```js
// fake window/document/Howl/localStorage/fetch rồi require joyce-music.js;
// bật/tắt globalThis.JoyceVoiceMain.isSpeaking và đọc Howl._v để thấy fade.
// 0.8 -> 0.128 khi speaking -> 0.8 sau ~1.6s im.
```
