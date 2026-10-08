# IA — embeddings locales + OpenCode Zen (respaldo OpenRouter)

Panorama usa IA en dos niveles: **embeddings locales** para recuperación/agrupación semántica y un **LLM bajo demanda** para enriquecer algunos temas. Proveedor **principal: OpenCode Zen** (plan Go, endpoint compatible OpenAI, `OPENCODE_API_KEY`); **respaldo: OpenRouter** (`OPENROUTER_API_KEY`). El flujo principal no depende de un LLM.

## Decisiones

- **Proveedor LLM opcional:** OpenRouter (`https://openrouter.ai/api/v1`).
- **Modelos:** lista configurable con `OPENROUTER_MODELS`; se prueba uno por uno y se cae a plantilla local.
- **Costo:** la key actual es **free tier** (límite 100 · **50 requests/día** a
  modelos `:free`). Elegir modelos `:free` salvo que se justifique otro.
- **Principio:** la IA **redacta y resume**; **no decide**. El puntaje de
  prioridad y la verificación son **deterministas**. Siempre hay *fallback* local
  si no hay key o falla la red.

## Verificación: prioridad ≠ verificación

Repetir un titular en más medios **no** verifica la noticia (eso es **eco**). Por
eso separamos dos cosas:

- **Prioridad** (determinista): `P = 30R + 25I + 20U + 15N + 10E`.
  Mide **atención editorial**, no verdad ni autorización para publicar.
- **Verificación** (determinista): mide **evidencia**, no popularidad.

Estados y regla (en `pipeline/process.py`):

| Estado | Cuándo | Confianza |
|--------|--------|-----------|
| **Confirmado** | Proviene de fuente **oficial/primaria** (`*.gob.pa`, Canal, etc.) | Alto |
| **Corroborado** | ≥2 **orígenes independientes** (sin cable común) | Medio/Alto |
| **Contradicho** | Una fuente confirma y otra desmiente | Bajo |
| **Sin verificar** | Un solo origen, **eco** o solo agencia | Bajo (abstención) |

Detección de **eco**: agrupamos por origen textual (similitud ≥ 0.70) y por
**agencia** (EFE/AP/Reuters/AFP…); los medios que copian cuentan como **una** sola
fuente. El resultado se muestra como *"N medios, M son eco"*.

> La IA entra bajo demanda para generar un resumen auxiliar y etiquetas. Las afirmaciones mostradas en la ficha siguen limitadas al titular/metadatos y sus fuentes.

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | Key de OpenRouter (**secreto**). |
| `OPENROUTER_MODELS` | Modelos a probar, separados por coma. |
| `PANORAMA_ADMIN_TOKEN` | Token opcional para proteger rutas mutables. |

## Dónde vive la key

- **Producción (Dokku):** en la config de la app, nunca en el repo.
  ```bash
  dokku config:set panorama OPENROUTER_API_KEY=... OPENROUTER_MODEL=...
  ```
- **Local:** en `.env` (ignorado por git). Plantilla en `.env.example`.
- **CI:** en *GitHub Actions secrets* si llega a hacer falta.

> ⚠️ Nunca commitear la key. Si se filtra, **rotarla** en OpenRouter.

## Uso directo

```python
import os, httpx
r = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
    json={"model": os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free"),
          "messages": [{"role": "user", "content": "..."}]},
)
```

> En la interfaz, la IA se ejecuta solo con el botón **Analizar con IA**. Si no hay key, se usa fallback local y se informa como tal.

## Agente respaldado por Notion

Demo del patrón `dato → validación determinista → IA → registro`:

```bash
set NOTION_TOKEN=ntn_...        # integración (New connection)
set OPENROUTER_API_KEY=sk-or-...
python agent/notion_agent.py
```

Lee entradas **Pendiente** de una base de Notion, aplica **reglas deterministas**
(prioridad por tema + nº de fuentes, confianza, y **abstención** si no hay
fuentes), redacta un **resumen** con IA y **actualiza el registro** en Notion.

## Modelos `:free` en OpenRouter (selección)

| Modelo | Uso |
|--------|-----|
| `inclusionai/ling-3.0-flash-sante:free` | Resumen fiable en español (**usado por defecto**) |
| `dots-studio/dots-3-note-preview:free` | Alternativa general |
| `nvidia/nemotron-3.5-lightning:free` | Respaldo (expone razonamiento) |

**Aprendizajes:**
- Muchos modelos `:free` son **de razonamiento**: si `max_tokens` es bajo, el
  `content` viene vacío (el razonamiento consume los tokens). Solución: usar
  `max_tokens` alto (~1200) y, si el `content` viene vacío, **pasar al siguiente
  modelo** (no usar el razonamiento en inglés).
- Los `:free` se **rate-limiten** a veces (HTTP 429) → por eso el agente prueba
  una **lista de modelos** y cae en una **plantilla local** si todos fallan.
- Disponibilidad limitada: **50 requests/día** a `:free`. Cachear y dosificar.

## Uso bajo demanda (consumo controlado)

La IA **no** corre en cada refresco. El refresco periódico es **determinista**
(BM25, dedupe, citas). El análisis con IA se dispara **solo a pedido**:

- Endpoint: `POST /api/analyze`
- En la interfaz: botón **"Analizar con IA"**.

Así no se quema la cuota de 50/día. `AI_TOP_N` controla cuántos temas analiza por corrida.

## IA sustantiva en el prototipo (embeddings, local)

- **Capacidad:** **recuperación semántica** con **embeddings** (`fastembed`, modelo
  `paraphrase-multilingual-MiniLM-L12-v2`, ONNX, 384 dim). Corre **100% local** →
  **costo 0** y **funciona sin API**. Módulo: `pipeline/embed.py`.
- **Dónde se usa:** buscador de la mesa (`GET /api/search`), agrupación de `/api/fichas` cuando el modelo está disponible y evaluación de calidad.
- **Baseline:** **BM25** (léxico) — comparado en `eval/benchmark.py` y `eval/quality.py`.
- **LLM (OpenRouter):** **inactivo** en la entrega → **costo 0**. Se mantiene el módulo
  `pipeline/ai.py` como extensión opcional (resumen de borradores), siempre con
  instrucciones separadas del contenido y salida con citas.

### Qué mejora y cuándo NO ayuda (medido)

- **Agrupación:** el semántico reconoce la **misma noticia con otra redacción** que el
  léxico separa. En la muestra etiquetada, baseline y semántico logran F1 alto; el
  semántico aporta en paráfrasis.
- **Clasificación temática:** el **baseline por palabras clave** (macro-F1 0.80) **supera**
  al modelo ML (TF-IDF + regresión logística, 0.36) **con tan pocas etiquetas** (30) →
  limitación documentada: más datos etiquetados serían necesarios para que el ML gane.
- **Ranking (P@5):** exploratorio (sin especialista); BM25 y semántico coinciden.

### Costo y límites

- **Costo de IA = 0** (embeddings locales + LLM inactivo).
- El modelo de embeddings se **pre-descarga en la imagen** (Dockerfile) para la demo offline.
- Límite: los títulos cortos tienen similitudes “comprimidas”; el umbral de abstención
  combina BM25 + cobertura de vocabulario + **similitud semántica**.
