# Cảnh báo của Windows khi mở ChineseStudy.exe

Tài liệu này giải thích chính xác vì sao Windows cảnh báo, phần nào đã được xử
lý sẵn trong repo, và phần nào **bắt buộc phải mua chứng chỉ** mới giải quyết
được.

## Tóm tắt ngắn

| Việc | Trạng thái | Ai được lợi |
| --- | --- | --- |
| Nhúng thông tin phiên bản (VERSIONINFO) | ✅ đã làm | Mọi người |
| Icon ứng dụng | ✅ đã làm | Mọi người |
| Tắt nén UPX (giảm cảnh báo antivirus) | ✅ đã làm | Mọi người |
| Ghi log ra tệp để chẩn đoán sự cố | ✅ đã làm | Mọi người |
| Quy trình ký Authenticode sẵn sàng | ✅ đã làm | Cần chứng chỉ |
| Chứng chỉ tự ký + tin cậy cục bộ | ✅ có script | Chỉ máy của bạn |
| **Xoá hẳn cảnh báo SmartScreen cho mọi người** | ❌ **cần mua chứng chỉ OV/EV** | Mọi người |

> **Điểm mấu chốt:** không có mẹo kỹ thuật nào xoá được cảnh báo
> "Unknown publisher" của Windows SmartScreen. Cảnh báo đó tồn tại chính xác để
> báo rằng tệp không được ký bởi một nhà phát hành đã được xác minh. Cách duy
> nhất để nhà phát hành được xác minh là mua chứng chỉ ký mã từ một tổ chức
> chứng thực (CA) và trải qua quá trình xác minh danh tính.

## Vì sao Windows cảnh báo

Windows hiển thị hai loại cảnh báo khác nhau, thường bị nhầm lẫn:

1. **SmartScreen** — "Windows protected your PC". Xuất hiện khi tệp chưa được ký
   hoặc chưa tích luỹ đủ danh tiếng (reputation). Đây là cảnh báo bạn đang gặp.
2. **Antivirus / Defender** — báo tệp là mã độc. Thường là dương tính giả với
   các tệp PyInstaller, đặc biệt khi được nén bằng UPX.

Repo này đã xử lý triệt để nguyên nhân của (2) và mọi thứ có thể làm được cho
(1) mà không cần tiền.

## Những gì đã được sửa trong repo

### 1. Tệp thực thi có danh tính thật

`scripts/version_info.py` sinh ra tài nguyên VERSIONINFO và được nhúng vào exe.
Nhấn chuột phải vào `ChineseStudy.exe` → Properties → Details, bạn sẽ thấy tên
sản phẩm, phiên bản, bản quyền thay vì các ô trống. Một tệp không có thông tin
này bị cả người dùng lẫn hệ thống chấm điểm danh tiếng đánh giá là đáng ngờ.

### 2. Icon ứng dụng

`scripts/make_icon.py` tạo `assets/app_icon.ico`. Icon xuất hiện trong Explorer,
trên thanh tác vụ và ngay trong hộp thoại SmartScreen.

### 3. Không nén UPX

Trước đây bản build dùng UPX. Tệp thực thi bị nén UPX là một trong những nguyên
nhân phổ biến nhất gây dương tính giả cho antivirus, vì mã độc cũng hay dùng kỹ
thuật này để che giấu. Bản build hiện tại mặc định **không** dùng UPX. Tệp lớn
hơn vài megabyte nhưng "sạch" hơn nhiều dưới góc nhìn của trình quét.

### 4. Tuỳ chọn build theo thư mục

`python scripts/build_exe.py --onedir` tạo ra một thư mục thay vì một tệp duy
nhất. Bản one-file phải tự giải nén ra thư mục tạm mỗi lần chạy — đúng hành vi
mà các trình quét heuristic coi là khả nghi. Bản `--onedir` khởi động nhanh hơn
và ít bị cảnh báo hơn; đánh đổi là phải phân phối cả thư mục.

## Cách xoá cảnh báo hoàn toàn (cần chứng chỉ)

### Phương án A — chứng chỉ EV (khuyến nghị nếu phát hành rộng)

- Giá tham khảo: khoảng 250–500 USD mỗi năm.
- Nhà cung cấp: DigiCert, Sectigo, GlobalSign, SSL.com.
- Cần xác minh danh tính doanh nghiệp; khoá riêng tư nằm trên thiết bị phần cứng
  (USB token) hoặc HSM đám mây.
- **Xoá cảnh báo SmartScreen ngay lập tức**, không cần tích luỹ danh tiếng.

### Phương án B — chứng chỉ OV / IV

- Rẻ hơn (khoảng 100–200 USD mỗi năm); cá nhân cũng đăng ký được (Individual
  Validation).
- Cảnh báo **không** biến mất ngay: SmartScreen cần thời gian tích luỹ danh
  tiếng qua số lượt tải và cài đặt. Thường mất vài tuần đến vài tháng.

Sau khi có chứng chỉ, ký bản build:

```powershell
$env:CHINESE_STUDY_CERT = "C:\path\to\certificate.pfx"
$env:CHINESE_STUDY_CERT_PASSWORD = "mật khẩu của bạn"
python scripts\build_exe.py --sign
```

Hoặc nếu chứng chỉ đã nằm trong kho chứng chỉ Windows:

```powershell
$env:CHINESE_STUDY_CERT_SUBJECT = "Tên công ty của bạn"
python scripts\build_exe.py --sign
```

Script tự tìm `signtool.exe` trong Windows SDK, tự động đóng dấu thời gian
(timestamp) để chữ ký vẫn hợp lệ sau khi chứng chỉ hết hạn, và thử lần lượt
nhiều máy chủ timestamp nếu một máy chủ gặp sự cố.

## Chỉ muốn hết cảnh báo trên máy của mình

Nếu bạn chỉ dùng ứng dụng cho bản thân, một chứng chỉ tự ký là đủ:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_selfsigned_cert.ps1 -Trust
$env:CHINESE_STUDY_CERT_SUBJECT = "Chinese Study"
python scripts\build_exe.py --sign
```

Lưu ý quan trọng: script này cài một chứng chỉ gốc vào kho tin cậy của tài khoản
người dùng hiện tại. Đó là một thay đổi thật đối với thiết lập bảo mật của máy —
chỉ chạy khi bạn hiểu và chấp nhận điều đó. Trên máy người khác, cảnh báo vẫn sẽ
xuất hiện như cũ.

## Cách người dùng cuối mở tệp khi chưa ký

Nếu bạn gửi bản chưa ký cho người khác, hướng dẫn họ:

1. Nhấn **More info** trong hộp thoại SmartScreen.
2. Nhấn **Run anyway**.

Hoặc: chuột phải vào tệp → Properties → tích **Unblock** → OK. Thao tác này gỡ
cờ "tải từ Internet" (Zone.Identifier) mà Windows gắn vào tệp tải về.

## Nếu Windows Defender báo virus

Đây gần như chắc chắn là dương tính giả của PyInstaller. Cách xử lý:

1. Build lại bằng `--onedir` (ít bị nhận nhầm hơn).
2. Gửi mẫu tới Microsoft để phân tích:
   <https://www.microsoft.com/en-us/wdsi/filesubmission> — thường được gỡ nhận
   nhầm trong vòng vài ngày và có hiệu lực cho tất cả người dùng.
3. Ký tệp — tệp đã ký ít bị đánh giá sai hơn đáng kể.
