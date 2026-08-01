"""FastAPI app entrypoint. Run with:
    uvicorn app.main:app --reload --port 8742
(or just `npm run dev` from the repo root, which does this for you)."""
from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .api import (
    routes_analysis,
    routes_export,
    routes_generate,
    routes_import,
    routes_jobs,
    routes_separation,
)
from .jobs import job_manager

config.ensure_dirs()

app = FastAPI(title="AI DJ Edit Studio backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_import.router)
app.include_router(routes_analysis.router)
app.include_router(routes_separation.router)
app.include_router(routes_generate.router)
app.include_router(routes_export.router)
app.include_router(routes_jobs.router)

# Serves everything under a session's directory (original audio, stems,
# rendered previews/exports) so the Electron UI can play/download them
# directly by relative path, e.g. GET /sessions/<id>/edits/<edit_id>/preview.wav
app.mount("/sessions", StaticFiles(directory=str(config.SESSIONS_DIR)), name="sessions")


@app.on_event("startup")
async def _bind_job_loop() -> None:
    job_manager.bind_loop(asyncio.get_running_loop())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
