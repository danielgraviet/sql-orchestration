"""
benchmark.py

Runs inside each Daytona sandbox. Loads a candidate SQL solution, runs it
through safety, correctness, and performance checks, then emits one JSON
result to stdout.

Usage: python benchmark.py <solution_path> <db_path>
"""

import importlib.util
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

BENCHMARK_RUNS = 5
EXPECTED_FILENAME = "expected_top10.json"

# keywords that make a statement unsafe
_BLOCKED = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|UPSERT|DROP|CREATE|ALTER|TRUNCATE|RENAME"
    r"|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|ATTACH|DETACH)\b",
    re.IGNORECASE,
)

# strip -- line comments and /* */ block comments before safety checks
_LINE_COMMENT = re.compile(r"--[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def check_safety(sql: str) -> tuple[bool, str]:
    if not sql or not sql.strip():
        return False, "EMPTY_SQL"

    clean = _LINE_COMMENT.sub(" ", sql)
    clean = _BLOCK_COMMENT.sub(" ", clean)

    match = _BLOCKED.search(clean)
    if match:
        return False, f"BLOCKED_KEYWORD: {match.group().upper()}"

    # multiple statements: semicolon followed by more non-whitespace
    if re.search(r";\s*\S", clean):
        return False, "MULTIPLE_STATEMENTS"

    return True, ""


def load_db(db_path: str) -> sqlite3.Connection: # TODO: explain what this code does. when you say load_db, is it just connecting to our local sqlite db?
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _db_in_memory(db_path: str) -> sqlite3.Connection:
    """Copy the fixture into a writable in-memory database (for index application)."""
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    src.backup(mem)
    src.close()
    mem.row_factory = sqlite3.Row
    return mem


def check_correctness(
    conn: sqlite3.Connection,
    sql: str,
    expected_path: str,
) -> tuple[bool, str]:
    try:
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
    except Exception as e:
        return False, f"EXEC_ERROR: {e}"

    try:
        expected = json.loads(Path(expected_path).read_text())
    except Exception as e:
        return False, f"EXPECTED_LOAD_ERROR: {e}"

    if len(rows) != len(expected):
        return False, f"ROW_COUNT_MISMATCH: got {len(rows)}, expected {len(expected)}"

    for i, (got, exp) in enumerate(zip(rows, expected)):
        if got.get("rider_id") != exp["rider_id"]:
            return False, f"RIDER_ID_MISMATCH at row {i}: got {got.get('rider_id')}, expected {exp['rider_id']}"
        if abs(got.get("trip_count", 0) - exp["trip_count"]) > 1:
            return False, f"TRIP_COUNT_MISMATCH at row {i}: got {got.get('trip_count')}, expected {exp['trip_count']}"

    return True, ""


def measure_performance(conn: sqlite3.Connection, sql: str) -> dict:
    times = []
    rows = []
    for _ in range(BENCHMARK_RUNS):
        start = time.perf_counter() # what does the perf_counter do? 
        rows = conn.execute(sql).fetchall()
        times.append((time.perf_counter() - start) * 1000)

    times.sort()
    median_ms = times[BENCHMARK_RUNS // 2]

    explain_cost = _explain_cost(conn, sql)

    return {
        "latency_ms": round(median_ms, 4),
        "rows_returned": len(rows),
        "explain_cost": explain_cost,
    }


def _explain_cost(conn: sqlite3.Connection, sql: str) -> int:
    """Sum estimated row scans from EXPLAIN QUERY PLAN output. Returns -1 if unparseable."""
    try:
        plan = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
        total = 0
        found = False
        for row in plan:
            detail = str(row[-1])
            match = re.search(r"~(\d+)", detail)
            if match:
                total += int(match.group(1))
                found = True
        return total if found else -1
    except Exception:
        return -1


def compute_score(
    latency_ms: float,
    explain_cost: int,
    passed_correctness: bool,
) -> float:
    if not passed_correctness:
        return 0.0
    base = (1 / latency_ms) * 500
    penalty = max(0, explain_cost / 100_000) * 100 if explain_cost > 0 else 0
    return round(max(0.0, base - penalty), 4)


def load_solution(solution_path: str): # TODO: is this looking at our cache first? 
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "get_sql"):
        raise AttributeError("Solution missing get_sql()")
    return mod


def run_benchmark(solution_path: str, db_path: str) -> dict:
    sandbox_id = Path(solution_path).stem
    expected_path = str(Path(db_path).parent / EXPECTED_FILENAME)
    sql_length = None
    role = None

    # load solution
    try:
        mod = load_solution(solution_path)
        sql = mod.get_sql()
        index_ddl = getattr(mod, "INDEX_DDL", None)
        role = _read_role_comment(solution_path)
        sql_length = len(sql)
    except Exception as e:
        return _error_result(sandbox_id, role, f"FAILED_LOAD: {e}", sql_length)

    # correctness gate (read-only connection)
    conn_ro = load_db(db_path)
    try:
        passed, reason = check_correctness(conn_ro, sql, expected_path)
    finally:
        conn_ro.close()

    if not passed:
        return _error_result(sandbox_id, role, f"FAILED_CORRECTNESS: {reason}", sql_length)

    # performance measurement
    # apply any index on an in-memory copy so the read-only fixture is untouched
    conn_bench = _db_in_memory(db_path)
    try:
        if index_ddl:
            try:
                conn_bench.execute(index_ddl)
                conn_bench.commit()
            except Exception:
                pass  # bad index DDL — still benchmark without it
        perf = measure_performance(conn_bench, sql)
    finally:
        conn_bench.close()

    score = compute_score(perf["latency_ms"], perf["explain_cost"], passed_correctness=True)

    return {
        "sandbox_id": sandbox_id,
        "role": role,
        "passed": True,
        "error": None,
        "latency_ms": perf["latency_ms"],
        "rows_returned": perf["rows_returned"],
        "explain_cost": perf["explain_cost"],
        "score": score,
        "sql_length": sql_length,
    }


def _read_role_comment(solution_path: str) -> str | None:
    """Read the '# role: ...' comment from the top of a solution file."""
    for line in Path(solution_path).read_text().splitlines():
        if line.startswith("# role:"):
            return line.removeprefix("# role:").strip()
    return None


def _error_result(sandbox_id: str, role: str | None, error: str, sql_length: int | None) -> dict:
    return {
        "sandbox_id": sandbox_id,
        "role": role,
        "passed": False,
        "error": error,
        "latency_ms": None,
        "rows_returned": None,
        "explain_cost": None,
        "score": 0,
        "sql_length": sql_length,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python benchmark.py <solution_path> <db_path>"}))
        sys.exit(1)

    try:
        result = run_benchmark(sys.argv[1], sys.argv[2])
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": f"UNHANDLED: {e}"}))
        sys.exit(1)
