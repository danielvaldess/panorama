"""T4 — clasificación temática con confianza (incluye relaciones exteriores/comercio)."""
from __future__ import annotations

from pipeline import process, theme


def item(title, url="https://www.tvn-2.com/a", source="TVN Noticias", published=None):
    return {"title": title, "url": url, "source": source, "published": published,
            "snippet": "", "topics": [], "id": title[:8], "official": False}


def test_mercosur_es_relaciones_exteriores_o_sin_clasificar_con_candidatos():
    titulo = "Panamá llega a la Cumbre del MERCOSUR como el principal conector global de la región"
    tema, conf, cands = theme.clasificar_tema(titulo)
    assert tema == "relaciones_exteriores" or tema == "sin_clasificar"
    if tema == "sin_clasificar":
        assert any(c["tema"] == "relaciones_exteriores" for c in cands)


def test_sismo_es_eventos_naturales():
    tema, _, _ = theme.clasificar_tema("Sismo de magnitud 4.2 se siente en la provincia de Darién")
    assert tema == "eventos_naturales"


def test_ficha_expone_confianza_y_candidatos():
    f = process.priority([[item("Cancillería firma tratado de comercio exterior")]], ["Panamá"])[0]
    assert "tema_confianza" in f and "tema_candidatos" in f and "tema_baseline" in f
