# HEe • Gatekeeper (`hee_welcome_builder`)

Bot Welcome / Goodbye (Embed Đỏ-Đen + GIF động) và tự động tạo kênh `/build` cho **High Ego eSport (HEe)**.

## 1. Chuẩn bị trên Discord Developer Portal
1. Tạo Application mới → vào mục **Bot** → lấy **Token**.
2. Trong mục **Bot → Privileged Gateway Intents**, bật **SERVER MEMBERS INTENT** (bắt buộc để nhận sự kiện vào/ra server).
3. Vào **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Manage Channels`, `Send Messages`, `Embed Links`, `Attach Files`, `View Channels`

## 2. Cài đặt & Chạy

### Windows (PowerShell)
```powershell
cd hee_welcome_builder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Điền DISCORD_TOKEN (và GUILD_ID nếu muốn sync lệnh ngay lập tức) vào .env

python bot.py
```

### Linux / macOS (Bash)
```bash
cd hee_welcome_builder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Điền DISCORD_TOKEN (và GUILD_ID nếu muốn sync lệnh ngay lập tức) vào .env

python bot.py
```

## 3. Các lệnh Slash chính (dành cho Admin/Manage Channels)
- `/build` — Tạo Text Channel, Voice Channel hoặc Category mới và tự động gắn chức năng (`welcome`, `goodbye`, `sleep_voice`).
- `/set-banner-channel` — Gắn một kênh Text có sẵn làm kênh Welcome hoặc Goodbye.
- `/test-banner` — Gửi thử ngay banner Welcome hoặc Goodbye kèm GIF để kiểm tra.
