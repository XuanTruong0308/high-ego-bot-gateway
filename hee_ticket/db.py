"""
db.py — Quản lý Database SQLite cho HEe Tribunal (P4 - Ticket Bot).
Lưu trạng thái từng ticket, thời gian tin nhắn cuối cùng để hỗ trợ auto-close sau 3 giờ.
"""

import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "tickets.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Tạo bảng lưu trữ tickets."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id      TEXT UNIQUE NOT NULL,
                guild_id        TEXT NOT NULL,
                creator_id      TEXT NOT NULL,
                category_type   TEXT NOT NULL,
                claimed_by      TEXT DEFAULT NULL,
                status          TEXT DEFAULT 'open',  -- 'open', 'closed'
                last_active_at  REAL NOT NULL,
                created_at      REAL NOT NULL,
                closed_at       REAL DEFAULT NULL,
                transcript_file TEXT DEFAULT NULL
            );
        """)


def create_ticket(channel_id: int, guild_id: int, creator_id: int, category_type: str) -> int:
    """Tạo mới một ticket và trả về ticket_id."""
    now = time.time()
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO tickets (channel_id, guild_id, creator_id, category_type, last_active_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(channel_id), str(guild_id), str(creator_id), category_type, now, now))
        return cursor.lastrowid


def get_ticket_by_channel(channel_id: int) -> sqlite3.Row | None:
    """Lấy thông tin ticket theo channel_id."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM tickets WHERE channel_id=?",
            (str(channel_id),)
        ).fetchone()


def update_last_active(channel_id: int) -> None:
    """Cập nhật thời gian hoạt động mới nhất của kênh ticket."""
    now = time.time()
    with _connect() as conn:
        conn.execute(
            "UPDATE tickets SET last_active_at=? WHERE channel_id=? AND status='open'",
            (now, str(channel_id))
        )


def claim_ticket(channel_id: int, claimer_id: int) -> bool:
    """Claim ticket bởi role HE."""
    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE tickets SET claimed_by=?
            WHERE channel_id=? AND status='open' AND claimed_by IS NULL
        """, (str(claimer_id), str(channel_id)))
        return cursor.rowcount > 0


def close_ticket(channel_id: int, transcript_path: str | None = None) -> None:
    """Đánh dấu ticket đã đóng và lưu đường dẫn file transcript."""
    now = time.time()
    with _connect() as conn:
        conn.execute("""
            UPDATE tickets 
            SET status='closed', closed_at=?, transcript_file=?
            WHERE channel_id=?
        """, (now, transcript_path, str(channel_id)))


def get_inactive_open_tickets(max_idle_seconds: int = 10800) -> list[sqlite3.Row]:
    """
    Lấy danh sách các ticket đang mở mà không có tin nhắn mới quá thời gian cho phép (mặc định 3 tiếng = 10800s).
    """
    threshold = time.time() - max_idle_seconds
    with _connect() as conn:
        return conn.execute("""
            SELECT * FROM tickets
            WHERE status='open' AND last_active_at < ?
        """, (threshold,)).fetchall()
