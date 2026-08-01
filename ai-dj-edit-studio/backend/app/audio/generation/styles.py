"""Style profiles: the tunable knobs that make a "House" edit sound
different from a "Drum & Bass" edit out of the same source stems.

Each `StyleProfile` is data, not behavior — the generic arrangement/engine
code reads these values to decide tempo, drum pattern family, kick tone,
swing, filter-sweep character, riser character, and how many bars of
drums-only intro/outro to build (a DJ needs enough clean beats to
beatmatch into/out of the track).
"""
from __future__ import annotations

from dataclasses import dataclass

from ...schemas import EditStyle


@dataclass(frozen=True)
class StyleProfile:
    style: EditStyle
    display_name: str
    bpm_range: tuple[float, float]
    default_bpm: float
    pattern_family: str          # key into drum_patterns.PATTERN_BY_FAMILY
    kick_tone: str                # key into dsp.synth.synth_kick's `tone`
    swing: float                  # 0-1
    riser_kind: str                # "noise" | "tonal"
    breakdown_filter_floor_hz: float   # how dark the breakdown lowpass gets
    intro_outro_bars: int
    drum_layer_gain: float        # how loud the synthesized layer sits under the original drum stem
    bass_emphasis: float          # gain applied to the bass stem (sub-heavy styles push this up)


STYLE_PROFILES: dict[EditStyle, StyleProfile] = {
    EditStyle.HOUSE: StyleProfile(
        style=EditStyle.HOUSE,
        display_name="House",
        bpm_range=(120, 126),
        default_bpm=124,
        pattern_family="four_on_the_floor",
        kick_tone="house",
        swing=0.04,
        riser_kind="noise",
        breakdown_filter_floor_hz=350,
        intro_outro_bars=16,
        drum_layer_gain=0.55,
        bass_emphasis=1.0,
    ),
    EditStyle.TECH_HOUSE: StyleProfile(
        style=EditStyle.TECH_HOUSE,
        display_name="Tech House",
        bpm_range=(124, 128),
        default_bpm=126,
        pattern_family="four_on_the_floor",
        kick_tone="tight",
        swing=0.08,
        riser_kind="noise",
        breakdown_filter_floor_hz=300,
        intro_outro_bars=16,
        drum_layer_gain=0.65,
        bass_emphasis=1.05,
    ),
    EditStyle.DRUM_AND_BASS: StyleProfile(
        style=EditStyle.DRUM_AND_BASS,
        display_name="Drum & Bass",
        bpm_range=(168, 176),
        default_bpm=174,
        pattern_family="drum_and_bass",
        kick_tone="break",
        swing=0.0,
        riser_kind="tonal",
        breakdown_filter_floor_hz=250,
        intro_outro_bars=16,
        drum_layer_gain=0.8,
        bass_emphasis=1.2,
    ),
    EditStyle.AFRO_HOUSE: StyleProfile(
        style=EditStyle.AFRO_HOUSE,
        display_name="Afro House",
        bpm_range=(118, 123),
        default_bpm=121,
        pattern_family="afro_house",
        kick_tone="house",
        swing=0.14,
        riser_kind="noise",
        breakdown_filter_floor_hz=400,
        intro_outro_bars=16,
        drum_layer_gain=0.5,
        bass_emphasis=0.95,
    ),
    EditStyle.MELODIC_HOUSE: StyleProfile(
        style=EditStyle.MELODIC_HOUSE,
        display_name="Melodic House",
        bpm_range=(120, 124),
        default_bpm=122,
        pattern_family="melodic_house",
        kick_tone="house",
        swing=0.03,
        riser_kind="tonal",
        breakdown_filter_floor_hz=500,
        intro_outro_bars=24,
        drum_layer_gain=0.4,
        bass_emphasis=0.9,
    ),
    EditStyle.BASS_HOUSE: StyleProfile(
        style=EditStyle.BASS_HOUSE,
        display_name="Bass House",
        bpm_range=(124, 128),
        default_bpm=126,
        pattern_family="bass_house",
        kick_tone="tight",
        swing=0.05,
        riser_kind="noise",
        breakdown_filter_floor_hz=280,
        intro_outro_bars=16,
        drum_layer_gain=0.7,
        bass_emphasis=1.3,
    ),
    EditStyle.EXTENDED_CLUB_EDIT: StyleProfile(
        style=EditStyle.EXTENDED_CLUB_EDIT,
        display_name="Extended Club Edit",
        bpm_range=(120, 128),
        default_bpm=124,
        pattern_family="four_on_the_floor",
        kick_tone="house",
        swing=0.04,
        riser_kind="noise",
        breakdown_filter_floor_hz=350,
        intro_outro_bars=32,
        drum_layer_gain=0.5,
        bass_emphasis=1.0,
    ),
}


def resolve_target_bpm(profile: StyleProfile, requested_bpm: float | None, detected_bpm: float) -> float:
    """Picks the final render BPM: an explicit user request wins (clamped to
    a sane +/-20% of the style's range so e.g. asking for 70 BPM on a D&B
    edit doesn't produce something unusable), otherwise the style's default,
    nudged toward the detected BPM if it's already close (so a track
    that's naturally 123 BPM House stays at 123 rather than being force-
    stretched to exactly 124)."""
    lo, hi = profile.bpm_range
    if requested_bpm:
        return float(min(max(requested_bpm, lo * 0.8), hi * 1.2))

    if lo <= detected_bpm <= hi:
        return float(detected_bpm)

    return profile.default_bpm
