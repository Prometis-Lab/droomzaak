# The agent loop contract (reference)

This is the contract a new tool plugs into. It lives in `backend/app/agent_loop.py` (the shared loop + `ProviderAdapter` protocol), `agent_tools.py` (specs + handlers), and `agent_validation.py`.

## ProviderAdapter protocol

Both providers implement a thin adapter; the loop is otherwise provider-agnostic. The adapter translates wire shapes only:

```
class ProviderAdapter(Protocol):
    name: str
    pricing_key: str                      # "openai" | "anthropic"
    def build_initial_messages(...) -> (messages, extra_kwargs)
    def translate_tool_specs(neutral_specs) -> provider_tools
    def call(messages, tools, **kwargs) -> ProviderResponse
    def append_assistant(messages, response) -> None
    def append_tool_results(messages, results) -> None
    def append_commit_nudge(messages, text) -> None
    def stage_name(iteration_index) -> str
    def error_stage_name() -> str
```

- **OpenAI**: Chat Completions wire; tools wrapped as `{type:"function", function:{…}}`; one tool-result message per tool; streams to extract the `reply` field token-by-token. Cached system+catalogue prefix.
- **Anthropic**: Messages API; neutral specs are already Anthropic-shaped (`translate_tool_specs` is a no-op); tool results batched into ONE user message; commit nudge sent as a user message (no mid-conversation system messages); explicit `cache_control: ephemeral` markers on system blocks.

Implication for a tool author: **you never touch provider code.** You write the neutral spec + handler once.

## Normalized types

- `ProviderResponse`: `{ text, tool_calls[], is_terminal, usage }`
- `ToolCall`: `{ id, name, arguments }`
- `reply_source` on the final response: `committed` | `synthesized_from_text` | `default_fallback` — tells you whether the model committed cleanly, the loop synthesized a commit from bare text, or fell back.

## run_loop behaviour you depend on

1. Bounded iterations (`AGENT_MAX_TOOL_ITERATIONS`, default 12).
2. Dispatch each `ToolCall` via `execute_tool()` → `_HANDLERS[name]`.
3. Plan capture on the first iteration that emits both text and tool calls.
4. **Commit enforcement**: model ends without `apply_map_actions` → inject one nudge ("Call apply_map_actions now") → one bounded retry → else synthesize a commit from the assistant text and auto-log a `report_problem(reason="other")`.
5. **Early break**: when `apply_map_actions` commits, skip the model's next wrap-up turn (~3–8s latency saved).
6. Usage accumulation (nested-dict merge for OpenAI's per-call token breakdown).

## Handler return shapes

- Read/analyse tool → compact JSON result (the model reasons over it).
- Error → `{"error": str, "hint": str}` (fed back for self-correction).
- Tool that produces features → register via `transient_layers.register(primary_key, primary_value, title, description, source, features, theme, prefix, geometry_types, publisher, license_name, license_url, provenance?)` and return its summary `{dataset_id, fields, geometry_types, records_count, …}`. Prefixes: `osm-`, `iso-`, `rt-`, `sub-`; pick a new prefix for new transient sources.
- `apply_map_actions` is the only tool that stashes `pending_reply` + `pending_actions` on the run; everything else is read/enrich.

## Candidate map (validation gate)

`apply_map_actions` validates each action's `dataset_id` against a candidate map = actions ∪ `referenced_dataset_ids` ∪ active layers ∪ persistent context (`stadswijken-gent`, `statistische-sectoren-gent`). Any tool that surfaces a dataset the model might act on must add it to `run.referenced_dataset_ids`, or the commit fails with a validation error.
