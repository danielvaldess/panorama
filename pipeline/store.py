"""Persistencia de decisiones humanas (append-only) en la base SQLite operativa.

- `revision`   → veredicto del Administrador sobre una ficha (historial)
- `veredicto`  → veredicto por afirmación (base de la eval ≥90%)

Viven en la tabla `decisiones` (SOLO INSERT: los triggers bloquean UPDATE/DELETE).
Degradación elegante: si la DB no está inicializada, la API continúa en memoria y
lo reporta (`persisted: false`), sin romper el flujo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pipeline import db


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def guardar_revision(registro: dict) -> bool:
    """Persiste el veredicto del Administrador sobre una ficha (append-only)."""
    conn = db.connection()
    if conn is None:
        return False
    try:
        db.add_decision(conn, "revision", registro.get("reviewer"), registro.get("note"),
                        registro.get("ts"), registro.get("id"), registro)
        return True
    except Exception:
        return False


def cargar_revisiones() -> dict[str, dict]:
    """Último estado por ficha (gana el más reciente)."""
    conn = db.connection()
    if conn is None:
        return {}
    por_id: dict[str, dict] = {}
    for d in db.list_decisiones(conn, "revision"):
        p = d.get("payload") or {}
        rid = p.get("id") or d.get("ficha_id")
        if rid:
            por_id[rid] = p
    return por_id


def guardar_veredicto(registro: dict) -> bool:
    """Persiste el veredicto del Administrador sobre una afirmación (append-only)."""
    conn = db.connection()
    if conn is None:
        return False
    try:
        db.add_decision(conn, "veredicto", registro.get("reviewer"), registro.get("comentario"),
                        registro.get("ts"), registro.get("id_caso"), registro)
        return True
    except Exception:
        return False


def cargar_veredictos() -> list[dict]:
    """Historial completo de veredictos de afirmaciones (orden de inserción)."""
    conn = db.connection()
    if conn is None:
        return []
    return [d.get("payload") or {} for d in db.list_decisiones(conn, "veredicto")]
