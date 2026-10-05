# Playbook de Notion — hackIAthon Panamá 2026 (equipo SWEETCODE)

El uso de **Notion es obligatorio** y la rúbrica lo evalúa: *"Notion: ejecución y
pitch — Trabajo trazable durante el evento, **catálogo** y **pruebas** completos;
**pitch navegable**"* (**15 pts**, el 3.º más pesado).

El error común: llenar Notion al final. La rúbrica premia **trazabilidad durante
el evento**. Por eso: se actualiza **el mismo día**, no en la víspera.

---

## Estructura del workspace

Crea una página raíz **"SWEETCODE — hackIAthon"** con estas subpáginas:

```
SWEETCODE — hackIAthon
├── 🏁 Pitch (página navegable)         ← lo que ve el jurado
├── ✅ Rúbrica viva (tabla)             ← dónde estamos vs. el máximo
├── 📚 Catálogo de fuentes (tabla)      ← "catálogo ... completo"
├── 🧪 Pruebas y métricas (tabla)       ← "pruebas completas", "métricas verificables"
├── 📝 Bitácora de ejecución (tabla)    ← "trabajo trazable durante el evento"
├── 🧭 Registro de decisiones (tabla)   ← arquitectura proporcional y reproducible
└── 📦 Priorización (tabla)             ← salida del prototipo (lo demostrable)
```

> Importación rápida: en Notion, `Import → CSV` y sube cada archivo de
> `notion/csv/`. Notion crea la base de datos con sus columnas ya definidas.

---

## Bases de datos: columnas y para qué sirven

### 📚 Catálogo de fuentes (`01-catalogo-fuentes.csv`)
Fuentes que consume el prototipo, con confiabilidad y derechos documentados.

| Propiedad | Tipo | Uso |
|---|---|---|
| Nombre | Título | — |
| Tipo | Select (RSS, Portal, Oficial, API) | origen |
| URL | URL | enlace |
| Sección | Select (Nacional, Economía, Salud, Seguridad, …) | cobertura |
| Frecuencia | Select (min, hora, día) | frescura |
| Confiabilidad | Número (1–5) | entra al score |
| Derechos | Texto | licencia / permiso (ética) |
| Estado | Select (Activa, Pausada) | operación |
| Notas | Texto | — |

### 🧪 Pruebas y métricas (`04-pruebas-metricas.csv`)
**Clave para 15 pts de IA + 10 de calidad.** Cada prueba con baseline y limitación.

| Propiedad | Tipo | Uso |
|---|---|---|
| Fecha | Fecha | — |
| Qué se probó | Título | — |
| Método | Texto | cómo se midió |
| Baseline | Texto | resultado del enfoque simple (keyword/BM25) |
| Resultado | Texto | resultado del modelo |
| Mejora | Texto | delta o "sin mejora" |
| Limitación detectada | Texto | **la rúbrica premia reconocerla** |
| Evidencia | URL | notebook, log, captura |

### 📝 Bitácora de ejecución (`02-bitacora.csv`)
Una fila por día/persona. Prueba que trabajaron **durante** el evento.

`Fecha · Persona · Área · Qué se hizo · Evidencia · Bloqueos · Próximo paso`

### 🧭 Registro de decisiones (`03-decisiones.csv`)
ADR ligero: por qué se eligió X y no Y.

`Fecha · Decisión · Alternativas · Por qué · Impacto · Estado`

### 📦 Priorización (`05-priorizacion-demo.csv`)
La salida del prototipo (lo que verá el jurado en el pitch).

`Fecha · Titular · Fuente · Enlace · Tema · Score · Confianza · Citas · Contradicción · Estado · Decisión humana`

### ✅ Rúbrica viva (crear manualmente, ver abajo)
`Dimensión · Peso · Nota (0–5) · Evidencia (URL) · Acción para subir`

---

## Pitch (página navegable)

Ordena la página así, con **enlaces vivos** al prototipo y a las tablas:

1. **Problema** (2–3 líneas) y **usuario** concreto (TVN o banca).
2. **Demo en vivo** — flujo de 6 pasos: Cargar → Consultar → Priorizar → Ficha → Borrador → Revisar.
3. **IA: baseline vs. mejora** — enlace a 🧪 Pruebas y métricas.
4. **Evidencia y explicabilidad** — cita, score reproducible, contradicciones, abstención.
5. **Impacto** — con números reales del demo (sin exagerar).
6. **Seguridad y ética** — no auto-publicar, derechos de fuentes, anti-abuso.
7. **Roadmap** — qué sigue.
8. **Equipo**.

---

## Rúbrica viva (créala así)

| Dimensión | Peso | Nota (0–5) | Evidencia |
|---|---|---|---|
| Utilidad para TVN o banca | 20 | | |
| Prototipo y flujo completo | 20 | | |
| Uso efectivo de IA | 15 | | |
| Evidencias y explicabilidad | 15 | | |
| Notion: ejecución y pitch | 15 | | |
| Calidad técnica y evaluación | 10 | | |
| Seguridad, privacidad y ética | 5 | | |

Actualiza la **nota** y la **evidencia** al cerrar cada día. Si una dimensión
baja, mira su "Acción para subir".

---

## Mapeo rúbrica → Notion (dónde se demuestra cada punto)

| Dimensión (peso) | Se demuestra en |
|---|---|
| Utilidad (20) | Pitch §1 y §5 (usuario + impacto) |
| Prototipo (20) | Pitch §2 (demo) + 📦 Priorización |
| IA (15) | 🧪 Pruebas y métricas (baseline vs mejora) |
| Evidencias (15) | 📦 Priorización (citas, score, abstención) |
| Notion (15) | Toda la estructura + bitácora diaria + pitch |
| Calidad (10) | 🧭 Decisiones + 🧪 Pruebas + repo reproducible |
| Ética (5) | 📚 Catálogo (derechos) + Pitch §6 |

---

## Orden de montaje (≈20 min)

1. Crear página raíz y las 7 subpáginas (`Import → CSV` para las 5 bases).
2. Crear la tabla **Rúbrica viva** (manual, tabla de arriba).
3. Pegar el outline del pitch (`notion/pitch.md`).
4. Primera fila en **Bitácora** hoy mismo (aunque sea "montaje del workspace").
5. Añadir 8–10 fuentes reales al **Catálogo**.

## Regla de oro

> Si no está en Notion, no ocurrió. Cada decisión, prueba y avance del día se
> registra **antes de dormir**.
