#!/usr/bin/env python3
"""Save continuation context before reloading VS Code:."""
import sys
import os
import json

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
CONTEXT_FILE = os.path.join(TOOLS_DIR, '.reload-context.txt')
HEARTBEAT_FILE = os.path.join(TOOLS_DIR, '.orbitscribe-heartbeat')
SESSION_FILE = os.path.join(TOOLS_DIR, '.kimi-last-session')

if __name__ == '__main__':
    context = sys.argv[1] if len(sys.argv) > 1 else ''
    with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
        f.write(context)
    print(f"[save_context] Saved {len(context)} chars to {CONTEXT_FILE}")

    # Also prime the heartbeat with session ID so crash detection can recover it
    session_id = ''
    try:
        if os.path.exists(SESSION_FILE):
            session_id = open(SESSION_FILE, 'r', encoding='utf-8').read().strip()
    except Exception:
        pass
    try:
        hb = {'timestamp': int(__import__('time').time() * 1000), 'pid': os.getpid(), 'sessionId': session_id}
        with open(HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
            json.dump(hb, f)
    except Exception as e:
        print(f"[save_context] Warning: could not write heartbeat: {e}")
