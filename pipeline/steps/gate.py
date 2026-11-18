"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    thr = cfg["gate"]["warn_ratio_hold"]
    stems = set(image_stems)
    reviewed = set(reviewed)
    n_images = len(stems)

    # Lỗi bắt buộc: đếm TẤT CẢ (kể cả lỗi cấp dataset như data.yaml), không bao giờ bỏ qua dù ảnh đã duyệt
    errors = [i for i in issues if i.severity == ERROR]
    n_errors = len(errors)

    # Cảnh báo: đếm số ẢNH khác nhau, chỉ ảnh thuộc dataset và chưa được người duyệt
    warn_images = {i.image for i in issues
                   if i.severity == WARN and i.image in stems and i.image not in reviewed}
    n_warn = len(warn_images)
    ratio = round(n_warn / n_images, 4) if n_images else 0.0

    reasons = []
    if n_errors:
        decision = "Rework"
        codes = sorted({i.code for i in errors})
        reasons.append(f"còn {n_errors} lỗi bắt buộc ({', '.join(codes)}) trên "
                       f"{len({i.image for i in errors})} ảnh/mục: phải sửa trước khi xuất")
    elif n_images and ratio >= thr:
        decision = "Hold"
        reasons.append(f"{n_warn}/{n_images} ảnh ({ratio:.2%}) còn cảnh báo chưa được người duyệt, "
                       f">= ngưỡng {thr:.0%}")
    else:
        decision = "Release"
        reasons.append(f"không còn lỗi bắt buộc; {n_warn}/{n_images} ảnh ({ratio:.2%}) còn cảnh báo chưa duyệt, "
                       f"< ngưỡng {thr:.0%}")
    if reviewed:
        reasons.append(f"{len(reviewed & stems)} ảnh đã được người duyệt (cảnh báo của các ảnh này coi như đã xử lý)")

    return dict(decision=decision, n_errors=n_errors, n_warn_images=n_warn,
                n_images=n_images, warn_ratio=ratio, reasons=reasons)
