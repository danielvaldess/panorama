"""T5 — puerta de relevancia del contexto oficial."""
from __future__ import annotations

from pipeline import context


def test_tema_sin_indicador_pertinente_no_muestra_contexto():
    ctx = context.build({"tema": "servicios_publicos", "title": "Metro amplía su horario"})
    assert len(ctx) == 1
    assert ctx[0]["tipo"] == "sin_contexto"
    assert "Sin indicador oficial pertinente" in ctx[0]["titulo"]


def test_relaciones_exteriores_usa_exportaciones_con_justificacion():
    ctx = context.build({"tema": "relaciones_exteriores_comercio", "title": "Cumbre del MERCOSUR"})
    assert ctx and ctx[0]["tipo"] == "indicador"
    assert "Exportaciones" in ctx[0]["titulo"]
    assert ctx[0]["justificacion"]
    assert "no es una medición de hoy" in ctx[0]["limite"]


def test_economia_usa_pib_con_periodo_y_unidad():
    ctx = context.build({"tema": "economia", "title": "Crecimiento del PIB"})
    assert ctx[0]["tipo"] == "indicador"
    assert ctx[0]["periodo"][:2] == "20"
    assert ctx[0]["unidad"]
