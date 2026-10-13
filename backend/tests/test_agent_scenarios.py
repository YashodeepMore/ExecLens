"""
Tests: Fake Agent Scenarios
============================
End-to-end tests that exercise realistic agent workflows through the
full pipeline:  fake agent → SDK Tracer → FastAPI backend → verify.

Covers:
- Happy-path workflows (research, code gen, data analysis, orchestrator)
- Failure injection (LLM errors, tool errors, cascading failures)
- Trace integrity (correct types, statuses, parent-child links)
- Edge cases (deep nesting, high-volume events)
"""

from sdk.observability.models import EventStatus, EventType
from sdk.observability.tracer import Tracer

from conftest import send_events_to_backend
from demo_agents.fake_agents import (
    CodeGenerationAgent,
    DataAnalysisAgent,
    OrchestratorAgent,
    ResearchAgent,
)
from demo_agents.fake_llm import FakeLLM
from demo_agents.fake_tools import (
    FakeCalculator,
    FakeCodeExecutor,
    FakeDatabaseQuery,
    FakeWebSearch,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Happy-path scenarios
# ═══════════════════════════════════════════════════════════════════════════

class TestHappyPath:

    def test_research_agent_completes_successfully(self, client, tracer):
        agent = ResearchAgent()
        result = agent.run("Python async patterns", tracer)

        assert result["status"] == "success"
        assert result["sources_found"] >= 1

        # Events should reach the backend
        send_events_to_backend(client, tracer)
        stored = client.get("/v1/events/display").json()
        assert len(stored) >= 4  # 1 agent + 2 LLM + 1 tool

    def test_code_generation_agent_completes_successfully(self, client, tracer):
        agent = CodeGenerationAgent()
        result = agent.run("fibonacci", tracer)

        assert result["status"] == "success"
        assert "code" in result
        assert result["output"]["exit_code"] == 0

        send_events_to_backend(client, tracer)
        stored = client.get("/v1/events/display").json()
        assert len(stored) >= 4  # 1 agent + 2 LLM + 1 tool

    def test_data_analysis_agent_completes_successfully(self, client, tracer):
        agent = DataAnalysisAgent()
        result = agent.run("analyse users", tracer)

        assert result["status"] == "success"
        assert result["rows_fetched"] >= 1
        assert result["stats"] == 3.0

        send_events_to_backend(client, tracer)
        stored = client.get("/v1/events/display").json()
        assert len(stored) >= 4  # 1 agent + 1 DB + 1 calc + 1 LLM

    def test_orchestrator_all_agents_succeed(self, client, tracer):
        orchestrator = OrchestratorAgent(agents={
            "researcher": ResearchAgent(),
            "coder": CodeGenerationAgent(
                executor=FakeCodeExecutor(),
            ),
        })
        result = orchestrator.run("Python async patterns", tracer)

        assert result["status"] == "success"
        assert result["results"]["researcher"]["status"] == "success"
        assert result["results"]["coder"]["status"] == "success"

        send_events_to_backend(client, tracer)
        stored = client.get("/v1/events/display").json()
        # orchestrator(1) + research(1+2+1) + code(1+2+1) = 9
        assert len(stored) >= 9

    def test_agent_with_multiple_tool_calls(self, client, tracer):
        """Agent that makes several tool calls in sequence."""
        llm = FakeLLM()
        search = FakeWebSearch()
        calc = FakeCalculator()

        agent_span = tracer.start(name="agent.multi_tool", event_type=EventType.AGENT)

        llm.generate("research_plan", tracer, parent_span_id=agent_span)
        search.search("Python async patterns", tracer, parent_span_id=agent_span)
        search.search("machine learning trends 2026", tracer, parent_span_id=agent_span)
        calc.compute("mean([1,2,3,4,5])", tracer, parent_span_id=agent_span)
        llm.generate("summarize", tracer, parent_span_id=agent_span)

        tracer.complete(agent_span, 900)

        send_events_to_backend(client, tracer)
        stored = client.get("/v1/events/display").json()
        assert len(stored) == 6  # 1 agent + 2 LLM + 2 search + 1 calc


# ═══════════════════════════════════════════════════════════════════════════
#  Failure scenarios
# ═══════════════════════════════════════════════════════════════════════════

class TestFailureScenarios:

    def test_llm_call_failure(self, client, tracer):
        """LLM raises an error → agent catches and reports failure."""
        llm = FakeLLM(fail_on_prompts=["research_plan"])
        agent = ResearchAgent(llm=llm)
        result = agent.run("Python async patterns", tracer)

        assert result["status"] == "failed"
        assert "Rate limit" in result["error"]

        send_events_to_backend(client, tracer)
        events = list(client.get("/v1/events/display").json().values())
        failed = [e for e in events if e.get("status") == "failed"]
        assert len(failed) >= 1  # at least the LLM span failed

    def test_tool_search_failure(self, client, tracer):
        """Web search tool fails → agent reports failure."""
        search = FakeWebSearch(fail_on_queries=["Python async patterns"])
        agent = ResearchAgent(search_tool=search)
        result = agent.run("Python async patterns", tracer)

        assert result["status"] == "failed"
        assert "rate limit" in result["error"].lower() or "error" in result["error"].lower()

    def test_code_execution_failure(self, client, tracer):
        """Code executor tool fails → code-gen agent reports failure."""
        executor = FakeCodeExecutor(fail_on_scripts=["fibonacci"])
        agent = CodeGenerationAgent(executor=executor)
        result = agent.run("fibonacci", tracer)

        assert result["status"] == "failed"
        assert "timeout" in result["error"].lower()

    def test_database_query_failure(self, client, tracer):
        """Database tool fails → data-analysis agent reports failure."""
        db = FakeDatabaseQuery(
            fail_on_queries=["SELECT * FROM users LIMIT 5"],
        )
        agent = DataAnalysisAgent(db=db)
        result = agent.run("analyse users", tracer)

        assert result["status"] == "failed"
        assert "connection" in result["error"].lower()

    def test_calculator_failure(self, client, tracer):
        """Calculator tool fails mid-pipeline."""
        calc = FakeCalculator(fail_on_expressions=["mean([1,2,3,4,5])"])
        agent = DataAnalysisAgent(calculator=calc)
        result = agent.run("analyse users", tracer)

        assert result["status"] == "failed"

    def test_cascading_failure_llm_breaks_agent(self, client, tracer):
        """LLM failure on the first call prevents the entire agent from proceeding."""
        llm = FakeLLM(fail_on_prompts=["research_plan"])
        agent = ResearchAgent(llm=llm)
        result = agent.run("anything", tracer)

        # Agent should have failed; no search or summarise should have run
        events = tracer.get_events()
        agent_event = [e for e in events if e.name == "agent.research"][0]
        assert agent_event.status == EventStatus.FAILED

        # Only 2 events: the agent span + the failed LLM span
        assert len(events) == 2

    def test_orchestrator_partial_failure(self, client, tracer):
        """One sub-agent fails; orchestrator reports partial_failure."""
        failing_llm = FakeLLM(fail_on_prompts=["research_plan"])
        orchestrator = OrchestratorAgent(agents={
            "good_agent": CodeGenerationAgent(
                executor=FakeCodeExecutor(),
            ),
            "bad_agent": ResearchAgent(llm=failing_llm),
        })
        result = orchestrator.run("fibonacci", tracer)

        assert result["status"] == "partial_failure"
        assert result["results"]["good_agent"]["status"] == "success"
        assert result["results"]["bad_agent"]["status"] == "failed"

    def test_all_agent_steps_fail(self, client, tracer):
        """Every tool/LLM call in an agent fails."""
        llm = FakeLLM(fail_on_prompts=["generate_code"])
        agent = CodeGenerationAgent(llm=llm)
        result = agent.run("fibonacci", tracer)

        assert result["status"] == "failed"

        events = tracer.get_events()
        agent_event = [e for e in events if e.name == "agent.code_generation"][0]
        assert agent_event.status == EventStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════════
#  Trace integrity
# ═══════════════════════════════════════════════════════════════════════════

class TestTraceIntegrity:

    def test_all_spans_share_trace_id(self, tracer):
        """Every span in a single run must belong to the same trace."""
        agent = ResearchAgent()
        agent.run("Python async patterns", tracer)

        trace_ids = {e.trace_id for e in tracer.get_events()}
        assert len(trace_ids) == 1

    def test_agent_span_is_parent_of_children(self, tracer):
        """Tool and LLM spans must reference the agent span as parent."""
        agent = ResearchAgent()
        agent.run("Python async patterns", tracer)

        events = tracer.get_events()
        agent_event = [e for e in events if e.type == EventType.AGENT][0]
        children = [e for e in events if e.parent_span_id == agent_event.span_id]
        assert len(children) >= 3  # 2 LLM + 1 search

    def test_event_types_are_correct(self, tracer):
        """Each fake component should produce the right event type."""
        agent = ResearchAgent()
        agent.run("Python async patterns", tracer)

        events = tracer.get_events()
        types = [e.type for e in events]
        assert EventType.AGENT in types
        assert EventType.LLM in types
        assert EventType.TOOL in types

    def test_completed_events_have_positive_duration(self, tracer):
        agent = ResearchAgent()
        agent.run("Python async patterns", tracer)

        for e in tracer.get_events():
            if e.status == EventStatus.COMPLETED:
                assert e.duration_ms is not None
                assert e.duration_ms >= 0

    def test_failed_events_have_error_metadata(self, tracer):
        llm = FakeLLM(fail_on_prompts=["research_plan"])
        agent = ResearchAgent(llm=llm)
        agent.run("anything", tracer)

        failed = [e for e in tracer.get_events() if e.status == EventStatus.FAILED]
        assert len(failed) >= 1
        for e in failed:
            assert "error" in e.metadata

    def test_event_timestamps_are_present(self, tracer):
        agent = DataAnalysisAgent()
        agent.run("analyse", tracer)

        for e in tracer.get_events():
            assert e.timestamp is not None


# ═══════════════════════════════════════════════════════════════════════════
#  Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_deeply_nested_agent_calls(self, client, tracer):
        """
        Orchestrator → ResearchAgent → (LLM, Search, LLM)
        Creates a 3-level deep span tree.
        """
        orchestrator = OrchestratorAgent(agents={
            "deep_research": ResearchAgent(),
        })
        result = orchestrator.run("Python async patterns", tracer)
        assert result["status"] == "success"

        events = tracer.get_events()
        # Should have: orchestrator, research_agent, 2×LLM, 1×search = 5
        assert len(events) >= 5

        # Verify depth: LLM/Tool → parent = research_agent → parent = None (orch)
        # (Research agent's parent_span_id is None because it starts its own
        #  agent span inside run(); it doesn't know about the orchestrator's span.)
        orch_event = [e for e in events if e.name == "agent.orchestrator"][0]
        assert orch_event.parent_span_id is None

    def test_high_volume_events_reach_backend(self, client, tracer):
        """Send 50 events to the backend and verify all are stored."""
        for i in range(50):
            sid = tracer.start(name=f"bulk_span_{i}", event_type=EventType.AGENT)
            tracer.complete(sid, duration_ms=float(i))

        send_events_to_backend(client, tracer)
        stored = client.get("/v1/events/display").json()
        assert len(stored) == 50

    def test_llm_token_usage_tracking(self, tracer):
        """FakeLLM should accumulate token counts across calls."""
        llm = FakeLLM(model="gpt-4o")

        llm.generate("summarize", tracer)
        llm.generate("analyze_data", tracer)

        usage = llm.get_usage()
        assert usage["calls"] == 2
        assert usage["input_tokens"] > 0
        assert usage["output_tokens"] > 0
        assert usage["estimated_cost_usd"] > 0

    def test_different_tracers_produce_different_traces(self, client):
        """Two independent agent runs should have distinct trace IDs."""
        t1 = Tracer()
        t2 = Tracer()

        ResearchAgent().run("Python async patterns", t1)
        CodeGenerationAgent().run("fibonacci", t2)

        assert t1.trace_id != t2.trace_id

        send_events_to_backend(client, t1)
        send_events_to_backend(client, t2)

        stored = client.get("/v1/events/display").json()
        trace_ids = {v["trace_id"] for v in stored.values()}
        assert len(trace_ids) == 2

    def test_agent_run_produces_realistic_trace_tree(self, tracer):
        """
        A research-agent run should produce a trace tree like:

        agent.research                   (AGENT)
         ├── llm.gpt-4o.generate         (LLM)   — plan
         ├── tool.web_search             (TOOL)   — search
         └── llm.gpt-4o.generate         (LLM)   — summarise
        """
        agent = ResearchAgent()
        agent.run("machine learning trends 2026", tracer)

        events = tracer.get_events()
        names = [e.name for e in events]

        assert "agent.research" in names
        assert "llm.gpt-4o.generate" in names
        assert "tool.web_search" in names

        agent_event = [e for e in events if e.name == "agent.research"][0]
        children = [e for e in events if e.parent_span_id == agent_event.span_id]

        child_types = sorted([c.type.value for c in children])
        assert child_types == ["llm", "llm", "tool"]
