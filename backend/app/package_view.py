"""Package renderer — builds the printable *Droomzaak-pakket* from the
render/session tier (DuckDB) and renders it via Jinja2.

Presentation only. This NEVER touches the DataGateway / Postgres — the pakket is
the founder's takeaway artefact, not analytical reasoning (data-tiers boundary).
Proxy labels carried on the data are rendered verbatim; the template adds a
disclaimer footer (never fake certainty).

Field shapes are the REAL ones produced by `handle_compose_package`
(droomzaak_tools.py) and `_CHAPTER_KEYS` (droomzaak_chapters.py) — not invented.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# backend/app/package_view.py → backend/templates/  (source-run resolution).
# If a wheel build is ever used, add backend/templates/*.html to the hatch
# wheel `artifacts`/`force-include` — hatchling excludes .html by default.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),  # injection boundary for free text
)


def _paragraphs(text: str) -> list[str]:
    """Split a narrative string into paragraphs in Python (no markdown dep).

    The template renders these as escaped <p>s — splitting here keeps the
    template free of any `| safe` escape hatch. A block with no blank lines
    becomes a single paragraph.
    """
    if not text:
        return []
    normalised = text.replace("\r\n", "\n")
    blocks = [block.strip() for block in normalised.split("\n\n")]
    return [block for block in blocks if block]


def _has_content(pkg: dict) -> bool:
    """A package worth rendering has at least a dream, a place, or some output."""
    return bool(
        pkg.get("dream_profile")
        or pkg.get("chosen_location")
        or pkg.get("permit_checklist")
        or pkg.get("subsidies")
        or pkg.get("dream_narrative")
    )


def build_package_dict(state: dict, session_id: str, *, generated_at: str = "") -> dict:
    """The single definition of the package shape — mirrors handle_compose_package.

    Used by the renderer's fallback path and by compose_from_state, so the shape
    lives in one place. `generated_at` is stamped only on the finalise path; the
    template hides the date line when it is empty.
    """
    return {
        "session_id": session_id,
        "generated_at": generated_at,
        "dream_profile": state.get("dream_profile") or {},
        "niche_signals": state.get("niche_signals") or {},
        "chosen_location": state.get("chosen_location") or {},
        "candidate_locations": state.get("candidate_locations") or [],
        "permit_checklist": state.get("permit_checklist") or [],
        "subsidies": state.get("subsidies") or [],
        "legal_form": state.get("legal_form") or {},
        "dream_narrative": state.get("dream_narrative") or "",
        "tuesday_morning": state.get("tuesday_morning") or "",
    }


def build_package_context(store, session_id: str) -> dict | None:
    """Load the composed package, or synthesize one from chapter_state.

    Returns None when there is nothing worth rendering (no session row, or only
    the empty default state) → the route turns that into a 404.
    """
    pkg = store.load_package(session_id)
    if pkg is None:
        state = store.load_chapter_state(session_id)
        if not state:
            return None
        pkg = build_package_dict(state, session_id)
    else:
        # Normalise the saved package through the same coalescing as build_package_dict,
        # so the template always receives clean defaults instead of None values.
        pkg = build_package_dict(pkg, session_id, generated_at=pkg.get("generated_at") or "")
    if not _has_content(pkg):
        return None
    ctx = dict(pkg)
    ctx["narrative_paragraphs"] = _paragraphs(pkg.get("dream_narrative") or "")
    return ctx


def compose_from_state(store, session_id: str) -> dict | None:
    """Finalise: build the package from the latest chapter_state and persist it.

    Lets the frontend produce the pakket regardless of whether the agent called
    compose_package. Returns None (→ 404) for an empty session.
    """
    state = store.load_chapter_state(session_id)
    if not state:
        return None
    pkg = build_package_dict(state, session_id, generated_at=_dt.date.today().isoformat())
    if not _has_content(pkg):
        return None
    store.save_package(session_id, pkg)
    return pkg


def render_package_html(ctx: dict) -> str:
    return _env.get_template("pakket.html").render(**ctx)
