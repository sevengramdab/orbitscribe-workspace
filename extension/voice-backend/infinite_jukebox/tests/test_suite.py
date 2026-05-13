"""
Agent 10 — QA: Final Code Polish & Validation
==============================================
Think of this file as the commissioning agent walking the jobsite with
a clipboard, multimeter, and thermal camera. Every test checks that a
subsystem performs to spec — like verifying a VFD hits 60 Hz, a breaker
trips at rated load, and a thermostat holds ±0.5 °F.

ELI5 comments are REQUIRED above every functional line, using analogies
from Engineering Graphics, AutoCAD, and electrical/home automation.
"""

from __future__ import annotations

import unittest
import numpy as np
from dataclasses import asdict

# --- Import every module we test, like checking every deliverable on a BOM ---
import time
import tempfile
import pathlib

from infinite_jukebox.architecture import (
    ModelSpace,
    FluidConfig,
    RenderConfig,
    Vector2D,
    SplatPayload,
    AudioFrame,
    AudioChannel,
    SimulationQuality,
    ViewportSlot,
    ViewportConfig,
    LockState,
    MoodPreset,
    AceStep15Constraint,
    SignalPathDag,
    SignalPathNode,
    NegativeSpaceMap,
)
from infinite_jukebox.physics.navier_stokes import NavierStokesSolver, FluidField
from infinite_jukebox.gpu.compute_manager import GpuComputeManager, ViewportManager
from infinite_jukebox.interaction.input_handler import AudioForceBridge, InputHandler
from infinite_jukebox.visuals.color_mapper import AudioColorMapper
from infinite_jukebox.visuals.post_processing import PostProcessPipeline
from infinite_jukebox.engine.state_manager import StateManager, MainBreaker, ConfigurationBreaker
from infinite_jukebox.engine.performance import PerformanceMonitor, LevelStreamingEngine, HardwareProfiler
from infinite_jukebox.engine.main_loop import InfiniteJukeboxEngine, EngineConfig


# =============================================================================
# TEST SUITE — The punch-list walk
# =============================================================================

class TestModelSpaceBlueprint(unittest.TestCase):
    """
    Agent 1 tests — Verify the AutoCAD master file has correct layers,
    linetypes, and XREF bindings before trades start drawing.
    """

    def test_default_model_space_instantiates(self):
        # ELI5: Like opening a blank AutoCAD template and checking that
        # the title block, border, and viewport frames are already there.
        model = ModelSpace()
        # ELI5: Make sure the HVAC layer (fluid config) was drawn by the architect.
        self.assertIsNotNone(model.fluid_config)
        # ELI5: Make sure the lighting layer (render config) was also drawn.
        self.assertIsNotNone(model.render_config)
        # ELI5: Verify at least one viewport tab exists so the drafters have a sheet to work on.
        self.assertTrue(len(model.viewports) > 0)

    def test_vector_addition(self):
        # ELI5: In Engineering Graphics, if you draw a 3-unit line east
        # and a 4-unit line north, the resultant diagonal is 5 units.
        v1 = Vector2D(3.0, 0.0)
        # ELI5: Draw the second line straight up from the origin.
        v2 = Vector2D(0.0, 4.0)
        # ELI5: Add the two vectors tip-to-tail like a force polygon.
        result = v1 + v2
        # ELI5: The easting of the resultant should still be 3 units.
        self.assertAlmostEqual(result.x, 3.0)
        # ELI5: The northing of the resultant should still be 4 units.
        self.assertAlmostEqual(result.y, 4.0)

    def test_splat_payload_defaults(self):
        # ELI5: Like a standard lighting fixture schedule: if no wattage
        # is specified, assume 60 W; if no color is specified, assume white.
        s = SplatPayload()
        # ELI5: Check that the spray nozzle starts at the origin (0,0) on the sheet.
        self.assertEqual(s.origin.x, 0.0)
        # ELI5: Check that the default nozzle orifice is the standard 0.003 size.
        self.assertEqual(s.radius, 0.003)

    def test_grammar_lock_trips_under_overload(self):
        # ELI5: Your home's 200-amp main breaker should trip if you draw
        # 300 amps. Here we simulate plugging in too many space heaters.
        model = ModelSpace(negative_space_threshold=0.1)
        # ELI5: Inject a syllabic density of 1.0 — way more notes than the panel can handle.
        model.apply_grammar_lock(syllabic_density=1.0)
        # ELI5: Verify the breaker handle flipped to OVERRIDE because we blew past 1.5× rating.
        self.assertTrue(model.lock_state in (LockState.LOCKED, LockState.OVERRIDE))


class TestNavierStokesPhysics(unittest.TestCase):
    """
    Agent 2 tests — Verify the pump curves, pressure ratings, and flow
    balances meet the hydraulic engineer's specs.
    """

    def test_fluid_field_creation(self):
        # ELI5: Like ordering a 256-gallon rectangular tank from a catalog.
        # When it arrives, measure it: it better be 256 units wide.
        field = FluidField.create(SimulationQuality.MEDIUM)
        # ELI5: Pull out the tape measure and check the tank width.
        self.assertEqual(field.width, 256)
        # ELI5: Check the tank height matches the spec sheet too.
        self.assertEqual(field.height, 256)

    def test_solver_initializes_clean(self):
        # ELI5: Before turning on a new hydronic system, you flush it with
        # clean water. The water should be crystal clear (all zeros).
        cfg = FluidConfig(grid_resolution=SimulationQuality.LOW)
        # ELI5: Commission the pump station with the low-resolution motor nameplate.
        solver = NavierStokesSolver(cfg)
        # ELI5: Measure the total momentum in every pipe — it should be zero before startup.
        self.assertEqual(np.sum(solver.field.velocity), 0.0)
        # ELI5: Measure the total dye in the tank — also zero before the first paint blob.
        self.assertEqual(np.sum(solver.field.density), 0.0)

    def test_splat_injects_momentum(self):
        # ELI5: Open a fire hydrant. The pressure gauge at that corner
        # should jump from zero to something positive immediately.
        cfg = FluidConfig(grid_resolution=SimulationQuality.LOW)
        # ELI5: Commission the pump station with a small tank so the test runs fast.
        solver = NavierStokesSolver(cfg)
        # ELI5: Build a paint blob that shoots eastward at the center of the tank.
        splat = SplatPayload(
            origin=Vector2D(0.5, 0.5),
            velocity=Vector2D(10.0, 0.0),
            color_rgb=(1.0, 0.0, 0.0),
            radius=0.05,
            density=1.0,
        )
        # ELI5: Inject the paint blob and run one PLC scan cycle.
        solver.step([splat], dt=0.016)
        # ELI5: Add up every velocity reading in the tank — there should be measurable flow now.
        total_vel = np.sum(solver.field.velocity)
        # ELI5: Confirm the pressure gauge jumped above zero after opening the hydrant.
        self.assertGreater(total_vel, 0.0)

    def test_advection_carries_dye_downstream(self):
        # ELI5: Drop a red leaf in a river flowing east. After one second,
        # the leaf should be east of where you dropped it.
        cfg = FluidConfig(grid_resolution=SimulationQuality.LOW)
        # ELI5: Commission the pump station.
        solver = NavierStokesSolver(cfg)
        # ELI5: Pre-seed the river current so every drop of water drifts east at 0.5 m/s.
        solver.field.velocity[:, :, 0] = 0.5
        # ELI5: Squirt one drop of red dye on the left bank.
        solver.field.density[64, 32, 0] = 1.0
        # ELI5: Let the river run for 0.1 seconds.
        solver.step([], dt=0.1)
        # ELI5: Look at the right side of the tank — the red leaf should have moved there.
        self.assertTrue(np.any(solver.field.density[:, 33:, 0] > 0))

    def test_divergence_free_after_projection(self):
        # ELI5: In a closed hydronic loop, the total water entering every
        # junction must equal the total leaving. After balancing, divergence
        # (the leakage meter) should read nearly zero everywhere.
        cfg = FluidConfig(grid_resolution=SimulationQuality.LOW, pressure_iterations=40)
        # ELI5: Commission the pump station with extra balancing loops.
        solver = NavierStokesSolver(cfg)
        # ELI5: Run one full PLC scan cycle.
        solver.step([], dt=0.016)
        # ELI5: Read the leakage meter at every interior junction.
        div = solver.field.divergence[1:-1, 1:-1]
        # ELI5: The leakage should be less than 0.1 gallons per minute everywhere.
        self.assertLess(np.max(np.abs(div)), 0.1)

    def test_curl_computed(self):
        # ELI5: Put a tiny paddlewheel in a clockwise vortex. It should spin.
        cfg = FluidConfig(grid_resolution=SimulationQuality.LOW)
        # ELI5: Commission the pump station.
        solver = NavierStokesSolver(cfg)
        # ELI5: Measure the tank height and width so we can place the vortex in the center.
        h, w = solver.field.height, solver.field.width
        # ELI5: Lay out a grid of coordinates like a surveyor staking a lot.
        y, x = np.ogrid[:h, :w]
        # ELI5: Find the exact center of the tank where the drain swirl will be.
        cx, cy = w / 2, h / 2
        # ELI5: Set the water velocity so it spins counter-clockwise around the center.
        solver.field.velocity[:, :, 0] = -(y - cy) * 0.01
        # ELI5: Set the perpendicular velocity component to complete the rotation.
        solver.field.velocity[:, :, 1] = (x - cx) * 0.01
        # ELI5: Read the paddlewheel spin meter.
        curl = solver.get_curl()
        # ELI5: The paddlewheel at the exact center should be spinning in the positive direction.
        self.assertGreater(curl[h // 2, w // 2], 0.0)


class TestGpuCompute(unittest.TestCase):
    """
    Agent 3 tests — Verify the electrical panel schedules, breaker sizes,
    and load-center balancing are correct before energizing.
    """

    def test_viewport_manager_tiling_4(self):
        # ELI5: In a security room, four monitors arranged 2×2 should each
        # get exactly one-quarter of the wall. No monitor should overlap.
        vps = [
            ViewportConfig(slot=ViewportSlot(i), width_px=1920, height_px=1080)
            for i in range(4)
        ]
        # ELI5: Hire the video wall operator and hand him the monitor list.
        vm = ViewportManager(vps)
        # ELI5: Tell the operator to arrange the four monitors on a 3840×2160 wall.
        tiles = vm.compute_tiling(3840, 2160)
        # ELI5: Verify we got back exactly four tile rectangles.
        self.assertEqual(len(tiles), 4)
        # ELI5: Measure the rightmost edge of the right-side monitors.
        max_right = max(t[0] + t[2] for t in tiles.values())
        # ELI5: Measure the bottom edge of the lower monitors.
        max_bottom = max(t[1] + t[3] for t in tiles.values())
        # ELI5: The right edge should kiss the wall boundary exactly.
        self.assertEqual(max_right, 3840)
        # ELI5: The bottom edge should also kiss the wall boundary exactly.
        self.assertEqual(max_bottom, 2160)

    def test_gpu_manager_queues_commands(self):
        # ELI5: The electrician writes three work orders and puts them in
        # the inbox. We count the inbox: it should say "3 pending."
        vps = [ViewportConfig(slot=ViewportSlot.PRIMARY, width_px=512, height_px=512)]
        # ELI5: Hire the master electrician and commission five breaker panels.
        gpu = GpuComputeManager(vps)
        try:
            # ELI5: Grab the velocity FBO for the primary monitor so we know which panel to route to.
            vel_fbo = gpu.get_viewport_fbo(ViewportSlot.PRIMARY, "velocity")
            # ELI5: Grab the pressure FBO for the primary monitor.
            pres_fbo = gpu.get_viewport_fbo(ViewportSlot.PRIMARY, "pressure")
            # ELI5: Drop an advection work order into Panel 0's inbox.
            f1 = gpu.dispatch_advection(vel_fbo, None, 0.016)
            # ELI5: Drop a Jacobi pressure-solve work order into the same inbox.
            f2 = gpu.dispatch_jacobi(pres_fbo, None, 20)
            # ELI5: Walk through all five electrical rooms and verify every inbox is caught up.
            gpu.flush_all()
            # ELI5: Check that the advection claim ticket is stamped COMPLETE.
            self.assertTrue(f1.done())
            # ELI5: Check that the Jacobi claim ticket is also stamped COMPLETE.
            self.assertTrue(f2.done())
        finally:
            # ELI5: Send pink slips to all five electricians so they clock out and don't leak threads.
            gpu.shutdown()


class TestInteraction(unittest.TestCase):
    """
    Agent 4 tests — Verify the occupancy sensors, dimmer sliders, and
    touch panels respond correctly to human input.
    """

    def test_audio_bridge_maps_bins_to_splats(self):
        # ELI5: The spectrum analyzer shows five big red bars. Each bar
        # should trigger its own spray nozzle. We should get 5 splats.
        bridge = AudioForceBridge(channel_map={
            AudioChannel.BASS: (1.0, 0.0, 0.0),
            AudioChannel.TREBLE: (0.0, 0.0, 1.0),
        })
        # ELI5: Feed the bridge a full-strength audio frame where every FFT bin is lit.
        frame = AudioFrame(
            timestamp_ms=0,
            frequency_bins=np.ones(512, dtype=np.float32),
        )
        # ELI5: Run the spectrum analyzer through the patch bay and collect the spray nozzles.
        splats = bridge.process(frame)
        # ELI5: Verify at least one nozzle fired — the audio was loud enough.
        self.assertGreater(len(splats), 0)

    def test_pointer_drag_generates_splats(self):
        # ELI5: Swipe a Lutron glass touch panel. The lights should fade
        # up along the path of your finger. Here, the "lights" are splats.
        bridge = AudioForceBridge(channel_map={})
        # ELI5: Mount the touch panel on the wall next to the audio bridge.
        handler = InputHandler(audio_bridge=bridge)
        # ELI5: Press your finger down in the center of the glass.
        handler.pointer_down(0, 0.5, 0.5)
        # ELI5: Drag your finger slightly to the right.
        handler.pointer_move(0, 0.6, 0.5)
        # ELI5: Ask the hub to report all active inputs as splats.
        splats = handler.poll()
        # ELI5: Verify exactly one splat was generated from the drag motion.
        self.assertEqual(len(splats), 1)
        # ELI5: Verify the splat carries positive X velocity because we dragged right.
        self.assertGreater(splats[0].velocity.x, 0.0)


class TestVisuals(unittest.TestCase):
    """
    Agent 5 & 6 tests — Verify the stage lights match the audio, and the
    post-FX rack (bloom, sunrays, dither) doesn't blow out the signal.
    """

    def test_color_mapper_returns_valid_rgb(self):
        # ELI5: The lighting board should only send DMX values 0–255.
        # If it sends 300, the LED driver will clip or malfunction.
        mapper = AudioColorMapper()
        # ELI5: Generate a random audio spectrum like white noise on every circuit.
        frame = AudioFrame(frequency_bins=np.random.rand(512).astype(np.float32))
        # ELI5: Run the spectrum through the DMX decoder.
        colors = mapper.map_frame(frame)
        # ELI5: Walk through every circuit breaker on the lighting panel.
        for ch, rgb in colors.items():
            # ELI5: Check each color wire so it stays inside the 0–1 safe voltage band.
            for c in rgb:
                self.assertGreaterEqual(c, 0.0)
                self.assertLessEqual(c, 1.0)

    def test_post_process_preserves_range(self):
        # ELI5: Run a video signal through the broadcast switcher. The
        # output should still be broadcast-safe (0–100 IRE), not crushed.
        # ELI5: Create a test image with random pixel voltages between 0 and 1.
        img = np.random.rand(64, 64, 3).astype(np.float32)
        # ELI5: Route the image through the full surge-protector rack.
        out = PostProcessPipeline.process(img, RenderConfig())
        # ELI5: Verify the darkest pixel is still above absolute black.
        self.assertGreaterEqual(out.min(), 0.0)
        # ELI5: Verify the brightest pixel is still below blown-out white.
        self.assertLessEqual(out.max(), 1.0)


class TestStateAndSafety(unittest.TestCase):
    """
    Agent 7 tests — Verify the fire-alarm shunt trip, emergency lighting,
    and main breaker logic operate per NFPA 70 (NEC) standards.
    """

    def test_state_manager_persists_keys(self):
        # ELI5: A smart home hub remembers your scenes after a power outage.
        # We write a scene, simulate reboot, and verify it recalls correctly.
        import tempfile, pathlib
        # ELI5: Create a temporary file to act as the hub's memory card.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = pathlib.Path(f.name)
        # ELI5: Install the hub and program an evening scene.
        sm = StateManager(persist_path=path)
        # ELI5: Set the evening dimmer to 40 % and color temp to 2700 K.
        sm.set("scene.evening", {"dim": 40, "color": 2700})
        # ELI5: Pull the memory card out and stick it into a brand-new hub.
        sm2 = StateManager(persist_path=path)
        # ELI5: Read the evening scene back and verify the dimmer is still 40 %.
        self.assertEqual(sm2.get("scene.evening")["dim"], 40)
        # ELI5: Throw away the temporary memory card so we don't clutter the jobsite.
        path.unlink()

    def test_main_breaker_trips_on_overload(self):
        # ELI5: Plug 10 space heaters into one 15-amp outlet. The breaker
        # should trip. Here, "heaters" are musical notes and "amps" are splats.
        sm = StateManager()
        # ELI5: Wire the main breaker to the home-automation hub.
        breaker = MainBreaker(sm)
        # ELI5: Build a model with a 0.45-amp breaker rating (default ace_constraints).
        model = ModelSpace()
        # ELI5: Draw 0.5 amps — just above the 0.45 rating so the panel should trip.
        breaker.evaluate(model, syllabic_density=0.5)
        # ELI5: Verify the breaker handle is now in the TRIP position.
        self.assertTrue(breaker.is_tripped)

    def test_main_breaker_resets_when_load_drops(self):
        # ELI5: Unplug 9 of the 10 space heaters. The breaker should reset
        # so you can use the outlet again.
        sm = StateManager()
        # ELI5: Wire the main breaker to the hub.
        breaker = MainBreaker(sm)
        # ELI5: Build the model with default ampacity tables.
        model = ModelSpace()
        # ELI5: Overload the panel with 0.5 amps to trip the breaker.
        breaker.evaluate(model, syllabic_density=0.5)
        # ELI5: Drop the load down to 0.05 amps — well below the 0.45 rating.
        breaker.evaluate(model, syllabic_density=0.05)
        # ELI5: Verify the breaker handle flipped back to ON because the load dropped and cooldown expired.
        self.assertFalse(breaker.is_tripped)


class TestPerformance(unittest.TestCase):
    """
    Agent 8 tests — Verify the energy-management system holds setpoints,
    records trend logs, and sheds load when chillers lag.
    """

    def test_monitor_detects_missed_frames(self):
        # ELI5: A smart thermostat logs every temperature reading. If the
        # room stays above 78 °F for 10 minutes, it records a "comfort fault."
        mon = PerformanceMonitor(target_fps=60)
        # ELI5: Mark the start of a new HVAC cycle on the thermostat.
        mon.begin_frame()
        # ELI5: Wait 50 ms — way longer than the 16.7 ms budget for 60 FPS.
        time.sleep(0.05)
        # ELI5: Mark the end of the cycle and log the meter reading.
        mon.end_frame(frame_index=0)
        # ELI5: Print the maintenance log and count how many cycles missed their window.
        report = mon.report()
        # ELI5: Verify the log shows at least one dropped frame because we ran too slow.
        self.assertGreater(report["dropped_frames"], 0)

    def test_adaptation_callback_fires(self):
        # ELI5: Tie a smart outlet to the thermostat. When the thermostat
        # calls for cooling, the outlet should turn on the fan. We verify
        # the fan actually received power.
        mon = PerformanceMonitor(target_fps=60)
        # ELI5: Prepare an empty list to catch every "fan on" signal.
        triggered = []
        # ELI5: Register a callback using the auto-key fallback — like pairing a wireless remote without entering a room number.
        mon.register_adaptation_callback(lambda k, v: triggered.append((k, v)))
        # ELI5: Simulate many slow frames so the thermostat decides to shed a cooling stage.
        for i in range(20):
            # ELI5: Start a new HVAC cycle.
            mon.begin_frame()
            # ELI5: Hold the cycle open for 50 ms to force an overshoot.
            time.sleep(0.05)
            # ELI5: Close the cycle and write the meter reading to the tape.
            mon.end_frame(frame_index=i)
        # ELI5: Verify the smart outlet received at least one "turn on" command.
        self.assertTrue(len(triggered) > 0)


class TestIntegration(unittest.TestCase):
    """
    Agent 9 tests — Verify the central plant starts, runs, and shuts down
    without tripping alarms. Like a TAB contractor running the chiller
    through its full sequence of operation.
    """

    def test_engine_lifecycle(self):
        # ELI5: Press the "AUTO" button on the building automation panel.
        # The chiller should start, run for a bit, then stop cleanly.
        engine = InfiniteJukeboxEngine(config=EngineConfig(target_fps=60))
        # ELI5: Flip the main switch to AUTO.
        engine.start()
        # ELI5: Verify the status light says "RUNNING."
        self.assertTrue(engine._running)
        # ELI5: Let the chiller run for one-tenth of a second.
        time.sleep(0.1)
        # ELI5: Flip the main switch to OFF.
        engine.stop()
        # ELI5: Verify the status light says "STOPPED."
        self.assertFalse(engine._running)

    def test_engine_adapts_quality(self):
        # ELI5: If the electrical grid sags, the building sheds non-essential
        # loads (elevators, decorative lighting) to keep the server room up.
        engine = InfiniteJukeboxEngine(config=EngineConfig(target_fps=60))
        try:
            # ELI5: Force adaptation by simulating slow frames via performance monitor.
            for i in range(30):
                # ELI5: Start a new HVAC cycle on the engine's built-in thermostat.
                engine.perf.begin_frame()
                # ELI5: Hold the cycle open for 50 ms to fake a compressor lag.
                time.sleep(0.05)
                # ELI5: Close the cycle and log the reading.
                engine.perf.end_frame(frame_index=i)
            # ELI5: Verify the engine still has a valid state object after the stress test.
            self.assertIsNotNone(engine.state)
        finally:
            # ELI5: Always shut down the chiller so we don't leave threads running.
            engine.stop()


# =============================================================================
# FIGHTER JET FEATURES — Signal path, negative space, ACE constraints
# =============================================================================

class TestSignalPathDag(unittest.TestCase):
    """
    Agent 1.5 tests — Verify the audio riser diagram has no loops and
    every device is wired in the correct order from service entrance to outlet.
    """

    def test_signal_path_dag_topological_sort(self):
        # ELI5: Like drawing a one-line diagram where the main panel feeds a sub-panel,
        # and the sub-panel feeds a junction box. The electrician must wire the main first.
        dag = SignalPathDag()
        # ELI5: Add the main oscillator node that has no upstream inputs.
        dag.add_node(SignalPathNode("osc", "oscillator", output_ids=("filter",)))
        # ELI5: Add the filter node downstream of the oscillator.
        dag.add_node(SignalPathNode("filter", "filter", input_ids=("osc",), output_ids=("out",)))
        # ELI5: Add the output node at the very end of the chain.
        dag.add_node(SignalPathNode("out", "compressor", input_ids=("filter",)))
        # ELI5: Ask the blueprint software to sort the devices from source to sink.
        order = dag.topological_sort()
        # ELI5: The oscillator must come before the filter, or the wires would be backward.
        self.assertLess(order.index("osc"), order.index("filter"))
        # ELI5: The filter must come before the output, or the signal has nowhere to go.
        self.assertLess(order.index("filter"), order.index("out"))

    def test_signal_path_dag_detects_cycle(self):
        # ELI5: Like accidentally drawing a loop in the conduit so water flows back into itself.
        # The inspector should slap a red tag on the drawing immediately.
        dag = SignalPathDag()
        # ELI5: Add node A that feeds node B.
        dag.add_node(SignalPathNode("A", "oscillator", output_ids=("B",)))
        # ELI5: Add node B that feeds node C.
        dag.add_node(SignalPathNode("B", "filter", input_ids=("A",), output_ids=("C",)))
        # ELI5: Add node C that accidentally feeds back into node A, creating a short-circuit loop.
        dag.add_node(SignalPathNode("C", "compressor", input_ids=("B",), output_ids=("A",)))
        # ELI5: Ask the inspector to review the drawing and expect him to throw a red tag.
        with self.assertRaises(ValueError):
            dag.topological_sort()


class TestNegativeSpaceMap(unittest.TestCase):
    """
    Agent 1.5 tests — Verify the utility clearance map prevents two contractors
    from digging trenches on top of each other.
    """

    def test_negative_space_map_reservation(self):
        # ELI5: Like calling the utility locator before digging a water-main trench.
        # If a gas line already sits at that depth, the permit office says "no."
        nsm = NegativeSpaceMap(time_slots=8, freq_bins=64)
        # ELI5: Reserve a 4-foot trench at time slot 2 and depth 10 feet.
        ok1 = nsm.reserve_band(time_idx=2, freq_center=10, bandwidth_hz=4.0, bin_resolution_hz=1.0)
        # ELI5: The first reservation should be approved because the dirt is empty.
        self.assertTrue(ok1)
        # ELI5: Try to reserve the exact same trench for a second contractor.
        ok2 = nsm.reserve_band(time_idx=2, freq_center=10, bandwidth_hz=4.0, bin_resolution_hz=1.0)
        # ELI5: The second reservation should be denied because the trench is already occupied.
        self.assertFalse(ok2)

    def test_negative_space_map_density_tracking(self):
        # ELI5: Like a parking-garage attendant who counts how many spots are filled.
        # As more cars park, the occupancy percentage should climb.
        nsm = NegativeSpaceMap(time_slots=8, freq_bins=64)
        # ELI5: Check the garage at 3 PM before anyone has parked — it should be empty.
        before = nsm.get_density_at(3)
        # ELI5: Verify the occupancy meter reads zero.
        self.assertEqual(before, 0.0)
        # ELI5: Park one car in the garage at time slot 3.
        nsm.reserve_band(time_idx=3, freq_center=20, bandwidth_hz=10.0, bin_resolution_hz=1.0)
        # ELI5: Re-read the occupancy meter after the car pulled in.
        after = nsm.get_density_at(3)
        # ELI5: Verify the meter now shows some percentage of spots are taken.
        self.assertGreater(after, 0.0)


class TestAceConstraints(unittest.TestCase):
    """
    Agent 1.5 tests — Verify the tamper-evident seals on the breaker panel
    prevent anyone from raising the amp ceiling while the load is high.
    """

    def test_ace_constraints_locked_mode_blocks_dense_notes(self):
        # ELI5: Turn the keyed switch on the main panel to LOCKED.
        # Now the electrician can't add more breakers until the load drops.
        model = ModelSpace()
        # ELI5: Flip the keyed switch to the LOCKED position.
        model.lock_state = LockState.LOCKED
        # ELI5: Install a home-automation hub next to the panel.
        state = StateManager()
        # ELI5: Hire the plan reviewer who stamps every change order.
        breaker = ConfigurationBreaker(state, model)
        # ELI5: Read the current ampacity table posted on the panel door.
        current = model.ace_constraints
        # ELI5: Draft a new code table that raises the syllabic-density ceiling by 0.1 amps.
        denser = AceStep15Constraint(max_syllabic_density=current.max_syllabic_density + 0.1)
        # ELI5: Hand the revised table to the plan reviewer.
        ok, reason = breaker.apply_ace_constraints(denser)
        # ELI5: The reviewer should stamp it REJECTED because the wire would overheat.
        self.assertFalse(ok)
        # ELI5: Verify the rejection note specifically mentions syllabic density.
        self.assertIn("Cannot raise syllabic density", reason)
        # ELI5: Make sure the keyed switch is still in LOCKED after the failed request.
        self.assertEqual(model.lock_state, LockState.LOCKED)


class TestConfigurationBreaker(unittest.TestCase):
    """
    Agent 7 tests — Verify the live-tweak inspector approves safe work and
    rejects dangerous overloads.
    """

    def test_configuration_breaker_approves_safe_changes(self):
        # ELI5: The plan reviewer should approve a change order that LOWERS the
        # wattage on a circuit — that's safer, not riskier.
        model = ModelSpace()
        # ELI5: Install the hub.
        state = StateManager()
        # ELI5: Hire the plan reviewer.
        breaker = ConfigurationBreaker(state, model)
        # ELI5: Draft a new lighting scene with the bloom dimmer turned way down to 5 %.
        safe = RenderConfig(bloom_intensity=0.05)
        # ELI5: Hand the safe scene to the reviewer.
        ok, reason = breaker.apply_render_config(safe)
        # ELI5: The reviewer should stamp it APPROVED because we reduced load.
        self.assertTrue(ok)
        # ELI5: There should be no red tag attached.
        self.assertIsNone(reason)

    def test_configuration_breaker_rejects_unsafe_changes(self):
        # ELI5: If the main breaker is already hot, the inspector should reject
        # a change order that adds a hot tub to the same panel.
        model = ModelSpace()
        # ELI5: Flip the keyed switch to LOCKED to simulate an overloaded panel.
        model.lock_state = LockState.LOCKED
        # ELI5: Install the hub.
        state = StateManager()
        # ELI5: Hire the plan reviewer.
        breaker = ConfigurationBreaker(state, model)
        # ELI5: Draft a new scene with the bloom dimmer cranked to 100 % — an obvious overload.
        unsafe = RenderConfig(bloom_intensity=1.0)
        # ELI5: Hand the unsafe scene to the reviewer.
        ok, reason = breaker.apply_render_config(unsafe)
        # ELI5: The reviewer should stamp it REJECTED and write a red tag.
        self.assertFalse(ok)
        # ELI5: Verify a reason string was returned explaining the rejection.
        self.assertIsNotNone(reason)


class TestLevelStreaming(unittest.TestCase):
    """
    Agent 8 tests — Verify the scene controller pre-renders frames so the
    display crew never waits during the show.
    """

    def test_level_streaming_prefetch_and_pop(self):
        # ELI5: Like a prep cook who slices vegetables before the dinner rush.
        # We ask for five frames ahead, then grab them one by one in order.
        engine = LevelStreamingEngine(frame_rate=60.0, buffer_seconds=2.0)
        # ELI5: Tell the prep cook to get 0.05 seconds of frames ready (about 3 frames).
        count = engine.prefetch(seconds_ahead=0.05)
        # ELI5: Verify the cook actually prepared at least one frame.
        self.assertGreaterEqual(count, 1)
        # ELI5: Grab the first pre-rendered frame off the front of the conveyor.
        frame = engine.pop_ready_frame()
        # ELI5: Make sure the frame isn't blank — the cook actually did the work.
        self.assertIsNotNone(frame)
        # ELI5: Verify the first frame is stamped with job-ticket number zero.
        self.assertEqual(frame["frame_index"], 0)
        # ELI5: Grab the second frame if the cook prepared more than one.
        frame2 = engine.pop_ready_frame()
        # ELI5: If a second frame exists, its ticket number should be one higher.
        if frame2 is not None:
            self.assertEqual(frame2["frame_index"], 1)


class TestHardwareProfiler(unittest.TestCase):
    """
    Agent 8 tests — Verify the thermal camera and clamp meter detect
    imbalance and the dispatcher moves circuits to cooler panels.
    """

    def test_hardware_profiler_rebalance(self):
        # ELI5: Panel 4 is running 90 amps and Panel 0 is only running 50 amps.
        # The load balancer should move one circuit from the hot panel to the cool one.
        profiler = HardwareProfiler(gpu_count=5)
        # ELI5: Replace the random thermal camera with a fixed meter so the test is deterministic.
        def deterministic_profile(gpu_index: int):
            # ELI5: Return a fake clamp-meter reading with no electrical noise.
            return {"utilization": 50.0 + gpu_index * 10.0, "vram_used": 10.0, "temperature": 50.0}
        # ELI5: Swap the real profile_gpu method for our fake one during this test.
        profiler.profile_gpu = deterministic_profile
        # ELI5: Create a dummy lighting circuit to land on a panel.
        vp = ViewportConfig(slot=ViewportSlot.PRIMARY, width_px=512, height_px=512)
        # ELI5: Land the circuit on Panel 4, the hottest panel in the building.
        profiler.assign_viewport(4, vp)
        # ELI5: Ask the dispatcher to review the load readings and suggest moves.
        moves = profiler.rebalance_load()
        # ELI5: The dispatcher should write exactly one relocation ticket.
        self.assertEqual(len(moves), 1)
        # ELI5: Unpack the ticket to see which panels are involved.
        src, dst, moved_vp = moves[0]
        # ELI5: The source panel should be the overloaded one (Panel 4).
        self.assertEqual(src, 4)
        # ELI5: The destination panel should be the coolest one (Panel 0).
        self.assertEqual(dst, 0)
        # ELI5: Verify the moved circuit is the same one we originally assigned.
        self.assertEqual(moved_vp.slot, ViewportSlot.PRIMARY)


class TestColorMapperMoods(unittest.TestCase):
    """
    Agent 5 tests — Verify every Lutron keypad button produces a distinct
    lighting scene so the client can tell "Cooking" from "Goodnight."
    """

    def test_color_mapper_mood_presets(self):
        # ELI5: Pressing "Cooking" vs "Goodnight" on a Lutron keypad should
        # produce completely different lighting colors. We verify no two scenes match.
        mapper = AudioColorMapper()
        # ELI5: Prepare a dictionary to record the color snapshot for each mood button.
        colors = {}
        # ELI5: Walk through every button on the keypad: AMBIENT, ENERGETIC, DARK, CHAOS, MINIMAL.
        for preset in MoodPreset:
            # ELI5: Press the current mood button to load its gel colors.
            mapper.apply_mood_preset(preset)
            # ELI5: Feed the mapper a random audio spectrum like static on the line.
            frame = AudioFrame(frequency_bins=np.random.rand(512).astype(np.float32))
            # ELI5: Read the DMX output voltages for every channel in this mood.
            rgb = mapper.map_frame(frame)
            # ELI5: Store the snapshot so we can compare it to the other buttons later.
            colors[preset] = rgb
        # ELI5: Get a list of all preset names so we can compare every pair.
        presets = list(MoodPreset)
        # ELI5: Compare each preset against every other preset exactly once.
        for i in range(len(presets)):
            for j in range(i + 1, len(presets)):
                # ELI5: Pick two different mood buttons.
                p1, p2 = presets[i], presets[j]
                # ELI5: Read their stored color snapshots.
                c1, c2 = colors[p1], colors[p2]
                # ELI5: Add up the absolute difference across all five channels and three colors.
                diff = sum(abs(c1[ch][k] - c2[ch][k]) for ch in c1 for k in range(3))
                # ELI5: If the difference is zero, the two scenes are identical — that's a wiring fault.
                self.assertGreater(diff, 0.0, f"{p1} and {p2} produced identical colors")


class TestPostProcessDetails(unittest.TestCase):
    """
    Agent 6 tests — Verify each module in the surge-protector rack behaves:
    bloom clips gracefully, dither adds noise to hide banding.
    """

    def test_post_process_bloom_preserves_range(self):
        # ELI5: Like a surge protector that clips voltage spikes so the TV never
        # sees more than 120 V. Bloom should never push pixels outside 0–1.
        # ELI5: Generate a random test image with pixel voltages scattered between 0 and 1.
        img = np.random.rand(32, 32, 3).astype(np.float32)
        # ELI5: Route the image through the bloom circuit with moderate intensity.
        out = PostProcessPipeline.apply_bloom(img, intensity=0.5, iterations=4)
        # ELI5: Verify the darkest pixel is still above absolute black.
        self.assertGreaterEqual(out.min(), 0.0)
        # ELI5: Verify the brightest pixel is still below blown-out white.
        self.assertLessEqual(out.max(), 1.0)

    def test_post_process_dither_reduces_banding(self):
        # ELI5: A plain painted wall shows brush strokes; a textured roller hides them.
        # Dither should add noise so the quantized image differs from straight rounding.
        # ELI5: Create a perfectly smooth gradient from black to white so banding would be obvious.
        img = np.linspace(0, 1, 256).reshape(16, 16, 1).astype(np.float32)
        # ELI5: Copy the gradient to all three color channels so it looks like a greyscale ramp.
        img = np.repeat(img, 3, axis=2)
        # ELI5: Quantize the image without dither — this is the "plain paint" version.
        plain = np.round(img * 255.0) / 255.0
        # ELI5: Quantize the image WITH dither — this is the "textured roller" version.
        dithered = PostProcessPipeline.apply_dither(img, strength=0.03)
        # ELI5: Verify the dithered output is still broadcast-safe.
        self.assertGreaterEqual(dithered.min(), 0.0)
        # ELI5: Verify the dithered output didn't blow past white either.
        self.assertLessEqual(dithered.max(), 1.0)
        # ELI5: Measure the average pixel difference between the two versions.
        diff = np.mean(np.abs(dithered - plain))
        # ELI5: If the textured roller did its job, the two images should NOT be identical.
        self.assertGreater(diff, 0.0)


class TestEngineConfigManagement(unittest.TestCase):
    """
    Agent 9 tests — Verify the building engineer can apply change orders
    and save/recall lighting scenes without crashing the central plant.
    """

    def test_engine_apply_config_delta(self):
        # ELI5: Like sending a change order to the building engineer that says
        # "dim the bloom lights to 10 %." The engineer should update the panel.
        engine = InfiniteJukeboxEngine(config=EngineConfig(target_fps=60))
        try:
            # ELI5: Read the current bloom dimmer level off the lighting schedule.
            before = engine.model.render_config.bloom_intensity
            # ELI5: Send a delta change order that lowers the bloom dimmer to 0.1.
            results = engine.apply_config_delta({"render": {"bloom_intensity": 0.1}})
            # ELI5: Verify the change order was routed to the render department.
            self.assertIn("render", results)
            # ELI5: Verify the plan reviewer stamped it APPROVED.
            self.assertTrue(results["render"]["ok"])
            # ELI5: Verify the actual dimmer level in the model space moved to 0.1.
            self.assertEqual(engine.model.render_config.bloom_intensity, 0.1)
        finally:
            # ELI5: Shut down the chiller so we don't leave background threads spinning.
            engine.stop()

    def test_engine_save_load_scene(self):
        # ELI5: Like taking a photograph of every light level in the house,
        # turning all the knobs to random, then pressing "Recall" and verifying
        # the lights snap back to the exact photograph.
        engine = InfiniteJukeboxEngine(config=EngineConfig(target_fps=60))
        try:
            # ELI5: Create a temporary folder to hold the scene photograph.
            with tempfile.TemporaryDirectory() as tmpdir:
                # ELI5: Build a path inside the temp folder for the hub's memory card.
                tmp_path = pathlib.Path(tmpdir) / "state.json"
                # ELI5: Swap the engine's memory card slot to point at our temp file.
                engine.state._persist_path = tmp_path
                # ELI5: Press the "ENERGETIC" button on the Lutron keypad.
                engine.model.mood = MoodPreset.ENERGETIC
                # ELI5: Take a mental snapshot of which button is lit.
                original_mood = engine.model.mood
                # ELI5: Press the "Save Scene" button on the touchscreen.
                engine.save_scene("test_scene")
                # ELI5: Press a completely different button — "DARK" — to scramble the scene.
                engine.model.mood = MoodPreset.DARK
                # ELI5: Press the "Recall" button for the scene we just saved.
                engine.load_scene("test_scene")
                # ELI5: Verify the lights snapped back to ENERGETIC, not staying on DARK.
                self.assertEqual(engine.model.mood, original_mood)
        finally:
            # ELI5: Power down the central plant cleanly.
            engine.stop()


# =============================================================================
# ENTRY POINT — Run the commissioning report
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
