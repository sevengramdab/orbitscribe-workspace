"""
money_engine
============
Autonomous money-making engine that controls mouse, keyboard, and browser
to perform real revenue-generating tasks.

10 agent verticals:
- content      : Blog posts, ebooks, social media
- affiliate    : Affiliate link posting, commission tracking
- dropshipping : Product listing, price monitoring
- saas         : Micro-SaaS building and deployment
- marketplace  : Gumroad, Etsy, Shopify listing automation
- leadgen      : Lead scraping and cold outreach
- ads          : Ad campaign creation and monitoring
- licensing    : Code/template/asset licensing
- subscription : Newsletter and membership management
- consulting   : Gig finding and proposal sending
"""

from . import agents  # noqa: F401  — triggers @register_agent side-effects
from .orchestrator import MoneyOrchestrator, register_agent, get_agent_class, list_agent_verticals
from .base_agent import BaseMoneyAgent, AgentDecision, AgentState
from .browser_controller import BrowserController, BrowserState
from .kimi_bridge import KimiBridge

__all__ = [
    "MoneyOrchestrator",
    "BaseMoneyAgent",
    "AgentDecision",
    "AgentState",
    "BrowserController",
    "BrowserState",
    "KimiBridge",
    "register_agent",
    "get_agent_class",
    "list_agent_verticals",
]
