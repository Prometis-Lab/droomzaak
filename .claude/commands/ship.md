---
description: The commit gate — code review → simplify → security scan → conventional commit. Never pushes.
argument-hint: [optional commit subject]
---

# /ship

Run the commit gate, in order, on the current changes. **Stop and report at the first failure — do not commit until every stage passes.** Never run `git push`.

## 0. Scope & triviality check
Run `git status` + `git diff --stat`. If the diff is **trivial or docs-only** (typo, comment, a `docs/` or `*.md` change with no code), you may skip the review/simplify gauntlet — go straight to stage 4 — but still run stage 3 (security) since secrets can hide anywhere.

## 1. Code review  →  `code-reviewer`
Dispatch the `code-reviewer` agent on the diff. It runs the build/type-check first (`uv run pytest backend/tests` and/or `npm run build`). **If the build fails or the verdict is NEEDS-CHANGES (Critical/High), STOP** — fix, then restart `/ship`.

## 2. Simplify  →  `code-simplifier`
Dispatch `code-simplifier` on the changed diff. It must preserve behaviour (re-runs the relevant test/build). Apply its edits. If it flags a behaviour-changing simplification, that's a design decision — handle it, don't auto-apply.

## 3. Security  →  `security-reviewer`
Dispatch `security-reviewer` (runs the `security-scan` skill → `.claude/hooks/security-gate.sh`). **If the gate exits 2 (findings) or the verdict is BLOCK, STOP** — fix the findings. If it WARNs "no scanner ran", tell the user the scan was not actually performed and recommend `/bootstrap` before relying on the gate (do not treat WARN as PASS for an audit-day commit).

## 4. Commit
Only after 1–3 pass: `git add` the intended files, then commit with a **Conventional Commits** message (`feat|fix|refactor|test|chore|docs|perf|build|ci|revert(scope): subject`) — the repo's `.githooks/commit-msg` enforces this. Use `$ARGUMENTS` as the subject if provided; otherwise write a concise one from the diff. Reference the spec in `docs/specs/` if there is one.

End the conventional message with the co-author trailer the harness requires. **Do not push** — pushing is a deliberate human action (and is denied in settings).

## 5. After
Remind (don't auto-run unless asked) that `/handover` is worth running if this finished a meaningful chunk.
