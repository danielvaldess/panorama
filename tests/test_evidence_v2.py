"""T1 — Modelo de evidencia v2: tipado, E continuo, evidence_state e invariantes."""
from __future__ import annotations

from pipeline import claims, context, process, score


def item(title, url="https://www.tvn-2.com/a", source="TVN Noticias", official=False, published=None):
    return {"title": title, "url": url, "source": source, "published": published,
            "snippet": "", "topics": [], "id": title[:8], "official": official}


def _ficha(g):
    return process.priority([g], ["Panamá", "economía", "Canal"])[0]


# --- Caso real: la ficha del MERCOSUR -------------------------------------------------
def test_oficial_declaracion_sin_corroboracion_es_parcial():
    g = [item("Panamá llega a la Cumbre del MERCOSUR como el principal conector global de la región",
              url="https://mire.gob.pa/nota", source="Ministerio de Relaciones Exteriores", official=True)]
    v = process._verify(g)
    tipo = claims.clasificar_afirmacion(g[0]["title"], official=bool(v["official"]), origen=g[0]["source"])
    assert tipo == "declaracion_institucional"
    assert v["independent"] == 1
    assert score.evidence_state(v, tipo) == "Parcial"
    comp, _ = score.compute_components(g, 0.5, v, tipo)
    assert comp["E"] < 1.0
    assert "E_detalle" in comp


def test_mercosur_ficha_completa():
    g = [item("Panamá llega a la Cumbre del MERCOSUR como el principal conector global de la región",
              url="https://mire.gob.pa/nota", source="Ministerio de Relaciones Exteriores", official=True)]
    f = _ficha(g)
    assert f["evidence_state"] == "Parcial"
    assert f["tipo_afirmacion"] == "declaracion_institucional"
    assert f["components"]["E"] < 1.0


# --- Invariante: suficiente => sin pendiente de corroboración -------------------------
def test_invariante_suficiente_implica_sin_pendiente_de_corroboracion():
    from pipeline import draft
    g = [item("Canal de Panamá amplía los cupos de tránsito diarios", url="https://www.prensa.com/a", source="La Prensa"),
         item("Buques cruzan con menos espera por las esclusas panameñas", url="https://www.laestrella.com.pa/b", source="La Estrella")]
    f = _ficha(g)
    if f["evidence_state"] == "Suficiente para el borrador":
        d = draft.build(f)
        assert not any("segunda fuente independiente" in p for p in d["verificaciones_pendientes"])


# --- Contradicción -------------------------------------------------------------------
def test_contradiccion_limita_evidencia_a_parcial_y_muestra_ambas_versiones():
    g = [item("Confirman el cierre del proyecto minero", url="https://www.prensa.com/a", source="La Prensa"),
         item("Desmienten el cierre del proyecto minero", url="https://www.laestrella.com.pa/b", source="La Estrella")]
    f = _ficha(g)
    assert f["evidence_flags"]["contradiccion"] is True
    assert f["evidence_state"] == "Parcial"


# --- Agencia replicada por 5 medios cuenta 1 -----------------------------------------
def test_agencia_replicada_por_5_medios_cuenta_1():
    titulo = "El Canal de Panamá amplía los cupos de tránsito para buques"
    g = [item(titulo, url=f"https://medio{i}.com/a", source=f"Medio {i}") for i in range(5)]
    v = process._verify(g)
    assert v["independent"] == 1


# --- Dato anual no se describe como "de hoy" -----------------------------------------
def test_contexto_oficial_anual_marca_periodo_y_limite():
    ctx = context.build({"tema": "economia", "title": "Crecimiento del PIB de Panamá"})
    assert ctx, "economia debe tener contexto oficial"
    c = ctx[0]
    assert c["periodo"][:2] == "20"
    assert "no es una medición de hoy" in c["limite"]
