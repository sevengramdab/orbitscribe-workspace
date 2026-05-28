#!/usr/bin/env python3
"""
extract_account_keys.py
=======================
Uses BrowserController to navigate to Medium/Substack/ClickBank settings
and extract API keys / account info via JavaScript console injection.

The user must already be logged into these services in Chrome.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "money_engine"))
sys.path.insert(0, str(Path(__file__).parent.parent))
from browser_controller import BrowserController

RESULTS_PATH = Path("content/account_setup/extracted_keys.json")


def extract_medium_token(bc: BrowserController) -> dict:
    """Navigate to Medium settings and try to extract integration token."""
    print("[extract] Navigating to Medium settings...")
    bc.navigate("https://medium.com/me/settings/security")
    time.sleep(3)
    bc.screenshot("medium_security_page.png")

    # Try to extract token via JS - Medium shows it in a visible text field
    js = """
    (function() {
        // Look for integration token input/field
        var inputs = document.querySelectorAll('input, textarea, code, pre');
        for (var i = 0; i < inputs.length; i++) {
            var val = inputs[i].value || inputs[i].textContent || '';
            if (val.length > 30 && val.match(/^[a-f0-9]+$/i)) {
                return {found: true, token: val, source: 'input/textarea'};
            }
        }
        // Look for any element containing "Integration token" label
        var labels = document.querySelectorAll('*');
        for (var j = 0; j < labels.length; j++) {
            var txt = labels[j].textContent || '';
            if (txt.toLowerCase().includes('integration token')) {
                var parent = labels[j].parentElement;
                if (parent) {
                    var sibling = parent.querySelector('input, textarea, code, pre');
                    if (sibling) {
                        var tok = sibling.value || sibling.textContent || '';
                        if (tok.length > 20) return {found: true, token: tok, source: 'label-sibling'};
                    }
                }
            }
        }
        return {found: false, html_snippet: document.body.innerText.substring(0, 500)};
    })()
    """
    bc.run_js(js)
    time.sleep(1)
    bc.screenshot("medium_after_js.png")
    print("[extract] Medium extraction attempted. Check screenshots.")
    return {"platform": "medium", "status": "attempted", "screenshots": ["medium_security_page.png", "medium_after_js.png"]}


def extract_substack_info(bc: BrowserController) -> dict:
    """Navigate to Substack publication settings."""
    print("[extract] Navigating to Substack settings...")
    bc.navigate("https://substack.com/settings")
    time.sleep(3)
    bc.screenshot("substack_settings.png")

    js = """
    (function() {
        var data = {};
        // Try to get publication URL from page
        var links = document.querySelectorAll('a[href*="substack.com"]');
        for (var i = 0; i < links.length; i++) {
            var href = links[i].href;
            if (href.includes('.substack.com') && !href.includes('substack.com/settings')) {
                data.publication_url = href;
                break;
            }
        }
        // Try to get publication name
        var h1 = document.querySelector('h1');
        if (h1) data.publication_name = h1.textContent.trim();
        // Get email
        var emailEls = document.querySelectorAll('*');
        for (var j = 0; j < emailEls.length; j++) {
            var txt = emailEls[j].textContent || '';
            if (txt.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/)) {
                data.email = txt.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/)[0];
                break;
            }
        }
        data.html_snippet = document.body.innerText.substring(0, 800);
        return data;
    })()
    """
    bc.run_js(js)
    time.sleep(1)
    bc.screenshot("substack_after_js.png")
    print("[extract] Substack extraction attempted. Check screenshots.")
    return {"platform": "substack", "status": "attempted", "screenshots": ["substack_settings.png", "substack_after_js.png"]}


def extract_clickbank_info(bc: BrowserController) -> dict:
    """Navigate to ClickBank account settings."""
    print("[extract] Navigating to ClickBank accounts...")
    bc.navigate("https://accounts.clickbank.com")
    time.sleep(4)
    bc.screenshot("clickbank_accounts.png")

    js = """
    (function() {
        var data = {};
        // Look for account nickname displayed on page
        var els = document.querySelectorAll('*');
        for (var i = 0; i < els.length; i++) {
            var txt = els[i].textContent || '';
            if (txt.toLowerCase().includes('nickname') || txt.toLowerCase().includes('account')) {
                data.page_text = (data.page_text || '') + txt.substring(0, 200) + ' | ';
            }
        }
        data.html_snippet = document.body.innerText.substring(0, 1000);
        return data;
    })()
    """
    bc.run_js(js)
    time.sleep(1)
    bc.screenshot("clickbank_after_js.png")
    print("[extract] ClickBank extraction attempted. Check screenshots.")
    return {"platform": "clickbank", "status": "attempted", "screenshots": ["clickbank_accounts.png", "clickbank_after_js.png"]}


def main():
    print("=" * 60)
    print("ACCOUNT KEY EXTRACTOR")
    print("=" * 60)
    print("This will control Chrome to navigate to settings pages.")
    print("Make sure Chrome is open and you're logged in.")
    print("=" * 60)

    bc = BrowserController(screenshot_dir="screenshots/extraction")
    Path("screenshots/extraction").mkdir(parents=True, exist_ok=True)

    results = []

    # Check if Chrome is running
    win = bc._find_chrome_window()
    if not win:
        print("[ERROR] Chrome window not found. Please open Chrome and log in first.")
        sys.exit(1)

    print(f"[OK] Found Chrome window: {win.title}")
    bc.focus_chrome()

    # Extract from each platform
    try:
        results.append(extract_medium_token(bc))
    except Exception as e:
        results.append({"platform": "medium", "status": "error", "error": str(e)})

    try:
        results.append(extract_substack_info(bc))
    except Exception as e:
        results.append({"platform": "substack", "status": "error", "error": str(e)})

    try:
        results.append(extract_clickbank_info(bc))
    except Exception as e:
        results.append({"platform": "clickbank", "status": "error", "error": str(e)})

    # Save results
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    for r in results:
        print(f"  {r['platform']}: {r['status']}")
    print(f"\nResults saved to: {RESULTS_PATH}")
    print(f"Screenshots saved to: screenshots/extraction/")
    print("=" * 60)


if __name__ == "__main__":
    main()
