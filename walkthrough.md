# Báo cáo Triển khai: Đính kèm Hình ảnh, Xóa Hội Thoại & Video Công Trình Thực Tế

Hệ thống **Nội Thất Bảo Khang** đã hoàn thành đợt nâng cấp toàn diện bao gồm:
1. **Live Chat Hình Ảnh**: Gửi/nhận ảnh trực quan, phóng to Lightbox.
2. **Quản Lý Đoạn Chat**: Xóa lịch sử chat phía Khách hàng (Trò chuyện mới) và phía Admin (Xóa cuộc hội thoại).
3. **Mục Video Công Trình Thực Tế**: Tự động quét, hiển thị danh sách video, phân trang tối đa 12 video và phát video bằng Lightbox.
4. **Tối ưu hóa giao diện di động & Khắc phục lỗi**:
   - Sửa lỗi đè chữ vào icon ở ô nhập liệu đăng nhập/đăng ký.
   - Sửa lỗi hiển thị nút hamburger menu (3 gạch) trên di động.
   - Sửa lỗi hiển thị nút "Tiếp tục mua sắm" bị màu trắng trên nền trắng ở giỏ hàng trống.
   - Bổ sung cấu hình email `noithatbaokhang@gmail.com` đồng bộ hiển thị lên website.

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

### 2. Tính năng Xóa Hội Thoại (Chat Management)
- **Cổng API Backend `/api/chat/delete`**:
  - Nhận yêu cầu `DELETE` hoặc `POST` chứa `session_id`.
  - Thực hiện truy vấn xóa toàn bộ các bản ghi tin nhắn tương ứng với `session_id` đó trong bảng `chat_messages`.
  - Đồng thời tự động quét và xóa sạch các file ảnh vật lý tương ứng trong thư mục `uploads/chat/` của phiên chat đó để tránh lãng phí dung lượng lưu trữ trên ổ đĩa.
  - Xóa bỏ các biến phiên làm việc (`chat_session_id`, `chat_customer_name`, `chat_customer_phone`) trong `session` của Flask nếu là khách tự xóa.
- **Giao diện Admin (`admin_chat.html`)**:
  - Tích hợp biểu tượng Thùng rác 🗑️ bên phải mỗi cuộc hội thoại trong danh sách khách hàng.
  - Khi click: Hiển thị hộp thoại xác nhận. Nếu đồng ý sẽ gọi API `/api/chat/delete`, xóa phiên đang active (nếu trùng) và tải lại danh sách hội thoại ngay lập tức.
- **Giao diện Khách hàng (`base.html` - Live Chat Widget)**:
  - Thêm nút biểu tượng Thùng rác 🗑️ trên Header của hộp thoại chat khi cuộc trò chuyện đang diễn ra.
  - Khách hàng bấm nút này để dọn dẹp lịch sử cũ, hệ thống xóa session local và bắt đầu cuộc trò chuyện mới từ đầu (hiện lại form điền Họ tên & SĐT).

### 3. Mục "Video Công Trình Thực Tế"
- **Định nghĩa bảng CSDL & Tự động quét seeding**:
  - Tạo bảng `construction_videos` chứa `video_path`, `video_name` và `created_at`.
  - Thiết lập cơ chế tự động quét thư mục `data/thicongthucte/` khi ứng dụng khởi chạy. Mọi file `.mp4`, `.webm` mới thêm vào thư mục này sẽ được tự động đồng bộ hóa vào database.
- **Trang hiển thị `templates/construction_videos.html`**:
  - Định tuyến tại `/cong-trinh-thuc-te`.
  - Thiết kế Liquid Glass / Apple Style sang trọng: Thẻ video kính mờ bo tròn góc rộng, hiệu ứng hover chuyển động mượt mà.
  - Tích hợp xem trực tiếp tại chỗ bằng HTML5 Video Player hoặc click nút phóng to để mở Trình xem Video Lightbox Modal khổ lớn mờ nền ấn tượng.
- **Quy tắc phân trang**:
  - Phân trang hiển thị chính xác tối đa **12 video trên một trang**, hỗ trợ thanh điều hướng thông minh rút gọn dạng dấu ba chấm `...` cực đẹp.

### 4. Tối ưu hóa UI/UX di động & Khắc phục lỗi
- **Sửa lỗi đè chữ vào icon tại trang Đăng nhập / Đăng ký**:
  - Cập nhật quy tắc ghi đè padding input trên di động trong `style.css` từ `input` thành `input:not(.pl-10)`. Nhờ đó, các input có icon (như tài khoản, mật khẩu, số điện thoại) giữ nguyên được khoảng cách đệm `pl-10` và không bị đè lên icon tuyệt đối.
- **Sửa lỗi ẩn dấu 3 gạch (Menu di động)**:
  - Ẩn nút "Đăng nhập" ở thanh Header chính khi xem trên di động (`hidden md:block`), thay vào đó tích hợp khối Đăng nhập / Thông tin cá nhân nằm gọn gàng ở **chân của Drawer Menu di động**.
  - Nhờ giảm tải thành phần thừa trên thanh Header di động, nút dấu 3 gạch (Hamburger Menu) đã hiển thị đầy đủ, ngay ngắn cạnh Giỏ hàng.
- **Sửa lỗi nút Tiếp tục mua sắm ở Giỏ hàng trống**:
  - Khắc phục lỗi chính tả trong class màu nền của nút từ `bg-amber-755` thành `bg-amber-800` (màu hợp lệ trong Tailwind CSS). Nút mua sắm giờ có nền màu hổ phách sang trọng nổi bật thay vì nền trắng tàng hình.
- **Đồng bộ Email thông tin liên lạc**:
  - Đưa cấu hình `email_receiver` (`noithatbaokhang@gmail.com`) vào bộ context processor của Flask để đồng bộ hóa hiển thị địa chỉ email liên hệ trên toàn bộ hệ thống (Thanh Topbar, chân trang Footer).

---

## 🚀 Hướng dẫn vận hành & kiểm thử

1. **Khởi động server**:
   ```bash
   python3 server.py
   ```
2. **Kiểm thử Xóa Chat**:
   - Gửi tin nhắn và ảnh từ phía khách hàng và admin.
   - Phía admin: Bấm biểu tượng 🗑️ bên phải danh sách khách để xóa.
   - Phía khách hàng: Bấm biểu tượng 🗑️ trên header khung chat để xóa lịch sử và bắt đầu hội thoại mới.
3. **Kiểm thử Trang Video**:
   - Truy cập `http://localhost:8000/cong-trinh-thuc-te` hoặc bấm liên kết **Thực Tế** trên Menu.
   - Trải nghiệm xem video trực tiếp hoặc mở phóng to Lightbox.
