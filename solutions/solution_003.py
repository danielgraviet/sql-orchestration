# role: Safety Cop
# rationale: The query filters trips to the previous full calendar month using SQLite date() modifiers, groups by rider, and returns the top 10 by trip count with a stable tie-break on rider_id. The composite index on (started_at, rider_id) lets SQLite satisfy the date range filter and the GROUP BY aggregation with a single efficient index scan, avoiding a full table scan on what is likely the largest table.

SQL = """
-- SAFETY:
-- 1. Read-only SELECT query; no INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
-- 2. No string concatenation or dynamic SQL; all values are literals or SQLite built-in functions.
-- 3. Date range uses SQLite-native date() with relative modifiers; no user input accepted.
-- 4. 'Last month' is computed as the calendar month prior to today using
--    date('now','start of month','-1 month') and date('now','start of month')
--    to cleanly bound the full previous calendar month.
-- 5. LIMIT 10 caps result set size; no unbounded output.
-- 6. Only columns from the defined schema are referenced.

SELECT
    t.rider_id,
    COUNT(t.trip_id) AS trip_count
FROM trips AS t
WHERE
    t.started_at >= date('now', 'start of month', '-1 month')
    AND t.started_at <  date('now', 'start of month')
GROUP BY
    t.rider_id
ORDER BY
    trip_count DESC,
    t.rider_id   ASC
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
