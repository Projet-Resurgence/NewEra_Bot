-- Table des pays
CREATE TABLE IF NOT EXISTS Countries (
    country_id INTEGER PRIMARY KEY AUTOINCREMENT,   -- Identifiant unique du pays
    role_id    TEXT NOT NULL,                       -- ID du rôle Discord associé
    name TEXT NOT NULL,                             -- Nom du pays
    public_channel_id TEXT NOT NULL,                -- ID du salon public (NON NULLABLE)
    secret_channel_id TEXT,                         -- ID du salon secret (NULLABLE)
    last_bilan TEXT DEFAULT NULL                    -- Dernier bilan du pays (NULLABLE)
);

-- Table des gouvernements
CREATE TABLE IF NOT EXISTS Governments (
    country_id INTEGER NOT NULL,
    slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 5),
    player_id TEXT NOT NULL,  -- ID du joueur occupant ce poste
    can_spend_money BOOLEAN DEFAULT FALSE,
    can_spend_points BOOLEAN DEFAULT FALSE,
    can_sign_treaties BOOLEAN DEFAULT FALSE,
    can_build BOOLEAN DEFAULT FALSE,
    can_recruit BOOLEAN DEFAULT FALSE,
    can_produce BOOLEAN DEFAULT FALSE,
    can_declare_war BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (country_id, slot),
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Doctrines (
    doctrine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT CHECK (category IN ('Ideologie', 'Economie')),
    description TEXT,
    discord_role_id TEXT,
    bonus_json JSONB  -- exemple : { "production_bonus": 0.1, "culture_penalty": -0.05 }
);

CREATE TABLE IF NOT EXISTS CountryDoctrines (
    country_id INTEGER NOT NULL,
    doctrine_id INTEGER NOT NULL,
    PRIMARY KEY (country_id, doctrine_id),
    FOREIGN KEY (country_id) REFERENCES Countries(country_id) ON DELETE CASCADE,
    FOREIGN KEY (doctrine_id) REFERENCES Doctrines(doctrine_id)
);