"""POST /import — accepts an uploaded MP3/WAV/FLAC/AIFF, decodes it into a
new session, and returns the session id the rest of the pipeline keys off of.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from .. import config
from ..audio.io import decode_to_working_wav
from ..schemas import ImportResult
from ..storage import Session

router = APIRouter(prefix="/import", tags=["import"])


@router.post("", response_model=ImportResult)
async def import_file(file: UploadFile) -> ImportResult:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in config.SUPPORTED_IMPORT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Supported: "
            f"{sorted(config.SUPPORTED_IMPORT_EXTENSIONS)}",
        )

    session = Session.create()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        sr, channels, duration = decode_to_working_wav(tmp_path, session.original_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not decode audio: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return ImportResult(
        session_id=session.id,
        filename=file.filename or "import",
        duration_sec=round(duration, 3),
        sample_rate=sr,
        channels=channels,
    )
