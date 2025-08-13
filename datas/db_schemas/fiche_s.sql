CREATE TABLE IF NOT EXISTS Personne (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_commun VARCHAR(100) NOT NULL,
    raison TEXT,
    gravite TINYINT CHECK (gravite BETWEEN 1 AND 3)
);

CREATE TABLE IF NOT EXISTS Compte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_discord BIGINT NOT NULL UNIQUE,
    username VARCHAR(100),
    id_personne INT,
    FOREIGN KEY (id_personne) REFERENCES Personne(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Sanctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('ban', 'mute')),
    id_personne INT,
    raison TEXT,
    FOREIGN KEY (id_personne) REFERENCES Personne(id) ON DELETE CASCADE
);
