# Flujo DevSecOps — Panorama

Cómo trabajamos el repositorio: ramas, pull requests, integración continua con
pruebas y seguridad, y despliegue. Nada llega a `main` sin pasar por el pipeline.

## 1. Ramas

- `main` es la rama de producción (protegida).
- Se trabaja en ramas cortas con prefijo:
  - `feat/*` — nueva funcionalidad
  - `fix/*` — corrección
  - `docs/*` — documentación
  - `chore/*` — mantenimiento / infraestructura

Commits en **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`).

## 2. Ciclo

```
feature branch ──► commit ──► push ──► Pull Request ──► CI (3 checks) ──► merge (squash) ──► main ──► deploy Dokku
```

1. `git checkout -b feat/mi-cambio`
2. Commits atómicos (un tema por commit).
3. `git push -u origin feat/mi-cambio`
4. `gh pr create --base main --head feat/mi-cambio`
5. El pipeline corre automáticamente sobre el PR.
6. Con los 3 checks en verde, se hace **squash merge** y se borra la rama.
7. `main` dispara el **auto-deploy** de Dokku (cron cada 3 min).

## 3. Integración continua (`.github/workflows/devsecops.yml`)

| Job | Qué hace | Bloqueante |
|---|---|---|
| **Pruebas (T01-T10 + benchmark)** | Matriz de aceptación, benchmark y smoke de la API | Sí |
| **Seguridad (SAST / SCA / secretos)** | `bandit` (SAST), `pip-audit` (SCA), `detect-secrets` | Sí (reporta) |
| **Build de imagen (Docker)** | `docker build` de la imagen desplegable | Sí |

El job de **build** depende de que pasen las **pruebas** (`needs: [test]`).

## 4. Protección de `main`

Regla activa (vía API de GitHub):

- Requiere los 3 checks en verde: `Pruebas (T01-T10 + benchmark)`,
  `Seguridad (SAST / SCA / secretos)`, `Build de imagen (Docker)`.
- `strict: true` → la rama debe estar **actualizada** con `main` antes de mergear.

## 5. Seguridad

- **SAST**: `bandit -r pipeline eval` (código).
- **SCA**: `pip-audit -r requirements.txt` (dependencias).
- **Secretos**: `detect-secrets`; los secretos reales viven en `.env` (ignorado) y en
  la config de Dokku, nunca en el repo.
- Rutas mutables (`/api/review`, `/api/refresh`, `/api/analyze`) admiten token
  opcional (`PANORAMA_ADMIN_TOKEN`).

## 6. Despliegue

- `main` → Dokku (`dokku git:sync --build`) → `panorama.sweetcode.studio`.
- La imagen se construye con `Dockerfile` (pre-descarga el modelo de embeddings
  para la demo offline).
