# Trang Nghiên cứu và Process Factory - kế hoạch

Spec: `docs/dev/2026-10-process-factory-design.md` · Trạng thái: đang làm · Bản: 1.3.7
Nhánh: `claude/trang-nghien-cuu-1-3-7` (tách từ `claude/sua-test-do-1-3-6`, bản 1.3.6 chưa merge)

## Mục tiêu

Trang Nghiên cứu hiện sáu khu, đọc số thật từ brain `Nghien Cuu - Concept Hinh Anh`. Ý tưởng
gửi vào phòng được ghi rõ loại (concept, quy trình mới, sửa quy trình cũ) và giai đoạn, để
trang hiện đúng đang ở bước nào.

## Ràng buộc chung

- Chỉ THÊM endpoint `GET /nghien-cuu`. Không đổi endpoint cũ.
- Không sửa `CLAUDE.md`: `test_prompt_budget` đã đỏ sẵn, thêm chữ là làm đỏ thêm.
- i18n: mọi khoá mới có cả `vi` và `en`. Không em dash.
- Trang chỉ ĐỌC brain. Brain chỉ được ghi bởi skill `h2o-y-tuong` khi chạy một ý tưởng.
- Brain không nằm trong git. Trước khi sửa file trong `brains/` phải sao lưu sang scratchpad.
- Test không đụng brain thật: `BRAINS_DIR` và `JOYCE_STATE_DIR` trỏ thư mục tạm.
- Trường mới của trang ý tưởng: `loai`, `giai_doan`. Trường `status` cũ (draft/active/archived) giữ nguyên.

## Quy ước dữ liệu

- `loai`: `concept` | `quy-trinh-moi` | `sua-quy-trinh` (mặc định `concept`).
- `giai_doan`: `moi` | `phan-tich` | `ban-nhap` | `ra-soat` | `cho-duyet` | `pilot` | `hoat-dong` | `gac`.
  Thiếu trường này thì suy ra từ `status`: draft → moi, active → hoat-dong, archived → gac.
- Thư viện concept: trang có `loai: concept` và `giai_doan` thuộc pilot, hoat-dong, gac.
  Số booking đọc từ trường `booking`. Thiếu thì ghi "chưa nối nguồn", không bịa số.
- SOP: `wiki/quy-trinh/*.md`, đọc `status` (active / superseded), `phien_ban`, `ngay_ra_soat`, `thay_the`.
- Bản tin xu hướng: `wiki/radar/*.md`, đọc `ngay` và tiêu đề `#` đầu tiên.
- Nhật ký: `wiki/log.md`, các dòng `## [ngày] loại | tiêu đề`.
- Change Request: trang ý tưởng có `loai: sua-quy-trinh` và giai đoạn chưa hoat-dong / gac.

## Các task

- [x] T0 - Đặt xí chỗ 1.3.7 (VERSION, CHANGELOG, plan). Kiểm: `tests/python/test_version_khop_changelog.py`
  và `tests/python/test_phien_ban_moi_nhat.py` đều xanh.
- [x] T1 - `server/nghien_cuu.py`: hàm thuần đọc một thư mục brain và trả sáu khu. Không import
  `main`. Kiểm: `tests/python/test_nghien_cuu.py` dựng brain tạm và kiểm từng khu, gồm trường hợp
  brain rỗng, trang thiếu `giai_doan`, log có dòng lạ, và frontmatter có dấu hai chấm trong giá trị.
- [x] T2 - Route `GET /nghien-cuu` trong `server/main.py`, gọi `nghien_cuu.doc_trang(root)`.
  Kiểm: `python tests/run.py route_table` xanh sau khi chụp lại có chủ ý; gọi endpoint trả JSON
  đủ sáu khoá.
- [x] T3 - Trang `dashboard/nghien-cuu.js` (sáu khu, chỉ đọc, token theme). Nối vào: nhóm
  `nang_luc` trong `RAIL_ITEMS`, dispatch trong `console.js`, `VIEW_META`, `server/ui_targets.py`
  (PAGES và ALIASES), `dashboard/ui-actions.js` (PAGES), `index.html` (script), `i18n` vi và en.
  Kiểm: `tests/js/test_trang_nghien_cuu.js` mới (nguồn có đủ nối dây), `test_i18n.mjs`,
  `test_giao_dien_toi.js`, `test_tong_quan.js` vẫn xanh.
- [x] T4 - Cổng ý tưởng: sao lưu `skills/h2o-y-tuong/SKILL.md` của brain pilot, rồi sửa bước 1 để
  nhận tiền tố `[Ý tưởng][loại]` (loại: Concept, Quy trình mới, Sửa quy trình). Không có tiền tố thì
  skill tự phân loại theo nội dung và ghi lý do. Ghi `loai` và `giai_doan: moi` vào frontmatter.
  Không đổi tiền tố `[Ý tưởng]` nên luồng tự chạy trong `server/tasks.py` và `task_store.py` không đổi.
  Kiểm: đọc lại skill; tạo một trang mẫu trong brain tạm, rồi `nghien_cuu.doc_trang` đọc đúng `loai` và `giai_doan`.
- [x] T5 - Tài liệu hoá quy tắc SOP ACTIVE: mẫu frontmatter (`phien_ban`, `thay_the`, `ngay_ra_soat`)
  và quy tắc sửa qua Change Request, ghi trong spec. Không khoá quyền ghi ở tầng file (để sau).
  Kiểm: trang trong T1 đọc được các trường này trong brain tạm.
- [x] T6 - Bộ test đầy đủ như CI (venv Python 3.12, Linux-equivalent), CHANGELOG hoàn chỉnh,
  commit từng việc, push nhánh. Không merge vào `main`: CI phải xanh trước.

## Quyết định đã chốt

- Làm trang sáu khu (chủ repo, 11/10).
- Brain pilot: `Nghien Cuu - Concept Hinh Anh` (chủ repo, 11/10).
- Cổng ý tưởng dùng tiền tố (chủ repo, 11/10).
- Mặc định, chưa được chốt riêng: mọi nhân viên đề nghị Change Request, trưởng phòng duyệt L1.

## Ngoài phạm vi

- Job tự động tạo bản tin radar (lịch nhắc + nguồn web). Trang chỉ hiện bản tin nếu đã có file.
- Khoá quyền ghi theo từng file SOP.
- Nguồn booking theo concept (chưa có kết nối). Cột booking ghi "chưa nối nguồn".
- Các brain khác ngoài pilot.
- Sửa `CLAUDE.md` hoặc thêm `workflows/` ở gốc repo.

## Kết quả kiểm cuối (T6)

Chạy trên worktree sạch ở `e622e8f`, toàn bộ 580 file test (Python và JS), mỗi file một tiến trình:
574 xanh, 6 đỏ. Sáu file đỏ đều là quyết định chủ repo, không do batch này:
`test_go_chatgpt_web`, `test_tai_lieu_song_ngu` (thiếu tài liệu trong docs/dev), `test_prompt_budget`
(CLAUDE.md và prompt cố định vượt trần), `test_logo_linh_vat`, `test_pet_bang_mau`,
`test_pet_thanh_truot_mau` (mascot và bảng màu mặc định).
