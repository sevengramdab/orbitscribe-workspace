# Morning Checklist — What To Do When You Wake Up

> Generated: May 28, 2026 | Your overnight batch is running. This list prioritizes the fastest path to real money.

---

## STEP 1: Publish Content (10 minutes = immediate traffic)

### Substack (fastest path to subscribers)
1. Go to https://substack.com/write
2. Copy-paste from `content/published/substack/nordvpn-vs-expressvpn-which-one-should-you-choose.md`
3. Add your affiliate links where placeholders exist
4. Hit Publish → set to "Free for everyone"
5. Repeat for the other 2 articles (space them 2-3 hours apart)

### Medium (manual only, API is dead)
1. Go to https://medium.com/new-story
2. Copy-paste from `content/published/medium/nordvpn-vs-expressvpn-which-one-should-you-choose.html`
   (Copy the BODY content only, not the `<html>` tags)
3. Add 5 tags: Technology, Software, VPN, Cybersecurity, Review
4. Hit Publish

**Why this first**: Content = traffic. Traffic = clicks. Clicks = commissions. Everything else is prep.

---

## STEP 2: Fix Affiliate Links (5 minutes = enables revenue)

1. Open `content/account_setup/PASTE_KEYS_HERE.env`
2. Fill in:
   - `CLICKBANK_ACCOUNT_NICKNAME` — from ClickBank Profile page
   - `AMAZON_ASSOCIATES_TAG` — from https://affiliate-program.amazon.com/home/account/tag
3. Save the file
4. Run: `python tools/ingest_account_keys.py`
5. Run: `python tools/affiliate_link_manager.py replace --interactive`

**Why this second**: Without real affiliate IDs, all links are dead. This is the revenue valve.

---

## STEP 3: Check Overnight Batch (2 minutes)

Look in `content/overnight/` for:
- 3 new comparison articles (Notion vs Trello vs Asana, etc.)
- A lead magnet ebook (`software_buyers_guide_2025.md`)
- 5-email nurture sequence
- A landing page (`stackcompare.html`)

If the folder exists and has files, the batch worked. If empty, check `overnight_asset_generator.py` output.

---

## STEP 4: ClickBank Setup (10 minutes)

1. Go to https://accounts.clickbank.com/master/dashboard.html
2. Click the **"Complete Profile"** button if it's still there
3. Navigate to Profile → find your **Account Nickname**
4. Go to Affiliate Marketplace → search for products matching your niches:
   - VPN/Privacy: search "VPN"
   - Web Hosting: search "hosting" or "website builder"
   - Design: search "design" or "photoshop"
5. Get HopLinks for 2-3 products and replace placeholders in articles

---

## STEP 5: Share for Traffic (15 minutes)

| Platform | Where to Post |
|----------|--------------|
| Reddit | r/webhosting, r/VPN, r/photoshop, r/sidehustle |
| Twitter/X | Thread comparing the tools, link to Substack |
| LinkedIn | "I compared 3 VPNs so you don't have to" |
| Indie Hackers | "How I'm building a content monetization stack" |

**Pro tip**: Don't drop raw links. Write a genuine 2-3 sentence take, THEN link.

---

## STEP 6: Set Up Lead Magnet (optional, 10 minutes)

1. Upload `content/overnight/lead_magnet/software_buyers_guide_2025.md` to:
   - Gumroad (free, pay-what-you-want) → https://gumroad.com
   - OR ConvertKit (free tier) → https://convertkit.com
2. Create a landing page with the download form
3. Add the download link to your Substack welcome email

---

## STEP 7: MSI Sync

On your MSI laptop:
```bash
git stash
git pull origin master
git stash pop
# Resolve any conflicts manually
```

---

## Expected Timeline to First Dollar

| Action | Time to Revenue |
|--------|----------------|
| Publish 3 articles + share | 24-72 hours |
| Replace affiliate links | Immediate (clicks start tracking) |
| Lead magnet + email list | 1-2 weeks (nurture then pitch) |
| Substack paid tier | After 100+ subscribers |

**Realistic first commission**: $5-50 within 72 hours if you share aggressively.
**Realistic first month**: $50-300 with consistent publishing.

---

## Files You Need Open This Morning

1. `content/account_setup/PASTE_KEYS_HERE.env` — fill missing keys
2. `content/published/substack/` — copy-paste to Substack
3. `content/published/medium/` — copy-paste to Medium
4. `content/overnight/` — review batch-generated assets
5. `content/guides/MONETIZATION_EXECUTION_PLAN.md` — Week 1 daily tasks

---

## If Something Broke Overnight

| Symptom | Fix |
|---------|-----|
| PC went to sleep | Check `tools/keep_awake_headless.pid` — restart if needed |
| Ollama stopped | Run `ollama list` — restart if empty |
| No assets in `content/overnight/` | Check background task output, re-run generator |
| Git sync fails on MSI | `git stash && git pull origin master && git stash pop` |

---

**Go make that first commission.**
