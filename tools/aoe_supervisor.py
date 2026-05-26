#!/usr/bin/env python3
"""AOE Supervisor (Python shim) — bare-metal process supervisor for the
aquaculture mesh. Spawns the Python mesh as a child process, monitors memory
via psutil, and exposes an HTTP control plane.

This is a drop-in shim for the Rust AOE supervisor (`aoe/supervisor/`).
When the Rust binary is compiled, replace this script with `aoe.exe`.

Usage:
    python tools/aoe_supervisor.py --port 58082 --memory-limit 512
"""
import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AOE_SHIM] %(message)s",
)
logger = logging.getLogger("AOE")

DEFAULT_SCRIPT = "swarm-backend/modes/aquaculture_mesh_mode.py"
DEFAULT_MEMORY_MB = 512


@dataclass
class MeshStatus:
    pid: Optional[int] = None
    running: bool = False
    memory_usage_mb: float = 0.0
    memory_limit_mb: int = DEFAULT_MEMORY_MB
    cpu_percent: float = 0.0
    cycles_completed: int = 0


class ProcessManager:
    """Wraps a Python subprocess, monitors memory, and kills on leak."""

    def __init__(self, script: str, memory_limit_mb: int):
        self.script = script
        self.memory_limit_mb = memory_limit_mb
        self.status = MeshStatus(memory_limit_mb=memory_limit_mb)
        self._proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def spawn(self) -> int:
        if self._proc is not None and self._proc.poll() is None:
            logger.warning("Mesh already running (PID %d). Stopping first.", self._proc.pid)
            self.stop()

        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([
            os.path.abspath("swarm-backend"),
            os.path.abspath("."),
            env.get("PYTHONPATH", ""),
        ])
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [sys.executable, self.script]
        self._proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        self.status.pid = self._proc.pid
        self.status.running = True
        logger.info("Mesh spawned (PID %d)", self._proc.pid)
        self._start_monitor()
        return self._proc.pid

    def stop(self) -> None:
        self._stop_event.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Force-killing PID %d", self._proc.pid)
                    self._proc.kill()
                    self._proc.wait(timeout=5)
            except Exception as e:
                logger.error("Error stopping process: %s", e)
            finally:
                self._proc = None
        self.status.running = False
        self.status.pid = None
        logger.info("Process wiped. State purged.")

    def failsafe(self) -> None:
        logger.critical("FAILSAFE triggered — immediate kill")
        self.stop()

    def logs(self) -> list[str]:
        # In a real implementation we'd tee stdout to a ring buffer.
        # For now, return a stub since reading from PIPE after spawn is tricky.
        return ["[AOE] Live logs require log-file redirection. Use --log-file to persist."]

    def _start_monitor(self) -> None:
        self._stop_event.clear()

        def monitor():
            try:
                import psutil
            except ImportError:
                logger.warning("psutil not installed — memory monitoring disabled")
                return

            while not self._stop_event.is_set() and self._proc is not None:
                try:
                    proc = psutil.Process(self._proc.pid)
                    mem_mb = proc.memory_info().rss / (1024 * 1024)
                    cpu = proc.cpu_percent(interval=1.0)
                    self.status.memory_usage_mb = mem_mb
                    self.status.cpu_percent = cpu
                    self.status.pid_count = len(proc.children(recursive=True)) + 1

                    if mem_mb > self.memory_limit_mb:
                        logger.error(
                            "MEMORY LEAK DETECTED: %.2f MB > %d MB — killing PID %d",
                            mem_mb,
                            self.memory_limit_mb,
                            self._proc.pid,
                        )
                        self._proc.kill()
                        self.status.running = False
                        break
                except psutil.NoSuchProcess:
                    self.status.running = False
                    break
                except Exception as e:
                    logger.warning("Monitor error: %s", e)
                time.sleep(2)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()


# ── HTTP Control Plane ──

async def http_server(manager: ProcessManager, port: int) -> None:
    from aiohttp import web

    async def health(_):
        return web.Response(text="ok")

    async def mesh_start(request):
        try:
            pid = manager.spawn()
            return web.json_response({"success": True, "data": {"container_id": str(pid)}})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def mesh_stop(_):
        try:
            manager.stop()
            return web.json_response({"success": True, "data": {"wiped": True}})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def mesh_status(_):
        return web.json_response({"success": True, "data": manager.status.__dict__})

    async def mesh_failsafe(_):
        try:
            manager.failsafe()
            return web.json_response({"success": True, "data": {"killed": True}})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def mesh_logs(_):
        try:
            lines = manager.logs()
            return web.json_response({"success": True, "data": {"lines": lines}})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_post("/mesh/start", mesh_start)
    app.router.add_post("/mesh/stop", mesh_stop)
    app.router.add_get("/mesh/status", mesh_status)
    app.router.add_post("/mesh/failsafe", mesh_failsafe)
    app.router.add_get("/mesh/logs", mesh_logs)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("AOE supervisor shim listening on 0.0.0.0:%d", port)

    while True:
        await asyncio.sleep(3600)


def main() -> int:
    parser = argparse.ArgumentParser(prog="aoe_supervisor")
    parser.add_argument("--port", type=int, default=58082)
    parser.add_argument("--script", default=DEFAULT_SCRIPT)
    parser.add_argument("--memory-limit", type=int, default=DEFAULT_MEMORY_MB)
    args = parser.parse_args()

    manager = ProcessManager(args.script, args.memory_limit)

    def shutdown(sig, frame):
        logger.info("Signal %s received — wiping mesh", sig)
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        asyncio.run(http_server(manager, args.port))
    except KeyboardInterrupt:
        manager.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
