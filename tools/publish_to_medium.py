#!/usr/bin/env python3
"""
Medium Publishing Automation Tool

Reads markdown articles from content/affiliate/, converts them to Medium-compatible HTML,
and publishes them as drafts (simulation mode writes HTML to disk for review).
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_ROOT / "content" / "affiliate"
PUBLISHED_DIR = PROJECT_ROOT / "content" / "published" / "medium"
TRACKING_FILE = PROJECT_ROOT / "content" / "published" / "medium_tracking.json"

# ---------------------------------------------------------------------------
# Medium-compatible HTML helpers
# Medium supports: p, a, strong, em, h1-h3, ul, ol, li, blockquote,
#                  pre, code, figure, figcaption, img, hr, br, table,
#                  thead, tbody, tr, td
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """Escape raw text for HTML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def markdown_to_medium_html(md: str) -> str:
    """
    Convert a subset of Markdown to Medium-compatible HTML.
    Handles: headers, bold, italic, links, images, lists, tables,
    horizontal rules, blockquotes, paragraphs.
    """
    lines = md.splitlines()
    html_parts: list[str] = []
    i = 0
    n = len(lines)

    def flush_paragraph(buf: list[str]) -> None:
        if buf:
            para = " ".join(buf).strip()
            if para:
                html_parts.append(f"<p>{para}</p>")
            buf.clear()

    paragraph_buffer: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Horizontal rule
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            flush_paragraph(paragraph_buffer)
            html_parts.append("<hr />")
            i += 1
            continue

        # Headers
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_paragraph(paragraph_buffer)
            level = len(m.group(1))
            tag = f"h{min(level, 3)}"
            html_parts.append(f"<{tag}>{_inline_markup(m.group(2))}</{tag}>")
            i += 1
            continue

        # Blockquote
        if stripped.startswith("> "):
            flush_paragraph(paragraph_buffer)
            quote_lines: list[str] = []
            while i < n and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            quote_text = " ".join(quote_lines)
            html_parts.append(f"<blockquote><p>{_inline_markup(quote_text)}</p></blockquote>")
            continue

        # Unordered list
        if re.match(r"^[-*+]\s+", stripped):
            flush_paragraph(paragraph_buffer)
            list_items: list[str] = []
            while i < n:
                s = lines[i].strip()
                if re.match(r"^[-*+]\s+", s):
                    item_text = re.sub(r"^[-*+]\s+", "", s)
                    list_items.append(f"<li>{_inline_markup(item_text)}</li>")
                    i += 1
                elif s == "" and i + 1 < n and re.match(r"^[-*+]\s+", lines[i + 1].strip()):
                    i += 1  # blank line inside list
                elif s == "":
                    break
                else:
                    # continuation of last item
                    if list_items:
                        list_items[-1] = list_items[-1][:-5] + " " + _inline_markup(s) + "</li>"
                    i += 1
            html_parts.append("<ul>" + "".join(list_items) + "</ul>")
            continue

        # Ordered list
        om = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if om:
            flush_paragraph(paragraph_buffer)
            list_items: list[str] = []
            while i < n:
                s = lines[i].strip()
                om2 = re.match(r"^(\d+)\.\s+(.*)$", s)
                if om2:
                    list_items.append(f"<li>{_inline_markup(om2.group(2))}</li>")
                    i += 1
                elif s == "" and i + 1 < n and re.match(r"^\d+\.\s+", lines[i + 1].strip()):
                    i += 1
                elif s == "":
                    break
                else:
                    if list_items:
                        list_items[-1] = list_items[-1][:-5] + " " + _inline_markup(s) + "</li>"
                    i += 1
            html_parts.append("<ol>" + "".join(list_items) + "</ol>")
            continue

        # Table (simple GFM-style) — tolerates blank lines between rows
        if "|" in stripped:
            # look ahead past blank lines for separator row
            sep_idx = i + 1
            while sep_idx < n and lines[sep_idx].strip() == "":
                sep_idx += 1
            if sep_idx < n and re.match(r"^\|?[\s\-:|]+\|", lines[sep_idx].strip()):
                flush_paragraph(paragraph_buffer)
                rows: list[str] = []
                # header row
                header_cells = [c.strip() for c in stripped.split("|")]
                header_cells = [c for c in header_cells if c]
                rows.append("<tr>" + "".join(f"<td>{_inline_markup(c)}</td>" for c in header_cells) + "</tr>")
                i = sep_idx + 1  # skip separator line
                while i < n:
                    s = lines[i].strip()
                    if s == "":
                        i += 1
                        continue
                    if "|" not in s:
                        break
                    cells = [c.strip() for c in s.split("|")]
                    cells = [c for c in cells if c]
                    if cells:
                        rows.append("<tr>" + "".join(f"<td>{_inline_markup(c)}</td>" for c in cells) + "</tr>")
                    i += 1
                html_parts.append("<table>" + "".join(rows) + "</table>")
                continue

        # Blank line -> flush paragraph
        if stripped == "":
            flush_paragraph(paragraph_buffer)
            i += 1
            continue

        # Regular paragraph line
        paragraph_buffer.append(_inline_markup(stripped))
        i += 1

    flush_paragraph(paragraph_buffer)
    return "\n".join(html_parts)


def _protect_html(text: str) -> tuple[str, list[str]]:
    """Replace existing HTML tags with placeholders so inline markdown doesn't corrupt them."""
    placeholders: list[str] = []

    def replacer(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"§HTML{len(placeholders) - 1}§"

    protected = re.sub(r"<[^>]+>", replacer, text)
    return protected, placeholders


def _restore_html(text: str, placeholders: list[str]) -> str:
    for i, ph in enumerate(placeholders):
        text = text.replace(f"§HTML{i}§", ph)
    return text


def _inline_markup(text: str) -> str:
    """Convert inline markdown to HTML."""
    # Images: ![alt](url)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        r'<figure><img src="\2" alt="\1" /></figure>',
        text,
    )
    # Links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    # Protect generated HTML from being mangled by _ / * / __ / ** patterns
    text, placeholders = _protect_html(text)
    # Bold/strong: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic/em: *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    # Inline code: `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = _restore_html(text, placeholders)
    return text


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

def load_tracking() -> dict[str, Any]:
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_tracking(data: dict[str, Any]) -> None:
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------

def publish_draft(
    title: str,
    html_content: str,
    tags: list[str],
    *,
    simulate: bool = True,
    article_source_path: str | None = None,
) -> dict[str, Any]:
    """
    Publish (or simulate publishing) a draft to Medium.

    Parameters
    ----------
    title: Article title.
    html_content: Medium-compatible HTML body.
    tags: List of tags (max 5).
    simulate: If True, write HTML to disk instead of calling the API.
    article_source_path: Optional path to the source markdown for tracking.

    Returns
    -------
    Response dict with ``success``, ``draft_url`` (simulated), and ``id``.
    """
    tags = tags[:5]
    tracking = load_tracking()
    source_key = article_source_path or title

    if simulate:
        PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]+", "-", title).strip("-").lower()[:60]
        out_path = PUBLISHED_DIR / f"{safe_name}.html"

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_escape_html(title)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 680px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #292929; }}
  h1, h2, h3 {{ font-weight: 600; }}
  a {{ color: #03a87c; text-decoration: none; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  td, th {{ border: 1px solid #ddd; padding: 8px; }}
  blockquote {{ border-left: 3px solid #03a87c; margin-left: 0; padding-left: 20px; color: #555; }}
  figure {{ margin: 1.5em 0; }}
  img {{ max-width: 100%; height: auto; }}
  hr {{ border: none; border-top: 1px solid #eee; margin: 2em 0; }}
  ul, ol {{ padding-left: 20px; }}
  .meta {{ color: #757575; font-size: 0.9em; margin-bottom: 2em; }}
</style>
</head>
<body>
<h1>{_escape_html(title)}</h1>
<p class="meta">Tags: {", ".join(tags)} | Simulated Medium Draft</p>
{html_content}
</body>
</html>"""

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        draft_url = f"file://{out_path.as_posix()}"
        article_id = f"simulated-{safe_name}"

        result = {
            "success": True,
            "simulate": True,
            "id": article_id,
            "draft_url": draft_url,
            "output_path": str(out_path),
        }
    else:
        # -----------------------------------------------------------------
        # TODO: Replace with real Medium API integration.
        # Medium API v1 endpoint: POST https://api.medium.com/v1/users/{userId}/posts
        # Headers: Authorization: Bearer {token}
        # Body: title, contentFormat="html", content, tags, publishStatus="draft"
        # -----------------------------------------------------------------
        raise NotImplementedError(
            "Live Medium API publishing is not yet implemented. "
            "Set simulate=True to generate reviewable HTML drafts."
        )

    # Update tracking
    tracking[source_key] = {
        "published_to_medium": True,
        "title": title,
        "simulate": simulate,
        "article_id": article_id,
        "draft_url": draft_url,
        "tags": tags,
    }
    save_tracking(tracking)
    return result


# ---------------------------------------------------------------------------
# Article processing
# ---------------------------------------------------------------------------

def process_article(md_path: Path, tags: list[str] | None = None) -> dict[str, Any]:
    """Read a markdown article, convert to HTML, and publish/simulate."""
    md_content = md_path.read_text(encoding="utf-8")

    # Extract title from first H1 and remove it from body so it isn't duplicated
    title_match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        md_content = re.sub(r"^#\s+.+\n\n?", "", md_content, count=1, flags=re.MULTILINE)
    else:
        title = md_path.stem.replace("-", " ").title()

    # Derive tags from filename if not provided
    if tags is None:
        base = md_path.stem.lower()
        # simple heuristic: split on "-vs-" or "-"
        parts = re.split(r"-vs-|-", base)
        parts = [p for p in parts if p not in ("which", "one", "should", "you", "choose")]
        tags = parts[:5] or ["affiliate"]

    html_body = markdown_to_medium_html(md_content)
    result = publish_draft(
        title=title,
        html_content=html_body,
        tags=tags,
        simulate=True,
        article_source_path=str(md_path),
    )
    return result


def process_all_articles() -> list[dict[str, Any]]:
    """Process every markdown file in content/affiliate/."""
    results: list[dict[str, Any]] = []
    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        print(f"Processing: {md_file.name}")
        result = process_article(md_file)
        results.append(result)
        print(f"  -> Draft saved to: {result['output_path']}")
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path_arg = Path(sys.argv[1])
        if not path_arg.is_absolute():
            path_arg = PROJECT_ROOT / path_arg
        if path_arg.is_dir():
            for md_file in sorted(path_arg.glob("*.md")):
                res = process_article(md_file)
                print(res["output_path"])
        else:
            res = process_article(path_arg)
            print(res["output_path"])
    else:
        process_all_articles()
