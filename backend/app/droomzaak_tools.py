"""The 11 Droomzaak tools.

- Analytical tools (peer_benchmarks_statbel, score_locations, rent_benchmark,
  permit_checklist_for, subsidies_for) are thin wrappers around `gateway.query`.
  They return the {error, hint} envelope when the gateway is unavailable.
- legal_form_advisor + compose_package are pure Python.
- extract_dream_profile + generate_dream_narrative are LLM-backed via complete_json
  (monkeypatched in tests).
set_chapter_state is NOT here — it is an action committed through apply_map_actions.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any

from backend.app import settings
from backend.app.agent_loop import AgentRun
from backend.app.data_gateway import DataGatewayUnavailable, gateway

_CURRENT_YEAR = 2024  # snapshot-frozen demo vintage


def _hash(*parts: Any) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


def _gw_error(exc: Exception) -> dict:
    return {"error": f"data unavailable: {exc}",
            "hint": "Probeer het zo opnieuw, of roep report_problem aan als het blijft falen."}


# ── LLM seam (monkeypatched in tests) ───────────────────────────────────
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


# ── tool specs ──────────────────────────────────────────────────────────
def tool_specs() -> list[dict]:
    return [
        {"name": "extract_dream_profile",
         "description": "Parse the founder's free-text dream into a structured profile. Chapter 1 only.",
         "input_schema": {"type": "object", "properties": {"text": {"type": "string"}},
                          "required": ["text"]}},
        {"name": "peer_benchmarks_statbel",
         "description": "Sector-cohort numbers for a NACE code in a municipality (openings, "
         "closings, bankruptcies, active count). DataGateway → Postgres.",
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
         "description": "Multi-axis scoring of Gent statistical sectors against a dream profile. "
         "Returns a transient score-locations- layer with a 'score' field. DataGateway → Postgres.",
         "input_schema": {"type": "object", "properties": {
             "dream_profile": {"type": "object"}, "weights": {"type": "object"},
             "top_n": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}},
             "required": ["dream_profile"]}},
        {"name": "rent_benchmark",
         "description": "Median commercial rent per m² for a sector — SECTOR-LEVEL PROXY (sale-€), "
         "NOT per address. DataGateway → Postgres.",
         "input_schema": {"type": "object", "properties": {
             "sector_id": {"type": "string"},
             "asset_type": {"type": "string", "enum": ["commercial", "mixed"], "default": "commercial"}},
             "required": ["sector_id"]}},
        {"name": "permit_checklist_for",
         "description": "Sector-branched permit checklist for a NACE + address + attributes. "
         "DataGateway → Postgres rules engine.",
         "input_schema": {"type": "object", "properties": {
             "nace_code": {"type": "string"}, "address": {"type": "string"},
             "attributes": {"type": "object"}}, "required": ["nace_code", "attributes"]}},
        {"name": "subsidies_for",
         "description": "Eligibility-checked subsidy shortlist for a founder profile.",
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


# ── handlers ─────────────────────────────────────────────────────────────
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


async def handle_peer_benchmarks_statbel(args: dict, run: AgentRun) -> dict:
    nace = args["nace_code"]
    refnis = args.get("refnis", "44021")
    years_back = int(args.get("years_back", 3))
    sql = (
        "SELECT year, openings, closings, bankruptcies, active_count, btw_evolution "
        "FROM droomzaak.peer_demography_nace "
        "WHERE nace_code = $1 AND refnis = $2 AND year >= $3 ORDER BY year DESC"
    )
    try:
        rows = await gateway.query(sql, [nace, refnis, _CURRENT_YEAR - years_back],
                                   tool_name="peer_benchmarks_statbel")
    except (DataGatewayUnavailable, Exception) as exc:
        return _gw_error(exc)
    summary = _summarize_cohort(rows)
    return {"nace_code": nace, "refnis": refnis, "rows": rows, "summary": summary}


def _summarize_cohort(rows: list[dict]) -> dict:
    if not rows:
        return {"active_count_latest": 0, "growth_3y_pct": None, "bankruptcies_latest": None}
    ordered = sorted(rows, key=lambda r: r["year"])
    latest, oldest = ordered[-1], ordered[0]
    growth = None
    if oldest.get("active_count"):
        growth = round((latest["active_count"] - oldest["active_count"]) / oldest["active_count"] * 100, 1)
    return {"active_count_latest": latest.get("active_count"),
            "growth_3y_pct": growth, "bankruptcies_latest": latest.get("bankruptcies")}


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


async def handle_score_locations(args: dict, run: AgentRun) -> dict:
    weights = {"demographic_match": 1.0, "competition_density": 0.7, "vacancy_score": 0.8,
               "transit_score": 0.6, "rent_score": 0.4, "disruption_penalty": 0.5}
    weights.update(args.get("weights") or {})
    top_n = int(args.get("top_n", 5))
    sql = (
        "SELECT sector_id, sector_name_nl, wijk_nl, demographic_match, competition_density, "
        "vacancy_score, transit_score, rent_score, disruption_penalty "
        "FROM droomzaak.sector_scores"
    )
    try:
        rows = await gateway.query(sql, [], tool_name="score_locations")
    except (DataGatewayUnavailable, Exception) as exc:
        return _gw_error(exc)
    ranked = []
    for r in rows:
        score = (
            weights["demographic_match"] * (r.get("demographic_match") or 0)
            + weights["vacancy_score"] * (r.get("vacancy_score") or 0)
            + weights["transit_score"] * (r.get("transit_score") or 0)
            - weights["competition_density"] * (r.get("competition_density") or 0)
            - weights["rent_score"] * (r.get("rent_score") or 0)
            - weights["disruption_penalty"] * (r.get("disruption_penalty") or 0)
        )
        ranked.append({**r, "score": round(score, 3)})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    ranked = ranked[:top_n]
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    dataset_id = f"score-locations-{_hash(args.get('dream_profile'))}"
    run.datasets[dataset_id] = {"dataset_id": dataset_id, "feature_count": len(ranked),
                                "ranked": ranked}
    return {"dataset_id": dataset_id, "ranked": ranked,
            "formula_label_nl": "Demografische match + leegstand + transit − concurrentie − huur − verstoring"}


async def handle_rent_benchmark(args: dict, run: AgentRun) -> dict:
    sector_id = args["sector_id"]
    asset_type = args.get("asset_type", "commercial")
    sql = ("SELECT median_eur_per_m2, p25_eur_per_m2, p75_eur_per_m2, sample_n, year "
           "FROM droomzaak.housing_price_sector WHERE sector_id = $1 AND asset_type = $2 "
           "ORDER BY year DESC LIMIT 1")
    try:
        rows = await gateway.query(sql, [sector_id, asset_type], tool_name="rent_benchmark")
    except (DataGatewayUnavailable, Exception) as exc:
        return _gw_error(exc)
    if not rows:
        return {"error": "geen huur-proxy voor deze sector",
                "hint": "Meld dit als gap; verwijs naar Immoweb/Realo voor actuele prijzen."}
    row = rows[0]
    return {"sector_id": sector_id, "asset_type": asset_type, **row,
            "label_nl": "proxy o.b.v. verkoopprijzen per sector — geen huurquote per adres"}


async def handle_permit_checklist_for(args: dict, run: AgentRun) -> dict:
    nace = args["nace_code"]
    attributes = args.get("attributes", {}) or {}
    sql = ("SELECT rule_id, attribute_filter, permit_name, authority, deep_link, "
           "estimated_cost_eur, estimated_processing_days, notes_nl "
           "FROM droomzaak.permit_rules WHERE nace_code = $1")
    try:
        rows = await gateway.query(sql, [nace], tool_name="permit_checklist_for")
    except (DataGatewayUnavailable, Exception) as exc:
        return _gw_error(exc)
    checklist = []
    for r in rows:
        flt = r.get("attribute_filter") or {}
        if isinstance(flt, str):
            flt = json.loads(flt)
        if all(attributes.get(k) == v for k, v in flt.items()):
            checklist.append({k: r[k] for k in (
                "rule_id", "permit_name", "authority", "deep_link",
                "estimated_cost_eur", "estimated_processing_days", "notes_nl")})
    total = sum(c.get("estimated_cost_eur") or 0 for c in checklist)
    longest = max((c.get("estimated_processing_days") or 0 for c in checklist), default=0)
    uncertain = []
    if not any(attributes.values()):
        uncertain.append("Attributen zijn schaars ingevuld — bevestig specifieke vereisten bij Stad Gent / FAVV.")
    return {"nace_code": nace, "address": args.get("address"), "checklist": checklist,
            "total_estimated_cost_eur": total, "longest_path_days": longest,
            "uncertain_areas_nl": uncertain}


async def handle_subsidies_for(args: dict, run: AgentRun) -> dict:
    profile = args.get("dream_profile", {}) or {}
    sql = ("SELECT subsidy_id, name, authority, max_amount_eur, eligibility_filter, "
           "deep_link, description_nl, estimated_processing_days, status "
           "FROM droomzaak.subsidies")
    try:
        rows = await gateway.query(sql, [], tool_name="subsidies_for")
    except (DataGatewayUnavailable, Exception) as exc:
        return _gw_error(exc)
    shortlist, ineligible = [], []
    for r in rows:
        flt = r.get("eligibility_filter") or {}
        if isinstance(flt, str):
            flt = json.loads(flt)
        eligible = _subsidy_eligible(flt, profile)
        item = {k: r[k] for k in ("subsidy_id", "name", "authority", "max_amount_eur",
                                  "deep_link", "description_nl", "estimated_processing_days", "status")}
        if eligible and r.get("status", "active") == "active":
            shortlist.append({**item, "eligible": True,
                              "why_eligible_nl": "Past bij je profiel en startfase."})
        else:
            reason = "Beëindigd voor 2026." if r.get("status") != "active" else "Profiel komt niet in aanmerking."
            ineligible.append({"name": r["name"], "reason_nl": reason})
    return {"shortlist": shortlist, "ineligible_with_reason": ineligible}


def _subsidy_eligible(flt: dict, profile: dict) -> bool:
    sg = flt.get("sector_group")
    if sg and sg not in ("any", profile.get("sector_group")):
        return False
    budget_max = flt.get("budget_eur_max")
    if budget_max and (profile.get("budget_eur_guess") or 0) > budget_max:
        return False
    return True


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


async def handle_compose_package(args: dict, run: AgentRun) -> dict:
    state = args.get("chapter_state", {})
    session_id = args["session_id"]
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


HANDLERS = {
    "extract_dream_profile": handle_extract_dream_profile,
    "peer_benchmarks_statbel": handle_peer_benchmarks_statbel,
    "places_search": handle_places_search,
    "score_locations": handle_score_locations,
    "rent_benchmark": handle_rent_benchmark,
    "permit_checklist_for": handle_permit_checklist_for,
    "subsidies_for": handle_subsidies_for,
    "legal_form_advisor": handle_legal_form_advisor,
    "generate_dream_narrative": handle_generate_dream_narrative,
    "compose_package": handle_compose_package,
}
