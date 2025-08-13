-- New structures schema with explicit values instead of ratios
-- This replaces the old structures.sql schema

-- Main structures table (unchanged)
CREATE TABLE IF NOT EXISTS Structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('Usine', 'Base', 'Ecole', 'Logement', 'Technocentre')),
    specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')),
    level INTEGER NOT NULL DEFAULT 1,
    capacity INTEGER DEFAULT 0 NOT NULL,  -- Capacité utile pour les logements/ecoles/bases
    population INTEGER DEFAULT 0 NOT NULL,  -- nb personnes affectées pour logements, bases, écoles, usines
    FOREIGN KEY (region_id) REFERENCES Regions(region_id)
        ON DELETE CASCADE
);

-- New table with explicit values for each structure type/specialisation/level
CREATE TABLE IF NOT EXISTS StructuresDatas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('Usine', 'Base', 'Ecole', 'Logement', 'Technocentre')),
    specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')),
    level INTEGER NOT NULL,
    capacity INTEGER DEFAULT 0 NOT NULL,  -- Production capacity or housing capacity
    population INTEGER DEFAULT 0 NOT NULL,  -- Required employees/population
    cout_construction INTEGER NOT NULL,  -- Construction cost
    UNIQUE(type, specialisation, level)
);

-- Technology level boost coefficients for production
CREATE TABLE IF NOT EXISTS TechnologyBoosts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tech_level INTEGER NOT NULL UNIQUE,
    boost_coefficient REAL NOT NULL DEFAULT 1.0
);

-- Infrastructure table (no levels, no specialisation)
CREATE TABLE IF NOT EXISTS Infrastructure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL,
    type TEXT NOT NULL,  -- Route sommaire, Route, Autoroute, etc.
    length_km REAL NOT NULL DEFAULT 0,  -- Length in kilometers
    cost_per_km INTEGER NOT NULL,  -- Cost per kilometer
    total_cost INTEGER NOT NULL,  -- Total construction cost
    FOREIGN KEY (region_id) REFERENCES Regions(region_id)
        ON DELETE CASCADE
);

-- Infrastructure types and costs
CREATE TABLE IF NOT EXISTS InfrastructureTypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL UNIQUE,
    cost_per_km INTEGER NOT NULL
);

-- Actual power plants table (instances owned by countries)
CREATE TABLE IF NOT EXISTS PowerPlants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    level INTEGER NOT NULL,
    built_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES Regions(region_id)
        ON DELETE CASCADE
);

-- Power plants data with specific values
CREATE TABLE IF NOT EXISTS PowerPlantsDatas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,  -- éolien onshore, éolien offshore, Solaire, etc.
    level INTEGER NOT NULL,
    production_mwh INTEGER NOT NULL,  -- Production in MW/H per year
    construction_cost INTEGER NOT NULL,
    danger_rate REAL DEFAULT 0,  -- Danger percentage
    resource_type TEXT,  -- Uranium, etc.
    resource_consumption REAL DEFAULT 0,  -- Consumption per year
    price_per_mwh REAL NOT NULL,
    UNIQUE(type, level)
);

-- Housing data with style, density, and quality multipliers
CREATE TABLE IF NOT EXISTS HousingDatas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    density_type TEXT NOT NULL,  -- Très Basse, Basse, Moyenne, etc.
    density_multiplier REAL NOT NULL,
    style_type TEXT NOT NULL,  -- Archaique, Traditionelle, etc.
    style_multiplier REAL NOT NULL,
    quality_type TEXT NOT NULL,  -- Très bonne qualité, etc.
    quality_multiplier REAL NOT NULL,
    base_cost_per_person INTEGER NOT NULL
);

-- Remove the old StructuresRatios table as it's no longer needed
DROP TABLE IF EXISTS StructuresRatios;
