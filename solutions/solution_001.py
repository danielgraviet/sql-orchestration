# role: Query Planner
# rationale: A CTE computes the exact start and end dates of the previous calendar month using SQLite date functions, keeping the filter logic readable and reusable. Trips are filtered and aggregated by rider in a second CTE, then joined to riders for plan/tenure context. The composite index on (started_at, rider_id) supports the date-range filter and allows a covering scan for the GROUP BY without touching the full table.

SQL = """
-- Top 10 riders by number of trips completed in the previous calendar month
WITH last_month_bounds AS (
    -- Compute the first and last day of the previous calendar month
    SELECT
        date('now', 'start of month', '-1 month')        AS month_start,
        date('now', 'start of month', '-1 day')           AS month_end
),
trip_counts AS (
    SELECT
        t.rider_id,
        COUNT(t.trip_id) AS trip_count
    FROM trips t
    CROSS JOIN last_month_bounds b
    WHERE date(t.started_at) >= b.month_start
      AND date(t.started_at) <= b.month_end
    GROUP BY t.rider_id
)
SELECT
    tc.rider_id,
    r.plan,
    r.member_since,
    tc.trip_count
FROM trip_counts tc
JOIN riders r ON r.rider_id = tc.rider_id
ORDER BY tc.trip_count DESC
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
