-- ==============================================================================
-- Schéma de base de données SQLite - Amazon Scraper Pro
-- ==============================================================================

-- 1. Table principale des produits
CREATE TABLE IF NOT EXISTS produits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nom           TEXT NOT NULL,
    prix          REAL NOT NULL,
    note          REAL NOT NULL DEFAULT 0.0,
    disponibilite INTEGER NOT NULL DEFAULT 1 CHECK (disponibilite IN (0, 1)),
    url           TEXT NOT NULL UNIQUE,
    image         TEXT,
    categorie     TEXT,
    date_scrape   TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime'))
);

-- 2. Index pour optimiser les filtres et les tris
CREATE INDEX IF NOT EXISTS idx_produits_categorie ON produits (categorie);
CREATE INDEX IF NOT EXISTS idx_produits_prix ON produits (prix);
CREATE INDEX IF NOT EXISTS idx_produits_note ON produits (note);
CREATE INDEX IF NOT EXISTS idx_produits_date ON produits (date_scrape);
