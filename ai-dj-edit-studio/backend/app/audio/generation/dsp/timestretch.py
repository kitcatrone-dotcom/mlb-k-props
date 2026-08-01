"""Tempo/pitch manipulation.

Rubber Band (via `pyrubberband`) is used when the `rubberband` CLI binary is
available on PATH — it's a formant-preserving time-stretch, which matters a
lot for vocals (naive resampling-based stretch shifts pitch with tempo and
makes vocals sound chipmunked/demonic at large tempo changes). Falls back to
librosa's phase-vocoder stretch (`librosa.effects.time_stretch`) so the app
still works without the system dependency, at somewhat lower quality on big
tempo jumps.
"""
from __future__ import annotations

import shutil

import numpy as np

_HAS_RUBBERBAND = shutil.which("rubberband") is not None


def stretch_rate_for_bpm(source_bpm: float, target_bpm: float) -> float:
    """Rate to pass to a time-stretch function: >1 speeds up (shortens),
    <1 slows down (lengthens)."""
    if source_bpm <= 0:
        return 1.0
    return target_bpm / source_bpm


def time_stretch(y: np.ndarray, sr: int, rate: float) -> np.ndarray:
    """Time-stretches stereo (samples, channels) or mono (samples,) audio by
    `rate` without changing pitch."""
    if abs(rate - 1.0) < 1e-3:
        return y

    if _HAS_RUBBERBAND:
        import pyrubberband as pyrb

        return pyrb.time_stretch(y, sr, rate)

    import librosa

    if y.ndim == 1:
        return librosa.effects.time_stretch(y, rate=rate)

    channels = [librosa.effects.time_stretch(np.ascontiguousarray(y[:, c]), rate=rate) for c in range(y.shape[1])]
    n = min(len(c) for c in channels)
    return np.stack([c[:n] for c in channels], axis=1)


def pitch_shift(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    if abs(semitones) < 1e-3:
        return y

    if _HAS_RUBBERBAND:
        import pyrubberband as pyrb

        return pyrb.pitch_shift(y, sr, semitones)

    import librosa

    if y.ndim == 1:
        return librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)

    channels = [
        librosa.effects.pitch_shift(np.ascontiguousarray(y[:, c]), sr=sr, n_steps=semitones)
        for c in range(y.shape[1])
    ]
    n = min(len(c) for c in channels)
    return np.stack([c[:n] for c in channels], axis=1)


def time_to_stretched(t: float, rate: float) -> float:
    """Maps a timestamp from the original track into the time-stretched
    track's timeline."""
    return t / rate
