"""Droomzaak unit + lean e2e tests. No real APIs: gateway, LLM, and the provider
adapter are all stubbed/monkeypatched."""

from __future__ import annotations

import pytest

from backend.app import droomzaak_chapters, droomzaak_tools
from backend.app.agent_loop import AgentRun, ProviderResponse, ToolCall, run_loop
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


# ── same-turn chapter-transition continuation ───────────────────────────
def _commit(reply, actions, text=""):
    return ProviderResponse(
        raw=None, text_content=text, is_terminal=False, usage_flat={},
        tool_calls=[ToolCall("c", "apply_map_actions", {"reply": reply, "actions": actions})],
    )


def _seed(store, sid, chapter, **extra):
    state = droomzaak_chapters.default_chapter_state()
    state["current_chapter"] = chapter
    state.update(extra)
    store.save_chapter_state(sid, state)


async def test_same_turn_advance_delivers(monkeypatch):
    """Niche→Waar: the agent advances AND delivers scored locations in one turn."""
    store = CatalogStore(":memory:")
    _seed(store, "s2", "2_niche",
          dream_profile={"sector": "horeca", "nace_code": "56.101"},
          niche_signals={"active_count": 13})
    scripted = [
        _commit("We gaan nu je plek zoeken.",
                [{"type": "set_chapter_state", "patch": {"current_chapter": "3_waar"}}]),
        _commit("Hier zijn 3 buurten rond Dampoort met sterk bakkerij-potentieel.",
                [{"type": "show_layer", "dataset_id": "score-locations-test"},
                 {"type": "set_layer_heatmap", "dataset_id": "score-locations-test",
                  "field": "score", "palette": "blue-yellow-red"},
                 {"type": "set_chapter_state",
                  "patch": {"candidate_locations": [{"sector_id": "A"}]}}]),
    ]
    monkeypatch.setattr(droomzaak_chapters, "pick_adapter", lambda: _FakeAdapter(scripted))

    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message="Ik wil mijn plek vinden", session_id="s2")

    assert result["reply"].startswith("Hier zijn 3 buurten")  # segment-2 reply, not the bridge
    assert result["chapter_state"]["current_chapter"] == "3_waar"
    assert result["chapter_state"]["candidate_locations"] == [{"sector_id": "A"}]
    assert result["chapter_transitioned"] is True
    types = [a["type"] for a in result["actions"]]
    assert "show_layer" in types and "set_layer_heatmap" in types
    assert types.count("set_chapter_state") == 2  # action_log union across both segments
    store.close()


async def test_droom_to_niche_no_same_turn_continuation(monkeypatch):
    """Droom→Niche keeps its gentle two-beat: the chapter advances but does NOT continue."""
    store = CatalogStore(":memory:")
    _seed(store, "s6", "1_droom")
    scripted = [_commit("Wat een warm idee.", [{"type": "set_chapter_state", "patch": {
        "dream_profile": {"sector": "horeca"}, "current_chapter": "2_niche"}}])]
    stages: list = []
    monkeypatch.setattr(droomzaak_chapters, "pick_adapter", lambda: _FakeAdapter(scripted))

    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message="een bistro", session_id="s6", debug_stages=stages)

    assert result["chapter_state"]["current_chapter"] == "2_niche"
    assert result["chapter_transitioned"] is True
    assert not any(s["stage"] == "same_turn_continuation" for s in stages)
    store.close()


async def test_no_advance_breaks_as_before(monkeypatch):
    """A commit with no chapter change breaks after one commit (regression guard)."""
    store = CatalogStore(":memory:")
    _seed(store, "s3", "3_waar", dream_profile={"sector": "horeca", "nace_code": "56.101"})
    scripted = [_commit("Drie buurten.", [
        {"type": "show_layer", "dataset_id": "score-locations-x"},
        {"type": "set_chapter_state", "patch": {"candidate_locations": [{"sector_id": "B"}]}}])]
    monkeypatch.setattr(droomzaak_chapters, "pick_adapter", lambda: _FakeAdapter(scripted))

    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message="waar?", session_id="s3")

    assert result["chapter_transitioned"] is False
    assert result["chapter_state"]["candidate_locations"] == [{"sector_id": "B"}]
    store.close()


async def test_continuation_budget_exhausted_surfaces_bridge(monkeypatch):
    """If the continuation never commits, the honest bridge reply surfaces and the
    chapter still advances (state lives on run.current_chapter_state)."""
    store = CatalogStore(":memory:")
    _seed(store, "s4", "2_niche",
          dream_profile={"sector": "horeca", "nace_code": "56.101"},
          niche_signals={"active_count": 3})
    scripted = [
        _commit("We gaan nu je plek zoeken.",
                [{"type": "set_chapter_state", "patch": {"current_chapter": "3_waar"}}]),
        ProviderResponse(raw=None, text_content="ik denk na", is_terminal=True,
                         usage_flat={}, tool_calls=[]),
    ]
    monkeypatch.setattr(droomzaak_chapters, "pick_adapter", lambda: _FakeAdapter(scripted))

    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message="Ik wil mijn plek vinden", session_id="s4")

    assert result["reply"] == "We gaan nu je plek zoeken."
    assert result["chapter_state"]["current_chapter"] == "3_waar"
    assert result["reply_source"] == "committed"
    store.close()


async def test_bridge_without_niche_signals_rejected(monkeypatch):
    """E7: a 2→3 advance without niche_signals fails the whole commit; no continuation."""
    store = CatalogStore(":memory:")
    _seed(store, "s5", "2_niche", dream_profile={"sector": "horeca", "nace_code": "56.101"})
    scripted = [
        _commit("We gaan nu je plek zoeken.",
                [{"type": "set_chapter_state", "patch": {"current_chapter": "3_waar"}}]),
        _commit("Hier is wat ik al weet over je niche.", []),
    ]
    stages: list = []
    monkeypatch.setattr(droomzaak_chapters, "pick_adapter", lambda: _FakeAdapter(scripted))

    result = await droomzaak_chapters.run_droomzaak_turn(
        store=store, user_message="Ik wil mijn plek vinden", session_id="s5", debug_stages=stages)

    assert result["chapter_state"]["current_chapter"] == "2_niche"
    assert result["chapter_transitioned"] is False
    assert not any(s["stage"] == "same_turn_continuation" for s in stages)
    assert result["reply"] == "Hier is wat ik al weet over je niche."
    store.close()


# ── run_loop on_commit contract (provider-neutral, no chapter knowledge) ──
async def _commit_executor(name, args, run):
    if name == "apply_map_actions":
        run.pending_reply = args.get("reply", "")
        run.pending_actions = args.get("actions", [])
        return {"applied": True}
    return {"ok": True}


async def test_run_loop_default_unchanged():
    """on_commit=None → early break after the single commit (locks today's contract)."""
    run = AgentRun()
    scripted = [_commit("klaar", [])]
    result = await run_loop(
        adapter=_FakeAdapter(scripted), run=run, system_text="", history=[],
        runtime_block="", user_message="hi", tool_specs_neutral=[],
        execute_tool=_commit_executor, max_iterations=5)
    assert result["reply"] == "klaar"
    assert result["iterations"] == 1  # broke after the commit; scripted had only one response


async def test_on_commit_exception_safe():
    """E9: a raising on_commit never crashes the turn; the committed reply still surfaces."""
    run = AgentRun()
    scripted = [_commit("brug", [])]
    stages: list = []

    def boom(_run, _stages):
        raise RuntimeError("boom")

    result = await run_loop(
        adapter=_FakeAdapter(scripted), run=run, system_text="", history=[],
        runtime_block="", user_message="hi", tool_specs_neutral=[],
        execute_tool=_commit_executor, on_commit=boom, debug_stages=stages, max_iterations=5)
    assert result["reply"] == "brug"
    assert any(s["stage"] == "on_commit_error" for s in stages)
