// Trái Đất H2O (brain-planet.js): Mặt Trời / Mặt Trăng theo GIỜ THẬT + khung nhìn địa lý.
// Chạy: node tests/js/test_planet_astro.js
//
// Kiểm bằng mốc thiên văn đã biết, không bằng cảm giác:
//   - 12:00 trưa giờ Việt Nam (05:00 UTC) ngày 06/10: giờ Mặt Trời nhanh hơn đồng hồ ~11,7
//     phút (phương trình thời gian), nên điểm đứng bóng ở (12 - 5,195) x 15 = ~102,1 độ Đông,
//     xích vĩ ~ -5 độ.
//   - Xuân phân 20/03/2026 14:46 UTC: xích vĩ ~ 0.
//   - Hạ chí 21/06/2026: xích vĩ ~ +23,4.
//   - Khung nhìn: điểm đặt giữa đĩa phải ra (0,0,1); phía Đông nằm bên PHẢI; Bắc hướng LÊN.
//   - Nửa đêm giờ VN, Mặt Trời ở SAU quả cầu khi nhìn từ Việt Nam (z < 0); trưa thì z > 0.
const fs = require("fs");
const path = require("path");

global.window = {};
global.document = { documentElement: { getAttribute: () => null } };
eval(fs.readFileSync(path.join(__dirname, "../../dashboard/brain-planet.js"), "utf8"));
const A = window.JoycePlanet.astro;

const fails = [];
const check = (name, cond, extra) => { console.log((cond ? "ok   " : "FAIL ") + name + (extra ? "  " + extra : "")); if (!cond) fails.push(name); };
const latLon = (v) => [Math.asin(v[1]) * 180 / Math.PI, Math.atan2(v[0], v[2]) * 180 / Math.PI];

let [la, lo] = latLon(A.sunGeo(new Date(Date.UTC(2026, 9, 6, 5, 0))));
check("trưa VN 06/10: Mặt Trời đứng bóng ~102,1°Đ", Math.abs(lo - 102.1) < 0.5, lo.toFixed(2));
check("trưa VN 06/10: xích vĩ ~ -5°", Math.abs(la + 5.2) < 0.8, la.toFixed(2));
[la] = latLon(A.sunGeo(new Date(Date.UTC(2026, 2, 20, 14, 46))));
check("xuân phân: xích vĩ ~ 0", Math.abs(la) < 0.3, la.toFixed(2));
[la] = latLon(A.sunGeo(new Date(Date.UTC(2026, 5, 21, 8, 0))));
check("hạ chí: xích vĩ ~ +23,4", Math.abs(la - 23.44) < 0.3, la.toFixed(2));

const G = A.viewMat(16, 106.5);
const c = A.toView(G, A.geoVec(16, 106.5));
check("điểm giữa đĩa = (0,0,1)", Math.abs(c[0]) < 1e-9 && Math.abs(c[1]) < 1e-9 && Math.abs(c[2] - 1) < 1e-9);
const east = A.toView(G, A.geoVec(16, 120));
check("phía Đông nằm bên phải", east[0] > 0.1);
const north = A.toView(G, A.geoVec(30, 106.5));
check("phía Bắc hướng lên", north[1] > 0.1);

const noon = A.toView(G, A.sunGeo(new Date(Date.UTC(2026, 9, 6, 5, 0))));
const midnight = A.toView(G, A.sunGeo(new Date(Date.UTC(2026, 9, 6, 17, 0))));
check("trưa VN: Mặt Trời phía trước quả cầu (z > 0,8)", noon[2] > 0.8, noon[2].toFixed(2));
check("nửa đêm VN: Mặt Trời sau quả cầu (z < -0,8)", midnight[2] < -0.8, midnight[2].toFixed(2));

// Mặt Trăng: trăng tròn 07/10/2025 03:47 UTC - đối diện Mặt Trời (góc ~180°).
const d = new Date(Date.UTC(2025, 9, 7, 3, 47));
const s = A.sunGeo(d), m = A.moonGeo(d);
const ang = Math.acos(s[0] * m[0] + s[1] * m[1] + s[2] * m[2]) * 180 / Math.PI;
check("trăng tròn: Mặt Trăng đối diện Mặt Trời (>170°)", ang > 170, ang.toFixed(1));

["nang", "nang_nhe", "nhieu_may", "mua", "giong", "bao", "loc_xoay"].forEach((k) =>
  check("có hiệu ứng thời tiết " + k, Array.isArray(A.WX[k]) && A.WX[k].length === 4));

console.log();
if (fails.length) { console.log(fails.length + " FAIL: " + fails.join(", ")); process.exit(1); }
console.log("TẤT CẢ PASS");
