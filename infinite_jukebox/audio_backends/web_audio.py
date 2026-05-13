"""
Agent 4 — Web Audio Backend: Procedural Synthesis Fallback
===========================================================
When the main studio (ComfyUI) is offline, this is the backup basement
rehearsal space. It uses oscillator-based synthesis to generate groove
loops that still drive the fluid visualization convincingly.
"""

from __future__ import annotations

import math
import random
import numpy as np
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from infinite_jukebox.audio_backends.base import AudioBackend, AudioSegment


@dataclass
class WebAudioBackend(AudioBackend):
    """
    A pure-Python procedural audio generator that mimics the Web Audio API
    engine we built earlier. Runs entirely in the Python backend so it can
    feed FFT frames to the fluid engine even when the browser is silent.
    """

    bpm: float = 110.0
    sample_rate: int = 44100
    scale: list = field(default_factory=lambda: [0, 2, 4, 7, 9])
    root_note: int = 55
    _running: bool = False
    _current_measure: int = 0
    _buffer: np.ndarray = field(default_factory=lambda: np.zeros(0))
    _buffer_pos: int = 0

    def is_available(self) -> bool:
        # Always available — like a battery-powered practice amp
        return True

    def generate(self, prompt: str = "", duration_sec: float = 10.0, **kwargs) -> Optional[AudioSegment]:
        """Render a complete audio segment to a NumPy buffer."""
        samples = int(self.sample_rate * duration_sec)
        buffer = np.zeros(samples, dtype=np.float32)
        beat_samples = int(60.0 / self.bpm * self.sample_rate)

        t = np.arange(samples) / self.sample_rate

        # Kick drum pattern: beats 1 and 3
        kick = self._synthesize_kick(t, beat_samples)
        # Snare pattern: beats 2 and 4
        snare = self._synthesize_snare(t, beat_samples)
        # Bass line
        bass = self._synthesize_bass(t, beat_samples)
        # Ambient pad
        pad = self._synthesize_pad(t, duration_sec)

        mix = kick * 0.9 + snare * 0.6 + bass * 0.55 + pad * 0.12
        # Simple limiter
        mix = np.tanh(mix * 1.5) / 1.5

        return AudioSegment(
            pcm_samples=mix,
            sample_rate=self.sample_rate,
            channels=1,
            duration_sec=duration_sec,
            metadata={"backend": "web_audio", "bpm": self.bpm, "prompt": prompt},
        )

    def get_fft_frame(self, n_bins: int = 512) -> Optional[np.ndarray]:
        """
        Analyze a sliding window of the internal buffer.
        Like a real-time spectrum analyzer plugin in a DAW.
        """
        if len(self._buffer) == 0:
            return np.zeros(n_bins, dtype=np.float32)
        window_size = min(2048, len(self._buffer))
        window = self._buffer[self._buffer_pos:self._buffer_pos + window_size]
        if len(window) < window_size:
            window = np.pad(window, (0, window_size - len(window)))
        fft = np.abs(np.fft.rfft(window * np.hanning(len(window))))
        # Resample to n_bins
        if len(fft) >= n_bins:
            frame = np.interp(np.linspace(0, len(fft) - 1, n_bins), np.arange(len(fft)), fft)
        else:
            frame = np.pad(fft, (0, n_bins - len(fft)))
        # Normalize
        peak = frame.max() + 1e-6
        return (frame / peak).astype(np.float32)

    def stream(self, callback: Callable[[AudioSegment], None]) -> None:
        # Not implemented for Python backend — used in JS context
        pass

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # Synthesis primitives — virtual analog oscillators
    # ------------------------------------------------------------------

    def _synthesize_kick(self, t: np.ndarray, beat_samples: int) -> np.ndarray:
        kick = np.zeros_like(t)
        for beat in range(0, int(len(t) / beat_samples) + 1):
            start = beat * beat_samples
            if start >= len(t):
                continue
            end = min(start + int(0.35 * self.sample_rate), len(t))
            kt = t[start:end] - t[start]
            freq = 150 * np.exp(-kt * 25) + 40
            phase = np.cumsum(2 * np.pi * freq / self.sample_rate)
            env = np.exp(-kt * 12)
            kick[start:end] += np.sin(phase) * env * 0.9
        return kick

    def _synthesize_snare(self, t: np.ndarray, beat_samples: int) -> np.ndarray:
        snare = np.zeros_like(t)
        for beat in range(0, int(len(t) / beat_samples) + 1):
            start = beat * beat_samples + int(beat_samples * 0.5)
            if start >= len(t):
                continue
            end = min(start + int(0.18 * self.sample_rate), len(t))
            kt = t[start:end] - t[start]
            noise = np.random.randn(end - start) * 0.35
            tone = np.sin(2 * np.pi * 180 * kt) * 0.25
            env = np.exp(-kt * 20)
            snare[start:end] += (noise + tone) * env
        return snare

    def _synthesize_bass(self, t: np.ndarray, beat_samples: int) -> np.ndarray:
        bass = np.zeros_like(t)
        note_dur = int(beat_samples * 0.8)
        for beat in range(0, int(len(t) / beat_samples) + 1):
            start = beat * beat_samples
            if start >= len(t):
                continue
            end = min(start + note_dur, len(t))
            note_idx = self.scale[beat % len(self.scale)]
            freq = 440 * 2 ** ((self.root_note + note_idx - 69) / 12)
            kt = t[start:end] - t[start]
            phase = 2 * np.pi * freq * kt
            env = np.exp(-kt * 3)
            bass[start:end] += np.tanh(np.sin(phase) * 1.2) * env * 0.6
        return bass

    def _synthesize_pad(self, t: np.ndarray, duration_sec: float) -> np.ndarray:
        pad = np.zeros_like(t)
        for detune in [-7, 0, 7]:
            freq = 440 * 2 ** ((self.root_note + 24 + detune - 69) / 12)
            phase = 2 * np.pi * freq * t
            lfo = 1.0 + 0.3 * np.sin(2 * np.pi * 0.2 * t + random.random())
            pad += np.sin(phase) * lfo * 0.04
        # Fade in/out
        fade = np.minimum(t / 1.0, 1.0) * np.minimum((duration_sec - t) / 1.0, 1.0)
        return pad * fade
