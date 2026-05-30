"""Runtime settings, sourced from the environment (`.env.demo` on Friday).

Everything here has a safe default so the app boots with no secrets — analytical
chapters degrade to the documented `{error, hint}` envelope until the DataGateway
is wired, but the shell, the map, and the pure-LLM chapters (1 + 5) still run.
"""

from __future__ import annotations

import os

try:  # Load .env.demo then .env (gitignored) so localhost needs no manual export.
    from dotenv import load_dotenv

    load_dotenv(".env.demo")
    load_dotenv(".env")
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _csv(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ── Model providers ────────────────────────────────────────────────────
AGENT_PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")  # anthropic | openai
AGENT_LANGUAGE = os.environ.get("AGENT_LANGUAGE", "nl")  # nl primary, en fallback
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
# GPT-5 reasoning effort: minimal | low | medium | high. Only sent to gpt-5* models.
OPENAI_REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "minimal")
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

# ── Dev-only flag — default OFF; MUST stay off for the demo/pitch ───────
# When on, the system prompt gains a block telling the agent to fabricate
# clearly-labelled placeholder figures whenever a data tool is offline, so the
# loop can be exercised without the DataGateway/warehouse. This intersects the
# "never fake certainty" invariant: NEVER add DROOMZAAK_DEV_FABRICATE to
# .env.demo or any demo/prod shell — a labelled fake is still a fake in front of
# a jury / the Aikido audit. Local dev only.
DROOMZAAK_DEV_FABRICATE = os.environ.get("DROOMZAAK_DEV_FABRICATE", "").strip().lower() in (
    "1", "true", "yes", "on",
)

# ── Conversation tracing (debug-only; data/ is gitignored) ─────────────
# Per-turn JSONL trace under DROOMZAAK_TRACE_DIR so a whole conversation can be
# replayed/judged offline. Default ON; never on the agent's read path.
DROOMZAAK_TRACE_TO_FILE = os.environ.get("DROOMZAAK_TRACE_TO_FILE", "1").strip().lower() in (
    "1", "true", "yes", "on",
)
DROOMZAAK_TRACE_DIR = os.environ.get("DROOMZAAK_TRACE_DIR", "data/traces")

# ── Live behaviour tools (not routed through the DataGateway) ───────────
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
