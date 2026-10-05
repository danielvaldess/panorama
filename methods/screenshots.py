"""Capturas de pantalla con Playwright + el Edge instalado (sin descargar navegadores).

Uso:
    python methods/screenshots.py
    pip install playwright

Ajusta BASE y la lista SHOTS a tu proyecto.
"""
import os

from playwright.sync_api import sync_playwright

BASE = "https://example.com"
OUT = "docs/screenshots"
os.makedirs(OUT, exist_ok=True)

# (archivo, ruta, full_page, acciones opcionales)
SHOTS = [
    ("01-home", "/", True, None),
    ("02-mobile", "/", True, "mobile"),
]


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for name, path, full, mode in SHOTS:
            vp = {"width": 390, "height": 844} if mode == "mobile" else {"width": 1440, "height": 1000}
            dsf = 2 if mode == "mobile" else 1
            page = browser.new_context(viewport=vp, device_scale_factor=dsf).new_page()
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(2500)
            # Ejemplo de interacción (descomenta y adapta):
            # page.fill("#input", "valor"); page.click("#boton"); page.wait_for_timeout(1200)
            page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
            print(name, "ok")
        browser.close()


if __name__ == "__main__":
    run()
