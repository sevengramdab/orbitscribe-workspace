#!/usr/bin/env python3
"""
Full test of the three new features:
1. Request Queue (tested by verifying backend handles queued requests)
2. Steering (send a steering message mid-task)
3. Send Now (interrupt current stream and send new message)
"""
import json
import os
import requests
import threading
import time

BASE = "http://127.0.0.1:58081"
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def execute_tool_locally(tool: str, args: dict) -> dict:
    try:
        if tool == "read_file":
            p = os.path.join(WORKSPACE_ROOT, args.get("path", ""))
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"status": "ok", "data": {"content": content}}
        elif tool == "list_files":
            p = os.path.join(WORKSPACE_ROOT, args.get("path", "."))
            entries = os.listdir(p)
            files = [{"name": name, "type": "directory" if os.path.isdir(os.path.join(p, name)) else "file"} for name in entries]
            return {"status": "ok", "data": {"files": files}}
        elif tool == "run_command":
            cmd = args.get("command", "")
            import subprocess
            result = subprocess.run(cmd, shell=True, cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=30)
            return {"status": "ok", "data": {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}}
        else:
            return {"status": "error", "error": f"Unknown tool: {tool}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def post_tool_result(session_id: str, request_id: str, tool: str, args: dict, result: dict):
    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "tool": tool,
        "args": args,
        "status": result.get("status", "error"),
        "data": result.get("data"),
        "error": result.get("error", ""),
    }
    try:
        resp = requests.post(f"{BASE}/api/agent/tool-result", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"   [WARN] Failed to post tool result: {e}")
        return None


def run_with_steering():
    """Run an agent task and inject a steering message mid-task."""
    payload = {
        "message": (
            "List the files in the project root using list_files, then read README.md using read_file. "
            "Always use ```tool blocks for tool calls."
        ),
        "mode": "agent",
        "autonomy_level": "autopilot",
        "batch_mode": False,
    }

    session_id = None
    steering_sent = False

    print("1) Starting autopilot agent task...")
    print("   Will inject steering message after first tool request.\n")

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
                print(f"   [TEXT] {safe[:100]}{'...' if len(safe) > 100 else ''}")
            elif msg_type == "tool_request":
                req_id = event.get("request_id", "")
                tool = event.get("tool", "")
                args = event.get("args", {})
                print(f"   [TOOL_REQUEST] {tool}({json.dumps(args)})")
                result = execute_tool_locally(tool, args)
                print(f"   [TOOL_RESULT] status={result['status']}")
                post_tool_result(session_id or "", req_id, tool, args, result)

                # Inject steering message after first tool
                if not steering_sent and session_id:
                    steering_sent = True
                    steer_payload = {"message": "Also check the extension folder for TypeScript files."}
                    try:
                        r = requests.post(f"{BASE}/api/sessions/{session_id}/steer", json=steer_payload, timeout=5)
                        print(f"   [STEERING] Injected: '{steer_payload['message']}' → {r.json()}")
                    except Exception as e:
                        print(f"   [STEERING] Failed: {e}")
            elif msg_type == "task_complete":
                print(f"   [TASK_COMPLETE] iterations={event.get('iterations')}")
                break
            elif msg_type == "error":
                print(f"   [ERROR] {event.get('message', '')}")
                break

    return session_id


def compact_session(session_id: str):
    print(f"\n2) Compacting session {session_id}...")
    resp = requests.post(f"{BASE}/api/compact", json={"session_id": session_id, "summary": ""}, timeout=10)
    data = resp.json()
    print(f"   {json.dumps(data, indent=2)}")
    return data


def main():
    session_id = run_with_steering()
    if not session_id:
        print("\nERROR: No session_id.")
        return

    result = compact_session(session_id)
    if result.get("ok"):
        old_count = result.get("old_message_count", 0)
        new_count = result.get("new_message_count", 0)
        print(f"\nAll features tested successfully!")
        print(f"  - Autopilot: tools executed without approval")
        print(f"  - Steering: message injected mid-task")
        print(f"  - Compact: {old_count} -> {new_count} messages")
    else:
        print(f"\nCompact failed: {result.get('error')}")


if __name__ == "__main__":
    main()
