"""Song structure segmentation: intro / verse / build / drop / breakdown /
bridge / outro.

Method (a standard MIR pipeline, "Foote novelty + clustering"):
  1. Aggregate timbre (MFCC) + harmony (chroma) + loudness (RMS) features
     per bar (using the detected beat/downbeat grid, so boundaries always
     land on musically sensible bar lines).
  2. Build a bar-by-bar self-similarity matrix.
  3. Detect structural boundaries from a novelty curve (local
     self-dissimilarity around each bar — a simplified Foote checkerboard
     novelty).
  4. Cluster the resulting segments by feature similarity, so e.g. every
     chorus repetition lands in the same cluster.
  5. Apply DJ/EDM-domain heuristics (position, energy, repetition count) to
     turn clusters into intro/verse/build/drop/breakdown/bridge/outro labels.

This is a heuristic pipeline, not a trained structure-labeling model — it's
tuned for 4/4 dance-music structure specifically, which is exactly the
material this app targets.
"""
from __future__ import annotations

import numpy as np
import librosa
from scipy.signal import find_peaks
from sklearn.cluster import AgglomerativeClustering

from ...schemas import Section, SectionLabel, StructureInfo, TempoInfo, TimeSignatureInfo

_MIN_SEGMENT_BARS = 4


def _bar_starts(tempo: TempoInfo, time_sig: TimeSignatureInfo, duration_sec: float) -> list[float]:
    if len(tempo.downbeat_times) >= 2:
        starts = list(tempo.downbeat_times)
    elif tempo.beat_times:
        step = max(1, time_sig.numerator)
        starts = tempo.beat_times[0::step]
    else:
        bar_len = (60.0 / max(tempo.bpm, 1e-6)) * max(time_sig.numerator, 1)
        starts = list(np.arange(0.0, duration_sec, bar_len))

    if not starts or starts[0] > 0.5:
        starts = [0.0] + starts

    # Extend the bar grid to the end of the track using the median bar length.
    if len(starts) >= 2:
        diffs = np.diff(starts)
        bar_len = float(np.median(diffs)) if len(diffs) else 2.0
    else:
        bar_len = (60.0 / max(tempo.bpm, 1e-6)) * max(time_sig.numerator, 1)

    while starts[-1] + bar_len < duration_sec:
        starts.append(starts[-1] + bar_len)
    starts.append(duration_sec)
    return starts


def _bar_features(y: np.ndarray, sr: int, bar_starts: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Returns (feature_matrix [n_bars, d], rms_per_bar [n_bars])."""
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    frame_times = librosa.frames_to_time(np.arange(mfcc.shape[1]), sr=sr)

    feats, bar_rms = [], []
    for start, end in zip(bar_starts[:-1], bar_starts[1:]):
        mask = (frame_times >= start) & (frame_times < end)
        if not np.any(mask):
            mask = np.zeros_like(frame_times, dtype=bool)
            nearest = int(np.argmin(np.abs(frame_times - start)))
            mask[nearest] = True
        vec = np.concatenate([mfcc[:, mask].mean(axis=1), chroma[:, mask].mean(axis=1)])
        feats.append(vec)
        bar_rms.append(float(rms[mask].mean()) if np.any(mask) else 0.0)

    X = np.array(feats)
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
    return X, np.array(bar_rms)


def _self_similarity(X: np.ndarray) -> np.ndarray:
    norm = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    return norm @ norm.T


def _novelty_curve(S: np.ndarray, window: int = 4) -> np.ndarray:
    n = S.shape[0]
    novelty = np.zeros(n)
    for i in range(n):
        a, b = max(0, i - window), i
        c, d = i, min(n, i + window)
        if b - a < 2 or d - c < 2:
            continue
        within_before = S[a:b, a:b].mean()
        within_after = S[c:d, c:d].mean()
        across = S[a:b, c:d].mean()
        novelty[i] = (within_before + within_after) / 2 - across
    return np.clip(novelty, 0, None)


def _boundaries(novelty: np.ndarray, n_bars: int) -> list[int]:
    if n_bars <= _MIN_SEGMENT_BARS * 2:
        return [0, n_bars]
    peaks, _ = find_peaks(novelty, distance=_MIN_SEGMENT_BARS, prominence=novelty.std() * 0.5 + 1e-6)
    bounds = sorted({0, n_bars, *[int(p) for p in peaks]})
    # Merge segments shorter than the minimum bar length.
    merged = [bounds[0]]
    for b in bounds[1:]:
        if b - merged[-1] < _MIN_SEGMENT_BARS and b != n_bars:
            continue
        merged.append(b)
    if merged[-1] != n_bars:
        merged[-1] = n_bars
    return merged


def _cluster_segments(seg_features: np.ndarray) -> np.ndarray:
    n = seg_features.shape[0]
    if n <= 1:
        return np.zeros(n, dtype=int)
    norm = seg_features / (np.linalg.norm(seg_features, axis=1, keepdims=True) + 1e-9)
    distance = 1 - (norm @ norm.T)
    distance = np.clip(distance, 0, None)
    n_clusters = max(1, min(n, n // 2 + 1))
    clustering = AgglomerativeClustering(
        n_clusters=None, distance_threshold=0.35, metric="precomputed", linkage="average"
    )
    try:
        labels = clustering.fit_predict(distance)
    except Exception:
        labels = np.arange(n)
    return labels


def _label_segments(
    seg_bounds: list[tuple[int, int]],
    seg_energy: list[float],
    cluster_ids: np.ndarray,
) -> list[SectionLabel]:
    n = len(seg_bounds)
    energy_arr = np.array(seg_energy)
    energy_norm = (energy_arr - energy_arr.min()) / (energy_arr.max() - energy_arr.min() + 1e-9)

    cluster_counts: dict[int, int] = {}
    cluster_mean_energy: dict[int, float] = {}
    for cid in set(cluster_ids.tolist()):
        idx = np.where(cluster_ids == cid)[0]
        cluster_counts[cid] = len(idx)
        cluster_mean_energy[cid] = float(energy_norm[idx].mean())

    # The "drop" cluster: highest mean energy among clusters that repeat
    # (or, failing that, the single highest-energy segment).
    repeating = [cid for cid, c in cluster_counts.items() if c >= 2]
    if repeating:
        drop_cluster = max(repeating, key=lambda cid: cluster_mean_energy[cid])
    else:
        drop_cluster = int(cluster_ids[int(np.argmax(energy_norm))])

    labels: list[SectionLabel] = [SectionLabel.VERSE] * n

    for i in range(n):
        is_first, is_last = i == 0, i == n - 1
        is_drop = cluster_ids[i] == drop_cluster

        if is_first and not is_drop:
            labels[i] = SectionLabel.INTRO
        elif is_last and not is_drop:
            labels[i] = SectionLabel.OUTRO
        elif is_drop:
            labels[i] = SectionLabel.DROP
        elif (
            i + 1 < n
            and cluster_ids[i + 1] == drop_cluster
            and energy_norm[i] < energy_norm[i + 1]
        ):
            labels[i] = SectionLabel.BUILD
        elif energy_norm[i] < 0.3 and 0 < i < n - 1:
            labels[i] = SectionLabel.BREAKDOWN
        elif cluster_counts[cluster_ids[i]] == 1 and i > n * 0.5:
            labels[i] = SectionLabel.BRIDGE
        else:
            labels[i] = SectionLabel.VERSE

    return labels


def analyze_structure(
    y: np.ndarray,
    sr: int,
    tempo: TempoInfo,
    time_sig: TimeSignatureInfo,
    duration_sec: float,
) -> StructureInfo:
    bar_starts = _bar_starts(tempo, time_sig, duration_sec)
    n_bars = len(bar_starts) - 1
    if n_bars < 2:
        return StructureInfo(
            sections=[
                Section(
                    label=SectionLabel.VERSE, start=0.0, end=duration_sec,
                    bar_start=0, bar_count=max(n_bars, 1), energy=0.5,
                )
            ],
            bar_length_sec=duration_sec,
        )

    X, bar_rms = _bar_features(y, sr, bar_starts)
    S = _self_similarity(X)
    novelty = _novelty_curve(S)
    bounds = _boundaries(novelty, n_bars)

    seg_bounds = list(zip(bounds[:-1], bounds[1:]))
    seg_features = np.array([X[a:b].mean(axis=0) for a, b in seg_bounds])
    seg_energy = [float(bar_rms[a:b].mean()) if b > a else 0.0 for a, b in seg_bounds]
    cluster_ids = _cluster_segments(seg_features)
    labels = _label_segments(seg_bounds, seg_energy, cluster_ids)

    energy_arr = np.array(seg_energy)
    energy_norm = ((energy_arr - energy_arr.min()) / (energy_arr.max() - energy_arr.min() + 1e-9)).tolist()

    diffs = np.diff(bar_starts)
    bar_length_sec = float(np.median(diffs)) if len(diffs) else 2.0

    sections = [
        Section(
            label=labels[i],
            start=round(bar_starts[a], 3),
            end=round(bar_starts[b], 3),
            bar_start=a,
            bar_count=b - a,
            energy=round(energy_norm[i], 3),
        )
        for i, (a, b) in enumerate(seg_bounds)
    ]

    return StructureInfo(sections=sections, bar_length_sec=round(bar_length_sec, 4))
