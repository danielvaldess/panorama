"""Capa de repositorio (SQLite, WAL).

Almacenamiento operativo de Panorama: decisiones humanas, caché del LLM, estado
de temas/clasificaciones, noticias, indicadores, eventos y snapshots. El snapshot
congelado (data/raw/*) sigue siendo el contrato de datos; esta base se reconstruye
desde él cuando no existe (ver `ensure_ready` y `pipeline.snapshot_io`).

Ruta configurable por variable de entorno `PANORAMA_DB` (por defecto
`data/panorama.db`). Para tests se usa `:memory:`.

Todas las consultas son parametrizadas (sin concatenar SQL).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SCHEMA_PATH = os.path.join(DATA, "schema.sql")
DEFAULT_DB = os.path.join(DATA, "panorama.db")

NOMBRE_MAX = 120
NOTA_MAX = 2000

_conn: sqlite3.Connection | None = None
_lock = threading.RLock()


def default_path() -> str:
    return os.environ.get("PANORAMA_DB") or DEFAULT_DB


def _read_schema() -> str:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return fh.read()


def connect(path: str | None = None) -> sqlite3.Connection:
    """Abre una conexión SQLite con WAL, claves foráneas y busy_timeout."""
    p = path or default_path()
    conn = sqlite3.connect(p, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(_read_schema())


def ensure_ready(path: str | None = None) -> sqlite3.Connection:
    """Devuelve la conexión compartida, creando el esquema si hace falta."""
    global _conn
    with _lock:
        if _conn is None:
            _conn = connect(path)
            init(_conn)
        return _conn


def connection() -> sqlite3.Connection | None:
    """Conexión compartida ya inicializada, o None (permite degradar con elegancia)."""
    return _conn


def reset() -> None:
    """Cierra y olvida la conexión compartida (para tests)."""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None


@contextmanager
def transaction(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _txt(value, maxlen: int) -> str | None:
    """Normaliza texto de entrada: recorta espacios, control chars y longitud máxima."""
    if value is None:
        return None
    s = " ".join(str(value).split())
    if not s:
        return None
    return s[:maxlen]


# --- fuentes ---

def insert_fuentes(conn: sqlite3.Connection, rows: list[dict]) -> int:
    n = 0
    for r in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO fuentes (nombre, url, tipo, confiabilidad, licencia) "
            "VALUES (?, ?, ?, ?, ?)",
            (_txt(r.get("nombre"), 200), _txt(r.get("url"), 2000), _txt(r.get("tipo"), 50),
             r.get("confiabilidad"), _txt(r.get("licencia"), 500)),
        )
        n += cur.rowcount
    return n


def list_fuentes(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM fuentes ORDER BY id")]


# --- noticias ---

_NOTICIA_FIELDS = ["id_noticia", "titulo", "url", "medio", "idioma",
                   "fecha_publicacion", "fecha_deteccion", "fecha_extraccion",
                   "tema", "origen", "alcance_texto", "descripcion"]
_DATE_FIELDS = {"fecha_publicacion", "fecha_deteccion", "fecha_extraccion"}


def insert_noticias(conn: sqlite3.Connection, items: list[dict]) -> list[str]:
    """INSERT OR IGNORE (dedup por UNIQUE(url)). Devuelve las URLs nuevas."""
    new: list[str] = []
    for it in items:
        row = {}
        for f in _NOTICIA_FIELDS:
            v = it.get(f, "")
            row[f] = None if (f in _DATE_FIELDS and v in ("", None)) else v
        cur = conn.execute(
            "INSERT OR IGNORE INTO noticias (id_noticia, titulo, url, medio, idioma, "
            "fecha_publicacion, fecha_deteccion, fecha_extraccion, tema, origen, "
            "alcance_texto, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["id_noticia"], row["titulo"], row["url"], row["medio"], row["idioma"],
             row["fecha_publicacion"], row["fecha_deteccion"], row["fecha_extraccion"],
             row["tema"], row["origen"], row["alcance_texto"], row["descripcion"]),
        )
        if cur.rowcount:
            new.append(it.get("url"))
    return new


def get_noticias(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id_noticia, titulo, url, medio, idioma, fecha_publicacion, "
        "fecha_deteccion, fecha_extraccion, tema, origen, alcance_texto, descripcion "
        "FROM noticias ORDER BY rowid")]


# --- clasificaciones ---

def upsert_clasificacion(conn: sqlite3.Connection, url: str, tema: str | None,
                         confianza: float | None, candidatos: list[dict] | None,
                         metodo: str | None, fuera_de_alcance: bool, sensible: bool) -> None:
    conn.execute(
        "INSERT INTO clasificaciones (noticia_url, tema, confianza, candidatos, metodo, "
        "fuera_de_alcance, sensible, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(noticia_url) DO UPDATE SET tema=excluded.tema, "
        "confianza=excluded.confianza, candidatos=excluded.candidatos, "
        "metodo=excluded.metodo, fuera_de_alcance=excluded.fuera_de_alcance, "
        "sensible=excluded.sensible, ts=excluded.ts",
        (url, tema, confianza,
         json.dumps(candidatos, ensure_ascii=False) if candidatos is not None else None,
         metodo, int(bool(fuera_de_alcance)), int(bool(sensible)), ahora()),
    )


def get_clasificaciones(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM clasificaciones ORDER BY id"):
        d = dict(r)
        d["candidatos"] = json.loads(d["candidatos"]) if d.get("candidatos") else None
        d["fuera_de_alcance"] = bool(d.get("fuera_de_alcance"))
        d["sensible"] = bool(d.get("sensible"))
        out.append(d)
    return out


# --- indicadores ---

def upsert_indicadores(conn: sqlite3.Connection, rows: list[dict]) -> int:
    n = 0
    for r in rows:
        valor = r.get("valor")
        valor_txt = None if valor in ("", None) else str(valor)
        cur = conn.execute(
            "INSERT INTO indicadores (pais_iso3, indicador_id, anio, valor, unidad, "
            "fuente_url, fecha_extraccion, licencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(pais_iso3, indicador_id, anio) DO UPDATE SET valor=excluded.valor, "
            "unidad=excluded.unidad, fuente_url=excluded.fuente_url, "
            "fecha_extraccion=excluded.fecha_extraccion, licencia=excluded.licencia",
            (r.get("pais_iso3"), r.get("indicador_id"), r.get("anio"), valor_txt,
             r.get("unidad"), r.get("fuente_url"), r.get("fecha_extraccion"),
             r.get("licencia")),
        )
        n += cur.rowcount
    return n


def get_indicadores(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT pais_iso3, indicador_id, anio, valor, unidad, fuente_url, "
        "fecha_extraccion, licencia FROM indicadores ORDER BY rowid")]


# --- eventos sísmicos ---

def replace_eventos(conn: sqlite3.Connection, features: list[dict]) -> None:
    conn.execute("DELETE FROM eventos_sismicos")
    for f in features:
        props = f.get("properties") or {}
        geom = (f.get("geometry") or {}).get("coordinates") or [None, None, None]
        conn.execute(
            "INSERT INTO eventos_sismicos (id, mag, place, time_ms, url, lat, lon, depth, "
            "feature_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f.get("id"), props.get("mag"), props.get("place"), props.get("time"),
             props.get("url"), geom[0], geom[1], geom[2],
             json.dumps(f, ensure_ascii=False)),
        )


def get_eventos_features(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM eventos_sismicos ORDER BY rowid"):
        d = dict(r)
        d["feature"] = json.loads(d["feature_json"]) if d.get("feature_json") else None
        out.append(d)
    return out


# --- fichas / borradores ---

def upsert_ficha(conn: sqlite3.Connection, f: dict) -> None:
    conn.execute(
        "INSERT INTO fichas (id_caso, titulo, tema, puntaje, componentes, estado_evidencia, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(id_caso) DO UPDATE SET titulo=excluded.titulo, tema=excluded.tema, "
        "puntaje=excluded.puntaje, componentes=excluded.componentes, "
        "estado_evidencia=excluded.estado_evidencia, ts=excluded.ts",
        (f.get("id"), f.get("title"), f.get("tema"), f.get("score"),
         json.dumps(f.get("components"), ensure_ascii=False), f.get("evidence_state"), ahora()),
    )


def add_borrador(conn: sqlite3.Connection, ficha_id: str, modelo: str, version: str,
                 prompt_hash: str, tokens: int | None, costo: float | None,
                 latencia: float | None, contenido: dict | None) -> None:
    conn.execute(
        "INSERT INTO borradores (ficha_id, modelo, version, prompt_hash, tokens, costo, "
        "latencia, contenido, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ficha_id, modelo, version, prompt_hash, tokens, costo, latencia,
         json.dumps(contenido, ensure_ascii=False) if contenido is not None else None, ahora()),
    )


# --- decisiones (append-only) ---

def add_decision(conn: sqlite3.Connection, tipo: str, nombre: str | None, nota: str | None,
                 fecha: str | None, ficha_id: str | None, payload: dict | None) -> int:
    """INSERT de una decisión. Solo inserta (los triggers bloquean UPDATE/DELETE)."""
    cur = conn.execute(
        "INSERT INTO decisiones (tipo, nombre, nota, fecha, ficha_id, payload) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (tipo, _txt(nombre, NOMBRE_MAX), _txt(nota, NOTA_MAX),
         fecha or ahora(), ficha_id,
         json.dumps(payload, ensure_ascii=False) if payload is not None else None),
    )
    return int(cur.lastrowid or 0)


def list_decisiones(conn: sqlite3.Connection, tipo: str | None = None) -> list[dict]:
    if tipo:
        rows = conn.execute("SELECT * FROM decisiones WHERE tipo = ? ORDER BY id", (tipo,))
    else:
        rows = conn.execute("SELECT * FROM decisiones ORDER BY id")
    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d["payload"]) if d.get("payload") else None
        out.append(d)
    return out


# --- cache LLM ---

def set_llm_cache(conn: sqlite3.Connection, clave: str, salida: dict, modelo: str | None = None) -> None:
    conn.execute(
        "INSERT INTO cache_llm (clave, salida, modelo, ts) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET salida=excluded.salida, modelo=excluded.modelo, ts=excluded.ts",
        (clave, json.dumps(salida, ensure_ascii=False), modelo, ahora()),
    )


def get_llm_cache(conn: sqlite3.Connection, clave: str) -> dict | None:
    r = conn.execute("SELECT salida FROM cache_llm WHERE clave = ?", (clave,)).fetchone()
    if r is None:
        return None
    try:
        return json.loads(r["salida"])
    except Exception:
        return None


# --- snapshots ---

def record_snapshot(conn: sqlite3.Connection, manifest: dict, eventos_json: str) -> None:
    conn.execute(
        "INSERT INTO snapshots (version, rules_version, fecha_corte_UTC, manifest_json, "
        "eventos_json, ts) VALUES (?, ?, ?, ?, ?, ?)",
        (manifest.get("version"), manifest.get("rules_version"),
         manifest.get("fecha_corte_UTC"), json.dumps(manifest, ensure_ascii=False),
         eventos_json, ahora()),
    )


def get_snapshot(conn: sqlite3.Connection) -> dict | None:
    r = conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
    if r is None:
        return None
    d = dict(r)
    d["manifest"] = json.loads(d["manifest_json"]) if d.get("manifest_json") else {}
    return d


def count_noticias(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS c FROM noticias").fetchone()["c"])
