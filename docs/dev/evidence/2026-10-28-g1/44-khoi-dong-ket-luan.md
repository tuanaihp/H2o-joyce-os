# A07.1 - đo khởi động (28/10/2026)

Máy: Windows 10, Python 3.14.6. Đo `import main` trừ chi phí interpreter trần, 12 vòng XEN KẼ giữa các phiên bản, mọi tiến trình
đều thoát mã 0. Script: `43-bench_import.py`. Số thô từng lần nằm trong các file `40`, `41`, `42` (mục `raw`).

| Phiên bản | venv | main nhỏ nhất (ms) | trung vị (ms) | tỉ lệ so fastapi (nhỏ nhất) |
|---|---|---|---|---|
| 1.3.39 (332ff4c) | dev (có click, rich) | 1362 | 1545 | 5,22 |
| 1.3.41 (6b22a33) | dev | 1378 | 1547 | 5,28 |
| ứng viên trước A07.1 (8bb9a6c) | dev | 1413 | 1569 | 5,43 |
| 1.3.39 | sạch (đúng requirements.txt) | 1246 | 1364 | 5,11 |
| 1.3.41 | sạch | 1202 | 1296 | 5,04 |
| ứng viên trước A07.1 | sạch | 1182 | 1391 | 5,02 |
| (lần đo kế) 1.3.39 | sạch | 1252 | 1369 | 5,23 |
| (lần đo kế) ứng viên trước | sạch | 1253 | 1339 | 5,07 |
| ứng viên SAU A07.1 | sạch | 1204 | 1395 | 4,75 |

Kết luận trung thực:

- **Trần 5,0 đã bị chạm từ 1.3.39**, trước mọi thay đổi của đợt này (5,11 đến 5,23 trên venv sạch; 5,22 trên venv dev). Bài
  `test_khoi_dong_nhe` đỏ trên máy này ở cả 1.3.39 lẫn 1.3.41, nên đây không phải hồi quy do gói A.
- Venv dev nặng hơn venv sạch khoảng 60ms vì có `click` và `rich` (httpx nạp module CLI của nó khi thấy chúng). Người dùng cài
  từ requirements.txt không trả khoản này.
- Phần tăng của gói A so với 1.3.41 nằm trong nhiễu đo (chênh vài chục ms, trung vị đảo chiều giữa các lần).
- Thử nghiệm duy nhất có bằng chứng: `cryptography` (~36ms) chỉ webpush.py nạp ở mức module, là tính năng tuỳ chọn. Đã chuyển sang
  nạp lười. Nhỏ nhất giảm khoảng 49ms (1253 xuống 1204), tỉ lệ 5,07 xuống 4,75. Trung vị KHÔNG cải thiện rõ trong lần đo này
  (nhiễu máy lớn, p95 lên 1764): khoản lợi là có thật nhưng nhỏ, đừng đọc thành "nhanh hơn 4%" ở mọi máy.
- Không nạp lười `messenger_ops` (plan cấm), không động `httpx` (14 module dùng, không tuỳ chọn), không động `fastapi` hay
  `uvicorn` (tiết kiệm ít, rủi ro lớn hơn lợi).
- Hàng rào mới trong `test_khoi_dong_nhe`: `cryptography` vào danh sách phải nạp lười, cấm `import cryptography` ở cột 0 của webpush,
  secrets_store, config. Trần 5,0 giữ nguyên.

## Gate của plan A07.1: CHƯA đạt, giữ A07.1 mở

Gate yêu cầu median giảm so với 1.3.41 và p95 của tỉ lệ dưới 5,0. Tỉ lệ từng vòng (main trừ interpreter, chia fastapi trừ interpreter,
cùng một vòng xen kẽ), 12 vòng mỗi bản, tính từ phần `raw` của file `41` và `42`:

| Lần đo | Bản | Tỉ lệ trung vị | p95 | Lớn nhất | Số vòng >= 5,0 |
|---|---|---|---|---|---|
| 41 | 1.3.39 | 3,94 | 5,68 | 5,87 | 3/12 |
| 41 | 1.3.41 | 4,60 | 5,51 | 5,98 | 3/12 |
| 41 | ứng viên trước A07.1 | 5,04 | 5,52 | 5,88 | 6/12 |
| 42 | 1.3.39 | 4,93 | 5,52 | 5,58 | 6/12 |
| 42 | ứng viên trước A07.1 | 4,99 | 5,48 | 5,51 | 6/12 |
| 42 | ứng viên SAU A07.1 | 4,84 | 5,17 | 5,44 | 3/12 |

- Hai lần đo cho thứ tự khác nhau giữa 1.3.39 và ứng viên, chứng tỏ biến động máy lớn hơn mọi chênh lệch giữa các bản. Không thể
  khẳng định bản nào nhanh hơn bản nào chỉ từ các số này.
- Sau A07.1 trung vị giảm nhẹ (4,99 xuống 4,84) và p95 giảm (5,48 xuống 5,17), cùng chiều với khoản ~36ms đã bỏ, nhưng p95 vẫn
  trên 5,0 và chênh lệch nằm trong biên độ nhiễu. **Gate chưa đạt.** Em không nâng trần 5,0 và không chọn lần xanh để báo xanh.
- Phép đo của chính `test_khoi_dong_nhe` (nhỏ nhất của 5 vòng) xanh sau A07.1 ở cả hai lần chạy (4,30 và 4,75) nhưng đó là thước thô,
  không thay cho gate p95 ở trên.
- Phần còn lại của chi phí khởi động là thư viện không tuỳ chọn (fastapi, httpx, asyncio, yaml, config) và thân main.py khai hơn
  300 route. Muốn xuống dưới 5,0 chắc chắn cần giảm số route nạp lúc import hoặc tách main.py, việc lớn hơn gói A; ghi vào tồn đọng
  G1-12.
