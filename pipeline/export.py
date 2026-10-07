"""Exporta artefactos del contrato de datos:
- data/processed/fichas.jsonl   (id_caso, modalidad, ids_fuente, afirmaciones, citas, puntaje, componentes, estado_evidencia, borrador, estado_revision)
- data/fuentes.json             (catálogo de fuentes con licencia)

Uso: python -m pipeline.export
"""
from __future__ import annotations

import json
import os

from pipeline import snapshot, process, draft, context, sources, embed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")

TOPICS = ["Panamá", "economía", "presupuesto", "Canal", "seguridad", "salud", "Asamblea"]


def build_fichas(limit: int = 80) -> list[dict]:
    raw = process.filter_editorial(snapshot.load_news())
    if embed.available():
        try:
            groups = embed.cluster(raw, threshold=0.72)
        except Exception:
            groups = process.cluster(raw)
    else:
        groups = process.cluster(raw)
    fichas = process.priority(groups, TOPICS)[:limit]
    out = []
    for f in fichas:
        d = draft.build(f)
        f["draft"] = d
        f["contexto"] = context.build(f)
        out.append({
            "id_caso": f["id"],
            "modalidad": "editorial",
            "titulo": f["title"],
            "tema": f.get("tema"),
            "ids_fuente": [s["name"] for s in f["sources"]],
            "afirmaciones": d["afirmaciones"],
            "citas": [s["url"] for s in f["sources"]],
            "puntaje": f["score"],
            "componentes": f["components"],
            "estado_evidencia": f["evidence_state"],
            "contexto_oficial": f["contexto"],
            "borrador": {"titulo": d["titulo_propuesto"], "brief": d["brief"],
                         "guion": d["guion_45_60s"], "copy": d["copy_digital"],
                         "preguntas": d["preguntas"], "disclaimer": d["disclaimer"]},
            "estado_revision": "nuevo",
        })
    return out


def fuentes_catalogo() -> list[dict]:
    return [{"nombre": s["nombre"], "url": s["url"], "tipo": s["tipo"],
             "confiabilidad": s["confiabilidad"], "licencia": s["licencia"]}
            for s in sources.CHALLENGE_SOURCES]


def main() -> int:
    os.makedirs(PROC, exist_ok=True)
    fichas = build_fichas()
    with open(os.path.join(PROC, "fichas.jsonl"), "w", encoding="utf-8") as fh:
        for f in fichas:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    with open(os.path.join(ROOT, "data", "fuentes.json"), "w", encoding="utf-8") as fh:
        json.dump(fuentes_catalogo(), fh, ensure_ascii=False, indent=2)
    print(f"fichas.jsonl: {len(fichas)} | fuentes.json: {len(fuentes_catalogo())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
