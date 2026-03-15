# role: Narrator
# rationale: Filtering on started_at to isolate the previous calendar month uses SQLite's 'start of month' modifier for clean, boundary-safe date arithmetic. Grouping by rider_id and counting gives each rider's total, and LIMIT 10 after descending sort surfaces the top performers. The composite index on (started_at, rider_id) lets SQLite satisfy both the range filter and the groupby column from the index alone, avoiding a full table scan.

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

   FROM trips t
     - We read from the trips table (nicknamed 't' for brevity).

   WHERE t.started_at >= date('now', 'start of month', '-1 month')
     - 'date("now", "start of month", "-1 month")' calculates the first day
       of the previous calendar month (e.g. if today is 2024-07-15, this
       evaluates to 2024-06-01). We only keep trips that started on or after
       that date.

   AND t.started_at < date('now', 'start of month')
     - 'date("now", "start of month")' is the first day of the current month
       (e.g. 2024-07-01). We exclude trips from the current month, so together
       the two WHERE conditions form an exact window covering all of last month.

   GROUP BY t.rider_id
     - We collapse all the matching rows so that each rider appears just once,
       and COUNT(*) tallies their trips within that group.

   ORDER BY trip_count DESC
     - We sort the results so the rider with the most trips appears first.

   LIMIT 10
     - We keep only the top 10 riders.

   Expected result shape: exactly 10 rows (or fewer if fewer than 10 riders
   took any trip last month). Each row has a rider_id and their trip count
   for the previous calendar month.
*/
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
