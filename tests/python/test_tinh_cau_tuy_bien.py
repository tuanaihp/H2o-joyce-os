"""Lưu giao diện tinh cầu xong F5 có còn không (POST /settings section=dashboard, khoá planet).

    python tests/python/test_tinh_cau_tuy_bien.py

Tab Cài đặt -> Giao diện Joyce -> Quả tinh cầu (0.65.38) ghi vào settings.dashboard.planet. Nhánh
dashboard của POST /settings dùng ALLOWLIST TỪNG KHOÁ (y như pet): khoá nào renderer có mà máy
chủ không biết thì người dùng kéo thanh trượt, thấy đổi, F5 là mất - không lỗi, không log
(test_luu_cai_dat_giong.py kể đúng vụ đó). Ba lớp canh:
  1. Vòng tròn THẬT qua TestClient: POST rồi đọc lại settings, đủ mọi khoá.
  2. Rác không lọt: số kẹp khoảng, màu chỉ "#rrggbb", bool phải là bool, lựa chọn trong danh sách.
  3. Bảng khoá + khoảng giá trị của máy chủ (main._PLANET_*) khớp TỪNG DÒNG với LOOK_* trong
     dashboard/brain-planet.js.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import json
import os
import re
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-tinhcau-")

from fastapi.testclient import TestClient   # noqa: E402
import config as c   # noqa: E402
import main          # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


# base_url phải là host được phép (rào chống DNS-rebinding trả 403 cho "testserver").
cl = TestClient(main.app, base_url="http://127.0.0.1:7777")


def luu(planet):
    return cl.post("/settings", data={"section": "dashboard", "data": json.dumps({"planet": planet})})


def doc() -> dict:
    return (c.read_settings().get("dashboard") or {}).get("planet") or {}


# ---- 1. Vòng tròn thật ----
DAY_DU = {
    "sunPower": 1.35, "sunSize": 1.3, "moonFull": 0.5, "moonGlow": 1.8, "moonSize": 1.25,
    "surface": 0.9, "atmo": 1.4, "clouds": 0.85, "cloudDark": 0.6, "coreVis": 1.7, "coreGlow": 0.4,
    "sunColor": "#ff7a3d", "seaColor": "#123abc", "rimColor": "#ffe14d",
    "rain": True, "lightning": True, "wind": False, "tornado": True, "eruption": True, "orbits": False,
    "moonMode": "manual", "palette": "custom",
}
r = luu(DAY_DU)
check("POST /settings section=dashboard planet trả ok", r.status_code == 200 and r.json().get("ok") is True)
pl = doc()
for k, want in DAY_DU.items():
    check(f"lưu rồi đọc lại giữ được '{k}'", pl.get(k) == want)
g = cl.get("/settings").json()
check("GET /settings trả dashboard.planet cho trình duyệt", (g.get("dashboard") or {}).get("planet", {}).get("palette") == "custom")

# ---- 2. Rác không lọt, bản cũ không bị xoá ----
luu({"sunPower": 99, "moonFull": -5, "clouds": "0.5", "coreVis": True, "sunColor": "red",
     "rain": "false", "palette": "khong-co", "moonMode": "abc", "atmo": float("nan"), "xau": "<script>"})
pl = doc()
check("số vượt trần bị kẹp", pl.get("sunPower") == 2 and pl.get("moonFull") == 0)
check("số dạng chuỗi bị bỏ (giữ bản cũ)", pl.get("clouds") == 0.85)
check("bool không được coi là số", pl.get("coreVis") == 1.7)
check("NaN bị bỏ", pl.get("atmo") == 1.4)
check("màu sai định dạng bị bỏ", pl.get("sunColor") == "#ff7a3d")
check('bool dạng chuỗi ("false") bị bỏ', pl.get("rain") is True)
check("lựa chọn lạ bị bỏ", pl.get("palette") == "custom" and pl.get("moonMode") == "manual")
check("khoá lạ không lọt vào settings.json", "xau" not in pl)
luu({"sunColor": "#ABCDEF"})
check("màu viết hoa được nhận và hạ về chữ thường", doc().get("sunColor") == "#abcdef")
luu("khong-phai-object")
check("planet không phải object: không vỡ, giữ nguyên bản cũ", doc().get("palette") == "custom")

# Lưu pet không được xoá mất giao diện tinh cầu (cùng nhánh dashboard).
cl.post("/settings", data={"section": "dashboard", "data": json.dumps({"pet": {"shape": "star"}})})
check("lưu linh vật không đụng giao diện tinh cầu", doc().get("palette") == "custom")

# ---- 3. Hai bảng khoá khớp nhau ----
JS = (ROOT / "dashboard" / "brain-planet.js").read_text(encoding="utf-8")


def khoi(ten):
    m = re.search(r"var " + ten + r" = \{(.*?)\n  \};", JS, re.S) or re.search(r"var " + ten + r" = \{(.*?)\};", JS, re.S)
    return m.group(1) if m else ""


so_js = {k: (float(a), float(b)) for k, a, b, _ in re.findall(r"(\w+): \[([\d.]+), ([\d.]+), ([\d.]+)\]", khoi("LOOK_NUM"))}
check("đọc được bảng LOOK_NUM của renderer", len(so_js) >= 10)
check("khoá số: máy chủ = renderer", set(so_js) == set(main._PLANET_SO))
for k, (lo, hi) in so_js.items():
    check(f"khoảng của '{k}' khớp", tuple(map(float, main._PLANET_SO.get(k, (None, None)))) == (lo, hi))
mau_js = set(re.findall(r"(\w+): \"#[0-9a-f]{6}\"", khoi("LOOK_COLOR")))
check("khoá màu: máy chủ = renderer", mau_js == set(main._PLANET_MAU))
bat_js = set(re.findall(r"(\w+): (?:true|false)", khoi("LOOK_BOOL")))
check("khoá bật/tắt: máy chủ = renderer", bat_js == set(main._PLANET_BAT))
pal_js = re.findall(r"^\s{4}(\w+):\s+\{ deep:", JS, re.M)
check("concept màu: máy chủ = renderer (+ custom)", set(pal_js) | {"custom"} == set(main._PLANET_CHON["palette"]))
check("chế độ trăng: máy chủ = renderer", '"auto", "manual"' in JS and set(main._PLANET_CHON["moonMode"]) == {"auto", "manual"})

if _fails:
    print(f"\n{len(_fails)} FAIL")
    raise SystemExit(1)
print("\nTất cả xanh.")
