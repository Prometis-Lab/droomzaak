"""Render/session tier — a thin DuckDB store.

Holds per-session conversation history + chapter state + the composed package.
This tier is NEVER the agent's analytical read path (that is the DataGateway);
it persists sessions and serves the package renderer.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import duckdb

from backend.app import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id          VARCHAR PRIMARY KEY,
    provider_label      VARCHAR,
    messages_json       VARCHAR,
    chapter_state_json  VARCHAR,
    package_json        VARCHAR,
    updated_at          TIMESTAMP DEFAULT now()
);
CREATE TABLE IF NOT EXISTS agent_debug_runs (
    debug_id    VARCHAR PRIMARY KEY,
    session_id  VARCHAR,
    stages_json VARCHAR,
    created_at  TIMESTAMP DEFAULT now()
);
"""


class CatalogStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(path)
        self.connection.execute(_SCHEMA)

    def close(self) -> None:
        self.connection.close()

    # ── sessions ────────────────────────────────────────────────────
    def load_messages(self, session_id: str) -> tuple[list, str | None]:
        with self._lock:
            row = self.connection.execute(
                "SELECT messages_json, provider_label FROM agent_sessions WHERE session_id = ?",
                [session_id],
            ).fetchone()
        if not row or not row[0]:
            return [], None
        return json.loads(row[0]), row[1]

    def save_messages(self, session_id: str, provider_label: str, messages: list) -> None:
        payload = json.dumps(messages, ensure_ascii=False, default=str)
        with self._lock:
            self.connection.execute(
                """INSERT INTO agent_sessions (session_id, provider_label, messages_json, updated_at)
                   VALUES (?, ?, ?, now())
                   ON CONFLICT (session_id) DO UPDATE SET
                     provider_label = excluded.provider_label,
                     messages_json  = excluded.messages_json,
                     updated_at     = now()""",
                [session_id, provider_label, payload],
            )

    # ── chapter state ───────────────────────────────────────────────
    def load_chapter_state(self, session_id: str) -> dict | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT chapter_state_json FROM agent_sessions WHERE session_id = ?",
                [session_id],
            ).fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])

    def save_chapter_state(self, session_id: str, state: dict) -> None:
        payload = json.dumps(state, ensure_ascii=False)
        with self._lock:
            self.connection.execute(
                """INSERT INTO agent_sessions (session_id, chapter_state_json, updated_at)
                   VALUES (?, ?, now())
                   ON CONFLICT (session_id) DO UPDATE SET
                     chapter_state_json = excluded.chapter_state_json,
                     updated_at         = now()""",
                [session_id, payload],
            )

    # ── package ─────────────────────────────────────────────────────
    def save_package(self, session_id: str, package: dict) -> None:
        payload = json.dumps(package, ensure_ascii=False)
        with self._lock:
            self.connection.execute(
                """INSERT INTO agent_sessions (session_id, package_json, updated_at)
                   VALUES (?, ?, now())
                   ON CONFLICT (session_id) DO UPDATE SET
                     package_json = excluded.package_json,
                     updated_at   = now()""",
                [session_id, payload],
            )

    def load_package(self, session_id: str) -> dict | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT package_json FROM agent_sessions WHERE session_id = ?",
                [session_id],
            ).fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])

    # ── debug ───────────────────────────────────────────────────────
    def save_debug(self, debug_id: str, session_id: str, stages: list) -> None:
        payload = json.dumps(stages, ensure_ascii=False, default=str)
        with self._lock:
            self.connection.execute(
                """INSERT INTO agent_debug_runs (debug_id, session_id, stages_json)
                   VALUES (?, ?, ?) ON CONFLICT (debug_id) DO UPDATE SET
                     stages_json = excluded.stages_json""",
                [debug_id, session_id, payload],
            )

    def load_debug(self, debug_id: str) -> dict | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT session_id, stages_json FROM agent_debug_runs WHERE debug_id = ?",
                [debug_id],
            ).fetchone()
        if not row:
            return None
        return {"session_id": row[0], "stages": json.loads(row[1]) if row[1] else []}

    def load_debugs_for_session(self, session_id: str) -> list[dict]:
        """Every turn's debug run for a session, oldest first — the trace source."""
        with self._lock:
            rows = self.connection.execute(
                "SELECT debug_id, stages_json, created_at FROM agent_debug_runs "
                "WHERE session_id = ? ORDER BY created_at",
                [session_id],
            ).fetchall()
        return [
            {"debug_id": r[0], "stages": json.loads(r[1]) if r[1] else [],
             "created_at": str(r[2]) if r[2] is not None else None}
            for r in rows
        ]


_store: CatalogStore | None = None


def get_store() -> CatalogStore:
    global _store
    if _store is None:
        _store = CatalogStore(settings.DUCKDB_PATH)
    return _store


def set_store(store: CatalogStore | None) -> None:
    """Test seam: override the singleton (e.g. an in-memory store)."""
    global _store
    _store = store
