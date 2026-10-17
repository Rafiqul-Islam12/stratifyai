"""SQLite append-only audit log with a verifiable SHA-256 hash chain."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "audit.sqlite3"
_SENSITIVE = re.compile(r"password|secret|token|credential|authorization|api.?key", re.IGNORECASE)
_VALUE_SECRET = re.compile(r"(?i)(bearer\s+\S+|(?:password|secret|token|api[_-]?key)\s*[:=]\s*\S+)")
_FIELDS = ("ts", "actor", "role", "action", "entity", "payload_json", "prev_hash")


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    broken_index: int | None
    message: str


def database_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path or os.getenv("STRATIFY_AUDIT_DB") or DEFAULT_DB)


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    with connect(db_path) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            actor TEXT NOT NULL,
            role TEXT NOT NULL,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        )""")
        connection.execute("""CREATE TRIGGER IF NOT EXISTS audit_log_no_update
            BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END""")
        connection.execute("""CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
            BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END""")


def _clean(value: Any, *, limit: int = 500) -> Any:
    if isinstance(value, dict):
        return {str(key)[:80]: ("[REDACTED]" if _SENSITIVE.search(str(key)) else _clean(item))
                for key, item in value.items() if not _SENSITIVE.search(str(key))}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value[:100]]
    if isinstance(value, str):
        cleaned = " ".join(value.replace("\x00", "").split())[:limit]
        return _VALUE_SECRET.sub("[REDACTED]", cleaned)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:limit]


def _canonical(record: dict[str, str]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_record(record: dict[str, str]) -> str:
    return hashlib.sha256((record["prev_hash"] + _canonical(record)).encode("utf-8")).hexdigest()


def log_event(
    actor: str,
    role: str,
    action: str,
    entity: str = "",
    payload: dict[str, Any] | None = None,
    *,
    db_path: str | Path | None = None,
) -> int:
    """Append a sanitized event and return its row id."""
    init_db(db_path)
    clean_payload = _clean(payload or {})
    payload_json = json.dumps(clean_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(payload_json.encode("utf-8")) > 4096:
        payload_json = json.dumps({"truncated": True}, separators=(",", ":"))
    with connect(db_path) as connection:
        previous = connection.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = previous["hash"] if previous else "0" * 64
        record = {
            "ts": datetime.now(UTC).isoformat(timespec="microseconds"),
            "actor": str(_clean(actor, limit=100)),
            "role": str(_clean(role, limit=40)),
            "action": str(_clean(action, limit=100)),
            "entity": str(_clean(entity, limit=200)),
            "payload_json": payload_json,
            "prev_hash": prev_hash,
        }
        digest = _hash_record(record)
        cursor = connection.execute(
            "INSERT INTO audit_log (ts, actor, role, action, entity, payload_json, prev_hash, hash) "
            "VALUES (:ts, :actor, :role, :action, :entity, :payload_json, :prev_hash, :hash)",
            {**record, "hash": digest},
        )
        return int(cursor.lastrowid)


def verify_chain(*, db_path: str | Path | None = None) -> ChainVerification:
    init_db(db_path)
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    prior = "0" * 64
    for row in rows:
        record = {field: str(row[field]) for field in _FIELDS}
        expected = _hash_record(record)
        if record["prev_hash"] != prior or row["hash"] != expected:
            return ChainVerification(False, int(row["id"]), f"Audit chain broken at entry {row['id']}.")
        prior = str(row["hash"])
    return ChainVerification(True, None, f"Audit chain OK ({len(rows)} entries).")


def list_events(
    *, actor: str | None = None, action: str | None = None, limit: int = 500,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    init_db(db_path)
    limit = min(2000, max(1, int(limit)))
    conditions, params = [], []
    if actor:
        conditions.append("actor = ?")
        params.append(actor)
    if action:
        conditions.append("action = ?")
        params.append(action)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM audit_log {where} ORDER BY id DESC LIMIT ?", (*params, limit)).fetchall()
    return [dict(row) for row in rows]
