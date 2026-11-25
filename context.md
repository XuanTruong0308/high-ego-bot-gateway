# High Ego eSport (`HEe`) — Discord Bot Suite Context

## 1. Tổng quan dự án
- **Tổ chức / Server:** High Ego eSport (`HEe`)
- **Repository:** `https://github.com/XuanTruong0308/high-ego-bot-gateway.git`
- **Ngôn ngữ & Thư viện:** Python 3.12+ (đã kiểm thử trên Python 3.13), `discord.py >= 2.4.0,<3.0.0`, `python-dotenv >= 1.0.1`
- **Kiến trúc:** Multi-bot độc lập trong cùng 1 monorepo. Mỗi bot nằm trong 1 thư mục riêng, dùng token, `.env`, `.venv` và thư mục `data/` tách biệt hoàn toàn để dễ cách ly lỗi và vận hành ổn định 24/7 trên laptop cá nhân (8GB RAM).
- **Nhận diện thương hiệu:** Tone **Đỏ - Đen** eSports (`COLOR_HEE_RED = 0xE11D48`, `COLOR_HEE_DARK_RED = 0x881337`), banner GIF động cho sự kiện Welcome/Goodbye.

---

## 2. Lộ trình & Kiến trúc 5 Bot (Priority P1 → P5)

| Priority | Thư mục | Tên hiển thị | Trạng thái | Chức năng cốt lõi |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | `hee_welcome_builder/` | **HEe • Gatekeeper** | Đã triển khai | Welcome/Goodbye Embed Đỏ-Đen + GIF động, slash command `/build`, `/set-banner-channel`, `/test-banner`. |
| **P2** | `hee_voice_afk/` | **HEe • Warden** | Kế hoạch | Theo dõi treo voice 2 tiếng (`AFK_TIMEOUT_SECONDS=7200`, test nhanh với `30`) → kéo xuống Room Ngủ, không ngoại lệ. |
| **P3** | `hee_stats/` | **HEe • Pulse** | Kế hoạch | Tự động cập nhật kênh đếm Server Stats (Tổng thành viên, Online, Đang trong Voice) mỗi 5–10 phút để tránh rate limit. |
| **P4** | `hee_ticket/` | **HEe • Tribunal** | Kế hoạch | Hệ thống Ticket (báo cáo toxic, khiếu nại, đăng ký giải đấu) dùng Buttons/Select Menu/Modal, phân quyền riêng tư và xuất transcript khi đóng. |
| **P5** | `hee_economy/` | **HEe • Vault** | Kế hoạch | Economy SQLite, `/daily`, minigame, Shop (Custom Role màu đơn HEX, Role Icon Lv2, Gradient 2 màu HEX khi server Boost Lv3). |

---

## 3. Đặc tả chi tiết từng Bot

### P1 — `hee_welcome_builder` (`HEe • Gatekeeper`)
- **Hiển thị (Kiểu 1 — Embed Đỏ-Đen + GIF gốc):**
  - Gửi Embed tone Đỏ-Đen (avatar thành viên, tên, lời chào/tạm biệt, `#MemberCount`, thời gian tạo tài khoản) đính kèm `assets/welcome.gif` hoặc `assets/goodbye.gif` giữ nguyên độ nét gốc.
- **Slash Commands (yêu cầu quyền `Manage Channels`):**
  - `/build`: Tạo `Text Channel`, `Voice Channel`, hoặc `Category`; hỗ trợ gắn tự động chức năng `welcome`, `goodbye`, `sleep_voice` (trả về ID Room Ngủ cho bot P2) và chọn `category` / `gioi_han_nguoi`.
  - `/set-banner-channel`: Gắn kênh Text có sẵn làm kênh Welcome hoặc Goodbye.
  - `/test-banner`: Gửi thử ngay banner Welcome hoặc Goodbye tại kênh hiện tại.
- **Lưu trữ:** `data/guild_config.json` (quản lý qua `config_store.py`, ghi atomic bằng file `.tmp`).
- **Discord Developer Portal:**
  - Bật **Server Members Intent** (`Privileged Gateway Intents`).
  - OAuth2 Scopes: `bot`, `applications.commands`.
  - Bot Permissions: `Manage Channels`, `View Channels`, `Send Messages`, `Embed Links`, `Attach Files`.

### P2 — `hee_voice_afk` (`HEe • Warden`)
- **Điều kiện kéo xuống Room Ngủ (không ngoại lệ):**
  1. Tắt mic hoặc tắt loa liên tục đủ 2 giờ (`AFK_TIMEOUT_SECONDS`), **HOẶC**
  2. Mở mic nhưng trạng thái Discord chuyển sang `Idle` và không có tương tác voice/chat nào trong 2 giờ.
- **Cấu hình:** Lưu ID Room Ngủ trong `.env` hoặc qua lệnh `/set-sleep-room`.
- **Quyền cần thiết:** `Move Members`, `View Channels`, kết hợp `Voice States` + `Presences` intents.

### P3 — `hee_stats` (`HEe • Pulse`)
- Cập nhật tên các kênh đếm định kỳ 5–10 phút/lần nhằm tránh rate limit đổi tên kênh của Discord.
- Yêu cầu `Server Members` và `Presences` intents + quyền `Manage Channels`.

### P4 — `hee_ticket` (`HEe • Tribunal`)
- Tạo kênh riêng tư với `PermissionOverwrite` giữa thành viên tạo ticket và Mod/Admin.
- Hỗ trợ bảng nút tạo ticket, đóng ticket và lưu log transcript.

### P5 — `hee_economy` (`HEe • Vault`)
- Tiền tệ ảo, `/daily`, thưởng event, minigame.
- Shop Custom Role: hỗ trợ 1 mã màu HEX (cơ bản), Role Icon (Server Boost Lv2), và Enhanced Role Styles / Gradient 2 mã HEX (Server Boost Lv3 — gọi trực tiếp Discord REST API nếu `discord.py` chưa hỗ trợ field mới).

---

## 4. Cấu hình môi trường & Bảo mật

- **Tuyệt đối không commit** các file chứa secret/runtime: `.env`, `.env.*` (trừ `.env.example`), `.venv/`, `data/`, `*.db`, `*.log`.
- Các biến môi trường chuẩn trong `hee_welcome_builder/.env.example`:
  - `DISCORD_TOKEN=` (bắt buộc)
  - `GUILD_ID=` (tùy chọn, điền để sync slash command tức thì vào server)
  - `WELCOME_CHANNEL_ID=` (tùy chọn, có thể cấu hình bằng `/build` hoặc `/set-banner-channel`)
  - `GOODBYE_CHANNEL_ID=` (tùy chọn, có thể cấu hình bằng `/build` hoặc `/set-banner-channel`)
- **Mạng / Proxy:** Nếu mạng chặn `discord.com` (ví dụ mạng công ty gây timeout tại `/api/v10/gateway`), cần bật Cloudflare WARP (`1.1.1.1`) hoặc VPN trước khi chạy bot.

---

## 5. Hướng dẫn cài đặt & chạy nhanh (P1)

### Windows (PowerShell)
```powershell
cd hee_welcome_builder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Điền DISCORD_TOKEN (và GUILD_ID nếu muốn sync nhanh) vào .env
python bot.py
```

### Linux / macOS (Bash)
```bash
cd hee_welcome_builder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Điền DISCORD_TOKEN (và GUILD_ID nếu muốn sync nhanh) vào .env
python bot.py
```
