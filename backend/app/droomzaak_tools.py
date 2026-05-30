"""The 11 Droomzaak tools.

Data-tier boundary (data-tiers.md):
  ANALYTICAL tools (peer_benchmarks_statbel, score_locations, rent_benchmark)
    → thin wrappers around gateway.query(sql, [params], tool_name="...")
    → return {error, hint} envelope on gateway failure, or fabricate fallback
      when settings.DROOMZAAK_DEV_FABRICATE is on.
  CONFIG-FILE tools (permit_checklist_for, subsidies_for)
    → read curated YAML from config/ at module level (lru_cache).
    → NO gateway call; config is always present on disk.
    → No fabricate fallback needed (YAML is always loadable).
  BEHAVIOUR tools (places_search) → native HTTP, no gateway.
  LLM tools (extract_dream_profile, generate_dream_narrative) → complete_json seam.
  PURE-PYTHON tools (legal_form_advisor, compose_package) → no I/O.

set_chapter_state is NOT here — committed through apply_map_actions.
"""

from __future__ import annotations

import datetime as _dt
import functools
import hashlib
import json
import pathlib
from typing import Any

import yaml  # pyyaml — already in pyproject.toml

from backend.app import droomzaak_fabricate, settings
from backend.app.agent_loop import AgentRun
from backend.app.data_gateway import DataGatewayUnavailable, gateway

_CURRENT_YEAR = 2025  # 2025: starters_flanders/bankruptcies have 2025 data


def _hash(*parts: Any) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


def _gw_error(exc: Exception) -> dict:
    return {"error": f"data unavailable: {exc}",
            "hint": "Probeer het zo opnieuw, of roep report_problem aan als het blijft falen."}


# ── NACE helpers ─────────────────────────────────────────────────────────────

def _norm_nace(code: str) -> str:
    """Strip dots and spaces from a dotted NACE code → nace5.

    '56.101' → '56101'  |  '47.610' → '47610'  |  '56101' → '56101'
    Fallback to empty string if code is None/falsy.
    """
    return (code or "").replace(".", "").replace(" ", "")


def _nace2(code: str) -> str:
    """Return the 2-digit NACE prefix for starters/VAT tables."""
    n = _norm_nace(code)
    return n[:2] if len(n) >= 2 else n


def _nace4(code: str) -> str:
    """Return the 4-digit NACE prefix for bankruptcies table."""
    n = _norm_nace(code)
    return n[:4] if len(n) >= 4 else n


# ── LLM seam (monkeypatched in tests) ────────────────────────────────────────

async def complete_json(system: str, user: str) -> dict:
    """Single structured-JSON completion against the active provider."""
    provider = settings.AGENT_PROVIDER
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = await client.messages.create(
        model=settings.ANTHROPIC_MODEL, max_tokens=1024,
        system=system + "\n\nOutput JSON only — no prose, no markdown fences.",
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    return json.loads(text or "{}")


# ── YAML config loaders (config-file tools — NOT the gateway) ─────────────────

_CONFIG_ROOT = pathlib.Path(__file__).parent.parent.parent / "config"


@functools.lru_cache(maxsize=1)
def _load_permit_rules() -> list[dict]:
    """Load permit_rules_horeca.yml once; cached for the process lifetime."""
    return yaml.safe_load((_CONFIG_ROOT / "permit_rules_horeca.yml").read_text()) or []


@functools.lru_cache(maxsize=1)
def _load_subsidies() -> list[dict]:
    """Load subsidies.yml once; cached for the process lifetime."""
    with open(_CONFIG_ROOT / "subsidies.yml") as f:
        return yaml.safe_load(f) or []


# ── tool specs ────────────────────────────────────────────────────────────────

def tool_specs() -> list[dict]:
    return [
        {"name": "extract_dream_profile",
         "description": "Parse the founder's free-text dream into a structured profile. Chapter 1 only.",
         "input_schema": {"type": "object", "properties": {"text": {"type": "string"}},
                          "required": ["text"]}},
        {"name": "peer_benchmarks_statbel",
         "description": (
             "Sector-cohort numbers for a NACE code: active VAT count (Gent arrondissement), "
             "starters/stops trend and growth (Flanders nace2), bankruptcies (Belgium nace4). "
             "DataGateway → Postgres. refnis is echoed as metadata but NOT used in WHERE clauses "
             "(the source tables have no refnis column — VAT is scoped by source to Gent "
             "arrondissement; starters/stops/bankruptcies are Flanders/Belgium level)."
         ),
         "input_schema": {"type": "object", "properties": {
             "nace_code": {"type": "string"}, "refnis": {"type": "string", "default": "44021"},
             "years_back": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3}},
             "required": ["nace_code"]}},
        {"name": "places_search",
         "description": "Live competitor/niche venue search via Google Places. Returns a transient "
         "places- layer. Native behaviour tool.",
         "input_schema": {"type": "object", "properties": {
             "query": {"type": "string"},
             "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}},
             "required": ["query"]}},
        {"name": "score_locations",
         "description": (
             "Multi-axis scoring of Gent statistical sectors against a dream profile. "
             "Returns a transient score-locations- layer with a 'score' field. "
             "Each ranked item includes nis9_code (canonical NIS9 sector key) and sector_id "
             "(alias, same value) so rent_benchmark can be called directly with either. "
             "DataGateway → Postgres."
         ),
         "input_schema": {"type": "object", "properties": {
             "dream_profile": {"type": "object"}, "weights": {"type": "object"},
             "top_n": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}},
             "required": ["dream_profile"]}},
        {"name": "rent_benchmark",
         "description": (
             "Median residential SALE price (€ total, NOT €/m², NOT rent) for a statistical "
             "sector — SECTOR-LEVEL PROXY for location cost. "
             "Pass nis9_code from score_locations output (e.g. '44021A20K'). "
             "property_type defaults to 'Appartementen' (closest proxy for small premises). "
             "DataGateway → Postgres (droomzaak.housing_price_sector)."
         ),
         "input_schema": {"type": "object", "properties": {
             "nis9_code": {"type": "string"},
             "property_type": {"type": "string", "default": "Appartementen"}},
             "required": ["nis9_code"]}},
        {"name": "permit_checklist_for",
         "description": (
             "Sector-branched permit checklist for a NACE + address + attributes. "
             "Reads curated config/permit_rules_horeca.yml (config-file tool, NOT the gateway). "
             "attributes dict drives conditional rules (serves_alcohol, seating, music, etc.)."
         ),
         "input_schema": {"type": "object", "properties": {
             "nace_code": {"type": "string"}, "address": {"type": "string"},
             "attributes": {"type": "object"}}, "required": ["nace_code", "attributes"]}},
        {"name": "subsidies_for",
         "description": (
             "Eligibility-checked subsidy shortlist for a founder profile. "
             "Reads curated config/subsidies.yml (config-file tool, NOT the gateway). "
             "Cancelled schemes (status: ended_2025) appear in ineligible_with_reason."
         ),
         "input_schema": {"type": "object", "properties": {
             "dream_profile": {"type": "object"}, "chosen_location": {"type": "object"}},
             "required": ["dream_profile"]}},
        {"name": "legal_form_advisor",
         "description": "Recommends eenmanszaak vs BV/SRL. Pure Python decision tree.",
         "input_schema": {"type": "object", "properties": {
             "dream_profile": {"type": "object"}, "chosen_location": {"type": "object"}},
             "required": ["dream_profile"]}},
        {"name": "generate_dream_narrative",
         "description": "3-paragraph dream narrative + Tuesday-morning simulation card. Chapter 5.",
         "input_schema": {"type": "object", "properties": {"chapter_state": {"type": "object"}},
                          "required": ["chapter_state"]}},
        {"name": "compose_package",
         "description": "Serialise the chapter state into the renderer's input. Idempotent.",
         "input_schema": {"type": "object", "properties": {
             "chapter_state": {"type": "object"}, "session_id": {"type": "string"}},
             "required": ["chapter_state", "session_id"]}},
    ]


# ── handlers ──────────────────────────────────────────────────────────────────

_EXTRACT_GUIDE = (
    "You are extracting a structured profile from one founder's free-text dream in Ghent.\n"
    "Output JSON with keys: sector, sector_group (one of horeca, retail, consultant, crafts, "
    "e_commerce, other), nace_code (valid NACE-BEL, e.g. 56.101 restaurant, 56.102 frituur, "
    "56.301 café, 47.610 boekenwinkel), scale (small|medium|large), seats_guess (int|null), "
    "partners_guess (int|null), budget_eur_guess (int|null), vibe (single word), "
    "neighbourhood_anchor (real Gent district/landmark), founder_quote (verbatim), "
    "confidence (0..1). Leave ambiguous fields null; do NOT guess."
)


async def handle_extract_dream_profile(args: dict, run: AgentRun) -> dict:
    try:
        profile = await complete_json(_EXTRACT_GUIDE, args.get("text", ""))
    except Exception as exc:
        return {"error": f"profiel-extractie mislukt: {exc}"}
    profile.setdefault("founder_quote", args.get("text", ""))
    return profile


# ── peer_benchmarks_statbel ───────────────────────────────────────────────────

_SQL_VAT = """
SELECT SUM(n_vat)       AS active_count,
       SUM(n_vat_start) AS vat_starts,
       SUM(n_vat_stop)  AS vat_stops,
       $2::text         AS scope
FROM droomzaak.peer_vat_nace_empl_gentarr
WHERE nace5 = $1
""".strip()

_SQL_STARTERS = """
SELECT year,
       SUM(n_first_start) AS n_first_start,
       SUM(n_restart)     AS n_restart,
       SUM(n_stop)        AS n_stop,
       SUM(n_eop)         AS n_eop
FROM droomzaak.peer_starters_flanders
WHERE nace2 = $1 AND year >= $2
GROUP BY year
ORDER BY year DESC
""".strip()

_SQL_BANKRUPTCIES = """
SELECT year,
       SUM(n_bankruptcies) AS n_bankruptcies
FROM droomzaak.peer_bankruptcies
WHERE nace4 = $1 AND year >= $2
GROUP BY year
ORDER BY year DESC
""".strip()


async def handle_peer_benchmarks_statbel(args: dict, run: AgentRun) -> dict:
    nace_raw = args["nace_code"]
    refnis = args.get("refnis", "44021")
    years_back = int(args.get("years_back", 3))

    nace5 = _norm_nace(nace_raw)
    n4 = _nace4(nace_raw)
    n2 = _nace2(nace_raw)
    cutoff_year = _CURRENT_YEAR - years_back

    try:
        vat_rows = await gateway.query(
            _SQL_VAT, [nace5, "gent_arrondissement"],
            tool_name="peer_benchmarks_statbel",
        )
        starter_rows = await gateway.query(
            _SQL_STARTERS, [n2, cutoff_year],
            tool_name="peer_benchmarks_statbel",
        )
        bankrupt_rows = await gateway.query(
            _SQL_BANKRUPTCIES, [n4, cutoff_year],
            tool_name="peer_benchmarks_statbel",
        )
    except (DataGatewayUnavailable, Exception) as exc:
        if settings.DROOMZAAK_DEV_FABRICATE:
            return droomzaak_fabricate.peer_benchmarks(nace_raw, refnis)
        return _gw_error(exc)

    # ── active count (VAT, Gent arrondissement) ───────────────────────────
    active_count: int | None = None
    if vat_rows and vat_rows[0].get("active_count") is not None:
        active_count = int(vat_rows[0]["active_count"])

    # ── starters: most recent full year in window ─────────────────────────
    starters_recent: int | None = None
    stops_recent: int | None = None
    if starter_rows:
        r0 = starter_rows[0]
        starters_recent = int((r0.get("n_first_start") or 0) + (r0.get("n_restart") or 0))
        stops_recent = abs(int(r0.get("n_stop") or 0))

    # ── growth: n_eop change oldest→latest in window ──────────────────────
    growth_3y_pct: float | None = None
    if len(starter_rows) >= 2:
        latest_eop = starter_rows[0].get("n_eop") or 0
        oldest_eop = starter_rows[-1].get("n_eop") or 0
        if oldest_eop:
            growth_3y_pct = round((latest_eop - oldest_eop) / abs(oldest_eop) * 100, 1)

    # ── bankruptcies: most recent year in window ──────────────────────────
    bankruptcies_latest: int | None = None
    bankruptcies_latest_year: int | None = None
    if bankrupt_rows:
        bankruptcies_latest = int(bankrupt_rows[0].get("n_bankruptcies") or 0)
        bankruptcies_latest_year = int(bankrupt_rows[0].get("year") or 0)

    summary = {
        "active_count_latest": active_count,
        "growth_3y_pct": growth_3y_pct,
        "bankruptcies_latest": bankruptcies_latest,
        "bankruptcies_latest_year": bankruptcies_latest_year,
        "starters_recent": starters_recent,
        "stops_recent": stops_recent,
        # Geographic scope disclaimer — surfaces in agent reasoning
        "scope_note": (
            "VAT: Gent arrondissement (nace5); "
            f"starters/stops/growth: Vlaanderen (nace2 {n2}); "
            f"faillissementen: België (nace4 {n4})"
        ),
    }

    rows = {
        "vat": [dict(r) for r in vat_rows],
        "starters_by_year": [dict(r) for r in starter_rows],
        "bankruptcies_by_year": [dict(r) for r in bankrupt_rows],
    }

    return {"nace_code": nace_raw, "refnis": refnis, "rows": rows, "summary": summary}


# ── score_locations ───────────────────────────────────────────────────────────

_SQL_SCORE_LOCATIONS = """
WITH
demo AS (
    SELECT nis9_code,
           COALESCE(population,    0) AS population,
           COALESCE(median_income, 0) AS median_income
    FROM droomzaak.demographics_sector
),
transit AS (
    SELECT nis9_code,
           COALESCE(departures_total, 0) AS departures_total
    FROM droomzaak.transit_access_sector
),
housing AS (
    SELECT DISTINCT ON (nis9_code)
        nis9_code,
        median_price
    FROM droomzaak.housing_price_sector
    WHERE property_type IN (
        'Appartementen',
        'Alle huizen met 2, 3, 4 of meer gevels (excl. appartementen)'
    )
      AND median_price IS NOT NULL
    ORDER BY nis9_code, year DESC, median_price DESC NULLS LAST
),
competition AS (
    SELECT nis9_code, COUNT(*) AS comp_count
    FROM droomzaak.business_registry
    WHERE LEFT(nace5, 2) = $1
    GROUP BY nis9_code
),
disruption AS (
    SELECT nis9_code, COUNT(*) AS event_count
    FROM droomzaak.disruption_events
    GROUP BY nis9_code
)
SELECT
    g.nis9_code,
    g.sectornaam,
    w.wijk                                       AS wijk_nl,
    COALESCE(d.population,       0)::float       AS population,
    COALESCE(d.median_income,    0)::float       AS median_income,
    COALESCE(t.departures_total, 0)::float       AS departures_total,
    COALESCE(h.median_price,     0)::float       AS median_price_raw,
    COALESCE(c.comp_count,       0)::float       AS comp_count,
    COALESCE(dis.event_count,    0)::float       AS disruption_count
FROM droomzaak.geo_sectors       g
LEFT JOIN droomzaak.geo_wijken   w   ON w.wijknr      = g.wijknr
LEFT JOIN demo                   d   ON d.nis9_code   = g.nis9_code
LEFT JOIN transit                t   ON t.nis9_code   = g.nis9_code
LEFT JOIN housing                h   ON h.nis9_code   = g.nis9_code
LEFT JOIN competition            c   ON c.nis9_code   = g.nis9_code
LEFT JOIN disruption             dis ON dis.nis9_code = g.nis9_code
ORDER BY g.nis9_code
""".strip()


def _minmax(vals: list[float]) -> list[float]:
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span <= 0:
        return [0.0] * len(vals)
    return [(v - lo) / span for v in vals]


def _inv(scaled: list[float]) -> list[float]:
    return [1.0 - v for v in scaled]


async def handle_score_locations(args: dict, run: AgentRun) -> dict:
    dream_profile = args.get("dream_profile") or {}
    top_n = int(args.get("top_n", 5))

    # NACE2 for competition filter (broad: all NACE-56 = food service for bistro)
    nace_raw = (dream_profile.get("nace_code") or "").replace(".", "").replace(" ", "")
    nace2 = nace_raw[:2] if len(nace_raw) >= 2 else "56"

    # Caller-supplied weight overrides (vacancy_score accepted but produces 0 — no source)
    weights = {"demographic_match": 1.0, "competition_density": 0.7,
               "transit_score": 0.6, "rent_score": 0.4, "disruption_penalty": 0.5}
    weights.update(args.get("weights") or {})
    total_w = sum(weights.values())

    try:
        all_rows = await gateway.query(
            _SQL_SCORE_LOCATIONS, [nace2], tool_name="score_locations"
        )
    except (DataGatewayUnavailable, Exception) as exc:
        if settings.DROOMZAAK_DEV_FABRICATE:
            fab = droomzaak_fabricate.score_locations(weights, top_n)
            run.datasets[fab["dataset_id"]] = {
                "dataset_id": fab["dataset_id"],
                "feature_count": len(fab["ranked"]),
                "ranked": fab["ranked"],
            }
            return fab
        return _gw_error(exc)

    if not all_rows:
        return {"error": "score_locations: geen sectordata beschikbaar",
                "hint": "Controleer de warehouse-verbinding."}

    # ── min-max scale each dimension ──────────────────────────────────────
    populations  = [float(r["population"])        for r in all_rows]
    incomes      = [float(r["median_income"])      for r in all_rows]
    departures   = [float(r["departures_total"])   for r in all_rows]
    rent_vals    = [float(r["median_price_raw"])   for r in all_rows]
    competition  = [float(r["comp_count"])         for r in all_rows]
    disruption   = [float(r["disruption_count"])   for r in all_rows]

    pop_sc   = _minmax(populations)
    inc_sc   = _minmax(incomes)
    demo_sc  = [0.5 * p + 0.5 * i for p, i in zip(pop_sc, inc_sc)]
    trs_sc   = _minmax(departures)
    ren_sc   = _inv(_minmax(rent_vals))   # higher price → lower score
    cmp_sc   = _inv(_minmax(competition)) # more competition → lower score
    dis_sc   = _inv(_minmax(disruption))  # more disruption → lower score

    scored = []
    for i, r in enumerate(all_rows):
        raw = (weights["demographic_match"]   * demo_sc[i]
             + weights["transit_score"]       * trs_sc[i]
             + weights["competition_density"] * cmp_sc[i]
             + weights["rent_score"]          * ren_sc[i]
             + weights["disruption_penalty"]  * dis_sc[i])
        nis9 = r["nis9_code"]
        scored.append({
            "nis9_code":      nis9,
            "sector_id":      nis9,   # alias — backward compat with fabricate shape
            "sector_name_nl": (r.get("sectornaam") or nis9).title(),
            "wijk_nl":        r.get("wijk_nl") or "",
            "score":          round(raw / total_w, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    ranked = scored[:top_n]
    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    dataset_id = f"score-locations-{_hash(args.get('dream_profile'))}"
    run.datasets[dataset_id] = {
        "dataset_id": dataset_id,
        "feature_count": len(ranked),
        "ranked": ranked,
    }
    return {
        "dataset_id": dataset_id,
        "ranked": ranked,
        "formula_label_nl": (
            "Demografische match + transit − concurrentie − huurproxy − verstoring "
            "(min-max genormaliseerd per sector; leegstand weggevallen — geen bron)"
        ),
    }


# ── rent_benchmark ────────────────────────────────────────────────────────────

_SQL_RENT_BENCHMARK = """
WITH target AS (
    SELECT nis9_code, property_type, year, n_transactions,
           median_price, p25_price, p75_price
    FROM droomzaak.housing_price_sector
    WHERE nis9_code = $1
      AND property_type = $2
      AND median_price IS NOT NULL
    ORDER BY year DESC LIMIT 1
), fallback AS (
    SELECT nis9_code, property_type, year, n_transactions,
           median_price, p25_price, p75_price
    FROM droomzaak.housing_price_sector
    WHERE nis9_code = $1
      AND median_price IS NOT NULL
    ORDER BY year DESC, n_transactions DESC NULLS LAST LIMIT 1
)
SELECT *, 'target'   AS match_level FROM target
UNION ALL
SELECT *, 'fallback' AS match_level FROM fallback
LIMIT 1
""".strip()


async def handle_rent_benchmark(args: dict, run: AgentRun) -> dict:
    nis9_code = args.get("nis9_code") or args.get("sector_id")  # accept old key too
    if not nis9_code:
        return {"error": "rent_benchmark: nis9_code ontbreekt",
                "hint": "Geef het nis9_code veld mee uit de score_locations output."}
    property_type = args.get("property_type", "Appartementen")

    try:
        rows = await gateway.query(
            _SQL_RENT_BENCHMARK, [nis9_code, property_type],
            tool_name="rent_benchmark",
        )
    except (DataGatewayUnavailable, Exception) as exc:
        if settings.DROOMZAAK_DEV_FABRICATE:
            return droomzaak_fabricate.rent_benchmark(nis9_code, property_type)
        return _gw_error(exc)

    if not rows:
        return {
            "error": "geen huur-proxy voor deze sector",
            "hint": "Weinig transacties in deze sector; verwijs naar Immoweb/Realo voor actuele prijzen.",
            "nis9_code": nis9_code,
            "data_available": False,
        }

    row = rows[0]
    median = round(row.get("median_price") or 0, -3)
    p25    = round(row.get("p25_price")    or 0, -3)
    p75    = round(row.get("p75_price")    or 0, -3)
    iqr    = round(p75 - p25, -3) if p25 and p75 else None
    n_tx   = int(row.get("n_transactions") or 0)
    year   = int(row.get("year") or 0)
    match_level = row.get("match_level", "target")
    prop_used = ("Appartementen" if match_level == "target"
                 else (row.get("property_type") or property_type))
    low_sample = n_tx < 5

    return {
        "nis9_code":          nis9_code,
        "property_type_used": prop_used,
        "match_level":        match_level,
        "year":               year,
        "n_transactions":     n_tx,
        "median_sale_eur":    int(median),
        "p25_sale_eur":       int(p25),
        "p75_sale_eur":       int(p75),
        "iqr_eur":            int(iqr) if iqr is not None else None,
        "low_sample_warning": low_sample,
        "data_available":     True,
        "label_nl":           f"Mediane verkoopprijs {prop_used} ({year}, sector proxy)",
        "proxy_caveat_nl": (
            "Dit zijn RESIDENTIËLE verkoopprijzen (€ totaal, NIET €/m², NIET huurprijs). "
            "Gebruikt als locatiekostproxy — geen commercieel vastgoedcijfer."
        ),
    }


# ── permit_checklist_for (YAML-loader — NOT the gateway) ─────────────────────

def _nace3_prefix(dotted: str) -> str:
    """'56.101' → '561'  |  '47.610' → '476'"""
    return _norm_nace(dotted)[:3]


def _rule_matches(rule: dict, nace_prefix: str, attributes: dict) -> bool:
    """Return True iff the rule's nace_code prefix matches AND all attribute filters pass."""
    rule_prefix = _norm_nace(rule.get("nace_code", ""))[:3]
    if rule_prefix != nace_prefix:
        return False
    flt = rule.get("attribute_filter") or {}
    return all(attributes.get(k) == v for k, v in flt.items())


async def handle_permit_checklist_for(args: dict, run: AgentRun) -> dict:
    nace = args["nace_code"]
    attributes = args.get("attributes", {}) or {}
    address = args.get("address")

    try:
        rules = _load_permit_rules()
    except FileNotFoundError:
        return {"error": "permit_rules config ontbreekt",
                "hint": "Neem contact op met het technisch team."}
    except Exception as exc:
        return {"error": f"permit_rules laad-fout: {exc}",
                "hint": "Neem contact op met het technisch team."}

    prefix = _nace3_prefix(nace)
    checklist = []
    for rule in rules:
        if _rule_matches(rule, prefix, attributes):
            checklist.append({k: rule.get(k) for k in (
                "rule_id", "permit_name", "authority", "deep_link",
                "estimated_cost_eur", "estimated_processing_days", "notes_nl")})

    total = round(sum(c.get("estimated_cost_eur") or 0 for c in checklist), 2)
    longest = max((c.get("estimated_processing_days") or 0 for c in checklist), default=0)

    uncertain: list[str] = []
    if not any(attributes.values()):
        uncertain.append(
            "Attributen zijn schaars ingevuld — bevestig specifieke vereisten bij Stad Gent / FAVV."
        )
    if not checklist:
        uncertain.append(
            f"Geen vergunningsregels gevonden voor NACE-prefix '{prefix}'. "
            "Raadpleeg Stad Gent OOG voor sector-specifieke vergunningen."
        )

    return {
        "nace_code":               nace,
        "address":                 address,
        "checklist":               checklist,
        "total_estimated_cost_eur": total,
        "longest_path_days":       longest,
        "uncertain_areas_nl":      uncertain,
    }


# ── subsidies_for (YAML-loader — NOT the gateway) ────────────────────────────

def _subsidy_eligible(flt: dict, profile: dict) -> bool:
    sg = flt.get("sector_group")
    if sg and sg not in ("any", profile.get("sector_group")):
        return False
    budget_max = flt.get("budget_eur_max")
    if budget_max and (profile.get("budget_eur_guess") or 0) > budget_max:
        return False
    return True


async def handle_subsidies_for(args: dict, run: AgentRun) -> dict:
    profile = args.get("dream_profile", {}) or {}

    try:
        entries = _load_subsidies()
    except Exception as exc:
        return {
            "error": f"subsidies config niet beschikbaar: {exc}",
            "hint": "Neem contact op met Stad Gent / VLAIO voor de actuele lijst.",
        }

    shortlist: list[dict] = []
    ineligible: list[dict] = []

    for entry in entries:
        flt = entry.get("eligibility_filter") or {}
        # flt is already a dict from yaml.safe_load — no json.loads needed
        status = entry.get("status", "active")
        eligible = _subsidy_eligible(flt, profile)
        item = {k: entry.get(k) for k in (
            "subsidy_id", "name", "authority", "max_amount_eur",
            "deep_link", "description_nl", "estimated_processing_days", "status")}
        if eligible and status == "active":
            shortlist.append({
                **item,
                "eligible": True,
                "why_eligible_nl": "Past bij je profiel en startfase.",
            })
        else:
            reason = (
                f"Beëindigd voor 2026 (status: {status})."
                if status != "active"
                else "Profiel komt niet in aanmerking."
            )
            ineligible.append({"name": entry.get("name", ""), "reason_nl": reason})

    return {"shortlist": shortlist, "ineligible_with_reason": ineligible}


# ── legal_form_advisor ────────────────────────────────────────────────────────

async def handle_legal_form_advisor(args: dict, run: AgentRun) -> dict:
    p = args.get("dream_profile", {}) or {}
    has_partners = (p.get("partners_guess") or 0) > 0
    has_premise = bool(args.get("chosen_location"))
    revenue = _estimate_revenue_eur(p)
    if has_partners:
        rec = "BV/SRL"
        rationale = "Met partners is een BV/SRL administratief eenvoudiger en beschermt het privévermogen."
    elif has_premise and revenue > 200000:
        rec = "BV/SRL"
        rationale = (f"Bij een fysiek pand en geschatte omzet ~€{revenue // 1000}k beschermt een "
                     "BV/SRL je privévermogen. ~€1.500 notariskosten bij oprichting.")
    else:
        rec = "Eenmanszaak"
        rationale = ("Een eenmanszaak is administratief het lichtst en past bij een klein startbudget. "
                     "Geen privévermogen-bescherming — overweeg later te schakelen naar BV/SRL.")
    return {"recommended": rec, "alternative": "BV/SRL" if rec == "Eenmanszaak" else "Eenmanszaak",
            "rationale_nl": rationale,
            "estimated_setup_cost_eur": 90 if rec == "Eenmanszaak" else 1500,
            "notes_nl": "We zetten beide opties in het pakket; de aanbeveling staat bovenaan."}


def _estimate_revenue_eur(p: dict) -> int:
    seats = p.get("seats_guess") or 0
    if seats:
        return int(seats * 15000)  # cheap horeca heuristic
    return {"small": 120000, "medium": 300000, "large": 600000}.get(p.get("scale"), 120000)


# ── generate_dream_narrative ──────────────────────────────────────────────────

_NARRATIVE_GUIDE = (
    "You are writing a 3-paragraph dream narrative + a 1-paragraph Tuesday-morning simulation "
    "for a Droomzaak package. THIRD-PERSON REPORTAGE ('Lisa is 32 en droomt van...'), NOT "
    "second-person. Concrete, grounded in the founder's own words. No aspirational AI prose, no "
    "emoji, no exclamation marks past the first sentence. Round revenue down, costs up. "
    "~80-120 words narrative, ~50-80 words Tuesday. Output JSON: "
    '{"dream_narrative_nl": "...", "tuesday_morning_nl": "..."}.'
)


async def handle_generate_dream_narrative(args: dict, run: AgentRun) -> dict:
    state = args.get("chapter_state", {})
    try:
        out = await complete_json(_NARRATIVE_GUIDE, json.dumps(state, ensure_ascii=False))
    except Exception as exc:
        return {"error": f"narratief mislukt: {exc}"}
    return {"dream_narrative_nl": out.get("dream_narrative_nl", ""),
            "tuesday_morning_nl": out.get("tuesday_morning_nl", "")}


# ── compose_package ───────────────────────────────────────────────────────────

async def handle_compose_package(args: dict, run: AgentRun) -> dict:
    # Prefer the server-known state/session over whatever the model passes: the
    # model is never told the real session_id, and the full chapter_state already
    # lives on the run. Falling back to args keeps the tool callable in isolation.
    state = args.get("chapter_state") or run.current_chapter_state or {}
    session_id = run.session_id or args.get("session_id")
    if not session_id:
        return {"error": "compose_package: geen session_id beschikbaar",
                "hint": "Dit is een serverfout; de sessie wordt normaal automatisch meegegeven."}
    package = {
        "session_id": session_id,
        "generated_at": _dt.date.today().isoformat(),
        "dream_profile": state.get("dream_profile"),
        "niche_signals": state.get("niche_signals"),
        "chosen_location": state.get("chosen_location"),
        "candidate_locations": state.get("candidate_locations"),
        "permit_checklist": state.get("permit_checklist"),
        "subsidies": state.get("subsidies"),
        "legal_form": state.get("legal_form"),
        "dream_narrative": state.get("dream_narrative"),
        "tuesday_morning": state.get("tuesday_morning"),
    }
    if run.store is not None:
        run.store.save_package(session_id, package)
    return {"package_url": f"/pakket/{session_id}", "ready": True}


# ── places_search ─────────────────────────────────────────────────────────────

async def handle_places_search(args: dict, run: AgentRun) -> dict:
    query = args.get("query", "")
    if not settings.GOOGLE_MAPS_API_KEY:
        return {"error": "places_search niet beschikbaar (geen GOOGLE_MAPS_API_KEY)",
                "hint": "Gebruik query_osm voor niche-/concurrentiepunten."}
    import httpx

    body = {"textQuery": f"{query} in Gent, België", "maxResultCount": 20}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://places.googleapis.com/v1/places:searchText", json=body,
                headers={"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                         "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,"
                         "places.location,places.rating,places.userRatingCount,places.types"})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        return {"error": f"places_search failed: {exc}", "hint": "Gebruik query_osm als fallback."}
    places, features = [], []
    for p in data.get("places", []):
        loc = p.get("location", {})
        coords = [loc.get("longitude"), loc.get("latitude")]
        places.append({"place_id": p.get("id"), "name": (p.get("displayName") or {}).get("text"),
                       "address": p.get("formattedAddress"), "rating": p.get("rating"),
                       "user_ratings_total": p.get("userRatingCount"), "coordinates": coords,
                       "types": p.get("types", [])})
        if coords[0] is not None:
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": coords},
                             "properties": {"name": (p.get("displayName") or {}).get("text")}})
    dataset_id = f"places-{_hash(query)}"
    run.datasets[dataset_id] = {"dataset_id": dataset_id, "feature_count": len(features),
                                "geojson": {"type": "FeatureCollection", "features": features}}
    return {"dataset_id": dataset_id, "places": places}


# ── dispatch table ────────────────────────────────────────────────────────────

HANDLERS = {
    "extract_dream_profile":    handle_extract_dream_profile,
    "peer_benchmarks_statbel":  handle_peer_benchmarks_statbel,
    "places_search":            handle_places_search,
    "score_locations":          handle_score_locations,
    "rent_benchmark":           handle_rent_benchmark,
    "permit_checklist_for":     handle_permit_checklist_for,
    "subsidies_for":            handle_subsidies_for,
    "legal_form_advisor":       handle_legal_form_advisor,
    "generate_dream_narrative": handle_generate_dream_narrative,
    "compose_package":          handle_compose_package,
}
