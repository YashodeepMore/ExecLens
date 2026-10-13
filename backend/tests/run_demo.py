"""
Run this script while your FastAPI server is running in another terminal.

Terminal 1:  uv run uvicorn src.app.main:app --reload
Terminal 2:  uv run python tests/run_demo.py

Then open:   http://localhost:8000/v1/events/display
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sdk.observability.decorators import observe


# ── Fake agent functions using @observe decorator ───────────────────────────

# @observe
# def research_agent(topic: str):
#     """Simulates a research agent — all output is fake."""
#     time.sleep(0.1)  # simulate work
#     return {
#         "summary": f"Research complete on '{topic}'. Found 3 key insights.",
#         "sources": 5,
#     }

@observe
def search():
    time.sleep(0.05)
    return "results"


@observe
def research_agent(topic: str):
    search()
    time.sleep(0.1)
    return {
        "summary": f"Research complete on '{topic}'.",
    }

@observe
def code_generation_agent(task: str):
    """Simulates a code gen agent — all output is fake."""
    time.sleep(0.15)
    return {
        "code": "def fibonacci(n): ...",
        "output": "[0, 1, 1, 2, 3, 5, 8]",
    }


@observe
def data_analysis_agent(query: str):
    """Simulates a data analysis agent — all output is fake."""
    time.sleep(0.1)
    return {
        "rows_analysed": 1542,
        "correlation": 0.87,
        "verdict": "Strong positive correlation found.",
    }


@observe
def failing_agent():
    """Simulates an agent that crashes — tests failure tracing."""
    time.sleep(0.05)
    raise RuntimeError("LLM API Error: Rate limit exceeded for model gpt-4o")


# ── Run all agents ──────────────────────────────────────────────────────────

print("=" * 50)
print("  AI Observatory — Demo Agent Runner")
print("  Using @observe decorator")
print("=" * 50)

print("\n[1] Research Agent...")
r1 = research_agent("machine learning trends 2026")
print(f"    Result: {r1}")

print("\n[2] Code Generation Agent...")
r2 = code_generation_agent("fibonacci")
print(f"    Result: {r2}")

print("\n[3] Data Analysis Agent...")
r3 = data_analysis_agent("SELECT * FROM orders")
print(f"    Result: {r3}")

print("\n[4] Failing Agent (expected error)...")
try:
    failing_agent()
except RuntimeError as e:
    print(f"    Caught expected error: {e}")

print("\n" + "=" * 50)
print("  Done! Check: http://localhost:8000/v1/events/display")
print("=" * 50)
