# Tab Lộ trình học viên - kế hoạch

Spec: `docs/dev/2026-10-lo-trinh-hoc-vien-design.md` · Trạng thái: xong (1.3.9)

## Mục tiêu

Trưởng phòng bấm Kích hoạt lộ trình cho người mới; mỗi ngày bài học tự mở (và tự nhắn Telegram nếu có
chat ID); học viên làm bài kiểm tra chấm tự động; mentor chấm phần quan sát; hệ thống đề xuất kết quả theo
luật của brain; trưởng phòng kết luận. Không bước nào gọi model.

## Ràng buộc chung

- Không đổi hợp đồng API cũ. Thêm mới: `GET /lo-trinh`, `POST /lo-trinh/kich-hoat`,
  `GET /lo-trinh/hoc-vien/{id}`, `GET /lo-trinh/bai/{id}/{ngay}`, `POST /lo-trinh/bai/{id}/{ngay}/nop`,
  `POST /lo-trinh/hoc-vien/{id}/cham`, `POST /lo-trinh/hoc-vien/{id}/nghi`, `POST /lo-trinh/hoc-vien/{id}/ket-luan`.
- `/lo-trinh` KHÔNG nằm trong `_STAFF_DENY`: học viên phải ghi được bài nộp của mình. Quyền kiểm trong module.
- i18n: mọi khoá mới có cả vi và en; không em dash; màu chỉ dùng token theme.
- Dữ liệu cá nhân ở `STATE_DIR/lo_trinh.json`, không vào brain.

## Các task

- [x] T1 - `server/lo_trinh.py`: đọc bài học từ brain, lịch ngày đào tạo, chấm, đề xuất, endpoint, vòng gửi Telegram
  - Kiểm: `python tests/run.py lo_trinh` (24 test, app riêng với phụ thuộc giả, brain tạm)
- [x] T2 - Nối vào `server/main.py`: import, `LoTrinhDeps`, đường gửi Telegram riêng (không qua `_tg_send_to`
  vì hàm đó đổi hướng sang chủ bot khi chat ID ngoài whitelist), vòng gửi lúc khởi động
  - Kiểm: `cd server && python -c "import main"`; `python tests/run.py route_table`
- [x] T3 - `dashboard/lo-trinh.js` + nối dây (`console.js`, `ui-actions.js`, `ui_targets.py`, `index.html`),
  i18n vi/en (117 khoá), CSS `.lt-*`
  - Kiểm: `node tests/js/test_trang_lo_trinh.js` (35 mục), `node tests/js/test_giao_dien_toi.js`, `node tests/js/test_i18n.mjs`
- [x] T4 - 15 bài Học việc Makeup trong brain `ThuyH2O - Hoc Viec` (`cap-do/hoc-viec/bai-hoc/`), soạn từ 15 SOP
  `San Xuat - Makeup`, 69 câu hỏi
  - Kiểm: `lo_trinh.doc_bai_hoc(<brain>, "hoc-viec")` trả 15 bài, 69 câu
- [x] T5 - Xáo thứ tự lựa chọn theo học viên (52/69 câu bản đầu có đáp án ở vị trí B)
  - Kiểm: test `test_lua_chon_duoc_xao_theo_hoc_vien_va_co_dinh`, `test_nop_bai_cham_tu_dong_hai_luot_roi_lo_dap_an`
- [x] T6 - Wiki (`bai-hoc-va-cham-diem`, nhánh Makeup, index), agent `truong-hoc-viec`, skill, log
  - Kiểm: script kiểm link và em dash của brain

## Ngoài phạm vi

- Bài học cho Thực tập sinh, CTV và các cấp trên (cần nội dung từ trưởng đào tạo).
- Nộp ảnh hoặc video bằng chứng trong tab.
- Gửi qua Zalo.
- Tự đổi chức vụ nhân viên khi đạt.
