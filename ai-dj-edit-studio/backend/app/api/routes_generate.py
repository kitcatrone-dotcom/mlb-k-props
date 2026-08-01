"""POST /generate — kicks off edit generation (arrangement + DSP render) as
a background job."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..audio.generation.engine import generate_edit
from ..jobs import job_manager
from ..schemas import AnalysisResult, GenerateRequest
from ..storage import Session

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("")
def start_generate(request: GenerateRequest) -> dict:
    try:
        session = Session.load(request.session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    analysis_data = session.load_analysis()
    if not analysis_data:
        raise HTTPException(status_code=409, detail="Run analysis before generating an edit.")
    if not session.has_stems():
        raise HTTPException(status_code=409, detail="Run stem separation before generating an edit.")

    analysis = AnalysisResult.model_validate(analysis_data)

    def work(report) -> dict:
        result = generate_edit(session, analysis, request, report=report)
        return result.model_dump(mode="json")

    job_id = job_manager.start("generation", work)
    return {"job_id": job_id}
