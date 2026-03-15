# sql-orchestration

Demo story for a mixed audience: **3–5 specialized Claude agents** compete (and optionally collaborate) to generate and validate SQL queries inside **isolated Daytona sandboxes**. The orchestrator scores each attempt on correctness, performance, and safety, then surfaces the best result.

The message: you don’t need 500 workers to feel like you have 500 brains— a small, diverse team of agents plus sandbox isolation delivers quality, speed, and safety.

---

## Why This Demo

- Sequential agents are slow and risky; they run untrusted code directly.
- Sandboxes let us explore many ideas safely and in parallel.
- A small team of opinionated agents (planner, optimizer, tester, safety cop, explainer) tends to beat a single “do everything” agent.

---

## Scenario (what the audience sees)

Given a natural-language request (e.g., “Top 10 riders by trips last month”), agents must produce a performant SQL query against a sample dataset. Each agent ships a tiny Python snippet that builds the SQL, plus optional indexes/hints. Daytona sandboxes execute the query against the dataset, measure latency, check results, and report metrics.

**Roles (3–5 agents):**

1) Query Planner – aims for correctness and readability.
2) Performance Hacker – minimizes latency and scan cost.
3) Safety Cop – checks for injection / destructive statements.
4) Regression Tester – runs hidden edge cases.
5) Narrator (optional) – explains the chosen plan for humans.

---

## Flow

1. **Generate variants** – Each role prompts Claude with its perspective; outputs live in `solutions/`.
2. **Isolated execution** – `sandbox_runner.py` boots a fresh Daytona sandbox per variant and uploads the candidate plus `benchmark.py`.
3. **Benchmark & safety checks** – `benchmark.py` validates results, measures runtime/memory, and rejects unsafe SQL.
4. **Score & select** – Orchestrator aggregates JSON results and picks the best-performing safe query.
5. **Observe** – Metrics like `sandboxes_running`, `success_rate`, `p50_latency_ms`, `est_cost` stream during the run.

---

## Safety Story

- Each agent’s code and SQL run in a disposable sandbox (filesystem, process, and resource isolation).
- Timeouts and auto-stop/auto-delete keep costs predictable.
- “Bad” behavior (DROP TABLE, infinite loops, network egress) is contained and surfaced as a failure, not an outage.

---

## Repository Map (today)

- `agent.py` – generates candidate implementations with Claude. Swap the prompt to emit SQL builders instead of `is_prime` functions.
- `benchmark.py` – in-sandbox evaluator. Currently targets a prime-checking exercise; replace the test harness with your SQL dataset + assertions.
- `sandbox_runner.py` – creates sandboxes, uploads a candidate + benchmark, executes, parses JSON, always destroys the sandbox.
- `solutions/` – generated candidates land here.
- `main.py` – thin entrypoint; extend to orchestrate the full multi-agent loop.

> Note: The code presently benchmarks prime-checking functions. The demo script above describes the SQL variant you’ll present. Adjust `agent.py` prompts and `benchmark.py` accordingly (see “Adapting to SQL” below).

---

## Run It (prototype)

```bash
export ANTHROPIC_API_KEY=...
python agent.py          # generate candidate implementations into solutions/
# Wire your orchestrator to call sandbox_runner.run_in_sandbox() for each file
```

Streaming metrics and selection logic live in the orchestrator you add on top of `sandbox_runner.py`.

---

## Adapting to SQL (what to change)

- **Prompt** (`agent.py`): ask for a function that returns a SQL string (and optional index DDL) given the task text and table schema.
- **Benchmark** (`benchmark.py`):
  - Load a fixture DB (e.g., SQLite file) inside the sandbox.
  - Execute the generated SQL safely (whitelist read-only ops, parameterize inputs).
  - Assert correctness vs. expected rows; measure latency/rows scanned.
  - Fail fast on disallowed statements.
- **Metrics**: emit `latency_ms`, `rows_scanned`, `explain_cost`, and a composite score.
- **Orchestrator**: run 3–5 agents with the role prompts above; keep them in independent sandboxes to prove isolation.

---

## What to Emphasize in the Talk

- Parallelism you can trust: every attempt runs in its own disposable sandbox.
- Small, diverse agent team > single agent; roles drive better search coverage.
- Infrastructure, not a toy: same pattern fits codegen, data cleaning, fuzzing—just swap the benchmark.
- Cost control: cap sandboxes, short timeouts, auto-delete.

---

## Quick FAQ

- **Why 3–5 agents, not 500?** Quality and interpretability win; sandbox isolation still scales if you need more.
- **What about safety?** Sandboxes, read-only DB fixtures, statement whitelists, and timeouts keep bad queries contained.
- **How hard is it to swap tasks?** Change the prompt + benchmark; the sandbox pattern stays the same.
