"""Panorama — pipeline de priorización editorial con evidencia.

    fetch (medios + GDELT) -> dedupe -> cluster de fuentes -> prioridad -> reporte

Uso:
    python -m pipeline.run                 # solo determinista
    python -m pipeline.run --ai            # + resumen con IA (OpenRouter)
    python -m pipeline.run --notion        # + publicar fichas en Notion
    pip install httpx
"""
from __future__ import annotations

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval import metrics
from pipeline import process, sources

USER_TOPICS = ["Panamá", "economía", "presupuesto", "Canal", "seguridad", "salud", "Asamblea"]


def ai_summary(title: str, sources_list: list[dict]) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return ""
    import httpx
    model = os.environ.get("OPENROUTER_MODEL", "inclusionai/ling-3.0-flash-sante:free")
    srcs = "; ".join(s["name"] for s in sources_list) or "sin fuente"
    prompt = ("Eres un asistente editorial. Responde SOLO con un resumen neutral de máximo "
              "30 palabras, verificable, sobre este titular. No inventes datos.\n"
              f"Titular: {title}\nFuentes: {srcs}")
    try:
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 900},
                       timeout=60)
        if r.status_code == 200:
            c = r.json()["choices"][0]["message"].get("content") or ""
            return c.strip()[:400]
    except Exception:
        pass
    return ""


def store_notion(fichas: list[dict]) -> int:
    import httpx
    tok = os.environ.get("NOTION_TOKEN", "")
    db = os.environ.get("NOTION_DB", "")
    if not tok or not db:
        return 0
    H = {"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    n = 0
    for f in fichas:
        src = f["sources"][0] if f["sources"] else {"name": "", "url": ""}
        props = {
            "Titular": {"title": [{"type": "text", "text": {"content": f["title"][:1900]}}]},
            "Fuente": {"rich_text": [{"type": "text", "text": {"content": src["name"]}}]},
            "Score": {"number": f["score"]},
            "Confianza": {"select": {"name": f["confidence"]}},
            "Estado": {"select": {"name": f["status"]}},
            "Citas": {"number": len(f["sources"])},
        }
        if src["url"]:
            props["Enlace"] = {"url": src["url"]}
        r = httpx.post("https://api.notion.com/v1/pages", headers=H,
                       json={"parent": {"type": "database_id", "database_id": db}, "properties": props}, timeout=30)
        n += r.status_code == 200
    return n


def main() -> int:
    ap = argparse.ArgumentParser(prog="pipeline.run")
    ap.add_argument("--ai", action="store_true", help="resúmenes con IA")
    ap.add_argument("--notion", action="store_true", help="publicar en Notion")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--query", default="Panamá", help="consulta GDELT")
    args = ap.parse_args()

    print("1) Leyendo fuentes…")
    raw = sources.fetch_all(gdelt_query=args.query)
    print(f"   {len(raw)} ítems brutos")

    print("2) Dedupe…")
    deduped = process.dedupe(raw)
    print(f"   {len(deduped)} tras dedupe")

    print("3) Agrupando fuentes y priorizando…")
    groups = process.cluster(deduped)
    fichas = process.priority(groups, USER_TOPICS)

    if args.ai:
        print("4) Resumiendo con IA…")
        for f in fichas[: args.limit]:
            f["summary"] = ai_summary(f["title"], f["sources"])

    print("\n--- Prioridades del día (prioridad · verificación) ---")
    for f in fichas[: args.limit]:
        srcs = ", ".join(s["name"] for s in f["sources"])
        v = f.get("verification") or {}
        ev = f"indep={v.get('independent', 0)} ofic={v.get('official', 0)} eco={v.get('echo', 0)}"
        print(f"  [{f['score']:>4}] {f['state']:<13} ({ev}) {f['title'][:56]}")
        print(f"        {srcs}")
        if f.get("summary"):
            print(f"        -> {f['summary']}")

    m = metrics.summarize(raw, deduped, fichas)
    print("\n--- Métricas ---")
    print(json.dumps(m, ensure_ascii=False, indent=2))

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "panorama.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(fichas, fh, ensure_ascii=False, indent=2)
    print("\nGuardado:", out)

    if args.notion:
        n = store_notion(fichas[: args.limit])
        print(f"Notion: {n} fichas publicadas")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
