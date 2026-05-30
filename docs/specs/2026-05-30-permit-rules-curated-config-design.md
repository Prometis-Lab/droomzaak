# Design — `permit_rules` curated config + fetch plan

**Date:** 2026-05-30
**Status:** design (brainstorming output) — pending implementation spec + spec-critic gate
**Track:** A (backend/data)

## Problem

CLAUDE.md and the PRD reference a "permit YAML" that does not exist yet. Today the repo
has only the **evidence** half of permits — `droomzaak.permits_events` + `permits/clean.py`
(granted Omgevingsloket applications clipped to Gent, answering *"has a permit been granted
nearby?"*). The **rules** half — the conditional decision table behind `permit_checklist_for`,
answering *"what do I legally need to open THIS here?"* — is missing: no `permit_rules.yaml`,
no `permit_rules` table.

This design covers acquiring + encoding those rules and landing them in Postgres, ready for
the (separately-built) `permit_checklist_for` tool.

## Source-of-truth references

- **PRD §5.2 / §6.3** — hand-curate `permit_rules` for the demo cases; hour-0–2 deliverable is
  the horeca catalogue with cost + lead-time per item.
- **data-shortlist §4 / §4a** — the de-facto spec: rule shape, ~10 verified horeca permits with
  URLs, critical-path ordering, the build method, and the "no invented numbers" rule.
- **data-tiers.md** — `permit_checklist_for` is a thin Soda Straw → Postgres wrapper; it cannot
  read a YAML directly. The YAML is the source artifact; a Postgres table is the read path.

## Scope

**In scope**
- The verified-fetch workflow (the "fetch the permits" half).
- `permit_rules.yaml` — **horeca deep**, **retail + consultant thin scaffolds**.
- `droomzaak.permit_rules` Postgres table (migration-managed).
- Loader plumbing: `datasets/permit_rules/clean.py` → canonical parquet → `load_to_supabase.py`.
- A validation test over the YAML.

**Out of scope (separate follow-ups)**
- The `permit_checklist_for` agent tool itself (`/new-tool` + `add-agent-tool`).
- `sector_attributes.yaml` (the canonical "company topology"). Coupling handled below.

## Decisions (from brainstorming)

1. **Approach:** curated, frozen, human-verified YAML — *never runtime scraping* — with
   `web_search` (Tavily) as the explicit official-domain fallback for off-script questions.
2. **Sector breadth:** horeca fully verified; retail + consultant as thin scaffolds
   (KBO/BTW baseline + 1–2 sector-specific triggers each), so the engine stays generic.
3. **`sector_attributes` is out of scope**, but `permit_rules` keys off it — handled by an
   inline attribute vocabulary (section C).
4. **`cost` is a tagged union** (section B), so the "no invented number" rule is structural,
   not a convention.

## A. Fetch / verify workflow

A **Friday one-shot → frozen artifact**, per data-shortlist §4:

1. **Seed from §4a** — ~90% of horeca facts are already tabulated with verified URLs; this is
   grounding + gap-fill, not a from-scratch crawl.
2. **WebFetch** the clean-HTML official pages → LLM drafts rows:
   `stad.gent`, `favv-afsca.be`, `vlaanderen.be/epb-eisen`, `unisono.be`, `economie.fgov.be`.
3. **Browser-curate** the WAF-blocked / JS sources via the `browser-data-curation` skill
   (Claude-in-Chrome MCP): **VLAREM-wegwijzer** (`vlaremwegwijzer.navigator.emis.vito.be`,
   omgevings class/rubriek) and **VLAIO** (`vlaio.be`, 403 on server fetch).
4. **Human verifies** trigger logic + `depends_on` order. Every row carries `source_url`.
5. **Runtime safety net:** `web_search` (Tavily), official-domain-biased, links-only — catches
   off-script jury questions; never the rehearsed path.

The ondernemingsloketten (Liantis, Securex, Acerta, Partena, Xerius, Group S, UCM, Eunomia)
are **downstream hand-off destinations**, not data sources — no public API. Their starter
guides + the official pages above are the grounding; the deep-links in the package point to them.

## B. `permit_rules.yaml` schema

```yaml
# --- attribute vocabulary (see section C) ---
attributes:
  horeca:
    serves_alcohol: [none, gegiste, sterke]
    seating: [none, indoor, terrace]
    takeaway_only: bool
    hot_kitchen_frying: bool
    capacity_seats: int
    renovation: bool
    music: bool
  retail:
    food_retail: bool
    signage: bool
  consultant:
    home_based: bool
    employees: int

# --- rules ---
rules:
  - permit: "Drankvergunning gegiste dranken"
    nace_prefix: ["56"]                       # NACE family this rule belongs to
    applies_when: {serves_alcohol: [gegiste, sterke]}
    official_url: "https://stad.gent/.../drankvergunning/...vaste-drankgelegenheid"
    source_url:   "https://stad.gent/.../drankvergunning/...vaste-drankgelegenheid"
    explainer: "Vergunning voor het schenken van gegiste dranken (bier/wijn)."
    cost: {type: none_published}
    lead_time_days: 30
    depends_on: ["KBO", "horeca-attest"]
    status: active                            # active | ended_2025
```

### `cost` — tagged union (exactly three variants)

```yaml
# variant 1 — no published fee (horeca-attest, drankvergunning, brandweer)
cost: {type: none_published}

# variant 2 — a fixed, verifiable amount. Optional modifiers:
#   period: one_time (default) | annual      approx: bool (default false)
cost: {type: fixed, eur: 105.50, period: one_time, note: "KBO-loket inschrijving 2026"}
cost: {type: fixed, eur: 100.58, period: annual, approx: true, note: "FAVV heffing starter 2025"}

# variant 3 — calculator-based; we must NOT invent a number (Unisono, terras-belasting, EPB)
cost: {type: simulator, url: "https://www.unisono.be/.../simulator"}
```

**Validation rules:** `cost.type ∈ {none_published, fixed, simulator}`; `eur` required iff
`fixed`; `url` required iff `simulator`; `period ∈ {one_time, annual}` when present.

### Horeca rows (the ~10 from §4a)
horeca-attest (umbrella) · FAVV toelating · drank gegiste · sterkedrank (+college machtiging) ·
omgevingsvergunning milieu (frying → rubriek 45.4.d; cooling ≥5kW → 16.3.2°; melding kl.3 /
vergunning kl.2) · terrasvergunning · Unisono · brandveiligheidsattest (≥100 m²) · EPB
(renovation) · KBO + BTW + soc.fonds baseline.

**Critical-path `depends_on` (hero):** soc.verzekeringsfonds → KBO → BTW → FAVV → drank →
omgevings melding/vergunning → horeca-attest (umbrella) → terras → Unisono → EPB.

### Retail / consultant scaffolds
- **retail (NACE 47.\*):** KBO/BTW baseline + FAVV (if `food_retail`) + signage permit (if `signage`).
- **consultant (NACE 70/74.\*):** KBO/BTW baseline only (home-based / employees rarely add permits).

## C. The `sector_attributes` coupling (handled gap)

`sector_attributes.yaml` is out of scope, but `applies_when` keys off its attribute taxonomy.
Resolution: the attribute vocabulary is **defined inline at the top of `permit_rules.yaml`**
(the `attributes:` block above). The future canonical `sector_attributes.yaml` MUST adopt these
keys verbatim — noted in both files. This keeps `permit_rules.yaml` self-contained and
verifiable now, with one clear migration point later.

## D. Plumbing

### Table (via `supabase-schema-sync` — read-only MCP, idempotent script, STOP-and-wait)
`droomzaak.permit_rules`:

| column | type | notes |
|---|---|---|
| `permit` | text | display name |
| `nace_prefix` | text[] | NACE families this rule applies to |
| `applies_when` | text | JSON-encoded attribute conditions (see note) |
| `official_url` | text | deep-link shown to the founder |
| `explainer` | text | one-line NL explainer |
| `cost` | text | JSON-encoded tagged union (section B) |
| `lead_time_days` | int | nullable |
| `depends_on` | text[] | ordering / prerequisites |
| `status` | text | `active` \| `ended_2025` |
| `source_url` | text | provenance |

> **`applies_when` / `cost` are JSON-encoded `text`, not `jsonb`.** The `permit_checklist_for`
> tool fetches rules by NACE family and evaluates conditions in Python — it never needs
> SQL-side JSON operators. `text` makes the DuckDB→Postgres load trivially correct (text→text,
> like every other column) and the test as simple as the existing loader tests. Upgrading to
> `jsonb` later is a one-line migration + a `SELECT_LIST` cast, with no change to the YAML or
> `clean.py`.

Migration → folded into `supabase/migrations/` + `schema.sql` regenerated + `QUICK_REFERENCE.md`
updated. **Column order must match the clean.py SELECT** (position-based INSERT).

### Loader
- `datasets/permit_rules/clean.py` — reads `permit_rules.yaml`, emits canonical parquet
  (`applies_when` / `cost` serialized as JSON text → cast to jsonb on load), one row per rule.
- Add `"permit_rules"` to `build.py` `ORDER` and to `load_to_supabase.py` `TABLES`.

### Test
A pytest over the YAML (no live calls): YAML parses; every rule has the required keys; every
`applies_when` key exists somewhere in the `attributes:` vocabulary (flattened across sectors —
avoids needing a nace→sector map in this artifact); `depends_on` references resolve to other
`permit` names; the `cost` union holds (type enum + `eur`/`url` presence rules); every row has a
`source_url`.

## Verification checks

- `uv run python pipelines/droomzaak/build.py` produces `data/canonical/permit_rules.parquet`.
- `load_to_supabase.py permit_rules` DELETE+INSERTs idempotently into `droomzaak.permit_rules`.
- `uv run pytest` — the validation test passes.
- Manual: every horeca row resolves to a live official URL.

## Risks

- **Curated rules may be wrong in edge cases** (PRD §6.1). Mitigation: scope tight to the demo
  sectors; where uncertain the agent says *"Dit wil je bevestigen bij Stad Gent / FAVV"* and
  points to a human — never fakes certainty.
- **Source URLs rot.** Mitigation: `source_url` per row + the Friday human-verify pass.
