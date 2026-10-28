"""Writer DÙNG CHUNG cho mọi thao tác ghi file của triển khai tự cải tiến: áp nguồn, nhân đích, lật lại, khôi phục.

A05 của gói A (docs/dev/2026-10-28-joyce-harness-g1-g2-sonnet-plan.md). Một primitive duy nhất, thay cho bốn cách ghi rời rạc.

Vì sao cần. `os.replace` làm người đọc không thấy file ghi dở, nhưng "đọc hash rồi ghi" vẫn không phải một giao dịch có điều
kiện: hai tiến trình cùng đọc một hash rồi cùng ghi thì một bản bị đè mất. Tên sao lưu theo `int(time.time())` trùng khi hai
file cùng stem ghi trong một giây. Đường dẫn sao lưu suy từ `dst.parent.parent` sai với skill nằm sâu. Không có nhật ký thì chết
giữa chừng không biết file đã ghi chưa.

Trình tự dưới khoá liên tiến trình theo đường dẫn chuẩn của đích (`ghi_co_dieu_kien`):

    1. kiểm đường dẫn: nằm trong gốc đã xác thực, KHÔNG có thành phần nào là symlink hay junction
    2. đọc lại, so với hash mong đợi (so-rồi-ghi); khác thì trả `conflict`, không ghi gì
    3. sao lưu bằng tạo-độc-quyền, tên theo deployment_id và target_id, xác minh lại hash
    4. ghi nhật ký `prepared` (before, after, backup)
    5. ghi tệp tạm cùng thư mục, fsync, `os.replace`
    6. đọc lại kiểm hash rồi ghi nhật ký `committed`

Khoá là khoá của HỆ ĐIỀU HÀNH trên một tệp khoá (msvcrt.locking, fcntl.flock): tiến trình chết thì hệ điều hành nhả khoá, không
để lại khoá mồ côi để xử lý tay. Khoá chỉ bảo vệ các writer CÙNG tuân thủ. Một trình soạn thảo hay công cụ CLI ngoài cơ chế vẫn
sửa được file trực tiếp: so-rồi-ghi phát hiện được phần lớn, không phát hiện được lần sửa nằm đúng giữa lần đọc lại và `os.replace`
(cửa sổ rất nhỏ, ghi ở plan). Route nào để editor ngoài sửa vùng này thì chưa được chứng nhận (B03).

Hash là SHA-256 trên văn bản UTF-8 đã chuẩn hoá xuống dòng (`\\r\\n` về `\\n`), nhất quán với `Path.read_text` ở mọi chỗ so sánh; file
được GHI bằng bytes xác định, không để Windows đổi `\\n` thành `\\r\\n`.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Callable, Iterable, Optional

try:
    import msvcrt  # type: ignore
except ImportError:      # POSIX
    msvcrt = None
    import fcntl  # type: ignore


class DuongKhongAnToan(Exception):
    """Đích có thành phần là symlink/junction, hoặc nằm ngoài gốc đã xác thực."""


class HetGioKhoa(Exception):
    """Không lấy được khoá trong thời hạn."""


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def doc(path: Path) -> Optional[str]:
    """Nội dung văn bản (xuống dòng chuẩn hoá) hoặc None nếu không có/không đọc được."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).is_file() else None
    except OSError:
        return None


# ---------------------------------------------------------------- khoá liên tiến trình
def _khoa_file(thu_muc: Path, khoa: str) -> Path:
    return Path(thu_muc) / (hashlib.sha256(khoa.encode("utf-8")).hexdigest()[:40] + ".lock")


@contextlib.contextmanager
def khoa(thu_muc_khoa: Path, *dich: str, het_gio: float = 30.0):
    """Khoá liên tiến trình theo một hoặc nhiều đường dẫn/tên chuẩn. Nhiều khoá luôn lấy theo thứ tự đã sắp xếp (không bế tắc).

    KHÔNG tái nhập: một tiến trình lấy lại chính khoá đang giữ sẽ chờ hết giờ. Người gọi không được lồng cùng khoá."""
    thu_muc_khoa = Path(thu_muc_khoa)
    thu_muc_khoa.mkdir(parents=True, exist_ok=True)
    tep = []
    try:
        for k in sorted({os.path.normcase(str(x)) for x in dich}):
            fd = os.open(_khoa_file(thu_muc_khoa, k), os.O_RDWR | os.O_CREAT, 0o600)
            try:
                try:
                    if os.fstat(fd).st_size == 0:
                        os.write(fd, b"\0")
                except OSError:
                    # Tiến trình khác vừa tạo file này và đã khoá byte 0: Windows từ chối ghi vào vùng đang khoá. Không sao,
                    # khoá byte 0 không cần byte đó đã tồn tại; vòng chờ bên dưới lo phần còn lại.
                    pass
                t0 = time.time()
                while True:
                    try:
                        os.lseek(fd, 0, os.SEEK_SET)
                        if msvcrt is not None:
                            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                        else:
                            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.time() - t0 > het_gio:
                            raise HetGioKhoa(f"không lấy được khoá {k} sau {het_gio}s") from None
                        time.sleep(0.02)
            except BaseException:
                os.close(fd)
                raise
            tep.append(fd)
        yield
    finally:
        for fd in reversed(tep):
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if msvcrt is not None:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                os.close(fd)


# ---------------------------------------------------------------- đường dẫn an toàn
def la_lien_ket(p: Path) -> bool:
    try:
        return p.is_symlink() or p.is_junction()
    except OSError:
        return True      # không biết thì coi là liên kết: từ chối


def duong_an_toan(goc: Path, dich: Path) -> Path:
    """Đích phải nằm TRONG gốc và KHÔNG thành phần nào từ gốc tới đích (kể cả lá nếu đã có) là symlink hoặc junction.
    Trả đường dẫn chuẩn. Ném DuongKhongAnToan nếu không chắc."""
    goc, dich = Path(goc), Path(dich)
    try:
        goc_that = Path(os.path.realpath(goc))
        # Đi từng thành phần trên đường dẫn CHƯA giải, để thấy được liên kết ở giữa đường.
        rel = Path(os.path.abspath(dich)).relative_to(Path(os.path.abspath(goc)))
    except (OSError, ValueError):
        raise DuongKhongAnToan(f"đích nằm ngoài gốc: {dich}") from None
    cur = Path(os.path.abspath(goc))
    if la_lien_ket(cur):
        raise DuongKhongAnToan(f"gốc là liên kết: {cur}")
    for phan in rel.parts:
        cur = cur / phan
        if cur.exists() or cur.is_symlink():
            if la_lien_ket(cur):
                raise DuongKhongAnToan(f"thành phần là liên kết (symlink hoặc junction): {cur}")
    ket_qua = Path(os.path.realpath(dich))
    try:
        ket_qua.relative_to(goc_that)
    except ValueError:
        raise DuongKhongAnToan(f"đích giải ra ngoài gốc: {ket_qua}") from None
    return ket_qua


# ---------------------------------------------------------------- nhật ký (receipt)
def _thu_muc_nhat_ky(goc: Path) -> Path:
    return Path(goc) / "Joyce" / "proposals" / ".deploy"


def _thu_muc_sao_luu(goc: Path) -> Path:
    return Path(goc) / "Joyce" / "proposals" / ".backup"


def _tep_nhat_ky(goc: Path, deployment_id: str, target_id: str) -> Path:
    return _thu_muc_nhat_ky(goc) / f"{deployment_id[:12]}-{target_id[:12]}.json"


def ten_sao_luu(goc: Path, dich: Path, deployment_id: str, target_id: str) -> Path:
    """Tên sao lưu DUY NHẤT theo triển khai và đích, không theo giây, và nằm dưới gốc đã xác thực (không suy từ cha của cha)."""
    return _thu_muc_sao_luu(goc) / f"{Path(dich).stem}-{deployment_id[:8]}-{target_id[:8]}.bak"


def _ghi_json_nguyen_tu(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp, "wb") as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=1).encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def doc_receipt(goc: Path, deployment_id: str, target_id: str) -> Optional[dict]:
    try:
        return json.loads(_tep_nhat_ky(goc, deployment_id, target_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- ghi có điều kiện
def _ghi_bytes_nguyen_tu(dich: Path, text: str) -> None:
    """Ghi bytes xác định (UTF-8, giữ nguyên `\\n`) vào tệp tạm cùng thư mục, fsync, rồi `os.replace`. Không để lại tệp tạm khi lỗi."""
    tmp = dich.with_name(f"{dich.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp, "wb") as f:
            f.write(text.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dich)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def ghi_co_dieu_kien(goc: Path, dich: Path, new_text: str, *, thu_muc_khoa: Path, deployment_id: str, target_id: str,
                     truoc_hash: Optional[str] = None, tao_moi: bool = False, dung_tai: Optional[Callable[[str], None]] = None) -> dict:
    """Ghi `new_text` vào `dich` nếu và chỉ nếu nội dung hiện tại còn đúng `truoc_hash` (SHA-256 đầy đủ). Trả receipt.

    `ket_qua` của receipt: `committed` | `conflict` (đích đã đổi) | `missing` (đích không còn, và không cho tạo mới).
    `dung_tai(buoc)` chỉ cho test: gọi ở các mốc `sau_sao_luu`, `sau_nhat_ky`, `sau_ghi` để mô phỏng chết giữa chừng.
    Ném DuongKhongAnToan / HetGioKhoa; lỗi I/O khác lan ra, và file đích KHÔNG bị ghi dở (chỉ `os.replace` đổi file)."""
    goc, dich = Path(goc), Path(dich)
    that = duong_an_toan(goc, dich)
    sau_hash = sha256(new_text)
    with khoa(thu_muc_khoa, str(that)):
        hien = doc(that)
        rc = {"deployment_id": deployment_id, "target_id": target_id, "duong_dan": str(that), "truoc_hash": sha256(hien) if hien is not None else "",
              "sau_hash": sau_hash, "backup": "", "backup_hash": "", "trang_thai": "prepared", "luc": time.time()}
        if hien is None and not tao_moi:
            return {**rc, "ket_qua": "missing", "trang_thai": "huy"}
        if truoc_hash is not None and (hien is None or sha256(hien) != truoc_hash):
            return {**rc, "ket_qua": "conflict", "trang_thai": "huy"}
        if hien is not None:
            bp = ten_sao_luu(goc, that, deployment_id, target_id)
            bp.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(bp, "xb") as f:      # tạo-độc-quyền: không bao giờ đè một bản sao lưu đang có
                    f.write(hien.encode("utf-8"))
                    f.flush()
                    os.fsync(f.fileno())
            except FileExistsError:
                pass                            # chạy lại cùng triển khai: dùng lại bản cũ NẾU nó đúng
            if doc(bp) != hien:
                raise OSError(f"bản sao lưu không khớp nội dung gốc: {bp}")
            rc["backup"], rc["backup_hash"] = str(bp), sha256(hien)
        if dung_tai:
            dung_tai("sau_sao_luu")
        _ghi_json_nguyen_tu(_tep_nhat_ky(goc, deployment_id, target_id), rc)
        if dung_tai:
            dung_tai("sau_nhat_ky")
        that.parent.mkdir(parents=True, exist_ok=True)
        _ghi_bytes_nguyen_tu(that, new_text)
        if dung_tai:
            dung_tai("sau_ghi")
        if doc(that) != new_text:
            raise OSError(f"đọc lại sau khi ghi không khớp: {that}")
        rc["trang_thai"] = "committed"
        _ghi_json_nguyen_tu(_tep_nhat_ky(goc, deployment_id, target_id), rc)
        return {**rc, "ket_qua": "committed"}


# ---------------------------------------------------------------- đối soát sau crash
def doi_soat(goc: Path, *, thu_muc_khoa: Path) -> list:
    """Quét nhật ký `prepared` của một gốc và đối soát với file thật. Trả danh sách việc đã làm.

    - file hiện tại = before: lần ghi chưa xảy ra -> huỷ nhật ký (`huy`)
    - file hiện tại = after:  đã ghi, chỉ thiếu bước chốt -> hoàn tất `committed`
    - khác cả hai:            có người sửa -> `xung_dot`, KHÔNG đoán và KHÔNG đè
    Không coi mọi file bằng bản mới là do mình ghi: chỉ khi có nhật ký `prepared` khớp."""
    ra = []
    nk = _thu_muc_nhat_ky(goc)
    if not nk.is_dir():
        return ra
    for tep in sorted(nk.glob("*.json")):
        try:
            rc = json.loads(tep.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra.append({"tep": tep.name, "viec": "hong"})
            continue
        if rc.get("trang_thai") != "prepared":
            continue
        dich = Path(rc.get("duong_dan") or "")
        try:
            with khoa(thu_muc_khoa, str(dich)):
                hien = doc(dich)
                h = sha256(hien) if hien is not None else ""
                if h == rc.get("sau_hash"):
                    rc["trang_thai"] = "committed"
                    viec = "hoan_tat"
                elif h == rc.get("truoc_hash") or hien is None and not rc.get("truoc_hash"):
                    rc["trang_thai"] = "huy"
                    viec = "huy"
                else:
                    rc["trang_thai"] = "xung_dot"
                    viec = "xung_dot"
                _ghi_json_nguyen_tu(tep, rc)
        except HetGioKhoa:
            viec = "bo_qua_het_gio"
        ra.append({"tep": tep.name, "viec": viec, "duong_dan": str(dich)})
    return ra
