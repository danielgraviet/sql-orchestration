---
phase: 5
title: Streaming Metrics & Demo Polish
status: pending
depends_on: phase-4
---

# Phase 5: Streaming Metrics & Demo Polish

## Objective

Make the demo compelling to watch live. Add real-time streaming of sandbox lifecycle events and metrics to the terminal, a cost estimate display, and a final summary that's screenshot-ready. The output should tell a story — the audience should be able to follow each agent's journey from generation to sandbox boot to result in real time.

---

## Context

Right now the orchestrator runs silently and dumps results at the end. A live demo needs:
- Progress indicators as each sandbox boots and runs
- Streaming metric updates during execution ("sandbox 3/5 returned")
- A final summary that reinforces the demo narrative: parallelism, safety, cost control

This phase adds a `reporter.py` module and wires it into the orchestrator as a callback system. The reporter is decoupled from the orchestrator — the orchestrator emits events, the reporter formats them — so you can swap in a web UI or Slack integration later without touching the core logic.

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `reporter.py` | Create — event-driven terminal reporter |
| `orchestrator.py` | Modify — emit lifecycle events via callback |
| `main.py` | Modify — wire reporter into orchestrator |

---

## Tasks

### 5.1 — Define the Event System

In `reporter.py`, define an `Event` dataclass and event types:

```python
from dataclasses import dataclass, field
from enum import Enum
import time

class EventType(Enum):
    GENERATION_START    = "generation_start"
    GENERATION_DONE     = "generation_done"
    SANDBOX_START       = "sandbox_start"
    SANDBOX_DONE        = "sandbox_done"
    SANDBOX_FAILED      = "sandbox_failed"
    COMPETITION_DONE    = "competition_done"

@dataclass
class Event:
    type: EventType
    sandbox_id: str | None = None
    role: str | None = None
    result: dict | None = None
    total: int | None = None
    completed: int | None = None
    timestamp: float = field(default_factory=time.time)
```

Export a `Reporter` class with a single method:
```python
class Reporter:
    def on_event(self, event: Event) -> None:
        ...
```

---

### 5.2 — Implement the Terminal Reporter

`Reporter.on_event` should print live updates using `\r` carriage returns for in-place updates where possible, falling back to new lines for milestone events.

**Required output behaviors:**

**GENERATION_START:**
```
[1/5] Generating SQL candidates from 5 agents...
```

**GENERATION_DONE:**
```
[1/5] Generated 5 candidates  ✓  (0.83s)
```

**SANDBOX_START** (one line per sandbox, printed as they start):
```
      → [Query Planner]       booting sandbox...
      → [Performance Hacker]  booting sandbox...
```

**SANDBOX_DONE** (update the line in place or append):
```
      ✓ [Query Planner]       passed   score=389.1  latency=1.57ms
      ✓ [Performance Hacker]  passed   score=412.5  latency=1.21ms
      ✗ [Safety Cop]          FAILED_SAFETY
```

**Progress counter** (shown during sandbox phase, updates in place):
```
[2/5] Sandboxes: 3/5 complete, 2 passed, 1 failed
```

**COMPETITION_DONE:**
```
[3/5] Competition complete in 4.2s

Sandboxes run:    5
Success rate:     80%  (4/5)
P50 latency:      1.6ms
Est. API cost:    ~$0.02
```

---

### 5.3 — Cost Estimation

Add a `estimate_cost(solution_paths: list, results: list) -> float` function to `reporter.py`.

Estimate based on approximate token counts:
- Input tokens per agent call: schema length (~600 tokens) + task (~20 tokens) + role prompt (~300 tokens) = ~920 tokens
- Output tokens per agent call: ~200 tokens (SQL + rationale JSON)
- Claude Sonnet pricing: $3 / 1M input tokens, $15 / 1M output tokens

```python
def estimate_cost(num_agents: int) -> float:
    input_tokens = num_agents * 920
    output_tokens = num_agents * 200
    cost = (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0
    return round(cost, 4)
```

Display as `~$0.02` in the summary.

---

### 5.4 — Wire Events into the Orchestrator

Modify `orchestrator.py` to accept an optional `reporter` parameter:

```python
async def run_competition(
    task: str,
    schema: str,
    daytona: AsyncDaytona,
    reporter: Reporter | None = None,
) -> dict
```

Emit events at each lifecycle point:

```python
def _emit(event: Event):
    if reporter:
        reporter.on_event(event)

# Before generation:
_emit(Event(type=EventType.GENERATION_START))

# After generation:
_emit(Event(type=EventType.GENERATION_DONE, total=len(paths)))

# Before each sandbox (wrap run_in_sandbox):
async def _run_with_events(daytona, path, index):
    role = _read_role_from_file(path)  # read the "# role: ..." comment
    _emit(Event(type=EventType.SANDBOX_START, sandbox_id=path.stem, role=role))
    result = await run_in_sandbox(daytona, path)
    event_type = EventType.SANDBOX_DONE if result["passed"] else EventType.SANDBOX_FAILED
    _emit(Event(type=event_type, sandbox_id=path.stem, role=role, result=result))
    return result

# After all sandboxes:
_emit(Event(type=EventType.COMPETITION_DONE, result=competition_result))
```

---

### 5.5 — Update `main.py`

Wire the reporter into the competition call:

```python
from reporter import Reporter

async def main():
    ...
    reporter = Reporter()
    async with AsyncDaytona() as daytona:
        result = await run_competition(args.task, schema, daytona, reporter=reporter)
    # _print_results is now handled by reporter — remove the separate call
```

---

### 5.6 — Final Summary Block

After `COMPETITION_DONE`, the reporter should print the leaderboard table and winner SQL (moving this logic from `main.py._print_results` into `Reporter.on_event` for `COMPETITION_DONE`).

Add a "demo narrative" footer that the narrator agent's rationale gets printed in:

```
--- Why This Query Won ---
<winner's rationale from the result dict>

--- Winning SQL ---
<winner's sql>
```

---

### 5.7 — Dry-Run Mode

Add a `--dry-run` flag to `main.py`. In dry-run mode:
- Skip real Daytona sandboxes
- Use mock results (load from a `tests/fixtures/mock_results.json` if it exists, otherwise generate random plausible data)
- All reporter output still fires as normal

This lets you demo the terminal output without spending API credits or requiring Daytona access.

**Checkpoint:** `python main.py --dry-run` prints the full terminal output in under 2 seconds.

---

### 5.8 — Snapshot the Demo Output

Run the full competition once with a real setup and capture the terminal output to `demo_output.txt`:

```bash
python main.py | tee demo_output.txt
```

Commit `demo_output.txt` so reviewers can see what the demo looks like without running it.

---

## Acceptance Criteria

- [ ] `reporter.py` defines `Event`, `EventType`, and `Reporter`
- [ ] Terminal output shows live progress as sandboxes complete (not just at the end)
- [ ] Cost estimate is printed in the summary
- [ ] `--dry-run` mode works end-to-end without API keys or Daytona
- [ ] `demo_output.txt` is committed showing full competition output
- [ ] Reporter is decoupled from orchestrator (no print statements in `orchestrator.py`)
- [ ] Existing orchestrator unit tests still pass after the refactor

---

## Learning Objectives

- The observer/event pattern for decoupling side effects (logging, UI) from core logic
- Why demo polish matters for developer advocacy: audiences remember what they see, not what they read
- How `\r` carriage-return tricks enable in-place terminal updates without a full TUI framework
- The importance of a dry-run mode for demos: never depend on live infrastructure in a presentation
- How to estimate LLM API costs at design time to build cost-aware systems
