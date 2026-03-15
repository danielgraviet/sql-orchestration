---
phase: 1
title: Data Layer — SQLite Fixture & Schema
status: pending
---

# Phase 1: Data Layer — SQLite Fixture & Schema

## Objective

Replace the abstract prime-checking exercise with a real, queryable dataset. By the end of this phase, the project has a self-contained SQLite fixture database that every agent and benchmark can reference, plus a schema definition file that gets injected into agent prompts.

---

## Context

The current codebase benchmarks `is_prime()` functions. The demo pivots to SQL query generation. Agents need something real to query against. The dataset must be:

- Small enough to ship in the repo (< 5 MB)
- Rich enough to support interesting queries (joins, aggregations, date filtering)
- Self-documenting so agents can read the schema and write correct SQL

A **bike-share ride dataset** is the canonical choice: riders, stations, trips, and timestamps. It maps naturally to the demo's headline query: *"Top 10 riders by trips last month."*

---

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `data/seed.py` | Create | Generates and writes `data/rides.db` |
| `data/rides.db` | Generated | SQLite fixture used by all sandboxes |
| `data/schema.sql` | Create | Human-readable DDL (also injected into prompts) |
| `data/README.md` | Create | Documents tables, row counts, and sample queries |

---

## Tasks

### 1.1 — Design the Schema

Create `data/schema.sql` with the following four tables. Every column must have a type and a comment explaining its meaning.

```sql
-- stations: docking stations across the city
CREATE TABLE stations (
    station_id   INTEGER PRIMARY KEY,
    name         TEXT    NOT NULL,
    latitude     REAL    NOT NULL,
    longitude    REAL    NOT NULL,
    capacity     INTEGER NOT NULL  -- number of bike docks
);

-- riders: registered members
CREATE TABLE riders (
    rider_id     INTEGER PRIMARY KEY,
    member_since DATE    NOT NULL,
    plan         TEXT    NOT NULL  -- 'monthly', 'annual', 'day-pass'
);

-- bikes: individual bikes in the fleet
CREATE TABLE bikes (
    bike_id      INTEGER PRIMARY KEY,
    type         TEXT    NOT NULL, -- 'classic', 'electric'
    acquired     DATE    NOT NULL
);

-- trips: one row per completed ride
CREATE TABLE trips (
    trip_id      INTEGER PRIMARY KEY,
    rider_id     INTEGER NOT NULL REFERENCES riders(rider_id),
    bike_id      INTEGER NOT NULL REFERENCES bikes(bike_id),
    start_station INTEGER NOT NULL REFERENCES stations(station_id),
    end_station   INTEGER NOT NULL REFERENCES stations(station_id),
    started_at   DATETIME NOT NULL,
    ended_at     DATETIME NOT NULL,
    duration_sec INTEGER  NOT NULL  -- ended_at - started_at in seconds
);
```

**Checkpoint:** `data/schema.sql` exists and parses cleanly with `sqlite3 :memory: < data/schema.sql`.

---

### 1.2 — Write the Seed Script

Create `data/seed.py`. It must:

1. Import only the Python standard library (`sqlite3`, `random`, `datetime`, `pathlib`).
2. Be **idempotent**: drop and recreate all tables on every run.
3. Generate realistic data volumes:
   - 20 stations
   - 200 riders
   - 150 bikes (120 classic, 30 electric)
   - **10,000 trips** spanning the last 90 days
4. Distribute trips across the last 90 days with a mild weekend peak.
5. Set `duration_sec` as a random value between 180 and 3600 (3 min – 1 hr).
6. Print a short summary on completion:
   ```
   Seeded rides.db: 20 stations, 200 riders, 150 bikes, 10000 trips
   ```

**Checkpoint:** Running `python data/seed.py` produces `data/rides.db` with the correct row counts, verified by:
```bash
sqlite3 data/rides.db "SELECT COUNT(*) FROM trips;"
# → 10000
```

---

### 1.3 — Verify the Target Query Works

Run the demo's headline query against the fixture manually. It must return 10 rows with a `trip_count` column:

```sql
SELECT r.rider_id, COUNT(*) AS trip_count
FROM trips t
JOIN riders r ON t.rider_id = r.rider_id
WHERE t.started_at >= date('now', '-30 days')
GROUP BY r.rider_id
ORDER BY trip_count DESC
LIMIT 10;
```

**Checkpoint:** Query returns exactly 10 rows. Capture and commit the output as `data/expected_top10.json` — this becomes the correctness ground truth for the benchmark in Phase 3.

---

### 1.4 — Export Schema for Prompt Injection

Add a helper function to `data/seed.py` (or a new `data/schema_loader.py`) that returns the schema as a plain string, suitable for embedding in a Claude prompt:

```python
def get_schema_string() -> str:
    """Returns the full DDL from schema.sql as a string."""
    ...
```

**Checkpoint:** `from data.schema_loader import get_schema_string; print(get_schema_string())` prints the full DDL without error.

---

### 1.5 — Document the Data Layer

Create `data/README.md` documenting:
- Table descriptions and row counts
- Date range of the data
- The three sample queries agents are expected to handle (top riders, busiest stations, average trip duration by bike type)
- How to regenerate the fixture: `python data/seed.py`

---

## Acceptance Criteria

- [ ] `data/schema.sql` exists and is valid SQLite DDL
- [ ] `python data/seed.py` runs in < 5 seconds and produces `data/rides.db`
- [ ] `rides.db` has correct row counts (20/200/150/10000)
- [ ] `data/expected_top10.json` exists with 10 rows of ground truth
- [ ] `get_schema_string()` returns the full DDL as a string
- [ ] No external dependencies added — stdlib only for the data layer

---

## Learning Objectives

- How to build self-contained fixture data for agent benchmarking
- Why deterministic, idempotent seed scripts are critical for reproducible tests
- How schema context injected into prompts shapes agent output quality
- The pattern of capturing expected output as ground truth before writing the evaluator
