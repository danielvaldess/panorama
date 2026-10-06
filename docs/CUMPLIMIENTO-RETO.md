# Cumplimiento del reto — Panorama (TVN Media)

Mapeo punto por punto del reto **"De la señal a la decisión"** contra el prototipo.
Leyenda: ✅ cubierto · 🟡 parcial · ⬜ pendiente.

## 1. Resumen ejecutivo

| Requisito | Dónde se cumple | Estado |
|---|---|---|
| Prototipo: noticias + datos oficiales → bandeja priorizada, fichas y borradores | `pipeline/` + `web/` (mesa y ficha por tema) | ✅ |
| Cada afirmación factual vinculada a fuente/fecha/alcance | `pipeline/draft.py` (afirmaciones con citas) + ficha | ✅ |
| No publica automáticamente; decisión humana | Estados de revisión (`POST /api/review`) | ✅ |
| Notion obligatorio | Espacio Notion (8 secciones + bitácora + decisiones + pruebas) | 🟡 (workspace oficial pendiente) |

## 2. Problema, beneficiarios y alcance

| Requisito | Dónde | Estado |
|---|---|---|
| Modalidad editorial TVN (principal) | Decisión D1; toda la UI y salidas son editoriales | ✅ |
| Banca como extensión (opcional) | **Fuera de alcance** por decisión D1 | ✅ (no exigido) |
| Objetivo: corpus público → información accionable con evidencia + priorización explicada + revisión en Notion | `pipeline/score.py`, `draft.py`, Notion | ✅ |
| Ingesta de **dos familias**: noticias/metadatos y **datos estructurados oficiales** | `data/raw/noticias.csv` + `indicadores.csv`/`eventos.geojson` | ✅ (ingesta) / 🟡 (aún no se enlazan en la ficha, ver §3) |
| Normalización, búsqueda, clasificación, agrupación de duplicados, faltantes/contradicciones | `process.py` (dedupe/agrupación/eco), `score.py`, `_contradiction` | ✅ |
| **No incluye**: rating, noticias falsas, datos personales, producción audiovisual | Documentado en Notion → Riesgos y ética | ✅ |

## 3. En qué consiste el prototipo (7 etapas)

| Etapa | Dónde | Estado |
|---|---|---|
| 1 · Cargar (validar IDs, URLs, fechas, nulos; reporte de calidad) | `ingest.py`, `validate.py` (T01) | ✅ |
| 2 · Organizar (clasificar temas; agrupar mismo evento) | `ingest._tema` (clasificación), `process.cluster` | ✅ |
| 3 · Contextualizar (relacionar noticia ↔ indicador/evento oficial; período/unidad; no forzar) | Datos cargados (`indicadores.csv`, `eventos.geojson`) | 🟡 **falta enlazar en la ficha** |
| 4 · Priorizar (puntaje con componentes + lista ordenada; relevancia ≠ suficiencia) | `score.py` (P=30R+25I+20U+15N+10E) | ✅ |
| 5 · Explicar (ficha: qué/quién/qué respaldado/qué falta/acción) | Ficha en `web/index.html` + `draft.py` | ✅ |
| 6 · Producir (borrador con citas por afirmación; hechos vs inferencias) | `draft.py` (brief, guion, copy, afirmaciones) | ✅ |
| 7 · Revisar (aceptación/corrección/descarte; Notion) | `POST /api/review` + Notion | ✅ |

| Salida TVN | Dónde | Estado |
|---|---|---|
| Brief ≤250 palabras; título; enfoque; 3 preguntas; fuentes/verificaciones | `draft.build` | ✅ |
| Guion 45–60 s; copy ≤80 palabras; no inventar | `draft.build` | ✅ |
| Disclaimer si solo hay titular/metadatos | `draft.DISCLAIMER` (siempre) | ✅ |

## 4. Casos de uso y priorización explicable

| Caso | Dónde | Estado |
|---|---|---|
| CU-01 TVN "¿Qué 5 temas revisar y por qué?" | Mesa ordenada + componentes visibles | ✅ |
| CU-02 TVN tema económico + serie oficial + brief sin confundir año | Indicadores cargados + brief | 🟡 (falta cita del indicador en la ficha) |
| CU-03 agrupar repetidos vs corroboración independiente | `process._verify` (eco vs independientes) | ✅ |
| CU-04 cifra inexistente/contradicción → abstención | `benchmark.decide` + T05/T06 | ✅ |
| CU-05 banca | Fuera de alcance (D1) | ✅ (no exigido) |
| P=30R+25I+20U+15N+10E (0–100), rangos bajo/medio/alto, empates, versión de reglas | `score.py` (reglas `p-1.0`) | ✅ |
| Estado de evidencia independiente (insuf./parcial/suficiente) | `score.evidence_state` | ✅ |
| No etiqueta verdadero/falso | Documentado; el sistema se abstiene | ✅ |

## 5. Notion (obligatorio)

| Página/Base exigida | En Notion | Estado |
|---|---|---|
| Inicio del reto | ✅ | ✅ |
| Plan y decisiones (≥8 tareas, ≥3 decisiones) | 13 tareas, 5 decisiones | ✅ |
| Catálogo de datos | 6 fuentes | ✅ |
| Diseño de solución | ✅ | ✅ |
| Casos y evidencias (≥5 fichas, 1 sin evidencia) | 6 fichas (PAN-005 abstención) | ✅ |
| Pruebas y métricas (T01–T10) | 10 + benchmark | ✅ |
| Riesgos y ética | ✅ | ✅ |
| Presentación al jurado | Página creada | ⬜ (pitch pendiente) |
| Evidencias mínimas: URL accesible al jurado; plan ≥8 tareas/3 decisiones; catálogo; ≥5 fichas; matriz + métricas; pitch 10 min | En el espacio de Daniel | 🟡 (workspace oficial pendiente) |

## 6. Set de datos públicos

| Componente | Dónde | Estado |
|---|---|---|
| A · Noticias (TVN RSS + GDELT) | `data/raw/noticias.csv` (260; 150 TVN) | ✅ |
| B · Banco Mundial (6 países × 6 ind. × 2010–2024) | `data/raw/indicadores.csv` (540) | ✅ |
| C · USGS sismos 2024 | `data/raw/eventos.geojson` (82) | ✅ |
| D · SBP (opcional) | — | ⬜ (opcional) |

## 7. Contrato de datos y reproducibilidad

| Artefacto | Dónde | Estado |
|---|---|---|
| `noticias.csv` (campos del contrato) | ✅ | ✅ |
| `indicadores.csv` (campos) | ✅ | ✅ |
| `eventos.geojson` | ✅ (USGS estándar) | ✅ |
| `fichas.jsonl` | — | ⬜ **falta exportar** |
| `manifest.json` (versión, corte, consultas, licencias, SHA-256, transformaciones) | ✅ | ✅ |
| `raw/` + `manifest` + diccionario | ✅ | ✅ |
| `processed/` | — | ⬜ **falta** |
| Benchmark 60 (30/10/10/10); 40 dev / 20 reservadas | `data/benchmark.jsonl` (60) | 🟡 **falta marcar dev/jurado** |
| UTF-8, ISO 8601 UTC, nulos conservados | `ingest.py` / `validate.py` | ✅ |

## 8. Arquitectura, IA y controles

| Requisito | Dónde | Estado |
|---|---|---|
| Arquitectura por lotes (sin monitoreo continuo) | `snapshot.py` (carga congelada) | ✅ |
| **IA sustantiva (NLP/ML)** | BM25 (IR) + RapidFuzz (agrupación) + clasificación por tema | 🟡 **falta componente semántica/ML** (embeddings/entidades) |
| Baseline comparado | `eval/benchmark.py` (BM25 vs decisión) | ✅ |
| Documentar modelo/versión/prompts/costo/límites | `docs/AI.md` | ✅ |
| Anti-inyección (dato ≠ instrucción) | `guard.py` + T07 | ✅ |
| Anti-alucinación / abstención | `draft.abstain` + `benchmark.decide` | ✅ |
| Privacidad, derechos, credenciales | Notion → Riesgos y ética | ✅ |
| Control humano (5 estados) | `POST /api/review` | ✅ |

## 9. Pruebas de aceptación y métricas

| Requisito | Dónde | Estado |
|---|---|---|
| T01–T10 | `eval/acceptance.py` (10/10) | ✅ |
| Cobertura de citas 100% | benchmark: 100% | ✅ |
| Abstención ≥80% | benchmark: 80% | ✅ |
| Clasificación/agrupación (macro-F1 / P-R) | — | ⬜ **falta medir con etiquetas humanas** |
| Utilidad del ranking (P@5) | — | ⬜ **falta (exploratoria)** |
| Eficiencia (mediana/p95) | benchmark: ~5 ms | ✅ |

## 10. Entregables y rúbrica

| Entregable | Dónde | Estado |
|---|---|---|
| Prototipo ejecutable con flujo completo | `panorama.sweetcode.studio` | ✅ |
| Repo GitHub con README, instalación, dependencias, `.env.example`, pruebas | GitHub `danielvaldess/panorama` | ✅ |
| Paquete de datos (snapshot, diccionario, manifest, licencias, benchmark) | `data/` | 🟡 (falta `fichas.jsonl`/`processed/`) |
| Espacio Notion + presentación | Notion (propio) | 🟡 |
| Rúbrica (100) — autoevaluación honesta | Notion → Rúbrica viva | ✅ |

## 11. Ejecución y presentación

| Requisito | Dónde | Estado |
|---|---|---|
| Demo en vivo (consulta útil, ficha con citas, borrador, abstención) | `web/` | ✅ |
| Demo sin internet (snapshot) | T10 | ✅ |
| Pitch 10 min desde Notion | — | ⬜ |

---

## Brechas priorizadas

1. **IA sustantiva semántica** (embeddings para agrupar/recuperar) + comparación con baseline. *(rúbrica: Uso efectivo de IA 15)*
2. **Contextualizar**: enlazar noticia ↔ indicador del Banco Mundial / evento USGS en la ficha, con período/unidad. *(etapa 3, CU-02)*
3. **Exportar `fichas.jsonl`** y crear `processed/`. *(contrato de datos)*
4. **Benchmark dev/jurado** (marcar 40/20). *(contrato)*
5. **Métricas de clasificación/agrupación** (macro-F1) y **P@5** (exploratoria). *(rúbrica: Calidad técnica 10)*
6. **Notion oficial** (workspace de la organización) + **pitch** + página Presentación.

---

## Mapa de herramientas

| Herramienta | Rol en Panorama | Dónde |
|---|---|---|
| **Python + FastAPI** | Núcleo y API | `pipeline/server.py` |
| **Docker** | Empaquetado (`python:3.12-slim` + uvicorn, copia `pipeline/eval/web/data`) | `Dockerfile` |
| **Dokku** | Build/deploy de la imagen y vhost | CT112 `dokku-hackathon`, app `panorama` |
| **Cloudflare Tunnel** | Publica el dominio y el SSH | CT101 `cloudflared` (túnel `proxmox-ssh`) |
| **Proxmox (infra)** | Host con LXC (CT101/110/111/112…) | Host `sweetcode` |
| **Auto-deploy** | Cron cada 3 min: `git ls-remote` → `dokku git:sync --build` | CT112 `/root/auto-deploy.sh` |
| **OpenRouter** | IA de lenguaje (resumen/borradores) — **opcional, hoy inactivo** | `pipeline/ai.py` (no usado en la UI) |
| **BM25 (rank_bm25)** | Recuperación/orden (baseline y motor) | `process.bm25`, `eval/benchmark.py` |
| **RapidFuzz** | Similitud/agrupación y detección de eco | `process.py` |
| **TVN RSS · GDELT · Banco Mundial · USGS** | Fuentes públicas | `pipeline/ingest.py` |
| **Notion** | Trazabilidad, decisiones, pruebas, presentación | Espacio Notion |
| **Playwright** | Capturas y diagramas del README | `scripts/` |
| **GitHub** | Repo, deploy key, topics, About | `danielvaldess/panorama` |
