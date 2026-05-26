"""Intent Router — classifies user requests and dispatches to the right mode/agent/tool.

Agents and subagents can call `route_intent` as a tool to determine which
subsystem should handle a task, then dispatch accordingly.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Intent(str, Enum):
    CODE = "code"           # build app, implement feature, write code
    TEST = "test"           # test, verify, validate
    FIX = "fix"             # debug, repair, patch
    DIAGRAM = "diagram"     # generate diagram, visualize, architecture
    RESEARCH = "research"   # explore, understand, find, investigate
    PLAN = "plan"           # design, architect, plan
    DEPLOY = "deploy"       # build binary, compile, release
    MESH = "mesh"           # aquaculture mesh, sensor, fortress, node
    AOE = "aoe"             # supervisor, container, docker, sandbox
    TOOL = "tool"           # create tool, script, utility
    DEFAULT = "default"     # fallback to ask


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    target_mode: str
    target_roles: List[str]
    reasoning: str


# Keyword maps for fast heuristic classification
INTENT_KEYWORDS: Dict[Intent, List[str]] = {
    Intent.CODE: [
        "build", "app", "implement", "create", "write code",
        "code", "develop", "program", "script", "function", "class",
        "module", "library", "api", "endpoint", "refactor", "feature",
        "add support", "integrate", "hook up", "wire",
    ],
    Intent.TEST: [
        "test", "verify", "validate", "check", "assert", "coverage",
        "unit test", "integration test", "pytest", "jest", "spec",
        "regression", "benchmark", "performance test",
    ],
    Intent.FIX: [
        "fix", "debug", "repair", "patch", "resolve", "troubleshoot",
        "broken", "error", "crash", "bug", "exception", "fails",
        "not working", "doesn't work", "broken",
    ],
    Intent.DIAGRAM: [
        "diagram", "visualize", "architecture", "draw", "chart",
        "flowchart", "uml", "erd", "schema", "graph", "mermaid",
        "plantuml", "structure", "overview",
    ],
    Intent.RESEARCH: [
        "research", "explore", "understand", "find", "investigate",
        "look into", "check out", "learn about", "how does", "what is",
        "explain", "document", "readme",
    ],
    Intent.PLAN: [
        "plan", "design", "architect", "strategy", "roadmap",
        "approach", "breakdown", "steps", "blueprint", "layout",
    ],
    Intent.DEPLOY: [
        "deploy", "compile", "build binary", "release", "package",
        "distribution", "dockerize", "containerize", "ship",
        "cargo build", "rustc", "executable",
    ],
    Intent.MESH: [
        "mesh", "aquaculture", "sensor", "fortress", "node",
        "telemetry", "dag", "relay", "actuator", "ph level",
        "alkaline pump", "intake valve", "ephemeral",
        "coral node", "archipelago", "life support",
    ],
    Intent.AOE: [
        "aoe", "supervisor", "container", "docker", "sandbox",
        "cgroup", "memory limit", "failsafe", "wipe state",
        "process manager", "daemon", "watchdog",
    ],
    Intent.TOOL: [
        "tool", "utility", "cli", "command line", "script",
        "automation", "bot", "generator", "converter",
    ],
}


def classify_intent(message: str) -> IntentResult:
    """Classify user message into an intent using keyword heuristics.

    Returns the best match with confidence score, target mode, and roles.
    """
    text = message.lower().strip()
    scores: Dict[Intent, float] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in text:
                # Longer matches get higher weight (more specific)
                score += len(kw) / 10.0
        scores[intent] = score

    # Normalize against max possible score for fairness
    max_score = max(scores.values()) if scores else 0.0
    if max_score > 0:
        for intent in scores:
            scores[intent] = min(scores[intent] / max_score, 1.0)

    best_intent = max(scores, key=scores.get) if scores else Intent.DEFAULT
    best_score = scores.get(best_intent, 0.0)

    # Threshold: if best score is too low, fall back to default
    if best_score < 0.2:
        best_intent = Intent.DEFAULT
        best_score = 1.0 - best_score

    return _map_intent(best_intent, best_score)


def _map_intent(intent: Intent, confidence: float) -> IntentResult:
    """Map classified intent to execution parameters."""
    mapping = {
        Intent.CODE:    ("swarm",    ["architect", "coder", "tester", "reviewer"],  "Coding swarm: architect -> coder -> tester -> reviewer"),
        Intent.TEST:    ("swarm",    ["tester", "debugger", "coder"],               "Test-focused swarm: tester -> debugger -> coder"),
        Intent.FIX:     ("swarm",    ["debugger", "coder", "tester"],               "Debug swarm: debugger -> coder -> tester"),
        Intent.DIAGRAM: ("agent",    ["diagram"],                                   "Diagram agent: generate architecture visualization"),
        Intent.RESEARCH:("agent",    ["researcher"],                                "Research agent: investigate codebase/docs"),
        Intent.PLAN:    ("plan",     ["plan"],                                      "Plan mode: step-by-step architecture design"),
        Intent.DEPLOY:  ("agent",    ["executor"],                                  "Deploy agent: build binary/package/release"),
        Intent.MESH:    ("mesh",     ["coordinator", "telemetry", "dag_router"],    "Aquaculture mesh: 10-agent sensor DAG"),
        Intent.AOE:     ("aoe",      ["supervisor"],                                "AOE supervisor: process manager / sandbox"),
        Intent.TOOL:    ("swarm",    ["architect", "coder", "executor"],            "Tool-building swarm: design -> code -> execute"),
        Intent.DEFAULT: ("ask",      ["ask"],                                       "Ask mode: direct Q&A with grounding"),
    }
    mode, roles, reasoning = mapping.get(intent, mapping[Intent.DEFAULT])
    return IntentResult(
        intent=intent,
        confidence=confidence,
        target_mode=mode,
        target_roles=roles,
        reasoning=reasoning,
    )


async def route_intent(message: str, session_id: str) -> Dict:
    """Top-level entrypoint for intent routing. Returns dispatch metadata."""
    result = classify_intent(message)
    return {
        "status": "ok",
        "intent": result.intent.value,
        "confidence": round(result.confidence, 2),
        "target_mode": result.target_mode,
        "target_roles": result.target_roles,
        "reasoning": result.reasoning,
        "session_id": session_id,
    }
