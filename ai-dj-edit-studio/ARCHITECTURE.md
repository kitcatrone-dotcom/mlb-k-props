# AI DJ Edit Studio — Architecture

Personal-use desktop application that takes a song you legally have access to and
produces professional-quality DJ edits: extended club edits, House, Tech House,
Drum & Bass, Afro House, Melodic House, and Bass House versions, with stems,
intros/outros, transitions, risers, fills, breakdowns, and drops.

## 1. High-level design

Audio ML (stem separation, beat/key detection, DSP synthesis) is dominated by the
Python ecosystem (PyTorch-based Demucs, librosa, pyrubberband, pedalboard). Native
desktop UI is best served by a web-tech shell (Electron) for the drag-and-drop /
waveform / mixer-style interface a DJ tool needs. So the app is a **two-process
local application**:

```
┌─────────────────────────────┐        HTTP + WebSocket (localhost only)
│  Electron + React (TS) UI   │ <────────────────────────────────┐
│  - Drag & drop import       │                                  │
│  - Waveform / structure view│                                  │
│  - Genre & remix controls   │                                  │
│  - Job progress             │                                  │
│  - Export panel             │                                  │
└─────────────────────────────┘                                  │
                                                                  ▼
                                              ┌───────────────────────────────────┐
                                              │  Python FastAPI backend (local)    │
                                              │  - Audio import/decode             │
                                              │  - Analysis: BPM/key/time-sig/     │
                                              │    structure/energy/genre          │
                                              │  - Stem separation (Demucs)        │
                                              │  - Edit generation engine          │
                                              │  - DSP: time-stretch, filters,     │
                                              │    risers, fills, synth drums      │
                                              │  - Render & export                 │
                                              └───────────────────────────────────┘
```

The Electron app spawns the Python backend as a child process on launch (a
"sidecar"), so from the user's point of view it's one application — `npm run dev`
in development, one installer/binary in production (packaged with PyInstaller +
electron-builder).

Why not put everything in Node? There is no Node-native equivalent of Demucs,
librosa, or rubberband with comparable quality — reimplementing them would be a
multi-year research project, not an engineering task. Why not a pure-Python
desktop UI (e.g. PyQt)? It's usable but noticeably behind web tech for the kind of
rich waveform/drag-drop/animated mixer UI this app calls for, and Electron +
React gives a much larger component ecosystem (wavesurfer.js, etc).

## 2. Processing pipeline

```
Import → Decode/Normalize → Analyze → Separate Stems → Generate Edit → Render → Export
```

1. **Import**: MP3/WAV/FLAC/AIFF accepted, decoded to a canonical working format
   (48kHz/32-bit float WAV) via `soundfile`/`pydub`+ffmpeg.
2. **Analyze**:
   - Tempo (BPM) — `librosa` beat tracking + tempogram, octave-error correction.
   - Key — chroma + Krumhansl-Schmuckler key-profile correlation, reported in
     both standard notation ("A Minor") and **Camelot notation** ("8A") since
     that's the notation working DJs actually use for harmonic mixing.
   - Time signature — periodicity analysis of the onset/beat grid (4/4, 3/4, 6/8).
   - Song structure — self-similarity matrix (MFCC/chroma) + novelty-curve
     segmentation + agglomerative clustering → labeled sections (intro, verse,
     build, drop/chorus, breakdown, bridge, outro).
   - Emotional energy & genre — RMS/spectral-contrast/onset-density feature
     heuristics now, with a pluggable interface to swap in a pretrained
     classifier (e.g. an Essentia/`mtg-jamendo` or HuggingFace audio-tagging
     model) later without touching the rest of the pipeline.
3. **Separate stems**: Demucs (`htdemucs_ft`, 4-stem: vocals/drums/bass/other).
4. **Generate edit**: a `StyleProfile` (House, Tech House, D&B, Afro House,
   Melodic House, Bass House, Extended Club Edit) drives an `Arrangement`
   built from the detected structure + user parameters (target BPM, intensity,
   energy, length). The vocal stem's original timing/alignment is preserved
   (only tempo/pitch-matched, never re-cut), while drum/bass/other stems are
   rebuilt: re-timed, layered with genre-appropriate synthesized percussion,
   filtered breakdowns, risers/sweeps, drum fills at transitions, and DJ-ready
   extended intro/outro (16/32-bar drum-only sections for beatmatching).
5. **Render**: mix the timeline of processed clips down to a stereo master with
   automation (filter sweeps, gain rides), loudness-normalize.
6. **Export**: WAV (24-bit), MP3 (320kbps via LAME), and the individual stems,
   all as a downloadable session bundle.

## 3. Recommended open-source libraries & models

| Purpose | Library / Model | Why |
|---|---|---|
| Stem separation | **Demucs v4** (`htdemucs_ft`, Meta/Facebook Research) | Best open-source separation quality available (SDR beats Spleeter/Open-Unmix); native PyTorch, pip-installable, actively maintained. |
| Alternative separation | **Spleeter** (Deezer) | Faster/lighter, lower quality; useful as a fast-preview fallback. |
| Beat/tempo detection | **librosa** (`beat_track`, `tempo`) | Standard, robust, pure Python + numpy/scipy, no heavy deps. |
| Advanced beat/downbeat | **madmom** | State-of-the-art downbeat/meter tracking (DBNBeatTracker/DownBeatTracker) — used for time-signature/downbeat refinement. |
| Key detection | **librosa** chroma + Krumhansl-Schmuckler profiles | Well-established, transparent algorithm; no black-box model needed. |
| Advanced audio features/genre | **Essentia** (with `essentia-tensorflow` + MTG models, e.g. `genre_discogs400`, `mood`/energy models) | Best open-source library for genre/mood tagging with pretrained models; optional upgrade path. |
| Time-stretch / pitch-shift | **pyrubberband** (wraps Rubber Band Library) / **librosa.effects** fallback | Rubber Band gives the highest-quality, most "DJ-grade" time-stretch (formant-preserving), critical for keeping vocals natural when changing tempo. |
| Audio effects (filters, reverb, delay) | **Pedalboard** (Spotify) | Fast, high-quality, VST-like effects in pure Python; used for filter sweeps, reverb tails, delays on risers/fills. |
| Core DSP / synthesis | **numpy / scipy** | Custom drum-hit synthesis (kick/clap/hat), riser/sweep synthesis, envelopes. |
| Audio I/O & format conversion | **soundfile**, **pydub** (+ **ffmpeg**) | Broad codec support incl. MP3/FLAC/AIFF; ffmpeg is the actual decode/encode workhorse. |
| MP3 encoding | **LAME** (via pydub/ffmpeg) | Standard high-quality MP3 encoder. |
| Loudness normalization | **pyloudnorm** (ITU-R BS.1770) | Broadcast-standard loudness metering for consistent export levels. |
| Backend framework | **FastAPI** + **uvicorn** | Async, typed, WebSocket support for progress streaming, trivial to sidecar from Electron. |
| Desktop shell | **Electron** + **electron-builder** | Cross-platform packaging (macOS/Windows/Linux) for a Python-backed app. |
| Frontend | **React 18 + TypeScript + Vite** | Fast dev loop, typed, huge component ecosystem. |
| Waveform UI | **wavesurfer.js** | De facto standard waveform/region UI, used by many browser DAWs. |
| State management | **Zustand** | Minimal, avoids Redux boilerplate for a UI this size. |

### On "AI music generation"

Full generative-AI music models (MusicGen, Stable Audio, JASCO, etc.) are for
**generating new musical material from scratch/text**, which is not what a DJ
edit tool should do to someone else's track — the goal here is *rearranging and
re-producing* the original song, not synthesizing new melodic/harmonic content
over it (and doing so would create real content/licensing problems even for
personal use). This architecture therefore does not use a generative music
model; "generation" here means **arrangement generation** (structure/timeline)
plus **DSP synthesis** for drums/risers/fx layered on top of the separated
stems. This is both the technically correct approach and the one that respects
the source material.

## 4. Full file structure

```
ai-dj-edit-studio/
├── ARCHITECTURE.md
├── README.md
├── package.json                     # root dev scripts (concurrently runs backend + frontend)
├── .gitignore
├── scripts/
│   ├── setup.sh                     # one-shot beginner setup (venv, pip, npm, ffmpeg check)
│   └── download_models.py           # fetches Demucs weights ahead of first run
├── backend/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── app/
│       ├── __init__.py
│       ├── main.py                  # FastAPI app, CORS, router mounting
│       ├── config.py                # paths, constants, env
│       ├── schemas.py               # pydantic models (shared contract w/ frontend types)
│       ├── jobs.py                  # in-memory job manager + progress events
│       ├── storage.py               # session/workdir management
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── io.py                # decode/normalize any input format
│       │   ├── analysis/
│       │   │   ├── __init__.py
│       │   │   ├── tempo.py
│       │   │   ├── key.py
│       │   │   ├── timesig.py
│       │   │   ├── structure.py
│       │   │   └── energy.py
│       │   ├── separation/
│       │   │   ├── __init__.py
│       │   │   └── demucs_engine.py
│       │   ├── generation/
│       │   │   ├── __init__.py
│       │   │   ├── engine.py        # EditGenerationEngine orchestrator
│       │   │   ├── arrangement.py   # structure + params -> section timeline
│       │   │   ├── styles.py        # StyleProfile definitions (7 styles) + registry
│       │   │   ├── drum_patterns.py # per-genre-family rhythm pattern generators
│       │   │   └── dsp/
│       │   │       ├── __init__.py
│       │   │       ├── timestretch.py
│       │   │       ├── synth.py     # kick/clap/hat/riser/impact/sweep synthesis
│       │   │       ├── fx.py        # filters/reverb/delay via Pedalboard
│       │   │       └── mixer.py     # timeline -> rendered stereo buffer
│       │   └── export/
│       │       ├── __init__.py
│       │       └── render.py        # mixdown, normalize, WAV/MP3/stems export
│       └── api/
│           ├── __init__.py
│           ├── routes_import.py
│           ├── routes_analysis.py
│           ├── routes_separation.py
│           ├── routes_generate.py
│           ├── routes_export.py
│           └── routes_jobs.py
├── models/
│   └── README.md                    # where model weights live + how they're fetched
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    ├── electron/
    │   ├── main.ts                  # Electron main process, spawns Python sidecar
    │   └── preload.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/client.ts
        ├── state/store.ts
        ├── types.ts
        ├── components/
        │   ├── DropZone.tsx
        │   ├── WaveformPlayer.tsx
        │   ├── StructureTimeline.tsx
        │   ├── AnalysisSummary.tsx
        │   ├── GenreSelector.tsx
        │   ├── RemixControls.tsx
        │   ├── JobProgress.tsx
        │   ├── StemMixer.tsx
        │   └── ExportPanel.tsx
        └── styles/
            └── global.css
```

## 5. Build phases

- **Phase 1 — Foundations**: repo scaffold, backend skeleton (FastAPI + job
  manager), frontend skeleton (Electron + React + Vite), install/setup docs.
- **Phase 2 — Analysis engine**: import/decode, BPM, key, time signature,
  structure segmentation, energy/genre heuristics, analysis API + UI display.
- **Phase 3 — Stem separation**: Demucs integration, job progress streaming,
  stem playback/mixer UI.
- **Phase 4 — Edit generation engine**: arrangement builder, all 7 style
  profiles, drum-pattern synthesis, time-stretch/pitch-match, filters/risers/
  fills/breakdowns, timeline renderer.
- **Phase 5 — Remix controls & UX polish**: target BPM/intensity/energy/length
  controls wired end-to-end, waveform + structure visualization, one-click
  export flow.
- **Phase 6 — Export & packaging**: WAV/MP3/stems export, loudness
  normalization, PyInstaller + electron-builder packaging into a real
  installable desktop app.

This build proceeds phase by phase, committing working code at each phase
boundary.
