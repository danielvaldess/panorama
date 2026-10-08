"""Rellena la app con decisiones y veredictos de ejemplo, como el editor "Daniel Valdés".

Lee `data/processed/fichas.jsonl` (el artefacto que evalúa el sustento) y escribe
`data/processed/revisiones.jsonl` y `data/processed/sustento_labels.jsonl`, para que la
mesa se vea en funcionamiento (demo). Es **dato de ejemplo**: en el evento se reemplaza
por la revisión humana real.

Uso: python -m pipeline.export && python scripts/seed_demo.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import store  # noqa: E402

REVIEWER = "Daniel Valdés"
TS = "2026-10-08T02:00:00+00:00"
ESTADOS = [
    "en revisión", "requiere evidencia", "aprobado como borrador", "descartado",
    "en revisión", "requiere evidencia", "aprobado como borrador", "en revisión",
    "requiere evidencia", "nuevo",
]


def main() -> int:
    path = os.path.join(ROOT, "data", "processed", "fichas.jsonl")
    fichas = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    os.makedirs(os.path.dirname(store.REVISIONES), exist_ok=True)

    n_rev = 0
    with open(store.REVISIONES, "w", encoding="utf-8") as fh:
        for i, f in enumerate(fichas[:10]):
            fh.write(json.dumps({
                "id": f["id_caso"], "state": ESTADOS[i % len(ESTADOS)],
                "note": "Revisión editorial de ejemplo (demo).", "reviewer": REVIEWER, "ts": TS,
            }, ensure_ascii=False) + "\n")
            n_rev += 1

    n_ver = 0
    with open(store.SUSTENTO, "w", encoding="utf-8") as fh:
        for f in fichas[:30]:
            for i, a in enumerate(f.get("afirmaciones") or []):
                veredicto = "válido" if (n_ver % 7 != 3) else "parcial"
                fh.write(json.dumps({
                    "id_caso": f["id_caso"], "indice": i, "veredicto": veredicto,
                    "comentario": None, "reviewer": REVIEWER, "ts": TS,
                    "texto": a.get("texto"), "tipo": a.get("tipo"),
                    "titulo_ficha": f.get("titulo"),
                }, ensure_ascii=False) + "\n")
                n_ver += 1

    print(f"revisiones: {n_rev} | veredictos: {n_ver} -> {store.REVISIONES}, {store.SUSTENTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
