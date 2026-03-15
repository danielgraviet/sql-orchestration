import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "rides.db"

_DROP_TABLES = """
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS bikes;
DROP TABLE IF EXISTS riders;
DROP TABLE IF EXISTS stations;
"""

_CREATE_STATIONS = """
CREATE TABLE stations (
    station_id  INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    capacity    INTEGER NOT NULL
)
"""

_CREATE_RIDERS = """
CREATE TABLE riders (
    rider_id     INTEGER PRIMARY KEY,
    member_since DATE    NOT NULL,
    plan         TEXT    NOT NULL
)
"""

_CREATE_BIKES = """
CREATE TABLE bikes (
    bike_id   INTEGER PRIMARY KEY,
    type      TEXT    NOT NULL,
    acquired  DATE    NOT NULL
)
"""

_CREATE_TRIPS = """
CREATE TABLE trips (
    trip_id        INTEGER PRIMARY KEY,
    rider_id       INTEGER NOT NULL REFERENCES riders(rider_id),
    bike_id        INTEGER NOT NULL REFERENCES bikes(bike_id),
    start_station  INTEGER NOT NULL REFERENCES stations(station_id),
    end_station    INTEGER NOT NULL REFERENCES stations(station_id),
    started_at     DATETIME NOT NULL,
    ended_at       DATETIME NOT NULL,
    duration_sec   INTEGER  NOT NULL
)
"""

STATION_NAMES = [
    "Downtown Transit Hub", "Riverside Park", "City Hall", "University Ave",
    "Central Market", "Harbor Front", "North Station", "East End",
    "West Loop", "South Beach", "Tech Campus", "Old Town Square",
    "Airport Connector", "Sports Complex", "Museum District",
    "Financial Center", "Midtown Plaza", "Lakeside Trail",
    "Convention Center", "Medical Campus",
]


def _seed_stations(cursor: sqlite3.Cursor) -> int:
    rows = []
    for i, name in enumerate(STATION_NAMES, start=1):
        rows.append((
            i,
            name,
            round(37.7 + random.uniform(-0.15, 0.15), 6),   # latitude
            round(-122.4 + random.uniform(-0.15, 0.15), 6), # longitude
            random.randint(10, 30),                          # capacity
        ))
    cursor.executemany(
        "INSERT INTO stations (station_id, name, latitude, longitude, capacity) VALUES (?,?,?,?,?)",
        rows,
    )
    return len(rows)


def _seed_riders(cursor: sqlite3.Cursor) -> int:
    plans = ["monthly", "annual", "day-pass"]
    today = datetime.now().date()
    rows = []
    for i in range(1, 201):
        days_ago = random.randint(30, 730)
        member_since = (today - timedelta(days=days_ago)).isoformat() # what is isoformat? is that industry standard? 
        rows.append((i, member_since, random.choice(plans)))
    cursor.executemany(
        "INSERT INTO riders (rider_id, member_since, plan) VALUES (?,?,?)",
        rows,
    )
    return len(rows)


def _seed_bikes(cursor: sqlite3.Cursor) -> int:
    today = datetime.now().date()
    rows = []
    for i in range(1, 151):
        bike_type = "electric" if i <= 75 else "classic"
        days_ago = random.randint(60, 1095) # I am guessing this just chooses a random number between the two??
        acquired = (today - timedelta(days=days_ago)).isoformat()
        rows.append((i, bike_type, acquired))
    cursor.executemany(
        "INSERT INTO bikes (bike_id, type, acquired) VALUES (?,?,?)",
        rows,
    )
    return len(rows)


def _seed_trips(cursor: sqlite3.Cursor, num_trips: int = 10_000) -> int:
    now = datetime.now()
    rows = []
    for i in range(1, num_trips + 1):
        # Distribute trips over the last 90 days with mild weekend peak
        days_ago = random.randint(0, 89)
        candidate = now - timedelta(days=days_ago)
        # Boost probability on weekends (Saturday=5, Sunday=6)
        if candidate.weekday() >= 5 and random.random() < 0.3:
            days_ago = max(0, days_ago - 1)

        duration_sec = random.randint(180, 3600)
        started_at = now - timedelta(days=days_ago, seconds=random.randint(0, 86400))
        ended_at = started_at + timedelta(seconds=duration_sec)

        start_station = random.randint(1, 20)
        end_station = random.randint(1, 20)

        rows.append((
            i,
            random.randint(1, 200),   # rider_id
            random.randint(1, 150),   # bike_id
            start_station,
            end_station,
            started_at.strftime("%Y-%m-%d %H:%M:%S"),
            ended_at.strftime("%Y-%m-%d %H:%M:%S"),
            duration_sec,
        ))
    cursor.executemany(
        """INSERT INTO trips
           (trip_id, rider_id, bike_id, start_station, end_station,
            started_at, ended_at, duration_sec)
           VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    return len(rows)

def seed(db_path: Path = DB_PATH):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Drop all tables and recreate — idempotent on every run
        for statement in _DROP_TABLES.strip().split(";"): 
            statement = statement.strip() # is this double strip necessary??
            if statement:
                cursor.execute(statement)

        cursor.execute(_CREATE_STATIONS)
        cursor.execute(_CREATE_RIDERS)
        cursor.execute(_CREATE_BIKES)
        cursor.execute(_CREATE_TRIPS)

        n_stations = _seed_stations(cursor)
        n_riders   = _seed_riders(cursor)
        n_bikes    = _seed_bikes(cursor)
        n_trips    = _seed_trips(cursor)

        conn.commit()

    print(f"Seeded {db_path.name}: {n_stations} stations, {n_riders} riders, {n_bikes} bikes, {n_trips} trips")


if __name__ == "__main__":
    random.seed(42)  # fixed seed for reproducible expected output
    seed()
