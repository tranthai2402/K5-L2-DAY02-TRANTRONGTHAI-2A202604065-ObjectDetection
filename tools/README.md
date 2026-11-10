# Tools

Ngoài hai script gốc của đề bài (`check_yolo_labels.py`, `evaluate_annotations.py`), thư mục này có thêm các script tôi viết để hỗ trợ bước gán nhãn và tự kiểm tra.

> **Lưu ý về `auto_label_ls.py`:** đây là công cụ *gợi ý* khung (pre-annotation) bằng model detect có sẵn, nhằm giảm thời gian vẽ tay. Nhãn cuối cùng vẫn phải do tôi review và Submit trong Label Studio — đúng quy định "không nộp nhãn do AI làm thay".

## `import_labels.py` — đưa nhãn export về `dataset/labels/train/`

Chuyển nhãn do công cụ annotation xuất ra sang đúng định dạng YOLO chuẩn hoá mà bài yêu cầu (`class_id x_center y_center width height`, tọa độ trong `[0,1]`, class đứng đầu).

Script tự nhận dạng 3 biến thể export:

| Định dạng export | Ví dụ | Nguồn |
| --- | --- | --- |
| Chuẩn hoá, class ID đứng đầu | `0 0.482000 0.613500 0.153100 0.213900` | Roboflow YOLOv5/YOLOv8, Ultralytics |
| Chuẩn hoá, tên lớp đứng đầu | `car 0.482000 0.613500 0.153100 0.213900` | Roboflow (bật class names) |
| Toạ độ pixel, class ở cuối | `120 200 320 480 0` | Label Studio YOLO export |

### Cách dùng

**Roboflow** (export xong có `data.yaml` + `images/` + `labels/`):

```bash
python tools/import_labels.py --source "C:\Users\...\Downloads\export" --class-map "C:\Users\...\Downloads\export\data.yaml"
```

**Label Studio** (export ra thư mục chứa các file `.txt` toạ độ pixel):

```bash
python tools/import_labels.py --source "C:\Users\...\Downloads\ls-export" --pixel
```

Nếu Label Studio xuất kèm `classes.txt`, truyền `--classes-file <đường dẫn>` để script dùng đúng thứ tự lớp bạn đã khai báo.

Tuỳ chọn khác:

- `--dry-run`: chỉ in kết quả, không ghi file
- `--images` / `--labels`: đổi thư mục ảnh và nhãn đích (mặc định `dataset/images/train`, `dataset/labels/train`)

Script chỉ ghi file cho những ảnh có trong `dataset/images/train/`, nên nhãn thừa sẽ được báo và bỏ qua.

## `visualize_labels.py` — rà nhãn bằng mắt

Vẽ mỗi box YOLO đè lên ảnh gốc: mỗi lớp một màu, kèm tên lớp và kích thước box theo pixel. Xuất ảnh từng cái và một contact sheet để xem nhiều ảnh cùng lúc.

```bash
# vẽ cả 50 ảnh train + contact sheet
python tools/visualize_labels.py

# chỉ xem một số ảnh
python tools/visualize_labels.py --stems drive_003 drive_021 drive_050

# đổi thư mục output
python tools/visualize_labels.py --out preview/qc2 --sheet preview/qc2_sheet.jpg
```

Màu theo lớp: `car` đỏ, `truck` xanh dương, `bus` vàng, `van` xanh lá.

Script bỏ qua ảnh chưa có file nhãn và in ra thông báo tương ứng.

> Lưu ý khi chạy script có in tiếng Việt trên Windows Terminal: nếu gặp `UnicodeEncodeError`, chạy với `$env:PYTHONIOENCODING="utf-8"`.

## `auto_label_ls.py` — auto-label Label Studio bằng model detect có sẵn

Đây là tool chính của luồng "import ảnh → bật tool → chỉnh lại":

1. Đọc labeling config + danh sách task của project Label Studio (REST API).
2. Tải ảnh từng task, chạy YOLO open-vocab (`yolov8s-worldv2.pt`) với đúng tên lớp của project.
3. Đổi box pixel → vùng Label Studio (đơn vị phần trăm), ghi vào **draft** của task.

Kết quả là khung gợi ý nằm sẵn trong Label Studio: mở task thấy khung → chỉnh/xoá/thêm → bấm **Submit** để chốt nhãn.

### Khởi động Label Studio

Label Studio chạy ở **port 8081** (CVAT giữ port 8080 để tránh xung đột):

```bash
# Windows: tools\start_label_studio.bat          -> chạy nền
# Windows: tools\start_label_studio.bat --stop   -> tắt
```

Mở giao diện: <http://localhost:8081>

> **Lưu ý khi xem task trên UI:** Data Manager phân trang **15 task/trang**. Muốn thấy hết 50 ảnh thì bấm phân trang (hoặc đổi sang chế độ Grid). Project hiện tại có **50 task / 50 ảnh** — không phải thiếu.

### Cài đặt (một lần)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics requests
```

Model được tải về `E:\models\yolov8s-worldv2.pt` (đổi đường dẫn trong `tools/auto_label_config.json` nếu muốn). Vì YOLO-World là model **open-vocab**, nó nhận diện được cả lớp `van` — lớp không có trong COCO.

### Cách dùng

```bash
# auto-label project đang có (id 2)
python tools/auto_label_ls.py --project 2

# dùng launcher ngắn
python tools/auto_label.py            # project mặc định trong config
python tools/auto_label.py 5          # theo id
python tools/auto_label.py "Bài mới"   # theo tên project

# tạo project mới + import ảnh + auto-label luôn
python tools/auto_label.py --new "Bài mới" --import-dir dataset/images/train

# trên Windows: tools\auto_label.bat 2
```

> **Import luôn đủ toàn bộ ảnh.** `--import-dir` upload *tất cả* ảnh trong thư mục (không giới hạn), và tool tự gán `meta.stem` cho từng task để `export_ls_yolo.py` xuất được nhãn đúng về `dataset/labels/train/`. Tool sẽ in cảnh báo nếu số task không khớp số ảnh.

### Tuỳ chọn hay dùng

| Cờ | Ý nghĩa |
| --- | --- |
| `--project` | id hoặc tên project (bắt buộc) |
| `--import-dir` | upload ảnh từ thư mục vào project trước khi auto-label |
| `--label-config` | file labeling config dùng khi tạo project mới |
| `--conf` | ngưỡng confidence (mặc định 0.25) |
| `--iou` | ngưỡng NMS (mặc định 0.5) |
| `--min-size-px` | bỏ box nhỏ hơn ngưỡng này (mặc định 24 px) |
| `--mode` | `draft` (gợi ý sửa trực tiếp) \| `prediction` (tab Model) \| `both` |
| `--stems` | chỉ xử lý một số ảnh, ví dụ `--stems drive_003 drive_021` |
| `--limit N` | chỉ xử lý N task đầu |
| `--keep-existing` | không xoá draft cũ trước khi ghi |
| `--dry-run` | chỉ chạy model, in kết quả, không ghi vào Label Studio |

### Token

Token đọc theo thứ tự: `--token` → biến môi trường `LS_API_TOKEN` → file `tools/.ls_token`.
File `tools/.ls_token` đã được thêm vào `.gitignore` (không commit secret).

### Lưu ý chất lượng

- Model chỉ **gợi ý**: với ảnh chụp từ trên, `car`/`van` hay bị nhầm lẫn, và có thể thừa/bớt khung. Đây là lý do bước review tay là bắt buộc.
- Script **không** ghi vào `dataset/labels/train/`. Muốn xuất nhãn YOLO sau khi đã Submit trên UI thì chạy `tools/export_ls_yolo.py`.
