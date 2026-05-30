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

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, field_validator

from backend.app import agent_trace, droomzaak_chapters, package_view, pdf_render, settings
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

    @field_validator("session_id")
    @classmethod
    def _safe_session_id(cls, v: str | None) -> str | None:
        # session_id is used as a filesystem stem by the trace sink — keep it to
        # the id alphabet (real ids are uuid4().hex). Reject path-traversal input.
        if v is not None and not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("session_id must be alphanumeric (with - or _)")
        return v


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


@app.get("/api/agent/debug/{debug_id}")
async def get_debug(debug_id: str, store: CatalogStore = StoreDep) -> dict:
    run = store.load_debug(debug_id)
    if run is None:
        raise HTTPException(404, "debug run not found")
    return run


@app.get("/api/agent/trace/{session_id}")
async def get_trace(session_id: str, format: str = "json", store: CatalogStore = StoreDep):
    """Full-conversation trace for judging a run after the fact: every turn's tool
    calls (args, result, latency, ok/error) + a per-turn summary. `format=text`
    returns a human-readable timeline; default is structured JSON with a digest."""
    turns = store.load_debugs_for_session(session_id)
    if not turns:
        raise HTTPException(404, "geen trace voor deze sessie")
    if format == "text":
        return PlainTextResponse(agent_trace.render_trace_text(session_id, turns))
    return {"session_id": session_id, "summary": agent_trace.summarize_session(turns),
            "turns": turns}


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


# ── Droomzaak-pakket (Chapter-5 printable artefact) ──────────────────────
@app.post("/api/droomzaak/package/{session_id}")
async def finalise_package(session_id: str, store: CatalogStore = StoreDep) -> dict:
    """Compose + persist the pakket from the latest chapter_state, then hand back
    its URL. Lets the frontend finalise regardless of whether the agent already
    called compose_package."""
    pkg = package_view.compose_from_state(store, session_id)
    if pkg is None:
        raise HTTPException(404, "Nog geen pakket voor deze sessie.")
    return {"package_url": f"/pakket/{session_id}", "ready": True}


@app.get("/pakket/{session_id}", response_class=HTMLResponse)
async def render_pakket(session_id: str, store: CatalogStore = StoreDep) -> HTMLResponse:
    """Server-rendered printable Droomzaak-pakket (render/session tier only)."""
    ctx = package_view.build_package_context(store, session_id)
    if ctx is None:
        raise HTTPException(404, "Nog geen pakket voor deze sessie.")
    return HTMLResponse(package_view.render_package_html(ctx))


@app.get("/pakket/{session_id}/pdf")
async def download_pakket_pdf(session_id: str, store: CatalogStore = StoreDep) -> Response:
    """One-click PDF: render the same pakket HTML to a real PDF via headless Chromium.

    503 (not 500) if the PDF engine/Chromium is unavailable, so the page's
    browser-print fallback stays the graceful degradation path."""
    ctx = package_view.build_package_context(store, session_id)
    if ctx is None:
        raise HTTPException(404, "Nog geen pakket voor deze sessie.")
    html = package_view.render_package_html(ctx)
    try:
        pdf_bytes = await pdf_render.html_to_pdf(html)
    except Exception as exc:  # ImportError / missing Chromium / render failure
        log.warning("PDF-generatie mislukt voor sessie %s: %s", session_id, exc)
        raise HTTPException(503, "PDF-generatie is niet beschikbaar; gebruik 'Afdrukken'.") from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="droomzaak-pakket.pdf"'},
    )
