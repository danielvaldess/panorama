"""Comparación de agrupación por procedencia (T2): baseline léxico vs v2 (origen real + embeddings).

Set etiquetado a mano (sintético, ≥30 pares). Reporta precisión/recall/macro-F1 con
numerador y denominador, y los casos donde el baseline cuenta de más.

Uso: python -m eval.provenance
"""
from __future__ import annotations

import json
import os
import sys

from pipeline import origin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (titulo_a, url_a, medio_a, titulo_b, url_b, medio_b, mismo_origen)
PAIRS = [
    # Agencia replicada (misma procedencia real) -> mismo_origen = True
    ("EFE: El Canal amplía cupos de tránsito", "https://a.com/1", "Medio A", "Panamá abre cupos en el Canal, según EFE", "https://b.com/1", "Medio B", True),
    ("Reuters: Panamá crece 3% este año", "https://c.com/1", "Medio C", "Reuters reporta crecimiento de Panamá", "https://d.com/1", "Medio D", True),
    ("AFP: nueva ruta aérea conecta Panamá y Colombia", "https://e.com/1", "Medio E", "Vuelo Panamá-Colombia, informa AFP", "https://f.com/1", "Medio F", True),
    ("AP: acuerdo comercial firma Panamá", "https://g.com/1", "Medio G", "Panamá firma acuerdo, según AP", "https://h.com/1", "Medio H", True),
    ("Bloomberg: bonos panameños suben", "https://i.com/1", "Medio I", "Bonos de Panamá al alza (Bloomberg)", "https://j.com/1", "Medio J", True),
    # Misma historia reescrita por redacciones distintas -> True
    ("Canal de Panamá amplía los cupos de tránsito diarios", "https://k.com/1", "Medio K", "El Canal aumentará los cupos para buques", "https://l.com/1", "Medio L", True),
    ("Lluvias intensas provocan inundaciones en Chiriquí", "https://m.com/1", "Medio M", "Inundaciones en Chiriquí por fuertes lluvias", "https://n.com/1", "Medio N", True),
    ("Sube el precio de la canasta básica en Panamá", "https://o.com/1", "Medio O", "Aumenta el costo de la canasta básica", "https://p.com/1", "Medio P", True),
    ("Sismo de magnitud 4.2 se siente en Darién", "https://q.com/1", "Medio Q", "Temblor de 4.2 en Darién", "https://r.com/1", "Medio R", True),
    ("Hospital de David recibe nuevo equipo", "https://s.com/1", "Medio S", "Nuevo equipo médico llega al hospital de David", "https://t.com/1", "Medio T", True),
    # Historias distintas -> False
    ("Canal de Panamá amplía cupos de tránsito", "https://u.com/1", "Medio U", "Incautan droga en un contenedor en Colón", "https://v.com/1", "Medio V", False),
    ("Sube la canasta básica", "https://w.com/1", "Medio W", "Selección de Panamá gana partido", "https://x.com/1", "Medio X", False),
    ("Presidente anuncia hospital en David", "https://y.com/1", "Medio Y", "Incendio en un mercado de la capital", "https://z.com/1", "Medio Z", False),
    ("Lluvias en Chiriquí", "https://a2.com/1", "Medio A2", "Aumenta el precio del combustible", "https://b2.com/1", "Medio B2", False),
    ("Turistas llegan a Bocas del Toro", "https://c2.com/1", "Medio C2", "Fallas eléctricas en Arraiján", "https://d2.com/1", "Medio D2", False),
    ("La Asamblea debate una ley de contrataciones", "https://e2.com/1", "Medio E2", "El Canal amplía cupos de tránsito", "https://f2.com/1", "Medio F2", False),
    ("Sismo en Darién", "https://g2.com/1", "Medio G2", "Metro amplía su horario", "https://h2.com/1", "Medio H2", False),
    ("Nuevo hospital en Veraguas", "https://i2.com/1", "Medio I2", "Aumentan las muertes por dengue", "https://j2.com/1", "Medio J2", False),
    ("Presupuesto 2027 pasa a segundo debate", "https://k2.com/1", "Medio K2", "Renuncia un viceministro", "https://l2.com/1", "Medio L2", False),
    ("Cruceros traen turistas a Colón", "https://m2.com/1", "Medio M2", "Sequía afecta el nivel de los lagos", "https://n2.com/1", "Medio N2", False),
    # Mismo medio, historias distintas -> False
    ("TVN: nueva conexión aérea a Colombia", "https://www.tvn-2.com/a", "TVN Noticias", "TVN: resultados de la lotería", "https://www.tvn-2.com/b", "TVN Noticias", False),
    ("TVN: precio del combustible sube", "https://www.tvn-2.com/c", "TVN Noticias", "TVN: partido de la selección", "https://www.tvn-2.com/d", "TVN Noticias", False),
    # Paráfrasis fuerte (semántico debe juntarlas)
    ("El gobierno presentó el presupuesto del próximo año", "https://o2.com/1", "Medio O2", "Panamá da a conocer su plan de gastos anual", "https://p2.com/1", "Medio P2", True),
    ("Autoridades decomisan mercancía ilegal en el puerto", "https://q2.com/1", "Medio Q2", "Aduanas retiene carga irregular en Balboa", "https://r2.com/1", "Medio R2", True),
    ("El turismo crece en la provincia de Bocas del Toro", "https://s2.com/1", "Medio S2", "Bocas del Toro registra más visitantes", "https://t2.com/1", "Medio T2", True),
    # Distintas pero con palabras comunes
    ("Canal de Panamá y su operación", "https://u2.com/1", "Medio U2", "Canal de riego en Azuero avanza", "https://v2.com/1", "Medio V2", False),
    ("Corte Suprema admite demanda", "https://w2.com/1", "Medio W2", "Corte de agua en la capital", "https://x2.com/1", "Medio X2", False),
    ("Ministerio de Salud refuerza vacunación", "https://y2.com/1", "Medio Y2", "Ministerio de Educación entrega útiles", "https://z2.com/1", "Medio Z2", False),
    ("Nueva ley regula el uso del agua", "https://a3.com/1", "Medio A3", "Nueva ley de contrataciones avanza", "https://b3.com/1", "Medio B3", False),
    ("Sismo en la frontera con Colombia", "https://c3.com/1", "Medio C3", "Frontera con Colombia refuerza seguridad", "https://d3.com/1", "Medio D3", False),
    ("Panamá y Costa Rica firman acuerdo migratorio", "https://e3.com/1", "Medio E3", "Panamá y Colombia revisan comercio", "https://f3.com/1", "Medio F3", False),
]


def _item(t, url, medio):
    return {"title": t, "url": url, "source": medio}


def _baseline(pair) -> bool:
    a, b = pair[0], pair[3]
    return origin._sim(a, b) >= origin.ECHO_SIM


def _v2(pair) -> bool:
    a = _item(pair[0], pair[1], pair[2])
    b = _item(pair[3], pair[4], pair[5])
    same = origin.collapse_origins([a, b]) == 1
    return same


def _prf(preds, labels):
    tp = sum(1 for p, y in zip(preds, labels) if p and y)
    fp = sum(1 for p, y in zip(preds, labels) if p and not y)
    fn = sum(1 for p, y in zip(preds, labels) if (not p) and y)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": round(prec, 2), "recall": round(rec, 2), "f1": round(f1, 2)}


def main() -> int:
    labels = [p[6] for p in PAIRS]
    base_preds = [_baseline(p) for p in PAIRS]
    v2_preds = [_v2(p) for p in PAIRS]
    sobre_cuenta = [p[0] for p, b, y in zip(PAIRS, base_preds, labels) if b and not y]
    out = {
        "set": "sintético, revisión del equipo",
        "n_pares": len(PAIRS),
        "positivos": sum(labels),
        "baseline_lexico": _prf(base_preds, labels),
        "v2_origen_embeddings": _prf(v2_preds, labels),
        "baseline_cuenta_de_mas": sobre_cuenta,
        "embeddings_disponibles": origin.embed.available(),
    }
    path = os.path.join(ROOT, "eval", "provenance.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
