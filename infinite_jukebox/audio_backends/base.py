"""
Agent 1 — Audio Backend Protocol
================================
Think of this as the audio patch bay in a recording studio. Every source
(microphone, synth, tape deck, ComfyUI generator) must present the same
connectors (XLR/TRS) so the mixing desk can route them without rewiring.
"""

from __future__ import annotations

from typing import Protocol, Optional, Dict, Any, Callable
from dataclasses import dataclass
import numpy as np


@dataclass
class AudioSegment:
    """
    One chunk of audio — like a single reel of tape on a multitrack.
    Contains the PCM samples, sample rate, and metadata (tempo, key, etc.).
    """
    pcm_samples: np.ndarray
    sample_rate: int = 44100
    channels: int = 2
    duration_sec: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AudioBackend(Protocol):
    """
    Anything that can produce audio segments and FFT analysis.
    Like a universal audio interface card: USB, Thunderbolt, or PCIe —
    the mixer doesn't care, as long as it receives a 48 kHz clock signal.
    """

    def is_available(self) -> bool:
        """Return True if this backend is installed and ready to run."""
        ...

    def generate(self, prompt: str, duration_sec: float = 10.0, **kwargs) -> Optional[AudioSegment]:
        """
        Generate a new audio segment from a text prompt.
        Like telling the session musician what groove to play.
        """
        ...

    def get_fft_frame(self, n_bins: int = 512) -> Optional[np.ndarray]:
        """
        Return the current frequency spectrum.
        Like the LED meters on a graphic equalizer.
        """
        ...

    def stream(self, callback: Callable[[AudioSegment], None]) -> None:
        """
        Start a real-time stream of audio segments.
        Like pressing RECORD on a tape machine that loops endlessly.
        """
        ...

    def stop(self) -> None:
        """Halt generation and free resources — like hitting the talkback button."""
        ...
