"""
db.py — SQLite wrapper cho HEe Chronicle (P6)
Lưu XP, stats, voice session của từng thành viên.
"""

import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rank.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Tạo bảng nếu chưa có."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS members (
                user_id       TEXT NOT NULL,
                guild_id      TEXT NOT NULL,
                xp            REAL    DEFAULT 0,
                total_messages   INTEGER DEFAULT 0,
                total_reactions  INTEGER DEFAULT 0,
                total_voice_min  INTEGER DEFAULT 0,
                last_msg_time    REAL    DEFAULT 0,
                voice_join_time  REAL    DEFAULT NULL,
                created_at    REAL,
                updated_at    REAL,
                PRIMARY KEY (user_id, guild_id)
            );
        """)


# ───────────────────────────── GET / UPSERT ──────────────────────────────

def get_member(user_id: int, guild_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM members WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        ).fetchone()


def upsert_member(user_id: int, guild_id: int) -> None:
    """Đảm bảo member tồn tại trong DB."""
    now = time.time()
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO members (user_id, guild_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (str(user_id), str(guild_id), now, now))


# ───────────────────────────── XP OPERATIONS ─────────────────────────────

def add_xp_message(user_id: int, guild_id: int, xp_gain: float, cooldown: int) -> bool:
    """
    Cộng XP tin nhắn. Trả về True nếu đã cộng (không trong cooldown).
    """
    now = time.time()
    upsert_member(user_id, guild_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT last_msg_time FROM members WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        ).fetchone()
        if row and (now - row["last_msg_time"]) < cooldown:
            return False
        conn.execute("""
            UPDATE members
            SET xp = xp + ?,
                total_messages = total_messages + 1,
                last_msg_time = ?,
                updated_at = ?
            WHERE user_id=? AND guild_id=?
        """, (xp_gain, now, now, str(user_id), str(guild_id)))
    return True


def add_xp_reaction(user_id: int, guild_id: int, xp_gain: float) -> None:
    """Cộng XP reaction."""
    now = time.time()
    upsert_member(user_id, guild_id)
    with _connect() as conn:
        conn.execute("""
            UPDATE members
            SET xp = xp + ?,
                total_reactions = total_reactions + 1,
                updated_at = ?
            WHERE user_id=? AND guild_id=?
        """, (xp_gain, now, str(user_id), str(guild_id)))


def set_voice_join(user_id: int, guild_id: int) -> None:
    """Ghi nhận thời điểm vào voice."""
    now = time.time()
    upsert_member(user_id, guild_id)
    with _connect() as conn:
        conn.execute("""
            UPDATE members SET voice_join_time=?, updated_at=?
            WHERE user_id=? AND guild_id=?
        """, (now, now, str(user_id), str(guild_id)))


def flush_voice_xp(user_id: int, guild_id: int, xp_per_min: float) -> int:
    """
    Tính XP voice từ lúc join đến giờ, cộng vào DB, xóa session.
    Trả về số phút đã tính.
    """
    now = time.time()
    upsert_member(user_id, guild_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT voice_join_time FROM members WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        ).fetchone()
        if not row or not row["voice_join_time"]:
            return 0
        minutes = int((now - row["voice_join_time"]) / 60)
        if minutes <= 0:
            return 0
        xp_gain = minutes * xp_per_min
        conn.execute("""
            UPDATE members
            SET xp = xp + ?,
                total_voice_min = total_voice_min + ?,
                voice_join_time = NULL,
                updated_at = ?
            WHERE user_id=? AND guild_id=?
        """, (xp_gain, minutes, now, str(user_id), str(guild_id)))
    return minutes


def add_voice_minute(user_id: int, guild_id: int, xp_gain: float) -> None:
    """Cộng 1 phút voice và XP tương ứng vào database."""
    now = time.time()
    upsert_member(user_id, guild_id)
    with _connect() as conn:
        conn.execute("""
            UPDATE members
            SET xp = xp + ?,
                total_voice_min = total_voice_min + 1,
                updated_at = ?
            WHERE user_id=? AND guild_id=?
        """, (xp_gain, now, str(user_id), str(guild_id)))


# ───────────────────────────── LEADERBOARD ───────────────────────────────

def get_leaderboard(guild_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("""
            SELECT user_id, xp, total_messages, total_reactions, total_voice_min
            FROM members WHERE guild_id=?
            ORDER BY xp DESC LIMIT ?
        """, (str(guild_id), limit)).fetchall()


def get_rank_position(user_id: int, guild_id: int) -> int:
    """Trả về vị trí xếp hạng (1-indexed) của user."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT user_id FROM members WHERE guild_id=? ORDER BY xp DESC",
            (str(guild_id),)
        ).fetchall()
    for i, row in enumerate(rows):
        if row["user_id"] == str(user_id):
            return i + 1
    return -1
