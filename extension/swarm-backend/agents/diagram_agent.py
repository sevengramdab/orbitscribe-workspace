"""Diagram Agent — generates architecture diagrams from codebase structure.

Produces Mermaid flowcharts, class diagrams, and DAG visualizations
by reading the project tree and inferring relationships.
"""
import os
import json
from typing import List, Dict
from agents.base import Agent


class DiagramAgent(Agent):
    """Generates Mermaid/PlantUML diagrams from project structure."""

    def __init__(self):
        super().__init__(
            name="Diagram",
            role="Generate architecture diagrams from codebase structure",
            prompt_template="""You are a technical diagrammer. Given project structure and relationships,
generate clear Mermaid or PlantUML diagrams. Prefer Mermaid for markdown embedding.

Task: {task}
Context: {context}""",
        )

    def _scan_project(self, root: str, max_depth: int = 3) -> Dict:
        """Scan project tree up to max_depth."""
        tree = {"name": os.path.basename(root) or root, "children": []}
        try:
            for name in sorted(os.listdir(root)):
                if name.startswith(".") or name in ("node_modules", "__pycache__", "target", "dist", "build"):
                    continue
                path = os.path.join(root, name)
                if os.path.isdir(path):
                    if max_depth > 0:
                        subtree = self._scan_project(path, max_depth - 1)
                        tree["children"].append(subtree)
                    else:
                        tree["children"].append({"name": name + "/", "children": []})
                else:
                    tree["children"].append({"name": name, "children": []})
        except PermissionError:
            pass
        return tree

    def _tree_to_mermaid(self, node: Dict, prefix: str = "", is_last: bool = True) -> str:
        """Convert tree dict to Mermaid flowchart subgraph."""
        lines = []
        name = node.get("name", "root")
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")
        if not safe_id:
            safe_id = "root"
        lines.append(f"    {safe_id}[\"{name}\"]")
        children = node.get("children", [])
        for i, child in enumerate(children):
            child_name = child.get("name", "item")
            child_id = re.sub(r"[^a-zA-Z0-9_]", "_", child_name).strip("_")
            if not child_id:
                child_id = f"item_{i}"
            lines.append(f"    {safe_id} --> {child_id}")
            if child.get("children"):
                lines.extend(self._tree_to_mermaid(child, prefix + "    ", i == len(children) - 1))
        return "\n".join(lines)

    async def generate_project_tree(self, root: str = ".") -> str:
        """Generate a Mermaid flowchart of the project directory tree."""
        tree = self._scan_project(root)
        mermaid = "```mermaid\nflowchart TD\n"
        mermaid += self._tree_to_mermaid(tree)
        mermaid += "\n```"
        return mermaid

    async def generate_agent_dag(self, agents: List[Dict]) -> str:
        """Generate a Mermaid DAG of agent relationships."""
        lines = ["```mermaid", "flowchart LR"]
        for agent in agents:
            aid = re.sub(r"[^a-zA-Z0-9_]", "_", agent["name"])
            lines.append(f"    {aid}[\"{agent['name']}\"]")
        for agent in agents:
            aid = re.sub(r"[^a-zA-Z0-9_]", "_", agent["name"])
            for dep in agent.get("depends_on", []):
                did = re.sub(r"[^a-zA-Z0-9_]", "_", dep)
                lines.append(f"    {did} --> {aid}")
        lines.append("```")
        return "\n".join(lines)

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        """Generate diagram based on task."""
        if "project" in task.lower() or "directory" in task.lower() or "tree" in task.lower():
            diagram = await self.generate_project_tree()
        elif "agent" in task.lower() or "dag" in task.lower() or "mesh" in task.lower():
            # Default aquaculture mesh DAG
            agents = [
                {"name": "Telemetry", "depends_on": []},
                {"name": "DAGRouter", "depends_on": ["Telemetry"]},
                {"name": "PhEvaluator", "depends_on": ["DAGRouter"]},
                {"name": "VolumeEvaluator", "depends_on": ["DAGRouter"]},
                {"name": "ActuatorDispatch", "depends_on": ["PhEvaluator", "VolumeEvaluator"]},
                {"name": "Failsafe", "depends_on": ["ActuatorDispatch"]},
                {"name": "StateWipe", "depends_on": ["Failsafe"]},
            ]
            diagram = await self.generate_agent_dag(agents)
        else:
            diagram = await self.generate_project_tree()

        # Save to file if path provided in context
        if context and context.endswith(".md"):
            with open(context, "w", encoding="utf-8") as f:
                f.write(f"# Architecture Diagram\n\n{diagram}\n")
            return json.dumps({"status": "saved", "path": context, "diagram": diagram})

        return json.dumps({"status": "generated", "diagram": diagram})


import re
