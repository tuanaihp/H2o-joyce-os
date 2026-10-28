"""Ảnh chụp chuẩn Joyce Harness cho trang Sơ đồ (1.3.39).

Chuẩn nằm ở `docs/dev/Joyce-harness.md` (v1.0.0), lộ trình ở `docs/dev/Joyce-harness-rollout.md`.
Trang Sơ đồ cần thấy chuẩn đó đang CHẠY tới đâu, không phải đọc lại tài liệu: mỗi thành phần một
đèn, đèn lấy từ số thật (plugin có bật không, brain nào có bộ ca thử, đề xuất nào đang chờ chủ).
Thứ chưa làm thì đèn `off` và nói thẳng là chưa làm, đừng tô xanh cho đẹp.

Ba tầng (chuẩn mục 3):
- A. Lõi chạy: giống nhau ở mọi brain (cache, chốt chặn, thu gọn ngữ cảnh, ranh giới quyền, phanh).
- B. Bề mặt phòng ban: của brain đang xem (trợ lý, trợ lý dùng chung, bộ ca thử, khai phạm vi).
- C. Vòng cải tiến: toàn hệ (tự cải tiến, giám định, cổng quyền, canary, trần token).

Hàm thuần: nơi gọi (main) gom số rồi đưa vào, nên test không cần dựng server.
"""
from __future__ import annotations

STANDARD_VERSION = "1.0.0"
TOKEN_CAP = 500_000
TOKEN_CAP_MAX = 1_000_000


def _o(ten, state, **v):
    return {"k": ten, "state": state, "v": v}


def snapshot(*, stages: dict, guard_on: bool, shared_agents: int, tool_rounds: int,
             trim_chars: int, brains_total: int, brains_self_improve: int,
             agents: list, evals_brain: int, telemetry_ready: bool = False, telemetry_n: int = 0,
             routes: dict = None) -> dict:
    """`agents`: frontmatter (dict) của trợ lý trong brain đang xem, gồm cả trợ lý dùng chung hiện ở đó."""
    sg = stages or {}
    pp = sg.get("proposals") or {}
    vd = sg.get("verdicts") or {}
    cn = sg.get("canary") or {}
    n_ag = len(agents or [])
    co_skill = sum(1 for a in agents or [] if (a or {}).get("skills"))
    khai_pham_vi = sum(1 for a in agents or [] if (a or {}).get("allowed_effects"))
    cho_chu = int(pp.get("cho_chu_duyet") or 0)
    evf = int(pp.get("eval_failed") or 0)
    c7 = sg.get("cong7") or {}
    rt = routes or {}
    lc = sg.get("luot_chay") or {}
    nk = sg.get("nhat_ky") or {}
    xem = sum(int(cn.get(k) or 0) for k in ("legacy_review", "het_han", "partial", "conflict"))

    a = [
        _o("cache", "ok"),
        _o("guard", "ok" if guard_on else "bad", n=3),
        _o("trim", "ok", n=trim_chars),
        _o("perm", "ok"),
        _o("brake", "ok", n=tool_rounds),
    ]
    b = [
        _o("agents", "ok" if n_ag else "off", n=n_ag, s=co_skill),
        _o("shared", "ok" if shared_agents else "warn", n=shared_agents),
        _o("evals", "ok" if evals_brain else "off", n=evals_brain),
        _o("scope", "ok" if n_ag and khai_pham_vi == n_ag else "off", n=khai_pham_vi, m=n_ag),
    ]
    c = [
        _o("self", "ok" if brains_self_improve else "off", n=brains_self_improve, m=brains_total),
        _o("judge", "ok", w=int(vd.get("win") or 0), k=int(vd.get("keep") or 0),
           i=int(vd.get("inconclusive") or 0)),
        _o("gate", "warn" if (cho_chu or evf) else "ok", n=cho_chu, e=evf),
        # Cổng đã làm gì trong 7 ngày qua (đếm từ chính các file đề xuất): cho thấy cổng đang CHẠY, không chỉ có cấu hình.
        _o("week", "ok" if sum(c7.values()) else "off", a=int(c7.get("tu_ap") or 0),
           h=int(c7.get("hanh_vi") or 0) + int(c7.get("khung") or 0), q=int(c7.get("quyen") or 0),
           o=int(c7.get("loi_thoi") or 0) + int(c7.get("telemetry") or 0) + int(c7.get("khac") or 0), f=int(c7.get("eval_hong") or 0)),
        # Bộ ghi file triển khai: nhật ký chưa chốt (chết giữa chừng và chưa được đối soát) là đèn vàng.
        _o("writer", "warn" if int(nk.get("dang_do") or 0) else "ok" if int(nk.get("da_chot") or 0) else "off",
           d=int(nk.get("dang_do") or 0), c=int(nk.get("da_chot") or 0), x=int(nk.get("huy") or 0)),
        # Canary "cần xem" (A01): cũ chưa có telemetry (legacy_review), hết hạn thiếu bằng chứng, một phần hay xung đột.
        # Những thứ này KHÔNG được hiện xanh: chưa đủ dữ liệu khác với không có lỗi.
        _o("canary", "warn" if (cn.get("reverted") or xem) else "ok", n=int(cn.get("canary") or 0),
           r=int(cn.get("reverted") or 0), l=xem),
        # Chứng nhận đường thực thi và ghi (B03): bản kê trung thực. Xanh chỉ khi MỌI đường đạt; có đường một phần thì vàng; còn lại xám.
        _o("routes", "ok" if rt.get("tong") and rt.get("chung_nhan") == rt.get("tong") else "warn" if rt.get("mot_phan") else "off",
           c=int(rt.get("chung_nhan") or 0), p=int(rt.get("mot_phan") or 0), u=int(rt.get("chua_chung_nhan") or 0), n=int(rt.get("tong") or 0)),
        # Lượt chạy thật do host ghi (B01): chat bot, việc giao cho trợ lý, bước workflow. Xám khi 7 ngày qua chưa ghi lượt nào.
        _o("runs", "ok" if int(lc.get("logical") or 0) else "off", n=int(lc.get("logical") or 0), v=int(lc.get("verified_pass") or 0),
           u=int(lc.get("chua_kiem") or 0), i=int(lc.get("gian_doan") or 0)),
        # Nguồn bằng chứng để kiểm chứng canary. XÁM khi chưa có (gói B): khi đó file dùng chung không được tự áp.
        _o("telemetry", "ok" if telemetry_ready else "off", ready=1 if telemetry_ready else 0, n=int(telemetry_n)),
        # Đã chốt (28/10/2026) nhưng CHƯA ép trong code: vòng cải tiến chưa đếm token theo lượt.
        _o("budget", "off", n=TOKEN_CAP, m=TOKEN_CAP_MAX),
    ]
    tiers = [{"id": "A", "items": a}, {"id": "B", "items": b}, {"id": "C", "items": c}]
    tong = sum(len(t["items"]) for t in tiers)
    xanh = sum(1 for t in tiers for x in t["items"] if x["state"] == "ok")
    return {
        "version": STANDARD_VERSION, "tiers": tiers, "ok": xanh, "total": tong,
        # Giai đoạn rollout (Joyce-harness-rollout.md mục 3): 0A xong ở 1.3.39; 0B mới xong ba lỗ
        # đã xác minh (B-01, B-10, B-12), phần còn lại (kiểm schema hợp đồng lúc chạy) chưa làm.
        "phases": [{"k": "0A", "state": "ok"}, {"k": "0B", "state": "warn"},
                   {"k": "1", "state": "off"}, {"k": "2", "state": "off"}],
    }
