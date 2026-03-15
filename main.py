"""
main.py

Demo entrypoint. Runs the SQL agent competition and streams live progress.

Usage:
    python main.py
    python main.py --task "Busiest stations by departures last week"
    python main.py --force      # regenerate solutions, ignore cache
    python main.py --dry-run    # simulate run without API or Daytona
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from daytona_sdk import AsyncDaytona

from data.schema_loader import get_schema_string
from orchestrator import run_competition
from reporter import Event, EventType, Reporter

DEFAULT_TASK = "Top 10 riders by trips last month"
FIXTURES_PATH = Path("tests/fixtures/mock_results.json")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task",    default=DEFAULT_TASK)
    parser.add_argument("--force",   action="store_true", help="Regenerate solutions from API, ignore cache")
    parser.add_argument("--dry-run", action="store_true", help="Simulate run without API or Daytona")
    args = parser.parse_args()

    reporter = Reporter()

    if args.dry_run:
        await _dry_run(args.task, reporter)
        return

    schema = get_schema_string()

    try:
        async with asyncio.timeout(120):
            async with AsyncDaytona() as daytona:
                await run_competition(
                    args.task, schema, daytona,
                    force=args.force,
                    reporter=reporter,
                )
    except TimeoutError:
        print("Competition timed out after 120s")
        sys.exit(1)


async def _dry_run(task: str, reporter: Reporter):
    """Simulate a competition run using fixture data. No API or Daytona needed."""
    mock_results = json.loads(FIXTURES_PATH.read_text())

    reporter.on_event(Event(type=EventType.GENERATION_START))
    await asyncio.sleep(0.4)
    reporter.on_event(Event(type=EventType.GENERATION_DONE, total=len(mock_results)))

    for i, r in enumerate(mock_results):
        reporter.on_event(Event(
            type=EventType.SANDBOX_START,
            sandbox_id=r["sandbox_id"],
            role=r["role"],
        ))

    await asyncio.sleep(0.3)

    for i, r in enumerate(mock_results):
        await asyncio.sleep(0.2)
        event_type = EventType.SANDBOX_DONE if r["passed"] else EventType.SANDBOX_FAILED
        reporter.on_event(Event(
            type=event_type,
            sandbox_id=r["sandbox_id"],
            role=r["role"],
            result=r,
            completed=i + 1,
            total=len(mock_results),
        ))

    mock_results_sorted = sorted(mock_results, key=lambda r: r.get("score", 0), reverse=True)
    passing   = [r for r in mock_results_sorted if r.get("passed")]
    winner    = passing[0] if passing else mock_results_sorted[0]
    latencies = [r["latency_ms"] for r in passing if r.get("latency_ms") is not None]
    p50       = sorted(latencies)[len(latencies) // 2] if latencies else None

    competition_result = {
        "task": task,
        "winner": {**winner, "rationale": "Uses a covering index on (rider_id, started_at) to avoid a full table scan, pushing the date filter before the join."},
        "winner_sql": "SELECT r.rider_id, COUNT(*) AS trip_count\nFROM trips t\nJOIN riders r ON t.rider_id = r.rider_id\nWHERE t.started_at >= date('now', '-30 days')\nGROUP BY r.rider_id\nORDER BY trip_count DESC\nLIMIT 10;",
        "all_results": mock_results_sorted,
        "sandboxes_run": len(mock_results),
        "success_count": len(passing),
        "failed_count": len(mock_results) - len(passing),
        "p50_latency_ms": p50,
        "best_score": winner.get("score", 0),
    }

    reporter.on_event(Event(type=EventType.COMPETITION_DONE, result=competition_result))


if __name__ == "__main__":
    asyncio.run(main())
