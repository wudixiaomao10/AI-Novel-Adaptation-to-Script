"""SQLite persistence for Novel2Script."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "novel2script.db"


def utc_now() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with dict-like rows."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def dumps(value: Any) -> str:
    """Serialize JSON payloads consistently."""
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None, fallback: Any) -> Any:
    """Deserialize JSON payloads with a fallback."""
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def init_database() -> None:
    """Create database tables when they do not exist."""
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '草稿',
                yaml TEXT NOT NULL DEFAULT '',
                script_data TEXT NOT NULL DEFAULT '{}',
                analysis TEXT NOT NULL DEFAULT '{}',
                stats TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                title TEXT NOT NULL,
                script_data TEXT NOT NULL DEFAULT '{}',
                yaml TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS storyboards (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                title TEXT NOT NULL,
                rows_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS history_records (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '成功',
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a project row to API JSON."""
    return {
        "id": row["id"],
        "title": row["title"],
        "source_text": row["source_text"],
        "status": row["status"],
        "yaml": row["yaml"],
        "scriptData": loads(row["script_data"], {}),
        "analysis": loads(row["analysis"], None),
        "stats": loads(row["stats"], {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_project(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a project."""
    now = utc_now()
    project_id = str(payload.get("id") or uuid4())
    with connect() as conn:
        existing = conn.execute("SELECT created_at FROM projects WHERE id = ?", (project_id,)).fetchone()
        created_at = existing["created_at"] if existing else str(payload.get("created_at") or now)
        conn.execute(
            """
            INSERT INTO projects (
                id, title, source_text, status, yaml, script_data,
                analysis, stats, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                source_text = excluded.source_text,
                status = excluded.status,
                yaml = excluded.yaml,
                script_data = excluded.script_data,
                analysis = excluded.analysis,
                stats = excluded.stats,
                updated_at = excluded.updated_at
            """,
            (
                project_id,
                str(payload.get("title") or "未命名项目"),
                str(payload.get("source_text") or ""),
                str(payload.get("status") or "草稿"),
                str(payload.get("yaml") or ""),
                dumps(payload.get("scriptData") or {}),
                dumps(payload.get("analysis")),
                dumps(payload.get("stats") or {}),
                created_at,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row_to_project(row)


def list_projects() -> list[dict[str, Any]]:
    """Return all projects newest first."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    return [row_to_project(row) for row in rows]


def get_project(project_id: str) -> dict[str, Any] | None:
    """Return one project by id."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row_to_project(row) if row else None


def delete_project(project_id: str) -> bool:
    """Delete one project."""
    with connect() as conn:
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return cursor.rowcount > 0


def save_history(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a history record."""
    record = {
        "id": str(payload.get("id") or uuid4()),
        "title": str(payload.get("title") or "未命名记录"),
        "action_type": str(payload.get("type") or payload.get("action_type") or "操作"),
        "status": str(payload.get("status") or "成功"),
        "payload": payload,
        "created_at": str(payload.get("createdAt") or payload.get("created_at") or utc_now()),
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO history_records (id, title, action_type, status, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["title"],
                record["action_type"],
                record["status"],
                dumps(record["payload"]),
                record["created_at"],
            ),
        )
    return record


def list_history() -> list[dict[str, Any]]:
    """Return history records newest first."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM history_records ORDER BY created_at DESC").fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "type": row["action_type"],
            "status": row["status"],
            "createdAt": row["created_at"],
            **loads(row["payload"], {}),
        }
        for row in rows
    ]


def upsert_setting(key: str, value: Any) -> None:
    """Save one settings value."""
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, dumps(value), utc_now()),
        )


def read_settings() -> dict[str, Any]:
    """Return settings as a plain object."""
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: loads(row["value"], None) for row in rows}
