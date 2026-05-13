#!/usr/bin/env python3
"""
Full end-to-end test of the OrbitScribe agent in AUTOPILOT mode.
Simulates the VS Code: extension by reading SSE events and executing tools locally.
"""
import json
import os
import subprocess
import glob
import requests

BASE = "http://127.0.0.1:58081"
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve_path(path_str: str) -> str:
    """Resolve a relative path against the workspace root."""
    if os.path.isabs(path_str):
        return path_str
    return os.path.join(WORKSPACE_ROOT, path_str)


def execute_tool_locally(tool: str, args: dict) -> dict:
    """Execute a tool locally and return the result."""
    try:
        if tool == "read_file":
            p = resolve_path(args.get("path", ""))
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"status": "ok", "data": {"content": content}}

        elif tool == "write_file":
            p = resolve_path(args.get("path", ""))
            content = args.get("content", "")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "ok", "data": {"path": args.get("path", "")}}

        elif tool == "list_files":
            p = resolve_path(args.get("path", "."))
            entries = os.listdir(p)
            files = []
            for name in entries:
                full = os.path.join(p, name)
                files.append({"name": name, "type": "directory" if os.path.isdir(full) else "file"})
            return {"status": "ok", "data": {"files": files}}

        elif tool == "run_command":
            cmd = args.get("command", "")
            result = subprocess.run(cmd, shell=True, cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=30)
            return {
                "status": "ok",
                "data": {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
            }

        elif tool == "search_files":
            query = args.get("query", "")
            pattern = query if "*" in query else f"**/*{query}*"
            matches = glob.glob(pattern, root_dir=WORKSPACE_ROOT, recursive=True)
            return {"status": "ok", "data": {"files": matches[:20]}}

        elif tool == "get_current_weather":
            return {"status": "error", "error": "Weather tools not available in test environment."}

        elif tool == "get_time_at_location":
            return {"status": "error", "error": "Time tools not available in test environment."}

        else:
            return {"status": "error", "error": f"Unknown tool: {tool}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def post_tool_result(session_id: str, request_id: str, tool: str, args: dict, result: dict):
    """Send tool result back to the backend."""
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


def run_autopilot_task(task: str):
    """Run an agent task in autopilot mode and handle tool requests."""
    payload = {
        "message": task,
        "mode": "agent",
        "autonomy_level": "autopilot",
        "batch_mode": False,
    }

    session_id = None
    message_count = 0
    tool_count = 0

    print(f"1) Starting autopilot agent task: {task!r}")
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
            message_count += 1
            sid = event.get("session_id")
            if sid:
                session_id = sid

            # Print key events
            if msg_type == "text":
                chunk = event.get("chunk", "")
                safe = chunk.encode('ascii', 'replace').decode('ascii')
                print(f"   [TEXT] {safe[:120]}{'...' if len(safe) > 120 else ''}")
            elif msg_type == "tool_request":
                tool_count += 1
                req_id = event.get("request_id", "")
                tool = event.get("tool", "")
                args = event.get("args", {})
                print(f"   [TOOL_REQUEST] {tool}({json.dumps(args)})  req_id={req_id}")

                # Execute tool locally and send result back
                result = execute_tool_locally(tool, args)
                print(f"   [TOOL_RESULT] status={result['status']}")
                post_tool_result(session_id or "", req_id, tool, args, result)
            elif msg_type == "task_complete":
                safe_result = str(event.get('result', '')).encode('ascii', 'replace').decode('ascii')
                print(f"   [TASK_COMPLETE] iterations={event.get('iterations')}, result={safe_result[:100]}")
                break
            elif msg_type == "done":
                break
            elif msg_type == "error":
                safe_err = str(event.get('message', '')).encode('ascii', 'replace').decode('ascii')
                print(f"   [ERROR] {safe_err}")
                break

    return session_id, message_count, tool_count


def compact_session(session_id: str):
    """Compact the given session."""
    payload = {"session_id": session_id, "summary": ""}
    resp = requests.post(f"{BASE}/api/compact", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main():
    # Use a task that encourages tool use
    task = (
        "List the files in the project root directory using the list_files tool, "
        "then read README.md using the read_file tool. "
        "Always wrap your tool calls in ```tool blocks."
    )

    session_id, msg_count, tool_count = run_autopilot_task(task)
    print(f"\n   session_id: {session_id}")
    print(f"   events received: {msg_count}")
    print(f"   tools executed: {tool_count}")

    if not session_id:
        print("\nERROR: No session_id found.")
        return

    print(f"\n2) Compacting session {session_id}...")
    result = compact_session(session_id)
    print(f"   {json.dumps(result, indent=2)}")

    if result.get("ok"):
        old_count = result.get("old_message_count", 0)
        new_count = result.get("new_message_count", 0)
        print(f"\nCompact succeeded: {old_count} -> {new_count} messages")
    else:
        print(f"\nCompact failed: {result.get('error')}")


if __name__ == "__main__":
    main()
