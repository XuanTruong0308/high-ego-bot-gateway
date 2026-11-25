import os
import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Tuple

DB_PATH = Path(__file__).parent / "data" / "giveaway.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                channel_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                prize TEXT NOT NULL,
                winner_count INTEGER DEFAULT 1,
                end_time REAL NOT NULL,
                host_id TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                min_level INTEGER DEFAULT 0,
                min_account_age_days INTEGER DEFAULT 7,
                min_server_stay_hours INTEGER DEFAULT 24,
                required_role_id TEXT DEFAULT NULL,
                is_vault_points INTEGER DEFAULT 0,
                vault_points_amount REAL DEFAULT 0,
                winners TEXT DEFAULT NULL,
                created_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                giveaway_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (giveaway_id, user_id),
                FOREIGN KEY (giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

def create_giveaway(
    message_id: int,
    channel_id: int,
    guild_id: int,
    prize: str,
    winner_count: int,
    end_time: float,
    host_id: int,
    min_level: int = 0,
    min_account_age_days: int = 90,
    min_server_stay_hours: int = 0,
    required_role_id: Optional[int] = None,
    is_vault_points: int = 0,
    vault_points_amount: float = 0
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO giveaways (
                message_id, channel_id, guild_id, prize, winner_count,
                end_time, host_id, status, min_level, min_account_age_days,
                min_server_stay_hours, required_role_id, is_vault_points,
                vault_points_amount, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(message_id), str(channel_id), str(guild_id), prize, winner_count,
            end_time, str(host_id), min_level, min_account_age_days,
            min_server_stay_hours, str(required_role_id) if required_role_id else None,
            is_vault_points, vault_points_amount, time.time()
        ))
        conn.commit()
        return cursor.lastrowid

def get_giveaway_by_message(message_id: int) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM giveaways WHERE message_id = ?", (str(message_id),))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_active_giveaways() -> List[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM giveaways WHERE status = 'running'")
        return [dict(r) for r in cursor.fetchall()]

def toggle_entry(giveaway_id: int, user_id: int) -> Tuple[bool, int]:
    """Bấm tham gia hoặc hủy tham gia. Trả về (is_joined: bool, total_entries: int)"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?", (giveaway_id, str(user_id)))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute("DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?", (giveaway_id, str(user_id)))
            is_joined = False
        else:
            cursor.execute("INSERT INTO giveaway_entries (giveaway_id, user_id, created_at) VALUES (?, ?, ?)",
                           (giveaway_id, str(user_id), time.time()))
            is_joined = True

        cursor.execute("SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))
        count = cursor.fetchone()[0]
        conn.commit()
        return is_joined, count

def get_entry_count(giveaway_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))
        return cursor.fetchone()[0]

def get_entries(giveaway_id: int) -> List[int]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))
        return [int(r[0]) for r in cursor.fetchall()]

def end_giveaway(giveaway_id: int, winner_ids: List[int]):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        winners_str = ",".join(str(w) for w in winner_ids)
        cursor.execute("UPDATE giveaways SET status = 'ended', winners = ? WHERE id = ?", (winners_str, giveaway_id))
        conn.commit()
