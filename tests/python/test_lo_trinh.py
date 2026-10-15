"""Tab Lộ trình (server/lo_trinh.py): mở bài theo ngày, chấm tự động, đề xuất theo luật, phân quyền.

    python tests/run.py lo_trinh

Dựng brain TẠM và app FastAPI riêng với phụ thuộc giả, không import main, không đụng brains/ thật.
Spec: docs/dev/2026-10-lo-trinh-hoc-vien-design.md.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path
import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import lo_trinh  # noqa: E402

BAI_CO_KIEM_TRA = """---
type: wiki
status: active
cap_do: hoc-viec
ngay: {ngay}
tieu_de: "Ngày {ngay}: bài thử"
thoi_luong_phut: 10
kiem_tra:
  - hoi: "Câu một?"
    lua_chon: ["A", "B", "C"]
    dap_an: 1
    giai_thich: "Đáp án là B."
  - hoi: "Câu hai?"
    lua_chon: ["X", "Y"]
    dap_an: 0
    giai_thich: "Đáp án là X."
---

# Bài ngày {ngay}

Nội dung.
"""

BAI_KHONG_KIEM_TRA = """---
type: wiki
status: active
cap_do: hoc-viec
ngay: {ngay}
tieu_de: "Ngày {ngay}: thi"
loai_ngay: thi
---

# Thi
"""


def _brain(tmp_path, ngay_co_kt=(0, 1, 2), ngay_khong_kt=(3,)):
    d = tmp_path / "brains" / lo_trinh.BRAIN_GIAO_TRINH / "wiki" / "hoc-viec" / "cap-do" / "hoc-viec" / "bai-hoc"
    d.mkdir(parents=True)
    for n in ngay_co_kt:
        (d / f"ngay-{n:02d}.md").write_text(BAI_CO_KIEM_TRA.format(ngay=n), encoding="utf-8")
    for n in ngay_khong_kt:
        (d / f"ngay-{n:02d}.md").write_text(BAI_KHONG_KIEM_TRA.format(ngay=n), encoding="utf-8")
    (d / "nhap.md").write_text("---\nstatus: draft\nngay: 9\n---\n", encoding="utf-8")
    return tmp_path / "brains"


# ------------------------------------------------------------------ hàm thuần

def test_doc_bai_hoc_chi_lay_active_va_sap_theo_ngay(tmp_path):
    goc = _brain(tmp_path) / lo_trinh.BRAIN_GIAO_TRINH
    ds = lo_trinh.doc_bai_hoc(goc, "hoc-viec")
    assert [b["ngay"] for b in ds] == [0, 1, 2, 3]          # bản nháp ngày 9 bị bỏ
    assert len(ds[0]["kiem_tra"]) == 2 and ds[3]["kiem_tra"] == []
    assert ds[3]["loai"] == "thi"
    assert lo_trinh.doc_bai_hoc(goc, "khong-co-cap") == []


def test_cau_hoi_sai_dinh_dang_bi_bo_khong_lam_hong_bai(tmp_path):
    q = lo_trinh._chuan_cau_hoi([
        {"hoi": "ok", "lua_chon": ["a", "b"], "dap_an": 1},
        {"hoi": "đáp án ngoài khoảng", "lua_chon": ["a", "b"], "dap_an": 5},
        {"hoi": "một lựa chọn", "lua_chon": ["a"], "dap_an": 0},
        "không phải dict",
    ])
    assert [x["hoi"] for x in q] == ["ok"]


def test_thang_lo_trinh_dem_bai_tung_cap(tmp_path):
    goc = _brain(tmp_path) / lo_trinh.BRAIN_GIAO_TRINH
    thang = {c["ma"]: c for c in lo_trinh.thang_lo_trinh(goc)}
    assert thang["hoc-viec"]["so_bai"] == 4 and thang["hoc-viec"]["so_bai_kiem_tra"] == 3
    assert thang["chu-tich-hdqt"]["so_bai"] == 0
    assert len(thang) == len(lo_trinh.CAP_DO)


def test_ngay_dao_tao_bo_qua_ngay_nghi():
    assert lo_trinh.ngay_dao_tao("2026-10-10", [], "2026-10-09") == -1
    assert lo_trinh.ngay_dao_tao("2026-10-10", [], "2026-10-10") == 0
    assert lo_trinh.ngay_dao_tao("2026-10-10", [], "2026-10-13") == 3
    # Nghỉ ngày 11: ngày 13 chỉ là ngày đào tạo thứ 2, lịch tự lùi.
    assert lo_trinh.ngay_dao_tao("2026-10-10", ["2026-10-11"], "2026-10-13") == 2
    lich = lo_trinh.lich_ngay("2026-10-10", ["2026-10-11"], 2)
    assert lich == {0: "2026-10-10", 1: "2026-10-12", 2: "2026-10-13"}


def test_cham_bai_so_dap_an():
    cau = [{"dap_an": 1}, {"dap_an": 0}, {"dap_an": 2}]
    kq = lo_trinh.cham_bai(cau, [1, 1, 2])
    assert (kq["dung"], kq["tong"], kq["diem"]) == (2, 3, 67)
    assert lo_trinh.cham_bai(cau, None)["diem"] == 0           # không trả lời = sai hết
    assert lo_trinh.cham_bai(cau, ["x", 0])["chi_tiet"][0]["chon"] is None


def test_kien_thuc_tinh_bo_bai_cho_ngay_da_qua():
    bai = [{"ngay": n, "kiem_tra": [1]} for n in (0, 1, 2)]
    hv = {"nop": {"0": [{"diem": 50}, {"diem": 100}]}}
    kt = lo_trinh.kien_thuc(hv, bai, 2)
    # Ngày 0: 100 (lần cao nhất). Ngày 1 đã qua mà chưa nộp: bỏ bài, tính 0. Ngày 2 là hôm nay: chưa tính.
    assert kt == {"trung_binh": 50, "so_bai": 2, "bo_bai": [1]}


def _hv_du(rubric=85, mp="dat", gate="dat", ks=(80, 80, 80), nop=100):
    return {
        "rubric": {"diem": dict(zip([m for m, _, _ in lo_trinh.RUBRIC],
                                    _chia_rubric(rubric)))},
        "must_pass": {m: mp for m, _ in lo_trinh.MUST_PASS},
        "gate1": {"ket_qua": gate},
        "khao_sat": {"1": dict(zip(("thai_do", "tuan_thu", "hoa_nhap"), ks)),
                     "2": dict(zip(("thai_do", "tuan_thu", "hoa_nhap"), ks))},
        "nop": {"0": [{"diem": nop}]},
    }


def _chia_rubric(tong):
    toi_da = [n for _, _, n in lo_trinh.RUBRIC]
    out, con = [], tong
    for n in toi_da:
        v = min(n, con)
        out.append(v)
        con -= v
    return out


BAI1 = [{"ngay": 0, "kiem_tra": [1]}]


def test_de_xuat_dat_khi_du_moi_dieu_kien():
    assert lo_trinh.de_xuat(_hv_du(), BAI1, 0) == {"ket_qua": "dat", "ly_do": []}


def test_de_xuat_must_pass_truot_luon_chuyen_truong_phong():
    dx = lo_trinh.de_xuat(_hv_du(rubric=100, mp="truot"), BAI1, 0)
    assert dx["ket_qua"] == "truong_phong_xem_xet" and dx["ly_do"][0]["ma"] == "mp_truot"


def test_de_xuat_nguong_rubric_cua_brain():
    assert lo_trinh.de_xuat(_hv_du(rubric=60), BAI1, 0)["ket_qua"] == "truong_phong_xem_xet"
    dx = lo_trinh.de_xuat(_hv_du(rubric=70), BAI1, 0)
    assert dx["ket_qua"] == "can_bo_sung" and dx["ly_do"][0] == {"ma": "rubric_65_79", "diem": 70}


def test_de_xuat_chua_du_du_lieu_khi_thieu_rubric():
    hv = _hv_du()
    hv["rubric"] = {"diem": {"ky_thuat": 30}}
    assert lo_trinh.de_xuat(hv, BAI1, 0)["ket_qua"] == "chua_du_du_lieu"


def test_de_xuat_kien_thuc_va_khao_sat():
    dx = lo_trinh.de_xuat(_hv_du(nop=40, ks=(60, 60, 60)), BAI1, 0)
    ma = {x["ma"] for x in dx["ly_do"]}
    assert dx["ket_qua"] == "can_bo_sung"
    assert {"kien_thuc_duoi_70", "khao_sat_duoi_70"} <= ma


def test_khao_sat_di_xuong_bi_ghi_nhan():
    ks = lo_trinh.danh_gia_khao_sat({"1": {"thai_do": 90, "tuan_thu": 90, "hoa_nhap": 90},
                                     "2": {"thai_do": 80, "tuan_thu": 80, "hoa_nhap": 40}})
    assert ks["khong_giam"] is False and ks["khong_duoi_san"] is False and ks["dat_nguong"] is True


# ------------------------------------------------------------------ endpoint và phân quyền

ADMIN = {}
TP_MAKEUP = {"id": "st_tp_000001", "ten": "Trưởng phòng", "role": "truong_phong", "phong_ban": ["makeup"]}
TP_KHAC = {"id": "st_tp_000002", "ten": "TP phòng khác", "role": "truong_phong", "phong_ban": ["sale"]}
MENTOR = {"id": "st_mt_000003", "ten": "Mentor", "role": "nhan_vien", "phong_ban": ["makeup"]}
HOC_VIEN = {"id": "st_hv_000004", "ten": "Học viên", "role": "hoc_viec", "phong_ban": ["makeup"]}
NGUOI = {s["id"]: s for s in (TP_MAKEUP, TP_KHAC, MENTOR, HOC_VIEN)}
CAP = {"truong_phong": "quan_ly", "nhan_vien": "nhan_vien", "hoc_viec": "hoc_viec"}


@pytest.fixture
def moi(tmp_path):
    brains = _brain(tmp_path)
    trang = {"ai": ADMIN, "hom_nay": "2026-10-10", "gio": 8, "gui": []}

    async def gui(chat, text):
        trang["gui"].append((chat, text))
        return True, ""

    deps = lo_trinh.LoTrinhDeps(
        brains_dir=lambda: str(brains),
        state_path=lambda: tmp_path / "state" / "lo_trinh.json",
        staff_of=lambda request: trang["ai"],
        staff_cap=lambda st: CAP.get(st.get("role"), "nhan_vien"),
        list_staff=lambda: list(NGUOI.values()),
        get_staff=lambda sid: NGUOI.get(sid),
        today=lambda: trang["hom_nay"],
        now_hour=lambda: trang["gio"],
        tg_send=gui,
    )
    app = FastAPI()
    lo_trinh.register(app, deps)
    return TestClient(app), trang, deps


def _kich_hoat(c, trang, ai=ADMIN, **them):
    trang["ai"] = ai
    body = {"staff_id": HOC_VIEN["id"], "cap_do": "hoc-viec", "ngay_bat_dau": "2026-10-10",
            "mentor_id": MENTOR["id"], **them}
    return c.post("/lo-trinh/kich-hoat", json=body)


def test_kich_hoat_quyen_theo_phong(moi):
    c, trang, _ = moi
    assert _kich_hoat(c, trang, ai=HOC_VIEN).status_code == 403
    assert _kich_hoat(c, trang, ai=MENTOR).status_code == 403
    assert _kich_hoat(c, trang, ai=TP_KHAC).json()["error"] == "khac_phong"
    r = _kich_hoat(c, trang, ai=TP_MAKEUP)
    assert r.json()["ok"] is True
    assert _kich_hoat(c, trang, ai=ADMIN).status_code == 409      # đang học cấp này rồi


def test_kich_hoat_tu_choi_cap_chua_co_bai_va_mentor_la_chinh_minh(moi):
    c, trang, _ = moi
    assert _kich_hoat(c, trang, cap_do="giam-doc").json()["error"] == "cap_chua_co_bai"
    assert _kich_hoat(c, trang, mentor_id=HOC_VIEN["id"]).json()["error"] == "mentor_sai"


def test_hoc_vien_chi_doc_bai_da_mo_va_khong_thay_dap_an(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["ai"] = HOC_VIEN
    tong = c.get("/lo-trinh").json()
    assert [x["id"] for x in tong["cua_toi"]] == [eid] and tong["hoc_vien"] == []
    assert tong["cua_toi"][0]["bai_hom_nay"]["ngay"] == 0
    assert c.get(f"/lo-trinh/bai/{eid}/1").json()["error"] == "chua_mo"
    b = c.get(f"/lo-trinh/bai/{eid}/0").json()
    assert b["ok"] and "dap_an" not in b["kiem_tra"][0] and b["nop_duoc"] is True
    # Học viên không xem được phần chấm của người khác chấm mình.
    ct = c.get(f"/lo-trinh/hoc-vien/{eid}").json()
    assert ct["ban_than"] is True and "rubric" not in ct and "de_xuat" not in ct


# Bài thử: câu 1 có 3 lựa chọn, đáp án gốc 1; câu 2 có 2 lựa chọn, đáp án gốc 0.
GOC = ((3, 1), (2, 0))


def _hien(eid, ngay, dung=(True, True)):
    """Vị trí ĐANG HIỆN cho học viên (đã xáo): đúng hoặc sai theo từng câu."""
    out = []
    for i, ((n, da), ok) in enumerate(zip(GOC, dung)):
        p = lo_trinh.hoan_vi(eid, ngay, i, n)
        out.append(p.index(da) if ok else p.index((da + 1) % n))
    return out


def test_nop_bai_cham_tu_dong_hai_luot_roi_lo_dap_an(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["ai"] = MENTOR
    assert c.post(f"/lo-trinh/bai/{eid}/0/nop", json={"tra_loi": _hien(eid, 0)}).json()["error"] == "chi_hoc_vien_nop"
    trang["ai"] = HOC_VIEN
    r1 = c.post(f"/lo-trinh/bai/{eid}/0/nop", json={"tra_loi": _hien(eid, 0, (False, True))}).json()
    assert r1["diem"] == 50 and r1["het_luot"] is False and "dap_an" not in r1["chi_tiet"][0]
    assert r1["chi_tiet"][0]["chon"] == _hien(eid, 0, (False, True))[0]     # trả lại đúng vị trí đang hiện
    r2 = c.post(f"/lo-trinh/bai/{eid}/0/nop", json={"tra_loi": _hien(eid, 0, (True, False))}).json()
    assert r2["diem"] == 50 and r2["het_luot"] is True
    assert r2["chi_tiet"][0]["dap_an"] == _hien(eid, 0)[0]
    assert c.post(f"/lo-trinh/bai/{eid}/0/nop", json={"tra_loi": _hien(eid, 0)}).json()["error"] == "het_luot"
    b = c.get(f"/lo-trinh/bai/{eid}/0").json()
    assert b["kiem_tra"][0]["dap_an"] == _hien(eid, 0)[0] and b["nop_duoc"] is False
    assert b["lan_cuoi"]["tra_loi"] == _hien(eid, 0, (True, False))      # lần cuối hiện đúng chỗ đã chọn


def test_lua_chon_duoc_xao_theo_hoc_vien_va_co_dinh(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["ai"] = HOC_VIEN
    a = c.get(f"/lo-trinh/bai/{eid}/0").json()["kiem_tra"][0]["lua_chon"]
    b = c.get(f"/lo-trinh/bai/{eid}/0").json()["kiem_tra"][0]["lua_chon"]
    assert a == b and sorted(a) == ["A", "B", "C"]                      # cố định, đủ lựa chọn
    # Học viên khác nhau thì thứ tự khác nhau ở ít nhất một số trường hợp: chọn cùng một chữ không qua được.
    thu_tu = {tuple(lo_trinh.hoan_vi(f"lt_{i:010x}", 0, 0, 4)) for i in range(30)}
    assert len(thu_tu) > 5


def test_dung_het_ngay_lan_dau_thi_khoa_nop(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["ai"] = HOC_VIEN
    r = c.post(f"/lo-trinh/bai/{eid}/0/nop", json={"tra_loi": _hien(eid, 0)}).json()
    assert r["diem"] == 100 and r["het_luot"] is True


def test_mentor_cham_duoc_hoc_vien_va_phong_khac_thi_khong(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["ai"] = HOC_VIEN
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/cham", json={"gate1": {"ket_qua": "dat"}}).status_code == 403
    trang["ai"] = TP_KHAC
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/cham", json={"gate1": {"ket_qua": "dat"}}).status_code == 403
    trang["ai"] = MENTOR
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/cham", json={"rubric": {"ky_thuat": 99}}).json()["error"] == "rubric_sai"
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/cham", json={"khao_sat": {"tuan": 1, "thai_do": 5,
                  "tuan_thu": 80, "hoa_nhap": 80}}).json()["error"] == "khao_sat_sai"
    ok = c.post(f"/lo-trinh/hoc-vien/{eid}/cham", json={
        "gate1": {"ket_qua": "dat"},
        "rubric": dict(zip([m for m, _, _ in lo_trinh.RUBRIC], _chia_rubric(85))),
        "must_pass": {m: "dat" for m, _ in lo_trinh.MUST_PASS},
        "khao_sat": {"tuan": 1, "thai_do": 80, "tuan_thu": 80, "hoa_nhap": 80}})
    assert ok.json()["ok"] is True
    ct = c.get(f"/lo-trinh/hoc-vien/{eid}").json()
    assert ct["tom_tat"]["rubric_tong"] == 85 and ct["cham_duoc"] is True and ct["quan_ly_duoc"] is False
    # Mentor không kết luận được, cũng không duyệt ngày nghỉ.
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/ket-luan", json={"ket_qua": "dat"}).status_code == 403
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/nghi", json={"ngay": "2026-10-12"}).status_code == 403


def test_ngay_nghi_lam_lui_bai_hom_nay(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["hom_nay"] = "2026-10-12"
    assert c.get("/lo-trinh").json()["hoc_vien"][0]["ngay_hien_tai"] == 2
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/nghi", json={"ngay": "2026-10-11"}).json()["ok"]
    assert c.get("/lo-trinh").json()["hoc_vien"][0]["ngay_hien_tai"] == 1
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/nghi", json={"ngay": "2026-10-10"}).json()["error"] == "ngay_truoc_bat_dau"


def test_ket_luan_can_ly_do_va_dong_lo_trinh(moi):
    c, trang, _ = moi
    eid = _kich_hoat(c, trang).json()["id"]
    trang["ai"] = TP_MAKEUP
    assert c.post(f"/lo-trinh/hoc-vien/{eid}/ket-luan", json={"ket_qua": "khong_dat"}).json()["error"] == "can_ly_do"
    r = c.post(f"/lo-trinh/hoc-vien/{eid}/ket-luan", json={"ket_qua": "can_bo_sung", "ly_do": "thêm 5 ngày"}).json()
    assert r["trang_thai"] == "dang_hoc"                      # cần bổ sung không đóng lộ trình
    r = c.post(f"/lo-trinh/hoc-vien/{eid}/ket-luan", json={"ket_qua": "dat"}).json()
    assert r["trang_thai"] == "da_ket_luan"
    trang["ai"] = HOC_VIEN
    assert c.post(f"/lo-trinh/bai/{eid}/0/nop", json={"tra_loi": [1, 0]}).json()["error"] == "lo_trinh_da_dong"


def test_id_la_bi_tu_choi(moi):
    c, trang, _ = moi
    assert c.get("/lo-trinh/hoc-vien/..%2F..%2Fx").status_code in (404, 405)
    assert c.get("/lo-trinh/hoc-vien/lt_khongphaihex").json()["error"] == "khong_thay"


def test_gui_tin_dung_chat_id_mot_lan_va_sau_7_gio(moi):
    c, trang, deps = moi
    _kich_hoat(c, trang, telegram_chat_id="98765")
    trang["gio"] = 6
    assert asyncio.run(lo_trinh.gui_bai_hom_nay(deps)) == 0       # chưa tới giờ gửi
    trang["gio"] = 8
    assert asyncio.run(lo_trinh.gui_bai_hom_nay(deps)) == 1
    assert asyncio.run(lo_trinh.gui_bai_hom_nay(deps)) == 0       # không gửi trùng
    assert trang["gui"][0][0] == "98765" and "Bài ngày 0" in trang["gui"][0][1]
    trang["hom_nay"] = "2026-10-11"
    assert asyncio.run(lo_trinh.gui_bai_hom_nay(deps)) == 1       # sang ngày mới gửi bài mới


def test_gui_loi_thi_khong_danh_dau_de_lan_sau_thu_lai(moi):
    c, trang, deps = moi
    _kich_hoat(c, trang, telegram_chat_id="98765")

    async def hong(chat, text):
        return False, "mất mạng"
    deps.tg_send = hong
    assert asyncio.run(lo_trinh.gui_bai_hom_nay(deps)) == 0
    assert lo_trinh.viec_can_gui(lo_trinh._doc(deps.state_path()), deps, "2026-10-10")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
