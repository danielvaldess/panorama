"""Renderiza un diagrama HTML/CSS a PNG (para README/PDF).

Uso:
    python methods/diagrams.py
    pip install playwright
"""
import os

from playwright.sync_api import sync_playwright

OUT = "docs/diagrams"
os.makedirs(OUT, exist_ok=True)

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#fff;color:#2a2a2a}
  #diagram{width:1500px;padding:40px 44px}
  h1{font-size:26px;margin:0 0 20px;color:#005588}
  .row{display:flex;align-items:center;justify-content:space-between}
  .card{border:1px solid #c7c7c7;border-radius:14px;padding:20px;text-align:center;box-shadow:0 10px 24px rgba(0,0,0,.08)}
  .box{width:250px} .core{width:560px;border-color:#0077c8}
  .arrow{width:100px;text-align:center;color:#005588;font-weight:700;font-size:12px}
</style></head><body>
<div id="diagram">
  <h1>Título del diagrama</h1>
  <div class="row">
    <div class="card box">Entrada</div>
    <div class="arrow">paso →</div>
    <div class="card core">Núcleo</div>
    <div class="arrow">paso →</div>
    <div class="card box">Salida</div>
  </div>
</div></body></html>"""


def run():
    path = os.path.join(OUT, "_diagram.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page.goto("file:///" + os.path.abspath(path).replace("\\", "/"))
        page.wait_for_timeout(600)
        page.locator("#diagram").screenshot(path=f"{OUT}/diagrama.png")
        b.close()
    os.remove(path)
    print("ok ->", f"{OUT}/diagrama.png")


if __name__ == "__main__":
    run()
