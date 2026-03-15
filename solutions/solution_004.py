# role: Regression Tester
# rationale: The query uses strict inequality bounds on started_at to correctly handle the month/year rollover boundary (e.g., December→January) and avoids including trips at exactly midnight on the first of the current month. A deterministic tiebreaker (rider_id ASC) is added to ORDER BY so that ties in trip count produce a stable, reproducible top-10 list. The composite index on (rider_id, started_at) supports both the date-range filter and the GROUP BY in a single index scan.

SQL = """
SELECT
    r.rider_id,
    -- EDGE CASE: COUNT(t.trip_id) instead of COUNT(*) so riders with zero trips
    -- in the window still show 0 if LEFT JOIN is used; here we use the subquery
    -- approach to ensure riders with no trips last month are excluded cleanly
    COALESCE(trip_counts.trip_count, 0) AS trips_last_month
FROM riders r
INNER JOIN (
    SELECT
        -- EDGE CASE: rider_id in trips is NOT NULL (FK constraint), but we still
        -- group defensively; no NULL rider_ids expected but safe to rely on schema
        t.rider_id,
        COUNT(t.trip_id) AS trip_count
    FROM trips t
    WHERE
        -- EDGE CASE: 'last month' boundary must handle year rollover
        -- (e.g., January -> previous December of prior year).
        -- Using date arithmetic on the first day of the current month minus 1 day
        -- to get last month's last day, then truncating to first of that month.
        -- This works correctly across all month/year boundaries.
        t.started_at >= DATE(
            DATE('now', 'start of month', '-1 month')
        )
        AND t.started_at < DATE(
            DATE('now', 'start of month')
        )
        -- EDGE CASE: upper bound is strictly less than the first day of the
        -- current month (not <=), so trips starting exactly at midnight on
        -- the 1st of this month are excluded. This handles the date boundary
        -- precisely even for DATETIME values with time components.
    GROUP BY t.rider_id
) AS trip_counts
    ON r.rider_id = trip_counts.rider_id
-- EDGE CASE: only include riders who actually had trips last month;
-- if we wanted zero-trip riders we'd LEFT JOIN from riders, but the
-- task asks for top 10 by trips so zero-trip riders are irrelevant
WHERE trip_counts.trip_count > 0
ORDER BY
    trip_counts.trip_count DESC,
    -- EDGE CASE: ties in trip_count would produce non-deterministic ordering;
    -- use rider_id as a stable tiebreaker so results are reproducible
    r.rider_id ASC
LIMIT 10;
-- EDGE CASE: if fewer than 10 riders had trips last month, LIMIT 10 safely
-- returns however many rows exist (could be 0 for an empty result set).
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_rider_started ON trips (rider_id, started_at);"""

def get_sql() -> str:
    return SQL.strip()
