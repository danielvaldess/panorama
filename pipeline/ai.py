"""IA sustantiva (OpenRouter): análisis asistido por tema + grounding.

Roles:
  - resumen, "por qué importa", temas (NLP/extracción).
  - relevancia editorial asistida (para comparar con el baseline BM25).
  - grounding: comprobar que el resumen se sostiene en la fuente (abstención).
Degrada con elegancia: lista de modelos + plantilla local si no hay IA.
"""
from __future__ import annotations

import json
import os
import re

import httpx

OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = os.environ.get(
    "OPENROUTER_MODELS",
    "inclusionai/ling-3.0-flash-sante:free,dots-studio/dots-3-note-preview:free,nvidia/nemotron-3.5-lightning:free",
).split(",")
PROFILE = "una mesa de redacción de noticias nacionales en Panamá (TVN)"


def _key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


def _chat(system: str, user: str, max_tokens: int = 900) -> str:
    if not _key():
        return ""
    for model in MODELS:
        model = model.strip()
        try:
            r = httpx.post(OR_URL, headers={"Authorization": f"Bearer {_key()}"},
                           json={"model": model,
                                 "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": user}],
                                 "max_tokens": max_tokens}, timeout=60)
            if r.status_code != 200:
                continue
            msg = r.json()["choices"][0]["message"]
            out = (msg.get("content") or "").strip()
            if not out and msg.get("reasoning"):
                out = msg["reasoning"]
            if out:
                return out
        except Exception:
            continue
    return ""


def _json(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def grounding(summary: str, title: str, sources: list[dict]) -> float:
    """Proxy de faithfulness: proporción de términos del resumen presentes en el titular."""
    stop = {"para", "con", "por", "del", "los", "las", "una", "que", "como", "sobre", "sus", "the"}
    st = {w for w in re.findall(r"[a-záéíóúñ0-9]{4,}", (title or "").lower()) if w not in stop}
    if not st:
        return 0.0
    sm = {w for w in re.findall(r"[a-záéíóúñ0-9]{4,}", (summary or "").lower()) if w not in stop}
    if not sm:
        return 0.0
    return round(len(st & sm) / len(sm), 2)


def analyze(title: str, sources_list: list[dict]) -> dict:
    """Devuelve {summary, why, topics, relevance, method}. Con fallback local."""
    srcs = "; ".join(s["name"] for s in sources_list) or "sin fuente"
    system = ("Eres un asistente editorial. Devuelve ÚNICAMENTE JSON válido, sin texto extra ni "
              "código. No inventes datos que no estén en el titular.")
    user = (
        "Analiza este titular para " + PROFILE + " y responde JSON con las claves:\n"
        'resumen (<=30 palabras, neutral, verificable), '
        'por_que_importa (<=20 palabras), '
        'temas (lista de 2 a 4 etiquetas cortas), '
        'relevancia (0.0 a 1.0, cuán relevante es para la mesa).\n'
        f"Titular: {title}\nFuentes: {srcs}"
    )
    raw = _chat(system, user)
    data = _json(raw)
    if data and data.get("resumen"):
        return {
            "summary": str(data.get("resumen", ""))[:400],
            "why": str(data.get("por_que_importa", ""))[:240],
            "topics": [str(t)[:24] for t in (data.get("temas") or [])][:4],
            "relevance": float(data.get("relevancia", 0) or 0),
            "method": "ai",
            "grounding": grounding(str(data.get("resumen", "")), title, sources_list),
        }
    return {
        "summary": f"{title}.",
        "why": "",
        "topics": [],
        "relevance": 0.0,
        "method": "local",
        "grounding": grounding(title, title, sources_list),
    }
