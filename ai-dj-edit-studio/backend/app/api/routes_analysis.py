"""GET /analysis/{session_id} — runs (or returns cached) full analysis:
tempo, key, time signature, structure, energy, genre guesses.

Defined as a plain `def` (not `async def`) so FastAPI runs it in its
threadpool executor — this is genuinely CPU-bound work (librosa/numpy/scipy)
and would otherwise block the event loop for every other request.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..audio.analysis.energy import analyze_energy, guess_genre
from ..audio.analysis.key import analyze_key
from ..audio.analysis.structure import analyze_structure
from ..audio.analysis.tempo import analyze_tempo
from ..audio.analysis.timesig import analyze_time_signature
from ..audio.io import load_mono
from ..schemas import AnalysisResult
from ..storage import Session

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{session_id}", response_model=AnalysisResult)
def get_analysis(session_id: str, force: bool = False) -> AnalysisResult:
    try:
        session = Session.load(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not force:
        cached = session.load_analysis()
        if cached:
            return AnalysisResult.model_validate(cached)

    if not session.original_path.exists():
        raise HTTPException(status_code=409, detail="Session has no imported audio yet.")

    y, sr = load_mono(session.original_path)
    duration_sec = len(y) / sr

    tempo = analyze_tempo(y, sr, wav_path_for_madmom=str(session.original_path))
    key = analyze_key(y, sr)
    time_sig = analyze_time_signature(y, sr, tempo.beat_times)
    structure = analyze_structure(y, sr, tempo, time_sig, duration_sec)
    energy = analyze_energy(y, sr, tempo)
    genre_guesses = guess_genre(y, sr, tempo)

    result = AnalysisResult(
        session_id=session.id,
        duration_sec=round(duration_sec, 3),
        tempo=tempo,
        key=key,
        time_signature=time_sig,
        structure=structure,
        energy=energy,
        genre_guesses=genre_guesses,
    )
    session.save_analysis(result.model_dump(mode="json"))
    return result
