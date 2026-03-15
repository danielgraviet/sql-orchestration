# role: Narrator
# rationale: Filtering on started_at and then grouping by rider_id means the database needs to scan only the relevant date range; a composite index on (started_at, rider_id) lets SQLite satisfy both the WHERE filter and the GROUP BY aggregation with a single efficient index range scan instead of a full table scan. The date window is built with SQLite's 'start of month' modifier to cleanly capture exactly one calendar month regardless of when the query runs.

SQL = """
SELECT
    t.rider_id,
    COUNT(*) AS trip_count
FROM trips t
WHERE t.started_at >= date('now', 'start of month', '-1 month')
  AND t.started_at <  date('now', 'start of month')
GROUP BY t.rider_id
ORDER BY trip_count DESC
LIMIT 10;

/* EXPLANATION:

  SELECT t.rider_id, COUNT(*) AS trip_count
    - We ask for each rider's ID and a count of how many trips they took.
      COUNT(*) simply counts every row that belongs to that rider.

  FROM trips t
    - We read from the trips table (nicknamed 't' for brevity).
      Every completed ride is one row here.

  WHERE t.started_at >= date('now', 'start of month', '-1 month')
    - 'date("now", "start of month", "-1 month")' calculates the first day
      of the previous calendar month (e.g. if today is 2024-07-15, this
      evaluates to 2024-06-01).  We only keep trips that started on or
      after that date.

  AND t.started_at < date('now', 'start of month')
    - 'date("now", "start of month")' is the first day of the current month
      (e.g. 2024-07-01).  Together with the lower bound this gives us an
      exact window: all of last month and nothing else.

  GROUP BY t.rider_id
    - After filtering, we collapse all rows for the same rider into a
      single summary row so COUNT(*) can total up their trips.

  ORDER BY trip_count DESC
    - Sort the summary rows from most trips to fewest, so the busiest
      riders float to the top.

  LIMIT 10
    - Keep only the top 10 rows — the ten riders with the most trips
      last month.

  Expected result shape: exactly 10 rows (or fewer if fewer than 10
  distinct riders took any trip last month).  Each row has a rider_id
  and their trip count for the previous calendar month.
*/
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
