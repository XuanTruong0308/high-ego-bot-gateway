"""
economy_db.py — Quản lý Database SQLite dùng chung cho điểm thưởng (HEe Vault) và trừ điểm vi phạm (HEe Sentinel).
Lưu số dư điểm, lịch sử điểm danh daily, số lần vi phạm và log giao dịch kiểm toán.
"""

import sqlite3
import time
import os
from datetime import datetime

SHARED_DB_PATH = os.path.join(os.path.dirname(__file__), "economy.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(SHARED_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Khởi tạo các bảng dữ liệu liên quan đến Điểm thưởng và Vi phạm."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_balance (
                user_id         TEXT NOT NULL,
                guild_id        TEXT NOT NULL,
                points          REAL DEFAULT 0,
                last_daily_date TEXT DEFAULT NULL,
                strike_count    INTEGER DEFAULT 0,
                updated_at      REAL NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS transaction_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT NOT NULL,
                guild_id        TEXT NOT NULL,
                amount          REAL NOT NULL,
                balance_after   REAL NOT NULL,
                action_type     TEXT NOT NULL, -- 'daily', 'admin_add', 'penalty'
                reason          TEXT NOT NULL,
                operator_id     TEXT DEFAULT NULL,
                created_at      REAL NOT NULL
            );
        """)


def get_user(user_id: int, guild_id: int) -> sqlite3.Row:
    """Lấy thông tin tài khoản, nếu chưa có thì khởi tạo."""
    now = time.time()
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO user_balance (user_id, guild_id, points, strike_count, updated_at)
            VALUES (?, ?, 0, 0, ?)
        """, (str(user_id), str(guild_id), now))
        return conn.execute(
            "SELECT * FROM user_balance WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        ).fetchone()


def claim_daily(user_id: int, guild_id: int, reward_points: float = 1.0) -> tuple[bool, str, float]:
    """
    Điểm danh nhận 1 điểm / ngày.
    Trả về: (Thành công hay không, Thông báo, Số dư mới)
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    user = get_user(user_id, guild_id)
    if user['last_daily_date'] == today_str:
        return False, "Hôm nay bạn đã điểm danh rồi! Hãy quay lại vào ngày mai nhé.", user['points']

    now = time.time()
    new_points = min(100.0, user['points'] + reward_points)  # Giới hạn max 100 điểm
    with _connect() as conn:
        conn.execute("""
            UPDATE user_balance 
            SET points=?, last_daily_date=?, updated_at=?
            WHERE user_id=? AND guild_id=?
        """, (new_points, today_str, now, str(user_id), str(guild_id)))

        conn.execute("""
            INSERT INTO transaction_logs (user_id, guild_id, amount, balance_after, action_type, reason, created_at)
            VALUES (?, ?, ?, ?, 'daily', 'Điểm danh hằng ngày', ?)
        """, (str(user_id), str(guild_id), reward_points, new_points, now))

    return True, f"Điểm danh thành công! Bạn nhận được +{reward_points:.0f} Điểm ({int(reward_points * 1000):,} VNĐ).", new_points


def add_points_admin(user_id: int, guild_id: int, amount: float, reason: str, operator_id: int) -> float:
    """Admin/Role HE cộng hoặc trừ điểm (bắt buộc có lý do)."""
    user = get_user(user_id, guild_id)
    now = time.time()
    new_points = max(0.0, min(100.0, user['points'] + amount))

    with _connect() as conn:
        conn.execute("""
            UPDATE user_balance
            SET points=?, updated_at=?
            WHERE user_id=? AND guild_id=?
        """, (new_points, now, str(user_id), str(guild_id)))

        conn.execute("""
            INSERT INTO transaction_logs (user_id, guild_id, amount, balance_after, action_type, reason, operator_id, created_at)
            VALUES (?, ?, ?, ?, 'admin_add', ?, ?, ?)
        """, (str(user_id), str(guild_id), amount, new_points, reason, str(operator_id), now))

    return new_points


def apply_profanity_penalty(user_id: int, guild_id: int, word: str) -> tuple[int, float, float]:
    """
    Áp dụng Phương Án 1 (Bậc thang cảnh cáo vi phạm ngôn từ):
    - Lần 1: Nhắc nhở, trừ 0 điểm.
    - Lần 2: Trừ -2 điểm.
    - Lần 3: Trừ -5 điểm.
    - Lần 4 trở lên: Trừ -10 điểm.
    Trả về: (Lần vi phạm thứ mấy, Số điểm bị phạt, Số dư còn lại)
    """
    user = get_user(user_id, guild_id)
    strike = user['strike_count'] + 1
    now = time.time()

    # Tính điểm phạt theo bậc thang
    if strike == 1:
        penalty = 0.0
    elif strike == 2:
        penalty = 2.0
    elif strike == 3:
        penalty = 5.0
    else:
        penalty = 10.0

    current_points = user['points']
    new_points = max(0.0, current_points - penalty)

    with _connect() as conn:
        conn.execute("""
            UPDATE user_balance
            SET strike_count=?, points=?, updated_at=?
            WHERE user_id=? AND guild_id=?
        """, (strike, new_points, now, str(user_id), str(guild_id)))

        if penalty > 0:
            conn.execute("""
                INSERT INTO transaction_logs (user_id, guild_id, amount, balance_after, action_type, reason, created_at)
                VALUES (?, ?, ?, ?, 'penalty', ?, ?)
            """, (str(user_id), str(guild_id), -penalty, new_points, f"Phạt vi phạm ngôn từ (Lần {strike}): '{word}'", now))

    return strike, penalty, new_points
