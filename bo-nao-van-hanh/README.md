# Bộ não vận hành Joyce (bản đóng gói)

Đây là bản **copy** phần vận hành của brain Joyce, để đưa sang dự án khác mà không mang theo
dữ liệu của dự án này. Không ảnh hưởng tới brain thật trong `brains/`.

## Có gì trong `khung/`

- **Schema** `CLAUDE.md` và `AGENTS.md`: luật làm việc của AI trên brain (làm rõ trước khi
  trả lời, chống bịa, cách chưng cất tri thức).
- **Skill hệ thống** trong `skills/` (và bản phản chiếu `.claude/skills/`): `ingest-source`,
  `query-wiki`, `lint-wiki`, `notes`, `joyce-builder`, `html-to-webcake`.
- **Skill làm việc** (học từ Javis): `lap-ke-hoach` - việc lớn đi qua spec → plan → task, mỗi
  task có bước kiểm.
- **Khung wiki**: `wiki/index.md`, `wiki/log.md`, `wiki/_open-questions.md`,
  `wiki/_session-handoff.md`.
- **Bộ nhớ**: `memory/MEMORY.md` (chỉ mục, rỗng; Joyce tự học dần).
- **Lịch và dashboard**: `00 - Dashboard/`, các thư mục nhật ký ngày/tuần/tháng/tương lai.
- **Thư mục trống có cấu trúc**: `agents/`, `workflows/`, `sources/`, `attachments/`.
- **Hướng dẫn tầng vận hành**: `Joyce/README.md`.

## Không có gì trong gói này (cố ý)

- Dữ liệu dự án: wiki, sources, memory, hội thoại, ảnh, khách hàng.
- `Joyce/index.md` và `.joyce/system-manifest.json`: sinh ra ở nơi cài đặt, đúng với máy đó.
- Khoá, token, cấu hình máy.

## Cách cài vào dự án khác

```
python bo-nao-van-hanh/cai-dat.py "<đường dẫn thư mục brain của dự án>"
```

Script chỉ tạo file còn thiếu, không ghi đè. Sau đó mở thư mục đó trong Joyce để Joyce sinh
chỉ mục và đồng bộ skill hệ thống theo phiên bản app.

## Vì sao bản này là copy chứ không phải bản gốc

Bản gốc của cơ chế (đồng bộ skill, khung brain, schema) vẫn nằm trong mã của Joyce OS
(`server/system_sync.py`, `server/meta_tools.py`, `.claude/skills/`). Bản này chụp lại trạng
thái tại thời điểm đóng gói. Khi Joyce OS cập nhật skill hệ thống, bản đóng gói này không tự
đổi; muốn lấy bản mới thì đóng gói lại.
