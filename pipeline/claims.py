"""Tipado de afirmaciones — baseline determinista (sin LLM).

Tipos:
- `hecho_verificable`        dato contrastable (cifra, serie oficial, sismo).
- `declaracion_institucional` la fuente oficial habla de sí misma o valora.
- `declaracion_tercero`      alguien declara (atribución en el titular).
- `inferencia`               derivado por el sistema.
- `hipotesis`                conjetura no sustentada.

Regla base (§T1): una fuente oficial **sobre sí misma** es DECLARACIÓN, no hecho
verificado. Marcadores valorativos/autorreferenciales (superlativos, "destaca",
"reafirma", "llega como") la clasifican como `declaracion_institucional`; las
cifras de series oficiales son `hecho_verificable`.
"""
from __future__ import annotations

import re

TIPOS = (
    "hecho_verificable",
    "declaracion_institucional",
    "declaracion_tercero",
    "inferencia",
    "hipotesis",
)

SUPERLATIVOS = (
    "principal", "mejor", "líder", "lider", "histórico", "historico", "récord", "record",
    "mayor", "primero", "puntero", "clave", "único", "unico", "referente",
)
AUTORREF = (
    "destaca", "reafirma", "llega como", "se posiciona", "consolida", "impulsa",
    "promueve", "celebra", "ratifica", "garantiza", "subraya", "exhibe", "presume",
)
ATRIBUCION = (
    "según", "dijo", "afirmó", "informó", "declaró", "aseguró", "advirtió",
    "sostuvo", "señaló", "manifestó",
)
UNIDADES = ("%", "por ciento", "millones", "mil millones", "habitantes", "dólares", "dolares")


def clasificar_afirmacion(titulo: str, *, official: bool = False, origen: str = "") -> str:
    """Clasifica el tipo de afirmación del titular (baseline por reglas)."""
    low = (titulo or "").lower()
    if official:
        if any(s in low for s in SUPERLATIVOS) or any(v in low for v in AUTORREF):
            return "declaracion_institucional"
        if re.search(r"\d", low) and any(u in low for u in UNIDADES):
            return "hecho_verificable"
        # Fuente oficial sobre su propia actuación: es declaración, no hecho verificado.
        return "declaracion_institucional"
    if any(m in low for m in ATRIBUCION):
        return "declaracion_tercero"
    return "hecho_verificable"


ETIQUETA = {
    "hecho_verificable": "hecho verificable",
    "declaracion_institucional": "declaración institucional",
    "declaracion_tercero": "declaración de tercero",
    "inferencia": "inferencia",
    "hipotesis": "hipótesis",
}


def etiqueta(tipo: str) -> str:
    return ETIQUETA.get(tipo, tipo)
