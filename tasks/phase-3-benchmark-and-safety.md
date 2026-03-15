---
phase: 3
title: Benchmark & Safety — SQL Evaluator
status: pending
depends_on: phase-1, phase-2
---

# Phase 3: Benchmark & Safety — SQL Evaluator

## Objective

Replace the `is_prime` test harness in `benchmark.py` with a SQL evaluator that runs inside each Daytona sandbox. The evaluator must: load the fixture database, execute a candidate SQL query safely, assert correctness against expected output, measure latency and rows scanned, and hard-reject any unsafe statement before execution.

---

## Context

`benchmark.py` currently imports `is_prime`, runs 17 correctness tests, measures execution time, and emits a JSON result. The new version must do the same shape of work for SQL:

1. **Safety gate** — reject destructive or injectable SQL before touching the database
2. **Correctness gate** — compare results to `expected_top10.json`
3. **Performance measurement** — wall-clock latency, row count, EXPLAIN cost estimate
4. **Scoring** — composite score that the orchestrator uses to rank candidates
5. **JSON output** — same envelope shape as today so `sandbox_runner.py` needs no changes

The evaluator runs *inside* the Daytona sandbox, which means it has no network access, no external packages, and only what gets uploaded alongside it. It must be stdlib-only (plus `sqlite3`, which is bundled).

---

## Files to Modify / Create

| File | Action |
|------|--------|
| `benchmark.py` | Full rewrite |
| `data/expected_top10.json` | Already created in Phase 1 — consumed here |

---

## Tasks

### 3.1 — Safety Gate

Write a `check_safety(sql: str) -> tuple[bool, str]` function. It must:

**Reject any statement that:**
- Contains DML keywords: `INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `UPSERT`
- Contains DDL keywords: `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `RENAME`
- Contains transaction control: `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`
- Contains ATTACH/DETACH (SQLite-specific database mounting)
- Contains multiple statements (`;` followed by non-whitespace — basic SQLi check)
- Is empty or whitespace-only

**Allow:**
- `SELECT` statements
- `WITH ... SELECT` (CTEs)
- `EXPLAIN` or `EXPLAIN QUERY PLAN` prefixes

Return `(True, "")` if safe, `(False, "<reason>")` if rejected.

**Important:** This check is case-insensitive and must handle SQL with leading whitespace or comments.

**Checkpoint:** Unit test the safety gate with at least 8 cases:
```python
assert check_safety("SELECT 1")[0] == True
assert check_safety("DROP TABLE trips")[0] == False
assert check_safety("SELECT 1; DROP TABLE trips")[0] == False
assert check_safety("  insert into riders values (1)")[0] == False
assert check_safety("WITH cte AS (SELECT ...) SELECT * FROM cte")[0] == True
```

---

### 3.2 — Database Loader

Write `load_db(db_path: str) -> sqlite3.Connection` that:
1. Opens the SQLite file in **read-only mode**: `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`
2. Sets `row_factory = sqlite3.Row` so results are accessible by column name
3. Raises `FileNotFoundError` if the file doesn't exist

**Why read-only?** Defense in depth — even if the safety gate misses something, the connection itself can't mutate the database.

---

### 3.3 — Correctness Gate

Write `check_correctness(conn, sql: str, expected_path: str) -> tuple[bool, str]`:

1. Execute the SQL against the connection
2. Fetch all rows as list of dicts
3. Load `expected_top10.json`
4. Compare: the result must contain the same `rider_id` values in the same order, with `trip_count` within ±1 of expected (to tolerate minor data variation)
5. Return `(True, "")` or `(False, "<reason>")`

**Note:** The ±1 tolerance exists because the fixture data is generated with randomness. The expected output was captured from one seed run and may not exactly match every subsequent run if the seed is regenerated. Consider whether to fix the random seed in `data/seed.py` (recommended — see Phase 1 acceptance criteria addendum).

**Checkpoint:** Running the correctness gate with the real `rides.db` and a manually written correct query returns `(True, "")`.

---

### 3.4 — Performance Measurement

Write `measure_performance(conn, sql: str) -> dict`:

```python
{
    "latency_ms": float,       # median wall-clock time over 5 runs
    "rows_returned": int,      # number of rows in result set
    "explain_cost": float,     # estimated cost from EXPLAIN QUERY PLAN (see below)
}
```

**Latency:** Run the query 5 times, take the median. Use `time.perf_counter()`.

**Rows returned:** Count of rows in the final result set.

**EXPLAIN cost:** Run `EXPLAIN QUERY PLAN <sql>` and parse the output for estimated scan counts. SQLite's EXPLAIN QUERY PLAN output is text-based; extract the number after `~` in the "SCAN" rows (e.g., `SCAN trips (~10000 rows)` → 10000). Sum all scan estimates. If no estimate is available, return -1.

---

### 3.5 — Scoring

Write `compute_score(latency_ms, explain_cost, rows_returned, passed_correctness) -> float`:

```
score = 0 if not passed_correctness

base = (1 / latency_ms) * 500        # speed: lower latency = higher score
cost_penalty = max(0, explain_cost / 100000) * 100  # penalize full table scans
score = round(base - cost_penalty, 4)
```

The orchestrator will rank by score descending; it must be non-negative for passing solutions.

---

### 3.6 — Rewrite `benchmark.py`

The new `benchmark.py` must:

1. Accept two positional CLI args: `<solution_path>` and `<db_path>`
2. Import `get_sql()` from the solution file (same `importlib.util` pattern as today)
3. Optionally import `INDEX_DDL` from the solution (apply indexes before benchmarking if present — use a writable in-memory copy for this)
4. Run the pipeline: safety → correctness → performance → scoring
5. Print **one JSON object** to stdout matching this schema:

```json
{
  "sandbox_id": "solution_001",
  "role": "Query Planner",
  "passed": true,
  "error": null,
  "latency_ms": 1.2345,
  "rows_returned": 10,
  "explain_cost": 10000,
  "score": 405.2,
  "sql_length": 187
}
```

6. Exit with code 0 on success, 1 on any unhandled exception

**Checkpoint:** Running `python benchmark.py solutions/solution_001.py data/rides.db` produces a valid JSON line on stdout.

---

### 3.7 — Update `sandbox_runner.py`

`sandbox_runner.py` currently uploads only `benchmark.py` and the solution. It must now also upload:
- `data/rides.db` (the fixture)
- `data/expected_top10.json` (the correctness ground truth)

Update the `exec` call to pass the `db_path` argument:
```python
f"python {SANDBOX_DIR}/benchmark.py {SANDBOX_DIR}/{solution_path.name} {SANDBOX_DIR}/rides.db"
```

Update `_make_error_result` to include the new fields (`role`, `latency_ms`, `rows_returned`, `explain_cost`, `sql_length`) with `None` defaults.

**Checkpoint:** `sandbox_runner.run_in_sandbox()` returns a dict with all required keys even on failure.

---

## Acceptance Criteria

- [ ] `check_safety` correctly rejects all 5 dangerous patterns and passes safe SELECT queries
- [ ] `load_db` opens the fixture in read-only mode
- [ ] `check_correctness` validates rider IDs and trip counts against expected output
- [ ] `measure_performance` returns latency, row count, and explain cost
- [ ] `benchmark.py` runs end-to-end and emits valid JSON to stdout
- [ ] `sandbox_runner.py` uploads the fixture and passes the db path argument
- [ ] All new output dict fields have `None` defaults in error paths

---

## Learning Objectives

- Defense in depth: why two safety layers (statement whitelist + read-only connection) beats one
- How to implement a correctness oracle for non-deterministic outputs (tolerance windows)
- Why median latency over N runs is more reliable than a single measurement in sandboxes
- The pattern of a self-contained evaluator that runs identically locally and inside an isolated sandbox
- How EXPLAIN QUERY PLAN output enables lightweight cost estimation without a full query optimizer
