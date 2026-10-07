# Báo cáo tổng — Cổng MCP cho 10 dự án H2O

Chuẩn chung: mỗi app phơi `POST /api/mcp` (JSON-RPC 2.0: `initialize`,
`notifications/initialized`, `ping`, `tools/list`, `tools/call`), xác thực
`Authorization: Bearer <H2O_MCP_TOKEN>`. Joyce: trang **Kết nối** → Thêm MCP →
transport HTTP. Chi tiết từng app nằm ở file `JOYCE-MCP.md` trong repo đó.

Mỗi dự án cũng có thể **tự kết nối**: thêm vào trang Dự án → Joyce tự probe
`<url>/api/mcp` → thấy endpoint là đăng ký vào MCP store (commit `f2ff40f`).
Nếu endpoint trả 401, nhập `mcp_token` lúc thêm hoặc gọi `POST
/h2o-projects/mcp-check` sau.

## Bảng tổng

| # | Dự án | Repo | App deploy | Stack | Cổng MCP | Tools | Env cần | Trạng thái |
|---|-------|------|------------|-------|----------|-------|---------|-----------|
| 1 | H2O Legacy | `E:\CLAUDECODE\H2OLEGACY` | `h2o-legacy-app/` → h2-o-legacy.vercel.app | Vite SPA + Supabase | `supabase/functions/h2o-mcp/index.ts` → `/functions/v1/h2o-mcp` | `legacy_health`, `legacy_report`, `legacy_list_cases`, `legacy_case_detail`, `legacy_list_worklogs` | `H2O_MCP_TOKEN` (supabase secrets) | ✅ Viết xong — cần `supabase functions deploy` |
| 2 | H2O Video Edit | `E:\CLAUDECODE\H2O-VIDEO-EDIT` | `cloud-uploader/` → h2-ovideoedit-omega.vercel.app | Next.js + R2 JSON store | `app/api/mcp/route.ts` → `/api/mcp` | Đọc: `video_health`, `video_report`, `video_list_batches`, `video_batch_status`, `video_list_scripts`. **Ghi (gated)**: `video_create_script`, `video_edit_script`, `video_approve_script` — đi qua `createScriptCloud/patchScriptCloud`, đánh dấu dirty để PC intake kéo về; PC chỉ render script đã `approved` | `H2O_MCP_TOKEN` (fallback `INTAKE_KEY`) + `H2O_MCP_WRITE=1` nếu mở ghi | ✅ typecheck sạch — commit local, chưa push |
| 3 | H2OBOOK | `E:\CLAUDECODE\H2OBOOK` | `H2OBOOK-UNIFIED-INPUT-4.13.7-PHASE7/` → h2-obook.vercel.app | Next.js + Supabase | `app/api/mcp/route.ts` → `/api/mcp` | `book_health`, `book_report`, `book_list_courses`, `book_list_books`, `book_list_classes` | `H2O_MCP_TOKEN` + Supabase sẵn | ✅ typecheck sạch |
| 4 | Thiệp cưới online | `E:\CLAUDECODE\THI-P-C-I-ONLINE` | root → Vercel | Next.js + Firebase (Firestore REST) | `app/api/mcp/route.ts` → `/api/mcp` | `thi_health`, `thi_report`, `thi_list_templates`, `thi_project_detail` | `H2O_MCP_TOKEN` | ✅ typecheck sạch — đọc public-read collections (rules `read: if true`) |
| 5 | H2O Studio CRM | `E:\CLAUDECODE\H2O-QUAN-TRI-CRM` | root → Vercel `h2o-crm-quan-tri` | Next.js + Drizzle + PG | `src/app/api/mcp/route.ts` → `/api/mcp` | `crm_health`, `crm_report`, `crm_list_bookings`, `crm_list_invoices`, `crm_customer_debt` | `H2O_MCP_TOKEN` | ✅ typecheck sạch — chỉ đọc, aggregate theo chứng từ |
| 6 | H2ODESIGN | `E:\CLAUDECODE\H2ODESIGN` | `admin/` — control plane license | Next.js + Prisma | `admin/app/api/mcp/route.ts` → `/api/mcp` | `design_health`, `design_report`, `design_list_licenses`, `design_list_customers`, `design_list_releases` | `H2O_MCP_TOKEN` | ✅ typecheck sạch |
| 7 | ARTCOLOR | `E:\CLAUDECODE\ARTCOLOR` | `apps/api/` — Fastify license API | Fastify + PG | `apps/api/src/server.ts` → `/v1/mcp` | `art_health`, `art_list_packs`, `art_device_entitlements` | `H2O_MCP_TOKEN` | ✅ typecheck + 10/10 test xanh |
| 8 | H2O Studio Sale Album | `...\H2OSALEALBUM\H2ostudio-sale-album-main` | root → Vercel | Vite + Supabase + api/*.ts | `api/mcp.ts` → `/api/mcp` | Đọc: `studio_health`, `studio_report`, `studio_list_consultations`, `studio_upcoming_shoots`. **Ghi (gated)**: `studio_update_consultation` — chỉ status/notes/follow_up_date | `H2O_MCP_TOKEN` + Supabase sẵn + `H2O_MCP_WRITE=1` nếu mở ghi | ✅ tsc file sạch — commit local, chưa push |
| 9 | ThuyH2O Makeup | `...\H2OSALEALBUM\thuyh2omakeupsale` | `ThuyH2O-Makeup-webapp-main/` | Vite + Supabase + api/*.ts | `api/mcp.ts` → `/api/mcp` | Đọc: `makeup_health`, `makeup_report`, `makeup_list_consultations`, `makeup_upcoming_shoots`. **Ghi (gated)**: `makeup_update_consultation` — chỉ status/notes/follow_up_date | `H2O_MCP_TOKEN` + Supabase sẵn + `H2O_MCP_WRITE=1` nếu mở ghi | ✅ tsc file sạch — commit local, chưa push |
| 10 | ArtDemy (đào tạo) | `...\H2OSALEALBUM\WEBDAOTAOTUANART` | `ArtDemy-main/` | Next.js + Supabase | `app/api/mcp/route.ts` → `/api/mcp` | `edu_health`, `edu_report`, `edu_list_orders`, `edu_list_courses`, `edu_list_leads` | `H2O_MCP_TOKEN` + Supabase sẵn | ✅ typecheck sạch — **schema đã đối chiếu thật** (`order_code`, `full_name`, `sale_price`, status `paid`) |

## Joyce side (đã làm)

- `h2o_projects.py`: `probe_mcp()` + `auto_connect_mcp()` — probe `/api/mcp`,
  `initialize` + `tools/list`, đăng ký vào `mcp_store` (Bearer mã hoá).
- `them()` tự probe sau khi thêm dự án (tắt bằng `auto_mcp=false`).
- `POST /h2o-projects/mcp-check` — probe lại bất cứ lúc nào (`ten`,
  `mcp_token`, `force`).
- Token rỗng → rơi về env `JOYCE_H2O_MCP_TOKEN` (nếu sau này đổi qua
  phương án token chung).
- Không duplicate: cùng URL → dùng lại connection; project đã gắn conn →
  không tạo mới trừ khi `force`.
- Server đã restart nạp code (commit `f2ff40f`).

## Tool GHI (mới thêm, mặc định TẮT)

Ba app có write tool scope hẹp, gate bằng env riêng **`H2O_MCP_WRITE=1`** —
không đặt biến này thì tool bị ẩn khỏi `tools/list` và `tools/call` trả
`-32601`. Bearer token vẫn bắt buộc như thường.

| App | Tool ghi | Phạm vi |
|---|---|---|
| Video Edit | `video_create_script` / `video_edit_script` / `video_approve_script` | Script trong cloud content store (R2), đi qua `createScriptCloud`/`patchScriptCloud`, đánh dấu dirty để PC intake kéo về; approve là bước duyệt trước khi PC render |
| Sale Album | `studio_update_consultation` | Chỉ `status` (new/contacted/registered), `notes` (≤2000 ký tự), `follow_up_date` (YYYY-MM-DD) — không đụng tiền HĐ, không xoá |
| ThuyH2O Makeup | `makeup_update_consultation` | Giống Sale Album |

7 app còn lại chỉ-đọc — ghi vào CRM/H2OBOOK/Legacy/H2ODESIGN/ARTCOLOR cần
phân tích riêng (branch scope, audit log, kỳ kế toán...) trước khi mở.

## Trạng thái deploy (cập nhật mới nhất)

| App | Code | Env | Deploy | Test live |
|---|---|---|---|---|
| **H2O Legacy** | ✅ pushed `main` | ✅ `secrets set` | ✅ Edge Function live | ✅ **initialize + tools/list + legacy_health qua Joyce hub — data thật (staff:4), 401 đúng** |
| **Video Edit** | ✅ pushed | ⛔ Vercel block | ⛔ | ✅ **local next dev**: init + 8 tools (write hiện khi WRITE=1), `video_create_script` tạo script thật `no=76` trong R2 (đã dọn sạch) |
| **ARTCOLOR** | ✅ file sẵn (không phải git repo) | — | self-host docker-compose | ✅ **local Fastify**: init + 3 tools + `art_health` (4 packs) + 401 đúng |
| 7 app Vercel còn lại | ✅ pushed | ⛔ Vercel block | ⛔ | chờ Vercel |

## ⛔ Blocker: 2 tài khoản Vercel

**Team `maxsamuelbldhp-7119s-projects` bị chặn fair-use** — `vercel env` và
mọi deployment trả "Team exceeded fair use limits" / `402
DEPLOYMENT_DISABLED`: 8 project trên account này (crm, thi-p-c-i,
h2odesign-admin, sale-crm, thuyh2omakeupcrm, tuan-art-demy...) chờ mở khoá.

**Team `h2o` (Hobby, account khác — CLI không có quyền) giữ 3 app chính:**

| App | Domain | Trạng thái sau push `main` |
|---|---|---|
| H2O Legacy | h2-o-legacy.vercel.app | SPA — MCP là Supabase Edge Fn, **đã live + nối Joyce** |
| Video Edit | h2-ovideoedit-omega.vercel.app | ✅ **LIVE**: init + 5 read tools, `video_health` trả data thật (78 scripts, 2 batches, 128 library). Auth qua `INTAKE_KEY` fallback — đã nối Joyce (`e14e161eba71`). Muốn write tools: đặt `H2O_MCP_TOKEN` + `H2O_MCP_WRITE=1` rồi đổi header trong Joyce |
| H2OBOOK | h2-obook.vercel.app | ✅ route **đã deploy** (đã vá middleware redirect-login) — trả 503 chờ `H2O_MCP_TOKEN` trên Vercel |

Đặt env trên team `h2o`: Vercel dashboard → project → Settings →
Environment Variables → `H2O_MCP_TOKEN` (giá trị trong
`E:\CLAUDECODE\H2O-MCP-TOKENS.md`) → redeploy.

## Còn lại / lưu ý

1. **H2OBOOK**: commit nằm trên nhánh `qa/full-product-audit-fixes` —
   production deploy cần merge về `main` (hoặc đổi production branch).
2. **Token**: bảng token + URL thật ở `E:\CLAUDECODE\H2O-MCP-TOKENS.md`.
3. **Joyce đã nối Legacy**: connection `53b6dcc94b81` trong mcp_store,
   tools hiện dưới tên `h2o-legacy__*` — engine nào cũng gọi được.
4. **ARTCOLOR**: chạy self-host (docker-compose), endpoint
   `http://<host>:4310/v1/mcp` — khi biết host thật thì đăng ký vào Joyce.
5. **Khi Vercel mở**: thêm từng dự án vào trang Dự án kèm `mcp_token` →
   Joyce tự probe + đăng ký tools.
