"""Builds the new section timeline (a list of `PlannedClip`s) from the
original song's detected structure, the chosen style, and the user's
remix/length parameters.

This is the "DJ edit arranger": it decides what a professional edit's
skeleton looks like — extended drums-only intro/outro for beatmatching, a
build into the first drop, one or more drop/breakdown cycles depending on
target length and intensity, and a matching outro — using the *original*
song's own sections as the raw material rather than inventing new music.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import cycle as _cycle

from ...schemas import LengthTarget, Section, SectionLabel
from .styles import StyleProfile

_LENGTH_TARGET_SECONDS = {
    LengthTarget.ORIGINAL: None,   # resolved from the source track's own duration
    LengthTarget.RADIO: 210,
    LengthTarget.CLUB: 330,
    LengthTarget.EXTENDED: 480,
}


@dataclass
class PlannedClip:
    role: str                          # e.g. "intro_drums_only", "verse_arranged", "build",
                                        # "build_synth", "drop_full", "breakdown_filtered",
                                        # "bridge", "outro_drums_only"
    source_section: Section | None      # None => purely synthesized material (DJ intro/outro)
    bar_count: int


def _drop_repeat_count(length_target: LengthTarget, intensity: float) -> int:
    base = {
        LengthTarget.ORIGINAL: 1,
        LengthTarget.RADIO: 1,
        LengthTarget.CLUB: 2,
        LengthTarget.EXTENDED: 3,
    }[length_target]
    if intensity > 0.75:
        base += 1
    return base


def build_arrangement(
    sections: list[Section],
    profile: StyleProfile,
    length_target: LengthTarget,
    intensity: float,
    original_duration_sec: float,
) -> list[PlannedClip]:
    if not sections:
        raise ValueError("Cannot build an arrangement from an empty structure")

    drops = [s for s in sections if s.label == SectionLabel.DROP] or [
        max(sections, key=lambda s: s.energy)
    ]
    builds = [s for s in sections if s.label == SectionLabel.BUILD]
    breakdowns = [s for s in sections if s.label == SectionLabel.BREAKDOWN]
    verses = [s for s in sections if s.label == SectionLabel.VERSE]
    bridges = [s for s in sections if s.label == SectionLabel.BRIDGE]

    plan: list[PlannedClip] = []

    plan.append(PlannedClip(role="intro_drums_only", source_section=None, bar_count=profile.intro_outro_bars))

    first_verse = verses[0] if verses else sections[0]
    plan.append(PlannedClip(role="verse_arranged", source_section=first_verse, bar_count=first_verse.bar_count))

    if builds:
        plan.append(PlannedClip(role="build", source_section=builds[0], bar_count=builds[0].bar_count))
    else:
        fallback_bars = min(8, max(4, first_verse.bar_count // 2))
        plan.append(PlannedClip(role="build_synth", source_section=first_verse, bar_count=fallback_bars))

    repeats = _drop_repeat_count(length_target, intensity)
    drop_cycle = list(_cycle(drops))
    verse_cycle = list(_cycle(verses)) if len(verses) > 1 else []

    for i in range(repeats):
        drop = drop_cycle[i]
        plan.append(PlannedClip(role="drop_full", source_section=drop, bar_count=drop.bar_count))

        if i < repeats - 1:
            if breakdowns:
                b = breakdowns[i % len(breakdowns)]
                plan.append(PlannedClip(role="breakdown_filtered", source_section=b, bar_count=b.bar_count))
            elif verse_cycle:
                v = verse_cycle[i + 1]
                plan.append(PlannedClip(role="verse_arranged", source_section=v, bar_count=v.bar_count))
            plan.append(PlannedClip(role="build_synth", source_section=drop, bar_count=4))

    if bridges and length_target in (LengthTarget.CLUB, LengthTarget.EXTENDED):
        bridge = bridges[0]
        plan.append(PlannedClip(role="bridge", source_section=bridge, bar_count=bridge.bar_count))
        plan.append(PlannedClip(role="build_synth", source_section=bridge, bar_count=4))
        plan.append(PlannedClip(role="drop_full", source_section=drop_cycle[repeats - 1], bar_count=drop_cycle[repeats - 1].bar_count))

    plan.append(PlannedClip(role="outro_drums_only", source_section=None, bar_count=profile.intro_outro_bars))

    return plan
