"""Persistencia operativa del poller: noticias + clasificación en una transacción.

El poller escribe noticias (dedup por UNIQUE(url)) y el estado de temas/
clasificación de cada noticia nueva dentro de una única transacción SQLite.
"""
from __future__ import annotations

from pipeline import db, theme


def persist_noticias(conn, items: list[dict]) -> list[str]:
    """Inserta noticias (INSERT OR IGNORE por url) y clasifica las nuevas.

    Devuelve las URLs que se insertaron por primera vez. Todo es transaccional.
    """
    nuevos: list[str] = []
    with db.transaction(conn):
        nuevos = db.insert_noticias(conn, items)
        for x in items:
            url = x.get("url", "")
            if url not in nuevos:
                continue
            t, conf, cands, metodo, fuera, sens = theme.clasificar_tema(
                x.get("title", ""), x.get("snippet", ""))
            db.upsert_clasificacion(conn, url, t, conf, cands, metodo, fuera, sens)
    return nuevos
