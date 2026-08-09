# Đặc tả MVP Chinese Study

## Chính sách bảo tồn

Phiên bản hiện tại là baseline di sản của dự án. Các phiên bản tiếp theo chỉ mở rộng theo hướng bổ sung và phải giữ tương thích ngược. Không loại bỏ chức năng, API, dữ liệu, giao diện hoặc hành vi hiện có và không thực hiện migration phá hủy dữ liệu nếu chưa có yêu cầu rõ ràng từ chủ dự án.

## Mục tiêu

Ứng dụng web local dành cho người Việt học từ vựng HSK1 bằng Flashcard và trò chơi nối từ. Giao diện dùng tiếng Việt, dữ liệu học và thống kê phải lấy từ backend.

## Các màn hình

1. **Tổng quan**: thống kê từ vựng, trạng thái học, kết quả nối từ và từ vừa học.
2. **Từ vựng HSK1**: danh sách có phân trang, tìm kiếm, lọc, chi tiết và cập nhật trạng thái.
3. **Flashcard**: tạo phiên 1–30 thẻ, lật thẻ, đánh giá và tổng kết.
4. **Nối từ**: sáu cặp mỗi vòng, hai chế độ `meaning` và `pinyin`, hai cột xáo độc lập.
5. **Luyện câu**: sắp xếp các cụm Hán ngữ theo đúng thứ tự, bật/tắt Pinyin và nghĩa tiếng Việt, lưu số lần đúng/sai.
6. **Tiến độ**: mức hoàn thành, từ cần ôn, từ đã thuộc và lịch sử phiên gần đây.

## Luyện câu

- Dữ liệu câu nằm trong SQLite và chỉ sử dụng cấu trúc cơ bản phù hợp HSK1.
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
