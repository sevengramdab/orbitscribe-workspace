"""
ACE-Step Prompt Generator — Autonomous Music Caption Generator
===============================================================
Like a creative director who instantly brainstorms unique track
concepts by mixing genres, moods, instruments, and production styles.

Works 100%% offline using a rich combinatorial template system.
Optionally augments with a local LLM (Ollama/LM Studio) if available.
"""

from __future__ import annotations

import random
from typing import List, Dict, Optional
from dataclasses import dataclass


# =============================================================================
# MUSIC VOCABULARY — The raw ingredients for creative prompts
# =============================================================================

GENRES = [
    "ambient", "electronic", "cinematic orchestral", "jazz", "classical",
    "lo-fi hip hop", "synthwave", "rock", "indie folk", "future bass",
    "techno", "house", "trap", "R&B", "soul", "funk", "disco",
    "progressive trance", "drum and bass", "dubstep", "reggae",
    "world fusion", "new age", "post-rock", "shoegaze", "trip-hop",
    "bossa nova", "bluegrass", "celtic", "medieval", "chiptune",
    "dark ambient", "idm", "glitch", "afrobeat", "latin",
]

MOODS = [
    "peaceful", "energetic", "melancholic", "uplifting", "dark",
    "dreamy", "nostalgic", "tense", "romantic", "mysterious",
    "euphoric", "haunting", "playful", "somber", "ethereal",
    "aggressive", "calm", "bittersweet", "whimsical", "brooding",
    "triumphant", "lonely", "warm", "cold", "introspective",
    "rebellious", "sensual", "spooky", "hopeful", "anxious",
]

INSTRUMENTS_LEAD = [
    "piano", "acoustic guitar", "electric guitar", "violin", "cello",
    "synthesizer", "flute", "saxophone", "trumpet", "harp",
    "sitar", "koto", "banjo", "mandolin", "oboe",
    "clarinet", " Rhodes piano", "Wurlitzer", "modular synth",
    "glass marimba", "hang drum", "kalimba", "theremin",
]

INSTRUMENTS_RHYTHM = [
    "drums", "percussion", "bass guitar", "upright bass", "synth bass",
    "tabla", "djembe", "bongos", "electronic drum machine",
    "frame drum", "shakers", "tambourine", "beatboxing",
]

INSTRUMENTS_PAD = [
    "pad synth", "string section", "choir", "ambient drones",
    "organ", "brass section", "woodwind section", "arpeggiated synth",
    "bells", "music box", "vocal harmonies", "field recordings",
]

TEMPO_DESCRIPTORS = [
    "slow and spacious", "mid-tempo", "upbeat", "fast-paced", "driving",
    "laid-back", "groovy", "pulsing", "floating", "breakneck",
    "meandering", "stomping", "skittering", "swinging", "marching",
]

PRODUCTION_STYLES = [
    "lo-fi with vinyl crackle", "cinematic and wide", "intimate and close-miked",
    "retro analog warmth", "futuristic and pristine", "reverb-drenched",
    "dry and punchy", "wall of sound", "minimal and sparse",
    "layered and complex", "raw and unpolished", "polished and glossy",
    "underground and gritty", "arena-sized", "bedroom producer aesthetic",
]

SETTINGS = [
    "rainy night in the city", "sunrise over mountains", "deep space station",
    "abandoned cathedral", "tropical beach at dusk", "neon-lit cyberpunk street",
    "medieval castle hall", "underwater reef", "desert at midnight",
    "jazz club at 2am", "futuristic botanical garden", "Arctic tundra",
    "bustling Tokyo intersection", "misty forest path", "cozy living room",
    "vast open plain", "subway tunnel", "ancient temple ruins",
    "floating cloud city", "subterranean cave system",
]

VOCAL_STYLES = [
    "soft female vocals", "powerful male vocals", "ethereal wordless vocals",
    "whispered spoken word", " gospel choir", "autotuned falsetto",
    "raspy blues singer", "operatic soprano", "rap verses",
    "layered vocal harmonies", "chanting", "breathy indie vocals",
    "no vocals — instrumental only",
]

STRUCTURES = [
    "building from a simple motif to a full arrangement",
    "verse-chorus with a dramatic bridge",
    "continuously evolving without repeating sections",
    "call and response between instruments",
    "A-B-A form with variations",
    "loop-based with gradual layering",
    "through-composed narrative arc",
    "intro-drop-breakdown-drop structure",
]


# =============================================================================
# TEMPLATES — How the ingredients are mixed into coherent captions
# =============================================================================

TEMPLATES = [
    "A {mood} {genre} track featuring {lead} and {rhythm}, {tempo} with {production}. {setting}.",
    "{genre} with {mood} undertones: {lead} carries the melody over {rhythm} and {pad}, {tempo}. {production}.",
    "An {mood} {genre} piece for {lead} and {pad}, {tempo}. Evokes {setting}. {production}.",
    "{tempo} {genre} — {lead} intertwined with {pad}, driven by {rhythm}. {mood} and {production}.",
    "{genre} soundscape: {mood} atmosphere created by {lead}, {pad}, and subtle {rhythm}. {setting}.",
    "A {mood} journey through {setting} via {genre} textures. {lead}, {rhythm}, {pad}. {tempo}, {production}.",
    "{production} {genre} track, {tempo}. {lead} melody with {pad} backing and {rhythm}. {mood} feeling.",
    "{genre} fusion blending {lead} and {rhythm} in a {mood}, {tempo} arrangement. {setting}. {production}.",
    "Cinematic {genre}: {lead} over swelling {pad}, punctuated by {rhythm}. {mood}, {tempo}. {setting}.",
    "{mood} {tempo} {genre}. {lead} takes center stage with {pad} and {rhythm}. {production}. {setting}.",
    "Experimental {genre} with {lead} and processed {pad}, {tempo} and {mood}. {production}. {setting}.",
    "{genre} for late nights: {mood} {lead}, deep {rhythm}, atmospheric {pad}. {tempo}. {setting}.",
]

VOCAL_TEMPLATES = [
    "A {mood} {genre} track with {vocal}, featuring {lead} and {rhythm}. {tempo}, {production}.",
    "{genre} ballad with {vocal}, accompanied by {lead} and {pad}. {mood}, {tempo}. {setting}.",
    "{vocal} over a {mood} {genre} arrangement of {lead}, {rhythm}, and {pad}. {tempo}. {production}.",
    "Upbeat {genre} with {vocal}, {lead} hooks, and driving {rhythm}. {mood}, {production}.",
    "{genre} track: {vocal} weave through layers of {lead} and {pad}, {tempo}. {mood}. {setting}.",
]


# =============================================================================
# GENERATOR
# =============================================================================

@dataclass
class GeneratedPrompt:
    caption: str
    genre: str
    mood: str
    bpm: int
    key: str
    duration: int
    has_vocals: bool


class PromptGenerator:
    """Generate creative music captions for ACE-Step."""

    KEYS_MAJOR = ["C major", "G major", "D major", "A major", "E major", "F major", "Bb major"]
    KEYS_MINOR = ["A minor", "E minor", "D minor", "G minor", "C minor", "F minor", "B minor"]

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def _pick(self, items: List[str]) -> str:
        return self.rng.choice(items)

    def _pick_n(self, items: List[str], n: int) -> List[str]:
        return self.rng.sample(items, min(n, len(items)))

    def _bpm_for_genre_mood(self, genre: str, mood: str) -> int:
        """Infer a sensible BPM from genre and mood."""
        base_bpm = 120

        # Genre adjustments
        genre_lower = genre.lower()
        if any(g in genre_lower for g in ["ambient", "new age", "medieval", "celtic"]):
            base_bpm = self.rng.randint(60, 90)
        elif any(g in genre_lower for g in ["lo-fi", "trip-hop", "downtempo", "bossa"]):
            base_bpm = self.rng.randint(70, 100)
        elif any(g in genre_lower for g in ["jazz", "blues", "soul", "funk", "R&B"]):
            base_bpm = self.rng.randint(85, 115)
        elif any(g in genre_lower for g in ["house", "techno", "trance", "disco", "funk"]):
            base_bpm = self.rng.randint(120, 130)
        elif any(g in genre_lower for g in ["drum and bass", "dubstep", "trap", "drum"]):
            base_bpm = self.rng.randint(140, 175)
        elif any(g in genre_lower for g in ["rock", "pop", "indie", "synthwave"]):
            base_bpm = self.rng.randint(110, 135)
        elif any(g in genre_lower for g in ["metal", "punk", "hardcore"]):
            base_bpm = self.rng.randint(140, 180)

        # Mood adjustments
        mood_lower = mood.lower()
        if any(m in mood_lower for m in ["calm", "peaceful", "somber", "melancholic", "lonely", "spacious"]):
            base_bpm = max(60, base_bpm - self.rng.randint(10, 25))
        elif any(m in mood_lower for m in ["energetic", "euphoric", "aggressive", "driving", "fast"]):
            base_bpm = min(180, base_bpm + self.rng.randint(10, 25))
        elif any(m in mood_lower for m in ["dark", "brooding", "mysterious", "tense"]):
            base_bpm = max(70, base_bpm - self.rng.randint(5, 15))

        return base_bpm

    def _key_for_mood(self, mood: str) -> str:
        """Pick a key that matches the mood."""
        mood_lower = mood.lower()
        if any(m in mood_lower for m in ["melancholic", "dark", "somber", "lonely", "brooding", "tense", "mysterious", "spooky"]):
            return self._pick(self.KEYS_MINOR)
        elif any(m in mood_lower for m in ["uplifting", "peaceful", "hopeful", "warm", "playful", "triumphant", "romantic"]):
            return self._pick(self.KEYS_MAJOR)
        else:
            return self._pick(self.KEYS_MAJOR + self.KEYS_MINOR)

    def _duration_for_genre(self, genre: str) -> int:
        """Pick a typical duration for the genre."""
        genre_lower = genre.lower()
        if any(g in genre_lower for g in ["ambient", "cinematic", "post-rock", "drone", "new age"]):
            return self.rng.choice([20, 25, 30])
        elif any(g in genre_lower for g in ["techno", "house", "trance", "drum and bass", "dubstep"]):
            return self.rng.choice([15, 20, 25])
        else:
            return self.rng.choice([10, 15, 20])

    def generate(self, include_vocals: Optional[bool] = None, custom_mood: Optional[str] = None,
                 custom_genre: Optional[str] = None) -> GeneratedPrompt:
        """Generate a complete music prompt with parameters."""
        genre = custom_genre or self._pick(GENRES)
        mood = custom_mood or self._pick(MOODS)
        has_vocals = include_vocals if include_vocals is not None else self.rng.random() < 0.4

        lead = self._pick(INSTRUMENTS_LEAD)
        rhythm = self._pick(INSTRUMENTS_RHYTHM)
        pad = self._pick(INSTRUMENTS_PAD)
        tempo = self._pick(TEMPO_DESCRIPTORS)
        production = self._pick(PRODUCTION_STYLES)
        setting = self._pick(SETTINGS)

        if has_vocals:
            vocal = self._pick(VOCAL_STYLES)
            template = self._pick(VOCAL_TEMPLATES)
            caption = template.format(
                mood=mood, genre=genre, lead=lead, rhythm=rhythm,
                pad=pad, tempo=tempo, production=production, setting=setting, vocal=vocal
            )
        else:
            template = self._pick(TEMPLATES)
            caption = template.format(
                mood=mood, genre=genre, lead=lead, rhythm=rhythm,
                pad=pad, tempo=tempo, production=production, setting=setting
            )

        # Clean up any double spaces
        caption = " ".join(caption.split())

        bpm = self._bpm_for_genre_mood(genre, mood)
        key = self._key_for_mood(mood)
        duration = self._duration_for_genre(genre)

        return GeneratedPrompt(
            caption=caption,
            genre=genre,
            mood=mood,
            bpm=bpm,
            key=key,
            duration=duration,
            has_vocals=has_vocals,
        )

    def generate_batch(self, count: int = 5) -> List[GeneratedPrompt]:
        """Generate multiple unique prompts."""
        return [self.generate() for _ in range(count)]


# Singleton
_generator: Optional[PromptGenerator] = None


def get_prompt_generator(seed: Optional[int] = None) -> PromptGenerator:
    global _generator
    if _generator is None or seed is not None:
        _generator = PromptGenerator(seed=seed)
    return _generator


def generate_prompt(include_vocals: Optional[bool] = None,
                    custom_mood: Optional[str] = None,
                    custom_genre: Optional[str] = None) -> Dict[str, any]:
    """Convenience function — returns a dict ready for JSON serialization."""
    g = get_prompt_generator()
    p = g.generate(include_vocals=include_vocals, custom_mood=custom_mood, custom_genre=custom_genre)
    return {
        "caption": p.caption,
        "genre": p.genre,
        "mood": p.mood,
        "bpm": p.bpm,
        "key": p.key,
        "duration": p.duration,
        "has_vocals": p.has_vocals,
    }
