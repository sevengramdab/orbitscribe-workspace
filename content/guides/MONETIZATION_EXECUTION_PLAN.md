# 4-Week Monetization Execution Plan

> **Current Status**: SIMULATION mode. All revenue figures are simulated until live API keys are added and ModeGuard approves.
>
> **Local Inference**: ACTIVE — Ollama on `localhost:11434` with `llama3.1:8b` (fast) and `qwen3:14b` (quality).

---

## Week 1: Foundation + Content Publishing

**Goal**: Get first affiliate content live. Zero capital required.

### Day 1-2: Account Setup & Verification
| Task | Owner | Status |
|------|-------|--------|
| ClickBank "Complete Profile" | You | Pending |
| ClickBank account nickname | You | Pending |
| Substack publication polish | You | Done (OrbStudio's Substack) |
| Medium profile + bio paste | You | Pending |
| Amazon Associates application | You | Optional |

### Day 3-4: Publish First Articles
| Task | Tool | Platform |
|------|------|----------|
| Review HTML draft | `content/published/medium/*.html` | Medium (copy-paste) |
| Review MD draft | `content/published/substack/*.md` | Substack (copy-paste) |
| Replace `{{AMAZON_ASSOCIATES_TAG}}` | `tools/affiliate_link_manager.py` | All |
| Replace `{{CLICKBANK_LINK:*}}` | `tools/affiliate_link_manager.py` | All |

### Day 5-7: Traffic Seed
| Task | How |
|------|-----|
| Share on Reddit (r/webhosting, r/VPN, r/photoshop) | Manual |
| Share on Twitter/X | Manual |
| Post to relevant forums | Manual |
| Enable Substack "Recommend" feature | Substack settings |

**Week 1 Agents**: `ContentMarketingAgent`, `AffiliateAgent`
**Expected Sim Revenue**: $50-150 (fiction)
**Realistic Actual**: $0-5 (first content rarely converts immediately)

---

## Week 2: Traffic + Email Capture

**Goal**: Build an audience asset (email list) that you own.

### Day 8-10: Substack Growth
| Task | How |
|------|-----|
| Publish 2 more posts (1 comparison + 1 deal alert) | Write or use swarm-generated |
| Cross-post Medium → Substack | Import feature |
| Add "Subscribe" CTA to every Medium story | Manual |
| Comment on 10 stories/day in your niche | Manual |

### Day 11-12: Lead Magnet
| Task | Tool |
|------|------|
| Create free PDF guide (e.g., "2025 VPN Buyer's Guide") | `AssetFactoryAgent` |
| Set up email capture landing page | `SaaSMicroAppAgent` |
| Connect SMTP for welcome sequence | `.env` SMTP vars |

### Day 13-14: First Data Review
| Task | Dashboard |
|------|-----------|
| Check which article got most clicks | Substack stats, Medium stats |
| Check affiliate link CTR | ClickBank reports, Amazon reports |
| Double down on winning topic | ContentMarketingAgent |

**Week 2 Agents**: `ContentMarketingAgent`, `LeadGenAgent`, `DataScienceAgent`
**Expected Sim Revenue**: $150-300
**Realistic Actual**: $0-15 (list building phase)

---

## Week 3: Product Expansion

**Goal**: Add revenue streams beyond affiliate.

### Day 15-17: Print-on-Demand Test
| Task | Agent | Note |
|------|-------|------|
| Generate 3 design concepts | `AssetFactoryAgent` | Uses local LLM |
| Create mockups | `PrintOnDemandAgent` | Simulation mode |
| Upload to Printify/Etsy stub | `PrintOnDemandAgent` | Needs real keys for live |

### Day 18-19: Micro-SaaS Experiment
| Task | Agent | Note |
|------|-------|------|
| Spin up simple tool (e.g., VPN comparison calculator) | `SaaSMicroAppAgent` | Saves to `products/apps/` |
| Stripe payment link | `SaaSMicroAppAgent` | Needs Stripe keys for live |
| Deploy to free tier (Vercel/Render) | Manual | Zero-cost hosting |

### Day 20-21: Content Scale
| Task | How |
|------|-----|
| Batch-generate 5 more comparison articles | `ContentMarketingAgent` + Ollama |
| Queue for publishing | `tools/publish_to_*.py` |
| Repurpose top performer into video script | `AssetFactoryAgent` |

**Week 3 Agents**: `PrintOnDemandAgent`, `SaaSMicroAppAgent`, `AssetFactoryAgent`
**Expected Sim Revenue**: $300-600
**Realistic Actual**: $0-30 (product validation phase)

---

## Week 4: Optimization + Scale Decision

**Goal**: Decide which verticals to take live.

### Day 22-24: Analytics Deep Dive
| Metric | Source | Decision |
|--------|--------|----------|
| Affiliate CTR by article | ClickBank/Amazon | Kill losers, double winners |
| Substack subscriber growth | Substack dashboard | If >100 subs, enable paid tier |
| POD mockup engagement | Etsy/Printify (sim) | If gravity >20, go live |
| SaaS tool signups | Stripe (sim) | If >10 signups, add real payments |

### Day 25-26: Live Mode Preparation
| Vertical | Required Keys | Risk Level |
|----------|--------------|------------|
| Affiliate (Amazon) | `AMAZON_ASSOCIATES_TAG` | Low |
| Affiliate (ClickBank) | `CLICKBANK_ACCOUNT_NICKNAME` | Low |
| Content (Substack) | Stripe connect | Low |
| Content (Medium) | None (manual) | None |
| Print-on-Demand | `PRINTIFY_API_KEY`, `ETSY_API_KEY` | Medium |
| SaaS Micro-App | `STRIPE_API_KEY`, `STRIPE_SECRET_KEY` | Medium |
| Dropshipping | `SPOCKET_API_KEY` | High (inventory risk) |

### Day 27-28: Go Live (Selected Verticals Only)
1. Add real API keys to `.env`
2. Run `python tools/vault_security.py encrypt_all_vaults`
3. Set `LIVE_MODE=true` in `.env`
4. Restart swarm backend
5. Activate only 1-2 verticals in live mode
6. Monitor `/api/intelligence/summary` hourly

**Week 4 Agents**: `DataScienceAgent`, `MarketIntelligenceAgent`, `SwarmOrchestrator`
**Expected Sim Revenue**: $600-1000
**Realistic Actual**: $10-100 (first real conversions)

---

## Daily Operations Checklist

### Morning (5 min)
- [ ] Check dashboard: `http://localhost:58083/monetization`
- [ ] Review overnight agent decisions
- [ ] Check Ollama health: `python tools/ollama_health_check.py`

### Midday (10 min)
- [ ] Respond to Substack comments
- [ ] Share new content to 1 social channel
- [ ] Check affiliate dashboard for clicks

### Evening (5 min)
- [ ] Review `swarm-backend/tools/saved_sessions/` for new vaults
- [ ] Check keep-awake status on dashboard
- [ ] Plan next day's content angle

---

## Go-Live Safety Rules

1. **Never activate all verticals at once.** Start with 1 (affiliate), add others weekly.
2. **Keep simulation running parallel.** Compare sim predictions vs actuals.
3. **Set spending caps.** Even in live mode, ModeGuard enforces minimums.
4. **Encrypt vaults immediately** after adding real keys.
5. **Shadow TOS watch:** Keep-awake is borderline. Do NOT run Salad/bandwidth apps 24/7.

---

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Ollama crashes | Auto-restart via `tools/ollama_health_check.py` or Windows service |
| Agent crashes | Swarm backend watchdog auto-restarts on port 58083 |
| Shadow disconnect | Keep-awake + resume watchdog maintain session |
| API key leak | Run `encrypt_all_vaults()`, rotate keys, check `.env` backups |
| Zero conversions after 2 weeks | Pivot topic → DataScienceAgent picks new niche |
| ClickBank ban | Switch to Amazon Associates + ShareASale fallback |

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `content/account_setup/PASTE_KEYS_HERE.env` | Where you paste account info |
| `tools/ingest_account_keys.py` | Wires keys into swarm config |
| `tools/publish_to_medium.py` | Generates Medium HTML drafts |
| `tools/publish_to_substack.py` | Generates Substack MD drafts |
| `tools/affiliate_link_manager.py` | Replaces placeholders with real IDs |
| `tools/ollama_health_check.py` | Verifies local LLM is running |
| `swarm-backend/business_config.json` | Central config after ingestion |
| `content/guides/clickbank_signup_guide.md` | ClickBank deep-dive |

---

*Plan version: May 2026 | Mode: SIMULATION | Next review: Week 1 end*
