// Original gesture rules. MediaPipe supplies landmarks, not gesture certainty.
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
// Đặc trưng dáng tay: 5 điểm "độ duỗi" [cái, trỏ, giữa, nhẫn, út] chuẩn hoá 0..1 theo
// kích thước lòng bàn tay (wrist->middle MCP) nên xa/gần camera không lệch. Dùng chung
// cho cả lúc luyện (trainer) lẫn lúc nhận diện (engine) — một công thức duy nhất.
export function fingerVector(lm, aspect = 4 / 3) {
  const dist = (a, b) => Math.hypot((a.x - b.x) * aspect, a.y - b.y);
  const w = lm[0], scale = dist(w, lm[9]) || 1e-6;
  const ext = (tip, mcp) => clamp((dist(lm[tip], w) / dist(lm[mcp], w) - 1) / 1.2);
  return [clamp(dist(lm[4], lm[5]) / scale / 1.4), ext(8, 5), ext(12, 9), ext(16, 13), ext(20, 17)];
}
export class GestureEngine {
  constructor(options = {}) {
    this.options = { mirror: true, pinchOn: .32, pinchOff: .5,
      pinchHoldMs: 160, palmHoldMs: 650, releaseMs: 200,
      pinchCooldownMs: 650, palmCooldownMs: 1800, maxGapMs: 300,
      // Vuốt tay: quãng ≥0.28 khung hình trong ≤450ms, trục chéo ≤0.22, cooldown 1200ms.
      swipeMinDelta: .28, swipeMaxSpanMs: 450, swipeMaxCross: .22, swipeCooldownMs: 1200,
      // Cử chỉ tự luyện: giữ dáng yên ≥450ms mới bắn, cooldown 1500ms, ngón duỗi của palm ≥1.12.
      poseHoldMs: 450, poseCooldownMs: 1500, palmExtMin: 1.12,
      ...options };
    this.profile = { custom: [], calib: {} };
    this.palmSuppressed = false;
    this.reset();
  }
  // Hồ sơ tay từ bảng huấn luyện: calib ghi đè ngưỡng mặc định; custom là các dáng tay
  // tự luyện gắn hành động. Nếu trong custom có dáng "giống xòe tay" (>=4 ngón duỗi),
  // nó THAY thế palm mặc định - palm gốc tắt hẳn để khỏi bắn đôi.
  setProfile(profile) {
    const p = profile && typeof profile === 'object' ? profile : {};
    this.profile = { custom: Array.isArray(p.custom) ? p.custom : [], calib: p.calib || {} };
    const c = this.profile.calib, o = this.options;
    for (const k of ['pinchOn', 'pinchOff', 'swipeMinDelta', 'swipeMaxSpanMs', 'palmExtMin', 'poseHoldMs'])
      if (Number.isFinite(c[k])) o[k] = c[k];
    this.palmSuppressed = this.profile.custom.some(g =>
      Array.isArray(g.vec) && g.vec.slice(1).filter(v => v > .55).length >= 4);
  }
  reset() {
    this.previousTime = null; this.pointer = null; this.pinch = false;
    this.pinchAt = null; this.pinchFired = false;
    this.palmAt = null; this.palmOrigin = null; this.palmFired = false; this.releaseAt = null;
    this.lastPinch = -Infinity; this.lastPalm = -Infinity;
    this.swipeTrail = []; this.lastSwipe = -Infinity;
    this.poseId = null; this.poseAt = null; this.poseOrigin = null;
    this.poseFired = false; this.poseReleaseAt = null; this.lastPose = -Infinity;
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
      .every(([tip,pip]) => dist(lm[tip],lm[0]) > dist(lm[pip],lm[0])*o.palmExtMin);
    // ── Cử chỉ TỰ LUYỆN: so đặc trưng 5 ngón với mẫu đã chốt (sai lệch theo tol từng
    // ngón). Phải giữ dáng yên (wrist không trôi quá 1/4 lòng bàn tay) đủ poseHoldMs
    // mới bắn - tay đang di chuyển/vuốt không bao giờ kích hoạt nhầm.
    let matched = null;
    if (this.profile.custom.length) {
      const fv = fingerVector(lm, aspect);
      let best = null, bestScore = Infinity;
      for (const g of this.profile.custom) {
        if (!Array.isArray(g.vec) || g.vec.length !== 5) continue;
        const tol = Array.isArray(g.tol) && g.tol.length === 5 ? g.tol : null;
        const score = Math.max(...fv.map((v, i) =>
          Math.abs(v - g.vec[i]) / Math.max(tol ? tol[i] : .16, .04)));
        if (score < bestScore) { bestScore = score; best = g; }
      }
      if (best && bestScore < 1) matched = best;
    }
    if (matched) {
      const moved = this.poseOrigin && dist(lm[0], this.poseOrigin) > scale * .25;
      if (this.poseId !== matched.id || moved) {
        this.poseId = matched.id; this.poseAt = now; this.poseOrigin = { ...lm[0] };
      }
      this.poseReleaseAt = null;
      if (!this.poseFired && now - this.poseAt >= o.poseHoldMs && now - this.lastPose >= o.poseCooldownMs) {
        gestures.push({ type: 'custom', id: matched.id, action: matched.action, label: matched.label, ...xy(lm[9]) });
        this.poseFired = true; this.lastPose = now;
      }
    } else {
      this.poseId = null; this.poseAt = null; this.poseOrigin = null;
      if (this.poseReleaseAt === null) this.poseReleaseAt = now;
      if (now - this.poseReleaseAt >= o.releaseMs) this.poseFired = false;
    }
    if (open && !this.palmSuppressed) {
      this.releaseAt=null;
      if (this.palmAt===null || dist(lm[0],this.palmOrigin)>scale*.25) {
        this.palmAt=now; this.palmOrigin={...lm[0]};
      }
      if (!this.palmFired && now-this.palmAt>=o.palmHoldMs && now-this.lastPalm>=o.palmCooldownMs) {
        gestures.push({type:'palm',...xy(lm[9])}); this.palmFired=true; this.lastPalm=now;
      }
    } else if (!open) {
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
      pose:this.pinch?'pinch':matched?'custom':open?'palm':'tracking', pinchRatio:ratio};
  }
}
