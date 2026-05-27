"""
Asset Factory Tools
Tools for generating, packaging, and listing digital assets for sale.

All tools are registered via the @business_tool decorator so the AssetFactoryAgent
(and other agents) can discover and execute them through the BusinessToolRegistry.
"""

import html
import json
import os
import re
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault
from core.model_router import router


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug or "untitled"


def _assets_dir() -> str:
    """Return the absolute path to the products/assets directory."""
    base = getattr(config, "WORKSPACE_ROOT", os.getcwd())
    path = os.path.join(base, "products", "assets")
    os.makedirs(path, exist_ok=True)
    return path


def _md_to_simple_html(title: str, markdown: str) -> str:
    """Very lightweight markdown-to-HTML converter for ebook preview."""
    lines = markdown.splitlines()
    out_lines: List[str] = []
    in_code = False
    out_lines.append("<!DOCTYPE html>")
    out_lines.append('<html lang="en"><head>')
    out_lines.append(f"<meta charset='UTF-8'><title>{html.escape(title)}</title>")
    out_lines.append("<style>")
    out_lines.append("body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;line-height:1.6;padding:0 20px}")
    out_lines.append("h1,h2,h3{color:#222}pre{background:#f4f4f4;padding:12px;border-radius:6px;overflow:auto}")
    out_lines.append("code{font-family:monospace;font-size:.95em}blockquote{border-left:4px solid #ccc;padding-left:12px;color:#555}")
    out_lines.append("</style></head><body>")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                out_lines.append("</code></pre>")
                in_code = False
            else:
                out_lines.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out_lines.append(html.escape(line))
            continue
        if stripped.startswith("# "):
            out_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            out_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            out_lines.append(f"<h3>{html.escape(stripped[4:])}</h3>")
        elif stripped.startswith("> "):
            out_lines.append(f"<blockquote>{html.escape(stripped[2:])}</blockquote>")
        elif stripped.startswith("- "):
            out_lines.append(f"<ul><li>{html.escape(stripped[2:])}</li></ul>")
        elif stripped == "":
            out_lines.append("<br>")
        else:
            out_lines.append(f"<p>{html.escape(line)}</p>")
    if in_code:
        out_lines.append("</code></pre>")
    out_lines.append("</body></html>")
    return "\n".join(out_lines)


async def _generate_text(
    system_prompt: str, user_prompt: str, temperature: float = 0.7
) -> str:
    """Helper to generate text via the model router."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        return await router.chat(messages=messages, temperature=temperature)
    except Exception as exc:
        return f"[LLM Error] {exc}"


@business_tool(
    name="generate_ebook_outline",
    description="Generate a structured ebook outline with chapter titles and descriptions via LLM.",
    category="asset_creation",
)
async def generate_ebook_outline(topic: str, chapters: int = 5) -> Dict[str, Any]:
    """
    Generate an ebook outline via LLM.

    Args:
        topic: The ebook topic.
        chapters: Number of chapters (default 5).

    Returns:
        Dict with 'outline', 'topic', 'chapters', and 'status'.
    """
    system = (
        "You are a professional book outline generator. "
        "Respond ONLY with valid JSON in this exact format:\n"
        '{\n  "title": "...",\n  "chapters": [\n'
        '    {"number": 1, "title": "...", "summary": "..."}\n'
        "  ]\n}"
    )
    user = f"Create a detailed {chapters}-chapter outline for an ebook about: {topic}"
    raw = await _generate_text(system, user, temperature=0.7)

    if raw.startswith("[LLM Error]"):
        return {"status": "error", "error": raw, "topic": topic, "chapters": chapters}

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in response")
        parsed = json.loads(raw[start:end])
        return {
            "status": "success",
            "topic": topic,
            "chapters": chapters,
            "outline": parsed,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": f"JSON parse failed: {exc}",
            "raw": raw,
            "topic": topic,
            "chapters": chapters,
        }


@business_tool(
    name="generate_ebook_content",
    description="Generate full ebook markdown content from a structured outline and write to disk.",
    category="asset_creation",
)
async def generate_ebook_content(outline: dict) -> Dict[str, Any]:
    """
    Generate full ebook content from a structured outline and write real files to disk.

    Args:
        outline: Dict with at least 'title' and 'chapters' list.

    Returns:
        Dict with 'content', 'title', 'paths', and 'status'.
    """
    title = outline.get("title", "Untitled Ebook")
    chapters = outline.get("chapters", [])
    system = (
        "You are an expert author. Write a complete ebook in Markdown. "
        "Include a title page, table of contents, and full chapter content. "
        "Use professional formatting with headings, bullet points, and examples."
    )

    chapter_summaries = "\n".join(
        f"Chapter {c.get('number', i + 1)}: {c.get('title', 'Untitled')}\n"
        f"Summary: {c.get('summary', '')}"
        for i, c in enumerate(chapters)
    )
    user = (
        f"Write the complete ebook titled '{title}'.\n\n"
        f"Outline:\n{chapter_summaries}\n\nWrite the full text now."
    )

    content = await _generate_text(system, user, temperature=0.8)

    if content.startswith("[LLM Error]"):
        return {"status": "error", "error": content, "title": title}

    title_slug = _slugify(title)
    assets = _assets_dir()
    md_path = os.path.join(assets, f"{title_slug}.md")
    html_path = os.path.join(assets, f"{title_slug}.html")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        html_content = _md_to_simple_html(title, content)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Disk write failed: {exc}",
            "title": title,
        }

    # Secondary vault persistence
    vault_doc = {
        "title": title,
        "title_slug": title_slug,
        "type": "ebook",
        "md_path": md_path,
        "html_path": html_path,
        "word_count": len(content.split()),
        "outline": outline,
    }
    vault_id = vault.insert("assets", vault_doc)

    return {
        "status": "success",
        "title": title,
        "content": content,
        "word_count": len(content.split()),
        "paths": {"markdown": md_path, "html": html_path},
        "vault_id": vault_id,
    }


@business_tool(
    name="generate_prompt_pack",
    description="Generate a pack of AI prompts for a specific niche and write to disk.",
    category="asset_creation",
)
async def generate_prompt_pack(niche: str, count: int = 10) -> Dict[str, Any]:
    """
    Generate AI prompt templates for sale and write a real file to disk.

    Args:
        niche: Target niche (e.g., 'copywriting', 'image generation').
        count: Number of prompts to generate.

    Returns:
        Dict with 'prompts', 'readme', 'niche', 'path', and 'status'.
    """
    system = (
        "You are a prompt engineering expert. "
        "Respond ONLY with valid JSON in this exact format:\n"
        '{\n  "prompts": [\n'
        '    {"name": "...", "prompt": "...", "use_case": "...", "category": "..."}\n'
        '  ],\n  "readme": "..."\n}'
    )
    user = (
        f"Create {count} high-quality, detailed AI prompts for the niche: {niche}. "
        "Include a README description."
    )
    raw = await _generate_text(system, user, temperature=0.8)

    if raw.startswith("[LLM Error]"):
        return {"status": "error", "error": raw, "niche": niche, "count": count}

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found")
        parsed = json.loads(raw[start:end])
        prompts = parsed.get("prompts", [])
        readme = parsed.get(
            "readme", f"# {niche} Prompt Pack\n\nA collection of {count} AI prompts."
        )
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Parse error: {exc}",
            "raw": raw,
            "niche": niche,
            "count": count,
        }

    niche_slug = _slugify(niche)
    assets = _assets_dir()
    txt_path = os.path.join(assets, f"{niche_slug}_prompts.txt")

    try:
        lines: List[str] = []
        lines.append(f"# {niche.title()} Prompt Pack")
        lines.append("")
        lines.append(readme)
        lines.append("")
        lines.append(f"Total prompts: {len(prompts)}")
        lines.append("=" * 60)
        lines.append("")
        for i, p in enumerate(prompts, start=1):
            lines.append(f"{i}. {p.get('name', 'Untitled')}")
            lines.append(f"   Category: {p.get('category', 'General')}")
            lines.append(f"   Use case: {p.get('use_case', 'N/A')}")
            lines.append("")
            lines.append(f"   Prompt:")
            lines.append(f"   {p.get('prompt', '')}")
            lines.append("")
            lines.append("-" * 60)
            lines.append("")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Disk write failed: {exc}",
            "niche": niche,
            "count": count,
        }

    # Secondary vault persistence
    vault_doc = {
        "niche": niche,
        "niche_slug": niche_slug,
        "type": "prompt_pack",
        "path": txt_path,
        "count": len(prompts),
        "prompts": prompts,
        "readme": readme,
    }
    vault_id = vault.insert("assets", vault_doc)

    return {
        "status": "success",
        "niche": niche,
        "count": len(prompts),
        "prompts": prompts,
        "readme": readme,
        "path": txt_path,
        "vault_id": vault_id,
    }


@business_tool(
    name="generate_code_template",
    description="Generate boilerplate code for a project type with specified features and write to disk.",
    category="asset_creation",
)
async def generate_code_template(project_type: str, features: list) -> Dict[str, Any]:
    """
    Generate boilerplate code and write real files to disk.

    Args:
        project_type: Type of project (e.g., 'fastapi_saas', 'react_dashboard').
        features: List of features (e.g., ['auth', 'stripe']).

    Returns:
        Dict with 'code', 'readme', 'requirements', 'dir', and 'status'.
    """
    system = (
        "You are a senior software engineer. Generate production-ready boilerplate code. "
        "Respond ONLY with valid JSON in this exact format:\n"
        '{\n  "readme": "...",\n  "code": "...",\n  "requirements": "..."\n}'
    )
    user = (
        f"Generate a {project_type} boilerplate with these features: {', '.join(features)}. "
        "Include a README, main source code, and requirements/dependencies."
    )
    raw = await _generate_text(system, user, temperature=0.3)

    if raw.startswith("[LLM Error]"):
        return {
            "status": "error",
            "error": raw,
            "project_type": project_type,
            "features": features,
        }

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found")
        parsed = json.loads(raw[start:end])
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Parse error: {exc}",
            "raw": raw,
            "project_type": project_type,
            "features": features,
        }

    readme = parsed.get("readme", "")
    code = parsed.get("code", "")
    requirements = parsed.get("requirements", "")

    assets = _assets_dir()
    project_dir = os.path.join(assets, _slugify(project_type))
    os.makedirs(project_dir, exist_ok=True)

    try:
        with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme)
        with open(os.path.join(project_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write(requirements)
        with open(os.path.join(project_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Disk write failed: {exc}",
            "project_type": project_type,
            "features": features,
        }

    # Secondary vault persistence
    vault_doc = {
        "project_type": project_type,
        "type": "code_template",
        "dir": project_dir,
        "features": features,
        "readme": readme,
        "code": code,
        "requirements": requirements,
    }
    vault_id = vault.insert("assets", vault_doc)

    return {
        "status": "success",
        "project_type": project_type,
        "features": features,
        "readme": readme,
        "code": code,
        "requirements": requirements,
        "dir": project_dir,
        "vault_id": vault_id,
    }


@business_tool(
    name="generate_notion_template",
    description="Generate a markdown structure suitable for Notion import and write to disk.",
    category="asset_creation",
)
async def generate_notion_template(purpose: str) -> Dict[str, Any]:
    """
    Generate a Notion-ready markdown template and write a real file to disk.

    Args:
        purpose: Purpose of the template (e.g., 'project_management', 'content_calendar').

    Returns:
        Dict with 'markdown', 'guide', 'purpose', 'path', and 'status'.
    """
    system = (
        "You are a productivity systems expert. Create a Notion-ready Markdown template. "
        "Use toggle lists, tables, headers, and checkboxes. "
        "Respond ONLY with valid JSON in this exact format:\n"
        '{\n  "markdown": "...",\n  "guide": "..."\n}'
    )
    user = f"Create a complete Notion template for: {purpose}. Include setup instructions."
    raw = await _generate_text(system, user, temperature=0.7)

    if raw.startswith("[LLM Error]"):
        return {"status": "error", "error": raw, "purpose": purpose}

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found")
        parsed = json.loads(raw[start:end])
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Parse error: {exc}",
            "raw": raw,
            "purpose": purpose,
        }

    markdown = parsed.get("markdown", "")
    guide = parsed.get("guide", "")

    purpose_slug = _slugify(purpose)
    assets = _assets_dir()
    md_path = os.path.join(assets, f"{purpose_slug}_notion.md")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Notion Template: {purpose.title()}\n\n")
            f.write(f"## Setup Guide\n\n{guide}\n\n")
            f.write(f"## Template\n\n{markdown}\n")
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Disk write failed: {exc}",
            "purpose": purpose,
        }

    # Secondary vault persistence
    vault_doc = {
        "purpose": purpose,
        "purpose_slug": purpose_slug,
        "type": "notion_template",
        "path": md_path,
        "markdown": markdown,
        "guide": guide,
    }
    vault_id = vault.insert("assets", vault_doc)

    return {
        "status": "success",
        "purpose": purpose,
        "markdown": markdown,
        "guide": guide,
        "path": md_path,
        "vault_id": vault_id,
    }


@business_tool(
    name="package_asset",
    description="Package generated asset files into a real zip archive with metadata.",
    category="asset_creation",
)
def package_asset(asset_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Package asset files into a real zip archive.

    Args:
        asset_id: Unique asset identifier.
        files: List of file dicts. Each dict may contain:
            - 'filename' (required): Name inside the zip.
            - 'content': String content to write.
            - 'path': Existing file path to copy (content takes precedence).

    Returns:
        Dict with 'zip_path', 'file_count', 'asset_id', and 'status'.
    """
    if not files:
        return {"status": "error", "error": "No files provided", "asset_id": asset_id}

    output_dir = _assets_dir()
    zip_path = os.path.join(output_dir, f"{asset_id}.zip")

    try:
        written = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            meta = {
                "asset_id": asset_id,
                "packaged_at": datetime.utcnow().isoformat(),
                "file_count": len(files),
            }
            zf.writestr("metadata.json", json.dumps(meta, indent=2))

            for file_info in files:
                filename = file_info.get("filename")
                if not filename:
                    continue
                content = file_info.get("content")
                path = file_info.get("path")

                if content is not None:
                    zf.writestr(filename, content)
                    written += 1
                elif path and os.path.isfile(path):
                    zf.write(path, filename)
                    written += 1
                elif path and os.path.isdir(path):
                    for root, _, names in os.walk(path):
                        for name in names:
                            full = os.path.join(root, name)
                            arcname = os.path.relpath(full, path)
                            zf.write(full, arcname)
                    written += 1
                else:
                    zf.writestr(filename, "")
                    written += 1

        # Secondary vault persistence
        vault_doc = {
            "asset_id": asset_id,
            "type": "package",
            "zip_path": zip_path,
            "file_count": written,
        }
        vault_id = vault.insert("assets", vault_doc)

        return {
            "status": "success",
            "asset_id": asset_id,
            "zip_path": zip_path,
            "file_count": written,
            "vault_id": vault_id,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "asset_id": asset_id}


@business_tool(
    name="list_asset_for_sale",
    description="Save a listing intent for an asset to the unified vault.",
    category="asset_creation",
)
def list_asset_for_sale(asset_id: str, platform: str, price: float) -> Dict[str, Any]:
    """
    Record an intent to list an asset for sale.

    Args:
        asset_id: The asset ID.
        platform: Marketplace platform (e.g., 'gumroad', 'etsy').
        price: Listing price.

    Returns:
        Dict with 'listing_id', 'status', and vault record details.
    """
    try:
        listing_doc = {
            "asset_id": asset_id,
            "platform": platform,
            "price": float(price),
            "status": "listed",
            "listed_at": datetime.utcnow().isoformat(),
        }
        listing_id = vault.insert("asset_sales", listing_doc)
        return {
            "status": "success",
            "listing_id": listing_id,
            "asset_id": asset_id,
            "platform": platform,
            "price": price,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "asset_id": asset_id,
            "platform": platform,
            "price": price,
        }


@business_tool(
    name="get_trending_asset_niches",
    description="Discover trending digital product niches via LLM market research.",
    category="market_research",
)
async def get_trending_asset_niches() -> Dict[str, Any]:
    """
    Use LLM to identify currently trending digital product niches.

    Returns:
        Dict with 'niches' list and 'status'.
    """
    system = (
        "You are a market research analyst specializing in digital products. "
        "Respond ONLY with valid JSON in this exact format:\n"
        '{\n  "niches": [\n'
        '    {"name": "...", "category": "...", "demand_score": 0, "note": "..."}\n'
        "  ]\n}"
    )
    user = (
        "What are the top 10 trending niches for digital products right now? "
        "Consider ebooks, prompt packs, Notion templates, code templates, and design assets."
    )
    raw = await _generate_text(system, user, temperature=0.8)

    if raw.startswith("[LLM Error]"):
        return {"status": "error", "error": raw}

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found")
        parsed = json.loads(raw[start:end])
        niches = parsed.get("niches", [])
        return {
            "status": "success",
            "niches": niches,
            "count": len(niches),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Parse error: {exc}",
            "raw": raw,
        }
