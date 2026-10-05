"""Fuentes de noticias: RSS de medios + GDELT. Normaliza a un formato común.

Uso:
    python -m pipeline.run
    pip install httpx
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

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


def _local(tag: str) -> str:
    return tag.split("}")[-1].lower()


def _child(el, names):
    for c in list(el):
        if _local(c.tag) in names:
            return "".join(c.itertext())
    return ""


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


def _id(title: str, url: str) -> str:
    return hashlib.sha1(f"{title}|{url}".encode("utf-8")).hexdigest()[:12]


def fetch_feed(name: str, url: str) -> list[dict]:
    out: list[dict] = []
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return out
    for it in root.iter():
        if _local(it.tag) not in ("item", "entry"):
            continue
        title = _clean(_child(it, {"title"}))
        link = _child(it, {"link"})
        if not link:
            for c in list(it):
                if _local(c.tag) == "link" and c.get("href"):
                    link = c.get("href")
                    break
        if not title or not link:
            continue
        out.append({
            "title": title,
            "url": link.strip(),
            "source": name,
            "published": _iso(_child(it, {"pubdate", "published", "updated", "date"})),
            "snippet": _clean(_child(it, {"description", "summary", "content"}))[:400],
            "topics": [],
            "id": _id(title, link),
        })
    return out


def fetch_gdelt(query: str, maxrecords: int = 50) -> list[dict]:
    """Artículos recientes de GDELT (global, multilingüe, gratis)."""
    out: list[dict] = []
    time.sleep(5)  # GDELT: máx. 1 request cada 5 s
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
