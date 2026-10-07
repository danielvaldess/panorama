"""Fuentes de noticias: RSS de medios (feedparser) + GDELT.
Solo se conservan las noticias de las últimas MAX_AGE_HOURS (por defecto 24)."""
from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from pipeline import process

UA = "Panorama/0.1 (hackIAthon Panama 2026)"
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_AGE_HOURS = int(os.environ.get("MAX_AGE_HOURS", "24"))

# Medios (RSS). El reto define noticias públicas como "TVN RSS + GDELT DOC 2.0".
FEEDS = [
    ("TVN Noticias", "https://www.tvn-2.com/rss/"),
]

# Fuentes declaradas por el reto (última página del documento).
CHALLENGE_SOURCES = [
    {"nombre": "TVN Noticias · RSS", "url": "https://www.tvn-2.com/rss/",
     "tipo": "RSS", "confiabilidad": 5,
     "licencia": "Metadatos/uso referencial; no republicar artículos"},
    {"nombre": "GDELT · DOC 2.0 (ArtList)", "url": "https://api.gdeltproject.org/api/v2/doc/doc",
     "tipo": "API", "confiabilidad": 4,
     "licencia": "Uso vía API; no transfiere derechos de los medios enlazados"},
    {"nombre": "Banco Mundial · Indicators v2", "url": "https://api.worldbank.org/v2/",
     "tipo": "API", "confiabilidad": 5, "licencia": "CC BY 4.0 (revisar excepciones)"},
    {"nombre": "USGS · Catálogo sísmico", "url": "https://earthquake.usgs.gov/fdsnws/event/1/",
     "tipo": "API", "confiabilidad": 5, "licencia": "Datos públicos (USGS)"},
]


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _struct_iso(st):
    if not st:
        return None
    try:
        return datetime(*st[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None


def _id(title: str, url: str) -> str:
    return hashlib.sha1(f"{title}|{url}".encode("utf-8")).hexdigest()[:12]


def _split_google(title: str) -> tuple[str, str]:
    """Google News: 'Titular - Medio' → (titular, medio)."""
    if " - " in title:
        head, _, outlet = title.rpartition(" - ")
        if head and outlet:
            return head.strip(), outlet.strip()
    return title, "Google News"


def fetch_feed(name: str, url: str) -> list[dict]:
    out: list[dict] = []
    try:
        d = feedparser.parse(url, agent=UA)
    except Exception:
        return out
    official_feed = name.startswith("Oficial")
    for e in getattr(d, "entries", []):
        raw_title = _clean(e.get("title"))
        link = (e.get("link") or "").strip()
        if not raw_title or not link:
            continue
        if name == "Google News" or official_feed:
            title, source = _split_google(raw_title)
        else:
            title, source = raw_title, name
        published = _struct_iso(e.get("published_parsed") or e.get("updated_parsed"))
        item = {
            "title": title, "url": link, "source": source, "published": published,
            "snippet": _clean(e.get("summary") or e.get("description"))[:400],
            "topics": [], "id": _id(title, link),
        }
        item["official"] = process.is_official(link) or (official_feed and process.is_official_source_name(source) and process.is_editorial_signal(item))
        out.append(item)
    return out


def fetch_gdelt(query: str, maxrecords: int = 50) -> list[dict]:
    """Artículos recientes de GDELT (global, multilingüe, gratis). Máx. 1 req/5 s."""
    out: list[dict] = []
    time.sleep(5)
    try:
        r = httpx.get(GDELT, params={
            "query": query, "mode": "artlist", "maxrecords": maxrecords,
            "format": "json", "sort": "datedesc",
        }, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        r.raise_for_status()
        arts = r.json().get("articles", [])
    except Exception:
        return out
    for a in arts:
        title = _clean(a.get("title"))
        url = a.get("url", "")
        if not title or not url:
            continue
        if not process.is_panamanian_outlet(url):
            continue  # solo salidas panameñas (evita "Panama City, Florida", ruido global)
        published = None
        sd = a.get("seendate")  # p. ej. 20250920T123000Z
        if sd and len(sd) >= 15:
            try:
                published = datetime.strptime(sd, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                published = None
        out.append({
            "title": title, "url": url, "source": a.get("domain") or "GDELT",
            "published": published, "snippet": "", "topics": [], "id": _id(title, url),
        })
    return out


def _recent(items: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    out: list[dict] = []
    for it in items:
        p = it.get("published")
        if not p:
            continue  # sin fecha -> no es "de hoy"
        try:
            if datetime.fromisoformat(p) >= cutoff:
                out.append(it)
        except Exception:
            continue
    return out


def fetch_all(gdelt_query: str = "Panamá", max_gdelt: int = 40) -> list[dict]:
    items: list[dict] = []
    for name, url in FEEDS:
        items += fetch_feed(name, url)
    items += fetch_gdelt(gdelt_query, max_gdelt)
    return _recent(items)
