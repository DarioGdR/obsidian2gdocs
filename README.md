# obsidian2gdocs (md2gdocs) — Obsidian & Markdown to Google Docs Exporter

Centralized CLI tool to convert Obsidian notes and complex Markdown documents (with Mermaid diagrams, highlighted code blocks, callouts, tables, local images, and links) into a self-contained HTML document optimized for direct pasting into Google Docs with full visual fidelity and free image resizing.

---

## Quickstart

From any terminal on macOS:

1. Compile and automatically COPY the formatted document to the macOS clipboard:
   ```bash
   obsidian2gdocs my-note.md
   # (or using the alias "md2gdocs")
   ```

2. Switch to Google Docs and press **Cmd + V**. Done!

---

## Supported Features

### 1. Mermaid Diagrams & Workflows
Supports any mermaid code block:
* Flowcharts (`flowchart TD`, `flowchart LR`, `graph TD`)
* Sequence diagrams (`sequenceDiagram`)
* Entity-Relationship, Class, and State diagrams (`erDiagram`, `classDiagram`, `stateDiagram`)
* Timelines (`timeline`), Git graphs (`gitGraph`), Pie charts (`pie`), Gantt (`gantt`)
* **Smart MD5 Caching:** Each diagram is rendered to a high-resolution PNG and stored in local cache (`diagrams/` or `.diagrams_cache/`). Re-rendering only occurs if diagram code changes, enabling builds in **0.1 seconds**.

### 2. Professional Code Blocks (Pygments Syntax Highlighting)
* Encapsulated in single-cell HTML tables with a continuous `#f6f8fa` background and `#d0d7de` border.
* **Eliminates the Google Docs `<pre>` bug:** No white horizontal gaps between lines and no fragmented black boxes.
* **Real Syntax Highlighting:** Powered by Pygments with support for Go, Kotlin, SQL, Python, JSON, Bash, YAML, TypeScript, and more.
* Clean uppercase header indicating the language (e.g. `GO`, `SQL`, `KOTLIN`).

### 3. Multi-File & Folder Merging
* If pointing to a folder (`obsidian2gdocs my-folder/`), naturally sorts all `.md` files in numerical order (`00`, `01`, ..., `10`, etc.) and merges them into a single continuous document.
* Automatically inserts native page breaks (`page-break-before: always`) between chapters so each file begins on a clean page in Google Docs and populates the native Document Outline / Sidebar.
* Supports passing multiple files in any custom order: `obsidian2gdocs 01.md 02.md 03.md`.

### 4. Full Obsidian Callout Palette
Converts standard Obsidian callout syntax (`> [!type] Title`) into beautifully styled visual cards with English defaults:
* `[!important]` ⚡ Important (Vibrant purple)
* `[!tip]` / `[!hint]` 💡 Tip / Hint (Green)
* `[!note]` / `[!seealso]` 📝 Note / See also (Blue)
* `[!info]` / `[!todo]` ℹ️ Info / Todo (Blue)
* `[!summary]` / `[!abstract]` / `[!tldr]` 📌 Summary / Abstract / TL;DR (Blue)
* `[!success]` / `[!check]` / `[!done]` ✅ Success / Checked / Done (Green)
* `[!question]` / `[!help]` / `[!faq]` ❓ Question / Help / FAQ (Indigo)
* `[!warning]` / `[!caution]` / `[!attention]` ⚠️ Warning / Caution / Attention (Amber)
* `[!danger]` / `[!error]` / `[!bug]` 🛑 Danger / Error / Bug (Deep red)
* `[!failure]` / `[!fail]` / `[!missing]` ❌ Failure (Red)
* `[!example]` 🧪 Example (Violet)
* `[!quote]` / `[!cite]` 💬 Quote (Grey)

### 5. Images (Obsidian Wikilinks & Markdown)
* **Wikilinks with custom width:** `![[image.png]]` or `![[image.png|450]]` (sets width to 450px).
* **Standard Markdown images:** `![alt](path/to/image.png)`.
* **Base64 Inlining:** All images and diagrams are inlined into the HTML; the resulting file is 100% self-contained and offline-ready.
* **Free Resizing in Google Docs:** Images are inserted directly without table wrappers, allowing you to click any image in Google Docs and drag the corner handles to resize freely.

### 6. Tables with Column Alignment
Interprets Markdown column alignments (`:---`, `:---:`, `---:`) to generate clean HTML tables with `#d0d7de` borders and shaded header rows that Google Docs converts into native editable tables.

### 7. Clean Temp Directory Output
* By default, intermediate HTML files are written to the macOS temporary directory (`$TMPDIR/obsidian2gdocs/`), keeping your vault and workspace clean without cluttering folders with `.html` files.

---

## CLI Options

```bash
# Compile single document (generates HTML in temp and copies to clipboard)
obsidian2gdocs my-note.md

# Compile and merge all notes in a folder in natural numeric order
obsidian2gdocs path/to/vault/

# Compile and automatically trigger Cmd + V in the frontmost window
obsidian2gdocs my-note.md -p

# Live watch mode (recompiles and copies on every save)
obsidian2gdocs my-note.md -w

# Open generated HTML in default browser
obsidian2gdocs my-note.md -b

# Custom output file path
obsidian2gdocs my-note.md -o output.html

# Custom default image width in pixels (default: 600)
obsidian2gdocs my-note.md --width 700

# Do not copy to clipboard
obsidian2gdocs my-note.md --no-copy
```

---

## Gemini CLI Integration

This repository includes a skill for Gemini CLI at `skills/obsidian-to-gdocs/SKILL.md`.

* **Skill Name:** `obsidian-to-gdocs`
* **Security Policy:** `~/.gemini/policies/obsidian-to-gdocs.toml`
