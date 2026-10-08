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

import math
from datetime import datetime, timezone

RULES_VERSION = "p-2.1"
WEIGHTS = {"R": 30, "I": 25, "U": 20, "N": 15, "E": 10}
CORE_THEMES = {"economia", "logistica", "turismo", "servicios", "eventos_naturales", "regulacion", "relaciones_exteriores"}
URGENCY_WINDOW_D = 14          # días: más allá, urgencia 0 (T3)
TAU_D = 7.0                    # constante de decaimiento (documentada)
RECIRCULADA_CAP = 39           # tope de prioridad para noticias fuera de ventana (T3)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _ref_dt(ref) -> datetime:
    """Fecha de referencia de la edición (por defecto, ahora)."""
    if ref is None:
        return datetime.now(timezone.utc)
    if isinstance(ref, str):
        dt = datetime.fromisoformat(ref)
    else:
        dt = ref
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def edad_dias(g: list[dict], ref=None) -> float | None:
    """Antigüedad en días desde la publicación más reciente del grupo (None si no hay fecha).

    `ref` permite medir contra la **fecha de la edición** del snapshot (fecha más
    reciente del dataset) en lugar del reloj, para un paquete congelado.
    """
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
        return None
    return (_ref_dt(ref) - best).total_seconds() / 86400


def _recency(g: list[dict], ref=None) -> float:
    """Urgencia 0–1 con decaimiento exponencial (T3): U = exp(-edad/τ), 0 si edad > ventana."""
    age = edad_dias(g, ref)
    if age is None or age > URGENCY_WINDOW_D:
        return 0.0
    return _clamp(math.exp(-age / TAU_D))


def _dominant_topic(g: list[dict]) -> str:
    temas = [x.get("topic") for x in g if x.get("topic")]
    return max(set(temas), key=temas.count) if temas else "general"


def compute_components(g: list[dict], rel_i: float, v: dict, tipo: str = "hecho_verificable",
                       tema: str | None = None, ref=None) -> tuple[dict, str]:
    """Devuelve (componentes 0–1, tema dominante).

    E (evidencia v2, continua): una fuente oficial sobre sí misma es **declaración**,
    no hecho verificado; sin corroboración independiente no basta para "suficiente".
    """
    if tema is None:
        tema = _dominant_topic(g)
    blob = " ".join((x.get("title", "") + " " + x.get("source", "")) for x in g).lower()
    panama = "panam" in blob
    topic_base = 0.85 if tema in CORE_THEMES else 0.40

    R = _clamp(0.6 * max(rel_i, topic_base) + 0.4 * (1.0 if panama else 0.5))

    indep = v.get("independent", 0)
    indep_score = _clamp((indep - 1) / 2.0) if indep > 1 else 0.0  # 2→0.5, 3→1.0
    I = _clamp(0.40 * topic_base + 0.35 * indep_score + 0.25 * (1.0 if v.get("official") else 0.30))

    rec = _recency(g, ref)
    U = rec
    N = _clamp(0.6 * rec + 0.4 * (1.0 / (1.0 + v.get("echo", 0))))

    # --- Evidencia v2: E = 0.35·primaria + 0.40·corroboración + 0.15·confiabilidad + 0.10·trazabilidad − 0.30·contradicción
    primaria = 1.0 if (v.get("official") and tipo == "hecho_verificable") else (0.5 if v.get("official") else 0.0)
    corroboracion = _clamp(min(max(indep - 1, 0), 2) / 2.0)
    confiabilidad = _clamp(v.get("reliability_avg", 0.6))
    trazabilidad = _clamp(v.get("trazabilidad", 1.0))
    contradiccion = 1.0 if v.get("contradict") else 0.0
    E = _clamp(0.35 * primaria + 0.40 * corroboracion + 0.15 * confiabilidad + 0.10 * trazabilidad
               - 0.30 * contradiccion)
    detalle = {"primaria": round(primaria, 2), "corroboracion": round(corroboracion, 2),
               "confiabilidad": round(confiabilidad, 2), "trazabilidad": round(trazabilidad, 2),
               "contradiccion": round(contradiccion, 2)}

    return ({"R": round(R, 2), "I": round(I, 2), "U": round(U, 2), "N": round(N, 2),
             "E": round(E, 2), "E_detalle": detalle}, tema)


def final_score(components: dict) -> int:
    return int(round(sum(WEIGHTS[k] * components.get(k, 0.0) for k in WEIGHTS)))


def band(score: int) -> str:
    if score < 40:
        return "bajo"
    if score < 70:
        return "medio"
    return "alto"


def evidence_state(v: dict, tipo: str = "hecho_verificable") -> str:
    """Estado de evidencia v2 (independiente del puntaje).

    Invariante: si falta corroboración independiente, el estado es "Parcial";
    nunca "Suficiente" con una fuente oficial que solo se declara a sí misma.
    """
    if v.get("contradict"):
        return "Parcial"                      # contradicción -> revisar, no escoger
    if v.get("independent", 0) >= 2:
        return "Suficiente para el borrador"  # corroboración independiente
    if v.get("official", 0) >= 1 and tipo == "hecho_verificable":
        return "Suficiente para el borrador"  # hecho verificable con fuente primaria
    if v.get("official", 0) >= 1:
        return "Parcial"                      # declaración institucional sin corroboración
    if v.get("independent", 0) == 1:
        return "Parcial"
    return "Insuficiente"


def evidence_reason(v: dict, tipo: str = "hecho_verificable") -> str:
    if v.get("contradict"):
        return "Las fuentes se contradicen; hay que mostrar ambas versiones."
    if v.get("independent", 0) >= 2:
        return "Reportado por orígenes independientes entre sí."
    if v.get("official", 0) >= 1 and tipo == "hecho_verificable":
        return "Dato verificable respaldado por una fuente primaria/oficial."
    if v.get("official", 0) >= 1:
        return "Declaración de una fuente oficial sobre sí misma; falta corroboración independiente."
    if v.get("independent", 0) == 1:
        return "Un solo origen; falta una segunda fuente independiente."
    return "Sin evidencia suficiente."
