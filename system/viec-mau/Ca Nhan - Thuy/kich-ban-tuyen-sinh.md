---
type: viec-mau
title: "Kịch bản tuyển sinh"
group: "Kinh doanh"
icon: megaphone
inputs: [{"key":"khoa","label":"Khoá cần tuyển","type":"text","required":true},{"key":"kenh","label":"Kênh","type":"select","required":false,"options":["Facebook","TikTok","Zalo","Trực tiếp"]}]
route: auto
sop: "wiki/dao-tao/tuyen-sinh"
by: "seed"
order: 40
hidden: false
---

Soạn kịch bản tuyển sinh khoá "{khoa}" cho kênh {kenh}, theo cách làm đã có trong wiki/dao-tao/tuyen-sinh.
