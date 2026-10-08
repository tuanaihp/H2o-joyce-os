// ============================================
// H2O ALIEN INTELLIGENCE PLANET - renderer mới cho lớp "Lõi nước" của khoang não.
// Cờ: localStorage "joyce_alien_intelligence_planet_v1" ("0" = ép bản Canvas 2D nhẹ, không
// shader). Quả cầu 2D thời trước trong hud.js đã gỡ theo yêu cầu chủ (2026-10-05).
//
// Thiên thể (role trong ProjectHealth, hud.js gán): "sun" = H2O Legacy, quầng vàng, là
// NGUỒN SÁNG của tinh cầu (hướng chiếu sáng trong shader lấy từ vị trí mặt trời);
// "moon" = một dự án, pha trăng tính theo ngày thật (moonPhase). Đang gọi (setInCall)
// thì tinh cầu hạ xuống, nhường chỗ cho khung hologram DOM của hud.js.
//
// Ba lớp, cùng phủ kín khoang não (không còn canvas vuông nằm giữa):
//   1. canvas WebGL2: một fragment shader ray-sphere vẽ hành tinh 3D thật (pháp tuyến,
//      ánh sáng, terminator, fresnel, lớp tinh vân bên trong lấy mẫu ở bán kính nhỏ hơn
//      nên có thị sai thật), khí quyển, tinh vân nền, bụi sao lớp hai và sương chân trời
//      làm lưới sàn tan dần. Không texture ngoài, không thư viện: toàn bộ hiệu ứng nằm
//      trong shader nên Three.js chỉ thêm ~600KB mà không thêm gì cho mắt.
//   2. canvas 2D phủ lên: ba Data Orbit 3D (điểm sau hành tinh bị che theo hình học
//      thật), hạt dữ liệu, ký hiệu tín hiệu, vệ tinh dự án + nhãn chống chồng, hologram
//      Joyce trong lõi khi đang gọi.
//   3. DOM: tooltip vệ tinh. Ngăn kéo ngữ cảnh dự án do hud.js dựng (nó có dữ liệu).
//
// Hồ sơ chất lượng: high (shader đủ lớp) / balanced (ít octave, bỏ voronoi) / safe
// (Canvas 2D, không shader) / reduced (prefers-reduced-motion: gần như tĩnh, chỉ đổi màu
// trạng thái). FPS trung bình < 30 thì tự hạ một bậc; mất context WebGL thì về safe.
// Trạng thái và mức âm KHÔNG tự bịa: hud.js đọc từ runtime thật rồi đẩy vào đây.
// ============================================
(function () {
  "use strict";

  var FLAG = "joyce_alien_intelligence_planet_v1";
  var QKEY = "joyce.planetQuality";       // ghi đè hồ sơ chất lượng bằng tay (tuỳ chọn)

  var PAL = {
    navy: [2, 8, 23], ocean: [6, 76, 255], cyan: [0, 231, 255], mint: [37, 255, 209],
    violet: [139, 92, 255], magenta: [255, 62, 200], green: [114, 255, 115], gold: [255, 211, 106],
  };
  var SAT_COLORS = ["cyan", "mint", "violet", "magenta", "green", "gold"];
  var GLYPHS = ["0x1F", "λ", "∑", "◇", "01", "Δt", "∞", "#4E", "~>", "10", "ψ", "::"];
  var STATES = ["READY", "CONNECTING", "LISTENING", "THINKING", "SPEAKING", "INTERRUPTING", "RECONNECTING", "ERROR"];

  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function hashStr(s) { var h = 0; s = String(s || ""); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }

  function flagOn() {
    try {
      var q = new URLSearchParams(location.search).get(FLAG);
      if (q === "0" || q === "1") localStorage.setItem(FLAG, q);
      return localStorage.getItem(FLAG) !== "0";
    } catch (e) { return true; }
  }
  function setFlag(on) { try { localStorage.setItem(FLAG, on ? "1" : "0"); } catch (e) {} }

  // ---------------------------------------------------------------------------
  // SHADER
  // ---------------------------------------------------------------------------
  var VS = "#version 300 es\nin vec2 aP;void main(){gl_Position=vec4(aP,0.,1.);}";

  // HI=1: voronoi (mạng nơron + thành phố trí tuệ), 4 octave, lớp tinh vân trong riêng.
  function fragSrc(hi) {
    return "#version 300 es\nprecision highp float;\n#define HI " + (hi ? 1 : 0) + "\n" + [
      "out vec4 o;",
      "uniform vec2 uRes; uniform vec2 uC; uniform float uR; uniform float uT;",
      "uniform vec2 uRot; uniform float uLight; uniform float uAmp; uniform float uHover;",
      "uniform vec4 uS1; uniform vec4 uS2; uniform vec2 uPar; uniform float uHorizon; uniform float uFlowT;",
      "uniform vec4 uSun; uniform vec3 uSunC;",
      // Trái Đất H2O: khung địa lý (nhìn -> địa lý), hướng Mặt Trời THẬT, bản đồ Việt Nam,
      // thời tiết kinh doanh, Ngân Hà + hố đen nạp dữ liệu.
      "uniform mat3 uGeo; uniform vec3 uL; uniform sampler2D uVN; uniform float uVNOn; uniform vec4 uVNBox; uniform vec3 uVNc;",
      "uniform vec4 uWx; uniform vec4 uWxC; uniform float uFlash; uniform float uGal; uniform vec4 uBH; uniform float uCore;",
      // Giao diện tùy biến (tab Quả tinh cầu): bảng màu bề mặt (đáy, biển, viền, điểm nhấn);
      // uLk = (sức nắng lên hành tinh, khí quyển, độ sáng bề mặt, ánh trăng); uMoonV = hướng
      // Mặt Trăng (khung nhìn); uCl = (độ phủ mây nền, độ u tối, pha gió, mưa toàn cầu);
      // uTor = (điểm chân lốc - địa lý, cường độ); uBolt = (điểm sét đánh - địa lý, độ chớp);
      // uCo = (độ rõ lõi, ánh sáng lõi, phun trào, độ đen mây ô bão: 0 = chỉ có gió, 1 = mưa/sét).
      "uniform vec3 uPa; uniform vec3 uPb; uniform vec3 uPc; uniform vec3 uPd;",
      "uniform vec4 uLk; uniform vec3 uMoonV; uniform vec4 uCl; uniform vec4 uTor; uniform vec4 uBolt; uniform vec4 uCo;",
      // Ô bão (0.65.41): uRc[i] = (tâm ô - địa lý, cường độ), uRs = bán kính góc của 4 ô.
      "uniform vec4 uRc[4]; uniform vec4 uRs;",
      "const vec3 NAVY=vec3(.008,.031,.09), OCEAN=vec3(.024,.298,1.), CYAN=vec3(0.,.906,1.), MINT=vec3(.145,1.,.82),",
      "  VIOLET=vec3(.545,.361,1.), MAGENTA=vec3(1.,.243,.784), GREEN=vec3(.447,1.,.451), GOLD=vec3(1.,.827,.416), RED=vec3(1.,.18,.22);",
      "float h13(vec3 p){p=fract(p*.1031);p+=dot(p,p.zyx+31.32);return fract((p.x+p.y)*p.z);}",
      "vec3 h33(vec3 p){p=fract(p*vec3(.1031,.103,.0973));p+=dot(p,p.yxz+33.33);return fract((p.xxy+p.yxx)*p.zyx);}",
      "float vn(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);",
      " return mix(mix(mix(h13(i),h13(i+vec3(1,0,0)),f.x),mix(h13(i+vec3(0,1,0)),h13(i+vec3(1,1,0)),f.x),f.y),",
      "  mix(mix(h13(i+vec3(0,0,1)),h13(i+vec3(1,0,1)),f.x),mix(h13(i+vec3(0,1,1)),h13(i+vec3(1,1,1)),f.x),f.y),f.z);}",
      "float fbm(vec3 p){float a=.5,s=0.;",
      "#if HI",
      " for(int i=0;i<4;i++){s+=a*vn(p);p=p*2.03+vec3(1.7,9.2,3.1);a*=.5;} return s/.9375;",
      "#else",
      " for(int i=0;i<3;i++){s+=a*vn(p);p=p*2.03+vec3(1.7,9.2,3.1);a*=.5;} return s/.875;",
      "#endif",
      "}",
      "#if HI",
      "vec3 vor(vec3 x){vec3 i=floor(x),f=fract(x);float d1=8.,d2=8.;vec3 id=vec3(0);",
      " for(int k=-1;k<=1;k++)for(int j=-1;j<=1;j++)for(int l=-1;l<=1;l++){",
      "  vec3 g=vec3(float(l),float(j),float(k));vec3 r=g+h33(i+g)-f;float d=dot(r,r);",
      "  if(d<d1){d2=d1;d1=d;id=i+g;}else if(d<d2)d2=d;}",
      " return vec3(sqrt(d1),sqrt(d2),h13(id));}",
      "#endif",
      "mat3 rY(float a){float c=cos(a),s=sin(a);return mat3(c,0,-s, 0,1,0, s,0,c);}",
      "mat3 rX(float a){float c=cos(a),s=sin(a);return mat3(1,0,0, 0,c,s, 0,-s,c);}",
      "vec3 rotAx(vec3 v,vec3 k,float a){float c=cos(a),s=sin(a);return v*c+cross(k,v)*s+k*dot(k,v)*(1.-c);}",
      "void main(){",
      " vec2 fc=gl_FragCoord.xy; vec2 p=(fc-uC)/uR; float d=length(p); float px=1.6/uR;",
      " float flow=uS1.x, energy=uS1.y, listen=uS1.z, speak=uS1.w;",
      " float conn=uS2.x, recon=uS2.y, err=uS2.z, intr=uS2.w;",
      " vec3 L=normalize(uL);",
      " vec2 lxy=length(L.xy)>.001?normalize(L.xy):vec2(-.7,.7);",
      " vec2 shadowDir=-lxy;",
      " float bgK=1.-uLight*.8;",
      // ---- nền: tinh vân + bụi sao + sương chân trời (premultiplied) ----
      " vec3 acc=vec3(0.); float al=0.;",
      // hố đen bẻ cong ánh sao phía sau: lấy mẫu nền ở toạ độ bị đẩy ra xa tâm hố
      " vec2 fcb=fc;",
      " if(uBH.z>0.){vec2 bv=fc-uBH.xy; float b2=dot(bv,bv)/(uBH.z*uBH.z); fcb=fc+bv*(2.2/(b2+.35));}",
      " vec2 q=(fcb+uPar)/uRes.y;",
      " float n1=fbm(vec3(q*1.7,uT*.006)); float n2=vn(vec3(q*3.4+7.,uT*.01));",
      " float nebFall=exp(-d*.42);",
      " vec3 neb=mix(OCEAN*.55,VIOLET,smoothstep(.42,.78,n1))+MAGENTA*.35*smoothstep(.62,.9,n2)*smoothstep(.5,.7,n1);",
      " float nebA=(.05+.17*nebFall)*smoothstep(.25,.75,n1)*bgK;",
      " acc+=neb*nebA; al+=nebA;",
      // Ngân Hà: dải sao chéo + lõi vàng + vệt bụi tối
      " vec2 gq=(fcb-uRes*.5+uPar*.6)/uRes.y; float ga=-.46;",
      " vec2 gr=vec2(cos(ga)*gq.x-sin(ga)*gq.y,sin(ga)*gq.x+cos(ga)*gq.y);",
      " float gw=.13+.05*vn(vec3(gr.x*2.2,1.,4.));",
      " float band=exp(-gr.y*gr.y/(gw*gw));",
      " vec2 gb=gr-vec2(.42,.02); float bulge=exp(-dot(gb,gb)*14.);",
      " float gn=vn(vec3(gr*6.,2.3))*.6+vn(vec3(gr*15.,7.1))*.4;",
      " float dust=smoothstep(.5,.75,vn(vec3(gr*vec2(5.,16.)+3.,5.1)))*exp(-gr.y*gr.y/(gw*gw*.2));",
      " vec3 galC=mix(vec3(.42,.52,1.),vec3(1.,.84,.66),clamp(bulge+.25*band,0.,1.))*(.45+.55*gn)*(1.-.4*dust);",
      " float galA=(band*.26*(.5+.5*gn)+bulge*.3)*(1.-.45*dust)*uGal*bgK;",
      " acc+=galC*galA; al+=galA*.7;",
      " vec2 dq=(fcb+uPar*1.8)/2.6; vec2 dc=floor(dq); float dh=h13(vec3(dc,3.1));",
      " if(dh>.9965-.0045*band*uGal){vec2 dd=fract(dq)-.5; float tw=.55+.45*sin(uT*(1.+dh*3.)+dh*40.);",
      "  float st=smoothstep(.32,0.,length(dd))*tw*.75*bgK; acc+=mix(vec3(.75,.9,1.),MINT,fract(dh*97.))*st; al+=st;}",
      " float yt=1.-fc.y/uRes.y;",
      " float fog=(.62*exp(-abs(yt-uHorizon)*16.)+.30*smoothstep(uHorizon-.01,uHorizon+.08,yt)*(1.-.55*smoothstep(uHorizon+.08,1.,yt)))*bgK;",
      " acc=acc*(1.-fog)+NAVY*fog; al=al*(1.-fog)+fog;",
      " if(uSun.w>0.){",
      "  vec2 sq=(fc-uSun.xy)/uSun.z; float sd=length(sq); float ang=atan(sq.y,sq.x);",
      "  float gran=vn(vec3(sq*5.,uT*.25));",
      "  float disk=1.-smoothstep(.95,1.05,sd);",
      "  vec3 diskC=mix(vec3(1.,.97,.86),uSunC,smoothstep(.2,1.,sd)*.75)*(.82+.3*gran);",
      "  float o1=max(sd-1.,0.);",
      "  float rays=pow(.5+.5*sin(ang*9.+vn(vec3(ang*1.6,o1*.4,uT*.12))*5.),5.)*exp(-o1*.85)*step(1.,sd);",
      "  float cor=exp(-o1*2.3)*.95+exp(-o1*.42)*.2;",
      // Đĩa sáng theo căn bậc ~1/3 của cường độ, quầng + tia theo đúng cường độ: Mặt Trời chỉnh
      // yếu (hay app Legacy lỗi) là quầng tắt hẳn mà đĩa vẫn là một khối sáng, không ra đĩa xám đục.
      "  vec3 sunC=(diskC*disk*1.7*pow(max(uSun.w,0.),.35)+uSunC*(cor+rays*.32)*(1.-disk)*uSun.w)*(1.-uLight*.35);",
      "  vec2 ab=uC-uSun.xy; float tt=clamp(dot(fc-uSun.xy,ab)/dot(ab,ab),0.,1.);",
      "  float perp=length(fc-(uSun.xy+ab*tt))/uR; float wdt=.3+.95*tt;",
      "  float beam=exp(-pow(perp/wdt,2.)*2.4)*smoothstep(0.,.22,tt)*(1.-smoothstep(.66,.97,tt))*(.24+.05*sin(uT*.7+perp*5.));",
      "  sunC+=uSunC*beam*uSun.w;",
      "  acc+=sunC; al+=dot(sunC,vec3(.3,.45,.25))+disk*.85;",
      " }",
      " if(uBH.z>0.){",
      "  vec2 bq=(fc-uBH.xy)/uBH.z; float br=length(bq);",
      "  if(br<7.){",
      "   float ca=cos(.32),sa=sin(.32); vec2 d2=vec2(ca*bq.x+sa*bq.y,-sa*bq.x+ca*bq.y);",
      "   float rr=length(vec2(d2.x,d2.y/.3)); float an=atan(d2.y/.3,d2.x); float ing=uBH.w;",
      "   float rin=1.45, rout=4.2+ing*.8;",
      "   float diskM=smoothstep(rin,rin+.25,rr)*(1.-smoothstep(rin+.6,rout,rr));",
      "   float strk=.55+.45*vn(vec3(an*3.,rr*2.2-uT*(.6+ing*3.),1.7));",
      "   float dop=.55+.45*cos(an+.4);",
      "   vec3 dC=mix(vec3(1.,.5,.18),vec3(1.,.93,.78),smoothstep(rout,rin,rr))*diskM*strk*dop*(.32+.9*ing)*bgK;",
      "   float fr0=step(d2.y,0.);",
      "   vec3 bk=dC*(1.-fr0)*.9; acc+=bk; al+=dot(bk,vec3(.3,.45,.25));",
      "   float sh=1.-smoothstep(.96,1.04,br); acc*=1.-sh; al=al*(1.-sh)+sh*.92;",
      "   float bang=atan(bq.y,bq.x);",
      "   float arm=pow(.5+.5*sin(3.*bang+6.*log(max(br,.2))+uT*4.),7.);",
      "   float flowM=smoothstep(6.5,1.6,br)*smoothstep(.98,1.25,br);",
      "   vec3 stream=mix(CYAN,MINT,.5+.5*sin(bang*2.+uT))*arm*flowM*ing*1.6*bgK;",
      "   vec3 rc=VIOLET*exp(-max(br-1.,0.)*1.6)*.1*step(1.,br)*bgK+dC*fr0*.55+stream;",
      "   acc+=rc; al+=dot(rc,vec3(.3,.45,.25));",
      "  }",
      " }",
      // ---- khí quyển + vòng trạng thái ngoài thân ----
      " float hh=d-1.; vec2 dir=d>0.?p/d:vec2(0.);",
      " float lightSide=.5+.5*dot(dir,lxy);",
      " float outer=smoothstep(-.015,.02,hh);",
      " float atm=exp(-max(hh,0.)*6.5)*outer*(.42+.48*lightSide)*(1.+.35*uHover)*(1.-.35*recon)*uLk.y;",
      " vec3 atmC=mix(uPb,uPc,.55+.35*lightSide)*atm*(1.-uLight*.3);",
      " float vm=smoothstep(.15,.95,dot(dir,shadowDir))*exp(-max(hh,0.)*15.)*outer;",
      " atmC+=mix(VIOLET,MAGENTA,.45)*vm*.55*uLk.y;",
      " atmC+=uSunC*atm*lightSide*.4*uSun.w;",
      " float lh=listen*(.24+uAmp*.9)*exp(-max(hh,0.)*(5.2-uAmp*2.4))*outer;",
      " atmC+=mix(GREEN,CYAN,.55)*lh;",
      " for(int k=0;k<3;k++){float ph=fract(uT*.42+float(k)/3.);",
      "  float rr=ph*1.35; float ring=exp(-pow((hh-rr)*20.,2.))*(1.-ph)*(1.-ph)*outer;",
      "  atmC+=mix(CYAN,MINT,ph)*ring*speak*(.2+uAmp*.6);",
      "  float pc=fract(-uT*.5+float(k)/3.); float rc=pc*1.7;",
      "  atmC+=CYAN*exp(-pow((hh-rc)*20.,2.))*smoothstep(0.,.35,pc)*(1.-smoothstep(.6,1.,pc))*conn*.3*outer;",
      "  float pi2=fract(uT*.9+float(k)/3.); float ri=(1.-pi2)*.9;",
      "  atmC+=VIOLET*exp(-pow((hh-ri)*16.,2.))*pi2*intr*.45*outer;}",
      " float eF=exp(-length(dir-normalize(vec2(.62,-.55)))*3.2)*exp(-max(hh,0.)*9.)*outer;",
      " atmC+=RED*eF*err*(.55+.45*step(.5,fract(uT*2.3)));",
      " acc+=atmC; al+=dot(atmC,vec3(.3,.45,.25));",
      // ---- hành tinh ----
      " float body=1.-smoothstep(1.-px,1.+px,d);",
      " if(body>0.){",
      "  vec3 n=vec3(p,sqrt(max(0.,1.-d*d)));",
      "  mat3 M=rY(uFlowT*.05+uRot.x)*rX(.38+uRot.y);",
      "  vec3 s=M*n;",
      "  vec3 g=uGeo*n;",
      "  float latD=degrees(asin(clamp(g.y,-1.,1.))); float lonD=degrees(atan(g.x,g.z));",
      "  float ft=uFlowT;",
      "  vec3 w=vec3(fbm(s*1.6+vec3(0.,0.,ft*.03)),fbm(s*1.6+vec3(5.2,1.3,ft*.03)),0.);",
      "  float oc=fbm(s*2.3+vec3(w.xy*1.3,ft*.025));",
      "  vec3 base=mix(uPa,uPb*.62,smoothstep(.25,.75,oc));",
      "  base=mix(base,uPc*.6,smoothstep(.64,.9,oc)*.4)*uLk.z;",
      "  float lat=s.y; float band=sin(lat*13.+w.x*6.5+ft*.22);",
      "  float cur=smoothstep(.93,1.,band)*smoothstep(.35,.75,vn(s*5.5+vec3(ft*.05)));",
      "  vec3 curC=mix(uPc,uPd,.5+.5*sin(lat*3.+ft*.1))*cur*.3;",
      // lớp trong: giao tia nhìn với cầu bán kính .8 -> thị sai thật, cộng khúc xạ nhẹ
      "  vec2 pr=p*(1.-.14*(1.-n.z));",
      "  float di=length(pr); vec3 ni=di<.8?vec3(pr,sqrt(.64-di*di))/.8:n;",
      "  vec3 si=rY(uFlowT*.032+uRot.x*.7)*rX(.38+uRot.y)*ni;",
      "  float es=ft*(.04+energy*.11);",
      "#if HI",
      "  float e1=fbm(si*2.+vec3(es)); float e2=fbm(si*3.1+vec3(7.,-es,2.)); float e3=fbm(si*2.7+vec3(13.,4.,es)); float e4=vn(si*3.3+vec3(21.,es,0.));",
      "#else",
      "  float e1=fbm(si*2.+vec3(es)); float e2=vn(si*3.1+vec3(7.,-es,2.)); float e3=vn(si*2.7+vec3(13.,4.,es)); float e4=vn(si*3.3+vec3(21.,es,0.));",
      "#endif",
      "  vec3 sub=VIOLET*smoothstep(.44,.74,e1)+MAGENTA*smoothstep(.54,.8,e2)*.8+GREEN*smoothstep(.6,.82,e3)*.45+GOLD*smoothstep(.7,.88,e4)*.4;",
      "  float trans=.35+.65*n.z;",
      "  float ndl=dot(n,L); float day=smoothstep(-.25,.45,ndl);",
      // sức nắng (thanh Cường độ Mặt Trời): .1 -> mặt ngày gần như tối, 2 -> chói gấp rưỡi
      "  float lit=.25+.75*uLk.x;",
      "  sub*=(.22+energy*.46+listen*.08)*trans*(.4+.6*day);",
      "  float core=exp(-d*d*5.)*(.08+energy*.22+speak*(.22+uAmp*.6)+listen*(.06+uAmp*.3));",
      "  vec3 coreC=mix(uPc,vec3(.85,.97,1.),.35)*core;",
      // ---- LÕI TRÁI ĐẤT (chủ yêu cầu 06/10): nhìn xuyên lớp nước xuống tận tâm hành tinh ----
      // Nhân ngoài lỏng bán kính .46: giao tia với cầu nhỏ (thị sai thật khi xoay) + khúc xạ mạnh
      // hơn lớp tinh vân, dung nham đối lưu = fbm bị vặn (domain warp) cho ra các DÒNG chảy
      // (ridged noise), xoay NGƯỢC chiều vỏ ngoài. Nhân trong rắn nóng trắng, có nhịp đập.
      // Cột magma bốc lên từ lõi + quầng nhiệt toả vào nước. Lõi lộ rõ hơn về đêm, khi rê chuột
      // lên hành tinh (uHover) và khi Joyce đang nghĩ (energy: dung nham chảy nhanh hơn);
      // uCore tắt dần khi phóng cận cảnh để không che bản đồ Việt Nam.
      // Tab Quả tinh cầu: uCo.x nhân độ rõ (nhìn xuyên nước nhiều hay ít), uCo.y nhân độ phát
      // sáng của dung nham + quầng nhiệt, uCo.z (phun trào) cho dung nham chảy nhanh, cột magma
      // to và vươn xa hơn.
      "  vec3 lavaC=vec3(0.);",
      "  float er=uCo.z;",
      "  if(uCore>.01&&uCo.x>.005){",
      "   float rc=.46;",
      "   vec2 prc=p*(1.-.22*(1.-n.z)); float dc2=length(prc);",
      "   if(dc2<rc*(1.75+er*.5)){",
      "    float vis=(.22+.28*(1.-day)+.45*uHover+.12*energy+.25*er)*uCore*uCo.x;",
      "    float lt=uT*(.05+energy*.16+er*.22);",
      "    if(dc2<rc+.01){",
      "     float inC=1.-smoothstep(rc-.018,rc+.004,dc2);",
      "     vec3 nc=vec3(prc,sqrt(max(0.,rc*rc-dc2*dc2)))/rc;",
      "     vec3 sc=rY(-uFlowT*.045+uRot.x*.55)*rX(.38+uRot.y)*nc;",
      "#if HI",
      "     vec3 wq=vec3(fbm(sc*2.2+vec3(lt,0.,0.)),fbm(sc*2.2+vec3(3.1,lt,1.7)),fbm(sc*2.2+vec3(7.4,2.2,lt)));",
      "#else",
      "     vec3 wq=vec3(vn(sc*2.2+vec3(lt,0.,0.)),vn(sc*2.2+vec3(3.1,lt,1.7)),vn(sc*2.2+vec3(7.4,2.2,lt)));",
      "#endif",
      "     float f1=fbm(sc*3.+wq*2.2+vec3(0.,lt*1.6,0.));",
      "     float vein=pow(1.-abs(f1*2.-1.),9.);",
      "     float cells=fbm(sc*5.5-wq*1.5+vec3(lt*2.));",
      "     float heat=clamp(vein*1.3+smoothstep(.6,.95,cells)*.3,0.,1.);",
      "     vec3 crust=vec3(.32,.06,.01)*(.6+.4*cells);",
      "     vec3 lava=mix(vec3(1.,.42,.06),vec3(1.,.85,.45),smoothstep(.5,1.,heat));",
      "     vec3 cs=mix(crust,lava,smoothstep(.15,.7,heat));",
      // Mép lõi SÁNG màu nham thạch (chủ không thích viền đen 06/10): rìa cầu là chỗ ta nhìn
      // xuyên lớp magma dày nhất, nên rực hơn chứ không tối đi như mép một quả cầu đặc.
      "     cs*=.8+.2*nc.z;",
      "     float rimC=pow(1.-nc.z,2.2);",
      "     cs+=mix(vec3(1.,.42,.06),vec3(1.,.84,.42),rimC)*rimC*1.3;",
      "     float di=dc2/rc;",
      "     cs+=vec3(1.,.55,.15)*exp(-di*di*3.)*.25;",
      "     cs+=vec3(1.,.85,.55)*exp(-di*di*12.5)*(.8+.2*sin(uT*1.7))*1.2;",
      "     cs=mix(cs,cs*vec3(.55,.75,1.)+vec3(0.,.02,.05),.3);",
      "     lavaC=cs*inC*vis*uCo.y;",
      "    }",
      "    float ou=max(dc2-rc,0.);",
      "    float halo=exp(-ou*9./(.55+.45*uCo.y+er*.6))*smoothstep(rc*.97,rc*1.01,dc2);",
      // Nhiễu theo HƯỚNG (vector đơn vị) chứ không theo góc atan: atan gãy ở ±π nên từng để lại
      // một vệt ngang cứng phía trái lõi, phun trào làm cột magma to ra là lộ hẳn.
      "#if HI",
      "    vec2 dcn=prc/max(dc2,1e-4);",
      "    float plume=pow(vn(vec3(dcn*7.,ou*7.-uT*(.25+energy*.6+er*1.4))),5.-er*2.)*exp(-ou*4.5/(1.+er*1.6))*smoothstep(rc,rc*1.04,dc2);",
      "    halo+=plume*(2.2+er*5.);",
      "#else",
      "    halo+=er*exp(-ou*5.)*smoothstep(rc,rc*1.04,dc2)*1.6;",
      "#endif",
      "    halo+=exp(-ou*30.)*smoothstep(rc*.97,rc*1.01,dc2)*1.2;",
      "    lavaC+=vec3(1.,.42,.08)*halo*.35*vis*uCo.y;",
      "   }",
      "  }",
      // mạng nơron + thành phố trí tuệ
      "  float pulseSp=1.4+energy*5.+listen*uAmp*3.;",
      "#if HI",
      "  vec3 v=vor(s*4.6+w*.35);",
      "  float edge=1.-smoothstep(0.,.032,v.y-v.x);",
      "  float city=smoothstep(.09,0.,v.x)*step(.55,v.z);",
      "#else",
      "  vec3 v=vec3(0.); float edge=1.-smoothstep(0.,.03,abs(vn(s*5.+w)-.5)); float city=0.;",
      "#endif",
      "  float pulse=.3+.7*pow(.5+.5*sin(dot(s,vec3(9.,7.,5.))-ft*pulseSp),3.);",
      "  float neural=edge*pulse*(.16+energy*.26+listen*uAmp*.6);",
      "  float conv=energy*edge*pow(.5+.5*sin(d*18.+uT*6.),4.)*.45;",
      "  vec3 neuC=mix(uPc,VIOLET,.3+.4*energy)*(neural+conv);",
      "  vec3 cityC=mix(GOLD,MINT,v.z)*city*(.35+.65*(1.-day))*(.6+.4*sin(ft*2.+v.z*30.));",
      "  float rip=listen*uAmp*sin(d*28.-uT*5.)*.5+speak*(.25+uAmp)*exp(-pow(fract(d*1.6-uT*.55)-.5,2.)*55.)*.6;",
      "  vec3 col=base*(.1+.9*day*lit)*(1.-min(1.,length(lavaC))*.35)+curC*(.5+.5*day)+sub+coreC+neuC*(.55+.45*day)+cityC+lavaC;",
      "  col+=uPc*max(rip,0.)*.35;",
      // ánh trăng: mặt đêm hứng sáng bạc từ phía Mặt Trăng (thanh Độ sáng trăng x phần trăng sáng)
      "  float mlt=max(dot(n,uMoonV),0.)*(1.-day)*uLk.w;",
      "  col+=(base*2.2+vec3(.02,.03,.06))*mlt;",
      // (0.65.44: bỏ khe nứt dung nham rải khắp vỏ - chủ thấy không thật; dung nham giờ phun
      // từ một ngọn núi rồi chảy thành sông, vẽ ở lớp 2D: drawEruption)
      // viền hoàng hôn: dải nắng vàng chạy dọc đường ranh ngày/đêm
      "  col+=uSunC*exp(-pow(ndl*5.,2.))*.12*uSun.w;",
      // mây mỏng trôi theo gió (xoay quanh trục cực), dày lên trên Việt Nam theo thời tiết kinh doanh.
      // uCl.z là PHA gió tích luỹ phía JS (gió mạnh = trôi nhanh hơn mà không giật khi bật/tắt).
      // Lốc xoáy (uTor): vặn trường mây quanh điểm chân lốc thành xoắn ốc chặt, dày và tối hơn.
      "  vec3 gw=g; float tw2=0.;",
      "  if(uTor.w>.01){float ta=acos(clamp(dot(g,uTor.xyz),-1.,1.)); tw2=exp(-ta*ta/.008)*uTor.w;",
      "   gw=mix(g,rotAx(g,uTor.xyz,tw2*10.+uT*1.5),smoothstep(0.,.3,tw2));}",
      "  vec3 cq=rY(uCl.z*.004)*gw;",
      "  float sw=0., sdc=9.;",
      "  if(uWx.w>0.){sdc=acos(clamp(dot(g,uWxC.xyz),-1.,1.)); sw=exp(-sdc*sdc/(uWxC.w*uWxC.w))*uWx.w;",
      "   vec3 tw=rotAx(g,uWxC.xyz,sw*9.+uT*.8); cq=mix(cq,tw,smoothstep(0.,.35,sw));}",
      "  float cd=fbm(cq*3.1+vec3(uCl.z*.006,0.,uCl.z*.004));",
      "  float vnA=acos(clamp(dot(g,uVNc),-1.,1.)); float wv=exp(-vnA*vnA/.045);",
      // ô bão: mây dày đặc + đen trong vùng, mưa chỉ rơi trong vùng này
      "  float rcW=0.;",
      "  for(int ci=0;ci<4;ci++){if(uRc[ci].w>.01){float ra=acos(clamp(dot(g,uRc[ci].xyz),-1.,1.)); float sg=uRs[ci]; rcW=max(rcW,exp(-ra*ra/(sg*sg))*uRc[ci].w);}}",
      "  float cov=uCl.x+uWx.x*wv*.85+sw*.95+tw2*.9+rcW*1.1;",
      "  float lo=.66-.42*min(cov,1.2); float cm=smoothstep(lo,lo+.16,cd);",
      "  cm=max(cm,smoothstep(.3,.62,cd)*smoothstep(.15,.65,rcW));",
      // bão / lốc: cánh mây xoắn ốc vẽ theo toạ độ cực quanh tâm, mắt bão trống ở giữa
      "  if(sw>.002){",
      "   vec3 e1=normalize(cross(uWxC.xyz,vec3(0.,1.,0.))); vec3 e2=cross(uWxC.xyz,e1);",
      "   vec3 tg=g-uWxC.xyz*dot(g,uWxC.xyz); float th=atan(dot(tg,e2),dot(tg,e1));",
      "   float rr2=sdc/uWxC.w;",
      "   float arm=.5+.5*sin(2.*th+5.5*log(rr2+.06)-uT*1.1);",
      "   float spir=smoothstep(.3,.8,arm*(.7+.6*cd))*smoothstep(.06,.18,rr2)+smoothstep(.3,.12,rr2)*smoothstep(.05,.11,rr2)*.9;",
      "   spir*=1.-smoothstep(1.6,2.6,rr2);",
      "   cm=mix(cm,clamp(spir,0.,1.),clamp(sw*1.6,0.,1.));",
      "   cm*=smoothstep(.04,.09,rr2);",
      "  }",
      "  float ca=cm*(.3+.5*min(1.,cov*1.3))*smoothstep(0.,.18,n.z+.05)*smoothstep(0.,.06,cov);",
      "  float dk=clamp((uWx.y*.5+uWx.z*.35)*wv+sw*.25+uCl.y+tw2*.55+rcW*.72*uCo.w,0.,.9);",
      "  vec3 cC=mix(vec3(.82,.9,1.),vec3(.2,.23,.31),dk)*(.07+.93*day*lit)+uSunC*exp(-pow(ndl*5.,2.))*.25*uLk.x+vec3(.03,.06,.12)*(1.-day)*(1.+2.*sw)+vec3(.45,.5,.62)*mlt*.6;",
      "  col*=1.-ca*.22*day;",
      "  col=mix(col,cC,ca);",
      "  float rn=(uWx.y*(wv+sw)+uCl.w*rcW*.6)*cm;",
      "  if(rn>.01){float rs=h13(vec3(floor(fc.x/2.5),floor((fc.y+uT*520.)/11.),3.)); col+=vec3(.6,.75,.92)*step(.975,rs)*rn*.55;}",
      "  col+=vec3(.85,.9,1.)*uFlash*cm*min(1.,wv+sw)*1.3;",
      // sét của tab Quả tinh cầu: chớp sáng mây + mặt đất quanh đúng điểm tia sét đánh xuống
      "  if(uBolt.w>.01){float bA=acos(clamp(dot(g,uBolt.xyz),-1.,1.)); col+=vec3(.8,.87,1.)*uBolt.w*(cm*.8+.3)*exp(-bA*bA/.01)*1.6;}",
      // Việt Nam hologram: viền phát sáng + nền mờ có vạch quét, Hoàng Sa/Trường Sa, đèn đô thị về đêm
      "  if(uVNOn>.5){",
      "   vec2 vuv=vec2((lonD-uVNBox.x)/uVNBox.z,(uVNBox.y-latD)/uVNBox.w);",
      "   if(vuv.x>0.&&vuv.x<1.&&vuv.y>0.&&vuv.y<1.){",
      "    vec4 tx=textureLod(uVN,vuv,0.);",
      "    float scan=.7+.3*sin(latD*26.-uT*2.4); float flk=.88+.12*sin(uT*6.3+lonD*2.);",
      "    float limb=smoothstep(0.,.3,n.z);",
      "    vec3 holo=(CYAN*(tx.g*2.1+tx.r*.3*scan)+MINT*tx.a*1.8)*flk*limb;",
      "    holo+=GOLD*tx.b*(1.-day)*1.4*limb+vec3(.9,.97,1.)*tx.b*day*.08*limb;",
      "    col+=holo*(1.-ca*.55);",
      "   }",
      "  }",
      "  col*=.6+.4*n.z;",
      "  vec3 nn=normalize(n+vec3(w.xy-.5,0.)*.16);",
      "  vec3 H=normalize(L+vec3(0.,0.,1.));",
      "  float sp=pow(max(dot(nn,H),0.),70.)*.38+pow(max(dot(nn,H),0.),11.)*.035;",
      "  col+=mix(vec3(.85,.96,1.),uSunC,.35*uSun.w)*sp*day*lit;",
      "  float fr=pow(1.-n.z,3.);",
      "  col+=uPc*fr*.7*(.55+.45*lightSide)*(1.+.3*uHover)*uLk.y;",
      "  col+=mix(VIOLET,MAGENTA,.5)*fr*smoothstep(.1,.9,dot(dir,shadowDir))*.75*uLk.y;",
      "  col+=uSunC*fr*day*.5*uSun.w;",
      "  float off=recon*smoothstep(.38,.62,vn(s*2.4+vec3(uT*.35)));",
      "  col*=1.-off*.65-recon*.12;",
      "  float em=smoothstep(.8,.97,dot(n,normalize(vec3(.55,-.5,.67))))*err;",
      "  float brk=.7+.3*step(.75,fract(fc.y/uR*9.+uT*1.5));",
      "  col=mix(col,RED*.75*brk,em*(.5+.25*step(.5,fract(uT*1.7))));",
      "  col=1.-exp(-col*1.3);",
      "  acc=acc*(1.-body)+col*body; al=al*(1.-body)+body;",
      " }",
      " vec3 c=1.-exp(-acc*1.15);",
      " float a=clamp(max(al,max(c.r,max(c.g,c.b))),0.,1.);",
      " o=vec4(min(c,vec3(a)),a);",
      "}",
    ].join("\n");
  }

  function compile(gl, type, src) {
    var sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      var log = gl.getShaderInfoLog(sh);
      gl.deleteShader(sh);
      throw new Error("shader: " + log);
    }
    return sh;
  }
  function makeProgram(gl, hi) {
    var vs = compile(gl, gl.VERTEX_SHADER, VS), fs = compile(gl, gl.FRAGMENT_SHADER, fragSrc(hi));
    var pr = gl.createProgram();
    gl.attachShader(pr, vs); gl.attachShader(pr, fs);
    gl.bindAttribLocation(pr, 0, "aP");
    gl.linkProgram(pr);
    gl.deleteShader(vs); gl.deleteShader(fs);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error("link: " + gl.getProgramInfoLog(pr));
    var u = {};
    ["uRes", "uC", "uR", "uT", "uRot", "uLight", "uAmp", "uHover", "uS1", "uS2", "uPar", "uHorizon", "uFlowT", "uSun", "uSunC",
     "uGeo", "uL", "uVN", "uVNOn", "uVNBox", "uVNc", "uWx", "uWxC", "uFlash", "uGal", "uBH", "uCore",
     "uPa", "uPb", "uPc", "uPd", "uLk", "uMoonV", "uCl", "uTor", "uBolt", "uCo", "uRc", "uRs"]
      .forEach(function (k) { u[k] = gl.getUniformLocation(pr, k); });
    return { pr: pr, u: u };
  }

  // Mục tiêu uniform cho mỗi trạng thái. Chuyển trạng thái = nội suy mềm về đây, nên đổi
  // nhanh từ nói sang nghe không làm hành tinh "giật màu".
  //            flow  energy listen speak conn  recon err  intr  orbitSpeed particleSpeed
  var TARGET = {
    READY:        [1.0, 0.0,  0.0,   0.0,  0.0,  0.0,  0.0, 0.0,  1.0, 1.0],
    CONNECTING:   [1.3, 0.1,  0.0,   0.0,  1.0,  0.0,  0.0, 0.0,  1.3, 1.6],
    LISTENING:    [1.2, 0.05, 1.0,   0.0,  0.0,  0.0,  0.0, 0.0,  0.9, 1.0],
    THINKING:     [2.8, 1.0,  0.0,   0.0,  0.0,  0.0,  0.0, 0.0,  1.6, 2.6],
    SPEAKING:     [1.5, 0.2,  0.0,   1.0,  0.0,  0.0,  0.0, 0.0,  1.1, 1.4],
    INTERRUPTING: [0.4, 0.0,  0.0,   0.0,  0.0,  0.0,  0.0, 1.0,  0.25, 0.3],
    RECONNECTING: [0.7, 0.0,  0.0,   0.0,  0.0,  1.0,  0.0, 0.0,  0.6, 0.6],
    ERROR:        [0.5, 0.0,  0.0,   0.0,  0.0,  0.2,  1.0, 0.0,  0.5, 0.4],
  };

  // ---------------------------------------------------------------------------
  // PHA MẶT TRĂNG theo ngày thật. Tháng giao hội trung bình 29.530588853 ngày, mốc trăng
  // mới 2000-01-06 18:14 UTC. Sai số của cách tính trung bình này cỡ dưới một ngày - đủ
  // để mắt thấy đúng trăng tròn / bán nguyệt / lưỡi liềm của hôm nay.
  // ---------------------------------------------------------------------------
  var SYNODIC = 29.530588853, NEW_MOON_REF = Date.UTC(2000, 0, 6, 18, 14) / 86400000;
  function moonPhase(date) {
    var days = date.getTime() / 86400000 - NEW_MOON_REF;
    var age = ((days % SYNODIC) + SYNODIC) % SYNODIC;
    var p = age / SYNODIC;
    return { phase: p, age: age, illum: (1 - Math.cos(2 * Math.PI * p)) / 2, lunation: Math.floor(days / SYNODIC) };
  }
  var MOON_KEYS = { "new": "planet.moon_new", wax_cres: "planet.moon_wax_cres", first_q: "planet.moon_first_q",
    wax_gib: "planet.moon_wax_gib", full: "planet.moon_full", wan_gib: "planet.moon_wan_gib",
    last_q: "planet.moon_last_q", wan_cres: "planet.moon_wan_cres" };
  function moonPhaseKey(p) {
    if (p < 0.0339 || p >= 0.9661) return "new";
    if (p < 0.2161) return "wax_cres";
    if (p < 0.2839) return "first_q";
    if (p < 0.4661) return "wax_gib";
    if (p < 0.5339) return "full";
    if (p < 0.7161) return "wan_gib";
    if (p < 0.7839) return "last_q";
    return "wan_cres";
  }

  // ---------------------------------------------------------------------------
  // THIÊN VĂN THEO GIỜ THẬT (Trái Đất H2O, chủ duyệt 2026-10-06)
  // Quy ước toạ độ ĐỊA LÝ (cố định theo Trái Đất): y = trục cực Bắc, z = (vĩ 0, kinh 0),
  // x = (vĩ 0, kinh 90 Đông). Mặt Trời: công thức rút gọn của Almanac (sai số < 0,01 độ, thừa
  // cho mắt). Mặt Trăng: kinh độ hoàng đạo = Mặt Trời + góc ly giác suy từ PHA trăng thật
  // (moonPhase), vĩ hoàng đạo 5,145 độ x sin(F) - đủ để vị trí và pha luôn khớp nhau.
  // Khoảng cách KHÔNG theo tỉ lệ thật (Mặt Trăng xa ~30 đường kính, Mặt Trời ~12.000):
  // giữ đúng HƯỚNG và THỜI GIAN, nén khoảng cách cho vừa khung.
  // ---------------------------------------------------------------------------
  var D2R = Math.PI / 180;
  function geoVec(latD, lonD) {
    var la = latD * D2R, lo = lonD * D2R;
    return [Math.cos(la) * Math.sin(lo), Math.sin(la), Math.cos(la) * Math.cos(lo)];
  }
  function astro(date) {
    var n = date.getTime() / 86400000 + 2440587.5 - 2451545.0;
    var L = 280.460 + 0.9856474 * n, g = (357.528 + 0.9856003 * n) * D2R;
    return { n: n, lam: L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g),
             eps: 23.439 - 0.0000004 * n, gmst: 280.46061837 + 360.98564736629 * n };
  }
  // Hoàng đạo (lam, bet - độ) -> xích đạo -> kinh/vĩ địa lý ngay dưới thiên thể -> vector địa lý.
  function eclToGeo(lamD, betD, A) {
    var l = lamD * D2R, b = betD * D2R, e = A.eps * D2R;
    var x = Math.cos(b) * Math.cos(l);
    var y = Math.cos(b) * Math.sin(l) * Math.cos(e) - Math.sin(b) * Math.sin(e);
    var z = Math.cos(b) * Math.sin(l) * Math.sin(e) + Math.sin(b) * Math.cos(e);
    var ra = Math.atan2(y, x) / D2R, dec = Math.asin(clamp(z, -1, 1)) / D2R;
    return geoVec(dec, ra - A.gmst);
  }
  function sunGeo(date) { var A = astro(date); return eclToGeo(A.lam, 0, A); }
  function moonEcl(date, A) {
    var F = (93.272 + 13.22935 * A.n) % 360;
    return { lam: A.lam + 360 * moonPhase(date).phase, F: F };
  }
  function moonGeo(date) { var A = astro(date), m = moonEcl(date, A); return eclToGeo(m.lam, 5.145 * Math.sin(m.F * D2R), A); }
  // Quỹ đạo Mặt Trăng HÔM NAY (giữ nguyên góc quay Trái Đất lúc tính) để vẽ đường đi.
  function moonOrbit(date) {
    var A = astro(date), m = moonEcl(date, A), out = [];
    for (var i = 0; i < 72; i++) {
      var d = i * 5;
      out.push(eclToGeo(m.lam + d, 5.145 * Math.sin((m.F + d) * D2R), A));
    }
    return out;
  }
  // Ma trận nhìn -> địa lý: điểm (latD, lonD) nằm giữa đĩa, Bắc hướng lên. G = Ry(lon)·Rx(-lat).
  function viewMat(latD, lonD) {
    var a = -latD * D2R, b = lonD * D2R, ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b);
    return [[cb, sb * sa, sb * ca], [0, ca, -sa], [-sb, cb * sa, cb * ca]];
  }
  function toView(G, v) {   // G^T v: vector địa lý -> khung nhìn (x phải, y lên, z về phía người xem)
    return [G[0][0] * v[0] + G[1][0] * v[1] + G[2][0] * v[2],
            G[0][1] * v[0] + G[1][1] * v[1] + G[2][1] * v[2],
            G[0][2] * v[0] + G[1][2] * v[1] + G[2][2] * v[2]];
  }
  function smooth(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }

  // Thời tiết kinh doanh -> mây/mưa/sét/xoáy trên Việt Nam: [độ phủ mây, mưa, sét, xoáy].
  var WX = { nang: [0.06, 0, 0, 0], nang_nhe: [0.28, 0, 0, 0], nhieu_may: [0.62, 0, 0, 0],
             mua: [0.78, 0.85, 0, 0], giong: [0.88, 1, 1, 0], bao: [0.95, 1, 0.8, 1], loc_xoay: [0.8, 0.7, 1, 1] };
  var VIEW_HOME = { lat: 14.5, lon: 108.4 };   // thấy trọn Việt Nam + Hoàng Sa + Trường Sa
  var VIEW_VN = { lat: 15.6, lon: 106.6 };     // phóng vừa: Việt Nam giữa đĩa
  var VIEW_NEAR = { lat: 20.87, lon: 106.6 };  // phóng sâu: Hải Phòng - nơi đặt H2O Studio
  var ZMIN = 0.32, ZMAX = 12;
  var VN_CENTER = geoVec(16, 106.5);

  // ---------------------------------------------------------------------------
  // GIAO DIỆN TÙY BIẾN (Cài đặt -> Giao diện Joyce -> Quả tinh cầu, chủ yêu cầu 2026-10-07)
  // MỘT bộ tham số dùng chung cho mọi renderer đang sống (tinh cầu ở màn Joyce + ô xem trước
  // trong Cài đặt): kéo thanh trượt là cả hai đổi cùng lúc. localStorage để mở trang là có
  // ngay; máy chủ (settings.dashboard.planet) là nguồn sự thật cho MỌI máy, hud.js hoà vào
  // lúc khởi động. Máy chủ lọc TỪNG KHOÁ theo đúng các bảng LOOK_* dưới đây (main.py,
  // _PLANET_*): thêm khoá ở đây thì thêm ở đó, test_tinh_cau_tuy_bien.py canh hai bên khớp nhau.
  // ---------------------------------------------------------------------------
  var LOOK_KEY = "joyce.planetLook";
  // Số: [nhỏ nhất, lớn nhất, mặc định]. Mặc định = đúng giao diện trước khi có tab này.
  var LOOK_NUM = {
    sunPower: [0.1, 2, 1], sunSize: [0.6, 1.8, 1],
    moonFull: [0, 1, 1], moonGlow: [0, 2, 1], moonSize: [0.6, 1.8, 1],
    surface: [0.4, 1.8, 1], atmo: [0, 2, 1],
    clouds: [0, 1, 0.3], cloudDark: [0, 1, 0],
    coreVis: [0, 2, 1], coreGlow: [0, 2, 1],
    lavaSpeed: [0.2, 3, 1],   // tốc độ chảy của sông dung nham (1 = chậm, ~1,5 phút một dòng)
    // Cỡ ba vành quỹ đạo dữ liệu, nhân thẳng vào bán kính vành (ringPt). Đáy 0,75 vì vành trong
    // cùng (1,42 R) nhỏ hơn nữa là chui vào lòng tinh cầu và bị che mất.
    orbitSize: [0.75, 1.8, 1],
    // Cỡ các chấm (tiểu hành tinh) chạy trên vành, nhân vào bán kính chấm ở drawParticles.
    orbitDot: [0.5, 3, 1],
  };
  var LOOK_COLOR = { sunColor: "#ffd46b", seaColor: "#064cff", rimColor: "#00e7ff" };
  var LOOK_BOOL = { rain: false, lightning: false, wind: false, tornado: false, eruption: false, orbits: true, knowledge: true };
  // Concept màu bề mặt: deep = đáy biển, sea = biển, rim = viền sáng + khí quyển, mint = điểm
  // nhấn của dòng hải lưu. "ocean" là bảng gốc (đúng các hằng OCEAN/CYAN/MINT trong shader).
  var PALETTES = {
    ocean:    { deep: [0.01, 0.06, 0.2],    sea: [0.024, 0.298, 1],   rim: [0, 0.906, 1],   mint: [0.145, 1, 0.82] },
    emerald:  { deep: [0.004, 0.07, 0.045], sea: [0.02, 0.6, 0.36],   rim: [0.3, 1, 0.62],  mint: [0.78, 1, 0.45] },
    amethyst: { deep: [0.05, 0.015, 0.14],  sea: [0.42, 0.18, 0.95],  rim: [0.86, 0.48, 1], mint: [1, 0.45, 0.8] },
    sunset:   { deep: [0.12, 0.02, 0.06],   sea: [0.92, 0.3, 0.22],   rim: [1, 0.68, 0.3],  mint: [1, 0.42, 0.66] },
    ice:      { deep: [0.05, 0.1, 0.18],    sea: [0.5, 0.74, 0.95],   rim: [0.85, 0.97, 1], mint: [0.62, 1, 0.95] },
    lava:     { deep: [0.09, 0.01, 0],      sea: [0.72, 0.15, 0.03],  rim: [1, 0.45, 0.1],  mint: [1, 0.78, 0.25] },
    gold:     { deep: [0.09, 0.055, 0],     sea: [0.82, 0.58, 0.12],  rim: [1, 0.86, 0.42], mint: [1, 0.96, 0.62] },
    abyss:    { deep: [0, 0.004, 0.02],     sea: [0.06, 0.09, 0.24],  rim: [0.3, 0.4, 0.85], mint: [0.5, 0.36, 0.9] },
  };
  var LOOK_ENUM = { moonMode: [["auto", "manual"], "auto"], palette: [Object.keys(PALETTES).concat("custom"), "ocean"],
    tornadoColor: [["concept", "cyan", "fire", "grey", "dark"], "concept"] };
  // Cảnh dựng sẵn: áp = mặc định + cảnh (thay CẢ bộ), rồi chỉnh tiếp từng chi tiết.
  var SCENES = {
    h2o: {},
    moon_night: { sunPower: 0.3, moonMode: "manual", moonFull: 1, moonGlow: 1.9, moonSize: 1.25, clouds: 0.2, coreVis: 1.3 },
    storm: { sunPower: 0.55, clouds: 0.9, cloudDark: 0.8, rain: true, lightning: true, wind: true },
    tornado: { sunPower: 0.75, clouds: 0.65, cloudDark: 0.55, rain: true, wind: true, tornado: true },
    volcano: { palette: "lava", sunPower: 0.7, clouds: 0.45, cloudDark: 0.7, coreVis: 1.8, coreGlow: 1.7, eruption: true },
    sunset: { sunColor: "#ff7a3d", sunPower: 1.35, sunSize: 1.3, palette: "sunset", clouds: 0.35 },
  };
  function lookDefault() {
    var o = {};
    Object.keys(LOOK_NUM).forEach(function (k) { o[k] = LOOK_NUM[k][2]; });
    Object.keys(LOOK_COLOR).forEach(function (k) { o[k] = LOOK_COLOR[k]; });
    Object.keys(LOOK_BOOL).forEach(function (k) { o[k] = LOOK_BOOL[k]; });
    Object.keys(LOOK_ENUM).forEach(function (k) { o[k] = LOOK_ENUM[k][1]; });
    return o;
  }
  // Chuẩn hoá: khoá thiếu hay sai kiểu thì về mặc định, số kẹp vào khoảng, màu chỉ nhận
  // "#rrggbb" (đi thẳng vào shader), bool phải là bool thật ("false" dạng chuỗi không tính).
  function normLook(o) {
    o = (o && typeof o === "object") ? o : {};
    var out = lookDefault();
    Object.keys(LOOK_NUM).forEach(function (k) {
      var v = o[k], d = LOOK_NUM[k];
      v = typeof v === "number" ? v : (typeof v === "string" && v.trim() ? +v : NaN);
      if (isFinite(v)) out[k] = Math.round(clamp(v, d[0], d[1]) * 1000) / 1000;
    });
    Object.keys(LOOK_COLOR).forEach(function (k) {
      if (typeof o[k] === "string" && /^#[0-9a-f]{6}$/i.test(o[k])) out[k] = o[k].toLowerCase();
    });
    Object.keys(LOOK_BOOL).forEach(function (k) { if (typeof o[k] === "boolean") out[k] = o[k]; });
    Object.keys(LOOK_ENUM).forEach(function (k) { if (LOOK_ENUM[k][0].indexOf(o[k]) >= 0) out[k] = o[k]; });
    return out;
  }
  function hexRGB(h) { return [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255]; }
  // Giá trị suy ra (màu dạng số, pha trăng tự chỉnh) tính MỘT lần khi đổi, không mỗi khung.
  function deriveLook(L) {
    var pal = PALETTES[L.palette];
    if (!pal) {   // "custom": đáy biển = màu biển hạ tối, điểm nhấn = viền sáng pha trắng
      var s = hexRGB(L.seaColor), r = hexRGB(L.rimColor);
      pal = { deep: [s[0] * 0.1, s[1] * 0.1, s[2] * 0.14 + 0.01], sea: s, rim: r,
              mint: [r[0] * 0.6 + 0.4, r[1] * 0.6 + 0.4, r[2] * 0.6 + 0.4] };
    }
    // Tự chỉnh: moonFull là PHẦN SÁNG (0 = trăng non, 1 = tròn) -> pha trăng đầu tháng tương ứng,
    // ngược với illum = (1 - cos 2πp) / 2 của moonPhase().
    var mp = L.moonMode === "manual" ? Math.acos(clamp(1 - 2 * L.moonFull, -1, 1)) / (2 * Math.PI) : null;
    return { sun: hexRGB(L.sunColor), pal: pal, moonP: mp };
  }
  function readLook() { try { return JSON.parse(localStorage.getItem(LOOK_KEY) || "null"); } catch (e) { return null; } }
  var look = normLook(readLook()), LD = deriveLook(look);
  function getLook() { return JSON.parse(JSON.stringify(look)); }
  // patch: khoá muốn đổi. opt.replace: thay cả bộ (khoá vắng về mặc định) - dùng cho cảnh dựng
  // sẵn, nút Đặt lại và lúc hoà bản của máy chủ.
  function setLook(patch, opt) {
    opt = opt || {};
    look = normLook(Object.assign({}, opt.replace ? {} : look, patch || {}));
    LD = deriveLook(look);
    try { localStorage.setItem(LOOK_KEY, JSON.stringify(look)); } catch (e) {}
    try { window.dispatchEvent(new Event("joyce:planet-look")); } catch (e) {}
    return getLook();
  }

  // ---------------------------------------------------------------------------
  // BỀ MẶT MẶT TRĂNG (chủ yêu cầu 2026-10-07): phần tối của trăng không còn là đĩa đen phẳng mà
  // hiện bề mặt lồi lõm, được ÁNH ĐẤT (earthshine - ánh Trái Đất hắt lên) soi mờ như ngoài đời;
  // các biển tối (maria) xếp thành hình CHÚ CUỘI NGỒI GỐC CÂY ĐA như tranh dân gian Việt Nam.
  // Dựng MỘT lần bản đồ 256² (độ phản xạ + độ dốc lồi lõm), hoàn toàn bằng toán (không canvas)
  // nên chạy được cả trong test. Lúc vẽ chỉ chiếu sáng lại theo pha + hướng nắng (moonPixels).
  // Toạ độ: đĩa trăng là vòng tròn đơn vị, u sang phải, v xuống dưới, Bắc ở trên. Mặt trăng luôn
  // ĐỨNG THẲNG (khoá thuỷ triều: luôn quay một mặt về Trái Đất) - chỉ phần sáng xoay theo nắng.
  // ---------------------------------------------------------------------------
  // Biển tối: ["C", u, v, r, độ đậm] tròn; ["E", u, v, rx, ry, đậm] elip; ["L", [[u,v]...], bề rộng, đậm] nét.
  var MARIA = [
    // tán cây đa (rộng, nhiều chùm lá)
    ["C", -0.05, -0.5, 0.28, 0.92], ["C", 0.25, -0.45, 0.22, 0.9], ["C", -0.32, -0.4, 0.2, 0.9],
    ["C", 0.42, -0.25, 0.16, 0.86], ["C", -0.45, -0.18, 0.13, 0.84], ["C", 0.1, -0.25, 0.2, 0.92],
    ["C", -0.18, -0.25, 0.16, 0.9], ["C", 0.0, -0.72, 0.16, 0.84], ["C", 0.3, -0.68, 0.12, 0.8],
    ["C", -0.3, -0.65, 0.12, 0.8], ["C", 0.52, -0.5, 0.1, 0.78],
    // thân cây + rễ toả ở gốc + rễ phụ buông từ tán
    ["L", [[0.08, -0.2], [0.06, 0.1], [0.1, 0.35], [0.1, 0.55]], 0.13, 0.95],
    ["L", [[0.1, 0.52], [-0.02, 0.6], [-0.14, 0.67]], 0.05, 0.85], ["L", [[0.12, 0.54], [0.25, 0.6], [0.37, 0.67]], 0.05, 0.85],
    ["L", [[0.1, 0.55], [0.13, 0.71]], 0.04, 0.8],
    ["L", [[-0.4, -0.1], [-0.39, 0.08]], 0.022, 0.6], ["L", [[-0.29, -0.06], [-0.28, 0.06]], 0.02, 0.55],
    ["L", [[0.3, -0.08], [0.31, 0.12]], 0.022, 0.6], ["L", [[0.43, -0.1], [0.44, 0.04]], 0.02, 0.55],
    // chú Cuội ngồi dựa gốc cây, quay mặt sang trái, gối co, tay gác lên gối
    ["C", -0.13, 0.19, 0.062, 0.96],
    ["L", [[-0.11, 0.26], [-0.1, 0.36], [-0.09, 0.45]], 0.1, 0.95],
    ["L", [[-0.09, 0.45], [-0.29, 0.37]], 0.076, 0.95],
    ["L", [[-0.29, 0.37], [-0.31, 0.56]], 0.066, 0.95],
    ["L", [[-0.11, 0.3], [-0.22, 0.37], [-0.28, 0.34]], 0.046, 0.9],
    // các biển khác giữ dáng Mặt Trăng thật (Nguy Hiểm, Phì Nhiêu, Mật Hoa, Bão Tố, Ẩm Ướt)
    ["C", 0.7, -0.25, 0.1, 0.85], ["C", 0.6, 0.15, 0.11, 0.7], ["C", 0.42, 0.36, 0.07, 0.6],
    ["E", -0.72, 0.05, 0.2, 0.38, 0.45], ["C", -0.5, 0.5, 0.07, 0.55],
  ];
  // Hố có tia sáng toả (u, v, r, độ sáng tia): Tycho phía Nam, Copernicus, Kepler.
  var RAY_CRATERS = [[-0.13, 0.82, 0.045, 1], [-0.33, -0.08, 0.05, 0.7], [-0.55, -0.05, 0.025, 0.5]];
  var MOON_N = 200, moonMap = null;
  // Hộp bao của từng biển tối (đã nới mép mềm): điểm nằm ngoài hộp thì khỏi tính khoảng cách.
  var MARIA_BB = MARIA.map(function (s) {
    var e = 0.035;
    if (s[0] === "C") return [s[1] - s[3] - e, s[1] + s[3] + e, s[2] - s[3] - e, s[2] + s[3] + e];
    if (s[0] === "E") return [s[1] - s[3] - e, s[1] + s[3] + e, s[2] - s[4] - e, s[2] + s[4] + e];
    var us = s[1].map(function (q) { return q[0]; }), vs = s[1].map(function (q) { return q[1]; }), w = s[2] / 2 + e;
    return [Math.min.apply(null, us) - w, Math.max.apply(null, us) + w, Math.min.apply(null, vs) - w, Math.max.apply(null, vs) + w];
  });
  function mrand(seed) { var s = seed >>> 0; return function () { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
  function hash2(x, y) { var h = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return h - Math.floor(h); }
  function vnoise2(x, y) {
    var ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
    var a = hash2(ix, iy), b = hash2(ix + 1, iy), c = hash2(ix, iy + 1), d = hash2(ix + 1, iy + 1);
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
  }
  function fbm2(x, y, o) {
    var s = 0, a = 0.5, t = 0;
    for (var i = 0; i < o; i++) { s += a * vnoise2(x, y); t += a; x = x * 2.03 + 17.1; y = y * 2.03 + 9.7; a *= 0.5; }
    return s / t;
  }
  function segDist(u, v, a, b) {
    var dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy || 1e-9;
    var t = clamp(((u - a[0]) * dx + (v - a[1]) * dy) / l2, 0, 1);
    return Math.hypot(u - a[0] - dx * t, v - a[1] - dy * t);
  }
  // Độ phủ biển tối tại (u, v): hợp các hình, mép mềm, cộng các khoảng hở như kẽ lá ở tán cây.
  function mariaAt(u, v, holes) {
    var m = 0, e = 0.03;
    for (var i = 0; i < MARIA.length; i++) {
      var s = MARIA[i], bb = MARIA_BB[i], d;
      if (u < bb[0] || u > bb[1] || v < bb[2] || v > bb[3] || s[s.length - 1] <= m) continue;
      if (s[0] === "C") d = Math.hypot(u - s[1], v - s[2]) - s[3];
      else if (s[0] === "E") d = (Math.hypot((u - s[1]) / s[3], (v - s[2]) / s[4]) - 1) * Math.min(s[3], s[4]);
      else {
        d = 9;
        for (var j = 1; j < s[1].length; j++) d = Math.min(d, segDist(u, v, s[1][j - 1], s[1][j]));
        d -= s[2] / 2;
      }
      var cov = (1 - smooth(-e, e, d)) * s[s.length - 1];
      if (cov > m) m = cov;
    }
    if (holes && m > 0) {
      for (var h = 0; h < holes.length; h++) {
        var q = holes[h], dh = Math.hypot(u - q[0], v - q[1]) - q[2];
        if (dh < e) m *= 1 - 0.45 * (1 - smooth(-e, e, dh));
      }
    }
    return m;
  }
  function buildMoonMap() {
    var N = MOON_N, rnd = mrand(20261007), i, x, y;
    var holes = [];
    for (i = 0; i < 24; i++) holes.push([-0.55 + rnd() * 1.1, -0.85 + rnd() * 0.75, 0.025 + rnd() * 0.025]);
    var craters = [];
    RAY_CRATERS.forEach(function (c) { craters.push([c[0], c[1], c[2]]); });
    for (i = 0; i < 90 && craters.length < 48; i++) {   // hố ngẫu nhiên: nhiều hố nhỏ, ít hố to
      var a = rnd() * 6.2832, rr = Math.sqrt(rnd()) * 0.96, cu = Math.cos(a) * rr, cv = Math.sin(a) * rr;
      var r0 = 0.01 + 0.06 * Math.pow(rnd(), 2.5);
      if (mariaAt(cu, cv, null) > 0.5 && rnd() > 0.35) continue;    // biển tối trẻ hơn, ít hố
      craters.push([cu, cv, r0]);
    }
    var rays = RAY_CRATERS.map(function (c, k) {
      var list = [], n = k === 0 ? 14 : 9;
      for (var j = 0; j < n; j++) list.push([rnd() * 6.2832, (k === 0 ? 0.25 : 0.1) + rnd() * (k === 0 ? 0.3 : 0.14), 0.014 + rnd() * 0.014]);
      return list;
    });
    var M = new Float32Array(N * N), A = new Float32Array(N * N), H = new Float32Array(N * N);
    for (y = 0; y < N; y++) for (x = 0; x < N; x++) {
      var u = (x + 0.5) / N * 2 - 1, v = (y + 0.5) / N * 2 - 1, o = y * N + x;
      if (u * u + v * v > 1.08) continue;
      // Uốn méo toạ độ bằng nhiễu trước khi tra hình: mép biển tối lượn sóng tự nhiên, tán lá
      // không còn là các đĩa tròn chồng lên nhau.
      var wu = u + 0.07 * (fbm2(u * 4.5 + 11, v * 4.5, 3) - 0.5), wv = v + 0.07 * (fbm2(u * 4.5, v * 4.5 + 23, 3) - 0.5);
      var m = mariaAt(wu, wv, holes);
      m = clamp(m * (0.88 + 0.3 * (fbm2(u * 7 + 3, v * 7, 3) - 0.5)), 0, 1);
      var high = 0.66 + 0.16 * (fbm2(u * 6, v * 6, 4) - 0.5);
      var mare = 0.3 + 0.08 * (fbm2(u * 9 + 5, v * 9, 3) - 0.5);
      var alb = high + (mare - high) * m;
      var hgt = 0.006 * (fbm2(u * 22, v * 22, 3) - 0.5) * (1 - 0.7 * m);
      for (var c = 0; c < craters.length; c++) {
        var cr = craters[c], dx = u - cr[0], dy = v - cr[1];
        if (Math.abs(dx) > cr[2] * 1.7 || Math.abs(dy) > cr[2] * 1.7) continue;
        var dd = Math.hypot(dx, dy) / cr[2];
        if (dd < 1) { hgt -= 0.45 * cr[2] * (1 - dd * dd); alb -= 0.02; }
        hgt += 0.18 * cr[2] * Math.exp(-Math.pow((dd - 1) / 0.25, 2));
        alb += 0.035 * Math.exp(-Math.pow((dd - 1) / 0.2, 2));
      }
      for (var k = 0; k < RAY_CRATERS.length; k++) {   // tia sáng toả từ hố trẻ
        var rc = RAY_CRATERS[k], rx = u - rc[0], ry = v - rc[1], dist = Math.hypot(rx, ry);
        if (dist < rc[2]) { alb += 0.08 * rc[3]; continue; }
        var ang = Math.atan2(ry, rx), sum = 0;
        for (var j = 0; j < rays[k].length; j++) {
          var R = rays[k][j], da = Math.abs(((ang - R[0] + 9.42478) % 6.28319) - 3.14159);
          sum += Math.exp(-Math.pow(da * dist / R[2], 2)) * Math.exp(-(dist - rc[2]) / R[1]);
        }
        alb += 0.1 * rc[3] * Math.min(1, sum) + 0.07 * rc[3] * Math.exp(-(dist - rc[2]) / 0.08);
      }
      M[o] = m; A[o] = clamp(alb, 0.08, 1); H[o] = hgt;
    }
    var GX = new Float32Array(N * N), GY = new Float32Array(N * N), sc = N / 4;
    for (y = 1; y < N - 1; y++) for (x = 1; x < N - 1; x++) {
      var p0 = y * N + x;
      GX[p0] = (H[p0 + 1] - H[p0 - 1]) * sc;
      GY[p0] = (H[p0 + N] - H[p0 - N]) * sc;
    }
    return { N: N, M: M, A: A, GX: GX, GY: GY };
  }
  // Dựng bản đồ lúc trình duyệt RẢNH (~170ms một lần): dựng ngay giữa khung hình là quả cầu
  // khựng một nhịp. Chưa xong thì drawMoonDisc vẽ đĩa phẳng kiểu cũ. Hỏng thì thôi, không thử lại.
  var moonMapPending = false, moonMapFailed = false;
  function scheduleMoonMap() {
    if (moonMap || moonMapPending || moonMapFailed) return;
    moonMapPending = true;
    var run = function () {
      try { moonMap = moonMap || buildMoonMap(); } catch (e) { moonMapFailed = true; }
      moonMapPending = false;
    };
    if (window.requestIdleCallback) window.requestIdleCallback(run, { timeout: 1500 });
    else setTimeout(run, 60);
  }
  // Chiếu sáng đĩa trăng res x res (RGBA). p = pha (0 non, 0,5 tròn), rot = góc màn hình tới Mặt
  // Trời, glow = thanh Độ sáng trăng, col = màu trăng (đổi theo sức khoẻ dự án). Phần sáng theo
  // nắng (Lambert dịu, ranh ngày đêm mềm); phần tối là ánh đất xanh nhạt chiếu xiên từ trên-trái
  // để vành hố vẫn nổi khối. Ánh đất mạnh nhất lúc trăng non (Trái Đất "tròn" nhất khi nhìn từ trăng).
  function moonPixels(res, p, rot, glow, col) {
    var mm = moonMap || (moonMap = buildMoonMap());
    var N = mm.N, out = new Uint8ClampedArray(res * res * 4);
    var ph = 2 * Math.PI * p, side = 1;
    var Lx = side * Math.sin(ph), Lz = -Math.cos(ph), cr = Math.cos(rot || 0), sr = Math.sin(rot || 0);
    var lx = Lx * cr, ly = Lx * sr, lz = Lz;
    var illum = (1 - Math.cos(ph)) / 2, g1 = Math.min(glow, 1), g2 = Math.max(0, glow - 1);
    var sunK = 1.12 * (0.3 + 0.7 * g1) + 0.35 * g2;
    var es = (0.1 + 0.14 * (1 - illum)) * (0.45 + 0.55 * g1 + 0.25 * g2);
    var tr = (0.65 * 255 + 0.35 * col[0]) / 255, tg = (0.65 * 250 + 0.35 * col[1]) / 255, tb = (0.65 * 238 + 0.35 * col[2]) / 255;
    var ex = -0.32, ey = -0.38, ez = 0.868, BUMP = 0.9;
    // Bề mặt trăng phản xạ kiểu Lommel-Seeliger (2·μ0/(μ0+μ)): trăng tròn sáng đều tới tận mép
    // như ngoài đời, không tối dần ra rìa như quả bóng nhựa (Lambert).
    for (var y = 0; y < res; y++) {
      var v = (y + 0.5) / res * 2 - 1, iy = Math.min(N - 1, ((v + 1) * 0.5 * N) | 0) * N;
      for (var x = 0; x < res; x++) {
        var u = (x + 0.5) / res * 2 - 1, d2 = u * u + v * v;
        var edge = (1 - Math.sqrt(d2)) * res / 2 + 0.5;
        if (edge <= 0) continue;
        var z = Math.sqrt(Math.max(0, 1 - d2)), ti = iy + Math.min(N - 1, ((u + 1) * 0.5 * N) | 0);
        var A = mm.A[ti] || 0.5;
        var nx = u - mm.GX[ti] * BUMP, ny = v - mm.GY[ti] * BUMP, nz = z, nl = Math.hypot(nx, ny, nz) || 1;
        nx /= nl; ny /= nl; nz /= nl;
        var term = smooth(-0.06, 0.1, u * lx + v * ly + z * lz);
        var mu0 = nx * lx + ny * ly + nz * lz, mu = Math.max(0.05, nz);
        var sun = mu0 > 0 ? Math.min(1.4, 2 * mu0 / (mu0 + mu)) * term * sunK : 0;
        // Ánh đất: phẳng như trăng tròn mờ, cộng độ NỔI KHỐI của riêng vành/lòng hố (chênh giữa
        // pháp tuyến lồi lõm và pháp tuyến cầu) để phần tối vẫn đọc ra bề mặt gồ ghề.
        var rel = 1 + 2.5 * ((nx * ex + ny * ey + nz * ez) - (u * ex + v * ey + z * ez));
        var earth = es * clamp(rel, 0.3, 1.8);
        var o = (y * res + x) * 4;
        out[o] = 255 * Math.pow(Math.min(1, A * (sun * tr + earth * 0.6)), 0.85);
        out[o + 1] = 255 * Math.pow(Math.min(1, A * (sun * tg + earth * 0.72)), 0.85);
        out[o + 2] = 255 * Math.pow(Math.min(1, A * (sun * tb + earth * 1.0)), 0.85);
        out[o + 3] = 255 * Math.min(1, edge);
      }
    }
    return out;
  }

  // ---------------------------------------------------------------------------
  // RENDERER (BrainRenderer)
  // ---------------------------------------------------------------------------
  function create(opts) {
    opts = opts || {};
    var R = {};                     // đối tượng trả về
    var host = null, glCv = null, ovCv = null, tip = null;
    var gl = null, prog = null, progHi = null, buf = null, vao = null;
    var ctx2 = null;
    var W = 0, H = 0, dprGL = 1, dprOv = 1;
    var raf = 0, running = false, paused = false, destroyed = false;
    var profile = "high", requested = null;
    var reducedMQ = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    var listeners = [];
    var ro = null;
    var t0 = performance.now(), simT = 0, flowT = 0, lastNow = 0;
    var state = "READY", stateAt = performance.now();
    var cur = TARGET.READY.slice();
    var amp = 0, ampS = 0, hover = 0, hoverT = 0;
    var projects = [], sats = [], hoverSat = null, labelSide = {};
    var cam = { yaw: 0, pitch: 0, zoom: 1, tyaw: 0, tpitch: 0, tzoom: 1 };
    var par = { x: 0, y: 0, tx: 0, ty: 0 };
    var geo = { cx: 0, cy: 0, R: 0 };
    var drag = null, clickTimer = 0;
    var particles = [], swirl = [], glyphs = [], nextGlyph = 0;
    var fpsWin = [], lowWins = 0, fpsSkipUntil = performance.now() + 1500;
    var inCall = false, callK = 0;  // callK 0..1: tinh cầu hạ xuống làm nền cho khung hologram
    var sun = null, moon = null;    // H2O Legacy = mặt trời; một dự án = mặt trăng (role từ hud.js)
    var Gm = viewMat(VIEW_HOME.lat, VIEW_HOME.lon);
    var sunG = sunGeo(new Date()), moonG = moonGeo(new Date()), orbitG = moonOrbit(new Date()), astroAt = 0;
    var vnTex = null, vnOn = false;
    var wx = { cur: WX.nang_nhe.slice(), tgt: WX.nang_nhe.slice(), center: VN_CENTER, sigma: 0.3,
               flash: 0, nextFlash: 0, flash2: 0, key: "nang_nhe" };
    var ing = { on: false, k: 0, items: [], parts: [], beam: 0, nextSpawn: 0, wasOn: false, nameIdx: 0 };
    var moonPh = moonPhase(new Date()), moonPhAt = performance.now();
    var light = false;
    // Hiệu ứng bật/tắt của tab Quả tinh cầu: cường độ 0..1 trôi mềm về công tắc (bật/tắt không
    // giật). windT = pha gió tích luỹ: gió mạnh làm mây trôi nhanh hơn mà không nhảy cóc.
    var FX_KEYS = ["rain", "lightning", "wind", "tornado", "eruption", "orbits", "knowledge"];
    var fx = { rain: 0, lightning: 0, wind: 0, tornado: 0, eruption: 0, orbits: look.orbits ? 1 : 0,
               knowledge: look.knowledge ? 1 : 0 };
    var windT = 0;
    var cells = [], splashes = [], streaks = [], bolts = [], bolt = { g: [0, 1, 0], k: 0 };
    var rcBuf = new Float32Array(16);   // 4 ô bão -> uniform uRc
    var cellSeq = 0;
    var hot = [];      // hạt nóng: tia lửa sét (toạ độ địa lý)
    var torn = { g: null, head: null, t: 0, parts: [], zaps: [], nz: 0, flash: 0, sz: 1, hk: 1 };

    function on(el, ev, fn, o) { el.addEventListener(ev, fn, o); listeners.push([el, ev, fn, o]); }

    // ---------- chất lượng ----------
    function pickProfile() {
      var forced = requested;
      if (!forced) { try { forced = localStorage.getItem(QKEY); } catch (e) {} }
      if (reducedMQ && reducedMQ.matches) return "reduced";
      if (!flagOn()) return "safe";            // cờ tắt = bản nhẹ Canvas 2D, không shader
      if (forced && /^(high|balanced|safe|reduced)$/.test(forced)) return forced;
      var mem = navigator.deviceMemory || 8;
      var cores = navigator.hardwareConcurrency || 8;
      return (mem < 4 || cores < 4) ? "balanced" : "high";
    }
    function wantsGL(p) { return p === "high" || p === "balanced" || p === "reduced"; }

    function initGL() {
      if (gl) return true;
      try {
        gl = glCv.getContext("webgl2", { alpha: true, premultipliedAlpha: true, antialias: false,
          depth: false, stencil: false, powerPreference: "high-performance", preserveDrawingBuffer: false });
      } catch (e) { gl = null; }
      if (!gl) return false;
      try {
        prog = makeProgram(gl, false);
        progHi = null;               // biên dịch lười: chỉ khi cần hồ sơ high
        vao = gl.createVertexArray();
        gl.bindVertexArray(vao);
        buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
        buildVNTexture();
        return true;
      } catch (e) {
        try { console.warn("[planet] WebGL lỗi, về Canvas 2D:", e && e.message); } catch (_) {}
        freeGL();
        return false;
      }
    }
    // Bản đồ Việt Nam -> texture RGBA 1024² trên khung kinh/vĩ (equirectangular) của vùng
    // window.JoyceVNGeo.bbox: R = nền đất liền, G = viền phát sáng, B = đèn đô thị,
    // A = Hoàng Sa + Trường Sa. Dựng một lần lúc có WebGL; shader tra theo kinh/vĩ từng điểm.
    function buildVNTexture() {
      var G = window.JoyceVNGeo;
      if (!G || !gl) return;
      try {
        var N = 1024, bb = G.bbox;
        var X = function (lon) { return (lon - bb[0]) / (bb[2] - bb[0]) * N; };
        var Y = function (lat) { return (bb[3] - lat) / (bb[3] - bb[1]) * N; };
        var mk = function () { var c = document.createElement("canvas"); c.width = c.height = N; return c.getContext("2d"); };
        var path = function (c, poly) {
          c.beginPath();
          poly.forEach(function (pt, i) { if (i) c.lineTo(X(pt[0]), Y(pt[1])); else c.moveTo(X(pt[0]), Y(pt[1])); });
          c.closePath();
        };
        var polys = [G.main].concat(G.islands || []);
        var f = mk(); f.fillStyle = "#fff"; polys.forEach(function (pl) { path(f, pl); f.fill(); });
        var e = mk(); e.strokeStyle = "#fff"; e.lineJoin = "round"; e.shadowColor = "#fff";
        e.shadowBlur = 14; e.lineWidth = 3; polys.forEach(function (pl) { path(e, pl); e.stroke(); });
        e.shadowBlur = 0; e.lineWidth = 1.6; polys.forEach(function (pl) { path(e, pl); e.stroke(); });
        var c3 = mk();
        (G.cities || []).forEach(function (ct) {
          var x = X(ct[1]), y = Y(ct[2]), r = 6 + 16 * ct[3];
          var gr = c3.createRadialGradient(x, y, 0, x, y, r);
          gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.25, "rgba(255,255,255,.55)"); gr.addColorStop(1, "rgba(255,255,255,0)");
          c3.fillStyle = gr; c3.beginPath(); c3.arc(x, y, r, 0, 6.2832); c3.fill();
        });
        var c4 = mk(); c4.fillStyle = "#fff"; c4.shadowColor = "#fff"; c4.shadowBlur = 8;
        [G.hoangSa || [], G.truongSa || []].forEach(function (grp) {
          grp.forEach(function (pt) { c4.beginPath(); c4.arc(X(pt[0]), Y(pt[1]), 3.2, 0, 6.2832); c4.fill(); });
          if (!grp.length) return;
          // vành nét đứt ôm quanh quần đảo để mắt nhận ra là một cụm, không phải bụi sao
          var xs = grp.map(function (p) { return X(p[0]); }), ys = grp.map(function (p) { return Y(p[1]); });
          var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
          c4.save(); c4.shadowBlur = 0; c4.strokeStyle = "rgba(255,255,255,.6)"; c4.lineWidth = 1.4; c4.setLineDash([7, 7]);
          c4.beginPath(); c4.ellipse((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 + 16, (y1 - y0) / 2 + 16, 0, 0, 6.2832); c4.stroke();
          c4.restore();
        });
        var a = f.getImageData(0, 0, N, N).data, b = e.getImageData(0, 0, N, N).data;
        var c = c3.getImageData(0, 0, N, N).data, d = c4.getImageData(0, 0, N, N).data;
        var u8 = new Uint8Array(N * N * 4);
        for (var i = 0, j = 3; i < u8.length; i += 4, j += 4) { u8[i] = a[j]; u8[i + 1] = b[j]; u8[i + 2] = c[j]; u8[i + 3] = d[j]; }
        vnTex = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, vnTex);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, N, N, 0, gl.RGBA, gl.UNSIGNED_BYTE, u8);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        vnOn = true;
      } catch (err) {
        vnOn = false;
        try { console.warn("[planet] bản đồ Việt Nam lỗi:", err && err.message); } catch (_) {}
      }
    }
    function freeGL() {
      if (!gl) return;
      try {
        if (vnTex) gl.deleteTexture(vnTex);
        if (prog) gl.deleteProgram(prog.pr);
        if (progHi) gl.deleteProgram(progHi.pr);
        if (buf) gl.deleteBuffer(buf);
        if (vao) gl.deleteVertexArray(vao);
      } catch (e) {}
      prog = progHi = null; buf = vao = null; gl = null; vnTex = null; vnOn = false;
    }
    function applyProfile(p) {
      profile = p;
      if (!glCv || destroyed) return;          // chưa mount (hoặc đã huỷ): mount() sẽ áp lại
      if (wantsGL(p) && !initGL()) profile = "safe";
      if (profile === "high" && gl && !progHi) {
        try { progHi = makeProgram(gl, true); } catch (e) { profile = "balanced"; }
      }
      glCv.style.display = (gl && profile !== "safe") ? "block" : "none";
      buildParticles();
      resize();
      if (host) host.dataset.quality = profile;
    }

    // ---------- kích thước + camera tự canh ----------
    function layout() {
      var insets = (opts.insets && opts.insets()) || { left: 0, right: 0, top: 0, bottom: 0 };
      var availW = Math.max(120, W - insets.left - insets.right);
      var availH = Math.max(120, H - (insets.top || 0) - (insets.bottom || 0));
      // Đường kính tinh cầu ~41% chiều cao khoang (= 54% phần còn lại sau công tắc trên và
      // nhãn trạng thái dưới), nhưng vành quỹ đạo ngoài cùng (1.92R) cộng chỗ cho nhãn
      // (~84px) phải lọt giữa hai cột telemetry.
      var byH = availH * 0.27;
      // Nhãn tự kẹp vào trong khung (drawLabels) nên chỉ chừa ~40px mỗi bên. Sàn 17% chiều
      // cao: khoang hẹp (cột hội thoại bung rộng) vẫn không ra "hòn bi" như quả cầu cũ.
      var byW = (availW / 2 - (W < 600 ? 30 : 40)) / 1.92;
      var base = Math.max(46, Math.min(byH, Math.max(byW, availH * 0.17)));
      geo.base = base;
      // Đang gọi: tinh cầu thu nhỏ một chút và HẠ xuống, nhường nửa trên cho khung hologram.
      geo.R = base * cam.zoom * (1 - 0.22 * callK);
      geo.cx = insets.left + availW / 2 + par.x * 6;
      geo.cy = (insets.top || 0) + availH * (0.47 + 0.19 * callK) + par.y * 4;
      // Mặt trời ở trên-trái tinh cầu (đúng hướng ánh sáng chính), không lấn cột telemetry
      // trái, cách tâm hành tinh tối thiểu 1.9R để quầng không đè lên vành quỹ đạo trong.
      // Góc nhìn địa lý: mặc định thấy trọn Việt Nam, phóng gần thì trôi về Hải Phòng; kéo chuột
      // xoay quả cầu tự do (yaw = kinh độ, pitch = vĩ độ).
      var n1 = smooth(1.4, 3.2, cam.zoom), n2 = smooth(4.5, 9, cam.zoom);
      var vlat = VIEW_HOME.lat + (VIEW_VN.lat - VIEW_HOME.lat) * n1 + (VIEW_NEAR.lat - VIEW_VN.lat) * n2 + cam.pitch * 57.3;
      var vlon = VIEW_HOME.lon + (VIEW_VN.lon - VIEW_HOME.lon) * n1 + (VIEW_NEAR.lon - VIEW_VN.lon) * n2 - cam.yaw * 57.3;
      Gm = viewMat(clamp(vlat, -75, 75), vlon);
      // Mặt Trời theo GIỜ THẬT: hướng sáng trong khung nhìn. Đĩa Mặt Trời đứng trên một vòng
      // quanh Trái Đất theo đúng góc đó; đêm ở Việt Nam thì nó lùi ra SAU quả cầu (quầng ló
      // quanh mép), ngày thì ra cạnh khung. Cỡ đĩa không theo zoom - Mặt Trời ở rất xa.
      var Lv = toView(Gm, sunG);
      geo.L = Lv;
      var sdx = Lv[0], sdy = -Lv[1], sl = Math.hypot(sdx, sdy);
      if (sl < 1e-3) { sdx = -0.7; sdy = -0.7; sl = 0.99; }
      var sr = base * 0.22 * look.sunSize;
      var sdist = geo.R * (0.92 + 1.58 * smooth(-0.95, 0.05, Lv[2]));
      var top = insets.top || 0, bot = insets.bottom || 0;
      geo.sun = { x: clamp(geo.cx + sdx / sl * sdist, insets.left + sr * 1.6, W - insets.right - sr * 1.6),
                  y: clamp(geo.cy + sdy / sl * sdist, top + sr * 1.4, H - bot - sr * 0.6), r: sr };
      geo.moonV = toView(Gm, moonG);
      // Ngân Hà rõ dần khi lùi xa; hố đen ở góc trên-phải, xa hẳn tinh cầu.
      geo.gal = 1 - smooth(0.42, 1.0, cam.zoom);
      geo.bh = { x: insets.left + availW * 0.86, y: top + availH * 0.15,
                 r: base * (0.085 + 0.08 * geo.gal) * (1 + 0.18 * ing.k) };
    }
    function resize() {
      if (!host || destroyed) return;
      var r = host.getBoundingClientRect();
      W = Math.round(r.width); H = Math.round(r.height);
      if (!W || !H) return;
      var dpr = window.devicePixelRatio || 1;
      dprOv = Math.min(dpr, 2);
      dprGL = Math.min(dpr, profile === "high" ? 2 : 1.25);
      // Trần số điểm ảnh: shader chạy trên TOÀN khoang não, màn 4K x dpr 2 thì quá tay.
      var maxPx = profile === "high" ? 2.6e6 : 1.4e6;
      if (W * H * dprGL * dprGL > maxPx) dprGL = Math.sqrt(maxPx / (W * H));
      glCv.width = Math.max(1, Math.round(W * dprGL)); glCv.height = Math.max(1, Math.round(H * dprGL));
      ovCv.width = Math.max(1, Math.round(W * dprOv)); ovCv.height = Math.max(1, Math.round(H * dprOv));
      glCv.style.width = ovCv.style.width = W + "px";
      glCv.style.height = ovCv.style.height = H + "px";
      ctx2.setTransform(dprOv, 0, 0, dprOv, 0, 0);
      // Khung đổi cỡ thì tâm hành tinh dời đi: quên vị trí màn hình cũ của hạt nóng, không thì
      // khung kế vẽ một vệt dài từ chỗ cũ tới chỗ mới.
      for (var hi = 0; hi < hot.length; hi++) hot[hi].sx = hot[hi].sy = null;
      layout();
      if (paused || !running) frame(performance.now(), true);   // vẽ lại một khung cho đúng cỡ
    }

    // ---------- quỹ đạo 3D ----------
    var RINGS = [
      { k: 1.42, incl: 1.20, roll: -0.20, col: PAL.cyan },
      { k: 1.66, incl: 1.07, roll: 0.17, col: PAL.mint },
      { k: 1.92, incl: 1.31, roll: -0.06, col: PAL.violet },
    ];
    // Điểm góc a trên vành i -> toạ độ màn hình + độ sâu z (>0 là phía trước hành tinh).
    function ringPt(i, a) {
      var g = RINGS[i], Rr = geo.R * g.k * look.orbitSize;
      var x = Math.cos(a) * Rr, y0 = Math.sin(a) * Rr;
      var y = y0 * Math.cos(g.incl), z = -y0 * Math.sin(g.incl);
      var cr = Math.cos(g.roll), sr = Math.sin(g.roll);
      var x2 = x * cr - y * sr, y2 = x * sr + y * cr;
      // xoay camera (kéo chuột): yaw quanh trục đứng, pitch quanh trục ngang
      var cyw = Math.cos(cam.yaw), syw = Math.sin(cam.yaw);
      var x3 = x2 * cyw + z * syw, z3 = -x2 * syw + z * cyw;
      var cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
      var y3 = y2 * cp - z3 * sp, z4 = y2 * sp + z3 * cp;
      var sx = geo.cx + x3, sy = geo.cy - y3;
      var dx = sx - geo.cx, dy = sy - geo.cy;
      var hidden = z4 < 0 && (dx * dx + dy * dy) < geo.R * geo.R * 0.985;
      return { x: sx, y: sy, z: z4 / Rr, hidden: hidden };
    }

    function buildParticles() {
      var per = profile === "high" ? 24 : profile === "balanced" ? 14 : profile === "safe" ? 8 : 0;
      particles = [];
      for (var i = 0; i < 3; i++) for (var j = 0; j < per; j++) {
        particles.push({ ring: i, a: Math.random() * 6.283, sp: (0.05 + Math.random() * 0.09) * (i % 2 ? -1 : 1), s: 0.6 + Math.random() * 0.9 });
      }
      swirl = [];
      var sw = profile === "high" ? 34 : profile === "balanced" ? 18 : 0;
      for (var k = 0; k < sw; k++) swirl.push({ a: Math.random() * 6.283, r: 1.06 + Math.random() * 0.3, sp: 0.6 + Math.random() * 0.9, ph: Math.random() * 6.283, tilt: 0.25 + Math.random() * 0.35 });
    }

    // ---------- vệ tinh dự án ----------
    // role "sun"/"moon" do hud.js gán (Legacy = mặt trời, mặt trăng do chủ ghim hoặc tự đổi
    // theo tuần trăng). Hai thiên thể này KHÔNG bay trên ba vành dữ liệu.
    function body(p, kind, old) {
      if (!p) return null;
      var b = old && old.id === String(p.id || p.name) ? old : { glow: 0, a: 2.2 };
      b.id = String(p.id || p.name); b.p = p; b.name = p.name || b.id; b.kind = kind;
      b.status = p.status || "online"; b.rank = -1;
      b.col = kind === "sun" ? PAL.gold : [214, 224, 245];
      return b;
    }
    function syncSats() {
      sun = body(projects.filter(function (p) { return p.role === "sun"; })[0], "sun", sun);
      moon = body(projects.filter(function (p) { return p.role === "moon"; })[0], "moon", moon);
      var keep = {};
      sats.forEach(function (s) { keep[s.id] = s; });
      var cnt = [0, 0, 0];
      sats = projects.filter(function (p) { return p.role !== "sun" && p.role !== "moon"; }).map(function (p, i) {
        var id = String(p.id || p.name || i);
        var s = keep[id];
        if (!s) {
          var ring = cnt[0] <= cnt[1] ? (cnt[0] <= cnt[2] ? 0 : 2) : (cnt[1] <= cnt[2] ? 1 : 2);
          s = { id: id, ring: ring, a: (hashStr(id) % 628) / 100, sp: 0.045 + (hashStr(id + "v") % 30) / 1000,
                col: PAL[SAT_COLORS[hashStr(id) % SAT_COLORS.length]], glow: 0 };
        }
        cnt[s.ring]++;
        s.p = p; s.name = p.name || id; s.status = p.status || "online"; s.prio = i;
        return s;
      });
      // Điện thoại: chỉ giữ vệ tinh ưu tiên - app đang lỗi trước, rồi theo thứ tự registry.
      var order = sats.slice().sort(function (a, b) {
        var wa = a.status === "online" ? 1 : 0, wb = b.status === "online" ? 1 : 0;
        return wa - wb || a.prio - b.prio;
      });
      order.forEach(function (s, i) { s.rank = i; });
    }
    function satColor(s) {
      if (s.status === "offline") return [255, 72, 84];
      if (s.status === "unauthorized") return [255, 140, 70];
      if (s.status === "degraded") return PAL.gold;
      return s.col;
    }
    function satVisible(s) { return W >= 600 || s.rank < 4; }

    // Màu + độ sáng mặt trời theo sức khoẻ của H2O Legacy: app lỗi thì mặt trời lịm, ngả đỏ.
    // Màu và cường độ chủ chọn ở tab Quả tinh cầu là nền; tín hiệu sức khoẻ vẫn đè lên (một
    // Mặt Trời tím đang lịm vẫn phải đọc ra được là có sự cố, nên màu báo lỗi chiếm 70%).
    function sunLook() {
      var c0 = LD.sun, pw = look.sunPower, h = null;
      if (sun && sun.status === "offline") h = { k: 0.4, c: [0.9, 0.36, 0.26] };
      else if (sun && sun.status === "unauthorized") h = { k: 0.6, c: [1, 0.55, 0.28] };
      else if (sun && sun.status === "degraded") h = { k: 0.78, c: [1, 0.7, 0.3] };
      if (!h) return { k: pw, c: c0 };
      return { k: h.k * pw, c: [c0[0] * 0.3 + h.c[0] * 0.7, c0[1] * 0.3 + h.c[1] * 0.7, c0[2] * 0.3 + h.c[2] * 0.7] };
    }

    // ---------- mặt trăng ----------
    // Quỹ đạo riêng chéo (không cùng mặt phẳng với ba vành dữ liệu), pha lấy từ NGÀY THẬT.
    // Giờ thật: vector Mặt Trăng (khung nhìn) đặt ở 1,9R. Không còn tự chạy vòng theo hoạt ảnh.
    var MOON_K = 1.9;
    // Pha đang VẼ: theo lịch thật, hoặc pha chủ tự chỉnh ở tab Quả tinh cầu. Thông tin "pha
    // trăng hôm nay" ở ngăn kéo dự án (moonInfo) vẫn là pha thật.
    function moonShownPhase() { return LD.moonP != null ? LD.moonP : moonPh.phase; }
    function moonScreen(v) {
      return { x: geo.cx + v[0] * geo.R * MOON_K, y: geo.cy - v[1] * geo.R * MOON_K, z: v[2] };
    }
    // Vẽ đĩa trăng đúng pha: p=0 trăng mới, .5 trăng tròn; bán cầu Bắc nên trăng đầu tháng
    // sáng bên PHẢI. Vùng sáng = nửa đĩa phía sáng + đường phân ranh là elip có bán trục
    // ngang r*cos(2πp) - dương thì lõm vào (lưỡi liềm), âm thì phình ra (trăng gần tròn).
    // rot: góc (màn hình) hướng về Mặt Trời - phần sáng luôn quay về phía nắng thật.
    // gl: độ sáng trăng của tab Quả tinh cầu (0 = mờ hẳn, 1 = gốc, 2 = rực, quầng to gấp rưỡi).
    // Ảnh đĩa trăng đã chiếu sáng (moonPixels) giữ lại giữa các khung: chỉ dựng lại khi cỡ (bậc
    // 16px), pha, hướng nắng, độ sáng hoặc màu đổi đủ nhiều. Kéo xoay quả cầu làm hướng nắng đổi
    // liên tục, nên bậc góc 1/40 rad: đủ mịn cho mắt, không dựng lại mỗi khung.
    var moonCv = null, moonCx = null, moonKey = "";
    function moonImage(res, p, rot, gl, col) {
      var key = res + "|" + Math.round(p * 500) + "|" + Math.round(rot * 40) + "|" + Math.round(gl * 20) + "|" + col.join(",");
      if (moonCv && key === moonKey) return moonCv;
      if (!moonMap) { scheduleMoonMap(); return null; }
      try {
        if (!moonCv) { moonCv = document.createElement("canvas"); moonCx = moonCv.getContext("2d"); }
        if (!moonCx) return null;
        if (moonCv.width !== res) moonCv.width = moonCv.height = res;
        var img = moonCx.createImageData(res, res);
        img.data.set(moonPixels(res, p, Math.round(rot * 40) / 40, gl, col));
        moonCx.putImageData(img, 0, 0);
        moonKey = key;
        return moonCv;
      } catch (e) { return null; }
    }
    function drawMoonDisc(c, x0, y0, r, p, col, a, rot, gl) {
      var k = Math.cos(2 * Math.PI * p), side = 1;
      gl = gl == null ? 1 : gl;
      var gr = r * (2.6 + 1.3 * Math.max(0, gl - 1));
      var glow = c.createRadialGradient(x0, y0, r * 0.8, x0, y0, gr);
      glow.addColorStop(0, rgba(col, Math.min(0.6, 0.22 * a * gl * (0.25 + 0.75 * (1 - k) / 2))));
      glow.addColorStop(1, rgba(col, 0));
      c.fillStyle = glow; c.beginPath(); c.arc(x0, y0, gr, 0, 6.2832); c.fill();
      // Bề mặt thật (biển tối hình chú Cuội ngồi gốc cây đa, hố lồi lõm, ánh đất ở phần tối).
      // Ảnh KHÔNG xoay theo nắng: trăng luôn đứng thẳng, chỉ phần sáng đổi hướng.
      var res = clamp(Math.ceil(2 * r * dprOv / 16) * 16, 32, 320);
      var img = moonImage(res, p, rot || 0, gl, col);
      if (img) {
        c.save(); c.globalAlpha = a; c.drawImage(img, x0 - r, y0 - r, 2 * r, 2 * r); c.restore();
        return;
      }
      // Đường lui (không dựng được ảnh): đĩa phẳng như trước.
      c.save(); c.translate(x0, y0); c.rotate(rot || 0);
      var x = 0, y = 0;
      a *= 0.35 + 0.65 * Math.min(1, gl);       // trăng mờ: phần sáng cũng nhạt đi
      c.fillStyle = "rgba(16,22,38," + 0.92 * a + ")";
      c.beginPath(); c.arc(x, y, r, 0, 6.2832); c.fill();
      c.strokeStyle = rgba(col, 0.18 * a); c.lineWidth = 0.8; c.stroke();     // ánh đất mờ ở rìa tối
      c.save();
      c.beginPath();
      c.arc(x, y, r, -Math.PI / 2, Math.PI / 2, side < 0);
      for (var th = Math.PI / 2; th >= -Math.PI / 2 - 1e-6; th -= Math.PI / 24) {
        c.lineTo(x + side * r * k * Math.cos(th), y + r * Math.sin(th));
      }
      c.closePath();
      var lg = c.createRadialGradient(x - r * 0.3, y - r * 0.35, r * 0.1, x, y, r * 1.1);
      lg.addColorStop(0, "rgba(250,248,240," + a + ")");
      lg.addColorStop(1, rgba(col, 0.92 * a));
      c.fillStyle = lg; c.fill();
      c.clip();
      // vài miệng hố cố định - đủ để nhận ra là Mặt trăng chứ không phải một chấm sáng
      [[-0.3, -0.2, 0.22], [0.25, 0.3, 0.16], [0.1, -0.45, 0.12], [-0.15, 0.4, 0.1], [0.42, -0.05, 0.13]].forEach(function (cr) {
        c.fillStyle = "rgba(120,128,150," + 0.28 * a + ")";
        c.beginPath(); c.arc(x + cr[0] * r, y + cr[1] * r, cr[2] * r, 0, 6.2832); c.fill();
      });
      c.restore();
      c.restore();
    }
    function drawMoon(c, front, dt) {
      if (!moon) return;
      var pt = moonScreen(geo.moonV || [0.6, 0.3, 0.7]);
      moon.pt = pt;
      if ((pt.z >= 0) !== front) return;
      var r = geo.R * 0.17 * look.moonSize * (0.92 + 0.08 * pt.z) * (1 + moon.glow * 0.12);
      moon.glow += ((hoverSat === moon ? 1 : 0) - moon.glow) * 0.18;
      var col = moon.status === "online" ? moon.col : satColor(moon);
      c.save();
      if (!front) {   // sau hành tinh: khoét đĩa hành tinh ra khỏi vùng vẽ (che thật)
        c.beginPath(); c.rect(0, 0, W, H); c.arc(geo.cx, geo.cy, geo.R, 0, 6.2832, true); c.clip();
      }
      var Lv = geo.L || [-0.6, 0.5, 0.6];
      drawMoonDisc(c, pt.x, pt.y, r, moonShownPhase(), col, front ? 1 : 0.75, Math.atan2(-Lv[1], Lv[0]), look.moonGlow);
      c.restore();
    }
    function drawMoonPath(c) {
      if (!moon) return;
      if (!orbitG.length) return;
      var prev = moonScreen(toView(Gm, orbitG[0]));
      c.lineWidth = 0.8;
      for (var s = 1; s <= orbitG.length; s++) {
        var pt = moonScreen(toView(Gm, orbitG[s % orbitG.length]));
        var dx = pt.x - geo.cx, dy = pt.y - geo.cy;
        if (!(pt.z < 0 && dx * dx + dy * dy < geo.R * geo.R)) {
          c.strokeStyle = "rgba(214,224,245," + (pt.z >= 0 ? 0.1 : 0.05) * (1 + moon.glow) + ")";
          c.beginPath(); c.moveTo(prev.x, prev.y); c.lineTo(pt.x, pt.y); c.stroke();
        }
        prev = pt;
      }
    }

    // Mặt trời cho bản SAFE (không shader): cùng vị trí, quầng + chùm sáng bằng gradient.
    function drawSafeSun(c) {
      if (!geo.sun) return;
      var s = geo.sun, L = sunLook(), col = [255 * L.c[0] | 0, 255 * L.c[1] | 0, 255 * L.c[2] | 0];
      var bx = (s.x + geo.cx) / 2, by = (s.y + geo.cy) / 2;
      c.save(); c.translate(bx, by); c.rotate(Math.atan2(geo.cy - s.y, geo.cx - s.x));
      var len = Math.hypot(geo.cx - s.x, geo.cy - s.y);
      c.beginPath(); c.moveTo(-len / 2, -s.r * 0.6); c.lineTo(len / 2, -geo.R * 0.9); c.lineTo(len / 2, geo.R * 0.9); c.lineTo(-len / 2, s.r * 0.6); c.closePath();
      c.fillStyle = rgba(col, 0.06 * L.k); c.fill();
      c.restore();
      var co = c.createRadialGradient(s.x, s.y, s.r * 0.9, s.x, s.y, s.r * 4.2);
      co.addColorStop(0, rgba(col, 0.55 * L.k)); co.addColorStop(1, rgba(col, 0));
      c.fillStyle = co; c.beginPath(); c.arc(s.x, s.y, s.r * 4.2, 0, 6.2832); c.fill();
      var dk = c.createRadialGradient(s.x - s.r * 0.25, s.y - s.r * 0.25, 0, s.x, s.y, s.r);
      dk.addColorStop(0, "rgba(255,250,230," + L.k + ")"); dk.addColorStop(1, rgba(col, L.k));
      c.fillStyle = dk; c.beginPath(); c.arc(s.x, s.y, s.r, 0, 6.2832); c.fill();
    }

    // ---------- vẽ lớp 2D ----------
    function drawSafePlanet(c, now) {
      var cx = geo.cx, cy = geo.cy, r = geo.R;
      var A = light ? 0.75 : 1;
      // Concept màu của tab Quả tinh cầu -> màu 0..255 cho gradient (bản này không có shader).
      var P = LD.pal, pc = function (v, m) { return [Math.min(255, v[0] * 255 * m) | 0, Math.min(255, v[1] * 255 * m) | 0, Math.min(255, v[2] * 255 * m) | 0]; };
      var cRim = pc(P.rim, 1), cSea = pc(P.sea, 1), aK = look.atmo;
      drawSafeSun(c);
      // Khí quyển vẽ bằng CUNG TRÒN (không fillRect) -> không bao giờ ra khung vuông.
      var at = c.createRadialGradient(cx, cy, r * 0.9, cx, cy, r * 1.9);
      at.addColorStop(0, rgba(cRim, Math.min(0.6, 0.22 * A * aK * (1 + hover * 0.4))));
      at.addColorStop(0.45, rgba(cSea, 0.10 * A * aK));
      at.addColorStop(1, rgba(cSea, 0));
      c.fillStyle = at; c.beginPath(); c.arc(cx, cy, r * 1.9, 0, 6.2832); c.fill();
      if (cur[2] > 0.02) {   // nghe: quầng xanh lá-cyan nở theo giọng
        var lr = r * (1.2 + ampS * 0.5);
        var lg = c.createRadialGradient(cx, cy, r, cx, cy, lr + r * 0.3);
        lg.addColorStop(0, rgba(PAL.green, 0.25 * cur[2])); lg.addColorStop(1, rgba(PAL.green, 0));
        c.fillStyle = lg; c.beginPath(); c.arc(cx, cy, lr + r * 0.3, 0, 6.2832); c.fill();
      }
      var b = c.createRadialGradient(cx - r * 0.38, cy - r * 0.4, 0, cx, cy, r * 1.05);
      var sB = look.surface * (0.3 + 0.7 * Math.min(1.4, look.sunPower));
      var mixP = function (u, v, t2, m) { return [u[0] + (v[0] - u[0]) * t2, u[1] + (v[1] - u[1]) * t2, u[2] + (v[2] - u[2]) * t2].map(function (x) { return x * m; }); };
      b.addColorStop(0, rgba(pc(mixP(P.sea, P.rim, 0.45, 1), sB), 1));
      b.addColorStop(0.35, rgba(pc(P.sea, 0.78 * sB), 1));
      b.addColorStop(0.75, rgba(pc(mixP(P.deep, P.sea, 0.3, 1), sB), 1));
      b.addColorStop(1, rgba(pc(P.deep, 0.8), 1));
      c.fillStyle = b; c.beginPath(); c.arc(cx, cy, r, 0, 6.2832); c.fill();
      c.save(); c.beginPath(); c.arc(cx, cy, r, 0, 6.2832); c.clip();
      var tt = simT;
      // Vùng năng lượng dưới mặt nước: vài đốm tinh vân mềm trôi chậm (thay cho shader).
      var blobs = [[PAL.violet, -0.2, 0.25, 0.55], [PAL.magenta, 0.35, -0.1, 0.4], [PAL.mint, -0.35, -0.3, 0.35], [PAL.gold, 0.25, 0.45, 0.25]];
      blobs.forEach(function (bl, i) {
        var bx = cx + (bl[1] + 0.12 * Math.sin(tt * 0.07 * (1 + cur[1] * 3) + i * 1.7)) * r;
        var by = cy + bl[2] * r;
        var gg = c.createRadialGradient(bx, by, 0, bx, by, r * bl[3]);
        gg.addColorStop(0, rgba(bl[0], (i === 3 ? 0.2 : 0.42) + cur[1] * 0.25));
        gg.addColorStop(1, rgba(bl[0], 0));
        c.fillStyle = gg; c.fillRect(cx - r, cy - r, r * 2, r * 2);
      });
      var gx = cx - r * 0.42, gy = cy - r * 0.45;      // vệt nắng nhỏ, không phải đốm nhựa
      var gl2 = c.createRadialGradient(gx, gy, 0, gx, gy, r * 0.22);
      gl2.addColorStop(0, "rgba(220,245,255,0.35)"); gl2.addColorStop(1, "rgba(220,245,255,0)");
      c.fillStyle = gl2; c.beginPath(); c.ellipse(gx, gy, r * 0.22, r * 0.11, -0.5, 0, 6.2832); c.fill();
      for (var i = 0; i < 7; i++) {   // dải nước vĩ tuyến
        var dy = -0.6 + i * 0.2, rx = r * Math.sqrt(Math.max(0.05, 1 - dy * dy)), ry = rx * 0.28;
        c.strokeStyle = rgba(i % 3 === 1 ? PAL.mint : PAL.cyan, 0.16 + cur[1] * 0.12);
        c.lineWidth = 1.2; c.beginPath();
        for (var th = 0.06; th <= Math.PI - 0.06; th += 0.05) {
          var xx = cx + Math.cos(th) * rx;
          var yy = cy + dy * r + Math.sin(th) * ry + Math.sin(th * 6 + tt * (0.6 + cur[0] * 0.4) + i) * (1.5 + ampS * 4) * Math.sin(th);
          if (th === 0.06) c.moveTo(xx, yy); else c.lineTo(xx, yy);
        }
        c.stroke();
      }
      var tm = c.createRadialGradient(cx + r * 0.55, cy + r * 0.6, r * 0.2, cx + r * 0.55, cy + r * 0.6, r * 1.5);
      tm.addColorStop(0, "rgba(2,8,23,0.6)"); tm.addColorStop(1, "rgba(2,8,23,0)");
      c.fillStyle = tm; c.fillRect(cx - r, cy - r, r * 2, r * 2);
      if (cur[6] > 0.02) {   // lỗi: đỏ CHỈ ở một vùng
        var ex = cx + r * 0.5, ey = cy + r * 0.45;
        var eg = c.createRadialGradient(ex, ey, 0, ex, ey, r * 0.45);
        eg.addColorStop(0, "rgba(255,46,56," + 0.5 * cur[6] + ")"); eg.addColorStop(1, "rgba(255,46,56,0)");
        c.fillStyle = eg; c.fillRect(cx - r, cy - r, r * 2, r * 2);
      }
      c.restore();
      c.strokeStyle = rgba(cRim, Math.min(0.5, 0.18 * aK)); c.lineWidth = 6;
      c.beginPath(); c.arc(cx, cy, r + 2, 0, 6.2832); c.stroke();
      c.strokeStyle = rgba(cRim, Math.min(1, 0.6 * Math.max(0.3, aK))); c.lineWidth = 1.4;
      c.beginPath(); c.arc(cx, cy, r, -Math.PI * 0.95, -Math.PI * 0.1); c.stroke();
      c.strokeStyle = rgba(PAL.magenta, 0.4);
      c.beginPath(); c.arc(cx, cy, r, Math.PI * 0.05, Math.PI * 0.45); c.stroke();
      if (cur[3] > 0.02) {   // nói: vòng sáng toả ra
        for (var k = 0; k < 3; k++) {
          var ph = ((now / 1000) * 0.42 + k / 3) % 1;
          c.strokeStyle = rgba(PAL.cyan, (1 - ph) * 0.5 * cur[3] * (0.4 + ampS));
          c.lineWidth = 1.5; c.beginPath(); c.arc(cx, cy, r * (1 + ph * 0.9), 0, 6.2832); c.stroke();
        }
      }
    }

    // Phóng gần (cận cảnh Việt Nam) thì vành dữ liệu + vệ tinh tan dần, khỏi che bản đồ.
    function ringFade() { return 1 - smooth(1.5, 2.3, cam.zoom); }
    // Công tắc "Vành quỹ đạo dữ liệu" (tab Quả tinh cầu) tắt vành + hạt + ký hiệu; vệ tinh dự
    // án vẫn ở lại vì chúng là DỮ LIỆU sức khoẻ app, không phải trang trí.
    function orbitFade() { return ringFade() * fx.orbits; }
    function drawRings(c, front) {
      var rf = orbitFade();
      if (rf < 0.02) return;
      var conn = cur[4], recon = cur[5];
      var since = (performance.now() - stateAt) / 1000;
      for (var i = 0; i < 3; i++) {
        var g = RINGS[i];
        var hot = hoverSat && hoverSat.ring === i ? 1 : 0;
        // Đang nối: các vành sáng dần lần lượt; nối lại: vành tắt rồi bật lại từng cái.
        var lit = 1;
        if (state === "CONNECTING") lit = 0.35 + 0.9 * clamp(since * 1.2 - i * 0.45, 0, 1);
        if (state === "RECONNECTING") lit = 0.2 + 0.8 * clamp(((since * 0.8) % 3) - i, 0, 1);
        var segs = 120, prev = ringPt(i, 0);
        for (var s = 1; s <= segs; s++) {
          var pt = ringPt(i, s / segs * 6.2832);
          var mz = (pt.z + prev.z) / 2;
          var isFront = mz >= 0;
          if (isFront === front && !(pt.hidden || prev.hidden)) {
            var a = (front ? 0.2 + 0.32 * mz : 0.09) * lit * (1 + hot * 1.4) * (1 + conn * 0.6) * (1 - recon * 0.2) * rf;
            c.strokeStyle = rgba(g.col, a * 0.35); c.lineWidth = 3.2;
            c.beginPath(); c.moveTo(prev.x, prev.y); c.lineTo(pt.x, pt.y); c.stroke();
            c.strokeStyle = rgba(g.col, a); c.lineWidth = front ? 1.1 : 0.8;
            c.beginPath(); c.moveTo(prev.x, prev.y); c.lineTo(pt.x, pt.y); c.stroke();
          }
          prev = pt;
        }
      }
    }

    function drawParticles(c, front, dt) {
      var speed = cur[9], rf = orbitFade();
      particles.forEach(function (p) {
        if (dt) p.a += p.sp * dt * speed;
        var pt = ringPt(p.ring, p.a);
        if ((pt.z >= 0) !== front || pt.hidden) return;
        var a = (front ? 0.55 + 0.4 * pt.z : 0.22) * (1 - cur[5] * 0.5) * rf;
        c.fillStyle = rgba(RINGS[p.ring].col, a);
        c.beginPath(); c.arc(pt.x, pt.y, p.s * (front ? 1.1 : 0.8) * look.orbitDot, 0, 6.2832); c.fill();
      });
      // Nghĩ: hạt xoáy nhẹ quanh hành tinh
      if (cur[1] > 0.03 && swirl.length) {
        var R0 = geo.R;
        swirl.forEach(function (w) {
          if (dt) w.a += w.sp * dt * (0.6 + cur[1] * 1.6);
          var rr = R0 * (w.r + 0.05 * Math.sin(simT * 1.3 + w.ph));
          var x = Math.cos(w.a) * rr, y0 = Math.sin(w.a) * rr;
          var y = y0 * Math.cos(1.2 + w.tilt), z = -y0 * Math.sin(1.2 + w.tilt);
          if ((z >= 0) !== front) return;
          var sx = geo.cx + x, sy = geo.cy - y;
          if (z < 0 && (x * x + y * y) < R0 * R0) return;
          c.fillStyle = rgba(w.ph > 3 ? PAL.violet : PAL.magenta, 0.55 * cur[1]);
          c.beginPath(); c.arc(sx, sy, 1.1, 0, 6.2832); c.fill();
        });
      }
    }

    function drawGlyphs(c, now) {
      if (profile === "reduced" || profile === "safe" || orbitFade() < 0.3) return;
      if (now > nextGlyph) {
        nextGlyph = now + 1400 + Math.random() * 2600;
        var ring = Math.floor(Math.random() * 3);
        glyphs.push({ ring: ring, a: Math.random() * 6.283, txt: GLYPHS[Math.floor(Math.random() * GLYPHS.length)], at: now });
        if (glyphs.length > 6) glyphs.shift();
      }
      c.font = "500 8px ui-monospace, 'Cascadia Mono', Consolas, monospace";
      c.textAlign = "center"; c.textBaseline = "middle";
      glyphs = glyphs.filter(function (g) {
        var age = (now - g.at) / 2600;
        if (age >= 1) return false;
        var pt = ringPt(g.ring, g.a + age * 0.15);
        if (pt.z < 0) return true;
        var a = Math.sin(age * Math.PI) * 0.5;
        // nháy ngắt quãng như tín hiệu vô tuyến
        if (((now / 90) | 0) % 7 === 0) a *= 0.3;
        c.fillStyle = rgba(RINGS[g.ring].col, a);
        c.fillText(g.txt, pt.x, pt.y - 7);
        return true;
      });
    }

    function drawSatDots(c, front, dt) {
      var rf = ringFade();
      sats.forEach(function (s) {
        if (!satVisible(s) || rf < 0.05) { s.pt = null; return; }
        var sp = s.status === "offline" ? 0.22 : 1;
        if (dt) s.a += s.sp * dt * sp * cur[8];
        var pt = ringPt(s.ring, s.a);
        s.pt = pt;
        if ((pt.z >= 0) !== front) return;
        var col = satColor(s);
        s.glow += ((hoverSat === s ? 1 : 0) - s.glow) * 0.18;
        var alpha = (pt.hidden ? 0.18 : front ? 0.95 : 0.55) * rf;
        var r = (front ? 3.4 : 2.6) * (1 + s.glow * 0.45);
        if (s.status === "degraded") alpha *= 0.7 + 0.3 * Math.sin(simT * 2.2);
        var halo = c.createRadialGradient(pt.x, pt.y, 0, pt.x, pt.y, r * 4.2);
        halo.addColorStop(0, rgba(col, 0.35 * alpha * (1 + s.glow)));
        halo.addColorStop(1, rgba(col, 0));
        c.fillStyle = halo; c.beginPath(); c.arc(pt.x, pt.y, r * 4.2, 0, 6.2832); c.fill();
        // tinh thể nhỏ: hình thoi
        c.fillStyle = rgba(col, alpha);
        c.beginPath();
        c.moveTo(pt.x, pt.y - r * 1.25); c.lineTo(pt.x + r * 0.85, pt.y);
        c.lineTo(pt.x, pt.y + r * 1.25); c.lineTo(pt.x - r * 0.85, pt.y); c.closePath(); c.fill();
        c.fillStyle = "rgba(255,255,255," + 0.7 * alpha + ")";
        c.beginPath(); c.arc(pt.x - r * 0.15, pt.y - r * 0.3, r * 0.28, 0, 6.2832); c.fill();
      });
    }

    // Nhãn: luôn đọc được (nền tối mờ phía sau chữ), chọn bên đặt sao cho không chồng nhau
    // và không lấn vào hai cột telemetry. Giữ bên đã chọn ở khung trước để nhãn không nhảy.
    function drawLabels(c) {
      var insets = (opts.insets && opts.insets()) || { left: 0, right: 0 };
      var minX = insets.left + 4, maxX = W - insets.right - 4;
      c.font = "600 10px 'Segoe UI', system-ui, sans-serif";
      c.textBaseline = "middle";
      var placed = [];
      if (sun && geo.sun) sun.pt = { x: geo.sun.x, y: geo.sun.y, z: 1 };
      var list = sats.filter(function (s) { return s.pt; })
        .sort(function (a, b) { return b.pt.z - a.pt.z; });
      // Mặt trời + mặt trăng đặt nhãn TRƯỚC (ưu tiên chỗ), vệ tinh xếp quanh.
      if (moon && moon.pt) list.unshift(moon);
      if (sun && sun.pt) list.unshift(sun);
      list.forEach(function (s) {
        // Mặt trời / mặt trăng có biểu tượng nhỏ VẼ bằng canvas trước tên (không dùng emoji:
        // repo cấm emoji trong giao diện, xem test_icons.py).
        var text = s.name, icoW = s.kind ? 12 : 0;
        var tw = c.measureText(text).width, h = 15, padX = 5;
        var bw = tw + padX * 2 + icoW;
        var off = s.kind === "sun" ? geo.sun.r + 8 : s.kind === "moon" ? geo.R * 0.17 * look.moonSize + 7 : 9;
        var cands = { r: [s.pt.x + off, s.pt.y - h / 2], l: [s.pt.x - off - bw, s.pt.y - h / 2],
                      u: [s.pt.x - bw / 2, s.pt.y - off - 3 - h], d: [s.pt.x - bw / 2, s.pt.y + off + 1] };
        var first = labelSide[s.id] || (s.kind === "sun" ? "d" : s.pt.x < geo.cx ? "l" : "r");
        var order = [first, "r", "l", "u", "d"];
        var pick = null;
        for (var i = 0; i < order.length && !pick; i++) {
          var cd = cands[order[i]];
          var bx = clamp(cd[0], minX, maxX - bw), by = cd[1];
          var hit = placed.some(function (q) { return bx < q[0] + q[2] + 3 && bx + bw + 3 > q[0] && by < q[1] + q[3] + 2 && by + h + 2 > q[1]; });
          if (!hit) pick = [bx, by, order[i]];
        }
        if (!pick) { var c0 = cands[order[0]]; pick = [clamp(c0[0], minX, maxX - bw), c0[1], order[0]]; }
        labelSide[s.id] = pick[2];
        placed.push([pick[0], pick[1], bw, h]);
        s.lbl = { x: pick[0], y: pick[1], w: bw, h: h };
        var back = s.pt.z < 0;
        var a = back ? 0.62 : 1;
        c.fillStyle = "rgba(2,8,23," + (light ? 0.62 : 0.55) * a + ")";
        roundRect(c, pick[0], pick[1], bw, h, 5); c.fill();
        var col = satColor(s);
        c.strokeStyle = rgba(col, (0.35 + s.glow * 0.5) * a); c.lineWidth = 1;
        roundRect(c, pick[0] + 0.5, pick[1] + 0.5, bw - 1, h - 1, 5); c.stroke();
        c.fillStyle = "rgba(230,248,255," + 0.95 * a + ")";
        c.textAlign = "left";
        c.fillText(text, pick[0] + padX + icoW, pick[1] + h / 2 + 0.5);
        if (s.kind) labelIcon(c, s.kind, pick[0] + padX + 4, pick[1] + h / 2, a);
      });
    }
    function labelIcon(c, kind, x, y, a) {
      if (kind === "sun") {
        c.fillStyle = rgba(PAL.gold, a);
        c.beginPath(); c.arc(x, y, 2.4, 0, 6.2832); c.fill();
        c.strokeStyle = rgba(PAL.gold, 0.9 * a); c.lineWidth = 1;
        for (var i = 0; i < 8; i++) {
          var an = i * Math.PI / 4;
          c.beginPath(); c.moveTo(x + Math.cos(an) * 3.6, y + Math.sin(an) * 3.6);
          c.lineTo(x + Math.cos(an) * 5, y + Math.sin(an) * 5); c.stroke();
        }
      } else {   // lưỡi liềm: đĩa sáng trừ đi một đĩa lệch phải
        c.save();
        c.fillStyle = "rgba(230,236,250," + a + ")";
        c.beginPath(); c.arc(x, y, 4.2, 0, 6.2832); c.arc(x + 2.2, y - 0.8, 3.6, 0, 6.2832, true); c.fill("evenodd");
        c.restore();
      }
    }
    // Điểm địa lý -> màn hình (null nếu ở mặt khuất). Dùng cho ghim studio và nhãn Việt Nam.
    function geoScreen(latD, lonD) {
      var v = toView(Gm, geoVec(latD, lonD));
      if (v[2] < 0.06) return null;
      return { x: geo.cx + v[0] * geo.R, y: geo.cy - v[1] * geo.R, z: v[2] };
    }
    function drawVN(c, now) {
      var G = window.JoyceVNGeo;
      if (!G || cam.zoom < 0.7) return;
      // Ngưỡng theo KÍCH THƯỚC THẬT trên màn hình (Việt Nam cao ~0,26R), không theo hệ số zoom:
      // cùng một mức zoom mà khoang hẹp thì Việt Nam vẫn bé, nhãn sẽ đè lên nhau.
      var R = geo.R;
      c.textAlign = "center"; c.textBaseline = "middle";
      var tag = function (txt, lat, lon, size, alpha, col) {
        var pt = geoScreen(lat, lon);
        if (!pt) return;
        var a = alpha * smooth(0.06, 0.35, pt.z);
        c.font = "600 " + size + "px 'Segoe UI', system-ui, sans-serif";
        c.fillStyle = "rgba(2,8,23," + 0.45 * a + ")";
        var w = c.measureText(txt).width + 10;
        roundRect(c, pt.x - w / 2, pt.y - size * 0.8, w, size * 1.6, 4); c.fill();
        c.fillStyle = rgba(col, a);
        c.fillText(txt, pt.x, pt.y + 0.5);
      };
      var la = smooth(800, 1000, R);
      if (la > 0.01) {
        tag("VIỆT NAM", 13.4, 107.9, 11, 0.9 * la, PAL.cyan);
        tag("Hoàng Sa (Việt Nam)", 17.6, 111.9, 9.5, 0.85 * la, PAL.mint);
        tag("Trường Sa (Việt Nam)", 12.1, 114.3, 9.5, 0.85 * la, PAL.mint);
      }
      // Ghim H2O Studio · ThuyH2O Makeup (Đại Bản, An Dương, Hải Phòng): chấm nhịp + nhãn khi gần.
      var st = G.studio, sp = st && geoScreen(st.lat, st.lon);
      if (!sp) return;
      var pulse = (now / 1600) % 1;
      var a0 = smooth(0.06, 0.3, sp.z);
      c.strokeStyle = rgba(PAL.gold, (1 - pulse) * 0.8 * a0); c.lineWidth = 1.4;
      c.beginPath(); c.arc(sp.x, sp.y, 3 + pulse * 14, 0, 6.2832); c.stroke();
      c.fillStyle = rgba(PAL.gold, a0); c.beginPath(); c.arc(sp.x, sp.y, 3, 0, 6.2832); c.fill();
      c.fillStyle = "rgba(255,255,255," + a0 + ")"; c.beginPath(); c.arc(sp.x, sp.y, 1.2, 0, 6.2832); c.fill();
      var ls = smooth(420, 560, R);
      if (ls > 0.01) {
        c.textAlign = "left";
        c.font = "700 10.5px 'Segoe UI', system-ui, sans-serif";
        var t1 = st.name, w1 = c.measureText(t1).width;
        var sub = R > 1100 ? st.place : "";
        c.font = "500 9px 'Segoe UI', system-ui, sans-serif";
        var w2 = sub ? c.measureText(sub).width : 0;
        var bw = Math.max(w1, w2) + 14, bh = sub ? 30 : 17;
        var bx = sp.x + 12, by = sp.y - bh - 6;
        c.strokeStyle = rgba(PAL.gold, 0.55 * ls * a0); c.lineWidth = 1;
        c.beginPath(); c.moveTo(sp.x + 3, sp.y - 3); c.lineTo(bx, by + bh); c.stroke();
        c.fillStyle = "rgba(2,8,23," + 0.62 * ls * a0 + ")"; roundRect(c, bx, by, bw, bh, 5); c.fill();
        c.strokeStyle = rgba(PAL.gold, 0.6 * ls * a0); roundRect(c, bx + 0.5, by + 0.5, bw - 1, bh - 1, 5); c.stroke();
        c.fillStyle = "rgba(255,240,200," + ls * a0 + ")";
        c.font = "700 10.5px 'Segoe UI', system-ui, sans-serif"; c.fillText(t1, bx + 7, by + 9);
        if (sub) { c.fillStyle = "rgba(220,235,255," + 0.85 * ls * a0 + ")"; c.font = "500 9px 'Segoe UI', system-ui, sans-serif"; c.fillText(sub, bx + 7, by + 22); }
      }
    }
    // Hố đen "hút" tài liệu khi Joyce đang nạp dữ liệu: hạt sáng (kèm tên file) xoắn ốc vào
    // tâm hố; nạp xong thì một tia sáng bắn từ hố đen về Trái Đất = tri thức đã vào brain.
    function drawIngest(c, now, dt) {
      var B = geo.bh;
      if (!B || profile === "reduced") return;
      if (ing.on && now > ing.nextSpawn) {
        ing.nextSpawn = now + 120 + Math.random() * 180;
        var ang = Math.random() * 6.2832, rad = Math.min(W, H) * (0.28 + Math.random() * 0.3);
        var txt = "";
        if (ing.items.length && Math.random() < 0.35) { txt = ing.items[ing.nameIdx % ing.items.length]; ing.nameIdx++; }
        ing.parts.push({ a0: ang, r0: rad, t: 0, sp: 0.32 + Math.random() * 0.22, txt: txt,
                         col: [PAL.cyan, PAL.mint, PAL.gold, PAL.violet][(Math.random() * 4) | 0] });
        if (ing.parts.length > 90) ing.parts.shift();
      }
      if (ing.wasOn && !ing.on) ing.beam = 1;
      ing.wasOn = ing.on;
      c.save();
      ing.parts = ing.parts.filter(function (p) {
        p.t += dt * p.sp;
        if (p.t >= 1) return false;
        var e = Math.pow(1 - p.t, 1.6);
        var a = p.a0 + p.t * 5.5;
        var x = B.x + Math.cos(a) * p.r0 * e, y = B.y + Math.sin(a) * p.r0 * e * 0.55;
        var al = Math.min(1, p.t * 5) * (1 - smooth(0.85, 1, p.t));
        // vệt đuôi: nối các vị trí trước đó trên cùng đường xoắn, nhạt dần về phía sau
        var tp = Math.max(0, p.t - 0.09), ep = Math.pow(1 - tp, 1.6), ap = p.a0 + tp * 5.5;
        var x0 = B.x + Math.cos(ap) * p.r0 * ep, y0 = B.y + Math.sin(ap) * p.r0 * ep * 0.55;
        var tg = c.createLinearGradient(x0, y0, x, y);
        tg.addColorStop(0, rgba(p.col, 0)); tg.addColorStop(1, rgba(p.col, 0.75 * al));
        c.strokeStyle = tg; c.lineWidth = 2; c.lineCap = "round";
        c.beginPath(); c.moveTo(x0, y0); c.lineTo(x, y); c.stroke();
        var g = c.createRadialGradient(x, y, 0, x, y, 8);
        g.addColorStop(0, rgba(p.col, 0.95 * al)); g.addColorStop(1, rgba(p.col, 0));
        c.fillStyle = g; c.beginPath(); c.arc(x, y, 8, 0, 6.2832); c.fill();
        if (p.txt && p.t < 0.65) {
          c.font = "500 9px ui-monospace, Consolas, monospace"; c.textAlign = "center";
          c.fillStyle = "rgba(220,240,255," + 0.85 * al * (1 - p.t / 0.65) + ")";
          c.fillText(p.txt.length > 26 ? p.txt.slice(0, 25) + "…" : p.txt, x, y - 10);
        }
        return true;
      });
      if (ing.beam > 0) {
        ing.beam = Math.max(0, ing.beam - dt / 1.8);
        // Đích: ghim H2O Studio · ThuyH2O Makeup (Hải Phòng) khi đang ở nửa thấy được; khuất thì
        // về mép hành tinh gần hố đen nhất như trước (giai đoạn 3 của bầu trời tri thức).
        var dx = geo.cx - B.x, dy = geo.cy - B.y, dl = Math.hypot(dx, dy) || 1;
        var stp = studioPt(), ex = stp ? stp.x : geo.cx - dx / dl * geo.R, ey = stp ? stp.y : geo.cy - dy / dl * geo.R;
        var k = Math.sin(ing.beam * Math.PI);
        c.lineCap = "round";
        c.strokeStyle = rgba(PAL.cyan, 0.22 * k); c.lineWidth = 9;
        c.beginPath(); c.moveTo(B.x, B.y); c.lineTo(ex, ey); c.stroke();
        c.strokeStyle = "rgba(235,252,255," + 0.9 * k + ")"; c.lineWidth = 2;
        c.beginPath(); c.moveTo(B.x, B.y); c.lineTo(ex, ey); c.stroke();
        var fr = geo.R * (stp ? 0.2 : 0.35), fl = c.createRadialGradient(ex, ey, 0, ex, ey, fr);
        fl.addColorStop(0, rgba(PAL.mint, 0.55 * k)); fl.addColorStop(1, rgba(PAL.mint, 0));
        c.fillStyle = fl; c.beginPath(); c.arc(ex, ey, fr, 0, 6.2832); c.fill();
      }
      c.restore();
    }
    // ---------------------------------------------------------------------------
    // BẦU TRỜI TRI THỨC (docs/dev/2026-10-bau-troi-tri-thuc.md). Mỗi tài liệu kiến thức là một
    // thiên thể: sao (wiki đã chưng cất; quy trình là sao bốn cánh), chấm trên vành (kỹ năng /
    // quy trình Joyce / trí nhớ), đá vụn quanh hố đen (tài liệu thô chưa chưng cất). Vị trí suy
    // từ id (băm cố định phía máy chủ): cùng tài liệu luôn nằm một chỗ, nạp lại không nhảy.
    // ---------------------------------------------------------------------------
    // Trần [sao, chấm vành, đá vụn] theo hồ sơ máy. Máy chủ xếp theo cỡ giảm dần nên cắt đầu
    // danh sách là giữ thiên thể quan trọng nhất.
    var KNOW_CAP = { high: [1500, 600, 600], balanced: [900, 400, 350], safe: [300, 150, 120], reduced: [300, 150, 120] };
    var KNOW_DUST = [150, 160, 175];   // đá vụn: màu thương hiệu pha xám đá
    var know = { stars: [], orbit: [], debris: [], hits: [], hover: null, counts: null, scope: "",
                 bi: {}, byId: {}, hl: null };
    var foc = null;   // Big Bang khi tìm kiếm đang diễn (xem focusKnowledge)
    function hashRnd(seed) {   // mulberry32: dãy giả ngẫu nhiên cố định theo id
      var s = seed >>> 0;
      return function () {
        s = (s + 0x6D2B79F5) >>> 0;
        var q = Math.imul(s ^ (s >>> 15), 1 | s);
        q = (q + Math.imul(q ^ (q >>> 7), 61 | q)) ^ q;
        return ((q ^ (q >>> 14)) >>> 0) / 4294967296;
      };
    }
    // Xoay một điểm khung nhìn theo camera, cùng phép như cuối ringPt (yaw rồi pitch).
    function camRot(x, y, z) {
      var cyw = Math.cos(cam.yaw), syw = Math.sin(cam.yaw);
      var x3 = x * cyw + z * syw, z3 = -x * syw + z * cyw;
      var cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
      return [x3, y * cp - z3 * sp, y * sp + z3 * cp];
    }
    function setKnowledge(d) {
      d = d || {};
      // Nạp lại bầu trời (mỗi 5 phút, sau mỗi lần nạp dữ liệu) KHÔNG được làm chấm vành và đá vụn
      // giật về góc ban đầu: giữ góc đang chạy của thiên thể cũ. Thiên thể mới hẳn (có bầu trời
      // trước đó mà chưa có id này) là tài liệu VỪA CHƯNG CẤT: sao đó "sinh ra" từ ghim H2O Studio.
      var cu = know.byId || {}, coCu = false, nowB = performance.now(), sinh = 0;
      for (var ck in cu) { coCu = true; break; }
      var bi = {}, list = Array.isArray(d.brains) ? d.brains : [];
      list.forEach(function (b, i) { bi[b.key] = { i: i, name: b.name || b.key, col: PAL[b.color] || PAL.gold }; });
      var nB = Math.max(1, list.length);
      var stars = [], orbit = [], debris = [];
      (Array.isArray(d.bodies) ? d.bodies : []).forEach(function (b) {
        if (!b || !b.id) return;
        var rnd = hashRnd(parseInt(b.id, 16) || 0);
        var br = bi[b.brain] || { i: 0, name: b.brain || "", col: PAL.gold };
        var k = { b: b, col: br.col, brainName: br.name, size: clamp(+b.size || 0, 0, 1),
                  ph: rnd() * 6.2832, tw: 0.6 + rnd() * 1.4 };
        var old = cu[b.id];
        if (b.kind === "star" && coCu && !old) { k.born = nowB + sinh * 220; sinh++; }
        if (b.kind === "star") {
          // Kinh độ theo CUNG của brain: kiến thức một phòng tụ thành một vùng trời. Vĩ độ ưu
          // tiên nửa trên ("bên trên địa cầu là các vì sao").
          var lon = (br.i + 0.08 + rnd() * 0.84) / nB * 6.2832, lat = -0.35 + rnd() * 1.55;
          var dist = 1.55 + rnd() * 1.05;
          k.v = [Math.cos(lat) * Math.sin(lon) * dist, Math.sin(lat) * dist, Math.cos(lat) * Math.cos(lon) * dist];
          stars.push(k);
        } else if (b.kind === "orbit") {
          k.ring = clamp(b.ring | 0, 0, 2); k.a = rnd() * 6.2832;
          if (old && old.ring === k.ring && old.a != null) k.a = old.a;
          k.sp = (0.025 + rnd() * 0.04) * (k.ring % 2 ? -1 : 1);
          orbit.push(k);
        } else {
          k.rho = 0.10 + rnd() * 0.14; k.a = rnd() * 6.2832; k.sp = 0.03 + rnd() * 0.05;
          k.spin = (rnd() - 0.5) * 1.2; k.rot = rnd() * 6.2832;
          k.dcol = [0, 1, 2].map(function (j) { return Math.round(br.col[j] * 0.45 + KNOW_DUST[j] * 0.55); });
          var nv = 5 + ((rnd() * 3) | 0);
          k.poly = [];
          for (var j = 0; j < nv; j++) k.poly.push(0.65 + rnd() * 0.5);
          if (old && old.rho != null) { k.a = old.a; k.rot = old.rot; }
          debris.push(k);
        }
      });
      know.stars = stars; know.orbit = orbit; know.debris = debris;
      know.counts = d.counts || null; know.scope = d.scope || ""; know.hover = null;
      know.bi = bi; know.byId = {};
      if (sinh && !ing.beam) ing.beam = 1;   // sao mới: bắn lại tia sáng cho khớp nhịp
      stars.concat(orbit, debris).forEach(function (k) { know.byId[k.b.id] = k; });
    }
    function knowCap(i) { return (KNOW_CAP[profile] || KNOW_CAP.balanced)[i]; }
    // Sao + đá vụn: vẽ ĐẦU TIÊN (sau quỹ đạo trăng), nằm sau mọi thứ. Đồng thời dựng lại danh
    // sách điểm bấm của khung này (know.hits); chấm vành tự thêm vào ở drawKnowOrbit.
    function drawKnowSky(c, now, dt) {
      know.hits = [];
      var kf = fx.knowledge;
      if (kf < 0.02) return;
      var t = now / 1000, R0 = geo.R, hv = know.hover;
      kf *= focDim();
      var ns = Math.min(know.stars.length, knowCap(0));
      for (var i = 0; i < ns; i++) {
        var s = know.stars[i], p = camRot(s.v[0], s.v[1], s.v[2]);
        var x = geo.cx + p[0] * R0, y = geo.cy - p[1] * R0;
        if (x < -10 || y < -10 || x > W + 10 || y > H + 10) continue;
        if (p[2] < 0 && Math.hypot(x - geo.cx, y - geo.cy) < R0) continue;   // khuất sau hành tinh
        s.sx = x; s.sy = y; s.seen = now;
        if (focHidden(s)) continue;   // đang là kết quả / đã lao vào vụ nổ
        if (s.born) {   // vừa chưng cất: bay từ ghim H2O Studio lên chỗ của nó, loé khi tới nơi
          var bu = (now - s.born) / 1800;
          if (bu < 0) continue;
          if (bu < 1) {
            if (!s.bornFrom) s.bornFrom = studioPt() || { x: geo.cx, y: geo.cy - R0 * 0.9 };
            var eb = 1 - Math.pow(1 - bu, 3), bx = s.bornFrom.x + (x - s.bornFrom.x) * eb, by = s.bornFrom.y + (y - s.bornFrom.y) * eb;
            var bg2 = c.createLinearGradient(s.bornFrom.x, s.bornFrom.y, bx, by);
            bg2.addColorStop(0, rgba(PAL.mint, 0)); bg2.addColorStop(1, rgba(PAL.mint, 0.7 * kf));
            c.strokeStyle = bg2; c.lineWidth = 1.6;
            c.beginPath(); c.moveTo(s.bornFrom.x, s.bornFrom.y); c.lineTo(bx, by); c.stroke();
            c.fillStyle = "rgba(240,255,250," + kf + ")"; c.beginPath(); c.arc(bx, by, 2.6, 0, 6.2832); c.fill();
            continue;
          }
          if (bu < 3.5) {
            var fk = (3.5 - bu) / 2.5;
            c.strokeStyle = rgba(PAL.mint, 0.7 * fk * kf); c.lineWidth = 1.2;
            c.beginPath(); c.arc(x, y, 3 + (bu - 1) * 10, 0, 6.2832); c.stroke();
          } else { s.born = 0; s.bornFrom = null; }
        }
        var on = hv === s ? 1 : 0;
        var a = (0.35 + 0.4 * (0.55 + 0.45 * Math.sin(t * s.tw + s.ph)) * 0.8 + 0.25 * s.size) * (p[2] < 0 ? 0.6 : 1);
        if (s.b.recent) a += 0.25 * (0.5 + 0.5 * Math.sin(t * 3 + s.ph));   // sửa trong 7 ngày: nháy
        var r = (0.8 + s.size * 1.6) * (1 + on * 0.8);
        c.fillStyle = rgba(s.col, Math.min(1, a * kf + on * 0.4));
        if (s.b.proc) {   // quy trình: sao bốn cánh
          c.fillRect(x - r * 2.2, y - 0.5, r * 4.4, 1);
          c.fillRect(x - 0.5, y - r * 2.2, 1, r * 4.4);
        }
        c.beginPath(); c.arc(x, y, r, 0, 6.2832); c.fill();
        if (on) { c.strokeStyle = rgba(s.col, 0.8); c.lineWidth = 1; c.beginPath(); c.arc(x, y, r + 4, 0, 6.2832); c.stroke(); }
        know.hits.push({ x: x, y: y, k: s });
      }
      var B = geo.bh;
      if (!B) return;
      var m = Math.min(W, H), nd = Math.min(know.debris.length, knowCap(2));
      for (var j = 0; j < nd; j++) {
        var d = know.debris[j];
        if (dt) { d.a += d.sp * dt; d.rot += d.spin * dt; }
        var rr = d.rho * m, dx = B.x + Math.cos(d.a) * rr, dy = B.y + Math.sin(d.a) * rr * 0.55;
        if (dx < -10 || dy < -10 || dx > W + 10 || dy > H + 10) continue;
        d.sx = dx; d.sy = dy; d.seen = now;
        if (focHidden(d)) continue;
        var on2 = hv === d ? 1 : 0, sz = (1.3 + d.size * 2.2) * (1 + on2 * 0.7);
        c.fillStyle = rgba(on2 ? d.col : d.dcol, Math.min(1, (0.5 + 0.2 * d.size) * kf + on2 * 0.4));
        c.beginPath();
        for (var q = 0; q < d.poly.length; q++) {
          var ang = d.rot + q / d.poly.length * 6.2832, pr = sz * d.poly[q];
          if (q) c.lineTo(dx + Math.cos(ang) * pr, dy + Math.sin(ang) * pr);
          else c.moveTo(dx + Math.cos(ang) * pr, dy + Math.sin(ang) * pr);
        }
        c.closePath(); c.fill();
        know.hits.push({ x: dx, y: dy, k: d });
      }
    }
    // Chấm tri thức trên vành: vẽ cùng nhịp drawParticles (nửa sau rồi nửa trước) để hành tinh
    // che đúng; hưởng luôn thanh Cỡ vành quỹ đạo (ringPt) và Cỡ chấm trên vành (orbitDot).
    function drawKnowOrbit(c, front, dt) {
      var kf = fx.knowledge * ringFade() * focDim();
      if (kf < 0.02) return;
      var n = Math.min(know.orbit.length, knowCap(1)), hv = know.hover, now = performance.now();
      for (var i = 0; i < n; i++) {
        var k = know.orbit[i];
        if (dt) k.a += k.sp * dt * cur[9];
        var pt = ringPt(k.ring, k.a);
        if ((pt.z >= 0) !== front || pt.hidden) continue;
        k.sx = pt.x; k.sy = pt.y; k.seen = now;
        if (focHidden(k)) continue;
        var on = hv === k ? 1 : 0;
        var r = (1.5 + k.size * 1.5) * look.orbitDot * (front ? 1 : 0.8) * (1 + on * 0.7);
        c.fillStyle = rgba(k.col, Math.min(1, (front ? 0.75 + 0.25 * pt.z : 0.35) * kf + on * 0.3));
        c.beginPath(); c.arc(pt.x, pt.y, r, 0, 6.2832); c.fill();
        if (front) {
          c.strokeStyle = rgba(k.col, 0.35 * kf); c.lineWidth = 1;
          c.beginPath(); c.arc(pt.x, pt.y, r + 1.8, 0, 6.2832); c.stroke();
        }
        know.hits.push({ x: pt.x, y: pt.y, k: k });
      }
    }
    function hitKnow(x, y) {
      var best = null, bd = 81;   // trong 9px
      for (var i = know.hits.length - 1; i >= 0; i--) {
        var h = know.hits[i], d = (h.x - x) * (h.x - x) + (h.y - y) * (h.y - y);
        if (d < bd) { bd = d; best = h.k; }
      }
      return best;
    }
    function knowKindKey(b) {
      if (b.kind === "star") return b.proc ? "planet.k_proc" : "planet.k_star";
      if (b.kind === "orbit") return ["planet.k_skill", "planet.k_workflow", "planet.k_memory"][b.ring | 0] || "planet.k_skill";
      return "planet.k_debris";
    }
    function showBHTip(x, y) {
      if (opts.tips === false) { tip.hidden = true; return; }
      var t = window.t || function (s) { return s; }, v = t("planet.bh_tip");
      tip.innerHTML = "";
      var n = document.createElement("div"); n.className = "pt-name"; n.textContent = v === "planet.bh_tip" ? "Hố đen chưng cất" : v;
      var ro = document.createElement("div"); ro.className = "pt-know";
      var v2 = t("planet.bh_tip_d", { n: know.debris.length });
      ro.textContent = v2 === "planet.bh_tip_d" ? know.debris.length + " tài liệu thô · bấm để nhìn sâu vào" : v2;
      tip.appendChild(n); tip.appendChild(ro);
      tip.hidden = false;
      var tw = tip.offsetWidth || 140;
      tip.style.left = clamp(x - tw - 14, 6, W - tw - 6) + "px";
      tip.style.top = clamp(y + 12, 6, H - 50) + "px";
    }
    function showKnowTip(k, x, y) {
      if (!k || opts.tips === false) { tip.hidden = true; return; }
      var t = (window.t || function (s) { return s; });
      tip.innerHTML = "";
      var n = document.createElement("div"); n.className = "pt-name"; n.textContent = k.b.title || k.b.path;
      var ro = document.createElement("div"); ro.className = "pt-know";
      ro.textContent = t(knowKindKey(k.b)) + (k.brainName ? " · " + k.brainName : "");
      tip.appendChild(n); tip.appendChild(ro);
      tip.hidden = false;
      var tw = tip.offsetWidth || 140;
      tip.style.left = clamp(x + 14, 6, W - tw - 6) + "px";
      tip.style.top = clamp(y - 10, 6, H - 50) + "px";
    }

    // ---- Hố đen luôn xoay (chủ yêu cầu 2026-10-08, ảnh mẫu: xoáy bụi + luồng bụi bị hút) ----
    // Bụi xoáy trong mặt phẳng ĐÚNG đĩa bồi tụ của shader (nghiêng 0,32 rad, dẹt 0,3, mục 6.3 của
    // 2026-10-tinh-cau-h2o.md): góc tốc độ theo kiểu Kepler (trong nhanh, ngoài chậm), trôi dần
    // vào tâm rồi sinh lại ở rìa. Một luồng bụi cong từ xa chảy vào rìa đĩa. Đang nạp dữ liệu thì
    // xoáy nhanh và dày hơn. Hạt ở nửa SAU đĩa mà rơi vào bóng đen thì bỏ (lớp 2D nằm trên shader).
    var BH_TILT = 0.32, BH_FLAT = 0.3;
    var BH_CAP = { high: [260, 90], balanced: [150, 50], safe: [70, 24], reduced: [70, 0] };
    var bhs = { parts: [], stream: [], init: false, spin: 0 };
    function bhPt(B, r, an, flat) {   // điểm trên đĩa (đơn vị bán kính hố) -> màn hình
      var dx = r * Math.cos(an), dy = (flat || BH_FLAT) * r * Math.sin(an);
      var ca = Math.cos(BH_TILT), sa = Math.sin(BH_TILT);
      return { x: B.x + (ca * dx - sa * dy) * B.r, y: B.y - (sa * dx + ca * dy) * B.r, front: Math.sin(an) <= 0 };
    }
    function bhInit() {
      var cap = BH_CAP[profile] || BH_CAP.balanced, rnd = hashRnd(4242);
      bhs.parts = []; bhs.stream = [];
      for (var i = 0; i < cap[0]; i++) bhs.parts.push({ a: rnd() * 6.2832, r: 1.15 + Math.pow(rnd(), 0.8) * 5.6, j: rnd() });
      for (var k = 0; k < cap[1]; k++) bhs.stream.push({ t: rnd(), ph: rnd() * 6.2832, sp: 0.08 + rnd() * 0.06, w: (rnd() - 0.5) });
      bhs.init = profile;
    }
    function bhStream(B, t, it) {   // luồng bụi: cung bậc hai từ trên-trái xa vào rìa đĩa
      var p0 = { x: B.x - B.r * 9, y: B.y - B.r * 4.2 }, p1 = { x: B.x - B.r * 1.5, y: B.y - B.r * 6.4 }, p2 = bhPt(B, 5.6, -0.6);
      var u = 1 - t, x = u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x, y = u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y;
      var tx = 2 * u * (p1.x - p0.x) + 2 * t * (p2.x - p1.x), ty = 2 * u * (p1.y - p0.y) + 2 * t * (p2.y - p1.y), tl = Math.hypot(tx, ty) || 1;
      var off = (Math.sin(t * 9 + it.ph) * 0.45 + it.w) * B.r * (1.4 - t);
      return { x: x - ty / tl * off, y: y + tx / tl * off };
    }
    function drawBHSwirl(c, now, dt) {
      var B = geo.bh;
      if (!B || !B.r) return;
      if (bhs.init !== profile) bhInit();
      var sp = 1 + 2.5 * ing.k, t = now / 1000;
      c.save();
      c.globalCompositeOperation = "lighter";
      c.lineCap = "round";
      // vệt mờ của luồng bụi (dải tinh vân)
      var s0 = bhStream(B, 0, { ph: 0, w: 0 }), s1 = bhStream(B, 0.5, { ph: 0, w: 0 }), s2 = bhStream(B, 1, { ph: 0, w: 0 });
      c.strokeStyle = "rgba(120,170,255," + (0.09 + 0.1 * ing.k) + ")"; c.lineWidth = B.r * 1.6;
      c.beginPath(); c.moveTo(s0.x, s0.y); c.quadraticCurveTo(2 * s1.x - (s0.x + s2.x) / 2, 2 * s1.y - (s0.y + s2.y) / 2, s2.x, s2.y); c.stroke();
      bhs.stream.forEach(function (it) {
        if (dt) it.t += it.sp * sp * dt;
        if (it.t >= 1) {   // tới rìa đĩa: nhập vào xoáy
          it.t -= 1;
          var p = bhs.parts[(Math.random() * bhs.parts.length) | 0];
          if (p) { p.r = 5.4 + Math.random() * 0.6; p.a = -0.6; }
        }
        var q = bhStream(B, it.t, it), al = Math.sin(Math.PI * it.t) * (0.6 + 0.3 * ing.k);
        c.fillStyle = "rgba(170,205,255," + al + ")";
        c.beginPath(); c.arc(q.x, q.y, 1.4, 0, 6.2832); c.fill();
      });
      // xoáy bụi theo kiểu Kepler
      bhs.parts.forEach(function (p) {
        var w = 0.42 / Math.pow(p.r, 1.2) * sp;
        if (dt) {
          p.a += w * dt;
          p.r -= (0.05 + 0.35 * ing.k) * dt;
          if (p.r < 1.08) { p.r = 5 + Math.random() * 1.6; p.a = Math.random() * 6.2832; }
        }
        var P = bhPt(B, p.r, p.a), Q = bhPt(B, p.r, p.a - Math.min(0.6, w * 0.35 + 0.08));
        if (!P.front && Math.hypot(P.x - B.x, P.y - B.y) < B.r * 1.02) return;   // khuất sau bóng đen
        var dop = 0.55 + 0.45 * Math.cos(p.a + 0.4), k = clamp((p.r - 1.1) / 5, 0, 1);
        var col = k < 0.35 ? [215, 238, 255] : k < 0.7 ? [110, 175, 255] : [160, 120, 255];
        c.strokeStyle = rgba(col, Math.min(1, (0.95 - 0.5 * k) * dop * (0.8 + 0.3 * ing.k)));
        c.lineWidth = 1.3 + (1 - k) * 0.9;
        c.beginPath(); c.moveTo(Q.x, Q.y); c.lineTo(P.x, P.y); c.stroke();
      });
      // vành sáng quanh miệng hố xoay chậm (thấy rõ là hố đang xoay)
      if (dt) bhs.spin += dt * (0.5 + 1.5 * ing.k);
      for (var i = 0; i < 3; i++) {
        var a0 = bhs.spin + i * 2.094;
        c.strokeStyle = "rgba(190,220,255," + (0.45 + 0.25 * ing.k) + ")"; c.lineWidth = 1.5;
        c.beginPath(); c.arc(B.x, B.y, B.r * 1.12, a0, a0 + 1.1); c.stroke();
      }
      c.restore();
      void t;
    }
    function onBlackHole(x, y) { return !!(geo.bh && Math.hypot(x - geo.bh.x, y - geo.bh.y) < Math.max(14, geo.bh.r * 1.8)); }

    // ---- Nhìn sâu vào hố đen: bấm giữa hố đen thì mở cảnh cận (chủ yêu cầu 2026-10-08) ----
    // Màn mở tròn từ hố đen ra cả khung. Giữa là hố đen lớn, đĩa bồi tụ xoay (trong xanh, ngoài
    // hồng cam như ảnh mẫu), hai tia phản lực tím xanh. Tinh thể dữ liệu THÔ (đúng tên file trong
    // sources/, inbox/) xoáy dần vào; cứ 1,4-2,2 giây hai tinh thể trong cùng va nhau: nổ lửa, nổ
    // xanh chưng cất, và một tia kiến thức đã chưng cất bắn ra theo luồng phản lực. Bấm bất kỳ
    // đâu hoặc Esc để quay ra.
    var BHV_CAP = { high: [700, 26], balanced: [400, 20], safe: [160, 12], reduced: [160, 12] };
    var bhv = { k: 0, target: 0, init: false, disk: [], crys: [], booms: [], sparks: [], stars: [], neb: [], names: [], nameI: 0, nextCol: 0 };
    function bhvName() {
      if (ing.on && ing.items && ing.items.length && Math.random() < 0.5) return String(ing.items[(Math.random() * ing.items.length) | 0]);
      if (!bhv.names.length) return "";
      var s = bhv.names[bhv.nameI % bhv.names.length]; bhv.nameI++;
      return s;
    }
    function bhvCrystal(rho) {
      return { name: bhvName(), a: Math.random() * 6.2832, rho: rho, sz: 4.5 + Math.random() * 4, spin: Math.random() * 6.2832,
               vs: (Math.random() - 0.5) * 1.4, hue: Math.random(), col: null };
    }
    function bhvInit() {
      var cap = BHV_CAP[profile] || BHV_CAP.balanced, rnd = hashRnd(777), i;
      bhv.names = know.debris.map(function (d) { return String(d.b.title || d.b.path || ""); }).filter(Boolean);
      bhv.disk = []; bhv.crys = []; bhv.stars = []; bhv.neb = []; bhv.booms = []; bhv.sparks = [];
      for (i = 0; i < cap[0]; i++) bhv.disk.push({ a: rnd() * 6.2832, r: 1.35 + Math.pow(rnd(), 0.9) * 3.3, j: rnd() });
      for (i = 0; i < cap[1]; i++) bhv.crys.push(bhvCrystal(0.4 + rnd() * 0.6));
      for (i = 0; i < 170; i++) bhv.stars.push({ x: rnd(), y: rnd(), s: 0.4 + rnd() * 1.2, tw: rnd() * 6.28 });
      for (i = 0; i < 34; i++) bhv.neb.push({ t: i / 33, o: (rnd() - 0.5) * 0.12, s: 0.05 + rnd() * 0.07 });
      bhv.init = profile;
    }
    function openBlackHole(on) {
      if (on && !bhv.target) { bhvInit(); bhv.nextCol = performance.now() + 900; }
      bhv.target = on ? 1 : 0;
      tip.hidden = true;
    }
    function bhvPos(C, Rm, rho, a) {   // vị trí tinh thể: cùng mặt phẳng đĩa, ít dẹt hơn để thấy rõ
      var dx = rho * Rm * Math.cos(a), dy = rho * Rm * Math.sin(a) * 0.5, ca = Math.cos(-0.18), sa = Math.sin(-0.18);
      return { x: C.x + ca * dx - sa * dy, y: C.y + sa * dx + ca * dy };
    }
    function drawCrystal(c, x, y, s, rot, a, hot) {
      c.save(); c.translate(x, y); c.rotate(rot);
      var g = c.createLinearGradient(-s, -s * 1.6, s, s * 1.6);
      var w = hot ? [255, 210, 140] : [235, 250, 255];
      g.addColorStop(0, rgba(w, 0.95 * a)); g.addColorStop(0.5, "rgba(110,200,255," + 0.85 * a + ")"); g.addColorStop(1, "rgba(150,110,255," + 0.8 * a + ")");
      c.fillStyle = g;
      c.beginPath(); c.moveTo(0, -s * 1.7); c.lineTo(s * 0.8, -s * 0.5); c.lineTo(s * 0.8, s * 0.6); c.lineTo(0, s * 1.5);
      c.lineTo(-s * 0.8, s * 0.6); c.lineTo(-s * 0.8, -s * 0.5); c.closePath(); c.fill();
      c.strokeStyle = "rgba(255,255,255," + 0.5 * a + ")"; c.lineWidth = 0.7;   // cạnh mặt tinh thể
      c.beginPath(); c.moveTo(0, -s * 1.7); c.lineTo(0, s * 1.5); c.moveTo(-s * 0.8, -s * 0.5); c.lineTo(s * 0.8, s * 0.6); c.stroke();
      c.restore();
    }
    function drawBHView(c, now, dt) {
      if (bhv.target === 0 && bhv.k < 0.003) { bhv.k = 0; return; }
      if (bhv.init !== profile) bhvInit();
      bhv.k += (bhv.target - bhv.k) * Math.min(1, dt * (bhv.target ? 3.2 : 4.5));
      var e = smooth(0, 1, bhv.k), B = geo.bh || { x: W * 0.86, y: H * 0.15, r: 12 };
      var C = { x: W / 2, y: H / 2 }, Rb = Math.min(W, H) * 0.1, Rm = Math.min(W, H) * 0.47;
      var ic = { x: B.x + (C.x - B.x) * e, y: B.y + (C.y - B.y) * e }, ir = B.r * 1.5 + (Math.hypot(W, H) - B.r * 1.5) * e;
      var spd = 1 + 1.5 * ing.k, t = now / 1000;
      c.save();
      c.beginPath(); c.arc(ic.x, ic.y, ir, 0, 6.2832); c.clip();
      var bg = c.createRadialGradient(C.x, C.y, 0, C.x, C.y, Math.hypot(W, H) * 0.6);
      bg.addColorStop(0, "rgb(14,18,46)"); bg.addColorStop(1, "rgb(2,4,14)");
      c.fillStyle = bg; c.fillRect(0, 0, W, H);
      bhv.stars.forEach(function (s) {
        c.fillStyle = "rgba(220,235,255," + (0.35 + 0.35 * Math.sin(t * 1.3 + s.tw)) + ")";
        c.fillRect(s.x * W, s.y * H, s.s, s.s);
      });
      c.globalCompositeOperation = "lighter";
      // dải tinh vân bị hút vào (như ảnh mẫu): các đám sáng dọc một đường cong từ trên-trái
      bhv.neb.forEach(function (n) {
        var u = 1 - n.t, p0 = { x: W * 0.05, y: H * 0.12 }, p1 = { x: W * 0.32, y: H * 0.62 }, p2 = { x: C.x - Rb * 2.2, y: C.y + Rb * 0.6 };
        var x = u * u * p0.x + 2 * u * n.t * p1.x + n.t * n.t * p2.x + n.o * W, y = u * u * p0.y + 2 * u * n.t * p1.y + n.t * n.t * p2.y;
        var rr = Math.min(W, H) * n.s, g = c.createRadialGradient(x, y, 0, x, y, rr);
        g.addColorStop(0, "rgba(110,160,255,0.10)"); g.addColorStop(1, "rgba(110,160,255,0)");
        c.fillStyle = g; c.beginPath(); c.arc(x, y, rr, 0, 6.2832); c.fill();
      });
      // đĩa bồi tụ: nửa sau, bóng đen + vành photon, nửa trước
      var tilt = -0.18, ca = Math.cos(tilt), sa = Math.sin(tilt);
      function diskPt(r, an) { var dx = r * Rb * Math.cos(an), dy = 0.26 * r * Rb * Math.sin(an); return { x: C.x + ca * dx - sa * dy, y: C.y + sa * dx + ca * dy }; }
      function diskPass(front) {
        c.lineCap = "round";
        bhv.disk.forEach(function (p) {
          var w = 0.9 / Math.pow(p.r, 1.3) * spd;
          if (front && dt) { p.a += w * dt; p.r -= 0.04 * spd * dt; if (p.r < 1.3) { p.r = 4.4 + Math.random() * 0.3; p.a = Math.random() * 6.2832; } }
          if ((Math.sin(p.a) > 0) !== front) return;   // sin > 0 = nửa GẦN (phía dưới trên màn) = vẽ đè lên hố
          var P = diskPt(p.r, p.a), Q = diskPt(p.r, p.a - 0.12 - w * 0.15), k = clamp((p.r - 1.35) / 3.3, 0, 1);
          var col = k < 0.25 ? [225, 242, 255] : k < 0.5 ? [120, 180, 255] : k < 0.75 ? [255, 140, 200] : [255, 175, 110];
          var dop = 0.5 + 0.5 * Math.cos(p.a + 0.4);
          c.strokeStyle = rgba(col, (0.55 - 0.3 * k) * (0.5 + 0.5 * dop)); c.lineWidth = 1.6 - k * 0.6;
          c.beginPath(); c.moveTo(Q.x, Q.y); c.lineTo(P.x, P.y); c.stroke();
        });
      }
      diskPass(false);
      // hai tia phản lực vuông góc với đĩa
      var ja = tilt - Math.PI / 2, jx = Math.cos(ja), jy = Math.sin(ja), L = H * 0.42, fl = 0.8 + 0.2 * Math.sin(t * 7);
      for (var s = -1; s <= 1; s += 2) {
        var tx = C.x + jx * L * s, ty = C.y + jy * L * s, jg = c.createLinearGradient(C.x, C.y, tx, ty);
        jg.addColorStop(0, "rgba(230,220,255," + 0.9 * fl + ")"); jg.addColorStop(0.35, "rgba(160,110,255," + 0.5 * fl + ")"); jg.addColorStop(1, "rgba(110,90,255,0)");
        c.strokeStyle = jg;
        c.lineWidth = Rb * 0.5; c.globalAlpha = 0.25; c.beginPath(); c.moveTo(C.x, C.y); c.lineTo(tx, ty); c.stroke();
        c.lineWidth = 2.4; c.globalAlpha = 1; c.beginPath(); c.moveTo(C.x, C.y); c.lineTo(tx, ty); c.stroke();
      }
      c.globalCompositeOperation = "source-over";
      c.fillStyle = "#000"; c.beginPath(); c.arc(C.x, C.y, Rb, 0, 6.2832); c.fill();
      c.globalCompositeOperation = "lighter";
      // Vành photon: gradient PHẢI bắt đầu từ tâm và trong suốt tới mép bóng. Bắt đầu từ 0,95Rb
      // thì canvas tô màu điểm dừng đầu cho cả phần bên trong, lòng hố thành đĩa màu be (chụp thử).
      var pr = c.createRadialGradient(C.x, C.y, 0, C.x, C.y, Rb * 1.35), r0 = 0.95 / 1.35;
      pr.addColorStop(0, "rgba(255,240,215,0)"); pr.addColorStop(r0 - 0.01, "rgba(255,240,215,0)");
      pr.addColorStop(r0, "rgba(255,240,215,0.85)"); pr.addColorStop(r0 + 0.08, "rgba(150,190,255,0.35)"); pr.addColorStop(1, "rgba(120,160,255,0)");
      c.fillStyle = pr; c.beginPath(); c.arc(C.x, C.y, Rb * 1.35, 0, 6.2832); c.fill();
      diskPass(true);
      // tinh thể dữ liệu thô xoáy vào + lịch va chạm
      if (now >= bhv.nextCol && bhv.crys.length >= 2) {
        var ds = bhv.crys.filter(function (q) { return !q.col; }).sort(function (p, q) { return p.rho - q.rho; });
        if (ds.length >= 2) {
          var A = ds[0], Bc = ds[1], pa = bhvPos(C, Rm, A.rho, A.a), pb = bhvPos(C, Rm, Bc.rho, Bc.a);
          var mid = { x: (pa.x + pb.x) / 2, y: (pa.y + pb.y) / 2 };
          A.col = Bc.col = { t0: now, mid: mid, pa: pa, pb: pb };
          A.from = pa; Bc.from = pb;
        }
        bhv.nextCol = now + (1400 + Math.random() * 800) / spd;
      }
      c.globalCompositeOperation = "source-over";
      var nhan = 0;
      bhv.nhanPts = [];
      bhv.crys.forEach(function (q, qi) {
        var x, y, hot = false;
        if (q.col) {
          var u = clamp((now - q.col.t0) / 450, 0, 1), eu = u * u;
          x = q.from.x + (q.col.mid.x - q.from.x) * eu; y = q.from.y + (q.col.mid.y - q.from.y) * eu; hot = true;
          if (u >= 1) {
            if (q.col.pa === q.from) bhv.booms.push({ px: q.col.mid.x, py: q.col.mid.y, t0: now, axis: Math.random() * 3.1416, fired: false });
            var nq = bhvCrystal(0.92 + Math.random() * 0.08);
            bhv.crys[qi] = nq;
            return;
          }
        } else {
          // Sàn 0,36: dưới mức đó tinh thể lọt vào trong bóng hố (đĩa dẹt 0,5) và vụ nổ bị che.
          if (dt) { q.a += 0.16 / Math.pow(q.rho, 1.3) * spd * dt; q.rho = Math.max(0.36, q.rho - 0.016 * spd * dt); q.spin += q.vs * dt; }
          var P = bhvPos(C, Rm, q.rho, q.a); x = P.x; y = P.y;
        }
        drawCrystal(c, x, y, q.sz, q.spin, 1, hot);
        // Nhãn thưa: chỉ tinh thể ở vòng ngoài, tối đa 6, cách nhau đủ xa (chụp thử thấy chồng chữ).
        var xa = (bhv.nhanPts || []).every(function (np) { return Math.abs(np.x - x) > 150 || Math.abs(np.y - y) > 22; });
        if (q.name && q.rho > 0.62 && !q.col && nhan < 6 && xa) {
          (bhv.nhanPts = bhv.nhanPts || []).push({ x: x, y: y });
          nhan++;
          var nm = q.name.length > 28 ? q.name.slice(0, 27) + "…" : q.name;
          c.font = "500 10px 'Segoe UI', system-ui, sans-serif"; c.textAlign = "center"; c.textBaseline = "top";
          c.fillStyle = "rgba(205,228,255,0.78)"; c.fillText(nm, x, y + q.sz * 1.8 + 3);
        }
      });
      // va chạm: nổ lửa -> nổ xanh chưng cất -> tia kiến thức bắn theo luồng phản lực
      bhv.booms = bhv.booms.filter(function (b) {
        var tb = (now - b.t0) / 1000, R1 = Rb * 0.55;
        if (tb >= 2.2) return false;
        if (tb < 0.6) fireBurst(c, b, R1, tb / 0.6, bhv.sparks);
        if (tb >= 0.5 && tb < 1.5) blueBurst(c, b, R1, (tb - 0.5) / 1.0);
        if (tb >= 0.7) {   // tia kiến thức: từ chỗ nổ vào tâm rồi vọt lên theo tia phản lực
          var u2 = clamp((tb - 0.7) / 1.5, 0, 1), px, py;
          if (u2 < 0.4) { var v = u2 / 0.4; px = b.px + (C.x - b.px) * v; py = b.py + (C.y - b.py) * v; }
          else { var v2 = (u2 - 0.4) / 0.6; px = C.x + jx * L * v2 * (b.axis > 1.57 ? 1 : -1); py = C.y + jy * L * v2 * (b.axis > 1.57 ? 1 : -1); }
          c.save(); c.globalCompositeOperation = "lighter";
          var kg = c.createRadialGradient(px, py, 0, px, py, 9);
          kg.addColorStop(0, "rgba(240,252,255," + (1 - u2 * 0.5) + ")"); kg.addColorStop(1, "rgba(90,180,255,0)");
          c.fillStyle = kg; c.beginPath(); c.arc(px, py, 9, 0, 6.2832); c.fill();
          c.restore();
        }
        return true;
      });
      if (bhv.sparks.length) {
        c.save(); c.globalCompositeOperation = "lighter"; c.lineCap = "round";
        bhv.sparks = bhv.sparks.filter(function (s2) {
          s2.t += dt; if (s2.t >= s2.life) return false;
          var dmp = Math.pow(0.08, dt), al = 1 - s2.t / s2.life;
          s2.vx *= dmp; s2.vy *= dmp; s2.x += s2.vx * dt; s2.y += s2.vy * dt;
          c.strokeStyle = "rgba(255," + Math.round(120 + 110 * al) + "," + Math.round(40 * al) + "," + al + ")"; c.lineWidth = 1.5;
          c.beginPath(); c.moveTo(s2.x, s2.y); c.lineTo(s2.x - s2.vx * 0.035, s2.y - s2.vy * 0.035); c.stroke();
          return true;
        });
        c.restore();
      }
      // chữ
      var tr = window.t || function (k) { return k; }, tx2 = function (k, v, fb) { var s3 = tr(k, v); return s3 === k ? fb : s3; };
      c.globalAlpha = e;
      c.textAlign = "left"; c.textBaseline = "top";
      c.font = "700 14px 'Segoe UI', system-ui, sans-serif"; c.fillStyle = "rgba(225,240,255,0.95)";
      c.fillText(tx2("planet.bh_title", null, "Hố đen chưng cất"), 24, 22);
      c.font = "500 11.5px 'Segoe UI', system-ui, sans-serif"; c.fillStyle = "rgba(190,215,245,0.85)";
      var dang = ing.on && ing.items && ing.items.length;
      c.fillText(dang ? tx2("planet.bh_now", { ten: ing.items[0] }, "Đang chưng cất: " + ing.items[0])
                      : tx2("planet.bh_wait", { n: bhv.names.length }, bhv.names.length + " tài liệu thô đang chờ chưng cất"), 24, 42);
      c.textAlign = "center"; c.fillStyle = "rgba(190,215,245,0.7)";
      c.fillText(tx2("planet.bh_exit", null, "Bấm bất kỳ đâu hoặc Esc để quay lại"), W / 2, H - 28);
      c.globalAlpha = 1;
      c.restore();
    }

    // ---- Giai đoạn 3: ghim H2O Studio trên Trái Đất (đích của tia sáng sau khi nạp) ----
    function studioPt() {
      var st = window.JoyceVNGeo && window.JoyceVNGeo.studio;
      if (!st || !geo.R) return null;
      var v = toView(Gm, geoVec(st.lat, st.lon));
      if (v[2] < 0.08) return null;   // đang ở nửa khuất
      return { x: geo.cx + v[0] * geo.R, y: geo.cy - v[1] * geo.R };
    }

    // ---- Tia tri thức khi hỏi Joyce (docs/dev/2026-10-tia-tri-thuc-khi-hoi.md) ----
    // Chỉ diễn đúng việc Joyce thật sự làm trong lượt: mỗi tài liệu đọc / nguồn ngoài gọi là một
    // sợi sáng về ghim H2O Studio. Không đọc gì thì không có sợi nào, chỉ một nhịp sáng ở lõi.
    var TR_MAX = 24, TR_GROW = 0.5, TR_BACK = 0.7, TR_GLOW = 10000;
    function trMoi() { return { on: false, t0: 0, tAns: 0, tDone: 0, threads: [], keys: {}, used: [], glowUntil: 0 }; }
    var tr = trMoi();
    function trPin() {   // ghim H2O Studio; khuất sau địa cầu thì mép địa cầu phía ghim
      var p = studioPt();
      if (p) return p;
      var st = window.JoyceVNGeo && window.JoyceVNGeo.studio;
      if (st && geo.R) {
        var v = toView(Gm, geoVec(st.lat, st.lon)), l = Math.hypot(v[0], v[1]) || 1;
        return { x: geo.cx + v[0] / l * geo.R, y: geo.cy - v[1] / l * geo.R };
      }
      return { x: geo.cx, y: geo.cy };
    }
    function trSatPos(id) {
      var all = sats.slice();
      if (sun) all.push(sun);
      if (moon) all.push(moon);
      for (var i = 0; i < all.length; i++) {
        var s = all[i];
        if (s && s.p && s.pt && String(s.p.id) === String(id)) return { x: s.pt.x, y: s.pt.y };
      }
      return null;
    }
    function traceTurn(pha, d) {
      var now = performance.now();
      d = d || {};
      if (pha === "start") { tr = trMoi(); tr.on = true; tr.t0 = now; return; }
      if (pha === "done") {
        if (!tr.on) return;
        if (!tr.tAns) tr.tAns = now;
        tr.tDone = now; tr.on = false;
        tr.used = tr.threads.filter(function (x) { return x.kind === "src"; }).map(function (x) { return x.k; });
        tr.glowUntil = now + TR_BACK * 1000 + TR_GLOW;
        return;
      }
      if (!tr.on) { tr = trMoi(); tr.on = true; tr.t0 = now; }   // an toàn khi thiếu "start"
      if (pha === "answer") { if (!tr.tAns) tr.tAns = now; return; }
      if (tr.threads.length >= TR_MAX) return;
      var key = pha === "source" ? "s" + d.id : "g" + (d.kind === "sat" ? d.id : d.label);
      if (tr.keys[key]) return;
      var th = { t0: now, ph: Math.random(), bend: (Math.random() - 0.5) * 0.6 };
      if (pha === "source") {
        var k = know.byId[d.id];
        if (!k) return;
        th.kind = "src"; th.k = k;
      } else if (pha === "gate") {
        th.kind = d.kind === "sat" ? "sat" : "edge"; th.id = d.id; th.label = String(d.label || "");
        th.gi = tr.threads.filter(function (x) { return x.kind === "edge"; }).length;
      } else return;
      // Bộ não nói một câu mở đầu ("Em sẽ kiểm tra Wiki...") RỒI mới đọc file: một nguồn GHÉP ĐƯỢC
      // tới sau nhịp "answer" thì mở lại vòng thu thập, sợi cũ hiện lại, tới đoạn trả lời sau mới
      // co về. Lệnh gọi không khớp gì thì không mở lại.
      if (tr.tAns) tr.tAns = 0;
      tr.keys[key] = 1;
      tr.threads.push(th);
    }
    function trStart(th) {
      if (th.kind === "src") return knowPos(th.k);
      if (th.kind === "sat") return trSatPos(th.id);
      var ins = (opts.insets && opts.insets()) || { left: 0, top: 0 };
      return { x: (ins.left || 0) + 26, y: (ins.top || 0) + 70 + th.gi * 46 };
    }
    function trCurve(A, B, bend, u) { return bez(A, B, bend, u); }
    function drawTrace(c, now) {
      var song = tr.on && !tr.tAns, lite = profile === "safe" || profile === "reduced";
      if (!tr.on && !tr.tAns && now > tr.glowUntil) return;
      if (!tr.on && tr.tAns && now - tr.tAns > (TR_BACK + 1.2) * 1000 && now > tr.glowUntil) return;
      var P = trPin(), maxR = Math.max(W, H) * 0.9;
      c.save();
      c.globalCompositeOperation = "lighter";
      // 1. Vòng sóng quét từ H2O, lặp mỗi 2,4 giây tới khi có câu trả lời
      if (song) {
        for (var w = 0; w < (lite ? 1 : 2); w++) {
          var ph = ((now - tr.t0) / 2400 + w * 0.5) % 1;
          if (lite && (now - tr.t0) > 2400) break;
          c.strokeStyle = "rgba(90,220,255," + 0.32 * (1 - ph) + ")"; c.lineWidth = 1.5;
          c.beginPath(); c.arc(P.x, P.y, 6 + ph * maxR, 0, 6.2832); c.stroke();
        }
      }
      // 2. Sợi sáng: mọc dần từ nguồn về H2O, hạt sáng trôi về H2O; trả lời thì co về H2O
      var back = tr.tAns ? clamp((now - tr.tAns) / (TR_BACK * 1000), 0, 1) : 0;
      if (back < 1) {
        c.lineCap = "round";
        tr.threads.forEach(function (th) {
          var A = trStart(th);
          if (!A) return;
          var grow = clamp((now - th.t0) / (TR_GROW * 1000), 0, 1), u0 = back * back, u1 = grow;
          if (u1 <= u0) return;
          var col = th.kind === "src" ? th.k.col : th.kind === "sat" ? PAL.gold : PAL.mint;
          var bendK = lite ? 0 : th.bend, n = 18, pts = [];
          for (var i = 0; i <= n; i++) pts.push(trCurve(A, P, bendK, u0 + (u1 - u0) * i / n));
          for (var pass = 0; pass < 2; pass++) {
            c.strokeStyle = pass ? rgba([235, 250, 255], 0.75) : rgba(col, 0.18);
            c.lineWidth = pass ? 1.3 : 5;
            c.beginPath(); c.moveTo(pts[0].x, pts[0].y);
            for (var j = 1; j < pts.length; j++) c.lineTo(pts[j].x, pts[j].y);
            c.stroke();
          }
          if (!lite) for (var q = 0; q < 3; q++) {   // hạt sáng trôi về H2O
            var s = ((now - th.t0) / 1000 * 0.55 + q / 3 + th.ph) % 1;
            if (s < u0 || s > u1) continue;
            var pp = trCurve(A, P, bendK, s);
            c.fillStyle = rgba(col, 0.95); c.beginPath(); c.arc(pp.x, pp.y, 2, 0, 6.2832); c.fill();
          }
          if (back === 0) {   // nguồn đang được đọc: vòng sáng nhấp nháy
            var rr = 6 + 2 * Math.sin(now / 160 + th.ph * 6);
            c.strokeStyle = rgba(col, 0.85); c.lineWidth = 1.4;
            c.beginPath(); c.arc(A.x, A.y, rr, 0, 6.2832); c.stroke();
          }
          if (th.kind === "edge" && back === 0) {   // cổng nguồn ngoài ở mép trái + tên nguồn
            c.globalCompositeOperation = "source-over";
            c.font = "600 10.5px 'Segoe UI', system-ui, sans-serif"; c.textAlign = "left"; c.textBaseline = "middle";
            c.fillStyle = "rgba(200,255,240,0.9)"; c.fillText(th.label, A.x + 12, A.y);
            c.globalCompositeOperation = "lighter";
          }
        });
      }
      // 3. Kiến thức về tới nơi: H2O loé sáng; không đọc gì thì chỉ một nhịp sáng nhẹ ở lõi
      if (tr.tAns) {
        var coSoi = tr.threads.length > 0, fu = (now - tr.tAns) / 1000 - (coSoi ? TR_BACK : 0);
        if (fu >= 0 && fu < 1.2) {
          var e = fu / 1.2, a = 1 - e;
          if (coSoi) {
            var gr = c.createRadialGradient(P.x, P.y, 0, P.x, P.y, 8 + 46 * e);
            gr.addColorStop(0, "rgba(255,255,255," + a + ")"); gr.addColorStop(0.4, "rgba(120,230,255," + 0.7 * a + ")");
            gr.addColorStop(1, "rgba(120,230,255,0)");
            c.fillStyle = gr; c.beginPath(); c.arc(P.x, P.y, 8 + 46 * e, 0, 6.2832); c.fill();
            c.strokeStyle = "rgba(150,240,255," + 0.6 * a + ")"; c.lineWidth = 1.6;
            c.beginPath(); c.arc(P.x, P.y, 10 + 80 * e, 0, 6.2832); c.stroke();
          } else {
            var cr = geo.R * 0.55, cg = c.createRadialGradient(geo.cx, geo.cy, 0, geo.cx, geo.cy, cr);
            cg.addColorStop(0, "rgba(150,230,255," + 0.22 * a + ")"); cg.addColorStop(1, "rgba(150,230,255,0)");
            c.fillStyle = cg; c.beginPath(); c.arc(geo.cx, geo.cy, cr, 0, 6.2832); c.fill();
          }
        }
      }
      // 4. Thiên thể đã dùng còn sáng thêm 10 giây
      if (tr.used.length && now < tr.glowUntil) {
        var ga = clamp((tr.glowUntil - now) / 3000, 0, 1);
        tr.used.forEach(function (k) {
          var p = knowPos(k);
          if (!p) return;
          c.strokeStyle = rgba(k.col, 0.7 * ga); c.lineWidth = 1.3;
          c.beginPath(); c.arc(p.x, p.y, 6 + Math.sin(now / 300) * 1.2, 0, 6.2832); c.stroke();
        });
      }
      c.restore();
    }

    // ---- Big Bang khi tìm kiếm (giai đoạn 2, mục 6 của docs/dev/2026-10-bau-troi-tri-thuc.md) ----
    // Bản 1.0.6 theo góp ý chủ (2026-10-08): tinh cầu kiến thức GIỮ NGUYÊN CHỖ trên bầu trời và
    // phóng to tại chỗ. Với mỗi kết quả: các thiên thể lân cận lao vào nó (0,3-1,1s), nổ LỬA vàng
    // cam (1,1-1,7s), rồi nổ XANH chưng cất có hai tia sáng như chuẩn tinh (1,6-2,6s). Tinh cầu là
    // khối ĐÁ lồi lõm có quầng màu dải ngân hà, lớn lên theo độ khớp (1,6-2,7s), và ánh Mặt Trời
    // chiếu dần lên (2,0-3,6s): khớp nhất sáng nhất. Máy yếu bỏ va chạm và vụ nổ.
    var FOC_MAX = 12, FOC_MORE = 30;
    var FOC_T = { dim: 0.3, hit: 1.1, fire: 0.6, blue0: 1.6, blue: 1.0, grow0: 1.6, grow1: 2.7, sun0: 2.0, sun1: 3.6, close: 0.8 };
    var FOC_GALAXY = [[255, 92, 190], [80, 150, 255], [150, 100, 255]];   // hồng, xanh, tím
    function focDim() {
      var d = foc ? 1 - 0.7 * (foc.dark || 0) : 1;
      // đang quét tìm kiến thức cho câu hỏi (tia tri thức): sao mờ đi một chút
      if (typeof tr !== "undefined" && tr.on && !tr.tAns) d *= 0.8;
      return d;
    }
    // Thiên thể đang là kết quả, hoặc đã lao vào vụ nổ: trời nền không vẽ nó trong lúc diễn.
    function focHidden(k) { return !!(foc && k && k.b && (foc.ids[k.b.id] || foc.gone[k.b.id])); }
    // Chỗ THẬT của một thiên thể trên màn hình, kể cả khi nó không được vẽ (vượt trần, khuất).
    function knowPos(k) {
      if (!k) return null;
      if (k.v) {
        var p = camRot(k.v[0], k.v[1], k.v[2]);
        return { x: geo.cx + p[0] * geo.R, y: geo.cy - p[1] * geo.R };
      }
      if (k.ring != null && k.a != null) { var pt = ringPt(k.ring, k.a); return { x: pt.x, y: pt.y }; }
      if (k.rho != null && geo.bh) {
        var m = Math.min(W, H);
        return { x: geo.bh.x + Math.cos(k.a) * k.rho * m, y: geo.bh.y + Math.sin(k.a) * k.rho * m * 0.55 };
      }
      return k.sx != null ? { x: k.sx, y: k.sy } : null;
    }
    // Thiên thể nằm SAU địa cầu có chỗ thật rơi vào giữa đĩa hành tinh: nổ và lớn lên ở đó thì
    // đè lên mặt địa cầu (ảnh chụp thử 2026-10-08). Đẩy ra sát mép, cùng hướng.
    function focAvoidEarth(p, r) {
      var dx = p.x - geo.cx, dy = p.y - geo.cy, d = Math.hypot(dx, dy), mn = geo.R + r + 8;
      if (d >= mn) return p;
      if (d < 0.01) { dx = 0; dy = -1; d = 1; }
      return { x: geo.cx + dx / d * mn, y: geo.cy + dy / d * mn };
    }
    function focClamp(p, r) {
      return { x: clamp(p.x, r + 12, Math.max(r + 12, W - r - 12)), y: clamp(p.y, r + 28, Math.max(r + 28, H - r - 40)) };
    }
    function focusKnowledge(d) {
      var now = performance.now();
      if (!d || !d.hits || !d.hits.length) {
        if (foc && !foc.closing) { foc.closing = true; foc.tc = now; }
        return;
      }
      var items = [], more = [], ids = {}, nB = 0;
      for (var bk in know.bi) nB++;
      d.hits.forEach(function (h, i) {
        if (!h || !h.id) return;
        ids[h.id] = 1;
        var k = know.byId[h.id], br = know.bi[h.brain];
        var rnd = hashRnd((parseInt(h.id, 16) || 0) ^ 0x5bd1e995);
        if (!k) {   // ngoài dữ liệu bầu trời đang có: đặt lên vòm trời theo id, như một ngôi sao
          var lon = ((br ? br.i : 0) + 0.08 + rnd() * 0.84) / Math.max(1, nB) * 6.2832;
          var lat = -0.35 + rnd() * 1.55, dist = 1.55 + rnd() * 1.05;
          k = { b: h, col: br ? br.col : PAL.gold, brainName: br ? br.name : (h.brain || ""), size: clamp(+h.size || 0, 0, 1),
                ph: 0, v: [Math.cos(lat) * Math.sin(lon) * dist, Math.sin(lat) * dist, Math.cos(lat) * Math.cos(lon) * dist] };
        }
        var it = { k: k, h: h, rank: items.length + more.length, del: Math.min(i, 11) * 0.035 + rnd() * 0.08,
                   axis: rnd() * 3.1416, rock: (rnd() * 6) | 0, spin: rnd() * 6.2832, tw: 0.8 + rnd() * 1.6,
                   off: { x: 0, y: 0 }, gk: 0, fired: false };
        if (items.length < FOC_MAX) items.push(it); else if (more.length < FOC_MORE) more.push(it);
      });
      if (!items.length) return;
      var sc = clamp(geo.R / 150, 0.7, 1.4);
      items.forEach(function (it) {
        it.rF = (7 + 17 * Math.pow(1 - it.rank / (FOC_MAX - 1), 1.3)) * sc;
        it.lit = it.rank === 0 ? 1 : Math.max(0.35, 0.78 - it.rank * 0.04);
        it.p0 = focClamp(focAvoidEarth(knowPos(it.k) || { x: geo.cx, y: geo.cy - geo.R * 1.8 }, it.rF), it.rF);
      });
      // Giãn chỗ: to ra thì hai tinh cầu gần nhau có thể đè lên nhau. Đẩy nhẹ cho đủ khoảng trống
      // và lưu thành ĐỘ LỆCH so với chỗ thật (chỗ thật vẫn trôi theo vành, theo camera).
      for (var pass = 0; pass < 40; pass++) {
        for (var a1 = 0; a1 < items.length; a1++) {
          for (var b1 = a1 + 1; b1 < items.length; b1++) {
            var A = items[a1], B = items[b1];
            var dx = (B.p0.x + B.off.x) - (A.p0.x + A.off.x), dy = (B.p0.y + B.off.y) - (A.p0.y + A.off.y);
            var dd = Math.hypot(dx, dy), mn = A.rF + B.rF + 16;
            if (dd < 0.01) { dx = Math.cos(B.axis); dy = Math.sin(B.axis); dd = 0.01; }
            if (dd < mn) {
              var push = (mn - dd) / 2, ux = dx / dd, uy = dy / dd;
              A.off.x -= ux * push; A.off.y -= uy * push; B.off.x += ux * push; B.off.y += uy * push;
            }
          }
          var E = items[a1], ep = focAvoidEarth({ x: E.p0.x + E.off.x, y: E.p0.y + E.off.y }, E.rF);
          E.off.x = ep.x - E.p0.x; E.off.y = ep.y - E.p0.y;   // giãn chỗ không được đẩy ngược vào đĩa
        }
      }
      // Mảnh va chạm: thiên thể ĐANG HIỆN gần mỗi kết quả (lấy từ điểm bấm khung trước) lao vào
      // nó; thiếu thì thêm vài mảnh đá từ quanh đó cho đủ 4.
      var gone = {}, frags = [], pts = know.hits.slice();
      items.forEach(function (it) {
        var cand = [];
        pts.forEach(function (h) {
          if (!h.k || !h.k.b || ids[h.k.b.id] || gone[h.k.b.id]) return;
          var dd2 = Math.hypot(h.x - it.p0.x, h.y - it.p0.y);
          if (dd2 > 2 && dd2 < 140) cand.push({ h: h, d: dd2 });
        });
        cand.sort(function (p, q) { return p.d - q.d; });
        var rnd = hashRnd(it.rank * 7919 + 17);
        cand.slice(0, 5).forEach(function (c0) {
          gone[c0.h.k.b.id] = 1;
          frags.push({ it: it, x0: c0.h.x, y0: c0.h.y, col: c0.h.k.col, bend: (rnd() - 0.5) * 0.8, s: 1.6 + rnd() * 1.4 });
        });
        for (var q = Math.min(cand.length, 5); q < 4; q++) {
          var ag = rnd() * 6.2832, rr = 60 + rnd() * 60;
          frags.push({ it: it, x0: it.p0.x + Math.cos(ag) * rr, y0: it.p0.y + Math.sin(ag) * rr, col: KNOW_DUST,
                       bend: (rnd() - 0.5) * 0.8, s: 1.4 + rnd() * 1.2 });
        }
      });
      var lite = profile === "safe" || profile === "reduced";
      var toBuild = [];
      items.forEach(function (it) { if (ROCK[it.rock] === undefined && toBuild.indexOf(it.rock) < 0) toBuild.push(it.rock); });
      foc = { toBuild: toBuild, t0: now, q: d.q || "", items: items, more: more, total: d.total || d.hits.length, ids: ids,
              gone: lite ? {} : gone, frags: lite ? [] : frags, sparks: [], lite: lite, closing: false, tc: 0, dark: 0 };
    }

    // ---- mặt đá lồi lõm của tinh cầu kiến thức: 6 mẫu dựng MỘT lần bằng nhiễu + miệng hố ----
    // Bảng hoán vị cho nhiễu thay cho băm bằng Math.sin: nhanh gấp nhiều lần, đủ để dựng mặt đá
    // ngay trong lúc trời đang tối lại mà không giật khung.
    var ROCK = [], NP = null, NV = null;
    function h3(i, j, k) {
      if (!NP) {
        var r0 = hashRnd(1337), pm = [], q;
        NP = new Uint8Array(512); NV = new Float32Array(256);
        for (q = 0; q < 256; q++) { pm.push(q); NV[q] = r0(); }
        for (q = 255; q > 0; q--) { var w = (r0() * (q + 1)) | 0, tmp = pm[q]; pm[q] = pm[w]; pm[w] = tmp; }
        for (q = 0; q < 512; q++) NP[q] = pm[q & 255];
      }
      return NV[NP[NP[NP[i & 255] + (j & 255)] + (k & 255)]];
    }
    function vnoise(x, y, z) {
      var xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), xf = x - xi, yf = y - yi, zf = z - zi;
      var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
      function L(a, b, t) { return a + (b - a) * t; }
      return L(L(L(h3(xi, yi, zi), h3(xi + 1, yi, zi), u), L(h3(xi, yi + 1, zi), h3(xi + 1, yi + 1, zi), u), v),
               L(L(h3(xi, yi, zi + 1), h3(xi + 1, yi, zi + 1), u), L(h3(xi, yi + 1, zi + 1), h3(xi + 1, yi + 1, zi + 1), u), v), w);
    }
    function fbm3(x, y, z, oct) {
      var s = 0, a = 0.5, f = 1;
      for (var o = 0; o < oct; o++) { s += a * vnoise(x * f, y * f, z * f); f *= 2.03; a *= 0.5; }
      return s / (1 - Math.pow(0.5, oct));
    }
    // Mặt đá đã dựng (hoặc null nếu chưa / không dựng được). KHÔNG tự dựng ở đây: dựng tốn vài
    // chục mili giây, nên drawKnowFocus dựng dần MỖI KHUNG MỘT MẪU (foc.toBuild).
    function rockSprite(v) { return ROCK[v] || null; }
    function buildRockNow(v) {
      if (ROCK[v] !== undefined) return;
      if (typeof document === "undefined") { ROCK[v] = null; return; }
      try { ROCK[v] = buildRock(v); } catch (e) { ROCK[v] = null; }
    }
    function buildRock(seed) {
      var S = 96, cv = document.createElement("canvas");
      cv.width = cv.height = S;
      var g = cv.getContext("2d"), img = g.createImageData(S, S), D = img.data;
      var rnd = hashRnd(seed * 2654435761 + 99), off = rnd() * 40, cr = [];
      for (var i = 0; i < 9; i++) {
        var la = Math.asin(rnd() * 2 - 1), lo = rnd() * 6.2832;
        cr.push([Math.cos(la) * Math.sin(lo), Math.sin(la), Math.cos(la) * Math.cos(lo), 0.12 + rnd() * 0.25]);
      }
      var Hh = new Float32Array(S * S), NZ = new Float32Array(S * S);
      for (var y = 0; y < S; y++) for (var x = 0; x < S; x++) {
        var nx = (x + 0.5) / S * 2 - 1, ny = (y + 0.5) / S * 2 - 1, r2 = nx * nx + ny * ny, id = y * S + x;
        if (r2 > 1) { Hh[id] = -1; continue; }
        var nz = Math.sqrt(1 - r2), h = fbm3(nx * 2.3 + off, ny * 2.3, nz * 2.3, 4);
        for (var c = 0; c < cr.length; c++) {   // miệng hố: lòng lõm + vành nổi
          var C = cr[c], dot = nx * C[0] - ny * C[1] + nz * C[2];
          var q = Math.acos(clamp(dot, -1, 1)) / C[3];
          if (q < 1) h -= 0.22 * (1 - q * q);
          else if (q < 1.25) h += 0.12 * (1 - (q - 1) / 0.25);
        }
        Hh[id] = h; NZ[id] = nz;
      }
      for (var y2 = 0; y2 < S; y2++) for (var x2 = 0; x2 < S; x2++) {
        var j = y2 * S + x2, o4 = j * 4, hv = Hh[j];
        if (hv < -0.5) { D[o4 + 3] = 0; continue; }
        var hl = x2 > 0 && Hh[j - 1] > -0.5 ? Hh[j - 1] : hv, hr = x2 < S - 1 && Hh[j + 1] > -0.5 ? Hh[j + 1] : hv;
        var hu = y2 > 0 && Hh[j - S] > -0.5 ? Hh[j - S] : hv, hd = y2 < S - 1 && Hh[j + S] > -0.5 ? Hh[j + S] : hv;
        // nổi khối: ánh sáng nướng sẵn từ trên-trái (ánh nắng thật phủ lên lúc vẽ)
        var shade = clamp(0.88 + ((hl - hr) * 0.9 + (hu - hd) * 1.1) * 5, 0.45, 1.4);
        var limb = 0.55 + 0.45 * NZ[j], kk = clamp(hv, 0, 1);
        var nx2 = (x2 + 0.5) / S * 2 - 1, ny2 = (y2 + 0.5) / S * 2 - 1;
        var pink = smooth(0.58, 0.78, fbm3(nx2 * 1.6 + off * 2, ny2 * 1.6, NZ[j] * 1.6 + 5, 2)) * 0.24;
        var blue = smooth(0.58, 0.78, fbm3(nx2 * 1.6 + 11, ny2 * 1.6 + off, NZ[j] * 1.6, 2)) * 0.22;
        var base = [64 + 112 * kk, 58 + 104 * kk, 54 + 90 * kk];
        for (var ch = 0; ch < 3; ch++) {
          var vcol = base[ch] * shade * limb;
          vcol += (FOC_GALAXY[0][ch] - vcol) * pink;
          vcol += (FOC_GALAXY[1][ch] - vcol) * blue;
          D[o4 + ch] = clamp(Math.round(vcol), 0, 255);
        }
        var edge = (1 - Math.sqrt(nx2 * nx2 + ny2 * ny2)) * S * 0.5;
        D[o4 + 3] = Math.round(clamp(edge, 0, 1) * 255);
      }
      g.putImageData(img, 0, 0);
      return cv;
    }
    function drawRockPlanet(c, it, r, a, lit, now, hot) {
      if (r < 0.6 || a < 0.01) return;
      var x = it.px, y = it.py, hr = r * 2.4, ag = now / 1000 * 0.25 + it.spin;
      // quầng màu dải ngân hà xoay chậm quanh tinh cầu
      for (var j = 0; j < 3; j++) {
        var col = FOC_GALAXY[j], ox = x + Math.cos(ag + j * 2.094) * r * 0.55, oy = y + Math.sin(ag + j * 2.094) * r * 0.55;
        var g = c.createRadialGradient(ox, oy, r * 0.2, ox, oy, hr);
        g.addColorStop(0, rgba(col, (0.2 + 0.2 * lit) * a)); g.addColorStop(1, rgba(col, 0));
        c.fillStyle = g; c.beginPath(); c.arc(ox, oy, hr, 0, 6.2832); c.fill();
      }
      var sx = geo.sun ? geo.sun.x - x : -1, sy = geo.sun ? geo.sun.y - y : -1, sd = Math.hypot(sx, sy) || 1;
      sx /= sd; sy /= sd;
      c.save();
      c.beginPath(); c.arc(x, y, r, 0, 6.2832); c.clip();
      c.globalAlpha = a;
      var spr = rockSprite(it.rock);
      if (spr) { c.save(); c.translate(x, y); c.rotate(it.spin); c.drawImage(spr, -r, -r, r * 2, r * 2); c.restore(); }
      else { c.fillStyle = "rgb(120,110,100)"; c.fillRect(x - r, y - r, r * 2, r * 2); }
      // Nắng: phía hướng Mặt Trời ấm sáng, phía kia chìm vào đêm; chưa được chiếu thì tối cả quả.
      var lg = c.createLinearGradient(x + sx * r, y + sy * r, x - sx * r, y - sy * r);
      lg.addColorStop(0, "rgba(255,226,170," + 0.32 * lit + ")");
      lg.addColorStop(0.42, "rgba(0,0,0," + (0.08 + 0.55 * (1 - lit)) + ")");
      lg.addColorStop(1, "rgba(0,0,0," + (0.6 + 0.3 * (1 - lit)) + ")");
      c.fillStyle = lg; c.fillRect(x - r, y - r, r * 2, r * 2);
      c.restore();
      if (lit > 0.05) {   // viền nắng mảnh phía Mặt Trời
        var sa = Math.atan2(sy, sx);
        c.strokeStyle = "rgba(255,226,170," + 0.6 * lit * a + ")"; c.lineWidth = 1.2;
        c.beginPath(); c.arc(x, y, r - 0.4, sa - 1.2, sa + 1.2); c.stroke();
      }
      if (hot) { c.strokeStyle = "rgba(235,248,255," + 0.7 * a + ")"; c.lineWidth = 1.4; c.beginPath(); c.arc(x, y, r + 4, 0, 6.2832); c.stroke(); }
    }
    // Nổ LỬA (ảnh mẫu 4 của chủ): lõi trắng, vàng, cam, mép cháy đỏ sẫm, lửa cuộn, tia lửa văng.
    function fireBurst(c, it, R1, u, sparks) {
      var x = it.px, y = it.py, e = 1 - Math.pow(1 - u, 3), fade = 1 - u;
      if (!it.fired) {
        it.fired = true;
        for (var s = 0; s < 26; s++) {
          var ag = Math.random() * 6.2832, v = (0.9 + Math.random() * 1.6) * R1 * 2.2;
          (sparks || foc.sparks).push({ x: x, y: y, vx: Math.cos(ag) * v, vy: Math.sin(ag) * v, life: 0.5 + Math.random() * 0.5, t: 0 });
        }
      }
      c.save();
      c.globalCompositeOperation = "lighter";
      var rr = R1 * (0.35 + e);
      var g = c.createRadialGradient(x, y, 0, x, y, rr);
      g.addColorStop(0, "rgba(255,255,235," + fade + ")"); g.addColorStop(0.3, "rgba(255,226,120," + 0.95 * fade + ")");
      g.addColorStop(0.62, "rgba(255,128,24," + 0.75 * fade + ")"); g.addColorStop(1, "rgba(150,30,0,0)");
      c.fillStyle = g; c.beginPath(); c.arc(x, y, rr, 0, 6.2832); c.fill();
      for (var j = 0; j < 7; j++) {
        var a2 = it.axis + j * 0.9, d = R1 * 0.55 * e * (0.7 + 0.3 * ((j * 37) % 10) / 10);
        var px = x + Math.cos(a2) * d, py = y + Math.sin(a2) * d, pr = R1 * (0.25 + 0.4 * e);
        var pg = c.createRadialGradient(px, py, 0, px, py, pr);
        pg.addColorStop(0, "rgba(255,214,110," + 0.7 * fade + ")"); pg.addColorStop(0.6, "rgba(255,110,20," + 0.45 * fade + ")");
        pg.addColorStop(1, "rgba(120,20,0,0)");
        c.fillStyle = pg; c.beginPath(); c.arc(px, py, pr, 0, 6.2832); c.fill();
      }
      c.restore();
    }
    // Nổ XANH chưng cất (ảnh mẫu 3): loé trắng xanh, vành đĩa hồng-xanh nghiêng, hai tia sáng
    // ngược chiều như chuẩn tinh, sóng xung kích xanh.
    function blueBurst(c, it, R1, u) {
      var x = it.px, y = it.py, e = 1 - Math.pow(1 - u, 2), env = Math.sin(Math.PI * Math.min(1, u * 1.15)), fade = 1 - u;
      c.save();
      c.globalCompositeOperation = "lighter";
      var fr = R1 * (0.3 + 0.7 * e), fg = c.createRadialGradient(x, y, 0, x, y, fr);
      fg.addColorStop(0, "rgba(240,250,255," + env + ")"); fg.addColorStop(0.4, "rgba(120,190,255," + 0.7 * env + ")");
      fg.addColorStop(1, "rgba(60,120,255,0)");
      c.fillStyle = fg; c.beginPath(); c.arc(x, y, fr, 0, 6.2832); c.fill();
      c.save();
      c.translate(x, y); c.rotate(it.axis + 1.5708); c.scale(1, 0.32);
      c.strokeStyle = "rgba(255,120,200," + 0.5 * fade + ")"; c.lineWidth = 4 * fade + 0.5;
      c.beginPath(); c.arc(0, 0, R1 * (0.5 + 1.5 * e), 0, 6.2832); c.stroke();
      c.strokeStyle = "rgba(100,170,255," + 0.6 * fade + ")";
      c.beginPath(); c.arc(0, 0, R1 * (0.4 + 1.2 * e), 0, 6.2832); c.stroke();
      c.restore();
      var dx = Math.cos(it.axis), dy = Math.sin(it.axis), L = R1 * (1.2 + 4.5 * e);
      c.lineCap = "round";
      for (var s = -1; s <= 1; s += 2) {
        var tx = x + dx * L * s, ty = y + dy * L * s, jg = c.createLinearGradient(x, y, tx, ty);
        jg.addColorStop(0, "rgba(235,248,255," + 0.95 * env + ")"); jg.addColorStop(0.5, "rgba(90,160,255," + 0.5 * env + ")");
        jg.addColorStop(1, "rgba(90,160,255,0)");
        c.strokeStyle = jg;
        c.lineWidth = 9; c.globalAlpha = 0.25; c.beginPath(); c.moveTo(x, y); c.lineTo(tx, ty); c.stroke();
        c.lineWidth = 2.2; c.globalAlpha = 1; c.beginPath(); c.moveTo(x, y); c.lineTo(tx, ty); c.stroke();
      }
      c.strokeStyle = "rgba(120,190,255," + 0.6 * fade + ")"; c.lineWidth = 1.5;
      c.beginPath(); c.arc(x, y, R1 * (0.4 + 2.6 * e), 0, 6.2832); c.stroke();
      c.restore();
    }
    function bez(a, b, bend, e) {   // đường cong bậc hai, điểm điều khiển lệch vuông góc
      var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2, dx = b.x - a.x, dy = b.y - a.y;
      var cx = mx - dy * bend, cy = my + dx * bend, u = 1 - e;
      return { x: u * u * a.x + 2 * u * e * cx + e * e * b.x, y: u * u * a.y + 2 * u * e * cy + e * e * b.y };
    }
    function easeBack(x) { var c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); }
    function drawKnowFocus(c, now, dt) {
      if (!foc) return;
      var T = FOC_T, t = (now - foc.t0) / 1000;
      var close = foc.closing ? clamp((now - foc.tc) / 1000 / T.close, 0, 1) : 0;
      if (close >= 1) { foc = null; return; }
      if (foc.toBuild.length) buildRockNow(foc.toBuild.shift());   // mỗi khung dựng một mẫu đá
      foc.dark = smooth(0, T.dim, t) * (1 - close);
      var lite = foc.lite, n = foc.items.length;
      var grow0 = lite ? T.dim : T.grow0, grow1 = lite ? T.dim + 0.6 : T.grow1;
      var sun0 = lite ? 0.5 : T.sun0, sun1 = lite ? 1.6 : T.sun1;
      c.save();
      c.fillStyle = "rgba(2,8,23," + 0.45 * foc.dark + ")";   // bầu trời tối lại
      c.fillRect(0, 0, W, H);
      // Chỗ sống của từng kết quả: chỗ thật + độ lệch giãn chỗ (mở dần theo lúc lớn lên).
      foc.items.forEach(function (it) {
        it.gk = clamp((t - grow0 - (lite ? 0 : it.del)) / (grow1 - grow0), 0, 1);
        var lp = knowPos(it.k) || it.p0, gs = smooth(0, 1, it.gk);
        var p = focClamp(focAvoidEarth({ x: lp.x + it.off.x * gs, y: lp.y + it.off.y * gs }, it.rF), it.rF);
        it.px = p.x; it.py = p.y;
      });
      if (!lite && !foc.closing) {
        // 1. Thiên thể lân cận lao vào tinh cầu kết quả, nóng đỏ dần khi tới gần.
        c.lineCap = "round";
        foc.frags.forEach(function (f) {
          var it = f.it, u = clamp((t - T.dim - it.del) / (T.hit - T.dim), 0, 1);
          if (u <= 0 || u >= 1) return;
          var e = Math.pow(u, 2.2), P = { x: it.px, y: it.py }, A = { x: f.x0, y: f.y0 };
          var p = bez(A, P, f.bend, e), q = bez(A, P, f.bend, Math.max(0, e - 0.1));
          var hc = [Math.round(f.col[0] + (255 - f.col[0]) * u), Math.round(f.col[1] + (170 - f.col[1]) * u), Math.round(f.col[2] + (60 - f.col[2]) * u)];
          var tg = c.createLinearGradient(q.x, q.y, p.x, p.y);
          tg.addColorStop(0, rgba(hc, 0)); tg.addColorStop(1, rgba(hc, 0.85));
          c.strokeStyle = tg; c.lineWidth = f.s;
          c.beginPath(); c.moveTo(q.x, q.y); c.lineTo(p.x, p.y); c.stroke();
          c.fillStyle = rgba(hc, 0.95); c.beginPath(); c.arc(p.x, p.y, f.s, 0, 6.2832); c.fill();
        });
        // 2. Nổ lửa vàng cam, rồi nổ xanh chưng cất có tia sáng.
        foc.items.forEach(function (it) {
          var R1 = it.rF * 1.7 + 10;
          var uf = (t - T.hit - it.del) / T.fire;
          if (uf >= 0 && uf < 1) fireBurst(c, it, R1, uf, foc.sparks);
          var ub = (t - T.blue0 - it.del) / T.blue;
          if (ub >= 0 && ub < 1) blueBurst(c, it, R1, ub);
        });
      }
      if (foc.sparks.length) {   // tia lửa văng: cam vàng nguội dần sang đỏ
        c.save(); c.globalCompositeOperation = "lighter"; c.lineCap = "round";
        foc.sparks = foc.sparks.filter(function (s) {
          s.t += dt; if (s.t >= s.life) return false;
          var dmp = Math.pow(0.08, dt), al = 1 - s.t / s.life;
          s.vx *= dmp; s.vy *= dmp; s.x += s.vx * dt; s.y += s.vy * dt;
          c.strokeStyle = "rgba(255," + Math.round(120 + 110 * al) + "," + Math.round(40 * al) + "," + al + ")"; c.lineWidth = 1.5;
          c.beginPath(); c.moveTo(s.x, s.y); c.lineTo(s.x - s.vx * 0.035, s.y - s.vy * 0.035); c.stroke();
          return true;
        });
        c.restore();
      }
      // 3. Tia nắng từ Mặt Trời tới tinh cầu khớp nhất.
      var top = foc.items[0], sl = smooth(sun0, sun1, t) * (1 - close) * top.gk;
      if (geo.sun && sl > 0.02) {
        var bg = c.createLinearGradient(geo.sun.x, geo.sun.y, top.px, top.py);
        bg.addColorStop(0, "rgba(255,214,140," + 0.24 * sl + ")"); bg.addColorStop(1, "rgba(255,230,180," + 0.1 * sl + ")");
        c.strokeStyle = bg; c.lineCap = "round";
        c.lineWidth = 10; c.beginPath(); c.moveTo(geo.sun.x, geo.sun.y); c.lineTo(top.px, top.py); c.stroke();
        c.lineWidth = 1.4; c.beginPath(); c.moveTo(geo.sun.x, geo.sun.y); c.lineTo(top.px, top.py); c.stroke();
      }
      // 4. Chòm sao: tài liệu [[liên kết]] tới nhau thì nối vệt sáng.
      var linkA = 0.3 * (1 - close);
      if (linkA > 0.02) {
        c.lineWidth = 1;
        for (var i1 = 0; i1 < n; i1++) for (var j1 = i1 + 1; j1 < n; j1++) {
          var A1 = foc.items[i1], B1 = foc.items[j1], h1 = A1.h, h2 = B1.h;
          if ((h1.links || []).indexOf(h2.stem) >= 0 || (h2.links || []).indexOf(h1.stem) >= 0) {
            c.strokeStyle = "rgba(170,210,255," + linkA * Math.min(A1.gk, B1.gk) + ")";
            c.beginPath(); c.moveTo(A1.px, A1.py); c.lineTo(B1.px, B1.py); c.stroke();
          }
        }
      }
      // 5. Tinh cầu đá lớn dần tại chỗ + nắng chiếu dần.
      foc.items.forEach(function (it, i) {
        var r = it.rF * (lite ? smooth(0, 1, it.gk) : easeBack(it.gk)), a = Math.min(1, it.gk * 3);
        if (close) { r *= 1 - 0.8 * close; a *= 1 - close; }
        var lit = it.lit * smooth(sun0, sun1, t);
        var hot = know.hover === it.k || know.hl === it.h.id;
        drawRockPlanet(c, it, r * (hot ? 1.15 : 1), a, lit, now, hot);
        if (!close && it.gk > 0.6) know.hits.push({ x: it.px, y: it.py, k: it.k });
        if ((it.rank < 3 || hot) && a > 0.3 && r > 2) {   // nhãn: ba kết quả đầu + cái đang trỏ
          var ttl = String(it.h.title || it.h.path || "");
          if (ttl.length > 26) ttl = ttl.slice(0, 25) + "…";
          c.font = (hot ? "700 " : "600 ") + "10px 'Segoe UI', system-ui, sans-serif";
          c.textAlign = "center"; c.textBaseline = "top";
          c.fillStyle = "rgba(225,245,255," + 0.9 * a + ")";
          c.fillText(ttl, it.px, it.py + r + 6);
        }
      });
      // 6. Phần còn lại: lấp lánh tại chỗ thật của chúng + dòng "và N tài liệu nữa".
      var mA = smooth(grow0, grow1, t) * (1 - close);
      if (mA > 0.02) {
        foc.more.forEach(function (it, i) {
          var p = knowPos(it.k);
          if (!p) return;
          p = focClamp(focAvoidEarth(p, 3), 3);
          var hot = know.hover === it.k || know.hl === it.h.id, tw = 0.55 + 0.45 * Math.sin(now / 1000 * it.tw + i);
          c.fillStyle = rgba(it.k.col, mA * tw); c.beginPath(); c.arc(p.x, p.y, hot ? 3.4 : 2.2, 0, 6.2832); c.fill();
          c.strokeStyle = "rgba(170,210,255," + 0.5 * mA * tw + ")"; c.lineWidth = 1;
          c.beginPath(); c.arc(p.x, p.y, (hot ? 3.4 : 2.2) + 3, 0, 6.2832); c.stroke();
          it.px = p.x; it.py = p.y;
          if (!close) know.hits.push({ x: p.x, y: p.y, k: it.k });
        });
        var con = foc.total - n;
        if (con > 0) {
          var tt = (window.t || function (s) { return s; })("planet.k_more", { n: con });
          if (tt === "planet.k_more") tt = "+" + con;
          c.font = "600 10.5px 'Segoe UI', system-ui, sans-serif"; c.textAlign = "center"; c.textBaseline = "top";
          c.fillStyle = "rgba(200,225,245," + 0.8 * mA + ")";
          c.fillText(tt, geo.cx, geo.cy + geo.R * 1.15);
        }
      }
      c.restore();
    }

    // ---------------------------------------------------------------------------
    // HIỆU ỨNG CỦA TAB QUẢ TINH CẦU (lớp 2D). Vẽ SAU những thứ nằm sau hành tinh và TRƯỚC vành
    // + mặt trăng phía trước, nên vành/trăng trước mặt vẫn che đúng. Mọi điểm neo trên bề mặt
    // lưu bằng toạ độ ĐỊA LÝ rồi chiếu qua Gm mỗi khung: kéo xoay quả cầu thì mưa, lốc, núi
    // lửa trôi theo đúng chỗ của nó.
    // ---------------------------------------------------------------------------
    function geoOf(v) {   // khung nhìn -> địa lý (G·v, ngược với toView)
      return [Gm[0][0] * v[0] + Gm[0][1] * v[1] + Gm[0][2] * v[2],
              Gm[1][0] * v[0] + Gm[1][1] * v[1] + Gm[1][2] * v[2],
              Gm[2][0] * v[0] + Gm[2][1] * v[1] + Gm[2][2] * v[2]];
    }
    function norm3(v) { var l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
    function cross3(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
    // Điểm ngẫu nhiên trên nửa cầu ĐANG THẤY (rmax < 1 để tránh sát mép).
    function randView(rmax) {
      var a = Math.random() * 6.2832, r = Math.sqrt(Math.random()) * rmax;
      var x = Math.cos(a) * r, y = Math.sin(a) * r;
      return [x, y, Math.sqrt(Math.max(0, 1 - x * x - y * y))];
    }

    // GIÓ MẠNH (0.65.43, chủ yêu cầu: luồng gió chỉ thổi quanh gần đám mây, từ đám này qua đám
    // kia). Mỗi luồng là một đường dòng ở độ cao mây, theo một trong hai kiểu:
    //   - "nối": chạy dọc cung tròn lớn từ ô mây A sang ô mây B, vồng lên ở giữa đường;
    //   - "vòng": cuộn quanh một ô mây ở rìa đám.
    // Bật riêng gió (không mưa, không sét) thì các ô vẫn có, nhưng là mây trắng (cloudLevel) để gió
    // có chỗ thổi; mưa/sét mới làm mây đen (stormLevel).
    function cellById(id) { for (var i = 0; i < cells.length; i++) if (cells[i].id === id) return cells[i]; return null; }
    function slerpG(a, b, t) {
      var d = clamp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1, 1), om = Math.acos(d);
      if (om < 1e-4) return a.slice();
      var s = Math.sin(om), k1 = Math.sin((1 - t) * om) / s, k2 = Math.sin(t * om) / s;
      return [a[0] * k1 + b[0] * k2, a[1] * k1 + b[1] * k2, a[2] * k1 + b[2] * k2];
    }
    function newStreak() {
      var vc = cells.filter(function (q) { return q.k > 0.2 && toView(Gm, q.g)[2] > 0.05; });
      if (!vc.length) return null;
      var a = vc[(Math.random() * vc.length) | 0];
      if (vc.length > 1 && Math.random() < 0.65) {
        var b = a;
        while (b === a) b = vc[(Math.random() * vc.length) | 0];
        var sp = 0.22 + Math.random() * 0.2, len = 0.16 + Math.random() * 0.12;
        // off: lệch làn so với đường nối, kẹp trong 0,55 bán kính đám mây để gió luôn sát mây
        return { a: a.id, b: b.id, sp: sp, len: len, off: clamp(gauss() * 0.3, -0.55, 0.55), h: 0.55 + Math.random() * 0.45, age: 0, life: (1 + len) / sp };
      }
      return { a: a.id, b: null, ang: Math.random() * 6.2832, sp: 0.8 + Math.random() * 0.8, rad: 0.95 + Math.random() * 0.55,
               len: 1.2 + Math.random(), h: 0.6 + Math.random() * 0.6, age: 0, life: 1.6 + Math.random() * 2 };
    }
    function drawWind(c, dt) {
      var k = fx.wind;
      if (k < 0.01 || !cells.length) { streaks.length = 0; return; }
      var n = profile === "high" ? 26 : profile === "balanced" ? 16 : 8;
      while (streaks.length < n) { var ns = newStreak(); if (!ns) break; streaks.push(ns); }
      if (streaks.length > n) streaks.length = n;
      var L = cloudLift();
      c.save(); c.lineCap = "round";
      for (var i = 0; i < streaks.length; i++) {
        var s = streaks[i], A = cellById(s.a), B = s.b != null ? cellById(s.b) : null;
        if (dt) s.age += dt;
        if (!A || (s.b != null && !B) || s.age >= s.life) { var nn = newStreak(); if (nn) streaks[i] = nn; else { streaks.splice(i, 1); i--; } continue; }
        var fade = Math.sin(Math.PI * s.age / s.life) * k, prev = null, head = null;
        var nrm = B ? norm3(cross3(A.g, B.g)) : null, sg = B ? Math.max(A.sig, B.sig) : A.sig;
        for (var j = 0; j <= 11; j++) {
          var f = j / 11, g, lift;
          if (B) {
            var u = s.age * s.sp - s.len * (1 - f);
            if (u < 0 || u > 1) { prev = null; continue; }
            g = slerpG(A.g, B.g, u);
            g = norm3([g[0] + nrm[0] * s.off * sg, g[1] + nrm[1] * s.off * sg, g[2] + nrm[2] * s.off * sg]);
            lift = L * (s.h + 0.45 * Math.sin(Math.PI * u));
          } else {
            var an = s.ang + s.sp * s.age - s.len * (1 - f);
            g = offsetGeo(A.g, Math.cos(an) * s.rad * A.sig, Math.sin(an) * s.rad * A.sig * 0.7);
            lift = L * s.h;
          }
          var p = scr(g);
          if (p.z < 0.03) { prev = null; continue; }
          var up = upOf(p.v), pt = { x: p.x + up[0] * lift, y: p.y + up[1] * lift, z: p.z };
          if (prev) {
            c.strokeStyle = "rgba(226,242,255," + (fade * f * f * smooth(0.03, 0.35, pt.z) * 0.75).toFixed(3) + ")";
            c.lineWidth = 0.6 + 1.3 * f;
            c.beginPath(); c.moveTo(prev.x, prev.y); c.lineTo(pt.x, pt.y); c.stroke();
          }
          prev = pt; head = g;
        }
        s.gh = head;
      }
      c.restore();
    }

    // ---------------------------------------------------------------------------
    // Ô BÃO + MƯA TỪNG VÙNG (0.65.41, chủ yêu cầu: chỉ mưa dưới những đám mây u tối, mưa rơi từ
    // đáy mây xuống bề mặt, từng vùng cách xa nhau chứ không mưa khắp quả cầu). 2-4 ô bão đặt ở
    // các vùng cách nhau >= 0,5 rad trên nửa cầu đang thấy, trôi theo gió, lớn lên - đứng - tan
    // rồi sinh lại chỗ khác. Shader làm mây trong ô dày + đen (uRc/uRs); lớp 2D vẽ màn mưa, hạt
    // mưa rơi từ đáy mây xuống đất (toé khi chạm) và khối mây nổi lên trên. Sét chỉ đánh trong ô.
    // "Lên trời" trên màn hình = pháp tuyến bề mặt chiếu lên màn, nghiêng thêm về phía trên khung
    // (giữa đĩa pháp tuyến chĩa vào mắt người xem: không nghiêng thì mưa, mây, sét dẹt thành chấm).
    // ---------------------------------------------------------------------------
    function gauss() { return Math.sqrt(-2 * Math.log(Math.random() + 1e-9)) * Math.cos(6.2832 * Math.random()); }
    function tangentBasis(g) {
      var a = Math.abs(g[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0], t1 = norm3(cross3(a, g));
      return [t1, cross3(g, t1)];
    }
    // Dời điểm địa lý g theo hai hướng tiếp tuyến (đơn vị radian trên mặt cầu).
    function offsetGeo(g, du, dv) {
      var T = tangentBasis(g);
      return norm3([g[0] + T[0][0] * du + T[1][0] * dv, g[1] + T[0][1] * du + T[1][1] * dv, g[2] + T[0][2] * du + T[1][2] * dv]);
    }
    function scr(g) { var v = toView(Gm, g); return { x: geo.cx + v[0] * geo.R, y: geo.cy - v[1] * geo.R, z: v[2], v: v }; }
    function upOf(v) { var ux = v[0] * 0.45, uy = -v[1] * 0.45 - 0.9, l = Math.hypot(ux, uy) || 1; return [ux / l, uy / l]; }
    function cloudLift() { return clamp(geo.R * 0.12, 12, 100); }   // đáy mây cách mặt đất (px)
    // Elip mờ đều tới mép: gradient tròn co dẹt theo elip (tô gradient tròn vào hình elip dẹt thì
    // trên/dưới bị cắt ngang, ra cái đĩa đen mép cứng).
    function softEllipse(c, x, y, rx, ry, rot, rgb, a0) {
      c.save(); c.translate(x, y); c.rotate(rot); c.scale(1, Math.max(0.05, ry / rx));
      var gr = c.createRadialGradient(0, 0, 0, 0, 0, rx);
      gr.addColorStop(0, rgba(rgb, a0.toFixed(3))); gr.addColorStop(0.55, rgba(rgb, (a0 * 0.6).toFixed(3))); gr.addColorStop(1, rgba(rgb, 0));
      c.fillStyle = gr; c.beginPath(); c.arc(0, 0, rx, 0, 6.2832); c.fill();
      c.restore();
    }
    function stormLevel() { return Math.max(fx.rain, fx.lightning); }              // mây ĐEN (mưa, sét)
    // Có mây: bật riêng gió vẫn có các đám mây (trắng xám) để gió thổi quanh và giữa chúng.
    function cloudLevel() { return Math.max(fx.rain, fx.lightning, fx.wind); }
    function newCell(first) {
      var g = geoOf(randView(0.8));
      for (var t = 0; t < 14; t++) {
        var ok = true;
        for (var i = 0; i < cells.length; i++) if (cells[i].g[0] * g[0] + cells[i].g[1] * g[1] + cells[i].g[2] * g[2] > Math.cos(0.5)) { ok = false; break; }
        if (ok) break;
        g = geoOf(randView(0.8));
      }
      var puffs = [], np = 12 + ((Math.random() * 7) | 0);
      for (var k = 0; k < np; k++) puffs.push({ du: gauss() * 0.42, dv: gauss() * 0.3, r: 0.4 + Math.random() * 0.45, h: Math.random() });
      return { id: ++cellSeq, g: g, sig: 0.12 + Math.random() * 0.08, k: 0, age: 0, life: first ? 12 + Math.random() * 30 : 24 + Math.random() * 26,
               east: 0.005 + Math.random() * 0.008, nb: 0, flash: 0, puffs: puffs, drops: [] };
    }
    function updateCells(dt) {
      var s = cloudLevel();
      if (s < 0.01) { cells.length = 0; return; }
      var want = profile === "high" ? 4 : profile === "balanced" ? 3 : 2;
      while (cells.length < want) cells.push(newCell(true));
      for (var i = 0; i < cells.length; i++) {
        var c = cells[i];
        if (dt) {
          c.age += dt;
          // trôi về phía Đông quanh trục cực, gió mạnh thì trôi nhanh gấp 4
          var th = c.east * dt * (1 + 3 * fx.wind), ct = Math.cos(th), st = Math.sin(th), g = c.g;
          c.g = [g[0] * ct + g[2] * st, g[1], -g[0] * st + g[2] * ct];
          c.flash *= Math.exp(-dt * 9);
        }
        c.k = Math.max(0, Math.min(1, c.age / 4, (c.life - c.age) / 4));
        if (c.age >= c.life) cells[i] = newCell(false);
      }
    }
    // Độ hiện của một ô: cường độ ô x mức bão x còn ở nửa cầu đang thấy.
    function cellVis(cl, cen) { return cl.k * cloudLevel() * smooth(0.0, 0.25, cen.z); }
    function drawRain(c, dt) {
      var rk = fx.rain;
      if (!cells.length) { splashes.length = 0; return; }
      var R = geo.R, L = cloudLift(), slant = 0.1 + 0.45 * fx.wind;
      c.save(); c.lineCap = "round";
      for (var i = 0; i < cells.length; i++) {
        var cl = cells[i], cen = scr(cl.g), vis = cellVis(cl, cen);
        var n = Math.round((profile === "high" ? 110 : profile === "balanced" ? 70 : 36) * rk);
        while (cl.drops.length < n) cl.drops.push({ du: gauss() * 0.45, dv: gauss() * 0.32, t: Math.random(), sp: 1.5 + Math.random() * 0.9 });
        if (cl.drops.length > n) cl.drops.length = n;
        if (vis < 0.01 || rk < 0.01) continue;
        var up = upOf(cen.v), px = -up[1], py = up[0], foot = cl.sig * R;
        // 1. màn mưa: ba dải xám mờ rủ từ đáy mây xuống mặt đất
        for (var m = -1; m <= 1; m++) {
          var b = scr(offsetGeo(cl.g, m * 0.45 * cl.sig, 0));
          if (b.z < 0.02) continue;
          var tx = b.x + up[0] * L - slant * L * 0.4, ty = b.y + up[1] * L, w = foot * 0.32;
          var vg = c.createLinearGradient(tx, ty, b.x, b.y);
          vg.addColorStop(0, "rgba(150,165,190," + (0.2 * vis * rk).toFixed(3) + ")");
          vg.addColorStop(1, "rgba(150,165,190," + (0.03 * vis * rk).toFixed(3) + ")");
          c.fillStyle = vg; c.beginPath();
          c.moveTo(tx - px * w, ty - py * w); c.lineTo(tx + px * w, ty + py * w);
          c.lineTo(b.x + px * w * 0.8, b.y + py * w * 0.8); c.lineTo(b.x - px * w * 0.8, b.y - py * w * 0.8);
          c.closePath(); c.fill();
        }
        // 2. hạt mưa: từ đáy mây (điểm đất nâng lên L) rơi xuống đúng điểm đất, xiên theo gió
        c.strokeStyle = "rgba(205,225,255," + (0.6 * vis * rk).toFixed(3) + ")"; c.lineWidth = 1;
        c.beginPath();
        for (var j = 0; j < cl.drops.length; j++) {
          var d = cl.drops[j];
          if (dt) d.t += dt * d.sp;
          var gp = scr(offsetGeo(cl.g, d.du * cl.sig, d.dv * cl.sig));
          if (d.t >= 1) {
            if (gp.z > 0.05 && splashes.length < 90) splashes.push({ x: gp.x, y: gp.y, t: 0, k: vis });
            d.t -= 1; d.du = gauss() * 0.45; d.dv = gauss() * 0.32;
          }
          if (gp.z < 0.03) continue;
          var sx = gp.x + up[0] * L - slant * L * 0.5, sy = gp.y + up[1] * L;
          var x = sx + (gp.x - sx) * d.t, y = sy + (gp.y - sy) * d.t;
          c.moveTo(x - (gp.x - sx) * 0.14, y - (gp.y - sy) * 0.14); c.lineTo(x, y);
        }
        c.stroke();
      }
      c.lineWidth = 0.8;
      splashes = splashes.filter(function (s) {
        if (dt) s.t += dt / 0.3;
        if (s.t >= 1) return false;
        var rr = (1.2 + s.t * 4) * Math.min(1.8, R / 150);
        c.strokeStyle = "rgba(215,232,255," + (0.55 * (1 - s.t) * s.k * rk).toFixed(3) + ")";
        c.beginPath(); c.ellipse(s.x, s.y, rr, rr * 0.35, 0, 0, 6.2832); c.stroke();
        return true;
      });
      c.restore();
    }
    // Khối mây giông nổi trên mỗi ô (vẽ SAU mưa để hạt mưa chui ra từ đáy mây): các cụm mây xám
    // đen mềm, viền sáng nhẹ phía có nắng, loé vàng trắng khi có chớp trong mây.
    function drawStormClouds(c) {
      if (!cells.length) return;
      var R = geo.R, L = cloudLift(), Lv = geo.L || [-0.6, 0.5, 0.6];
      var sx = Lv[0], sy = -Lv[1], sn = Math.hypot(sx, sy) || 1;
      sx /= sn; sy /= sn;
      for (var i = 0; i < cells.length; i++) {
        var cl = cells[i], cen = scr(cl.g), vis = cellVis(cl, cen);
        if (vis < 0.01) continue;
        var up = upOf(cen.v), fl = Math.min(1, cl.flash);
        var day = smooth(-0.2, 0.4, cen.v[0] * Lv[0] + cen.v[1] * Lv[1] + cen.v[2] * Lv[2]);
        // mây đen khi có mưa/sét, mây trắng xám khi chỉ có gió; loé vàng trắng khi có chớp
        var dkr = clamp(stormLevel() / Math.max(cloudLevel(), 1e-3), 0, 1);
        var b0r = 205 - 171 * dkr, b0g = 210 - 172 * dkr, b0b = 222 - 170 * dkr;
        var cr = Math.round(b0r + (255 - b0r) * fl), cg = Math.round(b0g + (240 - b0g) * fl), cb = Math.round(b0b + (200 - b0b) * fl);
        // đế mây: dải sẫm phẳng nằm ngang ở độ cao đáy mây, nơi mưa và sét rơi ra
        var brx = cl.sig * R * 0.95;
        softEllipse(c, cen.x + up[0] * L, cen.y + up[1] * L, brx, brx * 0.32, Math.atan2(up[0], -up[1]),
          [Math.round(cr * 0.72), Math.round(cg * 0.72), Math.round(cb * 0.72)], 0.8 * vis);
        for (var k = 0; k < cl.puffs.length; k++) {
          var p = cl.puffs[k], pp = scr(offsetGeo(cl.g, p.du * cl.sig, p.dv * cl.sig));
          if (pp.z < 0.02) continue;
          // cụm mây vồng: elip mờ dẹt, toả ngang nhiều hơn dồn lên cao (dáng mây vũ tích)
          var x = pp.x + up[0] * L * (1.08 + 0.35 * p.h), y = pp.y + up[1] * L * (1.08 + 0.35 * p.h);
          var rr = Math.max(6, p.r * cl.sig * R * 0.85);
          softEllipse(c, x, y, rr, rr * 0.62, Math.atan2(up[0], -up[1]), [cr, cg, cb], 0.82 * vis);
          if (day > 0.05) {        // viền mây hứng nắng
            var hx = x + sx * rr * 0.35, hy = y + sy * rr * 0.35, hr = rr * 0.6;
            var hg = c.createRadialGradient(hx, hy, 0, hx, hy, hr);
            hg.addColorStop(0, "rgba(170,180,200," + (0.22 * vis * day).toFixed(3) + ")"); hg.addColorStop(1, "rgba(170,180,200,0)");
            c.fillStyle = hg; c.beginPath(); c.arc(hx, hy, hr, 0, 6.2832); c.fill();
          }
        }
      }
    }

    // HẠT NÓNG: dung nham phun + tia lửa sét. Bay trong toạ độ ĐỊA LÝ (đơn vị = bán kính), trọng
    // lực hút về tâm (1/r²), rơi lại vào mặt đất là tắt. Chiếu lên màn mỗi khung, sau hành tinh
    // thì bị che. Màu nguội dần: trắng vàng -> cam -> đỏ sẫm.
    function launch(g, sp, spread, kind) {
      var a = Math.abs(g[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
      var t1 = norm3(cross3(a, g)), t2 = cross3(g, t1);
      var an = Math.random() * 6.2832, s = Math.random() * spread, ca = Math.cos(an) * s, sa = Math.sin(an) * s;
      var d = norm3([g[0] + t1[0] * ca + t2[0] * sa, g[1] + t1[1] * ca + t2[1] * sa, g[2] + t1[2] * ca + t2[2] * sa]);
      return { p: [g[0] * 1.004, g[1] * 1.004, g[2] * 1.004], v: [d[0] * sp, d[1] * sp, d[2] * sp], age: 0,
               life: kind === "spark" ? 0.45 + Math.random() * 0.45 : 1.6 + Math.random() * 1.2, kind: kind, sx: null, sy: null };
    }
    function drawHot(c, dt) {
      if (!hot.length) return;
      var R = geo.R, sz = clamp(R / 110, 0.7, 2.4);
      c.save(); c.globalCompositeOperation = "lighter"; c.lineCap = "round";
      hot = hot.filter(function (h) {
        if (dt) {
          var r2 = h.p[0] * h.p[0] + h.p[1] * h.p[1] + h.p[2] * h.p[2], r = Math.sqrt(r2);
          var gk = (h.kind === "spark" ? 1.7 : 1.4) / (r2 * r);
          h.v[0] -= h.p[0] * gk * dt; h.v[1] -= h.p[1] * gk * dt; h.v[2] -= h.p[2] * gk * dt;
          h.p[0] += h.v[0] * dt; h.p[1] += h.v[1] * dt; h.p[2] += h.v[2] * dt;
          h.age += dt;
          var rad = h.p[0] * h.v[0] + h.p[1] * h.v[1] + h.p[2] * h.v[2];
          if (h.age > h.life || (r < 1 && rad < 0)) return false;
        }
        var v = toView(Gm, h.p);
        var x = geo.cx + v[0] * R, y = geo.cy - v[1] * R;
        var hid = v[2] < 0 && (x - geo.cx) * (x - geo.cx) + (y - geo.cy) * (y - geo.cy) < R * R;
        var f = Math.min(1, h.age / h.life), col;
        if (h.kind === "spark") col = f < 0.3 ? [255, 250, 225] : f < 0.65 ? [255, 214, 120] : [255, 150, 60];
        else col = f < 0.15 ? [255, 238, 190] : f < 0.45 ? [255, 168, 60] : f < 0.75 ? [235, 92, 26] : [150, 40, 14];
        if (!hid) {      // vệt từ vị trí khung trước (chưa có thì là một chấm tròn nhờ lineCap)
          var ox = h.sx == null ? x : h.sx, oy = h.sy == null ? y : h.sy;
          if (Math.abs(ox - x) + Math.abs(oy - y) < 0.05) ox = x - 0.05;   // canvas bỏ qua nét dài 0
          var lw = (h.kind === "spark" ? 1.1 : 2.4) * sz * (1 - f * 0.45), al = 1 - f * f;
          if (h.kind !== "spark") {        // quầng nóng quanh cục dung nham (nét rộng, mờ)
            c.strokeStyle = rgba(col, (0.22 * al).toFixed(3)); c.lineWidth = lw * 3.2;
            c.beginPath(); c.moveTo(ox, oy); c.lineTo(x, y); c.stroke();
          }
          c.strokeStyle = rgba(col, al.toFixed(3)); c.lineWidth = lw;
          c.beginPath(); c.moveTo(ox, oy); c.lineTo(x, y); c.stroke();
        }
        h.sx = x; h.sy = y;
        return true;
      });
      c.restore();
    }

    // ---------------------------------------------------------------------------
    // NÚI LỬA + SÔNG DUNG NHAM (0.65.44, chủ yêu cầu: dung nham nhảy nhẹ nhàng từ lõi Trái Đất phun
    // lên đỉnh MỘT ngọn núi, chảy dài xuống chân núi thành sông dung nham chảy qua các ngả bao quanh
    // Trái Đất, không điểm dừng). Núi đặt ở Krakatoa (eo Sunda) - gần Việt Nam nên góc nhìn mặc
    // định thấy ngay. Thứ tự vẽ: sông (sát mặt đất) -> ống magma từ lõi lên chân núi -> thân núi ->
    // dòng dung nham chảy xuống sườn -> miệng núi rực -> giọt sủi nhẹ -> khói.
    // Sông: 4 nhánh chính toả từ chân núi + nhánh rẽ, mỗi bước 0,028 rad, dài 3-5 rad (vòng quanh
    // Trái Đất); "chảy dài" ra dần trong ~10 giây đầu sau khi bật, nét đứt chạy dọc = đang chảy.
    // Lõi sôi + cột magma trong lõi vẫn do shader lo (uCo.z).
    // ---------------------------------------------------------------------------
    var VOLC_G = geoVec(-6.1, 105.4);
    // front: đầu dòng (bước), flowT: đồng hồ trôi vỏ nguội (theo tốc độ), plume: hạt khói, acc: tích luỹ sinh khói.
    var volc = { rivers: null, front: 0, flowT: 0, bub: [], smoke: [], magma: [], plume: [], acc: [], acc2: [] };
    function rotAround(h, axis, a) {   // xoay h (vuông góc axis) quanh axis
      var x = cross3(axis, h), ca = Math.cos(a), sa = Math.sin(a);
      return [h[0] * ca + x[0] * sa, h[1] * ca + x[1] * sa, h[2] * ca + x[2] * sa];
    }
    function buildRivers() {
      var rnd = mrand(20261007), out = [];
      var grow = function (g, h, steps, w, depth, start) {
        var pts = [g], cur = g, turn = 0;
        for (var i = 0; i < steps; i++) {
          turn = turn * 0.9 + (rnd() - 0.5) * 0.07;            // lượn nhẹ theo địa hình, không cuộn vòng
          h = rotAround(h, cur, turn);
          var nx = norm3([cur[0] + h[0] * 0.028, cur[1] + h[1] * 0.028, cur[2] + h[2] * 0.028]);
          var dh = h[0] * nx[0] + h[1] * nx[1] + h[2] * nx[2];
          h = norm3([h[0] - nx[0] * dh, h[1] - nx[1] * dh, h[2] - nx[2] * dh]);
          cur = nx; pts.push(cur);
          if (depth < 1 && i > 14 && i < steps - 30 && rnd() < 0.014) {   // thỉnh thoảng rẽ một nhánh
            grow(cur, rotAround(h, cur, (rnd() < 0.5 ? -1 : 1) * (0.5 + rnd() * 0.5)),
                 Math.round((steps - i) * (0.35 + rnd() * 0.3)), w * 0.6, depth + 1, start + i);
          }
        }
        out.push({ pts: pts, w: w, depth: depth, start: start });
      };
      var T = tangentBasis(VOLC_G);
      for (var k = 0; k < 3; k++) {
        var a = k * 2.0944 + rnd() * 0.7, ca = Math.cos(a), sa = Math.sin(a);
        grow(VOLC_G, norm3([T[0][0] * ca + T[1][0] * sa, T[0][1] * ca + T[1][1] * sa, T[0][2] * ca + T[1][2] * sa]), 100 + Math.floor(rnd() * 60), 1, 0, 0);
      }
      return out;
    }
    // ---------------------------------------------------------------------------
    // SÔNG DUNG NHAM (1.0.2, chủ yêu cầu: chạy chậm từ từ, lan to rộng như dòng sông, chảy tới đâu
    // đốt cháy toả khói mù mịt tới đó, có chỉnh tốc độ). Mỗi dòng có một ĐẦU DÒNG (`volc.front`,
    // đơn vị bước 0,028 rad) tiến LAVA_RATE bước/giây x look.lavaSpeed - mặc định ~1,5 phút một dòng.
    // Bề rộng tính theo radian trên mặt cầu (phóng to là sông to); ngay đầu dòng hẹp, phía sau lan
    // rộng dần (`spread`) - đúng kiểu dung nham bò tới rồi tràn ra hai bên. Lớp vẽ: đất cháy sẫm
    // rộng gấp 2,6 -> quầng nóng -> thân dung nham (nóng gần núi, nguội đỏ sẫm ở xa) -> mảng vỏ nguội
    // trôi chậm -> lõi sáng; đầu dòng rực vàng trắng. Khói + lửa: drawLavaSmoke.
    // ---------------------------------------------------------------------------
    var LAVA_RATE = 1.6;              // bước/giây ở tốc độ 1 (0,045 rad/giây)
    var LAVA_HALF = 0.024;            // nửa bề rộng sông chính (rad); nhánh x0,6
    var LAVA_SPREAD = 14;             // số bước sau đầu dòng thì sông lan đủ rộng
    var P_CRUST = 5;                  // vỏ nguội trôi P_CRUST px/giây x tốc độ
    function lavaSeg(rv) { return Math.min(rv.pts.length, volc.front - rv.start); }   // số bước đã chảy (thực)
    function drawRivers(c, k) {
      if (!volc.rivers) volc.rivers = buildRivers();
      var R = geo.R, maxL = 0, ft = volc.flowT, sz = clamp(R / 150, 0.8, 3);
      volc.rivers.forEach(function (r) { maxL = Math.max(maxL, r.start + r.pts.length); });
      // Hai kiểu lớp:
      //  - lớp BÁN TRONG SUỐT (đất cháy, quầng nóng, mảng vỏ nguội) vẽ MỘT nét liền cho cả dòng:
      //    vẽ từng đoạn thì chỗ nối chồng alpha lên nhau thành chuỗi hạt tròn đều.
      //  - lớp ĐẶC (thân dung nham, lõi sáng) vẽ từng đoạn 3 bước để bề rộng lan dần và màu nguội
      //    dần theo khoảng cách; đặc nên chỗ nối không lộ.
      volc.rivers.forEach(function (rv) {
        var n = lavaSeg(rv);
        if (n < 1) return;
        var nf = Math.floor(n), pts = [];
        for (var j = 0; j <= Math.min(nf, rv.pts.length - 1); j++) pts.push(rv.pts[j]);
        if (nf < rv.pts.length - 1) {    // đầu dòng nằm GIỮA hai bước: nội suy để tiến mượt, không giật
          var a = rv.pts[nf], b = rv.pts[nf + 1], fr = n - nf;
          pts.push(norm3([a[0] + (b[0] - a[0]) * fr, a[1] + (b[1] - a[1]) * fr, a[2] + (b[2] - a[2]) * fr]));
        }
        var sc = pts.map(function (g) {
          var v = toView(Gm, g);
          return v[2] < 0.03 ? null : [geo.cx + v[0] * R * 1.002, geo.cy - v[1] * R * 1.002, v[2]];
        });
        var last = pts.length - 1, fMid = (rv.start + last / 2) / maxL;
        var full = 2 * LAVA_HALF * rv.w * R * (1 - 0.3 * fMid);      // bề rộng đã lan đủ
        var path = function (c0, c1) {
          c.beginPath();
          var pen = false;
          for (var q = c0; q <= c1; q++) {
            var s0 = sc[q];
            if (!s0) { pen = false; continue; }
            if (pen) c.lineTo(s0[0], s0[1]); else { c.moveTo(s0[0], s0[1]); pen = true; }
          }
        };
        var tail = Math.max(0, last - 5);                            // nét liền dừng trước đầu dòng hẹp
        // 1. đất cháy sẫm hai bên  2. quầng nóng
        [[2.7, "rgba(30,15,10,", 0.6], [1.8, "rgba(255,92,24,", 0.3]].forEach(function (L) {
          if (tail < 1) return;
          c.setLineDash([]);
          c.strokeStyle = L[1] + (L[2] * k).toFixed(3) + ")";
          c.lineWidth = Math.max(L[0] * 2.2, full * L[0]);
          path(0, tail); c.stroke();
        });
        // 3. thân + 4. lõi sáng: từng đoạn, lan rộng dần sau đầu dòng, đầu dòng rực vàng trắng
        [[1, [255, 132, 36], [150, 36, 12]], [0.42, [255, 226, 140], [235, 104, 36]]].forEach(function (L) {
          for (var c0 = 0; c0 < last; c0 += 3) {
            var c1 = Math.min(last, c0 + 3), mid = (c0 + c1) / 2;
            var f = (rv.start + mid) / maxL, behind = n - mid;
            var spread = 0.35 + 0.65 * smooth(0, LAVA_SPREAD, behind);
            var hot = 1 - smooth(0, 6, behind);
            var col = [0, 1, 2].map(function (q) {
              var x = L[1][q] + (L[2][q] - L[1][q]) * f;
              return Math.round(x + ([255, 245, 200][q] - x) * hot * 0.6);
            });
            c.setLineDash([]);
            c.strokeStyle = "rgba(" + col.join(",") + "," + k.toFixed(3) + ")";
            c.lineWidth = Math.max(L[0] * 2.2, 2 * LAVA_HALF * rv.w * R * L[0] * spread * (1 - 0.3 * f));
            path(c0, c1); c.stroke();
          }
        });
        // 5. mảng vỏ nguội sẫm trôi chậm theo dòng, đè lên lõi sáng (nhịp không đều cho tự nhiên)
        if (tail >= 1) {
          c.lineCap = "butt";
          c.setLineDash([3 * sz, 9 * sz, 6 * sz, 14 * sz, 2 * sz, 7 * sz, 9 * sz, 11 * sz]);
          c.lineDashOffset = P_CRUST * -ft * sz;
          c.strokeStyle = "rgba(60,22,10," + (0.5 * k).toFixed(3) + ")";
          c.lineWidth = Math.max(1.2, full * 0.42);
          path(0, tail); c.stroke();
          // 6. vệt sáng mảnh chảy nhanh hơn vỏ nguội trong lòng sông = dòng chảy đang sống
          c.setLineDash([1.5 * sz, 13 * sz, 1 * sz, 21 * sz]);
          c.lineDashOffset = P_CRUST * -ft * sz * 2.6;
          c.strokeStyle = "rgba(255,246,205," + (0.75 * k).toFixed(3) + ")";
          c.lineWidth = Math.max(0.8, full * 0.12);
          path(0, tail); c.stroke();
          c.lineCap = "round";
        }
      });
      c.setLineDash([]);
    }

    // KHÓI + LỬA theo dòng dung nham: đầu dòng đang chảy (lửa bập bùng + khói đen cuồn cuộn), dải
    // vừa chảy qua phía sau (khói âm ỉ + đốm than), dòng đã chảy hết (khói lác đác). Khói neo toạ độ
    // địa lý, bốc lên theo "phía trên trời" của điểm đó, trôi ngang theo gió, nở to, nhạt dần từ đen
    // sang xám. Lửa vẽ thủ tục mỗi khung (không cần nhớ hạt).
    function drawLavaSmoke(c, k, dt, now) {
      if (!volc.rivers) return;
      var R = geo.R, cap = profile === "high" ? 420 : profile === "balanced" ? 240 : 90;
      var spd = 0.6 + 0.4 * Math.min(2, look.lavaSpeed);
      var push = function (g, big) {
        if (volc.plume.length >= cap) return;
        volc.plume.push({ g: g, age: 0, life: (big ? 6 : 4.5) + Math.random() * 3.5, r0: (big ? 1.2 : 0.8) * (0.8 + Math.random() * 0.6),
                          dx: (Math.random() - 0.5) * 0.6, sp: 0.8 + Math.random() * 0.5 });
      };
      var t = simT;
      volc.rivers.forEach(function (rv, ri) {
        var n = lavaSeg(rv);
        if (n < 1) return;
        var flowing = n < rv.pts.length - 0.5;
        var at = function (s) { return rv.pts[clamp(Math.floor(s), 0, rv.pts.length - 1)]; };
        if (dt && k > 0.3) {
          if (flowing) {
            // đầu dòng: khói dày, tỉ lệ với tốc độ chảy
            var rate = 9 * spd * rv.w;
            volc.acc[ri] = (volc.acc[ri] || 0) + dt * rate;
            while (volc.acc[ri] >= 1) { volc.acc[ri] -= 1; push(offsetGeo(at(n), gauss() * 0.012, gauss() * 0.012), true); }
            // dải vừa cháy qua phía sau
            volc.acc2[ri] = (volc.acc2[ri] || 0) + dt * 10 * spd * rv.w;   // dải vừa cháy qua: khói âm ỉ dày
            while (volc.acc2[ri] >= 1) { volc.acc2[ri] -= 1; push(at(n - 2 - Math.random() * 40), false); }
          } else if (Math.random() < dt * 0.8 * rv.w) {
            push(at(Math.random() * rv.pts.length), false);
          }
        }
        if (!flowing) return;
        // lửa ở đầu dòng + đốm than phía sau
        var g0 = at(n), v0 = toView(Gm, g0);
        if (v0[2] < 0.05) return;
        var vis = k * smooth(0.05, 0.3, v0[2]), up = upOf(v0), rot = Math.atan2(up[0], -up[1]);
        for (var f = 0; f < 5; f++) {
          var gf = f === 0 ? g0 : at(n - 1 - f * 2.2), vf = toView(Gm, gf);
          if (vf[2] < 0.05) continue;
          var fl = 0.65 + 0.35 * Math.sin(t * (9 + f * 2.3) + f * 1.7 + ri);
          var hgt = Math.max(4, R * 0.04 * rv.w * fl * (f === 0 ? 1.4 : 1 - f * 0.12));
          var fx0 = geo.cx + vf[0] * R + up[0] * hgt * 0.45, fy0 = geo.cy - vf[1] * R + up[1] * hgt * 0.45;
          softEllipse(c, fx0, fy0, hgt * 0.42, hgt, rot, [255, 140, 30], 0.55 * vis * fl);
          softEllipse(c, fx0 - up[0] * hgt * 0.2, fy0 - up[1] * hgt * 0.2, hgt * 0.22, hgt * 0.5, rot, [255, 236, 170], 0.8 * vis * fl);
        }
        c.fillStyle = "rgba(255,170,60," + (0.7 * vis).toFixed(3) + ")";
        for (var e = 0; e < 8; e++) {
          var ge = at(n - 4 - e * 3), ve = toView(Gm, ge);
          if (ve[2] < 0.05 || Math.sin(t * 3 + e * 7.1 + ri) < 0.2) continue;
          var ex = geo.cx + ve[0] * R + Math.sin(e * 12.9 + ri) * R * 0.012, ey = geo.cy - ve[1] * R + Math.cos(e * 7.3 + ri) * R * 0.008;
          c.beginPath(); c.arc(ex, ey, Math.max(0.8, R * 0.0035), 0, 6.2832); c.fill();
        }
      });
      // khói (vẽ sau lửa để đầu dòng mờ mịt trong khói)
      var wind = 0.35 + fx.wind;
      volc.plume = volc.plume.filter(function (p) {
        if (dt) p.age += dt;
        var q = p.age / p.life;
        if (q >= 1) return false;
        var v = toView(Gm, p.g);
        if (v[2] < 0.03) return true;
        var up = upOf(v), rise = R * 0.03 * p.sp * p.age, side = R * 0.012 * wind * p.age * (1 + p.dx);
        var x = geo.cx + v[0] * R + up[0] * rise - up[1] * side, y = geo.cy - v[1] * R + up[1] * rise + up[0] * side;
        var r = R * (0.014 + 0.02 * p.age) * p.r0;
        var gr = Math.round(28 + 90 * q);
        var a = 0.7 * Math.pow(1 - q, 1.1) * smooth(0, 0.1, q) * k * smooth(0.03, 0.25, v[2]);
        softEllipse(c, x, y, r, r * 0.82, Math.atan2(up[0], -up[1]), [gr, gr - 4, gr - 2], a);
        return true;
      });
    }
    // Dòng dung nham chảy xuống SƯỜN núi: [bề rộng px, màu, nét đứt?, alpha]
    var SLOPE_PASS = [[5, "rgba(255,90,20,", 0, 0.3], [2.2, "rgba(255,160,60,", 0, 0.9], [1, "rgba(255,240,170,", 1, 0.9]];
    function drawEruption(c, now, dt) {
      var k = fx.eruption;
      if (k < 0.01) { volc.front = 0; volc.flowT = 0; volc.bub.length = 0; volc.magma.length = 0; volc.smoke.length = 0; volc.plume.length = 0; volc.acc = []; volc.acc2 = []; return; }
      if (dt) { volc.front += dt * LAVA_RATE * look.lavaSpeed; volc.flowT += dt * look.lavaSpeed; }
      var t = simT, R = geo.R, sz = clamp(R / 150, 0.8, 3);
      c.save(); c.lineCap = "round"; c.lineJoin = "round";
      drawRivers(c, k);
      drawLavaSmoke(c, k, dt, now);
      var v = toView(Gm, VOLC_G), vis = k * smooth(0.0, 0.25, v[2]);
      if (vis < 0.01) { c.restore(); return; }
      var bx = geo.cx + v[0] * R, by = geo.cy - v[1] * R, up = upOf(v), px = -up[1], py = up[0], rot = Math.atan2(py, px);
      var Hm = clamp(R * 0.12, 14, 90), Wm = Hm * 1.5;
      // 1. ống magma: từ mép lõi (lõi nhìn xuyên nước ở giữa đĩa, bán kính ~0,46R) lên chân núi,
      //    cục magma dâng chậm theo ống
      var dx = bx - geo.cx, dy = by - geo.cy, dl = Math.hypot(dx, dy);
      if (dl > R * 0.5) {
        var sx0 = geo.cx + dx / dl * R * 0.44, sy0 = geo.cy + dy / dl * R * 0.44;
        var lg = c.createLinearGradient(sx0, sy0, bx, by);
        lg.addColorStop(0, "rgba(255,120,30," + (0.42 * vis).toFixed(3) + ")"); lg.addColorStop(1, "rgba(255,90,20," + (0.16 * vis).toFixed(3) + ")");
        c.strokeStyle = lg; c.lineWidth = 3 * sz; c.beginPath(); c.moveTo(sx0, sy0); c.lineTo(bx, by); c.stroke();
        if (dt && Math.random() < dt * 3) volc.magma.push({ p: 0, sp: 0.18 + Math.random() * 0.12 });
        volc.magma = volc.magma.filter(function (m) {
          if (dt) m.p += dt * m.sp;
          if (m.p >= 1) return false;
          var mx = sx0 + (bx - sx0) * m.p, my = sy0 + (by - sy0) * m.p, mr = 3.5 * sz;
          var gr = c.createRadialGradient(mx, my, 0, mx, my, mr);
          gr.addColorStop(0, "rgba(255,230,150," + (0.9 * vis).toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,110,30,0)");
          c.fillStyle = gr; c.beginPath(); c.arc(mx, my, mr, 0, 6.2832); c.fill();
          return true;
        });
      } else volc.magma.length = 0;
      // 2. chân núi: bóng + quầng nóng
      softEllipse(c, bx, by, Wm * 1.3, Wm * 0.38, rot, [70, 22, 10], 0.6 * vis);
      // 3. thân núi hình nón, sống núi gồ ghề, đỉnh lõm thành miệng
      var P2 = function (a, b) { return [bx + px * a * Wm + up[0] * b * Hm, by + py * a * Wm + up[1] * b * Hm]; };
      var tx = bx + up[0] * Hm * 0.95, ty = by + up[1] * Hm * 0.95;
      var ridge = [[-1, 0], [-0.78, 0.17], [-0.62, 0.3], [-0.45, 0.5], [-0.3, 0.7], [-0.17, 0.97], [-0.08, 0.92], [0.08, 0.92],
                   [0.17, 0.98], [0.33, 0.68], [0.5, 0.46], [0.7, 0.26], [0.86, 0.11], [1, 0]];
      c.beginPath();
      ridge.forEach(function (q, i) { var p = P2(q[0], q[1]); if (i) c.lineTo(p[0], p[1]); else c.moveTo(p[0], p[1]); });
      var bl = P2(0, -0.1), b0 = P2(-1, 0);
      c.quadraticCurveTo(bl[0], bl[1], b0[0], b0[1]);
      c.closePath();
      var mg = c.createLinearGradient(bx, by, tx, ty);
      mg.addColorStop(0, "rgba(30,22,22," + (0.96 * vis).toFixed(3) + ")");
      mg.addColorStop(0.72, "rgba(58,34,28," + (0.96 * vis).toFixed(3) + ")");
      mg.addColorStop(1, "rgba(130,48,22," + (0.96 * vis).toFixed(3) + ")");
      c.fillStyle = mg; c.fill();
      // 4. dung nham chảy thành dòng xuống sườn (nét đứt chạy xuống = đang chảy)
      for (var f = 0; f < 4; f++) {
        var s0 = -0.1 + f * 0.065, e0 = [-0.75, -0.3, 0.32, 0.8][f];
        var A0 = P2(s0, 0.92), C0 = P2((s0 + e0) * 0.5 + 0.12 * Math.sin(f * 2.1), 0.45), E0 = P2(e0, 0.02);
        for (var li = 0; li < SLOPE_PASS.length; li++) {
          var LP = SLOPE_PASS[li];
          c.setLineDash(LP[2] ? [2.5 * sz, 6 * sz] : []); c.lineDashOffset = LP[2] ? -volc.flowT * 18 * sz : 0;
          c.strokeStyle = LP[1] + (LP[3] * vis).toFixed(3) + ")"; c.lineWidth = LP[0] * sz;
          c.beginPath(); c.moveTo(A0[0], A0[1]); c.quadraticCurveTo(C0[0], C0[1], E0[0], E0[1]); c.stroke();
        }
      }
      c.setLineDash([]);
      // 5. miệng núi rực + quầng
      softEllipse(c, tx, ty, Wm * 0.5, Wm * 0.2, rot, [255, 110, 30], 0.55 * vis);
      softEllipse(c, tx, ty, Wm * 0.18, Wm * 0.07, rot, [255, 230, 150], 0.95 * vis);
      // 6. dung nham sủi NHẸ: giọt nhảy thấp (đỉnh 0,06-0,27 chiều cao núi) rồi rơi lại miệng
      if (dt && Math.random() < dt * 9) volc.bub.push({ x: (Math.random() - 0.5) * 0.24, h: 0, vx: (Math.random() - 0.5) * 0.35, vh: 0.5 + Math.random() * 0.6, s: 0.8 + Math.random() * 0.9 });
      volc.bub = volc.bub.filter(function (b) {
        if (dt) { b.x += b.vx * dt; b.vh -= 2.2 * dt; b.h += b.vh * dt; }
        if (b.h < -0.02) return false;
        var x2 = tx + px * b.x * Wm + up[0] * b.h * Hm, y2 = ty + py * b.x * Wm + up[1] * b.h * Hm;
        c.fillStyle = "rgba(255," + Math.round(150 + 90 * clamp(b.vh + 0.5, 0, 1)) + ",60," + (vis * Math.min(1, 0.45 + b.h * 2)).toFixed(3) + ")";
        c.beginPath(); c.arc(x2, y2, b.s * sz, 0, 6.2832); c.fill();
        return true;
      });
      // 7. khói xám bốc lên, trôi theo gió
      if (dt && Math.random() < dt * 1.2) volc.smoke.push({ age: 0, life: 3 + Math.random() * 2, dx: (Math.random() - 0.5) * 0.2 });
      volc.smoke = volc.smoke.filter(function (s) {
        if (dt) s.age += dt;
        var q = s.age / s.life;
        if (q >= 1) return false;
        var drift = (s.dx + q * (0.6 + fx.wind)) * Wm, rise = q * Hm * 1.4;
        softEllipse(c, tx + px * drift + up[0] * rise, ty + py * drift + up[1] * rise, Wm * (0.25 + q * 0.6), Wm * (0.18 + q * 0.4), rot, [70, 66, 70], 0.45 * vis * (1 - q));
        return true;
      });
      c.restore();
    }

    // ---------------------------------------------------------------------------
    // VÒI RỒNG (0.65.41, theo ảnh tham khảo chủ gửi): hàng trăm HẠT SÁNG xoắn ốc, loe rộng ở đỉnh
    // nhập vào mây xoáy rồi thu nhỏ dần xuống chân; thân uốn lượn; gió cuộn xoắn quanh chân và
    // quanh thân; sét vàng trắng quấn quanh vòi. Vòi chạy KHÔNG NGỪNG quanh tinh cầu theo hướng
    // lượn ngẫu nhiên (ra gần mép thì lái nhẹ về giữa nửa cầu đang thấy để vẫn xem được), lúc to
    // lúc nhỏ, lúc cao lúc thấp (nhiễu chậm). Màu hạt theo concept bề mặt: Đại dương = vòi rồng
    // số xanh, Dung nham = vòi lửa. Chân vòi neo theo toạ độ địa lý và đẩy vào shader (uTor) để
    // mây quanh đó xoắn theo.
    // ---------------------------------------------------------------------------
    var sprCv = null, sprKey = "";
    function particleSprite(cb) {   // chấm sáng mềm 24px tô theo màu, dựng lại khi đổi màu
      var key = cb.join(",");
      if (sprCv && key === sprKey) return sprCv;
      try {
        if (!sprCv) sprCv = document.createElement("canvas");
        sprCv.width = sprCv.height = 24;
        var g = sprCv.getContext("2d");
        if (!g) return null;
        var gr = g.createRadialGradient(12, 12, 0, 12, 12, 12);
        gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.28, rgba(cb, 0.9)); gr.addColorStop(1, rgba(cb, 0));
        g.clearRect(0, 0, 24, 24); g.fillStyle = gr; g.fillRect(0, 0, 24, 24);
        sprKey = key;
        return sprCv;
      } catch (e) { return null; }
    }
    function spawnTornado() {
      torn.g = geoOf(randView(0.45));
      var T = tangentBasis(torn.g), a = Math.random() * 6.2832;
      torn.head = norm3([T[0][0] * Math.cos(a) + T[1][0] * Math.sin(a), T[0][1] * Math.cos(a) + T[1][1] * Math.sin(a), T[0][2] * Math.cos(a) + T[1][2] * Math.sin(a)]);
      torn.t = Math.random() * 100; torn.parts = []; torn.zaps = []; torn.nz = 0; torn.flash = 0;
    }
    // Màu vòi rồng (tab Quả tinh cầu, 0.65.44): theo concept bề mặt / xanh số / lửa / xám bão /
    // đen tối. Xám và tối là vòi rồng của bão thật: không phát sáng, nhiều bụi đen, thân đặc hơn,
    // sét quấn vòi dày hơn hẳn và có cả sét đánh xuống đất quanh chân vòi.
    function tornadoTheme() {
      var P = LD.pal, tc = look.tornadoColor;
      if (tc === "cyan") return { id: tc, cb: [0, 231, 255], glow: true, dust: 0.16, body: 0.5, zap: [500, 1300], ground: 0.15 };
      if (tc === "fire") return { id: tc, cb: [255, 128, 40], glow: true, dust: 0.16, body: 0.5, zap: [450, 1200], ground: 0.2 };
      if (tc === "grey") return { id: tc, cb: [196, 202, 212], glow: false, dust: 0.32, body: 0.62, zap: [220, 650], ground: 0.45 };
      if (tc === "dark") return { id: tc, cb: [104, 108, 124], glow: false, dust: 0.48, body: 0.78, zap: [140, 420], ground: 0.6 };
      return { id: "concept", cb: [Math.min(255, P.rim[0] * 255) | 0, Math.min(255, P.rim[1] * 255) | 0, Math.min(255, P.rim[2] * 255) | 0],
               glow: true, dust: 0.16, body: 0.5, zap: [500, 1300], ground: 0.15 };
    }
    function tornadoParticle(dr) {
      var r = Math.random();
      return { f: Math.random(), a: Math.random() * 6.2832, rj: 0.7 + Math.random() * 0.5, sp: 0.07 + Math.random() * 0.1,
               s: 0.6 + Math.random() * 1.1, kind: r < dr ? 1 : r < dr + 0.05 ? 2 : 0, rot: Math.random() * 6.28 };
    }
    function moveTornado(dt) {
      torn.t += dt;
      var g0 = torn.g, hd = torn.head, v0 = toView(Gm, g0);
      // lượn: hướng đi xoay quanh pháp tuyến theo nhiễu chậm; ra gần mép thì lái về giữa đĩa
      var turn = (vnoise2(torn.t * 0.13, 7.3) - 0.5) * 1.8 * dt;
      if (v0[2] < 0.45) {
        var cg = geoOf([0, 0, 1]), dg = cg[0] * g0[0] + cg[1] * g0[1] + cg[2] * g0[2];
        var want = norm3([cg[0] - g0[0] * dg, cg[1] - g0[1] * dg, cg[2] - g0[2] * dg]);
        var cx = cross3(hd, want), side = cx[0] * g0[0] + cx[1] * g0[1] + cx[2] * g0[2];
        turn += (side >= 0 ? 1 : -1) * dt * 1.6 * (0.45 - v0[2]);
      }
      var gx = cross3(g0, hd), ct = Math.cos(turn), st = Math.sin(turn);
      hd = [hd[0] * ct + gx[0] * st, hd[1] * ct + gx[1] * st, hd[2] * ct + gx[2] * st];
      var th = (0.045 + 0.045 * vnoise2(torn.t * 0.09, 2.1)) * dt, ca = Math.cos(th), sa = Math.sin(th);
      var g1 = norm3([g0[0] * ca + hd[0] * sa, g0[1] * ca + hd[1] * sa, g0[2] * ca + hd[2] * sa]);
      hd = [hd[0] * ca - g0[0] * sa, hd[1] * ca - g0[1] * sa, hd[2] * ca - g0[2] * sa];
      var dh = hd[0] * g1[0] + hd[1] * g1[1] + hd[2] * g1[2];
      torn.g = g1;
      torn.head = norm3([hd[0] - g1[0] * dh, hd[1] - g1[1] * dh, hd[2] - g1[2] * dh]);
    }
    function drawTornado(c, now, dt) {
      var k = fx.tornado;
      if (k < 0.01) { torn.g = null; return; }
      if (!torn.g) spawnTornado();
      if (dt) moveTornado(dt);
      var v = toView(Gm, torn.g);
      if (v[2] < -0.5) { spawnTornado(); v = toView(Gm, torn.g); }   // bị xoay hẳn ra sau: sinh lại ở nửa đang thấy
      torn.sz = 0.6 + 0.75 * vnoise2(torn.t * 0.06, 3.3);           // lúc to lúc nhỏ
      torn.hk = 0.5 + 0.7 * vnoise2(torn.t * 0.045, 9.1);           // lúc cao lúc thấp
      var vis = k * smooth(0.0, 0.25, v[2]);
      if (vis < 0.01) return;
      var R = geo.R, bx = geo.cx + v[0] * R, by = geo.cy - v[1] * R, up = upOf(v), px = -up[1], py = up[0];
      // Vòi chỉ cao từ MẶT ĐẤT tới ĐÁY MÂY (chủ 07/10: cao quá trông không thật); khối mây mẹ vẽ
      // đè lên đỉnh. "Lúc cao lúc thấp" = đáy mây hạ xuống, nâng lên quanh mức đó.
      var Ht = clamp(R * 0.2, 26, 140) * (0.6 + 0.55 * torn.hk), rTop = Ht * 0.42 * torn.sz, rBot = Math.max(2, rTop * 0.09);
      torn.ht = Ht / R;
      var t = simT, tw = torn.t;
      var spine = function (f) {
        var m = (Math.sin(f * 3.1 + t * 0.9 + tw * 0.2) * 0.09 + Math.sin(f * 6.7 - t * 1.6) * 0.035) * Ht * Math.pow(f, 0.9);
        return [bx + up[0] * Ht * f + px * m, by + up[1] * Ht * f + py * m];
      };
      var rad = function (f) { return rBot + (rTop - rBot) * Math.pow(f, 1.6); };
      var TH = tornadoTheme(), cb = TH.cb;
      if (torn.theme !== TH.id) { torn.theme = TH.id; torn.parts = []; }   // đổi màu: dựng lại hạt theo tỉ lệ bụi mới
      var spr = particleSprite(cb), fl = torn.flash;
      c.save();
      // 1. bụi + gió xoáy ở chân: đĩa bụi dẹt, ba cánh xoắn ốc cuộn vào tâm
      softEllipse(c, bx, by, rTop * 0.9, rTop * 0.3, Math.atan2(py, px), [55, 52, 50], 0.45 * vis);
      c.lineWidth = 1.2;
      for (var arm = 0; arm < 3; arm++) {
        c.beginPath();
        var started = false;
        for (var th = 0; th < 8.5; th += 0.18) {
          var rr = rBot * 2.2 * Math.exp(0.33 * th);
          if (rr > rTop * 1.5) break;
          var an = -th + t * 2.4 + arm * 2.094, x = bx + px * Math.cos(an) * rr - up[0] * Math.sin(an) * rr * 0.3, y = by + py * Math.cos(an) * rr - up[1] * Math.sin(an) * rr * 0.3;
          if (started) c.lineTo(x, y); else { c.moveTo(x, y); started = true; }
        }
        c.strokeStyle = rgba(cb, (0.3 * vis).toFixed(3)); c.stroke();
      }
      // 2. mây xoáy trên đỉnh
      var top = spine(1), cr = rTop * 2.3;
      softEllipse(c, top[0], top[1], cr, cr * 0.36, Math.atan2(py, px), [16, 20, 32], 0.35 * vis);
      // 3. lõi thân tối mờ phía sau các hạt (cho có khối)
      c.beginPath();
      for (var f0 = 0; f0 <= 1.0001; f0 += 0.1) { var s0 = spine(f0), r0 = rad(f0) * 0.62; if (f0) c.lineTo(s0[0] - px * r0, s0[1] - py * r0); else c.moveTo(s0[0] - px * r0, s0[1] - py * r0); }
      for (var f1 = 1; f1 >= -0.0001; f1 -= 0.1) { var s1 = spine(f1), r1 = rad(f1) * 0.62; c.lineTo(s1[0] + px * r1, s1[1] + py * r1); }
      c.closePath();
      var body = c.createLinearGradient(bx, by, top[0], top[1]);
      body.addColorStop(0, "rgba(12,16,28," + (0.5 * TH.body * vis).toFixed(3) + ")"); body.addColorStop(1, "rgba(12,16,28," + (TH.body * vis).toFixed(3) + ")");
      c.fillStyle = body; c.fill();
      // 4. hạt: xoắn quanh trục, xoay nhanh ở chân chậm ở đỉnh, bốc lên rồi loe ra thành vòng ở đỉnh
      var PN = Math.round((profile === "high" ? 520 : profile === "balanced" ? 300 : 150) * vis);
      while (torn.parts.length < PN) torn.parts.push(tornadoParticle(TH.dust));
      if (torn.parts.length > PN) torn.parts.length = PN;
      for (var pass = 0; pass < 2; pass++) {
        c.globalCompositeOperation = pass && TH.glow ? "lighter" : "source-over";
        for (var i = 0; i < torn.parts.length; i++) {
          var p = torn.parts[i];
          if (dt && pass === 0) {
            p.a += dt * (2.2 + 4.8 * (1 - p.f));
            p.f += dt * p.sp;
            p.rot += dt * 5;
            if (p.f > 1.1 || (p.kind === 2 && p.f > 0.55)) { p.f = 0; p.rj = 0.7 + Math.random() * 0.5; }
          }
          var ff = Math.min(p.f, 1), sp = spine(ff);
          var r = rad(ff) * p.rj * (1 + Math.max(0, p.f - 0.86) * 3.4);
          var sa = Math.sin(p.a), front = sa > 0;
          if ((pass === 1) !== front && p.kind === 0) continue;
          if (p.kind !== 0 && pass === 1) continue;
          var ca = Math.cos(p.a);
          var x2 = sp[0] + px * ca * r - up[0] * sa * r * 0.24, y2 = sp[1] + py * ca * r - up[1] * sa * r * 0.24;
          if (p.kind === 0) {        // hạt sáng: vệt cung ngắn theo chiều xoay + chấm sáng
            var al = vis * (front ? 0.8 : 0.26) * (0.4 + 0.6 * ff) * (1 + 0.8 * fl);
            // vệt cung xoắn (hai đoạn bám theo vòng elip) - giống các vòng hạt mảnh trong ảnh mẫu
            var a0 = p.a - 0.7, am = p.a - 0.35;
            var x0 = sp[0] + px * Math.cos(a0) * r - up[0] * Math.sin(a0) * r * 0.24, y0 = sp[1] + py * Math.cos(a0) * r - up[1] * Math.sin(a0) * r * 0.24;
            var xm = sp[0] + px * Math.cos(am) * r - up[0] * Math.sin(am) * r * 0.24, ym = sp[1] + py * Math.cos(am) * r - up[1] * Math.sin(am) * r * 0.24;
            c.strokeStyle = rgba(cb, Math.min(1, al * 0.6).toFixed(3)); c.lineWidth = 0.75;
            c.beginPath(); c.moveTo(x0, y0); c.quadraticCurveTo(xm, ym, x2, y2); c.stroke();
            var ds = (1.4 + 2.2 * p.s) * Math.min(1.6, R / 160);
            if (spr) { c.globalAlpha = Math.min(1, al); c.drawImage(spr, x2 - ds / 2, y2 - ds / 2, ds, ds); c.globalAlpha = 1; }
            else { c.fillStyle = rgba(cb, Math.min(1, al)); c.beginPath(); c.arc(x2, y2, ds * 0.2, 0, 6.2832); c.fill(); }
          } else if (p.kind === 1) { // bụi đen cuộn theo
            c.fillStyle = (TH.id === "dark" ? "rgba(12,12,16," : "rgba(35,34,38,") + ((TH.glow ? 0.55 : 0.75) * vis).toFixed(3) + ")";
            c.beginPath(); c.arc(x2, y2, 1.2 + p.s, 0, 6.2832); c.fill();
          } else {                   // mảnh vụn (cây, mái tôn) bị hút lên, quay lộn
            var dsz = (2 + 2.5 * p.s) * Math.min(1.6, R / 160);
            c.save(); c.translate(x2, y2); c.rotate(p.rot);
            c.fillStyle = "rgba(48,40,34," + (0.8 * vis).toFixed(3) + ")"; c.fillRect(-dsz / 2, -dsz / 4, dsz, dsz / 2);
            c.restore();
          }
        }
      }
      c.globalCompositeOperation = "source-over";
      // 4b. khối mây giông MẸ phủ đỉnh vòi: vòi thò ra từ đáy mây; loé sáng khi sét quấn vòi
      var cw = Math.max(rTop * 2.4, 18), crot = Math.atan2(py, px), cfl = Math.min(1, torn.flash * 0.8);
      var mc = [Math.round(30 + 200 * cfl), Math.round(33 + 190 * cfl), Math.round(44 + 150 * cfl)];
      softEllipse(c, top[0] + up[0] * cw * 0.05, top[1] + up[1] * cw * 0.05, cw, cw * 0.3, crot, mc, 0.85 * vis);
      for (var cp = 0; cp < 7; cp++) {
        var ox = (cp / 6 - 0.5) * 1.6 * cw, oy = (0.18 + 0.22 * Math.abs(Math.sin(cp * 2.3))) * cw;
        softEllipse(c, top[0] + px * ox + up[0] * oy, top[1] + py * ox + up[1] * oy, cw * (0.32 + 0.12 * Math.sin(cp * 1.7 + 1)), cw * 0.22, crot, mc, 0.8 * vis);
      }
      // 5. gió thổi vòng quanh thân: các cung mờ xoay quanh vòi ở ba độ cao
      for (var h = 0; h < 3; h++) {
        var fh = 0.3 + h * 0.25, sh = spine(fh), rh = rad(fh) * 1.9 + 6, a1 = t * (2.6 - h * 0.5) + h * 2;
        c.strokeStyle = "rgba(220,235,255," + (0.22 * vis).toFixed(3) + ")"; c.lineWidth = 1;
        c.beginPath(); c.ellipse(sh[0], sh[1], rh, rh * 0.24, Math.atan2(py, px), a1, a1 + 1.8); c.stroke();
      }
      // 6. sét quấn quanh vòi (vàng trắng), 0,5-1,8 giây một lần
      torn.flash *= Math.exp(-(dt || 0.016) * 8);
      if (dt && now > torn.nz && profile !== "reduced") {
        torn.nz = now + TH.zap[0] + Math.random() * (TH.zap[1] - TH.zap[0]);
        var zz = { at: now, a0: Math.random() * 6.28, dir: Math.random() < 0.5 ? -1 : 1, j: [] };
        for (var q = 0; q < 18; q++) zz.j.push((Math.random() - 0.5) * 0.35);
        torn.zaps.push(zz); torn.flash = 1;
        // sét từ mây mẹ đánh xuống đất quanh chân vòi (nhiều nhất ở tông xám / tối)
        if (Math.random() < TH.ground) spawnBolt(now, { g: torn.g, sig: 0.05, flash: 0 }, Ht * 0.97);
        if (torn.zaps.length > 3) torn.zaps.shift();
      }
      c.globalCompositeOperation = "lighter"; c.lineCap = "round"; c.lineJoin = "round";
      torn.zaps = torn.zaps.filter(function (zz) {
        var age = (now - zz.at) / 1000;
        if (age > 0.4) return false;
        var flk = (age < 0.06 ? 1 : age < 0.1 ? 0.3 : Math.max(0, 1 - (age - 0.1) / 0.3)) * vis;
        var pts = [];
        for (var q = 0; q < 18; q++) {
          var fz = 0.97 - q * 0.055, s2 = spine(Math.max(0, fz)), r2 = rad(Math.max(0, fz)) * (0.95 + zz.j[q]);
          var az = zz.a0 + fz * 7 * zz.dir;
          pts.push([s2[0] + px * Math.cos(az) * r2 - up[0] * Math.sin(az) * r2 * 0.24 + zz.j[q] * 8, s2[1] + py * Math.cos(az) * r2 - up[1] * Math.sin(az) * r2 * 0.24]);
        }
        BOLT_PASS.forEach(function (Lp) {
          c.strokeStyle = Lp[1] + (Lp[2] * flk).toFixed(3) + ")"; c.lineWidth = Math.max(0.6, Lp[0] * 0.7);
          c.beginPath(); c.moveTo(pts[0][0], pts[0][1]);
          for (var q2 = 1; q2 < pts.length; q2++) c.lineTo(pts[q2][0], pts[q2][1]);
          c.stroke();
        });
        return true;
      });
      c.restore();
    }

    // SẤM SÉT: tia đánh từ đáy mây xuống, chỉ trong các ô bão (spawnBolt). Tia là đường
    // gấp khúc (chia đôi đoạn + lệch ngẫu nhiên) kèm 1-2 nhánh, lưu dạng (t dọc thân, o lệch
    // ngang) nên quả cầu xoay thì tia vẫn bám đúng điểm. Chạm đất toé tia lửa (hạt nóng) và chớp
    // sáng mây quanh điểm đánh (uBolt trong shader). Nhịp chớp: loé - tắt - loé - tàn dần.
    function jag(pts, t0, o0, t1, o1, depth, rough) {
      if (!depth) { pts.push([t1, o1]); return; }
      var tm = (t0 + t1) / 2, om = (o0 + o1) / 2 + (Math.random() - 0.5) * rough;
      jag(pts, t0, o0, tm, om, depth - 1, rough * 0.55);
      jag(pts, tm, om, t1, o1, depth - 1, rough * 0.55);
    }
    // Sét chỉ sinh TRONG ô bão (0.65.41): điểm đánh rải quanh tâm ô, tia đi từ đáy mây (điểm đất
    // nâng lên cloudLift) xuống đất, 2-4 nhánh rẽ rộng. 30% số lần chỉ là chớp TRONG mây (khối mây
    // loé vàng trắng, không có tia).
    function spawnBolt(now, cl, lift) {
      var g = offsetGeo(cl.g, gauss() * 0.4 * cl.sig, gauss() * 0.3 * cl.sig);
      var main = [[0, 0]];
      jag(main, 0, 0, 1, 0, 5, 0.3);
      var paths = [{ p: main, w: 1 }], nb = 2 + ((Math.random() * 3) | 0);
      for (var b = 0; b < nb; b++) {
        var st = main[3 + Math.floor(Math.random() * (main.length - 10))], br = [st.slice()];
        jag(br, st[0], st[1], Math.min(0.97, st[0] + 0.25 + Math.random() * 0.25),
            st[1] + (Math.random() < 0.5 ? -1 : 1) * (0.15 + Math.random() * 0.3), 3, 0.16);
        paths.push({ p: br, w: 0.55 });
      }
      // tia bò lan trên mặt đất quanh điểm đánh
      var arcs = [], na = 4 + ((Math.random() * 3) | 0);
      for (var a = 0; a < na; a++) {
        var pa = [[0, 0]];
        jag(pa, 0, 0, 1, 0, 3, 0.35);
        arcs.push({ ang: (a / na) * 6.2832 + Math.random() * 0.6, len: 0.4 + Math.random() * 0.5, p: pa });
      }
      bolts.push({ g: g, at: now, paths: paths, arcs: arcs, jx: (Math.random() - 0.5) * 0.3, lift: lift || 0 });
      if (bolts.length > 5) bolts.shift();
      bolt = { g: g, k: 1 };
      cl.flash = 1;
      var nS = profile === "high" ? 26 : profile === "balanced" ? 16 : 8;
      for (var s = 0; s < nS; s++) hot.push(launch(g, 0.25 + Math.random() * 0.45, 0.9, "spark"));
    }
    // Màu sét vàng trắng: quầng vàng cam rộng, thân vàng nhạt, lõi trắng.
    var BOLT_PASS = [[9, "rgba(255,190,80,", 0.24], [3.2, "rgba(255,232,160,", 0.65], [1.3, "rgba(255,255,240,", 1]];
    function drawLightning(c, now, dt) {
      if (look.lightning && fx.lightning > 0.5 && profile !== "reduced") {
        for (var i = 0; i < cells.length; i++) {
          var cl = cells[i];
          if (cl.k < 0.5 || now < cl.nb) continue;
          var cz = toView(Gm, cl.g)[2];
          if (cz < 0.12) continue;
          cl.nb = now + 600 + Math.random() * 2400;
          if (Math.random() < 0.7) spawnBolt(now, cl); else cl.flash = 1;
        }
      }
      bolt.k *= Math.exp(-(dt || 0.016) * 7);
      if (!bolts.length) return;
      var R = geo.R, L = cloudLift();
      c.save(); c.globalCompositeOperation = "lighter"; c.lineCap = "round"; c.lineJoin = "round";
      bolts = bolts.filter(function (b) {
        var age = (now - b.at) / 1000;
        if (age > 0.45) return false;
        var v = toView(Gm, b.g);
        if (v[2] < 0.05) return true;
        var fl = (age < 0.07 ? 1 : age < 0.12 ? 0.3 : age < 0.2 ? 0.95 : Math.max(0, 1 - (age - 0.2) / 0.25)) * Math.max(fx.lightning, 0.3);
        var ex = geo.cx + v[0] * R, ey = geo.cy - v[1] * R, up = upOf(v);
        var LL = b.lift || L * 1.02;   // sét của vòi rồng đánh từ mây mẹ (cao hơn mây ô bão)
        var sx = ex + up[0] * LL - up[1] * LL * b.jx, sy = ey + up[1] * LL + up[0] * LL * b.jx;
        var px = -(sy - ey), py = sx - ex;
        var line = function (pts, w) {
          BOLT_PASS.forEach(function (Lp) {
            c.strokeStyle = Lp[1] + (Lp[2] * fl).toFixed(3) + ")"; c.lineWidth = Math.max(0.6, Lp[0] * w);
            c.beginPath(); c.moveTo(pts[0][0], pts[0][1]);
            for (var i2 = 1; i2 < pts.length; i2++) c.lineTo(pts[i2][0], pts[i2][1]);
            c.stroke();
          });
        };
        b.paths.forEach(function (path) {
          line(path.p.map(function (q) { return [sx + (ex - sx) * q[0] + px * q[1], sy + (ey - sy) * q[0] + py * q[1]]; }), path.w);
        });
        // lan trên mặt đất: mặt đất nhìn nghiêng nên tia bò dẹt theo trục "lên trời"
        var hx = -up[1], hy = up[0];
        b.arcs.forEach(function (ar) {
          var dx = hx * Math.cos(ar.ang) - up[0] * Math.sin(ar.ang) * 0.32, dy = hy * Math.cos(ar.ang) - up[1] * Math.sin(ar.ang) * 0.32;
          var ln = L * 0.7 * ar.len * Math.min(1, age / 0.08 + 0.2), nx2 = -dy, ny2 = dx;
          line(ar.p.map(function (q) { return [ex + dx * ln * q[0] + nx2 * ln * q[1], ey + dy * ln * q[0] + ny2 * ln * q[1]]; }), 0.45);
        });
        var gr = c.createRadialGradient(ex, ey, 0, ex, ey, L * 0.9);
        gr.addColorStop(0, "rgba(255,240,190," + (0.8 * fl).toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,200,110,0)");
        c.fillStyle = gr; c.beginPath(); c.ellipse(ex, ey, L * 0.9, L * 0.4, Math.atan2(hy, hx), 0, 6.2832); c.fill();
        return true;
      });
      c.restore();
    }
    function drawLookFx(c, now, dt) {
      drawEruption(c, now, dt);     // sông dung nham + núi sát mặt đất: vẽ trước mây, mưa, gió
      drawRain(c, dt);
      drawStormClouds(c);
      drawWind(c, dt);              // gió ở độ cao mây
      drawHot(c, dt);
      drawTornado(c, now, dt);
      drawLightning(c, now, dt);
    }

    function roundRect(c, x, y, w, h, r) {
      c.beginPath();
      c.moveTo(x + r, y); c.lineTo(x + w - r, y); c.quadraticCurveTo(x + w, y, x + w, y + r);
      c.lineTo(x + w, y + h - r); c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      c.lineTo(x + r, y + h); c.quadraticCurveTo(x, y + h, x, y + h - r);
      c.lineTo(x, y + r); c.quadraticCurveTo(x, y, x + r, y); c.closePath();
    }

    // ---------- khung hình ----------
    function frame(now, once) {
      if (destroyed || (!once && !running)) return;
      if (!once) raf = requestAnimationFrame(loopFn);
      if (!W || !H) { resize(); if (!W) return; }
      var reduced = profile === "reduced";
      // reduced: ~8 khung/giây là đủ cho một hành tinh gần như tĩnh chỉ đổi màu
      if (!once && reduced && now - lastNow < 120) return;
      var dt = lastNow ? Math.min(0.1, (now - lastNow) / 1000) : 0;
      lastNow = now;
      // FPS: chỉ đo khi chạy liên tục ở hồ sơ có shader nặng
      if (!once && !reduced && dt > 0 && now > fpsSkipUntil) {
        fpsWin.push(dt);
        if (fpsWin.length >= 90) {
          var avg = fpsWin.reduce(function (a, b) { return a + b; }, 0) / fpsWin.length;
          fpsWin = [];
          if (1 / avg < 30) {
            if (++lowWins >= 2) {
              lowWins = 0;
              var next = profile === "high" ? "balanced" : profile === "balanced" ? "safe" : null;
              if (next) { applyProfile(next); fpsSkipUntil = now + 2500; try { opts.onQuality && opts.onQuality(next); } catch (e) {} }
            }
          } else lowWins = 0;
        }
      }
      // nội suy trạng thái
      var tg = TARGET[state] || TARGET.READY;
      var k = reduced ? 0.35 : Math.min(1, dt * 3.2);
      for (var i = 0; i < cur.length; i++) cur[i] += (tg[i] - cur[i]) * (once ? 1 : k);
      ampS += (amp - ampS) * (amp > ampS ? 0.35 : 0.08);
      hover += (hoverT - hover) * 0.12;
      cam.yaw += (cam.tyaw - cam.yaw) * 0.12; cam.pitch += (cam.tpitch - cam.pitch) * 0.12;
      cam.zoom += (cam.tzoom - cam.zoom) * 0.15;
      if (!reduced) { par.x += (par.tx - par.x) * 0.05; par.y += (par.ty - par.y) * 0.05; }
      else { par.x = par.y = 0; }
      if (!reduced) { simT += dt; flowT += dt * cur[0]; }
      callK += ((inCall ? 1 : 0) - callK) * (reduced || once ? 1 : Math.min(1, dt * 2.6));
      if (now - moonPhAt > 600000) { moonPh = moonPhase(new Date()); moonPhAt = now; }   // pha trăng đổi chậm
      if (now - astroAt > 20000) {     // Mặt Trời trôi 0,25 độ/phút: 20 giây tính lại là mượt
        var dNow = new Date();
        sunG = sunGeo(dNow); moonG = moonGeo(dNow); orbitG = moonOrbit(dNow); astroAt = now;
      }
      var kw = once ? 1 : Math.min(1, dt * 0.8);
      for (var wi = 0; wi < 4; wi++) wx.cur[wi] += (wx.tgt[wi] - wx.cur[wi]) * kw;
      if (!reduced && wx.cur[2] > 0.3 && now > wx.nextFlash) {     // sét: chớp đôi, nhịp ngẫu nhiên
        wx.flash = 1; wx.flash2 = now + 110 + Math.random() * 120;
        wx.nextFlash = now + 900 + Math.random() * 4200 * (1.35 - wx.cur[2]);
      }
      if (wx.flash2 && now > wx.flash2) { wx.flash = Math.max(wx.flash, 0.7); wx.flash2 = 0; }
      wx.flash *= Math.exp(-(dt || 0.016) * 9);
      ing.k += ((ing.on ? 1 : 0) - ing.k) * (once ? 1 : Math.min(1, dt * 1.5));
      var fk = once ? 1 : Math.min(1, dt * 1.6);
      for (var fi = 0; fi < FX_KEYS.length; fi++) fx[FX_KEYS[fi]] += ((look[FX_KEYS[fi]] ? 1 : 0) - fx[FX_KEYS[fi]]) * fk;
      if (!reduced) windT += dt * (1 + 7 * fx.wind);
      updateCells(reduced ? 0 : dt);
      // opts.dark: ô xem trước trong Cài đặt luôn nằm trên nền vũ trụ tối, dù trang đang sáng.
      light = !opts.dark && document.documentElement.getAttribute("data-theme") === "light";
      layout();

      // --- lớp WebGL ---
      if (gl && profile !== "safe" && glCv.style.display !== "none") {
        var P = (profile === "high" && progHi) ? progHi : prog;
        gl.viewport(0, 0, glCv.width, glCv.height);
        gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
        gl.useProgram(P.pr);
        var u = P.u, s = dprGL;
        gl.uniform2f(u.uRes, glCv.width, glCv.height);
        gl.uniform2f(u.uC, geo.cx * s, (H - geo.cy) * s);
        gl.uniform1f(u.uR, geo.R * s);
        gl.uniform1f(u.uT, reduced ? 12.0 : simT);
        gl.uniform1f(u.uFlowT, reduced ? 12.0 : flowT + 40);
        gl.uniform2f(u.uRot, cam.yaw, cam.pitch);
        gl.uniform1f(u.uLight, light ? 1 : 0);
        gl.uniform1f(u.uAmp, ampS);
        gl.uniform1f(u.uHover, hover);
        gl.uniform4f(u.uS1, cur[0], cur[1], cur[2], cur[3]);
        gl.uniform4f(u.uS2, cur[4], cur[5], cur[6], cur[7]);
        gl.uniform2f(u.uPar, par.x * 14 * s, -par.y * 10 * s);
        gl.uniform1f(u.uHorizon, H < 320 ? 0.86 : 0.72);
        var SL = sunLook();
        if (geo.sun) gl.uniform4f(u.uSun, geo.sun.x * s, (H - geo.sun.y) * s, geo.sun.r * s, SL.k);
        else gl.uniform4f(u.uSun, 0, 0, 1, 0);
        gl.uniform3f(u.uSunC, SL.c[0], SL.c[1], SL.c[2]);
        gl.uniformMatrix3fv(u.uGeo, false, [Gm[0][0], Gm[1][0], Gm[2][0], Gm[0][1], Gm[1][1], Gm[2][1], Gm[0][2], Gm[1][2], Gm[2][2]]);
        var Lv = geo.L || [-0.6, 0.5, 0.6];
        gl.uniform3f(u.uL, Lv[0], Lv[1], Lv[2]);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, vnTex);
        gl.uniform1i(u.uVN, 0);
        gl.uniform1f(u.uVNOn, vnOn ? 1 : 0);
        var bb = (window.JoyceVNGeo && window.JoyceVNGeo.bbox) || [101.5, 6.5, 117.5, 24];
        gl.uniform4f(u.uVNBox, bb[0], bb[3], bb[2] - bb[0], bb[3] - bb[1]);
        gl.uniform3f(u.uVNc, VN_CENTER[0], VN_CENTER[1], VN_CENTER[2]);
        gl.uniform4f(u.uWx, wx.cur[0], wx.cur[1], wx.cur[2], wx.cur[3]);
        gl.uniform4f(u.uWxC, wx.center[0], wx.center[1], wx.center[2], wx.sigma);
        gl.uniform1f(u.uFlash, wx.flash);
        gl.uniform1f(u.uGal, 0.45 + 0.55 * (geo.gal || 0));
        gl.uniform1f(u.uCore, 1 - smooth(1.8, 3.6, cam.zoom));   // phóng cận Việt Nam: lõi lặn dần
        if (geo.bh) gl.uniform4f(u.uBH, geo.bh.x * s, (H - geo.bh.y) * s, geo.bh.r * s, ing.k);
        else gl.uniform4f(u.uBH, 0, 0, 0, 0);
        // Giao diện tùy biến (tab Quả tinh cầu)
        var PL = LD.pal;
        gl.uniform3f(u.uPa, PL.deep[0], PL.deep[1], PL.deep[2]);
        gl.uniform3f(u.uPb, PL.sea[0], PL.sea[1], PL.sea[2]);
        gl.uniform3f(u.uPc, PL.rim[0], PL.rim[1], PL.rim[2]);
        gl.uniform3f(u.uPd, PL.mint[0], PL.mint[1], PL.mint[2]);
        var mv = geo.moonV || [0, 0, 1], ml = Math.hypot(mv[0], mv[1], mv[2]) || 1;
        var mI = moon ? (1 - Math.cos(2 * Math.PI * moonShownPhase())) / 2 * look.moonGlow * 0.35 : 0;
        gl.uniform4f(u.uLk, look.sunPower, look.atmo, look.surface, mI);
        gl.uniform3f(u.uMoonV, mv[0] / ml, mv[1] / ml, mv[2] / ml);
        // Mưa/sét không còn phủ mây khắp quả cầu: chỉ dày + đen trong các ô bão (uRc/uRs).
        gl.uniform4f(u.uCl, look.clouds * 0.55, Math.min(0.85, look.cloudDark * 0.75), reduced ? 12.0 : windT, fx.rain * 0.9);
        var slv = cloudLevel(), rsv = [0.1, 0.1, 0.1, 0.1];
        for (var ci = 0; ci < 4; ci++) {
          var cc = cells[ci];
          rcBuf[ci * 4] = cc ? cc.g[0] : 0; rcBuf[ci * 4 + 1] = cc ? cc.g[1] : 1; rcBuf[ci * 4 + 2] = cc ? cc.g[2] : 0;
          rcBuf[ci * 4 + 3] = cc ? cc.k * slv : 0;
          if (cc) rsv[ci] = cc.sig;
        }
        gl.uniform4fv(u.uRc, rcBuf);
        gl.uniform4f(u.uRs, rsv[0], rsv[1], rsv[2], rsv[3]);
        var tgv = torn.g || [0, 1, 0];
        gl.uniform4f(u.uTor, tgv[0], tgv[1], tgv[2], torn.g ? fx.tornado : 0);
        gl.uniform4f(u.uBolt, bolt.g[0], bolt.g[1], bolt.g[2], bolt.k);
        gl.uniform4f(u.uCo, look.coreVis, look.coreGlow, fx.eruption, clamp(stormLevel() / Math.max(cloudLevel(), 1e-3), 0, 1));
        gl.bindVertexArray(vao);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      }

      // --- lớp 2D ---
      var c = ctx2;
      c.clearRect(0, 0, W, H);
      var ddt = reduced ? 0 : dt;
      if (profile === "safe" || !gl) drawSafePlanet(c, now);
      drawMoonPath(c);
      drawBHSwirl(c, now, ddt);
      drawKnowSky(c, now, ddt);
      drawRings(c, false);
      drawParticles(c, false, ddt);
      drawKnowOrbit(c, false, ddt);
      drawSatDots(c, false, ddt);
      drawMoon(c, false, ddt);
      drawLookFx(c, now, ddt);
      drawRings(c, true);
      drawParticles(c, true, 0);
      drawKnowOrbit(c, true, 0);
      drawSatDots(c, true, 0);
      drawMoon(c, true, 0);
      drawGlyphs(c, now);
      drawVN(c, now);
      drawIngest(c, now, ddt);
      drawTrace(c, now);                            // tia tri thức của câu hỏi đang trả lời
      if (opts.labels !== false) drawLabels(c);
      drawKnowFocus(c, now, reduced ? 0.12 : dt);   // Big Bang đè lên trên cùng (kể cả nhãn)
      drawBHView(c, now, reduced ? 0.12 : dt);      // cảnh nhìn sâu vào hố đen phủ cả khung
    }
    function loopFn(now) { frame(now, false); }

    // ---------- tương tác ----------
    function local(e) { var r = ovCv.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }
    function onPlanet(x, y) { return Math.hypot(x - geo.cx, y - geo.cy) <= geo.R; }
    function hitSat(x, y) {
      var best = null, bd = 1e9;
      var all = sats.slice();
      if (sun && sun.pt) all.push(sun);
      if (moon && moon.pt) all.push(moon);
      all.forEach(function (s) {
        if (!s.pt) return;
        // mặt trăng sau hành tinh bị che thì không bấm xuyên qua được
        if (s.kind === "moon" && s.pt.z < 0 && onPlanet(s.pt.x, s.pt.y)) return;
        var hr = s.kind === "sun" ? geo.sun.r * 1.3 : s.kind === "moon" ? geo.R * 0.19 * look.moonSize : 14;
        var d = Math.hypot(s.pt.x - x, s.pt.y - y);
        if (d < hr && d < bd) { best = s; bd = d; }
        var l = s.lbl;
        if (l && x >= l.x - 2 && x <= l.x + l.w + 2 && y >= l.y - 2 && y <= l.y + l.h + 2 && !best) best = s;
      });
      return best;
    }
    function statusText(s) {
      var t = (window.t || function (k) { return k; });
      var key = { online: "planet.st_online", degraded: "planet.st_degraded",
                  offline: "planet.st_offline", unauthorized: "planet.st_unauthorized" }[s.status];
      var v = key ? t(key) : s.status;
      return v === key ? s.status : v;
    }
    function showTip(s, x, y) {
      if (!s || opts.tips === false) { tip.hidden = true; return; }
      var p = s.p || {};
      tip.innerHTML = "";
      var n = document.createElement("div"); n.className = "pt-name"; n.textContent = s.name;
      var st = document.createElement("div"); st.className = "pt-st st-" + s.status;
      st.textContent = statusText(s) + (p.ms != null ? " · " + p.ms + "ms" : "");
      tip.appendChild(n); tip.appendChild(st);
      if (s.kind) {   // vai thiên thể: mặt trời / mặt trăng (kèm pha trăng hôm nay)
        var t = (window.t || function (k) { return k; });
        var ro = document.createElement("div"); ro.className = "pt-role";
        ro.textContent = s.kind === "sun" ? t("planet.role_sun")
          : t("planet.role_moon") + " · " + t(MOON_KEYS[moonPhaseKey(moonPh.phase)]) + " · " + Math.round(moonPh.illum * 100) + "%";
        tip.appendChild(ro);
      }
      tip.hidden = false;
      var tw = tip.offsetWidth || 140;
      tip.style.left = clamp(x + 14, 6, W - tw - 6) + "px";
      tip.style.top = clamp(y - 10, 6, H - 50) + "px";
    }

    // ---------- cảm ứng: chụm/mở hai ngón để zoom (chủ yêu cầu 07/10, điện thoại) ----------
    // Mỗi ngón đang chạm là một con trỏ trong `pts`. Hai ngón = cử chỉ chụm: tỉ lệ khoảng cách
    // hai ngón nhân vào zoom lúc bắt đầu chụm, điểm giữa hai ngón kéo đi thì xoay quả cầu. Đã
    // chụm thì lúc nhấc ngón KHÔNG tính là bấm (bấm hành tinh = gọi Joyce, gọi nhầm là phiền).
    var pts = {}, pinch = null, lastTap = null;
    function nPts() { return Object.keys(pts).length; }
    function pinchInfo() {
      var ids = Object.keys(pts), a = pts[ids[0]], b = pts[ids[1]];
      return { d: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
    }
    function startPinch() {
      var i = pinchInfo();
      pinch = { d0: i.d, z0: cam.tzoom, mx: i.mx, my: i.my, yaw: cam.tyaw, pitch: cam.tpitch };
      drag = null;
      clearTimeout(clickTimer);
      lastTap = null;
      tip.hidden = true;
    }
    function movePinch() {
      var i = pinchInfo();
      cam.tzoom = clamp(pinch.z0 * i.d / pinch.d0, ZMIN, ZMAX);
      var zk = 1 / Math.max(1, cam.zoom * 0.8);
      cam.tyaw = clamp(pinch.yaw + (i.mx - pinch.mx) * 0.004 * zk, -2.8, 2.8);
      cam.tpitch = clamp(pinch.pitch + (i.my - pinch.my) * 0.003 * zk, -1.1, 1.1);
    }
    // Ngón nhấc lên / bị huỷ: còn đúng một ngón thì kéo tiếp từ chỗ ngón đó, đánh dấu "đã di
    // chuyển" để nhấc nốt ngón cuối không thành một cú bấm.
    function liftPointer(e) {
      delete pts[e.pointerId];
      try { ovCv.releasePointerCapture(e.pointerId); } catch (_) {}
      if (!pinch) return false;
      if (nPts() >= 2) { startPinch(); return true; }
      pinch = null;
      var ids = Object.keys(pts);
      drag = ids.length ? { x: pts[ids[0]].x, y: pts[ids[0]].y, yaw: cam.tyaw, pitch: cam.tpitch, moved: true } : null;
      return true;
    }
    function onCancel(e) { liftPointer(e); pinch = null; drag = null; pts = {}; }

    function onMove(e) {
      var p = local(e);
      if (pts[e.pointerId]) pts[e.pointerId] = p;
      if (pinch) { if (nPts() >= 2) movePinch(); return; }
      if (drag) {
        var dx = p.x - drag.x, dy = p.y - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
        if (drag.moved) {
          // Xoay quả cầu: kéo ngang đổi kinh độ, kéo dọc đổi vĩ độ (chậm lại khi phóng gần).
          var zk = 1 / Math.max(1, cam.zoom * 0.8);
          cam.tyaw = clamp(drag.yaw + dx * 0.004 * zk, -2.8, 2.8);
          cam.tpitch = clamp(drag.pitch + dy * 0.003 * zk, -1.1, 1.1);
        }
        return;
      }
      if (bhv.k > 0.05) { ovCv.style.cursor = "pointer"; tip.hidden = true; return; }   // đang nhìn sâu vào hố đen
      if (profile !== "reduced" && W) { par.tx = (p.x / W - 0.5) * 2; par.ty = (p.y / H - 0.5) * 2; }
      var s = hitSat(p.x, p.y);
      hoverSat = s;
      var overBH = !s && onBlackHole(p.x, p.y);
      var kh = s || overBH ? null : hitKnow(p.x, p.y);
      if (kh !== know.hover) { try { opts.onKnowledgeHover && opts.onKnowledgeHover(kh ? kh.b : null); } catch (_) {} }
      know.hover = kh;
      var onP = !s && !kh && onPlanet(p.x, p.y);
      hoverT = onP ? 1 : 0;
      ovCv.style.cursor = s || kh || onP || overBH ? "pointer" : "default";
      if (overBH) showBHTip(p.x, p.y);
      else if (kh) showKnowTip(kh, p.x, p.y); else showTip(s, p.x, p.y);
    }
    function onDown(e) {
      if (e.button !== 0) return;
      var p = local(e);
      // Ngón ĐẦU của một cử chỉ mới: xoá con trỏ cũ còn sót (lỡ mất pointerup), không thì một
      // ngón chạm mới bị tính thành chụm với "bóng ma" của ngón trước.
      if (e.isPrimary) { pts = {}; pinch = null; }
      pts[e.pointerId] = p;
      try { ovCv.setPointerCapture(e.pointerId); } catch (_) {}
      if (nPts() >= 2) { startPinch(); return; }
      drag = { x: p.x, y: p.y, yaw: cam.tyaw, pitch: cam.tpitch, moved: false };
    }
    function onUp(e) {
      if (liftPointer(e)) return;          // đang/vừa chụm: không phải một cú bấm
      if (!drag) return;
      var moved = drag.moved;
      drag = null;
      if (moved) return;
      var p = local(e);
      if (bhv.target || bhv.k > 0.05) { openBlackHole(false); return; }   // đang nhìn sâu: bấm đâu cũng quay ra
      // Chạm đúp bằng ngón tay = về góc nhìn ban đầu (điện thoại không phải máy nào cũng bắn
      // dblclick; không bắt ở đây thì chạm đúp thành hai cú bấm: gọi Joyce rồi cúp ngay).
      if (e.pointerType === "touch") {
        var tnow = performance.now();
        if (lastTap && tnow - lastTap.t < 320 && Math.hypot(p.x - lastTap.x, p.y - lastTap.y) < 36) {
          lastTap = null;
          onDbl();
          return;
        }
        lastTap = { t: tnow, x: p.x, y: p.y };
      }
      var s = hitSat(p.x, p.y);
      if (s) { try { opts.onSatelliteClick && opts.onSatelliteClick(s.p, { x: p.x, y: p.y }); } catch (_) {} return; }
      if (onBlackHole(p.x, p.y)) { openBlackHole(true); return; }   // bấm giữa hố đen: nhìn sâu vào
      var kh = hitKnow(p.x, p.y);
      if (kh) { try { opts.onKnowledgeClick && opts.onKnowledgeClick(kh.b, { x: p.x, y: p.y }); } catch (_) {} return; }
      if (!onPlanet(p.x, p.y)) {   // bấm khoảng trống trên vũ trụ: hud.js đóng khung thông tin đang mở
        try { opts.onBackgroundClick && opts.onBackgroundClick(); } catch (_) {}
        return;
      }
      if (onPlanet(p.x, p.y)) {
        // Chờ một nhịp để nhận ra double-click (đặt lại góc nhìn) - không thì bấm đúp
        // sẽ gọi rồi cúp ngay.
        clearTimeout(clickTimer);
        clickTimer = setTimeout(function () {
          try { opts.onPlanetClick && opts.onPlanetClick(); } catch (_) {}
        }, 260);
      }
    }
    function onDbl() {
      clearTimeout(clickTimer);
      cam.tyaw = cam.tpitch = 0; cam.tzoom = 1;
    }
    function onWheel(e) {
      // Ô xem trước nằm giữa trang Cài đặt: lăn chuột phải cuộn trang, không phóng quả cầu.
      // Chụm hai ngón trên touchpad (trình duyệt gửi wheel kèm ctrlKey) thì vẫn zoom.
      if (opts.wheel === false && !e.ctrlKey) return;
      if (bhv.k > 0.05) { e.preventDefault(); return; }   // đang nhìn sâu vào hố đen: không zoom quả cầu
      e.preventDefault();
      if (e.ctrlKey) {   // chụm touchpad: nhiều sự kiện nhỏ liên tiếp -> zoom liên tục theo lực tay
        cam.tzoom = clamp(cam.tzoom * Math.exp(-clamp(e.deltaY, -60, 60) * 0.01), ZMIN, ZMAX);
        return;
      }
      // Bốn tầng: Ngân Hà (~0,35) - Hệ Mặt Trời (~0,6) - Trái Đất (1) - cận cảnh Việt Nam (2-3,4).
      var stp = cam.tzoom > 2 ? 1.14 : 1.087;
      cam.tzoom = clamp(cam.tzoom * (e.deltaY > 0 ? 1 / stp : stp), ZMIN, ZMAX);
    }
    function onLeave() { hoverSat = null; know.hover = null; hoverT = 0; par.tx = par.ty = 0; tip.hidden = true; }

    function onVis() { if (document.hidden) stopLoop(); else if (!paused) startLoop(); }
    function onLost(e) {
      e.preventDefault();
      stopLoop();
      freeGL();
      glCv.style.display = "none";
      profile = "safe";
      if (host) host.dataset.quality = "safe";
      if (!paused) startLoop();
    }
    function onRestored() { applyProfile(pickProfile()); }
    function onMotionPref() { applyProfile(pickProfile()); }

    function startLoop() {
      if (running || destroyed) return;
      running = true; lastNow = 0;
      raf = requestAnimationFrame(loopFn);
    }
    function stopLoop() { running = false; cancelAnimationFrame(raf); raf = 0; }

    // ---------- API BrainRenderer ----------
    R.mount = function (el) {
      host = el;
      host.classList.add("planet-stage");
      glCv = document.createElement("canvas"); glCv.className = "planet-gl"; glCv.setAttribute("aria-hidden", "true");
      ovCv = document.createElement("canvas"); ovCv.className = "planet-ov"; ovCv.setAttribute("aria-hidden", "true");
      tip = document.createElement("div"); tip.className = "planet-tip"; tip.hidden = true; tip.setAttribute("role", "status");
      host.appendChild(glCv); host.appendChild(ovCv); host.appendChild(tip);
      ctx2 = ovCv.getContext("2d");
      on(ovCv, "pointermove", onMove);
      on(ovCv, "pointerdown", onDown);
      on(ovCv, "pointerup", onUp);
      on(ovCv, "pointercancel", onCancel);
      on(ovCv, "pointerleave", onLeave);
      on(ovCv, "dblclick", onDbl);
      on(ovCv, "wheel", onWheel, { passive: false });
      // Safari iOS phớt lờ user-scalable=no: chụm trên quả cầu sẽ phóng CẢ TRANG thay vì quả
      // cầu. touch-action:none (style.css) lo phần lớn trình duyệt; gesture* là riêng của WebKit.
      on(ovCv, "gesturestart", function (e) { e.preventDefault(); }, { passive: false });
      on(ovCv, "gesturechange", function (e) { e.preventDefault(); }, { passive: false });
      on(glCv, "webglcontextlost", onLost);
      on(glCv, "webglcontextrestored", onRestored);
      on(document, "visibilitychange", onVis);
      on(window, "keydown", function (e) { if (e.key === "Escape" && bhv.target) openBlackHole(false); });
      if (reducedMQ) {
        if (reducedMQ.addEventListener) on(reducedMQ, "change", onMotionPref);
      }
      if (window.ResizeObserver) { ro = new ResizeObserver(function () { resize(); }); ro.observe(host); }
      else on(window, "resize", resize);
      applyProfile(pickProfile());
      startLoop();
    };
    R.resize = resize;
    R.setJoyceState = function (s) {
      s = String(s || "READY").toUpperCase();
      if (STATES.indexOf(s) < 0) s = "READY";
      if (s !== state) { state = s; stateAt = performance.now(); }
    };
    R.setAudioAmplitude = function (v) { amp = clamp(+v || 0, 0, 1); };
    R.setProjects = function (list) { projects = Array.isArray(list) ? list.slice() : []; syncSats(); };
    R.setQuality = function (p) {
      requested = /^(high|balanced|safe|reduced)$/.test(p) ? p : null;
      try { if (requested) localStorage.setItem(QKEY, requested); else localStorage.removeItem(QKEY); } catch (e) {}
      applyProfile(pickProfile());
    };
    R.pause = function () { paused = true; stopLoop(); if (tip) tip.hidden = true; };
    R.resume = function () { paused = false; if (!document.hidden) startLoop(); resize(); };
    R.destroy = function () {
      if (destroyed) return;
      destroyed = true;
      stopLoop();
      clearTimeout(clickTimer);
      listeners.forEach(function (l) { try { l[0].removeEventListener(l[1], l[2], l[3]); } catch (e) {} });
      listeners = [];
      if (ro) { ro.disconnect(); ro = null; }
      if (gl) {
        var lose = gl.getExtension("WEBGL_lose_context");
        freeGL();
        try { if (lose) lose.loseContext(); } catch (e) {}
      }
      [glCv, ovCv, tip].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
      if (host) { host.classList.remove("planet-stage"); delete host.dataset.quality; }
      host = glCv = ovCv = tip = ctx2 = null;
      sats = []; projects = []; particles = []; swirl = []; glyphs = []; sun = moon = null;
      cells = []; splashes = []; streaks = []; bolts = []; hot = []; torn.g = null; torn.parts = []; pts = {}; pinch = null;
    };
    // Phần mở rộng ngoài interface tối thiểu - hud.js cần.
    R.setInCall = function (v) { inCall = !!v; };
    R.quality = function () { return profile; };
    R.state = function () { return state; };
    R.planetGeom = function () { return { cx: geo.cx, cy: geo.cy, R: geo.R, callK: callK }; };
    R.moonInfo = function () { return { phase: moonPh.phase, illum: moonPh.illum, key: MOON_KEYS[moonPhaseKey(moonPh.phase)] }; };
    // Thời tiết kinh doanh (hud.js đọc /business-weather): mây, mưa, sét, bão trên Việt Nam.
    R.setWeather = function (key) {
      if (!WX[key]) key = "nang_nhe";
      wx.key = key;
      wx.tgt = WX[key].slice();
      var st = (window.JoyceVNGeo && window.JoyceVNGeo.studio) || { lat: 20.88, lon: 106.59 };
      if (key === "loc_xoay") { wx.center = geoVec(st.lat, st.lon); wx.sigma = 0.07; }
      else { wx.center = geoVec(15.6, 111.6); wx.sigma = 0.2; }      // bão ngoài Biển Đông
    };
    // Đang nạp dữ liệu (hud.js đọc /brain/nap-status): { active, items: [tên file] }.
    R.setIngest = function (st) {
      ing.on = !!(st && st.active);
      if (st && Array.isArray(st.items) && st.items.length) ing.items = st.items.slice(0, 8);
    };
    // Bầu trời tri thức (hud.js đọc /knowledge/sky): {scope, brains, bodies, counts}.
    R.setKnowledge = setKnowledge;
    // Tia tri thức khi hỏi Joyce (hud.js đổi khung tool_call của lượt chat thành các pha này).
    R.traceTurn = traceTurn;
    R.traceInfo = function () {
      return { on: tr.on, answered: !!tr.tAns, threads: tr.threads.map(function (x) { return x.kind + ":" + (x.k ? x.k.b.id : x.id || x.label); }),
               used: tr.used.length };
    };
    // Nhìn sâu vào hố đen (bấm giữa hố đen, hoặc gọi thẳng). Esc / bấm bất kỳ đâu để ra.
    R.openBlackHole = function (v) { openBlackHole(v !== false); };
    R.blackHoleView = function () {
      return { k: bhv.k, open: !!bhv.target, crystals: bhv.crys.length, booms: bhv.booms.length, waiting: bhv.names.length };
    };
    // Big Bang khi tìm kiếm (hud.js đọc /knowledge/search): {q, hits, total}; null = thu về.
    R.focusKnowledge = focusKnowledge;
    R.highlightKnowledge = function (id) { know.hl = id || null; };
    R.knowledgeFocus = function () {
      return foc ? { q: foc.q, n: foc.items.length, more: foc.more.length, total: foc.total,
                     closing: foc.closing, lite: foc.lite, t: (performance.now() - foc.t0) / 1000 } : null;
    };
    R.knowledgeInfo = function () {
      return { stars: know.stars.length, orbit: know.orbit.length, debris: know.debris.length,
               drawn: know.hits.length, scope: know.scope, counts: know.counts,
               hover: know.hover ? know.hover.b.id : null };
    };
    R.zoom = function (z) { if (z != null) { cam.tzoom = clamp(+z || 1, ZMIN, ZMAX); cam.zoom = cam.tzoom; } return cam.zoom; };
    // Đích camera (zoom/xoay đang hướng tới, trước khi nội suy mềm) - cho test cử chỉ cảm ứng.
    R.camera = function () { return { zoom: cam.tzoom, yaw: cam.tyaw, pitch: cam.tpitch }; };
    // Ô bão, tia sét, vòi rồng đang sống (toạ độ địa lý) - cho test hiệu ứng thời tiết.
    R.storm = function () {
      return { cells: cells.map(function (q) { return { id: q.id, g: q.g.slice(), k: q.k, sig: q.sig }; }),
               bolts: bolts.map(function (b) { return b.g.slice(); }),
               tornado: torn.g ? { g: torn.g.slice(), sz: torn.sz, hk: torn.hk, ht: torn.ht } : null,
               wind: streaks.filter(function (q) { return q.gh; }).map(function (q) { return { g: q.gh.slice(), a: q.a, b: q.b }; }),
               volcano: fx.eruption > 0.01 && volc.rivers ? { g: VOLC_G.slice(), rivers: volc.rivers.length,
                 longest: Math.max.apply(null, volc.rivers.map(function (r) { return r.pts.length; })) * 0.028,
                 shown: volc.rivers.reduce(function (a, r) { return a + clamp(Math.floor(volc.front - r.start), 0, r.pts.length); }, 0),
                 front: volc.front, plume: volc.plume.map(function (p) { return p.g.slice(); }),
                 tips: volc.rivers.filter(function (r) { return volc.front - r.start > 0 && volc.front - r.start < r.pts.length; })
                   .map(function (r) { return r.pts[Math.floor(volc.front - r.start)].slice(); }) } : null };
    };
    return R;
  }

  window.JoycePlanet = {
    FLAG: FLAG,
    enabled: flagOn,
    setEnabled: function (on) {
      setFlag(on);
      try { window.dispatchEvent(new Event("joyce:planet-flag")); } catch (e) {}
    },
    supportsWebGL2: function () {
      try { var c = document.createElement("canvas"); var g = c.getContext("webgl2"); var ok = !!g;
        if (g) { var x = g.getExtension("WEBGL_lose_context"); if (x) x.loseContext(); } return ok; } catch (e) { return false; }
    },
    create: create,
    STATES: STATES.slice(),
    moonPhase: moonPhase,
    moonPhaseKey: moonPhaseKey,
    MOON_KEYS: MOON_KEYS,
    // Hàm thiên văn - lộ ra cho test (tests/js/test_planet_astro.js) và để soi khi gỡ lỗi.
    astro: { sunGeo: sunGeo, moonGeo: moonGeo, geoVec: geoVec, viewMat: viewMat, toView: toView, WX: WX },
    // Giao diện tùy biến (Cài đặt -> Giao diện Joyce -> Quả tinh cầu). Bảng trả ra là BẢN SAO:
    // trang Cài đặt đọc khoảng giá trị / bảng màu / cảnh từ đây chứ không khai lại lần hai.
    LOOK_DEFAULT: lookDefault(),
    LOOK_NUM: JSON.parse(JSON.stringify(LOOK_NUM)),
    LOOK_BOOL: JSON.parse(JSON.stringify(LOOK_BOOL)),
    LOOK_ENUM: JSON.parse(JSON.stringify(LOOK_ENUM)),
    PALETTES: JSON.parse(JSON.stringify(PALETTES)),
    SCENES: JSON.parse(JSON.stringify(SCENES)),
    normLook: normLook,
    getLook: getLook,
    setLook: setLook,
    // Bản của máy chủ thắng bản nhớ tạm trên máy (gọi lúc khởi động và khi mở tab Cài đặt).
    hydrateLook: function (o) { return setLook(o, { replace: true }); },
    lookInfo: function () { return JSON.parse(JSON.stringify(LD)); },
    // Bề mặt Mặt Trăng (biển tối hình chú Cuội ngồi gốc cây đa) - lộ ra cho test.
    moonSurface: { mariaAt: mariaAt, build: buildMoonMap, pixels: moonPixels, MARIA: MARIA },
  };
})();
