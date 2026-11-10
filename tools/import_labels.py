#!/usr/bin/env python3
"""Import exported YOLO detection labels from Roboflow / Label Studio into dataset/labels/train.

Both tools export "YOLO" but in different formats, so this script auto-detects:

  * normalized, class FIRST      -> "0 0.482000 0.613500 0.153100 0.213900"
    (Roboflow YOLOv5 / YOLOv8, or Ultralytics)
  * normalized, class NAME first -> "car 0.482000 0.613500 0.153100 0.213900"
    (Roboflow YOLOv8 with class names)
  * PIXEL corners, class LAST   -> "120 200 320 480 0"
    (Label Studio YOLO export: xmin ymin xmax ymax class_index)

Usage:
    # Roboflow export (thư mục export/ chứa data.yaml + images/ + labels/)
    python tools/import_labels.py --source "path/to/export" --class-map data.yaml

    # Label Studio export (thư mục chứa các file .txt pixel + classes.txt)
    python tools/import_labels.py --source "path/to/ls_export" --pixel --classes-file classes.txt

Always writes to dataset/labels/train/ with the same basename as the images.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

CLASS_NAMES = ["car", "truck", "bus", "van"]
NAME_TO_ID = {name: index for index, name in enumerate(CLASS_NAMES)}
IMG_EXTS = (".jpg", ".jpeg", ".png")


def read_class_map(path: Path) -> dict[str, int]:
    """Parse a Roboflow data.yaml into {class_name: id}."""
    text = path.read_text(encoding="utf-8")
    names: dict[str, int] = {}
    in_names = False
    for line in text.splitlines():
        if line.strip().startswith("names:"):
            in_names = True
            continue
        if in_names:
            match = re.match(r"\s*(\d+)\s*:\s*(.+)", line)
            if match:
                names[match.group(2).strip().strip("'\"")] = int(match.group(1))
            elif line.strip() and not line.startswith((" ", "\t")):
                break
    if not names:
        raise ValueError(f"Không đọc được 'names:' từ {path}")
    return names


def looks_like_pixels(values: list[float], image_size: tuple[int, int]) -> bool:
    """Pixel coords exceed 1.0 (normalized) -> pixel format."""
    width, height = image_size
    return any(value > 1.5 for value in values)


def convert_lines(
    raw_lines: list[str],
    image_size: tuple[int, int],
    name_to_id: dict[str, int],
    source: Path,
) -> list[str]:
    width, height = image_size
    out: list[str] = []
    for number, raw in enumerate(raw_lines, start=1):
        parts = raw.split()
        if not parts:
            continue
        if len(parts) != 5:
            raise ValueError(f"{source}:{number} cần đúng 5 giá trị, thấy {len(parts)}: {raw!r}")

        # class token: numeric id or class name
        token = parts[0]
        try:
            class_id = int(token)
        except ValueError:
            key = token.strip().strip("'\"").lower()
            if key not in name_to_id:
                raise ValueError(f"{source}:{number} lớp lạ {token!r} (cần car/truck/bus/van)")
            class_id = name_to_id[key]
        values = [float(value) for value in parts[1:]]

        if looks_like_pixels(values, image_size):
            # pixel corners: xmin ymin xmax ymax  ->  normalized xc yc w h
            xmin, ymin, xmax, ymax = values
        else:
            # already normalized: xc yc w h -> pixel corners
            xc, yc, bw, bh = values
            xmin, ymin = (xc - bw / 2) * width, (yc - bh / 2) * height
            xmax, ymax = (xc + bw / 2) * width, (yc + bh / 2) * height

        if xmax < xmin:
            xmin, xmax = xmax, xmin
        if ymax < ymin:
            ymin, ymax = ymax, ymin

        new_xc = ((xmin + xmax) / 2) / width
        new_yc = ((ymin + ymax) / 2) / height
        new_w = (xmax - xmin) / width
        new_h = (ymax - ymin) / height

        new_xc = min(max(new_xc, 0.0), 1.0)
        new_yc = min(max(new_yc, 0.0), 1.0)
        new_w = min(max(new_w, 0.0), 1.0)
        new_h = min(max(new_h, 0.0), 1.0)
        if new_w <= 0 or new_h <= 0:
            continue

        out.append(f"{class_id} {new_xc:.6f} {new_yc:.6f} {new_w:.6f} {new_h:.6f}")
    return out


def find_image(image_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXTS:
        candidate = image_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Đưa nhãn export từ Roboflow/Label Studio về dataset/labels/train.")
    parser.add_argument("--source", type=Path, required=True, help="thư mục export")
    parser.add_argument("--images", type=Path, default=Path("dataset/images/train"))
    parser.add_argument("--labels", type=Path, default=Path("dataset/labels/train"))
    parser.add_argument("--class-map", type=Path, default=None, help="data.yaml của Roboflow (lấy đúng thứ tự lớp)")
    parser.add_argument("--classes-file", type=Path, default=None, help="classes.txt của Label Studio")
    parser.add_argument("--pixel", action="store_true", help="ép hiểu nhãn là toạ độ pixel")
    parser.add_argument("--dry-run", action="store_true", help="chỉ in ra kết quả, không ghi file")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Không tìm thấy {args.source}")
        return 1

    name_to_id = {name: index for index, name in enumerate(CLASS_NAMES)}
    if args.class_map and args.class_map.exists():
        name_to_id = read_class_map(args.class_map)
        print(f"Đọc class map từ {args.class_map}: {name_to_id}")
    if args.classes_file and args.classes_file.exists():
        names = [
            line.strip()
            for line in args.classes_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if names:
            name_to_id = {name: index for index, name in enumerate(names)}
            print(f"Đọc class map từ {args.classes_file}: {name_to_id}")

    label_files = sorted(args.source.rglob("*.txt"))
    label_files = [p for p in label_files if p.name != "classes.txt"]
    if not label_files:
        print(f"Không có file .txt nhãn trong {args.source}")
        return 1

    from PIL import Image

    written = 0
    skipped = []
    for label_path in label_files:
        stem = label_path.stem
        image_path = find_image(args.images, stem)
        if image_path is None:
            skipped.append(stem)
            continue

        raw_lines = label_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        with Image.open(image_path) as handle:
            image_size = handle.size

        if args.pixel:
            values = []
            for raw in raw_lines:
                parts = raw.split()
                if len(parts) == 5:
                    values.extend(float(v) for v in parts[1:])
            if values and not looks_like_pixels(values, image_size):
                print(f"CẢNH BÁO {stem}: --pixel được bật nhưng toạ độ có vẻ đã chuẩn hoá.")

        try:
            lines = convert_lines(raw_lines, image_size, name_to_id, label_path)
        except ValueError as error:
            print(f"LỖI {error}")
            return 2

        target = args.labels / f"{stem}.txt"
        print(f"{stem}: {len(lines)} box (ảnh {image_size[0]}x{image_size[1]})")
        if not args.dry_run:
            args.labels.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        written += 1

    print(f"\n{'Đã xem' if args.dry_run else 'Đã ghi'} {written} file {'vào ' + str(args.labels) if not args.dry_run else 'trong ' + str(args.source)}.")
    if skipped:
        print(f"BỎ QUA {len(skipped)} file không khớp ảnh: {', '.join(skipped[:10])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
