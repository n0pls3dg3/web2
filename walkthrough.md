# Hướng dẫn Kiểm thử & Vận hành Hệ thống - Python Flask & MS SQL

Hệ thống bán hàng **Nội Thất Bảo Khang** đã được chuyển đổi hoàn toàn và thành công sang kiến trúc **Python Flask & Microsoft SQL Server (MS SQL)** để tương thích 100% với máy chủ thực tế của bạn.

---

## 📁 Cấu trúc thư mục mới (Python Flask)

```text
/media/khang/data/web2/
├── server.py             # File chạy chính của ứng dụng Flask (chứa kết nối, định tuyến, quét ảnh & tự động import)
├── mail_helper.py        # Module gửi email thông báo đơn hàng dùng thư viện chuẩn Python (smtplib, email.mime)
├── schema.sql            # Bản thiết kế CSDL bằng SQL Server T-SQL (dành cho DBeaver/SSMS tham khảo)
├── data/                 # Thư mục chứa hình ảnh sản phẩm gốc
├── static/               # Thư mục chứa tài nguyên tĩnh
│   └── style.css         # CSS tùy chỉnh (Floating actions, glassmorphism, animations)
└── templates/            # Thư mục chứa các mẫu giao diện Jinja2
    ├── base.html         # Giao diện khung chính (Header, Footer, Flash alerts, Hotline/Zalo Sticky Widget)
    ├── index.html        # Trang chủ
    ├── category.html     # Catalog phân trang (10 SP/trang) và bộ lọc
    ├── detail.html       # Chi tiết sản phẩm & Form đặt nhanh
    ├── cart.html         # Giỏ hàng
    ├── checkout.html     # Xác nhận đặt hàng
    ├── login.html        # Đăng nhập
    ├── register.html     # Đăng ký
    ├── admin_index.html  # Admin Dashboard
    ├── admin_orders.html # Admin quản lý đơn hàng
    ├── admin_products.html# Admin quản lý sản phẩm (Có form upload nhiều ảnh)
    └── admin_users.html  # Admin xem khách hàng đăng ký
```

---

## 🚀 Hướng dẫn Chạy & Kiểm thử ứng dụng

### Bước 1: Kích hoạt môi trường ảo Python
Mở Terminal tại thư mục dự án `/media/khang/data/web2 ` và chạy các lệnh:
```bash
# 1. Tạo môi trường ảo (nếu chưa có)
python3 -m venv .venv

# 2. Kích hoạt môi trường ảo
source .venv/bin/activate

# 3. Cài đặt các thư viện cần thiết (Flask và pymssql)
pip install Flask pymssql
```

### Bước 2: Chạy Server
Mở dịch vụ Microsoft SQL Server trên máy của bạn (hiện tại cổng `1433` đang mở sẵn). Chạy lệnh khởi động website:
```bash
python3 server.py
```

### Bước 3: Tự động khởi tạo & Import dữ liệu mẫu
Khi lệnh `python3 server.py` chạy lên:
1. **Kiểm tra & Tạo database**: Server sẽ tự động kết nối qua tài khoản `sa` / `ntBK01011227` đã được cấu hình trong `server.py`, tự tạo cơ sở dữ liệu `noithatbaokhang_db` cùng tất cả các bảng nếu chúng chưa tồn tại.
2. **Tự động quét & Import ảnh mẫu**: Nếu bảng `Products` trống, hệ thống sẽ tự động quét đệ quy thư mục `data/` trong dự án để import sản phẩm, phân tích gán mã, gán giá Sale **3.800.000đ** cho tủ sale và nạp ảnh tương ứng.
3. **Tạo tài khoản quản trị**: Tài khoản admin được tự động thêm vào với mật khẩu băm SHA256 bảo mật:
   - **Tên đăng nhập**: `admin`
   - **Mật khẩu**: `admin123`

---

## 🛠️ Trải nghiệm các luồng tính năng

- **Xem trang chính**: Truy cập `http://localhost:8000/`. Giao diện có slider, sản phẩm hot, sản phẩm Sale nổi bật.
- **Trang danh mục & phân trang**: Truy cập `http://localhost:8000/category`. Bạn sẽ thấy bộ lọc sidebar, và phân trang tự động chia đúng **10 sản phẩm mỗi trang**.
- **Đặt hàng & Giỏ hàng**: Đặt hàng nhanh ngay tại trang chi tiết sản phẩm, hoặc thêm nhiều sản phẩm vào giỏ, điều chỉnh số lượng và thanh toán.
- **Trang quản trị Admin**: Đăng nhập qua đường dẫn `http://localhost:8000/login` bằng tài khoản `admin` / `admin123` để truy cập Dashboard, duyệt/xóa đơn hàng, quản lý danh sách sản phẩm (có form upload ảnh trực tiếp lên thư mục `data/uploads/` của máy chủ) và xem tài khoản khách hàng.
