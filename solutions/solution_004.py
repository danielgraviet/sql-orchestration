# role: Regression Tester
# rationale: The date window uses SQLite's 'start of month' modifier with '-1 month' to correctly handle year-rollover boundaries (e.g., January wrapping back to December), and the upper bound is exclusive to avoid including the first instant of the current month. A tiebreaker on rider_id ensures deterministic top-10 results when multiple riders share the same trip count. The composite index on (rider_id, started_at) lets SQLite satisfy both the join and the date-range filter with a single index scan.

SQL = """
SELECT
    r.rider_id,
    -- EDGE CASE: COUNT(t.trip_id) instead of COUNT(*) so riders with zero qualifying trips
    -- still return 0 if they appear via a LEFT JOIN (though here we use INNER JOIN intentionally
    -- to exclude non-riders; see riders CTE note below)
    COUNT(t.trip_id) AS trip_count
FROM (
    -- EDGE CASE: Anchor to ALL riders so we could detect zero-trip riders if needed;
    -- using riders table as the base ensures rider_id is never NULL from the left side
    SELECT rider_id FROM riders
) AS r
INNER JOIN trips AS t
    ON t.rider_id = r.rider_id
    -- EDGE CASE: rider_id could theoretically be NULL in trips (despite NOT NULL constraint);
    -- INNER JOIN naturally excludes any such rows
    -- EDGE CASE: "last month" uses exact calendar-month boundaries to avoid
    -- off-by-one errors at month/year rollovers (e.g., Jan -> Dec of prior year).
    -- date('now','start of month','-1 month') correctly handles January -> December rollover.
    AND t.started_at >= date('now', 'start of month', '-1 month')
    -- EDGE CASE: upper bound is exclusive start of current month, so trips at exactly
    -- midnight on the 1st of the current month are excluded (correct behaviour).
    AND t.started_at <  date('now', 'start of month')
GROUP BY r.rider_id
ORDER BY
    trip_count DESC,
    -- EDGE CASE: ties in trip_count would produce non-deterministic ordering;
    -- tiebreak on rider_id (ascending) gives a stable, reproducible top-10.
    r.rider_id ASC
-- EDGE CASE: if fewer than 10 riders took any trips last month, LIMIT 10 simply
-- returns however many rows exist (empty result set is handled gracefully).
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_rider_started ON trips (rider_id, started_at);"""

def get_sql() -> str:
    return SQL.strip()
