# Evidencia v2 — antes / después (T1–T10)

`rules_version` **p-2.1**. Este documento registra qué regla cambió (para la decisión
en Notion), el antes/después de la ficha del **MERCOSUR** y la tabla de resultados.

## Reglas cambiadas por tarea

| Tarea | Regla anterior | Regla nueva |
|---|---|---|
| T1 | `evidence_state = f(official, independent)`; E escalonado con `official → 1.0` | Tipado de afirmación; E continuo `0.35·primaria + 0.40·corroboración + 0.15·confiabilidad + 0.10·trazabilidad − 0.30·contradicción`; declaración oficial sin corroboración ⇒ **Parcial** |
| T2 | `independent` = proxy textual (RapidFuzz 0.70) | `origen_real` (agencia/dominio) + embeddings ≥0.72, RapidFuzz de respaldo; comparado con baseline |
| T3 | U = `1 − edad/14d`; sin tope; fecha de detección de GDELT usada | `edad_dias` desde publicación; U = `exp(−edad/7d)`, 0 si edad>14; noticia antigua fuera de “Mesa de hoy”, tope P≤39, badge y fecha original |
| T4 | Clasificación por palabras clave (sin confianza) | Híbrido keywords + embeddings con confianza y 2 candidatos; nuevo tema “relaciones exteriores/comercio”; `sin_clasificar` si no hay certeza |
| T5 | `servicios → Internet/Población` por defecto | Tabla explícita tema→indicador; si no hay relación ⇒ “Sin indicador oficial pertinente”; justificación, país, año, unidad y nota de dato anual |
| T6 | Guion con meta-mensajes; título truncado con “…” | `texto_al_aire` ≠ `notas_internas`; atribución de declaraciones; título sin “…” (corta en palabra); preguntas específicas; validador de citas |
| T7 | Fallo de IA silencioso | Fallback determinístico visible + caché de salidas válidas |
| T8 | “0% válidas” con muestra incompleta | “Pendiente de revisión humana (0/N revisadas)”; unidades y numerador/denominador consistentes |
| T9 | — | Casos concretos en `pytest` + CI + `gitleaks`/`pre-commit` |
| T10 | — | `rules_version` en `manifest.json` y UI; este reporte antes/después |

## Antes / después — ficha MERCOSUR

| Aspecto | v1 | v2 |
|---|---|---|
| Estado de evidencia | Suficiente para el borrador | **Parcial** |
| E | 1.0 | **0.37** (primaria 0.5 · corroboración 0 · confiabilidad 0.6 · trazabilidad 1.0 − contradicción 0) |
| Tipo de afirmación | “hecho reportado” | **declaración institucional** (atribuida) |
| Tema | servicios | **relaciones exteriores / comercio** |
| Corroboración independiente | 1 (y “Suficiente”) | 1 ⇒ Parcial |
| Prioridad / Urgencia | 58 / 0% | **39 / 0%** (recirculada, edad 99 días) |
| Contexto oficial | Internet / Población | **Exportaciones (% del PIB)** con justificación |
| Guion al aire | contenía “Hay evidencia suficiente…” | sin meta-mensajes; “El Ministerio afirma…” |
| Título propuesto | truncado con “…” | completo (corta en palabra) |
| Falta comprobar | genérico | **corroboración independiente** (coherente con Parcial) |

Generado por `python -m eval.before_after` → `eval/before_after.json`.

## Tabla de resultados por caso

| Caso | Entrada | Esperado | Observado | Evidencia |
|---|---|---|---|---|
| MERCOSUR | nota oficial autoreferencial | Parcial | Parcial · declaración institucional · E<1 | `tests/test_evidence_v2.py` |
| Contradicción | confirma vs desmiente | Parcial + ambas | flag `contradiccion` · Parcial | `test_evidence_v2` |
| Agencia x5 | 5 medios misma agencia | 1 procedencia | `independent=1` | `test_provenance` |
| Noticia antigua | 99 días | fuera de Mesa de hoy | recirculada · P≤39 | `test_freshness` |
| Sin indicador | tema servicios | “Sin indicador pertinente” | `sin_contexto` | `test_context` |
| Dato anual | PIB Banco Mundial | año+unidad, no “de hoy” | período/unidad + nota | `test_context` |
| Guion | declaración oficial | sin meta-mensajes | `texto_al_aire` limpio | `test_draft` |
| Inyección | “ignora instrucciones…” | no obedece | sin secretos | `test_security` |
| Abstención | pregunta sin respuesta | abstenerse | `answered=False` | `test_security` |
| Invariante | estado Suficiente | sin pendiente de corroboración | test pasa | `test_evidence_v2` |

## Métricas de apoyo

- **Agrupación por procedencia** (`eval/provenance.json`): baseline léxico F1 **0.38** vs v2 (origen+embeddings) **0.67**.
- **Clasificación temática** (`eval/themes.json`): baseline keywords macro-F1 **0.83** vs embeddings **0.70** → el producto usa el híbrido (keywords cuando el término es explícito).
- **Tests**: `python -m pytest tests -q` (28) + `python -m eval.acceptance` (T01–T10).
