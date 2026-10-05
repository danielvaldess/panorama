# Análisis de los retos iniciales — qué revelan sobre el reto final

Los 5 retos del PDF de filtro. Solucionamos el 4; los otros 4 son **pistas** del
ecosistema y de cómo esperan que trabajemos.

## Los 5 retos (resumen)

| # | Reto | Entrada | Núcleo | Salida |
|---|------|---------|--------|--------|
| 1 | **Pre-Autorización Quirúrgica** | Informe médico + póliza **en una base de datos de Notion** | Cobertura + carencia | Preaprobación / pedir documentos faltantes |
| 2 | **Auditor de Facturación (siniestros)** | Documentos + facturas del taller | Tarifario + siniestralidad | Detectar discrepancias/duplicados |
| 3 | **Estimador de Copago (conversacional)** | Síntoma del paciente | Plan de seguro | Copago exacto + hospital más conveniente |
| 4 | **Alerta Temprana de Emergencias** (el nuestro) | Ingreso a urgencias | Póliza + pre-existencias | Notificar a hospital **y** aseguradora |
| 5 | **Bienestar Preventivo y Gamificación** | Diagnósticos anónimos frecuentes | Analítica + campañas | Beneficios/descuentos **en el CRM de Notion** |

## Patrones comunes (el "cómo trabajaremos")

1. **Notion es central.** Los retos 1 y 5 lo usan explícitamente como **base de datos
   / CRM**, y la rúbrica evalúa "Notion: ejecución y pitch". → Notion es la **capa de
   datos/CRM** del ecosistema.
2. **Mismo blueprint de agente en todos:**
   `Entrada (documento/dato) → Validación determinista → IA que interpreta/sintetiza →
   Acción/borrador → REVISIÓN HUMANA → notificación/registro`.
3. **Humano en el loop, siempre.** "antes de que un humano revise" (2), "apoyar una
   decisión humana y no publicar" (reto nuevo), notificar a personas (4).
4. **Determinismo + IA.** Lo crítico (cobertura, tarifario, copago, pre-existencias)
   se calcula con **reglas/datos**; la IA **explica/redacta**. Nunca alucina la regla.
5. **Evidencia y trazabilidad.** Citas, cálculo reproducible, auditoría.
6. **Multi-partes.** Notificar/actualizar a varios actores (hospital, aseguradora,
   taller, paciente, redacción).

## Dominios

- Retos 1–5: **salud + seguros** (hospital, aseguradora, talleres, siniestros).
- Reto nuevo (selección): **medios (TVN) o banca**. → El sponsor y el patrón se
  mantienen: *datos → validación → IA → decisión humana*.

## Qué ya dejamos preparado (sirve para cualquier reto)

- **Notion operativo**: MCP + API, workspace con bases (catálogo, bitácora,
  decisiones, pruebas, priorización). Podemos **crear/leer/actualizar** registros.
- **Blueprint de agente**: ingesta → validación determinista → IA con citas →
  borrador → aprobación humana → auditoría (patrón de los 5 retos).
- **Capa de notificaciones** a múltiples destinos.
- **Diseño enterprise + lenguaje editorial** (sin jerga técnica).
- **Despliegue** `git push → Dokku` + Cloudflare Tunnel.

## Qué conviene preparar aún

- **Agente respaldado por Notion**: leer una base, validar contra reglas y
  **actualizar el registro** (por si el reto final usa Notion como CRM/datos).
- **Plantilla reutilizable de "ficha + evidencia"** (sirve a medios y a seguros).
- **Motor de reglas determinista** separado (cobertura/copago/tarifario/prioridad).
- **Baseline + métricas** de IA (la rúbrica premia medir mejora o limitación).

## Conclusión

El reto final, sea TVN o banca, caerá en el **mismo molde**: *recibir datos →
validar con reglas → asistir con IA (con evidencia) → decidir un humano →
registrar en Notion*. Por eso conviene invertir en **el blueprint del agente** y en
**Notion como capa de datos**, no en una solución específica.
