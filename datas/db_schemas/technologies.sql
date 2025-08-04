CREATE TABLE IF NOT EXISTS CountryTechnologies (
    country_id INTEGER NOT NULL,
    tech_field TEXT NOT NULL CHECK (
        tech_field IN (
            'Armement',
            'Mécanique Terrestre',
            'Aéronaval',
            'Industrie & Ingénierie',
            'Culture & Connaissance',
            'Santé & Sciences',
            'Survie & Agronomie',
            'TIC & Sciences'
        )
    ),
    level INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (country_id, tech_field),
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS StructureProduction (
    structure_id INTEGER NOT NULL,
    tech_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    days_remaining INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (structure_id, tech_id),
    FOREIGN KEY (structure_id) REFERENCES Structures(id) ON DELETE CASCADE,
    FOREIGN KEY (tech_id) REFERENCES Technologies(tech_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Technologies (
    tech_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cost INTEGER NOT NULL DEFAULT 0,
    specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')),
    development_time INTEGER NOT NULL DEFAULT 0, -- Durée de développement en jours
    development_cost INTEGER NOT NULL DEFAULT 0, -- Coût de développement en argent
    slots_taken FLOAT NOT NULL DEFAULT 1.0, -- Nombre de slots occupés par cette technologie   
    original_name TEXT NOT NULL,
    technology_level INTEGER NOT NULL DEFAULT 1 CHECK (technology_level >= 1 AND technology_level <= 11),
    image_url TEXT,
    developed_by INTEGER,
    exported BOOLEAN DEFAULT FALSE,
    is_secret BOOLEAN DEFAULT FALSE,
    type TEXT NOT NULL, -- 'rifle', 'ship', 'engine', etc.
    difficulty_rating INTEGER DEFAULT 1 CHECK (difficulty_rating >= 1 AND difficulty_rating <= 10), -- Échelle de difficulté de 1 à 10
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (developed_by) REFERENCES Countries(country_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS TechnologyAttributes (
    tech_id INTEGER NOT NULL,
    attribute_name TEXT NOT NULL,
    attribute_value TEXT NOT NULL,
    FOREIGN KEY (tech_id) REFERENCES Technologies(tech_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS TechnologyLicenses (
    license_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tech_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL, -- Pays qui détient la licence
    license_type TEXT NOT NULL CHECK(license_type IN ('commercial', 'personal')),
    granted_by INTEGER, -- Pays ayant accordé la licence
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tech_id) REFERENCES Technologies(tech_id) ON DELETE CASCADE,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES Countries(country_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS CountryTechnologyInventory (
    country_id INTEGER NOT NULL,
    tech_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0 NOT NULL,
    PRIMARY KEY (country_id, tech_id),
    FOREIGN KEY (country_id) REFERENCES Countries(country_id) ON DELETE CASCADE,
    FOREIGN KEY (tech_id) REFERENCES Technologies(tech_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS CountryTechnologyProduction (
    production_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER NOT NULL,
    tech_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    days_remaining INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id) ON DELETE CASCADE,
    FOREIGN KEY (tech_id) REFERENCES Technologies(tech_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS TechnologyDatas (
    type TEXT NOT NULL PRIMARY KEY,
    specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')),
    minimum_slots_taken FLOAT NOT NULL DEFAULT 1.0, -- Nombre de slots occupés par cette technologie
    maximum_slots_taken FLOAT NOT NULL DEFAULT 1.0, -- Nombre maximum de slots occupés par cette technologie
    minimum_dev_cost INTEGER NOT NULL DEFAULT 0, -- Coût minimum de développement
    minimum_dev_time INTEGER NOT NULL DEFAULT 0, -- Durée minimum de développement en jours
    minimum_prod_cost INTEGER NOT NULL DEFAULT 0, -- Coût minimum de production
    maximum_dev_cost INTEGER NOT NULL DEFAULT 0, -- Coût maximum de développement
    maximum_dev_time INTEGER NOT NULL DEFAULT 0, -- Durée maximum de développement en jours
    maximum_prod_cost INTEGER NOT NULL DEFAULT 0 -- Coût maximum de production
);

CREATE TABLE IF NOT EXISTS TechnologyRatios (
    type TEXT NOT NULL,
    level INTEGER NOT NULL,  -- Niveau de la technologie
    ratio_cost INTEGER NOT NULL,  -- Ratio de coût
    ratio_time INTEGER NOT NULL,  -- Ratio de temps de développement
    ratio_slots FLOAT NOT NULL,  -- Ratio de slots occupés
    PRIMARY KEY (type, level)
);