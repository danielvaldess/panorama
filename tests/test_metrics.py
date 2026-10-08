"""T8 — métricas de sustento consistentes (unidades y numerador/denominador)."""
from __future__ import annotations

from eval import sustento


def test_sustento_numerador_denominador(monkeypatch):
    monkeypatch.setattr(sustento, "_mapa_actuales", lambda: {})  # sin filtrado por ficha vigente
    etqs = [
        {"id_caso": "A", "indice": 0, "veredicto": "válido", "texto": "x", "tipo": "hecho_verificable"},
        {"id_caso": "A", "indice": 1, "veredicto": "parcial", "texto": "y", "tipo": "hecho_verificable"},
        {"id_caso": "B", "indice": 0, "veredicto": "válido", "texto": "z", "tipo": "hecho_verificable"},
    ]
    res = sustento.calcular(etiquetas=etqs)
    assert res["denominador"] == 3
    assert res["numerador_validos"] == 2
    assert res["pct_validos"] == round(2 / 3, 4)
    assert len(res["fallos"]) == 1        # reporta fallos, no los esconde


def test_sustento_sin_muestra_reporta_pendiente(monkeypatch):
    monkeypatch.setattr(sustento, "_mapa_actuales", lambda: {})
    res = sustento.calcular(etiquetas=[])
    assert res["denominador"] == 0
    assert res["pct_validos"] is None
    assert res["muestra"]["suficiente"] is False
