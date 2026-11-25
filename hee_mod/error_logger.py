"""
error_logger.py — Hệ thống ghi nhận và đọc logs lỗi command cho HEe Sentinel.
Lưu log vào file cục bộ và hỗ trợ lệnh truy vấn log trực tiếp cho Admin / Role HE.
"""

import os
import sys
import time
import traceback
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "command_errors.log")

def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)

def record_error(
    command_name: str,
    user_name: str,
    user_id: int,
    guild_id: int | None,
    channel_id: int | None,
    error: Exception
) -> str:
    """
    Ghi nhận lỗi vào file log.
    Trả về: Mã lỗi (Error ID) ngắn để người dùng báo cho Admin.
    """
    ensure_log_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    err_id = f"ERR-{int(time.time())}"
    
    tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    
    log_entry = (
        f"================================================================================\n"
        f"[{timestamp}] ID: {err_id}\n"
        f"Lệnh: /{command_name} | Người gọi: {user_name} ({user_id})\n"
        f"Guild: {guild_id} | Channel: {channel_id}\n"
        f"Ngoại lệ: {type(error).__name__}: {str(error)}\n"
        f"Chi tiết Traceback:\n{tb_str}"
        f"================================================================================\n\n"
    )
    
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[ERROR] Không thể ghi log file: {e}", file=sys.stderr)
        
    return err_id

def get_recent_logs(lines_count: int = 40) -> str:
    """
    Đọc N dòng log lỗi mới nhất từ file.
    """
    if not os.path.exists(ERROR_LOG_FILE):
        return "Chưa có log lỗi nào được ghi nhận."
    
    try:
        with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return "File log đang trống."
            return "".join(lines[-lines_count:])
    except Exception as e:
        return f"Lỗi khi đọc file log: {e}"

def clear_logs() -> bool:
    """Xóa file log lỗi."""
    if os.path.exists(ERROR_LOG_FILE):
        try:
            with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
                f.truncate(0)
            return True
        except Exception:
            return False
    return True
