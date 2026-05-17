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
    source_image_hash TEXT,
    source_kind TEXT NOT NULL DEFAULT 'upload',
    notes TEXT,
    parser_confidence REAL,
    raw_parse_json TEXT,
    deleted_at TEXT,
    delete_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(attacker_player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY(defender_player_id) REFERENCES players(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS image_submissions (
    image_hash TEXT PRIMARY KEY,
    source_filename TEXT,
    source_kind TEXT NOT NULL,
    first_attack_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS managed_alliances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    alliance_tag TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, alliance_tag)
);

CREATE TABLE IF NOT EXISTS discord_user_preferences (
    user_id TEXT PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'en-US',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_players_server_name ON players(server_id, normalized_name);
CREATE INDEX IF NOT EXISTS idx_attacks_server_time ON attacks(server_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_attacks_attacker ON attacks(attacker_player_id);
CREATE INDEX IF NOT EXISTS idx_attacks_defender ON attacks(defender_player_id);
CREATE INDEX IF NOT EXISTS idx_attacks_attacker_alliance ON attacks(attacker_alliance_tag);
CREATE INDEX IF NOT EXISTS idx_attacks_defender_alliance ON attacks(defender_alliance_tag);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_SQL)
        ensure_column(conn, "attacks", "source_image_hash", "TEXT")
        ensure_column(conn, "attacks", "deleted_at", "TEXT")
        ensure_column(conn, "attacks", "delete_reason", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attacks_source_image_hash ON attacks(source_image_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attacks_deleted_at ON attacks(deleted_at)")
        normalize_existing_alliance_tags(conn)


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def normalize_ocr_player_name(name: str) -> str:
    name = name.strip()
    if len(name) >= 4 and name.startswith("J") and name[1].isupper() and name[2].islower():
        return name[1:]
    return name


def normalize_alliance_tag(tag: str | None) -> str | None:
    if tag is None:
        return None
    tag = tag.strip()
    if tag.startswith("[") and tag.endswith("]"):
        tag = tag[1:-1].strip()
    return tag or None


def normalize_existing_alliance_tags(conn: sqlite3.Connection) -> None:
    for table, columns in {
        "attacks": ("attacker_alliance_tag", "defender_alliance_tag"),
        "players": ("current_alliance_tag",),
    }.items():
        rows = conn.execute(f"SELECT id, {', '.join(columns)} FROM {table}").fetchall()
        for row in rows:
            updates = {column: normalize_alliance_tag(row[column]) for column in columns}
            if any(updates[column] != row[column] for column in columns):
                assignments = ", ".join(f"{column} = ?" for column in columns)
                conn.execute(
                    f"UPDATE {table} SET {assignments} WHERE id = ?",
                    (*[updates[column] for column in columns], row["id"]),
                )


def get_discord_user_language(conn: sqlite3.Connection, user_id: int | str) -> str | None:
    row = conn.execute(
        "SELECT language FROM discord_user_preferences WHERE user_id = ?",
        (str(user_id),),
    ).fetchone()
    return row["language"] if row else None


def set_discord_user_language(conn: sqlite3.Connection, user_id: int | str, language: str) -> None:
    conn.execute(
        """
        INSERT INTO discord_user_preferences (user_id, language, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            language = excluded.language,
            updated_at = CURRENT_TIMESTAMP
        """,
        (str(user_id), language),
    )


def get_or_create_player(conn: sqlite3.Connection, name: str, server_id: int | None = None, alliance_tag: str | None = None) -> sqlite3.Row:
    alliance_tag = normalize_alliance_tag(alliance_tag)
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
    source_image_hash: str | None = None,
) -> int:
    attacker_name = normalize_ocr_player_name(attacker_name)
    if defender_name:
        defender_name = normalize_ocr_player_name(defender_name)
    attacker_alliance_tag = normalize_alliance_tag(attacker_alliance_tag)
    defender_alliance_tag = normalize_alliance_tag(defender_alliance_tag)
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
            occurred_at, occurred_at_text, source_filename, source_image_hash, source_kind,
            notes, parser_confidence, raw_parse_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            source_image_hash,
            source_kind,
            notes,
            parser_confidence,
            json.dumps(raw_parse_json) if raw_parse_json is not None else None,
        ),
    )
    return int(cursor.lastrowid)


def get_image_submission(conn: sqlite3.Connection, image_hash: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM image_submissions WHERE image_hash = ?",
        (image_hash,),
    ).fetchone()


def add_image_submission(
    conn: sqlite3.Connection,
    *,
    image_hash: str,
    source_filename: str | None,
    source_kind: str,
    first_attack_id: int | None,
) -> None:
    conn.execute(
        """
        INSERT INTO image_submissions (image_hash, source_filename, source_kind, first_attack_id)
        VALUES (?, ?, ?, ?)
        """,
        (image_hash, source_filename, source_kind, first_attack_id),
    )


def managed_alliance_tags(conn: sqlite3.Connection, server_id: int = 78) -> list[str]:
    return [
        row["alliance_tag"]
        for row in conn.execute(
            "SELECT alliance_tag FROM managed_alliances WHERE server_id = ? ORDER BY alliance_tag ASC",
            (server_id,),
        ).fetchall()
    ]


def is_managed_alliance(conn: sqlite3.Connection, alliance_tag: str | None, server_id: int = 78) -> bool:
    alliance_tag = normalize_alliance_tag(alliance_tag)
    if not alliance_tag:
        return False
    return conn.execute(
        "SELECT 1 FROM managed_alliances WHERE server_id = ? AND alliance_tag = ? LIMIT 1",
        (server_id, alliance_tag),
    ).fetchone() is not None


def add_managed_alliance(conn: sqlite3.Connection, alliance_tag: str, server_id: int = 78) -> None:
    alliance_tag = normalize_alliance_tag(alliance_tag)
    if not alliance_tag:
        return
    conn.execute(
        "INSERT OR IGNORE INTO managed_alliances (server_id, alliance_tag) VALUES (?, ?)",
        (server_id, alliance_tag),
    )


def remove_managed_alliance(conn: sqlite3.Connection, alliance_tag: str, server_id: int = 78) -> None:
    alliance_tag = normalize_alliance_tag(alliance_tag)
    if not alliance_tag:
        return
    conn.execute(
        "DELETE FROM managed_alliances WHERE server_id = ? AND alliance_tag = ?",
        (server_id, alliance_tag),
    )


def delete_attack(conn: sqlite3.Connection, attack_id: int, delete_reason: str | None = None) -> None:
    row = get_attack(conn, attack_id)
    if not row:
        return
    conn.execute(
        "UPDATE attacks SET deleted_at = CURRENT_TIMESTAMP, delete_reason = ? WHERE id = ?",
        (delete_reason, attack_id),
    )
    if row["source_image_hash"]:
        remaining = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM attacks
            WHERE source_image_hash = ?
              AND id != ?
              AND deleted_at IS NULL
            """,
            (row["source_image_hash"], attack_id),
        ).fetchone()["total"]
        if remaining == 0:
            conn.execute("DELETE FROM image_submissions WHERE image_hash = ?", (row["source_image_hash"],))


def soft_delete_expired_attacks(conn: sqlite3.Connection, days: int = 30) -> int:
    rows = conn.execute(
        """
        SELECT id
        FROM attacks
        WHERE deleted_at IS NULL
          AND datetime(COALESCE(occurred_at, created_at)) < datetime('now', ?)
        """,
        (f"-{days} days",),
    ).fetchall()
    for row in rows:
        delete_attack(conn, row["id"], delete_reason=f"Automatic {days}-day retention")
    return len(rows)


def j_prefix_attacker_candidates(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT server_id,
               attacker_alliance_tag,
               attacker_name,
               COUNT(*) AS attack_count,
               MIN(id) AS first_attack_id,
               MAX(id) AS last_attack_id
        FROM attacks
        WHERE attacker_name GLOB 'J[A-Z]*'
        GROUP BY server_id, attacker_alliance_tag, attacker_name
        ORDER BY attack_count DESC, attacker_name ASC
        """
    ).fetchall()
    candidates: list[dict] = []
    for row in rows:
        proposed = normalize_ocr_player_name(row["attacker_name"])
        if proposed == row["attacker_name"]:
            continue
        candidates.append(
            {
                "server_id": row["server_id"],
                "attacker_alliance_tag": row["attacker_alliance_tag"],
                "old_name": row["attacker_name"],
                "new_name": proposed,
                "attack_count": row["attack_count"],
                "first_attack_id": row["first_attack_id"],
                "last_attack_id": row["last_attack_id"],
            }
        )
    return candidates


def repair_j_prefixed_attackers(conn: sqlite3.Connection, apply: bool = False) -> list[dict]:
    candidates = j_prefix_attacker_candidates(conn)
    if not apply:
        return candidates
    for candidate in candidates:
        player = get_or_create_player(
            conn,
            candidate["new_name"],
            server_id=candidate["server_id"],
            alliance_tag=candidate["attacker_alliance_tag"],
        )
        conn.execute(
            """
            UPDATE attacks
            SET attacker_name = ?,
                attacker_player_id = ?
            WHERE attacker_name = ?
              AND server_id IS ?
              AND attacker_alliance_tag IS ?
            """,
            (
                candidate["new_name"],
                player["id"],
                candidate["old_name"],
                candidate["server_id"],
                candidate["attacker_alliance_tag"],
            ),
        )
    stale_players = conn.execute(
        """
        SELECT p.id
        FROM players p
        WHERE p.name GLOB 'J[A-Z]*'
          AND NOT EXISTS (SELECT 1 FROM attacks a WHERE a.attacker_player_id = p.id OR a.defender_player_id = p.id)
        """
    ).fetchall()
    for player in stale_players:
        conn.execute("DELETE FROM players WHERE id = ?", (player["id"],))
    return candidates


def duplicate_player_groups(conn: sqlite3.Connection) -> list[dict]:
    groups = conn.execute(
        """
        SELECT server_id,
               normalized_name,
               COUNT(*) AS player_count,
               GROUP_CONCAT(id) AS player_ids,
               MIN(id) AS canonical_id
        FROM players
        GROUP BY server_id, normalized_name
        HAVING COUNT(*) > 1
        ORDER BY player_count DESC, normalized_name ASC
        """
    ).fetchall()
    results: list[dict] = []
    for group in groups:
        players = conn.execute(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM attacks a WHERE a.attacker_player_id = p.id) AS attacker_refs,
                   (SELECT COUNT(*) FROM attacks a WHERE a.defender_player_id = p.id) AS defender_refs
            FROM players p
            WHERE p.server_id IS ? AND p.normalized_name = ?
            ORDER BY (attacker_refs + defender_refs) DESC, p.id ASC
            """,
            (group["server_id"], group["normalized_name"]),
        ).fetchall()
        canonical = players[0]
        duplicate_ids = [row["id"] for row in players if row["id"] != canonical["id"]]
        results.append(
            {
                "server_id": group["server_id"],
                "normalized_name": group["normalized_name"],
                "canonical_id": canonical["id"],
                "canonical_name": canonical["name"],
                "duplicate_ids": duplicate_ids,
                "player_count": group["player_count"],
                "attack_refs": sum(row["attacker_refs"] + row["defender_refs"] for row in players),
            }
        )
    return results


def merge_duplicate_players(conn: sqlite3.Connection, apply: bool = False) -> list[dict]:
    groups = duplicate_player_groups(conn)
    if not apply:
        return groups

    for group in groups:
        duplicate_ids = group["duplicate_ids"]
        if not duplicate_ids:
            continue
        placeholders = ", ".join("?" for _ in duplicate_ids)
        canonical_id = group["canonical_id"]
        conn.execute(
            f"UPDATE attacks SET attacker_player_id = ? WHERE attacker_player_id IN ({placeholders})",
            (canonical_id, *duplicate_ids),
        )
        conn.execute(
            f"UPDATE attacks SET defender_player_id = ? WHERE defender_player_id IN ({placeholders})",
            (canonical_id, *duplicate_ids),
        )
        canonical = conn.execute("SELECT * FROM players WHERE id = ?", (canonical_id,)).fetchone()
        if canonical and not canonical["current_alliance_tag"]:
            alliance = conn.execute(
                f"""
                SELECT current_alliance_tag
                FROM players
                WHERE id IN ({placeholders})
                  AND current_alliance_tag IS NOT NULL
                  AND current_alliance_tag != ''
                ORDER BY id ASC
                LIMIT 1
                """,
                duplicate_ids,
            ).fetchone()
            if alliance:
                conn.execute(
                    "UPDATE players SET current_alliance_tag = ? WHERE id = ?",
                    (alliance["current_alliance_tag"], canonical_id),
                )
        conn.execute(f"DELETE FROM players WHERE id IN ({placeholders})", duplicate_ids)

    return groups


def recent_attacks(conn: sqlite3.Connection, limit: int = 20, server_id: int | None = None) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM attacks
        WHERE deleted_at IS NULL
          AND (? IS NULL OR server_id = ?)
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
            SELECT p.*, (SELECT COUNT(*) FROM attacks a WHERE a.deleted_at IS NULL AND (a.attacker_player_id = p.id OR a.defender_player_id = p.id)) AS total_events
            FROM players p
            WHERE p.name LIKE ? AND (? IS NULL OR p.server_id = ?)
            ORDER BY total_events DESC, p.name ASC
            LIMIT 100
            """,
            (f"%{query}%", server_id, server_id),
        ).fetchall()
    return conn.execute(
        """
        SELECT p.*, (SELECT COUNT(*) FROM attacks a WHERE a.deleted_at IS NULL AND (a.attacker_player_id = p.id OR a.defender_player_id = p.id)) AS total_events
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


def get_attack(conn: sqlite3.Connection, attack_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM attacks WHERE id = ?", (attack_id,)).fetchone()


def player_history(conn: sqlite3.Connection, player_id: int, limit: int | None = None) -> list[sqlite3.Row]:
    sql = """
        SELECT * FROM attacks
        WHERE deleted_at IS NULL
          AND (attacker_player_id = ? OR defender_player_id = ?)
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
        WHERE deleted_at IS NULL
          AND (? IS NULL OR server_id = ?)
        GROUP BY attacker_player_id, attacker_name, attacker_alliance_tag, server_id
        ORDER BY attack_count DESC, attacker_name ASC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()


def attacking_alliance_options(conn: sqlite3.Connection, server_id: int | None = None) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT attacker_alliance_tag AS alliance_tag,
               COUNT(*) AS attack_count
        FROM attacks
        WHERE deleted_at IS NULL
          AND attacker_alliance_tag IS NOT NULL AND attacker_alliance_tag != ''
          AND (? IS NULL OR server_id = ?)
        GROUP BY attacker_alliance_tag
        ORDER BY attack_count DESC, attacker_alliance_tag ASC
        """,
        (server_id, server_id),
    ).fetchall()


def attacking_player_options(
    conn: sqlite3.Connection,
    server_id: int | None = None,
    attacker_alliance_tag: str | None = None,
) -> list[sqlite3.Row]:
    attacker_alliance_tag = normalize_alliance_tag(attacker_alliance_tag)
    return conn.execute(
        """
        SELECT NULL AS player_id,
               attacker_name AS player_name,
               attacker_name AS filter_value,
               MIN(attacker_alliance_tag) AS attacker_alliance_tag,
               MIN(server_id) AS server_id,
               COUNT(*) AS attack_count
        FROM attacks
        WHERE deleted_at IS NULL
          AND attacker_name IS NOT NULL AND attacker_name != ''
          AND (? IS NULL OR server_id = ?)
          AND (? IS NULL OR attacker_alliance_tag = ?)
        GROUP BY attacker_name
        ORDER BY attack_count DESC, attacker_name ASC
        LIMIT 200
        """,
        (server_id, server_id, attacker_alliance_tag, attacker_alliance_tag),
    ).fetchall()


def attacking_player_options_from_attacks(
    conn: sqlite3.Connection,
    attacker_alliance_tag: str | None = None,
) -> list[sqlite3.Row]:
    attacker_alliance_tag = normalize_alliance_tag(attacker_alliance_tag)
    return conn.execute(
        """
        SELECT NULL AS player_id,
               attacker_name AS player_name,
               attacker_name AS filter_value,
               MIN(attacker_alliance_tag) AS attacker_alliance_tag,
               COUNT(*) AS attack_count
        FROM attacks
        WHERE deleted_at IS NULL
          AND attacker_name IS NOT NULL AND attacker_name != ''
          AND (? IS NULL OR attacker_alliance_tag = ?)
        GROUP BY attacker_name
        ORDER BY attack_count DESC, attacker_name ASC
        LIMIT 500
        """,
        (attacker_alliance_tag, attacker_alliance_tag),
    ).fetchall()


def attack_type_timeline(
    conn: sqlite3.Connection,
    server_id: int | None = None,
    attacker_alliance_tag: str | None = None,
    attacker_player_id: int | None = None,
    attacker_name: str | None = None,
) -> list[sqlite3.Row]:
    attacker_alliance_tag = normalize_alliance_tag(attacker_alliance_tag)
    attacker_name = attacker_name.strip() if attacker_name else None
    return conn.execute(
        """
        SELECT date(COALESCE(occurred_at, created_at)) AS attack_day,
               attack_type,
               COUNT(*) AS attack_count
        FROM attacks
        WHERE deleted_at IS NULL
          AND (? IS NULL OR server_id = ?)
          AND (? IS NULL OR attacker_alliance_tag = ?)
          AND (? IS NULL OR attacker_player_id = ?)
          AND (? IS NULL OR attacker_name = ?)
        GROUP BY date(COALESCE(occurred_at, created_at)), attack_type
        ORDER BY date(COALESCE(occurred_at, created_at)) ASC, attack_type ASC
        """,
        (
            server_id,
            server_id,
            attacker_alliance_tag,
            attacker_alliance_tag,
            attacker_player_id,
            attacker_player_id,
            attacker_name,
            attacker_name,
        ),
    ).fetchall()


def top_alliances(conn: sqlite3.Connection, server_id: int | None = None, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT attacker_alliance_tag,
               COUNT(*) AS attack_count,
               COUNT(DISTINCT attacker_player_id) AS unique_attackers
        FROM attacks
        WHERE deleted_at IS NULL
          AND attacker_alliance_tag IS NOT NULL AND attacker_alliance_tag != ''
          AND (? IS NULL OR server_id = ?)
        GROUP BY attacker_alliance_tag
        ORDER BY unique_attackers DESC, attack_count DESC, attacker_alliance_tag ASC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()


def top_attacked_alliances(conn: sqlite3.Connection, server_id: int | None = None, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT defender_alliance_tag,
               COUNT(*) AS attack_count,
               COUNT(DISTINCT defender_player_id) AS unique_defenders,
               COUNT(DISTINCT attacker_player_id) AS unique_attackers,
               COUNT(DISTINCT attacker_alliance_tag) AS attacking_alliances
        FROM attacks
        WHERE deleted_at IS NULL
          AND defender_alliance_tag IS NOT NULL AND defender_alliance_tag != ''
          AND (? IS NULL OR server_id = ?)
        GROUP BY defender_alliance_tag
        ORDER BY attack_count DESC, unique_defenders DESC, defender_alliance_tag ASC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()


def alliance_overview(conn: sqlite3.Connection, server_id: int | None = None, limit: int = 100) -> list[sqlite3.Row]:
    return conn.execute(
        """
        WITH alliance_tags AS (
            SELECT attacker_alliance_tag AS tag
            FROM attacks
            WHERE deleted_at IS NULL
              AND attacker_alliance_tag IS NOT NULL AND attacker_alliance_tag != ''
            UNION
            SELECT defender_alliance_tag AS tag
            FROM attacks
            WHERE deleted_at IS NULL
              AND defender_alliance_tag IS NOT NULL AND defender_alliance_tag != ''
        )
        SELECT tag,
               (SELECT COUNT(*) FROM attacks a WHERE a.deleted_at IS NULL AND a.attacker_alliance_tag = tag AND (? IS NULL OR a.server_id = ?)) AS attacks_made,
               (SELECT COUNT(*) FROM attacks a WHERE a.deleted_at IS NULL AND a.defender_alliance_tag = tag AND (? IS NULL OR a.server_id = ?)) AS attacks_received,
               (SELECT COUNT(DISTINCT attacker_player_id) FROM attacks a WHERE a.deleted_at IS NULL AND a.attacker_alliance_tag = tag AND (? IS NULL OR a.server_id = ?)) AS attacking_members,
               (SELECT COUNT(DISTINCT defender_player_id) FROM attacks a WHERE a.deleted_at IS NULL AND a.defender_alliance_tag = tag AND (? IS NULL OR a.server_id = ?)) AS attacked_members
        FROM alliance_tags
        WHERE attacks_made > 0 OR attacks_received > 0
        ORDER BY (attacks_made + attacks_received) DESC, attacks_received DESC, tag ASC
        LIMIT ?
        """,
        (server_id, server_id, server_id, server_id, server_id, server_id, server_id, server_id, limit),
    ).fetchall()


def alliance_matchups(conn: sqlite3.Connection, server_id: int | None = None, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT attacker_alliance_tag,
               defender_alliance_tag,
               COUNT(*) AS attack_count,
               COUNT(DISTINCT attacker_player_id) AS unique_attackers,
               COUNT(DISTINCT defender_player_id) AS unique_defenders
        FROM attacks
        WHERE deleted_at IS NULL
          AND attacker_alliance_tag IS NOT NULL AND attacker_alliance_tag != ''
          AND defender_alliance_tag IS NOT NULL AND defender_alliance_tag != ''
          AND attacker_alliance_tag != defender_alliance_tag
          AND (? IS NULL OR server_id = ?)
        GROUP BY attacker_alliance_tag, defender_alliance_tag
        ORDER BY attack_count DESC, unique_attackers DESC, attacker_alliance_tag ASC, defender_alliance_tag ASC
        LIMIT ?
        """,
        (server_id, server_id, limit),
    ).fetchall()


def alliance_members(conn: sqlite3.Connection, alliance_tag: str, server_id: int | None = None, limit: int = 100) -> list[sqlite3.Row]:
    alliance_tag = normalize_alliance_tag(alliance_tag) or ""
    return conn.execute(
        """
        WITH alliance_players AS (
            SELECT id AS player_id
            FROM players
            WHERE current_alliance_tag = ? AND (? IS NULL OR server_id = ?)
            UNION
            SELECT attacker_player_id AS player_id
            FROM attacks
            WHERE deleted_at IS NULL AND attacker_alliance_tag = ? AND (? IS NULL OR server_id = ?)
            UNION
            SELECT defender_player_id AS player_id
            FROM attacks
            WHERE deleted_at IS NULL AND defender_alliance_tag = ? AND defender_player_id IS NOT NULL AND (? IS NULL OR server_id = ?)
        )
        SELECT p.id,
               p.name,
               p.server_id,
               p.current_alliance_tag,
               (SELECT COUNT(*) FROM attacks a WHERE a.deleted_at IS NULL AND a.attacker_player_id = p.id AND a.attacker_alliance_tag = ? AND (? IS NULL OR a.server_id = ?)) AS attacks_made,
               (SELECT COUNT(*) FROM attacks a WHERE a.deleted_at IS NULL AND a.defender_player_id = p.id AND a.defender_alliance_tag = ? AND (? IS NULL OR a.server_id = ?)) AS attacks_received
        FROM alliance_players ap
        JOIN players p ON p.id = ap.player_id
        ORDER BY (attacks_made + attacks_received) DESC, attacks_made DESC, attacks_received DESC, p.name ASC
        LIMIT ?
        """,
        (
            alliance_tag, server_id, server_id,
            alliance_tag, server_id, server_id,
            alliance_tag, server_id, server_id,
            alliance_tag, server_id, server_id,
            alliance_tag, server_id, server_id,
            limit,
        ),
    ).fetchall()


def alliance_opponents(conn: sqlite3.Connection, alliance_tag: str, direction: str, server_id: int | None = None, limit: int = 20) -> list[sqlite3.Row]:
    alliance_tag = normalize_alliance_tag(alliance_tag) or ""
    if direction == "incoming":
        own_column = "defender_alliance_tag"
        opponent_column = "attacker_alliance_tag"
        own_player_column = "defender_player_id"
        opponent_player_column = "attacker_player_id"
    else:
        own_column = "attacker_alliance_tag"
        opponent_column = "defender_alliance_tag"
        own_player_column = "attacker_player_id"
        opponent_player_column = "defender_player_id"

    return conn.execute(
        f"""
        SELECT {opponent_column} AS opponent_alliance_tag,
               COUNT(*) AS attack_count,
               COUNT(DISTINCT {own_player_column}) AS own_members,
               COUNT(DISTINCT {opponent_player_column}) AS opponent_members
        FROM attacks
        WHERE deleted_at IS NULL
          AND {own_column} = ?
          AND {opponent_column} IS NOT NULL AND {opponent_column} != ''
          AND {opponent_column} != ?
          AND (? IS NULL OR server_id = ?)
        GROUP BY {opponent_column}
        ORDER BY attack_count DESC, own_members DESC, opponent_alliance_tag ASC
        LIMIT ?
        """,
        (alliance_tag, alliance_tag, server_id, server_id, limit),
    ).fetchall()


def recent_attacks_for_alliance(conn: sqlite3.Connection, alliance_tag: str, server_id: int | None = None, limit: int = 50) -> list[sqlite3.Row]:
    alliance_tag = normalize_alliance_tag(alliance_tag) or ""
    return conn.execute(
        """
        SELECT * FROM attacks
        WHERE deleted_at IS NULL
          AND (attacker_alliance_tag = ? OR defender_alliance_tag = ?)
          AND (? IS NULL OR server_id = ?)
        ORDER BY COALESCE(occurred_at, created_at) DESC, id DESC
        LIMIT ?
        """,
        (alliance_tag, alliance_tag, server_id, server_id, limit),
    ).fetchall()


def deleted_attacks(conn: sqlite3.Connection, limit: int = 200) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM attacks
        WHERE deleted_at IS NOT NULL
        ORDER BY deleted_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
