"""
Fake LLM Provider
=================
Simulates OpenAI / Anthropic / Google LLM API calls.

- Externally looks like a real LLM integration (model name, temperature,
  token tracking, cost estimation).
- Internally returns 100 % predefined responses — zero API tokens spent.

Every call is instrumented with the observatory SDK Tracer so the backend
receives realistic LLM-type spans.
"""

import time

from sdk.observability.tracer import Tracer
from sdk.observability.models import EventType


# ---------------------------------------------------------------------------
# Predefined responses — these look like genuine LLM outputs
# ---------------------------------------------------------------------------

PREDEFINED_RESPONSES: dict[str, str] = {
    "research_plan": (
        "I will break this task into three steps: "
        "1) Search for recent publications and reports on the topic. "
        "2) Cross-reference at least three independent sources. "
        "3) Produce a concise executive summary with citations."
    ),
    "summarize": (
        "Based on my analysis of the collected sources, here are the key findings:\n"
        "• Market growth is projected at 15 % CAGR through 2028.\n"
        "• Leading players include Acme Corp, Globex Inc, and Initech Ltd.\n"
        "• Regulatory pressure is increasing in the EU and APAC regions.\n"
        "• The technology is expected to reach mainstream adoption by 2027."
    ),
    "generate_code": (
        "def fibonacci(n: int) -> list[int]:\n"
        '    """Return the first *n* Fibonacci numbers."""\n'
        "    if n <= 0:\n"
        "        return []\n"
        "    seq = [0, 1]\n"
        "    while len(seq) < n:\n"
        "        seq.append(seq[-1] + seq[-2])\n"
        "    return seq[:n]\n"
    ),
    "verify_code": (
        "The generated code is correct. "
        "It handles edge cases (n <= 0, n == 1) and produces the expected "
        "Fibonacci sequence for all tested inputs."
    ),
    "analyze_data": (
        "Statistical analysis reveals a strong positive correlation (r = 0.87, "
        "p = 0.003) between variables X and Y. The 95 % confidence interval "
        "for the slope is [0.72, 1.02]. No significant outliers were detected."
    ),
    "classify_sentiment": (
        "Sentiment: POSITIVE (confidence 0.94)\n"
        "Key phrases: 'excellent product', 'fast delivery', 'would recommend'."
    ),
    "extract_entities": (
        "Entities found:\n"
        "  PERSON  — Alice Johnson, Bob Smith\n"
        "  ORG     — OpenAI, Google DeepMind\n"
        "  DATE    — 2026-10-07\n"
        "  MONEY   — $4.2 million"
    ),
}


class FakeLLM:
    """
    Drop-in replacement for a real LLM client.

    Parameters
    ----------
    model : str
        Model identifier (e.g. ``"gpt-4o"``, ``"claude-3-opus"``).
    temperature : float
        Sampling temperature (cosmetic — not used for generation).
    fail_on_prompts : list[str]
        Prompt keys that should raise an exception (simulates API errors).
    latency_ms : float
        Artificial delay in milliseconds per call (set 0 for fast tests).
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        fail_on_prompts: list[str] | None = None,
        latency_ms: float = 0,
    ):
        self.model = model
        self.temperature = temperature
        self.fail_on_prompts = fail_on_prompts or []
        self.latency_ms = latency_ms
        self.call_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    # ----- core method -----

    def generate(
        self,
        prompt: str,
        tracer: Tracer,
        parent_span_id: str | None = None,
    ) -> str:
        """Simulate an LLM completion call."""
        self.call_count += 1

        span_id = tracer.start(
            name=f"llm.{self.model}.generate",
            event_type=EventType.LLM,
            parent_span_id=parent_span_id,
        )

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)

        # --- failure path ---
        if prompt in self.fail_on_prompts:
            error = f"LLM API Error: Rate limit exceeded for model {self.model}"
            tracer.fail(span_id, self.latency_ms, error)
            raise RuntimeError(error)

        # --- happy path ---
        response = PREDEFINED_RESPONSES.get(prompt, PREDEFINED_RESPONSES.get("summarize"))

        # Fake token accounting (~1 token per 4 characters)
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(response) // 4)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        tracer.complete(span_id, self.latency_ms or 120)
        return response

    # ----- usage stats -----

    def get_usage(self) -> dict:
        return {
            "model": self.model,
            "calls": self.call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(
                (self.total_input_tokens * 0.00003)
                + (self.total_output_tokens * 0.00006),
                6,
            ),
        }
