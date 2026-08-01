"""Emotional energy and genre estimation.

This ships as a transparent, dependency-light heuristic classifier (RMS
loudness, onset density/regularity, spectral centroid/contrast, tempo) so
the app works fully offline with no extra model download beyond Demucs.

Upgrade path: swap `guess_genre()`'s body for a call into a pretrained
tagging model without touching callers — e.g. Essentia's TensorFlow
`genre_discogs400`/`mood_*` models (see `models/README.md`), or a
HuggingFace audio-classification pipeline such as `MIT/ast-finetuned-
audioset-10-10-0.4593`. Both take a mono waveform + sample rate and return
label/confidence pairs, which is exactly the `GenreGuess` shape already
used here, so it's a drop-in replacement.
"""
from __future__ import annotations

import numpy as np
import librosa

from ...schemas import EnergyProfile, GenreGuess, TempoInfo

_GENRE_BPM_RANGES = {
    "house": (118, 128),
    "tech house": (122, 128),
    "afro house": (118, 124),
    "melodic house/techno": (118, 126),
    "bass house": (120, 128),
    "techno": (125, 145),
    "drum & bass": (160, 180),
    "trance": (128, 140),
    "hip hop / pop": (80, 110),
}


def _onset_regularity(y: np.ndarray, sr: int) -> float:
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")
    if len(onsets) < 4:
        return 0.3
    intervals = np.diff(onsets)
    if intervals.mean() <= 0:
        return 0.3
    cv = intervals.std() / (intervals.mean() + 1e-9)  # coefficient of variation
    return float(np.clip(1.0 - cv, 0.0, 1.0))


def analyze_energy(y: np.ndarray, sr: int, tempo: TempoInfo, n_bars_hint: int = 64) -> EnergyProfile:
    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

    overall_energy = float(np.clip(rms.mean() / (rms.max() + 1e-9), 0.0, 1.0))
    danceability = float(
        np.clip(0.5 * _onset_regularity(y, sr) + 0.5 * np.clip((tempo.bpm - 80) / 100, 0, 1), 0, 1)
    )
    # Spectral brightness as a rough proxy for perceived "valence" (brighter
    # timbre skews toward more upbeat/major-feeling material). Crude but
    # directionally reasonable and cheap to compute.
    valence = float(np.clip((centroid.mean() - 1000) / 4000, 0.0, 1.0))

    # Per-bar (well, per fixed-length window) energy curve for the UI graph.
    hop = max(1, len(rms) // n_bars_hint)
    curve = [
        float(np.clip(rms[i : i + hop].mean() / (rms.max() + 1e-9), 0, 1))
        for i in range(0, len(rms), hop)
    ]

    return EnergyProfile(
        overall_energy=round(overall_energy, 3),
        danceability=round(danceability, 3),
        valence=round(valence, 3),
        curve=[round(c, 3) for c in curve],
    )


def guess_genre(y: np.ndarray, sr: int, tempo: TempoInfo) -> list[GenreGuess]:
    """Heuristic genre scoring: BPM-range fit blended with a spectral
    "electronic-ness" score (flatness/contrast typical of synthesized,
    highly-produced dance music vs. acoustic/organic material)."""
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr).mean()
    flatness = float(librosa.feature.spectral_flatness(y=y).mean())
    electronic_score = float(np.clip(flatness * 8 + contrast / 40, 0.0, 1.0))

    scores: list[GenreGuess] = []
    for label, (lo, hi) in _GENRE_BPM_RANGES.items():
        mid = (lo + hi) / 2
        span = (hi - lo) / 2 + 1e-9
        bpm_fit = float(np.clip(1.0 - abs(tempo.bpm - mid) / (span * 2.5), 0.0, 1.0))
        is_electronic_label = label not in ("hip hop / pop",)
        blend = bpm_fit * 0.7 + (electronic_score if is_electronic_label else (1 - electronic_score)) * 0.3
        scores.append(GenreGuess(label=label, confidence=round(float(blend), 3)))

    scores.sort(key=lambda g: g.confidence, reverse=True)
    return scores[:5]
