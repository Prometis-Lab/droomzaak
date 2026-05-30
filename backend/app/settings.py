"""Runtime settings, sourced from the environment (`.env.demo` on Friday).

Everything here has a safe default so the app boots with no secrets — analytical
chapters degrade to the documented `{error, hint}` envelope until the DataGateway
is wired, but the shell, the map, and the pure-LLM chapters (1 + 5) still run.
"""

from __future__ import annotations

import os


def _csv(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ── Model providers ────────────────────────────────────────────────────
AGENT_PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")  # anthropic | openai
AGENT_LANGUAGE = os.environ.get("AGENT_LANGUAGE", "nl")  # nl primary, en fallback
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
AGENT_MAX_TOOL_ITERATIONS = int(os.environ.get("AGENT_MAX_TOOL_ITERATIONS", "8"))
AGENT_SESSION_TURNS = int(os.environ.get("AGENT_SESSION_TURNS", "20"))

# ── DataGateway (the agent's analytical read path) ─────────────────────
DROOMZAAK_POSTGRES_URL = (
    os.environ.get("DROOMZAAK_POSTGRES_URL")
    or os.environ.get("DROOMZAAK_PG_DSN")
    or os.environ.get("SUPABASE_DB_URL")
    or ""
)
DROOMZAAK_POOL_MAX_SIZE = int(os.environ.get("DROOMZAAK_POOL_MAX_SIZE", "5"))
DROOMZAAK_QUERY_TIMEOUT_SECONDS = float(os.environ.get("DROOMZAAK_QUERY_TIMEOUT_SECONDS", "10"))

# ── Live behaviour tools (not routed through the DataGateway) ───────────
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
OPENROUTESERVICE_API_KEY = os.environ.get("OPENROUTESERVICE_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
OVERPASS_API_URL = os.environ.get("OVERPASS_API_URL", "https://overpass-api.de/api/interpreter")
NOMINATIM_URL = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")

# ── Storage (render/session tier — DuckDB) ─────────────────────────────
DUCKDB_PATH = os.environ.get("DROOMZAAK_DUCKDB_PATH", "data/droomzaak.duckdb")

# ── HTTP / CORS ────────────────────────────────────────────────────────
CORS_ALLOW_ORIGINS = _csv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

# Ghent map default view (lon, lat) — Korenmarkt / Vrijdagmarkt area.
GHENT_CENTER = (3.7257, 51.0543)
GHENT_REFNIS = "44021"
