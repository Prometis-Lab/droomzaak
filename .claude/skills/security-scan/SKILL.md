---
name: security-scan
description: Use before any commit (it is the security stage of /ship) and when the user mentions "security scan", "secrets check", "Aikido", "SAST", or touches auth/data-access/external-fetch/secrets. Runs the deterministic gate (Opengrep/Semgrep + Betterleaks/gitleaks via security-gate.sh) and applies the Aikido-style checklist, producing the sponsor-facing report. The script's exit code owns pass/fail — not the model.
---

# Security scan

Sponsor **Aikido** audits this build. The gate is **deterministic** (a script), with the model triaging — never deciding pass/fail. Aikido's own OSS is the credible stack: **Opengrep** (their SAST engine), **Betterleaks** (secrets, by gitleaks' original author), **Safe Chain** (supply-chain).

## 1. Run the deterministic gate
```
.claude/hooks/security-gate.sh        # full scan (history + working tree + SARIF report) — for /ship
.claude/hooks/security-gate.sh fast   # working-tree + targeted rules — for the optional commit hook
```
It prefers Opengrep + Betterleaks, falls back to Semgrep CE + `gitleaks`. For SAST it uses a **local ruleset** (`.cache/semgrep-rules/{python,javascript,typescript}`) when present — offline-safe — and only falls back to the network Semgrep registry (`p/default`, `p/python`…) when that clone is absent (it WARNs in that case). **Missing tool → loud WARN + continue (exit 0 with a warning); real finding → exit 2 (block).** A scanner you can't install must **never** read as "clean" — if everything WARNs, say "no scanner ran — install via /bootstrap", don't report PASS.

Exit codes: `0` = clean (or only WARNs), `2` = findings → block. Capture the SARIF as the report artifact (the thing you'd show the judge).

## 2. Apply the Aikido-style checklist (categories borrowed from the MIT `anthropics/claude-code-security-review`)
On the changed diff, confirm:
- **Secrets** — no keys/tokens in code or committed files; `.env*` not committed (only `.env.demo.example`); no secret in a URL/query/log.
- **Injection** — SQL is **parameterized** (no string-formatted model/user input); no command injection; no `eval`/`exec` on model output; YAML via `safe_load`; no unsafe deserialization.
- **Soda Straw boundary** — analytical reads go through the straw, not direct Postgres/DuckDB; token is `agent_*` read-only (`rules/data-tiers.md`).
- **SSRF / fetch** — OSM/Places/ORS/Street View/Tavily URLs built from validated params, not raw model output; timeouts + caps.
- **Web** — FastAPI CORS not `*` in prod; route input validation; the package renderer escapes user/LLM text; no PII in the shareable `/pakket/<id>` URL.
- **AuthZ / data exposure** — Belfirst per-company rows never on the founder path (aggregates only); no facial-image/PII scraping.
- **Supply chain** — deps pinned (`uv.lock`, `package-lock.json`); `Safe Chain` recommended at setup.

**Suppressing a verified false-positive (so the gate clears):** put `# nosemgrep` on the finding's *anchor line* — the statement start (e.g. the `con.execute(` line), **not** the closing paren of a multi-line call, or it won't match. Prefer a **bare** `# nosemgrep`: the offline local ruleset (`.cache/semgrep-rules`) path-prefixes rule IDs (`cache.semgrep-rules.python.…`), so a named `# nosemgrep: <rule>` silently fails to suppress (it would only match under the network registry fallback). Suppress only a genuine false-positive — e.g. an internal-only identifier f-stringed into SQL while the runtime value is bound via `?` — and keep the SAST-note comment explaining why.

## 3. Report
```
Scan: gate exit 0 / 2 / WARN(no scanner)
SAST: <file:line rule severity> …
Secrets: …
Checklist: secrets ✓/✗ · injection ✓/✗ · straw ✓/✗ · SSRF ✓/✗ · web ✓/✗ · authz ✓/✗ · supply-chain ✓/✗
Verdict: PASS / BLOCK
```
BLOCK if the gate exits non-zero or any Critical/High checklist item fails. `/ship` does not commit on BLOCK.

## Two ways to run Semgrep (they coexist)
- **Deterministic CLI gate (source of truth for `/ship`):** `security-gate.sh` shells out to `semgrep`/`opengrep` + `gitleaks`/`betterleaks` and returns an **exit code** (0/2). This is what gates commits — simple, offline, audit-credible.
- **Interactive MCP (ergonomics):** the **`semgrep` MCP server** (`semgrep-mcp`, in `.mcp.json`, runs locally via `uvx`) lets you scan mid-session as a tool call and get structured findings without shelling out. Use it while building; the gate script still owns pass/fail for the commit. (gitleaks has no first-party local MCP — it stays CLI. GitHub's secret-scanning MCP is remote-only; Aikido's MCP plugin needs a cloud account — both optional.)

A scanner is **real software** (an AST/regex engine), so a *skill can't be* one — our `security-scan` skill *orchestrates* it. Nothing needs a heavy install, though: `uvx semgrep` / `uvx semgrep-mcp` fetch-and-cache on first run; secrets need `gitleaks` (brew/binary/docker) or `betterleaks`.

## Install (if the gate WARNs that tools are missing)
`/bootstrap` covers it. Quick refs: `uvx semgrep --version` · `brew install gitleaks` (or Betterleaks) · `git clone --depth 1 https://github.com/semgrep/semgrep-rules .cache/semgrep-rules` (gitignored — makes SAST offline-safe for **both** Semgrep CE and Opengrep; Opengrep ships no default rules, and the gate prefers this local clone over the network registry for either engine). `Safe Chain`: `curl -fsSL https://github.com/AikidoSec/safe-chain/releases/latest/download/install-safe-chain.sh | sh`.
