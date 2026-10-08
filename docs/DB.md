# Almacenamiento operativo (SQLite)

Panorama separa dos capas de datos:

1. **Snapshot congelado (contrato de datos del reto)** — `data/raw/*.csv`,
   `*.geojson` + `data/manifest.json` (SHA-256). Reproducible, versionado y
   verificable. **No se sustituye por la base.**
2. **Base operativa (SQLite)** — decisiones humanas, caché del LLM, estado de
   temas/clasificaciones, noticias, indicadores, eventos, fichas y borradores.
   Es **reconstruible desde el snapshot** (`make load-snapshot`) cuando no existe.

## Por qué SQLite (decisión técnica)

| Criterio | SQLite | PostgreSQL | MongoDB / otro DBMS |
|---|---|---|---|
| Infraestructura | Archivo local, sin servidor | Requiere servicio + credenciales | Requiere servicio |
| Demo offline (T10) | Funciona sin red | Necesita el servicio vivo | Necesita el servicio vivo |
| Despliegue (Dokku) | Solo montar un volumen para `data/` | Volumen + servicio extra | Volumen + servicio extra |
| Transacciones / integridad | ACID, FK, UNIQUE, triggers | ACID completo | Modelo documento |
| Concurrencia | Suficiente (1 proceso FastAPI + WAL) | Alta | Alta |
| Costo de operación | Cero | Bajo-medio | Bajo-medio |

**Decisión:** SQLite con **WAL** activado. El volumen de datos es pequeño
(≈130 noticias, 540 indicadores, 82 eventos) y el patrón de acceso es
mayormente lectura + escrituras append-only de decisiones. La demo debe poder
correr **sin internet** desde el snapshot; un DBMS con servidor añadiría un
punto de fallo y no aporta nada a esta escala.

**Alternativas descartadas:** PostgreSQL (correcto para producción multi-usuario,
pero innecesario ahora), MongoDB (sin ventaja relacional; ya manejamos JSON
como TEXT en columnas), Redis (no es almacén durable de este tipo).

**Ruta de migración a Postgres** (si el reto escala a producción editorial):
- El esquema ya es **relacional y versionado** (`data/schema.sql`) → las tablas
  se recrean casi 1:1 en Postgres.
- Cambios mínimos: `TEXT → TEXT/VARCHAR`, `REAL → DOUBLE PRECISION`,
  `INTEGER → BIGINT/INT`, triggers `RAISE(ABORT)` → `BEFORE UPDATE/DELETE ... RETURN NULL`.
- `pipeline/db.py` concentra todo el SQL en **consultas parametrizadas** (solo
  hay que cambiar el driver de `sqlite3` a `psycopg` y los placeholders `?`→`%s`).
- `cache_llm` / `decisiones` / `clasificaciones` migran con `COPY` o un dump.

## Esquema (`data/schema.sql`)

| Tabla | Propósito | Clave / restricción |
|---|---|---|
| `fuentes` | catálogo de fuentes (nombre, url, tipo, confiabilidad, licencia) | `UNIQUE(nombre, url)` |
| `noticias` | titulares del snapshot + llegadas del poller | `url UNIQUE` (dedup) |
| `clasificaciones` | tema, confianza, candidatos, método, fuera_de_alcance, sensible | `noticia_url UNIQUE`, FK a `noticias` |
| `grupos_evento` / `grupo_noticias` | agrupación de noticias por evento | FK a `noticias.url` |
| `indicadores` | Banco Mundial | PK `(pais_iso3, indicador_id, anio)`; `valor NULL` |
| `eventos_sismicos` | USGS (features parseadas + `feature_json` canónico) | PK `id` |
| `fichas` | ficha priorizada (puntaje, componentes, evidencia) | PK `id_caso` |
| `borradores` | borrador editorial + metadatos del LLM | `modelo, version, prompt_hash, tokens, costo, latencia` |
| `decisiones` | decisiones del editor | **SOLO INSERT** (triggers anti UPDATE/DELETE); `nombre, nota, fecha` |
| `cache_llm` | caché de salidas del LLM (offline) | PK `clave` |
| `snapshots` | manifest + texto canónico de `eventos.geojson` | histórico |

## Convenciones

- **Fechas**: ISO 8601 UTC (`TEXT`). La conversión a hora de Panamá es **solo de
  la UI** (nunca se guarda en zona local).
- **Nulos conservados**: `valor` de indicadores y fechas vacías quedan `NULL`;
  nunca se rellenan con `0`.
- **Decisiones append-only**: `pipeline/db.py::add_decision` solo hace `INSERT`; el
  esquema impide `UPDATE`/`DELETE` con triggers.
- **Consultas parametrizadas**: todo el SQL usa placeholders `?` (sin concatenar);
  `nombre` y `nota` se validan y truncan a longitud máxima (`NOMBRE_MAX=120`,
  `NOTA_MAX=2000`).

## Comandos

```bash
make load-snapshot      # construye la DB desde data/raw/* y verifica SHA-256
make export-snapshot    # regenera data/raw/* + manifest.json desde la DB
make test               # pytest (SQLite en memoria; no toca la DB real)
```

- `load-snapshot` **aborta** si el SHA-256 de un archivo no coincide con
  `manifest.json`.
- Round-trip `load-snapshot → export-snapshot` reproduce **los mismos SHA-256**
  (los CSV se regeneran fila a fila; `eventos.geojson` se conserva como texto
  canónico para no perder fidelidad del JSON anidado).

## Configuración

- **Path de la DB**: variable de entorno `PANORAMA_DB` (por defecto
  `data/panorama.db`). En tests se usa `:memory:`.
- **Al arrancar**, `pipeline.server` inicializa la DB y, si la tabla `noticias`
  está vacía, la **reconstruye desde el snapshot** (ver `lifespan`).

## Volumen persistente (despliegue)

La DB y el caché del LLM viven en `data/`. En Dokku hay que montar un volumen
persistente para que sobreviva a los redeploys:

```bash
# dentro del host CT112
mkdir -p /var/lib/dokku/data/storage/panorama
dokku storage:mount panorama /var/lib/dokku/data/storage/panorama:/app/data
dokku ps:restart panorama
```

En Docker plano, monta `data/` como volumen y define `PANORAMA_DB=/app/data/panorama.db`.

## Modo offline

La demo funciona sin internet: `load-snapshot` puebla la base desde el snapshot
congelado y `migrate_legacy` importa el caché del LLM previo (`ai_cache.json`)
hacia `cache_llm`, por lo que los resúmenes asistidos ya generados siguen
disponibles sin red (T10).
