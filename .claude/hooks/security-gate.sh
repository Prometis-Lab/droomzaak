#!/usr/bin/env bash
# Droomzaak security gate — the SINGLE source of truth for the security scan.
# Called from: /ship (security stage), .pre-commit-config.yaml, and the optional PreToolUse hook.
#
# Usage:
#   security-gate.sh         # full scan: secrets (working tree + git history) + SAST, writes SARIF
#   security-gate.sh fast    # working-tree only + targeted rules (for the commit-time hook)
#
# Engine preference = Aikido OSS (Opengrep SAST + Betterleaks secrets), with Semgrep CE + gitleaks
# as fallbacks. Degrade-gracefully contract:
#   - a MISSING tool  -> loud WARN, do NOT fail (so a 12h build isn't bricked)
#   - a real FINDING  -> exit 2 (block the commit)
# A scanner you can't install must never read as "clean" — the WARN lines make that explicit.

set -uo pipefail
MODE="${1:-full}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 1

findings=0
ran_sast=0
ran_secrets=0
warn() { printf '  \033[33m[WARN]\033[0m %s\n' "$*" >&2; }
ok()   { printf '  \033[32m[ OK ]\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m[FAIL]\033[0m %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "── Droomzaak security gate (${MODE}) ─────────────────────────────"

# ── Secrets ────────────────────────────────────────────────────────────
# Prefer Betterleaks (Aikido), fall back to gitleaks. .gitleaks.toml allowlists *.example.
if have betterleaks; then
  ran_secrets=1
  betterleaks dir . || findings=1
  [ "$MODE" = "full" ] && { betterleaks git . || findings=1; }
  ok "secrets scanned (betterleaks)"
elif have gitleaks; then
  ran_secrets=1
  gitleaks dir --no-banner . || findings=1
  [ "$MODE" = "full" ] && { gitleaks git --no-banner . || findings=1; }
  ok "secrets scanned (gitleaks)"
else
  warn "no secrets scanner (install gitleaks or betterleaks — see /bootstrap). NOT a clean result."
fi

# ── SAST ─────────────────────────────────────────────────────────────────
# Prefer Opengrep (Aikido engine; needs a local ruleset), fall back to Semgrep CE via uvx.
if have opengrep; then
  ran_sast=1
  RULES="${OPENGREP_RULES:-${ROOT}/.cache/semgrep-rules}"
  if [ -d "$RULES" ]; then
    opengrep scan -f "$RULES/python" -f "$RULES/javascript" -f "$RULES/typescript" --error . || findings=1
    ok "SAST scanned (opengrep)"
  else
    warn "opengrep present but no ruleset at $RULES — clone github.com/semgrep/semgrep-rules there (Opengrep ships no default rules)."
  fi
elif have semgrep || have uvx; then
  ran_sast=1
  SEMGREP="semgrep"; have semgrep || SEMGREP="uvx semgrep"
  if [ "$MODE" = "fast" ]; then
    $SEMGREP scan --quiet --error --config p/python --config p/javascript --config p/react --config p/secrets . || findings=1
  else
    $SEMGREP scan --quiet --error --config p/default --sarif --output security.sarif . || findings=1
    [ -f security.sarif ] && ok "SARIF written to security.sarif"
  fi
  ok "SAST scanned (semgrep CE)"
else
  warn "no SAST engine (install semgrep via 'uvx semgrep' or opengrep — see /bootstrap). NOT a clean result."
fi

# ── Verdict ────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────────────────────────"
if [ "$ran_sast" -eq 0 ] && [ "$ran_secrets" -eq 0 ]; then
  warn "NO scanner ran — this is NOT a pass. Install tools via /bootstrap before the Aikido audit."
  # exit 0 so a tools-less machine isn't bricked, but the WARN is unmissable and /ship surfaces it.
  exit 0
fi
if [ "$findings" -ne 0 ]; then
  bad "security findings detected — fix before committing (or justify explicitly)."
  exit 2
fi
ok "security gate passed (secrets=${ran_secrets} sast=${ran_sast})."
exit 0
