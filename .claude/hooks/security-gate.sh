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

# Scope the local clone to its security rules only. The full semgrep-rules tree
# bundles non-security namespaces (lang.maintainability, lang.correctness,
# lang.best-practice, react.portability.i18next) that flood a *security* gate
# with lint noise. Every security rule lives under a `security/` subdir
# (python/lang/security, python/flask/security, python/sqlalchemy/security, …),
# so collecting those subtrees keeps exactly the rules this gate exists for.
# Echoes one dir per line for whichever of the given language roots exist.
security_rule_dirs() {  # args: language names
  local lang
  for lang in "$@"; do
    [ -d "$RULES/$lang" ] && find "$RULES/$lang" -type d -name security 2>/dev/null
  done
}

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
    FLAGS=()
    while IFS= read -r d; do FLAGS+=(-f "$d"); done < <(security_rule_dirs python javascript typescript)
    if [ "${#FLAGS[@]}" -gt 0 ]; then
      opengrep scan "${FLAGS[@]}" --error . || findings=1
      ok "SAST scanned (opengrep, security rules)"
    else
      warn "opengrep ruleset at $RULES has no python/javascript/typescript security rules — is it a full clone of github.com/semgrep/semgrep-rules?"
    fi
  else
    warn "opengrep present but no ruleset at $RULES — clone github.com/semgrep/semgrep-rules there (Opengrep ships no default rules)."
  fi
elif have semgrep || have uvx; then
  ran_sast=1
  SEMGREP="semgrep"; have semgrep || SEMGREP="uvx semgrep"
  RULES="${SEMGREP_RULES:-${ROOT}/.cache/semgrep-rules}"
  # Prefer a local ruleset (offline-safe — the demo machine's network may be flaky);
  # scope it to the `security/` subtrees only (security_rule_dirs) so the gate runs
  # security rules, not the clone's maintainability/correctness/portability lint. A
  # partial/shallow clone with no security dirs degrades to the registry instead of
  # erroring (a missing --config path makes semgrep exit 7, which `|| findings=1`
  # would misread as a finding). Fall back to the Semgrep registry (p/…) otherwise.
  CFG=()
  while IFS= read -r d; do CFG+=(--config "$d"); done < <(security_rule_dirs python javascript typescript)
  if [ "${#CFG[@]}" -gt 0 ]; then
    SRC="semgrep CE, local security rules"
  else
    warn "no local ruleset at $RULES (clone github.com/semgrep/semgrep-rules there for offline SAST) — using the Semgrep registry, which needs network."
    if [ "$MODE" = "fast" ]; then
      CFG=(--config p/secrets --config p/security-audit)
    else
      CFG=(--config p/security-audit)
    fi
    SRC="semgrep CE, registry"
  fi
  if [ "$MODE" = "fast" ]; then
    $SEMGREP scan --quiet --error "${CFG[@]}" . || findings=1
  else
    $SEMGREP scan --quiet --error "${CFG[@]}" --sarif --output security.sarif . || findings=1
    [ -f security.sarif ] && ok "SARIF written to security.sarif"
  fi
  ok "SAST scanned (${SRC})"
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
