-- Table des régions
CREATE TABLE IF NOT EXISTS Regions (
    region_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Identifiant unique de la région
    country_id INTEGER NULL,                        -- Pour rattacher la région à un pays
    name TEXT NOT NULL,                          -- Nom de la région
    region_color_hex VARCHAR(8) NOT NULL UNIQUE,                 -- Couleur sur la map custom à parser
    population INTEGER DEFAULT 0 NOT NULL,       -- Population de la région
    continent VARCHAR(15) CHECK (continent IN ('Europe', 'Asie', 'Afrique', 'Amerique', 'Oceanie', 'Moyen-Orient')),
    geographical_area_id INTEGER,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE,
    FOREIGN KEY (geographical_area_id) REFERENCES GeographicalAreas(geographical_area_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS GeographicalAreas (
    geographical_area_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Identifiant unique de la zone géographique
    name TEXT UNIQUE NOT NULL                                      -- Nom de la zone géographique
);
