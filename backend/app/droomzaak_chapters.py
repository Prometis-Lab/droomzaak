"""The chapter state machine — a thin wrapper around the unchanged agent loop.

Loads/saves chapter state on the session, builds the chapter-aware prompt, filters
the tool surface to the chapter's allow-list, runs the loop, then applies validated
set_chapter_state patches and surfaces the DataGateway audit as debug stages.
"""

from __future__ import annotations

import json
import uuid

from backend.app import agent_tools, agent_trace, droomzaak_tools, settings
from backend.app.agent_loop import AgentRun, run_loop
from backend.app.data_gateway import gateway
from backend.app.droomzaak_prompt import CHAPTER_TOOL_ALLOWLIST, build_system_prompt
from backend.app.droomzaak_validation import deep_merge

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
    result = await run_loop(
        adapter=adapter, run=run, system_text=system_text, history=history,
        runtime_block=runtime_block, user_message=user_message, tool_specs_neutral=tools,
        execute_tool=_execute_tool, max_iterations=settings.AGENT_MAX_TOOL_ITERATIONS,
        debug_stages=debug_stages,
    )

    # Apply validated set_chapter_state patches.
    transitioned = False
    prev_chapter = chapter
    for action in result["actions"]:
        if action.get("type") == "set_chapter_state":
            patch = action.get("patch", {})
            state = apply_state_patch(state, patch)
            debug_stages.append({"stage": "chapter_state_patch_applied",
                                 "detail": {"patch_keys": list(patch.keys())}})
            if patch.get("current_chapter") and patch["current_chapter"] != prev_chapter:
                transitioned = True
                debug_stages.append({"stage": "chapter_transitioned",
                                     "detail": {"from": prev_chapter, "to": patch["current_chapter"]}})
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
        "actions": [a.get("type") for a in result["actions"]],
        "chapter_transitioned": transitioned,
    }})

    store.save_messages(session_id, adapter.name, result["messages"])
    debug_id = uuid.uuid4().hex
    store.save_debug(debug_id, session_id, debug_stages)
    agent_trace.write_trace_file(session_id, {"debug_id": debug_id, "stages": debug_stages})

    return {
        "reply": result["reply"], "actions": result["actions"], "model": result.get("model"),
        "reply_source": result.get("reply_source"), "plan": result.get("plan"),
        "problem_report": result.get("problem_report"), "usage": result.get("usage"),
        "datasets": result.get("datasets", {}), "chapter_state": state,
        "chapter_transitioned": transitioned, "debug_id": debug_id, "session_id": session_id,
    }
