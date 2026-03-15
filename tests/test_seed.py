"""
tests/test_seed.py

Tests for data/seed.py. All tests use a temp file SQLite database —
no persistent files are written and each test starts from a clean state.

Run with:
    pytest tests/test_seed.py -v
"""

import sqlite3
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.seed import seed


@pytest.fixture(scope="module")
def db(tmp_path_factory) -> Generator[sqlite3.Connection, None, None]:
    db_file = tmp_path_factory.mktemp("data") / "test_rides.db"
    seed(db_path=db_file)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# row counts

def test_station_count(db):
    (n,) = db.execute("SELECT COUNT(*) FROM stations").fetchone()
    assert n == 20

def test_rider_count(db):
    (n,) = db.execute("SELECT COUNT(*) FROM riders").fetchone()
    assert n == 200

def test_bike_count(db):
    (n,) = db.execute("SELECT COUNT(*) FROM bikes").fetchone()
    assert n == 150

def test_trip_count(db):
    (n,) = db.execute("SELECT COUNT(*) FROM trips").fetchone()
    assert n == 10_000


# referential integrity

def test_no_orphaned_rider_ids(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE rider_id NOT IN (SELECT rider_id FROM riders)"
    ).fetchone()
    assert n == 0, f"{n} trips reference non-existent riders"

def test_no_orphaned_bike_ids(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE bike_id NOT IN (SELECT bike_id FROM bikes)"
    ).fetchone()
    assert n == 0, f"{n} trips reference non-existent bikes"

def test_no_orphaned_start_stations(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE start_station NOT IN (SELECT station_id FROM stations)"
    ).fetchone()
    assert n == 0, f"{n} trips reference non-existent start stations"

def test_no_orphaned_end_stations(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE end_station NOT IN (SELECT station_id FROM stations)"
    ).fetchone()
    assert n == 0, f"{n} trips reference non-existent end stations"


# data quality

def test_no_negative_trip_duration(db):
    (n,) = db.execute("SELECT COUNT(*) FROM trips WHERE duration_sec < 0").fetchone()
    assert n == 0

def test_trip_duration_within_bounds(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE duration_sec < 180 OR duration_sec > 3600"
    ).fetchone()
    assert n == 0

def test_ended_at_after_started_at(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE ended_at <= started_at"
    ).fetchone()
    assert n == 0

def test_trips_within_90_day_window(db):
    (n,) = db.execute(
        "SELECT COUNT(*) FROM trips WHERE started_at < date('now', '-90 days')"
    ).fetchone()
    assert n == 0, f"{n} trips fall outside the 90-day window"


# distribution

def test_even_bike_type_split(db):
    rows = db.execute("SELECT type, COUNT(*) AS n FROM bikes GROUP BY type").fetchall()
    counts = {row["type"]: row["n"] for row in rows}
    assert counts.get("electric") == 75
    assert counts.get("classic") == 75

def test_all_rider_plans_present(db):
    rows = db.execute("SELECT DISTINCT plan FROM riders").fetchall()
    plans = {row["plan"] for row in rows}
    assert plans == {"monthly", "annual", "day-pass"}

def test_station_coordinates_are_realistic(db):
    rows = db.execute("SELECT latitude, longitude FROM stations").fetchall()
    for row in rows:
        assert 37.5 < row["latitude"] < 37.9
        assert -122.6 < row["longitude"] < -122.2

def test_trips_spread_across_multiple_days(db):
    (n,) = db.execute(
        "SELECT COUNT(DISTINCT DATE(started_at)) FROM trips"
    ).fetchone()
    assert n >= 60, f"Only {n} distinct days — data may not be spread correctly"


# target query

def test_top_10_riders_query_returns_10_rows(db):
    rows = db.execute("""
        SELECT r.rider_id, COUNT(*) AS trip_count
        FROM trips t
        JOIN riders r ON t.rider_id = r.rider_id
        WHERE t.started_at >= date('now', '-30 days')
        GROUP BY r.rider_id
        ORDER BY trip_count DESC
        LIMIT 10
    """).fetchall()
    assert len(rows) == 10

def test_top_10_riders_trip_counts_are_positive(db):
    rows = db.execute("""
        SELECT COUNT(*) AS trip_count
        FROM trips t
        WHERE t.started_at >= date('now', '-30 days')
        GROUP BY t.rider_id
        ORDER BY trip_count DESC
        LIMIT 10
    """).fetchall()
    for row in rows:
        assert row["trip_count"] > 0


# idempotency

def test_seed_is_idempotent(tmp_path):
    db_file = tmp_path / "idempotent.db"
    seed(db_path=db_file)
    seed(db_path=db_file)

    conn = sqlite3.connect(db_file)
    (n,) = conn.execute("SELECT COUNT(*) FROM trips").fetchone()
    conn.close()
    assert n == 10_000, "Second seed run should not double the row count"
