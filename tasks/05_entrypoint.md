# Task 05 — Wire Up the Entrypoint

## Goal
Create `agent.py` as the single entrypoint that runs the full pipeline end-to-end.

## Decisions
- One command runs everything: `python agent.py`
- Clear phase separation with progress headers printed to stdout
- Exits with code 0 on success, 1 if no valid solutions found

## Pipeline Phases

```
Phase 1: Generate Solutions
  → Call LLM, save 25 solution files to solutions/

Phase 2: Run Sandboxes
  → Orchestrator launches all sandboxes in parallel
  → Results written incrementally to results/results.jsonl

Phase 3: Select Best
  → Rank results, print winner
```

## CLI Output Structure

```
=== Phase 1: Generating Solutions ===
Requesting 25 completions from Claude...
Saved 24 valid solutions (1 skipped — syntax error)

=== Phase 2: Running Sandboxes ===
Launching 24 sandboxes via Daytona...
[ 24/24] Completed: 21 | Failed: 3 | Running: 0

=== Phase 3: Results ===

Best Solution
-------------
File:           solutions/solution_014.py
Score:          97.3
Accuracy:       100%
Execution Time: 1.41ms
Memory:         3.8MB

--- solution_014.py ---
def is_prime(n: int) -> bool:
    ...
```

## Error Conditions

| Condition | Behavior |
|-----------|----------|
| All solutions fail correctness | Exit 1, print "No correct solutions found" |
| LLM call fails | Exit 1, print error |
| Fewer than 10 valid solutions generated | Warn, continue anyway |

## Environment Variables Required

```
ANTHROPIC_API_KEY=...
DAYTONA_API_KEY=...
```

Fail fast with a clear message if either is missing.

## File to Modify
- `agent.py` (already exists — wire it to orchestrator + generation logic)
