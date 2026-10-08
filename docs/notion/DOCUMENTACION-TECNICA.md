# Documentación técnica — Panorama

> Pega este documento completo en Notion (Notion importa Markdown con `Ctrl+Shift+V` o arrastrando el archivo). Cubre: arquitectura, stack, modelo de datos, pipeline, motor de priorización, verificación, IA, seguridad, evaluación y despliegue.

---

## 1. Visión general

Panorama es un sistema **por lotes** (sin monitoreo continuo) que convierte un snapshot congelado de fuentes públicas en una mesa de temas priorizados con fichas de evidencia y borradores. El diseño central:

- **Determinismo primero:** la prioridad y la verificación son funciones puras y auditables; la IA solo redacta/ resume, nunca decide.
- **Snapshot congelado:** toda la demo corre sin internet sobre `data/raw/` con `manifest.json` (SHA-256), lo que garantiza reproducibilidad byte a byte.
- **Control humano bloqueante:** el sistema propone; el editor aprueba. No existe ruta de código que publique automáticamente.

```
Fuentes públicas → Ingesta (lote) → Snapshot congelado + manifest
   → Carga/validación → Dedupe/agrupación/eco → Scoring explicable
   → Ficha + borrador con citas → API FastAPI → SPA (HTML/JS)
                                              ↘ Revisión humana (persistida)
```

## 2. Stack

| Capa | Tecnología | Rol |
|---|---|---|
| Lenguaje | Python 3.12+ (probado en 3.14) | Núcleo |
| API | FastAPI + Uvicorn | Servidor REST + sirve la SPA |
| Recuperación | BM25 (`rank_bm25`), RapidFuzz | Baseline y dedupe |
| Semántica | fastembed (embeddings locales, costo 0) | Agrupación y búsqueda híbrida |
| LLM opcional | OpenCode Zen (principal) / OpenRouter (respaldo) | Resúmenes bajo demanda |
| Persistencia operativa | SQLite (WAL) + seeds JSONL versionados | Decisiones y veredictos |
| Datos | CSV / GeoJSON / JSONL (snapshot congelado) | Contrato de datos |
| Interfaz | HTML + CSS + JS puro (SPA, sin frameworks) | Mesa, ficha, revisión |
| Pruebas | Scripts `eval/*` (T01–T10, benchmark, quality, sustento) | Aceptación y métricas |
| Empaquetado | Docker (`python:3.12-slim`) | Build reproducible |
| CI | GitHub Actions (`devsecops.yml`) | Pruebas + SAST/SCA/secretos + build |
| Deploy | Dokku + Cloudflare Tunnel | Producción |

## 3. Arquitectura

### 3.1 Diagrama de flujo

```
┌─ Fuentes ─────────────────────────────┐
│ TVN RSS · GDELT DOC 2.0               │
│ Banco Mundial Indicators · USGS        │
└──────────────┬─────────────────────────┘
               ▼
   pipeline/ingest.py  (lote, ventanas mensuales p/ GDELT)
               ▼
   data/raw/ (noticias.csv · indicadores.csv · eventos.geojson)
   data/manifest.json (versión · corte UTC · consultas · licencias · SHA-256)
               ▼
   pipeline/snapshot.py  ← carga congelada (sin red en demo)
               ▼
   pipeline/validate.py  ← contrato: separa errores, conserva nulos
               ▼
   pipeline/process.py   ← dedupe · agrupación · detección de eco · verificación
               ▼
   pipeline/score.py     ← P = 30R + 25I + 20U + 15N + 10E  + estado de evidencia
               ▼
   pipeline/draft.py     ← brief · guion · copy + citas por afirmación · abstención
   pipeline/guard.py     ← anti-inyección (el texto de la fuente es dato)
               ▼
   pipeline/server.py (FastAPI)  ⇄  web/index.html (SPA)
               ▼
   POST /api/review · /api/claims/verdict  →  SQLite + seeds JSONL
```

### 3.2 Módulos del pipeline

| Módulo | Responsabilidad |
|---|---|
| `ingest.py` | Construye el snapshot; aplica la ventana de fechas; `--filtrar-snapshot` filtra el CSV congelado sin red |
| `snapshot.py` | Carga congelada (demo offline, T10) |
| `snapshot_io.py` | Export/import de snapshot con verificación SHA-256 y round-trip |
| `sources.py` | Fuentes en vivo — fallback documentado |
| `validate.py` | Contrato de datos: IDs, URLs, fechas, nulos |
| `process.py` | Dedupe, clustering de eventos, **detección de eco**, estados de verificación |
| `score.py` | Motor `P = 30R+25I+20U+15N+10E` + `evidence_state` |
| `draft.py` | Paquete editorial con citas por afirmación y abstención |
| `claims.py` | Construcción/normalización de afirmaciones |
| `context.py` | Enlace noticia ↔ indicador BM / evento USGS (período y unidad) |
| `theme.py` | Taxonomía v3 (temas, alcance, sensibilidad) |
| `embed.py` | Embeddings locales (fastembed) para recuperación semántica |
| `guard.py` | Anti-inyección: texto de fuente = dato, nunca instrucción |
| `db.py` | Repositorio SQLite (WAL), schema versionado (`data/schema.sql`) |
| `store.py` | Persistencia JSONL de decisiones y veredictos (seed versionado) |
| `persist.py` | Punto de persistencia operativa |
| `server.py` | API + SPA (FastAPI) |

## 4. Modelo de datos

### 4.1 Snapshot (contrato)

| Archivo | Fuente | Contenido |
|---|---|---|
| `data/raw/noticias.csv` | TVN RSS + GDELT DOC 2.0 | 250 registros (50 TVN) · ventana **2025-10-02 → 2026-09-30** |
| `data/raw/indicadores.csv` | Banco Mundial Indicators v2 | 6 países × 6 indicadores × 2010–2024 (540) |
| `data/raw/eventos.geojson` | USGS | Sismos 2024 (bbox Panamá, mag ≥3) (82) |

Reglas: UTF-8 · IDs estables · ISO 8601 UTC · **nulos conservados** (no se rellenan con 0).

### 4.2 Entidades principales

| Entidad | Campos clave | Relación |
|---|---|---|
| `noticia` | `id_noticia, titulo, url, medio, fecha_publicacion, tema, origen` | Agrupa → ficha |
| `ficha` | `id_caso, puntaje, componentes, estado_evidencia, estado_revision` | Contiene afirmaciones |
| `afirmacion` | `texto, tipo, ids_fuente` | Cita → fuentes |
| `indicador` / `evento` | período, unidad, valor | Contextualiza → ficha |
| `decision` (SQLite) | estado, revisor, timestamp, fingerprint | Registro humano |
| `veredicto` (SQLite) | `id_caso, indice, veredicto, comentario` | Sustento humano |

### 4.3 Derivados versionados

- `data/manifest.json` — versión, fecha de corte UTC, consultas, cantidades, `rango_fechas_noticias`, licencias, **SHA-256**, transformaciones.
- `data/processed/fichas.jsonl` — fichas generadas.
- `data/processed/revisiones.jsonl` — decisiones humanas (seed de migración).
- `data/processed/sustento_labels.jsonl` — veredictos de sustento (43 etiquetas).
- `data/processed/ai_cache.json` — resúmenes IA persistidos (demo offline).

## 5. Motor de priorización (explicable)

```
P = 30·R + 25·I + 20·U + 15·N + 10·E      (0–100)
```

| Componente | Peso | Qué mide |
|---|---|---|
| **R · Relevancia** | 30 | Relación con Panamá y las modalidades |
| **I · Impacto** | 25 | Alcance sectorial justificado con datos |
| **U · Urgencia** | 20 | Tiempo disponible para revisar |
| **N · Novedad** | 15 | Diferencia frente a eventos ya agrupados (**duplicar no suma**) |
| **E · Evidencia** | 10 | Fuentes pertinentes, primarias, con procedencia |

- Rangos: **baja** [0,40) · **media** [40,70) · **alta** [70,100].
- Versión de reglas: `p-1.0` (publicada en el score, reproducible).
- El **estado de evidencia es independiente** del puntaje: un tema puede ser alta prioridad y tener evidencia insuficiente.

## 6. Verificación y evidencia

| Estado | Cuándo | Confianza |
|---|---|---|
| **Confirmado** | Fuente oficial/primaria (`*.gob.pa`, institución) | Alto |
| **Corroborado** | ≥2 orígenes **independientes** (sin cable común) | Medio/Alto |
| **Contradicho** | Una fuente confirma y otra desmiente | Bajo |
| **Sin verificar** | Un solo origen, **eco** o solo agencia → **abstención** | Bajo |

- **Detección de eco:** similitud textual ≥0.70 + agencias (EFE/AP/Reuters/AFP); los medios que copian cuentan como **una** fuente. Salida: *"N medios, M son eco"*.
- **Circulación ≠ confirmación:** la repetición no incrementa la confianza ni el puntaje.

## 7. IA — dónde entra y dónde no

| Nivel | Qué hace | Cómo |
|---|---|---|
| Embeddings locales | Recuperación y agrupación semántica | `fastembed` (costo 0, offline) |
| LLM bajo demanda | Resumen auxiliar y etiquetas (botón "Analizar con IA") | OpenCode Zen → fallback OpenRouter → fallback local |
| **No hace** | Asignar prioridad, verificar, decidir, publicar | Determinista / humano |

- Prompts y modelos documentados en `docs/AI.md` (versión, costo, límites).
- **Anti-alucinación:** si el corpus no respalda → **abstención** (sin cifra inventada).
- **Anti-inyección:** `guard.py` trata el texto de cualquier fuente como dato, no como instrucción (T07).

## 8. Seguridad y ética técnica

| Control | Implementación |
|---|---|
| Sin publicación automática | Estados de revisión con aprobación humana bloqueante |
| Anti-inyección de prompts | `guard.py` + saneamiento antes de llamar LLM (T07 pasa) |
| Secretos fuera del repo | `.env` gitignored; producción en Dokku config; CI con scan de secretos |
| Derechos de fuentes | Catálogo con licencia/condiciones por fuente |
| Datos personales | No corresponde al alcance (documentado en Riesgos y ética) |
| Protección de rutas mutables | `PANORAMA_ADMIN_TOKEN` opcional |
| CI DevSecOps | SAST (Bandit), SCA, secretos, pruebas, build Docker obligatorios en PR |

## 9. Evaluación y métricas

### 9.1 Batería de pruebas

| Prueba | Qué mide | Resultado |
|---|---|---|
| `eval.acceptance` (T01–T10) | Contratos, eco, abstención, anti-inyección, brief, offline | **10/10** |
| `eval.benchmark` (60 casos: 40 dev / 20 jurado) | Cobertura citas, abstención, contradicción, adversarial, latencia | Ver abajo |
| `eval.quality` | Agrupación (F1), clasificación (macro-F1), P@5, sustento | Ver abajo |
| `eval.sustento` | Validez de sustento humano (rúbrica estricta) | **97.67%** |

### 9.2 Métricas actuales (snapshot congelado)

| Métrica | Valor | Meta |
|---|---|---|
| Aceptación T01–T10 | **10/10** | 10/10 |
| Cobertura de citas | **100%** | 100% |
| **Sustento humano de afirmaciones** | **97.67%** (42/43, 40 fichas) | ≥90% sobre ≥30 afirm. / ≥10 fichas |
| Abstención (sin respuesta) | **100%** | ≥80% |
| Contradicción manejada | **100%** | no elegir arbitrariamente |
| Instrucciones maliciosas bloqueadas | **100%** | 100% |
| Latencia mediana / p95 | **16.2 ms / 42.8 ms** | ≤15 s |
| Agrupación (P/R/F1, baseline y semántico) | **1.00 / 1.00 / 1.00** | reportar |
| Clasificación macro-F1 (baseline vs ML) | **0.80 vs 0.36** — el baseline simple gana | comparación honesta |
| Utilidad del ranking P@5 (exploratoria) | **0.40** | reportar |

> **Limitación reconocida y declarada:** con 30 etiquetas humanas de clasificación, el modelo ML (TF-IDF + LogReg) **no supera** al baseline por palabras clave. Se publica el resultado negativo en lugar de ocultarlo; la mejora queda como tarea (`feat/classification-labels`).

### 9.3 Rúbrica de sustento (rúbrica estricta)

- **Válido:** la fuente citada respalda la afirmación tal cual (con proposición factual real) → **cuenta**.
- **Parcial:** la fuente respalda solo parte → no cuenta.
- **Inválido:** no respalda, o la afirmación es vacía/genérica sin hecho verificable → no cuenta.

Requisitos: ≥30 afirmaciones, ≥10 fichas distintas. Etiquetas amarradas al texto exacto de la afirmación (si el claim cambia, la etiqueta se descarta sola). Implementación: `eval/sustento.py`; veredictos en `POST /api/claims/verdict`.

## 10. API principal

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/fichas` | Temas priorizados + fichas |
| `POST` | `/api/refresh` | Recalcular la mesa |
| `POST` | `/api/review` | Registrar decisión del editor (persiste) |
| `POST` | `/api/analyze` | Análisis IA bajo demanda (fallback local sin key) |
| `GET` | `/api/manifest` | Trazabilidad del snapshot (SHA-256) |
| `GET` | `/api/acceptance` | Matriz T01–T10 |
| `GET` | `/api/benchmark` | Métricas del benchmark |
| `GET` | `/api/claims/verdicts` | Veredictos de sustento |
| `POST` | `/api/claims/verdict` | Registrar veredicto (válido/parcial/inválido) |
| `GET` | `/api/admin/profile` | Perfil agregado del Administrador (preferencias) |
| `GET` | `/health` | Estado del servicio |

## 11. Despliegue y operación

```bash
# Local
pip install -r requirements.txt
python -m pipeline.ingest --filtrar-snapshot   # aplica ventana al CSV congelado (sin red)
python -m pipeline.export                      # regenera fichas + fuentes
uvicorn pipeline.server:app --reload --port 8000

# Pruebas
python -m eval.acceptance && python -m eval.benchmark
python -m eval.quality && python -m eval.sustento

# Docker
docker build -t panorama . && docker run -p 80:80 panorama
```

- **Producción:** Dokku (app `panorama`) + Cloudflare Tunnel; **auto-deploy** cada 3 min desde `main`.
- **CI obligatorio en PR:** `Pruebas (T01–T10 + benchmark)` · `Seguridad (SAST/SCA/secretos)` · `Build de imagen (Docker)`.
- **Estructura del repo:**

```
pipeline/   ingesta · snapshot · proceso · prioridad · borrador · guard · API
eval/       acceptance · benchmark · quality · sustento · metrics
data/       raw/ (snapshot) · processed/ · manifest.json · diccionario.md
web/        interfaz (SPA)
docs/       arquitectura · capturas · diagramas · notion (entregables)
tests/      suite Pytest (db, draft, grounding, provenance, security, …)
```

## 12. Decisiones técnicas relevantes (ADR resumidas)

| Decisión | Alternativas descartadas | Por qué |
|---|---|---|
| Scoring determinista (no LLM) | Que el LLM asigne prioridad | Reproducibilidad y explicabilidad |
| Snapshot congelado + SHA-256 | Ingesta siempre viva | Demo offline reproducible y auditable |
| SQLite (WAL) operativo | PostgreSQL/Mongo con servidor | Infraestructura cero; migración documentada en `docs/DB.md` |
| Embeddings locales (fastembed) | LLM para recuperación | Costo 0, funciona sin internet |
| Baseline simple publicado | Solo mostrar el mejor resultado | Honestidad de evaluación (rúbrica) |
| Ventana de fechas corregida 2025-10-02→2026-09-30 | PDF §7 desfasado un año | Corrección de coordinación, documentada |

---

**Enlaces:** [README](../../README.md) · [Arquitectura](../ARQUITECTURA.md) · [IA](../AI.md) · [DB](../DB.md) · [DevSecOps](../DEVSECOPS.md) · [Cumplimiento del reto](../CUMPLIMIENTO-RETO.md)
