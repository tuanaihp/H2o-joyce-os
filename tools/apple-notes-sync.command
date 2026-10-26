#!/bin/bash
# =============================================================================
# Đồng bộ Apple Notes -> Joyce OS   (chạy trên macOS)
#
# CÁCH DÙNG
#   1. Copy file này sang MacBook (đặt đâu cũng được, ví dụ Desktop).
#   2. Mở file, ĐIỀN giá trị vào giữa hai dấu " của 2 dòng dưới chữ CẤU HÌNH
#      (dòng không bắt đầu bằng #). Ví dụ sau khi điền xong trông như này:
#         JOYCE_URL="https://abc-xyz.trycloudflare.com"
#         TOKEN="japn_AbC123xyz"
#      JOYCE_URL = link tunnel Joyce gửi qua Telegram (KHÔNG gạch chéo cuối).
#      TOKEN = lấy ở http://127.0.0.1:7777/ext/apple-notes/ trên máy chạy Joyce.
#      Không muốn ghi vào file: đặt biến môi trường JOYCE_URL / JOYCE_NOTES_TOKEN.
#   3. Double-click (lần đầu macOS có thể hỏi quyền: chuột phải > Open), hoặc
#      chạy trong Terminal:  bash apple-notes-sync.command
#
# LỆNH TERMINAL (copy-dán, khỏi nhớ)
#   Mở Terminal:  Cmd + Space -> gõ "terminal" -> Enter
#   Chạy:         bash ~/Downloads/apple-notes-sync.command
#   Chạy lại:     bấm phím mũi tên lên rồi Enter (hiện lại lệnh vừa chạy)
#   File bị đổi tên khi tải trùng:
#                 ls ~/Downloads/apple-notes-sync*      (chạy bản mới nhất)
#   Dọn bản cũ:   rm -f ~/Desktop/apple-notes-sync.command \
#                       ~/Downloads/apple-notes-sync*.command
#
#   Mỗi lần chạy hiện hộp thoại CHỌN THƯ MỤC của macOS (chọn nhiều bằng Cmd-click)
#   -> chỉ các thư mục đã tick được gửi. Notes nằm trong thư mục con là một mục
#   riêng trong danh sách - muốn đồng bộ cả nhánh thì tick cả con.
#
# TỰ ĐỘNG HOÁ (không hỏi chọn): điền sẵn tên thư mục vào FOLDERS bên dưới, rồi
# chạy tay hoặc treo launchd/cron. Hoặc truyền tham số:
#      bash apple-notes-sync.command "iCloud/Work" "On My Mac/Personal"
#
# Yêu cầu: macOS có python3 (có sẵn nếu đã cài Xcode Command Line Tools;
# thiếu thì chạy: xcode-select --install). Không cần cài thêm gì khác.
# LƯU Ý: file chứa TOKEN = chìa ghi note vào brain - đừng đăng lên nơi công khai.
# =============================================================================

# ----------------------------- CẤU HÌNH ------------------------------------
JOYCE_URL=""        # <=== DÁN link tunnel vào giữa "" (vd "https://abc.trycloudflare.com")
TOKEN=""            # <=== DÁN token japn_... vào giữa ""
[ -z "$JOYCE_URL" ] && JOYCE_URL="${JOYCE_URL_ENV:-}"      # để trống thì lấy biến môi trường
[ -z "$TOKEN" ] && TOKEN="${JOYCE_NOTES_TOKEN:-}"
DEVICE_NAME="MacBook"

# Thư mục đồng bộ sẵn (đường đầy đủ dạng "Tài khoản/Thư mục/Con"), để trống ()
# thì mỗi lần chạy hiện hộp chọn. Ví dụ: FOLDERS=("iCloud/Công việc")
FOLDERS=()

# ---------------------------------------------------------------------------
export JOYCE_URL TOKEN DEVICE_NAME
echo "=== apple-notes-sync v2 (fix loi ngay locale VN) ==="
# Có tham số dòng lệnh HOẶC FOLDERS điền sẵn -> đồng bộ thẳng, không hiện hộp chọn.
python3 - "$@" "${FOLDERS[@]}" <<'PYEOF'

import json
import os
import subprocess
import sys
import tempfile
import urllib.request

JOYCE_URL = (os.environ.get("JOYCE_URL") or "").rstrip("/")
TOKEN = os.environ.get("TOKEN") or ""
DEVICE = os.environ.get("DEVICE_NAME") or "MacBook"
ENDPOINT = "/ext/apple-notes/push"

FS = chr(31)   # tách trường trong một bản ghi note
RS = chr(30)   # tách các note / các mục truyền qua argv


# ---------------------------------------------------------------- AppleScript
SCPT_FOLDERS = r'''
on add_folder(f, prefix, lst)
    tell application "Notes"
        set p to prefix & (name of f)
        set end of lst to p
        repeat with sf in folders of f
            my add_folder(sf, p & "/", lst)
        end repeat
    end tell
end add_folder

on run
    set lst to {}
    tell application "Notes"
        repeat with acc in accounts
            set acc_name to name of acc
            repeat with f in folders of acc
                my add_folder(f, acc_name & "/", lst)
            end repeat
        end repeat
    end tell
    set out to ""
    repeat with i in lst
        set out to out & i & linefeed
    end repeat
    return out
end run
'''

SCPT_CHOOSE = r'''
on run argv
    set tid to AppleScript's text item delimiters
    set AppleScript's text item delimiters to ASCII character 30
    set lst to text items of (item 1 of argv)
    set AppleScript's text item delimiters to tid
    set c to choose from list lst with prompt "Chọn thư mục Notes để đồng bộ lên Joyce:" ¬
        with multiple selections allowed
    if c is false then return ""
    set out to ""
    repeat with i in c
        set out to out & i & linefeed
    end repeat
    return out
end run
'''

SCPT_DUMP = r'''
on split(txt, d)
    set tid to AppleScript's text item delimiters
    set AppleScript's text item delimiters to d
    set parts to text items of txt
    set AppleScript's text item delimiters to tid
    return parts
end split

on pad2(n)
    return text -2 thru -1 of ("0" & (n as integer))
end pad2

on dstr(d)
    -- "1970-01-02T03:04:05" theo giờ máy - không phụ thuộc locale như parse chuỗi ngày
    return (year of d) & "-" & my pad2(month of d as integer) & "-" & my pad2(day of d) & ¬
        "T" & my pad2(hours of d) & ":" & my pad2(minutes of d) & ":" & my pad2(seconds of d)
end dstr

on run argv
    set segs to my split(item 1 of argv, "/")
    set fs to ASCII character 31
    set rs to ASCII character 30
    set out to ""
    tell application "Notes"
        set cur to account (item 1 of segs)
        repeat with i from 2 to (count of segs)
            set cur to folder (item i of segs) of cur
        end repeat
        repeat with n in notes of cur
            try
                set out to out & (id of n) & fs & (name of n) & fs & ¬
                    my dstr(creation date of n) & fs & ¬
                    my dstr(modification date of n) & fs & ¬
                    (plaintext of n) & rs
            end try
        end repeat
    end tell
    return out
end run
'''


def chay_scpt(src, *args, timeout=300):
    """Chạy một đoạn AppleScript, trả stdout (utf-8). Ném lỗi có lý do khi hỏng."""
    with tempfile.NamedTemporaryFile("w", suffix=".scpt", delete=False,
                                     encoding="utf-8") as fp:
        fp.write(src)
        duong = fp.name
    try:
        r = subprocess.run(["osascript", duong, *args],
                           capture_output=True, timeout=timeout)
    finally:
        try:
            os.unlink(duong)
        except OSError:
            pass
    if r.returncode != 0:
        loi = r.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"AppleScript lỗi: {loi or 'không rõ'}")
    return r.stdout.decode("utf-8", "replace")


def main():
    if sys.platform != "darwin":
        sys.exit("Script này chỉ chạy trên macOS (iPhone thì dùng app Shortcuts).")
    if not JOYCE_URL or not TOKEN:
        sys.exit("Chưa điền JOYCE_URL / TOKEN ở đầu file (hoặc biến môi trường "
                 "JOYCE_URL / JOYCE_NOTES_TOKEN).")

    # 1. Thư mục: tham số dòng lệnh > hộp chọn của macOS
    chon = [a for a in sys.argv[1:] if a.strip()]
    if not chon:
        print("Đang đọc danh sách thư mục Notes...")
        raw = chay_scpt(SCPT_FOLDERS)
        tat_ca = sorted({d.strip() for d in raw.splitlines() if d.strip()})
        if not tat_ca:
            sys.exit("Không đọc được thư mục nào. Lần đầu chạy macOS có thể hỏi "
                     "quyền cho Terminal/script điều khiển Notes - hãy Allow.")
        chon = [d.strip() for d in
                chay_scpt(SCPT_CHOOSE, RS.join(tat_ca)).splitlines() if d.strip()]
        if not chon:
            print("Không chọn thư mục nào - thoát.")
            return

    # 2. Gom notes từng thư mục
    folders = {}
    for duong in chon:
        try:
            raw = chay_scpt(SCPT_DUMP, duong)
        except Exception as e:
            print(f"  ! Bỏ qua '{duong}': {e}")
            continue
        notes = []
        for rec in raw.split(RS):
            if not rec.strip():
                continue
            f = (rec.split(FS) + ["", "", "", "", ""])[:5]
            nid, tieu_de, tao, sua, than = [x.strip() if i < 4 else x
                                            for i, x in enumerate(f)]
            notes.append({"id": nid, "title": tieu_de,
                          "created": tao, "modified": sua, "body": than})
        folders[duong] = notes
        print(f"  {duong}: {len(notes)} note")

    if not folders:
        sys.exit("Không gom được thư mục nào.")

    # 3. POST lên Joyce
    body = json.dumps({"device": DEVICE, "folders": folders},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(JOYCE_URL + ENDPOINT, data=body, method="POST",
                                 headers={"Authorization": "Bearer " + TOKEN,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            kq = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"Joyce trả lỗi {e.code}: {e.read().decode('utf-8', 'replace')[:300]}\n"
                 "(sai token? URL tunnel đã đổi?)")
    except Exception as e:
        sys.exit(f"Không gọi được Joyce ({e}). Kiểm tra link tunnel còn sống không "
                 "- nhắn 'gửi link' cho Joyce trên Telegram để lấy link mới.")

    print("\nXong:", json.dumps(kq, ensure_ascii=False))


main()
PYEOF
