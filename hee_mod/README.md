# HEe • Sentinel — AutoMod & Quick Delete & Debugger (P3)

> Bot giám sát trật tự, kiểm duyệt ngôn từ cực đoan, hỗ trợ Role **HE** xóa nhanh tin nhắn bằng icon và ghi nhận logs lỗi cho server **High Ego eSport**.

---

## 🚀 Chức Năng Chính

1. **Lọc từ tục tĩu cực đoan (Profanity AutoMod):**
   - Tự động xóa ngay lập tức các tin nhắn chứa từ ngữ bậy bạ (`cặc`, `lồn`, `địt mẹ mày`, `đụ má`,...) kể cả khi cố tình lách luật (`c.ặ.c`, `l_ồ_n`,...).
   - Bắn cảnh báo nhẹ tự biến mất sau 6 giây.
   - Ghi log vào kênh Mod (nếu có cài `MOD_LOG_CHANNEL_ID`).

2. **Role HE Thả Tick Xanh (`✅`) Xóa Tin Nhắn Sau 5 Giây:**
   - Khi bất kỳ ai có role **`HE`** thả reaction `✅` vào bất kỳ tin nhắn nào trong server:
     - Bot thả icon đồng hồ cát `⏳`.
     - Chờ đúng **5 giây** rồi xóa sạch tin nhắn đó.

3. **Ghi Nhận & Đọc Logs Lỗi Lệnh (Debugger):**
   - Bắt toàn bộ lỗi khi gõ slash command (`/`), ghi chi tiết Traceback vào file `logs/command_errors.log`.
   - Lệnh `/debug-logs` dành riêng cho Role **HE** và **Admin** để kiểm tra lỗi ngay trong Discord.
   - Lệnh `/clear-logs` cho Admin dọn dẹp file log.

---

## 🛠️ Cài Đặt & Chạy Trên Windows

```powershell
cd d:\bot_disc_hee\hee_mod
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt

# Tạo file .env và điền Token
Copy-Item .env.example .env

# Chạy bot
.\.venv\Scripts\python.exe bot.py
```

---

## 🔒 Quyền Discord Cần Cấp (Permissions)
- **Manage Messages** (Bắt buộc để xóa tin nhắn tục và xóa khi thả tick xanh)
- **Read Messages / View Channels**
- **Send Messages**
- **Embed Links**
- **Read Message History**
- **Add Reactions**

**Gateway Intents cần bật trên Developer Portal:**
- ✅ **Server Members Intent**
- ✅ **Message Content Intent** (Bắt buộc để bot đọc và lọc từ cấm)
