"""
Agent 1 — Architect: Model Space Blueprint
==========================================
Think of this file like the master blueprint drawer in AutoCAD who sets up
all the layers, linetypes, and viewport scales BEFORE the drafters start
drawing walls. We define every pipe, wire, and duct (data class) so the
electricians (Agent 3) and plumbers (Agent 2) know exactly what fittings
to bring to the jobsite.
"""

from __future__ import annotations

import enum
import dataclasses
from typing import Dict, List, Optional, Tuple, Callable, Any, Protocol, Set
from dataclasses import field
import numpy as np


# =============================================================================
# ENUMERATIONS — Like layer color standards in a CAD template
# =============================================================================

class SimulationQuality(enum.IntEnum):
    """
    LOD (Level of Detail) settings — just like AutoCAD viewport resolution.
    Low = quick wireframe preview; Ultra = full rendered ray-trace.
    """
    LOW = 128        # Draft mode: 128x128 grid, good for layout sketches
    MEDIUM = 256     # Standard mode: 256x256, like a typical plot preview
    HIGH = 512       # Presentation mode: 512x512, client-review quality
    ULTRA = 1024     # Final render: 1024x1024, billboard-print resolution


class AudioChannel(enum.IntEnum):
    """
    Audio routing channels — think of these as the colored phases in a
    three-phase electrical panel: L1 (bass), L2 (mids), L3 (treble).
    Each phase feeds a different bank of breakers (fluid splat sources).
    """
    BASS = 0         # 20–250 Hz   — sub-panel for heavy motors (kick drum)
    LOW_MID = 1      # 250–500 Hz  — general lighting branch
    MID = 2          # 500–2000 Hz — outlet circuits
    HIGH_MID = 3     # 2000–4000 Hz — HVAC control circuits
    TREBLE = 4       # 4000–20000 Hz — low-voltage data/communication


class ViewportSlot(enum.IntEnum):
    """
    Viewport slots for a 5× RTX 5090 cluster — like having five separate
    AutoCAD layout tabs, each looking at the model from a different angle.
    We tile them in a video wall (2×2 with one overhead, or 1×5 ribbon).
    """
    PRIMARY = 0      # Main front elevation
    SECONDARY = 1    # Right-side section
    TERTIARY = 2     # Plan (top-down) view
    AUX_A = 3        # Detail call-out A
    AUX_B = 4        # Detail call-out B


class MoodPreset(enum.Enum):
    """
    Pre-configured lighting scenes — like a Lutron HomeWorks keypad
    with buttons labeled "Cooking," "Entertaining," "Goodnight."
    Each mood rewires the audio-to-visual patch bay instantly.
    """
    AMBIENT = "ambient"
    ENERGETIC = "energetic"
    DARK = "dark"
    CHAOS = "chaos"
    MINIMAL = "minimal"


class LockState(enum.Enum):
    """
    ACE-Step 1.5 Proprietary Lock States — like a keyed switch on an
    industrial control panel that prevents unauthorized changes.
    FREE = anyone can adjust; LOCKED = only safety overrides work;
    OVERRIDE = emergency mode, all safeties bypassed.
    """
    FREE = "free"
    LOCKED = "locked"
    OVERRIDE = "override"


# =============================================================================
# DATA CLASSES — The "blocks" we insert into the drawing
# =============================================================================

@dataclasses.dataclass(frozen=True, slots=True)
class Vector2D:
    """
    A 2-D vector — like a simple line segment drawn from 0,0 to x,y
    in a two-point perspective sketch. Immutable so it can't accidentally
    get stretched after the structural engineer stamps it.
    """
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> Vector2D:
        return Vector2D(self.x * scalar, self.y * scalar)


@dataclasses.dataclass(frozen=True, slots=True)
class SplatPayload:
    """
    A 'splat' is like a paint blob shot from an airless sprayer into the
    fluid tank. It carries position (where the nozzle points), velocity
    (how hard the trigger is pulled), and color (what pigment is loaded).
    """
    origin: Vector2D = field(default_factory=Vector2D)
    velocity: Vector2D = field(default_factory=Vector2D)
    color_rgb: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    radius: float = 0.003          # Nozzle orifice diameter in UV space (0–1)
    density: float = 1.0           # Paint opacity / flow rate


@dataclasses.dataclass(frozen=True, slots=True)
class AudioFrame:
    """
    One frame of FFT analysis — like a single sweep of a spectrum analyzer
    hooked to a home-automation audio bus. Each bin is a circuit carrying
    a certain amount of "audio current."
    """
    timestamp_ms: int = 0
    frequency_bins: np.ndarray = field(default_factory=lambda: np.zeros(512, dtype=np.float32))
    peak_amplitude: float = 0.0
    zero_crossing_rate: float = 0.0
    spectral_centroid: float = 0.0


@dataclasses.dataclass(frozen=True, slots=True)
class FluidConfig:
    """
    The HVAC-style control panel for the fluid simulation.
    These knobs tune pressure, flow, and viscosity exactly like adjusting
    a VAV (Variable Air Volume) box in a commercial building.
    """
    grid_resolution: SimulationQuality = SimulationQuality.HIGH
    viscosity: float = 0.0              # 0 = water; higher = honey/molasses
    velocity_dissipation: float = 0.98  # How fast momentum bleeds off (duct friction)
    density_dissipation: float = 0.99   # How fast dye fades (lighting dimmer curve)
    pressure_iterations: int = 20       # Jacobi solver loops — like tightening a pipe joint
    curl_strength: float = 30.0         # Vorticity confinement — swirl booster
    splat_radius: float = 0.003         # Default nozzle orifice
    timestep: float = 0.016             # 60 FPS nominal — one frame = one time step


@dataclasses.dataclass(frozen=True, slots=True)
class RenderConfig:
    """
    The lighting and rendering schedule — like a Lutron home-automation
    scene that sets dimmer levels, color temperature, and blackout shades.
    """
    bloom_intensity: float = 0.3
    bloom_iterations: int = 8
    sunrays_weight: float = 1.0
    dither_strength: float = 0.03
    color_temperature: float = 6500.0   # Kelvin — daylight white
    exposure: float = 1.0
    gamma: float = 2.2


@dataclasses.dataclass(frozen=True, slots=True)
class ViewportConfig:
    """
    Each viewport is a separate monitor in a security-NOC video wall.
    We track resolution, which GPU card drives it, and what "camera angle"
    (transformation matrix) it uses.
    """
    slot: ViewportSlot = ViewportSlot.PRIMARY
    width_px: int = 1920
    height_px: int = 1080
    gpu_index: int = 0
    view_transform: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float32))
    enabled: bool = True


@dataclasses.dataclass(frozen=True, slots=True)
class AceStep15Constraint:
    """
    ACE-Step 1.5 Proprietary Lock State — like a tamper-evident seal on a
    junction box. Once these constraints are set, the music engine MUST
    obey them or the Main Breaker trips.
    
    This is the core of the "Fighter Jet" audio engine: instead of letting
    the neural net wander freely (paper airplane), we bolt it to a rigid
    grammar frame (fighter jet airframe) that controls syllabic density,
    rhythmic quantization, and frequency masking budgets.
    """
    max_syllabic_density: float = 0.45       # Notes-per-beat ceiling
    min_negative_space_ratio: float = 0.25   # Silence-to-sound floor
    frequency_mask_budget_hz: float = 120.0  # Min gap between simultaneous tones
    tempo_quantize_grid: int = 16            # 1/16th note snap — like a rigid conduit
    lock_state: LockState = LockState.FREE
    grammar_preset: str = "ambient_electronic"


@dataclasses.dataclass(frozen=True, slots=True)
class SignalPathNode:
    """
    One node in the Signal Path DAG (Directed Acyclic Graph).
    Think of this as a single device in a Crestron DM-NVX AV-over-IP
    chain: it has inputs (from upstream), outputs (to downstream),
    and a processing function (the internal DSP chip).
    
    The DAG ensures audio flows ONE WAY like water in a pipe — no
    feedback loops that cause howling or masking collisions.
    """
    node_id: str
    node_type: str                          # "oscillator", "filter", "compressor", etc.
    input_ids: Tuple[str, ...] = ()         # Upstream nodes feeding this one
    output_ids: Tuple[str, ...] = ()        # Downstream nodes this one feeds
    parameters: Dict[str, float] = field(default_factory=dict)
    enabled: bool = True


@dataclasses.dataclass
class SignalPathDag:
    """
    The complete audio routing diagram — like a riser diagram in an
    electrical blueprint showing how every panel, sub-panel, and
    junction box connects without any loops.
    
    We use this to enforce ACE-Step 1.5 constraints: before any note
    is rendered, we traverse the DAG to ensure no two oscillators
    occupy the same frequency mask budget at the same time.
    """
    nodes: Dict[str, SignalPathNode] = field(default_factory=dict)
    _sorted_order: List[str] = field(default_factory=list, repr=False)

    def add_node(self, node: SignalPathNode) -> None:
        """
        Insert a new device into the riser diagram.
        ELI5: Like adding a new outlet to a circuit — you have to make
        sure you don't create a loop that trips the breaker.
        """
        self.nodes[node.node_id] = node
        self._sorted_order = []  # Invalidate cached topological sort

    def topological_sort(self) -> List[str]:
        """
        Return nodes in dependency order — like wiring a house starting
        from the service entrance and working outward to the last outlet.
        If we tried to wire the bedroom before the breaker panel, nothing
        would work. This sort prevents that mistake.
        """
        if self._sorted_order:
            return self._sorted_order

        # Kahn's algorithm — like counting how many wires enter each junction
        # box, then wiring the boxes with zero incoming wires first.
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        for node in self.nodes.values():
            for out_id in node.output_ids:
                if out_id in in_degree:
                    in_degree[out_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_order: List[str] = []

        while queue:
            current = queue.pop(0)
            sorted_order.append(current)
            node = self.nodes[current]
            for out_id in node.output_ids:
                if out_id in in_degree:
                    in_degree[out_id] -= 1
                    if in_degree[out_id] == 0:
                        queue.append(out_id)

        if len(sorted_order) != len(self.nodes):
            raise ValueError("Cycle detected in Signal Path DAG — like a short circuit in the wiring.")

        self._sorted_order = sorted_order
        return sorted_order

    def get_active_path(self) -> List[SignalPathNode]:
        """
        Return only enabled nodes in processing order.
        ELI5: Like walking through a building and only turning on the
        lights in rooms that aren't marked "DO NOT ENTER."
        """
        order = self.topological_sort()
        return [self.nodes[nid] for nid in order if self.nodes[nid].enabled]


@dataclasses.dataclass
class NegativeSpaceMap:
    """
    Negative Space Mapping — like the clearance zones around high-voltage
    lines that keep trees and buildings at a safe distance. In audio, this
    tracks which frequency bands are "occupied" at each moment in time so
    we never place two notes so close together that they mask each other.
    
    The map is a 2-D grid: time (horizontal) vs frequency (vertical).
    A "1" means that frequency band is occupied; a "0" means it's open
    negative space where a new note can safely live.
    """
    time_slots: int = 64          # Horizontal resolution — like 64 timeline frames
    freq_bins: int = 512          # Vertical resolution — like 512 spectrum bands
    occupancy: np.ndarray = field(default_factory=lambda: np.zeros((64, 512), dtype=np.float32))

    def reserve_band(self, time_idx: int, freq_center: int, bandwidth_hz: float, bin_resolution_hz: float) -> bool:
        """
        Try to reserve a frequency band at a given time slot.
        Returns True if the reservation succeeded (space was available),
        False if the band was already occupied (masking collision).
        
        ELI5: Like calling the utility locator before digging. If there's
        already a gas line at 2 feet depth, you can't put a water main
        there — you'd have a dangerous collision. We return False so the
        scheduler picks a different depth (frequency) for the new note.
        """
        half_bins = max(1, int(bandwidth_hz / (2.0 * bin_resolution_hz)))
        lo = max(0, freq_center - half_bins)
        hi = min(self.freq_bins, freq_center + half_bins)
        t = time_idx % self.time_slots

        # Check if any part of this trench is already occupied
        if np.any(self.occupancy[t, lo:hi] > 0.5):
            return False

        # Mark the trench as dug
        self.occupancy[t, lo:hi] = 1.0
        return True

    def clear_past(self, current_time_idx: int) -> None:
        """
        Free up time slots that have already played.
        ELI5: Once the concrete truck has driven past a street segment,
        you can let normal traffic use that lane again.
        """
        self.occupancy[current_time_idx % self.time_slots, :] = 0.0

    def get_density_at(self, time_idx: int) -> float:
        """
        Fraction of frequency spectrum occupied at a given time slot.
        ELI5: Like measuring how full a parking garage is at 3 PM.
        0.0 = empty; 1.0 = every spot taken.
        """
        t = time_idx % self.time_slots
        return float(np.mean(self.occupancy[t, :]))


# =============================================================================
# PROTOCOLS — Interface contracts (like a submittal spec sheet)
# =============================================================================

class AudioBufferProvider(Protocol):
    """
    Anything that can feed audio frames — like a microphone pre-amp,
    a line-level mixer, or a DAW output channel.
    """
    def fetch_frame(self, n_bins: int = 512) -> AudioFrame:
        ...

    def register_callback(self, callback: Callable[[AudioFrame], None]) -> None:
        ...


class PhysicsSolver(Protocol):
    """
    Anything that steps the Navier-Stokes equations — like a pump
    controller that reads pressure sensors and adjusts impeller speed.
    """
    def step(self, splats: List[SplatPayload], dt: float) -> None:
        ...

    def get_velocity_field(self) -> np.ndarray:
        ...

    def get_density_field(self) -> np.ndarray:
        ...


class GpuComputeBackend(Protocol):
    """
    Anything that can dispatch GPU compute — like a PLC that talks
    Modbus to five different VFDs (Variable Frequency Drives).
    """
    def dispatch_advection(self, field: Any, velocity: Any, dt: float) -> Any:
        ...

    def dispatch_jacobi(self, pressure: Any, divergence: Any, iterations: int) -> Any:
        ...

    def dispatch_display(self, density: Any, config: RenderConfig) -> Any:
        ...


class StateStore(Protocol):
    """
    Anything that persists configuration and runtime state — like a
    home-automation hub that stores scenes and schedules in flash memory.
    """
    def get(self, key: str, default: Any = None) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def snapshot(self) -> Dict[str, Any]:
        ...


# =============================================================================
# MAIN BLUEPRINT — The jobsite trailer where all trades meet
# =============================================================================

@dataclasses.dataclass
class ModelSpace:
    """
    The master Model Space object — think of it as the locked reference file
    in AutoCAD that every discipline (MEP, Structural, Architecture) XREFs
    into their own drawings. It holds the single source of truth so nobody
    builds a beam through a supply duct.
    """
    fluid_config: FluidConfig = field(default_factory=FluidConfig)
    render_config: RenderConfig = field(default_factory=RenderConfig)
    viewports: List[ViewportConfig] = field(default_factory=list)
    audio_routing_map: Dict[AudioChannel, List[ViewportSlot]] = field(default_factory=dict)
    negative_space_threshold: float = 0.15   # Max splat density before masking kicks in
    lock_state: LockState = LockState.FREE

    # ACE-Step 1.5 hard constraints
    ace_constraints: AceStep15Constraint = field(default_factory=AceStep15Constraint)

    # Signal Path DAG — the audio riser diagram
    signal_path: SignalPathDag = field(default_factory=SignalPathDag)

    # Negative Space Map — the frequency clearance tracker
    negative_space_map: NegativeSpaceMap = field(default_factory=NegativeSpaceMap)

    # Mood preset for quick scene recall
    mood: MoodPreset = MoodPreset.AMBIENT

    def __post_init__(self) -> None:
        """
        Just like a project kick-off meeting: if nobody defined viewports,
        we create a default single-viewport layout so work can start.
        """
        if not self.viewports:
            self.viewports = [
                ViewportConfig(slot=ViewportSlot.PRIMARY, gpu_index=0),
            ]
        if not self.audio_routing_map:
            # Default audio patch: bass → primary, treble → secondary
            self.audio_routing_map = {
                AudioChannel.BASS: [ViewportSlot.PRIMARY],
                AudioChannel.TREBLE: [ViewportSlot.SECONDARY],
            }

    def apply_grammar_lock(self, syllabic_density: float) -> None:
        """
        The 'Main Breaker' grammar lock — like a fire-alarm shunt trip
        that disconnects non-essential loads when the generator is at max.
        If syllabic density (musical complexity) exceeds our visual budget,
        we clamp splat density to prevent frame drops.
        """
        # ELI5: Imagine your home's 200-amp main panel. If you try to draw
        # 250 amps (too many appliances), the main breaker trips to save
        # the house. Here we "trip" visual complexity instead of power.
        threshold = self.ace_constraints.max_syllabic_density
        if syllabic_density > threshold * 1.5:
            self.lock_state = LockState.OVERRIDE
        elif syllabic_density > threshold:
            self.lock_state = LockState.LOCKED
        else:
            self.lock_state = LockState.FREE

    def validate_signal_path(self) -> Tuple[bool, Optional[str]]:
        """
        Run a code-check on the audio DAG — like a plan reviewer at the
        building department making sure the electrical riser has no loops
        and every outlet is fed from a proper breaker.
        """
        try:
            self.signal_path.topological_sort()
            return True, None
        except ValueError as e:
            return False, str(e)
