# Sistema de diseño — plataforma editorial (TVN Media)

> Objetivo: una herramienta **empresarial de newsroom**, con la identidad de TVN
> Media. Lenguaje **editorial**, cero jerga técnica. La IA es invisible.

## 1. Tokens de marca (extraídos del sitio de TVN)

Fuente: CSS de `tvn-2.com` (`--background-accent-color: #058`, `.bbnx-btn`, etc.).

### Paleta
| Token | Hex | Uso |
|---|---|---|
| **Primario (TVN)** | `#005588` | Logo, botones, enlaces, acentos |
| Primario oscuro | `#00466f` | Hover/activo del primario |
| **Secundario (TVN rojo)** | `#e00710` | Alertas, "EN VIVO", destacados |
| Azul claro | `#0077c8` | Apoyo gráfico |
| Cian | `#06accb` | Acentos puntuales |
| Texto fuerte | `#2a2a2a` | Titulares y texto principal |
| Texto medio | `#6b6b6b` | Secundario |
| Texto suave | `#9b9b9b` | Metadatos, ayudas |
| Borde | `#c7c7c7` | Líneas y separadores |
| Fondo suave | `#ebebeb` | Superficies alternas |
| Éxito | `#6ded7e` | Confirmaciones |
| Riesgo/error | `#fc5432` | Errores, advertencias |

### Tipografía (las de TVN)
- **Raleway** (700/800, mayúsculas) → **titulares, kickers, etiquetas**.
- **Oxygen** (400/600) → **texto de interfaz y cuerpo**.
- Ambas son **Google Fonts** (gratis) → fidelidad de marca sin costo.

## 2. Estilo (empresarial, de medio)
- **Botones:** mayúsculas, bold, radio pequeño (~2px), primario `#005588`.
- **Cards de noticia:** kicker en Raleway mayúsculas, **titular en Raleway**, fuente
  y hora en Oxygen gris (`#9b9b9b`), estado con color semántico.
- **Densidad informativa:** tablas y listas legibles; nada de "dashboard de juguete".
- **Estados:** verificado (verde), por verificar (ámbar), atención (rojo `#e00710`).
- **Iconografía sobria**, líneas finas; evitar emojis en la UI.
- **Layout:** sidebar (Inicio · Prioridades · Bandeja · Fuentes · Verificación ·
  Borradores · Reportes) + topbar con **fecha de edición** y usuario.

## 3. Principios de UX
1. **Orientado a la tarea del periodista**, no a la del ingeniero.
2. **La IA es invisible**: "resumen asistido", "sugerencia", nunca "modelo/API".
3. **Evidencia siempre visible**: cada afirmación con su **fuente citada**.
4. **Confianza explícita**: Alto / Medio / Bajo; "sin evidencia suficiente".
5. **Human-in-the-loop**: nada se publica solo; flujo Borrador → En revisión → Aprobado.
6. **Accesible y rápida**: contraste, foco visible, atajos de teclado.

## 4. Glosario (no usar → usar)
"No usar" abajo = prohibido en la interfaz.

| ❌ Técnico | ✅ Editorial |
|---|---|
| API conectada / endpoint | Fuentes al día |
| Score IA / inferencia / modelo | Prioridad editorial |
| Webhook | Nueva alerta |
| Dataset | Fuentes y datos oficiales |
| Abstención | Sin evidencia suficiente |
| Confianza del modelo | Nivel de confianza: Alto/Medio/Bajo |

## 5. Aplicación rápida (frontend)
```css
:root {
  --tvn-primary: #005588;
  --tvn-primary-dark: #00466f;
  --tvn-red: #e00710;
  --tvn-blue: #0077c8;
  --tvn-cyan: #06accb;
  --tvn-text: #2a2a2a;
  --tvn-muted: #6b6b6b;
  --tvn-soft: #9b9b9b;
  --tvn-border: #c7c7c7;
  --tvn-bg-soft: #ebebeb;
  --tvn-ok: #6ded7e;
  --tvn-danger: #fc5432;
  --tvn-font-title: "Raleway", sans-serif;
  --tvn-font-ui: "Oxygen", sans-serif;
}
```
