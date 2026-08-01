# AI DJ Edit Studio

A personal-use desktop app that takes a song you have legal rights to and
generates professional-quality DJ edits — House, Tech House, Drum & Bass,
Afro House, Melodic House, Bass House, and Extended Club Edit — complete with
custom intros/outros, transitions, risers, drum fills, breakdowns, and drops,
built from stems separated out of the original track.

See `ARCHITECTURE.md` for the full technical design. This README is the
beginner-friendly "how do I actually get this running" guide.

> **Use responsibly.** Only import audio you have the legal right to edit.
> This tool is for personal use (practice edits, personal sets); it does not
> grant you any redistribution rights to the source material.

## What you're installing

The app has two halves that run together on your machine (nothing goes to
the cloud):

- A **Python backend** that does all the audio analysis, stem separation, and
  DSP/rendering work.
- An **Electron + React desktop UI** that talks to that backend on
  `localhost` and gives you the drag-and-drop / waveform / controls
  experience.

## 1. Prerequisites

Install these first (all free, all cross-platform):

| Tool | Why | macOS | Windows | Linux |
|---|---|---|---|---|
| **Python 3.10 or 3.11** | Backend runtime | `brew install python@3.11` | [python.org installer](https://www.python.org/downloads/) | `sudo apt install python3.11 python3.11-venv` |
| **Node.js 18+** | Frontend/Electron runtime | `brew install node` | `winget install OpenJS.NodeJS.LTS` | `sudo apt install nodejs npm` |
| **ffmpeg** | Decodes/encodes MP3, FLAC, AIFF | `brew install ffmpeg` | `winget install ffmpeg` | `sudo apt install ffmpeg` |
| **Rubber Band CLI** | High-quality time-stretch/pitch-shift | `brew install rubberband` | via MSYS2, or skip (see fallback note below) | `sudo apt install rubberband-cli` |
| **git** | To clone this repo | usually preinstalled | `winget install Git.Git` | usually preinstalled |

> Windows note: if installing `rubberband-cli` is inconvenient, the backend
> automatically falls back to librosa's built-in time-stretch (see
> `backend/app/audio/generation/dsp/timestretch.py`). Quality is slightly
> lower on large tempo changes, but everything still works.

A discrete GPU is **not required**. Demucs will use one automatically (CUDA
on Windows/Linux, MPS on Apple Silicon) if present, which speeds up stem
separation from ~1-2 minutes to a few seconds per song; on CPU-only machines
it just takes longer.

## 2. Get the code

```bash
git clone <this-repo-url>
cd ai-dj-edit-studio
```

## 3. One-command setup

```bash
npm run setup
```

This runs `scripts/setup.sh`, which:
1. Checks that ffmpeg/node/python/rubberband are on your `PATH`.
2. Creates a Python virtual environment at `backend/.venv` and installs every
   backend dependency from `backend/requirements.txt`.
3. Installs the root and `frontend/` npm dependencies.
4. Pre-downloads the Demucs stem-separation model weights (~330MB, one-time)
   so your first edit doesn't stall on a download.

If any prerequisite is missing, the script tells you exactly what to install
and stops — just install it and re-run `npm run setup`.

### Doing it manually (if you'd rather not run the script)

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ../scripts/download_models.py
deactivate
cd ..

# Frontend
npm install
cd frontend && npm install && cd ..
```

## 4. Run it

```bash
npm run dev
```

This starts the Python backend (`http://127.0.0.1:8742`) and the Electron
app together. The Electron window opens automatically. In development the
backend also auto-reloads on code changes.

## 5. Using the app

1. **Drag and drop** an MP3/WAV/FLAC/AIFF file onto the import zone (or click
   to browse).
2. Wait for **Analysis** — you'll see detected BPM, key (with Camelot
   notation), time signature, and a color-coded structure timeline
   (intro/verse/build/drop/breakdown/outro).
3. Click **Separate Stems** — Demucs pulls out vocals/drums/bass/other
   (progress streams live via WebSocket).
4. Pick an **edit style** (House, Tech House, D&B, Afro House, Melodic
   House, Bass House, or Extended Club Edit) and set:
   - Target BPM (or "keep original")
   - Remix intensity (how aggressively the arrangement is rebuilt)
   - Energy level (how hard the drops/risers hit)
   - Target song length
5. Click **Generate** — the edit generation engine rebuilds the instrumental
   arrangement around your original vocal timing, adds a DJ-ready intro/
   outro, transitions, risers, and fills.
6. Preview on the waveform, then **Export**: WAV, MP3 (320kbps), and/or the
   individual stems.

## 6. Project layout

See `ARCHITECTURE.md` §4 for the complete annotated file tree. Quick map:

- `backend/app/audio/analysis/` — BPM/key/time-signature/structure/energy
- `backend/app/audio/separation/` — Demucs stem separation
- `backend/app/audio/generation/` — arrangement + style profiles + DSP/synth
- `backend/app/audio/export/` — mixdown, loudness-normalize, WAV/MP3 export
- `backend/app/api/` — FastAPI routes the frontend calls
- `frontend/src/components/` — the UI (drop zone, waveform, controls, mixer)

## 7. Packaging a standalone installer (optional, later phase)

Once you're happy with a build, `npm run package` bundles the Python backend
with PyInstaller and wraps the whole thing with `electron-builder` into a
single installable app (`.dmg`/`.exe`/`.AppImage`) that doesn't require the
end user to have Python or Node installed. (This step ships in Phase 6 of
the build — see `ARCHITECTURE.md` §5 for phase status.)

## Troubleshooting

- **`madmom` fails to install**: it needs a C compiler and Cython. On macOS,
  `xcode-select --install` first. On Ubuntu, `sudo apt install build-essential
  python3-dev`. If it still fails, the app degrades gracefully — time
  signature detection falls back to the librosa-only heuristic.
- **Stem separation is slow**: expected on CPU-only machines (a few minutes
  per song). It's much faster with a CUDA or Apple Silicon GPU.
- **Import fails on an MP3**: confirm `ffmpeg -version` works in your
  terminal — pydub shells out to it for decoding.
