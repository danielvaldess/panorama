"""Clasificación temática híbrida v2 (Fase 2).

Taxonomía alineada a `data/taxonomy.yaml`: temas en alcance del reto + temas fuera de
alcance (existen pero no compiten en la mesa principal) + `sin_clasificar_con_certeza`
cuando la confianza es baja. Devuelve además `fuera_de_alcance` y `sensible`.

Método: reglas estrictas por tema (no basta "Panamá"/"Colón"/"Panamá Oeste") →
embeddings multilingües → LLM como desempatador (opcional).
"""
from __future__ import annotations

import numpy as np

from pipeline import embed

UMBRAL = 0.30

TEMA_EN_ALCANCE = {
    "economia", "logistica_canal", "turismo", "servicios_publicos",
    "eventos_naturales", "regulacion", "relaciones_exteriores_comercio",
}
TEMA_FUERA_ALCANCE = {
    "deportes", "entretenimiento_cultura", "sucesos_judicial", "politica_interna_general", "otros",
}

DESCRIPCIONES = {
    "economia": "economía, presupuesto, inflación, empleo, precios, crédito, PIB, FMI",
    "logistica_canal": "Canal de Panamá, puertos, esclusas, buques, contenedores, carga, aduanas, Zona Libre, ACP",
    "turismo": "turismo, cruceros, hoteles, vuelos, visitantes",
    "servicios_publicos": "salud, transporte público, agua, energía, educación pública",
    "eventos_naturales": "sismos, lluvias, inundaciones, protección civil, simulacros de evacuación",
    "regulacion": "leyes, decretos, contratos, licitaciones, tribunales, Asamblea",
    "relaciones_exteriores_comercio": "diplomacia, cancillería, comercio exterior, tratados, cumbres",
    "deportes": "fútbol, selección, torneos, amistosos, liga, goleador",
    "entretenimiento_cultura": "conciertos, artistas, espectáculos, gira, cultura",
    "sucesos_judicial": "aprehensiones, investigaciones, audiencias penales, operativos policiales",
    "politica_interna_general": "política interna no sectorial, partidos, campañas",
    "otros": "todo lo demás sin tema claro",
}

# Reglas estrictas (el orden importa: primero lo específico/sensible/fuera de alcance).
REGLAS = {
    "sucesos_judicial": ["aprehend", "detenid", "audiencia", "operación antidrogas", "operativo policial",
                          "presunta violación", "investigado por", "homicidio", "incauta", "violación"],
    "entretenimiento_cultura": ["concierto", "canta", "gira", "artista", "espectáculo", "show", "festival",
                                 "encender la candela", "estreno musical"],
    "deportes": ["selección de panamá", "amistoso", "premundial", "goleador", "liga de fútbol", "torneo de béisbol",
                  "amistosos ante", "beisbol", "béisbol"],
    "logistica_canal": ["canal de panamá", "esclusas", "buques", "contenedores", "zona libre", "acp",
                         "aduanas", "calado", "carga portuaria", "tránsito por el canal"],
    "relaciones_exteriores_comercio": ["mercosur", "relaciones exteriores", "cancillería", "tratado", "cumbre",
                                        "comercio exterior", "diplomaci", "embajad"],
    "eventos_naturales": ["simulacro", "evacuación", "protección civil", "sinaproc", "sismo", "terremoto",
                           "inundación", "sequía", "huracán"],
    "regulacion": ["licitación", "contrato público", "corte suprema", "tribunal electoral", "decreto",
                    "reforma al código electoral", "asamblea nacional"],
    "economia": ["economía", "inflación", "desempleo", "pib", "fmi", "crédito", "canasta básica", "presupuesto"],
    "turismo": ["turismo", "turistas", "crucero", "hoteles", "temporada alta", "visitantes"],
    "servicios_publicos": ["transporte público", "hospital", "salud pública", "agua potable", "energía eléctrica",
                            "apagones", "metro", "escuelas", "educación pública", "personas con ela", "censo de personas"],
    "politica_interna_general": ["presidente de la república", "diputado", "partido político", "campaña electoral"],
}

SENSIBLE_MARCADORES = (
    "violación", "violacion", "abuso sexual", "menor de edad", "suicidio", "femicidio", "asesinato",
    "presunta violación", "acusado de", "detenido por",
)

ORDEN = ["sucesos_judicial", "entretenimiento_cultura", "deportes", "logistica_canal",
         "relaciones_exteriores_comercio", "eventos_naturales", "regulacion", "economia",
         "turismo", "servicios_publicos", "politica_interna_general", "otros"]


def es_sensible(texto: str) -> bool:
    low = (texto or "").lower()
    return any(m in low for m in SENSIBLE_MARCADORES)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _ml(titulo: str, descripcion: str = "") -> tuple[str, float, list[dict]] | None:
    if not embed.available():
        return None
    try:
        names = list(DESCRIPCIONES.keys())
        texto = (titulo + " " + descripcion).strip()
        m = embed.cosine_matrix([texto] + list(DESCRIPCIONES.values()))
        sims = np.asarray(m[0, 1:], dtype=np.float32)
        probs = _softmax(sims * 6.0)
        order = np.argsort(-probs)
        top = int(order[0])
        cands = [{"tema": names[int(i)], "score": round(float(probs[int(i)]), 2)} for i in order[:2]]
        return names[top], round(float(probs[top]), 2), cands
    except Exception:
        return None


def clasificar_tema(titulo: str, descripcion: str = "", threshold: float = UMBRAL
                    ) -> tuple[str, float, list[dict], str, bool, bool]:
    """Devuelve (tema, confianza, candidatos, metodo, fuera_de_alcance, sensible)."""
    blob = (titulo + " " + descripcion).lower()
    sensible = es_sensible(blob)
    for tema in ORDEN:
        if any(k in blob for k in REGLAS.get(tema, [])):
            fuera = tema in TEMA_FUERA_ALCANCE
            return tema, 0.65, [{"tema": tema, "score": 0.65}], "regla", fuera, sensible

    ml = _ml(titulo, descripcion)
    if ml:
        tema, conf, cands = ml
        if conf >= threshold:
            fuera = tema in TEMA_FUERA_ALCANCE
            return tema, conf, cands, "embedding", fuera, sensible
        return "sin_clasificar_con_certeza", conf, cands, "embedding", False, sensible
    return "sin_clasificar_con_certeza", 0.3, [{"tema": "otros", "score": 0.3}], "regla", False, sensible


def clasificar_temas(titulos: list[str], descripciones: list[str] | None = None
                     ) -> list[tuple[str, float, list[dict], str, bool, bool]]:
    descs = descripciones or [""] * len(titulos)
    return [clasificar_tema(t, d) for t, d in zip(titulos, descs)]


ETIQUETA = {
    "economia": "Economía",
    "logistica_canal": "Logística / Canal",
    "turismo": "Turismo",
    "servicios_publicos": "Servicios públicos",
    "eventos_naturales": "Eventos naturales",
    "regulacion": "Regulación",
    "relaciones_exteriores_comercio": "Relaciones exteriores / comercio",
    "deportes": "Deportes",
    "entretenimiento_cultura": "Entretenimiento / cultura",
    "sucesos_judicial": "Sucesos / judicial",
    "politica_interna_general": "Política interna",
    "otros": "Otros",
    "sin_clasificar_con_certeza": "Sin clasificar con certeza",
    "general": "General",
}
