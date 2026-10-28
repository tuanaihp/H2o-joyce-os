# Joyce-hardness: kiểm tra harness của Joyce và của các phòng ban

> Tài liệu SỐNG. Mỗi lần thay đổi harness thì sửa bảng chấm điểm ở mục 2 và thêm một dòng vào "Nhật ký cập nhật" ở cuối file.
> Bản đầu: 2026-10-28, soi trên nhánh `claude/crm-v2-final-1-3-35` (bản 1.3.38). Người đọc: chủ Joyce và các phiên Claude Code làm việc trên repo này.
> Mục đích dài hạn: làm nền để xây **harness riêng cho Joyce** (một lõi dùng chung, không phụ thuộc engine nào).

## 0. Cách đọc

"Harness" là phần bao quanh model: vòng lặp, ngữ cảnh, công cụ, agent con, kỹ năng, bộ nhớ, system prompt, hook và phân quyền. Model quyết định làm gì, harness quyết định model được thấy gì, được làm gì và chuyện gì xảy ra sau mỗi bước. Tài liệu này đối chiếu Joyce với đúng chín thành phần trong bài giảng anh gửi:

Loop, Context, Tools và Skills, Sub-agent, Skill có sẵn, Memory, System prompt, Hooks, Phân quyền.

Quy ước mức chấm: **Tốt** (đủ và có kiểm chứng), **Khá** (có, còn lỗ hổng rõ), **Thiếu** (cơ chế có nhưng gần như không dùng hoặc thiếu mảnh quan trọng), **Chưa có**.

Mọi nhận định ghi kèm file đã đọc. Chỗ nào em chưa kiểm tra thì nói thẳng ở mục 7.

## 1. Kết luận nhanh

**Harness của Joyce mạnh ở tầng hub, phân quyền và quản lý ngữ cảnh. Yếu ở chỗ "một agent là gì".** Hôm nay agent của Joyce mới là một file prompt kèm danh sách skill và tên model. Nó chưa là một gói có phạm vi riêng (công cụ được dùng, mức quyền, trần số vòng, loại việc). Đó chính là khác biệt giữa bài giảng ("mỗi phụ bếp có phạm vi riêng") và Joyce hiện tại.

Điểm mạnh đáng giữ:
- Một cửa công cụ duy nhất (MCP Hub) cho mọi engine, có phân loại đọc, ghi, nguy hiểm, giới hạn tần suất và nhật ký kiểm toán.
- Vòng lặp tool của engine API có trần số vòng, phanh chống kẹt vòng và thử lại có chờ.
- Nén hội thoại và "Adaptive Context Runtime" đã chạy thật trên máy anh (mức Siêu tiết kiệm).
- Cơ chế bộ nhớ có kiểm soát (xem, sửa, quên, tắt học) và cơ chế tự học có người duyệt.

Bảy lỗ hổng lớn nhất, xếp theo mức đáng làm trước:
1. **Agent chưa có phạm vi riêng.** Frontmatter agent chỉ có `name, slug, role, group, skills, model, model_provider`. Không có `tools`, `mode`, `max_rounds`, loại việc (khám phá, thực hiện, kiểm tra). Phạm vi công cụ chỉ nằm ở bước workflow hoặc việc Kanban.
2. **Hook có cơ chế nhưng không có hook bảo vệ nào bật sẵn.** `pre_tool_call` chặn được và sửa được tham số, nhưng plugin duy nhất dùng hook là `tool-audit` (chỉ đếm, và tắt mặc định).
3. **Dọn ngữ cảnh trong một lượt dài còn thô.** Mỗi kết quả công cụ bị cắt ở 8.000 ký tự nhưng kết quả cũ không bị dọn trong cùng lượt (tối đa 30 vòng). Chưa thấy xử lý chủ động khi nhà cung cấp báo "ngữ cảnh quá dài".
4. **Các phòng ban chủ yếu là bản sao.** 549 trên 600 agent là 9 agent dùng chung nhân bản vào cả 61 brain. 14 brain khối chỉ có đúng 9 bản sao đó, không có agent nghiệp vụ nào.
5. **Bộ nhớ gần như rỗng trong thực tế.** 54 trên 61 brain có chỉ mục bộ nhớ trống, 48 file bộ nhớ agent không chứa bài học nào. Cơ chế tốt nhưng chưa có dữ liệu chảy vào.
6. **Prefix caching bị phá ở đường API.** Hai khối đổi mỗi lượt (đồng hồ theo phút và "Mức dùng hôm nay" đếm token) nằm TRONG system prompt, mà dấu cache của Anthropic đặt trên toàn bộ system như một khối duy nhất. Phần "tĩnh trước, động sau" đã đúng thứ tự, nhưng chưa tách khối nên không hưởng được. Chi tiết ở mục 3.11.
7. **Chưa có "dừng lại xin phép chủ" cho từng thao tác lớn trong chat.** Quyền chỉ là cho phép hoặc chặn. Việc xin duyệt có ở Sổ Shop (chi vượt hạn mức), cột Review của Kanban (sau khi chạy), và đường ghi có xác nhận (đang ở 0%). Chi tiết ở mục 3.9 và 3.13.

Trả lời hai câu hỏi của anh:
- **"Harness hiện tại của Joyce đã tốt chưa?"** Tầng nền (hub, quyền, ngữ cảnh) đã tốt đến khá. Tầng agent và hook chưa. Đủ dùng để vận hành H2O, chưa đủ để gọi là harness riêng của Joyce.
- **"Các agent các phòng đã có harness chưa?"** Có khung, chưa có phạm vi. Mỗi phòng đã có không gian riêng (brain riêng), lời dặn tập trung (đa số có mục Bối cảnh, Quy trình, Cấm), một skill nghiệp vụ. Còn thiếu công cụ giới hạn theo agent và bộ nhớ có dữ liệu. Chi tiết ở mục 4.

## 2. Bảng chấm điểm chín thành phần

| # | Thành phần | Mức | Một dòng lý do |
|---|---|---|---|
| 1 | Loop | Khá | Engine API có trần 30 vòng, phanh lặp, thử lại. Chưa có trần riêng theo agent. Vòng kiểm chứng chỉ có ở workflow, không có ở chat |
| 2 | Context | Khá | Nén tóm tắt và Adaptive Runtime đã chạy. Chưa dọn kết quả cũ trong lượt, chưa ghim mục không được nén |
| 3 | Tools và Skills | Tốt | Hub thống nhất ba nguồn, registry đủ trường, nạp tool lười khi đông. Skill cao cấp (git, PR, test) chỉ có ở engine CLI |
| 4 | Sub-agent | Thiếu | Có Team, Kanban, workflow nhiều bước, Task của CLI. Chưa có ba kiểu phụ bếp khai báo rõ, chưa chuẩn hóa "chỉ trả kết quả cần thiết" |
| 5 | Skill có sẵn | Khá | Sáu skill hệ thống có mặt ở mọi brain, tự cập nhật. Skill nghiệp vụ thật chỉ khoảng 41 cái, mỗi cái ở một phòng |
| 6 | Memory | Khá | Cơ chế đầy đủ và có kiểm soát. Dữ liệu thực gần như trống |
| 7 | System prompt | Khá | Xếp lớp rõ, có ngân sách và test. Prompt lớn (CLAUDE.md 31 KB) nên phải nhờ mức tiết kiệm mới nhẹ |
| 8 | Hooks | Thiếu | Hạ tầng hook tốt. Không có hook bảo vệ nào chạy sẵn |
| 9 | Phân quyền | Tốt | Ba mức quyền, kiểm từng lời gọi, hai lớp, kiểm toán. Thiếu quyền ở cấp agent |

Các chủ đề bổ sung trong bài giảng (cùng thang điểm):

| Chủ đề | Mức | Một dòng lý do |
|---|---|---|
| Nhật ký chỉ ghi thêm | Thiếu | Lịch sử chat nằm trong SQLite có sửa và xóa được. Nhật ký kiểm toán là file chỉ ghi thêm nhưng chỉ giữ khoảng 10 MB |
| Khôi phục và replay | Khá | Việc Kanban có lease và reclaim, nhóm chat có `recover`. Workflow có checkpoint nhưng đang ở 0% |
| Bộ nhớ độc lập với harness | Tốt | Phiên và bộ nhớ lưu riêng, đổi engine giữa chừng vẫn nạp lại được mạch |
| Lắp hướng dẫn đầu ca | Khá | Xếp nhiều tầng đúng ý bài giảng. CLAUDE.md của phòng chỉ là lược đồ vault chung, chưa có luật riêng từng phòng |
| Prefix caching | Thiếu | Đo thật: Claude Code qua Joyce 76%, Codex 96%. Đường API bị phá cache bởi khối đổi mỗi lượt |
| Hook gọi chương trình ngoài (JSON vào, exit code ra) | Chưa có | Hook của Joyce chỉ là hàm Python trong plugin |
| Dừng xin phép con người | Thiếu | Có ở vài điểm rời rạc, không có cổng chung |
| Làm, kiểm tra, điều chỉnh | Khá | Workflow có `verify_agent` kiểm độc lập, thử lại, kết luận không rõ là hỏng. Mới 5 workflow dùng |
| Kiểm tra theo loại việc | Thiếu | Một kiểu kiểm duy nhất (agent đọc và phán). Chưa có kiểu chạy test, so ảnh, hay tính lại số |
| Bếp thử nghiệm riêng (sandbox) | Khá | Sandbox của Codex, môi trường lọc cho lệnh, thư mục làm việc ghim, việc nền khóa công cụ. Không có bản sao brain để thử |
| Giới hạn dữ liệu và tài nguyên | Khá | Sổ cái token mỗi phút, tần suất theo kết nối, trần thời gian và output. Chưa có trần chi phí theo agent |

## 3. Chi tiết từng thành phần

### 3.1 Loop

Có gì:
- **Engine API** (OpenAI, Anthropic API, Gemini, OpenRouter, Groq, DeepSeek, Z.ai, Ollama): vòng gọi tool của Joyce tự viết, trong `server/engine.py`.
  - Trần vòng `_max_tool_rounds()` mặc định 30, chỉnh bằng `JOYCE_MAX_TOOL_ROUNDS` (kẹp 1 đến 120). Chạm trần thì báo rõ cách xử lý.
  - Phanh chống kẹt `_LapGuard`: gọi y hệt cùng tool cùng tham số, nhắc thẳng vào kết quả tool ở lần lặp thứ 3, dừng lượt ở lần thứ 5. Cố ý chỉ bắt lặp tuyệt đối liên tiếp nên đọc, sửa, đọc lại không bị bắt oan.
  - Thử lại khi lỗi tạm thời `thu_lai_khi_tam_thoi` (mặc định 3 lần, chờ có nhiễu, đọc `Retry-After`).
  - Ép dùng tool khi yêu cầu rõ ràng (`_tool_requirement`), cổng riêng cho hủy lịch (`schedule_cancel_gateway`).
  - Gửi thêm tin giữa chừng (`server/steer_inbox.py`): tin chủ gõ khi Joyce đang chạy được đưa vào bước kế tiếp, không mất.
  - Lượt chat là việc của máy chủ, không gắn với WebSocket (`server/chat_runtime.py`): đóng hoặc F5 tab không hủy việc đang chạy.
- **Engine CLI** (Claude Code, Codex, Grok, Antigravity): vòng lặp do chính CLI chạy. Joyce bọc thêm giới hạn thời gian cho việc nền (`max_wall_s`, mặc định 1 giờ, env `JOYCE_BG_MAX_WALL_S`) và chuỗi dự phòng engine `aux_engine.swap` (chỉ đổi engine khi bước trước chưa gọi tool nào, không bao giờ chạy lại việc đã làm dở).

Thiếu:
- Trần số vòng và thời gian chỉ là cấu hình toàn cục, chưa đặt được theo từng agent.
- Vòng "làm, kiểm tra, nhận kết quả, điều chỉnh" CÓ ở workflow (xem 3.14) nhưng chỉ khi bước khai `verify_agent`. Trong chat thường và với việc ghi tiền hoặc hợp đồng thì không có bước kiểm tra độc lập sau khi model nói xong. `DeterministicQualityGate` có trong `server/context_compiler.py` nhưng chỉ nằm trong đường thích ứng đang ở mức thử (xem mục 5).

### 3.2 Context (ngữ cảnh) và việc dọn bàn bếp

Tương ứng bài giảng "mỗi vòng bàn bếp lại đầy thêm" và "dọn có chọn lọc: giữ nguyên, tóm tắt, loại bỏ".

Có gì:
- **Lắp system prompt theo lớp** (mục 3.7), cộng thêm kết quả công cụ vào ngữ cảnh mỗi vòng.
- **Nén hội thoại cho engine API** (`server/compaction.py`):
  - Giữ NGUYÊN 12 tin gần nhất, phần cũ hơn gộp vào một bản tóm tắt (tối đa 6.000 ký tự, mỗi tin đưa vào tóm tắt cắt còn 1.500 ký tự).
  - Lời nhắc tóm tắt dặn giữ chủ đề chính, quyết định đã chốt, con số, tên riêng, đường dẫn, việc dang dở và sở thích của người dùng, bỏ chào hỏi xã giao. Tức là ba nhóm "giữ nguyên, tóm tắt, loại bỏ" đã có, theo nghĩa gần đúng.
  - Nén nền sau mỗi lượt. Nếu đuôi chưa nén dài hơn 24 tin thì nén ĐỒNG BỘ trước khi gửi để phần cũ không bị cắt câm.
- **Engine CLI tự quản mạch hội thoại.** Codex và Claude Code xoay sang mạch mới khi chạm 1.000.000 token, mang theo gói mồi tối đa 300.000 ký tự. Antigravity không nối mạch nên chỉ gửi gói 45.000 ký tự mỗi lượt.
- **Cắt kết quả công cụ** `_clip_tool_result`: tối đa 8.000 ký tự, giữ đầu 60% và cuối 40% kèm dòng báo bỏ bao nhiêu, để model biết dữ liệu bị thiếu.
- **Adaptive Context Runtime** (`server/context_compiler.py`, `adaptive_context_runtime.py`, `fast_path_runtime.py`, `lazy_skill_runtime.py`, `conversation_state.py`, `capability_*`): đo, biên soạn và gửi "capsule" thay cho prompt đầy đủ. Mặc định xuất xưởng là mức Siêu tiết kiệm (`PRESET_MAC_DINH = "max"`). Theo ghi chú đo trong `server/config.py`: mức Tắt tốn khoảng 8.900 token cố định mỗi lượt, mức Siêu tiết kiệm khoảng 460 token (đo trên một brain mẫu).
  - Nạp tool lười: khi có từ 40 tool trở lên chỉ phơi 8 tool khớp nhất trong ngân sách 6.000 ký tự, còn lại tìm qua `joyce_search_tools` rồi gọi bằng `joyce_run_tool`.

Thiếu:
- **Không dọn kết quả cũ trong cùng một lượt.** Một lượt có thể có đến 30 vòng, mỗi kết quả tới 8.000 ký tự. Chỉ cắt từng kết quả, không thay kết quả cũ bằng một dòng tóm tắt khi bàn đã đầy.
- **Chưa thấy xử lý chủ động khi nhà cung cấp báo ngữ cảnh quá dài** trong `engine.py` (chưa soi phần xử lý lỗi ở `main.py`, xem mục 7).
- **Bản tóm tắt chỉ có một khối phẳng.** Không có chỗ "ghim" những dữ kiện tuyệt đối không được mất (số tiền, mã hợp đồng, quyết định của chủ) và chưa có test phát hiện mất dữ kiện sau nén.
- Lần thử sai, lần gọi lỗi không bị loại khỏi bàn khi đã xử lý xong.

### 3.3 Tools và Skills, và Registry

Slide "Registry mô tả từng công cụ" nói đủ bốn trường: tên, quyền cần có, hàm xử lý, mô tả.

Có gì:
- **Ba nguồn công cụ qua một cửa** `server/mcp_hub.py`: MCP ngoài (POS, quảng cáo, lịch, Zalo...), công cụ lõi (`joyce_read_file`, `joyce_list_dir`, `joyce_write_file`, `joyce_use_skill`, `joyce_connections`, `joyce_search_tools`, `joyce_run_tool`, và `joyce_run_command` chỉ khi phiên có thư mục làm việc), và plugin.
- **Registry đủ bốn trường:**
  - Plugin: `ctx.register_tool(name, description, handler, schema, min_mode, emoji)` trong `server/plugins_host.py`. Tên (kiểm biểu thức chính quy, cấm trùng tên lõi), mô tả, hàm xử lý, quyền tối thiểu `min_mode` (readonly, safe, full).
  - MCP và lõi: mỗi mục route có `call`, `effect`, `required_mode`, `source_type`, `source_id`.
  - Có thêm Capability Registry dẫn xuất (`server/capability_registry.py`, SQLite) dựng lại hoàn toàn từ ảnh chụp tool của hub, có tìm kiếm lai chữ và embedding (`capability_index.py`).
- **24 plugin đi kèm** trong `system/plugins/`, ví dụ `joyce-shop`, `joyce-task`, `joyce-schedule`, `joyce-memory`, `joyce-team`, `web-pilot`.
- **Skill:** thư mục `skills/<slug>/SKILL.md` theo từng brain, nạp lười được (`lazy_skill_runtime.py`, thân tối đa 12.000 ký tự).

Thiếu (đối chiếu slide "skill cơ bản" và "skill cao cấp"):
- Engine CLI có sẵn đọc, ghi, sửa, tìm file, chạy lệnh, git. Engine API có đọc, liệt kê, ghi CẢ file, và khi mở tab Code (có thư mục làm việc) thì thêm `joyce_run_command` (`server/run_command.py`). Lệnh đó chạy MỘT lệnh mỗi lần, không qua shell, môi trường lọc, có trần thời gian và output, có audit, ba mức: `suggest` chỉ đề xuất chữ, `auto` chỉ chạy lệnh trong danh sách cho phép (pytest, python, node, npm test, ruff, eslint, tsc, ls, cat, find, grep, rg, git chỉ đọc), `full` chạy đầy đủ. Vậy tìm trong code và chạy kiểm thử làm được ở tab Code kể cả với engine API.
- Còn thiếu ở engine API: sửa từng đoạn (chỉ ghi lại cả file, dễ ghi đè hoặc làm hỏng file lớn). Tạo commit và đẩy lên phải lên mức `full`, vì `git commit`, `push`, `reset` cố ý nằm ngoài danh sách của mức `auto`. Trong chat thường (không có thư mục làm việc) thì không có tool chạy lệnh nào.

### 3.4 Sub-agent

Slide: khi một đầu bếp không gánh nổi thì harness gọi thêm agent con, mỗi phụ bếp có phiên riêng, dụng cụ giới hạn, lời dặn chỉ làm đúng việc, thu về kết quả cần thiết, bàn chính vẫn gọn. Có ba kiểu: khám phá (chỉ xem), thực hiện, kiểm tra.

Có gì:
- **Team runner** (`server/team_runner.py`): nhóm chat nhiều agent, trưởng nhóm giao việc bằng khối `JOYCE_TEAM: {"op":"assign",...}`, host kiểm từng op theo vai của lượt. Lượt nhóm ở T1 chỉ chữ (không công cụ). Có trần số lượt.
- **Kanban và `joyce_task`:** việc nền, có `deps` nối trước sau, mức quyền theo từng việc (`suggest`, `auto`, `full`).
- **Workflow nhiều bước** (`workflows/<slug>.md`): mỗi bước gọi một agent, có thể chỉ agent của phòng khác bằng cú pháp `Ten Brain|slug`. Chạy nền thì bị khóa: không Bash, WebFetch, WebSearch, Task, MCP rỗng và nghiêm ngặt (`main.py::_workflow_agent_helpers`).
- **Replan có kỷ luật** (`server/agent_runtime.py`): agent được thêm nút kế hoạch nhưng KHÔNG BAO GIỜ được cấp thêm quyền, kiểm trong code chứ không trong prompt. Nhưng đường này đang ở 0% (`agent_canary`).
- **Khám phá chỉ đọc** (`readonly_orchestrator.py`, `readonly_path_runtime.py`): có planner chỉ thấy manifest, chạy song song theo DAG. Cũng đang ở 0%.
- **Kiểm tra:** có lưới agent giám định đa miền (bảo mật, dữ liệu, nội dung, UX, harness) và workflow `review-da-mien`, nhưng đây là file prompt, không phải kiểu agent khai báo.
- Engine CLI có công cụ `Task` sinh agent con tự nhiên khi chat.

Thiếu:
- Không có khai báo "loại việc" (khám phá, thực hiện, kiểm tra) trên agent, nên không ép được "khám phá thì chỉ đọc".
- Phạm vi công cụ nằm ở bước workflow (`tools:`) chứ không ở agent. Cùng một agent chạy ở hai nơi có thể có hai phạm vi khác nhau, không ai nhìn một chỗ mà biết hết.
- Chưa có quy ước "chỉ gửi kết quả cần thiết về bàn chính": kết quả bước trước được truyền qua `{{prev}}` nguyên văn.
- Các đường nâng cao (replan, khám phá song song, workflow dạng đồ thị có checkpoint) đã viết xong nhưng đều ở 0%.

### 3.5 Skill có sẵn

Có gì:
- Sáu skill hệ thống có mặt ở cả 61 brain, tự cập nhật theo app: `joyce-builder`, `ingest-source`, `lint-wiki`, `notes`, `query-wiki`, `html-to-webcake`. Cộng `cham-diem-tuong-phan` (61 brain) và `h2o-y-tuong` (47 brain).
- Skill nghiệp vụ theo phòng, ví dụ `h2o-studio-ketoan-chi-kiem-soat`: có mục Vai trò, Kích hoạt, Quy trình, Đầu ra, Guardrail. Mẫu tốt.

Thiếu:
- Tổng cộng 530 skill nhưng chỉ 54 tên khác nhau. Khoảng 41 skill nghiệp vụ mỗi cái chỉ có ở một phòng. Phần lớn phòng chỉ có một skill nghiệp vụ.
- Skill nghiệp vụ ngắn (ví dụ skill chi chỉ 1.326 byte), chưa có ví dụ đầu vào đầu ra mẫu và mục "bẫy thường gặp" mà `joyce-builder` khuyến nghị.

### 3.6 Memory

Có gì:
- Cấu trúc: `memory/MEMORY.md` (chỉ mục nạp sẵn mỗi lượt), `memory/facts/*.md` (một sự kiện một file), `memory/conversations/YYYY-MM-DD.md` (nhật ký thô), và bộ nhớ riêng từng agent `memory/agents/<slug>/MEMORY.md`.
- **Điều khiển của người dùng** (`server/memory_control.py`): xem, sửa, quên (giữ dấu vân tay để vòng học không dựng lại), tắt học theo brain.
- **Tự học an toàn** (`server/learn.py`): nhánh học CHỈ ĐỌC, trả về một manifest JSON, chỉ Python tin cậy mới ghi. Có quét bí mật và quét chèn lệnh trước khi ghi, giới hạn tần suất cứng, chỉ tự ghi khi brain là kho git.
- **Bài học agent theo "model đề xuất, code ghi"**: agent phát dòng `JOYCE_LESSON: ...`, ứng dụng bóc ra, xếp chờ chủ duyệt rồi mới ghi (tối đa 15 dòng mới nhất, khử trùng).
- Nạp bộ nhớ vào prompt: hồ sơ cá nhân, MEMORY.md, chỉ mục wiki (tối đa 8.000 ký tự). Truy xuất có nguồn dưới Adaptive Runtime: tối đa 6 mục, độ tin cậy từ 0,38.

Thiếu (về dữ liệu, không phải cơ chế):
- 54 trên 61 brain có chỉ mục bộ nhớ trống. Chỉ Brain Default có 36 mục.
- 48 file bộ nhớ agent đã được tạo nhưng 0 bài học thật. Chỉ có 1 file nhật ký chạy.
- Chỉ 7 brain có thư mục `facts` có nội dung.

Hiểu đúng: các phòng chưa chạy việc thật nên chưa có gì để nhớ. Không phải lỗi cơ chế, nhưng cho thấy vòng "làm việc rồi học" chưa quay.

### 3.7 System prompt

Có gì:
- `build_system_prompt` trong `main.py` lắp theo lớp: `CLAUDE.md` (31.362 byte ở gốc), hồ sơ cá nhân, bộ nhớ dài hạn, tắt học (nếu có), chỉ mục wiki, khối phòng ban H2O, hướng dẫn dự án, danh sách skill, lớp agentic, khối kênh hội thoại và khối ngôn ngữ.
- Có ngân sách và test (`test_prompt_budget.py`, `test_ba_loi_tran_prompt.py`). Hai hằng số trần của Antigravity được giữ khớp nhau bằng test.
- Prompt agent: thân file agent, khối bộ nhớ và luật `JOYCE_LESSON` chèn vô điều kiện, thêm câu nói rõ đang trò chuyện chứ không phải một bước quy trình.
- Mỗi brain phòng có `CLAUDE.md` riêng (6.205 byte, giống `AGENTS.md`).

Thiếu:
- Prompt gốc lớn nên giá trị cố định mỗi lượt cao nếu mức tiết kiệm bị tắt (khoảng 8.900 token trên brain mẫu).
- Chưa có phiên bản hóa và đo chất lượng prompt theo thay đổi (chỉ đo kích thước).

### 3.8 Hooks

Có gì (`server/plugins_host.py`):
- Hai sự kiện quanh MỌI lời gọi tool, ở mọi engine: `pre_tool_call` và `post_tool_call`.
- **`pre_tool_call` chặn được và sửa được tham số:** trả `{"deny": "lý do"}` thì tool không chạy và model nhận đúng lý do, trả `{"args": {...}}` thì thay tham số. Hook ném lỗi thì tool vẫn chạy (fail-open có chủ ý). Hook đầu tiên nói `deny` thắng.
- Cả hai hook nhận `turn` (kênh, người gửi, nhóm hay riêng, có phải chủ): hook biết ai đang nói. Lời gọi bị chặn vẫn bắn `post_tool_call` để kiểm toán thấy đủ.
- Thêm `chatbot_turn_context`: mỗi lượt bot khách có thể thêm đúng một dòng ngữ cảnh vào prompt, hết thời gian chờ 2 giây thì bỏ qua.

Thiếu:
- **Không có hook bảo vệ nào chạy sẵn.** Trong 24 plugin đi kèm, chỉ `tool-audit` dùng hook (chỉ đếm sau khi gọi, manifest tắt mặc định).
- Chưa có hook mẫu cho các rủi ro đã biết: ghi ra ngoài brain, xóa hàng loạt, gửi tin Zalo hàng loạt, chi tiền vượt hạn mức.
- Hook mới chỉ có hai sự kiện công cụ. Chưa có sự kiện đầu lượt, cuối lượt, trước nén, khi lỗi (đối chiếu với Claude Code có nhiều sự kiện hơn).
- Đối chiếu các slide "Pre-tool hook, Post-tool hook, Cách giao tiếp với hook, Gắn quy định công ty": hai nửa đầu Joyce đã có (pre chặn, cho qua hoặc sửa đầu vào; post quan sát để ghi log và kiểm toán). Nửa sau chưa có: bài giảng nói hook nhận JSON và trả exit code để gắn kiểm tra mà không sửa phần lõi, còn hook Joyce là hàm Python trong plugin nên muốn gắn quy định công ty (bảo mật, kiểm toán, tuân thủ) bằng script riêng thì vẫn phải viết plugin.

### 3.9 Phân quyền

Có gì:
- **Ba mức quyền** theo phiên: đọc (readonly, ứng với `suggest`), an toàn (safe, `auto`), đầy đủ (full). Với Codex ánh xạ sang `--sandbox read-only`, `workspace-write`, và không rào.
- **Kiểm từng lời gọi** `mcp_hub._guard`: phân loại đọc, ghi, nguy hiểm theo luật của connector và theo cả tham số, đối chiếu quyền của kết nối với mức của phiên, giới hạn tần suất theo kết nối (chống spam và khóa tài khoản). Tool ghi bị ẩn ngay lúc LIỆT KÊ ở mức Chỉ đọc.
- **Nhật ký kiểm toán** `jsonl`, xoay vòng ở 5 MB, chỉ ghi TÊN tham số không ghi giá trị, có chẩn đoán lỗi để model không đổ nhầm cho hub.
- **Việc nền bị khóa kỹ:** danh sách cho phép từng lời gọi bằng `can_use_tool` ở engine SDK, kiểm toán từng lần, cấm Bash, WebFetch, WebSearch, Task, MCP rỗng.
- **Bot khách hàng** không được dùng 12 công cụ gốc (`BOT_CAM_NATIVE`) và 4 tool chỉ của chủ (`joyce_reply_policy`, `joyce_reply_policy_tune`, `joyce_team`, `joyce_memory`).
- **Nhân viên** bị khóa vào phạm vi phòng của họ (`_STAFF_SCOPE`), việc ghi sổ Shop qua `joyce_shop` phân quyền theo vai.
- Plugin: tên tool bị khóa, `min_mode` ép giống tool ghi file, plugin người dùng bật tắt bằng cờ môi trường.

Thiếu:
- Quyền chỉ ở cấp phiên và cấp kết nối, chưa ở cấp agent (liên quan lỗ hổng 1).
- Đối chiếu các slide quyền: ba phạm vi (chỉ xem, thao tác trong khu vực được giao, toàn quyền) Joyce đã có qua ba mức readonly, safe, full. "Cùng công cụ, khác cách dùng" cũng có: `mcp_catalog.classify` phân loại theo cả tham số của từng lời gọi, tool cổng gộp nhiều lệnh con thì lấy mức nặng nhất, thiếu tham số quyết định thì coi là nguy hiểm (fail-closed). "Khu vực được giao" là brain của phòng, phạm vi nhân viên (`_STAFF_SCOPE`) và thư mục làm việc của tab Code.
- Điểm chưa giống bài giảng: ở mức full mọi thao tác chạy thẳng (`allowed()` trả đúng ngay), ở mức thấp hơn thì bị chặn kèm câu "bảo người dùng nâng quyền". Không có trạng thái thứ ba "tạm dừng, giải thích lý do, chờ chủ đồng ý" cho một thao tác cụ thể. Đây cũng là quyết định có chủ ý của chủ ngày 2026-09-10 (bỏ luật "tiền, đơn, đăng bài, nhắn tin không bao giờ giao tự động"), nên cần chủ quyết trước khi đổi, xem mục 3.13.
- Trên Docker, `JOYCE_CODEX_SANDBOX=off` làm mức `suggest` không còn gì chặn Codex ghi file (ghi chú rõ trong `claude_cli.py`).
- Chat tương tác ở mức Đầy đủ với Claude Code chạy `bypassPermissions`: an toàn dựa vào mức quyền của phiên chứ không hỏi từng lệnh.

### 3.10 Nhật ký chỉ ghi thêm, khôi phục và replay

Tương ứng các slide "Nhật ký chỉ được ghi thêm, không được xóa", "Đầu bếp vắng mặt, nhật ký vẫn còn", "Replay" và "Bộ nhớ độc lập với harness".

Có gì:
- **Lịch sử chat là nguồn sự thật** trong SQLite (`server/sessions.py`, `conversations.py`). Adaptive Runtime coi bản ghi này là gốc, trạng thái hội thoại chỉ là bản chiếu dựng lại được (`conversation_state.py`).
- **Nhật ký kiểm toán hub** là file `jsonl` chỉ ghi thêm, ghi ngay mỗi lời gọi. Nhật ký việc Kanban `task_events` ghi sự kiện của từng việc (ví dụ `reclaimed`).
- **Checkpoint Task State mã hóa, chỉ ghi thêm** trong `runtime.db` (đường thích ứng).
- **Khôi phục sau khi máy chủ chết:**
  - Việc Kanban có lease 90 giây và nhịp tim, `reclaim_stale` lấy lại việc của worker đã chết và ghi sự kiện `reclaimed`.
  - Nhóm chat có `TeamRunner.recover`: lượt chưa tới mốc gọi engine thì chạy lại, đã qua mốc thì tính một lần, đánh dấu `interrupted`, chặn việc và đưa nút "Chạy lại bước", không tự chạy lại để khỏi làm trùng việc đã ghi ra ngoài.
  - Lượt chat là việc của máy chủ nên F5 hay đóng tab không hủy việc.
  - Workflow đồ thị có checkpoint (`workflow_runtime.py`: node đã xong không chạy lại, node ghi không tự chạy) nhưng `workflow_canary` đang ở 0%, nên workflow thật vẫn chạy bằng bộ chạy cũ.
- **Bộ nhớ độc lập với harness:** phiên, tóm tắt nén, bộ nhớ brain đều lưu riêng ngoài engine. Đổi engine giữa chừng thì lịch sử được nạp lại (`compaction.seed_messages`, `bootstrap_prompt`), engine CLI nối lại mạch bằng id phiên riêng.

Thiếu:
- **Lịch sử chat không phải nhật ký chỉ ghi thêm.** `sessions.py` có `DELETE FROM messages` và `UPDATE messages SET content` (dùng cho sửa, chạy lại, xóa phiên), `conversations.py` xóa tin cũ theo hạn giữ. `task_events` và `task_runs` bị xóa khi xóa việc. Bằng chứng runtime xóa theo `retention_days` (mặc định 14 ngày).
- **Nhật ký kiểm toán chỉ giữ khoảng 10 MB:** xoay vòng ở 5 MB và bản `.jsonl.1` cũ bị ghi đè lần xoay sau. Nhật ký chỉ có tên tham số, không có giá trị, nên không đủ để dựng lại một lời gọi (có chủ ý về riêng tư, nhưng cũng nghĩa là không replay được).
- **Replay thật chưa có.** Khôi phục hiện nay là "chạy tiếp từ bước dở" ở vài chỗ rời rạc, chưa có một nhật ký sự kiện chung của một lượt agent để đọc lại từ đầu đến cuối.
- Mọi đường khôi phục tốt hơn (workflow checkpoint, replan) đều đang ở 0%.

### 3.11 Prefix caching và thứ tự prompt

Tương ứng các slide "Prefix caching", "Phần tĩnh đặt trước, phần động đặt sau", "Chèn dòng ở đầu, phải xử lý lại", "Nội quy đã quen, ghi chú cần đọc kỹ".

Có gì:
- **Thứ tự đúng nguyên tắc.** `build_system_prompt` xếp từ ổn định đến thay đổi: CLAUDE.md, hồ sơ, bộ nhớ, chỉ mục wiki, khối phòng ban, dự án, lớp agentic, chỉ mục năng lực, router skill, rồi cuối cùng khối "Bây giờ" và khối ngôn ngữ và khối "Mức dùng hôm nay". Phần động đã nằm cuối.
- **Đánh dấu cache cho Anthropic** (`engine.py::_apply_anthropic_cache`): dấu `cache_control` lên system và 3 tin cuối, TTL 5 phút hoặc 1 giờ. Qua OpenRouter với model Claude thì đánh dấu system. OpenAI và Gemini tự cache.
- **Có đo.** `server/usage_index.py` tính `cache_hit` và có gợi ý "Cache hit thấp" khi dưới ngưỡng.

Số đo thật từ `usage_index.db` trên máy này (28/10/2026), tính bằng đọc cache chia tổng token vào:

| Nguồn | Lượt | Tỉ lệ cache |
|---|---|---|
| Claude Code qua Joyce (chat) | 219 | 84% |
| Claude Code qua Joyce (việc nền) | 760 | 73% |
| Claude Code qua Joyce (chung) | 979 | 76% |
| Codex qua Joyce | 7.879 | 96% |
| Claude Code chạy tay, không qua Joyce | 48.048 | 98% |
| Engine API qua Joyce | 24 | 0% |

Cách đọc: mẫu engine API chỉ có 24 lượt và toàn model mã nguồn mở (gpt-oss, qwen), có thể vì nhà cung cấp không báo token cache chứ chưa chắc là không cache được. Không kết luận từ số này. Còn số 76% của Claude Code qua Joyce thấp hơn rõ so với 98% của phiên làm việc thường, đáng điều tra.

Thiếu:
- **Dấu cache đặt trên cả system như một khối.** `_apply_anthropic_cache` biến chuỗi system thành MỘT khối text rồi gắn dấu cache lên khối đó. Đồng hồ (theo phút) và "Mức dùng hôm nay" (token đếm tăng sau mỗi lượt) nằm trong khối đó, nên mỗi lượt khối khác đi và phần system gần như không bao giờ trúng cache. Ghi chú trong `context_compiler.dong_ho` còn viết thẳng "system prompt của Joyce vốn đã đổi mỗi lượt", tức là đã biết và coi như chấp nhận được. Với bài giảng thì đây chính là kiểu "chèn dòng động vào phần đầu, phải xử lý lại, tốn thêm thời gian và tiền".
- **Cách sửa nhỏ:** tách system thành hai khối, khối tĩnh (tới hết router skill) mang dấu cache, khối động (giờ, ngôn ngữ, mức dùng) đứng sau không đánh dấu. Engine CLI thì giữ phần tĩnh ổn định và đưa phần động vào tin nhắn người dùng.
- Chỉ mục bộ nhớ và chỉ mục wiki nằm trong phần "tĩnh" nhưng đổi mỗi khi có ghi nhớ mới; chấp nhận được vì ít đổi, nhưng nên đặt sau các khối thật sự bất biến.

### 3.12 Lắp hướng dẫn đầu ca, chung cả chuỗi và riêng từng chi nhánh

Tương ứng các slide "Lắp ráp tờ hướng dẫn ở đầu ca", "Hướng dẫn đầu ca tại các chi nhánh", "Nội quy chung của cả chuỗi", "Chung công thức, riêng cách vận hành", "Nạp hướng dẫn đúng dự án".

Có gì:
- **Tầng 1, luật chung cả chuỗi:** `CLAUDE.md` ở gốc dự án (31.362 byte) là system prompt cho mọi lượt chat của Joyce.
- **Tầng 2, hướng dẫn của từng brain:** `CLAUDE.md` và `AGENTS.md` ở gốc mỗi brain (cùng nội dung, 6.205 byte) để Claude Code và Codex tự nạp khi chạy với thư mục làm việc là brain. `AGENTS.md` và `CLAUDE.md` được tạo cùng lúc để hai họ CLI đều thấy.
- **Tầng 3, khối riêng chi nhánh:** `_h2o_phong_block` thêm tên phòng, khối, thương hiệu (H2O hay ThuyH2O), tên Agent Trưởng Phòng, đường tới **brain chung chỉ đọc** (thương hiệu, bảng giá, quy trình chung) và trích chỉ mục bộ nhớ chung. Đây đúng là "chung công thức, riêng cách vận hành".
- **Tầng 4, khối theo cuộc trò chuyện:** hướng dẫn dự án và tài liệu gắn vào đúng cuộc chat.
- **Tầng 5, chính agent:** thân file agent, bộ nhớ riêng của agent và luật bài học.
- **Khóa mục hệ thống** (`KHOA_MAC_DINH`): nhân viên không đổi tên, xóa hay ghi đè `agents`, `skills`, `memory`, `CLAUDE.md`... của brain phòng bằng tay.

Thiếu:
- `CLAUDE.md` của từng phòng chỉ là lược đồ vault chung (ba lớp nguồn, wiki, bộ nhớ). **Chưa có luật nghiệp vụ riêng của phòng trong đó**; luật riêng nằm ở agent trưởng phòng và skill. Hậu quả: engine CLI khi chạy trong brain phòng chỉ nạp lược đồ vault, không nạp vai trò của phòng trừ khi agent được gọi.
- Chưa có tệp "nội quy chung của chuỗi" tách bạch, soạn một lần và tự rải xuống mọi phòng. Hiện phần chung nằm rải ở `CLAUDE.md` gốc và brain chung.

### 3.13 Dừng lại xin phép con người

Tương ứng các slide "Đổ nồi nước dùng: cần chủ quán đồng ý" và "Rõ việc tự làm, rõ việc cần con người".

Có gì (rời rạc):
- **Sổ Shop (`joyce_shop`):** chi của nhân viên từ 2.000.000 đồng trở lên nằm "chờ duyệt", chỉ chủ hoặc giám đốc duyệt được, trưởng phòng không tự duyệt chi của mình. Đây là cổng TRƯỚC khi ghi sổ, đúng tinh thần bài giảng.
- **Kanban:** việc có tác dụng ra ngoài (báo giá, động tiền, CRM) tự gắn `needs_approval` và risk cao bị ép vào cột Review. Nhưng việc đã CHẠY xong mới rơi vào Review, tức duyệt sau chứ không chặn trước.
- **Đường ghi có xác nhận** (`write_path_runtime.py`): vòng một chỉ lập đề xuất, người dùng gõ lại đúng mã xác nhận thì vòng hai mới chạy, lỗi mập mờ chuyển UNKNOWN và không tự thử lại. Đang ở 0%.
- **Workflow đồ thị:** node ghi dừng ở `WAITING_USER`. Đang ở 0%.
- **Vòng lặp mới tạo từ chat** mặc định `enabled: false` để chủ xem lại rồi mới bật.

Thiếu:
- Không có cổng chung "thao tác nguy hiểm trong chat thì dừng, giải thích lý do, chờ chủ bấm đồng ý". Mức full chạy thẳng, mức thấp hơn thì chặn.
- Ranh giới "việc tự làm" và "việc cần người" chưa được viết thành một bảng duy nhất mà cả chủ lẫn nhân viên đọc được.

Quyết định cần chủ: ngày 2026-09-10 chủ đã bỏ luật cũ "tiền, đơn, đăng bài, nhắn tin không bao giờ tự động" để Joyce tự hành động. Thêm cổng xin phép là đi ngược một phần quyết định đó, nên đề xuất ở mục 6 là **cổng tùy chọn theo từng loại thao tác**, mặc định tắt, chủ bật loại nào thì loại đó dừng lại hỏi.

### 3.14 Làm, kiểm tra, nhận kết quả, điều chỉnh, và kiểm tra theo loại việc

Tương ứng các slide "Làm, kiểm tra, nhận kết quả, điều chỉnh", "Mỗi loại việc cần cách kiểm tra phù hợp", "Test và giới hạn ghi bảo vệ công việc", "Lời nhắc và cơ chế cần phối hợp".

Có gì (`server/main.py`, bộ chạy workflow cũ và đường đồ thị dùng chung `_workflow_verdict`):
- Bước workflow khai `verify_agent` và `max_retries`. Agent làm xong thì một agent KHÁC kiểm, trả `{"pass": true/false, "reason", "fixes"}`. Chưa đạt thì agent làm nhận lý do và các chỉnh sửa rồi làm lại, tối đa `max_retries` lần.
- **Fail-closed:** không đọc được kết luận, hoặc agent kiểm lỗi, đều tính là CHƯA ĐẠT. Hết lượt thử vẫn chưa đạt thì bước HỎNG, output không chảy sang bước sau, quy trình dừng và nói rõ ở bước nào (`_verify_failed_message`).
- Bước engine báo lỗi được chốt là hỏng TRƯỚC khi vào vòng kiểm, để khỏi đốt thêm một lượt kiểm trên đầu ra rác.
- Ngoài workflow: agent giám định (bảo mật, dữ liệu, nội dung, UX, harness) cho việc cải tiến hệ thống; Kanban có cột Review; Sổ Shop tự kiểm luật (chống ghi trùng, hạn mức chi, hợp đồng chỉ có hoa hồng khi Đã ký) bằng code, không dùng model.

Đây đúng là "lời nhắc cộng cơ chế" của slide: lời nhắc nói nên làm gì (prompt agent), cơ chế phát hiện và ngăn lỗi (verify, `_LapGuard`, hạn mức chi, hook). Joyce có cả hai nhưng mỏng ở nửa sau.

Thiếu:
- **Chỉ 5 trong 239 file workflow dùng `verify_agent`** (năm quy trình bàn giao của H2O: lead sang sản xuất, nội dung sang lead, ngày chụp sang hậu kỳ, hậu kỳ sang bàn giao khách, chăm sóc sau dịch vụ). Phần còn lại, gồm cả ba workflow dùng chung, chạy một lượt không kiểm.
- **Một kiểu kiểm duy nhất: một agent khác đọc rồi phán.** Slide chia ba kiểu: đọc soát lỗi, so kết quả nhìn thấy (đúng, sai), tính toán đối chiếu. Joyce chưa có kiểu thứ hai và thứ ba cho việc nghiệp vụ. Ví dụ nên có: Sổ Shop tự đối chiếu "tổng thu trừ tổng chi bằng lãi gộp" và "lịch cọc khớp bảng giá" bằng tính toán; báo giá in ra thì so với bảng giá; ảnh chụp màn hình giao diện sau khi sửa. Đối chiếu số bằng code sẵn có ở Sổ Shop nhưng chưa là một bước kiểm có tên mà agent nào cũng gọi được.
- **Chat không có vòng này.** Model nói "xong" là xong, không ai chạy lại kiểm. Với việc code, tab Code có `run_command` chạy test nhưng không ép model phải chạy test trước khi báo xong.
- Chưa có "giới hạn ghi bảo vệ công việc" theo slide (test được khóa, agent không sửa test để cho qua). `KHOA_MAC_DINH` khóa brain phòng khỏi thao tác TAY của nhân viên, không khóa agent.

### 3.15 Bếp thử nghiệm riêng (sandbox), giới hạn dữ liệu và tài nguyên

Tương ứng các slide "Một căn bếp thử nghiệm riêng", "Giới hạn cả dữ liệu và tài nguyên" và sơ đồ SANDBOX (agent ở giữa, tới hệ thống, file, dữ liệu đều có dấu X chặn).

Có gì:
- **Sandbox của engine:** Codex có `--sandbox` read-only (suggest), workspace-write (auto), không rào (full); Docker tắt được bằng `JOYCE_CODEX_SANDBOX=off`. Claude Code SDK chạy `can_use_tool` kiểm từng lời gọi cho việc nền. Antigravity tự bỏ `--sandbox` vì xung đột chế độ in một lượt.
- **Cô lập thư mục:** mỗi phiên làm việc ghim `cwd` vào brain hoặc thư mục tab Code; `_safe_path` chặn thoát thư mục; nhân viên bị khóa vào phạm vi phòng; mỗi nhân viên có thư mục riêng `staff_workspaces/`; vùng nhận file chat `.staging` chỉ đọc và chỉ mở khi được cho phép.
- **Lệnh chạy có rào** (`server/run_command.py`): không qua shell, môi trường lọc trắng chỉ giữ vài biến (PATH, HOME, LANG, TEMP...) nên khóa API trong `.env` không lọt vào lệnh, có trần thời gian và output, có danh sách chặn cứng ở mọi mức kể cả full.
- **Việc nền bị khóa chặt:** không Bash, WebFetch, WebSearch, Task, MCP rỗng, trần 1 giờ (`JOYCE_BG_MAX_WALL_S`).
- **Giới hạn tài nguyên (nửa dưới của slide dữ liệu và tài nguyên):**
  - Sổ cái token mỗi phút dùng chung mọi nguồn (`quota_scheduler.py`), cộng với phần đang bay.
  - Giới hạn tần suất theo từng kết nối (chống spam và khóa tài khoản).
  - Học hạn mức token từ chính lỗi nhà cung cấp (`limit_learner.py`).
  - Trần 30 vòng tool, trần 8.000 ký tự mỗi kết quả, trần thời gian mỗi việc.
  - Ngân sách lượt mỗi ngày cho agent trong nhóm (`agent_budget`).
- **Giới hạn dữ liệu (nửa trên):** bot khách hàng không dùng được 12 công cụ gốc và các tool chỉ của chủ; hook `chatbot_turn_context` chỉ đưa vào đúng một dòng đã lọc; nhật ký kiểm toán chỉ ghi tên tham số.

Thiếu:
- **Không có "căn bếp thử riêng" theo nghĩa slide.** Sandbox hiện chặn việc nguy hiểm, nhưng không có bản sao brain hay bản sao sổ để agent thử rồi người duyệt kết quả mới đưa sang brain thật. Agent chạy ở mức đủ quyền là ghi thẳng vào brain thật. Brain không nằm trong git nên không hoàn tác được (xem mục 6, đề xuất 9).
- Việc thử ca nghiệp vụ của em ở bản 1.3.37 đến 1.3.38 phải tự dựng sổ sandbox bằng `JOYCE_STATE_DIR` và `BRAINS_DIR` riêng. Làm được vì app tách được hai thư mục đó, nhưng chưa có nút "chạy thử trong bản sao" cho người dùng.
- Trần chi phí theo agent hoặc theo phòng chưa có; `agent_budget` chỉ đếm lượt trong nhóm chat, không đếm tiền của việc Kanban hay workflow.
- Quyền đọc dữ liệu có vẻ chưa chia nhỏ theo thư mục con trong brain (em chưa kiểm từng đường): mức quyền chỉ chia đọc, ghi, nguy hiểm, chưa thấy kiểu "chỉ đọc wiki, không đọc nhật ký hội thoại".

### 3.16 CLAUDE.md và AGENTS.md, dùng coding agent làm nền, và công thức Agent = Model + Harness

Tương ứng các slide "CLAUDE.md/AGENTS.md" (hướng dẫn dự án, skills, hooks, kết nối công cụ), "Dùng coding agent có sẵn làm nền" và "The Core Equation".

Đối chiếu:
- **Công thức Agent = Model + Harness, "nếu không phải model thì là harness":** hệ thống đúng nghĩa này. Joyce không huấn luyện model nào; toàn bộ 154.000 dòng Python trong `server/` (cộng dashboard) là harness. Model đứng sau mười hai cổng thay được.
- **Dùng coding agent có sẵn làm nền, bổ sung phần của mình:** Joyce làm theo cả hai kiểu. Với ba engine CLI (Claude Code, Codex, Grok Build) cùng Antigravity thì lõi là chính CLI đó (vòng lặp, công cụ gốc, nén ngữ cảnh), Joyce chỉ bọc quyền, hub công cụ, bộ nhớ, và hệ agent. Với bảy engine API thì Joyce tự viết lõi (`server/engine.py`). Hai kiểu này là nguồn của mọi chênh lệch ở mục 5A.
- **Bốn ống nối của slide CLAUDE.md và AGENTS.md** trong Joyce:
  - Hướng dẫn dự án: `CLAUDE.md` gốc và của từng brain (tạo cùng `AGENTS.md`).
  - Skills cho việc thường làm: 530 skill trong brain, đồng bộ ra `.claude/skills` cho CLI tự thấy.
  - Hooks kiểm tra tự động: plugin `pre_tool_call` và `post_tool_call`, hiện chưa dùng cho bảo vệ.
  - Kết nối công cụ: MCP Hub, mọi engine cùng một cửa.
  Cả bốn ống đều có. Ống yếu nhất là hooks (mục 3.8). Ống chưa chuẩn nhất là hướng dẫn dự án: `CLAUDE.md` của phòng chỉ là lược đồ vault chung (3.12).
- Một điểm bài giảng không nhấn nhưng Joyce vướng: hai file `CLAUDE.md` và `AGENTS.md` ở brain là bản sao y hệt nhau (6.205 byte) nên sửa một nơi phải nhớ sửa nơi kia, trong khi `meta_tools` tạo cả hai cùng lúc. Nên một file là nguồn, file kia sinh ra.

## 4. Harness của các phòng ban (61 brain)

Số liệu quét ngày 2026-10-28, chỉ đọc, không sửa gì trong `brains/`.

| Chỉ số | Giá trị |
|---|---|
| Số brain | 61 (14 brain khối, 43 phòng có Agent Trưởng Phòng, 4 brain cá nhân hoặc chung) |
| Tổng agent | 600, nhưng chỉ 59 tên khác nhau |
| Agent là bản sao dùng chung | 549 (9 agent nhân vào cả 61 brain) |
| Tổng skill | 530, chỉ 54 tên khác nhau, khoảng 41 skill chỉ có ở một phòng |
| Tổng workflow | 239, chỉ 13 tên khác nhau (3 workflow dùng chung nằm ở cả 61 brain) |
| Agent có ghi `skills` rỗng | 490 trên 600 |
| Agent có đặt `model` | 50 trên 600 |
| Agent có mục Bối cảnh, Quy trình, Cấm | 410, 471, 427 |
| Brain có chỉ mục bộ nhớ không trống | 7 trên 61 |
| File bộ nhớ agent, có bài học thật | 48, và 0 |

Chín agent dùng chung ở mọi brain: năm giám định (`giam-dinh-bao-mat`, `-du-lieu`, `-noi-dung`, `-ux`, `-harness`), `ky-su-harness`, `giam-sat-dai-tu`, `ke-toan-vien-dai-tu`, `tro-ly-onboarding`. Ba workflow dùng chung: `dai-tu-codebase`, `review-da-mien`, `tu-cai-tien-agent`. Chúng là bộ "lưới review" cho việc cải tiến hệ thống, không phải việc của một phòng nghiệp vụ.

Đối chiếu slide "Mỗi agent có phạm vi riêng":

| Thuộc tính của slide | Phòng ban hiện tại |
|---|---|
| Phiên làm việc riêng | Có. Mỗi phòng có brain riêng, bộ nhớ riêng, và agent chat riêng theo khóa `dm:<agent_key>` |
| Lời dặn tập trung | Có ở Agent Trưởng Phòng (mục Bối cảnh, Nhiệm vụ, Cấm) |
| Công cụ bị giới hạn | CHƯA ở cấp agent. Chỉ giới hạn ở bước workflow hoặc việc Kanban |

Nhận xét:
- Hạ tầng cho 44 phòng H2O đã dựng đủ khung (brain, trưởng phòng, một skill nghiệp vụ, workflow chung). Chỗ thiếu là **ruột nghiệp vụ**: mỗi phòng nên có thêm vài skill thật và workflow thật cho việc hằng ngày.
- 14 brain khối (Ban Hang, Ke Toan, CSKH, Nhan Su, San Xuat, Marketing, Nghien Cuu, ThuyH2O, Truyen Thong, Ve Sinh, Van Thu, H2O Studio, ThuyH2O Studio, Kien Thuc Kinh Doanh Tham Khao Ngoai) chỉ có 9 agent dùng chung, chưa có agent điều phối khối.
- Sổ Quản lý Shop (bản 1.3.37) là ví dụ tốt nhất của agent có việc thật. Việc ghi sổ đi tới đúng Agent Trưởng của Sales Hình Ảnh, Phòng Thu, Phòng Chi, Đối Soát và Nhân Sự Vận Hành: việc ghi sổ đi qua `joyce_shop` và chạy bằng luật cố định, chỉ giao agent khi cần phán đoán.

## 5. Trạng thái cấu hình thật trên máy (28/10/2026)

Đọc từ `settings.json`, phần `context_runtime`:

| Đường | Mức hiện tại | Ý nghĩa |
|---|---|---|
| Chế độ chung | `canary` | Có đường đang chạy thật |
| Fast path (capsule gọn, không tool) | 100% | Câu hỏi chat thuần gửi gọn |
| Conversation state | 100% (chỉ engine API) | Trạng thái hội thoại có cấu trúc |
| Memory (truy xuất có nguồn) | 100% | Chỉ nạp mục bộ nhớ liên quan |
| Lazy skill | 100% | Nạp thân skill khi cần |
| Đọc một bước (readonly) | 0% | Chưa bật |
| Khám phá nhiều vòng (orchestrator) | 0% | Chưa bật |
| Workflow đồ thị có checkpoint | 0% | Chưa bật |
| Agent tự lập lại kế hoạch | 0% | Chưa bật |
| Chọn model theo bước | 0% | Chưa bật |
| Ghi có xác nhận (write) | 0% | Chưa bật |

Nghĩa là: phần tiết kiệm token đã chạy thật. Phần "agent con thông minh" (khám phá, replan, workflow có checkpoint, ghi có xác nhận) đã được viết và có test nhưng chưa được bật cho việc thật.

## 5A. Ví dụ thực tế: "sửa lỗi nút đăng nhập không bấm được"

Chạy thử bài giảng qua harness của Joyce. Đây là phần đọc code, chưa chạy thật một tác vụ sửa lỗi. Ba môi trường để so: (1) engine CLI Claude Code ở tab Code, (2) engine API ở tab Code có thư mục làm việc (não chính hiện tại trên thanh trên cùng của anh là Z.ai glm-4.7-flash, nghĩa là thuộc nhóm này), (3) engine API trong chat thường không có thư mục làm việc.

| Bước trong bài giảng | (1) Claude Code | (2) API ở tab Code | (3) API chat thường |
|---|---|---|---|
| Nạp hướng dẫn đúng dự án | CLI tự nạp CLAUDE.md và AGENTS.md ở thư mục làm việc | Chỉ system prompt của Joyce, không tự nạp CLAUDE.md của dự án code | Chỉ system prompt của Joyce và brain |
| Tìm code, đọc file, tìm lỗi | Grep, Read, Glob gốc | `joyce_run_command` (grep, rg, find, cat) và `joyce_read_file` | Chỉ đọc file trong brain, không thấy code |
| Giao việc cho agent con | Công cụ `Task` | Không có. Chỉ có Kanban và workflow, nặng và chạy nền | Không có |
| Kiểm tra quyền trước khi chạy | Mức quyền của phiên (mức full chạy thẳng) | Hub `_guard` và ba mức của `run_command`, lệnh phá hoại chặn cứng ở mọi mức | Hub `_guard` |
| Hooks và quy định môi trường | Không có hook Joyce nào bật sẵn | Như bên trái, chỉ còn rào đường dẫn và danh sách lệnh | Như bên trái |
| Sửa rồi chạy kiểm thử | Bash chạy pytest, Edit sửa đoạn | `joyce_write_file` ghi cả file rồi `run_command` pytest ở mức `auto` | Không chạy được lệnh |
| Lỗi thì quay lại sửa | Vòng lặp của CLI | Trần 30 vòng, `_LapGuard` chỉ bắt gọi lặp y hệt | Như bên trái |
| Ghi diễn biến | Bản ghi của CLI và tin chat trong Joyce | Tin chat, nhật ký hub chỉ có tên tham số | Như bên trái |
| Dọn context | CLI tự nén | Cắt từng kết quả ở 8.000 ký tự, KHÔNG dọn kết quả cũ trong lượt | Như bên trái |
| Đúng kết quả, đúng yêu cầu | Model tự báo cáo | Model tự báo cáo, chỉ có kiểm tra lời hứa suông | Như bên trái |

Đọc bảng:
- **"Tay nghề giống, môi trường khác" đúng với Joyce.** Cùng một model nhưng cột (1) có đủ công cụ, hướng dẫn và kiểm thử, cột (3) gần như không làm được việc code. Với việc code, anh nên chọn engine CLI hoặc mở tab Code, đừng giao cho não chính là API miễn phí.
- **Điểm yếu nặng nhất của cột (2)** là bước "dọn context": một vòng sửa, chạy pytest, đọc lỗi lặp nhiều lần dễ chất đầy bàn (tối đa 30 vòng, mỗi kết quả 8.000 ký tự, tức khoảng 240.000 ký tự). Và bước "kiểm tra cuối" không có người hay máy độc lập xác nhận.
- Server có một lớp kiểm tra nhỏ: phát hiện câu hứa suông kiểu "tôi sẽ báo lại" rồi so với việc nền thật, nếu rỗng thì nối thêm dòng đính chính. Đó là mầm của bước "đúng kết quả, đúng yêu cầu", mới dừng ở lời hứa chứ chưa kiểm kết quả.

Ví dụ nghiệp vụ, chạy thật trong sandbox ở bản 1.3.37 (câu "hợp đồng Tuấn Thủy 0899252392, gói chụp 15 triệu, thu 15tr, chi 4tr setup"): đây là "một yêu cầu, cả quá trình phía sau" chạy tốt vì harness làm hộ phần khó. Tool `joyce_shop` tách thành ba sự kiện, tìm khách theo số điện thoại để không tạo trùng, chống ghi hai lần trong 10 phút, chuyển hợp đồng sang Đã ký khi nhận cọc, chi của nhân viên vượt hạn mức thì dừng chờ chủ duyệt, mỗi bước ghi vào nhật ký hoạt động và hiện trên văn phòng ảo, kết quả đối chiếu được bằng số trong sổ. Việc nghiệp vụ có sẵn "đủ công cụ, ngữ cảnh và kiểm tra" như bên phải của slide cuối. Việc code thì chưa bằng.

## 5B. Lõi có sẵn cộng phần chủ bổ sung, và tìm cái thiếu trước khi đổi model

Hai slide cuối của bài giảng: harness gồm lõi có sẵn (model, công cụ, context, vòng lặp) cộng phần mình bổ sung theo công việc; và khi kết quả kém thì tìm phần đang thiếu (hướng dẫn rõ, công cụ, kiểm tra) trước khi nghĩ tới đổi model.

Joyce đặt vào khung đó:

| Lớp | Lõi có sẵn (app và engine) | Phần chủ bổ sung |
|---|---|---|
| Model | 12 bộ não, đổi ở trang Models | Chọn não chính, đặt model riêng cho agent (50 trên 600 agent có đặt) |
| Công cụ | Hub, 24 plugin đi kèm, tool lõi | Kết nối MCP, plugin riêng, skill nghiệp vụ |
| Context | Nén hội thoại, Adaptive Runtime | CLAUDE.md của brain, MEMORY.md, wiki, dự án |
| Vòng lặp | Vòng của engine, phanh lặp, trần 30 vòng | Workflow, loop, nhắc hẹn, việc Kanban |
| Hướng dẫn | System prompt gốc (31 KB) | Agent trưởng phòng, skill, nội quy phòng |
| Kiểm tra | Ba mức quyền, kiểm từng lời gọi | Hook (hiện 0 cái bật sẵn), agent giám định, duyệt chi |

Cái thiếu của Joyce theo đúng ba nhóm của slide:
- **Thiếu hướng dẫn và ngữ cảnh:** 54 trên 61 brain có bộ nhớ trống, CLAUDE.md của phòng chỉ là lược đồ vault chung, 490 trên 600 agent không gán skill nào.
- **Thiếu công cụ:** engine API trong chat thường không có công cụ chạy lệnh, không sửa từng đoạn file, không có Task. Việc code chỉ đủ đồ nghề ở engine CLI.
- **Thiếu kiểm tra:** vòng kiểm chứng có sẵn nhưng chỉ 5 workflow dùng (xem 3.14), chat không có bước kiểm cuối, không có bộ ca thử cho từng phòng, không có hook bảo vệ nào bật sẵn.

Hệ quả cho cách làm việc: Joyce đổi model rất dễ (một cú bấm ở trang Models), nên dễ phản xạ "kết quả kém thì đổi não". Ghi nhận ở đây thứ tự chẩn đoán đề xuất khi một agent làm sai việc: (1) có đọc đúng ngữ cảnh chưa (brain chung, bộ nhớ, wiki)? (2) có đủ công cụ trong phạm vi quyền chưa? (3) có bước kiểm kết quả chưa? Chỉ khi cả ba đủ mà vẫn kém mới đổi model.

Lưu ý lời hứa "năng lực của Joyce không đổi theo model" trong CLAUDE.md đã nói đúng các ngoại lệ (chỉ engine CLI có shell, WebFetch, Task và nối lại phiên). Nhưng mục 5A cho thấy chênh lệch thực tế ở việc code còn lớn hơn lời hứa đó gợi ý.

## 6. Đề xuất lộ trình xây harness riêng cho Joyce

Tất cả là ĐỀ XUẤT, chưa làm. Xếp từ rẻ và nhiều tác dụng đến lớn.

**Giai đoạn A: vá lỗ hổng lớn nhất, ít đụng lõi**
1. Mở rộng khuôn agent với các trường tùy chọn: `kind` (explore, execute, verify), `tools` (danh sách cho phép), `mode` (suggest, auto, full), `max_rounds`, `max_minutes`. Thiếu trường thì giữ hành vi cũ. Dùng đúng cơ chế khóa đã có ở workflow nền.
2. Một plugin hệ thống `guard` bật sẵn với `pre_tool_call` chặn các việc đã biết nguy hiểm: ghi ra ngoài brain, xóa hàng loạt, gửi tin hàng loạt, chi tiền vượt hạn mức khi người gọi không phải chủ. Fail-closed cho nhóm này (tự bắt lỗi rồi trả `deny`).
3. Tách system prompt thành khối tĩnh (có dấu cache) và khối động (giờ, ngôn ngữ, mức dùng) để lấy lại prefix caching ở đường API và đường Claude Code. Đo lại tỉ lệ cache trước và sau trên cùng bộ ca (mục tiêu: Claude Code qua Joyce từ 76% lên gần 95%).
4. Dọn ngữ cảnh trong lượt: khi tổng ký tự công cụ vượt ngưỡng thì thay kết quả cũ (trừ 2 đến 3 kết quả mới nhất) bằng một dòng tóm tắt. Thêm xử lý "ngữ cảnh quá dài": nén rồi thử lại một lần.

5. Cổng xin phép tùy chọn theo loại thao tác (gửi tin hàng loạt, ghi tiền, xóa, đăng bài), mặc định tắt: thao tác thuộc loại đã bật thì tạm dừng, nêu lý do và đối tượng bị tác động, chờ chủ bấm đồng ý. Dùng lại cơ chế `WAITING_USER` và mã xác nhận đã có sẵn.
6. Bộ chuyển hook ngoài: cho khai báo hook là lệnh (JSON vào, exit code ra) trong một file cấu hình, để chủ gắn quy định công ty (kiểm toán, tuân thủ) mà không viết plugin.

**Giai đoạn B: làm cho phòng ban có ruột**
7. Chuyển chín agent dùng chung thành agent hệ thống như skill hệ thống (một bản ở app, tự cập nhật), bỏ 549 bản sao. Cần cẩn thận vì `brains/` không có git.
8. Thêm agent điều phối cho 14 brain khối.
9. Mỗi phòng thêm 2 đến 3 skill nghiệp vụ thật kèm ví dụ vào ra và mục bẫy thường gặp, bắt đầu từ các phòng đang chạy việc thật (Sales, Thu, Chi, Đối soát, Nhân sự).
10. Ghim mục không được nén (số tiền, mã hợp đồng, quyết định của chủ) vào tóm tắt, kèm test "hỏi lại sau nén".

**Giai đoạn C: đo và đóng gói**
11. Bộ ca thử cố định cho mỗi phòng (đầu vào, đầu ra mong đợi, mức quyền) để mỗi lần đổi prompt hay skill có số đo trước sau.
12. Bật dần các đường đang ở 0%: workflow đồ thị có checkpoint cho việc nền, replan có kỷ luật quyền, ghi có xác nhận cho Sổ Shop.
13. "Bác sĩ harness": khi một việc agent thất bại hoặc bị chủ sửa lại, tự gắn nhãn nguyên nhân gần nhất (thiếu ngữ cảnh, thiếu công cụ, thiếu kiểm tra, hay hết cách mới là do model) và hiện ở trang Việc, để chủ biết cần bổ sung gì trước khi đổi não. Dùng lại nhật ký hub và `task_events`, không thêm model nào.
14. Thêm hai kiểu kiểm tra còn thiếu thành bước dùng chung: "kiểm bằng tính toán" (đối chiếu số trong Sổ Shop: thu trừ chi, lịch cọc khớp bảng giá, bảng lương khớp hoa hồng) và "kiểm bằng so kết quả" (báo giá in ra so với bảng giá). Gắn `verify_agent` vào các workflow chạm tiền và hợp đồng, bắt đầu từ ba phòng Thu, Chi, Đối soát.
15. Bản sao thử cho agent: chế độ "chạy thử" tạo bản sao sổ và brain trong thư mục tạm, agent làm trên bản sao, người duyệt rồi mới áp sang bản thật. Làm được vì `JOYCE_STATE_DIR` và `BRAINS_DIR` đã tách; còn thiếu phần giao diện và bước áp.
16. Gom thành "lõi harness Joyce" độc lập engine: một vòng lặp, một bộ ngữ cảnh, một sổ hook, một bảng quyền, mọi engine và mọi agent đi qua.

## 7. Chưa kiểm tra được hoặc cần anh xác nhận

- Em chưa chạy bộ test đầy đủ để xác nhận từng tính năng ở trên còn xanh. Các nhận định dựa trên đọc code, đọc cấu hình thật và quét file brain.
- Chưa soi phần engine CLI bên trong (vòng lặp của Claude Code, Codex, Grok, Antigravity do chính CLI quản lý).
- Chưa tìm thấy xử lý lỗi "ngữ cảnh quá dài" trong `engine.py`. Có thể nằm ở `main.py` mà em chưa đọc hết (28.000 dòng).
- Chưa soi harness của bot khách hàng (`chatbot_runtime.py`, `chatbot_reply_policy.py`) và của kênh Zalo, Telegram. Đây là harness riêng đáng một bản kiểm tra thứ hai.
- Số liệu phòng ban là ảnh chụp lúc quét, sẽ lệch khi anh thêm agent và skill.
- Số đo cache lấy từ bảng `file_daily` trong `usage_index.db`: nó gom theo ngày, nên "lượt" là cột `turns` cộng lại chứ không phải từng yêu cầu. Chưa kiểm tra thực nghiệm việc chuyển dấu cache sang khối tĩnh có tăng tỉ lệ trúng hay không.
- Chưa xác minh vì sao Claude Code qua Joyce chỉ đạt 76% so với 98% khi chạy tay (nghi do system prompt đổi mỗi lượt, nhưng chưa thử).
- Câu hỏi cho anh: các agent dùng chung (`ke-toan-vien-dai-tu` ở cả 61 brain) tên là "kế toán viên" nhưng thực chất là bước lập kế hoạch đại tu codebase. Anh muốn đổi tên cho đúng nghĩa khi dọn bản sao không.

## Nhật ký cập nhật

| Ngày | Nội dung |
|---|---|
| 2026-10-28 | Bản đầu: chấm chín thành phần, quét 61 brain, đối chiếu cấu hình thật, đề xuất lộ trình |
| 2026-10-28 | Slide cuối: thêm 3.14 (làm, kiểm tra, điều chỉnh; kiểm tra theo loại việc), 3.15 (sandbox, giới hạn dữ liệu và tài nguyên), 3.16 (CLAUDE.md và AGENTS.md, coding agent làm nền, công thức Agent = Model + Harness). SỬA nhận định cũ: workflow CÓ vòng kiểm chứng (`verify_agent`), chỉ 5 trên 239 workflow dùng; thêm hai bước lộ trình |
| 2026-10-28 | Thêm mục 5B (lõi có sẵn cộng phần bổ sung, tìm cái thiếu trước khi đổi model) và bước lộ trình "Bác sĩ harness" |
| 2026-10-28 | Thêm mục 5A ví dụ thực tế (sửa lỗi nút đăng nhập, so ba môi trường) và sửa nhận định ở 3.3 về công cụ code của engine API |
| 2026-10-28 | Bổ sung theo các slide tiếp theo: nhật ký và khôi phục (3.10), prefix caching kèm số đo thật (3.11), lắp hướng dẫn nhiều tầng (3.12), xin phép con người (3.13), đối chiếu hook và quyền; thêm hai lỗ hổng và hai bước lộ trình |
