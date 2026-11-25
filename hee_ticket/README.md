# HEe • Tribunal — Ticket Support System (P4)

> Hệ thống Ticket hỗ trợ thành viên chuyên nghiệp cho máy chủ **High Ego eSport**.

---

## 🚀 Chức Năng Cốt Lõi

1. **Bảng Điều Khiển (Panel) Dropdown:**
   - Tạo bằng lệnh `/setup-ticket-panel` (Dành cho Admin / Role HE).
   - Menu Dropdown phân loại 4 mục:
     - 🚨 Tố Giác Gian Lận / Toxic
     - 💵 Khiếu Nại & Đổi Thưởng
     - ❓ Hỏi Đáp & Hỗ Trợ Chung
     - 🏆 Đăng Ký / Hỗ Trợ Giải Đấu

2. **Kênh Ticket Riêng Tư:**
   - Ẩn với `@everyone`.
   - Chỉ có **Người tạo ticket** và thành viên có **Role HE** mới xem và trò chuyện được.

3. **Phân Quyền Thao Tác Chặt Chẽ:**
   - Nút `[🙋‍♂️ Tiếp nhận (Claim)]`: Chỉ thành viên mang **Role HE** mới được bấm.
   - Nút `[🔒 Đóng Ticket]` / Lệnh `/close-ticket`: Chỉ có **Người tạo ticket** hoặc thành viên mang **Role HE** mới có quyền đóng.

4. **Tự Động Đóng Sau 3 Giờ (Auto-Close 3h):**
   - Nếu trong phòng ticket không có phản hồi mới nào sau 3 tiếng (10,800 giây), bot sẽ tự động cảnh báo và đóng ticket.

5. **Xuất & Lưu Trữ Lịch Sử (Transcript HTML):**
   - Tự động xuất toàn bộ cuộc hội thoại ra file HTML chuyên nghiệp (avatar, hình ảnh, thời gian).
   - Lưu tại ổ cứng máy chủ: `data/transcripts/`.
   - Gửi bản sao file transcript vào tin nhắn riêng (DM) của người tạo và kênh log kiểm toán.

---

## 🛠️ Cài Đặt & Chạy Trên Windows

```powershell
cd d:\bot_disc_hee\hee_ticket
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt

# Tạo file .env và điền Token
Copy-Item .env.example .env

# Chạy bot
.\.venv\Scripts\python.exe bot.py
```
