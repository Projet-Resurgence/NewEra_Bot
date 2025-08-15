-- Table des régions
CREATE TABLE IF NOT EXISTS Regions (
    region_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Identifiant unique de la région
    country_id INTEGER NULL,                        -- Pour rattacher la région à un pays
    name TEXT NOT NULL,                          -- Nom de la région
    region_color_hex VARCHAR(8) NOT NULL,                 -- Couleur sur la map custom à parser
    population INTEGER DEFAULT 0 NOT NULL,       -- Population de la région
    area INTEGER DEFAULT 0 NOT NULL,             -- Superficie de la région
    geographical_area_id INTEGER,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
    FOREIGN KEY (geographical_area_id) REFERENCES GeographicalAreas(geographical_area_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS GeographicalAreas (
    geographical_area_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Identifiant unique de la zone géographique
    name TEXT NOT NULL,                                      -- Nom de la zone géographique
    delimitation_x_start INTEGER NOT NULL,         -- Délimitation de la zone géographique en X (début)
    delimitation_x_end INTEGER NOT NULL,           -- Délimitation de la zone géographique en X (fin)
    delimitation_y_start INTEGER NOT NULL,         -- Délimitation de la zone géographique en Y (début)
    delimitation_y_end INTEGER NOT NULL            -- Délimitation de la zone géographique en Y (fin)
);