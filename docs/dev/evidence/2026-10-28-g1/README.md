# Bằng chứng nền của gói G1 (A00)

> Lập theo A00 của [kế hoạch giao Sonnet](../../2026-10-28-joyce-harness-g1-g2-sonnet-plan.md). File này ghi **đúng cái đã đo**, kèm chỗ còn thiếu. Không có số nào ở đây được suy ra hay điền thêm.

## Môi trường đo

- Máy: Windows 10 (10.0.17763), Python 3.14.6, chạy bằng `.venv\Scripts\python.exe` của repo chính.
- Mọi lần chạy full suite dùng **worktree sạch** (không có `.env`, không có state thật) tạo bằng `git worktree add --detach`, rồi `python tests/run.py` với `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`.
- Máy đồng thời chạy server Joyce thật và các lệnh khác của phiên làm việc, nên **thời gian chạy không so sánh được giữa các lần**.

## Full suite (log thô đính kèm cùng thư mục)

| File log | Commit chạy | Kết quả cuối log | Ghi chú |
|---|---|---|---|
| `full-suite-6752fd0-ma-nhu-1.3.38.txt` | `6752fd0` | 855/883 xanh | Chỉ thêm số phiên bản 1.3.39 so với mã 1.3.38, nên dùng làm baseline suite 1.3.38 |
| `full-suite-332ff4c-1.3.39.txt` | `332ff4c` | 855/888 xanh | Bản 1.3.39 có mã harness |
| `full-suite-b606e41-1.3.40.txt` | `b606e41` | 861/890 xanh | Có hộp thư Messenger |
| `full-suite-8f07625-1.3.41.txt` | `8f07625` | 865/894 xanh | Có G1 (FIX-01..05) |

**Chưa ghi lại được:** exit code của runner (lệnh bọc chỉ ghi đầu ra), nên kết luận dựa trên dòng cuối của log. Đây là một khoảng hở của A00; lần chạy sau của gói A phải lưu exit code.

**29 mục ngoài số xanh của 1.3.41** (đọc từ chữ `ĐỎ` trong log; log không tách được "fail" với "error" hay "skip", nên chưa phân loại):
`test_aux_engine`, `test_aux_fallback`, `test_bau_troi_tri_thuc`, `test_deepseek_provider`, `test_full_quyen_ungated`, `test_go_chatgpt_web`, `test_graph_watch`, `test_groq_provider`, `test_icons`, `test_joyce_hands.js`, `test_joyce_humanoid.js`, `test_khoi_dong_nhe`, `test_learn_agent_workflow`, `test_mobile_layout`, `test_nhat_ky_song_ngu`, `test_oauth_scope_clerk`, `test_ollama`, `test_ollama_local_tool_pdf`, `test_pinned_folder`, `test_placeholder_ui`, `test_reply_policy_api`, `test_scheduled_call_0203`, `test_settings_ghi_an_toan`, `test_settings_khong_treo_theo_cli`, `test_subscription_router`, `test_team_docs`, `test_thu_lai_tam_thoi`, `test_workflow_graph_phase10`, `test_workflow_turn_ws`.

So với baseline suite 1.3.38 (28 mục đỏ): **chỉ `test_khoi_dong_nhe` là mới**. 28 mục còn lại đỏ ở cả hai bản. Nguyên nhân của 28 mục này chưa được điều tra, nên **không gọi là "lỗi cũ do môi trường"**; A07.2 phải kiểm lại từng mục ở đúng baseline.

`test_resonance_perf` đỏ ở log 1.3.40 và xanh ở log 1.3.41. Chạy lại riêng hai lần ở 1.3.40 đều xanh. Chưa có bằng chứng nguyên nhân.

## Benchmark `test_khoi_dong_nhe` (tỷ lệ nạp `main` so với nạp fastapi, ngưỡng nhỏ hơn 5,0)

Đo 5 lần mỗi bản, **xen kẽ**, lúc máy gần rảnh:

| Bản | 5 giá trị đã sắp xếp |
|---|---|
| `6752fd0` (mã như 1.3.38, gọi là "1.3.39 gốc" trong master plan) | 4,69 · 4,78 · 4,82 · 4,85 · 4,94 |
| 1.3.41 | 4,82 · 4,91 · 4,92 · 4,93 · 4,99 |

**Chỉ còn giá trị đã sắp xếp**, thứ tự chạy thật không được lưu. Lúc máy bận từng ra 5,19 và 5,42 (test đỏ). Chưa có profile import nên chưa biết module nào gây phần tăng; việc này là A07.1.

## Cô lập state

`tests/python/test_a00_cach_ly_state.py` chạy các test của G1 và gói A trong tiến trình con và kiểm `config.STATE_DIR` không phải thư mục `server/` thật. Tách riêng khỏi kết quả của chính các test đó.

## Giới hạn chung

- Không có CI Linux hay macOS trong phạm vi lượt này; mọi kết quả là Windows.
- Không đọc, sửa hay quét kho Kanban production trong A00. Con số `0/160` việc có khóa agent là kết quả quét chỉ-đọc của lượt trước, ghi ở master plan mục 3.4, không phải bất biến.

## Kết quả cuối gói A (1.3.42)

Chạy trong worktree sạch, `python tests/run.py` bằng `.venv\Scripts\python.exe`, Windows 10, Python 3.14.6, `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`.

| Log | Commit | Kết quả | Exit code | Thời gian |
|---|---|---|---|---|
| `full-suite-fdf44cd-1.3.42-lan1-co-2-loi.txt` | `fdf44cd` | 873/904 | 1 | 1774 giây |
| `full-suite-4062d3f-1.3.42-goi-A.txt` | `4062d3f` | **876/904** | 1 | 1761 giây |

- **Lần 1 lộ hai việc cần sửa, đã sửa trước lần 2:** `test_a03` đòi hơn 100 file mẫu từ `brains/` (không nằm trong git, nên worktree sạch chỉ có 10 file); và một lỗi THẬT của bộ khóa: `deploy_writer.khoa()` ném `PermissionError` khi hai tiến trình cùng tạo file khóa lần đầu (tái hiện 1/10 lần khi chạy 10 tiến trình song song, 0/20 sau khi sửa; test tái hiện đỏ trên mã cũ, xanh trên mã mới).
- **Lần 2:** 28 mục đỏ, **không mục nào mới** so với 1.3.41 (29 mục). `test_khoi_dong_nhe` hết đỏ (tỉ lệ 4,30 đến 4,75 theo phép đo thô của chính test; gate p95 của plan vẫn chưa đạt, xem `44-khoi-dong-ket-luan.md`). `test_resonance_perf` xanh ở lần này, nhưng từng đỏ ở log 1.3.40 nên vẫn là test có biến động.
- **28 mục đỏ còn lại giống hệt 1.3.41 và 1.3.38**, nên không do gói A. Đã kiểm lại riêng hai mục plan nêu tên ở đúng mã gốc 1.3.39 (`332ff4c`): `test_icons` đỏ vì 43 emoji còn trong giao diện và 109 tên icon chưa có trong vendor; `test_nhat_ky_song_ngu` đỏ vì một mục tiếng Anh cũ lẫn chữ Việt. Cả hai đỏ ở mã gốc. Nguyên nhân của các mục còn lại **chưa được điều tra**, nên vẫn không gọi là "lỗi môi trường".
- **Không khai suite xanh:** 876/904 không phải xanh toàn bộ.

## Khoảng hở độ phủ còn lại sau gói A

- Ca symlink FILE (lá và tráo symlink file) bị bỏ qua trên máy Windows này vì thiếu quyền tạo symlink; chỉ junction chạy thật.
- Chưa chạy trên Linux và macOS. Khóa liên tiến trình có hai nhánh (`msvcrt`, `fcntl`); nhánh `fcntl` chưa được chạy thật ở đâu cả.
- Chưa chạy luồng tự cải tiến trên brain thật, chỉ sandbox.

## Kết quả cuối gói B và G2 (1.3.43)

Cùng cách chạy như trên (worktree sạch, `python tests/run.py`, Windows 10, Python 3.14.6).

| Log | Commit | Kết quả | Exit code | Thời gian |
|---|---|---|---|---|
| `full-suite-a1d591d-1.3.43-lan1-co-2-loi.txt` | `a1d591d` | 883/914 | 1 | 1796 giây |
| `full-suite-ff1865d-1.3.43-goi-B-G2.txt` | `ff1865d` | **886/914** | 1 | 1856 giây |

- **Lần 1 lộ hai test đỏ mới do chính mã gói B, đã sửa:** `test_factory` (canary nay đọc bằng chứng từ sổ lượt chạy, và trần 2 lần mỗi tuần cản các đề xuất liên tiếp trong test) và `test_fastyaml` (mã mới gọi `yaml.safe_load` trần trái quy ước của repo). Còn phát hiện test làm bẩn sổ thật: một số test ghi lượt chạy giả vào `server/run_ledger.sqlite3`, làm `test_factory` chập chờn khi chạy song song (2 trong 8 lượt đỏ); nay sổ của test luôn nằm trong thư mục tạm (`JOYCE_RUN_LEDGER_DIR`, đặt ở `tests/python/_paths.py`) và 8 lượt song song đều xanh.
- **Lần 2:** 28 mục đỏ, **không mục nào mới** so với 1.3.41 (29 mục). 28 mục này giống hệt các lần trước.
- **`test_khoi_dong_nhe` xanh ở lần này nhưng vẫn dao động quanh trần 5,0** (đo riêng 4,22 đến 5,17 giữa các lần). Gate p95 của A07.1 vẫn CHƯA đạt; không coi một lần xanh là đã đạt.
- Không khai suite xanh: 886/914 không phải xanh toàn bộ. Khoảng hở độ phủ (symlink file, Linux, macOS, brain thật) vẫn như mục trước.

## 28 test đỏ cũ: nguyên nhân và cách sửa (29/10/2026, 1.3.44)

Chạy từng test ở worktree sạch, đọc lỗi, sửa theo đúng loại nguyên nhân. Phân loại: **MÃ** là chức năng bị mất dây hoặc thiếu, đã sửa mã; **TEST** là test giữ hợp đồng cũ đã bị thay có chủ ý, đã sửa test theo hợp đồng hiện hành; **MÔI TRƯỜNG** là test phụ thuộc thứ không có ở máy sạch.

| Test | Loại | Nguyên nhân thật | Sửa |
|---|---|---|---|
| test_go_chatgpt_web | MÃ | 3 chú thích trong main.py có gạch dài (luật CLAUDE.md) | thay bằng gạch ngang |
| test_aux_engine, test_aux_fallback, test_full_quyen_ungated, test_reply_policy_api | TEST | từ 1.3.19 `swap()` luôn bọc engine vào chuỗi một mắt trong suốt để ghi mức dùng; mức full có chuỗi ở chế độ safe_retry | assertion nhận chuỗi một mắt chứa đúng engine đó |
| test_groq_provider, test_deepseek_provider, test_ollama, test_ollama_local_tool_pdf | TEST | từ 1.3.18 các nhánh provider nằm trong closure `_vong_tool` và đi qua `_stream_chain`; ollama-local cần key sentinel | test dò đúng cấu trúc mới |
| test_ollama_local_tool_pdf (RAM Apple) | MÃ | khai tay RAM trên Mac chip Apple làm mất cờ GPU dùng chung | `_ol_specs_hien_dung` giữ GPU khi chắc cùng máy và đúng Apple Silicon |
| test_pinned_folder | MÃ | ba chỗ mất dây: khối prompt thư mục ghim ở chat thường, `resolve_path` và `brain_root` của route coding, tuỳ chọn `only_dirs` của /files/search | nối lại cả ba |
| test_team_docs | MÃ | dấu ">" của ô chọn thư mục (`/files/list?subdirs=1`) không còn | thêm lại cờ `dirs` |
| test_oauth_scope_clerk | MÃ | route callback OAuth không chuyển `error`/`error_description` của nhà cung cấp, và in lỗi không escape (XSS) | route nhận hai tham số, chuyển hướng khi có `retry_url`, escape thông báo |
| test_settings_khong_treo_theo_cli | MÃ | lệnh `taskkill` trong grok_cli không cắt stdin | thêm `stdin=DEVNULL` |
| test_scheduled_call_0203 | MÃ | cờ `call` của nhắc việc không đi qua tool joyce_schedule và khối JOYCE_VIEC | nối create, update, schema và khối |
| test_icons | MÃ | 43 emoji trong giao diện và 2 tên icon thiếu trong bộ vendor | 14 icon thêm vào bộ vendor; nút 3D Joyce, Apex, hạt lượng tử, trình phát nhạc, trang Quản lý Shop dùng icon Lucide. Lưu ý: trang Quản lý Shop trộn icon thật (12 ký hiệu đã đổi) với ký hiệu hình học cũ chưa bị test cấm |
| test_placeholder_ui | MÃ và TEST | placeholder "model", "theo vai" viết thường; placeholder chỉ là số "3" bị coi là lỗi | viết hoa hai chữ, test bỏ qua placeholder là số |
| test_mobile_layout | TEST | số `?v=` của brain-view.js đổi khi sửa file | test nhận mọi số |
| test_nhat_ky_song_ngu | MÃ | bản tiếng Anh của CHANGELOG lẫn chữ Việt (tên riêng, nhãn nút) | đổi sang không dấu hoặc dịch |
| test_workflow_turn_ws, test_workflow_graph_phase10 | TEST | fake `execute_workflow`, `mk`, engine có chữ ký cũ, thiếu `mode`, `extra_tools`, `is_available` | cập nhật fake |
| test_graph_watch | TEST | handshake WebSocket đi qua WebSocketGuard, host mặc định `testserver` bị từ chối | dùng `ws://localhost/...` |
| test_learn_agent_workflow | TEST | từ 0.105.0 sửa vai chỉ được THÊM luật, không viết lại thân hay đổi vai trò | test theo hợp đồng mới |
| test_subscription_router | TEST | câu hết lượt của nhánh Codex đi qua `_limit_frame` ở chỗ khác | regex theo mã hiện hành |
| test_bau_troi_tri_thuc | TEST | số chỗ gửi tool_call tăng khi thêm đường fallback | bất biến thay cho số cố định |
| test_thu_lai_tam_thoi | TEST | deepseek và zai chưa nằm trong danh sách engine giả | thêm vào |
| test_settings_ghi_an_toan | TEST | kênh WhatsApp đã gỡ nên route không còn | ghim điều cần ghim: mở trang không làm mất cấu hình |
| test_joyce_hands, test_joyce_humanoid | MÔI TRƯỜNG và TEST | `dashboard/humanoid/` được .gitignore giữ local (license); root Apex giả thiếu `querySelector` | bỏ qua có ghi rõ khi thiếu thư mục (đây là KHOẢNG HỞ độ phủ, không phải pass); thêm `querySelector` cho fake |
| test_khoi_dong_nhe | khác | tỉ lệ dao động quanh trần 5,0 | chưa đổi; xem `44-khoi-dong-ket-luan.md` |

Thêm một lỗi thật do gói A (không nằm trong 28): `deploy_writer.khoa()` ném `PermissionError` khi hai tiến trình cùng tạo file khóa (xem mục trên).

## Kết quả cuối 1.3.44 (29/10/2026)

Worktree sạch, `python tests/run.py`, Windows 10, Python 3.14.6, commit `94e2375`: **913/914 trên 916 mục xanh**, exit code 1, 1911 giây. Log thô: `full-suite-94e2375-1.3.44.txt`. So với 28 mục đỏ cũ ở 1.3.41: **hết cả 28**. Còn ba mục đỏ trong lần chạy này:

| Mục | Kết luận |
|---|---|
| `test_trang_coding.js` | LỖI DO MÃ MỚI của em: test dò chuỗi `+ _khoi_coding(_row0)` mà em đã thêm đối số thứ hai cho khối thư mục ghim. Đã sửa test (nhận đối số thứ hai) và chạy riêng: xanh. KHÔNG nằm trong lần chạy full suite này |
| `test_resonance_a3_learning` | Xanh khi chạy lại riêng ngay sau đó; nghi chập chờn theo tải máy (cùng loại với `test_resonance_perf` từng gặp). Chưa điều tra nguyên nhân gốc |
| `test_khoi_dong_nhe` | Dao động quanh trần 5,0 (đo riêng 4,83 đến 5,35 ba lần liền). Gate A07.1 chưa đạt, không nâng trần |

Vì vậy KHÔNG khai "full suite xanh": còn hai mục chập chờn và một mục đã sửa nhưng chưa chạy lại trong full suite.

## Kết quả cuối 1.3.45 (29/10/2026)

Worktree sạch, commit `d034446`: **918/919 xanh**, exit code 1, 1941 giây. Log: `full-suite-d034446-1.3.45.txt`. Mục đỏ duy nhất: `test_khoi_dong_nhe` (gate khởi động A07.1, dao động quanh trần 5,0, chưa đạt, không nâng trần).

Lần chạy đầu của 1.3.45 (`55ee824`, log `full-suite-55ee824-1.3.45-lan1-co-5-do.txt`) có 5 mục đỏ mới do chính mã chat vào sổ lượt chạy: bốn test cắt `run_turn` ra chạy riêng thiếu hàm sổ (thêm hàm giả), một test dò chuỗi `if isinstance(out, str):` bị lệch vì lớp bọc `_tg_answer` có cùng chuỗi (đổi tên biến). Đã sửa, chạy lại: hết.

Khi đó: **không còn mục đỏ nào ngoài gate khởi động**. Vẫn còn khoảng hở độ phủ: các ca symlink file, Linux và macOS, `dashboard/humanoid/` (giữ local) chưa chạy ở máy sạch.

