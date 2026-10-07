"""Sổ PHÒNG BAN H2O Studio: mỗi phòng một brain riêng; mỗi THƯƠNG HIỆU một brain chung riêng.

Mô hình (chủ duyệt 2026-10-06, mở rộng đa thương hiệu 2026-10-08):
- THƯƠNG HIỆU (brand): H2O Studio, ThuyH2O... Mỗi brand một brain CHUNG riêng
  (`shared_brain`: "H2O Studio", "ThuyH2O Studio") giữ kiến thức dùng chung của brand đó.
- KHỐI (Kế Toán, Nhân Sự, Sản Xuất...) thuộc một brand (`khoi.brand`), chỉ là nhóm hiển thị,
  không có brain.
- PHÒNG là đơn vị làm việc: một brain riêng trong BRAINS_DIR + một agent trưởng phòng ở
  `<brain>/agents/<slug>.md`. Dữ liệu nhân viên nạp mỗi ngày vào thẳng brain phòng đó, nên
  Joyce trả lời phòng nào thì chỉ đọc trí nhớ, wiki, agent của phòng đó.
- Brain CHUNG của brand: mọi phòng TRONG BRAND đọc được (nạp sẵn MEMORY.md của nó vào prompt
  khi chat trong brain phòng), chỉ admin ghi. Phòng brand A không thấy brain chung brand B.

Nhân viên mang `phong_ban: [id phòng]` (h2o_staff). Server khoá brain của request nhân viên
vào đúng các brain phòng đó (main._staff_scope_roots), nên nhân viên không đọc được Brain
Default của chủ hay brain phòng khác dù trình duyệt gửi gì lên.

Tên thư mục brain là ASCII không dấu ("San Xuat - Makeup"): đường dẫn brain đi vào cwd của
CLI, lệnh shell và link file, dấu tiếng Việt ở đó chỉ thêm rủi ro chuẩn hoá Unicode (macOS
NFD) mà không được gì. Tên có dấu để hiển thị nằm trong sổ này.

File state: STATE_DIR/h2o_departments.json, cạnh h2o_staff.json."""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import config as cfgmod

PATH = cfgmod.STATE_DIR / "h2o_departments.json"
SHARED_BRAIN = "H2O Studio"
DEFAULT_BRAND_ID = "h2o"   # thương hiệu gốc H2O Studio; brand khác khai qua add_brand()
ORG_CHART_REL = "Joyce/so-do-phong-ban.md"   # trong brain chung của MỖI brand, tự sinh lại mỗi lần đổi sổ

# ---- Sơ đồ khởi tạo của H2O Studio --------------------------------------------------------
# Mỗi khối: ten (hiển thị), prefix (đầu tên thư mục brain), boi_canh (bối cảnh chung cho
# agent trưởng phòng trong khối), dau_ra (khuôn báo cáo mong muốn).
# Mỗi phòng: ten, agent (tên agent đúng như chủ đặt), vai (một câu), nhiem_vu (việc chính).
H2O_SEED = [
    {
        "ten": "Kế Toán", "prefix": "Ke Toan",
        "boi_canh": "Khối Kế Toán giữ dòng tiền của H2O Studio: tiền thu từ khách (cọc, thanh toán gói chụp, makeup, váy cưới), tiền chi cho vận hành và nhà cung cấp, và đối soát hai dòng đó với nhau.",
        "dau_ra": "Báo cáo ngắn: tổng số tiền kèm kỳ (ngày/tuần/tháng), so với kỳ trước, các khoản bất thường liệt kê riêng, cuối cùng 1 đến 3 việc cần làm.",
        "phong": [
            {"ten": "Phòng Thu", "agent": "Agent Trưởng Phòng Thu",
             "vai": "quản lý mọi khoản tiền vào của studio",
             "nhiem_vu": ["Ghi nhận cọc và thanh toán theo từng hợp đồng, từng khách",
                          "Nhắc các khoản còn nợ, cọc sắp tới hạn thanh toán phần còn lại",
                          "Tổng hợp doanh thu theo dịch vụ: chụp hình, makeup, váy cưới, in ấn"]},
            {"ten": "Phòng Chi", "agent": "Agent Trưởng Phòng Chi",
             "vai": "quản lý mọi khoản tiền ra của studio",
             "nhiem_vu": ["Ghi nhận chi phí theo nhóm: lương, nhà cung cấp, mặt bằng, marketing, vật tư",
                          "Kiểm đề nghị chi có đủ chứng từ và người duyệt trước khi chi",
                          "Cảnh báo nhóm chi vượt định mức tháng"]},
            {"ten": "Đối Soát & Báo Cáo", "agent": "Agent Trưởng Phòng Đối Soát",
             "vai": "đối chiếu thu chi và lập báo cáo tài chính định kỳ",
             "nhiem_vu": ["Đối chiếu sổ thu, sổ chi với sao kê ngân hàng và tiền mặt",
                          "Chỉ ra chênh lệch, khoản chưa khớp và người cần giải trình",
                          "Lập báo cáo lãi lỗ tuần, tháng cho ban giám đốc"]},
        ],
    },
    {
        "ten": "Nhân Sự", "prefix": "Nhan Su",
        "boi_canh": "Khối Nhân Sự lo con người của từng bộ phận nghề trong H2O Studio: tuyển dụng, đào tạo, lịch làm, đánh giá, giữ chân nhân viên. Mỗi phòng nhân sự phụ trách đúng một bộ phận nghề.",
        "dau_ra": "Trả lời theo từng nhân viên hoặc từng vị trí, nêu rõ tình trạng hiện tại, việc cần làm và hạn chót.",
        "phong": [
            {"ten": "Nhân Sự Makeup", "agent": "Agent Trưởng Nhân Sự Makeup", "vai": "quản lý nhân sự bộ phận makeup",
             "nhiem_vu": ["Tuyển và đào tạo chuyên viên makeup theo chuẩn tay nghề H2O",
                          "Xếp lịch makeup theo lịch show, lịch chụp", "Theo dõi đánh giá khách về từng chuyên viên"]},
            {"ten": "Nhân Sự Bới Tóc", "agent": "Agent Trưởng Nhân Sự Bới Tóc", "vai": "quản lý nhân sự bộ phận bới tóc",
             "nhiem_vu": ["Tuyển và đào tạo thợ bới tóc", "Xếp lịch theo lịch makeup và lịch chụp",
                          "Theo dõi tay nghề và phản hồi khách"]},
            {"ten": "Nhân Sự Photoshop", "agent": "Agent Trưởng Nhân Sự Photoshop", "vai": "quản lý nhân sự bộ phận hậu kỳ photoshop",
             "nhiem_vu": ["Tuyển và đào tạo thợ hậu kỳ theo chuẩn màu H2O", "Chia khối lượng ảnh và theo dõi tiến độ từng người",
                          "Theo dõi tỉ lệ ảnh bị khách yêu cầu sửa lại"]},
            {"ten": "Nhân Sự Hình Ảnh", "agent": "Agent Trưởng Nhân Sự Hình Ảnh", "vai": "quản lý nhân sự bộ phận nhiếp ảnh",
             "nhiem_vu": ["Tuyển và đào tạo nhiếp ảnh, phụ ảnh", "Xếp lịch chụp studio và ngoại cảnh",
                          "Đánh giá tay nghề qua bộ ảnh giao khách"]},
            {"ten": "Nhân Sự Váy", "agent": "Agent Trưởng Nhân Sự Váy", "vai": "quản lý nhân sự bộ phận váy cưới",
             "nhiem_vu": ["Tuyển và đào tạo nhân viên tư vấn, thử váy, bảo quản váy", "Xếp ca trực showroom váy",
                          "Theo dõi chất lượng tư vấn qua phản hồi khách"]},
            {"ten": "Nhân Sự Marketing", "agent": "Agent Trưởng Nhân Sự Marketing", "vai": "quản lý nhân sự bộ phận marketing",
             "nhiem_vu": ["Tuyển content, designer, chạy quảng cáo", "Giao chỉ tiêu và theo dõi kết quả từng người",
                          "Lên lộ trình đào tạo kỹ năng mới"]},
            {"ten": "Nhân Sự Sales", "agent": "Agent Trưởng Nhân Sự Sales", "vai": "quản lý nhân sự bộ phận bán hàng",
             "nhiem_vu": ["Tuyển và đào tạo sales theo kịch bản tư vấn H2O", "Giao chỉ tiêu doanh số, tính hoa hồng",
                          "Kèm cặp sales có tỉ lệ chốt thấp"]},
            {"ten": "Nhân Sự CSKH", "agent": "Agent Trưởng Nhân Sự CSKH", "vai": "quản lý nhân sự bộ phận chăm sóc khách hàng",
             "nhiem_vu": ["Tuyển và đào tạo nhân viên CSKH", "Xếp ca trực tin nhắn, điện thoại",
                          "Theo dõi thời gian phản hồi và mức hài lòng của khách"]},
            {"ten": "Nhân Sự Vận Hành", "agent": "Agent Trưởng Nhân Sự Vận Hành", "vai": "quản lý nhân sự bộ phận vận hành, hậu cần, vệ sinh",
             "nhiem_vu": ["Tuyển và phân ca nhân viên vận hành, lễ tân, vệ sinh", "Theo dõi chấm công, nghỉ phép",
                          "Đảm bảo đủ người cho ngày cao điểm"]},
        ],
    },
    {
        "ten": "Marketing", "prefix": "Marketing",
        "boi_canh": "Khối Marketing mang khách về cho H2O Studio qua nội dung, quảng cáo và hình ảnh thương hiệu, chia theo ba dòng dịch vụ: hình ảnh cưới, makeup, váy cưới.",
        "dau_ra": "Kế hoạch hoặc báo cáo theo kênh (Facebook, TikTok, Instagram, Zalo...): số liệu thật, so kỳ trước, nội dung nào hiệu quả, việc tiếp theo.",
        "phong": [
            {"ten": "Marketing Hình Ảnh", "agent": "Agent Trưởng Marketing Hình Ảnh", "vai": "phụ trách marketing dòng dịch vụ chụp ảnh cưới",
             "nhiem_vu": ["Lên lịch nội dung từ bộ ảnh mới chụp", "Theo dõi quảng cáo gói chụp, chi phí mỗi khách tiềm năng",
                          "Đề xuất concept truyền thông theo mùa cưới"]},
            {"ten": "Marketing Makeup", "agent": "Agent Trưởng Marketing Makeup", "vai": "phụ trách marketing dòng dịch vụ makeup",
             "nhiem_vu": ["Làm nội dung trước sau, video makeup", "Theo dõi quảng cáo dịch vụ makeup cô dâu, makeup sự kiện",
                          "Xây hình ảnh chuyên viên makeup nổi bật"]},
            {"ten": "Marketing Váy Cưới", "agent": "Agent Trưởng Marketing Váy Cưới", "vai": "phụ trách marketing dòng váy cưới",
             "nhiem_vu": ["Giới thiệu bộ sưu tập váy mới", "Theo dõi quảng cáo thuê, may váy cưới",
                          "Phối hợp phòng Concept Váy Cưới ra nội dung theo xu hướng"]},
        ],
    },
    {
        "ten": "Bán Hàng", "prefix": "Ban Hang",
        "boi_canh": "Khối Bán Hàng tư vấn và chốt hợp đồng với khách của H2O Studio, chia theo ba dòng dịch vụ. Khách thường hỏi giá, so gói, hẹn lịch xem mẫu.",
        "dau_ra": "Theo từng khách hoặc từng ngày: số khách mới, số đã chốt, giá trị hợp đồng, khách cần chăm tiếp và câu trả lời mẫu nếu cần.",
        "phong": [
            {"ten": "Sales Hình Ảnh", "agent": "Agent Trưởng Sales Hình Ảnh", "vai": "phụ trách bán gói chụp ảnh cưới",
             "nhiem_vu": ["Tư vấn và chốt gói chụp studio, ngoại cảnh", "Theo dõi khách đang cân nhắc và nhắc chăm lại",
                          "Tổng hợp lý do khách từ chối để cải thiện gói"]},
            {"ten": "Sales Makeup", "agent": "Agent Trưởng Sales Makeup", "vai": "phụ trách bán dịch vụ makeup",
             "nhiem_vu": ["Tư vấn và chốt lịch makeup cô dâu, makeup sự kiện", "Giữ lịch chuyên viên không bị trùng",
                          "Bán kèm dịch vụ bới tóc, váy"]},
            {"ten": "Sales Váy Cưới", "agent": "Agent Trưởng Sales Váy Cưới", "vai": "phụ trách bán, cho thuê váy cưới",
             "nhiem_vu": ["Tư vấn thuê, may váy theo dáng và ngân sách khách", "Hẹn lịch thử váy và theo dõi đặt cọc",
                          "Theo dõi tình trạng váy đang cho thuê"]},
        ],
    },
    {
        "ten": "Sản Xuất", "prefix": "San Xuat",
        "boi_canh": "Khối Sản Xuất làm ra sản phẩm giao khách của H2O Studio: chụp, makeup, bới tóc, hậu kỳ, concept, in ấn album. Mỗi phòng nhận việc theo lịch hợp đồng đã chốt.",
        "dau_ra": "Danh sách việc theo lịch: khách, hạng mục, người làm, hạn giao, tình trạng (chưa làm, đang làm, xong, trễ). Việc trễ đưa lên đầu.",
        "phong": [
            {"ten": "Phòng Hình Ảnh", "agent": "Agent Trưởng Phòng Hình Ảnh", "vai": "điều phối các buổi chụp",
             "nhiem_vu": ["Lên lịch chụp, phân nhiếp ảnh và phụ ảnh", "Chuẩn bị thiết bị, địa điểm theo concept",
                          "Bàn giao ảnh gốc cho Phòng Photoshop đúng hạn"]},
            {"ten": "Phòng Makeup", "agent": "Agent Trưởng Phòng Makeup", "vai": "điều phối công việc makeup",
             "nhiem_vu": ["Phân chuyên viên makeup theo lịch chụp và lịch cưới", "Quản lý mỹ phẩm, dụng cụ và hạn dùng",
                          "Giữ chuẩn layout makeup theo từng concept"]},
            {"ten": "Phòng Photoshop", "agent": "Agent Trưởng Phòng Photoshop", "vai": "điều phối hậu kỳ ảnh",
             "nhiem_vu": ["Chia album cho thợ hậu kỳ, theo dõi hạn giao", "Kiểm chuẩn màu và chuẩn chỉnh sửa trước khi giao khách",
                          "Xử lý yêu cầu sửa lại của khách"]},
            {"ten": "Phòng Bới Tóc", "agent": "Agent Trưởng Phòng Bới Tóc", "vai": "điều phối công việc bới tóc",
             "nhiem_vu": ["Phân thợ theo lịch makeup", "Quản lý phụ kiện tóc, tóc giả",
                          "Giữ mẫu kiểu tóc theo từng concept"]},
            {"ten": "Phòng Concept", "agent": "Agent Trưởng Phòng Concept", "vai": "dựng concept cho từng buổi chụp",
             "nhiem_vu": ["Chuyển ý tưởng khách thành bảng concept: bối cảnh, trang phục, ánh sáng",
                          "Chuẩn bị đạo cụ, phông, phụ kiện", "Phối hợp Phòng Nghiên Cứu để áp concept mới"]},
            {"ten": "Phòng In Ấn", "agent": "Agent Trưởng Phòng In Ấn", "vai": "điều phối in album, ảnh phóng",
             "nhiem_vu": ["Nhận file đã duyệt, đặt in đúng kích thước và chất liệu", "Kiểm chất lượng bản in trước khi giao",
                          "Theo dõi đơn in với nhà in và hạn giao khách"]},
        ],
    },
    {
        "ten": "Nghiên Cứu", "prefix": "Nghien Cuu",
        "boi_canh": "Khối Nghiên Cứu tìm xu hướng và phát triển concept mới cho H2O Studio, để các phòng Sản Xuất và Marketing luôn có ý tưởng mới đưa cho khách.",
        "dau_ra": "Mỗi đề xuất concept gồm: tên, cảm hứng, đối tượng khách, bảng màu, đạo cụ hoặc vật tư cần có, chi phí ước tính, ảnh tham khảo (đường dẫn).",
        "phong": [
            {"ten": "Concept Hình Ảnh", "agent": "Agent Trưởng Phòng Concept Hình Ảnh", "vai": "nghiên cứu concept chụp ảnh",
             "nhiem_vu": ["Theo dõi xu hướng chụp ảnh cưới trong và ngoài nước", "Đề xuất concept mới mỗi mùa",
                          "Lưu thư viện concept đã làm và hiệu quả của từng concept"]},
            {"ten": "Concept Makeup", "agent": "Agent Trưởng Phòng Concept Makeup", "vai": "nghiên cứu phong cách makeup",
             "nhiem_vu": ["Theo dõi xu hướng makeup cô dâu", "Đề xuất layout makeup mới kèm sản phẩm cần dùng",
                          "Soạn hướng dẫn để Phòng Makeup áp dụng"]},
            {"ten": "Concept Váy Cưới", "agent": "Agent Trưởng Phòng Concept Váy Cưới", "vai": "nghiên cứu mẫu váy cưới",
             "nhiem_vu": ["Theo dõi bộ sưu tập váy của các nhà mốt", "Đề xuất mẫu váy nên nhập hoặc may",
                          "Đánh giá mẫu váy nào được khách chọn nhiều"]},
            {"ten": "Concept Phụ Kiện", "agent": "Agent Trưởng Phòng Concept Phụ Kiện", "vai": "nghiên cứu phụ kiện cưới",
             "nhiem_vu": ["Theo dõi xu hướng phụ kiện: hoa, khăn voan, trang sức, giày", "Đề xuất phụ kiện đi kèm từng concept",
                          "Tìm nhà cung cấp và so giá"]},
        ],
    },
    {
        "ten": "CSKH", "prefix": "CSKH",
        "boi_canh": "Khối Chăm Sóc Khách Hàng đi cùng khách của H2O Studio suốt hành trình: trước khi dùng dịch vụ, trong ngày chụp hoặc ngày cưới, và sau khi giao sản phẩm.",
        "dau_ra": "Theo từng khách: giai đoạn hiện tại, việc đã làm, việc cần làm tiếp, mẫu tin nhắn đề xuất gửi khách (giọng anh chị / em).",
        "phong": [
            {"ten": "Trước Dịch Vụ", "agent": "Agent Trưởng Phòng Trước Dịch Vụ", "vai": "chăm sóc khách từ lúc ký hợp đồng tới ngày dùng dịch vụ",
             "nhiem_vu": ["Nhắc lịch chụp, lịch thử váy, lịch makeup", "Gửi hướng dẫn chuẩn bị cho khách",
                          "Xác nhận lại yêu cầu riêng của khách với các phòng sản xuất"]},
            {"ten": "Trong Dịch Vụ", "agent": "Agent Trưởng Phòng Trong Dịch Vụ", "vai": "chăm sóc khách trong ngày dùng dịch vụ",
             "nhiem_vu": ["Đón tiếp, theo dõi tiến độ buổi chụp, buổi makeup", "Xử lý ngay phát sinh trong ngày",
                          "Ghi nhận cảm nhận của khách cuối buổi"]},
            {"ten": "Sau Dịch Vụ & Khiếu Nại", "agent": "Agent Trưởng Phòng Sau Dịch Vụ", "vai": "chăm sóc sau giao sản phẩm và xử lý khiếu nại",
             "nhiem_vu": ["Hỏi thăm sau giao ảnh, album; xin đánh giá", "Tiếp nhận khiếu nại, chuyển đúng phòng, theo tới khi xong",
                          "Tổng hợp khiếu nại theo nguyên nhân hằng tháng"]},
        ],
    },
    {
        "ten": "Vệ Sinh", "prefix": "Ve Sinh",
        "boi_canh": "Khối Vệ Sinh giữ cho studio, phòng makeup, showroom váy và thiết bị luôn sạch, sẵn sàng đón khách.",
        "dau_ra": "Checklist theo khu vực hoặc theo ca: hạng mục, người làm, đạt hay chưa đạt, ghi chú. Hạng mục chưa đạt đưa lên đầu.",
        "phong": [
            {"ten": "Không Gian Studio", "agent": "Agent Trưởng Phòng Không Gian Studio", "vai": "giữ vệ sinh các khu vực studio",
             "nhiem_vu": ["Lên lịch vệ sinh phòng chụp, sảnh, phòng chờ, nhà vệ sinh", "Kiểm tra trước giờ đón khách",
                          "Ghi nhận khu vực hư hỏng cần sửa"]},
            {"ten": "Dụng Cụ & Thiết Bị", "agent": "Agent Trưởng Phòng Dụng Cụ & Thiết Bị", "vai": "giữ vệ sinh dụng cụ và thiết bị",
             "nhiem_vu": ["Vệ sinh cọ, dụng cụ makeup, dụng cụ tóc theo chuẩn", "Lau chùi thiết bị chụp, đèn, phông",
                          "Báo thiết bị cần bảo dưỡng"]},
            {"ten": "Kiểm Tra Cuối Ca", "agent": "Agent Trưởng Phòng Kiểm Tra Cuối Ca", "vai": "kiểm tra tổng cuối mỗi ca",
             "nhiem_vu": ["Chạy checklist cuối ca: điện, nước, cửa, thiết bị", "Ghi nhận việc tồn để ca sau xử lý",
                          "Báo cáo ngắn cuối ngày cho quản lý"]},
        ],
    },
    {
        "ten": "Xử Lý Truyền Thông", "prefix": "Truyen Thong",
        "boi_canh": "Khối Xử Lý Truyền Thông bảo vệ uy tín H2O Studio trên mạng: theo dõi khách và cộng đồng nói gì, phản hồi đúng lúc, xử lý khi có khủng hoảng.",
        "dau_ra": "Theo từng tín hiệu: nguồn (đường dẫn), nội dung tóm tắt, mức độ (thấp, vừa, cao), đề xuất xử lý và câu phản hồi mẫu.",
        "phong": [
            {"ten": "Theo Dõi Tín Hiệu", "agent": "Agent Trưởng Phòng Theo Dõi Tín Hiệu", "vai": "theo dõi mọi nhắc đến H2O Studio trên mạng",
             "nhiem_vu": ["Quét bình luận, đánh giá, bài đăng nhắc đến studio", "Phân loại tín hiệu tốt, trung tính, xấu",
                          "Chuyển tín hiệu xấu sang Phòng Phản Hồi & Xử Lý"]},
            {"ten": "Phản Hồi & Xử Lý", "agent": "Agent Trưởng Phòng Phản Hồi & Xử Lý", "vai": "phản hồi bình luận, đánh giá của khách",
             "nhiem_vu": ["Soạn phản hồi đúng giọng thương hiệu", "Phối hợp CSKH xử lý tận gốc vấn đề của khách",
                          "Theo dõi tới khi khách hài lòng hoặc chuyển lên khủng hoảng"]},
            {"ten": "Khủng Hoảng & Sự Cố", "agent": "Agent Trưởng Phòng Khủng Hoảng & Sự Cố", "vai": "xử lý khủng hoảng truyền thông",
             "nhiem_vu": ["Đánh giá mức độ sự cố và báo ngay ban giám đốc", "Soạn thông cáo, kịch bản phản hồi thống nhất",
                          "Rút bài học sau mỗi sự cố thành quy trình"]},
        ],
    },
    {
        "ten": "Văn Thư & Quy Trình", "prefix": "Van Thu",
        "boi_canh": "Văn Thư & Quy Trình giữ hồ sơ, biểu mẫu, hợp đồng và quy trình chuẩn của toàn H2O Studio, để mọi phòng làm theo cùng một cách.",
        "dau_ra": "Văn bản có tiêu đề, số hiệu, ngày ban hành, phạm vi áp dụng, các bước đánh số. Hồ sơ liệt kê theo bảng: tên, loại, ngày, nơi lưu.",
        "phong": [
            {"ten": "Văn Thư & Quy Trình", "agent": "Agent Tổng Quản Văn Thư", "vai": "tổng quản văn thư và quy trình chuẩn",
             "nhiem_vu": ["Soạn, cập nhật quy trình chuẩn (SOP) cho các phòng", "Quản lý biểu mẫu, hợp đồng mẫu và hồ sơ lưu trữ",
                          "Đối chiếu quy trình đang làm thực tế với quy trình đã ban hành"]},
        ],
    },
]


def _ascii(s: str) -> str:
    s = str(s or "").replace("Đ", "D").replace("đ", "d")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def slug(s: str) -> str:
    s = _ascii(s).replace("&", " va ")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "phong"


def _clean(s: str) -> str:
    s = _ascii(s).replace("&", "va")
    s = re.sub(r'[\\/:*?"<>|]+', "", s)
    return re.sub(r"\s+", " ", s).strip()


def brain_folder(khoi: dict, ten_phong: str) -> str:
    """Tên thư mục brain của một phòng, luôn dạng '<Khối> - <Phòng>':
    'San Xuat' + 'Phòng Makeup' -> 'San Xuat - Makeup'; 'Nhan Su' + 'Nhân Sự Makeup' ->
    'Nhan Su - Makeup' (bỏ chữ 'Phòng' và tên khối lặp ở đầu). Khối chỉ có một phòng trùng
    tên khối (Văn Thư & Quy Trình) thì dùng luôn tên đó."""
    p = _clean(khoi.get("prefix") or khoi.get("ten"))
    ten = _clean(re.sub(r"^\s*ph[oò]ng\s+", "", str(ten_phong or ""), flags=re.I))
    if ten.lower() == _clean(khoi.get("ten")).lower():
        return ten[:60]
    if ten.lower().startswith(p.lower() + " "):
        ten = ten[len(p):].strip()
    if not ten or ten.lower() == p.lower():
        return p[:60]
    return f"{p} - {ten}"[:60].strip()


# ---- Kho -----------------------------------------------------------------------------------
def _doc() -> dict:
    try:
        d = json.loads(PATH.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            d.setdefault("khoi", [])
            d.setdefault("phong", [])
            d.setdefault("brands", [])
            if not any(b.get("id") == DEFAULT_BRAND_ID for b in d["brands"]):
                d["brands"].insert(0, {"id": DEFAULT_BRAND_ID, "ten": "H2O Studio",
                                       "shared_brain": SHARED_BRAIN, "created": time.time()})
            for k in d["khoi"]:
                k.setdefault("brand", DEFAULT_BRAND_ID)
            return d
    except Exception:
        pass
    return {"khoi": [], "phong": [], "brands": [{"id": DEFAULT_BRAND_ID, "ten": "H2O Studio",
                                                "shared_brain": SHARED_BRAIN,
                                                "created": time.time()}]}


def _save(d: dict) -> None:
    PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def list_all() -> dict:
    d = _doc()
    return {"shared_brain": SHARED_BRAIN, "brands": d["brands"], "khoi": d["khoi"],
            "phong": d["phong"]}


# ---- Thương hiệu (brand): mỗi brand một brain chung + sổ khối/phòng riêng ------------------
def brands() -> list:
    return _doc()["brands"]


def get_brand(bid: str):
    for b in _doc()["brands"]:
        if b.get("id") == bid:
            return b
    return None


def add_brand(ten: str, shared_brain: str = ""):
    """(ok, err|record). Mỗi thương hiệu một brain chung riêng: kiến thức chung (thương hiệu,
    bảng giá, sơ đồ phòng ban) của brand đó nằm ở brain chung của nó, không lẫn brand khác."""
    ten = str(ten or "").strip()
    if not ten:
        return False, "Thiếu tên thương hiệu"
    d = _doc()
    bid = slug(ten)
    if any(b.get("id") == bid for b in d["brands"]):
        return False, "Thương hiệu này đã có"
    sb = str(shared_brain or "").strip() or _clean(ten + " Studio")
    rec = {"id": bid, "ten": ten, "shared_brain": sb, "created": time.time()}
    d["brands"].append(rec)
    _save(d)
    return True, rec


def brand_of_khoi(khoi: dict):
    """Khối thuộc thương hiệu nào; khối cũ chưa khai brand mặc định về H2O Studio."""
    return get_brand((khoi or {}).get("brand") or DEFAULT_BRAND_ID) or get_brand(DEFAULT_BRAND_ID)


def brand_of_phong(phong: dict):
    return brand_of_khoi(khoi_of(phong))


def shared_brain_of_brand(brand: dict) -> str:
    return str((brand or {}).get("shared_brain") or SHARED_BRAIN)


def shared_brain_for_brain_folder(folder: str) -> str:
    """Thư mục brain bất kỳ -> brain chung của thương hiệu chứa phòng đó. Brain không thuộc
    sổ phòng (Brain Default...) và brand khác thì vẫn về brain chung H2O Studio mặc định."""
    p = phong_by_brain(folder)
    if p:
        return shared_brain_of_brand(brand_of_phong(p))
    f = str(folder or "").strip().lower()
    for b in _doc()["brands"]:
        if str(b.get("shared_brain") or "").lower() == f:
            return b["shared_brain"]
    return SHARED_BRAIN


def shared_brains() -> list:
    """Tên tất cả brain chung của các brand (để UI/scope đánh dấu 'chung, chỉ đọc')."""
    return [str(b.get("shared_brain") or "") for b in _doc()["brands"] if b.get("shared_brain")]


def get_phong(pid: str):
    for p in _doc()["phong"]:
        if p.get("id") == pid:
            return p
    return None


def phong_by_brain(folder: str):
    """Tên thư mục brain -> phòng (so không phân biệt hoa thường, như Windows)."""
    f = str(folder or "").strip().lower()
    if not f:
        return None
    for p in _doc()["phong"]:
        if str(p.get("brain") or "").lower() == f:
            return p
    return None


def khoi_of(phong: dict):
    kid = (phong or {}).get("khoi_id")
    for k in _doc()["khoi"]:
        if k.get("id") == kid:
            return k
    return None


def brains_of_staff(staff: dict) -> list:
    """Danh sách thư mục brain mà nhân viên được làm việc, đúng thứ tự admin gán.
    Mục đầu tiên là brain mặc định của người đó. Phòng đã bị gỡ khỏi sổ thì bỏ qua."""
    ids = [str(x) for x in ((staff or {}).get("phong_ban") or [])]
    by_id = {p.get("id"): p for p in _doc()["phong"]}
    out = []
    for i in ids:
        p = by_id.get(i)
        if p and p.get("brain") and p["brain"] not in out:
            out.append(p["brain"])
    return out


def valid_ids(ids) -> list:
    known = {p.get("id") for p in _doc()["phong"]}
    out = []
    for i in ids or []:
        i = str(i).strip()
        if i and i in known and i not in out:
            out.append(i)
    return out


# ---- Agent trưởng phòng ------------------------------------------------------------------
def agent_md(phong: dict, khoi: dict) -> str:
    """Nội dung file agent trưởng phòng, theo khung metaprompt của joyce-builder."""
    nv = "\n".join(f"- {x}" for x in (phong.get("nhiem_vu") or []))
    br = brand_of_khoi(khoi)
    brand_ten = (br or {}).get("ten") or "H2O Studio"
    shared = shared_brain_of_brand(br)
    return (
        "---\n"
        "type: agent\n"
        f"name: {phong.get('agent')}\n"
        f"slug: {phong.get('agent_slug')}\n"
        f"role: Trưởng {phong.get('ten')} thuộc khối {khoi.get('ten')}, {phong.get('vai')}\n"
        f"group: {khoi.get('ten')}\n"
        "skills: []\n"
        "model: \"\"\n"
        f"updated: {time.strftime('%Y-%m-%d')}\n"
        "---\n"
        f"Bạn là {phong.get('agent')} của {brand_ten}, {phong.get('vai')}. "
        "Làm tốt nghĩa là nhân viên trong phòng hỏi gì cũng nhận được câu trả lời đúng quy trình "
        "của phòng, có số liệu thật, và biết ngay bước tiếp theo.\n\n"
        "## Bối cảnh\n"
        f"{khoi.get('boi_canh')}\n"
        "Brain này là không gian RIÊNG của phòng: tài liệu, ghi chú, trí nhớ nhân viên nạp mỗi "
        "ngày đều nằm ở đây. Kiến thức chung của cả thương hiệu (thương hiệu, bảng giá, quy trình "
        f"chung, sơ đồ phòng ban) nằm ở brain chung {shared}, đã nạp sẵn vào ngữ cảnh.\n\n"
        "## Nhiệm vụ chính\n"
        f"{nv}\n\n"
        "## Quy trình\n"
        f"1. Đọc trí nhớ và wiki của phòng trước, rồi tới kiến thức chung {shared} nếu cần.\n"
        "2. Cần số liệu thì lấy từ nguồn thật (file trong brain, MCP đã kết nối); không có thì nói rõ là thiếu.\n"
        "3. Trả lời hoặc làm việc được giao, đúng phạm vi phòng.\n"
        "4. Có thông tin mới đáng nhớ (quy định, khách quen, quyết định của trưởng phòng) thì ghi vào trí nhớ của phòng.\n"
        "5. Việc thuộc phòng khác thì nói rõ phòng nào phụ trách, kèm nội dung cần chuyển.\n\n"
        "## Định dạng đầu ra\n"
        f"{khoi.get('dau_ra')}\n"
        "Câu đầu tiên là kết luận. Đoạn ngắn, gạch đầu dòng cho danh sách.\n\n"
        "## Trường hợp khó\n"
        "- Thiếu dữ liệu: nêu giả định hợp lý rồi làm tiếp, ghi rõ chỗ nào là giả định.\n"
        "- Yêu cầu mơ hồ mà đoán sai sẽ gây hại (tiền, lịch khách, gửi tin ra ngoài): hỏi lại một câu.\n"
        "- Ngoài phạm vi phòng: chỉ đúng phòng phụ trách thay vì tự làm.\n\n"
        "## Điều cấm\n"
        "- Không bịa số liệu, tên khách, lịch hẹn: sai một con số là sai quyết định của phòng.\n"
        "- Không ghi sang brain phòng khác hay brain chung: mỗi phòng giữ đúng luồng kiến thức của mình.\n"
        "- Không dùng dấu gạch dài (em dash): giọng đọc vấp khi gặp nó.\n"
    )


def org_chart_md(brand_id: str = "") -> str:
    """Sơ đồ phòng ban (tự sinh) của MỘT thương hiệu để mọi phòng biết việc nào chuyển cho ai.
    brand_id rỗng -> sơ đồ đầy đủ mọi brand (cho admin)."""
    d = _doc()
    br = get_brand(brand_id) if brand_id else None
    lines = ["---", "type: note", "auto_generated: true", "---",
             f"# Sơ đồ phòng ban {(br or {}).get('ten') or 'H2O'}", "",
             "_File này Joyce tự sinh lại mỗi khi admin đổi sơ đồ phòng ban. Sửa tay sẽ bị ghi đè._", ""]
    for k in d["khoi"]:
        if brand_id and k.get("brand") != brand_id:
            continue
        lines.append(f"## {k.get('ten')}")
        for p in d["phong"]:
            if p.get("khoi_id") != k.get("id"):
                continue
            lines.append(f"- **{p.get('ten')}**: {p.get('vai') or ''}. Trưởng phòng: {p.get('agent')}. Brain: `{p.get('brain')}`")
        lines.append("")
    return "\n".join(lines)


# ---- Tạo / sửa sổ --------------------------------------------------------------------------
def _upsert_khoi(d: dict, k: dict) -> dict:
    kid = slug(k["ten"])
    for x in d["khoi"]:
        if x.get("id") == kid:
            for f in ("ten", "prefix", "boi_canh", "dau_ra"):
                if k.get(f) and not x.get(f):
                    x[f] = k[f]
            if k.get("brand"):
                x["brand"] = k["brand"]
            return x
    rec = {"id": kid, "ten": k["ten"], "prefix": k.get("prefix") or _ascii(k["ten"]),
           "boi_canh": k.get("boi_canh") or "", "dau_ra": k.get("dau_ra") or "",
           "brand": k.get("brand") or DEFAULT_BRAND_ID}
    d["khoi"].append(rec)
    return rec


def _upsert_phong(d: dict, khoi: dict, p: dict) -> dict:
    pid = khoi["id"] + "--" + slug(re.sub(r"^\s*ph[oò]ng\s+", "", p["ten"], flags=re.I))
    for x in d["phong"]:
        if x.get("id") == pid:
            return x
    agent = p.get("agent") or f"Agent Trưởng {p['ten']}"
    rec = {
        "id": pid, "khoi_id": khoi["id"], "ten": p["ten"],
        "brain": brain_folder(khoi, p["ten"]),
        "agent": agent, "agent_slug": slug(re.sub(r"^\s*agent\s+", "", agent, flags=re.I)),
        "vai": p.get("vai") or f"quản lý {p['ten']}",
        "nhiem_vu": list(p.get("nhiem_vu") or []),
        "created": time.time(),
    }
    d["phong"].append(rec)
    return rec


def seed_h2o() -> list:
    """Ghi sơ đồ H2O_SEED vào sổ (idempotent: phòng đã có giữ nguyên). Trả danh sách phòng
    để caller dựng brain + agent (việc đó cần scaffold của main.py)."""
    d = _doc()
    for k in H2O_SEED:
        kr = _upsert_khoi(d, k)
        for p in k["phong"]:
            _upsert_phong(d, kr, p)
    _save(d)
    return d["phong"]


def add_phong(khoi_ten: str, ten: str, agent: str = "", vai: str = "", nhiem_vu=None,
              brand: str = ""):
    """(ok, err|record). Khối chưa có thì tạo mới; brand = id thương hiệu sở hữu khối đó
    (rỗng -> H2O Studio)."""
    khoi_ten, ten = str(khoi_ten or "").strip(), str(ten or "").strip()
    if not khoi_ten or not ten:
        return False, "Thiếu tên khối hoặc tên phòng"
    d = _doc()
    bid = str(brand or "").strip()
    if bid and not get_brand(bid):
        return False, "Thương hiệu chưa có - tạo thương hiệu trước"
    kr = _upsert_khoi(d, {"ten": khoi_ten, "brand": bid or DEFAULT_BRAND_ID})
    before = len(d["phong"])
    rec = _upsert_phong(d, kr, {"ten": ten, "agent": agent.strip(), "vai": vai.strip(),
                                "nhiem_vu": [x for x in (nhiem_vu or []) if str(x).strip()]})
    if len(d["phong"]) == before:
        return False, "Phòng này đã có trong khối"
    others = [x for x in d["phong"] if x is not rec and x.get("brain", "").lower() == rec["brain"].lower()]
    if others:
        d["phong"].remove(rec)
        return False, "Tên brain trùng với một phòng khác"
    _save(d)
    return True, rec


def remove_phong(pid: str):
    """Gỡ phòng khỏi sổ. KHÔNG xoá brain trên đĩa (tri thức của phòng còn nguyên, admin tự
    xoá ở dropdown brain nếu muốn) và gỡ id khỏi hồ sơ nhân viên ở caller."""
    d = _doc()
    n0 = len(d["phong"])
    d["phong"] = [p for p in d["phong"] if p.get("id") != pid]
    if len(d["phong"]) == n0:
        return False, "Không tìm thấy phòng"
    used = {p.get("khoi_id") for p in d["phong"]}
    d["khoi"] = [k for k in d["khoi"] if k.get("id") in used]
    _save(d)
    return True, None


# ---- Khoá mục hệ thống với tài khoản nhân viên ---------------------------------------------
# Trong brain phòng, nhân viên (kể cả trưởng phòng) không đổi tên/xoá/ghi đè các mục Joyce cần
# để vận hành: lỡ tay xoá `memory` là phòng mất trí nhớ, xoá `agents` là mất trưởng phòng.
# Khoá chỉ áp lên thao tác TAY ở trang Tệp tin; Joyce vẫn tự ghi memory/wiki như thường, và
# trưởng phòng vẫn sửa trợ lý/kỹ năng/quy trình qua trang riêng của chúng. Admin không bị khoá
# và tự bật/tắt hoặc chọn mục nào bị khoá ở trang Nhân viên.
KHOA_MAC_DINH = [".claude", ".joyce", "Joyce", "agents", "skills", "workflows", "memory", "wiki",
                 "AGENTS.md", "CLAUDE.md"]


def lock_config() -> dict:
    k = _doc().get("khoa") or {}
    muc = k.get("muc")
    return {"bat": bool(k.get("bat", True)),
            "muc": list(muc) if isinstance(muc, list) else list(KHOA_MAC_DINH),
            "mac_dinh": list(KHOA_MAC_DINH)}


def set_lock(bat=None, muc=None) -> dict:
    d = _doc()
    k = dict(d.get("khoa") or {})
    if bat is not None:
        k["bat"] = bool(bat)
    if muc is not None:
        sach = []
        for m in muc:
            m = str(m or "").strip().strip("/\\")
            # Chỉ tên mục ở GỐC brain (một cấp), không đường dẫn: khoá theo mục đầu tiên của path.
            if m and "/" not in m and "\\" not in m and m not in (".", "..") and m not in sach:
                sach.append(m[:80])
        k["muc"] = sach
    d["khoa"] = k
    _save(d)
    return lock_config()


def lock_items() -> set:
    """Tên mục (chữ thường) đang khoá với nhân viên; rỗng khi admin tắt khoá."""
    cfg = lock_config()
    return {m.lower() for m in cfg["muc"]} if cfg["bat"] else set()


# ---- Đề xuất đẩy kiến thức lên brain CHUNG ------------------------------------------------
# Brain chung chỉ admin ghi. Trưởng phòng thấy một tài liệu của phòng đáng dùng chung (bảng
# giá mới, quy trình đã chốt) thì ĐỀ XUẤT; admin duyệt mới chép sang H2O Studio. Lúc đề xuất,
# file được CHỤP lại vào STATE_DIR/h2o_shared_proposals/<id>/ để admin duyệt đúng bản đã đề
# xuất, kể cả khi phòng sửa hay xoá file gốc sau đó.
PROPOSALS_PATH = cfgmod.STATE_DIR / "h2o_shared_proposals.json"
PROPOSALS_DIR = cfgmod.STATE_DIR / "h2o_shared_proposals"
PROPOSAL_MAX_BYTES = 10 * 1024 * 1024
SHARED_INBOX_REL = "sources/tu-phong-ban"     # nơi bản duyệt rơi vào trong brain chung
_TEXT_EXT = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html", ".htm"}


def _pdoc() -> dict:
    try:
        d = json.loads(PROPOSALS_PATH.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            d.setdefault("items", [])
            return d
    except Exception:
        pass
    return {"items": []}


def _psave(d: dict) -> None:
    PROPOSALS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def propose(src: Path, brain_folder: str, rel: str, by: str, note: str = "", by_id: str = ""):
    """(ok, err|record). `src` là file THẬT đã được caller kiểm nằm trong brain phòng."""
    try:
        size = src.stat().st_size
    except OSError:
        return False, "Không đọc được file"
    if not src.is_file():
        return False, "Chỉ đề xuất được file, không phải thư mục"
    if size > PROPOSAL_MAX_BYTES:
        return False, "File quá lớn (tối đa 10MB)"
    ph = phong_by_brain(brain_folder)
    pid = time.strftime("%Y%m%d%H%M%S") + "-" + slug(src.stem)[:30]
    dst = PROPOSALS_DIR / pid / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    rec = {"id": pid, "brain": brain_folder, "phong": (ph or {}).get("ten") or brain_folder,
           "rel": rel, "name": src.name, "size": size, "by": by, "by_id": str(by_id or ""),
           "note": str(note or "").strip()[:500], "ts": time.time(), "status": "pending"}
    d = _pdoc()
    d["items"].append(rec)
    d["items"] = d["items"][-300:]
    _psave(d)
    return True, rec


def list_proposals(limit: int = 100) -> list:
    """Chờ duyệt trước, rồi mới tới đã xử lý gần nhất."""
    items = _pdoc()["items"]
    cho = [x for x in items if x.get("status") == "pending"]
    xong = [x for x in items if x.get("status") != "pending"]
    return (sorted(cho, key=lambda x: x.get("ts", 0), reverse=True)
            + sorted(xong, key=lambda x: x.get("ts_done", 0), reverse=True))[:limit]


def proposal_file(pid: str):
    d = _pdoc()
    rec = next((x for x in d["items"] if x.get("id") == pid), None)
    if not rec:
        return None, None
    f = PROPOSALS_DIR / pid / rec.get("name", "")
    try:
        f.resolve().relative_to(PROPOSALS_DIR.resolve())
    except ValueError:
        return rec, None
    return rec, (f if f.is_file() else None)


def preview(pid: str, cap: int = 20000) -> str:
    rec, f = proposal_file(pid)
    if not f or f.suffix.lower() not in _TEXT_EXT:
        return ""
    try:
        return f.read_text(encoding="utf-8", errors="replace")[:cap]
    except OSError:
        return ""


def decide(pid: str, approve: bool, shared_root: Path, reason: str = ""):
    """Duyệt -> chép bản chụp vào <brain chung>/sources/tu-phong-ban/<brain phòng>/ (không
    ghi đè: trùng tên thì thêm hậu tố). Từ chối -> chỉ ghi trạng thái. (ok, err|record)."""
    d = _pdoc()
    rec = next((x for x in d["items"] if x.get("id") == pid), None)
    if not rec:
        return False, "Không tìm thấy đề xuất"
    if rec.get("status") != "pending":
        return False, "Đề xuất này đã được xử lý"
    if approve:
        _, f = proposal_file(pid)
        if not f:
            return False, "Bản chụp của đề xuất không còn"
        dest_dir = Path(shared_root) / SHARED_INBOX_REL / rec["brain"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f.name
        n = 2
        while dest.exists():
            dest = dest_dir / f"{f.stem}-{n}{f.suffix}"
            n += 1
        dest.write_bytes(f.read_bytes())
        rec["dest"] = dest.relative_to(Path(shared_root)).as_posix()
        rec["status"] = "approved"
    else:
        rec["status"] = "rejected"
        rec["reason"] = str(reason or "").strip()[:300]
    rec["ts_done"] = time.time()
    _psave(d)
    return True, rec
