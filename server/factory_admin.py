"""Quản trị triển khai tự cải tiến cho CHỦ: xem trạng thái, xem diff, khôi phục từng đích, tạm dừng, đã đọc, yêu cầu nhân.

A06 của gói A (docs/dev/2026-10-28-joyce-harness-g1-g2-sonnet-plan.md). Logic nằm ở đây, route mỏng ở `main.py`, để test được mà không
cần dựng HTTP.

Nguyên tắc (plan A06):
- Server tự tra đường dẫn từ state theo `canary_id` và `target_id`; client KHÔNG gửi đường dẫn nào. Không có đường dẫn tuyệt đối
  trong kết quả trả về (chỉ tên brain và đường dẫn tương đối trong brain).
- Mọi thao tác ghi gửi kèm `expected_revision` (hash ứng viên đầy đủ), `action_id` chống lặp (cùng id trả đúng kết quả cũ, không làm
  lần hai) và `reason`. Bản đã đổi kể từ lúc chủ nhìn thì từ chối (stale) chứ không làm theo hình cũ.
- Khôi phục chỉ chạy khi có RECEIPT committed của chính triển khai đó, hash bản sao lưu đúng, và file hiện tại còn ĐÚNG bản triển khai
  đã ghi. Có sửa mới thì báo conflict kèm diff, không ghi. Sao lưu không tự tạo ra quyền ghi đè.
- "Yêu cầu nhân" đi qua CÙNG cổng với tự nhân: thiếu telemetry, thiếu bằng chứng, canary cũ hay đích override thì từ chối và liệt kê điều
  kiện còn thiếu. Không có nút "ép". `acknowledge` chỉ xác nhận đã đọc, không đánh dấu đạt chất lượng.
- Chủ duy nhất: tài khoản nhân viên bị từ chối ở route. Kiểm quyền ở server, không chỉ ẩn nút.
"""
from __future__ import annotations

import difflib
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import deploy_writer
import factory

HANH_DONG = ("pause", "restore", "ack", "promote")
TRAN_DIFF = 20000
TRAN_LICH_SU_HANH_DONG = 200


def _ten_goc(root: str) -> str:
    return Path(str(root or "")).name


def _tid(root: str) -> str:
    return factory._sha(str(Path(str(root or ""))))


def _canary(st: dict, canary_id: str) -> Optional[dict]:
    for c in st.get("canaries", []):
        if str(c.get("id")) == str(canary_id):
            return c
    return None


def _revision(c: dict) -> str:
    return str(c.get("candidate_hash") or c.get("hash") or "")


def _doan_dau(h: str) -> str:
    return str(h or "")[:10]


def dieu_kien_nhan(deps, c: dict) -> list:
    """Điều kiện còn THIẾU để một canary được nhân. Rỗng = đủ. Cùng các điều kiện mà `canary_tick` đòi, nên không có đường vòng."""
    thieu = []
    if c.get("state") != "canary":
        thieu.append(f"canary đang ở trạng thái `{c.get('state')}`, không phải đang canh")
    if not factory.telemetry_ready(deps, str(c.get("brain") or ""), str(c.get("target") or "")):
        thieu.append("chưa có telemetry: hệ chưa gắn lượt chạy với agent và phiên bản nên không kiểm chứng được")
    ev = factory._canary_evidence(deps, c)
    can = int(c.get("min_tasks") or factory.CANARY_MIN_TASKS)
    if ev["tasks"] < can:
        thieu.append(f"mới có {ev['tasks']}/{can} việc đã chạy trên bản mới")
    if ev["bad"]:
        thieu.append(f"có {ev['bad']} việc lỗi trên bản mới")
    if time.time() < float(c.get("promote_at") or 0):
        thieu.append("chưa đủ thời gian quan sát")
    ov = [t for t in (c.get("targets") or []) if t.get("state") == "override"]
    if ov:
        thieu.append(f"{len(ov)} đích có bản riêng từ trước (override), phải hợp nhất bằng đề xuất riêng")
    if factory._dang_tam_dung(deps):
        thieu.append("đang tạm dừng tự triển khai")
    return thieu


def _dich_chi_tiet(c: dict) -> list:
    ra = []
    dep = str(c.get("deployment_id") or c.get("id") or "")
    for t in c.get("targets") or []:
        rc = deploy_writer.doc_receipt(Path(str(t.get("root") or "")), dep, _tid(t.get("root"))) if dep else None
        co_the = bool(t.get("state") == "promoted" and t.get("co_receipt") and rc and rc.get("trang_thai") == "committed" and t.get("backup"))
        ra.append({"target_id": _tid(t.get("root")), "brain": _ten_goc(t.get("root")), "state": t.get("state"), "quan_he": t.get("quan_he") or "",
                   "co_receipt": bool(t.get("co_receipt")), "co_the_khoi_phuc": co_the, "restored": bool(t.get("restored_at")),
                   "loi": str(t.get("error") or "")[:120]})
    return ra


def trang_thai(deps) -> dict:
    """Chi tiết cho giao diện. KHÔNG chứa đường dẫn tuyệt đối. `telemetry_ready` luôn đi kèm để UI không hiện xanh khi thiếu dữ liệu."""
    st = factory._load_state(deps)
    ds = []
    for c in st.get("canaries", [])[-30:]:
        ds.append({
            "id": c.get("id"), "brain": c.get("brain"), "file": c.get("target"), "state": c.get("state"),
            "nguon_chay": "da_khoi_phuc" if c.get("nguon_restored_at") else ("ban_moi" if c.get("state") not in ("reverted", "superseded") else "khong_chac"),
            "ung_vien": _doan_dau(_revision(c)), "baseline": _doan_dau(str(c.get("source_baseline_hash") or "")),
            "revision": _revision(c), "deployment_id": c.get("deployment_id") or "",
            "evidence": c.get("evidence") or {}, "min_tasks": int(c.get("min_tasks") or factory.CANARY_MIN_TASKS),
            "promote_at": c.get("promote_at"), "applied_at": c.get("applied_at"),
            "legacy": bool(c.get("legacy")), "ly_do": (c.get("legacy") or {}).get("ly_do") or "",
            "acknowledged": bool(c.get("acknowledged")),
            "nguon_co_the_khoi_phuc": bool(c.get("deployment_id") and deploy_writer.doc_receipt(Path(str(c.get("root") or "")), str(c.get("deployment_id")), "nguon")),
            "dich": _dich_chi_tiet(c),
            "thieu": dieu_kien_nhan(deps, c) if c.get("state") in ("canary", "legacy_review", "partial", "conflict", "het_han") else [],
        })
    return {"ok": True, "telemetry_ready": bool(factory.telemetry_ready(deps)), "tam_dung": bool(st.get("tam_dung")), "schema": st.get("schema"),
            "canaries": ds}


def _tra_cuu(deps, st: dict, canary_id: str, target_id: str) -> Tuple[Optional[dict], Optional[dict], str]:
    """(canary, đích, lỗi). `target_id` = 'nguon' hoặc id đích do server cấp. Không nhận đường dẫn từ client."""
    c = _canary(st, canary_id)
    if not c:
        return None, None, "không có canary này"
    if target_id == "nguon":
        return c, {"root": c.get("root"), "state": "promoted", "co_receipt": True, "backup": c.get("backup"), "_nguon": True}, ""
    for t in c.get("targets") or []:
        if _tid(t.get("root")) == str(target_id):
            return c, t, ""
    return c, None, "không có đích này trong canary"


def diff_dich(deps, canary_id: str, target_id: str) -> Tuple[int, dict]:
    """Diff giữa file HIỆN TẠI và bản sao lưu (cái sẽ có sau khi khôi phục). Cắt ở TRAN_DIFF ký tự; đường dẫn là tương đối."""
    c, t, loi = _tra_cuu(deps, factory._load_state(deps), canary_id, target_id)
    if loi or not t:
        return 404, {"ok": False, "error": loi or "không có đích"}
    hien = factory._doc_file(Path(str(t.get("root") or "")) / str(c.get("target") or ""))
    goc = factory._doc_file(Path(str(t.get("backup") or ""))) if t.get("backup") else None
    if hien is None:
        return 409, {"ok": False, "error": "file không còn ở đích"}
    if goc is None:
        return 409, {"ok": False, "error": "không có bản sao lưu để so"}
    d = "\n".join(difflib.unified_diff(hien.splitlines(), goc.splitlines(), "hiện tại", "sau khi khôi phục", lineterm="", n=2))
    return 200, {"ok": True, "brain": _ten_goc(t.get("root")), "file": c.get("target"), "diff": d[:TRAN_DIFF], "cat_bot": len(d) > TRAN_DIFF}


def _nho_hanh_dong(st: dict, action_id: str, kq: dict) -> None:
    ls = st.setdefault("hanh_dong", {})
    ls[action_id] = kq
    if len(ls) > TRAN_LICH_SU_HANH_DONG:
        for k in list(ls)[:len(ls) - TRAN_LICH_SU_HANH_DONG]:
            ls.pop(k, None)


def thuc_hien(deps, action: str, *, canary_id: str = "", target_id: str = "", expected_revision: str = "", action_id: str = "",
              reason: str = "", on: Optional[bool] = None, nguoi: str = "chu") -> Tuple[int, dict]:
    """Một thao tác quản trị. Trả (mã HTTP, kết quả). Mọi kiểm tra ở đây, không phụ thuộc giao diện đã ẩn nút hay chưa."""
    if action not in HANH_DONG:
        return 400, {"ok": False, "error": "thao tác không hợp lệ"}
    if len(str(action_id or "")) < 8:
        return 400, {"ok": False, "error": "thiếu action_id (chống làm hai lần)"}
    if len(str(reason or "").strip()) < 3:
        return 400, {"ok": False, "error": "cần nêu lý do (ít nhất vài chữ)"}
    with factory._khoa_state(deps):
        st = factory._load_state(deps)
        cu = (st.get("hanh_dong") or {}).get(action_id)
        if cu is not None:
            return int(cu.get("http", 200)), {**cu["kq"], "lap_lai": True}      # cùng action_id: trả đúng kết quả cũ, không làm lần hai
        http, kq = _thuc_hien_trong_khoa(deps, st, action, canary_id, target_id, expected_revision, reason, on, nguoi)
        _nho_hanh_dong(st, action_id, {"http": http, "kq": kq, "luc": time.time(), "action": action})
        factory._save_state(deps, st)
        return http, kq


def _thuc_hien_trong_khoa(deps, st, action, canary_id, target_id, expected_revision, reason, on, nguoi) -> Tuple[int, dict]:
    if action == "pause":
        bat = bool(on)
        st["tam_dung"] = bat
        st.setdefault("nhat_ky_quan_tri", []).append({"luc": time.time(), "action": "pause", "on": bat, "ly_do": reason[:200], "nguoi": nguoi})
        return 200, {"ok": True, "tam_dung": bat}
    c = _canary(st, canary_id)
    if not c:
        return 404, {"ok": False, "error": "không có canary này"}
    if expected_revision != _revision(c):
        return 409, {"ok": False, "stale": True, "error": "canary đã đổi kể từ lúc anh xem (bản ứng viên khác), tải lại rồi thử"}
    if action == "ack":
        c["acknowledged"] = {"luc": time.time(), "nguoi": nguoi, "ly_do": reason[:200]}
        return 200, {"ok": True, "ghi_chu": "chỉ xác nhận đã đọc, KHÔNG đánh dấu đạt chất lượng"}
    if action == "promote":
        thieu = dieu_kien_nhan(deps, c)
        # Không có nhánh "ép": cùng cổng với tự nhân. Gói A chưa có telemetry nên luôn có điều kiện thiếu.
        return 409, {"ok": False, "dieu_kien_thieu": thieu or ["yêu cầu nhân thủ công chưa được hỗ trợ ở gói A"],
                     "error": "chưa đủ điều kiện để nhân; yêu cầu này không bỏ qua telemetry, eval, quyền hay đích override"}
    # restore
    c2, t, loi = _tra_cuu(deps, st, canary_id, target_id)
    if loi or not t:
        return 404, {"ok": False, "error": loi or "không có đích"}
    la_nguon = bool(t.get("_nguon"))
    goc = Path(str(t.get("root") or ""))
    dep = str(c.get("deployment_id") or "")
    tid = "nguon" if la_nguon else _tid(t.get("root"))
    if not dep:
        return 409, {"ok": False, "error": "canary cũ không có mã triển khai nên không có nhật ký để khôi phục an toàn"}
    if not la_nguon and (t.get("state") != "promoted" or not t.get("co_receipt")):
        return 409, {"ok": False, "error": "đích này không do lần triển khai này ghi (không có receipt), không đủ căn cứ để khôi phục"}
    rc = deploy_writer.doc_receipt(goc, dep, tid)
    if not rc or rc.get("trang_thai") != "committed":
        return 409, {"ok": False, "error": "không có nhật ký committed của lần triển khai này"}
    bp = Path(str(rc.get("backup") or ""))
    goc_text = factory._doc_file(bp)
    if goc_text is None or deploy_writer.sha256(goc_text) != rc.get("backup_hash"):
        return 409, {"ok": False, "error": "bản sao lưu mất hoặc hash không khớp nhật ký, KHÔNG ghi gì"}
    dst = goc / str(c.get("target") or "")
    hien = factory._doc_file(dst)
    if hien is None:
        return 409, {"ok": False, "error": "file không còn ở đích"}
    if deploy_writer.sha256(hien) != rc.get("sau_hash"):
        return 409, {"ok": False, "conflict": True, "error": "file đã bị sửa sau lần triển khai; không ghi đè. Xem diff rồi quyết định",
                     "diff_url_target": tid}
    try:
        kq = factory._ghi_dich(deps, goc, dst, goc_text, deployment_id=dep, target_id="kp-" + tid, truoc_hash=rc.get("sau_hash"))
    except deploy_writer.DuongKhongAnToan as e:
        return 409, {"ok": False, "error": f"đường dẫn không an toàn: {e}"[:160]}
    except Exception as e:  # noqa: BLE001
        return 500, {"ok": False, "error": f"không ghi được: {type(e).__name__}"}
    if kq.get("ket_qua") != "committed":
        return 409, {"ok": False, "conflict": kq.get("ket_qua") == "conflict", "error": "file đổi đúng lúc khôi phục, không ghi đè"}
    if la_nguon:
        c["nguon_restored_at"] = time.time()
    else:
        for tg in c.get("targets") or []:
            if _tid(tg.get("root")) == tid:
                tg["restored_at"], tg["state"] = time.time(), "restored"
    st.setdefault("nhat_ky_quan_tri", []).append({"luc": time.time(), "action": "restore", "canary": canary_id, "target": tid, "ly_do": reason[:200], "nguoi": nguoi})
    return 200, {"ok": True, "da_khoi_phuc": True, "target_id": tid}
