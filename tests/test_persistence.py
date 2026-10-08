"""Persistencia operativa: decisiones, caché LLM y clasificaciones (SQLite en memoria)."""
from __future__ import annotations

import sqlite3

import pytest

from pipeline import ai as ai_mod
from pipeline import db, persist, store


@pytest.fixture()
def db_ready():
    db.reset()
    conn = db.ensure_ready(":memory:")
    yield conn
    db.reset()


def test_store_revision_append_only_ultima_gana(db_ready):
    store.guardar_revision({"id": "f1", "state": "nuevo", "note": "n", "reviewer": "a",
                            "ts": "2026-10-08T00:00:00+00:00"})
    store.guardar_revision({"id": "f1", "state": "descartado", "note": "n2", "reviewer": "a",
                            "ts": "2026-10-08T00:00:01+00:00"})
    assert store.cargar_revisiones()["f1"]["state"] == "descartado"


def test_store_veredicto_roundtrip(db_ready):
    store.guardar_veredicto({"id_caso": "c1", "indice": 0, "veredicto": "válido",
                             "comentario": "ok", "reviewer": "a",
                             "ts": "2026-10-08T00:00:00+00:00"})
    vs = store.cargar_veredictos()
    assert vs[0]["veredicto"] == "válido"


def test_persist_noticias_clasifica_y_deduplica(db_ready):
    items = [{"title": "Canal de Panamá amplía cupos", "url": "http://x/c", "source": "TVN",
              "snippet": "", "id": "a", "published": None}]
    nuevos = persist.persist_noticias(db_ready, items)
    assert nuevos == ["http://x/c"]
    clas = db.get_clasificaciones(db_ready)
    assert clas and clas[0]["noticia_url"] == "http://x/c" and clas[0]["tema"]
    # segunda inserción no duplica (UNIQUE url)
    assert persist.persist_noticias(db_ready, items) == []


def test_ai_cache_db_roundtrip(db_ready):
    ai_mod._cache_set("k", {"summary": "s"}, "mimo")
    assert ai_mod._cache_get("k") == {"summary": "s"}


def test_decisiones_solo_insert_via_store(db_ready):
    store.guardar_revision({"id": "f", "state": "nuevo", "note": "n", "reviewer": "a", "ts": "t"})
    with pytest.raises(sqlite3.Error):
        db_ready.execute("DELETE FROM decisiones")
    assert len(store.cargar_revisiones()) == 1
