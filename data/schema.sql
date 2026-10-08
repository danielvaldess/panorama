-- schema.sql — almacenamiento operativo de Panorama (SQLite, WAL).
-- Contrato de datos del reto: los CSV/JSONL/GeoJSON de data/raw/* siguen siendo
-- el snapshot congelado; esta base es el estado operativo (decisiones, caché,
-- clasificaciones, eventos) reconstruible desde el snapshot.
--
-- Convenciones:
--   * Fechas en ISO 8601 UTC (TEXT). La conversión a hora de Panamá es solo de la UI.
--   * Nulos conservados (nunca se rellenan con 0).
--   * noticias.url es UNIQUE: el poller hace dedup vía INSERT OR IGNORE.

CREATE TABLE IF NOT EXISTS fuentes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL,
    url            TEXT,
    tipo           TEXT,
    confiabilidad  INTEGER,
    licencia       TEXT,
    UNIQUE (nombre, url)
);

CREATE TABLE IF NOT EXISTS noticias (
    id_noticia        TEXT PRIMARY KEY,
    titulo            TEXT NOT NULL,
    url               TEXT NOT NULL UNIQUE,
    medio             TEXT,
    idioma            TEXT,
    fecha_publicacion TEXT,
    fecha_deteccion   TEXT,
    fecha_extraccion  TEXT,
    tema              TEXT,
    origen            TEXT,
    alcance_texto     TEXT,
    descripcion       TEXT
);

CREATE TABLE IF NOT EXISTS clasificaciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    noticia_url     TEXT NOT NULL UNIQUE,
    tema            TEXT,
    confianza       REAL,
    candidatos      TEXT,           -- JSON (lista de {tema, score})
    metodo          TEXT,           -- 'regla' | 'embedding'
    fuera_de_alcance INTEGER,       -- 0/1
    sensible        INTEGER,        -- 0/1
    ts              TEXT NOT NULL,
    FOREIGN KEY (noticia_url) REFERENCES noticias(url)
);

CREATE TABLE IF NOT EXISTS grupos_evento (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    representante_titulo TEXT,
    ts                  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grupo_noticias (
    grupo_id    INTEGER NOT NULL,
    noticia_url TEXT NOT NULL,
    PRIMARY KEY (grupo_id, noticia_url),
    FOREIGN KEY (grupo_id) REFERENCES grupos_evento(id),
    FOREIGN KEY (noticia_url) REFERENCES noticias(url)
);

CREATE TABLE IF NOT EXISTS indicadores (
    pais_iso3        TEXT NOT NULL,
    indicador_id     TEXT NOT NULL,
    anio             TEXT NOT NULL,
    valor            TEXT,          -- NULL conservado (no 0); texto original para round-trip
    unidad           TEXT,
    fuente_url       TEXT,
    fecha_extraccion TEXT,
    licencia         TEXT,
    PRIMARY KEY (pais_iso3, indicador_id, anio)
);

CREATE TABLE IF NOT EXISTS eventos_sismicos (
    id           TEXT PRIMARY KEY,
    mag          REAL,
    place        TEXT,
    time_ms      INTEGER,
    url          TEXT,
    lat          REAL,
    lon          REAL,
    depth        REAL,
    feature_json TEXT              -- serialización canónica sin pérdida
);

CREATE TABLE IF NOT EXISTS fichas (
    id_caso          TEXT PRIMARY KEY,
    titulo           TEXT,
    tema             TEXT,
    puntaje          INTEGER,
    componentes      TEXT,         -- JSON
    estado_evidencia TEXT,
    ts               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS borradores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ficha_id    TEXT,
    modelo      TEXT,
    version     TEXT,
    prompt_hash TEXT,
    tokens      INTEGER,
    costo       REAL,
    latencia    REAL,
    contenido   TEXT,              -- JSON (titulo/brief/guion/copy/preguntas)
    ts          TEXT NOT NULL,
    FOREIGN KEY (ficha_id) REFERENCES fichas(id_caso)
);

-- decisiones: SOLO INSERT (append-only). Los triggers impiden UPDATE y DELETE.
CREATE TABLE IF NOT EXISTS decisiones (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo     TEXT NOT NULL,        -- 'revision' | 'veredicto'
    nombre   TEXT,                 -- reviewer (validado, longitud máxima)
    nota     TEXT,                 -- nota/comentario (validado, longitud máxima)
    fecha    TEXT NOT NULL,        -- ISO 8601 UTC
    ficha_id TEXT,
    payload  TEXT                  -- JSON (registro original completo)
);

CREATE TRIGGER IF NOT EXISTS decisiones_no_update
BEFORE UPDATE ON decisiones
BEGIN
    SELECT RAISE(ABORT, 'decisiones es append-only (SOLO INSERT)');
END;

CREATE TRIGGER IF NOT EXISTS decisiones_no_delete
BEFORE DELETE ON decisiones
BEGIN
    SELECT RAISE(ABORT, 'decisiones es append-only (SOLO INSERT)');
END;

CREATE TABLE IF NOT EXISTS cache_llm (
    clave  TEXT PRIMARY KEY,
    salida TEXT NOT NULL,          -- JSON
    modelo TEXT,
    ts     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT,
    rules_version   TEXT,
    fecha_corte_UTC TEXT,
    manifest_json   TEXT,          -- manifest completo (para regenerar manifest.json)
    eventos_json    TEXT,          -- texto canónico de eventos.geojson (round-trip sin pérdida)
    ts              TEXT NOT NULL
);
