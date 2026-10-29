# Bàn giao Joyce Harness: đã làm gì, chưa làm gì, làm tiếp thế nào

> Viết 29/10/2026 cho **Astra, Fable hoặc bất kỳ LLM nào** nhận việc tiếp. Đây là bản gom DUY NHẤT. Chi tiết nằm ở các tài liệu được trỏ tới; nếu hai chỗ nói khác nhau thì tin **mã và test** hơn tài liệu, rồi sửa tài liệu.
>
> Trạng thái đúng của hệ thống: **"G1 đã gia cố; gói B và một phần G2 đã làm; canary chưa chứng nhận ở quy mô thật; chưa pilot".** Không phải "harness hoàn chỉnh".

## 1. Đọc theo thứ tự này

1. [Joyce-harness.md](./Joyce-harness.md) (chuẩn v1.0.0 của Astra, KHÔNG sửa theo thực tế triển khai; xem mục 6 ở đó)
2. File này
3. [Kế hoạch phòng ban](./Joyce-harness-phong-ban-ke-hoach.md): mục 3.3 (G1), 3.4 (12 tồn đọng G1-01..12), 3.5 (kết quả gói A, B, G2), 3.6 (việc chờ chủ)
4. [Plan giao Sonnet](./2026-10-28-joyce-harness-g1-g2-sonnet-plan.md) (A00..A07, B01..B03; các ô checklist ở đó **chưa tick**, tin bảng ở file này)
5. Bằng chứng: `docs/dev/evidence/2026-10-28-g1/README.md` (log full suite thô, nguyên nhân từng test đỏ, đo khởi động)
6. [Hồ sơ pilot Đối Soát](./2026-10-29-ho-so-pilot-doi-soat.md) (chờ chủ duyệt)

## 2. Trạng thái theo hạng mục

Ký hiệu: **XONG** = có mã + test + chạy trong sandbox; **MỘT PHẦN** = có nhưng thiếu điều kiện nêu rõ; **CHƯA**.

| Hạng mục | Trạng thái | Ở đâu | Còn thiếu |
|---|---|---|---|
| FIX-01 so quyền theo cây YAML (JHA-01) | XONG | `harness_diff.py` | 30 skill lỗi YAML chờ chủ quyết |
| FIX-02 bộ ca thử hỏng thì chặn (JHA-02) | XONG | `factory.eval_load`, `eval_for_draft` | `eval_bat_buoc` mặc định tắt; 43/44 phòng chưa có bộ ca thử; eval mới là CHUỖI, chưa là hành vi |
| FIX-03 chốt ghi file (JHA-03) | MỘT PHẦN | `file_policy.py`, `mcp_hub._write` | chỉ tool `joyce_write_file`; CLI native, shell, plugin, route HTTP chưa |
| FIX-04/05 canary từng đích, bằng chứng | XONG | `factory.py` | xem B02 |
| A01 cổng host chặn tự áp | XONG | `factory._proposal_apply` | chỉ thay đổi `display_only` tự áp |
| A02 baseline chung và override (D2) | XONG | `factory._nhan_mot_dich` | chưa chạy trên brain thật |
| A03 phân loại thay đổi | XONG | `harness_diff.classify` | khoá lạ bị coi là chưa biết (an toàn nhưng gây ma sát) |
| A04 cổng eval 4 trạng thái | XONG | `factory.eval_for_draft` | |
| A05 writer chung, khoá liên tiến trình, phục hồi sau crash | XONG | `deploy_writer.py` | nhánh `fcntl` (Linux/macOS) chưa chạy thật ở đâu |
| A06 quản trị cho chủ | XONG | `factory_admin.py`, route cuối `main.py`, Sơ đồ | |
| A07 nghiệm thu, đo khởi động | MỘT PHẦN | `evidence/.../44-khoi-dong-ket-luan.md` | gate p95 < 5,0 CHƯA đạt |
| B01 sổ lượt chạy do host ghi | MỘT PHẦN | `run_ledger.py` + 5 cửa (bot, việc, workflow, khung chat của chủ `main._so_mo_luot_chat`, Telegram/CLI `main._tg_answer`) | engine CLI native tự gọi tool của nó vẫn ngoài sổ; bot Zalo đi `_tg_answer(bot=...)` không qua chatbot_runtime nên chưa ghi; chưa `parent_run_id`; `grant_hash`, `effective_config_hash` đang băm rỗng |
| B02 canary dựa trên lượt đã chấm | MỘT PHẦN | `factory._canary_evidence`, `factory_admin.cham_luot` | không có bộ chấm tự động; chưa nhóm ca bắt buộc theo phòng; chưa theo dõi lượt chạy TẠI đích sau nhân; ngưỡng 20/24h/14 ngày chưa hiệu chỉnh |
| B03 chứng nhận đường ghi | MỘT PHẦN | `route_cert.py` | KHÔNG đường nào đạt `chung_nhan`; mới có bản kê và test chặn trượt |
| G2 #2 quyết định quyền chung | MỘT PHẦN | `run_context.py`, `mcp_hub._boc_quyen` và `hub_effect` (MỌI tool của hub, hỏi lúc GỌI), `mcp_hub._write` | chỉ agent ĐÃ khai `allowed_effects` (0/13 ở brain mẫu); hub phân loại effect thô (read, write, danger) rồi ánh xạ thận trọng sang external_write; chưa grant theo tham số; CLI native vẫn ngoài hub |
| G2 #3 ngân sách token | MỘT PHẦN | `run_ledger.cong_token/ghi_usage`, hook ở `aux_engine` và `main._stream_chain` | đo được ở đường có sự kiện `usage`; trần theo LƯỢT, chưa theo CÂY (manager, con, retry, verifier, fallback); chưa gắn "lượt cải tiến" để áp mức 500k |
| G2 #4 cổng hoàn thành | MỘT PHẦN | `tasks.TasksFeature._rao_hoan_thanh` | chỉ capability `external-write` và chỉ đường Kanban; chưa đòi receipt nghiệp vụ |
| G2 #5 sổ đăng ký triển khai | MỘT PHẦN | đèn "Bản đang chạy", `run_ledger.ban_gan_nhat` | là sổ ĐỌC, không phải khóa phiên bản (JHA-12 chưa) |
| G2 #1 compiler (JHA-10) | **CHƯA** | | |
| JHA-06 guard bắt buộc mọi route | **CHƯA** | | `route_cert.py` liệt kê các đường |
| JHA-07 ghim Sổ Shop theo record/receipt | **CHƯA** | | |
| JHA-08 đèn Sơ đồ theo bằng chứng | MỘT PHẦN | `harness_map.py` (20 đèn) | đèn cũ (cache, guard, trim, perm) vẫn gán `ok` theo cấu hình, chưa theo đo |
| JHA-09 ACL dispatch cho shared agent | **CHƯA** | | |
| JHA-12 ghim revision cho shared agent | **CHƯA** | | |
| G3 pilot Đối Soát (chủ DUYỆT 29/10) | MỘT PHẦN | agent `doi-soat-pilot` + bộ ca thử đã tạo trong brain thật (bản sao ở `tests/fixtures/g3/doi-soat-pilot.*`), `docs/dev/2026-10-29-pilot-doi-soat-20-viec.md` | 20 việc CHƯA chạy (chủ chạy và chấm); sổ Quản lý Shop hiện RỖNG nên chỉ đối chiếu được file trong `sources/`; agent gốc dùng Codex nên chưa có rào (xem mục 6c) |
| G3 nền móng (sandbox) | MỘT PHẦN | `server/doi_soat_kiem.py` (bộ kiểm độc lập, thuần, tất định), `tests/fixtures/g3/doi_soat_mau.json`, `test_g3_doi_soat_sandbox.py` | CHƯA chạy trên brain thật: chưa khai `allowed_effects` cho agent thật, chưa có bộ ca thử trong `Joyce/evals/` của phòng, chưa có Phòng Thu thử; chờ chủ duyệt hồ sơ pilot |
| Rollout giai đoạn 1+, G4 sáu phòng, G5, G6 | **CHƯA** | | |

## 3. Bản đồ mã (file mới hoặc đổi nhiều)

- Quyết định tự áp: `server/factory.py` (`_proposal_apply`, `proposal_tick`, `canary_tick`, `_canary_evidence`, `telemetry_ready`), `server/harness_diff.py`
- Ghi file triển khai: `server/deploy_writer.py` (khoá, nhật ký `Joyce/proposals/.deploy`, đối soát crash)
- Quản trị: `server/factory_admin.py`; route `/work/factory`, `/work/factory/diff`, `/work/factory/action`, `/work/factory/grade` (chỉ chủ)
- Sổ lượt chạy: `server/run_ledger.py` (SQLite `run_ledger.sqlite3`, gitignored); ngữ cảnh: `server/run_context.py`; hook ở `chatbot_runtime._answer`, `tasks._claim_and_spawn/_worker_done`, `main._run_workflow_step`
- Chứng nhận: `server/route_cert.py`; Sơ đồ: `server/harness_map.py`, `dashboard/sodo.js`, i18n `sodo.hx.*` và `sodo.dp.*`
- Test mới: `test_a00..a07_*`, `test_b01_*`, `test_b02_*`, `test_b03_*`, `test_b_dau_cuoi`, `test_g2_*`, `test_fix01..05_*`; giàn giáo `tests/python/_so_luot_chay.py`

## 4. Núm vặn (cấu hình)

| Núm | Chỗ | Mặc định | Ý nghĩa |
|---|---|---|---|
| `self_improve`, `low_risk_auto` | `<brain>/Joyce/factory.json` | bật ở 61 brain | tự cải tiến |
| `auto_deploy` | factory.json | true | false = dừng tự triển khai |
| `eval_bat_buoc` | factory.json | false | true = thiếu bộ ca thử thì chặn |
| `canary_min_tasks`, `canary_hours` | factory.json | 20, theo cấu hình | ngưỡng canary |
| `max_ap_tuan` | factory.json | 2 | trần số lần tự cải tiến mỗi file mỗi 7 ngày (0 = không giới hạn) |
| `tasks.rao_hoan_thanh` | `settings.json` | `["external-write"]` | loại việc vào cột duyệt khi chưa nghiệm thu độc lập (`[]` = tắt) |
| `tasks.tran_token_luot` | `settings.json` | 0, chủ đặt **1.000.000** ngày 29/10 | trần token mỗi lượt (tối đa 1 triệu) |
| `telemetry_ready` | hàm `factory.telemetry_ready` | cần ≥5 lượt có revision trong 30 ngày | KHÔNG phải cờ cấu hình; test monkeypatch |
| `JOYCE_RUN_LEDGER_DIR` | env | không đặt | chỉ để test cô lập sổ; `tests/python/_paths.py` đặt |

## 5. Quy ước và bẫy đã dẫm (đọc kỹ trước khi sửa)

1. **Chạy test ở worktree sạch**, không ở checkout có `.env`: `git worktree add --detach <dir> <sha>` rồi `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python tests/run.py`. Full suite khoảng 30 phút. Ghi lệnh, HEAD, exit code, log thô (xem `evidence/`).
2. **Test cũ của repo hay đóng đinh hợp đồng đã đổi.** Trước khi "sửa mã cho test xanh", đọc docstring của hàm và lịch sử: ví dụ `aux_engine.swap()` BỌC mọi engine vào chuỗi một mắt trong suốt CÓ CHỦ Ý (ghi mức dùng token); sửa mã theo test sẽ phá tính năng.
3. **Thêm route mới ở CUỐI `main.py`** rồi `python tests/python/test_route_table.py --update` và commit file `route_table.json` cùng thay đổi.
4. **`agent_revision` = SHA-256 NỘI DUNG THÔ file agent** (`run_ledger.doc_file_agent`), để so được với `candidate_hash` của canary. Đổi cách băm là phá bằng chứng.
5. **Lỗi sổ không bao giờ làm hỏng lượt chạy** (`run_ledger.ghi_an_toan`). Giữ nguyên nguyên tắc này khi thêm hook.
6. **Không `git add -A`**: dữ liệu thật nằm trong `server/` (sổ, settings, khóa). Thêm file chạy lúc runtime vào `.gitignore`.
7. **Công cụ Bash trong phiên này làm hỏng chuỗi có `\\n` trong heredoc.** Sửa file có chuỗi nhiều dòng bằng công cụ Edit hoặc `chr(10)`, rồi `ast.parse` kiểm cú pháp.
8. `dashboard/humanoid/` được .gitignore giữ local (license); test cần nó phải bỏ qua có ghi rõ khi thiếu.
9. Không dùng gạch dài (em dash) ở bất cứ đâu: có test canh (`test_go_chatgpt_web`, `test_nhat_ky_song_ngu`).
10. Mỗi lần gộp vào `main` phải tăng `VERSION` và viết `CHANGELOG.md` + `CHANGELOG.en.md` cho màn hình điện thoại (`docs/quy-uoc-dev.md`).

## 6. Việc làm tiếp, theo thứ tự đề xuất

1. ~~Cho các tool của hub hỏi `run_context.cho_phep`~~ **ĐÃ LÀM ở 1.3.45** (mọi tool). Còn: tinh chỉnh `hub_effect` cho từng tool quan trọng (tiền, tin nhắn) thay vì phân loại thô, và khai `allowed_effects` dần theo phòng (bắt đầu Đối Soát với `[read]`, cần chủ duyệt hồ sơ pilot).
2. ~~Đưa chat vào sổ lượt chạy~~ **ĐÃ LÀM ở 1.3.45** (khung chat của chủ, Telegram, CLI). Còn: đường CLI native (Claude Code, Codex...) tự gọi tool ngoài hub, và bot Zalo.
3. **Bộ chấm tự động hoặc nhóm ca bắt buộc theo phòng** (G4): hiện chỉ chủ chấm tay và `verify_agent` của workflow tạo `verified_pass`.
4. **Trần theo CÂY** thay cho theo lượt (cộng manager, con, retry, verifier, fallback); xác định "lượt cải tiến" để áp mức 500k mà chủ đã chốt.
5. **JHA-12**: gói phát hành bất biến + ánh xạ brain/agent sang revision; hiện nâng trợ lý dùng chung đổi cho mọi phòng cùng lúc.
6. **JHA-06 và B03**: biến bản kê `route_cert.py` thành chốt bắt buộc từng route; sandbox chỉ-đọc cho CLI native.
7. **A07.1**: giảm số route nạp lúc import hoặc tách `main.py`; gate p95 khởi động chưa đạt.
8. **Độ phủ nền tảng**: chạy suite trên Linux và macOS (nhánh khóa `fcntl`, ca symlink file chưa chạy thật).
9. **Compiler (JHA-10)** và **cập nhật đặc tả** `Joyce-harness.md` theo thực tế (hiện đặc tả chưa phản ánh `run_context`, sổ lượt chạy, rào hoàn thành).

## 6b. Cách bắt đầu G3 thật khi chủ duyệt

1. Sao lưu `agents/truong-phong-doi-soat.md` (thư mục `brains/` KHÔNG có git, sửa sai là mất), khai `allowed_effects: [read]`, kiểm agent vẫn làm được việc đọc của nó (nếu nó ghi memory hay wiki thì `[read]` sẽ chặn: khai thêm `internal_write` có chủ ý, đừng bỏ qua).
2. Chuyển 5 đến 10 ca trong `test_g3_doi_soat_sandbox.py` thành bộ ca thử `Joyce/evals/<slug>.json` của phòng, dùng số của kỳ thật đã biết trước.
3. Mỗi lượt đối soát thật: dùng `doi_soat_kiem.kiem` làm căn cứ chấm, không tin câu 'đã đối chiếu xong'; nhập kết quả bằng nút Đạt/Rớt hoặc nối `cham_luot` tự động chỉ cho kết quả của bộ kiểm.
4. Theo dõi `lan_bi_chan_quyen` và token trên Sơ đồ; điều kiện dừng nằm ở hồ sơ pilot.

## 6c. Lỗ hổng quan trọng: engine CLI không mang danh tính lượt chạy xuống hub

Claude Code, Codex, Grok, Antigravity gọi hub bằng HTTP (`/hub/mcp`, header `Authorization`, `X-Joyce-Mode`, `X-Joyce-Vault`) ở TIẾN TRÌNH KHÁC, nên `run_context` (contextvars) không tới được hub: `allowed_effects` KHÔNG có hiệu lực ở đường đó. Chỉ engine API chạy trong tiến trình (Z.ai, OpenRouter, OpenAI API, Anthropic API, Gemini, Groq, DeepSeek, Ollama) mới được bảo vệ. Vì vậy pilot dùng bản sao `doi-soat-pilot` chạy Z.ai chứ không khai quyền cho agent gốc (gpt-5.6-sol qua Codex).

Hướng sửa (chưa làm): thêm header `X-Joyce-Run: <run_id>` vào cấu hình hub MỖI tiến trình CLI (Codex qua `extra_config`/`codex_vault_override`, Claude qua file `--mcp-config` theo lượt) và để `/hub/mcp` dựng `run_context` từ dòng sổ đang `running`. Header chỉ làm quyền HẸP lại (không bao giờ cấp thêm). Riêng Grok, Antigravity và Gemini ghi cấu hình vào file dùng chung theo brain nên header theo lượt sẽ giẫm lên nhau giữa các lượt đồng thời: cần thiết kế riêng. Đây là việc ưu tiên số một trước khi khai `allowed_effects` cho agent chạy bằng CLI.

## 7. Điều chủ đã quyết (không hỏi lại)

- 28/10: duyệt gói A; D2 như đề xuất; D4 nhẹ (chỉ chặn khi bộ ca thử hỏng, thiếu thì không chặn); hành vi không tự áp ở gói A.
- 28/10: nhiều lần "tiếp tục hoàn thiện, phần cần duyệt để sau" nên gói B và phần G2 đã làm không hỏi từng bước.
- 28/10: tắt máy 00:00 hằng đêm đã có tác vụ sẵn; tự bật Joyce cần chủ bật công tắc "Tự bật Joyce" (cài persistence bị chặn khi chưa được cho phép rõ).
- 29/10: duyệt pilot Đối Soát (em làm luôn); gộp `main` rồi sửa 28 test đỏ; có rào hoàn thành; đo token thật; trần 1.000.000 token mỗi lượt.
- Còn chờ chủ: mở pilot Đối Soát, giá trị `eval_bat_buoc` mặc định, sửa 30 skill lỗi YAML, loại việc nào là "lượt cải tiến", có đặt rào hoàn thành cho loại việc khác ngoài `external-write`.
