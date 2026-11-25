# High Ego eSport (HEe) — Discord Bot Suite Architecture

Tài liệu chuẩn hóa kiến trúc các bot Discord của **High Ego eSport (HEe)**.  
Được cập nhật tự động sau mỗi giai đoạn phát triển.

---

## 📌 Tổng Quan Hệ Thống

* **Máy Chủ Discord:** `High Ego eSport - HEe` (ID: `1545800312302870599`)
* **Mã Nguồn Git:** `https://github.com/XuanTruong0308/high-ego-bot-gateway.git`
* **Môi Trường Máy Chủ Chạy Bot:** Windows 10/11, PowerShell, Python 3.13.x
* **Thư Viện Chuẩn:** `discord.py >= 2.4.0, < 3.0.0`, `python-dotenv >= 1.0.1`
* **Màu Thương Hiệu (Brand Identity):**
  * Đỏ Chính (Primary Red): `#E11D48` (`0xE11D48`)
  * Đỏ Đậm / Đen (Dark Red): `#881337` (`0x881337`)

---

## 🗂️ Danh Sách Các Bot Trong Hệ Thống

| Priority | Thư Mục | Tên Bot | Trạng Thái | Mô Tả & Chức Năng |
|---|---|---|---|---|
| **P1** | `hee_welcome_builder/` | **HEe • Gatekeeper** | ✅ Hoạt động | Chào mừng / tạm biệt banner GIF, `/build`, `/set-banner-channel`, `/test-banner` |
| **P2** | `hee_rank/` | **HEe • Chronicle** | ⏳ Đã code (Chờ Intent) | Xếp hạng tương tác: XP tin nhắn, voice, reaction, lệnh `/rank`, `/leaderboard` |
| **P3** | `hee_mod/` | **HEe • Sentinel** | ✅ Đã code & push | **1.** Chặn từ ngữ tục tĩu cực đoan.<br>**2.** Role `HE` thả tick xanh `✅` -> Tự xóa tin nhắn sau 5s.<br>**3.** Đọc logs lỗi khi gõ lệnh (`/debug-logs`). |
| **P4** | `hee_ticket/` | **HEe • Tribunal** | ⏳ Tiếp theo | Ticket hỗ trợ: Phân loại dropdown, chỉ role `HE` hoặc người tạo mới được claim/đóng, tự đóng sau 3h, lưu transcript vào folder. |
| **P5** | `hee_economy/` | **HEe • Vault** | ⏳ Chờ triển khai | Tích điểm đổi tiền thật: `/daily` nhận 1 điểm = 1k VNĐ (min 50k, max 100k đổi). Chỉ role `HE` mới có quyền `/add` điểm và bắt buộc có reason. |

---

## 🚀 Hướng Dẫn Setup & Quyền Bot

### 1. `hee_welcome_builder` (P1)
- **Token:** Đã cấu hình trong `hee_welcome_builder/.env`
- **Quyền:** Send Messages, Embed Links, Attach Files

### 2. `hee_rank` (P2)
- **Token:** Cấu hình trong `hee_rank/.env`
- **Intents:** Bắt buộc bật `Server Members Intent` và `Message Content Intent`

### 3. `hee_mod` (P3)
- **Token:** Cấu hình trong `hee_mod/.env`
- **Quyền:** `Manage Messages` (quan trọng nhất để xóa tin nhắn bậy và xóa khi thả tick), `Read Message History`, `Send Messages`, `Embed Links`, `Add Reactions`
- **Intents:** Bắt buộc bật `Message Content Intent` (để đọc và quét từ cấm)

### 4. `hee_ticket` & `hee_economy` (P4, P5)
- Tuân thủ nghiêm ngặt: Quyền quản trị và duyệt yêu cầu thuộc về Role **`HE`**.
