# Recursos existentes (investigación) — qué podemos reutilizar

Investigación de APIs públicas, datasets y librerías para el reto (noticias +
datos oficiales → priorizado con evidencia, decisión humana). Marcado: ✅ verificado.

## A. Fuentes de noticias / datos (entrada)

| Recurso | Qué es | Notas |
|---|---|---|
| ✅ **GDELT Project** | Base global de noticias/eventos, **100+ idiomas**, actualiza cada 15 min; API + BigQuery + CSV | **Gratis y abierto.** Ideal para “mundo/última hora” y tono/entidades |
| ✅ **RSSHub** | Genera RSS de **casi cualquier sitio** (5.000+ rutas) | Licencia **AGPL** → usarlo como **servicio**, no copiar código |
| **RSS de medios (Panamá)** | TVN, La Prensa, Telemetro, Panamá América, La Estrella | Ya en el catálogo |
| **Datos Abiertos Panamá** | Portal oficial `datosabiertos.gob.pa` + INEC, Contraloría, ANTAI, Superintendencia de Bancos | Datos oficiales para “evidencia” |
| **Media Cloud** | Análisis de cobertura mediática (open source, API) | Para tendencias/atención |

## B. Verificación y evidencia (el corazón)

| Recurso | Qué es | Notas |
|---|---|---|
| ✅ **Google Fact Check Tools API** | Consulta **claims ya verificados** (Claim Search API) | **Gratis** (API key). Dan contexto/contradicción |
| ✅ **RAGAS** | Framework de **evaluación de RAG**: *faithfulness*, answer/context relevance | **Referencia**, sin ground truth. Apache-2.0 |
| ✅ **Vectara HHEM-2.1-Open** | Clasificador **open** de alucinación (T5): ¿la respuesta se sostiene en el contexto? | Encaja como paso de *faithfulness* de RAGAS |
| **Patrón RARR / CoVe** | “Attribution” y “chain-of-verification”: obligar cita por afirmación | Método, no librería |
| **NLI (DeBERTa-MNLI)** | Detectar **contradicción** entre afirmaciones/fuentes | Local, rápido |
| **Penalty-aware scoring + canaries** (arXiv 2026) | Mide **abstención correcta**: responder suma, equivocarse resta, abstenerse 0 | Refuerza nuestra decisión de **abstención** |

## C. Recuperación, dedupe y ranking

| Recurso | Qué es |
|---|---|
| **rank_bm25** | **Baseline** de recuperación (exacto, reproducible) |
| **sentence-transformers / BGE-M3** | Embeddings para búsqueda semántica (multilingüe) |
| **BGE reranker / Cohere Rerank** | Reordenar candidatos (mejora medible vs baseline) |
| **datasketch (MinHash/LSH)** | **Dedupe** de noticias casi idénticas |

## D. Productos parecidos (para inspirarse, no copiar tal cual)

- **marmelab/curator-ai** — puntúa relevancia + resume (el patrón).
- **mshumer/ai-journalist** — buscar → seleccionar → redactar → **editar**.
- **CrewAI news agents** — multi-agente investigador/redactor/editor.
- **Folo / RSSHub** — lector RSS moderno.

## E. Buenas prácticas de IA “profesional” (para subir el nivel)

1. **Grounding obligatorio**: cada afirmación con **cita**; sin cita → abstenerse.
2. **Salidas estructuradas** (JSON con esquema) → menos alucinación y más reproducible.
3. **Reranking** tras recuperar → precisión medible.
4. **NLI** para contradicciones entre fuentes.
5. **Selective prediction / abstención** (umbral) + medirla.
6. **Evaluación continua con RAGAS** (faithfulness, relevancia) → “mejora o limitación medida”.
7. **Guardrails** (allowlist de fuentes, defensa ante inyección de prompts).

---

## TOP picks para adoptar (decide tú)

| # | Recurso | Por qué | Riesgo |
|---|---|---|---|
| 1 | **GDELT** (fuente global) | Gratis, multilingüe, tiempo real → “mundo/última hora” | Curva de API/BigQuery |
| 2 | **RSSHub** (cobertura de fuentes) | RSS de casi cualquier medio | AGPL → usarlo como servicio |
| 3 | **Google Fact Check API** | contexto de verificación gratis | Cobertura variable en Panamá |
| 4 | **RAGAS + HHEM-Open** | mide grounding y alucinación → puntúa “IA efectiva” y “evidencias” | Integración media |
| 5 | **rank_bm25 + BGE + datasketch** | baseline vs mejora + dedupe | Coste de embeddings (usar modelo local) |

> Recomendación: **adoptar 1–5 como base**, con **baseline determinista** (reglas +
> BM25) y el **modelo** encima, midiendo con RAGAS. Todo **gratis** y alineado a la
> rúbrica (IA medida + evidencias + abstención).
