"""Renderiza assets: logo, favicon y diagramas (PNG) con la estética de la app."""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
WEB = os.path.join(ROOT, "web")
DIA = os.path.join(DOCS, "diagrams")
os.makedirs(DIA, exist_ok=True)

CIRCLE = """<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
<circle cx="60" cy="60" r="40" fill="none" stroke="#005588" stroke-width="11"/>
<g stroke="#005588" stroke-width="11" stroke-linecap="round">
<path d="M60 6 v16"/><path d="M60 98 v16"/><path d="M6 60 h16"/><path d="M98 60 h16"/></g></svg>"""

FONT = '<link href="https://fonts.googleapis.com/css2?family=Raleway:wght@600;700;800&family=Oxygen:wght@300;400;700&display=swap" rel="stylesheet">'

BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0;font-family:"Oxygen",system-ui,sans-serif}
body{background:#f5f6f8;padding:26px}
.wrap{background:#fff;border:1px solid #e3e6ea;border-radius:16px;padding:22px;box-shadow:0 6px 20px rgba(0,85,136,.06)}
h2{font-family:"Raleway",sans-serif;font-weight:800;color:#2a2a2a;font-size:18px;margin-bottom:2px}
.sub{color:#6b6b6b;font-size:12.5px;margin-bottom:18px}
.row{display:flex;align-items:stretch;gap:8px}
.step{flex:1;border:1px solid #e3e6ea;border-radius:14px;padding:14px 12px;background:#fff;min-width:150px;position:relative;overflow:hidden}
.step::before{content:"";position:absolute;top:0;left:0;right:0;height:4px;background:#005588}
.badge{width:26px;height:26px;border-radius:50%;background:#005588;color:#fff;font-family:"Raleway",sans-serif;font-weight:800;font-size:13px;display:flex;align-items:center;justify-content:center}
.ico{width:26px;height:26px;color:#0077c8}
.t{font-family:"Raleway",sans-serif;font-weight:700;color:#2a2a2a;font-size:14.5px;margin-top:8px}
.s{color:#6b6b6b;font-size:11.5px;margin-top:3px;line-height:1.35}
.chev{display:flex;align-items:center;color:#c7c7c7;font-size:22px;font-weight:800}
.lane{margin-bottom:14px}
.lane h4{font-family:"Raleway",sans-serif;font-size:11.5px;color:#6b6b6b;text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px}
.box{flex:1;min-width:150px;border:1px solid #e3e6ea;border-radius:12px;padding:12px 14px;background:#fff;position:relative;overflow:hidden}
.box::before{content:"";position:absolute;top:0;left:0;right:0;height:4px}
.box.blue::before{background:#005588}.box.cyan::before{background:#06accb}.box.red::before{background:#e00710}
.box .bt{display:flex;align-items:center;gap:8px}
.box b{color:#2a2a2a;font-size:13.5px;font-family:"Raleway",sans-serif}
.box span{color:#6b6b6b;font-size:11.5px;display:block;margin-top:3px}
"""

ICONS = {
    "load": '<path d="M12 3v10m0 0l-4-4m4 4l4-4"/><path d="M4 17h16"/>',
    "org": '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    "ctx": '<path d="M9 15l6-6"/><path d="M8 12l-2 2a3 3 0 104 4l2-2"/><path d="M16 12l2-2a3 3 0 10-4-4l-2 2"/>',
    "prio": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "expl": '<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h6M9 16h6"/>',
    "prod": '<path d="M4 20l4-1 9-9-3-3-9 9z"/><path d="M14 7l3 3"/>',
    "rev": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
}


def icon(name):
    return f'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'


def step(n, name, title, sub):
    return f'<div class="step"><div style="display:flex;justify-content:space-between;align-items:center"><span class="badge">{n}</span>{icon(name)}</div><div class="t">{title}</div><div class="s">{sub}</div></div>'


FLUJO = f"""<!doctype html><html><head><meta charset="utf-8">{FONT}<style>{BASE_CSS}</style></head><body>
<div id="diagram" class="wrap">
  <h2>Cómo funciona</h2>
  <div class="sub">De la señal a la decisión: siete pasos, siempre con revisión humana.</div>
  <div class="row">
    {step(1,"load","Cargar","Snapshot público congelado")}
    <div class="chev">›</div>
    {step(2,"org","Organizar","Clasificar y agrupar por evento")}
    <div class="chev">›</div>
    {step(3,"ctx","Contextualizar","Noticia ↔ dato oficial")}
    <div class="chev">›</div>
    {step(4,"prio","Priorizar","Puntaje explicable 0–100")}
    <div class="chev">›</div>
    {step(5,"expl","Explicar","Ficha con evidencia")}
    <div class="chev">›</div>
    {step(6,"prod","Producir","Brief, guion y copy con citas")}
    <div class="chev">›</div>
    {step(7,"rev","Revisar","Decisión del editor")}
  </div>
</div></body></html>"""


def box(color, title, sub):
    return f'<div class="box {color}"><div class="bt">{icon("org")}<b>{title}</b></div><span>{sub}</span></div>'


ARQ = f"""<!doctype html><html><head><meta charset="utf-8">{FONT}<style>{BASE_CSS}</style></head><body>
<div id="diagram" class="wrap">
  <h2>Arquitectura</h2>
  <div class="sub">Snapshot reproducible → núcleo determinista → producto → control humano.</div>
  <div class="lane"><h4>Fuentes públicas</h4><div class="row">
    {box("cyan","TVN RSS","titulares y enlaces")}{box("cyan","GDELT","noticias del mundo")}{box("cyan","Banco Mundial","indicadores 2010–2024")}{box("cyan","USGS","sismos 2024")}
  </div></div>
  <div class="lane"><h4>Ingesta y reproducibilidad</h4><div class="row">
    {box("blue","Snapshot congelado","data/raw + manifest (SHA-256)")}
  </div></div>
  <div class="lane"><h4>Núcleo</h4><div class="row">
    {box("blue","Dedupe y agrupación","repetición vs. fuentes independientes")}{box("blue","Prioridad explicable","P = 30R+25I+20U+15N+10E")}{box("blue","Borrador con citas","brief · guion · copy")}
  </div></div>
  <div class="lane"><h4>Producto</h4><div class="row">
    {box("red","Mesa editorial","ficha por tema")}{box("red","Revisión humana","nuevo → … → descartado")}{box("red","Notion","bitácora · decisiones · pruebas")}
  </div></div>
</div></body></html>"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 240, "height": 240}, device_scale_factor=2)
        pg.set_content(f"<body style='margin:0'><div style='width:240px;height:240px'>{CIRCLE}</div></body>")
        pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(DOCS, "logo.png"), omit_background=True)
        pg2 = b.new_page(viewport={"width": 180, "height": 180}, device_scale_factor=2)
        pg2.set_content(f"<body style='margin:0'><div style='width:180px;height:180px'>{CIRCLE}</div></body>")
        pg2.wait_for_timeout(150)
        pg2.screenshot(path=os.path.join(WEB, "favicon.png"), omit_background=True)

        jobs = [(FLUJO, os.path.join(DIA, "flujo.png"), 1560), (FLUJO, os.path.join(WEB, "como-funciona.png"), 1180),
                (ARQ, os.path.join(DIA, "arquitectura.png"), 1100)]
        for html, out, w in jobs:
            page = b.new_page(viewport={"width": w, "height": 700}, device_scale_factor=2)
            page.set_content(html)
            page.wait_for_timeout(500)
            page.locator("#diagram").screenshot(path=out)
            page.close()
        b.close()
    print("assets ok")


if __name__ == "__main__":
    main()
