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

## Convenciones

- Rama por defecto `main`; trabajo en `feat/*`, `fix/*`, `docs/*`.
- Commits estilo Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Sin secretos en el repo: usar variables de entorno y `.env` (ignorado).

## Datos y reproducibilidad

- Regenerar el snapshot: `python -m pipeline.ingest`
- Correr el prototipo: `uvicorn pipeline.server:app --reload` (usa el snapshot si existe; si no, *fallback* a fuentes en vivo).

## Notion

La organización evalúa el **trabajo trazable en Notion**. Regla: registrar avances
**el mismo día** (bitácora, decisiones, pruebas). El playbook está en `docs/notion/`.
