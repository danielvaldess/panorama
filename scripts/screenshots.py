"""Capturas reales de la app para el README (UI actual).

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
        pg.goto(BASE, wait_until="domcontentloaded", timeout=90000)

        # Mesa de hoy (vista principal)
        pg.wait_for_selector(".item", timeout=120000)
        pg.wait_for_timeout(700)
        shot(pg, "01-mesa.png")

        # Pestaña "Requieren evidencia"
        pg.click('.tab[data-estado="evidencia"]')
        pg.wait_for_timeout(600)
        shot(pg, "02-requieren-evidencia.png")

        # Ficha del tema (volver a "Todas")
        pg.click('.tab[data-estado="todos"]')
        pg.wait_for_selector(".item", timeout=30000)
        pg.click(".item")
        pg.wait_for_selector(".detail-head", timeout=30000)
        pg.wait_for_timeout(700)
        shot(pg, "03-ficha.png", full=True)
        pg.click("#back")

        # Publicaciones (con etiquetas Señal / Archivo)
        pg.click('a[data-section="bandeja"]')
        pg.wait_for_selector("table", timeout=30000)
        pg.wait_for_timeout(900)
        shot(pg, "04-publicaciones.png")

        # Fuentes
        pg.click('a[data-section="fuentes"]')
        pg.wait_for_timeout(700)
        shot(pg, "05-fuentes.png")

        # Cómo funciona
        pg.click('a[data-section="ayuda"]')
        pg.wait_for_timeout(700)
        shot(pg, "06-como-funciona.png")

        # Perfil de decisiones (menú de usuario)
        pg.click("#userBtn")
        pg.wait_for_timeout(300)
        pg.click('[data-menu="perfil"]')
        pg.wait_for_timeout(1200)
        shot(pg, "07-perfil.png")

        b.close()
    print("LISTO ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
