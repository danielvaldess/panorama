"""Pruebas de la capa de repositorio (db.py) con SQLite en memoria.

Ninguna prueba toca la DB real ni ai_cache.json: usamos `:memory:`.
"""
from __future__ import annotations

import sqlite3

import pytest

from pipeline import db


@pytest.fixture()
def conn():
    c = db.connect(":memory:")
    db.init(c)
    return c


def _noticia(url="http://x/a", idn="a", titulo="T1"):
    return {"id_noticia": idn, "titulo": titulo, "url": url, "medio": "M", "idioma": "es",
            "fecha_publicacion": None, "fecha_deteccion": None, "fecha_extraccion": None,
            "tema": "", "origen": "", "alcance_texto": "", "descripcion": ""}


def test_schema_crea_tablas(conn):
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ["fuentes", "noticias", "clasificaciones", "grupos_evento", "grupo_noticias",
              "indicadores", "eventos_sismicos", "fichas", "borradores", "decisiones",
              "cache_llm", "snapshots"]:
        assert t in names


def test_noticias_dedup_por_url_unique(conn):
    new = db.insert_noticias(conn, [_noticia(), _noticia(url="http://x/a", idn="b", titulo="T2")])
    assert new == ["http://x/a"]
    assert db.count_noticias(conn) == 1


def test_indicadores_valor_null_se_conserva(conn):
    db.upsert_indicadores(conn, [{"pais_iso3": "PAN", "indicador_id": "X", "anio": "2020",
                                  "valor": None, "unidad": "%", "fuente_url": "",
                                  "fecha_extraccion": "", "licencia": ""}])
    rows = db.get_indicadores(conn)
    assert rows[0]["valor"] is None  # nulo conservado, no 0


def test_decisiones_solo_insert(conn):
    db.add_decision(conn, "revision", "admin", "nota", None, "ficha1", {"state": "nuevo"})
    with pytest.raises(sqlite3.Error):
        conn.execute("UPDATE decisiones SET nota='x' WHERE id=1")
    with pytest.raises(sqlite3.Error):
        conn.execute("DELETE FROM decisiones WHERE id=1")
    assert len(db.list_decisiones(conn)) == 1


def test_decisiones_trunca_longitud(conn):
    db.add_decision(conn, "veredicto", "n" * 500, "m" * 5000, None, "f", {})
    d = db.list_decisiones(conn)[0]
    assert len(d["nombre"]) == db.NOMBRE_MAX
    assert len(d["nota"]) == db.NOTA_MAX


def test_decisiones_no_ejecuta_sql_injectado(conn):
    inj = "x'); DROP TABLE noticias;--"
    db.add_decision(conn, "revision", "admin", inj, None, "f", {})
    # la tabla sigue existiendo y el texto queda literal (consulta parametrizada)
    assert conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='noticias'").fetchone() is not None
    d = db.list_decisiones(conn)[0]
    assert d["nota"] == inj


def test_cache_llm_roundtrip(conn):
    db.set_llm_cache(conn, "clave", {"summary": "s"}, modelo="mimo")
    assert db.get_llm_cache(conn, "clave") == {"summary": "s"}
    assert db.get_llm_cache(conn, "ausente") is None
