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


def _is_number(value: object) -> bool:
    # bool is an int subclass; exclude it so a stray True can't read as 1 euro.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_SAFE_URL_SCHEMES = ("http://", "https://")


def _safe_url(value: object) -> str | None:
    """Return `value` only if it's a safe link target, else None.

    `deep_link` is rendered into an `<a href>`; Jinja autoescaping escapes the
    *text* but does NOT neutralise a dangerous URL scheme, so a stored
    `javascript:`/`data:`/`vbscript:` link would execute on click. deep_link can
    arrive from curated config, an agent tool, OR an attacker-controlled
    chapter-state patch (PUT /chapter), so this output-side guard is the real
    defence: only plain http(s) or a site-relative path survives; anything else
    drops to None and the template hides the link. (Aikido: stored XSS.)
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.lower().startswith(_SAFE_URL_SCHEMES):
        return candidate
    # Site-relative path, but reject protocol-relative `//host` which dodges the
    # scheme check above.
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return None


def _with_safe_links(items: object) -> list:
    """Copy each item with its `deep_link` passed through `_safe_url`."""
    if not isinstance(items, list):
        return []
    return [
        {**item, "deep_link": _safe_url(item.get("deep_link"))}
        if isinstance(item, dict) and "deep_link" in item
        else item
        for item in items
    ]


def _clean_permits(items: object) -> list[dict]:
    """Keep only renderable permit rows (a dict with a name).

    Guards the "don't render an empty section" rule against a truthy-but-itemless
    value — e.g. the agent persisting a placeholder list. A row with no
    permit_name has nothing to show, so it never reaches the template.
    """
    if not isinstance(items, list):
        return []
    return [p for p in items if isinstance(p, dict) and p.get("permit_name")]


def _clean_subsidies(items: object) -> list[dict]:
    """Keep only renderable subsidy rows (a dict with a name) — see _clean_permits."""
    if not isinstance(items, list):
        return []
    return [s for s in items if isinstance(s, dict) and s.get("name")]


# dream_profile keys → founder-facing label, in display order. sector + founder_quote
# are already in the header; nace_code is concrete and useful, so it stays.
_DREAM_FACT_LABELS: list[tuple[str, str]] = [
    ("scale", "Schaal"),
    ("seats_guess", "Zitplaatsen"),
    ("neighbourhood_anchor", "Buurt"),
    ("vibe", "Sfeer"),
    ("partners_guess", "Partners"),
    ("nace_code", "NACE-code"),
]


def _dream_facts(dp: dict) -> list[dict]:
    """The 'De droom' fiche — the profile bullets shown in the Droomkaart sidebar,
    minus what the header already carries (sector, founder_quote)."""
    facts: list[dict] = []
    for key, label in _DREAM_FACT_LABELS:
        value = dp.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        facts.append({"label": label, "value": str(value)})
    budget = dp.get("budget_eur_guess")
    if _is_number(budget):
        facts.append({"label": "Startbudget", "value": f"± €{int(budget)}"})
    return facts


# Technical plumbing that leaks into niche_signals (layer ids, fetch errors) — never
# founder-facing, so it must not surface in the printed pakket.
def _is_plumbing_key(key: str) -> bool:
    low = key.lower()
    return "layer" in low or "error" in low


def _niche_facts(ns: dict) -> list[dict]:
    """The 'Niche' fiche — clean primitive signals, mirroring the Droomkaart, plus a
    few peer-benchmark figures when present (the richest niche datum lives nested)."""
    facts: list[dict] = []
    for key, value in ns.items():
        if _is_plumbing_key(key):
            continue
        if isinstance(value, (str, int, float)) and not isinstance(value, bool) and str(value).strip():
            facts.append({"label": key.replace("_", " "), "value": str(value)})

    peers = ns.get("peer_benchmarks")
    if isinstance(peers, dict):
        count = peers.get("active_count_latest")
        if _is_number(count):
            facts.append({"label": "Vergelijkbare zaken", "value": f"± {int(count)}"})
        growth = peers.get("growth_3y_pct")
        if _is_number(growth):
            facts.append({"label": "Groei (3 jaar)", "value": f"{growth:+.1f}%"})
        bankruptcies = peers.get("bankruptcies_latest")
        if _is_number(bankruptcies):
            facts.append({"label": "Faillissementen (recent)", "value": str(int(bankruptcies))})
    return facts


def _niche_note(ns: dict) -> str:
    """The peer-benchmark scope note — a proxy label rendered verbatim (never fake
    certainty: the figures are cohort-level, not per-address)."""
    peers = ns.get("peer_benchmarks")
    if isinstance(peers, dict):
        note = peers.get("scope_note")
        if isinstance(note, str) and note.strip():
            return note.strip()
    return ""


def _summary_chips(pkg: dict) -> list[dict]:
    """The most-important points, surfaced as a glanceable strip atop the pakket.

    Pure presentation: counts/sums the already-curated package fields (never the
    warehouse). Each chip is hidden when its underlying data is absent, so a thin
    session shows a short strip rather than empty placeholders.
    """
    chips: list[dict] = []

    location = pkg.get("chosen_location") or {}
    place = location.get("wijk_nl") or location.get("address")
    if place:
        chips.append({"label": "Locatie", "value": place})

    permits = pkg.get("permit_checklist") or []
    if permits:
        chips.append({"label": "Vergunningen", "value": str(len(permits))})

    legal_form = pkg.get("legal_form") or {}
    setup_cost = legal_form.get("estimated_setup_cost_eur")
    total = sum(p["estimated_cost_eur"] for p in permits if _is_number(p.get("estimated_cost_eur")))
    if _is_number(setup_cost):
        total += setup_cost
    if total:
        chips.append({"label": "Geschatte opstartkosten", "value": f"± €{int(total)}"})

    active_subsidies = [s for s in (pkg.get("subsidies") or []) if s.get("status") != "ended_2025"]
    if active_subsidies:
        chips.append({"label": "Beschikbare steun", "value": f"{len(active_subsidies)} regeling(en)"})

    if legal_form.get("recommended"):
        chips.append({"label": "Rechtsvorm", "value": legal_form["recommended"]})

    return chips


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
        "permit_checklist": _with_safe_links(state.get("permit_checklist") or []),
        "subsidies": _with_safe_links(state.get("subsidies") or []),
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
    # Drop itemless permit/subsidy rows up front so the chips, the section guards,
    # and the template all see the same cleaned lists (no blank sections).
    pkg["permit_checklist"] = _clean_permits(pkg.get("permit_checklist"))
    pkg["subsidies"] = _clean_subsidies(pkg.get("subsidies"))
    if not _has_content(pkg):
        return None
    ctx = dict(pkg)
    ctx["narrative_paragraphs"] = _paragraphs(pkg.get("dream_narrative") or "")
    ctx["summary_chips"] = _summary_chips(pkg)
    ctx["dream_facts"] = _dream_facts(pkg.get("dream_profile") or {})
    ctx["niche_facts"] = _niche_facts(pkg.get("niche_signals") or {})
    ctx["niche_note"] = _niche_note(pkg.get("niche_signals") or {})
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
