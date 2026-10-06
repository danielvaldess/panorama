# Diccionario de datos — "Panamá · Señales y Evidencias v1"

Snapshot público y congelado para el reto **TVN Media**. Se versiona junto al
prototipo y se referencia en `manifest.json` (con SHA-256).

## A · `data/raw/noticias.csv`
Noticias públicas: **TVN RSS + GDELT DOC 2.0** + prensa oficial (`gob.pa`).

| Campo | Descripción |
|---|---|
| `id_noticia` | ID estable (SHA-1 corto de la URL) |
| `titulo` | Titular |
| `url` | Enlace de la fuente |
| `medio` | Medio/emisor |
| `idioma` | Código de idioma (es) |
| `fecha_publicacion` | ISO 8601 UTC (vacío si no disponible) |
| `fecha_deteccion` | Cuándo lo detectó la fuente (GDELT `seendate`) — **distinta** de publicación |
| `fecha_extraccion` | Cuándo se extrajo al snapshot |
| `tema` | economía · logística · turismo · servicios · eventos_naturales · regulación · general |
| `origen` | `RSS` · `GDELT` · `Oficial` |
| `alcance_texto` | `titular+metadatos` (no se asume lectura del cuerpo) |

> Regla: guardar `fecha_publicacion` **distinta** de `fecha_deteccion`; conservar nulos.

## B · `data/raw/indicadores.csv`
Banco Mundial **Indicators API v2** — 6 países (PAN, CRI, COL, DOM, MEX, GTM) × 6
indicadores × 2010–2024 (cuadrícula de 540 combinaciones).

| Campo | Descripción |
|---|---|
| `pais_iso3` | Código ISO-3 del país |
| `indicador_id` | Código del indicador (p. ej. `NY.GDP.MKTP.KD.ZG`) |
| `anio` | Año de referencia |
| `valor` | Valor (nullable; **no** se rellena con 0) |
| `unidad` | Unidad de medida |
| `fuente_url` | URL de origen |
| `fecha_extraccion` | ISO 8601 UTC |
| `licencia` | `CC BY 4.0` (revisar excepciones) |

## C · `data/raw/eventos.geojson`
USGS — sismos del **2024-01-01 al 2024-12-31**, bbox lat 5–12 / lon −86..−76,
magnitud ≥ 3. `FeatureCollection` estándar (id, mag, time, updated, place,
status, url, y geometría [lon, lat, depth]).

> Solo hechos sísmicos: **nunca** evidencia de inundación o pérdidas económicas.

## D · `data/manifest.json`
Trazabilidad: `version`, `fecha_corte_UTC`, `consultas`, `cantidad_por_archivo`,
`licencia_condiciones`, `sha256` y `transformaciones`.
