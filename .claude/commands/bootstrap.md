---
description: One-time team onboarding — enable plugins, approve MCP servers, check secrets, wire git hooks, report what's missing.
---

# /bootstrap

Get a freshly-cloned Droomzaak workspace ready. Run each step, then print a checklist of what's done vs. what the human still needs to do. **Don't install anything destructive or push; just enable/verify and report.**

## 1. superpowers plugin (generalisable methodology layer)
- `/plugin marketplace list` — is `claude-plugins-official` present (auto on macOS; on Windows it isn't pre-registered)?
- If superpowers isn't enabled: try `/plugin install superpowers@claude-plugins-official`. If that marketplace doesn't carry it, add the community one: `/plugin marketplace add obra/superpowers-marketplace` then `/plugin install superpowers@superpowers-marketplace`.
- Confirm with `/plugin` that superpowers is enabled (force-enable on clone via `enabledPlugins` is best-effort, claude-code#32606 — this step is the reliable path).

## 2. Project MCP servers (`.mcp.json`)
- These prompt once for approval on first use (by design). Tell the user to approve `soda-straw`, `think-strategies`, `sequential-thinking`, `context7`, `semgrep`, `supabase` when prompted (or run `/mcp`). `semgrep` runs locally via `uvx semgrep-mcp` (interactive scan; the `/ship` gate uses the CLI). `supabase` is **read-only** (`--read-only`) for schema inspection — DDL/DML goes through `supabase-schema-sync`, never the MCP.
- They need these env vars exported (or in gitignored `.claude/settings.local.json`): `SODA_STRAW_URL`, `SODA_STRAW_TOKEN`, `SUPABASE_PROJECT_REF`, `SUPABASE_ACCESS_TOKEN`, `CONTEXT7_API_KEY` (optional). Report which are unset (`printenv` check). `.mcp.json` fails to parse if a referenced var (e.g. `SODA_STRAW_TOKEN`, `SUPABASE_PROJECT_REF`) is unset with no default — so flag those loudly.

## 3. Secrets (`.env.demo`)
- Check `.env.demo` exists (copy from `.env.demo.example` if not — but the human fills it). List which required keys are empty: `SODA_STRAW_TOKEN`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `OPENROUTESERVICE_API_KEY`, `TAVILY_API_KEY`. Never print values.

## 4. Git hooks
- The repo ships `.githooks/commit-msg` (conventional commits) but it's not active until wired: run `git config core.hooksPath .githooks` and confirm.
- Optional deterministic security floor: tell the user they can `uvx pre-commit install` to enable `.pre-commit-config.yaml` (recommended before the Aikido audit). Don't install it unless asked.

## 5. Security scanners (optional but recommended for the Aikido audit)
- Check availability: `semgrep`/`uvx semgrep`, `gitleaks`/`betterleaks`, `opengrep`. Report which are missing with the install one-liners (`brew install gitleaks`; `uvx semgrep --version`; Aikido `Safe Chain` install script). The `/ship` security stage WARNs (not passes) when none is present.

## 6. Reference source
- Check whether `reference/` holds inspiration materials (optional; cloned public repos and/or a prior implementation; gitignored). If empty, note that `reference-scout` simply works from the PRD + the architecture summary — nothing to install.

## 7. Sanity
- `jq . .claude/settings.json` and `jq . .mcp.json` parse OK; `/agents` lists the 10 agents; `/help` lists the 6 commands.

## Output
A tick-list: ✅ done / ⚠️ needs human action (with the exact command or key to set). End with the single most important next step.
