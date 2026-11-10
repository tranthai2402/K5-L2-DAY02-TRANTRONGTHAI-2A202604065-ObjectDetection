#!/usr/bin/env python3
"""Export Label Studio annotations -> YOLO detection .txt for dataset/labels/train.

Reads annotations straight from the Label Studio SQLite DB (no API token needed),
converts each RectangleLabels region into `class_id x_center y_center width height`
with normalized coordinates, and writes one .txt per image into dataset/labels/train/.

Usage:
    python tools/export_ls_yolo.py
    python tools/export_ls_yolo.py --project 2 --check
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

CLASS_IDS = {"car": 0, "truck": 1, "bus": 2, "van": 3}

REPO = Path(__file__).resolve().parent.parent
IMAGES_DIR = REPO / "dataset" / "images" / "train"
LABELS_DIR = REPO / "dataset" / "labels" / "train"
DB = Path(os.environ.get(
    "LS_DB",
    r"C:\Users\Lenovo\AppData\Local\label-studio\label-studio\label_studio.sqlite3",
))


def load_tasks(conn: sqlite3.Connection, project_id: int) -> list[tuple[int, str, str]]:
    """Return (task_id, stem, result_json) for every task in the project.

    `meta.stem` là nguồn chuẩn, nhưng task import qua API có thể thiếu ->
    fallback suy ra stem từ đường dẫn ảnh trong `task.data` (vd
    "/data/upload/6/2616e233-drive_001.jpg" -> "drive_001").
    """
    rows = conn.execute(
        "SELECT t.id, t.meta, t.data, tc.result FROM task t "
        "LEFT JOIN task_completion tc ON tc.id = ("
        "  SELECT id FROM task_completion c2 "
        "  WHERE c2.task_id = t.id AND c2.was_cancelled = 0 "
        "  ORDER BY c2.id DESC LIMIT 1"
        ") "
        "WHERE t.project_id = ?",
        (project_id,),
    ).fetchall()

    tasks = []
    for task_id, meta_json, data_json, result_json in rows:
        stem = None
        if meta_json:
            import json
            try:
                stem = json.loads(meta_json).get("stem")
            except Exception:
                stem = None
        if not stem and data_json:
            import json
            try:
                data = json.loads(data_json)
            except Exception:
                data = {}
            for value in (data or {}).values():
                if isinstance(value, str) and value:
                    name = os.path.basename(value)
                    stem = os.path.splitext(name)[0]
                    # bỏ tiền tố hash do Label Studio thêm: "2616e233-drive_001"
                    if "-" in stem:
                        stem = stem.split("-", 1)[1]
                    break
        tasks.append((task_id, stem, result_json))
    return tasks


def parse_result(result_json: str | None) -> list[dict]:
    if not result_json:
        return []
    import json
    try:
        payload = json.loads(result_json)
    except Exception:
        return []
    if isinstance(payload, dict):
        payload = payload.get("result", [])
    return payload or []


def regions_to_yolo(regions: list[dict]) -> list[tuple[int, float, float, float, float]]:
    boxes = []
    for region in regions:
        if region.get("type") != "rectanglelabels":
            continue
        # Toạ độ nằm trong region["value"], không phải ở top-level.
        value = region.get("value") or {}
        labels = value.get("rectanglelabels") or region.get("rectanglelabels") or []
        if isinstance(labels, str):
            labels = [labels]
        if not labels:
            continue
        name = labels[0]
        if name not in CLASS_IDS:
            continue
        try:
            x = float(value["x"])
            y = float(value["y"])
            w = float(value["width"])
            h = float(value["height"])
        except (KeyError, TypeError, ValueError):
            continue
        # Label Studio stores percentages of the image size
        x_center = (x + w / 2) / 100.0
        y_center = (y + h / 2) / 100.0
        width = w / 100.0
        height = h / 100.0
        x_center = min(max(x_center, 0.0), 1.0)
        y_center = min(max(y_center, 0.0), 1.0)
        width = min(max(width, 0.0), 1.0)
        height = min(max(height, 0.0), 1.0)
        if width <= 0 or height <= 0:
            continue
        boxes.append((CLASS_IDS[name], x_center, y_center, width, height))
    return boxes


def main() -> int:
    parser = argparse.ArgumentParser(description="Export nhãn Label Studio ra YOLO detection.")
    parser.add_argument("--project", type=int, default=2, help="Label Studio project id")
    parser.add_argument("--images", type=Path, default=IMAGES_DIR)
    parser.add_argument("--labels", type=Path, default=LABELS_DIR)
    parser.add_argument("--check", action="store_true", help="chỉ in, không ghi file")
    args = parser.parse_args()

    if not DB.exists():
        print(f"Không tìm thấy database: {DB}")
        return 1

    conn = sqlite3.connect(DB)
    tasks = load_tasks(conn, args.project)
    print(f"Project {args.project}: {len(tasks)} task")

    labeled = 0
    total_boxes = 0
    written = 0
    for task_id, stem, result_json in tasks:
        if stem is None:
            print(f"  task {task_id}: thiếu stem trong meta, bỏ qua")
            continue
        regions = parse_result(result_json)
        boxes = regions_to_yolo(regions)
        if boxes:
            labeled += 1
            total_boxes += len(boxes)
        else:
            print(f"  {stem}: chưa có nhãn")
        lines = [f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}" for cid, xc, yc, w, h in boxes]
        if args.check:
            print(f"  {stem}: {len(boxes)} box")
            continue
        args.labels.mkdir(parents=True, exist_ok=True)
        target = args.labels / f"{stem}.txt"
        target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        written += 1

    print(f"\nTask đã gán nhãn: {labeled}/{len(tasks)}")
    print(f"Tổng số box: {total_boxes}")
    if not args.check:
        print(f"Đã ghi {written} file vào {args.labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())