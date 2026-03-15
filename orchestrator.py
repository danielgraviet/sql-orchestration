"""
orchestrator.py

Core competition logic. Generates SQL candidates, runs them in parallel
Daytona sandboxes, scores results, and returns a ranked summary.
"""

import asyncio

from daytona_sdk import AsyncDaytona

from agent import generate_solutions
from sandbox_runner import run_in_sandbox


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 != 0 else (s[mid - 1] + s[mid]) / 2


def _wrap_exception(sandbox_id: str, exc: BaseException) -> dict:
    return {
        "sandbox_id": sandbox_id,
        "role": None,
        "passed": False,
        "error": f"FAILED_EXCEPTION: {exc}",
        "latency_ms": None,
        "rows_returned": None,
        "explain_cost": None,
        "score": 0,
        "sql_length": None,
    }


async def run_competition(
    task: str,
    schema: str,
    daytona: AsyncDaytona,
    force: bool = False,
) -> dict:
    # generate candidates
    solution_paths = await generate_solutions(task, schema, force=force)
    if not solution_paths:
        raise RuntimeError("No solutions generated")
    print(f"Generated {len(solution_paths)} solutions")

    # run all sandboxes in parallel
    raw = await asyncio.gather(
        *[run_in_sandbox(daytona, path) for path in solution_paths],
        return_exceptions=True,
    )

    # normalize any unexpected exceptions into error result dicts
    all_results = []
    for path, outcome in zip(solution_paths, raw):
        if isinstance(outcome, BaseException):
            all_results.append(_wrap_exception(path.stem, outcome))
        else:
            all_results.append(outcome)

    # rank by score descending
    all_results.sort(key=lambda r: r.get("score", 0), reverse=True)

    passing = [r for r in all_results if r.get("passed") and r.get("score", 0) > 0]
    winner = passing[0] if passing else all_results[0]

    latencies = [r["latency_ms"] for r in passing if r.get("latency_ms") is not None]

    return {
        "task": task,
        "winner": winner,
        "all_results": all_results,
        "sandboxes_run": len(all_results),
        "success_count": len(passing),
        "failed_count": len(all_results) - len(passing),
        "p50_latency_ms": _median(latencies),
        "best_score": winner.get("score", 0),
    }
