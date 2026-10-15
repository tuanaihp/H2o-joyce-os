"""Bản dự phòng Telegram (server/kenh_du_phong.py) và chặn xoá trắng secret khi khoá hỏng (config.py).

    python tests/run.py kenh_du_phong

Chủ studio mất token bot Telegram trong settings.json (15/10). Hai lớp phòng:
  1. write_settings không ghi "" đè lên blob secret cũ khi blob đó KHÔNG giải mã được lúc ghi.
  2. Một bản dự phòng riêng ngoài settings.json, tự cập nhật khi bot chạy được.

JOYCE_STATE_DIR tạm: không đụng settings.json thật.
"""
import os
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-du-phong-")

from _paths import ROOT, SERVER  # noqa: E402,F401  - nạp server/ vào sys.path
import json  # noqa: E402

import pytest  # noqa: E402

import config as cfgmod  # noqa: E402
import kenh_du_phong  # noqa: E402
import secrets_store  # noqa: E402

TOKEN = "123456:ABCdefGhIjkLmnOPqrSTuvWXyz"


@pytest.fixture(autouse=True)
def sach():
    for p in (cfgmod.SETTINGS_PATH, kenh_du_phong._path()):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    yield


def test_luu_xem_lay_khong_lo_token():
    assert kenh_du_phong.xem() == {"co": False}
    assert kenh_du_phong.luu(TOKEN, "8980648636, -1001234567890", "tay")
    x = kenh_du_phong.xem()
    assert x["co"] and x["token_cuoi"] == "WXyz" and x["nguon"] == "tay"
    assert TOKEN not in json.dumps(x)                                   # giao diện không thấy token
    assert TOKEN not in kenh_du_phong._path().read_text(encoding="utf-8")  # trên đĩa cũng mã hoá
    assert kenh_du_phong.lay() == (TOKEN, "8980648636, -1001234567890")


def test_khong_ghi_de_ban_tot_bang_ban_rong():
    kenh_du_phong.luu(TOKEN, "1", "tay")
    assert kenh_du_phong.luu("", "2", "tay") is False
    assert kenh_du_phong.tu_dong("", "2") is False
    assert kenh_du_phong.lay() == (TOKEN, "1")


def test_tu_dong_chi_ghi_khi_khac():
    assert kenh_du_phong.tu_dong(TOKEN, "1") is True
    assert kenh_du_phong.tu_dong(TOKEN, "1") is False                    # y hệt: không ghi lại
    assert kenh_du_phong.tu_dong(TOKEN, "1, 2") is True                  # thêm chat ID: cập nhật
    assert kenh_du_phong.xem()["nguon"] == "tu-dong"


def _blob_token():
    return json.loads(cfgmod.SETTINGS_PATH.read_text(encoding="utf-8"))["telegram"]["token"]


def test_khoa_hong_thi_khong_xoa_trang_token(monkeypatch):
    s = cfgmod.read_settings()
    s["telegram"] = {"enabled": True, "token": TOKEN, "chat_id": "1"}
    cfgmod.write_settings(s)
    blob = _blob_token()
    assert blob.startswith(("enc:", "plain:"))
    if not blob.startswith("enc:"):
        pytest.skip("máy test thiếu cryptography: không có blob enc: để thử")
    # Giả lập khoá hỏng: mọi lần giải mã ra rỗng, nên read_settings đọc token = "".
    monkeypatch.setattr(secrets_store, "decrypt", lambda v: "" if str(v).startswith("enc:") else (v or ""))
    s2 = json.loads(cfgmod.SETTINGS_PATH.read_text(encoding="utf-8"))
    s2["telegram"]["token"] = ""                                        # thứ read_settings sẽ trả
    s2["model"] = {"provider": "x"}                                     # một lần ghi bất kỳ khác
    cfgmod.write_settings(s2)
    assert _blob_token() == blob                                        # blob cũ còn nguyên


def test_khoa_tot_thi_xoa_chu_dong_van_duoc():
    s = cfgmod.read_settings()
    s["telegram"] = {"enabled": True, "token": TOKEN, "chat_id": "1"}
    cfgmod.write_settings(s)
    s = cfgmod.read_settings()
    assert s["telegram"]["token"] == TOKEN
    s["telegram"]["token"] = ""
    cfgmod.write_settings(s)
    assert _blob_token() == ""


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
