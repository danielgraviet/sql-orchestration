# Task 04 — Build the Orchestrator

## Goal
Create `orchestrator.py` that launches all sandbox workers **in parallel**, collects results, persists them incrementally, and selects the best solution.

## Decisions
- All sandboxes launch concurrently via `asyncio.gather`
- Results written to `results/results.jsonl` **as each sandbox completes** (not at the end)
- On re-run, existing results in `results.jsonl` are loaded and those sandbox IDs are skipped (crash resume)
- Ranking: correctness gate → composite score → tie-break by lines of code

## Workflow

```
1. Load existing results from results/results.jsonl (if present)
2. Determine which solution files have not yet been run
3. Launch remaining sandboxes in parallel via asyncio.gather
4. As each completes, append result to results.jsonl
5. Print live progress to stdout
6. After all complete, rank results and print best solution
```

## Live Progress Output

```
[  5/25] Completed: 4 | Failed: 1 | Running: 20
[ 12/25] Completed: 10 | Failed: 2 | Running: 13
[25/25] Completed: 22 | Failed: 3 | Running: 0

Best Solution
-------------
File:           solutions/solution_014.py
Score:          97.3
Accuracy:       100%
Execution Time: 1.41ms
Memory:         3.8MB
```

## Persistence Format (`results/results.jsonl`)
One JSON object per line, appended as results arrive:

```jsonl
{"sandbox_id": "sandbox_001", "passed": true, "execution_time_ms": 2.1, ...}
{"sandbox_id": "sandbox_002", "passed": false, "error": "FAILED_TIMEOUT", ...}
```

## Ranking Logic

```python
# Step 1: filter to passed=True only
# Step 2: sort by score descending
# Step 3: tie-break by lines_of_code ascending
# Step 4: return top result
```

## File to Create
- `orchestrator.py`
- `results/` directory (gitignored)
