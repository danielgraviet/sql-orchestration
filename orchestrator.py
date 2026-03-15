"""
orchestrator.py

Core competition logic. Generates SQL candidates, runs them in parallel
Daytona sandboxes, scores results, and returns a ranked summary.
"""

import asyncio
import importlib.util
from pathlib import Path

from daytona_sdk import AsyncDaytona

from agent import generate_solutions
from reporter import Event, EventType, Reporter
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


def _read_solution_file(path: Path) -> tuple[str | None, str | None]:
    """Return (role, rationale) from a solution file's header comments."""
    role = rationale = None
    for line in path.read_text().splitlines():
        if line.startswith("# role:"):
            role = line.removeprefix("# role:").strip()
        elif line.startswith("# rationale:"):
            rationale = line.removeprefix("# rationale:").strip()
        if role and rationale:
            break
    return role, rationale


def _read_winner_sql(sandbox_id: str | None) -> str | None:
    if not sandbox_id:
        return None
    try:
        path = Path("solutions") / f"{sandbox_id}.py"
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location("sol", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.get_sql()
    except Exception:
        return None


async def run_competition(
    task: str,
    schema: str,
    daytona: AsyncDaytona,
    force: bool = False,
    reporter: Reporter | None = None,
) -> dict:
    def _emit(event: Event):
        if reporter:
            reporter.on_event(event)

    # generation
    _emit(Event(type=EventType.GENERATION_START))
    solution_paths = await generate_solutions(task, schema, force=force)
    if not solution_paths:
        raise RuntimeError("No solutions generated")
    _emit(Event(type=EventType.GENERATION_DONE, total=len(solution_paths)))

    # sandbox execution — each path gets its own wrapper that emits events
    completed = {"n": 0}

    async def _run_with_events(path: Path) -> dict:
        role, _ = _read_solution_file(path)
        _emit(Event(type=EventType.SANDBOX_START, sandbox_id=path.stem, role=role))
        result = await run_in_sandbox(daytona, path)
        completed["n"] += 1
        event_type = EventType.SANDBOX_DONE if result.get("passed") else EventType.SANDBOX_FAILED
        _emit(Event(
            type=event_type,
            sandbox_id=path.stem,
            role=role,
            result=result,
            completed=completed["n"],
            total=len(solution_paths),
        ))
        return result

    raw = await asyncio.gather(
        *[_run_with_events(path) for path in solution_paths],
        return_exceptions=True,
    )

    # normalize exceptions
    all_results = []
    for path, outcome in zip(solution_paths, raw):
        if isinstance(outcome, BaseException):
            all_results.append(_wrap_exception(path.stem, outcome))
        else:
            all_results.append(outcome)

    # rank
    all_results.sort(key=lambda r: r.get("score", 0), reverse=True)
    passing = [r for r in all_results if r.get("passed") and r.get("score", 0) > 0]
    winner  = passing[0] if passing else all_results[0]

    latencies = [r["latency_ms"] for r in passing if r.get("latency_ms") is not None]

    # enrich winner with rationale and SQL for the reporter
    _, rationale = _read_solution_file(Path("solutions") / f"{winner['sandbox_id']}.py") \
        if winner.get("sandbox_id") else (None, None)
    winner_sql = _read_winner_sql(winner.get("sandbox_id"))

    competition_result = {
        "task": task,
        "winner": {**winner, "rationale": rationale},
        "winner_sql": winner_sql,
        "all_results": all_results,
        "sandboxes_run": len(all_results),
        "success_count": len(passing),
        "failed_count": len(all_results) - len(passing),
        "p50_latency_ms": _median(latencies),
        "best_score": winner.get("score", 0),
    }

    _emit(Event(type=EventType.COMPETITION_DONE, result=competition_result))
    return competition_result
