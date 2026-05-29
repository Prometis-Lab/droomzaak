# Droomzaak — Open-Data Shortlist & Build Plan (Ghent)

_Hackathon: Hackers & Ravers, Sat 2026-05-30, Wintercircus. Product: a five-chapter, dream-first journey that turns one sentence ("a small vegan bistro near Vrijdagmarkt") into a printable Droomzaak-pakket. See the PRD at [`../../docs/superpowers/specs/2026-05-28-droomzaak-prd.md`](../../docs/superpowers/specs/2026-05-28-droomzaak-prd.md)._

**This rewrite (2026-05-29) traces the product backwards: from the PDF's claims → the 5 chapters' questions → the data/tools each answer needs → what we load, curate, download, or proxy.** It is research-verified — five parallel web-research passes confirmed exact URLs, formats, licences, and Ghent granularity for every "needs fetch" item, and corrected three PRD assumptions (see [§9 PRD corrections](#9-prd-corrections-from-research)). Constraint applied throughout: **Ghent only, fetchable today, no paywall, no signup-agreement.**

For the per-source ingestion contract (canonical tables, cadences) see [`phase1_gent_entrepreneur.md`](phase1_gent_entrepreneur.md). For on-disk state see [`../HANDOVER.md`](../HANDOVER.md) §"Droomzaak data prep".

---

## 0. Mental model — three kinds of "data"

The agent reasons over three distinct things; conflating them is the main planning error to avoid.

| Kind | What it is | Where it lives | Examples |
|---|---|---|---|
| **A. Analytical tables** | Numbers the agent queries to back a claim | Postgres `droomzaak` schema, behind **Soda Straw** | demographics, KBO peers, Belfirst financials, bankruptcies, sale-price-per-sector, footfall composite |
| **B. Curated config** | Rules & links, not a dataset — hand-authored, deterministic, demo-safe | YAML/JSON in repo (loaded into Postgres or read directly) | `permit_rules`, `subsidies`, `legal_form` facts, NACE-BEL reference |
| **C. Live tool calls** | Fetched per-request, never pre-stored | External APIs via agent tools | OSM Overpass, Google Places search, Street View, OpenRouteService isochrones, Tavily `web_search` |

Map rendering stays on Map Pilot's existing DuckDB + cached GeoJSON (Tier-1 RENDER) — **never** the agent's reasoning path. Soda Straw is the ingress for **A** only.

Tiering (from the brief): **T1** = on disk or one-command fetch, build for real · **T2** = real but needs a slice/fetch job, cache once · **T3** = mention only, stubbed in UI with citation. All spatial joins on **NIS9 statistical sectors**; secondary on the **25 stadswijken**.

---

## 1. The five chapters — question → claim → data/tool → proxy → status

Each chapter lists the concrete questions the agent must answer, the **claim** the package makes, what backs it, and the proxy fallback where no direct data exists.

> **The engine is generic — nothing here is hardcoded per persona.** The five chapters run the same tools (`extract_dream_profile → score_locations → permit_checklist_for → …`) for *any* `dream_profile` the agent extracts. Lisa (vegan bistro), Sofie (bookstore) and the consultant are **finetuned demo paths we rehearse**, not branches of canned logic — a jury member can pick a different address/sector and Chapter 3+ re-runs (PRD §6.3 #6). "Curated config" below means the **rules + official links the agent reasons over**, not pre-written answers; the agent still composes every response live from the profile + the data.

### Chapter 1 — *Droom* · tool `extract_dream_profile`

| Question | Claim in package | Backing | Status |
|---|---|---|---|
| What is this person building? | `dream_profile` {sector, nace[], sub_type, vibe, anchor{wijk,lat,lon}, scale{seats/m²}, partners, budget, **attributes{}**, confidence/field} | LLM classification grounded by **NACE-BEL ref** (code↔label↔synonyms, from KBO `code.csv`); anchor resolved via the **inherited Prometis geocoder** (address→lat/lon+**NIS9**) with Nominatim `geocode` fallback for vague place-names; follow-up questions driven by **`sector_attributes`** (§4d) | **Build** |

`nace[]` is a list (one concept can span codes, e.g. 56.101 + 56.102). `confidence/field` lets the agent ask a clarifying question instead of guessing when extraction is uncertain. NACE-mapping risk on fuzzy sentences → mitigated by the synonyms column ("vegan bistro" → 56.101) + the confidence gate.

**`attributes{}` + the dynamic questionnaire (your "company topology").** The follow-ups aren't a fixed form — they're driven by the **`sector_attributes` taxonomy** (§4d), which lists, per sector, the decision attributes that affect *permits, subsidies, and scoring* (horeca: serves_alcohol none/gegiste/sterke, seating none/indoor/terrace, takeaway_only, frying/hot_kitchen, capacity, renovation, music; retail: food_retail, signage, opening_hours; consultant: home_based, employees…). The agent asks **only the attributes relevant to the recognised NACE that the dream sentence didn't already state** — warm and short, but guaranteeing every permit-deciding fact is captured before Chapter 4. **Crucially, this is the same taxonomy Chapter 4's `applies_when` rules key off** — one source of truth links elicitation (Ch1) to branching (Ch4).

**Anchor + geocoding (resolves the §10 geocoding question).** The **inherited `prometis_toolkit` geocoder** (`inherited/`, gitignored) turns a Belgian address → lat/lon + full NIS hierarchy (incl. **NIS9 sector**) + confidence, using bundled BeSt centroids (4.8M buildings). Use it for the Ch1 anchor, the Ch3 candidate addresses, and the Ch5 chosen address — and to geocode KBO + Belfirst (§2). Vague place-names ("Vrijdagmarkt") fall back to the existing Nominatim `geocode` tool.

### Chapter 2 — *Niche* · tools `peer_benchmarks_statbel`, `query_osm`, `places_search`, `search_datasets`

| Question | Claim | Backing | Status |
|---|---|---|---|
| How many like me exist in Gent? Where? | "13 plant-based zaken, here on the map" | **KBO entities flat** (Ghent slice, NACE-filtered) ON DISK + curated `koop-lokaal-horeca/winkels`, `cafes-gent` ON DISK (T7); cross-validate LIVE with **OSM Overpass** + **Google Places search** (KBO = registered seat, not trading address) | **Build** — data on disk; geocoding needed |
| Is the niche growing? | "+27% over 3y" | **Statbel `TF_STARTERS_45`** (oprichtingen/stopzettingen × NACE) — ⚠️ **REGION-only**, so this is a *Flanders* trend, label it honestly | **T2 fetch** |
| Do they go bankrupt? | "4 faillissementen in 2024 vs 6 in 2023" | **Statbel `TF_BANKRUPTCIES`** — ✅ municipality (44021) × 4-digit NACE + company lifespan | **T2 fetch** |
| How are peers doing financially? | "median turnover €X, margin Y%" for the cohort | **Belfirst jaarrekeningen Gent** ON DISK (27,686 cos: Omzet, EBITDA, Solvency, margin) — **the real peer-performance source** (PRD says Statbel; Belfirst is stronger). ⚠️ proprietary → aggregates/client-side only | **Build** — on disk; licence boundary is a [user decision](#10-decisions-needed-from-you) |
| How saturated is my size class? | "N firms my size in this NACE in Gent" | **Statbel `TF_VAT_NACE_EMPL`** — ✅ municipality × 5-digit NACE × employee size class (best stock-of-peers file) | **T2 fetch** |

### Chapter 3 — *Waar* · tools `score_locations`, `nearest_features`, `spatial_count`, `rent_benchmark`, (`places_popular_times` → see correction)

`score_locations` is a weighted SQL join over sector-keyed tables. Each scoring dimension = a sub-question:

| Dimension (sub-question) | Direct data | Status | Proxy chain (see [§6](#6-proxy-strategy-the-hard-signals)) |
|---|---|---|---|
| Do my customers live/move here? | demographics (pop age/gender, fiscal income, cars/hh) ON DISK | **Build** | + student density, daytime/jobs population |
| Will people walk past? (**footfall**) | druktemeting 4 spots + parking + bike occupancy ON DISK | **Build + T2** | composite: De Lijn stop-frequency + NMBS boardings + Telraam + Donkey + parking/bike + Places density |
| How much competition? | `spatial_count` of NACE 56.101/56.102 within 500 m (KBO) | **Build** | OSM + Places cross-check |
| Is there a free unit? (**vacancy**) | ❌ no open Gent retail register | **Gap → proxy only** | OSM `shop=*`/vacant + invert koop-lokaal density; KBO churn (academic-history en route) |
| Walkable/transit? | **De Lijn GTFS** (stops+freq) + cycling infra | **T2 fetch** | isochrones (OpenRouteService) |
| What does space cost? (**rent**) | ❌ no open commercial rent in BE | **Gap → proxy only** | **Statbel `TF_IMMO_SECTOR`** sale-€/sector (Q10–Q90, NIS9) + Belfirst neighbour cost structure |
| Construction disruption? | inname openbaar domein + omleidingen ON DISK; **GIPOD** WFS | **Build + T2** | sum of active windows per sector |

### Chapter 4 — *Vergunningen & geld* · tools `permit_checklist_for`, `subsidies_for`, `legal_form_advisor`

**Permits half** — this is a **RULES problem, not a dataset problem.** What the agent needs is (1) the conditional rule logic and (2) verified official deep-links + cost/lead-time. Both → curated `permit_rules` config (see [§4](#4-curated-config-section-b--not-datasets)). Optional supporting evidence layer: granted environmental permits near the address from the **Flemish Omgevingsloket WFS** (open).

| Question | Claim | Backing | Status |
|---|---|---|---|
| What do I legally need to open THIS here? | conditional checklist w/ deep-link, cost, lead-time per item | `permit_rules` curated YAML (horeca-attest, FAVV, drank gegiste/sterke, omgevings klasse 2/3, terras, Unisono, brandweer, EPB, KBO/BTW baseline) — **all official URLs + facts verified** | **Curate** |
| Has a permit been granted nearby? | "3 horeca permits on this street recently" (evidence) | **Omgevingsvergunningen IIOA + kleinhandel** — ✅ **ALREADY ON DISK** (T7 `vlaanderen-omgevingsloket/`, GeoPackage 2026-05-19) | **clip to Gent** |
| May I open this type here at all? (zoning) | "this is woongebied / KMO-zone" | **Gewestplan** + **gemeentelijke RUP (DSI)** WFS/download, open | **T2 fetch** |

**Money half** — a curated `subsidies` table + eligibility logic. **VLAIO subsidiedatabank is WAF-blocked (403 to any scraper) → do NOT scrape; hand-pick ~18–22 grants as static JSON** (~3–4 h). All schemes verified with 2026 amounts/eligibility/URL.

| Question | Claim | Backing | Status |
|---|---|---|---|
| What money is on the table for me? | shortlist w/ eligibility ticks + amounts + links | curated `subsidies.json`: Startlening, Cofinanciering(+), Winwinlening, Vriendenaandeel, KMO-portefeuille, Ecologiepremie+, tax-shelter starters, BV-vrijstelling, Stad Gent starterscontract/handelsinitiatieven/energiepremies, OOG | **Curate** |

⚠️ **Honesty flags baked into the data:** most Stad Gent premies were **cancelled for 2026** (renovatie handelspand ended 22 Sep 2025); KMO-portefeuille *advies* narrowed to cybersecurity-only from 1 Feb 2026. Encode a `status: active|ended_2025` field so cancelled schemes render greyed-out — this makes the demo look *current*, not stale.

### Chapter 5 — *Pakket* · tools `legal_form_advisor`, `generate_dream_narrative`, `compose_package`

| Question | Claim | Backing | Status |
|---|---|---|---|
| Eenmanszaak or BV/SRL? | one-card recommendation + ~€1,500 notary note | pure decision tree (partners, liability, revenue, budget) + small verified fact ref (notary cost, no min-capital but "toereikend aanvangsvermogen") | **Curate (tiny)** |
| What's my Tuesday morning? | "open 8u, ~80 covers, ~€280k/yr, take-home/mo" | composes Ch2 (Belfirst cohort revenue/margin) + Ch3 (footfall proxy → covers, rent) — **present as a labelled scenario with visible assumptions, conservative** | **Build (compose)** |
| Address card image | Street View thumb | **Google Street View Static API** (1 call/session, ~$7/1k) | **Live tool** |

---

## 2. Postgres `droomzaak` schema — the load list (Section A data)

This is the exact set of analytical tables to stand up Friday behind Soda Straw. Source column says where each comes from and whether it's already local.

| Canonical table | Feeds | Source(s) | On disk? | Granularity | Notes |
|---|---|---|---|---|---|
| `geo_admin_units` | joins, map | statistische-sectoren-gent, stadswijken-gent | ✅ wired | sector + wijk | base geometry |
| `nace_ref` | `extract_dream_profile` | KBO `code.csv` + synonyms | ✅ (curate synonyms) | code | tiny |
| `demographics_sector_annual` | `score_locations` | statbel population + cars/hh + FOD fiscal income | ✅ wired | sector × year | purchasing power + customer profile |
| `business_registry` (Gent) | Ch2 count, `spatial_count` | **KBO entities flat** (postcode 9000–9052) | ✅ on disk (T7) | per entity | geocode via **inherited Prometis geocoder** → lat/lon + **NIS9** |
| `business_financials` (Gent) | `peer_benchmarks_statbel`, Tuesday sim | **Belfirst** jaarrekeningen | ✅ on disk | per company | proprietary → aggregates only; geocode address-strings via same toolkit |
| `peer_demography_nace` | `peer_benchmarks_statbel` | Statbel `TF_VAT_NACE_EMPL` (muni×5-digit) + `TF_BANKRUPTCIES` (muni×4-digit) + `TF_STARTERS_45` (region) | ❌ **T2 fetch** | mixed (see flags) | starters is region-only — label |
| `housing_price_sector` | `rent_benchmark` (proxy) | Statbel `TF_IMMO_SECTOR` (NIS9) | ❌ **T2 fetch** | sector × nature × year | **sale €, not rent** — proxy |
| `footfall_sector` (composite) | `score_locations` | De Lijn GTFS + NMBS boardings + druktemeting + parking/bike + (Telraam) | partial | sector score 0–1 | see [§6](#6-proxy-strategy-the-hard-signals) |
| `transit_access_sector` | `score_locations` | De Lijn GTFS stop-frequency | ❌ **T2 fetch** | sector | departures/week aggregated |
| `disruption_events` | `score_locations`, Ch3 filter | inname-openbaar-domein + omleidingen ON DISK + **GIPOD** WFS | partial | point+window | sum durations/sector |
| `permits_events` (evidence) | `permit_checklist_for` evidence | **Omgevingsloket** IIOA + kleinhandel + stedenbouw | ✅ **on disk** (T7 `vlaanderen-omgevingsloket`, GPKG 2026-05-19) | per permit | just clip to Gent (1.8 GB Flanders-wide) |
| `zoning` | Ch4 "may I open here" | **Gewestplan + RUP DSI** WFS | ❌ **T2 fetch** | polygon | bestemmingscategorie |
| `demand_proxies` | `score_locations` | kotzones + bloklocaties + toeristische-attracties + POI + buurtmonitor jobs/students | partial | mixed | demand-side weighting |
| `permit_rules` | `permit_checklist_for` | curated YAML → table | curate | rule rows | [§4](#4-curated-config-section-b--not-datasets) |
| `subsidies` | `subsidies_for` | curated JSON → table | curate | per scheme | [§4](#4-curated-config-section-b--not-datasets) |

**Friday load job:** extend the planned `dump_duckdb_to_postgres.py` to (1) copy the on-disk canonical layers, (2) load the Statbel/GIPOD/WFS T2 fetches from [§5](#5-download-now-friday--exact-urls), (3) **geocode KBO + Belfirst with the inherited Prometis toolkit → lat/lon + NIS9, then aggregate per sector**, (4) ingest the curated config files (`permit_rules`, `subsidies`, `sector_attributes`, `nace_ref`). Then register the DB as a Soda Straw source and smoke-test each tool. The toolkit's `geo_core` also supplies NIS9 sector centroids for `score_locations` distance maths.

---

## 3. Agent tools — new + reused, mapped to data

| Tool | New? | Backed by | Kind |
|---|---|---|---|
| `extract_dream_profile` | new | LLM + `nace_ref` + gazetteer | B+LLM |
| `peer_benchmarks_statbel` | new | Postgres: `peer_demography_nace` + `business_financials` | A |
| `places_search` | new | Google Places (New) searchText/searchNearby | C |
| ~~`places_popular_times`~~ | new | ❌ **not available** — replace, see [§9](#9-prd-corrections-from-research) | C |
| `score_locations` | new | Postgres weighted join over demographics/competition/footfall/transit/price/vacancy-proxy/disruption | A |
| `rent_benchmark` | new | Postgres `housing_price_sector` (sale-€ proxy) | A |
| `permit_checklist_for` | new | `permit_rules` config + optional `permits_events` | B |
| `subsidies_for` | new | `subsidies` config + eligibility logic | B |
| `legal_form_advisor` | new | decision tree + fact ref | B |
| `generate_dream_narrative` | new | LLM + style guide | LLM |
| `compose_package` / `set_chapter_state` | new | pure Python / validation | — |
| `web_search` (Tavily) | new | **Tavily API** (key available) — domain-biased to official sources | C |
| `apply_map_actions`, `set_layer_filter`, `spatial_count`, `nearest_features`, `geocode`, `query_osm`, `isochrone`, `route`, `aggregate_features`, `features_within_radius` | reused | Map Pilot existing | A/C |

**`web_search` (Tavily) — fallback knowledge tool.** A thin tool over the Tavily API (key already available; a colleague wires it into the agent loop alongside the Soda Straw client). Bias queries to official domains (`stad.gent`, `favv-afsca.be`, `vlaanderen.be`, `vlaio.be`, `pmv.eu`, `unisono.be`). **Role: long-tail fallback, not primary.** The rehearsed chapters answer entirely from curated config + Postgres (deterministic); `web_search` catches off-script jury questions ("Alcohol na 21u?", "Schoolstraat-zone?") and lets the agent cite a live official page when config doesn't cover it. It surfaces links, never acts (consistent with the "deep-links only, no booking" stance). Curated config is the engine; `web_search` is the safety net — never the reverse during a timed demo.

---

## 4. Curated config (Section B — *not* datasets)

These are hand-authored, ship in repo, and are the most demo-critical work because they're deterministic. All facts below are research-verified (2026).

**Form decision: structured YAML/JSON — not scraped-markdown, not PDFs-in-a-vector-DB.** The logic is conditional and finite (~10 permits, ~20 grants), e.g. "if frying → omgevings rubriek 45.4.d", "if serves spirits → +college machtiging". That's a decision table the agent reasons over, not prose to retrieve. A vector DB of permit PDFs would be slower, non-deterministic, and risks surfacing the wrong municipality's page on stage. The long-tail nuance Q&A is handled by `web_search` (Tavily, §3), so there is **no PDF-ingest / vector pipeline for the hackathon**. (Optional, only if time: a few official pages distilled to short markdown briefs given in-context — but Tavily makes this largely unnecessary.)

**How we build it (Friday, one-shot → frozen artifact, never runtime scraping):**
1. `WebFetch` the ~15 official pages that serve clean HTML (`stad.gent`, `favv-afsca.be`, `pmv.eu`, `fin.belgium.be`, `vlaanderen.be`, `unisono.be`) → LLM drafts rows to the schema → **human verifies** the trigger logic + `depends_on` order.
2. **For dynamic / WAF-blocked sources that refuse server-side fetch — notably VLAIO (`vlaio.be`, 403) and the interactive VLAREM-wegwijzer wizard — drive a real browser via the Claude Code Chrome extension** (`mcp__claude-in-chrome__*`): it executes JS and renders the page, getting past the bot-wall that blocks `WebFetch`, and reads the rendered content into the same drafting step.
3. ~90% of the facts are already captured in the §4a/§4b tables, so step 1–2 are mostly **grounding + gap-fill** (esp. the VLAIO entries), not a from-scratch crawl. Every row carries a `source_url`.

### 4a. `permit_rules.yaml` (horeca branch + retail/consultant scaffolds)

Each rule: `{permit, applies_when (NACE × attributes), official_url, explainer, cost, lead_time_days, depends_on}`. Verified deep-links + facts:

| Permit | Official URL | Trigger | Cost | Lead time |
|---|---|---|---|---|
| **Horeca-attest** (umbrella) | `stad.gent/.../horeca/horeca-attest` | any horeca | none published | **≥30 werkdagen** (≥45 if >100 m²) |
| FAVV toelating | `favv-afsca.be/nl/themas/starters/...` | food handling | reg. free; heffing starter ~€100.58/y (2025) | LCE 30 werkdagen |
| Drankvergunning gegiste | `stad.gent/.../drankvergunning/...vaste-drankgelegenheid` | beer/wine | none published | 30 (45) werkdagen |
| Sterkedrankvergunning | same page | spirits/cocktails → +college machtiging | none published | 30/45 + strafregister 596 |
| Omgevingsvergunning (milieu) | VLAREM-wegwijzer `vlaremwegwijzer.navigator.emis.vito.be` | frying → **rubriek 45.4.d**; cooling ≥5kW → **16.3.2°** → melding (kl.3) or vergunning (kl.2) | Vlaanderen-set | melding ack / ~105 d kl.2 |
| Terrasvergunning | `stad.gent/.../terrassen-gent/...openbaar-domein` · apply `innames.stad.gent` | terrace on public domain (needs horeca-attest first; 9-yr term) | annual belasting (m²/zone) | 30 d from site visit |
| Unisono (SABAM+billijke verg.) | `unisono.be` + simulator | public music | calculator (m²/type) | instant declare |
| Brandveiligheidsattest | via horeca-attest; rules `brandweerzonecentrum.be` | ≥100 m² | none | folded into 45-werkdagen |
| EPB | `vlaanderen.be/epb-eisen` | renovation needing OMV | private reporter fee | tied to OMV |
| KBO + BTW + soc.fonds | `economie.fgov.be/.../te-ondernemen-stappen-bij-een` | every business | KBO loket ~€105.50; BTW free via MyMinfin | same day |

Critical-path order (hero): soc.verzekeringsfonds → KBO → BTW → FAVV → drank → omgevings melding/vergunning → **horeca-attest** (umbrella) → terras → Unisono → EPB. Where cost is calculator-based (Unisono, terras tax), render "via official simulator" — do **not** invent a number.

### 4b. `subsidies.json` (~18–22 grants, hand-picked)

Verified schemes with 2026 amounts/eligibility/URL — full table in the research notes; encode `status`, `scope` (Gent/Flanders/federal), `need_type` (loan/equity/training/eco/premises), and eligibility flags (`age_months`, `has_employees`, `legal_form≠vzw`). Core set: Startlening (€100k, 3%), Cofinanciering(+) (€350k/€700k), Winwinlening (€300k borrower), Vriendenaandeel, KMO-portefeuille (30%, €7.5k/y — flag advies reform), Ecologiepremie+, Tax-shelter starters (45/30%), BV-vrijstelling doorstorting, Stad Gent starterscontract + handelsinitiatieven + energiepremies panden, OOG (free advice). Show the cancelled handelspand premie as `ended_2025`.

### 4c. `legal_form` + `nace_ref`

Decision-tree facts (BV/SRL ~€1,500 notary, no min-capital; eenmanszaak cheap, unlimited liability) + NACE-BEL synonyms map from KBO `code.csv`.

### 4d. `sector_attributes.yaml` — the "company topology" (drives questions AND permits)

Per sector/NACE family, the **decision attributes** that affect permits, subsidies, and scoring — the single source of truth shared by Chapter 1 (which follow-up questions to ask) and Chapter 4 (`applies_when` branching). Example:

```yaml
horeca:                      # NACE 56.*
  serves_alcohol: [none, gegiste, sterke]   # → drank/sterkedrank vergunning + strafregister
  seating: [none, indoor, terrace]          # terrace → terrasvergunning + inname OD
  takeaway_only: bool                        # flips FAVV class + drops terras/seating perms
  hot_kitchen_frying: bool                   # → omgevings rubriek 45.4.d
  capacity_seats: int                        # ≥100 m²/capacity → brandweer track
  renovation: bool                           # → EPB + possible omgevingsvergunning
  music: bool                                # → Unisono
retail:                      # NACE 47.*
  food_retail: bool                          # → FAVV
  signage: bool; opening_hours: enum; alcohol_offsale: bool
consultant:                  # NACE 70/74.*
  home_based: bool; employees: int           # mostly KBO/BTW baseline only
```

The agent asks only the attributes for the recognised NACE that the dream sentence didn't already fill. Adding a new sector = adding one block here → both elicitation and permit branching work for it (keeps the engine generic).

---

## 5. Download NOW (Friday) — exact URLs

All free, no signup, no agreement, fetchable today. Two need a human-created token (flagged 🔑).

**Statbel (peer benchmarks + rent proxy):**
- Firm stock: `https://statbel.fgov.be/sites/default/files/files/opendata/btw-plichtige/werknemersklasse/TF_VAT_NACE_EMPL_2023.xlsx` — **muni × 5-digit NACE × size**
- Bankruptcies: `https://statbel.fgov.be/sites/default/files/files/opendata/BRI_Nace/TF_BANKRUPTCIES%282025%29.xlsx` — **muni × 4-digit NACE**
- Oprichtingen: `https://statbel.fgov.be/sites/default/files/files/opendata/starter45/TF_STARTERS_45.xlsx` — region-only (overlay)
- Sale price/sector (rent proxy): `https://statbel.fgov.be/sites/default/files/files/opendata/Immo%20sector/TF_IMMO_SECTOR.xlsx` — **NIS9 sector**

**Geo / permits / zoning (Mercator WFS — clip to NIS 44021):**
- Omgevingsvergunningen IIOA + kleinhandel — ✅ **already on T7** (`vlaanderen-omgevingsloket/lu_omv_{iioa,kh,gd}_v2/2026-05-19/*.gpkg`); WFS below only for a fresher refresh: `https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/ogc/features/v1/collections/lu:lu_omv_iioa_v2`
- Gewestplan (zoning SHP) — **still fetch**: `https://datasets.omgeving.vlaanderen.be/be.vlaanderen.omgeving.distribution.geo.de1d2b77-fc8f-4032-b007-eb6c42686efe.lu_gwp_vector.zip`
- RUP contouren (DSI): `https://data.gov.be/nl/datasets/5107ff1c-b72e-4495-a671-2b83e4a21343`
- GIPOD road-works: WFS GetFeature, Gent bbox ≈ (3.65–3.85 E, 51.00–51.13 N) EPSG:4326 (GetCapabilities first)

**Mobility / footfall composite:**
- De Lijn GTFS (no signup mirror): `https://gtfs.irail.be/de-lijn/de_lijn-gtfs.zip`
- NMBS station boardings (CC0): `https://github.com/iRail/stations` → `embarkment_statistics.csv` (Gent-Sint-Pieters, Gent-Dampoort)
- Donkey Republic GBFS: `https://stables.donkey.bike/api/public/gbfs/3.0/donkey_gh/gbfs.json`
- 🔑 Telraam (per-street ped/bike): `https://telraam-api.net/v1` — needs a **free account + API token** (`X-Api-Key`); coverage patchy/residential-skewed → use to *calibrate*, not drive

**Stad Gent ODS (export `…/api/explore/v2.1/catalog/datasets/<slug>/exports/{geojson,csv}`):**
- Promote per HANDOVER Tier-1: `cafes-gent`, `koop-lokaal-horeca` (263), `koop-lokaal-winkels` (349), `sfeergebieden-puur-gent`, `druktemeting-*` (2022–23), `recente-bezetting-parking-vrijdagmarkt`, `bedrijvencentra-gent`, `bevolkingsaantal-per-wijk-per-jaar-gent`
- New demand-proxy adds: `kotzones-gent` (20), `bloklocaties-gent` (48), `toeristische-attracties-visit-gent` (393), `points-of-interest-poi-stam-gent` (119), `drukte-overpoortstraat-gent` (if not already held)
- Subsidy seed (correct manually — stale): `subsidies-ondernemen-kopie`

**On disk already (no fetch):** KBO entities flat (geocode needed), Belfirst jaarrekeningen, demographics/income/cars, real-estate transactions, inname/omleidingen, druktemeting, parking/bike occupancy, fietstelpalen.

🔑 **Human-only actions tonight:** (1) Telraam account+token, (2) optional UiTdatabank client key, (3) Google Maps API key (Places + Street View, billing on).

---

## 6. Proxy strategy — the hard signals

The user's explicit ask: where there's no direct data, build a proxy chain. Four signals have no clean open source for Ghent.

### Footfall (no per-street city-wide source)
Composite `footfall_sector` score, normalized 0–1 per sector:
`0.40·transit_access + 0.25·station_boardings + 0.25·telraam_measured + 0.10·micromobility`
(if no Telraam token: fold its weight into transit_access). Inputs: De Lijn departures/stop, NMBS boardings (2 anchors), Telraam segments, Donkey hub turnover. **Calibrate the weights against the on-disk druktemeting (Korenmarkt/Kouter/Veldstraat) + fietstelpaal ground-truth** — regress proxy vs observed, sanity-check. Episodic modifier: inname-evenementen (on disk) / UiTdatabank events. Ambient baseline: residential pop density + daytime/jobs population.

### Rent (no open commercial rent in BE)
1. **Statbel `TF_IMMO_SECTOR`** sale-€/sector (Q10–Q90) → relative cost gradient. 2. commercial vastgoedtransacties €/m² (on disk) → implied. 3. Belfirst neighbour cost structure → "what rent can businesses here sustain". Label every output a proxy; never quote per-address.

### Vacancy (no open Ghent retail register; Locatus paywalled)
1. OSM `shop=*` / `disused:shop` / `vacant` tags (via `query_osm`). 2. invert koop-lokaal shop-density — gaps along a commercial street. 3. KBO churn (deregistered address, none re-registered) once academic-history geocoded parquet lands. 4. low recent commercial transaction count (on disk). Optional city-KPI: provincies.incijfers Detailhandel (needs key, gemeente-only).

### Demand for a concept (e.g. vegan)
1. target-demographic density (young adults, higher income). 2. **student density** — `kotzones-gent` + buurtmonitor student indicators (Ghent ~80k students). 3. **daytime/workplace population** — buurtmonitor jobs-per-wijk + Statbel jobs-by-workplace (gemeente). 4. tourism/visitor proximity — `toeristische-attracties-visit-gent`. 5. peer success (Belfirst margins) + count growth. 6. spend-by-category — Statbel HBS (region-only constant).

---

## 7. Data access & infra — Soda Straw, the gateway, the failover

_The data/tool layer is our focus; a colleague wires the Soda Straw MCP client + Tavily into the agent loop. This section is the contract for how they connect._

### 7.1 The three access paths

- **Analytical (A) → Soda Straw → Postgres:** every `peer_benchmarks_statbel`, `score_locations`, `rent_benchmark`, `permit_checklist_for`, `subsidies_for` call. This is the demo's "every datum routes through Soda Straw" claim — the debug overlay shows it.
- **Live tools (C, behaviour not data) → native:** `query_osm` (Overpass `https://overpass-api.de/api/interpreter`, set User-Agent + bbox + cache between runs), `places_search` (Google Places New), Street View Static, `isochrone` (OpenRouteService), `web_search` (Tavily). These do **not** go through Soda Straw.
- **Map render → DuckDB + cached GeoJSON**, untouched. Never the agent's reasoning path.

### 7.2 How the map agent reaches Soda Straw (runtime, not dev-only)

Soda Straw is a **runtime dependency** for analytical calls — it's the company launching *at* this hackathon, and the pitch is scored on routing analytical calls through it. The browser never speaks MCP:

```
Browser (MapLibre + chat) ──HTTP /api/agent/chat──► FastAPI backend
                                                        │  agent_loop.py tool dispatch
                          peer_benchmarks / score_locations / rent_benchmark / ...
                                                        │  (thin wrappers call)
                                                 MCP client session
                                   (python `mcp` SDK · streamable-HTTP · bearer token)
                                                        │
                                            Soda Straw MCP ──► Postgres
```

- **One MCP session, opened at backend startup** (FastAPI lifespan), reused for every request. Call `list_tools()` once at startup to discover Soda Straw's tool shape (likely a generic `query(straw, sql)` — **confirm by calling it; it's not publicly documented**) and build wrappers around it.
- **Auth:** mint **one service/agent token** (`agent_*` scoped identity) with read on the Postgres straw; all calls run under it. No per-end-user OAuth.
- **Tonight (self-serve, no credit card):** sign up at `sodastraw.ai/trial/start`, connect Postgres as a straw, mint the token, run `list_tools()`. Everything downstream depends on that one call.

### 7.3 Failover — the demo safety net

Put a **`DataGateway` interface** in front of analytical access with a feature flag `DATA_BACKEND=soda_straw|postgres_direct` and a direct `asyncpg` pool to the **same** Postgres running the **same** SQL. Soda Straw is primary/default (required + scored); direct-Postgres is break-glass if the day-one hosted service wobbles on stage (PRD risk #1). Wrap Soda Straw calls in a short timeout + circuit-breaker. This also keeps the architecture **swappable** post-hackathon, where Soda Straw's value (governance/audit/per-user access) matters more than in a single-agent demo.

- **Stretch:** wrap Overpass / GIPOD live as small MCP servers behind Soda Straw to make the "everything through Soda Straw" claim literal — only past hour 6.

---

## 8. Persona flip — same data, city's questions

Zero net-new layers; flipped default queries.

| City question | Layers that answer it |
|---|---|
| Where are we under-served for a consumer type? | demographics + KBO competitor density (invert) |
| Which neighbourhoods host financially fragile retail/horeca? | Belfirst Solvency/margin per wijk × NACE |
| Where is commercial vacancy clustering? | vacancy proxy (§6) until a register lands |
| Where to route entrepreneurial support? | subsidieregister past awards + income |
| Which streets need foot-traffic intervention? | footfall composite + sfeergebieden |
| Where is disruption stacking up? | inname + omleidingen + GIPOD, summed per wijk |

---

## 9. PRD corrections from research

1. **`places_popular_times` does not exist** in the official Google Places API (New) — there is no per-venue foot-traffic field. Replace with: (a) **OSM/Places amenity density** as the competition signal, (b) **Places Aggregate API** density counts, or (c) paid **BestTime.app** if budget allows. Drop the "live popular-times footfall" claim; the footfall composite (§6) is the honest substitute.
2. **VLAIO subsidiedatabank can't be fetched server-side** (WAF/403 to httpx/`WebFetch` incl. robots.txt). Two viable build-time routes: hand-pick static JSON (~3–4 h, facts mostly already in §4b), or **read the rendered pages via the Claude Code Chrome extension** (real browser bypasses the bot-wall) — see §4 "How we build it". Either way it's a frozen build artifact, not runtime scraping.
3. **Stad Gent premies largely cancelled for 2026** (renovatie handelspand ended 22 Sep 2025; several eco/starter subsidies stopped 1 Jan 2026) and **KMO-portefeuille advies narrowed to cybersecurity-only** (1 Feb 2026). The PRD's Chapter-4 subsidy examples (renovatiepremie handelspanden as "eligible") are out of date — encode `status` and show cancelled ones greyed-out so the demo reads as current.

---

## 10. Decisions needed from you

- **Belfirst licence boundary** — proprietary, no redistribution. Per-postcode/per-wijk aggregates (median Omzet, solvent vs distressed count) on the dossier feel safe; per-company rows only in the operator's agent panel. Confirm the line before the demo.
- ~~**KBO geocoding path**~~ — **RESOLVED:** use the inherited `prometis_toolkit` geocoder (BeSt-based, bundled centroids, returns lat/lon + NIS9). Geocodes KBO + Belfirst in the Friday load. No decision needed.
- **Telraam token tonight?** — yes/no decides whether footfall has a direct-measure layer or is pure proxy (composite degrades gracefully either way).
- **Footfall proxy vs Google Places density** — given correction #1, confirm we lean on the §6 composite + OSM density rather than any "popular times".
- **T3 stub wording** — Locatus / leegstandsregister / terrasinplantingsplannen / horeca-attesten as "pilot unlocks this" cards with source citation.

---

## 11. Truly-missing (T3 stubs only)

Confirmed absent in open form for Ghent — render as cited placeholders, don't chase before Saturday: per-address commercial **rent**, retail **leegstandsregister** (Locatus paywalled), **terrasinplantingsplannen**, **horeca-attesten/drankvergunningen** as data (they're rules, curated instead), newer **VLOED/passantentellingen** (nothing past 2022–23 is open), **NBB CBSO** (superseded by Belfirst for the demo).

**Partly available after all (validated on disk/index, contra earlier audits):** **Omgevingsvergunningen** (full Flemish Omgevingsloket on T7 — see §2). **FAVV** is *not* fully missing — data.gov.be carries `Codelijst FAVV activiteiten` (food-activity → requirement mapping, useful for `permit_rules`), `Lijst operatoren` (registered food operators), and `Lijst Smileys` (hygiene certs). Worth a 30-min look for the horeca branch. The two Gent subsidy ODS (`subsidies-ondernemen-kopie`, `lijst-van-gesubsidieerde-derden`) are on T7 (stale / spending-register respectively — seed only). `premies-per-gemeente` is **Fluvius energy-premie counts**, not an entrepreneur-subsidy catalogue.

---

_Query the index again: `open-data/portals/<portal>/datasets_index.csv` or DuckDB over `open-data/catalogues/master_index.parquet`. See [`../HANDOVER.md`](../HANDOVER.md) and [`phase1_gent_entrepreneur.md`](phase1_gent_entrepreneur.md)._
