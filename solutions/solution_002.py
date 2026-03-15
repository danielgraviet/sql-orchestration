# role: Performance Hacker
# rationale: Filter trips to last month using a range on started_at, then aggregate by rider_id — no join needed since rider identity is already on the trips table. The composite index on (started_at, rider_id) allows the DB to satisfy the range filter and the GROUP BY aggregation via an index-only scan, minimizing I/O.

SQL = """
SELECT rider_id, COUNT(*) AS trips
FROM trips
WHERE started_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND started_at <  DATE_TRUNC('month', CURRENT_DATE)
GROUP BY rider_id
ORDER BY trips DESC
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
