# Joyce Harness Rollout

> Ngày lập: **2026-10-28**
>
> Đặc tả nguồn: [`Joyce-harness.md`](./Joyce-harness.md)
>
> Audit ban đầu: [`Joyce-hardness.md`](./Joyce-hardness.md)
>
> Audit bản final: [`Joyce-harness-final-audit.md`](./Joyce-harness-final-audit.md)

## 1. Nguyên tắc triển khai

- Chuẩn hóa một Joyce Manager trước khi nhân rộng.
- Enforce bằng code trước khi tin vào trường trong prompt hoặc frontmatter.
- Không migration hàng loạt `brains/` khi chưa có backup, dry-run và rollback.
- Mỗi giai đoạn có acceptance test và tiêu chí dừng.
- Không bật Probe nếu chưa có bản sao dữ liệu an toàn.
- Không để thay đổi tối ưu cache che mất việc sửa ranh giới quyền.

## 2. Giai đoạn -1: chốt chuẩn

### Công việc

1. Duyệt `Joyce-harness.md` làm nguồn chuẩn.
2. Chốt tên `Joyce Manager` và ranh giới với `Joyce Core`.
3. Chốt tập `allowed_effects` (đặc tả mục 6.1; không dùng thang `max_effect`).
4. Chốt schema task/result contract.
5. Chốt quy tắc kế thừa và merge.

### Xong khi

- Không còn quyết định mở ảnh hưởng schema hoặc permission semantics.
- Có decision log JH-001 đến JH-010.
- Audit, spec và rollout được tách rõ.

## 3. Giai đoạn 0A: vá lõi (chủ chốt 28/10/2026)

Chủ đã chốt thứ tự này. Ba việc đều nhỏ, đo được trước và sau, không đụng `brains/`.

1. Tách system prompt thành khối tĩnh có dấu cache và khối động (giờ, ngôn ngữ, mức dùng). Xong khi: cache của Claude Code qua Joyce trên 90% trong một tuần (đang 76%).
2. Plugin hệ thống `joyce-guard` bật sẵn: chặn ghi ra ngoài brain và vào `sources/`, chặn gửi tin hàng loạt khi người gọi không phải chủ, nối cảnh báo khi chi lớn chưa gắn hợp đồng. Xong khi: có test cho mỗi luật và số lần chặn đọc được.
3. Dọn kết quả tool cũ trong một lượt dài và ghim dữ kiện Sổ Shop khi nén. Xong khi: test lượt 30 vòng giữ payload dưới ngưỡng và test hỏi lại sau nén xanh.

Giai đoạn 0A và 0B chạy song song (chủ đồng ý cách xếp ngày 28/10/2026). Không việc nào của 0A được làm yếu ranh giới quyền.

**Đã làm ở 1.3.39:**

1. Cache: `engine._system_blocks` cắt system prompt ở tiêu đề `# === BÂY GIỜ ===`; phần tĩnh mang dấu cache, đuôi (giờ, ngôn ngữ, mức dùng) không. Áp cho Anthropic API (chat và vòng tool) và OpenRouter model Claude. Engine Claude Code CLI tự lo cache của nó, chưa đo lại tỷ lệ 90%. Test `test_engine_cache.py` mục 7.
2. `system/plugins/joyce-guard` bật sẵn, hook `pre_tool_call`, ba luật: không ghi đè file đã có trong `sources/` (ghi file mới vẫn được vì skill notes cần) và không ghi `Memory/` viết hoa; người không phải chủ tối đa 3 tin Zalo mỗi 10 phút, việc nền tối đa 30; chi từ 5 triệu phải có `khach` hoặc `hang_muc`. Ghi ra ngoài brain vốn đã bị `_safe_path` của hub chặn. Hook chỉ bọc tool đi qua MCP Hub, không bọc Bash/Write native của CLI. Số lần chặn: chưa đếm riêng, `tool-audit` thấy lời gọi bị chặn qua cờ `denied`. Test `test_joyce_guard.py`.
3. `engine._thu_gon_ket_qua_cu`: tổng kết quả tool trong lượt quá 80.000 ký tự thì thu kết quả cũ còn 700 ký tự đầu kèm lời dặn gọi lại; giữ 4 kết quả mới nhất và mọi kết quả `joyce_shop`. Áp cho cả ba vòng tool API (OpenAI chat, Codex Responses, Anthropic). Phần ghim Sổ Shop khi NÉN hội thoại giữa các lượt chưa làm. Test `test_thu_gon_tool_cu.py`.

## 3B. Giai đoạn 0B: schema và enforcement tối thiểu

Hai lỗ thật đã xác minh trong code, làm TRƯỚC các việc còn lại của 0B (xem [ma trận nghiệm thu](./joyce-harness/acceptance.md)):

- B-01: allowlist rỗng ở `claude_sdk_engine` thành `bypassPermissions`. Sửa: phân biệt "chưa khai" với "khai rỗng"; khai rỗng là không tool, có test hồi quy.
- B-12: `factory.proposal_tick` tin `risk: low` do model ghi. Sửa: host tự phân loại diff; đổi grant, effect, delegate, budget, policy, hook thì không tự áp. Vẫn giữ `self_improve` và `low_risk_auto` bật theo quyết định của chủ.

Cả ba lỗ (B-01, B-10, B-12) đã vá ở 1.3.39, xem cột hiện trạng của ma trận nghiệm thu. Công việc 4 bên dưới (`tools: []` là không tool) xong cùng B-01; các việc còn lại của 0B chưa làm.

### Công việc

1. Viết schema `joyce-agent-v1`.
2. Viết validator độc lập, không gọi model.
3. Thêm adapter đọc frontmatter cũ thành manifest tương thích.
4. Thực thi `tools: []` là không có tool.
5. Thực thi `allowed_effects`, budget và delegate depth.
6. Thêm revision hash sau khi merge.

### Test bắt buộc

- Manifest hợp lệ được compile ổn định.
- Manifest lỗi fail-closed.
- Agent con không tăng quyền.
- Tool rỗng không chạy được tool.
- Chu trình kế thừa bị từ chối.
- Save agent qua UI không làm mất trường manifest mới.

### Xong khi

- Runtime trả được manifest hiệu lực và revision của một agent.
- Mọi trường quyền trong golden Joyce Manager được enforce hoặc được đánh dấu rõ là chưa hỗ trợ.

## 4. Giai đoạn 1: Golden Joyce Manager

### Công việc

1. Tạo `system/agents/joyce-manager.md` hoặc profile tương đương.
2. Giữ `joyce-core.md` làm trợ lý hệ thống, không nhập hai vai thành một.
3. Tạo ba profile con: explorer, executor, verifier.
4. Tạo task/result contract validator.
5. Ghi các sự kiện quản trị tối thiểu theo `trace_id`.

### Bộ eval đầu tiên

- Joyce trả lời trực tiếp một câu hỏi đủ dữ liệu.
- Joyce gọi explorer khi thiếu bằng chứng.
- Joyce giao executor khi có việc chuyên môn.
- Joyce gọi verifier trước khi đóng việc.
- Joyce dừng chờ chủ khi thiếu quyết định.
- Joyce xử lý agent con trả `partial`.
- Joyce từ chối delegate hoặc tool ngoài quyền.

### Xong khi

- Một workflow quản trị chạy đủ từ `RECEIVED` đến `COMPLETED`.
- Kết quả có task contract, result contract và verdict.
- Không có lời gọi vượt quyền lọt qua.

## 5. Giai đoạn 2: một lát cắt nghiệp vụ end-to-end

Chọn một luồng có dữ liệu thật, cách kiểm rõ và rollback được. Đề xuất đầu tiên là Kế Toán Thu hoặc Đối Soát.

### Thành phần

- Một department manager.
- Một explorer chỉ đọc.
- Một executor ghi nghiệp vụ trong phạm vi.
- Một script kiểm số.
- Một verifier đọc verdict script và artifact.
- Năm đến tám eval có fixture.

### Xong khi

- Qua ít nhất một tuần chạy có theo dõi.
- First-pass verification, rework và human touch rate được đo.
- Có một lần rollback thử thành công trên bản sao.

## 6. Giai đoạn 3: sáu phòng pilot

Audit ban đầu liệt kê sáu nhóm pilot, không phải năm:

1. Sales Hình Ảnh.
2. Sales Váy Cưới.
3. Kế Toán Thu.
4. Kế Toán Chi.
5. Kế Toán Đối Soát.
6. Nhân Sự Vận Hành.

Mỗi phòng cần:

- Department profile.
- Nội quy ngắn và nguồn chuẩn.
- Trưởng phòng theo `department_manager`.
- Hai đến ba executor nghiệp vụ thật sự cần.
- Explorer và verifier dùng chung khi phù hợp.
- Post-check cho hành động nghiệp vụ.
- Bộ eval và baseline.

### Xong khi

- Mỗi phòng có manifest hiệu lực và revision.
- Mọi business write có guard hoặc post-check.
- Không còn agent báo completed khi verification chưa pass.
- Chỉ số được xem theo từng phòng, không chỉ toàn hệ thống.

## 7. Giai đoạn 4: Probe và tự cải tiến

### Điều kiện vào

- Có sandbox sao chép brain và dữ liệu liên quan.
- Có baseline eval đủ rộng.
- Có budget ledger.
- Có canary và rollback đã được thử.

### Công việc

1. Tách Propose INV và DOM.
2. Probe bản gốc, INV, DOM và bản compose trên cùng ca.
3. Kiểm tool trace, side effect, contract và chi phí.
4. Chọn ẩn danh, có thể giữ bản gốc.
5. Ghi kinh nghiệm theo phòng.

### Xong khi

- Một lượt cải tiến thật chạy đủ vòng nhưng không chạm production trong Probe.
- Canary có health signal đọc được.
- Rollback tự động hoặc một thao tác đã được kiểm thử.

## 8. Giai đoạn 5: mở rộng toàn hệ thống

### Công việc

1. Đưa agent dùng chung thật sự vào `system/agents/`.
2. Dùng content hash để nhận biết bản brain đã sửa tay.
3. Dry-run migration toàn bộ brain.
4. Backup bản đầy đủ trước khi thay đổi.
5. Mở rộng theo thứ tự phòng có việc thật, không theo số lượng file.

### Không làm

- Không xóa 549 bản sao chỉ dựa vào tên file.
- Không coi nội dung gần giống là giống hệt.
- Không ghi đè agent đã được chủ sửa.
- Không bật self-improve cho agent chưa có eval.

## 9. Thứ tự ưu tiên kỹ thuật

| Ưu tiên | Hạng mục | Lý do |
|---|---|---|
| P0 | `tools: []` fail-closed (B-01) | Ranh giới quyền, lỗ thật trong Claude SDK |
| P0 | Tự áp không tin `risk` do model ghi (B-12) | Ranh giới quyền của Tầng C |
| P0 | Schema, validator, inheritance | Nền để nhân bản |
| P0 | Task/result contract | Nền để quản trị và kiểm chứng |
| P0 | Joyce Manager lifecycle | Mục tiêu chính của harness |
| P1 | Verifier registry và post-check | Chống báo xong sớm |
| P1 | Golden eval suite | Có baseline trước khi nhân |
| P1 | Trace và management metrics | Biết hệ thống có tốt lên không |
| P0 (0A) | Prefix cache và dọn context | Chủ chốt làm trước trong giai đoạn 0A; không đổi ranh giới quyền |
| P2 | Probe và kinh nghiệm | Chỉ làm khi sandbox và baseline sẵn sàng |
| P3 | UI sức khỏe harness | 1.3.39 đã có khối Joyce Harness trên trang Sơ đồ (ba tầng, đèn theo số thật, thứ chưa làm hiện xám); chỉ số quản trị mục 15 vẫn chờ dữ liệu đo |

## 10. Cổng quyết định

Trước khi đụng dữ liệu `brains/`, cần chốt:

- Schema v1 có được coi là ổn định để migration không.
- Danh sách agent hệ thống nào thật sự dùng chung. Chủ chốt 28/10/2026 và đã làm ở 1.3.39: 9 trợ lý về một bản gốc trong `system/agents/` (`server/system_agents.py`), 549 bản chép trong 61 brain đã xoá sau khi sao lưu.
- Trần token, thời gian và số lần Probe. Chủ chốt 28/10/2026: trần token mỗi lượt cải tiến mặc định 500.000, nâng tới tối đa 1.000.000 khi việc cần (nhắm agent dùng chung nhiều brain, từ 5 ca thử trở lên, hoặc ca có vòng tool dài như đối soát cả tháng); không bao giờ vượt 1.000.000; mức đã chọn và lý do ghi vào file đề xuất; vẫn 2 lượt mỗi target mỗi tuần.
- Health signal nào làm canary rollback.
- Thời gian giữ backup.

Các quyết định trên không ngăn việc xây validator, golden profiles và eval trong code hệ thống.

## 11. Deliverables

- [ ] `Joyce-harness.md` được duyệt.
- [ ] Schema `joyce-agent-v1`.
- [ ] Validator và compiler kế thừa.
- [ ] Golden Joyce Manager.
- [ ] Explorer, executor, verifier profiles.
- [ ] Task/result contract validator.
- [ ] Golden eval suite.
- [ ] Trace và dashboard chỉ số quản trị.
- [ ] Một lát cắt end-to-end.
- [ ] Sáu phòng pilot.
- [ ] Probe sandbox.
- [ ] Migration tool có dry-run, backup và rollback.

## Nhật ký thay đổi

| Ngày | Nội dung |
|---|---|
| 2026-10-28 | 1.3.39: xong giai đoạn 0A (cache, joyce-guard, thu gọn kết quả tool cũ), vá B-01, B-10, B-12, gom 9 trợ lý dùng chung, khối Joyce Harness trên trang Sơ đồ |
| 2026-10-28 | Chủ duyệt cách xếp 0A song song 0B (B-01, B-12 làm đầu 0B) và chốt trần token 500.000 đến 1.000.000 theo mức cần |
| 2026-10-28 | Chỉnh cho khớp quyết định của chủ: thêm giai đoạn 0A (cache, joyce-guard, dọn ngữ cảnh), đổi giai đoạn 0 cũ thành 0B và đưa hai lỗ thật B-01, B-12 lên đầu; bỏ chữ `max_effect` còn sót; ghi trần chi phí chưa chốt số |
| 2026-10-28 | Tạo rollout mới theo thứ tự chuẩn, enforcement, golden manager, lát cắt end-to-end, sáu phòng pilot, Probe rồi mới mở rộng |
