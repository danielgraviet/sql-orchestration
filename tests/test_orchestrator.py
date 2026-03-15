"""
tests/test_orchestrator.py

Tests for orchestrator.py. No real API calls or Daytona sandboxes — all
dependencies are mocked.

Run with: pytest tests/test_orchestrator.py -v
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import run_competition, _median

MOCK_PATHS = [Path(f"solutions/solution_00{i}.py") for i in range(1, 4)]

MOCK_RESULTS = [
    {
        "sandbox_id": "solution_001", "role": "Query Planner", "passed": True,
        "score": 389.1, "latency_ms": 1.57, "rows_returned": 10,
        "explain_cost": 10000, "error": None, "sql_length": 180,
    },
    {
        "sandbox_id": "solution_002", "role": "Performance Hacker", "passed": True,
        "score": 412.5, "latency_ms": 1.21, "rows_returned": 10,
        "explain_cost": 8000, "error": None, "sql_length": 150,
    },
    {
        "sandbox_id": "solution_003", "role": "Safety Cop", "passed": False,
        "score": 0, "latency_ms": None, "rows_returned": None,
        "explain_cost": None, "error": "FAILED_CORRECTNESS", "sql_length": 200,
    },
]


@pytest.fixture
def patched_competition():
    """Returns run_competition with generate_solutions and run_in_sandbox mocked."""
    async def _run():
        with patch("orchestrator.generate_solutions", new=AsyncMock(return_value=MOCK_PATHS)):
            with patch("orchestrator.run_in_sandbox", new=AsyncMock(side_effect=MOCK_RESULTS)):
                return await run_competition("test task", "schema", daytona=None)
    return _run


async def test_winner_is_highest_score(patched_competition):
    result = await patched_competition()
    assert result["winner"]["role"] == "Performance Hacker"


async def test_success_and_failed_counts(patched_competition):
    result = await patched_competition()
    assert result["success_count"] == 2
    assert result["failed_count"] == 1


async def test_sandboxes_run_count(patched_competition):
    result = await patched_competition()
    assert result["sandboxes_run"] == 3


async def test_results_sorted_by_score_descending(patched_competition):
    result = await patched_competition()
    scores = [r["score"] for r in result["all_results"]]
    assert scores == sorted(scores, reverse=True)


async def test_best_score_matches_winner(patched_competition):
    result = await patched_competition()
    assert result["best_score"] == result["winner"]["score"]


async def test_p50_latency_excludes_failures(patched_competition):
    result = await patched_competition()
    # only passing results: 1.21 and 1.57 — median of two = average = 1.39
    assert result["p50_latency_ms"] == pytest.approx(1.39)


async def test_task_is_preserved(patched_competition):
    result = await patched_competition()
    assert result["task"] == "test task"


async def test_no_solutions_raises(tmp_path):
    with patch("orchestrator.generate_solutions", new=AsyncMock(return_value=[])):
        with pytest.raises(RuntimeError, match="No solutions generated"):
            await run_competition("task", "schema", daytona=None)


# _median unit tests

def test_median_odd():
    assert _median([3.0, 1.0, 2.0]) == 2.0

def test_median_even():
    assert _median([1.0, 2.0]) == 1.5

def test_median_empty():
    assert _median([]) is None

def test_median_single():
    assert _median([5.0]) == 5.0
