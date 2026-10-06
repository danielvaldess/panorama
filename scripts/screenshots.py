"""Capturas reales de la app desplegada (para el README).

Uso: python scripts/screenshots.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("PANORAMA_URL", "https://panorama.sweetcode.studio/")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")


def main():
    os.makedirs(OUT, exist_ok=True)

    def shot(page, name, full=True):
        page.screenshot(path=os.path.join(OUT, name), full_page=full)
        print("guardado", name)

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        pg.goto(BASE, wait_until="networkidle", timeout=90000)
        pg.wait_for_selector(".item", timeout=90000)
        shot(pg, "01-mesa-prioridades.png")

        pg.click(".item")
        pg.wait_for_selector(".detail-head", timeout=30000)
        pg.wait_for_timeout(400)
        shot(pg, "02-ficha-tema.png")

        for sec, name in [("fuentes", "03-fuentes.png"), ("verificacion", "04-verificacion.png"),
                          ("bandeja", "05-bandeja.png"), ("reportes", "06-reportes.png")]:
            pg.click(f'a[data-section="{sec}"]')
            pg.wait_for_timeout(1500 if sec == "reportes" else 600)
            shot(pg, name)

        b.close()
    print("LISTO ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
