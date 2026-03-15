"""
main.py

Demo entrypoint. Runs the SQL agent competition and prints the leaderboard.

Usage:
    python main.py
    python main.py --task "Busiest stations by departures last week"
    python main.py --dry-run
"""

import argparse
import asyncio
import sys

from daytona_sdk import AsyncDaytona

from data.schema_loader import get_schema_string
from orchestrator import run_competition

DEFAULT_TASK = "Top 10 riders by trips last month"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--force", action="store_true", help="Regenerate solutions from the API, ignoring cache")
    args = parser.parse_args()

    schema = get_schema_string()

    try:
        async with asyncio.timeout(120):
            async with AsyncDaytona() as daytona:
                result = await run_competition(args.task, schema, daytona, force=args.force)
    except TimeoutError:
        print("Competition timed out after 120s")
        sys.exit(1)

    _print_results(result)


def _print_results(result: dict):
    print(f"\n=== SQL Agent Competition ===")
    print(f"Task: {result['task']}\n")

    # header
    print(f"{'Rank':<5} {'Role':<20} {'Pass':<6} {'Score':<10} {'Latency(ms)':<13} {'Rows':<6} {'Explain Cost'}")
    print("-" * 72)

    for rank, r in enumerate(result["all_results"], start=1):
        passed_mark = "✓" if r.get("passed") else "✗"
        score = r.get("score") or 0
        latency = f"{r['latency_ms']:.2f}" if r.get("latency_ms") is not None else "-"
        rows = str(r["rows_returned"]) if r.get("rows_returned") is not None else "-"
        cost = str(r["explain_cost"]) if r.get("explain_cost") is not None else "-"
        role = r.get("role") or r.get("sandbox_id") or "-"
        print(f"{rank:<5} {role:<20} {passed_mark:<6} {score:<10} {latency:<13} {rows:<6} {cost}")
        if not r.get("passed") and r.get("error"):
            print(f"      error: {r['error']}")

    print()
    print(f"Sandboxes run:  {result['sandboxes_run']}")
    print(f"Success rate:   {result['success_count']}/{result['sandboxes_run']}")
    if result["p50_latency_ms"] is not None:
        print(f"P50 latency:    {result['p50_latency_ms']:.2f}ms")

    winner = result["winner"]
    role = winner.get("role") or winner.get("sandbox_id")
    print(f"\nWinner: {role} (score: {winner.get('score', 0)})")

    # get the winning SQL from the solution file
    winning_sql = _read_winner_sql(winner.get("sandbox_id"))
    if winning_sql:
        print("\n--- Winning SQL ---")
        print(winning_sql)


def _read_winner_sql(sandbox_id: str | None) -> str | None:
    """Read the SQL from the winner's solution file on disk."""
    if not sandbox_id:
        return None
    try:
        import importlib.util
        from pathlib import Path
        path = Path("solutions") / f"{sandbox_id}.py"
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location("sol", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.get_sql()
    except Exception:
        return None


if __name__ == "__main__":
    asyncio.run(main())
