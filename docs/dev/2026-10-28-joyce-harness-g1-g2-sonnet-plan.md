# Joyce Harness: kế hoạch giao Sonnet 5.5 khép G1 và nối G2

> **Trạng thái (28/10/2026): chủ đã duyệt GÓI A, riêng D4 chọn phương án nhẹ hơn (xem mục 2.4). Gói B CHƯA được duyệt. Các task A00 trở đi được làm trên nhánh `claude/crm-v2-final-1-3-35`, không merge main; tiến độ ghi ở mục 8.**
>
> Ngày: 28/10/2026. Audit code tại Joyce OS `1.3.41`, commit `8a981e6`; cập nhật báo cáo test theo commit tài liệu `6b22a33` và thông tin chủ bổ sung. Nhánh `claude/crm-v2-final-1-3-35`. Working tree sạch trước lượt viết plan đầu tiên; các thay đổi tài liệu của lượt đó được giữ khi cập nhật.
>
> Spec gốc: [Joyce Harness](./Joyce-harness.md). Backlog gốc: [master plan, mục 3.4](./Joyce-harness-phong-ban-ke-hoach.md#34-tồn-đọng-của-g1-và-việc-reviewer-cần-xem). Bản này bổ sung quyết định thiết kế và task cho 12 tồn đọng; không thay thế toàn bộ master plan, không chứng nhận các gate G2 khác đã xong.

## 1. Kết quả cần đạt và phạm vi duyệt

Sau gói A, hệ thống giữ được bản sửa riêng, ngừng tự áp thay đổi hành vi chưa đủ điều kiện, có đường khôi phục kiểm chứng được và hiển thị đúng phần chưa được kiểm. Sau gói B, canary lấy bằng chứng từ lượt chạy thật, biết chính xác bản cấu hình nào đã chạy và chỉ mở trên route đã được kiểm chứng.

Đề xuất **duyệt gói A trước**. Gói B được mô tả đủ để nối tiếp, nhưng chỉ bắt đầu khi anh duyệt phạm vi B. Duyệt A cho phép sửa code và test A, không tự động cho phép thay quyền phòng, áp proposal đang tồn, nhân sang 44 phòng hay mở canary production. Quy trình nhánh, phiên bản, PR và phát hành thực hiện theo [quy ước dev](../quy-uoc-dev.md) trong phạm vi được giao.

Ngoài phạm vi lần này: viết lại toàn bộ runtime; thay model hàng loạt; sửa 30 skill tại chỗ; tự tạo thêm 14 trưởng phòng; triển khai đủ compiler và ngân sách toàn cây của master plan. Vẫn giữ sáu phòng pilot và 11 khối đang có. Không dựng thêm kho nhiệm vụ để thay Kanban/chat/workflow.

## 2. Kết luận audit và các quyết định đề xuất

### 2.1 Những điều phải hiểu đúng trước khi code

- `_proposal_apply` ghi ứng viên vào **phòng nguồn trước** khi tạo canary. `het_han` vẫn giữ bản đó ở nguồn. Vì thế G1-01 không chỉ gây chậm nhân bản: nguồn đang chạy một bản chưa có tín hiệu lỗi đáng tin.
- `_canary_evidence` dùng khóa `agent:...` và `created_at`; không đối chiếu revision thực sự được nạp. Dù điền đủ khóa vào Kanban, vẫn chưa chứng minh tác vụ chạy đúng ứng viên. Không sửa bằng cách điền khóa giả, tìm slug trong tiêu đề hay đổi toàn bộ chat thành task.
- `_nhan_mot_dich` chỉ so với snapshot của đích. Snapshot không chứng minh đích thuộc cùng phiên bản nguồn; cần kiểm cả quan hệ kế thừa và việc đích có bị sửa sau snapshot hay không.
- `os.replace` giúp người đọc không thấy file ghi dở; nó không làm thao tác đọc-hash-rồi-ghi thành một giao dịch có điều kiện. `mtime`, `inode` hoặc đọc lại thêm một lần cũng không loại hết cuộc đua.
- Giám định bằng model và eval chuỗi không thay thế quyền do host kiểm hay test hành vi. Không coi model mạnh hơn là cách vá các lỗi này.
- Có thêm ca helper `diff_quyen` trả `[]` với hai bước trùng `id` mà bước đầu tăng quyền; YAML mở `---` nhưng thiếu dấu đóng cũng trả `[]`. Đây là kết quả diagnostic trực tiếp, **chưa phải bằng chứng toàn bộ `_proposal_apply` đều bị vượt qua**; A03 phải kiểm đầu cuối trước khi kết luận độ ảnh hưởng.
- `canaries = canaries[-50:]` có thể loại bản ghi còn hoạt động. `_nhan_mot_dich` ghi backup rồi mới lưu đường dẫn backup sau thao tác ghi đích. Cần lưu dấu vết trước khi ghi và không xóa bản ghi đang cần khôi phục.

Số `0/160` việc có khóa agent và `43/44` phòng thiếu eval được lấy từ báo cáo trong master plan tại `8a981e6`; lượt này không quét lại DB production. Không coi các con số đó là invariant. Kết quả full suite đã được bổ sung ở `6b22a33`, chi tiết mục 2.3 bên dưới; không còn ở trạng thái “đang chờ kết quả”.

### 2.2 Quy tắc để anh duyệt cùng gói A

| Quyết định | Đề xuất chốt | Ảnh hưởng |
|---|---|---|
| D1. Canary chưa có telemetry | Chặn tự đưa ứng viên hành vi vào nguồn và chặn tự nhân. Proposal vẫn được tạo, giám định và lưu nháp. Canary cũ chuyển trạng thái cần xem, ghi rõ bản nào còn đang chạy | Ngăn mở thêm thử nghiệm không quan sát được; không âm thầm rollback file cũ |
| D2. Bản sửa riêng | Đề xuất duyệt G1-02: chỉ tự nhân khi nội dung đích đúng bằng bản nguồn trước sửa, thuộc package/baseline đã xác minh và vẫn bằng snapshot trước ghi. Đích khác baseline từ trước là `override` chờ chủ xem | Giữ khác biệt của phòng; việc hợp nhất trở thành proposal riêng có diff |
| D3. Thân prompt và nội quy | Mọi thay đổi nội dung được model dùng để quyết định hành vi cần duyệt khi chưa có gate hành vi đầy đủ. Bao gồm body, `role`, `goal`, lời giao việc workflow và metadata được đưa vào prompt | Tạm giảm tự áp; không dựa vào regex hoặc model để chứng nhận “không nới quyền” |
| D4. Eval | Đề xuất duyệt G1-09: mặc định `eval_bat_buoc=true` cho brain phòng ban theo registry. Eval invalid hoặc fail luôn chặn áp. Missing chặn tự áp và tự nhân đối với cấu hình hành vi; vẫn cho đọc, chạy bản đã duyệt, tạo proposal và thử sandbox | Chặn phần lớn tự áp chưa có bộ kiểm; không làm phòng ngừng phục vụ bằng bản đã duyệt |
| D5. Quyền | Quyền thực thi do host cấp và kiểm theo operation, tham số, brain và revision; lời trong prompt không cấp quyền. Route chưa chặn được ghi ngoài hub chưa được chứng nhận | Đây là yêu cầu cần code/test, không phải tuyên bố runtime hiện đã đạt |
| D6. Khôi phục | Khôi phục theo từng đích, chỉ khi file hiện tại còn đúng bản do lần deploy đó ghi. Có sửa mới thì báo conflict và trình diff | Tránh rollback đè sửa tay; backup không tự tạo ra quyền ghi đè |

`eval_bat_buoc=false` cũ không được dùng như ngoại lệ tự áp hành vi trong chính sách mới. Tách **có nạp/chạy eval** khỏi **có đủ điều kiện tự áp**; không chỉ đổi một boolean rồi tuyên bố xong. Ngoại lệ thiếu eval chỉ dành cho thử nghiệm sandbox có phê duyệt gắn đúng revision; không cho vượt qua eval invalid/fail hoặc grant bị từ chối.

D2 và D4 vẫn **chờ anh duyệt**, thông tin bổ sung kết quả test không phải phê duyệt triển khai. Sonnet hiện thực default ở lớp chính sách hiệu lực sau duyệt, không ghi hàng loạt config 61 brain. Nhận diện phòng ban bằng registry; Brain Default/brain khối không tự bị đổi mặc định chỉ vì tên gần giống. UI phải hiển thị chính sách hiệu lực và lý do cấu hình `false` legacy không cho bỏ qua gate hành vi, tránh báo một đằng chạy một nẻo.

Gói A chưa mở tự áp body. Gói B chỉ được đề xuất mở lại theo từng package, loại thay đổi và route sau khi có bằng chứng; quyền, budget và phạm vi vẫn theo chủ duyệt. Duyệt một lần không cho phép agent tự nâng quyền về sau.

### 2.3 Cập nhật bằng chứng test 1.3.41

| Hạng mục | Kết quả được báo cáo | Cách sử dụng trong plan |
|---|---|---|
| Full suite ở worktree sạch 1.3.41 | **865/894 xanh** | Chưa phải full suite xanh. Còn 29 mục ngoài số xanh; cần log runner để tách fail/error/skip, không suy ra 29 lỗi code |
| Đối chiếu suite với 1.3.38 | Chỉ `test_khoi_dong_nhe` đỏ thêm | Đây là baseline đối chiếu danh sách test; không đánh đồng với baseline benchmark 1.3.39 |
| Benchmark 1.3.39, máy rảnh, 5 lần | Tỷ lệ nạp `main` so với `fastapi`: **4,69 đến 4,94** | Số liệu nền để đối chứng hiệu năng |
| Benchmark 1.3.41, máy rảnh, 5 lần | **4,82 đến 4,99**, ngưỡng test **nhỏ hơn 5,0** | Theo báo cáo, chi phí tăng nhẹ khoảng 0,1 điểm tỷ lệ; dư địa còn rất ít. Đưa vào task tối ưu, không đóng là nhiễu |
| 1.3.41 khi máy bận | Đã có lần **5,19** và **5,42** | Tải máy có thể khuếch đại tình trạng sát ngưỡng; giữ log cả lần đỏ |
| `test_resonance_perf` | Chủ báo lần mới xanh sau lần trước đỏ | Hiện chưa tái hiện lỗi; phù hợp khả năng dao động tải, chưa đủ để chứng minh nguyên nhân chỉ do tải máy |

Nguồn full suite và khoảng đo: master plan mục 3.4/nhật ký ở `6b22a33`. Kết quả `test_resonance_perf` lấy từ thông tin chủ bổ sung ở lượt này. Em chưa chạy lại suite hoặc benchmark và chưa có log từng lần trong phạm vi tài liệu đã đọc. Khoảng min/max không đủ tính chính xác median, độ tăng trung bình hay quy trách nhiệm cho từng module; A07 phải thu log thô và profile import trước khi sửa.

Ưu tiên xử lý hiệu năng bằng đo và nạp lười dependency thật sự không cần khi khởi động. **Giữ trần 5,0 trong gói A**. Nếu về sau có lý do đổi ngưỡng, tách đề xuất với số đo startup tuyệt đối, yêu cầu healthcheck, độ biến động và test chống hồi quy tương đương; không nâng ngưỡng như một cách làm suite xanh.

### 2.4 Quyết định của chủ ngày 28/10/2026

| Mục | Quyết định | Hệ quả khi hiện thực |
|---|---|---|
| Phạm vi | Duyệt **gói A** (A00 đến A07). Gói B chưa duyệt | Không làm B01, B02, B03 |
| D2 | Duyệt như đề xuất: chỉ tự nhân khi đích đúng bằng bản nguồn trước sửa; đích khác từ trước là `override` chờ xem | Làm đủ A02 |
| D4 | Chọn phương án nhẹ: **chỉ chặn khi bộ eval `invalid` hoặc `valid_fail`**. Phòng chưa có eval (`missing`) **không bị chặn bởi D4**. `eval_bat_buoc` giữ mặc định tắt | Khác đề xuất của Astra (mặc định bắt buộc). Không đổi mặc định theo registry |
| D1, D3, D5, D6 | Không có ý kiến riêng, làm theo đề xuất trong plan | D3 vẫn giữ: thay đổi hành vi (thân bài, `role`, `goal`, `task`) chưa tự áp ở gói A |

**Lưu ý tương tác giữa D3 và D4 nhẹ:** vì D3 chặn tự áp mọi thay đổi hành vi ở gói A, phần việc mà `missing` eval "được phép" thực tế chỉ còn các thay đổi hiển thị thuần (`display_only`). Phương án nhẹ vì thế ít tác dụng thực tế hơn mô tả; điểm khác biệt sẽ lộ ra khi gói B mở lại tự áp hành vi theo từng package.

## 3. Ánh xạ đủ 12 tồn đọng

| ID gốc | Task chịu trách nhiệm | Điều kiện đóng |
|---|---|---|
| G1-01 | A01, B01, B02 | A01 đóng đường thử mù; chỉ B01+B02 mới đóng thiếu bằng chứng thực tế |
| G1-02 | A02, A05 | Override có trước/sau snapshot đều được giữ, source apply cũng kiểm phiên bản |
| G1-03 | A06 | Chủ xem và khôi phục được từng đích; promote thủ công vẫn qua gate |
| G1-04 | A05, B03 | Writer dùng chung được khóa; giới hạn với editor/native ngoài cơ chế được công khai và cô lập |
| G1-05 | B03 | Ma trận route có test enforcement tại nơi ghi, không chỉ có reviewer nhận việc |
| G1-06 | A05, A07, B03 | Test hệ điều hành và symlink thực chạy; route chưa đủ bằng chứng giữ chưa chứng nhận |
| G1-07 | A03, B03 | Thay đổi hành vi không tự áp; host không nhận quyền từ body |
| G1-08 | A03 | Parser/ID/metadata xử lý chặt; 30 skill lỗi có báo cáo riêng, không bulk sửa |
| G1-09 | A04 | Quy tắc missing/invalid/fail có test; eval chuỗi không gắn nhãn eval hành vi |
| G1-10 | B01, B02 | Phân loại lỗi, đếm đúng revision, tách chờ duyệt, có ngưỡng và mẫu rõ ràng |
| G1-11 | A00, A06 | Không rewrite commit đã push; task mới tách commit; UI mới có vi/en |
| G1-12 | A07.1, A07.2 | Tối ưu chi phí nạp đã tăng, E2E sandbox, đối chiếu 865/894 với log từng test, benchmark và skip rõ |

Thứ tự thực hiện: **A00 → A01 → A02 → A03 → A04 → A05 → A06 → A07**. A02 mới xử lý logic kế thừa, chưa coi write path an toàn cho đến A05. Sau duyệt B: **B01 → B03 → B02**, rồi chạy canary sandbox; mở pilot production là quyết định riêng có hồ sơ.

## 4. Gói A: khép đường tự áp còn hở

### A00. Chụp baseline và tách kiểm chứng

- [ ] Đọc lại HEAD, working tree, master plan mục 3.3/3.4, spec và quy ước dev. Thu log full suite đã báo 865/894, commit code được test, môi trường và danh sách 29 mục ngoài số xanh; chưa có log thì ghi “kết quả theo báo cáo”, không tự điền chi tiết. So suite với 1.3.38, benchmark với 1.3.39 và code nền 1.3.41 bằng đúng commit tương ứng.
- [ ] Đặt phiên bản theo quy ước trước code, không cố định sẵn `1.3.42` trong plan này. Mỗi task một commit logic; không sửa lịch sử `9184b84` đã push.
- [ ] Dùng bản sao brain có dữ liệu giả và kho state tạm. Kiểm bootstrap để chắc các test không trỏ vào settings/state/brain thật.

**Kiểm:** lưu HEAD, lệnh test, exit code, đường dẫn log và phạm vi bị skip. Các số 195 check trong master plan thuộc snapshot cũ, không tái sử dụng làm kết quả hiện tại.

### A01. Chế độ an toàn cho tự cải tiến và canary cũ

**File chính:** `server/factory.py`, `server/harness_map.py`; hiển thị tại `dashboard/sodo.js`.

- [ ] Thêm gate host trước thao tác ghi trong `_proposal_apply`, áp dụng cả `direct` lẫn `canary`; trường hợp chưa phân loại được cũng chờ review. Không chỉ chặn ở cuối `canary_tick`.
- [ ] Tách quyền tạo proposal, thử sandbox, áp nguồn và nhân đích. Cờ dừng tự deploy không tắt giám định/đọc/trả lời bản đã duyệt.
- [ ] Có migration state có phiên bản, chạy lặp không đổi kết quả. Canary cũ thiếu telemetry/baseline đáng tin chuyển `legacy_review`; lưu nguyên state cũ, nguồn, hash, backup và lý do. Không tự giữ/xóa ứng viên hay tự viết lại file nguồn.
- [ ] Sơ đồ hiện “Chưa đủ dữ liệu để kiểm chứng”, nguồn đang chạy bản nào, đích nào đã đổi. `unknown`, `waiting`, `expired` không hiện xanh. Chưa có dữ liệu khác với không có lỗi.

**Kiểm:** proposal đạt giám định nhưng thiếu telemetry không đổi source/destination; zero-traffic không promote; restart giữ trạng thái; migration hai lần không ghi brain; bản hiện hành vẫn trả lời được. Canary cũ không biến mất sau migration.

### A02. Baseline chung, override và quan hệ kế thừa

**File chính:** `server/factory.py`; có thể tách module deploy nhỏ nếu cần. Không dùng `harness_diff` làm nguồn xác định quan hệ kế thừa.

- [ ] Lưu riêng `source_baseline_hash`, `candidate_hash`, `target_observed_hash`, `package_id`, `deployment_id`, `schema_version`. Hash mới dùng SHA-256 đầy đủ trên bytes chính xác sẽ ghi; chỉ rút ngắn khi hiển thị. Tương thích hash ngắn cũ qua migration, không đoán bản gốc còn thiếu.
- [ ] Với legacy chỉ có tên/path: cùng tên không đủ chứng minh cùng package. So với bản nguồn trước sửa để lập danh sách ứng viên, rồi xác nhận danh sách đích của lần deploy; không tự khai quan hệ kế thừa cho toàn bộ brain.
- [ ] Khi lập kế hoạch, đích khác baseline chung là `override`; đích thiếu là `missing`, không tự tạo. Đích đã bằng candidate là `already`, nhưng không kết luận hệ thống từng ghi hoặc đủ quyền rollback nếu thiếu receipt.
- [ ] Ngay trước ghi: đích vẫn phải bằng snapshot **và** thỏa điều kiện baseline/package. Khác snapshot là `conflict`. Đích override phải có proposal hợp nhất riêng, không có nút “force tất cả”.
- [ ] Cùng quy tắc version check cho source apply: review một hash không được ghi lên source đã đổi sau review.

**Kiểm:** đích đã khác từ trước; sửa sau snapshot; xóa file; đích bằng candidate nhưng không có receipt; cùng slug khác package/brain; source đổi sau duyệt; legacy thiếu baseline; lỗi một đích không ghi sai đích còn lại. Test phải gọi cả đường apply/tick, không chỉ helper.

### A03. Phân loại thay đổi hành vi và sửa điểm mù parser

**File chính:** `server/harness_diff.py`, `server/factory.py`; regression tại `tests/python/test_fix01_diff_quyen.py`.

- [ ] Giữ diff YAML theo cây, bổ sung kết quả phân loại rõ: `display_only`, `behavior_change`, `permission_change`, `invalid`, `unknown`. Giữ adapter tương thích chỗ gọi `diff_quyen` nếu cần.
- [ ] Allowlist hiển thị phải dựa trên nơi runtime sử dụng trường đó. Không mặc định `role`, `goal`, `description`, workflow `task` hay `name` là trung tính nếu chúng được đưa vào prompt hoặc dùng để định danh node.
- [ ] Body agent/skill/workflow/loop và nội quy được nạp vào prompt đều thuộc hành vi; thay đổi cấu trúc/thứ tự workflow cũng cần review. Không dùng ngưỡng số chữ hoặc tìm câu “được phép” để tự áp.
- [ ] YAML có dấu mở nhưng thiếu đóng, duplicate key, node `id` trùng, cấu trúc không hợp lệ, alias chu kỳ/quá sâu phải `invalid` hoặc `unknown`, không trả “không đổi”. Test tên/ID node trùng và đổi thứ tự node có ID.
- [ ] `x-`/`x_` không được bỏ qua một cách mặc định: chỉ metadata được đăng ký và không được runtime dùng mới là display-only. Parser phân loại và parser runtime phải nhất quán.
- [ ] Lập báo cáo 30 skill lỗi để sửa riêng sau duyệt; không đổi YAML hàng loạt, không nới parser để pass.

**Kiểm:** thêm câu cho phép gửi khách vào body phải chờ review; sửa `goal`/`task` thay hành vi cũng vậy. Tái hiện hai ca diagnostic mục 2.1 ở helper, sau đó kiểm đường `_proposal_apply`; nếu parser khác đã chặn thì ghi rõ lớp bảo vệ đó. Giữ test nested budget, hoán đổi tools giữa node, kiểu dữ liệu, alias và khóa lạ.

### A04. Gate eval cho hành vi, không làm gián đoạn phòng đang chạy

**File chính:** `server/factory.py`, `tests/python/test_fix02_eval_loader.py`, `tests/python/test_factory.py`.

- [ ] Chốt D4 trong spec/config và host gate sau duyệt: default true cho brain phòng ban theo registry, không bulk ghi config. Phân biệt `missing`, `invalid`, `valid_pass`, `valid_fail`; không biến lỗi đọc file hoặc lỗi chạy thành missing/pass. Ghi rõ chính sách hiệu lực khi gặp giá trị false legacy và khi loại brain chưa xác định; trường hợp chưa xác định vẫn chặn tự áp hành vi.
- [ ] Eval hợp lệ phải gắn đúng target/package và candidate hash. Kết quả cũ không được dùng để áp draft mới; sửa eval sau review phải chạy lại và duyệt lại nếu làm yếu tiêu chí.
- [ ] Thiếu eval: vẫn sinh nháp và liệt kê bộ kiểm cần bổ sung; không tự áp hành vi. Không cần tạo 44 bộ eval giả để vượt gate.
- [ ] Giữ eval chuỗi làm kiểm tĩnh. Bổ sung hợp đồng evidence hành vi cho luồng sandbox, ghi rõ chưa có thì chưa đạt; model tự đánh giá không phải ground truth duy nhất.

**Kiểm:** ma trận missing/invalid/fail/pass × display/behavior/permission; config cũ false; evaluator ném lỗi; kết quả sai revision; một proposal bị chặn không làm dừng agent phục vụ. Test cũ “eval hỏng vẫn áp” phải được sửa theo hợp đồng đã duyệt, không xóa test.

### A05. Writer chung, nhật ký trước ghi và phục hồi sau crash

**File chính:** `server/factory.py`, `server/file_policy.py`; rà `server/capability_executor.py`, `server/write_path_runtime.py` để tái sử dụng cơ chế phù hợp, không bật toàn bộ runtime khác.

- [ ] Dùng một primitive cho apply source, promote target, rollback và restore. Khóa liên tiến trình theo canonical path; thứ tự lấy nhiều khóa cố định. Không dùng chỉ `threading.Lock` hay file `.lock` tồn tại mà thiếu xử lý crash/owner.
- [ ] Dưới khóa: kiểm lại hash và policy, tạo backup tên duy nhất bằng deployment/target ID với exclusive-create, xác minh backup, lưu intent/receipt `prepared`, ghi file nguyên tử cùng filesystem, đọc kiểm hash rồi ghi `committed`. Không dùng timestamp giây làm tên duy nhất.
- [ ] State/journal cũng cần transaction hoặc khóa liên tiến trình, tránh hai worker ghi đè state của nhau. Backup phải nằm dưới root triển khai đã xác thực, không suy từ `dst.parent.parent` với đường dẫn skill lồng sâu.
- [ ] Restart đối soát `prepared`: current=before thì chưa ghi; current=after và có intent/backup phù hợp thì hoàn tất receipt; khác cả hai là conflict. Không coi mọi file bằng candidate là do mình ghi. Lỗi lưu state sau ghi không được làm mất đường rollback.
- [ ] Không cắt mất canary còn active/conflict/đợi khôi phục khi vượt 50 bản ghi. Retention chỉ dọn terminal records theo chính sách có liên kết backup; không GC backup đang được tham chiếu.
- [ ] Khóa chỉ bảo vệ writer cùng tuân thủ. CLI/editor ngoài cơ chế phải bị giới hạn khỏi vùng managed bằng sandbox/ACL hoặc giữ route chưa chứng nhận. Với file vẫn cho editor ngoài sửa trực tiếp, công bố rủi ro còn lại và không tự promote ở route đó.
- [ ] Với path race: kiểm toàn bộ đường cha, symlink/junction và boundary brain. `O_NOFOLLOW` riêng leaf hay `fstat` sau khi đã ghi không đủ. Dùng cơ chế handle/dir-relative phù hợp OS hoặc vùng ghi không cho đổi link; chưa làm được thì từ chối route đó.

**Kiểm:** hai process cùng sửa một target; hai process cập nhật canary khác nhau; crash trước/sau từng bước ghi; hỏng/mất backup; hai file cùng stem cùng giây; editor sửa trước rollback; nested skill path; path traversal/junction/symlink cha và leaf. Test phải xác minh bytes cuối và receipt, không chỉ trạng thái trả về.

### A06. API và Sơ đồ để chủ quyết định được

**File chính:** route factory trong `server/main.py`, `server/factory.py`, `server/harness_map.py`, `dashboard/sodo.js`, i18n hiện hữu.

- [ ] Mở rộng đọc trạng thái hiện có `/work/factory` một cách tương thích: candidate/source revision, telemetry readiness, lý do chặn, thời hạn, evidence counts, từng đích và khả năng khôi phục. State mới phải được `stages_snapshot` và UI hiểu.
- [ ] Thêm thao tác quản trị pause, xem diff, restore/rollback từng đích, acknowledge và yêu cầu promote. Endpoint cụ thể chốt theo router hiện hữu; POST có auth/chống CSRF theo cơ chế app, kiểm quyền ở server, không chỉ ẩn nút.
- [ ] Request gồm deployment/target ID, expected revision, action ID chống lặp và lý do. Server tự tra đường dẫn, không nhận path tùy ý từ client. Duyệt hết hạn hoặc đổi draft/target/grant thì phải review lại.
- [ ] Promote thủ công là yêu cầu qua cùng gate, không phải bỏ qua thiếu eval, override, quyền hoặc telemetry. Gói A giữ nó disabled nếu gate chưa đạt; UI nói điều kiện còn thiếu. Acknowledge chỉ xác nhận đã đọc, không đánh dấu đạt chất lượng.
- [ ] Restore xác minh receipt, before/after hash và backup trước ghi; conflict thì chỉ đưa diff. Hiển thị partial/error/expired riêng; lỗi gửi thông báo không được làm mất trạng thái hành động.
- [ ] Text mới có vi/en; dùng theme tokens và kiểm hai theme. Đường dẫn nhạy cảm/log nội dung không phơi cho người không có quyền.

**Kiểm:** người không có quyền gọi thẳng API; stale revision; double click; retry sau timeout; tamper target/path; rollback bản đã sửa tay; backup hash sai; nguồn đã superseded; UI trạng thái mới và hai ngôn ngữ. Không cho generic MCP tool tự gọi endpoint quản trị bằng quyền chủ.

### A07. Nghiệm thu gói A và báo cáo trung thực

#### A07.1. Tối ưu nạp server, giữ nguyên trần 5,0

**Phạm vi khảo sát:** `server/main.py` và dependency thực sự nằm trên đường import; `tests/python/test_khoi_dong_nhe.py`. `messenger_ops`, `system_agents`, `harness_*` là danh sách cần đo, không phải kết luận tất cả đều nạp sớm: tại baseline `harness_map` đã được import trong `_harness_snapshot`.

- [ ] Dùng `python -X importtime` trong state tạm để so baseline 1.3.39, 1.3.41 và candidate; lưu self/cumulative time cùng chuỗi dependency. Dùng cùng interpreter/dependencies và ghi rõ cache lạnh/ấm. Đo startup tuyệt đối và lần gọi đầu tiên của tính năng bị hoãn nạp.
- [ ] Chỉ chuyển dependency tùy chọn đã chứng minh tốn chi phí sang nạp tại lúc dùng. Giữ đăng ký route, startup hook và chốt quyền bắt buộc; đặc biệt không chuyển toàn bộ `messenger_ops.register(app)` sang lúc có request làm endpoint biến mất. Không trì hoãn enforcement hoặc nuốt lỗi thiếu dependency thành “được phép”.
- [ ] Test deterministic xác nhận dependency đã chọn không còn nạp sớm, nhưng tính năng vẫn hoạt động khi gọi lần đầu và đồng thời. Kiểm route/auth/hook vẫn tồn tại, import error hiện đúng nguyên nhân và không tạo fail-open. Task này có commit riêng, không trộn với sửa assertion nghiệp vụ của `test_factory`.
- [ ] Mọi subprocess đo phải kiểm exit code/stderr. Import lỗi không được ghi thành “khởi động nhanh”; đọc lại helper hiện tại vì lệnh subprocess chưa bật kiểm lỗi. Ghi phép tính tỷ lệ, chi phí interpreter, fastapi và main, không đổi cách tính âm thầm.

**Kiểm:** giữ `TRAN_TI_LE = 5.0` và điều kiện `< 5.0`. Chạy baseline 1.3.41/candidate xen kẽ tối thiểu 10 lần mỗi bản lúc máy rảnh; lưu từng lần, median/p95 và số lần vượt trần, không chỉ chọn lần xanh. Mục tiêu candidate có median giảm so với 1.3.41 và p95 dưới 5,0 trên môi trường đo đã ghi; đây là gate mẫu đo, không phải bảo đảm mọi máy đều dưới ngưỡng. Nếu chưa đạt hoặc chưa phân biệt được cải thiện với biến động, giữ A07.1 mở và tiếp tục profile; không tăng trần. So thêm 1.3.39 để theo dõi khoảng chi phí đã tăng, không gán toàn bộ phần tăng cho G1 khi chưa có profile.

#### A07.2. E2E, regression và điều kiện phát hành

- [ ] E2E trên brain tạm: proposal → phân loại → eval → chờ duyệt → apply được phép trong sandbox → một đích baseline, một override → crash/restart → restore. Dùng stub engine và dữ liệu giả; không gọi model trả phí hoặc gửi tin thật.
- [ ] Chạy regression FIX-01..05, factory, guard, schema, ranh giới quyền, harness map và test UI liên quan; chạy full suite trong state tạm khi không trùng job đang chạy. Log phải có command, HEAD, OS, thời gian, exit code, fail/skip.
- [ ] Symlink leaf và parent phải thực chạy trên môi trường có quyền; CI Linux và Windows, thêm macOS nếu muốn chứng nhận macOS. Skip là coverage gap, không phải pass. Chưa có máy thì giữ trạng thái nền tảng đó chưa chứng nhận.
- [ ] Đính kèm kết quả A07.1 vào nghiệm thu G1-12; không còn mô tả khởi động sát ngưỡng là “chỉ nhiễu”. `test_resonance_perf` ghi trạng thái mới theo log của candidate; nếu tái đỏ thì lưu điều kiện và điều tra riêng, không tự đổi timeout hay bỏ assertion.
- [ ] `test_icons` và `test_nhat_ky_song_ngu`: kiểm lại tại đúng baseline trước khi gọi là lỗi cũ. Không khai full suite xanh khi còn đỏ; không merge với CI đỏ theo quy ước repo. `test_factory` đổi hợp đồng phải cập nhật assertion và lý do.
- [ ] Cập nhật spec, acceptance, rollout và master plan để cùng trạng thái; liệt kê G1-01/05/06/10 còn cần B thay vì đánh dấu hoàn tất cả G1.

**Gate A đạt:** đường tự áp nguy hiểm đã đóng, override giữ được, restore chạy được, kiểm chứng A đầy đủ. Tên trạng thái phát hành là **“G1 đã gia cố, canary chưa chứng nhận”**, không phải “harness hoàn chỉnh”.

## 5. Gói B: bằng chứng chạy thật và route có chốt bắt buộc

### B01. Một hợp đồng lượt chạy cho chat, workflow và task

**Điểm nối cần khảo sát:** `server/main.py`, `server/engine.py`, các adapter engine, `server/workflow_graph.py`, `server/tasks.py`, `server/task_store.py`, `server/agent_jobs.py`. `server/hub_trace.py` hiện chỉ ghi MCP startup trong RAM, không phải kho lượt chạy nghiệp vụ. Tái dùng `task_runs` và evidence store nơi phù hợp, không ép chat vào Kanban.

- [ ] Host sinh execution context trước model call, chụp cấu hình thực sự nạp và truyền xuống tool, subagent, callback. Agent không tự khai revision hay kết quả verification.
- [ ] Tối thiểu có `run_id`, `logical_execution_id`, `attempt_id`, `parent_run_id`, `brain_id`, `agent_id`, `entrypoint`, `task/chat/workflow_node_ref`, `started_at`, `finished_at`, `engine`, `model`, `status`, `block_kind`, `verification_status`, `evidence_refs`.
- [ ] Revision gồm `agent_revision`, `harness_revision`, `effective_config_hash`, `grant_hash`, `eval_revision` và danh sách dependency revisions của skill/workflow đang được thử. Một skill đổi mà agent.md không đổi vẫn phải nhận đúng ứng viên; không chỉ lưu slug agent.
- [ ] Ghi lifecycle bền vững và event idempotent. Hủy, timeout, mất worker thành canceled/interrupted/unknown, không tự tính pass/fail. Một logical execution retry nhiều lần không thành nhiều bằng chứng độc lập.
- [ ] Lưu metadata tối thiểu, phân quyền theo brain; nội dung nhạy cảm nằm trong evidence store có redaction/retention hiện hữu. Không log toàn bộ prompt, secret hoặc hội thoại khách.

**Kiểm:** agent chạy qua chat không có task; workflow node; task tạo trước deploy nhưng chạy sau; run bắt đầu bản cũ kết thúc sau deploy; retry/restart/duplicate callback; parent-child; skill revision thay; cached session không thực nạp bản mới. Trace phản ánh bản thực dùng, không lấy mtime lúc kết thúc.

### B03. Chứng nhận đường thực thi và ghi dữ liệu

- [ ] Điền ma trận master plan mục 14 theo **engine × entrypoint × operation**, gồm API tool calls, MCP, CLI native write/shell, `joyce_run_command`, plugin, dashboard HTTP, skill/loop và bot khách hàng. Với mỗi route ghi rõ principal, grant nguồn, nơi enforcement và test.
- [ ] Dùng file policy chung nhưng phân biệt boundary/path policy với authorization. `file_policy.deny_reason` trả None ngoài brain không phải cho phép ghi ngoài brain; caller phải kiểm phạm vi trước.
- [ ] Mỗi side effect cần host grant theo operation và tham số. `tools: []` vẫn là không tool; không lấy body, tool description, UI scope hoặc lời agent làm grant. Grant của con là tập con của grant được phép giao, không giao chéo phòng bằng prompt.
- [ ] CLI hoặc shell không chặn được ghi tùy ý thì chạy read-only trong sandbox hoặc tắt trên route pilot đó. Không tuyên bố cùng mức bảo vệ chỉ vì engine cũng nối MCP Hub. Plugin trong process có thể ghi trực tiếp phải là mã tin cậy đã audit hoặc cô lập, không giả định hook kiểm được tất cả.
- [ ] Quyền chủ dùng UI quản trị tách khỏi quyền agent phục vụ khách; callback/kênh bot không kế thừa quyền chủ qua ambient context. Route chưa chứng nhận không được chạy canary có side effect.

**Kiểm:** cùng một yêu cầu ghi cấm thử qua từng route; sửa `sources` có sẵn, vượt brain, link swap, native tool, shell và plugin trực tiếp; tool/grant hỏng phải deny tại nơi thực thi. Bằng chứng riêng cho từng OS; không dùng một test hub thay mọi adapter.

### B02. Canary dựa trên run và chất lượng thực

- [ ] Mỗi canary pin package/revision/dependencies, danh sách đích, bộ eval, grant, engine/model và tập loại việc. Nguồn bằng chứng là B01, route phải qua B03; dữ liệu legacy không rõ revision loại khỏi mẫu và ghi lý do.
- [ ] `done` chỉ nghĩa là kết thúc xử lý. Một mẫu đạt cần completed và verification pass đúng nhiệm vụ/revision; tách lỗi nghiệp vụ, lỗi hệ thống, vi phạm quyền/dữ liệu, chờ duyệt/thiếu input và unknown. Unknown không được coi pass; thiếu event làm readiness giảm.
- [ ] Đề xuất ban đầu: tối thiểu 20 logical executions đủ điều kiện, tối thiểu 24 giờ quan sát, tối đa 14 ngày; trong tập có đủ nhóm ca bắt buộc của phòng. Mốc này là ngưỡng mở thử cần hiệu chỉnh, không phải kết luận chất lượng thống kê. Lưu cả tử số/mẫu số, retry và số bị loại; không giảm ngưỡng âm thầm khi ít traffic.
- [ ] Gate chất lượng ban đầu: toàn bộ ca bắt buộc pass, tối thiểu 20 execution verified-pass và không có lỗi nghiệp vụ đã xác minh còn chưa xử lý trong cửa sổ. Execution verified-fail vẫn nằm trong mẫu báo cáo, không loại đi để lấy đủ 20 pass. So baseline và candidate trên cùng bộ ca; regression mới chặn promote. Nếu sửa candidate thì mở cửa sổ cho revision mới, không cộng dồn bằng chứng bản cũ.
- [ ] Hard stop khi có vi phạm quyền, rò dữ liệu hoặc sai nghiệp vụ nghiêm trọng được xác minh gắn đúng run: ngừng nhận run mới của candidate, chặn promote và thực hiện rollback theo receipt khi an toàn. Phân biệt hành động cấm bị guard chặn với hành động cấm đã xảy ra; cả hai đều cần review trước promote nhưng mức sự cố khác nhau.
- [ ] `needs_approval`/`needs_input` không là lỗi agent; vẫn báo thời gian chờ và tỷ lệ bỏ dở, không dùng cách loại mẫu để giấu vấn đề. Dùng cùng một snapshot evidence cho quyết định dừng/promote để tránh số liệu lệch giữa hai lần đọc.
- [ ] Bản nguồn không chứng nhận mọi phòng. Từng đích phải qua eval phòng trước deploy; rollout tuần tự/canary theo đợt nhỏ và theo dõi run tại đích sau deploy. Phòng không có eval hoặc telemetry không nhận bản mới.
- [ ] Hết hạn không tự promote. Sandbox rollback an toàn theo receipt; production cần chính sách giữ/lùi đã duyệt trước khi bắt đầu, báo trạng thái nguồn thực tế. Giữ kill switch và cơ chế dừng route trong trường hợp không thể rollback do conflict.

**Kiểm:** zero traffic; nhiều trace nhưng sai revision; 20 lần trả lời chưa verified; retry làm phình mẫu; chạy từ workflow/skill; failure ở đích; chờ duyệt; collector outage; lỗi nghiêm trọng trước đủ 20; hết hạn; pause; restart; rollback conflict. Thiếu coverage loại việc phải chặn dù đủ số lượng.

**Gate B đạt:** một luồng từ chat qua agent và tool, có eval/receipt, dùng đúng revision, phát hiện lỗi và dừng/lùi thành công trong sandbox. Chỉ sau đó trình hồ sơ pilot Đối Soát ở chế độ đọc. Pilot có ghi tiền hoặc gửi khách cần grant và xác nhận nghiệp vụ theo master plan; B không thay các gate ngân sách/compiler còn lại.

## 6. Gợi ý kiểm tra và hồ sơ bàn giao

Các lệnh dưới dùng runner của repo, trong môi trường đã cô lập state theo A00. Sonnet đọc `tests/run.py` trước để xác nhận cách chọn suite; không chạy vào brain thật.

```powershell
.venv\Scripts\python.exe -B tests/run.py fix01_diff_quyen
.venv\Scripts\python.exe -B tests/run.py fix02_eval_loader
.venv\Scripts\python.exe -B tests/run.py fix03_file_guard
.venv\Scripts\python.exe -B tests/run.py fix04_fix05_canary
.venv\Scripts\python.exe -B tests/run.py factory
.venv\Scripts\python.exe -B tests/run.py harness_map
.venv\Scripts\python.exe -B tests/run.py khoi_dong_nhe
git diff --check
```

Test mới đặt theo ticket và dùng runner hiện hữu. Không coi danh sách lệnh này là full suite; ghi thêm lệnh UI, full suite và CI thật trong báo cáo. Diagnostic audit ở lượt lập plan chỉ gọi `diff_quyen` với chuỗi trong RAM, không sửa code hoặc chạy lại full suite.

Hồ sơ mỗi task gồm: commit; lỗi trước sửa và hành vi sau sửa; tests/exit codes; giới hạn chưa kiểm; migration và rollback. Hồ sơ cả gói thêm ma trận 12 ID, ảnh Sơ đồ hai theme, trạng thái canary nguồn/đích, cấu hình cần bật sau duyệt và điều kiện chưa cho rollout.

## 7. Prompt giao Sonnet 5.5 sau khi anh duyệt

```text
Đọc docs/dev/2026-10-28-joyce-harness-g1-g2-sonnet-plan.md và master plan Joyce Harness.
Đối chiếu HEAD hiện tại với baseline code 8a981e6 và cập nhật tài liệu 6b22a33;
giữ mọi thay đổi của phiên khác. Full suite 1.3.41 được báo 865/894 xanh,
chưa phải tất cả pass; thu log chi tiết và tách baseline suite/benchmark.
Chỉ thực hiện gói đã được chủ duyệt. Mặc định đề xuất là gói A (A00..A07);
đoạn prompt này tự nó không thay thế phê duyệt của chủ.

Chốt các quyết định D1..D6 trong spec trước code. Làm task theo thứ tự phụ thuộc,
mỗi task có regression test và commit logic riêng, dùng state/brain tạm.
Không dùng số test pass cũ làm bằng chứng mới; không đổi threshold để test xanh.
Làm A07.1 thành commit tối ưu riêng: profile trước, nạp lười dependency tùy chọn,
giữ route/auth/hook, kiểm import thành công và giữ trần 5,0.
Không coi compare+os.replace là CAS với editor ngoài cơ chế; không bỏ gate vì UI ẩn nút.
Không tự sửa quyền, agent, skill, settings hoặc canary production đang tồn.
Không sửa 30 skill hàng loạt, không điền agent key giả vào Kanban để đủ 20 mẫu.

Nếu phải thay hướng, sửa plan và nêu ảnh hưởng trước khi code phần lệch phạm vi.
Kết thúc bằng báo cáo đối chiếu 12 G1 IDs, tests thực chạy, những gì bị skip,
khả năng rollback và gate còn mở. A xong phải ghi “G1 đã gia cố, canary chưa chứng nhận”.
B chỉ triển khai sau khi được giao; production rollout theo hồ sơ duyệt riêng.
```

## 8. Nhật ký tài liệu

| Ngày | Kết quả |
|---|---|
| 2026-10-28 | Đọc G1 tại 1.3.41/8a981e6, đối chiếu apply/evidence/promote/parser/file policy/UI và task store; diagnostic helper trong RAM xác nhận ba ca trả diff rỗng. Viết plan A/B, chưa sửa runtime, chưa xác nhận full suite |
| 2026-10-28 | A00 (Sonnet): đặt chỗ phiên bản 1.3.42; lưu log full suite thô và `README.md` bằng chứng nền ở `docs/dev/evidence/2026-10-28-g1/`; thêm `test_a00_cach_ly_state.py`; ghi quyết định của chủ ở mục 2.4 (gói A, D4 nhẹ) |
| 2026-10-28 | Cập nhật theo 6b22a33 và thông tin chủ bổ sung: full suite 865/894; benchmark 1.3.39 4,69..4,94, 1.3.41 4,82..4,99; resonance_perf được báo xanh lại. Tách A07.1 tối ưu startup và A07.2 nghiệm thu, giữ ngưỡng 5,0; làm rõ đề xuất D2/D4 vẫn chờ duyệt. Chỉ sửa plan, không chạy lại suite, sửa code hay bật config |
