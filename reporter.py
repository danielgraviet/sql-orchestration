"""
reporter.py

Event-driven terminal reporter for the SQL agent competition.
The orchestrator emits events; this class formats and prints them.
Decoupled from orchestrator so the output layer can be swapped independently.
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    GENERATION_START = "generation_start"
    GENERATION_DONE  = "generation_done"
    SANDBOX_START    = "sandbox_start"
    SANDBOX_DONE     = "sandbox_done"
    SANDBOX_FAILED   = "sandbox_failed"
    COMPETITION_DONE = "competition_done"


@dataclass
class Event:
    type: EventType
    sandbox_id: str | None = None
    role: str | None = None
    result: dict | None = None
    total: int | None = None
    completed: int | None = None
    timestamp: float = field(default_factory=time.time)


def estimate_cost(num_agents: int) -> float:
    input_tokens  = num_agents * 920
    output_tokens = num_agents * 200
    return round((input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0, 4)


class Reporter:
    def __init__(self):
        self._start_time: float | None = None
        self._gen_start: float | None = None
        self._sandbox_total: int = 0
        self._sandbox_completed: int = 0
        self._sandbox_passed: int = 0

    def on_event(self, event: Event) -> None:
        if event.type == EventType.GENERATION_START:
            self._start_time = event.timestamp
            self._gen_start = event.timestamp
            print("\n=== SQL Agent Competition ===")
            print("[1/3] Generating SQL candidates from 5 agents...")

        elif event.type == EventType.GENERATION_DONE:
            elapsed = event.timestamp - (self._gen_start or event.timestamp)
            print(f"[1/3] Generated {event.total} candidates  ✓  ({elapsed:.2f}s)\n")
            print("[2/3] Running sandboxes in parallel...")

        elif event.type == EventType.SANDBOX_START:
            self._sandbox_total += 1
            role = event.role or event.sandbox_id or "unknown"
            print(f"      → [{role:<20}] booting sandbox...")

        elif event.type in (EventType.SANDBOX_DONE, EventType.SANDBOX_FAILED):
            self._sandbox_completed += 1
            role = event.role or event.sandbox_id or "unknown"
            r = event.result or {}

            if event.type == EventType.SANDBOX_DONE:
                self._sandbox_passed += 1
                score   = r.get("score", 0)
                latency = r.get("latency_ms")
                lat_str = f"latency={latency:.2f}ms" if latency is not None else ""
                print(f"      ✓ [{role:<20}] passed   score={score:<8} {lat_str}")
            else:
                error = (r.get("error") or "unknown error").replace("FAILED_", "")
                print(f"      ✗ [{role:<20}] {error}")

            print(
                f"         progress: {self._sandbox_completed}/{self._sandbox_total} complete"
                f"  |  {self._sandbox_passed} passed"
                f"  |  {self._sandbox_completed - self._sandbox_passed} failed"
            )

        elif event.type == EventType.COMPETITION_DONE:
            self._print_summary(event)

    def _print_summary(self, event: Event) -> None:
        result = event.result or {}
        elapsed = event.timestamp - (self._start_time or event.timestamp)

        print(f"\n[3/3] Competition complete in {elapsed:.1f}s\n")

        sandboxes_run = result.get("sandboxes_run", 0)
        success_count = result.get("success_count", 0)
        p50           = result.get("p50_latency_ms")
        cost          = estimate_cost(sandboxes_run)

        print(f"Sandboxes run:    {sandboxes_run}")
        print(f"Success rate:     {success_count}/{sandboxes_run}")
        if p50 is not None:
            print(f"P50 latency:      {p50:.2f}ms")
        print(f"Est. API cost:    ~${cost}")

        # leaderboard
        all_results = result.get("all_results", [])
        if all_results:
            print(f"\n{'Rank':<5} {'Role':<22} {'Pass':<6} {'Score':<10} {'Latency(ms)':<13} {'Rows':<6} Explain Cost")
            print("-" * 74)
            for rank, r in enumerate(all_results, start=1):
                mark    = "✓" if r.get("passed") else "✗"
                score   = r.get("score") or 0
                latency = f"{r['latency_ms']:.2f}" if r.get("latency_ms") is not None else "-"
                rows    = str(r["rows_returned"]) if r.get("rows_returned") is not None else "-"
                cost_c  = str(r["explain_cost"]) if r.get("explain_cost") is not None else "-"
                role    = r.get("role") or r.get("sandbox_id") or "-"
                print(f"{rank:<5} {role:<22} {mark:<6} {score:<10} {latency:<13} {rows:<6} {cost_c}")
                if not r.get("passed") and r.get("error"):
                    print(f"      error: {r['error']}")

        # winner
        winner = result.get("winner", {})
        role   = winner.get("role") or winner.get("sandbox_id") or "unknown"
        score  = winner.get("score", 0)
        print(f"\nWinner: {role} (score: {score})")

        rationale = winner.get("rationale")
        if rationale:
            print(f"\n--- Why This Query Won ---")
            print(rationale)

        sql = result.get("winner_sql")
        if sql:
            print(f"\n--- Winning SQL ---")
            print(sql)
