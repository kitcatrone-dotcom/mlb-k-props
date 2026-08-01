"""BPM / beat-grid detection.

Approach: librosa's onset-strength envelope drives both a global tempo
estimate (via the tempogram) and a dynamic-programming beat tracker. Because
tempo estimators are prone to "octave errors" (reporting half or double the
true tempo — e.g. 75 vs 150 BPM), we fold the estimate into the DJ-usable
range (config.MIN_DJ_BPM..MAX_DJ_BPM) since every target style in this app
operates in that range anyway.

Downbeats (first beat of each bar) are estimated from the beat grid using a
simple spectral-flux-accent heuristic; for higher-accuracy downbeat tracking
madmom's DBNDownBeatTracker is used when available (see `_madmom_downbeats`).
"""
from __future__ import annotations

import numpy as np
import librosa

from ... import config
from ...schemas import TempoInfo


def _fold_into_dj_range(bpm: float) -> float:
    while bpm < config.MIN_DJ_BPM:
        bpm *= 2
    while bpm > config.MAX_DJ_BPM:
        bpm /= 2
    return bpm


def _madmom_downbeats(path_str: str) -> list[float] | None:
    """Best-effort madmom downbeat tracking. Returns None if madmom isn't
    usable in this environment (it has a heavier native build than the rest
    of the stack), so callers must have a fallback."""
    try:
        from madmom.features.downbeats import (
            DBNDownBeatTrackingProcessor,
            RNNDownBeatProcessor,
        )
    except Exception:
        return None

    try:
        act = RNNDownBeatProcessor()(path_str)
        proc = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
        beats = proc(act)  # columns: [time, beat_position_in_bar]
        downbeats = [float(t) for t, pos in beats if int(round(pos)) == 1]
        return downbeats or None
    except Exception:
        return None


def analyze_tempo(y: np.ndarray, sr: int, wav_path_for_madmom: str | None = None) -> TempoInfo:
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)

    tempo_candidates, _ = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sr, units="frames"
    )
    raw_bpm = float(np.atleast_1d(tempo_candidates)[0]) if np.size(tempo_candidates) else 120.0
    if raw_bpm <= 0:
        raw_bpm = 120.0

    bpm = _fold_into_dj_range(raw_bpm)

    _, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sr, bpm=bpm, units="frames"
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    # Confidence: how concentrated the tempogram energy is around the chosen
    # BPM relative to the whole distribution — a crude but useful proxy.
    tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
    tempo_freqs = librosa.tempo_frequencies(tempogram.shape[0], sr=sr)
    target_bin = int(np.argmin(np.abs(tempo_freqs - bpm)))
    band = tempogram[max(0, target_bin - 2) : target_bin + 3, :].mean()
    total = tempogram.mean() + 1e-9
    confidence = float(np.clip(band / total / 3.0, 0.0, 1.0))

    downbeats = None
    if wav_path_for_madmom:
        downbeats = _madmom_downbeats(wav_path_for_madmom)
    if not downbeats:
        # Fallback: assume 4/4-style grouping starting on the first detected
        # beat; refined later against the actual detected time signature.
        downbeats = beat_times[0::4] if beat_times else []

    return TempoInfo(
        bpm=round(bpm, 2),
        confidence=round(confidence, 3),
        beat_times=beat_times,
        downbeat_times=downbeats,
    )
