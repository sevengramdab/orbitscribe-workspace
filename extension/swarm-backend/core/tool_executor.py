"""
ToolExecutor — Direct local execution of file, shell, and web tools in the workspace.
This allows subagents in swarm mode to actually DO work instead of just generating text essays.
"""

import os
import subprocess
import glob
import urllib.request
import urllib.parse
import re
from typing import Dict, Any

from core import config


def _get_workspace_root() -> str:
    """Attempt to find the workspace root from common markers."""
    # Prefer the workspace root set by the extension
    if config.WORKSPACE_ROOT and os.path.isdir(config.WORKSPACE_ROOT):
        return config.WORKSPACE_ROOT
    cwd = os.getcwd()
    markers = ['.git', 'package.json', 'pyproject.toml', 'requirements.txt', 'README.md']
    current = cwd
    for _ in range(5):
        for marker in markers:
            if os.path.exists(os.path.join(current, marker)):
                return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return cwd


# Note: call _get_workspace_root() dynamically — config.WORKSPACE_ROOT may be updated at runtime
# WORKSPACE_ROOT = _get_workspace_root()  # removed: evaluated lazily below


def _resolve_path(file_path: str) -> str:
    """Resolve a relative path against the workspace root."""
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(_get_workspace_root(), file_path)


def _web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web using DuckDuckGo HTML API (no key required)."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Try multiple regex patterns for DuckDuckGo result blocks
        results = []
        patterns = [
            # Classic DuckDuckGo
            r'<a[^>]*class="result__a"[^>]*href="(https?://[^"]+)"[^>]*>([^<]+)</a>',
            # Alternative format
            r'<a[^>]*href="(https?://[^"]+)"[^>]*class="result__a"[^>]*>([^<]+)</a>',
            # Result title links
            r'<a[^>]*href="(https?://[^"]+)"[^>]*class="result__snippet"[^>]*>([^<]+)</a>',
            # Generic result links
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]{10,200})</a>',
        ]
        for pattern in patterns:
            if len(results) >= max_results:
                break
            for match in re.finditer(pattern, html, re.IGNORECASE):
                href = match.group(1)
                title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                if href and title and len(title) > 5 and 'duckduckgo' not in href.lower():
                    if not any(r["url"] == href for r in results):
                        results.append({"title": title, "url": href})
                if len(results) >= max_results:
                    break

        if not results:
            # Fallback: try to extract any useful text snippets from the HTML
            snippets = []
            for match in re.finditer(r'<[^>]*class="result__snippet"[^>]*>([^<]{30,500})</a>', html):
                text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                if text:
                    snippets.append(text)
            if snippets:
                return {"status": "ok", "data": {"results": [{"title": "Search snippet", "url": "", "snippet": s} for s in snippets[:max_results]], "query": query, "note": "Results found as text snippets."}, "error": ""}
            return {"status": "ok", "data": {"results": [], "query": query, "note": "No results found. Use known market data from templates/etsy_listing_guide.md instead."}, "error": ""}

        return {"status": "ok", "data": {"results": results[:max_results], "query": query}, "error": ""}
    except Exception as e:
        return {"status": "error", "data": None, "error": f"Web search failed: {str(e)}. Use known market data from templates/etsy_listing_guide.md instead."}


def execute_tool(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool directly in the local workspace.
    Returns a dict matching the extension's tool result format.
    """
    try:
        if tool == "read_file":
            path_arg = args.get("path", "") or args.get("file", "") or args.get("filename", "")
            if not path_arg:
                return {"status": "error", "data": None, "error": "Missing required argument: path. Use args={\"path\": \"<file path>\"}"}
            path = _resolve_path(path_arg)
            if not os.path.exists(path):
                return {"status": "error", "data": None, "error": f"File not found: {path}"}
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return {"status": "ok", "data": {"content": content}, "error": ""}

        elif tool == "write_file":
            path_arg = args.get("path", "")
            if not path_arg:
                return {"status": "error", "data": None, "error": "Missing required argument: path. Use args={\"path\": \"<file path>\", \"content\": \"<content>\"}"}
            path = _resolve_path(path_arg)
            content = args.get("content", "")
            if content is None:
                return {"status": "error", "data": None, "error": "Missing required argument: content. Use args={\"path\": \"<file path>\", \"content\": \"<content>\"}"}
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            original = None
            if os.path.exists(path) and os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    original = f.read()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "ok", "data": {"path": path_arg, "size": len(content)}, "error": ""}

        elif tool == "list_files":
            dir_path = _resolve_path(args.get("path", "."))
            if not os.path.exists(dir_path):
                return {"status": "error", "data": None, "error": f"Directory not found: {dir_path}"}
            entries = []
            try:
                for name in os.listdir(dir_path):
                    full = os.path.join(dir_path, name)
                    entries.append({"name": name, "type": "directory" if os.path.isdir(full) else "file"})
            except PermissionError:
                return {"status": "error", "data": None, "error": f"Permission denied: {dir_path}"}
            return {"status": "ok", "data": {"files": entries}, "error": ""}

        elif tool == "run_command":
            command = args.get("command", "")
            if not command:
                return {"status": "error", "data": None, "error": "No command provided"}
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=_get_workspace_root(),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {
                    "status": "ok" if result.returncode == 0 else "error",
                    "data": {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "code": result.returncode,
                    },
                    "error": result.stderr if result.returncode != 0 else "",
                }
            except subprocess.TimeoutExpired:
                return {"status": "error", "data": {"stdout": "", "stderr": "", "code": -1}, "error": "Command timed out after 30s"}
            except Exception as e:
                return {"status": "error", "data": {"stdout": "", "stderr": "", "code": -1}, "error": str(e)}

        elif tool == "search_files":
            query = args.get("query", "")
            if not query:
                return {"status": "error", "data": None, "error": "No query provided"}
            pattern = f"**/*{query}*" if "*" not in query else query
            try:
                matches = glob.glob(pattern, root_dir=_get_workspace_root(), recursive=True)
                # Filter out common noise
                filtered = [m for m in matches if "node_modules" not in m and "__pycache__" not in m and ".git" not in m]
                return {"status": "ok", "data": {"files": filtered[:50]}, "error": ""}
            except Exception as e:
                return {"status": "error", "data": None, "error": str(e)}

        elif tool == "web_search":
            query = args.get("query", "")
            if not query:
                return {"status": "error", "data": None, "error": "No search query provided"}
            max_results = args.get("max_results", 5)
            return _web_search(query, max_results)

        elif tool == "get_current_weather":
            return {"status": "error", "data": None, "error": "Weather tool not available in backend."}

        elif tool == "get_time_at_location":
            return {"status": "error", "data": None, "error": "Time tool not available in backend."}

        else:
            return {"status": "error", "data": None, "error": f"Unknown tool: {tool}"}

    except Exception as e:
        return {"status": "error", "data": None, "error": f"Tool execution crashed: {str(e)}"}
