"""The provider-neutral agent tool loop.

One loop, one prompt, one tool dispatch — providers (OpenAI / Anthropic) sit
behind the `ProviderAdapter` Protocol; there are no `if provider ==` branches in
the loop. The five hard-earned behaviours are preserved:

1. Plan capture — first iteration's text (when it also emits tool calls) is the plan.
2. Commit-enforcement nudge — one forcing message if the model ends without committing.
3. Synthesis fallback — last bare text becomes the reply, with a problem_report.
4. JSON-envelope unwrap — `{"reply":...}` emitted as plaintext is unwrapped.
5. Early break after commit — exit immediately once apply_map_actions succeeds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

_COMMIT_NUDGE_TEXT = (
    "You must call apply_map_actions exactly once before ending the turn. "
    "Emit your final reply and any actions through the apply_map_actions tool now."
)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderResponse:
    raw: Any
    text_content: str
    tool_calls: list[ToolCall]
    is_terminal: bool
    usage_flat: dict
    raw_usage: dict | None = None
    stage_detail: dict = field(default_factory=dict)


@dataclass
class AgentRun:
    """Per-turn mutable state shared with tool handlers."""

    store: Any = None
    frontend_context: dict = field(default_factory=dict)
    current_chapter_state: dict | None = None
    pending_reply: str | None = None
    pending_actions: list[dict] = field(default_factory=list)
    pending_problem_report: dict | None = None
    referenced_dataset_ids: set[str] = field(default_factory=set)
    datasets: dict[str, dict] = field(default_factory=dict)  # transient layers this turn


@runtime_checkable
class ProviderAdapter(Protocol):
    name: str
    model_id: str
    model_label: str

    def build_initial_messages(
        self, *, system_text: str, history: list, runtime_block: str, user_message: str
    ) -> tuple[list, dict]: ...
    def translate_tool_specs(self, neutral_specs: list[dict]) -> list[dict]: ...
    async def call(self, *, messages: list, tools: list, **kwargs: Any) -> ProviderResponse: ...
    def append_assistant(self, messages: list, response: ProviderResponse) -> None: ...
    def append_tool_results(self, messages: list, results: list[tuple[ToolCall, dict]]) -> None: ...
    def append_commit_nudge(self, messages: list, text: str) -> None: ...
    def stage_name(self, iteration_index: int) -> str: ...
    def error_stage_name(self) -> str: ...


ToolExecutor = Callable[[str, dict, AgentRun], Awaitable[dict]]


def _emit(stages: list, name: str, detail: dict, on_stage=None) -> None:
    entry = {"stage": name, "detail": detail}
    stages.append(entry)
    if on_stage:
        on_stage(entry)


def _unwrap_apply_envelope(text: str) -> str | None:
    """If bare text is literally `{"reply": "...", "actions": [...]}`, return reply."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lstrip().lower().startswith("json"):
            candidate = candidate.lstrip()[4:]
    candidate = candidate.strip()
    if not (candidate.startswith("{") and '"reply"' in candidate):
        return None
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    reply = parsed.get("reply")
    return reply if isinstance(reply, str) else None


def default_reply() -> str:
    return (
        "Sorry, ik kon dit niet afronden. Probeer het opnieuw of herformuleer je vraag."
    )


async def run_loop(
    *,
    adapter: ProviderAdapter,
    run: AgentRun,
    system_text: str,
    history: list,
    runtime_block: str,
    user_message: str,
    tool_specs_neutral: list[dict],
    execute_tool: ToolExecutor,
    create_kwargs: dict | None = None,
    max_iterations: int = 8,
    debug_stages: list | None = None,
    on_stage=None,
) -> dict:
    debug_stages = debug_stages if debug_stages is not None else []
    create_kwargs = create_kwargs or {}

    messages, extra_kwargs = adapter.build_initial_messages(
        system_text=system_text,
        history=history,
        runtime_block=runtime_block,
        user_message=user_message,
    )
    tools = adapter.translate_tool_specs(tool_specs_neutral)

    final_text_fallback = ""
    plan_text: str | None = None
    usage_total: dict = {}
    nudge_used = False
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        try:
            response = await adapter.call(
                messages=messages, tools=tools, **{**extra_kwargs, **create_kwargs}
            )
        except Exception as exc:
            _emit(debug_stages, adapter.error_stage_name(), {"error": str(exc)}, on_stage)
            break

        adapter.append_assistant(messages, response)
        if response.text_content:
            final_text_fallback = response.text_content
            if plan_text is None and response.tool_calls:
                plan_text = response.text_content
        for key, val in (response.usage_flat or {}).items():
            usage_total[key] = usage_total.get(key, 0) + val
        _emit(
            debug_stages,
            adapter.stage_name(iterations),
            {
                "tool_calls": [tc.name for tc in response.tool_calls],
                "is_terminal": response.is_terminal,
                **response.stage_detail,
            },
            on_stage,
        )

        if response.is_terminal or not response.tool_calls:
            if run.pending_reply is None and not nudge_used and iterations < max_iterations:
                nudge_used = True
                adapter.append_commit_nudge(messages, _COMMIT_NUDGE_TEXT)
                continue
            break

        tool_results: list[tuple[ToolCall, dict]] = []
        for tc in response.tool_calls:
            result = await execute_tool(tc.name, tc.arguments, run)
            tool_results.append((tc, result))
        adapter.append_tool_results(messages, tool_results)

        if run.pending_reply is not None and any(
            tc.name == "apply_map_actions" for tc in response.tool_calls
        ):
            break  # early break after commit

    # Resolve reply via three-tier fallback.
    if run.pending_reply is not None:
        reply, reply_source = run.pending_reply, "committed"
    elif final_text_fallback:
        unwrapped = _unwrap_apply_envelope(final_text_fallback)
        reply, reply_source = (unwrapped or final_text_fallback), "synthesized_from_text"
        if run.pending_problem_report is None:
            run.pending_problem_report = {
                "reason": "other",
                "what_was_missing": "model ended turn without calling apply_map_actions",
            }
    else:
        reply, reply_source = default_reply(), "default_fallback"

    return {
        "reply": reply,
        "actions": run.pending_actions,
        "model": adapter.model_id,
        "model_label": adapter.model_label,
        "usage": usage_total,
        "messages": messages,
        "iterations": iterations,
        "plan": plan_text,
        "reply_source": reply_source,
        "problem_report": run.pending_problem_report,
        "datasets": run.datasets,
    }
