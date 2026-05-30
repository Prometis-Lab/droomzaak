"""OpenAI adapter implementing the provider-neutral ProviderAdapter Protocol."""

from __future__ import annotations

import json

from backend.app import settings
from backend.app.agent_loop import ProviderResponse, ToolCall


class OpenAIAdapter:
    name = "openai"

    def __init__(self) -> None:
        self.model_id = settings.OPENAI_MODEL
        self.model_label = f"OpenAI {settings.OPENAI_MODEL}"

    def build_initial_messages(self, *, system_text, history, runtime_block, user_message):
        messages = [{"role": "system", "content": system_text}]
        messages += [m for m in (history or []) if m.get("role") != "system"]
        messages.append({"role": "user", "content": f"{runtime_block}\n\n{user_message}".strip()})
        return messages, {}

    def translate_tool_specs(self, neutral_specs: list[dict]) -> list[dict]:
        return [{"type": "function", "function": {
            "name": s["name"], "description": s["description"],
            "parameters": s["input_schema"]}} for s in neutral_specs]

    async def call(self, *, messages, tools, **kwargs) -> ProviderResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=self.model_id, messages=messages, tools=tools or None)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = []
        for tc in (msg.tool_calls or []):
            try:
                arguments = json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, ValueError):
                arguments = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=arguments))
        usage = {}
        if resp.usage:
            usage = {"input_tokens": resp.usage.prompt_tokens, "output_tokens": resp.usage.completion_tokens}
        return ProviderResponse(raw=resp, text_content=msg.content or "", tool_calls=tool_calls,
                                is_terminal=choice.finish_reason in {"stop", "length", "content_filter"}
                                and not tool_calls,
                                usage_flat=usage, stage_detail={"finish_reason": choice.finish_reason})

    def append_assistant(self, messages, response: ProviderResponse) -> None:
        entry: dict = {"role": "assistant", "content": response.text_content or None}
        if response.tool_calls:
            entry["tool_calls"] = [{"id": tc.id, "type": "function", "function": {
                "name": tc.name, "arguments": json.dumps(tc.arguments)}} for tc in response.tool_calls]
        messages.append(entry)

    def append_tool_results(self, messages, results) -> None:
        for tc, result in results:
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)})

    def append_commit_nudge(self, messages, text) -> None:
        messages.append({"role": "system", "content": text})

    def stage_name(self, iteration_index: int) -> str:
        return f"openai_iteration_{iteration_index}"

    def error_stage_name(self) -> str:
        return "openai_error"
