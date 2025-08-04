CREATE TABLE IF NOT EXISTS Dates (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    playday INTEGER NOT NULL CHECK (playday >= 1),
    real_date DATE NOT NULL,
    PRIMARY KEY (year, month, playday)
);

CREATE TABLE IF NOT EXISTS PlaydaysPerMonth (
    month_number SMALLINT PRIMARY KEY CHECK (month_number BETWEEN 1 AND 12),
    playdays INTEGER NOT NULL DEFAULT 1 CHECK (playdays >= 0)
);