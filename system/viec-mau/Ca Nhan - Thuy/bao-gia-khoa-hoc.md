---
type: viec-mau
title: "Báo giá khoá học"
group: "Khoá học"
icon: receipt
inputs: [{"key":"hoc_vien","label":"Tên học viên","type":"text","required":true},{"key":"khoa","label":"Khoá quan tâm","type":"text","required":true}]
route: auto
sop: "wiki/kinh-doanh/bao-gia"
by: "seed"
order: 30
hidden: false
---

Soạn báo giá khoá "{khoa}" cho học viên {hoc_vien} theo bảng giá trong wiki/kinh-doanh/bao-gia. Không bịa giá; chỗ nào wiki chưa có thì ghi rõ cần chị Thủy xác nhận.
