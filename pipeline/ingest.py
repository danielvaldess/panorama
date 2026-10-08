"""Construye el snapshot congelado de datos públicos.

Paquete: "Panamá · Señales y Evidencias v1"
- A · noticias públicas: TVN RSS + GDELT DOC 2.0  -> data/raw/noticias.csv
- B · Banco Mundial Indicators v2 (6x6, 2010-2024) -> data/raw/indicadores.csv
- C · USGS sismos 2024                             -> data/raw/eventos.geojson
- manifest + diccionario                            -> data/manifest.json, data/diccionario.md

Uso:  python -m pipeline.ingest                      # snapshot completo (fuentes en vivo)
      python -m pipeline.ingest --filtrar-snapshot   # solo aplica el rango del contrato §7
                                                     # al CSV congelado (sin red)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import feedparser
import httpx

from pipeline import process
from pipeline import score as score_mod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
UA = "Panorama/0.1 (hackIAthon Panama 2026)"
NOW = datetime.now(timezone.utc)
CORTE = NOW.isoformat()
EXTRACCION = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")

# Contrato de datos §7 (corregido por coordinación): ver NEWS_WINDOW_* abajo.

FEEDS = [
    ("TVN Noticias", "https://www.tvn-2.com/rss/"),
]
# No usamos Google News como fuente: es agregador, no procedencia primaria.
OFFICIAL_FEEDS: list[tuple[str, str]] = []
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERIES = ["Panama", "Panama logistica", "Panama turismo", "Panama economia", "Panama terremoto"]

# Ventana de noticias del reto (coordinación): desde 2025-10-02 hasta el último mes completo (2026-09-30).
# El PDF (§7) trae [2024-01-01, 2025-10-01) — desfasado un año; se corrige aquí.
NEWS_WINDOW_START = os.environ.get("NEWS_WINDOW_START", "2025-10-02")
NEWS_WINDOW_END = os.environ.get("NEWS_WINDOW_END", "2026-09-30")
NEWS_TARGET = int(os.environ.get("NEWS_TARGET", "240"))
MIN_NOTICIAS = int(os.environ.get("MIN_NOTICIAS", "50"))  # guardia: no sobrescribir si quedan menos

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
    "logistica_canal": ["canal", "puerto", "logística", "logistica", "tránsito", "esclusa", "naviera", "carga"],
    "turismo": ["turismo", "turista", "hotel", "vuelo", "crucero", "playa", "vacacion"],
    "servicios_publicos": ["agua", "electricidad", "energía", "aseo", "metro", "transporte", "salud", "hospital", "educación"],
    "eventos_naturales": ["sismo", "terremoto", "inundación", "lluvia", "huracán", "volcán", "sequía"],
    "regulacion": ["regula", "decreto", "ley", "asamblea", "contrato", "licitación", "tribunal", "corte"],
    "relaciones_exteriores_comercio": ["canciller", "relaciones exteriores", "diplom", "tratado", "mercosur",
                              "comercio exterior", "cumbre", "onu", "embajad", "exterior"],
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


def _gdelt_query(query: str, tries: int = 3, startdatetime: str | None = None, enddatetime: str | None = None) -> list[dict]:
    """Consulta GDELT (1 req/5 s) con caché en disco y reintentos ante 429/timeout."""
    cpath = os.path.join(RAW, "_gdelt_cache", f"{query.replace(' ', '_')}_{startdatetime or ''}_{enddatetime or ''}.json")
    if os.path.exists(cpath):
        try:
            with open(cpath, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    for i in range(tries):
        time.sleep(5 if i == 0 else 6)
        try:
            params = {
                "query": query, "mode": "artlist", "maxrecords": 250,
                "format": "json", "sort": "datedesc",
            }
            if startdatetime:
                params["startdatetime"] = startdatetime
            if enddatetime:
                params["enddatetime"] = enddatetime
            r = httpx.get(GDELT_URL, params=params, headers={"User-Agent": UA}, timeout=90, follow_redirects=True)
            if r.status_code != 200:
                continue
            arts = (r.json() or {}).get("articles", []) or []
            os.makedirs(os.path.dirname(cpath), exist_ok=True)
            with open(cpath, "w", encoding="utf-8") as fh:
                json.dump(arts, fh, ensure_ascii=False)
            return arts
        except Exception:
            continue
    return []


def _month_windows() -> list[tuple[str, str]]:
    """Divide [NEWS_WINDOW_START, NEWS_WINDOW_END] en ventanas mensuales (GDELT por fechas)."""
    from calendar import monthrange
    start = datetime.strptime(NEWS_WINDOW_START, "%Y-%m-%d")
    end = datetime.strptime(NEWS_WINDOW_END, "%Y-%m-%d")
    out: list[tuple[str, str]] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        w_start = max(start, datetime(y, m, 1))
        w_end = min(end, datetime(y, m, monthrange(y, m)[1]))
        if w_start <= w_end:
            out.append((w_start.strftime("%Y%m%d000000"), w_end.strftime("%Y%m%d235959")))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


CAMPOS_NOTICIAS = ["id_noticia", "titulo", "url", "medio", "idioma",
                   "fecha_publicacion", "fecha_deteccion", "fecha_extraccion",
                   "tema", "origen", "alcance_texto", "descripcion"]


def _aplicar_rango(rows: list[dict]) -> tuple[list[dict], dict]:
    """Conserva solo noticias dentro de la ventana del reto (corrección de coordinación).

    Usa `fecha_publicacion` y, si está vacía, `fecha_deteccion`. Devuelve (filas_en_rango, estadísticas).
    """
    dentro: list[dict] = []
    excluidas_rango = 0
    sin_fecha = 0
    for r in rows:
        fecha = (r.get("fecha_publicacion") or "").strip() or (r.get("fecha_deteccion") or "").strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}", fecha):
            sin_fecha += 1
        elif NEWS_WINDOW_START <= fecha[:10] <= NEWS_WINDOW_END:
            dentro.append(r)
        else:
            excluidas_rango += 1
    stats = {"total_original": len(rows), "incluidas": len(dentro),
             "excluidas_por_rango": excluidas_rango, "excluidas_sin_fecha": sin_fecha}
    return dentro, stats


def collect_news() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    def add(titulo, url, medio, publicacion, deteccion, origen, descripcion=""):
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
            "descripcion": (descripcion or "")[:400],
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
            desc = _clean(e.get("summary") or e.get("description"))
            add(titulo, link, name, pub, pub or EXTRACCION, "RSS", desc)

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
            item = {"title": titulo, "url": link, "source": medio}
            origen = "Oficial" if (process.is_official(link) or (process.is_official_source_name(medio) and process.is_editorial_signal(item))) else "Agregador"
            add(titulo, link, medio, pub, pub or EXTRACCION, origen)

    # GDELT dividido por fechas (ventanas mensuales) dentro de la ventana del reto.
    # Se recorre de lo más reciente a lo más antiguo y se detiene al alcanzar la meta.
    for sd, ed in reversed(_month_windows()):
        arts = _gdelt_query("Panama", startdatetime=sd, enddatetime=ed)
        for a in arts:
            titulo = _clean(a.get("title"))
            link = a.get("url", "")
            if not process.is_panamanian_outlet(link):
                continue  # solo salidas panameñas (evita "Panama City, Florida", ruido global)
            sdet = a.get("seendate")  # 20250920T123000Z -> deteccion
            det = None
            if sdet and len(sdet) >= 15:
                try:
                    det = datetime.strptime(sdet, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    det = None
            add(titulo, link, a.get("domain") or "GDELT", None, det, "GDELT")
        if len(rows) >= NEWS_TARGET:
            break

    return _aplicar_rango(rows)


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


def filtrar_snapshot() -> int:
    """Aplica el rango del contrato §7 al snapshot congelado (sin red) y actualiza el manifest."""
    n_path = os.path.join(RAW, "noticias.csv")
    if not os.path.exists(n_path):
        print("No existe data/raw/noticias.csv; corre `python -m pipeline.ingest` primero.", flush=True)
        return 1
    with open(n_path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    dentro, stats = _aplicar_rango(rows)
    _write_csv(n_path, dentro, CAMPOS_NOTICIAS)

    m_path = os.path.join(ROOT, "data", "manifest.json")
    manifest: dict = {}
    if os.path.exists(m_path):
        with open(m_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    manifest.setdefault("cantidad_por_archivo", {})["noticias.csv"] = len(dentro)
    manifest.setdefault("sha256", {})["noticias.csv"] = _sha256(n_path)
    manifest["rango_fechas_noticias"] = {"inicio_inclusivo": NEWS_WINDOW_START, "fin_inclusivo": NEWS_WINDOW_END, **stats}
    nota = (f"Noticias: ventana de coordinación [{NEWS_WINDOW_START}, {NEWS_WINDOW_END}] — "
            f"{stats['incluidas']} de {stats['total_original']} (excluidas "
            f"{stats['excluidas_por_rango']} por rango, {stats['excluidas_sin_fecha']} sin fecha)")
    trans = manifest.setdefault("transformaciones", [])
    trans[:] = [t for t in trans if not t.startswith("Noticias: ventana de coordinación")] + [nota]
    with open(m_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print(f"Snapshot filtrado: {stats['incluidas']} de {stats['total_original']} noticias "
          f"en [{NEWS_WINDOW_START}, {NEWS_WINDOW_END}]", flush=True)
    print(f"   excluidas: {stats['excluidas_por_rango']} por rango, "
          f"{stats['excluidas_sin_fecha']} sin fecha", flush=True)
    print("manifest ->", m_path, flush=True)
    return 0


def main() -> int:
    if "--filtrar-snapshot" in sys.argv:
        return filtrar_snapshot()
    os.makedirs(RAW, exist_ok=True)
    print("A) noticias (TVN RSS + GDELT)...", flush=True)
    news, filtro = collect_news()
    if len(news) < MIN_NOTICIAS:
        print(f"   ABORTADO: solo {len(news)} noticias en la ventana [{NEWS_WINDOW_START}, {NEWS_WINDOW_END}] "
              f"(mínimo {MIN_NOTICIAS}); no se sobrescribe el snapshot congelado.", flush=True)
        return 1
    n_path = os.path.join(RAW, "noticias.csv")
    _write_csv(n_path, news, CAMPOS_NOTICIAS)
    tvn = sum(1 for x in news if x["origen"] == "RSS" and x["medio"] == "TVN Noticias")
    print(f"   {len(news)} noticias en rango (TVN: {tvn}; excluidas: "
          f"{filtro['excluidas_por_rango']} por rango, {filtro['excluidas_sin_fecha']} sin fecha)",
          flush=True)

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
        "rules_version": score_mod.RULES_VERSION,
        "fecha_corte_UTC": CORTE,
        "consultas": {
            "noticias": {
                "feeds": [f[0] for f in FEEDS],
                "gdelt": {"consulta_base": "Panama", "temas": GDELT_QUERIES[1:]},
                "ventana": f"{NEWS_WINDOW_START}/{NEWS_WINDOW_END}",
                "fraccionamiento": "mensual (GDELT startdatetime/enddatetime)",
            },
            "indicadores": {"paises": WB_COUNTRIES, "indicadores": list(WB_INDICATORS), "anios": WB_YEARS},
            "eventos": {"fuente": "USGS", "rango": "2024-01-01/2024-12-31",
                        "bbox_lat": [5, 12], "bbox_lon": [-86, -76], "magnitud_min": 3},
        },
        "cantidad_por_archivo": {"noticias.csv": len(news), "indicadores.csv": len(inds), "eventos.geojson": nq},
        "rango_fechas_noticias": {"inicio_inclusivo": NEWS_WINDOW_START, "fin_inclusivo": NEWS_WINDOW_END, **filtro},
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
            "Noticias: filtradas a la ventana del reto y dedupe por URL (sin querystring); fecha_deteccion distinta de fecha_publicacion",
            "Noticias: GDELT dividido por ventanas mensuales y filtrado a salidas panameñas",
            "Google News excluido (agregador, no fuente primaria)",
            f"Noticias: ventana de coordinación [{NEWS_WINDOW_START}, {NEWS_WINDOW_END}] — "
            f"{filtro['incluidas']} de {filtro['total_original']} (excluidas "
            f"{filtro['excluidas_por_rango']} por rango, {filtro['excluidas_sin_fecha']} sin fecha)",
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
