"""Final mixdown post-processing (broadcast-standard loudness normalization)
and file export: WAV (24-bit), MP3 (320kbps), and a stems zip bundle.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from pydub import AudioSegment

from ... import config


def loudness_normalize(data: np.ndarray, sr: int, target_lufs: float | None = None) -> np.ndarray:
    target = config.EXPORT_TARGET_LUFS if target_lufs is None else target_lufs
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(data)
    if not np.isfinite(loudness):
        return data

    normalized = pyln.normalize.loudness(data, loudness, target)
    peak = float(np.max(np.abs(normalized))) if normalized.size else 0.0
    if peak > 0.99:
        normalized = normalized / peak * 0.99
    return normalized.astype(np.float32)


def export_wav(data: np.ndarray, sr: int, out_path: Path) -> Path:
    normalized = loudness_normalize(data, sr)
    sf.write(out_path, normalized, sr, subtype="PCM_24")
    return out_path


def export_mp3(data: np.ndarray, sr: int, out_path: Path) -> Path:
    normalized = loudness_normalize(data, sr)
    channels = normalized.shape[1] if normalized.ndim > 1 else 1
    int16 = np.clip(normalized * 32767, -32768, 32767).astype(np.int16)
    segment = AudioSegment(
        int16.tobytes(), frame_rate=sr, sample_width=2, channels=channels
    )
    segment.export(out_path, format="mp3", bitrate=config.EXPORT_MP3_BITRATE)
    return out_path


def export_stems_zip(stem_paths: dict[str, Path], out_path: Path) -> Path:
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in stem_paths.items():
            if path.exists():
                zf.write(path, arcname=f"{name}.wav")
    return out_path
