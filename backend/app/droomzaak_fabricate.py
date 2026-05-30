"""Demo fabrication for the warehouse (Supabase/DataGateway) tools ONLY.

TEMPORARY. When `settings.DROOMZAAK_DEV_FABRICATE` is on and the DataGateway is
unavailable, the three Postgres-backed tools (peer_benchmarks_statbel, score_locations,
rent_benchmark) return plausible, **clearly-labelled** demo data instead of the honest
{error, hint} envelope — so the chapter flow can be exercised end-to-end before
Supabase is wired. Native tools (OSM, geocode, web_search) and the LLM tools
are unaffected: they run for real.

permit_checklist_for and subsidies_for are config-file tools (YAML-backed) — they always
have real data and therefore have NO fabricate fallback.

Each fabricated payload mirrors the shape its real handler returns (same keys including
nis9_code), plus two marker keys: `_fabricated: True` and a Dutch `_note_nl`, so the
debug overlay can tell it apart. Removing the flag (or wiring the gateway) restores
honest behaviour with no other changes.

Shape contract (must stay in sync with droomzaak_tools.py handlers):
  peer_benchmarks  → rows.vat, rows.starters_by_year, rows.bankruptcies_by_year;
                      summary keys: active_count_latest, growth_3y_pct,
                      bankruptcies_latest, bankruptcies_latest_year,
                      starters_recent, stops_recent, scope_note
  score_locations  → ranked items have: nis9_code, sector_id (= nis9_code),
                      sector_name_nl, wijk_nl, score, rank
  rent_benchmark   → nis9_code (not sector_id), property_type_used, match_level,
                      year, n_transactions, median_sale_eur, p25_sale_eur,
                      p75_sale_eur, iqr_eur, low_sample_warning, data_available,
                      label_nl, proxy_caveat_nl
"""

from __future__ import annotations

from typing import Any

_NOTE = "DEMO: verzonnen Supabase-data (warehouse nog niet aangesloten) — niet als echt behandelen."


def _wrap(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "_fabricated": True, "_note_nl": _NOTE}


# ── peer_benchmarks_statbel ───────────────────────────────────────────────────

def peer_benchmarks(nace_code: str, refnis: str) -> dict[str, Any]:
    """Mirrors the new rows dict shape: rows.vat / rows.starters_by_year / rows.bankruptcies_by_year."""
    vat = [{"active_count": 1042, "vat_starts": 87, "vat_stops": 74,
             "scope": "gent_arrondissement"}]
    starters_by_year = [
        {"year": 2025, "n_first_start": 3590, "n_restart": 412, "n_stop": -3705, "n_eop": 424800},
        {"year": 2024, "n_first_start": 3210, "n_restart": 390, "n_stop": -3420, "n_eop": 414500},
        {"year": 2023, "n_first_start": 3050, "n_restart": 370, "n_stop": -3250, "n_eop": 413200},
    ]
    bankruptcies_by_year = [
        {"year": 2025, "n_bankruptcies": 13},
        {"year": 2024, "n_bankruptcies": 11},
        {"year": 2023, "n_bankruptcies": 9},
    ]
    rows = {
        "vat": vat,
        "starters_by_year": starters_by_year,
        "bankruptcies_by_year": bankruptcies_by_year,
    }
    # Derive nace2/nace4 suffix for scope_note
    n5 = nace_code.replace(".", "").replace(" ", "")
    n2 = n5[:2] if len(n5) >= 2 else n5
    n4 = n5[:4] if len(n5) >= 4 else n5
    summary = {
        "active_count_latest":    1042,
        "growth_3y_pct":          2.7,
        "bankruptcies_latest":    13,
        "bankruptcies_latest_year": 2025,
        "starters_recent":        4002,   # 3590 + 412
        "stops_recent":           3705,
        "scope_note": (
            f"VAT: Gent arrondissement (nace5); "
            f"starters/stops/growth: Vlaanderen (nace2 {n2}); "
            f"faillissementen: België (nace4 {n4})"
        ),
    }
    return _wrap({"nace_code": nace_code, "refnis": refnis, "rows": rows, "summary": summary})


# ── score_locations ───────────────────────────────────────────────────────────

def score_locations(weights: dict, top_n: int) -> dict[str, Any]:
    """Ranked items include both nis9_code and sector_id (alias) per new shape."""
    base = [
        {"nis9_code": "44021A35K", "sector_id": "44021A35K",
         "sector_name_nl": "Station Gent-Sint-Pieters", "wijk_nl": "Stationsbuurt-Noord",
         "score": 0.7607},
        {"nis9_code": "44021G00K", "sector_id": "44021G00K",
         "sector_name_nl": "Centrum Ledeberg", "wijk_nl": "Ledeberg",
         "score": 0.7319},
        {"nis9_code": "44021A23K", "sector_id": "44021A23K",
         "sector_name_nl": "Koning Albertpark", "wijk_nl": "Binnenstad",
         "score": 0.7093},
        {"nis9_code": "44021B44K", "sector_id": "44021B44K",
         "sector_name_nl": "Zone Nieuw Gent", "wijk_nl": "Nieuw Gent - Uz",
         "score": 0.6955},
        {"nis9_code": "44021B33K", "sector_id": "44021B33K",
         "sector_name_nl": "Sterre", "wijk_nl": "Stationsbuurt-Zuid",
         "score": 0.6868},
    ]
    ranked = base[: max(1, top_n)]
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return _wrap({
        "dataset_id": "score-locations-DEMO",
        "ranked": ranked,
        "formula_label_nl": (
            "Demografische match + transit − concurrentie − huurproxy − verstoring "
            "(min-max genormaliseerd per sector; leegstand weggevallen — geen bron)"
        ),
    })


# ── rent_benchmark ────────────────────────────────────────────────────────────

def rent_benchmark(nis9_code: str | None, property_type: str) -> dict[str, Any]:
    """Uses new key names: nis9_code (not sector_id), median_sale_eur (not median_eur_per_m2)."""
    code = nis9_code or "44021A20K"
    return _wrap({
        "nis9_code":           code,
        "property_type_used":  property_type or "Appartementen",
        "match_level":         "target",
        "year":                2024,
        "n_transactions":      108,
        "median_sale_eur":     255000,
        "p25_sale_eur":        215000,
        "p75_sale_eur":        335000,
        "iqr_eur":             120000,
        "low_sample_warning":  False,
        "data_available":      True,
        "label_nl":            f"Mediane verkoopprijs {property_type or 'Appartementen'} (2024, sector proxy)",
        "proxy_caveat_nl": (
            "Dit zijn RESIDENTIËLE verkoopprijzen (€ totaal, NIET €/m², NIET huurprijs). "
            "Gebruikt als locatiekostproxy — geen commercieel vastgoedcijfer."
        ),
    })
