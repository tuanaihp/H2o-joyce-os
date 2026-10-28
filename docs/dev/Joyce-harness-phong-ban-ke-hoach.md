# Joyce Harness cho agent phòng ban: kế hoạch ý tưởng toàn hệ thống

> Viết 28/10/2026 theo câu hỏi của chủ: harness của Joyce có áp cho agent các phòng không, agent phòng có thông minh được không, và nhân bản harness ra toàn hệ thống như thế nào.
> Đây là **kế hoạch ý tưởng để chủ duyệt**, chưa phải code. Số liệu đo trực tiếp từ `brains/` ngày 28/10/2026 (chỉ đọc). Chuẩn gốc: [Joyce-harness.md](./Joyce-harness.md), lộ trình: [Joyce-harness-rollout.md](./Joyce-harness-rollout.md).

## 1. Trả lời ngắn

1. **Agent phòng ban đang nhận phần lõi chạy của harness, chưa có harness của riêng phòng.** Lõi (chốt chặn, cache, thu gọn kết quả cũ, ranh giới quyền, phanh vòng lặp) là code của app nên mọi agent đi qua MCP Hub đều được. Phần nghề của phòng (nội quy, phạm vi, cách kiểm, ca thử) thì chưa có.
2. **Agent phòng chạy được, trả lời được, nhưng chưa "thông minh có trách nhiệm".** Nó dựa vào khung prompt chung, wiki và trí nhớ của phòng. Chưa có ai kiểm nó làm đúng hay sai, và chưa có ca thử nào để biết nó tốt lên hay tệ đi.
3. **Không nhân bản bằng cách chép prompt.** Làm một lớp harness nền cho phòng ban, rồi mỗi khối và mỗi phòng chồng thêm lớp riêng của mình. Nâng lớp nền không tự đổi agent đang chạy.
4. **Joyce vẫn là bộ não tổng với harness riêng.** Agent phòng không kế thừa quyền giao việc của Joyce. Phòng chỉ báo lên, Joyce điều phối.

## 2. Hiện trạng đo được

| Điều đo | Kết quả | Ý nghĩa |
|---|---|---|
| Số brain, số agent | 61 brain, 51 agent | 14 brain chưa có agent nào, 45 brain có 1 (trưởng phòng), 2 brain có nhiều hơn |
| Agent dùng chung một khung | 44/51 có đúng 6 mục giống nhau (Bối cảnh, Nhiệm vụ chính, Quy trình, Định dạng đầu ra, Trường hợp khó, Điều cấm) và cùng dòng quy trình đầu tiên | Khác nhau chủ yếu ở tên phòng và vài dòng nhiệm vụ. Phần nghề chưa nằm trong agent |
| Skill gắn cho agent | 46/51 agent có `h2o-y-tuong`; skill nghề cụ thể (kế toán chi, thu công nợ, content plan...) chỉ gắn cho khoảng 3 agent mỗi skill | Trong brain có 46 skill nghề riêng nhưng đa số chưa nối vào agent của phòng |
| Khai tool, khai `allowed_effects` | 0/51 | Quyền đang theo phiên, chưa có phạm vi riêng từng agent |
| Nội quy phòng `Joyce/noi-quy.md` | 0/61 | Chưa có nguồn chuẩn ngắn để agent bám |
| Bộ ca thử `Joyce/evals/` | 1 bộ ở 1 brain | Gần như không đo được chất lượng |
| Model của agent phòng | qwen3:14b 18, sonnet 15, gpt-5.6-sol 10, grok-4.6 6 | Mô hình yếu hơn cần khung chặt hơn, đặc biệt agent ghi sổ hoặc gửi tin |

Lõi chạy đã có từ 1.3.39 và áp cho mọi agent đi qua hub. Hai giới hạn nói thẳng: `joyce-guard` chỉ bọc tool đi qua MCP Hub, không bọc lệnh Bash hoặc ghi file gốc của engine CLI; và phần "ghim Sổ Shop khi nén hội thoại giữa các lượt" chưa làm.

## 3. Kiến trúc: harness nhiều lớp, mỗi lớp một chủ

```text
Lõi chạy (app)            một bản, mọi agent
  Harness Joyce           bộ não tổng: điều phối, giao việc, kiểm, báo chủ
  Harness nền phòng ban   khung chung cho mọi phòng (department-base)
    Harness khối          Bán hàng, Kế toán, Marketing, CSKH, Sản xuất, Nhân sự, Học viện
      Harness phòng       nội quy, việc thật, nguồn chuẩn, cách kiểm, ca thử của một phòng
        Ghi đè agent      tinh chỉnh riêng một agent
```

Khớp với thứ tự lắp cấu hình trong chuẩn mục 5.1 (platform, role profile, organization, department, agent override). Khối là lớp thêm vào giữa vì H2O có nhiều phòng cùng nghề (ba phòng Sales, ba phòng Kế toán), nên viết một lần cho khối rồi phòng chỉ khai phần khác.

### Ranh giới giữa Joyce và phòng

- Joyce Manager có quyền giao việc cho trưởng phòng. Trưởng phòng **không** có quyền giao ngược lên hay giao ngang sang phòng khác; việc ngoài phạm vi thì báo lên Joyce.
- Trưởng phòng là `department_manager`, scope nhỏ hơn. Executor (nếu tách) chỉ có tool và effect đúng một việc.
- Explorer (chỉ đọc) và verifier (kiểm độc lập) dùng chung cho cả hệ thống, mỗi lần gọi là một run tách riêng.
- Quyền không kế thừa theo chiều dọc: harness nền chỉ đặt trần, phòng chỉ được thu hẹp.

### Mỗi harness phòng gồm những gì

1. **Nội quy ngắn** `Joyce/noi-quy.md`: 10 đến 20 dòng luật nghề của phòng. Ví dụ Kế toán Chi: khoản từ 5 triệu phải gắn hợp đồng; chi nhân viên báo thì chờ chủ duyệt.
2. **Việc thật của phòng**: 3 đến 5 việc, mỗi việc có đầu vào, đầu ra, nguồn dữ liệu chuẩn.
3. **Phạm vi**: phòng đọc được dữ liệu nào, ghi được loại gì (`allowed_effects`), tool nào, ngân sách mỗi việc.
4. **Skill nghề đã nối đúng agent**: dùng lại 46 skill nghề sẵn có thay vì viết mới.
5. **Cách kiểm**: ưu tiên script đối chiếu số (thu chi khớp sổ, lịch không trùng), rồi tới verifier đọc kết quả. Việc rủi ro thấp chỉ kiểm bằng luật cố định, không gọi thêm model.
6. **Bộ ca thử**: 5 đến 8 ca lấy từ việc thật gần đây của phòng, có đáp án đúng. Đây là thứ cho phép nói "agent tốt lên hay tệ đi".

## 4. Nhân bản như thế nào để vận hành toàn hệ thống

### Nguyên tắc

- **Chồng lớp, không chép file.** Phòng khai `Joyce/harness.md` tham chiếu lớp nền theo ID và phiên bản đã ghim. Nâng lớp nền không tự đổi phòng đang chạy; chủ duyệt rồi mới chuyển.
- **Làm theo khối, không làm từng phòng thủ công.** 61 brain chia thành khoảng 7 khối. Viết 7 harness khối chuẩn, mỗi phòng chỉ thêm phần riêng (thường 20 đến 40 dòng).
- **Phần quyền luôn do chủ duyệt.** Joyce có thể soạn nháp nội quy, ca thử, skill; mọi thay đổi về quyền, effect, ngân sách, tool thì nằm chờ chủ (đã có sẵn từ 1.3.39).
- **Luật cố định trước, model sau.** Kiểm số, kiểm trùng, kiểm quyền chạy bằng code, không tốn quota. Model chỉ soạn nội dung và phán đoán.

### Công cụ dựng harness phòng (hướng dẫn trưởng phòng một lần)

Một workflow hệ thống dựng harness cho một phòng, chạy trên chính brain của phòng đó:

1. Đọc wiki, trí nhớ, skill, MCP đã nối và 30 ngày việc gần nhất của phòng.
2. Hỏi trưởng phòng 5 đến 7 câu ngắn (việc nào hay làm nhất, sai chỗ nào đắt nhất, ai duyệt, nguồn nào là chuẩn).
3. Soạn nháp: nội quy, danh sách việc, phạm vi quyền đề xuất, nối skill, 5 đến 8 ca thử lấy từ việc thật.
4. Chạy thử các ca trên bản sao, báo kết quả cho chủ.
5. Chủ duyệt phần quyền; phần còn lại vào hoạt động với canary.

Làm một phòng khoảng một buổi làm việc của trưởng phòng. Không đụng `brains/` thật cho tới bước 5, và có sao lưu trước khi ghi.

### Tự cải tiến theo phòng

Vòng cải tiến (Tầng C) đã có sẵn. Mỗi phòng khi có bộ ca thử thì đề xuất sửa prompt chạy thử trên chính ca của phòng, thắng mới áp, có canary. Trần token mỗi lượt cải tiến 500.000, tối đa 1.000.000 như anh đã chốt; **chưa ép trong code**, là việc cần làm trước khi bật cho nhiều phòng.

## 5. Lộ trình đề xuất

| Giai đoạn | Việc | Xong khi |
|---|---|---|
| 0 (xong 1.3.39) | Lõi chạy, 9 trợ lý dùng chung, chốt chặn, vá 3 lỗ quyền, khối Harness trên Sơ đồ | Đã chạy |
| 1 | Nốt 0B: compile `harness.md` thành cấu hình hiệu lực, ép `allowed_effects` và `tools: []`, ép trần token, thêm profile `department-base` và `joyce-manager` | Một agent thử nghiệm chạy đủ vòng và không lọt lời gọi vượt quyền |
| 2 | Một lát cắt end-to-end: Kế toán Thu hoặc Đối Soát (có Sổ Shop, số kiểm bằng script được) | Chạy một tuần, đo được việc xong lần đầu đúng, số lần phải sửa, số lần chủ phải can thiệp |
| 3 | Sáu phòng pilot: Sales Hình Ảnh, Sales Váy Cưới, Kế Toán Thu, Chi, Đối Soát, Nhân Sự Vận Hành | Mỗi phòng có nội quy, việc thật, ca thử và baseline |
| 4 | Nhân ra theo khối bằng công cụ dựng harness; 14 brain chưa có agent được gắn trưởng phòng | Mỗi khối có harness chuẩn; mỗi phòng khai phần riêng |
| 5 | Tự cải tiến theo phòng với trần token đã ép | Có số liệu phòng nào tốt lên, phòng nào bị lật lại |

Thứ tự theo rủi ro: phòng ghi sổ và chi tiền làm trước, vì sai ở đó đắt nhất. Phòng chỉ tư vấn làm sau.

## 6. Những chỗ cần anh quyết

1. **Khối nào là khối đầu tiên** sau pilot. Đề xuất đi theo tiền: Kế toán, rồi Bán hàng, rồi Nhân sự.
2. **Agent chạy model yếu (qwen3:14b, 18 agent) có được ghi sổ và gửi tin không.** Đề xuất: được đọc và soạn; ghi sổ và gửi ra ngoài thì phải qua verifier hoặc chờ chủ duyệt cho tới khi ca thử của phòng đạt.
3. **Ai duyệt phần quyền của từng phòng**: chỉ chủ, hay trưởng phòng được duyệt phần phạm vi nhỏ của mình.
4. **14 brain chưa có agent**: tạo trưởng phòng từ mẫu khối, hay để trống tới khi phòng cần.

## 7. Rủi ro và cách chặn

- **Viết harness quá dài rồi không ai đọc.** Giới hạn nội quy 20 dòng, harness phòng 40 dòng phần riêng; test kiểm độ dài.
- **Harness làm agent chậm và tốn token hơn.** Kiểm theo rủi ro, việc nhẹ không gọi verifier; đo chi phí mỗi việc xong trước và sau.
- **Sửa nền làm vỡ 44 phòng cùng lúc.** Phiên bản ghim và canary theo khối: đổi một khối trước, canh 24 giờ rồi mới nhân ra.
- **Soạn tự động sai nghề.** Ca thử lấy từ việc thật và trưởng phòng duyệt; chưa qua ca thử thì không tự áp.
- **Dữ liệu mẫu lẫn vào dữ liệu thật.** Mọi bước thử chạy trên bản sao trong thư mục tạm, theo quy tắc không dùng thư mục thật để test.

## Nhật ký

| Ngày | Nội dung |
|---|---|
| 2026-10-28 | Bản đầu: đo hiện trạng 61 brain, kiến trúc nhiều lớp (lõi, Joyce, nền phòng ban, khối, phòng, agent), cách nhân bản bằng chồng lớp và công cụ dựng harness, lộ trình 6 giai đoạn, bốn câu cần chủ quyết |
