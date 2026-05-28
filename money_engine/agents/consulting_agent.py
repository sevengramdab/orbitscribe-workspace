"""
consulting_agent.py
===================
Automates finding consulting gigs and sending proposals.

Actions:
- find_gigs:        Scrape Upwork/Freelancer for open gigs.
- screenshot_opportunities: Capture browser state for review.
- generate_proposal: Write a tailored proposal text.
- send_proposal:    Submit proposal via browser automation.
- follow_up:        Simulate checking messages / winning gigs.

Revenue model:
- +$50 per proposal sent
- +$500 simulated per gig won (10 % chance on follow_up)
"""
from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path
from typing import List, Optional

from money_engine.base_agent import BaseMoneyAgent, AgentDecision
from money_engine.orchestrator import register_agent


@register_agent
class ConsultingAgent(BaseMoneyAgent):
    """
    Consulting gig automation agent.

    Cycles through scouting gigs, generating proposals, sending them,
    and following up. Tracks simulated revenue.
    """

    VERTICAL = "consulting"

    # Paths for persistence
    GIGS_FILE = Path(__file__).parent.parent.parent / "content" / "consulting" / "gigs.json"
    PROPOSALS_DIR = Path(__file__).parent.parent.parent / "content" / "consulting" / "proposals"

    def __init__(self, agent_id: Optional[str] = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self._cs = self._load_consulting_state()
        self.PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Consulting-specific state persistence
    # ------------------------------------------------------------------

    def _load_consulting_state(self) -> dict:
        if self.GIGS_FILE.exists():
            try:
                return json.loads(self.GIGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "stage": "find_gigs",
            "gigs": [],
            "proposals": [],
            "last_follow_up": 0.0,
            "last_screenshot": 0.0,
            "proposals_sent_count": 0,
            "gigs_won_count": 0,
            "platform_idx": 0,
        }

    def _save_consulting_state(self):
        self.GIGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.GIGS_FILE.write_text(json.dumps(self._cs, indent=2, default=str), encoding="utf-8")

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        stage = self._cs.get("stage", "find_gigs")
        now = time.time()

        if stage == "find_gigs":
            action = "find_gigs"
            reasoning = "No recent gig search; scouting Upwork/Freelancer for opportunities."
            next_stage = "screenshot_opportunities"

        elif stage == "screenshot_opportunities":
            action = "screenshot_opportunities"
            reasoning = "Capturing visual snapshot of current opportunities for review."
            next_stage = "generate_proposal" if self._cs.get("gigs") else "find_gigs"

        elif stage == "generate_proposal":
            action = "generate_proposal"
            reasoning = "Generating a tailored proposal for the best available open gig."
            next_stage = "send_proposal"

        elif stage == "send_proposal":
            action = "send_proposal"
            reasoning = "Submitting the generated proposal on the gig page."
            next_stage = "follow_up"

        elif stage == "follow_up":
            action = "follow_up"
            reasoning = "Checking messages and following up on pending proposals."
            next_stage = "find_gigs"

        else:
            action = "find_gigs"
            reasoning = "Resetting to default gig search due to unknown stage."
            next_stage = "screenshot_opportunities"

        self._cs["stage"] = next_stage
        self._save_consulting_state()

        return AgentDecision(
            decision_id=f"consult_{uuid.uuid4().hex[:8]}",
            timestamp=now,
            action=action,
            params={"next_stage": next_stage},
            reasoning=reasoning,
            approved=False,
            executed=False,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        action = decision.action
        self.log(f"ConsultingAgent executing: {action}")

        try:
            if action == "find_gigs":
                return self._execute_find_gigs()
            elif action == "generate_proposal":
                return self._execute_generate_proposal()
            elif action == "send_proposal":
                return self._execute_send_proposal()
            elif action == "follow_up":
                return self._execute_follow_up()
            elif action == "screenshot_opportunities":
                return self._execute_screenshot_opportunities()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as exc:
            self.log(f"Execute error for {action}: {exc}")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    def _execute_find_gigs(self) -> dict:
        """Open Upwork or Freelancer, search, screenshot, and store gig URLs."""
        platforms = [
            "https://www.upwork.com/nx/search/jobs/?q=python%20automation",
            "https://www.freelancer.com/jobs/python-automation/",
        ]
        idx = self._cs.get("platform_idx", 0) % len(platforms)
        url = platforms[idx]
        self._cs["platform_idx"] = idx + 1

        self.log(f"Opening platform: {url}")
        self.browser.open_chrome(url=url, new_window=False)
        time.sleep(4.0)

        state = self.browser.screenshot(filename=f"consulting_gigs_{int(time.time())}.png")

        # Simulated gig URLs (real extraction would parse HTML or use platform APIs)
        if "upwork" in url:
            simulated = [
                "https://www.upwork.com/jobs/Python-Automation-Script_~01abcd/",
                "https://www.upwork.com/jobs/Web-Scraping-Data-Pipeline_~02efgh/",
                "https://www.upwork.com/jobs/API-Integration-Consultant_~03ijkl/",
            ]
        else:
            simulated = [
                "https://www.freelancer.com/projects/python-automation/build-me-scraper",
                "https://www.freelancer.com/projects/python-automation/data-engineering-consultation",
            ]

        existing = {g["url"] for g in self._cs.get("gigs", [])}
        new_gigs = []
        for u in simulated:
            if u not in existing:
                new_gigs.append({
                    "url": u,
                    "title": u.split("/")[-1].replace("-", " ").replace("_", " ").title(),
                    "found_at": time.time(),
                    "platform": "upwork" if "upwork" in u else "freelancer",
                    "status": "open",
                })

        self._cs.setdefault("gigs", []).extend(new_gigs)
        self._save_consulting_state()

        self.log(f"Found {len(new_gigs)} new gigs (total {len(self._cs['gigs'])})")
        return {
            "success": True,
            "new_gigs": len(new_gigs),
            "screenshot_path": state.screenshot_path,
            "platform": url,
        }

    def _execute_screenshot_opportunities(self) -> dict:
        """Screenshot current browser state for opportunity review."""
        state = self.browser.screenshot(filename=f"consulting_opps_{int(time.time())}.png")
        self._cs["last_screenshot"] = time.time()
        self._save_consulting_state()
        self.log("Screenshot of opportunities saved.")
        return {
            "success": True,
            "screenshot_path": state.screenshot_path,
        }

    def _execute_generate_proposal(self) -> dict:
        """Generate a proposal for the next open gig and save to disk."""
        open_gigs = [g for g in self._cs.get("gigs", []) if g.get("status") == "open"]
        if not open_gigs:
            self.log("No open gigs available to generate a proposal.")
            return {"success": False, "error": "No open gigs available"}

        target = open_gigs[0]
        gig_title = target.get("title", "Python Automation Project")
        platform = target.get("platform", "upwork")
        url = target.get("url", "")

        proposal_text = self._generate_proposal_text(gig_title, platform)
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        proposal_file = self.PROPOSALS_DIR / f"{proposal_id}.txt"

        proposal_file.write_text(
            f"Gig: {gig_title}\n"
            f"Platform: {platform}\n"
            f"URL: {url}\n"
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"---\n"
            f"{proposal_text}\n",
            encoding="utf-8",
        )

        self._cs.setdefault("proposals", []).append({
            "proposal_id": proposal_id,
            "gig_url": url,
            "gig_title": gig_title,
            "platform": platform,
            "file": str(proposal_file),
            "status": "ready",
            "generated_at": time.time(),
        })
        target["status"] = "proposal_ready"
        self._save_consulting_state()

        self.log(f"Generated proposal {proposal_id} for '{gig_title}'")
        return {
            "success": True,
            "proposal_id": proposal_id,
            "file": str(proposal_file),
            "gig_url": url,
        }

    def _generate_proposal_text(self, gig_title: str, platform: str) -> str:
        """Create a tailored proposal text."""
        intros = ["Hi there,", "Hello,", "Hey,"]
        bodies = [
            (
                "I specialize in Python automation and have built dozens of scripts "
                "that save clients 10+ hours per week. I can deliver a clean, documented "
                "solution with error handling and logging."
            ),
            (
                "With 5+ years of experience in data pipelines and web scraping, "
                "I can architect a robust system that scales with your needs."
            ),
            (
                "I’m a full-stack Python consultant who focuses on deliverables, not just code. "
                "I’ll make sure the solution integrates smoothly into your existing workflow."
            ),
        ]
        closings = [
            "Let’s jump on a quick call to discuss details. Looking forward to it!",
            "Ready to start immediately. Happy to adjust scope based on your budget.",
            "I can provide a demo within 24 hours. Let me know if you're interested.",
        ]

        intro = random.choice(intros)
        body = random.choice(bodies)
        closing = random.choice(closings)

        return (
            f"{intro}\n\n"
            f"I came across your posting for '{gig_title}' and it aligns perfectly with my expertise.\n\n"
            f"{body}\n\n"
            f"{closing}\n\n"
            f"Best regards,\n"
            f"OrbitScribe Consulting"
        )

    def _execute_send_proposal(self) -> dict:
        """Open gig page, fill proposal, submit, and track revenue."""
        ready = [p for p in self._cs.get("proposals", []) if p.get("status") == "ready"]
        if not ready:
            self.log("No ready proposals to send.")
            return {"success": False, "error": "No ready proposals"}

        prop = ready[0]
        url = prop.get("gig_url", "")
        platform = prop.get("platform", "upwork")
        proposal_file = Path(prop.get("file", ""))
        proposal_text = (
            proposal_file.read_text(encoding="utf-8").split("---\n")[-1].strip()
            if proposal_file.exists()
            else ""
        )

        self.log(f"Navigating to gig page: {url}")
        self.browser.navigate(url)
        time.sleep(3.0)

        self.browser.screenshot(filename=f"before_apply_{int(time.time())}.png")

        # Heuristic click for apply button
        if platform == "upwork":
            self.browser.win_click(0.85, 0.25)
        else:
            self.browser.win_click(0.70, 0.30)
        time.sleep(2.0)

        # Fill cover-letter area
        self.browser.click_text_field(0.50, 0.65, clear=True)
        time.sleep(0.5)
        self.browser.win_type(proposal_text[:1200])  # safety cap
        time.sleep(1.0)

        self.browser.screenshot(filename=f"after_apply_{int(time.time())}.png")

        # Heuristic submit click
        self.browser.win_click(0.80, 0.90)
        time.sleep(2.0)

        # Update state
        prop["status"] = "sent"
        prop["sent_at"] = time.time()
        self._cs["proposals_sent_count"] = self._cs.get("proposals_sent_count", 0) + 1

        for g in self._cs.get("gigs", []):
            if g.get("url") == url:
                g["status"] = "applied"

        self._save_consulting_state()

        revenue = 50.0
        self.log(f"Proposal sent for {url}. Simulated revenue +${revenue}")
        return {
            "success": True,
            "proposal_id": prop.get("proposal_id"),
            "gig_url": url,
            "revenue": revenue,
        }

    def _execute_follow_up(self) -> dict:
        """Simulate checking messages; occasionally simulate a gig win."""
        self._cs["last_follow_up"] = time.time()

        proposals_sent = self._cs.get("proposals_sent_count", 0)
        gigs_won = self._cs.get("gigs_won_count", 0)
        revenue = 0.0

        if proposals_sent > gigs_won and random.random() < 0.10:
            self._cs["gigs_won_count"] = gigs_won + 1
            revenue = 500.0
            self.log(f"Simulated gig won! Revenue +${revenue}")
        else:
            self.log("Follow-up: no new messages or wins this cycle.")

        self._save_consulting_state()
        return {
            "success": True,
            "revenue": revenue,
            "proposals_sent": proposals_sent,
            "gigs_won": self._cs.get("gigs_won_count", 0),
        }

    # ------------------------------------------------------------------
    # Interval
    # ------------------------------------------------------------------

    def get_default_interval(self) -> int:
        return 1200  # 20 minutes
