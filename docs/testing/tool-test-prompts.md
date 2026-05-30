# Droomzaak — tool test prompts

A manual + scriptable harness to verify every agent tool fires and behaves as
expected. Each section gives: the **prompt**, the **chapter** it must run in, the
**tool(s)** it should call, and **how to verify**.

> Two tiers (see `.claude/rules/data-tiers.md`):
> - **Native / LLM tools work without the warehouse.**
> - **DataGateway tools** (`peer_benchmarks_statbel`, `score_locations`,
>   `rent_benchmark`, `permit_checklist_for`, `subsidies_for`) need
>   `DROOMZAAK_POSTGRES_URL`. Without it they return the honest
>   `{"error": "...", "hint": "..."}` envelope — that is the *expected* result in
>   degraded mode, not a failure.

## 0. Setup

```bash
export PATH="$HOME/.local/bin:$PATH"
uv run uvicorn backend.app.main:app --reload --port 8000
```

Confirm what's wired (no secrets printed):

```bash
curl -s localhost:8000/api/admin/health | jq
# gateway_ok:true  → DB tools return real data
# gateway_ok:false → DB tools return {error,hint} (expected in degraded mode)
```

Every `/api/agent/chat` response carries a `debug_id`. Pull the full trace —
including which tools were dispatched and the DataGateway audit log — with:

```bash
curl -s localhost:8000/api/agent/debug/<debug_id> | jq
```

The debug trace is where you confirm **"called as expected"**: look for each tool
name in the dispatched-tool list and inspect its returned payload.

---

## 1. Chapter 1 — Droom → `extract_dream_profile`

- **Chapter:** `1_droom` (the default for a fresh session)
- **Expected tool(s):** `extract_dream_profile`, then `apply_map_actions` with a
  `set_chapter_state` patch advancing to `2_niche`.
- **Backing:** LLM seam (OpenAI/Anthropic key). No warehouse needed.

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "Ik droom van een klein veganistisch bistro vlakbij de Vrijdagmarkt",
  "session_id": "smoke1"
}' | jq
```

**Verify:**
- Reply is one warm Dutch sentence summarising the dream.
- Debug shows `extract_dream_profile` returned `sector`, `nace_code`,
  `neighbourhood_anchor`, `confidence`.
- `current_chapter` is now `2_niche` (exit condition `dream_profile.sector` met).

**Edge case — low confidence / vague input** (agent may ask 1–2 follow-ups
instead of advancing):

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "ik wil iets met eten ofzo", "session_id": "smoke1b"
}' | jq
```

---

## 2. Chapter 2 — Niche → `peer_benchmarks_statbel` · `query_osm` · `web_search`

- **Chapter:** `2_niche` (reuse `smoke1` after step 1, or fast-forward — see §6)
- **Expected tool(s):** `peer_benchmarks_statbel` (DB ⚠️), `query_osm` (native).
  `web_search` is a fallback — exercise it with the off-script prompt below.

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "Hoeveel veganistische zaken zijn er al in deze buurt? Laat ze op de kaart zien.",
  "session_id": "smoke1"
}' | jq
```

**Verify:**
- Debug shows `query_osm` returned a `dataset_id` (`osm-…`) with `feature_count`.
- `peer_benchmarks_statbel` returned counts/summary **or** the `{error,hint}`
  envelope (degraded mode).
- Reply shows 2–4 key figures and a map layer is shown.

**`web_search` (Tavily fallback)** — ask an off-script rules question:

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "Wat zegt de stad Gent officieel over een terrasvergunning?",
  "session_id": "smoke1"
}' | jq
```
Expect `web_search` results biased to official domains (stad.gent, favv-afsca.be,
…), or `{error,hint}` if `TAVILY_API_KEY` is missing.

---

## 3. Chapter 3 — Waar → `score_locations` · `rent_benchmark` · `geocode`

- **Chapter:** `3_waar`
- **Expected tool(s):** `score_locations` (DB ⚠️), `rent_benchmark` (DB ⚠️),
  `geocode` (native, Nominatim) when a specific address is named.

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "Waar kan ik dit best openen? En wat denk je van Sleepstraat 12?",
  "session_id": "smoke1"
}' | jq
```

**Verify:**
- `geocode` returned `coordinates` + `label` for Sleepstraat 12.
- `score_locations` returned a ranked list **or** `{error,hint}`.
- `rent_benchmark` returned a sector **proxy** (never a per-address quote) **or**
  `{error,hint}`.
- If `score_locations` returned data, the reply's map shows the layer with a
  heatmap on `field=score` (non-negotiable per the Ch3 prompt).

---

## 4. Chapter 4 — Vergunningen & geld → `permit_checklist_for` · `subsidies_for` · `legal_form_advisor` · `web_search`

- **Chapter:** `4_vergunningen`
- **Expected tool(s):** `permit_checklist_for` (DB ⚠️), `subsidies_for` (DB ⚠️),
  `legal_form_advisor` (pure Python ✅).

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "Welke vergunningen heb ik nodig, kom ik in aanmerking voor premies, en welke rechtsvorm raad je aan?",
  "session_id": "smoke1"
}' | jq
```

**Verify:**
- `legal_form_advisor` always returns `recommended` (Eenmanszaak/BV-SRL),
  `alternative`, `rationale_nl`, `estimated_setup_cost_eur`. **This one must work
  even in degraded mode.**
- `permit_checklist_for` / `subsidies_for` return curated rows **or**
  `{error,hint}`. If empty in connected mode → config gap → agent should call
  `report_problem` with `reason="no_good_dataset"`.
- Honesty check: any `uncertain_areas_nl` from `permit_checklist_for` must be
  named in the reply, pointing to OOG / FAVV / Stad Gent.

---

## 5. Chapter 5 — Pakket → `generate_dream_narrative` · `compose_package`

- **Chapter:** `5_pakket`
- **Expected tool(s):** `generate_dream_narrative` (LLM ✅), `compose_package`
  (DuckDB ✅).

```bash
curl -s localhost:8000/api/agent/chat -H 'content-type: application/json' -d '{
  "message": "Maak mijn Droomzaak-pakket.",
  "session_id": "smoke1"
}' | jq
```

**Verify:**
- `generate_dream_narrative` returned `dream_narrative_nl` (3 paras, third-person
  reportage) + `tuesday_morning_nl`.
- `compose_package` returned `package_url` (`/pakket/<session_id>`) and `ready:true`.
- `GET /api/droomzaak/chapter/smoke1` shows `current_chapter:"5_pakket"` with the
  narrative + package_url persisted.

---

## 6. Fast-forward: jump straight to a chapter's tools

Tools are chapter-gated, and `PUT /api/droomzaak/chapter/{id}` enforces sequential
advance + exit conditions — so seed state **one chapter at a time**. Use this to
test a late-chapter tool without walking the whole flow.

```bash
S=ff1
# Ch1 → Ch2  (exit: dream_profile.sector)
curl -s -X PUT localhost:8000/api/droomzaak/chapter/$S -H 'content-type: application/json' \
 -d '{"patch":{"dream_profile":{"sector":"horeca","nace_code":"56.101","scale":"small","neighbourhood_anchor":"Vrijdagmarkt","seats_guess":20,"sector_group":"horeca"},"current_chapter":"2_niche"}}'
# Ch2 → Ch3  (exit: niche_signals)
curl -s -X PUT localhost:8000/api/droomzaak/chapter/$S -H 'content-type: application/json' \
 -d '{"patch":{"niche_signals":{"note":"seeded for test"},"current_chapter":"3_waar"}}'
# Ch3 → Ch4  (exit: chosen_location.coordinates)
curl -s -X PUT localhost:8000/api/droomzaak/chapter/$S -H 'content-type: application/json' \
 -d '{"patch":{"chosen_location":{"address":"Sleepstraat 12","wijk_nl":"Sluizeken-Tolhuis-Ham","coordinates":[3.7250,51.0580]},"current_chapter":"4_vergunningen"}}'
# Ch4 → Ch5  (exit: permit_checklist AND subsidies AND legal_form)
curl -s -X PUT localhost:8000/api/droomzaak/chapter/$S -H 'content-type: application/json' \
 -d '{"patch":{"permit_checklist":[{"name":"seeded"}],"subsidies":[{"name":"seeded"}],"legal_form":{"recommended":"Eenmanszaak"},"current_chapter":"5_pakket"}}'
```

Now `session_id:"ff1"` is parked wherever you stopped. Send the matching chat
prompt from the section above to exercise that chapter's tools directly.

> Note: a `PUT` that violates an exit condition or skips a chapter returns HTTP
> 400 with a Dutch `hint` — that itself is a good negative test of the state
> machine.

---

## 7. Coverage checklist

| Tool | Section | Backing | Works in degraded mode? |
|---|---|---|---|
| `extract_dream_profile` | §1 | LLM | ✅ (needs model key) |
| `apply_map_actions` | every turn | in-process | ✅ |
| `report_problem` | §2/§4 (on gaps) | in-process | ✅ |
| `peer_benchmarks_statbel` | §2 | DataGateway | ⚠️ `{error,hint}` |
| `query_osm` | §2 | Overpass | ✅ |
| `web_search` | §2/§4 | Tavily | ✅ (needs key) |
| `score_locations` | §3 | DataGateway | ⚠️ `{error,hint}` |
| `rent_benchmark` | §3 | DataGateway | ⚠️ `{error,hint}` |
| `geocode` | §3 | Nominatim | ✅ |
| `permit_checklist_for` | §4 | DataGateway | ⚠️ `{error,hint}` |
| `subsidies_for` | §4 | DataGateway | ⚠️ `{error,hint}` |
| `legal_form_advisor` | §4 | pure Python | ✅ |
| `generate_dream_narrative` | §5 | LLM | ✅ (needs model key) |
| `compose_package` | §5 | DuckDB | ✅ |
| `set_chapter_state` | §6 (+ every advance) | validated state machine | ✅ |

Once `DROOMZAAK_POSTGRES_URL` is set + seeded (`uv run python scripts/seed_demo.py`),
the five ⚠️ tools should return real rows. The fastest direct check of just those:

```bash
uv run python scripts/smoke_tools.py
```
