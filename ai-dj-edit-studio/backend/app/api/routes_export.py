"""POST /export — renders the requested export formats (WAV/MP3/stems zip)
for an already-generated edit. Fast enough to run synchronously (still
threadpooled by FastAPI since this is a plain `def`)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import config
from ..audio.export.render import export_mp3, export_stems_zip, export_wav
from ..audio.io import load_stereo
from ..schemas import ExportFormat, ExportRequest, ExportResult
from ..storage import Session

router = APIRouter(prefix="/export", tags=["export"])


@router.post("", response_model=ExportResult)
def export_edit(request: ExportRequest) -> ExportResult:
    try:
        session = Session.load(request.session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    edit_dir = session.edit_dir(request.edit_id)
    preview_path = edit_dir / "preview.wav"
    if not preview_path.exists():
        raise HTTPException(status_code=409, detail="Generate the edit before exporting.")

    files: dict[str, str] = {}

    if ExportFormat.WAV in request.formats or ExportFormat.MP3 in request.formats:
        data, sr = load_stereo(preview_path)

    if ExportFormat.WAV in request.formats:
        out = export_wav(data, sr, edit_dir / "export.wav")
        files["wav"] = session.relative(out)

    if ExportFormat.MP3 in request.formats:
        out = export_mp3(data, sr, edit_dir / "export.mp3")
        files["mp3"] = session.relative(out)

    if ExportFormat.STEMS in request.formats:
        stem_paths = {name: session.stem_path(name) for name in config.STEM_NAMES}
        out = export_stems_zip(stem_paths, edit_dir / "stems.zip")
        files["stems"] = session.relative(out)

    return ExportResult(session_id=session.id, edit_id=request.edit_id, files=files)
