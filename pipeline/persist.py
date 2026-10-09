"""Persistencia operativa del poller: noticias + clasificación en una transacción.

El poller escribe noticias (dedup por UNIQUE(url)) y el estado de temas/
clasificación de cada noticia nueva dentro de una única transacción SQLite.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pipeline import db, theme


def _id(title: str, url: str) -> str:
    return hashlib.sha1(f"{title}|{url}".encode("utf-8")).hexdigest()[:12]


def _normalize_item(x: dict) -> dict | None:
    """Acepta items del snapshot o del poller live y los adapta al schema SQLite."""
    title = (x.get("titulo") or x.get("title") or "").strip()
    url = (x.get("url") or "").strip()
    if not title or not url:
        return None
    published = x.get("fecha_publicacion") or x.get("published") or ""
    detected = x.get("fecha_deteccion") or published or datetime.now(timezone.utc).isoformat()
    return {
        "id_noticia": x.get("id_noticia") or x.get("id") or _id(title, url),
        "titulo": title,
        "url": url,
        "medio": x.get("medio") or x.get("source") or "",
        "idioma": x.get("idioma") or "es",
        "fecha_publicacion": published,
        "fecha_deteccion": detected,
        "fecha_extraccion": x.get("fecha_extraccion") or datetime.now(timezone.utc).isoformat(),
        "tema": x.get("tema") or x.get("topic") or "",
        "origen": x.get("origen") or x.get("origin") or "live",
        "alcance_texto": x.get("alcance_texto") or "titular+metadatos",
        "descripcion": x.get("descripcion") or x.get("snippet") or "",
    }


def persist_noticias(conn, items: list[dict]) -> list[str]:
    """Inserta noticias (INSERT OR IGNORE por url) y clasifica las nuevas.

    Devuelve las URLs que se insertaron por primera vez. Todo es transaccional.
    """
    normalized = [x for x in (_normalize_item(i) for i in items) if x is not None]
    nuevos: list[str] = []
    with db.transaction(conn):
        nuevos = db.insert_noticias(conn, normalized)
        for x in normalized:
            url = x.get("url", "")
            if url not in nuevos:
                continue
            t, conf, cands, metodo, fuera, sens = theme.clasificar_tema(
                x.get("titulo", ""), x.get("descripcion", ""))
            db.upsert_clasificacion(conn, url, t, conf, cands, metodo, fuera, sens)
    return nuevos
