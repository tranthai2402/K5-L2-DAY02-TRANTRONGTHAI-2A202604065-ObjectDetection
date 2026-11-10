# Mini guideline — bài làm cá nhân

> Điền nội dung này trước khi bắt đầu gán nhãn. Giữ lại các quyết định sau khi self-QC.

## Định nghĩa lớp

| Lớp | Định nghĩa của bạn | Ví dụ/điểm phân biệt |
| --- | --- | --- |
| `car` | Xe con bốn bánh, sedan/hatchback/SUV/taxi/pickup; kính xe quan sát được từ trên xuống | Bán tải (pickup) vẫn là `car` vì cabin + thùng hàng nhỏ, tỷ lệ dài ngang phần cabin; xe buýt/thùng hàng lớn không phải `car` |
| `truck` | Xe tải chở hàng (thùng hàng rộng, cabin nhỏ ở đầu) và xe đầu kéo | Thùng hàng chiếm phần lớn diện tích, thùng thẳng/bo, không có hàng kính ở phần sau |
| `bus` | Xe buýt chở khách và minibus chở khách; thân xe dài, kính sàn liên tục dọc hai bên | Không có hàng kính ở phần sau; minibus chở khách vẫn là `bus` |
| `van` | Xe van/minivan: thân hộp, kính lái và kính cửa sổ ở phía trước, phần sau là hàng/khoang không có kính sàn | Khác `bus` ở chỗ phần sau không có dãy kính sàn dài; khác `car` ở thân vuông, kính nhỏ ở đuôi |

## Quy tắc chung

- Box bám sát vật thể nghĩa là: box chỉ ôm đúng phần thân xe **nhìn thấy được** trên ảnh, không lấn mặt đường/sân vỉa, không lấn xe bên cạnh; 4 cạnh song song với mép ảnh (axis-aligned), không vẽ box xoay/polygon.
- Vật thể bị che khuất: vẽ box quanh **phần thân còn nhìn thấy** của chính chiếc xe đó, không vẽ vùng bị che, không gộp hai chiếc xe chồng lên nhau thành một box.
- Vật thể bị cắt bởi rìa ảnh: box chạm đúng mép ảnh (tọa độ = 0 hoặc 1), **không suy diễn** phần thân nằm ngoài ảnh.
- Vật thể rất nhỏ/mơ hồ: nếu không phân biệt được loại xe thì **không gán**; ghi tên ảnh vào mục bên dưới và hỏi giảng viên.

## Ghi lại quyết định cho ít nhất ba ca mơ hồ

| Ảnh | Tình huống | Quyết định cuối | Lý do theo schema |
| --- | --- | --- | --- |
| `drive_003` | Xe tải/thùng hàng lớn ở góc phải, một phần thân bị cắt bởi rìa ảnh; thùng hàng không có kính sàn nhưng cabin rất nhỏ so với thùng | **Gán `truck` (1)** | Tỷ lệ thùng hàng >> cabin và phần thùng không có dãy kính sàn dọc hai bên → không phải `van`/`bus`; thùng thẳng vuông → không phải `car` |
| `drive_021` | Nhiều xe nhỏ ở nửa dưới ảnh do góc nhìn xa, có xe 2–3 tông màu sát nhau trông như một khối | **Tách thành từng box riêng, mỗi xe một box**, không gộp | Quy tắc "mỗi xe một box": hai xe cạnh nhau vẫn là hai vật thể; nếu không tách được thì bỏ qua xe đó, không gộp |
| `drive_050` | Xe ở rìa phải bị cắt khung, chỉ còn một phần thân và không quan sát được đuôi để phân biệt `car` với `van` | **Gán `car` (0) nếu vẫn nhận diện được cabin + kính lái**; nếu mảnh quá nhỏ thì bỏ qua | Lớp mô tả **loại vật thể**; xe bị cắt khung vẫn gán nếu phần nhìn thấy đủ để nhận diện lớp; không đoán phần ngoài ảnh |

> Ba ca trên là các ca tôi đã ghi nhận khi xem trước tập train. Khi gán thực tế, nếu gặp ca khác lệch với các ca này (ví dụ xe tải nhỏ, xe buýt ở xa), bổ sung thêm vào bảng và hỏi giảng viên.
