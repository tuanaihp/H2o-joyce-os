"""Route GET /nghien-cuu: đọc đúng brain phòng Nghiên cứu, chặn nhân viên, không đụng brains/ thật.

    python tests/run.py nghien_cuu_route

Kế hoạch: docs/dev/2026-10-11-process-factory-plan.md (T2).
"""
from _paths import ROOT, SERVER  # noqa: F401
import os
import tempfile
from pathlib import Path

state = tempfile.mkdtemp(prefix="joyce-nc-route-")
os.environ["JOYCE_STATE_DIR"] = state
os.environ["BRAINS_DIR"] = str(Path(state) / "brains")
os.environ["JOYCE_SESSIONS_DB"] = str(Path(state) / "sessions.db")

import main  # noqa: E402
import nghien_cuu  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

app = FastAPI()
app.get("/nghien-cuu")(main.nghien_cuu_trang)
client = TestClient(app)

brain = Path(state) / "brains" / nghien_cuu.PILOT_BRAIN
(brain / "wiki" / "y-tuong").mkdir(parents=True)
(brain / "wiki" / "y-tuong" / "vay-trang.md").write_text(
    "---\nloai: concept\ngiai_doan: pilot\nbooking: 3\n---\n# Váy trắng\n", encoding="utf-8")


def test_admin_doc_dung_brain_pilot():
    r = client.get("/nghien-cuu")
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True and d["co_brain"] is True and d["brain"] == nghien_cuu.PILOT_BRAIN
    assert d["tong_quan"]["pilot_dang_chay"] == 1
    assert d["thu_vien"]["concept"][0]["booking"] == 3
    assert {"tong_quan", "pipeline", "thu_vien", "quy_trinh", "radar", "nhat_ky"} <= set(d)


def test_nhan_vien_bi_chan(monkeypatch):
    monkeypatch.setattr(main, "_staff_req", lambda request: {"id": "nv-1"})
    r = client.get("/nghien-cuu")
    assert r.status_code == 403
    assert r.json() == {"ok": False, "error": "staff_denied"}


def test_duong_dan_nam_trong_danh_sach_chan_nhan_vien():
    assert "/nghien-cuu" in main._STAFF_DENY


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
