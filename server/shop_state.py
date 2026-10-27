"""Quản lý Shop: lưu trạng thái của trang `dashboard/quan-ly-shop.html` lên máy chủ.

Trang mẫu đó giữ dữ liệu của 12 module (đơn bán, kho, thu chi, nhân sự, báo giá, chat nội bộ, ...) trong
localStorage của trình duyệt, nên mỗi máy một bản và xoá cache là mất. Ở đây máy chủ giữ MỘT bản chung:
console.js kéo bản này xuống trước khi mở trang, và đẩy lên mỗi khi trang ghi lại (sự kiện `storage`).

Chỉ lưu đúng bốn khoá của trang mẫu, mỗi khoá là một chuỗi JSON. Dữ liệu có thu chi và nhân sự nên chỉ
admin hoặc quản lý (ceo, giám đốc, trưởng phòng, lead) đọc và ghi được; nhân viên khác nhận 403.
Hai máy cùng sửa một lúc thì bản ghi sau cùng thắng (không có hợp nhất từng dòng).
"""
from __future__ import annotations

import json
import os
import time

from fastapi import APIRouter, Form, HTTPException, Request

import config as cfgmod

router = APIRouter()

KEYS = ("joyce-shop-org", "joyce-shop-sample", "joyce-shop-business", "joyce-shop-chat")
QUAN_LY = ("ceo", "giam_doc", "truong_phong", "lead")
TOI_DA = 2_000_000          # byte cho toàn bộ trạng thái; vượt thì từ chối thay vì cắt cụt dữ liệu


def _duong_dan():
    return cfgmod.STATE_DIR / "shop_state.json"


def doc() -> dict:
    try:
        d = json.loads(_duong_dan().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def ghi(keys: dict) -> dict:
    sach = {}
    for k in KEYS:
        v = keys.get(k)
        if v is None:
            continue
        if not isinstance(v, str):
            raise ValueError("Giá trị của " + k + " phải là chuỗi JSON")
        json.loads(v)       # sai JSON thì ném lỗi ngay, không lưu rác
        sach[k] = v
    if sum(len(v) for v in sach.values()) > TOI_DA:
        raise ValueError("Dữ liệu Quản lý Shop quá lớn")
    out = {"keys": sach, "updated": int(time.time())}
    p = _duong_dan()
    tam = p.with_name(p.name + ".tmp")
    tam.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    os.replace(tam, p)
    return out


def _kiem_quyen(request: Request) -> None:
    st = getattr(request.state, "staff", None) or {}
    if st and str(st.get("role") or "") not in QUAN_LY:
        raise HTTPException(403, "Chỉ chủ hoặc quản lý xem được dữ liệu Quản lý Shop")


@router.get("/shop/state")
async def shop_state_get(request: Request):
    _kiem_quyen(request)
    d = doc()
    return {"ok": True, "keys": d.get("keys") or {}, "updated": d.get("updated") or 0}


@router.post("/shop/state")
async def shop_state_set(request: Request, data: str = Form(...)):
    _kiem_quyen(request)
    try:
        keys = json.loads(data)
        if not isinstance(keys, dict):
            raise ValueError("Dữ liệu phải là một object")
        d = ghi(keys)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "updated": d["updated"]}


def register(app) -> None:
    app.include_router(router)
