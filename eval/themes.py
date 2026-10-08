"""Comparación de clasificación temática (T4): baseline por palabras clave vs embeddings.

Set etiquetado a mano (sintético). Reporta macro-F1 con numerador/denominador.

Uso: python -m eval.themes
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

from pipeline import theme
from pipeline.ingest import _tema as tema_kw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LABELED = [
    ("Sube el precio de la canasta básica en Panamá", "economia"),
    ("El PIB de Panamá crecerá 4% este año, proyecta el MEF", "economia"),
    ("Aumenta el desempleo en la ciudad de Colón", "economia"),
    ("Gobierno presenta el presupuesto general del Estado 2027", "economia"),
    ("Canal de Panamá amplía los cupos de tránsito para buques", "logistica_canal"),
    ("Puerto de Balboa rompe récord de movimiento de contenedores", "logistica_canal"),
    ("Nueva naviera inicia operaciones en aguas panameñas", "logistica_canal"),
    ("Tránsito de carga por el Canal crece en el primer trimestre", "logistica_canal"),
    ("Temporada de cruceros traerá más turistas a Bocas del Toro", "turismo"),
    ("Hoteles reportan alta ocupación en la temporada alta", "turismo"),
    ("Nueva conexión aérea conecta Panamá con Colombia", "turismo"),
    ("El turismo aporta más al PIB nacional este año", "turismo"),
    ("Fuerte lluvia provoca inundaciones en Chiriquí", "eventos_naturales"),
    ("Sismo de magnitud 4.2 se siente en la provincia de Darién", "eventos_naturales"),
    ("Alerta por lluvias y tormentas eléctricas en varias regiones", "eventos_naturales"),
    ("Sequía afecta el nivel de los lagos del Canal", "eventos_naturales"),
    ("La Asamblea debate una nueva ley de contrataciones", "regulacion"),
    ("Tribunal Electoral reglamenta las próximas elecciones", "regulacion"),
    ("Decreto regula el uso del agua en la cuenca del Canal", "regulacion"),
    ("La Corte Suprema admite demanda contra una ley", "regulacion"),
    ("Metro de Panamá amplía su horario de operación", "servicios_publicos"),
    ("Corte de agua afecta a varios sectores de la capital", "servicios_publicos"),
    ("Hospital Santo Tomás refuerza sus servicios de urgencia", "servicios_publicos"),
    ("Fallas eléctricas dejan sin luz a barrios de Arraiján", "servicios_publicos"),
    ("Panamá llega a la Cumbre del MERCOSUR como el principal conector global de la región", "relaciones_exteriores_comercio"),
    ("La Cancillería firma un tratado de comercio exterior con la Unión Europea", "relaciones_exteriores_comercio"),
    ("Panamá y Costa Rica revisan acuerdos diplomáticos", "relaciones_exteriores_comercio"),
    ("El país amplía su comercio exterior con Asia", "relaciones_exteriores_comercio"),
    ("Embajada de Panamá inaugura nueva sede en Asia", "relaciones_exteriores_comercio"),
    ("Panamá asume presidencia de un foro internacional", "relaciones_exteriores_comercio"),
]


def _macro_f1(y_true, y_pred, labels):
    def prf(lab):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if p == lab and t != lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        return f1
    return round(sum(prf(l) for l in labels) / len(labels), 2)


def main() -> int:
    texts = [t for t, _ in LABELED]
    y = [lbl for _, lbl in LABELED]
    labels = sorted(set(y))
    base = [tema_kw(t) for t in texts]
    ml = [(theme._ml(t) or ("general", 0.0, []))[0] for t in texts]
    out = {
        "set": "sintético, revisión del equipo",
        "n_etiquetas": len(texts),
        "clases": labels,
        "baseline_palabras_clave_macro_f1": _macro_f1(y, base, labels),
        "embeddings_macro_f1": _macro_f1(y, ml, labels),
        "embeddings_disponibles": theme.embed.available(),
        "desacuerdos": [
            {"texto": t, "humano": yt, "baseline": b, "embeddings": m}
            for t, yt, b, m in zip(texts, y, base, ml) if m != yt
        ][:10],
    }
    with open(os.path.join(ROOT, "eval", "themes.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
