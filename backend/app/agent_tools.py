"""Base behaviour tools — native, NOT routed through the DataGateway.

apply_map_actions (the one COMMIT tool), report_problem, and the live enrichment
tools query_osm / geocode / web_search. Handlers are async and take (args, run).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from backend.app import agent_validation, settings
from backend.app.agent_loop import AgentRun

_GHENT_BBOX = (3.66, 50.98, 3.83, 51.12)  # minlon, minlat, maxlon, maxlat


def _hash(*parts: Any) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


# ── specs ──────────────────────────────────────────────────────────────
SPEC_APPLY_MAP_ACTIONS = {
    "name": "apply_map_actions",
    "description": "Commit the turn: emit the user-facing reply and the list of map/state "
    "actions. Exactly one call per turn. actions=[] is valid.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "actions": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["reply", "actions"],
    },
}

SPEC_REPORT_PROBLEM = {
    "name": "report_problem",
    "description": "Log friction this turn (not user-visible). Call before apply_map_actions "
    "when anything was hard, partial, or a config gap.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "enum": [
                "ambiguous", "no_good_dataset", "filter_kept_retrying", "tool_error", "other"]},
            "what_was_missing": {"type": "string"},
            "attempted_steps": {"type": "string"},
            "suggested_fix": {"type": "string"},
        },
        "required": ["reason", "what_was_missing"],
    },
}

SPEC_QUERY_OSM = {
    "name": "query_osm",
    "description": "Overpass query for ambient amenities around Ghent (cafes, shops, etc.). "
    "tags = array of {key, value?}. Returns a transient osm- layer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array", "minItems": 1, "maxItems": 5,
                "items": {"type": "object", "properties": {
                    "key": {"type": "string"}, "value": {"type": "string"}},
                    "required": ["key"]},
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 120},
        },
        "required": ["tags"],
    },
}

SPEC_GEOCODE = {
    "name": "geocode",
    "description": "Address or place name in Ghent → [lon, lat].",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}

SPEC_WEB_SEARCH = {
    "name": "web_search",
    "description": "Official-domain-biased web search (Tavily) for off-script questions about "
    "Ghent permits/subsidies. Surfaces links; never acts. Fallback, not primary.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 4}},
        "required": ["query"],
    },
}

SPEC_ISOCHRONE = {
    "name": "isochrone",
    "description": "Compute a reachability polygon (isochrone) around a point in Ghent via "
    "OpenRouteService. Returns a transient GeoJSON layer the model can show_layer. "
    "Use in Chapter 3 to visualise a candidate location's walking/cycling reach.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
                "description": "[longitude, latitude] of the origin point.",
            },
            "minutes": {
                "type": "number",
                "default": 10,
                "description": "Travel-time budget in minutes (converted to seconds for ORS).",
            },
            "profile": {
                "type": "string",
                "enum": ["foot-walking", "cycling-regular", "driving-car"],
                "default": "foot-walking",
                "description": "ORS routing profile.",
            },
        },
        "required": ["location"],
    },
}


def tool_specs() -> list[dict]:
    return [
        SPEC_APPLY_MAP_ACTIONS,
        SPEC_REPORT_PROBLEM,
        SPEC_QUERY_OSM,
        SPEC_GEOCODE,
        SPEC_WEB_SEARCH,
        SPEC_ISOCHRONE,
    ]


# ── handlers ─────────────────────────────────────────────────────────────
async def handle_apply_map_actions(args: dict, run: AgentRun) -> dict:
    reply = args.get("reply", "")
    actions = args.get("actions", []) or []
    active_layers = (run.frontend_context or {}).get("active_layers", [])
    candidate_map = {**run.datasets, **{lid: {} for lid in active_layers}}
    normalized, errors = agent_validation.validate_actions(
        actions, candidate_map, current_chapter_state=run.current_chapter_state
    )
    if errors:
        return {"applied": False, "errors": errors}
    run.pending_reply = reply
    run.pending_actions = normalized
    return {"applied": True, "normalized_actions": normalized}


async def handle_report_problem(args: dict, run: AgentRun) -> dict:
    run.pending_problem_report = {
        "reason": args.get("reason", "other"),
        "what_was_missing": args.get("what_was_missing", ""),
        "attempted_steps": args.get("attempted_steps"),
        "suggested_fix": args.get("suggested_fix"),
    }
    return {"logged": True}


async def handle_query_osm(args: dict, run: AgentRun) -> dict:
    tags = args.get("tags", [])
    limit = int(args.get("limit", 120))
    minlon, minlat, maxlon, maxlat = _GHENT_BBOX
    selectors = "".join(
        f'["{t["key"]}"="{t["value"]}"]' if t.get("value") else f'["{t["key"]}"]'
        for t in tags
    )
    bbox = f"{minlat},{minlon},{maxlat},{maxlon}"
    # Match map-pilot-v2's working request shape: raw QL body as text/plain with a
    # User-Agent. Overpass returns 406 to form-encoded / no-User-Agent clients.
    # Union node+way+relation so POIs mapped as buildings (ways) are not missed.
    selector_union = "".join(f"{et}{selectors}({bbox});" for et in ("node", "way", "relation"))
    q = f"[out:json][timeout:25];({selector_union});out center {limit};"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.OVERPASS_API_URL,
                content=q.encode("utf-8"),
                headers={
                    "Content-Type": "text/plain; charset=utf-8",
                    "User-Agent": "droomzaak/0.1 (Hackers & Ravers hackathon)",
                },
            )
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
    except Exception as exc:
        return {"error": f"OSM query failed: {exc}", "hint": "Probeer andere tags of ga door met andere data."}

    features = []
    for el in elements[:limit]:
        lon, lat = el.get("lon"), el.get("lat")
        if lon is None and "center" in el:
            lon, lat = el["center"]["lon"], el["center"]["lat"]
        if lon is None:
            continue
        name = (el.get("tags") or {}).get("name", "")
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": {"name": name, **(el.get("tags") or {})}})
    dataset_id = f"osm-{tags[0]['key']}-{_hash(tags, bbox)}"
    run.datasets[dataset_id] = {
        "dataset_id": dataset_id, "feature_count": len(features),
        "geojson": {"type": "FeatureCollection", "features": features},
    }
    return {"dataset_id": dataset_id, "feature_count": len(features),
            "sample_records": [f["properties"].get("name") for f in features[:8]]}


async def handle_geocode(args: dict, run: AgentRun) -> dict:
    query = args.get("query", "")
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "droomzaak/0.1"}) as client:
            resp = await client.get(settings.NOMINATIM_URL, params={
                "q": f"{query}, Gent, België", "format": "json", "limit": 1})
            resp.raise_for_status()
            results = resp.json()
    except Exception as exc:
        return {"error": f"geocode failed: {exc}"}
    if not results:
        return {"error": "geen resultaat", "hint": "Probeer een specifieker adres."}
    top = results[0]
    return {"coordinates": [float(top["lon"]), float(top["lat"])],
            "label": top.get("display_name", query), "confidence": 0.7}


async def handle_web_search(args: dict, run: AgentRun) -> dict:
    if not settings.TAVILY_API_KEY:
        return {"error": "web_search niet beschikbaar (geen TAVILY_API_KEY)",
                "hint": "Verwijs de gebruiker naar de officiële bron (stad.gent / FAVV / VLAIO)."}
    query = args.get("query", "")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.tavily.com/search", json={
                "api_key": settings.TAVILY_API_KEY, "query": query,
                "max_results": int(args.get("max_results", 4)),
                "include_domains": ["stad.gent", "favv-afsca.be", "vlaanderen.be",
                                    "vlaio.be", "pmv.eu", "unisono.be", "economie.fgov.be"]})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        return {"error": f"web_search failed: {exc}"}
    return {"results": [{"title": r.get("title"), "url": r.get("url"),
                         "snippet": r.get("content", "")[:300]} for r in data.get("results", [])]}


async def handle_isochrone(args: dict, run: AgentRun) -> dict:
    location = args.get("location")
    if not location or len(location) != 2:
        return {"error": "location must be [lon, lat]", "hint": "Geef een geldige [lon, lat] op."}

    minutes = float(args.get("minutes", 10))
    profile = args.get("profile", "foot-walking")
    seconds = int(minutes * 60)

    if not settings.OPENROUTESERVICE_API_KEY:
        return {
            "error": "isochrone niet beschikbaar (geen OPENROUTESERVICE_API_KEY)",
            "hint": "Voeg OPENROUTESERVICE_API_KEY toe aan .env.demo en herstart de server.",
        }

    ors_url = f"https://api.openrouteservice.org/v2/isochrones/{profile}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                ors_url,
                headers={
                    "Authorization": settings.OPENROUTESERVICE_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"locations": [location], "range": [seconds]},
            )
            resp.raise_for_status()
            geojson = resp.json()
    except Exception as exc:
        return {
            "error": f"isochrone opvragen mislukt: {exc}",
            "hint": "Controleer of OPENROUTESERVICE_API_KEY geldig is en probeer opnieuw.",
        }

    profile_labels = {
        "foot-walking": "wandel",
        "cycling-regular": "fiets",
        "driving-car": "auto",
    }
    label = profile_labels.get(profile, profile)
    summary = f"{int(minutes)}-min {label}bereik"

    dataset_id = f"isochrone-{profile}-{int(minutes)}min-{_hash(location)}"
    run.datasets[dataset_id] = {
        "dataset_id": dataset_id,
        "feature_count": len((geojson or {}).get("features", [])),
        "geojson": geojson,
    }
    run.referenced_dataset_ids.add(dataset_id)

    return {
        "dataset_id": dataset_id,
        "minutes": minutes,
        "profile": profile,
        "summary": summary,
    }


HANDLERS = {
    "apply_map_actions": handle_apply_map_actions,
    "report_problem": handle_report_problem,
    "query_osm": handle_query_osm,
    "geocode": handle_geocode,
    "web_search": handle_web_search,
    "isochrone": handle_isochrone,
}
