"""Procedencia real de la información (T2).

`origen_real` deduce la procedencia: agencia/cable (por marcadores o dominio) o el
dominio raíz del medio. `collapse_origins` cuenta orígenes distintos colapsando por
(a) mismo origen real, (b) similitud semántica (embeddings) >= umbral o (c) RapidFuzz
como respaldo. Mantiene `collapse_baseline` (solo RapidFuzz 0.70) para comparar.
"""
from __future__ import annotations

import re
import urllib.parse

from rapidfuzz import fuzz

from pipeline import embed

AGENCY_MARKERS = (
    "efe", "afp", "reuters", "ap news", "dpa", "bloomberg", "notimex", "acan",
    "con información de", "con informacion de", "redacción/ agencias", "redaccion/ agencias",
    "agencias",
)
ECHO_SIM = 0.70          # umbral léxico (baseline)
SEM_THRESHOLD = 0.72     # umbral semántico (embeddings)


def _host(url: str) -> str:
    try:
        return urllib.parse.urlparse(url or "").netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _sim(a: str, b: str) -> float:
    return fuzz.token_set_ratio(a, b) / 100.0


def origen_real(item: dict) -> str:
    """Agencia/cable detectada, o dominio raíz del medio."""
    blob = f'{item.get("title", "")} {item.get("source", "")}'.lower()
    for a in AGENCY_MARKERS:
        if re.search(rf"(?:^|\W){re.escape(a)}(?:\W|$)", blob):
            return f"agencia:{a}"
    return _host(item.get("url", "")) or (item.get("source") or "sin-origen").strip().lower()


def _collapse(items: list[dict], same_as_rep) -> int:
    reps: list[dict] = []
    for x in items:
        if any(same_as_rep(x, r) for r in reps):
            continue
        reps.append(x)
    return max(1, len(reps))


def collapse_baseline(items: list[dict]) -> int:
    """Baseline: solo similitud léxica (RapidFuzz >= 0.70)."""
    return _collapse(items, lambda x, r: _sim(x["title"], r["title"]) >= ECHO_SIM)


def collapse_origins(items: list[dict], threshold: float = SEM_THRESHOLD) -> int:
    """T2: colapsa por mismo origen real o similitud semántica (o léxica si no hay embeddings)."""
    def same(x, r):
        if origen_real(x) == origen_real(r):
            return True
        if embed.available():
            try:
                m = embed.cosine_matrix([r["title"], x["title"]])
                return float(m[0, 1]) >= threshold
            except Exception:
                pass
        return _sim(x["title"], r["title"]) >= ECHO_SIM

    return _collapse(items, same)
