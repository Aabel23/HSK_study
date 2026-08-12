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

- `POST /matching/session` — body `{ "mode": "meaning", "count": 6 }`.
- `POST /matching/attempt` — body `{ "session_id": 2, "vocabulary_id": 1, "mode": "meaning", "is_correct": true }`.
- `POST /matching/session/{session_id}/complete` — body `{ "total_items": 6, "correct_items": 6, "incorrect_items": 2 }`.

`mode` chỉ nhận `meaning` hoặc `pinyin`. Hai danh sách trả về chứa cùng tập `vocabulary_id` nhưng khác thứ tự.

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
