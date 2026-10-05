"""Procesamiento determinista: dedupe, relevancia (BM25 baseline), prioridad,
cluster de fuentes (citas), confianza y abstención."""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

# Confiabilidad por fuente (1-5). Ampliable desde el catálogo.
SOURCE_RELIABILITY = {
    "TVN Noticias": 5, "La Prensa": 5, "Telemetro": 4, "La Estrella": 4,
    "tvn-2.com": 5, "prensa.com": 4, "telemetro.com": 4, "laestrella.com.pa": 4,
}
DEFAULT_RELIABILITY = 3


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-záéíóúñü0-9]{3,}", (s or "").lower())


def bm25(query: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in docs) / n or 1.0
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    scores = []
    for d in docs:
        dl = len(d) or 1
        tf: dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for q in query:
            if q not in tf:
                continue
            idf = math.log(1 + (n - df.get(q, 0) + 0.5) / (df.get(q, 0) + 0.5))
            s += idf * (tf[q] * (k1 + 1)) / (tf[q] + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def _norm(vals: list[float]) -> list[float]:
    mx = max(vals) if vals else 0.0
    return [v / mx if mx > 0 else 0.0 for v in vals]


def dedupe(items: list[dict], threshold: float = 0.72) -> list[dict]:
    """Quita títulos casi idénticos (misma noticia republicada)."""
    kept: list[dict] = []
    for it in items:
        t = it["title"].lower()
        if any(SequenceMatcher(None, t, k["title"].lower()).ratio() >= threshold for k in kept):
            continue
        kept.append(it)
    return kept


def cluster(items: list[dict], threshold: float = 0.55) -> list[list[dict]]:
    """Agrupa la misma historia contada por varias fuentes (para citas/confianza)."""
    groups: list[list[dict]] = []
    for it in items:
        t = it["title"].lower()
        for g in groups:
            if SequenceMatcher(None, t, g[0]["title"].lower()).ratio() >= threshold:
                g.append(it)
                break
        else:
            groups.append([it])
    return groups


def priority(groups: list[list[dict]], query: list[str]) -> list[dict]:
    """Prioridad reproducible: 0.55·relevancia + 0.30·frescura + 0.15·confiabilidad."""
    reps = [g[0]["title"] for g in groups]
    rel = _norm(bm25(query, [tokens(r) for r in reps]))
    fichas = []
    for i, g in enumerate(groups):
        sources = sorted({x["source"] for x in g})
        rel_i = rel[i] if i < len(rel) else 0.0
        fresh = 1.0 if any(x.get("published") for x in g) else 0.5
        relia = max(SOURCE_RELIABILITY.get(s, DEFAULT_RELIABILITY) for s in sources) / 5
        score = round(0.55 * rel_i + 0.30 * fresh + 0.15 * relia, 2)
        conf = "Alto" if len(sources) >= 2 else "Medio"
        abstain = not sources or all(not x["url"] for x in g)
        fichas.append({
            "title": g[0]["title"],
            "score": score,
            "confidence": "Bajo" if abstain else conf,
            "status": "Sin evidencia" if abstain else "Priorizado",
            "sources": [{"name": x["source"], "url": x["url"]} for x in g],
            "relevance": round(rel_i, 2),
        })
    return sorted(fichas, key=lambda f: -f["score"])
