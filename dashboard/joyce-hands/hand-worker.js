/* Classic Worker intentionally: MediaPipe's WASM loader can use importScripts.
   Dynamic import loads the pinned ESM bundle. No video/frame network upload. */
let detector;
self.onmessage = async ({data}) => {
  try {
    if (data.type === 'init') {
      const {FilesetResolver,HandLandmarker} = await import(data.moduleURL);
      const fileset = await FilesetResolver.forVisionTasks(data.wasmURL);
      detector = await HandLandmarker.createFromOptions(fileset, {
        baseOptions:{modelAssetPath:data.modelURL,delegate:'CPU'},
        runningMode:'VIDEO', numHands:2,
        minHandDetectionConfidence:.65, minHandPresenceConfidence:.65, minTrackingConfidence:.65
      });
      self.postMessage({type:'ready'});
    } else if (data.type === 'frame' && detector) {
      const frame = new ImageData(new Uint8ClampedArray(data.buffer),data.width,data.height);
      const result = detector.detectForVideo(frame,data.time);
      // Deliberately ignore multiple hands: do not jump control between people.
      self.postMessage({type:'result',time:data.time,count:result.landmarks.length,
        landmarks:result.landmarks.length===1?result.landmarks[0]:null});
    }
  } catch (error) {
    self.postMessage({type:'error',message:error?.message||String(error)});
  }
};
