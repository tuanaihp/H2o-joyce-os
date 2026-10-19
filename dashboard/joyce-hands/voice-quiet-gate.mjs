// Adapts an open-palm request to the host's real voice lifecycle.
// The host remains authoritative for state and response/session identifiers.
export class VoiceQuietGate extends EventTarget {
  constructor({getSnapshot, interruptSpeech, onResult = () => {}}) {
    super();
    if (typeof getSnapshot !== 'function' || typeof interruptSpeech !== 'function') {
      throw new TypeError('VoiceQuietGate cần getSnapshot và interruptSpeech.');
    }
    this.getSnapshot = getSnapshot;
    this.interruptSpeech = interruptSpeech;
    this.onResult = onResult;
    this.pending = new Map();
    this.disposed = false;
  }
  report(result) {
    this.onResult(result);
    this.dispatchEvent(new CustomEvent('result', {detail: result}));
    return result;
  }
  async request(meta = {}) {
    if (this.disposed) return this.report({status:'ignored', reason:'disposed'});
    const snapshot = this.getSnapshot() || {};
    if (snapshot.state !== 'speaking') {
      return this.report({status:'ignored', reason:'not-speaking', state:snapshot.state || 'unknown'});
    }
    const responseId = String(snapshot.responseId || '');
    if (!responseId) return this.report({status:'ignored', reason:'missing-response-id'});
    if (this.pending.has(responseId)) return this.report({status:'ignored', reason:'already-pending', responseId});
    const request = {responseId, sessionId:snapshot.sessionId, reason:meta.reason || 'open-palm', source:meta.source || 'camera'};
    const token = Symbol(responseId);
    this.pending.set(responseId, token);
    this.report({status:'accepted', ...request});
    try {
      await this.interruptSpeech(request);
      if (this.disposed || this.pending.get(responseId) !== token) return {status:'ignored', reason:'stale-completion', responseId};
      const current = this.getSnapshot() || {};
      // A new response must never be marked interrupted by completion from the old one.
      const stale = current.responseId && String(current.responseId) !== responseId;
      return this.report({status:stale?'completed-stale':'completed', responseId});
    } catch (error) {
      if (this.disposed || this.pending.get(responseId) !== token) return {status:'ignored', reason:'stale-error', responseId};
      return this.report({status:'error', responseId, message:error?.message || String(error)});
    } finally {
      if (this.pending.get(responseId) === token) this.pending.delete(responseId);
    }
  }
  dispose() { this.disposed = true; this.pending.clear(); }
}

export function handAssetURLs(base = '/joyce-hands/') {
  const root = new URL(base, globalThis.location?.href || 'http://localhost/');
  const href = path => new URL(path, root).href;
  return {workerURL:href('hand-worker.js'), moduleURL:href('vendor/mediapipe/vision_bundle.mjs'),
    wasmURL:href('vendor/mediapipe/wasm'), modelURL:href('models/hand_landmarker.task')};
}
