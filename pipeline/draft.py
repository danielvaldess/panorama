"""Paquete editorial (modalidad TVN): afirmaciones con citas, brief, guion y copy.

Determinista y honesto: si solo hay **titular/metadatos**, lo declara y **no inventa**
hechos, entrevistas, citas ni cifras. Si la evidencia es insuficiente, **se abstiene**
y explica qué falta comprobar.
"""
from __future__ import annotations

from pipeline import claims as claims_mod

DISCLAIMER = "Basado únicamente en titular/metadatos; no se leyó el artículo completo."

TEMA_FOCO = {
    "economia": "impacto en la economía familiar y el bolsillo",
    "logistica": "operación del Canal y la logística nacional",
    "turismo": "actividad turística y su efecto económico",
    "servicios": "servicios públicos y calidad de vida",
    "eventos_naturales": "seguridad y gestión de riesgo",
    "regulacion": "marco legal y control institucional",
    "relaciones_exteriores": "posición internacional y comercio del país",
    "sin_clasificar": "interés público (tema por confirmar)",
    "general": "interés público general",
}

ATRIBUCION = ("según", "dijo", "afirmó", "anunció", "informó", "declaró", "aseguró", "advirtió")


def _words(s: str) -> int:
    return len((s or "").split())


def _fit(s: str, limit: int) -> str:
    w = (s or "").split()
    return s if len(w) <= limit else " ".join(w[:limit]).rstrip(".,;:") + "…"


def _claims(title: str, sources: list[dict], tipo: str = "hecho_verificable") -> list[dict]:
    ids = [s.get("name") for s in sources] or ["sin fuente"]
    urls = [s.get("url") for s in sources if s.get("url")]
    cita = urls[0] if urls else ""
    low = title.lower()
    claims = [{"texto": title, "tipo": tipo, "tipo_label": claims_mod.etiqueta(tipo),
               "ids_fuente": ids[:1], "campo": "titular", "cita": cita}]
    if any(a in low for a in ATRIBUCION) and tipo != "declaracion_tercero":
        claims.append({"texto": f"Existe una declaración atribuida en el titular: “{title}”",
                       "tipo": "declaracion_tercero", "tipo_label": claims_mod.etiqueta("declaracion_tercero"),
                       "ids_fuente": ids, "campo": "titular", "cita": cita})
    if len(ids) > 1:
        claims.append({"texto": f"El tema circula en {len(ids)} medios", "tipo": "inferencia",
                       "tipo_label": claims_mod.etiqueta("inferencia"),
                       "ids_fuente": ids, "campo": "conteo de fuentes", "cita": cita})
    return claims


def build(ficha: dict) -> dict:
    title = ficha.get("title", "").strip()
    sources = ficha.get("sources", []) or []
    v = ficha.get("verification", {}) or {}
    ev = ficha.get("evidence_state", "Insuficiente")
    tema = ficha.get("tema", "general")
    fuente_txt = ", ".join(s.get("name", "") for s in sources) or "sin fuente identificable"
    enfoque = TEMA_FOCO.get(tema, TEMA_FOCO["general"])

    # Qué falta comprobar — coherente con el estado de evidencia (invariante T1.4):
    # si el estado es "Suficiente", NO se pide corroboración independiente.
    pendientes: list[str] = []
    if v.get("contradict"):
        pendientes.append("contrastar las versiones que se contradicen")
    elif ev == "Suficiente para el borrador":
        pendientes.append("confirmar detalles y alcance antes de publicar")
    else:
        if v.get("independent", 0) < 2:
            pendientes.append("una segunda fuente independiente (no una copia/eco)")
        if not v.get("official") and v.get("independent", 0) >= 2:
            pendientes.append("un documento o dato oficial que respalde la afirmación")
        if not pendientes:
            pendientes.append("confirmar detalles y alcance antes de publicar")

    abstain = ficha.get("state") == "Sin verificar" or ev == "Insuficiente"
    accion = ("investigar antes de producir" if abstain
              else ("enviar a revisión editorial" if ev == "Parcial" else "listo para borrador con revisión humana"))

    ev_frase = {
        "Suficiente para el borrador": "Hay evidencia suficiente para un borrador.",
        "Parcial": "La evidencia es parcial: hay una fuente, falta corroboración.",
        "Insuficiente": "No hay evidencia suficiente para sostener la afirmación.",
    }.get(ev, "Evidencia por determinar.")

    # Brief (≤250 palabras), en prosa
    brief = (
        f"{title}. Lo reporta {fuente_txt}. {ev_frase} "
        f"Antes de publicar falta comprobar {', '.join(pendientes)}. "
        f"El enfoque de interés público es {enfoque}, por lo que la acción recomendada es {accion}. "
        f"{DISCLAIMER}"
    )
    brief = _fit(brief, 250)

    # 3 preguntas de investigación
    preguntas = [
        f"¿Cuál es la fuente primaria u oficial de “{_fit(title, 12)}”?",
        f"¿Qué actores y datos concretos sustentan la afirmación?",
        f"¿Existe una segunda fuente independiente que la corrobore o la contradiga?",
    ]

    # Guion 45–60 s (~90–130 palabras)
    guion = (
        f"Al aire. {title}. "
        f"Lo reporta {fuente_txt}. {ev_frase} "
        f"Antes de afirmarlo, verificaremos {pendientes[0]}"
        + (f" y {pendientes[1]}." if len(pendientes) > 1 else ".")
        + f" Seguimos el tema por su {enfoque}. {DISCLAIMER}"
    )
    guion = _fit(guion, 130)

    # Copy digital (≤80 palabras)
    copy = f"{title} — {fuente_txt}. {ev_frase} {DISCLAIMER}"
    copy = _fit(copy, 80)

    return {
        "titulo_propuesto": _fit(title, 16),
        "enfoque_interes_publico": enfoque,
        "afirmaciones": _claims(title, sources, ficha.get("tipo_afirmacion", "hecho_verificable")),
        "brief": brief,
        "preguntas": preguntas,
        "guion_45_60s": guion,
        "copy_digital": copy,
        "verificaciones_pendientes": pendientes,
        "disclaimer": DISCLAIMER,
        "abstain": abstain,
        "accion_recomendada": accion,
    }
