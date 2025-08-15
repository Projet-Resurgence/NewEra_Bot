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
    -- Tech levels are stored per-domain in CountryTechnologies (Terrestre, Aerienne, Navale, Global)
    -- The view should not assume a single tech_level column in Stats (it doesn't exist).
    -- Consumers should query CountryTechnologies for domain-specific levels.
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

CREATE VIEW IF NOT EXISTS CountryProductionView AS
SELECT
    p.country_id,
    c.name AS country_name,
    t.name AS technology_name,
    p.quantity,
    p.months_remaining,
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
    sd.capacity AS effective_capacity,  -- Use the direct capacity value from StructuresDatas
    -- Use the country/domain-specific technology level when computing production slot usage.
    -- Prefer a technology level matching the technology's specialisation (e.g. 'Terrestre'),
    -- else fall back to the country's 'Global' tech level, else default to 1.
    SUM(
        t.slots_taken * (1 + (COALESCE(ct.level, 1) / 10.0)) * sp.quantity
    ) AS used_capacity
FROM StructureProduction sp
JOIN Structures s ON sp.structure_id = s.id
JOIN StructuresDatas sd ON s.type = sd.type AND s.specialisation = sd.specialisation AND s.level = sd.level
JOIN Technologies t ON sp.tech_id = t.tech_id
-- join country tech levels for the owning country of the structure
LEFT JOIN Regions r ON s.region_id = r.region_id
LEFT JOIN CountryTechnologies ct ON ct.country_id = r.country_id AND ct.tech_field = t.specialisation
LEFT JOIN CountryTechnologies cg ON cg.country_id = r.country_id AND cg.tech_field = 'Global'
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