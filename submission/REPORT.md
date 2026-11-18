# Báo cáo Day 09 — Nguyễn Thanh Thản, 2A202603202

## 1. Kết luận trước
Pipeline kết luận **HOLD** (mã thoát 10). Vào **224 ảnh** → loại 22 ở cửa vào → **202 ảnh** ra dataset `submission/export/clean_v1` (bản nháp, chưa phát hành).
Không còn lỗi bắt buộc (0 ERROR trong `07_error_list_v3`), nhưng **29/202 ảnh (14,36%)** còn cảnh báo chưa được người duyệt, ≥ ngưỡng 10%: hàng đợi cần duyệt 118 ảnh mà ngân sách chỉ 80.

## 2. Lỗi và phân việc
Từ `02_error_list_v1` (trước khi sửa, 194 dòng lỗi trên 224 ảnh quét):

| Mã lỗi | Số dòng (số ảnh) | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| CORRUPT_IMAGE | 2 (2) | máy — loại ảnh | không mở/load được, không dùng được để train |
| BAD_SIZE | 3 (3) | máy — loại ảnh | cạnh ngắn < 250 px (quy tắc dự án) |
| DUP_IMAGE_EXACT | 8 (8) | máy — loại ảnh | trùng từng byte (md5), chắc chắn |
| DUP_IMAGE_NEAR | 4 (4) | máy — loại ảnh | phash ≤ 12, đã mở xem từng cặp (mục 3) |
| LEAK_TEST | 5 (5) | máy — loại ảnh | trùng ảnh test/val: để lại là gian lận khi đo |
| BAD_CLASS_NAME | 2 (data.yaml) | máy — ghi lại `names` | danh sách lớp là quy tắc cố định của dự án |
| BAD_FORMAT | 3 (3) | máy — xoá dòng | dòng không đúng 5 cột số, không đoán được ý định |
| BAD_CLASS_ID | 6 (6) | máy — xoá dòng | id ngoài 0..3, không biết lớp đúng |
| BOX_ZERO | 4 (4) | máy — xoá dòng | box không có diện tích |
| DUP_BOX | 7 (7) | máy — xoá dòng sau | cùng lớp, IoU > 0.9: box thừa |
| BOX_OUT_OF_IMAGE | 8 (8) | máy — cắt box về [0,1] | sửa hình học, giữ nguyên lớp |
| MISSING_LABEL_FILE | 6 (6) | **người** — gán nhãn | máy không được bịa nhãn (file rỗng = "ảnh nền") |
| POSSIBLE_MISSING | 44 (43) | **người** | model lớn thấy vật mà nhãn không có — có thể model sai |
| POSSIBLE_FALSE_POS | 29 (27) | **người** | box không khớp vật nào model thấy |
| POSSIBLE_LOOSE_BOX | 22 (21) | **người** | đúng vật nhưng box lệch/lỏng |
| POSSIBLE_WRONG_CLASS | 16 (16) | **người** | nhầm lớp hợp lệ (car/truck/bus) — chỉ người phân xử được |
| EMPTY_LABEL / BOX_TINY / BOX_HUGE / CLASS_RARE | 12 / 6 / 3 / 4 | **người** (ưu tiên thấp) | ảnh nền hay thiếu nhãn? box nhỏ/lớn bất thường: cần nhìn |

Máy tự sửa **35 thay đổi** (`03_fixes.csv`: 20 `drop_line`, 8 `clip_box`, 1 `rename_classes`, 6 `needs_label`) + loại 22 ảnh; sau sửa (`04_error_list_v2`) chỉ còn 6 lỗi bắt buộc `MISSING_LABEL_FILE`.

**Hàng đợi `05_review_queue.csv` (118 ảnh)** xếp theo tổng trọng số `review.weights` của các mã trên ảnh: đầu hàng là img_0020 (11.5: vừa bị xoá dòng, vừa MISSING + WRONG_CLASS), rồi 6 ảnh `NEEDS_LABEL` (trọng số 10 — không người gán thì chắc chắn Rework), sau đó các ảnh WRONG_CLASS (3) / MISSING (2). Với ngân sách 80 ảnh, người duyệt đã xem **tất cả** ảnh có POSSIBLE_MISSING (43/43) và WRONG_CLASS (16/16), cùng 6/6 ảnh thiếu nhãn, nhưng chỉ 13/21 ảnh LOOSE_BOX và 11/23 ảnh FALSE_POS; 38 ảnh cuối hàng (FALSE_POS, LOOSE_BOX, BOX_TINY…) không ai xem → 29 ảnh còn cảnh báo ở `07_error_list_v3`.

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

## 5. Train: raw vs clean
Chạy `notebooks/day09_train_compare.ipynb` trên Colab T4: **yolo26n.pt, 20 epoch, imgsz 640, batch 16, seed 0 và 1**; cùng val (`gold_val`, 40 ảnh) và cùng test (100 ảnh) cho cả hai biến thể. `clean` = `submission/export/clean_v1` (manifest sha1 `efbf5ef…`, khớp file trong repo), là bản xuất khi pipeline **Hold**. Bảng từ `submission/results/comparison.md`:

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 202 | 2 | 0.712 ± 0.012 | 0.489 ± 0.009 | 0.772 ± 0.054 | 0.627 ± 0.029 |

AP50 theo lớp (TB 2 seed, từ `*_seed*.json`): car 0.738 (raw) / 0.745 (clean) · person 0.822 / 0.824 · **truck 0.648 / 0.556** · bus 0.695 / 0.725.

**Kết luận: chưa kết luận được clean tốt hơn hay kém hơn raw.** Chênh mAP50 (clean − raw) = **−0.013**, cỡ bằng độ lệch giữa 2 seed của clean (0.012); precision/recall lệch giữa seed tới 0.03–0.06, lớn hơn chênh lệch giữa hai biến thể. mAP50-95 thấp hơn 0.023 (≈ 2–3 lần độ lệch seed) nhưng chỉ có 2 seed nên ước lượng độ lệch rất thô. Gần như toàn bộ chênh lệch đến từ lớp **truck** (−0.09); car/person gần như bằng nhau, bus clean còn nhỉnh hơn.

**Giả thuyết và cách kiểm:**
1. **Raw được "nhìn trước" tập test.** Pipeline loại 5 ảnh `LEAK_TEST` (trùng ảnh test: test_009, 033, 039, 044, 085) khỏi clean nhưng raw vẫn train trên chúng → điểm raw bị thổi phồng. *Kiểm:* đánh giá lại cả hai model trên test bỏ 5 ảnh này; nếu khoảng cách thu hẹp/đảo chiều thì đây là nguyên nhân.
2. **Truck chỉ có 24 box trong test** → AP truck dao động mạnh theo vài box (2 seed của clean đã lệch 0.05). Clean thực ra có **nhiều** box truck hơn raw (40 so với 32, sau sửa tự động + người duyệt), nên −0.09 nhiều khả năng là nhiễu của lớp ít mẫu hoặc do định nghĩa truck/car không nhất quán (pickup). *Kiểm:* thêm seed (≥ 3–5), xem confusion matrix truck↔car trên test.
3. **Clean ít ảnh hơn (202 so với 224, −10%)** và còn 29 ảnh có cảnh báo chưa được duyệt (nhãn máy lỗi ngữ nghĩa còn nguyên, như img_0045) → lợi ích làm sạch bị bù trừ bởi mất dữ liệu. *Kiểm:* train biến thể `oracle` (nhãn chuẩn) làm chặn trên; tăng ngân sách duyệt để đưa pipeline về Release rồi train lại.

**Việc tiếp theo:** chạy thêm seed (≥ 3), đo lại trên test bỏ ảnh rò rỉ, và chỉ kết luận "clean tốt hơn" khi chênh lệch vượt rõ độ lệch giữa các seed.

## 6. Quyết định và ghi chú AI
**(a) Quyết định: HOLD** — dataset `clean_v1` chỉ dùng thử nghiệm, chưa phát hành. Để thành **Release** cần đưa tỉ lệ ảnh còn cảnh báo chưa duyệt xuống < 10%, tức còn tối đa 20/202 ảnh: duyệt thêm ít nhất **9** ảnh trong 38 ảnh cuối hàng đợi (ngân sách ~89 thay vì 80 — trong lab ngân sách cố định nên phải xin thêm giờ duyệt, không được nới ngưỡng); đồng thời không được phát sinh lỗi bắt buộc mới. Nếu người duyệt không gán được 6 ảnh thiếu nhãn thì kết luận chuyển sang **Rework** (đã chứng minh ở mục 4a). Không đổi `second_opinion.conf` lên 0.8 chỉ để ra Release (mục 3).

**(b) Có dùng AI (Claude)** để viết 4 module, chạy calibrate/pipeline và soạn nháp báo cáo.
- *Prompt chính:* đưa docstring của từng stub (đầu vào/đầu ra, bảng mã lỗi, bẫy), file test tương ứng, và yêu cầu: ngưỡng lấy từ `cfg`, không sửa `data/raw`, không viết cứng tên ảnh, dòng hỏng không làm script chết.
- *Cách kiểm:* chạy `pytest` từng module rồi cả bộ (79/79), tự thử thêm ca dòng dính 2 lỗi, dòng trống giữa file, ảnh `.JPG`, chạy `autofix` 2 lần (idempotent); chạy pipeline 2 lần so md5 báo cáo; đối chiếu 3 ảnh tự xem (`viz_labels.py`) với `02_error_list_v1` / `05_review_queue`; mở xem từng cặp ảnh bị coi là trùng khi chọn `phash_dist`.
- *Một lần AI sai:* khi đối chiếu ảnh, AI dự đoán img_0045 (box `car` trên người) sẽ bị cờ `POSSIBLE_WRONG_CLASS` và img_0060 bị cờ vì box lỏng (IoU < 0.5). Kiểm lại bằng dự đoán trong cache thì sai cả hai: img_0045 chỉ bị `LOOSE_BOX` (do box person bên cạnh chồng lên), img_0060 có IoU 0.84 với model nên không bị cờ — đã sửa báo cáo theo số đo thật và chuyển chúng thành điểm mù ở mục 4.
