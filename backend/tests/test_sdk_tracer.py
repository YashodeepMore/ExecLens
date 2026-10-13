"""
Tests: SDK Tracer
=================
Unit tests for the observability SDK Tracer class.
Verifies that trace IDs, spans, statuses, and parent-child relationships
are created correctly — independent of the backend.
"""

from sdk.observability.models import EventStatus, EventType
from sdk.observability.tracer import Tracer


# ── Trace ID ────────────────────────────────────────────────────────────────

class TestTracerIdentity:

    def test_tracer_generates_unique_trace_id(self):
        t1 = Tracer()
        t2 = Tracer()
        assert t1.trace_id != t2.trace_id, "Each tracer must have a unique trace ID"

    def test_tracer_trace_id_is_uuid_format(self):
        t = Tracer()
        parts = t.trace_id.split("-")
        assert len(parts) == 5, "trace_id should be a UUID (5 dash-separated groups)"


# ── Span creation ───────────────────────────────────────────────────────────

class TestSpanCreation:

    def test_start_creates_event(self):
        t = Tracer()
        span_id = t.start(name="test_span", event_type=EventType.AGENT)
        events = t.get_events()
        assert len(events) == 1
        assert events[0].span_id == span_id
        assert events[0].name == "test_span"

    def test_start_event_has_started_status(self):
        t = Tracer()
        t.start(name="x", event_type=EventType.AGENT)
        assert t.get_events()[0].status == EventStatus.STARTED

    def test_start_returns_unique_span_ids(self):
        t = Tracer()
        s1 = t.start(name="a", event_type=EventType.AGENT)
        s2 = t.start(name="b", event_type=EventType.TOOL)
        assert s1 != s2

    def test_multiple_spans_share_trace_id(self):
        t = Tracer()
        t.start(name="a", event_type=EventType.AGENT)
        t.start(name="b", event_type=EventType.TOOL)
        t.start(name="c", event_type=EventType.LLM)
        trace_ids = {e.trace_id for e in t.get_events()}
        assert len(trace_ids) == 1, "All spans in one tracer must share the same trace_id"


# ── Completing / failing spans ──────────────────────────────────────────────

class TestSpanCompletion:

    def test_complete_updates_status(self):
        t = Tracer()
        sid = t.start(name="x", event_type=EventType.AGENT)
        t.complete(sid, duration_ms=42.0)
        assert t.get_events()[0].status == EventStatus.COMPLETED

    def test_complete_sets_duration(self):
        t = Tracer()
        sid = t.start(name="x", event_type=EventType.AGENT)
        t.complete(sid, duration_ms=123.4)
        assert t.get_events()[0].duration_ms == 123.4

    def test_fail_updates_status(self):
        t = Tracer()
        sid = t.start(name="x", event_type=EventType.AGENT)
        t.fail(sid, duration_ms=10, error="boom")
        assert t.get_events()[0].status == EventStatus.FAILED

    def test_fail_stores_error_in_metadata(self):
        t = Tracer()
        sid = t.start(name="x", event_type=EventType.AGENT)
        t.fail(sid, duration_ms=10, error="connection timeout")
        assert t.get_events()[0].metadata["error"] == "connection timeout"


# ── Parent / child spans ────────────────────────────────────────────────────

class TestParentChildSpans:

    def test_child_span_references_parent(self):
        t = Tracer()
        parent = t.start(name="agent", event_type=EventType.AGENT)
        child = t.start(name="tool", event_type=EventType.TOOL, parent_span_id=parent)
        events = t.get_events()
        child_event = [e for e in events if e.span_id == child][0]
        assert child_event.parent_span_id == parent

    def test_root_span_has_no_parent(self):
        t = Tracer()
        t.start(name="root", event_type=EventType.AGENT)
        assert t.get_events()[0].parent_span_id is None

    def test_deep_nesting(self):
        t = Tracer()
        s1 = t.start(name="level_1", event_type=EventType.AGENT)
        s2 = t.start(name="level_2", event_type=EventType.TOOL, parent_span_id=s1)
        s3 = t.start(name="level_3", event_type=EventType.LLM, parent_span_id=s2)
        events = t.get_events()
        assert events[2].parent_span_id == s2
        assert events[1].parent_span_id == s1
        assert events[0].parent_span_id is None


# ── Event types ─────────────────────────────────────────────────────────────

class TestEventTypes:

    def test_agent_type(self):
        t = Tracer()
        t.start(name="a", event_type=EventType.AGENT)
        assert t.get_events()[0].type == EventType.AGENT

    def test_tool_type(self):
        t = Tracer()
        t.start(name="t", event_type=EventType.TOOL)
        assert t.get_events()[0].type == EventType.TOOL

    def test_llm_type(self):
        t = Tracer()
        t.start(name="l", event_type=EventType.LLM)
        assert t.get_events()[0].type == EventType.LLM
