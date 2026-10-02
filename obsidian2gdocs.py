#!/usr/bin/env python3
"""
obsidian2gdocs: Convert Markdown/Obsidian documents into Google Docs-optimized HTML.
Full Obsidian & standard Markdown support:
- Single file or Entire Folder consolidation (single merged Google Doc)
- Smart folder ordering: Map of Content (MOC / Index links) -> Frontmatter order -> Natural alphanumeric sort
- Native internal wikilink navigation ([[Note|Label]] -> <a href="#slug">)
- Native Google Docs page breaks between chapters (<div style="page-break-before: always;">)
- Auto-generated Table of Contents / Índice
- Mermaid diagrams (flowcharts, sequence, class, git, timelines, etc.) cached via MD5
- Complete Obsidian callout palette (including [!important], [!tip], [!danger], [!success], etc.)
- Obsidian wikilink images with custom widths (![[image.png|450]])
- Highlight syntax (==text==), strikethrough (~~text~~), task lists (- [ ] / - [x])
- Formatted tables with column alignment (:---, :---:, ---:)
- All images embedded inline as base64 (100% self-contained HTML)
- Unconstrained, freely resizable images for Google Docs (no table cell clipping)
- Automatic macOS clipboard copy (Cmd+V ready for Google Docs)
"""

import os
import re
import sys
import time
import json
import base64
import hashlib
import argparse
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^a-z0-9-]', '', text)
    return text.strip('-')

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def copy_html_to_clipboard(html_content, verbose=False):
    """
    Copies rich HTML to the macOS NSPasteboard using Swift standard library.
    Allows pasting directly into Google Docs without opening browser.
    """
    swift_code = '''
import AppKit
import Foundation

let pb = NSPasteboard.general
pb.clearContents()

let data = FileHandle.standardInput.readDataToEndOfFile()
if let html = String(data: data, encoding: .utf8) {
    pb.setString(html, forType: .html)
    pb.setString(html, forType: .string)
    print("SUCCESS")
}
'''
    try:
        proc = subprocess.Popen(
            ["swift", "-e", swift_code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(html_content.encode("utf-8"))
        if proc.returncode == 0 and "SUCCESS" in out.decode():
            if verbose:
                print("📋 Rich HTML successfully copied to macOS clipboard!", flush=True)
            return True
        else:
            if verbose:
                print(f"[warning] Clipboard copy failed: {err.decode()}", file=sys.stderr, flush=True)
    except Exception as e:
        if verbose:
            print(f"[warning] Clipboard copy error: {e}", file=sys.stderr, flush=True)
    return False

def render_mermaid(code, out_path, verbose=True):
    print(f"  [mermaid] Rendering diagram to {Path(out_path).name}...", flush=True)
    
    # Attempt 1: Kroki POST (Fast 8s timeout)
    try:
        req = urllib.request.Request(
            "https://kroki.io/mermaid/png",
            data=code.strip().encode("utf-8"),
            headers={"Content-Type": "text/plain", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
            if len(data) > 500:
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"    ✓ Saved via Kroki ({len(data):,} bytes)", flush=True)
                return True
    except Exception as e:
        if verbose:
            print(f"    Kroki failed ({e}), trying mermaid.ink...", flush=True)

    # Attempt 2: mermaid.ink GET (15s timeout)
    try:
        b64_str = base64.b64encode(code.strip().encode("utf-8")).decode("ascii")
        url = f"https://mermaid.ink/img/{b64_str}?bgColor=white"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) > 500:
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"    ✓ Saved via mermaid.ink ({len(data):,} bytes)", flush=True)
                return True
    except Exception as e:
        print(f"    [warning] Could not render diagram via web APIs: {e}", file=sys.stderr, flush=True)
        return False

def get_base64_img(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(file_path)[1].lower().replace(".", "")
        if ext == "jpg":
            ext = "jpeg"
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/{ext};base64,{b64}"
    except Exception:
        return None

def process_inline(text, slug_map=None):
    if slug_map is None:
        slug_map = {}

    # Obsidian internal wikilinks: [[Target|Label]] or [[Target]]
    def resolve_wikilink(m):
        target = m.group(1).strip()
        label = m.group(2).strip() if m.group(2) else target
        target_norm = slugify(target)

        # Look up in slug map
        if target_norm in slug_map:
            target_slug = slug_map[target_norm]
            return f'<a href="#{target_slug}" style="color: #0969da; text-decoration: underline; font-weight: 500;">{label}</a>'
        
        # Check by target raw lower
        if target.lower() in slug_map:
            target_slug = slug_map[target.lower()]
            return f'<a href="#{target_slug}" style="color: #0969da; text-decoration: underline; font-weight: 500;">{label}</a>'

        return f'<b>{label}</b>'

    text = re.sub(r'\[\[([^|\]]+)(?:\|([^\]]+))?\]\]', resolve_wikilink, text)

    # Markdown links: [text](url) -> <a href="url">text</a>
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a href="\2" target="_blank" style="color: #1a73e8; text-decoration: underline; font-weight: 500;">\1</a>',
        text
    )
    # Obsidian Highlight: ==text==
    text = re.sub(
        r'==(.*?)==',
        r'<mark style="background-color: #fff8c5; padding: 1px 4px; border-radius: 3px; color: #24292f;">\1</mark>',
        text
    )
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
    # Bold: **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic: *text* (prevent matching inside math or bullet points)
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    # Inline code: `text`
    text = re.sub(
        r'`(.*?)`',
        r'<code style="background-color: #f1f3f4; color: #b31d28; padding: 2px 5px; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Consolas, Menlo, monospace; font-size: 13px;">\1</code>',
        text
    )
    # Math arrows: $\to$ or \to
    text = text.replace(r'$\to$', '→').replace(r'\to', '→')
    return text

def render_table(tbl, slug_map=None):
    if not tbl:
        return ""
    rows = []
    alignments = []
    for line in tbl:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line[1:-1].split("|")]
            # Check if this is the separator row (:---, :---:, ---:)
            if all(set(p).issubset({"-", ":", " "}) for p in parts):
                alignments = []
                for p in parts:
                    if p.startswith(":") and p.endswith(":"):
                        alignments.append("center")
                    elif p.endswith(":"):
                        alignments.append("right")
                    else:
                        alignments.append("left")
                continue
            rows.append(parts)
    if not rows:
        return ""

    html = '<table style="border-collapse: collapse; width: 100%; margin: 20px 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 13.5px; border: 1px solid #d0d7de;">\n'
    html += '  <thead>\n    <tr style="background-color: #f6f8fa;">\n'
    for idx, c in enumerate(rows[0]):
        align = alignments[idx] if idx < len(alignments) else "left"
        html += f'      <th style="border: 1px solid #d0d7de; padding: 10px 12px; text-align: {align}; font-weight: 600; color: #24292f;">{process_inline(c, slug_map)}</th>\n'
    html += '  </tr>\n  </thead>\n  <tbody>\n'
    for r in rows[1:]:
        html += '    <tr>\n'
        for idx, c in enumerate(r):
            align = alignments[idx] if idx < len(alignments) else ("center" if idx > 0 else "left")
            bg = "#ffffff" if idx % 2 == 0 else "#fafbfc"
            html += f'      <td style="border: 1px solid #d0d7de; padding: 9px 12px; text-align: {align}; background-color: {bg}; color: #24292f;">{process_inline(c, slug_map)}</td>\n'
        html += '    </tr>\n'
    html += '  </tbody>\n</table>\n'
    return html

def parse_markdown_to_html_body(input_file, slug_map=None, max_img_width=600, section_id=None, verbose=False):
    input_file = Path(input_file).resolve()
    doc_dir = input_file.parent

    if (doc_dir / "diagrams").exists():
        cache_dir = doc_dir / "diagrams"
    else:
        cache_dir = doc_dir / ".diagrams_cache"
        cache_dir.mkdir(exist_ok=True)

    cache_meta_file = cache_dir / ".cache.json"
    cache = {}
    if cache_meta_file.exists():
        try:
            with open(cache_meta_file, "r") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()

    mermaid_pattern = re.compile(r'```mermaid\s*\n(.*?)```', re.DOTALL)
    mermaid_blocks = mermaid_pattern.findall(content)

    diagram_pngs = []
    existing_pngs = sorted([p for p in cache_dir.glob("*.png") if not p.name.startswith(".")])

    for idx, code in enumerate(mermaid_blocks):
        code_clean = code.strip()
        code_hash = hashlib.md5(code_clean.encode("utf-8")).hexdigest()
        matching_png = None
        if idx < len(existing_pngs):
            matching_png = existing_pngs[idx]

        diag_name = f"mermaid_{input_file.stem}_{idx+1}_{code_hash[:8]}"
        out_png = cache_dir / f"{diag_name}.png"

        if matching_png and matching_png.exists() and matching_png.stat().st_size > 1000 and len(mermaid_blocks) == len(existing_pngs):
            diagram_pngs.append(str(matching_png))
        elif out_png.exists() and out_png.stat().st_size > 1000 and cache.get(diag_name) == code_hash:
            diagram_pngs.append(str(out_png))
        else:
            if render_mermaid(code_clean, str(out_png), verbose):
                cache[diag_name] = code_hash
                diagram_pngs.append(str(out_png))
            elif matching_png and matching_png.exists():
                diagram_pngs.append(str(matching_png))
            else:
                diagram_pngs.append(None)

    with open(cache_meta_file, "w") as f:
        json.dump(cache, f, indent=2)

    html_lines = []
    frontmatter_count = 0
    in_mermaid = False
    mermaid_idx = 0
    in_code = False
    code_lines = []
    table_lines = []
    doc_title = input_file.stem.replace("-", " ").replace("_", " ").title()
    first_h1_set = False

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip() == "---":
            frontmatter_count += 1
            if frontmatter_count <= 2:
                i += 1
                continue

        if frontmatter_count == 1:
            if line.strip().startswith("title:"):
                doc_title = line.split(":", 1)[1].strip().strip('"').strip("'")
            i += 1
            continue

        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines.append(line)
            i += 1
            continue
        else:
            if table_lines:
                html_lines.append(render_table(table_lines, slug_map))
                table_lines = []

        if line.strip().startswith("```mermaid"):
            in_mermaid = True
            i += 1
            continue
        if in_mermaid:
            if line.strip().startswith("```"):
                in_mermaid = False
                if mermaid_idx < len(diagram_pngs):
                    img_path = diagram_pngs[mermaid_idx]
                    mermaid_idx += 1
                    if img_path:
                        b64 = get_base64_img(img_path)
                        if b64:
                            html_lines.append(
                                f'<p align="center" style="text-align: center; margin: 24px 0;">\n'
                                f'  <img src="{b64}" width="{max_img_width}" style="max-width: 100%; height: auto; border: 1px solid #d0d7de; border-radius: 6px;" />\n'
                                f'</p>\n'
                            )
            i += 1
            continue

        if line.strip().startswith("```"):
            if in_code:
                in_code = False
                code_text = "".join(code_lines)
                html_lines.append(
                    f'<pre style="background: #24292f; color: #f0f6fc; padding: 12px 16px; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Consolas, Menlo, monospace; font-size: 13px; overflow-x: auto; line-height: 1.45;">{code_text}</pre>\n'
                )
                code_lines = []
            else:
                in_code = True
                code_lines = []
            i += 1
            continue

        if in_code:
            code_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "\n")
            i += 1
            continue

        # Complete Obsidian Callouts
        if line.strip().startswith("> [!"):
            m = re.match(r'> \[!([a-zA-Z0-9_-]+)\][+-]?\s*(.*)', line.strip())
            if m:
                c_type = m.group(1).lower()
                c_title = m.group(2)
                c_body = []
                i += 1
                while i < len(lines) and lines[i].strip().startswith(">"):
                    c_body.append(lines[i].strip()[1:].strip())
                    i += 1

                callout_palette = {
                    "note": ("#ddf4ff", "#0969da", "#0969da", "📝 Nota"),
                    "seealso": ("#ddf4ff", "#0969da", "#0969da", "📝 Véase también"),
                    "summary": ("#ddf4ff", "#0969da", "#0969da", "📌 Resumen"),
                    "abstract": ("#ddf4ff", "#0969da", "#0969da", "📌 Resumen"),
                    "tldr": ("#ddf4ff", "#0969da", "#0969da", "📌 TL;DR"),
                    "info": ("#ddf4ff", "#0969da", "#0969da", "ℹ️ Información"),
                    "todo": ("#ddf4ff", "#0969da", "#0969da", "☑️ Por Hacer"),
                    "tip": ("#dafbe1", "#1a7f37", "#1a7f37", "💡 Sugerencia"),
                    "hint": ("#dafbe1", "#1a7f37", "#1a7f37", "💡 Pista"),
                    "important": ("#fbefff", "#8250df", "#8250df", "⚡ Importante"),
                    "success": ("#dafbe1", "#1a7f37", "#1a7f37", "✅ Éxito"),
                    "check": ("#dafbe1", "#1a7f37", "#1a7f37", "✅ Verificado"),
                    "done": ("#dafbe1", "#1a7f37", "#1a7f37", "✅ Listo"),
                    "question": ("#fbefff", "#8250df", "#8250df", "❓ Pregunta"),
                    "help": ("#fbefff", "#8250df", "#8250df", "❓ Ayuda"),
                    "faq": ("#fbefff", "#8250df", "#8250df", "❓ Preguntas Frecuentes"),
                    "warning": ("#fff8c5", "#9a6700", "#9a6700", "⚠️ Advertencia"),
                    "caution": ("#fff8c5", "#9a6700", "#9a6700", "⚠️ Precaución"),
                    "attention": ("#fff8c5", "#9a6700", "#9a6700", "⚠️ Atención"),
                    "failure": ("#ffebe9", "#cf222e", "#cf222e", "❌ Fallo"),
                    "fail": ("#ffebe9", "#cf222e", "#cf222e", "❌ Fallo"),
                    "missing": ("#ffebe9", "#cf222e", "#cf222e", "❌ Faltante"),
                    "danger": ("#ffebe9", "#cf222e", "#cf222e", "🛑 Peligro"),
                    "error": ("#ffebe9", "#cf222e", "#cf222e", "🛑 Error"),
                    "bug": ("#ffebe9", "#cf222e", "#cf222e", "🐛 Bug"),
                    "example": ("#f6f8fa", "#8250df", "#8250df", "🧪 Ejemplo"),
                    "quote": ("#f6f8fa", "#57606a", "#57606a", "💬 Cita"),
                    "cite": ("#f6f8fa", "#57606a", "#57606a", "💬 Cita"),
                }
                bg, border, title_col, def_title = callout_palette.get(
                    c_type, ("#f6f8fa", "#57606a", "#24292f", c_type.capitalize())
                )
                title_disp = c_title if c_title else def_title
                body_text = "<br/>".join([process_inline(b, slug_map) for b in c_body if b])

                html_lines.append(
                    f'<div style="background-color: {bg}; border-left: 4px solid {border}; border-radius: 4px; padding: 12px 16px; margin: 18px 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">'
                    f'<div style="font-weight: 600; color: {title_col}; margin-bottom: 6px; font-size: 14.5px;">{process_inline(title_disp, slug_map)}</div>'
                    f'<div style="color: #24292f; font-size: 13.5px; line-height: 1.6;">{body_text}</div>'
                    f'</div>\n'
                )
                continue

        # Obsidian Wikilink Images
        wikilink_img = re.search(r'!\[\[(.*?)\]\]', line)
        if wikilink_img:
            raw_target = wikilink_img.group(1).strip()
            target_parts = raw_target.split("|")
            target = target_parts[0].strip()
            custom_w = max_img_width
            if len(target_parts) > 1 and target_parts[1].strip().isdigit():
                custom_w = int(target_parts[1].strip())

            resolved_img = doc_dir / target
            if not resolved_img.exists():
                if (doc_dir / "diagrams" / target).exists():
                    resolved_img = doc_dir / "diagrams" / target

            b64 = get_base64_img(str(resolved_img))
            if b64:
                html_lines.append(
                    f'<p align="center" style="text-align: center; margin: 24px 0;">\n'
                    f'  <img src="{b64}" width="{custom_w}" style="max-width: 100%; height: auto; border: 1px solid #d0d7de; border-radius: 6px;" />\n'
                    f'  <br/><span style="font-size: 12px; color: #57606a; font-family: sans-serif;"><i>{target}</i></span>\n'
                    f'</p>\n'
                )
            i += 1
            continue

        # Standard Markdown Images
        md_img = re.search(r'!\[(.*?)\]\((.*?)\)', line)
        if md_img and not line.strip().startswith("```"):
            alt_text = md_img.group(1)
            img_src = md_img.group(2)
            resolved_img = doc_dir / img_src
            b64 = get_base64_img(str(resolved_img))
            if b64:
                html_lines.append(
                    f'<p align="center" style="text-align: center; margin: 24px 0;">\n'
                    f'  <img src="{b64}" width="{max_img_width}" style="max-width: 100%; height: auto; border: 1px solid #d0d7de; border-radius: 6px;" />\n'
                    f'  <br/><span style="font-size: 12px; color: #57606a; font-family: sans-serif;"><i>{alt_text}</i></span>\n'
                    f'</p>\n'
                )
            i += 1
            continue

        # Task Lists
        task_match = re.match(r'^\s*[-*]\s+\[([ xX])\]\s*(.*)', line)
        if task_match:
            is_checked = task_match.group(1).lower() == "x"
            task_text = process_inline(task_match.group(2), slug_map)
            check_icon = "☑" if is_checked else "☐"
            icon_style = "color: #1a7f37; font-weight: bold;" if is_checked else "color: #57606a;"
            text_rendered = f"<s>{task_text}</s>" if is_checked else task_text
            html_lines.append(
                f'<div style="margin-bottom: 6px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.6; color: #24292f;">'
                f'<span style="{icon_style} margin-right: 8px; font-size: 15px;">{check_icon}</span>{text_rendered}</div>\n'
            )
            i += 1
            continue

        # Headings with internal anchor IDs
        if line.startswith("# "):
            h_text = line[2:].strip()
            h_slug = section_id if (section_id and not first_h1_set) else slugify(h_text)
            first_h1_set = True
            doc_title = h_text
            html_lines.append(f'<h1 id="{h_slug}" style="color: #1f2328; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 26px; font-weight: 600; border-bottom: 1px solid #d0d7de; padding-bottom: 8px; margin-top: 24px; margin-bottom: 16px;">{process_inline(h_text, slug_map)}</h1>\n')
        elif line.startswith("## "):
            h_text = line[3:].strip()
            h_slug = slugify(h_text)
            html_lines.append(f'<h2 id="{h_slug}" style="color: #0969da; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 20px; font-weight: 600; border-bottom: 1px solid #d0d7de; padding-bottom: 6px; margin-top: 28px; margin-bottom: 14px;">{process_inline(h_text, slug_map)}</h2>\n')
        elif line.startswith("### "):
            h_text = line[4:].strip()
            h_slug = slugify(h_text)
            html_lines.append(f'<h3 id="{h_slug}" style="color: #1f2328; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 16px; font-weight: 600; margin-top: 20px; margin-bottom: 8px;">{process_inline(h_text, slug_map)}</h3>\n')
        elif line.startswith("#### "):
            html_lines.append(f'<h4 style="color: #57606a; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 13.5px; font-weight: 600; margin-top: 14px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">{process_inline(line[5:].strip(), slug_map)}</h4>\n')
        elif line.strip() == "---":
            html_lines.append('<hr style="border: 0; border-top: 1px solid #d0d7de; margin: 24px 0;" />\n')
        elif line.strip().startswith("* ") or line.strip().startswith("- "):
            html_lines.append(f'<li style="margin-bottom: 5px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.6; color: #24292f;">{process_inline(line.strip()[2:], slug_map)}</li>\n')
        elif re.match(r'^\d+\.\s', line.strip()):
            content_item = process_inline(re.sub(r'^\d+\.\s', '', line.strip()), slug_map)
            html_lines.append(f'<li style="margin-bottom: 5px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.6; color: #24292f;">{content_item}</li>\n')
        elif line.strip():
            html_lines.append(f'<p style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.65; color: #24292f; margin-bottom: 12px;">{process_inline(line.strip(), slug_map)}</p>\n')

        i += 1

    if table_lines:
        html_lines.append(render_table(table_lines, slug_map))

    return "".join(html_lines), doc_title

def convert_markdown(input_path, output_path=None, max_img_width=600, do_copy=True, verbose=False):
    input_file = Path(input_path).resolve()
    if not input_file.exists():
        print(f"[error] File not found: {input_path}", file=sys.stderr, flush=True)
        return None

    doc_dir = input_file.parent
    if output_path:
        out_file = Path(output_path).resolve()
    else:
        out_file = doc_dir / f"{input_file.stem}.html"

    # Single file slug map
    slug_map = {
        slugify(input_file.stem): slugify(input_file.stem),
        input_file.stem.lower(): slugify(input_file.stem)
    }

    body_html, doc_title = parse_markdown_to_html_body(input_file, slug_map, max_img_width, verbose=verbose)

    full_html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{doc_title}</title>
<style>
body {{
    max-width: 820px;
    margin: 40px auto;
    padding: 0 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #24292f;
    line-height: 1.6;
    background-color: #ffffff;
}}
ul, ol {{
    padding-left: 24px;
    margin-bottom: 12px;
}}
table {{
    page-break-inside: avoid;
}}
img {{
    page-break-inside: avoid;
}}
</style>
</head>
<body>
{body_html}
</body>
</html>'''

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[{time.strftime('%H:%M:%S')}] ✓ Generated: {out_file} ({len(full_html):,} bytes)", flush=True)

    if do_copy:
        copy_html_to_clipboard(full_html, verbose=True)

    return out_file

def discover_folder_order(folder_path):
    """
    Intelligently orders markdown files in a folder:
    1. Check for Index/README file with [[links]] (Obsidian Map of Content pattern)
    2. Check YAML frontmatter order/orden/seq
    3. Fallback to natural alphanumeric sort
    """
    folder = Path(folder_path).resolve()
    all_md_files = [f for f in folder.glob("*.md") if not f.name.startswith(".")]

    if len(all_md_files) <= 1:
        return all_md_files

    # 1. Look for potential index / MOC file
    index_candidates = ["readme.md", "index.md", "toc.md", f"{folder.name.lower()}.md"]
    index_file = None
    for cand in index_candidates:
        match = next((f for f in all_md_files if f.name.lower() == cand), None)
        if match:
            index_file = match
            break

    ordered_files = []
    if index_file:
        with open(index_file, "r", encoding="utf-8") as f:
            idx_content = f.read()

        # Find all [[wikilinks]] in index file
        links = re.findall(r'\[\[([^|\]]+)(?:\|[^\]]+)?\]\]', idx_content)
        # Also standard links: [text](file.md)
        std_links = re.findall(r'\[[^\]]+\]\(([^)]+\.md)\)', idx_content)
        links.extend([Path(l).stem for l in std_links])

        ordered_files.append(index_file)
        for link in links:
            link_stem = Path(link).stem.lower()
            matched_file = next(
                (f for f in all_md_files if f.stem.lower() == link_stem or slugify(f.stem) == slugify(link_stem)),
                None
            )
            if matched_file and matched_file not in ordered_files:
                ordered_files.append(matched_file)

    # 2. Check frontmatter order for any files not yet ordered
    unordered_files = [f for f in all_md_files if f not in ordered_files]
    with_order = []
    without_order = []

    for f in unordered_files:
        try:
            with open(f, "r", encoding="utf-8") as file_obj:
                first_lines = "".join([file_obj.readline() for _ in range(25)])
            order_match = re.search(r'^(?:order|orden|seq|weight):\s*(\d+)', first_lines, re.MULTILINE | re.IGNORECASE)
            if order_match:
                with_order.append((int(order_match.group(1)), f))
            else:
                without_order.append(f)
        except Exception:
            without_order.append(f)

    with_order.sort(key=lambda x: x[0])
    ordered_files.extend([item[1] for item in with_order])

    # 3. Fallback natural sort for remaining files
    without_order.sort(key=lambda f: natural_sort_key(f.name))
    ordered_files.extend(without_order)

    return ordered_files

def convert_folder(folder_path, output_path=None, max_img_width=600, do_copy=True, verbose=False):
    folder = Path(folder_path).resolve()
    ordered_files = discover_folder_order(folder)

    if not ordered_files:
        print(f"[error] No .md files found in {folder}", file=sys.stderr, flush=True)
        return None

    if len(ordered_files) == 1:
        return convert_markdown(ordered_files[0], output_path, max_img_width, do_copy, verbose)

    doc_title = folder.name.replace("-", " ").replace("_", " ").title()
    if output_path:
        out_file = Path(output_path).resolve()
    else:
        out_file = folder / f"{folder.name}-consolidado.html"

    print(f"📦 Consolidating {len(ordered_files)} notes from '{folder.name}':", flush=True)
    for idx, f in enumerate(ordered_files, 1):
        print(f"   {idx}. {f.name}", flush=True)

    # Build cross-document slug map for wikilink resolution
    slug_map = {}
    file_metadata = []

    for f in ordered_files:
        # Extract title from YAML or first H1
        f_title = f.stem.replace("-", " ").replace("_", " ").title()
        try:
            with open(f, "r", encoding="utf-8") as fo:
                content = fo.read()
            m_title = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
            if m_title:
                f_title = m_title.group(1).strip()
            else:
                m_h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if m_h1:
                    f_title = m_h1.group(1).strip()
        except Exception:
            pass

        f_slug = slugify(f_title) or slugify(f.stem)
        slug_map[slugify(f.stem)] = f_slug
        slug_map[f.stem.lower()] = f_slug
        slug_map[slugify(f_title)] = f_slug
        slug_map[f_title.lower()] = f_slug

        file_metadata.append({
            "path": f,
            "title": f_title,
            "slug": f_slug
        })

    # Render each section
    sections_html = []
    for meta in file_metadata:
        f = meta["path"]
        f_slug = meta["slug"]
        section_html, _ = parse_markdown_to_html_body(
            f, slug_map=slug_map, max_img_width=max_img_width, section_id=f_slug, verbose=verbose
        )
        sections_html.append({
            "slug": f_slug,
            "title": meta["title"],
            "html": section_html
        })

    # Generate Table of Contents (Índice de Navegación)
    toc_items = []
    for s in sections_html:
        toc_items.append(
            f'<li style="margin-bottom: 6px; font-size: 14.5px;">'
            f'<a href="#{s["slug"]}" style="color: #0969da; text-decoration: underline; font-weight: 500;">{s["title"]}</a>'
            f'</li>'
        )

    toc_html = f'''<div style="background-color: #f6f8fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 20px 24px; margin-bottom: 36px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
  <div style="font-weight: 600; font-size: 16px; color: #1f2328; margin-bottom: 12px;">📑 Índice del Documento</div>
  <ol style="margin: 0; padding-left: 20px;">
    {"".join(toc_items)}
  </ol>
</div>\n'''

    # Combine sections with native Google Docs page breaks
    combined_body = [toc_html]
    for idx, s in enumerate(sections_html):
        if idx > 0:
            # Native Google Docs page break
            combined_body.append('<div style="page-break-before: always; margin-top: 40px;"><hr style="border: 0; border-top: 1px dashed #d0d7de; margin: 30px 0;" /></div>\n')
        combined_body.append(s["html"])

    full_html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{doc_title}</title>
<style>
body {{
    max-width: 820px;
    margin: 40px auto;
    padding: 0 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #24292f;
    line-height: 1.6;
    background-color: #ffffff;
}}
ul, ol {{
    padding-left: 24px;
    margin-bottom: 12px;
}}
table {{
    page-break-inside: avoid;
}}
img {{
    page-break-inside: avoid;
}}
</style>
</head>
<body>
{"".join(combined_body)}
</body>
</html>'''

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[{time.strftime('%H:%M:%S')}] ✓ Consolidated Document Generated: {out_file} ({len(full_html):,} bytes)", flush=True)

    if do_copy:
        copy_html_to_clipboard(full_html, verbose=True)

    return out_file

def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown/Obsidian files or entire folders into Google Docs-optimized HTML with embedded diagrams."
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to markdown file or directory (default: current dir)")
    parser.add_argument("-o", "--output", help="Custom output HTML path")
    parser.add_argument("-c", "--copy", action="store_true", default=True, help="Automatically copy rich HTML to macOS clipboard (default: True)")
    parser.add_argument("--no-copy", dest="copy", action="store_false", help="Do not copy to clipboard")
    parser.add_argument("-b", "--open", action="store_true", help="Open generated HTML in browser")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch file or folder for changes and auto-rebuild")
    parser.add_argument("--width", type=int, default=600, help="Default max width for images in pixels (default: 600)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    target_path = Path(args.path).resolve()
    if target_path.is_dir():
        out_file = convert_folder(target_path, args.output, args.width, do_copy=args.copy, verbose=args.verbose)
    else:
        out_file = convert_markdown(target_path, args.output, args.width, do_copy=args.copy, verbose=args.verbose)

    if not out_file:
        sys.exit(1)

    if args.copy:
        print("💡 Document copied to clipboard! Just press Cmd+V in Google Docs.", flush=True)

    if args.open:
        subprocess.run(["open", str(out_file)])

    if args.watch:
        print(f"👀 Watching {target_path.name} for changes... (Press Ctrl+C to stop)", flush=True)
        def get_mtime():
            if target_path.is_dir():
                return max([f.stat().st_mtime for f in target_path.glob("*.md")] or [0])
            return target_path.stat().st_mtime

        last_mtime = get_mtime()
        while True:
            time.sleep(1)
            try:
                curr_mtime = get_mtime()
                if curr_mtime != last_mtime:
                    last_mtime = curr_mtime
                    if target_path.is_dir():
                        convert_folder(target_path, args.output, args.width, do_copy=args.copy, verbose=args.verbose)
                    else:
                        convert_markdown(target_path, args.output, args.width, do_copy=args.copy, verbose=args.verbose)
                    if args.copy:
                        print("💡 Updated & copied to clipboard! Press Cmd+V in Google Docs.", flush=True)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[error] {e}", file=sys.stderr, flush=True)

if __name__ == "__main__":
    main()
