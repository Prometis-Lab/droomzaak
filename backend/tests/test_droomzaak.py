"""Droomzaak unit + lean e2e tests. No real APIs: gateway, LLM, and the provider
adapter are all stubbed/monkeypatched."""

from __future__ import annotations

import pytest

from backend.app import droomzaak_chapters, droomzaak_tools
from backend.app.agent_loop import ProviderResponse, ToolCall
from backend.app.droomzaak_validation import validate_set_chapter_state
from backend.app.storage import CatalogStore


# ── validation ──────────────────────────────────────────────────────────
def _scs(patch, state):
    return validate_set_chapter_state({"type": "set_chapter_state", "patch": patch}, state)


def test_default_state():
    s = droomzaak_chapters.default_chapter_state()
    assert s["current_chapter"] == "1_droom"
    assert s["dream_profile"] is None


def test_apply_state_patch_deep_merges():
    s = {"current_chapter": "1_droom", "dream_profile": {"sector": "horeca"}}
    out = droomzaak_chapters.apply_state_patch(s, {"dream_profile": {"nace_code": "56.101"}})
    assert out["dream_profile"] == {"sector": "horeca", "nace_code": "56.101"}


def test_scs_accepts_dream_profile():
    _, err = _scs({"dream_profile": {"sector": "horeca"}}, {"current_chapter": "1_droom"})
    assert err is None


def test_scs_rejects_unknown_key():
    _, err = _scs({"intent_detected": "skip"}, {"current_chapter": "1_droom"})
    assert err and "unknown keys" in err["error"]


def test_scs_rejects_advance_without_exit():
    _, err = _scs({"current_chapter": "2_niche"}, {"current_chapter": "1_droom", "dream_profile": None})
    assert err and "exit condition not met" in err["error"]


def test_scs_accepts_advance_with_sector_in_same_patch():
    _, err = _scs(
        {"dream_profile": {"sector": "horeca"}, "current_chapter": "2_niche"},
        {"current_chapter": "1_droom"},
    )
    assert err is None


def test_scs_rejects_skip():
    _, err = _scs({"current_chapter": "5_pakket"},
                  {"current_chapter": "1_droom", "dream_profile": {"sector": "horeca"}})
    assert err and "sequentially" in err["hint"]


def test_scs_same_chapter_update_no_exit_check():
    _, err = _scs({"current_chapter": "3_waar", "chosen_location": {"coordinates": [3.7, 51.0]}},
                  {"current_chapter": "3_waar", "dream_profile": {"sector": "horeca"}})
    assert err is None


def test_chapter_tool_allowlist_filters():
    names = {s["name"] for s in droomzaak_chapters._chapter_tool_specs("1_droom")}
    assert "extract_dream_profile" in names
    assert "score_locations" not in names
    assert "apply_map_actions" in names


# ── tools ───────────────────────────────────────────────────────────────
@pytest.fixture
def stub_gateway(monkeypatch):
    responses: list = []

    async def fake_query(sql, params=None, *, tool_name=None):
        return responses.pop(0)

    monkeypatch.setattr(droomzaak_tools.gateway, "query", fake_query)
    return responses


async def test_peer_benchmarks_summary(stub_gateway):
    # New handler makes THREE sequential gateway calls: VAT, starters, bankruptcies.
    # Push three canned responses in order.
    stub_gateway.append([{"active_count": 13, "vat_starts": 2, "vat_stops": 1,
                          "scope": "gent_arrondissement"}])          # SQL-1 VAT
    stub_gateway.append([
        {"year": 2024, "n_first_start": 6, "n_restart": 1, "n_stop": -2, "n_eop": 130},
        {"year": 2021, "n_first_start": 5, "n_restart": 1, "n_stop": -3, "n_eop": 100},
    ])                                                                 # SQL-2 starters
    stub_gateway.append([{"year": 2024, "n_bankruptcies": 4}])        # SQL-3 bankruptcies
    out = await droomzaak_tools.HANDLERS["peer_benchmarks_statbel"](
        {"nace_code": "56.101", "refnis": "44021"}, _run())
    assert out["summary"]["active_count_latest"] == 13
    assert out["summary"]["growth_3y_pct"] == 30.0
    assert out["summary"]["starters_recent"] == 7   # 6 + 1
    assert out["summary"]["stops_recent"] == 2
    assert out["summary"]["bankruptcies_latest"] == 4
    # rows dict shape: vat / starters_by_year / bankruptcies_by_year
    assert "vat" in out["rows"] and "starters_by_year" in out["rows"]


async def test_permit_checklist_excludes_alcohol(stub_gateway):
    # permit_checklist_for is now a YAML-config tool — it does NOT call the gateway.
    # stub_gateway is unused here; the test verifies YAML-based behavior.
    # YAML has drankvergunning_gegist with attribute_filter {serves_alcohol: gegiste}
    # and drankvergunning_sterk with {serves_alcohol: sterke}.
    # An empty attributes dict should exclude both alcohol rules.
    out = await droomzaak_tools.HANDLERS["permit_checklist_for"](
        {"nace_code": "56.101", "attributes": {}}, _run())
    names = [c["permit_name"] for c in out["checklist"]]
    # Base rules (no attribute filter) must appear
    assert "Inschrijving KBO + BTW-activering" in names
    assert "Horeca-attest Stad Gent" in names
    # Alcohol rules must NOT appear (attribute_filter not satisfied)
    assert "Drankvergunning gegiste dranken" not in names
    assert "Sterkedrankvergunning" not in names


async def test_legal_form_bv_with_partners():
    out = await droomzaak_tools.HANDLERS["legal_form_advisor"](
        {"dream_profile": {"partners_guess": 1, "scale": "small"}, "chosen_location": {}}, _run())
    assert out["recommended"] == "BV/SRL"


async def test_gateway_unavailable_envelope():
    # real gateway has no pool open in tests → graceful error envelope
    out = await droomzaak_tools.HANDLERS["rent_benchmark"]({"sector_id": "44021A00-"}, _run())
    assert "error" in out and "hint" in out


def _run():
    from backend.app.agent_loop import AgentRun
    return AgentRun()


# ── lean e2e: chapter 1 transition ──────────────────────────────────────
class _FakeAdapter:
    name = "fake"
    model_id = "fake-1"
    model_label = "Fake"

    def __init__(self, scripted):
        self._scripted = list(scripted)

    def build_initial_messages(self, **_):
        return [], {}

    def translate_tool_specs(self, specs):
        return specs

    async def call(self, **_):
        return self._scripted.pop(0)

    def append_assistant(self, messages, response):
        messages.append({"role": "assistant", "content": response.text_content})

    def append_tool_results(self, messages, results):
        messages.append({"role": "tool", "content": "ok"})

    def append_commit_nudge(self, messages, text):
        messages.append({"role": "user", "content": text})

    def stage_name(self, i):
        return f"fake_{i}"

    def error_stage_name(self):
        return "fake_error"


async def test_chapter1_transitions_to_niche(monkeypatch):
    store = CatalogStore(":memory:")

    async def fake_complete_json(system, user):
        return {"sector": "horeca", "sector_group": "horeca", "nace_code": "56.101",
                "scale": "small", "neighbourhood_anchor": "Vrijdagmarkt", "vibe": "cozy",
                "confidence": 0.9}

    monkeypatch.setattr(droomzaak_tools, "complete_json", fake_complete_json)

    scripted = [
        ProviderResponse(raw=None, text_content="Plan: extract", is_terminal=False,
                         tool_calls=[ToolCall("t1", "extract_dream_profile", {"text": "vegan bistro"})],
                         usage_flat={}),
        ProviderResponse(raw=None, text_content="", is_terminal=False, usage_flat={},
                         tool_calls=[ToolCall("t2", "apply_map_actions", {
                             "reply": "Mooi, een veganistische bistro op de Vrijdagmarkt.",
                             "actions": [{"type": "set_chapter_state", "patch": {
                                 "dream_profile": {"sector": "horeca", "nace_code": "56.101"},
                                 "current_chapter": "2_niche"}}]})]),
    ]
    monkeypatch.setattr(droomzaak_chapters, "pick_adapter", lambda: _FakeAdapter(scripted))

    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message="Een kleine veganistische bistro", session_id="s1")
    assert result["chapter_state"]["current_chapter"] == "2_niche"
    assert result["chapter_state"]["dream_profile"]["sector"] == "horeca"
    assert result["chapter_transitioned"] is True
    assert result["reply_source"] == "committed"
    store.close()
