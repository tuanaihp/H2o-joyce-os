"""A07.1 (gói A): `cryptography` nạp lười trong webpush nhưng Web Push vẫn chạy, kể cả khi nhiều luồng gọi lần đầu cùng lúc.

    python tests/run.py a07_nap_luoi_webpush      (không mạng)

Chạy trong tiến trình con sạch để chắc chắn đây đúng là lần nạp đầu tiên của cryptography.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import subprocess
import sys
import tempfile

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


MA = r'''
import os, sys, threading, base64
sys.path.insert(0, %r)
import webpush
assert "cryptography" not in sys.modules, "import webpush không được nạp cryptography"
from cryptography.hazmat.primitives.asymmetric import ec   # chỉ để dựng một đăng ký giả; làm SAU khi đã kiểm. Các tên của webpush vẫn là None cho tới lần gọi đầu
kq, loi = [], []
def b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
pk = ec.generate_private_key(ec.SECP256R1())
from cryptography.hazmat.primitives import serialization
pub = b64(pk.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
auth = b64(os.urandom(16))
def lam():
    try:
        kq.append(webpush.ma_hoa(b"xin chao", pub, auth))
    except BaseException as e:
        loi.append(repr(e))
ts = [threading.Thread(target=lam) for _ in range(12)]
for t in ts: t.start()
for t in ts: t.join()
print("KQ", len(kq), "LOI", loi[:2])
'''

r = subprocess.run([sys.executable, "-c", MA % str(SERVER)], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, JOYCE_STATE_DIR=tempfile.mkdtemp(prefix="joyce-a07-wp-")))
check("import webpush KHÔNG nạp cryptography", r.returncode == 0 or "KQ" in r.stdout, r.stderr[-300:])
check("12 luồng gọi ma_hoa lần đầu cùng lúc: cả 12 mã hoá được, không luồng nào thấy tên chưa nạp", "KQ 12 LOI []" in r.stdout, (r.stdout, r.stderr[-300:]))

print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_a07_nap_luoi_webpush: tất cả pass")
