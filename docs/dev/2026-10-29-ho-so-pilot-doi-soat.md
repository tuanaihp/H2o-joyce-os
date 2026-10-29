# Hồ sơ pilot Đối Soát (chỉ đọc)

> Viết 29/10/2026 theo mục 7 của [kế hoạch phòng ban](./Joyce-harness-phong-ban-ke-hoach.md). **Chưa mở.** File này là thứ anh duyệt hay không duyệt; em không bật gì cho tới khi anh nói.

## 1. Pilot này chứng minh điều gì

Một luồng thật từ đầu đến cuối ở phòng **Kế Toán - Đối Soát và Báo Cáo** (brain `Ke Toan - Doi Soat va Bao Cao`, agent `truong-phong-doi-soat`): đối chiếu dữ liệu theo kỳ, nêu khoản lệch. **Chỉ đọc**: không ghi sổ, không gửi tin, không đụng tiền. Mục tiêu không phải câu trả lời có số đúng một lần, mà là chứng minh cả chuỗi: lượt chạy được ghi, đúng bản cấu hình, có người chấm, có số token thật, và agent bị chặn nếu thử ghi.

## 2. Đã sẵn sàng (đã kiểm bằng test, trong sandbox)

| Thành phần | Trạng thái |
|---|---|
| Ghi lại mọi lượt agent chạy, kèm đúng bản cấu hình | Có (bot, việc giao trợ lý, bước workflow) |
| Anh chấm Đạt hoặc Rớt từng lượt trên trang Sơ đồ | Có |
| Canary chỉ nhân sau 20 lượt anh chấm đạt, một lượt rớt là lật lại | Có |
| Chặn agent đã khai quyền mà gọi tool ngoài quyền (mọi tool của hub, từ 1.3.45) | Có, nhưng chỉ cho agent **đã khai** `allowed_effects`; mỗi lần chặn được ghi vào sổ |
| Rào hoàn thành cho việc tác động ra ngoài | Có (không áp cho Đối Soát vì việc chỉ đọc) |
| Đo token thật theo từng lượt, trần cấu hình được | Có (trần mặc định không chặn) |

## 3. Chưa sẵn sàng, cần làm trước khi mở

1. **Agent Đối Soát chưa khai quyền.** `0` agent trong brain này có `allowed_effects`. Chưa khai thì luật chặn ghi không áp, tức pilot "chỉ đọc" mới là lời hứa chứ chưa phải rào. Việc cần làm: khai `allowed_effects: [read]` cho agent pilot.
2. **Chưa có bộ ca thử cho phòng này** (`Joyce/evals/`). Không có bộ ca thử thì chưa có chuẩn "đúng" tự động; em đề xuất 5 đến 10 ca đối chiếu mẫu với số đã biết trước để làm chuẩn.
3. **Đường vào của pilot.** Từ 1.3.45 khung chat với một trợ lý, việc giao trợ lý và workflow đều vào sổ; chat với Joyce (không chọn trợ lý) cũng vào sổ nhưng không làm bằng chứng canary. Engine CLI native (Claude Code, Codex...) tự gọi tool ngoài hub nên pilot chỉ chạy bằng engine API hoặc qua hub.
4. **Chưa đặt trần token** (`settings.tasks.tran_token_luot`). Em đề xuất 500.000 cho pilot.
5. **Chưa có người chấm tự động.** Mọi lượt cần anh hoặc người anh chỉ định chấm tay trên Sơ đồ; 20 lượt đạt mới đủ ngưỡng canary.

## 4. Đề xuất các bước

1. Khai `allowed_effects: [read]` cho agent Đối Soát; thêm 5 đến 10 ca thử mẫu. (Em làm, anh xem.)
2. Đặt trần token 500.000 cho pilot.
3. Chạy 20 việc đối chiếu thật ở chế độ chỉ đọc, qua Kanban hoặc workflow.
4. Anh chấm từng lượt trên Sơ đồ ("Lượt chờ anh chấm"). Mỗi lượt cần nêu lý do ngắn.
5. Xem số liệu: bao nhiêu lượt đạt, rớt, gián đoạn, tổng token, lượt nào chưa đo được token.
6. Quyết định: mở thêm phòng Thu trong môi trường thử, hoặc dừng.

## 5. Điều kiện dừng ngay

- Một lượt bị chấm Rớt vì **sai số tiền hoặc sai nguồn** (không phải sai diễn đạt): dừng pilot, chưa mở phòng Thu.
- Agent cố gọi tool ghi bị chặn (log hub): dừng và xem vì sao nó thử.
- Tổng token vượt trần: lượt dừng sẵn; kiểm tra có vòng lặp không.
- Lượt chạy gián đoạn nhiều lần: kiểm tra máy trước khi chấm tiếp.

## 6. Anh cần duyệt gì

- [ ] Cho phép em khai quyền chỉ đọc và thêm ca thử cho phòng Đối Soát.
- [ ] Trần token cho pilot (đề xuất 500.000).
- [ ] Ai chấm lượt (anh, hay người anh chỉ định có tài khoản chủ).
- [ ] Mở pilot, hay chờ thêm một đợt sửa nữa.

Nhớ: pilot **chưa** mở phòng Thu hay Chi. Ghi tiền, gửi khách cần hồ sơ riêng theo mục 7.1 của kế hoạch.
