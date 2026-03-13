# Task 01 — Build the Benchmark Test Suite

## Goal
Create `benchmark.py` with a hardcoded ground-truth test suite that every candidate solution must pass before being ranked.

## Decisions
- Correctness is a **pass/fail gate** — any solution that fails a single test case is disqualified entirely
- The test suite covers known edge cases for prime detection

## Test Cases to Include

| Input | Expected | Reason |
|-------|----------|--------|
| -1 | False | Negative numbers are not prime |
| 0 | False | Zero is not prime |
| 1 | False | One is not prime by definition |
| 2 | True | Smallest prime |
| 3 | True | Small prime |
| 4 | False | Small composite |
| 13 | True | Small prime |
| 97 | True | Two-digit prime |
| 100 | False | Round composite |
| 561 | False | Carmichael number (tricky) |
| 1_000_003 | True | Large prime |
| 1_000_000_007 | True | Common CS prime |
| 1_000_000_008 | False | Large composite |

## Scoring (applied only after correctness gate passes)

```
score = (1 / execution_time_ms) * 0.6 + (1 / memory_mb) * 0.4
```

Tie-break: fewer lines of code wins.

## Performance Measurement
- Run each solution **5 times**, take the **median** execution time
- Measure peak memory with `tracemalloc`
- Record: `execution_time_ms`, `memory_mb`, `passed`, `score`

## Output Format

```json
{
  "sandbox_id": "sandbox_007",
  "passed": true,
  "execution_time_ms": 1.81,
  "memory_mb": 4.2,
  "score": 97.3,
  "lines_of_code": 12
}
```

## File to Create
- `benchmark.py`
