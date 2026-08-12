<div align="center">

<img src="assets/app_icon.png" alt="Chinese Study" width="96" />

# Chinese Study

**Ứng dụng học tiếng Trung HSK 1–9 dành cho người Việt — offline-first, chạy hoàn toàn trên máy của bạn.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![Tests](https://img.shields.io/badge/tests-140%20passed-brightgreen)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

<!--
  Sau khi đẩy lên GitHub, bỏ comment dòng dưới và thay <OWNER>/<REPO>
  để hiện huy hiệu trạng thái CI thật:

[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml)
-->

</div>

---

## Giới thiệu

Chinese Study là ứng dụng web chạy local: một backend FastAPI phục vụ cả REST API lẫn giao diện React đã build, dữ liệu nằm trong SQLite ngay trên máy. Không cần tài khoản, không cần mạng (trừ khi phát âm lần đầu), không có dữ liệu nào rời khỏi máy bạn.

Toàn bộ giao diện và dữ liệu nghĩa đều bằng tiếng Việt.

## Tính năng

| Màn hình | Mô tả |
| --- | --- |
| **Tổng quan** | Bảng điều khiển: thống kê từ vựng, chuỗi ngày học, hoạt động gần đây. |
| **Ôn tập thông minh** | Lặp lại ngắt quãng (SRS) — hệ thống tự xếp lịch từ cần ôn. |
| **Từ vựng** | Tra cứu, tìm kiếm, lọc theo cấp độ HSK / chủ đề / trạng thái học. |
| **Flashcard** | Chọn số thẻ mỗi phiên (tới 200), lật thẻ, bật/tắt pinyin, tự đánh giá (`forgot` / `hard` / `remembered`). |
| **Nối từ** | Ghép Hán tự với nghĩa hoặc pinyin, hai chế độ chơi. |
| **Luyện câu** | Chọn số câu mỗi phiên (tới 200), sắp xếp các cụm Hán ngữ theo đúng thứ tự, bật/tắt pinyin và bản dịch. |
| **Luyện nghe** | Nghe phát âm (text-to-speech) rồi chọn đáp án đúng. |
| **Kiểm tra** | Trắc nghiệm tổng hợp nhiều dạng câu hỏi. |
| **Luyện viết** | Tập viết chữ Hán đúng thứ tự nét (hanzi-writer). |
| **Gõ & chính tả** | Luyện gõ pinyin và nghe-viết. |
| **Tiến độ** | Mức hoàn thành, từ cần ôn, từ đã thuộc, lịch sử phiên học. |
| **Thành tích** | Huy hiệu và cột mốc theo quá trình học. |
| **Cài đặt** | Tuỳ chọn hiển thị, sao lưu và khôi phục dữ liệu. |
| **Donate cho anh Ba** | Ủng hộ tác giả bằng mã VietQR qua PayOS (tuỳ chọn, cần cấu hình khoá). |

Dữ liệu học bao gồm bộ từ vựng **HSK 1, 2, 3, 4, 5, 6 và 7–9** (10.969 từ) cùng kho **218 câu luyện tập** phủ đủ bảy cấp độ, nằm trong [scripts/data/](scripts/data/) và được nạp vào SQLite khi khởi động lần đầu. Toàn bộ nghĩa của từ đều bằng tiếng Việt — xem [Nguồn dữ liệu](#nguồn-dữ-liệu).

## Công nghệ

| Lớp | Thành phần |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLite (chuẩn thư viện) |
| Phát âm | `edge-tts`, có cache audio trên đĩa |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, React Router, Recharts, Framer Motion |
| Đóng gói | PyInstaller (file `.exe` một tệp cho Windows) |
| Chất lượng | pytest, ruff, oxlint |

## Bắt đầu nhanh

Yêu cầu: **Python 3.11+** và **Node.js 20+** (chỉ cần Node khi muốn build lại giao diện React).

```bash
git clone https://github.com/<OWNER>/<REPO>.git
cd <REPO>

# 1. Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Giao diện React
cd frontend-web
npm ci
npm run build
cd ..

# 3. Chạy ứng dụng
python scripts/app_entry.py
```

Trình duyệt sẽ tự mở tại <http://127.0.0.1:8000>. Lần chạy đầu tiên mất vài giây để nạp dữ liệu HSK vào `data/chinese_study.db`.

> `frontend-web/dist` đã được commit sẵn nên bước build ở trên là tuỳ chọn — chỉ cần chạy lại khi bạn sửa code trong `frontend-web/src`. Nếu thư mục `dist` bị thiếu, backend trả lỗi 503 kèm hướng dẫn thay vì phục vụ giao diện rỗng.

### Chế độ phát triển

Chạy hai tiến trình song song để có hot-reload cả hai phía:

```bash
# Terminal 1 — API, tự nạp lại khi sửa Python
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Vite dev server, proxy /api sang cổng 8000
cd frontend-web && npm run dev
```

Giao diện dev chạy tại <http://127.0.0.1:5173>, tài liệu API tương tác tại <http://127.0.0.1:8000/api/docs>.

## Cấu hình

Mọi biến môi trường đều là tuỳ chọn và có mặc định an toàn cho máy cá nhân. Xem danh sách đầy đủ kèm giải thích trong [.env.example](.env.example) — các biến hay dùng nhất:

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `CHINESE_STUDY_PORT` | `8000` | Cổng HTTP. |
| `CHINESE_STUDY_DB` | `data/chinese_study.db` | Đường dẫn file SQLite. |
| `CHINESE_STUDY_SEED` | `1` | Nạp dữ liệu HSK khi khởi động. |
| `CHINESE_STUDY_DOCS` | `1` | Bật `/api/docs` và `/api/redoc`. |
| `CHINESE_STUDY_NO_BROWSER` | `0` | Đặt `1` để không tự mở trình duyệt. |
| `CHINESE_STUDY_LOG_LEVEL` | `INFO` | Mức log. |

## Kiểm thử và lint

```bash
pip install -r requirements-dev.txt

pytest                              # 140 test, dùng database tạm — không đụng dữ liệu thật
ruff check .                        # lint Python
cd frontend-web && npm run lint     # lint TypeScript/React
```

Mỗi test tự tạo bản sao SQLite riêng trong thư mục tạm, nên chạy test không bao giờ ảnh hưởng tiến độ học đã lưu.

## Đóng gói bản Windows

```bash
pip install -r requirements-build.txt
cd frontend-web && npm run build && cd ..
python scripts/build_exe.py
```

Kết quả là `ChineseStudy.exe` chạy độc lập, lưu dữ liệu vào `%LOCALAPPDATA%\ChineseStudy\`. Xem thêm [docs/WINDOWS_TRUST.md](docs/WINDOWS_TRUST.md) về cảnh báo SmartScreen và cách ký số.

## Cấu trúc dự án

```
backend/            FastAPI: route (HTTP) và service (business logic + SQL)
  routes/           Một module cho mỗi nhóm endpoint
  services/         Toàn bộ SQL và quy tắc nghiệp vụ
  database.py       Kết nối và schema SQLite
frontend-web/       Giao diện: React 19 + TypeScript + Vite (dist/ được commit sẵn)
scripts/            Điểm chạy, nạp dữ liệu, build .exe, dữ liệu HSK gốc
tests/              pytest cho toàn bộ backend
docs/               Đặc tả, tài liệu API và database
data/               Database SQLite và cache audio (không commit)
```

## Ủng hộ qua PayOS (tuỳ chọn)

Tab **Donate cho anh Ba** tạo mã VietQR qua [PayOS](https://my.payos.vn): người
ủng hộ quét bằng app ngân hàng, trang tự nhận biết khi tiền về. Tính năng tắt sẵn
và ứng dụng chạy bình thường khi không bật.

Để bật, tạo file `.env` ở thư mục gốc (file này nằm trong `.gitignore`):

```bash
PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...
CHINESE_STUDY_DONATE_NAME=anh Ba
```

> **Không bao giờ đặt khoá PayOS vào mã nguồn.** Ba khoá này cho phép tạo lệnh
> thanh toán vào tài khoản ngân hàng thật và xác thực chữ ký webhook — commit lên
> GitHub hoặc đóng gói vào file `.exe` phát hành đồng nghĩa với việc trao chúng
> cho bất kỳ ai. Backend chỉ đọc khoá từ biến môi trường, và endpoint
> `/api/donate/config` không trả khoá ra ngoài.

Mã QR được sinh ngay trên trình duyệt từ chuỗi VietQR, không gọi dịch vụ ảnh QR
bên ngoài, nên tab này vẫn đúng tinh thần offline-first của ứng dụng.

## Nguồn dữ liệu

| Nguồn | Dùng cho | Giấy phép |
| --- | --- | --- |
| [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) | Chữ Hán, pinyin, nghĩa tiếng Anh tham chiếu | CC BY-SA 4.0 |
| [CVDICT](https://github.com/ph0ngp/CVDICT) của Phong Phan | Nghĩa tiếng Việt của từ vựng HSK | CC BY-SA 4.0 |

Bộ dữ liệu HSK trong `scripts/data/` là tác phẩm phái sinh từ hai nguồn trên và
vì vậy được chia sẻ theo **CC BY-SA 4.0**; mã nguồn của ứng dụng vẫn theo giấy
phép MIT.

Muốn dựng lại bộ dữ liệu (ví dụ khi CVDICT có bản mới):

```bash
python scripts/translate_meanings.py --download          # cập nhật nghĩa tiếng Việt
python scripts/translate_meanings.py --download --check  # chỉ kiểm tra, không ghi
```

Script tự dịch những mục còn tiếng Anh, sửa chuỗi mojibake, dịch mã từ loại và
hạ chữ hoa ở các cách đọc bị CC-CEDICT viết hoa như danh từ riêng — nhưng không
bao giờ ghi đè nghĩa tiếng Việt đã được viết tay.

## Tài liệu

- [docs/SPEC.md](docs/SPEC.md) — đặc tả sản phẩm và quy tắc nghiệp vụ.
- [docs/API.md](docs/API.md) — tham chiếu REST API.
- [docs/DATABASE.md](docs/DATABASE.md) — schema SQLite.
- [docs/WINDOWS_TRUST.md](docs/WINDOWS_TRUST.md) — ký số và SmartScreen.
- [AGENTS.md](AGENTS.md) — quy tắc bắt buộc khi sửa đổi repository.

## Quy tắc đóng góp

Dự án theo chính sách **chỉ bổ sung, không cắt giảm**: không xoá chức năng, route, API, dữ liệu hay hành vi hiện có, và không dùng migration phá huỷ dữ liệu. Đọc [AGENTS.md](AGENTS.md) trước khi gửi thay đổi, và chạy `pytest` sau khi sửa backend.

## Giấy phép

Phát hành theo giấy phép [MIT](LICENSE).
