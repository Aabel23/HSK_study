# Chinese Study

Chinese Study là ứng dụng web chạy local giúp người Việt học và ghi nhớ bộ từ vựng HSK1. Ứng dụng dùng giao diện tiếng Việt, không yêu cầu đăng nhập và lưu tiến độ trực tiếp trong SQLite trên máy.

## Phạm vi MVP

- Bộ 150 từ HSK1 với chữ Hán, pinyin có dấu, nghĩa tiếng Việt, câu ví dụ và chủ đề.
- Tìm kiếm theo Hanzi, pinyin hoặc nghĩa; lọc theo chủ đề và trạng thái học.
- Flashcard lật thẻ, tự đánh giá `Chưa nhớ`, `Khó`, `Đã nhớ` và tự đánh dấu đã thuộc sau ba lần nhớ đúng.
- Nối từ theo hai chế độ Hanzi ↔ nghĩa tiếng Việt và Hanzi ↔ pinyin.
- Luyện đặt câu bằng cách sắp xếp các cụm Hán ngữ, có thể bật/tắt phụ đề Pinyin và nghĩa tiếng Việt.
- Dashboard và trang tiến độ dùng dữ liệu thật từ backend.
- Không có audio, giọng nói, quiz, AI, tài khoản hoặc dữ liệu HSK2 trở lên.

## Công nghệ

- Frontend: HTML5, CSS3 và JavaScript thuần.
- Backend: Python, FastAPI, Pydantic.
- Database: SQLite qua module chuẩn `sqlite3`.
- Kiểm thử: pytest và FastAPI TestClient.

## Cấu trúc thư mục

```text
ChineseStudy.exe        File duy nhất người dùng cần chạy trên Windows
backend/                FastAPI, route, service và database
frontend/               Shell, page fragment, CSS và JavaScript
scripts/                Công cụ nội bộ để seed dữ liệu và đóng gói EXE
data/                   SQLite local (tự tạo khi chạy)
tests/                  Kiểm thử API với database tạm
docs/                   Đặc tả, API và database
```

## Dành cho người dùng Windows

Nhấp đúp `ChineseStudy.exe` ngay trong thư mục chính. Ứng dụng không cần cài Python, không cần tạo venv, không cần Internet để setup và sẽ tự mở trình duyệt tại [http://127.0.0.1:8000](http://127.0.0.1:8000).

Giữ cửa sổ console của EXE trong lúc sử dụng; đóng cửa sổ đó để tắt ứng dụng. Dữ liệu học được lưu bền vững tại `%LOCALAPPDATA%\ChineseStudy\chinese_study.db`, vì vậy cập nhật file EXE không làm mất tiến độ.

## Đóng gói lại EXE dành cho phát triển

Các công cụ build nằm trong `scripts/` để thư mục chính gọn hơn:

```powershell
python -m pip install -r scripts/requirements-build.txt
python scripts/build_exe.py
```

Lệnh tạo hoặc cập nhật trực tiếp `ChineseStudy.exe` trong thư mục chính. `build/` chỉ là dữ liệu tạm và có thể xóa sau khi build thành công.

Không build Windows EXE trên macOS/Linux; mỗi hệ điều hành cần build artifact riêng.

## Công cụ phát triển

Cài dependency và chạy mã nguồn khi cần phát triển:

```powershell
python -m pip install -r scripts/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Seed dữ liệu

Có thể chủ động chạy:

```bash
python scripts/seed_data.py
```

Script dùng `hanzi` làm khóa duy nhất, có thể chạy nhiều lần mà không tạo bản ghi trùng và sẽ in số từ mới đã thêm.

## Chạy test

```bash
python -m pytest -q
```

Mỗi test dùng file SQLite trong thư mục tạm do pytest cấp, không ghi vào `data/chinese_study.db`.

## API docs

Sau khi chạy ứng dụng, mở [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) để xem OpenAPI/Swagger.

Các nhóm API chính:

- `/api/health`
- `/api/vocabulary`
- `/api/flashcard`
- `/api/matching`
- `/api/sentences`
- `/api/progress`
- `/api/dashboard`

Chi tiết request/response nằm trong [docs/API.md](docs/API.md).

## Database

Khi chạy từ mã nguồn, database mặc định nằm tại `data/chinese_study.db`. Bản EXE dùng `%LOCALAPPDATA%\ChineseStudy\chinese_study.db`. Có thể đặt biến môi trường `CHINESE_STUDY_DB` để dùng file khác, đặc biệt hữu ích cho kiểm thử. Schema được mô tả trong [docs/DATABASE.md](docs/DATABASE.md).

## Giới hạn MVP

- Tiến độ chỉ lưu local trên một thiết bị, không có tài khoản hoặc đồng bộ cloud.
- Quy tắc ghi nhớ là `correct_count >= 3`, không phải thuật toán spaced repetition.
- Giao diện tối ưu cho desktop và tablet; màn hình nhỏ vẫn dùng được nhưng không phải mobile app.
- Không có âm thanh, phát âm, nhận diện giọng nói hoặc nội dung do AI tạo.
