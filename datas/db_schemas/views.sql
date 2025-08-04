-- VIEW : Population totale par pays
CREATE VIEW IF NOT EXISTS PopulationView AS
SELECT
    country_id,
    SUM(population) AS population
FROM Regions
GROUP BY country_id;

CREATE VIEW IF NOT EXISTS CountryNumberOfRegions AS
SELECT
    country_id,
    COUNT(region_id) AS number_of_regions
FROM Regions
GROUP BY country_id;

-- VIEW : Capacité d’accueil par pays
CREATE VIEW IF NOT EXISTS PopulationCapacityView AS
SELECT
    r.country_id,
    SUM(s.capacity) AS population_capacity
FROM Structures s
JOIN Regions r ON s.region_id = r.region_id
WHERE s.type IN ('Logement')  -- tu peux changer selon le gameplay
GROUP BY r.country_id;

-- VIEW : Vue globale des stats
CREATE VIEW IF NOT EXISTS StatsView AS
SELECT
    c.country_id,
    c.name,
    IFNULL(p.population, 0) AS population,
    IFNULL(pc.population_capacity, 0) AS population_capacity,
    IFNULL(s.tech_level, 1) AS tech_level,
    IFNULL(s.gdp, 0) AS gdp
FROM Countries c
LEFT JOIN Stats s ON c.country_id = s.country_id
LEFT JOIN PopulationView p ON c.country_id = p.country_id
LEFT JOIN PopulationCapacityView pc ON c.country_id = pc.country_id;

CREATE VIEW IF NOT EXISTS CountryStructuresView AS
SELECT
    c.country_id,
    c.name AS country_name,
    r.region_id,
    r.name AS region_name,
    s.id AS structure_id,
    s.type,
    s.specialisation,
    s.level,
    s.capacity,
    s.population
FROM Structures s
JOIN Regions r ON s.region_id = r.region_id
JOIN Countries c ON r.country_id = c.country_id;

CREATE VIEW IF NOT EXISTS CrossTechLevelsView AS
SELECT country_id, 'Armes improvisées' AS tech_name,
    MIN(level) AS level
FROM CountryTechnologies
WHERE tech_field IN ('Survie & Agronomie', 'Armement')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Armes à feu lourdes',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Industrie & Ingénierie', 'Armement')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Véhicules terrestres armés/blindés',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Mécanique Terrestre', 'Armement')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Véhicules terrestres lourds armés/blindés',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Mécanique Terrestre', 'Armement', 'Industrie & Ingénierie')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Véhicules aéronavals armés',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Aéronaval', 'Armement')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Moteurs à Réaction',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Industrie & Ingénierie', 'TIC & Sciences')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Armes Explosives, Biologiques et Chimiques',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Santé & Sciences', 'Armement')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Nucléaire',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Santé & Sciences', 'Industrie & Ingénierie', 'TIC & Sciences')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Cyber-Armes',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('TIC & Sciences', 'Armement')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Géologie',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Industrie & Ingénierie', 'Survie & Agronomie')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Logistique',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Mécanique Terrestre', 'Aéronaval', 'Industrie & Ingénierie')
GROUP BY country_id

UNION ALL

SELECT country_id, 'Spatial',
    MIN(level)
FROM CountryTechnologies
WHERE tech_field IN ('Aéronaval', 'Industrie & Ingénierie', 'TIC & Sciences')
GROUP BY country_id;

CREATE VIEW IF NOT EXISTS CountryProductionView AS
SELECT
    p.country_id,
    c.name AS country_name,
    t.name AS technology_name,
    p.quantity,
    p.days_remaining,
    p.started_at
FROM CountryTechnologyProduction p
JOIN Countries c ON p.country_id = c.country_id
JOIN Technologies t ON p.tech_id = t.tech_id;

CREATE VIEW IF NOT EXISTS StructureProductionView AS
SELECT
    sp.structure_id,
    r.region_id,
    r.name AS region_name,
    s.specialisation,
    s.level,
    sd.capacity AS base_capacity,
    sr.ratio_production,
    sd.capacity * sr.ratio_production AS effective_capacity,
    SUM(
        t.slots_taken * (1 + (t.technology_level / 10.0)) * sp.quantity
    ) AS used_capacity
FROM StructureProduction sp
JOIN Structures s ON sp.structure_id = s.id
JOIN StructuresDatas sd ON s.type = sd.type
JOIN StructuresRatios sr ON sr.type = s.type AND sr.level = s.level
JOIN Technologies t ON sp.tech_id = t.tech_id
JOIN Regions r ON s.region_id = r.region_id
GROUP BY sp.structure_id;

CREATE VIEW IF NOT EXISTS StructureFreeCapacityView AS
SELECT
    spv.structure_id,
    spv.region_id,
    spv.region_name,
    spv.effective_capacity,
    COALESCE(spv.used_capacity, 0) AS used_capacity,
    spv.effective_capacity - COALESCE(spv.used_capacity, 0) AS remaining_capacity
FROM StructureProductionView spv;