# -*- coding: utf-8 -*-
"""
Backend quản lý Bibi Flower — nối trực tiếp vào brain.db.
Chạy: python app.py  ->  http://127.0.0.1:5000/admin
"""
import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, os.getenv("DB_PATH", "brain.db"))
SYNC_CONFIG_PATH = os.path.join(BASE_DIR, "sync_config.json")
RESEND_CONFIG_PATH = os.path.join(BASE_DIR, "resend_config.txt")

app = Flask(__name__)


@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema():
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'physical',
                price INTEGER NOT NULL DEFAULT 0,
                description TEXT DEFAULT '',
                stock INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT,
                zalo TEXT,
                registered_at TEXT DEFAULT (datetime('now')),
                note TEXT DEFAULT ''
            )
            """
        )
        # Ensure 'note' column exists in customers
        cust_cols = [r[1] for r in conn.execute("PRAGMA table_info(customers)").fetchall()]
        if "note" not in cust_cols:
            conn.execute("ALTER TABLE customers ADD COLUMN note TEXT DEFAULT ''")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                quantity INTEGER NOT NULL DEFAULT 1,
                amount INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'cho_thanh_toan',
                order_date TEXT DEFAULT (datetime('now')),
                shipping_address TEXT DEFAULT '',
                size TEXT DEFAULT '',
                color TEXT DEFAULT '',
                note TEXT DEFAULT '',
                source TEXT DEFAULT 'web',
                payment_method TEXT DEFAULT 'Chuyển khoản QR (SePay)'
            )
            """
        )
        ord_cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "payment_method" not in ord_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'Chuyển khoản QR (SePay)'")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_order_sync (
                order_code TEXT PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id),
                synced_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                step INTEGER NOT NULL,
                subject TEXT NOT NULL,
                html_body TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                sent_at TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                resend_id TEXT DEFAULT '',
                error TEXT DEFAULT ''
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


ensure_schema()


# ---------- Cấu hình Resend & Gửi Email Tự Động ----------
def load_resend_config():
    cfg = {
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY", "").strip(),
        "SENDER_NAME": os.getenv("SENDER_NAME", "Bibi Flower").strip(),
        "SENDER_EMAIL": os.getenv("SENDER_EMAIL", "hi@aurafashion.io.vn").strip(),
    }
    if os.path.exists(RESEND_CONFIG_PATH):
        try:
            with open(RESEND_CONFIG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k and v and not os.getenv(k):
                        cfg[k] = v
        except Exception:
            pass
    return cfg


def send_resend_email(to_email, subject, html_body):
    cfg = load_resend_config()
    api_key = cfg.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "Chưa cấu hình RESEND_API_KEY"}
    sender_name = cfg.get("SENDER_NAME", "Bibi Flower").strip()
    sender_email = cfg.get("SENDER_EMAIL", "hi@aurafashion.io.vn").strip()
    payload = {
        "from": f"{sender_name} <{sender_email}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BibiFlower-Mailer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "id": resp_data.get("id", "")}
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        return {"ok": False, "error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def build_sequence_emails(customer_name):
    name = (customer_name or "khách").strip()
    wrap_start = (
        '<div style="font-family:\'Plus Jakarta Sans\',system-ui,-apple-system,sans-serif;'
        'max-width:580px;margin:0 auto;padding:28px 24px;color:#332722;line-height:1.7;'
        'background:#FAF6F0;border:1px solid #EADBCC;border-radius:18px;">'
    )
    wrap_end = (
        '<hr style="border:none;border-top:1px solid #EADBCC;margin:24px 0 14px;">'
        '<p style="font-size:12px;color:#7A6C65;margin:0;">'
        'Thương mến,<br><strong style="color:#8C5D33;">Em Bibi — Bibi Flower</strong><br>'
        'Website: <a href="https://soapflower.io.vn" style="color:#B78353;">https://soapflower.io.vn</a> '
        '| Zalo tư vấn nhanh: 0345573574</p></div>'
    )

    # Email 1: Gửi ngay (Ngày 0)
    subj1 = "Em nhận được thông tin của khách rồi nè 💐 (Gửi khách mã giảm 15% - 20% từ Bibi Flower nha)"
    html1 = (
        wrap_start
        + f"<p>Chào <strong>{name}</strong> ơi,</p>"
        + "<p>Em là Bibi từ <strong>Bibi Flower</strong> đây ạ 💐</p>"
        + "<p>Em nhắn thư này để báo là em đã nhận được thông tin đăng ký nhận ưu đãi của khách trên web rồi nha. "
        "Thật sự vui lắm vì khách đã ghé thăm tiệm hoa nhỏ của em nè.</p>"
        + "<p>Ở Bibi Flower, em chuyên làm các mẫu hoa sáp thơm nghệ thuật và hoa lụa xinh xắn — từ bó mini 1-3 bông, "
        "bó trái tim phủ nhũ, bó vương miện cho tới hộp quà nắp kính và hoa bánh kẹo. Cánh hoa sáp mềm mịn, thơm dịu nhẹ "
        "và giữ form bền đẹp suốt 3 đến 5 năm không lo héo tàn. Khách mua lẻ 1 bó tặng người thương hay đặt sỉ số lượng cho lớp, "
        "công ty bao nhiêu em cũng cân tất ạ.</p>"
        + '<div style="background:#FFFFFF;border:1px dashed #B78353;padding:16px 18px;border-radius:14px;margin:18px 0;text-align:center;">'
        + '<div style="font-size:13px;color:#7A6C65;">Như đã hẹn trên web, em gửi tặng khách mã giảm 15% - 20% kèm túi xách trong suốt và thiệp viết tay cho đơn đầu tiên nha:</div>'
        + '<div style="font-size:22px;font-weight:800;color:#8C5D33;letter-spacing:1.5px;margin-top:6px;">BIBI15NEW</div>'
        + "</div>"
        + "<p>Mấy ngày tới, em sẽ gửi thêm cho khách vài mẹo nhỏ chọn hoa hợp từng dịp lễ và cách giữ hoa sáp thơm lâu "
        "(em chỉ chia sẻ ngắn gọn thôi chứ không gửi thư quảng cáo dồn dập làm phiền khách đâu nè). Khách nhớ đón đọc giúp em nha 😘</p>"
        + "<p>Cần chọn mẫu gấp thì khách cứ nhắn Zalo <strong>0345573574</strong> cho em tư vấn, em gửi hình thật qua cho lẹ ạ 💐</p>"
        + wrap_end
    )

    # Email 2: Gửi sau 2 ngày (Ngày +2)
    subj2 = "Bí quyết nhỏ để bó hoa kỷ niệm giữ form xinh xắn suốt 3 - 5 năm nè khách ơi 💐"
    html2 = (
        wrap_start
        + f"<p>Chào <strong>{name}</strong> ơi,</p>"
        + "<p>Hôm nay em ghé qua chia sẻ với khách một chuyện nhỏ mà nhiều khách tìm tới Bibi Flower hay tâm sự với em lắm nè 💐</p>"
        + "<p>Nhiều khách kể với em là lúc trước dịp lễ mua bó hoa tươi mấy trăm ngàn tặng mẹ hay người yêu, lúc trao tay thì đẹp lắm "
        "nhưng chỉ để được 2 - 3 ngày là cánh hoa héo rũ, rơi rụng hết. Muốn giữ lại kỷ niệm mà đành phải bỏ đi, nhìn tiếc hùi hụi luôn ạ.</p>"
        + "<p>Từ lúc làm hoa sáp thơm tới giờ, em đúc kết được <strong>3 mẹo nhỏ</strong> để chọn và giữ một bó hoa vừa đẹp như thật vừa bền suốt 3 - 5 năm, "
        "em gửi khách tham khảo thử nha:</p>"
        + "<ul style=\"padding-left:18px;\">"
        + "<li><strong>Chọn hoa sáp dập vân 3–5 lớp cánh:</strong> Khi nhìn gần, cánh hoa có độ cong mềm mại tự nhiên chứ không bị cứng đơ, lên hình chụp kỷ niệm sáng bừng luôn nè.</li>"
        + "<li><strong>Để hoa nơi khô ráo, tránh nước và nắng gắt trực tiếp:</strong> Vì cánh hoa làm từ xà phòng hương tự nhiên nên chỉ cần để ở bàn làm việc, kệ sách hay phòng ngủ thoáng mát là hoa giữ màu và hương thơm dịu nhẹ được cả mấy năm trời ạ.</li>"
        + "<li><strong>Kèm túi mica trong suốt và dây đèn LED đom đóm:</strong> Vừa giúp chống bụi cho cánh hoa, vừa bật đèn lung linh vào buổi tối nhìn mê lắm nha.</li>"
        + "</ul>"
        + "<p>Hôm nay em chỉ viết thư chia sẻ vài mẹo nhỏ vậy thôi ạ, hoàn toàn không phải thư giục khách mua hàng đâu nè. "
        "Chỉ mong vài gạch đầu dòng này giúp khách chọn được món quà ưng ý nhất khi cần tặng người thương nha 😘</p>"
        + "<p>Chúc khách một ngày thật nhiều niềm vui ạ 💐</p>"
        + wrap_end
    )

    # Email 3: Gửi sau 5 ngày (Ngày +5)
    subj3 = "Mấy mẫu hoa sáp xinh xắn dễ tặng nhất ở tiệm em — khách xem thử mẫu nào hợp ý nha 😘"
    html3 = (
        wrap_start
        + f"<p>Chào <strong>{name}</strong> ơi,</p>"
        + "<p>Hôm trước em có chia sẻ với khách vài mẹo giữ hoa sáp bền đẹp 3 - 5 năm, không biết khách đã kịp đọc qua chưa nè?</p>"
        + "<p>Hôm nay em tổng hợp ngắn gọn <strong>4 dòng hoa được khách chọn nhiều nhất</strong> ở Bibi Flower theo từng nhu cầu để lúc nào cần tặng quà là khách chọn được liền cho lẹ nha:</p>"
        + "<ul style=\"padding-left:18px;\">"
        + "<li><strong>Bó Hoa Sáp Trái Tim Đỏ Nhũ / Vương Miện (350.000đ – 390.000đ):</strong> Phủ nhũ kim tuyến lấp lánh, đính bướm dạ quang và vương miện — cực hợp tặng Vợ, bạn gái dịp Sinh nhật, Valentine 14/2, 8/3 hay 20/10.</li>"
        + "<li><strong>Bó Hồng Sáp Pastel & Nơ Lưới Ren Hàn Quốc (280.000đ – 290.000đ):</strong> Tone hồng phấn hoặc kem thanh lịch, nhẹ nhàng — tặng Mẹ, chị gái, bạn thân hay chụp ảnh tốt nghiệp siêu xinh xắn.</li>"
        + "<li><strong>Hộp Quà Hoa Sáp Nắp Kính & Hoa Bánh Kẹo (250.000đ – 420.000đ):</strong> Làm quà tặng kỷ niệm, tân gia hoặc tạo bất ngờ ngọt ngào cho người thương.</li>"
        + "<li><strong>Bó Hoa Sáp Mini 1 – 3 Bông (Chỉ từ 45.000đ – 75.000đ):</strong> Nhỏ gọn, tinh tế — mua tặng tập thể lớp, thầy cô dịp 20/11 hay sự kiện công ty cực kỳ tiết kiệm (lấy sỉ số lượng bao nhiêu em cũng cân tất ạ).</li>"
        + "</ul>"
        + "<p>Đặc biệt, mọi đơn đặt tại Bibi Flower đều được <strong>tặng kèm túi xách trong suốt + thiệp viết tay nắn nót</strong>, "
        "hỗ trợ <strong>Free Ship</strong>, cho phép <strong>đồng kiểm tận tay ưng ý mới thanh toán</strong> và <strong>đổi mới 1-1 trong 3 ngày</strong> nếu có lỗi vận chuyển nha.</p>"
        + "<p>Nếu khách chấm được mẫu nào rồi thì nhớ dùng mã <strong style=\"color:#8C5D33;\">BIBI15NEW</strong> để được giảm ngay 15% - 20% cho đơn đầu tiên nhé!</p>"
        + '<div style="margin:22px 0;text-align:center;">'
        + '<a href="https://soapflower.io.vn/#danh-muc" style="display:inline-block;background:#B78353;color:#ffffff;text-decoration:none;font-weight:700;padding:12px 24px;border-radius:999px;margin:4px;">Xem Mẫu Hoa Trên Web 💐</a> '
        + '<a href="https://zalo.me/0345573574" style="display:inline-block;background:#FFFFFF;color:#8C5D33;border:1px solid #B78353;text-decoration:none;font-weight:700;padding:12px 24px;border-radius:999px;margin:4px;">Nhắn Zalo Em Tư Vấn (0345573574)</a>'
        + "</div>"
        + "<p>Cảm ơn khách đã luôn đọc những dòng chia sẻ của em nha 😘💐</p>"
        + wrap_end
    )

    return [
        (1, 0, subj1, html1),
        (2, 2, subj2, html2),
        (3, 5, subj3, html3),
    ]


def trigger_email_sequence(conn, customer_name, customer_email, immediate_all=False):
    email_clean = (customer_email or "").strip()
    if not email_clean or "@" not in email_clean:
        return []
    is_plus_test = "+test" in email_clean.lower() or immediate_all
    deliver_to = re.sub(r"\+[^@]+@", "@", email_clean) if is_plus_test else email_clean

    now = datetime.now()
    seq = build_sequence_emails(customer_name)
    results = []

    for step, delay_days, subj, html_body in seq:
        if step == 1 or is_plus_test:
            sched_str = now.strftime("%Y-%m-%d %H:%M:%S")
            send_res = send_resend_email(deliver_to, subj, html_body)
            status = "sent" if send_res.get("ok") else "failed"
            sent_at = now.strftime("%Y-%m-%d %H:%M:%S") if send_res.get("ok") else ""
            cur = conn.execute(
                """
                INSERT INTO email_queue
                (customer_email, customer_name, step, subject, html_body, scheduled_at, sent_at, status, resend_id, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deliver_to,
                    customer_name,
                    step,
                    subj,
                    html_body,
                    sched_str,
                    sent_at,
                    status,
                    send_res.get("id", ""),
                    send_res.get("error", ""),
                ),
            )
            results.append({"step": step, "status": status, "queue_id": cur.lastrowid, "resend": send_res})
        else:
            sched_dt = now + timedelta(days=delay_days)
            sched_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute(
                """
                INSERT INTO email_queue
                (customer_email, customer_name, step, subject, html_body, scheduled_at, sent_at, status, resend_id, error)
                VALUES (?, ?, ?, ?, ?, ?, '', 'pending', '', '')
                """,
                (deliver_to, customer_name, step, subj, html_body, sched_str),
            )
            results.append({"step": step, "status": "scheduled", "scheduled_at": sched_str, "queue_id": cur.lastrowid})
    return results


def send_order_confirmation_email(customer_name, customer_email, order_code, product_name, quantity, total):
    email_clean = (customer_email or "").strip()
    if not email_clean or "@" not in email_clean:
        return {"ok": False, "error": "Khách hàng chưa có email hợp lệ"}
    deliver_to = re.sub(r"\+[^@]+@", "@", email_clean)
    name = (customer_name or "khách").strip()
    total_fmt = f"{int(total or 0):,}".replace(",", ".") + "đ"
    subject = f"Em đã nhận đơn hoa {order_code} của khách rồi nha 💐 (Bibi Flower)"
    html_body = (
        '<div style="font-family:\'Plus Jakarta Sans\',system-ui,-apple-system,sans-serif;'
        'max-width:580px;margin:0 auto;padding:28px 24px;color:#332722;line-height:1.7;'
        'background:#FAF6F0;border:1px solid #EADBCC;border-radius:18px;">'
        f"<p>Chào <strong>{name}</strong> ơi,</p>"
        "<p>Em là Bibi từ <strong>Bibi Flower</strong> đây ạ 💐</p>"
        "<p>Em nhắn thư này để báo là em vừa ghi nhận và lên đơn hoa cho khách xong xuôi rồi nha. "
        "Thật sự vui lắm vì khách đã tin tưởng chọn hoa ở Bibi Flower nè.</p>"
        '<div style="background:#FFFFFF;border:1px solid #EADBCC;padding:16px 18px;border-radius:14px;margin:18px 0;">'
        '<div style="font-size:14px;font-weight:700;color:#8C5D33;margin-bottom:8px;">📋 Thông tin đơn hoa của khách:</div>'
        f"<div><strong>Mã đơn hàng:</strong> {order_code}</div>"
        f"<div><strong>Mẫu hoa đặt:</strong> {product_name} (Số lượng: {quantity})</div>"
        f'<div><strong>Tổng số tiền:</strong> <span style="color:#8C5D33;font-weight:700;">{total_fmt}</span></div>'
        "</div>"
        "<p><strong>📦 Hướng dẫn nhận hoa từ em:</strong></p>"
        '<ul style="padding-left:18px;margin-top:6px;">'
        "<li>Em đang chọn những bông hoa đẹp nhất, gói ghém chỉn chu kèm túi xách và ghi thiệp cẩn thận để chuẩn bị giao cho khách rồi nha.</li>"
        "<li>Khi shipper giao hoa tới, khách nhớ <strong>đồng kiểm mở hộp kiểm tra hoa tận tay, đúng mẫu và thật sự ưng ý rồi mới thanh toán</strong> ạ.</li>"
        "<li>Nếu trong quá trình vận chuyển hoa chẳng may bị móp méo hay có bất kỳ lỗi nào, bên em hỗ trợ <strong>đổi mới 1-1 miễn phí trong vòng 3 ngày</strong>, "
        "khách chỉ cần nhắn Zalo <strong>0345573574</strong> là em xử lý liền cho lẹ nha 😘</li>"
        "</ul>"
        "<p>Nếu khách cần dặn thêm giờ nhận hoa hay sửa lời chúc trên thiệp thì cứ trả lời lại thư này hoặc nhắn Zalo <strong>0345573574</strong> cho em bất cứ lúc nào nha 💐</p>"
        "<p>Cảm ơn khách đã tin tưởng và ủng hộ tiệm nhỏ của em nhiều ạ 😘</p>"
        '<hr style="border:none;border-top:1px solid #EADBCC;margin:24px 0 14px;">'
        '<p style="font-size:12px;color:#7A6C65;margin:0;">'
        'Thương mến,<br><strong style="color:#8C5D33;">Em Bibi — Bibi Flower</strong><br>'
        'Website: <a href="https://soapflower.io.vn" style="color:#B78353;">https://soapflower.io.vn</a> '
        '| Zalo hỗ trợ đơn hoa: 0345573574</p></div>'
    )
    return send_resend_email(deliver_to, subject, html_body)


def process_due_emails():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    sent_count = 0
    try:
        due_rows = conn.execute(
            "SELECT * FROM email_queue WHERE status = 'pending' AND scheduled_at <= ? ORDER BY id ASC",
            (now_str,),
        ).fetchall()
        for row in due_rows:
            res = send_resend_email(row["customer_email"], row["subject"], row["html_body"])
            if res.get("ok"):
                conn.execute(
                    "UPDATE email_queue SET status = 'sent', sent_at = ?, resend_id = ?, error = '' WHERE id = ?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), res.get("id", ""), row["id"]),
                )
                sent_count += 1
            else:
                conn.execute(
                    "UPDATE email_queue SET status = 'failed', error = ? WHERE id = ?",
                    (res.get("error", ""), row["id"]),
                )
        if due_rows:
            conn.commit()
    finally:
        conn.close()
    return sent_count


def email_scheduler_loop():
    while True:
        try:
            process_due_emails()
        except Exception:
            pass
        time.sleep(30)


threading.Thread(target=email_scheduler_loop, daemon=True).start()


def normalize_phone(phone):
    return re.sub(r"[\s.\-]", "", str(phone or "")).strip()


def validate_phone(phone):
    p = normalize_phone(phone)
    if not p:
        return True, ""
    if not re.match(r"^0\d{9}$", p):
        return False, "Số điện thoại không hợp lệ: cần có đúng 10 chữ số và bắt đầu bằng số 0 (ví dụ: 0345573574)."
    return True, p


def validate_email(email):
    e = str(email or "").strip()
    if not e:
        return True, ""
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", e):
        return False, "Email không hợp lệ: vui lòng nhập đúng định dạng email (ví dụ: ten@gmail.com)."
    return True, e


# ---------- Trang giao diện ----------
@app.route("/admin")
@app.route("/admin/")
def admin_page():
    return send_from_directory(BASE_DIR, "admin.html")


@app.route("/thanh-toan")
@app.route("/thanh-toan/")
def payment_page():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/")
def home_page():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, "images"), filename)


@app.route("/<path:filename>")
def static_files(filename):
    full_path = os.path.join(BASE_DIR, filename)
    if os.path.isfile(full_path):
        return send_from_directory(BASE_DIR, filename)
    img_path = os.path.join(BASE_DIR, "images", filename)
    if os.path.isfile(img_path):
        return send_from_directory(os.path.join(BASE_DIR, "images"), filename)
    return jsonify({"error": "Not found"}), 404


# ---------- Tổng quan ----------
@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_db()
    products_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    customers_count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    orders_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    revenue_paid = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status IN ('da_thanh_toan', 'hoan_thanh', 'success', 'paid')"
    ).fetchone()[0]
    revenue_all = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM orders").fetchone()[0]
    conn.close()
    return jsonify(
        {
            "products": products_count,
            "customers": customers_count,
            "orders": orders_count,
            "revenue_paid": revenue_paid,
            "revenue_all": revenue_all,
        }
    )


# ---------- PRODUCTS CRUD ----------
@app.route("/api/products", methods=["GET"])
def list_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/products", methods=["POST"])
def create_product():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Vui lòng nhập tên sản phẩm"}), 400
    try:
        price = int(data.get("price") or 0)
        stock = int(data.get("stock") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Giá bán và tồn kho phải là số nguyên hợp lệ"}), 400
    if price < 0:
        return jsonify({"error": "Giá bán không được là số âm"}), 400
    if stock < 0:
        return jsonify({"error": "Tồn kho không được là số âm"}), 400

    p_type = (data.get("type") or "physical").strip()
    if p_type not in ("physical", "digital", "service"):
        p_type = "physical"
    if p_type != "physical":
        stock = 0

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, type, price, stock, description) VALUES (?, ?, ?, ?, ?)",
        (name, p_type, price, stock, (data.get("description") or "").strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Đã thêm sản phẩm"}), 201


@app.route("/api/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Vui lòng nhập tên sản phẩm"}), 400
    try:
        price = int(data.get("price") or 0)
        stock = int(data.get("stock") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Giá bán và tồn kho phải là số nguyên hợp lệ"}), 400
    if price < 0:
        return jsonify({"error": "Giá bán không được là số âm"}), 400
    if stock < 0:
        return jsonify({"error": "Tồn kho không được là số âm"}), 400

    p_type = (data.get("type") or "physical").strip()
    if p_type not in ("physical", "digital", "service"):
        p_type = "physical"
    if p_type != "physical":
        stock = 0

    conn = get_db()
    conn.execute(
        "UPDATE products SET name=?, type=?, price=?, stock=?, description=? WHERE id=?",
        (name, p_type, price, stock, (data.get("description") or "").strip(), pid),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Đã cập nhật sản phẩm"})


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    conn = get_db()
    used = conn.execute("SELECT COUNT(*) FROM orders WHERE product_id=?", (pid,)).fetchone()[0]
    if used:
        conn.close()
        return jsonify({"error": f"Sản phẩm đang có trong {used} đơn hàng, không thể xóa"}), 400
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Đã xóa sản phẩm"})


# ---------- CUSTOMERS CRUD ----------
@app.route("/api/customers", methods=["GET"])
def list_customers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM customers ORDER BY id ASC").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["created_at"] = d.get("registered_at") or ""
        out.append(d)
    return jsonify(out)


@app.route("/api/customers", methods=["POST"])
def create_customer():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Vui lòng nhập tên khách hàng"}), 400

    ok_phone, phone_val = validate_phone(data.get("phone"))
    if not ok_phone:
        return jsonify({"error": phone_val}), 400
    if not phone_val:
        return jsonify({"error": "Vui lòng nhập số điện thoại hợp lệ (10 chữ số bắt đầu bằng 0)"}), 400

    ok_email, email_val = validate_email(data.get("email"))
    if not ok_email:
        return jsonify({"error": email_val}), 400

    note_val = (data.get("note") or data.get("zalo") or "").strip()
    trigger_seq = (
        bool(data.get("trigger_sequence"))
        or ("waitlist" in note_val.lower())
        or ("voucher" in note_val.lower())
        or ("ưu đãi" in note_val.lower())
    )

    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM customers WHERE phone = ? LIMIT 1", (phone_val,)).fetchone()
        if existing:
            cid = existing["id"]
            conn.execute(
                "UPDATE customers SET name = ?, email = COALESCE(NULLIF(?, ''), email), note = ? WHERE id = ?",
                (name, email_val, note_val, cid),
            )
            new_id = cid
        else:
            now_str = (data.get("registered_at") or data.get("created_at") or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute(
                "INSERT INTO customers (name, phone, email, zalo, registered_at, note) VALUES (?, ?, ?, ?, ?, ?)",
                (name, phone_val, email_val, phone_val, now_str, note_val),
            )
            new_id = cur.lastrowid

        seq_info = []
        if email_val and trigger_seq:
            seq_info = trigger_email_sequence(conn, name, email_val)
        conn.commit()
        return jsonify({"id": new_id, "message": "Đã thêm khách hàng", "email_sequence": seq_info}), 201
    finally:
        conn.close()


@app.route("/api/customers/<int:cid>", methods=["PUT"])
def update_customer(cid):
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Vui lòng nhập tên khách hàng"}), 400

    ok_phone, phone_val = validate_phone(data.get("phone"))
    if not ok_phone:
        return jsonify({"error": phone_val}), 400

    ok_email, email_val = validate_email(data.get("email"))
    if not ok_email:
        return jsonify({"error": email_val}), 400

    note_val = (data.get("note") or data.get("zalo") or "").strip()

    conn = get_db()
    conn.execute(
        "UPDATE customers SET name=?, phone=COALESCE(NULLIF(?, ''), phone), email=?, zalo=COALESCE(NULLIF(?, ''), zalo), note=? WHERE id=?",
        (name, phone_val, email_val, phone_val, note_val, cid),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Đã cập nhật khách hàng"})


@app.route("/api/customers/<int:cid>", methods=["DELETE"])
def delete_customer(cid):
    conn = get_db()
    used = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_id=?", (cid,)).fetchone()[0]
    if used:
        conn.close()
        return jsonify({"error": f"Khách hàng đang có {used} đơn hàng, không thể xóa"}), 400
    conn.execute("DELETE FROM customers WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Đã xóa khách hàng"})


# ---------- WAITLIST & EMAIL SEQUENCE API ----------
@app.route("/api/waitlist", methods=["POST", "OPTIONS"])
def register_waitlist():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(force=True, silent=True)
    if not data:
        data = request.form.to_dict() if request.form else {}

    name = (data.get("name") or data.get("fullname") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    occasion = (data.get("occasion") or data.get("style_group") or "").strip()
    extra_note = (data.get("note") or "").strip()

    if not name or not email:
        return jsonify({"ok": False, "error": "Khách điền giúp em đầy đủ Họ tên và Email nhận mã ưu đãi nha."}), 400

    ok_phone, phone_val = validate_phone(phone)
    if not ok_phone:
        return jsonify({"ok": False, "error": phone_val}), 400

    ok_email, email_val = validate_email(email)
    if not ok_email:
        return jsonify({"ok": False, "error": email_val}), 400

    note_parts = ["Đăng ký Waitlist nhận voucher BIBI15NEW"]
    if occasion:
        note_parts.append(f"Dịp tặng: {occasion}")
    if extra_note:
        note_parts.append(extra_note)
    full_note = " | ".join(note_parts)

    conn = get_db()
    try:
        deliver_email = re.sub(r"\+[^@]+@", "@", email_val) if "+test" in email_val.lower() else email_val
        existing = None
        if phone_val:
            existing = conn.execute("SELECT id FROM customers WHERE phone = ? LIMIT 1", (phone_val,)).fetchone()
        if not existing:
            existing = conn.execute(
                "SELECT id FROM customers WHERE LOWER(email) = LOWER(?) LIMIT 1",
                (deliver_email,),
            ).fetchone()

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existing:
            customer_id = existing["id"]
            conn.execute(
                "UPDATE customers SET name = ?, email = ?, note = ? WHERE id = ?",
                (name, deliver_email, full_note, customer_id),
            )
        else:
            p_insert = phone_val or f"099{int(time.time()) % 10000000:07d}"
            cur = conn.execute(
                "INSERT INTO customers (name, phone, email, zalo, registered_at, note) VALUES (?, ?, ?, ?, ?, ?)",
                (name, p_insert, deliver_email, p_insert, now_str, full_note),
            )
            customer_id = cur.lastrowid

        seq_results = trigger_email_sequence(conn, name, email_val)
        conn.commit()
        return jsonify(
            {
                "ok": True,
                "customer_id": customer_id,
                "voucher": "BIBI15NEW",
                "message": "Đã đăng ký nhận ưu đãi và kích hoạt chuỗi 3 email tự động thành công!",
                "sequence": seq_results,
            }
        )
    finally:
        conn.close()


@app.route("/api/email-queue", methods=["GET"])
def list_email_queue():
    process_due_emails()
    conn = get_db()
    rows = conn.execute("SELECT * FROM email_queue ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------- ORDERS CRUD ----------
@app.route("/api/orders", methods=["GET"])
def list_orders():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT o.id, o.order_code, o.customer_id, c.name AS customer_name, c.phone AS customer_phone, c.email AS customer_email,
               o.product_id, p.name AS product_name, p.type AS product_type,
               o.quantity, o.amount, o.amount AS total, o.status, o.payment_method,
               o.shipping_address, o.size, o.color, o.note, o.order_date, o.order_date AS created_at, o.source
        FROM orders o
        LEFT JOIN customers c ON c.id = o.customer_id
        LEFT JOIN products p ON p.id = o.product_id
        ORDER BY o.id ASC
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    try:
        customer_id = data.get("customer_id")
        product_id = data.get("product_id")

        if not customer_id and (data.get("name") or data.get("customer_name") or data.get("phone")):
            c_name = (data.get("name") or data.get("customer_name") or "Khách đặt hoa Web").strip()
            _, c_phone = validate_phone(data.get("phone"))
            _, c_email = validate_email(data.get("email"))
            c_addr = (data.get("address") or data.get("shipping_address") or "").strip()
            c_note = f"Khách đặt hoa Web. Địa chỉ: {c_addr}".strip()
            existing_c = None
            if c_phone:
                existing_c = conn.execute("SELECT id FROM customers WHERE phone = ? LIMIT 1", (c_phone,)).fetchone()
            if not existing_c and c_email:
                existing_c = conn.execute("SELECT id FROM customers WHERE LOWER(email) = LOWER(?) LIMIT 1", (c_email,)).fetchone()
            if existing_c:
                customer_id = existing_c["id"]
                if c_email:
                    conn.execute("UPDATE customers SET email = ? WHERE id = ?", (c_email, customer_id))
            else:
                p_ins = c_phone or f"098{int(time.time()) % 10000000:07d}"
                cur_c = conn.execute(
                    "INSERT INTO customers (name, phone, email, zalo, registered_at, note) VALUES (?, ?, ?, ?, ?, ?)",
                    (c_name, p_ins, c_email, p_ins, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), c_note),
                )
                customer_id = cur_c.lastrowid

        if not product_id and (data.get("product") or data.get("product_name")):
            p_name = (data.get("product") or data.get("product_name") or "Bó Hoa Bibi Flower").strip()
            existing_p = conn.execute("SELECT id FROM products WHERE LOWER(name) = LOWER(?) LIMIT 1", (p_name,)).fetchone()
            if not existing_p:
                first_part = p_name.split("(")[0].strip()
                existing_p = conn.execute("SELECT id FROM products WHERE name LIKE ? LIMIT 1", (f"%{first_part}%",)).fetchone()
            if existing_p:
                product_id = existing_p["id"]
            else:
                unit_p = int(data.get("price") or data.get("total") or data.get("amount") or 280000)
                cur_p = conn.execute(
                    "INSERT INTO products (name, type, price, stock, description) VALUES (?, 'physical', ?, 50, 'Mẫu hoa đặt từ Website')",
                    (p_name, unit_p),
                )
                product_id = cur_p.lastrowid

        try:
            customer_id = int(customer_id or 0)
            product_id = int(product_id or 0)
            qty = int(data.get("quantity") or data.get("qty") or 1)
        except (ValueError, TypeError):
            return jsonify({"error": "Dữ liệu khách hàng, sản phẩm hoặc số lượng không hợp lệ"}), 400

        if qty <= 0:
            return jsonify({"error": "Số lượng phải lớn hơn 0"}), 400

        cust = conn.execute("SELECT id, name, email FROM customers WHERE id=?", (customer_id,)).fetchone()
        if not cust:
            return jsonify({"error": "Vui lòng chọn khách hàng hợp lệ"}), 400

        prod = conn.execute("SELECT id, name, type, price, stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not prod:
            return jsonify({"error": "Không tìm thấy sản phẩm"}), 404

        current_stock = int(prod["stock"] or 0)
        if prod["type"] == "physical":
            if current_stock < qty:
                return (
                    jsonify(
                        {
                            "error": f"Sản phẩm '{prod['name']}' chỉ còn {current_stock} trong kho (yêu cầu {qty}). Không thể tạo đơn!"
                        }
                    ),
                    400,
                )
            new_stock = current_stock - qty
            conn.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))
        else:
            new_stock = prod["stock"]

        total = data.get("total") if data.get("total") not in (None, "") else data.get("amount")
        if total in (None, "", 0, "0"):
            total = int(prod["price"]) * qty
        else:
            try:
                total = int(total)
            except (ValueError, TypeError):
                return jsonify({"error": "Tổng tiền không hợp lệ"}), 400
            if total < 0:
                return jsonify({"error": "Tổng tiền không được là số âm"}), 400

        now_str = (data.get("order_date") or data.get("created_at") or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note_str = (data.get("note") or "").strip()
        shipping_addr = (data.get("address") or data.get("shipping_address") or "").strip()
        size_val = (data.get("size") or "Tiêu chuẩn").strip()
        color_val = (data.get("color") or "Mặc định").strip()

        next_num = (conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM orders").fetchone()[0]) or 1
        order_code_in = (data.get("order_code") or "").strip() or f"BIBI{next_num:04d}"

        # Avoid duplicate order_code
        dup_code = conn.execute("SELECT id FROM orders WHERE order_code = ?", (order_code_in,)).fetchone()
        if dup_code:
            order_code_in = f"{order_code_in}-{next_num}"

        cur = conn.execute(
            """
            INSERT INTO orders (order_code, customer_id, product_id, quantity, amount, status, order_date, shipping_address, size, color, note, source, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'web', ?)
            """,
            (
                order_code_in,
                customer_id,
                product_id,
                qty,
                total,
                data.get("status", "cho_thanh_toan"),
                now_str,
                shipping_addr,
                size_val,
                color_val,
                note_str,
                (data.get("payment_method") or "Chuyển khoản QR (SePay)").strip(),
            ),
        )
        new_id = cur.lastrowid
        conn.execute(
            "INSERT OR IGNORE INTO web_order_sync (order_code, order_id, synced_at) VALUES (?, ?, ?)",
            (order_code_in, new_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()

        email_to = (data.get("customer_email") or data.get("email") or cust["email"] or "").strip()
        email_result = None
        if email_to:
            email_result = send_order_confirmation_email(
                cust["name"], email_to, order_code_in, prod["name"], qty, total
            )

        return (
            jsonify(
                {
                    "id": new_id,
                    "order_code": order_code_in,
                    "product_type": prod["type"],
                    "remaining_stock": new_stock,
                    "email_sent": bool(email_result and email_result.get("ok")),
                    "email_sent_to": email_to if (email_result and email_result.get("ok")) else "",
                    "email_result": email_result,
                    "message": "Đã tạo đơn hàng "
                    + order_code_in
                    + (f" (đã trừ {qty} khỏi tồn kho)" if prod["type"] == "physical" else " (sản phẩm số/dịch vụ — không trừ kho)"),
                }
            ),
            201,
        )
    finally:
        conn.close()


@app.route("/api/orders/<int:oid>", methods=["PUT"])
def update_order(oid):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    old = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not old:
        conn.close()
        return jsonify({"error": "Không tìm thấy đơn hàng"}), 404

    try:
        new_pid = int(data.get("product_id") or old["product_id"])
        new_cid = int(data.get("customer_id") or old["customer_id"])
        new_qty = int(data.get("quantity") or old["quantity"])
    except (ValueError, TypeError):
        conn.close()
        return jsonify({"error": "Dữ liệu đơn hàng không hợp lệ"}), 400
    if new_qty <= 0:
        conn.close()
        return jsonify({"error": "Số lượng phải lớn hơn 0"}), 400

    old_prod = conn.execute("SELECT * FROM products WHERE id=?", (old["product_id"],)).fetchone()
    if old_prod and old_prod["type"] == "physical":
        conn.execute(
            "UPDATE products SET stock = COALESCE(stock, 0) + ? WHERE id=?",
            (old["quantity"], old["product_id"]),
        )

    new_prod = conn.execute("SELECT * FROM products WHERE id=?", (new_pid,)).fetchone()
    if not new_prod:
        conn.rollback()
        conn.close()
        return jsonify({"error": "Không tìm thấy sản phẩm mới"}), 404

    if new_prod["type"] == "physical":
        avail = int(new_prod["stock"] or 0)
        if avail < new_qty:
            conn.rollback()
            conn.close()
            return (
                jsonify(
                    {
                        "error": f"Sản phẩm '{new_prod['name']}' chỉ còn {avail} trong kho (yêu cầu {new_qty})"
                    }
                ),
                400,
            )
        conn.execute("UPDATE products SET stock = COALESCE(stock, 0) - ? WHERE id=?", (new_qty, new_pid))

    total = data.get("total") if data.get("total") not in (None, "") else data.get("amount")
    if total in (None, "", 0, "0"):
        total = int(new_prod["price"]) * new_qty
    else:
        try:
            total = int(total)
        except (ValueError, TypeError):
            conn.rollback()
            conn.close()
            return jsonify({"error": "Tổng tiền không hợp lệ"}), 400
        if total < 0:
            conn.rollback()
            conn.close()
            return jsonify({"error": "Tổng tiền không được là số âm"}), 400

    conn.execute(
        """
        UPDATE orders
        SET customer_id=?, product_id=?, quantity=?, amount=?, status=?, payment_method=?, note=?
        WHERE id=?
        """,
        (
            new_cid,
            new_pid,
            new_qty,
            total,
            data.get("status", old["status"]),
            (data.get("payment_method") or old["payment_method"] or "Chuyển khoản QR (SePay)").strip(),
            (data.get("note") or old["note"] or "").strip(),
            oid,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Đã cập nhật đơn hàng"})


@app.route("/api/orders/<int:oid>", methods=["DELETE"])
def delete_order(oid):
    conn = get_db()
    old = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not old:
        conn.close()
        return jsonify({"error": "Không tìm thấy đơn hàng"}), 404
    prod = conn.execute("SELECT * FROM products WHERE id=?", (old["product_id"],)).fetchone()
    if prod and prod["type"] == "physical":
        conn.execute("UPDATE products SET stock = COALESCE(stock, 0) + ? WHERE id=?", (old["quantity"], old["product_id"]))
    conn.execute("DELETE FROM web_order_sync WHERE order_id=?", (oid,))
    conn.execute("DELETE FROM orders WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Đã xóa đơn hàng (đã hoàn lại tồn kho nếu là sản phẩm vật lý)"})


# ---------- ĐỒNG BỘ TỰ ĐỘNG TỪ WEBSITE (GOOGLE SHEET + SEPAY) VỀ BRAIN.DB ----------
_sync_state = {
    "last_sync": None,
    "last_result": "Chưa chạy",
    "imported_total": 0,
    "updated_total": 0,
}


def load_sync_config():
    cfg = {
        "sheet_web_app_url": os.getenv(
            "SHEET_WEB_APP_URL",
            "https://script.google.com/macros/s/AKfycbzLVl9P2RV8SK78ejbCR6zhfySQ58Cnj75GE2SXaWL6mnfsbLyhs6A_J8h8_Xnxf-vhQg/exec",
        ).strip(),
        "sync_token": os.getenv("SYNC_TOKEN", "3zp7FNmMzvs383ydY4sddsLUuR0eaR9w").strip(),
        "sync_interval_seconds": int(os.getenv("SYNC_INTERVAL_SECONDS", "4") or 4),
    }
    if os.path.exists(SYNC_CONFIG_PATH):
        try:
            with open(SYNC_CONFIG_PATH, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                if not os.getenv("SHEET_WEB_APP_URL") and file_cfg.get("sheet_web_app_url"):
                    cfg["sheet_web_app_url"] = file_cfg["sheet_web_app_url"]
                if not os.getenv("SYNC_TOKEN") and file_cfg.get("sync_token"):
                    cfg["sync_token"] = file_cfg["sync_token"]
                if not os.getenv("SYNC_INTERVAL_SECONDS") and file_cfg.get("sync_interval_seconds"):
                    cfg["sync_interval_seconds"] = file_cfg["sync_interval_seconds"]
        except Exception:
            pass
    return cfg


def map_sheet_status(sheet_status, received=0, total=0):
    s = (sheet_status or "").strip().lower()
    try:
        if int(received or 0) > 0 and int(total or 0) > 0 and int(received) >= int(total):
            return "da_thanh_toan"
    except Exception:
        pass
    if "đã thanh toán" in s or s in ("da_thanh_toan", "paid", "hoan_thanh", "completed", "success"):
        return "da_thanh_toan"
    if "hủy" in s or s in ("da_huy", "cancelled", "canceled"):
        return "da_huy"
    if "xử lý" in s or "giao" in s or s in ("dang_xu_ly", "dang_giao"):
        return "dang_giao"
    return "cho_thanh_toan"


def sync_from_sheet_once():
    cfg = load_sync_config()
    url = (cfg.get("sheet_web_app_url") or "").strip()
    token = (cfg.get("sync_token") or "").strip()
    if not url or not token:
        _sync_state["last_result"] = "Chưa cấu hình URL hoặc token"
        return {"ok": False, "error": _sync_state["last_result"]}

    sep = "&" if "?" in url else "?"
    full_url = f"{url}{sep}action=export&token={urllib.parse.quote(token)}"

    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "BibiFlower-Sync/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        _sync_state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _sync_state["last_result"] = f"Lỗi kết nối: {e}"
        return {"ok": False, "error": str(e)}

    if not payload.get("ok"):
        _sync_state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _sync_state["last_result"] = payload.get("error", "Google Sheet trả về lỗi")
        return {"ok": False, "error": _sync_state["last_result"]}

    remote_orders = payload.get("orders") or []
    conn = get_db()
    imported = 0
    updated = 0

    try:
        for ro in remote_orders:
            code = str(ro.get("order_code") or "").strip()
            if not code or not code.upper().startswith("BIBI"):
                continue

            name = str(ro.get("name") or "Khách hàng Web").strip()
            raw_phone = str(ro.get("phone") or "").strip()
            phone = ("0" + raw_phone.lstrip("0")) if raw_phone else ""
            email = str(ro.get("email") or "").strip()
            raw_note = str(ro.get("note") or "").strip()
            if not email and raw_note:
                m_em = re.search(r"Email:\s*([^\s|]+@[^\s|]+)", raw_note, re.IGNORECASE)
                if m_em:
                    email = m_em.group(1).strip()

            address = str(ro.get("address") or "").strip()
            product_name = str(ro.get("product") or "Sản phẩm Web").strip()
            size = str(ro.get("size") or "Tiêu chuẩn").strip()
            color = str(ro.get("color") or "Mặc định").strip()
            qty = max(1, int(ro.get("qty") or ro.get("quantity") or 1))
            total = int(ro.get("total") or 0)
            received = int(ro.get("received") or 0)
            new_status = map_sheet_status(ro.get("status"), received, total)
            paid_at = str(ro.get("paid_at") or "").strip()

            ts_raw = str(ro.get("created_at") or ro.get("time") or "").strip()
            order_date = ts_raw if ts_raw else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            synced = conn.execute(
                "SELECT order_id FROM web_order_sync WHERE order_code = ?",
                (code,),
            ).fetchone()
            if not synced:
                synced = conn.execute(
                    "SELECT id AS order_id FROM orders WHERE order_code = ?",
                    (code,),
                ).fetchone()

            if synced:
                local_oid = synced["order_id"]
                cur_ord = conn.execute("SELECT status, note, customer_id FROM orders WHERE id = ?", (local_oid,)).fetchone()
                if cur_ord:
                    if email and cur_ord["customer_id"]:
                        conn.execute(
                            "UPDATE customers SET email = ? WHERE id = ? AND (email IS NULL OR email = '')",
                            (email, cur_ord["customer_id"]),
                        )
                    if cur_ord["status"] != new_status and new_status in ("da_thanh_toan", "hoan_thanh", "success"):
                        note_text = cur_ord["note"] or ""
                        if "SePay" not in note_text and received > 0:
                            note_text = (note_text + f" | Đã TT {received:,}đ qua SePay ({paid_at})").strip(" |")
                        conn.execute(
                            "UPDATE orders SET status = ?, note = ? WHERE id = ?",
                            (new_status, note_text, local_oid),
                        )
                        updated += 1
                continue

            cust = None
            if phone:
                cust = conn.execute("SELECT id, email FROM customers WHERE phone = ? LIMIT 1", (phone,)).fetchone()
            if not cust and email:
                cust = conn.execute("SELECT id, email FROM customers WHERE LOWER(email) = LOWER(?) LIMIT 1", (email,)).fetchone()
            if cust:
                customer_id = cust["id"]
                if email and not (cust["email"] or "").strip():
                    conn.execute("UPDATE customers SET email = ? WHERE id = ?", (email, customer_id))
            else:
                p_ins = phone or f"097{int(time.time()) % 10000000:07d}"
                cust_note = f"Khách đặt trên Web ({code}). Địa chỉ: {address}" if address else f"Khách đặt trên Web ({code})"
                cur_c = conn.execute(
                    "INSERT INTO customers (name, phone, email, zalo, registered_at, note) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, p_ins, email, p_ins, order_date, cust_note),
                )
                customer_id = cur_c.lastrowid

            prod = conn.execute(
                "SELECT id, type, price, stock FROM products WHERE LOWER(name) = LOWER(?) LIMIT 1",
                (product_name,),
            ).fetchone()
            if not prod:
                first_part = product_name.split("(")[0].strip()
                prod = conn.execute(
                    "SELECT id, type, price, stock FROM products WHERE name LIKE ? LIMIT 1",
                    (f"%{first_part}%",),
                ).fetchone()

            if prod:
                product_id = prod["id"]
                if prod["type"] == "physical" and int(prod["stock"] or 0) >= qty:
                    conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, product_id))
            else:
                unit_price = int(total / qty) if total > 0 else 0
                cur_p = conn.execute(
                    "INSERT INTO products (name, type, price, stock, description) VALUES (?, 'physical', ?, 50, 'Tự động thêm từ đơn hàng trên Website')",
                    (product_name, unit_price),
                )
                product_id = cur_p.lastrowid

            note_parts = []
            if raw_note:
                note_parts.append(raw_note)
            if new_status in ("da_thanh_toan", "success") and received > 0:
                note_parts.append(f"Đã TT {received:,}đ qua SePay")

            cur_o = conn.execute(
                """
                INSERT INTO orders (order_code, customer_id, product_id, quantity, amount, status, order_date, shipping_address, size, color, note, source, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'web', 'Chuyển khoản QR (SePay)')
                """,
                (code, customer_id, product_id, qty, total, new_status, order_date, address, size, color, " | ".join(note_parts)),
            )
            local_order_id = cur_o.lastrowid

            conn.execute(
                "INSERT OR IGNORE INTO web_order_sync (order_code, order_id, synced_at) VALUES (?, ?, ?)",
                (code, local_order_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            imported += 1

            if email:
                try:
                    send_order_confirmation_email(name, email, code, product_name, qty, total)
                except Exception:
                    pass

        conn.commit()
    finally:
        conn.close()

    _sync_state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _sync_state["last_result"] = f"OK (thêm {imported} đơn mới, cập nhật {updated} đơn)"
    _sync_state["imported_total"] += imported
    _sync_state["updated_total"] += updated
    return {"ok": True, "imported": imported, "updated": updated, "state": _sync_state}


def background_sync_loop():
    time.sleep(1)
    while True:
        try:
            sync_from_sheet_once()
        except Exception as e:
            _sync_state["last_result"] = f"Lỗi: {e}"
        cfg = load_sync_config()
        interval = max(3, int(cfg.get("sync_interval_seconds") or 4))
        time.sleep(interval)


@app.route("/api/sync", methods=["POST", "GET"])
def manual_sync():
    return jsonify(sync_from_sheet_once())


@app.route("/api/sync/status", methods=["GET"])
def sync_status():
    return jsonify(_sync_state)


@app.route("/api/order-status/<order_code>", methods=["GET"])
def check_order_status(order_code):
    code = (order_code or "").strip()
    if not code:
        return jsonify({"ok": False, "paid": False}), 400
    try:
        sync_from_sheet_once()
    except Exception:
        pass
    conn = get_db()
    row = conn.execute(
        "SELECT id, status, amount, note FROM orders WHERE order_code = ? ORDER BY id DESC LIMIT 1",
        (code,),
    ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id, status, amount, note FROM orders WHERE note LIKE ? ORDER BY id DESC LIMIT 1",
            (f"%{code}%",),
        ).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": True, "found": False, "paid": False, "status": "pending"})
    paid = row["status"] in ("da_thanh_toan", "hoan_thanh", "paid", "success")
    return jsonify(
        {
            "ok": True,
            "found": True,
            "paid": paid,
            "status": row["status"],
            "total": row["amount"],
        }
    )


threading.Thread(target=background_sync_loop, daemon=True).start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000") or 5000)
    debug_mode = os.getenv("FLASK_DEBUG", "0").strip() in ("1", "true", "True")
    print("=" * 60)
    print(f"  Bibi Flower Server đang chạy tại: http://127.0.0.1:{port}/admin")
    print("  Đã bật tự động đồng bộ đơn từ Website + SePay + Resend Email về brain.db!")
    print("=" * 60)
    app.run(host="127.0.0.1", port=port, debug=debug_mode)
