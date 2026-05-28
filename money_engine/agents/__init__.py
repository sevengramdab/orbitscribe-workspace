"""
Money Engine Agents
===================
All 10 vertical agents are registered here for the orchestrator.
"""

# Agents will be imported below as they are built.
# Each agent class must use @register_agent from money_engine.orchestrator

try:
    from .content_agent import ContentAgent
except ImportError as e:
    pass

try:
    from .affiliate_agent import AffiliateAgent
except ImportError as e:
    pass

try:
    from .dropshipping_agent import DropshippingAgent
except ImportError as e:
    pass

try:
    from .saas_agent import SaaSAgent
except ImportError as e:
    pass

try:
    from .marketplace_agent import MarketplaceAgent
except ImportError as e:
    pass

try:
    from .leadgen_agent import LeadGenAgent
except ImportError as e:
    pass

try:
    from .ads_agent import AdsAgent
except ImportError as e:
    pass

try:
    from .licensing_agent import LicensingAgent
except ImportError as e:
    pass

try:
    from .subscription_agent import SubscriptionAgent
except ImportError as e:
    pass

try:
    from .consulting_agent import ConsultingAgent
except ImportError as e:
    pass
