"""Conversation tracing — capture how a turn went so a run can be judged after
the fact: every tool call's arguments, result, latency and ok/error, plus a
per-turn summary (user message, final reply, how the reply was produced).

Pure helpers + an optional JSONL file sink. Import-light (stdlib only at module
load; settings is imported lazily in the file sink) so the provider-neutral loop
can import `summarize` without pulling in app config or risking a cycle.

Debug/dev only. This never feeds the agent's reasoning — it only observes it.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

_MAX_TRACE_CHARS = 2000


def summarize(value, max_chars: int = _MAX_TRACE_CHARS):
    """A JSON-safe, length-capped view of a tool argument or result.

    Small values pass through unchanged; large ones (e.g. a GeoJSON blob) are
    replaced by a truncated preview so a trace stays readable and the debug store
    doesn't balloon.
    """
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {"_unserializable": repr(value)[:max_chars]}
    if len(text) <= max_chars:
        return value
    return {"_truncated": True, "_chars": len(text), "preview": text[:max_chars]}


# ── reading a saved trace back ──────────────────────────────────────────
def _turn_summary(stages: list) -> dict:
    for s in stages:
        if s.get("stage") == "turn_summary":
            return s.get("detail", {})
    return {}


def summarize_session(turns: list) -> dict:
    """Aggregate counts across all turns of a session — the at-a-glance verdict."""
    tool_counts: dict[str, int] = {}
    errors: list[dict] = []
    transitions: list[dict] = []
    reply_sources: dict[str, int] = {}
    for i, turn in enumerate(turns, 1):
        for s in turn.get("stages", []):
            stage, detail = s.get("stage"), s.get("detail", {})
            if stage == "tool_call":
                name = detail.get("tool", "?")
                tool_counts[name] = tool_counts.get(name, 0) + 1
                if not detail.get("ok", True):
                    errors.append({"turn": i, "tool": name,
                                   "error": detail.get("error") or detail.get("raised")})
            elif stage == "chapter_transitioned":
                transitions.append({"turn": i, **detail})
            elif stage in ("openai_error", "anthropic_error", "fake_error"):
                errors.append({"turn": i, "tool": "<provider>", "error": detail.get("error")})
        src = _turn_summary(turn.get("stages", [])).get("reply_source")
        if src:
            reply_sources[src] = reply_sources.get(src, 0) + 1
    return {
        "turns": len(turns),
        "tool_calls": tool_counts,
        "errors": errors,
        "error_count": len(errors),
        "chapter_transitions": transitions,
        "reply_sources": reply_sources,
    }


def render_trace_text(session_id: str, turns: list) -> str:
    """A human-readable timeline of the whole conversation — paste-into-an-issue
    friendly. Mirrors what summarize_session counts, expanded per turn."""
    summary = summarize_session(turns)
    lines: list[str] = []
    lines.append(f"TRACE  session={session_id}  turns={summary['turns']}  "
                 f"errors={summary['error_count']}")
    if summary["tool_calls"]:
        tallies = ", ".join(f"{n}×{c}" for n, c in summary["tool_calls"].items())
        lines.append(f"tools: {tallies}")
    if summary["reply_sources"]:
        srcs = ", ".join(f"{k}={v}" for k, v in summary["reply_sources"].items())
        lines.append(f"reply sources: {srcs}")
    lines.append("=" * 72)

    for i, turn in enumerate(turns, 1):
        stages = turn.get("stages", [])
        ts = _turn_summary(stages)
        chapter = next((s["detail"].get("current_chapter")
                        for s in stages if s.get("stage") == "chapter_state_loaded"), "?")
        when = turn.get("created_at", "")
        lines.append(f"\n— Turn {i}  ({when})  chapter={chapter} —")
        if ts.get("user_message"):
            lines.append(f"  USER: {ts['user_message']}")
        if ts.get("plan"):
            lines.append(f"  plan: {ts['plan']}")
        for s in stages:
            if s.get("stage") != "tool_call":
                continue
            d = s.get("detail", {})
            mark = "ok " if d.get("ok", True) else "ERR"
            args = json.dumps(d.get("arguments"), ensure_ascii=False, default=str)
            line = f"  [{mark}] {d.get('tool')} ({d.get('latency_ms')}ms)  args={args}"
            lines.append(line)
            if not d.get("ok", True):
                lines.append(f"        → error: {d.get('error') or d.get('raised')}")
        for s in stages:
            if s.get("stage") == "datagateway_call":
                d = s.get("detail", {})
                lines.append(f"  [gw ] {d.get('tool_name')}: {d.get('rows_returned')} rows "
                             f"in {d.get('latency_ms')}ms")
            if s.get("stage") == "chapter_transitioned":
                d = s.get("detail", {})
                lines.append(f"  >>> chapter {d.get('from')} → {d.get('to')}")
        if ts:
            src = ts.get("reply_source", "?")
            lines.append(f"  REPLY ({src}): {ts.get('reply', '')}")
            if ts.get("problem_report"):
                lines.append(f"  problem_report: "
                             f"{json.dumps(ts['problem_report'], ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


# ── optional file sink (gitignored data/traces) ─────────────────────────
def _safe_trace_name(session_id: str) -> str | None:
    """A filesystem-safe trace filename stem from a (possibly hostile) session_id.

    session_id reaches here from the chat API, so it is untrusted: strip it to its
    basename (kills `../` and absolute paths) and allow only the id alphabet. A
    name that survives intact is used; anything that changed under stripping is
    rejected (return None) rather than silently written to a coerced path.
    """
    stem = Path(session_id).name
    if stem and stem == session_id and all(c.isalnum() or c in "-_" for c in stem):
        return stem
    return None


def write_trace_file(session_id: str, turn_record: dict) -> None:
    """Append one turn's record as a JSON line to data/traces/<session>.jsonl.

    Best-effort: tracing must never break a turn, so all errors are swallowed.
    The filename is confined to the trace dir (session_id is untrusted input).
    """
    from backend.app import settings  # lazy: keep this module import-light

    if not settings.DROOMZAAK_TRACE_TO_FILE:
        return
    stem = _safe_trace_name(session_id)
    if stem is None:
        return
    try:
        directory = Path(settings.DROOMZAAK_TRACE_DIR).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        target = (directory / f"{stem}.jsonl").resolve()
        if target.parent != directory:  # defence in depth: never escape the dir
            return
        record = {"ts": _dt.datetime.now().isoformat(timespec="seconds"), **turn_record}
        line = json.dumps(record, ensure_ascii=False, default=str)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # pragma: no cover - tracing is never load-bearing
        pass
