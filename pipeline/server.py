"""Panorama — API + web (funcional).

Sirve la interfaz y la API de fichas priorizadas, generadas en vivo desde las
fuentes reales (medios + GDELT). Refresca en segundo plano.

Uso local:
    pip install -r requirements.txt
    uvicorn pipeline.server:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline import process, sources, snapshot, draft, embed, context, store
from pipeline import ai as ai_mod
from eval import metrics, sustento

REVIEW_STATES = ["nuevo", "en revisión", "requiere evidencia", "aprobado como borrador", "descartado"]
VEREDICTOS = ["válido", "parcial", "inválido"]
MIN_DECISIONES_PERFIL = 5
_review: dict[str, dict] = {}
_claim_verdicts: dict[str, dict] = {}

USER_TOPICS = ["Panamá", "economía", "presupuesto", "Canal", "seguridad", "salud", "Asamblea"]
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "900"))
AI_TOP_N = int(os.environ.get("AI_TOP_N", "6"))
ADMIN_TOKEN = os.environ.get("PANORAMA_ADMIN_TOKEN", "")

_lock = threading.Lock()
_cache: dict = {"fichas": [], "generated_at": None}

# --- Tiempo real: poller de fuentes en vivo + novedades ---
LIVE_POLL_SECONDS = int(os.environ.get("LIVE_POLL_SECONDS", "180"))
MAX_LIVE = int(os.environ.get("MAX_LIVE", "200"))
_live: dict = {"items": [], "seen": set(), "novedades": [], "last_poll": None, "ok": None}


def _sources_catalog() -> list[dict]:
    """Catálogo alineado a las fuentes declaradas por el reto (última página del PDF)."""
    return [{"name": s["nombre"], "url": s["url"], "reliability": s["confiabilidad"],
             "licencia": s["licencia"], "status": "al día"} for s in sources.CHALLENGE_SOURCES]


def _cluster(items: list[dict]) -> tuple[list[list[dict]], str]:
    if embed.available():
        try:
            return embed.cluster(items, threshold=float(os.environ.get("SEMANTIC_CLUSTER_THRESHOLD", "0.72"))), "semántico (embeddings locales)"
        except Exception:
            pass
    return process.cluster(items), "léxico (similitud de texto)"


def _authorized(token: str | None) -> bool:
    return not ADMIN_TOKEN or token == ADMIN_TOKEN


def _build_fast() -> dict:
    """Determinista y rápido (sin IA): fuentes → dedupe → prioridad + citas."""
    # D5: snapshot congelado como base + lo que va llegando en vivo (tiempo real).
    used_snapshot = snapshot.available()
    if used_snapshot:
        raw = snapshot.load_news() + list(_live["items"])
    else:
        raw = sources.fetch_all(gdelt_query="Panamá")
    editorial = process.filter_editorial(raw)
    groups, grouping_method = _cluster(editorial)
    # La frescura se mide contra la fecha de la edición (lo más nuevo del snapshot),
    # no contra el reloj: el paquete es un archivo congelado.
    pubs = [x["published"] for x in editorial if x.get("published")]
    edicion = max(pubs) if pubs else None
    fichas = process.priority(groups, USER_TOPICS, ref=edicion)
    for f in fichas:  # contexto oficial + paquete editorial + estado de revisión
        f["contexto"] = context.build(f)
        f["draft"] = draft.build(f)
        rev = _review.get(f.get("id"), {})
        f["review_state"] = rev.get("state", "nuevo")
        f["reviewer"] = rev.get("reviewer")
        f["review_ts"] = rev.get("ts")
    deduped = process.dedupe(raw)  # métrica de entrada completa
    feed_items = process.dedupe(editorial)
    feed = [{"id": x.get("id"), "title": x["title"], "url": x["url"], "source": x["source"],
             "published": x.get("published"), "tema": x.get("tema"), "origin": x.get("origin")}
            for x in feed_items]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "edicion": edicion,
        "counts": {"fetched": len(raw), "after_dedupe": len(deduped), "editorial_signals": len(editorial),
                   "fichas": len(fichas), "official_items": sum(1 for x in raw if x.get("official"))},
        "fichas": fichas,
        "feed": feed,
        "sources": _sources_catalog(),
        "metrics": metrics.summarize(raw, deduped, fichas),
        "ai_ready": bool(_cache.get("ai_ready")),
        "ai_configured": ai_mod.available(),
        "live": {"last_poll": _live["last_poll"], "items": len(_live["items"]),
                 "novedades": list(_live["novedades"])[:30], "ok": _live["ok"]},
        "method": {"grouping": grouping_method, "retrieval": "BM25 + semántico",
                   "llm": "IA bajo demanda (OpenCode Zen / OpenRouter)" if ai_mod.available() else "inactivo (sin proveedor de IA)"},
        "snapshot": (
            {"used": True, **{k: v for k, v in snapshot.manifest().items() if k in ("version", "fecha_corte_UTC")}}
            if used_snapshot else {"used": False}
        ),
    }


def _enrich_ai(fichas: list[dict]) -> None:
    """Análisis asistido por IA (resumen, por qué importa, temas, relevancia).
    Mide baseline (BM25) vs asistido (IA) con concordancia de orden."""
    bm25: list[float] = []
    ai_rel: list[float] = []
    for f in fichas[:AI_TOP_N]:
        a = ai_mod.analyze(f["title"], f["sources"])
        f.update(summary=a["summary"], why=a["why"], topics=a["topics"],
                 relevance_ai=a["relevance"], method=a["method"], grounding=a["grounding"],
                 ai_fallback=a.get("fallback", False), ai_message=a.get("message", ""))
        bm25.append(f.get("relevance", 0))
        ai_rel.append(a["relevance"])
    n = len(bm25)
    if n:
        with _lock:
            _cache["ai"] = {
                "analyzed": n,
                "baseline_avg": round(sum(bm25) / n, 2),
                "ai_avg": round(sum(ai_rel) / n, 2),
                "concordance": metrics.rank_agreement(bm25, ai_rel),
            }
            _cache["ai_ready"] = True


def refresh() -> dict:
    """Refresco determinista (sin IA). La IA se dispara solo a pedido (/api/analyze)."""
    data = _build_fast()
    with _lock:
        _cache.update(data)
    return data


def _poll_live() -> None:
    """Trae noticias nuevas de las fuentes en vivo, las clasifica y registra novedades."""
    try:
        items = sources.fetch_all(gdelt_query="Panamá")
    except Exception:
        with _lock:
            _live["ok"] = False
        return
    editorial = process.filter_editorial(items)
    nuevos: list[dict] = []
    with _lock:
        for x in editorial:
            key = (x.get("url") or "").split("?")[0]
            if not key or key in _live["seen"]:
                continue
            _live["seen"].add(key)
            _live["items"].insert(0, x)
            nuevos.append(x)
        _live["items"] = _live["items"][:MAX_LIVE]
        if nuevos:
            _live["novedades"] = ([{"id": x.get("id"), "title": x.get("title"), "source": x.get("source"),
                                    "published": x.get("published")} for x in nuevos]
                                  + _live["novedades"])[:50]
        _live["last_poll"] = datetime.now(timezone.utc).isoformat()
        _live["ok"] = True
    if nuevos:
        refresh()  # recalcula la mesa con lo que acaba de llegar


def _live_poller():
    while True:
        try:
            _poll_live()
        except Exception:
            pass
        time.sleep(LIVE_POLL_SECONDS)


def _refresher():
    while True:
        try:
            refresh()
        except Exception:
            pass
        time.sleep(REFRESH_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _review.update(store.cargar_revisiones())
    for r in store.cargar_veredictos():
        clave = f"{r.get('id_caso')}#{r.get('indice')}"
        if r.get("id_caso") is not None and r.get("indice") is not None:
            _claim_verdicts[clave] = {"veredicto": r.get("veredicto"),
                                      "comentario": r.get("comentario"), "ts": r.get("ts")}
    if snapshot.available():  # las URLs del snapshot no cuentan como novedad
        _live["seen"].update((x.get("url") or "").split("?")[0] for x in snapshot.load_news())
    threading.Thread(target=_refresher, daemon=True).start()
    threading.Thread(target=_live_poller, daemon=True).start()
    yield


app = FastAPI(title="Panorama API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "generated_at": _cache.get("generated_at")}


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


@app.get("/api/search")
async def search(q: str = ""):
    """Recuperación semántica sobre los temas (embeddings). Fallback léxico."""
    if len(q.strip()) < 2:
        return JSONResponse({"q": q, "method": "—", "ids": []})
    with _lock:
        fichas = list(_cache.get("fichas", []))
    if not fichas:
        return JSONResponse({"q": q, "method": "—", "ids": []})
    titles = [f["title"] for f in fichas]
    bm = process.bm25(process.tokens(q), [process.tokens(t) for t in titles])
    mx = max(bm) or 1.0
    sem = {}
    if embed.available():
        for item, s in embed.retrieve(q, [{"title": t} for t in titles], len(titles)):
            sem[item["title"]] = s
    def score(i):
        return 0.5 * (bm[i] / mx) + 0.5 * sem.get(titles[i], 0.0)
    order = sorted(range(len(fichas)), key=lambda i: -score(i))
    return JSONResponse({"q": q, "method": "híbrido (semántico + léxico)",
                         "ids": [fichas[i]["id"] for i in order][:12]})


@app.get("/api/manifest")
async def manifest():
    """Trazabilidad del snapshot de datos públicos (versión, corte y hashes)."""
    return JSONResponse(snapshot.manifest())


@app.get("/api/acceptance")
async def acceptance():
    """Matriz de aceptación T01–T10 (evaluación reproducible)."""
    return JSONResponse(_read_json(os.path.join("eval", "acceptance.json")) or [])


@app.get("/api/benchmark")
async def benchmark():
    """Benchmark de 60 consultas y métricas (evaluación reproducible)."""
    return JSONResponse(_read_json(os.path.join("eval", "results.json")) or {})


@app.get("/api/fichas")
async def fichas():
    with _lock:
        data = dict(_cache)
    if not data.get("fichas"):
        threading.Thread(target=refresh, daemon=True).start()
        return JSONResponse({"generating": True, "fichas": [], "counts": {}})
    return JSONResponse(data)


@app.post("/api/refresh")
async def force_refresh(x_panorama_token: str | None = Header(default=None)):
    if not _authorized(x_panorama_token):
        return JSONResponse({"ok": False, "error": "no autorizado"}, status_code=401)
    return JSONResponse(refresh())


@app.post("/api/seen")
async def mark_seen():
    """Marca las novedades como vistas (apaga las notificaciones)."""
    with _lock:
        _live["novedades"] = []
    return JSONResponse({"ok": True})


class ReviewIn(BaseModel):
    id: str
    state: str
    note: str | None = None
    reviewer: str | None = None


@app.post("/api/review")
async def set_review(body: ReviewIn, x_panorama_token: str | None = Header(default=None)):
    """Registra la decisión humana sobre una ficha (nuevo → … → descartado)."""
    if not _authorized(x_panorama_token):
        return JSONResponse({"ok": False, "error": "no autorizado"}, status_code=401)
    if body.state not in REVIEW_STATES:
        return JSONResponse({"ok": False, "error": "estado inválido", "valid": REVIEW_STATES}, status_code=400)
    registro = {"id": body.id, "state": body.state, "note": body.note, "reviewer": body.reviewer,
                "ts": store.ahora()}
    persisted = store.guardar_revision(registro)
    _review[body.id] = registro
    with _lock:
        for f in _cache.get("fichas", []):
            if f.get("id") == body.id:
                f["review_state"] = body.state
    return JSONResponse({"ok": True, "id": body.id, "state": body.state, "persisted": persisted})


class ClaimVerdictIn(BaseModel):
    id_caso: str
    indice: int
    veredicto: str
    comentario: str | None = None
    reviewer: str | None = None


@app.post("/api/claims/verdict")
async def set_claim_verdict(body: ClaimVerdictIn, x_panorama_token: str | None = Header(default=None)):
    """Veredicto del Administrador sobre una afirmación (válido / parcial / inválido)."""
    if not _authorized(x_panorama_token):
        return JSONResponse({"ok": False, "error": "no autorizado"}, status_code=401)
    if body.veredicto not in VEREDICTOS:
        return JSONResponse({"ok": False, "error": "veredicto inválido", "valid": VEREDICTOS},
                            status_code=400)
    with _lock:
        fichas = list(_cache.get("fichas", []))
    if not fichas:
        refresh()
        with _lock:
            fichas = list(_cache.get("fichas", []))
    f = next((x for x in fichas if x.get("id") == body.id_caso), None)
    if f is None:
        return JSONResponse({"ok": False, "error": "ficha no encontrada"}, status_code=404)
    claims = (f.get("draft") or {}).get("afirmaciones") or []
    if not 0 <= body.indice < len(claims):
        return JSONResponse({"ok": False, "error": "índice de afirmación fuera de rango"}, status_code=400)
    claim = claims[body.indice]
    registro = {
        "id_caso": body.id_caso,
        "indice": body.indice,
        "veredicto": body.veredicto,
        "comentario": body.comentario,
        "reviewer": body.reviewer,
        "ts": store.ahora(),
        "texto": claim.get("texto"),
        "tipo": claim.get("tipo"),
        "ids_fuente": claim.get("ids_fuente"),
        "titulo_ficha": f.get("title"),
        "tema": f.get("tema"),
        "estado_evidencia": f.get("evidence_state"),
        "puntaje": f.get("score"),
        "citas": [s.get("url") for s in (f.get("sources") or [])],
    }
    persisted = store.guardar_veredicto(registro)
    clave = f"{body.id_caso}#{body.indice}"
    _claim_verdicts[clave] = {"veredicto": body.veredicto, "comentario": body.comentario,
                              "ts": registro["ts"]}
    return JSONResponse({"ok": True, "clave": clave, "veredicto": body.veredicto,
                         "persisted": persisted})


@app.get("/api/claims/verdicts")
async def claim_verdicts():
    """Veredictos de afirmaciones ya registrados (para repintar la ficha)."""
    return JSONResponse(_claim_verdicts)


def _clase_estado(state: str) -> str:
    if state == "aprobado como borrador":
        return "aprobados"
    if state == "descartado":
        return "descartados"
    return "en_proceso"


def _agrupar(regs: list[tuple[dict, dict]], clave) -> dict:
    """Agrupa decisiones por una clave de la ficha: {clave: {aprobados, descartados, en_proceso}}."""
    out: dict[str, dict] = {}
    for reg, f in regs:
        k = clave(f) or "sin dato"
        bucket = out.setdefault(k, {"aprobados": 0, "descartados": 0, "en_proceso": 0})
        bucket[_clase_estado(reg.get("state", ""))] += 1
    return dict(sorted(out.items(), key=lambda kv: -(kv[1]["aprobados"] + kv[1]["descartados"])))


def _promedio(regs: list[tuple[dict, dict]], getter) -> float | None:
    vals = [getter(f) for _, f in regs]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 1) if vals else None


@app.get("/api/admin/profile")
async def admin_profile():
    """Preferencias detectadas del Administrador a partir de sus decisiones.

    Lectura descriptiva para alimentar la revisión humana; **no** re-ordena la mesa.
    """
    with _lock:
        fichas = list(_cache.get("fichas", []))
    by_id = {f.get("id"): f for f in fichas}
    pares = [(r, by_id[rid]) for rid, r in _review.items() if rid in by_id]
    sust = sustento.calcular()
    n = len(pares)
    if n < MIN_DECISIONES_PERFIL:
        return JSONResponse({
            "estado": "insuficiente",
            "decisiones": n,
            "minimo": MIN_DECISIONES_PERFIL,
            "mensaje": (f"Se necesitan al menos {MIN_DECISIONES_PERFIL} decisiones registradas "
                        f"sobre fichas para perfilar preferencias ({n}/{MIN_DECISIONES_PERFIL})."),
            "sustento": sust,
            "nota": "Lectura descriptiva de tus decisiones; el orden de la mesa no cambia.",
        })

    aprob = [(r, f) for r, f in pares if _clase_estado(r.get("state", "")) == "aprobados"]
    desc = [(r, f) for r, f in pares if _clase_estado(r.get("state", "")) == "descartados"]
    counts = {"total": n,
              "aprobados": len(aprob), "descartados": len(desc),
              "en_proceso": n - len(aprob) - len(desc),
              "tasa_aprobacion": round(len(aprob) / max(1, len(aprob) + len(desc)), 2)}

    def fuentes(regs: list[tuple[dict, dict]], top: int = 8) -> dict:
        c: dict[str, int] = {}
        for _, f in regs:
            for s in (f.get("sources") or []):
                c[s.get("name") or "?"] = c.get(s.get("name") or "?", 0) + 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1])[:top])

    insights: list[str] = []
    temas = _agrupar(pares, lambda f: f.get("tema"))
    mejor = [(t, v) for t, v in temas.items() if (v["aprobados"] + v["descartados"]) >= 2]
    if mejor:
        mejor.sort(key=lambda kv: (-kv[1]["aprobados"], kv[0]))
        insights.append(f"Más aprobaciones en el tema «{mejor[0][0]}» "
                        f"({mejor[0][1]['aprobados']} de {mejor[0][1]['aprobados'] + mejor[0][1]['descartados']}).")
    evid_aprob = _agrupar(aprob, lambda f: f.get("evidence_state"))
    if evid_aprob:
        top_ev = next(iter(evid_aprob))
        insights.append(f"Tus aprobaciones suelen tener evidencia «{top_ev}».")
    pa, pd = _promedio(aprob, lambda f: f.get("score")), _promedio(desc, lambda f: f.get("score"))
    if pa is not None and pd is not None:
        insights.append(f"Puntaje promedio: aprobados {pa} vs descartados {pd}.")

    return JSONResponse({
        "estado": "ok",
        "decisiones": counts,
        "por_tema": temas,
        "por_banda": _agrupar(pares, lambda f: f.get("band")),
        "por_evidencia": _agrupar(pares, lambda f: f.get("evidence_state")),
        "fuentes_frecuentes": {"aprobados": fuentes(aprob), "descartados": fuentes(desc)},
        "puntaje_promedio": {"aprobados": pa, "descartados": pd},
        "componentes_promedio": {
            "aprobados": {k: _promedio(aprob, lambda f, k=k: (f.get("components") or {}).get(k)) for k in ("R", "I", "U", "N", "E")},
            "descartados": {k: _promedio(desc, lambda f, k=k: (f.get("components") or {}).get(k)) for k in ("R", "I", "U", "N", "E")},
        },
        "sustento": sust,
        "insights": insights,
        "nota": "Lectura descriptiva de tus decisiones; el orden de la mesa no cambia.",
    })


@app.post("/api/analyze")
async def analyze_now(x_panorama_token: str | None = Header(default=None)):
    """Ejecuta el análisis con IA bajo demanda (consume cuota de OpenRouter)."""
    if not _authorized(x_panorama_token):
        return JSONResponse({"ok": False, "error": "no autorizado"}, status_code=401)
    with _lock:
        fichas = list(_cache.get("fichas", []))
    if not fichas:
        refresh()
        with _lock:
            fichas = list(_cache.get("fichas", []))
    _enrich_ai(fichas)
    with _lock:
        data = dict(_cache)
    return JSONResponse(data)


# Interfaz (después de las rutas /api)
app.mount("/", StaticFiles(directory="web", html=True), name="web")
