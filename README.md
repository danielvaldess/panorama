<p align="center">
  <img src="docs/logo.png" width="96" alt="Panorama" />
</p>

<h1 align="center">Panorama</h1>

<p align="center">
  <b>Inteligencia editorial para la redacción.</b><br/>
  Convierte noticias públicas y datos oficiales en información priorizada, con evidencia verificable.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white" alt="HTML5" />
  <img src="https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white" alt="CSS3" />
  <img src="https://img.shields.io/badge/IA-OpenRouter-6C5CE7" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/Deploy-Dokku-4E9A06?logo=linux&logoColor=white" alt="Dokku" />
  <img src="https://img.shields.io/badge/Cloudflare-Tunnel-F38020?logo=cloudflare&logoColor=white" alt="Cloudflare Tunnel" />
  <img src="https://img.shields.io/badge/hackIAthon-Panam%C3%A1%202026-005588" alt="hackIAthon" />
</p>

<p align="center">
  <a href="https://sandbox.sweetcode.studio"><b>Demo en vivo</b></a>
</p>

---

## ¿Qué es?

**Panorama** (nombre provisional) es una herramienta de **mesa editorial** para
medios: toma **noticias públicas y datos oficiales**, los **prioriza** según la
relevancia para el usuario y entrega cada tema en una **ficha con evidencia
verificable** (fuentes citadas, nivel de confianza y contradicciones).

**Principio rector:** la IA **asiste** (resume, clasifica, sugiere); **la decisión
es humana**. Nada se publica soló — el flujo siempre pasa por una **revisión**.

> Reto: convertir noticias públicas y datos oficiales en información priorizada con
> evidencia verificable, **para apoyar una decisión humana y no publicar directamente.**

## Demo

![Mesa de prioridades](docs/screenshots/01-mesa-prioridades.png)

▶ **https://sandbox.sweetcode.studio**

## Cómo funciona

```
Fuentes (medios + datos oficiales)
   → Lectura y normalización
   → Priorización editorial (puntuación reproducible)
   → Ficha del tema con fuentes citadas y nivel de confianza
   → Detección de contradicciones / "sin evidencia suficiente"
   → Borrador asistido
   → REVISIÓN HUMANA → publicado (nunca automático)
```

## Diseño

Interfaz **empresarial de newsroom**, con la identidad de **TVN Media**:

- **Colores:** primario `#005588` · rojo `#e00710` · apoyo `#0077c8`.
- **Tipografía:** **Raleway** (titulares) + **Oxygen** (interfaz).
- **Lenguaje editorial**, sin jerga técnica (ver [`docs/DESIGN.md`](docs/DESIGN.md)).
- **IA invisible:** se muestra "resumen asistido", no "modelo" ni "API".

## Estado

- [x] Concepto y diseño (mockup de la mesa de prioridades)
- [x] Identidad visual (tokens de TVN)
- [x] Entorno de despliegue y auto-deploy
- [x] Notion (trazabilidad del evento)
- [ ] Prototipo con datos reales
- [ ] Baseline de IA + métricas
- [ ] Pitch

## Estructura

```
web/            mockup de la interfaz (mesa de prioridades)
pipeline/       fuentes (medios + GDELT) → dedupe → prioridad + evidencia
eval/           métricas (baseline vs modelo, citas, abstención)
agent/          agente respaldado por Notion
docs/
  DESIGN.md     sistema de diseño (identidad TVN)
  AI.md         integración con OpenRouter
  SERVER.md     infraestructura y despliegue
  RECURSOS-EXISTENTES.md  APIs/datasets reutilizables
  RETOS-ANALISIS.md       patrones de los retos
  notion/       playbook + bases de datos
  screenshots/  capturas
methods/        utilidades reutilizables (capturas, PDF, diagramas, Notion)
```

### Pipeline (priorización con evidencia)

```bash
pip install httpx
python -m pipeline.run            # determinista (medios + GDELT → citas → prioridad)
python -m pipeline.run --ai       # + resúmenes con OpenRouter
python -m pipeline.run --notion   # + publicar fichas en Notion
```

## Despliegue

Auto-deploy vía **Dokku**: un `git push` a `main` reconstruye y publica
(ver [`docs/SERVER.md`](docs/SERVER.md)).

## Equipo

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/authors/daniel_round.png" width="130" alt="Daniel Valdés" /><br/>
      <b>Daniel Valdés</b><br/>
      <sub>DevSecOps · Infraestructura</sub><br/><br/>
      <a href="https://www.linkedin.com/in/daniel--valdes/">LinkedIn</a> ·
      <a href="https://github.com/danielvaldess">GitHub</a>
    </td>
    <td align="center" width="50%">
      <img src="docs/authors/jose_round.png" width="130" alt="José C. Miranda" /><br/>
      <b>José C. Miranda</b><br/>
      <sub>Backend · Datos</sub><br/><br/>
      <a href="https://www.linkedin.com/in/jos-mi-cast-300mm1500/">LinkedIn</a> ·
      <a href="https://github.com/josecmirandac15">GitHub</a>
    </td>
  </tr>
</table>

---

<p align="center"><sub>Equipo SWEETCODE · hackIAthon Panamá 2026</sub></p>
