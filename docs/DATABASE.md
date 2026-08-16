# Database

SQLite mặc định khi chạy mã nguồn: `data/chinese_study.db`. Bản Windows EXE lưu tại `%LOCALAPPDATA%\ChineseStudy\chinese_study.db` để dữ liệu không nằm trong thư mục giải nén tạm của PyInstaller. Kết nối luôn bật `PRAGMA foreign_keys = ON` và dùng `sqlite3.Row`.

## `vocabulary`

Lưu 150 từ HSK1: Hanzi duy nhất, pinyin, nghĩa tiếng Việt, ba trường ví dụ, chủ đề và timestamps.

## `learning_progress`

Mỗi từ có tối đa một dòng tiến độ nhờ unique key `vocabulary_id`. Các bộ đếm gồm:

- `review_count`
- `correct_count`
- `incorrect_count`
- `last_reviewed_at`

`status` có CHECK constraint chỉ cho `new`, `learning`, `review`, `mastered`. Xóa từ sẽ cascade xóa tiến độ.

## `study_sessions`

Lưu phiên `flashcard` hoặc `matching`, thời gian bắt đầu/kết thúc và tổng số mục đúng/sai.

## `matching_attempts`

Lưu từng lần nối với `session_id`, `vocabulary_id`, chế độ và kết quả boolean. Nếu phiên bị xóa, `session_id` chuyển thành `NULL`; nếu từ bị xóa, attempt bị cascade xóa.

## `sentences`

Lưu câu HSK1, Pinyin, nghĩa tiếng Việt, chủ đề và hai mảng JSON song song gồm cụm Hán ngữ/Pinyin. `hanzi` là duy nhất để seed chạy lặp an toàn.

## `sentence_sessions`

Lưu phiên luyện đặt câu và các bộ đếm tổng số câu, câu đúng và lần thử sai. Bảng riêng giúp giữ nguyên CHECK constraint và hành vi của `study_sessions` di sản.

## `sentence_attempts`

Lưu thứ tự `position` mà người dùng gửi và kết quả kiểm tra từ backend. Xóa phiên hoặc câu sẽ cascade xóa attempt tương ứng.

## Lớp chữ Hán

Bốn bảng đặt dưới lớp từ vựng, phục vụ màn hình **Giải mã Hán-Việt**. Nội dung
ship trong `scripts/data/characters.json` (dựng bởi `scripts/build_characters.py`).

### `characters`

Khoá chính là chính chữ Hán. Ngoài `pinyin`, `han_viet`, `meaning_vi`,
`stroke_count`, `radicals_json` và `mnemonic_vi`, bảng còn giữ hai cột **suy ra
lúc seed** chứ không lấy từ nguồn:

- `word_count` — số từ trong kho được dựng từ chữ này, để "chữ nào mở khoá nhiều
  từ nhất" chỉ là một `ORDER BY`.
- `hsk_level` — cấp HSK **thấp nhất** mà chữ xuất hiện, tức thứ tự nên học.

`han_viet_source` ghi lại nguồn của cách đọc, để giao diện nói rõ mức độ chắc
chắn thay vì im lặng tin tưởng. `radical_source` làm việc tương tự cho phần
components: `dataset` là chiết tự đầy đủ do người viết (659 chữ), `kangxi` là bộ
thủ chính suy từ Unihan (số còn lại). Một thành phần kèm chú giải kém xa một bản
chiết tự đầy đủ nhưng hơn hẳn một khung trống, nên nó được hiện ra và **được ghi
nhãn đúng là bộ thủ** chứ không đội lốt chiết tự.

### `radicals`

414 bộ thủ kèm tên, nghĩa và mẹo nhớ tiếng Việt.

### `word_characters`

Chỉ mục từ ↔ chữ (`vocabulary_id`, `position`, `hanzi`). Cố tình phi chuẩn hoá:
"mọi từ chứa 学" là truy vấn chạy mỗi lần gõ phím, và `LIKE '%学%'` trên 11 nghìn
dòng thì không dùng được index. Bảng này được dựng lại toàn bộ mỗi lần seed.

### `character_progress`, `decode_sessions`, `decode_attempts`

`character_progress` mang cả lịch ôn riêng cho chữ (`ease_factor`,
`interval_days`, `repetitions`, `lapses`, `due_at` — thêm bằng ALTER TABLE nên
database cũ nâng cấp tại chỗ). Chữ là đơn vị đáng lên lịch nhất trong ứng dụng
này: khác với từ, một chữ nhớ được hôm nay còn dùng được cho những từ chưa bao
giờ học. Trước khi có lịch, bảng chỉ đếm đúng/sai và bài luyện rút ngẫu nhiên —
chữ vừa quên ba mươi giây trước không hề dễ gặp lại hơn chữ nào khác.

Tiến độ và lịch sử luyện tập của người học, tách khỏi nội dung — cùng cách chia
mà `grammar_points` / `grammar_progress` đang dùng — nên seed lại nội dung mới
không bao giờ đụng vào lịch sử.

Cột `vocabulary.han_viet` là cách đọc Hán-Việt của **cả từ** (图书馆 → "đồ thư
quán"). Chỉ được điền khi *mọi* chữ trong từ đều có cách đọc: một bản phiên âm
dở dang như "đồ thư ?" đúng là trường hợp người học dễ tin nhầm nhất.

## `word_examples`

Câu ví dụ cho từng từ. Chỉ 150/10.969 từ có sẵn ví dụ khi ship, nên seeder đánh
chỉ mục **kho câu sẵn có của chính dự án** thay vì nhập một corpus mà không ai ở
đây đọc được phần tiếng Việt: kho luyện câu (`sentences`), ví dụ trong từng bài
ngữ pháp, và đề nói HSKK — 483 câu đều có đủ Hán tự, pinyin và bản dịch tiếng
Việt do người viết cho chính ứng dụng này. Kết quả: **1.177 từ (10,7%)** có ví dụ.

Ba quy tắc đáng nhớ, vì bỏ quy tắc nào cũng sinh ra lỗi hiển thị thật:

- **Bỏ đề nói mở.** Các mục có `hints` là đề tả tranh, `vi` của chúng là gợi ý
  dàn ý chứ không phải bản dịch của `hanzi` bên cạnh — dùng làm ví dụ sẽ hiện
  bản dịch lệch hẳn.
- **Khử trùng theo nội dung câu.** Ba nguồn có chồng lấn (你叫什么名字？ nằm ở cả
  kho câu lẫn đề HSKK), nếu không khử thì cùng một câu hiện hai lần dưới một từ.
- **Từ một chữ bị siết chặt.** 的 xuất hiện trong gần như mọi câu, nên từ một chữ
  chỉ lấy tối đa 2 ví dụ và chỉ từ câu ngắn; từ nhiều chữ lấy tối đa 4.

Bảng là dữ liệu suy ra, dựng lại từ đầu mỗi lần seed, không chứa gì của người học.

## Khởi tạo và seed

`backend/database.py` tự tạo thư mục, file và bảng nếu thiếu. `scripts/seed_data.py` dùng `INSERT ... ON CONFLICT(hanzi) DO NOTHING`, sau đó bổ sung dòng tiến độ bằng `INSERT OR IGNORE`. Seed không reset hoặc xóa dữ liệu học cũ.

Test đặt `CHINESE_STUDY_DB` sang đường dẫn trong `tmp_path`, vì vậy không tác động database chính.
