# role: Safety Cop
# rationale: The query joins riders to trips, filters to the previous calendar month using only built-in SQLite date functions (no user input), groups by rider, and returns the top 10 by trip count with a deterministic tiebreaker. The composite index on (rider_id, started_at) supports both the join and the date-range filter efficiently, avoiding a full table scan on the typically large trips table.

SQL = """
-- SAFETY:
-- 1. Read-only SELECT query; no INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
-- 2. No string concatenation or dynamic SQL used.
-- 3. All table and column references are static and schema-verified.
-- 4. Date range for 'last month' is computed entirely from built-in date functions
--    (no user input accepted), eliminating injection risk.
-- 5. LIMIT 10 is a hard-coded literal, not a parameter.
-- 6. No subquery accepts external input; all filters are deterministic.

SELECT
    r.rider_id,
    r.plan,
    COUNT(t.trip_id) AS trips_last_month
FROM riders r
JOIN trips t
    ON t.rider_id = r.rider_id
WHERE
    t.started_at >= DATE(
        'now', 'start of month', '-1 month'
    )
    AND t.started_at <  DATE(
        'now', 'start of month'
    )
GROUP BY
    r.rider_id,
    r.plan
ORDER BY
    trips_last_month DESC,
    r.rider_id ASC          -- deterministic tiebreaker
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_rider_started ON trips (rider_id, started_at);"""

def get_sql() -> str:
    return SQL.strip()
