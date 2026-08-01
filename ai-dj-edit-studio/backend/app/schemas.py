"""Pydantic models shared across the API. Mirrors 1:1 with `frontend/src/types.ts`
so the two stay in sync by hand (small enough surface that codegen isn't worth it)."""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Analysis ---

class KeyInfo(BaseModel):
    tonic: str            # "A"
    mode: Literal["major", "minor"]
    display: str           # "A Minor"
    camelot: str            # "8A" — the notation DJs actually use for harmonic mixing
    confidence: float


class TempoInfo(BaseModel):
    bpm: float
    confidence: float
    beat_times: list[float]        # seconds
    downbeat_times: list[float]    # seconds, first beat of each bar


class TimeSignatureInfo(BaseModel):
    numerator: int
    denominator: int
    confidence: float


class SectionLabel(str, Enum):
    INTRO = "intro"
    VERSE = "verse"
    PRE_CHORUS = "pre_chorus"
    BUILD = "build"
    DROP = "drop"          # chorus/hook/high-energy repeated section
    BREAKDOWN = "breakdown"
    BRIDGE = "bridge"
    OUTRO = "outro"


class Section(BaseModel):
    label: SectionLabel
    start: float    # seconds, in the ORIGINAL track
    end: float
    bar_start: int
    bar_count: int
    energy: float    # 0-1, RMS-derived, relative to the track's own range


class StructureInfo(BaseModel):
    sections: list[Section]
    bar_length_sec: float


class EnergyProfile(BaseModel):
    overall_energy: float          # 0-1
    danceability: float            # 0-1, onset-density/regularity based
    valence: float                  # 0-1, spectral-brightness proxy for "mood"
    curve: list[float]              # 0-1 per-bar energy, for the UI energy graph


class GenreGuess(BaseModel):
    label: str
    confidence: float


class AnalysisResult(BaseModel):
    session_id: str
    duration_sec: float
    tempo: TempoInfo
    key: KeyInfo
    time_signature: TimeSignatureInfo
    structure: StructureInfo
    energy: EnergyProfile
    genre_guesses: list[GenreGuess]


# --- Import ---

class ImportResult(BaseModel):
    session_id: str
    filename: str
    duration_sec: float
    sample_rate: int
    channels: int


# --- Separation ---

class SeparationResult(BaseModel):
    session_id: str
    stems: dict[str, str]   # stem name -> relative path under the session dir


# --- Edit generation ---

class EditStyle(str, Enum):
    HOUSE = "house"
    TECH_HOUSE = "tech_house"
    DRUM_AND_BASS = "drum_and_bass"
    AFRO_HOUSE = "afro_house"
    MELODIC_HOUSE = "melodic_house"
    BASS_HOUSE = "bass_house"
    EXTENDED_CLUB_EDIT = "extended_club_edit"


class LengthTarget(str, Enum):
    ORIGINAL = "original"
    RADIO = "radio"          # ~3:30
    CLUB = "club"             # ~5:30
    EXTENDED = "extended"     # ~7:30+, DJ-tool length with long intro/outro


class GenerateRequest(BaseModel):
    session_id: str
    style: EditStyle
    target_bpm: Optional[float] = None   # None = keep detected BPM
    intensity: float = Field(0.6, ge=0.0, le=1.0)   # how aggressively arrangement is rebuilt
    energy: float = Field(0.7, ge=0.0, le=1.0)        # how hard drops/risers hit
    length_target: LengthTarget = LengthTarget.CLUB


class TimelineClip(BaseModel):
    section_label: str
    style_role: str        # e.g. "intro_drums_only", "drop_full", "breakdown_filtered"
    start_sec: float
    end_sec: float
    source_section_label: Optional[str] = None   # which original section this was built from


class GenerateResult(BaseModel):
    session_id: str
    edit_id: str
    style: EditStyle
    resulting_bpm: float
    duration_sec: float
    timeline: list[TimelineClip]
    preview_path: str   # relative path to a rendered preview WAV


# --- Export ---

class ExportFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"
    STEMS = "stems"


class ExportRequest(BaseModel):
    session_id: str
    edit_id: str
    formats: list[ExportFormat]


class ExportResult(BaseModel):
    session_id: str
    edit_id: str
    files: dict[str, str]   # format -> relative path (or zip path for "stems")


# --- Jobs (async progress) ---

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobProgress(BaseModel):
    job_id: str
    kind: str            # "separation" | "generation" | "export"
    status: JobStatus
    progress: float = 0.0   # 0-1
    message: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
