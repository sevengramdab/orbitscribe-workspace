"""
Agent 6 — VFX Artist: Post-Processing Pipeline
==============================================
ELI5: This module is like a whole-home surge protector with four stages.
The raw video signal comes in from the street, gets smoothed (bloom),
gets sunlight added (sunrays), gets its voltage leveled (tone-map),
and finally gets grain added so the wall paint doesn't show streaks (dither).
Each stage is a separate breaker in the panel, wired in series.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from infinite_jukebox.architecture import RenderConfig


class PostProcessPipeline:
    """
    A rack of signal processors wired like a Lutron lighting-control panel.
    The image signal enters at the top, flows through each dimmer module,
    and exits at the bottom ready for the display wall.
    """

    def __init__(self, config: RenderConfig = None) -> None:
        # ELI5: Like loading a Lutron scene into the processor's memory card
        # so it remembers the default dimmer levels even if no one touches the knobs.
        self.config = config if config is not None else RenderConfig()

    # ======================================================================
    # BLOOM — Atmospheric glow around bright objects
    # ======================================================================

    @staticmethod
    def apply_bloom(frame: np.ndarray, intensity: float, iterations: int) -> np.ndarray:
        """
        Gaussian blur pyramid bloom using separable kernels.
        ELI5: Like a smart-home accent-lighting circuit that detects which
        bulbs are drawing too much current and bleeds their glow onto the
        neighboring walls through a series of dimming modules.
        """
        # Extract only the overloaded bright pixels, like an electrician
        # tracing which breakers are above 80% load on the panel.
        bright = np.maximum(frame - 0.8, 0.0) * 5.0

        # Set up an empty accumulator, like a spare bus bar waiting to
        # collect all the blurred light layers before they hit the fixtures.
        bloom = np.zeros_like(bright)

        # Start with the raw bright layer; each loop is another floor
        # in the building where the lights get softer and smaller.
        layer = bright.copy()

        for i in range(iterations):
            # Blur this floor with a separable Gaussian kernel,
            # like running cable through a conduit first east-west,
            # then north-south, instead of bending it diagonally.
            sigma = 1.0 + float(i) * 0.8
            layer = gaussian_filter(layer, sigma=sigma, mode="constant")

            # If the layer is still bigger than a postage stamp,
            # downsample to the next floor by skipping every other stud.
            if layer.shape[0] > 4 and layer.shape[1] > 4:
                layer = layer[::2, ::2]

            # Stretch the blurred layer back to full wallpaper size
            # so it can be wired into the accumulator.
            if layer.shape[:2] != bright.shape[:2]:
                # Compute lookup indices like a surveyor marking studs
                # at proportional intervals along a long wall.
                y_idx = np.clip(
                    np.arange(bright.shape[0]) * layer.shape[0] // bright.shape[0],
                    0,
                    layer.shape[0] - 1,
                )
                x_idx = np.clip(
                    np.arange(bright.shape[1]) * layer.shape[1] // bright.shape[1],
                    0,
                    layer.shape[1] - 1,
                )
                # Pull the resized layer from the blueprint using the stud marks.
                layer = layer[y_idx[:, None], x_idx[None, :]]

            # Add this floor's glow to the accumulator bus bar.
            bloom = bloom + layer

        # Average the stack so we don't overload the final circuit.
        bloom = bloom / float(iterations)

        # Mix the glow back onto the original image through the intensity dimmer.
        result = frame + bloom * intensity

        # Clamp to 0–1 like a circuit breaker preventing display overload.
        return np.clip(result, 0.0, 1.0)

    # ======================================================================
    # SUNRAYS — Volumetric light shafts (god-rays)
    # ======================================================================

    @staticmethod
    def apply_sunrays(frame: np.ndarray, weight: float) -> np.ndarray:
        """
        Radial god-rays effect emanating from center.
        ELI5: Stand in a dark warehouse with one skylight. Dust catches
        the beam and you see rays fanning outward. This effect stretches
        bright pixels away from the center like pulling taffy.
        """
        # Measure the building dimensions so we know where the electrical room is.
        h, w = frame.shape[:2]
        center_y = h // 2
        center_x = w // 2

        # Lay out a coordinate grid like a surveyor staking a construction lot.
        y = np.arange(h)
        x = np.arange(w)
        dy = y[:, None] - center_y
        dx = x[None, :] - center_x

        # Distance from center for every pixel, like measuring cable run length.
        dist = np.sqrt(dy.astype(np.float32) ** 2 + dx.astype(np.float32) ** 2)
        max_dist = np.sqrt(center_y ** 2 + center_x ** 2) + 1e-5

        # Normalize to 0–1 like a potentiometer dial on a dimmer rack.
        norm_dist = dist / max_dist

        # Accumulator for light shafts, like a bus bar collecting current.
        rays = np.zeros_like(frame)

        # March from each pixel back toward the center and sample,
        # like tracing a conduit run back to the main panel.
        samples = 32
        for i in range(1, samples + 1):
            # Scale factor: how far back toward the center we look,
            # like zooming a lens to focus on the skylight.
            scale = float(i) / float(samples)

            # Coordinates scaled toward center,
            # like pulling a tape measure from the wall back to the electrical room.
            src_y = center_y + (dy * scale).astype(int)
            src_x = center_x + (dx * scale).astype(int)

            # Clamp to blueprint bounds so we don't look outside the lot.
            src_y = np.clip(src_y, 0, h - 1)
            src_x = np.clip(src_x, 0, w - 1)

            # Sample the frame at these traced coordinates.
            sample = frame[src_y, src_x]

            # Fade samples farther from center, like voltage drop along a long cord.
            fade = 1.0 - scale * 0.9

            # Wire this sample into the accumulator bus bar.
            rays += sample * fade

        # Average the accumulated samples like balancing loads across phases.
        rays = rays / float(samples)

        # Composite the rays onto the original image, scaled by the weight knob.
        result = frame + rays * weight * 0.15

        # Clamp to valid display voltage so we don't blow any fuses.
        return np.clip(result, 0.0, 1.0)

    # ======================================================================
    # DITHERING — Break color banding with ordered noise
    # ======================================================================

    @staticmethod
    def apply_dither(frame: np.ndarray, strength: float) -> np.ndarray:
        """
        Bayer matrix ordered dither to prevent banding.
        ELI5: When you paint a wall, you sometimes see lap marks where
        wet paint meets dry. Dithering taps the wall with a textured roller
        so the eye can't see those stripes.
        """
        # Measure the wall dimensions so we know how many tiles to lay.
        h, w = frame.shape[:2]

        # 4×4 Bayer tile pattern, like a predetermined stamp for concrete.
        bayer = np.array(
            [
                [0, 8, 2, 10],
                [12, 4, 14, 6],
                [3, 11, 1, 9],
                [15, 7, 13, 5],
            ],
            dtype=np.float32,
        )

        # Normalize to -0.5..0.5 like a balanced audio line centered on zero.
        bayer = bayer / 16.0 - 0.5

        # Tile across the whole wall like laying vinyl flooring in a grid.
        tile_y = (h // 4) + 1
        tile_x = (w // 4) + 1
        tiled = np.tile(bayer, (tile_y, tile_x))

        # Trim the excess at the edges like cutting wallpaper to fit.
        noise = tiled[:h, :w]

        # Inject the texture into the image, like adding a small hum to a
        # clean audio line so the quantization steps are inaudible.
        dithered = frame + noise[..., np.newaxis] * strength

        # Quantize to 8-bit like a DAC converting digital to analog,
        # then normalize back to the 0–1 voltage range.
        dithered = np.round(dithered * 255.0) / 255.0

        # Clamp to safe voltage levels for the display hardware.
        return np.clip(dithered, 0.0, 1.0)

    # ======================================================================
    # TONE MAPPING — Reinhard-ish + gamma correction
    # ======================================================================

    @staticmethod
    def apply_tone_mapping(frame: np.ndarray, exposure: float, gamma: float) -> np.ndarray:
        """
        Reinhard-ish tone mapping + gamma correction.
        ELI5: This is the master breaker panel before the power hits your house.
        It boosts weak signals (exposure), compresses spikes so nothing
        overheats (tone map), and shapes the curve so your eyes perceive
        it naturally (gamma).
        """
        # Boost the master dimmer like turning up a Lutron smart switch.
        exposed = frame * exposure

        # Reinhard compression: cap bright spikes like an HVAC limit switch
        # that prevents the furnace from overdriving the ductwork.
        mapped = exposed / (1.0 + exposed)

        # Gamma correction: shape the response curve like a smart dimmer that
        # knows human eyes don't perceive brightness in a straight line.
        corrected = np.power(np.maximum(mapped, 0.0), 1.0 / gamma)

        # Clamp to display-safe range like a surge protector cutting off overvoltage.
        return np.clip(corrected, 0.0, 1.0)

    # ======================================================================
    # FULL PIPELINE — Wire everything in series
    # ======================================================================

    @staticmethod
    def process(frame: np.ndarray, config: RenderConfig) -> np.ndarray:
        """
        Runs the full pipeline in order: bloom → sunrays → tone map → dither.
        ELI5: The image signal enters the breaker panel, flips through each
        circuit in order, and exits clean and ready for the TV wall.
        """
        # Upgrade to float32 like swapping thin residential wire for thick
        # commercial cable so it can carry more precision current.
        result = frame.astype(np.float32)

        # If the bloom dimmer is above zero, route through the glow circuit.
        if config.bloom_intensity > 0.0:
            result = PostProcessPipeline.apply_bloom(
                result, config.bloom_intensity, config.bloom_iterations
            )

        # If the sunrays dimmer is above zero, route through the god-rays circuit.
        if config.sunrays_weight > 0.0:
            result = PostProcessPipeline.apply_sunrays(result, config.sunrays_weight)

        # Always run tone mapping: it's the voltage regulator on the main line.
        result = PostProcessPipeline.apply_tone_mapping(
            result, config.exposure, config.gamma
        )

        # If the dither dimmer is above zero, route through the texture circuit.
        if config.dither_strength > 0.0:
            result = PostProcessPipeline.apply_dither(result, config.dither_strength)

        # Return the fully conditioned signal, ready for the display monitor.
        return result
