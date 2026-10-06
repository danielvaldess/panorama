"""Construye el snapshot congelado de datos públicos.

Paquete: "Panamá · Señales y Evidencias v1"
- A · noticias públicas: TVN RSS + GDELT DOC 2.0  -> data/raw/noticias.csv
- B · Banco Mundial Indicators v2 (6x6, 2010-2024) -> data/raw/indicadores.csv
- C · USGS sismos 2024                             -> data/raw/eventos.geojson
- manifest + diccionario                            -> data/manifest.json, data/diccionario.md

Uso:  python -m pipeline.ingest
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone

import feedparser
import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
UA = "Panorama/0.1 (hackIAthon Panama 2026)"
NOW = datetime.now(timezone.utc)
CORTE = NOW.isoformat()
EXTRACCION = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")

FEEDS = [
    ("TVN Noticias", "https://www.tvn-2.com/rss/"),
    ("La Prensa", "https://www.prensa.com/arc/outboundfeeds/rss/"),
    ("Foco Panamá", "https://focopanama.com/feed/"),
    ("TVMax", "https://www.tvmax-9.com/rss/"),
]
# Prensa oficial (primarias) vía agregador restringido a dominios de gobierno.
OFFICIAL_FEEDS = [
    ("Oficial gob.pa", "https://news.google.com/rss/search?q=site:gob.pa&hl=es-419&gl=PA&ceid=PA:es-419"),
]
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERIES = ["Panama", "Panama logistica", "Panama turismo", "Panama economia", "Panama terremoto"]

WB_COUNTRIES = ["PAN", "CRI", "COL", "DOM", "MEX", "GTM"]
WB_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": ("Crecimiento del PIB", "% anual"),
    "FP.CPI.TOTL.ZG": ("Inflación, precios al consumidor", "% anual"),
    "SL.UEM.TOTL.ZS": ("Desempleo (% fuerza laboral)", "%"),
    "SP.POP.TOTL": ("Población total", "personas"),
    "IT.NET.USER.ZS": ("Personas que usan Internet", "% población"),
    "NE.EXP.GNFS.ZS": ("Exportaciones de bienes y servicios", "% del PIB"),
}
WB_YEARS = "2010:2024"

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_PARAMS = {
    "format": "geojson", "starttime": "2024-01-01", "endtime": "2024-12-31",
    "minlatitude": 5, "maxlatitude": 12, "minlongitude": -86, "maxlongitude": -76,
    "minmagnitude": 3,
}

TEMAS = {
    "economia": ["economía", "economia", "pib", "inflación", "presupuesto", "banco", "dólar", "canasta", "empleo", "salario"],
    "logistica": ["canal", "puerto", "logística", "logistica", "tránsito", "esclusa", "naviera", "carga"],
    "turismo": ["turismo", "turista", "hotel", "vuelo", "crucero", "playa", "vacacion"],
    "servicios": ["agua", "electricidad", "energía", "aseo", "metro", "transporte", "salud", "hospital", "educación"],
    "eventos_naturales": ["sismo", "terremoto", "inundación", "lluvia", "huracán", "volcán", "sequía"],
    "regulacion": ["regula", "decreto", "ley", "asamblea", "contrato", "licitación", "tribunal", "corte"],
}


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _iso(st):
    if not st:
        return None
    try:
        return datetime(*st[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def _tema(texto: str) -> str:
    t = texto.lower()
    for tema, keys in TEMAS.items():
        if any(k in t for k in keys):
            return tema
    return "general"


def _medio_google(title: str) -> tuple[str, str]:
    if " - " in title:
        head, _, medio = title.rpartition(" - ")
        if head and medio:
            return head.strip(), medio.strip()
    return title, "Google News"


def collect_news() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    def add(titulo, url, medio, publicacion, deteccion, origen):
        if not titulo or not url:
            return
        key = url.split("?")[0]
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "id_noticia": _id(url),
            "titulo": titulo,
            "url": url,
            "medio": medio,
            "idioma": "es",
            "fecha_publicacion": publicacion or "",
            "fecha_deteccion": deteccion or "",
            "fecha_extraccion": EXTRACCION,
            "tema": _tema(titulo),
            "origen": origen,
            "alcance_texto": "titular+metadatos",
        })

    for name, url in FEEDS:
        try:
            d = feedparser.parse(url, agent=UA)
        except Exception:
            continue
        for e in getattr(d, "entries", []):
            titulo = _clean(e.get("title"))
            link = (e.get("link") or "").strip()
            pub = _iso(e.get("published_parsed") or e.get("updated_parsed"))
            add(titulo, link, name, pub, pub or EXTRACCION, "RSS")

    for name, url in OFFICIAL_FEEDS:
        try:
            d = feedparser.parse(url, agent=UA)
        except Exception:
            continue
        for e in getattr(d, "entries", []):
            raw = _clean(e.get("title"))
            titulo, medio = _medio_google(raw)
            link = (e.get("link") or "").strip()
            pub = _iso(e.get("published_parsed") or e.get("updated_parsed"))
            add(titulo, link, medio, pub, pub or EXTRACCION, "Oficial")

    for q in GDELT_QUERIES:
        time.sleep(5)  # GDELT: máx. 1 req / 5 s
        try:
            r = httpx.get(GDELT_URL, params={
                "query": q, "mode": "artlist", "maxrecords": 250,
                "format": "json", "sort": "datedesc",
            }, headers={"User-Agent": UA}, timeout=45, follow_redirects=True)
            arts = r.json().get("articles", [])
        except Exception:
            arts = []
        for a in arts:
            titulo = _clean(a.get("title"))
            link = a.get("url", "")
            sd = a.get("seendate")  # 20250920T123000Z -> deteccion
            det = None
            if sd and len(sd) >= 15:
                try:
                    det = datetime.strptime(sd, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    det = None
            add(titulo, link, a.get("domain") or "GDELT", None, det, "GDELT")

    return rows


def collect_indicators() -> list[dict]:
    rows: list[dict] = []
    countries = ";".join(WB_COUNTRIES)
    for ind, (_, unidad) in WB_INDICATORS.items():
        url = f"https://api.worldbank.org/v2/country/{countries}/indicator/{ind}"
        try:
            r = httpx.get(url, params={"date": WB_YEARS, "format": "json", "per_page": 2000},
                          headers={"User-Agent": UA}, timeout=45, follow_redirects=True)
            data = r.json()
            obs = data[1] if isinstance(data, list) and len(data) > 1 and data[1] else []
        except Exception:
            obs = []
        for o in obs:
            rows.append({
                "pais_iso3": o.get("countryiso3code", ""),
                "indicador_id": ind,
                "anio": o.get("date", ""),
                "valor": "" if o.get("value") is None else o.get("value"),
                "unidad": unidad,
                "fuente_url": f"{url}?date={WB_YEARS}&format=json",
                "fecha_extraccion": EXTRACCION,
                "licencia": "CC BY 4.0",
            })
    return rows


def collect_quakes() -> dict:
    try:
        r = httpx.get(USGS_URL, params=USGS_PARAMS, headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
        return r.json()
    except Exception:
        return {"type": "FeatureCollection", "features": []}


def _write_csv(path: str, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(RAW, exist_ok=True)
    print("A) noticias (TVN RSS + GDELT)...", flush=True)
    news = collect_news()
    n_path = os.path.join(RAW, "noticias.csv")
    _write_csv(n_path, news, ["id_noticia", "titulo", "url", "medio", "idioma",
                              "fecha_publicacion", "fecha_deteccion", "fecha_extraccion",
                              "tema", "origen", "alcance_texto"])
    tvn = sum(1 for x in news if x["origen"] == "RSS" and x["medio"] == "TVN Noticias")
    print(f"   {len(news)} noticias (TVN: {tvn})", flush=True)

    print("B) indicadores (Banco Mundial)...", flush=True)
    inds = collect_indicators()
    i_path = os.path.join(RAW, "indicadores.csv")
    _write_csv(i_path, inds, ["pais_iso3", "indicador_id", "anio", "valor", "unidad",
                              "fuente_url", "fecha_extraccion", "licencia"])
    print(f"   {len(inds)} filas (cuadrícula {len(WB_COUNTRIES)*len(WB_INDICATORS)*15} esperada)", flush=True)

    print("C) sismos (USGS 2024)...", flush=True)
    quakes = collect_quakes()
    q_path = os.path.join(RAW, "eventos.geojson")
    with open(q_path, "w", encoding="utf-8") as fh:
        json.dump(quakes, fh, ensure_ascii=False, indent=2)
    nq = len(quakes.get("features", []))
    print(f"   {nq} eventos sísmicos", flush=True)

    manifest = {
        "version": "Panamá · Señales y Evidencias v1",
        "fecha_corte_UTC": CORTE,
        "consultas": {
            "noticias": {"feeds": [f[0] for f in FEEDS], "gdelt": GDELT_QUERIES},
            "indicadores": {"paises": WB_COUNTRIES, "indicadores": list(WB_INDICATORS), "anios": WB_YEARS},
            "eventos": {"fuente": "USGS", "rango": "2024-01-01/2024-12-31",
                        "bbox_lat": [5, 12], "bbox_lon": [-86, -76], "magnitud_min": 3},
        },
        "cantidad_por_archivo": {"noticias.csv": len(news), "indicadores.csv": len(inds), "eventos.geojson": nq},
        "licencia_condiciones": {
            "TVN RSS": "Metadatos/uso referencial; no republicar artículos",
            "GDELT": "Uso vía API; no transfiere derechos de los medios enlazados",
            "Banco Mundial": "CC BY 4.0 (revisar excepciones por indicador)",
            "USGS": "Datos públicos (USGS)",
        },
        "sha256": {
            "noticias.csv": _sha256(n_path),
            "indicadores.csv": _sha256(i_path),
            "eventos.geojson": _sha256(q_path),
        },
        "transformaciones": [
            "Noticias: dedupe por URL (sin querystring); fecha_deteccion distinta de fecha_publicacion",
            "Indicadores: valores nulos conservados (no se rellenan con 0)",
            "Eventos: solo hechos sísmicos (no evidencia de inundación/pérdidas)",
        ],
    }
    m_path = os.path.join(ROOT, "data", "manifest.json")
    with open(m_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print("manifest ->", m_path, flush=True)
    print("F3 snapshot OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
