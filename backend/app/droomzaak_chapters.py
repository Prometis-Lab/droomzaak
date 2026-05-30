"""The chapter state machine — a thin wrapper around the unchanged agent loop.

Loads/saves chapter state on the session, builds the chapter-aware prompt, filters
the tool surface to the chapter's allow-list, runs the loop, then applies validated
set_chapter_state patches and surfaces the DataGateway audit as debug stages.
"""

from __future__ import annotations

import json
import uuid

from backend.app import agent_tools, agent_trace, droomzaak_tools, settings
from backend.app.agent_loop import AgentRun, Continuation, run_loop
from backend.app.data_gateway import gateway
from backend.app.droomzaak_prompt import (
    CHAPTER_TOOL_ALLOWLIST,
    build_chapter_block,
    build_system_prompt,
)
from backend.app.droomzaak_validation import deep_merge

# Advance at most one chapter per user turn — a chapter advance triggers an in-turn
# continuation that delivers the new chapter's result; capping at 1 keeps a turn from
# racing through the whole journey. Chapters still advance sequentially (validator-enforced).
MAX_SAME_TURN_ADVANCES = 1

# Same-turn continuation fires only on the heavier analysis transitions (Niche→Waar onward),
# where the agent otherwise over-promises results. Droom→Niche keeps its gentle two-beat:
# capture the dream warmly first, then explore the niche on the next turn. The chapter still
# advances on a 1→2 commit; it just doesn't continue in-turn.
SAME_TURN_CONTINUE_FROM = frozenset({"2_niche", "3_waar", "4_vergunningen"})

_CHAPTER_KEYS = [
    "current_chapter", "dream_profile", "niche_signals", "candidate_locations",
    "chosen_location", "permit_checklist", "subsidies", "legal_form",
    "dream_narrative", "tuesday_morning", "package_url",
]


def default_chapter_state() -> dict:
    state = {k: None for k in _CHAPTER_KEYS}
    state["current_chapter"] = "1_droom"
    return state


def apply_state_patch(state: dict, patch: dict) -> dict:
    """Merge an already-validated patch (deep for dicts, replace for lists/scalars)."""
    return deep_merge(state, patch)


def pick_adapter():
    provider = settings.AGENT_PROVIDER
    if provider == "openai" and settings.OPENAI_API_KEY:
        from backend.app.agent_openai import OpenAIAdapter

        return OpenAIAdapter()
    if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        from backend.app.agent_anthropic import AnthropicAdapter

        return AnthropicAdapter()
    # Fall back to whichever key exists.
    if settings.ANTHROPIC_API_KEY:
        from backend.app.agent_anthropic import AnthropicAdapter

        return AnthropicAdapter()
    if settings.OPENAI_API_KEY:
        from backend.app.agent_openai import OpenAIAdapter

        return OpenAIAdapter()
    return None


def build_runtime_block(frontend_context: dict, state: dict) -> str:
    map_state = {
        "active_layers": (frontend_context or {}).get("active_layers", []),
        "selected_dataset_id": (frontend_context or {}).get("selected_dataset_id"),
    }
    return (
        "<map_state>\n" + json.dumps(map_state, ensure_ascii=False) + "\n</map_state>\n\n"
        "<chapter_state>\n" + json.dumps(state, ensure_ascii=False) + "\n</chapter_state>"
    )


async def _execute_tool(name: str, args: dict, run: AgentRun) -> dict:
    if name in agent_tools.HANDLERS:
        return await agent_tools.HANDLERS[name](args, run)
    if name in droomzaak_tools.HANDLERS:
        return await droomzaak_tools.HANDLERS[name](args, run)
    return {"error": f"unknown tool: {name}"}


def _chapter_tool_specs(chapter: str) -> list[dict]:
    allowed = CHAPTER_TOOL_ALLOWLIST[chapter]
    all_specs = agent_tools.tool_specs() + droomzaak_tools.tool_specs()
    return [s for s in all_specs if s["name"] in allowed]


def _make_on_commit(run, transitions, action_log, debug_stages, frontend_context):
    """Build the run_loop on_commit hook.

    `run.current_chapter_state` is the single source of truth: this hook merges every
    committed set_chapter_state patch into it (so the validator sees the live chapter on
    the next segment), accumulates each commit's actions into `action_log` for the
    frontend, and — when a commit ADVANCES the chapter (capped at MAX_SAME_TURN_ADVANCES)
    — returns a Continuation that re-expands the tool surface and re-prompts the new
    chapter so its result is delivered in the same turn.
    """
    advances = {"n": 0}

    def on_commit(_run, _stages):
        # run.pending_actions holds EXACTLY this commit's actions (it is overwritten,
        # not appended, on every apply_map_actions) — so accumulate the union here.
        action_log.extend(run.pending_actions)
        advancing_to = None
        advancing_from = None
        for action in run.pending_actions:
            if action.get("type") != "set_chapter_state":
                continue
            patch = action.get("patch", {})
            prev = (run.current_chapter_state or {}).get("current_chapter")
            run.current_chapter_state = apply_state_patch(run.current_chapter_state, patch)
            debug_stages.append({"stage": "chapter_state_patch_applied",
                                 "detail": {"patch_keys": list(patch.keys())}})
            nxt = patch.get("current_chapter")
            if nxt and nxt != prev:
                advancing_to, advancing_from = nxt, prev
                transitions.append({"from": prev, "to": nxt})

        # State always advances; only the heavier transitions continue in-turn (Droom→Niche
        # keeps its gentle two-beat), and never more than MAX_SAME_TURN_ADVANCES per turn.
        if (advancing_to is None
                or advancing_from not in SAME_TURN_CONTINUE_FROM
                or advances["n"] >= MAX_SAME_TURN_ADVANCES):
            return None
        advances["n"] += 1
        debug_stages.append({"stage": "same_turn_continuation", "detail": {"to": advancing_to}})
        block = build_chapter_block(run.current_chapter_state)
        state_snapshot = build_runtime_block(frontend_context, run.current_chapter_state)
        nudge = (
            f"Je bent nu in {advancing_to}. {block}\n\n{state_snapshot}\n\n"
            "Voer de verplichte calls van dit hoofdstuk uit en commit het eindresultaat "
            "met apply_map_actions. Je vorige reply was alleen een brug — deze commit "
            "levert het echte resultaat dat de gebruiker ziet. Houd de kaart leesbaar: "
            "verberg met hide_layer de lagen uit <map_state>.active_layers die in dit "
            "hoofdstuk niet meer nodig zijn (behalve een laag die de gebruiker net koos)."
        )
        return Continuation(
            tool_specs_neutral=_chapter_tool_specs(advancing_to), nudge_text=nudge
        )

    return on_commit


async def run_droomzaak_turn(
    *, store, user_message: str, session_id: str, frontend_context: dict | None = None,
    debug_stages: list | None = None,
) -> dict:
    frontend_context = frontend_context or {}
    debug_stages = debug_stages if debug_stages is not None else []

    history, provider_label = store.load_messages(session_id)
    state = store.load_chapter_state(session_id) or default_chapter_state()
    chapter = state["current_chapter"]
    debug_stages.append({"stage": "chapter_state_loaded",
                         "detail": {"current_chapter": chapter, "user_message": user_message}})

    adapter = pick_adapter()
    if adapter is None:
        return {"reply": "Agent niet beschikbaar: stel ANTHROPIC_API_KEY of OPENAI_API_KEY in.",
                "actions": [], "chapter_state": state, "chapter_transitioned": False,
                "debug_id": None, "reply_source": "default_fallback", "datasets": {}}

    system_text = build_system_prompt(state)
    debug_stages.append({"stage": "chapter_prompt_built", "detail": {"chapter": chapter}})
    tools = _chapter_tool_specs(chapter)
    runtime_block = build_runtime_block(frontend_context, state)

    run = AgentRun(store=store, session_id=session_id, frontend_context=frontend_context,
                   current_chapter_state=state)
    # `run.current_chapter_state` is the single source of truth from here on: the hook
    # advances it on each commit and may continue the loop in-turn after a chapter advance.
    transitions: list[dict] = []
    action_log: list[dict] = []
    on_commit = _make_on_commit(run, transitions, action_log, debug_stages, frontend_context)
    result = await run_loop(
        adapter=adapter, run=run, system_text=system_text, history=history,
        runtime_block=runtime_block, user_message=user_message, tool_specs_neutral=tools,
        execute_tool=_execute_tool, max_iterations=settings.AGENT_MAX_TOOL_ITERATIONS,
        debug_stages=debug_stages, on_commit=on_commit,
    )

    # The hook already merged every committed set_chapter_state patch into
    # run.current_chapter_state, so it is the final state — no post-loop re-application.
    state = run.current_chapter_state
    transitioned = bool(transitions)
    for t in transitions:
        debug_stages.append({"stage": "chapter_transitioned", "detail": t})
    # action_log is the union of every committed segment's actions; result["actions"] would
    # be only the LAST commit's (pending_actions is overwritten per commit).
    final_actions = action_log or result["actions"]
    store.save_chapter_state(session_id, state)

    # Surface the DataGateway audit (the demo centrepiece).
    for entry in gateway.drain_audit():
        debug_stages.append({"stage": "datagateway_call", "detail": entry})

    # A self-contained per-turn summary so a saved trace tells the whole story:
    # what was asked, how the reply was produced, and what (if anything) failed.
    debug_stages.append({"stage": "turn_summary", "detail": {
        "user_message": user_message,
        "reply": result["reply"],
        "reply_source": result.get("reply_source"),
        "plan": result.get("plan"),
        "problem_report": result.get("problem_report"),
        "iterations": result.get("iterations"),
        "usage": result.get("usage"),
        "actions": [a.get("type") for a in final_actions],
        "chapter_transitioned": transitioned,
    }})

    store.save_messages(session_id, adapter.name, result["messages"])
    debug_id = uuid.uuid4().hex
    store.save_debug(debug_id, session_id, debug_stages)
    agent_trace.write_trace_file(session_id, {"debug_id": debug_id, "stages": debug_stages})

    return {
        "reply": result["reply"], "actions": final_actions, "model": result.get("model"),
        "reply_source": result.get("reply_source"), "plan": result.get("plan"),
        "problem_report": result.get("problem_report"), "usage": result.get("usage"),
        "datasets": result.get("datasets", {}), "chapter_state": state,
        "chapter_transitioned": transitioned, "debug_id": debug_id, "session_id": session_id,
    }
