"""T6 — generación de borradores: al aire vs notas internas, atribución, validador."""
from __future__ import annotations

from pipeline import draft, process


def item(title, url="https://mire.gob.pa/x", source="Ministerio de Relaciones Exteriores",
         official=True, published="2026-10-01T00:00:00Z"):
    return {"title": title, "url": url, "source": source, "published": published,
            "snippet": "", "topics": [], "id": title[:8], "official": official}


def _ficha(g):
    return process.priority([g], ["Panamá"])[0]


def test_texto_al_aire_no_contiene_meta_mensajes():
    f = _ficha([item("Panamá llega a la Cumbre del MERCOSUR como el principal conector de la región")])
    d = draft.build(f)
    al_aire = (d["texto_al_aire"]["guion"] + " " + d["texto_al_aire"]["copy"]).lower()
    assert "evidencia suficiente" not in al_aire
    assert "segunda fuente" not in al_aire
    assert "titular/metadatos" not in al_aire
    assert d["notas_internas"], "las advertencias deben ir en notas internas"


def test_titulo_sin_puntos_suspensivos():
    f = _ficha([item("Panamá llega a la Cumbre del MERCOSUR como el principal conector global de la región con acuerdos e inversiones")])
    d = draft.build(f)
    assert "…" not in d["titulo_propuesto"]
    assert "..." not in d["titulo_propuesto"]


def test_declaracion_institucional_atribuida():
    f = _ficha([item("Panamá llega a la Cumbre del MERCOSUR como el principal conector de la región")])
    d = draft.build(f)
    assert "Según" in d["texto_al_aire"]["guion"] or "afirma" in d["texto_al_aire"]["guion"]
    assert f["tipo_afirmacion"] == "declaracion_institucional"


def test_citas_validas():
    f = _ficha([item("Policía Nacional incauta 65 paquetes en un contenedor",
                     url="https://www.policia.gob.pa/a", source="Policía Nacional")])
    d = draft.build(f)
    assert d["citas_ok"] is True
    assert all(a.get("cita") and a.get("campo") for a in d["afirmaciones"])
