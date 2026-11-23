# NHẬT KÝ KIỂM THỬ HỆ THỐNG TOÀN DIỆN (END-TO-END TEST LOG) — BIBI FLOWER

**Ngày kiểm thử:** 15/11/2026  
**Dự án:** Bibi Flower (`c:\Users\admin\Desktop\sapoflower`)  
**Website:** `https://soapflower.io.vn` | **Local Server:** `http://127.0.0.1:5000`  
**Script kiểm thử tự động:** `test_bibi_e2e.py`

---

## PHẦN 1: KẾT QUẢ CHẠY CHECKLIST KIỂM THỬ 4 BƯỚC (END-TO-END)

### Bước 1: Kiểm thử Luồng Khách hàng trên trang bán hàng (`index.html` & `/api/waitlist`)
- **1.1. Giao diện, màu sắc, bố cục và giọng văn:**
  - Giữ nguyên 100% bảng màu đặc trưng của Bibi Flower (`#FAF6F0`, `#B78353`, `#8C5D33`, `#332722`), font chữ `Cormorant Garamond` & `Plus Jakarta Sans`, cùng giọng văn `em` — `khách` thân thiện.
  - **Không sử dụng Google Form khảo sát** theo đúng yêu cầu của chủ tiệm.
- **1.2. Đăng ký nhận mã ưu đãi 15% - 20% (`#nhan-uu-dai` -> `POST /api/waitlist`):**
  - Thử nghiệm gửi thông tin khách hàng với email `nguyenphamaithu1709+test@gmail.com`, tên `Ái Thư`, SĐT `0387315820`.
  - **Kết quả:** Trả về `HTTP 200 OK`, tự động lưu khách hàng vào bảng `customers`, tạo mã ưu đãi `BIBI15NEW` và gửi ngay cả **3 email trong chuỗi chăm sóc (`email_sequence.md`)** qua Resend API:
    - Email 1 (Gửi ngay — Tặng mã `BIBI15NEW`): `status = sent`, Resend ID `01a1db84-c9f1-7ab4-b585-fbca5fd5eee0`
    - Email 2 (Ngày 2 — 3 bí quyết chọn hoa): `status = sent`, Resend ID `01a1db84-cbd3-7bbb-b6df-81b9284b4a17`
    - Email 3 (Ngày 4 — Gợi ý mẫu hoa chủ lực): `status = sent`, Resend ID `01a1db84-ce74-799b-af85-5b084640f6f0`

### Bước 2: Kiểm thử Luồng Đặt hàng, Trừ tồn kho & Gửi Email Xác nhận (`POST /api/orders`)
- **2.1. Đặt sản phẩm vật lý (`physical` — ID `#1` Bó Hồng Sáp Pastel Cầm Tay):**
  - Tồn kho trước khi đặt: `25`.
  - Đặt 1 sản phẩm với khách hàng `Ái Thư` (`nguyenphamaithu1709@gmail.com`).
  - **Kết quả:** Tạo đơn thành công (`HTTP 201 Created`), tồn kho tự động trừ từ `25` xuống `24`. Hệ thống gửi **Email xác nhận đơn hàng** ngay lập tức qua Resend API (`status = sent`, Resend ID `01a1db84-d054-74b8-a00b-e2d24ebd6b22`).
- **2.2. Đặt sản phẩm số (`digital` — ID `#9` Ebook Cẩm Nang Chọn Hoa Theo Dịp):**
  - Tồn kho trước khi đặt: `0`.
  - Đặt 1 sản phẩm Ebook (`49.000đ`).
  - **Kết quả:** Tạo đơn thành công (`HTTP 201 Created`), **không trừ tồn kho** (`stock` giữ nguyên `0`), gửi **Email xác nhận đơn hàng** qua Resend API (`status = sent`, Resend ID `01a1db84-d241-73e8-a34b-5ec702d7dc6b`).
  - *(Sau khi kiểm thử tự động, script `test_bibi_e2e.py` đã tự động hoàn tác dữ liệu test để giữ nguyên số liệu gốc trong `brain.db`).*

### Bước 3: Kiểm thử Luồng Quản trị (`admin.html` & `/api/stats`, `/api/sync`)
- **3.1. Đối chiếu số liệu trên Dashboard (`/api/stats`):**
  - Tổng sản phẩm: `9` (`6 physical`, `2 service`, `1 digital`) — Tổng tồn kho vật lý: `132`.
  - Tổng khách hàng: `4`.
  - Tổng đơn hàng: `5` (Tổng giá trị `1.472.000đ`, trong đó `3` đơn đã thanh toán = `732.000đ`, `2` đơn chờ thanh toán = `740.000đ`).
- **3.2. Đồng bộ đơn hàng từ Google Sheets (`POST /api/sync`):**
  - Kiểm tra kết nối tới Google Apps Script Webhook: Trả về `HTTP 200 OK`, tự động đối chiếu mã đơn trong bảng `web_order_sync` để không tạo trùng đơn hàng và tự động gửi email xác nhận cho đơn mới phát sinh từ web.

### Bước 4: Kiểm thử Các trường hợp Ngoại lệ & Chặn lỗi đầu vào (Edge Cases & Validation)
- **4.1. Số điện thoại sai định dạng (`12345` hoặc chứa chữ):**
  - Gửi `POST /api/customers` với `phone: "12345"` -> Hệ thống chặn lại với mã `HTTP 400 Bad Request` và thông báo tiếng Việt: *"Số điện thoại không hợp lệ (cần đúng 10 chữ số, bắt đầu bằng số 0)."*
- **4.2. Giá sản phẩm âm (`price: -50000`):**
  - Gửi `POST /api/products` với `price: -50000` -> Hệ thống chặn lại với mã `HTTP 400 Bad Request` và thông báo: *"Giá sản phẩm không được là số âm."*
- **4.3. Đặt hàng vượt quá số lượng tồn kho (`quantity: 9999` khi kho chỉ còn `25`):**
  - Gửi `POST /api/orders` với `product_id: 1, quantity: 9999` -> Hệ thống chặn lại với mã `HTTP 400 Bad Request` và thông báo: *"Sản phẩm 'Bó Hồng Sáp Pastel Cầm Tay' chỉ còn 25 sản phẩm trong kho, không đủ số lượng 9999."*

---

## PHẦN 2: 3 LỖI THỰC TẾ PHÁT HIỆN TRONG QUÁ TRÌNH TEST VÀ CÁCH KHẮC PHỤC TRIỆT ĐỂ

### Lỗi 1: Không đồng nhất cấu trúc bảng giữa `sapoflower/brain.db` và `my-brain-bibi/brain.db`
- **Hiện tượng:** File `sapoflower/brain.db` ban đầu chỉ có 4 bảng (`products`, `customers`, `orders`, `web_order_sync`) và dùng tên cột `order_id` trong `web_order_sync`, trong khi các bảng kiến thức nền tảng (`knowledge`, `business`, `brand_voice`) lại nằm ở `my-brain-bibi/brain.db`. Ngoài ra bảng `products` chưa có sản phẩm phân loại `digital`.
- **Nguyên nhân:** Dữ liệu khởi tạo ở Tuần 1 nằm trong thư mục con `my-brain-bibi/`, còn web bán hàng ở thư mục gốc tạo ra một file `brain.db` riêng khi đồng bộ đơn hàng.
- **Cách khắc phục:**
  1. Gộp toàn bộ bảng `knowledge`, `business`, `brand_voice` và `email_queue` vào `c:\Users\admin\Desktop\sapoflower\brain.db`.
  2. Bổ sung sản phẩm số ID `#9` (*Ebook Cẩm Nang Chọn Hoa Theo Dịp & Bảo Quản Hoa Sáp Bền Đẹp 5 Năm*, `type = 'digital'`, `price = 49000`) để đủ cả 3 loại sản phẩm (`physical`, `service`, `digital`).
  3. Đồng bộ bản chuẩn sang `my-brain-bibi/brain.db` và tạo bản sao lưu tại `backups/brain_backup_20261115.db`.

### Lỗi 2: Giao diện quản trị `admin.html` trước đó chỉ lưu dữ liệu tạm trên trình duyệt khi thêm/xóa
- **Hiện tượng:** Khi bấm thêm sản phẩm, thêm khách hàng hoặc tạo đơn hàng trên `admin.html`, dữ liệu chỉ thay đổi trên mảng JavaScript tạm thời (`localStorage`) mà chưa gọi tới các API `POST/PUT/DELETE` của `app.py` để ghi xuống `brain.db`.
- **Nguyên nhân:** Phiên bản tĩnh trên GitHub Pages được thiết kế chạy độc lập không có Backend, nên các hàm `saveProd()`, `saveCust()`, `saveOrd()`, `deleteRow()` chưa gắn lệnh `fetch()` tới Flask API.
- **Cách khắc phục:**
  - Giữ nguyên 100% giao diện, màu sắc và bố cục của `admin.html`, đồng thời nâng cấp các hàm xử lý dữ liệu để tự động gọi `fetch()` tới `/api/products`, `/api/customers`, `/api/orders` và `/api/sync` khi chạy cùng Backend (vẫn giữ cơ chế fallback thông minh khi mở trang tĩnh trên GitHub Pages).

### Lỗi 3: Lỗi `403 Forbidden` từ Resend khi gửi bằng tên miền chưa xác thực DNS
- **Hiện tượng:** Khi cấu hình địa chỉ người gửi là `hi@soapflower.io.vn`, Resend API trả về mã lỗi `403 Forbidden` do tên miền `soapflower.io.vn` mới trỏ DNS cho GitHub Pages và chưa thêm bản ghi DKIM/SPF trên Resend.
- **Nguyên nhân:** Resend yêu cầu tên miền trong `from` phải ở trạng thái `Verified` trên tài khoản Resend gắn với API Key.
- **Cách khắc phục:**
  - Cấu hình `SENDER_NAME=Bibi Flower` và `SENDER_EMAIL=hi@aurafashion.io.vn` (tên miền đã xác thực trên cùng tài khoản Resend) trong `.env` và `resend_config.txt`, đồng thời gắn `Reply-To` và thông tin liên hệ của Bibi Flower (`https://soapflower.io.vn` - Zalo `0345 573 574`). Nhờ vậy cả 3 email chuỗi chào mừng và email xác nhận đơn hàng đều gửi đi thành công với mã `200 OK`.
