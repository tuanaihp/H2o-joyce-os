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

