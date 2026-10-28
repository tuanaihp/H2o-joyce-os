# Joyce Harness Standard v1.0.0

> **Final: đặc tả để triển khai và nhân bản agent.**
> Ngày: 2026-10-28. Baseline code đã đối chiếu: Joyce OS 1.3.38, commit `b78d12a4b2509d2a12134cea4f986044eb5a5548`.
> **Runtime chưa được chứng nhận tuân thủ v1.** Việc lưu tài liệu hoặc thêm frontmatter không làm hệ thống tự thực thi các quy tắc mới.

Tài liệu liên quan:

- [Audit bản cuối và các điểm đã sửa](./Joyce-harness-final-audit.md).
- [Lộ trình triển khai, kiểm tra và migration](./Joyce-harness-rollout.md).
- [Schema máy đọc được](./joyce-harness/contract.schema.json) và [bộ ví dụ tham chiếu](./joyce-harness/reference.json).
- [Prompt mẫu cho các vai](./joyce-harness/prompts.md) và [ma trận nghiệm thu](./joyce-harness/acceptance.md).
- [Audit lịch sử](./Joyce-hardness.md): giữ nguyên số liệu tại lần khảo sát cũ.

## 1. Mục tiêu và quyết định nền

Joyce quản trị một công việc từ lúc nhận yêu cầu đến lúc có kết quả được kiểm chứng: hiểu mục tiêu, tìm dữ liệu, chọn cách làm, giao đúng chuyên viên, xử lý ngoại lệ và báo lại người giao việc.

Harness chuẩn gồm: runtime dùng chung + profile vai + kiến thức tổ chức/phòng + cấu hình agent + hợp đồng của từng việc. Nhân bản bằng tham chiếu phiên bản và phần cấu hình riêng; không sao chép toàn bộ tài liệu này vào prompt.

Các từ BẮT BUỘC, NÊN và CÓ THỂ lần lượt chỉ điều kiện nghiệm thu, mặc định khuyến nghị và tùy chọn.

Quyết định áp dụng:

1. Giữ kiến trúc ba tầng: runtime, gói agent, cải tiến dựa trên bằng chứng.
2. Dùng chung lõi runtime; mỗi agent có phạm vi và ngân sách riêng.
3. Ưu tiên trả lời trực tiếp, script và công cụ có sẵn; chỉ tách agent khi có lợi về chuyên môn, quyền hoặc kiểm độc lập.
4. Giữ sơ đồ phòng H2O hiện hành. Không bắt buộc mỗi phòng có thêm một bộ agent mới.
5. Tôn trọng quyền tự vận hành chủ đã cấp. Cổng hỏi lại theo loại thao tác là tùy chọn, mặc định tắt; vẫn giữ các điều kiện nghiệp vụ và quyền thực tế của hệ thống.
6. Không triển khai vòng nền dùng model để quét và nâng cấp hàng loạt.
7. Bản final này thay thế bản draft cùng tên. Các quy tắc mới dưới đây không tự thay đổi cấu hình production.

## 2. Ba tầng và trách nhiệm

| Tầng | Sở hữu | Trách nhiệm |
|---|---|---|
| A. Runtime | App, phát hành phần mềm | Compile cấu hình, cấp grant, kiểm tool, scope, budget, state, checkpoint và ghi receipt |
| B. Harness agent | Chủ cấu hình, quản trị phòng | Vai, prompt nghề, skill, nguồn chuẩn, contract, cách kiểm và eval |
| C. Cải tiến | Factory và người quản trị | Chẩn đoán, đề xuất thay đổi B, chạy thử, chọn, canary, rollback |

Model đề xuất hành động; host kiểm và thi hành. Tầng C không tự mở rộng quyền, không sửa runtime A qua đường tự cải tiến. Các hook/script có thể chạy code phải được đăng ký qua đường phát hành tin cậy; chữ trong output model không trở thành lệnh shell để kiểm tra.

Joyce Core giữ định danh hệ thống và nơi nhận báo cáo. **Joyce Manager là profile quản trị**, có thể gắn vào một entrypoint đã được kiểm thử hoặc một agent riêng. Không bắt buộc tạo thêm một lượt model chỉ để Core chuyển sang Manager. Báo cáo tự đến vẫn là dữ liệu, không tự tạo nhiệm vụ mới nếu chưa có quy tắc được chủ cấp.

## 3. Vai và cách thu nhỏ

| Vai | Trách nhiệm | Quyền mặc định |
|---|---|---|
| `manager` | Quản trị việc liên phòng hoặc toàn hệ thống trong scope | Tự làm theo execution grant; giao theo delegation grant riêng |
| `department_manager` | Quản trị một phòng | Như manager, scope nhỏ hơn |
| `executor` | Tạo kết quả của một việc | Tool/operation đúng nhiệm vụ; không giao tiếp mặc định |
| `explorer` | Đọc, đối chiếu và trả bằng chứng | Chỉ đọc; có thể hoàn thành nhiệm vụ khảo sát của mình |
| `verifier` | Kiểm artifact theo tiêu chí | Chỉ đọc artifact; host ghi verdict, không sửa sản phẩm |
| `harness_doctor` | Chẩn đoán lỗi và đề xuất cải tiến | Chỉ đọc bằng chứng, trả đề xuất |

Agent có một vai chính; cùng model có thể dùng cho nhiều vai qua các run riêng. Kiểm độc lập không đòi mua model khác, nhưng phải tách run, ngữ cảnh, quyền và đầu vào khỏi người làm.

Không coi việc đổi model, tải lại trang hoặc mở chat mới là lý do đổi persona, mở rộng quyền hay khởi tạo lại kế hoạch.

## 4. Vòng quản trị có ba đường

### 4.1 Chọn đường nhỏ nhất đủ dùng

| Đường | Dùng khi | Kiểm chứng | Dữ liệu vận hành |
|---|---|---|---|
| `direct` | Hỏi đáp, giải thích, soạn nháp trong lượt | So nguồn/tiêu chí ngay trong lượt; không bắt buộc verifier model | Trace lượt; không tự tạo Kanban |
| `task` | Có hành động, artifact hoặc nhiều bước trong cùng lượt | Script/read-back; thêm review khi cần | Task contract nội bộ và receipt |
| `durable` | Cần chạy nền, nhiều phòng, chờ hoặc khôi phục | Như task, thêm checkpoint và bàn giao | Task lưu bền, lease, người nhận báo cáo |

Hợp đồng ở đường task có thể do host dựng từ yêu cầu; không bắt chủ điền biểu mẫu JSON. Các kế hoạch do Joyce tự đề xuất không được tự chuyển thành hàng đợi. Khi công việc đã được giao, các bước cần thiết trong phạm vi đó được tiếp tục theo grant hiện có.

### 4.2 Trạng thái chuẩn

Dùng chữ thường thống nhất trong lưu trữ, API và ví dụ:

```text
received -> scoped -> planned -> queued -> running -> verifying -> completed
                                       |               |
                                       +---- paused ---+
                           waiting_owner / blocked
terminal: completed / partial / failed / cancelled
```

Đường direct có thể bỏ planned/queued; đường task đồng bộ có thể bỏ queued. Mọi đường muốn completed đều qua kiểm phù hợp. `paused` là trạng thái host do người dùng yêu cầu; không được tự coi im lặng là đồng ý tiếp tục.

| Chuyển trạng thái | Điều kiện host phải kiểm |
|---|---|
| scoped | Mục tiêu, phạm vi, tiêu chí xong và người chịu trách nhiệm rõ |
| queued | Enqueue đã có receipt; chưa được nói đang chạy |
| running | Worker đã nhận lease hoặc lượt đồng bộ đã bắt đầu |
| verifying | Có artifact/evidence và revision cần kiểm |
| completed | Các tiêu chí bắt buộc pass, không còn tác động chưa rõ kết quả |
| waiting_owner | Thiếu quyết định hay quyền thực sự cần thiết, nêu một câu hỏi cụ thể |
| blocked | Vướng dữ liệu, dịch vụ hoặc phụ thuộc; ghi điều kiện đánh thức |
| partial | Kết thúc với phần dùng được; không tính là hoàn thành đầy đủ |
| failed | Dừng vì lỗi không phục hồi trong giới hạn |
| cancelled | Nhận yêu cầu hủy, dừng cả con; ghi tác động đã xảy ra trước lúc hủy |

`waiting_owner`, `blocked`, `paused` không tự chạy lại theo model. Host resume khi có sự kiện hợp lệ và revalidate grant. Nếu chủ đổi mục tiêu, tăng `task_version`, sửa tiêu chí và vô hiệu verdict cũ; hủy phần con không còn phù hợp.

### 4.3 Hành vi quản trị bắt buộc

- Xác định nguồn chuẩn và độ mới trước khi kết luận về hiện tại.
- Mỗi việc có một accountable owner; agent con là assignee, không làm mất trách nhiệm của owner.
- Ưu tiên việc đang bị chặn, deadline và phụ thuộc theo policy đã cấp; không tự đổi độ khẩn chỉ để vượt quota.
- Câu trả lời cuối nêu kết quả, bằng chứng chính, phần chưa đạt và bước tiếp theo thật sự cần.
- Việc nền ghi người nhận từ kênh nguồn. Nếu cần tổng hợp sau nhiều job, host/workflow phải có bước tổng hợp và dependencies.
- Không hứa sẽ tự quay lại khi không có job hoặc cơ chế tiếp tục đã đăng ký.

## 5. Kế thừa cấu hình và phân quyền là hai việc khác nhau

### 5.1 Lắp cấu hình

```text
platform -> role profile -> organization -> department -> agent override -> task constraints
```

Đây là thứ tự **lắp tài liệu và cấu hình**. Executor không kế thừa quyền làm việc của Joyce Manager như một lớp cha phần mềm. Explorer/executor/verifier dùng profile riêng và cùng base.

V1 dùng một chuỗi overlay có thứ tự, mỗi tham chiếu gồm ID và version được pin. Không đa kế thừa tự do hoặc dùng `latest` trong run production. Compiler từ chối chu trình, trùng layer, loại layer sai vị trí và tham chiếu không tồn tại.

| Trường | Merge |
|---|---|
| Luật hệ thống, owner rules | Giữ các mục được bảo vệ; thêm luật có ID và nguồn; xung đột cần giải quyết trước active |
| Scope, tool, operation, effect | Kế thừa khi thiếu; khai rõ thì chỉ thu hẹp tập ứng viên; grant host là trần ngoài cùng |
| Deny | Hợp tất cả deny, thắng allow |
| Budgets | Giá trị nhỏ nhất của các giới hạn có khai |
| Skills | Hợp ID đã pin; skill không cấp quyền tool |
| Verification | Hợp check bắt buộc; không bỏ check cấp trên |
| Contracts | Cùng ID/version hoặc refinement đã được validator đăng ký; không tự suy tương thích từ văn xuôi |
| Prompt nghề | Bổ sung đúng phạm vi; nguồn động không ghi đè policy |

Danh sách rỗng hợp lệ: `tools: []` nghĩa không có tool; `delegates: []` nghĩa không được giao; scope rỗng nghĩa không truy cập dữ liệu đó. Agent vẫn có thể tính toán/trả lời thuần chữ. **Rỗng không phải lỗi và cũng không phải toàn quyền.**

Trường thiếu chỉ có nghĩa kế thừa ở bản authored. Sau compile, manifest resolved phải đủ mọi trường bắt buộc. Không resolve được thì không active. `null`, chuỗi rỗng ở ID, key sai chính tả và schema không hỗ trợ đều bị từ chối.

### 5.2 Schema và vị trí lưu

Giữ agent ở `agents/<slug>.md`, cùng các trường hiện hành `name, slug, role, skills, model, model_provider, tags`. Thêm cấu hình authored dưới khóa `harness`; không chuyển tất cả metadata sang `identity` rồi làm loader cũ mất tên/model.

Schema trong [contract.schema.json](./joyce-harness/contract.schema.json) mô tả **manifest resolved** và các contract truyền giữa host/agent. Nó không khẳng định parser authored, compiler hoặc permission gate đã tồn tại.

Compiler phải xuất:

- Manifest resolved hợp schema.
- Nguồn và revision của từng layer.
- Bản đồ grant hiệu lực và deny.
- Trạng thái hỗ trợ theo engine/entrypoint.
- Diagnostic với đường dẫn trường lỗi; không âm thầm bỏ trường quyền lạ.

Giữ nội quy ở `Joyce/noi-quy.md`, memory ở `memory/`, skill ở `skills/`. Behavioral eval v1 đặt ở `Joyce/evals-v1/`, tách khỏi `Joyce/evals/` đang được Factory đọc như các phép kiểm chuỗi.

## 6. Quyền thực thi và quyền giao việc

### 6.1 Effect là tập độc lập

Loại bỏ `max_effect` của draft. Dùng `allowed_effects`:

| Effect | Nghĩa |
|---|---|
| `read` | Đọc dữ liệu thuộc scope |
| `internal_write` | Ghi nháp, artifact nội bộ hoặc trạng thái công việc |
| `business_write` | Ghi sổ nghiệp vụ, cập nhật hợp đồng/kho |
| `external_write` | Gửi tin, đăng bài, thay đổi hệ thống ngoài |
| `financial_write` | Chuyển tiền, hoàn tiền, tạo cam kết thanh toán |
| `policy_write` | Thay policy, harness hoặc cấu hình quyền |
| `destructive` | Xóa hoặc thay đổi khó phục hồi |

Không có thứ bậc ngầm. Cho financial_write không đồng nghĩa có policy_write hay destructive. Một operation có thể mang nhiều effect, và phải được cấp **tất cả**. Ghi nhận một khoản thu đã có chứng từ thường là business_write; chuyển tiền thật là financial_write, có thể đồng thời external_write.

Tính toán không có tác động dùng tập effect rỗng; không cần effect `none`.

### 6.2 Quyết định cho từng lời gọi

Host chỉ cho chạy khi đồng thời đạt:

1. Principal hiện tại và connection có quyền.
2. Task nằm trong ủy quyền hiện hành của chủ.
3. Tool và operation nằm trong execution grant; không trúng deny.
4. Effect do registry xác định là tập con của allowed_effects.
5. Resource, brain, đường dẫn và trường dữ liệu nằm trong scope.
6. Tham số qua schema và argument policy; hạn mức nghiệp vụ còn hiệu lực.
7. Budget, deadline và trạng thái task cho phép.
8. Approval rule cụ thể, nếu chủ đã bật hoặc hệ thống nghiệp vụ yêu cầu, được đáp ứng.

Effect, identity, scope và approval state do host lấy từ nguồn tin cậy; không tin giá trị do model tự khai. Với tool đa năng, operation rỗng hoặc chưa phân loại phải từ chối. Wrapper và lệnh batch kiểm từng thao tác con, chống đi vòng qua run-tool, shell hoặc MCP native.

Giữ các mode hiện hành: `suggest/readonly`, `auto/safe`, `full`. V1 là lớp thu hẹp bên dưới, không tự nâng mode. `full` không bỏ gate v1. Không suy từ mode sang quyền tài chính/policy/destructive mà thiếu operation grant cụ thể.

Cổng hỏi lại bổ sung mặc định tắt. Khi đã có standing authorization hợp lệ, không hỏi lại từng lần. Giữ nguyên hạn mức chi và các approval nghiệp vụ hiện có; không thêm luật chung “mọi tiền phải hỏi chủ”.

### 6.3 Giao việc không cấp quyền tự làm

Host cấp cho manager hai tập:

- `execution`: operation manager được tự gọi.
- `delegation`: grant tối đa được chuyển cho từng agent đích, đã gắn brain ID và slug cụ thể.

Grant con = giao của delegation grant cha, manifest con, task constraint, quyền principal/connection và policy hiện hành. Một manager chỉ đọc sổ có thể giao chuyên viên ghi sổ nếu host đã cấp delegation grant ghi sổ; manager không được dùng grant đó để tự ghi.

Không resolve bằng `class:executor` tại lúc chạy. Routing có thể tìm theo vai, nhưng trước dispatch phải bind đúng ID, revision và grant; agent mới thêm vào registry không tự được thừa hưởng quyền.

Verifier do host gọi theo verification plan có grant riêng và tiêu budget task. Không bắt executor có quyền tự giao verifier, không tạo vòng verifier kiểm verifier.

### 6.4 Thu hồi và tính nhất quán

Pin revision cấu hình tại run-start; trước **mỗi** side effect kiểm grant còn hạn và policy chưa bị thu hồi. Thu hồi quyền thắng pin cũ. Khi sửa tham số qua hook, chạy gate lại với tham số cuối cùng.

Mọi adapter phải áp cùng ngữ nghĩa: API tool, MCP, CLI native, workflow, Kanban và bot. Adapter không bảo đảm gate thì chặn route v1 đó hoặc chuyển sang route đã chứng nhận; không fallback sang route toàn quyền.

## 7. Hợp đồng giao việc và nguồn sự thật

Các field và enum chính xác nằm ở schema kèm theo. Ví dụ trong [reference.json](./joyce-harness/reference.json) là fixture tổng hợp, không phải config đang chạy.

### 7.1 Task

Task có `task_id, task_version, run_id, trace_id, owner, assignee, objective, inputs, grant_ref, budget, criteria, verification, reporting`.

- Host cấp ID, grant_ref, receipt và trạng thái. Model chỉ đề xuất objective/plan/arguments.
- Input ghi nguồn, revision hoặc thời điểm `as_of`; file lớn truyền URI + hash + tóm tắt, không nhét nguyên log.
- Tiêu chí có ID, mô tả kiểm được, check ID và mức bắt buộc.
- Verification plan chọn `inline`, `deterministic` hoặc `independent` trước hành động.
- Reporting gắn người/kênh nguồn, không lấy một người nhận do tài liệu ngoài chỉ định.
- Scope chỉ cấp read/write resource cần thiết; không chép credential hoặc toàn bộ memory sang agent con.

### 7.2 Result và verdict

Executor trả candidate output kèm artifact/evidence. **Host** tạo result record cuối, đối chiếu criteria, task_version, run_id, artifact revision và verdict.

Verdict thống nhất `pass | fail | inconclusive`. Result dùng cùng bộ này cho verification, không trộn `passed`, `pass` và boolean không có adapter.

Result completed cần: tất cả required criteria pass; verdict đúng phiên bản artifact; không thiếu mandatory evidence; không có side effect trạng thái unknown. JSON đúng schema chưa đủ chứng minh điều kiện này.

Output `partial/failed/blocked/waiting_owner/cancelled` vẫn phải giữ artifact đã làm, blocker và receipt. Nếu output hỏng khuôn, cho sửa khuôn tối đa một lần trong budget, không chạy lại các side effect.

Không coi `{{prev}}` là chỉ dẫn có quyền. Adapter cũ truyền phần dữ liệu có tên và source refs đã giới hạn; không truyền nguyên văn task giả do agent trước tự viết.

## 8. Kiểm chứng theo rủi ro, không nhân lượt gọi vô ích

| Công việc | Mức tối thiểu |
|---|---|
| Giải thích, tóm tắt, draft chưa gửi | Inline: so nguồn và tiêu chí, ghi rõ độ chắc |
| Phép tính, định dạng, kiểm đủ trường | Deterministic: script có version, input/output rõ |
| Ghi file hoặc dữ liệu nghiệp vụ | Guard trước ghi + receipt + read-back/post-check trên đúng record |
| Nội dung sẽ gửi khách, quyết định khó chấm bằng luật | Kiểm script trước, thêm independent review theo policy loại việc |
| Task rủi ro cao theo policy phòng | Verification plan bắt buộc do policy cấu hình; không cho agent tự bỏ |
| UI hoặc file xuất | Mở artifact thực tế, kiểm nhìn thấy khi tiêu chí yêu cầu |

Không tạo verifier model chỉ để đọc lại verdict script đã đủ rõ. Với independent review: run khác executor, chỉ nhận artifact, tiêu chí, nguồn và trace cần thiết; không nhận lời tự chấm như bằng chứng.

Lỗi check, timeout, check không tồn tại hoặc bị bỏ qua = inconclusive. Không dùng “không có fail” làm pass. Verdict hợp lệ phải có `check_id, subject_version, subject_hash, evidence, evaluated_by`; verifier đọc dữ liệu nghiệp vụ nhưng host chịu trách nhiệm lưu kết luận.

Retry sửa artifact tối đa một lần mặc định; giá trị khác nằm trong policy được pin. Hết retry giữ kết quả chưa đạt, không đổi rubric để cho qua.

## 9. Hành động có tác động, retry và khôi phục

Một khóa idempotency cho cả task là chưa đủ. Mỗi hành động có `action_id` và khóa host sinh từ task_id + task_version + action_id + đích chuẩn hóa. Hai hành động khác nhau phải khác khóa; retry cùng hành động dùng cùng khóa.

Quy trình:

```text
validate -> reserve budget/claim -> record intent -> execute -> record receipt
         -> read-back -> verify -> checkpoint
```

Receipt ghi operation, hash args đã che dữ liệu nhạy cảm, revision dữ liệu trước/sau nếu có, remote ID và trạng thái `confirmed | failed | unknown`.

- Timeout sau khi gửi có thể nghĩa dịch vụ đã làm xong. Với unknown, tra remote ID/idempotency record trước; không gửi lại mù.
- Nếu provider không hỗ trợ dedup hoặc tra cứu đáng tin, chuyển blocked và đối soát. Không hứa exactly-once.
- Tác vụ đồng thời trên cùng record dùng version check/transaction/lease; không chỉ chống trùng theo title hoặc cửa sổ thời gian.
- Worker restart tiếp tục từ checkpoint đã xác nhận; kiểm lease còn thuộc worker trước commit.
- Hủy hoặc hết budget: ngừng dispatch và gọi con mới, yêu cầu dừng con đang chạy, ghi tác động đã xác nhận và tác động chưa rõ.

Rollback harness chỉ khôi phục cấu hình tương lai, không đảo được tin nhắn đã gửi hay tiền đã chuyển. Dữ liệu dùng compensation có quyền riêng và audit; thao tác không đảo được ghi rõ recovery plan. Không overwrite cả brain từ backup nếu sẽ mất dữ liệu người dùng mới tạo.

## 10. Ngân sách dùng chung toàn cây công việc

Các giới hạn phải bao gồm manager, con, retry, verifier, fallback và tool calls. Tạo agent mới không làm reset budget. Host reserve quota nguyên tử trước dispatch, thu hồi phần không dùng khi run kết thúc.

Mặc định **để pilot đo và điều chỉnh**, không phải SLA sản phẩm:

| Loại | Vòng model tối đa/run | Deadline active | Con đồng thời | Độ sâu giao | Model calls toàn task | Token toàn task |
|---|---:|---:|---:|---:|---:|---:|
| Manager | 12 | 15 phút | 2 | 2 | 24 | 100.000 |
| Executor | 8 | 10 phút | 0 | 0 | 12 | 50.000 |
| Explorer | 6 | 5 phút | 0 | 0 | 8 | 30.000 |
| Verifier | 4 | 5 phút | 0 | 0 | 6 | 20.000 |

Deadline tuyệt đối áp vào run đang hoạt động; chờ chủ có trạng thái riêng, resume nhận deadline mới được host ghi. Deadline không tự gia hạn vì đổi model. Tool call có timeout hữu hạn trong thời gian còn lại.

Đếm input/output và token cache theo usage nhận được; ghi usage chưa biết, không biến thành 0. Với engine không đo token chính xác, dùng reservation bảo thủ, trần calls và thời gian; công khai trạng thái estimated. Với API trả phí có thể thêm trần tiền đã cấu hình.

Không nhầm 12 lần chạy Probe với 12 lần gọi model: mỗi run có nhiều vòng. Budget Probe là riêng, không lấy quota task production.

## 11. Prompt, context và memory

Prompt luôn bật gồm sáu mục: sứ mệnh, phạm vi, cách làm INV, quy tắc nghề DOM, kiểm chứng/escalation và đầu ra. [Các prompt mẫu](./joyce-harness/prompts.md) đã được viết để thu nhỏ theo vai.

Prefix tĩnh đứng trước context động. Nạp skill theo trigger, tải tool theo registry, đọc nguồn theo nhu cầu. Không tải toàn bộ 44 phòng để trả một câu hỏi. Cache là tối ưu hiệu năng; khi nguồn mới hơn phải cập nhật, không giữ dữ liệu cũ để tăng hit rate.

Ngưỡng context đề xuất: bắt đầu compact khi payload dự kiến vượt 70% cửa sổ khả dụng; dành ít nhất 20% cho output và tool tiếp theo. Host điều chỉnh theo model đã cấu hình. Output tool lớn đưa sang artifact URI, giữ ID, hash và trích phần liên quan.

Checkpoint/compaction giữ: mục tiêu, task_version, scope, criteria, deadline, grant_ref, action receipts, unknown effects, blocker, next step và source refs. Credential không nằm trong checkpoint đưa vào prompt.

Memory tách:

| Lớp | Nội dung | Cách cập nhật |
|---|---|---|
| Luật chủ và policy | Chỉ dẫn bền, có nguồn và phạm vi | Đường xác thực, không đẩy ra vì giới hạn số bài học |
| Tri thức tổ chức/phòng | SOP, nguồn chuẩn, định nghĩa nghiệp vụ | Version, owner, hiệu lực; đọc mới khi cần |
| Bài học agent | Bài học tái dùng đã có bằng chứng | Model đề xuất, host ghi theo cơ chế duyệt hiện có |
| Task/CRM | Sự kiện cụ thể, khách/hợp đồng, log | Store nghiệp vụ hoặc task; không nhét vào luật luôn bật |

Phân biệt authority và freshness: nguồn cấp trên không khiến một con số cũ thành đúng. Khi hai nguồn mâu thuẫn, kiểm thời điểm và source of truth; chỉ hỏi chủ nếu không tự phân giải được mà ảnh hưởng hành động.

Không cấm lưu sự kiện khách ở CRM hoặc log. Cấm biến sự kiện đơn lẻ thành quy tắc chung. Quyền xem/sửa/quên và tắt học tiếp tục được tôn trọng.

## 12. Eval đủ để quyết định phát hành

Bộ [acceptance](./joyce-harness/acceptance.md) xác định ca, fixture và assertion; đây là yêu cầu nghiệm thu, không phải báo cáo test production đã pass.

Tách ba loại:

1. Static/contract: schema, merge, registry, reference, dependency.
2. Behavioral: chạy agent với fixture, kiểm tool trace, artifact, quyền và kết quả.
3. Recovery/concurrency: timeout, crash, duplicate dispatch, revoke, cancel, resume.

Dùng dữ liệu tổng hợp/đã che. Tách development cases khỏi holdout chưa đưa cho người sửa harness. Chạy baseline và candidate trên cùng snapshot/tool giả, model và tham số được ghi rõ. Một lần pass không chứng minh ổn định; pilot chạy mỗi ca hành vi ít nhất ba lần.

Cổng phát hành ban đầu:

- Tất cả ca bắt buộc chạy đủ, không skip; mọi assertion ranh giới quyền và hoàn thành đều pass.
- Baseline cùng điều kiện; candidate không giảm số ca đạt, không thêm false completed.
- Tổng chi phí/calls/thời gian trong ngân sách; nếu tăng hơn 10% mà không cải thiện chất lượng đo được, giữ baseline.
- Ca fail hoặc inconclusive chưa phân giải: không promote.
- Các ngưỡng là mặc định vận hành v1, không phải số hiệu quả đã đo.

## 13. Tự cải tiến có bằng chứng

Kích hoạt: chủ yêu cầu, hai lần sửa cùng loại trong bảy ngày, hoặc hai lỗi verify/post-check cùng chữ ký. Incident nghiêm trọng có thể khóa rollout ngay từ lần đầu; không đợi đủ hai lần.

Doctor trước tiên phân loại: dữ liệu thiếu/cũ, tool/permission, cách làm, kiến thức nghề, verifier, hạ tầng, hoặc model. Tool bị chặn có thể là hoạt động đúng của quyền; không mặc định là lý do mở quyền.

Chọn thay đổi nhỏ nhất có hiệu quả: prompt -> skill -> script/hook -> phát hành runtime. Không đòi mô hình nhiều người sửa cho một lỗi chính tả. Với thay đổi hành vi phức tạp, có thể tách INV và DOM:

1. Gom bằng chứng đầy đủ qua artifact refs, giữ bản đã che dữ liệu.
2. Propose candidate; validator chặn phạm vi/quyền/budget vượt trần.
3. Probe baseline và candidate; nếu có Compose thì **chạy lại bản composed**.
4. Chọn dựa trên hành vi, kiểm ẩn danh khi dùng judge; không chỉ so chữ.
5. Holdout và policy checks độc lập.
6. Canary, giữ bản cũ khi không đủ bằng chứng.
7. Lưu cue, bài học, evidence, revision, confidence và phạm vi áp dụng.

Sandbox Probe cần bản sao dữ liệu **và** chặn đường ra production: credential tách, egress bị khóa/allowlist test, remote MCP giả, schedule/webhook/notification production bị vô hiệu. Copy brain riêng không đủ.

Mặc định một lượt cải tiến: tối đa 500.000 token, 80 model calls, 20 phút, một candidate hoạt động cùng lúc mỗi target; tối đa hai lượt tự kích hoạt mỗi target/tuần. Đây là cấu hình đề xuất cho pilot, chưa thay các trần chủ từng chốt hoặc config thật. Chạm trần giữ baseline. Lịch poll Factory xử lý đề xuất có sẵn không đồng nghĩa được gọi model để quét nâng cấp hàng loạt.

## 14. Phát hành, canary và rollback

Package có `spec_version`, `harness_version` và `package_revision`. Revision do host hash manifest resolved, prompt/policy, skill/check/contract versions và dependency lock; không chỉ hash file prompt. Dynamic data có run snapshot refs riêng. Thay model ghi engine/model/run profile mới, re-eval; không phải sửa quyền.

```text
draft -> validated -> eval_passed -> canary -> active -> deprecated
                                rollback <- canary/active
```

Canary mặc định một brain và một agent; đủ **24 giờ lẫn 20 task phù hợp đã qua kiểm** mới xét promote. Không có traffic thì giữ canary, không tự xem là thắng. Sau bảy ngày thiếu mẫu, giữ baseline và ghi insufficient_evidence.

Ngừng canary ngay khi có unauthorized successful effect, ghi trùng, mất dữ liệu hoặc false completed. Với chất lượng, so với baseline cùng loại việc; fail rate tăng hơn 5 điểm phần trăm thì ngừng promote và điều tra, không suy kết luận thống kê mạnh từ mẫu nhỏ.

Áp/rollback dùng expected revision (compare-and-swap). Nếu chủ đã sửa file sau snapshot, không ghi đè; báo conflict và merge có kiểm. Giữ backup tối thiểu 30 ngày và ít nhất hai revision gần nhất; không tự xóa backup trong migration đầu.

Không tự áp sửa grant, effect, delegate, approval, budget, policy hoặc mã hook qua low-risk auto. Thay đổi nội dung trong vùng được phép có thể tự áp khi eval/canary đạt. Host phân loại diff, không tin `risk: low` do model ghi.

## 15. Quan sát vận hành

Event dùng duy nhất: `accepted, scoped, planned, queued, started, delegated, tool_called, effect_recorded, verification_started, verification_finished, waiting_owner, blocked, paused, resumed, closed`.

Không bắt event delegated cho task không giao ai. Host ghi timestamp, task_id/version, run_id, parent_run_id, trace_id, agent ID, package_revision, grant_ref, engine/model, trạng thái và evidence refs. Không cần hoặc lưu suy nghĩ nội bộ của model.

Chỉ số khởi đầu:

| Chỉ số | Định nghĩa |
|---|---|
| Completion | completed / terminal tasks, báo cancelled riêng để thấy mẫu số |
| First-pass verification | Task pass kiểm lần đầu / task đã được kiểm; missing/inconclusive không tính pass |
| Rework | Task cần sửa sau verify / task đã được kiểm |
| False completed | Completed nhưng read-back/review chứng minh không đạt; guardrail bằng 0 trong eval |
| Human correction | Task có chủ sửa / task đã được review; tách hỏi thiếu input |
| Blocked age | Thời gian trong blocked theo task, ưu tiên p95 và việc lâu nhất |
| Cost per completion | Tổng usage của cả cây task / completed; không bỏ chi phí failed |
| Unauthorized effect | Lời gọi bị chặn báo riêng; side effect vượt quyền thành công phải bằng 0 |

Trace giữ dữ liệu tối thiểu cần audit, che secrets/PII và chịu chính sách lưu/xóa của tổ chức. Không coi log chat sửa được là sổ receipt bất biến. Dashboard dùng sau khi các mẫu số được ghi đúng.

## 16. Golden package và áp dụng từng cấp

Bộ reference gồm manager, explorer, executor và verifier với ID fixture rõ ràng. Manager có execution grant nhỏ để điều phối và delegation grant riêng cho chuyên viên. Tất cả examples được kiểm bằng schema; chúng chưa được nạp vào agent thật.

Để áp dụng vào H2O:

1. Bind brain ID thật từ registry, không đoán từ tên thư mục hoặc copy ID fixture.
2. Bind tool/operation/check có thật và routes đã chứng nhận.
3. Giữ nguyên agent chủ đã sửa; chỉ bổ sung authored harness/profile references sau dry-run.
4. Mỗi phòng chọn việc có thật, owner, input/output, nguồn chuẩn và cách kiểm.
5. Chỉ tách thêm executor khi đủ khác biệt nghề/quyền; có thể dùng explorer/verifier chung bằng các run cách ly.
6. Nhân qua dependency đã pin và overlay phòng; nâng base không tự thay mọi agent đang chạy.

Mục đích cuối: Joyce vẫn là đầu mối quen thuộc với chủ; runtime chọn đúng profile và cấp grant cho từng việc. Người dùng không phải hiểu lớp schema để giao việc.

## 17. Compatibility và điều kiện được chạy production

| Nội dung | Hiện trạng đọc từ code 1.3.38 | Việc cần làm |
|---|---|---|
| Metadata agent | Có name/role/skills/model, giữ khóa lạ khi save | Đọc authored harness và compile v1 |
| Joyce Core | Slug/kênh hệ thống riêng, không tự cấp quyền | Tích hợp profile quản trị ở entrypoint đã kiểm |
| Tool gate | Có mode/permission theo lời gọi; CLI có đường allowlist rỗng thành bypass | Thêm v1 adapter: no-tools khác legacy unset |
| Workflow | Có graph contract, checkpoint, replan grant | Ánh xạ contract v1; kiểm mỗi node/tool |
| Tool `joyce_task` | Queue/list, route workflow, không có gọi agent theo class | Binder/dispatcher thật; không giả định tool mới đã có |
| Factory eval | Kiểm chuỗi bản nháp, check lạ có thể bị bỏ qua | Runner behavioral riêng và gate không bỏ qua check |
| Canary | Có backup và cơ chế tín hiệu | Thêm đủ mẫu, revision conflict, compare với baseline |
| Memory | Có owner rules và lesson approval | Giữ cơ chế, bổ sung provenance/version khi cần |

V1 không có `runtime_min_version: 1.3.38`: chưa có bản runtime nào được chứng nhận trong lần sửa tài liệu này. Thay bằng `required_features` và readiness matrix theo engine/entrypoint. Trường quyền unsupported làm route không đủ điều kiện v1; không chỉ hiển thị cảnh báo rồi vẫn chạy.

Legacy chưa opt-in giữ hành vi cũ, không gắn nhãn v1. Migration không đổi trực tiếp ý nghĩa tất cả allowlist rỗng cũ. Adapter phân biệt legacy unset và v1 explicit empty, chuyển thành cấu hình no-tools thật của từng engine, kèm test hồi quy.

## 18. Definition of Done

### Đặc tả final

- Có vai, vòng đời, merge rules, grants, contract, action/recovery và rollout thống nhất.
- Có schema máy đọc được, ví dụ hợp lệ, negative examples và prompt mẫu.
- Có audit chỉ ra giới hạn bằng chứng; không gọi tài liệu là tính năng đã triển khai.
- Có ma trận acceptance đủ làm backlog cho đội triển khai.

### Runtime/agent v1

- [ ] Parser authored, compiler, schema và dependency pin chạy đúng.
- [ ] Mọi trường quyền, scope, operation, budget, grant con enforce trên route được bật.
- [ ] No-tools, revoke, wrapper, fallback không mở đường vượt quyền.
- [ ] Host kiểm criteria/verdict/hash trước completed.
- [ ] Receipt/action dedup, crash, retry, cancel/resume qua acceptance.
- [ ] Có eval baseline + holdout, đầy đủ ca bắt buộc, không skip.
- [ ] Có backup, canary đủ mẫu, rollback thử và xử lý sửa tay đồng thời.
- [ ] Có báo cáo đúng kênh, memory control và trace.
- [ ] Manifest effective và readiness matrix xác nhận route được bật; route khác chưa active v1.

## 19. Nhật ký và quyết định

| Mã | Quyết định final |
|---|---|
| JH-001 | Một core runtime, các profile vai dùng chung base |
| JH-002 | Manager là profile hành vi; Core là định danh/entrypoint hệ thống |
| JH-003 | Tách execution và delegation grant, host quyết định |
| JH-004 | Effect là tập độc lập; không dùng max_effect |
| JH-005 | Missing là kế thừa authored, empty là không cấp; resolved không mập mờ |
| JH-006 | Kiểm chứng theo loại việc; host chốt completed |
| JH-007 | Receipt và idempotency theo action; unknown không retry mù |
| JH-008 | Budget toàn cây, các route/engine cùng enforcement |
| JH-009 | Probe cô lập credential/egress, có holdout; canary cần traffic |
| JH-010 | Final đặc tả không đồng nghĩa runtime sẵn sàng |

| Ngày | Phiên bản | Nội dung |
|---|---|---|
| 2026-10-28 | 1.0.0-draft | Bản đầu, chưa có schema thực và còn mâu thuẫn grant/verify/migration |
| 2026-10-28 | 1.0.0 final | Audit lại code; sửa các mâu thuẫn, giảm chi phí điều phối, chốt contract/reference/acceptance và rollout |
| 2026-10-28 | 1.0.0 final | Hoàn thiện các file kèm theo (schema, reference, prompts, acceptance, final audit) và test `test_joyce_harness_schema.py`; rollout thêm giai đoạn 0A theo quyết định của chủ; đặc tả không đổi quy tắc |
