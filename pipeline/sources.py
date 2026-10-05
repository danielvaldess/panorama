"""Fuentes de noticias: RSS de medios (feedparser) + GDELT. Normaliza a un formato común.

Estándares: feedparser (RSS/Atom), httpx (HTTP).
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

UA = "Panorama/0.1 (hackIAthon Panama 2026)"
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"

# Medios (RSS). Los que fallen se ignoran.
FEEDS = [
    ("TVN Noticias", "https://www.tvn-2.com/rss/"),
    ("La Prensa", "https://www.prensa.com/arc/outboundfeeds/rss/"),
    ("Google News", "https://news.google.com/rss/search?q=Panam%C3%A1&hl=es-419&gl=PA&ceid=PA:es-419"),
]


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _iso(s: str | None):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except Exception:
            return None


def _struct_iso(st):
    if not st:
        return None
    try:
        return datetime(*st[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None


def _id(title: str, url: str) -> str:
    return hashlib.sha1(f"{title}|{url}".encode("utf-8")).hexdigest()[:12]


def fetch_feed(name: str, url: str) -> list[dict]:
    out: list[dict] = []
    try:
        d = feedparser.parse(url, agent=UA)
    except Exception:
        return out
    for e in getattr(d, "entries", []):
        title = _clean(e.get("title"))
        link = (e.get("link") or "").strip()
        if not title or not link:
            continue
        published = _struct_iso(e.get("published_parsed") or e.get("updated_parsed")) \
            or _iso(e.get("published") or e.get("updated") or e.get("pubDate"))
        out.append({
            "title": title,
            "url": link,
            "source": name,
            "published": published,
            "snippet": _clean(e.get("summary") or e.get("description"))[:400],
            "topics": [],
            "id": _id(title, link),
        })
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
        out.append({
            "title": title,
            "url": url,
            "source": a.get("domain") or "GDELT",
            "published": None,
            "snippet": "",
            "topics": [],
            "id": _id(title, url),
        })
    return out


def fetch_all(gdelt_query: str = "Panamá", max_gdelt: int = 40) -> list[dict]:
    items: list[dict] = []
    for name, url in FEEDS:
        items += fetch_feed(name, url)
    items += fetch_gdelt(gdelt_query, max_gdelt)
    return items
