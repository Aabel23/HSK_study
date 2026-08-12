# Quy tắc làm việc trong repository

- Xem phiên bản hiện tại là baseline di sản cần được bảo tồn.
- Mọi thay đổi từ thời điểm này phải theo hướng chỉ bổ sung, không cắt giảm, trừ khi chủ dự án yêu cầu rõ ràng.
- Giữ tương thích ngược với API, schema database và dữ liệu tiến độ đã lưu.
- Không dùng migration phá hủy dữ liệu; thay đổi schema phải theo hướng bổ sung và giữ được dữ liệu cũ.
- Đọc `README.md` và `docs/SPEC.md` trước khi sửa code.
- Ứng dụng dùng dữ liệu HSK 1-9 đầy đủ (không chỉ HSK1).
- Mọi nội dung người học nhìn thấy phải bằng tiếng Việt. Không để nghĩa tiếng Anh
  lọt vào cột `meaning`; `meaning_en` chỉ là tham chiếu phụ có nhãn rõ ràng.
- Quy tắc nhận biết "đây có phải tiếng Việt thật không" nằm ở
  `scripts/meaning_quality.py` và được dùng chung bởi script dựng dữ liệu lẫn
  seeder — sửa ở đó, đừng sao chép sang nơi khác.
- Dữ liệu nghĩa tiếng Việt lấy từ CVDICT (CC BY-SA 4.0); giữ nguyên phần ghi
  công trong `README.md` khi cập nhật lại dữ liệu.
- Frontend là React 19 + TypeScript + Vite trong `frontend-web/`; không còn giao diện vanilla JS.
- `frontend-web/dist/` được commit vào git vì môi trường deploy (Render) không có Node — build lại và commit `dist/` sau khi sửa `frontend-web/src`.
- Không viết SQL trong route; business logic đặt trong service.
- Không hardcode dữ liệu học trong frontend.
- Chạy `pytest` sau khi sửa backend, `npm run build` sau khi sửa frontend-web.
- Không để test tác động database chính.
- Không thay đổi kiến trúc lớn nếu không cần thiết.
