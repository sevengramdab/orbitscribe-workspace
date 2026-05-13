"""
Agent 9 — Integrator: Flask Blueprint & REST API
================================================
Think of this file as the patch panel that wires the Infinite Jukebox
into the existing OrbitScribe building. It creates a Flask Blueprint
so the main voice web server can "mount" us like an AV rack sliding
into an equipment bay.

ELI5: Imagine you already have a home with a breaker panel (Flask app).
We're adding a new wing (the visualizer). Instead of rebuilding the whole
house, we just run a new feeder cable (Blueprint) from the main panel
to the new wing's sub-panel.
"""

from __future__ import annotations

# Like the file cabinet where you store the as-built drawings for each jobsite.
import json
# Like the wall clock in the home-automation hub that schedules when lights turn on and off.
import time
# Like the blueprint drawer that labels every wire size and breaker rating on the plans.
from typing import Dict, Any, Optional
# Like the janitor's key ring that opens every door in the building.
import os
import platform
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

# Like ordering the breaker panel, dimmer racks, and conduit from the electrical supply house.
from flask import Blueprint, render_template, jsonify, request, Response

# Like pulling the locked reference drawing and the VAV schedules from the jobsite trailer.
from infinite_jukebox.architecture import (
    # The locked reference drawing that every discipline XREFs into their own sheets.
    ModelSpace,
    # The HVAC VAV box settings that control airflow in each room.
    FluidConfig,
    # The Lutron dimmer scene that sets every light level in the house at once.
    RenderConfig,
    # The tamper-evident seal on a junction box that says how much load is allowed.
    AceStep15Constraint,
    # The keyed switch on an industrial panel: free, locked, override.
    LockState,
    # The Lutron keypad buttons labeled "Cooking," "Entertaining," "Goodnight."
    MoodPreset,
    # The resolution settings on a plotter: draft, standard, presentation, final.
    SimulationQuality,
)
# Like pulling the master PLC program that sequences chillers, boilers, and air handlers.
from infinite_jukebox.engine.main_loop import InfiniteJukeboxEngine, EngineConfig
# Like pulling the battery-powered practice amp out of the truck for when the studio is offline.
from infinite_jukebox.audio_backends.web_audio import WebAudioBackend
# Like pulling the Dante audio-over-IP bridge out of the rack to talk to the main mixing desk.
from infinite_jukebox.audio_backends.comfyui import ComfyUIBackend
# Like pulling the Wi-Fi thermostat app configuration off the touchscreen.
from infinite_jukebox.comfyui.client import ComfyUIConfig
from infinite_jukebox.gpu.detector import detect_gpus, gpu_count, primary_gpu_name
# Like the Dante bridge that connects the ACE-Step studio to the jukebox cockpit.
from infinite_jukebox.acestep_bridge import get_acestep_bridge, AceStepBridge


# =============================================================================
# BLUEPRINT — The new equipment rack sliding into the main panel
# =============================================================================

# Like bolting a new sub-panel onto the main breaker box with its own set of circuit breakers.
infinite_jukebox_bp = Blueprint(
    # Like engraving the panel name on the sub-panel door so the electrician knows which wing it feeds.
    "infinite_jukebox",
    # Like the nameplate on the sub-panel that says who manufactured it.
    __name__,
    # Like telling the sub-panel where the lighting-control templates are stored.
    template_folder="templates",
    # Like telling the sub-panel where the spare conduit and wire are kept.
    static_folder="static",
    # Like labeling the static wire rack with a special tag so it doesn't collide with the main house wiring.
    static_url_path="/jukebox-static",
    # Like painting the sub-panel address on the feeder cable so every electrician knows it's for the new wing.
    url_prefix="/jukebox",
)

# Global engine instance — like the central plant chiller that stays running 24/7.
_engine: Optional[InfiniteJukeboxEngine] = None


def get_or_create_engine() -> InfiniteJukeboxEngine:
    """
    Singleton factory — like ensuring there's only one boiler in the
    mechanical room. If it already exists, return it; otherwise commission.
    """
    # Like telling the function it can touch the global chiller variable instead of installing a second one.
    global _engine
    # Like checking if the boiler is already roaring before wheeling in a second one.
    if _engine is None:
        # Like commissioning a brand new Carrier i-Vu with a 60 Hz scan cycle setpoint.
        _engine = InfiniteJukeboxEngine(config=EngineConfig(target_fps=60.0))
        # Like pressing the AUTO button so the chiller starts and the scan cycle begins.
        _engine.start()
    # Like pointing at the single approved boiler and telling the caller to connect their pipes to it.
    return _engine


# =============================================================================
# ROUTES — The HMI screens and API endpoints
# =============================================================================

@infinite_jukebox_bp.route("/")
def jukebox_index():
    """
    Main visualizer page — like the primary touchscreen in the lobby
    that shows the pretty fluid graphics.
    """
    gpus = detect_gpus()
    response = render_template(
        "jukebox.html",
        gpu_name=gpus[0]["name"] if gpus else "CPU Render",
        gpu_count=len(gpus),
        gpu_memory=f"{gpus[0]['memory_mb'] // 1024} GB" if gpus else "N/A",
        gpu_util=gpus[0]["utilization"] if gpus else 0,
        gpu_temp=gpus[0]["temperature"] if gpus else 0,
    )
    resp = Response(response)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@infinite_jukebox_bp.route("/api/status")
def api_status():
    """
    Health check — like reading the BAS trend log for chiller status.
    Returns FPS, quality level, breaker state, lock state, mood, GPU temps, and viewport map.
    """
    # Like walking into the mechanical room and glancing at the Carrier i-Vu display.
    engine = get_or_create_engine()
    # Like printing the full BACnet trend log to a PDF so we can read every meter at once.
    perf_report = engine.get_performance_report()
    # Like bundling every meter reading into one JSON packet so the lobby touchscreen can display it.
    return jsonify({
        # Like the green RUN light on the chiller control panel.
        "running": engine._running,
        # Like the job-ticket counter on the printer that shows how many frames have been processed.
        "frame_index": engine._frame_index,
        # Like the plotter resolution dial: LOW, MEDIUM, HIGH, or ULTRA.
        "quality": engine.model.fluid_config.grid_resolution.name,
        # Like the red TRIP indicator on the main breaker handle.
        "breaker_tripped": engine.breaker.is_tripped,
        # Like the red fault tag hanging on the breaker handle explaining why it opened.
        "breaker_reason": engine.breaker.reason,
        # Like the position of the keyed switch on the industrial panel: free, locked, or override.
        "breaker_lock_state": engine.model.lock_state.value,
        # Like the complete BACnet report with avg_fps, p99_frame_time, dropped_frames, and GPU profiles.
        "performance": perf_report,
        # Like the monitor schedule on the security desk showing which screens are on and what resolution they use.
        "viewports": [
            {
                # Like the engraved monitor label on the video wall: PRIMARY, SECONDARY, etc.
                "slot": vp.slot.name,
                # Like the power LED on the monitor showing whether it's energized or dark.
                "enabled": vp.enabled,
                # Like the panel number sticker on the back of the monitor showing which GPU room feeds it.
                "gpu_index": vp.gpu_index,
                # Like the placard that says "Room 101: 1920×1080" instead of two separate notes.
                "resolution": f"{vp.width_px}x{vp.height_px}",
            }
            for vp in engine.model.viewports
        ],
        # Like the Lutron keypad button that is currently illuminated: ambient, energetic, dark, chaos, or minimal.
        "mood": engine.model.mood.value,
        # Like the thermal-camera snapshots from each GPU electrical room.
        "gpu_profiles": perf_report.get("gpu_profiles", {}),
        "gpu_utilization": [
            g.get("utilization", 0)
            for g in perf_report.get("gpu_profiles", {}).values()
        ],
    })


@infinite_jukebox_bp.route("/api/config", methods=["GET", "POST"])
def api_config():
    """
    Read or update engine configuration — like the facilities manager
    adjusting thermostat setpoints from their laptop.
    """
    # Like walking into the mechanical room and pulling up the i-Vu screen on the laptop.
    engine = get_or_create_engine()
    # If the facilities manager just wants to read the current setpoints without changing anything.
    if request.method == "GET":
        # Like printing the current VAV schedule, lighting scene, code table, and keypad button to a single PDF.
        return jsonify({
            # Like the HVAC control panel page showing viscosity, curl strength, and grid resolution.
            "fluid": {
                # Like the plotter resolution dial reading.
                "resolution": engine.model.fluid_config.grid_resolution.name,
                # Like the viscosity knob position.
                "viscosity": engine.model.fluid_config.viscosity,
                # Like the curl-strength knob position.
                "curl_strength": engine.model.fluid_config.curl_strength,
                # Like the Jacobi iteration counter.
                "pressure_iterations": engine.model.fluid_config.pressure_iterations,
                # Like the velocity-dissipation friction curve setting.
                "velocity_dissipation": engine.model.fluid_config.velocity_dissipation,
                # Like the density-dissipation dimmer fade speed.
                "density_dissipation": engine.model.fluid_config.density_dissipation,
                # Like the nozzle-orifice size.
                "splat_radius": engine.model.fluid_config.splat_radius,
                # Like the timestep clock speed.
                "timestep": engine.model.fluid_config.timestep,
            },
            # Like the Lutron lighting scene sheet showing bloom, sunrays, exposure, and gamma.
            "render": {
                # Like the bloom dimmer slider.
                "bloom_intensity": engine.model.render_config.bloom_intensity,
                # Like the bloom iteration counter.
                "bloom_iterations": engine.model.render_config.bloom_iterations,
                # Like the sunrays weight knob.
                "sunrays_weight": engine.model.render_config.sunrays_weight,
                # Like the dither strength roller pressure.
                "dither_strength": engine.model.render_config.dither_strength,
                # Like the color-temperature dial in Kelvin.
                "color_temperature": engine.model.render_config.color_temperature,
                # Like the master exposure dimmer.
                "exposure": engine.model.render_config.exposure,
                # Like the gamma curve knob.
                "gamma": engine.model.render_config.gamma,
            },
            # Like the NEC ampacity table posted on the panel door.
            "ace_constraints": {
                # Like the max-amps rating on the main breaker.
                "max_syllabic_density": engine.model.ace_constraints.max_syllabic_density,
                # Like the minimum clearance zone around high-voltage lines.
                "min_negative_space_ratio": engine.model.ace_constraints.min_negative_space_ratio,
                # Like the minimum spacing between parallel conduits.
                "frequency_mask_budget_hz": engine.model.ace_constraints.frequency_mask_budget_hz,
                # Like the rigid-conduit spacing grid size.
                "tempo_quantize_grid": engine.model.ace_constraints.tempo_quantize_grid,
                # Like the keyed-switch position.
                "lock_state": engine.model.ace_constraints.lock_state.value,
                # Like the grammar preset label.
                "grammar_preset": engine.model.ace_constraints.grammar_preset,
            },
            # Like the illuminated button on the Lutron keypad.
            "mood": engine.model.mood.value,
        })

    # If the facilities manager is sending new setpoints from the laptop, we parse the JSON packet.
    data = request.get_json(force=True, silent=True) or {}
    # Like handing the change order to the central plant controller so it can route each item through the plan reviewer.
    results = engine.apply_config_delta(data)
    # Like sending the annotated clipboard back to the facilities manager showing what was approved or rejected.
    return jsonify({"ok": True, "results": results})


@infinite_jukebox_bp.route("/api/audio_frame", methods=["POST"])
def api_audio_frame():
    """
    Push an audio FFT frame from an external source (e.g., the extension
    or a separate audio capture thread). Like a BACnet analog input
    object receiving a 4–20 mA signal from a microphone pre-amp.
    """
    # Like walking into the mechanical room and plugging the microphone pre-amp into the analog input card.
    engine = get_or_create_engine()
    # Like reading the voltage levels off the 4–20 mA loop that the extension just transmitted.
    data = request.get_json(force=True, silent=True) or {}
    # Like checking the packet to see if it actually contains spectrum bins or just silence.
    bins = data.get("bins", [])
    # If the packet is empty, it's like a dead sensor wire — we return a bad-signal error.
    if not bins:
        # Like the BAS showing a red "SENSOR FAULT" light on the analog input card.
        return jsonify({"ok": False, "error": "No bins provided"}), 400

    # Like pulling the spectrum analyzer sweep definition off the shelf.
    from infinite_jukebox.architecture import AudioFrame
    # Like pulling the digital multimeter out of the toolbox to measure the incoming signal.
    import numpy as np

    # Like building one complete spectrum-analyzer sweep packet with timestamp, bins, peak, and metadata.
    frame = AudioFrame(
        # Like writing the current wall-clock time on the sweep ticket so we know when the sample was taken.
        timestamp_ms=int(time.time() * 1000),
        # Like copying the 512-bin voltage readings from the sensor into the packet buffer.
        frequency_bins=np.array(bins, dtype=np.float32),
        # Like noting the highest peak voltage seen during this sweep.
        peak_amplitude=float(data.get("peak", 0.0)),
        # Like noting how many times the waveform crossed zero — a rough brightness gauge.
        zero_crossing_rate=float(data.get("zcr", 0.0)),
        # Like noting where the "center of mass" of the spectrum sits — bright sounds vs. dark sounds.
        spectral_centroid=float(data.get("centroid", 0.5)),
    )
    # Like plugging the completed sweep packet into the engine's analog input jack.
    engine.feed_audio(frame)
    # Like the BAS showing a green "SIGNAL OK" light.
    return jsonify({"ok": True})


@infinite_jukebox_bp.route("/api/stream")
def api_stream():
    """
    Server-Sent Events stream of engine telemetry.
    Like a Modbus TCP server constantly broadcasting register values
    so any HMI on the network can display live data.
    """
    # Like the BACnet broadcast module that shouts meter readings into the building network every half-second.
    def event_stream():
        # Like grabbing the one and only boiler so we can read its dials.
        engine = get_or_create_engine()
        # Like the Modbus server that keeps broadcasting forever until someone pulls the network cable.
        while True:
            # Like printing the full trend log for the last two minutes.
            perf = engine.get_performance_report()
            # Like stuffing every dial reading into one JSON register packet.
            payload = json.dumps({
                # Like the job-ticket counter showing how many frames the plant has processed.
                "frame_index": engine._frame_index,
                # Like the RPM gauge on the chiller converted back from cycle time.
                "fps": perf.get("avg_fps", 0),
                # Like the plotter resolution dial reading.
                "quality": perf.get("quality", "HIGH"),
                # Like the main breaker status: tripped or closed, plus the reason tag and keyed-switch position.
                "breaker_state": {
                    # Like the red TRIP indicator on the breaker handle.
                    "tripped": engine.breaker.is_tripped,
                    # Like the fault tag hanging on the handle.
                    "reason": engine.breaker.reason,
                    # Like the keyed-switch position.
                    "lock_state": engine.model.lock_state.value,
                },
                # Like the thermal camera pointed at each GPU electrical room.
                "gpu_temps": {
                    # Like reading the temperature display on each panel and writing it down.
                    k: v.get("temperature", 0.0)
                    for k, v in perf.get("gpu_profiles", {}).items()
                },
            })
            # Like shouting the register packet onto the Modbus network followed by a newline.
            yield f"data: {payload}\n\n"
            # Like the broadcast timer waiting 500 milliseconds before the next shout.
            time.sleep(0.5)

    # Like connecting the BACnet broadcast wire to the Flask response socket with the correct protocol header.
    return Response(event_stream(), mimetype="text/event-stream")


@infinite_jukebox_bp.route("/api/breaker/reset", methods=["POST"])
def api_breaker_reset():
    """
    Reset the Main Breaker after a trip.
    Like the facilities manager walking to the main panel, checking
    that the overload has cleared, and flipping the handle back to ON.
    """
    # Like walking into the electrical room and pointing at the main breaker panel.
    engine = get_or_create_engine()
    # Like flipping the main breaker handle back to ON and turning the keyed switch to FREE.
    engine.reset_breaker()
    # Like the BAS showing a green "SYSTEM NORMAL" light on the fire panel.
    return jsonify({
        # Like telling the HMI the breaker is now closed.
        "ok": True,
        # Like confirming the breaker handle is pointing to ON.
        "tripped": engine.breaker.is_tripped,
        # Like confirming the keyed switch is back in the FREE position.
        "lock_state": engine.model.lock_state.value,
    })


@infinite_jukebox_bp.route("/api/scene/save", methods=["POST"])
def api_scene_save():
    """
    Save the current engine state as a named scene.
    Like pressing the 'Save Scene' button on the Lutron HomeWorks
    touchscreen so the current light levels are stored in flash memory.
    """
    # Like walking up to the home-automation hub touchscreen in the lobby.
    engine = get_or_create_engine()
    # Like reading the name the homeowner typed into the save dialog.
    data = request.get_json(force=True, silent=True) or {}
    # Like checking if the homeowner actually typed a name or just hit save on a blank field.
    name = data.get("name", "")
    # If the name is blank, it's like trying to label a breaker slot with an empty sticker — not allowed.
    if not name:
        # Like the hub showing "PLEASE ENTER A SCENE NAME" in red text.
        return jsonify({"ok": False, "error": "Scene name required"}), 400
    # Like pressing the actual save button and writing every dimmer level to the memory card.
    engine.save_scene(name)
    # Like the hub beeping once and showing "SCENE SAVED" in green.
    return jsonify({"ok": True, "scene": name})


@infinite_jukebox_bp.route("/api/scene/load", methods=["POST"])
def api_scene_load():
    """
    Load a previously saved scene by name.
    Like pressing the 'Cooking' or 'Goodnight' button on the Lutron
    keypad and watching every light fade to its stored level.
    """
    # Like walking up to the keypad on the wall.
    engine = get_or_create_engine()
    # Like reading which button the homeowner pressed.
    data = request.get_json(force=True, silent=True) or {}
    # Like checking the button label to see if it's blank.
    name = data.get("name", "")
    # If the label is blank, it's like pressing a ghost button — nothing happens.
    if not name:
        # Like the keypad flashing red and showing "NO SCENE SELECTED."
        return jsonify({"ok": False, "error": "Scene name required"}), 400
    # Like pressing the button and sending the recall command to every dimmer in the house.
    engine.load_scene(name)
    # Like the lights fading to the saved scene and the hub showing "SCENE RECALLED" in green.
    return jsonify({
        # Like acknowledging the recall succeeded.
        "ok": True,
        # Like echoing the scene name back to the touchscreen.
        "scene": name,
        # Like showing the current plotter resolution after the scene change.
        "quality": engine.model.fluid_config.grid_resolution.name,
        # Like showing the current Lutron keypad button that is now active.
        "mood": engine.model.mood.value,
    })


@infinite_jukebox_bp.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Generate audio via ACE-Step 1.5 (ComfyUI) or fallback to Web Audio.
    Like pressing the 'Call for Elevator' button — if the express car
    (ComfyUI) is available, take it; otherwise use the stairs (Web Audio).
    """
    # Like reading the work order that just came in from the front desk.
    data = request.get_json(force=True, silent=True) or {}
    # Like checking if the client wrote lyrics on the order form, or leaving it blank for instrumental.
    lyrics = data.get("lyrics", "")
    # Like reading the genre tags off the form, defaulting to electronic ambient if the line is blank.
    tags = data.get("tags", "electronic, ambient, fluid")
    # Like reading the duration request, defaulting to ten seconds if the client didn't specify.
    duration = float(data.get("duration", 10.0))

    # Like calling the main studio control room to see if the mixing desk is powered on.
    comfy = ComfyUIBackend(config=ComfyUIConfig())
    # Like checking if the Dante bridge has a green link light.
    if comfy.is_available():
        # Like pressing the generate button on the ACE-Step console and waiting for the AI to compose.
        segment = comfy.generate(prompt=lyrics, tags=tags, duration_sec=duration)
        # If the studio actually delivered a wav file, we report success.
        if segment:
            # Like handing the finished track to the DJ with a label that says "Mixed at ComfyUI Studios."
            return jsonify({"ok": True, "backend": "comfyui", "duration": segment.duration_sec})

    # If the express elevator is out of order, we take the stairs.
    # Like pulling the battery-powered practice amp out of the closet.
    web = WebAudioBackend()
    # Like playing a groove loop on the practice amp that still drives the fluid visualizer.
    segment = web.generate(prompt=lyrics, duration_sec=duration)
    # Like handing the loop to the DJ with a label that says "Recorded in the basement."
    return jsonify({
        # Like saying the track is ready even though it came from the backup amp.
        "ok": True,
        # Like labeling the delivery slip "Web Audio" so the DJ knows it's a procedural loop.
        "backend": "web_audio",
        # Like writing the actual length of the loop on the slip, or zero if the amp failed.
        "duration": segment.duration_sec if segment else 0,
    })


# =============================================================================
# AUTO DJ INTEGRATION — Proxy panel for the external AUTO DJ ecosystem
# =============================================================================

_AUTO_DJ_ROOT = Path("d:/claw source code/claw-code-parity")
_AUTO_DJ_WEBUI_PORT = 8503
_AUTO_DJ_STATUS_URL = f"http://localhost:{_AUTO_DJ_WEBUI_PORT}/status"
_COMBO_LOG = _AUTO_DJ_ROOT / "outputs" / "auto_dj" / "combo_feedback.jsonl"

_webui_proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]
_webui_lock = threading.Lock()


def _profile_hardware() -> Dict[str, Any]:
    """
    Detect GPU tier via pynvml + psutil.
    Like the pre-flight scan the fighter-jet engine runs before ignition.
    """
    gpu_name = "Unknown"
    vram_gb = 0.0
    compute_cap: tuple[int, int] = (0, 0)
    gpu_ok = False

    try:
        import warnings as _warnings
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", FutureWarning)
            import pynvml  # type: ignore[import]
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode()
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_gb = mem_info.total / (1024 ** 3)
        compute_cap = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
        gpu_ok = True
    except Exception:
        pass

    cpu_cores = 4
    ram_gb = 8.0
    try:
        import psutil  # type: ignore[import]
        cpu_cores = psutil.cpu_count(logical=True) or 4
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    if gpu_ok and vram_gb >= 20.0 and cpu_cores >= 16 and ram_gb >= 60.0:
        tier = "Tier 1 (Fighter Jet)"
    elif gpu_ok and vram_gb >= 10.0 and cpu_cores >= 8 and ram_gb >= 24.0:
        tier = "Tier 2 (Commercial Jet)"
    else:
        tier = "Tier 3 (Minimum Safe)"

    return {
        "gpu_name": gpu_name,
        "vram_gb": round(vram_gb, 1),
        "compute_capability": f"{compute_cap[0]}.{compute_cap[1]}" if gpu_ok else None,
        "cpu_cores": cpu_cores,
        "ram_gb": round(ram_gb, 1),
        "tier": tier,
        "platform": platform.system(),
        "python_version": sys.version.split()[0],
    }


def _auto_dj_status() -> Optional[Dict[str, Any]]:
    """
    Read current AUTO DJ session state.
    Priority: /status API (port 8503) -> combo_feedback.jsonl fallback.
    Like the audio reactivity reader in launch_art_engine.py.
    """
    try:
        req = urllib.request.Request(_AUTO_DJ_STATUS_URL, method="GET")
        with urllib.request.urlopen(req, timeout=1) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        pass
    if _COMBO_LOG.is_file():
        try:
            with open(_COMBO_LOG, "rb") as fh:
                fh.seek(0, 2)
                size = fh.tell()
                block = min(4096, size)
                fh.seek(-block, 2)
                tail = fh.read(block).decode("utf-8", errors="replace")
            lines = [ln for ln in tail.splitlines() if ln.strip()]
            return json.loads(lines[-1]) if lines else None
        except Exception:
            pass
    return None


@infinite_jukebox_bp.route("/api/hardware")
def api_hardware():
    """
    Return pre-flight hardware scan.
    Like the fighter-jet engine's diagnostic relay panel.
    """
    try:
        return jsonify(_profile_hardware())
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@infinite_jukebox_bp.route("/api/auto_dj/status")
def api_auto_dj_status():
    """
    Proxy current AUTO DJ track metadata.
    Like reading the flight-deck tape for current heading and airspeed.
    """
    data = _auto_dj_status()
    if data is None:
        return jsonify({"ok": False, "error": "AUTO DJ not running or unreachable"}), 503
    # Normalise field names so the panel doesn't care which source replied.
    return jsonify({
        "ok": True,
        "bpm": data.get("current_bpm") or data.get("bpm"),
        "key": data.get("current_key") or data.get("key"),
        "time_signature": data.get("current_time_signature") or data.get("time_signature"),
        "title": data.get("current_track_title") or data.get("track_title"),
        "prompt": data.get("current_prompt") or data.get("prompt"),
        "gpu_utilization": data.get("gpu_utilization"),
    })


@infinite_jukebox_bp.route("/api/auto_dj/launch", methods=["POST"])
def api_auto_dj_launch():
    """
    Spawn the AUTO DJ Web UI (port 8503) as a background process.
    Like pressing the ignition switch on the fighter-jet engine.
    """
    global _webui_proc
    with _webui_lock:
        if _webui_proc is not None and _webui_proc.poll() is None:
            return jsonify({"ok": True, "pid": _webui_proc.pid, "already_running": True})
        script = _AUTO_DJ_ROOT / "AUTO_DJ" / "auto_dj_web_ui.py"
        if not script.is_file():
            return jsonify({"ok": False, "error": f"Script not found: {script}"}), 404
        python = str(_AUTO_DJ_ROOT / ".venv" / "Scripts" / "python.exe")
        if not Path(python).is_file():
            python = sys.executable
        log_path = _AUTO_DJ_ROOT / "logs" / "auto_dj_webui_launcher.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "PYTHONPATH": str(_AUTO_DJ_ROOT)}
        try:
            with open(log_path, "a", encoding="utf-8") as lf:
                kwargs: Dict[str, Any] = {
                    "cwd": str(_AUTO_DJ_ROOT),
                    "stdout": lf,
                    "stderr": lf,
                    "stdin": subprocess.DEVNULL,
                    "env": env,
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                _webui_proc = subprocess.Popen([python, str(script)], **kwargs)
            return jsonify({"ok": True, "pid": _webui_proc.pid})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500


@infinite_jukebox_bp.route("/api/auto_dj/kill", methods=["POST"])
def api_auto_dj_kill():
    """
    Terminate every known AUTO DJ backend/frontend process.
    Like the master kill-switch on the flight-deck.
    """
    import psutil  # type: ignore[import]

    killed: list[str] = []
    own_pid = os.getpid()
    patterns = [
        "auto_dj_web_ui",
        "auto_dj_engine",
        "run_auto_dj",
        "launch_auto_dj",
        "launch_art_engine",
        "launch_jet_engine_webui",
        "launch_jet_plus_webui",
    ]

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        pid = proc.info["pid"]
        if pid == own_pid:
            continue
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if any(pat.lower() in cmdline.lower() for pat in patterns):
                proc.kill()
                killed.append(f"{proc.info['name']} (pid {pid})")
        except Exception:
            pass

    # Kill by port occupation
    for port in (8502, 8503, 8504, 8505):
        try:
            for conn in psutil.net_connections(kind="tcp"):
                laddr = getattr(conn, "laddr", None)
                if laddr and laddr.port == port and conn.pid and conn.pid != own_pid:
                    try:
                        psutil.Process(conn.pid).kill()
                        killed.append(f"port {port} -> {conn.pid}")
                    except Exception:
                        pass
        except Exception:
            pass

    global _webui_proc
    with _webui_lock:
        if _webui_proc is not None:
            try:
                _webui_proc.kill()
                killed.append(f"webui (pid {_webui_proc.pid})")
            except Exception:
                pass
            _webui_proc = None

    return jsonify({"ok": True, "killed": killed})


@infinite_jukebox_bp.route("/api/system/optimize", methods=["POST"])
def api_system_optimize():
    """
    Free RAM/VRAM caches and trim idle working sets.
    Like the janitor sweeping the hangar before the next sortie.
    """
    import gc

    freed: list[str] = []
    collected = gc.collect()
    if collected:
        freed.append(f"GC freed {collected} objects")

    torch_mod = sys.modules.get("torch")
    if torch_mod is not None:
        try:
            torch_mod.cuda.empty_cache()
            freed.append("VRAM cache flushed (torch)")
        except Exception:
            pass

    if sys.platform == "win32":
        try:
            import ctypes
            psapi = ctypes.windll.psapi
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            psapi.EmptyWorkingSet(handle)
            freed.append("Working set trimmed")
        except Exception:
            pass

    return jsonify({"ok": True, "freed": freed})


# =============================================================================
# ACE-STEP INTEGRATION — Connect the music generation studio
# =============================================================================

@infinite_jukebox_bp.route("/api/acestep/status")
def api_acestep_status():
    """
    Check if ACE-Step V1.5 is online and reachable.
    Like calling the studio control room to see if the engineer is at the desk.
    """
    bridge = get_acestep_bridge()
    available = bridge.is_available()
    return jsonify({
        "ok": True,
        "available": available,
        "host": bridge.host,
        "pending": bridge.is_pending,
    })


@infinite_jukebox_bp.route("/api/acestep/params", methods=["GET", "POST"])
def api_acestep_params():
    """
    Read or update ACE-Step generation parameters.
    Like the remote-control panel that lets the pilot adjust the studio mixing desk.
    """
    bridge = get_acestep_bridge()
    if request.method == "GET":
        return jsonify({"ok": True, "params": bridge.get_params_dict()})

    data = request.get_json(force=True, silent=True) or {}
    bridge.update_params(data)
    return jsonify({"ok": True, "params": bridge.get_params_dict()})


@infinite_jukebox_bp.route("/api/acestep/generate", methods=["POST"])
def api_acestep_generate():
    """
    Trigger ACE-Step music generation.
    Like the pilot pressing the 'REQUEST TRACK' button on the intercom.
    """
    bridge = get_acestep_bridge()
    data = request.get_json(force=True, silent=True) or {}

    caption = data.get("caption") or data.get("music_caption", "")
    lyrics = data.get("lyrics", "")
    duration = float(data.get("duration", -1))

    result = bridge.generate(caption=caption, lyrics=lyrics, duration=duration)
    return jsonify({
        "ok": result.ok,
        "audio_path": result.audio_path,
        "audio_url": result.audio_url,
        "error": result.error,
    })


@infinite_jukebox_bp.route("/api/acestep/result")
def api_acestep_result():
    """
    Get the latest generation result.
    Like the studio messenger running down the hall with the finished tape reel.
    """
    bridge = get_acestep_bridge()
    result = bridge.latest_result
    if result is None:
        return jsonify({"ok": False, "error": "No generation has been run yet"}), 404
    return jsonify({
        "ok": result.ok,
        "audio_path": result.audio_path,
        "audio_url": result.audio_url,
        "metadata": result.metadata,
        "error": result.error,
    })


@infinite_jukebox_bp.route("/api/acestep/auto_dj", methods=["POST"])
def api_acestep_auto_dj():
    """
    Trigger ACE-Step with randomized auto-dj parameters.
    Like the autopilot randomly selecting a flight path and radioing the studio.
    """
    import random
    bridge = get_acestep_bridge()

    moods = [
        {"caption": "A peaceful acoustic guitar melody with soft vocals", "bpm": 90, "key": "G major"},
        {"caption": "Energetic electronic dance music with driving bass", "bpm": 128, "key": "F minor"},
        {"caption": "Dark cinematic orchestral score with haunting strings", "bpm": 110, "key": "D minor"},
        {"caption": "Chaotic industrial noise rock with distorted guitars", "bpm": 140, "key": "A minor"},
        {"caption": "Minimal ambient drone with subtle piano textures", "bpm": 70, "key": "C major"},
    ]
    mood = random.choice(moods)

    bridge.update_params({
        "music_caption": mood["caption"],
        "bpm": mood["bpm"],
        "key": mood["key"],
        "dit_inference_steps": random.choice([30, 50, 75]),
        "dit_guidance_scale": round(random.uniform(5.0, 9.0), 1),
        "lm_codes_strength": round(random.uniform(0.5, 1.0), 2),
        "audio_duration": random.choice([15, 20, 30]),
        "shift": round(random.uniform(2.0, 4.0), 1),
        "lm_temperature": round(random.uniform(0.7, 1.0), 2),
    })

    result = bridge.generate()
    return jsonify({
        "ok": result.ok,
        "audio_path": result.audio_path,
        "audio_url": result.audio_url,
        "mood": mood,
        "error": result.error,
    })


# =============================================================================
# REGISTRATION HELPER — Slide the rack into the main panel
# =============================================================================

def register_with_app(app):
    """
    Mount this blueprint onto an existing Flask app.
    ELI5: Like bolting a new sub-panel onto the main breaker box.
    """
    # Like aligning the new sub-panel's mounting holes with the existing breaker box rails.
    app.register_blueprint(infinite_jukebox_bp)
