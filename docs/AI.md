# IA — OpenRouter

Usamos **OpenRouter** como **único gateway de IA** para el proyecto: permite
cambiar de modelo sin tocar el código y trabajar con modelos `:free`.

## Decisiones

- **Un solo proveedor:** OpenRouter (`https://openrouter.ai/api/v1`).
- **Modelo por defecto:** `qwen/qwen3.8-27b:free` (configurable con `OPENROUTER_MODEL`).
- **Costo:** la key actual es **free tier** (límite 100 · **50 requests/día** a
  modelos `:free`). Elegir modelos `:free` salvo que se justifique otro.
- **Principio:** la IA **redacta y resume**; **no decide**. El puntaje de
  prioridad y la verificación son **deterministas**. Siempre hay *fallback* local
  si no hay key o falla la red.

## Verificación: prioridad ≠ verificación

Repetir un titular en más medios **no** verifica la noticia (eso es **eco**). Por
eso separamos dos cosas:

- **Prioridad** (determinista): `0.55·relevancia (BM25) + 0.30·frescura + 0.15·confiabilidad`.
  Mide **importancia** para la mesa.
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

> La IA entra (bajo demanda) para **extraer claims**, **trazar origen** y
> **verificar entailment** contra datos oficiales; no como "juez de verdad".

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | Key de OpenRouter (**secreto**). |
| `OPENROUTER_MODEL` | Modelo a usar (por defecto `qwen/qwen3.8-27b:free`). |

## Dónde vive la key

- **Producción (Dokku):** en la config de la app, nunca en el repo.
  ```bash
  dokku config:set panorama OPENROUTER_API_KEY=... OPENROUTER_MODEL=...
  ```
- **Local:** en `.env` (ignorado por git). Plantilla en `.env.example`.
- **CI:** en *GitHub Actions secrets* si llega a hacer falta.

> ⚠️ Nunca commitear la key. Si se filtra, **rotarla** en OpenRouter.

## Uso (cuando exista el código)

```python
import os, httpx
r = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
    json={"model": os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free"),
          "messages": [{"role": "user", "content": "..."}]},
)
```

> En la interfaz, la IA es **invisible**: se muestra "resumen asistido" o
> "sugerencia", nunca "modelo" ni "API conectada".

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
