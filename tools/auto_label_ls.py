#!/usr/bin/env python3
"""Auto-label cho Label Studio — chạy model detect có sẵn rồi đổ kết quả về làm pre-annotation.

Luồng:
    1. Đọc cấu hình labeling + danh sách task của project Label Studio (qua REST API).
    2. Tải ảnh của từng task, chạy YOLO (open-vocab YOLO-World hoặc YOLO COCO).
    3. Đổi box (pixel) -> vùng Label Studio (phần trăm) theo đúng tên lớp + category id.
    4. Ghi vào Label Studio dưới dạng **draft** (vùng gợi ý để bạn chỉnh) hoặc **prediction**.

Sau khi chạy xong, mở http://localhost:8081/projects/<id>/data?labeling=1,
chọn task, thấy sẵn khung -> bạn chỉnh lại rồi Submit.

Kết quả ghi vào là DRAFT/PREDICTION, KHÔNG ghi thẳng vào dataset/labels/train/.
Nhãn cuối cùng vẫn phải do bạn review và submit bằng tay (đúng quy định bài).

Ví dụ:
    python tools/auto_label_ls.py --project 2
    python tools/auto_label_ls.py --project "K5-L2-DAY02 Object Detection" --conf 0.2
    python tools/auto_label_ls.py --project 2 --mode prediction --limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import requests

REPO = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(__file__).resolve().parent / "auto_label_config.json"
TOKEN_FILE = Path(__file__).resolve().parent / ".ls_token"

DEFAULTS: dict[str, Any] = {
    "url": "http://localhost:8081",
    "model": r"E:\models\yolov8s-worldv2.pt",
    "conf": 0.25,
    "iou": 0.5,
    "imgsz": 640,
    "device": "cpu",
    "min_size_px": 24,
    "mode": "draft",
    "model_version": "autolabel-yolov8-worldv2",
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

DEFAULT_LABEL_CONFIG = """<View>
  <Image name="image" value="$image" zoom="true"/>
  <RectangleLabels name="label" toName="image">
    <Label value="car" category="0"/>
    <Label value="truck" category="1"/>
    <Label value="bus" category="2"/>
    <Label value="van" category="3"/>
  </RectangleLabels>
</View>"""


# --------------------------------------------------------------------------- #
# cấu hình & token
# --------------------------------------------------------------------------- #
def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    return cfg


def resolve_token(explicit: str | None) -> str:
    """Ưu tiên: --token > env LS_API_TOKEN > file tools/.ls_token."""
    if explicit:
        return explicit.strip()
    env = os.environ.get("LS_API_TOKEN", "").strip()
    if env:
        return env
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    raise SystemExit(
        "Chưa có API token của Label Studio.\n"
        "  - đặt biến môi trường LS_API_TOKEN, hoặc\n"
        f"  - ghi token vào file {TOKEN_FILE}, hoặc\n"
        "  - truyền --token <token>"
    )


# --------------------------------------------------------------------------- #
# Label Studio API
# --------------------------------------------------------------------------- #
class LabelStudio:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {token}"})

    def get(self, path: str, **params) -> Any:
        resp = self.session.get(f"{self.url}{path}", params=params, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, payload: dict) -> Any:
        resp = self.session.post(f"{self.url}{path}", json=payload, timeout=120)
        if resp.status_code >= 400:
            raise RuntimeError(f"POST {path} -> {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    # -- projects ----------------------------------------------------------- #
    def list_projects(self) -> list[dict]:
        return self.get("/api/projects", page_size=100).get("results", [])

    def create_project(self, title: str, label_config: str, description: str = "") -> dict:
        return self.post(
            "/api/projects",
            {"title": title, "label_config": label_config, "description": description},
        )

    def import_images(self, project_id: int, image_paths: list[Path]) -> dict:
        """Upload ảnh lên project (mỗi ảnh 1 task).

        Gán luôn `meta.stem` cho từng task (tên file không đuôi) để
        `export_ls_yolo.py` tìm được ảnh tương ứng khi export.
        """
        handles = []
        files = []
        try:
            for idx, p in enumerate(image_paths):
                fh = open(p, "rb")
                handles.append(fh)
                mime = "image/jpeg" if p.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
                files.append((f"file_{idx}", (p.name, fh, mime)))
            resp = self.session.post(
                f"{self.url}/api/projects/{project_id}/import",
                files=files,
                data={"commit_to_project": "true"},
                timeout=900,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Import lỗi: {resp.status_code} {resp.text[:500]}")
            info = resp.json()
        finally:
            for fh in handles:
                fh.close()

        # Label Studio không tự đặt meta.stem -> phải gán tay, nếu không
        # export_ls_yolo.py sẽ bỏ qua task và sinh file nhãn rỗng.
        self.tag_stems(project_id, image_paths)
        return info

    def tag_stems(self, project_id: int, image_paths: list[Path]) -> int:
        """Gán meta.stem cho các task mới import (khớp theo tên file trong data)."""
        wanted = {p.stem: p for p in image_paths}
        tagged = 0
        for task in self.project_tasks(project_id):
            meta = task.get("meta") or {}
            if meta.get("stem"):
                continue
            data = task.get("data") or {}
            url = ""
            for value in data.values():
                if isinstance(value, str) and value:
                    url = value
                    break
            stem = Path(url).stem
            # /data/upload/6/2616e233-drive_001.jpg -> "2616e233-drive_001"
            if stem not in wanted:
                for cand in wanted:
                    if stem.endswith(cand):
                        stem = cand
                        break
            if stem not in wanted:
                continue
            try:
                self.session.patch(
                    f"{self.url}/api/tasks/{task['id']}",
                    json={"meta": {**meta, "stem": stem}},
                    timeout=60,
                )
                tagged += 1
            except Exception:
                pass
        return tagged

    def resolve_project(self, ref: str | int) -> dict:
        project = self.resolve_project_optional(ref)
        if project is None:
            raise SystemExit(f"Không tìm thấy project '{ref}'. Các project hiện có:")
            for p in self.list_projects():
                print(f"  - {p['id']}: {p['title']}")
        return project

    def resolve_project_optional(self, ref: str | int) -> dict | None:
        """Trả về project theo id/title, hoặc None nếu chưa tồn tại."""
        for p in self.list_projects():
            if str(p["id"]) == str(ref) or p["title"] == str(ref):
                return self.get(f"/api/projects/{p['id']}")
        return None

    def project_tasks(self, project_id: int, page_size: int = 100) -> list[dict]:
        """Lấy toàn bộ task của project (endpoint trả về dạng list hoặc phân trang)."""
        tasks: list[dict] = []
        page = 1
        while True:
            data = self.get(
                f"/api/projects/{project_id}/tasks",
                page=page,
                page_size=page_size,
            )
            if isinstance(data, list):
                tasks.extend(data)
                break
            chunk = data.get("tasks") or data.get("results") or []
            tasks.extend(chunk)
            if not data.get("next"):
                break
            page += 1
        return tasks

    def download_image(self, url_path: str) -> bytes:
        url = url_path if url_path.startswith("http") else f"{self.url}{url_path}"
        resp = self.session.get(url, timeout=120)
        resp.raise_for_status()
        return resp.content


# --------------------------------------------------------------------------- #
# đọc labeling config
# --------------------------------------------------------------------------- #
@dataclass
class LabelSpec:
    control: str  # tên control, ví dụ "label"
    image_control: str  # tên control ảnh, ví dụ "image"
    image_key: str  # key trong task.data, ví dụ "image"
    labels: list[dict] = field(default_factory=list)  # [{value, category}]

    @property
    def names(self) -> list[str]:
        return [lb["value"] for lb in self.labels]


def parse_label_config(label_config: str) -> LabelSpec:
    """Bóc tên lớp + category id từ labeling config (RectangleLabels/Choices...)."""
    root = ET.fromstring(label_config)
    image_control, image_key = None, None
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag == "Image" and image_control is None:
            image_control = node.get("name")
            value = node.get("value") or ""
            image_key = value.lstrip("$").split(".")[0] or "image"
    if not image_control:
        raise SystemExit("Labeling config không có thẻ <Image>.")

    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag not in {"RectangleLabels", "Labels", "Choices"}:
            continue
        labels = []
        for lb in node.findall("Label"):
            labels.append({"value": lb.get("value"), "category": lb.get("category")})
        if labels:
            return LabelSpec(
                control=node.get("name"),
                image_control=image_control,
                image_key=image_key,
                labels=labels,
            )
    raise SystemExit("Không tìm thấy control nhãn (RectangleLabels/Labels/Choices) trong config.")


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
def load_model(weights: str, class_names: list[str]):
    os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(weights).parent))
    from ultralytics import YOLO

    model = YOLO(weights)
    # Model open-vocab (YOLO-World) cho phép đặt lớp tuỳ ý -> dùng đúng tên lớp
    # của project, kể cả các lớp không có trong COCO (ví dụ "van").
    if "world" in Path(weights).name.lower() or hasattr(model, "set_classes"):
        try:
            model.set_classes(class_names)
            print(f"[model] open-vocab: set_classes({class_names})")
        except Exception as exc:  # pragma: no cover
            print(f"[model] không set_classes được ({exc}), dùng lớp mặc định của model.")
    return model


def run_detection(model, image_bytes: bytes, names: list[str], args) -> list[dict]:
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    res = model.predict(
        img,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device,
        agnostic_nms=True,  # NMS không phân biệt lớp: bỏ box trùng của "car" và "van"
        verbose=False,
    )[0]

    model_names = getattr(model, "names", None) or {}
    allowed = set(names)
    out: list[dict] = []
    if res.boxes is None or len(res.boxes) == 0:
        return out
    w, h = img.size
    for cls_id, conf, xyxy in zip(
        res.boxes.cls.tolist(), res.boxes.conf.tolist(), res.boxes.xyxy.tolist()
    ):
        name = model_names.get(int(cls_id))
        if name is None and int(cls_id) < len(names):
            name = names[int(cls_id)]
        if name is None:
            continue
        # Chỉ giữ lớp có trong labeling config (model COCO hay dò thêm lớp lạ).
        if allowed and name not in allowed:
            continue
        x1, y1, x2, y2 = xyxy
        bw, bh = x2 - x1, y2 - y1
        if bw < args.min_size_px or bh < args.min_size_px:
            continue
        out.append(
            {
                "name": name,
                "conf": float(conf),
                # đổi sang phần trăm ngay từ pixel
                "x": round(max(0.0, min(x1, w)) / w * 100.0, 3),
                "y": round(max(0.0, min(y1, h)) / h * 100.0, 3),
                "width": round((min(x2, w) - max(0.0, min(x1, w))) / w * 100.0, 3),
                "height": round((min(y2, h) - max(0.0, min(y1, h))) / h * 100.0, 3),
            }
        )
    return out


def to_regions(detections: list[dict], spec: LabelSpec) -> list[dict]:
    """Đổi box pixel -> vùng Label Studio (toạ độ phần trăm 0..100)."""
    regions = []
    for det in detections:
        value: dict[str, Any] = {
            "x": det["x"],
            "y": det["y"],
            "width": det["width"],
            "height": det["height"],
            "rotation": 0,
            "rectanglelabels": [det["name"]],
        }
        # Label Studio định danh class theo TÊN nhãn (thứ tự trong labeling config),
        # nên không cần (và không nên gắn) trường category vào vùng.
        regions.append(
            {
                "id": uuid.uuid4().hex[:10],
                "type": "rectanglelabels",
                "value": value,
                "from_name": spec.control,
                "to_name": spec.image_control,
                "origin": "prediction",
                "image_rotation": 0,
                "readonly": False,
                "score": round(det["conf"], 4),
                "hidden": False,
            }
        )
    return regions


# --------------------------------------------------------------------------- #
# ghi kết quả về Label Studio
# --------------------------------------------------------------------------- #
def delete_existing_drafts(ls: LabelStudio, task_id: int, project_id: int) -> int:
    try:
        drafts = ls.get(f"/api/tasks/{task_id}/drafts")
    except Exception:
        return 0
    items = drafts.get("results", drafts) if isinstance(drafts, dict) else drafts
    removed = 0
    for d in items or []:
        try:
            ls.session.delete(f"{ls.url}/api/drafts/{d['id']}", timeout=60)
            removed += 1
        except Exception:
            pass
    return removed


def main() -> int:
    cfg = load_config()
    parser = argparse.ArgumentParser(
        description="Auto-label Label Studio bằng model detect có sẵn.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--project", required=True, help="ID hoặc tên project Label Studio")
    parser.add_argument(
        "--import-dir",
        type=Path,
        default=None,
        help="Thư mục ảnh: sẽ upload vào project trước khi auto-label",
    )
    parser.add_argument(
        "--label-config",
        type=Path,
        default=None,
        help="File labeling config dùng khi --import-dir tạo task mới",
    )
    parser.add_argument("--url", default=cfg["url"], help="Địa chỉ Label Studio")
    parser.add_argument("--token", default=None, help="API token (mặc định lấy từ env/file)")
    parser.add_argument("--model", default=cfg["model"], help="Đường dẫn weights YOLO")
    parser.add_argument("--conf", type=float, default=cfg["conf"], help="Ngưỡng confidence")
    parser.add_argument("--iou", type=float, default=cfg["iou"], help="Ngưỡng NMS IoU")
    parser.add_argument("--imgsz", type=int, default=cfg["imgsz"], help="Kích thước suy luận")
    parser.add_argument("--device", default=cfg["device"], help="cpu | cuda:0 | 0")
    parser.add_argument(
        "--min-size-px", type=int, default=cfg["min_size_px"], help="Bỏ box nhỏ hơn (px)"
    )
    parser.add_argument(
        "--mode",
        choices=["draft", "prediction", "both"],
        default=cfg["mode"],
        help="draft: gợi ý sửa trực tiếp trong UI; prediction: lưu ở tab Model",
    )
    parser.add_argument(
        "--detect-names",
        nargs="*",
        default=None,
        help="Tên lớp dùng cho model open-vocab (mặc định lấy từ labeling config)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N task đầu (0 = tất cả)")
    parser.add_argument(
        "--stems", nargs="*", default=None, help="Chỉ xử lý các ảnh có stem nằm trong danh sách"
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Không xoá draft cũ của bạn trước khi ghi (mặc định: xoá để chạy lại sạch)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ chạy model, không ghi vào LS")
    args = parser.parse_args()

    token = resolve_token(args.token)
    ls = LabelStudio(args.url, token)

    project = ls.resolve_project_optional(args.project)
    if project is None:
        if not args.import_dir:
            raise SystemExit(f"Không tìm thấy project '{args.project}'.")
        label_config = (
            args.label_config.read_text(encoding="utf-8")
            if args.label_config
            else DEFAULT_LABEL_CONFIG
        )
        project = ls.create_project(args.project, label_config, "Tạo bằng tools/auto_label_ls.py")
        print(f"[project] đã tạo mới: {project['id']}: {project['title']}")

    project_id = project["id"]
    spec = parse_label_config(project["label_config"])
    print(f"[project] {project_id}: {project['title']}")
    print(f"[config]  control='{spec.control}' -> '{spec.image_control}', lớp: {spec.names}")
    print(f"[model]   {args.model} (conf={args.conf}, iou={args.iou}, imgsz={args.imgsz})")

    if args.import_dir:
        images = sorted(
            p for p in args.import_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
        )
        if not images:
            raise SystemExit(f"Không có ảnh nào trong {args.import_dir}")
        print(f"[import]  đang upload {len(images)} ảnh vào project {project_id}...")
        info = ls.import_images(project_id, images)
        print(f"[import]  xong: {info.get('task_count')} task mới")

    tasks = ls.project_tasks(project_id)
    if args.stems:
        wanted = {s.lower() for s in args.stems}
        tasks = [
            t for t in tasks if str((t.get("meta") or {}).get("stem", "")).lower() in wanted
        ]
    if args.limit:
        tasks = tasks[: args.limit]

    # Kiểm tra toàn vẹn: số task phải khớp số ảnh định vào (nếu có import).
    n_stem = sum(1 for t in tasks if (t.get("meta") or {}).get("stem"))
    print(f"[tasks]   {len(tasks)} task sẽ xử lý ({n_stem} task có meta.stem)")
    if args.import_dir and len(tasks) < len(images):
        print(
            f"[CẢNH BÁO] project chỉ có {len(tasks)} task nhưng đã import "
            f"{len(images)} ảnh -> có thể thiếu ảnh!"
        )
    if n_stem < len(tasks):
        print(
            f"[CẢNH BÁO] {len(tasks) - n_stem} task thiếu meta.stem -> "
            f"export_ls_yolo.py sẽ không xuất được nhãn cho các task đó."
        )
    print()

    model = load_model(args.model, args.detect_names or spec.names)

    per_class: dict[str, int] = {n: 0 for n in spec.names}
    total_boxes = 0
    empty_tasks: list[str] = []
    failed: list[str] = []

    for idx, task in enumerate(tasks, 1):
        task_id = task["id"]
        stem = (task.get("meta") or {}).get("stem") or f"task{task_id}"
        data = task.get("data") or {}
        image_path = data.get(spec.image_key) or data.get("image")
        if not image_path:
            print(f"  [{idx}/{len(tasks)}] {stem}: không tìm thấy ảnh trong task.data")
            failed.append(stem)
            continue

        try:
            image_bytes = ls.download_image(image_path)
        except Exception as exc:
            print(f"  [{idx}/{len(tasks)}] {stem}: tải ảnh lỗi ({exc})")
            failed.append(stem)
            continue

        detections = run_detection(model, image_bytes, spec.names, args)
        regions = to_regions(detections, spec)
        total_boxes += len(regions)
        for r in regions:
            per_class[r["value"]["rectanglelabels"][0]] = (
                per_class.get(r["value"]["rectanglelabels"][0], 0) + 1
            )
        if not regions:
            empty_tasks.append(stem)

        if args.dry_run:
            names = [r["value"]["rectanglelabels"][0] for r in regions]
            print(f"  [{idx}/{len(tasks)}] {stem}: {len(regions)} box ({', '.join(names) or '-'}) [dry-run]")
            continue

        if args.mode in ("draft", "both"):
            if not args.keep_existing:
                delete_existing_drafts(ls, task_id, project_id)
            ls.post(f"/api/tasks/{task_id}/drafts?project={project_id}", {"result": regions})
        if args.mode in ("prediction", "both"):
            ls.post(
                "/api/predictions",
                {
                    "task": task_id,
                    "project": project_id,
                    "result": regions,
                    "model_version": cfg["model_version"],
                    "score": max([r["score"] for r in regions], default=0.0),
                },
            )

        detail = ", ".join(r["value"]["rectanglelabels"][0] for r in regions)
        print(f"  [{idx}/{len(tasks)}] {stem}: {len(regions)} box ({detail or '-'})")

    print("\n=== Tổng kết ===")
    print(f"Tổng box: {total_boxes} trên {len(tasks)} task")
    for name, count in per_class.items():
        print(f"  - {name}: {count}")
    if empty_tasks:
        print(f"Không tìm thấy phương tiện (cần xem tay): {', '.join(empty_tasks)}")
    if failed:
        print(f"Lỗi: {', '.join(failed)}")
    if not args.dry_run:
        print(f"\nMở: {args.url}/projects/{project_id}/data?labeling=1")
        print("Vào từng task, chỉnh khung cho đúng rồi bấm Submit để chốt nhãn.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
