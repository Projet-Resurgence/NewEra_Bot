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

-- Table des dettes/emprunts
CREATE TABLE IF NOT EXISTS Debts (
    debt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    debt_reference TEXT NOT NULL UNIQUE,
    country_id INTEGER NOT NULL,
    original_amount INTEGER NOT NULL,
    remaining_amount INTEGER NOT NULL,
    interest_rate REAL NOT NULL,
    max_years INTEGER NOT NULL CHECK (max_years BETWEEN 1 AND 10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);