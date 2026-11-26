"""
arena_db.py — Quản lý cơ sở dữ liệu giải đấu eSport / Scrims cho HEe • Arena.
Hỗ trợ lưu thông tin giải, đội tuyển (team & thành viên), lịch thi đấu, nhánh đấu (bracket),
và các phòng voice tạm thời.
"""

import json
import os
import sqlite3
import time
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "arena.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Khởi tạo cấu trúc các bảng cho hệ thống giải đấu."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        TEXT NOT NULL,
                name            TEXT NOT NULL,
                format          TEXT NOT NULL, -- 'fast' (knockout mì ăn liền), 'groups' (vòng bảng -> chung kết)
                team_size       INTEGER DEFAULT 5,
                status          TEXT DEFAULT 'registering', -- 'registering', 'in_progress', 'completed', 'cancelled'
                category_id     TEXT DEFAULT NULL,
                created_by      TEXT NOT NULL,
                created_at      REAL NOT NULL,
                updated_at      REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS teams (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id   INTEGER NOT NULL,
                name            TEXT NOT NULL,
                captain_id      TEXT NOT NULL,
                members_json    TEXT NOT NULL, -- JSON array of string user IDs
                seed            INTEGER DEFAULT 0,
                group_name      TEXT DEFAULT NULL, -- 'A', 'B' nếu đấu vòng bảng
                points          INTEGER DEFAULT 0,
                wins            INTEGER DEFAULT 0,
                losses          INTEGER DEFAULT 0,
                created_at      REAL NOT NULL,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS matches (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id   INTEGER NOT NULL,
                round_name      TEXT NOT NULL, -- 'Tứ Kết', 'Bán Kết', 'Chung Kết', 'Vòng Bảng'
                match_number    INTEGER NOT NULL,
                team_a_id       INTEGER,
                team_b_id       INTEGER,
                winner_id       INTEGER DEFAULT NULL,
                status          TEXT DEFAULT 'pending', -- 'pending', 'ongoing', 'completed'
                team_a_voice_id TEXT DEFAULT NULL,
                team_b_voice_id TEXT DEFAULT NULL,
                scheduled_time  TEXT DEFAULT NULL,
                created_at      REAL NOT NULL,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                FOREIGN KEY (team_a_id) REFERENCES teams(id) ON DELETE SET NULL,
                FOREIGN KEY (team_b_id) REFERENCES teams(id) ON DELETE SET NULL,
                FOREIGN KEY (winner_id) REFERENCES teams(id) ON DELETE SET NULL
            );
        """)


# ─────────────────────────── TOURNAMENT ───────────────────────────

def create_tournament(guild_id: int, name: str, format_type: str, created_by: int, team_size: int = 5) -> int:
    now = time.time()
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO tournaments (guild_id, name, format, created_by, team_size, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(guild_id), name, format_type, str(created_by), team_size, now, now))
        return cursor.lastrowid


def get_active_tournament(guild_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("""
            SELECT * FROM tournaments
            WHERE guild_id = ? AND status IN ('registering', 'in_progress')
            ORDER BY id DESC LIMIT 1
        """, (str(guild_id),)).fetchone()


def get_tournament(tournament_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,)).fetchone()


def update_tournament_status(tournament_id: int, status: str, category_id: int | None = None) -> None:
    now = time.time()
    with _connect() as conn:
        if category_id is not None:
            conn.execute("""
                UPDATE tournaments
                SET status = ?, category_id = ?, updated_at = ?
                WHERE id = ?
            """, (status, str(category_id), now, tournament_id))
        else:
            conn.execute("""
                UPDATE tournaments
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, now, tournament_id))


# ─────────────────────────── TEAMS ───────────────────────────

def add_team(tournament_id: int, name: str, captain_id: int, members: list[int]) -> int:
    now = time.time()
    # Chuyển đổi members thành list string
    str_members = [str(m) for m in members]
    if str(captain_id) not in str_members:
        str_members.insert(0, str(captain_id))

    members_json = json.dumps(str_members)
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO teams (tournament_id, name, captain_id, members_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tournament_id, name, str(captain_id), members_json, now))
        return cursor.lastrowid


def get_teams(tournament_id: int) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("""
            SELECT * FROM teams WHERE tournament_id = ? ORDER BY id ASC
        """, (tournament_id,)).fetchall()


def get_team(team_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()


def update_team_group(team_id: int, group_name: str, seed: int) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE teams SET group_name = ?, seed = ? WHERE id = ?
        """, (group_name, seed, team_id))


def update_team_stats(team_id: int, won: bool) -> None:
    with _connect() as conn:
        if won:
            conn.execute("""
                UPDATE teams
                SET wins = wins + 1, points = points + 3
                WHERE id = ?
            """, (team_id,))
        else:
            conn.execute("""
                UPDATE teams
                SET losses = losses + 1
                WHERE id = ?
            """, (team_id,))


# ─────────────────────────── MATCHES ───────────────────────────

def create_match(tournament_id: int, round_name: str, match_num: int, team_a_id: int | None, team_b_id: int | None) -> int:
    now = time.time()
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO matches (tournament_id, round_name, match_number, team_a_id, team_b_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tournament_id, round_name, match_num, team_a_id, team_b_id, now))
        return cursor.lastrowid


def get_matches(tournament_id: int) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("""
            SELECT m.*,
                   ta.name as team_a_name, ta.captain_id as team_a_captain, ta.members_json as team_a_members,
                   tb.name as team_b_name, tb.captain_id as team_b_captain, tb.members_json as team_b_members,
                   tw.name as winner_name
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            WHERE m.tournament_id = ?
            ORDER BY m.id ASC
        """, (tournament_id,)).fetchall()


def get_match(match_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("""
            SELECT m.*,
                   ta.name as team_a_name, ta.captain_id as team_a_captain, ta.members_json as team_a_members,
                   tb.name as team_b_name, tb.captain_id as team_b_captain, tb.members_json as team_b_members,
                   tw.name as winner_name
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            WHERE m.id = ?
        """, (match_id,)).fetchone()


def set_match_ongoing(match_id: int, team_a_voice_id: int, team_b_voice_id: int) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE matches
            SET status = 'ongoing', team_a_voice_id = ?, team_b_voice_id = ?
            WHERE id = ?
        """, (str(team_a_voice_id), str(team_b_voice_id), match_id))


def set_match_winner(match_id: int, winner_id: int) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE matches
            SET status = 'completed', winner_id = ?
            WHERE id = ?
        """, (winner_id, match_id))


def clear_match_voices(match_id: int) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE matches
            SET team_a_voice_id = NULL, team_b_voice_id = NULL
            WHERE id = ?
        """, (match_id,))
