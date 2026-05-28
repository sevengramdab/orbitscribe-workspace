#!/usr/bin/env python3
"""
account_setup_helper.py
=======================
Generates pre-filled profile text, API config templates, and account
creation checklists for Medium, Substack, and ClickBank.

Usage:
    python tools/account_setup_helper.py
    python tools/account_setup_helper.py --platform medium
    python tools/account_setup_helper.py --export-json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path("content/account_setup")

PROFILE_TEMPLATES = {
    "medium": {
        "bio_short": (
            "Tech enthusiast comparing software, VPNs & hosting so you don't have to. "
            "Transparent reviews. Affiliate links = no extra cost to you."
        ),
        "bio_alt": (
            "Honest reviews of the tools that power the web. "
            "Software, security & hosting — tested, compared, explained."
        ),
        "about_page": """# About This Publication

I compare software, VPNs, web hosting, and design tools so you can make informed decisions without spending hours researching.

## What I Cover
- **Software**: Photo editors, design suites, productivity tools
- **VPNs**: Privacy, security, streaming access
- **Web Hosting**: Shared, VPS, cloud — speed & value
- **Design**: Graphics, video, UI/UX tools

## Affiliate Disclosure
Some posts contain affiliate links. If you purchase through them, I earn a commission at no extra cost to you. I only recommend products I research thoroughly.

## Contact
{email}
""",
        "publication_names": [
            "The Tool Comparator",
            "Software Stack Weekly",
            "Build & Compare",
        ],
    },
    "substack": {
        "description": (
            "Honest, tested comparisons of the software that runs the internet. "
            "VPNs, hosting, design tools — broken down so you choose with confidence."
        ),
        "about_page": """## What This Is

A no-BS newsletter comparing software, VPNs, web hosting, and design tools. I test, research, and explain so you don't have to waste money on the wrong product.

## What You Get
- **Weekly deep-dives**: Side-by-side comparisons with real data
- **Buying guides**: What to look for, what to avoid, what to pay
- **Deal alerts**: When top tools go on sale
- **Industry news**: What matters for builders and creators

## The Fine Print
Some posts contain affiliate links. If you buy through them, I earn a commission — at zero extra cost to you. I only recommend products I've researched. Full disclosure in every post.

## Contact
Reply to any email or reach me at: {email}
""",
        "email_footer": """---
*Disclosure: This email contains affiliate links. If you purchase through these links, I earn a commission at no extra cost to you. I only recommend products I research and trust.*
""",
        "publication_names": [
            "The Tool Comparator",
            "Software Stack Weekly",
            "VPN & Hosting Insider",
            "Build & Compare",
        ],
    },
    "clickbank": {
        "nickname_suggestions": [
            "techcompare",
            "toolreviewer",
            "softstack",
            "vpnhostpro",
        ],
        "tracking_id_base": "TCSW",
    },
}

API_CONFIG_TEMPLATES = {
    "medium": {
        "comment": "Medium API v1 integration token (get from Settings -> Integration tokens)",
        "MEDIUM_API_TOKEN": "your_medium_integration_token_here",
        "MEDIUM_API_URL": "https://api.medium.com/v1",
    },
    "substack": {
        "comment": "Substack uses email/web publishing. No API token needed for basic publishing.",
        "SUBSTACK_URL": "https://your-publication.substack.com",
        "SUBSTACK_PUBLICATION_ID": "your_publication_id_if_using_api",
    },
    "clickbank": {
        "comment": "ClickBank API keys (get from Account Settings -> API)",
        "CLICKBANK_ACCOUNT_NICKNAME": "your_nickname",
        "CLICKBANK_DEVELOPER_KEY": "your_developer_api_key",
        "CLICKBANK_API_SECRET": "your_api_secret",
        "CLICKBANK_CLIENT_ID": "your_clerk_client_id",
        "CLICKBANK_CLIENT_SECRET": "your_clerk_client_secret",
    },
}


def _generate_medium_texts(email: str) -> dict:
    tmpl = PROFILE_TEMPLATES["medium"]
    return {
        "bio_short": tmpl["bio_short"],
        "bio_alt": tmpl["bio_alt"],
        "about_page": tmpl["about_page"].format(email=email),
        "publication_names": tmpl["publication_names"],
        "optimal_tags": [
            "Technology",
            "Software",
            "VPN",
            "Web Hosting",
            "Product Review",
        ],
    }


def _generate_substack_texts(email: str) -> dict:
    tmpl = PROFILE_TEMPLATES["substack"]
    return {
        "description": tmpl["description"],
        "about_page": tmpl["about_page"].format(email=email),
        "email_footer": tmpl["email_footer"],
        "publication_names": tmpl["publication_names"],
        "optimal_tags": [
            "Technology",
            "Software Engineering",
            "Cybersecurity",
            "Web Development",
            "Productivity",
        ],
    }


def _generate_clickbank_texts() -> dict:
    tmpl = PROFILE_TEMPLATES["clickbank"]
    return {
        "nickname_suggestions": tmpl["nickname_suggestions"],
        "tracking_id_base": tmpl["tracking_id_base"],
        "ftc_disclosure": (
            "This post contains affiliate links. We earn a commission when you "
            "purchase through these links, at no extra cost to you."
        ),
        "niche_search_terms": [
            "software", "SaaS", "productivity tools", "automation",
            "VPN", "privacy", "cybersecurity", "online security",
            "website builder", "hosting", "WordPress", "domain",
            "Photoshop", "design", "graphics", "video editing",
        ],
    }


def generate_all(email: str) -> dict:
    return {
        "medium": _generate_medium_texts(email),
        "substack": _generate_substack_texts(email),
        "clickbank": _generate_clickbank_texts(),
        "api_templates": API_CONFIG_TEMPLATES,
    }


def write_text_files(data: dict, email: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Medium
    medium = data["medium"]
    (OUTPUT_DIR / "medium_bio_short.txt").write_text(medium["bio_short"], encoding="utf-8")
    (OUTPUT_DIR / "medium_bio_alt.txt").write_text(medium["bio_alt"], encoding="utf-8")
    (OUTPUT_DIR / "medium_about_page.md").write_text(medium["about_page"], encoding="utf-8")

    # Substack
    substack = data["substack"]
    (OUTPUT_DIR / "substack_description.txt").write_text(substack["description"], encoding="utf-8")
    (OUTPUT_DIR / "substack_about_page.md").write_text(substack["about_page"], encoding="utf-8")
    (OUTPUT_DIR / "substack_email_footer.txt").write_text(substack["email_footer"], encoding="utf-8")

    # ClickBank
    cb = data["clickbank"]
    (OUTPUT_DIR / "clickbank_nicknames.txt").write_text(
        "\n".join(cb["nickname_suggestions"]), encoding="utf-8"
    )
    (OUTPUT_DIR / "clickbank_ftc_disclosure.txt").write_text(cb["ftc_disclosure"], encoding="utf-8")

    # API config template
    api_lines = ["# Add these to your .env file after creating accounts", ""]
    for platform, cfg in data["api_templates"].items():
        api_lines.append(f"# --- {platform.upper()} ---")
        if "comment" in cfg:
            api_lines.append(f"# {cfg.pop('comment')}")
        for key, val in cfg.items():
            api_lines.append(f'{key}="{val}"')
        api_lines.append("")
    (OUTPUT_DIR / "api_keys_template.env").write_text("\n".join(api_lines), encoding="utf-8")

    print(f"[helper] Wrote {len(list(OUTPUT_DIR.iterdir()))} files to {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Account setup helper")
    parser.add_argument("--email", default="joshldyer@gmail.com", help="Contact email for profiles")
    parser.add_argument("--platform", choices=["medium", "substack", "clickbank", "all"], default="all")
    parser.add_argument("--export-json", action="store_true", help="Dump everything as JSON")
    args = parser.parse_args()

    data = generate_all(args.email)

    if args.platform != "all":
        filtered = {args.platform: data[args.platform]}
        data = filtered

    if args.export_json:
        print(json.dumps(data, indent=2))
        return

    write_text_files(data, args.email)

    # Print summary
    print("\n" + "=" * 60)
    print("ACCOUNT SETUP HELPER - READY TO COPY-PASTE")
    print("=" * 60)

    if args.platform in ("all", "medium"):
        print("\n[MEDIUM]")
        print(f"  Bio (short): {data['medium']['bio_short'][:60]}...")
        print(f"  About page:  {OUTPUT_DIR / 'medium_about_page.md'}")
        print(f"  Tags:        {', '.join(data['medium']['optimal_tags'])}")

    if args.platform in ("all", "substack"):
        print("\n[SUBSTACK]")
        print(f"  Description: {data['substack']['description'][:60]}...")
        print(f"  About page:  {OUTPUT_DIR / 'substack_about_page.md'}")
        print(f"  Tags:        {', '.join(data['substack']['optimal_tags'])}")

    if args.platform in ("all", "clickbank"):
        print("\n[CLICKBANK]")
        print(f"  Nicknames:   {', '.join(data['clickbank']['nickname_suggestions'])}")
        print(f"  Disclosure:  {data['clickbank']['ftc_disclosure'][:60]}...")

    print(f"\n[API Template]: {OUTPUT_DIR / 'api_keys_template.env'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
