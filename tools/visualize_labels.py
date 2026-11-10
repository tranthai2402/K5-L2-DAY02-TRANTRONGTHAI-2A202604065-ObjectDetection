#!/usr/bin/env python3
"""Overlay YOLO detection labels on train images to self-QC annotations by eye.

Usage:
    python tools/visualize_labels.py                    # all train images -> preview/labeled/
    python tools/visualize_labels.py --images drive_003 drive_021
    python tools/visualize_labels.py --out preview/qc2 --min-class 0 --max-class 2

Draws one axis-aligned rectangle per label line, colour-coded by class, with the
class name and the box size in pixels. Writes a JPEG per image and a contact
sheet so many images can be reviewed at once.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CLASS_NAMES = {0: "car", 1: "truck", 2: "bus", 3: "van"}
CLASS_COLORS = {
    0: (255, 92, 92),
    1: (78, 121, 167),
    2: (242, 193, 78),
    3: (89, 161, 79),
}
IMG_EXTS = (".jpg", ".jpeg", ".png")


def parse_yolo(path: Path) -> list[tuple[int, float, float, float, float]]:
    """Return [(class_id, x_center, y_center, width, height)] for one label file."""
    if not path.exists():
        return []
    boxes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            raise ValueError(f"{path}: cần đúng 5 cột YOLO, thấy {len(parts)}")
        class_id = int(parts[0])
        xc, yc, w, h = map(float, parts[1:])
        boxes.append((class_id, xc, yc, w, h))
    return boxes


def load_font(size: int = 15):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_image(image_path: Path, label_path: Path, out_path: Path, font) -> int:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image)

    boxes = parse_yolo(label_path)
    for class_id, xc, yc, bw, bh in boxes:
        x1 = (xc - bw / 2) * width
        y1 = (yc - bh / 2) * height
        x2 = (xc + bw / 2) * width
        y2 = (yc + bh / 2) * height
        color = CLASS_COLORS.get(class_id, (255, 255, 255))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        name = CLASS_NAMES.get(class_id, str(class_id))
        caption = f"{name} {round(bw * width)}x{round(bh * height)}px"
        text_box = draw.textbbox((0, 0), caption, font=font)
        tw, th = text_box[2] - text_box[0], text_box[3] - text_box[1]
        ty = y1 - th - 6 if y1 - th - 6 >= 0 else y1 + 2
        draw.rectangle([x1, ty, x1 + tw + 8, ty + th + 6], fill=color)
        draw.text((x1 + 4, ty + 2), caption, fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, quality=92)
    return len(boxes)


def make_sheet(image_paths: list[Path], sheet_path: Path, cols: int = 5, tile: int = 340) -> None:
    if not image_paths:
        return
    rows = (len(image_paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + 22)), "white")
    draw = ImageDraw.Draw(sheet)
    font = load_font(13)
    for index, path in enumerate(image_paths):
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((tile, tile))
        x = (index % cols) * tile
        y = (index // cols) * (tile + 22)
        sheet.paste(thumb, (x + (tile - thumb.width) // 2, y + 22))
        draw.text((x + 6, y + 4), path.stem, fill="black", font=font)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, quality=90)


def main() -> int:
    parser = argparse.ArgumentParser(description="Vẽ nhãn YOLO lên ảnh để rà bằng mắt.")
    parser.add_argument("--images", type=Path, default=Path("dataset/images/train"))
    parser.add_argument("--labels", type=Path, default=Path("dataset/labels/train"))
    parser.add_argument("--out", type=Path, default=Path("preview/labeled"))
    parser.add_argument("--sheet", type=Path, default=Path("preview/labeled_sheet.jpg"))
    parser.add_argument("--stems", nargs="*", default=None, help="chỉ vẽ các ảnh này")
    parser.add_argument("--min-class", type=int, default=None)
    parser.add_argument("--max-class", type=int, default=None)
    args = parser.parse_args()

    image_files = sorted(p for p in args.images.glob("*") if p.suffix.lower() in IMG_EXTS)
    if args.stems:
        wanted = set(args.stems)
        image_files = [p for p in image_files if p.stem in wanted]
    if not image_files:
        print(f"Không tìm thấy ảnh trong {args.images}")
        return 1

    font = load_font(15)
    drawn = []
    for image_path in image_files:
        label_path = args.labels / f"{image_path.stem}.txt"
        if not label_path.exists():
            print(f"BỎ QUA {image_path.stem}: chưa có file nhãn")
            continue
        if args.min_class is not None or args.max_class is not None:
            classes = [box[0] for box in parse_yolo(label_path)]
            keep = [
                box for box in parse_yolo(label_path)
                if (args.min_class is None or box[0] >= args.min_class)
                and (args.max_class is None or box[0] <= args.max_class)
            ]
            if not classes or not keep:
                continue
        out_path = args.out / f"{image_path.stem}.jpg"
        count = draw_image(image_path, label_path, out_path, font)
        drawn.append(out_path)
        print(f"{image_path.stem}: {count} box -> {out_path}")

    make_sheet(drawn, args.sheet)
    print(f"\nĐã vẽ {len(drawn)} ảnh. Contact sheet: {args.sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
