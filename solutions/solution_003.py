# role: Safety Cop
# rationale: The query filters trips to the previous calendar month using SQLite date literals, groups by rider, and returns the top 10 by trip count with a tie-breaking sort on rider_id for determinism. The composite index on (started_at, rider_id) supports the date-range filter and allows the grouping aggregation to be resolved efficiently from the index alone.

SQL = """
-- SAFETY:
-- 1. Read-only SELECT query; no INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
-- 2. No string concatenation or dynamic SQL; all values are literals.
-- 3. Date range uses SQLite-native date() with relative modifiers; no user input.
-- 4. 'Last month' is computed as the calendar month prior to today using
--    date('now','start of month','-1 month') and date('now','start of month'),
--    ensuring a precise, injection-safe boundary.
-- 5. LIMIT is a hard-coded integer literal, not a parameter.
-- 6. All referenced columns and tables exist in the provided schema.
SELECT
    t.rider_id,
    COUNT(t.trip_id) AS trip_count
FROM trips AS t
WHERE t.started_at >= date('now', 'start of month', '-1 month')
  AND t.started_at <  date('now', 'start of month')
GROUP BY t.rider_id
ORDER BY trip_count DESC, t.rider_id ASC
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
