"""Contextualización: relaciona un tema con datos oficiales (Banco Mundial / USGS).

Regla del reto: mostrar **período, unidad y limitaciones**; si no hay relación
sustentada, **no forzarla**.
"""
from __future__ import annotations

from pipeline import snapshot

TEMA_INDICADORES = {
    "economia": ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS"],
    "logistica": ["NE.EXP.GNFS.ZS"],
    "servicios": ["IT.NET.USER.ZS", "SP.POP.TOTL"],
    "turismo": [],
    "eventos_naturales": [],
    "regulacion": [],
    "general": [],
}
INDICADOR_NOMBRE = {
    "NY.GDP.MKTP.KD.ZG": "Crecimiento del PIB",
    "FP.CPI.TOTL.ZG": "Inflación",
    "SL.UEM.TOTL.ZS": "Desempleo",
    "SP.POP.TOTL": "Población",
    "IT.NET.USER.ZS": "Uso de Internet",
    "NE.EXP.GNFS.ZS": "Exportaciones (% del PIB)",
}
LIMITE = "Dato anual histórico del Banco Mundial; no es una medición de hoy."

_ind_cache = None
_ev_cache = None


def _indicators():
    global _ind_cache
    if _ind_cache is None:
        rows = snapshot.load_indicators()
        by = {}
        for r in rows:
            if r.get("pais_iso3") == "PAN" and r.get("valor") is not None:
                by.setdefault(r["indicador_id"], {})[r["anio"]] = r
        _ind_cache = by
    return _ind_cache


def _events():
    global _ev_cache
    if _ev_cache is None:
        feats = snapshot.load_events().get("features", [])
        _ev_cache = feats
    return _ev_cache


def _fmt(v):
    try:
        return f"{v:,.1f}".replace(",", " ")
    except Exception:
        return str(v)


def build(ficha: dict) -> list[dict]:
    tema = ficha.get("tema", "general")
    out: list[dict] = []

    for ind in TEMA_INDICADORES.get(tema, []):
        serie = _indicators().get(ind, {})
        if not serie:
            continue
        anio = max(serie)
        row = serie[anio]
        prev = serie.get(str(int(anio) - 1))
        detalle = f"Panamá · {anio}: {_fmt(row['valor'])} {row['unidad']}"
        if prev:
            d = row["valor"] - prev["valor"]
            detalle += f" ({'▲' if d >= 0 else '▼'} {abs(d):.1f} vs {prev['anio']})"
        out.append({
            "tipo": "indicador", "titulo": INDICADOR_NOMBRE.get(ind, ind), "detalle": detalle,
            "periodo": f"{anio} (anual)", "unidad": row["unidad"], "limite": LIMITE,
            "fuente_url": row.get("fuente_url", ""),
        })

    if tema == "eventos_naturales":
        ev = _events()
        if ev:
            latest = max(ev, key=lambda f: (f.get("properties", {}) or {}).get("time", 0))
            p = latest.get("properties", {})
            out.append({
                "tipo": "evento",
                "titulo": "Sismos recientes en la región",
                "detalle": f"{len(ev)} sismos (mag ≥3) en 2024 · último: M{p.get('mag')} — {p.get('place')}",
                "periodo": "2024", "unidad": "magnitud",
                "limite": "USGS solo reporta hechos sísmicos; no implica daños ni inundaciones.",
                "fuente_url": p.get("url", ""),
            })
    return out
