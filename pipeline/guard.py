"""Defensas del agente: el texto de una fuente es **dato**, no instrucción.

Anti-inyección (T07 y benchmark adversarial): una fuente nunca cambia reglas ni
pide revelar secretos. `sanitize` marca y neutraliza segmentos sospechosos.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignora\s+(todas\s+)?las\s+instrucciones",
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"disregard\s+(all\s+)?(previous\s+)?",
    r"revela\s+(el|los|la)\s+(secreto|token|contraseña|api\s*key)",
    r"(reveal|show)\s+(the\s+)?(secret|token|password|api\s*key|system\s*prompt)",
    r"system\s*prompt",
    r"cambia\s+(las\s+)?reglas",
    r"act[uú]a\s+como",
    r"you\s+are\s+now",
]

_FLAGS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def is_injection(text: str) -> bool:
    t = text or ""
    return any(f.search(t) for f in _FLAGS)


def sanitize(text: str) -> tuple[str, bool]:
    """Devuelve (texto_seguro, marcado). Neutraliza segmentos tipo instrucción."""
    t = text or ""
    flagged = False
    for f in _FLAGS:
        if f.search(t):
            flagged = True
            t = f.sub("[contenido no confiable omitido]", t)
    return t, flagged
