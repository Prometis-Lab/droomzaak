"""Package-renderer tests — the printable Droomzaak-pakket.

No real APIs/DB: an in-memory DuckDB store via set_store, and the DataGateway is
kept disabled (DROOMZAAK_POSTGRES_URL forced empty) so the app lifespan boots in
degraded mode under TestClient.

Field shapes mirror the REAL package (handle_compose_package) / chapter_state
(_CHAPTER_KEYS).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import settings
from backend.app.droomzaak_chapters import default_chapter_state
from backend.app.main import app
from backend.app.storage import CatalogStore, set_store


@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch):
    """Force degraded mode + a fresh in-memory store for every test."""
    monkeypatch.setattr(settings, "DROOMZAAK_POSTGRES_URL", "")
    store = CatalogStore(":memory:")
    set_store(store)
    yield store
    set_store(None)
    store.close()


def _client() -> TestClient:
    return TestClient(app)


def _full_package(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "generated_at": "2026-05-30",
        "dream_profile": {"sector": "veganistische bistro", "nace_code": "56.101",
                          "founder_quote": "Een kleine plek bij de Vrijdagmarkt."},
        "niche_signals": {"gap": "weinig vegan"},
        "chosen_location": {"address": "Vrijdagmarkt 12", "wijk_nl": "Binnenstad"},
        "candidate_locations": [],
        "permit_checklist": [
            {"rule_id": "terras", "permit_name": "Terrasvergunning", "authority": "Stad Gent",
             "deep_link": "https://stad.gent/terras", "estimated_cost_eur": 150,
             "estimated_processing_days": 30, "notes_nl": "Voor een terras op de stoep."},
        ],
        "subsidies": [
            {"subsidy_id": "starter", "name": "Starterspremie", "authority": "VLAIO",
             "max_amount_eur": 5000, "deep_link": "https://vlaio.be/start",
             "description_nl": "Steun voor starters.", "status": "active"},
            {"subsidy_id": "reno", "name": "Renovatie handelspand", "authority": "Stad Gent",
             "max_amount_eur": 10000, "deep_link": "https://stad.gent/renovatie",
             "description_nl": "Vervallen regeling.", "status": "ended_2025"},
        ],
        "legal_form": {"recommended": "Eenmanszaak", "alternative": "BV/SRL",
                       "rationale_nl": "Administratief het lichtst voor een kleine start.",
                       "estimated_setup_cost_eur": 90,
                       "notes_nl": "Aanbeveling staat bovenaan; bevestig met een boekhouder."},
        "dream_narrative": "Lisa is 32 en droomt van haar eigen plek.\n\nNa jaren in andermans keuken zet ze de stap.",
        "tuesday_morning": "Het is dinsdag 7u. Lisa zet de oven aan en ruikt vers brood.",
    }


def test_renders_saved_package(_isolated_store):
    sid = "sess-full"
    _isolated_store.save_package(sid, _full_package(sid))
    res = _client().get(f"/pakket/{sid}")
    assert res.status_code == 200
    html = res.text
    assert "Vrijdagmarkt" in html              # quote / location
    assert "Terrasvergunning" in html          # a permit
    assert "Starterspremie" in html            # a subsidy
    assert "Eenmanszaak" in html               # legal form
    assert "dinsdagochtend" in html.lower() or "Een dinsdagochtend" in html  # tuesday card heading


def test_renders_tuesday_morning(_isolated_store):
    sid = "sess-tue"
    _isolated_store.save_package(sid, _full_package(sid))
    html = _client().get(f"/pakket/{sid}").text
    assert "ruikt vers brood" in html          # the tuesday_morning string itself


def test_greys_out_ended_subsidies(_isolated_store):
    sid = "sess-ended"
    _isolated_store.save_package(sid, _full_package(sid))
    html = _client().get(f"/pakket/{sid}").text
    assert "vervallen in 2025" in html         # ended marker present
    assert "dz-ended" in html                   # greyed-out class applied


def test_fallback_from_chapter_state(_isolated_store):
    sid = "sess-state"
    state = default_chapter_state()
    state["dream_profile"] = {"sector": "atelier", "founder_quote": "Een klein atelier."}
    state["chosen_location"] = {"address": "Sleepstraat 3"}
    state["dream_narrative"] = "Het begon met een idee."
    _isolated_store.save_chapter_state(sid, state)
    res = _client().get(f"/pakket/{sid}")
    assert res.status_code == 200
    assert "atelier" in res.text
    assert "Sleepstraat 3" in res.text


def test_empty_session_404(_isolated_store):
    res = _client().get("/pakket/does-not-exist")
    assert res.status_code == 404


def test_default_state_404(_isolated_store):
    """A session that only has the empty default state is not worth rendering."""
    sid = "sess-empty"
    _isolated_store.save_chapter_state(sid, default_chapter_state())
    assert _client().get(f"/pakket/{sid}").status_code == 404


def test_autoescape_blocks_injection(_isolated_store):
    sid = "sess-xss"
    pkg = _full_package(sid)
    pkg["dream_narrative"] = "Onschuldig.\n\n<script>alert('xss')</script>"
    _isolated_store.save_package(sid, pkg)
    html = _client().get(f"/pakket/{sid}").text
    assert "<script>alert('xss')</script>" not in html
    assert "&lt;script&gt;" in html


def test_compose_from_state_endpoint(_isolated_store):
    sid = "sess-finalise"
    state = default_chapter_state()
    state["dream_profile"] = {"sector": "te finaliseren", "founder_quote": "x"}
    _isolated_store.save_chapter_state(sid, state)
    res = _client().post(f"/api/droomzaak/package/{sid}")
    assert res.status_code == 200
    assert res.json()["package_url"] == f"/pakket/{sid}"
    saved = _isolated_store.load_package(sid)
    assert saved is not None and saved["generated_at"]   # persisted + dated

    empty = _client().post("/api/droomzaak/package/nope")
    assert empty.status_code == 404
