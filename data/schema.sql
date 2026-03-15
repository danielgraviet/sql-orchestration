-- stations: docking stations across the city
CREATE TABLE stations (
    station_id  INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    capacity    INTEGER NOT NULL  -- number of bike docks
);

-- riders: registered members
CREATE TABLE riders (
    rider_id     INTEGER PRIMARY KEY,
    member_since DATE    NOT NULL,
    plan         TEXT    NOT NULL  -- 'monthly', 'annual', 'day-pass'
);

-- bikes: individual bikes in the fleet
CREATE TABLE bikes (
    bike_id   INTEGER PRIMARY KEY,
    type      TEXT    NOT NULL,  -- 'classic', 'electric'
    acquired  DATE    NOT NULL
);

-- trips: one row per completed ride
CREATE TABLE trips (
    trip_id       INTEGER PRIMARY KEY,
    rider_id      INTEGER  NOT NULL REFERENCES riders(rider_id),
    bike_id       INTEGER  NOT NULL REFERENCES bikes(bike_id),
    start_station INTEGER  NOT NULL REFERENCES stations(station_id),
    end_station   INTEGER  NOT NULL REFERENCES stations(station_id),
    started_at    DATETIME NOT NULL,
    ended_at      DATETIME NOT NULL,
    duration_sec  INTEGER  NOT NULL  -- ended_at - started_at in seconds
);
