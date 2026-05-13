"""
Agent 8 — Performance Engineer: Zero-Latency Profiling
======================================================
Think of this module as the building's BACnet energy-management system.
It reads every meter (frame time, GPU memory, audio buffer depth) in
real time and automatically adjusts setpoints so the HVAC (renderer)
never short-cycles and the lights (shaders) never flicker.
"""

from __future__ import annotations

# Import the wall clock so we can time how long each HVAC cycle runs.
import time
# Import math so we can calculate conduit fill percentages like an electrician.
import math
# Import random so our fake meter readings wiggle like real analog gauges.
import random
# Import threading so we can put padlocks on shared water tanks.
import threading
# Import deque because it acts like a circular conveyor belt for paint buckets.
from collections import deque
# Import typing helpers so the blueprint knows what shape each wire connector is.
from typing import Dict, List, Optional, Callable, Any, Tuple

# Fetch the AutoCAD layer standards that tell us how detailed each viewport render should be.
from infinite_jukebox.architecture import SimulationQuality
# Fetch the security-monitor layout sheet so we know which GPU drives which screen.
from infinite_jukebox.architecture import ViewportConfig
# Fetch the HVAC control-panel knobs so the streamer knows fluid simulation settings.
from infinite_jukebox.architecture import FluidConfig


class PerformanceMonitor:
    """
    Profiles every frame and adapts simulation quality to maintain target FPS.
    Like an Ecobee smart thermostat: if it notices the house keeps overshooting
    temperature, it learns to start the AC earlier. Here, if frames take too
    long, we drop grid resolution or turn off expensive effects.
    """

    def __init__(
        self,
        target_fps: float = 60.0,
        history_size: int = 120,
        adaptation_aggressiveness: float = 0.2,
    ) -> None:
        # Program the thermostat setpoint — like dialing 72 °F on a Honeywell T6 Pro.
        self.target_fps = target_fps
        # Convert the FPS setpoint into a millisecond duty-cycle budget for the compressor.
        self.target_frame_time = 1000.0 / target_fps
        # Install a circular data tape that only keeps the last 120 meter readings.
        self.history: deque = deque(maxlen=history_size)
        # Set how jumpy the thermostat is — 0.2 means gradual changes, not hair-trigger.
        self.aggression = adaptation_aggressiveness
        # Stick a blank Post-it on the wall to mark when the current HVAC cycle started.
        self._frame_start: Optional[float] = None
        # Create a breaker panel where each breaker is labeled with a room name.
        self._adaptation_callbacks: Dict[str, Callable[[str, int], None]] = {}
        # Start a scratchpad for tracking how many paint blobs the sprayer fired.
        self._splat_count = 0
        # Start a fake sub-meter reading for the server room's GPU memory usage.
        self._gpu_memory_mb = 0.0
        # Start a maintenance log counting how many times the compressor missed its window.
        self._dropped_frames = 0

    def begin_frame(self) -> None:
        # Read the utility clock and mark the start of a new HVAC cycle.
        self._frame_start = time.perf_counter() * 1000.0

    def end_frame(
        self,
        frame_index: int,
        cpu_time_ms: float = 0.0,
        gpu_time_ms: float = 0.0,
        audio_buffer_ms: float = 0.0,
        memory_mb: float = 0.0,
        splat_count: int = 0,
        quality_level: str = "HIGH",
    ) -> Dict[str, Any]:
        # Read the utility clock again to see when the current HVAC cycle finished.
        now = time.perf_counter() * 1000.0
        # Subtract the start stamp from the end stamp like calculating total kWh for the month.
        total = now - self._frame_start if self._frame_start else self.target_frame_time
        # If the cycle lasted longer than 1.5x the compressor budget, log a blown fuse.
        if total > self.target_frame_time * 1.5:
            # Increment the outage counter in the maintenance log.
            self._dropped_frames += 1
        # Jot down the GPU memory reading like copying a sub-meter onto the master ledger.
        self._gpu_memory_mb = memory_mb
        # Record the paint-blob count like noting how many gallons the sprayer used.
        self._splat_count = splat_count
        # Build one row for the circular data tape, like a single line on a BACnet trend log.
        metric = {
            "frame_index": frame_index,
            "cpu_time_ms": cpu_time_ms,
            "gpu_time_ms": gpu_time_ms,
            "total_time_ms": total,
            "audio_buffer_ms": audio_buffer_ms,
            "memory_mb": memory_mb,
            "splat_count": splat_count,
            "quality_level": quality_level,
        }
        # Feed that row into the circular tape so the oldest reading falls off the back.
        self.history.append(metric)
        # Ask the thermostat brain whether to raise, lower, or hold the cooling stage.
        self._adapt_if_necessary()
        # Hand the completed row back to the dispatcher who requested it.
        return metric

    def register_adaptation_callback(
        self,
        key: str,
        callback: Optional[Callable[[str, int], None]] = None,
    ) -> None:
        # If the electrician only hands us one wire and no label, auto-generate a breaker number.
        if callback is None and callable(key):
            # Treat the lone wire as the callback and give it a generic breaker label.
            callback = key
            # Assign a default room name so the thermostat knows where to send orders.
            key = "quality_delta"
        # Mount the labeled smart-switch into the breaker panel.
        self._adaptation_callbacks[key] = callback

    def report(self) -> Dict[str, Any]:
        # If the utility meter box is still empty, hand back a blank invoice.
        if not self.history:
            # Return an empty receipt because no power has been consumed yet.
            return {}
        # Pull every total-cycle-time reading off the circular tape like reading monthly kWh.
        times = [m["total_time_ms"] for m in self.history]
        # Add up every cycle time like summing all the meter dials.
        total_sum = sum(times)
        # Count how many readings we pulled so we can find the average load.
        count = len(times)
        # Divide total load by number of readings to get the average cycle time.
        avg_time = total_sum / count
        # Convert the average cycle time back into frames-per-second like calculating RPM.
        avg_fps = 1000.0 / avg_time
        # Sort the cycle times like arranging pipe diameters from smallest to largest.
        sorted_times = sorted(times)
        # Compute the index for the 99th-percentile pipe — the one that almost never chokes.
        p99_index = int(count * 0.99)
        # Clamp the index so we never ask for a pipe that doesn't exist on the rack.
        p99_index = min(p99_index, count - 1)
        # Grab that near-worst-case cycle time for the report.
        p99_frame_time = sorted_times[p99_index]
        # Count how many cycles blew past 1.5x the compressor budget.
        dropped = sum(1 for t in times if t > self.target_frame_time * 1.5)
        # Ask the thermostat whether we need to shed load, add load, or stay put.
        quality_recommendation = self._compute_quality_recommendation()
        # Bundle everything into a single work-order for the building engineer.
        return {
            "avg_fps": avg_fps,
            "p99_frame_time": p99_frame_time,
            "dropped_frames": dropped,
            "quality_recommendation": quality_recommendation,
        }

    def _compute_quality_recommendation(self) -> int:
        # If the tape has fewer than 10 readings, we don't have enough data to decide.
        if len(self.history) < 10:
            # Stay at the current thermostat setting until more rooms are measured.
            return 0
        # Read the last 10 cycle times like checking the last 10 minutes on a trend log.
        recent = list(self.history)[-10:]
        # Add up the last 10 readings to prepare for averaging.
        recent_sum = sum(m["total_time_ms"] for m in recent)
        # Divide by 10 to get the average room temperature over the last few minutes.
        avg_time = recent_sum / len(recent)
        # See how far above or below the 72 °F setpoint we actually are.
        overshoot = avg_time - self.target_frame_time
        # If the house is more than 15 % too hot, tell the AC to crank up harder.
        if overshoot > self.target_frame_time * 0.15:
            # Shed a stage of cooling by dropping the render quality one notch.
            return -1
        # If the house is more than 30 % too cold, we can ease off and add eye candy.
        if overshoot < -self.target_frame_time * 0.30:
            # Add a stage of cooling because we have spare compressor capacity.
            return 1
        # The temperature is inside the dead-band, so leave the thermostat alone.
        return 0

    def _adapt_if_necessary(self) -> None:
        # Ask the thermostat brain whether we need to raise, lower, or hold quality.
        delta = self._compute_quality_recommendation()
        # If the brain says "hold," there's no reason to touch any smart switches.
        if delta == 0:
            # Skip flipping breakers because the temperature is already comfortable.
            return
        # Walk down the breaker panel and flip every smart switch tied to this system.
        for key, cb in self._adaptation_callbacks.items():
            # Try to flip the switch without letting a broken bulb crash the whole panel.
            try:
                # Send the quality change order to this specific room's smart switch.
                cb(key, delta)
            # If a wire is loose, just ignore that outlet and keep the rest powered.
            except Exception:
                # Log a silent fault so the other 99 circuits stay live.
                pass


class LevelStreamingEngine:
    """
    Pre-computes simulation frames so the main renderer never waits.
    Like a home-automation scene controller that pre-dims the lights
    five seconds before the movie starts, so there's no visible fade delay.
    """

    def __init__(
        self,
        frame_rate: float = 60.0,
        buffer_seconds: float = 2.0,
        fluid_config: Optional[FluidConfig] = None,
    ) -> None:
        # Store the refresh rate so we know how many frames equal one second of wall clock.
        self.frame_rate = frame_rate
        # Calculate how many frames fit in the buffer, like sizing a water tank in gallons.
        self.buffer_size = int(frame_rate * buffer_seconds)
        # Install the circular storage tank that holds pre-rendered frames.
        self._ring: deque = deque(maxlen=self.buffer_size)
        # Place a blank work order on the clipboard to track what the renderer owes us.
        self._pending_frame_index = 0
        # Create a padlock so two workers don't try to fill the same tank at once.
        self._lock = threading.Lock()
        # Remember the HVAC control-panel knobs so every pre-rendered frame uses the same settings.
        self._fluid_config = fluid_config if fluid_config is not None else FluidConfig()

    def prefetch(self, seconds_ahead: float = 2.0) -> int:
        # Figure out how many empty slots we want to fill, like ordering concrete trucks.
        target_count = int(self.frame_rate * seconds_ahead)
        # Grab the padlock so no other thread moves the fill hose while we're working.
        with self._lock:
            # Count how many frames are already sitting in the tank.
            current_len = len(self._ring)
            # Figure out how many more buckets we need to reach the target water level.
            needed = target_count - current_len
            # If the tank is already full or overflowing, stop the pump early.
            if needed <= 0:
                # Return zero because no new concrete was poured.
                return 0
            # Pour each missing bucket into the ring one at a time.
            for _ in range(needed):
                # Stamp the next work-order number on the bucket before placing it.
                frame = self._render_frame(self._pending_frame_index)
                # Slide the bucket onto the conveyor so the renderer can grab it.
                self._ring.append(frame)
                # Advance the work-order counter like incrementing a job ticket printer.
                self._pending_frame_index += 1
            # Return how many new buckets we added so the foreman knows progress.
            return needed

    def _render_frame(self, frame_index: int) -> Dict[str, Any]:
        # Pretend to run the fluid simulation, like calculating airflow for one HVAC zone.
        simulated_time = frame_index / self.frame_rate
        # Read the current grid resolution off the HVAC control panel.
        grid_res = self._fluid_config.grid_resolution
        # Build a dummy frame packet with a timestamp so the renderer knows when to show it.
        return {
            "frame_index": frame_index,
            "simulated_time": simulated_time,
            "grid_resolution": int(grid_res),
            "state": "precomputed",
        }

    def pop_ready_frame(self) -> Optional[Dict[str, Any]]:
        # Grab the padlock so we don't pull a bucket while the filler is adding more.
        with self._lock:
            # If the tank is dry, tell the renderer there's nothing to drink right now.
            if not self._ring:
                # Return None like an empty water cooler bottle.
                return None
            # Pull the oldest bucket off the front of the conveyor belt.
            return self._ring.popleft()

    def drain(self) -> int:
        # Grab the padlock so the filler stops pouring while we dump the tank.
        with self._lock:
            # Count how many buckets we're throwing away so we can log the waste.
            dumped = len(self._ring)
            # Open the drain valve and empty every pre-computed frame.
            self._ring.clear()
            # Reset the work-order printer back to zero for the new scene.
            self._pending_frame_index = 0
            # Return the number of wasted buckets so accounting knows the loss.
            return dumped


class HardwareProfiler:
    """
    Simulates health checks for a 5-GPU render farm.
    Like walking the jobsite with a thermal camera and a clamp meter,
    reading each electrical panel's load, temperature, and how full the conduit is.
    """

    def __init__(self, gpu_count: int = 5) -> None:
        # Remember how many breaker panels (GPUs) are installed on this jobsite.
        self.gpu_count = gpu_count
        # Create a roster of viewport assignments, like a lighting schedule per panel.
        self._assignments: Dict[int, List[ViewportConfig]] = {i: [] for i in range(gpu_count)}
        # Set a fake ceiling for each GPU's VRAM, like a 200-amp main breaker rating.
        self._vram_limit_gb = 32.0

    def profile_gpu(self, gpu_index: int) -> Dict[str, float]:
        # If the electrician asks about a panel number that doesn't exist, throw a red tag.
        if gpu_index < 0 or gpu_index >= self.gpu_count:
            # Raise an error like locking out a non-existent breaker slot.
            raise ValueError(f"GPU {gpu_index} is not on the jobsite; we only have {self.gpu_count} panels.")
        # Simulate a base load that shifts per panel, like different floors in a high-rise.
        base_util = 50.0 + gpu_index * 10.0
        # Add some electrical noise to the clamp meter so it looks like a real analog gauge.
        util = min(100.0, max(0.0, base_util + random.uniform(-10.0, 10.0)))
        # Guess how full the conduit is based on how hard the panel is working.
        vram_used = (util / 100.0) * self._vram_limit_gb + random.uniform(-1.0, 1.0)
        # Clamp the conduit fill to zero so we never report negative wire count.
        vram_used = max(0.0, vram_used)
        # Simulate a temperature rise like a thermal camera pointed at a hot busbar.
        temp = 45.0 + (util / 100.0) * 35.0 + random.uniform(-2.0, 2.0)
        # Bundle the three meter readings into one work order for the foreman.
        return {
            "utilization": round(util, 2),
            "vram_used": round(vram_used, 2),
            "temperature": round(temp, 2),
        }

    def assign_viewport(self, gpu_index: int, viewport: ViewportConfig) -> None:
        # If the panel number is out of range, slap a "do not energize" tag on it.
        if gpu_index < 0 or gpu_index >= self.gpu_count:
            # Refuse the connection because the panel doesn't exist.
            raise ValueError(f"Cannot land a viewport on GPU {gpu_index}; panel not found.")
        # Add the new lighting circuit to the chosen panel's load list.
        self._assignments[gpu_index].append(viewport)

    def rebalance_load(self) -> List[Tuple[int, int, ViewportConfig]]:
        # Create an empty move list, like a clipboard for circuit relocation tickets.
        moves: List[Tuple[int, int, ViewportConfig]] = []
        # Read every panel's current utilization with the thermal camera.
        utilizations = [self.profile_gpu(i)["utilization"] for i in range(self.gpu_count)]
        # Find the hottest panel — the one most likely to trip its main breaker.
        max_util = max(utilizations)
        # Find the coolest panel — the one with spare ampacity left.
        min_util = min(utilizations)
        # If the spread between hottest and coldest is less than 20 %, the load is already balanced.
        if max_util - min_util < 20.0:
            # Return an empty move list because no circuits need relocation.
            return moves
        # Identify which panel is running hottest so we can relieve it.
        overloaded_idx = utilizations.index(max_util)
        # Identify which panel has the most spare capacity to accept new circuits.
        idle_idx = utilizations.index(min_util)
        # Look at the circuits currently wired to the overloaded panel.
        assigned = self._assignments[overloaded_idx]
        # If there are no circuits to move, there's nothing we can do.
        if not assigned:
            # Hand back an empty clipboard because the panel is bare.
            return moves
        # Pick the first circuit on the panel like pulling the first wire off the busbar.
        viewport_to_move = assigned[0]
        # Remove that circuit from the overloaded panel's load list.
        self._assignments[overloaded_idx].remove(viewport_to_move)
        # Reattach the same circuit to the cooler panel's busbar.
        self._assignments[idle_idx].append(viewport_to_move)
        # Write a relocation ticket showing old panel, new panel, and the moved circuit.
        moves.append((overloaded_idx, idle_idx, viewport_to_move))
        # Return the list of tickets so the dispatcher knows what changed.
        return moves
