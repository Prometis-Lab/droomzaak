---
description: Adversarial pre-demo readiness check against the PRD's "demo succeeded" criteria.
argument-hint: [chapter or area, optional]
---

# /demo-check $ARGUMENTS

Dispatch the **`demo-readiness-reviewer`** agent (it uses think-strategies) before a rehearsal or the pitch.

It checks the build against PRD §6.3 (all seven "demo succeeded" criteria) and hunts the §6.1 failure modes: hardcoded happy-path, any analytical call bypassing the DataGateway, a chapter that never commits, faking certainty on permits, per-address rent, a stale/cancelled subsidy shown as eligible, a stray `places_popular_times`, provider/secret fragility, post-hour-6 scope creep.

Scope to `$ARGUMENTS` if given (e.g. "chapter 3"), else the whole flow. Output: a ranked list of high-confidence, demo-breaking findings + a go/no-go read + the one thing most likely to break on stage. Read-only — it reports, it doesn't edit.
