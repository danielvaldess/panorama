# Métodos — cómo se construyó todo (reutilizable)

Registro del **know-how** usado para generar documentación, capturas, diagramas,
PDFs, la configuración de Notion y el despliegue. Todo reproducible.

## Toolchain

| Herramienta | Para qué |
|---|---|
| **opencode** | Asistente que ejecuta y redacta |
| **Playwright + Edge (`channel="msedge"`)** | Capturas interactivas y render de diagramas |
| **Edge headless** | Capturas rápidas sin instalar nada |
| **Pillow (PIL)** | Logo/favicon y fotos circulares |
| **fpdf2** | PDF profesional (Arial TTF) |
| **GitHub CLI (`gh`)** | Repos, deploy keys, colaboradores |
| **Dokku + Cloudflare Tunnel** | Despliegue `git push → deploy` con HTTPS |
| **Notion API** | Crear/llenar el workspace automáticamente |

Instalación: `pip install playwright pillow fpdf2 imageio-ffmpeg` ·
`winget install Cloudflare.cloudflared` · `gh auth login`.

---

## 1. Capturas (screenshots)

**Rápida, sin dependencias** (solo Edge instalado):
```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --headless=new --disable-gpu --hide-scrollbars `
  --window-size=1440,1000 --virtual-time-budget=9000 `
  --screenshot="docs\screenshots\01-home.png" "https://example.com/"
```

**Interactiva (inevitable para formularios/hover):** Playwright usando el Edge
instalado (sin descargar navegadores):
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(viewport={"width":1440,"height":1000}).new_page()
    pg.goto("https://example.com/", wait_until="networkidle")
    pg.fill("#url", "https://sweetcode.studio"); pg.click("#apply")
    pg.wait_for_timeout(1200)
    pg.screenshot(path="docs/screenshots/01.png", full_page=True)
    b.close()
```
> Para **detectar desborde** horizontal en móvil:
> `document.documentElement.scrollWidth > window.innerWidth` (y listar elementos con `getBoundingClientRect().right > innerWidth`).

## 2. Diagramas (HTML → PNG)

Se diseña el diagrama en **HTML/CSS** (o SVG) con la paleta del producto y se
captura el elemento con Playwright (`channel="msedge"`, `device_scale_factor=2`):
```python
pg.goto("file:///" + path.replace("\\","/"))
pg.locator("#diagram").screenshot(path="docs/diagrams/architecture.png")
```

## 3. Logo / favicon y fotos circulares (Pillow)

```python
from PIL import Image, ImageDraw
img = Image.new("RGBA", (256,256), (0,0,0,0))
ImageDraw.Draw(img).rounded_rectangle([0,0,255,255], radius=56, fill=(11,16,32,255))
img.save("favicon.png"); img.save("favicon.ico", sizes=[(16,16),(32,32),(48,48),(64,64)])

def circle(src, dst, size=320):          # foto circular para README/PDF
    im = Image.open(src).convert("RGB"); w,h = im.size; s = min(w,h)
    im = im.crop(((w-s)//2,(h-s)//2,(w+s)//2,(h+s)//2)).resize((size,size), Image.LANCZOS)
    m = Image.new("L",(size,size),0); ImageDraw.Draw(m).ellipse((0,0,size-1,size-1), fill=255)
    out = Image.new("RGBA",(size,size),(0,0,0,0)); out.paste(im,(0,0),m); out.save(dst)
```

## 4. GIF desde un video (ffmpeg vía imageio)

```python
import imageio_ffmpeg, subprocess
ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, "-ss","22","-t","12","-i","demo.mp4","-vf",
  "fps=10,scale=820:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse",
  "-loop","0","demo.gif"])
```
> GitHub **no** renderiza `<video>` en README: usar **GIF** (autoplay) + enlace al video.

## 5. PDF profesional (fpdf2)

- Fuente **Arial TTF** (`C:/Windows/Fonts/arial.ttf`) → mejor acabado y Unicode.
- Cabecera con banda de color + logo; `section()` con línea; `table()` con
  filas alternas; `image()` para capturas/diagramas; pie con número de página.
- Script base: `methods/make_pdf.py`.

## 6. READMEs profesionales

Usar la skill **`professional-readme`** (`~/.agents/skills/professional-readme/`):
logo centrado, badges shields.io, capturas con pies explicativos, diagramas,
tabla de stack y sección de autores con fotos circulares.

## 7. Notion (workspace por API)

- Integración **"New connection"** → token `ntn_...` → `NOTION_TOKEN`.
- MCP de Notion en `~/.config/opencode/opencode.jsonc`
  (`npx -y @notionhq/notion-mcp-server`).
- Crear bases con `POST /v1/databases` (Notion-Version 2022-06-28) y filas con
  `POST /v1/pages`. Script: `methods/notion_setup.py`.

## 8. Despliegue (Dokku + Cloudflare Tunnel)

- **Dokku:** `dokku apps:create`, `dokku domains:set`, deploy con
  `dokku git:sync --build <app> <git-url> <branch>`.
- **Auto-deploy:** cron que compara `git ls-remote` y reconstruye si cambió.
- **Cloudflare Tunnel:** añadir `ingress` en el `config.yml` de cloudflared
  (`hostname → http://<ip>:<puerto>`), `cloudflared tunnel route dns`, y
  `systemctl restart cloudflared` (⚠️ reiniciar corta el SSH si entras por el túnel).
- **Deploy keys:** clave SSH por contenedor → `gh api repos/<o>/<r>/keys` (read-only).

## 9. Entorno del servidor (resumen)

Ver [`SERVER.md`](SERVER.md): CT112 `dokku-hackathon` → app `panorama`
en `panorama.sweetcode.studio`, auto-deploy cada 3 min.

---

## Reproducir de cero

1. `pip install playwright pillow fpdf2 imageio-ffmpeg` (y `gh`, Edge, cloudflared).
2. Capturas → `methods/screenshots.py`.
3. Diagramas → `methods/diagrams.py`.
4. PDF → `methods/make_pdf.py`.
5. README → skill `professional-readme`.
6. Notion → `methods/notion_setup.py`.
7. Deploy → Dokku + tunnel (sección 8).
