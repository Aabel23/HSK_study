# Đặc tả MVP Chinese Study

## Chính sách bảo tồn

Phiên bản hiện tại là baseline di sản của dự án. Các phiên bản tiếp theo chỉ mở rộng theo hướng bổ sung và phải giữ tương thích ngược. Không loại bỏ chức năng, API, dữ liệu, giao diện hoặc hành vi hiện có và không thực hiện migration phá hủy dữ liệu nếu chưa có yêu cầu rõ ràng từ chủ dự án.

## Mục tiêu

Ứng dụng web local dành cho người Việt học từ vựng HSK1 bằng Flashcard và trò chơi nối từ. Giao diện dùng tiếng Việt, dữ liệu học và thống kê phải lấy từ backend.

## Các màn hình

1. **Tổng quan**: thống kê từ vựng, trạng thái học, kết quả nối từ và từ vừa học.
2. **Từ vựng HSK1**: danh sách có phân trang, tìm kiếm, lọc, chi tiết và cập nhật trạng thái.
3. **Flashcard**: tạo phiên 1–200 thẻ (chọn nhanh hoặc nhập số cụ thể), lọc theo cấp độ HSK đang chọn, lật thẻ, bật/tắt pinyin ngay trong phiên, đánh giá và tổng kết.
4. **Nối từ**: sáu cặp mỗi vòng, hai chế độ `meaning` và `pinyin`, hai cột xáo độc lập.
5. **Luyện câu**: chọn số câu mỗi phiên (1–200), sắp xếp các cụm Hán ngữ theo đúng thứ tự, bật/tắt Pinyin và nghĩa tiếng Việt, lưu số lần đúng/sai.
6. **Thi thử HSK**: một đề duy nhất chạy từ phần đọc tới phần thi nói. Phần đọc
   theo cấu trúc 阅读 của đề thật (判断对错, 选词填空, 排列顺序, 阅读理解) với
   đáp án chấm ở server; nửa nói theo đúng số phần/số câu/thang điểm/thời gian
   của HSKK Sơ cấp và Trung cấp. Trang Kiểm tra cũ đã gộp vào đây và bị ẩn khỏi
   menu. Phát đề bằng TTS, ghi âm trong trình
   duyệt, chấm bằng Gemini khi có khoá và tự chấm khi không. Mỗi nửa thang 100,
   điểm cuối là trung bình. Xem `docs/API.md` mục Thi thử HSK cho thang điểm và
   phần cấu hình khoá.
7. **Giải mã Hán-Việt**: xem mục riêng bên dưới.
8. **Tiến độ**: mức hoàn thành, từ cần ôn, từ đã thuộc và lịch sử phiên gần đây.

## Giải mã Hán-Việt

Màn hình duy nhất trong ứng dụng **không** kiểm tra trí nhớ. Mọi màn hình khác
hỏi lại một từ đã dạy; màn hình này đưa ra một từ **chưa** dạy và yêu cầu người
học suy ra nghĩa.

Cơ sở của nó là một lợi thế mà người học Việt Nam có còn người học nước khác thì
không: hơn một nửa từ vựng tiếng Việt trang trọng là gốc Hán, và mỗi chữ Hán có
một âm Hán-Việt cố định. Biết 学 = *học* và 生 = *sinh* thì 学生 không phải từ
cần thuộc lòng — nó là "học sinh", từ đã biết từ nhỏ. Cũng hai chữ đó mở tiếp
学期 (học kỳ), 生活 (sinh hoạt), 医生 (y sinh) và hàng trăm từ khác.

Ba tab:

1. **Tra chữ** — âm Hán-Việt, pinyin, nghĩa, số nét, phồn thể, chiết tự theo bộ
   thủ kèm mẹo nhớ, và **họ từ**: mọi từ trong kho được dựng từ chữ đó, nhóm
   theo cấp HSK.
2. **Luyện giải mã** — ba chế độ (`han_viet_to_meaning`, `meaning_to_han_viet`,
   `character_reading`). Đề **ưu tiên rút từ những từ người học chưa mở bao
   giờ**: chỉ khi đó mới thật sự là giải mã chứ không phải nhớ lại. Trả lời đúng
   một từ sẽ ghi công cho **từng chữ** trong từ, vì chữ mới là thứ mang sang
   được từ tiếp theo.
3. **Chữ chủ lực** — xếp hạng chữ theo số từ mà nó mở khoá.

Chữ nào không có cách đọc đáng tin thì để trống chứ không đoán; xem phần ghi chú
về Unihan trong `README.md`.

## Lịch ôn nhận phản hồi từ mọi bài luyện

Trước đây lịch SM-2 chỉ nhúc nhích ở màn hình Ôn tập. Người học có thể sai chữ
我 ở bài luyện nghe, sai tiếp ở bài luyện gõ, mà cái quyết định ngày mai cho học
gì lại không hề biết cả hai lần đó.

Nay sáu bài luyện — kiểm tra, luyện nghe, nối từ, luyện gõ, nghe chép và giải mã
— đều gọi `srs_service.record_lapse` khi trả lời sai. `review_log.source` ghi
lại màn hình nào gây ra, nên lịch sử vẫn phân biệt được.

Chiều phản hồi là **một chiều, chỉ tính câu sai**, và đây là phần dễ làm hỏng
nhất. Câu bốn lựa chọn đúng nhờ may mắn một phần tư số lần, nên coi câu đúng là
bằng chứng sẽ đẩy khoảng ôn dài ra dựa trên không có gì, và một cú đoán mò trông
sẽ giống như đã thuộc. Câu sai thì không có chỗ nào mơ hồ như vậy. Vì thế bài
luyện chỉ có thể **kéo từ trở lại** hàng đợi, không bao giờ đẩy từ ra khỏi đó;
chỉ đánh giá của chính người học ở màn hình Ôn tập mới làm giãn khoảng ôn.

Hai chi tiết bắt buộc:

- `submit_review(..., record_streak=False)` khi gọi từ bài luyện, vì các bài đó
  đã tự cộng điểm cho câu trả lời rồi — cộng lần nữa là trả công hai lần cho
  cùng một câu. Cùng cờ và cùng lý do với `session_store.complete`.
- `record_lapse` trả `None` khi không có từ nào để quy trách nhiệm (nghe chép cả
  câu) hoặc khi từ không còn tồn tại. Lịch ôn là tác dụng phụ, không được phép
  làm hỏng việc lưu câu trả lời.

## Độ sâu ngân hàng đề

Mỗi pool phải chứa **ít nhất gấp bốn số câu rút ra mỗi lượt thi**. Trước đây
phần đọc HSK4 rút 5/3/4 câu từ pool 10/6/6, và phần nói HSKK Sơ cấp rút 15 câu
từ pool 24 — nghĩa là thi lại lần hai gặp gần như đúng đề cũ, biến bài thi thử
thành bài kiểm tra trí nhớ về chính đề đó.

Quy tắc "gấp bốn" được `tests/test_reading_bank.py` canh cho cả phần đọc lẫn
phần nói, nên thêm dạng câu mới mà quên nạp đủ đề sẽ làm đỏ test. `item_pool`
phát câu chưa gặp trước, nên pool sâu chuyển thẳng thành đề mới.

## Độ dài đáp án trắc nghiệm

Kho từ giữ nguyên mục từ điển đầy đủ, nên nghĩa dài từ 1 tới 472 ký tự. Rút bốn
từ ngẫu nhiên rồi in nghĩa lên bốn nút sinh ra câu hỏi tự lộ đáp án: nút dài
nhất là nút đúng, người học chọn được mà không cần đọc chữ Hán nào.

Sửa ở **hai tầng**, và cần cả hai:

- **Lúc chọn từ** (`backend/services/gloss.py`, `mcq.py`, `matching_service.py`,
  `character_service.py`): rút dư ứng viên rồi giữ những từ có độ dài đáp án gần
  với từ đích nhất. Với đáp án là âm Hán-Việt thì so theo **số âm tiết**, vì
  "cáp tử" đứng cạnh "tinh ích cầu tinh" bị đoán ra bằng cách đếm chữ.
- **Lúc hiển thị** (`frontend-web/src/lib/format.ts`): cắt mỗi nhãn còn một
  dòng, và nới dần cho tới khi bốn nhãn khác nhau — nếu không, hai từ khác nghĩa
  có thể cắt về cùng một chuỗi và câu hỏi mất đáp án đúng.

Chỉ cắt lúc hiển thị thì **không đủ**: việc cắt xảy ra sau khi bốn từ đã được
chọn, nên không xoá được manh mối. Quy tắc nhận biết "đoạn này là nghĩa hay là
chú thích từ điển" (`lượng từ:`, `CL:`) nằm cả ở `gloss.py` lẫn `format.ts` —
sửa thì phải sửa cả hai, nếu không backend cân theo một độ dài mà người học
không hề nhìn thấy.

## Ngôn ngữ hiển thị

Toàn bộ nội dung người học đọc phải bằng tiếng Việt. Trường `meaning` của mỗi từ
vựng là nghĩa tiếng Việt; `meaning_en` chỉ là tham chiếu phụ, hiển thị trong
phần chi tiết với nhãn rõ ràng và không bao giờ thay thế nghĩa tiếng Việt.

Bộ dữ liệu gốc lấy từ CC-CEDICT nên từng để lại ba loại lỗi: nghĩa tiếng Anh nằm
trong cột tiếng Việt, chuỗi mojibake, và mã từ loại thô (`g`, `cc`, `Mg`, `Rg`).
`scripts/translate_meanings.py` sửa cả ba từ CVDICT, và `scripts/seed_data.py`
lặp lại việc sửa trên các database đã tồn tại. Quy tắc nhận biết nằm ở
`scripts/meaning_quality.py` — chỉ một nơi duy nhất, để hai bên không lệch nhau.

## Luyện câu

- Dữ liệu câu nằm trong SQLite, phủ đủ bảy cấp độ HSK 1–9.
- Mỗi cụm từ có `position` riêng; backend kiểm tra danh sách vị trí thay vì so sánh nội dung hiển thị.
- Một câu sai không bị khóa và không lộ đáp án, người dùng có thể sắp xếp lại.
- Khi câu đúng, giao diện hiển thị câu hoàn chỉnh, Pinyin và bản dịch theo tùy chọn phụ đề.
- Trạng thái bật/tắt Pinyin và tiếng Việt có hiệu lực ngay trong phiên.
- Kết quả từng lần thử và tổng kết phiên được lưu trong các bảng riêng, không thay đổi schema phiên Flashcard/Nối từ cũ.

## Trạng thái học

- `new`: chưa học.
- `learning`: đang học.
- `review`: cần ôn lại.
- `mastered`: đã thuộc.

Flashcard cập nhật tiến độ như sau:

- `forgot`: tăng số lần ôn và số lần sai, chuyển sang `review`.
- `hard`: tăng số lần ôn, chuyển sang `learning`.
- `remembered`: tăng số lần ôn và số lần đúng; chuyển sang `mastered` khi tổng số lần đúng đạt ba.

## Quy tắc nối từ

- Hai item được so sánh bằng `vocabulary_id`, không so sánh nội dung hiển thị.
- Cặp đúng bị khóa và không thể chọn lại.
- Cặp sai chỉ hiển thị phản hồi ngắn rồi bỏ chọn; không lộ đáp án.
- Độ chính xác bằng `correct_attempts / (correct_attempts + incorrect_attempts) × 100`.

## Kiến trúc

- Route chỉ nhận/validate request, gọi service và chuyển lỗi thành HTTP response.
- SQL và business logic nằm trong service; kết nối/schema nằm trong `database.py`.
- Frontend là một shell cố định. Page fragment được tải vào `main`, sidebar không render lại.
- Mọi REST request của frontend đi qua `frontend/js/api.js`.

## Ngoài phạm vi

HSK2+, audio, text-to-speech, speech-to-text, luyện/chấm phát âm, chatbot/AI, quiz, canvas viết chữ, authentication, cloud, WebSocket, Docker và mobile app.
