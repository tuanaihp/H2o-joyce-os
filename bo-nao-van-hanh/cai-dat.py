"""Cài bộ não vận hành Joyce vào một thư mục brain bất kỳ.

    python cai-dat.py <thu-muc-brain>

Chỉ TẠO file còn thiếu, không bao giờ ghi đè file đã có: chạy lại nhiều lần vô hại, và
không làm mất ghi chú, wiki hay trí nhớ của dự án đã có sẵn.
"""
import pathlib
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

KHUNG = pathlib.Path(__file__).resolve().parent / "khung"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dich = pathlib.Path(sys.argv[1]).expanduser().resolve()
    dich.mkdir(parents=True, exist_ok=True)
    tao, bo_qua = 0, 0
    for nguon in KHUNG.rglob("*"):
        if not nguon.is_file():
            continue
        rel = nguon.relative_to(KHUNG)
        dest = dich / rel
        if dest.exists():
            bo_qua += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nguon, dest)
        tao += 1
    print(f"Đã cài vào: {dich}")
    print(f"  tạo mới: {tao} file · giữ nguyên (đã có): {bo_qua} file")
    print("Bước tiếp: mở thư mục này trong Joyce (chọn làm brain) để Joyce tự sinh Joyce/index.md")
    print("và đồng bộ bản skill hệ thống theo phiên bản.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
