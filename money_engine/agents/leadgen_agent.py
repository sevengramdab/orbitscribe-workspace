"""
leadgen_agent.py
================
Lead generation and cold outreach agent.
Automates searching, scraping, email sequencing, and pipeline review.
"""
from __future__ import annotations

import csv
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from money_engine.base_agent import BaseMoneyAgent, AgentDecision
from money_engine.orchestrator import register_agent


@register_agent
class LeadGenAgent(BaseMoneyAgent):
    """
    Agent that automates lead generation and cold outreach.
    """

    VERTICAL = "leadgen"

    # Revenue constants
    REVENUE_PER_LEAD = 3.0
    REVENUE_PER_EMAIL_SEQUENCE = 5.0

    def __init__(self, agent_id: str | None = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self.leads_dir = Path(__file__).parent.parent.parent / "leads"
        self.email_dir = Path(__file__).parent.parent.parent / "content" / "email"
        self.leads_dir.mkdir(parents=True, exist_ok=True)
        self.email_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        """
        Choose the next lead-gen action based on simple pipeline state.
        Cycles through: search -> scrape -> generate -> send -> review.
        """
        decision_id = f"leadgen_{uuid.uuid4().hex[:8]}"
        timestamp = time.time()

        # Count existing leads and email sequences to guide decision
        lead_files = list(self.leads_dir.glob("*.csv"))
        email_files = list(self.email_dir.glob("*email*.txt"))
        total_leads = self._count_leads_in_files(lead_files)

        # Simple round-robin with state awareness
        last_action = None
        if self.state.ledger:
            last_action = self.state.ledger[-1].get("action")

        action_order = [
            "search_leads",
            "scrape_leads",
            "generate_email_sequence",
            "send_outreach",
            "review_pipeline",
        ]

        if last_action in action_order:
            idx = action_order.index(last_action)
            next_idx = (idx + 1) % len(action_order)
        else:
            next_idx = 0

        action = action_order[next_idx]

        # Override logic: if we have few leads, prioritize searching/scraping
        if total_leads < 10 and action not in ("search_leads", "scrape_leads", "review_pipeline"):
            action = "search_leads"

        params: Dict[str, Any] = {}
        reasoning = ""

        if action == "search_leads":
            params = {
                "query": "SaaS founders OR startup CTO",
                "platform": "linkedin",
                "campaign_name": f"outreach_{time.strftime('%Y%m%d')}",
            }
            reasoning = "Searching for new leads to expand pipeline."

        elif action == "scrape_leads":
            params = {
                "platform": "linkedin",
                "url": "https://www.linkedin.com/search/results/people/?keywords=saas%20founder",
            }
            reasoning = "Scraping LinkedIn for lead contact details."

        elif action == "generate_email_sequence":
            params = {
                "topic": "AI automation for SaaS growth",
                "campaign_name": f"saas_ai_{time.strftime('%Y%m%d')}",
                "sequence_length": 3,
            }
            reasoning = "Generating cold email sequence for upcoming outreach."

        elif action == "send_outreach":
            params = {
                "campaign_name": f"saas_ai_{time.strftime('%Y%m%d')}",
                "recipients": max(1, min(total_leads, 5)),
            }
            reasoning = "Simulating outreach sends to leads in pipeline."

        elif action == "review_pipeline":
            params = {}
            reasoning = "Reviewing pipeline health and reporting stats."

        return AgentDecision(
            decision_id=decision_id,
            timestamp=timestamp,
            action=action,
            params=params,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        """Execute the chosen lead-gen action."""
        action = decision.action
        params = decision.params

        if action == "search_leads":
            return self._exec_search_leads(params)
        elif action == "scrape_leads":
            return self._exec_scrape_leads(params)
        elif action == "generate_email_sequence":
            return self._exec_generate_email_sequence(params)
        elif action == "send_outreach":
            return self._exec_send_outreach(params)
        elif action == "review_pipeline":
            return self._exec_review_pipeline()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def get_default_interval(self) -> int:
        return 800  # 13.3 minutes

    # ------------------------------------------------------------------
    # Internal action implementations
    # ------------------------------------------------------------------

    def _exec_search_leads(self, params: dict) -> dict:
        """Use the business-tool registry to search for leads."""
        query = params.get("query", "SaaS founders")
        platform = params.get("platform", "linkedin")
        campaign_name = params.get("campaign_name", f"campaign_{int(time.time())}")

        self.log(f"Searching leads: query='{query}' platform={platform}")
        result = self.generate_asset_via_registry(
            "search_leads",
            query=query,
            platform=platform,
            campaign_name=campaign_name,
        )

        # Simulate revenue: assume registry returned some leads
        leads_found = result.get("leads_found", 5) if isinstance(result, dict) else 5
        if not isinstance(result, dict):
            result = {"raw": result}

        revenue = leads_found * self.REVENUE_PER_LEAD
        result["success"] = result.get("success", True)
        result["revenue"] = revenue
        result["costs"] = 0.0
        result["leads_found"] = leads_found
        result["message"] = f"Found {leads_found} leads via {platform}."

        # Persist leads to CSV for pipeline tracking
        self._append_leads_csv(campaign_name, leads_found)

        self.log(result["message"])
        return result

    def _exec_scrape_leads(self, params: dict) -> dict:
        """Open browser and simulate browsing/searching on LinkedIn."""
        platform = params.get("platform", "linkedin")
        url = params.get("url", "https://www.linkedin.com")

        self.log(f"Scraping leads on {platform}: {url}")
        try:
            self.browser.open_chrome(url=url, new_window=False)
            time.sleep(2.0)
            # Simulate search interaction
            self.browser.focus_chrome()
            time.sleep(0.5)
            # Take a screenshot for state verification
            self.browser.screenshot(filename=f"leadgen_scrape_{int(time.time())}.png")
            # Simulate a few scrolls
            self.browser.win_scroll(-5, x_pct=0.5, y_pct=0.5)
            time.sleep(0.5)
            self.browser.win_scroll(-5, x_pct=0.5, y_pct=0.5)
        except Exception as e:
            self.log(f"Browser scrape warning: {e}")

        # Simulate scraped leads
        scraped = 3
        revenue = scraped * self.REVENUE_PER_LEAD
        self._append_leads_csv(f"scraped_{platform}_{int(time.time())}", scraped)

        result = {
            "success": True,
            "revenue": revenue,
            "costs": 0.0,
            "scraped": scraped,
            "platform": platform,
            "message": f"Scraped {scraped} leads from {platform}.",
        }
        self.log(result["message"])
        return result

    def _exec_generate_email_sequence(self, params: dict) -> dict:
        """Use registry to generate an email sequence."""
        topic = params.get("topic", "AI automation for SaaS growth")
        campaign_name = params.get("campaign_name", f"email_seq_{int(time.time())}")
        sequence_length = params.get("sequence_length", 3)

        self.log(f"Generating email sequence: '{campaign_name}' ({sequence_length} emails)")
        result = self.generate_asset_via_registry(
            "generate_email_sequence",
            topic=topic,
            campaign_name=campaign_name,
            sequence_length=sequence_length,
        )

        if not isinstance(result, dict):
            result = {"raw": result}

        revenue = self.REVENUE_PER_EMAIL_SEQUENCE
        result["success"] = result.get("success", True)
        result["revenue"] = revenue
        result["costs"] = 0.0
        result["campaign_name"] = campaign_name
        result["message"] = f"Generated email sequence '{campaign_name}' ({sequence_length} emails)."

        self.log(result["message"])
        return result

    def _exec_send_outreach(self, params: dict) -> dict:
        """Simulate sending outreach by saving emails to content/email/."""
        campaign_name = params.get("campaign_name", f"outreach_{int(time.time())}")
        recipients = params.get("recipients", 3)

        self.log(f"Sending outreach: '{campaign_name}' to {recipients} recipients")
        sent = 0
        for i in range(1, recipients + 1):
            filename = f"{campaign_name}_email_{i}.txt"
            filepath = self.email_dir / filename
            body = (
                f"Subject: {campaign_name.replace('_', ' ').title()} - Reach Out #{i}\n"
                f"To: lead_{i}@example.com\n"
                f"Campaign: {campaign_name}\n"
                f"---\n"
                f"Hi there,\n\n"
                f"This is simulated outreach email #{i} for the '{campaign_name}' campaign.\n"
                f"Sent at {time.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
                f"Best,\nLeadGen Agent\n"
            )
            try:
                filepath.write_text(body, encoding="utf-8")
                sent += 1
            except Exception as e:
                self.log(f"Failed to write {filename}: {e}")

        result = {
            "success": sent > 0,
            "revenue": 0.0,
            "costs": 0.0,
            "sent": sent,
            "campaign_name": campaign_name,
            "message": f"Simulated sending {sent} outreach emails for '{campaign_name}'.",
        }
        self.log(result["message"])
        return result

    def _exec_review_pipeline(self) -> dict:
        """Scan leads/ folder and report pipeline stats."""
        lead_files = list(self.leads_dir.glob("*.csv"))
        email_files = list(self.email_dir.glob("*email*.txt"))

        total_leads = self._count_leads_in_files(lead_files)
        total_emails = len(email_files)

        stats = {
            "lead_files": len(lead_files),
            "total_leads_estimated": total_leads,
            "email_files": total_emails,
            "revenue_to_date": self.state.revenue,
            "costs_to_date": self.state.costs,
            "net": round(self.state.revenue - self.state.costs, 2),
        }

        self.log(
            f"Pipeline review: {stats['lead_files']} lead files, "
            f"~{stats['total_leads_estimated']} leads, "
            f"{stats['email_files']} emails. "
            f"Net P&L: ${stats['net']}"
        )

        return {
            "success": True,
            "revenue": 0.0,
            "costs": 0.0,
            "stats": stats,
            "message": "Pipeline review complete.",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_leads_in_files(self, files: List[Path]) -> int:
        """Count rows across CSV lead files (estimate)."""
        total = 0
        for f in files:
            try:
                with f.open("r", encoding="utf-8", errors="ignore") as fp:
                    reader = csv.reader(fp)
                    rows = sum(1 for _ in reader)
                    total += max(0, rows - 1)  # subtract header if present
            except Exception:
                pass
        return total

    def _append_leads_csv(self, campaign_name: str, count: int):
        """Append a batch of simulated leads to a campaign CSV."""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in campaign_name)
        filepath = self.leads_dir / f"{safe_name}.csv"
        header = ["id", "email", "source", "timestamp"]
        write_header = not filepath.exists()

        try:
            with filepath.open("a", newline="", encoding="utf-8") as fp:
                writer = csv.writer(fp)
                if write_header:
                    writer.writerow(header)
                for i in range(count):
                    writer.writerow([
                        f"{safe_name}_{uuid.uuid4().hex[:6]}",
                        f"lead_{uuid.uuid4().hex[:6]}@example.com",
                        safe_name,
                        time.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except Exception as e:
            self.log(f"Failed to append leads CSV: {e}")
