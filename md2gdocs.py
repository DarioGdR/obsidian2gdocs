#!/usr/bin/env python3
"""
md2gdocs / obsidian2gdocs: Convert Markdown/Obsidian documents into Google Docs-optimized HTML.
Full Obsidian & standard Markdown support:
- Mermaid diagrams (flowcharts, sequence, class, git, timelines, etc.) cached via MD5
- Complete Obsidian callout palette (including [!important], [!tip], [!danger], [!success], etc.)
- Multi-markdown & directory merging with natural numerical sorting (00, 01, ..., 10, etc.)
- Clean, continuous code blocks with Pygments syntax highlighting (no white gaps or black boxes)
- Obsidian wikilink images with custom widths (![[image.png|450]])
- Internal wikilinks ([[Note|Label]])
- Highlight syntax (==text==)
- Strikethrough (~~text~~)
- Task lists (- [ ] / - [x])
- Formatted tables with column alignment (:---, :---:, ---:)
- All images embedded inline as base64 (100% self-contained HTML)
- Unconstrained, freely resizable images for Google Docs (no table cell clipping)
- Automatic macOS clipboard copy (Cmd+V ready for Google Docs)
- Optional automatic paste (--paste / -p) via macOS System Events
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
import urllib.request
from pathlib import Path

# Optional Pygments integration for professional syntax highlighting
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.formatters import HtmlFormatter
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


def natural_sort_key(p):
    """Sorts file paths containing numbers naturally (e.g., 00, 01, 02, 10, 11)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', p.name)]


def copy_html_to_clipboard(html_content, verbose=False):
    """
    Copies rich HTML to the macOS NSPasteboard using Swift standard library.
    Allows pasting directly into Google Docs without opening browser.
    """
    swift_code = """
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
"""
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


def paste_to_frontmost_app(verbose=False):
    """
    Triggers Cmd+V in the frontmost application (e.g., Google Docs in Chrome/Safari)
    using macOS System Events via AppleScript.
    """
    apple_script = """
    tell application "System Events"
        delay 0.3
        keystroke "v" using command down
    end tell
    """
    try:
        proc = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
        if proc.returncode == 0:
            if verbose:
                print("🚀 Successfully sent Cmd+V paste keystroke to frontmost window!", flush=True)
            return True
        else:
            if verbose:
                print(f"[warning] Auto-paste failed: {proc.stderr}", file=sys.stderr, flush=True)
    except Exception as e:
        if verbose:
            print(f"[warning] Auto-paste error: {e}", file=sys.stderr, flush=True)
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


def process_inline(text):
    # Obsidian internal wikilinks: [[Note|Label]] or [[Note]]
    text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'<b>\2</b>', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'<b>\1</b>', text)

    # Markdown links: [text](url) -> <a href="\2">text</a>
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


def render_code_block(code_str, lang=""):
    """
    Renders code blocks inside a single-cell HTML <table> with a clean light background (#f6f8fa).
    This completely eliminates Google Docs' bug where <pre> blocks get split into paragraphs
    with ugly white lines/spaces between lines and black boxes.
    """
    lang_clean = (lang or "").strip().lower()
    lang_aliases = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "golang": "go",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "yml": "yaml",
        "kt": "kotlin",
        "kts": "kotlin",
        "rb": "ruby",
        "cs": "csharp",
    }
    canonical_lang = lang_aliases.get(lang_clean, lang_clean)

    highlighted = None
    if HAS_PYGMENTS and code_str.strip():
        try:
            if canonical_lang:
                lexer = get_lexer_by_name(canonical_lang, stripall=False)
            else:
                lexer = guess_lexer(code_str)
            formatter = HtmlFormatter(nowrap=True, noclasses=True, style="friendly")
            raw_hl = highlight(code_str, lexer, formatter)
            # Pygments wraps whitespace tokens in spans; clean them out so regular spaces remain untouched
            highlighted = re.sub(r'<span style="color: #BBB">(\s+)</span>', r'\1', raw_hl)
        except Exception:
            pass

    if not highlighted:
        # Safe fallback escaping
        escaped = code_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        highlighted = escaped

    header_html = ""
    if lang_clean:
        header_html = (
            f'<thead><tr><th style="padding: 6px 14px; background-color: #eaeef2; '
            f'border-bottom: 1px solid #d0d7de; text-align: left; font-family: -apple-system, BlinkMacSystemFont, sans-serif; '
            f'font-size: 11px; font-weight: 600; color: #57606a; text-transform: uppercase; '
            f'letter-spacing: 0.5px; border-top-left-radius: 5px; border-top-right-radius: 5px;">'
            f'{lang_clean.upper()}</th></tr></thead>'
        )

    return (
        f'<table style="border-collapse: separate; border-spacing: 0; width: 100%; margin: 18px 0; '
        f'background-color: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;">\n'
        f'{header_html}\n'
        f'<tbody><tr><td style="padding: 12px 16px; background-color: #f6f8fa; '
        f'font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \'Courier New\', monospace; '
        f'font-size: 12px; line-height: 1.5; color: #1f2328; white-space: pre-wrap; word-break: break-word; '
        f'border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;">'
        f'<div style="font-family: inherit; font-size: inherit; line-height: inherit; white-space: pre-wrap; word-break: break-word;">'
        f'{highlighted}'
        f'</div>'
        f'</td></tr></tbody>\n'
        f'</table>\n'
    )


def render_table(tbl):
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
        html += f'      <th style="border: 1px solid #d0d7de; padding: 10px 12px; text-align: {align}; font-weight: 600; color: #24292f;">{process_inline(c)}</th>\n'
    html += '  </tr>\n  </thead>\n  <tbody>\n'
    for r in rows[1:]:
        html += '    <tr>\n'
        for idx, c in enumerate(r):
            align = alignments[idx] if idx < len(alignments) else ("center" if idx > 0 else "left")
            bg = "#ffffff" if idx % 2 == 0 else "#fafbfc"
            html += f'      <td style="border: 1px solid #d0d7de; padding: 9px 12px; text-align: {align}; background-color: {bg}; color: #24292f;">{process_inline(c)}</td>\n'
        html += '    </tr>\n'
    html += '  </tbody>\n</table>\n'
    return html


def convert_markdown_source(content, doc_dir, output_file, max_img_width=600, do_copy=True, verbose=False, auto_paste=False, doc_title=None):
    """Core compiler that transforms Markdown text into rich, self-contained HTML."""
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

        diag_name = f"mermaid_{idx+1}_{code_hash[:8]}"
        out_png = cache_dir / f"{diag_name}.png"

        if matching_png and matching_png.exists() and matching_png.stat().st_size > 1000:
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
    code_lang = ""
    code_lines = []
    table_lines = []

    if not doc_title:
        doc_title = output_file.stem.replace("-", " ").replace("_", " ").title()

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
                html_lines.append(render_table(table_lines))
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
                html_lines.append(render_code_block(code_text, code_lang))
                code_lines = []
                code_lang = ""
            else:
                in_code = True
                code_lang = line.strip()[3:].strip()
                code_lines = []
            i += 1
            continue

        if in_code:
            code_lines.append(line + "\n")
            i += 1
            continue

        # Complete Obsidian Callouts: > [!type] or > [!type]+ or > [!type]-
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

                # Comprehensive Obsidian Callout Palette
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
                body_text = "<br/>".join([process_inline(b) for b in c_body if b])

                html_lines.append(
                    f'<div style="background-color: {bg}; border-left: 4px solid {border}; border-radius: 4px; padding: 12px 16px; margin: 18px 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">'
                    f'<div style="font-weight: 600; color: {title_col}; margin-bottom: 6px; font-size: 14.5px;">{process_inline(title_disp)}</div>'
                    f'<div style="color: #24292f; font-size: 13.5px; line-height: 1.6;">{body_text}</div>'
                    f'</div>\n'
                )
                continue

        # Obsidian Wikilink Images: ![[image.png]] or ![[image.png|500]]
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
                elif (doc_dir / "images" / target).exists():
                    resolved_img = doc_dir / "images" / target

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

        # Standard Markdown Images: ![alt](path)
        md_img = re.search(r'!\[(.*?)\]\((.*?)\)', line)
        if md_img and not line.strip().startswith("```"):
            alt_text = md_img.group(1)
            img_src = md_img.group(2)
            resolved_img = doc_dir / img_src
            if not resolved_img.exists() and (doc_dir / "images" / img_src).exists():
                resolved_img = doc_dir / "images" / img_src
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

        # Task Lists: - [ ] or - [x]
        task_match = re.match(r'^\s*[-*]\s+\[([ xX])\]\s*(.*)', line)
        if task_match:
            is_checked = task_match.group(1).lower() == "x"
            task_text = process_inline(task_match.group(2))
            check_icon = "☑" if is_checked else "☐"
            icon_style = "color: #1a7f37; font-weight: bold;" if is_checked else "color: #57606a;"
            text_rendered = f"<s>{task_text}</s>" if is_checked else task_text
            html_lines.append(
                f'<div style="margin-bottom: 6px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.6; color: #24292f;">'
                f'<span style="{icon_style} margin-right: 8px; font-size: 15px;">{check_icon}</span>{text_rendered}</div>\n'
            )
            i += 1
            continue

        # HTML-level page breaks passed via markdown
        if '<div style="page-break-before: always' in line or "<hr" in line:
            html_lines.append(line + "\n")
            i += 1
            continue

        # Headings
        if line.startswith("# "):
            html_lines.append(f'<h1 style="color: #1f2328; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 26px; font-weight: 600; border-bottom: 1px solid #d0d7de; padding-bottom: 8px; margin-top: 24px; margin-bottom: 16px;">{process_inline(line[2:].strip())}</h1>\n')
        elif line.startswith("## "):
            html_lines.append(f'<h2 style="color: #0969da; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 20px; font-weight: 600; border-bottom: 1px solid #d0d7de; padding-bottom: 6px; margin-top: 28px; margin-bottom: 14px;">{process_inline(line[3:].strip())}</h2>\n')
        elif line.startswith("### "):
            html_lines.append(f'<h3 style="color: #1f2328; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 16px; font-weight: 600; margin-top: 20px; margin-bottom: 8px;">{process_inline(line[4:].strip())}</h3>\n')
        elif line.startswith("#### "):
            html_lines.append(f'<h4 style="color: #57606a; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 13.5px; font-weight: 600; margin-top: 14px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">{process_inline(line[5:].strip())}</h4>\n')
        elif line.strip() == "---":
            html_lines.append('<hr style="border: 0; border-top: 1px solid #d0d7de; margin: 24px 0;" />\n')
        elif line.strip().startswith("* ") or line.strip().startswith("- "):
            html_lines.append(f'<li style="margin-bottom: 5px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.6; color: #24292f;">{process_inline(line.strip()[2:])}</li>\n')
        elif re.match(r'^\d+\.\s', line.strip()):
            content_item = process_inline(re.sub(r'^\d+\.\s', '', line.strip()))
            html_lines.append(f'<li style="margin-bottom: 5px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.6; color: #24292f;">{content_item}</li>\n')
        elif line.strip():
            html_lines.append(f'<p style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.65; color: #24292f; margin-bottom: 12px;">{process_inline(line.strip())}</p>\n')

        i += 1

    if table_lines:
        html_lines.append(render_table(table_lines))

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
{"".join(html_lines)}
</body>
</html>'''

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[{time.strftime('%H:%M:%S')}] ✓ Generated: {output_file} ({len(full_html):,} bytes)", flush=True)

    if do_copy:
        copy_html_to_clipboard(full_html, verbose=True)

    if auto_paste:
        paste_to_frontmost_app(verbose=True)

    return output_file


def convert_markdown(input_path_or_paths, output_path=None, max_img_width=600, do_copy=True, verbose=False, auto_paste=False, single_mode=False):
    """
    Main conversion handler. Accepts a single file, a directory, or multiple files.
    If multiple files or a directory with multiple .md files is passed, it merges them in natural order.
    """
    if isinstance(input_path_or_paths, (list, tuple)):
        paths = [Path(p).resolve() for p in input_path_or_paths]
    else:
        paths = [Path(input_path_or_paths).resolve()]

    # If single path and is directory, find markdown files inside
    if len(paths) == 1 and paths[0].is_dir():
        dir_path = paths[0]
        md_candidates = [
            p for p in dir_path.glob("*.md")
            if not p.name.startswith(".") and p.suffix == ".md"
        ]
        non_readme = [p for p in md_candidates if p.name.lower() != "readme.md"]
        
        if not md_candidates:
            print(f"[error] No .md files found in {dir_path}", file=sys.stderr, flush=True)
            return None

        if single_mode:
            target_files = [non_readme[0] if non_readme else md_candidates[0]]
        else:
            # Multi-file directory mode: naturally sort all markdown files
            target_files = sorted(non_readme if non_readme else md_candidates, key=natural_sort_key)
            if len(target_files) > 1:
                print(f"📂 Merging {len(target_files)} Markdown files from '{dir_path.name}' in natural order...", flush=True)
    else:
        target_files = [p for p in paths if p.exists() and p.is_file()]

    if not target_files:
        print("[error] No valid markdown files provided.", file=sys.stderr, flush=True)
        return None

    doc_dir = target_files[0].parent

    if output_path:
        out_file = Path(output_path).resolve()
    else:
        if len(target_files) > 1:
            out_file = doc_dir / f"{doc_dir.name}_compilado.html"
        else:
            out_file = doc_dir / f"{target_files[0].stem}.html"

    # Merge content
    merged_sections = []
    for idx, f in enumerate(target_files):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                file_text = fp.read()
            if idx > 0:
                # Add elegant page break between merged chapters/files
                merged_sections.append(
                    '\n\n<div style="page-break-before: always; height: 0; margin: 30px 0;"></div>\n'
                    '<hr style="border: 0; border-top: 1px solid #d0d7de; margin: 24px 0;" />\n\n'
                )
            merged_sections.append(file_text)
        except Exception as e:
            print(f"[warning] Failed reading {f.name}: {e}", file=sys.stderr, flush=True)

    combined_content = "".join(merged_sections)
    doc_title = target_files[0].stem.replace("-", " ").replace("_", " ").title() if len(target_files) == 1 else doc_dir.name.replace("-", " ").title()

    return convert_markdown_source(
        content=combined_content,
        doc_dir=doc_dir,
        output_file=out_file,
        max_img_width=max_img_width,
        do_copy=do_copy,
        verbose=verbose,
        auto_paste=auto_paste,
        doc_title=doc_title
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown/Obsidian files into Google Docs-optimized HTML with embedded diagrams and highlighted code."
    )
    parser.add_argument("paths", nargs="*", default=["."], help="Path(s) to markdown file(s) or directory (default: current dir)")
    parser.add_argument("-o", "--output", help="Custom output HTML path")
    parser.add_argument("-c", "--copy", action="store_true", default=True, help="Automatically copy rich HTML to macOS clipboard (default: True)")
    parser.add_argument("--no-copy", dest="copy", action="store_false", help="Do not copy to clipboard")
    parser.add_argument("-p", "--paste", action="store_true", help="Automatically trigger Cmd+V in the frontmost application")
    parser.add_argument("-b", "--open", action="store_true", help="Open generated HTML in browser")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch file(s) for changes and auto-rebuild")
    parser.add_argument("--width", type=int, default=600, help="Default max width for images in pixels (default: 600)")
    parser.add_argument("--single", action="store_true", help="If directory is given, only convert the first file instead of merging all")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    out_file = convert_markdown(
        input_path_or_paths=args.paths,
        output_path=args.output,
        max_img_width=args.width,
        do_copy=args.copy,
        verbose=args.verbose,
        auto_paste=args.paste,
        single_mode=args.single
    )

    if not out_file:
        sys.exit(1)

    if args.copy and not args.paste:
        print("💡 Document copied to clipboard! Just press Cmd+V in Google Docs.", flush=True)

    if args.open:
        subprocess.run(["open", str(out_file)])

    if args.watch:
        watched_files = [Path(p).resolve() for p in args.paths if Path(p).is_file()]
        if not watched_files and Path(args.paths[0]).is_dir():
            watched_files = list(Path(args.paths[0]).glob("*.md"))

        print(f"👀 Watching {len(watched_files)} file(s) for changes... (Press Ctrl+C to stop)", flush=True)
        mtimes = {f: f.stat().st_mtime for f in watched_files if f.exists()}
        while True:
            time.sleep(1)
            try:
                changed = False
                for f in watched_files:
                    if f.exists() and f.stat().st_mtime != mtimes.get(f, 0):
                        mtimes[f] = f.stat().st_mtime
                        changed = True
                if changed:
                    convert_markdown(
                        input_path_or_paths=args.paths,
                        output_path=args.output,
                        max_img_width=args.width,
                        do_copy=args.copy,
                        verbose=args.verbose,
                        auto_paste=args.paste,
                        single_mode=args.single
                    )
                    if args.copy and not args.paste:
                        print("💡 Updated & copied to clipboard! Press Cmd+V in Google Docs.", flush=True)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[error] {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
