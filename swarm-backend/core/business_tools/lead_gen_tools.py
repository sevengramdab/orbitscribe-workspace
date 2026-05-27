"""
Lead Generation Tools

Business automation tools for scraping, enriching, scoring, and outreach.
All functions are registered via the @business_tool decorator so agents can
discover and execute them through the BusinessToolRegistry.
"""

import csv
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault
from core.model_router import router

# ── Constants ───────────────────────────────────────────────────────────

VALID_PIPELINE_STAGES = ["new", "contacted", "qualified", "proposal", "closed"]

_PLATFORM_MODIFIERS = {
    "linkedin": "site:linkedin.com/in",
    "twitter": "site:twitter.com OR site:x.com",
    "general": "",
}

# ── Internal helpers ────────────────────────────────────────────────────


def _perform_web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo HTML and return structured results.

    This is a lightweight, keyless search approach.  If DuckDuckGo changes
    their HTML layout the call degrades gracefully.
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Dict[str, str]] = []
        for result in soup.select(".result"):
            title_el = result.select_one(".result__title")
            snippet_el = result.select_one(".result__snippet")
            href_el = result.select_one(".result__url")
            if title_el and snippet_el:
                results.append(
                    {
                        "title": title_el.get_text(strip=True),
                        "url": href_el.get_text(strip=True) if href_el else "",
                        "snippet": snippet_el.get_text(strip=True),
                    }
                )
            if len(results) >= num_results:
                break
        return results
    except Exception as exc:
        return [{"error": f"Web search failed: {exc}"}]


def _extract_name_from_title(title: str) -> str:
    """Heuristic extraction of a person's name from a search result title."""
    title = (
        title.replace(" | LinkedIn", "")
        .replace(" | Twitter", "")
        .replace(" on X", "")
    )
    parts = title.split(" - ")[0].split(" | ")[0]
    return parts.strip()


def _update_pipeline_aggregate(lead_id: str, from_stage: str, to_stage: str) -> None:
    """Maintain a lightweight pipeline snapshot collection for quick querying."""
    doc = vault.get("pipeline_stages", "pipeline_snapshot")
    if not doc:
        doc = {
            "new": [],
            "contacted": [],
            "qualified": [],
            "proposal": [],
            "closed": [],
        }
        vault.insert("pipeline_stages", doc, doc_id="pipeline_snapshot")
        doc = vault.get("pipeline_stages", "pipeline_snapshot")

    if doc:
        if from_stage in doc:
            doc[from_stage] = [lid for lid in doc[from_stage] if lid != lead_id]
        if to_stage in doc and lead_id not in doc[to_stage]:
            doc[to_stage].append(lead_id)
        vault.update(
            "pipeline_stages",
            "pipeline_snapshot",
            {
                from_stage: doc.get(from_stage, []),
                to_stage: doc.get(to_stage, []),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )


# ── Business Tools ──────────────────────────────────────────────────────


@business_tool(
    name="search_leads",
    description="Search the web for potential leads in a target niche/platform and export to CSV.",
    category="lead_generation",
)
def search_leads(
    query: str, platform: str = "linkedin", campaign_name: str = "default"
) -> Dict[str, Any]:
    """
    Perform a web search to discover potential leads.

    Discovered leads are exported to ``leads/{campaign_name}_{date}.csv`` and
    persisted to the vault as a secondary store.

    Args:
        query: Search query describing the target niche or persona.
        platform: Platform hint (linkedin, twitter, general).
        campaign_name: Campaign label used for the CSV filename.

    Returns:
        Dict with discovered leads, raw search results, and CSV path.
    """
    modifier = _PLATFORM_MODIFIERS.get(platform, "")
    full_query = f"{modifier} {query}".strip() if modifier else query

    raw_results = _perform_web_search(full_query, num_results=8)

    leads: List[Dict[str, Any]] = []
    for res in raw_results:
        if "error" in res:
            continue
        lead = {
            "name": _extract_name_from_title(res.get("title", "")),
            "title": res.get("title", ""),
            "source_url": res.get("url", ""),
            "source_platform": platform,
            "snippet": res.get("snippet", ""),
            "query": query,
            "discovered_at": datetime.utcnow().isoformat(),
            "stage": "new",
            "score": 0,
        }
        leads.append(lead)

    # ── Export to CSV ────────────────────────────────────────────────────
    date_str = datetime.utcnow().strftime("%Y%m%d")
    csv_filename = f"{campaign_name}_{date_str}.csv"
    leads_dir = os.path.join(config.WORKSPACE_ROOT, "leads")
    os.makedirs(leads_dir, exist_ok=True)
    csv_path = os.path.join(leads_dir, csv_filename)

    fieldnames = [
        "name",
        "title",
        "source_url",
        "source_platform",
        "snippet",
        "query",
        "discovered_at",
        "stage",
        "score",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)

    # ── Secondary vault persistence ─────────────────────────────────────
    for lead in leads:
        vault.insert("leads", lead)

    return {
        "query": full_query,
        "platform": platform,
        "leads_found": len(leads),
        "leads": leads,
        "raw_results": raw_results,
        "csv_export": csv_path,
    }


@business_tool(
    name="enrich_lead",
    description="Enrich a lead record with additional data via LLM and web search.",
    category="lead_generation",
)
async def enrich_lead(
    lead_id: str,
    email: Optional[str] = None,
    company: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich an existing lead with additional contextual data.

    Args:
        lead_id: Vault document ID of the lead.
        email: Optional known email to attach.
        company: Optional known company to attach.

    Returns:
        Dict with enrichment results and updated lead data.
    """
    lead = vault.get("leads", lead_id)
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    updates: Dict[str, Any] = {}
    if email:
        updates["email"] = email
    if company:
        updates["company"] = company

    # Web search for additional context
    search_query = f"{lead.get('name', '')} {company or lead.get('company', '')}".strip()
    web_results: List[Dict[str, str]] = []
    if search_query:
        web_results = _perform_web_search(search_query, num_results=3)

    # LLM synthesis
    context = json.dumps(
        {
            "lead": lead,
            "web_results": web_results,
            "provided_email": email,
            "provided_company": company,
        },
        indent=2,
        default=str,
    )

    system_prompt = (
        "You are a lead research analyst. Given raw lead data and web search snippets, "
        "extract or infer: job_title, company_size, industry, location, and a brief summary. "
        "Respond ONLY in JSON with keys: job_title, company_size, industry, location, summary."
    )

    try:
        llm_text = await router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            temperature=0.2,
        )
        json_match = re.search(r"\{.*\}", llm_text, re.DOTALL)
        if json_match:
            enrichment = json.loads(json_match.group())
            updates.update(enrichment)
    except Exception as exc:
        updates["enrichment_error"] = str(exc)

    updates["enriched"] = True
    updates["enriched_at"] = datetime.utcnow().isoformat()
    updates["enrichment_sources"] = [
        r.get("url", "") for r in web_results if "error" not in r
    ]

    success = vault.update("leads", lead_id, updates)
    return {
        "lead_id": lead_id,
        "success": success,
        "updates": updates,
        "web_results": web_results,
    }


@business_tool(
    name="score_lead",
    description="Calculate a 0-100 lead score based on available signals.",
    category="lead_generation",
)
def score_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a lead based on data completeness and quality signals.

    Scoring rubric:
        +20  has email
        +10  has phone
        +10  linkedin source / linkedin_url
        +10  has company
        +10  has job_title
        +10  is enriched
        + 5  meaningful company_size
        -20  missing name
        -10  missing company
        -10  no contact info at all

    Args:
        lead: Lead document dict.

    Returns:
        Dict with ``score`` (0-100), ``signals`` list, and ``lead_id``.
    """
    score = 50
    signals: List[str] = []

    # Positive signals
    if lead.get("email"):
        score += 20
        signals.append("has_email")
    if lead.get("phone"):
        score += 10
        signals.append("has_phone")
    if lead.get("linkedin_url") or lead.get("source_platform") == "linkedin":
        score += 10
        signals.append("linkedin_source")
    if lead.get("company"):
        score += 10
        signals.append("has_company")
    if lead.get("job_title"):
        score += 10
        signals.append("has_job_title")
    if lead.get("enriched"):
        score += 10
        signals.append("is_enriched")
    company_size = lead.get("company_size", "")
    if company_size and company_size not in ("unknown", "1-10", ""):
        score += 5
        signals.append("meaningful_company_size")

    # Negative signals
    if not lead.get("name"):
        score -= 20
        signals.append("missing_name")
    if not lead.get("company"):
        score -= 10
        signals.append("missing_company")
    if not lead.get("email") and not lead.get("phone"):
        score -= 10
        signals.append("no_contact_info")

    final_score = max(0, min(100, score))
    return {
        "score": final_score,
        "signals": signals,
        "lead_id": lead.get("_id"),
    }


@business_tool(
    name="draft_outreach_email",
    description="Generate a personalized outreach email for a lead, save it to disk, and persist to the vault.",
    category="lead_generation",
)
async def draft_outreach_email(
    lead: Dict[str, Any],
    product: str,
    tone: str = "professional",
) -> Dict[str, Any]:
    """
    Draft a personalized cold outreach email.

    The drafted email is written to ``leads/{lead_id}_outreach.txt`` and
    stored in the vault as a secondary record.

    Args:
        lead: Lead document dict.
        product: Product or service description.
        tone: Email tone (professional, casual, friendly, assertive).

    Returns:
        Dict with subject, body, filepath, and personalization notes.
    """
    name = lead.get("name", "there")
    company = lead.get("company", "your company")
    job_title = lead.get("job_title", "your role")
    industry = lead.get("industry", "your industry")

    system_prompt = (
        f"You are a world-class sales copywriter. Write a concise, personalized cold outreach email. "
        f"Tone: {tone}. Do not use generic fluff. Reference specific details about the recipient. "
        f"Respond ONLY in JSON with keys: subject, body, personalization_notes."
    )

    user_prompt = (
        f"Recipient: {name}, {job_title} at {company} ({industry})\n"
        f"Product/Service: {product}\n"
        f"Lead Snippet: {lead.get('snippet', '')}\n"
        f"Write a short, compelling email."
    )

    try:
        llm_text = await router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        json_match = re.search(r"\{.*\}", llm_text, re.DOTALL)
        if json_match:
            email_data = json.loads(json_match.group())
        else:
            email_data = {
                "subject": f"Quick question, {name}",
                "body": llm_text,
                "personalization_notes": "Parsed from raw LLM output.",
            }
    except Exception as exc:
        email_data = {
            "subject": f"Quick question, {name}",
            "body": (
                f"Hi {name},\n\n"
                f"I wanted to reach out about {product}.\n\n"
                f"Best regards,"
            ),
            "personalization_notes": f"LLM failed: {exc}",
        }

    # ── Write to disk ────────────────────────────────────────────────────
    lead_id = lead.get("_id") or lead.get("id") or "unknown"
    leads_dir = os.path.join(config.WORKSPACE_ROOT, "leads")
    os.makedirs(leads_dir, exist_ok=True)
    filepath = os.path.join(leads_dir, f"{lead_id}_outreach.txt")

    email_text = (
        f"Subject: {email_data.get('subject', '')}\n"
        f"To: {name} <{lead.get('email', 'unknown')}>\n"
        f"Company: {company}\n\n"
        f"{email_data.get('body', '')}"
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(email_text)

    # ── Secondary vault persistence ─────────────────────────────────────
    vault_doc: Dict[str, Any] = {
        "lead_id": lead_id,
        "email": email_data,
        "tone": tone,
        "product": product,
        "filepath": filepath,
        "created_at": datetime.utcnow().isoformat(),
    }
    vault.insert("outreach_emails", vault_doc)

    return {
        "lead_id": lead_id,
        "email": email_data,
        "tone": tone,
        "product": product,
        "filepath": filepath,
    }


@business_tool(
    name="create_campaign",
    description="Create and persist an outreach campaign in the vault.",
    category="lead_generation",
)
def create_campaign(
    name: str,
    target_niche: str,
    message_template: str,
) -> Dict[str, Any]:
    """
    Save a new outreach campaign to the unified vault.

    Args:
        name: Campaign name.
        target_niche: Target market niche.
        message_template: Base message template.

    Returns:
        Dict with campaign_id and created campaign data.
    """
    doc: Dict[str, Any] = {
        "name": name,
        "target_niche": target_niche,
        "message_template": message_template,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
        "leads_contacted": 0,
        "leads_converted": 0,
    }
    campaign_id = vault.insert("outreach_campaigns", doc)
    return {
        "campaign_id": campaign_id,
        "campaign": doc,
    }


@business_tool(
    name="move_lead_stage",
    description="Move a lead to a new pipeline stage.",
    category="lead_generation",
)
def move_lead_stage(lead_id: str, stage: str) -> Dict[str, Any]:
    """
    Update a lead's pipeline stage.

    Args:
        lead_id: Vault document ID.
        stage: One of new, contacted, qualified, proposal, closed.

    Returns:
        Dict with success flag and previous stage.
    """
    if stage not in VALID_PIPELINE_STAGES:
        return {
            "error": f"Invalid stage '{stage}'. Must be one of {VALID_PIPELINE_STAGES}",
            "lead_id": lead_id,
        }

    lead = vault.get("leads", lead_id)
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    previous_stage = lead.get("stage", "new")
    stage_entry = {
        "from": previous_stage,
        "to": stage,
        "moved_at": datetime.utcnow().isoformat(),
    }
    updates = {
        "stage": stage,
        "stage_history": lead.get("stage_history", []) + [stage_entry],
    }
    success = vault.update("leads", lead_id, updates)
    _update_pipeline_aggregate(lead_id, previous_stage, stage)

    return {
        "lead_id": lead_id,
        "success": success,
        "previous_stage": previous_stage,
        "new_stage": stage,
    }


@business_tool(
    name="get_leads_by_stage",
    description="Query leads filtered by pipeline stage.",
    category="lead_generation",
)
def get_leads_by_stage(stage: str) -> Dict[str, Any]:
    """
    Retrieve all leads in a given pipeline stage.

    Args:
        stage: Pipeline stage to filter by.

    Returns:
        Dict with list of leads and count.
    """
    leads = vault.find(
        "leads",
        filter_fn=lambda doc: doc.get("stage", "new") == stage,
        limit=500,
    )
    return {
        "stage": stage,
        "count": len(leads),
        "leads": leads,
    }
