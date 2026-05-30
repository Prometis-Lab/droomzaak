"""Conversation-tracing tests — no real APIs/DB (in-memory store, fake adapter).

Covers: the loop emits a tool_call stage with args + result + latency + ok/error;
summarize() caps large blobs; the per-session trace endpoint (json + text) and
its 404; storage.load_debugs_for_session ordering; the JSONL file sink.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import agent_trace, settings
from backend.app.agent_loop import AgentRun, ProviderResponse, ToolCall, run_loop
from backend.app.main import app
from backend.app.storage import CatalogStore, set_store


# ── summarize() ──────────────────────────────────────────────────────────
def test_summarize_passes_small_values():
    assert agent_trace.summarize({"a": 1}) == {"a": 1}


def test_summarize_truncates_large_values():
    big = {"blob": "x" * 5000}
    out = agent_trace.summarize(big, max_chars=100)
    assert out["_truncated"] is True
    assert out["_chars"] > 100
    assert len(out["preview"]) == 100


# ── loop emits tool_call stages with args + result + latency ─────────────
class _FakeAdapter:
    name, model_id, model_label = "fake", "fake-1", "Fake 1"

    def __init__(self, responses):
        self._responses = list(responses)

    def build_initial_messages(self, *, system_text, history, runtime_block, user_message):
        return ([{"role": "system", "content": system_text}], {})

    def translate_tool_specs(self, specs):
        return specs

    async def call(self, *, messages, tools, **kwargs):
        return self._responses.pop(0)

    def append_assistant(self, messages, response):
        pass

    def append_tool_results(self, messages, results):
        pass

    def append_commit_nudge(self, messages, text):
        pass

    def stage_name(self, i):
        return f"fake_iteration_{i}"

    def error_stage_name(self):
        return "fake_error"


def _run_traced_turn():
    async def execute_tool(name, args, run):
        if name == "apply_map_actions":
            run.pending_reply = "klaar"
            run.pending_actions = args.get("actions", [])
            return {"ok": True}
        if name == "rent_benchmark":
            return {"error": "geen huur-proxy voor deze sector"}
        return {"rows": [1, 2, 3]}

    responses = [
        ProviderResponse(raw=None, text_content="plan", tool_calls=[
            ToolCall(id="1", name="peer_benchmarks_statbel", arguments={"nace_code": "56.101"}),
            ToolCall(id="2", name="rent_benchmark", arguments={"sector_id": "BAD"})],
            is_terminal=False, usage_flat={}),
        ProviderResponse(raw=None, text_content="", tool_calls=[
            ToolCall(id="3", name="apply_map_actions", arguments={"actions": [{"type": "x"}]})],
            is_terminal=False, usage_flat={}),
    ]
    stages: list = []
    asyncio.run(run_loop(
        adapter=_FakeAdapter(responses), run=AgentRun(), system_text="s", history=[],
        runtime_block="r", user_message="hoi", tool_specs_neutral=[],
        execute_tool=execute_tool, max_iterations=8, debug_stages=stages,
    ))
    return stages


def test_loop_traces_tool_calls():
    stages = _run_traced_turn()
    calls = [s["detail"] for s in stages if s["stage"] == "tool_call"]
    assert [c["tool"] for c in calls] == [
        "peer_benchmarks_statbel", "rent_benchmark", "apply_map_actions"]
    peer = calls[0]
    assert peer["arguments"] == {"nace_code": "56.101"}      # args captured
    assert peer["ok"] is True
    assert "rows" in peer["result_keys"]                      # result captured
    assert isinstance(peer["latency_ms"], float)             # latency captured


def test_loop_traces_tool_errors():
    stages = _run_traced_turn()
    rent = next(s["detail"] for s in stages
                if s["stage"] == "tool_call" and s["detail"]["tool"] == "rent_benchmark")
    assert rent["ok"] is False
    assert "huur-proxy" in rent["error"]


def test_loop_reraises_and_traces_tool_exception():
    async def boom(name, args, run):
        raise RuntimeError("kaboom")

    responses = [ProviderResponse(raw=None, text_content="", tool_calls=[
        ToolCall(id="1", name="peer_benchmarks_statbel", arguments={})],
        is_terminal=False, usage_flat={})]
    stages: list = []
    with pytest.raises(RuntimeError, match="kaboom"):
        asyncio.run(run_loop(
            adapter=_FakeAdapter(responses), run=AgentRun(), system_text="s", history=[],
            runtime_block="r", user_message="hoi", tool_specs_neutral=[],
            execute_tool=boom, max_iterations=8, debug_stages=stages))
    failed = next(s["detail"] for s in stages if s["stage"] == "tool_call")
    assert failed["ok"] is False
    assert "kaboom" in failed["raised"]


# ── session aggregation + renderers ──────────────────────────────────────
def _sample_turns():
    return [{
        "debug_id": "d1", "created_at": "2026-05-30 12:00:00",
        "stages": [
            {"stage": "chapter_state_loaded", "detail": {"current_chapter": "2_niche",
                                                         "user_message": "vind mijn niche"}},
            {"stage": "tool_call", "detail": {"tool": "peer_benchmarks_statbel", "ok": True,
                                              "arguments": {"nace_code": "56.101"}, "latency_ms": 4.2}},
            {"stage": "tool_call", "detail": {"tool": "rent_benchmark", "ok": False,
                                              "arguments": {"sector_id": "BAD"}, "latency_ms": 1.1,
                                              "error": "geen huur-proxy"}},
            {"stage": "chapter_transitioned", "detail": {"from": "2_niche", "to": "3_waar"}},
            {"stage": "turn_summary", "detail": {"user_message": "vind mijn niche",
                                                 "reply": "Hier is je niche.",
                                                 "reply_source": "committed"}},
        ],
    }]


def test_summarize_session_counts():
    summary = agent_trace.summarize_session(_sample_turns())
    assert summary["turns"] == 1
    assert summary["tool_calls"] == {"peer_benchmarks_statbel": 1, "rent_benchmark": 1}
    assert summary["error_count"] == 1
    assert summary["errors"][0]["tool"] == "rent_benchmark"
    assert summary["reply_sources"] == {"committed": 1}
    assert summary["chapter_transitions"][0]["to"] == "3_waar"


def test_render_trace_text():
    text = agent_trace.render_trace_text("sess-1", _sample_turns())
    assert "session=sess-1" in text
    assert "USER: vind mijn niche" in text
    assert "[ERR] rent_benchmark" in text
    assert "chapter 2_niche → 3_waar" in text
    assert "REPLY (committed)" in text


# ── file sink ────────────────────────────────────────────────────────────
def test_write_trace_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DROOMZAAK_TRACE_TO_FILE", True)
    monkeypatch.setattr(settings, "DROOMZAAK_TRACE_DIR", str(tmp_path))
    agent_trace.write_trace_file("sess-x", {"debug_id": "d1", "stages": [{"stage": "x"}]})
    f = tmp_path / "sess-x.jsonl"
    assert f.exists()
    record = json.loads(f.read_text().strip())
    assert record["debug_id"] == "d1" and "ts" in record


def test_write_trace_file_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DROOMZAAK_TRACE_TO_FILE", False)
    monkeypatch.setattr(settings, "DROOMZAAK_TRACE_DIR", str(tmp_path))
    agent_trace.write_trace_file("sess-y", {"debug_id": "d2", "stages": []})
    assert not (tmp_path / "sess-y.jsonl").exists()


@pytest.mark.parametrize("evil", ["../../evil", "/tmp/dz_escape_test", "a/b", "..", ""])
def test_write_trace_file_rejects_path_traversal(tmp_path, monkeypatch, evil):
    """A hostile session_id must never write anywhere — it is rejected before the
    sink creates its directory, so nothing escapes and nothing is written."""
    trace_dir = tmp_path / "traces"
    monkeypatch.setattr(settings, "DROOMZAAK_TRACE_TO_FILE", True)
    monkeypatch.setattr(settings, "DROOMZAAK_TRACE_DIR", str(trace_dir))
    agent_trace.write_trace_file(evil, {"debug_id": "d", "stages": []})
    # Rejected before mkdir → the trace dir is never created, nothing is written.
    assert not trace_dir.exists()
    assert list(tmp_path.rglob("*.jsonl")) == []
    assert not Path("/tmp/dz_escape_test.jsonl").exists()


def test_safe_trace_name():
    assert agent_trace._safe_trace_name("abc123DEF") == "abc123DEF"
    assert agent_trace._safe_trace_name("with-dash_under") == "with-dash_under"
    assert agent_trace._safe_trace_name("../../evil") is None
    assert agent_trace._safe_trace_name("/abs/path") is None
    assert agent_trace._safe_trace_name("a/b") is None
    assert agent_trace._safe_trace_name("") is None


# ── storage + endpoint ───────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch):
    monkeypatch.setattr(settings, "DROOMZAAK_POSTGRES_URL", "")
    store = CatalogStore(":memory:")
    set_store(store)
    yield store
    set_store(None)
    store.close()


def test_load_debugs_for_session_orders(_isolated_store):
    _isolated_store.save_debug("d1", "sess", [{"stage": "a"}])
    _isolated_store.save_debug("d2", "sess", [{"stage": "b"}])
    runs = _isolated_store.load_debugs_for_session("sess")
    assert [r["debug_id"] for r in runs] == ["d1", "d2"]
    assert runs[0]["stages"][0]["stage"] == "a"


def test_trace_endpoint_json(_isolated_store):
    _isolated_store.save_debug("d1", "sess-e", _sample_turns()[0]["stages"])
    res = TestClient(app).get("/api/agent/trace/sess-e")
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["error_count"] == 1
    assert len(body["turns"]) == 1


def test_trace_endpoint_text(_isolated_store):
    _isolated_store.save_debug("d1", "sess-t", _sample_turns()[0]["stages"])
    res = TestClient(app).get("/api/agent/trace/sess-t?format=text")
    assert res.status_code == 200
    assert "USER: vind mijn niche" in res.text


def test_trace_endpoint_404(_isolated_store):
    assert TestClient(app).get("/api/agent/trace/nope").status_code == 404


def test_chat_rejects_traversal_session_id(_isolated_store):
    """The chat API must reject a path-traversal session_id (422), not pass it on."""
    res = TestClient(app).post("/api/agent/chat",
                               json={"message": "hoi", "session_id": "../../evil"})
    assert res.status_code == 422
