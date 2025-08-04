-- I will create a SQL schema for a diplomacy database that includes tables:
-- 1. `treaties` to store about specific types of treaties such as non-agression pacts, free trade agreements, research pacts, peace agreements, and more.
-- 2. `alliances` to manage alliances between different countries or factions.
-- 3. `war_declarations` to record instances of war declarations between countries or factions.
CREATE TABLE IF NOT EXISTS Treaties (
    treaty_id INTEGER PRIMARY KEY AUTOINCREMENT,
    treaty_type VARCHAR(50) NOT NULL,
    country_a INTEGER NOT NULL,
    country_b INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'expired', 'terminated')),
    is_public BOOLEAN NOT NULL DEFAULT 1, -- Indique si la déclaration de guerre est publique
    message_url TEXT, -- URL pour le message de la déclaration de guerre
    UNIQUE (country_a, country_b, treaty_type, start_date),
    FOREIGN KEY (country_a) REFERENCES Countries(country_id),
    FOREIGN KEY (country_b) REFERENCES Countries(country_id)
);

CREATE TABLE IF NOT EXISTS Alliances (
    alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alliance_name VARCHAR(100) NOT NULL,
    country_a INTEGER NOT NULL,
    country_b INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    alliance_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'expired', 'terminated')),
    message_url TEXT, -- URL pour le message de l'alliance
    is_public BOOLEAN NOT NULL DEFAULT 1, -- Indique si la déclaration de guerre est publique
    UNIQUE (country_a, country_b, alliance_name, start_date),
    FOREIGN KEY (country_a) REFERENCES Countries(country_id),
    FOREIGN KEY (country_b) REFERENCES Countries(country_id)
);

CREATE TABLE IF NOT EXISTS AlliancesAppartenance (
    alliance_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL,
    PRIMARY KEY (alliance_id, country_id),
    FOREIGN KEY (alliance_id) REFERENCES Alliances(alliance_id)
        ON DELETE CASCADE,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS WarDeclarations (
    war_declaration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_a INTEGER NOT NULL,
    country_b INTEGER NOT NULL,
    declaration_date DATE NOT NULL,
    message_url TEXT, -- URL pour le message de la déclaration de guerre
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'resolved', 'terminated')),
    UNIQUE (country_a, country_b, declaration_date),
    FOREIGN KEY (country_a) REFERENCES Countries(country_id),
    FOREIGN KEY (country_b) REFERENCES Countries(country_id)
);