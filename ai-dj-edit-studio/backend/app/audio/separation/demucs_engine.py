"""Stem separation via Demucs v4 (`htdemucs_ft`), 4 stems: vocals, drums,
bass, other.

Uses `demucs.api.Separator`, the documented Python API (as opposed to
shelling out to the `demucs` CLI), so we can run in-process and hook Demucs's
own per-chunk progress callback into our job progress reporting.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import torch

from ... import config

_separator = None  # lazily constructed; loading the model takes a couple seconds


def _get_separator():
    global _separator
    if _separator is None:
        from demucs.api import Separator

        device = "cuda" if torch.cuda.is_available() else (
            "mps" if torch.backends.mps.is_available() else "cpu"
        )
        _separator = Separator(model=config.DEMUCS_MODEL, device=device)
    return _separator


def separate_to_stems(
    input_wav: Path,
    output_dir: Path,
    report: Callable[[float, str], None] | None = None,
) -> dict[str, str]:
    """Runs Demucs on `input_wav`, writes one WAV per stem into `output_dir`,
    and returns {stem_name: absolute_path_str}."""
    from demucs.api import save_audio

    def _report(p: float, msg: str) -> None:
        if report:
            report(p, msg)

    _report(0.02, "loading separation model")
    separator = _get_separator()

    progress_state = {"done": 0, "total": 1}

    def _demucs_callback(data: dict) -> None:
        # demucs.api.Separator's callback receives a dict with at least
        # 'segment_offset' and the model's total audio length in samples;
        # we don't depend on exact keys beyond a best-effort ratio.
        try:
            offset = float(data.get("segment_offset", 0))
            total = float(data.get("audio_length", 1)) or 1.0
            progress_state["done"] = offset
            progress_state["total"] = total
            frac = min(0.95, 0.1 + 0.85 * (offset / total))
            _report(frac, "separating stems")
        except Exception:
            pass

    _report(0.1, "separating stems")
    try:
        _, separated = separator.separate_audio_file(str(input_wav), callback=_demucs_callback)
    except TypeError:
        # Older/newer demucs versions may not accept `callback`; degrade to
        # coarse progress reporting instead of failing outright.
        _, separated = separator.separate_audio_file(str(input_wav))

    output_dir.mkdir(parents=True, exist_ok=True)
    stems: dict[str, str] = {}
    stem_items = list(separated.items())
    for i, (name, source) in enumerate(stem_items):
        out_path = output_dir / f"{name}.wav"
        save_audio(source, str(out_path), samplerate=separator.samplerate)
        stems[name] = str(out_path)
        _report(0.95 + 0.05 * (i + 1) / len(stem_items), f"wrote {name} stem")

    _report(1.0, "separation complete")
    return stems
