"""
Content marketing automation tools for the Monetization Swarm.

Provides generation, optimization, scheduling, and analytics for blog posts,
social media, newsletters, and email sequences. All tools are registered via
the @business_tool decorator so agents can discover and execute them dynamically.
"""

import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault
from core.model_router import router
from core.tool_executor import _web_search


# ── Disk helpers ────────────────────────────────────────────────────────

_CONTENT_ROOT = os.path.join(config.WORKSPACE_ROOT, "content")


def _sanitize_slug(text: str) -> str:
    """Convert arbitrary text into a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:80] or "untitled"


def _write_to_disk(relative_path: str, content: str) -> str:
    """Write content to a path under the content root. Returns the absolute path."""
    abs_path = os.path.join(_CONTENT_ROOT, relative_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return abs_path


# ── LLM helper ──────────────────────────────────────────────────────────

async def _llm_generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> str:
    """Generate text via the global model router."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        return await router.chat(messages=messages, temperature=temperature)
    except Exception as exc:
        return f"[LLM generation failed: {exc}]"


# ── Trending Topics ─────────────────────────────────────────────────────

@business_tool(
    name="research_trending_topics",
    description="Research trending topics for a given niche using web search.",
    category="content",
)
async def research_trending_topics(niche: str) -> Dict[str, Any]:
    """
    Search the web for trending topics in a given niche.

    Args:
        niche: The market niche to research (e.g. "AI automation", "vegan recipes").

    Returns:
        Dict with trending topics, search metadata, and confidence score.
    """
    if not niche or not isinstance(niche, str):
        return {"error": "Invalid niche parameter", "topics": []}

    query = f"trending topics in {niche} 2024 2025"
    loop = asyncio.get_event_loop()
    search_result = await loop.run_in_executor(None, _web_search, query, 8)

    topics: List[Dict[str, Any]] = []
    if search_result.get("status") == "ok":
        raw_results = search_result.get("data", {}).get("results", [])
        for idx, item in enumerate(raw_results, start=1):
            topics.append(
                {
                    "rank": idx,
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                }
            )
    else:
        # Graceful fallback so the agent keeps working even if search fails
        topics = [
            {
                "rank": 1,
                "title": f"Latest innovations in {niche}",
                "url": "",
                "snippet": "Industry leaders discuss emerging trends.",
            },
            {
                "rank": 2,
                "title": f"How {niche} is changing the market",
                "url": "",
                "snippet": "Market analysis and forecast.",
            },
            {
                "rank": 3,
                "title": f"Beginner's guide to {niche}",
                "url": "",
                "snippet": "Comprehensive overview for newcomers.",
            },
        ]

    return {
        "niche": niche,
        "topics": topics,
        "topic_count": len(topics),
        "researched_at": datetime.utcnow().isoformat(),
        "source": "web_search" if search_result.get("status") == "ok" else "fallback",
    }


# ── Blog Post ───────────────────────────────────────────────────────────

@business_tool(
    name="generate_blog_post",
    description="Generate a full blog post via LLM given a topic, keywords, tone, and length.",
    category="content",
)
async def generate_blog_post(
    topic: str,
    keywords: List[str],
    tone: str = "professional",
    length: str = "medium",
) -> Dict[str, Any]:
    """
    Generate a blog post and persist it to disk and vault.

    Args:
        topic: The blog post topic.
        keywords: SEO keywords to weave into the content.
        tone: Writing tone (professional, casual, authoritative, playful).
        length: Desired length - short (~400 words), medium (~800), long (~1500).

    Returns:
        Dict with title, body, meta description, word count, file path, and vault ID.
    """
    if not topic:
        return {"error": "Topic is required"}

    word_target = {"short": 400, "medium": 800, "long": 1500}.get(length, 800)
    keyword_str = ", ".join(keywords) if keywords else "none provided"

    system = (
        "You are an expert content marketer and SEO copywriter. "
        "Write original, engaging, well-structured blog posts."
    )
    user = (
        f"Write a {length} blog post (~{word_target} words) about: {topic}\n"
        f"Tone: {tone}\n"
        f"Keywords to include naturally: {keyword_str}\n\n"
        "Return ONLY valid JSON with these keys:\n"
        "  title (string)\n"
        "  body (string, markdown format)\n"
        "  meta_description (string, under 160 chars)\n"
        "  tags (list of strings)\n"
    )

    raw = await _llm_generate(system, user, temperature=0.7)

    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group())
        else:
            payload = json.loads(raw)
    except Exception:
        payload = {
            "title": topic,
            "body": raw,
            "meta_description": f"Read our latest insights on {topic}.",
            "tags": keywords,
        }

    payload.setdefault("title", topic)
    payload.setdefault("body", raw)
    payload.setdefault("meta_description", f"Read our latest insights on {topic}.")
    payload.setdefault("tags", keywords or [])

    word_count = len(payload["body"].split())
    content_id = f"blog_{uuid.uuid4().hex[:8]}"
    slug = _sanitize_slug(topic)
    now_iso = datetime.utcnow().isoformat()

    # Build markdown with frontmatter
    frontmatter = (
        f"---\n"
        f"title: {payload['title']}\n"
        f"date: {now_iso}\n"
        f"keywords: {', '.join(keywords or [])}\n"
        f"---\n\n"
    )
    md_content = frontmatter + payload["body"]
    file_path = _write_to_disk(f"blog/{slug}.md", md_content)

    doc = {
        "content_id": content_id,
        "topic": topic,
        "tone": tone,
        "length": length,
        "keywords": keywords,
        "title": payload["title"],
        "body": payload["body"],
        "meta_description": payload["meta_description"],
        "tags": payload["tags"],
        "word_count": word_count,
        "created_at": now_iso,
        "platform": "blog",
        "status": "draft",
        "file_path": file_path,
    }
    vault.insert("blog_posts", doc, doc_id=content_id)

    return {
        "content_id": content_id,
        "title": payload["title"],
        "word_count": word_count,
        "file_path": file_path,
        "status": "saved",
        "collection": "blog_posts",
    }


# ── Twitter Thread ──────────────────────────────────────────────────────

@business_tool(
    name="generate_twitter_thread",
    description="Generate a Twitter / X thread on a given topic.",
    category="content",
)
async def generate_twitter_thread(
    topic: str,
    tweets: int = 5,
) -> Dict[str, Any]:
    """
    Generate a Twitter thread and persist it to disk and vault.

    Args:
        topic: The thread topic or hook.
        tweets: Number of tweets in the thread (default 5).

    Returns:
        Dict with thread_id, tweets list, file path, and engagement hooks.
    """
    if not topic:
        return {"error": "Topic is required"}

    system = (
        "You are a viral social-media strategist. "
        "Write punchy, high-engagement Twitter threads. "
        "Each tweet must be under 280 characters. "
        "Use hooks, line breaks, and strong CTAs."
    )
    user = (
        f"Create a {tweets}-tweet Twitter thread about: {topic}\n\n"
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "hook": "first tweet hook",\n'
        '  "tweets": ["tweet 1", "tweet 2", ...],\n'
        '  "hashtags": ["#tag1", "#tag2"]\n'
        "}"
    )

    raw = await _llm_generate(system, user, temperature=0.8)

    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group())
        else:
            payload = json.loads(raw)
    except Exception:
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        payload = {
            "hook": lines[0] if lines else topic,
            "tweets": lines[:tweets] or [topic],
            "hashtags": [],
        }

    thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    tweet_list = payload.get("tweets", [])
    if not tweet_list:
        tweet_list = [payload.get("hook", topic)]

    slug = _sanitize_slug(topic)
    thread_text = f"Hook: {payload.get('hook', '')}\n\n" + "\n\n".join(
        f"[{i + 1}/{len(tweet_list)}] {t}" for i, t in enumerate(tweet_list)
    )
    if payload.get("hashtags"):
        thread_text += "\n\n" + " ".join(payload["hashtags"])
    file_path = _write_to_disk(f"social/{slug}_thread.txt", thread_text)

    doc = {
        "content_id": thread_id,
        "topic": topic,
        "platform": "twitter",
        "hook": payload.get("hook", ""),
        "tweets": tweet_list,
        "hashtags": payload.get("hashtags", []),
        "tweet_count": len(tweet_list),
        "created_at": datetime.utcnow().isoformat(),
        "status": "draft",
        "file_path": file_path,
    }
    vault.insert("social_posts", doc, doc_id=thread_id)

    return {
        "content_id": thread_id,
        "tweet_count": len(tweet_list),
        "tweets": tweet_list,
        "file_path": file_path,
        "status": "saved",
        "collection": "social_posts",
    }


# ── Newsletter ──────────────────────────────────────────────────────────

@business_tool(
    name="generate_newsletter",
    description="Generate a newsletter in HTML/text format.",
    category="content",
)
async def generate_newsletter(
    subject: str,
    topics: List[str],
    cta: str,
) -> Dict[str, Any]:
    """
    Generate an email newsletter and persist it to disk and vault.

    Args:
        subject: Email subject line.
        topics: List of content topics / sections to include.
        cta: Call-to-action text (e.g. "Shop Now", "Read More").

    Returns:
        Dict with newsletter_id, html, text, file path, and subject.
    """
    if not subject:
        return {"error": "Subject is required"}

    topic_str = "\n".join(f"- {t}" for t in topics)

    system = (
        "You are an elite email marketing copywriter. "
        "Create beautiful, conversion-optimized newsletters. "
        "Output clean HTML with inline styles and a plain-text version."
    )
    user = (
        f"Subject: {subject}\n"
        f"Topics to cover:\n{topic_str}\n"
        f"Primary CTA: {cta}\n\n"
        "Return ONLY valid JSON with these keys:\n"
        "  subject (string)\n"
        "  preview_text (string)\n"
        "  html (string, full HTML email)\n"
        "  text (string, plain text version)\n"
    )

    raw = await _llm_generate(system, user, temperature=0.7)

    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group())
        else:
            payload = json.loads(raw)
    except Exception:
        payload = {
            "subject": subject,
            "preview_text": f"Don't miss our update on {subject}",
            "html": (
                f"<html><body><h1>{subject}</h1>"
                f"<p>{raw}</p><a href='#'>{cta}</a></body></html>"
            ),
            "text": raw,
        }

    newsletter_id = f"nl_{uuid.uuid4().hex[:8]}"
    slug = _sanitize_slug(subject)
    html_content = payload.get("html", "")
    file_path = _write_to_disk(f"email/{slug}_newsletter.html", html_content)

    doc = {
        "content_id": newsletter_id,
        "subject": payload.get("subject", subject),
        "preview_text": payload.get("preview_text", ""),
        "html": payload.get("html", ""),
        "text": payload.get("text", ""),
        "topics": topics,
        "cta": cta,
        "platform": "newsletter",
        "created_at": datetime.utcnow().isoformat(),
        "status": "draft",
        "file_path": file_path,
    }
    vault.insert("email_sequences", doc, doc_id=newsletter_id)

    return {
        "content_id": newsletter_id,
        "subject": doc["subject"],
        "file_path": file_path,
        "status": "saved",
        "collection": "email_sequences",
    }


# ── Email Sequence ──────────────────────────────────────────────────────

@business_tool(
    name="generate_email_sequence",
    description="Generate a drip email campaign sequence.",
    category="content",
)
async def generate_email_sequence(
    goal: str,
    emails: int = 3,
) -> Dict[str, Any]:
    """
    Generate a multi-email drip sequence and persist each email to disk and vault.

    Args:
        goal: Campaign goal (e.g. "onboard new users", "recover abandoned carts").
        emails: Number of emails in the sequence.

    Returns:
        Dict with sequence_id, emails list, file paths, and schedule recommendations.
    """
    if not goal:
        return {"error": "Goal is required"}

    system = (
        "You are a conversion-rate-optimization expert. "
        "Write high-converting email drip sequences. "
        "Each email needs a subject line, body, and clear CTA."
    )
    user = (
        f"Create a {emails}-email drip sequence for this goal: {goal}\n\n"
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "sequence_name": "Name of sequence",\n'
        '  "emails": [\n'
        '    {"day": 0, "subject": "...", "body": "...", "cta": "..."},\n'
        "    ...\n"
        "  ],\n"
        '  "schedule_recommendation": "Send every X days..."\n'
        "}"
    )

    raw = await _llm_generate(system, user, temperature=0.7)

    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group())
        else:
            payload = json.loads(raw)
    except Exception:
        payload = {
            "sequence_name": goal,
            "emails": [
                {
                    "day": i,
                    "subject": f"Email {i + 1} - {goal}",
                    "body": raw[:500] if i == 0 else "Follow-up content...",
                    "cta": "Learn More",
                }
                for i in range(emails)
            ],
            "schedule_recommendation": (
                f"Send 1 email every 2 days across {emails * 2} days."
            ),
        }

    sequence_id = f"seq_{uuid.uuid4().hex[:8]}"
    slug = _sanitize_slug(goal)
    email_list = payload.get("emails", [])
    file_paths: List[str] = []

    for idx, email in enumerate(email_list, start=1):
        email_text = (
            f"Subject: {email.get('subject', '')}\n"
            f"Day: {email.get('day', idx)}\n"
            f"CTA: {email.get('cta', '')}\n\n"
            f"{email.get('body', '')}"
        )
        fp = _write_to_disk(f"email/{slug}_email_{idx}.txt", email_text)
        file_paths.append(fp)

    doc = {
        "content_id": sequence_id,
        "goal": goal,
        "sequence_name": payload.get("sequence_name", goal),
        "emails": email_list,
        "email_count": len(email_list),
        "schedule_recommendation": payload.get("schedule_recommendation", ""),
        "platform": "email",
        "created_at": datetime.utcnow().isoformat(),
        "status": "draft",
        "file_paths": file_paths,
    }
    vault.insert("email_sequences", doc, doc_id=sequence_id)

    return {
        "content_id": sequence_id,
        "sequence_name": doc["sequence_name"],
        "email_count": doc["email_count"],
        "file_paths": file_paths,
        "status": "saved",
        "collection": "email_sequences",
    }


# ── SEO Optimization ────────────────────────────────────────────────────

@business_tool(
    name="optimize_for_seo",
    description="Rewrite existing content for better SEO performance.",
    category="content",
)
async def optimize_for_seo(
    content_id: str,
    target_keywords: List[str],
) -> Dict[str, Any]:
    """
    Retrieve a piece of content and rewrite it for SEO.

    Args:
        content_id: Vault document ID of the content to optimize.
        target_keywords: Keywords to emphasize.

    Returns:
        Dict with optimized content, SEO score estimate, and update status.
    """
    if not content_id or not target_keywords:
        return {"error": "content_id and target_keywords are required"}

    original = None
    collection_found = None
    for coll in ("blog_posts", "social_posts", "email_sequences"):
        doc = vault.get(coll, content_id)
        if doc:
            original = doc
            collection_found = coll
            break

    if not original:
        return {"error": f"Content {content_id} not found in any collection"}

    body = original.get("body", original.get("text", original.get("html", "")))
    title = original.get("title", original.get("subject", "Untitled"))
    keyword_str = ", ".join(target_keywords)

    system = (
        "You are an SEO specialist. Rewrite content to maximize search visibility "
        "while preserving readability and voice. Add headers, meta suggestions, "
        "and keyword density improvements."
    )
    user = (
        f"Original title: {title}\n"
        f"Target keywords: {keyword_str}\n\n"
        f"Original content:\n{body[:2000]}\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "title": "optimized title",\n'
        '  "body": "optimized content",\n'
        '  "meta_description": "...",\n'
        '  "seo_score_estimate": 85,\n'
        '  "changes_made": ["added H2", "increased keyword density", ...]\n'
        "}"
    )

    raw = await _llm_generate(system, user, temperature=0.5)

    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group())
        else:
            payload = json.loads(raw)
    except Exception:
        payload = {
            "title": title,
            "body": body,
            "meta_description": original.get("meta_description", ""),
            "seo_score_estimate": 50,
            "changes_made": ["failed to parse LLM response"],
        }

    optimized_id = f"seo_{uuid.uuid4().hex[:8]}"
    updates = {
        "optimized_version": {
            "content_id": optimized_id,
            "title": payload.get("title", title),
            "body": payload.get("body", body),
            "meta_description": payload.get("meta_description", ""),
            "seo_score_estimate": payload.get("seo_score_estimate", 70),
            "target_keywords": target_keywords,
            "changes_made": payload.get("changes_made", []),
            "optimized_at": datetime.utcnow().isoformat(),
        },
        "status": "optimized",
    }

    vault.update(collection_found, content_id, updates)

    vault.insert(
        "seo_keywords",
        {
            "content_id": content_id,
            "optimized_id": optimized_id,
            "target_keywords": target_keywords,
            "seo_score_estimate": payload.get("seo_score_estimate", 70),
            "optimized_at": datetime.utcnow().isoformat(),
        },
    )

    return {
        "original_content_id": content_id,
        "optimized_id": optimized_id,
        "collection": collection_found,
        "seo_score_estimate": payload.get("seo_score_estimate", 70),
        "changes_made": payload.get("changes_made", []),
        "status": "optimized",
    }


# ── Content Scheduling ──────────────────────────────────────────────────

@business_tool(
    name="schedule_content",
    description="Schedule a piece of content for publication on a platform.",
    category="content",
)
async def schedule_content(
    content_id: str,
    platform: str,
    publish_at: str,
) -> Dict[str, Any]:
    """
    Schedule content for future publication.

    Args:
        content_id: Vault document ID.
        platform: Target platform (blog, twitter, linkedin, newsletter, email).
        publish_at: ISO-8601 datetime string for publication.

    Returns:
        Dict with schedule confirmation and calendar entry ID.
    """
    if not content_id or not platform or not publish_at:
        return {"error": "content_id, platform, and publish_at are required"}

    exists = False
    source_collection = None
    for coll in ("blog_posts", "social_posts", "email_sequences"):
        if vault.get(coll, content_id):
            exists = True
            source_collection = coll
            break

    if not exists:
        return {"error": f"Content {content_id} not found"}

    entry_id = f"cal_{uuid.uuid4().hex[:8]}"
    doc = {
        "entry_id": entry_id,
        "content_id": content_id,
        "platform": platform.lower(),
        "publish_at": publish_at,
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat(),
        "source_collection": source_collection,
    }
    vault.insert("content_calendar", doc, doc_id=entry_id)

    if source_collection:
        vault.update(
            source_collection,
            content_id,
            {"status": "scheduled", "scheduled_for": publish_at},
        )

    return {
        "entry_id": entry_id,
        "content_id": content_id,
        "platform": platform,
        "publish_at": publish_at,
        "status": "scheduled",
        "collection": "content_calendar",
    }


# ── Analytics ───────────────────────────────────────────────────────────

@business_tool(
    name="get_content_performance",
    description="Retrieve performance analytics for a content piece.",
    category="content",
)
async def get_content_performance(content_id: str) -> Dict[str, Any]:
    """
    Get traffic and engagement analytics for a content piece.

    Args:
        content_id: Vault document ID.

    Returns:
        Dict with views, clicks, conversions, and engagement metrics.
    """
    if not content_id:
        return {"error": "content_id is required"}

    analytics = vault.find(
        "content_analytics",
        lambda d: d.get("content_id") == content_id,
        limit=1,
    )
    if analytics:
        return {
            "content_id": content_id,
            "found": True,
            "metrics": analytics[0],
        }

    if config.LIVE_MODE:
        return {
            "content_id": content_id,
            "found": False,
            "metrics": {},
            "message": "No analytics configured",
        }

    # Fallback: empty metrics in non-live mode so agents still receive a valid shape
    return {
        "content_id": content_id,
        "found": False,
        "metrics": {},
        "message": "No analytics data available",
    }
