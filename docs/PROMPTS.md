# Prompts y convenciones reutilizables ("notebooks")

Equivalente a los *notebooks* de Cursor (mentoría de Ricardo) y al **prompt
estructurado** (mentoría de Israel). Se versiona con el repo para que el equipo
trabaje con el mismo contexto. Referéncialo al pedir ayuda a un asistente.

## Estructura de prompt (usar siempre)

1. **Objetivo** — el resultado que se busca.
2. **Contexto** — dónde vive, qué existe ya, qué no tocar.
3. **Restricciones** — estilo, librerías, convenciones, límites.
4. **Validaciones** — cómo se comprueba que quedó bien.

> Evitar el *prompt overengineering*: dividir en pasos y revisar cada resultado
> (prompts **iterativos** > un prompt gigante).

## Plantillas

### Añadir una fuente de noticias
```
Objetivo: agregar <fuente> a pipeline/ingest.py (FEEDS) y reconstruir el snapshot.
Contexto: noticias públicas; dedupe por URL; campos del contrato en data/diccionario.md.
Restricciones: no republicar contenido; conservar nulos; UA ASCII.
Validaciones: python -m pipeline.ingest; verificar conteo y origen en noticias.csv.
```

### Añadir una prueba de aceptación (T11…)
```
Objetivo: añadir una prueba a eval/acceptance.py siguiendo el patrón existente.
Contexto: pruebas T01–T10; devuelven (pass, observado).
Restricciones: determinista, sin red.
Validaciones: python -m eval.acceptance  → 11/11.
```

### Contextualizar un tema con dato oficial
```
Objetivo: enlazar un tema con un indicador (Banco Mundial) o evento (USGS).
Contexto: pipeline/context.py; TEMA_INDICADORES; mostrar período y unidad.
Restricciones: si no hay relación sustentada, NO forzarla.
Validaciones: revisar la ficha en /api/fichas (campo contexto).
```

### Generar un diagrama
```
Objetivo: renderizar un diagrama PNG con la estética de la app.
Contexto: scripts/render_assets.py (Playwright + HTML con colores TVN).
Restricciones: colores #005588/#e00710/#06accb; texto claro, sin jerga.
Validaciones: revisar el PNG y referenciarlo en README/docs.
```

### Revisar seguridad
```
Objetivo: revisar una fuente o función por riesgos (inyección, XSS, secretos).
Contexto: pipeline/guard.py; esc() en web; .env ignorado.
Restricciones: tratar el texto de fuentes como no confiable.
Validaciones: T07 + benchmark adversarial (100%).
```

## Decisiones de arquitectura (registro breve)

- **Front/back separados**: `web/` (interfaz) y `pipeline/` (núcleo/API).
- **Snapshot congelado** para la demo (sin internet); fuentes en vivo solo como *fallback*.
- **Motor determinista** `P = 30R+25I+20U+15N+10E`; IA **asiste**, no decide.
- **Abstención** cuando no hay evidencia; **anti-inyección** siempre.
- **IA sustantiva = embeddings locales** (costo 0) + baseline BM25.

## Convenciones del equipo

- Conventional Commits; ramas `feat/*`, `fix/*`, `docs/*`.
- Notion = fuente de verdad (bitácora y decisiones el mismo día).
- Cada avance: código + prueba + entrada en Notion.
