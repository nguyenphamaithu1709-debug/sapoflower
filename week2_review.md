# NHÌN LẠI TUẦN 2 (WEEK 2 REVIEW) — BIBI FLOWER (`soapflower.io.vn`)

**Ngày tổng kết:** 15/11/2026  
**Dự án:** Tiệm Hoa Sáp Thơm & Hoa Quà Tặng Thiết Kế **Bibi Flower**  
**Website chính thức:** `https://soapflower.io.vn`  
**Database trung tâm:** `c:\Users\admin\Desktop\sapoflower\brain.db`

---

## Câu 1: Tuần qua mình đã xây được những gì và hệ thống đang chạy ra sao?

Trong Tuần 2, mình đã hoàn thiện toàn bộ hệ thống bán hàng khép kín cho **Bibi Flower** từ giao diện khách hàng, cổng thanh toán tự động, hệ thống quản trị đến chuỗi chăm sóc khách hàng qua email:

1. **Website bán hàng (`index.html`, `thanh-toan.html`) tại `https://soapflower.io.vn`:**
   - Giữ trọn vẹn phong cách ấm áp, thanh lịch của Bibi Flower với tông màu kem sữa (`#FAF6F0`), nâu caramel (`#B78353`), nâu trầm (`#8C5D33`) và giọng văn thân thương (`em` — `khách`, `nha, ạ, nè, cho lẹ, em cân tất`).
   - Có đầy đủ danh mục sản phẩm, bảng giá minh bạch theo từng cỡ bó, giỏ hàng thông minh, tạo đơn hàng trực tiếp kèm **mã VietQR MBBank (`0345573574` - `NGUYEN THI KIM ANH`)** tự động điền sẵn số tiền và mã đơn (`BIBIxxxx`).
   - Bổ sung mục **Đăng ký nhận mã ưu đãi 15% - 20% (`BIBI15NEW`) & bí quyết chọn hoa (`#nhan-uu-dai`)** kết nối trực tiếp với Backend và Resend API (không dùng form khảo sát theo đúng định hướng gọn nhẹ của tiệm).
2. **Hệ thống Backend (`app.py`) & Cơ sở dữ liệu (`brain.db`):**
   - Hợp nhất toàn bộ 7 bảng dữ liệu vào `brain.db`: `knowledge` (5 mục kiến thức nền tảng), `business` (4 mảng hoạt động), `brand_voice` (5 quy tắc giọng văn), `products` (9 sản phẩm đủ 3 phân loại `physical`, `service`, `digital`), `customers` (4 khách hàng), `orders` (5 đơn hàng), và `email_queue` (hàng đợi gửi thư tự động).
   - Kiểm tra dữ liệu đầu vào chặt chẽ (chặn số điện thoại sai định dạng, chặn giá âm, chặn đặt quá số lượng tồn kho, chỉ trừ kho với sản phẩm `physical`).
3. **Hệ thống Email tự động qua Resend API (`email_sequence.md`):**
   - Khi khách để lại email nhận ưu đãi trên web, hệ thống tự động gửi chuỗi 3 email chăm sóc mang đúng giọng văn của Bibi Flower.
   - Khi khách đặt hàng mới hoặc đồng bộ đơn từ Cloud, hệ thống tự động gửi **Email xác nhận đơn hàng** kèm hướng dẫn kiểm tra hoa trước khi nhận.

---

## Câu 2: Con số thực tế hiện tại trong hệ thống là bao nhiêu? (Đối chiếu từ `so_lieu.md`)

Toàn bộ con số dưới đây được trích xuất trực tiếp từ `brain.db` (không có số liệu ước chừng):

- **Sản phẩm đang kinh doanh:** **9 sản phẩm**
  - **6 sản phẩm vật lý (`physical`):** Tổng tồn kho **132 bó** (giá từ `45.000đ` đến `390.000đ`).
  - **2 dịch vụ (`service`):** Thiết kế hoa theo ngân sách (`200.000đ`) & Combo quà tặng trọn gói (`50.000đ`).
  - **1 sản phẩm số (`digital`):** Ebook Cẩm Nang Chọn Hoa Theo Dịp & Bảo Quản Hoa Sáp Bền Đẹp 5 Năm (`49.000đ`).
- **Khách hàng trong hệ thống:** **4 khách hàng** (`Nguyễn Phương Linh`, `Ái Thư`, `Trần Bảo Ngọc`, `Lê Hoàng Long`).
- **Tổng số đơn hàng:** **5 đơn hàng** (`BIBI0001` đến `BIBI0005`) với tổng giá trị (GMV) là **1.472.000đ**:
  - **Đơn đã thanh toán (`da_thanh_toan` / `hoan_thanh`):** **3 đơn hàng** (`BIBI0001`, `BIBI0003`, `BIBI0005`) — Doanh thu thực thu: **732.000đ**.
  - **Đơn đang chờ thanh toán (`cho_thanh_toan`):** **2 đơn hàng** (`BIBI0002`, `BIBI0004`) — Giá trị chờ thu: **740.000đ**.
- **Email tự động đã gửi thành công qua Resend:** **3/3 email** trong chuỗi chào mừng (`status = 'sent'`) cùng các email xác nhận đơn hàng tự động.

---

## Câu 3: Điều gì đã làm tốt nhất trong tuần qua?

1. **Giữ vững cá tính thương hiệu (Brand Voice 10/10):** Từ câu chữ trên website, bảng hướng dẫn chọn hoa, bài đăng mạng xã hội (`day11.txt`, `day12.txt`) cho đến từng bức thư trong `email_sequence.md` đều giữ đúng cách xưng hô `em` — `khách`, ấm áp, thật thà, giải quyết đúng nỗi lo *"sợ hoa giao tới bị móp giấy gói hoặc không giống hình"*.
2. **Trải nghiệm đặt hoa và thanh toán mượt mà:** Khách vào web không cần qua các bước khảo sát rườm rà, có thể chọn mẫu hoa, ghi lời chúc lên thiệp, chọn ngày giờ nhận và quét mã QR thanh toán tự động ngay lập tức.
3. **Đồng bộ dữ liệu hai chiều (Cloud & Local SQLite):** Dù khách đặt trên GitHub Pages (`https://soapflower.io.vn`) hay chạy qua máy chủ Flask (`app.py`), đơn hàng đều được đồng bộ về `brain.db` và gửi email xác nhận tự động.

---

## Câu 4: Những điểm nghẽn hoặc lỗi nào đã phát hiện và xử lý triệt để?

Trong quá trình kiểm thử End-to-End (`test_log.md`), mình đã phát hiện và xử lý dứt điểm 3 vấn đề kỹ thuật:

1. **Đồng bộ cấu trúc bảng giữa `my-brain-bibi/brain.db` và `sapoflower/brain.db`:** Trước đây file database ở thư mục gốc thiếu các bảng `knowledge`, `business`, `brand_voice`, `email_queue` và sản phẩm `digital`. Mình đã hợp nhất toàn bộ sang một cấu trúc chuẩn duy nhất và tạo bản sao lưu tại `backups/brain_backup_20261115.db`.
2. **Kết nối trực tiếp các nút Thêm / Sửa / Xóa trên `admin.html` với API Backend:** Nâng cấp `admin.html` để khi chạy cùng `app.py`, mọi thao tác tạo đơn, thêm khách, cập nhật tồn kho và đồng bộ Cloud đều lưu thẳng xuống `brain.db` và kích hoạt Resend API.
3. **Cấu hình tên miền gửi thư Resend (`resend_config.txt` & `.env`):** Sử dụng địa chỉ gửi đã xác thực `Bibi Flower <hi@aurafashion.io.vn>` giúp toàn bộ chuỗi 3 email chào mừng và email xác nhận đơn hàng gửi đi đạt `HTTP 200 OK` ngay lập tức, không bị chặn bởi lỗi xác thực tên miền.

---

## Câu 5: Kế hoạch trọng tâm cho tuần tiếp theo là gì?

1. **Chuyển đổi 2 đơn chờ thanh toán (`BIBI0002` và `BIBI0004` - trị giá `740.000đ`):** Nhắn Zalo gửi ảnh chụp bó hoa thật trước khi giao để khách yên tâm xác nhận và hoàn tất đơn hàng.
2. **Đẩy mạnh dòng sản phẩm số (`Ebook 49.000đ`) và Combo dịch vụ (`50.000đ`):** Tận dụng ưu điểm không tốn tồn kho vật lý và biên lợi nhuận cao để bán kèm (upsell) cho khách đặt hoa dịp lễ và tốt nghiệp.
3. **Thu hút thêm khách đăng ký nhận ưu đãi `BIBI15NEW` trên web:** Đăng 2 bài viết mời trải nghiệm web trong `day12.txt` lên trang cá nhân và Zalo để kéo khách thật vào phễu email tự động của Bibi Flower.
