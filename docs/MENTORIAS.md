# Mentorías del hackIAthon — aprendizajes

Resumen de las **5 mentorías** del evento (transcripciones en el material del
hackIAthon) y **cómo aplica cada una a Panorama**. Fueron las "pistas" de cómo
trabajar, no requisitos del reto.

---

## 1 · Israel Julio Gómez — Codex, Skills, MCP y desarrollo agéntico

**Ideas clave**
- Fases del uso de IA en desarrollo: autocompletado → chat → **delegación agéntica** (el agente hace la tarea completa: entorno, archivos, pruebas, deploy).
- **Prompt estructurado** = **objetivo** (resultado), **contexto** (comportamiento), **restricciones/reglas** (qué sí/qué no, estilo) y **validaciones** (qué hacer al terminar).
- **`AGENTS.md`** en el repo: comprobaciones, entorno por defecto, consistencia entre personas y entornos.
- **Skills**: empaquetar flujos de trabajo reutilizables en comandos.
- **MCP**: conectar herramientas externas (Slack, Figma, Linear, AWS, Firebase, Supabase…) para tener contexto directo e integridad.
- Frameworks/APIs: **Agno** (agentes en Python), **Groq** (API gratuita y rápida), modelos open source.

**Aplicado a Panorama:** usamos **`AGENTS.md`**; prompts con objetivo/contexto/restricciones/validaciones (en la generación editorial); agentes de CLI para construir. (No necesitamos MCP/Agno para el MVP.)

## 2 · Johanna Barragán — Vibecoding con Lovable

**Ideas clave**
- **Vibecoding**: describir en lenguaje natural → la IA genera código; luego **revisar, probar y refinar**.
- Ventajas: productividad, **MVP en minutos**, **código portable** (GitHub), menor curva.
- Riesgos: dependencia, **alucinación**, **seguridad** (revisar, SonarQube/SCA); no confiar ciegamente.
- **Prompt**: contexto, tarea, guías y restricciones; método **C.L.E.A.R.** (conciso, lógico, explícito, adaptable, reflexivo); evitar ambigüedad; dividir tareas; *meta-prompting*.
- **Separar front y back** (no mezclar Lovable + Supabase full-stack).

**Aplicado a Panorama:** **front (`web/`) y back (`pipeline/`) separados**; UI iterada con asistencia; revisión humana y disclaimers; seguridad (anti-inyección, `guard.py`).

## 3 · Jeyson Jaramillo — Despliegue de un chatbot (Cloud Run + Firebase + LangChain)

**Ideas clave**
- Backend **Python + LangChain** + LLM (Llama 3 vía **Fireworks**), empaquetado con **Dockerfile**, desplegado en **Google Cloud Run**.
- Frontend React (**Lovable**) → **Firebase Hosting** (`build` → deploy).
- Requisitos: GCP (prueba **$300/91 días**), facturación activa, Artifact Registry.

**Aplicado a Panorama:** mismo principio de **contenedor reproducible** y separación back/front, pero desplegamos con **Docker + Dokku** y **Cloudflare Tunnel** (sin depender de GCP).

## 4 · Ricardo Gómez — Cursor para trabajar (transcripción parcial)

**Ideas clave**
- **Cursor**: editor con IA integrada, con **contexto de los archivos**; importa proyectos de VS Code.
- **Reglas de usuario** (idioma, concisión, dar alternativas, priorizar lo técnico) → ahorro de tiempo y consistencia.
- **3 modos**: **agente** (multi-archivo, ejecuta), **pregunta** (explica), **background** (lee sin modificar).

**Aplicado a Panorama:** trabajamos con un asistente con **reglas de proyecto** (`AGENTS.md`) que cumple ese rol; separamos "explicar" de "ejecutar".

## 5 · Jorge Hugo Cruz — RPA + IA (web scraping)

**Ideas clave**
- Automatizar la validación de **RUC** en el DGI con **RPA** (Rocketbot / Automation Anywhere) + **web scraping**.
- CAPTCHA: extensión **Buster** o API **2Captcha** (con librería Python).

**Aplicado a Panorama:** refuerza el valor de los **datos oficiales**, pero preferimos **APIs públicas** (Banco Mundial, USGS, GDELT) en lugar de scraping frágil con captchas.

---

## Principios transversales (lo que repitieron)

1. **Prompt estructurado**: contexto + objetivo + restricciones + validaciones.
2. **Reglas del proyecto** (`AGENTS.md` / Cursor rules) para consistencia.
3. **Revisar** lo que genera la IA: seguridad y pruebas; no confiar ciego (**alucinación**).
4. **Separar front y back**; código **portable** en GitHub.
5. **Herramientas**: Codex/Cursor/opencode + **skills**; APIs gratuitas (**Groq**); frameworks de agentes (**Agno**).
6. **Reutilizar**: skills, plantillas, ejemplos.

## Cómo lo aplicamos en Panorama

- `AGENTS.md` en el repositorio.
- **Front/back separados**: `web/` (interfaz) y `pipeline/` (núcleo/API).
- **Generación con estructura** y **anti-alucinación/abstención** (`draft.py`, `guard.py`).
- **Docker reproducible** + deploy (Dokku + Cloudflare Tunnel).
- **Datos por API pública** (sin scraping).
- Nota: la mentoría de **Ricardo quedó parcial** (transcripción ~6 min de 30).
