# -*- coding: utf-8 -*-
"""kenh_du_phong.py - bản dự phòng token và chat ID của kênh Telegram (1.3.10).

Chủ studio mất token bot Telegram trong settings.json (15/10) và phải xin lại ở BotFather. File
này giữ một bản RIÊNG ở STATE_DIR/kenh_du_phong.json: settings.json có bị xoá trắng thì bản này
vẫn còn, bấm "Dùng lại" là bot chạy lại.

- Token mã hoá bằng secrets_store (cùng khoá máy với settings.json), không bao giờ trả ra ngoài
  nguyên văn: giao diện chỉ thấy 4 ký tự cuối.
- Tự cập nhật khi bot chạy được thật (gửi test thành công, hoặc bot đang nhận tin) và cấu hình
  khác bản đang giữ. Bấm tay "Lưu bản dự phòng" cũng được.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import config as cfgmod

_LOCK = threading.Lock()


def _path() -> Path:
    return Path(cfgmod.STATE_DIR) / "kenh_du_phong.json"


def _doc() -> dict:
    try:
        d = json.loads(_path().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ghi(d: dict) -> None:
    p = _path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def xem(kenh: str = "telegram") -> dict:
    """Thông tin để hiện lên giao diện: KHÔNG có token, chỉ 4 ký tự cuối."""
    b = _doc().get(kenh) or {}
    if not b.get("token"):
        return {"co": False}
    return {"co": True, "chat_id": b.get("chat_id") or "", "token_cuoi": b.get("token_cuoi") or "",
            "luc": b.get("luc") or 0, "nguon": b.get("nguon") or ""}


def lay(kenh: str = "telegram") -> tuple:
    """(token, chat_id) đã giải mã, để khôi phục. Token rỗng = không có hoặc không giải mã được."""
    import secrets_store
    b = _doc().get(kenh) or {}
    return secrets_store.decrypt(b.get("token") or ""), str(b.get("chat_id") or "")


def luu(token: str, chat_id: str, nguon: str, kenh: str = "telegram") -> bool:
    """Ghi bản dự phòng. Token rỗng thì không ghi (không bao giờ ghi đè bản tốt bằng bản rỗng)."""
    import secrets_store
    token = str(token or "").strip()
    if not token:
        return False
    with _LOCK:
        d = _doc()
        d[kenh] = {"token": secrets_store.encrypt(token), "token_cuoi": token[-4:],
                   "chat_id": str(chat_id or "").strip(), "luc": int(time.time()), "nguon": nguon}
        _ghi(d)
    return True


def tu_dong(token: str, chat_id: str, kenh: str = "telegram") -> bool:
    """Cập nhật bản dự phòng khi cấu hình đang CHẠY ĐƯỢC khác bản đang giữ. Trả True nếu có ghi."""
    token = str(token or "").strip()
    if not token:
        return False
    cu_token, cu_chat = lay(kenh)
    if cu_token == token and cu_chat == str(chat_id or "").strip():
        return False
    return luu(token, chat_id, "tu-dong", kenh)
