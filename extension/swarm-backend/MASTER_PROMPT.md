# MASTER PROMPT — Etsy/Printify Dropshipping Business Builder

Paste this entire prompt into the OrbitScribe dashboard (Swarm mode) and press Enter.

---

## MISSION
Build a complete Etsy + Printify dropshipping business automation system in the workspace. Create REAL business files with actual content, not placeholder code.

## BACKGROUND KNOWLEDGE
Read these template files for API details:
- `templates/printify_api_guide.md` — Printify API endpoints
- `templates/stripe_api_guide.md` — Stripe payment integration
- `templates/etsy_listing_guide.md` — Etsy SEO and pricing strategy

## REQUIRED OUTPUT FILES
Create ALL of these files in the workspace:

### 1. `products.json` — Product Catalog
10 print-on-demand products. Each product must have:
- `id` (1-10)
- `title` (SEO-optimized, under 140 chars)
- `description` (5-7 sentences, benefit-focused)
- `tags` (array of 13 tags)
- `etsy_price` (USD string like "$24.99")
- `printify_cost` (USD float like 8.50)
- `profit_margin` (percentage string like "65%")
- `blueprint_id` (Printify blueprint number)
- `image_prompt` (AI image generation prompt for the design)
- `niche` (one of: celestial, botanical, pet, motivational, dark-academia, cottagecore, retro, japanese, spiritual, gaming)

Choose trending niches. Prices must be realistic ($19.99-$39.99).

### 2. `etsy_listings.csv` — Ready-to-Upload Listings
Columns: title, description, tags, price, quantity, image_urls, category, who_made, is_supply, when_made, is_digital
One row per product. Description column must be FULL text.

### 3. `printify_integration.py` — Printify Automation Script
Python script that:
- Loads products.json
- Has functions: `create_product(shop_id, product_data)`, `publish_product(shop_id, product_id)`, `list_blueprints()`, `list_providers(blueprint_id)`
- Uses requests library with Bearer auth
- Has `if __name__ == "__main__"` demo that prints the first product creation payload
- All functions have docstrings

### 4. `stripe_checkout.py` — Stripe Payment Integration
Python script that:
- Loads products.json
- Has function `create_checkout_session(product)` that returns a Stripe checkout URL
- Has function `create_stripe_products(products)` that creates Stripe products + prices
- Uses stripe Python SDK
- Has placeholder API key: `stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_your_key_here")`

### 5. `storefront.html` — Product Gallery Page
Beautiful dark-themed HTML page with:
- Product grid (responsive CSS grid)
- Each product card: image placeholder, title, price, "Buy Now" button linking to Stripe checkout
- CSS in `<style>` block (no external files)
- Professional typography and spacing

### 6. `business_plan.md` — Complete Business Plan
Sections:
- Executive Summary
- Market Research (niches, competitors, trends)
- Product Strategy (10 products with rationale)
- Pricing Model (cost + margin breakdown)
- Operations (Printify workflow, fulfillment)
- Marketing (Etsy SEO, Pinterest, Instagram)
- Financial Projections (month 1-12 revenue estimates)
- Action Checklist (next 10 steps)

### 7. `README.md` — Setup Instructions
Step-by-step guide for:
1. Getting Printify API key
2. Getting Stripe API key
3. Setting up Etsy shop
4. Running printify_integration.py
5. Running stripe_checkout.py
6. Uploading listings to Etsy

## RESEARCH INSTRUCTIONS
Before creating files, use web_search to research:
1. "trending Etsy print on demand niches 2026"
2. "best selling Printify products 2026"
3. "Etsy SEO tags for wall art"

If web_search fails or returns no results, use the niche knowledge from `templates/etsy_listing_guide.md`.

## QUALITY RULES
- All prices must be REALISTIC (not $999 or $0.01)
- All descriptions must be FULL sentences (not "Lorem ipsum")
- All Python code must be FUNCTIONAL (no syntax errors)
- All tags must be Etsy-appropriate (no special chars except spaces)
- File paths MUST use `./` prefix (e.g., `./products.json`)
- write_file MUST include FULL content argument

## EXECUTION ORDER
1. Researcher reads templates and searches web for trends
2. Architect designs the full system and assigns products to niches
3. Coder creates ALL 7 files with real content
4. Tester verifies all files exist, JSON is valid, Python syntax is correct
5. Debugger fixes any issues
6. Executor creates a summary of all deliverables

DO NOT create toy scripts. Create REAL business files. The user will use these to launch an actual store.
