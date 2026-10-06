"""Procesamiento determinista con librerías estándar:
rank_bm25 (baseline) y rapidfuzz (dedupe/agrupación). Prioridad reproducible + abstención."""
from __future__ import annotations

import re
import urllib.parse

from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz

# Confiabilidad por fuente (1-5).
SOURCE_RELIABILITY = {
    "TVN Noticias": 5, "TVN": 5, "La Prensa": 5, "Telemetro": 4, "TVMax": 4,
    "Panamá América": 4, "La Estrella": 4, "Crítica": 3, "El Siglo": 3,
    "Mi Diario": 3, "Foco Panamá": 3, "Google News": 3,
    "tvn-2.com": 5, "prensa.com": 5, "telemetro.com": 4, "laestrella.com.pa": 4,
}
DEFAULT_RELIABILITY = 3

# Verificación: fuentes primarias/oficiales, agencias (cable) y señales de contradicción.
OFFICIAL_DOMAINS = {
    "gob.pa", "presidencia.gob.pa", "contraloria.gob.pa", "ine.gob.pa",
    "mop.gob.pa", "mitradel.gob.pa", "mef.gob.pa", "minsa.gob.pa",
    "meduca.gob.pa", "attt.gob.pa", "asamblea.gob.pa", "organojudicial.gob.pa",
    "tribunal-electoral.gob.pa", "panamacanal.com",
}
WIRE_MARKERS = ("efe", "reuters", "afp", "ap news", "dpa", "bloomberg", "acan", "notimex")
# Similitud a partir de la cual dos titulares del mismo grupo se consideran ECO (misma historia reescrita).
ECHO_SIM = 0.70
DENY_MARKERS = ("desmiente", "desmintió", "niega", "negó", "falso", "no es cierto",
                "descart", "rechaz", "desment")
CONFIRM_MARKERS = ("confirma", "confirmó", "ratifica", "ratificó", "anunció", "informó", "asegura")


def _host(url: str) -> str:
    try:
        return urllib.parse.urlparse(url or "").netloc.lower()
    except Exception:
        return ""


def is_official(url: str) -> bool:
    """¿Proviene de un dominio oficial/primario (gob.pa, Canal, etc.)?"""
    h = _host(url)
    return any(h == d or h.endswith("." + d) for d in OFFICIAL_DOMAINS)


def _is_wire(x: dict) -> bool:
    t = f'{x.get("title", "")} {x.get("source", "")}'.lower()
    return any(w in t for w in WIRE_MARKERS)


def _independent(g: list[dict]) -> int:
    """Nº de orígenes textuales distintos dentro del grupo (colapsa eco/reescrituras)."""
    origins: list[dict] = []
    for x in g:
        if not any(_sim(x["title"], o["title"]) >= ECHO_SIM for o in origins):
            origins.append(x)
    return max(1, len(origins))


def _contradiction(g: list[dict]) -> bool:
    has_deny = any(any(m in x["title"].lower() for m in DENY_MARKERS) for x in g)
    has_conf = any(any(m in x["title"].lower() for m in CONFIRM_MARKERS) for x in g)
    return has_deny and has_conf


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


def _verify(g: list[dict]) -> dict:
    """Evalúa evidencia: oficial/primaria, orígenes independientes, eco y contradicción.

    La confianza NO sube por repetir el titular en más medios (eso es eco):
    sube por prueba oficial o por orígenes realmente independientes.
    """
    uniq: dict[str, dict] = {}
    for x in g:
        uniq.setdefault(x["source"], x)
    items = list(uniq.values())  # un ítem por medio
    # oficial si CUALQUIER ítem del grupo es oficial (no solo el representante)
    official = [x for x in g if x.get("official") or is_official(x["url"])]
    indep = _independent(items)
    wires = sum(1 for x in items if _is_wire(x))
    if wires and indep > 1:
        indep -= 1  # descuenta el origen compartido de agencia
    echo = max(0, len(items) - indep)
    contradict = _contradiction(items)
    if official:
        state, conf = "Confirmado", "Alto"
        reason = "Respaldado por una fuente oficial/primaria."
    elif contradict:
        state, conf = "Contradicho", "Bajo"
        reason = "Las fuentes se contradicen (una confirma y otra desmiente)."
    elif indep >= 2 and wires == 0:
        state, conf = ("Corroborado", "Alto" if indep >= 3 else "Medio")
        reason = "Reportado por orígenes independientes entre sí."
    elif indep >= 2:
        state, conf = "Corroborado", "Medio"
        reason = "Varios orígenes, pero alguno proviene de agencia (independencia parcial)."
    else:
        state, conf = "Sin verificar", "Bajo"
        reason = "Un solo origen o copias del mismo (eco). Falta prueba independiente u oficial."
    return {
        "state": state, "confidence": conf, "reason": reason,
        "official": len(official), "independent": indep, "echo": echo, "wire": wires > 0,
    }


def priority(groups: list[list[dict]], query: list[str]) -> list[dict]:
    """Calcula prioridad (importancia) y verificación (evidencia) por separado.

    prioridad = 0.55·relevancia (BM25) + 0.30·frescura + 0.15·confiabilidad
    """
    reps = [g[0]["title"] for g in groups]
    rel = _norm(bm25(query, [tokens(r) for r in reps]))
    fichas = []
    for i, g in enumerate(groups):
        uniq: dict[str, str] = {}
        for x in g:
            uniq.setdefault(x["source"], x["url"])
        sources = sorted(uniq)
        v = _verify(g)
        rel_i = rel[i] if i < len(rel) else 0.0
        fresh = 1.0 if any(x.get("published") for x in g) else 0.5
        rels = [SOURCE_RELIABILITY.get(s, DEFAULT_RELIABILITY) for s in sources]
        if v["official"]:
            rels.append(5)  # una fuente oficial es lo más fiable
        relia = (max(rels) if rels else DEFAULT_RELIABILITY) / 5
        bonus = 0.10 if v["official"] else 0.0
        score = round(min(1.0, 0.55 * rel_i + 0.30 * fresh + 0.15 * relia + bonus), 2)
        fichas.append({
            "title": g[0]["title"],
            "score": score,
            "priority": score,
            "confidence": v["confidence"],
            "state": v["state"],
            "status": v["state"],
            "verification": {
                "state": v["state"], "reason": v["reason"], "official": v["official"],
                "independent": v["independent"], "echo": v["echo"], "wire": v["wire"],
            },
            "sources": [{"name": n, "url": u} for n, u in uniq.items()],
            "relevance": round(rel_i, 2),
        })
    return sorted(fichas, key=lambda f: -f["priority"])
