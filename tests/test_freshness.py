"""T3 — frescura: noticias antiguas fuera de la Mesa de hoy, con fecha original."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeline import process


def item(title, url="https://www.tvn-2.com/a", source="TVN Noticias", published=None):
    return {"title": title, "url": url, "source": source, "published": published,
            "snippet": "", "topics": [], "id": title[:8], "official": False}


def _ficha(g):
    return process.priority([g], ["Panamá", "Canal"])[0]


def test_noticia_antigua_marcada_y_tope_prioridad():
    old = (datetime.now(timezone.utc) - timedelta(days=99)).strftime("%Y-%m-%dT%H:%M:%SZ")
    f = _ficha([item("Panamá llega a la Cumbre como el principal conector de la región", published=old)])
    assert f["recirculada"] is True
    assert f["edad_dias"] >= 90
    assert f["score"] <= 39                       # T3: sin urgencia no queda en media/alta
    assert f["published"] == old                  # se conserva la fecha original


def test_noticia_reciente_tiene_urgencia():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    f = _ficha([item("El Canal amplía los cupos de tránsito hoy", published=now)])
    assert f["recirculada"] is False
    assert f["components"]["U"] > 0.5
