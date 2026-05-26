"""Research Agent — explores the codebase and generates summaries.

Capable of:
- Finding files by pattern or keyword
- Reading and summarizing file contents
- Generating architecture reports
- Cross-referencing imports and dependencies
"""
import os
import json
import glob as pyglob
from typing import List, Dict, Optional
from agents.base import Agent


class ResearchAgent(Agent):
    """Explores codebase and produces structured research reports."""

    def __init__(self):
        super().__init__(
            name="Research",
            role="Investigate codebase, find files, and summarize architecture",
            prompt_template="""You are a senior researcher. Investigate the codebase thoroughly
and report findings in structured JSON.

Task: {task}
Context: {context}""",
        )

    def _find_files(self, pattern: str, root: str = ".") -> List[str]:
        """Find files matching pattern, excluding noise."""
        paths = []
        for p in pyglob.glob(os.path.join(root, "**", pattern), recursive=True):
            if any(x in p for x in ["node_modules", "__pycache__", ".git", "target", "dist"]):
                continue
            paths.append(os.path.relpath(p, root))
        return sorted(paths)[:50]

    def _search_content(self, keyword: str, root: str = ".") -> List[Dict]:
        """Search file contents for keyword."""
        matches = []
        for dirpath, _, filenames in os.walk(root):
            if any(x in dirpath for x in ["node_modules", "__pycache__", ".git", "target", "dist"]):
                continue
            for fname in filenames:
                if not fname.endswith((".py", ".ts", ".js", ".md", ".txt", ".json", ".rs", ".toml")):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines, 1):
                            if keyword.lower() in line.lower():
                                matches.append({
                                    "file": os.path.relpath(fpath, root),
                                    "line": i,
                                    "snippet": line.strip()[:120],
                                })
                                if len(matches) >= 30:
                                    return matches
                except Exception:
                    continue
        return matches

    def _summarize_module(self, fpath: str, root: str = ".") -> Dict:
        """Read a Python/TypeScript file and extract top-level definitions."""
        full = os.path.join(root, fpath)
        summary = {"file": fpath, "classes": [], "functions": [], "imports": []}
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("class "):
                    summary["classes"].append(stripped.split("(")[0].replace("class ", "").strip(":"))
                elif stripped.startswith("def ") and not stripped.startswith("def _"):
                    summary["functions"].append(stripped.split("(")[0].replace("def ", "").strip(":"))
                elif stripped.startswith("import ") or stripped.startswith("from "):
                    summary["imports"].append(stripped)
            summary["imports"] = summary["imports"][:10]
            summary["line_count"] = len(lines)
        except Exception:
            pass
        return summary

    async def explore(self, query: str, root: str = ".") -> Dict:
        """Run a full exploration for the given query."""
        report = {"query": query, "files": [], "matches": [], "summaries": []}

        # Heuristic: if query looks like a file pattern, find files
        if "." in query or "/" in query or "*" in query:
            report["files"] = self._find_files(query, root)

        # Always search content
        report["matches"] = self._search_content(query, root)

        # Summarize top matching files
        seen = set()
        for m in report["matches"][:5]:
            f = m["file"]
            if f not in seen:
                seen.add(f)
                report["summaries"].append(self._summarize_module(f, root))

        return report

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        """Execute research and return JSON report."""
        report = await self.explore(task)
        return json.dumps(report, indent=2, default=str)
