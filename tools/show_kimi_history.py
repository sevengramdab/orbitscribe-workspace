#!/usr/bin/env python3
"""
Show Kimi CLI chat history for a given session.
Parses the session's context.jsonl and prints the last N turns
in a terminal-friendly format.

Usage:
    python show_kimi_history.py <session_id> [--turns N]
    python show_kimi_history.py --last          # show history for most recent session
"""

import argparse
import json
import glob
import os
import sys


def find_session_dir(session_id: str) -> str | None:
    """Locate the session directory under ~/.kimi/sessions."""
    sessions_root = os.path.expanduser("~/.kimi/sessions")
    pattern = os.path.join(sessions_root, "*", session_id)
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def find_most_recent_session() -> tuple[str, str] | None:
    """Return (session_id, session_dir) for the most recently modified session."""
    sessions_root = os.path.expanduser("~/.kimi/sessions")
    best = None
    for parent in os.listdir(sessions_root):
        parent_path = os.path.join(sessions_root, parent)
        if not os.path.isdir(parent_path):
            continue
        for child in os.listdir(parent_path):
            child_path = os.path.join(parent_path, child)
            if not os.path.isdir(child_path):
                continue
            mtime = os.path.getmtime(child_path)
            if best is None or mtime > best[0]:
                best = (mtime, child, child_path)
    if best is None:
        return None
    return best[1], best[2]


def extract_text(content):
    """Extract plain text from a message content field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if part.get("type") == "text":
                texts.append(part.get("text", ""))
        return "\n".join(texts)
    return ""


def is_system_message(text: str) -> bool:
    """Return True if the message is a system/compaction frame."""
    if not text:
        return True
    return text.startswith("<system>") or text.startswith("<current_focus>")


def load_history(session_dir: str, max_turns: int = 10):
    """Load the last N user/assistant turns from context.jsonl."""
    context_file = os.path.join(session_dir, "context.jsonl")
    if not os.path.isfile(context_file):
        return []

    # Read all lines — jsonl is line-delimited
    with open(context_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    turns = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        role = obj.get("role", "")
        if role not in ("user", "assistant"):
            continue

        text = extract_text(obj.get("content", ""))
        if is_system_message(text):
            continue

        # For assistant, prefer visible text over think blocks
        if role == "assistant":
            content = obj.get("content", [])
            visible_texts = []
            if isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        t = part.get("text", "")
                        if not t.startswith("<system>"):
                            visible_texts.append(t)
            text = "\n".join(visible_texts)
            if not text.strip():
                continue

        # Collapse consecutive messages from same role
        if turns and turns[-1]["role"] == role:
            turns[-1]["text"] += "\n" + text
        else:
            turns.append({"role": role, "text": text})

    # Return last N turns, but ensure we have pairs when possible
    return turns[-max_turns * 2:]


# Force UTF-8 on Windows terminals, swallow encoding errors gracefully
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ANSI colors — disabled on Windows unless explicitly supported
if sys.platform == "win32" and os.environ.get("TERM") is None:
    CYAN = GREEN = DIM = RESET = BOLD = ""
else:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_history(turns: list, width: int = 78):
    """Print formatted chat history to stdout."""
    if not turns:
        print("[No chat history found for this session.]")
        return

    # Use ASCII-only borders for Windows console compatibility
    header = "+-- Chat History (last {} turns) ".format(len(turns) // 2 + len(turns) % 2)
    header += "-" * (width - len(header) - 1) + "+"
    footer = "+" + "-" * (width - 2) + "+"

    print(header)
    for turn in turns:
        if turn["role"] == "user":
            label = f"{BOLD}{CYAN}You:{RESET}"
        else:
            label = f"{BOLD}{GREEN}Kimi:{RESET}"

        text = turn["text"].strip()
        # Truncate very long messages
        max_len = 400
        if len(text) > max_len:
            text = text[:max_len] + " ..."

        # Word-wrap to width
        lines = []
        for paragraph in text.splitlines():
            while len(paragraph) > width - 4:
                lines.append(paragraph[: width - 4])
                paragraph = paragraph[width - 4 :]
            lines.append(paragraph)

        for i, line in enumerate(lines):
            if i == 0:
                print(f"| {label} {line}")
            else:
                print(f"|      {line}")
        print(f"|")
    print(footer)


def main():
    parser = argparse.ArgumentParser(description="Show Kimi CLI chat history")
    parser.add_argument("session", nargs="?", help="Session ID to show history for")
    parser.add_argument("--turns", type=int, default=8, help="Number of turns to show (default: 8)")
    parser.add_argument("--last", action="store_true", help="Use the most recent session")
    args = parser.parse_args()

    if args.last or not args.session:
        result = find_most_recent_session()
        if result is None:
            print("[No Kimi sessions found.]", file=sys.stderr)
            sys.exit(1)
        session_id, session_dir = result
        print(f"{DIM}Session: {session_id}{RESET}")
    else:
        session_dir = find_session_dir(args.session)
        if session_dir is None:
            print(f"[Session {args.session} not found.]", file=sys.stderr)
            sys.exit(1)

    turns = load_history(session_dir, max_turns=args.turns)
    print_history(turns)


if __name__ == "__main__":
    main()
