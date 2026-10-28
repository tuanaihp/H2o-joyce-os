# Báo cáo 30 skill có đầu file YAML không đọc được (A03)

> Lập chỉ-đọc ngày 28/10/2026 bằng `yaml.safe_load` trên khối đầu file của mọi `brains/*/skills/*/SKILL.md`. **Không sửa file nào.** Plan (A03) yêu cầu báo cáo để sửa riêng sau khi chủ duyệt, không đổi YAML hàng loạt và không nới bộ đọc cho qua.

Tổng số skill đọc không được: **30**.

Hệ quả: với các file này bộ phân loại trả `invalid` nên tự cải tiến KHÔNG tự áp lên chúng, chờ chủ xem. Ứng dụng vẫn đọc chúng (bộ đọc của ứng dụng chịu lỗi); chỉ cổng an toàn của harness là không chắc.

| # | Brain | Skill | Dòng | Lỗi | Dòng gây lỗi (cắt) |
|---|---|---|---|---|---|
| 1 | Brain Default | h2o-studio-admin-fanpage | 2 | mapping values are not allowed here | `description: Điều phối đăng bài/trả lời trên Fanpage H2O: lọc tín hiệu, soạn nội dung nháp, báo chủ duyệt.` |
| 2 | Brain Default | h2o-studio-chief-of-staff | 2 | mapping values are not allowed here | `description: Đọc board các phòng, hợp báo cáo sáng cho chủ: việc mới/kẹt/quá hạn + 3 ưu tiên ngày` |
| 3 | CSKH - Sau Dich Vu va Khieu Nai | h2o-studio-cskh-post-service-followup | 2 | mapping values are not allowed here | `description: Soạn nội dung chăm sóc sau khi khách dùng dịch vụ (chụp xong/makeup xong/trả váy): cảm ơn, xin fe` |
| 4 | CSKH - Trong Dich Vu | h2o-studio-cskh-post-service-followup | 2 | mapping values are not allowed here | `description: Soạn nội dung chăm sóc sau khi khách dùng dịch vụ (chụp xong/makeup xong/trả váy): cảm ơn, xin fe` |
| 5 | CSKH - Truoc Dich Vu | h2o-studio-cskh-post-service-followup | 2 | mapping values are not allowed here | `description: Soạn nội dung chăm sóc sau khi khách dùng dịch vụ (chụp xong/makeup xong/trả váy): cảm ơn, xin fe` |
| 6 | Ke Toan - Thu | h2o-studio-ketoan-thu-cong-no | 2 | mapping values are not allowed here | `description: Theo dõi đơn đã chốt: lập sổ thu, nhắc cọc/phần còn lại đúng hạn, xuất phiếu đối soát cuối đơn.` |
| 7 | Marketing - Hinh Anh | h2o-studio-marketing-performance-review | 2 | mapping values are not allowed here | `description: Phân tích bài đăng đã chạy: metric nào ăn, bài nào kéo lead, đề xuất nhân hoặc dừng format.` |
| 8 | Marketing - Makeup | h2o-studio-marketing-performance-review | 2 | mapping values are not allowed here | `description: Phân tích bài đăng đã chạy: metric nào ăn, bài nào kéo lead, đề xuất nhân hoặc dừng format.` |
| 9 | Marketing - Vay Cuoi | h2o-studio-marketing-performance-review | 2 | mapping values are not allowed here | `description: Phân tích bài đăng đã chạy: metric nào ăn, bài nào kéo lead, đề xuất nhân hoặc dừng format.` |
| 10 | Nghien Cuu - Concept Hinh Anh | h2o-y-tuong | 2 | mapping values are not allowed here | `description: Pipeline ý tưởng mới của phòng Nghiên cứu concept: ghi kho ý tưởng, phân tích, đề xuất giải pháp,` |
| 11 | Nhan Su - Boi Toc | h2o-studio-nhansu-tuyen-danh-gia-boi-toc | 2 | mapping values are not allowed here | `description: Tuyển, đánh giá và lên lịch đào tạo thợ bới tóc: JD, tiêu chí tay nghề, bài test, KPI giữ chân.` |
| 12 | Nhan Su - CSKH | h2o-studio-nhansu-tuyen-danh-gia-cskh | 2 | mapping values are not allowed here | `description: Tuyển và đánh giá nhân viên CSKH: tiêu chí giao tiếp, test xử lý tình huống, KPI hài lòng khách.` |
| 13 | Nhan Su - Hinh Anh | h2o-studio-nhansu-tuyen-danh-gia-hinh-anh | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá nhiếp ảnh và phục vụ chụp: portfolio review, test chụp thử, KPI theo buổi.` |
| 14 | Nhan Su - Makeup | h2o-studio-nhansu-tuyen-danh-gia-makeup | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá thợ makeup cô dâu: test trên da thật, tốc độ, vệ sinh dụng cụ, KPI khách hài lòng.` |
| 15 | Nhan Su - Marketing | h2o-studio-nhansu-tuyen-danh-gia-marketing | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá nhân viên marketing studio: test viết content, hiểu kênh, KPI lead về cho Sales.` |
| 16 | Nhan Su - Photoshop | h2o-studio-nhansu-tuyen-danh-gia-photoshop | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá nhân viên hậu kỳ: test chỉnh ảnh cưới, tốc độ vs chất lượng, KPI sửa lại.` |
| 17 | Nhan Su - Sales | h2o-studio-nhansu-tuyen-danh-gia-sales | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá sales tư vấn cưới: test tư vấn thử, hiểu gói dịch vụ, KPI chốt đơn và giữ khách.` |
| 18 | Nhan Su - Van Hanh | h2o-studio-nhansu-tuyen-danh-gia-van-hanh | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá nhân viên vận hành: điều phối lịch, xử lý sự cố ngày chụp, KPI vận hành trơn.` |
| 19 | Nhan Su - Vay | h2o-studio-nhansu-tuyen-danh-gia-vay | 2 | mapping values are not allowed here | `description: Tuyển/đánh giá nhân viên phòng váy: tư vấn chọn váy, giữ váy, KPI lượt thuê và tình trạng váy.` |
| 20 | San Xuat - Boi Toc | h2o-studio-sx-boi-toc | 2 | mapping values are not allowed here | `description: Chuẩn bị và phối hợp thợ bới tóc cho buổi chụp/makeup: lịch, mẫu tóc theo concept, checklist.` |
| 21 | San Xuat - Concept | h2o-studio-sx-concept-trien-khai | 2 | mapping values are not allowed here | `description: Biến concept nghiên cứu thành set chụp thật: bối cảnh, đạo cụ, ánh sáng, kiểm thử trước giờ khách` |
| 22 | San Xuat - Hinh Anh | h2o-studio-sx-hinh-anh-ngay-chup | 2 | mapping values are not allowed here | `description: Điều hành buổi chụp: ekip, shot list, timeline, xử lý sự cố, giao file thô đúng quy cách.` |
| 23 | San Xuat - Makeup | h2o-studio-sx-makeup-ngay-lam | 2 | mapping values are not allowed here | `description: Điều phối makeup cho buổi dịch vụ: look theo concept, thời gian, vệ sinh dụng cụ, sửa nhanh.` |
| 24 | ThuyH2O - Hoc Viec | h2o-studio-thuyh2o-hoc-viec | 2 | mapping values are not allowed here | `description: Theo dõi học việc (đệ tử thực tập): tiến độ tay nghề, lịch làm, đánh giá lên cấp.` |
| 25 | ThuyH2O - Hoc Vien | h2o-studio-thuyh2o-hoc-vien | 2 | mapping values are not allowed here | `description: Đồng hành học viên khoá học: tiến độ học, nhắc bài, trả lời thắc mắc, giữ động lực tới tốt nghiệp` |
| 26 | ThuyH2O - Nhan Vien | h2o-studio-thuyh2o-nhan-vien | 2 | mapping values are not allowed here | `description: Theo dõi nhân viên học viện: phân ca, chấm công, lương thưởng, giải quyết vấn đề nội bộ.` |
| 27 | Truyen Thong - Phan Hoi va Xu Ly | h2o-studio-tt-phan-hoi-xu-ly | 2 | mapping values are not allowed here | `description: Soạn câu trả lời bình luận/tin nhắn công khai: khen, hỏi, chê, giận - đúng giọng H2O.` |
| 28 | Van Thu va Quy Trinh | h2o-studio-vanthu-quy-trinh | 2 | mapping values are not allowed here | `description: Quản lý văn bản, hợp đồng, quy trình nội bộ: soạn nháp, phiên bản, truy xuất nhanh cho các phòng.` |
| 29 | Ve Sinh - Khong Gian Studio | h2o-studio-vs-khong-gian | 2 | mapping values are not allowed here | `description: Checklist vệ sinh khu vực: sảnh, phòng makeup, phòng chụp, kho váy, vệ sinh - theo ca.` |
| 30 | Ve Sinh - Kiem Tra Cuoi Ca | h2o-studio-vs-kiem-tra-cuoi-ca | 2 | mapping values are not allowed here | `description: Checklist đóng cửa: thiết bị tắt, váy cất đúng, khoá cửa, báo cáo bất thường cuối ngày.` |

## Cách sửa đề xuất (chưa làm)

Hầu hết là một giá trị có dấu hai chấm hoặc dấu ngoặc chưa được đặt trong dấu nháy (thường là `description:`). Sửa một lần cho mỗi file bằng cách bọc giá trị trong dấu nháy kép hoặc dùng khối `>-`. Nên sửa trong một commit riêng sau khi chủ duyệt, rồi chạy lại báo cáo này để xác nhận bằng 0.
