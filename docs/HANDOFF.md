# Handoff — Panorama (para el equipo)

Resumen completo del estado del proyecto para que cualquiera pueda retomar y avanzar.

## Qué es
**Panorama** — copiloto editorial para **TVN Media** (hackIAthon Panamá 2026):
convierte **noticias públicas + datos oficiales** en **temas priorizados**, **fichas
de evidencia** y **borradores**, para **decisión humana**. **Nunca publica.**

- Repo: https://github.com/danielvaldess/panorama (privado; colaboradores: Daniel, José)
- Demo: https://panorama.sweetcode.studio
- Notion (fuente de verdad del proceso): espacio del equipo
- Documentos clave: `README.md`, `docs/ARQUITECTURA.md`, `docs/CUMPLIMIENTO-RETO.md`,
  `docs/MENTORIAS.md`, `docs/PROMPTS.md`, `docs/AI.md`, `docs/SERVER.md`, `.cursor/rules/panorama.mdc`

## Estado actual (todo en `main`, desplegado)
| Fase | Estado |
|---|---|
| F1 Notion · F2 Patrimonio · F3 Datos · F4 Motor · F5 Producto · F6 Pruebas · F7 Pitch | ✅ |
| Cierre de brechas (IA semántica, contexto oficial, contrato, métricas) | ✅ |

- **Motor:** `P = 30R+25I+20U+15N+10E` (0–100), reglas `p-1.0`, estado de evidencia independiente.
- **IA:** embeddings **locales** (fastembed) para recuperación semántica + baseline BM25; LLM inactivo (costo 0).
- **Datos:** snapshot congelado (260 noticias · 540 indicadores · 82 sismos) + `manifest.json`.
- **Métricas:** T01–T10 **10/10** · citas **100%** · abstención **100%** · adversarial **100%** · latencia **~15 ms**.

## Cómo correr (local)
```bash
pip install -r requirements.txt
python -m pipeline.ingest          # regenera el snapshot (necesita internet)
python -m pipeline.export          # regenera fichas.jsonl + fuentes.json
uvicorn pipeline.server:app --reload --port 8000   # http://localhost:8000
python -m eval.acceptance          # T01–T10
python -m eval.benchmark           # 40 dev / 20 jurado
python -m eval.quality             # agrupación, macro-F1, P@5
```

## Estructura
```
pipeline/  ingest · snapshot · sources · process · score · draft · context · embed · guard · validate · export · server
eval/      acceptance (T01–T10) · benchmark (60) · quality · metrics
data/      raw/ (noticias, indicadores, eventos) · processed/fichas.jsonl · manifest.json · fuentes.json · benchmark.jsonl · diccionario.md
web/       interfaz (SPA) · favicon · como-funciona.png
docs/      arquitectura · cumplimiento · mentorías · prompts · IA · servidor · capturas · diagramas
.cursor/rules/panorama.mdc   reglas del proyecto (versionadas)
```

## Convenciones (importante)
- Ramas: `feat/*`, `fix/*`, `docs/*` → **PR a `main`**. Conventional Commits.
- Reglas del proyecto: `.cursor/rules/panorama.mdc`. Prompts: `docs/PROMPTS.md`.
- **Sin secretos** en el repo (`.env` ignorado; en producción viven en Dokku config).
- **No describir el reto** en textos públicos.
- Notion: registrar avances el mismo día.

## Qué FALTA (tareas para avanzar en rama)

> Prioridad sugerida. Cada una es un buen PR.

### 1. `feat/sustento-eval` — Validez de sustento ≥90% (rúbrica)
- **Qué:** revisar humanamente **≥30 afirmaciones** y medir el % con respaldo válido (meta ≥90%).
- **Dónde:** nuevo `eval/sustento.py` + muestra etiquetada; salida en `eval/quality.json` y base “Pruebas y métricas” de Notion.
- **Acepta:** script reproducible + resultado con numerador/denominador y fallos.

### 2. `feat/date-range-filter` — Rango de fechas del contrato (§7)
- **Qué:** filtrar `noticias.csv` al intervalo **`[2024-01-01, 2025-10-01)`** (hoy no se aplica).
- **Dónde:** `pipeline/ingest.py` (`collect_news`) + documentar en `data/diccionario.md`.
- **Acepta:** noticias fuera del rango excluidas y registradas en el manifest.

### 3. `feat/sbp-optional` — Extensión bancaria SBP (opcional)
- **Qué:** 12 informes mensuales 2024 de la SBP → `data/raw/sbp.csv` (período/unidad/página).
- **Dónde:** nuevo fetcher en `pipeline/ingest.py` + catálogo.
- **Acepta:** archivo + licencia/condiciones documentadas.

### 4. `feat/embeddings-grouping` — Agrupación semántica calibrada
- **Qué:** usar embeddings para **agrupar eventos** (distinta redacción) con umbral calibrado vs baseline.
- **Dónde:** `pipeline/embed.py` (`cluster`) + integrar en `server._build_fast` con *fallback*.
- **Acepta:** mejora medida en `eval/quality.py` (P/R de agrupación).

### 5. `feat/classification-labels` — Mejorar clasificación ML
- **Qué:** ampliar etiquetas humanas para que el modelo ML **supere** al baseline por palabras clave (hoy 0.80 vs 0.36).
- **Dónde:** `eval/quality.py` (`LABELED`) + posible clasificador en `pipeline/`.
- **Acepta:** macro-F1 reportado y comparación honesta.

### 6. `docs/notion-official` — Migrar al Notion oficial
- **Qué:** replicar la estructura (8 secciones + bases) en el workspace de la organización y compartir con el jurado.
- **Acepta:** URL accesible + artefactos migrados.

## Entornos / infra (resumen)
- **Deploy:** Dokku en CT112 (app `panorama`), dominio `panorama.sweetcode.studio` vía Cloudflare Tunnel; **auto-deploy** cada 3 min desde `main` (CT112 `/root/auto-deploy.sh`).
- **Imagen:** `Dockerfile` (python:3.12-slim; pre-descarga el modelo de embeddings para la demo offline).
- Detalles en `docs/SERVER.md`. **No** hay secretos en el repo.

## Preguntas frecuentes (jurado)
- “¿De dónde viene esta cifra y de qué año?” → **Contexto oficial** en la ficha (período/unidad).
- “5 medios replican la misma agencia, ¿cuántas fuentes?” → **una** (detección de repetición).
- “¿Sin evidencia o fuente maliciosa?” → **abstención** + **anti-inyección**.
