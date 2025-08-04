-- Table des structures
CREATE TABLE IF NOT EXISTS Structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('Usine', 'Base', 'Ecole', 'Logement', 'Centrale', 'Technocentre')),
    specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')),
    level INTEGER NOT NULL DEFAULT 1,
    capacity INTEGER DEFAULT 0 NOT NULL,  -- Capacité utile pour les logements/ecoles/bases
    population INTEGER DEFAULT 0 NOT NULL,  -- nb personnes affectées pour logements, bases, écoles, usines
    FOREIGN KEY (region_id) REFERENCES Regions(region_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS StructuresDatas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('Usine', 'Base', 'Ecole', 'Logement', 'Centrale', 'Technocentre')),
    specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')),
    capacity INTEGER DEFAULT 0 NOT NULL,  -- Capacité utile pour les logements/ecoles/bases
    population INTEGER DEFAULT 0 NOT NULL,  -- nb personnes affectées pour logements, bases
    cout_construction INTEGER NOT NULL,  -- Coût de construction de la structure
    UNIQUE(type, specialisation)
);

CREATE TABLE IF NOT EXISTS StructuresRatios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('Usine', 'Base', 'Ecole', 'Logement', 'Centrale', 'Technocentre')),
    level INTEGER NOT NULL,  -- Niveau de la structure
    ratio_production INTEGER NOT NULL,  -- Ratio de production ou d'efficacité
    ratio_cost INTEGER NOT NULL,  -- Ratio de coût
    UNIQUE(type, level)
);