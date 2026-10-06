"""Métricas del pipeline (deterministas)."""
from __future__ import annotations


def summarize(raw: list[dict], deduped: list[dict], fichas: list[dict]) -> dict:
    def v(f):
        return f.get("verification") or {}
    multi = sum(1 for f in fichas if v(f).get("independent", 0) >= 2)
    single = sum(1 for f in fichas if v(f).get("independent", 0) <= 1)
    official = sum(1 for f in fichas if v(f).get("official", 0) >= 1)
    echo = sum(v(f).get("echo", 0) for f in fichas)
    unverified = sum(1 for f in fichas if f.get("state") in ("Sin verificar", "Contradicho"))
    total = len(fichas) or 1
    ev = [f.get("evidence_state", "") for f in fichas]
    bands = [f.get("band", "") for f in fichas]
    return {
        "fetched": len(raw),
        "after_dedupe": len(deduped),
        "dedupe_ratio": round(1 - len(deduped) / max(1, len(raw)), 2),
        "fichas": len(fichas),
        "multi_source": multi,
        "single_source": single,
        "official": official,
        "echo_copies": echo,
        "abstain": unverified,
        "citation_coverage": round(multi / total, 2),
        "avg_score": int(round(sum(f.get("score", 0) for f in fichas) / total)),
        "evidence_sufficient": sum(1 for x in ev if x.startswith("Suficiente")),
        "evidence_partial": sum(1 for x in ev if x == "Parcial"),
        "evidence_insufficient": sum(1 for x in ev if x == "Insuficiente"),
        "band_alto": sum(1 for b in bands if b == "alto"),
        "band_medio": sum(1 for b in bands if b == "medio"),
        "band_bajo": sum(1 for b in bands if b == "bajo"),
    }


def baseline_vs_model(queries: list[str], docs: list[list[str]], relevance: list[float]) -> dict:
    """Comparación mínima baseline (coincidencia exacta) vs BM25 (modelo).

    La rúbrica premia 'mejora o limitación medida': aquí reportamos el delta.
    """
    def exact(doc):
        return sum(1 for q in queries if q in doc) / max(1, len(queries))
    base = [exact(d) for d in docs]
    n = len(docs) or 1
    return {
        "baseline_exact_avg": round(sum(base) / n, 3),
        "model_bm25_avg": round(sum(relevance) / n, 3),
        "delta": round((sum(relevance) - sum(base)) / n, 3),
        "n": len(docs),
    }


def rank_agreement(a: list[float], b: list[float]) -> float:
    """Spearman (sin scipy): ¿coinciden el orden del baseline y el de la IA?"""
    if len(a) != len(b) or len(a) < 2:
        return 0.0

    def ranks(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0] * len(x)
        for rank, i in enumerate(order):
            r[i] = rank
        return r

    ra, rb = ranks(a), ranks(b)
    n = len(a)
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return round(1 - (6 * d2) / (n * (n * n - 1)), 2)
