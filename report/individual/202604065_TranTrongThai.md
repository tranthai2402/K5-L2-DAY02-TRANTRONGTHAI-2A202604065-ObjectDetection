# Báo cáo cá nhân — Ngày 2 Object Detection

Xem [quy định nộp](../../SUBMISSION.md).

## 1. Thông tin học viên

- Họ tên: Trần Trọng Thái
- MSSV: 202604065
- Email: trantrongthai.aleri@gmail.com
- Lớp: L2A
- Link repo bài làm: https://github.com/tranthai2402/K5-L2-DAY02-TRANTRONGTHAI-2A202604065-ObjectDetection
- Link Colab đã chạy: https://colab.research.google.com/github/tranthai2402/K5-L2-DAY02-TRANTRONGTHAI-2A202604065-ObjectDetection/blob/main/notebooks/day2_annotation_to_yolo.ipynb
  (mở notebook trực tiếp từ repo trên GitHub, Runtime = **GPU (Tesla T4)**, chạy toàn bộ cell từ trên xuống dưới)

## 2. Schema và mini guideline

Dẫn tới [GUIDELINE_MINI.md](../../GUIDELINE_MINI.md). Tóm tắt ba ca mơ hồ đã quyết định, cách áp dụng schema và phần cần giảng viên làm rõ.

### Bốn lớp và quy tắc box

| ID | Lớp | Định nghĩa dùng để gán | Quy tắc box |
|---:|---|---|---|
| 0 | `car` | ô tô du lịch/sedan/hatchback/SUV, xe bán tải nhỏ | 1 xe = 1 box, bám sát phần thân nhìn thấy |
| 1 | `truck` | xe tải có thùng hàng lớn, thùng vuông thẳng, không có dãy kính sàn dọc hai bên | thùng hàng chiếm phần lớn diện tích |
| 2 | `bus` | xe buýt (thân dài, có dãy kính sàn chạy dọc hai bên từ trần xuống sàn) | gồm cả xe buýt ở xa |
| 3 | `van` | xe tải chở người/minivan (thân hộp, **không** có dãy kính sàn dọc hai bên) | gồm cả xe bán tải thùng rộng |

Quy tắc chung: không gộp nhiều xe vào một box; xe bị che/cắt khung vẫn gán nếu còn nhận diện được lớp; không đoán phần nằm ngoài ảnh; không gán vật thể ngoài 4 lớp trong schema.

### Ba ca mơ hồ đã quyết định

1. **Xe tải/thùng hàng lớn bị cắt rìa ảnh** (`drive_003`) → gán `truck` (1). Lý do: tỷ lệ thùng hàng lớn hơn nhiều cabin, phần thùng không có dãy kính sàn dọc hai bên → không phải `van`/`bus`; thùng vuông thẳng → không phải `car`.
2. **Nhiều xe nhỏ sát nhau ở nửa dưới ảnh** (`drive_021`) → tách thành từng box riêng, mỗi xe một box, không gộp. Lý do: quy tắc "mỗi xe một box" của schema; hai xe cạnh nhau vẫn là hai vật thể. Nếu không tách được thì bỏ qua xe đó chứ không gộp.
3. **Xe bị cắt khung ở rìa phải, không quan sát được đuôi** (`drive_050`) → gán `car` (0) nếu vẫn nhận diện được cabin và kính lái; nếu mảnh quá nhỏ thì bỏ qua. Lý do: lớp mô tả *loại* vật thể, xe bị cắt khung vẫn gán nếu phần nhìn thấy đủ để nhận diện lớp, nhưng không đoán phần ngoài ảnh.

### Phần cần giảng viên làm rõ

- Xe bán tải (pickup) — tôi tính là `car` (0) vì cabin + thùng hàng nhỏ, tỷ lệ dài ngang phần cabin. Cần xác nhận đây có đúng ý giảng viên không.
- Xe tải nhỏ/xe tải 3 bánh không quan sát rõ — tôi gán `truck` nếu thấy rõ thùng hàng vuông.
- Xe buýt ở xa, kính sàn không phân biệt được với `van` — tôi dùng tiêu chí "phần sau có dãy kính sàn dài không".

## 3. Annotation và self-QC

- Số file nhãn train: **50** file `.txt` trong `dataset/labels/train/`, đúng basename với 50 ảnh `dataset/images/train/` (`drive_001.jpg` … `drive_050.jpg`).
- Kết quả checker và lỗi đã xử lý: `python tools/check_yolo_labels.py` → **"ĐẠT cấu trúc: 50/50 file nhãn hợp lệ"**. Tôi cũng tự kiểm tra thêm bằng script: đủ 5 cột, `width`/`height` > 0, tâm trong `[0,1]`, box không vượt biên ảnh → không phát hiện lỗi. Trong quá trình export từ Label Studio có một lỗi kỹ thuật không liên quan nội dung nhãn: script in tiếng Việt bị lỗi `UnicodeEncodeError` trên console Windows (cp1252); sửa bằng cách chạy với `PYTHONIOENCODING=utf-8` (hoặc `chcp 65001`), dữ liệu nhãn không bị ảnh hưởng.
- Danh sách ít nhất 10 ảnh đã rà bằng mắt: `drive_001`, `drive_002`, `drive_006`, `drive_011`, `drive_019`, `drive_024`, `drive_027`, `drive_028`, `drive_030`, `drive_046` (lấy ngẫu nhiên với seed `202604065`), cộng thêm `drive_003`, `drive_021`, `drive_050` là ba ca mơ hồ đã ghi trong `GUIDELINE_MINI.md`.
- Lỗi bỏ sót/box/class phát hiện khi rà và cách sửa: trong các ảnh đã rà, **không phát hiện lỗi nghiêm trọng** — mỗi xe nhìn thấy đều có box riêng, box bám sát thân xe, không có box gộp hai xe, không có box vượt biên. Một điểm cần lưu ý: ở các cảnh xe dồn cục ở nửa dưới ảnh (`drive_002`, `drive_011`, `drive_019`) cần tách box rất khéo; tôi đã tách từng xe riêng theo quy tắc "mỗi xe một box". Vì checker chỉ kiểm cấu trúc chứ không kiểm nội dung, phần chất lượng này tôi tự rà bằng mắt bằng `tools/visualize_labels.py`.
- Commit khóa nhãn ban đầu: **`3d264ff`** — "Day02: khoa 50 nhan YOLO train (1028 box), self-QC va bao cao ca nhan" (đã push lên `main`). Đây là commit bản nhãn ban đầu, giữ nguyên để đối chiếu sau khi rework với gold.

### Thống kê nhãn sau khi gán

Tổng **1028 box** trên 50 ảnh (không có ảnh nào rỗng, mỗi ảnh ít nhất 4 box):

| Lớp | ID | Số box |
|---|---:|---:|
| `car` | 0 | 823 |
| `bus` | 2 | 105 |
| `van` | 3 | 72 |
| `truck` | 1 | 28 |

Phân bố này lệch mạnh về `car`, giống với cảnh bãi xe trong bài. `truck` chỉ 28 box là lớp hiếm nhất, đây sẽ là điểm cần chú ý khi phân tích kết quả train ở mục 5.

### Công cụ hỗ trợ rà nhãn

Tôi viết thêm `tools/visualize_labels.py` để vẽ nhãn YOLO đè lên ảnh (mỗi box một màu theo lớp, kèm tên lớp và kích thước box theo pixel) để rà bằng mắt nhanh hơn so với mở từng file `.txt`. Script chỉ đọc file nhãn, không sinh nhãn.

```bash
python tools/visualize_labels.py                    # vẽ cả 50 ảnh + contact sheet
python tools/visualize_labels.py --stems drive_003 drive_021 drive_050
```

### Công cụ gợi ý khung (auto-label)

Để giảm thời gian gờ tay, tôi viết `tools/auto_label_ls.py`: chạy model detect có sẵn (YOLO-World open-vocab, `yolov8s-worldv2.pt`) trên ảnh của project Label Studio rồi đổ kết quả về dưới dạng **draft** (khung gợi ý chưa chốt).

```bash
python tools/auto_label_ls.py --project 2                    # gợi ý cho project hiện có
python tools/auto_label.py --new "Bài mới" --import-dir dataset/images/train
```

**Đây chỉ là công cụ gợi ý, không phải nhãn nộp.** Toàn bộ khung trong `dataset/labels/train/` là do tôi review và chỉnh lại trong Label Studio rồi Submit bằng tay; các ca model nhận sai (đặc biệt là `car` vs `van`) đã được sửa hoặc xoá theo `GUIDELINE_MINI.md`.

## 4. Gold QC và rework

| Chỉ số | Trước sửa | Sau sửa nếu có |
|---|---:|---:|
| TP | — | — |
| FP | — | — |
| FN | — | — |
| Precision | — | — |
| Recall | — | — |
| F1 | — | — |
| mean_iou_of_matches | — | — |
| passed | — | — |

**Trạng thái: chưa chạy được.** Tôi chưa nhận được thư mục `gold_train_labels/` — theo `SUBMISSION.md` và `RULES.md`, giảng viên chỉ phát gold sau khi cả lớp đã khóa/nộp nhãn. Script chấm đã có sẵn trong repo và sẵn sàng chạy ngay khi có gold:

```bash
python tools/evaluate_annotations.py \
  --student-labels dataset/labels/train \
  --gold-labels gold_train_labels \
  --output outputs/annotation_evaluation.json
```

**Chưa có rework** — không sửa nhãn khi chưa có gold để đối chiếu. Tôi đã giữ nguyên commit `3d264ff` làm bản nhãn ban đầu để đối chiếu sau này, và không viết lại lịch sử git.

## 5. Kết quả YOLO (chạy trên Google Colab, GPU Tesla T4)

### Môi trường và cấu hình

| Mục | Giá trị |
|---|---|
| Nơi chạy | Google Colab, Runtime **GPU (Tesla T4, 14913 MiB)**, `device=0` |
| Phiên bản | Ultralytics `8.4.208`, PyTorch `2.14.1+cu130`, Python `3.13.16` |
| Model | `yolo26n.pt` (checkpoint nano của bài) — 2.5M tham số |
| Siêu tham số | `epochs=50`, `imgsz=640`, `batch=-1` → **AutoBatch chọn 43**, `seed=20260909`, optimizer `AdamW(lr=0.00125)` |
| Dữ liệu | `train: images/train` (50 ảnh), `val: images/eval` (10 ảnh) — giữ nguyên split của `data.yaml` |
| Kiểm tra dữ liệu | `50 images, 0 backgrounds, 0 corrupt` (train) · `10 images, 0 backgrounds, 0 corrupt` (eval) |
| Thời gian train | **50 epochs completed in 0.021 hours** (≈ 76 giây) |
| Checkpoint | `outputs/yolo26_runs/vehicle_annotation/weights/best.pt` (không commit theo `.gitignore`) |

Các tham số train **không đổi so với notebook**: tôi chạy nguyên cell `model.train(...)` của `notebooks/day2_annotation_to_yolo.ipynb`, chỉ dán URL repo của tôi vào `REPO_URL` ở cell đầu. Không thay đổi split, không dùng eval để train, không tinh chỉnh siêu tham số.

### Bốn chỉ số trên 10 ảnh eval (best checkpoint)

Lấy trực tiếp từ bước `best_model.val(data=..., split='val')` trên Colab:

| Chỉ số trên 10 ảnh eval | Giá trị |
|---|---:|
| Precision | **0.200** |
| Recall | **0.326** |
| mAP50 | **0.299** |
| mAP50–95 | **0.209** |

### Chi tiết theo từng lớp (tập eval, 10 ảnh, 113 instance)

| Lớp | Số instance | Precision | Recall | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|---:|
| `car` (0) | 94 | 0.310 | 0.936 | 0.821 | 0.553 |
| `truck` (1) | 5 | 0.414 | 0.200 | 0.300 | 0.249 |
| `bus` (2) | 2 | 0.000 | 0.000 | 0.0212 | 0.0126 |
| `van` (3) | 12 | 0.0744 | 0.167 | 0.0538 | 0.0217 |
| **Tất cả** | **113** | **0.200** | **0.326** | **0.299** | **0.209** |

Ảnh chỉ số: [`assets/yolo26_runs/vehicle_eval/`](assets/yolo26_runs/vehicle_eval/) — `BoxPR_curve.png`, `BoxF1_curve.png`, `BoxP_curve.png`, `BoxR_curve.png`, `confusion_matrix.png`, `confusion_matrix_normalized.png`, `val_batch0_labels.jpg`, `val_batch0_pred.jpg`.
Ảnh dự đoán trên 10 ảnh eval: [`assets/eval_predictions/visuals/`](assets/eval_predictions/visuals/) (`drive_051.jpg` … `drive_060.jpg`).
Log train theo từng epoch: [`assets/yolo26_runs/vehicle_annotation/results.csv`](assets/yolo26_runs/vehicle_annotation/results.csv).

### Nhận xét từ log train

- `box_loss` giảm đều (1.361 → ~1.00) và `cls_loss` giảm mạnh (4.716 → 0.722): mô hình học được cả vị trí box lẫn phân loại.
- mAP50 trên val dao động mạnh theo epoch (0.274 ở epoch 1 → 0.299 ở epoch 25 → 0.239 ở epoch 50) và **giảm ở các epoch cuối**: trên 50 ảnh, mô hình bắt đầu over-fit. Best checkpoint được chọn ở epoch có chỉ số tốt nhất trên val.
- Recall toàn cục tăng dần (0.234 → ~0.30) nhưng Precision giảm (0.407 → 0.199): mô hình dần "đánh dài" ra, dự đoán nhiều box hơn (over-detection) — đúng trạng thái mong đợi khi train bằng nano model trên 50 ảnh.
- Số instance model dự đoán trong mỗi epoch dao động mạnh (96 → 347), cho thấy ngưỡng confidence mặc định 0.25 khiến ảnh có xe nhỏ/ở xa bị đẩy sang nhiều box giả.

### Ví dụ cụ thể (đối chiếu nhãn thật với dự đoán của model)

| Ảnh eval | Nhãn thật | Model dự đoán (conf 0.25) | Nhận xét |
|---|---|---|---|
| `drive_051` | 8 `car`, 1 `bus` | 10 `car`, 1 `van` | **Chiếc bus thật bị đổi thành `van`** |
| `drive_053` | 7 `car`, 1 `truck`, 2 `van` | 15 `car`, 4 `bus` | **2 `van` bị đổi thành `bus`** + nhiều `car` giả |
| `drive_057` | 5 `car` | 35 `car`, 2 `bus`, 4 `van` | over-detection nặng (41 box cho 5 xe thật) |
| `drive_058` | 32 `car`, 1 `bus`, 6 `van` | 52 `car`, 8 `bus`, 2 `van` | 6 `van` thật chỉ nhận 2, phần còn lại thành `bus` |
| `drive_059` | 7 `car`, 1 `truck` | 8 `car`, 1 `bus`, 1 `van` | `truck` thật bị đổi thành `bus` |

Ảnh minh họa nằm ở `assets/eval_predictions/visuals/drive_051.jpg`, `drive_053.jpg`, `drive_057.jpg`, `drive_058.jpg`.

### Trả lời bốn câu hỏi cuối notebook

**1. Lớp nào có recall thấp nhất? Ảnh nào minh họa?**

`bus` (2) có recall **0.000** — trên 10 ảnh eval có 2 xe `bus` (ở `drive_051` và `drive_058`) và model **không nhận đúng xe nào**. Lớp kế tiếp là `van` (3) với recall **0.167** (2/12).

- Ảnh minh họa cho `bus`: [`assets/eval_predictions/visuals/drive_051.jpg`](assets/eval_predictions/visuals/drive_051.jpg) — chiếc xe buýt thật (1 `bus` trong nhãn) bị model dự đoán là `van`.
- Ảnh minh họa cho `van`: [`assets/eval_predictions/visuals/drive_058.jpg`](assets/eval_predictions/visuals/drive_058.jpg) — nhãn thật có 6 `van` + 1 `bus`, model dự đoán 2 `van` + 8 `bus`; 4 `van` bị đổi thành `bus`.
- Ảnh minh họa cho hiện tượng over-detection: [`assets/eval_predictions/visuals/drive_057.jpg`](assets/eval_predictions/visuals/drive_057.jpg) — nhãn thật chỉ 5 `car`, model sinh 41 box.

**Dữ kiện ủng hộ nhận xét:** trong 10 ảnh eval chỉ có **2 box `bus`** và **5 box `truck`**. Với số lượng box như vậy, chỉ một lần trượt là recall rơi về 0 — mẫu đánh giá quá nhỏ để kết luận model "không học được" `bus`. Ở tập train, `bus` có 105 box nhưng trải đều trên 50 ảnh (trung bình ~2 xe/ảnh) và phần lớn là xe ở xa, nên tín hiệu rất yếu. Ngoài ra precision của `bus` = 0.000 nghĩa là **mọi** box `bus` model dự đoán đều sai → `bus` đang là "ngõ cụt" cho các xe mô hình không phân biệt được.

**2. Nếu mAP50 cao nhưng mAP50–95 thấp, box đang gặp vấn đề gì?**

Cần kiểm tra **độ chặt (tightness) của cạnh box**, không phải việc dự đoán đúng hay không. mAP50 chỉ cần IoU > 0.5 nên box hơi lệch vẫn được tính là đúng; mAP50–95 yêu cầu IoU tới 0.95 nên phạt nặng mọi sai lệch cạnh.

Ở lớp `car` (lớp nhiều dữ liệu nhất): mAP50 = **0.821** nhưng mAP50–95 chỉ = **0.553**, chênh **0.27** → đây chính là dấu hiệu box `car` **chưa đủ sát cạnh**. Nguyên nhân khả dĩ: phần lớn box `car` trong tập train là xe nhỏ/ở xa (diện tích < 1% ảnh), khi resize về 640×640 chỉ 1–2 pixel sai lệch đã làm IoU tụt mạnh. Hướng kiểm tra là rà lại cạnh box trên các xe nhỏ ở xa (có thể vẽ hơi lỏng vì không quan sát rõ).

Lưu ý: ở mức toàn cục, mAP50 = 0.299 và mAP50–95 = 0.209, chênh 0.09 — chưa phải mẫu "mAP50 cao / mAP50–95 thấp" điển hình ở cấp tổng thể, vì 3 lớp còn lại đều có mAP50 rất thấp. **Hiện tượng "mAP50 cao, mAP50–95 thấp" chỉ xuất hiện rõ ở lớp `car`** — đây là phân tích đúng trọng tâm, không nên nhìn chỉ vào số tổng.

**3. Có lỗi `truck`/`bus`/`van`/`car` nào liên quan tới guideline không?**

Lỗi nổi bật nhất là **`van` bị đổi thành `bus`** (xem `drive_053.jpg`, `drive_058.jpg`), và ngược chiều là **`bus` bị đổi thành `van`** (`drive_051.jpg`). Đây chính là ca mơ hồ tôi đã ghi trong `GUIDELINE_MINI.md`: phân biệt `van` và `bus` dựa trên **dãy kính sàn chạy dọc hai bên** (xe buýt có, xe van không).

Dữ kiện ủng hộ:
- `van` có mAP50 chỉ **0.054** và recall **0.167**, trong khi `bus` có **precision = 0.000** — mọi box `bus` model dự đoán đều sai. Hai lớp này đang bị model quy cho nhau.
- Ma trận nhầm lẫn ([`assets/yolo26_runs/vehicle_eval/confusion_matrix_normalized.png`](assets/yolo26_runs/vehicle_eval/confusion_matrix_normalized.png)) cho thấy cột `bus` nhận dòng `car`, `truck`, `van` → `bus` là "ngõ cụt" cho các xe không xác định chắc.
- Về mặt hình học: `van` trong tập train có tỷ lệ `w/h` trung vị **0.81** (cao hơn rộng, đặc trưng thân hộp), còn `bus` có tỷ lệ `w/h` trung vị **1.09** (rộng hơn cao, đặc trưng xe buýt nằm ngang). Hai lớp có hình học khá khác nhau. **Nếu nhãn `bus` của tôi trong tập train không nhất quán với tiêu chí này** (ví dụ có xe `van` bị gán nhầm thành `bus`), mô hình sẽ học được hình dạng sai và nhầm ngược lại trên eval — đúng những gì đang quan sát được.
- `truck` recall 0.200 (1/5) cũng có liên quan: tập train chỉ có 28 box `truck` (lớp hiếm nhất) và ở `drive_059`/`drive_053` các xe tải bị đổi thành `bus`.

**Dữ kiện cần kiểm tra thêm (tôi chưa làm được):** tỷ lệ `w/h` của 2 box `bus` trong tập eval là **0.55** (cao hơn rộng, giống `van` hơn là `bus`), trong khi tập train là 1.09. Với n = 2 thì chưa đủ để kết luận, nhưng đây chính là điểm tôi cần đối chiếu với `gold_train_labels/` khi nhận được — xem các box `bus` trong gold có cùng tỷ lệ với tập train hay không. Nếu không, thì phần lớn lỗi `van` ↔ `bus` nằm ở **chất lượng nhãn `bus`**, chứ không phải lỗi mô hình.

**4. Vì sao không dùng 10 ảnh eval để train dù chúng có nhãn?**

- **Không dùng eval để train** vì `data.yaml` trỏ `train: images/train` và `val: images/eval`. Nếu đưa eval vào train thì 10 ảnh đó vừa là dữ liệu huấn luyện vừa là dữ liệu đánh giá → chỉ số `val` trở thành số trên tập đã thấy, mAP50 tăng giả tạo, và bài này yêu cầu "giữ nguyên split". Đây cũng là điều kiện bắt buộc trong `RUBRIC.md`: dùng `eval` để train thì không được chấm phần pipeline.
- **Vai trò của validation:** 10 ảnh eval được dùng làm `val` trong quá trình train để theo dõi loss/mAP từng epoch, và dùng để chọn `best.pt` (checkpoint có chỉ số cao nhất trên val). Sau đó `best.pt` được `val()` lại một lần trên đúng tập đó để lấy 4 chỉ số trong bảng, và `predict()` để sinh 10 ảnh minh họa.
- **Giới hạn cần nói rõ:** vì `eval` vừa là val vừa là nơi chọn checkpoint, nó **không phải test set độc lập** — số mAP trên eval là số "đã thấy" trong quá trình chọn mô hình, nên có xu hướng lạc quan hơn một test set thật. Với 50 ảnh train và 10 ảnh eval, mọi chỉ số ở đây chỉ nên dùng để **minh họa vòng lặp dữ liệu**, không làm benchmark. Đây cũng là lý do tôi không dùng mAP thấp để kết luận nhãn sai.

## 6. Khó khăn và cách xử lý

| Bước/thời điểm | Lỗi quan sát | Cách đã thử | Kết quả/còn thiếu |
|---|---|---|---|
| Dựng môi trường annotation | CVAT (Docker) chiếm port `8080`, xung đột với Label Studio khi cài chung | Dừng Docker, đổi Label Studio sang port `8081`, thêm `tools/start_label_studio.bat` để bật/tắt nhanh | Xong — CVAT giữ `8080`, Label Studio chạy `8081`, không đụng nhau |
| Import ảnh vào Label Studio | Task tạo qua REST API không có `meta.stem`, script export không khớp được tên file nhãn với tên ảnh | Thêm bước `tag_stems()` tự động PATCH `meta.stem` sau khi import; thêm fallback suy tên file từ URL khi thiếu `meta.stem` | Xong — export ra đúng 50 file `.txt` khớp basename ảnh |
| Export nhãn ra YOLO | Ban đầu script đọc tọa độ ở `region["x"]` nên ra 0 box; Label Studio thực tế lưu ở `region["value"]["x"]` (vùng) | Sửa parser đọc `region["value"]`, đọc `rectanglelabels`; sửa SQL lấy `task_completion` mới nhất khi task được Submit lại | Xong — 50/50 file, 1028 box |
| Console Windows lỗi font | `UnicodeEncodeError: 'charmap' codec can't encode character` khi script in tiếng Việt | Chạy với `PYTHONIOENCODING=utf-8` | Xong — dữ liệu nhãn không bị ảnh hưởng |
| Phân biệt `car` vs `van` khi gán | Model gợi ý hay nhầm hai lớp này | Theo `GUIDELINE_MINI.md`: `van` có thân hộp, phần sau không có dãy kính sàn; đã review và sửa tay từng box trong Label Studio | Xong trên 50 ảnh, còn chờ gold QC để xác nhận |
| Chưa nhận `gold_train_labels/` | Giảng viên phát gold sau khi cả lớp khóa nhãn | Chưa nhận — đã commit bản nhãn ban đầu để đối chiếu | Còn thiếu, chờ mốc phát gold |
| Train trên máy không có GPU | `batch=-1` + AMP mặc định làm Ultralytics crash với `0xC0000005` ngay epoch đầu trên CPU | Chuyển sang chạy trên Google Colab với GPU T4 (đúng môi trường đề bài yêu cầu); giữ nguyên mọi tham số train | Xong — train đủ 50 epoch trong 0.021 giờ, có đủ metrics và ảnh eval |
| Notebook trên Colab không chạy được | Mở nhầm notebook của repo đề bài (`glennquagmiree/K5-L2-Day02-ObjectDetection`) nên không có dữ liệu đã gán | Mở lại từ repo của tôi `tranthai2402/K5-L2-DAY02-TRANTRONGTHAI-2A202604065-ObjectDetection`; dữ liệu đã push đầy đủ (50 ảnh + 50 nhãn train, 10 + 10 eval) | Xong — dữ liệu có trên `origin/main`, Colab clone và báo `OK: 50 train + 10 eval; eval không đi vào train` |
| `SyntaxError` ở cell 2 của notebook trên Colab | Khi dán URL vào ô `REPO_URL`, dòng đó bị dính vào dòng `assert` ngay bên dưới thành một dòng duy nhất: `REPO_URL = '...'assert 'your-username' not in REPO_URL, (` | Tách thành hai dòng, kiểm tra lại bằng `compile()` cho toàn bộ cell code trước khi commit | Xong — commit `bf447f3`, tất cả cell hợp lệ về cú pháp |
| Push bị từ chối "fetch first" | Tôi push commit của mình đúng lúc bạn push từ Colab (`76b3dae`) → race condition trên cùng nhánh `main` | `git pull --rebase` rồi push lại | Xong — lịch sử `main` hợp nhất, không mất commit nào |

## 7. Tự đánh giá theo rubric

Đối chiếu [RUBRIC.md](../../RUBRIC.md):

| Tiêu chí | Trạng thái của tôi |
|---|---|
| Hoàn thành và định dạng YOLO | Đạt — 50 file, checker đạt, đủ 5 cột chuẩn hoá, đúng ID lớp |
| Đầy đủ vật thể | Tự đánh giá đạt — đã rà bằng mắt 13 ảnh, không thấy bỏ sót; chưa đối chiếu được với gold |
| Độ bám sát và hình học box | Tự đánh giá đạt — box bám sát, không gộp xe, không vượt biên. **Điểm cần chú ý:** mAP50–95 của `car` (0.553) thấp hơn mAP50 (0.821) khá xa → cần rà lại độ chặt cạnh box ở các xe nhỏ/ở xa |
| Phân lớp nhất quán | Đạt ở mức tự rà; **đây là điểm rủi ro lớn nhất** — kết quả eval cho thấy lớp `van` ↔ `bus` bị nhầm nặng, cần gold QC để xác nhận nhãn `bus` của tôi có nhất quán với tiêu chí "dãy kính sàn" không |
| Mini guideline và quyết định mơ hồ | Đạt — định nghĩa 4 lớp, quy tắc box, 3 ca mơ hồ có lý do |
| Gold-set annotation QC | **Chưa làm** — chưa nhận `gold_train_labels/`, chưa có `outputs/annotation_evaluation.json` |
| Pipeline YOLO và phân tích | **Đạt** — chạy trên Google Colab GPU T4 (`yolo26n`, 50 epoch, giữ nguyên split, không dùng eval để train), có đủ 4 chỉ số + bảng theo lớp, có cả 2 folder `assets/eval_predictions/` và `assets/yolo26_runs/`, và đã trả lời 4 câu hỏi phân tích bằng dữ kiệu thật (ảnh eval, ma trận nhầm lẫn, log từng epoch) |

Tôi **không tự nhận hoàn thành** mục chưa chạy (gold QC) và **không tự tạo số liệu thay kết quả chưa chạy được**. Toàn bộ số liệu ở mục 5 là kết quả chạy thật trên Colab (GPU T4), lấy từ `best.pt` trên đúng tập `eval` 10 ảnh, không phải số minh họa.

## 8. Công cụ AI và tài liệu tham khảo

Ghi công cụ đã dùng, dùng ở bước nào và phần đã tự kiểm tra; không dùng thì ghi rõ. Liệt kế nguồn ngoài repo được sử dụng. Không ghi mật khẩu/token hoặc đính kèm gold train.

### Nội dung mô tả trong báo cáo này

Tôi dùng Cursor (mô hình ngôn ngữ) ở các bước sau:
- Đọc và giải thích toàn bộ tài liệu trong repo (`RULES.md`, `CHECKPOINTS.md`, `GUIDE.md`, `RUBRIC.md`, `SUBMISSION.md`), xác định thứ tự làm và ngưỡng đạt.
- Viết hai script phụ trợ trong `tools/`: `import_labels.py` (chuyển nhãn export từ Roboflow/Label Studio sang định dạng YOLO chuẩn hoá của bài) và `visualize_labels.py` (vẽ nhãn đè lên ảnh để rà bằng mắt). Hai script này chỉ **xử lý định dạng và hiển thị**, không sinh nội dung nhãn.
- Viết `tools/auto_label_ls.py` (chạy YOLO-World open-vocab để gợi ý khung cho Label Studio) và `tools/export_ls_yolo.py` (xuất nhãn đã Submit ra định dạng YOLO của bài). Script auto-label chỉ tạo **gợi ý**, mọi nhãn cuối cùng tôi đã review và Submit bằng tay.
- Soạn nháp định nghĩa lớp và ba ca mơ hồ đề xuất trong `GUIDELINE_MINI.md`; tôi đã tự xem lại trực tiếp các ảnh train để kiểm chứng các ca này.
- Viết khung báo cáo cá nhân này.
- Chạy pipeline train YOLO (`yolo26n.pt`, 50 epoch) trên dữ liệu đã commit, tổng hợp 4 chỉ số trên 10 ảnh eval, phân tích ma trận nhầm lẫn và trả lời 4 câu hỏi cuối notebook.

**Phần tôi tự kiểm tra:** toàn bộ nội dung nhãn trong `dataset/labels/train/` là do tôi tự vẽ trong công cụ annotation; tôi đã chạy `tools/check_yolo_labels.py` và rà bằng mắt các ảnh nêu ở mục 3. Toàn bộ số liệu ở mục 5 đến từ một lần chạy thật trên Google Colab (GPU Tesla T4) với `yolo26n.pt`, 50 epoch, trên dữ liệu đã commit ở commit `3d264ff`; tôi đã đối chiếu lại 10 ảnh dự đoán trong `assets/eval_predictions/visuals/` với nhãn thật trong `dataset/labels/eval/` để đối chiếu từng dòng trong bảng "Ví dụ cụ thể".

### Tài liệu tham khảo ngoài repo

- Ultralytics YOLO documentation (https://docs.ultralytics.com/) — tham khảo tham số `model.train()`, ý nghĩa các chỉ số `P/R/mAP50/mAP50-95` và cấu trúc thư mục `runs/`.
- Google Colab — tài liệu chính thức (https://research.google.com/colaboratory/faq.html) về chọn runtime GPU.
