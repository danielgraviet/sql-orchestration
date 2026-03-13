# Task 03 — Build the Sandbox Runner

## Goal
Create `sandbox_runner.py` that takes a single solution file, runs it inside a **Daytona workspace**, executes the benchmark, and returns structured results.

## Decisions
- Sandbox provider: **Daytona**
- Hard timeout: **10 seconds** per sandbox execution
- Any sandbox exceeding the timeout is marked `FAILED_TIMEOUT` and destroyed
- Each Daytona workspace is destroyed after execution regardless of outcome

## Responsibilities
This module does one thing: run one solution in one sandbox and return one result.

## Workflow Per Sandbox

```
1. Create a Daytona workspace
2. Upload solution file + benchmark.py into the workspace
3. Execute: python benchmark.py
4. Capture stdout (JSON result)
5. Destroy the workspace
6. Return the result dict
```

## Timeout Handling
- Wrap the Daytona execution call with a 10-second timeout
- On timeout: destroy workspace, return:

```json
{
  "sandbox_id": "sandbox_007",
  "passed": false,
  "error": "FAILED_TIMEOUT",
  "execution_time_ms": null,
  "memory_mb": null,
  "score": 0
}
```

## Error States

| Error | Behavior |
|-------|----------|
| Timeout (>10s) | Mark `FAILED_TIMEOUT`, destroy workspace |
| Runtime exception in solution | Mark `FAILED_RUNTIME`, destroy workspace |
| Workspace creation failure | Mark `FAILED_SANDBOX`, log and skip |
| Benchmark parse error | Mark `FAILED_BENCHMARK`, destroy workspace |

## Interface

```python
async def run_in_sandbox(sandbox_id: str, solution_path: str) -> dict:
    ...
```

Returns the result dict defined in Task 01.

## File to Create
- `sandbox_runner.py`
