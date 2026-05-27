"""
Generate real money-making assets directly.
Calls business tools with high-quality parameters to create deliverables.
"""
import os
import sys
import asyncio

os.environ["LIVE_MODE"] = "true"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "swarm-backend"))

from core.business_tools.registry import registry
from core.business_tools.vault import vault


async def main():
    print("=" * 70)
    print("GENERATING REAL MONEY ASSETS")
    print("=" * 70)
    print()

    # 1. Ebook about AI Automation
    print("[1] Generating ebook: AI Automation Mastery...")
    outline = await registry.execute("generate_ebook_outline", topic="AI Automation for Small Business", chapters=7)
    if "outline" in outline:
        ebook = await registry.execute("generate_ebook_content", outline=outline["outline"])
        print(f"    -> {ebook.get('filepath', 'saved to vault')}")

    # 2. Prompt pack for ChatGPT
    print("[2] Generating prompt pack: ChatGPT for Entrepreneurs...")
    prompts = await registry.execute("generate_prompt_pack", niche="entrepreneurship and business growth", count=15)
    print(f"    -> {prompts.get('filepath', 'saved to vault')}")

    # 3. Code template: Flask API starter
    print("[3] Generating code template: Flask API Starter...")
    code = await registry.execute("generate_code_template", project_type="flask_api", features=["JWT auth", "rate limiting", "OpenAPI docs"])
    print(f"    -> {code.get('directory', 'saved to vault')}")

    # 4. Micro-SaaS app: URL Shortener
    print("[4] Generating micro-app: URL Shortener with Analytics...")
    app = await registry.execute("generate_app_code", app_type="url_shortener", features=["analytics dashboard", "custom domains", "QR codes"], tech_stack="flask")
    print(f"    -> Files: {list(app.get('disk_paths', {}).keys()) if isinstance(app.get('disk_paths'), dict) else app.get('disk_paths', 'N/A')}")

    # 5. Blog post
    print("[5] Generating blog post: 10 AI Tools That Save 10 Hours Per Week...")
    blog = await registry.execute("generate_blog_post", topic="10 AI Tools That Save 10 Hours Per Week", keywords=["AI automation", "productivity tools", "time saving"], tone="professional", length="long")
    print(f"    -> {blog.get('filepath', 'saved to vault')}")

    # 6. Affiliate comparison article
    print("[6] Generating affiliate article: Notion vs Obsidian...")
    article = await registry.execute("generate_comparison_post", product_a="Notion", product_b="Obsidian", affiliate_links={"notion": "https://affiliate.notion.so", "obsidian": "https://obsidian.md/affiliate"})
    print(f"    -> {article.get('filepath', 'saved to vault')}")

    # 7. Lead list
    print("[7] Scraping leads: SaaS founders...")
    leads = await registry.execute("search_leads", query="SaaS founders startup CEOs", platform="linkedin", campaign_name="saas_outreach_may2026")
    print(f"    -> {leads.get('csv_path', 'saved to vault')}, count: {leads.get('count', 0)}")

    # 8. Email sequence
    print("[8] Generating email sequence: SaaS onboarding...")
    emails = await registry.execute("generate_email_sequence", goal="Convert trial users to paid SaaS customers", emails=5)
    print(f"    -> {emails.get('filepaths', 'saved to vault')}")

    # 9. Newsletter
    print("[9] Generating newsletter: AI Weekly Roundup...")
    newsletter = await registry.execute("generate_newsletter", subject="AI Weekly: 3 Tools That Just Changed Everything", topics=["Claude 4 rumors", "new OpenAI pricing", "open-source LLM breakthrough"], cta="Upgrade to Pro for full analysis")
    print(f"    -> {newsletter.get('filepath', 'saved to vault')}")

    # 10. Twitter thread
    print("[10] Generating Twitter thread: How I Built a $5k/mo Micro-SaaS...")
    thread = await registry.execute("generate_twitter_thread", topic="How I built a $5,000/month micro-SaaS in 30 days with AI", tweets=8)
    print(f"    -> {thread.get('filepath', 'saved to vault')}")

    print()
    print("=" * 70)
    print("DONE. Check these directories for your real deliverables:")
    print("  products/assets/    - ebooks, prompt packs, code templates")
    print("  products/apps/      - runnable micro-SaaS apps")
    print("  content/blog/       - blog posts ready to publish")
    print("  content/affiliate/  - comparison articles with affiliate links")
    print("  content/email/      - email sequences and newsletters")
    print("  content/social/     - Twitter threads")
    print("  leads/              - CSV lead lists")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
