# Nhật ký phiên bản - H2O Joyce OS

***Tiếng Việt** · [English](CHANGELOG.en.md)*

## [1.3.46] - 2026-10-29
### Thêm
- **Chặn quyền theo từng lệnh, không chỉ theo tên tool.** Ví dụ trợ lý chỉ đọc vẫn xem được số liệu sổ Quản lý Shop nhưng không ghi được thu chi vào sổ tiền; tool nhiều hành động của kết nối ngoài cũng được phân loại lại lúc gọi.
- **Pilot Đối Soát đã sẵn sàng chạy:** có trợ lý bản thử "Agent Đối Soát (pilot G3)" (không sửa trợ lý gốc), bộ ca thử và 20 việc kèm bảng chấm để anh chạy và chấm trên trang Sơ đồ.

## [1.3.45] - 2026-10-29
### Thêm
- **Mọi tool của hub hỏi quyền trước khi chạy.** Trợ lý đã khai quyền (ví dụ chỉ đọc) mà gọi tool gửi tin, ghi sổ hay xóa thì bị chặn, và lần chặn được ghi lại để anh xem. Trợ lý chưa khai quyền vẫn chạy như cũ.
- **Khung chat của anh, Telegram và CLI nay vào sổ lượt chạy.** Chat với một trợ lý được ghi theo trợ lý đó; đo được token và số lượt, và trần token áp cho cả chat.

## [1.3.44] - 2026-10-29
### Thêm
- **Rào hoàn thành cho việc tác động ra ngoài:** việc làm ngoài (gửi, đăng, thanh toán) mà chưa được nghiệm thu độc lập thì không tự sang "xong", nằm ở cột duyệt chờ anh xác nhận. Chỉnh hoặc tắt bằng `tasks.rao_hoan_thanh`.
- **Đo token thật theo từng lượt chạy,** hiện trên Sơ đồ; lượt engine không báo thì ghi "chưa đo", không tính 0. Đặt trần bằng `tasks.tran_token_luot` (tối đa 1.000.000): vượt trần thì lượt dừng.
### Sửa
- **Sửa 28 test đỏ cũ:** nối lại ghim thư mục làm việc ở chat thường, dấu ">" của ô chọn thư mục, cờ "gọi" của nhắc việc, lỗi trả về từ nhà cung cấp khi kết nối OAuth. Giao diện không còn emoji (dùng icon). Hồ sơ pilot Đối Soát viết xong, chờ anh duyệt.

## [1.3.43] - 2026-10-28
### Thêm
- **Joyce ghi lại mọi lượt trợ lý chạy thật** (bot trả lời khách, việc giao cho trợ lý, bước workflow) kèm đúng bản cấu hình đã dùng. Retry chỉ tính một lần; máy tắt giữa chừng ghi là gián đoạn, không tính đạt.
- **Canary chỉ nhân khi đủ 20 lượt anh chấm đạt.** Hoàn tất chưa phải đạt. Trang Sơ đồ có khung "Lượt chờ anh chấm" với nút Đạt và Rớt; một lượt rớt là lật lại ngay.
- **Trợ lý đã khai quyền thì bị chặn ghi file nếu thiếu quyền ghi, và mỗi file tự cải tiến tối đa 2 lần mỗi tuần** (lần thứ ba chờ anh duyệt).
- **Sơ đồ thêm 5 đèn:** Cổng 7 ngày, Bộ ghi file, Lượt chạy thật, Bản đang chạy, Chứng nhận đường ghi. Nói thẳng: chưa đường ghi nào đạt chứng nhận, và chat trực tiếp với Joyce chưa vào sổ lượt chạy.

## [1.3.42] - 2026-10-28
### Sửa
- **Tự cải tiến chỉ tự áp thay đổi hiển thị.** Đổi lời giao việc, vai trò hay quyền thì chờ anh xem; lý do hiện rõ trong thông báo. Có công tắc tạm dừng tự triển khai trên trang Sơ đồ.
- **Không đè bản phòng tự sửa.** Phòng có biến thể riêng từ trước thì đứng yên chờ anh quyết, không bị nhân bản ghi đè. Mỗi lần ghi đều lưu bản cũ để khôi phục từng phòng, kể cả khi máy tắt giữa chừng.
- **Sơ đồ có khung quản trị triển khai:** xem phần khác biệt, khôi phục từng phòng, đánh dấu đã đọc. Bộ ca thử hỏng thì chặn, chưa có ca thử thì không chặn.
- **Nói thẳng:** canary vẫn chưa được chứng nhận vì việc chạy chưa gắn với agent, nên file dùng chung nhiều phòng chưa tự áp. Khởi động nhẹ hơn một chút, nhưng test khởi động vẫn sát trần trên máy này.

## [1.3.41] - 2026-10-28
### Sửa
- **Tự cải tiến nhìn ra mọi thay đổi về quyền**, kể cả khoá lồng trong cấu hình hay tráo công cụ giữa các bước. Cấu hình đọc không chắc thì chờ anh xem, không tự áp. 30 skill có đầu file sai cú pháp từ trước cũng vì vậy mà chờ anh.
- **Bộ ca thử hỏng không còn mở đường.** File ca thử sai sẽ chặn bản sửa tự động thay vì bị coi như chưa có ca thử nào.
- **Không ghi đè tài liệu gốc bằng đường vòng.** Chốt bảo vệ `sources/` nay nằm ngay ở lệnh ghi file, chặn cả đường dẫn viết vòng, thư mục liên kết và file bị tráo phút chót.
- **Canary an toàn hơn.** Nhân từng phòng và không đè bản phòng tự sửa; cần đủ 20 việc chạy thật mới nhân; có lỗi là dừng ngay. Lưu ý: hiện việc chưa được gắn với agent nên canary sẽ chờ rồi hết hạn thay vì nhân; phần gắn việc làm ở gói sau.

## [1.3.40] - 2026-10-28
### Thêm
- **Hộp thư Messenger ngay trong tab Fanpage.** Bật cho từng Trang, xem hội thoại khách, bấm "Gợi ý trả lời" để Joyce soạn nháp rồi anh sửa và bấm Gửi. Mặc định chỉ lưu tin vào hộp thư, không có gì tự gửi đi.
- **Tự động trả lời là công tắc riêng, mặc định tắt.** Phải xác nhận mới bật vì tin đi thẳng tới khách. Meta chỉ cho trả lời trong 24 giờ sau tin cuối của khách, giao diện nhắc rõ và báo lỗi nói thẳng khi quá hạn.
- **Đưa khách vào CRM bằng một nút** để Joyce đề xuất cập nhật hồ sơ, chờ anh duyệt.
- Làm một lần: dán địa chỉ webhook sang app Facebook và xin thêm quyền nhắn tin. Khách thật cần Meta duyệt quyền `pages_messaging`; trước đó chỉ thử được với người có vai trò trong app.

## [1.3.39] - 2026-10-28
### Thêm
- **Trang Sơ đồ có khối Joyce Harness.** Ba tầng (lõi chạy, bề mặt phòng ban, vòng cải tiến), 14 thành phần, mỗi cái một đèn theo số thật; thứ chưa làm hiện xám và nói thẳng là chưa làm.
- **Chốt chặn joyce-guard bật sẵn.** Không ghi đè tài liệu gốc trong sources/, người ngoài không nhờ Joyce gửi Zalo dồn dập, khoản chi từ 5 triệu phải gắn hợp đồng hoặc ghi rõ hạng mục.
### Đổi
- **9 trợ lý dùng chung giờ chỉ còn một bản gốc.** Năm giám định, kỹ sư cải tiến, hai trợ lý đại tu và Trợ lý Onboarding sửa một nơi là mọi phòng đổi theo; 549 bản chép trong các brain đã xoá (có sao lưu). Phòng cần khác thì lưu bản riêng.
- **Rẻ token hơn.** Phần cố định của lời dặn Joyce được cache thật, không còn trượt mỗi lượt vì đồng hồ; lượt đọc nhiều trang dữ liệu tự thu gọn kết quả cũ, số liệu Sổ Shop giữ nguyên.
### Sửa
- Việc khai "không dùng tool nào" trước đây lại chạy toàn quyền ở engine Claude; tự cải tiến đổi quyền của trợ lý giờ phải chờ chủ duyệt; ca thử không kiểm được tính là rớt.

## [1.3.38] - 2026-10-27
### Thêm
- **Tab mới "Bảng giá & hoa hồng".** Bảng giá 46 gói dịch vụ kèm lịch cọc lần 1, lần 2 và thanh toán cuối; bảng đầu việc theo phòng (Makeup, Chụp ảnh, Photoshop, Tư vấn váy...) kèm hoa hồng cố định mỗi việc. Cả hai nạp sẵn từ sheet của H2O, sửa được ngay trên màn hình.
- **Gõ mã gói là có giá.** Lập hợp đồng hoặc báo giá chỉ cần gõ mã hay tên gói, giá tự điền; đơn bán hàng nhắc khách còn phải trả cọc nào. Hỏi Joyce "giá gói PRW-STCB" là tra được ngay.
- **Chia việc theo hợp đồng.** Mỗi hợp đồng giao từng đầu việc cho từng người; hoa hồng vào bảng lương tự tính theo số tiền của từng việc, không còn chỉ theo phần trăm.

- **Hai tab mới: Danh mục đồ và Lịch sử thuê đồ.** Quản lý váy, vest, áo dài cho thuê: đồ nào sẵn sàng, đang thuê hay quá hạn chưa trả. Cho thuê gắn hợp đồng và ghi thu luôn, chặn thuê trùng ngày kể cả số ngày giặt phơi sau mỗi lần trả (mặc định 3, sửa được theo từng món), nhận trả báo trễ hạn. Có nút nạp 5 đồ mẫu để thử và xóa gọn.

## [1.3.37] - 2026-10-27
### Thêm
- **Báo một câu trong chat, Joyce ghi sổ và giao đúng phòng.** Ví dụ "hợp đồng Tuấn Thủy 0899252392, gói chụp studio 15 triệu, thu 15tr, chi 4tr setup": Sales ghi khách, cơ hội và báo giá vào CRM, Phòng Thu ghi thu, Phòng Chi ghi chi. Khách trùng số điện thoại không bị tạo hai lần, gửi lại cùng câu không ghi hai lần.
- **Sổ Quản lý Shop là số thật.** Thu chi, đơn bán (hợp đồng), báo giá, nhân sự và lương, công việc đều đọc từ sổ chung; số mẫu "Tiệm bánh Mây" đã bỏ; Kho, Hộp chat, Chăm sóc, Marketing và Ảnh AI ghi rõ "chưa nối dữ liệu thật". Lương có hoa hồng phần trăm tính tự động từ lãi gộp của hợp đồng đã ký.
- **Văn phòng ảo hiện agent đang làm.** Phòng nào vừa xử lý việc thì sáng lên, kèm nhật ký "agent nào, skill nào, làm gì".
### Đổi
- **Chi lớn của nhân viên chờ chủ duyệt** (hạn mức đặt được, mặc định 2 triệu); chủ báo thì ghi luôn. Hợp đồng hoàn thành thì Đối Soát lập báo cáo lãi lỗ.

## [1.3.36] - 2026-10-27
### Thêm
- **Nút "Nạp dữ liệu mẫu" trong CRM vận hành** (chủ và quản lý, khi phòng đang chưa có khách): tạo 4 khách mẫu kèm cơ hội và việc để xem giao diện có dữ liệu. Khách mẫu mang nguồn "Dữ liệu mẫu"; nút "Xóa dữ liệu mẫu" dọn sạch chúng, khách thật không bị đụng.

## [1.3.35] - 2026-10-27
### Thêm
- **Quản lý Shop dùng chung nhiều máy**: dữ liệu của 12 module (đơn bán, kho, thu chi, nhân sự, báo giá, phòng chat nội bộ...) trước chỉ nằm trong trình duyệt từng máy, nay được lưu lên máy chủ Joyce nên điện thoại và máy tính thấy cùng một bản. Chỉ chủ và quản lý (CEO, giám đốc, trưởng phòng, lead) thấy trang này vì có thu chi và nhân sự. Hai máy sửa cùng lúc thì bản lưu sau cùng thắng.
### Đổi
- Quản lý Shop nằm trong mục con của **Vận hành kinh doanh** cùng Nghiên cứu, Lộ trình, Cộng sự, Team, Chatbot, CRM vận hành.
- CRM vận hành tự chọn phòng đang có nhiều khách nhất (trước đây có thể rơi vào phòng trống nên mọi số liệu bằng 0 và cột hồ sơ trống). Tiêu đề các khung nhỏ về 14px như bản mẫu.

## [1.3.34] - 2026-10-27
### Thêm
- **Trang Quản lý Shop** trong mục Năng lực, theo đúng bản mẫu `JOYCE_QUAN_LY_SHOP_PROTOTYPE_V2.html`: thanh 14 module (Tổng quan bộ, CRM, Bán hàng, Đơn bán, Kho, Thu chi, Nhân sự, Trợ lý điều hành, Báo giá, Hộp chat, Chăm sóc, Marketing, Ảnh AI, Công việc), sơ đồ phòng ban, thẻ phòng và phòng chat nội bộ. Tab CRM khách hàng trong trang dùng CRM thật của Joyce; các module còn lại lưu dữ liệu trên trình duyệt như bản mẫu.
### Đổi
- CRM vận hành dùng bản `crm.js` mới nhất trong bộ bàn giao (thanh thông báo đồng bộ, hướng dẫn, định dạng tiền).

## [1.3.33] - 2026-10-27
### Đổi
- **CRM vận hành khớp bản HTML mẫu hơn**: cột trái gồm Thêm nhanh bằng AI, ô tìm và danh sách khách (kèm số điện thoại và số tiền đã chốt), cột phải là hồ sơ. Tab có icon và số đếm, có thêm dòng "Hướng dẫn dùng CRM" thu gọn, nút Sao lưu và Nhập khách (file .json hoặc .csv) ở góc phải thanh tab. Tên cột Pipeline viết hoa như mẫu.
### Sửa
- Nút và ô nhập trong CRM không còn bị to quá khổ so với thiết kế.

## [1.3.32] - 2026-10-27
### Đổi
- **CRM vận hành dùng bộ giao diện mới**: thêm nhanh khách bằng AI, hồ sơ 6 mục Joyce tự thu thập (có khoá từng mục), giao khách cho nhiều phòng, chọn từng mục đề xuất trước khi duyệt, quản lý giai đoạn pipeline và việc cần làm có bộ lọc.
- Người chỉ được xem không còn thấy nút sửa; báo lỗi rõ khi không có quyền hoặc máy chủ chưa nạp CRM.

## [1.3.31] - 2026-10-27
### Đổi
- **CRM vận hành bám sát bản thiết kế HTML**: thẻ số liệu có icon và dòng phụ (đã mua hàng, số cơ hội, tỉ lệ thắng, trễ hạn), thanh tab dạng viên kèm số đếm, cột trái gồm khung Thêm nhanh bằng AI (luôn mở, có nút Nhập tay), ô tìm và danh sách khách kèm số tiền đã chốt, cột phải là hồ sơ và tự mở khách đầu tiên. Màu vẫn theo giao diện sáng hoặc tối của Joyce.
### Sửa
- Chọn "Tất cả phòng" thì các thẻ cơ hội và đã chốt không còn hiện 0, mà cộng dồn các phòng bạn được xem.
- Menu bên: nhóm Năng lực không còn bị cắt cụt trên điện thoại; Nghiên cứu, Lộ trình, Cộng sự, Team, Chatbot, CRM nằm trong mục con của Vận hành kinh doanh.

## [1.3.30] - 2026-10-27
### Sửa
- **CRM vận hành báo rõ khi máy chủ chưa nạp CRM** (trước đó chỉ hiện "Not Found" trên trang trống): cần khởi động lại Joyce sau khi cập nhật. Khay "Thêm nhanh bằng AI" mở sẵn và có hướng dẫn một phút ở đầu Danh bạ, đúng như thiết kế.

## [1.3.29] - 2026-10-26
### Thêm mới
- **CRM vận hành**: tab riêng quản khách hàng cho các phòng (Danh bạ, Pipeline, Việc cần làm, Đề xuất, Phân khúc). Một khách thuộc nhiều phòng, mỗi phòng chỉ thấy cơ hội và việc của phòng mình. Pipeline có nút + và - để thêm xoá giai đoạn.
- **Cấp quyền từng nhân viên và từng phòng**: tab CRM mặc định ẩn. Ở trang Nhân viên chọn "Chỉ xem" hoặc "Dùng đầy đủ" cho từng tài khoản; chủ còn mở hoặc đóng CRM theo phòng, phòng nào được mở mới xem được. Chỉ chủ, CEO, giám đốc và trưởng phòng được xoá khách và nhập khách từ hộp thư.
- **Joyce tự thu thập hồ sơ khách**: đọc hội thoại, đề xuất nhu cầu, ngân sách, hạn; nhân viên duyệt từng mục mới vào hồ sơ. Chủ chọn Tắt, Chờ duyệt hoặc Tự áp. Có thêm "Thêm nhanh bằng AI" (dán đoạn chat) và "Ghi nhớ cách xử lý khách này" lên wiki phòng.
- Sửa chữ nút chính khó đọc ở khay Việc hằng ngày.

## [1.3.28] - 2026-10-26
### Thêm mới
- **Z.ai (GLM) thành bộ não thứ 12**: có sẵn model flash miễn phí (`glm-4.7-flash`, `glm-4.5-flash`, `glm-4.6v-flash`). Trang Models có khu "Não miễn phí", picker đánh chip FREE cho id đuôi `:free` (OpenRouter, TokenHarbor, 9router). Key chết thì thẻ tô đỏ kèm lý do và Joyce bỏ qua nhà đó khi dự phòng.
- **Nhân bản giọng**: nói "fake giọng anh" là Joyce ghi mẫu từ mic, lưu hồ sơ rồi đọc lại bằng giọng đó mãi (chạy trên máy, giấy phép phi thương mại). Nói "giọng cũ" để quay về giọng mặc định.
- **Nhạc tự nhỏ khi Joyce nói**: trình phát nhạc chuyển sang lõi Howler.js, phát stream nhanh hơn, âm lượng chuyển mượt. Có thêm nguồn nhạc trong máy và lệnh giọng ("mở nhạc lofi", "bài tiếp", "tắt nhạc").
- **Đổi cảnh nền avatar bằng giọng** và chip mục lục tri thức ngay trong khung chat trống.
- **Nhà máy Joyce (factory) và sweep bù**: sau khi việc xong, Joyce chạy lệnh kiểm chứng và tự mở việc sửa nếu hỏng; mỗi giờ quét mọi brain tìm việc đáng lẽ đã chạy mà lỡ rồi gửi một thư tổng hợp vào hòm thư. Số liệu hiện ở trang Sơ đồ.
- **Gọi tool theo ý nghĩa**: Joyce dịch câu hỏi sang tiếng Anh bằng model rẻ rồi so khớp với tên tool, nên "chốt đơn cho khách" tìm được `create_invoice`. Vẫn qua lớp lọc quyền như trước.
- **Học viên H2O Book trên màn hình 3D**, **đồng bộ Apple Notes** vào `sources/apple-notes/`, **Sevbot hỏi-đáp sự cố**, và hướng dẫn dùng Joyce trên xe hơi.
- Agent dùng Claude cũng có chuỗi dự phòng: nhà chết giữa chừng thì chuyển sang nhà khác khi chưa làm gì ra ngoài.

### Sửa
- Vá các chuỗi dịch còn sót gạch dài hoặc thẻ HTML.

## [1.3.27] - 2026-10-26
### Thêm mới
- **Việc hằng ngày ngay trong Trò chuyện**: mở chat là thấy các việc mẫu của phòng mình (tư vấn, chăm sóc, báo cáo...). Bấm một việc, điền vài ô là Joyce làm. Mỗi nhóm có nút **+** để tự thêm việc của phòng, bấm vào việc để sửa hoặc xóa.
- **Làm xong bấm "Đã xong"**: Joyce tự hỏi khi việc chạy xong, bấm là việc vào cột Xong ở Việc → Công việc của phòng. Bấm "Ghi nhớ cách làm này" để Joyce ghi cách làm thực tế vào wiki; đủ 3 lần làm một việc thì tự ghi nhớ.
- Có sẵn việc mẫu cho Bán hàng, CSKH và hai brain cá nhân (Thủy, Tuấn). Chọn "Toàn khối" thì nhân viên chỉ thấy việc của phòng chính.

## [1.3.26] - 2026-10-23
### Thêm mới
- **Trang Sơ đồ hệ thống**: một trang nhìn cả hệ thống Joyce - hiệu suất từng phòng ban theo board kanban thật, loop đang bật, dispatcher, các điểm cần chú ý. Có bộ lọc "Tất cả" và "Cần chú ý".

## [1.3.25] - 2026-10-21
### Thêm mới
- **Tầng tự cải tiến (PPC) theo mô hình Harness²**: Joyce học cách tối ưu harness (prompt, skill, agent) từ bằng chứng kết quả thật thay vì sửa theo cảm tính. Gồm 3 năng lực mới trong Brain Default - skill `cham-diem-tuong-phan` (chấm A/B ẩn danh, chống nịnh người chấm và chống lệnh nhúng trong bằng chứng), workflow `tu-cai-tien-agent` (Kỹ sư Cải tiến đề xuất -> Giám định Tương phản chấm ẩn danh -> phiếu chờ chủ duyệt, không bao giờ tự áp), loop `dinh-duong-bai-hoc` (mỗi ngày chưng cất bài học có bằng chứng từ việc đã chạy, tự mở đề xuất khi thấy agent lặp lỗi). Workflow và loop tạo ở trạng thái TẮT - bật ở trang Việc khi muốn dùng.
- **Thẻ "Tự cải tiến (PPC)" trong tab Tổng quan**: đếm đề xuất chờ duyệt trong `Joyce/proposals/`, số bài học và ngày nhật ký trong `Joyce/learn-log/`, lượt học gần nhất - đọc trực tiếp từ file vault nên không cần thêm cơ sở dữ liệu.

## [1.3.24] - 2026-10-20
### Thêm mới
- **Tinh vân kiểu chòm sao**: tab Tinh vân giờ có quả cầu của brain đang mở ở giữa (Trái Đất cho Brain Default, tinh cầu đúng phòng ban, ngôi sao cho brain thương hiệu) trong vòng vàng, quanh đó là các nhánh: xanh = tri thức, cam = vận hành, xám = kết nối MCP (nét đứt khi chưa bật).
- **Nhánh sáng theo việc thật**: Joyce đọc file trong `wiki` thì nhánh WIKI sáng, gọi Zalo thì nút Zalo sáng, hạt chạy từ lõi ra; Joyce nghĩ / nói thì cả mạng chạy nhanh hơn.
- **Bấm một nhánh** mở thẻ tổng quan: số note, % vault, các note mới nhất (bấm là mở). Nút **Mạng note** ở góc phải chuyển về đồ thị từng note như cũ (có timelapse).

## [1.3.23] - 2026-10-19
### Thêm mới
- **3D Joyce xuất hiện bằng hạt lượng tử**: mở tab 3D Joyce, các hạt phóng ra từ một đốm sáng dưới chân, xoắn thành dòng sao chổi rồi ghép thành hình người; ghép xong thì nhân vật quen thuộc hiện lên đúng chỗ đó. Giao diện sau đó giữ nguyên như cũ.
- **3D Joyce trích xuất dữ liệu khi làm việc**: khi bạn giao một việc (ví dụ "gửi anh bản hướng dẫn sale"), nhân vật phát sóng ánh sáng từ ngực, tia quét chạy dọc thân, người nghiêng và gật nhẹ mỗi lần lấy được dữ liệu. Tên tài liệu trong brain đang được đọc và các con số thật trong kết quả bay ra hai bên màn hình, bộ đếm "ĐANG DÒ DỮ LIỆU" chạy tổng số mục đã dò. Lúc trả lời, bộ đếm chốt "ĐÃ DÒ XONG" và ánh sáng nhịp theo giọng. Không có dữ liệu thì không hiện số bịa.

### Sửa lỗi
- Sửa các kiểm tra tự động đang đỏ (chữ gạch dài trong bản dịch, danh sách trang lệch, kiểm tra camera cũ).

## [1.3.22] - 2026-10-21
### Thêm mới
- **Bảng HUẤN LUYỆN cử chỉ tay** (`gesture-trainer.mjs`, mở từ nút "🎓 DẠY" cạnh HAND CAM trong 3D Joyce hoặc thẻ "Cử chỉ tay" trong Cài đặt): dạy Joyce nhận diện theo đúng tay người dùng thay vì ngưỡng chung. Mỗi cử chỉ **quét 3 lần với nhịp khác nhau** - hệ thống lấy trung bình + độ lệch làm ngưỡng khoan dung riêng; 3 lần lệch nhau quá thì báo quét lại chứ không lưu bừa. Bảng này CÓ khung xem trước camera (luyện phải thấy tay), khác chế độ điều khiển vẫn chạy ẩn.
- **Cử chỉ tự luyện gắn hành động**: giơ 2/3/4/5 ngón hay dáng tay bất kỳ (✌️🤟🖐✊👌 + preset) → chọn hành động trong 7 loại: sóng năng lượng, bảo Joyce ngừng nói, mở/lật-tới/lật-lùi/đóng album, toàn màn hình. Nhận diện bằng đặc trưng 5 ngón (`fingerVector` chuẩn hoá theo lòng bàn tay) khớp mẫu đã chốt; phải giữ dáng yên 450ms mới bắn nên tay đang di chuyển/vuốt không kích hoạt nhầm.
- **Hiệu chuẩn cử chỉ có sẵn**: luyện lại chụm ngón (pinch), xòe tay (palm), vuốt ngang (swipe) → engine đổi ngưỡng theo đo từ tay thật (pinchOn/Off, palmExtMin, quãng đường+tốc độ vuốt). Nút ↺ đưa về mặc định.
- **Dáng 5 ngón tự luyện thay palm mặc định**: nếu trong hồ sơ có cử chỉ ≥4 ngón duỗi, nó thay hẳn lệnh ngừng-nói gốc (palmSuppressed) - khớp đúng dáng tay chủ.
- **Hồ sơ lưu trên server**: `GET/PUT /hands/profile` → `STATE_DIR/hand_gestures.json`, validate chặt (tối đa 16 cử chỉ, action whitelist, vec/tol 5 float, calib trong biên an toàn). Bảng lưu xong phát sự kiện `joyce-hands:profile` → cam điều khiển đang chạy áp ngưỡng mới ngay không cần tắt mở.
- **Mở bảng luyện tạm ngừng cam điều khiển** (khỏi 2 worker đua CPU), đóng bảng thì mở lại nếu trước đó đang bật.

## [1.3.21] - 2026-10-21
### Thêm mới
- **Nút bung khoang não toàn màn hình** (⤢ cạnh icon mắt trong stage-tools): requestFullscreen trên `.hud-center` - ở lớp nhìn 3D Joyce thì toàn màn hình chỉ còn người ảo + giọng nói + camera, ESC hoặc bấm lại để thu về.
- **Vuốt tay mở ALBUM TRÌNH CHIẾU** (cử chỉ mới trong GestureEngine): quét ngón nhanh ≥0,28 khung hình trong <450ms phát swipe - vuốt phải/trái mở album rồi lật ảnh, vuốt xuống đóng. Album lấy ảnh từ brain **"Ban Hang - Sales Hinh Anh"** (endpoint mới `GET /album` quét `attachments/` + `sources/`, ảnh mở qua `/files/raw` sẵn có); trống thì báo cách bỏ ảnh vào.
- **Pho tượng thu nhỏ khi album mở**: `.hum-layer` co về 26% góc phải-dưới với hiệu ứng trượt, album chiếm trung tâm sân khấu.
- **Hai đầu ngón tay zoom album liên tục**: khoảng cách ngón cái-ngón trỏ (pinchRatio sẵn có trong kết quả tracking) map 1x..4,5x trực tiếp - dang 2 ngón phóng to, khép lại thu nhỏ. Chỉ tính khi đúng 1 tay và không phải pose palm (palm vẫn là cử chỉ ngừng nói).

## [1.3.20] - 2026-10-21
### Thêm mới
- **Điều khiển avatar bằng tay qua camera - bản Worker hoàn chỉnh** (`dashboard/joyce-hands/`): tích hợp JOYCE_HAND_GESTURE_KIT vào lớp nhìn 3D Joyce, chạy CHẾ ĐỘ ẨN - bấm "✋ HAND CAM" là camera tự xin quyền + nhận diện ngay, video sống ngoài DOM nên giao diện chỉ có Joyce (trạng thái báo qua nút CAM ON + dòng notice của avatar); bấm lại hoặc rời lớp nhìn thì tắt hẳn. Không bao giờ xin micro, xử lý toàn bộ tại máy - không khung hình/landmark nào rời trình duyệt.
- **Nhận diện chạy trong Worker riêng**, không còn `detectForVideo` trên main thread: ~15 suy diễn/giây, một khung đang chờ, kết quả cũ hơn 500ms bị bỏ, watchdog 4 giây, timeout nạp model 30 giây, tắt camera khi ẩn tab/pagehide/thoát lớp nhìn/huỷ avatar/stream chết. Worker chết thì báo lỗi rõ chứ không lén chạy lại trên main thread. Trước đây detect chạy ngay trong vòng lặp vẽ làm giật khung và không có watchdog.
- **Cử chỉ theo GestureEngine của kit** (dwell + hysteresis + cooldown), thay ngưỡng khoảng cách thô: chụm ngón giữ ≥160ms bắn ĐÚNG 1 sóng năng lượng cho tới khi nhả + 650ms; xòe lòng bàn tay giữ yên ≥650ms mới gửi yêu cầu ngừng nói (lắc tay reset thời gian giữ, nhả ≥200ms mới cho bắn lại, cooldown 1800ms); hai bàn tay vào khung thì phớt lờ chứ không nhảy quyền điều khiển; mất tay thì attention về giữa.
- **Attention lái đầu pho tượng** qua hook `setAttention(x,y)` mới (đầu quay + parallax hạt, cùng kênh với chuột); chụm ngón gọi `pulse()` đúng vị trí ngón; avatar phát `joyce-avatar:exit`/`dispose` để bridge tự tắt camera.
- **Lòng bàn tay = yêu cầu Joyce ngừng nói** qua `VoiceQuietGate`: chỉ ngắt khi avatar đang ở trạng thái "speaking" thật (đọc từ `#orbState`), gọi đúng đường `stopCurrent()` (= nút Dừng trong app.js - cắt TTS đang phát + huỷ lượt của đúng phiên, mic/cuộc gọi không bị tắt). Không nói thì chỉ pulse nhẹ báo nhận, không làm gì.
- **Dùng lại toàn bộ model + runtime MediaPipe sẵn có** ở `/static/humanoid/` - không nhân bản ~28MB, không CDN. Panel hỗ trợ sáng/tối, phím Escape đóng + trả focus, responsive mobile.
- Test `tests/js/test_joyce_hands.js`: 47 kiểm tra - đủ ngữ nghĩa cử chỉ (dwell/hysteresis/cooldown/release), mất tay, tay nhỏ, mirror, và toàn bộ khớp nối tĩnh.

## [1.3.19] - 2026-10-20
### Thêm mới
- **Sổ mức dùng theo LOẠI TÁC VỤ** (`STATE_DIR/task_usage.json`): mọi engine việc nền giờ chạy qua một lớp đếm chung trong `swap()`/`_FallbackChain` - mỗi lượt ghi loại việc (nhắc hẹn, loop, Kanban, tự học...) + provider/model THẬT SỰ đã chạy lượt đó (mắt dự phòng chạy thì tính cho mắt đó) + token vào/ra + tiền thật nếu provider trả về. Rollup theo ngày, giữ ~2 tháng, không ghi lượt 0-token rỗng. Đây là sổ riêng cạnh `usage.json` (sổ đó gộp theo provider|model cho trang Mức dùng), không đếm trùng.
- **Bảng Phân việc não hiện 30 ngày qua thật**: mỗi loại việc có cột mức dùng - số lượt, tổng token (gộp vào/ra), não nào đã gánh, và con số $ ƯỚC TÍNH theo `usage_pricing.json` (model ':free' và model chưa có giá hiện $0, không bịa số). Tiền thật provider trả về (Claude Code CLI) được giữ riêng, không bị ước tính đè.
- **Đề xuất não theo kết quả đã dùng**: mỗi loại việc có chip đề xuất - "đang theo gợi ý" khi provider hiện tại nằm trong danh sách curate; "nên đổi sang X" khi một nhà gợi ý đã nối sẵn key/endpoint mà việc chưa chạy trên nó; "đang tốn ~$X/30n" khi đang đốt tiền thật mà còn mắt miễn phí chạy được; "chưa nối nhà gợi ý nào" khi chưa cấu hình. Đề xuất chỉ chỉ vào provider chủ ĐÃ nối thật, không xúi nối thêm.
- **Ghi sổ không rơi mất qua strip_tools**: lớp bóc tool cho lượt không-tin-cậy (phán xét trả lời nhóm) giờ giữ nguyên gắn loại việc khi dựng lại chuỗi engine.
- **i18n**: tiếng Đức được dịch đủ toàn bộ trang Phân việc não (trước thiếu hẳn khối rt.*).
- **Khung dọc API key cho từng provider** (card Vòng quay key): thay ô dán nhiều dòng bằng danh sách key từng dòng - mỗi key một hàng có số thứ tự, đuôi key, trạng thái cháy và nút × xoá riêng; ô nhập + nút "Thêm key" (hoặc Enter) thêm không giới hạn số key, trùng thì từ chối. Endpoint mới `/key-rings/add` + `/key-rings/remove` để thao tác từng key mà không cần gửi lại nguyên vòng; gỡ key cuối cùng cũng xoá luôn key chính (trước để lại key ma vẫn chạy được).
- **Chuỗi dự phòng việc nền - nhảy provider** (card mới trong Phân việc não, `settings.model.aux_fallbacks`): chủ xếp thứ tự provider cho việc nền - mắt chính của loại việc chết quota/hết SẠCH key thì nhảy sang provider kế, mỗi nhà vẫn tự xoay hết vòng key của nó trước. Chuỗi đứng SAU mắt chính và TRƯỚC các mắt máy đoán (Claude → não chính → OpenRouter free). Khác chuỗi chat: nhận cả provider đăng nhập gói (OpenAI OAuth/Codex-gmail, Grok CLI, Antigravity) vì việc nền xoay theo engine. Ví dụ cấu hình: Gemini (nhiều key) → Groq → OpenAI OAuth.
- **Nút "Đặt lại tất cả về mặc định" bắt gõ RESET xác nhận**: một cú click nhầm là cả bảng phân việc mất - giờ hiện ô nhập chữ (cùng kiểu gõ-tên khi xoá brain), gõ sai hay Huỷ thì không làm gì. Lời nhắc nói đúng phạm vi: chỉ task_models bị gỡ, vòng key + chuỗi dự phòng chat không bị động vào.

### Sửa
- **Ô model không gợi ý sau khi đổi provider** (cả hàng não dự phòng chat lẫn bảng việc nền): datalist chỉ vẽ một lần theo provider lúc render nên đổi nhà vẫn giữ model cũ hoặc trống. Giờ đổi provider là nạp lại gợi ý; riêng nhà catalog động (OpenAI Compatible, Ollama Local, Ollama Cloud, Codex) còn gọi `/provider/models` hỏi danh sách LIVE - kể cả hàng đã lưu provider từ trước cũng tự nạp ngay khi mở trang.

## [1.3.18] - 2026-10-20
### Thêm mới
- **Chuỗi dự phòng cho CHAT trực tiếp** (card "Chat trực tiếp" trên trang Phân việc não): khung chat dashboard, Telegram và các kênh trực tiếp trước chỉ có thử lại tạm thời trên cùng provider - hết quota là lượt chết, không ra lệnh được từ Telegram. Giờ chủ xếp sẵn một chuỗi não dự phòng có thứ tự; khi não chính trả lỗi quota/key chết, Joyce duyệt từng mắt theo đúng vòng quay key của nó rồi mới nhảy mắt kế, trong cùng một lượt và giữ nguyên ngữ cảnh hội thoại + MCP tools.
- **An toàn khi đổi não**: chuỗi chỉ đổi provider khi lượt CHƯA phát nội dung nào ra ngoài - đã có chữ, tool_call hay usage là dừng xoay ngay, vì chạy lại trên nhà khác sẽ nhân đôi hành động thật (gửi tin hai lần, ghi file hai lần). Lỗi không phải quota (500, timeout, model không tồn tại) cũng không bị xoay mò.
- **Chuỗi chủ tự xếp đi trước chuỗi máy đoán trên Telegram**: `_fallback_chain` sẵn có (CLI đã cài → Ollama local → Groq → API khác) giờ ưu tiên `chat_fallbacks` do chủ chọn trước, heuristic chỉ chạy sau. Dashboard với não chính là gói CLI vẫn giữ hành vi cũ (binary không xoay bằng cấu hình được).
- **Card "Chat trực tiếp" trong trang Phân việc não**: hiện não chính đang chạy (đổi ở trang Models), danh sách não dự phòng thêm/xoá/lên-xuống thứ tự, chỉ nhận provider API; bảng việc nền đổi tiêu đề rõ "việc NỀN" để không lẫn với khung chat.

## [1.3.17] - 2026-10-20
### Thêm mới
- **Trang "Phân việc não" mới** (nhóm Kết nối, cạnh Models): liệt kê mọi loại việc nền thật sự gọi LLM - nhắc hẹn/cron, vòng lặp, việc Kanban, tiêu hoá nguồn, bản tin, quyết định trả lời nhóm, phán xét agent, tự học - và cho gán từng loại một provider/model riêng thay vì chỉ một model việc nền chung. Mỗi loại kèm mô tả việc là gì và gợi ý provider free/hợp lý; để trống thì vẫn theo model việc nền chung trên trang Models như cũ. Khi provider được gán chết lúc chạy, việc vẫn rơi xuống chuỗi dự phòng như trước.
- **Vòng quay nhiều API key cho một provider**: mỗi provider API (Gemini, Groq, OpenRouter, DeepSeek, OpenAI, Anthropic, Ollama cloud) giờ nhận nhiều key của các tài khoản hợp lệ chủ tự đăng ký - dán mỗi dòng một key trên trang Phân việc não. Key nào bị từ chối vì hết quota/429/lỗi xác thực sẽ "cháy" một thời gian (ước lượng theo nội dung lỗi: lỗi phút chờ ~1 phút, lỗi ngày chờ tới nửa đêm UTC) và Joyce tự nhảy sang key kế ngay trong cùng lượt, trước khi chuỗi fallback tới engine khác. Trạng thái cháy lưu ở `key_burns.json` nên restart server cũng không thử lại key vừa cháy; trang hiển thị đuôi key, số lượt mỗi key gánh và nút mở khoá tay - không bao giờ lộ key đầy đủ.
- **Attribution theo key**: lượt và token ghi về đúng key slot đang dùng (nhận diện bằng fingerprint + 4 ký tự đuôi), để thấy tài khoản nào đang gánh việc mà không lưu key thô trong sổ.

## [1.3.16] - 2026-10-19
### Sửa lỗi
- **Tunnel + gửi link nhận lầm cloudflared của app khác**: `tunnel_notify` và watchdog trước chỉ lọc theo tên tiến trình `cloudflared.exe`, nên khi H2O Video Studio chạy tunnel riêng (port 5170) chúng tưởng tunnel của Joyce (:7777) vẫn sống - server mới boot xong sẽ không mở tunnel mới và không gửi link về Telegram; thao tác refresh còn giết nhầm tunnel của app kia. Giờ nhận diện/giết theo command line trỏ về :7777, tunnel hai app song song hoàn toàn độc lập.
- **Joyce không tự khởi động sau khi mở máy**: đăng ký tự chạy (Run key `JoyceOS` + 2 scheduled task) đã biến mất sau đêm 18/10 nên sáng 19/10 server không lên và không gửi link - đã tái đăng ký. Nếu lặp lại, nghi phần mềm dọn máy/AV gỡ mục khởi động - kiểm tra danh sách cho phép của AV hoặc mở trang Cài đặt bấm "Bật lại" tự khởi động.

## [1.3.15] - 2026-10-19
### Thêm mới
- **Đầu pho tượng quay trái/phải như bản tham chiếu**: shader giờ nén ngang theo góc yaw (foreshorten) và cho vùng mặt trong trượt nhiều hơn viền silhouette, tạo cảm giác quay đầu khoảng 20 độ thay vì chỉ nghiêng nhẹ. Đầu bám con trỏ hoặc đầu ngón trỏ (khi bật HAND CAM), tự đung đưa nhẹ khi thả trôi; lớp hạt bụi xoay cùng góc nên không phản bội ảo giác.
- **Hiệu ứng nói có nhịp**: lõi miệng đập theo nhịp sin + biên độ tiếng, lớp hạt rung mạnh hơn khi đang nói, và mỗi lần giọng vọt ngưỡng phát một vòng sóng lan từ miệng - phản ứng tần số đọc như nhịp thở thay vì trơn đều.

## [1.3.14] - 2026-10-19
### Thêm mới
- **Nhận diện bàn tay thật qua camera trong 3D Joyce**: nút "HAND CAM" bật camera (chỉ khi bấm), MediaPipe HandLandmarker chạy tại máy - đầu ngón trỏ lái sự chú ý của pho tượng, chụm ngón cái + trỏ tạo sóng năng lượng, mở lòng bàn tay làm pho tượng dịu lại. Camera tự tắt khi thoát lớp nhìn/đổi tab, tự mở lại khi quay về; có ô preview nhỏ góc phải và cảnh báo rõ không gửi hình ảnh đi đâu.
- **Cảm giác 3D hơn**: pho tượng nghiêng nhẹ theo con trỏ/bàn tay (parallax shear trong shader), kết hợp sự chú ý vùng mặt đã có.

### Sửa lỗi
- Thẻ hologram Joyce (ảnh giọt nước + SCANNING) không còn đè lên mặt pho tượng khi đang gọi ở lớp nhìn 3D Joyce - pho tượng chính là gương mặt cuộc gọi. Về Lõi nước giữa cuộc gọi thẻ hiện lại bình thường.

## [1.3.13] - 2026-10-19
### Thêm mới
- **3D Joyce nâng cấp lên renderer tham chiếu APEX**: lớp nhìn giờ dùng bộ render lấy cảm hứng apex-humanoid (plates WebP + trường hạt 2.5D) do Astra chuẩn bị - hình người contour rỗng ruột, não vàng, sống lưng tết và địa hình năng lượng đúng hình mẫu, thay pho tượng tham số hoá trước đó. Cảnh lắp ráp, nút EXIT (quay về Lõi nước), ripple khi chạm vào pho tượng và sự chú ý theo con trỏ đi kèm sẵn.
- Trạng thái và mức âm thật của Joyce vẫn lái hình: LISTENING/THINKING/SPEAKING đổi đúng plate, mức mic/loa khuấy lõi và vùng miệng; không tạo đường mic thứ hai.
- **Dự phòng tự động**: thiếu renderer APEX, thiếu assets hoặc lỗi khởi tạo thì pho tượng hạt tham số hoá (bản 1.3.12) tự thay thế - lớp nhìn không bao giờ trống. Plates APEX nằm trong `dashboard/humanoid/` và đang được giữ local (license artwork chưa xác minh, không đẩy lên git).

## [1.3.12] - 2026-10-19
### Thêm mới
- **Lớp nhìn "3D Joyce" thay "3D View"**: tab đầu của khoang não giờ hiện pho tượng bán thân dựng từ hơn 13 nghìn hạt phát sáng (WebGL2 thuần, không thư viện ngoài) thay cho chế độ tinh cầu siêu nét cũ. Pho tượng phản ứng theo trạng thái thật của Joyce: lơ lửng khi sẵn sàng, nghiêng tới trước khi lắng nghe, hạt quay vòng khi đang nghĩ, khuấy động theo mức âm khi nói, mờ đi khi bị ngắt, tông đỏ khi lỗi. Vùng miệng và lõi não vàng cam đập theo giọng nói.
- Mở lớp nhìn lần đầu có cảnh hạt lắp ráp thành hình; tinh cầu bên dưới mờ thành phông sao nhưng vệ tinh và sao tri thức vẫn bấm được. Lựa chọn được nhớ giữa các phiên.
- Kế thừa đầy đủ cơ chế an toàn của tinh cầu: bốn hồ sơ chất lượng (cao/cân bằng/nhẹ/tối giản), tự hạ bậc khi FPS thấp, dựng lại khi mất ngữ cảnh WebGL, tôn trọng prefers-reduced-motion.

## [1.3.11] - 2026-10-18
### Thêm mới
- **Cài giờ cho việc định kỳ không còn phải tự cộng phút**: form tạo/sửa việc lặp đổi ô "chu kỳ (phút)" thành preset dễ chọn (mỗi 15 phút, mỗi giờ, mỗi ngày, mỗi tuần...) kèm ô tuỳ chỉnh ngày - giờ - phút.
- **Ghim giờ chạy cố định hằng ngày**: việc lặp có chu kỳ từ 1 ngày trở lên chọn được giờ chạy cố định (ví dụ "mỗi ngày lúc 21:00") thay vì trôi theo mốc lần chạy trước. Việc mới đợi đúng giờ đã ghim kể từ lúc bật, không chạy bù các mốc đã lỡ.
- Thẻ việc, trang Tổng quan, Cẩm nang và chỉ mục năng lực gửi engine hiển thị chu kỳ bằng tiếng người ("mỗi ngày lúc 21:00") thay vì "mỗi 1445 phút".

## [1.3.10] - 2026-10-15
### Thêm mới
- **Sửa chat ID Telegram sau khi đã kích hoạt**: trong màn chi tiết học viên ở tab Lộ trình, trưởng phòng thêm, đổi hoặc xoá chat ID để Joyce nhắn bài hằng ngày đúng người. Có nút gửi thử để biết học viên đã bấm Start với bot chưa.
- **Bản dự phòng bot Telegram**: trang Kênh có thẻ Bản dự phòng cạnh thẻ Telegram, giữ token (chỉ hiện 4 ký tự cuối) và chat ID. Joyce tự lưu mỗi khi bot chạy được; lỡ mất cấu hình thì bấm Dùng lại bản này.

### Sửa lỗi
- Token Telegram, Zalo và các khoá API không còn bị xoá trắng khi Joyce tạm thời không giải mã được chúng.

## [1.3.9] - 2026-10-15
### Thêm mới
- **Tab Lộ trình**: trưởng phòng bấm Kích hoạt lộ trình cho người mới, chọn mentor và ngày bắt đầu. Mỗi ngày bài học tự mở cho học viên, có chat ID Telegram thì 7 giờ sáng Joyce tự nhắn tên bài.
- **Bài kiểm tra chấm tự động, không tốn quota**: học viên làm trắc nghiệm ngay trong tab, nộp tối đa hai lần, lựa chọn được xáo riêng cho từng người nên không đoán theo vị trí được.
- **Mentor chấm, trưởng phòng kết luận**: Gate 1, khảo sát tuần, rubric 100 điểm và must-pass nhập ngay trong tab. Joyce đưa đề xuất Đạt, Cần bổ sung hay Trưởng phòng xem xét kèm lý do, người bấm kết luận cuối.
- Học việc Makeup có sẵn 15 bài (ngày 0 đến 14) soạn từ quy trình thật của phòng Makeup. Ngày nghỉ được duyệt không tính, lịch tự lùi.

## [1.3.8] - 2026-10-15
### Thêm mới
- **Lệnh Telegram `/link`**: nhắn `/link` cho bot là nhận lại đường link đăng nhập Joyce đang chạy, không phải mở máy để xem.
- **Lệnh Telegram `/openclaw mo` và `/openclaw tat`**: bật hoặc tắt cổng OpenClaw từ xa ngay trong Telegram.
- Trên Windows, Joyce nhận ra Grok Build cài bằng bộ cài của x.ai (thư mục `~/.grok/bin`).

### Sửa lỗi
- Khi não chính lỗi và các não dự phòng cũng lỗi, Joyce báo đúng lỗi gốc (ví dụ hết hạn đăng nhập) thay vì lỗi của một não bạn không chọn.

## [1.3.7] - 2026-10-11
### Thêm mới
- **Trang Nghiên cứu**: một chỗ để xem ý tưởng concept đang ở bước nào, thư viện concept, SOP liên quan, bản tin xu hướng và nhật ký quyết định của phòng Nghiên cứu concept hình ảnh.
- **Phân loại ý tưởng**: ý tưởng gửi vào phòng ghi rõ là concept, quy trình mới hay sửa quy trình cũ, để kết quả không lẫn vào nhau.
- **Linh vật mặc định là ngôi sao cam**, đúng logo của Joyce. Ai đã tự chọn hình thì giữ nguyên lựa chọn của mình.

## [1.3.6] - 2026-10-10
### Sửa lỗi
- Mục "Hôm nay" đẩy việc tóm tắt bằng AI không còn rơi mất các mục do một lỗi bị nuốt im lặng.
- Đường dẫn file kiểu Windows (`E:\...`) trong câu trả lời chỉ hiện thành link khi file thật sự nằm trong brain, không còn hiện link chết.
- Trang Nhật ký cập nhật tải theo từng trang và có bộ nhớ đệm, mở nhanh hơn và không tải lại cả kho mỗi lần.
- Trên Windows: giờ Việt Nam đúng ngay cả khi thiếu dữ liệu múi giờ, và các lệnh chạy nền không còn bật cửa sổ đen.

## [1.3.5] - 2026-10-10
### Thêm mới
- **Trưởng phòng xem được phòng của mình**: tab Phòng ban và Tài liệu chưng cất hiện với trưởng phòng, chỉ gồm phòng và tài liệu của phòng đó. Quản trị vẫn xem tất cả, nhân viên thường không thấy hai tab này.

### Sửa lỗi
- Số việc trên mũi tên sơ đồ khối không còn bị đếm trùng: việc vừa kẹt vừa chờ duyệt từng được cộng hai lần.
- Mục "hay mở" trong Tri thức phòng không còn hiện ngày 01/01, và file đã xoá không còn xuất hiện ở đó.
- Tri thức phòng ghi rõ khi còn tài liệu chưa hiện, thay vì cắt im lặng. Con số trên đầu khớp với toàn bộ tài liệu.
- Bấm "đã xem" liên tục hoặc nhiều người cùng bấm không còn làm mất dấu của nhau.

## [1.3.4] - 2026-10-09
### Thêm mới
- **Chọn cả khối trong ô chọn brain**: ngoài từng phòng, giờ có mục `★ Toàn khối Bán Hàng` ghim đầu mỗi nhóm, kèm tổng số note của cả khối. Đứng ở đó hỏi "tổng doanh số cả khối" thì Joyce đọc được dữ liệu của mọi phòng trong khối, còn ghi thì vẫn vào đúng brain của từng phòng.
- **Thùng rác, phục hồi được**: xoá file, thư mục, trợ lý, kỹ năng hay quy trình giờ chuyển vào thùng rác giữ 30 ngày thay vì mất hẳn. Mở bằng nút **Thùng rác** ở trang Tệp tin, mỗi mục có nút Phục hồi.
- **Tab Phòng ban vận hành**: sơ đồ luồng khách giờ ghi số việc đang ùn ngay trên mũi tên và tô đỏ chỗ có việc kẹt, nhìn một cái là thấy nút thắt. CSKH và Kế Toán tách thành dải chạy dọc phía dưới vì chúng chạm vào mọi chặng chứ không nằm ở một khúc.
- **Mở quy trình thẳng từ phòng**: bấm một phòng rồi xem toàn màn hình, ba cột Trước - Trong - Sau giờ liệt kê đúng các file quy trình đang có. Bấm một quy trình là nhảy sang chat, đã chuyển sẵn brain phòng và điền sẵn câu lệnh để nhờ Joyce rà và chuẩn hoá.

### Sửa lỗi
- Gọi lấy lại link truy cập không còn làm đứng cả máy chủ gần một phút, và lệnh làm mới nay thực sự mở lại được tunnel khi link cũ chết.
- Watchdog không còn tự bật lại tunnel khi anh cố ý tắt (tạo file `tools/tunnel-off.flag` để giữ tắt).
- Tài khoản nhân viên không còn đọc được mã nguồn plugin, nơi thường chứa khoá API.
- Hai người cùng sửa một file plugin không còn ghi đè mất bài của nhau.

## [1.3.3] - 2026-10-08
### Thêm mới
- **Kéo thả tinh thể kiến thức**: sau khi Big Bang nổ, kéo bất kỳ tinh thể nào bằng chuột hoặc ngón tay trên điện thoại sang vị trí mới. Tinh thể đang kéo sáng lên, các tinh thể khác mờ đi, thả ra có hiệu ứng hạ cánh. Bấm mà không kéo vẫn mở chi tiết như cũ.
- **3 chế độ xem kết quả tìm kiếm** (3 nút tròn dưới màn hình khi có Big Bang):
  - **✦ Bầu trời** (mặc định): giữ nguyên vị trí trên vòm trời.
  - **◎ Quỹ đạo**: xếp tinh thể thành 3 vòng tròn đồng tâm theo kích thước (to/vừa/bé); kéo tinh thể vòng trong dời cả 3 vòng.
  - **△ Chòm sao**: xếp thành 3 tam giác theo kích thước.
- Chuyển chế độ có hoạt ảnh 0.6 giây, vòng quỹ đạo và tam giác vẽ nét đứt làm khung hình.
- **Kéo dịch thiên hà**: ở tầng thiên hà (zoom nhỏ), kéo chuột/ngón tay giờ dịch chuyển toàn bộ tầm nhìn thay vì xoay quả cầu, giúp bấm được các tinh cầu phòng ban ở rìa màn hình. Chạm đúp hoặc bay tới tinh cầu sẽ reset vị trí.
- **Kéo tinh cầu và khối phòng ban**: ở tầng thiên hà, kéo lẻ một tinh cầu sang vị trí mới, hoặc kéo nhãn khối (ví dụ "Kế Toán") để dời cả cụm tinh cầu trong khối đó. Bấm mà không kéo vẫn bay tới tinh cầu như cũ. Con trỏ đổi thành bàn tay khi rê trên tinh cầu.
- **Kéo nhóm tam giác**: ở chế độ Chòm sao, kéo bất kỳ tinh thể nào sẽ dời cả tam giác cùng nhóm.
- **3D View**: nút mới trên thanh chuyển lớp nhìn (3D View | Lõi nước | Tinh vận). Bật lên để xem tinh cầu ở chế độ HD siêu nét: shader biên dịch lại với 6 tầng fbm, sao nền dày hơn với kích thước khác nhau và tia nhiễu xạ, sao băng ngẫu nhiên trong shader, hố đen có đĩa bồi tụ hai tần số nhiễu loạn và gradient cam-trắng giàu hơn, khí quyển dày hơn, ánh specular 3 tầng (120/30/8), fresnel rộng với ánh cyan ban đêm, tone mapping nâng cao. Canvas 2D cũng nâng cấp: bụi thiên thể lấp lánh quanh hành tinh, sao băng ngẫu nhiên bay qua bầu trời, mặt trăng phân giải lên 512px với quầng sáng mềm hơn, tinh thể kiến thức có hào quang, mặt trời có 6 tia quầng corona xoay. Phù hợp trình chiếu cho team. Click "Lõi nước" để quay về chế độ nhẹ.
- **Peek vùng dưới**: ẩn mắt xem (chế độ Quan sát), rê chuột hoặc chạm vào vùng dưới chữ SẴN SÀNG sẽ hiện 3 nút chế độ xem.

### Cải thiện
- Vùng click tinh thể kiến thức mở rộng từ 9px lên 15px, dễ bấm trúng hơn.
- Nút "Nghe thử" giọng nói giờ dùng TTS đọc text thay vì phát file MP3 thu sẵn, đúng tên "Joyce".
- Câu mẫu nghe thử đổi từ "HoaiMy/NamMinh" sang "Joyce".

## [1.3.2] - 2026-10-08
### Cải thiện
- **Cẩm nang → Fanpage**: mỗi Trang giờ có nút ↗ mở thẳng sang trang Facebook tương ứng (tab mới), không phải copy ID dán lên trình duyệt nữa. Bấm vào tên Trang vẫn chọn để xem báo cáo như cũ.

## [1.3.1] - 2026-10-08
### Thêm mới
- **Tab Kinh doanh** mới trong nhóm Năng lực, mở ra mục con **Xưởng content AI**: trung tâm tạo nội dung của H2O với 8 kiểu đầu ra chuẩn (trang bán hàng, ảnh ads, carousel, slide, bìa reel, ebook, banner, bộ nhận diện), bảng công việc theo trạng thái, hàng chờ duyệt, thư viện đầu ra và Brand Kit cho cả H2O Studio lẫn Thủy H2O Academy. Số liệu trong màn hình là mẫu minh hoạ; nối nguồn thật sẽ theo thiết kế.
- Nói "mở kinh doanh" hay "mở xưởng content" với Joyce cũng tới đúng trang này.

## [1.3.0] - 2026-10-08
### Thêm mới
- **Thiên hà phòng ban**: thu nhỏ tinh cầu (hoặc bấm nút **Thiên hà**) là thấy 44 tinh cầu phòng ban gom thành 11 cụm theo khối, xoắn quanh Trái Đất. Mỗi khối một kiểu: Kế Toán vàng có vành, Nhân Sự xanh lá, Marketing cam có bão, Sản Xuất dung nham, Nghiên Cứu tím tinh thể, CSKH đại dương, Vệ Sinh băng, ThuyH2O hồng kim tuyến...
- Tinh cầu to theo số tài liệu, sáng theo hoạt động tuần, vòng đỏ khi có việc kẹt, hố đen nhỏ khi còn tài liệu thô, mặt trăng là trợ lý của phòng. Rê chuột xem số liệu.
- **Bấm vào tinh cầu phòng ban là bay tới và đổi luôn brain đang mở** (khung chat, VAULT đổi theo); tinh cầu mang màu của khối, hố đen, Big Bang, sợi sáng hoạt động như Trái Đất. Nút **← Trái Đất** để về. Chọn brain phòng ở ô chọn cũng bay vào đúng tinh cầu đó.
- Tìm ở ô VAULT khi đang xem thiên hà: phòng nào có tài liệu khớp thì sáng lên kèm số; bấm vào là Big Bang luôn.

## [1.2.2] - 2026-10-08
### Cải thiện
- Bỏ vệt nền trắng xám cong phía trên hố đen; chỉ còn các hạt bụi li ti chảy vào hố.

## [1.2.1] - 2026-10-08
### Cải thiện
- **Dải ngân hà nằm ngang, hơi nghiêng, chạy qua sau tinh cầu** về phía hố đen, tông tím xanh có mây hồng, dịu để không lấn tinh cầu.
- **Vành đai bụi sao vòng quanh tinh cầu** như một chiếc vòng: nửa sau khuất sau tinh cầu, nửa trước chạy ngang trước mặt, quay rất chậm.

## [1.2.0] - 2026-10-08
### Cải thiện
- **Hố đen thành đĩa xoáy bồi tụ như ảnh mẫu**: xoắn ốc nghiêng, sát lòng hố trắng vàng, ra ngoài hồng cam rồi tím xanh, lòng hố tối viền đỏ cam, các nhánh tự cuộn khi xoay. Nhìn từ xa hay bấm vào phóng to đều cùng một kiểu.
- **Mưa sao băng khi nạp xong**: mỗi tài liệu vừa nạp là một sao băng từ hố đen bay về H2O, đầu bùng cam khi vào khí quyển rồi loé ở ghim H2O. Nạp nhiều thì thành trận mưa sao băng. Khi hỏi Joyce vẫn giữ sợi sáng như cũ.

## [1.1.2] - 2026-10-08
### Cải thiện
- **Hố đen nằm ngang như phễu xoáy**: bấm vào hố đen giờ thấy một phễu nhìn chéo từ trên, bụi đá tinh thể nhiều cỡ cuộn theo nhánh xoắn ốc rơi xuống miệng hố ở đáy, tinh thể dữ liệu thô nằm trên vách phễu; hết cảnh đĩa tròn đen dựng đứng.
- Quanh hố đen ở bầu trời thường là bụi và mảnh đá màu đá nhạt bị hút vào, không còn vệt xanh lam như đèn neon.

## [1.1.1] - 2026-10-08
### Sửa lỗi
- **Tia tri thức chạy cả với bộ não Codex**: trước chỉ có vòng sóng quét mà không có sợi sáng, vì Codex đọc file bằng câu lệnh và nói một câu mở đầu trước khi đọc. Giờ nhận ra file trong câu lệnh, và tài liệu Joyce trích dẫn ở dòng "Nguồn" cũng thành sợi sáng về H2O và chip "Nguồn tri thức".

## [1.1.0] - 2026-10-08
### Thêm mới
- **Tia tri thức khi hỏi Joyce**: gửi câu hỏi là từ ghim H2O phát vòng sóng quét bầu trời. Mỗi tài liệu Joyce thật sự đọc thì ngôi sao (hoặc viên đá vụn) đó bừng sáng và có sợi sáng chạy về H2O. Joyce bắt đầu trả lời thì các sợi co về và ghim H2O loé sáng.
- Joyce lấy dữ liệu từ app H2O thì tia đi từ đúng vệ tinh / Mặt Trời của app đó; từ Facebook, Zalo, Internet thì đi từ cổng ở mép trái có ghi tên nguồn. Không đọc tài liệu nào thì chỉ một nhịp sáng nhẹ ở lõi địa cầu, không bịa tia.
- **Hàng chip "Nguồn tri thức"** dưới câu trả lời: tài liệu Joyce đã đọc, bấm là mở file.

## [1.0.9] - 2026-10-08
### Cải thiện
- **Bấm vào thiên thể giờ mở theo hai bước**: trước tiên là thẻ tóm tắt nhỏ (đầu mục, thuộc phòng nào), bấm **Mở** trên thẻ mới mở khung đọc file lớn. Mở được cả file ở brain phòng ban khác.

## [1.0.8] - 2026-10-08
### Sửa lỗi
- **Số tài liệu thô không còn bị đếm đôi**: mỗi file Word đều có một bản chữ trích ra đi kèm, trước đây thành hai viên đá vụn. Giờ 47 brain đúng 261 tài liệu thô (trước báo 477), và Đọc nhanh file Word ra được đầu mục thật.
### Thêm mới
- **Khối KHO TRI THỨC trong khung TÍN HIỆU GẦN** (góc phải trên): tổng số tài liệu và chia đúng như bầu trời: sao đã chưng cất (bao nhiêu quy trình), kỹ năng, quy trình Joyce, trí nhớ doanh nghiệp, đá vụn tài liệu thô, kèm số theo từng thương hiệu.

## [1.0.7] - 2026-10-08
### Sửa lỗi
- **Bấm vào ngôi sao, chấm hay tinh cầu kiến thức là mở thẳng file đó** để đọc, kể cả file nằm ở brain phòng ban khác khi đang xem bầu trời gộp ở Brain Default. Thẻ Đọc nhanh vẫn còn phía sau, đóng file là thấy.

## [1.0.6] - 2026-10-08
### Cải thiện
- **Big Bang làm lại theo góp ý**: tinh cầu kiến thức giữ nguyên chỗ trên bầu trời và phóng to tại chỗ, mặt đá lồi lõm có miệng hố và quầng màu dải ngân hà. Các thiên thể quanh nó lao vào, nổ lửa vàng rồi nổ xanh chưng cất có hai tia sáng; Mặt Trời chiếu dần, tài liệu khớp nhất sáng nhất.
- **Hố đen luôn xoay chậm**, có luồng bụi bị hút vào và tài liệu thô chờ quanh đó; đang nạp dữ liệu thì xoáy nhanh hơn.
- **Bấm giữa hố đen để nhìn sâu vào**: đĩa bồi tụ, tia phản lực, tinh thể dữ liệu thô mang đúng tên file va vào nhau, nổ và chưng cất. Bấm bất kỳ đâu hoặc Esc để ra.
- **Nạp xong**, tia sáng bắn đúng vào ghim H2O Studio ở Hải Phòng, và tài liệu vừa chưng cất sinh thành sao mới bay từ đó lên trời.

## [1.0.5] - 2026-10-08
### Thêm mới
- **Big Bang khi tìm kiếm**: gõ từ khoá ở ô VAULT rồi bấm Enter (hoặc ngừng gõ một chút), bầu trời tối lại, các thiên thể liên quan bay về một điểm, va vào nhau thành vụ nổ, rồi nở ra thành **chòm sao tinh cầu nhỏ** quanh địa cầu để chọn.
- Admin ở Brain Default tìm được kiến thức của **mọi phòng ban**, không chỉ brain đang mở. Kết quả khớp nhất to nhất, nằm giữa; tài liệu nào liên kết tới nhau thì có vệt sáng nối.
- Rê chuột lên dòng kết quả là tinh cầu tương ứng sáng lên, và ngược lại. Bấm tinh cầu để Đọc nhanh; xoá ô tìm thì chòm sao bay về chỗ cũ.

## [1.0.4] - 2026-10-08
### Thêm mới
- **Bầu trời tri thức quanh quả tinh cầu**: mỗi tài liệu trong brain là một thiên thể. Trang wiki là **vì sao** (quy trình là sao bốn cánh), kỹ năng và trí nhớ là **chấm trên vành quỹ đạo**, tài liệu thô chưa chưng cất là **đá vụn** quanh hố đen. Màu theo thương hiệu: H2O Studio xanh, ThuyH2O hồng.
- Rê chuột lên thiên thể thấy tên và thuộc phòng nào; bấm vào hiện thẻ **Đọc nhanh** gồm các đầu mục có sẵn trong tài liệu, kèm nút Mở và Hỏi Joyce.
- Admin ở Brain Default thấy bầu trời **gộp mọi phòng ban**; mở brain một phòng thì chỉ trời phòng đó; nhân viên thấy trời brain của mình. Tắt được ở Cài đặt → Giao diện Joyce → thẻ Khác.

## [1.0.3] - 2026-10-08
### Cải thiện
- **Nút Quay lại trên đầu mọi trang**: bấm mũi tên sang trang khác xong, nút ghi rõ "Quay lại Bảng điều hành" (hay trang vừa rời) đưa về đúng chỗ đang xem, kể cả vị trí đã cuộn tới.
- Nút Back của trình duyệt, nút lùi trên chuột và cú vuốt cạnh trên điện thoại cũng lùi về trang trước, không còn văng ra khỏi Joyce.
- **Thanh trượt Cỡ vành quỹ đạo** trong Cài đặt → Giao diện Joyce → Quả tinh cầu (thẻ Khác): kéo để phóng to hoặc thu nhỏ ba vành quỹ đạo dữ liệu quanh tinh cầu, và thanh **Cỡ chấm trên vành** cho các tiểu hành tinh chạy trên vành.
- **Gỡ và thêm Fanpage ngay trong Cẩm nang → Fanpage**: mỗi Trang có nút Gỡ (Joyce và AI thôi đụng tới Trang đó, Trang trên Facebook vẫn nguyên), Trang đã gỡ thêm lại được bằng một nút, và nút "Thêm Trang từ Facebook" mở đăng nhập để tick thêm Trang mới.

## [1.0.2] - 2026-10-07
### Cải thiện
- **Sông dung nham chảy chậm và lan rộng như dòng sông thật**: đầu dòng bò tới từ từ (khoảng 1,5 phút một dòng), phía sau tràn rộng ra, hai bên là dải đất cháy sẫm, mặt dung nham có mảng vỏ nguội trôi chậm.
- **Chảy tới đâu cháy tới đó**: lửa bập bùng ở đầu dòng, khói đen cuồn cuộn bốc lên và trôi theo gió dọc đường dung nham vừa chảy qua, có đốm than âm ỉ phía sau.
- **Thanh Tốc độ dòng dung nham** trong Cài đặt → Giao diện Joyce → Quả tinh cầu (thẻ Lõi tinh cầu), từ 0,2 lần tới 3 lần.

## [1.0.1] - 2026-10-07
### Thêm mới
- **Nhóm Tổng quan** đứng đầu thanh bên, gồm 5 trang: **Bảng điều hành**, Hôm nay, **Phòng ban**, **Lịch & kế hoạch**, **Báo cáo**. Hôm nay giữ nguyên, chỉ chuyển vào nhóm này.
- **Bảng điều hành**: brief buổi sáng, 6 chỉ số việc, hàng đợi ưu tiên, nhịp vận hành theo lĩnh vực, sức khoẻ phòng ban, lịch hôm nay, sức khoẻ hệ thống và hoạt động gần đây. Toàn số thật, chưa nối nguồn thì nói thẳng, không bịa số.
- **Phòng ban**: từng phòng của từng thương hiệu, phòng có việc kẹt lên đầu; bấm vào là mở brain của phòng hoặc hỏi Joyce. **Lịch** gom nhắc hẹn mọi brain trong 7 ngày. **Báo cáo** dẫn tới đúng chỗ giữ số liệu hoặc nhờ Joyce viết.
- Nói "mở tổng quan", "mở báo cáo"... bằng giọng nói cũng tới đúng trang.

## [1.0.0] - 2026-10-07

### Bản phát hành nội bộ đầu tiên của H2O
- Fork độc lập từ Joyce OS (MIT), giữ nguyên LICENSE và ghi công tác giả gốc.
- Tách toàn bộ phụ thuộc hạ tầng ngoài: không kiểm tra bản mới, không kho gói ngoài,
  không telemetry; tài liệu đọc nội bộ qua /static/docs/view.html.
- Bảng điều khiển theo phòng ban H2O (46 brain), trang Cẩm nang với tab con:
  Tổng quan, Phòng ban, Fanpage, Zalo.
- Skill nghiệp vụ đầu tiên: phân loại lead, kế hoạch nội dung, review hiệu quả,
  comment → lead, chăm sóc sau dịch vụ.
