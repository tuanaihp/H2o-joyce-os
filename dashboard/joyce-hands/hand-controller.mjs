import {GestureEngine} from './gesture-engine.mjs';
const here = new URL('.',import.meta.url);
const absolute = path => new URL(path,here).href;
export const HAND_EDGES = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],
  [13,17],[0,17],[17,18],[18,19],[19,20]];
export function cameraMessage(error) {
  const messages = {
    NotAllowedError:'Quyền camera bị từ chối hoặc bị chính sách trình duyệt chặn. Cho phép camera rồi bấm bật lại.',
    NotFoundError:'Không tìm thấy camera.', NotReadableError:'Không đọc được camera. Kiểm tra ứng dụng khác đang sử dụng camera.',
    SecurityError:'Camera bị chặn bởi chính sách bảo mật.', OverconstrainedError:'Camera không đáp ứng cấu hình yêu cầu.'
  };
  return messages[error?.name] || error?.message || 'Không thể bật điều khiển tay.';
}
export class JoyceHandController extends EventTarget {
  constructor(options) {
    super();
    if (!options?.video) throw new TypeError('Cần video element riêng cho camera.');
    this.options = {fps:15, width:320, height:240, mirror:true, initTimeoutMs:30000,
      workerURL:absolute('hand-worker.js'),moduleURL:absolute('vendor/mediapipe/vision_bundle.mjs'),
      wasmURL:absolute('vendor/mediapipe/wasm'),modelURL:absolute('models/hand_landmarker.task'),...options};
    this.video=options.video; this.overlay=options.overlay;
    this.video.muted=true; this.video.playsInline=true;
    this.engine=new GestureEngine({mirror:this.options.mirror,...options.gestures});
    this.state='off'; this.epoch=0; this.disposed=false;
    this.canvas=document.createElement('canvas');
    this.canvas.width=this.options.width; this.canvas.height=this.options.height;
    this.ctx=this.canvas.getContext('2d',{willReadFrequently:true});
    this.onHidden=()=>{if(document.hidden)this.stop('Đã tắt camera khi rời tab. Bấm bật để dùng lại.');};
    this.onPageHide=()=>this.stop();
    document.addEventListener('visibilitychange',this.onHidden);
    window.addEventListener('pagehide',this.onPageHide);
  }
  emit(type,detail) { this.dispatchEvent(new CustomEvent(type,{detail})); }
  setStatus(state,message) {this.state=state; this.emit('status',{state,message});}
  async start() {
    if(this.disposed)throw new Error('Controller đã dispose. Tạo instance mới.');
    if(this.state==='starting'||this.state==='active')return false;
    this.stop(); const epoch=++this.epoch;
    const current=()=>!this.disposed&&epoch===this.epoch;
    try {
      if(!globalThis.isSecureContext||!navigator.mediaDevices?.getUserMedia)
        throw new Error('Mở bằng HTTPS hoặc http://localhost; không mở file HTML bằng file://.');
      if(document.hidden)throw new Error('Quay lại tab này rồi bấm bật camera.');
      this.setStatus('starting','Đang nạp bộ nhận diện tại thiết bị…');
      const worker=new Worker(this.options.workerURL); this.worker=worker;
      await new Promise((resolve,reject)=>{
        const finish=(error)=>{clearTimeout(this.initTimer);this.cancelInit=null;error?reject(error):resolve();};
        this.cancelInit=()=>finish(new DOMException('Cancelled','AbortError'));
        this.initTimer=setTimeout(()=>finish(new Error('Nạp model quá lâu. Kiểm tra vendor/, models/ và chính sách CSP.')),this.options.initTimeoutMs);
        worker.onerror=()=>finish(new Error('Không khởi tạo được Worker/WASM. Kiểm tra file và CSP.'));
        worker.onmessage=({data})=>{
          if(data.type==='ready')finish();
          if(data.type==='error')finish(new Error(data.message));
        };
        worker.postMessage({type:'init',moduleURL:this.options.moduleURL,wasmURL:this.options.wasmURL,modelURL:this.options.modelURL});
      });
      if(!current())return false;
      this.setStatus('starting','Đang chờ anh cho phép camera — không yêu cầu microphone.');
      const stream=await navigator.mediaDevices.getUserMedia({
        audio:false,video:{facingMode:'user',width:{ideal:640},height:{ideal:480},frameRate:{ideal:24,max:30}}
      });
      if(!current()){stream.getTracks().forEach(t=>t.stop());return false;}
      this.stream=stream;
      stream.getTracks().forEach(track=>track.addEventListener('ended',()=>{
        if(current())this.stop('Camera đã ngắt. Bấm bật để kết nối lại.');
      },{once:true}));
      this.video.srcObject=stream;
      await this.video.play();
      if(!current())return false;
      worker.onerror=()=>{if(current())this.fail(new Error('Bộ nhận diện gặp lỗi. Camera đã tắt.'));};
      worker.onmessage=({data})=>{
        if(!current())return;
        if(data.type==='error'){this.fail(new Error(data.message));return;}
        if(data.type!=='result')return;
        this.busy=false;
        if(performance.now()-data.time>500){this.engine.reset();this.draw(null);this.emit('tracking',{tracked:false,pointer:null,pose:'slow',gestures:[],landmarks:null});return;}
        const result=this.engine.update(data.landmarks,data.time,this.canvas.width/this.canvas.height);
        this.draw(data.landmarks);
        this.emit('tracking',{...result,handCount:data.count,landmarks:data.landmarks});
        for(const gesture of result.gestures)this.emit('gesture',{...gesture,source:'camera',timestamp:data.time});
      };
      this.busy=false;this.lastFrame=-Infinity;this.lastVideo=-1;
      this.setStatus('active','Camera đang bật · xử lý tại thiết bị');
      const loop=now=>{
        if(!current()||this.state!=='active')return;
        this.raf=requestAnimationFrame(loop);
        if(this.busy&&now-this.sentAt>4000){this.fail(new Error('Nhận diện không phản hồi. Camera đã tắt; anh có thể bật lại.'));return;}
        if(this.busy||this.video.readyState<2||this.video.currentTime===this.lastVideo||now-this.lastFrame<1000/this.options.fps)return;
        try {
          // Preserve camera aspect ratio. Overlay and landmark distances use this same aspect.
          const h=Math.round(this.options.width*this.video.videoHeight/this.video.videoWidth);
          if(h>0&&this.canvas.height!==h)this.canvas.height=h;
          this.ctx.drawImage(this.video,0,0,this.canvas.width,this.canvas.height);
          const frame=this.ctx.getImageData(0,0,this.canvas.width,this.canvas.height);
          this.busy=true;this.sentAt=now;this.lastFrame=now;this.lastVideo=this.video.currentTime;
          worker.postMessage({type:'frame',buffer:frame.data.buffer,width:frame.width,height:frame.height,time:now},[frame.data.buffer]);
        }catch(error){this.fail(error);}
      };
      this.raf=requestAnimationFrame(loop);return true;
    } catch(error) {
      if(current()&&error.name!=='AbortError')this.fail(error);
      return false;
    }
  }
  draw(lm) {
    if(!this.overlay)return;
    const c=this.overlay; c.width=this.canvas.width;c.height=this.canvas.height;
    const ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);
    if(!lm)return;
    const x=p=>(this.options.mirror?1-p.x:p.x)*c.width,y=p=>p.y*c.height;
    ctx.strokeStyle='#19ddff';ctx.lineWidth=2;
    ctx.beginPath();for(const [a,b] of HAND_EDGES){ctx.moveTo(x(lm[a]),y(lm[a]));ctx.lineTo(x(lm[b]),y(lm[b]));}ctx.stroke();
    ctx.fillStyle='#ffb54d';for(const p of lm){ctx.beginPath();ctx.arc(x(p),y(p),2.5,0,Math.PI*2);ctx.fill();}
  }
  fail(error) {this.stop();this.setStatus('error',cameraMessage(error));this.emit('error',{message:cameraMessage(error)});}
  stop(message='Camera đã tắt.') {
    ++this.epoch;cancelAnimationFrame(this.raf);clearTimeout(this.initTimer);
    this.cancelInit?.();this.cancelInit=null;
    this.worker?.terminate();this.worker=null;
    this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;
    this.video.pause();this.video.srcObject=null;
    this.busy=false;this.engine.reset();this.draw(null);
    this.emit('tracking',{tracked:false,pointer:null,gestures:[],pose:'none'});
    this.setStatus('off',message);
  }
  dispose() {
    if(this.disposed)return;
    this.disposed=true;this.stop();
    document.removeEventListener('visibilitychange',this.onHidden);
    window.removeEventListener('pagehide',this.onPageHide);
  }
}
