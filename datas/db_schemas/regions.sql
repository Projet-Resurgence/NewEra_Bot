-- Table des régions
CREATE TABLE IF NOT EXISTS Regions (
    region_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Identifiant unique de la région
    country_id INTEGER NULL,                        -- Pour rattacher la région à un pays
    name TEXT NOT NULL,                          -- Nom de la région
    mapchart_name TEXT NOT NULL,                 -- Nom associé à MapChart
    population INTEGER DEFAULT 0 NOT NULL,       -- Population de la région
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);