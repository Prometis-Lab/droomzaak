"""Droomzaak FastAPI app.

Boots with no secrets. The DataGateway pool is opened at startup only when
`DROOMZAAK_POSTGRES_URL` is configured; otherwise the app still serves the shell
and the pure-LLM chapters, and analytical tools return the documented
`{error, hint}` envelope.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app import droomzaak_chapters, settings
from backend.app.storage import CatalogStore, get_store

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


StoreDep = Depends(get_store)


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


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict = {}


@app.post("/api/agent/chat")
async def agent_chat(body: ChatRequest, store: CatalogStore = StoreDep) -> dict:
    session_id = body.session_id or uuid.uuid4().hex
    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message=body.message, session_id=session_id,
        frontend_context=body.context,
    )
    return result


@app.post("/api/agent/session")
async def create_session() -> dict:
    return {"session_id": uuid.uuid4().hex}


@app.delete("/api/agent/session/{session_id}")
async def delete_session(session_id: str, store: CatalogStore = StoreDep) -> dict:
    store.delete_session(session_id)
    return {"deleted": True}


@app.get("/api/agent/debug/{debug_id}")
async def get_debug(debug_id: str, store: CatalogStore = StoreDep) -> dict:
    run = store.load_debug(debug_id)
    if run is None:
        raise HTTPException(404, "debug run not found")
    return run


@app.get("/api/droomzaak/chapter/{session_id}")
async def get_chapter(session_id: str, store: CatalogStore = StoreDep) -> dict:
    state = store.load_chapter_state(session_id) or droomzaak_chapters.default_chapter_state()
    return {"current_chapter": state["current_chapter"], "chapter_state": state}


class ChapterPatch(BaseModel):
    patch: dict


@app.put("/api/droomzaak/chapter/{session_id}")
async def put_chapter(session_id: str, body: ChapterPatch, store: CatalogStore = StoreDep) -> dict:
    from backend.app.droomzaak_validation import validate_set_chapter_state

    state = store.load_chapter_state(session_id) or droomzaak_chapters.default_chapter_state()
    validated, err = validate_set_chapter_state({"type": "set_chapter_state", "patch": body.patch}, state)
    if err:
        raise HTTPException(400, detail=err)
    new_state = droomzaak_chapters.apply_state_patch(state, validated["patch"])
    store.save_chapter_state(session_id, new_state)
    return {"current_chapter": new_state["current_chapter"], "chapter_state": new_state}
