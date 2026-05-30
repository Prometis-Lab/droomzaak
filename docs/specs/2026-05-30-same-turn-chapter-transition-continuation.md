# Spec — Same-turn chapter-transition continuation

- **Date:** 2026-05-30
- **Track:** A (backend / agent)
- **Status:** Cleared — spec-critic 8.5/10 (GO), 2026-05-30. Ready for implementation.
- **Files in scope:** `backend/app/agent_loop.py`, `backend/app/droomzaak_chapters.py`, `backend/app/droomzaak_prompt.py`, `backend/tests/`
- **Skills:** `chapter-state-machine` (loop contract), `add-agent-tool` (loop gotchas), `data-tool` (gateway boundary)

---

## 1. Context & problem

When a founder triggers a chapter advance — e.g. in **Chapter 2 (Niche)** they type *"Ik wil mijn plek vinden"* — the agent advances to **Chapter 3 (Waar)** by committing `set_chapter_state(current_chapter="3_waar")`, and writes a reply that **promises results it never produces**:

> *"Mooi: we schakelen naar 'Waar'. We scoren buurten rond Dampoort op bakkerij‑potentieel en tonen meteen de heatmap en 3 concrete opties om te verkennen."*

Confirmed in `data/traces/71e69990e06641beaa588812c7f61b64.jsonl` line 5: the turn committed **only** `set_chapter_state` — no `score_locations`, no `rent_benchmark`, no heatmap. The founder must send a *second* message (*"Heb je iets kunnen vinden?"*) before locations appear.

### Root cause (three compounding facts)
1. **Tools are chapter-gated to the *current* chapter.** `droomzaak_chapters.py:105` calls `_chapter_tool_specs(chapter)` **before** the loop runs. In Chapter 2, `score_locations`/`rent_benchmark` are not in the allowlist (`droomzaak_prompt.py:19-26`), so the model cannot call them this turn.
2. **The transition patch applies *after* the loop.** `droomzaak_chapters.py:117-130` applies `set_chapter_state` patches only once `run_loop` has returned. The new chapter's tools/prompt take effect only on the *next* turn.
3. **No guidance for a transition reply.** Chapter 2's exit text (`droomzaak_prompt.py:191`) only says "set current_chapter='3_waar'". With no rule for what to *say*, the model fills the gap with an over-promising teaser — violating base Rule 8 ("No teaser, no promise") with nothing to enforce honesty.

### Goal
When the loop commits a `set_chapter_state` that **advances** `current_chapter`, `run_droomzaak_turn` must **re-expand the tool surface to the new chapter, re-prompt with the new chapter block, and continue the same loop within the same user turn**, so the agent actually runs the new chapter's required tools (`score_locations` + `rent_benchmark` + `show_layer` + `set_layer_heatmap` for Waar) and the founder sees real locations immediately.

### Non-goals
- Not changing how chapters are validated or persisted (`set_chapter_state` remains the only writer; sequential-only advance unchanged).
- Not building a parallel orchestrator (chapter-state-machine Rule 5: "reuse, don't fork").
- Not skipping more than one chapter per user turn.
- No provider branching (base Rule 6 / clean-room rule).

---

## 2. Design — `on_commit` continuation hook + `run.current_chapter_state` as single source of truth

Two genuine designs were considered:

- **A — outer loop in the wrapper (multiple `run_loop` calls).** Rejected as primary: each re-call rebuilds `messages` from `history + user_message`, so segment 2 needs a *synthetic* user directive; action/dataset aggregation and per-segment `pending_*` reset add fragility.
- **B — `on_commit` continuation hook inside `run_loop` (CHOSEN).** One `messages` list, one `AgentRun`, shared iteration budget. `run_loop` stays provider-neutral and chapter-agnostic; *all* chapter knowledge lives in the callback the wrapper supplies.

### Critical code facts this design is built on (verified against the source)
1. **`run.pending_reply` / `run.pending_actions` are OVERWRITTEN on every commit** (`agent_tools.py:151-152`: `run.pending_reply = reply`, `run.pending_actions = normalized`). They are **not** cumulative. Therefore at the moment `on_commit` fires, `run.pending_actions` holds **exactly this commit's** actions — no slice/`consumed` counter is needed, and the previous commit's actions are gone.
2. **`set_chapter_state` validation reads `run.current_chapter_state`** (`agent_tools.py:147` → `agent_validation.py:79-85` → `droomzaak_validation.validate_set_chapter_state`), using its `current_chapter` to enforce the exit condition and sequential-advance check. So the hook **must advance `run.current_chapter_state`** after a commit, or segment-2 validation runs against the wrong chapter.
3. **A rejected `set_chapter_state` fails the *entire* `apply_map_actions` call** (`agent_tools.py:149-150` returns `{"applied": False, "errors": ...}` and does **not** set `pending_reply`). So `run.pending_reply` stays `None`, the early-break guard at `agent_loop.py:208` is false, and `on_commit` is never invoked — the loop just continues and the model self-corrects. (This is exactly how E7 works.)
4. **Chapter-2 exit requires `niche_signals`** (`CHAPTER_EXIT_CONDITIONS["2_niche"]`, `droomzaak_validation.py:38`). The validator merges the patch into `current_state` before checking, so the 2→3 advance succeeds only if `niche_signals` is already in state (set on an earlier Chapter-2 turn) **or** included in the advancing patch.
5. **`run.datasets` IS cumulative** (handlers write `run.datasets[id] = ...`; never reassigned), so transient layers naturally accumulate across segments and `run_loop` returns the union — no extra work.

**Consequence — single source of truth.** Because `pending_actions` is overwritten, the post-loop reconstruction (current `droomzaak_chapters.py:117-130`) cannot see the bridge's advancing patch after segment 2 overwrites it. We therefore **make `run.current_chapter_state` the one canonical state**: the hook merges *every* commit's `set_chapter_state` patch into it (advancing or not), and the wrapper reads the final `run.current_chapter_state` instead of re-applying patches post-loop. The old post-loop patch loop is **removed**.

### 2.1 `run_loop` change (`agent_loop.py`)

Add one optional parameter and a small dataclass. **Default behaviour is byte-for-byte unchanged** (param defaults to `None` → today's early-break).

```python
@dataclass
class Continuation:
    """Returned by on_commit to keep the loop going after a commit."""
    tool_specs_neutral: list[dict]   # new tool surface (re-translated by the adapter)
    nudge_text: str                  # appended as a forcing nudge message (new chapter block + directive)
```

```python
# new signature param (keyword-only, after on_stage):
on_commit: Callable[[AgentRun, list], "Continuation | None"] | None = None,
```

Change **only** the early-break block (current lines 208-211):

```python
        if run.pending_reply is not None and any(
            tc.name == "apply_map_actions" for tc in response.tool_calls
        ):
            continuation = None
            if on_commit is not None:
                try:
                    continuation = on_commit(run, debug_stages)
                except Exception as exc:          # E9 — never crash the turn
                    _emit(debug_stages, "on_commit_error", {"error": str(exc)}, on_stage)
                    continuation = None
            if continuation is None:
                break  # early break after commit (unchanged default when on_commit is None)
            # Same-turn continuation: re-expand tools, re-prompt, keep looping.
            tools = adapter.translate_tool_specs(continuation.tool_specs_neutral)
            adapter.append_commit_nudge(messages, continuation.nudge_text)
            # Do NOT reset pending_reply: the next commit overwrites it (fact 1), and if
            # the continuation never commits, the (honest) bridge reply is the safe fallback.
        # falls through to the next while iteration
```

Notes:
- `append_commit_nudge` already exists on the adapter Protocol and appends a forcing nudge message — **role is adapter-specific** (`user` on Anthropic `agent_anthropic.py:61`; `system` on OpenAI `agent_openai.py:68`). Reused here to inject the new chapter block + directive. No new adapter method, no provider branching.
- The shared `while iterations < max_iterations` bound now covers both segments — continuation cannot exceed the per-turn iteration budget.
- The `nudge_used` commit-enforcement flag is independent and unaffected; if a continuation segment ends without committing, the existing nudge logic (line 175) may still fire once.
- The injected nudge message **is** persisted via `store.save_messages` (like the existing commit-nudge). This is intentional and consistent; design B's advantage over A is the single `messages`/`AgentRun`/budget, not "cleaner history".

### 2.2 Wrapper change (`droomzaak_chapters.py`)

Supply `on_commit`, make `run.current_chapter_state` canonical, and **remove** the post-loop patch loop (lines 117-130). The hook is the single place that knows about chapters.

```python
MAX_SAME_TURN_ADVANCES = 1  # advance at most one chapter per user turn

def _make_on_commit(run, transitions, debug_stages, frontend_context, action_log):
    advances = {"n": 0}
    def on_commit(_run, _stages):
        # fact 1: run.pending_actions holds EXACTLY this commit's actions.
        action_log.extend(run.pending_actions)           # accumulate union for the frontend
        advancing_to = None
        for a in run.pending_actions:
            if a.get("type") == "set_chapter_state":
                patch = a.get("patch", {})
                prev = run.current_chapter_state.get("current_chapter")
                # fact 2: advance the CANONICAL state the validator reads.
                run.current_chapter_state = apply_state_patch(run.current_chapter_state, patch)
                nxt = patch.get("current_chapter")
                if nxt and nxt != prev:
                    advancing_to = nxt
                    transitions.append({"from": prev, "to": nxt})
        if advancing_to is None or advances["n"] >= MAX_SAME_TURN_ADVANCES:
            return None
        advances["n"] += 1
        debug_stages.append({"stage": "same_turn_continuation", "detail": {"to": advancing_to}})
        # rebuild ONLY the new chapter block (base prompt already in messages) + a fresh
        # <chapter_state> snapshot so the model-facing state matches the injected chapter.
        block = build_chapter_block(run.current_chapter_state)
        state_snapshot = build_runtime_block(frontend_context, run.current_chapter_state)
        nudge = (
            f"Je bent nu in {advancing_to}. {block}\n\n{state_snapshot}\n\n"
            "Voer de verplichte calls van dit hoofdstuk uit en commit het eindresultaat "
            "met apply_map_actions. Je vorige reply was alleen een brug — deze commit "
            "levert het echte resultaat dat de gebruiker ziet."
        )
        return Continuation(tool_specs_neutral=_chapter_tool_specs(advancing_to), nudge_text=nudge)
    return on_commit
```

Wiring in `run_droomzaak_turn`:
```python
    run = AgentRun(..., current_chapter_state=state)   # canonical state lives here
    transitions: list[dict] = []
    action_log: list[dict] = []
    on_commit = _make_on_commit(run, transitions, debug_stages, frontend_context, action_log)
    result = await run_loop(..., on_commit=on_commit)

    state = run.current_chapter_state                  # single source of truth
    transitioned = len(transitions) > 0
    # union of every committed segment's actions (frontend executes these);
    # result["actions"] alone would be only the LAST commit (fact 1).
    final_actions = action_log or result["actions"]
    store.save_chapter_state(session_id, state)
```
**Exact edit sites (G1 — do not return `result["actions"]`, or the round-1 "only the last commit's actions reach the frontend" bug returns).** Remove the old patch loop (lines 117-130) and edit the four sites that read `state`/`result["actions"]`:

```python
    # turn_summary (was result["actions"]):
    "actions": [a.get("type") for a in final_actions],
    "chapter_transitioned": transitioned,
    ...
    return {
        "reply": result["reply"],
        "actions": final_actions,            # ← union, NOT result["actions"]
        ...
        "chapter_state": state,              # ← run.current_chapter_state
        "chapter_transitioned": transitioned,
        ...
    }
```

The DataGateway audit drain (line 133) is unchanged.

**Trace parity (G2):** to keep `chapter_state_patch_applied` fidelity now that the post-loop loop is gone, emit that debug stage inside the hook for *every* `set_chapter_state` patch (advancing or not), e.g. `debug_stages.append({"stage": "chapter_state_patch_applied", "detail": {"patch_keys": list(patch.keys())}})` — preserves today's trace shape.

- **`build_chapter_block(state)`** is extracted from `build_system_prompt` so the hook can render *just* the new chapter block (see 2.3).
- **No double application:** each commit's patch is merged into `run.current_chapter_state` exactly once, in the hook; the post-loop reconstruction is gone. There is now exactly one state reference.
- **`action_log` union** keeps every chapter's committed actions (incl. both `set_chapter_state` patches); duplicate `set_chapter_state` entries are harmless because the chapter rail is driven by the returned `chapter_state`, not by replaying actions.

### 2.3 Prompt change (`droomzaak_prompt.py`)

1. **Extract** the per-chapter block builder so it is reusable mid-loop:
   ```python
   def build_chapter_block(state: dict) -> str:
       chapter = state.get("current_chapter", "1_droom")
       return CHAPTER_PROMPT_BLOCKS[chapter](state)
   # build_system_prompt now = DROOMZAAK_BASE_PROMPT + "\n\n" + build_chapter_block(state)
   ```
2. **Honest-bridge rule** so the surfaced reply is never a lie even if continuation can't finish. Add to the base prompt Rules (near Rule 8):
   > *"When you advance the chapter (set_chapter_state with a new current_chapter), you will be re-prompted in the same turn with the new chapter's tools and asked to deliver its result — so do NOT claim results you have not yet produced. The reply attached to the advancing commit is a short bridge ('we gaan nu je plek zoeken'), in present/future tense, never 'hier zijn de 3 buurten' until score_locations has actually returned."*
3. **Chapter-2 exit guidance** (`_chapter2`, line 191): append — *"Bij de overgang naar 3_waar: zet `niche_signals` in dezelfde set_chapter_state-patch (vereist voor de hoofdstuk-uitgang) en schrijf een korte brug-zin (geen beloofde resultaten). Je krijgt direct daarna de Waar-tools om de buurten echt te scoren in dezelfde beurt."* — this is load-bearing: per fact 4, an advancing patch without `niche_signals` (when not already in state) is **rejected**, the whole commit fails, and the continuation never fires.

No allowlist change. No provider branching.

---

## 3. Edge cases

| # | Case | Required behaviour |
|---|---|---|
| E1 | Commit with **no** `set_chapter_state` | `on_commit` returns `None` → break (today's behaviour). |
| E2 | `set_chapter_state` patch that does **not** change `current_chapter` (e.g. only `candidate_locations`) | Not an advance → return `None` → break. |
| E3 | Second advance in the same turn (3→4) | Blocked by `MAX_SAME_TURN_ADVANCES=1`; return `None` → break. The new chapter's work happens next user turn. |
| E4 | Continuation segment exhausts `max_iterations` without committing | Loop ends; `run.pending_reply` = the (honest) bridge reply from the advancing commit (fact 1: not yet overwritten) → surfaces safely. `reply_source="committed"`. **`run.current_chapter_state` is already advanced** (hook ran on the bridge commit), so the chapter rail still moves — next turn resumes correctly in the new chapter. Trace shows the incomplete continuation. |
| E5 | New chapter's required tool errors (e.g. `score_locations` DataGateway failure) | Base Rule 4 still applies: one attempt, name the gap, `report_problem`, still commit `apply_map_actions`. Same as a normal Chapter-3 turn. |
| E6 | Advance lands in Chapter 5 (terminal) | Continuation runs Ch5 tools normally; `MAX_SAME_TURN_ADVANCES=1` prevents chaining beyond one. |
| E7 | Bridge `set_chapter_state` is **invalid** / rejected (e.g. 2→3 without `niche_signals`, fact 4) | The whole `apply_map_actions` returns `{"applied": False, "errors": ...}` (fact 3); `run.pending_reply` stays `None`; the early-break guard is false; `on_commit` is **never invoked**; the loop continues and the model reads the validation hint and self-corrects (existing behaviour). No spurious advance, no continuation. |
| E8 | Two `set_chapter_state` actions in one commit | `on_commit` merges both into `run.current_chapter_state` in order; the last advancing `current_chapter` wins. Sequential validation still enforced upstream by the validator. |
| E9 | `on_commit` raises | The `try/except` in 2.1 logs an `on_commit_error` debug stage and treats it as `None` (break) — the already-committed reply surfaces; turn never crashes. |
| E10 | Normal single-chapter turn, no advance (e.g. Ch3 re-scoring) | `on_commit` fires, merges any non-advancing patch into `run.current_chapter_state`, finds no advance → returns `None` → break. Identical user-visible behaviour to today. |
| E11 | Turn ends with **no** commit (synthesized_from_text / default_fallback) | `on_commit` never fires; `run.current_chapter_state` unchanged; `transitioned=False`. Matches today. |

---

## 4. Tests (`backend/tests/`, all monkeypatched — never live)

Use a **fake `ProviderAdapter`** scripted to emit a deterministic sequence of `ProviderResponse`s, and a **fake `execute_tool`** / monkeypatched `DataGateway` (per CRITICAL RULE 4). No real model, Postgres, Places, or ORS.

1. **`test_same_turn_advance_delivers`** — Fake adapter: segment 1 → bridge text + `apply_map_actions(set_chapter_state {niche_signals, current_chapter 2→3})`; after the injected nudge, segment 2 → `score_locations` + `rent_benchmark`, then `apply_map_actions(show_layer + set_layer_heatmap + place_marker + set_chapter_state candidate_locations)`. Assert: final `reply` is segment 2's (not the bridge); the returned `actions` union contains the heatmap + markers; `datasets` has the `score-locations-*` layer; `chapter_state.current_chapter == "3_waar"` **and** `candidate_locations` set; `chapter_transitioned is True`.
2. **`test_no_advance_breaks_as_before`** — segment 1 commits with no chapter change → loop breaks after one commit; `on_commit` returns `None`; one commit, state unchanged save any non-advancing patch (E10). Regression guard.
3. **`test_max_one_advance_per_turn`** — adapter tries to advance 2→3 then 3→4 in the same turn. Assert only one advance applied; final chapter is `3_waar`; second advance deferred (`advances["n"]` capped).
4. **`test_continuation_budget_exhausted_surfaces_bridge`** (E4) — segment 2 never commits within `max_iterations`. Assert surfaced reply == the honest bridge text; `reply_source == "committed"`; **`chapter_state.current_chapter == "3_waar"`** (advance still persisted via `run.current_chapter_state`); no crash.
5. **`test_run_loop_default_unchanged`** — call `run_loop` with `on_commit=None` and a scripted commit; assert it early-breaks exactly as today (locks the default contract; pure `agent_loop.py` unit test).
6. **`test_bridge_without_niche_signals_rejected`** (E7, fact 4) — segment 1 commits `set_chapter_state(current_chapter 2→3)` with **no** `niche_signals` and none in prior state. Assert: `apply_map_actions` returned `{"applied": False}`, `on_commit` never fired (no `same_turn_continuation` stage), chapter stays `2_niche`, and the model gets the validation hint to retry.
7. **`test_canonical_state_is_single_source`** — multi-patch turn (bridge advance + segment-2 `candidate_locations`); assert final persisted `state == run.current_chapter_state` and reflects **both** patches (guards the removed-post-loop-reconstruction invariant — the bug the v1 spec had).
8. **`test_on_commit_exception_safe`** (E9) — `on_commit` raises → turn still returns the committed reply, `on_commit_error` stage logged, no crash.

---

## 5. Acceptance criteria

- [ ] A founder saying *"Ik wil mijn plek vinden"* in Chapter 2 receives, in **one** turn, a reply naming concrete buurten + a committed `show_layer` + `set_layer_heatmap(field="score")` + `place_marker`s, and `current_chapter == "3_waar"`. (Reproduces the trace scenario, fixed.)
- [ ] Exactly **one** user-facing reply per turn — the final chapter's, never the bridge (unless continuation fails → honest bridge surfaces, still not a false promise).
- [ ] At most **one** chapter advance per user turn; chapters still advance sequentially; `set_chapter_state` remains the only writer.
- [ ] Per-turn iteration budget (`AGENT_MAX_TOOL_ITERATIONS`) is respected across both segments.
- [ ] `run_loop` with `on_commit=None` is behaviourally identical to before (test 5 green).
- [ ] Trace tells the whole story: bridge commit, `same_turn_continuation` stage, new chapter's `tool_call`s, final `turn_summary` with `chapter_transitioned=True` and both chapters' actions.
- [ ] DataGateway boundary intact — Chapter-3 data still flows through `gateway.query(...)`; the audit drain (line 133) shows the `score_locations` query. Parameterized SQL only. Rent labelled as a buurt-proxy.
- [ ] No provider branching anywhere in the change; `uv run pytest backend/tests` green; `tsc -b` unaffected (no frontend change).

---

## 6. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Continuation burns the iteration budget, leaving Ch3 half-done | Med | `MAX_SAME_TURN_ADVANCES=1` + honest bridge fallback (E4) + default `AGENT_MAX_TOOL_ITERATIONS=8` leaves headroom; trace surfaces incomplete runs. |
| `run_loop` change regresses the single-chapter happy path | Med | Default `on_commit=None` is byte-for-byte unchanged; regression test 5 locks it. |
| State diverges across references (the v1 bug) | Med | Collapsed to **one** canonical reference, `run.current_chapter_state`, advanced only in the hook; post-loop reconstruction removed; test 7 locks it. |
| Bridge advance silently rejected (no `niche_signals`) → continuation never fires | Med | Chapter-2 exit guidance (2.3 #3) requires `niche_signals` in the advancing patch; test 6 covers the rejection path; the model self-corrects from the validation hint. |
| Stored history bloated by the injected nudge | Low | One `append_commit_nudge` message per advance (≤1/turn); acceptable and consistent with the existing commit-nudge mechanism. |
| Demo-readiness reviewer flags "two commits per turn" as a contract break | Med | chapter-state-machine Rule 4 *requires* each chapter to commit; spec documents that the per-turn invariant is "one **user-facing** reply", and each chapter still fires its own `apply_map_actions` + DataGateway call. Note this explicitly in the PR/handover. |
| Agent still over-promises in the bridge | Low | Prompt Rule + Chapter-2 exit guidance make the bridge present/future-tense; even if surfaced, it is not a false claim. |

---

## 7. Open questions
1. ~~Is `MAX_SAME_TURN_ADVANCES=1` the right cap, and should Droom→Niche chain?~~ **Resolved (user, 2026-05-30):** continuation fires **only Niche→Waar onward** — encoded as `SAME_TURN_CONTINUE_FROM = {"2_niche","3_waar","4_vergunningen"}` in `droomzaak_chapters.py`. Droom→Niche keeps its gentle two-beat: the chapter still advances on the 1→2 commit, but does **not** continue in-turn. `MAX_SAME_TURN_ADVANCES=1` kept.
2. ~~Where is `set_chapter_state` validation enforced?~~ **Resolved:** `agent_tools.py:147` → `agent_validation.validate_agent_action` (line 79-85) → `droomzaak_validation.validate_set_chapter_state`, reading `run.current_chapter_state`. Hence the hook advances that reference (fact 2). E7 confirmed (fact 3).
3. ~~Merge or drop the bridge's actions?~~ **Resolved:** merge — `action_log` in the hook accumulates every commit's actions into the returned union (a bridge usually carries only `set_chapter_state`, which is harmless to replay since the rail reads `chapter_state`).
