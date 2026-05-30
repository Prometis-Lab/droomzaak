"""Monkeypatched unit tests for the `isochrone` agent tool.

Real ORS, real settings keys, and real HTTP are NEVER touched — httpx.AsyncClient
is monkeypatched at the module level, exactly as the rest of the test suite
handles external HTTP.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app import agent_tools, settings
from backend.app.agent_loop import AgentRun


# ── helpers ────────────────────────────────────────────────────────────────────

def _run() -> AgentRun:
    return AgentRun()


_FAKE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[3.72, 51.05], [3.73, 51.05], [3.73, 51.06], [3.72, 51.05]]],
            },
            "properties": {"value": 600},
        }
    ],
}


def _make_fake_client(status_code: int = 200, body: Any = _FAKE_GEOJSON):
    """Build a context-manager-compatible fake httpx.AsyncClient."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=body)
    if status_code >= 400:
        resp.raise_for_status = MagicMock(side_effect=Exception(f"HTTP {status_code}"))
    else:
        resp.raise_for_status = MagicMock()

    async_client = AsyncMock()
    async_client.post = AsyncMock(return_value=resp)

    # Support `async with httpx.AsyncClient(...) as client:`
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=async_client)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    return context_manager


# ── success path ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_isochrone_success_registers_transient_dataset(monkeypatch):
    """Happy path: ORS returns 200, dataset_id is registered on the run."""
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "test-key-abc")

    fake_ctx = _make_fake_client(200, _FAKE_GEOJSON)
    with patch("backend.app.agent_tools.httpx.AsyncClient", return_value=fake_ctx):
        run = _run()
        result = await agent_tools.HANDLERS["isochrone"](
            {"location": [3.7257, 51.0543], "minutes": 10, "profile": "foot-walking"},
            run,
        )

    # Return shape
    assert "dataset_id" in result, f"unexpected result: {result}"
    assert "error" not in result
    assert result["minutes"] == 10.0
    assert result["profile"] == "foot-walking"
    assert result["summary"] == "10-min wandelbereik"

    # Transient dataset registered on the run
    ds_id = result["dataset_id"]
    assert ds_id in run.datasets
    assert run.datasets[ds_id]["geojson"]["type"] == "FeatureCollection"
    assert run.datasets[ds_id]["feature_count"] == 1

    # dataset_id is widened into the candidate map
    assert ds_id in run.referenced_dataset_ids


@pytest.mark.asyncio
async def test_isochrone_cycling_profile_label(monkeypatch):
    """Cycling profile produces the correct Dutch label."""
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "test-key-xyz")

    fake_ctx = _make_fake_client(200, _FAKE_GEOJSON)
    with patch("backend.app.agent_tools.httpx.AsyncClient", return_value=fake_ctx):
        run = _run()
        result = await agent_tools.HANDLERS["isochrone"](
            {"location": [3.72, 51.05], "minutes": 15, "profile": "cycling-regular"},
            run,
        )

    assert "error" not in result
    assert result["summary"] == "15-min fietsbereik"


@pytest.mark.asyncio
async def test_isochrone_dataset_id_is_deterministic(monkeypatch):
    """Same inputs produce the same dataset_id (hash is stable)."""
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "test-key")

    fake_ctx = _make_fake_client(200, _FAKE_GEOJSON)
    with patch("backend.app.agent_tools.httpx.AsyncClient", return_value=fake_ctx):
        run1 = _run()
        r1 = await agent_tools.HANDLERS["isochrone"](
            {"location": [3.7257, 51.0543], "minutes": 10, "profile": "foot-walking"}, run1
        )
        run2 = _run()
        r2 = await agent_tools.HANDLERS["isochrone"](
            {"location": [3.7257, 51.0543], "minutes": 10, "profile": "foot-walking"}, run2
        )

    assert r1["dataset_id"] == r2["dataset_id"]


# ── missing-key path ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_isochrone_missing_api_key_returns_error_envelope(monkeypatch):
    """When OPENROUTESERVICE_API_KEY is empty, return {error, hint} — never raise."""
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "")

    run = _run()
    result = await agent_tools.HANDLERS["isochrone"](
        {"location": [3.7257, 51.0543], "minutes": 10}, run
    )

    assert "error" in result
    assert "hint" in result
    # No dataset registered when key is absent
    assert len(run.datasets) == 0


# ── ORS non-200 path ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_isochrone_ors_http_error_returns_error_envelope(monkeypatch):
    """ORS returns a 4xx/5xx → error envelope, no raise."""
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "test-key")

    fake_ctx = _make_fake_client(status_code=403)
    with patch("backend.app.agent_tools.httpx.AsyncClient", return_value=fake_ctx):
        run = _run()
        result = await agent_tools.HANDLERS["isochrone"](
            {"location": [3.72, 51.05], "minutes": 10}, run
        )

    assert "error" in result
    assert "hint" in result
    assert len(run.datasets) == 0


# ── bad-input path ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_isochrone_bad_location_returns_error_envelope(monkeypatch):
    """Missing or malformed location returns error envelope without hitting ORS."""
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "test-key")

    run = _run()
    result = await agent_tools.HANDLERS["isochrone"]({"location": [3.72]}, run)

    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_isochrone_no_location_key_returns_error_envelope(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTESERVICE_API_KEY", "test-key")

    run = _run()
    result = await agent_tools.HANDLERS["isochrone"]({}, run)

    assert "error" in result
    assert "hint" in result


# ── prompt allowlist smoke-test ────────────────────────────────────────────────

def test_isochrone_in_chapter3_allowlist():
    from backend.app.droomzaak_prompt import CHAPTER_TOOL_ALLOWLIST
    assert "isochrone" in CHAPTER_TOOL_ALLOWLIST["3_waar"]


def test_isochrone_not_in_other_chapters():
    from backend.app.droomzaak_prompt import CHAPTER_TOOL_ALLOWLIST
    for chapter in ("1_droom", "2_niche", "4_vergunningen", "5_pakket"):
        assert "isochrone" not in CHAPTER_TOOL_ALLOWLIST[chapter], (
            f"isochrone leaked into {chapter} allowlist"
        )


def test_isochrone_spec_in_tool_specs():
    specs = agent_tools.tool_specs()
    names = {s["name"] for s in specs}
    assert "isochrone" in names


def test_isochrone_handler_in_handlers():
    assert "isochrone" in agent_tools.HANDLERS
