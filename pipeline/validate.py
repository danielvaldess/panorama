"""Validación del paquete de datos (contrato): separa errores y conserva nulos.

No bloquea toda la carga por una fila mala (T01). Los campos opcionales pueden
venir vacíos (se conservan como nulos); los obligatorios no.
"""
from __future__ import annotations

from datetime import datetime

REQUIRED = ("id_noticia", "titulo", "url")


def validate_news(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Devuelve (filas_ok, errores). Errores incluyen fila, motivos y el registro."""
    ok: list[dict] = []
    errors: list[dict] = []
    for i, r in enumerate(rows):
        motivos: list[str] = []
        for f in REQUIRED:
            if not (str(r.get(f, "")) or "").strip():
                motivos.append(f"{f} vacío")
        fp = (str(r.get("fecha_publicacion", "")) or "").strip()
        if fp:
            try:
                datetime.fromisoformat(fp.replace("Z", "+00:00"))
            except Exception:
                motivos.append("fecha_publicacion inválida")
        if motivos:
            errors.append({"fila": i, "motivos": motivos, "registro": r})
        else:
            ok.append(r)  # nulos en campos opcionales se conservan
    return ok, errors
