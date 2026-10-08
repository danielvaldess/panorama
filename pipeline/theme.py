"""Clasificación temática con confianza (T4).

Híbrido: embeddings (zero-shot por similitud a descripciones de tema) con respaldo
por palabras clave. Si la confianza es baja, devuelve `sin_clasificar` y los 2
mejores candidatos, en lugar de inventar un enfoque que no está en el titular.
"""
from __future__ import annotations

import numpy as np

from pipeline import embed

UMBRAL = 0.30

TEMAS = {
    "economia": "economía, presupuesto, inflación, precios, empleo, canasta básica, PIB",
    "logistica": "Canal de Panamá, puertos, logística, tránsito de buques, carga, esclusas",
    "turismo": "turismo, cruceros, hoteles, vuelos, visitantes, playas",
    "servicios": "servicios públicos, agua, electricidad, metro, transporte, salud, educación",
    "eventos_naturales": "sismos, terremotos, lluvias, inundaciones, huracanes, sequía",
    "regulacion": "leyes, decretos, contratos, licitaciones, tribunales, Asamblea",
    "relaciones_exteriores": "diplomacia, cancillería, relaciones exteriores, comercio exterior, tratados, cumbres internacionales",
}


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _ml(titulo: str) -> tuple[str, float, list[dict]] | None:
    """Clasificación pura por embeddings (para comparación), o None si no hay."""
    if not embed.available():
        return None
    try:
        names = list(TEMAS.keys())
        m = embed.cosine_matrix([titulo] + list(TEMAS.values()))
        sims = np.asarray(m[0, 1:], dtype=np.float32)
        probs = _softmax(sims * 6.0)
        order = np.argsort(-probs)
        top = int(order[0])
        cands = [{"tema": names[int(i)], "score": round(float(probs[int(i)]), 2)} for i in order[:2]]
        return names[top], round(float(probs[top]), 2), cands
    except Exception:
        return None


def clasificar_tema_ml(titulo: str, threshold: float = UMBRAL) -> str:
    """Tema por embeddings puros (baseline de comparación)."""
    from pipeline.ingest import _tema as _tema_kw
    ml = _ml(titulo)
    if ml is None:
        return _tema_kw(titulo)
    return ml[0] if ml[1] >= threshold else "sin_clasificar"


def clasificar_tema(titulo: str, threshold: float = UMBRAL) -> tuple[str, float, list[dict]]:
    """Híbrido (producto): palabras clave cuando son explícitas; si no, embeddings.

    Devuelve (tema, confianza 0–1, candidatos[{tema, score}]). Si nada es claro,
    `sin_clasificar` con los 2 mejores candidatos.
    """
    from pipeline.ingest import _tema as _tema_kw

    kw = _tema_kw(titulo)
    ml = _ml(titulo)
    if kw != "general":
        cands = ([{"tema": kw, "score": 0.5}] + (ml[2] if ml else []))[:2]
        return kw, 0.5, cands
    if ml and ml[1] >= threshold:
        return ml[0], ml[1], ml[2]
    if ml:
        return "sin_clasificar", ml[1], ml[2]
    return "sin_clasificar", 0.3, [{"tema": "general", "score": 0.3}]


def clasificar_temas(titulos: list[str], threshold: float = UMBRAL) -> list[tuple[str, float, list[dict]]]:
    """Versión en lote: una sola llamada de embeddings para todos los títulos.

    Evita cientos de llamadas por build (rendimiento).
    """
    from pipeline.ingest import _tema as _tema_kw

    if not titulos:
        return []
    if not embed.available():
        return [clasificar_tema(t, threshold) for t in titulos]
    try:
        names = list(TEMAS.keys())
        m = embed.cosine_matrix(list(titulos) + list(TEMAS.values()))
        n = len(titulos)
        out: list[tuple[str, float, list[dict]]] = []
        for i in range(n):
            sims = np.asarray(m[i, n:], dtype=np.float32)
            probs = _softmax(sims * 6.0)
            order = np.argsort(-probs)
            top = int(order[0])
            cands = [{"tema": names[int(j)], "score": round(float(probs[int(j)]), 2)} for j in order[:2]]
            kw = _tema_kw(titulos[i])
            if kw != "general":
                out.append((kw, 0.5, ([{"tema": kw, "score": 0.5}] + cands)[:2]))
            elif float(probs[top]) >= threshold:
                out.append((names[top], round(float(probs[top]), 2), cands))
            else:
                out.append(("sin_clasificar", round(float(probs[top]), 2), cands))
        return out
    except Exception:
        return [clasificar_tema(t, threshold) for t in titulos]


ETIQUETA = {
    "economia": "Economía",
    "logistica": "Logística",
    "turismo": "Turismo",
    "servicios": "Servicios",
    "eventos_naturales": "Eventos naturales",
    "regulacion": "Regulación",
    "relaciones_exteriores": "Relaciones exteriores / comercio",
    "sin_clasificar": "Sin clasificar con certeza",
    "general": "General",
}
