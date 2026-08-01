"""Import/decode any supported input format into the canonical working
format (48kHz stereo float32 WAV) that the rest of the pipeline assumes.

pydub (backed by ffmpeg) handles the actual codec work, which is why it can
transparently read MP3/FLAC/AIFF/WAV without format-specific branches here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from pydub import AudioSegment

from .. import config


def decode_to_working_wav(input_path: Path, output_path: Path) -> tuple[int, int, float]:
    """Decodes any supported input file to the canonical working WAV.

    Returns (sample_rate, channels, duration_sec).
    """
    ext = input_path.suffix.lower()
    if ext not in config.SUPPORTED_IMPORT_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: "
            f"{sorted(config.SUPPORTED_IMPORT_EXTENSIONS)}"
        )

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(config.WORKING_SAMPLE_RATE)
    audio = audio.set_channels(config.WORKING_CHANNELS)
    audio = audio.set_sample_width(4)  # 32-bit for headroom through the DSP chain

    samples = np.array(audio.get_array_of_samples(), dtype=np.int32).astype(np.float32)
    samples = samples.reshape((-1, config.WORKING_CHANNELS))
    # pydub's 32-bit int PCM is full-scale int32; normalize to [-1, 1] float.
    samples /= float(2 ** 31)

    sf.write(output_path, samples, config.WORKING_SAMPLE_RATE, subtype="FLOAT")

    duration_sec = samples.shape[0] / config.WORKING_SAMPLE_RATE
    return config.WORKING_SAMPLE_RATE, config.WORKING_CHANNELS, duration_sec


def load_mono(path: Path) -> tuple[np.ndarray, int]:
    """Loads audio as mono float32 for analysis (librosa/madmom convention)."""
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    return mono, sr


def load_stereo(path: Path) -> tuple[np.ndarray, int]:
    """Loads audio as (samples, channels) float32 for rendering/mixing."""
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    return data, sr


def write_stereo(path: Path, data: np.ndarray, sr: int) -> None:
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    sf.write(path, data, sr, subtype="PCM_24")
