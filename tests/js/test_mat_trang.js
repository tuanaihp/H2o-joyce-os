/* Bề mặt Mặt Trăng: chú Cuội ngồi gốc cây đa + phần tối lồi lõm dưới ánh đất (0.65.40).

       node tests/js/test_mat_trang.js

   Chủ repo yêu cầu 2026-10-07: "phần đen của mặt trăng sẽ là hình ảnh lồi lõm của bề mặt mặt
   trăng, giống như hình ảnh mô phỏng chú Cuội chị Hằng Nga của Việt Nam". Trước bản này phần
   tối là một đĩa xanh đen phẳng, phần sáng có năm chấm tròn làm "miệng hố".

   Kiểm trên hàm THUẦN của brain-planet.js (dựng bản đồ + chiếu sáng không cần canvas):
     - Biển tối xếp thành tán cây đa, thân, rễ, và dáng chú Cuội ngồi dưới gốc.
     - Phần tối KHÔNG đen đặc: ánh đất soi ra bề mặt, biển tối vẫn tối hơn cao nguyên, hố nổi khối.
     - Phần sáng quay đúng về phía nắng theo pha; mặt trăng luôn đứng thẳng (không xoay theo nắng).
     - Dựng bản đồ đủ nhanh, và dựng lúc trình duyệt rảnh chứ không chặn khung hình. */
const fs = require("fs");
const path = require("path");

const PLANET = fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", "brain-planet.js"), "utf8");
const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!cond) fails.push(name);
}
// Nạp thẳng vào ngữ cảnh chính (như test_planet_astro.js), KHÔNG qua vm: trong vm mỗi lần gọi
// Math.* đi qua lớp chặn của sandbox, chậm hơn ~12 lần, nên số đo thời gian sẽ sai.
global.window = {};
global.document = { documentElement: { getAttribute: () => null } };
(0, eval)(PLANET);
const S = window.JoycePlanet.moonSurface;
check("JoycePlanet.moonSurface có mariaAt/build/pixels", S && ["mariaAt", "build", "pixels"].every((f) => typeof S[f] === "function"));

// ---- 1. Hình chú Cuội ngồi gốc cây đa ----
const M = (u, v) => S.mariaAt(u, v, null);
check("tán cây đa (giữa, trên)", M(-0.05, -0.5) > 0.8 && M(0.25, -0.45) > 0.8 && M(-0.32, -0.4) > 0.8);
check("thân cây (giữa)", M(0.08, 0.0) > 0.8 && M(0.1, 0.4) > 0.8);
check("rễ toả hai bên gốc", M(-0.08, 0.63) > 0.6 && M(0.3, 0.63) > 0.6);
check("chú Cuội: đầu, lưng, gối, chân", M(-0.13, 0.19) > 0.8 && M(-0.1, 0.36) > 0.8 && M(-0.27, 0.37) > 0.8 && M(-0.31, 0.52) > 0.7);
check("Cuội ngồi BÊN TRÁI gốc cây, tách khỏi thân ở ngang đầu", M(-0.03, 0.19) < 0.3);
check("cao nguyên sáng quanh hình (không phủ kín đĩa)", M(0.75, 0.55) < 0.1 && M(-0.6, 0.75) < 0.1 && M(0.0, 0.92) < 0.1);
check("có dáng Mặt Trăng thật: biển Nguy Hiểm ở mép phải", M(0.7, -0.25) > 0.7);

const t0 = Date.now();
const map = S.build();
const tBuild = Date.now() - t0;
check("dựng bản đồ bề mặt < 600ms (máy chậm nhất vẫn chịu được, chạy lúc rảnh)", tBuild < 600, tBuild + "ms");
const map2 = S.build();
let same = true;
for (let i = 0; i < map.A.length; i += 97) if (map.A[i] !== map2.A[i]) { same = false; break; }
check("bản đồ cố định (seed cố định, lần nào cũng như nhau)", same);
const at = (arr, u, v) => arr[Math.floor((v + 1) / 2 * map.N) * map.N + Math.floor((u + 1) / 2 * map.N)];
check("biển tối có độ phản xạ thấp hơn cao nguyên rõ rệt", at(map.A, 0.75, 0.55) - at(map.A, -0.05, -0.5) > 0.2);
let bumps = 0;
for (let i = 0; i < map.GX.length; i++) if (Math.abs(map.GX[i]) > 0.3) bumps++;
check("bề mặt có độ dốc lồi lõm (vành, lòng hố)", bumps > 500, bumps + " điểm dốc");

// ---- 2. Chiếu sáng ----
const COL = [214, 224, 245], RES = 128;
const lum = (px, u, v) => {
  const x = Math.round((u + 1) / 2 * RES - 0.5), y = Math.round((v + 1) / 2 * RES - 0.5), o = (y * RES + x) * 4;
  return (px[o] + px[o + 1] + px[o + 2]) / 3;
};
const nm = S.pixels(RES, 0.02, 0, 1, COL);
check("trăng non: phần tối KHÔNG đen đặc (ánh đất soi ra bề mặt)", lum(nm, 0.75, 0.55) > 18, lum(nm, 0.75, 0.55).toFixed(0));
check("trăng non: biển tối (hình Cuội, cây đa) vẫn đọc ra được trong phần tối",
  lum(nm, 0.75, 0.55) - lum(nm, -0.05, -0.5) > 6 && lum(nm, 0.75, 0.55) - lum(nm, -0.13, 0.19) > 5);
let lo = 255, hi = 0;
for (let y = 30; y < 98; y++) for (let x = 30; x < 98; x++) { const o = (y * RES + x) * 4; lo = Math.min(lo, nm[o]); hi = Math.max(hi, nm[o]); }
check("trăng non: phần tối có chênh sáng tối (lồi lõm), không phải màu phẳng", hi - lo > 25, (hi - lo) + "");
const fm = S.pixels(RES, 0.5, 0, 1, COL);
check("trăng tròn sáng đều tới gần mép (không tối dần như quả bóng)", lum(fm, 0.75, 0.55) > 150 && lum(fm, -0.6, 0.75) > 150);
check("trăng tròn sáng hơn hẳn phần tối lúc trăng non", lum(fm, 0.75, 0.55) > 2.5 * lum(nm, 0.75, 0.55));
const wax = S.pixels(RES, 0.15, 0, 1, COL), wan = S.pixels(RES, 0.85, 0, 1, COL);
check("trăng đầu tháng sáng bên PHẢI (bán cầu Bắc)", lum(wax, 0.85, -0.2) > 2 * lum(wax, -0.85, -0.2));
check("trăng cuối tháng sáng bên TRÁI", lum(wan, -0.85, -0.2) > 2 * lum(wan, 0.85, -0.2));
const down = S.pixels(RES, 0.25, Math.PI / 2, 1, COL);
check("nắng chiếu từ dưới -> nửa DƯỚI sáng (phần sáng xoay theo hướng nắng)", lum(down, 0.3, 0.75) > 2 * lum(down, 0.3, -0.75));
const nmRot = S.pixels(RES, 0.02, 1.3, 1, COL);
check("mặt trăng luôn đứng thẳng: hình Cuội không xoay theo hướng nắng", Math.abs(lum(nmRot, -0.13, 0.19) - lum(nm, -0.13, 0.19)) < 4);
const dim = S.pixels(RES, 0.5, 0, 0.2, COL), bright = S.pixels(RES, 0.5, 0, 2, COL);
check("thanh Độ sáng trăng: mờ < gốc < rực", lum(dim, 0.6, 0.6) < lum(fm, 0.6, 0.6) && lum(bright, 0.6, 0.6) > lum(fm, 0.6, 0.6));
check("ngoài đĩa trong suốt", nm[3] === 0 && nm[(RES * RES - 1) * 4 + 3] === 0);
const t1 = Date.now();
S.pixels(320, 0.3, 0.4, 1, COL);
const tPx = Date.now() - t1;
check("chiếu sáng đĩa 320px < 80ms (chỉ chạy khi pha/hướng/cỡ đổi)", tPx < 80, tPx + "ms");

// ---- 3. Nối vào renderer ----
check("drawMoonDisc dùng ảnh bề mặt, có đường lui đĩa phẳng", /var img = moonImage\(res, p, rot \|\| 0, gl, col\);/.test(PLANET) && /Đường lui/.test(PLANET));
check("ảnh trăng được giữ giữa các khung (bộ đệm theo cỡ/pha/hướng/độ sáng/màu)", /if \(moonCv && key === moonKey\) return moonCv;/.test(PLANET));
check("dựng bản đồ lúc trình duyệt rảnh, không chặn khung hình", /requestIdleCallback\(run/.test(PLANET) && /if \(!moonMap\) \{ scheduleMoonMap\(\); return null; \}/.test(PLANET));
check("ảnh trăng giới hạn 320px (phóng to không làm nặng)", /clamp\(Math\.ceil\(2 \* r \* dprOv \/ 16\) \* 16, 32, 320\)/.test(PLANET));

if (fails.length) {
  console.log("\n" + fails.length + " FAIL");
  process.exit(1);
}
console.log("\nTất cả xanh.");
