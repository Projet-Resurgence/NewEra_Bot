-- Table de l’inventaire
CREATE TABLE IF NOT EXISTS Inventory (
    country_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0 NOT NULL,
    pol_points INTEGER DEFAULT 0 NOT NULL,
    diplo_points INTEGER DEFAULT 0 NOT NULL,
    tech_points INTEGER DEFAULT 0 NOT NULL,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS InventoryUnits (
    country_id INTEGER NOT NULL,
    unit_type TEXT NOT NULL,
    quantity INTEGER DEFAULT 0 NOT NULL,
    PRIMARY KEY (country_id, unit_type)
);

CREATE TABLE IF NOT EXISTS InventoryPricings (
    item TEXT NOT NULL PRIMARY KEY,
    price INTEGER NOT NULL,
    maintenance INTEGER NOT NULL
);