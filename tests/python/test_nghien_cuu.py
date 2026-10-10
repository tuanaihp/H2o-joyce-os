"""Trang Nghiên cứu (server/nghien_cuu.py): sáu khu đọc đúng từ brain, chỉ đọc.

    python tests/run.py nghien_cuu

Dựng brain TẠM (tmp_path), không đụng brains/ thật. Kế hoạch: docs/dev/2026-10-11-process-factory-plan.md (T1).
"""
from _paths import ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path
import nghien_cuu  # noqa: E402

HOM_NAY = "2026-10-11"


def _ghi(path, noi_dung):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(noi_dung, encoding="utf-8")


def _y_tuong(root, ten, **truong):
    khoi = "\n".join(f"{k}: {v}" for k, v in truong.items())
    _ghi(root / "wiki" / "y-tuong" / f"{ten}.md", f"---\ntype: wiki\n{khoi}\n---\n\n# {ten}\n\nNội dung.\n")


def test_brain_khong_ton_tai(tmp_path):
    d = nghien_cuu.doc_trang(tmp_path / "khong-co", hom_nay=HOM_NAY)
    assert d["co_brain"] is False
    assert d["tong_quan"]["y_tuong_tong"] == 0
    assert [c["giai_doan"] for c in d["pipeline"]["cot"]] == list(nghien_cuu.PIPELINE)


def test_brain_rong_van_du_sau_khu(tmp_path):
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    assert d["co_brain"] is True
    assert set(d) >= {"tong_quan", "pipeline", "thu_vien", "quy_trinh", "radar", "nhat_ky"}
    assert d["thu_vien"] == {"concept": [], "nguon_booking": False}
    assert d["radar"]["muc"] == [] and d["nhat_ky"]["muc"] == []


def test_pipeline_va_tong_quan_theo_giai_doan(tmp_path):
    _y_tuong(tmp_path, "vay-trang", loai="concept", giai_doan="pilot", created="2026-10-05")
    _y_tuong(tmp_path, "vay-do", loai="concept", giai_doan="hoat-dong", created="2026-09-01")
    _y_tuong(tmp_path, "quy-trinh-nhan-anh", loai="quy-trinh-moi", giai_doan="moi", created="2026-10-10")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    t = d["tong_quan"]
    assert t["y_tuong_tong"] == 3
    assert t["pilot_dang_chay"] == 1
    assert t["theo_giai_doan"]["moi"] == 1 and t["theo_giai_doan"]["hoat-dong"] == 1
    cot = {c["giai_doan"]: c["the"] for c in d["pipeline"]["cot"]}
    assert [x["slug"] for x in cot["pilot"]] == ["vay-trang"]
    assert [x["slug"] for x in cot["moi"]] == ["quy-trinh-nhan-anh"]


def test_thu_vien_concept_va_booking(tmp_path):
    _y_tuong(tmp_path, "a", loai="concept", giai_doan="pilot", booking="7")
    _y_tuong(tmp_path, "b", loai="concept", giai_doan="hoat-dong")
    _y_tuong(tmp_path, "c", loai="concept", giai_doan="moi")          # chưa vào thư viện
    _y_tuong(tmp_path, "d", loai="concept", giai_doan="gac", booking="khong-so")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    slugs = [x["slug"] for x in d["thu_vien"]["concept"]]
    assert slugs == ["a", "b", "d"]
    booking = {x["slug"]: x["booking"] for x in d["thu_vien"]["concept"]}
    assert booking == {"a": 7, "b": None, "d": None}                   # chữ không phải số thì None
    assert d["thu_vien"]["nguon_booking"] is True


def test_nguon_booking_chua_co_thi_bao_chua_noi(tmp_path):
    _y_tuong(tmp_path, "a", loai="concept", giai_doan="hoat-dong")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    assert d["thu_vien"]["nguon_booking"] is False


def test_trang_thieu_giai_doan_suy_ra_tu_status_cu(tmp_path):
    _y_tuong(tmp_path, "nhap", status="draft")
    _y_tuong(tmp_path, "da-duyet", status="active")
    _y_tuong(tmp_path, "loai-bo", status="archived")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    cot = {c["giai_doan"]: [x["slug"] for x in c["the"]] for c in d["pipeline"]["cot"]}
    assert cot["moi"] == ["nhap"]
    assert cot["hoat-dong"] == ["da-duyet"]
    assert "loai-bo" not in sum(cot.values(), [])                    # gac không hiện ở pipeline
    assert d["tong_quan"]["theo_giai_doan"]["gac"] == 1


def test_loai_la_va_gia_tri_dau_hai_cham(tmp_path):
    _y_tuong(tmp_path, "lạ", loai="khong-biet", giai_doan="moi", title="Ánh sáng: ấm và mềm")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    muc = d["pipeline"]["cot"][0]["the"][0]
    assert muc["loai"] == "concept"                                  # loại lạ thì rơi về concept
    assert muc["tieu_de"] == "Ánh sáng: ấm và mềm"


def test_change_request_mo_va_da_dong(tmp_path):
    _y_tuong(tmp_path, "sua-a", loai="sua-quy-trinh", giai_doan="cho-duyet")
    _y_tuong(tmp_path, "sua-b", loai="sua-quy-trinh", giai_doan="hoat-dong")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    assert d["tong_quan"]["change_request_mo"] == 1
    assert [x["slug"] for x in d["quy_trinh"]["change_request"]] == ["sua-a"]


def test_sop_qua_han_va_ban_da_thay_the(tmp_path):
    _ghi(tmp_path / "wiki" / "quy-trinh" / "chup-album.md",
         "---\nstatus: active\nphien_ban: 2\nngay_ra_soat: 2026-09-01\n---\n# Chụp album\n")
    _ghi(tmp_path / "wiki" / "quy-trinh" / "chup-album-v1.md",
         "---\nstatus: superseded\nphien_ban: 1\nngay_ra_soat: 2026-01-01\n---\n# Chụp album v1\n")
    _ghi(tmp_path / "wiki" / "quy-trinh" / "loc-anh.md",
         "---\nstatus: active\nphien_ban: 1\nngay_ra_soat: 2026-12-01\nthay_the: x\n---\n# Lọc ảnh\n")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    assert d["tong_quan"]["sop_active"] == 2
    assert d["tong_quan"]["sop_superseded"] == 1
    assert d["tong_quan"]["sop_qua_han"] == 1                         # chỉ chụp-album quá hạn
    qua = {s["slug"]: s["qua_han"] for s in d["quy_trinh"]["sop"]}
    assert qua == {"chup-album": True, "chup-album-v1": False, "loc-anh": False}


def test_radar_moi_nhat_len_dau_va_toi_da_nam(tmp_path):
    for i in range(7):
        _ghi(tmp_path / "wiki" / "radar" / f"tuan-{i}.md",
             f"---\nngay: 2026-10-{i + 1:02d}\n---\n# Bản tin tuần {i}\n")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    muc = d["radar"]["muc"]
    assert len(muc) == nghien_cuu.MUC_RADAR == 5
    assert muc[0]["slug"] == "tuan-6" and muc[0]["ngay"] == "2026-10-07"


def test_nhat_ky_dao_nguoc_va_bo_dong_la(tmp_path):
    _ghi(tmp_path / "wiki" / "log.md",
         "# Wiki Log\n\nMô tả chung.\n\n"
         "## [2026-10-05] y-tuong | Vay trang\n- chi tiết\n\n"
         "dòng không phải mục\n\n"
         "## [2026-10-07] ingest | Bản tin\n")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    muc = d["nhat_ky"]["muc"]
    assert [m["ngay"] for m in muc] == ["2026-10-07", "2026-10-05"]
    assert muc[1] == {"ngay": "2026-10-05", "loai": "y-tuong", "tieu_de": "Vay trang"}


def test_trang_ghi_theo_skill_doc_dung(tmp_path):
    # Đúng định dạng skill h2o-y-tuong ghi (T4): có ngoặc kép, ngày YAML, booking số.
    _ghi(tmp_path / "wiki" / "y-tuong" / "anh-sang-am.md",
         "---\ntype: wiki\nstatus: draft\nloai: quy-trinh-moi\ngiai_doan: cho-duyet\n"
         'loai_ly_do: "Có tiền tố [Ý tưởng][Quy trình mới]"\n'
         'title: "Ánh sáng: ấm và mềm"\nbooking: 5\ncreated: 2026-10-11\n---\n# Ánh sáng\n')
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    muc = d["pipeline"]["cot"][4]["the"][0]                      # cột cho-duyet
    assert muc["tieu_de"] == "Ánh sáng: ấm và mềm"
    assert muc["loai"] == "quy-trinh-moi" and muc["ngay"] == "2026-10-11"
    assert d["tong_quan"]["change_request_mo"] == 0               # quy-trinh-moi không phải đề nghị sửa


def test_file_gach_duoi_khong_duoc_dem(tmp_path):
    _ghi(tmp_path / "wiki" / "y-tuong" / "_open-questions.md", "---\nstatus: active\n---\n# Câu hỏi\n")
    _y_tuong(tmp_path, "that", loai="concept", giai_doan="moi")
    d = nghien_cuu.doc_trang(tmp_path, hom_nay=HOM_NAY)
    assert d["tong_quan"]["y_tuong_tong"] == 1


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
