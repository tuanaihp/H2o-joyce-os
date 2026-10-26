---
type: viec-mau
title: "Tạo khoá học mới"
group: "Khoá học"
icon: graduation-cap
inputs: [{"key":"ten_khoa","label":"Tên khoá","type":"text","required":true},{"key":"doi_tuong","label":"Học viên là ai","type":"text","required":false},{"key":"muc_tieu","label":"Học xong làm được gì","type":"longtext","required":false}]
route: auto
sop: "wiki/dao-tao/khoa-hoc"
by: "seed"
order: 10
hidden: false
---

Lên bản thiết kế khoá học "{ten_khoa}" cho {doi_tuong}. Mục tiêu đầu ra: {muc_tieu}. Dựa vào khung thiết kế khoá học và các khoá đã có trong wiki/dao-tao để giữ cùng phong cách: mục tiêu, lộ trình theo buổi, bài tập, cách đánh giá. Trình bày gọn, có thể giao ngay cho người soạn bài.
