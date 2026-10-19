import {JoyceHandController} from './hand-controller.mjs';
let sequence=0;
export function mountHandPanel(host,options={}) {
  const id='jh-camera-title-'+(++sequence), panel=document.createElement('section');
  panel.className='joyce-hands';panel.hidden=true;
  panel.setAttribute('role','region');panel.setAttribute('aria-labelledby',id);
  panel.innerHTML=`<header><div><small>JOYCE / VISION INPUT</small><h2 id="${id}">Điều khiển bằng tay</h2></div><button type="button" data-close aria-label="Đóng và tắt camera">×</button></header>
    <p class="jh-privacy">Hình ảnh chỉ xử lý trên thiết bị. Không ghi hình, không tải lên server, không bật mic.</p>
    <div class="jh-camera"><video muted playsinline aria-label="Hình camera xem trước"></video><canvas aria-hidden="true"></canvas><span class="jh-camera-badge">CAMERA OFF</span></div>
    <p class="jh-camera-status" role="status" aria-live="polite">Camera chưa bật.</p>
    <div class="jh-camera-actions"><button type="button" data-start>Bật camera</button><button type="button" data-stop disabled>Tắt camera</button></div>
    <dl><div><dt>Di chuyển tay</dt><dd>Avatar hướng sự chú ý theo đầu ngón trỏ</dd></div><div><dt>Chụm ngón cái + trỏ</dt><dd>Giữ khoảng 0,2 giây để phát sóng năng lượng</dd></div><div><dt>Xòe tay, giữ yên</dt><dd>Giữ khoảng 0,7 giây để yêu cầu ngừng nói</dd></div></dl>
    <p class="jh-camera-hint">Dùng một bàn tay, hướng lòng bàn tay về camera, đủ sáng. Thả cử chỉ trước khi làm lại.</p><output class="jh-detected">Chưa theo dõi</output>`;
  host.appendChild(panel);
  const $=s=>panel.querySelector(s),video=$('video');
  video.style.transform=options.mirror===false?'none':'scaleX(-1)';
  const controller=new JoyceHandController({...options,video,overlay:$('canvas')});
  let returnFocus;
  const onStatus=({detail})=>{
    $('.jh-camera-status').textContent=detail.message;
    $('[data-start]').disabled=detail.state==='starting'||detail.state==='active';
    $('[data-stop]').disabled=!['starting','active'].includes(detail.state);
    $('.jh-camera-badge').textContent=detail.state==='active'?'● CAMERA ON':detail.state==='starting'?'ĐANG BẬT…':'CAMERA OFF';
    panel.dataset.camera=detail.state;
  };
  const onTracking=({detail})=>{
    $('.jh-detected').textContent=detail.handCount>1?'Chỉ đưa một bàn tay vào khung hình':
      ({pinch:'Đang chụm ngón',palm:'Đang xòe tay',tracking:'Đang theo tay',slow:'Thiết bị xử lý chậm'}[detail.pose]||'Chưa thấy bàn tay');
  };
  controller.addEventListener('status',onStatus);controller.addEventListener('tracking',onTracking);
  const open=()=>{returnFocus=document.activeElement;panel.hidden=false;$('[data-start]').focus();};
  const close=()=>{controller.stop();panel.hidden=true;if(returnFocus?.isConnected)returnFocus.focus();};
  const click=e=>{if(e.target.closest('[data-start]'))void controller.start();if(e.target.closest('[data-stop]'))controller.stop();if(e.target.closest('[data-close]'))close();};
  const key=e=>{if(e.key==='Escape'){e.stopPropagation();close();}};
  panel.addEventListener('click',click);panel.addEventListener('keydown',key);
  return {controller,open,close,element:panel,dispose(){controller.dispose();controller.removeEventListener('status',onStatus);controller.removeEventListener('tracking',onTracking);panel.removeEventListener('click',click);panel.removeEventListener('keydown',key);panel.remove();}};
}
