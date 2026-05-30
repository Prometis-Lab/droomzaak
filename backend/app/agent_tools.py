"""Base behaviour tools — native, NOT routed through the DataGateway.

apply_map_actions (the one COMMIT tool), report_problem, and the live enrichment
tools query_osm / geocode / web_search. Handlers are async and take (args, run).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from shapely.geometry import shape, Point
from shapely.ops import unary_union

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


SPEC_CLIP_POINTS_TO_AREA = {
    "name": "clip_points_to_area",
    "description": (
        "Clip a point layer to only those points that fall within a polygon area. "
        "Typical use in Chapter 3 (Waar): clip query_osm or places_search points to an "
        "isochrone polygon so only venues within walking/cycling reach are shown. "
        "Returns a new transient layer; use show_layer to display it. "
        "source_dataset_id must already exist in this turn's datasets (call query_osm or "
        "places_search first). within.layer is the most common variant — pass the dataset_id "
        "of an isochrone layer; within.polygon accepts a raw GeoJSON Polygon/MultiPolygon."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "source_dataset_id": {
                "type": "string",
                "description": "dataset_id of the point layer to clip (e.g. an osm- or places- id).",
            },
            "within": {
                "type": "object",
                "description": (
                    "Exactly one of: {\"layer\": \"<dataset_id>\"} to union all polygons from a "
                    "transient layer (e.g. an isochrone), or {\"polygon\": <GeoJSON Polygon|MultiPolygon>} "
                    "for a raw geometry."
                ),
                "properties": {
                    "layer": {"type": "string"},
                    "polygon": {"type": "object"},
                },
            },
            "label": {
                "type": "string",
                "description": "Short title for the new layer (Dutch). Auto-generated if omitted.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 500,
                "default": 500,
                "description": "Cap on the number of features to keep in the result.",
            },
        },
        "required": ["source_dataset_id", "within"],
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
        SPEC_CLIP_POINTS_TO_AREA,
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


async def handle_clip_points_to_area(args: dict, run: AgentRun) -> dict:
    source_id = args.get("source_dataset_id")
    if not isinstance(source_id, str) or not source_id:
        return {
            "error": "source_dataset_id is vereist",
            "hint": "Geef de dataset_id van een punt-laag op (bv. na query_osm of places_search).",
        }
    source_ds = run.datasets.get(source_id)
    if source_ds is None:
        return {
            "error": f"source_dataset_id '{source_id}' niet gevonden in de huidige datasets",
            "hint": "Roep eerst query_osm of places_search aan om een punt-laag te maken.",
        }
    features = (source_ds.get("geojson") or {}).get("features")
    if not isinstance(features, list):
        return {
            "error": f"dataset '{source_id}' bevat geen geldige GeoJSON features-lijst",
            "hint": "Roep eerst query_osm of places_search aan om een punt-laag te maken.",
        }

    within = args.get("within")
    if not isinstance(within, dict):
        return {
            "error": "within is vereist en moet een object zijn",
            "hint": "Geef within.layer of within.polygon op.",
        }
    within_keys = [k for k in ("polygon", "layer") if k in within]
    if len(within_keys) == 0:
        return {
            "error": "within moet exact één sleutel bevatten: 'polygon' of 'layer'",
            "hint": "Geef within.layer (dataset_id van een isochrone) of within.polygon (GeoJSON geometrie) op.",
        }
    if len(within_keys) > 1:
        return {
            "error": "within mag slechts één sleutel bevatten, niet beide: 'polygon' en 'layer'",
            "hint": "Gebruik within.layer (meest gebruikelijk) of within.polygon, niet beide tegelijk.",
        }

    within_geom = None
    if "polygon" in within:
        geom_obj = within["polygon"]
        if not isinstance(geom_obj, dict):
            return {
                "error": "within.polygon moet een GeoJSON geometrie-object zijn",
                "hint": "Geef een geldig GeoJSON Polygon of MultiPolygon object op.",
            }
        geom_type = geom_obj.get("type")
        if geom_type not in ("Polygon", "MultiPolygon"):
            return {
                "error": f"within.polygon heeft type '{geom_type}', maar moet Polygon of MultiPolygon zijn",
                "hint": "Controleer de GeoJSON geometrie.",
            }
        try:
            within_geom = shape(geom_obj)
        except Exception as exc:
            return {
                "error": f"within.polygon kon niet worden geparseerd: {exc}",
                "hint": "Controleer of de GeoJSON coördinaten geldig zijn.",
            }
        if within_geom.is_empty:
            return {
                "error": "within.polygon is een lege geometrie",
                "hint": "Geef een niet-lege polygoon op.",
            }

    else:  # "layer" variant
        ref_id = within["layer"]
        if not isinstance(ref_id, str) or not ref_id:
            return {
                "error": "within.layer moet een niet-lege dataset_id string zijn",
                "hint": "Geef de dataset_id van een isochrone of polygoon-laag op.",
            }
        ref_ds = run.datasets.get(ref_id)
        if ref_ds is None:
            return {
                "error": f"within.layer '{ref_id}' niet gevonden in de huidige datasets",
                "hint": "Zorg dat de polygon-laag (bv. isochrone) al aangemaakt is voor je clipt.",
            }
        ref_features = (ref_ds.get("geojson") or {}).get("features") or []
        polygons: list[Any] = []
        for feat in ref_features:
            if not isinstance(feat, dict):
                continue
            try:
                g = shape(feat.get("geometry") or {})
            except Exception:
                continue
            if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
                continue
            polygons.append(g)
        if not polygons:
            return {
                "error": f"within.layer '{ref_id}' bevat geen Polygon/MultiPolygon features",
                "hint": "Controleer of de laag polygonen bevat (bv. een isochrone-laag).",
            }
        within_geom = polygons[0] if len(polygons) == 1 else unary_union(polygons)
        run.referenced_dataset_ids.add(ref_id)

    limit = 500
    raw_limit = args.get("limit")
    if raw_limit is not None:
        try:
            limit = max(1, min(int(raw_limit), 500))
        except (TypeError, ValueError):
            return {
                "error": "limit moet een geheel getal zijn (1–500)",
                "hint": "Geef een integer op voor limit.",
            }

    kept: list[dict] = []
    examined = 0
    rejected_by_within = 0
    truncated = False

    for feat in features:
        if not isinstance(feat, dict):
            continue
        examined += 1
        geom_raw = feat.get("geometry")
        if not isinstance(geom_raw, dict):
            rejected_by_within += 1
            continue
        try:
            g = shape(geom_raw)
            pt = Point(g.coords[0]) if g.geom_type == "Point" else g.representative_point()
        except Exception:
            rejected_by_within += 1
            continue
        if not within_geom.covers(pt):
            rejected_by_within += 1
            continue
        kept.append(feat)
        if len(kept) >= limit:
            truncated = len(features) - examined > 0 or examined < len(features)
            break

    if not kept:
        return {
            "error": f"Geen punten van '{source_id}' vallen binnen het opgegeven gebied",
            "hint": "Vergroot het zoekgebied of gebruik een ruimere isochrone.",
            "source_dataset_id": source_id,
            "examined": examined,
            "rejected_by_within": rejected_by_within,
        }

    label = args.get("label") or f"{len(kept)} punten binnen het gebied"
    dataset_id = f"clip-{_hash(source_id, args.get('within'), label)}"
    run.datasets[dataset_id] = {
        "dataset_id": dataset_id,
        "feature_count": len(kept),
        "geojson": {"type": "FeatureCollection", "features": kept},
    }
    run.referenced_dataset_ids.add(dataset_id)

    return {
        "dataset_id": dataset_id,
        "feature_count": len(kept),
        "source_dataset_id": source_id,
        "kept": len(kept),
        "examined": examined,
        "label": label,
        "truncated": truncated,
    }


HANDLERS = {
    "apply_map_actions": handle_apply_map_actions,
    "report_problem": handle_report_problem,
    "query_osm": handle_query_osm,
    "geocode": handle_geocode,
    "web_search": handle_web_search,
    "isochrone": handle_isochrone,
    "clip_points_to_area": handle_clip_points_to_area,
}
