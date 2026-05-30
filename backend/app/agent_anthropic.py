"""Anthropic adapter implementing the provider-neutral ProviderAdapter Protocol."""

from __future__ import annotations

import json
from typing import Any

from backend.app import settings
from backend.app.agent_loop import ProviderResponse, ToolCall


class AnthropicAdapter:
    name = "anthropic"

    def __init__(self) -> None:
        self.model_id = settings.ANTHROPIC_MODEL
        self.model_label = f"Anthropic {settings.ANTHROPIC_MODEL}"

    def build_initial_messages(self, *, system_text, history, runtime_block, user_message):
        messages = [m for m in (history or []) if m.get("role") != "system"]
        messages.append({"role": "user", "content": f"{runtime_block}\n\n{user_message}".strip()})
        return messages, {"system": system_text}

    def translate_tool_specs(self, neutral_specs: list[dict]) -> list[dict]:
        return [{"name": s["name"], "description": s["description"],
                 "input_schema": s["input_schema"]} for s in neutral_specs]

    async def call(self, *, messages, tools, **kwargs) -> ProviderResponse:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=self.model_id, max_tokens=kwargs.get("max_tokens", 2048),
            system=kwargs.get("system", ""), messages=messages, tools=tools or [])
        text, tool_calls = "", []
        for block in resp.content:
            if getattr(block, "type", "") == "text":
                text += block.text
            elif getattr(block, "type", "") == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        return ProviderResponse(raw=resp, text_content=text, tool_calls=tool_calls,
                                is_terminal=resp.stop_reason == "end_turn",
                                usage_flat=usage, stage_detail={"stop_reason": resp.stop_reason})

    def append_assistant(self, messages, response: ProviderResponse) -> None:
        content: list[dict[str, Any]] = []
        if response.text_content:
            content.append({"type": "text", "text": response.text_content})
        for tc in response.tool_calls:
            content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
        messages.append({"role": "assistant", "content": content})

    def append_tool_results(self, messages, results) -> None:
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tc.id,
             "content": json.dumps(result, ensure_ascii=False, default=str)}
            for tc, result in results]})

    def append_commit_nudge(self, messages, text) -> None:
        messages.append({"role": "user", "content": [{"type": "text", "text": text}]})

    def stage_name(self, iteration_index: int) -> str:
        return f"anthropic_iteration_{iteration_index}"

    def error_stage_name(self) -> str:
        return "anthropic_error"
