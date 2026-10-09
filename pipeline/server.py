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
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline import process, sources, snapshot, draft, embed, context, store
from pipeline import ai as ai_mod
from pipeline import db, persist, snapshot_io
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
_build_lock = threading.Lock()
_cache: dict = {"fichas": [], "generated_at": None}

# --- Tiempo real: poller de fuentes en vivo + novedades ---
LIVE_POLL_SECONDS = int(os.environ.get("LIVE_POLL_SECONDS", "180"))
MAX_LIVE = int(os.environ.get("MAX_LIVE", "200"))
_live: dict = {"items": [], "raw_items": [], "seen": set(), "novedades": [], "last_poll": None, "ok": None}


PANAMA_TZ = timezone(timedelta(hours=-5))  # Panamá no observa horario de verano


def _published_day(value: str | None) -> str | None:
    """Día de publicación en hora de Panamá (misma zona que usa la interfaz)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(PANAMA_TZ).date().isoformat()
    except Exception:
        return None


def _compact_news(x: dict, *, editorial: bool) -> dict:
    return {"id": x.get("id") or x.get("id_noticia"), "title": x.get("title") or x.get("titulo"),
            "url": x.get("url"), "source": x.get("source") or x.get("medio"),
            "published": x.get("published") or x.get("fecha_publicacion"),
            "tema": x.get("tema"), "origin": x.get("origin") or x.get("origen"),
            "official": bool(x.get("official")), "editorial_signal": editorial}


def _db_news() -> list[dict]:
    conn = db.connection()
    if conn is None:
        return []
    try:
        return [_compact_news(x, editorial=False) for x in db.get_noticias(conn) if x.get("url") and x.get("titulo")]
    except Exception:
        return []


def _persist_operational_state(fichas: list[dict]) -> None:
    conn = db.connection()
    if conn is None:
        return
    try:
        with db.transaction(conn):
            for f in fichas:
                db.upsert_ficha(conn, f)
                if f.get("draft"):
                    db.set_llm_cache(conn, f"draft:{f.get('id')}", f["draft"], "deterministic")
    except Exception:
        pass


def _merge_live_news(data: dict) -> dict:
    """Mantiene Publicaciones al día aunque el cache principal venga del snapshot."""
    with _lock:
        live_items = list(_live.get("raw_items") or []) + list(_live.get("items") or [])
    out = dict(data)
    all_news = list(out.get("all_news") or []) + _db_news()
    if not all_news and not live_items:
        return data
    seen = {(x.get("url") or "").split("?")[0] for x in all_news if x.get("url")}
    for item in live_items:
        key = (item.get("url") or "").split("?")[0]
        if not key or key in seen:
            continue
        all_news.insert(0, _compact_news(item, editorial=True))
        seen.add(key)
    out["all_news"] = all_news
    days = sorted({d for d in (_published_day(x.get("published")) for x in all_news) if d}, reverse=True)
    cal = dict(out.get("calendar") or {})
    cal["available_days"] = days
    cal["latest_day"] = days[0] if days else cal.get("latest_day")
    out["calendar"] = cal
    counts = dict(out.get("counts") or {})
    counts["after_dedupe"] = max(int(counts.get("after_dedupe") or 0), len(all_news))
    counts["fetched"] = max(int(counts.get("fetched") or 0), len(all_news))
    out["counts"] = counts
    return out


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
    with _lock:
        live_items = list(_live.get("items") or [])
    if used_snapshot:
        raw = snapshot.load_news() + live_items
    else:
        raw = sources.fetch_all(gdelt_query="Panamá")
    editorial = process.filter_editorial(raw)
    editorial_keys = {(x.get("url") or "").split("?")[0] for x in editorial if x.get("url")}
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
    all_news = [_compact_news(x, editorial=(x.get("url") or "").split("?")[0] in editorial_keys)
                for x in deduped]
    available_days = sorted({d for d in (_published_day(x.get("published")) for x in all_news) if d}, reverse=True)
    feed = [{"id": x.get("id"), "title": x["title"], "url": x["url"], "source": x["source"],
              "published": x.get("published"), "tema": x.get("tema"), "origin": x.get("origin")}
             for x in feed_items]
    _persist_operational_state(fichas)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "edicion": edicion,
        "counts": {"fetched": len(raw), "after_dedupe": len(deduped), "editorial_signals": len(editorial),
                   "fichas": len(fichas), "official_items": sum(1 for x in raw if x.get("official"))},
        "fichas": fichas,
        "feed": feed,
        "all_news": all_news,
        "calendar": {"available_days": available_days, "latest_day": available_days[0] if available_days else None,
                     "edition_day": _published_day(edicion)},
        "sources": _sources_catalog(),
        "metrics": metrics.summarize(raw, deduped, fichas),
        "ai_ready": bool(_cache.get("ai_ready")),
        "ai_configured": ai_mod.available(),
        "live": {"last_poll": _live["last_poll"], "items": len(_live["items"]),
                  "novedades": list(_live["novedades"])[:30], "ok": _live["ok"]},
        "live_count_in_fichas": len(live_items),
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
        a = ai_mod.analyze(f["title"], f["sources"], f.get("snippet", ""))
        f.update(summary=a["summary"], why=a["why"], topics=a["topics"],
                 relevance_ai=a["relevance"], method=a["method"], grounding=a["grounding"],
                 ai_fallback=a.get("fallback", False), ai_message=a.get("message", ""),
                 ai_respaldo=a.get("respaldo", ""))
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
    """Refresco determinista. Serializado: nunca hay dos builds a la vez (evita saturar CPU)."""
    if not _build_lock.acquire(blocking=False):
        with _lock:
            return dict(_cache)  # ya hay un build en curso; devolvemos lo actual
    try:
        data = _build_fast()
        with _lock:
            _cache.update(data)
        return data
    finally:
        _build_lock.release()


def _schedule_refresh() -> None:
    """Lanza un refresco en segundo plano sin bloquear el request (evita picos de latencia)."""
    if _build_lock.locked():
        return
    threading.Thread(target=refresh, daemon=True).start()


def _poll_live() -> None:
    """Trae noticias nuevas de las fuentes en vivo, las clasifica y registra novedades."""
    try:
        feed_items: list[dict] = []
        for name, url in sources.FEEDS:
            feed_items += sources.fetch_feed(name, url)
        items = feed_items + sources.fetch_gdelt("Panamá", maxrecords=100)
    except Exception:
        with _lock:
            _live["ok"] = False
        return
    editorial = process.filter_editorial(items)
    editorial_recent = sources._recent(editorial)
    # Persistir noticias nuevas + clasificación en una transacción (dedup por URL).
    conn = db.connection()
    if conn is not None:
        try:
            persist.persist_noticias(conn, items)
        except Exception:
            pass
    nuevos: list[dict] = []
    with _lock:
        raw_seen: set[str] = set()
        raw_items: list[dict] = []
        for x in items:
            key = (x.get("url") or "").split("?")[0]
            if not key or key in raw_seen:
                continue
            raw_seen.add(key)
            raw_items.append(x)
        _live["raw_items"] = raw_items[:MAX_LIVE]
        for x in editorial_recent:
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
    # DB operativa: inicializar (WAL + esquema) y reconstruir desde el snapshot si está vacía.
    try:
        conn = db.ensure_ready()
        db.migrate_legacy(conn)
        if db.count_noticias(conn) == 0 and snapshot.available():
            snapshot_io.load_snapshot(conn=conn)
    except Exception as e:
        print(f"[db] inicialización: {e}", flush=True)
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
app.add_middleware(GZipMiddleware, minimum_size=1024)


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


@app.get("/api/state")
async def state_meta():
    """Metadatos livianos para que la UI decida si vale la pena recargar el payload completo."""
    with _lock:
        data = dict(_cache)
        live = dict(_live)
    counts = data.get("counts") or {}
    return JSONResponse({
        "generated_at": data.get("generated_at"),
        "ready": bool(data.get("fichas")),
        "counts": {"fetched": counts.get("fetched"), "fichas": counts.get("fichas")},
        "live": {"last_poll": live.get("last_poll"), "items": len(live.get("items") or []),
                 "novedades": len(live.get("novedades") or []), "ok": live.get("ok")},
    })


@app.get("/api/fichas")
async def fichas():
    with _lock:
        data = dict(_cache)
        live_count = len(_live.get("items") or [])
    if not data.get("fichas"):
        _schedule_refresh()
        return JSONResponse({"generating": True, "fichas": [], "counts": {}})
    if live_count and int(data.get("live_count_in_fichas") or 0) < live_count:
        _schedule_refresh()  # se sirve el cache de inmediato; la mesa se actualiza en segundo plano
    return JSONResponse(_merge_live_news(data))


@app.post("/api/refresh")
async def force_refresh(x_panorama_token: str | None = Header(default=None)):
    if not _authorized(x_panorama_token):
        return JSONResponse({"ok": False, "error": "no autorizado"}, status_code=401)
    return JSONResponse(_merge_live_news(refresh()))


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
