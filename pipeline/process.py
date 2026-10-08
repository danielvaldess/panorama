"""Procesamiento determinista con librerías estándar:
rank_bm25 (baseline) y rapidfuzz (dedupe/agrupación). Prioridad reproducible + abstención."""
from __future__ import annotations

import re
import urllib.parse

from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz

from pipeline import score as score_mod
from pipeline import claims
from pipeline import origin
from pipeline import theme as theme_mod

# Confiabilidad por fuente (1-5).
SOURCE_RELIABILITY = {
    "TVN Noticias": 5, "TVN": 5, "La Prensa": 5, "Telemetro": 4, "TVMax": 4,
    "Panamá América": 4, "La Estrella": 4, "Crítica": 3, "El Siglo": 3,
    "Mi Diario": 3, "Foco Panamá": 3,
    "tvn-2.com": 5, "prensa.com": 5, "telemetro.com": 4, "laestrella.com.pa": 4,
    "panamaamerica.com.pa": 4, "midiario.com": 3, "critica.com.pa": 3,
    "diaadia.com.pa": 3, "newsroompanama.com": 3, "focopanama.com": 3,
}
DEFAULT_RELIABILITY = 3

# Salidas panameñas permitidas para GDELT (evita ruido tipo "Panama City, Florida").
PA_TLD = ".pa"
PA_OUTLETS = frozenset({
    "tvn-2.com", "telemetro.com", "tvmax-9.com", "focopanama.com", "newsroompanama.com",
    "midiario.com", "prensa.com", "panamaon.com", "elsiglo.com", "laestrella.com.pa",
    "panamaamerica.com.pa", "critica.com.pa", "diaadia.com.pa", "panamacanal.com",
})

# Verificación: fuentes primarias/oficiales, agencias (cable) y señales de contradicción.
OFFICIAL_DOMAINS = {
    "gob.pa", "presidencia.gob.pa", "contraloria.gob.pa", "ine.gob.pa",
    "mop.gob.pa", "mitradel.gob.pa", "mef.gob.pa", "minsa.gob.pa",
    "meduca.gob.pa", "attt.gob.pa", "asamblea.gob.pa", "organojudicial.gob.pa",
    "tribunal-electoral.gob.pa", "panamacanal.com",
}
AGGREGATOR_DOMAINS = {"news.google.com"}
WIRE_MARKERS = ("efe", "reuters", "afp", "ap news", "dpa", "bloomberg", "acan", "notimex")
GENERIC_TITLE_PATTERNS = (
    "noticias de actualidad",
    "cultura y educación",
    "república de panamá",
    "ministerio de economía y finanzas de panamá",
    "gaceta oficial digital",
    "listado de cepadem",
    "inicio - ministerio",
    "author at ministerio",
    "zimbra web client",
    "cálculo de prestaciones",
    "calculo de prestaciones",
    "contenido exclusivo:",
    "emotiva jornada recreativa",
    "celebración carnavalera",
    "celebracion carnavalera",
    "liga de naciones",
    "concacaf resultados",
    "tras una rápida acción",
    "tras una rapida accion",
    "jay wheeler",
    "gira 'la voz favorita'",
    "josué vergara",
    "josue vergara",
    "gente tvn",
    "lpf resultado",
    "torneo apertura",
)
OFFICIAL_SOURCE_MARKERS = (
    "ministerio", "policia nacional", "policía nacional", "autoridad", "gaceta oficial",
    "meduca", "minsa", "contraloría", "contraloria", "ifaruh", "bomberos",
)
LOCAL_MARKERS = (
    "panam", "canal", "chiriquí", "chiriqui", "veraguas", "colón", "colon", "darién", "darien",
    "coclé", "cocle", "herrera", "los santos", "bocas del toro", "san miguelito", "arraiján",
    "arraijan", "la chorrera", "tumba muerto", "coiba", "azuero", "metro", "asamblea",
    "contraloría", "contraloria", "meduca", "minsa", "css", "santo tomás", "santo tomas",
    "gobierno", "presupuesto", "policía nacional", "policia nacional", "bomberos", "samer",
)
SPANISH_STOPWORDS = {"el", "la", "los", "las", "de", "del", "en", "por", "para", "con", "que", "un", "una", "al"}
ENGLISH_NOISE = {
    "workers", "after", "with", "stand", "navigation", "death", "captain", "inland",
    "first", "fountain", "generates", "drinking", "water", "humidity", "inaugurated",
}
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
    if h in AGGREGATOR_DOMAINS:
        return False
    return any(h == d or h.endswith("." + d) for d in OFFICIAL_DOMAINS)


def is_aggregator(url: str) -> bool:
    return _host(url) in AGGREGATOR_DOMAINS


def is_panamanian_outlet(url: str) -> bool:
    """¿El medio enlazado es panameño? Filtra ruido de GDELT (p. ej. Panama City, Florida)."""
    h = _host(url)
    if not h:
        return False
    if h.endswith(PA_TLD):
        return True
    return h in PA_OUTLETS or any(h.endswith("." + d) for d in PA_OUTLETS)


def is_official_source_name(source: str) -> bool:
    low = (source or "").lower()
    return any(m in low for m in OFFICIAL_SOURCE_MARKERS)


def is_editorial_signal(item: dict) -> bool:
    """Descarta páginas/índices genéricos que no son temas investigables."""
    title = (item.get("title") or "").strip()
    url = (item.get("url") or "").strip()
    source = (item.get("source") or "").strip()
    low = title.lower()
    blob = f"{title} {source}".lower()
    local_blob = blob if is_official_source_name(source) else low
    if is_aggregator(url):
        return False
    if len(tokens(title)) < 4:
        return False
    if any(p in low for p in GENERIC_TITLE_PATTERNS):
        return False
    if source and low == source.lower():
        return False
    if re.search(r"\bimg[-_ ]?\d+\b", low):
        return False
    if not any(m in local_blob for m in LOCAL_MARKERS):
        return False
    words = set(re.findall(r"[a-záéíóúñü]+", low))
    if words & ENGLISH_NOISE and len(words & SPANISH_STOPWORDS) < 2:
        return False
    return True


def filter_editorial(items: list[dict]) -> list[dict]:
    return [x for x in items if is_editorial_signal(x)]


def _is_wire(x: dict) -> bool:
    t = f'{x.get("title", "")} {x.get("source", "")}'.lower()
    return any(w in t for w in WIRE_MARKERS)


def _reliability(x: dict) -> int:
    """Confiabilidad 1–5 por nombre de medio o dominio."""
    name = (x.get("source") or "").strip()
    host = _host(x.get("url", ""))
    for k, val in SOURCE_RELIABILITY.items():
        if k.lower() == name.lower() or k == host:
            return val
    return DEFAULT_RELIABILITY


def _independent(g: list[dict]) -> int:
    """T2: nº de orígenes reales distintos (agencia/dominio) tras colapsar eco/reescrituras."""
    return origin.collapse_origins(g)


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
    rels = [_reliability(x) for x in items] or [DEFAULT_RELIABILITY]
    reliability_avg = round((sum(rels) / len(rels)) / 5.0, 2)
    trazabilidad = round(sum(1 for x in items if x.get("url")) / len(items), 2) if items else 0.0
    return {
        "state": state, "confidence": conf, "reason": reason,
        "official": len(official), "independent": indep, "echo": echo, "wire": wires > 0,
        "contradict": contradict, "reliability_avg": reliability_avg, "trazabilidad": trazabilidad,
        "origenes": sorted({origin.origen_real(x) for x in items})[:8],
    }


def priority(groups: list[list[dict]], query: list[str], ref=None) -> list[dict]:
    """Prioridad explicable (P=30R+25I+20U+15N+10E, 0–100) + verificación/evidencia.

    El puntaje y el estado de evidencia son independientes. Orden: P desc,
    empates por urgencia desc y luego ID.
    """
    reps = [g[0]["title"] for g in groups]
    rel = _norm(bm25(query, [tokens(r) for r in reps]))
    fichas = []
    for i, g in enumerate(groups):
        uniq: dict[str, dict] = {}
        for x in g:
            uniq.setdefault(x["source"], x)
        v = _verify(g)
        rel_i = rel[i] if i < len(rel) else 0.0
        tipo = claims.clasificar_afirmacion(g[0]["title"], official=bool(v["official"]),
                                            origen=g[0].get("source", ""))
        tema_baseline = score_mod._dominant_topic(g)
        tema, tema_conf, tema_cands = theme_mod.clasificar_tema(g[0]["title"])
        comp, _ = score_mod.compute_components(g, rel_i, v, tipo, tema, ref)
        p = score_mod.final_score(comp)
        pubs = [x.get("published") for x in g if x.get("published")]
        published = max(pubs) if pubs else None
        age = score_mod.edad_dias(g, ref)
        recirculada = age is not None and age > score_mod.URGENCY_WINDOW_D
        if recirculada and p > score_mod.RECIRCULADA_CAP:
            p = score_mod.RECIRCULADA_CAP  # T3: sin urgencia no puede quedar en media/alta
        fichas.append({
            "id": g[0].get("id", ""),
            "title": g[0]["title"],
            "published": published,
            "score": p,
            "band": score_mod.band(p),
            "edad_dias": round(age, 1) if age is not None else None,
            "recirculada": recirculada,
            "components": comp,
            "rules_version": score_mod.RULES_VERSION,
            "tipo_afirmacion": tipo,
            "tipo_afirmacion_label": claims.etiqueta(tipo),
            "evidence_state": score_mod.evidence_state(v, tipo),
            "evidence_reason": score_mod.evidence_reason(v, tipo),
            "evidence_flags": {"contradiccion": bool(v.get("contradict"))},
            "confidence": v["confidence"],
            "state": v["state"],
            "status": v["state"],
            "tema": tema,
            "tema_confianza": tema_conf,
            "tema_candidatos": tema_cands,
            "tema_baseline": tema_baseline,
            "verification": {
                "state": v["state"], "reason": v["reason"], "official": v["official"],
                "independent": v["independent"], "echo": v["echo"], "wire": v["wire"],
                "contradict": v.get("contradict", False),
                "reliability_avg": v.get("reliability_avg", 0.0),
                "origenes": v.get("origenes", []),
            },
            "sources": [{"name": n, "url": x["url"]} for n, x in uniq.items()],
            "relevance": round(rel_i, 2),
        })
    return sorted(fichas, key=lambda f: (-f["score"], -f["components"]["U"], f.get("id", "")))
