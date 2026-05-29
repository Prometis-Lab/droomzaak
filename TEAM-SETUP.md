# Team setup — Droomzaak

Everyone who clones this repo: do this once. The fastest path is to open Claude Code here and run **`/bootstrap`**, which automates and checks the steps below. This file is the human-readable version.

## What you get for free on clone (no install)
- **Agents** (`.claude/agents/`, 10) and **skills** (`.claude/skills/`, 15 incl. 5 vendored) load automatically — `/agents` and `/help` should list them.
- **Settings** (`.claude/settings.json`): everything is allowed except `git push` (denied — push manually). No babysitting; commits flow, but use **`/ship`** so reviews run first.

## What needs one-time setup

### 1. superpowers plugin (brainstorming, plans, TDD, debugging)
It's declared in settings, but force-enable-on-clone is unreliable ([claude-code#32606](https://github.com/anthropics/claude-code/issues/32606)). In Claude Code:
```
/plugin install superpowers@claude-plugins-official
# if not found there:
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```
(On Windows the official marketplace isn't pre-registered — add it first.)

### 2. Secrets — `.env.demo`
```
cp .env.demo.example .env.demo      # then fill it in (gitignored; NEVER commit)
```
Required for the demo: `SODA_STRAW_URL` + `SODA_STRAW_TOKEN` (sign up at sodastraw.ai/trial/start, connect Postgres, mint an `agent_*` read token), `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `OPENROUTESERVICE_API_KEY`, `TAVILY_API_KEY`. Export them in your shell (or put them in gitignored `.claude/settings.local.json`).

### 3. MCP servers
On first use you'll be **prompted once** to approve the project MCP servers (`soda-straw`, `think-strategies`, `sequential-thinking`, `context7`). Approve them, or run `/mcp`. `.mcp.json` won't parse if `SODA_STRAW_TOKEN` is unset, so set it first.

### 4. Git hooks
```
git config core.hooksPath .githooks          # activates the conventional-commits check
# optional, recommended before the Aikido audit:
uvx pre-commit install                        # deterministic security floor (.pre-commit-config.yaml)
```

### 5. Security scanners (optional, for the Aikido audit)
The `/ship` security stage uses whatever is installed and **warns** (doesn't silently pass) when none is:
```
uvx semgrep --version                         # SAST (Semgrep CE) — or Aikido's Opengrep
brew install gitleaks                         # secrets — or Aikido's Betterleaks
curl -fsSL https://github.com/AikidoSec/safe-chain/releases/latest/download/install-safe-chain.sh | sh   # supply-chain
```

### 6. Inspiration materials (optional)
`git clone` any public repos worth learning from (map apps, MapLibre/FastAPI/agent examples) and/or drop a prior implementation under `reference/` so `reference-scout` can mine them for ideas. **`reference/` is gitignored — it stays local, never committed.** Until then the scout works from the PRD + the architecture summary in CLAUDE.md.

## Daily workflow
`brainstorm → /spec (≥8/10) → implement → /ship (review→simplify→security→commit) → /handover`. Never `git push` via the agent. Source-of-truth precedence: **data-shortlist > PRD** (see CLAUDE.md "Known corrections").
