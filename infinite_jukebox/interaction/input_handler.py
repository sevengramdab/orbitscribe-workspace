"""
Agent 4 — UX Engineer: Real-Time Interactive Forces & Audio Input
==================================================================
Think of this module as the smart-home occupancy sensor and touch panel
combined. It listens for two kinds of input:
1. Human touch / mouse drag   → like a Lutron dimmer slider
2. Audio FFT peaks            → like a whole-house audio zone volume
Then it translates both into physical "splat" forces that stir the fluid.
"""

from __future__ import annotations

import math
from typing import List, Callable, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from infinite_jukebox.architecture import (
    AudioFrame,
    AudioChannel,
    SplatPayload,
    Vector2D,
    AudioBufferProvider,
)


# =============================================================================
# POINTER STATE — The user's finger on the glass
# =============================================================================

@dataclass
class PointerState:
    """
    Tracks a single pointer (mouse, touch, or stylus) — like a single-gang
    dimmer switch that knows its position (where on the wall it is) and
    how fast the user slid it (velocity).
    """
    active: bool = False
    x: float = 0.0          # 0–1 in UV space
    y: float = 0.0
    dx: float = 0.0         # Delta since last frame
    dy: float = 0.0
    pressure: float = 1.0   # How hard the user is pressing (0–1)


# =============================================================================
# AUDIO FORCE BRIDGE — From spectrum analyzer to fire hose
# =============================================================================

class AudioForceBridge:
    """
    Converts FFT audio frames into fluid splat payloads.
    Like a variable-frequency drive that reads a 4–20 mA sensor signal
    and converts it into motor torque: small signal → gentle flow;
    big signal → fire-hose blast.
    """

    def __init__(
        self,
        channel_map: Dict[AudioChannel, Tuple[float, float, float]],
        smoothing: float = 0.85,
    ) -> None:
        """
        channel_map: Maps each audio channel to an RGB color.
        smoothing:   Exponential moving average factor (0 = no memory;
                     0.99 = very sluggish, like a heavy flywheel).
        """
        self.channel_map = channel_map
        self.smoothing = smoothing
        self._history: Dict[AudioChannel, float] = {ch: 0.0 for ch in AudioChannel}

    def process(self, frame: AudioFrame) -> List[SplatPayload]:
        """
        Turn one audio frame into a bouquet of splats — like a fountain
        show where each water jet fires in time with a different drum pad.
        """
        splats: List[SplatPayload] = []
        bins = frame.frequency_bins
        n_bins = len(bins)

        for ch, color in self.channel_map.items():
            # Map channel enum to a slice of FFT bins
            # ELI5: The spectrum analyzer has 512 LEDs. We assign each
            # musical octave to a different colored zone on the strip.
            start, end = self._bin_range(ch, n_bins)
            band = bins[start:end]
            if len(band) == 0:
                continue

            # Compute band energy — like reading the RMS current on one
            # phase of a three-phase electrical panel.
            raw_energy = float(np.mean(band))
            peak = float(np.max(band))

            # Exponential smoothing — like a thermal mass in a hydronic
            # buffer tank that prevents short-cycling the boiler.
            prev = self._history[ch]
            energy = prev * self.smoothing + raw_energy * (1.0 - self.smoothing)
            self._history[ch] = energy

            # Threshold gate — ignore electrical noise below the floor
            if energy < 0.02:
                continue

            # Map band index to horizontal position on screen
            # ELI5: Bass sounds (low Hz) spray from the left side of the
            # pool; treble sounds (high Hz) spray from the right.
            center_bin = (start + end) / 2
            x_pos = center_bin / n_bins
            y_pos = 0.5 + 0.1 * math.sin(frame.timestamp_ms * 0.003 + ch.value)

            # Velocity proportional to energy — louder = harder push
            vx = (energy * 4.0) * (1.0 if ch.value % 2 == 0 else -1.0)
            vy = -energy * 6.0   # Upward bias like a geyser

            splats.append(
                SplatPayload(
                    origin=Vector2D(x_pos, y_pos),
                    velocity=Vector2D(vx, vy),
                    color_rgb=color,
                    radius=0.005 + energy * 0.02,
                    density=min(1.0, energy * 2.0),
                )
            )

        return splats

    @staticmethod
    def _bin_range(ch: AudioChannel, n_bins: int) -> Tuple[int, int]:
        """
        Return start/end FFT bin indices for a channel.
        Like labeling breaker slots 1–42 in a panel: each channel gets
        a contiguous block so the wires don't cross.
        """
        # Map channels to proportional slices (simple log-ish mapping)
        ratios = {
            AudioChannel.BASS: (0.0, 0.08),
            AudioChannel.LOW_MID: (0.08, 0.16),
            AudioChannel.MID: (0.16, 0.35),
            AudioChannel.HIGH_MID: (0.35, 0.60),
            AudioChannel.TREBLE: (0.60, 1.0),
        }
        lo, hi = ratios[ch]
        return int(lo * n_bins), int(hi * n_bins)


# =============================================================================
# INPUT HANDLER — The Crestron control processor
# =============================================================================

class InputHandler:
    """
    Aggregates pointer (human) and audio (machine) inputs into a unified
    stream of splat payloads. Like a home-automation hub that merges
    motion-sensor events and voice commands into one action list.
    """

    def __init__(
        self,
        audio_bridge: AudioForceBridge,
        audio_provider: Optional[AudioBufferProvider] = None,
    ) -> None:
        self.audio_bridge = audio_bridge
        self.audio_provider = audio_provider
        self.pointers: Dict[int, PointerState] = {}
        self._last_audio_frame: Optional[AudioFrame] = None

    # -------------------------------------------------------------------------
    # POINTER API — Touch / mouse events
    # -------------------------------------------------------------------------

    def pointer_down(self, pointer_id: int, x: float, y: float, pressure: float = 1.0) -> None:
        """User touched the glass — like flipping a momentary switch ON."""
        self.pointers[pointer_id] = PointerState(active=True, x=x, y=y, pressure=pressure)

    def pointer_move(self, pointer_id: int, x: float, y: float, pressure: float = 1.0) -> None:
        """User dragged — like sliding a fader on a mixing console."""
        p = self.pointers.get(pointer_id)
        if p is None:
            return
        p.dx = x - p.x
        p.dy = y - p.y
        p.x = x
        p.y = y
        p.pressure = pressure

    def pointer_up(self, pointer_id: int) -> None:
        """User released — like the spring-return on a doorbell button."""
        if pointer_id in self.pointers:
            self.pointers[pointer_id].active = False

    # -------------------------------------------------------------------------
    # POLLING — Gather everything into splats for this frame
    # -------------------------------------------------------------------------

    def poll(self, audio_frame: Optional[AudioFrame] = None) -> List[SplatPayload]:
        """
        Collect all active inputs and convert to splats.
        Like the master schedule that says: at 8:00 AM turn on lights,
        at 8:05 AM start coffee maker, at 8:10 AM open blinds.
        """
        splats: List[SplatPayload] = []

        # 1. Pointer contributions (human touch)
        # ELI5: Every finger on the screen is a garden hose. The faster
        # you drag, the harder the nozzle sprays.
        for p in self.pointers.values():
            if not p.active:
                continue
            splats.append(
                SplatPayload(
                    origin=Vector2D(p.x, p.y),
                    velocity=Vector2D(p.dx * 8.0, p.dy * 8.0),
                    color_rgb=(1.0, 1.0, 1.0),   # White for human input
                    radius=0.003 + p.pressure * 0.01,
                    density=p.pressure,
                )
            )
            # Reset deltas so we don't accumulate stale motion
            p.dx = 0.0
            p.dy = 0.0

        # 2. Audio contributions (machine listening)
        # ELI5: The microphone is a rain detector on the roof. When it
        # hears thunder (bass), it opens the big valve; birds (treble)
        # open the misting nozzles.
        frame = audio_frame or self._last_audio_frame
        if frame is not None:
            splats.extend(self.audio_bridge.process(frame))
            self._last_audio_frame = frame

        return splats
