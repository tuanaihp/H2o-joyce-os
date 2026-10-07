# H2O MCP — cổng đọc dữ liệu chung cho mọi webapp H2O

Một file `index.ts` duy nhất. Deploy nó vào project Supabase của webapp nào,
Joyce đọc được **toàn bộ bảng + file R2** của webapp đó qua lệnh chat —
không cần viết thêm code cho từng app.

## Webapp mới — 3 bước (không code)

**Bước 1 — Đưa file vào project**

Copy `index.ts` (file nằm cạnh tài liệu này) vào:

```
<project-webapp>/supabase/functions/h2o-mcp/index.ts
```

**Bước 2 — Deploy + đặt token**

```bash
cd <project-webapp>
supabase functions deploy h2o-mcp --no-verify-jwt
supabase secrets set H2O_MCP_TOKEN=<chuoi-ngau-nhien-it-nhat-24-ky-tu>
```

Tuỳ chọn thêm (không bắt buộc):

```bash
supabase secrets set H2O_APP_NAME=<ten-app>          # ten hien thi, vd h2obook
supabase secrets set H2O_R2_WORKER=<url-worker-r2>   # neu app co R2
supabase secrets set H2O_R2_TOKEN=<token-worker>
supabase secrets set H2O_MCP_DENY=bang1,bang2        # chan them bang nhay cam
supabase secrets set H2O_MCP_ALLOW=bang1,bang2       # neu dat: CHI cho doc cac bang nay
```

**Bước 3 — Cắm vào Joyce (ô nhập trên giao diện, không sửa file)**

Vào Joyce → trang **Kết nối** → **Thêm MCP** → transport **HTTP**:

| Ô | Điền |
|---|---|
| Tên | `h2o-<ten-app>` (vd `h2o-legacy`, `h2o-book`) |
| URL | `https://<project-ref>.supabase.co/functions/v1/h2o-mcp` |
| Header | `Authorization: Bearer <H2O_MCP_TOKEN>` |

Bấm Lưu → Kết nối. Xong — Joyce tự thấy 6 tool `h2o_*` và dùng được ngay.

## Tool Joyce nhận được

| Tool | Dùng | Args |
|---|---|---|
| `h2o_ping` | Check sống: tên app, số bảng, có R2 không | — |
| `h2o_tables` | Liệt kê mọi bảng + cột đọc được | — |
| `h2o_count` | Đếm dòng 1 bảng | `table`, `filters` |
| `h2o_query` | Đọc dòng bất kỳ bảng | `table`, `select`, `filters`, `order`, `limit` (≤200), `offset` |
| `h2o_r2_ls` | Liệt kê file R2 | `prefix` |
| `h2o_r2_url` | Link đọc 1 file R2 (presigned) | `key` |

### Cú pháp filters của `h2o_query` / `h2o_count`

```json
"filters": [{"col": "created_at", "op": "gte", "val": "2026-10-08"}]
```

`op`: `eq` `neq` `gt` `gte` `lt` `lte` `like` `ilike` `in` `is` `cs`.
Nhiều filter = AND. Bảng nào có cột `is_deleted` tự lọc `is_deleted = false`.

Ví dụ Joyce sẽ tự dịch lệnh anh: *"liệt kê concept tạo hôm nay"* →
`h2o_query(table="concept_registry", filters=[{col:"created_at",op:"gte",val:"<hôm nay>"}], order="created_at.desc")`.

## Bảo mật

- Xác thực `Authorization: Bearer <H2O_MCP_TOKEN>` — token riêng, không phải
  Supabase JWT, đặt bằng `supabase secrets` (không bao giờ nằm trong code/git).
- Đọc **toàn bộ** = service-level. Vì vậy mặc định chặn `staff`,
  `staff_sessions`, `profiles`, `id_counters` (PIN/hash). Chỉnh bằng
  `H2O_MCP_DENY`/`H2O_MCP_ALLOW`.
- **Chỉ đọc.** Không có tool ghi/xoá — muốn Joyce ghi vào app phải làm MCP
  riêng có kiểm soát (mẫu tool `crm_*`/`legacy_*` trong các app hiện có).

## App KHÔNG dùng Supabase?

Mẫu này chỉ áp cho app lưu trên Supabase (+ R2). App backend riêng thì vẫn
phải viết route MCP riêng một lần — mẫu: `JOYCE-MCP.md` trong từng project
(H2O-QUAN-TRI-CRM dùng `/api/mcp` Next.js, H2O-VIDEO-EDIT dùng Vercel route).

## Kiểm thử tay

```bash
curl -X POST https://<project-ref>.supabase.co/functions/v1/h2o-mcp \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"h2o_tables","arguments":{}}}'
```

Trả danh sách bảng là thành công. `401` = sai token, `503` = chưa set
`H2O_MCP_TOKEN`.
