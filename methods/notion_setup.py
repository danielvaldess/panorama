"""Crea bases de datos y filas en Notion vía API (integración "New connection").

Requisitos:
    1) Crear una conexión en https://www.notion.so/profile/integrations
    2) Compartir la pagina destino con la conexion (••• → Connections)
    3) Exportar NOTION_TOKEN, y poner ROOT = id de la pagina destino

Uso:
    pip install httpx
    set NOTION_TOKEN=ntn_...
    python methods/notion_setup.py
"""
import os

import httpx

TOKEN = os.environ["NOTION_TOKEN"]           # ntn_...
ROOT = "REEMPLAZA_PAGE_ID"                     # id de la pagina contenedora
VER = "2022-06-28"                              # version valida para crear bases
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": VER, "Content-Type": "application/json"}
API = "https://api.notion.com/v1"


def create_db(title, props):
    r = httpx.post(f"{API}/databases", headers=H, json={
        "parent": {"type": "page_id", "page_id": ROOT},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": props,
    }, timeout=30)
    r.raise_for_status()
    print("db:", title, "->", r.json()["id"])
    return r.json()["id"]


def add_row(db_id, props):
    r = httpx.post(f"{API}/pages", headers=H, json={
        "parent": {"type": "database_id", "database_id": db_id}, "properties": props,
    }, timeout=30)
    if r.status_code != 200:
        print("row error", r.status_code, r.text[:200])


def t(v):  return {"title": [{"type": "text", "text": {"content": v}}]}
def rt(v): return {"rich_text": [{"type": "text", "text": {"content": v}}]}
def sel(v): return {"select": {"name": v}}
def num(v): return {"number": v}
def date(v): return {"date": {"start": v}}
def url(v): return {"url": v}


if __name__ == "__main__":
    db = create_db("Ejemplo", {
        "Nombre": {"title": {}},
        "Tipo": {"select": {"options": [{"name": x} for x in ["A", "B"]]}},
        "Estado": {"select": {"options": [{"name": x} for x in ["Activa", "Pausada"]]}},
        "Fecha": {"date": {}},
        "Enlace": {"url": {}},
        "Notas": {"rich_text": {}},
    })
    add_row(db, {"Nombre": t("Fila 1"), "Tipo": sel("A"), "Estado": sel("Activa"), "Notas": rt("")})
    print("DONE")
