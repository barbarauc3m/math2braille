PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documento (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_archivo          TEXT    NOT NULL,
    ruta_archivo            TEXT    NOT NULL,
    num_paginas             INTEGER NOT NULL,
    fecha_carga             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_apertura   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS formula (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id        INTEGER NOT NULL,
    pagina              INTEGER NOT NULL,
    x                   REAL    NOT NULL,
    y                   REAL    NOT NULL,
    ancho               REAL    NOT NULL,
    alto                REAL    NOT NULL,
    confidence_score    REAL    NOT NULL,
    mathml              TEXT,
    fecha_procesado     DATETIME,
    FOREIGN KEY (documento_id) REFERENCES documento(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_formula_documento_id ON formula(documento_id);