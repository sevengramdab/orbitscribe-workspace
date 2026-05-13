"""
Agent 9 — ComfyUI API Client
============================
Think of this as the remote-control app for a smart-home audio system.
It talks to the ComfyUI server over HTTP (like a Wi-Fi thermostat app
 talking to the HVAC controller) to queue prompts, poll progress, and
download the finished audio files.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import requests
import numpy as np

from infinite_jukebox.audio_backends.base import AudioSegment


@dataclass
class ComfyUIConfig:
    host: str = "127.0.0.1"
    port: int = 8188
    workflow_path: str = "infinite_jukebox/comfyui/workflows/ace_step_1_5.json"


class ComfyUIClient:
    """
    HTTP client for ComfyUI's REST API.
    Like a BACnet client polling a building automation server:
    it reads registers (queue status), writes setpoints (prompts),
    and fetches trend logs (output files).
    """

    def __init__(self, config: ComfyUIConfig = None) -> None:
        self.cfg = config or ComfyUIConfig()
        self.base_url = f"http://{self.cfg.host}:{self.cfg.port}"
        self._workflow = self._load_workflow()

    def _load_workflow(self) -> Dict[str, Any]:
        """Load the ACE-Step 1.5 workflow JSON from disk."""
        try:
            with open(self.cfg.workflow_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ComfyUI] Could not load workflow: {e}")
            return {}

    def is_online(self) -> bool:
        """Ping the ComfyUI server — like a network connectivity test."""
        try:
            resp = requests.get(f"{self.base_url}/system_stats", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def queue_prompt(
        self,
        lyrics: str = "",
        tags: str = "electronic, ambient, fluid",
        duration_sec: float = 10.0,
        cfg_scale: float = 2.0,
        keyscale: str = "E minor",
        timesignature: str = "4",
    ) -> Optional[str]:
        """
        Submit a generation job to ComfyUI.
        Returns the prompt_id (like a work-order number) or None on failure.
        """
        if not self._workflow:
            return None

        # Clone workflow and set inputs
        workflow = json.loads(json.dumps(self._workflow))
        nodes = workflow.get("nodes", [])
        for node in nodes:
            if node.get("id") == 21:
                wv = node.get("widgets_values", [])
                # Map widgets: [tags, lyrics, lang, time, key, gen_codes, cfg, dur, dur_ctrl, unet, clip1, clip2, vae]
                if len(wv) >= 13:
                    wv[0] = tags
                    wv[1] = lyrics
                    wv[6] = cfg_scale
                    wv[7] = duration_sec
                node["widgets_values"] = wv

        payload = {
            "prompt": workflow,
            "client_id": str(uuid.uuid4()),
        }

        try:
            resp = requests.post(f"{self.base_url}/prompt", json=payload, timeout=10)
            data = resp.json()
            return data.get("prompt_id")
        except Exception as e:
            print(f"[ComfyUI] Queue failed: {e}")
            return None

    def get_history(self, prompt_id: str, timeout_sec: float = 300.0) -> Optional[Dict]:
        """
        Poll ComfyUI history until the job completes or times out.
        Like waiting for the elevator to arrive — we check the indicator
        light every second until the doors open.
        """
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                resp = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=5)
                data = resp.json()
                if prompt_id in data:
                    return data[prompt_id]
            except Exception:
                pass
            time.sleep(1.0)
        return None

    def download_audio(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """Fetch a generated audio file from ComfyUI's view endpoint."""
        try:
            params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            resp = requests.get(f"{self.base_url}/view", params=params, timeout=30)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            print(f"[ComfyUI] Download failed: {e}")
        return None

    def generate_and_fetch(
        self,
        lyrics: str = "",
        tags: str = "electronic, ambient, fluid",
        duration_sec: float = 10.0,
        **kwargs
    ) -> Optional[AudioSegment]:
        """
        End-to-end: queue, wait, download, and return an AudioSegment.
        Like pressing the 'Generate' button and catching the output file.
        """
        prompt_id = self.queue_prompt(lyrics=lyrics, tags=tags, duration_sec=duration_sec, **kwargs)
        if not prompt_id:
            return None

        history = self.get_history(prompt_id)
        if not history:
            return None

        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            files = node_output.get("files", [])
            for f in files:
                data = self.download_audio(f)
                if data:
                    # Convert WAV bytes to numpy array (simplified)
                    samples = self._wav_bytes_to_pcm(data)
                    return AudioSegment(
                        pcm_samples=samples,
                        sample_rate=44100,
                        channels=2,
                        duration_sec=duration_sec,
                        metadata={"backend": "comfyui", "prompt_id": prompt_id, "lyrics": lyrics},
                    )
        return None

    @staticmethod
    def _wav_bytes_to_pcm(data: bytes) -> np.ndarray:
        """Quick WAV parser — assumes 16-bit stereo 44.1kHz."""
        try:
            import wave
            import io
            with wave.open(io.BytesIO(data), "rb") as wf:
                nframes = wf.getnframes()
                raw = wf.readframes(nframes)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if wf.getnchannels() == 2:
                    samples = samples.reshape(-1, 2).mean(axis=1)
                return samples
        except Exception:
            return np.zeros(44100, dtype=np.float32)
