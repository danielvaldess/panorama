"""Carga el snapshot congelado (data/raw/*) para el pipeline.

Decisión D5: la demo usa un snapshot reproducible (sin fuentes en vivo), y el
`fallback` local queda documentado si el snapshot no está disponible.
"""
from __future__ import annotations

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")


def available() -> bool:
    return os.path.exists(os.path.join(RAW, "noticias.csv"))


def load_news(limit: int | None = None) -> list[dict]:
    items: list[dict] = []
    with open(os.path.join(RAW, "noticias.csv"), encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            items.append({
                "title": (r.get("titulo") or "").strip(),
                "url": (r.get("url") or "").strip(),
                "source": (r.get("medio") or "").strip(),
                "published": (r.get("fecha_publicacion") or r.get("fecha_deteccion") or "") or None,
                "snippet": "",
                "topic": (r.get("tema") or "").strip(),
                "topics": [],
                "id": (r.get("id_noticia") or "").strip(),
                "official": (r.get("origen") == "Oficial"),
            })
    if limit:
        items = items[:limit]
    return items


def load_indicators() -> list[dict]:
    path = os.path.join(RAW, "indicadores.csv")
    if not os.path.exists(path):
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            val = r.get("valor", "")
            rows.append({
                "pais_iso3": r.get("pais_iso3"),
                "indicador_id": r.get("indicador_id"),
                "anio": r.get("anio"),
                "valor": None if val in ("", None) else float(val),
                "unidad": r.get("unidad"),
                "fuente_url": r.get("fuente_url"),
                "licencia": r.get("licencia"),
            })
    return rows


def load_events() -> dict:
    path = os.path.join(RAW, "eventos.geojson")
    if not os.path.exists(path):
        return {"type": "FeatureCollection", "features": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def manifest() -> dict:
    path = os.path.join(ROOT, "data", "manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
