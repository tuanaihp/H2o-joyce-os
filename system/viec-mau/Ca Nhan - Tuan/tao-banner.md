---
type: viec-mau
title: "Tạo banner"
group: "Banner"
icon: image
inputs: [{"key":"noi_dung","label":"Banner về","type":"text","required":true},{"key":"kich_thuoc","label":"Kích thước","type":"select","required":false,"options":["Vuông","Ngang","Dọc"]}]
route: auto
sop: ""
by: "seed"
order: 60
hidden: false
---

Tạo banner về "{noi_dung}" khổ {kich_thuoc} bằng joyce_generate_image, hiện ảnh ngay trong chat.
