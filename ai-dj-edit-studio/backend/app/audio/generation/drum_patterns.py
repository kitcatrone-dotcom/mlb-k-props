"""Per-genre-family rhythm pattern generators.

Each function returns a list of hits `{instrument, beat, velocity}` for a
single 4/4 bar (beat positions in the range [0, 4)), meant to be looped by
`dsp.mixer.render_pattern`. These are deliberately simple, readable patterns
that capture each genre's defining rhythmic signature rather than
over-fitted machine-learned patterns — this is exactly how a human producer
would sketch these grooves in a DAW's step sequencer.
"""
from __future__ import annotations


def four_on_the_floor(swing: float = 0.0, variant: str = "house") -> list[dict]:
    hits = [
        {"instrument": "kick", "beat": 0.0, "velocity": 1.0},
        {"instrument": "kick", "beat": 1.0, "velocity": 0.95},
        {"instrument": "kick", "beat": 2.0, "velocity": 1.0},
        {"instrument": "kick", "beat": 3.0, "velocity": 0.95},
        {"instrument": "clap", "beat": 1.0, "velocity": 0.85},
        {"instrument": "clap", "beat": 3.0, "velocity": 0.85},
    ]
    offbeats = [0.5, 1.5, 2.5, 3.5]
    for i, b in enumerate(offbeats):
        beat = b + (swing * 0.12 if i % 2 == 1 else 0.0)
        hits.append({"instrument": "hat_closed", "beat": beat, "velocity": 0.55})
    if variant == "tech_house":
        hits.append({"instrument": "hat_open", "beat": 3.75, "velocity": 0.5})
    return hits


def bass_house_pattern(swing: float = 0.05) -> list[dict]:
    hits = four_on_the_floor(swing=swing, variant="bass_house")
    # Bass House leans on a syncopated clap/perc accent ahead of beat 3.
    hits.append({"instrument": "clap", "beat": 2.75, "velocity": 0.6})
    return hits


def afro_house_pattern(swing: float = 0.12) -> list[dict]:
    hits = [
        {"instrument": "kick", "beat": 0.0, "velocity": 1.0},
        {"instrument": "kick", "beat": 2.0, "velocity": 0.9},
        {"instrument": "perc", "beat": 0.75, "velocity": 0.6},
        {"instrument": "perc", "beat": 1.5, "velocity": 0.7},
        {"instrument": "perc", "beat": 2.25 + swing * 0.1, "velocity": 0.55},
        {"instrument": "perc", "beat": 3.5, "velocity": 0.65},
        {"instrument": "clap", "beat": 1.0, "velocity": 0.5},
        {"instrument": "clap", "beat": 3.0, "velocity": 0.5},
    ]
    for b in (0.5, 1.75, 2.5, 3.75):
        hits.append({"instrument": "hat_closed", "beat": b, "velocity": 0.4})
    return hits


def melodic_house_pattern(swing: float = 0.03) -> list[dict]:
    # Sparser than club house — leaves room for the melodic/other stem.
    hits = [
        {"instrument": "kick", "beat": 0.0, "velocity": 0.95},
        {"instrument": "kick", "beat": 1.0, "velocity": 0.8},
        {"instrument": "kick", "beat": 2.0, "velocity": 0.95},
        {"instrument": "kick", "beat": 3.0, "velocity": 0.8},
        {"instrument": "clap", "beat": 2.0, "velocity": 0.6},
        {"instrument": "hat_closed", "beat": 1.5, "velocity": 0.35},
        {"instrument": "hat_closed", "beat": 3.5, "velocity": 0.35},
    ]
    return hits


def drum_and_bass_pattern(variation: int = 0) -> list[dict]:
    """A classic breakbeat skeleton: kick on 1, syncopated kick around the
    'and' of 2, snare on the backbeat, fast 16th hats. `variation` swaps in
    a couple of common fills so consecutive bars don't feel robotic."""
    hits = [
        {"instrument": "kick", "beat": 0.0, "velocity": 1.0},
        {"instrument": "clap", "beat": 1.5, "velocity": 0.9},   # "snare"
        {"instrument": "kick", "beat": 2.25, "velocity": 0.7},
        {"instrument": "clap", "beat": 3.5, "velocity": 0.9},
    ]
    if variation % 2 == 1:
        hits.append({"instrument": "kick", "beat": 2.75, "velocity": 0.55})
    for i in range(16):
        beat = i * 0.25
        if beat in (0.0, 1.5, 2.25, 3.5):
            continue
        hits.append({"instrument": "hat_closed", "beat": beat, "velocity": 0.3 if i % 2 == 0 else 0.2})
    return hits


def drum_fill(beats_per_bar: int = 4, intensity: float = 0.7) -> list[dict]:
    """A short fill for the last bar before a section change: a snare/clap
    roll building in density and velocity."""
    hits: list[dict] = []
    n_hits = int(6 + intensity * 10)
    for i in range(n_hits):
        beat = (i / n_hits) * beats_per_bar
        velocity = 0.4 + 0.5 * (i / n_hits)
        instrument = "clap" if i % 3 == 0 else "hat_closed"
        hits.append({"instrument": instrument, "beat": beat, "velocity": velocity})
    hits.append({"instrument": "kick", "beat": beats_per_bar - 0.01, "velocity": 1.0})
    return hits


PATTERN_BY_FAMILY = {
    "four_on_the_floor": four_on_the_floor,
    "bass_house": bass_house_pattern,
    "afro_house": afro_house_pattern,
    "melodic_house": melodic_house_pattern,
    "drum_and_bass": drum_and_bass_pattern,
}


def get_pattern(family: str, bars: int, swing: float = 0.0) -> list[dict]:
    """Returns a concatenated multi-bar pattern (beat positions offset per
    bar) built from the named single-bar generator, with light per-bar
    variation for D&B so it doesn't loop identically forever."""
    fn = PATTERN_BY_FAMILY.get(family, four_on_the_floor)
    all_hits: list[dict] = []
    for bar in range(bars):
        if family == "drum_and_bass":
            bar_hits = fn(variation=bar)
        elif fn is four_on_the_floor:
            bar_hits = fn(swing=swing)
        else:
            bar_hits = fn(swing=swing) if "swing" in fn.__code__.co_varnames else fn()
        for h in bar_hits:
            all_hits.append({**h, "beat": h["beat"] + bar * 4})
    return all_hits
