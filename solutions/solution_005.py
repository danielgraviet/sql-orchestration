# role: Narrator
# rationale: Filtering on started_at to isolate last calendar month and then grouping by rider_id with COUNT(*) is the most direct approach. The composite index on (started_at, rider_id) lets the database satisfy the date range filter with a seek and then read rider_id directly from the index without touching the main table heap, making the query efficient even on large trip tables.

SQL = """
SELECT
    t.rider_id,
    COUNT(*) AS trip_count
FROM trips t
WHERE t.started_at >= DATE('now', 'start of month', '-1 month')
  AND t.started_at <  DATE('now', 'start of month')
GROUP BY t.rider_id
ORDER BY trip_count DESC
LIMIT 10;

/* EXPLANATION:
   SELECT t.rider_id, COUNT(*) AS trip_count
     - We ask for each rider's ID and a count of how many trips they took.

   FROM trips t
     - We look in the trips table (nicknamed 't' for short).

   WHERE t.started_at >= DATE('now', 'start of month', '-1 month')
     AND t.started_at <  DATE('now', 'start of month')
     - We only keep rows where the trip started during last calendar month.
       DATE('now', 'start of month') gives us midnight on the 1st of the
       current month; subtracting one month gives us the 1st of last month.
       Together the two conditions form a half-open interval [first of last
       month, first of this month), so every day of last month is included
       and nothing from this month sneaks in.

   GROUP BY t.rider_id
     - We collapse all the matching rows down to one row per rider so
       COUNT(*) can tally each rider's trips separately.

   ORDER BY trip_count DESC
     - We sort the results so the rider with the most trips appears first.

   LIMIT 10
     - We keep only the top 10 rows.

   Expected shape: exactly 10 rows (or fewer if fewer than 10 riders
   took any trips last month). Each row has a rider_id and their trip
   count for last month, sorted highest to lowest.
*/
"""

INDEX_DDL = """CREATE INDEX IF NOT EXISTS idx_trips_started_at_rider ON trips (started_at, rider_id);"""

def get_sql() -> str:
    return SQL.strip()
