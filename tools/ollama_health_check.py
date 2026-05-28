#!/usr/bin/env python3
"""Ollama health-check utility.

Checks that the local Ollama server is reachable, lists available models,
runs a quick inference smoke-test, and reports tokens/second for each model.
Can be run standalone for monitoring or integrated into CI.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_PROMPT = "Say hello in one sentence."
DEFAULT_TIMEOUT = 120


def _fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def _post_json(url: str, payload: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def check_reachable(base_url: str) -> dict[str, Any]:
    """Return server info or raise."""
    return _fetch(f"{base_url}/api/tags", timeout=10)


def list_models(base_url: str) -> list[dict[str, Any]]:
    data = check_reachable(base_url)
    return data.get("models", [])


def inference_test(
    base_url: str,
    model: str,
    prompt: str = DEFAULT_PROMPT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run a single generate call and return enriched metrics."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    start = time.perf_counter()
    result = _post_json(f"{base_url}/api/generate", payload, timeout=timeout)
    elapsed = time.perf_counter() - start

    eval_count = result.get("eval_count", 0)
    eval_duration_ns = result.get("eval_duration", 0)
    prompt_eval_count = result.get("prompt_eval_count", 0)
    prompt_eval_duration_ns = result.get("prompt_eval_duration", 0)
    total_duration_ns = result.get("total_duration", 0)

    # Tokens per second (generation phase)
    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0.0
    # Prompt tokens per second
    prompt_tps = (
        (prompt_eval_count / (prompt_eval_duration_ns / 1e9))
        if prompt_eval_duration_ns > 0
        else 0.0
    )

    return {
        "model": model,
        "reachable": True,
        "response": result.get("response", "").strip(),
        "elapsed_sec": round(elapsed, 2),
        "total_duration_sec": round(total_duration_ns / 1e9, 2),
        "load_duration_sec": round(result.get("load_duration", 0) / 1e9, 2),
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_tps": round(prompt_tps, 2),
        "eval_count": eval_count,
        "eval_tps": round(tps, 2),
        "done": result.get("done", False),
        "done_reason": result.get("done_reason", None),
    }


def health_check(
    base_url: str = DEFAULT_BASE_URL,
    models: list[str] | None = None,
    prompt: str = DEFAULT_PROMPT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Full health check: reachability, model list, inference on each model."""
    report: dict[str, Any] = {
        "server_url": base_url,
        "reachable": False,
        "models": [],
        "inference_tests": [],
        "errors": [],
    }

    # 1. Reachability + model list
    try:
        available = list_models(base_url)
        report["reachable"] = True
        report["models"] = [m.get("name") for m in available]
    except urllib.error.URLError as exc:
        report["errors"].append(f"Server unreachable: {exc.reason}")
        return report
    except Exception as exc:
        report["errors"].append(f"Unexpected error listing models: {exc}")
        return report

    # 2. Determine which models to benchmark
    targets = models if models else report["models"]
    if not targets:
        report["errors"].append("No models available on server.")
        return report

    # 3. Inference test for each target
    for model in targets:
        try:
            test_result = inference_test(base_url, model, prompt=prompt, timeout=timeout)
            report["inference_tests"].append(test_result)
        except urllib.error.HTTPError as exc:
            report["inference_tests"].append(
                {
                    "model": model,
                    "reachable": False,
                    "error": f"HTTP {exc.code}: {exc.reason}",
                }
            )
        except Exception as exc:
            report["inference_tests"].append(
                {
                    "model": model,
                    "reachable": False,
                    "error": str(exc),
                }
            )

    return report


def print_report(report: dict[str, Any]) -> None:
    reachable = report.get("reachable", False)
    models = report.get("models", [])
    tests = report.get("inference_tests", [])
    errors = report.get("errors", [])

    print("=" * 60)
    print("Ollama Health Check Report")
    print("=" * 60)
    print(f"Server URL : {report.get('server_url')}")
    print(f"Reachable  : {'YES' if reachable else 'NO'}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err}")

    if reachable:
        print(f"\nAvailable models ({len(models)}):")
        for m in models:
            print(f"  • {m}")

        if tests:
            print("\nInference Tests:")
            for t in tests:
                name = t.get("model", "?")
                if t.get("reachable"):
                    print(
                        f"  • {name:<30} "
                        f"eval={t['eval_count']:>3} tok  "
                        f"{t['eval_tps']:>6.2f} tok/s  "
                        f"total={t['elapsed_sec']:>6.2f}s  "
                        f"done={t['done']}"
                    )
                    print(f"    Response: {t['response'][:100]}{'...' if len(t['response']) > 100 else ''}")
                else:
                    print(f"  • {name:<30} FAILED — {t.get('error', 'unknown')}")

    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ollama health check and performance monitor",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Ollama base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Specific models to test (default: all available)",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt for inference test",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw JSON report",
    )
    args = parser.parse_args(argv)

    report = health_check(
        base_url=args.url,
        models=args.models,
        prompt=args.prompt,
        timeout=args.timeout,
    )

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    return 0 if report["reachable"] and not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
