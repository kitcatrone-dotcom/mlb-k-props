"""EditGenerationEngine: turns separated stems + analysis + a
`GenerateRequest` into a fully rendered DJ edit.

Core principle from the product spec: the vocal stem's original timing is
preserved (it is only tempo/pitch-matched as a whole, never chopped or
reordered — whichever slice of the vocal a section contains plays through
exactly as sung), while the drums/bass/other stems are rebuilt: re-arranged
into a new section order, layered with genre-appropriate synthesized
percussion, filtered for breakdowns/builds, and bookended with a DJ-ready
extended drums-only intro/outro.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from ... import config
from ...schemas import AnalysisResult, GenerateRequest, GenerateResult, Section, TimelineClip
from ...storage import Session, new_edit_id
from ..io import load_stereo, write_stereo
from .arrangement import PlannedClip, build_arrangement
from .drum_patterns import drum_fill, get_pattern
from .dsp.fx import add_reverb, equal_power_crossfade, filter_sweep, gain_ramp
from .dsp.mixer import loop_to_length, mix_at, new_buffer, normalize_peak, render_pattern, to_stereo
from .dsp.synth import synth_clap, synth_hat, synth_impact, synth_kick, synth_perc, synth_riser
from .dsp.timestretch import stretch_rate_for_bpm, time_stretch, time_to_stretched
from .styles import STYLE_PROFILES, StyleProfile, resolve_target_bpm


def _build_sample_bank(sr: int, profile: StyleProfile) -> dict[str, np.ndarray]:
    return {
        "kick": synth_kick(sr, tone=profile.kick_tone),
        "clap": synth_clap(sr),
        "hat_closed": synth_hat(sr, open_=False),
        "hat_open": synth_hat(sr, open_=True),
        "perc": synth_perc(sr),
    }


def _slice(buf: np.ndarray, sr: int, start_sec: float, end_sec: float) -> np.ndarray:
    start = max(0, int(start_sec * sr))
    end = min(buf.shape[0], int(end_sec * sr))
    if end <= start:
        return new_buffer(0)
    return buf[start:end]


def _section_range_stretched(section: Section, rate: float) -> tuple[float, float]:
    return time_to_stretched(section.start, rate), time_to_stretched(section.end, rate)


def _clip_time_range(clip: PlannedClip, rate: float, bar_length_target: float) -> tuple[float, float]:
    start, end = _section_range_stretched(clip.source_section, rate)
    if clip.role in ("build", "build_synth"):
        wanted = clip.bar_count * bar_length_target
        start = max(start, end - wanted)
    return start, end


def _render_synth_only_clip(
    clip: PlannedClip,
    stretched: dict[str, np.ndarray],
    sr: int,
    bar_length_target: float,
    beats_per_bar: int,
    profile: StyleProfile,
    sample_bank: dict[str, np.ndarray],
    energy: float,
) -> np.ndarray:
    pattern = get_pattern(profile.pattern_family, bars=1, swing=profile.swing)
    drum_layer = render_pattern(pattern, bar_length_target, clip.bar_count, sr, sample_bank, beats_per_bar)

    loop_source_len = min(len(stretched["bass"]), int(bar_length_target * 4 * sr) or 1)
    bass_loop_src = stretched["bass"][:loop_source_len] if loop_source_len else new_buffer(0)
    bass_loop = loop_to_length(bass_loop_src, drum_layer.shape[0]) * 0.5 * profile.bass_emphasis

    clip_audio = drum_layer * (0.6 + 0.4 * energy) + bass_loop
    if clip.role == "intro_drums_only":
        clip_audio = gain_ramp(clip_audio, 0.05, 1.0)
    else:
        clip_audio = gain_ramp(clip_audio, 1.0, 0.0)
    return normalize_peak(clip_audio, 0.85)


def _render_source_clip(
    clip: PlannedClip,
    stretched: dict[str, np.ndarray],
    sr: int,
    rate: float,
    bar_length_target: float,
    beats_per_bar: int,
    profile: StyleProfile,
    sample_bank: dict[str, np.ndarray],
    intensity: float,
    energy: float,
) -> np.ndarray:
    start, end = _clip_time_range(clip, rate, bar_length_target)
    vocals = to_stereo(_slice(stretched["vocals"], sr, start, end))
    other = to_stereo(_slice(stretched["other"], sr, start, end))
    bass = to_stereo(_slice(stretched["bass"], sr, start, end)) * profile.bass_emphasis
    drums = to_stereo(_slice(stretched["drums"], sr, start, end))

    n = min(x.shape[0] for x in (vocals, other, bass, drums))
    if n <= 0:
        return new_buffer(0)
    vocals, other, bass, drums = (x[:n] for x in (vocals, other, bass, drums))

    n_bars = max(1, clip.bar_count)
    pattern = get_pattern(profile.pattern_family, bars=n_bars, swing=profile.swing)
    synth_layer = render_pattern(pattern, bar_length_target, n_bars, sr, sample_bank, beats_per_bar)
    synth_layer = loop_to_length(synth_layer, n)

    drum_gain, synth_gain = 1.0, profile.drum_layer_gain * 0.6
    if clip.role == "breakdown_filtered":
        drum_gain, synth_gain = 0.25, 0.0
    elif clip.role == "drop_full":
        drum_gain = 1.0
        synth_gain = profile.drum_layer_gain * (0.7 + 0.6 * energy)
    elif clip.role in ("build", "build_synth"):
        synth_gain = profile.drum_layer_gain

    mix = vocals + other + bass + drums * drum_gain + synth_layer * synth_gain

    if clip.role in ("build", "build_synth"):
        top = 400 + 3200 * intensity
        mix = filter_sweep(mix, sr, start_hz=40, end_hz=top, btype="highpass")
        riser = synth_riser(sr, duration=n / sr, kind=profile.riser_kind) * (0.25 + 0.5 * energy)
        mix = mix + to_stereo(np.resize(riser, n))

        fill_len = int(bar_length_target * sr)
        if n > fill_len > 0:
            fill_pattern = drum_fill(beats_per_bar, intensity)
            fill_audio = render_pattern(fill_pattern, bar_length_target, 1, sr, sample_bank, beats_per_bar)
            mix = mix_at(mix, n - fill_len, fill_audio, gain=0.8)

    elif clip.role == "drop_full":
        impact = synth_impact(sr, duration=min(1.2, n / sr))
        mix = mix_at(mix, 0, impact, gain=0.4 + 0.4 * energy)

    elif clip.role == "breakdown_filtered":
        floor_hz = profile.breakdown_filter_floor_hz
        mix = filter_sweep(mix, sr, start_hz=floor_hz * 3, end_hz=floor_hz, btype="lowpass")
        mix = add_reverb(mix, sr, room_size=0.5 + 0.3 * intensity, wet=0.3)

    return mix.astype(np.float32)


def _render_clip(
    clip: PlannedClip,
    stretched: dict[str, np.ndarray],
    sr: int,
    rate: float,
    bar_length_target: float,
    beats_per_bar: int,
    profile: StyleProfile,
    sample_bank: dict[str, np.ndarray],
    intensity: float,
    energy: float,
) -> np.ndarray:
    if clip.source_section is None:
        return _render_synth_only_clip(clip, stretched, sr, bar_length_target, beats_per_bar, profile, sample_bank, energy)
    return _render_source_clip(
        clip, stretched, sr, rate, bar_length_target, beats_per_bar, profile, sample_bank, intensity, energy
    )


def generate_edit(
    session: Session,
    analysis: AnalysisResult,
    request: GenerateRequest,
    report: Callable[[float, str], None] | None = None,
) -> GenerateResult:
    def _report(p: float, m: str) -> None:
        if report:
            report(p, m)

    profile = STYLE_PROFILES[request.style]
    target_bpm = resolve_target_bpm(profile, request.target_bpm, analysis.tempo.bpm)
    rate = stretch_rate_for_bpm(analysis.tempo.bpm, target_bpm)

    _report(0.05, "loading stems")
    stems: dict[str, np.ndarray] = {}
    working_sr = config.WORKING_SAMPLE_RATE
    for name in config.STEM_NAMES:
        data, working_sr = load_stereo(session.stem_path(name))
        stems[name] = data

    _report(0.15, "time-stretching to target tempo")
    stretched = {name: time_stretch(buf, working_sr, rate) for name, buf in stems.items()}

    bar_length_target = max(time_to_stretched(analysis.structure.bar_length_sec, rate), 0.1)
    beats_per_bar = analysis.time_signature.numerator or 4

    plan = build_arrangement(
        analysis.structure.sections, profile, request.length_target, request.intensity, analysis.duration_sec
    )
    sample_bank = _build_sample_bank(working_sr, profile)

    _report(0.25, "rendering arrangement")
    rendered_clips: list[np.ndarray] = []
    timeline: list[TimelineClip] = []
    cursor_sec = 0.0
    n_clips = max(len(plan), 1)

    for i, clip in enumerate(plan):
        clip_audio = _render_clip(
            clip, stretched, working_sr, rate, bar_length_target, beats_per_bar,
            profile, sample_bank, request.intensity, request.energy,
        )
        if clip_audio.shape[0] == 0:
            continue
        rendered_clips.append(clip_audio)
        dur = clip_audio.shape[0] / working_sr
        timeline.append(
            TimelineClip(
                section_label=(clip.source_section.label.value if clip.source_section else "synth"),
                style_role=clip.role,
                start_sec=round(cursor_sec, 3),
                end_sec=round(cursor_sec + dur, 3),
                source_section_label=(clip.source_section.label.value if clip.source_section else None),
            )
        )
        cursor_sec += dur
        _report(0.25 + 0.6 * (i + 1) / n_clips, f"rendered {clip.role}")

    if not rendered_clips:
        raise RuntimeError("Arrangement produced no audio — check stem/session state.")

    _report(0.88, "mixing timeline")
    fade_samples = int(working_sr * 0.05)
    final = rendered_clips[0]
    for nxt in rendered_clips[1:]:
        final = equal_power_crossfade(final, nxt, fade_samples)
    final = normalize_peak(final, target_peak=0.9)

    edit_id = new_edit_id()
    edit_dir = session.edit_dir(edit_id)
    preview_path = edit_dir / "preview.wav"
    write_stereo(preview_path, final, working_sr)

    _report(1.0, "done")

    return GenerateResult(
        session_id=session.id,
        edit_id=edit_id,
        style=request.style,
        resulting_bpm=round(target_bpm, 2),
        duration_sec=round(final.shape[0] / working_sr, 3),
        timeline=timeline,
        preview_path=session.relative(preview_path),
    )
