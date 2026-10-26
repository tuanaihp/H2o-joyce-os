"""Việc mẫu theo phòng (server/viec_mau.py). Chạy tay / CI:

    python tests/run.py viec_mau          (KHÔNG mạng, KHÔNG đụng brains/ thật)

Thiết kế: docs/dev/2026-10-chat-cong-viec-hang-ngay.md. Dựng brain giả trong thư mục tạm. Phủ:
- bộ mẫu đi kèm app: nạp được, brain con rơi về bộ của brain cha, chữ có dấu không hỏng;
- thêm / sửa / xoá: chặn trùng tên, giới hạn ô nhập, việc seed xoá thành file ẩn rồi hiện lại;
- nút "Đã xong": việc nằm thẳng ở cột Xong, KHÔNG bao giờ vào hàng chờ (bẫy chạy lại tốn quota);
  bấm đúp không nhân đôi; hồ sơ nằm ở sources/viec-lam/;
- chưng cất: đủ 3 hồ sơ mới thì tự xếp đúng MỘT việc, nút "Ghi nhớ" chạy ngay khi mới có 1 hồ sơ.
"""
from _paths import ROOT, SERVER, moi_duong_dan  # noqa: E402,F401
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("JOYCE_STATE_DIR", tempfile.mkdtemp(prefix="joyce-vm-"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from fastapi import FastAPI          # noqa: E402
from tasks import TasksDeps, TasksFeature   # noqa: E402
import viec_mau as vm                # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


TMP = Path(tempfile.mkdtemp(prefix="joyce-vm-brains-"))
SALES = TMP / "Ban Hang - Sales Makeup"      # brain con, không có bộ riêng -> bộ của "Ban Hang"
THUY = TMP / "Ca Nhan - Thuy"
TRONG = TMP / "Brain Khong Co Bo Mau"
for d in (SALES, THUY, TRONG):
    d.mkdir(parents=True)


def _atomic(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


async def _workflow(*_a, **_k):
    if False:
        yield {}


feat = TasksFeature(TasksDeps(
    brain_root=lambda v: str(v),
    atomic_write_text=_atomic,
    execute_workflow=_workflow,
    workflows_dir=lambda b: Path(b) / "workflows",
    build_system_prompt=lambda b: "system",
    aux_model=lambda: None,
    safe_tools=["Read"],
    state_dir=TMP / "state",
    scheduler_brains=lambda: [str(SALES), str(THUY)],
))


class TasksGia:
    """Dùng hàng đợi thật, chỉ thay bước tạo worker (cần engine thật)."""
    def __init__(self):
        self.spawned = []

    def ghi_viec_xong(self, *a, **k):
        return feat.ghi_viec_xong(*a, **k)

    def enqueue(self, *a, **k):
        return feat.enqueue(*a, **k)

    async def _claim_and_spawn(self, tid):
        self.spawned.append(tid)
        return True


gia = TasksGia()
vm._deps.update(brain_root=lambda b: str(b), tasks=lambda: gia)


def req(ten="Lan"):
    return SimpleNamespace(state=SimpleNamespace(staff={"ten": ten} if ten else None))


def chay(coro):
    return asyncio.run(coro)


# ---- 1. Bộ mẫu đi kèm app ----
sales = vm.liet_ke(str(SALES))
check(f"brain con 'Ban Hang - Sales Makeup' dùng bộ của 'Ban Hang' ({len(sales)} việc)", len(sales) >= 5)
check("mọi việc seed có nhóm, tên và lệnh", all(i["group"] and i["title"] and i["prompt"] for i in sales))
check("việc seed mang by=seed", all(i["by"] == "seed" and i["origin"] == "seed" for i in sales))
check("chữ có dấu không hỏng", any(i["title"] == "Tư vấn báo giá online" for i in sales))
check("brain không có bộ mẫu thì trả rỗng, không lỗi", vm.liet_ke(str(TRONG)) == [])
thuy = vm.liet_ke(str(THUY))
check("brain cá nhân Thủy có việc khoá học, content, banner, họp",
      {"Khoá học", "Content", "Banner", "Họp và giải pháp"} <= set(vm.nhom(thuy)))
tuan = vm.liet_ke(str(TMP / "Ca Nhan - Tuan"))
check("brain cá nhân Tuấn có ý tưởng kinh doanh và họp", {"Ý tưởng kinh doanh", "Họp và giải pháp"} <= set(vm.nhom(tuan)))

# Mọi file seed trong repo phải hợp lệ: slug, ô nhập đủ, không gạch dài, route đúng.
loi = []
for d in sorted(vm.SEED_DIR.iterdir()):
    for i in vm._doc_thu_muc(d, "seed"):
        f = d / f"{i['slug']}.md"
        raw = f.read_text(encoding="utf-8")
        meta, body = vm.tach(raw)
        if "—" in raw:
            loi.append(f"{d.name}/{i['slug']}: gạch dài")
        if len(i["inputs"]) != len(vm.chuan_o(meta.get("inputs"))):
            loi.append(f"{d.name}/{i['slug']}: ô nhập hỏng")
        for k in [o["key"] for o in i["inputs"]]:
            if "{" + k + "}" not in body:
                loi.append(f"{d.name}/{i['slug']}: lệnh không dùng ô {k}")
        for ph in __import__("re").findall(r"\{(\w+)\}", body):
            if ph not in [o["key"] for o in i["inputs"]]:
                loi.append(f"{d.name}/{i['slug']}: lệnh dùng {{{ph}}} mà không có ô nhập")
        if i["route"] != "auto" or not i["group"]:
            loi.append(f"{d.name}/{i['slug']}: route/nhóm")
check("toàn bộ file seed hợp lệ" + (": " + "; ".join(loi[:5]) if loi else ""), not loi)

# ---- 2. Thêm / sửa / xoá ----
moi = vm.luu(str(SALES), {"title": "Gửi hợp đồng cho khách", "group": "Sau chốt", "prompt": "Soạn mail hợp đồng cho {khach}",
                           "inputs": json.dumps([{"key": "khach", "label": "Tên khách", "required": True}])}, "Lan")
check("thêm việc mới: slug tự đặt, by là người thêm", moi["slug"] == "gui-hop-dong-cho-khach" and moi["by"] == "Lan")
check("file ghi ở <brain>/viec-mau/", (SALES / "viec-mau" / "gui-hop-dong-cho-khach.md").is_file())
check("việc mới hiện trong danh sách cùng nhóm tự tạo", "Sau chốt" in vm.nhom(vm.liet_ke(str(SALES))))
try:
    vm.luu(str(SALES), {"title": "gui hop dong cho khach", "prompt": "x"}, "Lan")
    check("chặn trùng tên (không phân biệt dấu)", False)
except ValueError as e:
    check("chặn trùng tên (không phân biệt dấu)", "Đã có" in str(e))
try:
    vm.luu(str(SALES), {"title": "Không có lệnh", "prompt": ""}, "Lan")
    check("chặn việc thiếu nội dung lệnh", False)
except ValueError:
    check("chặn việc thiếu nội dung lệnh", True)
nhieu = [{"key": f"o{i}", "label": f"Ô {i}"} for i in range(9)] + [{"key": "O Xau", "label": "x"}, {"key": "o1", "label": "trùng"}]
check(f"ô nhập tối đa {vm.TOI_DA_O}, bỏ khoá sai và khoá trùng", len(vm.chuan_o(nhieu)) == vm.TOI_DA_O)
check("ô chọn không có lựa chọn thì đổi thành ô chữ", vm.chuan_o([{"key": "a", "type": "select"}])[0]["type"] == "text")
sua = vm.luu(str(SALES), {"slug": "gui-hop-dong-cho-khach", "title": "Gửi hợp đồng cho khách", "prompt": "Bản sửa {khach}"}, "Hoa")
check("sửa việc của brain giữ nguyên người thêm ban đầu", sua["by"] == "Lan" and sua["prompt"] == "Bản sửa {khach}")

truoc = len(vm.liet_ke(str(SALES)))
check("xoá việc của brain: biến mất và file bị xoá",
      vm.xoa(str(SALES), "gui-hop-dong-cho-khach") and not (SALES / "viec-mau" / "gui-hop-dong-cho-khach.md").exists()
      and len(vm.liet_ke(str(SALES))) == truoc - 1)
check("xoá việc không tồn tại trả False", vm.xoa(str(SALES), "khong-co-viec-nay") is False)
seed_slug = "tu-van-bao-gia-online"
seed_file = vm.SEED_DIR / "Ban Hang" / f"{seed_slug}.md"
seed_truoc = seed_file.read_bytes()
check("xoá việc seed: ẩn đi", vm.xoa(str(SALES), seed_slug) and seed_slug not in [i["slug"] for i in vm.liet_ke(str(SALES))])
check("xoá việc seed KHÔNG đụng file của app", seed_file.read_bytes() == seed_truoc)
check("việc seed đã ẩn vẫn nằm trong danh sách đầy đủ để hiện lại",
      seed_slug in [i["slug"] for i in vm.liet_ke(str(SALES), kem_an=True)])
vm.luu(str(SALES), {"slug": seed_slug, "title": "Tư vấn báo giá online", "prompt": "Bản của phòng {khach}", "hidden": "0",
                    "inputs": json.dumps([{"key": "khach", "label": "Tên khách", "required": True}, {"key": "nhu_cau", "label": "Nhu cầu của khách", "type": "longtext"}])}, "Lan")
hien = [i for i in vm.liet_ke(str(SALES)) if i["slug"] == seed_slug]
check("sửa lại việc seed: hiện lại và đè bản seed", len(hien) == 1 and hien[0]["prompt"].startswith("Bản của phòng"))
try:
    vm.xoa(str(SALES), "../../etc/passwd")
    check("slug có .. bị chặn", False)
except ValueError:
    check("slug có .. bị chặn", True)

# ---- 3. "Đã xong": cột Xong, không xếp hàng chờ ----
vals = json.dumps({"khach": "Chị Mai", "dich_vu": "Makeup", "nhu_cau": "cưới tháng 12"})
r1 = chay(vm.viec_mau_xong(req(), brain=str(SALES), slug="tu-van-bao-gia-online", title="Tư vấn báo giá online",
                           values=vals, result="Đã gửi báo giá gói A cho chị Mai.", edited="1", chat_id="web:s1", key="abcdef123456"))
check("Đã xong trả ok", r1.get("ok") is True and r1.get("id"))
root = str(Path(str(SALES)).resolve())
tasks = feat.store.list_tasks(root, include_archived=True)
mine = [t for t in tasks if t["id"] == r1["id"]]
check("việc nằm thẳng ở cột done", len(mine) == 1 and mine[0]["status"] == "done")
check("tiêu đề có tên việc và giá trị chính", mine and mine[0]["title"].startswith("Tư vấn báo giá online: Chị Mai"))
check("kết quả được lưu để xem lại", mine and "báo giá gói A" in mine[0]["result"])
check("bộ điều phối KHÔNG nhặt lại việc đã xong", feat.store.next_candidate(root) is None)
check("việc ghi dưới tên người làm", mine and mine[0]["created_by"] == "Lan")
r2 = chay(vm.viec_mau_xong(req(), brain=str(SALES), slug="tu-van-bao-gia-online", title="Tư vấn báo giá online",
                           values=vals, result="Đã gửi báo giá gói A cho chị Mai.", edited="1", chat_id="web:s1", key="abcdef123456"))
check("bấm đúp (cùng key): không nhân đôi việc", r2["id"] == r1["id"] and r2["duplicate"] is True
      and len([t for t in feat.store.list_tasks(root, include_archived=True) if t["status"] == "done"]) == 1)
hoso = vm.ds_ho_so(str(SALES), "tu-van-bao-gia-online")
check("bấm đúp không sinh thêm hồ sơ", len(hoso) == 1)
txt = hoso[0][0].read_text(encoding="utf-8")
check("hồ sơ có người làm, đầu vào và kết quả", "by: \"Lan\"" in txt and "Tên khách: Chị Mai" in txt and "báo giá gói A" in txt)
check("hồ sơ ghi dấu người làm có sửa kết quả", "edited: true" in txt)
check("chưa đủ 3 hồ sơ thì chưa chưng cất", "chung_cat" not in r1 and not gia.spawned)

# ---- 4. Chưng cất ----
for i, k in enumerate(("k2aaaaaa", "k3bbbbbb")):
    r = chay(vm.viec_mau_xong(req("Hoa"), brain=str(SALES), slug="tu-van-bao-gia-online", title="Tư vấn báo giá online",
                              values=json.dumps({"khach": f"Khách {i}"}), result=f"Kết quả {i}", edited="", chat_id="", key=k))
check("hồ sơ thứ 3 tự xếp ĐÚNG MỘT việc chưng cất", r.get("chung_cat", {}).get("ok") and len(gia.spawned) == 1)
cc = feat.store.get_task(r["chung_cat"]["id"])
check("việc chưng cất có tiền tố và trỏ đúng trang wiki", cc["title"].startswith("[Chưng cất]")
      and "wiki/quy-trinh/viec-mau/tu-van-bao-gia-online.md" in cc["intent"] and "ingest-source" in cc["intent"])
check("việc chưng cất dùng engine phụ, quyền vừa đủ", cc["capability"] == "mcp-read" and cc["execution_mode"] == "auto")
check("sau chưng cất, hồ sơ mới về 0", len(vm.ho_so_moi(str(SALES), "tu-van-bao-gia-online")) == 0)
r4 = chay(vm.viec_mau_xong(req("Hoa"), brain=str(SALES), slug="tu-van-bao-gia-online", title="Tư vấn báo giá online",
                           values="{}", result="x", edited="", chat_id="", key="k4cccccc"))
check("hồ sơ thứ 4 chưa kích hoạt lần nữa", "chung_cat" not in r4 and len(gia.spawned) == 1)

# "Ghi nhớ cách làm này": chạy ngay dù mới có 1 hồ sơ
chay(vm.viec_mau_xong(req(), brain=str(THUY), slug="tao-banner", title="Tạo banner", values="{}", result="Banner xong",
                      edited="", chat_id="", key="thuy-banner-1"))
check("brain Thủy: mới 1 hồ sơ, chưa tự chưng cất", len(gia.spawned) == 1)
g = chay(vm.viec_mau_ghi_nho(brain=str(THUY), slug="tao-banner", chat_id=""))
check("nút Ghi nhớ chạy ngay khi mới có 1 hồ sơ", isinstance(g, dict) and g.get("ok") and len(gia.spawned) == 2)
g2 = chay(vm.viec_mau_ghi_nho(brain=str(THUY), slug="tao-banner", chat_id=""))
check("bấm Ghi nhớ lần nữa khi hết hồ sơ mới: báo lỗi rõ", getattr(g2, "status_code", 200) == 409)
g3 = chay(vm.viec_mau_ghi_nho(brain=str(THUY), slug="../x", chat_id=""))
check("Ghi nhớ chặn slug lạ", getattr(g3, "status_code", 200) == 400)

# ---- 5. Thống kê, router ----
st = vm.thong_ke(str(SALES))
check("thống kê đếm đủ hồ sơ theo việc", st["tu-van-bao-gia-online"]["tong"] == 4 and st["tu-van-bao-gia-online"]["bay_ngay"] == 4)
app = FastAPI()
vm.register(app, lambda b: str(b), lambda: gia)
duong = set(moi_duong_dan(app))
check("đã đăng ký đủ 5 đường", {"/viec-mau", "/viec-mau/delete", "/viec-mau/xong", "/viec-mau/ghi-nho"} <= duong)
out = chay(vm.viec_mau_list(brain=str(THUY), all=0, stats=1))
check("GET trả danh sách, nhóm và thống kê", out["ok"] and out["items"] and out["groups"] and "tao-banner" in out["stats"])

print("\n" + ("TẤT CẢ OK" if not _fails else f"{len(_fails)} FAIL: " + "; ".join(_fails)))
sys.exit(1 if _fails else 0)
