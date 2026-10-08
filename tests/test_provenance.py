"""T2 — procedencia real (agencia/dominio) y conteo de orígenes."""
from __future__ import annotations

from pipeline import origin


def _it(title, url, source):
    return {"title": title, "url": url, "source": source}


def test_origen_real_detecta_agencia():
    x = _it("EFE: El Canal amplía cupos de tránsito", "https://medio.com/a", "Medio")
    assert origin.origen_real(x).startswith("agencia:")


def test_origen_real_usa_dominio_raiz():
    x = _it("Nota local", "https://www.tvn-2.com/nacionales/x", "TVN Noticias")
    assert origin.origen_real(x) == "tvn-2.com"


def test_agencia_replicada_cuenta_uno():
    g = [_it("Reuters: Panamá crece 3%", f"https://m{i}.com/a", f"Medio {i}") for i in range(4)]
    assert origin.collapse_origins(g) == 1


def test_origenes_distintos_cuentan_dos():
    g = [_it("El Canal amplía cupos de tránsito para buques", "https://prensa.com/a", "La Prensa"),
         _it("Bocas del Toro registra más visitantes", "https://laestrella.com.pa/b", "La Estrella")]
    assert origin.collapse_origins(g) == 2
