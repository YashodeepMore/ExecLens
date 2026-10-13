"""
Tests: Backend Event API
========================
Integration tests for the FastAPI event endpoints.
Verifies that events can be ingested, stored, and retrieved correctly.

Uses the TestClient — the server starts/stops automatically; no manual
server launch is needed.
"""

from sdk.observability.models import EventStatus, EventType
from sdk.observability.tracer import Tracer

from conftest import send_events_to_backend


# ── Health check ────────────────────────────────────────────────────────────

class TestHealthCheck:

    def test_health_check_returns_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Single event ingestion ──────────────────────────────────────────────────

class TestEventIngestion:

    def test_post_single_event(self, client):
        event = {
            "trace_id": "abc-123",
            "span_id": "span-001",
            "parent_span_id": None,
            "type": "agent",
            "name": "test_agent",
            "status": "started",
            "timestamp": "2026-10-07T12:00:00",
            "duration_ms": None,
            "metadata": {},
        }
        resp = client.post("/v1/events", json=event)
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    def test_post_agent_event(self, client):
        event = {
            "trace_id": "t1",
            "span_id": "s1",
            "type": "agent",
            "name": "research_agent",
            "status": "completed",
            "timestamp": "2026-10-07T12:00:00",
            "duration_ms": 500,
            "metadata": {},
        }
        resp = client.post("/v1/events", json=event)
        assert resp.status_code == 200

    def test_post_tool_event(self, client):
        event = {
            "trace_id": "t1",
            "span_id": "s2",
            "type": "tool",
            "name": "web_search",
            "status": "completed",
            "timestamp": "2026-10-07T12:00:01",
            "duration_ms": 200,
            "metadata": {"query": "AI trends"},
        }
        resp = client.post("/v1/events", json=event)
        assert resp.status_code == 200

    def test_post_llm_event(self, client):
        event = {
            "trace_id": "t1",
            "span_id": "s3",
            "type": "llm",
            "name": "gpt-4o.generate",
            "status": "completed",
            "timestamp": "2026-10-07T12:00:02",
            "duration_ms": 120,
            "metadata": {"model": "gpt-4o", "tokens": 350},
        }
        resp = client.post("/v1/events", json=event)
        assert resp.status_code == 200

    def test_post_failed_event(self, client):
        event = {
            "trace_id": "t2",
            "span_id": "s4",
            "type": "llm",
            "name": "gpt-4o.generate",
            "status": "failed",
            "timestamp": "2026-10-07T12:01:00",
            "duration_ms": 30000,
            "metadata": {"error": "Rate limit exceeded"},
        }
        resp = client.post("/v1/events", json=event)
        assert resp.status_code == 200


# ── Event display / retrieval ───────────────────────────────────────────────

class TestEventDisplay:

    def test_display_events_empty_initially(self, client):
        resp = client.get("/v1/events/display")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_display_returns_posted_event(self, client):
        event = {
            "trace_id": "t-display",
            "span_id": "s-display",
            "type": "agent",
            "name": "demo_agent",
            "status": "completed",
            "timestamp": "2026-10-07T12:00:00",
        }
        client.post("/v1/events", json=event)
        resp = client.get("/v1/events/display")
        data = resp.json()
        assert len(data) == 1
        assert "T1" in data
        assert data["T1"]["trace_id"] == "t-display"

    def test_display_multiple_events(self, client):
        for i in range(5):
            event = {
                "trace_id": f"t-multi-{i}",
                "span_id": f"s-multi-{i}",
                "type": "agent",
                "name": f"agent_{i}",
                "status": "completed",
                "timestamp": "2026-10-07T12:00:00",
            }
            client.post("/v1/events", json=event)

        resp = client.get("/v1/events/display")
        data = resp.json()
        assert len(data) == 5


# ── SDK → Backend round-trip ────────────────────────────────────────────────

class TestSDKRoundTrip:

    def test_tracer_events_reach_backend(self, client, tracer):
        """Events created by the SDK Tracer can be POSTed and retrieved."""
        sid = tracer.start(name="round_trip_agent", event_type=EventType.AGENT)
        tracer.complete(sid, duration_ms=100)

        responses = send_events_to_backend(client, tracer)
        assert all(r.status_code == 200 for r in responses)

        display = client.get("/v1/events/display").json()
        assert len(display) == 1

    def test_tracer_preserves_trace_id_in_backend(self, client, tracer):
        sid = tracer.start(name="id_check", event_type=EventType.AGENT)
        tracer.complete(sid, duration_ms=50)

        send_events_to_backend(client, tracer)
        stored = list(client.get("/v1/events/display").json().values())[0]
        assert stored["trace_id"] == tracer.trace_id

    def test_parent_child_events_reach_backend(self, client, tracer):
        parent = tracer.start(name="parent_agent", event_type=EventType.AGENT)
        child = tracer.start(
            name="child_tool", event_type=EventType.TOOL, parent_span_id=parent,
        )
        tracer.complete(child, 30)
        tracer.complete(parent, 100)

        send_events_to_backend(client, tracer)
        display = client.get("/v1/events/display").json()
        assert len(display) == 2
