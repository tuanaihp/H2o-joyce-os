// Original gesture rules. MediaPipe supplies landmarks, not gesture certainty.
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export class GestureEngine {
  constructor(options = {}) {
    this.options = { mirror: true, pinchOn: .32, pinchOff: .5,
      pinchHoldMs: 160, palmHoldMs: 650, releaseMs: 200,
      pinchCooldownMs: 650, palmCooldownMs: 1800, maxGapMs: 300,
      // Vuốt tay: quãng ≥0.28 khung hình trong ≤450ms, trục chéo ≤0.22, cooldown 1200ms.
      swipeMinDelta: .28, swipeMaxSpanMs: 450, swipeMaxCross: .22, swipeCooldownMs: 1200,
      ...options };
    this.reset();
  }
  reset() {
    this.previousTime = null; this.pointer = null; this.pinch = false;
    this.pinchAt = null; this.pinchFired = false;
    this.palmAt = null; this.palmOrigin = null; this.palmFired = false; this.releaseAt = null;
    this.lastPinch = -Infinity; this.lastPalm = -Infinity;
    this.swipeTrail = []; this.lastSwipe = -Infinity;
  }
  update(landmarks, now, aspect = 4 / 3) {
    const empty = { tracked: false, pointer: null, gestures: [], pose: 'none' };
    if (!Number.isFinite(now) || !Array.isArray(landmarks) || landmarks.length !== 21 ||
      landmarks.some(p => !p || !Number.isFinite(p.x) || !Number.isFinite(p.y) ||
        p.x < -.1 || p.x > 1.1 || p.y < -.1 || p.y > 1.1)) {
      this.reset(); return empty;
    }
    if (this.previousTime !== null && (now - this.previousTime > this.options.maxGapMs || now <= this.previousTime)) this.reset();
    const dt = this.previousTime === null ? 80 : now - this.previousTime;
    this.previousTime = now;
    const o = this.options, lm = landmarks;
    const dist = (a,b) => Math.hypot((a.x-b.x)*aspect, a.y-b.y);
    const scale = dist(lm[0], lm[9]);
    if (scale < .035) { this.reset(); return empty; }
    const xy = p => ({ x: clamp(o.mirror ? 1-p.x : p.x), y: clamp(p.y) });
    const target = xy(lm[8]);
    const alpha = 1-Math.exp(-dt/90);
    this.pointer = this.pointer ? { x:this.pointer.x+(target.x-this.pointer.x)*alpha,
      y:this.pointer.y+(target.y-this.pointer.y)*alpha } : target;
    const ratio = dist(lm[4],lm[8])/scale, gestures = [];
    if (!this.pinch && ratio < o.pinchOn) { this.pinch=true; this.pinchAt=now; }
    if (this.pinch && ratio > o.pinchOff) { this.pinch=false; this.pinchAt=null; this.pinchFired=false; }
    if (this.pinch && !this.pinchFired && now-this.pinchAt >= o.pinchHoldMs && now-this.lastPinch >= o.pinchCooldownMs) {
      gestures.push({type:'pinch', ...xy({x:(lm[4].x+lm[8].x)/2,y:(lm[4].y+lm[8].y)/2})});
      this.pinchFired=true; this.lastPinch=now;
    }
    const open = !this.pinch && ratio>.65 && [[8,6],[12,10],[16,14],[20,18]]
      .every(([tip,pip]) => dist(lm[tip],lm[0]) > dist(lm[pip],lm[0])*1.12);
    if (open) {
      this.releaseAt=null;
      if (this.palmAt===null || dist(lm[0],this.palmOrigin)>scale*.25) {
        this.palmAt=now; this.palmOrigin={...lm[0]};
      }
      if (!this.palmFired && now-this.palmAt>=o.palmHoldMs && now-this.lastPalm>=o.palmCooldownMs) {
        gestures.push({type:'palm',...xy(lm[9])}); this.palmFired=true; this.lastPalm=now;
      }
    } else {
      this.palmAt=null; this.palmOrigin=null;
      if (this.releaseAt===null) this.releaseAt=now;
      if (now-this.releaseAt>=o.releaseMs) this.palmFired=false;
    }
    // Vuốt tay nhanh qua khung hình (trái/phải/xuống) -> mở/lật/đóng album.
    // Độc lập pose: vuốt giữa palm cũng tính (palm dwell đã tự reset khi tay lắc).
    this.swipeTrail.push({ x: this.pointer.x, y: this.pointer.y, t: now });
    while (this.swipeTrail.length && now - this.swipeTrail[0].t > o.swipeMaxSpanMs) this.swipeTrail.shift();
    if (this.swipeTrail.length >= 3 && now - this.lastSwipe >= o.swipeCooldownMs) {
      const a = this.swipeTrail[0], b = this.swipeTrail[this.swipeTrail.length - 1];
      const dx = b.x - a.x, dy = b.y - a.y;
      let dir = null;
      if (dx >= o.swipeMinDelta && Math.abs(dy) <= o.swipeMaxCross) dir = 'right';
      else if (dx <= -o.swipeMinDelta && Math.abs(dy) <= o.swipeMaxCross) dir = 'left';
      else if (dy >= o.swipeMinDelta && Math.abs(dx) <= o.swipeMaxCross) dir = 'down';
      else if (dy <= -o.swipeMinDelta && Math.abs(dx) <= o.swipeMaxCross) dir = 'up';
      if (dir) { gestures.push({ type: 'swipe', dir, x: b.x, y: b.y }); this.lastSwipe = now; this.swipeTrail = []; }
    }
    return {tracked:true, pointer:{...this.pointer}, gestures,
      pose:this.pinch?'pinch':open?'palm':'tracking', pinchRatio:ratio};
  }
}
