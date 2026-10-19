# Nhật ký phiên bản - H2O Joyce OS

***Tiếng Việt** · [English](CHANGELOG.en.md)*

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
