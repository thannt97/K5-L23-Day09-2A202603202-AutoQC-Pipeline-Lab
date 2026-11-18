# Báo cáo Day 09 — <Họ và tên>, <MSHV>

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước
TODO(học viên): pipeline kết luận **Release / Hold / Rework**? Bao nhiêu ảnh vào, bao nhiêu ảnh ra dataset? Lý do chính (1–3 câu).

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| TODO(học viên) | | | |

TODO(học viên): vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?

## 3. Calibration (2 ngưỡng)
Số liệu từ `submission/calibration/calibration_report.md` (calib 39 ảnh) và từ chạy thử pipeline trên raw với từng cặp giá trị.

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **12** | DUP_IMAGE_NEAR: 1.00 / 0.50 → 1.00 / 0.67 (EXACT giữ 1.00 / 1.00) | Lỗi này dẫn tới **xoá ảnh** nên ưu tiên precision. Trên calib 4–14 cho cùng P/R; 16 nhìn đẹp nhất trên calib (R 0.83) nhưng trên raw loại thêm 9 ảnh mà 8 ảnh là khác hẳn nhau (xem dưới). 12 nằm giữa vùng an toàn 4–14, vẫn bắt được cặp trùng thật ở khoảng cách 10 (img_0186 ~ img_0061). |
| `second_opinion.conf` | 0.25 | **0.7** | WRONG_CLASS 0.56 / 0.83 → 0.62 / 0.83; MISSING 0.50 / 1.00 → 0.58 / 0.88; LOOSE_BOX 0.29 / 0.40 → 0.50 / 0.20; FALSE_POS 0.31 / 1.00 (không đổi, dùng `fp_conf` cố định) | Đây là **cảnh báo cho người** nên giữ recall cao: precision tăng, recall WRONG_CLASS giữ 0.83, MISSING chỉ mất 1/8. Hàng đợi raw giảm 145 → 118 ảnh. Không chọn 0.8 dù ra Release (hàng đợi 102): recall MISSING tụt còn 0.75 — hạ recall chỉ để hàng đợi "vừa" là Release giả. Không chọn ≤ 0.6: precision MISSING ~0.5, hàng đợi ≥ 125 ảnh, phần dư không ai xem. |

**Một chỗ calibration đánh lừa: `phash_dist = 16`.** Trên calib, 16 có F1 DUP_IMAGE_NEAR cao nhất (0.91 so với 0.80). Nhưng chạy trên raw, từ 12 → 16 số ảnh bị loại ở bước 1 tăng 22 → 31. Mở xem từng cặp (`submission/evidence_phash_pairs.png`): chỉ img_0084 ~ img_0074 là trùng thật (ảnh crop); 8 ảnh còn lại là ảnh **khác hẳn** — img_0011 (tennis) bị coi là trùng img_0008 (trượt tuyết), img_0177 (lướt sóng) ~ img_0113 (người ngồi bàn), và 6 ảnh bị báo `LEAK_TEST` sai (img_0013 bàn làm việc ~ test_087 sân bóng chày, img_0038 lướt sóng ~ test_002 bánh cưới…). Lý do: calib chỉ có 6 cặp gần trùng và **không có ca LEAK_TEST**, trong khi raw so với cả kho test/val 140 ảnh nên số cặp "trùng do ngẫu nhiên" lớn hơn nhiều. Tối ưu theo calib sẽ xoá nhầm ~4% dữ liệu tốt. Đổi lại, với 12 pipeline bỏ sót cặp crop img_0084 ~ img_0074 (khoảng cách 16) — ghi nhận là điểm mù ở mục 4.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

**(a) Gate chặn thật.** Chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt):
log in `kết luận: REWORK — còn 6 lỗi bắt buộc (MISSING_LABEL_FILE) trên 6 ảnh/mục`, rồi `Bước 5/5 KHÔNG xuất: còn lỗi bắt buộc (Rework)`; **mã thoát 20**, thư mục `work/exp_nb` **không được tạo**.
Lý do: 6 ảnh thiếu file nhãn máy không được bịa nhãn (`autofix` chỉ ghi `needs_label`), không người gán thì lỗi bắt buộc còn nguyên → Rework.
Với ngân sách 80 (`make run`): người gán 6 ảnh này (NEEDS_LABEL ưu tiên đầu hàng đợi) → 0 lỗi bắt buộc, mã thoát 10 (Hold). Chạy lại 2 lần: các CSV và `manifest.json` giống hệt (md5).

**Quan sát thủ công trước khi chạy pipeline** (`python scripts/viz_labels.py ...`, xem `work/viz/`) và đối chiếu sau `make run`:

| Ảnh | Lỗi nhìn thấy | Pipeline báo (`02_error_list_v1`) | Hàng đợi (`05_review_queue`) | Kết quả |
|---|---|---|---|---|
| img_0001 | Thiếu box người lính đứng giữa | `POSSIBLE_MISSING` (WARN) | hạng 20/118 → được duyệt | bắt đúng |
| img_0001 | Dòng 1 và dòng 3 gần trùng hệt (cùng lớp person) | `DUP_BOX` dòng 3 (ERROR) | — | máy tự xoá dòng 3 |
| img_0045 | Box `car` (dòng 6) đặt lên người phụ nữ đội mũ trắng → gán nhầm person → car | chỉ `POSSIBLE_LOOSE_BOX`, **không** có WRONG_CLASS / FALSE_POS | hạng 83/118 → **ngoài** ngân sách 80, không ai xem | **lọt** (cờ sai loại) |
| img_0060 | Box truck cắt mất phần đầu xe | **không có cờ nào** | không vào hàng đợi | **lọt** |

Nhận xét: 3 lỗi nhìn thấy bằng mắt đều là lỗi **ngữ nghĩa** — chỉ 1/3 được máy cờ đúng loại; `DUP_BOX` là lỗi **quy tắc**, máy bắt và sửa chắc chắn. Đúng tinh thần "máy kiểm quy tắc, người kiểm ý nghĩa".

**(b) Điểm mù có bằng chứng.**
1. **Model lớn cũng sai giống nhãn** (img_0060): box truck cắt mất đầu xe, nhưng dự đoán yolo26l (truck, conf 0.78) có IoU **0.84** với box nhãn — model vẽ box gần giống nên "ý kiến thứ hai" đồng ý với nhãn sai, không cờ gì. Calib cũng cho thấy box lỏng khó bắt: recall `POSSIBLE_LOOSE_BOX` chỉ 0.20 (1/5).
2. **Nhầm lớp bị che bởi nhãn cùng lớp bên cạnh** (img_0045): model thấy *person* (conf 0.75) trùng box `car` dòng 6 với IoU **0.91** — đáng lẽ là WRONG_CLASS. Nhưng một box person bên cạnh cũng chồng lên dự đoán với IoU ≥ 0.3, và quy tắc "có ứng viên cùng lớp thì ưu tiên" biến nó thành `POSSIBLE_LOOSE_BOX` (trọng số thấp) → hạng 83, ngoài ngân sách 80 nên không ai xem. Box `car` cũng không bị FALSE_POS vì có dự đoán khớp. Ảnh đông người là chỗ thuật toán ghép dự đoán–nhãn yếu.
3. **Ảnh trùng biến đổi mạnh (crop)**: img_0084 ~ img_0074 là cùng một cảnh bị cắt, khoảng cách phash 16 > ngưỡng 12 → không bị loại (xem mục 3). Tăng ngưỡng lên 16 thì bắt được nhưng xoá nhầm 8 ảnh khác.
4. **Ngân sách duyệt**: 118 ảnh cần duyệt nhưng chỉ có 80 → 29/202 ảnh (14,36%) còn cảnh báo chưa ai xem; các lỗi ngữ nghĩa trong đó (như img_0045) đi thẳng vào dataset nếu ép Release.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).

TODO(học viên): chênh mAP50 (clean − raw) so với **độ lệch chuẩn giữa các seed**; kết luận **trung thực** (nằm trong nhiễu thì nói là chưa kết luận được); ≥ 2 giả thuyết giải thích (ảnh trùng/rò rỉ test trong `raw`, nhãn máy còn lại trong `clean`, test chỉ 100 ảnh…) và cách kiểm.

## 6. Quyết định và ghi chú AI
TODO(học viên): (a) quyết định cuối; nếu Hold/Rework cần làm gì để thành Release? (b) Dùng AI viết code? Ghi 3 dòng: prompt chính, cách bạn kiểm code AI, 1 lần AI sai. Không dùng: ghi "không dùng".

*(Thưởng +2, tùy chọn)* CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
