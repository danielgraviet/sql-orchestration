"""
tests/test_benchmark.py

Tests for benchmark.py. Uses the real rides.db fixture — no mocking.
Run with: pytest tests/test_benchmark.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark import (
    check_safety,
    check_correctness,
    compute_score,
    load_db,
    measure_performance,
    run_benchmark,
)

DB_PATH = str(Path(__file__).parent.parent / "data" / "rides.db")
EXPECTED_PATH = str(Path(__file__).parent.parent / "data" / "expected_top10.json")

CORRECT_SQL = """
    SELECT r.rider_id, COUNT(*) AS trip_count
    FROM trips t
    JOIN riders r ON t.rider_id = r.rider_id
    WHERE t.started_at >= date('now', '-30 days')
    GROUP BY r.rider_id
    ORDER BY trip_count DESC
    LIMIT 10
"""


# check_safety

def test_safety_allows_select():
    assert check_safety("SELECT 1")[0] is True

def test_safety_allows_cte():
    assert check_safety("WITH cte AS (SELECT 1) SELECT * FROM cte")[0] is True

def test_safety_blocks_drop():
    ok, reason = check_safety("DROP TABLE trips")
    assert ok is False
    assert "DROP" in reason

def test_safety_blocks_insert():
    ok, reason = check_safety("  insert into riders values (1)")
    assert ok is False

def test_safety_blocks_multiple_statements():
    # two benign selects — no blocked keyword, but semicolon-separated
    ok, reason = check_safety("SELECT 1; SELECT 2")
    assert ok is False
    assert "MULTIPLE_STATEMENTS" in reason

def test_safety_blocks_empty():
    assert check_safety("")[0] is False
    assert check_safety("   ")[0] is False

def test_safety_allows_commented_out_drop():
    # A comment mentioning DROP should not be flagged
    assert check_safety("SELECT 1 -- DROP TABLE trips")[0] is True

def test_safety_blocks_attach():
    assert check_safety("ATTACH '/tmp/evil.db' AS evil")[0] is False


# load_db

def test_load_db_opens_connection():
    conn = load_db(DB_PATH)
    assert conn is not None
    conn.close()

def test_load_db_is_readonly():
    conn = load_db(DB_PATH)
    with pytest.raises(Exception):
        conn.execute("INSERT INTO stations VALUES (999, 'test', 0, 0, 0)")
    conn.close()

def test_load_db_raises_for_missing_file():
    with pytest.raises(FileNotFoundError):
        load_db("/tmp/does_not_exist.db")


# check_correctness

def test_correctness_passes_for_correct_sql():
    conn = load_db(DB_PATH)
    passed, reason = check_correctness(conn, CORRECT_SQL)
    conn.close()
    assert passed is True
    assert reason == ""

def test_correctness_fails_wrong_row_count():
    conn = load_db(DB_PATH)
    bad_sql = "SELECT rider_id, COUNT(*) AS trip_count FROM trips GROUP BY rider_id ORDER BY trip_count DESC LIMIT 5"
    passed, reason = check_correctness(conn, bad_sql)
    conn.close()
    assert passed is False
    assert "ROW_COUNT_MISMATCH" in reason

def test_correctness_fails_unsorted_results():
    conn = load_db(DB_PATH)
    bad_sql = "SELECT rider_id, COUNT(*) AS trip_count FROM trips GROUP BY rider_id ORDER BY rider_id ASC LIMIT 10"
    passed, _ = check_correctness(conn, bad_sql)
    conn.close()
    assert passed is False


# measure_performance

def test_measure_performance_returns_expected_keys():
    conn = load_db(DB_PATH)
    result = measure_performance(conn, CORRECT_SQL)
    conn.close()
    assert "latency_ms" in result
    assert "rows_returned" in result
    assert "explain_cost" in result

def test_measure_performance_latency_is_positive():
    conn = load_db(DB_PATH)
    result = measure_performance(conn, CORRECT_SQL)
    conn.close()
    assert result["latency_ms"] > 0

def test_measure_performance_row_count():
    conn = load_db(DB_PATH)
    result = measure_performance(conn, CORRECT_SQL)
    conn.close()
    assert result["rows_returned"] == 10


# compute_score

def test_score_is_zero_when_correctness_fails():
    assert compute_score(1.0, 1000, passed_correctness=False) == 0.0

def test_score_is_positive_for_passing_result():
    assert compute_score(1.0, 1000, passed_correctness=True) > 0

def test_faster_query_scores_higher():
    fast = compute_score(1.0, 1000, passed_correctness=True)
    slow = compute_score(5.0, 1000, passed_correctness=True)
    assert fast > slow

def test_lower_explain_cost_scores_higher():
    cheap = compute_score(1.0, 100, passed_correctness=True)
    expensive = compute_score(1.0, 500_000, passed_correctness=True)
    assert cheap > expensive


# run_benchmark end-to-end

def test_run_benchmark_with_real_solution(tmp_path):
    solution = tmp_path / "solution_001.py"
    solution.write_text(
        f'SQL = """{CORRECT_SQL}"""\n'
        f'INDEX_DDL = None\n'
        f'def get_sql(): return SQL.strip()\n'
    )
    result = run_benchmark(str(solution), DB_PATH)
    assert result["passed"] is True
    assert result["score"] > 0
    assert result["rows_returned"] == 10
    assert result["error"] is None

def test_run_benchmark_fails_wrong_sql(tmp_path):
    # unsafe SQL now reaches the DB (sandbox handles containment),
    # but it will fail the correctness check since results won't match expected
    solution = tmp_path / "solution_bad.py"
    solution.write_text(
        'SQL = "SELECT rider_id, 0 AS trip_count FROM riders LIMIT 10"\n'
        'INDEX_DDL = None\n'
        'def get_sql(): return SQL\n'
    )
    result = run_benchmark(str(solution), DB_PATH)
    assert result["passed"] is False
    assert "FAILED_CORRECTNESS" in result["error"]

def test_run_benchmark_result_has_all_keys(tmp_path):
    solution = tmp_path / "solution_001.py"
    solution.write_text(
        f'SQL = """{CORRECT_SQL}"""\n'
        f'INDEX_DDL = None\n'
        f'def get_sql(): return SQL.strip()\n'
    )
    result = run_benchmark(str(solution), DB_PATH)
    for key in ("sandbox_id", "role", "passed", "error", "latency_ms",
                "rows_returned", "explain_cost", "score", "sql_length"):
        assert key in result, f"missing key: {key}"
