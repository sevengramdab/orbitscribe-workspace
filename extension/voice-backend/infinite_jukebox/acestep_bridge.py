"""
ACE-Step V1.5 Bridge — Gradio API Client
=========================================
Like a Dante audio-over-IP bridge that connects the ACE-Step
music generation studio (port 7860) to the Infinite Jukebox
fighter-jet cockpit (port 58080).

ELI5: Imagine a walkie-talkie that lets the jukebox pilot
talk to the ACE-Step composer in the studio. The pilot says
"make me a 120-BPM ambient track" and the composer replies
with a WAV file.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import threading

import numpy as np


ACESTEP_HOST = os.environ.get("ACESTEP_HOST", "http://127.0.0.1:7860").rstrip("/")
GENERATION_ENDPOINT = f"{ACESTEP_HOST}/gradio_api/api/generation_wrapper"
PARAMS_ENDPOINT = f"{ACESTEP_HOST}/gradio_api/api/capture_current_params"


@dataclass
class AceStepParams:
    """All tunable knobs on the ACE-Step mixing desk.
    Matched to ACE-Step V1.5 Gradio API parameter schema (74 data slots, 0-73).
    """
    music_caption: str = ""
    lyrics: str = ""
    bpm: float = 120.0
    key: str = ""
    time_signature: str = ""
    vocal_language: str = "en"
    dit_inference_steps: float = 8.0
    dit_guidance_scale: float = 7.0
    random_seed: bool = True
    seed: str = "-1"
    audio_duration: float = -1.0
    batch_size: float = 2.0
    lm_codes_hints: str = ""
    lm_codes_strength: float = 1.0
    cover_strength: float = 0.0
    task_type: str = "text2music"
    no_fsq: bool = False
    use_adg: bool = False
    cfg_interval_start: float = 0.0
    cfg_interval_end: float = 1.0
    shift: float = 3.0
    inference_method: str = "ode"
    sampler_mode: str = "euler"
    velocity_norm_threshold: float = 0.0
    velocity_ema_factor: float = 0.0
    enable_dcw: bool = True
    dcw_mode: str = "double"
    dcw_scaler: float = 0.05
    dcw_high_scaler: float = 0.02
    dcw_wavelet: str = "haar"
    custom_timesteps: str = ""
    audio_format: str = "mp3"
    mp3_bitrate: str = "128k"
    mp3_sample_rate: str = "48000"
    lm_temperature: float = 0.85
    think: bool = True
    lm_cfg_scale: float = 2.0
    lm_top_k: float = 0.0
    lm_top_p: float = 0.9
    lm_negative_prompt: str = "NO USER INPUT"
    cot_metas: bool = True
    caption_rewrite: bool = False
    cot_language_detection: bool = True
    constrained_decoding_debug: bool = False
    parallel_thinking: bool = True
    auto_score: bool = False
    auto_lrc: bool = False
    quality_score_sensitivity: float = 0.5
    lm_batch_chunk_size: float = 8.0
    track_name: str = ""
    track_names: List[str] = field(default_factory=list)
    enable_normalization: bool = True
    target_peak_db: float = -1.0
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0
    latent_shift: float = 0.0
    latent_rescale: float = 1.0
    repaint_mode: str = "balanced"
    repaint_strength: float = 0.5
    variance: float = 0.0
    seed_extra: str = ""
    edit: bool = False
    source_caption: str = ""
    source_lyrics: str = ""
    n_min: float = 0.0
    n_max: float = 1.0
    n_avg: float = 1.0
    auto_gen: bool = False


@dataclass
class AceStepGenerationResult:
    """The finished track delivered from the ACE-Step studio."""
    ok: bool = False
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class AceStepBridge:
    """
    Client for the ACE-Step V1.5 Gradio API.
    Like the patch bay that routes audio between two studios.
    """

    def __init__(self, host: str = ACESTEP_HOST):
        self.host = host.rstrip("/")
        self._params = AceStepParams()
        self._latest_result: Optional[AceStepGenerationResult] = None
        self._lock = threading.Lock()
        self._pending: bool = False

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Return True if ACE-Step is online. Like checking if the studio phone rings."""
        try:
            req = urllib.request.Request(
                f"{self.host}/gradio_api/info",
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return detailed connection diagnostics for troubleshooting."""
        result = {
            "configured_host": self.host,
            "env_var": os.environ.get("ACESTEP_HOST", "(not set, using default)"),
            "gradio_info_reachable": False,
            "gradio_info_status": None,
            "gradio_info_error": None,
            "generation_endpoint": GENERATION_ENDPOINT,
        }
        try:
            req = urllib.request.Request(
                f"{self.host}/gradio_api/info",
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result["gradio_info_reachable"] = True
                result["gradio_info_status"] = resp.status
                body = resp.read().decode("utf-8")
                try:
                    data = json.loads(body)
                    endpoints = list(data.get("named_endpoints", {}).keys())
                    result["named_endpoints"] = endpoints
                    result["has_generation_wrapper"] = "/generation_wrapper" in endpoints
                except json.JSONDecodeError:
                    result["gradio_info_error"] = "Non-JSON response"
        except urllib.error.HTTPError as e:
            result["gradio_info_error"] = f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            result["gradio_info_error"] = f"URL Error: {e.reason}"
        except Exception as e:
            result["gradio_info_error"] = f"{type(e).__name__}: {e}"
        return result

    # ------------------------------------------------------------------
    # Parameter get / set
    # ------------------------------------------------------------------
    @property
    def params(self) -> AceStepParams:
        return self._params

    def update_params(self, delta: Dict[str, Any]) -> None:
        """Update parameters from a JSON delta. Like turning knobs on the mixing desk."""
        for key, value in delta.items():
            if hasattr(self._params, key):
                # Coerce types where needed
                field_type = type(getattr(self._params, key))
                if field_type == bool and isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes", "on")
                elif field_type in (int, float) and value is not None:
                    value = field_type(value)
                setattr(self._params, key, value)

    def get_params_dict(self) -> Dict[str, Any]:
        """Return all parameters as a flat dict."""
        return {
            "music_caption": self._params.music_caption,
            "lyrics": self._params.lyrics,
            "bpm": self._params.bpm,
            "key": self._params.key,
            "time_signature": self._params.time_signature,
            "vocal_language": self._params.vocal_language,
            "dit_inference_steps": self._params.dit_inference_steps,
            "dit_guidance_scale": self._params.dit_guidance_scale,
            "random_seed": self._params.random_seed,
            "seed": self._params.seed,
            "audio_duration": self._params.audio_duration,
            "batch_size": self._params.batch_size,
            "lm_codes_hints": self._params.lm_codes_hints,
            "lm_codes_strength": self._params.lm_codes_strength,
            "cover_strength": self._params.cover_strength,
            "task_type": self._params.task_type,
            "no_fsq": self._params.no_fsq,
            "use_adg": self._params.use_adg,
            "cfg_interval_start": self._params.cfg_interval_start,
            "cfg_interval_end": self._params.cfg_interval_end,
            "shift": self._params.shift,
            "inference_method": self._params.inference_method,
            "sampler_mode": self._params.sampler_mode,
            "velocity_norm_threshold": self._params.velocity_norm_threshold,
            "velocity_ema_factor": self._params.velocity_ema_factor,
            "enable_dcw": self._params.enable_dcw,
            "dcw_mode": self._params.dcw_mode,
            "dcw_scaler": self._params.dcw_scaler,
            "dcw_high_scaler": self._params.dcw_high_scaler,
            "dcw_wavelet": self._params.dcw_wavelet,
            "custom_timesteps": self._params.custom_timesteps,
            "audio_format": self._params.audio_format,
            "mp3_bitrate": self._params.mp3_bitrate,
            "mp3_sample_rate": self._params.mp3_sample_rate,
            "lm_temperature": self._params.lm_temperature,
            "think": self._params.think,
            "lm_cfg_scale": self._params.lm_cfg_scale,
            "lm_top_k": self._params.lm_top_k,
            "lm_top_p": self._params.lm_top_p,
            "lm_negative_prompt": self._params.lm_negative_prompt,
            "cot_metas": self._params.cot_metas,
            "caption_rewrite": self._params.caption_rewrite,
            "cot_language_detection": self._params.cot_language_detection,
            "constrained_decoding_debug": self._params.constrained_decoding_debug,
            "parallel_thinking": self._params.parallel_thinking,
            "auto_score": self._params.auto_score,
            "auto_lrc": self._params.auto_lrc,
            "quality_score_sensitivity": self._params.quality_score_sensitivity,
            "lm_batch_chunk_size": self._params.lm_batch_chunk_size,
            "track_name": self._params.track_name,
            "track_names": self._params.track_names,
            "enable_normalization": self._params.enable_normalization,
            "target_peak_db": self._params.target_peak_db,
            "fade_in_seconds": self._params.fade_in_seconds,
            "fade_out_seconds": self._params.fade_out_seconds,
            "latent_shift": self._params.latent_shift,
            "latent_rescale": self._params.latent_rescale,
            "repaint_mode": self._params.repaint_mode,
            "repaint_strength": self._params.repaint_strength,
            "variance": self._params.variance,
            "seed_extra": self._params.seed_extra,
            "edit": self._params.edit,
            "source_caption": self._params.source_caption,
            "source_lyrics": self._params.source_lyrics,
            "n_min": self._params.n_min,
            "n_max": self._params.n_max,
            "n_avg": self._params.n_avg,
            "auto_gen": self._params.auto_gen,
        }

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def generate(self, caption: Optional[str] = None, lyrics: Optional[str] = None,
                 duration: float = -1, **overrides) -> AceStepGenerationResult:
        """
        Trigger ACE-Step generation via the Gradio API.
        Like pressing the red RECORD button in the studio.
        """
        with self._lock:
            if self._pending:
                return AceStepGenerationResult(ok=False, error="Generation already in progress")
            self._pending = True

        try:
            p = self._params
            # Allow runtime overrides
            if caption is not None:
                p.music_caption = caption
            if lyrics is not None:
                p.lyrics = lyrics
            if duration > 0:
                p.audio_duration = duration
            for k, v in overrides.items():
                if hasattr(p, k):
                    setattr(p, k, v)

            payload = self._build_generation_payload(p)
            result = self._call_gradio("/gradio_api/api/generation_wrapper", payload)

            # Parse result — Gradio returns a list of outputs
            audio_path = self._extract_audio_path(result)

            self._latest_result = AceStepGenerationResult(
                ok=audio_path is not None,
                audio_path=audio_path,
                audio_url=f"{self.host}/gradio_api/file={audio_path}" if audio_path else None,
                metadata={"raw_response": result},
            )
            return self._latest_result

        except Exception as exc:
            self._latest_result = AceStepGenerationResult(ok=False, error=str(exc))
            return self._latest_result
        finally:
            with self._lock:
                self._pending = False

    def _build_generation_payload(self, p: AceStepParams) -> Dict[str, Any]:
        """Pack parameters into the Gradio predict body.
        Aligned to ACE-Step V1.5 source-code inputs order (78 slots).
        The Gradio app has 78 inputs: 73 visible + 5 hidden states.
        """
        return {
            "data": [
                p.music_caption,          # 0  Music Caption
                p.lyrics,                 # 1  Lyrics
                p.bpm,                    # 2  BPM
                p.key,                    # 3  Key
                p.time_signature,         # 4  Time Signature
                p.vocal_language,         # 5  Vocal Language
                max(1, min(20, p.dit_inference_steps)),  # 6  DiT Inference Steps (clamped to Gradio slider max=20)
                p.dit_guidance_scale,     # 7  DiT Guidance Scale
                p.random_seed,            # 8  Random Seed
                p.seed,                   # 9  Seed
                None,                     # 10 Reference Audio
                int(p.audio_duration) if p.audio_duration > 0 else -1,  # 11 Audio Duration (int)
                int(p.batch_size),        # 12 Batch Size (int)
                None,                     # 13 Source Audio
                p.lm_codes_hints,         # 14 LM Codes Hints
                0.0,                      # 15 Repainting Start
                -1.0,                     # 16 Repainting End
                "Fill the audio semantic mask based on the given conditions:",  # 17 Instruction
                p.lm_codes_strength,      # 18 LM Codes Strength
                p.cover_strength,         # 19 Cover Strength
                "text2music",             # 20 task_type (fixed)
                p.no_fsq,                 # 21 no_fsq
                p.use_adg,                # 22 Use ADG
                p.cfg_interval_start,     # 23 CFG Interval Start
                p.cfg_interval_end,       # 24 CFG Interval End
                p.shift,                  # 25 Shift
                p.inference_method,       # 26 Inference Method
                p.sampler_mode,           # 27 Sampler Mode
                p.velocity_norm_threshold,# 28 Velocity Norm Threshold
                p.velocity_ema_factor,    # 29 Velocity EMA Factor
                p.enable_dcw,             # 30 Enable DCW
                p.dcw_mode,               # 31 DCW Mode
                p.dcw_scaler,             # 32 DCW Scaler
                p.dcw_high_scaler,        # 33 DCW High Scaler
                p.dcw_wavelet,            # 34 DCW Wavelet
                p.custom_timesteps,       # 35 Custom Timesteps
                p.audio_format,           # 36 Audio Format
                p.mp3_bitrate,            # 37 MP3 Bitrate
                int(p.mp3_sample_rate) if p.mp3_sample_rate else 48000,  # 38 MP3 Sample Rate (int)
                p.lm_temperature,         # 39 LM Temperature
                p.think,                  # 40 Think
                p.lm_cfg_scale,           # 41 LM CFG Scale
                p.lm_top_k,               # 42 LM Top-K
                p.lm_top_p,               # 43 LM Top-P
                p.lm_negative_prompt,     # 44 LM Negative Prompt
                p.cot_metas,              # 45 CoT Metas
                p.caption_rewrite,        # 46 CaptionRewrite
                p.cot_language_detection, # 47 CoT Language Detection
                None,                     # 48 HIDDEN STATE: is_format_caption_state
                p.constrained_decoding_debug,  # 49 Constrained Decoding Debug
                p.parallel_thinking,           # 50 ParallelThinking
                p.auto_score,                  # 51 Auto Score
                p.auto_lrc,                    # 52 Auto LRC
                p.quality_score_sensitivity,   # 53 Quality Score Sensitivity
                int(p.lm_batch_chunk_size),    # 54 LM Batch Chunk Size (int)
                p.track_name or None,          # 55 Track Name (None, not "")
                p.track_names,                 # 56 Track Names
                p.enable_normalization,        # 57 Enable Normalization
                p.target_peak_db,              # 58 Target Peak (dB)
                p.fade_in_seconds,             # 59 Fade In
                p.fade_out_seconds,            # 60 Fade Out
                p.latent_shift,                # 61 Latent Shift
                p.latent_rescale,              # 62 Latent Rescale
                p.repaint_mode,                # 63 Repaint Mode
                p.repaint_strength,            # 64 Repaint Strength
                p.variance,                    # 65 variance
                p.seed_extra,                  # 66 seed
                p.edit,                        # 67 Edit
                p.source_caption or None,      # 68 source caption
                p.source_lyrics or None,       # 69 source lyrics
                p.n_min,                       # 70 n_min
                p.n_max,                       # 71 n_max
                p.n_avg,                       # 72 n_avg
                p.auto_gen,                    # 73 AutoGen
                0,                             # 74 HIDDEN STATE: current_batch_index
                0,                             # 75 HIDDEN STATE: total_batches
                [],                            # 76 HIDDEN STATE: batch_queue
                {},                            # 77 HIDDEN STATE: generation_params_state
            ],
        }

    def _call_gradio(self, path: str, payload: Dict[str, Any]) -> Any:
        """POST to the Gradio API and return the JSON response."""
        url = f"{self.host}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _extract_audio_path(self, result: Any) -> Optional[str]:
        """Dig through Gradio's nested response to find the audio file path.
        ACE-Step V1.5 returns FileData inside update dicts: {"value": {"path": "...", "url": "..."}}
        """
        try:
            data = result.get("data", result)
            if isinstance(data, list):
                for item in data:
                    # ACE-Step V1.5 format: {"value": {"path": "...", "url": "..."}}
                    if isinstance(item, dict):
                        val = item.get("value")
                        if isinstance(val, dict) and val.get("path"):
                            return val["path"]
                        if isinstance(val, str) and (val.endswith(".mp3") or val.endswith(".wav") or val.endswith(".flac")):
                            return val
                        if item.get("path"):
                            return item["path"]
                    if isinstance(item, str) and (item.endswith(".mp3") or item.endswith(".wav") or item.endswith(".flac")):
                        return item
            if isinstance(data, dict):
                val = data.get("value")
                if isinstance(val, dict) and val.get("path"):
                    return val["path"]
                if data.get("path"):
                    return data["path"]
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Latest result
    # ------------------------------------------------------------------
    @property
    def latest_result(self) -> Optional[AceStepGenerationResult]:
        with self._lock:
            return self._latest_result

    @property
    def is_pending(self) -> bool:
        with self._lock:
            return self._pending


# Singleton bridge instance — like the one dedicated patch cable
# that always stays plugged between the two studios.
_acestep_bridge: Optional[AceStepBridge] = None
_acestep_lock = threading.Lock()


def get_acestep_bridge() -> AceStepBridge:
    """Return the singleton ACE-Step bridge."""
    global _acestep_bridge
    with _acestep_lock:
        if _acestep_bridge is None:
            _acestep_bridge = AceStepBridge()
        return _acestep_bridge
