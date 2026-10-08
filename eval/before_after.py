"""Reporte antes/después (T10): la ficha del MERCOSUR con reglas v1 vs v2.

Uso: python -m eval.before_after
Genera eval/before_after.json con el estado observado v1 (documentado) y el v2 (calculado).
"""
from __future__ import annotations

import json
import os
import sys

from pipeline import context, draft, process

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MERCOSUR = {
    "title": "Panamá llega a la Cumbre del MERCOSUR como el principal conector global de la región",
    "url": "https://mire.gob.pa/nota", "source": "Ministerio de Relaciones Exteriores",
    "published": "2026-06-30T12:00:00Z", "official": True,
    "snippet": "", "topics": [], "id": "mercosur",
}

V1_OBSERVADO = {
    "evidence_state": "Suficiente para el borrador",
    "E": 1.0,
    "tema": "servicios",
    "medios_independientes": 1,
    "estado": "Confirmado",
    "prioridad": 58,
    "urgencia": 0.0,
    "marca_antiguedad": None,
    "contexto": "Uso de Internet / Población (sin relación)",
    "guion_con_meta_mensaje": True,
    "titulo_truncado": True,
}


def main() -> int:
    f = process.priority([[MERCOSUR]], ["Panamá", "Canal"])[0]
    d = draft.build(f)
    v2 = {
        "evidence_state": f["evidence_state"],
        "E": f["components"]["E"],
        "E_detalle": f["components"].get("E_detalle"),
        "tipo_afirmacion": f["tipo_afirmacion"],
        "tema": f["tema"],
        "tema_candidatos": f.get("tema_candidatos"),
        "medios_independientes": f["verification"]["independent"],
        "estado": f["state"],
        "prioridad": f["score"],
        "urgencia": f["components"]["U"],
        "recirculada": f["recirculada"],
        "edad_dias": f["edad_dias"],
        "contexto": [c["titulo"] for c in context.build(f)],
        "guion_al_aire": d["texto_al_aire"]["guion"],
        "notas_internas": d["notas_internas"],
        "titulo_propuesto": d["titulo_propuesto"],
        "pendientes": d["verificaciones_pendientes"],
    }
    out = {"caso": "MERCOSUR", "v1_observado": V1_OBSERVADO, "v2_calculado": v2}
    with open(os.path.join(ROOT, "eval", "before_after.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
