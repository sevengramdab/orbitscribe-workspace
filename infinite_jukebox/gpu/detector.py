"""
GPU Detection — Auto-detect real NVIDIA GPUs via nvidia-smi.
Returns actual card names, memory, utilization, and temperature.
Falls back to empty list if nvidia-smi is unavailable.
"""

from __future__ import annotations

import subprocess
from typing import List, Dict, Any


def detect_gpus() -> List[Dict[str, Any]]:
    """
    Detect NVIDIA GPUs using nvidia-smi. Returns a list of GPU dicts
    with keys: name, memory_mb, utilization, temperature.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append({
                    "name": parts[0],
                    "memory_mb": int(parts[1]) if parts[1].isdigit() else 0,
                    "utilization": int(parts[2]) if parts[2].isdigit() else 0,
                    "temperature": int(parts[3]) if parts[3].isdigit() else 0,
                })
        return gpus
    except Exception:
        return []


def gpu_count() -> int:
    """Return the number of detected NVIDIA GPUs."""
    return len(detect_gpus())


def primary_gpu_name() -> str:
    """Return the name of the first detected GPU, or 'CPU Render' if none."""
    gpus = detect_gpus()
    return gpus[0]["name"] if gpus else "CPU Render"
