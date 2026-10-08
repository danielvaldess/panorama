# 🚀 Pitch Day — Panorama · SWEETCODE (hackIAthon Panamá 2026)

> **Página navegable para el jurado.** Recorrido de 10 minutos. Cada sección tiene el enlace vivo para verificarlo.
> Demo: **https://panorama.sweetcode.studio** · Repo: **https://github.com/danielvaldess/panorama**

---

## ⏱️ Guion de 10 minutos

| Min | Sección | Qué se dice |
|---|---|---|
| 0:00 | [#1 Problema](#1-problema) | La señal existe; la decisión no |
| 1:30 | [#2 Usuario](#2-usuario) | La redacción de TVN en su jornada real |
| 3:00 | [#3 Demo](#3-demo-en-vivo) | Flujo completo en vivo |
| 5:00 | [#4 Cómo funciona](#4-cómo-funciona-arquitectura) | Pipeline determinista |
| 6:30 | [#5 IA](#5-ia-baseline-vs-mejora) | Baseline vs. mejora, con la limitación |
| 7:30 | [#6 Evidencia](#6-evidencia-y-explicabilidad) | Cita, score, abstención |
| 8:30 | [#7 Impacto](#7-impacto-números-reales) | Números del demo |
| 9:00 | [#8 Ética](#8-seguridad-privacidad-y-ética) | Nunca publica |
| 9:30 | [#9–10 Roadmap y equipo](#9-roadmap) | Qué sigue |

---

## 1. Problema

Una redacción recibe **más señal de la que puede procesar**: titulares que se repiten en varios medios, datos oficiales con años distintos, urgencias de verdad y urgencias de aparariencia.

> **El costo real:** priorizar a intuición significa repetir eco por segunda fuente, publicar una cifra sin contexto de año, o dejar que el tema urgente pase desapercibido.

**Panorama resuelve el paso que falta entre la señal y la decisión:** *¿qué merece atención hoy, con qué evidencia, y qué aún no está listo?*

## 2. Usuario

**Editor de TVN Media (modalidad editorial del reto).**

| Su jornada hoy | Con Panorama |
|---|---|
| Revisa 6 portales y 3 dashboards | Abre **una mesa** ordenada por prioridad con motivo |
| Pregunta "¿esto ya lo dijeron?" | Ve *"4 medios, 3 son eco"* — la repetición no engaña |
| Busca el dato oficial que respalda la cifra | La ficha ya enlaza indicador con **período y unidad** |
| Decide con poco tiempo y sin garantía | Cada tema trae **borrador con citas** o **abstención explícita** |

> *"¿Qué 5 temas reviso hoy y por qué?"* — esa es la pregunta que Panorama responde con una fórmula publicada.

## 3. Demo en vivo

**URL:** https://panorama.sweetcode.studio

Flujo completo (6 pasos):

1. **Acceso** — el editor se identifica; toda decisión queda firmada.
2. **Mesa de hoy** — temas ordenados; pestañas por estado; clic abre la ficha.
3. **Ficha del tema** — qué se reporta · quién · qué está respaldado · qué falta + desglose `R I U N E`.
4. **Requieren evidencia** — una sola fuente, eco o versiones contradictorias.
5. **Borrador** — brief ≤250 palabras, guion 45–60 s, copy ≤80 palabras, **cita por afirmación**.
6. **Decisión humana** — aprobar / corregir / descartar. **No hay botón de publicar.**

<details>
<summary>📸 Capturas (si no hay red en vivo)</summary>

- Mesa: `docs/screenshots/01-mesa.png`
- Ficha: `docs/screenshots/02-ficha.png`
- Requieren evidencia: `docs/screenshots/03-requieren-evidencia.png`
- Fuentes: `docs/screenshots/04-fuentes.png`
- Publicaciones: `docs/screenshots/05-publicaciones.png`
- Calidad: `docs/screenshots/06-calidad.png`

</details>

**Demo sin internet (T10):** todo corre sobre el snapshot local con SHA-256 — la misma máquina sirve la demo en el salón sin conexión.

## 4. Cómo funciona (arquitectura)

```
Fuentes públicas          Ingesta (lote)           Núcleo determinista
TVN RSS · GDELT    →   snapshot congelado    →   valida → agrupa → eco
Banco Mundial · USGS     + manifest SHA-256       → score P → ficha+borrador
                                                          ↓
                          Interfaz SPA  ←——  API FastAPI  ←—— guard (anti-inyección)
                                ↓
                     Revisión humana firmada (persistida)
```

- **Por lotes**, sin monitoreo continuo — como exige el reto.
- **Determinista:** prioridad y verificación son funciones puras; la IA no decide.
- **Reproducible:** `manifest.json` con SHA-256; mismo snapshot → misma mesa.
- Detalle completo: [Documentación técnica en Notion] · repo `docs/ARQUITECTURA.md`.

## 5. IA: baseline vs. mejora

| Nivel | Enfoque | Costo |
|---|---|---|
| Recuperación/agrupación | **Embeddings locales (fastembed)** vs. baseline **BM25** | $0, offline |
| Redacción | LLM bajo demanda (OpenCode Zen → OpenRouter → plantilla local) | free tier |
| **Prioridad y verificación** | **No usan LLM** — determinista y auditable | — |

**Métricas reales:**

| Métrica | Resultado | Meta |
|---|---|---|
| Cobertura de citas | **100%** | 100% |
| Sustento humano (rúbrica estricta) | **97.67%** (42/43 · 40 fichas) | ≥90% |
| Abstención (sin respuesta) | **100%** | ≥80% |
| Contradicción manejada | **100%** | sin elegir arbitrariamente |
| Adversarial bloqueado | **100%** | 100% |
| Aceptación T01–T10 | **10/10** | 10/10 |
| Latencia mediana / p95 | **16.2 ms / 42.8 ms** | ≤15 s |

> **⚠️ Limitación reconocida (decimos la verdad al jurado):** con 30 etiquetas humanas de clasificación, el modelo ML (TF-IDF + LogReg, macro-F1 **0.36**) **no supera** al baseline por palabras clave (**0.80**). Publicamos el resultado negativo y dejamos la ampliación de etiquetas como tarea pendiente (`feat/classification-labels`). La agrupación semántica sí logra **F1 = 1.00** en la muestra etiquetada.

**Benchmark:** 60 consultas (30 sustentadas · 10 contradicción · 10 sin respuesta · 10 adversariales), de las cuales **20 quedan reservadas al jurado** (`data/benchmark.jury.jsonl`).

## 6. Evidencia y explicabilidad

| Garantía | Cómo se ve |
|---|---|
| **Cita por afirmación** | Cada afirmación del borrador enlaza fuente + fecha + URL (cobertura 100%) |
| **Score reproducible** | `P = 30R + 25I + 20U + 15N + 10E`, reglas `p-1.0` publicadas |
| **Eco ≠ corroboración** | "N medios, M son eco"; la duplicación **no** sube puntaje ni confianza |
| **Contradicciones marcadas** | "versiones en conflicto" en vez de elegir una |
| **Abstención** | Si el corpus no respalda, lo dice — sin cifra inventada (T06) |
| **Estado de evidencia** | Confirmado · Corroborado · Contradicho · Sin verificar — **independiente** del puntaje |

## 7. Impacto (números reales)

| Dato | Valor |
|---|---|
| Noticias procesadas en la demo | **250** (50 TVN + 200 GDELT), ventana 2025-10-02 → 2026-09-30 |
| Indicadores oficiales | **540** (6 países × 6 indicadores × 2010–2024, Banco Mundial) |
| Eventos oficiales | **82** sismos USGS (2024, bbox Panamá) |
| Fichas generadas | **40** con evidencia y afirmaciones citadas |
| Afirmaciones revisadas por humanos | **43** → 42 válidas (**97.67%** ≥ meta 90%) |
| Respuesta a la consulta | **16.2 ms** mediana (frente a ≤15 s del contrato) |
| Cobertura de citas | **100%** de las afirmaciones con su fuente |

> **Sin exagerar:** estos son los números del snapshot actual, verificables con `python -m eval.benchmark` y `python -m eval.sustento` desde el repo.

## 8. Seguridad, privacidad y ética

- **Nunca publica.** No existe acción de publicación en el producto; aprobar un borrador ≠ publicar.
- **Anti-inyección:** el texto de cualquier fuente se trata como **dato, no instrucción** (T07; 100% adversarial bloqueado).
- **Derechos documentados:** catálogo de fuentes con licencia/condiciones por fuente.
- **Sin datos personales** y sin rating/desinformación — fuera de alcance, documentado.
- **Secretos** fuera del repo (Dokku config); CI con SAST, SCA y scan de secretos obligatorio en cada PR.
- **Decisiones firmadas** con usuario y timestamp — trazabilidad completa.

## 9. Roadmap

| Siguiente | Motivo |
|---|---|
| Ampliar etiquetas de clasificación (ML > baseline) | Cerrar la limitación declarada en §5 |
| Calibrar umbral de agrupación con más pares reales | P/R reales fuera de la muestra exploratoria |
| Migrar workspace al **Notion oficial** del evento | Trazabilidad exigida por la rúbrica |
| Extensión bancaria SBP (opcional) | Modalidad de riesgo — fuera de alcance actual |
| Correos/alertas de mesa diaria | Distribución del resultado al equipo |

## 10. Equipo

<table>
  <tr>
    <td align="center" width="50%">
      <img src="../authors/daniel_round.png" width="120" alt="Daniel Valdés" /><br/>
      <b>Daniel Valdés</b><br/>
      <sub>DevSecOps · Infraestructura y datos</sub><br/>
      <a href="https://www.linkedin.com/in/daniel--valdes">LinkedIn</a> ·
      <a href="https://github.com/danielvaldess">GitHub</a>
    </td>
    <td align="center" width="50%">
      <img src="../authors/jose_round.png" width="120" alt="José C. Miranda" /><br/>
      <b>José C. Miranda</b><br/>
      <sub>Backend · Datos e IA</sub><br/>
      <a href="https://www.linkedin.com/in/jos-mi-cast-300mm1500/">LinkedIn</a> ·
      <a href="https://github.com/josecmirandac15">GitHub</a>
    </td>
  </tr>
</table>

**SWEETCODE** · Panamá · hackIAthon 2026 — *De la señal a la decisión.*

---

## 🔗 Enlaces para el jurado (verificable)

| Qué | Dónde |
|---|---|
| Demo en vivo | https://panorama.sweetcode.studio |
| Repo (README, instalación, pruebas) | https://github.com/danielvaldess/panorama |
| Matriz de pruebas T01–T10 | `GET /api/acceptance` o `python -m eval.acceptance` |
| Benchmark 60 casos (20 reservados) | `python -m eval.benchmark` |
| Sustento ≥90% | `python -m eval.sustento` |
| Documentación técnica / funcional | `docs/notion/DOCUMENTACION-TECNICA.md` · `DOCUMENTACION-FUNCIONAL.md` |
| Trazabilidad (bitácora, decisiones, pruebas) | Tablas 📝 bitácora · 🧭 decisiones · 🧪 pruebas de este workspace |
