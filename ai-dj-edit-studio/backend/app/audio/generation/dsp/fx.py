"""Time-varying filter sweeps (breakdowns, build-ups) and send effects
(reverb/delay for risers, impacts, and breakdown atmosphere).

Filter sweeps are implemented as overlap-add Butterworth filtering with the
cutoff frequency interpolated (log-scale) chunk to chunk — a standard,
dependency-light way to get an audibly moving filter without needing a
sample-accurate modulated biquad. Reverb/delay use Pedalboard (Spotify),
which is fast and high quality for static-parameter sends.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt


def _sos(cutoff_hz: float, sr: int, btype: str, order: int = 4):
    nyq = sr / 2
    normal = np.clip(cutoff_hz / nyq, 1e-4, 0.999)
    return butter(order, normal, btype=btype, output="sos")


def filter_sweep(
    x: np.ndarray,
    sr: int,
    start_hz: float,
    end_hz: float,
    btype: str = "lowpass",
    chunk_ms: float = 60.0,
) -> np.ndarray:
    """Applies a swept low/high-pass filter across the whole buffer, cutoff
    moving exponentially from `start_hz` to `end_hz`. Works on mono or
    (samples, channels) audio."""
    mono_in = x.ndim == 1
    data = x[:, None] if mono_in else x

    n = data.shape[0]
    chunk = max(1, int(sr * chunk_ms / 1000))
    n_chunks = max(1, int(np.ceil(n / chunk)))
    window = np.hanning(chunk * 2)

    out = np.zeros_like(data)
    gain_sum = np.zeros(n)

    for i in range(n_chunks):
        start = i * chunk
        end = min(n, start + chunk * 2)
        if end <= start:
            continue
        frac = i / max(n_chunks - 1, 1)
        cutoff = start_hz * (end_hz / start_hz) ** frac if start_hz > 0 and end_hz > 0 else end_hz
        sos = _sos(cutoff, sr, btype)

        w = window[: end - start]
        for c in range(data.shape[1]):
            filtered = sosfilt(sos, data[start:end, c])
            out[start:end, c] += filtered * w
        gain_sum[start:end] += w

    gain_sum[gain_sum < 1e-6] = 1.0
    out /= gain_sum[:, None]
    return out[:, 0] if mono_in else out


def _to_pedalboard(x: np.ndarray) -> np.ndarray:
    """(samples,) or (samples, channels) -> Pedalboard's (channels, samples)."""
    if x.ndim == 1:
        return x[None, :].astype(np.float32)
    return x.T.astype(np.float32)


def _from_pedalboard(x: np.ndarray, was_mono: bool) -> np.ndarray:
    return x[0] if was_mono else x.T


def add_reverb(x: np.ndarray, sr: int, room_size: float = 0.6, wet: float = 0.35) -> np.ndarray:
    from pedalboard import Pedalboard, Reverb

    was_mono = x.ndim == 1
    board = Pedalboard([Reverb(room_size=room_size, wet_level=wet, dry_level=1 - wet)])
    out = board(_to_pedalboard(x), sr)
    return _from_pedalboard(out, was_mono)


def add_delay(x: np.ndarray, sr: int, seconds: float = 0.375, feedback: float = 0.3, mix: float = 0.25) -> np.ndarray:
    from pedalboard import Pedalboard, Delay

    was_mono = x.ndim == 1
    board = Pedalboard([Delay(delay_seconds=seconds, feedback=feedback, mix=mix)])
    out = board(_to_pedalboard(x), sr)
    return _from_pedalboard(out, was_mono)


def gain_ramp(x: np.ndarray, start_gain: float, end_gain: float) -> np.ndarray:
    n = x.shape[0]
    ramp = np.linspace(start_gain, end_gain, n)
    return x * (ramp[:, None] if x.ndim > 1 else ramp)


def equal_power_crossfade(a: np.ndarray, b: np.ndarray, fade_samples: int) -> np.ndarray:
    """Crossfades the tail of `a` into the head of `b` and returns the
    concatenated result. `a`/`b` are (samples, channels)."""
    fade_samples = min(fade_samples, len(a), len(b))
    if fade_samples <= 0:
        return np.concatenate([a, b], axis=0)

    t = np.linspace(0, np.pi / 2, fade_samples)
    fade_out = np.cos(t)[:, None]
    fade_in = np.sin(t)[:, None]

    head = a[: len(a) - fade_samples]
    mixed = a[len(a) - fade_samples :] * fade_out + b[:fade_samples] * fade_in
    tail = b[fade_samples:]
    return np.concatenate([head, mixed, tail], axis=0)
