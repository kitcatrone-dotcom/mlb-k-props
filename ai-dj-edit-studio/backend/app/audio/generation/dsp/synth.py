"""Synthesized percussion and transition FX.

The edit generation engine layers these under/over the separated `drums`
stem rather than replacing it outright — the goal is to reinforce the
genre's characteristic feel (a tighter, punchier four-on-the-floor kick for
House, a snappier breakbeat for D&B, etc.) without needing a bundled sample
library (which would mean shipping/licensing third-party drum samples).
Everything below is generated from scratch with basic oscillator + noise +
envelope DSP — the same technique classic drum machines used, just in code.
"""
from __future__ import annotations

import numpy as np


def _exp_decay(n: int, tau_samples: float) -> np.ndarray:
    t = np.arange(n)
    return np.exp(-t / max(tau_samples, 1e-6))


def synth_kick(sr: int, duration: float = 0.28, tone: str = "house") -> np.ndarray:
    """`tone`: "house" (round, ~55Hz body), "tight" (short, punchy, tech
    house/bass house), "sub" (deep, longer sub tail), "break" (short/dry, D&B)."""
    n = int(sr * duration)
    t = np.arange(n) / sr

    params = {
        "house": dict(f0=150, f1=50, pitch_tau=0.045, amp_tau=0.16, click=0.15),
        "tight": dict(f0=180, f1=55, pitch_tau=0.02, amp_tau=0.09, click=0.25),
        "sub": dict(f0=120, f1=40, pitch_tau=0.06, amp_tau=0.32, click=0.08),
        "break": dict(f0=200, f1=65, pitch_tau=0.015, amp_tau=0.07, click=0.3),
    }[tone]

    pitch_env = params["f1"] + (params["f0"] - params["f1"]) * _exp_decay(n, params["pitch_tau"] * sr)
    phase = 2 * np.pi * np.cumsum(pitch_env) / sr
    body = np.sin(phase)
    amp_env = _exp_decay(n, params["amp_tau"] * sr)

    click_n = max(1, int(sr * 0.003))
    click = np.zeros(n)
    click[:click_n] = np.random.uniform(-1, 1, click_n) * _exp_decay(click_n, click_n / 4)

    out = body * amp_env + click * params["click"]
    return np.tanh(out * 1.4).astype(np.float32)


def synth_clap(sr: int, duration: float = 0.22) -> np.ndarray:
    n = int(sr * duration)
    out = np.zeros(n)
    # A handclap is a few short, slightly-offset noise bursts through a
    # broad bandpass, which is what gives it that "flam" texture.
    burst_offsets = [0.0, 0.008, 0.016, 0.028]
    for off in burst_offsets:
        start = int(sr * off)
        remain = n - start
        if remain <= 0:
            continue
        burst_n = min(remain, int(sr * 0.05))
        noise = np.random.uniform(-1, 1, burst_n)
        env = _exp_decay(burst_n, sr * 0.012)
        out[start : start + burst_n] += noise * env * 0.6
    tail_n = n
    tail = np.random.uniform(-1, 1, tail_n) * _exp_decay(tail_n, sr * 0.05) * 0.3
    out += tail
    out = _bandpass(out, sr, 900, 6000)
    return np.tanh(out * 1.6).astype(np.float32)


def synth_hat(sr: int, duration: float = 0.08, open_: bool = False) -> np.ndarray:
    n = int(sr * (0.35 if open_ else duration))
    noise = np.random.uniform(-1, 1, n)
    noise = _bandpass(noise, sr, 6000, 16000)
    env = _exp_decay(n, sr * (0.12 if open_ else 0.018))
    return (noise * env * 0.7).astype(np.float32)


def synth_perc(sr: int, duration: float = 0.15, pitch: float = 400.0) -> np.ndarray:
    """A woody/conga-like percussion hit for Afro House patterns."""
    n = int(sr * duration)
    t = np.arange(n) / sr
    tone = np.sin(2 * np.pi * pitch * t) * _exp_decay(n, sr * 0.05)
    noise = np.random.uniform(-1, 1, n) * _exp_decay(n, sr * 0.01) * 0.3
    return (tone * 0.8 + noise).astype(np.float32)


def synth_riser(sr: int, duration: float, kind: str = "noise") -> np.ndarray:
    """A build-up riser: rising pitch and rising amplitude over `duration`
    seconds, used in the last bars before a drop."""
    n = int(sr * duration)
    t = np.linspace(0, 1, n)
    amp_env = t ** 1.5

    if kind == "noise":
        noise = np.random.uniform(-1, 1, n)
        sig = _bandpass_sweep(noise, sr, 200, 9000)
    else:  # "tonal"
        freq = 100 * (20 ** t)  # exponential sweep 100Hz -> 2kHz
        phase = 2 * np.pi * np.cumsum(freq) / sr
        sig = np.sin(phase) + 0.5 * np.sin(2 * phase)

    return (sig * amp_env).astype(np.float32)


def synth_impact(sr: int, duration: float = 1.2) -> np.ndarray:
    """A single sub/noise impact hit for the exact moment a drop lands."""
    n = int(sr * duration)
    t = np.arange(n) / sr
    sub = np.sin(2 * np.pi * 45 * t) * _exp_decay(n, sr * 0.6)
    noise = np.random.uniform(-1, 1, n) * _exp_decay(n, sr * 0.05)
    return np.tanh((sub * 1.2 + noise * 0.6)).astype(np.float32)


def synth_downlifter(sr: int, duration: float = 0.9) -> np.ndarray:
    """A falling-pitch sweep, used going *into* a breakdown."""
    n = int(sr * duration)
    t = np.linspace(1, 0, n)
    freq = 60 + 3000 * (t ** 2)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    sig = np.sin(phase)
    env = t ** 0.7
    return (sig * env).astype(np.float32)


# --- small internal filter helpers (kept local so this module has no
# hard dependency on the fx.py Pedalboard chain for basic synthesis) ---

def _bandpass(x: np.ndarray, sr: int, low: float, high: float, order: int = 2) -> np.ndarray:
    from scipy.signal import butter, sosfilt

    nyq = sr / 2
    lo = np.clip(low / nyq, 1e-4, 0.999)
    hi = np.clip(high / nyq, lo + 1e-4, 0.999)
    sos = butter(order, [lo, hi], btype="bandpass", output="sos")
    return sosfilt(sos, x)


def _bandpass_sweep(x: np.ndarray, sr: int, low: float, high: float) -> np.ndarray:
    """Cheap time-varying bandpass: filters the whole buffer at a handful of
    center frequencies and crossfades between them, so the riser's tone
    audibly rises rather than sitting static."""
    from scipy.signal import butter, sosfilt

    n = len(x)
    steps = 6
    chunk = n // steps
    out = np.zeros(n)
    window = np.hanning(chunk * 2) if chunk > 0 else np.ones(1)
    for i in range(steps):
        start = i * chunk
        end = min(n, start + chunk * 2)
        seg = x[start:end]
        if len(seg) == 0:
            continue
        frac = i / max(steps - 1, 1)
        center = low * (high / low) ** frac
        lo = max(20, center * 0.7)
        hi = min(sr / 2 - 100, center * 1.4)
        nyq = sr / 2
        sos = butter(2, [np.clip(lo / nyq, 1e-4, 0.99), np.clip(hi / nyq, lo / nyq + 1e-4, 0.999)], btype="bandpass", output="sos")
        filtered = sosfilt(sos, seg)
        w = window[: len(seg)]
        out[start:end] += filtered * w
    return out
