# -*- coding: utf-8 -*-
# Mail Helper script for sending order email notifications in Python

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

# SMTP Configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "noithatbaokhang@gmail.com"
SMTP_PASS = "your_app_password_here"  # User replaces this with an app password

EMAIL_RECEIVER = "noithatbaokhang@gmail.com"
HOTLINE_DISPLAY = "0903 979 525"
OFFICE_ADDRESS = "26 DCT 15, Phường Đông Hưng Thuận, TP.HCM"

def format_price(price):
    try:
        val = float(price)
        if val <= 0:
            return f"Liên hệ Hotline / Zalo: {HOTLINE_DISPLAY}"
        return f"{int(val):,}đ".replace(",", ".")
    except (ValueError, TypeError):
        return f"Liên hệ Hotline / Zalo: {HOTLINE_DISPLAY}"

def send_order_notification_email(order_details, items):
    """
    Sends an email notification for a new order.
    
    :param order_details: dict containing (id, customer_name, customer_phone, customer_address, note)
    :param items: list of dicts containing (code, name, quantity, sale_price, original_price, price_text)
    :return: bool indicating success or failure
    """
    try:
        # Construct MIME Message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(f"Đơn hàng mới #{order_details['id']} - {order_details['customer_name']}", 'utf-8')
        msg['From'] = f"Nội Thất Bảo Khang <no-reply@noithatbaokhang.com>"
        msg['To'] = EMAIL_RECEIVER

        # Build HTML content
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
                h2 {{ color: #8b5a2b; border-bottom: 2px solid #8b5a2b; padding-bottom: 8px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #f7f7f7; }}
                .total {{ font-weight: bold; color: #8b5a2b; font-size: 1.1em; }}
                .footer {{ margin-top: 20px; font-size: 0.8em; color: #777; border-top: 1px solid #eee; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Thông tin đơn hàng mới</h2>
                <p><strong>Mã đơn hàng:</strong> #{order_details['id']}</p>
                <p><strong>Khách hàng:</strong> {order_details['customer_name']}</p>
                <p><strong>Số điện thoại:</strong> {order_details['customer_phone']}</p>
                <p><strong>Địa chỉ giao hàng:</strong> {order_details['customer_address']}</p>
                <p><strong>Ghi chú từ khách:</strong> {order_details.get('note', 'Không có')}</p>
                
                <h3>Chi tiết sản phẩm</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Mã sản phẩm</th>
                            <th>Tên sản phẩm</th>
                            <th>Số lượng</th>
                            <th>Đơn giá</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        total_calculated = 0
        has_real_prices = False

        for item in items:
            price = 0
            price_text = "Liên hệ"

            # Parse item pricing properties
            sale_price = item.get('sale_price')
            original_price = item.get('original_price')
            
            try:
                if sale_price and float(sale_price) > 0:
                    price = float(sale_price)
                    price_text = format_price(price)
                    total_calculated += price * int(item['quantity'])
                    has_real_prices = True
                elif original_price and float(original_price) > 0:
                    price = float(original_price)
                    price_text = format_price(price)
                    total_calculated += price * int(item['quantity'])
                    has_real_prices = True
                elif item.get('price_text'):
                    price_text = item['price_text']
            except (ValueError, TypeError):
                pass

            html_content += f"""
                        <tr>
                            <td>{item['code']}</td>
                            <td>{item['name']}</td>
                            <td>{item['quantity']}</td>
                            <td>{price_text}</td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>
        """

        if has_real_prices:
            html_content += f"<p class='total'>Tổng số tiền đơn hàng: {format_price(total_calculated)}</p>"
        else:
            html_content += "<p class='total'>Tổng số tiền đơn hàng: Liên hệ thống nhất báo giá</p>"

        html_content += f"""
                <div class="footer">
                    <p>Website: Nội Thất Bảo Khang</p>
                    <p>Địa chỉ văn phòng: {OFFICE_ADDRESS}</p>
                    <p>Hotline: {HOTLINE_DISPLAY}</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # Connect to SMTP Server
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        # Non-blocking log, fallback safely
        import sys
        print(f"Failed to send email: {e}. (SMTP is not configured)", file=sys.stderr)
        return False
