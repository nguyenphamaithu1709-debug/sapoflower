# 🌸 BIBI FLOWER — HỆ THỐNG BÁN HÀNG, QUẢN TRỊ & EMAIL TỰ ĐỘNG

**Bibi Flower** là hệ thống thương mại điện tử và quản trị dữ liệu trung tâm dành cho tiệm hoa sáp thơm & hoa quà tặng thiết kế, hoạt động tại tên miền chính thức **[https://soapflower.io.vn](https://soapflower.io.vn)**.

Hệ thống kết hợp giao diện đặt hoa trực tuyến chuẩn phong cách **Warm Caramel & Cream**, thanh toán tự động qua **SePay VietQR (MBBank)**, cơ sở dữ liệu trung tâm **SQLite (`brain.db`)**, bảng điều khiển quản trị **Admin Dashboard (`admin.html`)**, và hệ thống chăm sóc khách hàng tự động qua **Resend Email API**.

---

## 1. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
sapoflower/
├── app.py                      # Máy chủ Flask Backend (REST API, SQLite, Resend Email, Cloud Sync)
├── brain.db                    # Cơ sở dữ liệu trung tâm (Single Source of Truth - 7 bảng)
├── brain.db.bak                # Bản sao lưu dự phòng trực tiếp của brain.db
├── backups/
│   └── brain_backup_20261115.db # Bản sao lưu định kỳ theo ngày
├── index.html                  # Trang chủ bán hàng, giỏ hàng, thanh toán VietQR & đăng ký nhận mã ưu đãi 15% - 20%
├── thanh-toan.html             # Trang thanh toán đồng bộ
├── admin.html                  # Hệ thống quản trị trung tâm (Dashboard, Sản phẩm, Khách hàng, Đơn hàng)
├── email_sequence.md           # Kịch bản chuỗi 3 email tự động & email xác nhận đơn hàng
├── resend_config.txt           # Cấu hình kết nối Resend API
├── .env.example                # Mẫu biến môi trường (.env)
├── requirements.txt            # Các thư viện Python cần thiết (Flask, python-dotenv)
├── CNAME                       # Cấu hình tên miền tùy chỉnh GitHub Pages (soapflower.io.vn)
├── brain_review.md             # Báo cáo rà soát và kiểm định chất lượng bộ não dữ liệu
├── brain_score.md              # Bảng tự chấm điểm hệ thống (9.5/10)
├── so_lieu.md                  # Báo cáo đối chiếu số liệu thực tế giữa brain.db và Dashboard
├── week2_review.md             # Tổng kết Tuần 2 (5 câu hỏi trọng tâm kèm số liệu thực)
├── day11.txt                   # Bài đăng mạng xã hội Ngày 11 (chuẩn giọng văn Bibi Flower)
├── day12.txt                   # Bài đăng tổng kết 2 tuần & 2 bài mời nhận ưu đãi trên web
├── test_log.md                 # Nhật ký kiểm thử End-to-End và 3 lỗi thực tế đã khắc phục
└── test_bibi_e2e.py            # Script kiểm thử tự động toàn bộ API, Database và Resend Email
```

---

## 2. HƯỚNG DẪN CÀI ĐẶT & CHẠY HỆ THỐNG TRÊN MÁY CÁ NHÂN (LOCAL)

### Bước 1: Cài đặt thư viện Python
Mở Terminal / PowerShell tại thư mục `c:\Users\admin\Desktop\sapoflower` và chạy:

```bash
pip install -r requirements.txt
```

### Bước 2: Cấu hình biến môi trường (`.env`)
Sao chép file `.env.example` thành `.env` (hoặc kiểm tra file `.env` đã được cấu hình sẵn):

```ini
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxx
SENDER_NAME=Bibi Flower
SENDER_EMAIL=hi@aurafashion.io.vn
PORT=5000
```

### Bước 3: Khởi động máy chủ Flask (`app.py`)
```bash
python app.py
```

Sau khi khởi động, truy cập các đường dẫn sau trên trình duyệt:
- **Trang chủ bán hàng:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Trang quản trị Admin Dashboard:** [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin)
- **API Thống kê dữ liệu thực:** [http://127.0.0.1:5000/api/stats](http://127.0.0.1:5000/api/stats)

---

## 3. DANH SÁCH API BACKEND (`app.py`)

| Phương thức | Endpoint | Chức năng |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | Lấy toàn bộ thống kê tổng quan, danh sách sản phẩm, khách hàng, đơn hàng từ `brain.db` |
| `GET / POST` | `/api/products` | Xem danh sách hoặc thêm sản phẩm mới (có kiểm tra chặn giá âm, tồn kho âm) |
| `PUT / DELETE` | `/api/products/<id>` | Cập nhật hoặc xóa sản phẩm |
| `GET / POST` | `/api/customers` | Xem danh sách hoặc thêm khách hàng mới (kiểm tra SĐT 10 số bắt đầu bằng `0`, định dạng email) |
| `DELETE` | `/api/customers/<id>` | Xóa khách hàng (chặn xóa nếu khách đã có đơn hàng) |
| `GET / POST` | `/api/orders` | Xem danh sách hoặc tạo đơn hàng mới (trừ kho với sản phẩm `physical`, tự động gửi email xác nhận đơn hàng) |
| `PUT / DELETE` | `/api/orders/<id>` | Cập nhật trạng thái đơn hàng hoặc xóa đơn hàng (hoàn lại tồn kho nếu đơn chưa hủy) |
| `POST` | `/api/waitlist` | Đăng ký nhận mã ưu đãi 15% - 20% (`BIBI15NEW`) và kích hoạt chuỗi 3 email tự động qua Resend (hỗ trợ `+test` gửi ngay cả 3 email) |
| `POST` | `/api/sync` | Đồng bộ đơn hàng mới từ Google Sheets về `brain.db` và tự động gửi email xác nhận |
| `GET` | `/api/order-status/<code>` | Kiểm tra trạng thái thanh toán thực tế của đơn hàng (`BIBIxxxx`) |

---

## 4. HƯỚNG DẪN KIỂM THỬ TỰ ĐỘNG & SAO LƯU DỮ LIỆU

### Chạy kiểm thử tự động End-to-End:
```bash
python test_bibi_e2e.py
```
Script sẽ tự động kiểm tra:
1. Gửi chuỗi 3 email chào mừng qua `/api/waitlist` với địa chỉ `+test`.
2. Kiểm tra chặn lỗi đầu vào (SĐT sai, giá âm, đặt quá số lượng tồn kho).
3. Kiểm tra trừ tồn kho với sản phẩm `physical` và không trừ kho với sản phẩm `digital`, kèm gửi email xác nhận đơn hàng qua Resend.

### Sao lưu cơ sở dữ liệu (`brain.db`):
```powershell
Copy-Item brain.db -Destination "backups\brain_backup_$(Get-Date -Format 'yyyyMMdd').db"
```

---

## 5. THÔNG TIN LIÊN HỆ & TÊN MIỀN CHÍNH THỨC

- **Website chính thức:** [https://soapflower.io.vn](https://soapflower.io.vn)
- **Trang quản trị:** [https://soapflower.io.vn/admin.html](https://soapflower.io.vn/admin.html)
- **Zalo / Số điện thoại hỗ trợ:** `0345 573 574`
- **Tài khoản nhận thanh toán VietQR (SePay):** MBBank — `0345573574` — `NGUYEN THI KIM ANH`
