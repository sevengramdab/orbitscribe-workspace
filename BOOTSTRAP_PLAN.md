# OrbitScribe Zero-to-Revenue Bootstrap Plan

> **Status:** Draft — synthesized from hardware, platform, sales-data, and swarm-capability research  
> **Audience:** Unemployed builder waiting on settlement; needs cash flow without upfront spend  
> **Tone:** Realistic, encouraging, no get-rich-quick promises. Every dollar estimate is conservative.

---

## Executive Summary

You already own a revenue engine:
- **NVIDIA RTX A4500 (20 GB)** — professional GPU worth $1,200+
- **AMD EPYC 7543P** — server-grade CPU
- **10-agent Money Engine** — content, affiliate, SaaS, lead-gen, dropshipping, licensing agents
- **Swarm backend** — FastAPI tool registry that generates ebooks, prompt packs, code templates, apps, email sequences, and lead lists
- **SimplePod** — remote control layer for a second machine if you need it
- **Pre-generated assets** sitting in `content/`, `products/assets/`, `products/apps/`, and `leads/`

This plan treats your hardware as **Tier-0 revenue** (money while you sleep) and the swarm as **Tier-1 revenue** (money while you work). The goal is to reach **$300–$800/month** within 8 weeks, then scale to **$1,500+/month** after settlement reinvestment.

---

## Phase 0: Hardware Monetization (Week 1, $0 Out-of-Pocket)

> **Goal:** Turn idle GPU/CPU cycles into $3–$8/day while the swarm runs.

### Your Hardware Profile
| Component | Spec | Monetization Fit |
|-----------|------|-----------------|
| GPU | NVIDIA RTX A4500, 20 GB VRAM, Compute 8.6, 200 W TDP | AI inference rental, render farm, ML training pods |
| CPU | AMD EPYC 7543P (VM-visible: 4C/8T @ 2.8 GHz) | Container hosting, background batch jobs, swarm backend |
| RAM | ~16–32 GB (verify with `systeminfo`) | Limits concurrent GPU workloads |

> **Note:** The EPYC 7543P is a 32-core chip, but your current instance shows 4C/8T. This is normal for a VM or remote-desktop slice. The bootstrap plan assumes the visible 4C/8T; if you have bare-metal access to all 32 cores, double the CPU-compute estimates below.

### Top 3 Compute-Sharing Platforms

#### 1. Salad.com (Best for Passive Income)
- **What it is:** Distributed cloud. Your machine joins a pool and runs containerized workloads (AI inference, video encoding, game streaming).
- **A4500 payout:** ~$0.12–$0.22/hour historically for comparable workstation cards.
- **Expected daily:** **$2.50–$5.00** if online 20–22 hrs/day.
- **Pros:** Set-and-forget; pays in USD or crypto; low utilization threshold.
- **Cons:** Workloads are intermittent; you need a stable IP and port forwarding can be tricky behind NAT.

**Setup Steps:**
1. Create account at `https://salad.com` → download Salad Bowl (Windows app).
2. During onboarding, select **"GPU Workloads"** and whitelist the A4500.
3. Set **earning schedule:** 11 PM – 7 AM local time (swarm downtime).
4. In Salad settings, cap CPU allocation to **20%** so the swarm backend (port 58081) stays responsive.
5. Add payout method (PayPal or crypto wallet). Minimum payout: **$5.00**.

#### 2. Vast.ai (Best for AI/ML Rental Income)
- **What it is:** Peer-to-peer GPU rental. Researchers and indie devs rent your GPU by the hour.
- **A4500 payout:** ~$0.18–$0.35/hour depending on demand and reliability score.
- **Expected daily:** **$3.00–$7.00** if rented 60% of the day.
- **Pros:** Highest per-hour rate for workstation GPUs; you set pricing.
- **Cons:** Must configure SSH + Docker; rental demand fluctuates; requires inbound port 22 or Vast’s tunnel.

**Setup Steps:**
1. Create host account at `https://vast.ai/host`.
2. Install Docker Desktop for Windows + WSL2 backend.
3. Run the Vast host installer (PowerShell as Administrator):
   ```powershell
   # Follow the CLI instructions on the host dashboard
   vastai install host
   ```
4. List your machine with a **reliability discount** (e.g., $0.22/hr) to get initial rentals and build a 5-star rating.
5. Set **maintenance windows:** 8 AM – 10 PM = swarm-active hours. Block rentals during that window.

#### 3. RunPod (Best for Serverless Inference)
- **What it is:** Serverless GPU pods + persistent pods. You run a Docker template and get paid per minute of usage.
- **A4500 payout:** ~$0.15–$0.28/hour in serverless pool; ~$0.20–$0.40/hour in dedicated pod rental.
- **Expected daily:** **$2.00–$5.00** in serverless mode if the pool dispatches workloads.
- **Pros:** Automatic scaling; you don’t manage SSH clients; integrates with popular AI templates (Stable Diffusion, ComfyUI, Ollama).
- **Cons:** Serverless work is bursty; network proxy adds latency.

**Setup Steps:**
1. Sign up at `https://runpod.io` → **Become a Host**.
2. Download the RunPod worker binary for Windows (or run inside WSL2 if available).
3. Deploy a **ComfyUI** or **Ollama** template — your A4500 is perfect for 7B–13B LLM inference or SDXL.
4. Set max concurrency to **1 GPU job** (you only have one A4500).
5. Payout via Stripe. Minimum: **$1.00**.

### Conflict-Avoidance Schedule

Your swarm uses the GPU for local LLM inference (Ollama is already running) and the CPU for the FastAPI backend, browser automation, and content generation. You cannot share the GPU simultaneously with a rental workload.

| Time Block (Local) | GPU Task | CPU Task | Income Stream |
|-------------------|----------|----------|--------------|
| 12:00 AM – 07:00 AM | Compute rental (Salad/Vast/RunPod) | Idle / low-priority batch jobs | Hardware $ |
| 07:00 AM – 08:00 AM | Warm-up Ollama; preload models | Swarm backend startup | — |
| 08:00 AM – 12:00 PM | Swarm inference + asset generation | Money Engine active; browser automation | Content/affiliate $ |
| 12:00 PM – 01:00 PM | Lunch break / optional rental | Idle | Hardware $ |
| 01:00 PM – 06:00 PM | Swarm inference + app builds | Lead gen + outreach | Lead-gen $ |
| 06:00 PM – 08:00 PM | Render farm (if any pending) | Email sequencing + publishing | Digital product $ |
| 08:00 PM – 11:00 PM | Light Ollama use | Monitoring + P&L review | — |
| 11:00 PM – 12:00 AM | Transition to compute rental | Shutdown swarm GPU agents | Hardware $ |

> **Rule of thumb:** If the Money Engine is running `AUTOPILOT` and generating assets, the GPU belongs to the swarm. If you are asleep or AFK for >2 hours, switch the GPU to rental mode.

### Phase 0 Expected Earnings (Week 1)
| Platform | Conservative | Optimistic |
|----------|-------------|------------|
| Salad.com | $15/week | $35/week |
| Vast.ai | $18/week | $45/week |
| RunPod | $12/week | $30/week |
| **Combined** | **$45/week** | **$110/week** |

**Realistic blended estimate:** **$40–$70/week** once you find the right platform mix. Start with Salad (easiest), add Vast (highest rate), and keep RunPod as a fallback.

---

## Phase 1: Content & Affiliate (Weeks 1–2, $0 Out-of-Pocket)

> **Goal:** Publish the assets already in `content/` and `products/assets/` to free platforms. Earn first commission within 14–21 days.

### Inventory You Already Have
| Directory | Count | State | Action |
|-----------|-------|-------|--------|
| `content/affiliate/` | 3 comparison articles | Needs affiliate links replaced | Publish to Medium/Substack |
| `content/blog/` | 7 blog posts | Ready to publish | Publish to Medium + Pinterest pins |
| `content/email/` | 2 newsletters + 5 email sequences | Needs subscriber list | Use as lead magnets |
| `content/social/` | 1 Twitter thread | Ready | Post to X/Twitter + repurpose to threads |
| `products/assets/` | 20+ ebooks, prompts, templates | Packaged as .zip/.md/.html | List on Gumroad free tier |

### Free Publishing Platforms

#### Medium (Partner Program + Affiliate)
- **Why:** Domain authority is high; Google indexes Medium posts fast.
- **Monetization:** Medium Partner Program pays by member reading time (~$0.02–$0.05 per read). Affiliate links are allowed if disclosed.
- **Action:**
  1. Create account at `https://medium.com`.
  2. Import or paste the 7 blog posts from `content/blog/`.
  3. Add a **CTA box** at the bottom: *“Get the free prompt pack → [Gumroad link]”*.
  4. Add affiliate links inline (see programs below).
  5. Tag each post with 5 relevant topics (AI, Productivity, Side Hustle, Automation, Entrepreneurship).

#### Substack (Newsletter + SEO)
- **Why:** Free newsletter + public posts that rank in Google. You own the subscriber list.
- **Monetization:** Paid subscriptions (turn on later), affiliate links, sponsorships at 500+ subs.
- **Action:**
  1. Create publication at `https://substack.com`.
  2. Publish the 2 newsletters from `content/email/` as starter posts.
  3. Set a schedule: **1 post per week** (Tuesday 9 AM works well).
  4. Add a **Subscribe CTA** and embed your Gumroad lead magnet.

#### Pinterest (Traffic Driver)
- **Why:** Pinterest is a search engine, not social media. Pins drive traffic for 6–12 months.
- **Monetization:** Indirect — drives to Medium/Substack/Gumroad where affiliate links live.
- **Action:**
  1. Create business account at `https://business.pinterest.com` (free).
  2. For each blog post, create **3 Pin variations** using Canva free tier (1000×1500 px).
  3. Link each Pin directly to the Medium post or Gumroad product.
  4. Pin 1–2 times per day using the free Tailwind plan (or manually).

### Affiliate Programs to Join (Instant or Fast Approval)

| Program | Approval Speed | Payout | Best For | Sign-up |
|---------|---------------|--------|----------|---------|
| **ClickBank** | Instant | 10–75% commission | Digital products, health, biz-op | `https://clickbank.com` |
| **Amazon Associates** | Instant (but need 3 sales in 180 days) | 1–10% | Software, books, gear | `https://affiliate-program.amazon.com` |
| **Fiverr Affiliates** | 1–3 days | $15–$150 per action | Freelance services, AI gigs | `https://affiliates.fiverr.com` |
| **Gumroad Discover** | Instant (if you have a Gumroad account) | Variable % on others’ products | Digital products, templates | `https://gumroad.com/discover` |
| **NordVPN** | 1–2 days via Impact | 40–100% rev share | Privacy, security posts | `https://nordvpn.com/affiliates` |
| **ConvertKit** | Instant | 30% recurring | Email marketing, creators | `https://convertkit.com/affiliates` |
| **Hostinger** | 1–2 days | 60% one-time | Web hosting, SaaS builders | `https://www.hostinger.com/make-money-online` |
| **Notion** | Waitlist (2–4 weeks) | 50% first payment | Productivity templates | `https://www.notion.so/partners` |

> **Priority order for Week 1:**
> 1. ClickBank (instant — grab your hoplinks today)
> 2. Amazon Associates (instant — replace `{{AMAZON_ASSOCIATES_TAG}}` in `content/affiliate/`)
> 3. Fiverr + ConvertKit (fast — apply now, approved by Week 2)

### Content Syndication Strategy

Instead of writing new content, syndicate what you have:

```
Blog Post (Medium) ──► Pin on Pinterest ──► Thread on X/Twitter
       │
       ▼
   Newsletter (Substack) ──► Email sequence to subscribers
       │
       ▼
   Repackage as PDF ──► Gumroad free product (captures email)
```

**Week 1–2 Publishing Calendar:**
| Day | Action |
|-----|--------|
| Day 1 | Join ClickBank + Amazon Associates. Replace placeholder tags in `content/affiliate/`. |
| Day 2 | Publish 3 blog posts to Medium. Add affiliate CTAs. |
| Day 3 | Create 9 Pinterest pins (3 per post). Schedule 1/day. |
| Day 4 | Publish 1 affiliate comparison post to Medium. |
| Day 5 | Set up Substack. Import 2 newsletters as archive posts. |
| Day 6 | Post Twitter thread from `content/social/`. Pin a link to Gumroad. |
| Day 7 | Review analytics. Double down on the post with the most reads. |
| Day 8–14 | Publish remaining blog posts. Start email capture via Gumroad freebie. |

### Phase 1 Expected Earnings
| Source | Conservative | Optimistic | Timeline |
|--------|-------------|------------|----------|
| Medium Partner Program | $5–$15/month | $30–$80/month | 2–4 weeks |
| Affiliate commissions | $0–$10/month | $50–$200/month | 2–6 weeks |
| Gumroad freebie → paid upsell | $0–$20/month | $40–$100/month | 3–4 weeks |
| **Phase 1 Total** | **$5–$45/month** | **$120–$380/month** | — |

**Realistic blended estimate:** **$50–$150/month** by end of Week 4 if you publish consistently and replace affiliate placeholders with real links.

---

## Phase 2: Digital Products (Weeks 2–4, $0 Out-of-Pocket)

> **Goal:** Package existing swarm output into sellable products. List on zero-upfront platforms.

### Product Types from Your Existing Assets

#### A. Prompt Packs (Fastest to List)
- **What you have:** `products/assets/*_prompts.txt` files (entrepreneurship, copywriting, e-commerce, personal finance, etc.)
- **What to do:**
  1. Combine 3–5 niche prompt files into a themed pack (e.g., *“The AI Entrepreneur’s Prompt Vault — 50 Prompts for Business Growth”*).
  2. Add a 1-page PDF cover in Canva (free).
  3. List on Gumroad for **$7–$17**.
- **Expected revenue per sale:** $5–$12 after Gumroad fee (10% + $0.30).

#### B. Code Templates / Starter Kits
- **What you have:** `products/assets/flask_api/` and multiple `.zip` templates.
- **What to do:**
  1. Pick the best 2 templates (Flask API starter, URL shortener).
  2. Add a `README.md` with setup instructions and a screenshot.
  3. List on Gumroad for **$15–$39**.
  4. Also list on GitHub as a public repo with a **“Sponsor”** link and Ko-fi button.
- **Expected revenue per sale:** $12–$30 after fees.

#### C. Notion Templates
- **What you have:** `products/assets/notion_productivity_templates_notion.md`.
- **What to do:**
  1. Convert the markdown into an actual Notion page with databases and views.
  2. Duplicate it and share the public link.
  3. List on Gumroad + Notion Template Gallery for **$5–$15**.
- **Expected revenue per sale:** $4–$12 after fees.

#### D. Ebooks / Guides
- **What you have:** Multiple `.html` and `.md` ebooks (cybersecurity, AI automation, sustainable living, digital marketing).
- **What to do:**
  1. Pick the 2 highest-quality ebooks (AI automation + cybersecurity are trending).
  2. Convert `.html` to PDF using browser print-to-PDF.
  3. Design a cover in Canva.
  4. List on Gumroad for **$9–$27**.
  5. Also publish on **Leanpub** (free to list, 80% royalty) and **Payhip** (free tier, 5% fee).
- **Expected revenue per sale:** $7–$20 after fees.

#### E. Print-on-Demand (Truly Passive)
- **What to do:**
  1. Use the swarm or Canva to generate 10 minimalist text-based designs (quotes, niche humor, productivity slogans).
  2. Upload to **Printify** (free) → push to **Etsy** ($0.20 listing fee per item — skip if truly $0, use Redbubble instead).
  3. Alternative: Upload directly to **Redbubble** (zero listing fees; you earn margin on each sale).
- **Expected revenue per sale:** $2–$8 profit per item; expect 0–5 sales in Month 1 unless you drive traffic.

### Listing Platforms (All Free to Start)

| Platform | Fee Structure | Best For | Sign-up |
|----------|--------------|----------|---------|
| **Gumroad** | 10% + $0.30/transaction | All digital products | `https://gumroad.com` |
| **Payhip** | 5%/transaction | Ebooks, courses | `https://payhip.com` |
| **Leanpub** | 80% royalty to author | Technical ebooks | `https://leanpub.com` |
| **Redbubble** | Artist sets margin; RB handles rest | POD shirts, stickers, prints | `https://redbubble.com` |
| **Printify** | Free plan; pay per item when ordered | POD fulfillment for Etsy/Shopify | `https://printify.com` |
| **GitHub Sponsors + Ko-fi** | 0% fee (GH), 5% (Ko-fi) | Code templates, open-source | `https://ko-fi.com` |

### Phase 2 Expected Earnings
| Product Type | Conservative | Optimistic |
|-------------|-------------|------------|
| Prompt packs (2 listings) | $15–$40/month | $80–$200/month |
| Code templates (2 listings) | $10–$30/month | $50–$150/month |
| Ebooks (2 listings) | $10–$40/month | $60–$180/month |
| Notion template (1 listing) | $5–$20/month | $30–$80/month |
| POD (Redbubble) | $0–$10/month | $20–$60/month |
| **Phase 2 Total** | **$40–$140/month** | **$240–$670/month** |

**Realistic blended estimate:** **$100–$300/month** by end of Week 6 with 6–8 live listings and modest traffic from Phase 1 content.

---

## Phase 3: Micro-SaaS (Weeks 4–8, $0 Hosting)

> **Goal:** Deploy one working micro-app, collect emails, and monetize via Ko-fi/Gumroad.

### Your Existing Apps

From `products/apps/` and `products/apps/saas_registry.json`:

| App | Stack | Status | Hosting Fit |
|-----|-------|--------|------------|
| URL Shortener v1 | Flask | Deployed on Render (`url_shortener_1.onrender.com`) | Already live; keep running |
| JSON Formatter | Static HTML/JS | Local | Vercel free tier (instant deploy) |
| Custom App (`custom_5d2afaba`) | Flask + Docker | Local | Render free tier (Web Service) |

### Recommended: Pick the JSON Formatter

**Why:**
- Zero backend = zero server costs on Vercel.
- SEO-friendly for dev-tool keywords (*“json formatter”*, *“json prettifier”*).
- Easy to add affiliate ads (Carbon, EthicalAds) or a Ko-fi link.
- Can upsell to a “Pro” version (JSON diff, schema validation) later.

**Deployment Steps (Vercel, Free):**
1. Install Vercel CLI: `npm i -g vercel`
2. `cd products/apps/json_formatter`
3. `vercel --prod` (no credit card required for hobby tier).
4. Add a custom domain later (free via Vercel or use a $3/year `.store` domain after settlement).

### Monetization Stack for Micro-SaaS

| Layer | Tool | Cost | Purpose |
|-------|------|------|---------|
| Hosting | Vercel / Netlify / Render | $0 | Serve the app |
| Auth (optional) | Clerk free tier | $0 | User accounts for Pro version |
| Database (optional) | Supabase free tier | $0 | 500 MB Postgres + Auth |
| Payments | Ko-fi / Gumroad | $0 upfront | Accept one-time or recurring payments |
| Analytics | Plausible (self-host) or Google Analytics | $0 | Track conversions |
| Email capture | ConvertKit free tier | $0 | Up to 1,000 subscribers |

### LeadGen Integration

Your `money_engine/agents/leadgen_agent.py` already scrapes leads. Connect it to the micro-SaaS:

1. Add a **newsletter signup** to the JSON formatter page.
2. Use the LeadGen agent to find dev-tool newsletters and indie-hacker communities.
3. Post the tool in:
   - `r/webdev`, `r/SideProject`, `r/IndieHackers`
   - Hacker News “Show HN”
   - Product Hunt (free to list; schedule for Tuesday 12:01 AM PST for max visibility)
   - Dev.to (write a “How I Built This” post linking to the tool)

### Phase 3 Expected Earnings
| Source | Conservative | Optimistic |
|--------|-------------|------------|
| Ko-fi donations / “Buy Me a Coffee” | $5–$20/month | $30–$100/month |
| Gumroad “Pro” upgrade | $10–$30/month | $50–$200/month |
| Affiliate (hosting, dev tools) | $0–$10/month | $20–$60/month |
| Ads (Carbon/EthicalAds at 10k+ pageviews) | $0 | $50–$150/month |
| **Phase 3 Total** | **$15–$60/month** | **$150–$510/month** |

**Realistic blended estimate:** **$50–$200/month** by Week 8 with consistent posting and one Product Hunt launch.

---

## Phase 4: Scale with Real Data (Ongoing)

> **Goal:** Stop guessing. Use data to double down on what works. Reinvest settlement capital into high-ROI channels.

### Data Sources to Monitor Weekly

#### 1. Google Trends
- **URL:** `https://trends.google.com/trends`
- **How to use:**
  - Enter your niche keywords: *“AI automation,” “Notion templates,” “prompt engineering”*
  - Filter by country (US) and time frame (Past 90 days).
  - Look for rising queries (breakout terms) and create content around them within 48 hours.
- **Action:** Feed breakout keywords to the Content Agent (`money_engine/agents/content_agent.py`) for instant blog drafts.

#### 2. Amazon Best Sellers
- **URL:** `https://www.amazon.com/gp/bestsellers`
- **How to use:**
  - Browse “Computers & Technology,” “Business & Money,” and “Kindle Store.”
  - Find gaps: high-ranking books with <100 reviews = opportunity for a better ebook.
  - Mirror their cover style and title format.
- **Action:** Use the Licensing Agent to generate competing ebook outlines; publish on Gumroad at 50% of the Amazon price.

#### 3. TikTok Creative Center
- **URL:** `https://ads.tiktok.com/business/en-US/solutions/tiktok-for-business/creative-center`
- **How to use:**
  - Check “Trending Hashtags” and “Top Ads” in your niche.
  - Repurpose the top 3 ad concepts into Pinterest pins or short-form blog intros.
- **Action:** If a product trend spikes (e.g., a new AI gadget), publish a review post with Amazon affiliate links within 24 hours.

### A/B Testing Framework

You already have a Data Science Agent concept via the swarm backend. Here is a lightweight framework you can run locally:

```
Hypothesis → Variant A (Control) vs. Variant B (Test) → Traffic Split → Metric → Winner
```

| Test | What to Split | Metric | Tool |
|------|--------------|--------|------|
| Gumroad price | $7 vs. $12 | Conversion rate | Gumroad analytics |
| Email subject line | “3 AI Tools” vs. “Save 10 Hours” | Open rate | ConvertKit |
| Pin design | Text-heavy vs. Minimalist | Click-through | Pinterest analytics |
| Blog CTA | Inline link vs. Box | Click rate | Medium stats + UTM params |

**Automation:**
- Use the swarm’s `generate_email_sequence` to create 2 subject-line variants.
- Use `generate_blog_post` to create 2 intro styles.
- Manually publish both and track for 7 days.
- Scale the winner. Kill the loser.

### Reinvestment Strategy (Post-Settlement)

When the settlement arrives, deploy capital in this priority order:

| Priority | Investment | Expected ROI | Why |
|----------|-----------|--------------|-----|
| 1 | Domain + Hosting ($50–$100/year) | Infinite (fixed cost) | Own your platform; no Medium algo risk |
| 2 | Etsy Plus / Shopify Starter ($5–$29/month) | 3–5x | POD + digital product storefront |
| 3 | Paid ads ($100–$300 test budget) | 1.5–3x | Pinterest + Meta ads for top-performing Gumroad product |
| 4 | Better GPU or dedicated server ($300–$600) | 2–4x | More compute rental income; faster asset generation |
| 5 | Freelancer / VA ($100–$200/month) | 2–3x | Outsource Pin creation, email scheduling, outreach |

> **Never reinvest more than 20% of settlement into any single experiment.** Split tests first, then scale winners.

---

## Appendix A: Free Tools & APIs

### Content & Publishing
| Tool | Purpose | Free Tier Limits | Link |
|------|---------|-----------------|------|
| Medium | Blog hosting | Unlimited posts | `https://medium.com` |
| Substack | Newsletter + blog | Unlimited subs; paid tier at 10% fee | `https://substack.com` |
| Pinterest Business | Traffic driver | Unlimited pins | `https://business.pinterest.com` |
| Canva | Graphic design | 5 GB storage, 250k+ templates | `https://canva.com` |
| X/Twitter | Micro-content | Unlimited posts | `https://x.com` |
| Dev.to | Dev audience | Unlimited posts | `https://dev.to` |
| Hacker News | Launch visibility | Free submission | `https://news.ycombinator.com` |
| Product Hunt | Launch visibility | Free listing | `https://producthunt.com` |

### Digital Product Platforms
| Tool | Fee | Payout Threshold | Link |
|------|-----|-----------------|------|
| Gumroad | 10% + $0.30 | $10 (weekly) or $0.10 (instant deposit with fee) | `https://gumroad.com` |
| Payhip | 5% | No minimum | `https://payhip.com` |
| Leanpub | 80% to author | $40 minimum | `https://leanpub.com` |
| Ko-fi | 0% (Gold is $6/mo) | $0 (PayPal/Stripe direct) | `https://ko-fi.com` |
| Redbubble | Artist margin | $20 minimum | `https://redbubble.com` |
| Printify | Free plan | Pay per order | `https://printify.com` |

### Hosting & Infrastructure
| Tool | Purpose | Free Tier | Link |
|------|---------|-----------|------|
| Vercel | Static / Next.js hosting | 100 GB bandwidth, serverless functions | `https://vercel.com` |
| Netlify | Static hosting | 100 GB bandwidth, 300 build mins | `https://netlify.com` |
| Render | Web services + databases | 750 hrs/mo Web Service, 1 Postgres instance | `https://render.com` |
| Supabase | Postgres + Auth | 500 MB DB, 2 GB egress | `https://supabase.com` |
| Clerk | Auth / user management | 10,000 monthly active users | `https://clerk.com` |
| GitHub Pages | Static sites | 1 GB, soft bandwidth limit | `https://pages.github.com` |

### Analytics & Research
| Tool | Purpose | Free Tier | Link |
|------|---------|-----------|------|
| Google Trends | Keyword trends | Unlimited | `https://trends.google.com` |
| Google Analytics | Web analytics | Unlimited | `https://analytics.google.com` |
| Pinterest Analytics | Pin performance | Unlimited with business account | Built-in |
| TikTok Creative Center | Ad / trend research | Unlimited | `https://ads.tiktok.com/business` |
| Amazon Best Sellers | Product research | Unlimited | `https://www.amazon.com/gp/bestsellers` |
| UTM Builder | Campaign tracking | Unlimited | `https://ga-dev-tools.google/ga4/campaign-url-builder/` |

### Compute Monetization
| Platform | Payout Model | Min Payout | Link |
|----------|-------------|-----------|------|
| Salad.com | Crypto or USD | $5.00 | `https://salad.com` |
| Vast.ai | USD (Stripe) | $5.00 | `https://vast.ai` |
| RunPod | USD (Stripe) | $1.00 | `https://runpod.io` |

### Affiliate Networks
| Network | Approval | Payout Threshold | Link |
|---------|----------|-----------------|------|
| ClickBank | Instant | $10 | `https://clickbank.com` |
| Amazon Associates | Instant (3 sales in 180 days to stay active) | $10 | `https://affiliate-program.amazon.com` |
| Impact | 1–5 days (per brand) | Varies by brand | `https://impact.com` |
| CJ Affiliate | 1–3 days | $50 | `https://cj.com` |
| ShareASale | 1–2 days | $50 | `https://shareasale.com` |

---

## Appendix B: Hardware Utilization Schedule

### GPU Time Allocation (RTX A4500, 20 GB)

| Window | Hours/Day | Allocation | Notes |
|--------|-----------|------------|-------|
| 00:00 – 07:00 | 7 | Compute rental (Salad/Vast/RunPod) | No swarm inference; pre-warm Ollama at 06:45 |
| 07:00 – 08:00 | 1 | Ollama warm-up + model preload | Load 7B model into VRAM |
| 08:00 – 12:00 | 4 | Swarm inference (Money Engine) | Content generation, asset creation |
| 12:00 – 13:00 | 1 | Optional compute rental or idle | Lunch break |
| 13:00 – 18:00 | 5 | Swarm inference + local LLM tasks | Lead gen, email sequences, app building |
| 18:00 – 20:00 | 2 | Render / batch GPU jobs | Video export, image generation, ComfyUI |
| 20:00 – 23:00 | 3 | Light Ollama use + monitoring | Chat-based research, P&L review |
| 23:00 – 00:00 | 1 | Transition to rental | Drain swarm GPU agents, flush VRAM |

**Daily GPU math:**
- Compute rental: **7–8 hours/day** → ~$3–$7/day
- Swarm / inference: **12–13 hours/day** → revenue via content & products
- Transition / idle: **1–2 hours/day** → buffer for thermal stability

### CPU Time Allocation (AMD EPYC 4C/8T)

| Window | Allocation | Expected Load |
|--------|-----------|--------------|
| 24/7 | Swarm backend (FastAPI, port 58081) | 5–15% |
| 08:00 – 18:00 | Money Engine browser automation + Kimi bridge | 20–40% |
| 00:00 – 07:00 | Background batch jobs (lead scraping, analytics sync) | 30–60% |
| On demand | Salad CPU container (if enabled) | 10–20% |

**Daily CPU math:**
- Swarm backend is lightweight; it can run 24/7 without impacting GPU rental.
- Browser automation (pyautogui) is the heaviest CPU task. Schedule it during waking hours only.
- If you enable Salad CPU sharing, cap it at 20% to prevent UI lag.

### Conflict Resolution Rules

1. **GPU is single-tenant.** Never run Ollama inference and a Vast rental container at the same time. Use a PowerShell toggle script:
   ```powershell
   # gpu_mode.ps1
   param([ValidateSet("swarm","rental")]$mode)
   if ($mode -eq "rental") { Stop-Process -Name "ollama" -ErrorAction SilentlyContinue }
   else { Start-Process "ollama" }
   ```
2. **VRAM flush.** Before switching modes, run `nvidia-smi` to confirm no dangling processes. Kill any zombie Python processes holding GPU memory.
3. **Network ports.** Swarm backend uses 58081. SimplePod uses 58090–58091. Salad/Vast need random high ports. No conflicts expected unless you manually change defaults.
4. **Power / thermals.** The A4500 is a 200 W card. Ensure case airflow is adequate if running 24/7. Monitor with `nvidia-smi -l 10` during the first week.

---

## Final Checklist: Your First 7 Days

| Day | Task | Done |
|-----|------|------|
| 1 | Sign up for Salad.com, ClickBank, Amazon Associates, Gumroad | [ ] |
| 1 | Run `python tools/generate_money_assets.py` to refresh asset inventory | [ ] |
| 2 | Replace `{{AMAZON_ASSOCIATES_TAG}}` in `content/affiliate/*.md` with real tag | [ ] |
| 2 | Publish 3 blog posts to Medium | [ ] |
| 3 | Create 9 Pinterest pins in Canva; link to Medium posts | [ ] |
| 4 | List 2 prompt packs on Gumroad (free tier) | [ ] |
| 4 | Publish affiliate comparison post to Medium | [ ] |
| 5 | Set up Substack; import newsletters as archive | [ ] |
| 5 | Deploy `products/apps/json_formatter` to Vercel | [ ] |
| 6 | Post Twitter thread; add Ko-fi link to all bios | [ ] |
| 6 | Start Salad Bowl in rental mode overnight | [ ] |
| 7 | Review Medium stats + Gumroad views; double down on top performer | [ ] |

---

## Closing Note

You are not starting from zero. You have a GPU that costs most people $1,200, a 10-agent business swarm that generates assets while you sleep, and a catalog of products that just need to be listed. The only missing ingredient is **distribution** — getting what you already built in front of people.

This plan is designed to cost $0, require no new skills, and generate cash flow in 7–14 days. The estimates are conservative. Many builders with less hardware and no automation make $500/month within 60 days. Your stack is stronger than theirs.

**Start with Day 1. Publish something today.**

---

*Document version: 2026-05-28*  
*Next review: After Week 2 completion — update earnings and pivot tactics based on real data.*
