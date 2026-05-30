"""Unit tests for the `clip_points_to_area` agent tool.

All geometry is synthetic; no network, no DataGateway, no model is touched.
Tests cover both within-variants (polygon and layer), the success shape,
property preservation, truncation, and all error paths.
"""

from __future__ import annotations

import pytest

from backend.app import agent_tools
from backend.app.agent_loop import AgentRun

# ── fixtures ──────────────────────────────────────────────────────────────────

# A unit square in lon/lat space centred around Ghent-ish coords, for simplicity.
# Points at the corners of a 0.1-degree square; inside = (3.71, 51.03).
_SQUARE_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[3.70, 51.00], [3.80, 51.00], [3.80, 51.10], [3.70, 51.10], [3.70, 51.00]]],
}

# Points: two inside the square, one outside.
_INSIDE_1 = {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [3.72, 51.03]},
             "properties": {"name": "Café De Graslei", "address": "Graslei 1, Gent", "rating": 4.5}}
_INSIDE_2 = {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [3.75, 51.08]},
             "properties": {"name": "Brasserie 't Klokke", "address": "Korenmarkt 2, Gent", "rating": 4.2}}
_OUTSIDE = {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [3.50, 50.80]},
            "properties": {"name": "Ver-weg Café", "address": "Ergens anders", "rating": 3.0}}

_POINT_LAYER_ID = "osm-cafe-testlayer"
_POLYGON_LAYER_ID = "isochrone-foot-walking-10min-test"


def _run_with_layers(include_polygon_layer: bool = True) -> AgentRun:
    run = AgentRun()
    run.datasets[_POINT_LAYER_ID] = {
        "dataset_id": _POINT_LAYER_ID,
        "feature_count": 3,
        "geojson": {
            "type": "FeatureCollection",
            "features": [_INSIDE_1, _INSIDE_2, _OUTSIDE],
        },
    }
    if include_polygon_layer:
        run.datasets[_POLYGON_LAYER_ID] = {
            "dataset_id": _POLYGON_LAYER_ID,
            "feature_count": 1,
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": _SQUARE_POLYGON, "properties": {"value": 600}}
                ],
            },
        }
    return run


# ── success: within.polygon variant ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_within_polygon_keeps_inside_points():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
        },
        run,
    )

    assert "error" not in result, f"unexpected error: {result}"
    assert result["kept"] == 2
    assert result["examined"] == 3
    assert result["source_dataset_id"] == _POINT_LAYER_ID
    assert result["feature_count"] == 2
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_clip_within_polygon_registers_new_dataset():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
        },
        run,
    )

    ds_id = result["dataset_id"]
    assert ds_id.startswith("clip-")
    assert ds_id in run.datasets
    fc = run.datasets[ds_id]["geojson"]
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 2


@pytest.mark.asyncio
async def test_clip_within_polygon_adds_to_referenced_dataset_ids():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
        },
        run,
    )
    assert result["dataset_id"] in run.referenced_dataset_ids


@pytest.mark.asyncio
async def test_clip_within_polygon_preserves_properties():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
        },
        run,
    )
    ds_id = result["dataset_id"]
    names = {f["properties"]["name"] for f in run.datasets[ds_id]["geojson"]["features"]}
    assert names == {"Café De Graslei", "Brasserie 't Klokke"}
    # Full properties intact (address, rating)
    for feat in run.datasets[ds_id]["geojson"]["features"]:
        assert "address" in feat["properties"]
        assert "rating" in feat["properties"]


# ── success: within.layer variant ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_within_layer_keeps_inside_points():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"layer": _POLYGON_LAYER_ID},
        },
        run,
    )

    assert "error" not in result, f"unexpected error: {result}"
    assert result["kept"] == 2
    assert result["examined"] == 3


@pytest.mark.asyncio
async def test_clip_within_layer_adds_polygon_layer_to_referenced_ids():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"layer": _POLYGON_LAYER_ID},
        },
        run,
    )
    assert _POLYGON_LAYER_ID in run.referenced_dataset_ids
    assert result["dataset_id"] in run.referenced_dataset_ids


@pytest.mark.asyncio
async def test_clip_within_layer_preserves_properties():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"layer": _POLYGON_LAYER_ID},
        },
        run,
    )
    ds_id = result["dataset_id"]
    names = {f["properties"]["name"] for f in run.datasets[ds_id]["geojson"]["features"]}
    assert names == {"Café De Graslei", "Brasserie 't Klokke"}


# ── label ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_auto_label_is_dutch():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
        },
        run,
    )
    # Auto-label should contain the count and be in Dutch (no English words).
    assert "2" in result["label"]
    assert "punten" in result["label"]


@pytest.mark.asyncio
async def test_clip_custom_label_is_used():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
            "label": "Cafés op wandelafstand",
        },
        run,
    )
    assert result["label"] == "Cafés op wandelafstand"


# ── limit / truncation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_limit_truncates_results():
    """With limit=1, only 1 of the 2 inside points is kept; truncated=True."""
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON},
            "limit": 1,
        },
        run,
    )
    assert "error" not in result, f"unexpected error: {result}"
    assert result["kept"] == 1
    assert result["feature_count"] == 1
    assert result["truncated"] is True


# ── id stability ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_dataset_id_is_deterministic():
    """Same inputs produce the same dataset_id."""
    run1 = _run_with_layers()
    r1 = await agent_tools.HANDLERS["clip_points_to_area"](
        {"source_dataset_id": _POINT_LAYER_ID, "within": {"polygon": _SQUARE_POLYGON}},
        run1,
    )
    run2 = _run_with_layers()
    r2 = await agent_tools.HANDLERS["clip_points_to_area"](
        {"source_dataset_id": _POINT_LAYER_ID, "within": {"polygon": _SQUARE_POLYGON}},
        run2,
    )
    assert r1["dataset_id"] == r2["dataset_id"]


# ── error: 0 matches ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_zero_matches_returns_error_with_counts():
    """When no point is inside the polygon, return an informative error dict."""
    tiny_polygon = {
        "type": "Polygon",
        # A tiny square somewhere in the North Sea — nothing will match.
        "coordinates": [[[2.00, 52.00], [2.01, 52.00], [2.01, 52.01], [2.00, 52.01], [2.00, 52.00]]],
    }
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": tiny_polygon},
        },
        run,
    )
    assert "error" in result
    assert "examined" in result
    assert "rejected_by_within" in result
    assert result["source_dataset_id"] == _POINT_LAYER_ID
    # No dataset registered when nothing matched.
    clip_ids = [k for k in run.datasets if k.startswith("clip-")]
    assert clip_ids == []


# ── error: missing source ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_missing_source_returns_error():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": "nonexistent-layer",
            "within": {"polygon": _SQUARE_POLYGON},
        },
        run,
    )
    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_clip_empty_source_id_returns_error():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {"source_dataset_id": "", "within": {"polygon": _SQUARE_POLYGON}},
        run,
    )
    assert "error" in result
    assert "hint" in result


# ── error: within validation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_both_within_keys_returns_error():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": _SQUARE_POLYGON, "layer": _POLYGON_LAYER_ID},
        },
        run,
    )
    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_clip_no_within_key_returns_error():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {},
        },
        run,
    )
    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_clip_within_layer_not_found_returns_error():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"layer": "nonexistent-polygon-layer"},
        },
        run,
    )
    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_clip_within_polygon_wrong_type_returns_error():
    run = _run_with_layers()
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"polygon": {"type": "Point", "coordinates": [3.72, 51.03]}},
        },
        run,
    )
    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_clip_within_polygon_layer_has_no_polygons_returns_error():
    """A layer that only contains Points should give a clear error."""
    run = _run_with_layers()
    # Register a points-only layer under a new id and use it as the within.layer.
    run.datasets["points-only-layer"] = {
        "dataset_id": "points-only-layer",
        "feature_count": 1,
        "geojson": {
            "type": "FeatureCollection",
            "features": [_INSIDE_1],
        },
    }
    result = await agent_tools.HANDLERS["clip_points_to_area"](
        {
            "source_dataset_id": _POINT_LAYER_ID,
            "within": {"layer": "points-only-layer"},
        },
        run,
    )
    assert "error" in result
    assert "hint" in result


# ── wiring smoke-tests ────────────────────────────────────────────────────────

def test_clip_in_handlers():
    assert "clip_points_to_area" in agent_tools.HANDLERS


def test_clip_spec_in_tool_specs():
    names = {s["name"] for s in agent_tools.tool_specs()}
    assert "clip_points_to_area" in names


def test_clip_in_chapter3_allowlist():
    from backend.app.droomzaak_prompt import CHAPTER_TOOL_ALLOWLIST
    assert "clip_points_to_area" in CHAPTER_TOOL_ALLOWLIST["3_waar"]


def test_clip_not_in_other_chapters():
    from backend.app.droomzaak_prompt import CHAPTER_TOOL_ALLOWLIST
    for chapter in ("1_droom", "2_niche", "4_vergunningen", "5_pakket"):
        assert "clip_points_to_area" not in CHAPTER_TOOL_ALLOWLIST[chapter], (
            f"clip_points_to_area onverwacht aanwezig in {chapter}"
        )
