# Báo cáo Triển khai: Đính kèm Hình ảnh vào Live Chat & Rút gọn Phân trang

Hệ thống **Nội Thất Bảo Khang** đã hoàn thành đợt nâng cấp toàn diện về tính năng **Live Chat Trực Tuyến**, cho phép cả Khách hàng và Admin gửi nhận hình ảnh trực tiếp trong cuộc hội thoại.

---

## 🛠️ Chi tiết các hạng mục đã hoàn thành

### 1. Nâng cấp Live Chat gửi/nhận Hình ảnh
- **Cơ sở dữ liệu (`schema.sql` & `server.py`)**:
  - Bổ sung 2 cột mới trong bảng `chat_messages`: `message_type` (`NVARCHAR(20)` với ràng buộc check `'text'` / `'image'`) và `image_url` (`NVARCHAR(255)`).
  - Tự động chạy đoạn mã kiểm tra và chạy di chuyển cấu trúc dữ liệu (`ALTER TABLE`) khi server khởi động giúp dữ liệu cũ không bị ảnh hưởng.
  - Tự động khởi tạo thư mục lưu trữ file tĩnh `uploads/chat/` tại runtime.
- **Xử lý Backend (`server.py`)**:
  - API `/api/chat/send` được nâng cấp để xử lý song song cả yêu cầu JSON thuần túy (tin nhắn chữ) lẫn `multipart/form-data` (tin nhắn chứa file đính kèm hình ảnh).
  - Áp dụng các bước kiểm tra mở rộng: Chỉ cho phép các định dạng ảnh phổ biến (`png`, `jpg`, `jpeg`, `webp`, `gif`), khống chế kích thước file tối đa 5MB và đổi tên file ngẫu nhiên an toàn bằng UUID để tránh bị trùng tên hoặc khai thác lỗ hổng bảo mật.
  - Expose tuyến dẫn `/uploads/<path:filename>` để Flask phục vụ ảnh tĩnh trực tiếp từ thư mục uploads của dự án.
- **Giao diện Khách hàng (`base.html` - Live Chat Widget)**:
  - Thêm nút đính kèm biểu tượng 📷 (Camera) ngay bên trái khung nhập liệu.
  - Hỗ trợ đầy đủ 3 cơ chế tải ảnh: chọn từ thiết bị thông qua cửa sổ File, kéo thả file ảnh trực tiếp vào khung chat, hoặc nhấn tổ hợp phím Paste (Ctrl+V) khi đang sao chép ảnh trong clipboard.
  - Hiển thị hiệu ứng tải xoay tròn (`loading`) trong bóng hội thoại chat trong khi chờ upload.
  - Hình ảnh gửi lên hiển thị dưới dạng bong bóng ảnh bo góc tròn tinh tế, nhấn vào ảnh sẽ mở xem kích thước đầy đủ (Lightbox modal) mờ nền cực đẹp.
- **Giao diện Admin (`admin_chat.html` - Admin Chat Panel)**:
  - Bổ sung nút 📷 bên cạnh ô nhập để Admin gửi ảnh thực tế, báo giá, hoặc bản vẽ kỹ thuật cho khách hàng.
  - Hỗ trợ đầy đủ drag-and-drop kéo thả và copy-paste hình ảnh.
  - Cập nhật danh sách bên trái để hiển thị biểu tượng `📷 [Hình ảnh]` thay vì chuỗi rỗng khi khách hàng gửi ảnh cuối cùng.
  - Tích hợp Lightbox modal xem ảnh gốc tương tự phía client.

### 2. Phân trang rút gọn thông minh (Smart Pagination)
- **Thuật toán Backend**: Thêm hàm logic `make_pagination` giới hạn số lượng nút phân trang.
- **Giao diện**: Hiển thị dấu ba chấm `...` thay thế cho dãy số quá dài để tránh vỡ khung giao diện, ví dụ: `1 2 3 4 ... 44` hoặc `1 ... 9 10 11 ... 44`.

---

## 🚀 Hướng dẫn vận hành & kiểm thử

1. **Khởi động server**:
   ```bash
   python3 server.py
   ```
2. **Kiểm tra Live Chat phía Khách hàng**:
   - Truy cập trang chủ `http://localhost:8000`.
   - Bấm vào widget Live Chat góc dưới bên phải, nhập thông tin liên hệ để mở chat.
   - Thử click nút camera để chọn ảnh gửi lên, hoặc kéo thả ảnh từ màn hình vào khung chat, hoặc chụp màn hình rồi bấm Ctrl+V vào ô chat để gửi.
3. **Kiểm tra Live Chat phía Admin**:
   - Truy cập Bảng quản trị tại `http://localhost:8000/admin/chat` (Tài khoản mặc định: `admin` / mật khẩu `admin123`).
   - Nhấn vào phiên chat của khách hàng tương ứng. Bạn sẽ thấy ảnh khách hàng gửi xuất hiện.
   - Admin tiến hành đính kèm gửi lại ảnh hoặc xem ảnh bằng Lightbox.
