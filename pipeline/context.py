"""Contextualización con puerta de relevancia (T5).

Solo se enlaza un indicador oficial si el tema tiene una relación explícita y
sustentada. Si no la hay, se muestra **"Sin indicador oficial pertinente"** en vez
de rellenar con Población/Internet. Cada contexto incluye país, año, unidad, la
justificación y la nota de que es un dato anual histórico.
"""
from __future__ import annotations

from pipeline import snapshot

# Tabla explícita tema -> indicadores permitidos (T5).
TEMA_INDICADORES = {
    "economia": ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS"],
    "logistica": ["NE.EXP.GNFS.ZS"],
    "relaciones_exteriores": ["NE.EXP.GNFS.ZS"],
    "turismo": ["NE.EXP.GNFS.ZS"],
}

INDICADOR_NOMBRE = {
    "NY.GDP.MKTP.KD.ZG": "Crecimiento del PIB",
    "FP.CPI.TOTL.ZG": "Inflación",
    "SL.UEM.TOTL.ZS": "Desempleo",
    "SP.POP.TOTL": "Población",
    "IT.NET.USER.ZS": "Uso de Internet",
    "NE.EXP.GNFS.ZS": "Exportaciones (% del PIB)",
}

JUSTIFICACION = {
    ("economia", "NY.GDP.MKTP.KD.ZG"): "El crecimiento del PIB enmarca el desempeño económico del país.",
    ("economia", "FP.CPI.TOTL.ZG"): "La inflación mide la evolución de los precios.",
    ("economia", "SL.UEM.TOTL.ZS"): "El desempleo mide el mercado laboral.",
    ("logistica", "NE.EXP.GNFS.ZS"): "Las exportaciones (% del PIB) aproximan el peso del comercio ligado al Canal y la logística.",
    ("relaciones_exteriores", "NE.EXP.GNFS.ZS"): "El comercio exterior se mide con las exportaciones (% del PIB).",
    ("turismo", "NE.EXP.GNFS.ZS"): "Las exportaciones (% del PIB) aproximan el aporte del sector externo, que incluye el turismo.",
}

LIMITE = "Dato anual histórico del Banco Mundial; no es una medición de hoy."
PROYECCION = ("proyecta", "proyección", "proyeccion", "estima", "prevé", "preve", "pronostica", "se espera")
COMPARABILIDAD = ("El titular reporta una proyección; el dato oficial es observado. "
                  "No son comparables directamente.")

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


def _sin_contexto() -> dict:
    return {
        "tipo": "sin_contexto", "titulo": "Sin indicador oficial pertinente",
        "detalle": "No hay una serie oficial que sustente este tema; no se fuerza el contexto.",
        "periodo": "", "unidad": "", "limite": "", "fuente_url": "", "justificacion": "",
    }


def build(ficha: dict) -> list[dict]:
    tema = ficha.get("tema", "general")
    title = (ficha.get("title") or "").lower()
    proyeccion = any(m in title for m in PROYECCION)
    out: list[dict] = []

    for i, ind in enumerate(TEMA_INDICADORES.get(tema, [])):
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
            "justificacion": JUSTIFICACION.get((tema, ind), "Relación temática con la serie."),
            "principal": i == 0,
            "comparabilidad": COMPARABILIDAD if proyeccion else "",
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
                "justificacion": "USGS documenta hechos sísmicos verificables.",
            })

    if not out:
        out.append(_sin_contexto())
    return out
