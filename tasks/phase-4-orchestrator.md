---
phase: 4
title: Orchestrator — Parallel Execution & Winner Selection
status: pending
depends_on: phase-2, phase-3
---

# Phase 4: Orchestrator — Parallel Execution & Winner Selection

## Objective

Build the orchestrator in `main.py` that ties all phases together: generate SQL candidates from all 5 agent roles, run each candidate in its own Daytona sandbox in parallel, collect benchmark results, score them, and surface the winning query. This is the demo's central loop.

---

## Context

Right now `main.py` is a stub that prints "Hello from 500-brain-agent!". By the end of this phase it becomes the full demo entrypoint. When run, it must:

1. Accept a task string (hardcoded or CLI arg)
2. Generate 5 SQL candidates via `agent.py`
3. Boot 5 Daytona sandboxes in parallel via `sandbox_runner.py`
4. Collect all 5 results
5. Print a ranked leaderboard
6. Declare the winner and print its SQL

The orchestrator must complete even if some sandboxes fail — partial results are valid.

---

## Files to Modify / Create

| File | Action |
|------|--------|
| `main.py` | Full rewrite |
| `orchestrator.py` | Create — core logic extracted here, `main.py` is the thin entrypoint |
| `tests/test_orchestrator.py` | Create — integration smoke test |

---

## Tasks

### 4.1 — Design the Orchestrator Interface

Create `orchestrator.py` and export one async function:

```python
async def run_competition(
    task: str,
    schema: str,
    daytona: AsyncDaytona,
) -> dict
```

**Returns:**
```json
{
  "task": "Top 10 riders by trips last month",
  "winner": { ...benchmark_result... },
  "all_results": [ ...list of benchmark_results... ],
  "sandboxes_run": 5,
  "success_count": 4,
  "failed_count": 1,
  "p50_latency_ms": 1.8,
  "best_score": 412.5
}
```

---

### 4.2 — Generation Step

Inside `run_competition`:

1. Call `generate_solutions(task, schema)` and await the list of paths
2. If fewer than 1 solution was generated, raise `RuntimeError("No solutions generated")`
3. Log: `Generated {len(paths)} solutions`

---

### 4.3 — Parallel Sandbox Execution

Fire all sandbox runs simultaneously:

```python
results = await asyncio.gather(
    *[run_in_sandbox(daytona, path) for path in solution_paths],
    return_exceptions=False,
)
```

**Error handling:**
- If `run_in_sandbox` raises an exception (it shouldn't — it catches internally), wrap it in an error result dict so the gather never propagates exceptions upward
- A solution that failed its safety check, correctness check, or timed out still returns a result dict with `passed=False` and a non-zero `score=0`
- Count `passed=True` results for `success_count`

---

### 4.4 — Scoring & Ranking

After collecting all results:

1. Sort `all_results` by `score` descending
2. `winner` = first result where `passed=True` and `score > 0`; if none, winner is the result with the highest score regardless
3. Compute `p50_latency_ms` as the median of `latency_ms` values for passing results only (skip `None` values)
4. Set `best_score` from the winner's score

---

### 4.5 — Rewrite `main.py`

`main.py` should be a clean entrypoint, ~30 lines:

```python
import asyncio
import argparse
from daytona_sdk import AsyncDaytona
from data.schema_loader import get_schema_string
from orchestrator import run_competition

DEFAULT_TASK = "Top 10 riders by trips last month"

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=DEFAULT_TASK)
    args = parser.parse_args()

    schema = get_schema_string()
    async with AsyncDaytona() as daytona:
        result = await run_competition(args.task, schema, daytona)

    _print_results(result)

def _print_results(result: dict):
    # Print ranked leaderboard and winner SQL
    ...

if __name__ == "__main__":
    asyncio.run(main())
```

**`_print_results` must output:**
- A table with columns: Rank, Role, Passed, Score, Latency(ms), Rows, Explain Cost
- Winner announcement: "Winner: <role> (score: <score>)"
- The winning SQL query printed verbatim

Example output:
```
=== SQL Agent Competition ===
Task: Top 10 riders by trips last month

Rank  Role                Passed  Score    Latency(ms)  Rows  Explain Cost
1     Performance Hacker  ✓       412.5    1.21         10    8000
2     Query Planner       ✓       389.1    1.57         10    10000
3     Safety Cop          ✓       371.2    1.63         10    10000
4     Regression Tester   ✓       345.8    1.89         10    10000
5     Narrator            ✗       0        -            -     -

Winner: Performance Hacker (score: 412.5)

--- Winning SQL ---
WITH monthly_trips AS (
  SELECT rider_id, COUNT(*) AS trip_count
  ...
```

---

### 4.6 — Async Context Manager for Daytona Client

Wrap the `AsyncDaytona` client in an async context manager in `main.py` (as shown above) so it's properly closed after the run. Add a top-level timeout of 120 seconds:

```python
async with asyncio.timeout(120):
    result = await run_competition(...)
```

If the timeout fires, print "Competition timed out after 120s" and exit with code 1.

---

### 4.7 — Integration Smoke Test

Create `tests/test_orchestrator.py` with a test that mocks `run_in_sandbox` to return fixture results (no real Daytona calls) and validates that `run_competition` correctly identifies the winner:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from orchestrator import run_competition

MOCK_RESULTS = [
    {"sandbox_id": "solution_001", "role": "Query Planner", "passed": True,
     "score": 389.1, "latency_ms": 1.57, "rows_returned": 10, "explain_cost": 10000, "error": None},
    {"sandbox_id": "solution_002", "role": "Performance Hacker", "passed": True,
     "score": 412.5, "latency_ms": 1.21, "rows_returned": 10, "explain_cost": 8000, "error": None},
    {"sandbox_id": "solution_003", "role": "Safety Cop", "passed": False,
     "score": 0, "latency_ms": None, "rows_returned": None, "explain_cost": None, "error": "FAILED_SAFETY"},
]

@pytest.mark.asyncio
async def test_winner_is_highest_score():
    with patch("orchestrator.run_in_sandbox", side_effect=[AsyncMock(return_value=r)() for r in MOCK_RESULTS]):
        with patch("orchestrator.generate_solutions", return_value=["p1", "p2", "p3"]):
            result = await run_competition("test task", "schema", daytona=None)
    assert result["winner"]["role"] == "Performance Hacker"
    assert result["success_count"] == 2
    assert result["failed_count"] == 1
```

**Checkpoint:** `pytest tests/test_orchestrator.py` passes without real API calls or Daytona access.

---

## Acceptance Criteria

- [ ] `orchestrator.py` exports `run_competition` returning the full result dict
- [ ] All 5 sandboxes fire in parallel (verify with timing: 5 runs should take ~max(individual) not ~sum)
- [ ] Partial failures (some sandboxes fail) don't break the competition — results are still ranked
- [ ] `main.py` prints the leaderboard table and winner SQL
- [ ] `--task` CLI argument works
- [ ] 120-second top-level timeout is enforced
- [ ] Unit test passes with mocked dependencies

---

## Learning Objectives

- How `asyncio.gather` enables true parallel execution of I/O-bound tasks
- Why the orchestrator must be resilient to partial failures — in distributed systems, some workers will always fail
- The pattern of separating orchestration logic (`orchestrator.py`) from the entrypoint (`main.py`) for testability
- How to mock async functions in pytest for fast, reliable integration tests
- Why a leaderboard output (vs. just the winner) is more valuable for debugging and demo storytelling
