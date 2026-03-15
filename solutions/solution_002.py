# role: Performance Hacker
# rationale: Filter trips to last calendar month using date boundary arithmetic so the index range scan is tight. The composite index on (started_at, rider_id) lets SQLite satisfy both the WHERE filter and the GROUP BY aggregation with a single index-only scan, avoiding a full table scan on trips.

SQL = """
SELECT rider_id, COUNT(*) AS trip_count
FROM trips
WHERE started_at >= date('now','start of month','-1 month')
  AND started_at <  date('now','start of month')
GROUP BY rider_id
ORDER BY trip_count DESC
LIMIT 10;
"""

INDEX_DDL = """CREATE INDEX idx_trips_started_rider ON trips(started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
