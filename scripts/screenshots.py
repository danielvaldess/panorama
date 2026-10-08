"""Capturas reales de la app para el README (UI rediseñada).

Uso:
    uvicorn pipeline.server:app --port 8010
    set PANORAMA_URL=http://localhost:8010/   (o la URL desplegada)
    python scripts/screenshots.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("PANORAMA_URL", "https://panorama.sweetcode.studio/")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")


def main():
    os.makedirs(OUT, exist_ok=True)

    def shot(page, name, full=False):
        page.screenshot(path=os.path.join(OUT, name), full_page=full)
        print("guardado", name)

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        pg.goto(BASE, wait_until="networkidle", timeout=90000)

        # Pantalla de acceso
        pg.wait_for_selector("#gateForm", timeout=60000)
        shot(pg, "00-acceso.png")
        pg.fill("#gName", "Daniel Valdés")
        pg.select_option("#gRole", label="Editor/a")
        pg.click('#gateForm button[type="submit"]')

        # Mesa de hoy
        pg.wait_for_selector(".item", timeout=120000)
        pg.wait_for_timeout(500)
        shot(pg, "01-mesa.png")

        # Ficha del tema
        pg.click(".item")
        pg.wait_for_selector(".detail-head", timeout=30000)
        pg.wait_for_timeout(500)
        shot(pg, "02-ficha.png", full=True)

        # Volver y ver la pestaña "Requieren evidencia"
        pg.click("#back")
        pg.wait_for_selector('.tab[data-estado="evidencia"]', timeout=30000)
        pg.click('.tab[data-estado="evidencia"]')
        pg.wait_for_timeout(600)
        shot(pg, "03-requieren-evidencia.png")

        for sec, name, wait in [("fuentes", "04-fuentes.png", 700),
                                ("bandeja", "05-publicaciones.png", 900),
                                ("reportes", "06-calidad.png", 2200),
                                ("ayuda", "07-como-funciona.png", 700)]:
            pg.click(f'a[data-section="{sec}"]')
            pg.wait_for_timeout(wait)
            shot(pg, name)

        b.close()
    print("LISTO ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
