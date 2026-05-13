#!/usr/bin/env python3
"""Test script: run a quick agent task, grab session_id, then compact it."""
import json
import requests

BASE = "http://127.0.0.1:58081"


def get_session_id():
    """Start an agent task and grab the session_id from early SSE events."""
    payload = {
        "message": "Say a short hello",
        "mode": "agent",
        "autonomy_level": "autopilot",
        "batch_mode": False,
    }

    session_id = None
    events = 0

    # Short read timeout - we don't need to wait for the whole task
    with requests.post(
        f"{BASE}/api/chat",
        json=payload,
        stream=True,
        timeout=(10, 5),  # 10s connect, 5s read between events
    ) as resp:
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

            events += 1
            msg_type = event.get("type", "")
            print(f"  [{msg_type}] {json.dumps(event)[:120]}...")

            sid = event.get("session_id")
            if sid:
                session_id = sid
                print(f"   Got session_id: {session_id}")
                break

    return session_id, events


def compact_session(session_id: str):
    """Compact the given session."""
    payload = {
        "session_id": session_id,
        "summary": "",
    }
    resp = requests.post(
        f"{BASE}/api/compact",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    print("1) Starting agent task and capturing session_id...")
    session_id, event_count = get_session_id()
    print(f"   events read: {event_count}")

    if not session_id:
        print("ERROR: No session_id found in stream.")
        return

    print(f"\n2) Compacting session {session_id}...")
    result = compact_session(session_id)
    print(f"   {json.dumps(result, indent=2)}")

    if result.get("ok"):
        print("\nCompact succeeded.")
    else:
        print(f"\nCompact failed: {result.get('error')}")


if __name__ == "__main__":
    main()
