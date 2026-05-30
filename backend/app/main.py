"""Droomzaak FastAPI app.

Boots with no secrets. The DataGateway pool is opened at startup only when
`DROOMZAAK_POSTGRES_URL` is configured; otherwise the app still serves the shell
and the pure-LLM chapters, and analytical tools return the documented
`{error, hint}` envelope.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app import settings

log = logging.getLogger("droomzaak")


@asynccontextmanager
async def lifespan(app: FastAPI):
    gateway_ok = False
    if settings.DROOMZAAK_POSTGRES_URL:
        try:
            from backend.app.data_gateway import gateway

            await gateway.connect()
            health = await gateway.health_check()
            gateway_ok = bool(health.get("ok"))
            log.info("DataGateway connected (health=%s)", health)
        except Exception as exc:  # pragma: no cover - startup diagnostics
            log.warning("DataGateway unavailable at startup: %s", exc)
    else:
        log.info("DROOMZAAK_POSTGRES_URL not set — DataGateway disabled (degraded mode)")
    app.state.gateway_ok = gateway_ok
    yield
    if settings.DROOMZAAK_POSTGRES_URL:
        try:
            from backend.app.data_gateway import gateway

            await gateway.close()
        except Exception:  # pragma: no cover
            pass


app = FastAPI(title="Droomzaak", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/admin/health")
async def health() -> dict:
    """Liveness probe — always 200 once the process is up."""
    return {
        "ok": True,
        "service": "droomzaak",
        "provider": settings.AGENT_PROVIDER,
        "language": settings.AGENT_LANGUAGE,
        "gateway_configured": bool(settings.DROOMZAAK_POSTGRES_URL),
        "gateway_ok": getattr(app.state, "gateway_ok", False),
    }
