# Data Layer

Bike-share ride dataset for the SQL agent demo. A SQLite fixture with four tables covering stations, riders, bikes, and trips.

## Tables

| Table | Rows | Description |
|-------|------|-------------|
| `stations` | 20 | Docking stations with name, coordinates, and capacity |
| `riders` | 200 | Registered members on monthly, annual, or day-pass plans |
| `bikes` | 150 | Fleet of 75 classic and 75 electric bikes |
| `trips` | 10,000 | Completed rides over the last 90 days |

## Date range

Trips span the 90 days prior to when `seed.py` was last run, with a mild weekend peak in ride frequency.

## Sample queries

Top 10 riders by trips last month:
```sql
SELECT r.rider_id, COUNT(*) AS trip_count
FROM trips t
JOIN riders r ON t.rider_id = r.rider_id
WHERE t.started_at >= date('now', '-30 days')
GROUP BY r.rider_id
ORDER BY trip_count DESC
LIMIT 10;
```

Busiest stations by departures:
```sql
SELECT s.name, COUNT(*) AS departures
FROM trips t
JOIN stations s ON t.start_station = s.station_id
GROUP BY s.station_id
ORDER BY departures DESC
LIMIT 5;
```

Average trip duration by bike type:
```sql
SELECT b.type, ROUND(AVG(t.duration_sec) / 60.0, 1) AS avg_minutes
FROM trips t
JOIN bikes b ON t.bike_id = b.bike_id
GROUP BY b.type;
```

## Regenerating the database

```bash
python data/seed.py
```

The script is idempotent — running it again drops and recreates all tables cleanly. The random seed is fixed at 42 so output is reproducible.

## Schema prompt injection

```python
from data.schema_loader import get_schema_string
schema = get_schema_string()  # pass this string into agent prompts
```
