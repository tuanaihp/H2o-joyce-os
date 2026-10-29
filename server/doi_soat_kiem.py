"""Bộ kiểm ĐỘC LẬP cho pilot Đối Soát (G3): tính lại số từ dữ liệu gốc rồi đối chiếu với báo cáo của agent.

Vì sao có: plan (mục 7.1) đòi "check độc lập đọc lại" thay vì tin câu trả lời của model. Hàm ở đây THUẦN và tất định: không gọi model, không đọc đĩa, không
mạng. Kết quả của nó là căn cứ để chấm một lượt `verified_pass` hay `verified_fail`; câu "đã đối chiếu xong" của agent không phải căn cứ.

Quy tắc nghiệp vụ giữ đúng như plan: tiền là số nguyên đồng; thu và chi tính RIÊNG, không suy ra "lãi gộp" khi chưa có định nghĩa kế toán được duyệt; số liệu
hỏng (phiếu trùng mã, số âm, phiếu trỏ tới hợp đồng không có) làm cả lần kiểm KHÔNG đạt chứ không bị bỏ qua êm.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _nguyen(v: Any):
    """Số tiền nguyên đồng không âm, hoặc None nếu không hợp lệ (bool, số lẻ, âm, chữ)."""
    if isinstance(v, bool) or not isinstance(v, int):
        return None
    return v if v >= 0 else None


def tinh(du_lieu: Dict[str, Any]) -> Dict[str, Any]:
    """Số ĐÚNG tính từ dữ liệu gốc. Trả {"hop_dong": {id: {gia_tri, tong_thu, tong_chi, con_phai_thu}}, "loi": [...]}.

    `con_phai_thu` = giá trị hợp đồng trừ tổng thu; âm (thu vượt giá trị) vẫn giữ nguyên số âm để lộ ra, không kẹp về 0."""
    loi: List[str] = []
    hd: Dict[str, Dict[str, int]] = {}
    for h in (du_lieu or {}).get("hop_dong") or []:
        hid, gt = str((h or {}).get("id") or ""), _nguyen((h or {}).get("gia_tri"))
        if not hid:
            loi.append("hợp đồng không có mã")
        elif hid in hd:
            loi.append(f"hợp đồng trùng mã {hid}")
        elif gt is None:
            loi.append(f"hợp đồng {hid}: giá trị không hợp lệ")
        else:
            hd[hid] = {"gia_tri": gt, "tong_thu": 0, "tong_chi": 0}
    thay = set()
    for p in (du_lieu or {}).get("phieu") or []:
        pid, hid, loai, tien = str((p or {}).get("id") or ""), str((p or {}).get("hop_dong") or ""), str((p or {}).get("loai") or ""), _nguyen((p or {}).get("so_tien"))
        if not pid or pid in thay:
            loi.append(f"phiếu {pid or '(không mã)'}: thiếu mã hoặc trùng mã (nguy cơ tính trùng)")
            continue
        thay.add(pid)
        if tien is None:
            loi.append(f"phiếu {pid}: số tiền không hợp lệ")
        elif hid not in hd:
            loi.append(f"phiếu {pid}: trỏ tới hợp đồng không có ({hid or 'trống'})")
        elif loai == "thu":
            hd[hid]["tong_thu"] += tien
        elif loai == "chi":
            hd[hid]["tong_chi"] += tien
        else:
            loi.append(f"phiếu {pid}: loại lạ ({loai or 'trống'})")
    for v in hd.values():
        v["con_phai_thu"] = v["gia_tri"] - v["tong_thu"]
    return {"hop_dong": hd, "loi": loi}


TRUONG_SO = ("tong_thu", "con_phai_thu")


def kiem(du_lieu: Dict[str, Any], bao_cao: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Đối chiếu `bao_cao` của agent (danh sách {hop_dong, tong_thu, con_phai_thu}) với số tính lại.

    `dat` chỉ True khi: dữ liệu gốc sạch, MỌI hợp đồng của dữ liệu có mặt trong báo cáo (phủ đủ), không hợp đồng thừa, và mọi số khớp từng đồng.
    Số khai thiếu hoặc sai kiểu tính là lệch, không tính là "không ai hỏi"."""
    dung = tinh(du_lieu)
    ket_qua, thua, da_bao = [], [], set()
    for b in bao_cao or []:
        hid = str((b or {}).get("hop_dong") or "")
        da_bao.add(hid)
        if hid not in dung["hop_dong"]:
            thua.append(hid or "(không mã)")
            continue
        lech = {}
        for tr in TRUONG_SO:
            bao = (b or {}).get(tr)
            if isinstance(bao, bool) or not isinstance(bao, int) or bao != dung["hop_dong"][hid][tr]:
                lech[tr] = {"bao": bao, "dung": dung["hop_dong"][hid][tr]}
        ket_qua.append({"hop_dong": hid, "dat": not lech, "lech": lech})
    thieu = sorted(h for h in dung["hop_dong"] if h not in da_bao)
    dat = not dung["loi"] and not thieu and not thua and all(k["dat"] for k in ket_qua) and bool(ket_qua)
    return {"dat": dat, "ket_qua": ket_qua, "thieu": thieu, "thua": sorted(thua), "loi_du_lieu": dung["loi"]}
