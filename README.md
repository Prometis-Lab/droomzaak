<p align="center">
  <img src="droomzaak.png" alt="droomzaak" width="280">
</p>

<h1 align="center">droomzaak</h1>

<p align="center"><em>Ondernemen, dat is een zaak van dromen.</em></p>

---

Starting a business in Ghent means drowning in tabs — VLAIO, the city's ondernemerspaginas, a Liantis blog, Reddit, three open Excel sheets and Google Maps — long before you ever sign anything. **Droomzaak** ("dream company") turns that overwhelm into one guided, map-anchored journey. You say a single sentence about the business you dream of — *"a small vegan bistro near Vrijdagmarkt"* — and an agent does the reading you used to do at midnight, over 60+ curated Belgian open datasets. Fifteen minutes later you walk away with a printable *Droomzaak-pakket*: your dream, the numbers, a scored location, the permits, the funding, and the links to the people who actually help you found it.

Dream-first, not form-first. The data frames your dream — it never gates it. Where the answer is uncertain, the agent says so and points you to a human (OOG, FAVV, Stad Gent) instead of faking certainty.

Built by [Prometis Lab](https://prometislab.org) for the Hackers & Ravers company cup, aligned with the Stad Gent / District09 one-stop-shop-for-starters challenge.

## The journey, in five chapters

1. **Droom** — Tell us about the business you dream of. One sentence. We pull out your sector, scale and neighbourhood, ask one or two warm follow-ups, and your *Droomkaart* starts to fill in.
2. **Niche** — See who's already doing it. Every comparable venue in Ghent on the map, how fast the niche is growing, peer numbers and closures — so you know what you're walking into.
3. **Waar** — Find your spot. Every Ghent neighbourhood scored on your target customers, competition, footfall, rent, walkability and roadworks. The top candidate addresses, ranked, each with a plain-language *"why here"*.
4. **Vergunningen & geld** — What you'll need. A permit checklist branched to your sector and address (with costs, timings and official links), a subsidy shortlist checked against your profile, and a legal-form recommendation — eenmanszaak or BV/SRL.
5. **Droomzaak-pakket** — Your take-away. One page: a short dream narrative, a *"your Tuesday morning"* simulation, your chosen spot, all the numbers and checklists, and a hand-off block to Stad Gent, FAVV, FOD, VLAIO and the ondernemingsloketten. Download as PDF or share the link.

## How it's built

A five-chapter state machine wraps a provider-neutral agent loop (OpenAI + Anthropic) on a React + MapLibre canvas. Two data tiers, never crossed: the map renders from a fast local cache, while **every analytical claim the agent makes is brokered through the [Soda Straw](https://sodastraw.ai/) MCP into a Postgres warehouse** — one straw, one audit log, visible in the debug overlay. The warehouse is loaded from open data: Statbel, FOD Financiën, KBO, Stad Gent Open Data, OpenStreetMap and VLAIO.

See [`droomzaak-prd.md`](droomzaak-prd.md) for the full vision and architecture, and [`CLAUDE.md`](CLAUDE.md) for the build conventions.

## Setup

After cloning, point git at the shared hooks directory once:

```sh
git config core.hooksPath .githooks
```
