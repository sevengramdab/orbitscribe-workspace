#!/usr/bin/env python3
"""Ollama Model Manager — CLI utility for managing local Ollama models."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

OLLAMA_HOST = "http://localhost:11434"
VRAM_GB = 20  # RTX A4500


def api_get(path: str) -> Any:
    resp = requests.get(f"{OLLAMA_HOST}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_delete(path: str, payload: dict | None = None) -> requests.Response:
    resp = requests.delete(f"{OLLAMA_HOST}{path}", json=payload, timeout=30)
    resp.raise_for_status()
    return resp


def api_post_stream(path: str, payload: dict) -> Any:
    with requests.post(f"{OLLAMA_HOST}{path}", json=payload, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass


def format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:3.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_datetime(dt_str: str | None) -> str:
    if not dt_str:
        return "never"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt_str)


def cmd_list() -> None:
    data = api_get("/api/tags")
    models = data.get("models", [])
    if not models:
        print("No local models found.")
        return

    print(f"{'Model':<40} {'Size':>10} {'Modified':>18} {'Digest':>16}")
    print("-" * 90)
    for m in models:
        name = m.get("name", m.get("model", "unknown"))
        size = format_size(m.get("size", 0))
        modified = format_datetime(m.get("modified_at"))
        digest = m.get("digest", "")[:12]
        print(f"{name:<40} {size:>10} {modified:>18} {digest:>16}")
    print(f"\nTotal models: {len(models)}")


def cmd_pull(model: str) -> None:
    print(f"Pulling model: {model}")
    try:
        for chunk in api_post_stream("/api/pull", {"name": model}):
            status = chunk.get("status", "")
            if "completed" in chunk and "total" in chunk:
                completed = chunk["completed"]
                total = chunk["total"]
                pct = (completed / total * 100) if total else 0
                bar_len = 30
                filled = int(bar_len * completed / total) if total else bar_len
                bar = "█" * filled + "░" * (bar_len - filled)
                print(f"\r[{bar}] {pct:5.1f}% {format_size(completed)} / {format_size(total)}", end="", flush=True)
            elif status:
                print(f"\rStatus: {status}{' ' * 20}", end="", flush=True)
            if chunk.get("error"):
                print(f"\nError: {chunk['error']}")
                sys.exit(1)
        print(f"\nModel '{model}' pulled successfully.")
    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to Ollama at {OLLAMA_HOST}. Is it running?")
        sys.exit(1)


def cmd_remove(model: str) -> None:
    print(f"Removing model: {model}")
    api_delete("/api/delete", {"name": model})
    print(f"Model '{model}' removed.")


def cmd_benchmark(model: str) -> None:
    print(f"Benchmarking model: {model}")
    prompt = "Explain the difference between a list and a tuple in Python. Be concise."
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.7},
    }

    tokens = 0
    start = time.perf_counter()
    first_token_time: float | None = None
    try:
        for chunk in api_post_stream("/api/generate", payload):
            if chunk.get("error"):
                print(f"\nError: {chunk['error']}")
                sys.exit(1)
            if "response" in chunk:
                tokens += 1
                if first_token_time is None:
                    first_token_time = time.perf_counter()
    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to Ollama at {OLLAMA_HOST}. Is it running?")
        sys.exit(1)

    elapsed = time.perf_counter() - start
    ttft = (first_token_time - start) if first_token_time else 0.0
    tok_per_sec = tokens / elapsed if elapsed > 0 else 0.0

    print(f"\n{'='*40}")
    print(f"Tokens generated : {tokens}")
    print(f"Total time       : {elapsed:.2f} s")
    print(f"Time to first tok: {ttft:.3f} s")
    print(f"Throughput       : {tok_per_sec:.2f} tok/s")
    print(f"VRAM (static est): ~{estimate_vram(model):.1f} GB")
    print(f"{'='*40}")


def estimate_vram(model_name: str) -> float:
    """Rough static VRAM estimate based on model name / parameter count."""
    name = model_name.lower()
    mapping = {
        "1b": 0.8,
        "1.5b": 1.2,
        "3b": 2.0,
        "4b": 2.5,
        "7b": 4.5,
        "8b": 5.0,
        "9b": 5.5,
        "13b": 8.0,
        "14b": 8.5,
        "20b": 12.0,
        "27b": 16.0,
        "30b": 18.0,
        "34b": 20.0,
        "40b": 24.0,
        "70b": 40.0,
        "72b": 42.0,
        "110b": 64.0,
    }
    for key, gb in mapping.items():
        if key in name:
            return gb
    return 5.0  # default guess


@dataclass
class ModelRec:
    name: str
    purpose: str
    vram_gb: float
    notes: str


RECOMMENDATIONS: list[ModelRec] = [
    # Coding
    ModelRec("qwen2.5-coder:7b", "coding", 4.5, "Excellent code completion & reasoning"),
    ModelRec("qwen2.5-coder:14b", "coding", 8.5, "Stronger coder, fits comfortably"),
    ModelRec("deepseek-coder-v2:16b-lite", "coding", 10.0, "DeepSeek V2 lite coder variant"),
    ModelRec("codellama:7b", "coding", 4.5, "Meta’s Code Llama, solid baseline"),
    ModelRec("codellama:13b", "coding", 8.0, "Better quality, still within VRAM"),
    # General chat
    ModelRec("llama3.1:8b", "general", 5.0, "Fast, balanced multilingual chat"),
    ModelRec("llama3.1:70b", "general", 40.0, "Best quality — requires quantization or offload"),
    ModelRec("qwen2.5:7b", "general", 4.5, "Great reasoning & long context"),
    ModelRec("qwen2.5:14b", "general", 8.5, "Higher quality general purpose"),
    ModelRec("mistral:7b", "general", 4.5, "Fast, good instruction following"),
    ModelRec("mixtral:8x7b", "general", 26.0, "MoE — too large for 20 GB full precision"),
    ModelRec("gemma2:9b", "general", 5.5, "Google Gemma 2, strong for size"),
    ModelRec("phi4:14b", "general", 8.5, "Microsoft Phi-4, efficient & capable"),
    # Embeddings
    ModelRec("nomic-embed-text:latest", "embeddings", 0.5, "Best open embedding for RAG"),
    ModelRec("mxbai-embed-large:latest", "embeddings", 1.0, "Larger, higher quality embeddings"),
    ModelRec("snowflake-arctic-embed:latest", "embeddings", 0.5, "Fast, good retrieval accuracy"),
]


def cmd_recommend() -> None:
    print(f"GPU: RTX A4500 ({VRAM_GB} GB VRAM)\n")

    categories = {"coding": [], "general": [], "embeddings": []}
    for rec in RECOMMENDATIONS:
        categories[rec.purpose].append(rec)

    for purpose, label in (
        ("coding", "💻  Coding"),
        ("general", "💬  General Chat"),
        ("embeddings", "🔎  Embeddings"),
    ):
        print(f"{label}")
        print("-" * 70)
        for rec in categories[purpose]:
            fit = "✅ fits" if rec.vram_gb <= VRAM_GB else "⚠️  tight / offload needed"
            print(f"  {rec.name:<36} ~{rec.vram_gb:>5.1f} GB  {fit}")
            print(f"      {rec.notes}")
        print()

    print("Tip: Use Q4_K_M or Q5_K_M quantizations to fit larger models.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ollama_model_manager",
        description="Manage Ollama models via the local REST API.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List local models with size and last-used info")

    p_pull = sub.add_parser("pull", help="Pull a model with progress display")
    p_pull.add_argument("model", help="Model name (e.g. llama3.1:8b)")

    p_remove = sub.add_parser("remove", help="Remove a model to free disk space")
    p_remove.add_argument("model", help="Model name to delete")

    p_bench = sub.add_parser("benchmark", help="Run a quick speed test (tok/s) + VRAM estimate")
    p_bench.add_argument("model", help="Model name to benchmark")

    sub.add_parser("recommend", help="Recommend models for your GPU (RTX A4500 20GB)")

    args = parser.parse_args()

    try:
        if args.command == "list":
            cmd_list()
        elif args.command == "pull":
            cmd_pull(args.model)
        elif args.command == "remove":
            cmd_remove(args.model)
        elif args.command == "benchmark":
            cmd_benchmark(args.model)
        elif args.command == "recommend":
            cmd_recommend()
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to Ollama at {OLLAMA_HOST}. Is the server running?")
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"HTTP error: {exc.response.status_code} — {exc.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
