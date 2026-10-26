---
type: viec-mau
title: "Báo cáo bán hàng cuối ngày"
group: "Báo cáo"
icon: clipboard-list
inputs: [{"key":"so_khach","label":"Số khách tư vấn","type":"text","required":false},{"key":"so_chot","label":"Số khách chốt","type":"text","required":false},{"key":"ghi_chu","label":"Ghi chú trong ngày","type":"longtext","required":false}]
route: auto
sop: ""
by: "seed"
order: 60
hidden: false
---

Viết báo cáo bán hàng cuối ngày: tư vấn {so_khach} khách, chốt {so_chot}. Ghi chú: {ghi_chu}. Trình bày gọn: kết quả, lý do khách chưa chốt, việc cần làm ngày mai. Nếu có số liệu từ hệ thống bán hàng đã kết nối thì đối chiếu, không có thì nói rõ là chỉ dựa trên số nhân viên nhập.
