from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("ATTACK_SCANNER_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("ATTACK_SCANNER_DB", DATA_DIR / "attacks.sqlite3"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    current_alliance_tag TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, normalized_name)
);

CREATE TABLE IF NOT EXISTS attacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER,
    attack_type TEXT NOT NULL,
    attacker_player_id INTEGER NOT NULL,
    attacker_name TEXT NOT NULL,
    attacker_alliance_tag TEXT,
    defender_player_id INTEGER,
    defender_name TEXT,
    defender_alliance_tag TEXT,
    occurred_at TEXT,
    occurred_at_text TEXT,
    source_filename TEXT,
    source_kind TEXT NOT NULL DEFAULT 'upload',
    notes TEXT,
    parser_confidence REAL,
    raw_parse_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(attacker_player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY(defender_player_id) REFERENCES players(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_players_server_name ON players(server_id, normalized_name);
CREATE INDEX IF NOT EXISTS idx_attacks_server_time ON attacks(server_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_attacks_attacker ON attacks(attacker_player_id);
CREATE INDEX IF NOT EXISTS idx_attacks_defender ON attacks(defender_player_id);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_SQL)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def get_or_create_player(conn: sqlite3.Connection, name: str, server_id: int | None = None, alliance_tag: str | None = None) -> sqlite3.Row:
    normalized = normalize_name(name)
    row = conn.execute(
        "SELECT * FROM players WHERE server_id IS ? AND normalized_name = ?",
        (server_id, normalized),
    ).fetchone()
    if row:
        if alliance_tag and alliance_tag != row["current_alliance_tag"]:
            conn.execute("UPDATE players SET current_alliance_tag = ? WHERE id = ?", (alliance_tag, row["id"]))
            row = conn.execute("SELECT * FROM players WHERE id = ?", (row["id"],)).fetchone()
        return row
    cursor = conn.execute(
        "INSERT INTO players (server_id, name, normalized_name, current_alliance_tag) VALUES (?, ?, ?, ?)",
        (server_id, name.strip(), normalized, alliance_tag),
    )
    return conn.execute("SELECT * FROM players WHERE id = ?", (cursor.lastrowid,)).fetchone()


def add_attack(
    conn: sqlite3.Connection,
    *,
    attack_type: str,
    attacker_name: str,
    attacker_alliance_tag: str | None,
    defender_name: str | None,
    defender_alliance_tag: str | None,
    server_id: int | None,
    occurred_at: str | None,
    occurred_at_text: str | None,
    source_filename: str | None,
    source_kind: str,
    notes: str | None,
    parser_confidence: float | None,
    raw_parse_json: dict | list | None,
) -> int:
    attacker = get_or_create_player(conn, attacker_name, server_id=server_id, alliance_tag=attacker_alliance_tag)
    defender_id = None
    defender_clean = defender_name.strip() if defender_name else None
    if defender_clean:
        defender = get_or_create_player(conn, defender_clean, server_id=server_id, alliance_tag=defender_alliance_tag)
        defender_id = defender["id"]

    cursor = conn.execute(
        """
        INSERT INTO attacks (
            server_id, attack_type, attacker_player_id, attacker_name, attacker_alliance_tag,
            defender_player_id, defender_name, defender_alliance_tag,
            occurred_at, occurred_at_text, source_filename, source_kind,
            notes, parser_confidence, raw_parse_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            server_id,
            attack_type,
            attacker["id"],
            attacker_name.strip(),
            attacker_alliance_tag,
            defender_id,
            defender_clean,
            defender_alliance_tag,
            occurred_at,
            occurred_at_text,
            source_filename,
            source_kind,
            notes,
            parser_confidence,
            json.dumps(raw_parse_json) if raw_parse_json is not None else None,
        ),
    )
    return int(cursor.lastrowid)


def delete_attack(conn: sqlite3.Connection, attack_id: int) -> None:
    conn.execute("DELETE FROM attacks WHERE id = ?", (attack_id,))


def recent_attacks(conn: sqlite3.Connection, limit: int = 20, server_id: int | None = None) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM attacks
        WHERE (? IS NULL OR server_id = ?)
        ORDER BY COALESCE(occurred_at, created_at) DESC, id DESC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()


def search_players(conn: sqlite3.Connection, query: str = "", server_id: int | None = None) -> list[sqlite3.Row]:
    query = query.strip()
    if query:
        return conn.execute(
            """
            SELECT p.*, (SELECT COUNT(*) FROM attacks a WHERE a.attacker_player_id = p.id OR a.defender_player_id = p.id) AS total_events
            FROM players p
            WHERE p.name LIKE ? AND (? IS NULL OR p.server_id = ?)
            ORDER BY total_events DESC, p.name ASC
            LIMIT 100
            """,
            (f"%{query}%", server_id, server_id),
        ).fetchall()
    return conn.execute(
        """
        SELECT p.*, (SELECT COUNT(*) FROM attacks a WHERE a.attacker_player_id = p.id OR a.defender_player_id = p.id) AS total_events
        FROM players p
        WHERE (? IS NULL OR p.server_id = ?)
        ORDER BY total_events DESC, p.name ASC
        LIMIT 100
        """,
        (server_id, server_id),
    ).fetchall()


def find_player_by_name(conn: sqlite3.Connection, name: str, server_id: int | None = None) -> sqlite3.Row | None:
    normalized = normalize_name(name)
    row = conn.execute(
        """
        SELECT * FROM players
        WHERE normalized_name = ? AND (? IS NULL OR server_id = ?)
        ORDER BY CASE WHEN server_id IS ? THEN 0 ELSE 1 END, id ASC
        LIMIT 1
        """,
        (normalized, server_id, server_id, server_id),
    ).fetchone()
    if row:
        return row
    return conn.execute(
        "SELECT * FROM players WHERE name LIKE ? AND (? IS NULL OR server_id = ?) ORDER BY id ASC LIMIT 1",
        (f"%{name.strip()}%", server_id, server_id),
    ).fetchone()


def get_player(conn: sqlite3.Connection, player_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()


def player_history(conn: sqlite3.Connection, player_id: int, limit: int | None = None) -> list[sqlite3.Row]:
    sql = """
        SELECT * FROM attacks
        WHERE attacker_player_id = ? OR defender_player_id = ?
        ORDER BY COALESCE(occurred_at, created_at) DESC, id DESC
    """
    params: list[object] = [player_id, player_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def top_attackers(conn: sqlite3.Connection, server_id: int | None = None, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT attacker_player_id, attacker_name, attacker_alliance_tag, server_id,
               COUNT(*) AS attack_count,
               SUM(CASE WHEN attack_type = 'covert_ops' THEN 1 ELSE 0 END) AS covert_ops_count,
               SUM(CASE WHEN attack_type = 'battle' THEN 1 ELSE 0 END) AS battle_count
        FROM attacks
        WHERE (? IS NULL OR server_id = ?)
        GROUP BY attacker_player_id, attacker_name, attacker_alliance_tag, server_id
        ORDER BY attack_count DESC, attacker_name ASC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()


def top_alliances(conn: sqlite3.Connection, server_id: int | None = None, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT attacker_alliance_tag,
               COUNT(*) AS attack_count,
               COUNT(DISTINCT attacker_player_id) AS unique_attackers
        FROM attacks
        WHERE attacker_alliance_tag IS NOT NULL AND attacker_alliance_tag != ''
          AND (? IS NULL OR server_id = ?)
        GROUP BY attacker_alliance_tag
        ORDER BY unique_attackers DESC, attack_count DESC, attacker_alliance_tag ASC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()
