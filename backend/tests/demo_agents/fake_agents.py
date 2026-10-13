"""
Fake Agent Implementations
===========================
Simulates realistic AI agent architectures:

- ResearchAgent       — plans → searches → summarises
- CodeGenerationAgent — generates code → executes → verifies
- DataAnalysisAgent   — queries DB → computes stats → interprets
- OrchestratorAgent   — coordinates multiple sub-agents

Each agent uses the SDK Tracer to emit realistic parent → child spans.
All outputs are 100 % static.  No real LLM or tool calls are made.
"""

from sdk.observability.tracer import Tracer
from sdk.observability.models import EventType

from .fake_llm import FakeLLM
from .fake_tools import (
    FakeCalculator,
    FakeCodeExecutor,
    FakeDatabaseQuery,
    FakeWebSearch,
)


# ═══════════════════════════════════════════════════════════════════════════
# Research Agent
# ═══════════════════════════════════════════════════════════════════════════

class ResearchAgent:
    """
    Simulates an AI research assistant.

    Workflow
    --------
    1. LLM → decide search strategy
    2. Tool → web search
    3. LLM → summarise findings
    """

    def __init__(
        self,
        llm: FakeLLM | None = None,
        search_tool: FakeWebSearch | None = None,
    ):
        self.llm = llm or FakeLLM(model="gpt-4o")
        self.search = search_tool or FakeWebSearch()

    def run(self, topic: str, tracer: Tracer) -> dict:
        agent_span = tracer.start(
            name="agent.research",
            event_type=EventType.AGENT,
        )

        try:
            # Step 1 — plan
            plan = self.llm.generate(
                "research_plan", tracer, parent_span_id=agent_span,
            )

            # Step 2 — search
            results = self.search.search(
                topic, tracer, parent_span_id=agent_span,
            )

            # Step 3 — summarise
            summary = self.llm.generate(
                "summarize", tracer, parent_span_id=agent_span,
            )

            tracer.complete(agent_span, 520)
            return {
                "status": "success",
                "summary": summary,
                "sources_found": len(results),
            }

        except Exception as exc:
            tracer.fail(agent_span, 520, str(exc))
            return {"status": "failed", "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# Code Generation Agent
# ═══════════════════════════════════════════════════════════════════════════

class CodeGenerationAgent:
    """
    Simulates an AI coding assistant.

    Workflow
    --------
    1. LLM → generate code
    2. Tool → execute in sandbox
    3. LLM → verify output correctness
    """

    def __init__(
        self,
        llm: FakeLLM | None = None,
        executor: FakeCodeExecutor | None = None,
    ):
        self.llm = llm or FakeLLM(model="gpt-4o")
        self.executor = executor or FakeCodeExecutor()

    def run(self, task: str, tracer: Tracer) -> dict:
        agent_span = tracer.start(
            name="agent.code_generation",
            event_type=EventType.AGENT,
        )

        try:
            # Step 1 — generate
            code = self.llm.generate(
                "generate_code", tracer, parent_span_id=agent_span,
            )

            # Step 2 — execute
            output = self.executor.execute(
                task, tracer, parent_span_id=agent_span,
            )

            # Step 3 — verify
            verification = self.llm.generate(
                "verify_code", tracer, parent_span_id=agent_span,
            )

            tracer.complete(agent_span, 850)
            return {
                "status": "success",
                "code": code,
                "output": output,
                "verification": verification,
            }

        except Exception as exc:
            tracer.fail(agent_span, 850, str(exc))
            return {"status": "failed", "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# Data Analysis Agent
# ═══════════════════════════════════════════════════════════════════════════

class DataAnalysisAgent:
    """
    Simulates an AI data analyst.

    Workflow
    --------
    1. Tool → query database
    2. Tool → compute statistics
    3. LLM → interpret and explain
    """

    def __init__(
        self,
        llm: FakeLLM | None = None,
        calculator: FakeCalculator | None = None,
        db: FakeDatabaseQuery | None = None,
    ):
        self.llm = llm or FakeLLM(model="gpt-4o")
        self.calculator = calculator or FakeCalculator()
        self.db = db or FakeDatabaseQuery()

    def run(self, task: str, tracer: Tracer) -> dict:
        agent_span = tracer.start(
            name="agent.data_analysis",
            event_type=EventType.AGENT,
        )

        try:
            # Step 1 — fetch data
            data = self.db.query(
                "SELECT * FROM users LIMIT 5", tracer, parent_span_id=agent_span,
            )

            # Step 2 — compute
            stats = self.calculator.compute(
                "mean([1,2,3,4,5])", tracer, parent_span_id=agent_span,
            )

            # Step 3 — interpret
            analysis = self.llm.generate(
                "analyze_data", tracer, parent_span_id=agent_span,
            )

            tracer.complete(agent_span, 640)
            return {
                "status": "success",
                "rows_fetched": len(data),
                "stats": stats,
                "analysis": analysis,
            }

        except Exception as exc:
            tracer.fail(agent_span, 640, str(exc))
            return {"status": "failed", "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# Orchestrator Agent
# ═══════════════════════════════════════════════════════════════════════════

class OrchestratorAgent:
    """
    Coordinates multiple sub-agents to complete a complex task.

    The orchestrator itself is an agent-type span; each sub-agent
    creates its own child spans, producing a realistic multi-level
    trace tree.
    """

    def __init__(self, agents: dict[str, object] | None = None):
        self.agents = agents or {}

    def run(self, task: str, tracer: Tracer) -> dict:
        orch_span = tracer.start(
            name="agent.orchestrator",
            event_type=EventType.AGENT,
        )

        results: dict[str, dict] = {}
        all_ok = True

        for name, agent in self.agents.items():
            try:
                result = agent.run(task, tracer)
                results[name] = result
                if result.get("status") != "success":
                    all_ok = False
            except Exception as exc:
                results[name] = {"status": "failed", "error": str(exc)}
                all_ok = False

        if all_ok:
            tracer.complete(orch_span, 2200)
        else:
            tracer.fail(orch_span, 2200, "One or more sub-agents failed")

        return {
            "status": "success" if all_ok else "partial_failure",
            "results": results,
        }
