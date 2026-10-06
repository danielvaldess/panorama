"""Embeddings semánticos locales (fastembed/ONNX) con *fallback* a BM25.

Capacidad NLP/ML sustantiva: similitud semántica para **agrupar eventos** y
**recuperación semántica**. Baseline comparable: BM25 (léxico) en `eval/benchmark.py`.
Corre local → costo 0 y funciona sin API.
"""
from __future__ import annotations

import os

import numpy as np

_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_CACHE = os.environ.get("FASTEMBED_CACHE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".fastembed_cache"))
_model = None
_ready: bool | None = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(_MODEL_NAME, cache_dir=_CACHE)
    return _model


def available() -> bool:
    global _ready
    if _ready is None:
        try:
            _get_model()
            _ready = True
        except Exception:
            _ready = False
    return _ready


def embed(texts: list[str]) -> np.ndarray:
    m = _get_model()
    return np.asarray(list(m.embed([t or "" for t in texts])), dtype=np.float32)


def _l2(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return v / n


def cosine_matrix(texts: list[str]) -> np.ndarray:
    v = _l2(embed(texts))
    return v @ v.T


def cluster(items: list[dict], threshold: float = 0.62) -> list[list[dict]]:
    """Agrupa por similitud semántica (coseno) — agrupa eventos, no solo copias."""
    titles = [x.get("title", "") for x in items]
    if not titles:
        return []
    sim = cosine_matrix(titles)
    groups: list[list[dict]] = []
    used = [False] * len(items)
    for i in range(len(items)):
        if used[i]:
            continue
        g = [items[i]]
        used[i] = True
        for j in range(i + 1, len(items)):
            if not used[j] and sim[i, j] >= threshold:
                g.append(items[j])
                used[j] = True
        groups.append(g)
    return groups


def retrieve(query: str, items: list[dict], topk: int = 5):
    if not items:
        return []
    sim = cosine_matrix([query] + [x.get("title", "") for x in items])
    row = sim[0, 1:]
    order = np.argsort(-row)[:topk]
    return [(items[i], float(row[i])) for i in order]
