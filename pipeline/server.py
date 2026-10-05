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

from pipeline import process, sources
from eval import metrics

USER_TOPICS = ["Panamá", "economía", "presupuesto", "Canal", "seguridad", "salud", "Asamblea"]
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "900"))
MAX_FICHAS = int(os.environ.get("MAX_FICHAS", "40"))
AI_TOP_N = int(os.environ.get("AI_TOP_N", "6"))

_lock = threading.Lock()
_cache: dict = {"fichas": [], "generated_at": None}


def _ai_summary(title: str, sources_list: list[dict]) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return ""
    model = os.environ.get("OPENROUTER_MODEL", "inclusionai/ling-3.0-flash-sante:free")
    srcs = "; ".join(s["name"] for s in sources_list) or "sin fuente"
    prompt = ("Eres un asistente editorial. Responde SOLO con un resumen neutral de máximo 30 "
              "palabras, verificable. No inventes datos.\n"
              f"Titular: {title}\nFuentes: {srcs}")
    try:
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": model, "messages": [{"role": "user", "content": prompt}],
                             "max_tokens": 900}, timeout=60)
        if r.status_code == 200:
            c = r.json()["choices"][0]["message"].get("content") or ""
            c = c.strip()
            if "the user wants" in c.lower():
                return ""
            return c[:400]
    except Exception:
        pass
    return ""


def _sources_catalog() -> list[dict]:
    rel = process.SOURCE_RELIABILITY
    cat = [{"name": n, "url": u, "reliability": rel.get(n, 3), "status": "al día"} for n, u in sources.FEEDS]
    cat.append({"name": "GDELT", "url": "https://www.gdeltproject.org/", "reliability": 4, "status": "al día"})
    return cat


def _build_fast() -> dict:
    """Determinista y rápido (sin IA): fuentes → dedupe → prioridad + citas."""
    raw = sources.fetch_all(gdelt_query="Panamá")
    deduped = process.dedupe(raw)
    groups = process.cluster(deduped)
    fichas = process.priority(groups, USER_TOPICS)[:MAX_FICHAS]
    feed = [{"title": x["title"], "url": x["url"], "source": x["source"], "published": x.get("published")}
            for x in deduped[:120]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"fetched": len(raw), "after_dedupe": len(deduped), "fichas": len(fichas)},
        "fichas": fichas,
        "feed": feed,
        "sources": _sources_catalog(),
        "metrics": metrics.summarize(raw, deduped, fichas),
        "ai_ready": False,
    }


def _enrich_ai(fichas: list[dict]) -> None:
    """Resúmenes con IA en segundo plano (no bloquea la primera respuesta)."""
    changed = False
    for f in fichas[:AI_TOP_N]:
        s = _ai_summary(f["title"], f["sources"])
        if s:
            f["summary"] = s
            changed = True
    if changed:
        with _lock:
            _cache["ai_ready"] = True


def refresh() -> dict:
    data = _build_fast()
    with _lock:
        _cache.update(data)
    threading.Thread(target=_enrich_ai, args=(data["fichas"],), daemon=True).start()
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


# Interfaz (después de las rutas /api)
app.mount("/", StaticFiles(directory="web", html=True), name="web")
