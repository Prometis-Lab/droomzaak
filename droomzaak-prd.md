# Droomzaak — Product Requirements Document

_Status: design-approved, ready for hackathon implementation._
_Author session: 2026-05-28._
_Hackathon: Hackers & Ravers — Saturday 2026-05-30, 10:00–20:00, Wintercircus Ghent. 12-hour build, in-person, AI evaluator → live jury → 3 winners. Required infra: **Soda Straw** MCP. Claude Code supported._
_Repository: a new repo, branched from Map Pilot v2, reusing the existing agent loop, MapLibre canvas, catalogue ingest, and open-data pipeline. This PRD is written in Map Pilot v2 so the design context is colocated with the foundation it builds on._

---

## TL;DR

**Droomzaak** ("dream company") guides aspiring entrepreneurs in Ghent through the wall of decisions and paperwork that follow the first thought of *"I want my own business"* — keeping the *dreaming* alive instead of crushing it. A five-chapter map-anchored journey turns a sentence (*"a small vegan bistro near Vrijdagmarkt"*) into a printable *Droomzaak-pakket*: dream narrative, scored location candidates, niche peer numbers, a sector-branched permit checklist, a subsidy shortlist, a legal-form recommendation, and a clear set of next-step links. The agent does the reading the founder used to do at midnight.

The product is a hackathon-built extension of Map Pilot. It reuses the existing 16-tool LLM agent, the MapLibre canvas, the open-data catalogue, the validation contract, and the chapter-style debug viewer. It adds: a chapter state machine, ~8 new agent tools, a Droomkaart sidebar, a slim chapter rail, and a printable package renderer. All analytical data the agent reasons over is brokered through **Soda Straw**, with a Postgres warehouse loaded from 60+ pre-curated Belgian open datasets behind it. The map keeps rendering from Map Pilot's existing DuckDB + cached GeoJSON layer so panning stays instant.

It addresses the City of Ghent's own RFP: *"one-stop-shop voor startende ondernemers: digitale tool die ondernemers helpt bij locatiekeuze en zaakopstart op basis van relevante stadsdata"*. After the hackathon, Droomzaak is the candidate for that one-stop shop: post-MVP roadmap covers execution flow (form-filing, appointment booking), live real-estate integration, CBSO peer benchmarks, city expansion, and a parallel OOG-advisor surface.

The hackathon-MVP adds ~12 new agent tools on top of Map Pilot's existing 16, a slim chapter rail, a Droomkaart sidebar, and a printable package renderer. Everything else is reused.

---

## 1. Vision & positioning

### 1.1 Vision sentence

> **Droomzaak turns the overwhelm of starting a business in Ghent into a five-chapter map-anchored journey that ends with a printable "dream + plan" — keeping the founder dreaming, not drowning in tabs.**

### 1.2 Primary user

The aspiring first-time founder. Knows the dream (*"I want my own vegan bistro"*), doesn't know what they don't know. Currently bouncing between VLAIO 1700, Stad Gent's ondernemerspaginas, a Liantis blog, Reddit, three open Excel tabs, and Google Maps. Almost everyone has, at some point, been this person.

### 1.3 Secondary users

1. **Stad Gent OOG (Ondersteuningspunt Ondernemers Gent)** as a force-multiplier for their human advisors. Droomzaak *is* the digital arm of the city's one-stop-shop ambition; OOG advisors can see what their founders' Droomzaken contain and pick up from there.
2. **Ondernemingsloketten** (Liantis / Securex / Acerta / Partena / Xerius / Group S / UCM / Eunomia) as the downstream hand-off when the founder is ready to actually register. Droomzaak pre-qualifies and informs; the loket files.

### 1.4 Identity — *dream-first, not form-first*

Every chapter begins with the founder's dream (a sentence, a vibe, a neighbourhood) and only then surfaces the data that makes or breaks it. Numbers and rules frame the dream — never gate it. Tone: warm, concrete, grounded. The output artefact is shaped like a passion-project moodboard plus a real planning document — never like a tax form. Where uncertainty exists, the agent says so plainly and points to a human (OOG, FAVV, Stad Gent) — it does not fake certainty.

### 1.5 The strategic wedge

Today, an aspiring founder in Ghent has three modes available to them:
- **VLAIO subsidiedatabank + FOD Economie pages**: comprehensive but text-walls, theme-anchored not address-anchored, not conversational.
- **OOG human advisors**: warm and personalised but scarce, daytime-only, and they don't surface the data the founder needs to make confident decisions.
- **Companyweb / Graydon / commercial intelligence**: paywalled, B2B credit-risk lens — wrong shape for founders.

Droomzaak is the fourth mode: *as personalised as OOG, as comprehensive as VLAIO, available at 2am, visual on a map.* No Belgian competitor fuses map + agent + open data + checklist into one founder journey. The closest international analogues are **NYC Business Express** (permits checklist Q&A) plus **SizeUp** (peer benchmarks) plus **Esri Business Analyst** (site suitability) — and none of those exist for Belgium.

### 1.6 Out of scope (explicit)

- **Filing forms / submitting to KBO / e-signing notary deeds.** V2 territory. Brief explicitly defers this.
- **Accounting, bookkeeping, invoicing post-launch.** Yuki / Octopus / Accountable / Billit own that lane.
- **Live real-estate listings.** Realo / Immoweb own that. We surface open-data proxies only (FOD Financiën rental medians, leegstand handelspanden, vastgoedtransacties) — clearly labeled as benchmarks, never per-address asking-rent quotes.
- **Operating outside Ghent.** The engine is generic; the data layer is Gent-only for now. City expansion is the V2 lane.
- **Existing-business operations** (HR, payroll, scaling). Entirely different product.
- **Active outreach on the founder's behalf** — no appointment-booking, no contact-form filing, no emails sent. Deep-links and references only.

### 1.7 Acceptance test for "the product is the product"

Lisa says one sentence about her dream, spends 15–20 minutes in Droomzaak, walks away with a PDF her grandmother could read aloud — and that her accountant would respect as a real planning artefact.

---

## 2. Hero journey: Lisa's five-chapter walkthrough

The journey is anchored on **Lisa, 32, who dreams of opening a small vegan bistro near Vrijdagmarkt**. This is the demo path and the canonical PRD user-story. The same engine flexes underneath for retail (e.g., a boutique bookstore in Patershol) and service (a freelance consultant going independent) — Saturday's MVP polishes horeca end-to-end and scaffolds the other branches enough to defend the breadth claim.

### Chapter 1 — *Droom*

Soft illustrated welcome (warm earth tones, sketched line-art, a hint of Ghent skyline). One textbox: *"Vertel me over de zaak waar je van droomt."*

Lisa types: *"Een kleine veganistische bistro, koffie 's ochtends, soep en pasta 's middags. Iets met sfeer, dichtbij waar ik woon — Vrijdagmarktbuurt."*

The agent extracts a `dream_profile` via the `extract_dream_profile` tool: sector=horeca, sub=plant-based bistro, NACE=56.101, vibe=cozy, neighbourhood-anchor=Vrijdagmarkt, scale=small. Two warm follow-ups ("hoeveel zitplaatsen droom je over?", "alleen of met iemand erbij?") fill in the remaining parameters.

A *Droomkaart* sidebar appears: sector icon, ambition tagline, parameters (seats: 18, partners: 0, budget: TBD), and a placeholder for the dream narrative that fills in at Chapter 5.

→ Unlock *Bekijk je niche*.

### Chapter 2 — *Niche*

Map fades in: Ghent overview, every existing plant-based or vegetarian horeca venue rendered as dots, drawn from KBO NACE 56.101 + 56.102 ∩ Stad Gent's "Koop Lokaal — Horeca" curated tag, enriched with an OSM Overpass live query and a Google Places `places_search` call (cross-validation against KBO addresses, since KBO records registered seats not trading addresses).

Right rail: niche cards.
- *"13 plant-based zaken in Gent, +27 % de laatste 3 jaar"* — Statbel maandevolutie BTW-plichtige ondernemingen × NACE, joined to KBO open extract.
- **Peer-performance benchmarks for the NACE 56.101 cohort in Gent** — pulled from Statbel HVD detailhandel + maandevolutie BTW + Zelfstandige ondernemers DataLab (CBSO is the cleaner source for this signal and lives in the V2 roadmap; Statbel gives us defensible cohort numbers in time for Saturday).
- *"Faillissementen in jouw niche: 4 in 2024 vs 6 in 2023"* — Statbel NodeID4027.
- *Stretch:* "Wil je zien wat de drie hoogst-gewaardeerde gemeen hebben?" — Google Places review enrichment.

Agent voiceover (Dutch): *"13 anderen hebben het gedurfd. Hier is hoe ze het doen."*

→ *Vind je plek*.

### Chapter 3 — *Waar*

Map widens. Agent-driven filters apply via `set_layer_filter` calls running over Map Pilot's existing layer tools, scoring every Gent statistical sector on:
- Demographic match against Lisa's target customer (working young adults, family weekend brunch traffic) using `demographics_sector_annual`.
- Foot-traffic signal — triangulated from Stad Gent open traffic counters, citycard usage, museumbezoek (open-data tier) **plus** Google Places popular-times for the actually-existing horeca venues in each sector (live tier).
- Competition density: `spatial_count` of NACE 56.101 ∪ 56.102 within 500 m of every sector centroid.
- Vacancy filter: `commercial_premises` clipped to horeca-eligible vacant panden.
- Walkability / transit: De Lijn haltes + cycling infrastructure within 300 m.
- Rent benchmark: median commercial-rent per sector from FOD Financiën huurcontracten (clearly labelled as a sector-level proxy, not a per-address quote).
- Disruption filter: avoid sectors with active GIPOD-flagged road works lasting longer than 6 months.

Agent surfaces the top 3–5 candidate addresses, ranked, each with a one-line "waarom hier". Lisa hovers each → prose explanation in the chat. She picks one. The Droomkaart locks the choice.

→ *Vergunningen & geld*.

### Chapter 4 — *Vergunningen & geld*

Sector-branched permit checklist appears for "horeca @ Vrijdagmarkt @ NACE 56.101":
- Horeca-attest Stad Gent.
- FAVV registratie (food + drinks).
- Drankvergunning gegiste dranken + sterkedrankvergunning (Lisa says wine: yes; agent escalates).
- Omgevingsvergunning klasse — auto-detected as klasse 2 (ventilation + frying).
- Terrasvergunning + the terrasinplantingsplan polygon for her exact address overlaid on the map (yes / no / restricted, with visual).
- Unisono (music rights), brandweerkeuring (capacity-driven), EPB if renovation.
- Each item: a deep-link to the official Stad Gent / FAVV / FOD page, a one-line explainer, an estimated cost, an estimated processing time.

Subsidies card, filtered to Lisa's profile:
- Startlening PMV — eligible up to €100 k.
- Win-Win lening — friends/family up to €75 k/lender.
- Stad Gent renovatiepremie handelspanden — eligible for her chosen pand.
- KMO-portefeuille — 30 % on advice + training, capped at €7.5 k/yr.

Legal-form quick-recommend: *"0 partners, fysieke horecapand, omzetprognose €280 k → BV/SRL beschermt je privévermogen, ~€1 500 notariskosten; eenmanszaak is OK als budget krap is. We zetten beide in het pakket."* A single card, deliberately not a sub-flow.

Agent answers nuance in chat (*"Alcohol na 21u?"*, *"Schoolstraat-zone?"*, *"Allergenen-bordjes?"*).

→ *Mijn Droomzaak-pakket*.

### Chapter 5 — *Droomzaak-pakket*

One click renders the take-away page.
- **Top:** AI-generated 3-paragraph dream narrative + chosen address card + Streetview thumb + Lisa's own vibe quote from Chapter 1.
- **Jouw dinsdagochtend:** day-in-the-life simulation card — open 8u, ~80 covers/dag op basis van footfall, geschatte omzet €280 k/jaar, geschatte take-home na kosten per maand. *This is the dream-materialisation pillar made concrete and conservative — never extrapolating beyond what the data supports.*
- **Dossier per chapter:** location dossier · niche numbers · permit checklist with deep-links · subsidy shortlist with eligibility ticks · legal-form recommendation.
- **Volgende stappen:** *"Klaar om door te zetten? Hier is je checklist en de plekken waar je terecht kunt."* Deep-link block to Stad Gent / FAVV / FOD Economie / VLAIO / the eight ondernemingsloketten. Informational only — no booking, no contact form.
- **Two buttons:** *Download als PDF* and *Deel link* (a stable URL on the public demo host).

This is the pitch climax. The artefact is the demo's final shot.

---

## 3. System architecture

### 3.1 Architecture in one picture

```
Frontend (extends Map Pilot React)
├── MapLibre canvas (reused, untouched)
├── Chapter rail (NEW — 5-step progress, gated transitions)
├── Droomkaart sidebar (NEW — accumulating profile)
├── Chat panel (reused — Droomzaak system prompt swapped in)
└── Pakket renderer (NEW — server-rendered HTML + Print-to-PDF)

Backend (extends Map Pilot FastAPI + agent_loop)
├── Agent loop (reused, no changes — agent_loop.py + ProviderAdapter)
├── Droomzaak chapter state machine (NEW — JSON column on agent_sessions)
├── Existing tool surface (reused — apply_map_actions, query_osm, etc.)
└── New tool surface (NEW — see §3.5)

Data tier — two-tier
├── Tier 1: RENDER (local, fast)
│   └── DuckDB + cached GeoJSON (reused from Map Pilot)
│   └── Feeds MapLibre layer cache only — never agent reasoning
└── Tier 2: REASON (via Soda Straw)
    └── Postgres 16 ('droomzaak' schema) — canonical analytical tables
    └── Soda Straw MCP server in front of Postgres = the only path for
        agent analytical tool calls (peer benchmarks, scoring, lookups)

Live external (not in Postgres)
├── OSM Overpass (query_osm tool, reused)
├── Google Maps Places + popular times (NEW)
├── MapLibre vector tiles (reused)
└── OpenRouteService isochrones (reused)
```

### 3.2 What stays exactly the same as Map Pilot

- The `agent_loop.py` + provider adapter shape. We only swap the system prompt and the tool list.
- `agent_validation.py`. Extended with new action types as needed.
- The MapLibre canvas, layer cache, filter expressions, debug viewer.
- DuckDB catalogue + ingest scaffolding. We subset which datasets get loaded.
- `agent_sessions` storage. We add a JSON column for chapter state.

### 3.3 The chapter state machine

A thin server-side state machine wrapping the existing agent loop — *not* a parallel orchestrator. Five canonical chapters, each with a required tool subset, a typed `state` shape, and an explicit exit condition.

| Chapter | State accumulates | Required tools | Exit condition |
|---|---|---|---|
| 1 *Droom* | `dream_profile` | `extract_dream_profile`, `apply_map_actions` | `dream_profile.sector` set |
| 2 *Niche* | + `niche_signals` | `peer_benchmarks_statbel`, `query_osm`, `places_search`, `search_datasets` | user clicks *Vind je plek* |
| 3 *Waar* | + `candidate_locations[]` | `score_locations`, `nearest_features`, `spatial_count`, `rent_benchmark`, `places_popular_times` | user picks a location |
| 4 *Vergunningen & geld* | + `permit_checklist[]`, `subsidies[]`, `legal_form` | `permit_checklist_for`, `subsidies_for`, `legal_form_advisor` | all items rendered |
| 5 *Pakket* | render-only | `generate_dream_narrative`, `compose_package` | PDF / link delivered |

The agent's system prompt branches behaviour off `current_chapter`. The chapter rail in the UI is a thin reflection of this state — clicking ahead requires the exit condition. State is persisted as JSON on `agent_sessions`.

### 3.4 Soda Straw posture — "every datum the agent surfaces flows through here"

[Soda Straw](https://sodastraw.ai/) is access management for AI agents: an MCP-server frontend that gates per-person, per-agent, per-straw access to data sources, with audit logging. Connectors today are Postgres, Snowflake, Salesforce, and any upstream MCP server.

We use it as **the canonical ingress for all analytical data the agent reasons over**. One Postgres straw, one connection, one audit log. Every new analytical tool the agent calls is a thin Python wrapper around a Soda Straw MCP `query` call. The agent's existing action tools (`apply_map_actions`, `query_osm`, etc.) stay native — those are *behaviour* tools, not data tools.

This gives the hackathon-winning posture: the debug overlay during the demo shows every analytical reasoning step routed through Soda Straw. Map rendering stays as fast as Map Pilot is today.

**Stretch:** wrap one or two live APIs (OSM Overpass, Google Places, GIPOD live LDES) as small MCP servers and broker them through Soda Straw too, so the *"everything goes through Soda Straw"* claim becomes literal. Only if Track A has bandwidth past hour 6.

### 3.5 New agent tools (additions on top of Map Pilot's 16)

| Tool | Role | Backed by |
|---|---|---|
| `extract_dream_profile(text)` | LLM-classifier hidden behind a tool — extracts sector, NACE, scale, vibe, neighbourhood, scale signals from one sentence. | OpenAI / Anthropic with constrained output schema. |
| `peer_benchmarks_statbel(nace, refnis)` | Sector-cohort openings, closings, faillissementen, BTW evolution. | Soda Straw → Postgres → Statbel-derived tables. |
| `places_search(query, bbox, types)` | Live competitor / niche venue discovery. | Google Places API. |
| `places_popular_times(place_id)` | Hour-level footfall signal for a venue. | Google Places API (Insights / popular times). |
| `score_locations(profile, weights)` | Ranks Gent sectors / candidate addresses on demographic + competition + vacancy + transit + rent + disruption. | Soda Straw → Postgres → weighted SQL join. |
| `rent_benchmark(sector_id, asset_type)` | Median commercial rent + p25 / p75 + n for a sector. | Soda Straw → Postgres → FOD Financiën huurcontracten. |
| `permit_checklist_for(nace, address, attributes)` | Sector-branched checklist with deep-links, estimated cost, and estimated processing time per item. | Soda Straw → Postgres → `permit_rules` config + `permits_events` evidence. |
| `subsidies_for(profile, address)` | Eligibility-checked subsidy shortlist. | Soda Straw → Postgres → VLAIO + Stad Gent + federal. |
| `legal_form_advisor(profile)` | Eenmanszaak vs BV/SRL recommendation. | Decision tree, pure Python. |
| `generate_dream_narrative(...)` | Constrained-style 3-paragraph narrative + Tuesday-morning simulation. | LLM with style guide + two-shot examples. |
| `compose_package(state)` | Serialises chapter state into the renderer input. | Pure Python. |
| `set_chapter_state(patch)` | Validated state persistence. | Existing validation pipeline extended. |

### 3.6 Frontend additions

- **Chapter rail** — ~120 LOC React, five icons, gated transitions.
- **Droomkaart sidebar** — ~200 LOC, accumulating profile card driven off chapter state.
- **Package renderer** — ~400 LOC + a print stylesheet, server-rendered HTML at `/pakket/<session_id>`, Print → PDF for the take-away, the static URL is the shareable link.

### 3.7 Deployment

A public hostname (Vercel + Render + Fly TBD) so the shareable URL in the package resolves during the pitch. Backend on a single VM near the venue. Secrets pre-provisioned by Friday night: Soda Straw token, OpenAI key, Anthropic key, Google Maps key, OpenRouteService key.

---

## 4. Data plan

### 4.1 Data categories the agent reasons over

Rather than a 30-row dataset table (which lives as a technical appendix in `open-data/docs/phase1_gent_entrepreneur.md`), the categories of evidence the agent draws on:

1. **Administrative geographies** — statistische sectoren, stadswijken. The join keys for everything spatial.
2. **People context** — demographics, income, household composition, mobility behaviour per sector.
3. **Place context** — real-estate transaction and rental medians, vacant commercial premises, sfeergebieden, amenity layers (transit, walkability).
4. **Business context** — KBO firm registry, NACE-coded firm counts, faillissementen, sector openings/closings (Statbel HVD + maandevolutie BTW). Statbel-derived peer-performance benchmarks for the chosen NACE cohort.
5. **Regulatory context** — historical permits (omgevingsvergunningen, bouwvergunningen), a hand-curated city-level permit-rule catalogue keyed on NACE × address attributes, municipal tax reference.
6. **Funding context** — VLAIO subsidiedatabank + Stad Gent subsidieregister + federal tax-shelter starter, normalised into a single eligibility model.
7. **Disruption context** — planned road works + events + stadsvernieuwing (so the agent doesn't recommend a candidate location facing 18 months of construction).

Each category becomes one or more Postgres tables in the `droomzaak` schema. The full dataset list and ingest provenance live in the existing `open-data/docs/phase1_gent_entrepreneur.md` ingest plan plus the broader Map Pilot open-data pipeline.

### 4.2 Live (dynamic) sources, not in Postgres

- OSM Overpass — comprehensive niche / competitor discovery beyond KBO.
- Google Maps Places + popular times — foot-traffic signal stronger than open-data proxies for known venues.
- Google Maps Streetview Static API — Streetview thumb for the chosen address in the package (Chapter 5). One call per session. Falls back to a generic "your location" illustration if quota / cost is a concern.
- MapLibre vector tiles — base map.
- OpenRouteService isochrones — travel-time catchments.
- *Stretch:* GIPOD live LDES — real-time road works wow factor if Soda Straw can broker it.

### 4.3 Substitutions for hackathon scope

- **NBB CBSO annual accounts → Statbel cohort aggregates.** CBSO is the highest-quality peer-performance source (joins to KBO via VAT, gives per-NACE-cohort financials for free) but the XBRL parsing is too heavy to ship by Saturday. Statbel HVD detailhandel + maandevolutie BTW + faillissementen give us defensible cohort numbers in time. CBSO returns in V2.
- **Companyweb / Graydon → out of scope.** Paid, B2B credit-risk lens. Statbel + KBO cover the founder lens.
- **Realo / Immoweb rent listings → out of scope.** Sector-median rent from FOD Financiën huurcontracten is our proxy. V2 partner integration.

### 4.4 Pre-event load (Friday work)

1. Stand up Postgres 16 (managed: Neon / Supabase / Railway free tier, or Render self-host).
2. Run a one-shot `dump_duckdb_to_postgres.py` (~50 LOC) over the existing Map Pilot DuckDB + Parquet dumps. Subset to the seven categories.
3. Hand-curate the `permit_rules` table for horeca + the 5 retail + 3 consultant cases we'll demo.
4. Register the Postgres database as a Soda Straw source. Document the connection string in `.env.demo`.
5. Smoke-test every new analytical tool from a local MCP client.

### 4.5 Refresh strategy

Snapshot-and-freeze: take a final dump Friday evening. No live re-ingest during the 12 hours. Predictable demo beats marginal recency. GIPOD live LDES is the one exception if Soda Straw brokers it cleanly.

---

## 5. MVP scope (Saturday) versus vision (V2+)

### 5.1 Saturday MVP commits

| Pillar | Saturday MVP commits to | Defers |
|---|---|---|
| Map + canvas | Reuse Map Pilot canvas. Add chapter rail + Droomkaart. | No new map style work. |
| Chapter engine | 5-chapter state machine, server-persisted, gated transitions. | No backtracking polish, no cross-session resume beyond what `agent_sessions` already gives. |
| Agent | Reuse existing loop, swap prompt, add ~12 new tools. | No multi-agent, no escalation policy, no streaming. |
| Data via Soda Straw | All canonical Postgres tables behind one straw. Every analytical tool routes through it. | No live-API MCP wrappers (stretch only). |
| Live data | OSM via `query_osm`. Google Places + popular times via new tools. | No GIPOD live (snapshot fine). |
| Sector coverage | **Horeca branch polished end-to-end.** Retail + consultant: scaffolded — sector recognised, degraded version of Chapters 3 + 4, thinner package. Enough to defend "the engine handles other sectors". | Crafts, e-commerce, regulated professions — recognised but no targeted content. |
| Package output | Server-rendered HTML at `/pakket/<session_id>`, Print → PDF, shareable URL on public host. | No persistent account, no editable package, no email delivery. |
| Dream narrative | LLM-generated 3-paragraph narrative + a Tuesday-morning simulation card. Restrained, concrete. | No AI imagery, no mood-board, no audio. |
| Hand-off | Deep-link block to Stad Gent / FAVV / FOD / VLAIO / loketten. Informational only. | No booking, no contact form, no email. |
| Languages | Dutch primary, EN fallback via `AGENT_LANGUAGE`. | French / multi-lingual UX. |
| Deployment | Public host for demo + shareable links. Pre-provisioned Friday night. | No prod hardening, no autoscaling, no monitoring. |

### 5.2 Build sequence — the 12 hours

Pre-event (Friday evening): Postgres load + Soda Straw connection + secrets pre-provisioned + public host deployed. *None of this is Saturday work.*

| Hour | Track A (backend / agent) | Track B (frontend / canvas) | Track C (content / pitch) |
|---|---|---|---|
| 0–2 | Wire Soda Straw MCP client in the agent. Smoke-test each new tool against Postgres. Provision Google Places API client + key. | Chapter rail + Droomkaart shell in React. | Permit-rule catalogue YAML for horeca (the rules we demo, with cost + processing-time estimates per item). |
| 2–4 | Implement `extract_dream_profile`, `score_locations` (consumes `rent_benchmark` + disruption + competition + transit), `peer_benchmarks_statbel`, `places_search`, `places_popular_times`. | Wire Chapter 1 prompt → state. Wire Chapter 2 dots + cards. | Subsidies eligibility config (VLAIO Startlening, Win-Win, Stad Gent renovatiepremie, KMO-portefeuille). |
| 4–6 | Implement `permit_checklist_for`, `subsidies_for`, `legal_form_advisor`, `set_chapter_state`. | Wire Chapter 3 scoring overlays + Chapter 4 checklist cards. | Dream-narrative + Tuesday-morning prompt templates with two-shot examples. |
| 6–8 | Implement `generate_dream_narrative`, `compose_package`. End-to-end Lisa rehearsal. Sofie retail walkthrough as the second demo path. | Package renderer + print stylesheet. | Pitch script + one slide (the rest is the live demo). |
| 8 | **Hacking stops, pitch + AI evaluation.** | | |

**Hard rule: no scope creep after hour 6.** Only the planned tools and polish — no new ideas, no late-breaking pivots, no last-hour additions.

### 5.3 Vision (V2 and beyond)

- **Execution flow** — pre-filled KBO / BTW / social-fund forms, ondernemingsloket appointment booking. The brief calls this out explicitly as future scope.
- **CBSO peer-benchmarks** with proper XBRL ingest and granular cohort filtering.
- **Live real-estate** via Realo / Immoweb partner API (replacing the median-rent proxy).
- **City expansion** — same engine, datasets for Antwerpen / Brussel / Leuven.
- **Post-launch lane** — bookkeeping software pick (Yuki / Octopus / Accountable / Billit) + Peppol e-invoicing onboarding wizard.
- **Mood-board / AI imagery** for the dream narrative.
- **Persistent founder account** — return weeks later, the package is still there, updated as the data changes.
- **OOG-facing advisor dashboard** — see all in-flight Droomzaken in their commune, comment, intervene.
- **Founder-to-founder benchmarking** — "you're in the top quartile / bottom quartile for footfall vs peers in your NACE."

### 5.4 Pitch evaluation criteria

| Claim the pitch makes | Evidence the demo must show |
|---|---|
| Real city need, validated by Stad Gent's own RFP. | Verbatim quote of the city's one-stop-shop ask in the deck. |
| Map + data + agent fused — first of its kind in Belgium. | Side-by-side: VLAIO subsidiedatabank text-walls vs Droomzaak's map-anchored conversational journey. |
| Soda Straw at the centre of the data architecture. | Debug overlay showing every agent analytical call routed through Soda Straw. |
| 60+ open datasets pre-curated, deployable to any Belgian city. | One sentence in the deck + dataset count in the package footer. |
| Keeps the dream alive. | The Tuesday-morning card + dream narrative read out loud on stage. |
| Saturday demo is a slice of a much bigger product. | Vision roadmap visible at the close of the pitch. |

---

## 6. Risks, open items, success criteria

### 6.1 Top risks

| Risk | Impact | Mitigation |
|---|---|---|
| Soda Straw is the single dependency for all analytical tools. If the connector hiccups during the demo, every chapter past 1 stalls. | High × Medium | Stand it up Friday, smoke-test every tool, keep a local-Postgres-direct failover code path behind a feature flag — never used unless something breaks live. |
| Permit-rule catalogue is hand-curated and may be wrong in edge cases. | High × Medium | Scope rules tight to horeca + 5 retail + 3 consultant cases. Where uncertain, the agent says *"Dit wil je bevestigen bij Stad Gent / FAVV"* — refuses to fake certainty. |
| KBO addresses are registered seats, not trading addresses. Competitor density may be misleading at street level. | Medium × High | Triangulate with OSM + Google Places. Frame both signals in the demo so jury sees where they agree / disagree. |
| No open per-address rent. Sector-median rent is a coarse proxy. | Medium × High | Explicitly labelled in the package: *"benchmark voor commerciële panden in deze sector. Voor het exacte pand vraag bij Stad Gent OOG / makelaar."* Never quoted per-address. |
| Google Maps popular-times has cost + ToS implications. | Medium × Medium | Use Places API officially (paid tier, free credits cover the demo). Cap to Chapter 3 (5–10 calls / session). Don't scrape. |
| Dream-narrative tone risks landing as cringey AI-magazine prose. | High × Medium | Style guide in prompt: warm, concrete, grounded in Lisa's words, third-person reportage *not* second-person aspirational. Length capped. Two-shot examples from real OOG advisory write-ups. Pre-screen before Saturday. |
| Multi-sector branching is thin outside horeca. | Medium × Medium | Pre-build a 60-second Sofie / bookstore retail walkthrough as a second demo path. Skip consultant unless asked. |
| 12-hour scope creep. Every hour on polish is an hour not on the next chapter. | High × High | Strict hour timeboxes (§5.2). At each checkpoint, the chapter ships end-to-end *or* degraded. No new tools after hour 6. |
| Demo-day environment flake (laptop, venue WiFi, model API rate limits). | High × Low | Pre-recorded 90-second "everything dies" backup video. Both OpenAI and Anthropic wired so providers can swap mid-demo. Demo machine offline-capable for chapter content; only live deps are OSM, Places, the model. |
| Open data licensing edge cases. | Low × Medium | Package footer + deck slide: *"Powered by open data: Statbel, FOD Financiën, KBO, Stad Gent Open Data, OpenStreetMap, VLAIO."* |

### 6.2 Open items to resolve before / during the hackathon

1. **Soda Straw credentials & connector inventory** — what's pre-connected by Friday afternoon? Is the Postgres straw confirmed available? Any upstream MCP straws already wired by the organisers?
2. **Hosting target** — Vercel / Render / Fly? Where does the demo URL live? Who owns DNS / certs?
3. **Google Maps Places API key + quota** — provisioned before Friday or fall back to OSM-only.
4. **Team roles** — who owns Track A (agent / tools), Track B (frontend / canvas), Track C (content / pitch)? Solo paths are not viable for the §5.2 sequence — at least 2 builders + 1 content/pitch person.
5. **Pitch language** — Dutch (jury context) or English (broader reach)? Demo stays Dutch; pitch can differ.
6. **Brand assets** — logo, colour, illustrated welcome screen. Defaulting to warm earth tones, sketched line-art unless overruled.
7. **Stad Gent pre-notify** — pre-pitch OOG that we're demoing a tool that scales their offering? Could turn into a post-hackathon conversation.

### 6.3 Definition of "demo succeeded"

The Saturday demo is successful if **all** the following hold:

1. Lisa's walkthrough completes from Chapter 1 to a downloaded PDF without operator intervention.
2. The agent makes at least one Soda Straw call per chapter and the debug overlay shows this.
3. Chapter 3 surfaces 3+ scored candidate addresses, each clickable for a "why this one" explanation.
4. Chapter 4 surfaces 5+ permit / licence items correctly tagged for horeca + 3+ eligible subsidies for Lisa's profile.
5. Chapter 5 renders the dream narrative, location dossier, niche numbers, permit checklist, subsidies, legal-form recommendation, and hand-off block — on one page, looking like a deliberate artefact, not a database dump.
6. A jury member can pick a non-Vrijdagmarkt address and the agent re-runs Chapter 3+ without crashing (proves the engine is generic, not hard-coded).
7. The pitch deck closes on the vision roadmap, not the MVP.

### 6.4 Definition of "PRD succeeded" (longer term)

The PRD has done its job if, three months from now:
- A new team member can read it cold and understand what we're building, why, and the founder journey we serve.
- It convinces Stad Gent that Droomzaak is a credible candidate to be the city's one-stop founder tool.
- It functions as the contract for what V2 looks like: execution flow, CBSO peer benchmarks, real-estate partner integration, city expansion.

---

## Appendix A — Source notes

This PRD draws on:
- The City of Ghent's one-stop-shop RFP wording quoted in the brief.
- The existing Map Pilot foundation (`backend/app/agent_loop.py`, `agent_validation.py`, `agent_tools.py`, `layer_context.py`, the open-data ingest at `backend/app/sources/`).
- The pre-existing entrepreneur use-case scoping at `open-data/docs/phase1_gent_entrepreneur.md` — 43 datasets inventoried, 9 canonical tables, 6 agent tools sketched. Droomzaak's data plan is the operational version of that document, with substitutions noted in §4.3.
- The broader Map Pilot open-data pipeline catalogue at `open-data/catalogues/` (60+ relevant datasets across data.stad.gent, Statbel, FOD Financiën, KBO, NBB CBSO, GIPOD, VLAIO, buurtmonitor).
- Founder-journey research (2026-05-28 brainstorming session): Belgian company forms (eenmanszaak vs BV/SRL vs NV), mandatory administrative chronology, sector-specific permits (horeca attest, FAVV, drankvergunningen, omgevingsvergunning klasse, terrasvergunning, Unisono), Ghent-specific permits, Vlaams + federal subsidies, the existing starter-support ecosystem (VLAIO 1700, UNIZO, Voka Bryo, Bedrijvencentrum Gent, OOG, ondernemingsloketten, accounting tools).
- Competitive scan: VLAIO subsidiedatabank, ondernemen.stad.gent + OOG, startupmap.gent, 1819 / hub.brussels, Companyweb, GraydonCreditsafe, provincies.incijfers.be, Statbel monitor, the eight ondernemingsloketten' starter portals, international analogues (NYC Business Express, SizeUp, Esri Business Analyst, Placer.ai, Stripe Atlas / Doola / Firstbase).
- Soda Straw capabilities: documented at [sodastraw.ai](https://sodastraw.ai/). Confirmed connectors: Postgres, Snowflake, Salesforce, any upstream MCP server. Capabilities: per-person / per-agent / per-straw access management, audit logging.

## Appendix B — Glossary

- **Atelier / Droomzaak** — the founder journey product. "Droomzaak" is the Dutch word for "dream company", chosen as the consumer-facing brand.
- **KBO / BCE** — Kruispuntbank van Ondernemingen, the federal company registry.
- **NACE / NACE-BEL** — European activity classification codes; NACE-BEL is the Belgian adaptation.
- **OOG** — Ondersteuningspunt Ondernemers Gent, the city's human one-stop for entrepreneurs.
- **Ondernemingsloket** — accredited one-stop business counter (8 in Belgium: Liantis, Securex, Acerta, Partena, Xerius, Group S, UCM, Eunomia). Legally required for KBO registration.
- **VLAIO** — Vlaams Agentschap Innoveren & Ondernemen. Owns the Flemish subsidy database.
- **CBSO** — Central Balance Sheet Office at the NBB. Annual accounts repository.
- **GIPOD** — Generiek Informatieplatform Openbaar Domein. Flemish road-works + public-domain occupation feed.
- **Omgevingsvergunning** — environmental permit. Class 3 = notification, class 2 = municipal permit, class 1 = provincial permit.
- **Soda Straw** — MCP-based access management product for AI agents. Mandatory hackathon infrastructure.
- **Map Pilot** — the open-data Ghent map + agent product Droomzaak extends. Foundation provides: agent loop, validation, MapLibre canvas, DuckDB catalogue.
