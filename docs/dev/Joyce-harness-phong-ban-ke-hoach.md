# Joyce Harness: kế hoạch tổng tổ chức agent, vá lỗi và nâng cấp

> **Trạng thái (cập nhật 28/10/2026): chủ yêu cầu triển khai theo plan. Gói G1 (FIX-01..05) ĐÃ LÀM ở 1.3.41, xem mục 3.3. G2 trở đi (JHA-06..12, compiler, ledger ngân sách, pilot) CHƯA làm. Phần còn lại của tài liệu giữ nguyên là kế hoạch; migration production và mở quyền từng phòng vẫn theo hồ sơ từng pilot.**
>
> Ngày audit: 2026-10-28. Baseline: Joyce OS **1.3.39**, commit `48cee2defdd7412aeb25c80e22aec8ff9335519e`.
>
> Bản này thay thế kế hoạch phòng ban trước đó tại cùng đường dẫn. Đã đọc lại đặc tả, rollout, schema, reference, prompt, acceptance, code liên quan và metadata trong 61 brain. Chỉ file kế hoạch này được cập nhật trong lượt chốt plan; không đổi runtime, quyền, model, agent, skill hay dữ liệu nghiệp vụ.
>
> Tài liệu đầu vào: [đặc tả](./Joyce-harness.md), [rollout](./Joyce-harness-rollout.md), [audit trước](./Joyce-harness-final-audit.md), [schema](./joyce-harness/contract.schema.json), [prompt mẫu](./joyce-harness/prompts.md), [acceptance](./joyce-harness/acceptance.md), [audit lịch sử](./Joyce-hardness.md).

## 1. Đề xuất điều hành

Mục tiêu là biến Joyce thành đầu mối quản trị có thể giao đúng việc, giữ đúng phạm vi, kiểm được kết quả và nhân rộng theo phòng mà không làm tăng số agent hoặc quota vô ích.

Đề xuất triển khai theo thứ tự:

1. **Khóa các lỗi còn lại của 1.3.39**, đặc biệt thay đổi quyền, eval và canary.
2. **Hoàn thành runtime harness 0B**: compiler, grant theo operation, ngân sách toàn cây và kết quả do host kiểm chứng.
3. **Chứng minh một luồng thật** ở Đối Soát chỉ đọc, sau đó Phòng Thu ghi vào sổ thử.
4. **Mở sáu phòng pilot**, cấp quyền theo bằng chứng của từng loại việc.
5. **Nhân theo 11 khối hiện có**, pin phiên bản và canary từng nhóm nhỏ.
6. **Tự cải tiến có điều kiện**, sau khi eval, sandbox và ngân sách thực thi đã hoạt động.

Joyce có harness điều phối riêng. Trưởng phòng dùng nền phòng ban và kiến thức nghề của khối/phòng, không sao chép quyền của Joyce. Phòng chỉ giao cho chuyên viên trong phòng khi được cấp; việc liên phòng báo lên Joyce để Joyce điều phối.

Bốn lựa chọn kiến nghị để anh duyệt cùng plan:

| Nội dung | Phương án kiến nghị |
|---|---|
| Thứ tự mở rộng sau pilot | Kế toán -> Bán hàng -> Nhân sự; các khối còn lại theo mức sẵn sàng dữ liệu và nhu cầu |
| Điều kiện cho model thực hiện nghiệp vụ | Chứng nhận theo loại việc + model/engine + harness revision; mọi cấu hình chưa có bằng chứng chỉ thử/soạn/đọc ở route pilot |
| Người duyệt quyền | Anh duyệt grant, phạm vi, effect, hạn mức và thay đổi ngân sách; người phụ trách nghiệp vụ duyệt SOP và đáp án ca thử |
| 14 brain không có agent riêng | Giữ làm brain khối/kho dùng chung; chỉ tạo agent khi có vai, việc và owner thật, không tạo hàng loạt |

Đây là kiến nghị, chưa phải thay đổi quyền hoặc quyết định mới đã được anh phê duyệt. Các quyết định anh đã chốt trước đây vẫn giữ, gồm trần cải tiến mặc định 500.000 token, có lý do thì tối đa 1.000.000, hai lượt mỗi target/tuần.

## 2. Hiện trạng đã đo lại và đính chính

Nguồn: metadata file agent/skill ở `brains/`, định nghĩa dùng chung ở `system/agents/`, registry thực `server/h2o_departments.json`. Không suy số phòng từ seed trong code vì seed chưa phản ánh hết registry hiện hành.

| Hạng mục | Kết quả audit lần này | Hệ quả cho kế hoạch |
|---|---|---|
| Tổ chức | 2 thương hiệu, 11 khối, 44 phòng trong registry | Không đổi tổ chức thành 7 khối; 7 nhóm nghề chỉ có thể là nhóm template |
| Brain | 61 brain | Brain không đồng nghĩa phòng |
| Agent riêng | 51 file agent trong brain; cả 44 phòng đều có agent riêng | Không cần tạo lại bộ trưởng phòng |
| Agent dùng chung | 9 định nghĩa dùng chung; 8 scope hệ thống, Onboarding scope phòng | Giữ mô hình 1.3.39 đã làm |
| Brain Default | 4 agent riêng + 9 agent dùng chung | Giải thích đúng con số 13; Joyce Core là entrypoint hệ thống riêng |
| Khung prompt | 44/51 có cùng bộ 6 tiêu đề | Chưa đủ kết luận chúng giống toàn bộ nội dung; cần đánh giá quy tắc nghề và hành vi |
| Skill đã gắn | 47/51 có skill ngoài `h2o-y-tuong`; 2 chỉ có skill ý tưởng; 2 không khai skill | Nhận định “46/51 chỉ gắn h2o-y-tuong” trong bản tổng hợp không đúng với file hiện tại |
| Skill phòng ban | 43/44 phòng có khai skill ngoài ý tưởng; **Sales Makeup** là phòng còn thiếu | Sửa đúng một khoảng trống đã xác định, không nối lại toàn bộ |
| Tên skill có file | Mọi skill được agent tham chiếu đều tìm thấy file tương ứng trong brain | Còn phải kiểm runtime có nạp và agent có sử dụng đúng không |
| Kho skill | 54 slug khác nhau, trong đó 46 bắt đầu `h2o-`: 45 ngoài skill ý tưởng và 1 skill ý tưởng | Không gọi cả 46 là 46 skill nghề độc lập |
| Khai harness/quyền riêng | 0/51 file khai các khóa `tools/allowed_tools/allowed_effects/harness` | Quyền theo phiên chưa tương đương quyền theo từng agent |
| Nội quy phòng | 0/61 có `Joyce/noi-quy.md` | Cần tạo luật có nguồn, không suy ngưỡng tài chính từ ví dụ |
| Eval hiện có | 1 file ở Brain Default, dành cho Giám định Harness | Đây là kiểm chuỗi bản nháp, chưa phải bộ behavioral eval cho 44 phòng |
| Model | qwen3:14b 18; sonnet 15; gpt-5.6-sol 10; grok-4.6 6; glm-4.7-flash 1; kế thừa 1 | Chưa benchmark nên không khẳng định model nào “yếu nhất” |

**14 brain không có agent riêng** gồm 11 brain khối và 3 kho: `H2O Studio`, `ThuyH2O Studio`, `Kien Thuc Kinh Doanh Tham Khao Ngoai`. Đây không phải 14 phòng chưa có trưởng phòng. Các brain này vẫn có thể thấy Onboarding và dùng entrypoint hệ thống.

Phân biệt ba mức skill: **đã khai -> đã nạp trong run -> đã dùng đúng và tạo kết quả đạt**. Lần audit này xác minh mức đầu và đường dẫn file; hai mức sau phải được đo bằng trace và eval.

### 2.1 Những gì 1.3.39 đã làm được

- Gom chín trợ lý dùng chung và giữ alias tên cũ.
- Phân biệt `None` và `[]` ở Claude SDK; `[]` không còn bật bypass tại đường đã được test.
- Check không nhận diện được trong bộ eval hợp lệ được tính là rớt.
- Factory đã thêm kiểm diff một số trường quyền.
- Có joyce-guard, tách prefix cache ở một số engine API, thu gọn tool output và khối Harness trên Sơ đồ.

**Không ghi “giai đoạn 0 hoàn tất toàn bộ”.** Vẫn chưa ghim đầy đủ trạng thái Sổ Shop qua compaction giữa lượt; chưa chứng nhận mọi route CLI; chưa ép trần token cải tiến; chưa đo lại cache thực tế theo từng engine. Các lỗi biên của diff/eval/canary dưới đây vẫn còn.

## 3. Audit kỹ thuật: lỗi xác minh và khoảng trống

Quy ước: **Tái hiện** là đã chạy hàm thật bằng input tổng hợp hoặc mock trong RAM; **Code** là kết luận từ nhánh code đã đọc; **Thiếu triển khai** là khoảng cách với đặc tả. Không có thử nghiệm gửi tin, ghi sổ thật hoặc khai thác tài khoản thật.

### 3.1 Backlog lỗi cần vá trước khi mở rộng

| ID | Ưu tiên, bằng chứng | Phát hiện | Đề xuất vá sau duyệt | Điều kiện nghiệm thu |
|---|---|---|---|---|
| JHA-01 | P0, tái hiện | `factory.diff_quyen` không thấy đổi `harness.budgets.max_tokens`; chuyển tools giữa hai bước workflow cũng trả `[]` | Parse YAML cấu trúc, so theo đường dẫn và node identity, không làm phẳng/sort mất quan hệ; subtree quyền/khóa lạ trong harness phải review | Nested budget, alias/anchor, đổi tools giữa node, thay kiểu dữ liệu đều bị phát hiện; sửa nội dung thuần vẫn hợp lệ |
| JHA-02 | P0, tái hiện | Eval JSON hỏng hoặc case thiếu `check` trả `None`, giống “không có bộ eval”; auto-apply chỉ chặn khi có `fails` | Loader trả trạng thái rõ: missing/invalid/valid; eval bắt buộc bị missing/invalid thì không áp. Không lọc bỏ case lỗi âm thầm | File hỏng, root sai, case thiếu trường, bộ trống bắt buộc và case vượt giới hạn phải báo lỗi, không biến thành pass |
| JHA-03 | P0, tái hiện cấp hàm | Guard chặn `sources/original.md` nhưng bỏ lọt `wiki/../sources/original.md` khi cùng đích | Chuẩn hóa đường dẫn trước kiểm policy, dùng chung resolver với write; xử lý case và symlink/junction theo OS | Mọi biểu diễn trỏ cùng file cho cùng kết quả; test thật chỉ trên vault tạm |
| JHA-04 | P0, tái hiện toàn hàm bằng filesystem giả | Canary promote ghi đè file ở brain đích đã được chủ sửa. Hash hiện chỉ kiểm nguồn | Snapshot hash từng đích; compare-and-swap, backup từng đích, skip conflict; rollback cũng kiểm version | Đích sửa sau snapshot được giữ nguyên, báo conflict; không nhân theo “cùng tên file” |
| JHA-05 | P1, tái hiện | Canary không có task nào vẫn promote khi hết giờ | Thêm đủ số task phù hợp và baseline theo revision; lỗi phải gắn trace, không tìm slug trong title | Không traffic thì không promote; canary có lỗi nghiêm trọng dừng ngay |
| JHA-06 | P0 với route nghiệp vụ, code | Guard lỗi thì fail-open; CLI native không đi qua hook hub | Tách check bắt buộc vào gate runtime; hook hỗ trợ có policy lỗi riêng. Lập matrix từng route, không bật route chưa giữ được bất biến | Lỗi mandatory guard làm operation bị chặn; wrapper, native tool và fallback không đi vòng |
| JHA-07 | P1, tái hiện | Tám output `joyce_shop` mỗi output 20.000 ký tự còn nguyên 160.000 ký tự, vượt ngưỡng 80.000 vì được ghim toàn bộ | Ghim record ID, số liệu cần thiết và receipt; lưu payload lớn ra artifact; áp budget toàn prompt bằng token | Phiên toàn Shop vẫn có trần; compaction giữ đúng hợp đồng, số tiền và tác động đã xảy ra |
| JHA-08 | P1, code | Sơ đồ gán sẵn `ok` cho cache/perm/trim; scope xanh dựa vào metadata; phase 0A xanh dù còn điều kiện chưa đạt | Tách trạng thái “có code / bật / đã kiểm / đo đạt”; chỉ xanh nghiệm thu khi có evidence và timestamp | Có cấu hình nhưng chưa enforce hoặc chưa test phải hiện chưa chứng nhận; biết rõ engine/brain phạm vi |
| JHA-09 | P0 trước mở quyền phòng, code | `scope: system/department` của shared agent là lọc hiển thị. Loader vẫn đọc shared agent theo slug cho workflow | Giữ tương thích workflow hệ thống nhưng bắt dispatch principal + target grant; không dùng hide UI làm ACL | Phòng không tự gọi ngang/lên; host có quyền vẫn gọi giám định hệ thống qua verification plan |
| JHA-10 | P0 trước 0B, thiếu triển khai | Chưa có compiler authored và gate v1 đầy đủ; danh sách skill trong prompt không chứng minh skill đã được nạp | Compiler, loader và adapter dùng chung; error chỉ rõ trường/route; ghi skill revision vào trace | Manifest hợp lệ không đủ: route phải enforce tool/op/scope/effect/delegate |
| JHA-11 | P0 trước tự cải tiến rộng, thiếu triển khai | Trần 500k/1m mới có trong tài liệu và UI, chưa là budget bắt buộc toàn cây | Host reserve ngân sách nguyên tử, cộng manager/con/retry/verifier/Probe/fallback | Chạm cap dừng dispatch; unknown usage không tính 0; không tự tăng lên 1m |
| JHA-12 | P1, code/đặc tả | Shared agent một bản mới nhất giúp bỏ clone nhưng chưa pin revision cho từng deployment; không tương đương canary theo phòng | Release package bất biến + mapping brain/agent -> revision; route legacy giữ riêng | Nâng package không đổi agent chưa promote; rollback chọn đúng revision |

Nguồn code để đội triển khai mở đúng chỗ:

- JHA-01: [factory.diff_quyen](../../server/factory.py#L788).
- JHA-02: [eval loader và gate](../../server/factory.py#L1039).
- JHA-03, JHA-06: [joyce-guard](../../system/plugins/joyce-guard/plugin.py#L34).
- JHA-04, JHA-05: [canary_tick](../../server/factory.py#L1284).
- JHA-07: [thu gọn output](../../server/engine.py#L1476).
- JHA-08: [harness_map](../../server/harness_map.py#L26).
- JHA-09: [loader shared agent](../../server/main.py#L7448) và [registry shared](../../server/system_agents.py).
- JHA-10: [lắp prompt agent](../../server/main.py#L11242), [schema tham chiếu](./joyce-harness/contract.schema.json).

### 3.2 Các chỗ đặc tả cần hợp nhất sau duyệt

| Mâu thuẫn/khoảng trống | Phương án |
|---|---|
| Đặc tả lắp platform/role/org/department; plan phòng thêm khối; schema chưa có layer khối | Bổ sung layer `block`, khóa org/brand isolation rõ; cập nhật schema, examples, compiler và test cùng lần |
| Đặc tả dùng khóa `harness` trong agent, plan phòng dùng `Joyce/harness.md` | Chọn một mapping: profile immutable trong app; `Joyce/harness.md` khai tham chiếu cấp phòng; `agents/<slug>.md.harness` chỉ override của agent; không hai bản khai quyền cạnh tranh |
| `scope` ở shared agent là enum hiển thị, scope của harness là quyền dữ liệu | Giữ trường legacy để tương thích; compiler đặt quyền dữ liệu trong namespace harness và tuyệt đối không suy ACL từ enum hiển thị |
| Schema resolved chỉ kiểm shape; contract giữa task/verdict/receipt chưa có host validator đầy đủ | Thêm validation task_id/version, artifact hash, criteria coverage, operation/effects/scope, identity của verifier và receipt thật |
| Slug legacy có Unicode, ví dụ agent Fanpage; schema mới ép ASCII | Migration lập alias/ID ổn định; không tự rename làm mất session, link và workflow |
| Budget pool, retries, token cached/estimated chưa thống nhất | Chốt accounting contract và reservation trước dispatch; tách budget công việc với budget cải tiến |
| Prompt mẫu dễ tạo chuỗi manager -> explorer -> executor -> verifier cho việc đơn giản | Quy tắc direct/inline trước; agent chỉ tách khi khác quyền/chuyên môn hoặc cần kiểm độc lập |
| “Chỉ hỏi 5-7 câu” và giới hạn cứng 20/40 dòng | Chỉ hỏi người phụ trách phần còn thiếu sau khi đọc nguồn; giới hạn token đo được, không cắt mất policy chỉ để đủ số dòng |
| Chờ duyệt chuẩn mới và tự động hỏi lại giao dịch bị trộn | Duyệt plan/quyền ở cấu hình; tác vụ đã có ủy quyền chạy theo grant. Không yêu cầu anh duyệt lại từng việc thường lệ |
| Thứ tự P0/P1 của acceptance không phản ánh rủi ro ghi thật | Idempotency, completion gate và tổng budget là điều kiện trước mở write; không để đến bước tối ưu |

### 3.3 Trạng thái triển khai G1 (1.3.41)

**Phần code và test của cả năm ticket đã xong, nhưng G1 CHƯA đạt đủ tiêu chí kết thúc ở mục 13**: còn các tồn đọng ở mục 3.4, trong đó G1-01 làm FIX-05 chưa có tác dụng thật và G1-02 làm tiêu chí "giữ bản sửa riêng của phòng" mới đạt một phần. Đừng đọc bảng dưới như "đã xong hẳn".

Mỗi ticket có test tái hiện chạy ĐỎ trên code cũ trước khi vá, rồi xanh sau khi vá. Test mới chỉ dùng thư mục tạm, không gọi model hay kết nối thật.

| Ticket | Commit | Đã làm | Giới hạn còn lại |
|---|---|---|---|
| FIX-01 (JHA-01) | `9f706b3` | `server/harness_diff.py`: so cây YAML, khoá lồng, tráo giữa nút, alias, đổi kiểu, khoá lạ; không đọc chắc thì không tự áp. Thử trên 51 agent, 239 workflow, 530 skill, 66 loop thật: 0 bị chặn oan khi chỉ sửa thân bài | 30 skill có đầu file YAML sai cú pháp từ trước nay phải chờ chủ xem (đúng điều kiện dừng); khoá `x-...` coi là trung tính |
| FIX-02 (JHA-02) | `b066349` | `factory.eval_load`: missing / invalid / valid, lỗi từng ca; JSON hỏng, bộ rỗng, thiếu name/check/value, regex hỏng, quá 20 ca đều chặn; `eval_bat_buoc` tuỳ chọn | `eval_bat_buoc` mặc định tắt để không đổi hành vi 61 brain; đảo quyết định cũ "eval hỏng vẫn áp" |
| FIX-03 (JHA-03) | `30419de` | `server/file_policy.py` dùng chung; `mcp_hub._write` kiểm sát lúc ghi, giải lại đích, tạo-độc-quyền cho `sources/`; hook chỉ còn báo sớm | Mới phủ tool `joyce_write_file` đi qua hub. Tool ghi native của CLI vẫn do JHA-06/G2. Ca symlink file chưa chạy được trên máy Windows thiếu quyền (junction thì đã chạy) |
| FIX-04 (JHA-04) | `9184b84` | Chụp hash từng đích, CAS, sao lưu, ghi nguyên tử, lưu trạng thái từng đích, kết quả promoted/partial/conflict, rollback có kiểm phiên bản | CAS là so-rồi-ghi trong cùng tiến trình, không có khoá liên tiến trình |
| FIX-05 (JHA-05) | `9184b84` | Cần đủ giờ và 20 việc đã chạy trên bản ứng viên, gắn qua khoá agent; lỗi dừng ngay; hết hạn 14 ngày thì dừng và báo chủ | Việc chạy qua workflow (`route=wf:`) chưa gắn được vào agent nên chưa tính làm bằng chứng; ngưỡng 20 là đề xuất của plan, chỉnh được bằng `canary_min_tasks` |

Bảy bộ test có sẵn (schema, ranh giới quyền, joyce-guard, system_agents, harness_map, thu gọn tool, cache) vẫn đạt. Chưa làm: JHA-06..12 và toàn bộ G2.

### 3.4 Tồn đọng của G1 và việc reviewer cần xem

Ghi ngày 28/10/2026 sau khi làm xong G1. Mục tiêu: người review (đề xuất Astra cho thiết kế và đặc tả, Fable cho an toàn và đồng thời) biết chính xác chỗ nào chưa chắc, không phải đoán. Mức: **P0** là làm tính năng chưa có tác dụng thật hoặc có thể gây hại trước khi dùng; **P1** là lỗ hổng hoặc quyết định thiết kế cần chốt trước G2; **P2** là hạn chế đã biết; **P3** là ghi nhận. "Số liệu thật" là đo trên máy này ngày 28/10/2026, chỉ đọc, không sửa dữ liệu.

| Mã | Mức | Ticket | Vấn đề chưa giải quyết | Bằng chứng | Đề xuất | Người xem |
|---|---|---|---|---|---|---|
| G1-01 | **P0** | FIX-05 | **Canary không có nguồn bằng chứng trong hệ thật.** Bằng chứng và tín hiệu lỗi chỉ tính việc có khóa `idempotency_key = agent:<mã>:<slug>`. Hệ thật không gắn việc vào agent theo cách đó | Kho `kanban.sqlite3`: 0/160 việc có khóa `agent:`; cột `assignee_key` rỗng ở 160/160; 112 việc `route=auto`, 47 `bai-hoc`, 1 `wf:`; chỉ 3 việc `done`, 0 `blocked`. Việc của phòng ban chủ yếu chạy qua chat, không qua Kanban | Với canary file chung, ngưỡng 20 việc sẽ không bao giờ đạt, canary hết hạn sau 14 ngày và KHÔNG nhân (an toàn nhưng vô dụng). Đồng thời bản cũ nhận lỗi bằng chữ slug trong tiêu đề/lý do, bản mới chỉ nhận lỗi gắn khóa nên **lỗi trên bản ứng viên sẽ không làm canary dừng**. Cần G2 gắn trace agent và revision vào mỗi lượt chạy (chat turn, workflow node, task), rồi canary đọc từ trace. Trước đó coi canary chỉ là bộ chặn nhân bản, không phải bằng chứng chất lượng. Cần Astra quyết nguồn bằng chứng cho agent chủ yếu dùng qua chat | Astra, Fable |
| G1-02 | **P1** | FIX-04 | **Chỉ bảo vệ đích bị sửa SAU lúc chụp hash.** Đích vốn đã khác bản nguồn từ trước (phòng tự có biến thể riêng từ lâu) vẫn bị ghi đè nếu nó không đổi từ lúc chụp. Mục 11 của plan nói hash khác baseline thì coi là override cần review, G1 chưa làm đúng vậy | `harness_diff`/`factory._nhan_mot_dich`: `base_hash` là hash của đích tại lúc áp, không phải hash bản nguồn trước khi sửa. Test hiện chỉ có ca "sửa sau lúc áp", chưa có ca "đã khác từ trước". Mỗi đích bị ghi đều có file sao lưu trong `Joyce/proposals/.backup/` | Chỉ nhân sang đích có nội dung đúng bằng bản nguồn TRƯỚC khi sửa (baseline chung); đích khác baseline thành `override` chờ chủ xem. Thêm test ca này. Cần Astra xác nhận quy tắc, em sửa nhanh được sau khi chốt | Astra |
| G1-03 | P1 | FIX-04, FIX-05 | **Chưa có đường để chủ xử lý kết quả.** Thông báo `partial`, `conflict`, `het_han` nói "anh quyết định" nhưng chưa có nút hay lệnh nhân thủ công, lật lại, hay khôi phục các đích đã nhân. Chưa có lệnh khôi phục từ file sao lưu. Sơ đồ chưa hiện các trạng thái mới và số bằng chứng (JHA-08) | `canary_tick` chỉ ghi trạng thái và gửi thông báo; không có route hay công cụ nào đọc `targets[].backup` | Thêm hành động của chủ cho từng canary: nhân thủ công theo từng đích, lật lại đích đã nhân từ sao lưu, đánh dấu chấp nhận. Hiện `evidence` và `targets` lên Sơ đồ. Gom vào G2 cùng JHA-08 | Astra |
| G1-04 | P1 | FIX-04 | **So-rồi-ghi chỉ an toàn trong một tiến trình.** Không có khóa liên tiến trình. Hai bản server chạy cùng lúc, hoặc người sửa file đúng vào khoảng mili-giây giữa lần đọc lại và lần đổi tên, vẫn có thể bị ghi đè | `_nhan_mot_dich`: đọc lại hash rồi `os.replace`, không khóa file | Xem có cần khóa file (hoặc ghi kèm kiểm `mtime`/`inode`) hay chấp nhận cửa sổ này cho một công cụ chạy một tiến trình | Fable |
| G1-05 | **P1** | FIX-03 | **Chốt ghi file mới chỉ phủ tool `joyce_write_file` đi qua MCP Hub.** Chưa phủ: tool ghi native của CLI (Claude Code, Codex, Grok, agy), `joyce_run_command`, plugin tự ghi file, route HTTP ghi file của dashboard, skill hoặc loop ghi trực tiếp, bot khách hàng | Chỉ `mcp_hub._write` gọi `file_policy.deny_reason`; không nơi nào khác import `file_policy` | Đây chính là JHA-06 (chốt bắt buộc cho mọi route) và ma trận mục 14. Không bật route nghiệp vụ nào ghi sổ hay sửa tài liệu gốc cho tới khi ma trận từng route có bằng chứng | Fable, Astra |
| G1-06 | P2 | FIX-03 | **Chưa kiểm hết nền tảng và hạn chế còn lại.** (a) Ca symlink file và ca tráo symlink file chưa chạy được vì máy Windows này thiếu quyền; chỉ junction được chạy. (b) Chưa chạy trên Linux (phân biệt hoa thường) và macOS (không phân biệt hoa thường, nhánh `samefile` và `casefold` chưa có test thật). (c) Còn cửa sổ rất nhỏ nếu thư mục cha bị tráo ngay giữa lần giải cuối và lúc mở file; riêng `sources/` dùng tạo-độc-quyền nên file đã có không bị ghi đè, nhưng tạo file mới qua thư mục vừa tráo vẫn có thể đi sai chỗ | In `skip` của `test_fix03_file_guard.py`; `file_policy._khong_phan_biet_hoa_thuong` chỉ được thử trên Windows | Chạy test này trên CI Linux và một máy macOS hoặc Windows bật Developer Mode để tạo symlink. Cân nhắc mở file bằng `O_NOFOLLOW` hoặc kiểm `fstat` sau khi mở | Fable |
| G1-07 | P1 | FIX-01 | **Chỉ so frontmatter, không so thân bài.** Một bản nháp chỉ đổi thân bài của agent hay skill (ví dụ thêm câu "được phép gửi tin cho khách") vẫn bị coi là sửa nội dung thuần và vẫn tự áp, dù về hành vi nó có thể nới quyền | `diff_quyen` chỉ đọc khối đầu file; thân bài không được phân tích | Câu hỏi thiết kế cho Astra: có nguyên tắc "thân bài không cấp quyền, quyền chỉ nằm ở harness và grant do host kiểm" không (đặc tả mục 5, 6). Nếu có thì nói rõ cho người viết agent; nếu không thì cần luật nhận diện thân bài, hoặc để thân bài thay đổi lớn đi qua giám định | Astra |
| G1-08 | P2 | FIX-01 | **Hạn chế của phân loại.** (a) Danh sách khóa "nội dung" lấy từ dữ liệu hiện có; khóa mới hợp lệ sẽ bị coi "chưa biết" và chặn tự áp (an toàn nhưng gây ma sát). (b) Bước workflow định danh theo vị trí, nên chèn một bước làm các bước sau bị báo đổi `agent`. (c) 30 skill có đầu file YAML sai cú pháp từ trước nay luôn phải chờ chủ. (d) Khóa bắt đầu bằng `x-` coi là trung tính; nếu sau này runtime đọc khóa `x-...` thì thành lỗ. (e) Giới hạn 64KB cho đầu file | Đo trên 51 agent, 239 workflow, 530 skill, 66 loop: 0 chặn oan khi chỉ sửa thân bài; 30 skill không đọc chắc | Chủ quyết có sửa 30 đầu file skill hay không. Nếu thêm khóa metadata mới thì đăng ký trong `harness_diff.KHOA_NOI_DUNG`. Gắn `id` cho bước workflow quan trọng để so theo định danh | Chủ, Astra |
| G1-09 | **P1** | FIX-02 | **Tự áp ở phần lớn phòng vẫn không có bộ eval nào.** `eval_bat_buoc` mặc định tắt và chỉ có 1 bộ eval trên cả hệ thống, nên 43/44 phòng tự áp nội dung chỉ dựa vào so quyền và giám định ẩn danh. Eval hiện chỉ kiểm chuỗi, không kiểm hành vi. Và quyết định cũ "eval hỏng thì vẫn áp" đã bị đảo | `factory.eval_load`; 1 file `giam-dinh-harness.json` (7 ca, hợp lệ); `load_factory_cfg().eval_bat_buoc` mặc định False | Chủ và Astra quyết: bật `eval_bat_buoc` mặc định cho brain phòng ban (gần như chặn mọi tự áp cho tới khi có eval ở G4) hay giữ tắt. Xác nhận việc đảo quyết định cũ | Chủ, Astra |
| G1-10 | P2 | FIX-05 | **Quy tắc bằng chứng thô.** (a) Ngưỡng 20 việc, 24 giờ, 14 ngày là mặc định đề xuất của plan, chưa hiệu chỉnh theo lưu lượng. (b) Việc `blocked` đều tính là lỗi, kể cả việc chỉ chờ chủ duyệt, không phải lỗi agent. (c) Chưa phân loại lỗi quyền hoặc dữ liệu để dừng ngay như plan yêu cầu. (d) Chỉ nhìn việc ở brain nguồn, không nhìn brain nhận. (e) Việc chạy qua workflow (`route=wf:`) chưa tính | `_canary_evidence` | Quyết sau khi G1-01 có dữ liệu thật; phân loại `block_kind` (có sẵn cột) để tách chờ duyệt khỏi lỗi | Astra |
| G1-11 | P3 | FIX-04, FIX-05 | **Hai ticket chung một commit** (`9184b84`) trái nguyên tắc "không gộp" của plan, vì cùng viết lại `canary_tick`. Revert riêng một ticket phải tách tay. Thông báo canary chỉ có tiếng Việt cố định | Lịch sử git nhánh `claude/crm-v2-final-1-3-35` | Ghi nhận; nếu cần revert riêng thì làm theo từng hàm `_canary_evidence` và `_nhan_mot_dich` | Astra |
| G1-12 | P2 | Chung | **Kiểm chứng ngoài các test tổng hợp còn mỏng.** (a) Chưa chạy luồng đề xuất tự cải tiến đầu cuối trên brain thật; chỉ có quét chỉ-đọc 51/239/530/66 file. (b) `test_khoi_dong_nhe` (chi phí nạp `main` so với nạp fastapi, ngưỡng 5,0 lần): đo 5 lần mỗi bên lúc máy rảnh, bản 1.3.39 gốc 4,69 đến 4,94, bản 1.3.41 4,82 đến 4,99, tức cao hơn khoảng 0,1 và sát ngưỡng; khi máy bận từng ra 5,19 và 5,42 và test đỏ. Đây là chi phí nạp tăng nhẹ thật qua 1.3.39 đến 1.3.41 (nhiều module mới nạp lúc khởi động), không chỉ là nhiễu. (c) Hai test cũ `test_icons`, `test_nhat_ky_song_ngu` đỏ sẵn từ trước, không do harness. (d) Test cũ `test_factory` bị đảo hợp đồng ở hai chỗ (eval hỏng, canary không traffic) | Bộ test đầy đủ ở worktree sạch (1.3.41): 865/894 xanh; so với bản 1.3.38 chỉ `test_khoi_dong_nhe` đỏ thêm (xem (b)) | Nạp lười các module mới (`messenger_ops`, `system_agents`, `harness_*`) hoặc nâng ngưỡng có lý do; chạy thử đề xuất trên bản sao brain trong thư mục tạm | Fable |

**Điều kiện coi G1 là xong thật (đề xuất):** G1-01 có hướng xử lý được duyệt (hoặc canary file chung bị khóa tạm ở trạng thái chỉ-chặn, ghi rõ trên Sơ đồ), G1-02 được sửa và có test, G1-05 và G1-06 có người nhận trong G2, G1-09 có quyết định của chủ. Các mục P2 và P3 ghi nhận, không chặn G2.

**Việc đang làm tạm ổn nhờ thiết kế an toàn:** các tồn đọng G1-01, G1-03, G1-10 đều lệch về phía KHÔNG nhân bản và KHÔNG ghi, tức là chậm chứ không hại. Riêng G1-02 và G1-07 là hai chỗ có thể áp thay đổi mà chủ không mong muốn; G1-02 có sao lưu từng đích, G1-07 hiện chỉ giảm nhờ giám định ẩn danh.

## 4. Bằng chứng kiểm tra và giới hạn

Đã chạy lại bảy bộ test hiện có trong môi trường state/brain tạm, không gọi model hoặc kết nối production:

| Bộ test | Check pass |
|---|---:|
| `test_joyce_harness_schema.py` | 72 |
| `test_harness_ranh_gioi_quyen.py` | 20 |
| `test_joyce_guard.py` | 21 |
| `test_system_agents.py` | 32 |
| `test_harness_map.py` | 14 |
| `test_thu_gon_tool_cu.py` | 10 |
| `test_engine_cache.py` | 26 |
| **Tổng** | **195** |

Các test trên pass xác nhận phần đã được bao phủ, không phủ định các ca biên mới.

Kết quả diagnostic bổ sung, không sửa code:

```text
nested_harness_budget       diff_quyen -> []
reassign_workflow_tools      diff_quyen -> []
eval_malformed_file         eval_for_draft -> None
eval_missing_check_field    eval_for_draft -> None
guard_direct_sources        denied -> True
guard_dot_segments          denied -> False
pinned_shop_trim_count      -> 0
pinned_shop_remaining_chars -> 160000
canary_without_tasks        promoted -> 1
destination_owner_edit      replaced by candidate
```

Ca canary dùng `canary_tick` thật với read/write được mock hoàn toàn trong RAM; không sửa file brain. Ca path là kiểm hàm guard, chưa phải thử end-to-end qua mọi adapter.

Chưa thực hiện: benchmark 18 agent qwen trên nghiệp vụ, test quyền toàn bộ engine/kênh, đo cache sau một tuần, chạy Probe thật, canary production hoặc rà toàn bộ nội dung wiki. Kế hoạch không chứng nhận hệ thống đã an toàn ở những phần chưa kiểm.

## 5. Kiến trúc tổ chức agent đề xuất

### 5.1 Cơ cấu và lớp nghề

```text
Chủ: duyệt mục tiêu, policy và quyền
  Joyce Manager: quản trị liên phòng, nhận kết quả và báo chủ
    Trưởng phòng: trách nhiệm nghiệp vụ trong đúng phòng
      Chuyên viên: chỉ tách khi cần khác quyền hoặc chuyên môn

Runtime dùng chung cho mọi vai
  Role profile riêng của Joyce / department_manager / executor / explorer / verifier
    Tổ chức và thương hiệu
      Khối theo registry (11 khối)
        Phòng (44 phòng)
          Override agent
            Constraint của task
```

Không biến sơ đồ kế thừa cấu hình thành sơ đồ quyền: executor kế thừa profile executor, không kế thừa quyền điều phối của Joyce. Lớp khối mang quy tắc nghề tái sử dụng, không mặc định sinh thêm “agent trưởng khối”.

Joyce Core giữ định danh và nơi nhận báo cáo. Joyce Manager là profile quản trị riêng được host gắn vào entrypoint phù hợp; không bắt chủ phải nói chuyện với hai bot cho một việc.

Bốn agent riêng của Brain Default được giữ vai hiện có. Giám đốc Studio, Giám đốc Học viện và Tham mưu không tự trở thành cấp điều phối có quyền ngang Joyce; nếu cần ủy quyền thì bind task và grant rõ. AdminFanpage giữ phạm vi nội dung/kênh được cấp.

Chín agent dùng chung là dịch vụ chuyên môn hệ thống, không phải chín trưởng phòng. Onboarding có thể hiện khắp phòng nhưng dữ liệu phải theo scope từng run.

### 5.2 Quyền và trách nhiệm

| Chủ thể | Được quyết định | Không tự quyết định |
|---|---|---|
| Anh | Scope, operation/effect, delegation, budget, promotion quyền | Không cần xác nhận lại tác vụ thường lệ đã được ủy quyền |
| Người phụ trách nghề | SOP, nguồn chuẩn, đáp án và tiêu chí nghiệm thu | Không nâng grant nếu anh chưa ủy quyền |
| Joyce Manager | Chọn route, ưu tiên và giao đúng phòng trong grant | Không tự cấp quyền, thay rubric hoặc đổi scope |
| Trưởng phòng agent | Thực hiện/giao nội bộ phòng khi được grant, báo blocker | Không giao việc ngược lên Joyce hoặc ngang sang phòng khác |
| Executor | Tạo candidate artifact, receipt và đề nghị hoàn thành | Không tự đóng việc đã qua kiểm |
| Verifier/check script | Kết luận theo tiêu chí và bằng chứng | Không sửa sản phẩm rồi tự pass |
| Host runtime | Enforce, accounting, state, receipts và chốt completed | Không tin quyền/verdict vì model tự khai |

“Báo lên” là trả kết quả/blocker cho task cha; không phải được quyền tạo task mới cho Joyce. Cross-department flow do Joyce/host điều phối, trong một trace và budget đã cấp.

### 5.3 Hợp đồng nghề tối thiểu cho mỗi phòng

Mỗi phòng có một gói ngắn gồm:

- Owner nghiệp vụ, registry ID, thương hiệu và phạm vi đọc/ghi.
- Ba đến năm loại việc thật; mỗi loại có trigger, input, output, nguồn chuẩn và tiêu chí xong.
- Skill đang có: khi nào nạp, nguồn nào được đọc, version nào sử dụng.
- Tool/operation và argument policy; execution grant riêng với delegation grant.
- Quy tắc fail/blocked/waiting_owner và báo cáo lên Joyce.
- Check script hoặc verifier phù hợp; chỉ rõ kiểm trước ghi và sau ghi.
- Eval có fixture, đáp án được người biết nghề xác nhận và holdout.
- Budget, revision, trạng thái deployment và rollback.

Không điền giả luật nghề để gói nhìn “đủ”. Nguồn chưa có thì ghi thiếu và giới hạn route tương ứng.

## 6. Dùng model theo bằng chứng

Không tự đổi 18 agent qwen3:14b, không đánh giá “yếu nhất” từ tên model. Cùng một model có thể phù hợp tác vụ đọc, nhưng không đạt tác vụ đối soát dài hoặc gọi tool phức tạp.

Đề xuất ba mức readiness, áp **cho mọi model**:

| Mức | Được đưa vào pilot | Điều kiện lên mức tiếp |
|---|---|---|
| Chưa chứng nhận | Đọc/soạn, shadow trên fixture; output ghi chỉ là đề nghị | Qua ca nghiệp vụ và ca quyền của đúng route |
| Có điều kiện | Host thực hiện operation cụ thể sau pre-check, receipt và post-check; thêm independent review khi loại việc cần | Đạt baseline, recovery và canary |
| Được chứng nhận theo task | Tự vận hành trong grant đã duyệt | Theo dõi regression, đổi model/prompt lớn thì kiểm lại |

Verifier không cấp quyền cho model và không hoàn tác được tin đã gửi sai. Với hành động không đảo được, kiểm quan trọng phải diễn ra **trước** side effect; đọc lại kết quả để xác nhận sau đó.

Không bắt năm giám định cùng chạy cho mọi tác vụ. Chọn đúng check rẻ nhất đủ quyết định. Thiếu chỉ một phần dữ liệu thì đọc bổ sung; không tăng model theo phản xạ.

## 7. Luồng pilot và nhân theo khối

### 7.1 Luồng đầu tiên

**Đối Soát chỉ đọc -> Phòng Thu trong môi trường thử -> live canary được duyệt.**

Ví dụ fixture tổng hợp: hợp đồng 15 triệu, đã thu 1,5 triệu, nhận yêu cầu ghi thêm 3 triệu.

1. Joyce xác định hợp đồng và task criteria, giữ số tiền theo chứng từ.
2. Phòng Thu đọc sổ/bảng giá sống; không tìm thấy hoặc có hai hợp đồng cùng khớp thì chờ thông tin.
3. Host kiểm grant, amount, action idempotency, hạn mức và version record.
4. Tool nghiệp vụ ghi đúng một phiếu; receipt có remote/local record ID.
5. Check độc lập đọc lại: tổng thu 4,5 triệu, còn phải thu 10,5 triệu theo fixture; không tự hoàn thành hợp đồng.
6. Host chốt kết quả, trả Joyce và đúng người giao việc.
7. Nếu timeout sau ghi: reconcile theo receipt/action key, không ghi lại mù.

Đối Soát không cần quyền ghi của Thu để kiểm. Mục tiêu là chứng minh cả quyền và completion contract, không chỉ một câu trả lời có số đúng.

Phòng Chi được audit/eval từ đầu vì rủi ro cao, nhưng chỉ mở ghi sau khi nền và luồng Thu đã đạt.

### 7.2 Sáu phòng pilot

| Phòng | Việc chính để đo | Kiểm bắt buộc |
|---|---|---|
| Đối Soát | Đối chiếu dữ liệu theo kỳ, nêu khoản lệch | Nguồn/thời điểm, coverage, tổng và chênh lệch đúng |
| Thu | Thu cọc/thanh toán theo hợp đồng | Đúng hợp đồng, idempotency, amount, read-back |
| Chi | Ghi chi và quy trình hạn mức hiện hành | Chứng từ/hạng mục, quyền và approval nghiệp vụ, không ghi trùng |
| Sales Hình ảnh | Tra gói, báo giá, chuẩn bị hợp đồng | Giá/SOP có hiệu lực, không bịa ưu đãi, dữ liệu bắt buộc |
| Sales Váy cưới | Tra lịch, giữ chỗ/thuê | Trùng lịch, thời gian giặt, concurrency trên cùng món |
| Nhân sự Vận hành | Giao việc, tính khoản theo quy tắc được duyệt | Đúng phiên bản công thức, không tính trùng, phân quyền dữ liệu nhân sự |

Không đồng nhất thu trừ chi với lãi gộp khi chưa có định nghĩa kế toán được duyệt; script dùng đúng công thức nghiệp vụ nguồn, không suy từ tên chỉ số.

### 7.3 Nhân theo 11 khối

| Wave | Khối | Điều kiện ưu tiên |
|---|---|---|
| 1 sau pilot | Kế Toán | Luật số và chứng từ đã xác minh |
| 2 | Bán Hàng | Bảng giá, lịch, hợp đồng đáng tin |
| 3 | Nhân Sự | Công thức và quyền dữ liệu cá nhân rõ |
| Theo readiness | Marketing, CSKH, Xử Lý Truyền Thông | Nguồn thương hiệu, recipient scope, kiểm trước gửi |
| Theo readiness | Sản Xuất, Nghiên Cứu, Vệ Sinh | Checklist đầu ra, lịch, thiết bị và bàn giao |
| Theo readiness | Văn Thư & Quy Trình, ThuyH2O | Phiên bản SOP, học viên và tách thương hiệu |

Bảy nhóm template nghề nếu hữu ích chỉ là taxonomy tái sử dụng, không được đổi 11 khối/44 phòng hoặc gộp dữ liệu hai thương hiệu.

## 8. Workflow dựng harness phòng

Đề xuất một workflow dựng **bản nháp**, gọi theo phòng khi có nhu cầu; không phải vòng quét nền.

1. **Inventory:** đọc registry, agent, skill, wiki index, tool được cấp và tối đa 30 ngày việc liên quan. Nếu chưa có log, dùng fixture tổng hợp và ghi rõ.
2. **Nguồn nghề:** lấy SOP/bảng giá/hạn mức có owner và ngày hiệu lực; kiểm mâu thuẫn trước khi viết nội quy.
3. **Trao đổi:** chỉ hỏi người phụ trách các điểm còn thiếu. Trưởng phòng AI không tự xác nhận luật mới do chính nó suy ra.
4. **Draft:** sinh profile refs, skill trigger, task catalog, đề xuất quyền, check/eval và phần thiếu. Giữ file ngoài brain production.
5. **Validate:** schema + semantic compiler + scope/grant + dependency lock, không gọi model nếu không cần.
6. **Probe:** baseline/candidate cùng fixture trong sandbox, khóa credential/egress thật; composite candidate phải chạy lại.
7. **Review packet:** diff dễ đọc, căn cứ SOP, phần quyền đổi, eval pass/fail, chi phí, rủi ro và rollback.
8. **Duyệt/promotion:** anh duyệt quyền; owner nghề duyệt nội dung; deploy một brain trước, có canary đủ mẫu.

Nếu chỉ sửa một trigger skill đã có, không chạy đủ workflow nhiều model. Quy trình chọn mức nặng tương ứng với thay đổi.

## 9. Lộ trình và cổng nghiệm thu

| Giai đoạn | Deliverable chính | Phụ thuộc | Điều kiện xong |
|---|---|---|---|
| G0. Chốt plan | Phạm vi, owner, danh sách quyết định và baseline 1.3.39 | Anh duyệt plan này | Có phạm vi triển khai được duyệt; chưa tự mở quyền production |
| G1. Vá lỗi nền | JHA-01..04; mandatory gate coverage; test regression | G0 | Các ca biên tái hiện đổi sang đạt; không phá test cũ; không mất bản sửa riêng |
| G2. Runtime 0B | Authored schema/compiler, grant theo operation, ledger budget, completion/receipt, registry revision | G1 | Một route API/hub và một đường workflow pilot enforce thực; các route chưa chứng nhận bị giới hạn đúng |
| G3. Golden Joyce + pilot nhỏ | Manager profile, một phòng Đối Soát, Thu thử, check script và dataset | G2 | Hành vi, quyền, retry, cancel/recovery đạt; báo đúng kênh |
| G4. Sáu phòng | Nội quy có nguồn, task catalog, eval và readiness từng model/route | G3 | Qua eval và live canary được duyệt từng phòng |
| G5. Nhân theo khối | Profile package immutable, migration dry-run, rollout theo revision | G4 | Không sửa phòng chưa promote; rollback và conflict xử lý được |
| G6. Tự cải tiến có kiểm soát | Probe isolated, holdout, budget hard cap, promote có bằng chứng | G2 + G4 | Một lượt cải tiến đầy đủ; không chạm production trong Probe; giữ baseline khi thiếu bằng chứng |

JHA-05, JHA-07, JHA-08, JHA-12 và hợp nhất đặc tả làm cùng G2 trước mở rộng G4/G5. 0A tối ưu cache tiếp tục theo quyết định đã có, nhưng không được dùng mục tiêu cache để bỏ gate hoặc trì hoãn lỗi mất dữ liệu.

Không cam kết lịch bằng số bản phát hành khi chưa ước lượng effort theo hạng mục. Sau G0, chia issue có owner và ước lượng; G1/G2 chạy theo dependency và kết quả test, không dựa vào số file đã viết.

### 9.1 Gate chất lượng

- Tất cả ca bắt buộc chạy đủ, không skip hoặc inconclusive chưa xử lý.
- Ca quyền, dữ liệu và false completed: không chấp nhận lỗi trong bộ nghiệm thu.
- Mỗi task family có happy path, thiếu dữ liệu, dữ liệu mâu thuẫn, vượt quyền, tool lỗi và đọc lại sau ghi; write có thêm duplicate, concurrent và timeout sau commit.
- Behavioral pilot chạy ít nhất ba lần/ca; không đưa đáp án holdout cho agent đang được sửa.
- Baseline và candidate dùng cùng fixture/model/config; báo cả chất lượng và tổng chi phí cây việc.
- Đề xuất canary: một brain, ít nhất 24 giờ **và** 20 task phù hợp đã được kiểm; không có traffic thì chưa đủ bằng chứng promote. Các task ghi phải được duyệt phạm vi trước.
- Các ngưỡng này là tiêu chuẩn nghiệm thu đề xuất, không phải chứng minh thống kê độ tin cậy production.

### 9.2 Gate hiệu quả

Theo dõi first-pass verification, task completion, human correction, blocked age, false completed và cost/completed task. Mẫu số tính cả lỗi và chi phí retry/verifier; không tăng “tự động hóa” bằng cách đẩy task khó sang blocked rồi loại khỏi báo cáo.

Không đặt KPI theo số agent được tạo, số skill được gắn hoặc số đèn xanh. Khi script đã đủ quyết định, số model calls bổ sung phải bằng 0 cho bước kiểm đó.

## 10. Backlog triển khai theo phạm vi file

Chỉ là bản đồ công việc sau duyệt, không phải danh sách file đã sửa.

| Nhóm | Điểm tích hợp | Nguyên tắc |
|---|---|---|
| Factory | `server/factory.py`, tests harness/eval/canary | Semantic diff, loader chặt, CAS từng đích, traffic threshold |
| Guard và quyền | `mcp_hub.py`, `plugins_host.py`, `joyce-guard`, adapters engine | Tái sử dụng gate; mandatory checks không chỉ nằm trong prompt/hook hỗ trợ |
| Compiler | Module harness riêng và schema authored/resolved | `main.py` chỉ tích hợp, không nhét thêm toàn bộ logic vào file lớn |
| Profiles | Package profile có version trong `system/harness/` (đề xuất) | Root policy tin cậy, layer khối/brand; ID từ registry |
| Shared agents | `system_agents.py` và loader trong `main.py` | UI visibility khác dispatch ACL; giữ alias và bản sửa phòng |
| Workflow/task | `workflow_graph.py`, `agent_runtime.py`, `tasks.py`, `agent_jobs.py` | Map state và contract; không tạo kho task song song |
| Grant/recovery | `resonance_grants.py`, `capability_executor.py`, `write_path_runtime.py` | Tái sử dụng narrowing, receipt/lock/reconcile; không bật nguyên write-path vì nó có luật xác nhận riêng |
| Budget | Các ledger usage/quota hiện có + adapter tree budget | Một nguồn accounting, không thêm bộ đếm rời dễ lệch |
| Context/cache | `engine.py`, `compaction.py` | Ghim fact/receipt thay vì toàn output; đo từng engine |
| Dashboard | `harness_map.py`, route snapshot, Sơ đồ | Đèn phản ánh enforcement/evidence, không chỉ file có mặt |
| Tài liệu | Spec, rollout, final-audit, schema, reference, prompts, acceptance | Cập nhật đồng bộ theo baseline mới; audit cũ giữ lịch sử |

Compiler cần semantic validation ngoài JSON Schema: khối/thương hiệu đúng registry, grants là giao hợp lệ, operation registry thật, scope con không nới, criteria coverage và artifact hash/version đúng. `recorded_by: host` trong JSON không chứng minh caller là host; identity phải đến từ execution context.

## 11. Migration và đường quay lại

1. Read-only inventory: ID, alias, model/provider, skills, refs, body hash, quyền hiệu lực và deployment revision.
2. Dry-run: xuất mapping cũ -> mới và diff cho từng brain; không rename hoặc xóa agent.
3. Giữ bản phòng đã sửa; nếu hash khác baseline thì coi là override cần review.
4. Backup manifest/prompt/config sẽ đổi, kèm hash, thời điểm và đường restore.
5. Áp atomically với expected revision; xung đột thì dừng đúng target, không overwrite.
6. Bật route v1 từng brain, legacy giữ nhãn chưa chứng nhận.
7. Rollback cấu hình có kiểm revision, không chép cả brain đè dữ liệu mới.

Bỏ chín bản clone đã được làm ở 1.3.39: không làm lại migration 549 file. Việc còn lại là pin deployment và bảo vệ override.

Thay đổi quyền, model, skill hay bản phát hành dùng chung đều ghi audit và có người chịu trách nhiệm. Agent mới không tự vào danh sách delegate của phòng khác.

## 12. Phạm vi anh duyệt và phạm vi chưa được làm

### Gói đề xuất để duyệt

- Kiến trúc Joyce riêng, phòng chỉ giao nội bộ, giữ 11 khối và 44 phòng.
- Sửa JHA-01..12 và hoàn thiện 0B theo thứ tự dependency ở mục 9.
- Chọn Đối Soát đọc trước, Thu thử sau; mở sáu phòng rồi nhân theo khối.
- Giữ quyền do anh duyệt; nội dung nghề do người phụ trách xác nhận.
- Không tạo agent cho 14 brain khối/kho chung khi chưa có công việc cụ thể.
- Model được cấp tác vụ theo eval, không đổi hàng loạt theo tên model.
- Giữ hard cap cải tiến 500k/1m và hai lượt/target/tuần như đã chốt.

### Sau khi anh duyệt plan

Có thể triển khai code và test trong môi trường tách biệt theo gói đã duyệt. Trước migration/live write, trình diff cụ thể và grant của từng pilot theo policy anh đã chọn; nếu anh đã cấp rõ từ trước thì áp đúng phạm vi đó, không hỏi lại cùng quyết định.

**Trước khi anh duyệt:** chỉ audit, hoàn thiện plan và đọc bằng chứng. Không vá runtime, không tạo/chỉnh agent production, không đổi model/quyền, không chạy Probe thật hoặc tự bật canary.

## 13. Gói việc đầu tiên sau khi được duyệt

Gói đầu là **G1: vá lỗi đã tái hiện và kiểm chứng hồi quy**, chưa gồm rollout quyền phòng hoặc thay model. Mỗi ticket có một bản vá nhỏ, test tái hiện trước vá, test sau vá và diff để review. Không gộp các thay đổi độc lập thành một lần phát hành khó quay lại.

| Ticket | Đầu ra phải bàn giao | Ca âm bắt buộc | Điều kiện dừng |
|---|---|---|---|
| FIX-01: semantic diff | Hàm so cấu hình theo cây YAML và danh sách đường dẫn thay đổi, thay dấu vân tay chuỗi hiện tại | Nested budget; tráo tools giữa node; thêm quyền qua alias; YAML lỗi; khóa quyền mới chưa biết | Không parse chắc cấu hình thì không auto-apply; không suy là sửa nội dung thuần |
| FIX-02: eval loader | Kết quả có trạng thái missing/invalid/valid, số ca đọc/chạy/thất bại và lỗi cụ thể | JSON lỗi, case thiếu name/check, root sai kiểu, bộ rỗng, check lạ, quá số ca cho phép | Nếu eval bắt buộc mà không kiểm đủ thì giữ baseline; không tự sửa đáp án để qua |
| FIX-03: file guard | Resolver policy và đích write thống nhất; check bắt buộc sát thời điểm ghi | Dot segments, absolute path, Windows case, symlink/junction, file thay giữa check và write | Không xác định được cùng đích an toàn thì từ chối operation, không fallback đường write khác |
| FIX-04: canary target | Snapshot từng đích, CAS, backup và kết quả promotion theo target | Đích sửa tay, đích bị xóa, chỉ một đích ghi lỗi, process chết giữa promotion | Không overwrite conflict; partial promotion không được báo toàn bộ đã thành công |
| FIX-05: canary evidence | Điều kiện đủ thời gian + đủ traffic, gắn outcome vào revision thực chạy | Zero traffic, task không dùng revision candidate, lỗi không nhắc slug, số mẫu chưa đủ | Thiếu evidence thì không promote; sự cố quyền/dữ liệu dừng canary |

Mandatory gate của JHA-06 được thiết kế cùng FIX-03 và hoàn thành cho route pilot ở G2. G1 không tuyên bố đã kiểm soát mọi shell/native tool chỉ vì sửa hook hub.

Tiêu chí kết thúc gói: tất cả ca tái hiện tương ứng chuyển sang kết quả mong muốn, bảy bộ test hiện có tiếp tục đạt, test mới không gọi production, và review xác nhận bản sửa riêng của người dùng được giữ. Không dùng đúng con số 195 làm mục tiêu test sau này vì số check sẽ tăng khi bổ sung hồi quy.

### 13.1 Gói G2 tối thiểu, tránh xây lại cả nền tảng

1. **Một compiler:** nhận layer có version và override; xuất resolved manifest, dependency lock, hash và diagnostics. Schema authored và schema resolved tách rõ.
2. **Một quyết định quyền chung:** host nhận principal, task, agent, operation, args, scope và grant; mọi adapter pilot gọi cùng quyết định này. Không tự viết luật quyền khác nhau cho từng model.
3. **Một ledger ngân sách:** reserve trước model/tool dispatch; release phần chưa dùng, cộng usage thật; cùng task tree không được cộng thêm trần khi retry hoặc đổi engine.
4. **Một completion gate:** kiểm đủ criteria và receipt của đúng task/version trước khi chuyển completed. Câu “đã xong” của model chỉ là candidate output.
5. **Một registry deployment:** agent/brain trỏ đúng package revision; hiển thị trạng thái chưa chứng nhận nếu thiếu route capability.
6. **Một tích hợp nhỏ:** API qua hub + workflow của pilot; kênh/engine khác không bị gắn nhãn đã tuân thủ v1 nếu chưa kiểm.

Trước khi chọn module mới, đối chiếu các khả năng sẵn có của Resonance, workflow graph, task store, capability executor và usage ledger. Tái sử dụng cơ chế phù hợp nhưng không bật một subsystem kèm luật khác với quyết định đã chốt, chẳng hạn write-path hiện yêu cầu mã xác nhận riêng.

## 14. Ma trận route cần chứng nhận

“Mọi agent hưởng lõi chung” phải được kiểm theo đường chạy thật. Model giống nhau nhưng entrypoint khác có thể nhận tool, permission và prompt khác nhau.

| Route | Bằng chứng hiện có | Gate trước khi dùng harness v1 cho pilot |
|---|---|---|
| API chat -> MCP Hub | Có hub gate, guard và thu gọn output ở các vòng tool API | Manifest agent được truyền vào gate; skill thực nạp được ghi trace; effect/scope/budget cùng enforce |
| Claude SDK native/MCP | Test no-tools `[]` đã pass tại SDK | Kiểm native tools, ambient settings, tool discovery và fallback; không cho native Write/Bash vượt policy dữ liệu |
| Các CLI khác | Chưa được chứng nhận trong audit này | Bằng chứng sandbox/tool gate tương ứng; nếu không có, route này không nhận task v1 cần write |
| Workflow | Có verify_agent, helper và shared-agent fallback | Mọi node bind agent/revision/grant; kết quả trước là dữ liệu; replan không nới quyền |
| Kanban/việc nền | Có queue, lease và report | Grant đi cùng task; restart/reclaim không mất budget/receipt; queued không báo running |
| Team/Resonance | Có grant narrowing và cơ chế công việc riêng | Adapter contract thống nhất, không lấy trần/quyền mới khi chuyển giữa các subsystem |
| Bot khách hàng | Phạm vi người gọi khác chủ | Không kế thừa owner grant; kiểm sender/recipient/brain và policy từng operation |
| Factory/Probe | Có draft checks và canary; chưa có Probe cô lập hoàn chỉnh | Không credential/egress production; check bắt buộc không skip; diff quyền và ngân sách do host quản |

Mỗi ô readiness phải lưu: engine/entrypoint, version, ngày test, check IDs, evidence refs và giới hạn còn lại. Không dùng một cờ xanh toàn hệ thống thay cho ma trận này.

## 15. Hồ sơ duyệt và bàn giao của một phòng

Một hồ sơ gọn phải trả lời được các câu dưới đây trước khi mở route thật. Phần kỹ thuật có thể đính kèm máy đọc, phần anh duyệt trình bày bằng nghiệp vụ.

| Phần | Nội dung cần có |
|---|---|
| Nhận diện | Tên phòng, registry ID, thương hiệu, agent hiện có và người phụ trách nghiệp vụ |
| Việc được làm | Tối đa 3-5 task family đầu tiên; loại việc nào chỉ đọc/soạn, loại nào có quyền ghi |
| Nguồn chuẩn | Sổ/SOP/bảng giá, version và ngày hiệu lực; nguồn nào còn thiếu hoặc mâu thuẫn |
| Quyền đề nghị | Tool + operation + điều kiện tham số + scope + effect + giới hạn; liệt kê riêng quyền tự làm và quyền giao |
| Chứng minh | Baseline/candidate, check IDs, số ca/lần chạy, fail/inconclusive, holdout, evidence thực |
| Chi phí | Model calls, token thực/ước lượng, thời gian, tổng cả cây việc và giới hạn dừng |
| Deployment | Revision cũ/mới, target canary, điều kiện promote, cách nhận báo cáo |
| Quay lại | Backup/hash từng target, cách revert config, xử lý tác động đã xảy ra và conflict |
| Duyệt | Người duyệt nghiệp vụ, người duyệt quyền, phạm vi quyết định và thời điểm |

### 15.1 Hồ sơ pilot đầu tiên đề xuất

**Phòng Đối Soát:** đọc sổ theo kỳ, tìm khoản không khớp và lập báo cáo có nguồn. Không chỉnh sổ; không gửi báo cáo cho người nhận ngoài scope. Đáp án ca thử do người phụ trách xác nhận dựa trên fixture, không để agent tự sinh cả lời giải và điểm của nó.

**Phòng Thu:** tra hợp đồng, soạn đề nghị thu, sau khi được cấp đúng operation mới ghi trên sổ thử và live canary. Dùng skill đang gắn `h2o-studio-ketoan-thu-cong-no`; audit nội dung/trigger của skill trước khi quyết định viết mới. Trường hợp thiếu tiền, thiếu hợp đồng, trùng người, timeout và ghi đồng thời đều nằm trong bộ nghiệm thu.

Sau khi hai hồ sơ đạt, mới dùng chúng làm mẫu để soạn hồ sơ các phòng tiếp theo. Được tái sử dụng cấu trúc và check engine, không sao chép quyền hoặc giả định nghề của Phòng Thu sang phòng khác.

### 15.2 Nội dung cần anh duyệt một lần cho gói triển khai

- Đồng ý kiến trúc và đính chính số liệu tại mục 2, 5.
- Đồng ý thứ tự G1 -> G2 -> pilot, với gói G1 cụ thể tại mục 13.
- Đồng ý phương án khuyến nghị cho bốn lựa chọn ở mục 1, hoặc ghi rõ lựa chọn khác.
- Xác định phạm vi duyệt: triển khai code/test ở môi trường tách biệt; việc mở quyền và migration production theo hồ sơ từng pilot.

Quyết định duyệt ghi rõ gói và phạm vi được làm. Trước quyết định đó, các ticket vẫn ở trạng thái đề xuất.

## 16. Nhật ký

| Ngày | Nội dung |
|---|---|
| 2026-10-28 | Kế hoạch phòng ban ban đầu dựa trên snapshot 61 brain |
| 2026-10-28 | Thay bằng master plan chờ duyệt: tái đo skill/registry, xác minh 195 check có sẵn, tái hiện lỗi biên diff/eval/guard/canary/context, chốt đề xuất tổ chức, backlog, gates và migration; chưa triển khai các đề xuất |
| 2026-10-28 | Hoàn thiện gói G1 thành năm ticket, gói G2 tối thiểu, ma trận chứng nhận route và mẫu hồ sơ duyệt phòng; giữ trạng thái plan chờ duyệt |
| 2026-10-28 | Chủ yêu cầu triển khai theo plan: làm xong G1 (FIX-01..05) ở 1.3.41 theo thứ tự ticket, mỗi ticket có test tái hiện đỏ trước vá; thêm mục 3.3 ghi trạng thái và giới hạn. G2 chưa làm |
| 2026-10-28 | Bộ test đầy đủ ở worktree sạch cho 1.3.41: 865/894 xanh. So với 1.3.38, chỉ `test_khoi_dong_nhe` đỏ thêm; đo lại lúc máy rảnh cho thấy chi phí nạp `main` tăng nhẹ thật (đã ghi vào G1-12) |
| 2026-10-28 | Chủ yêu cầu ghi tồn đọng G1 để Astra hoặc Fable xem lại: thêm mục 3.4 (12 mục G1-01..G1-12). Phát hiện lớn nhất: kho việc thật không có việc nào gắn khóa agent, nên bằng chứng canary của FIX-05 chưa có nguồn. Đồng thời sửa mục 3.3 để không đọc như "đã xong hẳn" |
