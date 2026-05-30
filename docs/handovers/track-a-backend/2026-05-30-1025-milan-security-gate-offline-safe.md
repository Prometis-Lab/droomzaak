# Handover — security gate: offline-safe + scoped to first-party code

**Track:** track-a-backend (cross-cutting tooling) · **Author:** milan · **2026-05-30 10:25**

## State now
The `/ship` security gate (`.claude/hooks/security-gate.sh`) is **green and offline-safe**. Before today it blocked *every* commit: it scanned the whole tree (incl. vendored Apache-2.0 skills → 2 phantom findings) and ran SAST against the network Semgrep registry (dies on flaky Wi-Fi). Now: `security gate passed (secrets=1 sast=1)`, exit 0, in both `full` and `fast` modes. Committed in `401e619`.

Installed locally (NOT in git — teammates must replicate): **gitleaks 8.30.1** (`brew install gitleaks`) and the **semgrep ruleset** at `.cache/semgrep-rules` (gitignored).

## What I just did (commit `401e619`)
- `.semgrepignore` (new) — scope SAST to our code (exclude vendored, reference, inherited, deps, build/cache, sarif).
- `.gitleaks.toml` — allowlist the same out-of-scope dirs (the rules clone is full of planted test secrets → 380 false positives without this).
- `security-gate.sh` — prefer local ruleset over registry; build `--config` from the language dirs that *exist* so a partial clone degrades to the registry instead of emitting a phantom finding (review catch).
- Docs: `/bootstrap` §5, `TEAM-SETUP.md` §5, `security-scan` SKILL.md — install + offline-safe behaviour.

## Next concrete step
Nothing blocking. For the **Aikido demo specifically**, install the sponsor's native engines so the gate runs on their tooling instead of the gitleaks/Semgrep-CE fallbacks: `betterleaks` (secrets) + `opengrep` (SAST). The gate already prefers them when present (`have opengrep` / `have betterleaks` branches).

## Open questions / blockers
- None for this change. (Unrelated: `inherited/` prometis_toolkit geocoder + `.env.demo` secrets are delivered out-of-band — pre-existing, not affected here.)

## Exact entry points
- Gate: `.claude/hooks/security-gate.sh` — SAST branch ~`:57-90`, secrets ~`:30-44`.
- Run it: `bash .claude/hooks/security-gate.sh full` (or `fast`).
- Team setup: `TEAM-SETUP.md` §5 · `/bootstrap` §5 · `.claude/skills/security-scan/SKILL.md`.
- Allowlists: `.gitleaks.toml` · `.semgrepignore`.

## Gotchas hit
- **Teammates need two local-only pieces** or the gate degrades: `brew install gitleaks` + `git clone --depth 1 https://github.com/semgrep/semgrep-rules .cache/semgrep-rules`. Both now in onboarding docs.
- Scanner-ignored ≠ removed from repo — vendored skills are still fully git-tracked (86 files); we only skip *scanning* them.
- `semgrep` exits **7** on a missing `--config` path; `|| findings=1` would misread that as a finding → hence the build-from-existing-dirs guard.
- gitleaks/semgrep do **not** honour each other's ignore files — they need separate scoping (`.gitleaks.toml` vs `.semgrepignore`).

## Verification
```
bash .claude/hooks/security-gate.sh full   # expect: security gate passed (secrets=1 sast=1), exit 0
```
Offline proof (registry blocked, still passes via local rules):
```
HTTPS_PROXY=http://127.0.0.1:1 bash .claude/hooks/security-gate.sh full   # exit 0, "semgrep CE, local rules"
```
