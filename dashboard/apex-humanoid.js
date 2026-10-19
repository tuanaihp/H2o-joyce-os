/* Joyce Humanoid Reference Edition. Original renderer/UI code, no framework dependency.
 * Art plates: apex-humanoid.vercel.app; see ASSET_PROVENANCE.md before production use.
 * Hybrid 2.5D textured WebGL + Canvas particle field; NOT a rigged 3D human mesh.
 */
(function (global) {
  'use strict';
  const FILES = {
    backdrop:'backdrop-v1.webp',idle:'apex-idle-v1.webp',listening:'apex-listening-v1.webp',
    thinking:'apex-thinking-v1.webp',speaking:'apex-speaking-v1.webp',strong:'apex-speaking-strong-v1.webp',
    assembly25:'apex-assembly-25-v1.webp',assembly60:'apex-assembly-60-v1.webp'
  };
  const STATES = ['idle','listening','thinking','speaking','interrupting','reconnecting','error'];
  const clamp = (n,a=0,b=1) => Math.max(a,Math.min(b,Number.isFinite(n)?n:0));
  const smooth = n => { n=clamp(n); return n*n*(3-2*n); };
  function seeded(seed) { return () => ((seed=(seed*16807)%2147483647)-1)/2147483646; }
  function figureRect(w,h,aspect) {
    const height=Math.min(h*1.01,w*1.6),width=height*aspect;
    return {x:(w-width)/2,y:h-height,w:width,h:height};
  }
  const VERT = `attribute vec2 position;varying vec2 uv;
    void main(){uv=position*.5+.5;gl_Position=vec4(position,0.,1.);}`;
  const FRAG = `precision mediump float;
    uniform sampler2D plateA;uniform sampler2D plateB;
    uniform vec2 viewport;uniform vec4 rect;
    uniform float mixAmount;uniform float clock;uniform float level;uniform float reveal;
    uniform vec2 attention;uniform float reduceMotion;
    uniform float yaw;
    varying vec2 uv;
    void main(){
      vec2 px=vec2(uv.x,1.-uv.y)*viewport;
      vec2 q=(px-rect.xy)/rect.zw;
      if(q.x<0.||q.x>1.||q.y<0.||q.y>1.){gl_FragColor=vec4(0.);return;}
      float face=exp(-pow((q.y-.43)*5.,2.)-pow((q.x-.5)*4.,2.));
      float motion=1.-reduceMotion;
      // Quay đầu giả-3D (yaw): nén ngang theo cos góc (foreshorten) rồi cho
      // vùng mặt trong trượt nhiều hơn viền silhouette - đọc là đầu quay
      // trái/phải ~20 độ, đúng kiểu tham chiếu.
      float turn=clamp(yaw,-1.,1.)*motion;
      float inner=exp(-pow((q.y-.42)*4.5,2.)-pow((q.x-.5)*3.2,2.));
      q.x=.5+(q.x-.5)/max(.62,cos(turn*.42));
      q.x-=turn*(.012+.038*inner);
      // Nghiêng nhẹ theo con trỏ (attention) + gợn sóng khi nói.
      q.x-=(q.y-.5)*attention.x*.014*motion;
      q.x+=sin(q.y*40.-clock*2.)*.0015*level*face*motion;
      q+=attention*.004*face*motion;
      vec3 col=mix(texture2D(plateA,q).rgb,texture2D(plateB,q).rgb,mixAmount);
      float mouth=exp(-pow((q.y-.45)*12.,2.)-pow((q.x-.5)*9.,2.));
      // Lõi miệng đập có nhịp: biên độ rung theo clock + độ lớn tiếng.
      col+=vec3(1.,.28,.015)*mouth*level*(.06+.05*(.5+.5*sin(clock*7.+level*6.)));
      col*=reveal;
      gl_FragColor=vec4(col,1.);
    }`;

  class PlateRenderer {
    constructor(canvas) {
      this.canvas=canvas; this.gl=canvas.getContext('webgl',{alpha:true,antialias:false,premultipliedAlpha:false,powerPreference:'high-performance'});
      if(!this.gl) throw new Error('WebGL unavailable');
      const gl=this.gl;
      const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){const log=gl.getShaderInfoLog(s);gl.deleteShader(s);throw new Error(log);}return s;};
      const vs=shader(gl.VERTEX_SHADER,VERT),fs=shader(gl.FRAGMENT_SHADER,FRAG);
      this.program=gl.createProgram();gl.attachShader(this.program,vs);gl.attachShader(this.program,fs);gl.linkProgram(this.program);
      gl.deleteShader(vs);gl.deleteShader(fs);
      if(!gl.getProgramParameter(this.program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(this.program));
      gl.useProgram(this.program);this.buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
      const pos=gl.getAttribLocation(this.program,'position');gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
      this.u={};for(const n of ['plateA','plateB','viewport','rect','mixAmount','clock','level','reveal','attention','reduceMotion','yaw'])this.u[n]=gl.getUniformLocation(this.program,n);
      this.textures={};
    }
    load(images){const gl=this.gl;for(const [key,img] of Object.entries(images)){if(key==='backdrop')continue;const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);this.textures[key]=t;}}
    draw(a,b,mix,r,w,h,t,level,reveal,attention,reduced,yaw){const g=this.gl;if(g.isContextLost())return;
      g.viewport(0,0,this.canvas.width,this.canvas.height);g.useProgram(this.program);
      g.activeTexture(g.TEXTURE0);g.bindTexture(g.TEXTURE_2D,this.textures[a]||this.textures.idle);g.uniform1i(this.u.plateA,0);
      g.activeTexture(g.TEXTURE1);g.bindTexture(g.TEXTURE_2D,this.textures[b]||this.textures.idle);g.uniform1i(this.u.plateB,1);
      g.uniform2f(this.u.viewport,w,h);g.uniform4f(this.u.rect,r.x,r.y,r.w,r.h);g.uniform1f(this.u.mixAmount,mix);g.uniform1f(this.u.clock,t);
      g.uniform1f(this.u.level,level);g.uniform1f(this.u.reveal,reveal);g.uniform2f(this.u.attention,attention.x,attention.y);g.uniform1f(this.u.reduceMotion,reduced?1:0);g.uniform1f(this.u.yaw,yaw||0);g.drawArrays(g.TRIANGLES,0,6);
    }
    dispose(){const g=this.gl;Object.values(this.textures).forEach(t=>g.deleteTexture(t));g.deleteBuffer(this.buffer);g.deleteProgram(this.program);}
  }

  class JoyceHumanoid {
    constructor(host,options={}) {
      if(!host||!host.appendChild)throw new TypeError('A mount HTMLElement is required');
      this.host=host;this.options=options;this.state='idle';this.level=0;this.externalLevel=0;this.levelAt=-Infinity;
      this.running=false;this.disposed=false;this.paused=false;this.mic=null;this.micPending=false;this.micEpoch=0;this.sound=false;
      this.pointer={x:0,y:0};this.ripples=[];this.listeners=[];this.plate='idle';this.previous='idle';this.transitionAt=0;
      // Điều khiển tay qua camera sống ở joyce-hands/ (Worker MediaPipe, xử lý tại máy):
      // nút HAND CAM mở panel của kit qua options.onGestureRequest; kit gọi lại
      // setAttention()/pulse() ở đây qua connectJoyceHands(). Avatar không tự chạy detector.
      this.mediaQuery=global.matchMedia('(prefers-reduced-motion: reduce)');this.reduced=options.reducedMotion??this.mediaQuery.matches;
      this.root=document.createElement('section');this.root.className='jh';this.root.setAttribute('aria-label','Animated cyan and gold humanoid');
      this.root.innerHTML=`<img class="jh-backdrop" alt="" draggable="false"><canvas class="jh-gl" aria-hidden="true"></canvas><img class="jh-fallback" alt="Cyan and gold humanoid" hidden><canvas class="jh-particles" aria-hidden="true"></canvas>
        <div class="jh-top" hidden><button data-action="exit" aria-label="Exit humanoid view">EXIT</button><button data-action="train" aria-label="Train hand gestures">🎓 DẠY</button><button data-action="gesture" aria-pressed="false" aria-label="Toggle hand tracking camera">✋ HAND CAM</button></div>
        <div class="jh-status" role="status" aria-live="polite"></div>
        <nav class="jh-controls" aria-label="Avatar demo controls" hidden>${['idle','listening','thinking','speaking'].map(s=>`<button data-state="${s}" aria-pressed="${s==='idle'}">${s}</button>`).join('')}<button data-action="mic" aria-pressed="false">♩ MIC OFF</button><button data-action="replay">↻ REPLAY</button><button data-action="sound" aria-pressed="false">♪ SOUND OFF</button></nav>
        <aside class="jh-panel" aria-label="Gesture controls" hidden><strong>GESTURE · CAMERA</strong><p>Nút HAND CAM bật/tắt điều khiển tay - camera chạy ẩn, không hiện khung hình: đầu ngón trỏ lái sự chú ý của pho tượng, chụm ngón cái + trỏ tạo sóng năng lượng, xòe lòng bàn tay giữ yên yêu cầu Joyce ngừng nói.</p><p>Nhận diện chạy tại máy trong một Worker riêng (MediaPipe), camera chỉ bật khi anh bấm nút, không gửi hình ảnh đi đâu.</p><button data-action="close-gesture">Đã hiểu</button></aside>
        <div class="jh-notice" role="status" hidden></div>
        <div class="jh-entry"><div><h1>JOYCE</h1><p>a figure of light that assembles itself</p><button data-action="enter" disabled>LOADING</button><small class="jh-load-text">Đang nạp tài nguyên nhân vật…</small></div></div>`;
      host.appendChild(this.root);this.$=s=>this.root.querySelector(s);this.bg=this.$('.jh-backdrop');this.glCanvas=this.$('.jh-gl');this.particleCanvas=this.$('.jh-particles');this.ctx=this.particleCanvas.getContext('2d');this.status=this.$('.jh-status');this.fallback=this.$('.jh-fallback');
      this.listen(this.root,'click',e=>{const b=e.target.closest('button');if(b){if(b.dataset.state)this.setState(b.dataset.state);else this.action(b.dataset.action);return;}if(this.running){const r=this.root.getBoundingClientRect();this.pulse((e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height);}});
      this.listen(this.root,'pointermove',e=>{const r=this.root.getBoundingClientRect();this.pointer={x:clamp((e.clientX-r.left)/r.width)*2-1,y:clamp((e.clientY-r.top)/r.height)*2-1};});
      this.listen(this.root,'pointerleave',()=>this.pointer={x:0,y:0});
      this.listen(this.root,'keydown',e=>{if(e.key==='Escape'){if(!this.$('.jh-panel').hidden)this.action('close-gesture');else this.exit();}});
      this.listen(document,'visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(this.raf);this.lastFrame=0;this.audio?.suspend();}else if(this.running&&!this.paused){if(this.sound)this.audio?.resume();this.raf=requestAnimationFrame(t=>this.frame(t));}});
      this.listen(this.glCanvas,'webglcontextlost',e=>{e.preventDefault();this.useFallback();this.notice('WebGL tạm ngắt — đang dùng chế độ ảnh dự phòng.');});
      this.listen(this.glCanvas,'webglcontextrestored',()=>{try{this.renderer?.dispose();this.renderer=new PlateRenderer(this.glCanvas);this.renderer.load(this.images);this.glCanvas.hidden=false;this.fallback.hidden=true;}catch(err){this.report(err);this.useFallback();}});
      this.listen(this.mediaQuery,'change',e=>{if(options.reducedMotion===undefined)this.reduced=e.matches;});
      this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(host);this.resize();
      this.ready=this.load();
    }
    listen(target,event,fn){target.addEventListener(event,fn);this.listeners.push(()=>target.removeEventListener(event,fn));}
    report(error){this.options.onError?.(error);this.root.dispatchEvent(new CustomEvent('joyce-avatar:error',{detail:{message:error.message}}));}
    async load(){try{
      const pairs=await Promise.all(Object.entries(FILES).map(([key,file])=>new Promise((resolve,reject)=>{const img=new Image();img.crossOrigin='anonymous';img.onload=()=>resolve([key,img]);img.onerror=()=>reject(new Error('Không tải được '+file));img.src=this.options.assets?.[key]||(this.options.assetsBase||'./assets/')+file;})));
      if(this.disposed)return;this.images=Object.fromEntries(pairs);this.bg.src=this.images.backdrop.src;this.fallback.src=this.images.idle.src;
      this.aspect=this.images.idle.naturalWidth/this.images.idle.naturalHeight;
      try{this.renderer=new PlateRenderer(this.glCanvas);this.renderer.load(this.images);}catch(err){this.report(err);this.useFallback();}
      this.sampleParticles();this.loaded=true;this.$('[data-action=enter]').disabled=false;this.$('[data-action=enter]').textContent='ENTER';
      this.$('.jh-load-text').textContent='Reference edition · âm thanh và mic chỉ bật khi anh chọn';
      if(this.options.autoStart)this.enter();
    }catch(err){if(this.disposed)return;this.report(err);this.$('.jh-load-text').textContent=err.message+' — mở bản standalone.html hoặc kiểm tra assets/.';this.$('[data-action=enter]').textContent='LOAD FAILED';}}
    sampleParticles(){const c=document.createElement('canvas');c.width=340;c.height=Math.round(340/this.aspect);const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(this.images.idle,0,0,c.width,c.height);
      try{const d=ctx.getImageData(0,0,c.width,c.height).data,random=seeded(48671),particles=[];
        for(let y=0;y<c.height;y+=2)for(let x=0;x<c.width;x+=2){const i=(y*c.width+x)*4,l=Math.max(d[i],d[i+1],d[i+2]);if(l<52||random()>.48)continue;particles.push({u:x/c.width,v:y/c.height,color:`rgb(${d[i]},${d[i+1]},${d[i+2]})`,phase:random()*Math.PI*2,scatter:random(),size:.4+random()*1.1});}
        this.particles=particles;
      }catch(err){this.particles=[];this.report(err);}
    }
    resize(){const r=this.host.getBoundingClientRect();this.w=Math.max(1,r.width);this.h=Math.max(1,r.height);const dpr=Math.min(global.devicePixelRatio||1,this.options.maxDpr||1.5);this.dpr=dpr;
      for(const c of [this.glCanvas,this.particleCanvas]){c.width=Math.round(this.w*dpr);c.height=Math.round(this.h*dpr);}
      this.ctx.setTransform(dpr,0,0,dpr,0,0);
    }
    useFallback(){this.glCanvas.hidden=true;this.fallback.hidden=false;}
    action(a){if(a==='enter')this.enter();if(a==='exit')this.exit();if(a==='replay')this.replay();if(a==='mic')this.toggleMic();if(a==='sound')this.setSound(!this.sound);
      if(a==='gesture'){this.options.onGestureRequest?.();return;}
      if(a==='train'){this.options.onTrainRequest?.();return;}
      if(a==='close-gesture'){this.$('.jh-panel').hidden=true;this.$('[data-action=gesture]').focus();}}
    enter(){if(!this.loaded||this.disposed)return;this.running=true;this.paused=false;this.$('.jh-entry').hidden=true;this.$('.jh-top').hidden=false;this.$('.jh-controls').hidden=this.options.controls===false;this.$('[data-action=exit]').focus();this.replay();}
    exit(){this.running=false;cancelAnimationFrame(this.raf);this.stopMic();this.setSound(false);this.$('.jh-entry').hidden=false;this.$('.jh-top').hidden=true;this.$('.jh-controls').hidden=true;this.$('.jh-panel').hidden=true;this.status.textContent='';this.$('[data-action=enter]').focus();this.options.onExit?.();this.root.dispatchEvent(new CustomEvent('joyce-avatar:exit'));}
    replay(){if(!this.running||this.disposed)return;cancelAnimationFrame(this.raf);this.startedAt=performance.now();this.lastFrame=0;this.ripples=[];this.ignited=false;this.raf=requestAnimationFrame(t=>this.frame(t));if(this.sound)this.tone(48,1.4);}
    setState(state){if(!STATES.includes(state))throw new RangeError('Unknown avatar state: '+state);if(this.disposed)return;this.state=state;
      for(const b of this.root.querySelectorAll('[data-state]'))b.setAttribute('aria-pressed',String(b.dataset.state===state));
      const plate=['idle','listening','thinking','speaking'].includes(state)?state:'idle';this.selectPlate(plate,performance.now());
      this.options.onStateChange?.(state);this.root.dispatchEvent(new CustomEvent('joyce-avatar:state',{detail:{state}}));}
    selectPlate(plate,now){if(plate===this.plate)return;this.previous=this.plate;this.plate=plate;this.transitionAt=now;}
    setLevel(level){this.externalLevel=clamp(Number(level));this.levelAt=performance.now();}
    // Kit joyce-hands gọi: lái sự chú ý (đầu quay, parallax hạt) theo đầu ngón trỏ.
    // Cùng kênh pointer với chuột: nguồn nào emit sau thắng, -1..1 -> giữa là trung tâm.
    setAttention(x=0,y=0){this.pointer={x:clamp(x,-1,1),y:clamp(y,-1,1)};}
    pulse(x=.5,y=.45){this.ripples.push({x:clamp(x),y:clamp(y),at:performance.now()});if(this.ripples.length>5)this.ripples.shift();if(this.sound)this.tone(180,.24);}
    setSound(enabled){this.sound=!!enabled&&!this.disposed;const b=this.$('[data-action=sound]');b.textContent=this.sound?'♪ SOUND ON':'♪ SOUND OFF';b.setAttribute('aria-pressed',String(this.sound));if(this.sound){this.tone(100,.5);}else{this.audio?.suspend();}}
    tone(freq,duration){try{const AC=global.AudioContext||global.webkitAudioContext;if(!AC)return;this.audio=this.audio||new AC();this.audio.resume();const now=this.audio.currentTime,o=this.audio.createOscillator(),g=this.audio.createGain();o.type='sine';o.frequency.setValueAtTime(freq,now);o.frequency.exponentialRampToValueAtTime(freq*.55,now+duration);g.gain.setValueAtTime(.0001,now);g.gain.exponentialRampToValueAtTime(.045,now+.03);g.gain.exponentialRampToValueAtTime(.0001,now+duration);o.connect(g);g.connect(this.audio.destination);o.start();o.stop(now+duration+.02);o.onended=()=>{o.disconnect();g.disconnect();};}catch(err){this.report(err);}}
    async toggleMic(){if(this.mic){this.stopMic();return;}if(this.micPending)return;
      if(!navigator.mediaDevices?.getUserMedia){this.notice('Mic cần HTTPS hoặc localhost. Các chế độ demo vẫn dùng được.');return;}
      this.micPending=true;const epoch=++this.micEpoch;const b=this.$('[data-action=mic]');b.disabled=true;let stream,context;
      try{stream=await navigator.mediaDevices.getUserMedia({audio:true});if(this.disposed||!this.running||epoch!==this.micEpoch){stream.getTracks().forEach(t=>t.stop());return;}
        const AC=global.AudioContext||global.webkitAudioContext;context=new AC();await context.resume();const source=context.createMediaStreamSource(stream),analyser=context.createAnalyser();analyser.fftSize=512;source.connect(analyser);
        this.mic={stream,context,source,analyser,data:new Uint8Array(analyser.fftSize)};b.textContent='♩ MIC ON';b.setAttribute('aria-pressed','true');this.setState('listening');this.notice('Mic chỉ đo âm lượng tại thiết bị; không ghi hoặc gửi âm thanh.');
      }catch(err){stream?.getTracks().forEach(t=>t.stop());context?.close();this.notice('Không bật được mic: '+err.message);this.report(err);}finally{this.micPending=false;if(!this.disposed)b.disabled=false;}}
    stopMic(){this.micEpoch++;if(this.mic){this.mic.stream.getTracks().forEach(t=>t.stop());this.mic.source.disconnect();this.mic.context.close();this.mic=null;}if(!this.disposed){const b=this.$('[data-action=mic]');b.textContent='♩ MIC OFF';b.setAttribute('aria-pressed','false');}}
    notice(message){if(this.disposed)return;const n=this.$('.jh-notice');n.textContent=message;n.hidden=false;clearTimeout(this.noticeTimer);this.noticeTimer=setTimeout(()=>n.hidden=true,6000);}
    // ---------- Camera tay: do /static/joyce-hands/ điều phối (Worker + GestureEngine).
    // Avatar chỉ giữ nút mở panel + hook setAttention/pulse ở trên; không detect ở đây.
    frame(now){if(this.disposed||!this.running||this.paused||document.hidden)return;this.raf=requestAnimationFrame(t=>this.frame(t));
      if(this.lastFrame&&now-this.lastFrame<1000/(this.options.fps||40))return;this.lastFrame=now;
      const t=now/1000,elapsed=(now-this.startedAt)/1000,p=this.reduced?1:clamp(elapsed/(this.options.assemblyDuration||6));
      let target=0;if(this.mic){const {analyser,data}=this.mic;analyser.getByteTimeDomainData(data);let sum=0;for(const x of data)sum+=((x-128)/128)**2;target=clamp(Math.sqrt(sum/data.length)*6);}else if(now-this.levelAt<1200)target=this.externalLevel;
      else if(this.options.demo!==false&&this.state==='speaking')target=.2+.52*Math.abs(Math.sin(t*4)*Math.sin(t*7.1));else if(this.state==='thinking')target=.12+.08*Math.sin(t*2);
      this.level+=(target-this.level)*.16;
      if(this.state==='speaking'){const next=this.level>.58?'strong':this.level<.39?'speaking':this.plate;this.selectPlate(next,now);}
      const r=figureRect(this.w,this.h,this.aspect||.926);const plateReveal=smooth((p-.5)/.5),backgroundReveal=smooth((p-.82)/.18);
      this.bg.style.opacity=String(backgroundReveal*(.92+this.level*.08));
      const mix=smooth((now-this.transitionAt)/320);
      // Đầu quay trái/phải: bám con trỏ/bàn tay (pointer.x -1..1) cộng đung đưa
      // nhẹ lúc idle; nội suy mềm để không giật.
      const targetYaw=clamp(this.pointer.x*.6+Math.sin(t*.42)*.09,-1,1);
      this.yaw=(this.yaw||0)+(targetYaw-(this.yaw||0))*.085;
      // Nhịp nói: mỗi lần level vọt qua ngưỡng -> vòng sóng phát từ miệng.
      if(this.state==='speaking'&&this.level>.48&&now-(this._beatAt||0)>650){this._beatAt=now;this.pulse(.5,(r.y+r.h*.44)/this.h);}
      if(this.renderer&&!this.glCanvas.hidden)this.renderer.draw(this.previous,this.plate,mix,r,this.w,this.h,t,this.level,plateReveal,this.pointer,this.reduced,this.yaw);
      else{this.fallback.src=this.images[this.plate].src;this.fallback.style.opacity=String(plateReveal);}
      const message=p<1?'ASSEMBLING... '+Math.round(p*100)+'%':'STATUS: '+this.state.toUpperCase();if(message!==this.status.textContent)this.status.textContent=message;
      if(p===1&&!this.ignited){this.ignited=true;this.pulse(.5,(r.y+r.h*.44)/this.h);}
      this.drawParticles(t,p,r,now);
    }
    drawParticles(t,p,r,now){const c=this.ctx;c.clearRect(0,0,this.w,this.h);if(this.reduced)return;c.globalCompositeOperation='lighter';
      const settling=smooth(p),unformed=1-settling;
      // Xoay cùng góc yaw với plate: nén ngang + vùng mặt trượt nhiều hơn viền,
      // để lớp hạt không phản bội cảm giác đầu quay.
      const turn=clamp(this.yaw||0,-1,1),fw=Math.max(.62,Math.cos(turn*.42));
      const speakBoost=this.state==='speaking'?1+this.level*.9:1;
      for(const pt of this.particles||[]){const delay=pt.v*.14;const convergence=smooth(clamp((p-delay)/.86));const spread=1-convergence;
        const dx=pt.u-.5,inner=Math.exp(-Math.pow((pt.v-.42)*4.5,2)-Math.pow(dx*3.2,2));
        const tx=r.x+(.5+dx/fw-turn*(.012+.038*inner))*r.w,ty=r.y+pt.v*r.h;
        const angle=pt.phase+t*(.35+pt.scatter*.2),radius=spread*(60+pt.scatter*this.w*.42);
        const x=tx+Math.cos(angle)*radius+this.pointer.x*pt.scatter*3;
        const y=ty+Math.sin(angle)*radius+spread*this.h*.15;
        const shimmer=(.35+.65*(.5+.5*Math.sin(t*(.8+pt.scatter)+pt.phase)))*speakBoost;
        c.globalAlpha=clamp((.18+unformed*.7)*shimmer*(p<.05?p/.05:1));c.fillStyle=pt.color;c.fillRect(x,y,pt.size,pt.size);
      }
      c.globalAlpha=1;
      for(const q of this.ripples){const age=(now-q.at)/1000;if(age<0||age>2)continue;const radius=age*this.w*.5;
        c.strokeStyle=`rgba(25,221,255,${(1-age/2)*.16})`;c.lineWidth=1;c.beginPath();c.ellipse(q.x*this.w,q.y*this.h,Math.max(.1,radius),Math.max(.1,radius*.7),0,0,Math.PI*2);c.stroke();}
      this.ripples=this.ripples.filter(q=>now-q.at<2000);
      if(p<1){const gx=r.x+r.w*.5,gy=r.y+r.h*.94,g=c.createRadialGradient(gx,gy,0,gx,gy,55);g.addColorStop(0,'rgba(160,245,255,'+(Math.sin(p*Math.PI)*.7)+')');g.addColorStop(1,'rgba(0,190,255,0)');c.fillStyle=g;c.fillRect(gx-55,gy-55,110,110);}
      c.globalCompositeOperation='source-over';
    }
    pause(){this.paused=true;cancelAnimationFrame(this.raf);this.audio?.suspend();}
    resume(){if(this.disposed||!this.running||!this.paused)return;this.paused=false;this.lastFrame=0;if(this.sound)this.audio?.resume();this.raf=requestAnimationFrame(t=>this.frame(t));}
    dispose(){if(this.disposed)return;this.stopMic();this.disposed=true;this.running=false;cancelAnimationFrame(this.raf);clearTimeout(this.noticeTimer);this.observer.disconnect();this.listeners.forEach(off=>off());this.root.dispatchEvent(new CustomEvent('joyce-avatar:dispose'));this.renderer?.dispose();this.audio?.close();this.root.remove();}
  }
  global.JoyceHumanoidApex=JoyceHumanoid;
  if(typeof module!=='undefined'&&module.exports)module.exports={JoyceHumanoid,clamp,smooth,seeded,figureRect,STATES,FILES,VERT,FRAG};
})(typeof window!=='undefined'?window:globalThis);
