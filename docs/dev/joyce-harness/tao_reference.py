"""Sinh docs/dev/joyce-harness/reference.json và kiểm bằng contract.schema.json.

    python docs/dev/joyce-harness/tao_reference.py        (ghi đè reference.json cạnh file này)

Chạy lại được: cùng đầu vào ra cùng file. Ví dụ đúng phải qua schema, ví dụ sai phải bị từ chối.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
SCHEMA = json.loads((D / "contract.schema.json").read_text(encoding="utf-8"))


def h(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


TS = "2026-10-28T09:00:00+07:00"
PLATFORM = {"kind": "platform", "id": "joyce.platform", "version": "1.0.0", "hash": h("platform-1.0.0")}
ORG = {"kind": "organization", "id": "h2o.org", "version": "1.0.0", "hash": h("h2o-org-1.0.0")}
DEPT = {"kind": "department", "id": "h2o.ke-toan-thu", "version": "1.0.0", "hash": h("dept-thu-1.0.0")}
CONTRACTS = {"task": {"id": "joyce.task", "version": "1.0.0"}, "result": {"id": "joyce.result", "version": "1.0.0"}}
FEATURES = ["v1.manifest-compiler", "v1.operation-gate", "v1.no-tools-explicit", "v1.budget-tree", "v1.host-verdict"]
BRAIN_SYS = "fixture.system"
BRAIN_THU = "fixture.ke-toan-thu"


def role_layer(role):
    return {"kind": "role_profile", "id": f"joyce.role.{role}", "version": "1.0.0", "hash": h(f"role-{role}-1.0.0")}


def budget(rounds, deadline, kids, depth, calls, tokens):
    return {"max_rounds_per_run": rounds, "deadline_s": deadline, "max_concurrent_children": kids,
            "max_delegate_depth": depth, "max_model_calls": calls, "max_tokens": tokens}


def manifest(slug, name, role, brain, layers, scope, grants, effects, delegation, deny, b, skills, checks):
    return {"kind": "manifest", "spec_version": "1.0.0", "harness_version": "1.0.0",
            "package_revision": h(f"pkg-{brain}-{slug}-1.0.0"),
            "agent": {"brain_id": brain, "slug": slug, "name": name},
            "role": role, "layers": layers, "scope": scope,
            "execution": {"grants": grants, "allowed_effects": effects},
            "delegation": delegation, "deny": deny, "budget": b, "skills": skills,
            "verification": {"required_checks": checks}, "contracts": CONTRACTS,
            "required_features": FEATURES}


G_SHOP_XEM = {"tool": "joyce_shop", "operation": "xem", "effects": ["read"]}
G_SHOP_GIA = {"tool": "joyce_shop", "operation": "gia", "effects": ["read"]}
G_SHOP_GHI_THU = {"tool": "joyce_shop", "operation": "ghi.thu", "effects": ["business_write"], "argument_policy": "h2o.thu-co-hop-dong"}
G_READ = {"tool": "joyce_read_file", "operation": "read", "effects": ["read"]}
G_TASK = {"tool": "joyce_task", "operation": "enqueue", "effects": ["internal_write"]}
DENY_SEND = {"tool": "zalo_send_message", "operation": "*", "reason": "Phòng Thu không nhắn khách"}

executor = manifest(
    "thu-ghi-so", "Chuyên viên ghi thu", "executor", BRAIN_THU,
    [PLATFORM, role_layer("executor"), ORG, DEPT],
    {"brains": [BRAIN_THU], "read": ["shop_so:hop_dong", "shop_so:quy", "shop_so:dich_vu"], "write": ["shop_so:quy"]},
    [G_SHOP_XEM, G_SHOP_GHI_THU], ["read", "business_write"], [], [DENY_SEND],
    budget(8, 600, 0, 0, 12, 50000), [{"id": "h2o-studio-ketoan-thu-cong-no", "version": "1.0.0"}],
    [{"id": "check.kiem-so", "version": "1.0.0"}])

explorer = manifest(
    "thu-tra-cuu", "Tra cứu sổ thu", "explorer", BRAIN_THU,
    [PLATFORM, role_layer("explorer"), ORG, DEPT],
    {"brains": [BRAIN_THU], "read": ["shop_so:hop_dong", "shop_so:quy", "shop_so:dich_vu", "wiki"], "write": []},
    [G_SHOP_XEM, G_SHOP_GIA, G_READ], ["read"], [], [],
    budget(6, 300, 0, 0, 8, 30000), [], [])

verifier = manifest(
    "thu-kiem-chung", "Kiểm chứng phiếu thu", "verifier", BRAIN_THU,
    [PLATFORM, role_layer("verifier"), ORG, DEPT],
    {"brains": [BRAIN_THU], "read": ["shop_so:quy", "shop_so:hop_dong"], "write": []},
    [G_SHOP_XEM], ["read"], [], [],
    budget(4, 300, 0, 0, 6, 20000), [], [])

no_tools = manifest(
    "soan-loi-nhan", "Soạn lời nhắn nháp", "executor", BRAIN_THU,
    [PLATFORM, role_layer("executor"), ORG, DEPT],
    {"brains": [BRAIN_THU], "read": [], "write": []},
    [], [], [], [], budget(4, 300, 0, 0, 4, 10000), [], [])

dept_manager = manifest(
    "truong-phong-thu", "Agent Trưởng Phòng Thu", "department_manager", BRAIN_THU,
    [PLATFORM, role_layer("department_manager"), ORG, DEPT],
    {"brains": [BRAIN_THU], "read": ["shop_so:hop_dong", "shop_so:quy", "wiki"], "write": ["kanban"]},
    [G_SHOP_XEM, G_TASK], ["read", "internal_write"],
    [{"target": {"brain_id": BRAIN_THU, "slug": "thu-ghi-so"}, "target_revision": executor["package_revision"],
      "grants": [G_SHOP_XEM, G_SHOP_GHI_THU], "allowed_effects": ["read", "business_write"]},
     {"target": {"brain_id": BRAIN_THU, "slug": "thu-tra-cuu"}, "target_revision": explorer["package_revision"],
      "grants": [G_SHOP_XEM, G_SHOP_GIA, G_READ], "allowed_effects": ["read"]}],
    [DENY_SEND], budget(12, 900, 2, 1, 24, 100000), [], [])

manager = manifest(
    "joyce-manager", "Joyce Manager", "manager", BRAIN_SYS,
    [PLATFORM, role_layer("manager"), ORG],
    {"brains": [BRAIN_SYS, BRAIN_THU], "read": ["shop_so:*", "crm:*", "kanban"], "write": ["kanban"]},
    [G_SHOP_XEM, G_TASK], ["read", "internal_write"],
    [{"target": {"brain_id": BRAIN_THU, "slug": "truong-phong-thu"}, "target_revision": dept_manager["package_revision"],
      "grants": [G_SHOP_XEM, G_SHOP_GHI_THU, G_TASK], "allowed_effects": ["read", "business_write", "internal_write"]}],
    [], budget(12, 900, 2, 2, 24, 100000), [], [])

task = {
    "kind": "task", "task_id": "task.20261028.0001", "task_version": 1, "run_id": "run.20261028.0001.a",
    "trace_id": "trace.20261028.0001", "route": "task", "state": "running", "owner": "owner.chu-studio",
    "assignee": {"brain_id": BRAIN_THU, "slug": "thu-ghi-so", "package_revision": executor["package_revision"]},
    "objective": "Ghi khoản thu cọc 1.500.000 đồng của khách Tuấn Thủy (0899252392) vào hợp đồng HD0001.",
    "inputs": [
        {"name": "hop-dong", "source": "shop_so:hop_dong/HD0001", "revision": "r12", "summary": "Gói chụp ảnh studio 15.000.000 đồng, đang báo giá"},
        {"name": "so-tien", "source": "chat:web/turn-42", "as_of": TS, "value": 1500000}],
    "grant_ref": "grant.20261028.0001",
    "budget": budget(8, 600, 0, 0, 12, 50000),
    "criteria": [
        {"id": "c1", "description": "Có đúng một phiếu thu 1.500.000 đồng gắn HD0001", "check_id": "check.kiem-so", "required": True},
        {"id": "c2", "description": "Tổng thu của HD0001 không vượt giá trị hợp đồng", "check_id": "check.kiem-so", "required": True}],
    "verification": {"mode": "deterministic", "max_repair_retries": 1},
    "reporting": {"channel": "web", "recipient": "web:sess-8f2c"}}

receipt = {
    "kind": "receipt", "action_id": "act.ghi-thu.1", "idempotency_key": h("task.20261028.0001|1|act.ghi-thu.1|shop_so:quy:HD0001"),
    "task_id": task["task_id"], "task_version": 1, "operation": {"tool": "joyce_shop", "operation": "ghi.thu"},
    "effects": ["business_write"], "args_hash": h("redacted-args"), "before_revision": "quy:r40",
    "after_revision": "quy:r41", "remote_id": "quy:118", "status": "confirmed", "recorded_at": TS}

verdict = {
    "kind": "verdict", "check_id": "check.kiem-so", "criterion_id": "c1", "subject_version": "quy:r41",
    "subject_hash": h("quy-r41"), "verdict": "pass",
    "evidence": ["shop_so:quy/118 so_tien=1500000 hop_dong=HD0001", "tong_thu(HD0001)=1500000 <= 15000000"],
    "evaluated_by": {"type": "script", "id": "check.kiem-so", "version": "1.0.0"}, "evaluated_at": TS}
verdict2 = dict(verdict, criterion_id="c2")

result = {
    "kind": "result", "task_id": task["task_id"], "task_version": 1, "run_id": task["run_id"], "status": "completed",
    "artifacts": [{"uri": "shop_so:quy/118", "hash": h("quy-r41"), "revision": "quy:r41"}],
    "verdicts": [verdict, verdict2], "receipts": [receipt],
    "summary": "Đã ghi thu cọc 1.500.000 đồng vào HD0001; hợp đồng chuyển Đã ký. Kiểm số đạt cả hai tiêu chí.",
    "recorded_by": "host"}

result_blocked = {
    "kind": "result", "task_id": "task.20261028.0002", "task_version": 1, "run_id": "run.20261028.0002.a",
    "status": "blocked", "artifacts": [], "verdicts": [], "receipts": [],
    "summary": "Chưa ghi được thu vì không tìm thấy hợp đồng của số điện thoại đã cho.",
    "blocker": "Không có hợp đồng của 0911000999", "wake_condition": "Sales tạo hợp đồng cho khách này",
    "recorded_by": "host"}


def bad(name, why, base, mutate):
    doc = copy.deepcopy(base)
    mutate(doc)
    return {"name": name, "why": why, "doc": doc}


invalid = [
    bad("executor-giao-viec", "Executor không được có delegation (mục 3, 6.3).", executor,
        lambda d: d["delegation"].append(copy.deepcopy(dept_manager["delegation"][1]))),
    bad("explorer-ghi-so", "Explorer chỉ được effect read (mục 3).", explorer,
        lambda d: d["execution"]["allowed_effects"].append("business_write")),
    bad("giao-theo-lop", "Không resolve 'class:executor' lúc chạy; phải bind slug cụ thể (JH-003).", dept_manager,
        lambda d: d["delegation"][0]["target"].__setitem__("slug", "class:executor")),
    bad("skill-latest", "Không dùng 'latest' trong production (mục 5.1).", executor,
        lambda d: d["skills"][0].__setitem__("version", "latest")),
    bad("operation-rong", "Tool đa năng phải nêu operation, rỗng bị từ chối (mục 6.2).", executor,
        lambda d: d["execution"]["grants"][0].__setitem__("operation", "")),
    bad("effect-la", "Effect ngoài danh sách bị từ chối, không có 'none' hay 'admin'.", executor,
        lambda d: d["execution"]["allowed_effects"].append("admin")),
    bad("khoa-sai-chinh-ta", "Khóa lạ bị từ chối, không âm thầm bỏ (mục 5.1).", executor,
        lambda d: d.__setitem__("delegates", [])),
    bad("doc-lap-thieu-verifier", "Kiểm độc lập phải nêu verifier (mục 7.1).", task,
        lambda d: d["verification"].__setitem__("mode", "independent")),
    bad("completed-chua-pass", "Completed khi có verdict inconclusive (mục 7.2, 8).", result,
        lambda d: d["verdicts"][1].__setitem__("verdict", "inconclusive")),
    bad("completed-tac-dong-chua-ro", "Completed khi còn receipt status unknown (mục 7.2, 9).", result,
        lambda d: d["receipts"][0].__setitem__("status", "unknown")),
    bad("completed-khong-verdict", "Completed mà không có verdict nào (mục 8).", result,
        lambda d: d.__setitem__("verdicts", [])),
    bad("agent-tu-ghi-result", "Result record cuối do host ghi (mục 7.2).", result,
        lambda d: d.__setitem__("recorded_by", "agent")),
    bad("blocked-thieu-dieu-kien-danh-thuc", "Blocked phải ghi điều kiện đánh thức (mục 4.2).", result_blocked,
        lambda d: d.pop("wake_condition")),
    bad("receipt-trang-thai-la", "Receipt chỉ có confirmed, failed, unknown (mục 9).", receipt,
        lambda d: d.__setitem__("status", "done")),
    bad("verdict-boolean", "Verdict là pass, fail, inconclusive; không dùng boolean (mục 7.2).", verdict,
        lambda d: d.__setitem__("verdict", True)),
]

ref = {
    "spec_version": "1.0.0",
    "note": "Fixture tổng hợp cho Joyce Harness Standard v1.0.0. Không phải cấu hình đang chạy. Brain ID, slug, tool là ví dụ; khi áp vào H2O phải bind ID thật từ registry (mục 16). Sinh bằng script, mọi mục 'valid' qua schema, mọi mục 'invalid' bị schema từ chối.",
    "valid": {
        "manifests": {"joyce-manager": manager, "truong-phong-thu": dept_manager, "thu-ghi-so": executor,
                      "thu-tra-cuu": explorer, "thu-kiem-chung": verifier, "soan-loi-nhan-khong-tool": no_tools},
        "tasks": {"ghi-thu-coc": task},
        "receipts": {"ghi-thu-coc": receipt},
        "verdicts": {"kiem-so-c1": verdict, "kiem-so-c2": verdict2},
        "results": {"ghi-thu-coc-completed": result, "ghi-thu-blocked": result_blocked}},
    "invalid": invalid}

validator = jsonschema.Draft202012Validator(SCHEMA)
errs = []
for group, items in ref["valid"].items():
    for k, doc in items.items():
        e = list(validator.iter_errors(doc))
        if e:
            errs.append(f"VALID {group}/{k} bị từ chối: {e[0].message[:200]}")
for b in invalid:
    if validator.is_valid(b["doc"]):
        errs.append(f"INVALID {b['name']} lại qua schema")
if errs:
    print("\n".join(errs))
    sys.exit(1)
(D / "reference.json").write_text(json.dumps(ref, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
n_valid = sum(len(v) for v in ref["valid"].values())
print(f"OK: {n_valid} ví dụ đúng qua schema, {len(invalid)} ví dụ sai bị từ chối")
