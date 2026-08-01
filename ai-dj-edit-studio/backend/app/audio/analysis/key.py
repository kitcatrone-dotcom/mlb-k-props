"""Musical key detection via chroma + Krumhansl-Schmuckler key profiles.

Also reports the Camelot Wheel notation (e.g. "8A") alongside the standard
name, since that's what working DJs actually use to judge harmonic
compatibility between tracks — a plain "A Minor" label without it would be
half-useful for a DJ tool.
"""
from __future__ import annotations

import numpy as np
import librosa

from ...schemas import KeyInfo

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Kessler key profiles (classic cognitive-science derived weights
# for how strongly each scale degree "belongs" to a major/minor key).
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

# Camelot Wheel: maps (tonic pitch class index, mode) -> Camelot code.
# Built from the standard wheel (relative major/minor share a number;
# 'B' = major, 'A' = minor).
_CAMELOT_MAJOR = {
    "B": "1B", "F#": "2B", "Db": "3B", "Ab": "4B", "Eb": "5B", "Bb": "6B",
    "F": "7B", "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B",
}
_CAMELOT_MINOR = {
    "Ab": "1A", "Eb": "2A", "Bb": "3A", "F": "4A", "C": "5A", "G": "6A",
    "D": "7A", "A": "8A", "E": "9A", "B": "10A", "F#": "11A", "Db": "12A",
}
# Enharmonic aliases so lookups work regardless of sharp/flat spelling.
_ENHARMONIC = {"C#": "Db", "D#": "Eb", "F#": "F#", "G#": "Ab", "A#": "Bb"}


def _camelot(tonic: str, mode: str) -> str:
    spelling = _ENHARMONIC.get(tonic, tonic)
    table = _CAMELOT_MAJOR if mode == "major" else _CAMELOT_MINOR
    return table.get(spelling, table.get(tonic, "?"))


def analyze_key(y: np.ndarray, sr: int) -> KeyInfo:
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    chroma_mean = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-9)

    best_score = -np.inf
    best_tonic_idx = 0
    best_mode = "major"

    for shift in range(12):
        major_rot = np.roll(_MAJOR_PROFILE, shift)
        minor_rot = np.roll(_MINOR_PROFILE, shift)
        major_rot = major_rot / np.linalg.norm(major_rot)
        minor_rot = minor_rot / np.linalg.norm(minor_rot)

        major_score = float(np.dot(chroma_mean, major_rot))
        minor_score = float(np.dot(chroma_mean, minor_rot))

        if major_score > best_score:
            best_score, best_tonic_idx, best_mode = major_score, shift, "major"
        if minor_score > best_score:
            best_score, best_tonic_idx, best_mode = minor_score, shift, "minor"

    tonic = PITCH_CLASSES[best_tonic_idx]
    display = f"{tonic} {'Minor' if best_mode == 'minor' else 'Major'}"

    # Normalize correlation (~[-1, 1]) into a 0-1 confidence.
    confidence = float(np.clip((best_score + 1) / 2, 0.0, 1.0))

    return KeyInfo(
        tonic=tonic,
        mode=best_mode,  # type: ignore[arg-type]
        display=display,
        camelot=_camelot(tonic, best_mode),
        confidence=round(confidence, 3),
    )
