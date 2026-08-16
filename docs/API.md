# REST API

Base URL: `http://127.0.0.1:8000/api`

Lỗi validation trả HTTP `422`; tài nguyên không tồn tại trả `404`; thao tác không phù hợp trạng thái tài nguyên trả `409`.

## Health

- `GET /health` — trạng thái dịch vụ.

## Vocabulary

- `GET /vocabulary?search=&topic=&status=&limit=20&offset=0` — danh sách và tổng số kết quả.
- `GET /vocabulary/topics` — danh sách chủ đề hiện có.
- `GET /vocabulary/random?count=10&status=` — từ ngẫu nhiên.
- `GET /vocabulary/{vocabulary_id}` — chi tiết từ và tiến độ.

Riêng `GET /vocabulary/{id}` trả thêm `examples`: danh sách câu ví dụ, mỗi câu
gồm `hanzi`, `pinyin`, `meaning_vi`, `source` (`sentences` | `grammar` | `hskk`)
và `source_ref`. Endpoint danh sách **không** kèm trường này — mỗi trang hiển
thị hai chục thẻ và không có chỗ cho câu ví dụ, nên join thêm bảng cho mỗi dòng
chỉ tốn truy vấn mà không đổi được gì.

## Progress

- `GET /progress` — tổng hợp trạng thái, phần trăm hoàn thành, danh sách và phiên gần đây.
- `GET /progress/{vocabulary_id}` — tiến độ một từ.
- `POST /progress/status` — body `{ "vocabulary_id": 1, "status": "review" }`.

## Flashcard

- `POST /flashcard/session` — body `{ "count": 10, "include_mastered": false, "hsk_level": null }`.
- `POST /flashcard/review` — body `{ "session_id": 1, "vocabulary_id": 1, "result": "remembered" }`.
- `POST /flashcard/session/{session_id}/complete` — body `{ "total_items": 10, "correct_items": 6, "incorrect_items": 4 }`.

`result` chỉ nhận `forgot`, `hard`, `remembered`. `count` nhận 1–200 để hỗ trợ
những phiên dài liên tục; phiên chỉ chứa tối đa số từ thực có sau khi lọc.
`hsk_level` nhận `1`–`6`, `7-9` hoặc `null` (mọi cấp độ).

## Matching

- `POST /matching/session` — body `{ "mode": "meaning", "count": 6, "hsk_level": "1" }`.
  `hsk_level` là tuỳ chọn; bỏ trống thì rút từ toàn bộ kho như trước.
- `POST /matching/attempt` — body `{ "session_id": 2, "vocabulary_id": 1, "mode": "meaning", "is_correct": true }`.
- `POST /matching/session/{session_id}/complete` — body `{ "total_items": 6, "correct_items": 6, "incorrect_items": 2 }`.

`mode` chỉ nhận `meaning` hoặc `pinyin`. Hai danh sách trả về chứa cùng tập `vocabulary_id` nhưng khác thứ tự.

Ở chế độ `meaning`, các từ được chọn sao cho nghĩa của chúng dài xấp xỉ nhau: ô
ghi "ăn" nằm cạnh ô dài bốn trăm ký tự thì nhìn là nối được, không cần biết
nghĩa. Xem `docs/SPEC.md` mục "Độ dài đáp án trắc nghiệm".

## Characters (`/api/characters`)

Lớp chữ Hán dưới lớp từ vựng, phục vụ màn hình Giải mã Hán-Việt.

### Tra cứu

- `GET /characters` — danh sách, phân trang. Query: `search` (khớp chữ Hán, âm
  Hán-Việt, pinyin hoặc nghĩa), `hsk_level`, `sort`, `limit`, `offset`,
  `in_bank_only`. `sort` nhận `reach` (mặc định — nhiều từ mở khoá nhất trước),
  `strokes`, `level`, `han_viet`.
- `GET /characters/{hanzi}` — một chữ, kèm `radical_details` (bộ thủ đã tra
  nghĩa) và `words` (họ từ, tối đa 60 từ, xếp theo cấp HSK rồi độ dài).
- `GET /characters/stats` — tổng số chữ, số chữ đã nắm, số từ **giải mã được**
  và số từ **đã mở khoá** nhờ những chữ đã nắm.
- `POST /characters/{hanzi}/status` — body `{ "status": "mastered" }`. Nhận
  `new`, `learning` hoặc `mastered`.

### Luyện giải mã

- `GET /characters/modes` — ba chế độ kèm nhãn tiếng Việt.
- `POST /characters/drill/session` — body
  `{ "mode": "han_viet_to_meaning", "count": 10, "hsk_level": "3" }`.
- `GET /characters/drill/session/{id}/next` — một câu hỏi: từ, pinyin, âm
  Hán-Việt cả từ, `breakdown` (một mục cho mỗi chữ, đúng thứ tự trong từ) và
  bốn `options`.
- `POST /characters/drill/attempt` — body
  `{ "session_id": 1, "word": "图书馆", "is_correct": true, "vocabulary_id": 42 }`.
  Ghi công cho **từng chữ** trong từ, không phải cho từ.
- `POST /characters/drill/session/{id}/complete` — như các phiên khác.
- `GET /characters/drill/stats` — số phiên, số câu đúng/sai, độ chính xác.

Đề ưu tiên rút những từ người học chưa mở bao giờ. Các lựa chọn được chọn cho
cân độ dài (hoặc cân số âm tiết, với đáp án là âm Hán-Việt).

## Dashboard

- `GET /dashboard` — thống kê từ vựng, kết quả nối từ và hoạt động gần đây.

## Sentences

- `GET /sentences/topics` — danh sách chủ đề câu.
- `GET /sentences/stats` — số phiên, lần đúng/sai và độ chính xác.
- `GET /sentences/levels` — số câu và độ dài theo từng cấp độ HSK.
- `POST /sentences/session` — body `{ "count": 10, "topic": null, "hsk_level": null, "max_tokens": null }`; trả câu và các token Hán ngữ đã xáo trộn.
- `POST /sentences/attempt` — body `{ "session_id": 1, "sentence_id": 1, "ordered_positions": [0, 1, 2] }`.
- `POST /sentences/session/{session_id}/complete` — body `{ "total_items": 10, "correct_items": 10, "incorrect_items": 2 }`.

Frontend gửi thứ tự `position`; backend tự quyết định kết quả đúng/sai. Mỗi vị trí phải xuất hiện đúng một lần.
`count` nhận 1–200; nếu bộ lọc không còn câu nào, endpoint trả `409` thay vì một phiên rỗng.

## Thi thử HSK (`/api/hskk`)

Một đề gồm hai nửa: **phần đọc** (阅读, theo cấu trúc đề HSK thật) và **phần nói**
(theo cấu trúc HSKK). Mỗi nửa chấm riêng trên thang 100, điểm cuối là trung bình
cộng hai nửa.

### Phần đọc

Ngân hàng đề ở `scripts/data/hsk_reading_bank.json`, phục vụ bởi
`backend/services/reading_service.py`. Dạng câu hỏi theo đúng đề thật:

| Cấp | Phần 1 | Phần 2 | Phần 3 |
|---|---|---|---|
| Sơ cấp (HSK 2) | 判断对错 — xét đúng/sai | 选词填空 — chọn từ điền vào câu | 对话选择 — đọc hội thoại chọn đáp án |
| Trung cấp (HSK 4) | 选词填空 | 排列顺序 — sắp xếp vế câu | 阅读理解 — đọc đoạn văn chọn đáp án |

Hai quy tắc quan trọng:

- **Đáp án không bao giờ rời khỏi server.** Đề gửi cho trình duyệt đã bị lược bỏ
  `answer` và `explanation_vi`; client chỉ gửi lên thứ thí sinh chọn, còn
  `reading_service.check_answer()` mới là nơi quyết định đúng/sai. Cách cũ gửi
  kèm id đáp án đúng, tức là mở devtools là thấy bài giải.
- **Bảng từ của 选词填空 luôn thừa đúng một từ**, như đề thật, để chỗ trống cuối
  cùng vẫn là một lựa chọn thật sự. Các phương án và các vế câu cũng được xáo
  lại mỗi lần tạo đề.

- `GET /hskk/levels` — cấu trúc chính thức của `beginner` (Sơ cấp) và `intermediate` (Trung cấp): số câu, điểm mỗi câu, thời gian trả lời, thời gian chuẩn bị, phần trắc nghiệm và cờ `ai_grading`. Không kèm câu hỏi nên gọi được ở màn hình giới thiệu.
- `GET /hskk/grading` — `{ "ai_grading": true|false }`, cho giao diện biết có chấm bằng AI được không.
- `GET /hskk/stats` — số lượt đã nộp, điểm cao nhất/trung bình/gần nhất và các lượt gần đây.
- `POST /hskk/session` — body `{ "exam_level": "beginner" }`; trả `written` (câu trắc nghiệm) và `parts` (phần nói). Câu của phần "nghe rồi nhắc lại"/"nghe rồi trả lời" có `audio_text`; phần đọc đề trả `null` để giao diện không lộ lời đề trước khi thí sinh nghe.
- `POST /hskk/reading` — body `{ "session_id": 1, "question_index": 0, "question_id": "br1-03", "answer": … }`. `answer` là `true`/`false` với 判断对错, chuỗi chữ Hán với các dạng chọn đáp án, và **mảng các vế theo thứ tự đã sắp** với 排列顺序. Trả về `is_correct`, `correct_answer` và `explanation_vi`; mỗi câu đúng được `100 / số câu` điểm.
- `POST /hskk/answer` — body `{ "session_id": 1, "part": 1, "question_index": 0, "question_id": "b1-01", "self_rating": "good", "spoken_seconds": 12 }`. Dùng khi tự chấm.
- `POST /hskk/grade` — chấm bằng AI. Body gồm `transcript` (log lời nói do trình duyệt nhận dạng) và/hoặc `audio_base64` (WAV 16 kHz mono); thiếu cả hai thì trả `409`. Trả điểm, bản gỡ băng, nhận xét tiếng Việt và ba điểm thành phần (phát âm / nội dung / trôi chảy).
- `POST /hskk/session/{session_id}/complete` — trả điểm hai nửa, `overall_percent`, đạt/chưa đạt và điểm từng phần.

Gửi lại cùng một `(session_id, part, question_index)` ở bất kỳ endpoint nào ở trên
sẽ **ghi đè** kết quả cũ chứ không cộng thêm. Backend giữ toàn bộ phép tính điểm.

Khi tự chấm: `good` = 100% điểm câu, `ok` = 60%, `bad` = 20%, `skipped` = 0. Khi
AI chấm, điểm phần trăm Gemini trả về được nhân với điểm tối đa của câu, và được
quy về cùng bốn mức trên để thống kê không phải phân biệt hai nguồn chấm.

Ngân hàng đề là file tĩnh `scripts/data/hskk_bank.json` (đi kèm bản `.exe`); mỗi
lượt thi bốc ngẫu nhiên một tập con của từng pool nên hai lần thi không trùng đề.
Trung cấp bỏ phần 2 (nhìn tranh kể chuyện) vì chưa có bộ tranh — điểm dồn sang
phần nêu quan điểm, và `skipped_parts` nói rõ lý do để giao diện hiển thị.

### Chấm điểm bằng Gemini

Bài nói không thể chấm bằng so khớp chuỗi. Trình duyệt vừa ghi âm vừa chuyển lời
nói thành chữ (Web Speech API, `zh-CN`); **log văn bản đó** là thứ được gửi tới
Gemini kèm một prompt có thang điểm riêng cho từng dạng đề (nhắc lại / trả lời /
nói theo đề / nêu quan điểm). Đoạn ghi âm chỉ gửi kèm khi bài dưới 150 giây, để
chấm thêm phần phát âm. Toàn bộ prompt nằm ở `_GRADING_PROMPTS` trong
`backend/services/hskk_service.py`, và `build_grading_prompt()` ráp chúng lại —
hàm này không có tác dụng phụ nên test kiểm tra được đúng chuỗi gửi đi.

Khi chỉ có log văn bản mà không có ghi âm, prompt nói thẳng với model rằng nó
**không** được chấm thanh điệu như thể đã nghe giọng thí sinh — nếu không, model
sẽ bịa ra lỗi phát âm từ một bản gỡ băng đã được máy chuẩn hoá.

- Khoá đọc từ biến môi trường `GEMINI_API_KEY`, **không bao giờ** commit hay đóng
  gói vào `.exe`. `GEMINI_MODEL` mặc định `gemini-flash-latest` (alias, không ghim số phiên bản vì Google có gỡ model cũ).
- AI Studio cấp khoá ở nhiều dạng (`AIza…` lẫn `AQ.…`) và cả hai đều là API key,
  gửi bằng header `x-goog-api-key`; chỉ OAuth access token (`ya29.…`) mới dùng
  `Authorization: Bearer`. Đoán sai dạng khoá thì client tự thử lại bằng header
  còn lại trước khi báo lỗi, nên khoá hợp lệ không bao giờ bị báo nhầm là sai.
- Chưa cấu hình khoá → `/hskk/grade` trả `409` kèm hướng dẫn, và bài thi tự
  chuyển sang chế độ tự chấm. Khoá sai/hết hạn → `409` nói rõ cần tạo khoá mới.
- **Lưu ý riêng tư**: khi bật chấm AI, đoạn ghi âm được gửi ra dịch vụ ngoài. Khi
  tắt (không có khoá), bản ghi chỉ nằm trong trình duyệt.
- Test không bao giờ gọi API thật: fixture `_no_live_ai_credentials` trong
  `tests/conftest.py` xoá khoá, test nào cần thì stub `gemini_service.generate_json`.

## Donate (PayOS)

- `GET /donate/config` — `{ enabled, recipient, min_amount, max_amount, suggested_amounts, currency }`. `enabled` là `false` khi chưa có khoá PayOS; endpoint này **không bao giờ** trả khoá.
- `GET /donate/summary` — tổng số tiền đã nhận, số lượt và thời điểm gần nhất.
- `GET /donate/recent?limit=10` — các lượt ủng hộ gần đây.
- `POST /donate/session` — body `{ "amount": 50000, "message": "", "donor_name": "" }`; trả `qr_code` (chuỗi VietQR) và `checkout_url`.
- `GET /donate/status/{order_code}` — hỏi PayOS trạng thái và lưu lại. Đơn đã kết thúc không hỏi lại.
- `POST /donate/cancel/{order_code}` — huỷ một đơn còn `pending`.
- `POST /donate/webhook` — PayOS gọi khi chuyển khoản thành công; chữ ký được xác thực bằng checksum key.

Khi thiếu khoá PayOS, mọi endpoint cần gọi ra ngoài trả `409` kèm hướng dẫn cấu
hình; `config`, `summary` và `recent` vẫn hoạt động bình thường. Ứng dụng thường
chạy ở `127.0.0.1` nên PayOS không gọi webhook tới được — giao diện chủ động poll
`status` mỗi 3 giây, webhook chỉ là đường dự phòng khi deploy công khai.

OpenAPI tương tác có tại `/docs` khi server đang chạy.
