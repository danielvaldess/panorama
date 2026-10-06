"""Panorama — API + web (funcional).

Sirve la interfaz y la API de fichas priorizadas, generadas en vivo desde las
fuentes reales (medios + GDELT). Refresca en segundo plano.

Uso local:
    pip install -r requirements.txt
    uvicorn pipeline.server:app --reload --port 8000
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from pipeline import process, sources, snapshot
from pipeline import ai as ai_mod
from eval import metrics

USER_TOPICS = ["Panamá", "economía", "presupuesto", "Canal", "seguridad", "salud", "Asamblea"]
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "900"))
MAX_FICHAS = int(os.environ.get("MAX_FICHAS", "40"))
AI_TOP_N = int(os.environ.get("AI_TOP_N", "6"))

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


def _build_fast() -> dict:
    """Determinista y rápido (sin IA): fuentes → dedupe → prioridad + citas."""
    # D5: preferir el snapshot congelado; si no existe, fallback a fuentes en vivo.
    used_snapshot = snapshot.available()
    raw = snapshot.load_news() if used_snapshot else sources.fetch_all(gdelt_query="Panamá")
    groups = process.cluster(raw)  # agrupa TODO (incluye eco) para medir verificación
    fichas = process.priority(groups, USER_TOPICS)[:MAX_FICHAS]
    deduped = process.dedupe(raw)  # solo para el feed y métricas
    feed = [{"title": x["title"], "url": x["url"], "source": x["source"], "published": x.get("published")}
            for x in deduped[:120]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"fetched": len(raw), "after_dedupe": len(deduped), "fichas": len(fichas),
                   "official_items": sum(1 for x in raw if x.get("official"))},
        "fichas": fichas,
        "feed": feed,
        "sources": _sources_catalog(),
        "metrics": metrics.summarize(raw, deduped, fichas),
        "ai_ready": False,
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


@app.get("/api/manifest")
async def manifest():
    """Trazabilidad del snapshot de datos públicos (versión, corte y hashes)."""
    return JSONResponse(snapshot.manifest())


@app.get("/api/fichas")
async def fichas():
    with _lock:
        data = dict(_cache)
    if not data.get("fichas"):
        threading.Thread(target=refresh, daemon=True).start()
        return JSONResponse({"generating": True, "fichas": [], "counts": {}})
    return JSONResponse(data)


@app.post("/api/refresh")
async def force_refresh():
    return JSONResponse(refresh())


@app.post("/api/analyze")
async def analyze_now():
    """Ejecuta el análisis con IA bajo demanda (consume cuota de OpenRouter)."""
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
