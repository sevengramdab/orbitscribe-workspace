"""
Business Agent Registry for the Monetization Swarm.
Import all business agents here for auto-discovery.
"""

from typing import Dict, Type
from .base import BaseBusinessAgent

# Registry will be populated by importing each agent module
BUSINESS_AGENT_REGISTRY: Dict[str, Type[BaseBusinessAgent]] = {}


def register_business_agent(name: str, agent_class: Type[BaseBusinessAgent]):
    BUSINESS_AGENT_REGISTRY[name] = agent_class


def get_business_agent(name: str) -> Type[BaseBusinessAgent]:
    return BUSINESS_AGENT_REGISTRY.get(name)


def list_business_agents() -> Dict[str, str]:
    return {name: cls.__doc__ or "" for name, cls in BUSINESS_AGENT_REGISTRY.items()}


# Lazy imports to avoid circular dependencies
def _load_all_agents():
    """Call after all modules are imported to populate registry."""
    try:
        from .dropshipping_agent import DropshippingAgent
        register_business_agent("dropshipping", DropshippingAgent)
    except Exception as e:
        print(f"[Business Agents] dropshipping not loaded: {e}")

    try:
        from .stripe_agent import StripeAgent
        register_business_agent("stripe", StripeAgent)
    except Exception as e:
        print(f"[Business Agents] stripe not loaded: {e}")

    try:
        from .lead_gen_agent import LeadGenAgent
        register_business_agent("lead_gen", LeadGenAgent)
    except Exception as e:
        print(f"[Business Agents] lead_gen not loaded: {e}")

    try:
        from .asset_factory_agent import AssetFactoryAgent
        register_business_agent("asset_factory", AssetFactoryAgent)
    except Exception as e:
        print(f"[Business Agents] asset_factory not loaded: {e}")

    try:
        from .print_on_demand_agent import PrintOnDemandAgent
        register_business_agent("print_on_demand", PrintOnDemandAgent)
    except Exception as e:
        print(f"[Business Agents] print_on_demand not loaded: {e}")

    try:
        from .content_marketing_agent import ContentMarketingAgent
        register_business_agent("content_marketing", ContentMarketingAgent)
    except Exception as e:
        print(f"[Business Agents] content_marketing not loaded: {e}")

    try:
        from .crypto_web3_agent import CryptoWeb3Agent
        register_business_agent("crypto_web3", CryptoWeb3Agent)
    except Exception as e:
        print(f"[Business Agents] crypto_web3 not loaded: {e}")

    try:
        from .saas_micro_app_agent import SaasMicroAppAgent
        register_business_agent("saas_micro_app", SaasMicroAppAgent)
    except Exception as e:
        print(f"[Business Agents] saas_micro_app not loaded: {e}")

    try:
        from .market_intelligence_agent import MarketIntelligenceAgent
        register_business_agent("market_intelligence", MarketIntelligenceAgent)
    except Exception as e:
        print(f"[Business Agents] market_intelligence not loaded: {e}")

    try:
        from .affiliate_agent import AffiliateAgent
        register_business_agent("affiliate", AffiliateAgent)
    except Exception as e:
        print(f"[Business Agents] affiliate not loaded: {e}")
