# AGENTS.md — panorama

Contexto para sesiones de opencode en este repo.

## Qué es

Proyecto oficial del **hackIAthon Panamá 2026** (4ta edición), reto **TVN Media**
— *"De la señal a la decisión"*: un copiloto de inteligencia informativa que
convierte **noticias públicas + datos oficiales** en una **bandeja priorizada**,
**fichas de evidencia** y **borradores** para **decisión humana**. **No publica
automáticamente.**

## Estado

- Reto: **confirmado** — modalidad **editorial TVN (100%)**; banca fuera de alcance.
- Stack: **Python / FastAPI + SPA**, desplegado en Dokku (`panorama.sweetcode.studio`).
- Datos: **snapshot congelado** en `data/raw/` (ver `data/diccionario.md`).
  Filtrado a la ventana de coordinación `[2025-10-02, 2026-09-30]`: **250 noticias** (50 TVN + 200 GDELT).
- Revisión humana y eval de sustento **integrados en `main`** (2026-10-07):
  filtro de fechas ✅ · veredictos por afirmación + perfil del Administrador +
  `eval/sustento.py` ✅ · **pendiente: etiquetar ≥30 afirmaciones (5/30 hoy) y
  iterar `pipeline/draft.py::_claims` hasta ≥90%**. Detalle: `docs/HANDOFF.md`.

## Convenciones

- Rama por defecto `main`; trabajo en `feat/*`, `fix/*`, `docs/*`.
- Commits estilo Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Sin secretos en el repo: usar variables de entorno y `.env` (ignorado).

## Datos y reproducibilidad

- Regenerar el snapshot: `python -m pipeline.ingest` (aborta si quedan menos de 50
  noticias en la ventana de coordinación `[2025-10-02, 2026-09-30]`, para no
  sobrescribir el snapshot congelado).
- Aplicar solo el rango de fechas al CSV congelado (sin red):
  `python -m pipeline.ingest --filtrar-snapshot` (documentado en `data/diccionario.md`).
- Correr el prototipo: `uvicorn pipeline.server:app --reload` (usa el snapshot si existe; si no, *fallback* a fuentes en vivo).
- **Almacenamiento operativo (SQLite, WAL)**: `data/panorama.db` (env `PANORAMA_DB`),
  reconstruible desde el snapshot. Esquema en `data/schema.sql`, repositorio en
  `pipeline/db.py`, decisión técnica en `docs/DB.md`. `make load-snapshot` /
  `make export-snapshot` (verifica/regenera SHA-256). El snapshot CSV/JSONL/GeoJSON
  + `manifest.json` sigue siendo el contrato de datos.

## Revisión humana (Administrador) y eval de sustento

- **UI**: en la ficha, cada afirmación tiene botones *Válido / Parcial / Inválido*
  (sección «Afirmaciones y citas») y la vista **«Perfil del Admin»** resume las
  preferencias aprendidas de las decisiones del editor.
- **API**: `POST /api/claims/verdict` · `GET /api/claims/verdicts` ·
  `GET /api/admin/profile` · `POST /api/review` (persistente).
- **Persistencia** (en SQLite, tabla `decisiones` append-only): `pipeline/store.py`
  escribe/lee vía `pipeline/db.py` (antes `data/processed/revisiones.jsonl` +
  `sustento_labels.jsonl`; migración automática en `db.migrate_legacy`).
- **Métrica de sustento** (rúbrica estricta: solo «válido» cuenta; meta ≥90% sobre
  ≥30 afirmaciones de ≥10 fichas): `python -m eval.sustento` (merge en
  `eval/quality.json`) · `python -m eval.sustento --pendientes`.

## Notion

La organización evalúa el **trabajo trazable en Notion**. Regla: registrar avances
**el mismo día** (bitácora, decisiones, pruebas). El playbook está en `docs/notion/`.

## Reglas y prompts (aprendizajes de las mentorías)

- **Reglas del proyecto:** [`.cursor/rules/panorama.mdc`](.cursor/rules/panorama.mdc)
  (stack, convenciones, seguridad, qué no hacer). Versionadas con el repo.
- **Prompts y convenciones reutilizables:** [`docs/PROMPTS.md`](docs/PROMPTS.md)
  (equivalente a los *notebooks* de Cursor + prompt estructurado).
- **Aprendizajes de las mentorías:** [`docs/MENTORIAS.md`](docs/MENTORIAS.md).
- **Cumplimiento del reto:** [`docs/CUMPLIMIENTO-RETO.md`](docs/CUMPLIMIENTO-RETO.md).
