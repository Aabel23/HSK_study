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
chắn thay vì im lặng tin tưởng.

### `radicals`

414 bộ thủ kèm tên, nghĩa và mẹo nhớ tiếng Việt.

### `word_characters`

Chỉ mục từ ↔ chữ (`vocabulary_id`, `position`, `hanzi`). Cố tình phi chuẩn hoá:
"mọi từ chứa 学" là truy vấn chạy mỗi lần gõ phím, và `LIKE '%学%'` trên 11 nghìn
dòng thì không dùng được index. Bảng này được dựng lại toàn bộ mỗi lần seed.

### `character_progress`, `decode_sessions`, `decode_attempts`

Tiến độ và lịch sử luyện tập của người học, tách khỏi nội dung — cùng cách chia
mà `grammar_points` / `grammar_progress` đang dùng — nên seed lại nội dung mới
không bao giờ đụng vào lịch sử.

Cột `vocabulary.han_viet` là cách đọc Hán-Việt của **cả từ** (图书馆 → "đồ thư
quán"). Chỉ được điền khi *mọi* chữ trong từ đều có cách đọc: một bản phiên âm
dở dang như "đồ thư ?" đúng là trường hợp người học dễ tin nhầm nhất.

## Khởi tạo và seed

`backend/database.py` tự tạo thư mục, file và bảng nếu thiếu. `scripts/seed_data.py` dùng `INSERT ... ON CONFLICT(hanzi) DO NOTHING`, sau đó bổ sung dòng tiến độ bằng `INSERT OR IGNORE`. Seed không reset hoặc xóa dữ liệu học cũ.

Test đặt `CHINESE_STUDY_DB` sang đường dẫn trong `tmp_path`, vì vậy không tác động database chính.
