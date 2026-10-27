"""Plugin bundled: tool `joyce_shop` - ghi sổ Quản lý Shop và CRM từ chat, qua agent từng phòng.

Vai của bộ não tổng (Joyce) ở đây là LỄ TÂN: đọc câu của chủ, tách thành các sự kiện có cấu trúc,
rồi gọi tool này MỘT lần. Việc ghi sổ và định tuyến về phòng phụ trách (Sales, Thu, Chi, Đối Soát,
Nhân Sự) do `shop_so.xu_ly` làm bằng luật cố định, nên một câu không tốn thêm lượt model nào. Agent
trưởng phòng chỉ được giao một việc Kanban khi cần phán đoán (chi của nhân viên vượt hạn mức, hợp
đồng hoàn thành cần báo cáo đối soát).

Người báo là chủ hay nhân viên được lấy từ phiên chat (không tin tham số do model tự khai): nhân
viên báo khoản chi từ hạn mức trở lên thì khoản đó nằm "chờ duyệt".
"""
from __future__ import annotations

import json
import sys

import shop_so

try:
    import luot_dang_chay
except Exception:          # chạy ngoài máy chủ
    luot_dang_chay = None

_LOAI = ("hop_dong", "thu", "chi", "viec", "phan_cong", "giao_viec", "thue_do", "tra_do")


def _la_nhan_vien() -> bool:
    """Lượt chat này của nhân viên (đã bị khoá vào phạm vi phòng) hay của chủ."""
    m = sys.modules.get("main")
    try:
        return m is not None and m._STAFF_SCOPE.get() is not None
    except Exception:
        return False


def _ghi(args, ctx) -> str:
    ev = (args or {}).get("su_kien")
    if isinstance(ev, str):
        try:
            ev = json.loads(ev)
        except Exception:
            return "ERROR: su_kien phải là danh sách object (JSON hợp lệ)."
    if isinstance(ev, dict):
        ev = [ev]
    if not isinstance(ev, list) or not ev:
        return ("ERROR: thiếu su_kien. Mỗi sự kiện là một object có `loai` (hop_dong | thu | chi | viec | phan_cong | giao_viec | thue_do | tra_do). "
                "Ví dụ: [{loai:'hop_dong', ten:'Tuấn Thủy', sdt:'0899252392', goi:'Gói chụp ảnh studio', gia_tri:15000000}, "
                "{loai:'thu', so_tien:15000000, khach:'0899252392'}, {loai:'chi', so_tien:4000000, dien_giai:'Setup', khach:'0899252392'}]")
    chat_id = str((args or {}).get("chat_id") or "").strip()
    if not chat_id and luot_dang_chay is not None and ctx.vault_root:
        try:
            chat_id = luot_dang_chay.doan_chat_id(ctx.vault_root) or ""
        except Exception:
            chat_id = ""
    by_info = {"role": "nhan_vien"} if _la_nhan_vien() else {}
    r = shop_so.xu_ly(ev, "Joyce", chat_id, by_info)
    ra = []
    for k in r["ket_qua"]:
        ra.append("- " + k.get("tom_tat", k.get("loai", "")))
        if k.get("giao_agent"):
            ra.append("  " + k["giao_agent"])
    for e in r["loi"]:
        ra.append(f"- LỖI sự kiện {e['stt']} ({e.get('loai', '')}): {e['loi']}. Chưa ghi sự kiện này; hỏi lại chủ phần còn thiếu.")
    if r["ket_qua"]:
        ra.append("Xem ở trang Quản lý Shop (Vận hành kinh doanh); các agent vừa làm hiện trên văn phòng ảo.")
    return "\n".join(ra)


def _xem(args, ctx) -> str:
    ky = str((args or {}).get("ky") or "").strip()
    t = shop_so.tong_quan(ky)
    hd = t["hop_dong"]
    d = shop_so._vnd
    ra = [f"Kỳ {t['ky']}: thu {d(t['thu'])}đ, chi {d(t['chi'])}đ, lãi gộp {d(t['lai_gop'])}đ.",
          f"Hợp đồng: {hd['bao_gia']} báo giá (tiềm năng {d(t['pipeline'])}đ), {hd['da_ky']} đã ký, {hd['hoan_thanh']} hoàn thành, {hd['huy']} hủy.",
          f"Công nợ phải thu {d(t['cong_no'])}đ. Lương và hoa hồng tạm tính {d(t['luong'])}đ."]
    if t["cho_duyet"]:
        ra.append(f"CÓ {t['cho_duyet']} khoản chi chờ chủ duyệt ({d(t['cho_duyet_tien'])}đ): duyệt ở trang Thu chi.")
    if t["viec_qua_han"]:
        ra.append(f"{t['viec_qua_han']} việc quá hạn.")
    return "\n".join(ra)


def _bao_cao(args, ctx) -> str:
    hd, canh_bao = shop_so.tim_hop_dong((args or {}).get("hop_dong"))
    if not hd:
        return "ERROR: " + (canh_bao or "thiếu hop_dong (mã HD0001, số điện thoại hoặc tên khách).")
    return shop_so.giao_bao_cao(hd["id"], str((args or {}).get("chat_id") or "").strip())


def _do(args, ctx) -> str:
    """Tra danh mục đồ: đồ còn trống hay đang thuê, giữ chỗ những ngày nào."""
    d = shop_so._vnd
    ten = {"san_sang": "sẵn sàng", "giu_cho": "có người giữ chỗ", "dang_thue": "ĐANG THUÊ", "qua_han": "QUÁ HẠN chưa trả", "tam_ngung": "tạm ngưng", "dang_giat": "đang giặt phơi"}
    ds = shop_so.goi_y_do(str((args or {}).get("tu_khoa") or ""))
    if not ds:
        return "Danh mục đồ không có món nào khớp. Nói rõ hơn mã hoặc loại đồ, hoặc xem tab Danh mục đồ."
    ra = []
    for x in ds:
        dong = f"- {x['ten_do']} ({x['nhom']}{', cỡ ' + x['co'] if x['co'] else ''}) {d(x['don_gia'])}đ/lần, thuê {x['so_lan_thue']} lần: {ten[x['tinh_trang']]}{', sẵn sàng từ ' + shop_so._dmy(x['san_lai']) if x.get('san_lai') else ''}"
        if x["lich"]:
            dong += "; lịch " + ", ".join(f"{v['tu']} đến {v['den']} ({v['khach']})" for v in x["lich"])
        ra.append(dong)
    return "\n".join(ra)


def _gia(args, ctx) -> str:
    """Tra bảng giá dịch vụ: khách hỏi giá một gói thì đọc đúng số trong bảng, không tự bịa."""
    d = shop_so._vnd
    ds = shop_so.goi_y_dich_vu(str((args or {}).get("tu_khoa") or ""))
    if not ds:
        return "Bảng giá không có gói nào khớp. Nói rõ hơn tên gói hoặc loại dịch vụ, hoặc xem tab Bảng giá & hoa hồng."
    ra = []
    for v in ds:
        if v["don_gia"] <= 0:
            ra.append(f"- {v['ma']} ({v['loai']}) {v['goi']}: chưa có giá trong bảng, báo giá theo yêu cầu.")
            continue
        dong = f"- {v['ma']} ({v['loai']}) {v['goi']}: {d(v['don_gia'])}đ"
        if v["coc1_pct"] or v["coc2_pct"]:
            dong += f"; cọc lần 1 {d(v['coc1'])}đ ({v['coc1_pct']:g}%), cọc lần 2 {d(v['coc2'])}đ ({v['coc2_pct']:g}%), thanh toán cuối {d(v['con_lai'])}đ"
        ra.append(dong)
    return "\n".join(ra)


async def _chay(args, ctx) -> str:
    op = str((args or {}).get("op") or "").strip().lower()
    try:
        if op == "ghi":
            return _ghi(args, ctx)
        if op == "xem":
            return _xem(args, ctx)
        if op == "bao_cao":
            return _bao_cao(args, ctx)
        if op == "gia":
            return _gia(args, ctx)
        if op == "do":
            return _do(args, ctx)
    except Exception as e:
        return f"ERROR: không ghi được ({type(e).__name__}: {e})."
    return "ERROR: op phải là 'ghi' (ghi sự kiện), 'xem' (số liệu kỳ này), 'bao_cao' (giao Đối Soát báo cáo một hợp đồng) 'gia' (tra bảng giá dịch vụ) hoặc 'do' (tra đồ còn trống hay đang thuê)."


def register(ctx):
    ctx.register_tool(
        "joyce_shop",
        "Ghi vào SỔ Quản lý Shop và CRM khi chủ báo một việc kinh doanh: có khách mới hay hợp đồng, báo giá, "
        "đã THU tiền, đã CHI tiền, một việc cần làm, hoặc phân công nhân sự. Bạn chỉ ĐỌC câu và tách thành sự kiện; "
        "tool tự định tuyến về đúng phòng (Sales, Phòng Thu, Phòng Chi, Đối Soát, Nhân Sự), tự tìm khách theo số "
        "điện thoại để không tạo trùng, và hiện agent của phòng đó trên văn phòng ảo. KHÔNG tự bịa số: thiếu số tiền "
        "hay không rõ thu hay chi thì HỎI LẠI một câu, đừng ghi. Một câu nhiều ý thì gom hết vào MỘT lần gọi. "
        "op=ghi: su_kien là danh sách object, mỗi cái có loai: "
        "hop_dong {ten, sdt, goi (tên gói/dịch vụ), gia_tri, thuong_hieu ('h2o' mặc định hoặc 'thuyh2o'), "
        "trang_thai ('bao_gia' mặc định, hoặc da_ky)}; "
        "thu {so_tien, khach (số điện thoại, mã HD0001 hoặc tên để gắn hợp đồng), hang_muc, dien_giai}; "
        "chi {so_tien, khach, hang_muc, dien_giai}; viec {tieu_de, han (YYYY-MM-DD), giao_cho, hop_dong}; "
        "phan_cong {hop_dong, ten, vai: sales|chup|makeup|hotro}; "
        "giao_viec {hop_dong, cong_viec (tên đầu việc trong bảng hoa hồng, vd 'Makeup cô dâu'), ten (nhân sự), so_luong (mặc định 1), han}: "
        "chia một đầu việc của hợp đồng cho một người, hoa hồng cố định theo bảng và tự vào bảng lương. Số tiền là số đồng (15 triệu = 15000000). "
        "Nhận thu cọc của hợp đồng đang báo giá thì hợp đồng tự chuyển Đã ký. Gửi lại cùng một sự kiện trong 10 phút "
        "không bị ghi hai lần. Khoản chi nhân viên báo từ hạn mức trở lên nằm 'chờ duyệt' cho chủ; chủ báo thì ghi luôn. "
        "op=xem: số liệu thu chi, hợp đồng, công nợ của kỳ (ky=YYYY-MM hoặc all). "
        "op=bao_cao: giao phòng Đối Soát lập báo cáo lãi lỗ một hợp đồng (hop_dong). "
        "thue_do {ma_do (như VAY-CC209), hop_dong (mã/sđt/tên để gắn khách) hoặc ten_khach+sdt, ngay_thue, ngay_tra, khuyen_mai, thu_ngay (true = ghi luôn khoản thu còn lại)}: "
        "cho khách thuê hoặc giữ chỗ một món đồ, tự chặn nếu đồ đã có người thuê hay giữ chỗ trùng ngày; "
        "tra_do {ma_do hoặc key}: nhận đồ trả về, báo nếu trễ hạn. "
        "op=do: tra danh mục ĐỒ theo tu_khoa (mã, loại, màu): còn trống hay đang thuê, lịch giữ chỗ. "
        "op=gia: tra BẢNG GIÁ dịch vụ theo tu_khoa (mã như PRW-STCB hoặc tên/loại gói); khách hỏi giá thì đọc đúng số này, không tự bịa. "
        "Khi lập hop_dong, goi là đúng MÃ hoặc đúng TÊN gói trong bảng giá thì không cần nói gia_tri, sổ tự lấy giá và cọc theo bảng; "
        "chủ nói giá khác (thương lượng) thì dùng giá chủ nói. "
        "Kết quả chỉ nói việc ĐÃ ghi; nếu có dòng 'điều phối đang off' thì nói thẳng với chủ, đừng hứa agent đang chạy.",
        _chay,
        schema={
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": ["ghi", "xem", "bao_cao", "gia", "do"]},
                "tu_khoa": {"type": "string", "description": "Mã, tên hoặc loại gói/đồ cần tra (op=gia hoặc op=do)"},
                "su_kien": {"type": "array", "items": {"type": "object", "properties": {
                    "loai": {"type": "string", "enum": list(_LOAI)}}, "required": ["loai"]},
                    "description": "Danh sách sự kiện kinh doanh (op=ghi)"},
                "ky": {"type": "string", "description": "YYYY-MM hoặc all (op=xem)"},
                "hop_dong": {"type": "string", "description": "Mã HD0001, số điện thoại hoặc tên khách (op=bao_cao)"},
                "chat_id": {"type": "string", "description": "Người nhận kết quả việc giao cho agent, vd web:<mã phiên>"},
            },
            "required": ["op"],
        },
        min_mode="safe",
        emoji="🧾",
    )
