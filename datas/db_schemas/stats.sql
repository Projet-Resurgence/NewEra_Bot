-- Table des stats fixes
CREATE TABLE IF NOT EXISTS Stats (
    country_id INTEGER PRIMARY KEY,
    gdp INTEGER DEFAULT 0 NOT NULL,
    FOREIGN KEY (country_id) REFERENCES Countries(country_id)
        ON DELETE CASCADE
);
