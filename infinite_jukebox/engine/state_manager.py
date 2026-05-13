"""
Agent 7 — State Manager: Main Breaker & Dynamic Configuration
=============================================================
Think of this module as the electrical service entrance and main breaker
panel for the entire building. It decides which circuits are live, which
are locked out for maintenance, and how much total load is allowed before
the main breaker trips to protect the transformer.
"""

# Like keeping a copy of the National Electrical Code on your truck so you always have the rules handy.
from __future__ import annotations

# Like filing every conduit tag in the electrical room so the inspector can read them.
import json
# Like putting a padlock on the breaker panel so only the licensed electrician can open it.
import threading
# Like the wall clock in the home-automation hub that schedules when lights turn on and off.
import time
# Like the blueprint drawer that labels every wire size and breaker rating on the plans.
from typing import Dict, Any, Optional, Callable, List, Tuple
# Like the CAD template that stamps every drawing with the project name and date.
from dataclasses import dataclass, field, asdict, is_dataclass, replace
# Like the file cabinet where you store the as-built drawings for each jobsite.
from pathlib import Path
# Like the scientific calculator the engineer uses to size transformer loads.
import numpy as np
# Like the color-coded wire labels that tell you if a conductor is hot, neutral, or ground.
import enum
# Like the master parts catalog that lists every fitting in a panel schedule.
import dataclasses

# Like ordering all the specialty breakers from the supply house before rough-in starts.
from infinite_jukebox.architecture import (
    # Like the HVAC VAV box settings that control airflow in each room.
    FluidConfig,
    # Like the Lutron dimmer scene that sets every light level in the house at once.
    RenderConfig,
    # Like the monitor layout plan for the security operations center video wall.
    ViewportConfig,
    # Like the locked reference drawing that every trade XREFs into their own sheets.
    ModelSpace,
    # Like the contract spec that says every home-automation hub must store scenes in flash memory.
    StateStore,
    # Like the keyed switch on an industrial panel that has three positions: free, locked, override.
    LockState,
    # Like the tamper-evident seal on a junction box that says how much load is allowed.
    AceStep15Constraint,
    # Like the Lutron keypad buttons labeled "Cooking," "Entertaining," "Goodnight."
    MoodPreset,
    # Like the layout tabs in AutoCAD that show front elevation, section, plan view.
    ViewportSlot,
    # Like the resolution settings on a plotter: draft, standard, presentation, final.
    SimulationQuality,
    # Like the colored phases in a three-phase panel: L1 bass, L2 mids, L3 treble.
    AudioChannel,
    # Like the floor plan that shows where you can dig without hitting utility lines.
    NegativeSpaceMap,
    # Like the riser diagram that shows how every electrical panel connects without loops.
    SignalPathDag,
    # Like a single outlet or junction box on the electrical riser diagram.
    SignalPathNode,
)


# =============================================================================
# JSON SERIALIZATION — Like translating blueprint AutoCAD blocks into PDFs and back
# =============================================================================

# Like the master directory at the permit office that lists every approved subcontractor by name.
_TYPE_MAP: Dict[str, Any] = {
    "FluidConfig": FluidConfig,
    "RenderConfig": RenderConfig,
    "ViewportConfig": ViewportConfig,
    "AceStep15Constraint": AceStep15Constraint,
    "SignalPathNode": SignalPathNode,
    "SignalPathDag": SignalPathDag,
    "NegativeSpaceMap": NegativeSpaceMap,
    "ModelSpace": ModelSpace,
    "LockState": LockState,
    "MoodPreset": MoodPreset,
    "ViewportSlot": ViewportSlot,
    "SimulationQuality": SimulationQuality,
    "AudioChannel": AudioChannel,
}


def _encode_value(obj: Any) -> Any:
    # Like taking a photograph of the jobsite so the client can see progress without visiting.
    if isinstance(obj, np.ndarray):
        # Like writing down the exact dimensions of a beam on the submittal sheet so the fabricator can rebuild it.
        return {
            "__numpy__": True,
            "data": obj.tolist(),
            "shape": obj.shape,
            "dtype": str(obj.dtype),
        }
    # Like writing the wire color on a tag so the apprentice knows which phase it is.
    if isinstance(obj, enum.IntEnum):
        # Like snapping a photo of the wire label and the conduit number together.
        return {"__intenum__": True, "cls": obj.__class__.__name__, "value": int(obj)}
    # Like writing the model number on a light fixture so the supplier ships the right part.
    if isinstance(obj, enum.Enum):
        # Like snapping a photo of the fixture catalog page with the part number circled.
        return {"__enum__": True, "cls": obj.__class__.__name__, "value": obj.value}
    # Like creating a parts list for an electrical panel so every breaker and bus bar is accounted for.
    if is_dataclass(obj) and not isinstance(obj, type):
        # Like opening the panel door and starting a blank inventory sheet.
        result: Dict[str, Any] = {"__dataclass__": True, "cls": obj.__class__.__name__}
        # Like walking through every breaker position and writing down the amp rating.
        for f in dataclasses.fields(obj):
            # Like copying the amp rating from the breaker handle onto the inventory sheet.
            result[f.name] = _encode_value(getattr(obj, f.name))
        # Like handing the completed inventory sheet to the general contractor.
        return result
    # Like cataloging every device in a home-automation rack so nothing gets lost during a move.
    if isinstance(obj, dict):
        # Like opening a new moving box and labeling it room-by-room.
        result: Dict[str, Any] = {}
        # Like picking up each device and deciding which box it goes into.
        for k, v in obj.items():
            # Like checking if the device already has a plain paper label or needs a special barcode.
            if isinstance(k, str):
                # Like dropping the device into the box with the matching room label.
                result[k] = _encode_value(v)
            else:
                # Like printing a barcode sticker for a device that has no readable label.
                encoded_key = "__key__:" + json.dumps(_encode_value(k), separators=(",", ":"))
                # Like placing the barcoded device into the moving box.
                result[encoded_key] = _encode_value(v)
        # Like sealing the box and writing the room name on the outside.
        return result
    # Like writing down the wire sequence for a three-way switch so you don't mix up travelers.
    if isinstance(obj, tuple):
        # Like making a numbered list of wire colors in the exact order they enter the switch.
        return {"__tuple__": True, "items": [_encode_value(v) for v in obj]}
    # Like copying a simple measurement from the tape measure straight onto the cut list.
    if isinstance(obj, list):
        # Like transferring a stack of lumber tags one by one onto the delivery ticket.
        return [_encode_value(v) for v in obj]
    # Like a standard screw size that doesn't need any special translation.
    return obj


def _decode_value(obj: Any) -> Any:
    # Like opening the delivery crate and checking every part against the packing slip.
    if isinstance(obj, dict):
        # Like unrolling a blueprint sheet that was folded for shipping and laying it flat again.
        if "__numpy__" in obj:
            # Like re-cutting the beam to the exact length written on the submittal.
            arr = np.array(obj["data"], dtype=obj["dtype"])
            # Like bending the beam back into the shape shown on the structural drawing.
            return arr.reshape(obj["shape"])
        # Like matching the wire color tag back to the phase diagram in the panel schedule.
        if "__intenum__" in obj:
            # Like looking up the wire color code in the NEC appendix.
            return _TYPE_MAP[obj["cls"]](obj["value"])
        # Like matching the model number on a light fixture back to the spec sheet.
        if "__enum__" in obj:
            # Like looking up the fixture catalog number in the lighting schedule.
            return _TYPE_MAP[obj["cls"]](obj["value"])
        # Like rebuilding a three-way switch by following the wire sequence you wrote down earlier.
        if "__tuple__" in obj:
            # Like cutting each wire to length and placing them in the exact order on the terminal screws.
            return tuple(_decode_value(v) for v in obj["items"])
        # Like assembling an electrical panel from the parts list you cataloged last week.
        if "__dataclass__" in obj:
            # Like finding the right panel catalog page for this brand of breaker box.
            cls = _TYPE_MAP[obj["cls"]]
            # Like laying out every breaker on the bench before snapping it into the bus.
            field_values: Dict[str, Any] = {}
            # Like checking each breaker position against the panel schedule one slot at a time.
            for f in dataclasses.fields(cls):
                # Like snapping the breaker into the slot if the schedule says it belongs there.
                if f.name in obj:
                    # Like tightening the terminal screw after the breaker is seated.
                    field_values[f.name] = _decode_value(obj[f.name])
            # Like closing the panel door once every breaker is in its proper place.
            return cls(**field_values)
        # Like walking through every room in the house and checking off devices on the punch list.
        result: Dict[str, Any] = {}
        # Like inspecting each wall plate and outlet to see if it needs correction.
        for k, v in obj.items():
            # Like finding a barcode sticker on a device that was packed without a readable label.
            if isinstance(k, str) and k.startswith("__key__:"):
                # Like scanning the barcode to reveal the original hidden label.
                key_payload = json.loads(k[8:])
                # Like writing the real device name onto the punch list instead of the barcode.
                decoded_key = _decode_value(key_payload)
                # Like marking the device as inspected with its true name.
                result[decoded_key] = _decode_value(v)
            else:
                # Like checking off a plainly labeled outlet the way it appears on the plans.
                result[k] = _decode_value(v)
        # Like handing the completed punch list to the superintendent.
        return result
    # Like unspooling a coil of wire and measuring each segment against your cut list.
    if isinstance(obj, list):
        # Like stripping the insulation off each wire segment one at a time.
        return [_decode_value(v) for v in obj]
    # Like a standard screw that came out of the box exactly as ordered.
    return obj


# =============================================================================
# STATE MANAGER — The home-automation hub flash memory
# =============================================================================

class StateManager(StateStore):
    """
    Thread-safe key/value store for all runtime configuration.
    Like a Lutron HomeWorks processor that keeps scene data in non-volatile
    memory so lights come back to the right level after a power outage.
    """

    def __init__(self, persist_path: Optional[Path] = None, model_space: Optional[ModelSpace] = None) -> None:
        # Like initializing a blank schedule in the home-automation hub before programming scenes.
        self._data: Dict[str, Any] = {}
        # Like installing a keyed lock on the hub so two electricians can't reprogram it at once.
        self._lock = threading.RLock()
        # Like choosing the filing cabinet drawer where the as-built drawings will live.
        self._persist_path = persist_path
        # Like connecting the hub to the actual light circuits it will control.
        self._model_space = model_space
        # Like creating an empty contact list for every tenant who wants text alerts when a breaker trips.
        self._subscribers: List[Callable[[str, Any], None]] = []
        # Like checking if there is already a saved schedule on the hub's memory card from last week.
        if persist_path and persist_path.exists():
            # Like pressing the "restore from backup" button on the hub touchscreen.
            self._load_from_disk()

    # -------------------------------------------------------------------------
    # STATE STORE PROTOCOL
    # -------------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        # Like glancing at a thermostat display to see what temperature the room is set to.
        with self._lock:
            # Like opening the front panel of the home-automation hub to read a sensor value.
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        # Like turning a Lutron dimmer slider with one hand while watching the light change.
        with self._lock:
            # Like checking what the dimmer was set to before you touched it.
            old = self._data.get(key)
            # Like moving the slider to the new brightness level.
            self._data[key] = value
            # Like checking if the room actually got brighter or if you barely moved the slider.
            if old != value:
                # Like walking down the hallway and flipping every switch that is tied to this scene.
                for cb in self._subscribers:
                    # Like trying to send a text alert to one tenant; if their phone is off, skip them.
                    try:
                        # Like actually pressing send on the text message.
                        cb(key, value)
                    # Like shrugging when one tenant's mailbox is full and moving to the next.
                    except Exception:
                        pass
                # Like checking if the hub has a memory card slot so you can save the new scene.
                if self._persist_path:
                    # Like pressing the "save" button on the hub touchscreen.
                    self._save_to_disk()

    def snapshot(self) -> Dict[str, Any]:
        # Like printing the full panel schedule to PDF so you can carry a copy in your truck.
        with self._lock:
            # Like photocopying every page of the binder so the original never leaves the office.
            return json.loads(json.dumps(self._data, default=str))

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        # Like pairing a wireless Lutron Pico remote to the hub so it can control scenes.
        self._subscribers.append(callback)

    def _save_to_disk(self) -> None:
        # Like writing the as-built drawings onto a USB drive so they don't disappear if the computer crashes.
        if self._persist_path:
            # Like trying to copy the files without dropping any pages in the puddle outside.
            try:
                # Like dragging the PDF folder onto the flash drive icon.
                self._persist_path.write_text(json.dumps(self._data, indent=2, default=str))
            # Like shrugging if the USB port is broken and making a mental note to fix it later.
            except Exception:
                pass

    def _load_from_disk(self) -> None:
        # Like reloading the panel schedule from the backup drive after the laptop died.
        try:
            # Like opening the backup PDF and reading every page back into the laptop.
            self._data = json.loads(self._persist_path.read_text())
        # Like shrugging if the backup drive is blank and starting with a fresh template.
        except Exception:
            self._data = {}

    # -------------------------------------------------------------------------
    # SCENE SAVE / LOAD — Like storing and recalling Lutron lighting scenes
    # -------------------------------------------------------------------------

    def save_scene(self, name: str) -> None:
        # Like checking if the home-automation hub is actually wired to the lights before saving a scene.
        if self._model_space is None:
            # Like displaying an error on the hub screen saying "No lights found to save."
            raise ValueError("No model space bound to this state manager")
        # Like choosing the folder on the server where all the scene files are kept.
        scenes_dir = (self._persist_path.parent / "scenes") if self._persist_path else Path("scenes")
        # Like creating the folder if the electrician forgot to make it last week.
        scenes_dir.mkdir(parents=True, exist_ok=True)
        # Like naming the file "Evening.scene.json" so you know which button it belongs to.
        scene_path = scenes_dir / f"{name}.scene.json"
        # Like taking a photograph of every light level in the house and writing it down in one packet.
        payload = _encode_value(self._model_space)
        # Like saving that packet to the hard drive so the scene survives a power outage.
        scene_path.write_text(json.dumps(payload, indent=2))

    def load_scene(self, name: str) -> None:
        # Like checking if the hub is connected to the lights before pressing the recall button.
        if self._model_space is None:
            # Like showing an error that says "No lighting system found to restore."
            raise ValueError("No model space bound to this state manager")
        # Like opening the drawer on the server where all the scene backups are stored.
        scenes_dir = (self._persist_path.parent / "scenes") if self._persist_path else Path("scenes")
        # Like picking up the specific file labeled with the scene name you want.
        scene_path = scenes_dir / f"{name}.scene.json"
        # Like checking if the file actually exists before trying to load it.
        if not scene_path.exists():
            # Like telling the homeowner that the "Evening" scene was never programmed.
            raise FileNotFoundError(f"Scene {name} not found")
        # Like reading the entire contents of the scene file into memory.
        payload = json.loads(scene_path.read_text())
        # Like translating the saved packet back into real light levels and switch positions.
        loaded = _decode_value(payload)
        # Like making sure the decoded packet is actually a lighting schedule and not a grocery list.
        if not isinstance(loaded, ModelSpace):
            # Like throwing away a corrupted file before it fries the dimmers.
            raise ValueError("Corrupted scene file")
        # Like walking through every switch in the house and setting it to match the saved scene.
        for f in dataclasses.fields(ModelSpace):
            # Like adjusting one dimmer at a time until the whole room matches the photograph.
            setattr(self._model_space, f.name, getattr(loaded, f.name))


# =============================================================================
# MAIN BREAKER — The safety interlock for musical grammar
# =============================================================================

class MainBreaker:
    """
    Enforces hard visual constraints that map to musical grammar.
    Like a fire-alarm shunt-trip breaker: when the band plays too dense
    (too many notes per second = too much electrical load), we shed
    non-essential visual circuits to keep the main engine from crashing.
    """

    def __init__(self, state: StateManager, cooldown_seconds: float = 0.0) -> None:
        # Like wiring the breaker to the home-automation hub so it can log every trip event.
        self.state = state
        # Like setting the breaker handle to the ON position when you first energize the panel.
        self._tripped = False
        # Like clearing the fault sticker so the panel starts with a clean history.
        self._trip_reason: Optional[str] = None
        # Like resetting the stopwatch that measures how long ago the last trip happened.
        self._last_trip_time: float = 0.0
        # Like setting the mandatory cool-down timer so the compressor can't restart immediately.
        self._cooldown_seconds = cooldown_seconds

    def evaluate(self, model: ModelSpace, syllabic_density: float) -> None:
        # Like reading the amp rating off the main breaker handle to know the house limit.
        threshold = model.ace_constraints.max_syllabic_density

        # Like checking if every appliance in the house is drawing more than one-and-a-half times the panel rating.
        if syllabic_density > threshold * 1.5:
            # Like pulling the fire-alarm shunt-trip handle to disconnect everything instantly.
            self._trip("CRITICAL: syllabic density exceeded 1.5× rated load")
            # Like writing down the exact time the fire alarm went off for the incident report.
            self._last_trip_time = time.time()
            # Like flipping the keyed switch to OVERRIDE so the fire marshal can bypass safeties.
            model.lock_state = LockState.OVERRIDE
            # Like shutting off every decorative light circuit so only emergency exit signs stay on.
            model.render_config = replace(
                model.render_config,
                # Like turning the bloom dimmer all the way to zero.
                bloom_intensity=0.0,
                # Like disabling the bloom processor entirely.
                bloom_iterations=0,
                # Like pulling the fuse on the sunray generator.
                sunrays_weight=0.0,
                # Like turning off the dither circuit so no extra noise is added.
                dither_strength=0.0,
            )
            # Like preparing a new list of monitors for the security wall.
            new_vps: List[ViewportConfig] = []
            # Like walking past every monitor and deciding which ones stay on.
            for vp in model.viewports:
                # Like checking if this monitor is the main front-door camera or just a backup hallway view.
                if vp.slot != ViewportSlot.PRIMARY:
                    # Like cutting power to the backup monitor so the main feed doesn't glitch.
                    new_vps.append(replace(vp, enabled=False))
                else:
                    # Like leaving the main monitor powered because the guard needs to see the front door.
                    new_vps.append(vp)
            # Like updating the video wall controller with the new power schedule.
            model.viewports = new_vps

        # Like checking if the load is above the normal rating but not yet at fire-alarm levels.
        elif syllabic_density > threshold:
            # Like flipping the main breaker to the TRIP position because the panel is running hot.
            self._trip("WARNING: shedding post-FX to maintain 60 FPS")
            # Like writing the trip time in the logbook for the maintenance crew.
            self._last_trip_time = time.time()
            # Like turning the keyed switch to LOCKED so tenants can't turn on more appliances.
            model.lock_state = LockState.LOCKED
            # Like reading the current dimmer settings before dimming them for load shed.
            cfg = model.render_config
            # Like creating a new scene with lower wattage so the main breaker survives.
            model.render_config = replace(
                cfg,
                # Like dimming the bloom lights down to thirty percent so they use less power.
                bloom_intensity=cfg.bloom_intensity * 0.3,
                # Like reducing the number of bloom processing loops by half, but never below zero.
                bloom_iterations=max(0, cfg.bloom_iterations // 2),
                # Like pulling the fuse on the sunray generator completely.
                sunrays_weight=0.0,
            )
            # Like preparing a revised monitor list for the security wall.
            new_vps = []
            # Like inspecting every monitor to decide if it is essential.
            for vp in model.viewports:
                # Like checking if this screen is the primary entrance camera.
                if vp.slot != ViewportSlot.PRIMARY:
                    # Like turning off the secondary monitor to save amps for the main feed.
                    new_vps.append(replace(vp, enabled=False))
                else:
                    # Like keeping the primary monitor on because the guard station must stay operational.
                    new_vps.append(vp)
            # Like uploading the revised monitor schedule to the video wall controller.
            model.viewports = new_vps

        # Like checking if the house is back within its normal amp budget.
        else:
            # Like verifying the breaker is tripped and enough time has passed to safely re-energize.
            if self._tripped and (time.time() - self._last_trip_time) > self._cooldown_seconds:
                # Like flipping the main breaker back to ON because the load has dropped and the timer expired.
                self._reset()

    def _trip(self, reason: str) -> None:
        # Like checking if the breaker is already in the tripped position.
        if not self._tripped:
            # Like flipping the handle to TRIP so no more power flows.
            self._tripped = True
            # Like sending a text alert to the hub saying the breaker is now open.
            self.state.set("main_breaker.tripped", True)
        # Like writing the exact reason on the red fault tag.
        self._trip_reason = reason
        # Like logging the fault description into the home-automation history file.
        self.state.set("main_breaker.reason", reason)

    def _reset(self) -> None:
        # Like checking if the breaker handle is actually in the tripped position before resetting.
        if self._tripped:
            # Like pushing the handle back to ON so power flows again.
            self._tripped = False
            # Like peeling the red fault tag off the breaker.
            self._trip_reason = None
            # Like sending a text to the hub saying the breaker is closed again.
            self.state.set("main_breaker.tripped", False)
            # Like clearing the fault description from the automation log.
            self.state.set("main_breaker.reason", None)

    @property
    def is_tripped(self) -> bool:
        # Like glancing at the breaker handle to see if it is pointing to TRIP.
        return self._tripped

    @property
    def reason(self) -> Optional[str]:
        # Like reading the red fault tag hanging on the breaker handle.
        return self._trip_reason


# =============================================================================
# CONFIGURATION BREAKER — The live-tweak inspector who checks every change
# =============================================================================

class ConfigurationBreaker:
    """
    Live-tweak dynamic configuration gatekeeper.
    Like a plan reviewer at the building department: every change order
    must be stamped BEFORE the contractor rips open the wall. If the change
    violates the NEC ampacity tables (ACE-Step 1.5 constraints), it is
    rejected and the wall stays closed.
    """

    def __init__(self, state: StateManager, model: ModelSpace) -> None:
        # Like giving the inspector a two-way radio to the home-automation hub.
        self.state = state
        # Like handing the inspector the master blueprint so he can compare every change order.
        self.model = model

    def apply_render_config(self, config: RenderConfig) -> Tuple[bool, Optional[str]]:
        # Like reading the current lighting schedule to know how bright the room already is.
        current = self.model.render_config
        # Like checking if the keyed switch is in LOCKED or OVERRIDE position.
        if self.model.lock_state in (LockState.LOCKED, LockState.OVERRIDE):
            # Like checking if the proposed change would make the lights brighter than they already are.
            if (
                # Like comparing the proposed bloom wattage to the current wattage.
                config.bloom_intensity > current.bloom_intensity
                # Like checking if the proposed bloom circuit needs more processing loops.
                or config.bloom_iterations > current.bloom_iterations
                # Like checking if the sunray generator would draw more power than before.
                or config.sunrays_weight > current.sunrays_weight
            ):
                # Like stamping the change order REJECTED because it overloads the panel.
                return False, "Breaker is tripped: cannot increase post-processing load"
        # Like updating the lighting schedule because the change passed inspection.
        self.model.render_config = config
        # Like logging the new scene to the home-automation hub memory.
        self.state.set("config.render", asdict(config))
        # Like handing the approved stamp back to the contractor.
        return True, None

    def apply_fluid_config(self, config: FluidConfig) -> Tuple[bool, Optional[str]]:
        # Like checking if the emergency override key is still in the lock.
        if self.model.lock_state == LockState.OVERRIDE:
            # Like comparing the proposed HVAC grid size to the current one.
            if config.grid_resolution.value > self.model.fluid_config.grid_resolution.value:
                # Like rejecting the change because a bigger air handler would trip the mains.
                return False, "Override lock: cannot increase simulation grid resolution"
        # Like updating the VAV box schedule because the change is safe.
        self.model.fluid_config = config
        # Like writing the new settings into the building automation trend log.
        self.state.set("config.fluid", asdict(config))
        # Like giving the mechanical contractor the green light.
        return True, None

    def apply_ace_constraints(self, constraints: AceStep15Constraint) -> Tuple[bool, Optional[str]]:
        # Like reading the current NEC ampacity table that is posted on the panel door.
        current = self.model.ace_constraints
        # Like checking if the engineer wants to raise the amp ceiling above what the wire can handle.
        if constraints.max_syllabic_density > current.max_syllabic_density:
            # Like stamping the drawing REJECTED because the wire would overheat.
            return False, "Cannot raise syllabic density ceiling above current safety limit"
        # Like checking if the engineer wants to shrink the clearance zone around high-voltage lines.
        if constraints.min_negative_space_ratio < current.min_negative_space_ratio:
            # Like rejecting the change because two conductors would be too close together.
            return False, "Cannot reduce negative space ratio below current safety limit"
        # Like checking if the engineer wants to reduce the frequency gap between parallel circuits.
        if constraints.frequency_mask_budget_hz < current.frequency_mask_budget_hz:
            # Like rejecting the change because crosstalk would fry the equipment.
            return False, "Cannot tighten frequency mask below current safety limit"
        # Like posting the revised ampacity table on the panel door.
        self.model.ace_constraints = constraints
        # Like saving the updated code table into the permanent project file.
        self.state.set("config.ace", asdict(constraints))
        # Like telling the inspector the new rules are approved.
        return True, None

    def set_lock_state(self, state: LockState) -> Tuple[bool, Optional[str]]:
        # Like turning the keyed switch to the requested position.
        self.model.lock_state = state
        # Like logging the switch position in the access-control audit trail.
        self.state.set("lock.state", state.value)
        # Like handing the key back to the facilities manager.
        return True, None

    def set_mood(self, mood: MoodPreset) -> Tuple[bool, Optional[str]]:
        # Like pressing the "Cooking" or "Goodnight" button on the Lutron keypad.
        self.model.mood = mood
        # Like recording which scene was recalled in the automation log.
        self.state.set("config.mood", mood.value)
        # Like watching the lights fade to the new scene.
        return True, None

    def enable_viewport(self, slot: ViewportSlot, enabled: bool) -> Tuple[bool, Optional[str]]:
        # Like checking if the main breaker is tripped and non-essential loads are shed.
        if self.model.lock_state in (LockState.LOCKED, LockState.OVERRIDE):
            # Like checking if someone is trying to turn on a backup monitor while the panel is hot.
            if enabled and slot != ViewportSlot.PRIMARY:
                # Like refusing to power the backup monitor because the main feed needs every available amp.
                return False, "Breaker is tripped: cannot enable non-primary viewports"
        # Like preparing a new monitor schedule for the video wall controller.
        new_vps: List[ViewportConfig] = []
        # Like walking past every monitor and checking its label.
        for vp in self.model.viewports:
            # Like checking if this monitor is the one the change order is talking about.
            if vp.slot == slot:
                # Like flipping the power switch on this specific monitor to match the request.
                new_vps.append(replace(vp, enabled=enabled))
            else:
                # Like leaving all the other monitors exactly as they are.
                new_vps.append(vp)
        # Like uploading the revised monitor schedule to the video wall controller.
        self.model.viewports = new_vps
        # Like logging which monitor was toggled in the security system audit trail.
        self.state.set(f"viewport.{slot.name}.enabled", enabled)
        # Like telling the security guard the monitor status has been updated.
        return True, None

    def apply_change(self, key: str, value: Any) -> Tuple[bool, Optional[str]]:
        # Like sorting the incoming change order into the correct filing cabinet drawer.
        if key == "render_config":
            # Like checking if the contractor handed you a lighting schedule or a plumbing invoice.
            if not isinstance(value, RenderConfig):
                # Like sending the plumber away because this desk only reviews electrical.
                return False, "Value must be RenderConfig"
            # Like forwarding the lighting schedule to the electrical plan reviewer.
            return self.apply_render_config(value)
        # Like checking if the change order belongs to the mechanical department.
        elif key == "fluid_config":
            # Like verifying the document is actually an HVAC drawing and not a landscape plan.
            if not isinstance(value, FluidConfig):
                # Like rejecting the document because it is on the wrong blueprint sheet.
                return False, "Value must be FluidConfig"
            # Like sending the HVAC plan to the mechanical reviewer.
            return self.apply_fluid_config(value)
        # Like checking if the change order is for the structural ampacity table.
        elif key == "ace_constraints":
            # Like making sure the document is a stamped engineering calculation.
            if not isinstance(value, AceStep15Constraint):
                # Like refusing to review it because it lacks the engineer's seal.
                return False, "Value must be AceStep15Constraint"
            # Like handing the calculation to the code-compliance officer.
            return self.apply_ace_constraints(value)
        # Like checking if the change order is just moving the keyed switch.
        elif key == "lock_state":
            # Like making sure the key is a real key and not a screwdriver.
            if not isinstance(value, LockState):
                # Like telling the tenant to use the proper key.
                return False, "Value must be LockState"
            # Like forwarding the request to the access-control desk.
            return self.set_lock_state(value)
        # Like checking if the change order is a mood scene recall.
        elif key == "mood":
            # Like making sure the button label matches one of the keypad buttons.
            if not isinstance(value, MoodPreset):
                # Like telling the homeowner that keypad does not have a "Disco" button.
                return False, "Value must be MoodPreset"
            # Like pressing the button and recording the scene change.
            return self.set_mood(value)
        # Like checking if the change order refers to a specific video wall monitor.
        elif key.startswith("viewport.") and key.endswith(".enabled"):
            # Like reading the monitor number from the middle of the work order string.
            slot_name = key.split(".")[1]
            # Like looking up that monitor in the equipment schedule.
            try:
                # Like finding the monitor label in the directory.
                slot = ViewportSlot[slot_name]
            # Like telling the technician that monitor does not exist in this building.
            except KeyError:
                return False, f"Unknown viewport slot {slot_name}"
            # Like making sure the work order says ON or OFF and not "maybe."
            if not isinstance(value, bool):
                # Like rejecting the order because it is written in pencil and smudged.
                return False, "Value must be bool"
            # Like sending the work order to the AV technician.
            return self.enable_viewport(slot, value)
        # Like finding a change order that does not match any department and filing it in the trash.
        else:
            # Like stamping the document UNKNOWN and returning it to the sender.
            return False, f"Unknown configuration key: {key}"
