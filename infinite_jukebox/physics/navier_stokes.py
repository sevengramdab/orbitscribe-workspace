"""
Agent 2 — Physicist: Navier-Stokes Mathematics
===============================================
Think of the fluid like water rushing through a municipal pipe network.
The Navier-Stokes equations are just fancy accounting: they track how much
water (mass) enters and leaves every pipe junction, and how much momentum
the water carries as it goes around bends. We solve them on a computer the
same way a hydraulic engineer uses Hardy-Cross iteration to balance flows.
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional
from dataclasses import dataclass, field

from infinite_jukebox.architecture import (
    FluidConfig,
    SplatPayload,
    Vector2D,
    SimulationQuality,
    NegativeSpaceMap,
)


# =============================================================================
# FLUID FIELD — The storage tank and pipe grid
# =============================================================================

@dataclass
class FluidField:
    """
    A FluidField is like a spreadsheet the city water department uses to
    track pressure at every intersection in a grid of streets. Each cell
    holds one number: velocity (how fast the water is moving) or density
    (how much dye or chlorine is in the water at that corner).
    """
    width: int
    height: int
    velocity: np.ndarray = field(repr=False)   # (H, W, 2) vector field
    density: np.ndarray = field(repr=False)    # (H, W, 3) RGB dye field
    pressure: np.ndarray = field(repr=False)   # (H, W) scalar field
    divergence: np.ndarray = field(repr=False) # (H, W) source/sink field

    @classmethod
    def create(cls, quality: SimulationQuality) -> FluidField:
        """
        Factory method — like prefabricating a standardized pressure vessel.
        We stamp out a clean, zero-filled grid in the exact size ordered.
        """
        # Read the viewport scale off the title block to know how big the drawing sheet is.
        res = int(quality)
        # Cast a concrete foundation slab with exactly the right square footage.
        return cls(
            # The horizontal lot line measured in pixels, like the X-dimension on a civil survey.
            width=res,
            # The vertical lot line measured in pixels, like the Y-dimension on a civil survey.
            height=res,
            # Pour a flat, empty velocity field — like installing empty conduit runs before pulling wire.
            velocity=np.zeros((res, res, 2), dtype=np.float32),
            # Lay down a blank RGB dye canvas — like hanging fresh drywall before the painter arrives.
            density=np.zeros((res, res, 3), dtype=np.float32),
            # Zero out the pressure ledger — like resetting a digital manometer before a balancing test.
            pressure=np.zeros((res, res), dtype=np.float32),
            # Clear the divergence log — like zeroing a flow meter before measuring pump output.
            divergence=np.zeros((res, res), dtype=np.float32),
        )


# =============================================================================
# NAVIER-STOKES SOLVER — The pump station controller
# =============================================================================

class NavierStokesSolver:
    """
    Steps the incompressible Navier-Stokes equations using Jos Stam's
    "Stable Fluids" semi-Lagrangian method. This is the digital equivalent
    of a SCADA system controlling a water-treatment plant: it reads sensors
    (current field), predicts where particles will drift (advection), then
    corrects pressure so pipes don't explode (projection).
    """

    def __init__(self, config: FluidConfig) -> None:
        """
        Initialize the solver with a configuration — like commissioning a
        new variable-frequency drive (VFD) with the motor nameplate data.
        """
        # Clip the config sheet to the clipboard so every sub-routine can read the motor specs.
        self.config = config
        # Fabricate the main fluid tank according to the drawing dimensions on the blueprint.
        self.field = FluidField.create(config.grid_resolution)
        # Pre-allocate spare velocity buffer — like keeping an empty spool of 12-AWG on the truck for emergency pulls.
        self._temp_velocity = np.zeros_like(self.field.velocity)
        # Pre-allocate spare density buffer — like stacking an extra sheet of drywall in the corner.
        self._temp_density = np.zeros_like(self.field.density)
        # Pre-allocate spare pressure buffer — like mounting a second pressure gauge as a backup.
        self._temp_pressure = np.zeros_like(self.field.pressure)
        # Pre-allocate a generic scalar scratch pad — like a notepad the foreman keeps in his hard-hat.
        self._temp_scalar = np.zeros_like(self.field.pressure)

    # -------------------------------------------------------------------------
    # PUBLIC API — The control room buttons
    # -------------------------------------------------------------------------

    def apply_negative_space_mask(
        self,
        splats: List[SplatPayload],
        nsm: NegativeSpaceMap,
    ) -> List[SplatPayload]:
        """
        Filter incoming splats through the NegativeSpaceMap before they
        hit the fluid grid. Like a load-shedding relay that checks how
        many circuits are already drawing power before allowing a new
        motor to start — if the panel is full, the relay drops the call.
        """
        # Start with an empty permit tray, like an inspector sorting approved breakers from rejected ones.
        approved: List[SplatPayload] = []
        # Read the ampacity threshold off the Main Breaker nameplate so we know when the panel is overloaded.
        threshold = 0.15
        # Walk down the incoming splat conveyor belt like an electrician checking every device before energizing it.
        for s in splats:
            # Convert the splat's horizontal position (0–1) into a station number on the surveyor's chain.
            time_idx = int(s.origin.x * nsm.time_slots)
            # Clamp the station number so the surveyor doesn't step off the end of the tape into the mud.
            time_idx = max(0, min(nsm.time_slots - 1, time_idx))
            # Call the utility locator to see how many trenches are already dug in this section of the jobsite.
            density = nsm.get_density_at(time_idx)
            # If the trench is less than 85 % full, the code official stamps the permit.
            if density < threshold:
                # Reserve a narrow band in the clearance map so the next excavator knows this spot is taken.
                nsm.reserve_band(time_idx, int(s.origin.y * nsm.freq_bins), 1.0, 1.0)
                # Add this approved load to the panel schedule.
                approved.append(s)
            else:
                # The breaker is already at max amps; this load gets shed and the motor stays off.
                continue
        # Hand the stamped permit stack back to the general contractor so the crew can start work.
        return approved

    def step(
        self,
        splats: List[SplatPayload],
        dt: float,
        nsm: Optional[NegativeSpaceMap] = None,
    ) -> None:
        """
        One full simulation step — like one complete PLC scan cycle:
        1. Filter splats through negative-space mask  → load-shedding relay
        2. Inject external forces (splat)              → open a fire hydrant
        3. Advect velocity by itself                   → water carries its own momentum
        4. Diffuse / apply viscosity                   → friction in long straight pipes
        5. Apply vorticity confinement                 → eductor jet re-injecting swirl
        6. Compute divergence                          → count water entering vs leaving
        7. Solve pressure Poisson equation             → install pressure regulator
        8. Subtract pressure gradient                  → balance the manifold
        9. Advect dye by velocity                      → carry chlorine downstream
        """
        # Pin the config sheet to the jobsite trailer wall so every trade can read the VFD settings.
        cfg = self.config
        # Point to the live velocity conduit so we don't have to keep writing the full pipe rack name.
        vel = self.field.velocity
        # Point to the live dye tank so we can tint it without typing the full storage vessel ID.
        dye = self.field.density

        # 1. NEGATIVE-SPACE MASKING
        # If the clearance-map relay is installed, run every new load through it before closing the breaker.
        if nsm is not None:
            # Reassign the splat list to only the loads that passed the load-shedding relay.
            splats = self.apply_negative_space_mask(splats, nsm)

        # 2. SPLAT (external force injection)
        # Walk through each approved fire-hydrant request one at a time.
        for s in splats:
            # Open the hydrant valve and let the water (velocity) and dye (color) surge into the grid.
            self._apply_splat(vel, dye, s)

        # 3. ADVECTION — "Carry yourself downstream"
        # Trace every drop of momentum backward in time, like reading a UPS tracking number to find where a package started.
        self._advect_field(vel, vel, self._temp_velocity, dt)
        # Copy the newly calculated routes back into the main dispatch ledger.
        np.copyto(vel, self._temp_velocity)

        # 4. VISCOSITY DIFFUSION — "Friction in the pipes"
        # Only run the friction loop if the VFD says the fluid is thicker than water.
        if cfg.viscosity > 0.0:
            # Spread the velocity evenly through the grid, like heat creeping through a thick concrete radiant slab.
            self._diffuse_field(vel, self._temp_velocity, cfg.viscosity, dt)
            # Paste the smoothed velocities back into the live pipe network drawing.
            np.copyto(vel, self._temp_velocity)

        # 5. VORTICITY CONFINEMENT — "Eductor jet boost"
        # Re-inject lost swirl so the hydronic heat exchanger doesn't go laminar and lose efficiency.
        self.apply_vorticity_confinement(dt)

        # 6. COMPUTE DIVERGENCE — "Is water piling up somewhere?"
        # Count how many gallons are entering each junction versus how many are leaving it.
        self._compute_divergence(vel, self.field.divergence)

        # 7. PRESSURE POISSON SOLVER — "Install a pressure regulator"
        # Walk around the building tightening flange bolts until every radiator reads the same pressure.
        self._solve_pressure_jacobi(
            self.field.pressure, self.field.divergence, cfg.pressure_iterations
        )

        # 8. GRADIENT SUBTRACTION — "Balance the manifold"
        # Adjust each balancing valve so no one room hogs all the hot water from the boiler.
        self._subtract_pressure_gradient(vel, self.field.pressure)

        # 9. DYE ADVECTION — "Carry the chlorine downstream"
        # Trace the dye backward along the streamlines, like following a food-coloring trail upstream to find the leak.
        self._advect_field(dye, vel, self._temp_density, dt, is_scalar=True)
        # Overwrite the old dye map with the newly transported pigment positions.
        np.copyto(dye, self._temp_density)
        # Fade the dye slightly, like a dimmer switch lowering the chandelier after dinner.
        dye *= cfg.density_dissipation

    def get_curl(self) -> np.ndarray:
        """
        Vorticity (curl) measures how much the fluid spins at each point.
        Think of it as an anemometer in a duct: positive = clockwise swirl,
        negative = counter-clockwise.
        """
        # Grab the live velocity drawing so we can measure how fast each wall is moving.
        vel = self.field.velocity
        # Roll out a fresh sheet of trace paper to sketch the curl values on.
        curl = np.zeros((self.field.height, self.field.width), dtype=np.float32)
        # Measure how much faster the right-hand wall is sliding than the left-hand wall in the Y-direction.
        dy = vel[1:-1, 2:, 1] - vel[1:-1, :-2, 1]
        # Measure how much faster the bottom wall is sliding than the top wall in the X-direction.
        dx = vel[2:, 1:-1, 0] - vel[:-2, 1:-1, 0]
        # Combine the two shear measurements and halve them, like averaging two dial gauge readings.
        curl[1:-1, 1:-1] = (dy - dx) * 0.5
        # Hand the curl trace back to the mechanical engineer for review.
        return curl

    def apply_vorticity_confinement(self, dt: float) -> None:
        """
        Boosts small eddies that numerical dissipation is killing off.
        Like a eductor jet in a hydronic system that re-injects turbulence
        so the heat exchanger doesn't go laminar and lose efficiency.
        """
        # Point to the live velocity conduit so we can add swirl forces to it.
        vel = self.field.velocity
        # Measure the current spin at every point, like an anemometer in every duct.
        curl = self.get_curl()
        # Roll out a fresh X-gradient sheet — like a new layer in AutoCAD for the horizontal pressure readings.
        grad_x = np.zeros_like(curl)
        # Roll out a fresh Y-gradient sheet — like a new layer for the vertical pressure readings.
        grad_y = np.zeros_like(curl)
        # Calculate the horizontal slope of the spin map by comparing the cell to its left and right neighbors.
        grad_x[1:-1, 1:-1] = 0.5 * (np.abs(curl[1:-1, 2:]) - np.abs(curl[1:-1, :-2]))
        # Calculate the vertical slope of the spin map by comparing the cell to its top and bottom neighbors.
        grad_y[1:-1, 1:-1] = 0.5 * (np.abs(curl[2:, 1:-1]) - np.abs(curl[:-2, 1:-1]))

        # Compute the total steepness of the spin hill, adding a tiny shim so we never divide by zero.
        norm = np.sqrt(grad_x**2 + grad_y**2) + 1e-5
        # Normalize the X-gradient so it becomes a unit vector, like scaling a line to exactly 1 inch in AutoCAD.
        grad_x /= norm
        # Normalize the Y-gradient the same way, keeping both dimensions on the same sheet scale.
        grad_y /= norm

        # Multiply the curl-strength knob by the time step to get the size of the eductor boost this frame.
        conf = self.config.curl_strength * dt
        # Compute the X-direction swirl force by crossing the Y-gradient with the local curl.
        force_x = conf * grad_y * curl
        # Compute the Y-direction swirl force by crossing the negative X-gradient with the local curl.
        force_y = -conf * grad_x * curl

        # Add the swirl force to the X-velocity layer, like bumping up a VFD speed by 2 Hz.
        vel[:, :, 0] += force_x
        # Add the swirl force to the Y-velocity layer, like bumping up a second VFD in parallel.
        vel[:, :, 1] += force_y

    # -------------------------------------------------------------------------
    # INTERNALS — The pump curves and valve schedules
    # -------------------------------------------------------------------------

    def _apply_splat(
        self,
        velocity: np.ndarray,
        density: np.ndarray,
        splat: SplatPayload,
    ) -> None:
        """
        Inject a Gaussian blob of velocity and color at a point.
        Like a paint-sprayer nozzle: the farther from center, the less paint.
        """
        # Measure the height of the drawing sheet in pixels, like reading the Y-axis on a title block.
        h = velocity.shape[0]
        # Measure the width of the drawing sheet in pixels, like reading the X-axis on a title block.
        w = velocity.shape[1]
        # Convert the splat's normalized X position into an absolute column number on the grid.
        cx = int(splat.origin.x * w)
        # Convert the splat's normalized Y position into an absolute row number on the grid.
        cy = int(splat.origin.y * h)
        # Convert the nozzle radius from a percentage of sheet width into actual pixels, keeping it at least one pixel wide.
        r_px = max(1, int(splat.radius * w))

        # Lay out an open-ended coordinate grid for the rows and columns, like a surveyor setting up offset stakes.
        y_coords, x_coords = np.ogrid[:h, :w]
        # Measure the squared distance from every grid point back to the spray nozzle center.
        dist_sq = (x_coords - cx) ** 2 + (y_coords - cy) ** 2
        # Build a Gaussian bell curve that peaks at the nozzle and fades like overspray on a drywall mask.
        gaussian = np.exp(-dist_sq / (2.0 * r_px * r_px + 1e-6))

        # Push the X-momentum into the velocity field, like a plumber forcing water through a pipe with a plunger.
        velocity[:, :, 0] += gaussian * splat.velocity.x * splat.density
        # Push the Y-momentum into the velocity field, like a second plunger working the cross-connection.
        velocity[:, :, 1] += gaussian * splat.velocity.y * splat.density

        # Loop through the three color channels like an electrician landing RGB LED wires on separate terminals.
        for i, c in enumerate(splat.color_rgb):
            # Tint the dye field by the Gaussian mask, like spraying paint through a stencil so only the cut-out gets color.
            density[:, :, i] += gaussian * c * splat.density

    def _diffuse_field(
        self,
        field: np.ndarray,
        out: np.ndarray,
        viscosity: float,
        dt: float,
    ) -> None:
        """
        Stable diffusion via Jacobi iteration.
        Like a radiant floor where hot water loops spread warmth evenly;
        the higher the viscosity, the thicker the concrete slab, and the
        slower the heat spreads.
        """
        # Measure the grid height so we know the north-south dimension of the radiant slab.
        h = field.shape[0]
        # Measure the grid width so we know the east-west dimension of the radiant slab.
        w = field.shape[1]
        # Calculate the diffusion coefficient, like figuring out how many BTUs the boiler must deliver per square foot.
        a = dt * viscosity * h * w
        # Pre-compute the reciprocal of the denominator so we don't do division inside the hot loop.
        inv_denom = 1.0 / (1.0 + 4.0 * a)
        # Copy the original field into the current-guess buffer, like setting all thermostats to the starting temperature.
        x_old = field.copy()
        # Remember which buffer the caller wants filled, like marking the destination conduit with blue tape.
        target = out
        # Run the Jacobi iteration as many times as the pressure-regulator spec calls for.
        for _ in range(self.config.pressure_iterations):
            # Spread each cell's value to its four neighbors and blend back with the original, like a four-way dimmer circuit.
            out[1:-1, 1:-1] = (
                # Add the right neighbor's value, like heat leaking through the east wall.
                x_old[1:-1, 2:] +
                # Add the left neighbor's value, like heat leaking through the west wall.
                x_old[1:-1, :-2] +
                # Add the bottom neighbor's value, like heat rising through the floor.
                x_old[2:, 1:-1] +
                # Add the top neighbor's value, like heat sinking through the ceiling.
                x_old[:-2, 1:-1]
            ) * a * inv_denom + field[1:-1, 1:-1] * inv_denom
            # Swap the two clipboards so the newest guess becomes the old one on the next lap.
            x_old, out = out, x_old
        # Copy the final balanced temperatures back into the output buffer so the HVAC controller can read them.
        np.copyto(target, x_old)

    def _advect_field(
        self,
        field: np.ndarray,
        velocity: np.ndarray,
        out: np.ndarray,
        dt: float,
        is_scalar: bool = False,
    ) -> None:
        """
        Semi-Lagrangian advection — the heart of Stable Fluids.
        Instead of asking "where does this particle GO?" (which can blow up),
        we ask "where did this particle COME FROM?" and trace backward.
        It's like reverse-engineering a UPS delivery route by looking at
        where a package was yesterday to guess where it is today.
        """
        # Measure the grid height so the surveyor knows how many north-south stations there are.
        h = field.shape[0]
        # Measure the grid width so the surveyor knows how many east-west stations there are.
        w = field.shape[1]
        # Lay out a rectangular grid of easting coordinates, like setting up a surveyor's grid along the X-axis.
        x_grid, y_grid = np.meshgrid(np.arange(w), np.arange(h))

        # Branch based on whether we're moving a scalar (dye) or a vector (velocity), like choosing between a voltmeter and an ammeter.
        if is_scalar:
            # Trace backward in time along the X-streamline to find where this parcel of dye came from.
            x_src = x_grid - velocity[:, :, 0] * dt * w
            # Trace backward in time along the Y-streamline to find the same parcel's vertical origin.
            y_src = y_grid - velocity[:, :, 1] * dt * h
            # Sample the dye color at those origin coordinates using bilinear interpolation, like mixing four paint cans.
            out[:, :] = self._sample_bilinear(field, x_src, y_src)
        else:
            # Loop through each vector component (X and Y), like checking both phases of a split-phase motor.
            for c in range(field.shape[2]):
                # Backtrack along the X-streamline for this component.
                x_src = x_grid - velocity[:, :, 0] * dt * w
                # Backtrack along the Y-streamline for this component.
                y_src = y_grid - velocity[:, :, 1] * dt * h
                # Sample the old velocity component at the traced origin and write it into the output buffer.
                out[:, :, c] = self._sample_bilinear(field[:, :, c], x_src, y_src)

    def _sample_bilinear(
        self,
        src: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:
        """
        Bilinear interpolation — like AutoCAD's SURFBLEND command.
        We estimate the value between four known survey points by weighting
        each corner based on how close the sample spot is to it.
        """
        # Read the height of the source image so we know the boundary of our lot.
        h = src.shape[0]
        # Read the width of the source image so we know the other boundary of our lot.
        w = src.shape[1]
        # Find the integer column just to the left of the sample point, like snapping to the nearest grid line.
        x0 = np.floor(x).astype(np.int32)
        # Find the integer row just above the sample point, like snapping to the nearest contour line.
        y0 = np.floor(y).astype(np.int32)
        # Step one grid line to the right for the next column over.
        x1 = x0 + 1
        # Step one contour line down for the next row below.
        y1 = y0 + 1

        # Measure how far past the left grid line the sample landed, like reading the fractional foot on a tape measure.
        fx = x - x0
        # Measure how far past the top contour line the sample landed.
        fy = y - y0

        # Clamp the left column to stay inside the sheet border, like a setback line preventing construction on the easement.
        x0 = np.clip(x0, 0, w - 1)
        # Clamp the right column to stay inside the sheet border.
        x1 = np.clip(x1, 0, w - 1)
        # Clamp the top row to stay inside the sheet border.
        y0 = np.clip(y0, 0, h - 1)
        # Clamp the bottom row to stay inside the sheet border.
        y1 = np.clip(y1, 0, h - 1)

        # If the source has multiple channels, expand the fractional weights so they broadcast to every color.
        if src.ndim == 3:
            # Add a dummy axis to the horizontal fraction so it can multiply across RGB channels.
            fx = fx[..., np.newaxis]
            # Add a dummy axis to the vertical fraction so it also spans all three colors.
            fy = fy[..., np.newaxis]

        # Blend the four corner samples using the SURFBLEND weights, like mixing concrete from four bags based on proximity.
        sample = (
            # Top-left bag contributes its share, weighted by how far we are from the other three corners.
            src[y0, x0] * (1 - fx) * (1 - fy)
            # Top-right bag contributes its share, weighted by horizontal closeness.
            + src[y0, x1] * fx * (1 - fy)
            # Bottom-left bag contributes its share, weighted by vertical closeness.
            + src[y1, x0] * (1 - fx) * fy
            # Bottom-right bag contributes its share, weighted by closeness in both directions.
            + src[y1, x1] * fx * fy
        )
        # Deliver the blended sample back to the inspector.
        return sample

    def _compute_divergence(self, velocity: np.ndarray, out: np.ndarray) -> None:
        """
        Divergence = ∂vx/∂x + ∂vy/∂y.
        Like checking if more amps are entering a junction than leaving it.
        Positive divergence = source (water spraying out);
        Negative divergence = sink (water draining down).
        """
        # Measure the horizontal current difference between the right and left neighbors.
        dx = velocity[1:-1, 2:, 0] - velocity[1:-1, :-2, 0]
        # Measure the vertical current difference between the bottom and top neighbors.
        dy = velocity[2:, 1:-1, 1] - velocity[:-2, 1:-1, 1]
        # Calculate the imbalance at every interior cell by comparing inflow to outflow, like a load study on a breaker panel.
        out[1:-1, 1:-1] = 0.5 * (dx + dy)

    def _solve_pressure_jacobi(
        self,
        pressure: np.ndarray,
        divergence: np.ndarray,
        iterations: int,
    ) -> None:
        """
        Jacobi iteration for the Poisson equation ∇²p = div.
        Think of it as balancing a hydronic heating loop:
        you walk around to each radiator, feel if it's too hot or cold,
        adjust its valve a tiny bit, then move to the next one.
        After enough laps (iterations), the whole house is balanced.
        """
        # Duplicate the current pressure map so we don't overwrite the readings while we're still using them.
        p_prev = pressure.copy()
        # Point to the spare pressure buffer, like switching to the backup manometer.
        p_next = self._temp_pressure
        # Walk around the building this many times, adjusting one valve per lap.
        for _ in range(iterations):
            # Read the pressure from the east neighbor, like feeling the radiator in the next room.
            east = p_prev[1:-1, 2:]
            # Read the pressure from the west neighbor.
            west = p_prev[1:-1, :-2]
            # Read the pressure from the north neighbor.
            north = p_prev[2:, 1:-1]
            # Read the pressure from the south neighbor.
            south = p_prev[:-2, 1:-1]
            # Set each interior cell to the average of its four neighbors minus the local divergence.
            p_next[1:-1, 1:-1] = (east + west + north + south - divergence[1:-1, 1:-1]) * 0.25
            # Swap the two manometers so the adjusted readings become the baseline for the next lap.
            p_prev, p_next = p_next, p_prev
        # Copy the final balanced pressures back into the official pressure map.
        np.copyto(pressure, p_prev)

    def _subtract_pressure_gradient(
        self, velocity: np.ndarray, pressure: np.ndarray
    ) -> None:
        """
        Make the velocity field divergence-free by subtracting ∇p.
        Like installing a pressure-balancing valve in a shower so that
        when someone flushes a toilet, the hot/cold mix stays perfect.
        """
        # Measure the horizontal pressure drop from east to west, like reading the differential across a balancing valve.
        grad_x = pressure[1:-1, 2:] - pressure[1:-1, :-2]
        # Measure the vertical pressure drop from south to north, like reading the differential on a top-floor balancing valve.
        grad_y = pressure[2:, 1:-1] - pressure[:-2, 1:-1]
        # Adjust the X-velocity by half the horizontal pressure difference, like turning a balancing valve left or right.
        velocity[1:-1, 1:-1, 0] -= 0.5 * grad_x
        # Adjust the Y-velocity by half the vertical pressure difference, like adjusting the top-floor balancing valve.
        velocity[1:-1, 1:-1, 1] -= 0.5 * grad_y
