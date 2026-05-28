#!/usr/bin/env python3
"""
overnight_asset_generator.py
============================
Runs overnight using local Ollama (zero API cost) to generate:
- New affiliate comparison articles
- A lead magnet ebook
- Email nurture sequences
- Micro-SaaS landing page copy

Usage:
    python tools/overnight_asset_generator.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
OUTPUT_DIR = Path("content/overnight")

def _ollama_generate(prompt: str, model: str = "llama3.1:8b", max_tokens: int = 2000) -> str:
    """Generate text via Ollama OpenAI-compatible endpoint."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR: {e}]"


def generate_article(topic: str, output_path: Path) -> None:
    """Generate a full affiliate comparison article."""
    prompt = f"""Write a comprehensive affiliate comparison blog post about: {topic}

Requirements:
- 800-1200 words
- Objective, balanced tone
- Include: Introduction, Feature Comparison table (markdown), Pros/Cons for each, Verdict/Recommendation
- Add an affiliate disclosure footer: "Disclosure: This post contains affiliate links. We earn a commission at no extra cost to you."
- Use markdown formatting with H2 headers
- End with a CTA: "Which tool do you prefer? Let us know in the comments."

Return ONLY the article content in markdown. No extra commentary."""

    print(f"[gen] Article: {topic}")
    content = _ollama_generate(prompt, model="qwen3:14b", max_tokens=2500)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"[gen] Saved: {output_path}")


def generate_lead_magnet(output_path: Path) -> None:
    """Generate a lead magnet ebook/PDF content."""
    prompt = """Write a short but valuable lead magnet ebook titled "The 2025 Software Stack Buyer's Guide"

Target audience: Small business owners and freelancers choosing software tools.

Structure:
- Title page
- Introduction (why the right software matters)
- Chapter 1: Project Management (Notion vs Trello vs Asana)
- Chapter 2: Design (Canva vs Adobe Express vs Figma)
- Chapter 3: Communication (Slack vs Discord vs Microsoft Teams)
- Chapter 4: File Storage (Google Drive vs Dropbox vs OneDrive)
- Chapter 5: Website Builders (WordPress vs Webflow vs Squarespace)
- Quick-reference comparison chart for all tools
- Conclusion with affiliate disclosure

Return as markdown. Be specific with pricing and features."""

    print("[gen] Lead magnet ebook...")
    content = _ollama_generate(prompt, model="qwen3:14b", max_tokens=3000)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"[gen] Saved: {output_path}")


def generate_email_sequence(output_dir: Path) -> None:
    """Generate a 5-email nurture sequence."""
    emails = [
        ("email_1_welcome.txt", "Write a welcome email for new Substack subscribers to OrbStudio's Substack. Introduce the publication, set expectations (1 comparison post + 1 deal alert per week), and ask them to reply with their biggest software buying challenge."),
        ("email_2_value.txt", "Write an email sharing the 'Top 5 Free Tools Every Freelancer Needs in 2025'. Include brief descriptions and affiliate links (placeholder: {{AFFILIATE_LINK}}). End with a question to drive replies."),
        ("email_3_social_proof.txt", "Write an email about a reader who saved $200/year by switching software after reading our comparison. Include a testimonial template and link to our best comparison post."),
        ("email_4_soft_pitch.txt", "Write an email introducing our lead magnet '2025 Software Stack Buyer's Guide' as a free download. Explain the value and include a download link placeholder: {{DOWNLOAD_LINK}}."),
        ("email_5_deal_alert.txt", "Write a deal alert email about current software discounts (Black Friday style, but for regular promos). Include urgency but be honest. Link placeholders: {{DEAL_LINKS}}."),
    ]

    for filename, prompt in emails:
        print(f"[gen] Email: {filename}")
        content = _ollama_generate(prompt, model="llama3.1:8b", max_tokens=1500)
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        print(f"[gen] Saved: {path}")


def generate_landing_page(output_path: Path) -> None:
    """Generate HTML landing page copy for a micro-SaaS or lead magnet."""
    prompt = """Write a high-converting landing page for a free tool called "StackCompare" — a simple web app that compares software tools side-by-side.

Return as HTML with embedded CSS. Include:
- Hero section with headline, subheadline, and email capture form
- 3 feature sections with icons (use emoji)
- Social proof section (testimonial placeholders)
- FAQ section (5 questions)
- Footer with affiliate disclosure

Style: Clean, modern, single-page. Use inline CSS. Mobile-responsive basics."""

    print("[gen] Landing page...")
    content = _ollama_generate(prompt, model="qwen3:14b", max_tokens=2500)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"[gen] Saved: {output_path}")


def main():
    print("=" * 60)
    print("OVERNIGHT ASSET GENERATOR")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generate 3 new comparison articles
    articles = [
        ("Notion vs Trello vs Asana: Best Project Management Tool 2025", "articles/notion-vs-trello-vs-asana.md"),
        ("Canva vs Adobe Express vs Figma: Best Design Tool for Non-Designers", "articles/canva-vs-adobe-express-vs-figma.md"),
        ("Google Drive vs Dropbox vs OneDrive: Best Cloud Storage 2025", "articles/google-drive-vs-dropbox-vs-onedrive.md"),
    ]

    for topic, filename in articles:
        generate_article(topic, OUTPUT_DIR / filename)
        time.sleep(2)  # Brief pause between requests

    # 2. Lead magnet ebook
    generate_lead_magnet(OUTPUT_DIR / "lead_magnet/software_buyers_guide_2025.md")
    time.sleep(2)

    # 3. Email sequence
    generate_email_sequence(OUTPUT_DIR / "email_sequence")
    time.sleep(2)

    # 4. Landing page
    generate_landing_page(OUTPUT_DIR / "landing_page/stackcompare.html")

    print("\n" + "=" * 60)
    print(f"DONE: {datetime.now().isoformat()}")
    print(f"Assets saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
