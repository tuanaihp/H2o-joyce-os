# Joyce Harness: audit bản final v1.0.0

> Ngày: 2026-10-28. Đối chiếu với code Joyce OS 1.3.38 trên nhánh `claude/crm-v2-final-1-3-35`.
> Đặc tả: [`Joyce-harness.md`](./Joyce-harness.md). Lộ trình: [`Joyce-harness-rollout.md`](./Joyce-harness-rollout.md). Audit hiện trạng ban đầu: [`Joyce-hardness.md`](./Joyce-hardness.md).
> Bộ chuẩn do hai phiên soạn: Codex (GPT-6 Astra) viết đặc tả và lộ trình rồi hết lượt giữa chừng; Claude Code (Opus 5.5) hoàn thiện các file còn thiếu, kiểm lại nhận định trong code và gỡ các chỗ mâu thuẫn. File này ghi lại cả hai phần.

## 1. Bộ chuẩn gồm những file nào

| File | Vai trò | Trạng thái |
|---|---|---|
| [`Joyce-harness.md`](./Joyce-harness.md) | Đặc tả chuẩn v1.0.0, nguồn quy tắc | Xong (Astra) |
| [`Joyce-harness-rollout.md`](./Joyce-harness-rollout.md) | Thứ tự triển khai, tiêu chí xong, cổng quyết định | Xong (Astra), đã chỉnh cho khớp quyết định của chủ |
| [`joyce-harness/contract.schema.json`](./joyce-harness/contract.schema.json) | Schema máy đọc: manifest resolved, task, result, verdict, receipt | Xong (Claude) |
| [`joyce-harness/reference.json`](./joyce-harness/reference.json) | 12 ví dụ đúng (Joyce Manager, Trưởng Phòng Thu, chuyên viên ghi thu, explorer, verifier, agent không tool, một việc ghi thu cọc) và 15 ví dụ sai | Xong (Claude), sinh bằng [`tao_reference.py`](./joyce-harness/tao_reference.py) |
| [`joyce-harness/prompts.md`](./joyce-harness/prompts.md) | Prompt mẫu sáu vai, mỗi vai sáu mục | Xong (Claude) |
| [`joyce-harness/acceptance.md`](./joyce-harness/acceptance.md) | Ma trận nghiệm thu, có cột hiện trạng 1.3.38 | Xong (Claude) |
| [`Joyce-hardness.md`](./Joyce-hardness.md) | Audit hiện trạng ngày 2026-10-28, giữ làm lịch sử | Giữ nguyên số liệu |
| `tests/python/test_joyce_harness_schema.py` | Kiểm schema, ví dụ, liên kết giữa các file, không có ký tự gạch dài | Xong (Claude), xanh |

## 2. Ba lỗi thiết kế của bản draft đã được sửa (Astra)

1. **Thang quyền `max_effect`.** Xếp quyền thành một thang làm người đọc hiểu nhầm "được chi tiền thì cũng được sửa policy". Bản final dùng tập độc lập `allowed_effects` (read, internal_write, business_write, external_write, financial_write, policy_write, destructive), không có thứ bậc ngầm; một operation mang nhiều effect thì phải được cấp đủ cả.
2. **Joyce Manager được giao việc nhưng không có cách cấp quyền cho chuyên viên.** Bản final tách `execution` (tự làm) và `delegation` (giao được cho đúng agent nào, với grant nào). Giao việc ghi sổ không cho manager quyền tự ghi sổ.
3. **Bắt mọi việc đều phải qua verifier.** Làm câu hỏi đơn giản cũng tốn thêm một lượt model, đi ngược luật "vận hành không tốn quota". Bản final kiểm theo rủi ro: hỏi đáp kiểm ngay trong lượt, tính toán kiểm bằng script, ghi nghiệp vụ thì guard trước, receipt và read-back sau; verifier model chỉ khi cần phán đoán.

## 3. Các điểm đã khóa trong bản final

- Joyce Manager tách khỏi Joyce Core; vai executor, explorer, verifier, harness_doctor tách riêng.
- Agent con không tăng quyền; grant con là giao của grant cha, manifest con và ràng buộc của việc.
- `tools: []` nghĩa là không có tool, không phải toàn quyền; thiếu trường mới là kế thừa.
- Quyền xét theo từng operation và tham số, không chỉ theo tên tool.
- Mỗi việc giao có đầu vào có nguồn, tiêu chí kiểm được, cách kiểm, idempotency theo từng hành động và cách khôi phục.
- Có chuẩn lắp cấu hình từ platform xuống task để nhân bản xuống trưởng phòng và chuyên viên.
- Pilot là sáu nhóm, không phải năm (Astra sửa đúng chỗ bản audit cũ ghi năm nhưng liệt kê sáu).
- Tài liệu phân biệt đặc tả mục tiêu với runtime chưa triển khai.

## 4. Nhận định đã xác minh trong code (Claude)

| Nhận định | Kết quả | Bằng chứng |
|---|---|---|
| CLI coi allowlist rỗng là toàn quyền | **Đúng, là lỗ thật** | `claude_sdk_engine.py` kiểm `if self.allowed_tools:` nên `[]` thành `bypassPermissions`. Ghi chú ở `main.py` gần `BOT_KHONG_TOOL` xác nhận và đang tránh bằng một chuỗi giả. Ca B-01 |
| Factory bỏ qua check lạ | **Đúng** | `factory._eval_run` trả `ok=None` cho check không biết, `eval_for_draft` không tính là fail. Ca B-10 |
| Tự áp đề xuất tin chữ do model ghi | **Đúng, là lỗ thật** | `factory.proposal_tick` chỉ cần frontmatter `verdict: win` và `risk: low`, hai trường do agent giám định viết. Ca B-12 |
| Lưu agent giữ khóa frontmatter lạ | **Đúng** | `save_agent` dựng `meta = dict(previous)` rồi chỉ ghi đè các trường của form. Thêm khóa `harness` sẽ không mất khi sửa ở giao diện. Ca S-14 |
| Hook sửa tham số mà không kiểm lại | **Đúng một phần** | Với tool MCP, tham số sau hook đi qua `_guard` nên được phân loại lại; tool lõi và plugin chỉ kiểm theo mức quyền. Ca B-08 |
| `joyce_task` không có gọi agent theo lớp | Đúng | Không có resolver `class:executor`; schema cũng cấm kiểu đó |

## 5. Mâu thuẫn còn lại và cách gỡ trong lần hoàn thiện này

| Chỗ | Mâu thuẫn | Đã xử lý |
|---|---|---|
| Rollout còn chữ `max_effect` | Đặc tả đã bỏ `max_effect` nhưng rollout giai đoạn -1 và 0 vẫn ghi | Đổi sang `allowed_effects` |
| Thứ tự giai đoạn 0 | Chủ đã chốt (28/10): cache trước, rồi `joyce-guard`, rồi dọn ngữ cảnh. Rollout của Astra xếp cache ở P2, sau schema và enforcement | Giữ quyết định của chủ thành giai đoạn 0A. Phần schema và enforcement của Astra thành giai đoạn 0B, làm song song. Hai lỗ thật B-01 và B-12 đưa lên đầu 0B vì là ranh giới quyền. Chủ đã đồng ý cách xếp này (28/10/2026) |
| Trần chi phí một lượt cải tiến | Đặc tả mục 13: 500.000 token, 80 lượt gọi, 20 phút, 2 lượt mỗi target mỗi tuần. Audit cũ đề xuất 1.000.000 token, 2 lượt mỗi phòng mỗi tuần | Chủ chốt 28/10/2026: trần token mỗi lượt cải tiến mặc định 500.000, nâng tới tối đa 1.000.000 khi việc cần (nhắm agent dùng chung nhiều brain, từ 5 ca thử trở lên, hoặc ca có vòng tool dài như đối soát cả tháng); không bao giờ vượt 1.000.000; mức đã chọn và lý do ghi vào file đề xuất; vẫn 2 lượt mỗi target mỗi tuần. |
| Tự áp đề xuất rủi ro thấp | Chủ chốt giữ `self_improve` và `low_risk_auto` bật ở 61 brain. Đặc tả mục 14 cấm tin `risk: low` do model ghi | Không trái nhau nếu sửa B-12: vẫn tự áp, nhưng host tự phân loại diff và không tự áp thay đổi grant, effect, budget, policy, hook. Hiện mới có 2 đề xuất trên cả hệ thống nên rủi ro thực tế thấp, nhưng nên sửa trước khi có đề xuất thật |

## 6. Giới hạn bằng chứng

- Không có route nào của 1.3.38 được chứng nhận tuân thủ v1. Bộ chuẩn là mục tiêu, chưa phải tính năng.
- Schema và ví dụ đã kiểm bằng `jsonschema` 4.26 (Draft 2020-12). Compiler, permission gate v1 và runner eval hành vi chưa tồn tại.
- Chưa chạy ca hành vi nào với model thật. Chưa chạy demo của Harness².
- Số liệu phòng ban và cache lấy từ audit ngày 2026-10-28, sẽ lệch khi dữ liệu đổi.
- 1.3.39 đã vá B-01, B-10, B-12 và xong giai đoạn 0A bằng test không gọi model. Tỷ lệ cache sau khi tách khối tĩnh chưa đo lại trên dữ liệu thật; trần token đã chốt nhưng chưa ép trong code.

## Nhật ký

| Ngày | Nội dung |
|---|---|
| 2026-10-29 | Ghi chú triển khai: audit này là bản của ngày 28/10 và KHÔNG được viết lại theo tiến độ; trạng thái hiện tại ở [bàn giao](./2026-10-29-ban-giao-joyce-harness.md) |
| 2026-10-28 | 1.3.39: ba lỗ thật đã vá, giai đoạn 0A xong, 9 trợ lý dùng chung về một bản gốc, khối Joyce Harness lên trang Sơ đồ |
| 2026-10-28 | Ghi hai quyết định của chủ: cách xếp 0A song song 0B, trần token 500.000 đến 1.000.000 theo mức cần |
| 2026-10-28 | Bản đầu: liệt kê bộ chuẩn, ba lỗi draft đã sửa, các điểm đã khóa, xác minh sáu nhận định trong code, gỡ bốn mâu thuẫn |
