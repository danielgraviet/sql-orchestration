# role: Query Planner
# rationale: The CTE filters and aggregates trips to the previous calendar month using date truncation for clean month boundaries, then joins to riders for profile details. The composite index on (rider_id, started_at) supports both the date range filter and the GROUP BY in a single index scan, avoiding a full table scan on what is likely the largest table.

SQL = """
WITH last_month_trips AS (
    -- Filter trips to only those that started in the previous calendar month
    SELECT
        rider_id,
        COUNT(*) AS trip_count
    FROM trips
    WHERE
        started_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        AND started_at <  DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY rider_id
)
SELECT
    r.rider_id,
    r.plan,
    r.member_since,
    lmt.trip_count
FROM last_month_trips lmt
JOIN riders r ON r.rider_id = lmt.rider_id
ORDER BY lmt.trip_count DESC
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX idx_trips_rider_started ON trips (rider_id, started_at);"""

def get_sql() -> str:
    return SQL.strip()
