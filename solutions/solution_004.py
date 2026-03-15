# role: Regression Tester
# rationale: The query derives exact calendar-month boundaries using SQLite's 'start of month' modifier so it handles year and month rollovers correctly (e.g., January → December of the prior year). A LEFT JOIN from riders into the aggregated trip counts ensures riders with zero trips in the window are visible, and COALESCE converts NULLs to 0. A secondary ORDER BY rider_id tiebreaker makes the top-10 ranking fully deterministic when multiple riders share the same trip count.

SQL = """
WITH last_month_bounds AS (
    -- EDGE CASE: compute exact calendar-month boundaries to avoid partial-month inclusion
    -- 'start of month' gives first day of current month; stepping back 1 month gives first day of last month
    SELECT
        date('now', 'start of month', '-1 month')          AS period_start,  -- inclusive lower bound
        date('now', 'start of month')                       AS period_end      -- exclusive upper bound (first day of current month)
),
trip_counts AS (
    SELECT
        t.rider_id,
        COUNT(*) AS trip_count
    FROM trips t
    CROSS JOIN last_month_bounds b
    WHERE
        -- EDGE CASE: use >= / < on the DATETIME column so midnight of the last day is included
        -- and the first instant of the current month is excluded (handles year/month rollover correctly)
        t.started_at >= b.period_start
        AND t.started_at <  b.period_end
    GROUP BY t.rider_id
),
all_riders AS (
    -- EDGE CASE: LEFT JOIN ensures riders with zero trips last month are represented;
    -- they will show trip_count = 0 via COALESCE and naturally rank below active riders
    SELECT
        r.rider_id,
        COALESCE(tc.trip_count, 0) AS trip_count
    FROM riders r
    LEFT JOIN trip_counts tc ON r.rider_id = tc.rider_id  -- EDGE CASE: rider_id is INTEGER PK, no NULL join keys possible, but LEFT JOIN still guards against riders absent from trips entirely
)
SELECT
    rider_id,
    trip_count
FROM all_riders
WHERE trip_count > 0          -- EDGE CASE: exclude riders with zero trips so the top-10 list is meaningful; remove this line if zero-trip riders should appear
ORDER BY
    trip_count DESC,
    rider_id   ASC             -- EDGE CASE: tiebreaker on rider_id (deterministic, stable sort when trip counts are equal)
LIMIT 10;                      -- EDGE CASE: if fewer than 10 riders took trips last month, LIMIT safely returns however many exist (no error on empty/small result set)
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
