"""Persistencia local de decisiones humanas (JSONL versionado en data/processed/).

- `revisiones.jsonl`       → veredicto del Administrador por ficha (historial append-only)
- `sustento_labels.jsonl`  → veredicto por afirmación (base de la eval ≥90%)

Degradación elegante: si el archivo no se puede leer/escribir, la API continúa
en memoria y lo reporta (`persisted: false`), sin romper el flujo.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")

REVISIONES = os.path.join(PROC, "revisiones.jsonl")
SUSTENTO = os.path.join(PROC, "sustento_labels.jsonl")


def _append(path: str, record: dict) -> bool:
    """Agrega una línea JSON al archivo. Devuelve False si no se pudo escribir."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def _load(path: str) -> list[dict]:
    """Lee todas las líneas JSON; ignora líneas corruptas. Vacío si no existe."""
    if not os.path.exists(path):
        return []
    out: list[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out


def guardar_revision(registro: dict) -> bool:
    """Persiste el veredicto del Administrador sobre una ficha."""
    return _append(REVISIONES, registro)


def cargar_revisiones() -> dict[str, dict]:
    """Último estado por ficha (gana el más reciente)."""
    por_id: dict[str, dict] = {}
    for r in _load(REVISIONES):
        if r.get("id"):
            por_id[r["id"]] = r
    return por_id


def guardar_veredicto(registro: dict) -> bool:
    """Persiste el veredicto del Administrador sobre una afirmación."""
    return _append(SUSTENTO, registro)


def cargar_veredictos() -> list[dict]:
    """Historial completo de veredictos de afirmaciones (gana el más reciente por clave)."""
    return _load(SUSTENTO)


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()
