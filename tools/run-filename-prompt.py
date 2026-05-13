#!/usr/bin/env python3
"""Use the given filename text as a prompt for the OrbitScribe swarm."""
import json
import requests

BASE = "http://127.0.0.1:58081"


def main():
    filename_text = (
        "backend went offline mid request, we need a queue system for request "
        "and steering option, and oops mode, rename that tho"
    )
    print("Parsed prompt from filename:")
    print(f"  {filename_text}")
    print()

    payload = {
        "message": (
            f"{filename_text}. "
            "Implement these features in the OrbitScribe Swarm extension and backend: "
            "(1) A request queue + retry system for when the backend goes offline mid-request. "
            "(2) A steering option to guide the agent mid-task. "
            "(3) An 'oops' undo/rewind feature with a better name."
        ),
        "mode": "agent",
        "autonomy_level": "autopilot",
        "batch_mode": True,
    }

    session_id = None
    print("Sending to swarm backend (autopilot)...")
    print("-" * 60)

    with requests.post(f"{BASE}/api/chat", json=payload, stream=True, timeout=(10, 300)) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace").strip()
            if not decoded.startswith("data: "):
                continue
            data = decoded[6:]
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = event.get("type", "")
            sid = event.get("session_id")
            if sid:
                session_id = sid

            if msg_type == "text":
                chunk = event.get("chunk", "")
                safe = chunk.encode("ascii", "replace").decode("ascii")
                print(safe, end="", flush=True)
            elif msg_type == "tool_request":
                req_id = event.get("request_id", "")
                tool = event.get("tool", "")
                args = event.get("args", {})
                print(f"\n[TOOL_REQUEST] {tool}({json.dumps(args)}) req_id={req_id}")
            elif msg_type == "task_complete":
                print(f"\n[TASK_COMPLETE] session_id={session_id}")
                break
            elif msg_type == "error":
                print(f"\n[ERROR] {event.get('message', '')}")
                break

    print("-" * 60)
    if session_id:
        print(f"\nSession: {session_id}")


if __name__ == "__main__":
    main()
