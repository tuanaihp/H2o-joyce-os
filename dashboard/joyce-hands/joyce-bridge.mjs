// Never change voice state in response to a gesture: host voice remains the source of truth.
export function connectJoyceHands(controller,avatar,{onQuietRequest=()=>{},onGesture=()=>{},onTracking=()=>{}}={}) {
  const tracking=({detail})=>{
    if(avatar.disposed)return;
    const p=detail.tracked?detail.pointer:null;
    avatar.setAttention?.(p?p.x*2-1:0,p?p.y*2-1:0);
    onTracking(detail);
  };
  const gesture=({detail})=>{
    if(avatar.disposed)return;
    if(detail.type==='pinch')avatar.pulse(detail.x,detail.y);
    if(detail.type==='palm')onQuietRequest({reason:'open-palm',source:'camera'});
    onGesture(detail);
  };
  const stop=()=>controller.stop();
  controller.addEventListener('tracking',tracking);
  controller.addEventListener('gesture',gesture);
  avatar.root.addEventListener('joyce-avatar:exit',stop);
  avatar.root.addEventListener('joyce-avatar:dispose',stop);
  return ()=>{
    controller.stop();controller.removeEventListener('tracking',tracking);
    controller.removeEventListener('gesture',gesture);
    avatar.root.removeEventListener('joyce-avatar:exit',stop);
    avatar.root.removeEventListener('joyce-avatar:dispose',stop);
  };
}
