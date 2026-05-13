"""
Agent 9 — Integrator: Main Engine Loop
======================================
Think of this file as the master PLC ladder logic that ties every
subsystem together: the audio pre-amp (Agent 4), the pump controller
(Agent 2), the lighting board (Agent 5), the video wall router
(Agent 3), and the safety interlocks (Agent 7). It runs the scan
cycle at exactly 60 Hz, reading inputs, solving physics, rendering
frames, and writing outputs — just like a BACnet automation engine.
"""

from __future__ import annotations

# Like the wall clock in the home-automation hub that schedules when lights turn on and off.
import time
# Like the master key ring that keeps every electrical room locked except the one being worked on.
import threading
# Like the blueprint drawer that labels every wire size and breaker rating on the plans.
from typing import Optional, List, Dict, Any
# Like the CAD template that stamps every drawing with the project name and date.
from dataclasses import dataclass, field, replace
# Like the file cabinet where you store the as-built drawings for each jobsite.
from pathlib import Path

# Like pulling every blueprint sheet out of the reference file cabinet so each trade knows the plan.
from infinite_jukebox.architecture import (
    # The locked reference drawing that every discipline XREFs into their own sheets.
    ModelSpace,
    # The HVAC VAV box settings that control airflow in each room.
    FluidConfig,
    # The Lutron dimmer scene that sets every light level in the house at once.
    RenderConfig,
    # The monitor spec sheet for each TV in the security operations center video wall.
    ViewportConfig,
    # The numbered labels on the monitors: PRIMARY, SECONDARY, TERTIARY, AUX_A, AUX_B.
    ViewportSlot,
    # A single sweep of the spectrum analyzer hooked to the audio bus.
    AudioFrame,
    # The colored phases in a three-phase panel: L1 bass, L2 mids, L3 treble.
    AudioChannel,
    # The keyed switch on an industrial panel: free, locked, override.
    LockState,
    # The Lutron keypad buttons labeled "Cooking," "Entertaining," "Goodnight."
    MoodPreset,
    # The tamper-evident seal on a junction box that says how much load is allowed.
    AceStep15Constraint,
    # The floor plan that shows where you can dig without hitting utility lines.
    NegativeSpaceMap,
    # The riser diagram that shows how every electrical panel connects without loops.
    SignalPathDag,
    # The resolution settings on a plotter: draft, standard, presentation, final.
    SimulationQuality,
)
# Like hiring the hydraulic engineer who balances water pressure in the municipal pipes.
from infinite_jukebox.physics.navier_stokes import NavierStokesSolver
# Like commissioning separate electrical rooms with their own breaker panels and VFDs.
from infinite_jukebox.gpu.compute_manager import (
    # The master PLC that sends Modbus commands to five variable-frequency drives.
    GpuComputeManager,
    # The security-NOC video wall operator who decides which camera goes to which monitor.
    ViewportManager,
    # The conveyor belt of pre-built wall sections ready for the display crew.
    StreamingRingBuffer,
)
# Like calling the lighting designer who picks gel colors for every PAR can on stage.
from infinite_jukebox.visuals.color_mapper import AudioColorMapper
# Like installing the whole-home surge protector that smooths the video signal before the TV wall.
from infinite_jukebox.visuals.post_processing import PostProcessPipeline
# Like wiring the fire-alarm shunt-trip breaker and the plan-review desk into the same control room.
from infinite_jukebox.engine.state_manager import (
    # The home-automation hub flash memory that keeps scene data after a power outage.
    StateManager,
    # The main breaker that sheds non-essential loads when the panel is overloaded.
    MainBreaker,
    # The plan reviewer who stamps every change order before the contractor rips open a wall.
    ConfigurationBreaker,
)
# Like mounting the BACnet energy meters and the smart thermostat on the same DIN rail.
from infinite_jukebox.engine.performance import (
    # The Ecobee smart thermostat that learns when to start the AC earlier.
    PerformanceMonitor,
    # The scene controller that pre-dims the lights five seconds before the movie starts.
    LevelStreamingEngine,
    # The thermal camera and clamp meter that walk the jobsite reading every panel.
    HardwareProfiler,
)
# Like connecting the occupancy sensor and the audio spectrum analyzer to the same Crestron processor.
from infinite_jukebox.interaction.input_handler import InputHandler, AudioForceBridge
# Like checking how many breaker panels are actually installed before pulling wire.
from infinite_jukebox.gpu.detector import gpu_count


# =============================================================================
# ENGINE CONFIG — The commissioning sheet taped to the jobsite trailer wall
# =============================================================================

@dataclass
class EngineConfig:
    # Like the setpoint schedule written on the whiteboard in the mechanical room.
    target_fps: float = 60.0
    # Like the number of breaker positions on the spectrum analyzer face.
    audio_fft_bins: int = 512
    # Like the switch that says whether the video wall shows one camera or five.
    enable_multiview: bool = True
    # Like the maximum number of monitors the security desk can support.
    max_viewports: int = 5
    # Like the default plotter resolution setting when nobody touches the dial.
    default_quality: str = "HIGH"


# =============================================================================
# INFINITE JUKEBOX ENGINE — The central plant controller
# =============================================================================

class InfiniteJukeboxEngine:
    """
    The main orchestrator. Owns every subsystem and runs the frame loop.
    Like a Carrier i-Vu building automation system that sequences chillers,
    boilers, air handlers, and VAV boxes from a single front end.
    """

    def __init__(self, config: EngineConfig = None) -> None:
        # Like grabbing the commissioning sheet off the clipboard, or using the factory-default settings if the sheet is blank.
        self.cfg = config or EngineConfig()

        # --- MODEL SPACE (the locked XREF drawing every trade copies) ---
        # Like reading the plotter resolution off the title block to see if the client ordered draft or final.
        quality_enum = getattr(FluidConfig, self.cfg.default_quality, None)
        # If the title block has a smudge and we can't read the resolution, default to presentation quality.
        if quality_enum is None:
            # Like pulling the standard "HIGH" setting off the wall chart because the spec is illegible.
            quality_enum = SimulationQuality.HIGH

        # Auto-detect GPU count so viewports match real hardware.
        detected_gpus = gpu_count()
        actual_viewports = max(1, detected_gpus if detected_gpus > 0 else 1)

        # Like building the master model file that every subcontractor references so nobody builds a beam through a duct.
        self.model = ModelSpace(
            # Like setting the HVAC VAV box to the resolution we just read off the title block.
            fluid_config=FluidConfig(grid_resolution=quality_enum),
            # Like loading the default Lutron scene with all dimmers at mid-level.
            render_config=RenderConfig(),
            # Wire one viewport per detected GPU (minimum 1).
            viewports=[
                ViewportConfig(slot=ViewportSlot(i), gpu_index=i % max(1, detected_gpus))
                for i in range(actual_viewports)
            ],
        )

        # --- STATE & SAFETY (the home-automation hub and main breaker panel) ---
        # Like installing a Lutron HomeWorks processor with a memory card slot in the utility closet.
        self.state = StateManager(persist_path=Path("jukebox_state.json"), model_space=self.model)
        # Like wiring a 200-amp main breaker with a fire-alarm shunt-trip coil to the hub.
        self.breaker = MainBreaker(self.state)
        # Like giving the plan reviewer a desk right next to the hub so he can stamp changes instantly.
        self.config_breaker = ConfigurationBreaker(self.state, self.model)

        # --- PHYSICS (the pump station SCADA controller) ---
        # Like commissioning the variable-frequency drive with the motor nameplate data from the blueprint.
        self.physics = NavierStokesSolver(self.model.fluid_config)

        # --- GPU / VIEWPORTS (the detected GPU electrical rooms) ---
        # Like hiring the master electrician to wire each detected service panel.
        self.gpu = GpuComputeManager(self.model.viewports)
        # Like hiring the security desk operator to manage the video wall.
        self.viewport_manager = ViewportManager(self.model.viewports)

        # --- STREAMING RING BUFFER (the conveyor belt of pre-built wall sections) ---
        # Like sizing the warehouse shelf to hold at least two seconds of pre-fabbed wall sections.
        self.ring_buffer = StreamingRingBuffer(
            # Like counting how many pallets fit on the carousel at 60 frames per second for two seconds.
            capacity=max(30, int(self.cfg.target_fps * 2)),
            # Like handing the warehouse foreman the monitor list so he knows which rooms get pre-built frames.
            viewports=self.model.viewports,
            # Like handing him the HVAC control panel settings so every pre-built wall has the right smoke thickness.
            fluid_config=self.model.fluid_config,
        )
        # Like plugging the conveyor belt into the master PLC so it can request GPU time when needed.
        self.gpu.attach_streamer(self.ring_buffer)
        # Like pressing the green START button on the conveyor belt so the factory worker begins pre-building.
        self.ring_buffer.start()

        # --- INTERACTION (the Crestron touch panel and audio mixer) ---
        # Like programming the audio spectrum analyzer so bass feeds the red PAR cans and treble feeds the blues.
        bridge = AudioForceBridge(
            # Like a patch bay that routes each audio phase to a specific color circuit.
            channel_map={
                # Like sending the heavy-motor sub-panel to the red dimmer.
                AudioChannel.BASS: (0.9, 0.2, 0.1),
                # Like sending the general lighting branch to the amber dimmer.
                AudioChannel.LOW_MID: (0.8, 0.5, 0.1),
                # Like sending the outlet circuits to the green dimmer.
                AudioChannel.MID: (0.2, 0.8, 0.3),
                # Like sending the HVAC control circuits to the cyan dimmer.
                AudioChannel.HIGH_MID: (0.2, 0.5, 0.9),
                # Like sending the low-voltage data circuits to the violet dimmer.
                AudioChannel.TREBLE: (0.6, 0.2, 0.9),
            }
        )
        # Like mounting the occupancy sensor and the audio spectrum analyzer on the same wall plate.
        self.input_handler = InputHandler(audio_bridge=bridge)

        # --- VISUALS (the lighting desk and the color-correction suite) ---
        # Like calling the lighting designer to the venue before the show starts.
        self.color_mapper = AudioColorMapper()
        # Like installing the rack of signal processors: bloom, sunrays, tone-map, dither.
        self.post_process = PostProcessPipeline(self.model.render_config)

        # --- PERFORMANCE (the BACnet energy-management system) ---
        # Like mounting the smart thermostat and programming it for 60 cycles per minute.
        self.perf = PerformanceMonitor(target_fps=self.cfg.target_fps)
        # Like wiring the thermostat to a relay that can call the building engineer when load needs to change.
        self.perf.register_adaptation_callback(self._on_adaptation)

        # Like installing the scene controller that pre-dims the lights before the movie starts.
        self.level_streamer = LevelStreamingEngine(
            # Like telling the scene controller the house refresh rate is 60 Hz.
            frame_rate=self.cfg.target_fps,
            # Like giving the controller a copy of the HVAC settings so pre-rendered frames match.
            fluid_config=self.model.fluid_config,
        )
        # Like walking onto the jobsite with a thermal camera to read each real breaker panel.
        self.hw_profiler = HardwareProfiler(gpu_count=max(1, detected_gpus))

        # --- RUNTIME VARIABLES ---
        # Like flipping the STOP switch to off before the first shift begins.
        self._running = False
        # Like leaving the time-clock slot empty because no worker has punched in yet.
        self._thread: Optional[threading.Thread] = None
        # Like resetting the job-ticket printer to zero so the first frame is number zero.
        self._frame_index = 0
        # Like leaving the audio input jack unplugged until the DJ shows up.
        self._last_audio_frame: Optional[AudioFrame] = None
        # Like leaving the loading dock empty because no panels have been built yet.
        self._last_frame_payload: Optional[Dict[str, Any]] = None
        # Like installing a padlock on the breaker panel so two electricians can't throw the same breaker at once.
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # LIFECYCLE — Start / Stop the central plant
    # -------------------------------------------------------------------------

    def start(self) -> None:
        # Like checking if the Carrier i-Vu is already in AUTO mode before pressing the button again.
        if self._running:
            # Like shrugging because the chiller is already running and there's nothing to do.
            return
        # Like flipping the main switch to AUTO so the scan cycle can begin.
        self._running = True
        # Like hiring a night-shift worker and telling him to run the scan cycle in the background.
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        # Like punching the time clock so the worker walks onto the factory floor.
        self._thread.start()

    def stop(self) -> None:
        # Like flipping the main switch to OFF so the chillers begin their shutdown sequence.
        self._running = False
        # Like checking if there is actually a worker on the clock before waiting by the time clock.
        if self._thread:
            # Like giving the worker two seconds to clean his bench before locking the door.
            self._thread.join(timeout=2.0)
            # Like erasing his employee ID from the schedule because he has gone home.
            self._thread = None
        # Like pressing the red emergency STOP button on the conveyor belt so it halts at the end of the cycle.
        self.ring_buffer.stop()

    def feed_audio(self, frame: AudioFrame) -> None:
        # Like locking the electrical room so no one else changes the patch bay while the DJ is plugging in.
        with self._lock:
            # Like plugging the XLR cable from the DJ mixer into the spectrum analyzer input jack.
            self._last_audio_frame = frame

    # -------------------------------------------------------------------------
    # CONFIGURATION — Route change orders through the plan reviewer
    # -------------------------------------------------------------------------

    def apply_config_delta(self, delta_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Like creating a blank clipboard where we will staple every approved or rejected change order.
        results: Dict[str, Any] = {}
        # Like sorting through the incoming mail and handling each envelope one at a time.
        for key, value in delta_dict.items():
            # Like checking if the envelope is marked "HVAC" and actually contains a drawing.
            if key == "fluid" and isinstance(value, dict):
                # Like opening the current VAV box settings so we know what to compare against.
                fc = self.model.fluid_config
                # Like building a new VAV schedule that keeps every knob we aren't touching exactly where it is.
                new_fc = FluidConfig(
                    # Like reading the resolution off the change order, or keeping the old one if the line is blank.
                    grid_resolution=SimulationQuality[value.get("resolution", fc.grid_resolution.name)] if "resolution" in value else fc.grid_resolution,
                    # Like reading the viscosity knob position, or leaving it alone if the field is blank.
                    viscosity=value.get("viscosity", fc.viscosity),
                    # Like reading the velocity-dissipation setting, or keeping the old friction curve.
                    velocity_dissipation=value.get("velocity_dissipation", fc.velocity_dissipation),
                    # Like reading the density-dissipation setting, or keeping the old dimmer fade speed.
                    density_dissipation=value.get("density_dissipation", fc.density_dissipation),
                    # Like reading the Jacobi iteration count, or keeping the old pipe-tightening schedule.
                    pressure_iterations=value.get("pressure_iterations", fc.pressure_iterations),
                    # Like reading the curl-strength knob, or keeping the old eductor boost level.
                    curl_strength=value.get("curl_strength", fc.curl_strength),
                    # Like reading the nozzle-orifice size, or keeping the old spray tip.
                    splat_radius=value.get("splat_radius", fc.splat_radius),
                    # Like reading the timestep clock speed, or keeping the old 60 Hz scan rate.
                    timestep=value.get("timestep", fc.timestep),
                )
                # Like handing the new VAV schedule to the plan reviewer for approval.
                ok, reason = self.config_breaker.apply_fluid_config(new_fc)
                # If the reviewer stamps APPROVED, we re-commission the pump station with the new motor specs.
                if ok:
                    # Like swapping the old VFD programming card for the new one.
                    self.physics = NavierStokesSolver(self.model.fluid_config)
                    # Like telling the conveyor belt foreman the smoke thickness settings just changed.
                    self.ring_buffer.fluid_config = self.model.fluid_config
                    # Like updating the scene controller's backup copy of the HVAC schedule.
                    self.level_streamer._fluid_config = self.model.fluid_config
                # Like stapling the approved or rejected stamp onto the results clipboard.
                results["fluid"] = {"ok": ok, "reason": reason}
            # Like checking if the envelope is marked "LIGHTING" and contains a dimmer scene.
            elif key == "render" and isinstance(value, dict):
                # Like opening the current Lutron scene so we know the baseline dimmer levels.
                rc = self.model.render_config
                # Like writing a new lighting schedule that only moves the dimmers mentioned in the change order.
                new_rc = RenderConfig(
                    # Like reading the bloom dimmer level, or leaving it where it is.
                    bloom_intensity=value.get("bloom_intensity", rc.bloom_intensity),
                    # Like reading the bloom iteration count, or keeping the old accent-light loop count.
                    bloom_iterations=value.get("bloom_iterations", rc.bloom_iterations),
                    # Like reading the sunrays weight, or keeping the old skylight brightness.
                    sunrays_weight=value.get("sunrays_weight", rc.sunrays_weight),
                    # Like reading the dither strength, or keeping the old textured-roller pressure.
                    dither_strength=value.get("dither_strength", rc.dither_strength),
                    # Like reading the color-temperature dial, or keeping the old daylight-white setting.
                    color_temperature=value.get("color_temperature", rc.color_temperature),
                    # Like reading the master exposure dimmer, or leaving it at unity.
                    exposure=value.get("exposure", rc.exposure),
                    # Like reading the gamma curve knob, or keeping the old 2.2 response shape.
                    gamma=value.get("gamma", rc.gamma),
                )
                # Like handing the new lighting schedule to the electrical plan reviewer.
                ok, reason = self.config_breaker.apply_render_config(new_rc)
                # If the reviewer stamps APPROVED, we reload the surge protector rack with the new scene.
                if ok:
                    # Like swapping the old Lutron processor memory card for the new scene.
                    self.post_process = PostProcessPipeline(self.model.render_config)
                # Like writing the reviewer's decision onto the clipboard.
                results["render"] = {"ok": ok, "reason": reason}
            # Like checking if the envelope is marked "CODE COMPLIANCE" and contains new ampacity tables.
            elif key == "ace_constraints" and isinstance(value, dict):
                # Like opening the current NEC table posted on the panel door.
                ac = self.model.ace_constraints
                # Like drafting a revised code table that only changes the lines the engineer marked.
                new_ac = AceStep15Constraint(
                    # Like reading the new syllabic-density ceiling, or keeping the old amp rating.
                    max_syllabic_density=value.get("max_syllabic_density", ac.max_syllabic_density),
                    # Like reading the new silence-to-sound floor, or keeping the old clearance zone.
                    min_negative_space_ratio=value.get("min_negative_space_ratio", ac.min_negative_space_ratio),
                    # Like reading the new frequency-gap requirement, or keeping the old conduit spacing.
                    frequency_mask_budget_hz=value.get("frequency_mask_budget_hz", ac.frequency_mask_budget_hz),
                    # Like reading the new quantization grid, or keeping the old rigid-conduit spacing.
                    tempo_quantize_grid=value.get("tempo_quantize_grid", ac.tempo_quantize_grid),
                    # Like reading the new keyed-switch position, or keeping the old lock state.
                    lock_state=LockState[value.get("lock_state", ac.lock_state.value)] if "lock_state" in value else ac.lock_state,
                    # Like reading the new grammar preset name, or keeping the old ambient_electronic label.
                    grammar_preset=value.get("grammar_preset", ac.grammar_preset),
                )
                # Like handing the revised code table to the plan reviewer for approval.
                ok, reason = self.config_breaker.apply_ace_constraints(new_ac)
                # Like stapling the decision onto the clipboard.
                results["ace_constraints"] = {"ok": ok, "reason": reason}
            # Like checking if the envelope is just a mood scene recall button press.
            elif key == "mood":
                # Like translating the button label string into the actual Lutron keypad enum.
                mood = MoodPreset(value) if isinstance(value, str) else value
                # Like forwarding the button press to the access-control desk.
                ok, reason = self.config_breaker.set_mood(mood)
                # If the keypad accepted the button, we reload the lighting designer's gel colors.
                if ok:
                    # Like swapping every PAR can gel to match the new scene.
                    self.color_mapper.apply_mood_preset(mood)
                # Like writing the keypad acknowledgment onto the clipboard.
                results["mood"] = {"ok": ok, "reason": reason}
            # Like finding an envelope with no return address and filing it in the trash.
            else:
                # Like stamping the mystery envelope UNKNOWN and pinning it to the bulletin board.
                results[key] = {"ok": False, "reason": f"Unknown config key: {key}"}
        # Like handing the fully annotated clipboard back to the general contractor.
        return results

    # -------------------------------------------------------------------------
    # SCENE MANAGEMENT — Save and recall lighting scenes
    # -------------------------------------------------------------------------

    def save_scene(self, name: str) -> None:
        # Like pressing the "Save Scene" button on the Lutron HomeWorks touchscreen.
        self.state.save_scene(name)

    def load_scene(self, name: str) -> None:
        # Like pressing the "Evening" or "Cooking" recall button on the Lutron keypad.
        self.state.load_scene(name)
        # Like swapping the old VFD programming card for a new one that matches the recalled scene.
        self.physics = NavierStokesSolver(self.model.fluid_config)
        # Like reloading the surge protector rack with the dimmer scene that was just recalled.
        self.post_process = PostProcessPipeline(self.model.render_config)
        # Like swapping every PAR can gel to match the recalled mood.
        self.color_mapper.apply_mood_preset(self.model.mood)
        # Like telling the conveyor belt foreman the smoke thickness and monitor list may have changed.
        self.ring_buffer.fluid_config = self.model.fluid_config
        self.ring_buffer.viewports = self.model.viewports
        # Like updating the scene controller's backup copy of the HVAC schedule.
        self.level_streamer._fluid_config = self.model.fluid_config

    # -------------------------------------------------------------------------
    # PERFORMANCE — Read every meter in the building
    # -------------------------------------------------------------------------

    def get_performance_report(self) -> Dict[str, Any]:
        # Like printing the BACnet trend log for the last two hours of HVAC cycles.
        report = self.perf.report()
        # Like creating a blank clipboard for the thermal-camera readings from each electrical room.
        gpu_profiles: Dict[str, Any] = {}
        # Like walking down the hallway and pointing the thermal camera at each breaker panel.
        for i in range(self.hw_profiler.gpu_count):
            # Like taking a snapshot of panel temperature, utilization, and conduit fill.
            gpu_profiles[f"gpu_{i}"] = self.hw_profiler.profile_gpu(i)
        # Like stapling the thermal-camera packet to the back of the BACnet report.
        report["gpu_profiles"] = gpu_profiles
        # Like writing the current job-ticket number on the report so accounting knows where we are.
        report["frame_index"] = self._frame_index
        # Like noting the current plotter resolution setting on the report header.
        report["quality"] = self.model.fluid_config.grid_resolution.name
        # Like noting which Lutron keypad button is active so the client knows the scene name.
        report["mood"] = self.model.mood.value
        # Like noting the position of the keyed switch on the main panel.
        report["lock_state"] = self.model.lock_state.value
        # Like handing the completed report to the facilities manager.
        return report

    # -------------------------------------------------------------------------
    # SAFETY — Reset the main breaker after a trip
    # -------------------------------------------------------------------------

    def reset_breaker(self) -> None:
        # Like flipping the main breaker handle back to ON after the overload has cleared.
        self.breaker._reset()
        # Like turning the keyed switch back to FREE so tenants can use appliances again.
        self.model.lock_state = LockState.FREE
        # Like reloading the default Lutron scene because the emergency is over.
        new_rc = RenderConfig()
        # Like forwarding the default scene to the plan reviewer so it gets stamped.
        ok, _ = self.config_breaker.apply_render_config(new_rc)
        # If the reviewer approves, we swap the surge protector rack memory card.
        if ok:
            # Like installing the factory-default lighting schedule.
            self.post_process = PostProcessPipeline(self.model.render_config)
        # Like walking past every monitor on the video wall and flipping the power switch back ON.
        for vp in self.model.viewports:
            # Like sending a work order to the AV technician to energize every monitor.
            self.config_breaker.enable_viewport(vp.slot, True)

    # -------------------------------------------------------------------------
    # INTERNAL LOOP — The PLC scan cycle
    # -------------------------------------------------------------------------

    def _run_loop(self) -> None:
        # Like calculating how long one scan cycle should take to hit 60 Hz — just like a VFD holding a pump at exactly 60 Hz.
        dt = 1.0 / self.cfg.target_fps

        # Like the building automation clock that keeps ticking until the facilities manager hits STOP.
        while self._running:
            # Like reading the utility clock to see exactly when this scan cycle began.
            cycle_start = time.perf_counter()
            # Like the thermostat marking the start of a new HVAC cycle on its data tape.
            self.perf.begin_frame()

            # ---- INPUT STAGE ----
            # Like the security guard checking motion sensors and badge readers before doing anything else.
            with self._lock:
                # Like copying the current microphone signal onto a clipboard so the loop can use it safely.
                frame = self._last_audio_frame
            # Like gathering every active input — human touch and audio peaks — into one unified splat list.
            splats = self.input_handler.poll(frame)

            # ---- APPLY NEGATIVE SPACE MASK ----
            # Like calling the utility locator before digging to make sure we don't hit existing gas lines.
            masked_splats = self.physics.apply_negative_space_mask(splats, self.model.negative_space_map)

            # ---- EVALUATE MAIN BREAKER ----
            # Like reading the grid resolution off the title block to know how many cells are in the simulation.
            grid_cells = int(self.model.fluid_config.grid_resolution)
            # Like calculating how many splats per cell we are trying to inject — the electrical load on the panel.
            syllabic_density = len(masked_splats) / (grid_cells * 0.01)
            # Like checking the amp meter on the main panel to see if we need to shed load or if we can re-energize.
            self.breaker.evaluate(self.model, syllabic_density)

            # If the breaker panel is in lockdown or override, we thin out the splats so the system survives.
            if self.model.lock_state != LockState.FREE:
                # Like skipping every other appliance during a demand-response event so the grid doesn't collapse.
                masked_splats = masked_splats[::max(1, int(syllabic_density / 2))]

            # ---- PHYSICS STAGE ----
            # Like one revolution of the chiller's compressor: refrigerant enters, gets squeezed, and exits hotter.
            self.physics.step(masked_splats, dt)

            # ---- COLOR MAPPING ----
            # If the DJ is actually playing music, we translate the spectrum into lighting colors.
            if frame is not None:
                # Like the lighting director programming a moving-head spot to change color based on which instrument is soloing.
                channel_colors = self.color_mapper.map_frame(frame)
                # Like updating the patch bay so the audio spectrum analyzer now routes to the new color palette.
                self.input_handler.audio_bridge.channel_map = channel_colors

            # ---- RENDER VIEWPORTS ----
            # Like the video wall controller routing camera feeds to each monitor in the security NOC.
            for vp in self.viewport_manager.get_enabled():
                # Like looking up the display output circuit for this monitor in the breaker panel directory.
                fbo = self.gpu.get_viewport_fbo(vp.slot, "display")
                # Like putting a sticky note on the junction box that says "WORK IN PROGRESS — fresh render needed."
                fbo.dirty = True

            # ---- POST-PROCESS ----
            # Like pulling the raw dye tank out of the pump station and running it through the surge protector rack.
            density = self.physics.field.density
            # Like routing the image signal through bloom, sunrays, tone-map, and dither in series.
            processed = self.post_process.process(density, self.model.render_config)

            # ---- STREAM TO RING BUFFER ----
            # Like dropping the finished electrical panel onto the conveyor belt so the delivery truck can haul it away.
            self._last_frame_payload = {
                # Like writing the job-ticket number on the panel so the dispatcher knows the sequence.
                "frame_index": self._frame_index,
                # Like strapping the processed dye field onto the pallet so it doesn't shift in transit.
                "density": processed,
                # Like stamping the shipping label with today's date and time.
                "timestamp": time.time(),
            }
            # Like telling the conveyor belt foreman the smoke thickness settings may have changed this frame.
            self.ring_buffer.fluid_config = self.model.fluid_config
            # Like telling the foreman the monitor list may have changed this frame.
            self.ring_buffer.viewports = self.model.viewports
            # Like telling the scene controller to pre-dim the lights for the next second so the renderer never waits.
            self.level_streamer.prefetch(seconds_ahead=1.0)

            # ---- METRICS ----
            # Like the thermostat writing one row to its circular data tape before moving to the next cycle.
            self.perf.end_frame(
                # Like stamping the job-ticket number on the meter reading.
                frame_index=self._frame_index,
                # Like noting how many paint blobs the sprayer fired this cycle.
                splat_count=len(masked_splats),
                # Like noting whether the plotter is in draft or presentation mode.
                quality_level=self.model.fluid_config.grid_resolution.name,
            )
            # Like advancing the job-ticket printer by one so the next frame gets the next number.
            self._frame_index += 1

            # ---- FRAME PACING ----
            # Like checking the stopwatch to see how long this HVAC cycle actually ran.
            elapsed = time.perf_counter() - cycle_start
            # Like calculating exactly how many milliseconds are left before the next 60 Hz cycle must start.
            sleep_time = max(0, dt - elapsed)
            # If we finished early, we take a micro-nap so the scan cycle stays locked to 60 Hz.
            if sleep_time > 0:
                # Like the VFD holding the pump at exactly 60 Hz by idling for the remaining milliseconds.
                time.sleep(sleep_time)

    def _on_adaptation(self, key: str, delta: int) -> None:
        # Like the thermostat calling the building engineer and saying "room 3 needs more cooling."
        if key != "quality_delta":
            # Like the engineer saying "I only handle temperature complaints, not plumbing."
            return
        # Like pulling the list of available cooling stages off the wall chart.
        qualities = [SimulationQuality.LOW, SimulationQuality.MEDIUM,
                     SimulationQuality.HIGH, SimulationQuality.ULTRA]
        # Like reading the current stage label on the chiller control panel.
        current = self.model.fluid_config.grid_resolution
        # Like finding the index of the current stage in the wall chart list.
        idx = qualities.index(current) if current in qualities else 2
        # Like adding the thermostat's recommendation (up one or down one) to the current stage index.
        new_idx = max(0, min(len(qualities) - 1, idx + delta))
        # Like looking up the new stage name from the wall chart.
        new_quality = qualities[new_idx]
        # If the thermostat actually wants a different stage, we start the changeover sequence.
        if new_quality != current:
            # Like drafting a new VAV schedule that only changes the grid resolution.
            new_fc = replace(self.model.fluid_config, grid_resolution=new_quality)
            # Like handing the new schedule to the plan reviewer for approval.
            ok, _ = self.config_breaker.apply_fluid_config(new_fc)
            # If the reviewer stamps APPROVED, we re-commission the pump station.
            if ok:
                # Like swapping the VFD programming card for the new resolution.
                self.physics = NavierStokesSolver(self.model.fluid_config)
                # Like logging the new stage to the home-automation hub memory.
                self.state.set("quality", new_quality.name)
                # Like telling the conveyor belt foreman the smoke thickness just changed.
                self.ring_buffer.fluid_config = self.model.fluid_config
                # Like updating the scene controller's backup copy of the HVAC schedule.
                self.level_streamer._fluid_config = self.model.fluid_config
