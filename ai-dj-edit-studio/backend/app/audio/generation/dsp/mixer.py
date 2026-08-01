"""Small buffer-mixing primitives used by the edit generation engine to
assemble synthesized drum patterns and layer stems together."""
from __future__ import annotations

import numpy as np


def to_stereo(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        return np.stack([x, x], axis=1)
    return x


def mix_at(buffer: np.ndarray, start_sample: int, segment: np.ndarray, gain: float = 1.0) -> np.ndarray:
    """Adds `segment` into `buffer` starting at `start_sample`, growing
    `buffer` if needed. Both are (samples, channels)."""
    segment = to_stereo(segment) * gain
    end_sample = start_sample + segment.shape[0]
    if end_sample > buffer.shape[0]:
        pad = np.zeros((end_sample - buffer.shape[0], buffer.shape[1]), dtype=buffer.dtype)
        buffer = np.concatenate([buffer, pad], axis=0)
    buffer[start_sample:end_sample] += segment
    return buffer


def new_buffer(n_samples: int, channels: int = 2) -> np.ndarray:
    return np.zeros((max(n_samples, 0), channels), dtype=np.float32)


def render_pattern(
    pattern: list[dict],
    bar_length_sec: float,
    n_bars: int,
    sr: int,
    sample_bank: dict[str, np.ndarray],
    beats_per_bar: int = 4,
) -> np.ndarray:
    """Renders a repeating one-bar `pattern` (list of {instrument, beat,
    velocity}, `beat` in [0, beats_per_bar)) across `n_bars` bars into a
    stereo buffer."""
    total_samples = int(bar_length_sec * n_bars * sr)
    buf = new_buffer(total_samples)
    beat_sec = bar_length_sec / beats_per_bar

    for bar in range(n_bars):
        bar_start_sample = int(bar * bar_length_sec * sr)
        for hit in pattern:
            sample = sample_bank.get(hit["instrument"])
            if sample is None:
                continue
            hit_sample_pos = bar_start_sample + int(hit["beat"] * beat_sec * sr)
            buf = mix_at(buf, hit_sample_pos, sample, gain=hit.get("velocity", 1.0))

    return buf


def loop_to_length(x: np.ndarray, n_samples: int) -> np.ndarray:
    """Loops (or trims) `x` to exactly `n_samples`, crossfading the seam so
    a short source loop doesn't click when repeated."""
    if len(x) == 0:
        return new_buffer(n_samples)
    if len(x) >= n_samples:
        return x[:n_samples]

    from .fx import equal_power_crossfade

    x = to_stereo(x)
    out = x
    fade = min(int(0.01 * n_samples), len(x) // 4, 2000)
    while len(out) < n_samples:
        out = equal_power_crossfade(out, x, fade_samples=max(fade, 1))
    return out[:n_samples]


def normalize_peak(x: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak < 1e-9:
        return x
    return x * (target_peak / peak)
