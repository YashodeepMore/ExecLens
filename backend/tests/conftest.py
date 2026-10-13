"""
Pytest configuration for AI Observatory demo tests.

- Automatically provides a FastAPI TestClient (no manual server start needed)
- Resets backend state between tests
- Generates a test_results.txt file after all tests complete
"""

import sys
import os
from datetime import datetime

import pytest

# ---------------------------------------------------------------------------
# Path setup — make SDK and backend app importable from within tests
# ---------------------------------------------------------------------------
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)
sys.path.insert(0, os.path.join(_backend_dir, "src"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from sdk.observability.tracer import Tracer  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """
    Provides a fresh FastAPI TestClient.
    Resets the in-memory event store before each test so tests are isolated.
    """
    import app.api.routes.event as event_module
    event_module.global_temp_TRACERS.clear()
    event_module.i = 1

    with TestClient(app) as c:
        yield c


@pytest.fixture
def tracer():
    """Provides a fresh Tracer instance for each test."""
    return Tracer()


# ---------------------------------------------------------------------------
# Helpers — available to every test file via conftest
# ---------------------------------------------------------------------------

def send_events_to_backend(client: TestClient, tracer: Tracer):
    """
    Takes the events collected by a Tracer and POSTs each one individually
    to the backend API (matches the current route signature).
    Returns a list of HTTP responses.
    """
    responses = []
    for event in tracer.get_events():
        resp = client.post("/v1/events", json=event.model_dump(mode="json"))
        responses.append(resp)
    return responses


# ---------------------------------------------------------------------------
# Result-file generation
# ---------------------------------------------------------------------------

_test_results: list[dict] = []


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        _test_results.append({
            "name": item.name,
            "nodeid": item.nodeid,
            "status": "PASS" if report.passed else "FAIL",
            "duration": f"{report.duration:.3f}s",
        })


def pytest_sessionfinish(session, exitstatus):
    results_dir = os.path.dirname(os.path.abspath(__file__))
    results_file = os.path.join(results_dir, "test_results.txt")

    passed = sum(1 for r in _test_results if r["status"] == "PASS")
    failed = sum(1 for r in _test_results if r["status"] == "FAIL")
    total = len(_test_results)

    with open(results_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  AI OBSERVATORY - Demo Agent Test Results\n")
        f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"  Total: {total}   |   Passed: {passed}   |   Failed: {failed}\n\n")
        f.write("-" * 70 + "\n\n")

        # Group by file
        current_file = None
        for r in _test_results:
            file_part = r["nodeid"].split("::")[0]
            if file_part != current_file:
                current_file = file_part
                f.write(f"\n  [{current_file}]\n\n")

            icon = "PASS" if r["status"] == "PASS" else "FAIL"
            f.write(f"    [{icon}]  {r['name']}  ({r['duration']})\n")

        f.write("\n" + "=" * 70 + "\n")

        if failed == 0:
            f.write("\n  All tests passed!\n")
        else:
            f.write(f"\n  {failed} test(s) FAILED. Review output above.\n")

        f.write("\n" + "=" * 70 + "\n")
