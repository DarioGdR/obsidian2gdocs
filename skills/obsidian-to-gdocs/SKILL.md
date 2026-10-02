---
name: obsidian-to-gdocs
description: Converts Obsidian and Markdown documents containing Mermaid diagrams, callouts, tables, and images into self-contained HTML optimized for Google Docs pasting. Use when the user wants to export, convert, or copy Obsidian or Markdown notes to Google Docs or HTML.
---

# Obsidian to Google Docs Exporter (`obsidian2gdocs`)

Expert skill to convert Obsidian notes, vaults, and Markdown files (including Mermaid diagrams, embedded images, formatted tables, code blocks with syntax highlighting, and callouts) into a self-contained HTML document and copy it directly to the macOS clipboard ready to be pasted with full fidelity into Google Docs.

## Overview

Pasting raw Markdown directly into Google Docs fails because Google Docs does not natively interpret:
1. Mermaid diagram blocks (rendered as raw text).
2. Code blocks (rendered with black background stripes, white gaps between lines, and no syntax highlighting).
3. Obsidian image syntax (`![[image.png]]`, `![[image.png|width]]`) or relative image links (fails to resolve local files).
4. Markdown tables (pasted as plain text separated by linebreaks).
5. Obsidian callouts (`> [!important]`, `> [!tip]`, `> [!danger]`, `> [!info]`, etc.).
6. Obsidian highlights (`==text==`) and task lists (`- [ ]`, `- [x]`).

This skill uses the centralized CLI utility **`obsidian2gdocs`** located at `~/dev/repos/dariogdr/obsidian2gdocs/obsidian2gdocs.py` (available in `$PATH` as `obsidian2gdocs`).

## When to Use This Skill

Activate this skill when:
- The user asks to pass, export, convert, or copy an Obsidian note, a directory of notes, or any Markdown document to Google Docs.
- The document contains Mermaid flowcharts, sequence diagrams, or ERDs that need to be visible as images in Google Docs.
- The document contains code blocks that need clean, continuous styling without black-and-white zebra striping.
- The user asks to watch changes on a Markdown file or folder and keep a Google Docs-friendly HTML version updated.

## Available CLI Tool: `obsidian2gdocs`

```bash
obsidian2gdocs [paths...] [options]
```

### Options

* `obsidian2gdocs note.md`: Converts `note.md` and **automatically copies rich HTML to the macOS clipboard**.
* `obsidian2gdocs my-folder/`: **Multi-markdown merging:** Automatically finds all `.md` files in the folder, sorts them in natural numeric order (`00`, `01`, ..., `10`, etc.), merges them with page breaks between chapters, and copies the unified document to the clipboard.
* `obsidian2gdocs file1.md file2.md file3.md`: Merges specific files in the provided order.
* `obsidian2gdocs note.md -p` (or `--paste`): Automatically triggers `Cmd + V` in the frontmost application via AppleScript.
* `obsidian2gdocs note.md -o output.html`: Specifies a custom output HTML filename.
* `obsidian2gdocs note.md --open` (or `-b`): Generates HTML and immediately opens it in the default browser.
* `obsidian2gdocs note.md --watch` (or `-w`): Keeps running and automatically recompiles & copies whenever any Markdown file is saved.
* `obsidian2gdocs note.md --width 600`: Sets custom max width for images in pixels (default: 600px).
* `obsidian2gdocs note.md --single`: If given a directory, converts only the primary file instead of merging all.
* `obsidian2gdocs note.md --no-copy`: Skips copying to clipboard.

## How `obsidian2gdocs` Works

1. **Mermaid Pre-rendering & Caching:**
   * Scans all ````mermaid ... ```` blocks (flowchart, sequenceDiagram, erDiagram, classDiagram, timeline, etc.).
   * Renders them to high-resolution PNGs via Kroki (with fast fallback to mermaid.ink).
   * Caches diagrams by MD5 hash in `diagrams/` or `.diagrams_cache/` so subsequent builds take < 0.1s.
2. **Professional Code Blocks (Single-Cell Table Container):**
   * Eliminates the Google Docs bug where `<pre>` blocks fragment into paragraphs with white lines between lines.
   * Encapsulates code in a single-cell `<table>` with `#f6f8fa` continuous background and `#d0d7de` border.
   * Applies syntax highlighting via Pygments with inline styles (keywords, types, strings, comments) and an uppercase language banner header (e.g. `GO`, `SQL`, `KOTLIN`).
3. **Multi-Markdown & Directory Merging:**
   * Detects multiple Markdown files in a folder and applies natural sort (`00 - Index.md`, `01 - ...`, `10 - ...`).
   * Inserts `<div style="page-break-before: always;"></div>` and horizontal rules between files so Google Docs starts each chapter on a clean page and populates the native Document Outline / Tabs.
4. **Base64 Inlining:**
   * Converts all images (Mermaid PNGs, Obsidian `![[...]]`, and standard `![alt](...)`) to inline `data:image/...;base64` strings.
   * Produces a 100% self-contained HTML file that requires no external assets.
5. **Google Docs Image Ergonomics (No Table Encapsulation for Images):**
   * Embeds images inside clean `<p align="center">` paragraphs without table cell wrappers.
   * Images can be selected and resized freely with corner drag handles in Google Docs.
6. **Full Obsidian Callouts Support:**
   * Supports `[!important]` (⚡ vibrant purple), `[!tip]` / `[!hint]` (💡 green), `[!note]` (📝 blue), `[!info]` (ℹ️ blue), `[!summary]` (📌 blue), `[!success]` (✅ green), `[!question]` (❓ purple), `[!warning]` (⚠️ yellow), `[!danger]` / `[!error]` / `[!bug]` (🛑 red).
7. **Rich Typography & Tables:**
   * Formats Markdown tables with column alignments into styled HTML tables with headers and alternating row colors that Google Docs imports as native editable tables.
   * Converts Markdown links `[text](url)` to active `<a href="...">` hyperlinks.
   * Converts highlights `==text==` to soft yellow `<mark>`.
   * Converts task lists `- [ ]` and `- [x]` to checkbox symbols (`☐`, `☑`).
8. **Automatic macOS Clipboard Injection:**
   * Uses Swift (`NSPasteboard`) to place the rich HTML directly into the system clipboard.

## Standard Procedure for the Agent

1. **Identify the Source Document or Directory:**
   Determine the target Markdown file or directory.
2. **Execute `obsidian2gdocs`:**
   ```bash
   obsidian2gdocs <path-to-markdown-or-dir>
   ```
3. **Instruct the User on Pasting to Google Docs:**
   Notify the user that the document has been compiled and is already in their macOS clipboard:
   * *"El documento ya fue compilado y copiado a tu portapapeles. Solo ve a tu Google Doc y presiona **`Cmd + V`**."*
