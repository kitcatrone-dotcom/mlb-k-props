"""POST /separation/{session_id} — kicks off Demucs stem separation as a
background job and returns a job id to poll/subscribe to.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from .. import config
from ..audio.separation.demucs_engine import separate_to_stems
from ..jobs import job_manager
from ..schemas import SeparationResult
from ..storage import Session

router = APIRouter(prefix="/separation", tags=["separation"])


@router.post("/{session_id}")
def start_separation(session_id: str) -> dict:
    try:
        session = Session.load(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not session.original_path.exists():
        raise HTTPException(status_code=409, detail="Session has no imported audio yet.")

    if session.has_stems():
        stems = {name: session.relative(session.stem_path(name)) for name in config.STEM_NAMES}
        job_id = job_manager.start("separation", lambda report: {"session_id": session.id, "stems": stems})
        return {"job_id": job_id, "cached": True}

    def work(report) -> dict:
        stems_abs = separate_to_stems(session.original_path, session.dir / "stems", report=report)
        stems_rel = {name: session.relative(Path(p)) for name, p in stems_abs.items()}
        return SeparationResult(session_id=session.id, stems=stems_rel).model_dump(mode="json")

    job_id = job_manager.start("separation", work)
    return {"job_id": job_id, "cached": False}
