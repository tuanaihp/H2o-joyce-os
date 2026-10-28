"""Giàn giáo cho test canary cũ: bằng chứng canary nay đọc từ SỔ LƯỢT CHẠY (B02), còn các test từ gói A dựng bằng chứng bằng danh sách
việc Kanban giả (`deps.store.t`). `cai_dat(factory)` bọc `factory._canary_evidence` để đổi danh sách việc giả đó thành lượt chạy
trong sổ (đã kiểm chứng đạt hoặc rớt) rồi mới đọc bằng ĐÚNG hàm thật. Phần ngữ nghĩa của sổ (chưa kiểm không tính, sai revision bị
loại, retry một lần...) có test riêng ở test_b02_bang_chung_so.py; ở đây chỉ để các test về luồng canary khỏi phải dựng lại sổ.

Chỉ dùng trong test. Quy tắc đổi giống bằng chứng cũ: việc gắn khoá `agent:<mã>:<slug>`, tạo sau lúc áp; done là đạt, blocked là rớt."""
import time
from pathlib import Path


def cai_dat(factory):
    import run_ledger
    goc = factory._canary_evidence

    def boc(deps, c):
        # Mỗi kịch bản test dùng lại tên brain `nguon` và cùng băm ứng viên: chỉ giữ lượt của canary đang xét để kịch bản này không
        # thấy bằng chứng của kịch bản khác.
        run_ledger._db().execute("DELETE FROM agent_runs WHERE run_id LIKE 'gg-%' AND run_id NOT LIKE ?", (f"gg-{c.get('id')}-%",))
        slug = str(c.get("slug") or "").lower()
        cand = str(c.get("candidate_hash") or "")
        if len(cand) != 64 and c.get("hash"):        # canary cũ: cùng cách suy ra như factory._canary_evidence
            cur = factory._doc_file(Path(str(c.get("root") or "")) / str(c.get("target") or ""))
            if cur is not None and factory._sha(cur) == str(c.get("hash")):
                cand = factory._sha256(cur)
        since = float(c.get("applied_at") or 0)
        try:
            tasks = deps.store.list_tasks(str(c.get("root")), include_archived=False, limit=400) or []
        except Exception:  # noqa: BLE001
            tasks = []
        for i, t in enumerate(tasks):
            ik = str(t.get("idempotency_key") or "")
            parts = ik[len("agent:"):].split(":") if ik.startswith("agent:") else []
            if len(parts) < 2 or parts[1].lower() != slug or float(t.get("created_at") or 0) < since:
                continue
            stt = str(t.get("status") or "")
            if stt not in ("done", "blocked"):
                continue
            rid = f"gg-{c.get('id')}-{i}-{t.get('id')}"
            if run_ledger.lay(rid):
                continue
            run_ledger.bat_dau(brain_id=Path(str(c.get("root"))).name, agent_id=slug, entrypoint="task", run_id=rid,
                               logical_execution_id=rid, revision={"agent_revision": cand}, now=float(t.get("created_at") or time.time()))
            if stt == "done":
                run_ledger.ket_thuc(rid, "completed", verification="verified_pass")
            else:
                run_ledger.ket_thuc(rid, "failed", block_kind="business", verification="verified_fail")
        return goc(deps, c)

    factory._canary_evidence = boc
