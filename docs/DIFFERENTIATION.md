# Chinese Study đứng ở đâu so với thị trường

Tài liệu này trả lời một câu hỏi cụ thể: **ứng dụng này làm được gì mà các app
tiếng Trung phổ biến ở Việt Nam không làm**, và tại sao nên dồn sức vào đúng chỗ
đó. Phần cuối liệt kê những chỗ ta đang thua — vì một bản phân tích chỉ kể điều
hay thì không dùng được để ra quyết định.

## Bối cảnh: thị trường đã rất tốt ở đâu

[Hanzii](https://apps.apple.com/vn/app/id1468400944) là mốc so sánh hợp lý nhất
cho người Việt: từ điển Trung–Việt, tra bằng chữ viết tay / giọng nói / hình
ảnh, mẹo nhớ Hán tự bằng hình ảnh và câu chuyện, hơn 200 đề thi thử HSK / HSKK /
TOCFL, flashcard và quiz. Ngoài ra còn Pleco (từ điển Trung–Anh sâu nhất thị
trường), Anki (SRS mạnh nhất), Duolingo và HelloChinese (vòng lặp học gây
nghiện nhất).

Đây đều là những sản phẩm nhiều năm tuổi, có đội ngũ. **Đua tính năng trực diện
với họ là thua.** Ta không có OCR, không có nhận dạng chữ viết tay, không có 200
đề thi được biên soạn tay.

Nhưng cả bốn nhóm trên đều bỏ trống đúng một chỗ.

---

## Điểm vượt trội: dạy **giải mã**, không chỉ dạy **ghi nhớ**

### Vấn đề mà không app nào đang giải

Mọi app học tiếng Trung đều là app dạy **danh sách từ**. HSK 1 có 500 từ, HSK
7–9 có 11.000 từ. Học xong danh sách thì hết — người học đọc một bài báo và vẫn
gặp từ chưa từng thấy, và không có công cụ nào để xử lý.

Đó là trần của mô hình "dạy từ": nó tuyến tính. Học 1 từ được 1 từ.

### Lợi thế mà chỉ người Việt mới có

Hơn một nửa từ vựng tiếng Việt trang trọng là gốc Hán, và **mỗi chữ Hán có một
âm Hán-Việt cố định**. Nghĩa là với người Việt, một từ tiếng Trung chưa học vẫn
có thể **suy ra được**:

| Từ | Âm Hán-Việt | Người Việt nhận ra |
| --- | --- | --- |
| 图书馆 | đồ thư quán | thư viện |
| 发展 | phát triển | phát triển |
| 经济 | kinh tế | kinh tế |
| 热水器 | nhiệt thuỷ khí | máy nước nóng |
| 脱口而出 | thoát khẩu nhi xuất | buột miệng nói ra |

Người học tiếng Anh, Nhật, Hàn không có đường tắt này. **Đây là lợi thế cấu trúc
của thị trường Việt Nam, và chưa ai khai thác nó như một kỹ năng có thể dạy
được.**

### Hanzii làm gì, và tại sao vẫn chưa đủ

Hanzii **có hiển thị** âm Hán-Việt — nó là một trường trong mục từ điển. Cách
tiếp cận đó coi âm Hán-Việt là **thông tin tra cứu**.

Ta coi nó là **kỹ năng cần luyện**. Khác biệt nằm ở bốn thứ Hanzii không có:

1. **Đề rút từ những từ người học *chưa từng mở*.** Mọi bài luyện khác trong mọi
   app đều hỏi lại từ đã dạy. Bài "Luyện giải mã" cố tình làm ngược lại — vì chỉ
   khi từ trên màn hình là từ lạ thì mới thật sự đang luyện giải mã chứ không
   phải nhớ lại. Đây là điểm khác biệt sâu nhất và cũng khó sao chép nhất, vì nó
   đòi hỏi biết người học *chưa* học gì.

2. **Ghi công theo chữ, không theo từ.** Trả lời đúng 图书馆 được tính là bằng
   chứng cho 图, 书 và 馆 — vì chính ba chữ đó mới mang sang được từ tiếp theo.
   Tiến độ nằm ở lớp có khả năng khái quát hoá.

3. **Họ từ, tra được bằng chỉ mục.** Bảng `word_characters` liên kết 21.946 cặp
   từ–chữ, nên "mọi từ trong kho được dựng từ chữ 学" là một truy vấn có index,
   không phải quét `LIKE '%学%'`. Người học đi từ 1 chữ ra 58 từ ngay lập tức.

4. **Xếp hạng theo đòn bẩy.** Chữ được xếp theo số từ mà nó mở khoá:

   | Chữ | Âm | Số từ mở khoá |
   | --- | --- | --- |
   | 不 | bất | 207 |
   | 人 | nhân | 142 |
   | 子 | tử | 139 |
   | 一 | nhất | 130 |
   | 大 | đại | 111 |

   Không giáo trình HSK nào sắp xếp theo trục này, vì HSK sắp theo tần suất
   *từ*, không theo *độ phủ của chữ*. Học 100 chữ đầu bảng này phủ được phần lớn
   kho từ — học phi tuyến, khác hẳn "1 từ ăn 1 từ".

### Con số hậu thuẫn

Số liệu thật từ cơ sở dữ liệu hiện tại:

- **8.200 chữ Hán** có âm Hán-Việt, trong đó **2.735 chữ** xuất hiện trong kho
  từ HSK.
- **10.357 / 10.969 từ (94,4%)** đọc được **trọn vẹn** bằng âm Hán-Việt.
- Tính theo **tần suất sử dụng**, độ phủ chữ đạt **97,1%**.
- **414 bộ thủ** kèm tên, nghĩa và mẹo nhớ tiếng Việt; **83% chữ trong kho** có
  ít nhất bộ thủ chính kèm chú giải.

### Chỗ ta chọn *không* làm, và vì sao đó là điểm mạnh

Unihan có trường `kVietnamese` phủ thêm khoảng 5.000 chữ nữa. Ta **không dùng**,
vì nó trộn âm Hán-Việt với âm Nôm mà không phân biệt: 库 ghi "kho" (Nôm; Hán-Việt
là *khố*), 貝 ghi "buổi" (đúng ra *bối*), 礎 ghi "sờ" (đúng ra *sở*), 紐 ghi "néo"
(đúng ra *nữu*).

Nhận nguồn đó sẽ nâng độ phủ từ 92% lên 96% — và dạy sai hàng nghìn chữ, trên
đúng màn hình lấy "âm Hán-Việt cho biết nghĩa" làm nền tảng. **Chữ nào không có
cách đọc đáng tin thì để trống.** Với sản phẩm giáo dục, đó là tính năng chứ
không phải thiếu sót, và nó là thứ một đối thủ chạy theo con số sẽ làm sai.

---

## Ba điểm vượt trội phụ

### 1. Đáp án trắc nghiệm không tự lộ

Kho từ giữ nguyên mục từ điển đầy đủ, nên nghĩa dài từ 1 tới 472 ký tự. Hầu hết
app rút bốn từ ngẫu nhiên rồi in nghĩa lên bốn nút — và câu hỏi tự lộ đáp án:

```
A. ăn        B. và        C. đi
D. (sau một mệnh đề giả định) trong trường hợp đó; thì; (sau một mệnh đề
   hành động) ngay khi; ngay sau khi; chỉ; không gì khác ngoài; …
```

Chọn được D mà không cần đọc một chữ Hán nào. Ta sửa ở **khâu chọn từ**, không
chỉ cắt lúc hiển thị: rút dư ứng viên rồi giữ những từ có độ dài đáp án gần nhau
nhất. Độ lệch trung vị giảm từ **13 xuống 2 ký tự**. Với đáp án là âm Hán-Việt
thì cân theo **số âm tiết** — 99,5% câu hỏi lệch tối đa 1 âm tiết, vì "cáp tử"
đứng cạnh "tinh ích cầu tinh" bị đoán ra bằng cách đếm chữ.

Chỉ cắt lúc hiển thị là **không đủ**, vì việc cắt xảy ra *sau* khi bốn từ đã
được chọn — không xoá được manh mối.

### 2. Chạy local hoàn toàn, dữ liệu là của người dùng

Không tài khoản, không đăng nhập, không gửi dữ liệu đi đâu. SQLite nằm trên máy,
sao lưu và khôi phục bằng file JSON. Hanzii, Pleco, Duolingo đều là dịch vụ đám
mây — mất tài khoản là mất tiến độ. Ngoài ra ứng dụng đóng gói thành `.exe`
Windows chạy không cần cài Python hay Node.

Kèm theo đó: **toàn bộ nguồn dữ liệu đều có giấy phép mở và được ghi công**
(CC-CEDICT, CVDICT, hanzi-sino-vietnamese, Wiktionary, Unihan). Người dùng kiểm
chứng được nghĩa đến từ đâu.

### 3. Đề thi thử là một bài liền mạch

Phần đọc (判断对错, 选词填空, 排列顺序, 阅读理解) chạy thẳng sang phần nói theo
đúng số câu, thang điểm và thời gian của HSKK — trong một phiên duy nhất, chứ
không phải hai bài rời. Phần nói chấm bằng Gemini khi có khoá, tự chấm khi
không, và bài thi không bao giờ hỏng vì thiếu khoá.

---

## Chỗ ta đang thua, nói thẳng

| Hạng mục | Hiện trạng | Ghi chú |
| --- | --- | --- |
| Tra bằng chữ viết tay / ảnh / giọng nói | Không có | Hanzii có cả ba. Cần model on-device, chi phí lớn. |
| Số lượng đề thi thử | Ít hơn nhiều | Hanzii có 200+ đề biên soạn tay. Ngân hàng của ta hiện 397 câu, mọi pool đủ cho ít nhất 4 lượt thi không lặp câu nào. |
| Câu ví dụ cho từ | 1.177 / 10.969 từ (10,7%) | Đã tăng 8 lần bằng cách đánh chỉ mục chính kho câu sẵn có của dự án. Vẫn kém xa một từ điển thật; muốn hơn nữa phải có nguồn câu mới. |
| SRS dùng chung mọi hoạt động | Xong một chiều | Sai ở bất kỳ bài luyện nào cũng kéo từ về hàng đợi ôn. Câu đúng cố tình không tính, để một cú đoán mò không thành "đã thuộc". |
| Di động | Chỉ web | Không có app native. |
| Mẹo nhớ Hán tự | 659 / 2.735 chữ trong kho | Phần còn lại chưa có mnemonic viết tay. |
| Chiết tự / bộ thủ | 2.279 / 2.735 chữ (83%) | 659 chữ có chiết tự đầy đủ; số còn lại có bộ thủ chính suy từ Unihan, kèm tên và mẹo nhớ tiếng Việt, và được ghi nhãn đúng là bộ thủ chứ không phải chiết tự. |
| Lịch ôn cho chữ | Xong | Chữ có lịch SM-2 riêng; chữ quá hạn được hỏi trước. Không app nào khác lên lịch ở mức chữ. |

### Việc nên làm tiếp, theo thứ tự

1. **Thêm câu ví dụ.** Đã đi từ 1,4% lên 10,7% mà không nhập nguồn ngoài, bằng
   cách đánh chỉ mục 483 câu dự án đã tự viết và đã kiểm (kho luyện câu, ví dụ
   trong bài ngữ pháp, đề nói HSKK). Muốn vượt mốc này phải soạn thêm câu —
   Tatoeba chỉ có 798 cặp Trung–Việt nên không giải quyết được vấn đề.
2. **Mnemonic cho phần chữ còn lại**, để phần chiết tự phủ đều thay vì chỉ 659
   chữ cốt lõi.
4. **App di động.** Hiện chỉ có web và bản `.exe` Windows.

---

## Tóm lại

Định vị nên gói trong một câu: **đây là ứng dụng duy nhất dạy người Việt cách
đọc hiểu những từ tiếng Trung chưa từng học, bằng chính vốn Hán-Việt họ đã có.**

Mọi app khác cạnh tranh ở "dạy được bao nhiêu từ". Ta cạnh tranh ở "sau khi hết
từ để dạy thì sao" — và đó là câu hỏi mà lợi thế ngôn ngữ của người Việt trả lời
được, còn thị trường thì chưa hỏi.
