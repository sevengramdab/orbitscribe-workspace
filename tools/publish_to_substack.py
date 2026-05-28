#!/usr/bin/env python3
"""
Substack publishing automation.

Reads markdown articles from content/affiliate/, converts them to
Substack-compatible format (clean markdown with YAML frontmatter),
and simulates publishing by writing drafts to content/published/substack/.
"""

import json
import os
import re
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AFFILIATE_DIR = Path("content/affiliate")
PUBLISHED_DIR = Path("content/published/substack")
STATUS_FILE = PUBLISHED_DIR / "published_status.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs() -> None:
    """Ensure the output directory exists."""
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)


def slugify(title: str) -> str:
    """Convert a title to a URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


def extract_title(content: str) -> str:
    """Extract the H1 title from markdown content."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled"


def strip_h1(content: str) -> str:
    """Remove the first H1 so it doesn't duplicate the frontmatter title."""
    return re.sub(r"^#\s+.+\n?", "", content, count=1, flags=re.MULTILINE).lstrip("\n")


def clean_markdown(content: str) -> str:
    """
    Basic clean-up for Substack compatibility.
    - Strips raw affiliate query params like ?tag={{AMAZON_ASSOCIATES_TAG}}
      and replaces them with clean URLs or a placeholder.
    - Normalises multiple blank lines.
    """
    # Remove Amazon affiliate tracking tags (Substack can be picky about raw tags)
    content = re.sub(r"\?tag=\{\{[^}]+\}\}", "", content)

    # Collapse more than two consecutive blank lines to two
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def build_frontmatter(
    title: str,
    subtitle: str = "",
    tags: List[str] | None = None,
    publish_as_free: bool = True,
) -> str:
    """Build YAML frontmatter suitable for Substack imports."""
    tags = tags or []
    fm = "---\n"
    fm += f"title: \"{title}\"\n"
    if subtitle:
        fm += f"subtitle: \"{subtitle}\"\n"
    if tags:
        # Substack's importer usually expects comma-separated keywords
        fm += f"keywords: {', '.join(tags)}\n"
    fm += f"publish_as_free: {str(publish_as_free).lower()}\n"
    fm += "---\n\n"
    return fm


def load_status() -> dict:
    """Load the JSON tracking file."""
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"published": []}


def save_status(status: dict) -> None:
    """Save the JSON tracking file."""
    with open(STATUS_FILE, "w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=2)


# ---------------------------------------------------------------------------
# Core publishing function
# ---------------------------------------------------------------------------

def publish_draft(
    title: str,
    content: str,
    tags: List[str],
    publish_as_free: bool = True,
    *,
    simulate: bool = True,
) -> Path:
    """
    Publish (or simulate publishing) a Substack draft.

    Parameters
    ----------
    title : str
        Article title.
    content : str
        Markdown body.
    tags : list[str]
        Tags / keywords for the post.
    publish_as_free : bool
        Whether the post should be free (True) or paid-only (False).
    simulate : bool
        If True, write the formatted draft to disk instead of hitting
        the Substack API / email integration.

    Returns
    -------
    Path
        Path to the written draft (simulation mode) or an empty Path.
    """
    ensure_dirs()

    if simulate:
        slug = slugify(title)
        out_path = PUBLISHED_DIR / f"{slug}.md"

        body = strip_h1(content)
        body = clean_markdown(body)

        frontmatter = build_frontmatter(
            title=title,
            subtitle="",
            tags=tags,
            publish_as_free=publish_as_free,
        )

        draft = frontmatter + body + "\n"

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(draft)

        # Update status tracker
        status = load_status()
        entry = {
            "slug": slug,
            "title": title,
            "tags": tags,
            "publish_as_free": publish_as_free,
            "simulated": True,
            "output_path": str(out_path),
        }
        # Replace existing entry by slug if present
        status["published"] = [e for e in status["published"] if e["slug"] != slug]
        status["published"].append(entry)
        save_status(status)

        print(f"[SIMULATION] Draft written to {out_path}")
        return out_path

    # -----------------------------------------------------------------------
    # Real API / email integration stub
    # -----------------------------------------------------------------------
    print("[LIVE] Publishing to Substack API …")
    # TODO: integrate with Substack REST API or email workflow here.
    return Path()


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_article(path: Path) -> Path:
    """Read an affiliate article and simulate publishing it to Substack."""
    raw = path.read_text(encoding="utf-8")
    title = extract_title(raw)

    # Derive tags from filename / title heuristics
    lower_title = title.lower()
    tags: List[str] = ["affiliate", "comparison"]

    if "photoshop" in lower_title or "gimp" in lower_title:
        tags.extend(["design", "software", "photo editing"])
    elif "bluehost" in lower_title or "siteground" in lower_title:
        tags.extend(["hosting", "web", "wordpress"])
    elif "nordvpn" in lower_title or "expressvpn" in lower_title:
        tags.extend(["vpn", "privacy", "security"])
    else:
        tags.append("review")

    return publish_draft(
        title=title,
        content=raw,
        tags=list(set(tags)),
        publish_as_free=True,
        simulate=True,
    )


def process_all() -> List[Path]:
    """Process every *.md file in content/affiliate/."""
    ensure_dirs()
    paths = sorted(AFFILIATE_DIR.glob("*.md"))
    results: List[Path] = []
    for p in paths:
        print(f"Processing {p.name} …")
        results.append(process_article(p))
    return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generated = process_all()
    print(f"\nDone. {len(generated)} draft(s) generated.")
    for g in generated:
        print(f"  - {g}")
