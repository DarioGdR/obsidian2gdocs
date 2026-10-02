# obsidian2gdocs — Obsidian & Markdown to Google Docs Exporter

Herramienta CLI centralizada para convertir notas de Obsidian y documentos Markdown complejos (con diagramas Mermaid, callouts, tablas, imágenes locales y enlaces) en un documento HTML autocontenido optimizado para pegarse directamente en Google Docs con fidelidad visual completa y redimensionamiento libre.

---

## 🚀 Inicio Rápido

Desde cualquier carpeta o terminal de tu Mac:

```bash
# 1. Compila y COPIA automáticamente el documento formateado al portapapeles de macOS:
obsidian2gdocs mi-nota.md

# 2. Ve a Google Docs y presiona Cmd + V. ¡Listo!
```

---

## 🌟 Características Soportadas

### 1. Diagramas Mermaid & Flujos
Soporta cualquier bloque ````mermaid ... ````:
* Flowcharts (`flowchart TD`, `flowchart LR`, `graph TD`)
* Diagramas de secuencia (`sequenceDiagram`)
* Diagramas de clases, estados, entidad-relación (`erDiagram`, `classDiagram`, `stateDiagram`)
* Líneas de tiempo (`timeline`), Git graphs (`gitGraph`), gráficos circulares (`pie`), Gantt (`gantt`)
* **Caché Inteligente por MD5:** Cada diagrama se renderiza a PNG de alta resolución y se almacena en caché local (`diagrams/` o `.diagrams_cache/`). Solo se vuelve a renderizar si modificas el código del diagrama, permitiendo compilaciones en **0.1 segundos**.

### 2. Paleta Completa de Callouts de Obsidian
Convierte sintaxis estándar de callouts `> [!tipo] Título` (incluyendo variantes plegables `+` y `-`) en tarjetas visuales estilizadas:
* `[!important]` ⚡ Importante (Púrpura vibrante)
* `[!tip]` / `[!hint]` 💡 Sugerencia / Pista (Verde)
* `[!note]` / `[!seealso]` 📝 Nota (Azul)
* `[!info]` / `[!todo]` ℹ️ Información / Por Hacer (Azul)
* `[!summary]` / `[!abstract]` / `[!tldr]` 📌 Resumen Ejecutivo (Azul)
* `[!success]` / `[!check]` / `[!done]` ✅ Éxito / Listo (Verde)
* `[!question]` / `[!help]` / `[!faq]` ❓ Preguntas Frecuentes (Índigo)
* `[!warning]` / `[!caution]` / `[!attention]` ⚠️ Advertencia / Precaución (Ámbar)
* `[!danger]` / `[!error]` / `[!bug]` 🛑 Peligro / Error / Bug (Rojo profundo)
* `[!failure]` / `[!fail]` / `[!missing]` ❌ Fallo (Rojo)
* `[!example]` 🧪 Ejemplo (Violeta)
* `[!quote]` / `[!cite]` 💬 Cita (Gris)

### 3. Imágenes de Obsidian & Markdown
* **Wikilinks con ancho personalizado:** `![[imagen.png]]` o `![[imagen.png|450]]` (fija el ancho a 450px).
* **Imágenes estándar:** `![texto](ruta/a/imagen.png)`.
* **Embebido en Base64:** Todas las imágenes y diagramas se convierten a cadenas inline en el HTML; el archivo resultante es 100% autocontenido y funciona sin conexión.
* **Redimensionamiento libre en Google Docs:** Las imágenes se insertan como párrafos directos sin celdas de tabla invisibles. Al pegarlas en Google Docs, puedes hacer clic en cualquier imagen y arrastrar los 4 tiradores de las esquinas para estirarla o achicarla libremente.

### 4. Tablas con Alineación de Columnas
Interpreta las marcas de alineación de Markdown:
* `:---` (Alineado a la izquierda)
* `:---:` (Centrado)
* `---:` (Alineado a la derecha)
Genera tablas limpias con bordes `#d0d7de` y cabeceras sombreadas que Google Docs convierte en tablas editables nativas.

### 5. Sintaxis Adicional de Obsidian & Markdown
* **Resaltado:** `==texto resaltado==` $\to$ `<mark>` amarillo suave.
* **Listas de tareas:** `- [ ] Pendiente` $\to$ `☐ Pendiente`, `- [x] Completada` $\to$ `☑ Completada`.
* **Wikilinks internos:** `[[Mi Nota|Texto a mostrar]]` $\to$ `Texto a mostrar`.
* **Tachado:** `~~texto tachado~~` $\to$ `<s>texto tachado</s>`.
* **Hipervínculos:** `[texto](url)` $\to$ enlaces clickeables con subrayado azul.
* **Bloques de código y código inline:** Fuentes monoespacio con fondo oscuro/claro estilizado.

---

## 🛠️ Comandos y Opciones de la CLI

```bash
# Compilar documento actual (genera mi-nota.html y lo copia al portapapeles)
obsidian2gdocs mi-nota.md

# Abrir el HTML en el navegador por defecto tras compilar
obsidian2gdocs mi-nota.md --open    # o flag corto: -b

# Modo observación en vivo (recompila y copia automáticamente cada vez que guardas en Obsidian)
obsidian2gdocs mi-nota.md --watch   # o flag corto: -w

# Especificar archivo de salida personalizado
obsidian2gdocs mi-nota.md -o /ruta/personalizada/salida.html

# Ajustar el ancho máximo por defecto de las imágenes (por defecto 600px)
obsidian2gdocs mi-nota.md --width 700

# No copiar al portapapeles
obsidian2gdocs mi-nota.md --no-copy

# Si ejecutas obsidian2gdocs en una carpeta sin argumentos, detecta automáticamente el .md principal
cd /mi/carpeta/con/notas
obsidian2gdocs
```

---

## 📍 Ubicación en tu Sistema

* **Script Python:** `~/dev/repos/dariogdr/obsidian2gdocs/obsidian2gdocs.py`
* **Acceso en PATH:** `~/dev/terminal/bin/obsidian2gdocs`
* **Skill de Gemini CLI:** `~/.gemini/skills/obsidian-to-gdocs/SKILL.md`
* **Política Always-Allow:** `~/.gemini/policies/obsidian-to-gdocs.toml`
