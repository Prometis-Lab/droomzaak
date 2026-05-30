"""The DataGateway — the single audited seam onto the droomzaak Postgres.

Every analytical datum the agent reasons over flows through `gateway.query(...)`
(parameterized SQL only). This is the architectural pitch: one chokepoint, one
audit log, visible in the debug overlay. Behaviour tools (OSM, Places, geocode,
web_search) do NOT come through here.

The audit log is in-process and exposed so a per-turn debug stage can show every
analytical read. Parameterized SQL only — never string-format model/user input.
"""

from __future__ import annotations

import time
from typing import Any

from backend.app import settings

try:  # asyncpg is optional at import time so the app boots without Postgres
    import asyncpg
except Exception:  # pragma: no cover
    asyncpg = None  # type: ignore


class DataGatewayUnavailable(RuntimeError):
    """Raised when an analytical read is attempted but the pool isn't open."""


class DataGateway:
    """One pool, one `query(sql, params)` method, one audit log."""

    def __init__(self) -> None:
        self._pool: Any | None = None
        self.audit_log: list[dict] = []

    @property
    def is_connected(self) -> bool:
        return self._pool is not None

    async def connect(self) -> None:
        """Open the pool. Called from the FastAPI lifespan at startup."""
        if asyncpg is None:  # pragma: no cover
            raise DataGatewayUnavailable("asyncpg not installed")
        if not settings.DROOMZAAK_POSTGRES_URL:
            raise DataGatewayUnavailable("DROOMZAAK_POSTGRES_URL not configured")
        self._pool = await asyncpg.create_pool(
            dsn=settings.DROOMZAAK_POSTGRES_URL,
            min_size=1,
            max_size=settings.DROOMZAAK_POOL_MAX_SIZE,
            command_timeout=settings.DROOMZAAK_QUERY_TIMEOUT_SECONDS,
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def query(
        self, sql: str, params: list[Any] | None = None, *, tool_name: str | None = None
    ) -> list[dict]:
        """Issue a parameterized SELECT; return rows as dicts. Audit-logged.

        `tool_name` is recorded for the debug overlay so each read is attributable
        to the analytical tool that made it.
        """
        if self._pool is None:
            raise DataGatewayUnavailable(
                "DataGateway pool not open — analytical data is unavailable"
            )
        started = time.perf_counter()
        rows = await self._pool.fetch(sql, *(params or []))
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        self.audit_log.append(
            {
                "tool_name": tool_name,
                "sql_summary": " ".join(sql.split())[:120],
                "params_count": len(params or []),
                "rows_returned": len(rows),
                "latency_ms": latency_ms,
            }
        )
        return [dict(r) for r in rows]

    async def health_check(self) -> dict:
        rows = await self.query("SELECT 1 AS ok")
        return {"ok": rows[0]["ok"] == 1}

    def drain_audit(self) -> list[dict]:
        """Return and clear the audit entries accumulated this turn."""
        entries = self.audit_log[:]
        self.audit_log.clear()
        return entries


gateway = DataGateway()
