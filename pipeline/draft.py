"""Paquete editorial (modalidad TVN).

Separa **texto_al_aire** (lo que se dice en pantalla) de **notas_internas** (avisos
para el editor: estado de evidencia, límites de lectura, pendientes). El texto al
aire nunca contiene meta-mensajes internos. Atribuye las declaraciones ("Según …")
y no presenta una declaración institucional como hecho. Incluye un validador de
citas: toda afirmación debe traer fuente, campo y URL de evidencia.
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
    """Recorta a `limit` palabras **sin** puntos suspensivos (corta en palabra completa)."""
    w = (s or "").split()
    if len(w) <= limit:
        return s
    return " ".join(w[:limit]).rstrip(".,;: ")


def _claims(title: str, sources: list[dict], tipo: str = "hecho_verificable") -> list[dict]:
    ids = [s.get("name") for s in sources] or ["sin fuente"]
    urls = [s.get("url") for s in sources if s.get("url")]
    cita = urls[0] if urls else ""
    low = title.lower()
    out = [{"texto": title, "tipo": tipo, "tipo_label": claims_mod.etiqueta(tipo),
            "ids_fuente": ids[:1], "campo": "titular", "cita": cita}]
    if any(a in low for a in ATRIBUCION) and tipo != "declaracion_tercero":
        out.append({"texto": f"Existe una declaración atribuida en el titular: “{title}”",
                    "tipo": "declaracion_tercero", "tipo_label": claims_mod.etiqueta("declaracion_tercero"),
                    "ids_fuente": ids, "campo": "titular", "cita": cita})
    if len(ids) > 1:
        out.append({"texto": f"El tema circula en {len(ids)} medios", "tipo": "inferencia",
                    "tipo_label": claims_mod.etiqueta("inferencia"),
                    "ids_fuente": ids, "campo": "conteo de fuentes", "cita": cita})
    return out


def validar_citas(afirmaciones: list[dict], sources: list[dict]) -> tuple[bool, list[str]]:
    """T6.6: toda afirmación debe tener fuente, campo y URL de evidencia válida."""
    urls = {s.get("url") for s in sources if s.get("url")}
    fallos: list[str] = []
    for i, a in enumerate(afirmaciones):
        if not a.get("ids_fuente"):
            fallos.append(f"afirmación {i}: sin fuente")
        if not a.get("campo"):
            fallos.append(f"afirmación {i}: sin campo")
        if not a.get("cita") or (urls and a["cita"] not in urls):
            fallos.append(f"afirmación {i}: cita no verificable")
    return (not fallos), fallos


def _atribucion(tipo: str, fuente_txt: str) -> str:
    if tipo == "declaracion_institucional":
        return f"Según {fuente_txt},"
    if tipo == "declaracion_tercero":
        return f"{fuente_txt} informa que"
    return f"Lo reporta {fuente_txt}."


def build(ficha: dict) -> dict:
    title = ficha.get("title", "").strip()
    sources = ficha.get("sources", []) or []
    v = ficha.get("verification", {}) or {}
    ev = ficha.get("evidence_state", "Insuficiente")
    tema = ficha.get("tema", "general")
    tipo = ficha.get("tipo_afirmacion", "hecho_verificable")
    fuente_txt = ", ".join(s.get("name", "") for s in sources) or "una fuente"
    enfoque = TEMA_FOCO.get(tema, TEMA_FOCO["general"])
    titulo_corto = _fit(title, 16)

    # Qué falta comprobar (coherente con el estado; invariante T1.4)
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
              else ("enviar a revisión editorial" if ev == "Parcial"
                    else "listo para borrador con revisión humana"))

    # --- Texto al aire (sin meta-mensajes internos) ---
    atrib = _atribucion(tipo, fuente_txt)
    guion = (f"Al aire. {atrib} {titulo_corto}. "
             f"El interés público de este tema: {enfoque}. "
             f"Seguimos el desarrollo de esta información.")
    if tipo == "declaracion_institucional":
        guion = (f"Al aire. {fuente_txt} afirma: {titulo_corto}. "
                 f"Por ahora es una declaración de la propia institución. "
                 f"El interés público de este tema: {enfoque}.")
    guion = _fit(guion, 130)
    copy = _fit(f"{titulo_corto} — {atrib} {fuente_txt}.", 80)

    # --- Notas internas (para el editor) ---
    notas = [DISCLAIMER, f"Estado de evidencia: {ev}.",
             f"Antes de publicar falta comprobar: {', '.join(pendientes)}."]

    afirmaciones = _claims(title, sources, tipo)
    ok_citas, fallos = validar_citas(afirmaciones, sources)
    if not ok_citas:
        abstain = True
        accion = "abstención: citas no verificables"
        notas.append("Validador: " + "; ".join(fallos))

    preguntas = [
        f"¿Qué datos, documentos o acuerdos concretos respaldan «{_fit(title, 12)}»?",
        (f"¿Existe una fuente independiente de {fuente_txt} que confirme o matice lo afirmado?"
         if v.get("independent", 0) < 2 else
         f"¿Qué alcance tiene la información de {fuente_txt} y a quién afecta?"),
        "¿Qué otras fuentes o datos permitirían descartar la versión contraria?",
    ]

    brief = (f"{title}. {atrib} {fuente_txt}. {notas[1]} "
             f"El enfoque de interés público es {enfoque}; acción recomendada: {accion}. {DISCLAIMER}")
    brief = _fit(brief, 250)

    return {
        "titulo_propuesto": titulo_corto,
        "enfoque_interes_publico": enfoque,
        "afirmaciones": afirmaciones,
        "citas_ok": ok_citas,
        "brief": brief,
        "preguntas": preguntas,
        "texto_al_aire": {"guion": guion, "copy": copy},
        "guion_45_60s": guion,
        "copy_digital": copy,
        "notas_internas": notas,
        "verificaciones_pendientes": pendientes,
        "disclaimer": DISCLAIMER,
        "abstain": abstain,
        "accion_recomendada": accion,
    }
