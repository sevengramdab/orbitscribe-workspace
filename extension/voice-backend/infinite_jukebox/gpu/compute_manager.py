"""
Agent 3 — GPU Specialist: Compute & Viewport Orchestration
===========================================================
Imagine you are the master electrician wiring a smart mansion with FIVE
separate service panels (one per RTX 5090). Each panel feeds a different
wing of the house (viewport). This module is the lighting-control processor:
it makes sure no single panel is overloaded and that every room gets
power at exactly 60 Hz (one frame) without flicker, by pre-dimming scenes
into a memory buffer before the show starts.
"""

# Like ordering specialized conduit benders and wire pullers from the supply house.
from __future__ import annotations

# Like hiring five separate electrical crews so no one panel gets swamped.
import asyncio
# Like keeping a stopwatch on the foreman's belt so he knows when the concrete truck arrives.
import time
# Like having a master parts list so every electrician knows which breaker fits which panel.
from typing import Any, Dict, List, Optional, Tuple
# Like using standardized junction box templates instead of fabricating each one by hand.
from dataclasses import dataclass, field
# Like the structural engineer's load tables for calculating beam deflection.
import numpy as np
# Like the master key ring that keeps every electrical room locked except the one being worked on.
import threading

# Like pulling the approved fixture schedule, panel schedules, and one-line diagrams from the jobsite trailer.
from infinite_jukebox.architecture import (
    # The HVAC duct sizing chart that controls how thick the smoke gets.
    FluidConfig,
    # The Lutron lighting scene sheet with dimmer levels and color temperature.
    RenderConfig,
    # The monitor spec sheet for each TV in the security video wall.
    ViewportConfig,
    # The numbered labels on the monitors: PRIMARY, SECONDARY, TERTIARY, AUX_A, AUX_B.
    ViewportSlot,
    # The contract spec that says every PLC must speak Modbus to the VFDs.
    GpuComputeBackend,
)


# =============================================================================
# FBO DESCRIPTOR — The breaker panel directory sticker
# =============================================================================

# The directory sticker on a breaker panel that tells you every circuit's amp rating and room.
@dataclass
class FboDescriptor:
    """
    Framebuffer Object descriptor — like a breaker panel directory sticker that
    lists every circuit number, amp rating, which room it feeds, and whether
    the electrician has finished wiring it or left it unfinished (dirty).
    In GPU terms: width, height, format, handle, owner panel, and resolution.
    """
    # How many pixels wide the texture is — like counting the light switches on a wall plate.
    width: int
    # How many pixels tall the texture is — like counting the rows of outlets in a floor box.
    height: int
    # RGBA = 4 conductors in a single Romex cable; monochrome = 1 hot wire only.
    channels: int = 4
    # 32-bit float = heavy 10-AWG wire for industrial loads; 16-bit = light 14-AWG for lamps.
    dtype: str = "float32"
    # Handle assigned by the GPU driver — like the engraved circuit number on a breaker handle.
    texture_id: Optional[int] = None
    # True if the buffer has been modified since the last time the display thread read it —
    # like a sticky note on a junction box that says "DO NOT ENERGIZE — WORK IN PROGRESS."
    dirty: bool = True
    # Which of the five RTX 5090 panels owns this circuit — like labeling each breaker
    # with the panel number (Panel A, Panel B, etc.) so the apprentice knows where to go.
    gpu_owner: int = 0
    # Cached (width, height) tuple — like keeping a cut-sheet of drywall sizes
    # taped to the foreman's clipboard so he doesn't measure twice.
    resolution: Tuple[int, int] = field(init=False)
    # Time stamp of last write — like the sign-in sheet on a construction site
    # so you know when the last electrician touched the box.
    last_write_time: float = field(default_factory=time.time)

    # Like printing a placard that says "Room 101: 12 ft × 10 ft" instead of two separate notes.
    def __post_init__(self) -> None:
        # Glue the width and height together into one label for quick reference.
        self.resolution = (self.width, self.height)


# =============================================================================
# GPU COMMAND — A work order sitting in an electrician's inbox
# =============================================================================

# A three-part carbon form that says what job to do, which tools to bring, and where to sign when finished.
@dataclass
class GpuCommand:
    """
    One work order sitting in an electrician's inbox.
    """
    # The name of the shader kernel — like the job code on a work ticket: "ADVECT-001" or "JACOBI-007".
    name: str
    # The arguments passed to the kernel — like the materials list on a pick sheet.
    args: Tuple[Any, ...]
    # An asyncio.Future that the GPU worker fills in when the job is done —
    # like the pink copy of a purchase order that gets stapled to the invoice.
    future: asyncio.Future


# =============================================================================
# STREAMED FRAME — One pre-fabbed wall section on the warehouse shelf
# =============================================================================

# A pre-built wall section with studs, drywall, and outlets already assembled.
@dataclass
class StreamedFrame:
    """
    One pre-fabbed wall section sitting on the warehouse shelf.
    The construction crew just picks it up and nails it in place.
    """
    # A complete set of FBOs for every viewport in this frame —
    # like a pallet of pre-wired junction boxes, one box per room.
    fbo_banks: Dict[ViewportSlot, Dict[str, FboDescriptor]]
    # True if this frame has finished pre-rendering and is ready for the display thread —
    # like a green "PASSED INSPECTION" sticker on the electrical panel cover.
    ready: bool = False
    # The simulation step number this frame represents —
    # like the sequential address labels on a mail carrier's route.
    frame_number: int = 0
    # A padlock on the pallet so two forklifts don't grab the same box at once.
    _lock: threading.Lock = field(default_factory=threading.Lock)


# =============================================================================
# STREAMING RING BUFFER — The conveyor belt of pre-rendered frames
# =============================================================================

# An automated drywall hoist that keeps the next five sheets ready at ceiling height.
class StreamingRingBuffer:
    """
    A conveyor belt of pre-rendered frames — like an automated drywall
    hoist that keeps the next five sheets ready at ceiling height so the
    installer never has to stop and wait for the next board.
    """

    # Commission the conveyor belt with a given shelf size, monitor list, and smoke settings.
    def __init__(
        self,
        # How many future frames we keep on the shelf — like keeping five pre-cut wire harnesses in stock.
        capacity: int,
        # The list of monitors in our security wall — like the room schedule on a lighting plan.
        viewports: List[ViewportConfig],
        # The HVAC control settings that govern how thick the smoke is in each frame.
        fluid_config: FluidConfig,
    ) -> None:
        # Remember how many pallets fit on the conveyor.
        self.capacity = capacity
        # Remember which monitors need frames rendered for them.
        self.viewports = viewports
        # Remember the viscosity and dissipation knobs.
        self.fluid_config = fluid_config
        # The circular warehouse shelf with numbered slots — each slot holds one pre-built frame.
        self._slots: List[StreamedFrame] = []
        # Where the factory robot places the NEXT finished frame — like the conveyor index on a packaging line.
        self._write_seq = 0
        # Where the delivery truck picks up the NEXT frame for the jobsite — like the dispatch counter number.
        self._read_seq = 0
        # The last frame we handed to the display crew — like keeping a photo of the last panel
        # we installed so we know what it looked like if the new one isn't ready yet.
        self._last_delivered: Optional[StreamedFrame] = None
        # The master key for the warehouse — only one person can move the conveyor index at a time.
        self._lock = threading.Lock()
        # A doorbell that rings when new frames arrive — so the truck driver knows to wake up.
        self._not_empty = threading.Condition(self._lock)
        # Whether the assembly line is currently running — like the START/STOP button on a CNC machine.
        self._running = False
        # The factory worker thread that builds frames all day long.
        self._precompute_thread: Optional[threading.Thread] = None
        # The GPU manager we call to actually do the rendering — like the subcontractor
        # we hire to manufacture the wall sections before they reach our warehouse.
        self._manager: Optional[Any] = None
        # Stock the empty warehouse shelves with blank pallets before the first shift starts.
        self._allocate_slots()

    # Walk down the conveyor and place an empty pallet in every slot.
    def _allocate_slots(self) -> None:
        # Repeat once for every slot on the carousel.
        for _ in range(self.capacity):
            # Build a blank FBO bank for every viewport — one junction box per room per pallet.
            bank: Dict[ViewportSlot, Dict[str, FboDescriptor]] = {}
            # For each monitor in the security wall...
            for vp in self.viewports:
                # ...create the standard set of fluid simulation textures —
                # like wiring every junction box with the same color code.
                bank[vp.slot] = {
                    # The velocity field is a 2-channel texture — like a 240-V split-phase circuit.
                    "velocity": FboDescriptor(vp.width_px, vp.height_px, 2, gpu_owner=vp.gpu_index),
                    # The density field is RGBA — like a four-conductor thermostat cable.
                    "density": FboDescriptor(vp.width_px, vp.height_px, 4, gpu_owner=vp.gpu_index),
                    # Pressure is monochrome — like a single hot wire to a dedicated outlet.
                    "pressure": FboDescriptor(vp.width_px, vp.height_px, 1, gpu_owner=vp.gpu_index),
                    # Divergence is monochrome — like a neutral wire carrying return current.
                    "divergence": FboDescriptor(vp.width_px, vp.height_px, 1, gpu_owner=vp.gpu_index),
                    # Curl is monochrome — like a ground wire for safety monitoring.
                    "curl": FboDescriptor(vp.width_px, vp.height_px, 1, gpu_owner=vp.gpu_index),
                    # Display output is RGBA — like the full-color LED tape under the cabinets.
                    "display": FboDescriptor(vp.width_px, vp.height_px, 4, gpu_owner=vp.gpu_index),
                }
            # Place the finished blank pallet onto the conveyor shelf.
            self._slots.append(StreamedFrame(fbo_banks=bank))

    # Hand the subcontractor's business card to the warehouse foreman.
    def bind_manager(self, manager: Any) -> None:
        # Now the foreman knows who to call when he needs a new batch of wall sections.
        self._manager = manager

    # Press the green START button on the conveyor belt.
    def start(self) -> None:
        # The factory worker thread wakes up and begins pre-building frames.
        self._running = True
        # Hire the worker and tell him which assembly line to run.
        self._precompute_thread = threading.Thread(target=self._precompute_loop, daemon=True)
        # The worker clocks in and walks to his station.
        self._precompute_thread.start()

    # Press the red emergency STOP button — the conveyor halts at the end of the current cycle.
    def stop(self) -> None:
        # Flip the STOP switch to off.
        self._running = False
        # If the worker is still on the clock, wait up to two seconds for him to clean up his bench.
        if self._precompute_thread is not None:
            # Stand by the time clock until he punches out.
            self._precompute_thread.join(timeout=2.0)

    # This is the factory worker's daily routine — he builds frames until the whistle blows.
    def _precompute_loop(self) -> None:
        # Keep working as long as the START button is still lit.
        while self._running:
            # Lock the warehouse door so we can safely count inventory.
            with self._lock:
                # Count finished pallets minus delivered pallets = inventory still in stock.
                buffered = self._write_seq - self._read_seq
                # If every shelf slot is full, the worker takes a coffee break for one millisecond.
                if buffered >= self.capacity:
                    # Nap briefly so the delivery truck can catch up.
                    time.sleep(0.001)
                    # Skip back to the top of the loop and check again.
                    continue
                # Figure out which conveyor slot to fill next — like reading the next empty bin number.
                slot_idx = self._write_seq % self.capacity
                # Grab that pallet off the shelf so we can work on it.
                frame = self._slots[slot_idx]
            # If the pallet already has a green "PASSED" sticker, we can't reuse it yet.
            if frame.ready:
                # Nap for a millisecond while the delivery truck catches up.
                time.sleep(0.001)
                # Go check the next slot.
                continue
            # Render the next simulation frame into this blank pallet —
            # like wiring the junction boxes, installing breakers, and closing the cover.
            self._render_frame_into(frame, self._write_seq)
            # Lock the door again to update the inventory clipboard.
            with self._lock:
                # Stick the green "READY" sticker on the pallet.
                frame.ready = True
                # Write the sequence number on the sticker so the truck driver knows the order.
                frame.frame_number = self._write_seq
                # Advance the conveyor to the next empty slot.
                self._write_seq += 1
                # Ring the doorbell so the delivery driver knows fresh inventory arrived.
                self._not_empty.notify()

    # Wire the junction boxes, install breakers, and close the cover for one frame.
    def _render_frame_into(self, frame: StreamedFrame, frame_number: int) -> None:
        # If we haven't hired the GPU subcontractor yet, there's nothing to build.
        if self._manager is None:
            # Leave the pallet blank and return to the break room.
            return
        # In a full production build, this would dispatch advection, Jacobi, curl, and display
        # kernels through the GPU manager for every viewport — like sending work orders
        # to all five electrical panels to update their breaker settings for the next scene.
        # For now we just clear the dirty flags to simulate a fresh render pass.
        for bank in frame.fbo_banks.values():
            # For every circuit in this room's panel...
            for fbo in bank.values():
                # Wipe off the "WORK IN PROGRESS" sticky notes — the panel is now clean.
                fbo.dirty = False
                # Stamp today's date on the inspection tag so we know it's fresh.
                fbo.last_write_time = time.time()

    # The delivery truck driver walks into the warehouse and asks for the next pallet.
    def acquire_display_frame(self) -> Dict[ViewportSlot, Dict[str, FboDescriptor]]:
        # Lock the warehouse door so nobody moves the conveyor while we're grabbing.
        with self._lock:
            # If the read counter has caught up to the write counter, the shelf is empty.
            if self._read_seq >= self._write_seq:
                # If we have a photo of the last delivered frame, show that again so the screen doesn't go black.
                if self._last_delivered is not None:
                    # Hand over the photo so the display never flickers.
                    return self._last_delivered.fbo_banks
                # Brand new warehouse with nothing ever built — return an empty loading dock.
                return {}
            # Calculate which conveyor slot holds the next undelivered frame.
            slot_idx = self._read_seq % self.capacity
            # Grab that pallet and check its sticker.
            frame = self._slots[slot_idx]
            # If the sticker is missing, the worker hasn't finished building it yet.
            if not frame.ready:
                # Show the photo of the last frame again so the display never flickers.
                if self._last_delivered is not None:
                    # Hand over the archived photo.
                    return self._last_delivered.fbo_banks
                # Absolutely nothing to show — hand over an empty dock.
                return {}
            # Peel the "READY" sticker off so the slot can be reused for a future frame.
            frame.ready = False
            # Take a photo of this pallet for our records in case the next one isn't ready.
            self._last_delivered = frame
            # Advance the delivery counter so the next truck gets the next pallet.
            self._read_seq += 1
            # Hand the complete pallet of pre-wired junction boxes to the display crew.
            return frame.fbo_banks


# =============================================================================
# VIEWPORT MANAGER — The security-NOC video wall operator
# =============================================================================

# The operator at the security desk who decides which camera goes to which monitor.
class ViewportManager:
    """
    Manages a cluster of up to five viewports — like the operator at a
    security desk who decides which camera feeds go to which monitor
    in a 2×2 or 1×5 video wall. Each monitor can show a different angle
    (orthographic, perspective, top-down) of the same fluid scene.
    """

    # Set up the desk with the monitor list from the architect.
    def __init__(self, configs: List[ViewportConfig]) -> None:
        # Build a lookup table from monitor number to its configuration —
        # like labeling each TV on the security desk with a permanent marker.
        self.configs: Dict[ViewportSlot, ViewportConfig] = {}
        # Walk through the list of monitors the architect specified on the drawings.
        for cfg in configs:
            # Place each monitor's spec sheet into the labeled filing cabinet.
            self.configs[cfg.slot] = cfg
        # Default render order is lowest monitor number first —
        # like numbering cameras 1 through 5 along the hallway.
        self._render_order: List[ViewportSlot] = sorted(self.configs.keys())

    # The security chief rearranges the camera priority list.
    def set_render_order(self, order: List[ViewportSlot]) -> None:
        # Camera 3 goes full-screen during an incident, then drops back to thumbnail.
        self._render_order = order

    # Return only the monitors that are powered on and not blanked.
    def get_enabled(self) -> List[ViewportConfig]:
        # Skip the broken TV when you do your nightly patrol of the video wall.
        return [self.configs[s] for s in self._render_order if self.configs[s].enabled]

    # Pull the AutoCAD viewport scale drawing for a specific monitor.
    def viewport_transform(self, slot: ViewportSlot) -> np.ndarray:
        # It shows exactly how the 3-D model is rotated and zoomed for that camera.
        return self.configs[slot].view_transform

    # Auto-arrange the monitors on the wall like a Crestron touch panel.
    def compute_tiling(self, wall_width: int, wall_height: int) -> Dict[ViewportSlot, Tuple[int, int, int, int]]:
        # Returns: {slot: (x, y, w, h)} in pixels, like a lighting plot showing fixture positions.
        enabled = self.get_enabled()
        # Count how many TVs are actually turned on.
        n = len(enabled)
        # If every TV is off, the wall is blank — return an empty room.
        if n == 0:
            return {}
        # One monitor gets the entire wall — like a single 100-inch presentation screen.
        if n == 1:
            # Grab the only enabled monitor.
            vp = enabled[0]
            # Give it the full wall from corner to corner.
            return {vp.slot: (0, 0, wall_width, wall_height)}
        # Two monitors split the wall vertically — like a pair of french doors.
        if n == 2:
            # Cut the wall exactly in half.
            w = wall_width // 2
            # Place the left monitor on the left side.
            return {
                enabled[0].slot: (0, 0, w, wall_height),
                enabled[1].slot: (w, 0, wall_width - w, wall_height),
            }
        # Three monitors: two on top, one wide banner below — like a home theater with a center channel.
        if n == 3:
            # The top row takes two-thirds of the height.
            top_h = wall_height * 2 // 3
            # The bottom banner gets the remaining third.
            bot_h = wall_height - top_h
            # Split the top row into two equal halves.
            top_w = wall_width // 2
            # Lay out the three screens.
            return {
                enabled[0].slot: (0, 0, top_w, top_h),
                enabled[1].slot: (top_w, 0, wall_width - top_w, top_h),
                enabled[2].slot: (0, top_h, wall_width, bot_h),
            }
        # Four monitors: classic 2×2 grid — like a four-way security camera split screen.
        if n == 4:
            # Each column gets half the wall width.
            cw = wall_width // 2
            # Each row gets half the wall height.
            ch = wall_height // 2
            # Place the four quadrants.
            return {
                enabled[0].slot: (0, 0, cw, ch),
                enabled[1].slot: (cw, 0, wall_width - cw, ch),
                enabled[2].slot: (0, ch, cw, wall_height - ch),
                enabled[3].slot: (cw, ch, wall_width - cw, wall_height - ch),
            }
        # Five monitors: 2×2 grid plus one banner across the top — like a control room
        # with four detail screens and one master overview monitor above them all.
        if n == 5:
            # The top banner takes one-third of the height.
            banner_h = wall_height // 3
            # The remaining two-thirds is the 2×2 grid.
            grid_h = wall_height - banner_h
            # Two columns in the grid.
            cw = wall_width // 2
            # Two rows in the grid.
            ch = grid_h // 2
            # Place the banner across the entire top, then the 2×2 grid below.
            return {
                enabled[0].slot: (0, 0, wall_width, banner_h),
                enabled[1].slot: (0, banner_h, cw, ch),
                enabled[2].slot: (cw, banner_h, wall_width - cw, ch),
                enabled[3].slot: (0, banner_h + ch, cw, grid_h - ch),
                enabled[4].slot: (cw, banner_h + ch, wall_width - cw, grid_h - ch),
            }
        # Fallback for more than five: stretch them in a single horizontal ribbon —
        # like a stock-ticker LED strip above a trading floor.
        cw = wall_width // n
        # Create a slot-to-rectangle mapping by enumerating across the ribbon.
        return {
            vp.slot: (i * cw, 0, cw, wall_height)
            for i, vp in enumerate(enabled)
        }


# =============================================================================
# GPU COMPUTE MANAGER — The master PLC talking to five VFDs
# =============================================================================

# The programmable logic controller that sends Modbus commands to five variable-frequency drives.
class GpuComputeManager(GpuComputeBackend):
    """
    Abstracts GPU dispatch across a cluster of up to 5 RTX 5090 cards.
    Think of it as a PLC that sends Modbus commands to five VFDs,
    each running its own pump in its own electrical room.
    """

    # Commission the load center with the viewport list from the architect.
    def __init__(self, viewports: List[ViewportConfig]) -> None:
        # Save the list of monitors so we know which rooms need power.
        self.viewports = viewports
        # A filing cabinet where each drawer holds one viewport's set of FBOs —
        # like a panel schedule book with one page per breaker panel.
        self._fbos: Dict[ViewportSlot, Dict[str, FboDescriptor]] = {}
        # Map each GPU index to its async inbox — like giving each VFD its own mail slot.
        self._queues: Dict[int, asyncio.Queue] = {}
        # Map each GPU index to its event loop — like the programmable timer inside each VFD.
        self._loops: Dict[int, asyncio.AbstractEventLoop] = {}
        # Map each GPU index to its worker thread — like the electrician permanently assigned to each panel.
        self._threads: Dict[int, threading.Thread] = {}
        # A master padlock for the breaker room so two foremen don't throw the same breaker at once.
        self._lock = threading.RLock()
        # Build the FBO directory and spin up the five electrical rooms.
        self._commission_gpus()
        # Create the ring buffer that pre-renders frames so the display crew never waits.
        self._streamer: Optional[StreamingRingBuffer] = None

    # Build the breaker panels and hire the electricians.
    def _commission_gpus(self) -> None:
        # For each viewport in the building plan...
        for vp in self.viewports:
            # ...stock its breaker panel with the standard set of circuits.
            self._fbos[vp.slot] = {
                # The velocity field is a 2-channel texture — like a 240-V split-phase circuit.
                "velocity": FboDescriptor(vp.width_px, vp.height_px, 2, gpu_owner=vp.gpu_index),
                # The density field is RGBA — like a four-conductor thermostat cable.
                "density": FboDescriptor(vp.width_px, vp.height_px, 4, gpu_owner=vp.gpu_index),
                # Pressure is monochrome — like a single hot wire to a dedicated outlet.
                "pressure": FboDescriptor(vp.width_px, vp.height_px, 1, gpu_owner=vp.gpu_index),
                # Divergence is monochrome — like a neutral wire carrying return current.
                "divergence": FboDescriptor(vp.width_px, vp.height_px, 1, gpu_owner=vp.gpu_index),
                # Curl is monochrome — like a ground wire for safety monitoring.
                "curl": FboDescriptor(vp.width_px, vp.height_px, 1, gpu_owner=vp.gpu_index),
                # Display output is RGBA — like the full-color LED tape under the cabinets.
                "display": FboDescriptor(vp.width_px, vp.height_px, 4, gpu_owner=vp.gpu_index),
            }
        # We have five RTX 5090 cards — like five separate service entrances.
        for gpu_index in range(5):
            # Create a brand new async inbox for this GPU's work orders.
            loop = asyncio.new_event_loop()
            # File the loop away in the foreman's master key cabinet.
            self._loops[gpu_index] = loop
            # Create an empty mail slot that can hold unlimited work orders.
            queue: asyncio.Queue = asyncio.Queue()
            # Label the slot with the panel number and file it.
            self._queues[gpu_index] = queue
            # Hire an electrician and assign him permanently to this one panel.
            thread = threading.Thread(
                target=self._gpu_thread_main,
                args=(gpu_index, loop, queue),
                daemon=True,
            )
            # Put his employee ID badge in the payroll system.
            self._threads[gpu_index] = thread
            # The electrician walks into his electrical room and flips on the lights.
            thread.start()

    # The electrician enters his assigned room, sits down, and starts his timer.
    def _gpu_thread_main(
        self,
        # Which panel number is painted on the door.
        gpu_index: int,
        # The programmable timer on the electrician's bench.
        loop: asyncio.AbstractEventLoop,
        # The inbox where work orders appear.
        queue: asyncio.Queue,
    ) -> None:
        # The electrician enters his assigned room, sits down, and starts his timer.
        asyncio.set_event_loop(loop)
        # He will now read work orders from his inbox until he sees a pink slip (shutdown).
        loop.run_until_complete(self._gpu_worker(gpu_index, queue))

    # The electrician's daily routine: open the inbox, read the top form, do the job, repeat.
    async def _gpu_worker(self, gpu_index: int, queue: asyncio.Queue) -> None:
        # Keep reading forms forever until the pink slip arrives.
        while True:
            # If the inbox is empty, he takes a nap until the bell rings.
            cmd: GpuCommand = await queue.get()
            # If the job code is "shutdown," he cleans his bench and goes home.
            if cmd.name == "shutdown":
                # Sign the pink slip and file it in the completed bin.
                cmd.future.set_result(None)
                # Break out of the infinite loop — the shift is over.
                break
            # If the job code is "flush," it means the foreman wants a status report
            # after everything already in the inbox is finished. Since we process
            # one at a time, everything before this point is already done.
            if cmd.name == "flush":
                # Stamp the form "COMPLETE" and hand it back immediately.
                cmd.future.set_result(None)
                # Go back to waiting for the next work order.
                continue
            # Simulate the actual GPU kernel execution —
            # like tightening every lug on a breaker panel with a torque wrench.
            await asyncio.sleep(0)
            # For advection, we return the field handle so the next shader can find it.
            if cmd.name == "advect":
                cmd.future.set_result(cmd.args[0] if cmd.args else None)
            # For Jacobi pressure solve, we return the updated pressure buffer.
            elif cmd.name == "jacobi":
                cmd.future.set_result(cmd.args[0] if cmd.args else None)
            # For display composite, we return the final RGBA display buffer.
            elif cmd.name == "display":
                cmd.future.set_result(cmd.args[0] if cmd.args else None)
            # For curl calculation, we return the curl magnitude buffer.
            elif cmd.name == "curl":
                cmd.future.set_result(cmd.args[0] if cmd.args else None)
            # For vorticity confinement, we return the velocity buffer with swirls injected.
            elif cmd.name == "vorticity":
                cmd.future.set_result(cmd.args[0] if cmd.args else None)
            # Unknown job code — like receiving a work order for plumbing instead of electrical.
            else:
                cmd.future.set_result(None)

    # Figure out which electrical panel owns this wire.
    def _resolve_gpu(self, field: Any) -> int:
        # If the field carries a panel number tag, read that first.
        if isinstance(field, FboDescriptor):
            # The cable jacket is stamped with the panel number — easy.
            return field.gpu_owner
        # If the field has a dictionary with a gpu_owner key, read that tag.
        if isinstance(field, dict) and "gpu_owner" in field:
            # The wire nut has a colored band that tells us the panel.
            return int(field["gpu_owner"])
        # No tags found — default to Panel 0, the main service entrance.
        return 0

    # Plug the pre-render conveyor belt into this PLC so it can request GPU time.
    def attach_streamer(self, streamer: StreamingRingBuffer) -> None:
        # Remember the conveyor belt so we can ask it for pre-rendered frames later.
        self._streamer = streamer
        # Hand the PLC's business card to the conveyor belt foreman.
        streamer.bind_manager(self)

    # Queue an advection kernel — like telling a VFD to ramp a pump to a new speed.
    def dispatch_advection(self, field: Any, velocity: Any, dt: float) -> Any:
        # Find which panel the field's cable runs back to.
        gpu_index = self._resolve_gpu(field)
        # Get the programmable timer for that panel's electrical room.
        loop = self._loops[gpu_index]
        # Schedule the work order in that room and return a claim ticket.
        return asyncio.run_coroutine_threadsafe(
            self._async_dispatch(gpu_index, "advect", field, velocity, dt),
            loop,
        )

    # The foreman walks into the electrical room and drops a work order in the inbox.
    async def _async_dispatch(self, gpu_index: int, name: str, *args: Any) -> Any:
        # Grab the programmable timer for this specific electrical room.
        loop = self._loops[gpu_index]
        # Create a pink claim slip that the electrician will stamp when done.
        fut = loop.create_future()
        # Drop the work order and the pink slip into the inbox.
        await self._queues[gpu_index].put(GpuCommand(name, args, fut))
        # Wait right here in the waiting room until the electrician finishes and stamps the slip.
        return await fut

    # Queue a Jacobi solver — like telling the HVAC balancer to walk the building.
    def dispatch_jacobi(self, pressure: Any, divergence: Any, iterations: int) -> Any:
        # Find which panel the pressure sensor wire runs back to.
        gpu_index = self._resolve_gpu(pressure)
        # Get the programmable timer for that panel's electrical room.
        loop = self._loops[gpu_index]
        # Schedule the work order and return a claim ticket.
        return asyncio.run_coroutine_threadsafe(
            self._async_dispatch(gpu_index, "jacobi", pressure, divergence, iterations),
            loop,
        )

    # Queue the final lighting scene — like pressing the "Present" button on a Lutron keypad.
    def dispatch_display(self, density: Any, config: RenderConfig) -> Any:
        # Find which panel the density display cable runs back to.
        gpu_index = self._resolve_gpu(density)
        # Get the programmable timer for that panel's electrical room.
        loop = self._loops[gpu_index]
        # Schedule the work order and return a claim ticket.
        return asyncio.run_coroutine_threadsafe(
            self._async_dispatch(gpu_index, "display", density, config),
            loop,
        )

    # Queue a curl-calculation kernel — like using a clamp meter to measure swirl.
    def dispatch_curl(self, field: Any) -> Any:
        # Find which panel the field cable runs back to.
        gpu_index = self._resolve_gpu(field)
        # Get the programmable timer for that panel's electrical room.
        loop = self._loops[gpu_index]
        # Schedule the work order and return a claim ticket.
        return asyncio.run_coroutine_threadsafe(
            self._async_dispatch(gpu_index, "curl", field),
            loop,
        )

    # Queue a vorticity confinement kernel — like adding a swirl booster fan to a duct.
    def dispatch_vorticity(self, velocity: Any, curl: Any, strength: float) -> Any:
        # Find which panel the velocity cable runs back to.
        gpu_index = self._resolve_gpu(velocity)
        # Get the programmable timer for that panel's electrical room.
        loop = self._loops[gpu_index]
        # Schedule the work order and return a claim ticket.
        return asyncio.run_coroutine_threadsafe(
            self._async_dispatch(gpu_index, "vorticity", velocity, curl, strength),
            loop,
        )

    # Wait until every work order already in one specific panel's inbox is finished.
    def flush(self, gpu_index: int) -> None:
        # Get the programmable timer for that specific electrical room.
        loop = self._loops[gpu_index]
        # Send a "status check" form to the room and block until it comes back stamped.
        asyncio.run_coroutine_threadsafe(self._async_flush(gpu_index), loop).result()

    # Drop a special "flush" form in the inbox — the electrician signs it immediately after everything ahead of it is done.
    async def _async_flush(self, gpu_index: int) -> None:
        # Grab the programmable timer for this specific electrical room.
        loop = self._loops[gpu_index]
        # Create a pink claim slip that the electrician will stamp when the flush is acknowledged.
        fut = loop.create_future()
        # Drop the flush form and the pink slip into the inbox.
        await self._queues[gpu_index].put(GpuCommand("flush", (), fut))
        # Wait right here until the electrician stamps the slip.
        await fut

    # Wait until all five electrical rooms are caught up — like a final walk-through.
    def flush_all(self) -> None:
        # A basket to collect all the claim tickets from the five rooms.
        pending: List[Any] = []
        # Visit each of the five electrical rooms in turn.
        for gpu_index in self._loops:
            # Grab the timer for that room.
            loop = self._loops[gpu_index]
            # Drop a flush form in each room and collect the claim ticket.
            f = asyncio.run_coroutine_threadsafe(self._async_flush(gpu_index), loop)
            # Put the ticket in the basket.
            pending.append(f)
        # Stand in the hallway and wait for all five rooms to hand back signed forms.
        for f in pending:
            # Block until this specific room's form is signed.
            f.result()

    # Look up a specific circuit in a specific room's breaker panel.
    def get_viewport_fbo(self, slot: ViewportSlot, name: str) -> FboDescriptor:
        # Open the correct drawer in the filing cabinet.
        return self._fbos[slot][name]

    # Turn off the entire building — send pink slips to all five electrical rooms.
    def shutdown(self) -> None:
        # Walk down the hall and visit each of the five panels.
        for gpu_index in range(5):
            # If this room was never commissioned, skip it.
            if gpu_index not in self._loops:
                continue
            # Grab the timer for this room.
            loop = self._loops[gpu_index]
            # Create a pink claim slip for the shutdown notice.
            fut = loop.create_future()
            # The shutdown command needs to be scheduled in the loop.
            async def _send_shutdown() -> None:
                # Drop the pink slip into the inbox.
                await self._queues[gpu_index].put(GpuCommand("shutdown", (), fut))
            # Schedule the delivery in the electrical room.
            asyncio.run_coroutine_threadsafe(_send_shutdown(), loop)
            # Wait for the electrician to clean his bench and clock out.
            try:
                # Run a tiny coroutine that just waits for the future, then block on it.
                async def _wait_shutdown() -> None:
                    await fut
                # Give him two seconds to pack his tools.
                asyncio.run_coroutine_threadsafe(_wait_shutdown(), loop).result(timeout=2.0)
            except Exception:
                # If he doesn't respond, we'll cut power remotely.
                pass
            # Try to stop the timer gracefully.
            try:
                # Press the OFF button on the programmable timer.
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                # If the button is stuck, we'll yank the plug later.
                pass
            # Wait for the electrician to actually leave the building.
            thread = self._threads.get(gpu_index)
            if thread is not None:
                # Stand by the time clock for up to two seconds.
                thread.join(timeout=2.0)
