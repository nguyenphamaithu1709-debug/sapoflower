# BÁO CÁO ĐỐI CHIẾU SỐ LIỆU THỰC TẾ — BIBI FLOWER

**Ngày kiểm tra:** 15/11/2026  
**Nguồn dữ liệu duy nhất (Single Source of Truth):** `c:\Users\admin\Desktop\sapoflower\brain.db` (đồng bộ với `my-brain-bibi/brain.db`, giao diện Admin Dashboard và trang bán hàng `https://soapflower.io.vn`).

---

## 1. BẢNG ĐỐI CHIẾU SỐ LIỆU TỔNG HỢP

| Chỉ số | Số liệu trong `brain.db` | Số liệu hiển thị trên `admin.html` | Trạng thái đối chiếu |
| :--- | :--- | :--- | :--- |
| **Tổng số sản phẩm (`products`)** | **9 sản phẩm** (`6 physical`, `2 service`, `1 digital`) | **9 sản phẩm** | **Khớp 100%** |
| **Tổng tồn kho vật lý (`stock`)** | **132 sản phẩm** (`25 + 15 + 12 + 20 + 50 + 10`) | **132 sản phẩm** | **Khớp 100%** |
| **Tổng số khách hàng (`customers`)** | **4 khách hàng** | **4 khách hàng** | **Khớp 100%** |
| **Tổng số đơn hàng (`orders`)** | **5 đơn hàng** (`BIBI0001` – `BIBI0005`) | **5 đơn hàng** | **Khớp 100%** |
| **Đơn hàng đã thanh toán (`da_thanh_toan` / `hoan_thanh`)** | **3 đơn hàng** (`BIBI0001`, `BIBI0003`, `BIBI0005`) | **3 đơn hàng** | **Khớp 100%** |
| **Doanh thu thực thu (Đã thanh toán)** | **732.000đ** (`280.000đ + 2.000đ + 450.000đ`) | **732.000đ** | **Khớp 100%** |
| **Đơn hàng đang chờ thanh toán (`cho_thanh_toan`)** | **2 đơn hàng** (`BIBI0002`, `BIBI0004`) | **2 đơn hàng** | **Khớp 100%** |
| **Giá trị đơn chờ thanh toán** | **740.000đ** (`350.000đ + 390.000đ`) | **740.000đ** | **Khớp 100%** |
| **Tổng giá trị toàn bộ đơn hàng (GMV)** | **1.472.000đ** (`732.000đ + 740.000đ`) | **1.472.000đ** | **Khớp 100%** |
| **Email tự động đã gửi (`email_queue`)** | **3 email chuỗi chào mừng** (`status = 'sent'`) + email xác nhận đơn hàng qua Resend | **Đã gửi thành công (HTTP 200 OK)** | **Khớp 100%** |

---

## 2. CHI TIẾT DANH SÁCH SẢN PHẨM TRONG `brain.db` (9 SẢN PHẨM - ĐỦ 3 LOẠI)

| ID | Tên sản phẩm | Phân loại (`type`) | Giá bán (`price`) | Tồn kho (`stock`) | Ghi chú tồn kho |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Bó Hồng Sáp Pastel Cầm Tay | `physical` | 280.000đ | 25 | Có trừ kho khi bán |
| **2** | Bó Hoa Sáp Trái Tim Lãng Mạn | `physical` | 350.000đ | 15 | Có trừ kho khi bán |
| **3** | Bó Hoa Vương Miện Hoàng Gia | `physical` | 390.000đ | 12 | Có trừ kho khi bán |
| **4** | Bó Hoa Sáp Phối Gấu Bông Dễ Thương | `physical` | 320.000đ | 20 | Có trừ kho khi bán |
| **5** | Bó Hoa Mini 1 - 3 Bông Xinh Xắn | `physical` | 45.000đ | 50 | Có trừ kho khi bán |
| **6** | Bó Hoa Hướng Dương Sáp Tốt Nghiệp | `physical` | 290.000đ | 10 | Có trừ kho khi bán |
| **7** | Thiết Kế Hoa Theo Yêu Cầu & Ngân Sách | `service` | 200.000đ | 0 | Dịch vụ — Không trừ kho |
| **8** | Combo Quà Tặng Trọn Gói (Hoa + Thiệp + Đèn LED) | `service` | 50.000đ | 0 | Dịch vụ — Không trừ kho |
| **9** | Ebook Cẩm Nang Chọn Hoa Theo Dịp & Bảo Quản Hoa Sáp Bền Đẹp 5 Năm | `digital` | 49.000đ | 0 | Sản phẩm số — Không trừ kho |

---

## 3. CHI TIẾT DANH SÁCH KHÁCH HÀNG TRONG `brain.db` (4 KHÁCH HÀNG)

| ID | Họ và tên | Số điện thoại | Email | Nguồn / Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Nguyễn Phương Linh | `0912345678` | `linh@gmail.com` | Khách mua lẻ bó hoa Pastel |
| **2** | Ái Thư | `0387315820` | `nguyenphamaithu1709@gmail.com` | Khách đăng ký Waitlist nhận mã `BIBI15NEW` & đặt hàng trên web |
| **3** | Trần Bảo Ngọc | `0903123456` | `baongoc.flower@gmail.com` | Khách đặt bó hoa Vương Miện |
| **4** | Lê Hoàng Long | `0938889900` | `hoanglong@outlook.com` | Khách đặt sỉ 10 bó hoa mini tặng sự kiện |

---

## 4. CHI TIẾT DANH SÁCH ĐƠN HÀNG TRONG `brain.db` (5 ĐƠN HÀNG)

| ID | Mã đơn (`order_code`) | Khách hàng | Sản phẩm | Số lượng | Thành tiền (`amount`) | Trạng thái (`status`) | Phương thức |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `BIBI0001` | Nguyễn Phương Linh (`#1`) | Bó Hồng Sáp Pastel Cầm Tay (`#1`) | 1 | **280.000đ** | `da_thanh_toan` | Chuyển khoản |
| **2** | `BIBI0002` | Ái Thư (`#2`) | Bó Hoa Sáp Trái Tim Lãng Mạn (`#2`) | 1 | **350.000đ** | `cho_thanh_toan` | Chuyển khoản QR |
| **3** | `BIBI0003` | Ái Thư (`#2`) | Bó Hồng Sáp Pastel Cầm Tay (Đơn test thực tế) | 1 | **2.000đ** | `hoan_thanh` | SePay VietQR MBBank |
| **4** | `BIBI0004` | Trần Bảo Ngọc (`#3`) | Bó Hoa Vương Miện Hoàng Gia (`#3`) | 1 | **390.000đ** | `cho_thanh_toan` | COD |
| **5** | `BIBI0005` | Lê Hoàng Long (`#4`) | Bó Hoa Mini 1 - 3 Bông Xinh Xắn (`#5`) | 10 | **450.000đ** | `da_thanh_toan` | Chuyển khoản |

---

## 5. KẾT LUẬN ĐỐI CHIẾU

1. **Không có số liệu ảo hay lệch số:** Toàn bộ số liệu giữa `sapoflower/brain.db`, `sapoflower/my-brain-bibi/brain.db`, API `/api/stats` và giao diện quản trị `admin.html` hoàn toàn trùng khớp.
2. **Tách biệt rõ doanh thu thực thu và đơn chờ thanh toán:**
   - Doanh thu đã thu tiền thật (`da_thanh_toan` + `hoan_thanh`): **732.000đ** (3 đơn).
   - Giá trị đơn đang chờ thanh toán (`cho_thanh_toan`): **740.000đ** (2 đơn).
   - Tổng giá trị đơn hàng (GMV): **1.472.000đ** (5 đơn).
