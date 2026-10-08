"""Eval de sustento de afirmaciones — rúbrica del reto (meta ≥90%).

El Administrador revisa afirmaciones de las fichas y da un veredicto por una:
- **válido**   → la fuente citada respalda la afirmación tal cual se enuncia
- **parcial**  → la fuente respalda solo parte (NO cuenta para la meta)
- **inválido** → la fuente no respalda o la afirmación no tiene proposición factual (NO cuenta)

Rúbrica estricta: `pct_validos = válidos / total ≥ 0.90`, sobre ≥30 afirmaciones
de ≥10 fichas distintas. Los veredictos viven en `data/processed/sustento_labels.jsonl`
(capta la UI: POST /api/claims/verdict).

Uso:
    python -m eval.sustento                # calcula, imprime y merge en eval/quality.json
    python -m eval.sustento --pendientes   # qué afirmaciones faltan por veredicto
"""
from __future__ import annotations

import json
import os
import sys

from pipeline import db, store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MIN_AFIRMACIONES = 30
MIN_FICHAS = 10
META = 0.90
VALIDO = "válido"


def _ensure_store() -> None:
    """Permite ejecutar la métrica fuera del servidor FastAPI."""
    conn = db.ensure_ready()
    db.migrate_legacy(conn)

RUBRICA = {
    "válido": "la fuente citada respalda la afirmación tal cual se enuncia (con proposición factual real)",
    "parcial": "la fuente respalda solo parte de la afirmación — NO cuenta para la meta",
    "inválido": "la fuente no respalda, o la afirmación es vacía/genérica sin hecho verificable — NO cuenta",
}


def cargar_etiquetas() -> list[dict]:
    """Veredictos registrados (UI o API); gana el último por (id_caso, indice)."""
    _ensure_store()
    ultimo: dict[tuple, dict] = {}
    for e in store.cargar_veredictos():
        k = (e.get("id_caso"), e.get("indice"))
        if e.get("id_caso") is not None and e.get("indice") is not None:
            ultimo[k] = e
    return list(ultimo.values())


def _mapa_actuales() -> dict[tuple, str]:
    """(id_caso, indice) -> texto vigente en data/processed/fichas.jsonl (vacío si no existe)."""
    path = os.path.join(ROOT, "data", "processed", "fichas.jsonl")
    out: dict[tuple, str] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            f = json.loads(line)
            for i, c in enumerate(f.get("afirmaciones") or []):
                out[(f.get("id_caso"), i)] = c.get("texto") or ""
    return out


def calcular(etiquetas: list[dict] | None = None) -> dict:
    """Resumen de la revisión humana: numerador/denominador, meta y fallos."""
    etqs = cargar_etiquetas() if etiquetas is None else etiquetas
    # Validez de la muestra: solo cuentan veredictos sobre la afirmación vigente
    actuales = _mapa_actuales()
    descartadas = 0
    if actuales:
        validas: list[dict] = []
        for e in etqs:
            k = (e.get("id_caso"), e.get("indice"))
            if k in actuales and (e.get("texto") or "") == actuales[k]:
                validas.append(e)
            else:
                descartadas += 1
        etqs = validas
    total = len(etqs)
    validos = sum(1 for e in etqs if e.get("veredicto") == VALIDO)
    fichas = len({e.get("id_caso") for e in etqs})
    pct = round(validos / total, 4) if total else None
    suficiente = total >= MIN_AFIRMACIONES and fichas >= MIN_FICHAS
    fallos = sorted(
        ({"id_caso": e.get("id_caso"), "indice": e.get("indice"), "veredicto": e.get("veredicto"),
          "texto": e.get("texto"), "tipo": e.get("tipo"), "comentario": e.get("comentario"),
          "titulo_ficha": e.get("titulo_ficha")}
         for e in etqs if e.get("veredicto") != VALIDO),
        key=lambda x: (x["id_caso"] or "", x["indice"] or 0),
    )
    return {
        "descripcion": "Validez de sustento de afirmaciones (revisión humana, rúbrica estricta)",
        "fuente_datos": "data/processed/sustento_labels.jsonl",
        "numerador_validos": validos,
        "denominador": total,
        "pct_validos": pct,
        "meta_pct": META,
        "cumple_meta": bool(suficiente and pct is not None and pct >= META),
        "muestra": {"min_afirmaciones": MIN_AFIRMACIONES, "min_fichas": MIN_FICHAS,
                    "afirmaciones": total, "fichas": fichas, "suficiente": suficiente,
                    "etiquetas_descartadas_cambiadas": descartadas},
        "rubrica": RUBRICA,
        "fallos": fallos,
    }


def merge_quality(resumen: dict) -> None:
    """Escribe/actualiza la clave 'sustento' en eval/quality.json sin tocar el resto."""
    path = os.path.join(ROOT, "eval", "quality.json")
    out: dict = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                out = json.load(fh)
        except (OSError, json.JSONDecodeError):
            out = {}
    out["sustento"] = resumen
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)


def pendientes() -> dict:
    """Afirmaciones de data/processed/fichas.jsonl sin veredicto."""
    _ensure_store()
    labeled = {(e.get("id_caso"), e.get("indice")) for e in cargar_etiquetas()}
    path = os.path.join(ROOT, "data", "processed", "fichas.jsonl")
    pend: list[dict] = []
    total = 0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                f = json.loads(line)
                for i, _ in enumerate(f.get("afirmaciones") or []):
                    total += 1
                    if (f.get("id_caso"), i) not in labeled:
                        pend.append({"id_caso": f.get("id_caso"), "indice": i,
                                     "titulo_ficha": f.get("titulo")})
    return {"total_afirmaciones": total, "veredictadas": len(labeled),
            "pendientes": len(pend), "detalle": pend}


def main() -> int:
    if "--pendientes" in sys.argv:
        print(json.dumps(pendientes(), ensure_ascii=False, indent=2))
        return 0
    resumen = calcular()
    merge_quality(resumen)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(f"\nmerge -> eval/quality.json (clave 'sustento')", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
