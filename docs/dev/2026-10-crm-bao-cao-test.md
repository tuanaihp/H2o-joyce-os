# CRM van hanh 1.3.29 - bao cao kiem thu (26/10/2026)

Nhanh: `claude/crm-van-hanh-1-3-29` (dung tren `claude/gop-sua-do-1-3-28`). Chay trong worktree sach `E:\CLAUDECODE\wt-crm`, khong co `.env`.

## Ket qua bo test day du (880 test)

- **848/880 xanh** o lan chay dau, trong 1903 giay. 32 do, trong do:
  - **30 do tu truoc**, cung cac test do tren nhanh gop 1.3.28 (da chay lai rieng tren commit `c3be74a` de doi chieu: 28 test Python + `test_joyce_hands.js` + `test_joyce_humanoid.js`). Khong lien quan CRM (engine, nha cung cap, icon emoji, thieu module `channels.*`...).
  - **1 do do em gay ra va da sua**: `test_ui_actions.js` (danh sach trang cua lenh giong noi phai khop thanh ben). Da them `crm` vao `ui-actions.js` va `ui_targets.py`, chay lai xanh.
  - **1 do ngau nhien**: `test_khoi_dong_nhe.py` do khi may dang tai nang, chay rieng xanh (10 giay).
- Test moi cua tinh nang, deu xanh: `test_crm.py` (hop dong server), `test_crm_nhan_vien.py` (quyen), `test_crm.js` (giao dien tinh). `test_i18n.mjs`, `test_viec_mau*`, `test_hoi_thoai_crm` van xanh.

## Test bat duoc loi that

- Wiki phong ban dau ghi ca so dien thoai qua dong thoi gian ("phone: 0966..."). Da sua: dong thoi gian chi ghi ten truong, wiki con xoa SDT/email khoi moi dong.
- Chu nut chinh kho doc (dung `--accent-ink` thay vi `--on-accent`), co ca o khay Viec hang ngay cua 1.3.27. Da sua.

## Thu that tren trinh duyet (Chrome headless, may chu thu co lap cong 7792, du lieu tam)

Da thu: mo trang CRM tu thanh ben, danh ba, chi tiet khach, doi phong, pipeline, nut + va - giai doan, chuyen co hoi sang Da chot, bam xong viec (xuat hien o cot Xong cua Kanban voi tieu de `[CRM]`), phan khuc, man hinh dien thoai. Khong thu voi Zalo/Telegram that.

## Chua kiem chung

- CI tren GitHub (may nay khong co `gh`).
- Dang nhap bang tai khoan nhan vien that tren trinh duyet (quyen da duoc test o tang HTTP voi middleware that cua `main.py`).
- Goi model that de trich ho so (test dung model gia; khi khong co model chi con luat co dinh: SDT, email).
