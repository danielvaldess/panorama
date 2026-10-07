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
| Rango §7 de fechas (tarea 2 del backlog) | ✅ en rama `feat/sustento-eval` |
| Infra revisión humana + eval sustento (tarea 1) | ✅ en rama `feat/sustento-eval` |
| Etiquetaje ≥30 afirmaciones → meta ≥90% | 🟡 **5/30 hechas** (continuar en la UI) |

- **Motor:** `P = 30R+25I+20U+15N+10E` (0–100), reglas `p-1.0`, estado de evidencia independiente.
- **IA:** embeddings **locales** (fastembed) para recuperación semántica + baseline BM25; LLM inactivo (costo 0).
- **Datos:** snapshot congelado filtrado a `[2024-01-01, 2025-10-01)` → **82 noticias** (de 260 originales) · 540 indicadores · 82 sismos.
- **Métricas (post-filtro, 2026-10-07):** T01–T10 **10/10** · citas **100%** · abstención **100%** · adversarial **100%** · sustentadas **100%** · latencia **~8 ms**.

## Cómo correr (local)
```bash
pip install -r requirements.txt
python -m pipeline.ingest --filtrar-snapshot   # aplica rango §7 al CSV congelado (sin red)
python -m pipeline.ingest                      # regenera el snapshot (necesita internet)
python -m pipeline.export                      # regenera fichas.jsonl + fuentes.json
uvicorn pipeline.server:app --reload --port 8000   # http://localhost:8000
python -m eval.acceptance          # T01–T10
python -m eval.benchmark           # 40 dev / 20 jurado
python -m eval.quality             # agrupación, macro-F1, P@5 (preserva 'sustento')
python -m eval.sustento            # métrica de sustento (rúbrica estricta)
python -m eval.sustento --pendientes  # qué afirmaciones faltan por veredicto
```

## Estructura
```
pipeline/  ingest · snapshot · sources · process · score · draft · context · embed · guard · validate · export · server · store (persistencia JSONL)
eval/      acceptance (T01–T10) · benchmark (60) · quality · metrics · sustento (≥90%)
data/      raw/ (noticias, indicadores, eventos) · processed/fichas.jsonl · processed/revisiones.jsonl · processed/sustento_labels.jsonl · manifest.json · fuentes.json · benchmark.jsonl · diccionario.md
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

### 1. `feat/sustento-eval` — Validez de sustento ≥90% (rúbrica) 🟡 EN CURSO
- **Hecho (rama `feat/sustento-eval`):**
  - `pipeline/store.py` — persistencia JSONL de decisiones y veredictos
    (`data/processed/revisiones.jsonl`, `sustento_labels.jsonl`; sobrevive reinicios,
    versionable en git).
  - API: `POST /api/claims/verdict` · `GET /api/claims/verdicts` ·
    `GET /api/admin/profile` (preferencias del Administrador, sin re-ranking) ·
    `POST /api/review` ahora persistente.
  - UI: botones *Válido / Parcial / Inválido* por afirmación en la ficha +
    contador de progreso + vista **«Perfil del Admin»**.
  - `eval/sustento.py` — rúbrica estricta (solo «válido» cuenta), meta ≥90%,
    ≥30 afirmaciones de ≥10 fichas, descarta etiquetas de afirmaciones que cambiaron,
    merge en `eval/quality.json` (clave `sustento`; `eval/quality.py` la preserva),
    modo `--pendientes`.
- **Falta:** etiquetar **≥30 afirmaciones** en la UI (**5/30 hoy**, 4 fichas) →
  correr `python -m eval.sustento` → si <90%, pulir `pipeline/draft.py::_claims`
  (hoy emite títulos vacíos tipo *"REPÚBLICA DE PANAMA?"*) → `python -m pipeline.export`
  → re-etiquetar lo nuevo → re-medir. Luego fila CSV en `docs/notion/csv/04-pruebas-metricas.csv`.

### 2. ~~`feat/date-range-filter`~~ ✅ HECHO (en `feat/sustento-eval`)
- Filtro `[2024-01-01, 2025-10-01)` en `pipeline/ingest.py` (`_aplicar_rango`,
  `--filtrar-snapshot`), CSV congelado filtrado (82/260), `manifest.json`
  (`rango_fechas_noticias` + sha256), `data/diccionario.md`, guardia de
  sobrescritura en `pipeline.ingest`. Derivados regenerados (10/10).

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
