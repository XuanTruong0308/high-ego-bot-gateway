# HEe • Chronicle — Rank Interaction Bot (P6)

> Bot xếp hạng tương tác cho server **High Ego eSport**.
> Track XP từ tin nhắn, reaction và thời gian voice.

---

## Slash Commands

| Lệnh | Mô tả |
|---|---|
| `/rank [thanh_vien]` | Xem rank + XP của bản thân hoặc người khác |
| `/leaderboard [so_luong]` | Top N thành viên XP cao nhất (mặc định 10) |
| `/rank-info` | Xem các tier và cách kiếm XP |
| `/xp-add <thanh_vien> <so_xp>` | (Admin) Cộng/trừ XP thủ công |

---

## Hệ thống Rank

| Tier | XP cần |
|---|---|
| ⚔️ Iron | 0 – 499 |
| 🥉 Bronze | 500 – 1,999 |
| 🥈 Silver | 2,000 – 4,999 |
| 👑 Gold | 5,000 – 14,999 |
| 💎 Diamond | 15,000 – 49,999 |
| 🔥 Legend | 50,000+ |

---

## Cài đặt (Windows)

```powershell
# 1. Di chuyển vào thư mục
cd d:\bot_disc_hee\hee_rank

# 2. Tạo virtual environment
python -m venv .venv

# 3. Kích hoạt venv
.\.venv\Scripts\Activate.ps1

# 4. Cài thư viện
pip install -r requirements.txt

# 5. Tạo file .env từ mẫu
Copy-Item .env.example .env
# Mở .env và điền BOT_TOKEN thật

# 6. Chạy bot
python bot.py
```

---

## Cấu hình .env

```env
BOT_TOKEN=your_bot_token_here
GUILD_ID=1545800312302870599
XP_MSG=1
XP_REACTION=0.5
XP_VOICE_PER_MIN=2
MSG_COOLDOWN=60
```

---

## Quyền Discord cần thiết

- `Read Messages / View Channels`
- `Send Messages`
- `Embed Links`
- `Read Message History`
- `Add Reactions`

**Privileged Intents (bật trong Developer Portal):**
- ✅ Server Members Intent
- ✅ Message Content Intent
