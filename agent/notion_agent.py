"""Agente respaldado por Notion.

Lee entradas "Pendiente" de una base de Notion, las valida con REGLAS
deterministas, redacta un resumen con IA (OpenRouter) y ACTUALIZA el registro.
Demuestra el patrón de los retos: dato → validación → IA → decisión/registro.

Uso:
    set NOTION_TOKEN=ntn_...
    set OPENROUTER_API_KEY=sk-or-...
    python agent/notion_agent.py

Variables:
    NOTION_TOKEN            (requerido)
    NOTION_ENTRADAS_DB      id de la base (por defecto la del demo)
    OPENROUTER_API_KEY      opcional; sin ella usa plantilla local
    OPENROUTER_MODELS       lista separada por comas (por defecto: gemma, nemotron)
"""
import os
import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DB = os.environ.get("NOTION_ENTRADAS_DB", "3f04692c-7103-8145-9000-d5e3f3fb0417")
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OR_MODELS = os.environ.get(
    "OPENROUTER_MODELS",
    "inclusionai/ling-3.0-flash-sante:free,dots-studio/dots-3-note-preview:free,nvidia/nemotron-3.5-lightning:free",
).split(",")

NH = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
API = "https://api.notion.com/v1"

# --- reglas deterministas (la IA no decide esto) ---
TEMA_PESO = {"Nacionales": 0.90, "Economía": 0.80, "Gobierno": 0.70,
             "Seguridad": 0.85, "Salud": 0.75, "Internacional": 0.60}


def score(tema: str, citas: int) -> float:
    if citas <= 0:
        return 0.0
    return min(1.0, TEMA_PESO.get(tema, 0.5) + min(citas, 3) * 0.05)


def confianza(citas: int) -> str:
    return "Alto" if citas >= 2 else "Medio" if citas == 1 else "Bajo"


def estado(citas: int) -> str:
    return "Sin evidencia" if citas <= 0 else "Priorizado"


def limpiar(texto: str) -> str:
    """Devuelve solo el resumen. Si el modelo expuso razonamiento en inglés, lo descarta."""
    t = (texto or "").strip()
    if not t:
        return ""
    low = t.lower()
    if "the user wants" in low or "thinking process" in low or "we need to" in low or "analyze the" in low:
        for q in reversed(re.findall(r'[«"“]([^"”»]{15,240})[»"”]', t)):
            if len(q.split()) >= 4:
                return q.strip()
        for s in re.split(r"[\n.]+", t):
            s = s.strip()
            if 6 <= len(s.split()) <= 40 and re.search(r"[áéíóúñü¿¡]", s):
                return s
        return ""      # razonamiento sin resumen en español -> descartar
    return t


def resumen_ia(titular: str, tema: str, citas: int, log: list) -> str:
    if citas <= 0:
        log.append("local (abstención)")
        return "Sin evidencia suficiente para resumir."     # abstención correcta
    if not OR_KEY:
        log.append("local (sin key)")
        return f"{titular} (resumen local; tema: {tema})."

    prompt = (
        "Eres un asistente editorial de una mesa de redacción. Responde ÚNICAMENTE con "
        "un resumen de máximo 30 palabras, neutral y verificable, del siguiente titular. "
        "No incluyas pasos ni explicaciones. No inventes datos.\n"
        f"Titular: {titular}\nTema: {tema}"
    )
    for model in OR_MODELS:
        model = model.strip()
        try:
            r = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1200},
                timeout=60,
            )
            if r.status_code == 200:
                msg = r.json()["choices"][0]["message"]
                out = limpiar(msg.get("content") or "")
                if out:
                    log.append(model)
                    return out[:1900]
            else:
                log.append(f"{model}: {r.status_code}")
        except Exception as e:
            log.append(f"{model}: error")
    log.append("local (fallback)")
    return f"{titular} (resumen local; tema: {tema})."


def main() -> int:
    if not NOTION_TOKEN:
        print("Falta NOTION_TOKEN")
        return 1

    q = httpx.post(f"{API}/databases/{DB}/query", headers=NH, json={
        "filter": {"property": "Estado", "select": {"equals": "Pendiente"}}, "page_size": 50,
    }, timeout=30)
    q.raise_for_status()
    pages = q.json()["results"]
    print(f"Pendientes: {len(pages)}")

    for pg in pages:
        props = pg["properties"]
        titular = "".join(x.get("plain_text", "") for x in props["Titular"]["title"])
        tema = (props.get("Tema", {}).get("select") or {}).get("name", "")
        citas = int(props.get("Citas", {}).get("number") or 0)

        s, est, conf = score(tema, citas), estado(citas), confianza(citas)
        log: list = []
        res = resumen_ia(titular, tema, citas, log)

        httpx.patch(f"{API}/pages/{pg['id']}", headers=NH, json={"properties": {
            "Score": {"number": round(s, 2)},
            "Confianza": {"select": {"name": conf}},
            "Estado": {"select": {"name": est}},
            "Resumen": {"rich_text": [{"type": "text", "text": {"content": res[:1900]}}]},
        }}, timeout=30).raise_for_status()

        print(f"  [{est:14s}] score={s:.2f} conf={conf:5s} fuente={log} | {titular[:46]}")

    print("Listo. Revisa la base en Notion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
