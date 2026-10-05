# Stack recomendado (2026) — mainstream, mantenido y verificado

Criterio: usar **frameworks estándar y mantenidos**, no código a medida.
Se marca qué **adoptamos ya** y qué queda **preparado para el reto**.

## Capas

| Capa | Recomendado (2026) | Por qué | Estado |
|------|--------------------|---------|--------|
| **API/serving** | **FastAPI + Uvicorn** | Estándar de facto en Python | ✅ en uso |
| **Ingesta RSS** | **feedparser** | El parser RSS/Atom de referencia | ✅ adoptar |
| **HTTP** | **httpx** | Cliente moderno (sync/async) | ✅ en uso |
| **Dedupe** | **rapidfuzz** (o `datasketch` MinHash a escala) | Rápido y robusto | ✅ adoptar |
| **Retrieval baseline** | **rank_bm25** | BM25 canónico (baseline reproducible) | ✅ adoptar |
| **Embeddings** | **fastembed** (ONNX, ligero) o `sentence-transformers` con **BGE-M3** (multilingüe) | Búsqueda semántica | ⏳ luego |
| **Vector store** | **pgvector** (si ya hay Postgres) o **Qdrant** | pgvector: cero servicio extra; Qdrant: filtrar/urgente | ⏳ luego |
| **Reranking** | **BGE reranker** (cross-encoder) o Cohere Rerank | Mejora medible tras recuperar | ⏳ luego |
| **Orquestación RAG** | **Haystack 2.x** (pipelines explícitos, serializables, evaluación nativa) | Producción, depurable, agnóstico de modelo | ⏳ luego |
| **Gateway LLM** | **OpenRouter** | Un solo endpoint, modelos `:free` | ✅ en uso |
| **Evaluación** | **RAGAS** (+ **HHEM-2.1-Open** de Vectara) | Faithfulness/alucinación, series reproducible | ⏳ luego |
| **Frontend** | **Next.js + Tailwind + shadcn/ui** (o HTML/CSS ligero) | Estándar para apps React | ⏳ luego |
| **Deploy** | **Docker + Dokku + Cloudflare Tunnel** | Ya montado | ✅ en uso |

## Alternativas y cuándo cambiar

- **Haystack vs LlamaIndex vs LangChain**:
  - **Haystack** → pipelines explícitos, **producción**, evaluación y YAML (nuestra elección).
  - **LlamaIndex** → mejor si el núcleo es *consulta sobre documentos* (muchos conectores).
  - **LangChain/LangGraph** → cuando RAG es *una herramienta* de un agente mayor.
- **pgvector vs Qdrant**: pgvector para <10 M chunks y si ya hay Postgres; Qdrant si se
  necesita filtrar/priorizar latencia.
- **DIY con disciplina** es válido para apps pequeñas; aquí usamos frameworks porque se
  **evalúa** calidad, evidencias y métricas.

## Buenas prácticas (de la investigación)

1. **Hybrid search** (BM25 + vectores) supera a vector puro con identificadores/fechas.
2. **Reranking** tras recuperar (los LLM sufren con contexto largo).
3. **Grounding obligatorio**: cada afirmación con cita; sin cita → **abstenerse**.
4. **Evaluar con RAGAS**: *faithfulness* y relevancia; umbral (~0.8) para alertar.
5. **Salidas estructuradas** (JSON) y `temperature=0` para datos.
6. **Gateway único** (OpenRouter) para no atarse a un proveedor.

## Referencias
- Haystack 2.31 (`haystack-ai`) · LlamaIndex 0.14 (`llama-index`)
- RAGAS (`ragas`) · Vectara HHEM-2.1-Open · `fastembed` / `sentence-transformers` (BGE-M3)
- `rank_bm25` · `rapidfuzz` · `datasketch` · `feedparser`
- pgvector · Qdrant
