"""Central configuration: paths, constants, tunables.

Kept as a single module (rather than env-var soup) since this is a local
single-user desktop app, not a multi-environment service.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Filesystem layout ---
# Everything the backend writes at runtime (decoded audio, stems, rendered
# edits) lives under a per-user data directory, never inside the repo.
BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DATA_DIR = Path(
    os.environ.get("AI_DJ_EDIT_STUDIO_DATA_DIR")
    or (Path.home() / ".ai-dj-edit-studio")
)
SESSIONS_DIR = APP_DATA_DIR / "sessions"

# --- Server ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_DJ_EDIT_STUDIO_PORT", "8742"))
# Electron loads its UI from a local dev server / file://, both of which
# count as distinct origins from the FastAPI server, so CORS must allow them.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "file://",
]

# --- Audio pipeline defaults ---
WORKING_SAMPLE_RATE = 48_000
WORKING_CHANNELS = 2
SUPPORTED_IMPORT_EXTENSIONS = {".mp3", ".wav", ".flac", ".aiff", ".aif"}

# DJ-usable tempo range; used to correct octave errors in BPM detection
# (e.g. detecting 75 BPM for a track that's actually a 150 BPM half-time feel).
MIN_DJ_BPM = 80
MAX_DJ_BPM = 180

# Demucs model. htdemucs_ft = 4-stem, fine-tuned, best quality/speed tradeoff
# for a desktop app. See models/README.md.
DEMUCS_MODEL = os.environ.get("AI_DJ_EDIT_STUDIO_DEMUCS_MODEL", "htdemucs_ft")
STEM_NAMES = ("vocals", "drums", "bass", "other")

# --- Export ---
EXPORT_MP3_BITRATE = "320k"
EXPORT_TARGET_LUFS = -9.0  # club-loud but not brickwalled; matches typical DJ pool masters


def ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id
