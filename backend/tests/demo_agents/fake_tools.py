"""
Fake Tool Implementations
=========================
Simulates the external tools an AI agent would call:

- Web Search  (Google / Bing / Tavily)
- Calculator  (Wolfram Alpha / code sandbox math)
- Code Executor  (E2B / Modal / local sandbox)
- Database Query  (Postgres / Supabase)

Each tool records spans via the SDK Tracer so the observatory backend
receives realistic tool-call telemetry.  All outputs are 100 % static.
"""

import time

from sdk.observability.tracer import Tracer
from sdk.observability.models import EventType


# ═══════════════════════════════════════════════════════════════════════════
# Web Search
# ═══════════════════════════════════════════════════════════════════════════

class FakeWebSearch:
    """Simulates a web search API (Tavily, SerpAPI, etc.)."""

    PREDEFINED_RESULTS: dict[str, list[dict]] = {
        "Python async patterns": [
            {
                "title": "AsyncIO Best Practices in 2026",
                "url": "https://realpython.com/async-io-python/",
                "snippet": "Learn how to write efficient async code with Python 3.12+ ...",
            },
            {
                "title": "Concurrency vs Parallelism Explained",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "snippet": "The asyncio module provides infrastructure for writing ...",
            },
        ],
        "machine learning trends 2026": [
            {
                "title": "Top 10 ML Trends Shaping 2026",
                "url": "https://arxiv.org/abs/2026.01234",
                "snippet": "This survey covers the most impactful developments in ML ...",
            },
            {
                "title": "State of AI Report 2026",
                "url": "https://www.stateof.ai/2026",
                "snippet": "Annual report on the most important developments in AI ...",
            },
            {
                "title": "Enterprise AI Adoption Survey",
                "url": "https://mckinsey.com/ai-adoption-2026",
                "snippet": "85 % of enterprises now use at least one AI application ...",
            },
        ],
    }

    def __init__(
        self,
        fail_on_queries: list[str] | None = None,
        latency_ms: float = 0,
    ):
        self.fail_on_queries = fail_on_queries or []
        self.latency_ms = latency_ms
        self.call_count = 0

    def search(
        self,
        query: str,
        tracer: Tracer,
        parent_span_id: str | None = None,
    ) -> list[dict]:
        self.call_count += 1
        span_id = tracer.start(
            name="tool.web_search",
            event_type=EventType.TOOL,
            parent_span_id=parent_span_id,
        )

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)

        if query in self.fail_on_queries:
            error = f"Search API error: rate limit exceeded for query '{query}'"
            tracer.fail(span_id, self.latency_ms, error)
            raise RuntimeError(error)

        results = self.PREDEFINED_RESULTS.get(
            query,
            [{"title": "Generic Result", "url": "https://example.com", "snippet": "..."}],
        )
        tracer.complete(span_id, self.latency_ms or 180)
        return results


# ═══════════════════════════════════════════════════════════════════════════
# Calculator / Math
# ═══════════════════════════════════════════════════════════════════════════

class FakeCalculator:
    """Simulates a computation / math tool."""

    PREDEFINED_RESULTS: dict[str, float | int] = {
        "2 + 2": 4,
        "factorial(10)": 3628800,
        "mean([1,2,3,4,5])": 3.0,
        "std([1,2,3,4,5])": 1.4142,
        "sqrt(144)": 12.0,
        "pi * r^2 where r=5": 78.5398,
    }

    def __init__(
        self,
        fail_on_expressions: list[str] | None = None,
        latency_ms: float = 0,
    ):
        self.fail_on_expressions = fail_on_expressions or []
        self.latency_ms = latency_ms
        self.call_count = 0

    def compute(
        self,
        expression: str,
        tracer: Tracer,
        parent_span_id: str | None = None,
    ) -> float | int:
        self.call_count += 1
        span_id = tracer.start(
            name="tool.calculator",
            event_type=EventType.TOOL,
            parent_span_id=parent_span_id,
        )

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)

        if expression in self.fail_on_expressions:
            error = f"Computation error: invalid expression '{expression}'"
            tracer.fail(span_id, self.latency_ms, error)
            raise RuntimeError(error)

        result = self.PREDEFINED_RESULTS.get(expression, 0)
        tracer.complete(span_id, self.latency_ms or 30)
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Code Executor
# ═══════════════════════════════════════════════════════════════════════════

class FakeCodeExecutor:
    """Simulates sandboxed code execution (E2B, Modal, etc.)."""

    PREDEFINED_OUTPUTS: dict[str, dict] = {
        "fibonacci": {
            "stdout": "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]",
            "stderr": "",
            "exit_code": 0,
        },
        "hello_world": {
            "stdout": "Hello, World!",
            "stderr": "",
            "exit_code": 0,
        },
        "data_transform": {
            "stdout": '{"rows_processed": 1542, "errors": 0}',
            "stderr": "",
            "exit_code": 0,
        },
        "syntax_error": {
            "stdout": "",
            "stderr": "SyntaxError: unexpected EOF while parsing (line 12)",
            "exit_code": 1,
        },
        "timeout_script": {
            "stdout": "",
            "stderr": "TimeoutError: execution exceeded 30 s limit",
            "exit_code": 137,
        },
    }

    def __init__(
        self,
        fail_on_scripts: list[str] | None = None,
        latency_ms: float = 0,
    ):
        self.fail_on_scripts = fail_on_scripts or []
        self.latency_ms = latency_ms
        self.call_count = 0

    def execute(
        self,
        script_name: str,
        tracer: Tracer,
        parent_span_id: str | None = None,
    ) -> dict:
        self.call_count += 1
        span_id = tracer.start(
            name="tool.code_executor",
            event_type=EventType.TOOL,
            parent_span_id=parent_span_id,
        )

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)

        if script_name in self.fail_on_scripts:
            error = f"Execution timeout: script '{script_name}' exceeded 30 s limit"
            tracer.fail(span_id, self.latency_ms, error)
            raise RuntimeError(error)

        result = self.PREDEFINED_OUTPUTS.get(
            script_name,
            {"stdout": "OK", "stderr": "", "exit_code": 0},
        )

        if result.get("exit_code", 0) != 0:
            tracer.fail(span_id, self.latency_ms, result.get("stderr", "Unknown error"))
            raise RuntimeError(result.get("stderr", "Execution failed"))

        tracer.complete(span_id, self.latency_ms or 250)
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Database Query
# ═══════════════════════════════════════════════════════════════════════════

class FakeDatabaseQuery:
    """Simulates a database query tool (Postgres, Supabase, etc.)."""

    PREDEFINED_RESULTS: dict[str, list[dict]] = {
        "SELECT * FROM users LIMIT 5": [
            {"id": 1, "name": "Alice Johnson", "email": "alice@acme.com", "role": "admin"},
            {"id": 2, "name": "Bob Smith", "email": "bob@acme.com", "role": "user"},
            {"id": 3, "name": "Carol Lee", "email": "carol@acme.com", "role": "user"},
        ],
        "SELECT COUNT(*) FROM orders": [{"count": 1542}],
        "SELECT AVG(amount) FROM transactions WHERE date > '2026-01-01'": [
            {"avg_amount": 284.37}
        ],
    }

    def __init__(
        self,
        fail_on_queries: list[str] | None = None,
        latency_ms: float = 0,
    ):
        self.fail_on_queries = fail_on_queries or []
        self.latency_ms = latency_ms
        self.call_count = 0

    def query(
        self,
        sql: str,
        tracer: Tracer,
        parent_span_id: str | None = None,
    ) -> list[dict]:
        self.call_count += 1
        span_id = tracer.start(
            name="tool.database_query",
            event_type=EventType.TOOL,
            parent_span_id=parent_span_id,
        )

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)

        if sql in self.fail_on_queries:
            error = "Database error: connection refused (PostgreSQL @ 5432)"
            tracer.fail(span_id, self.latency_ms, error)
            raise RuntimeError(error)

        result = self.PREDEFINED_RESULTS.get(sql, [])
        tracer.complete(span_id, self.latency_ms or 45)
        return result
