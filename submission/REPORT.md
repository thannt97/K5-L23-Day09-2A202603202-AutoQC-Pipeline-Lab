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
TODO(học viên): (a) chứng minh gate chặn đúng: chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt nên ảnh thiếu file nhãn còn nguyên), chỉ ra kết luận **Rework**, mã thoát 20 và việc **không xuất** dataset. (Đừng sửa tay `work/run/ds`: pipeline dựng lại thư mục này từ raw mỗi lần chạy.) (b) ≥ 2 điểm mù có bằng chứng (box lỏng nhẹ, nhầm lớp mà model lớn cũng nhầm, ảnh trùng biến đổi mạnh…).

**Quan sát thủ công trước khi chạy pipeline** (`python scripts/viz_labels.py ...`, xem `work/viz/`):

| Ảnh | Lỗi nhìn thấy | Mã lỗi dự kiến | Ai bắt |
|---|---|---|---|
| img_0001 | Thiếu box người lính đứng giữa ảnh | `POSSIBLE_MISSING` (WARN) | `second_opinion` → người duyệt |
| img_0001 | Dòng 1 và dòng 3 gần trùng hệt (cùng lớp person, IoU ≈ 1) | `DUP_BOX` (ERROR) | `label_format` → `autofix` xoá dòng 3 |
| img_0045 | Box `car` (dòng 6) đặt lên người phụ nữ đội mũ trắng, người này không có box person nào → nghi gán nhầm lớp person → car | `POSSIBLE_WRONG_CLASS` (hoặc `POSSIBLE_FALSE_POS`) (WARN) | `second_opinion` → người duyệt |
| img_0060 | Box truck không bao hết xe, cắt mất phần đầu xe (mép phải ~263px trong khi xe tới ~303px) | `POSSIBLE_LOOSE_BOX` (WARN) | `second_opinion` → người duyệt |

Nhận xét: 3 lỗi nhìn thấy bằng mắt đều là lỗi **ngữ nghĩa**, check cú pháp không bắt được; máy (yolo26l) chỉ cảnh báo, người duyệt quyết định. Riêng `DUP_BOX` ở img_0001 là lỗi **quy tắc**, máy sửa an toàn — đúng tinh thần "máy kiểm quy tắc, người kiểm ý nghĩa".
TODO(học viên): sau `make run`, đối chiếu 3 ảnh này trong `02_error_list_v1` và `05_review_queue.csv`: có bị cờ không, có nằm trong 80 ảnh được duyệt không. Ảnh nào không bị cờ → ghi vào điểm mù ở (b).

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).

TODO(học viên): chênh mAP50 (clean − raw) so với **độ lệch chuẩn giữa các seed**; kết luận **trung thực** (nằm trong nhiễu thì nói là chưa kết luận được); ≥ 2 giả thuyết giải thích (ảnh trùng/rò rỉ test trong `raw`, nhãn máy còn lại trong `clean`, test chỉ 100 ảnh…) và cách kiểm.

## 6. Quyết định và ghi chú AI
TODO(học viên): (a) quyết định cuối; nếu Hold/Rework cần làm gì để thành Release? (b) Dùng AI viết code? Ghi 3 dòng: prompt chính, cách bạn kiểm code AI, 1 lần AI sai. Không dùng: ghi "không dùng".

*(Thưởng +2, tùy chọn)* CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
