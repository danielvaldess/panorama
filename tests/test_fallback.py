"""T7 — fallback visible del resumen asistido cuando la IA no está disponible."""
from __future__ import annotations

from pipeline import ai


def test_fallback_visible_sin_ia(monkeypatch):
    monkeypatch.setattr(ai, "_key", lambda: "")   # fuerza el camino sin LLM
    ai._CACHE.clear()
    r = ai.analyze("El Canal de Panamá amplía sus cupos de tránsito", [{"name": "TVN", "url": "https://x"}])
    assert r["method"] == "local"
    assert r["fallback"] is True
    assert r["message"]
    assert r["summary"]


def test_cache_devuelve_la_misma_salida(monkeypatch):
    monkeypatch.setattr(ai, "_key", lambda: "")
    ai._CACHE.clear()
    titulo = "Nota de prueba en caché sobre el Canal"
    a = ai.analyze(titulo, [{"name": "TVN", "url": "https://x"}])
    b = ai.analyze(titulo, [{"name": "TVN", "url": "https://x"}])
    assert a is b or a == b
