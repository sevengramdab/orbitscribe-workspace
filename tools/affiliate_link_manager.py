#!/usr/bin/env python3
"""
Affiliate Link Manager

Scans all markdown files in `content/` for affiliate placeholders like:
    {{CLICKBANK_LINK:product_name}}

Reports counts, lists files needing real links, and can batch-replace
placeholders with actual affiliate IDs when provided.

Usage:
    python affiliate_link_manager.py scan
    python affiliate_link_manager.py replace --mapping mapping.json
    python affiliate_link_manager.py replace --interactive
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Regex matching {{CLICKBANK_LINK:product_name}}
CLICKBANK_PATTERN = re.compile(r"\{\{CLICKBANK_LINK:([^}]+)\}\}")

# Base content directory to scan
DEFAULT_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

# Files to exclude from scan/replace (e.g. documentation)
EXCLUDED_FILE_NAMES = {"clickbank_insertions.md"}


def find_markdown_files(content_dir: Path) -> List[Path]:
    """Recursively find all .md files under content_dir."""
    files = sorted(content_dir.rglob("*.md"))
    return [f for f in files if f.name not in EXCLUDED_FILE_NAMES]


def scan_file(path: Path) -> List[Tuple[int, str]]:
    """
    Scan a single markdown file for ClickBank placeholders.
    Returns list of (line_number, placeholder_token) tuples.
    """
    matches: List[Tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Warning: could not read {path}: {exc}", file=sys.stderr)
        return matches

    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in CLICKBANK_PATTERN.finditer(line):
            token = match.group(1).strip()
            matches.append((line_no, token))
    return matches


def scan_content(content_dir: Path) -> Dict[Path, List[Tuple[int, str]]]:
    """
    Scan all markdown files under content_dir.
    Returns mapping of file path -> list of (line_number, token).
    """
    results: Dict[Path, List[Tuple[int, str]]] = {}
    for md_file in find_markdown_files(content_dir):
        matches = scan_file(md_file)
        if matches:
            results[md_file] = matches
    return results


def report(results: Dict[Path, List[Tuple[int, str]]]) -> int:
    """
    Print a human-readable report of placeholders found.
    Returns total number of placeholder occurrences.
    """
    total_occurrences = 0
    unique_tokens: set = set()

    if not results:
        print("No ClickBank placeholders found in content/.")
        return 0

    print(f"{'=' * 60}")
    print(f" CLICKBANK PLACEHOLDER SCAN REPORT")
    print(f"{'=' * 60}\n")

    for path, matches in results.items():
        rel_path = path.relative_to(Path.cwd())
        print(f"[FILE] {rel_path} ({len(matches)} occurrence(s))")
        for line_no, token in matches:
            print(f"   Line {line_no}: {{{{CLICKBANK_LINK:{token}}}}}")
            unique_tokens.add(token)
            total_occurrences += 1
        print()

    print(f"{'=' * 60}")
    print(f"Files needing real links: {len(results)}")
    print(f"Total placeholder occurrences: {total_occurrences}")
    print(f"Unique placeholder tokens: {len(unique_tokens)}")
    print(f"{'=' * 60}")
    return total_occurrences


def replace_in_file(path: Path, mapping: Dict[str, str]) -> Tuple[int, int]:
    """
    Replace placeholders in a single file using the provided mapping.
    Returns (replacements_made, unique_tokens_replaced).
    """
    try:
        original_text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Warning: could not read {path}: {exc}", file=sys.stderr)
        return 0, 0

    replacement_count = 0
    tokens_replaced: set = set()

    def replacer(match: re.Match) -> str:
        nonlocal replacement_count
        token = match.group(1).strip()
        if token in mapping:
            replacement_count += 1
            tokens_replaced.add(token)
            return mapping[token]
        return match.group(0)

    new_text = CLICKBANK_PATTERN.sub(replacer, original_text)

    if replacement_count > 0:
        path.write_text(new_text, encoding="utf-8")

    return replacement_count, len(tokens_replaced)


def batch_replace(content_dir: Path, mapping: Dict[str, str]) -> None:
    """
    Batch-replace all known placeholders under content_dir using mapping.
    mapping keys = placeholder tokens (e.g. 'seo_traffic_course')
    mapping values = actual replacement strings (e.g. full hoplink HTML or markdown)
    """
    results = scan_content(content_dir)
    if not results:
        print("No placeholders found — nothing to replace.")
        return

    total_replacements = 0
    total_files_changed = 0

    for path in results:
        count, _ = replace_in_file(path, mapping)
        if count:
            rel_path = path.relative_to(Path.cwd())
            print(f"[OK] Replaced {count} placeholder(s) in {rel_path}")
            total_replacements += count
            total_files_changed += 1

    print(f"\n[DONE] {total_replacements} replacement(s) across {total_files_changed} file(s).")


def interactive_replace(content_dir: Path) -> None:
    """
    Interactively prompt for replacement values for each unique token found.
    """
    results = scan_content(content_dir)
    if not results:
        print("No placeholders found — nothing to replace.")
        return

    unique_tokens: set = set()
    for matches in results.values():
        for _, token in matches:
            unique_tokens.add(token)

    mapping: Dict[str, str] = {}
    print("Interactive mode — enter the real affiliate link (or HTML/markdown) for each token.")
    print("Leave blank to skip that token.\n")

    for token in sorted(unique_tokens):
        user_input = input(f"  {token}: ").strip()
        if user_input:
            mapping[token] = user_input

    if mapping:
        batch_replace(content_dir, mapping)
    else:
        print("No replacements provided — exiting.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan and replace ClickBank affiliate placeholders in content/"
    )
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=DEFAULT_CONTENT_DIR,
        help="Directory to scan for markdown files (default: ../content)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    subparsers.add_parser("scan", help="Scan for placeholders and print a report")

    # replace command
    replace_parser = subparsers.add_parser("replace", help="Replace placeholders with real links")
    replace_parser.add_argument(
        "--mapping",
        type=Path,
        help="Path to a JSON file mapping token -> replacement string",
    )
    replace_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for replacement values interactively",
    )

    args = parser.parse_args()

    if args.command == "scan" or args.command is None:
        results = scan_content(args.content_dir)
        report(results)
        return 0

    if args.command == "replace":
        if args.interactive:
            interactive_replace(args.content_dir)
        elif args.mapping:
            if not args.mapping.exists():
                print(f"Error: mapping file not found: {args.mapping}", file=sys.stderr)
                return 1
            mapping = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
            if not isinstance(mapping, dict):
                print("Error: mapping JSON must be an object.", file=sys.stderr)
                return 1
            batch_replace(args.content_dir, mapping)
        else:
            print("Error: --mapping or --interactive is required for replace.", file=sys.stderr)
            return 1
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
