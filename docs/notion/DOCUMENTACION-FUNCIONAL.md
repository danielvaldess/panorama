# Documentación funcional — Panorama

> Pega este documento en Notion. Cubre: usuario, alcance funcional, casos de uso, flujos, estados, pantallas, reglas de negocio y criterios de aceptación — sin jerga técnica.

---

## 1. Usuario y contexto

| Pregunta | Respuesta |
|---|---|
| **¿Para quién es?** | Redacción de **TVN Media** (modalidad editorial del reto). Extensión a banca: fuera de alcance (decisión D1). |
| **¿Qué hace hoy?** | Llegan muchas señales (noticias, datos oficiales) y el equipo debe decidir rápido qué es tema, qué necesita verificar y qué no es noticia. |
| **¿Qué le duele?** | Priorizar a intuición, repetir información ya publicada (eco), publicar algo sin sustento o perder un tema urgente. |
| **¿Cómo se lo resuelve Panorama?** | Una **mesa priorizada con motivo explicado** y, por cada tema, una **ficha con evidencia** y un **borrador con citas** — y la decisión final es del editor. |

> **Diseño clave:** la circulación de una noticia **no equivale a su confirmación**. Panorama distingue repetición (eco) de corroboración independiente, se **abstiene** cuando no hay evidencia y **nunca publica**.

## 2. Alcance funcional

### 2.1 Lo que SÍ hace

1. **Cargar** un snapshot de fuentes públicas validando IDs, URLs, fechas y nulos (reporta calidad, no bloquea por errores aislados).
2. **Organizar** el material: clasificar por tema y agrupar el mismo evento (sin duplicar).
3. **Contextualizar** cada tema con datos oficiales (indicador del Banco Mundial con período/unidad; sismos USGS) sin forzar relaciones.
4. **Priorizar** con un puntaje explicado por componentes: relevancia, impacto, urgencia, novedad, evidencia.
5. **Explicar** cada tema en una ficha: qué se reporta, quién lo reporta, qué está respaldado y qué falta comprobar.
6. **Producir** un borrador editorial (brief, guion 45–60 s, copy ≤80 palabras) con **cita por afirmación**.
7. **Revisar**: el editor acepta, corrige o descarta; cada decisión queda firmada y persistida.

### 2.2 Lo que NO hace (por diseño)

| No hace | Por qué |
|---|---|
| Publicar automáticamente | La decisión es humana y bloqueante |
| Etiquetar noticias como "verdadero/falso" | El sistema mide evidencia, no verdad absoluta |
| Sumar repetición como confirmación | Eco ≠ corroboración independiente |
| Incluir rating, desinformación, datos personales o producción audiovisual | Fuera del alcance del reto (documentado) |
| Modificar el puntaje con decisiones humanas | El perfil del Administrador es **descriptivo**, sin re-ranking oculto |

## 3. Casos de uso

| ID | Caso | Comportamiento esperado | Estado |
|---|---|---|---|
| CU-01 | "¿Qué 5 temas revisar hoy y por qué?" | Mesa ordenada por puntaje con componentes visibles | ✅ |
| CU-02 | Tema económico con serie oficial | Indicador BM enlazado con **período y unidad** (no se confunde el año) | ✅ |
| CU-03 | Tres medios publican el mismo evento | Se agrupa en **una** ficha; "2 son eco"; la duplicación no sube el puntaje | ✅ |
| CU-04 | Cifra inexistente en el corpus o contradicción | **Abstención** o "versiones en conflicto" — sin elegir arbitrariamente | ✅ |
| CU-05 | Titular con instrucción maliciosa ("ignora tus reglas") | Se trata como **dato**, nunca como instrucción; disclaimer presente | ✅ |
| CU-06 | Editor aprueba un borrador | Queda registrado quién, cuándo y en qué estado; **no publica** | ✅ |
| CU-07 | Banca (riesgo/reputación) | Fuera de alcance por decisión D1 (no exigido) | ✅ |

## 4. Flujo principal (7 etapas)

```
1 Cargar → 2 Organizar → 3 Contextualizar → 4 Priorizar
     → 5 Explicar (ficha) → 6 Producir (borrador) → 7 Revisar (humano)
```

1. **Cargar** — valida el snapshot; los nulos se conservan; un registro malo no tumba la carga.
2. **Organizar** — clasifica temas y agrupa duplicados del mismo evento.
3. **Contextualizar** — vincula el dato oficial pertinente (o no vincula nada si no hay relación honesta).
4. **Priorizar** — calcula `P = 30R+25I+20U+15N+10E` y expone cada componente.
5. **Explicar** — la ficha responde: ¿qué se reporta? ¿quién? ¿qué está respaldado? ¿qué falta?
6. **Producir** — brief ≤250 palabras, guion 45–60 s, copy ≤80 palabras, con cita por afirmación.
7. **Revisar** — el editor mueve el tema entre estados; nada avanza sin su acción.

## 5. Estados de revisión (control humano)

| Desde | Acción del editor | Hasta |
|---|---|---|
| Nuevo | Enviar a revisión | En revisión |
| Nuevo | Detectar que falta evidencia | Requiere evidencia |
| En revisión | Aprobar borrador | Aprobado borrador |
| En revisión | Descartar | Descartado |
| Requiere evidencia | Evidencia conseguida | En revisión |

> **Aprobar un borrador no significa publicar.** No existe acción de "publicar" en el producto.

## 6. Pantallas

| # | Pantalla | Qué ve y hace el usuario |
|---|---|---|
| 0 | **Acceso** | Se identifica con nombre y rol; cada decisión queda firmada por la persona responsable |
| 1 | **Mesa de hoy** | Temas ordenados por prioridad; pestañas: Todos · Requieren evidencia · En revisión · Listos para publicar; filtros por categoría; un clic abre la ficha |
| 2 | **Ficha del tema** | Qué se reporta, paquete editorial (guion y copy), afirmaciones con citas y evidencia, y desglose del puntaje (R, I, U, N, E) |
| 3 | **Requieren evidencia** | Temas con una sola fuente, repetición entre medios o versiones contradictorias |
| 4 | **Fuentes** | Medios y datos oficiales con confiabilidad y derechos |
| 5 | **Publicaciones** | Lo publicado por las fuentes, sin duplicados, hora de Panamá |
| 6 | **Calidad** | Actividad de la mesa y control de calidad del sistema (T01–T10, métricas) |
| 7 | **Cómo funciona** | El recorrido en 4 pasos dentro de la propia plataforma |

## 7. Reglas de negocio visibles para el usuario

| Regla | Cómo se ve |
|---|---|
| Prioridad explicable | Cada tema muestra P y sus 5 componentes; fórmula publicada |
| Rangos | baja [0,40) · media [40,70) · alta [70,100] |
| Evidencia independiente del puntaje | Un tema "alta" puede estar "sin verificar" |
| Eco ≠ fuentes | "N medios, M son eco" en la ficha |
| Abstención | Si el corpus no respalda, la ficha lo dice explícitamente en vez de rellenar |
| Cita por afirmación | Cada afirmación del borrador enlaza a su fuente, fecha y alcance |
| Disclaimer | Si solo hay titular/metadatos, se marca el límite del material |
| Prioridad de datos oficiales | El indicador siempre muestra período y unidad |

## 8. Criterios de aceptación (resumen T01–T10)

| ID | Criterio | Resultado |
|---|---|---|
| T01 | Fechas inválidas y nulos: reporta errores sin bloquear la carga | ✅ |
| T02 | Tres registros del mismo evento → 1 grupo, sin triplicar | ✅ |
| T03 | Noticia antigua recirculada → urgencia baja, fecha original conservada | ✅ |
| T04 | Cifra anual del Banco Mundial se presenta con su año/unidad | ✅ |
| T05 | Afirmaciones incompatibles → contradicción detectada, sin elegir | ✅ |
| T06 | Consulta sin respuesta → abstención, sin cifra inventada | ✅ |
| T07 | Fuente con instrucción hostil → tratada como dato | ✅ |
| T08 | Caso de prioridad alta → componentes expuestos, sin aprobación automática | ✅ |
| T09 | Brief editorial dentro de límites, con citas | ✅ |
| T10 | Demo sin internet sobre snapshot local | ✅ |

## 9. Métricas funcionales (contrato con el usuario)

| Expectativa | Métrica | Resultado |
|---|---|---|
| "Toda afirmación tiene su fuente" | Cobertura de citas | **100%** |
| "El sustento resiste revisión humana" | Sustento válido (rúbrica estricta) | **97.67%** (42/43) ≥90% ✅ |
| "No responde lo que no sabe" | Abstención correcta | **100%** ≥80% ✅ |
| "No se contradice sin avisar" | Contradicción manejada | **100%** ✅ |
| "Resiste intentos de manipulación" | Adversarial bloqueado | **100%** ✅ |
| "Es rápido" | Latencia mediana | **16.2 ms** |

## 10. Roles y responsabilidad

| Rol | Qué puede hacer |
|---|---|
| **Editor (usuario)** | Priorizar, abrir fichas, aprobar/corregir/descartar borradores, registrar decisiones firmadas |
| **Administrador** | Todo lo anterior + ver su perfil de decisiones (preferencias agregadas, ≥5 decisiones para mostrar) + registrar veredictos de sustento por afirmación |
| **Sistema** | Proponer orden, fichas, borradores y estados; **nunca aprobar ni publicar** |

## 11. Requisitos no funcionales

| Requisito | Cómo se cumple |
|---|---|
| Reproducibilidad | Snapshot congelado + SHA-256; mismo input → mismo output |
| Offline (demo) | Todo corre sin internet sobre `data/raw/` |
| Rendimiento | Mediana 16.2 ms / p95 42.8 ms |
| Accesibilidad | HTML semántico, sin frameworks, contraste alto en la UI |
| Trazabilidad | Decisiones firmadas con usuario y timestamp; auditables |
| Transparencia | Fórmula, reglas y limitaciones publicadas en docs y en la UI |

---

**Enlaces:** [Documentación técnica](DOCUMENTACION-TECNICA.md) · [Pitch Day](pitch-day.md) · [Cumplimiento del reto](../CUMPLIMIENTO-RETO.md)
