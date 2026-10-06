"""Renderiza el logo circular -> docs/logo.png (para el README)."""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "logo.png")

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}
.logo{width:240px;height:240px;display:block}
</style></head><body>
<svg class="logo" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <circle cx="60" cy="60" r="40" fill="none" stroke="#005588" stroke-width="10"/>
  <g stroke="#005588" stroke-width="10" stroke-linecap="round">
    <path d="M60 6 v16"/><path d="M60 98 v16"/><path d="M6 60 h16"/><path d="M98 60 h16"/>
  </g>
</svg>
</body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 240, "height": 240}, device_scale_factor=2)
    pg.set_content(HTML)
    pg.wait_for_timeout(200)
    pg.screenshot(path=OUT, omit_background=True)
    b.close()
print("logo ->", OUT)
