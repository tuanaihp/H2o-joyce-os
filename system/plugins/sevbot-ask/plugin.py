"""Plugin bundled: Sevbot hỏi-đáp về sự cố (OpenAI Sevbot answering questions).

Sevbot của OpenAI trong lúc outage gom context và TRẢ LỜI CÂU HỎI trong kênh sự cố,
nhưng không tự hành động khắc phục. Tool này cho agent đọc context sự cố của brain
hiện tại để trả lời kiểu đó. Mọi hành động khắc phục vẫn là việc của incident_desk
(retry/person/quiet) - tool này chỉ đọc, min_mode readonly.

Nguồn dữ liệu: incident_desk singleton của server (plugin chạy trong tiến trình
server nên import trực tiếp; nếu chạy ngoài tiến trình thì trả lỗi thân thiện).
"""
from __future__ import annotations

import json
from pathlib import Path


def _brain_name(ctx) -> str:
    try:
        return Path(str(ctx.vault_root)).name
    except Exception:
        return ""


def _list_incidents(ctx):
    try:
        import incident_desk  # module của server
        desk = incident_desk.current()
        if desk is None:
            return None
        return desk.list(_brain_name(ctx), 50) or []
    except Exception:
        return []


def _fmt(inc: dict) -> dict:
    """Rút các trường hữu ích để agent đọc nhanh, bỏ trường nội bộ."""
    return {
        "id": inc.get("id"),
        "title": inc.get("title") or inc.get("source"),
        "brain": inc.get("brain"),
        "status": inc.get("status"),
        "count": inc.get("count"),
        "error": str(inc.get("error") or "")[:400],
        "first_seen": inc.get("first_seen") or inc.get("created_at"),
        "last_seen": inc.get("last_seen") or inc.get("updated_at"),
        "decision": inc.get("decision"),
        "decided_by": inc.get("decided_by"),
        "note": str(inc.get("note") or "")[:400],
        "retries": inc.get("retries"),
        "request": str(inc.get("request") or "")[:300],
    }


def _sevbot_ask(args, ctx):
    args = args or {}
    items = _list_incidents(ctx)
    if items is None:
        return ("ERROR: plugin này chỉ chạy được trong tiến trình server Joyce "
                "(cần incident_desk). Ngoài server không đọc được sự cố.")

    iid = str(args.get("incident_id") or "").strip()
    if not iid:
        # Liệt kê sự cố đang mở (chưa resolved) để agent chọn đúng cái người hỏi.
        open_items = [_fmt(i) for i in items if i.get("status") != "resolved"]
        return json.dumps({
            "open_count": len(open_items),
            "incidents": open_items[:15],
            "hint": "Gọi lại với incident_id để đọc sâu 1 sự cố.",
        }, ensure_ascii=False)

    cur = next((i for i in items if str(i.get("id")) == iid), None)
    if cur is None:
        return json.dumps({"error": f"Không thấy sự cố id={iid} trong brain này."},
                          ensure_ascii=False)
    return json.dumps({
        "incident": _fmt(cur),
        "cung_dau_hieu": [_fmt(i) for i in items
                          if i is not cur
                          and str(i.get("source") or "") == str(cur.get("source") or "")
                          and i.get("status") != "resolved"][:5],
        "huong_dan": ("Trả lời người dùng dựa trên context này: đã xảy ra gì, bao nhiêu "
                      "lần, bàn sự cố đã quyết gì (decision/decided_by), nên làm gì. "
                      "KHÔNG được hứa tự khắc phục - hành động thuộc incident_desk/chủ."),
    }, ensure_ascii=False)


def register(ctx):
    ctx.register_tool(
        name="sevbot_ask",
        description=("Hỏi-đáp về sự cố (incident) của brain: không truyền gì → liệt kê sự cố "
                     "đang mở; truyền incident_id → đọc context đầy đủ (lỗi, số lần, quyết định "
                     "triage, các sự cố cùng dấu hiệu). Chỉ đọc - KHÔNG khắc phục. Dùng khi người "
                     "dùng hỏi 'sự cố X là gì / sao lại lỗi / xử lý chưa'."),
        handler=_sevbot_ask, min_mode="readonly",
        schema={"type": "object",
                "properties": {
                    "incident_id": {"type": "string",
                                    "description": "id sự cố cần đọc sâu; bỏ trống = liệt kê đang mở"}},
                "required": []},
    )
