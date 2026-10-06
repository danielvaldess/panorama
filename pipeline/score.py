"""Motor de priorización explicable del reto (determinista y versionado).

P = 30·R + 25·I + 20·U + 15·N + 10·E   (cada componente normalizado 0–1; P en 0–100)

- R  Relevancia: relación con Panamá y con los temas de la modalidad.
- I  Impacto potencial: alcance sectorial justificado con datos (no sensacionalismo).
- U  Urgencia: tiempo disponible para revisar.
- N  Novedad: diferencia frente a eventos ya agrupados (la duplicación NO incrementa).
- E  Evidencia disponible: fuentes pertinentes, primarias y con procedencia identificable.

Rangos: bajo [0,40) · medio [40,70) · alto [70,100]. Empates: mayor urgencia y luego ID.
El **estado de evidencia** es independiente del puntaje. El prototipo NO etiqueta
automáticamente una noticia como verdadera o falsa.
"""
from __future__ import annotations

from datetime import datetime, timezone

RULES_VERSION = "p-1.0"
WEIGHTS = {"R": 30, "I": 25, "U": 20, "N": 15, "E": 10}
CORE_THEMES = {"economia", "logistica", "turismo", "servicios", "eventos_naturales", "regulacion"}
URGENCY_WINDOW_H = 24 * 14  # 14 días hasta urgencia ~0


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _recency(g: list[dict]) -> float:
    """0–1 según antigüedad de la publicación más reciente del grupo."""
    best = None
    for x in g:
        p = x.get("published")
        if not p:
            continue
        try:
            dt = datetime.fromisoformat(p)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if best is None or dt > best:
                best = dt
        except Exception:
            continue
    if best is None:
        return 0.5
    age_h = (datetime.now(timezone.utc) - best).total_seconds() / 3600
    return _clamp(1.0 - age_h / URGENCY_WINDOW_H)


def _dominant_topic(g: list[dict]) -> str:
    temas = [x.get("topic") for x in g if x.get("topic")]
    return max(set(temas), key=temas.count) if temas else "general"


def compute_components(g: list[dict], rel_i: float, v: dict) -> tuple[dict, str]:
    """Devuelve (componentes 0–1, tema dominante)."""
    tema = _dominant_topic(g)
    blob = " ".join((x.get("title", "") + " " + x.get("source", "")) for x in g).lower()
    panama = "panam" in blob
    topic_base = 0.85 if tema in CORE_THEMES else 0.40

    R = _clamp(0.6 * max(rel_i, topic_base) + 0.4 * (1.0 if panama else 0.5))

    indep = v.get("independent", 0)
    indep_score = _clamp((indep - 1) / 2.0) if indep > 1 else 0.0  # 2→0.5, 3→1.0
    I = _clamp(0.40 * topic_base + 0.35 * indep_score + 0.25 * (1.0 if v.get("official") else 0.30))

    rec = _recency(g)
    U = rec
    N = _clamp(0.6 * rec + 0.4 * (1.0 / (1.0 + v.get("echo", 0))))

    if v.get("official"):
        E = 1.0
    elif indep >= 3:
        E = 0.8
    elif indep >= 2:
        E = 0.6
    elif indep == 1:
        E = 0.3
    else:
        E = 0.0

    return {"R": round(R, 2), "I": round(I, 2), "U": round(U, 2), "N": round(N, 2), "E": round(E, 2)}, tema


def final_score(components: dict) -> int:
    return int(round(sum(WEIGHTS[k] * components.get(k, 0.0) for k in WEIGHTS)))


def band(score: int) -> str:
    if score < 40:
        return "bajo"
    if score < 70:
        return "medio"
    return "alto"


def evidence_state(v: dict) -> str:
    """Estado de evidencia, independiente del puntaje."""
    if v.get("official", 0) >= 1 or v.get("independent", 0) >= 2:
        return "Suficiente para el borrador"
    if v.get("independent", 0) == 1:
        return "Parcial"
    return "Insuficiente"
