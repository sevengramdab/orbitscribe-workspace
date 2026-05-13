"""
Agent 4 — ComfyUI Backend: ACE-Step 1.5 Integration
====================================================
This is the main studio control room. When ComfyUI is running and the
ACE-Step 1.5 models are loaded, we use AI-generated music instead of
synthetic oscillators. The output is still fed into the same FFT analyzer
so the fluid visualizer reacts to the actual composition.
"""

from __future__ import annotations

import threading
import numpy as np
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from infinite_jukebox.audio_backends.base import AudioBackend, AudioSegment
from infinite_jukebox.comfyui.client import ComfyUIClient, ComfyUIConfig


@dataclass
class ComfyUIBackend(AudioBackend):
    """
    Bridges the Infinite Jukebox to ComfyUI's ACE-Step 1.5 text-to-audio model.
    Like a Dante audio-over-IP bridge: it translates between two different
    digital audio networks so devices on either side can talk.
    """

    config: ComfyUIConfig = field(default_factory=ComfyUIConfig)
    _client: Optional[ComfyUIClient] = None
    _last_segment: Optional[AudioSegment] = None
    _playback_pos: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        self._client = ComfyUIClient(self.config)

    def is_available(self) -> bool:
        """Check if ComfyUI server is reachable — like pinging the mixing desk."""
        return self._client is not None and self._client.is_online()

    def generate(self, prompt: str = "", duration_sec: float = 10.0, **kwargs) -> Optional[AudioSegment]:
        """Generate a new segment via ACE-Step 1.5."""
        if not self.is_available():
            return None
        segment = self._client.generate_and_fetch(lyrics=prompt, duration_sec=duration_sec, **kwargs)
        with self._lock:
            self._last_segment = segment
            self._playback_pos = 0
        return segment

    def get_fft_frame(self, n_bins: int = 512) -> Optional[np.ndarray]:
        """Analyze the currently playing AI-generated audio."""
        with self._lock:
            seg = self._last_segment
            if seg is None or len(seg.pcm_samples) == 0:
                return np.zeros(n_bins, dtype=np.float32)
            window_size = min(2048, len(seg.pcm_samples) - self._playback_pos)
            if window_size <= 0:
                self._playback_pos = 0
                window_size = min(2048, len(seg.pcm_samples))
            window = seg.pcm_samples[self._playback_pos:self._playback_pos + window_size]
            self._playback_pos = (self._playback_pos + window_size) % len(seg.pcm_samples)
        fft = np.abs(np.fft.rfft(window * np.hanning(len(window))))
        if len(fft) >= n_bins:
            frame = np.interp(np.linspace(0, len(fft) - 1, n_bins), np.arange(len(fft)), fft)
        else:
            frame = np.pad(fft, (0, n_bins - len(fft)))
        peak = frame.max() + 1e-6
        return (frame / peak).astype(np.float32)

    def stream(self, callback: Callable[[AudioSegment], None]) -> None:
        pass

    def stop(self) -> None:
        with self._lock:
            self._last_segment = None
            self._playback_pos = 0
