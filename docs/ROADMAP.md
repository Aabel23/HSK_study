# Danh sách việc cần làm để app chuyên nghiệp hơn

Bản rà soát toàn bộ mã nguồn và dữ liệu, xếp theo mức độ ảnh hưởng tới người
học. Mục đã làm được đánh dấu ✅ kèm chỗ code tương ứng; mục còn lại ghi rõ vì
sao đáng làm chứ không chỉ ghi tên việc.

---

## 1. Dữ liệu — chỗ yếu nhất của app

### ✅ 1.1 Nghĩa tiếng Việt sai trong từ điển

3.152 mục có nghĩa tiếng Việt đọc trôi chảy nhưng **sai nghĩa**: `少见`
("hiếm, ít thấy") ghi là "nhìn", `忽悠` ("lắc lư, lóe lên") ghi là "nhẹ",
`满怀` ghi là "đầy tâm".

Nguyên nhân nằm ở hai tầng, cùng một cái bẫy: cả `translate_meanings.py` lẫn
`seed_data.py` đều chỉ sửa nghĩa khi nó *trông giống tiếng Anh*. Nghĩa sai mà
trông Việt thì lọt qua cả hai. CVDICT vốn đã có nghĩa đúng cho gần như toàn bộ
số đó — không cần dịch lại, chỉ cần một quy tắc biết khi nào nên tin CVDICT.

Đã xử lý bằng `scripts/repair_meanings.py` với hai quy tắc thận trọng: **thay
hẳn** khi nghĩa hiện tại không trùng một nét nghĩa nào với CVDICT (1.406 mục),
và **bổ sung** khi CVDICT là tập cha thực sự (1.617 mục, hợp nhất chứ không ghi
đè nên không mất nét nghĩa cũ). Chữ đơn đa âm được miễn trừ vì tra theo âm hay
chọn nhầm nghĩa (`更` gèng "hơn" dễ bị thay bằng gēng "thay đổi"), và 150 từ
HSK1 viết tay được giữ nguyên vì chúng cố ý hẹp hơn từ điển cho người mới.

### ⬜ 1.2 Câu ví dụ — thiếu 10.819/10.969 từ

Chỉ 150 từ HSK1 có câu ví dụ. Với mục tiêu "từ điển thật", đây là khoảng trống
lớn nhất còn lại: một mục từ không có ví dụ thì người học biết nghĩa nhưng
không biết dùng.

Hướng làm: dùng `scripts/generate_bank.py` (đã có sẵn bộ máy sinh + kiểm định)
thêm chế độ sinh ví dụ, ràng buộc chữ dùng trong ví dụ phải nằm trong vốn từ
cùng cấp trở xuống, và câu phải chứa chính từ đang minh hoạ. Chạy offline theo
từng cấp, commit kết quả.

### ⬜ 1.3 Kho câu luyện tập còn mỏng

246 câu cho cả 7 cấp (HSK6 và HSK7-9 mỗi cấp chỉ 20 câu). Luyện câu vì thế lặp
lại rất nhanh. Cần nâng lên khoảng 150–200 câu mỗi cấp bằng cùng bộ máy sinh.

---

## 2. Đề thi — chống trùng lặp

### ✅ 2.1 Sinh đề bằng LLM, kiểm duyệt offline

`scripts/generate_bank.py` gọi Gemini sinh đề mới, `scripts/content_quality.py`
kiểm định từng câu trước khi cho vào ngân hàng. Ba lớp giữ chất lượng: prompt
mang theo **danh sách từ vựng thật của cấp đó lấy từ database** (không để model
tự đoán "HSK 2 là gì"), prompt liệt kê các câu đã có kèm lệnh cấm viết lại, và
câu nào sai thì **loại bỏ chứ không vá** — vá một câu hỏng ngầm tốn hơn nhiều
so với sinh lại.

Kiểm định gồm ba nhóm: đúng cấu trúc (đủ trường runtime cần), tự nhất quán
(đáp án thật sự giải được câu hỏi), và đúng trình độ (≥85% chữ nằm trong vốn từ
của cấp). Bộ kiểm định được hiệu chỉnh bằng chính đề viết tay: 124/126 câu cũ
đạt, 2 câu bị gắn cờ đều là lỗi thật — trong đó `br2-05` là **lỗi đang chạy
trong đề thật**, đáp án `可以` lộ nguyên văn ở vế sau của chính câu đó. Đã sửa.

Đã sinh 96 câu đạt chuẩn cho phần đọc sơ cấp (30 → 126 câu).

### ✅ 2.2 Không lặp câu khi chưa dùng hết ngân hàng

Ngân hàng to hơn vẫn chưa đủ: `random.sample` trên 40 câu vẫn phát lại câu cũ
sau vài lượt thi. `backend/services/item_pool.py` ghi nhớ câu đã phát
(`item_exposure`) và **ưu tiên câu chưa gặp**, chỉ quay vòng khi đã dùng hết.
Ghi nhận lúc phát đề chứ không phải lúc nộp, vì câu đã đọc rồi thì coi như đã
dùng. Nếu bảng lịch sử có sự cố thì tự lùi về random — lỗi sổ sách không được
phép chặn một kỳ thi.

### ⬜ 2.3 Mở rộng nốt các phần còn lại

Đọc trung cấp (10/6/6 câu) và HSKK (8–24 câu mỗi phần) vẫn còn mỏng. Chạy tiếp
`generate_bank.py` cho từng phần. Giới hạn tốc độ của Gemini là nút thắt: mỗi
lượt chạy nên giới hạn `--count 50` cho một phần rồi chạy lại.

### ⬜ 2.4 Hiện pinyin và bản dịch sau khi trả lời *(đang làm dở)*

Backend đã xong: mỗi câu trong ngân hàng nhận thêm khối `gloss`, và
`reading_service.check_answer` trả về danh sách `reveal` gồm đoạn văn, câu hỏi
và đáp án — mỗi mục có chữ Hán, pinyin, nghĩa tiếng Việt.

Còn lại: chạy `generate_bank.py --gloss` để bù pinyin/bản dịch cho các câu đã
có, và render khối `reveal` trong `ReadingRunner.tsx`.

### ⬜ 2.5 Hai chế độ thi *(đang làm dở)*

Cột `feedback_mode` (`instant` / `deferred`) và `given_answer` đã được thêm vào
schema theo hướng bổ sung. Còn lại: chế độ `deferred` phải giấu kết quả tới khi
nộp bài, thêm endpoint xem lại toàn bài sau khi nộp, và nút chọn chế độ ở màn
hình bắt đầu.

---

## 3. Kiến trúc — gọn lại phần cồng kềnh

### ✅ 3.1 Vòng đời phiên học bị lặp ở 7 service

Bảy loại bài luyện tập đều có bản sao của cùng bốn bước: tạo phiên, tìm phiên
và từ chối nếu đã nộp, đóng phiên kèm điểm, cộng vào chuỗi ngày. Các bản sao
chỉ khác nhau tên bảng và danh từ tiếng Việt trong câu lỗi.

Gom vào `backend/services/session_store.py`: mỗi service khai báo một
`SessionKind` thay vì chép lại SQL. Service vẫn giữ phần thật sự riêng của nó —
cách chọn câu, cách chấm.

Nhân tiện sửa được một lỗi tính trùng: luyện gõ và nghe chép vừa cộng chuỗi
ngày ở mỗi câu trả lời, vừa cộng lại lúc kết thúc phiên. Nay cờ `record_streak`
nói rõ bên nào chịu trách nhiệm.

### ✅ 3.2 Sinh câu trắc nghiệm bị chép đôi

`quiz_service` và `listening_service` có hai bản `_generate_one` gần như giống
hệt. Gom vào `backend/services/mcq.py`.

### ✅ 3.3 Thống kê không nhất quán

Có service đếm mọi phiên từng mở, có service chỉ đếm phiên đã nộp. Nay
`session_store.attempt_stats` chỉ đếm phiên đã nộp ở mọi nơi, nên phiên bỏ dở
không còn thổi phồng số liệu.

### ⬜ 3.4 `hskk_service.py` vẫn còn to (860 dòng)

Nó đang ôm ba việc: dựng đề, chấm bằng AI, và tổng kết điểm. Nên tách phần
prompt + chấm AI ra `hskk_grading.py`, giữ `hskk_service` cho vòng đời bài thi.

### ⬜ 3.5 `Hskk.tsx` 797 dòng

Trang lớn nhất frontend, gộp cả màn chọn đề, phần đọc, phần nói và màn tổng
kết. Tách theo từng giai đoạn như `ReadingRunner.tsx` đã tách sẵn.

---

## 4. Tính năng học

### ✅ 4.1 Tab Ngữ pháp *(backend xong)*

Mảng lớn duy nhất app còn thiếu so với một app HSK hoàn chỉnh. 32 điểm ngữ pháp
HSK1–4, mỗi điểm có mẫu câu, giải thích viết **theo thói quen tiếng Việt** chứ
không dịch từ sách Anh ngữ, một mục `pitfall` gọi tên đúng lỗi người Việt hay
mắc (`我学习在学校` sai vì tiếng Việt đặt nơi chốn sau động từ), ví dụ có pinyin,
và bài tập chấm ở server.

Còn lại: trang React và mục trong menu.

### ✅ 4.2 Tab Ngân hàng đề *(backend xong)*

`/api/content/overview` trả về quy mô từng pool, tỉ lệ đã gặp, số đề còn "mới"
có thể phát, và pool nào sắp cạn. Còn lại: trang React.

### ⬜ 4.3 Trang Luyện viết đang bị ẩn

Code và API đã đủ, chỉ thiếu phần chấm nét. Bật lại chỉ là đổi một cờ trong
`navigation.ts` sau khi hoàn thiện phần chấm.

---

## 5. Vận hành

### ⬜ 5.1 Model Gemini mặc định đang hỏng

`gemini-flash-latest` trả 503 liên tục trong suốt phiên làm việc, nghĩa là
**chấm nói bằng AI hiện đang không dùng được**. `gemini-3.5-flash` chạy tốt.
Nên đổi mặc định trong `backend/settings.py`, hoặc để `GEMINI_MODEL` trong môi
trường triển khai.

### ✅ 5.2 Phân biệt lỗi tạm thời và lỗi vĩnh viễn

Trước đây mọi lỗi Gemini đều như nhau, nên script sinh đề thử lại cả những lỗi
mà chờ bao lâu cũng vô ích (model đã bị gỡ, khoá sai). Nay `TransientError`
(429, 5xx, mất mạng) mới được thử lại; lỗi vĩnh viễn dừng ngay và báo rõ.

### ⬜ 5.3 Chưa có test cho luồng sinh nội dung

`content_quality.py` là thứ quyết định câu hỏi nào tới tay người học, nhưng
chưa có test. Nên có test cho từng loại lỗi mà nó bắt.
