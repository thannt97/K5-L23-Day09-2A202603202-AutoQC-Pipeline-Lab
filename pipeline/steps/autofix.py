"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
CLIP_CODES = {"BOX_OUT_OF_IMAGE"}
REMOVE_CODES = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _fmt(c, x, y, w, h):
    return f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"


def _clip(text):
    """Cắt box về [0,1]. Trả về dòng mới, hoặc None nếu sau khi cắt box không còn diện tích."""
    c, x, y, w, h = parse_yolo_line(text)
    x1, x2 = max(0.0, x - w / 2), min(1.0, x + w / 2)
    y1, y2 = max(0.0, y - h / 2), min(1.0, y + h / 2)
    if x2 <= x1 or y2 <= y1:
        return None
    return _fmt(c, (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)


def fix(ds, issues, cfg):
    errors = [i for i in issues if i.severity == ERROR]      # cảnh báo là việc của người: không động tới
    fixes = []

    # 1) Xoá ảnh (trùng, rò rỉ test, hỏng, quá nhỏ): mỗi ảnh xoá 1 lần
    removed = set()
    for stem in dict.fromkeys(i.image for i in errors if i.code in REMOVE_CODES):
        img = ds.image_path(stem)
        lab = ds.label_path(stem)
        if img is None and not lab.exists():
            continue                                        # đã xoá từ lần trước: idempotent
        codes = sorted({i.code for i in errors if i.image == stem and i.code in REMOVE_CODES})
        if img is not None:
            img.unlink()
        if lab.exists():
            lab.unlink()
        removed.add(stem)
        fixes.append(dict(image=stem, line="", action="remove_image",
                          before=img.name if img is not None else lab.name, after=f"đã xoá ({', '.join(codes)})"))

    # 2) data.yaml: ghi lại names đúng cfg["classes"] (1 lần dù có nhiều lỗi BAD_CLASS_NAME)
    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        data = {}
        if ds.yaml_path.exists():
            data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
        before = data.get("names")
        if before != list(cfg["classes"]):
            data["names"] = list(cfg["classes"])
            data["nc"] = len(cfg["classes"])
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            fixes.append(dict(image="data.yaml", line="", action="rename_classes",
                              before=str(before), after=str(list(cfg["classes"]))))

    # 3) Sửa dòng nhãn: gom theo file, dùng số dòng GỐC, ghi lại file MỘT lần
    by_file = defaultdict(dict)                             # stem -> {số dòng: "drop" | "clip"}
    for i in errors:
        if i.line is None or i.image in removed:
            continue
        if i.code in DROP_CODES:
            by_file[i.image][int(i.line)] = "drop"          # xoá dòng thắng clip
        elif i.code in CLIP_CODES:
            by_file[i.image].setdefault(int(i.line), "clip")

    for stem, todo in by_file.items():
        lab = ds.label_path(stem)
        if not lab.exists():
            continue                                        # ảnh/nhãn đã bị xoá: bỏ qua êm
        raw = lab.read_text(encoding="utf-8", errors="replace").splitlines()
        out, changed = [], False
        for no, text in enumerate(raw, 1):                  # đếm cả dòng trống, giống read_label_lines
            act = todo.get(no)
            if act is None or not text.strip():
                out.append(text)
                continue
            if act == "clip":
                try:
                    new = _clip(text)
                except ValueError:
                    new = None
                if new is not None:
                    out.append(new)
                    changed = True
                    fixes.append(dict(image=stem, line=no, action="clip_box", before=text, after=new))
                    continue
                # cắt xong không còn diện tích (hoặc dòng hỏng) -> xoá dòng
            changed = True
            fixes.append(dict(image=stem, line=no, action="drop_line", before=text, after="(xoá dòng)"))
        if changed:
            lab.write_text("".join(t + "\n" for t in out), encoding="utf-8")

    # 4) Thiếu file nhãn: KHÔNG bịa nhãn, KHÔNG tạo file rỗng -> chuyển người gán
    for stem in dict.fromkeys(i.image for i in errors if i.code == "MISSING_LABEL_FILE"):
        if stem in removed or ds.label_path(stem).exists():
            continue
        fixes.append(dict(image=stem, line="", action="needs_label", before="(không có file)", after="chuyển người gán"))

    return fixes
