"""
Agent 5 — Visual Designer: Audio Frequency → Color Synthesis
=============================================================
Think of this module as the lighting designer at a rock concert.
Each frequency band is a different PAR can (stage light):
- Bass = deep reds and ambers (warm, powerful)
- Mids = greens and cyans (human voice range, natural)
- Treble = blues and violets (ice-cold, energetic)
We map amplitude to brightness and spectral centroid to hue shift,
exactly like a DMX console controlling RGBW LED fixtures.
"""

from __future__ import annotations

import time
from typing import Dict, Tuple

import numpy as np

from infinite_jukebox.architecture import AudioFrame, AudioChannel, MoodPreset


# =============================================================================
# HSL → RGB vector decoder  (like a DMX-to-LED-driver chip on a PCB)
# =============================================================================

def _hsl_to_rgb_vec(hsl: np.ndarray) -> np.ndarray:
    """
    Convert a batch of HSL tuples into RGB — like a PLC output card
    translating 0–10 V control signals into actual red/green/blue
    PWM duty cycles for a strip of RGB tape light.
    """
    # Pull the hue wire off the ribbon cable — this is the color wheel position.
    h = hsl[:, 0]
    # Pull the saturation wire — how much grey is mixed into the color.
    s = hsl[:, 1]
    # Pull the lightness wire — how bright the fixture is overall.
    l = hsl[:, 2]
    # Build a greyscale fallback voltage for when saturation is zero.
    grey = np.stack([l, l, l], axis=1)
    # Calculate the intermediate 'q' voltage like a Lutron dimmer curve.
    q = np.where(l < 0.5, l * (1.0 + s), l + s - l * s)
    # Calculate 'p' as the complementary shadow voltage — the neutral leg.
    p = 2.0 * l - q
    # This helper is the interpolation slider inside a Chauvet RGB mixer.
    def _channel(t: np.ndarray) -> np.ndarray:
        # Wrap the hue dial around so 0° and 360° touch the same contact.
        t = np.where(t < 0.0, t + 1.0, t)
        # Snap back if we overshoot past 360° on the rotary switch.
        t = np.where(t > 1.0, t - 1.0, t)
        # First ramp segment on the 0–10 V RGB triangle wave.
        seg1 = p + (q - p) * 6.0 * t
        # Second segment holds at peak voltage like a flat-top on an oscilloscope.
        seg2 = q
        # Third segment ramps back down to the shadow voltage.
        seg3 = p + (q - p) * (2.0 / 3.0 - t) * 6.0
        # Pick the correct segment with nested relays on a multi-throw switch.
        return np.where(
            t < 1.0 / 6.0,
            seg1,
            np.where(t < 1.0 / 2.0, seg2, np.where(t < 2.0 / 3.0, seg3, p)),
        )
    # Run the red channel through the decoder with a +120° phase lead.
    r = _channel(h + 1.0 / 3.0)
    # Run the green channel at zero phase offset — right on time.
    g = _channel(h)
    # Run the blue channel with a -120° phase lag.
    b = _channel(h - 1.0 / 3.0)
    # Bundle the three PWM signals back onto one ribbon cable.
    rgb = np.stack([r, g, b], axis=1)
    # Where saturation was zero, bypass the decoder and pass grey straight through.
    zero_sat = s == 0.0
    rgb[zero_sat] = grey[zero_sat]
    # Clamp every wire to 0–1 V so the LED drivers don't burn out.
    return np.clip(rgb, 0.0, 1.0)


class AudioColorMapper:
    """
    Converts live FFT frames into per-channel RGB colors and a global
    density field prescription. Like a Philips Hue Entertainment zone
    that syncs every bulb in the room to the beat of the music.
    """

    def __init__(self) -> None:
        # Start with the AMBIENT scene as the default lighting schedule.
        self._mood = MoodPreset.AMBIENT
        # Create a blank set of DMX gel presets we can swap out later.
        self._base_hsl = np.zeros((5, 3), dtype=np.float32)
        # Create the "hot" side of each gel — what the color becomes at peak.
        self._hot_hsl = np.zeros((5, 3), dtype=np.float32)
        # Load the initial gel colors into the fixture memory.
        self._build_palette()

    def apply_mood_preset(self, preset: MoodPreset) -> None:
        # Swap the whole lighting scene like pressing a Lutron keypad button.
        self._mood = preset
        # Recompute the gel colors for every PAR can in the rig.
        self._build_palette()

    def _build_palette(self) -> None:
        # If the scene is AMBIENT, load cool blues and purples.
        if self._mood == MoodPreset.AMBIENT:
            # BASS gets a deep midnight-blue gel.
            self._base_hsl[0] = [0.72, 0.60, 0.15]
            # At peak, the bass fixture shifts toward violet.
            self._hot_hsl[0] = [0.75, 0.90, 0.35]
            # LOW_MID gets a royal-blue gel.
            self._base_hsl[1] = [0.60, 0.50, 0.20]
            # At peak, it blooms into bright sky blue.
            self._hot_hsl[1] = [0.65, 0.85, 0.40]
            # MID gets a cyan-tinged blue gel.
            self._base_hsl[2] = [0.55, 0.50, 0.25]
            # At peak, it glows aqua like an illuminated swimming pool.
            self._hot_hsl[2] = [0.58, 0.80, 0.45]
            # HIGH_MID gets a periwinkle gel.
            self._base_hsl[3] = [0.70, 0.55, 0.30]
            # At peak, it becomes a bright lavender.
            self._hot_hsl[3] = [0.78, 0.90, 0.50]
            # TREBLE gets a violet gel.
            self._base_hsl[4] = [0.78, 0.60, 0.20]
            # At peak, it shifts to magenta like a neon sign.
            self._hot_hsl[4] = [0.85, 0.95, 0.40]
        # If the scene is ENERGETIC, load warm oranges and reds.
        elif self._mood == MoodPreset.ENERGETIC:
            # BASS gets a deep ruby-red gel.
            self._base_hsl[0] = [0.00, 0.70, 0.15]
            # At peak, it flares into bright scarlet.
            self._hot_hsl[0] = [0.02, 0.95, 0.35]
            # LOW_MID gets a burnt-orange gel.
            self._base_hsl[1] = [0.08, 0.70, 0.25]
            # At peak, it turns into tangerine.
            self._hot_hsl[1] = [0.10, 0.95, 0.45]
            # MID gets a warm amber gel.
            self._base_hsl[2] = [0.12, 0.70, 0.30]
            # At peak, it glows like a sodium street lamp.
            self._hot_hsl[2] = [0.14, 0.95, 0.50]
            # HIGH_MID gets a golden-yellow gel.
            self._base_hsl[3] = [0.16, 0.70, 0.35]
            # At peak, it becomes pure incandescent filament white-yellow.
            self._hot_hsl[3] = [0.18, 0.95, 0.55]
            # TREBLE gets a hot coral gel.
            self._base_hsl[4] = [0.05, 0.80, 0.25]
            # At peak, it flares into a daylight-balanced red.
            self._hot_hsl[4] = [0.08, 1.00, 0.45]
        # If the scene is DARK, load desaturated greys with red accents.
        elif self._mood == MoodPreset.DARK:
            # BASS gets a dark rust gel — barely any pigment.
            self._base_hsl[0] = [0.00, 0.30, 0.08]
            # At peak, the rust becomes a dull ember glow.
            self._hot_hsl[0] = [0.00, 0.60, 0.15]
            # LOW_MID is essentially charcoal with zero saturation.
            self._base_hsl[1] = [0.00, 0.00, 0.08]
            # At peak, it barely warms to dark ash grey.
            self._hot_hsl[1] = [0.00, 0.10, 0.15]
            # MID is a medium charcoal.
            self._base_hsl[2] = [0.00, 0.00, 0.12]
            # At peak, it lightens to warm grey concrete.
            self._hot_hsl[2] = [0.00, 0.05, 0.20]
            # HIGH_MID is another charcoal variant.
            self._base_hsl[3] = [0.00, 0.00, 0.10]
            # At peak, it shifts to slightly reddish grey.
            self._hot_hsl[3] = [0.00, 0.08, 0.18]
            # TREBLE gets a dark blood-red accent gel.
            self._base_hsl[4] = [0.00, 0.50, 0.08]
            # At peak, it glows like a dim exit sign.
            self._hot_hsl[4] = [0.00, 0.80, 0.15]
        # If the scene is CHAOS, spin the color wheel like a disco ball.
        elif self._mood == MoodPreset.CHAOS:
            # Read the current wall-clock time to drive the spinning wheel.
            now = time.time()
            # Compute how many full color-wheel rotations have happened.
            spin = (now * 0.5) % 1.0
            # Fixture 0 starts at red on the wheel and spins.
            self._base_hsl[0] = [(0.00 + spin) % 1.0, 0.80, 0.20]
            # Its hot side is a little further around the rainbow.
            self._hot_hsl[0] = [(0.05 + spin) % 1.0, 1.00, 0.50]
            # Fixture 1 starts at yellow-green.
            self._base_hsl[1] = [(0.20 + spin) % 1.0, 0.80, 0.20]
            # Its hot side moves toward pure green.
            self._hot_hsl[1] = [(0.25 + spin) % 1.0, 1.00, 0.50]
            # Fixture 2 starts at cyan.
            self._base_hsl[2] = [(0.40 + spin) % 1.0, 0.80, 0.20]
            # Its hot side moves toward pure cyan.
            self._hot_hsl[2] = [(0.45 + spin) % 1.0, 1.00, 0.50]
            # Fixture 3 starts at blue.
            self._base_hsl[3] = [(0.60 + spin) % 1.0, 0.80, 0.20]
            # Its hot side moves toward pure blue.
            self._hot_hsl[3] = [(0.65 + spin) % 1.0, 1.00, 0.50]
            # Fixture 4 starts at magenta.
            self._base_hsl[4] = [(0.80 + spin) % 1.0, 0.80, 0.20]
            # Its hot side moves toward pure magenta.
            self._hot_hsl[4] = [(0.85 + spin) % 1.0, 1.00, 0.50]
        # If the scene is MINIMAL, keep everything monochrome white/cyan.
        elif self._mood == MoodPreset.MINIMAL:
            # BASS is a dim cool white.
            self._base_hsl[0] = [0.00, 0.00, 0.20]
            # At peak, it brightens to pure white like a frosted LED bulb.
            self._hot_hsl[0] = [0.00, 0.00, 0.50]
            # LOW_MID is a pale cyan.
            self._base_hsl[1] = [0.50, 0.30, 0.25]
            # At peak, it becomes a brighter spa-blue.
            self._hot_hsl[1] = [0.50, 0.60, 0.55]
            # MID is the main cyan accent.
            self._base_hsl[2] = [0.50, 0.50, 0.30]
            # At peak, it becomes a vivid Tiffany-box cyan.
            self._hot_hsl[2] = [0.50, 0.80, 0.60]
            # HIGH_MID mirrors LOW_MID for symmetry.
            self._base_hsl[3] = [0.50, 0.30, 0.25]
            # At peak, it also brightens to spa-blue.
            self._hot_hsl[3] = [0.50, 0.60, 0.55]
            # TREBLE mirrors BASS for symmetry.
            self._base_hsl[4] = [0.00, 0.00, 0.20]
            # At peak, it brightens to pure white.
            self._hot_hsl[4] = [0.00, 0.00, 0.50]

    def map_frame(
        self, audio_frame: AudioFrame
    ) -> Dict[AudioChannel, Tuple[float, float, float]]:
        # Grab the spectrum analyzer's 512-bin output like reading
        # voltage levels off a multi-channel power-quality meter.
        bins = audio_frame.frequency_bins
        # Count how many breaker positions are on the meter's face
        # so we know how to split them into the five audio circuits.
        n_bins = float(len(bins))
        # BASS covers the first 8 % of breakers — like the heavy-motor
        # sub-panel that only runs compressors and pumps.
        lo_bass = int(0.0 * n_bins)
        # BASS ends right before the LOW_MID section starts.
        hi_bass = int(0.08 * n_bins)
        # LOW_MID is the next bank — general lighting branch circuits.
        lo_low = int(0.08 * n_bins)
        # LOW_MID ends where the MID bank begins.
        hi_low = int(0.16 * n_bins)
        # MID is the outlet circuit bank in the middle of the panel.
        lo_mid = int(0.16 * n_bins)
        # MID ends where the HVAC control bank begins.
        hi_mid = int(0.35 * n_bins)
        # HIGH_MID is the HVAC control circuit bank near the top.
        lo_hm = int(0.35 * n_bins)
        # HIGH_MID ends where the low-voltage comm bank begins.
        hi_hm = int(0.60 * n_bins)
        # TREBLE is the low-voltage data/comm bank at the very end.
        lo_tr = int(0.60 * n_bins)
        # TREBLE runs all the way to the last breaker position.
        hi_tr = int(1.00 * n_bins)
        # Measure average current on the bass branch with a clamp meter.
        e0 = float(bins[lo_bass:hi_bass].mean()) if hi_bass > lo_bass else 0.0
        # Measure average current on the low-mid branch circuit.
        e1 = float(bins[lo_low:hi_low].mean()) if hi_low > lo_low else 0.0
        # Measure average current on the mid branch circuit.
        e2 = float(bins[lo_mid:hi_mid].mean()) if hi_mid > lo_mid else 0.0
        # Measure average current on the high-mid branch circuit.
        e3 = float(bins[lo_hm:hi_hm].mean()) if hi_hm > lo_hm else 0.0
        # Measure average current on the treble branch circuit.
        e4 = float(bins[lo_tr:hi_tr].mean()) if hi_tr > lo_tr else 0.0
        # Stack the five meter readings into a single bus bar so we
        # can process them all at once like a PLC scanning its inputs.
        energies = np.array([e0, e1, e2, e3, e4], dtype=np.float32)
        # Convert raw current to a 0–100 % dimmer level, but never let
        # the breaker trip past 100 % — clamp it like a current limiter.
        t = np.clip(energies * 3.0, 0.0, 1.0)
        # If the mood is CHAOS, the gels are spinning — refresh the DMX patch.
        if self._mood == MoodPreset.CHAOS:
            # Reload the color wheel position so the rainbow keeps rotating.
            self._build_palette()
        # Reshape the dimmer levels so they can drive each HSL channel separately.
        t = t.reshape(-1, 1)
        # Interpolate hue between the base gel and the hot gel like a
        # fader on a lighting desk sliding from scene A to scene B.
        h = self._base_hsl[:, 0] + (self._hot_hsl[:, 0] - self._base_hsl[:, 0]) * t[:, 0]
        # Interpolate saturation the same way — more energy means more vivid pigment.
        s = self._base_hsl[:, 1] + (self._hot_hsl[:, 1] - self._base_hsl[:, 1]) * t[:, 0]
        # Interpolate lightness — louder sounds turn the dimmer up higher.
        l = self._base_hsl[:, 2] + (self._hot_hsl[:, 2] - self._base_hsl[:, 2]) * t[:, 0]
        # Stack hue, saturation, and lightness back into one cable per fixture.
        hsl = np.stack([h, s, l], axis=1)
        # Send the HSL values through the DMX decoder to get actual RGB voltages.
        rgb = _hsl_to_rgb_vec(hsl)
        # Pull the red voltage off the first output terminal.
        r = rgb[:, 0]
        # Pull the green voltage off the second output terminal.
        g = rgb[:, 1]
        # Pull the blue voltage off the third output terminal.
        b = rgb[:, 2]
        # Build the final DMX packet as a dictionary mapping each circuit
        # breaker to its own RGB triple — one address per light fixture.
        return {
            AudioChannel.BASS: (float(r[0]), float(g[0]), float(b[0])),
            AudioChannel.LOW_MID: (float(r[1]), float(g[1]), float(b[1])),
            AudioChannel.MID: (float(r[2]), float(g[2]), float(b[2])),
            AudioChannel.HIGH_MID: (float(r[3]), float(g[3]), float(b[3])),
            AudioChannel.TREBLE: (float(r[4]), float(g[4]), float(b[4])),
        }

    def map_spectral_centroid(self, centroid: float) -> Tuple[float, float, float]:
        # Clamp the centroid to 0–1 just like a thermostat limit switch.
        c = float(np.clip(centroid, 0.0, 1.0))
        # Map the centroid to a hue from warm red (0.0) to cool blue (0.6).
        hue = c * 0.6
        # Use high saturation so the tint is visible — like a strong gel.
        sat = 0.85
        # Keep lightness moderate so it doesn't wash out the whole stage.
        lit = 0.45
        # Package the HSL values into a single decoder input for one fixture.
        hsl = np.array([[hue, sat, lit]], dtype=np.float32)
        # Run the spectral tint through the DMX-to-RGB decoder chip.
        rgb = _hsl_to_rgb_vec(hsl)
        # Read the red voltage off the first output terminal.
        r = float(rgb[0, 0])
        # Read the green voltage off the second output terminal.
        g = float(rgb[0, 1])
        # Read the blue voltage off the third output terminal.
        b = float(rgb[0, 2])
        # Return the RGB triple as a tuple — the final wire labels.
        return (r, g, b)

    def get_negative_space_color(self) -> Tuple[float, float, float]:
        # If the mood is AMBIENT, the background is a very dark midnight blue.
        if self._mood == MoodPreset.AMBIENT:
            # Mix a tiny amount of blue into near-black like a night-light.
            hsl = np.array([[0.65, 0.50, 0.04]], dtype=np.float32)
        # If the mood is ENERGETIC, the background is a very dark warm grey.
        elif self._mood == MoodPreset.ENERGETIC:
            # Mix a hint of orange into the dark like a dying ember.
            hsl = np.array([[0.08, 0.40, 0.05]], dtype=np.float32)
        # If the mood is DARK, the background is almost black like a blackout.
        elif self._mood == MoodPreset.DARK:
            # Turn all channels down to barely a glow — like a theater during intermission.
            hsl = np.array([[0.00, 0.00, 0.02]], dtype=np.float32)
        # If the mood is CHAOS, the background is a dark neutral grey.
        elif self._mood == MoodPreset.CHAOS:
            # Use no hue at all — just a dim grey so the rainbow pops.
            hsl = np.array([[0.00, 0.00, 0.06]], dtype=np.float32)
        # If the mood is MINIMAL, the background is a very dark cool grey.
        elif self._mood == MoodPreset.MINIMAL:
            # Add a trace of cyan so it feels like moonlight on snow.
            hsl = np.array([[0.50, 0.20, 0.04]], dtype=np.float32)
        # Otherwise default to pure black like all breakers being off.
        else:
            # Cut power completely — total blackout.
            hsl = np.array([[0.00, 0.00, 0.00]], dtype=np.float32)
        # Convert the background HSL to RGB through the same decoder.
        rgb = _hsl_to_rgb_vec(hsl)
        # Extract the red component from the decoder output.
        r = float(rgb[0, 0])
        # Extract the green component from the decoder output.
        g = float(rgb[0, 1])
        # Extract the blue component from the decoder output.
        b = float(rgb[0, 2])
        # Return the negative-space RGB triple — the "room lights off" color.
        return (r, g, b)
