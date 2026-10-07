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

from pipeline import process, sources, snapshot, draft, embed, context
from pipeline import ai as ai_mod
from eval import metrics

REVIEW_STATES = ["nuevo", "en revisión", "requiere evidencia", "aprobado como borrador", "descartado"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_PATH = os.path.join(ROOT, "data", "processed", "reviews.json")


def _load_reviews() -> dict[str, dict]:
    try:
        with open(REVIEW_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_reviews() -> None:
    os.makedirs(os.path.dirname(REVIEW_PATH), exist_ok=True)
    with open(REVIEW_PATH, "w", encoding="utf-8") as fh:
        json.dump(_review, fh, ensure_ascii=False, indent=2)


_review: dict[str, dict] = _load_reviews()

USER_TOPICS = ["Panamá", "economía", "presupuesto", "Canal", "seguridad", "salud", "Asamblea"]
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "900"))
MAX_FICHAS = int(os.environ.get("MAX_FICHAS", "40"))
AI_TOP_N = int(os.environ.get("AI_TOP_N", "6"))
ADMIN_TOKEN = os.environ.get("PANORAMA_ADMIN_TOKEN", "")

_lock = threading.Lock()
_cache: dict = {"fichas": [], "generated_at": None}


def _sources_catalog() -> list[dict]:
    rel = process.SOURCE_RELIABILITY
    seen: dict[str, str] = {}
    for n, u in sources.FEEDS:
        seen[n] = u
    cat = [{"name": n, "url": u, "reliability": rel.get(n, 3), "status": "al día"} for n, u in seen.items()]
    cat.append({"name": "GDELT", "url": "https://www.gdeltproject.org/", "reliability": 4, "status": "al día"})
    return cat


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
    # D5: preferir el snapshot congelado; si no existe, fallback a fuentes en vivo.
    used_snapshot = snapshot.available()
    raw = snapshot.load_news() if used_snapshot else sources.fetch_all(gdelt_query="Panamá")
    editorial = process.filter_editorial(raw)
    groups, grouping_method = _cluster(editorial)
    fichas = process.priority(groups, USER_TOPICS)[:MAX_FICHAS]
    for f in fichas:  # contexto oficial + paquete editorial + estado de revisión
        f["contexto"] = context.build(f)
        f["draft"] = draft.build(f)
        f["review_state"] = _review.get(f.get("id"), {}).get("state", "nuevo")
    deduped = process.dedupe(raw)  # métrica de entrada completa
    feed_items = process.dedupe(editorial)
    feed = [{"title": x["title"], "url": x["url"], "source": x["source"], "published": x.get("published")}
            for x in feed_items[:120]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"fetched": len(raw), "after_dedupe": len(deduped), "editorial_signals": len(editorial),
                   "fichas": len(fichas), "official_items": sum(1 for x in raw if x.get("official"))},
        "fichas": fichas,
        "feed": feed,
        "sources": _sources_catalog(),
        "metrics": metrics.summarize(raw, deduped, fichas),
        "ai_ready": bool(_cache.get("ai_ready")),
        "ai_configured": ai_mod.available(),
        "method": {"grouping": grouping_method, "retrieval": "BM25 + semántico",
                   "llm": "OpenRouter bajo demanda" if ai_mod.available() else "inactivo (sin OPENROUTER_API_KEY)"},
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
                 relevance_ai=a["relevance"], method=a["method"], grounding=a["grounding"])
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


def _refresher():
    while True:
        try:
            refresh()
        except Exception:
            pass
        time.sleep(REFRESH_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_refresher, daemon=True).start()
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
    _review[body.id] = {"state": body.state, "note": body.note, "reviewer": body.reviewer,
                        "ts": datetime.now(timezone.utc).isoformat()}
    _save_reviews()
    with _lock:
        for f in _cache.get("fichas", []):
            if f.get("id") == body.id:
                f["review_state"] = body.state
    return JSONResponse({"ok": True, "id": body.id, "state": body.state})


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
