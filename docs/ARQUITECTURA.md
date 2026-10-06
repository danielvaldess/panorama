# Arquitectura — Panorama

Copiloto editorial para **TVN Media**. Snapshot público → pipeline determinista → mesa de prioridades → decisión humana.

## Arquitectura técnica

```mermaid
flowchart TB
  subgraph Fuentes públicas
    TVN[TVN RSS]
    GDELT[GDELT DOC 2.0]
    WB[Banco Mundial]
    USGS[USGS]
  end

  subgraph Ingesta
    ING[pipeline/ingest.py]
    RAW[(data/raw\nnoticias · indicadores · eventos)]
    MAN[data/manifest.json\nSHA-256]
  end

  subgraph Núcleo
    SNAP[snapshot.py\ncarga congelada]
    PROC[process.py\ndedupe · agrupación · eco]
    SCORE[score.py\nP = 30R+25I+20U+15N+10E]
    DRAFT[draft.py\nbrief · guion · copy + citas]
    GUARD[guard.py\nanti-inyección]
    VAL[validate.py\ncontrato]
  end

  subgraph Producto
    API[server.py FastAPI]
    WEB[web/index.html SPA]
    NOTION[(Notion\nbitácora · decisiones · pruebas)]
  end

  TVN & GDELT & WB & USGS --> ING --> RAW --> SNAP
  ING --> MAN
  SNAP --> VAL --> PROC --> SCORE --> DRAFT --> API --> WEB
  PROC --> GUARD
  WEB -. decisión humana .-> API
  API -. registro .-> NOTION
```

## Secuencia — abrir un tema

```mermaid
sequenceDiagram
  participant E as Editor
  participant W as Interfaz (SPA)
  participant A as API
  participant P as Pipeline

  E->>W: clic en un tema
  W->>A: GET /api/fichas
  A->>P: snapshot → dedupe → agrupar → priorizar → borrador
  P-->>A: ficha (P, componentes, evidencia, citas)
  A-->>W: ficha completa
  W-->>E: ficha con brief, guion, copy y fuentes
  E->>W: registrar decisión
  W->>A: POST /api/review {estado}
  A-->>W: ok
```

## Modelo de datos

```mermaid
erDiagram
  NOTICIAS ||--o{ FICHA : "agrupa"
  INDICADORES }o--o{ FICHA : "contextualiza"
  EVENTOS }o--o{ FICHA : "contextualiza"
  FICHA ||--|{ AFIRMACION : "cita"
  NOTICIAS {
    string id_noticia
    string titulo
    string url
    string medio
    string fecha_publicacion
    string fecha_deteccion
    string tema
    string origen
  }
  FICHA {
    string id_caso
    int puntaje
    json componentes
    string estado_evidencia
    string estado_revision
  }
  AFIRMACION {
    string texto
    string tipo
    string ids_fuente
  }
```

## Estados de revisión (control humano)

```mermaid
stateDiagram-v2
  [*] --> nuevo
  nuevo --> en_revision: enviar a revisión
  nuevo --> requiere_evidencia: falta evidencia
  en_revision --> aprobado_borrador: aprobar borrador
  en_revision --> descartado: descartar
  requiere_evidencia --> en_revision: evidencia conseguida
  aprobado_borrador --> [*]
  descartado --> [*]
```

> **Aprobar un borrador no significa publicar.**

## Componentes del pipeline

| Módulo | Responsabilidad |
|---|---|
| `ingest.py` | Construye el snapshot público (noticias, indicadores, eventos) + `manifest` |
| `snapshot.py` | Carga el snapshot congelado (demo reproducible, sin red) |
| `sources.py` | Fuentes en vivo — *fallback* documentado |
| `validate.py` | Contrato de datos: separa errores y conserva nulos |
| `process.py` | Dedupe, agrupación de eventos, **detección de eco**, verificación |
| `score.py` | Motor explicable `P = 30R+25I+20U+15N+10E` + estado de evidencia |
| `draft.py` | Paquete editorial con **citas por afirmación** y abstención |
| `guard.py` | Anti-inyección: el texto de una fuente es **dato, no instrucción** |
| `server.py` | API + interfaz (FastAPI) |

## Reproducibilidad

- **Snapshot congelado** en `data/raw/` con `manifest.json` (versión, corte UTC, consultas, licencias, **SHA-256**).
- Regenerar: `python -m pipeline.ingest`.
- Demo **sin internet** (T10) garantizada por el snapshot local.
- Evaluación reproducible: `python -m eval.acceptance` y `python -m eval.benchmark`.
