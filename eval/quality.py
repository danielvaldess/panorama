"""Métricas de calidad (reto §9.1): agrupación, clasificación y ranking.

- Agrupación: baseline (RapidFuzz) vs **semántico** (embeddings) sobre pares etiquetados.
- Clasificación: baseline (palabras clave) vs **ML** (TF-IDF + LogisticRegression), macro-F1.
- Ranking: Precision@5 (exploratoria, sin especialista).

Genera eval/quality.json.  Uso: python -m eval.quality
"""
from __future__ import annotations

import json
import os
import sys

from rapidfuzz import fuzz

from pipeline import embed, process
from pipeline.ingest import _tema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMAS = ["economia", "logistica", "turismo", "servicios", "eventos_naturales", "regulacion"]

# Etiquetas humanas (muestra pequeña, ilustrativa) ---------------------------------
LABELED = [
    ("Sube el precio de la canasta básica en Panamá", "economia"),
    ("Inflación se desacelera en el país, según el INEC", "economia"),
    ("El PIB de Panamá crecerá 4% este año, proyecta el MEF", "economia"),
    ("Aumenta el desempleo en la ciudad de Colón", "economia"),
    ("Gobierno presenta el presupuesto general del Estado 2027", "economia"),
    ("Canal de Panamá amplía los cupos de tránsito para buques", "logistica"),
    ("Puerto de Balboa rompe récord de movimiento de contenedores", "logistica"),
    ("Nueva naviera inicia operaciones en aguas panameñas", "logistica"),
    ("Las esclusas Panamax aumentan su capacidad de carga", "logistica"),
    ("Tránsito de carga por el Canal crece en el primer trimestre", "logistica"),
    ("Temporada de cruceros traerá más turistas a Bocas del Toro", "turismo"),
    ("Hoteles reportan alta ocupación en la temporada alta", "turismo"),
    ("Nueva conexión aérea conecta Panamá con Colombia", "turismo"),
    ("Aumentan las visitas a las playas del Pacífico panameño", "turismo"),
    ("El turismo aporta más al PIB nacional este año", "turismo"),
    ("Fuerte lluvia provoca inundaciones en Chiriquí", "eventos_naturales"),
    ("Sismo de magnitud 4.2 se siente en la provincia de Darién", "eventos_naturales"),
    ("Alerta por lluvias y tormentas eléctricas en varias regiones", "eventos_naturales"),
    ("Sequía afecta el nivel de los lagos del Canal", "eventos_naturales"),
    ("Deslizamiento de tierra deja varias viviendas afectadas", "eventos_naturales"),
    ("La Asamblea debate una nueva ley de contrataciones", "regulacion"),
    ("Tribunal electoral reglamenta las próximas elecciones", "regulacion"),
    ("Decreto regula el uso del agua en la cuenca del Canal", "regulacion"),
    ("La Corte Suprema admite demanda contra una ley", "regulacion"),
    ("Nueva licitación para el contrato de aseo en la capital", "regulacion"),
    ("Metro de Panamá amplía su horario de operación", "servicios"),
    ("Corte de agua afecta a varios sectores de la capital", "servicios"),
    ("Hospital Santo Tomás refuerza sus servicios de urgencia", "servicios"),
    ("Fallas eléctricas dejan sin luz a barrios de Arraiján", "servicios"),
    ("Empresa de aseo anuncia cambios en las rutas de recolección", "servicios"),
]

GROUP_PAIRS = [
    ("Incautan 65 paquetes dentro de un contenedor en Colón", "Policía decomisa 65 paquetes en un contenedor", True),
    ("Canal de Panamá amplía cupos de tránsito", "El Canal aumentará los cupos para buques", True),
    ("Lluvias intensas provocan inundaciones en Chiriquí", "Inundaciones en Chiriquí por fuertes lluvias", True),
    ("Gobierno anuncia nuevo hospital en David", "Se construirá un hospital en David", True),
    ("Sube el precio de la canasta básica", "Aumenta el costo de la canasta básica en Panamá", True),
    ("Sismo de magnitud 4.2 en Darién", "Un temblor de 4.2 se registra en Darién", True),
    ("Canal de Panamá amplía cupos", "Lluvias intensas en Chiriquí", False),
    ("Incautan paquetes en Colón", "Nuevo hospital en David", False),
    ("Sube la canasta básica", "Selección de Panamá gana partido", False),
    ("Presidente anuncia hospital", "Incautan droga en un contenedor", False),
    ("Lluvias en Chiriquí", "Aumenta el precio del combustible", False),
    ("Turistas llegan a Bocas del Toro", "Fallas eléctricas en Arraiján", False),
    ("La Asamblea debate una ley", "El Canal amplía cupos de tránsito", False),
    ("Sismo en Darién", "Metro amplía su horario", False),
]

RANK_QUERIES = [
    ("canal cupos tránsito buques", ["Canal de Panamá amplía los cupos de tránsito para buques", "Las esclusas Panamax aumentan su capacidad de carga"]),
    ("lluvias inundaciones Chiriquí", ["Fuerte lluvia provoca inundaciones en Chiriquí", "Alerta por lluvias y tormentas eléctricas en varias regiones"]),
    ("canasta básica precio", ["Sube el precio de la canasta básica en Panamá", "Inflación se desacelera en el país, según el INEC"]),
    ("turismo cruceros Bocas", ["Temporada de cruceros traerá más turistas a Bocas del Toro", "El turismo aporta más al PIB nacional este año"]),
]


def _prf(scores, labels, t):
    tp = fp = fn = 0
    for s, y in zip(scores, labels):
        p = s >= t
        if p and y:
            tp += 1
        elif p and not y:
            fp += 1
        elif not p and y:
            fn += 1
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return round(prec, 2), round(rec, 2), round(f1, 2)


def grouping_eval() -> dict:
    labels = [same for *_, same in GROUP_PAIRS]
    a = [x[0] for x in GROUP_PAIRS]
    b = [x[1] for x in GROUP_PAIRS]
    base = [fuzz.token_set_ratio(x, y) / 100 for x, y in zip(a, b)]
    sem = [0.0] * len(a)
    if embed.available():
        m = embed.cosine_matrix(a + b)
        n = len(a)
        sem = [float(m[i, n + i]) for i in range(n)]
    out = {"n_pares": len(a), "positivos": sum(labels)}
    best = {"baseline": (0, None), "semantico": (0, None)}
    for name, scores in [("baseline", base), ("semantico", sem)]:
        for t in [x / 100 for x in range(40, 96, 2)]:
            _, _, f1 = _prf(scores, labels, t)
            if f1 > best[name][0]:
                best[name] = (f1, t)
    for name, scores in [("baseline", base), ("semantico", sem)]:
        f1, t = best[name]
        p, r, _ = _prf(scores, labels, t)
        out[name] = {"umbral": t, "precision": p, "recall": r, "f1": f1}
    return out


def classification_eval() -> dict:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.metrics import f1_score

    texts = [t for t, _ in LABELED]
    y = [lbl for _, lbl in LABELED]
    # baseline: palabras clave (reglas)
    yb = [_tema(t) for t in texts]
    base_f1 = round(f1_score(y, yb, average="macro", labels=TEMAS, zero_division=0), 2)
    # modelo ML: TF-IDF + regresión logística (validación cruzada)
    clf = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=1), LogisticRegression(max_iter=1000))
    ym = cross_val_predict(clf, texts, y, cv=5)
    ml_f1 = round(f1_score(y, ym, average="macro", labels=TEMAS, zero_division=0), 2)
    return {"n_etiquetas": len(texts), "clases": len(TEMAS),
            "metodo_etiquetado": "revisión humana (muestra pequeña)",
            "baseline_palabras_clave_macro_f1": base_f1, "ml_tfidf_logreg_macro_f1": ml_f1,
            "mejora": round(ml_f1 - base_f1, 2)}


def ranking_eval() -> dict:
    """Precision@5 (exploratoria, sin especialista)."""
    rows = []
    for q, rel in RANK_QUERIES:
        corpus = [{"title": t, "url": ""} for t in rel] + [{"title": t, "url": ""} for t in
                  ["Lluvias en Chiriquí", "Sube la canasta básica", "Sismo en Darién", "Metro amplía horario", "Fallas eléctricas"]]
        # BM25
        docs = [process.tokens(x["title"]) for x in corpus]
        scores = process.bm25(process.tokens(q), docs)
        bm_top = [corpus[i]["title"] for i in sorted(range(len(corpus)), key=lambda i: -scores[i])[:5]]
        bm_p = round(sum(1 for t in bm_top if t in rel) / 5, 2)
        # semántico
        if embed.available():
            sem_top = [x["title"] for x, _ in embed.retrieve(q, corpus, 5)]
            sem_p = round(sum(1 for t in sem_top if t in rel) / 5, 2)
        else:
            sem_p = None
        rows.append({"consulta": q, "p@5_bm25": bm_p, "p@5_semantico": sem_p})
    return {"tipo": "exploratoria (sin especialista)", "consultas": len(rows), "detalle": rows}


def run() -> dict:
    out = {"grouping": grouping_eval(), "classification": classification_eval(), "ranking": ranking_eval()}
    with open(os.path.join(ROOT, "eval", "quality.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(run(), ensure_ascii=False, indent=2))
