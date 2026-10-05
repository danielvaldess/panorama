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

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | Key de OpenRouter (**secreto**). |
| `OPENROUTER_MODEL` | Modelo a usar (por defecto `qwen/qwen3.8-27b:free`). |

## Dónde vive la key

- **Producción (Dokku):** en la config de la app, nunca en el repo.
  ```bash
  dokku config:set hackathon-sandbox OPENROUTER_API_KEY=... OPENROUTER_MODEL=...
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
