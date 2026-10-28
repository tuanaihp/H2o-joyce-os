# Joyce Harness: khung harness của Joyce (bản 2)

> Tài liệu SỐNG. Đổi harness thì sửa bảng chấm điểm ở mục 3, mục kiểm tra ở mục 11, và thêm một dòng vào "Nhật ký cập nhật" ở cuối.
> Bản 1: 2026-10-28 (chấm theo bài giảng). Bản 2: 2026-10-28, viết lại thành khung ba tầng, có ghép phương pháp của repo Harness² và sửa các nhận định sai của bản 1.
> Soi trên nhánh `claude/crm-v2-final-1-3-35` (bản 1.3.38). Người đọc: chủ Joyce và các phiên Claude Code làm việc trên repo này.

## 0. Cách đọc

### 0.1 Nguồn

| Nguồn | Dùng để |
|---|---|
| Code Joyce (`server/`, `system/plugins/`, `dashboard/`) | Biết Joyce đang có gì thật |
| Dữ liệu thật trên máy chủ: 61 brain trong `brains/`, `server/settings.json`, `server/usage_index.db` | Biết cơ chế có đang chạy và có dữ liệu không. Chỉ đọc, không sửa |
| Repo Harness² (Google, bài báo arXiv 2610.14224), bản tải về ở `E:\CLAUDECODE\TOOK\harness2-main` | Phương pháp tự cải tiến harness và cách chia thành phần |
| Bài giảng "Harness" (các slide bếp phở anh gửi) | Chín thành phần cơ bản và các nguyên tắc vận hành |

### 0.2 Cấu trúc mỗi mục

Mỗi thành phần được viết theo năm phần cố định:
1. **Hiện trạng:** Joyce có gì, ở file nào, số liệu thật.
2. **Nguyên tắc:** bài giảng hoặc Harness² nói gì.
3. **Lỗ hổng:** chênh giữa hai cái trên.
4. **Giải pháp cho Joyce:** làm gì, áp vào công việc H2O ra sao.
5. **Đo:** biết đã xong bằng con số nào.

Thang điểm: **Tốt** (đủ và có kiểm chứng), **Khá** (có, còn lỗ hổng rõ), **Thiếu** (có cơ chế nhưng gần như không dùng, hoặc thiếu mảnh quan trọng), **Chưa có**.

### 0.3 Ràng buộc của chủ mà mọi giải pháp phải giữ

Đây là các quyết định chủ đã chốt. Giải pháp nào đi ngược thì phải hỏi chủ trước, không tự làm.

| Ràng buộc | Nguồn | Hệ quả cho harness |
|---|---|---|
| Vận hành không tốn quota: gửi bài, chấm điểm, nhắc việc, ghi sổ chạy bằng luật cố định; model chỉ để soạn nội dung và phán đoán | Bộ nhớ dự án | Kiểm tra nên viết bằng script và code trước, chỉ dùng model khi thật sự cần phán đoán |
| Không có vòng nền quét và nâng cấp skill, agent hàng loạt (16/08/2026) | `CLAUDE.md` gốc | Tự cải tiến chỉ chạy khi có bằng chứng cụ thể, lúc đang dùng, không theo lịch |
| Joyce tự hành động, bỏ luật "tiền, đơn, đăng bài, nhắn tin không tự động" (10/09/2026) | `CLAUDE.md` gốc | Cổng xin phép phải là tùy chọn theo loại thao tác, mặc định tắt |
| Giữ nguyên 44 phòng H2O, mỗi việc do agent đúng phòng làm | Bộ nhớ dự án | Gói harness đặt theo phòng, không gom về Joyce |
| `brains/` không có git, xóa là mất vĩnh viễn | Bộ nhớ dự án | Mọi sửa tự động vào brain phải có bản sao lưu và đường lật lại |
| Không dùng ký tự gạch dài, xưng hô theo người dùng | `CLAUDE.md` gốc | Áp cho cả prompt agent sinh ra |

## 1. Kết luận

### 1.1 Trả lời ngắn

- **Harness của Joyce đã tốt chưa?** Lõi chạy (vòng lặp, ngữ cảnh, hub công cụ, phân quyền) ở mức khá đến tốt. Vòng tự cải tiến đã được viết khá đầy đủ nhưng gần như chưa chạy. Phần yếu nhất là "một agent là gì": agent mới là một file prompt, chưa là một gói có phạm vi, ca thử và cách kiểm của riêng nó.
- **Agent các phòng đã có harness chưa?** Có khung, chưa có ruột. 61 brain đều có agent, skill, workflow, bộ nhớ, cấu hình factory. Nhưng 549 trên 600 agent là bản sao dùng chung, bộ nhớ gần như trống, không phòng nào có lệnh kiểm tra sau việc, và chỉ 1 bộ ca thử tồn tại trên cả hệ thống.

### 1.2 Khung Joyce Harness ba tầng

Harness² tách hai thứ: **hạ tầng đóng băng** (CLI, công cụ gốc, nhà cung cấp model) và **bề mặt sửa được** (tám thành phần quanh model). Rồi thêm một vòng **tự cải tiến bề mặt** dựa trên bằng chứng chạy thật. Joyce đặt vào đúng khung đó thành ba tầng:

```
TẦNG C  VÒNG CẢI TIẾN          đề xuất -> chạy thử -> so sánh -> chọn -> áp có canary -> ghi kinh nghiệm
          (harnessing)          ky-su-harness, giam-dinh-harness, factory.py, Joyce/proposals, Joyce/evals
                 |  sửa
                 v
TẦNG B  BỀ MẶT NGHỀ             mỗi agent / mỗi phòng một gói:
          (của từng phòng)       prompt, nội quy, bộ nhớ, hướng dẫn công cụ, agent con,
                                 skill, script kiểm tra, hook, phạm vi, ca thử, cách kiểm
                 |  chạy trên
                 v
TẦNG A  LÕI CHẠY                vòng lặp, ngữ cảnh, lắp prompt, hub công cụ, quyền,
          (app sở hữu, cố định)  hook, nhật ký, sandbox, giới hạn tài nguyên, bộ nhớ lõi
                 |  gọi
                 v
        MODEL (12 bộ não, đổi ở trang Models)
```

Quy tắc giữa các tầng:
- Tầng A do app sở hữu, chỉ đổi qua bản phát hành. Model và agent không được sửa nó.
- Tầng B là thứ chủ, trưởng phòng và Tầng C được sửa. Mỗi lần sửa phải đi qua kiểm tra của Tầng A (khuôn, quyền, khóa mục hệ thống).
- Tầng C không bao giờ tự cấp thêm quyền cho Tầng B (đúng bất biến "replan không cấp thêm quyền" đã có ở `server/agent_runtime.py`).

### 1.3 Năm phát hiện chính của bản 2

1. **Vòng tự cải tiến đã có, bản 1 bỏ sót.** `server/factory.py` (1.379 dòng) đã có: chạy lệnh kiểm sau việc rồi tự mở việc sửa (CI babysit), theo dõi kết quả sau khi xong (watch), gom lỗi cùng gốc thành một việc, tự áp đề xuất cải tiến có bản sao lưu, áp thử ở một brain 24 giờ rồi mới nhân (canary) và tự lật lại khi có tín hiệu xấu, bảng điểm từng agent, tỉ lệ việc tự chạy không cần người. Factory đang BẬT ở cả 61 brain.
2. **Nhưng gần như không có gì chảy qua nó.** Lệnh kiểm sau việc (`post_check`) rỗng ở cả 61 brain. Cả hệ thống có 1 bộ ca thử (`Brain Default/Joyce/evals/giam-dinh-harness.json`) và 2 đề xuất cải tiến (đều ở Brain Default, đều loại sửa lỗi hiệu năng). Vòng PPC mới chạy 4 lần, ra 2 bài học. Tức là nhà máy dựng xong mà chưa có nguyên liệu.
3. **Joyce đã mượn Harness² nửa chừng.** Agent `ky-su-harness` ghi rõ là "Propose của PPC", `giam-dinh-harness` là "Compose của PPC", skill `cham-diem-tuong-phan` dịch nguyên ba khối prompt từ `harness2/core/prompts.py`. Phần còn thiếu là phần quan trọng nhất của Harness²: **Probe**, tức chạy thử bản sửa trên cùng việc thật rồi so hành vi. Giám định của Joyce hiện so hai bản CHỮ của prompt, không so hai lần CHẠY.
4. **Workflow có vòng kiểm chứng, chat thì không.** Bước workflow khai `verify_agent` thì có agent khác kiểm, chưa đạt làm lại, không rõ kết luận là hỏng. Nhưng chỉ 5 trên 239 file workflow dùng, và chat không có bước kiểm cuối.
5. **Lõi chạy còn ba lỗ đáng vá sớm vì rẻ:** prefix cache bị phá bởi khối đổi mỗi lượt (Claude Code qua Joyce chỉ trúng 76%), không có hook bảo vệ nào bật sẵn, và kết quả công cụ cũ không được dọn trong một lượt dài.

## 2. Gói harness của một agent (mục tiêu của Tầng B)

Đây là hình dạng đích. Phần lớn đã có chỗ để đặt, chỉ chưa được điền.

| Thành phần (Harness²) | Đặt ở đâu trong brain phòng | Đã có chưa |
|---|---|---|
| c1 Thân prompt | `agents/<slug>.md`, thân file | Có, 600 file |
| Phạm vi (mới, không có trong Harness²) | `agents/<slug>.md`, frontmatter: `kind`, `tools`, `mode`, `max_rounds`, `max_minutes`, `verify` | Chưa |
| c2 Nội quy luôn bật | Đề xuất: `Joyce/noi-quy.md` của phòng, app tự ghép vào khối phòng ban của prompt | Chưa. Hiện nằm rải trong mục "Cấm" của từng agent |
| c3 Bộ nhớ dài hạn | `memory/` của brain và `memory/agents/<slug>/MEMORY.md` | Có cơ chế, gần như không có dữ liệu |
| c4 Hướng dẫn dùng công cụ | Đề xuất: mục "Công cụ" trong `Joyce/noi-quy.md`, cộng mô tả của từng tool | Một phần: mô tả tool có, hướng dẫn theo phòng chưa |
| c5 Agent con | Agent khác trong cùng brain hoặc `Ten Brain\|slug` ở workflow | Có cách gọi, chưa có kiểu khai báo |
| c6 Skill | `skills/<slug>/SKILL.md` | Có, phần lớn là skill hệ thống |
| c7 Script kiểm tra cố định | `Joyce/scripts/*.py` | Có thư mục ở Brain Default (`h2o-bao-cao.py`), chưa có ở phòng |
| c8 Plugin và hook | `plugins/<slug>/` (vault) hoặc plugin hệ thống | Có hạ tầng, chưa có hook bảo vệ |
| Ca thử | `Joyce/evals/<slug>.json` | Có cơ chế (`factory.eval_for_draft`), 1 file trên cả hệ thống |
| Cách kiểm sau việc | `Joyce/factory.json` (`post_check`, `watch`), `verify_agent` trong workflow | Có cơ chế, rỗng |
| Đề xuất và kinh nghiệm | `Joyce/proposals/`, `Joyce/learn-log/`, đề xuất thêm `Joyce/kinh-nghiem/` | Có hai thư mục đầu |

### 2.1 Chọn thành phần rẻ nhất mà hiệu quả

Harness² dặn người sửa harness: "khớp mỗi lỗi với thành phần rẻ nhất mà hiệu quả", và không thêm code cho một lỗi chỉ gặp một lần. Đây cũng là cách tôn trọng luật "vận hành không tốn quota". Thang từ rẻ đến đắt:

| Bậc | Dùng khi | Chi phí mỗi lượt | Ví dụ H2O |
|---|---|---|---|
| 1. Một dòng trong thân prompt hoặc nội quy | Lỗi thứ tự làm việc bình thường, áp cho MỌI việc của phòng | Trả mỗi lượt, nên có trần | "Gọi `joyce_shop op=gia` trước khi báo giá cho khách, không đọc giá từ trí nhớ" |
| 2. Skill | Quy trình nhiều bước có dấu hiệu kích hoạt rõ | Chỉ tốn khi dùng | Quy trình đối soát cuối tháng của Phòng Đối Soát |
| 3. Script cố định | Việc lặp lại có đầu vào, đầu ra rõ: trích, đổi định dạng, kiểm số | Không tốn model | `kiem_so.py` đối chiếu tổng thu trừ tổng chi bằng lãi gộp |
| 4. Hook | Lời dặn đã rõ mà model vẫn bỏ qua nhiều lần, cần kiểm lại ngay trong vòng | Không tốn model (hoặc rất ít) | Sau mỗi `joyce_shop op=ghi` có khoản chi lớn, hook kiểm đã gắn hợp đồng chưa |
| 5. Code lõi (Tầng A) | Đúng cho mọi phòng, mọi engine | Không tốn, nhưng cần phát hành | Chống ghi trùng 10 phút của Sổ Shop |

Harness² còn hai luật đi kèm: bộ nhớ luôn bật chỉ chứa sự thật ngắn đúng cho MỌI việc của lĩnh vực đó ("thêm thì phải bớt"), và **không bao giờ lưu sự việc của một vụ cụ thể làm bộ nhớ bền**, vì nó thành mỏ neo sai cho vụ sau.

## 3. Bảng chấm điểm

| Mã | Thành phần | Mức | Một dòng lý do |
|---|---|---|---|
| **A** | **Lõi chạy** | | |
| A1 | Vòng lặp | Khá | Trần 30 vòng, phanh lặp, thử lại, chat sống qua F5. Chưa có trần theo agent |
| A2 | Ngữ cảnh và dọn bàn | Khá | Nén tóm tắt, Adaptive Runtime chạy thật. Không dọn kết quả cũ trong lượt |
| A3 | Lắp prompt và prefix cache | Khá | Xếp lớp đúng thứ tự. Khối động phá cache, Claude Code qua Joyce trúng 76% |
| A4 | Hub công cụ và registry | Tốt | Một cửa cho mọi engine, registry đủ trường, nạp tool lười |
| A5 | Quyền và xin phép | Khá | Ba mức, kiểm từng lời gọi theo cả tham số. Không có trạng thái "dừng chờ chủ" chung |
| A6 | Hook | Thiếu | Hạ tầng chặn được và sửa được đầu vào. Không hook bảo vệ nào bật sẵn |
| A7 | Nhật ký và khôi phục | Khá | Kanban reclaim, nhóm chat recover, chat sống qua F5. Lịch sử chat sửa xóa được |
| A8 | Sandbox và giới hạn tài nguyên | Khá | Lệnh có rào, việc nền khóa, sổ cái token. Không có bản sao để chạy thử |
| A9 | Bộ nhớ lõi | Tốt | Có kiểm soát, quên có dấu vân tay, học có người duyệt, độc lập engine |
| **B** | **Bề mặt nghề** | | |
| B1 | Thân prompt agent | Khá | 600 file, đa số có Bối cảnh, Quy trình, Cấm. 549 là bản sao |
| B2 | Nội quy phòng | Thiếu | `CLAUDE.md` của phòng chỉ là lược đồ vault chung |
| B3 | Bộ nhớ phòng và agent | Thiếu | 54 trên 61 brain trống, 0 bài học agent |
| B4 | Hướng dẫn công cụ | Thiếu | Có mô tả tool, không có hướng dẫn theo phòng |
| B5 | Agent con | Thiếu | Gọi được, chưa khai báo ba kiểu khám phá, làm, kiểm |
| B6 | Skill | Khá | 530 skill, chỉ 54 tên, khoảng 41 skill nghiệp vụ riêng |
| B7 | Script kiểm tra | Chưa có | Một script ở Brain Default, không phòng nào có |
| B8 | Plugin và hook của phòng | Chưa có | Không phòng nào có hook riêng |
| B9 | Phạm vi agent | Chưa có | Frontmatter không có công cụ, quyền, trần |
| B10 | Cách kiểm theo loại việc | Thiếu | `verify_agent` ở 5 trên 239 workflow, `post_check` rỗng ở 61 brain |
| **C** | **Vòng cải tiến** | | |
| C1 | Đề xuất có bằng chứng | Khá | `ky-su-harness` đúng tinh thần, mới chạy 4 lần |
| C2 | Chạy thử bản sửa (Probe) | Chưa có | Giám định so chữ, không so lần chạy |
| C3 | Chọn ẩn danh | Khá | Có giao thức A/B ẩn danh, chưa có nhiều bản đã chạy để chọn |
| C4 | Áp an toàn (canary, lật lại) | Tốt | Có sẵn trong factory: sao lưu, canary 24 giờ, tự lật lại |
| C5 | Thư viện kinh nghiệm theo phòng | Thiếu | Có learn-log, chưa có kinh nghiệm dạng gợi ý, bài học, bằng chứng |
| C6 | Đo hiệu quả | Khá | Có bảng điểm agent và tỉ lệ tự chạy, chưa ai nhìn |

## 4. Tầng A: lõi chạy

### A1. Vòng lặp

**Hiện trạng**
- Engine API (OpenAI, Anthropic API, Gemini, OpenRouter, Groq, DeepSeek, Z.ai, Ollama): vòng tool tự viết ở `server/engine.py::_cc_tool_loop`. Trần `JOYCE_MAX_TOOL_ROUNDS` mặc định 30 (kẹp 1 đến 120), chạm trần báo cách xử lý. `_LapGuard`: gọi y hệt cùng tool cùng tham số thì nhắc ở lần thứ 3, dừng ở lần thứ 5; chỉ bắt lặp tuyệt đối liên tiếp nên đọc, sửa, đọc lại không bị bắt oan. `thu_lai_khi_tam_thoi` thử lại 3 lần có chờ và đọc `Retry-After`.
- Engine CLI (Claude Code, Codex, Grok Build, Antigravity): vòng do CLI chạy, Joyce bọc trần thời gian việc nền (`JOYCE_BG_MAX_WALL_S`, mặc định 1 giờ) và chuỗi dự phòng `aux_engine.swap` (chỉ đổi engine khi bước trước chưa gọi tool nào).
- Lượt chat là việc của máy chủ (`chat_runtime.py`), đóng tab hay F5 không hủy. Tin gõ thêm giữa chừng được đưa vào bước kế (`steer_inbox.py`).

**Nguyên tắc**: bài giảng "làm, kiểm tra, nhận kết quả, điều chỉnh"; Harness² định nghĩa "đủ bằng chứng" và "kiểm lại sản phẩm, một lần ghi thành công không chứng minh dùng được".

**Lỗ hổng**
- Trần vòng và thời gian là cấu hình toàn máy, không đặt theo agent. Một agent soạn nội dung và một agent đối soát dùng chung trần 30 vòng.
- Vòng không có bước "mở lại sản phẩm để kiểm" trước khi trả lời.

**Giải pháp cho Joyce**
- Đọc `max_rounds`, `max_minutes` từ frontmatter agent (B9), mặc định giữ 30 vòng và 1 giờ. Đưa vào `_max_tool_rounds()` qua ngữ cảnh lượt, không đổi chữ ký hàm.
- Thêm luật vào nội quy các phòng ghi sổ: "sau khi ghi, gọi `joyce_shop op=xem` hoặc đọc lại phiếu vừa ghi rồi mới báo xong". Rẻ, bậc 1.

**Đo**: số lượt chạm trần vòng mỗi tuần theo agent; số lượt bị `_LapGuard` dừng.

### A2. Ngữ cảnh và dọn bàn

**Hiện trạng**
- `server/compaction.py`: giữ nguyên 12 tin gần nhất, phần cũ gộp thành tóm tắt tối đa 6.000 ký tự; lời nhắc tóm tắt dặn giữ quyết định, con số, tên riêng, đường dẫn, việc dang dở. Đuôi chưa nén dài hơn 24 tin thì nén đồng bộ trước khi gửi, để phần cũ không bị cắt câm.
- Engine CLI tự quản mạch; Codex và Claude Code xoay mạch ở 1.000.000 token, mang gói mồi tối đa 300.000 ký tự. Antigravity gửi 45.000 ký tự mỗi lượt.
- Mỗi kết quả tool cắt ở 8.000 ký tự, giữ đầu 60% và cuối 40% kèm dòng báo bỏ bao nhiêu (`_clip_tool_result`).
- Adaptive Context Runtime chạy thật trên máy (mục 12): capsule thay prompt đầy đủ, nạp tool lười khi từ 40 tool trở lên (phơi 8 tool khớp nhất trong 6.000 ký tự).

**Nguyên tắc**: bài giảng "dọn context, giữ thông tin cần thiết", ba nhóm giữ nguyên, tóm tắt, loại bỏ. Harness² cảnh báo ngược chiều: cắt nhật ký dưới 10.000 ký tự khi đưa cho người phân tích là "khoảng bịa ra lỗi" (`BenchSpec.obs_trunc` từ chối giá trị dưới 10.000), vì người đọc thấy chỗ cụt và tưởng agent làm thiếu.

**Lỗ hổng**
- Không dọn kết quả cũ trong cùng lượt: 30 vòng nhân 8.000 ký tự là tới khoảng 240.000 ký tự trên bàn.
- Bản tóm tắt là một khối phẳng, không có chỗ ghim dữ kiện tuyệt đối không được mất.
- Nếu Tầng C đọc nhật ký đã bị cắt 8.000 ký tự để chẩn đoán agent, nó rơi đúng vào vùng "bịa ra lỗi" của Harness².

**Giải pháp cho Joyce**
- Dọn trong lượt: khi tổng ký tự kết quả tool vượt ngưỡng (đề xuất 60.000), thay các kết quả cũ (trừ 3 kết quả mới nhất) bằng một dòng "đã đọc X, kết quả chính: ..." lấy từ phần đầu đã có. Không gọi model để tóm tắt.
- Ghim dữ kiện: phần tóm tắt có mục riêng "Không được mất" do code điền từ sự kiện Sổ Shop của phiên (mã hợp đồng, số tiền, số điện thoại khách). Ví dụ: chat 40 lượt về hợp đồng Tuấn Thủy thì mã HD0001 và số 15.000.000 vẫn còn sau nén.
- Khi Tầng C cần bằng chứng, đọc nhật ký gốc từ nơi lưu (tin chat, `task_events`), không đọc bản đã cắt.

**Đo**: kích thước trung bình payload vòng cuối của lượt dài; test "hỏi lại sau nén" cho các dữ kiện đã ghim.

### A3. Lắp prompt và prefix cache

**Hiện trạng**
- `main.py::build_system_prompt` xếp từ ổn định đến thay đổi: `CLAUDE.md` gốc (31.362 byte), hồ sơ, bộ nhớ, chỉ mục wiki (tối đa 8.000 ký tự), khối phòng ban H2O, dự án, cuộc chat, lớp agentic, chỉ mục năng lực, router skill, rồi khối "Bây giờ" (giờ theo phút), khối ngôn ngữ, khối "Mức dùng hôm nay" (token tăng sau mỗi lượt).
- Đánh dấu cache cho Anthropic `_apply_anthropic_cache`: biến system thành MỘT khối rồi gắn dấu lên khối đó, cộng 3 tin cuối.
- Số đo thật từ `usage_index.db` (tỉ lệ đọc cache trên tổng token vào):

| Nguồn | Lượt | Cache |
|---|---|---|
| Claude Code qua Joyce, chat | 219 | 84% |
| Claude Code qua Joyce, việc nền | 760 | 73% |
| Codex qua Joyce | 7.879 | 96% |
| Claude Code chạy tay, không qua Joyce | 48.048 | 98% |
| Engine API qua Joyce | 24 | 0% (mẫu nhỏ, model mã nguồn mở, có thể nhà cung cấp không báo số cache) |

**Nguyên tắc**: bài giảng "phần tĩnh trước, phần động sau", "chèn dòng ở đầu phải xử lý lại, tốn thêm thời gian và tiền".

**Lỗ hổng**: thứ tự đã đúng, nhưng khối động nằm CHUNG khối với phần tĩnh nên mỗi lượt cả system đổi. Ghi chú trong `context_compiler.dong_ho` còn ghi "system prompt của Joyce vốn đã đổi mỗi lượt", tức đã biết và chấp nhận.

**Giải pháp cho Joyce**
- Tách system thành hai khối: tĩnh (tới hết router skill) có dấu cache, động (giờ, ngôn ngữ, mức dùng) không dấu.
- Với Claude Code và Codex: giữ phần tĩnh ổn định, đưa phần động vào tin nhắn người dùng của lượt.
- Đẩy chỉ mục bộ nhớ và chỉ mục wiki xuống sau các khối bất biến thật, vì hai khối này đổi khi có ghi nhớ mới.

**Đo**: tỉ lệ cache của Claude Code qua Joyce, mục tiêu từ 76% lên trên 90%, đo trước và sau trên cùng một tuần dùng.

### A4. Hub công cụ và registry

**Hiện trạng**
- `server/mcp_hub.py`: ba nguồn qua một cửa (MCP ngoài, tool lõi, plugin). Tool lõi: `joyce_read_file`, `joyce_list_dir`, `joyce_write_file`, `joyce_use_skill`, `joyce_connections`, `joyce_search_tools`, `joyce_run_tool`, và `joyce_run_command` chỉ khi phiên có thư mục làm việc.
- Registry đủ bốn trường của bài giảng (tên, quyền, hàm xử lý, mô tả): `ctx.register_tool(name, description, handler, schema, min_mode)`; route MCP có `effect`, `required_mode`, `source_type`. Có Capability Registry dẫn xuất (`capability_registry.py`) với tìm kiếm lai chữ và embedding.
- 24 plugin đi kèm, ví dụ `joyce-shop`, `joyce-task`, `joyce-schedule`, `web-pilot`.

**Nguyên tắc**: Harness² xem "hướng dẫn dùng công cụ" (c4) là một thành phần sửa được riêng, khác với bản thân công cụ.

**Lỗ hổng**
- Engine API không sửa được từng đoạn file, chỉ ghi lại cả file. Trong chat thường không có tool chạy lệnh.
- Mô tả tool viết một lần cho mọi phòng. Không có chỗ để Phòng Chi nói "với chúng tôi, `joyce_shop` dùng như sau".

**Giải pháp cho Joyce**
- Thêm tool lõi `joyce_edit_file` (thay một đoạn duy nhất, giống Edit của Claude Code), bậc 5, có ích cho mọi phòng sửa wiki và báo giá.
- Mục "Công cụ" trong `Joyce/noi-quy.md` của phòng (B4).

**Đo**: số lần `joyce_write_file` ghi lại file lớn hơn 20 KB; số lỗi "ghi đè mất nội dung".

### A5. Quyền và xin phép

**Hiện trạng**
- Ba mức theo phiên: chỉ đọc (`suggest`), an toàn (`auto`), đầy đủ (`full`). Codex ánh xạ sang `--sandbox read-only`, `workspace-write`, không rào.
- `mcp_hub._guard` kiểm TỪNG lời gọi: `mcp_catalog.classify` phân loại đọc, ghi, nguy hiểm theo cả tham số; tool cổng gộp nhiều lệnh con lấy mức nặng nhất; thiếu tham số quyết định thì coi là nguy hiểm. Tool ghi bị ẩn ngay lúc liệt kê ở mức Chỉ đọc. Giới hạn tần suất theo từng kết nối.
- Phạm vi người: nhân viên bị khóa vào phòng (`_STAFF_SCOPE`), bot khách hàng không dùng được 12 công cụ gốc và 4 tool chỉ của chủ.
- Xin phép có ở: Sổ Shop (chi của nhân viên từ 2.000.000 đồng chờ chủ hoặc giám đốc duyệt, trưởng phòng không tự duyệt chi của mình), Kanban (`needs_approval`, risk cao vào cột Review, nhưng duyệt SAU khi chạy), factory `low_risk_auto` (việc rủi ro thấp và chỉ ghi trong brain thì tự qua; tiền và ghi ra ngoài không bao giờ tự qua).

**Nguyên tắc**: bài giảng ba phạm vi quyền, "cùng công cụ khác cách dùng", "đổ nồi nước dùng cần chủ quán đồng ý", "rõ việc tự làm, rõ việc cần con người".

**Lỗ hổng**
- Không có trạng thái thứ ba "tạm dừng, giải thích, chờ chủ bấm" cho một thao tác cụ thể trong chat.
- Quyền ở cấp phiên và kết nối, không ở cấp agent.

**Giải pháp cho Joyce**
- Cổng xin phép TÙY CHỌN theo loại thao tác, mặc định tắt (tôn trọng quyết định 10/09). Chủ bật loại nào thì loại đó dừng: ví dụ "gửi Zalo cho hơn 5 người", "xóa file trong brain", "ghi chi trên 10 triệu". Dùng lại `WAITING_USER` và mã xác nhận đã có ở `write_path_runtime.py`.
- Một trang "Việc tự làm và việc cần anh" liệt kê bảng phân loại hiện hành, để chủ và trưởng phòng cùng đọc.

**Đo**: số lần cổng dừng mỗi tuần, thời gian chờ chủ trung bình.

### A6. Hook

**Hiện trạng** (`server/plugins_host.py`)
- `pre_tool_call` chặn được (`{"deny": lý do}`), sửa được tham số (`{"args": ...}`), hoặc cho qua. Hook ném lỗi thì tool vẫn chạy (fail-open có chủ ý). `post_tool_call` quan sát, kể cả lời gọi bị chặn. Cả hai biết ai đang nói qua `turn` (kênh, người gửi, nhóm hay riêng, có phải chủ).
- `chatbot_turn_context`: mỗi lượt bot khách được thêm đúng một dòng ngữ cảnh, quá 2 giây thì bỏ.
- Plugin duy nhất dùng hook là `tool-audit`, chỉ đếm, manifest tắt mặc định.

**Nguyên tắc**: bài giảng "lời nhắc và cơ chế cần phối hợp", hook gắn quy định công ty (bảo mật, kiểm toán, tuân thủ), "JSON vào, mã thoát ra, gắn kiểm tra mà không sửa phần lõi". Harness² dùng plugin `tool.execute.after` để **kiểm lại sản phẩm ngay trong vòng** (sau khi ghi thì kiểm, thiếu thì nối cảnh báo vào kết quả), thay vì một lời dặn tĩnh.

**Lỗ hổng**: không có hook bảo vệ nào chạy sẵn; không gắn được kiểm tra bằng script ngoài mà không viết plugin Python.

**Giải pháp cho Joyce**
- Plugin hệ thống `joyce-guard`, bật sẵn, ba luật đầu tiên đều bằng code, không tốn model:
  1. Chặn ghi ra ngoài brain và vào `sources/` (nguồn bất biến theo lược đồ vault).
  2. Chặn gửi Zalo hàng loạt quá N người trong M phút khi người gọi không phải chủ.
  3. Sau `joyce_shop op=ghi`, nếu có khoản chi lớn chưa gắn hợp đồng thì nối cảnh báo vào kết quả để model hỏi lại chủ (kiểu `tool.execute.after` của Harness²).
- Bộ chuyển hook ngoài: khai trong `Joyce/hooks.json` một lệnh (đọc JSON từ stdin, trả mã thoát 0 cho qua, 2 chặn kèm lý do), để chủ gắn quy định riêng của studio mà không viết plugin.

**Đo**: số lần mỗi luật chặn mỗi tuần (đọc từ `post_tool_call` có `denied`).

### A7. Nhật ký và khôi phục

**Hiện trạng**
- Lịch sử chat trong SQLite là nguồn sự thật (`sessions.py`, `conversations.py`). Nhật ký kiểm toán hub là file chỉ ghi thêm, xoay vòng ở 5 MB, chỉ ghi TÊN tham số. Nhật ký việc `task_events`. Checkpoint Task State mã hóa chỉ ghi thêm trong `runtime.db`.
- Khôi phục: Kanban lease 90 giây và `reclaim_stale`; nhóm chat `TeamRunner.recover` (đã qua mốc gọi engine thì đánh dấu `interrupted`, chặn việc, không tự chạy lại để khỏi làm trùng việc ghi ra ngoài); workflow đồ thị có checkpoint nhưng đang 0%.
- Bộ nhớ độc lập với harness: đổi engine giữa chừng vẫn nạp lại mạch.

**Nguyên tắc**: bài giảng "nhật ký chỉ ghi thêm", "đầu bếp vắng mặt nhật ký vẫn còn", "replay đọc lại từ đầu đến cuối". Harness² mỗi lần chạy có thư mục riêng, chạy lại cùng lệnh thì tiếp tục từ chỗ dở (idempotent theo `run_id`).

**Lỗ hổng**: lịch sử chat sửa và xóa được; `task_events` bị xóa khi xóa việc; nhật ký kiểm toán chỉ giữ khoảng 10 MB; chưa có một nhật ký sự kiện chung của một lượt agent để đọc lại.

**Giải pháp cho Joyce**
- Không cần đổi lịch sử chat (sửa và chạy lại là tính năng). Thay vào đó: một **sổ sự kiện chỉ ghi thêm** riêng cho việc có tác dụng ra ngoài (ghi sổ tiền, gửi tin, đăng bài, xóa file), mỗi dòng có lượt, agent, tool, kết quả, giữ ít nhất 12 tháng. Sổ Shop đã có `so_hoat_dong` đúng tinh thần này; mở rộng thành chung.
- Bật `workflow_canary` cho các workflow nền chạm tiền, để tiến trình chết không chạy lại bước đã ghi.

**Đo**: có trả lời được câu "tuần trước agent nào đã ghi khoản chi này" từ sổ sự kiện không.

### A8. Sandbox và giới hạn tài nguyên

**Hiện trạng**
- Sandbox engine: Codex `--sandbox`; Claude Code SDK `can_use_tool` kiểm từng lời gọi cho việc nền; việc nền cấm Bash, WebFetch, WebSearch, Task, MCP rỗng.
- Cô lập thư mục: `cwd` ghim vào brain hoặc thư mục tab Code, `_safe_path` chặn thoát thư mục, thư mục riêng từng nhân viên `staff_workspaces/`.
- `run_command.py`: một lệnh mỗi lần, không qua shell, môi trường lọc trắng (khóa API trong `.env` không lọt vào lệnh), trần thời gian và output, danh sách lệnh cho mức `auto` (pytest, npm test, ruff, eslint, grep, rg, git chỉ đọc), chặn cứng một số lệnh phá hoại ở mọi mức.
- Tài nguyên: sổ cái token mỗi phút dùng chung (`quota_scheduler.py`), học hạn mức từ lỗi nhà cung cấp (`limit_learner.py`), giới hạn tần suất theo kết nối, ngân sách lượt mỗi ngày cho agent nhóm (`agent_budget`).

**Nguyên tắc**: bài giảng "một căn bếp thử nghiệm riêng", "giới hạn cả dữ liệu và tài nguyên". Harness² mỗi bản harness được dựng ra thư mục riêng (`write_tree` vào `harnesses/<label>`) và chạy độc lập, chạy thật mà không đụng bản gốc.

**Lỗ hổng**: không có bản sao để agent thử rồi người duyệt mới áp; không có trần chi phí theo agent hay phòng.

**Giải pháp cho Joyce**
- "Chạy thử trong bản sao": app đã tách được `BRAINS_DIR` và `JOYCE_STATE_DIR` (em dùng đúng cách này để thử Sổ Shop ở bản 1.3.37 và 1.3.38). Thêm một chế độ tạo bản sao tạm của brain phòng và sổ, agent làm trên bản sao, kết quả hiện dạng so sánh, chủ bấm áp. Đây cũng là nền cho Probe ở C2.
- Trần chi phí theo phòng mỗi ngày, đọc từ `usage_store`, chạm trần thì việc nền của phòng đó xếp hàng chờ.

**Đo**: số việc chạy thử trước khi áp; chi phí theo phòng mỗi tuần.

### A9. Bộ nhớ lõi

**Hiện trạng**: `memory/MEMORY.md` (chỉ mục nạp mỗi lượt), `memory/facts/` (một sự thật một file), `memory/conversations/` (nhật ký thô), `memory/agents/<slug>/MEMORY.md`. `memory_control.py` cho xem, sửa, quên (giữ dấu vân tay để không dựng lại), tắt học theo brain. `learn.py`: nhánh học chỉ đọc, trả manifest, chỉ Python tin cậy mới ghi, quét bí mật và chèn lệnh trước khi ghi, giới hạn tần suất cứng. Bài học agent theo "model đề xuất, code ghi", chờ chủ duyệt.

**Nguyên tắc**: bài giảng "bộ nhớ độc lập với harness". Harness² tách bộ nhớ bền (sự thật ngắn, chung) khỏi sự việc của từng vụ.

**Lỗ hổng**: cơ chế tốt, nằm ở Tầng A là đúng. Lỗ hổng thật là dữ liệu (B3).

**Giải pháp cho Joyce**: giữ nguyên lõi. Thêm một kiểm tra khi ghi: nếu một mục bộ nhớ chứa số điện thoại, mã hợp đồng hoặc số tiền cụ thể của một khách thì đẩy sang CRM hoặc Sổ Shop thay vì bộ nhớ bền (luật "không lưu sự việc một vụ" của Harness²).

**Đo**: số mục bộ nhớ bị đẩy sang CRM hoặc sổ.

## 5. Tầng B: bề mặt nghề của từng phòng

Số liệu quét 61 brain ngày 28/10/2026, chỉ đọc:

| Chỉ số | Giá trị |
|---|---|
| Brain | 61 (43 phòng có Agent Trưởng Phòng, 14 brain khối, 4 brain cá nhân hoặc chung) |
| Agent | 600, chỉ 59 tên khác nhau; 549 là 9 agent dùng chung nhân vào cả 61 brain |
| Skill | 530, chỉ 54 tên; khoảng 41 skill nghiệp vụ mỗi cái chỉ ở một phòng |
| Workflow | 239, chỉ 13 tên; 3 workflow dùng chung ở cả 61 brain |
| Agent có `skills` rỗng | 490 trên 600 |
| Agent có đặt `model` | 50 trên 600 |
| Agent có mục Bối cảnh, Quy trình, Cấm | 410, 471, 427 |
| Brain có chỉ mục bộ nhớ không trống | 7 trên 61 |
| File bộ nhớ agent, có bài học | 48, và 0 |
| `post_check` trong `Joyce/factory.json` | rỗng ở 61 trên 61 |
| Bộ ca thử `Joyce/evals/*.json` | 1 trên cả hệ thống |

Chín agent dùng chung, có mặt y hệt ở cả 61 brain (cùng nội dung, không do app quản lý: `.joyce/system-manifest.json` của brain chỉ quản skill hệ thống, không quản các agent này, nên sửa một bản không cập nhật 60 bản kia):

| Slug | Tên | Làm gì | Thuộc nhóm | Dùng ở workflow |
|---|---|---|---|---|
| `ky-su-harness` | Kỹ sư Cải tiến Agent | Đề xuất sửa prompt, skill, agent từ bằng chứng thật (Propose) | Tầng C | `tu-cai-tien-agent` |
| `giam-dinh-harness` | Giám định Tương phản | Chấm ẩn danh bản đề xuất với bản gốc, quyết thắng, giữ, chưa rõ (Compose) | Tầng C | `tu-cai-tien-agent` |
| `giam-dinh-bao-mat` | Giám định Bảo mật | Soát lộ khóa, nâng quyền, chèn lệnh, lộ dữ liệu trong một đề xuất | Tầng C, lưới review | `review-da-mien` |
| `giam-dinh-du-lieu` | Giám định Dữ liệu | Soát tương thích ngược, định dạng lưu, đổi nghĩa trường | Tầng C, lưới review | `review-da-mien` |
| `giam-dinh-noi-dung` | Giám định Nội dung | Soát giọng thương hiệu, đúng chủ đề, ngôn ngữ, không bịa | Tầng C, lưới review; dùng được làm `verify_agent` cho nội dung marketing | `review-da-mien` |
| `giam-dinh-ux` | Giám định Trải nghiệm | Soát luồng người dùng, thông báo, độ rõ, chống spam | Tầng C, lưới review | `review-da-mien` |
| `ke-toan-vien-dai-tu` | Kế toán viên Đại-tu | Khảo sát code, lập kế hoạch chia một cuộc đại tu thành chuỗi việc nhỏ | Việc code | `dai-tu-codebase` |
| `giam-sat-dai-tu` | Giám sát Đại-tu | Kiểm kế hoạch đại tu rồi xếp chuỗi việc Kanban nối nhau | Việc code | `dai-tu-codebase` |
| `tro-ly-onboarding` | Trợ lý Onboarding | Trả lời "cách làm X" cho người mới của phòng, dựa trên wiki và nguồn của chính phòng đó | Phòng nghiệp vụ (agent duy nhất trong chín cái thật sự cần ở mọi phòng) | không |

Nhận xét: tám cái đầu là bộ máy cải tiến hệ thống và việc code, không phải việc của phòng nghiệp vụ. `ke-toan-vien-dai-tu` không liên quan Phòng Kế Toán, tên dễ gây nhầm khi Joyce định tuyến việc kế toán. `tro-ly-onboarding` đúng là việc của phòng nhưng nội dung giống nhau, chỉ khác dữ liệu nó đọc.

### B1. Thân prompt agent (c1)

**Hiện trạng**: Agent Trưởng Phòng có Bối cảnh, Nhiệm vụ, Cấm, ví dụ `truong-phong-chi.md`. Prompt agent khi chạy được ghép thêm khối bộ nhớ và luật `JOYCE_LESSON` (`main.py::_agent_sysprompt`).

**Nguyên tắc**: Harness² chia người sửa prompt làm hai: **INV** (cách agent làm việc: thứ tự, dùng tool, khi nào xong) và **DOM** (điều người làm nghề biết: sản phẩm, người dùng sản phẩm, nguồn chuẩn, cấu trúc bắt buộc, quy tắc nhất quán). Luật DOM: không bao giờ bịa nguồn hay con số; chỉ viết kiến thức agent ÁP DỤNG và KIỂM được, không viết bài đọc nền.

**Lỗ hổng**: thân prompt trưởng phòng nghiêng về mô tả vai, ít "quy tắc kiểm được". Ví dụ Phòng Chi viết "kiểm đề nghị chi có đủ chứng từ" nhưng không nói đủ là gồm những gì và kiểm bằng cách nào.

**Giải pháp cho Joyce**: chuẩn hóa thân prompt trưởng phòng thành hai phần đúng INV và DOM:
- "Cách làm" (INV): thứ tự gọi tool, điều kiện xong việc. Ví dụ Phòng Chi: "1) `joyce_shop op=xem` lấy hợp đồng liên quan; 2) ghi chi kèm `khach`; 3) đọc lại phiếu; 4) chỉ báo xong khi phiếu có mã".
- "Điều nghề biết" (DOM), viết thành quy tắc kiểm được. Ví dụ: "Chứng từ đủ = ngày, số tiền, đơn vị nhận, lý do. Thiếu một trong bốn thì ghi 'chờ bổ sung', không ghi sổ".

**Đo**: tỉ lệ việc của agent qua kiểm (B10) trước và sau khi chuẩn hóa.

### B2. Nội quy phòng (c2)

**Hiện trạng**: `CLAUDE.md` và `AGENTS.md` của mỗi brain là bản sao y hệt lược đồ vault chung (6.205 byte). Khối `_h2o_phong_block` thêm tên phòng, khối, thương hiệu, trưởng phòng, brain chung chỉ đọc.

**Nguyên tắc**: bài giảng "nội quy chung của cả chuỗi, riêng cách vận hành từng chi nhánh". Harness² có c2 guardrails là luật luôn bật, có trần ký tự cho phần luôn bật.

**Lỗ hổng**: không có chỗ cho luật nghiệp vụ riêng của phòng mà mọi agent trong phòng đều đọc.

**Giải pháp cho Joyce**
- File `Joyce/noi-quy.md` mỗi phòng, app ghép vào `_h2o_phong_block`, có trần 1.500 ký tự (luôn bật thì phải ngắn). Hai mục: "Luật" và "Công cụ".
- Ví dụ Phòng Thu: "Thu cọc phải gắn hợp đồng. Thu đủ lịch cọc thì báo bước tiếp theo theo bảng giá. Không tự đổi trạng thái hợp đồng sang Hoàn thành".
- Luật chung cả chuỗi H2O (thương hiệu, xưng hô với khách, cấm bịa giá) đặt một lần ở brain chung, không chép vào từng phòng.
- Sinh `AGENTS.md` từ `CLAUDE.md` thay vì giữ hai bản tay.

**Đo**: số phòng có nội quy; độ dài phần luôn bật mỗi phòng.

### B3. Bộ nhớ phòng và agent (c3)

**Hiện trạng**: 7 trên 61 brain có chỉ mục bộ nhớ không trống; 48 file bộ nhớ agent, 0 bài học; 37 nhật ký hội thoại trên toàn bộ brain.

**Nguyên tắc**: Harness² "bộ nhớ luôn bật chỉ cho sự thật ngắn đúng với MỌI việc, thêm thì bớt; không lưu sự việc một vụ".

**Lỗ hổng**: chưa có dữ liệu vì các phòng chưa chạy việc thật qua agent.

**Giải pháp cho Joyce**: không ép điền. Cho dữ liệu chảy từ việc thật: khi Sổ Shop, CRM, Hoa hồng chạy hằng ngày, mỗi lần chủ SỬA kết quả của agent là một bằng chứng; đó là nguồn cho `JOYCE_LESSON` và cho Tầng C. Bộ nhớ phòng chỉ nhận quy tắc chung (ví dụ "khách H2O hay đặt cọc 10% qua chuyển khoản"), sự việc từng khách thì vào CRM.

**Đo**: số bài học agent được chủ duyệt mỗi tháng.

### B4. Hướng dẫn công cụ (c4)

**Hiện trạng**: mô tả tool viết một lần (ví dụ mô tả `joyce_shop` dặn hỏi lại khi thiếu số tiền).

**Nguyên tắc**: Harness² c4 là văn xuôi hướng dẫn dùng bộ công cụ, sửa được riêng.

**Giải pháp cho Joyce**: mục "Công cụ" trong `Joyce/noi-quy.md`. Ví dụ Sales Váy Cưới: "Trước khi hứa ngày cho khách, gọi `joyce_shop op=do tu_khoa=<mã váy>` để xem lịch và ngày giặt. Thuê bị chặn thì đọc ngày sẵn sàng trong câu báo, đề xuất ngày đó cho khách".

**Đo**: số lần thuê đồ bị chặn trùng lịch mà agent vẫn báo khách là được.

### B5. Agent con (c5)

**Hiện trạng**: Team runner (trưởng nhóm giao việc bằng khối `JOYCE_TEAM`), Kanban có `deps`, workflow gọi agent phòng khác bằng `Ten Brain|slug`, engine CLI có `Task`. Đường khám phá chỉ đọc nhiều vòng (`readonly_orchestrator.py`) và replan có kỷ luật quyền (`agent_runtime.py`) đã viết nhưng đang 0%.

**Nguyên tắc**: bài giảng ba kiểu phụ bếp: khám phá (chỉ xem), thực hiện, kiểm tra; phụ bếp có phiên riêng, dụng cụ giới hạn, trả về kết quả cần thiết. Harness² chỉ cho agent con khi bề mặt cho phép (`allow_subagents`), mỗi agent con khai `mode: subagent`.

**Lỗ hổng**: không khai báo kiểu; kết quả bước trước truyền nguyên văn qua `{{prev}}`.

**Giải pháp cho Joyce**: trường `kind: explore | execute | verify` trong frontmatter (B9). `explore` tự động chỉ đọc; `verify` không được ghi gì ngoài kết luận. Bước workflow thêm trường `tra_ve:` mô tả khuôn kết quả cần thiết (ví dụ "mã hợp đồng, số tiền, trạng thái"), bước sau chỉ nhận phần đó.

**Đo**: kích thước trung bình `{{prev}}` giữa các bước.

### B6. Skill (c6)

**Hiện trạng**: sáu skill hệ thống ở mọi brain, tự cập nhật; skill nghiệp vụ mẫu `h2o-studio-ketoan-chi-kiem-soat` (1.326 byte) có Vai trò, Kích hoạt, Quy trình, Đầu ra, Guardrail.

**Nguyên tắc**: Harness² "skill là nhà mặc định cho kiến thức nghề có dấu hiệu kích hoạt", và nêu dấu hiệu đó trong phần luôn bật để agent biết gọi.

**Lỗ hổng**: phần lớn phòng chỉ có một skill nghiệp vụ, skill ngắn, chưa có ví dụ vào ra và mục bẫy thường gặp.

**Giải pháp cho Joyce**: mỗi phòng pilot thêm 2 đến 3 skill gắn đúng việc hằng ngày, có ví dụ vào ra và mục "Bẫy" (ghi từ lần chủ sửa thật). Ví dụ:
- Phòng Thu: "thu-coc-theo-lich" (đọc lịch cọc của hợp đồng, nhắc bước tiếp).
- Đối Soát: "doi-soat-hop-dong-hoan-thanh" (đã có ý trong `giao_bao_cao` của Sổ Shop).
- Nhân Sự Vận Hành: "chia-viec-tinh-hoa-hong".

**Đo**: số lần skill được gọi (`skill-usage.json` đã có).

### B7. Script kiểm tra cố định (c7)

**Hiện trạng**: `Brain Default/Joyce/scripts/h2o-bao-cao.py` là script duy nhất.

**Nguyên tắc**: Harness² "lặp lại máy móc thì dùng `scripts/<tên>.py` có đầu vào, đầu ra và cách báo lỗi rõ"; không tự động hóa phán đoán nghề. Rất khớp luật "vận hành không tốn quota".

**Giải pháp cho Joyce**: bộ script kiểm Sổ Shop dùng chung, đặt ở plugin hệ thống để mọi phòng gọi được (không chép vào brain):
- `kiem_so`: tổng thu trừ tổng chi bằng lãi gộp theo kỳ; mỗi phiếu thu cọc khớp lịch cọc của bảng giá.
- `kiem_luong`: lương bằng lương cơ bản cộng hoa hồng việc cộng hoa hồng phần trăm, không ai bị tính cả hai ở cùng hợp đồng.
- `kiem_thue_do`: không phiếu nào chồng lịch kể cả ngày giặt.
Đây cũng là nội dung của `post_check` (B10).

**Đo**: số lỗi script bắt được mỗi tuần.

### B8. Plugin và hook của phòng (c8)

**Hiện trạng**: không phòng nào có. Plugin trong brain chạy được khi chủ bật cờ người dùng.

**Giải pháp cho Joyce**: ưu tiên hook hệ thống (A6). Hook riêng phòng chỉ khi luật thật sự riêng, ví dụ CSKH: chặn agent gửi tin cho khách ngoài giờ 8 đến 21 giờ.

### B9. Phạm vi agent

**Hiện trạng**: frontmatter có `name, slug, role, group, skills, model, model_provider`. Phạm vi công cụ chỉ ở bước workflow (`tools:`) hoặc việc Kanban.

**Nguyên tắc**: bài giảng "mỗi agent có phạm vi riêng: phiên riêng, lời dặn tập trung, công cụ bị giới hạn".

**Giải pháp cho Joyce**: thêm các trường tùy chọn, thiếu thì giữ hành vi cũ:

```yaml
kind: execute            # explore | execute | verify
tools: [joyce_shop, joyce_read_file]   # danh sách cho phép, rỗng = như cũ
mode: auto               # trần quyền, không bao giờ cao hơn mức của phiên
max_rounds: 12
max_minutes: 10
verify: giam-sat-so      # agent hoặc script kiểm sau việc
```

Thực thi bằng đúng cơ chế đã có của việc nền (`allowed_tools`, `disallowed_tools`, `can_use_tool`), không viết bộ khóa thứ hai. Bất biến: `mode` của agent chỉ được hạ, không được nâng mức của phiên.

Ví dụ Phòng Chi: `kind: execute`, `tools: [joyce_shop, joyce_read_file]`, `mode: auto`, `verify: kiem_so`. Agent này không thể gửi Zalo hay ghi file ngoài brain dù model muốn.

**Đo**: số agent có phạm vi; số lời gọi bị chặn vì ngoài phạm vi.

### B10. Cách kiểm theo loại việc

**Hiện trạng**
- Workflow: `verify_agent` và `max_retries`. Kết luận dạng `{"pass", "reason", "fixes"}`, không đọc được là CHƯA ĐẠT, hết lượt thử thì bước hỏng và quy trình dừng (`main.py::_workflow_verdict`, `_verify_failed_message`). Dùng ở 5 trên 239 workflow (năm quy trình bàn giao H2O).
- Factory: `post_check` (lệnh do chủ khai, không bao giờ lấy từ output model, fail thì mở việc `[CI fix]`, tối đa 3 vòng), `watch_spec` (file tồn tại, chứa chuỗi, URL sống, kiểm sau 10 phút trong 120 phút, fail mở lại việc một lần), `Joyce/evals/<slug>.json` (chứa, không chứa, có khóa, độ dài tối đa, biểu thức) chạy trên bản nháp đề xuất.
- Sổ Shop tự kiểm bằng code: chống ghi trùng, hạn mức chi, hoa hồng chỉ khi Đã ký, chặn thuê trùng lịch kể cả ngày giặt.

**Nguyên tắc**: bài giảng "mỗi loại việc cần cách kiểm phù hợp": đọc soát lỗi, so kết quả nhìn thấy, tính toán đối chiếu. Harness² "một lần ghi thành công không chứng minh sản phẩm dùng được; mở lại hoặc kiểm máy móc".

**Lỗ hổng**: mới có kiểu "agent khác đọc rồi phán"; hai kiểu còn lại có mảnh (script, watch) nhưng không gắn vào việc nào; chat không có bước kiểm cuối.

**Giải pháp cho Joyce**: bảng chọn cách kiểm theo loại việc của H2O:

| Loại việc | Cách kiểm | Công cụ đã có để dùng |
|---|---|---|
| Ghi sổ tiền, hoa hồng, lương | Tính toán đối chiếu | Script B7 làm `post_check` của việc Kanban phòng Thu, Chi, Đối Soát |
| Báo giá, hợp đồng | So với bảng giá | Script so dòng báo giá với `so_dich_vu` |
| Thuê đồ | Kiểm luật lịch | Đã có trong `shop_so` (chặn trước), thêm `kiem_thue_do` quét định kỳ |
| Nội dung marketing | Đọc soát | `verify_agent` là `giam-dinh-noi-dung` |
| Bàn giao giữa phòng | Đọc soát cộng file tồn tại | `verify_agent` (đã có ở 5 workflow) cộng `watch_spec` |
| Sửa code | Chạy test | `post_check` là lệnh test, tab Code `run_command` |
| Giao diện | So ảnh chụp | Chưa có, để sau |

**Đo**: tỉ lệ việc qua kiểm ngay lần đầu, theo phòng.

## 6. Tầng C: vòng tự cải tiến

### C0. Harness² làm gì, tóm tắt cho Joyce

Harness² giữ nguyên model, chỉ sửa harness, theo hai vòng đệ quy:
- **Vòng trong (mỗi việc)**: Propose, Probe, Compose.
  1. Propose: hai người sửa song song, một lo INV (cách làm), một lo DOM (kiến thức nghề), mỗi người đề xuất bản harness sửa. Đề xuất chỉ ghi phần thay đổi, phần bỏ trống là giữ nguyên.
  2. Probe: CHẠY từng bản đề xuất trên CÙNG việc đó, lấy nhật ký và sản phẩm.
  3. Compose: đọc tương phản hành vi giữa các lần chạy, ghép thành bản harness cuối. Không cần đáp án đúng.
  4. Chọn: các bản cuối được đổi tên ẩn danh, một người chọn đọc nhật ký và sản phẩm rồi chọn bản tốt nhất (có thể giữ bản gốc).
- **Vòng ngoài (qua nhiều việc)**: sau mỗi việc, lưu bản harness được chọn cùng một "kinh nghiệm" gồm dấu hiệu (cue), bài học, bằng chứng, độ tin cậy vào thư viện theo lĩnh vực. Việc sau cùng lĩnh vực đọc thư viện trước khi sửa.
- **Kỷ luật đi kèm**: ngân sách cố định (k bước thì 4k lần chạy và 3k lượt sửa, kiểm khớp sổ); đề xuất sai khuôn được thử lại MỘT lần kèm lý do bị từ chối, rồi giữ bản hiện tại; không để chữ "người chấm", "điểm", "rubric" lọt vào harness (chống học cách lấy lòng người chấm); bằng chứng đưa dạng file đầy đủ, không cắt cho vừa prompt; chấm điểm thật chỉ chạy SAU khi đã chọn xong.
- Kết quả công bố trong README: tăng tới 11,5 điểm trên WorkBuddy-Bench, 4,5 điểm trên JobBench, 11,8 điểm phần trăm trên LAB, với một bước sửa.

### C1. Hiện trạng ở Joyce

| Mảnh Harness² | Joyce có | Trạng thái thật |
|---|---|---|
| Propose có bằng chứng | `ky-su-harness` (mỗi chế hành vi phải trỏ bằng chứng, sửa tối thiểu, đảo ngược được, viết vào `Joyce/proposals/`) | Có ở 61 brain. Cả hệ thống có 2 đề xuất |
| Tách INV và DOM | Chưa | Một người đề xuất lo cả hai |
| Probe | Chưa | Giám định đọc chữ hai bản, không chạy |
| Compose và chọn ẩn danh | `giam-dinh-harness` cộng skill `cham-diem-tuong-phan` (A/B ẩn danh, ba khối prompt dịch từ Harness²) | Có, chưa từng có nhiều bản đã chạy để chọn |
| Áp an toàn | `factory._proposal_apply`: `verdict=win` cộng `risk=low` cộng có bản nháp đầy đủ thì tự áp, có bản sao lưu; file chung nhiều brain thì canary 24 giờ, tín hiệu xấu là việc bị chặn có nhắc slug thì tự lật lại | Bật ở 61 brain |
| Ca thử bản nháp | `factory.eval_for_draft` đọc `Joyce/evals/<slug>.json` | 1 file |
| Thư viện kinh nghiệm | `Joyce/learn-log/` (95 file), `ppc-state.json` (Brain Default: 4 lượt, 2 bài học) | Có nhật ký, chưa có dạng dấu hiệu, bài học, bằng chứng, độ tin cậy |
| Đo | `agent_scoreboard`, `autonomy_stats` | Có, trả qua `GET /work/factory` |

### C2. Lỗ hổng chính

1. **Không có Probe.** Đây là cốt lõi Harness². So hai bản prompt bằng mắt không thấy được hành vi; hai prompt đọc giống nhau có thể làm việc rất khác nhau.
2. **Không có nguyên liệu.** Không ca thử, không `post_check`, bài học agent bằng 0, nên Propose không có bằng chứng để bám.
3. **Thư viện kinh nghiệm là nhật ký phẳng**, phòng sau không lấy lại được "lần trước phòng này đã sửa gì và vì sao".

### C3. Thiết kế vòng C cho Joyce

Giữ đúng hai ràng buộc của chủ: chỉ chạy khi có bằng chứng (không lịch quét), và tốn ít quota.

**Kích hoạt** (một trong các tín hiệu, đếm bằng code):
- Chủ sửa tay kết quả của agent 2 lần trong 7 ngày cho cùng loại việc.
- Bước workflow trượt `verify` 2 lần.
- `post_check` hoặc script B7 báo lỗi 2 lần cùng chữ ký.
- Chủ bấm "Cải tiến agent này" trên thẻ agent.

**Một lượt cải tiến** (một bước Harness² với k bằng 1, giới hạn ngân sách):
1. Gom bằng chứng dạng file: nhật ký gốc (không cắt dưới 10.000 ký tự), kết quả, chỗ chủ sửa, thư viện kinh nghiệm của phòng.
2. Propose hai bản: INV (cách làm: thứ tự tool, điều kiện xong, thêm script hay hook) và DOM (quy tắc nghề kiểm được của phòng). Mỗi bản chỉ ghi phần đổi.
3. Kiểm khuôn bằng code (frontmatter, trần phần luôn bật, khóa mục hệ thống, không chứa chữ "người chấm"); sai thì thử lại một lần kèm lý do, rồi bỏ.
4. Probe trong bản sao (A8): chạy bản gốc và hai bản đề xuất trên 3 đến 5 ca thử của phòng (`Joyce/evals/<slug>.json` mở rộng thêm loại ca "chạy việc mẫu"). Mỗi lần chạy là một việc nền thật trong sandbox, có trần tiền.
5. Compose một bản từ tương phản, rồi chọn ẩn danh giữa bản gốc và bản ghép bằng `cham-diem-tuong-phan`.
6. Áp theo luật đã có của factory: rủi ro thấp và thắng thì tự áp có sao lưu; còn lại chờ chủ. File chung nhiều brain thì canary 24 giờ.
7. Ghi kinh nghiệm (C4).

Ngân sách mỗi lượt (k bằng 1): 4 lần chạy (gốc, INV, DOM, ghép) nhân số ca thử, cộng 3 lượt sửa. Đặt trần chi phí mỗi lượt và mỗi tháng theo phòng.

### C4. Thư viện kinh nghiệm theo phòng

Theo `harness2/core/library.py`, mỗi phòng một thư mục `Joyce/kinh-nghiem/`:

```
Joyce/kinh-nghiem/INDEX.md                   danh sách, mỗi dòng có dấu hiệu
Joyce/kinh-nghiem/<ngay>-<slug>/harness/     bản đầy đủ đã được chọn (không phải tóm tắt)
Joyce/kinh-nghiem/<ngay>-<slug>/KINH-NGHIEM.md
    - Dấu hiệu: khi nào bài học này áp dụng
    - Bài học: một câu
    - Bằng chứng: lần chạy nào, kết quả khác nhau ra sao
    - Độ tin cậy: thấp, vừa, cao
```

Chỉ ghi khi đủ cả dấu hiệu, bài học, bằng chứng (đúng điều kiện `has_experience` của Harness²). Ví dụ Phòng Chi: "Dấu hiệu: khoản chi có chữ 'setup' hoặc 'đạo cụ'. Bài học: hỏi gắn hợp đồng nào trước khi ghi. Bằng chứng: 3 phiếu chi tháng 10 không gắn hợp đồng làm lãi gộp HD0001 sai. Độ tin cậy: vừa".

### C5. Bác sĩ harness: tìm cái thiếu trước khi đổi model

Bài giảng "tìm phần đang thiếu trước khi đổi model". Joyce đổi não chỉ bằng một cú bấm, nên dễ phản xạ đổi model. Đề xuất: khi một việc thất bại hoặc bị chủ sửa, code gắn nhãn nguyên nhân gần nhất và hiện trên thẻ việc:

| Nhãn | Dấu hiệu đọc được bằng code | Sửa ở đâu |
|---|---|---|
| Thiếu ngữ cảnh | Agent không gọi tool đọc nào trước khi trả lời; trả lời "không có dữ liệu" khi wiki có trang khớp | B2, B3, B6 |
| Thiếu công cụ | Tool bị chặn vì ngoài phạm vi; model nói "không có công cụ" | B9, A4 |
| Thiếu cách làm (INV) | Gọi đúng tool nhưng sai thứ tự; báo xong khi phiếu chưa có mã | B1 phần Cách làm |
| Thiếu kiến thức nghề (DOM) | Script B7 bắt lỗi số; chủ sửa nội dung nghề | B1 phần Điều nghề biết, B6 |
| Thiếu kiểm tra | Lỗi chỉ phát hiện sau khi khách phàn nàn | B10 |
| Model | Đủ cả năm mà vẫn sai trên nhiều ca | Đổi model cho agent đó (đã có trường `model`) |

### C6. Đo hiệu quả

Dùng số đã có: `autonomy_stats` (tỉ lệ việc xong không cần người chạm), `agent_scoreboard` (việc xong, bị chặn, số đề xuất thắng), tỉ lệ qua kiểm (B10), tỉ lệ cache (A3), chi phí theo phòng (A8). Đề xuất một ô "Sức khỏe harness" trên trang Việc gom năm số này theo phòng.

## 7. Kế hoạch theo phòng

### 7.1 Năm phòng pilot

Chọn các phòng đang có việc thật nhờ Sổ Quản lý Shop (bản 1.3.37 và 1.3.38):

| Phòng | Việc thật đang có | Gói harness cần thêm |
|---|---|---|
| Ban Hàng, Sales Hình Ảnh | Lập hợp đồng, báo giá theo bảng giá 46 gói | Nội quy (tra giá trước khi báo), skill báo giá, kiểm báo giá so bảng giá |
| Ban Hàng, Sales Váy Cưới | Cho thuê, giữ chỗ, nhận trả đồ | Hướng dẫn công cụ thuê đồ, `kiem_thue_do` |
| Kế Toán, Thu | Ghi thu, lịch cọc | Phạm vi `joyce_shop` mức auto, skill thu cọc theo lịch, `kiem_so` |
| Kế Toán, Chi | Ghi chi, chi chờ duyệt | Phạm vi, nội quy chứng từ đủ, hook cảnh báo chi không gắn hợp đồng |
| Kế Toán, Đối Soát | Báo cáo hợp đồng hoàn thành | `verify` bằng `kiem_so`, skill đối soát, ca thử |
| Nhân Sự, Vận Hành | Chia việc, hoa hồng, lương | `kiem_luong`, skill chia việc |

### 7.2 Còn lại

- 14 brain khối: thêm một agent điều phối khối (đọc việc các phòng con, không ghi sổ), `kind: explore`.
- 9 agent dùng chung: chuyển thành agent hệ thống như skill hệ thống (một bản ở app, tự cập nhật), bỏ 549 bản sao. Cẩn thận vì `brains/` không có git: làm bằng đường sao lưu của factory, áp canary.
- Đổi tên `ke-toan-vien-dai-tu` cho khỏi nhầm với Phòng Kế Toán (cần chủ đồng ý).

## 8. Ba ví dụ thực tế đi qua khung

### 8.1 "Hợp đồng Tuấn Thủy 0899252392, gói chụp 15 triệu, thu 15tr, chi 4tr setup"

| Bước | Tầng, thành phần | Hôm nay | Khi có khung đầy đủ |
|---|---|---|---|
| Joyce đọc câu, tách sự kiện | A1 vòng lặp, B1 prompt Joyce | Có | Như cũ |
| Gọi `joyce_shop op=ghi` một lần | A4 hub, plugin | Có | Như cũ |
| Tra giá gói, tra khách theo số điện thoại | Lõi Sổ Shop (bậc 5) | Có | Như cũ |
| Giao Sales, Thu, Chi ghi | Định tuyến bằng luật | Có, không tốn model | Như cũ |
| Chi 4 triệu của nhân viên vượt hạn mức chờ duyệt | A5 xin phép | Có | Như cũ |
| Hook kiểm khoản chi đã gắn hợp đồng | A6 | Chưa | `joyce-guard` nối cảnh báo nếu thiếu |
| Kiểm số sau khi ghi | B10, B7 | Chưa | `kiem_so` chạy sau việc: thu 15, chi 4, lãi gộp 11 |
| Ghi sổ sự kiện | A7 | `so_hoat_dong` | Sổ sự kiện chung |
| Chủ sửa kết quả thì thành bằng chứng | C3 | Chưa | Đếm vào kích hoạt cải tiến của phòng tương ứng |

### 8.2 "Cho cô dâu B thuê VAY-CC209 ngày 13/11" khi cô dâu A trả 12/11

- Hôm nay (đã sửa ở 1.3.38): lõi Sổ Shop chặn vì còn 3 ngày giặt, báo ngày sẵn sàng 15/11. Đây là kiểm tra bậc 5, không tốn model, đúng nguyên tắc "cơ chế ngăn lỗi".
- Khung thêm: hướng dẫn công cụ của Sales Váy Cưới (B4) bảo agent đọc ngày sẵn sàng trong câu báo và đề xuất ngày đó cho khách, thay vì chỉ nói "không được". Ca thử của phòng có đúng tình huống này (B10, C3).

### 8.3 "Sửa lỗi nút đăng nhập không bấm được" (việc code)

| Bước bài giảng | Claude Code ở tab Code | Engine API ở tab Code | Engine API chat thường |
|---|---|---|---|
| Nạp hướng dẫn dự án | CLI tự nạp `CLAUDE.md`, `AGENTS.md` | Chỉ prompt Joyce | Chỉ prompt Joyce |
| Tìm code, đọc file | Grep, Read gốc | `joyce_run_command` (grep, rg), `joyce_read_file` | Không thấy code |
| Giao agent con | `Task` | Không | Không |
| Sửa rồi chạy test | Edit, Bash | Ghi cả file, `run_command` pytest ở mức auto | Không chạy được lệnh |
| Kiểm cuối | Model tự báo | Model tự báo | Model tự báo |

Khung thêm: `post_check` là lệnh test cho việc Kanban loại code (CI babysit đã có, chỉ cần khai), `joyce_edit_file` (A4), và luật "việc code giao engine CLI hoặc tab Code" trong prompt Joyce. Kết luận giữ nguyên bản 1: cùng một model, môi trường khác thì kết quả khác; não chính hiện tại của anh (Z.ai glm-4.7-flash, engine API) không hợp việc code.

## 9. Lộ trình

Mỗi giai đoạn có tiêu chí xong đo được. Không giai đoạn nào cần thêm vòng nền theo lịch.

**Giai đoạn 0: vá lõi rẻ (1 bản phát hành)**
1. Tách khối tĩnh và động của system prompt (A3). Xong khi: cache Claude Code qua Joyce trên 90% trong một tuần.
2. Plugin `joyce-guard` bật sẵn với ba luật đầu (A6). Xong khi: có test cho mỗi luật và số lần chặn hiện trên trang.
3. Dọn kết quả tool cũ trong lượt và ghim dữ kiện Sổ Shop khi nén (A2). Xong khi: test lượt 30 vòng giữ payload dưới ngưỡng và test hỏi lại sau nén xanh.

**Giai đoạn 1: gói harness cho 5 phòng pilot (2 đến 3 bản)**
4. Trường phạm vi agent `kind, tools, mode, max_rounds, max_minutes, verify` (B9).
5. `Joyce/noi-quy.md` có trần ký tự, ghép vào khối phòng (B2, B4).
6. Script kiểm `kiem_so`, `kiem_luong`, `kiem_thue_do` và khai làm `post_check` cho việc của các phòng pilot (B7, B10).
7. Chuẩn hóa thân prompt trưởng phòng pilot thành Cách làm và Điều nghề biết (B1), 2 đến 3 skill mỗi phòng (B6).
8. Bộ ca thử `Joyce/evals/` cho mỗi trưởng phòng pilot, 3 đến 5 ca.
Xong khi: mỗi phòng pilot có gói đầy đủ ở mục 2 và tỉ lệ qua kiểm được đo.

**Giai đoạn 2: vòng C có Probe (1 đến 2 bản)**
9. Chế độ chạy thử trong bản sao brain và sổ (A8).
10. Tách người đề xuất INV và DOM, thêm bước Probe chạy ca thử, giữ giám định ẩn danh và luật áp của factory (C3).
11. Thư viện `Joyce/kinh-nghiem/` (C4) và nhãn bác sĩ harness (C5).
12. Ô "Sức khỏe harness" theo phòng (C6).
Xong khi: một lượt cải tiến thật trên phòng pilot chạy đủ bảy bước và có ghi kinh nghiệm.

**Giai đoạn 3: mở rộng và đóng gói**
13. Gói harness cho các phòng còn lại theo thứ tự có việc thật.
14. Chín agent dùng chung thành agent hệ thống, bỏ bản sao.
15. Sổ sự kiện chỉ ghi thêm cho việc có tác dụng ra ngoài (A7); bật workflow đồ thị có checkpoint cho việc nền chạm tiền.
16. Cổng xin phép tùy chọn theo loại thao tác (A5), bộ chuyển hook ngoài (A6), trần chi phí theo phòng (A8).
17. Gom Tầng A thành "lõi harness Joyce" độc lập engine.

## 10. Chưa kiểm tra hoặc cần chủ quyết

- Em chưa chạy bộ test đầy đủ. Nhận định dựa trên đọc code, đọc cấu hình thật và quét file brain. Em chưa chạy thật một lượt PPC hay một workflow có `verify_agent`.
- Em chưa chạy demo của Harness² (`harness2-demo`); chỉ đọc mã nguồn và README. Số tăng điểm là số họ công bố.
- Chưa soi harness của bot khách hàng (Zalo, Telegram, `chatbot_runtime.py`) và vòng lặp bên trong các engine CLI.
- Số cache gom theo ngày từ `usage_index.db`; chưa thử thực nghiệm việc tách khối.
### 10.1 Chủ đã chốt (28/10/2026)

| # | Câu hỏi | Chốt |
|---|---|---|
| 1 | Thứ tự giai đoạn 0 | Theo đề xuất: (1) tách khối tĩnh và động của prompt để lấy lại cache, (2) plugin `joyce-guard` bật sẵn, (3) dọn kết quả tool cũ trong lượt và ghim dữ kiện khi nén |
| 2 | Cổng xin phép | Làm dạng tùy chọn theo loại thao tác, MẶC ĐỊNH TẮT; chủ bật loại nào thì loại đó dừng chờ duyệt |
| 3 | Trần chi phí mỗi lượt cải tiến | Có trần. Con số đề xuất ở 10.2, chờ chủ xác nhận |
| 4 | Gom chín agent dùng chung | Danh sách và vai ở mục 5. Cách gom ở 10.3, chờ chủ duyệt trước khi đụng `brains/` |
| 5 | Tự áp đề xuất rủi ro thấp | GIỮ như hiện tại: `self_improve: true`, `low_risk_auto: true` ở 61 brain. Tiền và ghi ra ngoài vẫn không bao giờ tự qua (luật `low_risk_auto` của factory) |

### 10.2 Đề xuất trần chi phí cho một lượt cải tiến

Một lượt Tầng C với k bằng 1 gồm 4 lần chạy (bản gốc, bản INV, bản DOM, bản ghép) trên mỗi ca thử, cộng 3 lượt sửa và 1 lượt chọn. Với 3 ca thử là khoảng 16 lượt gọi model. Đề xuất (ước lượng, chỉnh lại sau lượt thật đầu tiên):
- Trần mỗi lượt: 1.000.000 token. Chạm trần thì dừng ngay, giữ bản gốc, ghi lý do vào đề xuất.
- Trần mỗi phòng: 2 lượt mỗi tuần.
- Đếm bằng token chứ không bằng tiền, vì phần lớn chạy trên gói thuê bao (Claude Code, Codex) nơi tiền không đo được theo lượt. Nếu chạy bằng model miễn phí (Z.ai glm-4.7-flash) thì vẫn giữ trần token để khỏi chạm giới hạn tần suất.
- Lượt chạy thử luôn trong bản sao (A8), nên không có lượt nào đụng sổ hay brain thật.

### 10.3 Đề xuất cách gom chín agent dùng chung

1. Đặt chín file một lần trong app: `system/agents/` (đã có thư mục, hiện chứa `joyce-core.md`), cập nhật theo bản phát hành giống skill hệ thống.
2. App đọc agent theo thứ tự: brain trước, hệ thống sau. Brain nào đã sửa tay bản của mình thì giữ bản đó (giống quy tắc skill hệ thống bị sửa thì thành của người dùng).
3. Gỡ 549 bản sao bằng đường sao lưu của factory: chuyển vào `Joyce/backup/` của từng brain thay vì xóa, chỉ gỡ bản còn GIỐNG HỆT bản gốc (so mã băm), bản đã bị sửa thì để nguyên.
4. Đổi tên `ke-toan-vien-dai-tu` thành `lap-ke-hoach-dai-tu` (giữ tên cũ làm bí danh để workflow cũ vẫn chạy).
5. `tro-ly-onboarding` giữ ở mọi phòng nhưng cũng đọc từ bản hệ thống, vì nó đã tự đọc wiki của đúng brain đang chạy.

Lợi ích: sửa một lần áp cho 61 brain; trang Agents của mỗi phòng chỉ còn agent nghiệp vụ; Joyce bớt nhầm khi định tuyến việc kế toán.

### 10.4 Còn chờ chủ

- Xác nhận con số trần ở 10.2.
- Duyệt cách gom ở 10.3 (đây là thao tác trên `brains/`, không hoàn tác được nếu làm sai, nên cần chủ đồng ý trước).

## 11. Mục lục kiểm tra Joyce Harness

Ký hiệu: **[Có]** chạy được và đang dùng, **[Có, chưa dùng]** có cơ chế nhưng chưa có dữ liệu hoặc chưa bật, **[Một phần]**, **[Chưa]**.

**Tầng A: lõi chạy**
- A1 Vòng lặp
  - [Có] Trần 30 vòng, chỉnh bằng biến môi trường
  - [Có] Phanh lặp `_LapGuard` (nhắc lần 3, dừng lần 5)
  - [Có] Thử lại lỗi tạm thời có chờ
  - [Có] Chat sống qua F5, gõ thêm giữa chừng
  - [Có] Trần thời gian việc nền, chuỗi dự phòng engine
  - [Chưa] Trần vòng và thời gian theo agent
- A2 Ngữ cảnh
  - [Có] Nén tóm tắt giữ 12 tin, nén đồng bộ khi đuôi dài
  - [Có] Cắt kết quả tool có dòng báo
  - [Có] Adaptive Runtime: capsule, nạp tool lười, bộ nhớ có nguồn, skill lười
  - [Chưa] Dọn kết quả cũ trong lượt
  - [Chưa] Ghim dữ kiện không được mất khi nén
- A3 Lắp prompt và cache
  - [Có] Xếp lớp tĩnh trước, động sau
  - [Có] Đánh dấu cache Anthropic, đo tỉ lệ cache
  - [Chưa] Tách khối tĩnh và động để cache trúng
- A4 Hub công cụ
  - [Có] Một cửa ba nguồn cho mọi engine
  - [Có] Registry đủ tên, quyền, hàm, mô tả
  - [Có] 24 plugin đi kèm
  - [Một phần] Chạy lệnh có rào (chỉ ở tab Code)
  - [Chưa] Sửa từng đoạn file cho engine API
- A5 Quyền
  - [Có] Ba mức quyền, kiểm từng lời gọi theo tham số
  - [Có] Phạm vi nhân viên, bot khách, tool chỉ của chủ
  - [Có] Duyệt chi vượt hạn mức (Sổ Shop)
  - [Một phần] Duyệt ở Kanban (sau khi chạy)
  - [Có, chưa dùng] Ghi có mã xác nhận (đường thích ứng 0%)
  - [Chưa] Cổng xin phép chung theo loại thao tác
- A6 Hook
  - [Có] `pre_tool_call` chặn và sửa đầu vào, `post_tool_call` quan sát, biết người nói
  - [Có] `chatbot_turn_context`
  - [Chưa] Hook bảo vệ bật sẵn
  - [Chưa] Hook bằng lệnh ngoài (JSON vào, mã thoát ra)
- A7 Nhật ký và khôi phục
  - [Có] Nhật ký kiểm toán hub chỉ ghi thêm (khoảng 10 MB)
  - [Có] Kanban lease và reclaim, nhóm chat recover
  - [Có] Bộ nhớ và phiên độc lập engine
  - [Có, chưa dùng] Workflow đồ thị có checkpoint
  - [Chưa] Sổ sự kiện chung chỉ ghi thêm cho việc ra ngoài
- A8 Sandbox và tài nguyên
  - [Có] Sandbox Codex, cổng từng lời gọi của Claude Code việc nền
  - [Có] Thư mục ghim, chặn thoát thư mục, thư mục riêng nhân viên
  - [Có] Lệnh không qua shell, môi trường lọc, chặn cứng
  - [Có] Sổ cái token mỗi phút, học hạn mức, giới hạn tần suất
  - [Chưa] Chạy thử trong bản sao brain và sổ
  - [Chưa] Trần chi phí theo phòng
- A9 Bộ nhớ lõi
  - [Có] Chỉ mục, sự thật, nhật ký, bộ nhớ agent
  - [Có] Xem, sửa, quên, tắt học
  - [Có] Học chỉ đọc, code ghi, quét bí mật, chủ duyệt bài học
  - [Chưa] Đẩy sự việc từng khách sang CRM thay vì bộ nhớ

**Tầng B: bề mặt nghề**
- [Có] B1 Thân prompt agent (600 file; 549 là bản sao)
- [Chưa] B1 Chia Cách làm và Điều nghề biết
- [Chưa] B2 Nội quy phòng có trần ký tự
- [Có, chưa dùng] B3 Bộ nhớ phòng và agent (7 trên 61 brain có dữ liệu, 0 bài học agent)
- [Chưa] B4 Hướng dẫn công cụ theo phòng
- [Một phần] B5 Agent con (gọi được, chưa khai kiểu)
- [Một phần] B6 Skill (6 hệ thống, khoảng 41 nghiệp vụ)
- [Chưa] B7 Script kiểm tra cố định cho phòng
- [Chưa] B8 Hook riêng phòng
- [Chưa] B9 Phạm vi agent
- [Một phần] B10 Cách kiểm theo loại việc (`verify_agent` ở 5 trên 239 workflow, luật Sổ Shop bằng code)
- [Có, chưa dùng] B10 `post_check`, `watch_spec`, ca thử `Joyce/evals`

**Tầng C: vòng cải tiến**
- [Có, chưa dùng] C1 Đề xuất có bằng chứng (`ky-su-harness`, 2 đề xuất trên cả hệ thống)
- [Chưa] C1 Tách INV và DOM
- [Chưa] C2 Probe: chạy thử bản sửa trên ca thật
- [Có, chưa dùng] C3 Chọn ẩn danh (`giam-dinh-harness`, `cham-diem-tuong-phan`)
- [Có] C4 Áp an toàn: sao lưu, canary 24 giờ, tự lật lại
- [Một phần] C5 Thư viện kinh nghiệm (có learn-log, chưa có dạng dấu hiệu, bài học, bằng chứng)
- [Chưa] C5 Bác sĩ harness gắn nhãn nguyên nhân
- [Có, chưa dùng] C6 Bảng điểm agent, tỉ lệ việc tự chạy
- [Chưa] C6 Ô Sức khỏe harness theo phòng

## Phụ lục: cấu hình thật trên máy (28/10/2026)

`server/settings.json`, phần `context_runtime` (mức phân bổ, 10000 là 100%):

| Đường | Mức |
|---|---|
| Chế độ chung | canary |
| Fast path | 100% |
| Conversation state (chỉ engine API) | 100% |
| Memory có nguồn | 100% |
| Lazy skill | 100% |
| Đọc một bước, khám phá nhiều vòng, workflow đồ thị, agent replan, chọn model theo bước, ghi có xác nhận | 0% |

`brains/*/Joyce/factory.json` (giống nhau ở 61 brain): `post_check.code` rỗng, `ci_max_rounds` 3, `watch_delay_min` 10, `watch_minutes` 120, `low_risk_auto` true, `discovery` true, `recipes` true, `self_improve` true, `canary_hours` 24.

## Nhật ký cập nhật

| Ngày | Nội dung |
|---|---|
| 2026-10-28 | Bản 1: chấm chín thành phần theo bài giảng, quét 61 brain, đối chiếu cấu hình thật, đề xuất lộ trình; bổ sung nhật ký, prefix caching, lắp hướng dẫn, xin phép, ví dụ thực tế, sandbox, công thức Agent bằng Model cộng Harness |
| 2026-10-28 | Chủ chốt năm câu ở mục 10.1 (thứ tự giai đoạn 0 theo đề xuất, cổng xin phép tùy chọn mặc định tắt, có trần chi phí, giữ tự áp rủi ro thấp); thêm bảng chín agent dùng chung, đề xuất trần và cách gom |
| 2026-10-28 | Bản 2: viết lại thành khung ba tầng (lõi chạy, bề mặt nghề, vòng cải tiến), mỗi thành phần có hiện trạng, nguyên tắc, lỗ hổng, giải pháp cho H2O, cách đo. Ghép phương pháp Harness² (tám thành phần, INV và DOM, Propose Probe Compose, thư viện kinh nghiệm, ngân sách, luật chọn thành phần rẻ nhất). Sửa nhận định sai của bản 1: `server/factory.py` đã có CI babysit, watch, tự áp có canary và lật lại, bảng điểm agent, ca thử bản nháp; nhưng `post_check` rỗng ở 61 brain và chỉ có 1 bộ ca thử, 2 đề xuất. Thêm mục lục kiểm tra (mục 11) |
