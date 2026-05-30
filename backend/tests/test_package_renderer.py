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


def test_renders_dream_and_niche_fiche(_isolated_store):
    """De droom + Niche fiche (the Droomkaart sidebar facts) surface in the pakket."""
    sid = "sess-fiche"
    pkg = _full_package(sid)
    pkg["dream_profile"] = {
        "sector": "veganistische bistro", "nace_code": "56.101",
        "founder_quote": "Een kleine plek bij de Vrijdagmarkt.",
        "scale": "small", "vibe": "knus", "neighbourhood_anchor": "Vrijdagmarkt",
        "budget_eur_guess": 40000,
    }
    pkg["niche_signals"] = {
        "trend": "stijgend",
        "osm_layer_id": "osm-shop-abc",          # plumbing — must NOT render
        "peer_benchmarks": {"active_count_latest": 12, "growth_3y_pct": 4.2,
                            "scope_note": "VAT: Gent arrondissement."},
    }
    _isolated_store.save_package(sid, pkg)
    html = _client().get(f"/pakket/{sid}").text
    assert "De droom" in html and "Niche" in html
    assert "knus" in html and "Vrijdagmarkt" in html          # dream facts
    assert "± €40000" in html                                  # budget formatted
    assert "trend" in html                                     # primitive niche signal
    assert "± 12" in html and "+4.2%" in html                  # peer-benchmark figures
    assert "VAT: Gent arrondissement." in html                 # scope note (proxy label)
    assert "osm-shop-abc" not in html                          # plumbing filtered out


def test_omits_itemless_permits_and_subsidies(_isolated_store):
    """A truthy-but-itemless permit/subsidy list renders no section (don't add
    what isn't worth mentioning)."""
    sid = "sess-itemless"
    pkg = _full_package(sid)
    pkg["permit_checklist"] = [{"rule_id": "x"}]               # no permit_name → not renderable
    pkg["subsidies"] = [{"subsidy_id": "y"}]                   # no name → not renderable
    _isolated_store.save_package(sid, pkg)
    res = _client().get(f"/pakket/{sid}")
    assert res.status_code == 200                  # still renders (it has a dream + narrative)
    assert "<h2>Vergunningen</h2>" not in res.text
    assert "Subsidies" not in res.text


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


def test_deep_link_javascript_scheme_neutralised(_isolated_store):
    """A javascript: deep_link (injectable via PUT /chapter) must never reach href.

    Jinja escapes text but not URL schemes, so deep_link is sanitized in
    package_view._safe_url. Covered for both link sinks (subsidies + permits) and
    the protocol-relative `//host` bypass; a legit https link still survives.
    """
    sid = "sess-jsurl"
    pkg = _full_package(sid)
    pkg["subsidies"][0]["deep_link"] = "javascript:alert(document.domain)"
    pkg["permit_checklist"][0]["deep_link"] = "//evil.example/x"
    pkg["subsidies"][1]["deep_link"] = "https://stad.gent/ok"  # a safe one survives
    _isolated_store.save_package(sid, pkg)
    html = _client().get(f"/pakket/{sid}").text
    assert "javascript:" not in html
    assert 'href="//evil.example/x"' not in html
    assert 'href="https://stad.gent/ok"' in html


def test_deep_link_sanitised_on_chapter_state_path(_isolated_store):
    """Same guard on the synth-from-chapter-state render path (no saved package)."""
    sid = "sess-jsurl-state"
    state = default_chapter_state()
    state["dream_profile"] = {"sector": "bistro", "founder_quote": "x"}
    state["subsidies"] = [
        {"subsidy_id": "x", "name": "Boobytrap", "deep_link": "javascript:alert(1)",
         "status": "active"},
    ]
    _isolated_store.save_chapter_state(sid, state)
    html = _client().get(f"/pakket/{sid}").text
    assert "javascript:" not in html
    assert "Boobytrap" in html  # the entry still renders, just without the link


def test_pdf_download_returns_pdf(_isolated_store, monkeypatch):
    """The /pdf route hands back an attachment with the bytes from html_to_pdf
    (monkeypatched — tests never launch a real browser)."""
    from backend.app import pdf_render

    captured = {}

    async def fake_html_to_pdf(html: str) -> bytes:
        captured["html"] = html
        return b"%PDF-1.4 fake bytes"

    monkeypatch.setattr(pdf_render, "html_to_pdf", fake_html_to_pdf)
    sid = "sess-pdf"
    _isolated_store.save_package(sid, _full_package(sid))
    res = _client().get(f"/pakket/{sid}/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment" in res.headers["content-disposition"]
    assert res.content == b"%PDF-1.4 fake bytes"
    assert "Terrasvergunning" in captured["html"]   # the real rendered pakket HTML was passed


def test_pdf_download_404_for_empty_session(_isolated_store):
    assert _client().get("/pakket/does-not-exist/pdf").status_code == 404


def test_pdf_download_503_when_engine_unavailable(_isolated_store, monkeypatch):
    """If the PDF engine/Chromium is missing, degrade to 503 (browser-print stays usable)."""
    from backend.app import pdf_render

    async def boom(html: str) -> bytes:
        raise RuntimeError("chromium not installed")

    monkeypatch.setattr(pdf_render, "html_to_pdf", boom)
    sid = "sess-pdf-fail"
    _isolated_store.save_package(sid, _full_package(sid))
    assert _client().get(f"/pakket/{sid}/pdf").status_code == 503


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
