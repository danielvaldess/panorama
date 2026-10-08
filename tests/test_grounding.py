"""T6.6 — puerta anti-alucinación del resumen + tipado de proyección + contexto."""
from __future__ import annotations

from pipeline import ai, claims, context, draft, process


def _item(title, url="https://www.tvn-2.com/a", source="TVN Noticias", official=False):
    return {"title": title, "url": url, "source": source, "published": "2026-10-01T00:00:00Z",
            "snippet": "", "topics": [], "id": title[:8], "official": official}


# --- Resumen asistido: se descarta si no se sostiene en el titular ---
def test_resumen_no_respaldado_se_descarta(monkeypatch):
    ai._CACHE.clear()
    monkeypatch.setattr(ai, "_save_cache", lambda: None)
    monkeypatch.setattr(ai, "_chat", lambda *a, **k: '{"resumen": "La proyección orienta el seguimiento económico nacional y las expectativas para 2026."}')
    r = ai.analyze("FMI proyecta que la economía de Panamá crecerá cerca de 5% este 2026",
                   [{"name": "TVN", "url": "https://x"}])
    assert r["fallback"] is True
    assert "determinística" in r["message"]


def test_resumen_respaldado_se_acepta(monkeypatch):
    ai._CACHE.clear()
    monkeypatch.setattr(ai, "_save_cache", lambda: None)
    monkeypatch.setattr(ai, "_chat", lambda *a, **k: '{"resumen": "El FMI proyecta que la economía de Panamá crecerá cerca de 5% este 2026."}')
    r = ai.analyze("FMI proyecta que la economía de Panamá crecerá cerca de 5% este 2026",
                   [{"name": "TVN", "url": "https://x"}])
    assert r["fallback"] is False
    assert r["method"] == "ai"


# --- Proyección = declaración de tercero, no hecho verificable ---
def test_proyeccion_es_declaracion_de_tercero():
    assert claims.clasificar_afirmacion("FMI proyecta que la economía crecerá 5% en 2026") == "declaracion_tercero"


def test_draft_marca_proyeccion_y_fuente_primaria():
    f = process.priority([[ _item("FMI proyecta que la economía de Panamá crecerá cerca de 5% este 2026") ]],
                         ["Panamá", "economía"])[0]
    d = draft.build(f)
    assert d["proyeccion"] is True
    assert d["fuente_primaria"] == "FMI · World Economic Outlook"
    assert any("proyección" in p for p in d["verificaciones_pendientes"])


# --- Contexto: nota de comparabilidad para proyecciones + principal ---
def test_contexto_proyeccion_tiene_comparabilidad():
    ctx = context.build({"tema": "economia", "title": "FMI proyecta que la economía crecerá 5% en 2026"})
    assert ctx and ctx[0]["principal"] is True
    assert "No son comparables" in ctx[0]["comparabilidad"]
