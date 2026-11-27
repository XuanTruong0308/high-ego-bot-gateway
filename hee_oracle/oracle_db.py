"""
oracle_db.py — Quản lý lưu trữ SQLite cho HEe • Oracle.
Lưu trữ các giáo án đội hình, chiến thuật thi đấu Road To VCS và nhật ký phân tích Scrims.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "oracle.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        # Bảng lưu trữ bộ khung đội hình của Team (Comp Presets)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_comps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                name TEXT NOT NULL,
                top TEXT NOT NULL,
                jungle TEXT NOT NULL,
                mid TEXT NOT NULL,
                adc TEXT NOT NULL,
                support TEXT NOT NULL,
                playstyle TEXT,
                notes TEXT,
                created_by TEXT,
                created_at REAL NOT NULL
            )
        """)

        # Bảng nhật ký phân tích trận Scrims thực tế (Post-Match Scrim Analysis)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrim_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                title TEXT NOT NULL,
                our_comp TEXT NOT NULL,
                enemy_comp TEXT NOT NULL,
                result TEXT NOT NULL, -- 'win' | 'loss'
                key_takeaway TEXT,
                recorded_by TEXT,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()


def save_comp(guild_id: int, name: str, top: str, jg: str, mid: str, adc: str, sup: str, playstyle: str = "", notes: str = "", created_by: int = 0) -> int:
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO saved_comps (guild_id, name, top, jungle, mid, adc, support, playstyle, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(guild_id), name, top, jg, mid, adc, sup, playstyle, notes, str(created_by), time.time()))
        conn.commit()
        return cur.lastrowid


def list_saved_comps(guild_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM saved_comps WHERE guild_id = ? ORDER BY id DESC", (str(guild_id),)).fetchall()
        return [dict(r) for r in rows]


def get_comp_by_id(comp_id: int, guild_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM saved_comps WHERE id = ? AND guild_id = ?", (comp_id, str(guild_id))).fetchone()
        return dict(row) if row else None


def delete_comp(comp_id: int, guild_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM saved_comps WHERE id = ? AND guild_id = ?", (comp_id, str(guild_id)))
        conn.commit()
        return cur.rowcount > 0


def log_scrim(guild_id: int, title: str, our_comp: str, enemy_comp: str, result: str, takeaway: str, recorded_by: int) -> int:
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO scrim_reports (guild_id, title, our_comp, enemy_comp, result, key_takeaway, recorded_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(guild_id), title, our_comp, enemy_comp, result, takeaway, str(recorded_by), time.time()))
        conn.commit()
        return cur.lastrowid


def list_scrim_reports(guild_id: int, limit: int = 5) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM scrim_reports WHERE guild_id = ? ORDER BY id DESC LIMIT ?", (str(guild_id), limit)).fetchall()
        return [dict(r) for r in rows]
