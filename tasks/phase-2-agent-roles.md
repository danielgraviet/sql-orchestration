---
phase: 2
title: Agent Roles — Five Specialized SQL Generators
status: pending
depends_on: phase-1
---

# Phase 2: Agent Roles — Five Specialized SQL Generators

## Objective

Rewrite `agent.py` to support five opinionated agent roles, each of which generates a SQL query (and optional index DDL) for the same natural-language task. Agents run in parallel. Each role's system prompt encodes a distinct perspective that drives different query strategies, giving the orchestrator a diverse candidate set.

---

## Context

The current `agent.py` generates 25 variants of an `is_prime()` function by cycling through algorithm hints. The new version should:

- Accept a task description and schema string as inputs
- Define 5 role-specific prompts (Query Planner, Performance Hacker, Safety Cop, Regression Tester, Narrator)
- Fire all 5 in parallel via `asyncio.gather`
- Return structured output per role: the SQL string, optional index DDL, and a brief rationale
- Save each solution as a `.py` file in `solutions/` that, when executed, produces the SQL string — preserving compatibility with `sandbox_runner.py`

---

## Files to Modify / Create

| File | Action |
|------|--------|
| `agent.py` | Full rewrite |
| `roles.py` | Create — role definitions live here, separate from generation logic |
| `solutions/` | Output directory (already exists) |

---

## Tasks

### 2.1 — Define Role Prompts in `roles.py`

Create `roles.py` with a `ROLES` list. Each entry is a dict with `name`, `focus`, and `system_prompt`. Write the system prompts so each role produces structurally different SQL for the same input.

**Role definitions:**

**1. Query Planner**
- Focus: correctness and readability
- Strategy: write the most straightforward JOIN/GROUP BY query possible, use CTEs for clarity, prefer explicit column names over `SELECT *`
- Output style: clean, commented SQL with no clever tricks

**2. Performance Hacker**
- Focus: minimize latency and scan cost
- Strategy: prefer covering indexes, avoid correlated subqueries, push filters as early as possible, consider window functions over self-joins, always suggest an `CREATE INDEX` statement alongside the query
- Output style: terse SQL, includes index DDL

**3. Safety Cop**
- Focus: security and statement safety
- Strategy: reject any query with DML/DDL (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER), enforce parameterized-style placeholders for any user-supplied values, flag any pattern that could allow injection
- Output style: adds a `-- SAFETY: ...` comment block at the top noting what was checked

**4. Regression Tester**
- Focus: edge cases and correctness under unusual data
- Strategy: think about NULL handling, empty result sets, ties in ORDER BY, riders with zero trips in the window, date boundary conditions (what if "last month" spans a year boundary?), and write the query defensively
- Output style: includes `-- EDGE CASE:` comments explaining each defensive choice

**5. Narrator**
- Focus: explainability for a non-technical audience
- Strategy: write a correct query, then produce a plain-English explanation of each clause, and estimate the approximate result shape (e.g., "should return ~8–15 rows for typical monthly data")
- Output style: SQL followed by a `/*  EXPLANATION: ... */` block

Each system prompt must:
- Embed the schema string (injected at call time)
- Specify exact output format (see 2.2)
- Forbid markdown fences and prose outside the structured format

**Checkpoint:** `python -c "from roles import ROLES; print([r['name'] for r in ROLES])"` prints all 5 role names.

---

### 2.2 — Define the Output Format

Each agent must return a JSON object — no markdown, no fences. Define this schema and include it verbatim in every system prompt:

```json
{
  "role": "<role name>",
  "sql": "<the complete SQL query>",
  "index_ddl": "<optional CREATE INDEX statement or null>",
  "rationale": "<1-3 sentence explanation of the approach>"
}
```

The generation function must:
1. Call Claude with `temperature=0.2` (low — we want focused, role-adherent output)
2. Strip any accidental markdown fences
3. Parse the JSON response
4. Validate that `sql` and `role` keys are present
5. Return `None` on any parse or validation failure

---

### 2.3 — Rewrite `agent.py`

Replace the existing `agent.py` with a new version that:

**Exports this async function:**
```python
async def generate_solutions(
    task: str,
    schema: str,
    count: int = 5,
) -> list[Path]
```

**Behavior:**
1. Build one prompt per role using the role's system prompt + the task + the schema
2. Fire all `count` requests in parallel with `asyncio.gather`
3. For each successful JSON response, write a `.py` file to `solutions/` in this format:

```python
# role: Query Planner
# rationale: Uses explicit JOINs and CTEs for readability.

SQL = """
SELECT r.rider_id, COUNT(*) AS trip_count
FROM trips t
JOIN riders r ON t.rider_id = r.rider_id
WHERE t.started_at >= date('now', '-30 days')
GROUP BY r.rider_id
ORDER BY trip_count DESC
LIMIT 10;
"""

INDEX_DDL = None  # or a CREATE INDEX string

def get_sql() -> str:
    return SQL.strip()
```

4. Return the list of saved `Path` objects

**Important:** The `.py` output format must be parseable by the new `benchmark.py` (Phase 3). The benchmark will call `get_sql()` to retrieve the query.

**Checkpoint:** Running `python -c "import asyncio; from agent import generate_solutions; from data.schema_loader import get_schema_string; paths = asyncio.run(generate_solutions('Top 10 riders by trips last month', get_schema_string())); print(paths)"` produces 5 files in `solutions/`.

---

### 2.4 — Preserve Backward Compatibility (Temporary)

The old `is_prime`-based code in `agent.py` should be removed entirely. The old `solutions/` directory contents should be cleared on each new run (add a `solutions/` cleanup step at the top of `generate_solutions`).

---

### 2.5 — Smoke Test All Roles

Write a quick smoke test in `tests/test_agent_roles.py`:

```python
import asyncio
import pytest
from agent import generate_solutions
from data.schema_loader import get_schema_string

TASK = "Top 10 riders by trips last month"

@pytest.mark.asyncio
async def test_generate_solutions_returns_five_files():
    paths = await generate_solutions(TASK, get_schema_string())
    assert len(paths) == 5

@pytest.mark.asyncio
async def test_each_solution_has_get_sql():
    paths = await generate_solutions(TASK, get_schema_string())
    for path in paths:
        import importlib.util
        spec = importlib.util.spec_from_file_location("sol", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sql = mod.get_sql()
        assert isinstance(sql, str)
        assert len(sql) > 10
```

**Checkpoint:** `pytest tests/test_agent_roles.py` passes (requires `ANTHROPIC_API_KEY` set).

---

## Acceptance Criteria

- [ ] `roles.py` defines 5 role dicts with `name`, `focus`, and `system_prompt`
- [ ] Each system prompt specifies the JSON output format
- [ ] `agent.py` exports `generate_solutions(task, schema, count)`
- [ ] Running the function produces 5 `.py` files, each with a callable `get_sql()`
- [ ] Solutions are cleared and regenerated on each run
- [ ] Smoke test passes end-to-end

---

## Learning Objectives

- Why role specialization produces a more diverse candidate set than temperature variation alone
- How system prompts encode domain expertise and constrain output shape
- The pattern of structured JSON output from Claude vs. free-form code generation
- Why `asyncio.gather` over sequential calls matters at demo scale
- How to design output formats that serve both human readers and downstream automated consumers
