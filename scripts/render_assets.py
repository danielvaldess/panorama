"""Renderiza assets: favicon, logo y diagramas (PNG) para el README."""
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

FLUJO = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0;font-family:"Segoe UI",Arial,sans-serif}
body{background:#fff;padding:28px}
.row{display:flex;align-items:stretch;gap:10px}
.step{flex:1;border:1px solid #c7c7c7;border-top:4px solid #005588;border-radius:8px;padding:14px 12px;background:#fff;min-width:150px}
.n{font-size:12px;font-weight:800;color:#e00710;letter-spacing:.5px}
.t{font-weight:800;color:#2a2a2a;font-size:15px;margin-top:4px}
.s{color:#6b6b6b;font-size:12px;margin-top:4px;line-height:1.35}
.arrow{display:flex;align-items:center;color:#9b9b9b;font-size:20px}
</style></head><body>
<div id="diagram">
  <div class="row">
    <div class="step"><div class="n">PASO 1</div><div class="t">Cargar</div><div class="s">Snapshot público congelado</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="n">PASO 2</div><div class="t">Organizar</div><div class="s">Clasificar y agrupar por evento</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="n">PASO 3</div><div class="t">Contextualizar</div><div class="s">Noticia ↔ dato oficial</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="n">PASO 4</div><div class="t">Priorizar</div><div class="s">Puntaje explicable 0–100</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="n">PASO 5</div><div class="t">Explicar</div><div class="s">Ficha con evidencia</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="n">PASO 6</div><div class="t">Producir</div><div class="s">Brief · guion · copy con citas</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="n">PASO 7</div><div class="t">Revisar</div><div class="s">Decisión humana</div></div>
  </div>
</div></body></html>"""

ARQ = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0;font-family:"Segoe UI",Arial,sans-serif}
body{background:#fff;padding:28px}
.lane{margin-bottom:14px}
.lane h4{font-size:12px;color:#6b6b6b;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;font-weight:700}
.row{display:flex;gap:10px;flex-wrap:wrap}
.box{flex:1;min-width:150px;border:1px solid #c7c7c7;border-radius:8px;padding:12px 14px;background:#fff}
.box.blue{border-top:4px solid #005588}
.box.cyan{border-top:4px solid #06accb}
.box.red{border-top:4px solid #e00710}
.box b{color:#2a2a2a;font-size:14px;display:block}
.box span{color:#6b6b6b;font-size:12px}
</style></head><body>
<div id="diagram">
  <div class="lane"><h4>Fuentes públicas</h4><div class="row">
    <div class="box cyan"><b>TVN RSS</b><span>titulares y enlaces</span></div>
    <div class="box cyan"><b>GDELT</b><span>noticias del mundo</span></div>
    <div class="box cyan"><b>Banco Mundial</b><span>indicadores 2010–2024</span></div>
    <div class="box cyan"><b>USGS</b><span>sismos 2024</span></div>
  </div></div>
  <div class="lane"><h4>Ingesta y reproducibilidad</h4><div class="row">
    <div class="box blue"><b>Snapshot congelado</b><span>data/raw + manifest (SHA-256)</span></div>
  </div></div>
  <div class="lane"><h4>Núcleo</h4><div class="row">
    <div class="box blue"><b>Dedupe y agrupación</b><span>eco vs. fuentes independientes</span></div>
    <div class="box blue"><b>Prioridad explicable</b><span>P = 30R+25I+20U+15N+10E</span></div>
    <div class="box blue"><b>Borrador con citas</b><span>brief · guion · copy</span></div>
  </div></div>
  <div class="lane"><h4>Producto</h4><div class="row">
    <div class="box red"><b>API + Interfaz</b><span>mesa editorial · ficha por tema</span></div>
    <div class="box red"><b>Revisión humana</b><span>nuevo → … → descartado</span></div>
    <div class="box red"><b>Notion</b><span>bitácora · decisiones · pruebas</span></div>
  </div></div>
</div></body></html>"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        # logo + favicon
        pg = b.new_page(viewport={"width": 240, "height": 240}, device_scale_factor=2)
        pg.set_content(f"<body style='margin:0'><div style='width:240px;height:240px'>{CIRCLE}</div></body>")
        pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(DOCS, "logo.png"), omit_background=True)
        pg2 = b.new_page(viewport={"width": 180, "height": 180}, device_scale_factor=2)
        pg2.set_content(f"<body style='margin:0'><div style='width:180px;height:180px'>{CIRCLE}</div></body>")
        pg2.wait_for_timeout(150)
        pg2.screenshot(path=os.path.join(WEB, "favicon.png"), omit_background=True)
        # diagrams
        for html, out, w in [(FLUJO, "flujo.png", 1500), (ARQ, "arquitectura.png", 1080)]:
            pg3 = b.new_page(viewport={"width": w, "height": 600}, device_scale_factor=2)
            pg3.set_content(html)
            pg3.wait_for_timeout(200)
            pg3.locator("#diagram").screenshot(path=os.path.join(DIA, out))
            pg3.close()
        b.close()
    print("assets ->", DOCS, "y", WEB)


if __name__ == "__main__":
    main()
