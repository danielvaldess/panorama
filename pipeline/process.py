"""Procesamiento determinista con librerías estándar:
rank_bm25 (baseline) y rapidfuzz (dedupe/agrupación). Prioridad reproducible + abstención."""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz

# Confiabilidad por fuente (1-5).
SOURCE_RELIABILITY = {
    "TVN Noticias": 5, "La Prensa": 5, "Google News": 3,
    "tvn-2.com": 5, "prensa.com": 5, "telemetro.com": 4, "laestrella.com.pa": 4,
}
DEFAULT_RELIABILITY = 3


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-záéíóúñü0-9]{3,}", (s or "").lower())


def bm25(query: list[str], docs: list[list[str]]) -> list[float]:
    if not docs:
        return []
    bm = BM25Okapi([list(d) for d in docs])
    return [float(x) for x in bm.get_scores(query)]


def _norm(vals: list[float]) -> list[float]:
    mx = max(vals) if vals else 0.0
    return [v / mx if mx > 0 else 0.0 for v in vals]


def _sim(a: str, b: str) -> float:
    return fuzz.token_set_ratio(a, b) / 100.0


def dedupe(items: list[dict], threshold: float = 0.80) -> list[dict]:
    """Quita títulos casi idénticos (misma noticia republicada)."""
    kept: list[dict] = []
    for it in items:
        if any(_sim(it["title"], k["title"]) >= threshold for k in kept):
            continue
        kept.append(it)
    return kept


def cluster(items: list[dict], threshold: float = 0.62) -> list[list[dict]]:
    """Agrupa la misma historia contada por varias fuentes (citas/confianza)."""
    groups: list[list[dict]] = []
    for it in items:
        for g in groups:
            if _sim(it["title"], g[0]["title"]) >= threshold:
                g.append(it)
                break
        else:
            groups.append([it])
    return groups


def priority(groups: list[list[dict]], query: list[str]) -> list[dict]:
    """Prioridad reproducible: 0.55·relevancia (BM25) + 0.30·frescura + 0.15·confiabilidad."""
    reps = [g[0]["title"] for g in groups]
    rel = _norm(bm25(query, [tokens(r) for r in reps]))
    fichas = []
    for i, g in enumerate(groups):
        sources = sorted({x["source"] for x in g})
        rel_i = rel[i] if i < len(rel) else 0.0
        fresh = 1.0 if any(x.get("published") for x in g) else 0.5
        relia = max(SOURCE_RELIABILITY.get(s, DEFAULT_RELIABILITY) for s in sources) / 5
        score = round(0.55 * rel_i + 0.30 * fresh + 0.15 * relia, 2)
        abstain = not sources or all(not x["url"] for x in g)
        fichas.append({
            "title": g[0]["title"],
            "score": score,
            "confidence": "Bajo" if abstain else ("Alto" if len(sources) >= 2 else "Medio"),
            "status": "Sin evidencia" if abstain else "Priorizado",
            "sources": [{"name": x["source"], "url": x["url"]} for x in g],
            "relevance": round(rel_i, 2),
        })
    return sorted(fichas, key=lambda f: -f["score"])
