"""Time-signature estimation.

The vast majority of house/tech-house/D&B/afro-house source material is 4/4,
so this heuristic is deliberately biased toward that prior and only departs
from it when the beat-accent grid clearly supports 3 (waltz-like) or 6
(compound) groupings. This is a pragmatic simplification, not a claim of
general-purpose meter detection — documented here rather than hidden.
"""
from __future__ import annotations

import numpy as np
import librosa

from ...schemas import TimeSignatureInfo


def analyze_time_signature(
    y: np.ndarray, sr: int, beat_times: list[float]
) -> TimeSignatureInfo:
    if len(beat_times) < 8:
        return TimeSignatureInfo(numerator=4, denominator=4, confidence=0.3)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_times = librosa.times_like(onset_env, sr=sr)

    def accent_at(t: float) -> float:
        idx = int(np.searchsorted(onset_times, t))
        idx = min(max(idx, 0), len(onset_env) - 1)
        return float(onset_env[idx])

    beat_accents = np.array([accent_at(t) for t in beat_times])

    # For candidate grouping sizes, measure how much stronger beat[0 mod n]
    # is than the average beat within that grouping — a real downbeat
    # accent pattern should show a periodic spike.
    best_n, best_strength = 4, -np.inf
    for n in (3, 4, 6):
        if len(beat_accents) < n * 2:
            continue
        groups = [beat_accents[offset::n] for offset in range(n)]
        means = np.array([g.mean() for g in groups if len(g) > 0])
        if means.sum() <= 0:
            continue
        strength = float(means.max() - means.mean())
        # Bias toward 4/4 since it's overwhelmingly the common case for the
        # genres this app targets.
        bias = 0.15 if n == 4 else 0.0
        if strength + bias > best_strength:
            best_strength, best_n = strength + bias, n

    numerator = best_n
    denominator = 8 if best_n == 6 else 4
    confidence = float(np.clip(0.5 + best_strength, 0.3, 0.95))

    return TimeSignatureInfo(numerator=numerator, denominator=denominator, confidence=round(confidence, 3))
