"""Session/workdir management.

Each imported song gets a session directory under `config.SESSIONS_DIR`:

    sessions/<session_id>/
        original.wav            # decoded/normalized import
        analysis.json           # cached AnalysisResult
        stems/
            vocals.wav drums.wav bass.wav other.wav
        edits/
            <edit_id>/
                preview.wav
                export.wav / export.mp3 / stems.zip

Nothing here is a database — a local JSON sidecar per session is plenty for
a single-user desktop app and keeps the whole thing inspectable on disk.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from . import config


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def new_edit_id() -> str:
    return uuid.uuid4().hex[:10]


class Session:
    def __init__(self, session_id: str):
        self.id = session_id
        self.dir = config.session_dir(session_id)

    @classmethod
    def create(cls) -> "Session":
        session = cls(new_session_id())
        session.dir.mkdir(parents=True, exist_ok=True)
        (session.dir / "stems").mkdir(exist_ok=True)
        (session.dir / "edits").mkdir(exist_ok=True)
        return session

    @classmethod
    def load(cls, session_id: str) -> "Session":
        session = cls(session_id)
        if not session.dir.exists():
            raise FileNotFoundError(f"Unknown session: {session_id}")
        return session

    # --- paths ---
    @property
    def original_path(self) -> Path:
        return self.dir / "original.wav"

    @property
    def analysis_path(self) -> Path:
        return self.dir / "analysis.json"

    def stem_path(self, stem_name: str) -> Path:
        return self.dir / "stems" / f"{stem_name}.wav"

    def edit_dir(self, edit_id: str) -> Path:
        d = self.dir / "edits" / edit_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def relative(self, path: Path) -> str:
        return str(path.relative_to(self.dir))

    # --- cached analysis ---
    def save_analysis(self, data: dict[str, Any]) -> None:
        self.analysis_path.write_text(json.dumps(data, indent=2))

    def load_analysis(self) -> dict[str, Any] | None:
        if not self.analysis_path.exists():
            return None
        return json.loads(self.analysis_path.read_text())

    def has_stems(self) -> bool:
        return all(self.stem_path(name).exists() for name in config.STEM_NAMES)
