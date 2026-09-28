# obsidian2gdocs (md2gdocs) — Obsidian & Markdown to Google Docs Exporter

Herramienta CLI centralizada para convertir notas de Obsidian y documentos Markdown complejos (con diagramas Mermaid, bloques de código resaltados, callouts, tablas, imágenes locales y enlaces) en un documento HTML autocontenido optimizado para pegarse directamente en Google Docs con fidelidad visual completa y redimensionamiento libre.

---

## Inicio Rápido

Desde cualquier terminal de tu Mac:

1. Compila y COPIA automáticamente el documento formateado al portapapeles de macOS:
   obsidian2gdocs mi-nota.md
   (o también mediante el alias md2gdocs)

2. Ve a Google Docs y presiona Cmd + V. ¡Listo!

---

## Características Soportadas

### 1. Diagramas Mermaid & Flujos
Soporta cualquier bloque mermaid:
- Flowcharts (flowchart TD, flowchart LR, graph TD)
- Diagramas de secuencia (sequenceDiagram)
- Diagramas de clases, estados, entidad-relación (erDiagram, classDiagram, stateDiagram)
- Líneas de tiempo (timeline), Git graphs (gitGraph), gráficos circulares (pie), Gantt (gantt)
- Caché Inteligente por MD5: Cada diagrama se renderiza a PNG de alta resolución y se almacena en caché local (diagrams/ o .diagrams_cache/). Solo se vuelve a renderizar si modificas el código del diagrama, permitiendo compilaciones en 0.1 segundos.

### 2. Bloques de Código Profesionales (Pygments Syntax Highlighting)
- Encapsulado en celdas de tabla únicas (table tr td) con fondo continuo #f6f8fa y borde #d0d7de.
- Elimina el bug de Google Docs: Se acabaron las franjas blancas intermedias o el fondo negro entrecortado.
- Resaltado de sintaxis: Soporte para Go, Kotlin, SQL, Python, JSON, Bash, YAML, TypeScript, etc.
- Etiqueta superior con el nombre del lenguaje (GO, SQL, KOTLIN).

### 3. Fusión de Múltiples Markdown y Carpetas (Multi-File Merging)
- Si apuntas a una carpeta (obsidian2gdocs mi-carpeta/), detecta todas las notas .md, aplica ordenamiento natural numérico (00, 01, ..., 10, etc.) y las une en un único documento continuo.
- Inserta saltos de página nativos (page-break-before: always) entre capítulos para que cada sección comience en una página limpia en Google Docs y se indexe en el Document Outline.
- Soporta pasar múltiples archivos en el orden deseado: obsidian2gdocs 01.md 02.md 03.md.

### 4. Paleta Completa de Callouts de Obsidian
Convierte sintaxis estándar de callouts en tarjetas visuales estilizadas:
- [!important] Importante (Púrpura vibrante)
- [!tip] / [!hint] Sugerencia / Pista (Verde)
- [!note] / [!seealso] Nota (Azul)
- [!info] / [!todo] Información / Por Hacer (Azul)
- [!summary] / [!abstract] / [!tldr] Resumen Ejecutivo (Azul)
- [!success] / [!check] / [!done] Éxito / Listo (Verde)
- [!question] / [!help] / [!faq] Preguntas Frecuentes (Índigo)
- [!warning] / [!caution] / [!attention] Advertencia / Precaución (Ámbar)
- [!danger] / [!error] / [!bug] Peligro / Error / Bug (Rojo profundo)
- [!failure] / [!fail] / [!missing] Fallo (Rojo)
- [!example] Ejemplo (Violeta)
- [!quote] / [!cite] Cita (Gris)

### 5. Imágenes de Obsidian & Markdown
- Wikilinks con ancho personalizado: ![[imagen.png]] o ![[imagen.png|450]]
- Imágenes estándar: ![texto](ruta/a/imagen.png)
- Embebido en Base64: Todas las imágenes y diagramas se convierten a cadenas inline en el HTML; el archivo resultante es 100% autocontenido y funciona sin conexión.
- Redimensionamiento libre en Google Docs: Las imágenes se insertan como párrafos directos sin celdas de tabla invisibles. Al pegarlas en Google Docs, puedes hacer clic en cualquier imagen y arrastrar los tiradores de las esquinas para estirarla o achicarla libremente.

### 6. Tablas con Alineación de Columnas
Interpreta las marcas de alineación de Markdown generando tablas limpias con bordes #d0d7de y cabeceras sombreadas que Google Docs convierte en tablas editables nativas.

---

## Comandos y Opciones de la CLI

- obsidian2gdocs mi-nota.md: Compilar documento individual (genera .html y lo copia al portapapeles)
- obsidian2gdocs ruta/a/mi-vault/: Compilar y fusionar todas las notas de una carpeta en orden numérico natural
- obsidian2gdocs mi-nota.md -p: Compilar y pegar automáticamente en la app frontal (Cmd + V vía AppleScript)
- obsidian2gdocs mi-nota.md -w: Modo observación en vivo (recompila y copia automáticamente en cada guardado)
- obsidian2gdocs mi-nota.md -b: Abrir el HTML en el navegador por defecto tras compilar
- obsidian2gdocs mi-nota.md -o salida.html: Especificar archivo de salida personalizado
- obsidian2gdocs mi-nota.md --width 700: Ajustar el ancho máximo por defecto de las imágenes (por defecto 600px)
- obsidian2gdocs mi-nota.md --no-copy: No copiar al portapapeles

---

## Integración con Gemini CLI

Este repositorio incluye el skill para Gemini CLI en skills/obsidian-to-gdocs/SKILL.md.

- Skill: obsidian-to-gdocs
- Políticas Always-Allow: ~/.gemini/policies/obsidian-to-gdocs.toml
